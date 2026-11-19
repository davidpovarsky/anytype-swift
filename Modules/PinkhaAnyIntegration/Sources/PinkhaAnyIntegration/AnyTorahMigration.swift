import Foundation
import PinkhaKit
import PinkhaAnyEngine

/// A reviewable non-destructive import of ONE canonical association snapshot.
/// This is not a complete Heart database/editor/file migration.
public struct AnyTorahMigrationPlan: Sendable {
    public let workspace: AnyTorahWorkspace
    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let targetObjectID: String
    public let sourceBytes: Data
    public let sourceSHA256: String
    public let planID: String
    public let operations: [AnyTorahOperation]

    public init(sourceBytes: Data, sourceSpaceID: String, sourceObjectID: String,
                workspace: AnyTorahWorkspace, targetObjectID: String,
                blockIDMap: [String: String], migrationKey: String) throws {
        guard !sourceSpaceID.isEmpty, !sourceObjectID.isEmpty, !targetObjectID.isEmpty,
              !migrationKey.isEmpty, migrationKey.utf8.count <= 256,
              blockIDMap.allSatisfy({ !$0.key.isEmpty && !$0.value.isEmpty }),
              Set(blockIDMap.values).count == blockIDMap.count else {
            throw AnyEngineError.invalidIdentity("migration mapping")
        }
        let codec = TorahAssociationPayloadCodec()
        let sourceLocation = TorahAssociationLocation(
            spaceId: sourceSpaceID, target: .object(objectId: sourceObjectID))
        let payload = try codec.decodeCanonicalDocument(sourceBytes, legacyLocation: sourceLocation)
        var identities = Set<String>()
        var operations: [AnyTorahOperation] = []
        for source in payload.records {
            guard source.spaceId == sourceSpaceID, source.objectId == sourceObjectID,
                  !source.item.id.isEmpty, !source.item.providerID.isEmpty,
                  !source.item.canonicalKey.isEmpty || !source.item.externalID.isEmpty else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
            let key = Self.key([source.spaceId, source.objectId, source.blockId ?? "", source.item.id])
            guard identities.insert(key).inserted else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
            let target: TorahAssociationTarget
            if let oldBlock = source.blockId {
                guard !oldBlock.isEmpty, let newBlock = blockIDMap[oldBlock] else {
                    throw AnyEngineError.invalidIdentity("unmapped source block")
                }
                target = .block(objectId: targetObjectID, blockId: newBlock)
            } else {
                target = .object(objectId: targetObjectID)
            }
            let location = TorahAssociationLocation(spaceId: workspace.spaceID, target: target)
            let mapped = TorahStoredAssociationRecord(
                location: location, item: source.item, unknownFields: source.unknownFields)
            let encoded = try codec.encodeCanonicalDocument(.init(
                records: [mapped], unknownFields: payload.unknownFields))
            // Operation identity excludes payload bytes: reusing this migration
            // identity with different source data is a collision, not an overwrite.
            let identity = Self.key([
                "pinkha-any-migration-v1", migrationKey, workspace.accountID, workspace.spaceID,
                source.spaceId, source.objectId, source.blockId ?? "", source.item.id,
                targetObjectID, target.blockId ?? ""
            ])
            let operationID = String(AnyContentDigest.sha256(Data(identity.utf8)).prefix(32))
            operations.append(try AnyTorahOperation(
                operationID: operationID, spaceID: workspace.spaceID, authorID: workspace.accountID,
                kind: .add, targetObjectID: targetObjectID, targetBlockID: target.blockId ?? "",
                providerID: source.item.providerID,
                canonicalRef: source.item.canonicalKey.isEmpty ? source.item.externalID : source.item.canonicalKey,
                payload: encoded))
        }
        let sourceHash = AnyContentDigest.sha256(sourceBytes)
        let mapping = blockIDMap.keys.sorted().map { Self.key([$0, blockIDMap[$0] ?? ""]) }
        let planMaterial = Self.key([
            "pinkha-any-migration-plan-v1", migrationKey, workspace.accountID, workspace.spaceID,
            sourceSpaceID, sourceObjectID, targetObjectID, sourceHash
        ] + mapping + operations.map(\.claimID).sorted())
        self.workspace = workspace
        self.sourceSpaceID = sourceSpaceID
        self.sourceObjectID = sourceObjectID
        self.targetObjectID = targetObjectID
        self.sourceBytes = sourceBytes
        self.sourceSHA256 = sourceHash
        self.planID = AnyContentDigest.sha256(Data(planMaterial.utf8))
        self.operations = operations
    }

