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


extension HeartCaptureFixture {
    static func projectionValues(populated: Bool = false) -> [String: Google_Protobuf_Value] {
        [
            "_pinkhaTorahState": .with { $0.stringValue = "READY" },
            "_pinkhaTorahReady": .with { $0.boolValue = true },
            "_pinkhaTorahProjectionVersion": .with { $0.numberValue = 1 },
            "_pinkhaTorahRelatedVersion": .with { $0.numberValue = 1 },
            "_pinkhaTorahCanonicalHash": .with { $0.stringValue = String(repeating: "a", count: 64) },
            "_pinkhaTorahCacheIntegrity": .with { $0.stringValue = String(repeating: "b", count: 64) },
            "_pinkhaTorahCanonicalPropertyKey": .with { $0.stringValue = "owned-opaque-canonical-key" },
            "_pinkhaTorahAttachedProperties": .with {
                $0.listValue = .with {
                    $0.values = populated ? ["pinkhaTorahSources", "pinkhaTorahTopics", "pinkhaTorahWords"].map {
                        property in .with { $0.stringValue = property }
                    } : []
                }
            },
            "_pinkhaTorahLabels": .with {
                $0.stringValue = populated ? #"{"owned-source":{"he":"מקור","en":"Source"},"owned-topic":{"he":"נושא"}}"# : "{}"
            }
        ]
    }

    static func withProjection(_ response: Anytype_Rpc.Object.Show.Response,
                               values: [String: Google_Protobuf_Value]) throws -> Anytype_Rpc.Object.Show.Response {
        var result = response
        let id = try request().objectID
        let index = try XCTUnwrap(result.objectView.details.firstIndex { $0.id.utf8.elementsEqual(id.utf8) })
        for (key, value) in values { result.objectView.details[index].details.fields[key] = value }
        return result
    }

    static func projectionReply(values: [String: Google_Protobuf_Value],
                                mutate: (inout Anytype_ResponseEvent) throws -> Void = { _ in }) throws -> Data {
        let request = try request()
        return try eventReply { event in
            event.messages.insert(.with {
                $0.spaceID = request.spaceID
                $0.objectDetailsAmend = .with {
                    $0.id = request.objectID
                    $0.details = values.keys.sorted().map { key in .with { $0.key = key; $0.value = values[key]! } }
                }
            }, at: 0)
            try mutate(&event)
        }
    }

    static func withUnknown<M: SwiftProtobuf.Message>(_ value: M) throws -> M {
        // A real unknown protobuf field, rather than a mock unknownFields flag.
        try M(serializedBytes: value.serializedData() + Data([0x98, 0x06, 0x01]))
    }
}

final class PinkhaHeartSemanticAnchorWireTests: XCTestCase {

    func testCapturedProjectionAndMarksRequireTheExactSameObjectPreflight() throws {
        let plan = try HeartCaptureFixture.plan()
        for populated in [false, true] {
            let values = HeartCaptureFixture.projectionValues(populated: populated)
            let before = try HeartCaptureFixture.withProjection(HeartCaptureFixture.before(), values: values)
            let reply = try PinkhaHeartSemanticAnchorAppliedReply.decode(
                HeartCaptureFixture.projectionReply(values: values), request: plan.request)
            let event = try plan.validatedEvent(reply, preflight: before)
            XCTAssertEqual(event.messages.count, 2)
            XCTAssertEqual(try event.serializedData(), reply.responseEvent)
            try plan.verifyReadback(HeartCaptureFixture.after(), receipt: reply.receipt)
            XCTAssertThrowsError(try plan.validatedEvent(reply), "Projection needs the actual preflight")
        }
    }

