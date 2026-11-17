import Foundation
import HanlinHostContracts

/// One completion without a structured-task join. A stalled native callback cannot hold up timeout.
/// The host admits at most one unfinished native read; late data is discarded, never retained here.
final class PinkhaHanlinReadRace: @unchecked Sendable {
    private let lock = NSLock()
    private var continuation: CheckedContinuation<PinkhaHanlinTextSnapshot, any Error>?
    private var terminalError: (any Error)?
    private var completed = false
    private var dispatched = false
    private var ended = false
    private var worker: Task<Void, Never>?
    private var timer: Task<Void, Never>?

    var wasDispatched: Bool { lock.withLock { dispatched } }
    var hasEnded: Bool { lock.withLock { ended } }

    func install(_ continuation: CheckedContinuation<PinkhaHanlinTextSnapshot, any Error>) -> Bool {
        lock.lock()
        if completed {
            let error = terminalError ?? HanlinHostError.cancelled
            lock.unlock()
            continuation.resume(throwing: error)
            return false
        }
        self.continuation = continuation
        lock.unlock()
        return true
    }

    func attach(worker: Task<Void, Never>, timer: Task<Void, Never>) {
        lock.lock()
        let stop = completed
        if !stop { self.worker = worker; self.timer = timer }
        lock.unlock()
        if stop { worker.cancel(); timer.cancel() }
    }

    /// Called immediately after the actual queued MainActor worker rechecks the invocation fence.
    func beginDispatch() -> Bool {
        lock.withLock {
            guard !completed else { return false }
            dispatched = true
            return true
        }
    }

    func operationEnded() { lock.withLock { ended = true } }
    func cancel() { finish(.failure(HanlinHostError.cancelled)) }

    func finish(_ result: Result<PinkhaHanlinTextSnapshot, any Error>) {
        lock.lock()
        guard !completed else { lock.unlock(); return }
        completed = true
        if case .failure(let error) = result { terminalError = error }
        let continuation = continuation
        self.continuation = nil
        let worker = worker
        let timer = timer
        self.worker = nil
        self.timer = nil
        lock.unlock()
        worker?.cancel()
        timer?.cancel()
        continuation?.resume(with: result)
    }
}
