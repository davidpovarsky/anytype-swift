import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Synthetic native JSON/PB bindings. Actual native producer equivalence and
/// full Space coverage remain independent acceptance requirements.
final class NativeTextBlockPlanTests: XCTestCase {
    private func text(_ id: String, style: Int64 = 0, children: [String] = [],
                      value: String = "מקור", fields: AnyJSON = .null) -> AnyJSON {
        .object(["id": .string(id), "childrenIds": .array(children.map(AnyJSON.string)),
            "fields": fields, "restrictions": .null, "backgroundColor": .string(""),
            "align": .integer(0), "verticalAlign": .integer(0),
            "text": .object(["text": .string(value), "style": .integer(style), "marks": .null,
                "checked": .bool(style == 8), "color": .string(""),
                "iconEmoji": .string(""), "iconImage": .string("")])])
    }
    private func snapshot(_ rows: [AnyJSON], roots: [String]? = nil) throws -> AnyHeartNativeSnapshotView {
        let pb = Data([0x0a, 0x00])
        let root: AnyJSON = .object(["id": .string("doc"), "childrenIds": .array(
            (roots ?? rows.map { $0["id"]!.string! }).map(AnyJSON.string)), "smartblock": .object([:])])
        let native: AnyJSON = .object(["blocks": .array([root] + rows),
            "details": .object([:]), "objectTypes": .array([]), "relationLinks": .array([])])
        let view: AnyJSON = .object(["Contract": .string("pinkha-native-snapshot-json-v1"),
            "SpaceID": .string("space"), "ObjectID": .string("doc"), "NativeType": .integer(16),
            "UniqueKey": .string(""), "SnapshotSHA256": .string(AnyContentDigest.sha256(pb)),
            "SnapshotBytes": .integer(Int64(pb.count)), "Snapshot": native])
        return try .init(jsonView: JSONEncoder().encode(view), snapshotBytes: pb,
                         sourceSpaceID: "space", sourceObjectID: "doc")
    }

    func testNineNativeTextStylesAndOriginalMetadataArePreservedInTheMappedPlan() throws {
        let styles: [Int64] = [0, 1, 2, 3, 5, 6, 8, 9, 10]
        let rows = styles.map { style in
            text("b-\(style)", style: style, value: "literal [עברית] 😀",
                 fields: style == 6 ? .object(["lang": .string("swift")]) : .null)
        }
        let view = try snapshot(rows), plan = try AnyHeartNativeTextBlockPlan(snapshot: view)
        XCTAssertEqual(plan.entries.map(\.type), ["paragraph", "heading", "heading", "heading", "quote", "code",
                                                 "check_list_item", "list_item", "list_item"])
        XCTAssertEqual(plan.entries[5].text, "literal [עברית] 😀")
        XCTAssertEqual(plan.entries[5].style["lang"], .string("swift"))
        XCTAssertEqual(plan.entries[6].style["checked"], .bool(true))
        XCTAssertEqual(plan.entries[7].style["ordered"], .bool(false))
        XCTAssertEqual(plan.entries[8].style["number"], .integer(1))
        XCTAssertEqual(plan.entries.map(\.originalNative), rows)
        XCTAssertEqual(plan.snapshotSHA256, view.snapshotSHA256)
        XCTAssertEqual(plan.viewSHA256, view.viewSHA256)
        XCTAssertEqual(plan.contentSHA256, try AnyHeartNativeTextBlockPlan(snapshot: view).contentSHA256)
    }

    func testNativeGraphOrderAndMappedParentReferencesSurviveTheDestinationPlan() throws {
        let source = try snapshot([
            text("child", value: "nested"), text("last", style: 10),
            text("parent", style: 10, children: ["child"]), text("middle", style: 10)
        ], roots: ["parent", "middle", "last"])
        let textPlan = try AnyHeartNativeTextBlockPlan(snapshot: source)
        XCTAssertEqual(textPlan.entries.map(\.sourceBlockID), ["parent", "child", "middle", "last"])
        XCTAssertEqual(textPlan.entries[1].parentSourceKey, textPlan.entries[0].sourceKey)
        XCTAssertEqual([0, 2, 3].map { textPlan.entries[$0].style["number"] }, [.integer(1), .integer(2), .integer(3)])
        XCTAssertTrue(textPlan.entries[0].position < textPlan.entries[2].position)
        XCTAssertTrue(textPlan.entries[2].position < textPlan.entries[3].position)
        let root = AnyDestinationMigrationItem(sourceKey: "new-doc", sourceObjectID: "doc",
            operation: .object(type: .native("test-native-type"), collections: [], initialProperties: .literal(.object([:]))))
        let items = [root] + textPlan.destinationItems(ownerSourceKey: root.sourceKey)
        let sourceBinding = try AnyDestinationSourceBinding(accountID: "account", spaceID: "space",
            witnessSHA256: String(repeating: "a", count: 64), captureManifestSHA256: String(repeating: "b", count: 64),
            semanticPlanSHA256: textPlan.contentSHA256, sourceObjectIDs: ["doc"])
        let plan = try AnyDestinationMigrationPlan(source: sourceBinding,
            workspace: .init(accountID: "destination-account", spaceID: "destination-space"), storeID: "native-store",
            planID: "fixture-plan", coverage: [.init(sourceObjectID: "doc", disposition: .mapped(itemSourceKeys: items.map(\.sourceKey)))], items: items)
        let copy = try AnyDestinationMigrationPlan.decode(JSONEncoder().encode(plan))
        XCTAssertEqual(copy.binding.planSHA256, plan.binding.planSHA256)
        guard case .editorBlock(_, _, _, _, _, let parent, _) = copy.items[2].operation else {
            return XCTFail("Expected the native child block")
        }
        XCTAssertEqual(parent, .mapped(sourceKey: textPlan.entries[0].sourceKey, slot: .record(index: 0), encoding: .rawID))
    }

    func testUnknownContentMetadataAndDisconnectedBlocksCannotDisappear() throws {
        var row = text("a").object!
        row["align"] = .integer(2)
        XCTAssertThrowsError(try AnyHeartNativeTextBlockPlan(snapshot: snapshot([.object(row)])))
        row = text("a").object!; row["fields"] = .object(["unmapped": .string("preserve")])
        XCTAssertThrowsError(try AnyHeartNativeTextBlockPlan(snapshot: snapshot([.object(row)])))
        row = text("a").object!; row["text"] = nil; row["layout"] = .object(["style": .integer(1)])
        XCTAssertThrowsError(try AnyHeartNativeTextBlockPlan(snapshot: snapshot([.object(row)])))
        for style in [Int64(4), 7, 11, 12, 13, 14, 15, 16, 999] {
            XCTAssertThrowsError(try AnyHeartNativeTextBlockPlan(snapshot: snapshot([text("a", style: style)])))
        }
        let disconnected = try snapshot([text("visible"), text("orphan")], roots: ["visible"])
        XCTAssertThrowsError(try AnyHeartNativeTextBlockPlan(snapshot: disconnected))
        row = text("a").object!; var content = row["text"]!.object!
        content["futureValue"] = .null; row["text"] = .object(content)
        XCTAssertThrowsError(try AnyHeartNativeTextBlockPlan(snapshot: snapshot([.object(row)])))
    }
}
