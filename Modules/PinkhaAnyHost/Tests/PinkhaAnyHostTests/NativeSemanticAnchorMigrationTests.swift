import Foundation
import XCTest
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Codec and plan controls use synthetic bound native snapshots. Actual engine
/// writes, full-space migration and UI acceptance are separate requirements.
final class NativeSemanticAnchorMigrationTests: XCTestCase {
    private let anchorID = UUID(uuidString: "cfe050d0-e511-440c-86a5-526bc1234567")!
    private let sourceSpace = "source-מרחב"
    private let sourceObject = "source-document"
    private let targetSpace = "target-מרחב"
    private let targetObject = "native-allocated-document"

    private func anchor(space: String? = nil, object: String? = nil) throws -> PinkhaSemanticTextAnchor {
        try .init(spaceID: space ?? sourceSpace, objectID: object ?? sourceObject, id: anchorID)
    }
    private func remap(_ value: String) throws -> String {
        try AnyInlineMarkdown(value).remappingSemanticAnchors(sourceSpaceID: sourceSpace,
            sourceObjectID: sourceObject, destinationSpaceID: targetSpace, destinationObjectID: targetObject)
    }

    func testParserOwnedRemapPreservesExactUnicodeStylesLinksAndLiteralMarkerText() throws {
        let marker = try anchor(), destination = try anchor(space: targetSpace, object: targetObject)
        let original = "**before** [שָׁלוֹם 😀 a\u{301}](\(marker.markerString)) _after_ " +
            "[web](https://example.com/a%2Fb?q=1) literal \(marker.markerString) " +
            "\u{60}[\(marker.markerString)]\u{60}"
        let parsed = AnyInlineMarkdown(original), before = try parsed.semanticText()
        XCTAssertTrue(parsed.isEditable)
        let changed = try remap(original), projected = AnyInlineMarkdown(changed)
        XCTAssertEqual(projected.display.data(using: .utf8), parsed.display.data(using: .utf8))
        XCTAssertEqual(try projected.semanticText().marks, before.marks.map { .init(anchor: destination, range: $0.range) })
        XCTAssertTrue(changed.contains("[web](https://example.com/a%2Fb?q=1)"))
        XCTAssertTrue(changed.contains("literal \(marker.markerString)"))
        XCTAssertTrue(changed.contains("\u{60}[\(marker.markerString)]\u{60}"))
        XCTAssertTrue(changed.hasPrefix("**before** "))
        XCTAssertTrue(changed.contains(" _after_ "))
        XCTAssertEqual(try PinkhaSemanticTextAnchor(markerURL: destination.markerURL()).id, marker.id)
        XCTAssertFalse(destination.belongsTo(spaceID: sourceSpace, objectID: sourceObject))
        XCTAssertFalse(marker.belongsTo(spaceID: targetSpace, objectID: targetObject))
        let template = try AnyDestinationAnchoredText(sourceSpaceID: sourceSpace, sourceObjectID: sourceObject,
                                                     inlineMarkdown: original)
        XCTAssertEqual(try template.resolved(destinationSpaceID: targetSpace, destinationObjectID: targetObject), changed)
        XCTAssertEqual(try JSONDecoder().decode(AnyDestinationAnchoredText.self,
            from: JSONEncoder().encode(template)), template)
    }

    func testForeignMalformedFutureAndCanonicallyDifferentSourceIdentitiesRemainRefused() throws {
        let original = try anchor().markerString
        for value in [
            try anchor(space: "other-space").markerString,
            try anchor(object: "other-document").markerString,
            original.replacingOccurrences(of: "://v1/", with: "://v2/"),
            original + "?foreign=1", original.uppercased()
        ] {
            XCTAssertThrowsError(try remap("[selected](\(value))"))
            XCTAssertThrowsError(try AnyDestinationAnchoredText(sourceSpaceID: sourceSpace,
                sourceObjectID: sourceObject, inlineMarkdown: "[selected](\(value))"))
        }
        let composed = try anchor(space: "é")
        XCTAssertThrowsError(try AnyInlineMarkdown("[a](\(composed.markerString))").remappingSemanticAnchors(
            sourceSpaceID: "e\u{301}", sourceObjectID: sourceObject,
            destinationSpaceID: targetSpace, destinationObjectID: targetObject)) {
            XCTAssertEqual($0 as? PinkhaSemanticTextAnchorError, .wrongDocument)
        }
        XCTAssertThrowsError(try AnyDestinationAnchoredText(sourceSpaceID: sourceSpace,
            sourceObjectID: sourceObject, inlineMarkdown: "no semantic link"))
        let literal = "[literal](\(original))"
        XCTAssertEqual(try AnyInlineMarkdown(literal: literal).remappingSemanticAnchors(
            sourceSpaceID: sourceSpace, sourceObjectID: sourceObject,
            destinationSpaceID: targetSpace, destinationObjectID: targetObject), literal)
    }

