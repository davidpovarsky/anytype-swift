import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

private actor MemoryStore: AnyTorahOperationStore {
    nonisolated let workspace: AnyTorahWorkspace
    private var claims: [AnyTorahClaim] = []
    private var remainingWrites: Int?
    private var afterNextAppend: AnyTorahOperation?
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func snapshot() throws -> AnyTorahProjection { try .init(claims: claims) }
    func append(_ op: AnyTorahOperation, authorize: @escaping @Sendable () async throws -> Void) async throws {
        try await authorize()
        if remainingWrites == 0 { throw AnyEngineError.unverifiedWrite }
        if let remainingWrites { self.remainingWrites = remainingWrites - 1 }
        if claims.contains(where: { $0.id == op.claimID }) { return }
        if claims.contains(where: { $0.operation.logicalKey == op.logicalKey }) {
            throw AnyEngineError.collision(op.logicalKey)
        }
        claims.append(try .init(operation: op, creator: workspace.accountID))
        if let injected = afterNextAppend {
            afterNextAppend = nil
            claims.append(try .init(operation: injected, creator: injected.authorID))
        }
    }
    func seed(_ op: AnyTorahOperation) throws {
        claims.append(try .init(operation: op, creator: op.authorID))
    }
    func limitWrites(_ limit: Int?) { remainingWrites = limit }
    func injectAfterNextAppend(_ operation: AnyTorahOperation) { afterNextAppend = operation }
    func count() -> Int { claims.count }
}

private actor TargetAccess: AnyTorahTargetAccess {
    nonisolated let workspace: AnyTorahWorkspace
    private var allowed = true
    private var validTargets: Set<TorahAssociationTarget>?
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func setAllowed(_ value: Bool) { allowed = value }
    func setTargets(_ targets: Set<TorahAssociationTarget>) { validTargets = targets }
    func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) throws {
        if !allowed { throw TorahAssociationRepositoryError.permissionDenied }
        if let validTargets, !validTargets.contains(target) {
            throw TorahAssociationRepositoryError.targetNotFound
        }
    }
}

@Suite("Actual PinkhaKit domain on the Any operation bridge")
struct AssociationBridgeTests: Sendable {
    private func fixture() throws -> (AnyTorahWorkspace, MemoryStore, TargetAccess, AnyTorahAssociationRepository) {
        let workspace = try AnyTorahWorkspace(accountID: "new-account", spaceID: "new-space")
        let store = MemoryStore(workspace)
        let access = TargetAccess(workspace)
        let repository = try AnyTorahAssociationRepository(workspace: workspace, store: store, access: access)
        return (workspace, store, access, repository)
    }
    private let target = TorahAssociationTarget.object(objectId: "new-document")
    private func item(_ id: String = "stable-id", source: String = "Genesis 1:1",
                      role: TorahAssociationRole = .context) -> TorahAssociationItem {
        .init(id: id, kind: .ref, role: role, providerID: "sefaria",
              externalID: "Genesis.1.1", canonicalKey: source, labelHe: "בראשית א:א",
              unknownFields: ["futureItem": .object(["value": .number(7)])])
    }

    @Test func originalContextPolicyDeduplicatesNFCAndPreservesStableID() async throws {
        let (_, store, _, repository) = try fixture()
        _ = try await repository.addAssociation(item("first", source: "e\u{301}"),
                                               target: target, spaceId: "new-space")
        let result = try await repository.addAssociation(item("retry", source: "\u{e9}"),
                                                        target: target, spaceId: "new-space")
        #expect(result.id == "first")
        #expect(try await repository.listDocumentAssociations(objectId: "new-document", spaceId: "new-space").count == 1)
        #expect(try await store.snapshot().live.count == 1)
    }

    @Test func quoteInstancesStayDistinctAndExactRetryDoesNotAppend() async throws {
        let (_, store, _, repository) = try fixture()
        for id in ["quote-A", "quote-B", "quote-A"] {
            _ = try await repository.addAssociation(item(id, role: .sourceQuote),
                                                   target: target, spaceId: "new-space")
        }
        let items = try await repository.listDocumentAssociations(objectId: "new-document", spaceId: "new-space")
        #expect(Set(items.map(\.id)) == ["quote-A", "quote-B"])
        #expect(await store.count() == 2)
    }

