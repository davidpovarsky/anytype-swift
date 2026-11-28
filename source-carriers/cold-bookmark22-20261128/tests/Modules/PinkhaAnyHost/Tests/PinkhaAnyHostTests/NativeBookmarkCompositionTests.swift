import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// These are explicit synthetic PB/JSON semantic controls, never a captured
/// original Bookmark or native destination/source-authority acceptance.
final class NativeBookmarkCompositionTests: XCTestCase {
    func testBoundBookmarkHeaderKeepsDescriptionAndOrderedBodySeparate() throws {
        let source = try bookmark("first", other: "second")
        let layout = try AnyHeartNativeBookmarkLayout(snapshot: source)
        let body = try AnyHeartNativeTextBlockPlan(snapshot: source, bookmarkLayout: layout)
        XCTAssertEqual(layout.structuralBlockIDs, ["first-header", "first-title", "first-description", "first-featured"])
        XCTAssertEqual(layout.originalStructuralBlocks.count, 5)
        XCTAssertEqual(layout.bodyBlockIDs, ["first-body", "first-nested"])
        XCTAssertEqual(layout.bodyRootIDs, ["first-body"])
        XCTAssertEqual(layout.featuredRelations, ["description"])
        XCTAssertEqual(layout.structuralDetailKeys, ["featuredRelations"])
        XCTAssertEqual(layout.title, "כותרת first")
        XCTAssertEqual(layout.description, "תיאור first — a\u{301}")
        XCTAssertEqual(Data(try XCTUnwrap(layout.sourceURL).utf8),
                       Data("HTTPS://Example.test:443/a%2fb?x=1&x=2#שָׁלוֹם".utf8))
        XCTAssertEqual(body.entries.map(\.sourceBlockID), layout.bodyBlockIDs)
        XCTAssertNil(body.entries[0].parentSourceKey)
        XCTAssertEqual(body.entries[1].parentSourceKey, body.entries[0].sourceKey)
        XCTAssertFalse(body.entries.contains { $0.text == layout.title || $0.text == layout.description })
        XCTAssertNil(body.pageLayout)
        XCTAssertEqual(body.bookmarkLayout?.contentSHA256, layout.contentSHA256)
        XCTAssertFalse(layout.permitsDestinationWrites)
        XCTAssertFalse(body.permitsDestinationWrites)
        XCTAssertEqual(try AnyHeartNativeBookmarkLayout(snapshot: source).contentSHA256, layout.contentSHA256)
        XCTAssertThrowsError(try AnyHeartNativePageLayout(snapshot: source),
                             "A Bookmark description header is not a basic Page header")
    }