    private static func key(_ parts: [String]) -> String {
        parts.map { "\($0.utf8.count):\($0)" }.joined(separator: "|")
    }
}

public struct AnyTorahMigrationReceipt: Sendable {
    public enum Status: String, Sendable { case complete, incomplete }
    public let planID: String
    public let status: Status
    public let alreadyPresentClaimIDs: [String]
    public let acknowledgedClaimIDs: [String]
    public let pendingClaimIDs: [String]
    public let failure: String?
}

/// Executes a validated plan against the same explicit new-engine workspace.
/// An incomplete result is a resumable receipt, never a success boolean.
public struct AnyTorahMigrationExecutor: Sendable {
    public let workspace: AnyTorahWorkspace
    private let store: any AnyTorahOperationStore
    private let access: any AnyTorahTargetAccess

    public init(workspace: AnyTorahWorkspace, store: any AnyTorahOperationStore,
                access: any AnyTorahTargetAccess) throws {
        guard store.workspace == workspace, access.workspace == workspace else {
            throw AnyEngineError.invalidIdentity("mixed migration workspace")
        }
        self.workspace = workspace
        self.store = store
        self.access = access
    }

    public func execute(_ plan: AnyTorahMigrationPlan,
                        authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyTorahMigrationReceipt {
        guard plan.workspace == workspace else { throw TorahAssociationRepositoryError.targetOutsideSpace }
        try Task.checkCancellation()
        try await authorize()
        // Validate every target and all known collisions before the first write.
        var targets = Set<TorahAssociationTarget>()
        for operation in plan.operations {
            let target: TorahAssociationTarget = operation.targetBlockID.isEmpty
                ? .object(objectId: operation.targetObjectID)
                : .block(objectId: operation.targetObjectID, blockId: operation.targetBlockID)
            targets.insert(target)
        }
        if targets.isEmpty { targets.insert(.object(objectId: plan.targetObjectID)) }
        for target in targets { try await access.validate(target, intent: .write) }
        let before = try await store.snapshot()
        let byLogical = Dictionary(grouping: before.all, by: { $0.operation.logicalKey })
        var previous: [String] = []
        for operation in plan.operations {
            if let existing = byLogical[operation.logicalKey] {
                guard existing.count == 1, existing[0].operation == operation else {
                    throw TorahAssociationRepositoryError.writeConflict("Migration identity already carries different data")
                }
                previous.append(operation.claimID)
            }
        }
        var acknowledged: [String] = []
        let priorIDs = Set(previous)
        let pending = plan.operations.filter { !priorIDs.contains($0.claimID) }
        for (index, operation) in pending.enumerated() {
            do {
                try Task.checkCancellation()
                let target: TorahAssociationTarget = operation.targetBlockID.isEmpty
                    ? .object(objectId: operation.targetObjectID)
                    : .block(objectId: operation.targetObjectID, blockId: operation.targetBlockID)
                try await store.append(operation) { [access] in
                    try Task.checkCancellation()
                    try await authorize()
                    try await access.validate(target, intent: .write)
                }
                acknowledged.append(operation.claimID)
            } catch {
                return .init(
                    planID: plan.planID, status: .incomplete,
                    alreadyPresentClaimIDs: previous, acknowledgedClaimIDs: acknowledged,
                    pendingClaimIDs: pending[index...].map(\.claimID),
                    failure: String(describing: error))
            }
        }
        // Sequential acknowledgements are not a global transaction. Re-read all
        // planned logical identities before issuing a complete snapshot receipt.
        do {
            let after = try await store.snapshot()
            let groups = Dictionary(grouping: after.all, by: { $0.operation.logicalKey })
            let unresolved = plan.operations.filter { operation in
                guard let group = groups[operation.logicalKey], group.count == 1 else { return true }
                return group[0].operation != operation
            }.map(\.claimID)
            guard unresolved.isEmpty else {
                return .init(planID: plan.planID, status: .incomplete,
                    alreadyPresentClaimIDs: previous, acknowledgedClaimIDs: acknowledged,
                    pendingClaimIDs: unresolved, failure: "Final readback missing or conflicted")
            }
        } catch {
            return .init(planID: plan.planID, status: .incomplete,
                alreadyPresentClaimIDs: previous, acknowledgedClaimIDs: acknowledged,
                pendingClaimIDs: plan.operations.map(\.claimID),
                failure: "Final readback unavailable")
        }
        return .init(planID: plan.planID, status: .complete,
                     alreadyPresentClaimIDs: previous, acknowledgedClaimIDs: acknowledged,
                     pendingClaimIDs: [], failure: nil)
    }
}
