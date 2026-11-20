import Foundation
import PinkhaKit
import PinkhaAnyEngine

public protocol AnyTorahObservableOperationStore: AnyTorahOperationStore {
    /// Each update is a complete canonical projection. The first is atomic.
    func watch(session: AnyStreamSession, limit: Int) async throws
        -> AsyncThrowingStream<AnyTorahLiveSnapshot, Error>
}

extension AnyNativeTorahOperationStore: AnyTorahObservableOperationStore {
    public func watch(session: AnyStreamSession, limit: Int = 10_000) async throws
        -> AsyncThrowingStream<AnyTorahLiveSnapshot, Error> {
        try await repository.watch(session: session, limit: limit)
    }
}

public struct AnyTorahAssociationLiveSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let target: TorahAssociationTarget
    public let generation: UUID
    public let initial: Bool
    public let snapshot: AnyTorahAssociationSnapshot
}
