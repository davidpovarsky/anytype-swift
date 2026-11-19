import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

private func archiveProof(_ operations: [AnyTorahOperation], reachable: Set<String> = [])
    throws -> AnyGuardedTorahObjectSnapshot {
    let records = operations.map { operation -> AnyJSON in
        var fields = operation.fields.object!
        fields["id"] = .string(operation.recordID)
        fields["creator"] = .string(operation.authorID)
        fields["nativeChangeId"] = .string("change")
        fields["nativeACLHeadId"] = .string("acl")
        return .object(fields)
    }
    return try .init(response: .object([
        "contract": .string("pinkha-torah-native-v1"), "scope": .string("object-logical-closure"),
        "version": .integer(1), "spaceId": .string("space"), "rootObjectId": .string("root"),
        "dataset": .string("pinkha_torah_claims_v1"), "targetObjectId": .string("object"),
        "complete": .bool(true), "limit": .integer(10_000), "records": .array(records),
        "reachableClaimBlockIds": .array(reachable.sorted().map(AnyJSON.string)),
        "readiness": .object(["version": .integer(1), "state": .string("ready-local-snapshot"),
                              "generation": .string(String(repeating: "a", count: 64))])
    ]), expectedSpaceID: "space", expectedRootObjectID: "root", expectedObjectID: "object")
}

private actor ArchiveStoreFixture: AnyTorahObjectOperationReading {
    nonisolated let workspace: AnyTorahWorkspace
    var operations: [AnyTorahOperation]
    var objectReads = 0
    var globalReads = 0
    var writes = 0
    let nativeExport: Bool
    init(_ operations: [AnyTorahOperation], workspace: AnyTorahWorkspace, nativeExport: Bool = false) {
        self.operations = operations; self.workspace = workspace; self.nativeExport = nativeExport
    }
    func snapshot() throws -> AnyTorahProjection {
        globalReads += 1
        if nativeExport { throw AnyEngineError.readLimit }
        return try .init(claims: operations.map { try .init(operation: $0, creator: $0.authorID) })
    }
    func objectSnapshot(objectID: String, limit: Int) throws -> AnyGuardedTorahObjectSnapshot {
        objectReads += 1
        return try archiveProof(operations)
    }
    func append(_ operation: AnyTorahOperation,
                authorize: @escaping @Sendable () async throws -> Void) async throws {
        try await authorize()
        operations.append(operation); writes += 1
    }
    func counts() -> (object: Int, global: Int, writes: Int) { (objectReads, globalReads, writes) }
}
private actor ArchiveAccessFixture: AnyTorahTargetAccess {
    nonisolated let workspace: AnyTorahWorkspace
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) throws {}
}
private actor ArchiveAuthorization {
    var calls = 0
    func authorize() throws {
        calls += 1
        if calls == 2 { throw TorahAssociationRepositoryError.permissionDenied }
    }
}

