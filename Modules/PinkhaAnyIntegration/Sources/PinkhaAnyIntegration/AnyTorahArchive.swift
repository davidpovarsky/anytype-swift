import Foundation
import PinkhaAnyEngine
import PinkhaKit

public enum AnyTorahArchiveError: Error, Equatable, Sendable {
    case invalidArchive
    case unsupportedFormat
    case noncanonicalEncoding
    case incompleteOrConflicted
    case unreachableBlock(String)
}

/// A portable copy of one complete native object claim closure. Payload bytes
/// remain opaque, including unknown JSON fields and exact numeric tokens.
/// Native provenance is retained for audit only: importing never grants its
/// author, ACL, signatures or original claim identities to the new workspace.
public struct AnyTorahArchive: Sendable {
    public static let format = "pinkha-canonical-archive-v1"
    public static let maximumBytes = 24 * 1024 * 1024
    private struct Entry: Codable, Equatable, Sendable {
        let operation: AnyTorahOperation
        let creator: String
        let nativeChangeID: String
        let nativeACLHeadID: String
    }
    private struct Envelope: Codable, Equatable, Sendable {
        let format: String
        let sourceSpaceID: String
        let sourceObjectID: String
        let sourceRootObjectID: String
        let sourceGeneration: String
        let reachableClaimBlockIDs: [String]
        let claims: [Entry]
    }
    private let envelope: Envelope
    private let projection: AnyTorahProjection

    public var sourceSpaceID: String { envelope.sourceSpaceID }
    public var sourceObjectID: String { envelope.sourceObjectID }
    public var sourceGeneration: String { envelope.sourceGeneration }
    public var claimCount: Int { envelope.claims.count }
    public var liveClaimCount: Int { projection.live.count }
    public var conflictCount: Int { projection.conflicts.count }
    public var pendingObservedCount: Int { projection.pendingObserved.count }
    public var sourceBlockIDs: [String] {
        Array(Set(projection.live.map { $0.operation.targetBlockID }.filter { !$0.isEmpty }))
            .sorted(by: Self.byteLess)
    }

    /// Known internal Note references need an explicit source-to-destination
    /// object map. The shared migration validator owns their identity grammar.
    public func requiredReferencedObjectIDs() throws -> [String] {
        var result = Set<String>()
        for record in try checkedLiveRecords() {
            do {
                _ = try AnyTorahMigrationPlan.remapInternalNote(record.item, objectIDMap: [:])
            } catch AnyTorahMigrationError.unmappedReferencedObject(let id) {
                result.insert(id)
            }
        }
        return result.sorted(by: Self.byteLess)
    }
    /// Includes historical payloads. Derived Source/Topic/Word fields, local
    /// caches, credentials and UI state are deliberately absent from the format.
    public var canonicalPayloads: [Data] { envelope.claims.map(\.operation.payload) }

    public init(snapshot: AnyGuardedTorahObjectSnapshot) throws {
        let entries = try snapshot.projection.all.map { claim -> Entry in
            guard let provenance = snapshot.provenance[claim.id],
                  provenance.creator == claim.creator else {
                throw AnyTorahArchiveError.invalidArchive
            }
            return .init(operation: claim.operation, creator: claim.creator,
                         nativeChangeID: provenance.changeID, nativeACLHeadID: provenance.aclHeadID)
        }
        try self.init(envelope: .init(
            format: Self.format, sourceSpaceID: snapshot.spaceID,
            sourceObjectID: snapshot.targetObjectID, sourceRootObjectID: snapshot.rootObjectID,
            sourceGeneration: snapshot.readinessGeneration,
            reachableClaimBlockIDs: snapshot.reachableClaimBlockIDs.sorted(by: Self.byteLess),
            claims: entries.sorted { $0.operation.claimID < $1.operation.claimID }))
        _ = try encodedData()
    }

