import Foundation
import Testing

private struct PropertyPresentationRendezvousDeadline: Error {}

@MainActor
private final class SuspendedPropertyCalls<Value: Sendable> {
    private(set) var invocationCount = 0
    private var pending: [Int: CheckedContinuation<Value, any Error>] = [:]
    private var startedWaiters: [Int: CheckedContinuation<Void, any Error>] = [:]

    func invoke() async throws -> Value {
        let id = invocationCount
        invocationCount += 1
        return try await withTaskCancellationHandler {
            try Task.checkCancellation()
            return try await withCheckedThrowingContinuation { continuation in
                pending[id] = continuation
                startedWaiters.removeValue(forKey: id)?.resume(returning: ())
            }
        } onCancel: {
            Task { @MainActor [weak self] in self?.cancelPending(id) }
        }
    }

    func waitUntilStarted(_ id: Int) async throws {
        try Task.checkCancellation()
        guard invocationCount <= id else { return }
        // A missing dispatch fails the test instead of leaking a continuation.
        // The timer is only a failure deadline; normal scheduling uses the
        // exact invocation rendezvous and never sleeps to guess completion.
        let deadline = Task { @MainActor [weak self] in
            do { try await Task.sleep(for: .seconds(10)) }
            catch { return }
            self?.failWaiter(id, PropertyPresentationRendezvousDeadline())
        }
        defer { deadline.cancel() }
        try await withTaskCancellationHandler {
            try Task.checkCancellation()
            try await withCheckedThrowingContinuation { continuation in
                startedWaiters[id] = continuation
            }
        } onCancel: {
            Task { @MainActor [weak self] in self?.failWaiter(id, CancellationError()) }
        }
    }

    func succeed(_ id: Int, _ value: Value) throws {
        let continuation = try #require(pending.removeValue(forKey: id))
        continuation.resume(returning: value)
    }

    func fail(_ id: Int, _ error: any Error) throws {
        let continuation = try #require(pending.removeValue(forKey: id))
        continuation.resume(throwing: error)
    }

    func cancelAll() {
        let calls = Array(pending.values), waiters = Array(startedWaiters.values)
        pending.removeAll(); startedWaiters.removeAll()
        for call in calls { call.resume(throwing: CancellationError()) }
        for waiter in waiters { waiter.resume(throwing: CancellationError()) }
    }

    private func cancelPending(_ id: Int) {
        pending.removeValue(forKey: id)?.resume(throwing: CancellationError())
    }

    private func failWaiter(_ id: Int, _ error: any Error) {
        startedWaiters.removeValue(forKey: id)?.resume(throwing: error)
    }
}