    @Test func documentAndBlockLocationsRemainIndependent() async throws {
        let (_, _, _, repository) = try fixture()
        _ = try await repository.addAssociation(item(), target: target, spaceId: "new-space")
        _ = try await repository.addAssociation(item(),
            target: .block(objectId: "new-document", blockId: "new-block"), spaceId: "new-space")
        try await repository.removeAssociation(associationId: "stable-id", target: target, spaceId: "new-space")
        #expect(try await repository.listDocumentAssociations(objectId: "new-document", spaceId: "new-space").isEmpty)
        #expect(try await repository.listBlockAssociations(objectId: "new-document", blockId: "new-block", spaceId: "new-space").count == 1)
    }

    @Test func wrongSpaceRejectedBeforeStoreMutation() async throws {
        let (_, store, _, repository) = try fixture()
        await #expect(throws: TorahAssociationRepositoryError.targetOutsideSpace) {
            try await repository.addAssociation(item(), target: target, spaceId: "heart-space")
        }
        #expect(await store.count() == 0)
    }

    @Test func mismatchedWorkspaceCannotConstructRepository() throws {
        let (workspace, store, _, _) = try fixture()
        let other = try AnyTorahWorkspace(accountID: "other", spaceID: workspace.spaceID)
        #expect(throws: AnyEngineError.invalidIdentity("mixed engine workspace")) {
            try AnyTorahAssociationRepository(workspace: workspace, store: store, access: TargetAccess(other))
        }
    }

    @Test func staleWholeSnapshotReplacementStillRefused() async throws {
        let (_, _, _, repository) = try fixture()
        await #expect(throws: TorahAssociationRepositoryError.unsafeSnapshotReplacement) {
            try await repository.setDocumentAssociations(objectId: "new-document", items: [item()], spaceId: "new-space")
        }
    }

    @Test func revokedPermissionPreventsWrites() async throws {
        let (_, store, access, repository) = try fixture()
        await access.setAllowed(false)
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await repository.addAssociation(item(), target: target, spaceId: "new-space")
        }
        #expect(await store.count() == 0)
    }

    @Test func authorityIsRecheckedAtAppendAfterInitialRead() async throws {
        let (_, store, access, repository) = try fixture()
        actor Gate {
            var calls = 0
            func check(_ access: TargetAccess) async {
                calls += 1
                if calls > 1 { await access.setAllowed(false) }
            }
        }
        let gate = Gate()
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await repository.apply(item(), target: target, spaceId: "new-space") {
                await gate.check(access)
            }
        }
        #expect(await store.count() == 0)
    }

    @Test func missingTargetPreventsWrites() async throws {
        let (_, store, access, repository) = try fixture()
        await access.setTargets([])
        await #expect(throws: TorahAssociationRepositoryError.targetNotFound) {
            try await repository.addAssociation(item(), target: target, spaceId: "new-space")
        }
        #expect(await store.count() == 0)
    }

    @Test func updateRequiresExistingStableID() async throws {
        let (_, store, _, repository) = try fixture()
        await #expect(throws: TorahAssociationRepositoryError.associationNotFound("stable-id")) {
            try await repository.updateAssociation(item(), target: target, spaceId: "new-space")
        }
        #expect(await store.count() == 0)
    }

    @Test func concurrentLocalMutationsDoNotReplaceUnrelatedItems() async throws {
        let (_, store, _, repository) = try fixture()
        try await withThrowingTaskGroup(of: Void.self) { group in
            for n in 1...20 {
                group.addTask {
                    _ = try await repository.addAssociation(item("id-\(n)", source: "Genesis 1:\(n)"),
                                                           target: target, spaceId: "new-space")
                }
            }
            try await group.waitForAll()
        }
        #expect(try await repository.listDocumentAssociations(objectId: "new-document", spaceId: "new-space").count == 20)
        #expect(await store.count() == 20)
    }

    @Test func concurrentSuccessorsAreVisibleConflictsNotSilentLWW() async throws {
        let (workspace, store, _, repository) = try fixture()
        _ = try await repository.addAssociation(item(), target: target, spaceId: workspace.spaceID)
        let original = try #require(try await store.snapshot().live.first)
        let codec = TorahAssociationPayloadCodec()
        for (n, label) in [(1, "first successor"), (2, "second successor")] {
            var revised = item(); revised.labelEn = label
            let record = TorahStoredAssociationRecord(
                location: .init(spaceId: workspace.spaceID, target: target), item: revised)
            try await store.seed(.init(
                operationID: String(repeating: String(n), count: 32),
                spaceID: workspace.spaceID, authorID: workspace.accountID, kind: .replace,
                targetObjectID: target.objectId, providerID: revised.providerID,
                canonicalRef: revised.canonicalKey,
                payload: codec.encodeCanonicalDocument(.init(records: [record])),
                observed: [original.id]))
        }
        let snapshot = try await repository.snapshot(target: target, spaceID: workspace.spaceID)
        #expect(snapshot.records.count == 2)
        #expect(snapshot.conflicts.count == 1)
        await #expect(throws: (any Error).self) {
            _ = try await repository.listDocumentAssociations(objectId: target.objectId, spaceId: workspace.spaceID)
        }
    }

    @Test func oldV1FixtureMigratesWithoutInventedMetadata() async throws {
        // Exact input from PinkhaKit TorahCanonicalAssociationsTests.legacyLift.
        let bytes = Data(#"{"futureEnvelope":{"kept":true},"items":[{"id":"legacy","kind":"ref","role":"source_quote","providerID":"sefaria","externalID":"Genesis.1.1","canonicalKey":"Genesis 1:1","labelHe":"בראשית א:א","futureItem":7}],"version":1}"#.utf8)
        let (workspace, store, access, repository) = try fixture()
        let plan = try AnyTorahMigrationPlan(
            sourceBytes: bytes, sourceSpaceID: "old-space", sourceObjectID: "old-document",
            workspace: workspace, targetObjectID: target.objectId, blockIDMap: [:], migrationKey: "first")
        #expect(plan.sourceBytes == bytes)
        #expect(plan.operations.count == 1)
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        #expect(try await executor.execute(plan).status == .complete)
        let result = try #require(try await repository.listDocumentAssociations(objectId: target.objectId, spaceId: workspace.spaceID).first)
        #expect(result.id == "legacy")
        #expect(result.role == .sourceQuote)
        #expect(result.createdAt == nil)
        #expect(result.unknownFields["futureItem"] == .number(7))
    }

    @Test func v2MigrationAndLaterEditRetainEnvelopeRecordAndItemUnknownFields() async throws {
        let (workspace, store, access, repository) = try fixture()
        let originalItem = item()
        let originalRecord = TorahStoredAssociationRecord(
            location: .init(spaceId: "old-space", target: .block(objectId: "old-document", blockId: "old-block")),
            item: originalItem, unknownFields: ["recordFuture": .string("kept")])
        let payload = TorahCanonicalAssociationsPayload(
            records: [originalRecord], unknownFields: ["envelopeFuture": .array([.number(1), .null])])
        let codec = TorahAssociationPayloadCodec()
        let bytes = try codec.encodeCanonicalDocument(payload)
        let plan = try AnyTorahMigrationPlan(
            sourceBytes: bytes, sourceSpaceID: "old-space", sourceObjectID: "old-document",
            workspace: workspace, targetObjectID: target.objectId,
            blockIDMap: ["old-block": "new-block"], migrationKey: "snapshot")
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        let receipt = try await executor.execute(plan)
        #expect(receipt.status == .complete)
        let retry = try await executor.execute(plan)
        #expect(retry.acknowledgedClaimIDs.isEmpty)
        #expect(retry.alreadyPresentClaimIDs.count == 1)
        var revised = originalItem
        revised.labelEn = "updated"
        revised.unknownFields = [:]
        _ = try await repository.updateAssociation(
            revised, target: .block(objectId: target.objectId, blockId: "new-block"), spaceId: workspace.spaceID)
        let op = try #require(try await store.snapshot().live.first).operation
        let reopened = try codec.decodeCanonicalDocument(op.payload,
            legacyLocation: .init(spaceId: workspace.spaceID, target: target))
        #expect(reopened.unknownFields == payload.unknownFields)
        #expect(reopened.records[0].unknownFields == originalRecord.unknownFields)
        #expect(reopened.records[0].item.unknownFields == originalItem.unknownFields)
        #expect(reopened.records[0].blockId == "new-block")
        #expect(plan.sourceBytes == bytes)
    }

    @Test func migrationRejectsMissingBlockMappingAndUnsupportedVersionBeforeWrites() throws {
        let (workspace, _, _, _) = try fixture()
        let payload = TorahCanonicalAssociationsPayload(records: [
            .init(location: .init(spaceId: "old", target: .block(objectId: "doc", blockId: "b")), item: item())
        ])
        let data = try TorahAssociationPayloadCodec().encodeCanonicalDocument(payload)
        #expect(throws: AnyEngineError.invalidIdentity("unmapped source block")) {
            try AnyTorahMigrationPlan(sourceBytes: data, sourceSpaceID: "old", sourceObjectID: "doc",
                workspace: workspace, targetObjectID: target.objectId, blockIDMap: [:], migrationKey: "key")
        }
        #expect(throws: TorahAssociationPayloadCodecError.unsupportedVersion(99)) {
            try AnyTorahMigrationPlan(sourceBytes: Data(#"{"version":99,"records":[]}"#.utf8),
                sourceSpaceID: "old", sourceObjectID: "doc", workspace: workspace,
                targetObjectID: target.objectId, blockIDMap: [:], migrationKey: "key")
        }
    }

    @Test func migrationPartialFailureHasResumableReceipt() async throws {
        let (workspace, store, access, _) = try fixture()
        let payload = TorahCanonicalAssociationsPayload(records: (1...3).map {
            .init(location: .init(spaceId: "old", target: .object(objectId: "doc")),
                  item: item("id-\($0)", source: "Genesis 1:\($0)"))
        })
        let plan = try AnyTorahMigrationPlan(
            sourceBytes: TorahAssociationPayloadCodec().encodeCanonicalDocument(payload),
            sourceSpaceID: "old", sourceObjectID: "doc", workspace: workspace,
            targetObjectID: target.objectId, blockIDMap: [:], migrationKey: "key")
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        await store.limitWrites(1)
        let partial = try await executor.execute(plan)
        #expect(partial.status == .incomplete)
        #expect(partial.acknowledgedClaimIDs.count == 1)
        #expect(partial.pendingClaimIDs.count == 2)
        await store.limitWrites(nil)
        let complete = try await executor.execute(plan)
        #expect(complete.status == .complete)
        #expect(complete.alreadyPresentClaimIDs.count == 1)
        #expect(complete.acknowledgedClaimIDs.count == 2)
        #expect(await store.count() == 3)
    }

    @Test func reusedMigrationIdentityWithChangedPayloadFailsBeforeWrite() async throws {
        let (workspace, store, access, _) = try fixture()
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        func plan(label: String) throws -> AnyTorahMigrationPlan {
            var value = item(); value.labelEn = label
            let bytes = try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(records: [
                .init(location: .init(spaceId: "old", target: .object(objectId: "doc")), item: value)
            ]))
            return try .init(sourceBytes: bytes, sourceSpaceID: "old", sourceObjectID: "doc",
                workspace: workspace, targetObjectID: target.objectId, blockIDMap: [:], migrationKey: "same")
        }
        #expect(try await executor.execute(plan(label: "A")).status == .complete)
        await #expect(throws: (any Error).self) {
            _ = try await executor.execute(plan(label: "B"))
        }
        #expect(await store.count() == 1)
    }
}