    func testHeartNativeMarksProduceScopedTemplateAndKeepOriginalSnapshotBytes() throws {
        let marker = try anchor()
        let visible = "lead שָׁלוֹם 😀 a\u{301} tail"
        let range = (visible as NSString).range(of: "שָׁלוֹם 😀 a\u{301}")
        let rows: [AnyJSON] = [
            mark(5, range: range, parameter: marker.markerString),
            mark(3, range: (visible as NSString).range(of: "שָׁלוֹם"), parameter: ""),
            mark(2, range: (visible as NSString).range(of: "a\u{301}"), parameter: "")
        ]
        let view = try snapshot(text: visible, marks: rows)
        let block = try XCTUnwrap(view.blocks.first { $0.id == "body" })
        let projection = try block.inlineProjection()
        XCTAssertThrowsError(try AnyHeartInlineConversion(projection),
                             "The unscoped conversion must never admit a semantic marker")
        let textPlan = try AnyHeartNativeTextBlockPlan(snapshot: view)
        XCTAssertEqual(textPlan.snapshotSHA256, view.snapshotSHA256)
        XCTAssertEqual(textPlan.viewSHA256, view.viewSHA256)
        XCTAssertEqual(textPlan.entries.first?.originalNative, block.raw)
        let template = try XCTUnwrap(textPlan.entries.first?.semanticAnchors)
        XCTAssertEqual(AnyInlineMarkdown(template.inlineMarkdown).display.data(using: .utf8), visible.data(using: .utf8))
        XCTAssertEqual(try AnyInlineMarkdown(template.inlineMarkdown).semanticText().marks,
                       [.init(anchor: marker, range: range)])
        guard case .anchoredEditorBlock(_, _, _, let submitted, _, _, _) =
            try XCTUnwrap(textPlan.destinationItems(ownerSourceKey: "created-owner").first).operation else {
            return XCTFail("Native semantic marks must remain source-scoped until owner allocation")
        }
        XCTAssertEqual(submitted, template)
        XCTAssertThrowsError(try AnyHeartNativeTextBlockPlan(snapshot: snapshot(text: visible,
            marks: [mark(5, range: range, parameter: try anchor(object: "foreign").markerString)])))
        let literal = "[source code](\(marker.markerString))"
        let code = try AnyHeartNativeTextBlockPlan(snapshot: snapshot(text: literal, marks: [], style: 6))
        XCTAssertNil(code.entries.first?.semanticAnchors)
        XCTAssertEqual(code.entries.first?.text, literal)
        XCTAssertFalse(textPlan.permitsDestinationWrites)
    }

