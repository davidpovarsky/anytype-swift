import Foundation
import PinkhaKit
import PinkhaAnyEngine

/// A reviewable non-destructive import of ONE canonical association snapshot.
/// A validated native archive can supply multiple canonical payloads.
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
    public let objectIDMap: [String: String]
    public let blockIDMap: [String: String]
    public let referencedObjectIDs: [String]

    public init(sourceBytes: Data, sourceSpaceID: String, sourceObjectID: String,
                workspace: AnyTorahWorkspace, targetObjectID: String,
                blockIDMap: [String: String], objectIDMap: [String: String] = [:],
                migrationKey: String) throws {
        guard !sourceSpaceID.isEmpty, !sourceObjectID.isEmpty, !targetObjectID.isEmpty,
              !migrationKey.isEmpty, migrationKey.utf8.count <= 256,
              blockIDMap.allSatisfy({ !$0.key.isEmpty && !$0.value.isEmpty }),
              Set(blockIDMap.values).count == blockIDMap.count else {
            throw AnyEngineError.invalidIdentity("migration mapping")
        }
        var completeObjectMap = objectIDMap
        guard completeObjectMap[sourceObjectID] == nil || completeObjectMap[sourceObjectID] == targetObjectID else {
            throw AnyEngineError.invalidIdentity("source object mapping disagrees with destination")
        }
        completeObjectMap[sourceObjectID] = targetObjectID
        guard completeObjectMap.allSatisfy({ !$0.key.isEmpty && !$0.value.isEmpty }),
              Set(completeObjectMap.values).count == completeObjectMap.count else {
            throw AnyEngineError.invalidIdentity("referenced object mapping")
        }
        let codec = TorahAssociationPayloadCodec()
        let sourceLocation = TorahAssociationLocation(
            spaceId: sourceSpaceID, target: .object(objectId: sourceObjectID))
        let payload = try codec.decodeCanonicalDocument(sourceBytes, legacyLocation: sourceLocation)
        try AnyTorahSourceJSONGuard.validateCanonicalPayload(sourceBytes, decoded: payload)
        var identities = Set<String>()
        var semanticIdentities = Set<TorahAssociationIdentity>()
        var operations: [AnyTorahOperation] = []
        var referencedObjects = Set<String>()
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
            let remapped = try Self.remapInternalNote(source.item, objectIDMap: completeObjectMap)
            let mappedItem = try AnyTorahSemanticAnchorMigration.remapping(remapped.item,
                source: source.location, destination: location)
            if let referenced = remapped.referencedObjectID { referencedObjects.insert(referenced) }
            guard semanticIdentities.insert(TorahAssociationIdentity(item: mappedItem, location: location)).inserted else {
                throw TorahAssociationRepositoryError.writeConflict("Source contains duplicate association identities")
            }
            let mapped = TorahStoredAssociationRecord(
                location: location, item: mappedItem, unknownFields: source.unknownFields)
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
                providerID: mappedItem.providerID,
                canonicalRef: mappedItem.canonicalKey.isEmpty ? mappedItem.externalID : mappedItem.canonicalKey,
                payload: encoded))
        }
        let sourceHash = AnyContentDigest.sha256(sourceBytes)
        let mapping = blockIDMap.keys.sorted().map { Self.key(["block", $0, blockIDMap[$0] ?? ""]) }
            + completeObjectMap.keys.sorted().map { Self.key(["object", $0, completeObjectMap[$0] ?? ""]) }
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
        self.objectIDMap = completeObjectMap
        self.blockIDMap = blockIDMap
        self.referencedObjectIDs = referencedObjects.sorted()
    }


    /// Combines independently validated live canonical payloads from an archive.
    /// The single executor still preflights every operation before any append.
    init(archiveComponents components: [Self], sourceBytes: Data, migrationKey: String) throws {
        guard let first = components.first, !sourceBytes.isEmpty,
              components.allSatisfy({
                  $0.workspace == first.workspace && $0.sourceSpaceID == first.sourceSpaceID &&
                  $0.sourceObjectID == first.sourceObjectID && $0.targetObjectID == first.targetObjectID &&
                  $0.objectIDMap == first.objectIDMap && $0.blockIDMap == first.blockIDMap
              }) else { throw AnyEngineError.invalidIdentity("mixed canonical archive mapping") }
        let operations = components.flatMap(\.operations)
        guard operations.count <= 10_000,
              Set(operations.map(\.claimID)).count == operations.count,
              Set(operations.map(\.logicalKey)).count == operations.count else {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }
        var stable = Set<String>()
        var semantic = Set<TorahAssociationIdentity>()
        for operation in operations {
            let target: TorahAssociationTarget = operation.targetBlockID.isEmpty
                ? .object(objectId: operation.targetObjectID)
                : .block(objectId: operation.targetObjectID, blockId: operation.targetBlockID)
            let location = TorahAssociationLocation(spaceId: operation.spaceID, target: target)
            let payload = try TorahAssociationPayloadCodec().decodeCanonicalDocument(
                operation.payload, legacyLocation: location)
            guard payload.records.count == 1, let record = payload.records.first,
                  record.location == location,
                  stable.insert(Self.key([operation.targetObjectID, operation.targetBlockID, record.item.id])).inserted,
                  semantic.insert(.init(item: record.item, location: location)).inserted else {
                throw TorahAssociationRepositoryError.writeConflict("Archive repeats a canonical association identity")
            }
        }
        workspace = first.workspace
        sourceSpaceID = first.sourceSpaceID
        sourceObjectID = first.sourceObjectID
        targetObjectID = first.targetObjectID
        self.sourceBytes = sourceBytes
        sourceSHA256 = AnyContentDigest.sha256(sourceBytes)
        self.operations = operations
        objectIDMap = first.objectIDMap
        blockIDMap = first.blockIDMap
        referencedObjectIDs = Array(Set(components.flatMap(\.referencedObjectIDs))).sorted()
        planID = AnyContentDigest.sha256(Data(Self.key([
            "pinkha-any-canonical-archive-import-v1", migrationKey, sourceSHA256
        ] + components.map(\.planID)).utf8))
    }


    static func remapInternalNote(
        _ source: TorahAssociationItem, objectIDMap: [String: String]
    ) throws -> (item: TorahAssociationItem, referencedObjectID: String?) {
        let prefix = "anytype-note:"
        let metadataID = source.customMetadata?["anytypeNoteObjectId"]
        guard source.canonicalKey.hasPrefix(prefix) || metadataID != nil else {
            return (source, nil)
        }
        let originalID = String(source.canonicalKey.dropFirst(prefix.count))
        guard source.canonicalKey.hasPrefix(prefix), !originalID.isEmpty,
              source.kind == .ref, source.role == .context,
              source.externalID == originalID, metadataID == originalID else {
            throw AnyTorahMigrationError.malformedInternalNoteLink(itemID: source.id)
        }
        guard let destination = objectIDMap[originalID] else {
            throw AnyTorahMigrationError.unmappedReferencedObject(originalID)
        }
        var item = source
        item.externalID = destination
        item.canonicalKey = prefix + destination
        item.customMetadata?["anytypeNoteObjectId"] = destination
        return (item, destination)
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
        var semanticTargets: [String: PinkhaSemanticTextAnchor] = [:]
        for operation in plan.operations {
            let source = try record(operation)
            if let semantic = try TorahSemanticAnchorAssociation.decoding(source.item, location: source.location) {
                try await validateSemanticTarget(semantic.anchor)
                semanticTargets[operation.claimID] = semantic.anchor
            }
        }
        for referencedID in plan.referencedObjectIDs {
            try await access.validate(.object(objectId: referencedID), intent: .read)
        }
        let before = try await store.snapshot()
        try rejectExistingIdentityConflicts(plan: plan, projection: before)
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
                let semanticTarget = semanticTargets[operation.claimID]
                try await store.append(operation) { [access] in
                    try Task.checkCancellation()
                    try await authorize()
                    try await access.validate(target, intent: .write)
                    if let semanticTarget { try await self.validateSemanticTarget(semanticTarget) }
                    for referencedID in plan.referencedObjectIDs {
                        try await access.validate(.object(objectId: referencedID), intent: .read)
                    }
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
            for anchor in semanticTargets.values { try await validateSemanticTarget(anchor) }
            let after = try await store.snapshot()
            let unresolved = try finalUnresolved(plan: plan, projection: after)
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
    private func validateSemanticTarget(_ anchor: PinkhaSemanticTextAnchor) async throws {
        guard let semantic = access as? any AnyTorahSemanticTargetAccess else {
            throw AnyEngineError.invalidOperation("semantic migration requires a verified native document target")
        }
        try await semantic.validateSemanticTarget(anchor)
    }

    private struct StableRecordIdentity: Hashable {
        let location: TorahAssociationLocation
        let itemID: String
    }

    /// A migration may not silently merge into an existing association identity.
    /// Reusing the exact imported claim is the only automatic idempotent case.
    private func rejectExistingIdentityConflicts(
        plan: AnyTorahMigrationPlan, projection: AnyTorahProjection
    ) throws {
        var semantic: [TorahAssociationIdentity: String] = [:]
        var stable: [StableRecordIdentity: String] = [:]
        var targets = Set<TorahAssociationLocation>()
        for operation in plan.operations {
            let incoming = try record(operation)
            targets.insert(incoming.location)
            semantic[TorahAssociationIdentity(item: incoming.item, location: incoming.location)] = operation.claimID
            stable[.init(location: incoming.location, itemID: incoming.item.id)] = operation.claimID
        }
        func location(_ operation: AnyTorahOperation) -> TorahAssociationLocation {
            .init(spaceId: operation.spaceID, target: operation.targetBlockID.isEmpty
                ? .object(objectId: operation.targetObjectID)
                : .block(objectId: operation.targetObjectID, blockId: operation.targetBlockID))
        }
        for claim in projection.live where targets.contains(location(claim.operation)) {
            let existing = try record(claim.operation)
            let semanticID = semantic[TorahAssociationIdentity(item: existing.item, location: existing.location)]
            let stableID = stable[.init(location: existing.location, itemID: existing.item.id)]
            guard [semanticID, stableID].compactMap({ $0 }).allSatisfy({ $0 == claim.id }) else {
                throw TorahAssociationRepositoryError.writeConflict(
                    "Migration target already contains this association identity")
            }
        }
        for group in projection.conflicts.values
            where group.contains(where: { targets.contains(location($0.operation)) }) {
            throw TorahAssociationRepositoryError.writeConflict(
                "Migration target contains quarantined operation variants")
        }
    }

    private func finalUnresolved(
        plan: AnyTorahMigrationPlan, projection: AnyTorahProjection
    ) throws -> [String] {
        let groups = Dictionary(grouping: projection.all, by: { $0.operation.logicalKey })
        let live = Set(projection.live.map(\.id))
        var unresolved = Set(plan.operations.compactMap { operation -> String? in
            guard let group = groups[operation.logicalKey], group.count == 1,
                  group[0].operation == operation, live.contains(operation.claimID) else {
                return operation.claimID
            }
            return nil
        })
        do {
            try rejectExistingIdentityConflicts(plan: plan, projection: projection)
        } catch {
            // The receipt is intentionally conservative. It never certifies a
            // partially ambiguous target as a complete visible import.
            unresolved.formUnion(plan.operations.map(\.claimID))
        }
        return unresolved.sorted()
    }

    private func record(_ operation: AnyTorahOperation) throws -> TorahStoredAssociationRecord {
        let target: TorahAssociationTarget = operation.targetBlockID.isEmpty
            ? .object(objectId: operation.targetObjectID)
            : .block(objectId: operation.targetObjectID, blockId: operation.targetBlockID)
        let location = TorahAssociationLocation(spaceId: workspace.spaceID, target: target)
        let payload = try TorahAssociationPayloadCodec().decodeCanonicalDocument(
            operation.payload, legacyLocation: location)
        guard operation.spaceID == workspace.spaceID,
              payload.records.count == 1, let record = payload.records.first,
              record.location == location, !record.item.id.isEmpty,
              record.item.providerID == operation.providerID,
              (record.item.canonicalKey.isEmpty ? record.item.externalID : record.item.canonicalKey)
                == operation.canonicalRef else {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }
        return record
    }


}