extension AssociationBridgeTests {
    @Test func workspaceDecoderCannotBypassValidation() {
        #expect(throws: (any Error).self) {
            try JSONDecoder().decode(AnyTorahWorkspace.self,
                from: Data(#"{"accountID":"","spaceID":"new-space"}"#.utf8))
        }
    }

    @Test func emptyMigrationPlanIdentityIncludesDestinationAndMigrationKey() throws {
        let (workspace, _, _, _) = try fixture()
        let data = Data(#"{"version":2,"records":[]}"#.utf8)
        func plan(_ target: String, _ key: String) throws -> AnyTorahMigrationPlan {
            try .init(sourceBytes: data, sourceSpaceID: "old", sourceObjectID: "doc",
                workspace: workspace, targetObjectID: target, blockIDMap: [:], migrationKey: key)
        }
        #expect(try plan("A", "key").planID != plan("B", "key").planID)
        #expect(try plan("A", "key").planID != plan("A", "other").planID)
    }

    @Test func preparedMutationReplaysExactObservedSetAfterInterveningEdit() async throws {
        let (_, store, _, repository) = try fixture()
        _ = try await repository.addAssociation(item(), target: target, spaceId: "new-space")
        var a = item(); a.labelEn = "Prepared A"
        let prepared = try #require(try await repository.prepareMutation(a, target: target, spaceId: "new-space"))
        let bytes = try JSONEncoder().encode(prepared)
        let restored = try JSONDecoder().decode(AnyTorahPreparedMutation.self, from: bytes)
        #expect(restored.operation == prepared.operation)
        var b = item(); b.labelEn = "Intervening B"
        _ = try await repository.updateAssociation(b, target: target, spaceId: "new-space")
        _ = try await repository.commitPrepared(restored)
        _ = try await repository.commitPrepared(restored)
        let snapshot = try await repository.snapshot(target: target, spaceID: "new-space")
        #expect(Set(snapshot.records.compactMap { $0.item.labelEn }) == ["Prepared A", "Intervening B"])
        #expect(snapshot.conflicts.count == 1)
        #expect(await store.count() == 3)
    }

    @Test func authoritativeMemberRoleAndIdentityFailClosed() throws {
        let (workspace, _, _, _) = try fixture()
        func member(_ role: String, status: String = "active", identity: String = "new-account") -> AnyJSON {
            .object(["identity": .string(identity), "permission": .string(role), "status": .string(status)])
        }
        try AnyHTTPTorahTargetAccess.validateMember(member("owner"), workspace: workspace, intent: .write)
        try AnyHTTPTorahTargetAccess.validateMember(member("reader"), workspace: workspace, intent: .read)
        for invalid in [member("reader"), member("none"), member("writer", status: "removed"),
                        member("owner", identity: "other")] {
            #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
                try AnyHTTPTorahTargetAccess.validateMember(invalid, workspace: workspace, intent: .write)
            }
        }
    }

    @Test func targetObjectCannotResolveAliasForeignSpaceOrBin() throws {
        let (workspace, _, _, _) = try fixture()
        func object(_ id: String = "new-document", space: String = "new-space",
                    type: String = "page", collections: [String] = []) -> AnyJSON {
            .object(["objectId": .string(id), "record": .object([
                "id": .string(id), "spaceId": .string(space),
                "any": .object(["type": .string(type), "collections": .array(collections.map(AnyJSON.string))])
            ])])
        }
        try AnyHTTPTorahTargetAccess.validateObject(object(), target: target, workspace: workspace,
            allowedTypeIDs: ["page"], excludedCollectionIDs: ["bin", "template"])
        let nativeEmptyCollections: AnyJSON = .object([
            "objectId": .string("new-document"), "record": .object([
                "id": .string("new-document"), "spaceId": .string("new-space"),
                "any": .object(["type": .string("page")])
            ])
        ])
        try AnyHTTPTorahTargetAccess.validateObject(nativeEmptyCollections, target: target, workspace: workspace,
            allowedTypeIDs: ["page"], excludedCollectionIDs: ["bin", "template"])
        for invalid in [object("alias-expanded"), object(space: "other"),
                        object(type: "operations"), object(collections: ["bin"])] {
            #expect(throws: TorahAssociationRepositoryError.targetNotFound) {
                try AnyHTTPTorahTargetAccess.validateObject(invalid, target: target, workspace: workspace,
                    allowedTypeIDs: ["page"], excludedCollectionIDs: ["bin", "template"])
            }
        }
    }

