import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// A generation belongs to one owned engine/account lifetime. Invalidate before
/// switching that lifetime; invalidation cancels every registered HTTP stream.
public actor AnyStreamSession {
    public let generation: UUID
    private var active = true
    private var cancellations: [UUID: @Sendable () -> Void] = [:]

    public init(generation: UUID = UUID()) { self.generation = generation }

    public func requireActive(generation: UUID) throws {
        guard active, generation == self.generation else { throw AnyLiveQueryError.staleGeneration }
    }

    public func invalidate() {
        active = false
        let pending = Array(cancellations.values)
        cancellations.removeAll()
        for cancel in pending { cancel() }
    }

    public func register(generation: UUID, _ cancel: @escaping @Sendable () -> Void) throws -> UUID {
        try Task.checkCancellation()
        try requireActive(generation: generation)
        let id = UUID()
        cancellations[id] = cancel
        return id
    }

    public func unregister(_ id: UUID) { cancellations.removeValue(forKey: id) }
}

/// Callback bridge only. Safety invariant: every mutable field is protected by
/// lock; continuation delivery/cancellation occurs after unlocking. URLSession
/// callbacks use a serial queue. Follow-up: replace with a portable structured
/// URLSession byte sequence once FoundationNetworking supports it on Windows.
private final class AnySSEConnection: NSObject, URLSessionDataDelegate, @unchecked Sendable {
    private let lock = NSLock()
    private var parser: AnySSEParser
    private var continuation: AsyncThrowingStream<AnySSEFrame, Error>.Continuation?
    private var session: URLSession?
    private var task: URLSessionDataTask?
    private var finished = false

    private init(
        continuation: AsyncThrowingStream<AnySSEFrame, Error>.Continuation,
        maximumFrameBytes: Int
    ) {
        self.continuation = continuation
        parser = AnySSEParser(maximumFrameBytes: maximumFrameBytes)
    }

    static func open(
        request: URLRequest, maximumFrameBytes: Int
    ) -> (AnySSEConnection, AsyncThrowingStream<AnySSEFrame, Error>) {
        let pair = AsyncThrowingStream<AnySSEFrame, Error>.makeStream(bufferingPolicy: .bufferingOldest(8))
        let connection = AnySSEConnection(
            continuation: pair.continuation, maximumFrameBytes: maximumFrameBytes)
        pair.continuation.onTermination = { @Sendable [weak connection] _ in connection?.cancel() }
        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpShouldSetCookies = false
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.timeoutIntervalForRequest = 90
        configuration.timeoutIntervalForResource = 3600
        let queue = OperationQueue()
        queue.maxConcurrentOperationCount = 1
        let session = URLSession(configuration: configuration, delegate: connection, delegateQueue: queue)
        let task = session.dataTask(with: request)
        connection.lock.lock()
        connection.session = session
        connection.task = task
        connection.lock.unlock()
        task.resume()
        return (connection, pair.stream)
    }

    func cancel() { finish(CancellationError()) }

    private func finish(_ error: Error) {
        lock.lock()
        guard !finished else { lock.unlock(); return }
        finished = true
        let continuation = self.continuation
        let session = self.session
        let task = self.task
        self.continuation = nil
        self.session = nil
        self.task = nil
        lock.unlock()
        continuation?.finish(throwing: error)
        task?.cancel()
        session?.invalidateAndCancel()
    }

    func urlSession(
        _ session: URLSession, task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest,
        completionHandler: @escaping @Sendable (URLRequest?) -> Void
    ) {
        completionHandler(nil)
    }

    func urlSession(
        _ session: URLSession, dataTask: URLSessionDataTask, didReceive response: URLResponse,
        completionHandler: @escaping @Sendable (URLSession.ResponseDisposition) -> Void
    ) {
        guard let response = response as? HTTPURLResponse else {
            completionHandler(.cancel)
            finish(AnyLiveQueryError.invalidEvent("HTTP response"))
            return
        }
        guard response.statusCode == 200 else {
            completionHandler(.cancel)
            finish(AnyLiveQueryError.http(response.statusCode))
            return
        }
        guard response.mimeType?.lowercased() == "text/event-stream" else {
            completionHandler(.cancel)
            finish(AnyLiveQueryError.invalidEvent("Content-Type"))
            return
        }
        completionHandler(.allow)
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        lock.lock()
        guard !finished, let continuation else { lock.unlock(); return }
        let frames: [AnySSEFrame]
        do { frames = try parser.feed(data) }
        catch { lock.unlock(); finish(error); return }
        lock.unlock()
        for frame in frames {
            switch continuation.yield(frame) {
            case .enqueued: break
            case .dropped: finish(AnyLiveQueryError.bufferOverflow); return
            case .terminated: cancel(); return
            @unknown default: finish(AnyLiveQueryError.bufferOverflow); return
            }
        }
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        lock.lock()
        guard !finished else { lock.unlock(); return }
        var finalError: Error = error ?? AnyLiveQueryError.disconnected
        do { try parser.finish() } catch { finalError = error }
        lock.unlock()
        finish(finalError)
    }
}

