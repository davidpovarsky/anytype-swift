import Foundation
import SwiftProtobuf
import XCTest
@testable import ProtobufMessages

enum HeartCaptureFixture {
    struct Request: Decodable {
        struct Snapshot: Decodable {
            struct Mark: Decodable { let from: Int32; let to: Int32; let kind: Int32; let param: String }
            let text: String
            let marks: [Mark]
        }
        let spaceID: String
        let objectID: String
        let blockID: String
        let anchorID: String
        let from: Int32
        let to: Int32
        let expected: Snapshot
    }

    static func data(_ name: String) throws -> Data {
        let root = try XCTUnwrap(Bundle.module.url(forResource: "NativePage", withExtension: nil))
        return try Data(contentsOf: root.appendingPathComponent(name))
    }

    static func request() throws -> Request {
        try JSONDecoder().decode(Request.self, from: data("capture-applied-request.json"))
    }

    static func before() throws -> Anytype_Rpc.Object.Show.Response {
        try .init(serializedBytes: data("capture-before-object-show.pb"))
    }

    static func after() throws -> Anytype_Rpc.Object.Show.Response {
        try .init(serializedBytes: data("capture-after-object-show.pb"))
    }

    static func plan() throws -> PinkhaHeartSemanticAnchorPlan {
        let request = try request()
        let block = try XCTUnwrap(before().objectView.blocks.first {
            $0.id.utf8.elementsEqual(request.blockID.utf8)
        })
        return try .init(spaceID: request.spaceID, objectID: request.objectID, anchorID: request.anchorID,
            range: NSRange(location: Int(request.from), length: Int(request.to - request.from)), nativeBlock: block)
    }

    static func reply(_ mutate: (inout [String: Any]) throws -> Void) throws -> Data {
        var value = try XCTUnwrap(JSONSerialization.jsonObject(with: data("capture-applied-response.json")) as? [String: Any])
        try mutate(&value)
        return try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    }

    static func eventReply(_ mutate: (inout Anytype_ResponseEvent) throws -> Void) throws -> Data {
        var event = try Anytype_ResponseEvent(serializedBytes: data("capture-response-event.pb"))
        try mutate(&event)
        let encoded = try event.serializedData().base64EncodedString()
        return try reply { $0["responseEvent"] = encoded }
    }

    static func alterTarget(_ original: Anytype_Rpc.Object.Show.Response,
                            _ mutate: (inout Anytype_Model_Block) throws -> Void) throws
        -> Anytype_Rpc.Object.Show.Response {
        let blockID = try request().blockID
        var response = original
        var view = response.objectView
        let index = try XCTUnwrap(view.blocks.firstIndex { $0.id.utf8.elementsEqual(blockID.utf8) })
        try mutate(&view.blocks[index])
        response.objectView = view
        return response
    }
}

final class PinkhaHeartSemanticAnchorWireTests: XCTestCase {
    func testActualNativePageRequestDigestsEventAndColdReadback() throws {
        let plan = try HeartCaptureFixture.plan()
        let original = try JSONSerialization.jsonObject(with: HeartCaptureFixture.data("capture-applied-request.json")) as? NSDictionary
        let encoded = try JSONSerialization.jsonObject(with: plan.request.encodedRequest()) as? NSDictionary
        XCTAssertEqual(original, encoded)
        let reply = try PinkhaHeartSemanticAnchorAppliedReply.decode(
            HeartCaptureFixture.data("capture-applied-response.json"), request: plan.request)
        XCTAssertEqual(reply.receipt.beforeTextMarksSHA256, plan.request.expected.digest)
        XCTAssertEqual(reply.responseEvent, try HeartCaptureFixture.data("capture-response-event.pb"))
        try plan.verifyCurrent(HeartCaptureFixture.before())
        let event = try plan.validatedEvent(reply)
        XCTAssertEqual(event.messages.count, 1)
        try plan.verifyReadback(HeartCaptureFixture.after(), receipt: reply.receipt)
        let cold = try Anytype_Rpc.Object.Show.Response(
            serializedBytes: HeartCaptureFixture.data("cold-reopen-object-show.pb"))
        try plan.verifyReadback(cold, receipt: reply.receipt)
    }