    func testBookmarkCompositionKeepsExactURLAndDistinctReferenceCycles() throws {
        let definitions = try self.definitions()
        XCTAssertTrue(definitions.issues.isEmpty)
        XCTAssertFalse(try definitions.admittedSchemaItems().isEmpty)
        let snapshots = try [bookmark("first", other: "second"), bookmark("second", other: "first")]
        let objects = bindings(snapshots)
        let first = try AnyHeartNativeBookmarkComposition(snapshot: snapshots[0], definitions: definitions, objects: objects)
        let second = try AnyHeartNativeBookmarkComposition(snapshot: snapshots[1], definitions: definitions, objects: objects)
        XCTAssertNotEqual(first.sourceKey, second.sourceKey, "Equal source URLs must not merge source object identities")
        XCTAssertEqual(first.sourceKey, AnyHeartNativePageComposition.objectSourceKey(spaceID: "source-space", objectID: "first"))
        XCTAssertEqual(first.body.entries.count, 2)
        XCTAssertEqual(first.items.count, 4)
        XCTAssertTrue(Set(first.presentDetailKeys) == Set(snapshots[0].details.keys))
        let groups = try first.values.initialProperties.resolved(resolve)
        XCTAssertEqual(groups["any"]?["name"], snapshots[0].details["name"])
        XCTAssertEqual(groups["any"]?["description"], snapshots[0].details["description"])
        let url = try XCTUnwrap(definitions.property(sourceKey: "source"))
        let owner = try resolve(url.owner)
        let actualURL = try XCTUnwrap(groups[owner]?[try resolve(url.record)]?.string)
        XCTAssertEqual(Data(actualURL.utf8), Data(try XCTUnwrap(first.layout.sourceURL).utf8))
        for (key, expected) in [("done", AnyJSON.bool(false)), ("count", .integer(0)), ("empty", .string(""))] {
            let property = try XCTUnwrap(definitions.property(sourceKey: key))
            XCTAssertEqual(groups[try resolve(property.owner)]?[try resolve(property.record)], expected)
        }
        let reference = try XCTUnwrap(definitions.property(sourceKey: "other"))
        XCTAssertEqual(first.values.deferredGroups.count, 1)
        let patch = try first.values.deferredGroups[0].fields.resolved(resolve)
        XCTAssertEqual(patch[try resolve(reference.record)], .array([.string("any://" + second.sourceKey)]))
        let reverse = try second.values.deferredGroups[0].fields.resolved(resolve)
        XCTAssertEqual(reverse[try resolve(reference.record)], .array([.string("any://" + first.sourceKey)]))
        guard case .object(let type, let collections, _) = first.items[0].operation else {
            return XCTFail("The source identity must be created before its body and reference writes")
        }
        XCTAssertEqual(type, try XCTUnwrap(definitions.type(sourceURL: "ot-bookmark")).object)
        XCTAssertEqual(collections, [try XCTUnwrap(definitions.propertyOwner)])
        XCTAssertFalse(first.values.initialRelationKeys.contains("featuredRelations"))
        XCTAssertThrowsError(try first.admittedCurrentItems(), "Detached controls cannot authorize source execution")
        XCTAssertFalse(first.permitsDestinationWrites)
        XCTAssertEqual(try AnyHeartNativeBookmarkComposition(snapshot: snapshots[0],
            definitions: definitions, objects: objects).contentSHA256, first.contentSHA256)
    }

    func testBodylessBookmarkPreservesAbsentAndExplicitEmptyDescriptionAndURL() throws {
        let definitions = try self.definitions()
        let absent = try bookmark("absent", other: nil, body: false) { details, _ in
            _ = details.removeValue(forKey: "description")
            _ = details.removeValue(forKey: "featuredRelations")
            details["source"] = .string("")
        }
        let empty = try bookmark("empty", other: nil, body: false) { details, _ in
            details["description"] = .string("")
            details["source"] = .string("")
        }
        for source in [absent, empty] {
            let plan = try AnyHeartNativeBookmarkComposition(snapshot: source, definitions: definitions, objects: bindings([source]))
            XCTAssertTrue(plan.body.entries.isEmpty)
            XCTAssertEqual(plan.items.count, 1, "No empty editor block or fetched preview is synthesized")
            let fields = try plan.values.initialProperties.resolved(resolve)
            if source.sourceObjectID == "absent" {
                XCTAssertNil(fields["any"]?["description"])
                XCTAssertNil(plan.layout.featuredRelations)
            } else {
                XCTAssertEqual(fields["any"]?["description"], .string(""))
                XCTAssertEqual(plan.layout.featuredRelations, ["description"])
            }
            let url = try XCTUnwrap(definitions.property(sourceKey: "source"))
            XCTAssertEqual(fields[try resolve(url.owner)]?[try resolve(url.record)], .string(""))
            XCTAssertThrowsError(try plan.admittedCurrentItems())
        }
    }

