import Foundation
import XCTest
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Composition controls for the production canonical migration path. These
/// detached records do not qualify whole-source authority or native persistence.
final class NativeTorahSemanticMigrationTests: XCTestCase, @unchecked Sendable {
    private let old = TorahAssociationLocation(spaceId: "old-מרחב", target: .object(objectId: "old-document"))
    private let target = TorahAssociationLocation(spaceId: "new-מרחב", target: .object(objectId: "new-document"))
    private let uuid1 = UUID(uuidString: "cfe050d0-e511-440c-86a5-526bc1234567")!
    private let uuid2 = UUID(uuidString: "27ed89f1-066e-4360-9b5a-c624c2345678")!

    func testCanonicalMigrationRemapsTwoSameVerseTargetsAndPreservesAllOtherFields() throws {
        let first = try item(id: "first", anchorID: uuid1)
        let second = try item(id: "second", anchorID: uuid2)
        let (plan, bytes) = try plan([first, second])
        XCTAssertEqual(plan.sourceBytes, bytes)
        XCTAssertEqual(plan.sourceSHA256, AnyContentDigest.sha256(bytes))
        XCTAssertEqual(plan.operations.count, 2)
        var identities = Set<TorahAssociationIdentity>()
        for (index, operation) in plan.operations.enumerated() {
            let source = [first, second][index]
            let decoded = try TorahAssociationPayloadCodec().decodeCanonicalDocument(operation.payload,
                                                                                      legacyLocation: target)
            XCTAssertEqual(decoded.unknownFields, ["envelopeFuture": .array([.number(1), .null])])
            let record = try XCTUnwrap(decoded.records.only)
            XCTAssertEqual(record.location, target)
            XCTAssertEqual(record.unknownFields, ["recordFuture": .bool(false)])
            let semantic = try XCTUnwrap(TorahSemanticAnchorAssociation.decoding(record.item, location: target))
            XCTAssertEqual(semantic.anchor.id, [uuid1, uuid2][index])
            XCTAssertTrue(semantic.anchor.belongsTo(spaceID: target.spaceId, objectID: target.target.objectId))
            var restored = record.item
            restored.customMetadata?[TorahSemanticAnchorAssociation.metadataKey] =
                source.customMetadata?[TorahSemanticAnchorAssociation.metadataKey]
            XCTAssertEqual(restored, source)
            XCTAssertThrowsError(try TorahSemanticAnchorAssociation.decoding(record.item, location: old))
            XCTAssertTrue(identities.insert(.init(item: record.item, location: target)).inserted)
            XCTAssertNoThrow(try AnyTorahPreparedMutation(workspace: plan.workspace, operation: operation))
            let oldAnchor = try XCTUnwrap(TorahSemanticAnchorAssociation.decoding(source, location: old)).anchor
            let text = try AnyInlineMarkdown("[שָׁלוֹם 😀](\(oldAnchor.markerString))").remappingSemanticAnchors(
                sourceSpaceID: old.spaceId, sourceObjectID: old.target.objectId,
                destinationSpaceID: target.spaceId, destinationObjectID: target.target.objectId)
            XCTAssertEqual(try AnyInlineMarkdown(text).semanticText().marks.first?.anchor, semantic.anchor)
        }
    }

    func testLegacyAndInternalNoteMappingsComposeWithoutDroppingSemanticOrFutureMetadata() throws {
        var note = try item(id: "note", anchorID: uuid1)
        note.canonicalKey = "anytype-note:old-note"; note.externalID = "old-note"
        note.customMetadata?["anytypeNoteObjectId"] = "old-note"
        var legacy = note
        legacy.id = "legacy"; legacy.customMetadata?.removeValue(forKey: TorahSemanticAnchorAssociation.metadataKey)
        let (plan, _) = try plan([note, legacy], objects: ["old-note": "new-note"])
        XCTAssertEqual(plan.referencedObjectIDs, ["new-note"])
        let records = try plan.operations.map {
            try XCTUnwrap(TorahAssociationPayloadCodec().decodeCanonicalDocument($0.payload,
                legacyLocation: target).records.only)
        }
        for record in records {
            XCTAssertEqual(record.item.canonicalKey, "anytype-note:new-note")
            XCTAssertEqual(record.item.externalID, "new-note")
            XCTAssertEqual(record.item.customMetadata?["anytypeNoteObjectId"], "new-note")
            XCTAssertEqual(record.item.customMetadata?["future"], "kept a\u{301}")
            XCTAssertEqual(record.item.unknownFields, note.unknownFields)
        }
        XCTAssertEqual(try TorahSemanticAnchorAssociation.decoding(records[0].item, location: target)?.anchor.id, uuid1)
        XCTAssertNil(try TorahSemanticAnchorAssociation.decoding(records[1].item, location: target))
        XCTAssertThrowsError(try self.plan([note]))
    }