    func testStrictJSONPreservesDuplicatesAndUTF16EscapeEvidence() throws {
        let invalid = [
            #"{"protocolVersion":1,"outcome":"changed","outcome":"uncertain"}"#,
            #"{"protocolVersion":1,"outcome":"changed","out\u0063ome":"uncertain"}"#,
            #"{"a":{"version":1,"version":1}}"#,
            #"{"a":"\ud800"}"#, #"{"a":"\udc00"}"#,
            #"{"a":"\ud800\u0041"}"#, #"{"a":"\ud800x"}"#,
            #"{"a":"\uZZZZ"}"#, #"{"a":1}{"b":2}"#,
            #"{"a":1.0}"#, #"{"a":1e0}"#, #"{"a":01}"#
        ]
        for value in invalid {
            XCTAssertThrowsError(try HeartSemanticJSON.validate(Data(value.utf8), maximumBytes: 4_194_304), value)
        }
        XCTAssertThrowsError(try HeartSemanticJSON.validate(Data([0xff]), maximumBytes: 4_194_304))
        for value in [#"{"a":"\ufffd"}"#, #"{"a":"\uD83D\uDE00"}"#,
                      "{\"a\":\"\u{fffd}\"}", #"{"a":"\\ud800"}"#] {
            try HeartSemanticJSON.validate(Data(value.utf8), maximumBytes: 4_194_304)
        }
    }

    func testReplyRejectsUnknownFieldsWrongShapesAndNoncanonicalBase64() throws {
        let plan = try HeartCaptureFixture.plan()
        let variants: [([String: Any]) -> [String: Any]] = [
            { var x = $0; x["isOwner"] = true; return x },
            { var x = $0; x["protocolVersion"] = "1"; return x },
            { var x = $0; x["protocolVersion"] = true; return x },
            { var x = $0; x["protocolVersion"] = 4_294_967_296 as Int64; return x },
            { var x = $0; x["outcome"] = "futureApplied"; return x },
            { var x = $0; x["receipt"] = NSNull(); return x },
            { var x = $0; x["responseEvent"] = NSNull(); return x },
            { var x = $0; x["responseEvent"] = ""; return x },
            { var x = $0; x["responseEvent"] = "/w"; return x },
            { var x = $0; x["responseEvent"] = "/w==\n"; return x },
            { var x = $0; var r = x["receipt"] as! [String: Any]; r["retry"] = true; x["receipt"] = r; return x },
            { var x = $0; var r = x["receipt"] as! [String: Any]; r["spaceID"] = "foreign"; x["receipt"] = r; return x },
            { var x = $0; var r = x["receipt"] as! [String: Any]; r["nativeChangeSHA256"] = String(repeating: "A", count: 64); x["receipt"] = r; return x },
            { var x = $0; var r = x["receipt"] as! [String: Any]; r["beforeTextMarksSHA256"] = String(repeating: "0", count: 64); x["receipt"] = r; return x }
        ]
        for transform in variants {
            let raw = try HeartCaptureFixture.reply { $0 = transform($0) }
            XCTAssertThrowsError(try PinkhaHeartSemanticAnchorAppliedReply.decode(raw, request: plan.request))
        }
        let tooLarge = try HeartCaptureFixture.reply {
            $0["responseEvent"] = Data(repeating: 0, count: 2 * 1_024 * 1_024 + 1).base64EncodedString()
        }
        XCTAssertThrowsError(try PinkhaHeartSemanticAnchorAppliedReply.decode(tooLarge, request: plan.request))
        XCTAssertThrowsError(try PinkhaHeartSemanticAnchorAppliedReply.decode(
            Data(repeating: 32, count: 4 * 1_024 * 1_024 + 1), request: plan.request))
    }

