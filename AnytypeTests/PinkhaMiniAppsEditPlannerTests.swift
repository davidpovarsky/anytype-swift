import XCTest
import HanlinMiniAppsBridge
#if canImport(Anytype)
@testable import Anytype
#else
@testable import MiniAppsConsumerPlanner
#endif

final class PinkhaMiniAppsEditPlannerTests: XCTestCase {
    private func request(_ blocks: [PinkhaMiniAppsBlockSnapshot], selection: MiniAppTextSelection? = nil) throws -> MiniAppInvocation {
        .init(appID: "text-studio", source: .init(appID: "io.anytype.app.dev",
            displayName: "Anytype", documentID: "object-original", selection: selection,
            documentText: blocks.map(\.text).joined(separator: "\n"),
            metadata: ["anytype.blocks": String(decoding: try JSONEncoder().encode(blocks), as: UTF8.self)]))
    }
    private func block(_ text: String) -> PinkhaMiniAppsBlockSnapshot {
        block("block-original", text)
    }
    private func block(_ id: String, _ text: String) -> PinkhaMiniAppsBlockSnapshot {
        .init(id: id, text: text, marks: Data())
    }
    private func result(_ request: MiniAppInvocation, _ operation: MiniAppOperation, _ text: String) -> MiniAppResult {
        .init(requestID: request.id, operation: operation, items: [.init(kind: .text, text: text)])
    }

    func testHebrewEmojiSelectionReplacesActualUTF16Range() throws {
        let original = "לפני 🙂 אחרי"
        let range = (original as NSString).range(of: "🙂")
        let invocation = try request([block(original)], selection: .init(
            location: range.location, length: range.length, text: "🙂", blockIDs: ["block-original"]))
        let plan = try PinkhaMiniAppsEditPlanner.make(request: invocation, result: result(invocation, .replaceSelection, "שלום"))
        XCTAssertEqual(plan.mutations.count, 1)
        XCTAssertEqual(plan.mutations.first?.before.id, "block-original")
        XCTAssertEqual(plan.mutations.first?.afterText, "לפני שלום אחרי")
    }

    func testCaretInsertionPreservesTextOnBothSides() throws {
        let invocation = try request([block("אב🙂ג")], selection: .init(
            location: 4, length: 0, text: "", blockIDs: ["block-original"]))
        let plan = try PinkhaMiniAppsEditPlanner.make(request: invocation, result: result(invocation, .insert, "חדש"))
        XCTAssertEqual(plan.mutations.first?.afterText, "אב🙂חדשג")
        XCTAssertTrue(plan.additions.isEmpty)
    }

    func testInvalidSurrogateOffsetIsRejected() throws {
        let invocation = try request([block("🙂")], selection: .init(
            location: 1, length: 1, text: "?", blockIDs: ["block-original"]))
        XCTAssertThrowsError(try PinkhaMiniAppsEditPlanner.make(
            request: invocation, result: result(invocation, .replaceSelection, "new")))
    }

    func testOverflowingRangeIsRejected() throws {
        let invocation = try request([block("text")], selection: .init(
            location: Int.max, length: 1, text: "", blockIDs: ["block-original"]))
        XCTAssertThrowsError(try PinkhaMiniAppsEditPlanner.make(
            request: invocation, result: result(invocation, .insert, "new")))
    }

    func testBlockSelectionUsesNativeDocumentOrderAndRetainsIDs() throws {
        let invocation = try request([block("a", "first"), block("b", "second"), block("c", "untouched")],
            selection: .init(location: 0, length: 12, text: "first\nsecond", blockIDs: ["b", "a"]))
        let plan = try PinkhaMiniAppsEditPlanner.make(request: invocation, result: result(invocation, .replaceSelection, "returned"))
        XCTAssertEqual(plan.mutations.map { $0.before.id }, ["a", "b"])
        XCTAssertEqual(plan.mutations.map(\.afterText), ["returned", ""])
    }

    func testDocumentBodyReplacementRetainsOriginalBlockIDsAndAttachments() throws {
        let invocation = try request([block("a", "first"), block("b", "second")])
        let attachment = MiniAppContent(kind: .file, attachmentID: UUID(), typeIdentifier: "public.pdf", name: "result.pdf")
        let returned = MiniAppResult(requestID: invocation.id, operation: .replaceDocument,
            items: [.init(kind: .text, text: "whole body"), attachment])
        let plan = try PinkhaMiniAppsEditPlanner.make(request: invocation, result: returned)
        XCTAssertEqual(plan.mutations.map { $0.before.id }, ["a", "b"])
        XCTAssertEqual(plan.mutations.map(\.afterText), ["whole body", ""])
        XCTAssertEqual(plan.additions, [attachment])
    }

