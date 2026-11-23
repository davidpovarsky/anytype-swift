private final class OriginalEventDeliveryFence: @unchecked Sendable {
    enum Failure: Error { case ended, counterExhausted, invalidCompletion }
    private let lock = NSLock()
    private var accepted: UInt64 = 0
    private var delivered: UInt64 = 0
    private var failure: Failure?
    private var waiters: [(target: UInt64, continuation: CheckedContinuation<Void, Error>)] = []

    func enqueue(_ data: Data, into continuation: AsyncStream<Data>.Continuation) {
        lock.lock()
        var failed: [CheckedContinuation<Void, Error>] = []
        if failure == nil {
            if accepted == UInt64.max {
                failed = failLocked(.counterExhausted)
            } else {
                accepted += 1
            }
        }
        // Counter order and the original stream's enqueue order share this
        // lock. The original consumer/handler cannot acknowledge beforehand.
        switch continuation.yield(data) {
        case .enqueued:
            break
        case .dropped, .terminated:
            failed += failLocked(.ended)
        @unknown default:
            failed += failLocked(.ended)
        }
        let reason = failure
        lock.unlock()
        if let reason { for waiter in failed { waiter.resume(throwing: reason) } }
    }

    func didDeliverOne() {
        lock.lock()
        guard failure == nil else { lock.unlock(); return }
        guard delivered < accepted else {
            let failed = failLocked(.invalidCompletion)
            lock.unlock()
            for waiter in failed { waiter.resume(throwing: Failure.invalidCompletion) }
            return
        }
        delivered += 1
        let completed = waiters.filter { $0.target <= delivered }.map(\.continuation)
        waiters.removeAll { $0.target <= delivered }
        lock.unlock()
        for waiter in completed { waiter.resume() }
    }

    func waitForCurrentFrontier() async throws {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            lock.lock()
            if let failure {
                lock.unlock()
                continuation.resume(throwing: failure)
            } else if delivered == accepted {
                lock.unlock()
                continuation.resume()
            } else {
                waiters.append((accepted, continuation))
                lock.unlock()
            }
        }
    }

    func end() {
        lock.lock()
        let failed = failLocked(.ended)
        lock.unlock()
        for waiter in failed { waiter.resume(throwing: Failure.ended) }
    }

    private func failLocked(_ reason: Failure) -> [CheckedContinuation<Void, Error>] {
        if failure == nil { failure = reason }
        let failed = waiters.map(\.continuation)
        waiters.removeAll()
        return failed
    }
}