    func testRequestEnforcesUTF8MarksAndGraphemeSelectionBounds() throws {
        let exact = String(repeating: "\u{05d0}", count: 32_768)
        XCTAssertEqual(exact.utf8.count, 65_536)
        _ = try PinkhaHeartSemanticAnchorSnapshot(text: exact, marks: [])
        XCTAssertThrowsError(try PinkhaHeartSemanticAnchorSnapshot(text: exact + "\u{05d0}", marks: []))
        let mark = PinkhaHeartSemanticAnchorMark(from: 0, to: 1, kind: 3, param: "")
        _ = try PinkhaHeartSemanticAnchorSnapshot(text: "A", marks: Array(repeating: mark, count: 1_024))
        XCTAssertThrowsError(try PinkhaHeartSemanticAnchorSnapshot(text: "A", marks: Array(repeating: mark, count: 1_025)))
        let parameter = PinkhaHeartSemanticAnchorMark(from: 0, to: 1, kind: 3, param: String(repeating: "x", count: 8_192))
        _ = try PinkhaHeartSemanticAnchorSnapshot(text: "A", marks: Array(repeating: parameter, count: 32))
        XCTAssertThrowsError(try PinkhaHeartSemanticAnchorSnapshot(text: "A",
            marks: Array(repeating: parameter, count: 32) + [.init(from: 0, to: 1, kind: 3, param: "x")]))
        let fixture = try HeartCaptureFixture.request()
        func request(_ text: String, _ range: NSRange) throws -> PinkhaHeartSemanticAnchorRequest {
            try .init(spaceID: fixture.spaceID, objectID: fixture.objectID, blockID: fixture.blockID,
                anchorID: fixture.anchorID, range: range, expected: .init(text: text, marks: []))
        }
        XCTAssertThrowsError(try request("\u{1f600}", .init(location: 1, length: 1)))
        XCTAssertThrowsError(try request("e\u{0301}", .init(location: 0, length: 1)))
        XCTAssertThrowsError(try request("A", .init(location: NSNotFound, length: 1)))
        XCTAssertThrowsError(try request("A", .init(location: 0, length: 0)))
        _ = try request("e\u{0301}", .init(location: 0, length: 2))
    }

    func testNativeLinksOrderedMarksAndUnicodeByteIdentityRemainDistinct() throws {
        let plan = try HeartCaptureFixture.plan()
        XCTAssertThrowsError(try PinkhaHeartSemanticAnchorRequest(spaceID: plan.request.spaceID,
            objectID: plan.request.objectID, blockID: plan.request.blockID, anchorID: plan.request.anchorID,
            range: NSRange(location: 7, length: 4), expected: plan.request.expected))
        let composed = try PinkhaHeartSemanticAnchorSnapshot(text: "\u{00e9}", marks: [])
        let decomposed = try PinkhaHeartSemanticAnchorSnapshot(text: "e\u{0301}", marks: [])
        XCTAssertNotEqual(composed, decomposed)
        XCTAssertNotEqual(composed.digest, decomposed.digest)
        let first = PinkhaHeartSemanticAnchorMark(from: 0, to: 1, kind: 3, param: "\u{00e9}")
        let second = PinkhaHeartSemanticAnchorMark(from: 0, to: 1, kind: 3, param: "e\u{0301}")
        XCTAssertNotEqual(first, second)
        let left = try PinkhaHeartSemanticAnchorSnapshot(text: "A", marks: [first, second, first])
        let right = try PinkhaHeartSemanticAnchorSnapshot(text: "A", marks: [first, first, second])
        XCTAssertNotEqual(left, right)
        XCTAssertTrue(left.hasSameMarks(as: right))
        XCTAssertFalse(try left.hasSameMarks(as: .init(text: "A", marks: [first, second])))
    }

