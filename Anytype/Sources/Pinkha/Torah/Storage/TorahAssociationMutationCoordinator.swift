import Foundation
import PinkhaKit

struct TorahAssociationDocumentKey: Sendable, Hashable {
    let spaceId: String
    let objectId: String
}

/// A process-wide, per-document async operation chain. The complete native
/// read/apply/write/readback transaction is one queued closure, so actor
/// reentrancy at an internal await cannot admit another mutation for that key.
actor TorahAssociationMutationCoordinator {
    static let shared = TorahAssociationMutationCoordinator()

    private struct Tail: Sendable {
        let token: UUID
        let task: Task<Void, Never>
    }

    private var tails: [TorahAssociationDocumentKey: Tail] = [:]

    func enqueue<Value: Sendable>(
        key: TorahAssociationDocumentKey,
        operation: @escaping @Sendable () async throws -> Value
    ) async throws -> Value {
        try Task.checkCancellation()

        let predecessor = tails[key]?.task
        let token = UUID()
        let work = Task<Value, Error> {
            if let predecessor {
                await predecessor.value
            }
            return try await operation()
        }
        let completion = Task<Void, Never> {
            _ = await work.result
        }
        tails[key] = Tail(token: token, task: completion)

        let result = await work.result
        if tails[key]?.token == token {
            tails.removeValue(forKey: key)
        }
        return try result.get()
    }
}

enum TorahAssociationPersistenceState: Sendable, Equatable {
    case waiting
    case saving
    case saved
    case conflict(String)
    case uncertain(String)
    case error(String)
}

struct TorahAssociationPersistenceEvent: Sendable, Equatable {
    let operationId: String
    let location: TorahAssociationLocation
    let state: TorahAssociationPersistenceState
}

/// Async observable state used by the later host UI. A UI must never infer
/// success from optimistic state; only a confirmed native readback emits saved.
actor TorahAssociationPersistenceStatusCenter {
    static let shared = TorahAssociationPersistenceStatusCenter()

    private var latest: [TorahAssociationLocation: TorahAssociationPersistenceEvent] = [:]
    private var continuations: [UUID: AsyncStream<TorahAssociationPersistenceEvent>.Continuation] = [:]

    func state(for location: TorahAssociationLocation) -> TorahAssociationPersistenceEvent? {
        latest[location]
    }

    func updates() -> AsyncStream<TorahAssociationPersistenceEvent> {
        let id = UUID()
        let (stream, continuation) = AsyncStream<TorahAssociationPersistenceEvent>.makeStream()
        continuations[id] = continuation
        continuation.onTermination = { [weak self] _ in
            Task { await self?.removeContinuation(id: id) }
        }
        return stream
    }

    func publish(_ event: TorahAssociationPersistenceEvent) {
        latest[event.location] = event
        for continuation in continuations.values {
            continuation.yield(event)
        }
    }

    private func removeContinuation(id: UUID) {
        continuations.removeValue(forKey: id)
    }
}
