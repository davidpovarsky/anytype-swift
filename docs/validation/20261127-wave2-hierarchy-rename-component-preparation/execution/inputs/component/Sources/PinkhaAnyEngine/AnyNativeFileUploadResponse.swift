import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// A single native request owns its upload/data task and serial response
/// delegate. The original file body is streamed by Foundation from a completed
/// private file; only a bounded JSON acknowledgement is retained in memory.
final class AnyNativeFileUploadResponse: NSObject, URLSessionDataDelegate, @unchecked Sendable {
    static let maximumResponseBytes = 65_536
    private let lock = NSLock()
    private let delegateQueue: OperationQueue
    private var continuation: CheckedContinuation<(Data, HTTPURLResponse), any Error>?
    private var currentSession: URLSession?
    private var currentTask: URLSessionTask?
    private var expectedURL: URL?
    private var response: HTTPURLResponse?
    private var bytes = Data()
    private var consumed = false
    private var finishing = false
    private var taskCompleted = false
    private var sessionInvalidated = false
    private var pendingResult: Result<(Data, HTTPURLResponse), any Error>?

    init(delegateQueue: OperationQueue? = nil) {
        let queue = delegateQueue ?? OperationQueue()
        queue.maxConcurrentOperationCount = 1
        self.delegateQueue = queue
        super.init()
    }