    func testChangedHeaderBindingsAndObjectSpecificFeaturedOverridesAreRefused() throws {
        let changes: [(inout [String: AnyJSON], inout [String: AnyJSON]) -> Void] = [
            { _, raw in Self.changeBlock(&raw, index: 1, field: "childrenIds",
                value: .array([.string("bad-title"), .string("bad-featured"), .string("bad-description")])) },
            { _, raw in Self.changeBlock(&raw, index: 3, field: "fields",
                value: .object(["_detailsKey": .array([.string("description")])])) },
            { _, raw in Self.changeText(&raw, index: 3, field: "style", value: .integer(7)) },
            { _, raw in Self.changeText(&raw, index: 3, field: "text", value: .string("independent body text")) },
            { _, raw in Self.changeText(&raw, index: 3, field: "color", value: .string("red")) },
            { _, raw in Self.changeBlock(&raw, index: 3, field: "align", value: .integer(1)) },
            { details, _ in details["featuredRelations"] = .array([]) },
            { details, _ in details["featuredRelations"] = .array([.string("source"), .string("description")]) },
            { details, _ in details["description"] = .null },
            { details, _ in details["source"] = .integer(1) },
            { details, _ in details["done"] = .string("false") }
        ]
        for (index, mutate) in changes.enumerated() {
            let source = try bookmark("bad", other: nil, mutate: mutate)
            XCTAssertThrowsError(try AnyHeartNativeBookmarkLayout(snapshot: source), "header mutation \(index)")
        }
    }

    func testBookmarkNeverDropsUnsupportedDetailsMetadataOrBody() throws {
        let definitions = try self.definitions()
        let changes: [(inout [String: AnyJSON], inout [String: AnyJSON]) -> Void] = [
            { details, _ in details["unknown"] = .string("retained, not ignored") },
            { details, _ in _ = details.removeValue(forKey: "name") },
            { details, _ in _ = details.removeValue(forKey: "source") },
            { _, raw in raw["fileInfo"] = .object(["retained": .bool(true)]) },
            { _, raw in raw["originalCreatedTimestamp"] = .string("123") },
            { _, raw in raw["objectTypes"] = .array([.string("ot-bookmark"), .string("ot-other")]) },
            { _, raw in raw["relationLinks"] = .array([.object(["key": .string("source"), "format": .integer(1)])]) },
            { _, raw in
                var blocks = raw["blocks"]!.array!
                var body = blocks[5].object!
                body.removeValue(forKey: "text")
                body["bookmark"] = .object(["url": .string("https://unmapped.example")])
                blocks[5] = .object(body); raw["blocks"] = .array(blocks)
            }
        ]
        for (index, mutate) in changes.enumerated() {
            let source = try bookmark("refuse", other: nil, mutate: mutate)
            XCTAssertThrowsError(try AnyHeartNativeBookmarkComposition(snapshot: source,
                definitions: definitions, objects: bindings([source])), "unrepresented mutation \(index)")
        }
    }

    func testExactTypeCanonicalDescriptionAndReferenceIdentityRemainMandatory() throws {
        let source = try bookmark("first", other: "second")
        let target = try bookmark("second", other: nil)
        let objects = bindings([source, target])
        let basic = try definitions(layout: 0)
        XCTAssertTrue(basic.issues.isEmpty)
        XCTAssertThrowsError(try AnyHeartNativeBookmarkComposition(snapshot: source, definitions: basic, objects: objects))
        XCTAssertThrowsError(try AnyHeartNativeBookmarkComposition(snapshot: source,
            definitions: definitions(descriptionUniqueKey: "rel-custom-description"), objects: objects))
        let exact = try definitions()
        var missing = bindings([source])
        XCTAssertThrowsError(try AnyHeartNativeBookmarkComposition(snapshot: source, definitions: exact, objects: missing))
        missing.append(.init(sourceObjectID: target.sourceObjectID, destinationSourceKey: missing[0].destinationSourceKey))
        XCTAssertThrowsError(try AnyHeartNativeBookmarkComposition(snapshot: source, definitions: exact, objects: missing))
        let composed = AnyHeartNativeBookmarkComposition.objectSourceKey(spaceID: "space", objectID: "\u{00E9}")
        let decomposed = AnyHeartNativeBookmarkComposition.objectSourceKey(spaceID: "space", objectID: "e\u{301}")
        XCTAssertNotEqual(composed, decomposed)
        let layout = try AnyHeartNativeBookmarkLayout(snapshot: source)
        XCTAssertThrowsError(try AnyHeartNativeTextBlockPlan(snapshot: target, bookmarkLayout: layout))
    }