    func testNewerEditIsPreservedAndAlreadyAppliedMutationIsNotRepeated() throws {
        let invocation = try request([block("original")], selection: .init(
            location: 0, length: 8, text: "original", blockIDs: ["block-original"]))
        let plan = try PinkhaMiniAppsEditPlanner.make(request: invocation, result: result(invocation, .replaceSelection, "returned"))
        let mutation = try XCTUnwrap(plan.mutations.first)
        XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: mutation,
            current: block("original"), alreadyRecorded: false, expectedMarks: Data()), .apply)
        XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: mutation,
            current: block("returned"), alreadyRecorded: false, expectedMarks: Data()), .alreadyApplied)
        XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: mutation,
            current: block("newer user edit"), alreadyRecorded: false, expectedMarks: Data()), .preserveNewerContent)
        XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: mutation,
            current: nil, alreadyRecorded: false, expectedMarks: Data()), .preserveNewerContent)
        XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: mutation,
            current: block("later user edit"), alreadyRecorded: true, expectedMarks: Data()), .alreadyApplied)
    }

    func testMarkRangesPreserveUnaffectedUTF16Text() {
        XCTAssertEqual(PinkhaMiniAppsEditPlanner.shiftedMarkRanges(from: 1, to: 8,
            editLocation: 3, editLength: 2, replacementLength: 4),
            [NSRange(location: 1, length: 2), NSRange(location: 7, length: 3)])
        XCTAssertEqual(PinkhaMiniAppsEditPlanner.shiftedMarkRanges(from: 7, to: 9,
            editLocation: 3, editLength: 2, replacementLength: 4), [NSRange(location: 9, length: 2)])
        XCTAssertEqual(PinkhaMiniAppsEditPlanner.shiftedMarkRanges(from: 3, to: 5,
            editLocation: 3, editLength: 2, replacementLength: 4), [])
    }

    func testInsertionAtMarkInteriorDoesNotStyleReturnedText() {
        XCTAssertEqual(PinkhaMiniAppsEditPlanner.shiftedMarkRanges(from: 1, to: 5,
            editLocation: 2, editLength: 0, replacementLength: 2),
            [NSRange(location: 1, length: 1), NSRange(location: 4, length: 3)])
    }

    func testDuplicateNativeBlockIDsAreRejected() throws {
        let invocation = try request([block("same", "a"), block("same", "b")])
        XCTAssertThrowsError(try PinkhaMiniAppsEditPlanner.make(
            request: invocation, result: result(invocation, .replaceDocument, "returned")))
    }

    func testPreparedProgressSurvivesColdStartRoundTrip() throws {
        let invocation = try request([block("old")])
        var plan = try PinkhaMiniAppsEditPlanner.make(request: invocation, result: result(invocation, .replaceDocument, "new"))
        plan.appliedBlocks = ["block-original"]
        plan.insertedBlocks = ["request:0": "inserted-native-id"]
        plan.preservedNewerContent = true
        plan.completed = true
        let restored = try JSONDecoder().decode(PinkhaMiniAppsEditPlan.self, from: JSONEncoder().encode(plan))
        XCTAssertEqual(restored.requestID, invocation.id)
        XCTAssertEqual(restored.appliedBlocks, ["block-original"])
        XCTAssertEqual(restored.insertedBlocks["request:0"], "inserted-native-id")
        XCTAssertEqual(restored.mutations.first?.afterText, "new")
        XCTAssertTrue(restored.preservedNewerContent)
        XCTAssertTrue(restored.completed)
    }

    func testEmptyDocumentInsertionCarriesReturnedFilesWithoutLosingIdentity() throws {
        let invocation = try request([])
        let item = MiniAppContent(kind: .file, attachmentID: UUID(), name: "returned.pdf")
        let plan = try PinkhaMiniAppsEditPlanner.make(request: invocation, result:
            .init(requestID: invocation.id, operation: .insert, items: [item]))
        XCTAssertTrue(plan.mutations.isEmpty)
        XCTAssertEqual(plan.additions, [item])
    }

    func testDisplayDoesNotCreateAnEditPlan() throws {
        let invocation = try request([block("unchanged")])
        let plan = try PinkhaMiniAppsEditPlanner.make(request: invocation, result: result(invocation, .display, "answer"))
        XCTAssertTrue(plan.mutations.isEmpty)
        XCTAssertTrue(plan.additions.isEmpty)
    }
}