    func perform(_ request: URLRequest, fileURL: URL?) async throws -> (Data, HTTPURLResponse) {
        try await withTaskCancellationHandler {
            try Task.checkCancellation()
            return try await withCheckedThrowingContinuation { continuation in
                // Register and start under the cancellation lock. Cancellation
                // before this point creates no session; after it, completion
                // must await both callbacks from this exact owned task/session.
                lock.lock()
                guard !consumed else {
                    lock.unlock()
                    continuation.resume(throwing: AnyEngineError.malformedResponse("file attachment response reused"))
                    return
                }
                consumed = true
                if let pendingResult {
                    lock.unlock()
                    continuation.resume(with: pendingResult)
                    return
                }
                let configuration = URLSessionConfiguration.ephemeral
                configuration.httpShouldSetCookies = false
                configuration.httpCookieStorage = nil
                configuration.urlCredentialStorage = nil
                configuration.urlCache = nil
                configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
                configuration.timeoutIntervalForRequest = request.timeoutInterval
                configuration.timeoutIntervalForResource = 300
                let session = URLSession(configuration: configuration, delegate: self, delegateQueue: delegateQueue)
                let task: URLSessionTask
                if let fileURL { task = session.uploadTask(with: request, fromFile: fileURL) }
                else { task = session.dataTask(with: request) }
                self.continuation = continuation
                currentSession = session; currentTask = task; expectedURL = request.url
                task.resume()
                lock.unlock()
            }
        } onCancel: {
            self.finish(.failure(CancellationError()))
        }
    }

    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest,
                    completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        // No second target receives the original body or managed capability.
        completionHandler(nil)
        if owns(session, task: task) { finish(.failure(AnyNativeFileUploadError.redirectRefused)) }
    }

    func urlSession(_ session: URLSession, task: URLSessionTask,
                    didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping @Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        // The loopback runtime uses its explicit per-boot header, never an HTTP
        // authentication challenge that could repeat the mutation body.
        completionHandler(.cancelAuthenticationChallenge, nil)
    }

    func urlSession(_ session: URLSession, task: URLSessionTask,
                    needNewBodyStream completionHandler: @escaping @Sendable (InputStream?) -> Void) {
        // A request that asks to replay the upload does not obtain a new body.
        completionHandler(nil)
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive response: URLResponse,
                    completionHandler: @escaping @Sendable (URLSession.ResponseDisposition) -> Void) {
        guard owns(session, task: dataTask) else { completionHandler(.cancel); return }
        guard let http = response as? HTTPURLResponse else {
            completionHandler(.cancel)
            finish(.failure(AnyEngineError.malformedResponse("file attachment HTTP response")))
            return
        }
        guard response.expectedContentLength <= Int64(Self.maximumResponseBytes) else {
            completionHandler(.cancel)
            finish(.failure(AnyEngineError.readLimit))
            return
        }
        lock.lock()
        let active = !finishing
        let matches = expectedURL?.absoluteString.utf8.elementsEqual(http.url?.absoluteString.utf8 ?? "".utf8) == true
        if active && matches { self.response = http }
        lock.unlock()
        guard matches else {
            completionHandler(.cancel)
            finish(.failure(AnyEngineError.malformedResponse("file attachment HTTP origin")))
            return
        }
        completionHandler(active ? .allow : .cancel)
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        lock.lock()
        guard currentSession === session, currentTask === dataTask, !finishing else { lock.unlock(); return }
        guard data.count <= Self.maximumResponseBytes - bytes.count else {
            lock.unlock()
            finish(.failure(AnyEngineError.readLimit))
            return
        }
        bytes.append(data)
        lock.unlock()
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: (any Error)?) {
        lock.lock()
        guard currentSession === session, currentTask === task else { lock.unlock(); return }
        taskCompleted = true
        let result: Result<(Data, HTTPURLResponse), any Error>
        if let error { result = .failure(error) }
        else if let response { result = .success((bytes, response)) }
        else { result = .failure(AnyEngineError.malformedResponse("file attachment missing response")) }
        let shutdown = beginFinishLocked(result)
        lock.unlock()
        requestShutdown(shutdown)
        resumeAfterDrain()
    }

    func urlSession(_ session: URLSession, didBecomeInvalidWithError error: (any Error)?) {
        lock.lock()
        guard currentSession === session else { lock.unlock(); return }
        sessionInvalidated = true
        lock.unlock()
        resumeAfterDrain()
    }

    private func owns(_ session: URLSession, task: URLSessionTask) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return currentSession === session && currentTask === task
    }

    private func finish(_ result: Result<(Data, HTTPURLResponse), any Error>) {
        lock.lock()
        let shutdown = beginFinishLocked(result)
        lock.unlock()
        requestShutdown(shutdown)
    }

    /// The caller holds lock. Observing task completion and preserving its
    /// first outcome are one transaction against concurrent cancellation.
    private func beginFinishLocked(_ result: Result<(Data, HTTPURLResponse), any Error>) -> (URLSessionTask?, URLSession?)? {
        guard !finishing else { return nil }
        finishing = true
        pendingResult = result
        return (currentTask, currentSession)
    }

    private func requestShutdown(_ shutdown: (URLSessionTask?, URLSession?)?) {
        guard let (task, session) = shutdown else { return }
        // Cancel this session's sole task, then request invalidation only after
        // its completion callbacks. invalidateAndCancel may invalidate the
        // session immediately; that alone cannot establish transport drain.
        // These calls initiate shutdown. They are not a completion barrier.
        // Keep the task, delegate, continuation and staged-file lifetime owned
        // until both actual completion and session invalidation are observed.
        task?.cancel()
        session?.finishTasksAndInvalidate()
    }

    private func resumeAfterDrain() {
        lock.lock()
        guard taskCompleted, sessionInvalidated,
              let result = pendingResult, let continuation else { lock.unlock(); return }
        self.continuation = nil; currentTask = nil; currentSession = nil
        pendingResult = nil
        response = nil; expectedURL = nil; bytes = Data()
        lock.unlock()
        // A completed 201 wins over later cancellation, preserving the existing
        // original-scope receipt callback before the caller's postflight fence.
        // An earlier cancellation still has an uncertain native outcome.
        // The serial queue also lets the last delegate callback return before
        // the Swift operation can finish and release its staged-file owner.
        delegateQueue.addOperation { continuation.resume(with: result) }
    }
}
