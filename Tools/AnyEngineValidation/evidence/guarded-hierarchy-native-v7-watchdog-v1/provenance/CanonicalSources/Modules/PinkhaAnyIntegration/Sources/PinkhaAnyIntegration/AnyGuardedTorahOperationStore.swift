
import Foundation
import PinkhaKit
import PinkhaAnyEngine

/// Explicit signed native lane. This type cannot be initialized with the generic
/// records-backed repository, even when account and Space happen to match.
public struct AnyGuardedTorahOperationStore: AnyTorahObservableOperationStore, AnyTorahObjectOperationObserving, Sendable {
    public let workspace: AnyTorahWorkspace
    public let repository: AnyGuardedTorahClaimsRepository

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard client.expectedAccountID == workspace.accountID else { throw AnyEngineError.accountChanged }
        self.workspace = workspace
        self.repository = try AnyGuardedTorahClaimsRepository(client: client, spaceID: workspace.spaceID)
    }

    public func snapshot() async throws -> AnyTorahProjection {
        try await repository.snapshot()
    }

    public func objectSnapshot(objectID: String, limit: Int = 10_000) async throws -> AnyGuardedTorahObjectSnapshot {
        try await repository.readObjectSnapshot(objectID: objectID, limit: limit)
    }

    public func watchObject(objectID: String, session: AnyStreamSession, limit: Int = 10_000) async throws
        -> AsyncThrowingStream<AnyGuardedTorahObjectLiveSnapshot, Error> {
        try await repository.watchObject(objectID: objectID, session: session, limit: limit)
    }

    public func append(_ operation: AnyTorahOperation,
                       authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard operation.spaceID == workspace.spaceID else { throw TorahAssociationRepositoryError.targetOutsideSpace }
        let result = try await repository.append(operation, authorize: authorize)
        guard !result.conflicted else { throw TorahAssociationRepositoryError.writeConflict(operation.logicalKey) }
    }

    public func watch(session: AnyStreamSession, limit: Int) async throws -> AsyncThrowingStream<AnyTorahLiveSnapshot, Error> {
        try await repository.watch(session: session, limit: limit)
    }
}