@Suite("Canonical native archive transport")
struct AnyTorahArchiveTests {
    private let destination = try! AnyTorahWorkspace(accountID: "new-account", spaceID: "new-space")
    private func operation(_ id: String, itemID: String = "item", objectID: String = "object",
                           blockID: String = "", kind: AnyTorahOperation.Kind = .add,
                           observed: [String] = [], rawPayload: Data? = nil) throws -> AnyTorahOperation {
        let target: TorahAssociationTarget = blockID.isEmpty
            ? .object(objectId: objectID) : .block(objectId: objectID, blockId: blockID)
        let item = TorahAssociationItem(id: itemID, kind: .ref,
            role: blockID.isEmpty ? .context : .sourceQuote, providerID: "sefaria",
            externalID: "Genesis.1.1", canonicalKey: "Genesis 1:1", labelHe: "Genesis",
            unknownFields: ["futureItem": .string("retained")])
        let payload = try rawPayload ?? TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(records: [
            .init(location: .init(spaceId: "space", target: target), item: item,
                  unknownFields: ["futureRecord": .bool(true)])
        ], unknownFields: ["futureEnvelope": .object(["retained": .string("exact")])]))
        return try .init(operationID: String(repeating: id, count: 32), spaceID: "space", authorID: "account",
            kind: kind, targetObjectID: objectID, targetBlockID: blockID,
            providerID: kind == .remove ? "" : "sefaria", canonicalRef: kind == .remove ? "" : "Genesis 1:1",
            payload: kind == .remove ? Data() : payload, observed: observed)
    }
    private func plan(_ archive: AnyTorahArchive, blocks: [String: String] = [:]) throws -> AnyTorahMigrationPlan {
        try archive.prepareImport(workspace: destination, targetObjectID: "new-object",
            blockIDMap: blocks, migrationKey: "reviewed-import")
    }

    @Test func opaquePayloadBytesAndUnknownNumbersRoundTripWithoutLocalFields() throws {
        let base = try operation("1")
        let raw = Data((" { \"futureLarge\":9007199254740993, " +
                        String(decoding: base.payload, as: UTF8.self).dropFirst()).utf8)
        let op = try operation("1", rawPayload: raw)
        let archive = try AnyTorahArchive(snapshot: archiveProof([op]))
        let bytes = try archive.encodedData()
        let reopened = try AnyTorahArchive.decode(bytes)
        #expect(reopened.canonicalPayloads == [raw])
        #expect(try reopened.encodedData() == bytes)
        let text = String(decoding: bytes, as: UTF8.self)
        #expect(!text.contains("sourceIndex") && !text.contains("credential") && !text.contains("localCache"))
        // Export remains lossless, while typed import refuses numeric loss.
        #expect(throws: (any Error).self) { try plan(reopened) }
        #expect(reopened.canonicalPayloads == [raw])
    }

    @Test func explicitMappingPreservesEachEnvelopeAndOriginalArchiveForAudit() throws {
        let values = try [operation("1", itemID: "doc"), operation("2", itemID: "quote", blockID: "block")]
        let archive = try AnyTorahArchive(snapshot: archiveProof(values, reachable: ["block"]))
        let mapped = try plan(archive, blocks: ["block": "new-block"])
        #expect(mapped.operations.count == 2)
        #expect(mapped.sourceBytes == (try archive.encodedData()))
        #expect(mapped.sourceSHA256 == AnyContentDigest.sha256(mapped.sourceBytes))
        #expect(Set(mapped.operations.map(\.targetBlockID)) == ["", "new-block"])
        #expect(mapped.operations.allSatisfy { $0.spaceID == "new-space" && $0.authorID == "new-account" })
        for op in mapped.operations {
            let location = TorahAssociationLocation(spaceId: "new-space", target: op.targetBlockID.isEmpty
                ? .object(objectId: "new-object") : .block(objectId: "new-object", blockId: "new-block"))
            let payload = try TorahAssociationPayloadCodec().decodeCanonicalDocument(op.payload, legacyLocation: location)
            #expect(payload.unknownFields["futureEnvelope"] != nil)
            #expect(payload.records.first?.unknownFields["futureRecord"] == .bool(true))
            #expect(payload.records.first?.item.unknownFields["futureItem"] == .string("retained"))
        }
        #expect(throws: (any Error).self) { try plan(archive) }
    }

    @Test func removedHistoryIsArchivedWithoutResurrectingItsAssociation() throws {
        let add = try operation("1")
        let remove = try operation("2", kind: .remove, observed: [add.claimID])
        let archive = try AnyTorahArchive(snapshot: archiveProof([add, remove]))
        #expect(archive.claimCount == 2 && archive.liveClaimCount == 0)
        #expect(archive.canonicalPayloads.contains(add.payload))
        #expect(try plan(archive).operations.isEmpty)
    }

    @Test func foreignCollisionRemainsAuditableButCannotBeImportedAsSuccess() throws {
        let seed = try operation("1")
        let witness = try operation("1", itemID: "foreign", objectID: "foreign")
        let archive = try AnyTorahArchive(snapshot: archiveProof([seed, witness]))
        #expect(archive.claimCount == 2 && archive.conflictCount == 1)
        #expect(try AnyTorahArchive.decode(archive.encodedData()).claimCount == 2)
        #expect(throws: AnyTorahArchiveError.incompleteOrConflicted) { try plan(archive) }
    }

    @Test func missingObservedHistoryCannotProduceACompleteImportPlan() throws {
        let missing = try operation("1")
        let replacement = try operation("2", kind: .replace, observed: [missing.claimID])
        let archive = try AnyTorahArchive(snapshot: archiveProof([replacement]))
        #expect(archive.pendingObservedCount == 1)
        #expect(throws: AnyTorahArchiveError.incompleteOrConflicted) { try plan(archive) }
    }

    @Test func unreachableBlockHistoryIsPreservedAndRequiresExplicitResolution() throws {
        let archive = try AnyTorahArchive(snapshot: archiveProof([operation("1", blockID: "orphan")]))
        #expect(archive.claimCount == 1)
        #expect(throws: AnyTorahArchiveError.unreachableBlock("orphan")) {
            try plan(archive, blocks: ["orphan": "new-block"])
        }
    }

    @Test func unknownEnvelopeFieldsAndDuplicateKeysAreRejectedWithoutDroppingBytes() throws {
        let bytes = try AnyTorahArchive(snapshot: archiveProof([operation("1")])).encodedData()
        let original = String(decoding: bytes, as: UTF8.self)
        for prefix in ["{\"futureArchive\":true,", "{\"format\":\"pinkha-canonical-archive-v1\","] {
            let changed = Data((prefix + original.dropFirst()).utf8)
            #expect(throws: (any Error).self) { try AnyTorahArchive.decode(changed) }
        }
        #expect(try AnyTorahArchive.decode(bytes).encodedData() == bytes)
    }

    @Test func duplicateLiveAssociationIdentityAcrossPayloadsFailsBeforeAnyWrites() throws {
        let archive = try AnyTorahArchive(snapshot: archiveProof([
            operation("1", itemID: "first"), operation("2", itemID: "second")
        ]))
        #expect(throws: (any Error).self) { try plan(archive) }
    }

    @Test func wholeImportPreflightAndRetryDoNotDuplicateAcceptedClaims() async throws {
        let archive = try AnyTorahArchive(snapshot: archiveProof([
            operation("1", itemID: "doc"), operation("2", itemID: "block-item", blockID: "block")
        ], reachable: ["block"]))
        let prepared = try plan(archive, blocks: ["block": "new-block"])
        let store = ArchiveStoreFixture([], workspace: destination)
        let executor = try AnyTorahMigrationExecutor(workspace: destination, store: store,
                                                     access: ArchiveAccessFixture(destination))
        let first = try await executor.execute(prepared)
        let second = try await executor.execute(prepared)
        #expect(first.status == .complete && second.status == .complete)
        #expect(first.acknowledgedClaimIDs.count == 2 && second.alreadyPresentClaimIDs.count == 2)
        #expect(await store.counts().writes == 2)
    }

    private func noteOperation(metadataID: String = "old-note") throws -> AnyTorahOperation {
        let item = TorahAssociationItem(id: "internal-note", kind: .ref, role: .context,
            providerID: "anytype", externalID: "old-note", canonicalKey: "anytype-note:old-note",
            labelHe: "Internal note", customMetadata: ["anytypeNoteObjectId": metadataID])
        let payload = try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(records: [
            .init(location: .init(spaceId: "space", target: .object(objectId: "object")), item: item)
        ]))
        return try .init(operationID: String(repeating: "a", count: 32), spaceID: "space",
            authorID: "account", kind: .add, targetObjectID: "object",
            providerID: item.providerID, canonicalRef: item.canonicalKey, payload: payload)
    }

    @Test func reviewExposesExactBlockAndInternalNoteMappings() throws {
        let archive = try AnyTorahArchive(snapshot: archiveProof([
            noteOperation(), operation("2", blockID: "source-block")
        ], reachable: ["source-block"]))
        #expect(archive.sourceBlockIDs == ["source-block"])
        #expect(try archive.requiredReferencedObjectIDs() == ["old-note"])
        let mapped = try archive.prepareImport(workspace: destination, targetObjectID: "new-object",
            blockIDMap: ["source-block": "target-block"], objectIDMap: ["old-note": "new-note"],
            migrationKey: "reviewed-import")
        #expect(mapped.referencedObjectIDs == ["new-note"])
        #expect(mapped.objectIDMap["old-note"] == "new-note")
    }

    @Test func contradictoryInternalNoteMetadataIsNeverSuggestedAsAValidMapping() throws {
        let archive = try AnyTorahArchive(snapshot: archiveProof([noteOperation(metadataID: "different")]))
        #expect(throws: AnyTorahMigrationError.malformedInternalNoteLink(itemID: "internal-note")) {
            try archive.requiredReferencedObjectIDs()
        }
        #expect(throws: (any Error).self) { try plan(archive) }
    }

    @Test func payloadLocationCannotDisagreeWithItsArchivedOperation() throws {
        let blockPayload = try operation("1", blockID: "hidden-block").payload
        let archivedAsObject = try operation("2", rawPayload: blockPayload)
        let archive = try AnyTorahArchive(snapshot: archiveProof([archivedAsObject]))
        // The raw archive remains recoverable, but a user-supplied mismatched
        // envelope must not smuggle a different target through the mapping UI.
        #expect(try AnyTorahArchive.decode(archive.encodedData()).claimCount == 1)
        #expect(throws: TorahAssociationRepositoryError.malformedCanonicalData) {
            try archive.requiredReferencedObjectIDs()
        }
        #expect(throws: (any Error).self) { try plan(archive, blocks: ["hidden-block": "mapped"]) }
    }

    @Test func scopedReadDoesNotExportLateDataAfterOwnerRevocation() async throws {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let store = ArchiveStoreFixture([try operation("1")], workspace: workspace, nativeExport: true)
        let service = try AnyTorahArchiveService(workspace: workspace, store: store,
                                                access: ArchiveAccessFixture(workspace))
        let authorization = ArchiveAuthorization()
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await service.export(objectID: "object") { try await authorization.authorize() }
        }
        let counts = await store.counts()
        #expect(counts.object == 1 && counts.global == 0 && counts.writes == 0)
    }
}