    func testForeignFutureUnknownAndDuplicateReservedMetadataFailBeforePlanCreation() throws {
        let original = try item(id: "source", anchorID: uuid1)
        let marker = try XCTUnwrap(TorahSemanticAnchorAssociation.decoding(original, location: old)).anchor.markerString
        let foreign = try PinkhaSemanticTextAnchor(spaceID: "foreign", objectID: old.target.objectId, id: uuid1)
        let good = try XCTUnwrap(original.customMetadata?[TorahSemanticAnchorAssociation.metadataKey])
        let rawCases = [
            "{\"version\":1,\"marker\":\"\(foreign.markerString)\"}",
            "{\"version\":2,\"marker\":\"\(marker)\"}",
            "{\"version\":1,\"marker\":\"\(marker)\",\"future\":\"unrepresented\"}",
            "{\"version\":1,\"marker\":\"\(marker)\",\"future\":null}",
            "{\"version\":1,\"marker\":\"\(marker)\",\"version\":1}",
            "{\"version\":1,\"marker\":\"\(marker)\",\"marker\":\"\(marker)\"}",
            good.replacingOccurrences(of: "://v1/", with: "://v2/")
        ]
        for raw in rawCases {
            var value = original; value.customMetadata?[TorahSemanticAnchorAssociation.metadataKey] = raw
            XCTAssertThrowsError(try plan([value]))
            XCTAssertThrowsError(try AnySemanticAnchorAssociationMigration.remapping(
                value, source: old, destination: target))
        }
    }