    private func resolve(_ reference: AnyDestinationReference) throws -> String {
        switch reference {
        case .native(let id): return id
        case .mapped(let key, _, let encoding): return encoding == .anyURI ? "any://" + key : key
        }
    }

    private func bindings(_ snapshots: [AnyHeartNativeSnapshotView]) -> [AnyHeartNativeDefinitionPlan.ObjectBinding] {
        snapshots.map { .init(sourceObjectID: $0.sourceObjectID,
            destinationSourceKey: AnyHeartNativeBookmarkComposition.objectSourceKey(
                spaceID: $0.sourceSpaceID, objectID: $0.sourceObjectID)) }
    }

    private func definitions(layout: Int64 = 11, descriptionUniqueKey: String = "rel-description") throws
        -> AnyHeartNativeDefinitionPlan {
        var rows: [AnyHeartNativeSnapshotView] = []
        let relations: [(String, Int64)] = [("name", 1), ("description", 0), ("source", 7),
                                            ("other", 100), ("done", 6), ("count", 2), ("empty", 0)]
        for (key, format) in relations {
            let canonical = key == "name" || key == "description"
            let name = key == "name" ? "Name" : (key == "description" ? "Description" : key)
            let description = key == "name" ? "Name of the object" : ""
            rows.append(try snapshot(id: "relation-" + key, type: 521,
                key: key == "description" ? descriptionUniqueKey : "rel-" + key,
                raw: .object(["blocks": .array([]), "objectTypes": .array([]), "relationLinks": .array([]),
                    "details": .object(["name": .string(name), "description": .string(description),
                        "relationKey": .string(key), "relationFormat": .integer(format),
                        "relationDefaultValue": .null, "relationReadonlyValue": .bool(false),
                        "relationMaxCount": .integer(canonical || key == "source" ? 1 : 0),
                        "relationFormatIncludeTime": .bool(false), "relationFormatObjectTypes": .array([]),
                        "isHidden": .bool(canonical)])])))
        }
        rows.append(try snapshot(id: "bookmark-type", type: 528, key: "ot-bookmark",
            raw: .object(["blocks": .array([]), "objectTypes": .array([]), "relationLinks": .array([]),
                "details": .object(["name": .string("Bookmark"), "recommendedLayout": .integer(layout),
                    "recommendedRelations": .array([.string("relation-name"), .string("relation-source")]),
                    "recommendedFeaturedRelations": .array([.string("relation-description"), .string("relation-source")]),
                    "recommendedHiddenRelations": .array([]), "recommendedFileRelations": .array([])])])))
        return try .init(catalog: .init(sourceAccountID: "source-account", sourceSpaceID: "source-space",
            captureManifestSHA256: String(repeating: "a", count: 64),
            sourceWitnessSHA256: String(repeating: "b", count: 64), snapshots: rows))
    }

