import Foundation
import PinkhaKit
import PinkhaAnyEngine

/// This is explicitly an object closure, including all global collision
/// witnesses for that object's logical keys. It does not replace snapshot(),
/// whose complete-workspace contract remains necessary for migration/admin work.
public protocol AnyTorahObjectOperationReading: AnyTorahOperationStore {
    func objectSnapshot(objectID: String, limit: Int) async throws -> AnyGuardedTorahObjectSnapshot
}

public protocol AnyTorahObjectOperationObserving: AnyTorahObjectOperationReading {
    func watchObject(objectID: String, session: AnyStreamSession, limit: Int) async throws
        -> AsyncThrowingStream<AnyGuardedTorahObjectLiveSnapshot, Error>
}

public struct AnyTorahObjectAssociationSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let objectID: String
    public let records: [TorahStoredAssociationRecord]
    public let conflicts: [AnyTorahAssociationConflict]
    public let reachableClaimBlockIDs: Set<String>
    public let nativeGeneration: String
}

public struct AnyTorahObjectAssociationLiveSnapshot: Sendable {
    public let generation: UUID
    public let initial: Bool
    public let snapshot: AnyTorahObjectAssociationSnapshot
}
