import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Parser controls use synthetic wire inputs. Native producer provenance is
/// checked separately with the original captured protobuf/JSON fixture pair.
final class NativeSnapshotViewTests: XCTestCase {
    private let sourceBytes = Data([0x0a, 0x00, 0x2a, 0x00])

    private func block(_ id: String, children: [String] = [], text: String? = nil,
                       marks: [AnyJSON] = [], extra: [String: AnyJSON] = [:]) -> AnyJSON {
        var row: [String: AnyJSON] = ["id": .string(id), "childrenIds": .array(children.map(AnyJSON.string)),
            "fields": .null, "restrictions": .null, "align": .integer(0),
            "verticalAlign": .integer(0), "backgroundColor": .string("")]
        if let text {
            row["text"] = .object(["text": .string(text), "style": .integer(0),
                "marks": .object(["marks": .array(marks)]), "checked": .bool(false),
                "color": .string(""), "iconEmoji": .string(""), "iconImage": .string("")])
        } else { row["smartblock"] = .object([:]) }
        row.merge(extra) { _, incoming in incoming }
        return .object(row)
    }

    private func mark(_ kind: Int64, _ from: Int64, _ to: Int64, parameter: String = "") -> AnyJSON {
        .object(["type": .integer(kind), "range": .object(["from": .integer(from), "to": .integer(to)]),
                 "param": .string(parameter)])
    }

    private func view(_ blocks: [AnyJSON], extra: [String: AnyJSON] = [:],
                      rootExtra: [String: AnyJSON] = [:]) throws -> Data {
        var snapshot: [String: AnyJSON] = ["blocks": .array(blocks), "details": .object(["name": .string("מקור")]),
            "objectTypes": .array([.string("ot-page")]), "relationLinks": .array([]),
            "fileKeys": .null, "extraRelations": .array([]), "collections": .null,
            "removedCollectionKeys": .array([]), "key": .string(""),
            "originalCreatedTimestamp": .string("1795540000"), "fileInfo": .null]
        snapshot.merge(extra) { _, incoming in incoming }
        var envelope: [String: AnyJSON] = ["Contract": .string("pinkha-native-snapshot-json-v1"),
            "SpaceID": .string("space"), "ObjectID": .string("doc"), "NativeType": .integer(16),
            "UniqueKey": .string(""), "SnapshotSHA256": .string(AnyContentDigest.sha256(sourceBytes)),
            "SnapshotBytes": .integer(Int64(sourceBytes.count)), "Snapshot": .object(snapshot)]
        envelope.merge(rootExtra) { _, incoming in incoming }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(AnyJSON.object(envelope))
    }

    private func read(_ bytes: Data, protobuf: Data? = nil, space: String = "space") throws -> AnyHeartNativeSnapshotView {
        try .init(jsonView: bytes, snapshotBytes: protobuf ?? sourceBytes,
                  sourceSpaceID: space, sourceObjectID: "doc")
    }

    func testNativeVisibleTextAndUTF16MarksDoNotReparseExportSyntax() throws {
        let text = "**literal** א😀ב"
        let range = (text as NSString).range(of: "א😀ב")
        let bytes = try view([block("doc", children: ["text"]),
            block("text", text: text, marks: [mark(3, Int64(range.location), Int64(NSMaxRange(range)))])])
        let snapshot = try read(bytes)
        let inline = try XCTUnwrap(snapshot.blocks.first { $0.id == "text" }).inlineProjection()
        XCTAssertEqual(inline.text, text)
        XCTAssertEqual(inline.marks[0].range, range)
        let converted = try AnyHeartInlineConversion(inline)
        XCTAssertEqual(Array(AnyInlineMarkdown(converted.inlineMarkdown).display.utf8), Array(text.utf8))
        XCTAssertEqual(snapshot.protobufBytes, sourceBytes)
        XCTAssertEqual(snapshot.jsonViewBytes, bytes)
    }