    private init(envelope: Envelope) throws {
        guard envelope.format == Self.format else { throw AnyTorahArchiveError.unsupportedFormat }
        let bounded: (String) -> Bool = {
            !$0.isEmpty && $0.utf8.count <= 1024 && !$0.utf8.contains(0) && $0 != "." && $0 != ".."
        }
        guard [envelope.sourceSpaceID, envelope.sourceObjectID, envelope.sourceRootObjectID].allSatisfy(bounded),
              envelope.sourceGeneration.utf8.count == 64,
              envelope.sourceGeneration.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
              envelope.claims.count <= AnyGuardedTorahCapabilities.maximumRecords,
              envelope.reachableClaimBlockIDs.allSatisfy(bounded),
              envelope.reachableClaimBlockIDs == Array(Set(envelope.reachableClaimBlockIDs)).sorted(by: Self.byteLess)
        else { throw AnyTorahArchiveError.invalidArchive }
        let claims = try envelope.claims.map { entry -> AnyTorahClaim in
            guard entry.operation.spaceID == envelope.sourceSpaceID,
                  bounded(entry.nativeChangeID), bounded(entry.nativeACLHeadID) else {
                throw AnyTorahArchiveError.invalidArchive
            }
            return try .init(operation: entry.operation, creator: entry.creator)
        }
        let ids = claims.map(\.id)
        guard ids == ids.sorted(), Set(ids).count == ids.count else {
            throw AnyTorahArchiveError.invalidArchive
        }
        let seeds = claims.filter { $0.operation.targetObjectID == envelope.sourceObjectID }
        let seededKeys = Set(seeds.map { $0.operation.logicalKey })
        guard claims.allSatisfy({
            $0.operation.targetObjectID == envelope.sourceObjectID ||
            seededKeys.contains($0.operation.logicalKey)
        }), Set(envelope.reachableClaimBlockIDs).isSubset(of:
                Set(seeds.map { $0.operation.targetBlockID }.filter { !$0.isEmpty }))
        else { throw AnyTorahArchiveError.invalidArchive }
        let projection = try AnyTorahProjection(claims: claims)
        guard projection.live.allSatisfy({ $0.operation.targetObjectID == envelope.sourceObjectID }) else {
            throw AnyTorahArchiveError.invalidArchive
        }
        self.envelope = envelope
        self.projection = projection
    }