extension AnyHTTPClient {
    /// The query must request includeTotal when requireComplete is true. Every
    /// terminal event, EOF or overflow requires a new subscription/snapshot.
    /// Consumers must check the generation before committing a buffered update
    /// to their UI; the host owns account switching and the lifetime fence.
    public func subscribeQuery(
        spaceID: String, query: AnyJSON, streamSession: AnyStreamSession,
        maximumRecords: Int, requireComplete: Bool = false,
        maximumFrameBytes: Int = 8 * 1024 * 1024
    ) async throws -> AsyncThrowingStream<AnyQueryUpdate, Error> {
        try await subscribe(
            path: ["v1", "spaces", spaceID, "query", "subscribe"],
            spaceID: spaceID, query: query, streamSession: streamSession,
            maximumRecords: maximumRecords, requireComplete: requireComplete,
            maximumFrameBytes: maximumFrameBytes)
    }

    /// Live native object query, sharing the exact transport, atomic window and
    /// generation fences of dataset subscriptions.
    public func subscribeObjectQuery(
        spaceID: String, query: AnyJSON, streamSession: AnyStreamSession,
        maximumRecords: Int, requireComplete: Bool = false,
        maximumFrameBytes: Int = 8 * 1024 * 1024
    ) async throws -> AsyncThrowingStream<AnyQueryUpdate, Error> {
        try await subscribe(
            path: ["v1", "spaces", spaceID, "objects", "query", "subscribe"],
            spaceID: spaceID, query: query, streamSession: streamSession,
            maximumRecords: maximumRecords, requireComplete: requireComplete,
            maximumFrameBytes: maximumFrameBytes)
    }

    private func subscribe(
        path: [String], spaceID: String, query: AnyJSON, streamSession: AnyStreamSession,
        maximumRecords: Int, requireComplete: Bool, maximumFrameBytes: Int
    ) async throws -> AsyncThrowingStream<AnyQueryUpdate, Error> {
        guard !spaceID.isEmpty, (1...10001).contains(maximumRecords) else {
            throw AnyLiveQueryError.incompleteWindow
        }
        let generation = streamSession.generation
        let frames = try await subscribeFrames(
            method: "POST", path: path, body: query, streamSession: streamSession,
            maximumFrameBytes: maximumFrameBytes)
        return AsyncThrowingStream(bufferingPolicy: .bufferingOldest(2)) { continuation in
            let worker = Task {
                do {
                    var window = AnyQueryWindow(
                        generation: generation, limit: maximumRecords, requireComplete: requireComplete,
                        maximumWindowBytes: maximumFrameBytes)
                    for try await frame in frames {
                        try Task.checkCancellation()
                        try await streamSession.requireActive(generation: generation)
                        guard let update = try window.apply(frame, generation: generation) else { continue }
                        switch continuation.yield(update) {
                        case .enqueued: break
                        case .dropped: throw AnyLiveQueryError.bufferOverflow
                        case .terminated: throw CancellationError()
                        @unknown default: throw AnyLiveQueryError.bufferOverflow
                        }
                    }
                    throw AnyLiveQueryError.disconnected
                } catch { continuation.finish(throwing: error) }
            }
            continuation.onTermination = { @Sendable _ in worker.cancel() }
        }
    }

    /// One bounded transport for stock query deltas and native full-state
    /// snapshots. Routes supply their own atomic-state parser; none uses replay.
    func subscribeFrames(
        method: String, path: [String], body: AnyJSON? = nil,
        query: [String: String] = [:], streamSession: AnyStreamSession,
        maximumFrameBytes: Int
    ) async throws -> AsyncThrowingStream<AnySSEFrame, Error> {
        guard ["GET", "POST"].contains(method),
              (1024...64 * 1024 * 1024).contains(maximumFrameBytes) else {
            throw AnyLiveQueryError.incompleteWindow
        }
        let generation = streamSession.generation
        try await streamSession.requireActive(generation: generation)
        try await checkAccount()
        try Task.checkCancellation()
        try await streamSession.requireActive(generation: generation)
        var request = try makeRequest(method: method, path: path, body: body, query: query)
        request.timeoutInterval = 90
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        guard (request.httpBody?.count ?? 0) <= 1024 * 1024 else { throw AnyLiveQueryError.frameTooLarge }
        let (connection, frames) = AnySSEConnection.open(
            request: request, maximumFrameBytes: maximumFrameBytes)
        let registration: UUID
        do { registration = try await streamSession.register(generation: generation) { connection.cancel() } }
        catch { connection.cancel(); throw error }
        // Registration can suspend while the caller is cancelled.
        do { try Task.checkCancellation() }
        catch {
            connection.cancel()
            await streamSession.unregister(registration)
            throw error
        }
        return AsyncThrowingStream(bufferingPolicy: .bufferingOldest(2)) { continuation in
            let worker = Task {
                do {
                    for try await frame in frames {
                        try Task.checkCancellation()
                        try await streamSession.requireActive(generation: generation)
                        try await checkAccount()
                        try await streamSession.requireActive(generation: generation)
                        switch continuation.yield(frame) {
                        case .enqueued: break
                        case .dropped: throw AnyLiveQueryError.bufferOverflow
                        case .terminated: throw CancellationError()
                        @unknown default: throw AnyLiveQueryError.bufferOverflow
                        }
                    }
                    throw AnyLiveQueryError.disconnected
                } catch { continuation.finish(throwing: error) }
                connection.cancel()
                await streamSession.unregister(registration)
            }
            continuation.onTermination = { @Sendable _ in
                worker.cancel()
                connection.cancel()
            }
        }
    }
}