    @Test func blockTargetMustBeReachableNotMerelyPresent() throws {
        func response(_ pairs: [(String, String)]) -> AnyJSON {
            .object(["records": .array(pairs.map { id, parent in
                .object(["id": .string(id), "nav": .object(["parentId": .string(parent)])])
            }), "total": .integer(Int64(pairs.count)), "hasNext": .bool(false)])
        }
        try AnyHTTPTorahTargetAccess.requireReachableBlock("child",
            response: response([("parent", ""), ("child", "parent")]), limit: 10)
        for invalid in [response([("child", "deleted-parent")]),
                        response([("child", "parent"), ("parent", "child")]),
                        response([("unrelated", "")])] {
            #expect(throws: TorahAssociationRepositoryError.targetNotFound) {
                try AnyHTTPTorahTargetAccess.requireReachableBlock("child", response: invalid, limit: 10)
            }
        }
        #expect(throws: TorahAssociationRepositoryError.malformedCanonicalData) {
            try AnyHTTPTorahTargetAccess.requireReachableBlock("child",
                response: response([("child", ""), ("child", "")]), limit: 10)
        }
        #expect(throws: AnyEngineError.readLimit) {
            try AnyHTTPTorahTargetAccess.requireReachableBlock("child",
                response: response([("parent", ""), ("child", "parent")]), limit: 1)
        }
    }
}