    public func encodedData() throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let bytes = try encoder.encode(envelope)
        guard bytes.count <= Self.maximumBytes else { throw AnyEngineError.readLimit }
        return bytes
    }

    /// Accept the exact versioned encoding emitted by encodedData(). Comparing
    /// the bytes also rejects duplicate keys and unknown envelope fields. Future
    /// data inside an operation payload remains unchanged because it is Data.
    public static func decode(_ bytes: Data) throws -> AnyTorahArchive {
        guard !bytes.isEmpty, bytes.count <= maximumBytes else { throw AnyEngineError.readLimit }
        let envelope = try JSONDecoder().decode(Envelope.self, from: bytes)
        let result = try AnyTorahArchive(envelope: envelope)
        guard try result.encodedData() == bytes else { throw AnyTorahArchiveError.noncanonicalEncoding }
        return result
    }

    public func prepareImport(
        workspace: AnyTorahWorkspace, targetObjectID: String,
        blockIDMap: [String: String], objectIDMap: [String: String] = [:],
        migrationKey: String
    ) throws -> AnyTorahMigrationPlan {
        guard !migrationKey.isEmpty, migrationKey.utf8.count <= 256 else {
            throw AnyEngineError.invalidIdentity("archive migration key")
        }
        guard projection.conflicts.isEmpty, projection.pendingObserved.isEmpty else {
            throw AnyTorahArchiveError.incompleteOrConflicted
        }
        _ = try checkedLiveRecords()
        let reachable = Set(envelope.reachableClaimBlockIDs)
        for claim in projection.live where !claim.operation.targetBlockID.isEmpty {
            guard reachable.contains(claim.operation.targetBlockID) else {
                throw AnyTorahArchiveError.unreachableBlock(claim.operation.targetBlockID)
            }
        }
        let sourceBytes = try encodedData()
        let digest = AnyContentDigest.sha256(sourceBytes)
        let components = try projection.live.map { claim in
            let key = AnyContentDigest.sha256(Data(Self.key([migrationKey, digest, claim.id]).utf8))
            return try AnyTorahMigrationPlan(
                sourceBytes: claim.operation.payload, sourceSpaceID: sourceSpaceID,
                sourceObjectID: sourceObjectID, workspace: workspace, targetObjectID: targetObjectID,
                blockIDMap: blockIDMap, objectIDMap: objectIDMap, migrationKey: key)
        }
        // An empty valid archive still needs the same destination/mapping
        // preflight before the executor can issue a complete receipt.
        let plans = components.isEmpty ? [try AnyTorahMigrationPlan(
            sourceBytes: Data("{\"version\":2,\"records\":[]}".utf8),
            sourceSpaceID: sourceSpaceID, sourceObjectID: sourceObjectID,
            workspace: workspace, targetObjectID: targetObjectID, blockIDMap: blockIDMap,
            objectIDMap: objectIDMap, migrationKey: migrationKey)] : components
        return try AnyTorahMigrationPlan(archiveComponents: plans, sourceBytes: sourceBytes,
                                         migrationKey: migrationKey)
    }

    private func checkedLiveRecords() throws -> [TorahStoredAssociationRecord] {
        guard projection.conflicts.isEmpty, projection.pendingObserved.isEmpty else {
            throw AnyTorahArchiveError.incompleteOrConflicted
        }
        return try projection.live.map { claim in
            let op = claim.operation
            let target: TorahAssociationTarget = op.targetBlockID.isEmpty
                ? .object(objectId: op.targetObjectID)
                : .block(objectId: op.targetObjectID, blockId: op.targetBlockID)
            let location = TorahAssociationLocation(spaceId: sourceSpaceID, target: target)
            let payload = try TorahAssociationPayloadCodec().decodeCanonicalDocument(op.payload, legacyLocation: location)
            try AnyTorahSourceJSONGuard.validateCanonicalPayload(op.payload, decoded: payload)
            guard payload.records.count == 1, let record = payload.records.first,
                  record.location == location, !record.item.id.isEmpty,
                  record.item.providerID == op.providerID,
                  (record.item.canonicalKey.isEmpty ? record.item.externalID : record.item.canonicalKey) == op.canonicalRef else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
            return record
        }
    }

    private static func byteLess(_ left: String, _ right: String) -> Bool {
        left.utf8.lexicographicallyPrecedes(right.utf8)
    }
    private static func key(_ parts: [String]) -> String {
        parts.map { "\($0.utf8.count):\($0)" }.joined(separator: "|")
    }
}

/// Export is read-only and requires a complete, authoritative object closure.
/// The caller supplies its existing account/UI authorization lease; a revoked
/// owner never receives bytes from a late response.
public struct AnyTorahArchiveService: Sendable {
    public let workspace: AnyTorahWorkspace
    private let store: any AnyTorahObjectOperationReading
    private let access: any AnyTorahTargetAccess

    public init(workspace: AnyTorahWorkspace, store: any AnyTorahObjectOperationReading,
                access: any AnyTorahTargetAccess) throws {
        guard store.workspace == workspace, access.workspace == workspace else {
            throw AnyEngineError.invalidIdentity("mixed archive workspace")
        }
        self.workspace = workspace; self.store = store; self.access = access
    }

    public func export(
        objectID: String,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyTorahArchive {
        try Task.checkCancellation()
        try await authorize()
        try await access.validate(.object(objectId: objectID), intent: .read)
        let snapshot = try await store.objectSnapshot(objectID: objectID, limit: 10_000)
        guard snapshot.spaceID == workspace.spaceID, snapshot.targetObjectID == objectID else {
            throw AnyTorahArchiveError.invalidArchive
        }
        let archive = try AnyTorahArchive(snapshot: snapshot)
        try await access.validate(.object(objectId: objectID), intent: .read)
        try Task.checkCancellation()
        try await authorize()
        return archive
    }
}