    func testBlockOwnedSemanticMetadataAndDuplicateLogicalTargetRemainRefused() throws {
        let first = try item(id: "first", anchorID: uuid1)
        let second = try item(id: "second", anchorID: uuid1)
        XCTAssertThrowsError(try plan([first, second]))
        let location = TorahAssociationLocation(spaceId: old.spaceId,
            target: .block(objectId: old.target.objectId, blockId: "old-block"))
        let bytes = try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(
            records: [.init(location: location, item: first)]))
        XCTAssertThrowsError(try AnyTorahMigrationPlan(sourceBytes: bytes, sourceSpaceID: old.spaceId,
            sourceObjectID: old.target.objectId, workspace: workspace(), targetObjectID: target.target.objectId,
            blockIDMap: ["old-block": "new-block"], migrationKey: "semantic"))
    }

    func testRetryKeepsOperationIdentityWhileChangedOriginalPayloadChangesClaim() throws {
        var source = try item(id: "stable", anchorID: uuid1)
        let (first, _) = try plan([source])
        let (repeatPlan, _) = try plan([source])
        XCTAssertEqual(first.planID, repeatPlan.planID)
        XCTAssertEqual(first.operations, repeatPlan.operations)
        source.labelEn = "Changed original label"
        let (changed, _) = try plan([source])
        XCTAssertEqual(first.operations.first?.operationID, changed.operations.first?.operationID)
        XCTAssertNotEqual(first.operations.first?.claimID, changed.operations.first?.claimID)
        XCTAssertNotEqual(first.planID, changed.planID)
    }


    func testSemanticMigrationRefusesObjectOnlyAuthorityBeforeReadingOrWritingClaims() async throws {
        let (plan, _) = try plan([item(id: "first", anchorID: uuid1)])
        let store = SemanticControlStore(plan.workspace)
        let executor = try AnyTorahMigrationExecutor(workspace: plan.workspace, store: store,
                                                     access: ObjectOnlySemanticControlAccess(workspace: plan.workspace))
        do {
            _ = try await executor.execute(plan)
            XCTFail("Object membership alone cannot admit a semantic target")
        } catch AnyEngineError.invalidOperation {}
        let counts = await store.counts()
        XCTAssertEqual(counts.reads, 0); XCTAssertEqual(counts.writes, 0)
    }

    func testSemanticTargetLossAtAppendReturnsIncompleteWithoutCreatingClaim() async throws {
        let (plan, _) = try plan([item(id: "first", anchorID: uuid1)])
        let store = SemanticControlStore(plan.workspace)
        let access = SemanticControlAccess(plan.workspace, failAt: 2)
        let executor = try AnyTorahMigrationExecutor(workspace: plan.workspace, store: store, access: access)
        let result = try await executor.execute(plan)
        XCTAssertEqual(result.status, .incomplete)
        XCTAssertEqual(result.pendingClaimIDs, plan.operations.map(\.claimID))
        XCTAssertTrue(result.acknowledgedClaimIDs.isEmpty)
        let counts = await store.counts()
        XCTAssertEqual(counts.writes, 0)
    }

    func testSemanticTargetLossAfterAcknowledgementCannotProduceCompleteReceiptAndExactRetryRecovers() async throws {
        let (plan, _) = try plan([item(id: "first", anchorID: uuid1)])
        let store = SemanticControlStore(plan.workspace)
        let access = SemanticControlAccess(plan.workspace, failAt: 3)
        let executor = try AnyTorahMigrationExecutor(workspace: plan.workspace, store: store, access: access)
        let first = try await executor.execute(plan)
        XCTAssertEqual(first.status, .incomplete)
        XCTAssertEqual(first.acknowledgedClaimIDs, plan.operations.map(\.claimID))
        XCTAssertEqual(first.pendingClaimIDs, plan.operations.map(\.claimID))
        let before = await store.counts()
        XCTAssertEqual(before.writes, 1)
        await access.allow()
        let retry = try await executor.execute(plan)
        XCTAssertEqual(retry.status, .complete)
        XCTAssertEqual(retry.alreadyPresentClaimIDs, plan.operations.map(\.claimID))
        XCTAssertTrue(retry.acknowledgedClaimIDs.isEmpty)
        let after = await store.counts()
        XCTAssertEqual(after.writes, 1)
    }

    private func item(id: String, anchorID: UUID) throws -> TorahAssociationItem {
        let base = TorahAssociationItem(id: id, kind: .ref, role: .context, providerID: "sefaria",
            externalID: "Genesis 1:1", canonicalKey: "Genesis.1.1", labelHe: "בראשית א׳ א׳",
            labelEn: "Genesis 1:1", rawInput: "raw a\u{301}", providerPayload: "{\"original\":[0,false,null]}",
            createdAt: Date(timeIntervalSince1970: 123), updatedAt: Date(timeIntervalSince1970: 456),
            customMetadata: ["future": "kept a\u{301}"], unknownFields: ["futureValue": .array([.null, .bool(false)])])
        let anchor = try PinkhaSemanticTextAnchor(spaceID: old.spaceId, objectID: old.target.objectId, id: anchorID)
        return try TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: base, location: old)
    }

    private func workspace() throws -> AnyTorahWorkspace {
        try .init(accountID: "new-account", spaceID: target.spaceId)
    }

    private func plan(_ items: [TorahAssociationItem], objects: [String: String] = [:]) throws
        -> (AnyTorahMigrationPlan, Data) {
        let bytes = try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(
            records: items.map { .init(location: old, item: $0, unknownFields: ["recordFuture": .bool(false)]) },
            unknownFields: ["envelopeFuture": .array([.number(1), .null])]))
        return (try .init(sourceBytes: bytes, sourceSpaceID: old.spaceId, sourceObjectID: old.target.objectId,
            workspace: workspace(), targetObjectID: target.target.objectId, blockIDMap: [:],
            objectIDMap: objects, migrationKey: "semantic"), bytes)
    }
}

private extension Array {
    var only: Element? { count == 1 ? first : nil }
}

private struct ObjectOnlySemanticControlAccess: AnyTorahTargetAccess {
    let workspace: AnyTorahWorkspace
    func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) async throws {}
}

private actor SemanticControlAccess: AnyTorahSemanticTargetAccess {
    nonisolated let workspace: AnyTorahWorkspace
    private var calls = 0
    private var failAt: Int?
    init(_ workspace: AnyTorahWorkspace, failAt: Int) { self.workspace = workspace; self.failAt = failAt }
    func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) async throws {}
    func validateSemanticTarget(_ anchor: PinkhaSemanticTextAnchor) throws {
        calls += 1
        if failAt == calls { throw AnyHostError.invalidSelection }
    }
    func allow() { failAt = nil }
}

private actor SemanticControlStore: AnyTorahOperationStore {
    nonisolated let workspace: AnyTorahWorkspace
    private var claims: [AnyTorahClaim] = []
    private var reads = 0
    private var writes = 0
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func snapshot() throws -> AnyTorahProjection {
        reads += 1
        return try .init(claims: claims)
    }
    func append(_ operation: AnyTorahOperation,
                authorize: @escaping @Sendable () async throws -> Void) async throws {
        try await authorize()
        guard !claims.contains(where: { $0.operation.logicalKey == operation.logicalKey }) else {
            throw AnyEngineError.collision(operation.logicalKey)
        }
        claims.append(try .init(operation: operation, creator: workspace.accountID))
        writes += 1
    }
    func counts() -> (reads: Int, writes: Int) { (reads, writes) }
}