    func testGraphUsesNativeChildOrderAndRejectsCyclesAndMultipleParents() throws {
        let snapshot = try read(view([block("b", text: "B"), block("nested", text: "N"),
            block("doc", children: ["a", "b"]), block("a", children: ["nested"], text: "A")]))
        XCTAssertEqual(snapshot.depthFirstIDs, ["doc", "a", "nested", "b"])
        XCTAssertEqual(snapshot.blocks.first { $0.id == "nested" }?.parentID, "a")
        XCTAssertThrowsError(try read(view([block("doc", children: ["a"]), block("a", children: ["doc"], text: "A")])))
        XCTAssertThrowsError(try read(view([block("doc", children: ["a", "b"]),
            block("a", children: ["b"], text: "A"), block("b", text: "B")])))
        XCTAssertThrowsError(try read(view([block("doc"), block("a", children: ["b"], text: "A"),
            block("b", children: ["a"], text: "B")])))
    }

    func testHashScopeAndNativeIdentityBindingsCannotBeSubstituted() throws {
        let bytes = try view([block("doc")])
        XCTAssertThrowsError(try read(bytes, protobuf: sourceBytes + Data([1])))
        XCTAssertThrowsError(try read(bytes, space: "other-space"))
        XCTAssertThrowsError(try read(view([block("doc")], rootExtra: ["ObjectID": .string("other")])))
        XCTAssertThrowsError(try read(view([block("doc")], rootExtra: ["SnapshotBytes": .integer(1)])))
        XCTAssertThrowsError(try read(view([block("doc")], rootExtra: ["SnapshotSHA256": .string(String(repeating: "0", count: 64))])))
    }

    func testSurrogateSplitsUnknownMarkKindsAndCodeMarksRefuseConversion() throws {
        let invalid = try read(view([block("doc", children: ["t"]), block("t", text: "א😀ב", marks: [mark(3, 1, 2)])]))
        XCTAssertThrowsError(try XCTUnwrap(invalid.blocks.first { $0.id == "t" }).inlineProjection())
        let unknown = try read(view([block("doc", children: ["t"]), block("t", text: "abc", marks: [mark(999, 0, 2)])]))
        XCTAssertThrowsError(try XCTUnwrap(unknown.blocks.first { $0.id == "t" }).inlineProjection())
        let emoji = try read(view([block("doc", children: ["t"]), block("t", text: "abc", marks: [mark(9, 0, 2, parameter: "native")])]))
        let projection = try XCTUnwrap(emoji.blocks.first { $0.id == "t" }).inlineProjection()
        XCTAssertEqual(projection.marks[0].kind, .emoji)
        XCTAssertThrowsError(try AnyHeartInlineConversion(projection))
        let code: AnyJSON = .object(["text": .string("code"), "style": .integer(6),
            "marks": .object(["marks": .array([mark(3, 0, 2)])])])
        let markedCode = try read(view([block("doc", children: ["t"]), block("t", text: "code", extra: ["text": code])]))
        XCTAssertThrowsError(try XCTUnwrap(markedCode.blocks.first { $0.id == "t" }).inlineProjection())
    }

    func testUnknownFieldsAndUnreachableRowsRemainExplicitAndRetained() throws {
        let future: AnyJSON = .object(["exact": .string("retained")])
        let snapshot = try read(view([block("doc"), block("orphan", text: "hidden", extra: ["future": future])],
                                     extra: ["futureSnapshot": future]))
        XCTAssertEqual(snapshot.blocks.count, 2)
        XCTAssertEqual(snapshot.rawSnapshot["futureSnapshot"], future)
        XCTAssertEqual(snapshot.blocks.first { $0.id == "orphan" }?.raw["future"], future)
        XCTAssertEqual(Set(snapshot.issues.map(\.kind.rawValue)), ["unknownSnapshotField", "unknownBlockField", "unreachableBlock"])
    }

    func testCanonicallyEquivalentNativeIDsCannotAlias() throws {
        let composed = "é", decomposed = "e\u{301}"
        XCTAssertEqual(composed, decomposed)
        XCTAssertNotEqual(Data(composed.utf8), Data(decomposed.utf8))
        XCTAssertThrowsError(try read(view([block("doc", children: [composed, decomposed]),
                                           block(composed, text: "first"), block(decomposed, text: "second")])))
    }
}
