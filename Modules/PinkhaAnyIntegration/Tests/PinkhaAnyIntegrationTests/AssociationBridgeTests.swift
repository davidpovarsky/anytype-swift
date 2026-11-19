import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

private actor MemoryStore: AnyTorahOperationStore {
    nonisolated let workspace: AnyTorahWorkspace
    private var claims: [AnyTorahClaim] = []
    private var remainingWrites: Int?
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
    }
    func seed(_ op: AnyTorahOperation) throws {
        claims.append(try .init(operation: op, creator: op.authorID))
    }
    func limitWrites(_ limit: Int?) { remainingWrites = limit }
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
