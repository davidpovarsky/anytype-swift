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
    private var continuation: CheckedContinuation<(Data, HTTPURLResponse), any Error>?
    private var currentSession: URLSession?
    private var currentTask: URLSessionTask?
    private var expectedURL: URL?
    private var response: HTTPURLResponse?
    private var bytes = Data()
    private var finished = false

    func perform(_ request: URLRequest, fileURL: URL?) async throws -> (Data, HTTPURLResponse) {
        try await withTaskCancellationHandler {
            try Task.checkCancellation()
            return try await withCheckedThrowingContinuation { continuation in
                let configuration = URLSessionConfiguration.ephemeral
                configuration.httpShouldSetCookies = false
                configuration.httpCookieStorage = nil
                configuration.urlCredentialStorage = nil
                configuration.urlCache = nil
                configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
                configuration.timeoutIntervalForRequest = request.timeoutInterval
                configuration.timeoutIntervalForResource = 300
                let queue = OperationQueue()
                queue.maxConcurrentOperationCount = 1
                let session = URLSession(configuration: configuration, delegate: self, delegateQueue: queue)
                let task: URLSessionTask
                if let fileURL { task = session.uploadTask(with: request, fromFile: fileURL) }
                else { task = session.dataTask(with: request) }
                lock.lock()
                guard !finished else {
                    lock.unlock()
                    session.invalidateAndCancel()
                    continuation.resume(throwing: CancellationError())
                    return
                }
                self.continuation = continuation
                currentSession = session; currentTask = task; expectedURL = request.url
                lock.unlock()
                task.resume()
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
        finish(.failure(AnyNativeFileUploadError.redirectRefused))
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
        let active = !finished
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
        guard !finished else { lock.unlock(); return }
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
        let result: Result<(Data, HTTPURLResponse), any Error>
        if let error { result = .failure(error) }
        else if let response { result = .success((bytes, response)) }
        else { result = .failure(AnyEngineError.malformedResponse("file attachment missing response")) }
        lock.unlock()
        finish(result)
    }

    private func finish(_ result: Result<(Data, HTTPURLResponse), any Error>) {
        lock.lock()
        guard !finished else { lock.unlock(); return }
        finished = true
        let continuation = continuation, task = currentTask, session = currentSession
        self.continuation = nil; currentTask = nil; currentSession = nil
        response = nil; expectedURL = nil; bytes = Data()
        lock.unlock()
        task?.cancel()
        session?.invalidateAndCancel()
        continuation?.resume(with: result)
    }
}