extension AssociationBridgeTests {
    @Test func migrationRefusesNumbersTheOriginalDomainCannotPreserve() throws {
        let (workspace, _, _, _) = try fixture()
        for token in ["9007199254740993", "0.12345678901234567890123456789",
                      "100000000000000000000000000000000000001"] {
            let bytes = Data("{\"version\":2,\"records\":[],\"futureNumber\":\(token)}".utf8)
            #expect(throws: AnyTorahMigrationError.numericPrecisionWouldChange(path: "/futureNumber")) {
                try AnyTorahMigrationPlan(sourceBytes: bytes, sourceSpaceID: "old",
                    sourceObjectID: "doc", workspace: workspace, targetObjectID: target.objectId,
                    blockIDMap: [:], migrationKey: "precision")
            }
        }
    }

    @Test func exactDecimalGuardAcceptsEquivalentNotationAndIgnoresNumericStrings() throws {
        try AnyTorahSourceJSONGuard.validateRoundTrip(
            original: Data(#"{"a":1.00e3,"b":-0,"c":0.0001000,"quoted":"9007199254740993","nested":[7,true,null]}"#.utf8),
            encoded: Data(#"{"a":1000,"b":0,"c":1e-4,"quoted":"9007199254740993","nested":[7.0,true,null]}"#.utf8))
        #expect(throws: AnyTorahMigrationError.numericPrecisionWouldChange(path: "/a~1b~0c/0")) {
            try AnyTorahSourceJSONGuard.validateRoundTrip(
                original: Data(#"{"a/b~c":[9007199254740993]}"#.utf8),
                encoded: Data(#"{"a/b~c":[9007199254740992]}"#.utf8))
        }
    }

    @Test func ambiguousDuplicateJSONKeysCannotBeImported() throws {
        #expect(throws: AnyTorahMigrationError.duplicateJSONKey(path: "/future")) {
            try AnyTorahSourceJSONGuard.validateRoundTrip(
                original: Data(#"{"future":1,"\u0066uture":2}"#.utf8),
                encoded: Data(#"{"future":1}"#.utf8))
        }
    }

    private func oneItemPlan(_ workspace: AnyTorahWorkspace,
                             stableID: String = "imported") throws -> AnyTorahMigrationPlan {
        try .init(sourceBytes: TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(records: [
            .init(location: .init(spaceId: "old", target: .object(objectId: "doc")), item: item(stableID))
        ])), sourceSpaceID: "old", sourceObjectID: "doc", workspace: workspace,
        targetObjectID: target.objectId, blockIDMap: [:], migrationKey: "verification")
    }

    @Test func migrationKnownSemanticCollisionFailsBeforeAnyWrite() async throws {
        let (workspace, store, access, repository) = try fixture()
        _ = try await repository.addAssociation(item("already-here"), target: target, spaceId: workspace.spaceID)
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        await #expect(throws: (any Error).self) {
            _ = try await executor.execute(oneItemPlan(workspace))
        }
        #expect(await store.count() == 1)
    }

    @Test func migrationCannotReportCompleteAfterConcurrentSemanticCollision() async throws {
        let (workspace, store, access, _) = try fixture()
        let plan = try oneItemPlan(workspace)
        let original = try #require(plan.operations.first)
        let concurrent = try AnyTorahOperation(
            operationID: String(repeating: "f", count: 32), spaceID: workspace.spaceID,
            authorID: workspace.accountID, kind: .add, targetObjectID: target.objectId,
            providerID: original.providerID, canonicalRef: original.canonicalRef, payload: original.payload)
        await store.injectAfterNextAppend(concurrent)
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        let receipt = try await executor.execute(plan)
        #expect(receipt.status == .incomplete)
        #expect(receipt.acknowledgedClaimIDs == [original.claimID])
        #expect(receipt.pendingClaimIDs == [original.claimID])
    }

    @Test func migrationCannotReportCompleteAfterConcurrentObservedRemove() async throws {
        let (workspace, store, access, _) = try fixture()
        let plan = try oneItemPlan(workspace)
        let original = try #require(plan.operations.first)
        let remove = try AnyTorahOperation(
            operationID: String(repeating: "e", count: 32), spaceID: workspace.spaceID,
            authorID: workspace.accountID, kind: .remove, targetObjectID: target.objectId,
            observed: [original.claimID])
        await store.injectAfterNextAppend(remove)
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        let receipt = try await executor.execute(plan)
        #expect(receipt.status == .incomplete)
        #expect(receipt.pendingClaimIDs == [original.claimID])
        #expect(try await store.snapshot().live.isEmpty)
    }

    @Test func migrationCannotReportCompleteAfterConcurrentLogicalCollision() async throws {
        let (workspace, store, access, _) = try fixture()
        let plan = try oneItemPlan(workspace)
        let original = try #require(plan.operations.first)
        let codec = TorahAssociationPayloadCodec()
        var payload = try codec.decodeCanonicalDocument(original.payload,
            legacyLocation: .init(spaceId: workspace.spaceID, target: target))
        payload.records[0].item.labelEn = "Concurrent changed payload"
        let collision = try AnyTorahOperation(
            operationID: original.operationID, spaceID: workspace.spaceID,
            authorID: workspace.accountID, kind: .add, targetObjectID: target.objectId,
            providerID: original.providerID, canonicalRef: original.canonicalRef,
            payload: codec.encodeCanonicalDocument(payload))
        await store.injectAfterNextAppend(collision)
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        let receipt = try await executor.execute(plan)
        #expect(receipt.status == .incomplete)
        #expect(receipt.pendingClaimIDs == [original.claimID])
        #expect(try await store.snapshot().conflicts.count == 1)
    }
}

extension AssociationBridgeTests {
    private func internalNoteSource(metadataID: String = "old-note") throws -> Data {
        let note = TorahAssociationItem(
            id: "stable-note-link", kind: .ref, role: .context, providerID: "sefaria",
            externalID: "old-note", canonicalKey: "anytype-note:old-note", labelHe: "הערה",
            customMetadata: ["anytypeNoteObjectId": metadataID, "torahSelectionId": "selection-unchanged",
                             "futureMetadata": "preserved"],
            unknownFields: ["future": .array([.number(7), .null])])
        return try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(records: [
            .init(location: .init(spaceId: "old", target: .object(objectId: "origin")), item: note)
        ]))
    }

    @Test func internalNoteLinksRequireExplicitDestinationMapping() throws {
        let (workspace, _, _, _) = try fixture()
        #expect(throws: AnyTorahMigrationError.unmappedReferencedObject("old-note")) {
            try AnyTorahMigrationPlan(sourceBytes: internalNoteSource(),
                sourceSpaceID: "old", sourceObjectID: "origin", workspace: workspace,
                targetObjectID: target.objectId, blockIDMap: [:], migrationKey: "note")
        }
    }

    @Test func internalNoteMappingRewritesOnlyKnownNativeReferenceFields() throws {
        let (workspace, _, _, _) = try fixture()
        let bytes = try internalNoteSource()
        let plan = try AnyTorahMigrationPlan(sourceBytes: bytes,
            sourceSpaceID: "old", sourceObjectID: "origin", workspace: workspace,
            targetObjectID: target.objectId, blockIDMap: [:],
            objectIDMap: ["old-note": "new-note"], migrationKey: "note")
        let operation = try #require(plan.operations.first)
        let decoded = try TorahAssociationPayloadCodec().decodeCanonicalDocument(operation.payload,
            legacyLocation: .init(spaceId: workspace.spaceID, target: target))
        let item = try #require(decoded.records.first).item
        #expect(item.id == "stable-note-link")
        #expect(item.externalID == "new-note")
        #expect(item.canonicalKey == "anytype-note:new-note")
        #expect(item.customMetadata?["anytypeNoteObjectId"] == "new-note")
        #expect(item.customMetadata?["torahSelectionId"] == "selection-unchanged")
        #expect(item.customMetadata?["futureMetadata"] == "preserved")
        #expect(item.unknownFields["future"] == .array([.number(7), .null]))
        #expect(plan.sourceBytes == bytes)
        #expect(plan.referencedObjectIDs == ["new-note"])
        #expect(plan.objectIDMap == ["origin": target.objectId, "old-note": "new-note"])
    }

    @Test func malformedInternalNoteLinkCannotBeGuessed() throws {
        let (workspace, _, _, _) = try fixture()
        #expect(throws: AnyTorahMigrationError.malformedInternalNoteLink(itemID: "stable-note-link")) {
            try AnyTorahMigrationPlan(sourceBytes: internalNoteSource(metadataID: "different"),
                sourceSpaceID: "old", sourceObjectID: "origin", workspace: workspace,
                targetObjectID: target.objectId, blockIDMap: [:],
                objectIDMap: ["old-note": "new-note"], migrationKey: "note")
        }
    }

    @Test func mappedNoteMustExistInDestinationWorkspaceBeforeImport() async throws {
        let (workspace, store, access, _) = try fixture()
        await access.setTargets([target])
        let plan = try AnyTorahMigrationPlan(sourceBytes: internalNoteSource(),
            sourceSpaceID: "old", sourceObjectID: "origin", workspace: workspace,
            targetObjectID: target.objectId, blockIDMap: [:],
            objectIDMap: ["old-note": "new-note"], migrationKey: "note")
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        await #expect(throws: TorahAssociationRepositoryError.targetNotFound) {
            _ = try await executor.execute(plan)
        }
        #expect(await store.count() == 0)
    }
}