    func testCanonicalSnapshotUsesGoStringEscapingAndEmptyMarkArray() throws {
        let snapshot = try PinkhaHeartSemanticAnchorSnapshot(text: "<&>\u{2028}\u{2029}\n\0\"\\", marks: [])
        XCTAssertEqual(snapshot.canonicalJSON, #"{"text":"\u003c\u0026\u003e\u2028\u2029\n\u0000\"\\","marks":[]}"#)
        let empty = try PinkhaHeartSemanticAnchorSnapshot(text: "", marks: [])
        XCTAssertEqual(empty.canonicalJSON, #"{"text":"","marks":[]}"#)
        XCTAssertEqual(empty.digest.count, 64)
    }

    func testFixedRefusalsCannotCarrySuccessReceiptsOrEvents() throws {
        let request = try HeartCaptureFixture.plan().request
        for outcome in ["invalid", "unsupportedVersion", "limit", "changed", "alreadyLinked",
                        "pendingEdit", "permissionDenied", "unavailable", "uncertain"] {
            let raw = Data("{\"protocolVersion\":1,\"outcome\":\"\(outcome)\"}".utf8)
            XCTAssertThrowsError(try PinkhaHeartSemanticAnchorAppliedReply.decode(raw, request: request)) {
                XCTAssertEqual($0 as? PinkhaHeartSemanticAnchorError,
                    .nativeRefusal(PinkhaHeartSemanticAnchorOutcome(rawValue: outcome)!))
            }
            let smuggled = Data("{\"protocolVersion\":1,\"outcome\":\"\(outcome)\",\"receipt\":null}".utf8)
            XCTAssertThrowsError(try PinkhaHeartSemanticAnchorAppliedReply.decode(smuggled, request: request)) {
                XCTAssertEqual($0 as? PinkhaHeartSemanticAnchorError, .invalidReply)
            }
        }
    }

    func testNativeSnapshotRejectsMissingUnknownAndUnsupportedMarkFields() throws {
        let original = try HeartCaptureFixture.plan().originalBlock
        var block = original
        block.text.marks.marks[0].clearRange()
        XCTAssertThrowsError(try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: block))
        block = original
        block.text.marks.marks[0].type = .UNRECOGNIZED(11)
        XCTAssertThrowsError(try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: block))
        block = original
        let mark = block.text.marks.marks[0]
        block.text.marks.marks[0] = try .init(serializedBytes: mark.serializedData() + Data([0x98, 0x06, 0x01]))
        XCTAssertThrowsError(try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: block))
        block = original
        let text = block.text
        block.text = try .init(serializedBytes: text.serializedData() + Data([0x98, 0x06, 0x01]))
        XCTAssertThrowsError(try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: block))
    }

    func testNativeEventRejectsWrongOwnerExtraMutationAndChangedMarks() throws {
        let plan = try HeartCaptureFixture.plan()
        let mutations: [(inout Anytype_ResponseEvent) -> Void] = [
            { $0.contextID = "other-object" },
            { $0.messages[0].spaceID = "other-space" },
            { $0.messages.append($0.messages[0]) },
            { $0.messages[0].blockSetText.text.value = "replacement" },
            { $0.messages[0].blockSetText.marks.value.marks[0].param += "changed" }
        ]
        for mutation in mutations {
            let raw = try HeartCaptureFixture.eventReply(mutation)
            let reply = try PinkhaHeartSemanticAnchorAppliedReply.decode(raw, request: plan.request)
            XCTAssertThrowsError(try plan.validatedEvent(reply))
        }
    }

    func testReadbackRejectsIdentityMissingBlockAndEveryOpaqueFieldMutation() throws {
        let plan = try HeartCaptureFixture.plan()
        let reply = try PinkhaHeartSemanticAnchorAppliedReply.decode(
            HeartCaptureFixture.data("capture-applied-response.json"), request: plan.request)
        var wrongRoot = try HeartCaptureFixture.after()
        wrongRoot.objectView.rootID = "wrong-root"
        XCTAssertThrowsError(try plan.verifyReadback(wrongRoot, receipt: reply.receipt))
        var missing = try HeartCaptureFixture.after()
        missing.objectView.blocks.removeAll { $0.id == plan.request.blockID }
        XCTAssertThrowsError(try plan.verifyReadback(missing, receipt: reply.receipt))
        for field in ["background", "alignment", "opaque", "restriction"] {
            let changed = try HeartCaptureFixture.alterTarget(HeartCaptureFixture.after()) { block in
                switch field {
                case "background": block.backgroundColor = "red"
                case "alignment": block.align = .left
                case "opaque": block.fields.fields["semanticAnchorControlOpaque"] = .with { $0.stringValue = "changed" }
                default: block.restrictions.edit = true
                }
            }
            XCTAssertThrowsError(try plan.verifyReadback(changed, receipt: reply.receipt), field)
        }
    }

    func testReadbackAllowsOnlyUpstreamEmptyRestrictionPresenceNormalization() throws {
        let original = try HeartCaptureFixture.plan()
        var missingPresence = original.originalBlock
        missingPresence.clearRestrictions()
        let plan = try PinkhaHeartSemanticAnchorPlan(spaceID: original.request.spaceID,
            objectID: original.request.objectID, anchorID: original.request.anchorID,
            range: NSRange(location: Int(original.request.from), length: Int(original.request.to - original.request.from)),
            nativeBlock: missingPresence)
        let reply = try PinkhaHeartSemanticAnchorAppliedReply.decode(
            HeartCaptureFixture.data("capture-applied-response.json"), request: plan.request)
        try plan.verifyReadback(HeartCaptureFixture.after(), receipt: reply.receipt)
        // Presence is normalized only for readback; a stale pre-write block is
        // still rejected by the complete current-read comparison.
        XCTAssertThrowsError(try plan.verifyCurrent(HeartCaptureFixture.before()))
    }
}