extension PinkhaMiniAppsEditPlannerTests {
    func testSourceSelectionRequiresExactUnicodeBytes() throws {
        let pairs = [("\u{00E9}", "e\u{0301}"),
                     ("\u{05E9}\u{05B8}\u{05C1}", "\u{05E9}\u{05C1}\u{05B8}")]
        for (stored, equivalent) in pairs {
            XCTAssertEqual(stored, equivalent)
            XCTAssertNotEqual(Data(stored.utf8), Data(equivalent.utf8))
            let invocation = try request([block(stored)], selection: .init(
                location: 0, length: stored.utf16.count, text: equivalent, blockIDs: ["block-original"]))
            XCTAssertThrowsError(try PinkhaMiniAppsEditPlanner.make(
                request: invocation, result: result(invocation, .replaceSelection, "returned")))
            let exact = try request([block(stored)], selection: .init(
                location: 0, length: stored.utf16.count, text: stored, blockIDs: ["block-original"]))
            let plan = try PinkhaMiniAppsEditPlanner.make(
                request: exact, result: result(exact, .replaceSelection, "returned"))
            XCTAssertEqual(plan.mutations.count, 1)
            XCTAssertEqual(Data(try XCTUnwrap(plan.mutations.first?.before.text).utf8), Data(stored.utf8))
        }
    }

    func testReplayRequiresExactBeforeAndRequestedAfterBytes() throws {
        let pairs = [("\u{00E9}", "e\u{0301}"),
                     ("\u{05E9}\u{05B8}\u{05C1}", "\u{05E9}\u{05C1}\u{05B8}")]
        for (stored, equivalent) in pairs {
            let initial = try request([block(stored)])
            let initialPlan = try PinkhaMiniAppsEditPlanner.make(
                request: initial, result: result(initial, .replaceDocument, "returned"))
            let beforeMutation = try XCTUnwrap(initialPlan.mutations.first)
            XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: beforeMutation,
                current: block(equivalent), alreadyRecorded: false, expectedMarks: Data()), .preserveNewerContent)
            XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: beforeMutation,
                current: block(stored), alreadyRecorded: false, expectedMarks: Data()), .apply)

            let invocation = try request([block("old")])
            let plan = try PinkhaMiniAppsEditPlanner.make(
                request: invocation, result: result(invocation, .replaceDocument, stored))
            let mutation = try XCTUnwrap(plan.mutations.first)
            XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: mutation,
                current: block(equivalent), alreadyRecorded: false, expectedMarks: Data()), .preserveNewerContent)
            XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: mutation,
                current: block(stored), alreadyRecorded: false, expectedMarks: Data()), .alreadyApplied)
            XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: mutation,
                current: block("different-native-id", stored), alreadyRecorded: false,
                expectedMarks: Data()), .preserveNewerContent)
            // A durable applied receipt still prevents a second write after a newer edit.
            XCTAssertEqual(PinkhaMiniAppsEditPlanner.replayDecision(mutation: mutation,
                current: block(equivalent), alreadyRecorded: true, expectedMarks: Data()), .alreadyApplied)
        }
    }

    func testReadbackSnapshotRequiresExactIdentityTextAndMarks() throws {
        let stored = "\u{00E9}", equivalent = "e\u{0301}"
        let expected = PinkhaMiniAppsBlockSnapshot(id: "block-" + stored,
                                                 text: stored, marks: Data([1, 2]))
        let roundTrip = try JSONDecoder().decode(PinkhaMiniAppsBlockSnapshot.self,
            from: JSONEncoder().encode(expected))
        XCTAssertTrue(roundTrip.matchesExactly(expected))
        XCTAssertFalse(PinkhaMiniAppsBlockSnapshot(id: "block-" + equivalent,
            text: stored, marks: expected.marks).matchesExactly(expected))
        XCTAssertFalse(PinkhaMiniAppsBlockSnapshot(id: expected.id,
            text: equivalent, marks: expected.marks).matchesExactly(expected))
        XCTAssertFalse(PinkhaMiniAppsBlockSnapshot(id: expected.id,
            text: stored, marks: Data([1, 3])).matchesExactly(expected))
    }
}