extension AssociationBridgeTests {
    private func payloadWithNumericProbe(workspace: AnyTorahWorkspace,
                                         replacement: String) throws -> Data {
        var value = item()
        value.unknownFields["precisionProbe"] = .number(7)
        let bytes = try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(records: [
            .init(location: .init(spaceId: workspace.spaceID, target: target), item: value)
        ]))
        let original = try #require(String(data: bytes, encoding: .utf8))
        let marker = #""precisionProbe":7"#
        #expect(original.contains(marker))
        return Data(original.replacingOccurrences(of: marker,
            with: #""precisionProbe":"# + replacement).utf8)
    }

    private func incomingOperation(workspace: AnyTorahWorkspace, payload: Data) throws -> AnyTorahOperation {
        try .init(operationID: String(repeating: "a", count: 32),
            spaceID: workspace.spaceID, authorID: workspace.accountID, kind: .add,
            targetObjectID: target.objectId, providerID: "sefaria", canonicalRef: "Genesis 1:1",
            payload: payload)
    }

    @Test func incomingPeerUnknownNumbersCannotSilentlyRoundDuringOrdinaryEdit() async throws {
        for number in ["9007199254740993", "0.10000000000000000000000000000000000000001"] {
            let (workspace, store, _, repository) = try fixture()
            let bytes = try payloadWithNumericProbe(workspace: workspace, replacement: number)
            try await store.seed(incomingOperation(workspace: workspace, payload: bytes))
            await #expect(throws: AnyTorahMigrationError.self) {
                try await repository.listDocumentAssociations(objectId: target.objectId, spaceId: workspace.spaceID)
            }
            var changed = item(); changed.labelEn = "Changed label"
            await #expect(throws: AnyTorahMigrationError.self) {
                try await repository.updateAssociation(changed, target: target, spaceId: workspace.spaceID)
            }
            #expect(await store.count() == 1)
            #expect(try await store.snapshot().all.first?.operation.payload == bytes)
        }
    }

    @Test func incomingPeerDuplicateUnknownKeysCannotBeSilentlyCollapsed() async throws {
        let (workspace, store, _, repository) = try fixture()
        let bytes = try payloadWithNumericProbe(workspace: workspace,
                                               replacement: #"7,"precisionProbe":8"#)
        try await store.seed(incomingOperation(workspace: workspace, payload: bytes))
        await #expect(throws: AnyTorahMigrationError.self) {
            try await repository.snapshot(target: target, spaceID: workspace.spaceID)
        }
        #expect(await store.count() == 1)
        #expect(try await store.snapshot().all.first?.operation.payload == bytes)
    }

    @Test func restoredPreparedMutationCannotBypassIncomingNumberPreservation() throws {
        let (workspace, _, _, _) = try fixture()
        let bytes = try payloadWithNumericProbe(workspace: workspace, replacement: "9007199254740993")
        let operation = try incomingOperation(workspace: workspace, payload: bytes)
        #expect(throws: AnyTorahMigrationError.self) {
            try AnyTorahPreparedMutation(workspace: workspace, operation: operation)
        }
    }
}