    private func bookmark(_ id: String, other: String?, body: Bool = true,
                          mutate: (inout [String: AnyJSON], inout [String: AnyJSON]) -> Void = { _, _ in }) throws
        -> AnyHeartNativeSnapshotView {
        func block(_ suffix: String, children: [String] = [], kind: String, value: AnyJSON,
                   restrictions: [String: Bool]? = nil, fields: AnyJSON = .null) -> AnyJSON {
            .object(["id": .string(suffix.isEmpty ? id : id + suffix),
                "childrenIds": .array(children.map { .string(id + $0) }), "fields": fields,
                "backgroundColor": .string(""), "align": .integer(0), "verticalAlign": .integer(0),
                "restrictions": restrictions.map { .object($0.mapValues(AnyJSON.bool)) } ?? .null, kind: value])
        }
        func text(_ value: String, style: Int64 = 0) -> AnyJSON {
            .object(["text": .string(value), "style": .integer(style), "checked": .bool(false),
                "marks": .object(["marks": .array([])]), "color": .string(""),
                "iconEmoji": .string(""), "iconImage": .string("")])
        }
        let protected = ["drag": true, "dropOn": true, "edit": false, "read": false, "remove": true]
        var blocks = [
            block("", children: body ? ["-header", "-body"] : ["-header"], kind: "smartblock", value: .object([:]),
                restrictions: ["drag": false, "dropOn": false, "edit": false, "read": false, "remove": false]),
            block("-header", children: ["-title", "-description", "-featured"], kind: "layout", value: .object(["style": .integer(3)]),
                restrictions: ["drag": true, "dropOn": true, "edit": true, "read": false, "remove": true]),
            block("-title", kind: "text", value: text("", style: 7), restrictions: protected,
                fields: .object(["_detailsKey": .array([.string("name"), .string("done")])])),
            block("-description", kind: "text", value: text("", style: 12), restrictions: protected,
                fields: .object(["_detailsKey": .string("description")])),
            block("-featured", kind: "featuredRelations", value: .object([:]), restrictions: protected)
        ]
        if body {
            blocks.append(block("-body", children: ["-nested"], kind: "text", value: text("גוף \(id)")))
            blocks.append(block("-nested", kind: "text", value: text("המשך \(id) 😀", style: 5)))
        }
        var details: [String: AnyJSON] = ["name": .string("כותרת \(id)"),
            "description": .string("תיאור \(id) — a\u{301}"),
            "source": .string("HTTPS://Example.test:443/a%2fb?x=1&x=2#שָׁלוֹם"),
            "done": .bool(false), "count": .integer(0), "empty": .string(""),
            "featuredRelations": .array([.string("description")])]
        if let other { details["other"] = .array([.string(other)]) }
        var raw: [String: AnyJSON] = ["blocks": .array(blocks), "objectTypes": .array([.string("ot-bookmark")]),
            "relationLinks": .array([.object(["key": .string("name"), "format": .integer(1)]),
                                    .object(["key": .string("description"), "format": .integer(0)]),
                                    .object(["key": .string("source"), "format": .integer(7)])]),
            "key": .string(""), "originalCreatedTimestamp": .string("0")]
        mutate(&details, &raw); raw["details"] = .object(details)
        return try snapshot(id: id, type: 16, key: "page", raw: .object(raw))
    }

    private func snapshot(id: String, type: Int64, key: String, raw: AnyJSON) throws -> AnyHeartNativeSnapshotView {
        let pb = Data("synthetic-bookmark-composition-control:\(id)".utf8)
        let envelope: AnyJSON = .object(["Contract": .string("pinkha-native-snapshot-json-v1"),
            "SpaceID": .string("source-space"), "ObjectID": .string(id), "NativeType": .integer(type),
            "UniqueKey": .string(key), "SnapshotSHA256": .string(AnyContentDigest.sha256(pb)),
            "SnapshotBytes": .integer(Int64(pb.count)), "Snapshot": raw])
        return try .init(jsonView: JSONEncoder().encode(envelope), snapshotBytes: pb,
                         sourceSpaceID: "source-space", sourceObjectID: id)
    }

    private static func changeBlock(_ raw: inout [String: AnyJSON], index: Int, field: String, value: AnyJSON) {
        var rows = raw["blocks"]!.array!, fields = rows[index].object!
        fields[field] = value; rows[index] = .object(fields); raw["blocks"] = .array(rows)
    }

    private static func changeText(_ raw: inout [String: AnyJSON], index: Int, field: String, value: AnyJSON) {
        var rows = raw["blocks"]!.array!, fields = rows[index].object!, text = fields["text"]!.object!
        text[field] = value; fields["text"] = .object(text); rows[index] = .object(fields); raw["blocks"] = .array(rows)
    }
}
