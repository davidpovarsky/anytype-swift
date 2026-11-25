import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativePageLayoutTests: XCTestCase {
    func testBoundHeaderPreservesTitlePropertiesAndTheOrderedBodyGraph() throws {
        let source = try snapshot()
        let layout = try AnyHeartNativePageLayout(snapshot: source)
        XCTAssertEqual(layout.title, "כותרת מקור 😀")
        XCTAssertEqual(layout.done, false)
        XCTAssertEqual(layout.featuredRelations, ["status", "tags"])
        XCTAssertEqual(layout.structuralBlockIDs, ["header", "title", "featured"])
        XCTAssertEqual(layout.bodyRootIDs, ["body", "after"])
        XCTAssertEqual(layout.bodyBlockIDs, ["body", "nested", "after"])
        XCTAssertEqual(layout.originalStructuralBlocks.map { $0["id"]?.string }, ["doc", "header", "title", "featured"])
        XCTAssertEqual(layout.originalPropertyBindings["presentDetails"], .object(source.details))
        XCTAssertFalse(layout.permitsDestinationWrites)
        XCTAssertThrowsError(try AnyHeartNativeTextBlockPlan(snapshot: source))
        let plan = try AnyHeartNativeTextBlockPlan(snapshot: source, pageLayout: layout)
        XCTAssertEqual(plan.entries.map(\.sourceBlockID), layout.bodyBlockIDs)
        XCTAssertEqual(plan.entries.map(\.text), ["גוף המקור", "nested", "last"])
        XCTAssertEqual(plan.entries[1].parentSourceKey, plan.entries[0].sourceKey)
        XCTAssertNil(plan.entries[2].parentSourceKey)
        XCTAssertEqual(plan.pageLayout?.contentSHA256, layout.contentSHA256)
        XCTAssertFalse(plan.permitsDestinationWrites)
        XCTAssertEqual(plan.contentSHA256, try AnyHeartNativeTextBlockPlan(snapshot: source,
            pageLayout: AnyHeartNativePageLayout(snapshot: source)).contentSHA256)
        let changed = try snapshot { _, details in details["name"] = .string("changed") }
        XCTAssertThrowsError(try AnyHeartNativeTextBlockPlan(snapshot: changed, pageLayout: layout))
    }

    func testMissingPropertiesAndUnsupportedHeaderSemanticsStayExplicit() throws {
        let absent = try AnyHeartNativePageLayout(snapshot: snapshot { _, details in details = [:] })
        XCTAssertNil(absent.title); XCTAssertNil(absent.done); XCTAssertNil(absent.featuredRelations)
        XCTAssertEqual(absent.originalPropertyBindings["presentDetails"], .object([:]))
        let changes: [(inout [AnyJSON], inout [String: AnyJSON]) -> Void] = [
            { _, details in details["name"] = .null },
            { _, details in details["done"] = .string("false") },
            { _, details in details["featuredRelations"] = .array([.string("same"), .string("same")]) },
            { rows, _ in Self.replace(&rows, index: 0, key: "childrenIds", value: .array([.string("body"), .string("header"), .string("after")])) },
            { rows, _ in Self.replace(&rows, index: 1, key: "layout", value: .object(["style": .integer(0)])) },
            { rows, _ in Self.replace(&rows, index: 1, key: "backgroundColor", value: .string("red")) },
            { rows, _ in Self.replace(&rows, index: 1, key: "restrictions", value: .object(["read": .bool(true)])) },
            { rows, _ in Self.replace(&rows, index: 4, key: "fields", value: .object(["_detailsKey": .array([.string("done"), .string("name")])])) },
            { rows, _ in
                var text = rows[4]["text"]!.object!; text["text"] = .string("unbound title")
                Self.replace(&rows, index: 4, key: "text", value: .object(text))
            },
            { rows, _ in Self.replace(&rows, index: 5, key: "featuredRelations", value: .object(["unknown": .bool(true)])) }
        ]
        for (index, change) in changes.enumerated() {
            XCTAssertThrowsError(try AnyHeartNativePageLayout(snapshot: snapshot(mutate: change)), "Unsupported mutation \(index)")
        }
    }

    func testOriginalNativePageProjectsItsBoundTitleAndBodyWithoutRewritingTheSnapshot() throws {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_NATIVE_CAPTURE_FIXTURE"] else {
            throw XCTSkip("An independently retained private native capture is required")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true).resolvingSymlinksInPath().standardizedFileURL
        func bytes(_ relative: String, under directory: URL) throws -> Data {
            let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
            guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
                  !parts.isEmpty, parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
                throw FixtureError.invalidPath
            }
            let file = directory.appendingPathComponent(relative).resolvingSymlinksInPath().standardizedFileURL
            guard file.path.hasPrefix(directory.path + "/"),
                  try file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else {
                throw FixtureError.invalidPath
            }
            return try Data(contentsOf: file)
        }
        let contextBytes = try bytes("fixture-context.json", under: root)
        guard AnyContentDigest.sha256(contextBytes) == "5357d52f5e76b604a40d7a5f2b1bc002e19bc864c419a45f90128bfa965d5850" else {
            throw FixtureError.changedOriginal
        }
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        let sample = try XCTUnwrap(context["nativeJSONSample"])
        let directory = root.appendingPathComponent("source-bundle", isDirectory: true)
        let pbPath = try XCTUnwrap(sample["protobufPath"]?.string)
        let jsonPath = try XCTUnwrap(sample["jsonPath"]?.string)
        let pb = try bytes(pbPath, under: directory), json = try bytes(jsonPath, under: directory)
        guard AnyContentDigest.sha256(pb) == sample["protobufSHA256"]?.string,
              AnyContentDigest.sha256(json) == sample["jsonSHA256"]?.string else {
            throw FixtureError.changedOriginal
        }
        let objectID = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: json)["ObjectID"]?.string)
        XCTAssertEqual(AnyContentDigest.sha256(Data(objectID.utf8)), sample["objectSHA256"]?.string)
        let source = try AnyHeartNativeSnapshotView(jsonView: json, snapshotBytes: pb,
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string), sourceObjectID: objectID)
        let layout = try AnyHeartNativePageLayout(snapshot: source)
        let plan = try AnyHeartNativeTextBlockPlan(snapshot: source, pageLayout: layout)
        XCTAssertTrue(layout.title == sample["expectedTitle"]?.string, "Original captured Unicode title changed")
        XCTAssertNil(layout.done); XCTAssertNil(layout.featuredRelations)
        XCTAssertEqual(layout.originalStructuralBlocks.count, 4)
        XCTAssertEqual(plan.entries.count, 1)
        XCTAssertTrue(plan.entries[0].sourceBlockID == sample["expectedTextBlockID"]?.string)
        XCTAssertTrue(plan.entries[0].text == sample["expectedText"]?.string, "Original visible Unicode body changed")
        XCTAssertEqual(plan.entries[0].type, "paragraph")
        XCTAssertNil(plan.entries[0].parentSourceKey)
        XCTAssertEqual(source.protobufBytes, pb); XCTAssertEqual(source.jsonViewBytes, json)
        XCTAssertEqual(try bytes(pbPath, under: directory), pb)
        XCTAssertEqual(try bytes(jsonPath, under: directory), json)
        XCTAssertFalse(plan.permitsDestinationWrites)
        print("NATIVE_PAGE_LAYOUT_VERIFIED structuralBlocks=4 bodyBlocks=1 titleBound=true absentDonePreserved=true rawBytesUnchanged=true destinationWrites=false layoutSHA256=\(layout.contentSHA256)")
    }

    private static func replace(_ rows: inout [AnyJSON], index: Int, key: String, value: AnyJSON) {
        var fields = rows[index].object!; fields[key] = value; rows[index] = .object(fields)
    }

    private func snapshot(mutate: (inout [AnyJSON], inout [String: AnyJSON]) -> Void = { _, _ in }) throws -> AnyHeartNativeSnapshotView {
        func block(_ id: String, children: [String] = [], kind: String, content: AnyJSON,
                   restrictions: [String: Bool]? = nil, fields: AnyJSON = .null) -> AnyJSON {
            .object(["id": .string(id), "childrenIds": .array(children.map(AnyJSON.string)),
                "backgroundColor": .string(""), "align": .integer(0), "verticalAlign": .integer(0),
                "fields": fields, "restrictions": restrictions.map { .object($0.mapValues(AnyJSON.bool)) } ?? .null,
                kind: content])
        }
        func text(_ string: String, style: Int64 = 0) -> AnyJSON {
            .object(["text": .string(string), "style": .integer(style), "checked": .bool(false),
                "marks": .object(["marks": .array([])]), "color": .string(""),
                "iconEmoji": .string(""), "iconImage": .string("")])
        }
        let protected = ["drag": true, "dropOn": true, "edit": false, "read": false, "remove": true]
        var rows = [
            block("doc", children: ["header", "body", "after"], kind: "smartblock", content: .object([:]),
                  restrictions: ["drag": false, "dropOn": false, "edit": false, "read": false, "remove": false]),
            block("header", children: ["title", "featured"], kind: "layout", content: .object(["style": .integer(3)]),
                  restrictions: ["drag": true, "dropOn": true, "edit": true, "read": false, "remove": true]),
            block("body", children: ["nested"], kind: "text", content: text("גוף המקור")),
            block("after", kind: "text", content: text("last")),
            block("title", kind: "text", content: text("", style: 7), restrictions: protected,
                  fields: .object(["_detailsKey": .array([.string("name"), .string("done")])])),
            block("featured", kind: "featuredRelations", content: .object([:]), restrictions: protected),
            block("nested", kind: "text", content: text("nested"))
        ]
        var details: [String: AnyJSON] = ["name": .string("כותרת מקור 😀"), "done": .bool(false),
            "featuredRelations": .array([.string("status"), .string("tags")])]
        mutate(&rows, &details)
        let pb = Data([0x0a, 0x00])
        let native: AnyJSON = .object(["blocks": .array(rows), "details": .object(details),
            "objectTypes": .array([.string("ot-page")]), "relationLinks": .array([])])
        let envelope: AnyJSON = .object(["Contract": .string("pinkha-native-snapshot-json-v1"),
            "SpaceID": .string("space"), "ObjectID": .string("doc"), "NativeType": .integer(16),
            "UniqueKey": .string(""), "SnapshotSHA256": .string(AnyContentDigest.sha256(pb)),
            "SnapshotBytes": .integer(Int64(pb.count)), "Snapshot": native])
        return try .init(jsonView: JSONEncoder().encode(envelope), snapshotBytes: pb,
                         sourceSpaceID: "space", sourceObjectID: "doc")
    }

    private enum FixtureError: Error { case invalidPath, changedOriginal }
}