    func testProjectionRejectsForeignAmbiguousStaleAndMalformedNativeEvents() throws {
        let plan = try HeartCaptureFixture.plan()
        let values = HeartCaptureFixture.projectionValues()
        let before = try HeartCaptureFixture.withProjection(HeartCaptureFixture.before(), values: values)
        let raw = try HeartCaptureFixture.projectionReply(values: values)
        let reply = try PinkhaHeartSemanticAnchorAppliedReply.decode(raw, request: plan.request)
        func rejects(_ bytes: Data, preflight: Anytype_Rpc.Object.Show.Response, label: String) throws {
            let candidate = try PinkhaHeartSemanticAnchorAppliedReply.decode(bytes, request: plan.request)
            XCTAssertThrowsError(try plan.validatedEvent(candidate, preflight: preflight), label)
        }

        let eventMutations: [(String, (inout Anytype_ResponseEvent) throws -> Void)] = [
            ("foreign context", { $0.contextID += "-foreign" }),
            ("foreign projection Space", { $0.messages[0].spaceID += "-foreign" }),
            ("foreign block Space", { $0.messages[1].spaceID += "-foreign" }),
            ("foreign object", { $0.messages[0].objectDetailsAmend.id += "-foreign" }),
            ("sub-object mutation", { $0.messages[0].objectDetailsAmend.subIds = ["foreign"] }),
            ("missing projection field", { $0.messages[0].objectDetailsAmend.details.removeLast() }),
            ("extra projection field", { $0.messages[0].objectDetailsAmend.details.append(.with {
                $0.key = "name"; $0.value.stringValue = "unrelated mutation"
            }) }),
            ("duplicate projection field", { $0.messages[0].objectDetailsAmend.details[1] = $0.messages[0].objectDetailsAmend.details[0] }),
            ("unrelated key", { $0.messages[0].objectDetailsAmend.details[0].key = "name" }),
            ("missing value", { $0.messages[0].objectDetailsAmend.details[0].clearValue() }),
            ("third message", { $0.messages.append($0.messages[0]) }),
            ("reversed messages", { $0.messages.reverse() }),
            ("duplicate block update", { $0.messages[0] = $0.messages[1] }),
            ("duplicate details update", { $0.messages[1] = $0.messages[0] }),
            ("foreign block", { $0.messages[1].blockSetText.id += "-foreign" }),
            ("text mutation", { $0.messages[1].blockSetText.text.value = "unrelated text" }),
            ("changed mark", { $0.messages[1].blockSetText.marks.value.marks[0].param += "-changed" }),
            ("event unknown field", { $0 = try HeartCaptureFixture.withUnknown($0) }),
            ("message unknown field", { $0.messages[0] = try HeartCaptureFixture.withUnknown($0.messages[0]) }),
            ("amendment unknown field", { $0.messages[0].objectDetailsAmend = try HeartCaptureFixture.withUnknown($0.messages[0].objectDetailsAmend) }),
            ("key-value unknown field", { $0.messages[0].objectDetailsAmend.details[0] = try HeartCaptureFixture.withUnknown($0.messages[0].objectDetailsAmend.details[0]) })
        ]
        for (label, mutate) in eventMutations {
            try rejects(HeartCaptureFixture.projectionReply(values: values, mutate: mutate),
                        preflight: before, label: label)
        }

        let rowIndex = try XCTUnwrap(before.objectView.details.firstIndex { $0.id == plan.request.objectID })
        for key in values.keys.sorted() {
            var missing = before
            missing.objectView.details[rowIndex].details.fields.removeValue(forKey: key)
            XCTAssertThrowsError(try plan.validatedEvent(reply, preflight: missing), "Missing preflight: " + key)
        }
        for variant in ["missing-row", "duplicate-row", "sub-ids", "unknown-row", "unknown-details", "foreign-root", "changed-block"] {
            var candidate = before
            switch variant {
            case "missing-row": candidate.objectView.details.remove(at: rowIndex)
            case "duplicate-row": candidate.objectView.details.append(candidate.objectView.details[rowIndex])
            case "sub-ids": candidate.objectView.details[rowIndex].subIds = ["unrelated"]
            case "unknown-row": candidate.objectView.details[rowIndex] = try HeartCaptureFixture.withUnknown(candidate.objectView.details[rowIndex])
            case "unknown-details": candidate.objectView.details[rowIndex].details = try HeartCaptureFixture.withUnknown(candidate.objectView.details[rowIndex].details)
            case "foreign-root": candidate.objectView.rootID += "-foreign"
            default: candidate = try HeartCaptureFixture.alterTarget(candidate) { $0.backgroundColor = "changed" }
            }
            XCTAssertThrowsError(try plan.validatedEvent(reply, preflight: candidate), variant)
        }

        var stale = before
        stale.objectView.details[rowIndex].details.fields["_pinkhaTorahCacheIntegrity"]?.stringValue = String(repeating: "c", count: 64)
        XCTAssertThrowsError(try plan.validatedEvent(reply, preflight: stale), "Valid-shaped stale cache proof")
        stale = before
        stale.objectView.details[rowIndex].details.fields["_pinkhaTorahCanonicalHash"]?.stringValue = String(repeating: "d", count: 64)
        XCTAssertThrowsError(try plan.validatedEvent(reply, preflight: stale), "Valid-shaped different canonical content")
        stale = before
        stale.objectView.details[rowIndex].details.fields["_pinkhaTorahCanonicalPropertyKey"]?.stringValue += "-foreign"
        XCTAssertThrowsError(try plan.validatedEvent(reply, preflight: stale), "Opaque canonical key mismatch")

        let invalidValues: [(String, Google_Protobuf_Value)] = [
            ("_pinkhaTorahState", .with { $0.stringValue = "MALFORMED" }),
            ("_pinkhaTorahState", .with { $0.stringValue = "UNSUPPORTED" }),
            ("_pinkhaTorahReady", .with { $0.boolValue = false }),
            ("_pinkhaTorahReady", .with { $0.numberValue = 1 }),
            ("_pinkhaTorahProjectionVersion", .with { $0.numberValue = 2 }),
            ("_pinkhaTorahProjectionVersion", .with { $0.stringValue = "1" }),
            ("_pinkhaTorahRelatedVersion", .with { $0.numberValue = 0 }),
            ("_pinkhaTorahRelatedVersion", .with { $0.boolValue = true }),
            ("_pinkhaTorahCanonicalHash", .with { $0.stringValue = String(repeating: "A", count: 64) }),
            ("_pinkhaTorahCacheIntegrity", .with { $0.stringValue = String(repeating: "a", count: 63) }),
            ("_pinkhaTorahCanonicalPropertyKey", .with { $0.stringValue = "" }),
            ("_pinkhaTorahAttachedProperties", .with { $0.stringValue = "[]" }),
            ("_pinkhaTorahAttachedProperties", .with { $0.listValue.values = [.with { $0.stringValue = "foreign" }] }),
            ("_pinkhaTorahAttachedProperties", .with { $0.listValue.values = [.with { $0.boolValue = true }] }),
            ("_pinkhaTorahAttachedProperties", .with { $0.listValue.values = Array(repeating: .with { $0.stringValue = "pinkhaTorahSources" }, count: 2) }),
            ("_pinkhaTorahLabels", .with { $0.structValue = .init() }),
            ("_pinkhaTorahLabels", .with { $0.stringValue = "[]" }),
            ("_pinkhaTorahLabels", .with { $0.stringValue = #"{"":{"he":"x"}}"# }),
            ("_pinkhaTorahLabels", .with { $0.stringValue = #"{"id":{"en":"x"}}"# }),
            ("_pinkhaTorahLabels", .with { $0.stringValue = #"{"id":{"he":1}}"# }),
            ("_pinkhaTorahLabels", .with { $0.stringValue = #"{"id":{"he":"x","en":null}}"# }),
            ("_pinkhaTorahLabels", .with { $0.stringValue = #"{"id":{"he":"x","other":"x"}}"# }),
            ("_pinkhaTorahLabels", .with { $0.stringValue = #"{"id":{"he":"x","he":"y"}}"# }),
            ("_pinkhaTorahLabels", .with { $0.stringValue = #"{"id":{"he":"\ud800"}}"# })
        ]
        for (key, value) in invalidValues {
            var invalid = values
            invalid[key] = value
            try rejects(HeartCaptureFixture.projectionReply(values: invalid),
                        preflight: HeartCaptureFixture.withProjection(HeartCaptureFixture.before(), values: invalid),
                        label: "Even equal preflight/event must satisfy native projection schema: " + key)
        }
        for key in values.keys.sorted() {
            var invalid = values
            invalid[key] = try HeartCaptureFixture.withUnknown(values[key]!)
            try rejects(HeartCaptureFixture.projectionReply(values: invalid),
                        preflight: HeartCaptureFixture.withProjection(HeartCaptureFixture.before(), values: invalid),
                        label: "Unknown projection value field: " + key)
        }
        for nested in ["list", "element"] {
            var invalid = values
            var list = Google_Protobuf_ListValue.with { $0.values = [.with { $0.stringValue = "pinkhaTorahWords" }] }
            if nested == "list" { list = try HeartCaptureFixture.withUnknown(list) }
            else { list.values[0] = try HeartCaptureFixture.withUnknown(list.values[0]) }
            invalid["_pinkhaTorahAttachedProperties"] = .with { $0.listValue = list }
            try rejects(HeartCaptureFixture.projectionReply(values: invalid),
                        preflight: HeartCaptureFixture.withProjection(HeartCaptureFixture.before(), values: invalid),
                        label: "Unknown nested list field")
        }
        var composed = values
        composed["_pinkhaTorahCanonicalPropertyKey"] = .with { $0.stringValue = "\u{00e9}" }
        var decomposed = composed
        decomposed["_pinkhaTorahCanonicalPropertyKey"] = .with { $0.stringValue = "e\u{0301}" }
        try rejects(HeartCaptureFixture.projectionReply(values: composed),
                    preflight: HeartCaptureFixture.withProjection(HeartCaptureFixture.before(), values: decomposed),
                    label: "Canonically equivalent opaque keys must retain byte identity")
    }


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
