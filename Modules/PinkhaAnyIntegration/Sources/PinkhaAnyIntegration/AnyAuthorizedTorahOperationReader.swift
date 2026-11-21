import Foundation
import PinkhaKit
import PinkhaAnyEngine

/// The engine owner supplies its real stream/session lifetime. Invalidation
/// cancels an in-flight read and prevents an old-account response being released.
/// This adapter does not install data or fall back to a workspace scan.
/// After awaiting, a UI owner must compare the returned scope with its current
/// engine/account/Space/generation on the publishing actor before changing UI.
public struct AnyAuthorizedTorahOperationReader: TorahAuthorizedOperationReading, Sendable {
    public let scope: TorahOperationReadScope
    private let session: AnyStreamSession
    private let load: @Sendable (String) async throws -> AnyGuardedTorahOperationReadSnapshot

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                session: AnyStreamSession) async throws {
        guard client.expectedAccountID.utf8.elementsEqual(workspace.accountID.utf8) else {
            throw TorahOperationReadError.accountChanged
        }
        let repository = try AnyGuardedTorahClaimsRepository(client: client, spaceID: workspace.spaceID)
        try await self.init(workspace: workspace, session: session,
                      load: { try await repository.readOperation(operationID: $0) })
    }

    // Internal dependency seam for account-lifetime tests. Public construction
    // always selects the capability-negotiated native repository above.
    init(workspace: AnyTorahWorkspace, session: AnyStreamSession,
         load: @escaping @Sendable (String) async throws -> AnyGuardedTorahOperationReadSnapshot) async throws {
        let generation = await session.generation
        self.scope = try .init(engine: .any, accountID: workspace.accountID,
                               spaceID: workspace.spaceID, sessionGeneration: generation)
        self.session = session; self.load = load
    }

    public func readOperation(operationID: String) async throws -> TorahAuthorizedOperationSnapshot {
        try TorahAuthorizedOperationReadContract.validateOperationID(operationID)
        do {
            try Task.checkCancellation()
            try await session.requireActive(generation: scope.sessionGeneration)
            let task = Task {
                try Task.checkCancellation()
                let native = try await load(operationID)
                try Task.checkCancellation()
                try await session.requireActive(generation: scope.sessionGeneration)
                return try map(native, expectedOperationID: operationID)
            }
            let registration: UUID
            do {
                registration = try await session.register(generation: scope.sessionGeneration) { task.cancel() }
            } catch {
                task.cancel()
                throw error
            }
            do {
                let result = try await withTaskCancellationHandler { try await task.value }
                    onCancel: { task.cancel() }
                await session.unregister(registration)
                try Task.checkCancellation()
                try await session.requireActive(generation: scope.sessionGeneration)
                return result
            } catch {
                await session.unregister(registration)
                throw error
            }
        } catch {
            if error is CancellationError { throw error }
            if let shared = error as? TorahOperationReadError { throw shared }
            if error as? AnyLiveQueryError == .staleGeneration { throw TorahOperationReadError.accountChanged }
            guard let native = error as? AnyEngineError else { throw TorahOperationReadError.nativeFailure }
            switch native {
            case .accountChanged: throw TorahOperationReadError.accountChanged
            case .readLimit: throw TorahOperationReadError.readLimit
            case .incompatibleSchema: throw TorahOperationReadError.unsupportedContract
            case .invalidClaim: throw TorahOperationReadError.malformedNativeResponse
            case .http(let status, let code):
                if status == 403 { throw TorahOperationReadError.permissionDenied }
                switch code {
                case "pinkha.history_unavailable", "bundle.not_found", "bundle.not_ready":
                    throw TorahOperationReadError.historyUnavailable
                case "pinkha.target_state_unavailable": throw TorahOperationReadError.targetStateUnavailable
                case "pinkha.snapshot_changed": throw TorahOperationReadError.snapshotChanged
                case "pinkha.projection_behind": throw TorahOperationReadError.projectionBehind
                case "pinkha.read_limit": throw TorahOperationReadError.readLimit
                default: throw TorahOperationReadError.nativeFailure
                }
            default: throw TorahOperationReadError.nativeFailure
            }
        }
    }

    private func map(_ native: AnyGuardedTorahOperationReadSnapshot,
                     expectedOperationID: String) throws -> TorahAuthorizedOperationSnapshot {
        guard native.spaceID.utf8.elementsEqual(scope.spaceID.utf8),
              native.operationID == expectedOperationID else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        let variants = try native.variants.map { variant -> TorahAuthorizedOperationVariant in
            let operation = variant.claim.operation
            guard let reachability = TorahOperationTargetReachability(rawValue: variant.reachability.rawValue) else {
                throw TorahOperationReadError.malformedNativeResponse
            }
            return try .init(claimID: variant.claim.id, operationID: operation.operationID,
                spaceID: operation.spaceID, authorID: operation.authorID,
                target: operation.targetBlockID.isEmpty
                    ? .object(objectId: operation.targetObjectID)
                    : .block(objectId: operation.targetObjectID, blockId: operation.targetBlockID),
                canonicalBytes: variant.canonicalBytes,
                provenance: [.init(creator: variant.provenance.creator,
                    nativeChangeID: variant.provenance.changeID, nativeACLHeadID: variant.provenance.aclHeadID)],
                reachability: reachability)
        }
        return try .init(scope: scope, operationID: expectedOperationID,
            outcome: native.absentInVerifiedLocalSnapshot ? .absentInVerifiedLocalSnapshot : .found,
            nativeSnapshotToken: native.readinessGeneration, complete: true, variants: variants)
    }
}