    func testDestinationPlanResolvesOnlyActualMappedOwnerAndPreservesCanonicalJournalBytes() throws {
        let template = try AnyDestinationAnchoredText(sourceSpaceID: sourceSpace, sourceObjectID: sourceObject,
            inlineMarkdown: "[selected](\(anchor().markerString))")
        let operation = anchored(template)
        let plan = try plan(operation)
        let copy = try AnyDestinationMigrationPlan.decode(AnyDestinationMigrationJournal.encoded(plan))
        XCTAssertEqual(copy.canonicalBytes, plan.canonicalBytes)
        XCTAssertEqual(copy.items[1].operation, operation)
        XCTAssertThrowsError(try operation.resolved { _ in self.targetObject })
        XCTAssertThrowsError(try AnyDestinationNativeIntent.make(operation, binding: plan.binding,
            sourceKey: "body", sequence: nil, inlineContent: nil))
        let resolved = try operation.resolved(destinationSpaceID: targetSpace) { _ in self.targetObject }
        guard case .editorBlock(let owner, _, _, let text, _, _, _) = resolved else { return XCTFail() }
        XCTAssertEqual(owner, .native(targetObject))
        let mark = try XCTUnwrap(AnyInlineMarkdown(text).semanticText().marks.first)
        XCTAssertEqual(mark.anchor, try anchor(space: targetSpace, object: targetObject))
        XCTAssertNoThrow(try AnyDestinationNativeIntent.make(resolved, binding: plan.binding,
            sourceKey: "body", sequence: nil, inlineContent: nil))
        XCTAssertEqual(try JSONDecoder().decode(AnyDestinationMigrationOperation.self,
            from: AnyDestinationMigrationJournal.encoded(resolved)), resolved)
        let unscoped = AnyDestinationMigrationOperation.editorBlock(owner: ref("owner"), dataset: "editor_blocks",
            type: "paragraph", text: template.inlineMarkdown, style: .literal(.object([:])), parent: nil, position: "A")
        XCTAssertThrowsError(try self.plan(unscoped))
        XCTAssertThrowsError(try self.plan(anchored(template, owner: .native("foreign-existing-document"))))
        let foreignSpace = try AnyDestinationAnchoredText(sourceSpaceID: "foreign", sourceObjectID: sourceObject,
            inlineMarkdown: "[selected](\(anchor(space: "foreign").markerString))")
        XCTAssertThrowsError(try self.plan(anchored(foreignSpace)))
        let foreignObject = try AnyDestinationAnchoredText(sourceSpaceID: sourceSpace, sourceObjectID: "foreign",
            inlineMarkdown: "[selected](\(anchor(object: "foreign").markerString))")
        XCTAssertThrowsError(try self.plan(anchored(foreignObject)))
        XCTAssertThrowsError(try self.plan(anchored(template, type: "code")))
    }

    func testAssociationRemapsSameUUIDAndPreservesEveryOtherMetadataAndPayloadField() throws {
        let source = TorahAssociationLocation(spaceId: sourceSpace, target: .object(objectId: sourceObject))
        let destination = TorahAssociationLocation(spaceId: targetSpace, target: .object(objectId: targetObject))
        let original = TorahAssociationItem(id: "existing-association-id", kind: .ref, role: .sourceQuote,
            providerID: "sefaria", externalID: "Genesis 1:1", canonicalKey: "Genesis.1.1",
            labelHe: "בראשית א׳ א׳", labelEn: "Genesis 1:1", rawInput: "raw a\u{301}",
            providerPayload: "{\"original\":[0,false,null]}", createdAt: Date(timeIntervalSince1970: 123),
            updatedAt: Date(timeIntervalSince1970: 456), customMetadata: ["unknown": "retained"],
            unknownFields: ["future": .object(["present": .bool(false)])])
        let marked = try TorahSemanticAnchorAssociation(anchor: anchor()).attaching(to: original, location: source)
        let changed = try AnySemanticAnchorAssociationMigration.remapping(marked, source: source, destination: destination)
        let current = try XCTUnwrap(TorahSemanticAnchorAssociation.decoding(changed, location: destination))
        XCTAssertEqual(current.anchor, try anchor(space: targetSpace, object: targetObject))
        var restored = changed
        restored.customMetadata?[TorahSemanticAnchorAssociation.metadataKey] =
            marked.customMetadata?[TorahSemanticAnchorAssociation.metadataKey]
        XCTAssertEqual(restored, marked, "Only reserved semantic target metadata may change")
        XCTAssertThrowsError(try TorahSemanticAnchorAssociation.decoding(marked, location: destination))
        XCTAssertThrowsError(try TorahSemanticAnchorAssociation.decoding(changed, location: source))
        XCTAssertEqual(try AnySemanticAnchorAssociationMigration.remapping(original,
            source: source, destination: destination), original)
        let block = TorahAssociationLocation(spaceId: targetSpace, target: .block(objectId: targetObject, blockId: "block"))
        XCTAssertThrowsError(try AnySemanticAnchorAssociationMigration.remapping(marked, source: source, destination: block))
        var invalid = marked
        invalid.customMetadata?[TorahSemanticAnchorAssociation.metadataKey] = "{\"version\":99,\"marker\":\"future\"}"
        XCTAssertThrowsError(try AnySemanticAnchorAssociationMigration.remapping(invalid, source: source, destination: destination))
    }

    func testDuplicateFragmentsRemainAmbiguousAndOldMarkerCannotResolveInNewDocument() throws {
        let marker = try anchor(), destination = try anchor(space: targetSpace, object: targetObject)
        let native = "[selected](\(marker.markerString))"
        let changed = try remap(native)
        let blocks: [PinkhaSemanticTextAnchorResolver.Block] = [
            .init(id: "first", content: try AnyInlineMarkdown(changed).semanticText()),
            .init(id: "separator", content: try .init(text: "unrelated")),
            .init(id: "copy", content: try AnyInlineMarkdown(changed).semanticText())
        ]
        XCTAssertEqual(try PinkhaSemanticTextAnchorResolver.resolve(destination,
            spaceID: targetSpace, objectID: targetObject, blocks: blocks), .ambiguous)
        XCTAssertThrowsError(try PinkhaSemanticTextAnchorResolver.resolve(marker,
            spaceID: targetSpace, objectID: targetObject, blocks: blocks)) {
            XCTAssertEqual($0 as? PinkhaSemanticTextAnchorError, .wrongDocument)
        }
    }

    private func ref(_ key: String) -> AnyDestinationReference {
        .mapped(sourceKey: key, slot: .objectID, encoding: .rawID)
    }
    private func anchored(_ text: AnyDestinationAnchoredText, owner: AnyDestinationReference? = nil,
                          type: String = "paragraph") -> AnyDestinationMigrationOperation {
        .anchoredEditorBlock(owner: owner ?? ref("owner"), dataset: "editor_blocks", type: type, text: text,
            style: .literal(.object([:])), parent: nil, position: "A")
    }
    private func plan(_ block: AnyDestinationMigrationOperation) throws -> AnyDestinationMigrationPlan {
        let source = try AnyDestinationSourceBinding(accountID: "source-account", spaceID: sourceSpace,
            witnessSHA256: String(repeating: "a", count: 64), captureManifestSHA256: String(repeating: "b", count: 64),
            semanticPlanSHA256: String(repeating: "c", count: 64), sourceObjectIDs: [sourceObject])
        let items: [AnyDestinationMigrationItem] = [
            .init(sourceKey: "owner", sourceObjectID: sourceObject, operation: .object(type: .native("page"),
                collections: [], initialProperties: .literal(.object([:])))),
            .init(sourceKey: "body", sourceObjectID: sourceObject, operation: block)
        ]
        return try .init(source: source, workspace: .init(accountID: "destination-account", spaceID: targetSpace),
            storeID: "destination-store", planID: String(repeating: "d", count: 64),
            coverage: [.init(sourceObjectID: sourceObject, disposition: .mapped(itemSourceKeys: items.map(\.sourceKey)))],
            items: items)
    }
    private func mark(_ kind: Int64, range: NSRange, parameter: String) -> AnyJSON {
        .object(["type": .integer(kind), "range": .object(["from": .integer(Int64(range.location)),
            "to": .integer(Int64(NSMaxRange(range)))]), "param": .string(parameter)])
    }
    private func snapshot(text: String, marks: [AnyJSON], style: Int64 = 0) throws -> AnyHeartNativeSnapshotView {
        let pb = Data("synthetic-native-anchor-source-control".utf8)
        let native: AnyJSON = .object(["blocks": .array([
            .object(["id": .string(sourceObject), "childrenIds": .array([.string("body")]), "smartblock": .object([:])]),
            .object(["id": .string("body"), "childrenIds": .array([]), "text": .object([
                "text": .string(text), "style": .integer(style), "marks": .object(["marks": .array(marks)])
            ])])
        ]), "details": .object([:]), "objectTypes": .array([]), "relationLinks": .array([])])
        let view: AnyJSON = .object(["Contract": .string("pinkha-native-snapshot-json-v1"),
            "SpaceID": .string(sourceSpace), "ObjectID": .string(sourceObject), "NativeType": .integer(16),
            "UniqueKey": .string(""), "SnapshotSHA256": .string(AnyContentDigest.sha256(pb)),
            "SnapshotBytes": .integer(Int64(pb.count)), "Snapshot": native])
        return try .init(jsonView: JSONEncoder().encode(view), snapshotBytes: pb,
                         sourceSpaceID: sourceSpace, sourceObjectID: sourceObject)
    }
}
