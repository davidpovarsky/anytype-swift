import Foundation
import XCTest
@testable import PinkhaKit

final class PinkhaSemanticTypingContinuationTests: XCTestCase {
    private func anchor() throws -> PinkhaSemanticTextAnchor {
        try .init(spaceID: "space", objectID: "object",
                  id: UUID(uuidString: "11112233-4455-6677-8899-aabbccddeeff")!)
    }

    func testConsecutiveNativeKeyInputsPreserveOneIdentityForTheWholeReplacement() throws {
        for keys in [["C", "h", "a", "n", "g", "e", "d"], ["ש", "ָ", "ׁ", "ל", "ו", "ֹ", "ם", " ", "😀"]] {
            let identity = try anchor()
            var value = try PinkhaSemanticText(text: "Anchor", marks: [.init(anchor: identity, range: .init(location: 0, length: 6))])
            var range = NSRange(location: 0, length: 6)
            var continuation: PinkhaSemanticTypingContinuation?
            for key in keys {
                let replacement = try continuation?.continuing(in: value, range: range, with: key)
                    ?? .init(range: range, text: key)
                let after = try value.replacing(replacement.range, with: replacement.text).after
                continuation = try .init(before: value, replacing: replacement.range, with: replacement.text, after: after)
                range = .init(location: range.location + key.utf16.count, length: 0)
                value = after
            }
            XCTAssertEqual(value.text, keys.joined())
            XCTAssertEqual(value.marks, [.init(anchor: identity, range: .init(location: 0, length: keys.joined().utf16.count))])
        }
    }

    func testIndependentBoundaryInsertionDoesNotJoinOrStartAContinuation() throws {
        let identity = try anchor()
        let before = try PinkhaSemanticText(text: "A", marks: [.init(anchor: identity, range: .init(location: 0, length: 1))])
        for position in [0, 1] {
            let range = NSRange(location: position, length: 0)
            let after = try before.replacing(range, with: "Z").after
            XCTAssertNil(try PinkhaSemanticTypingContinuation(before: before, replacing: range, with: "Z", after: after))
            XCTAssertEqual(after.marks.first?.range.length, 1)
            XCTAssertEqual(after.marks.first?.range.location, position == 0 ? 1 : 0)
        }
    }

    func testChangedNativeTextIdentityOrSelectionCannotReuseTypingIntent() throws {
        let identity = try anchor(), range = NSRange(location: 0, length: 1)
        let before = try PinkhaSemanticText(text: "A", marks: [.init(anchor: identity, range: range)])
        let after = try before.replacing(range, with: "C").after
        let typing = try XCTUnwrap(PinkhaSemanticTypingContinuation(before: before, replacing: range, with: "C", after: after))
        let other = try PinkhaSemanticTextAnchor(spaceID: "space", objectID: "object")
        for changed in [try PinkhaSemanticText(text: "D", marks: after.marks),
                        try PinkhaSemanticText(text: "C", marks: [.init(anchor: other, range: range)]),
                        try PinkhaSemanticText(text: "C", marks: [])] {
            XCTAssertNil(try typing.continuing(in: changed, range: typing.caret, with: "h"))
        }
        XCTAssertNil(try typing.continuing(in: after, range: .init(location: 0, length: 0), with: "h"))
        XCTAssertNil(try typing.continuing(in: after, range: .init(location: 0, length: 1), with: "h"))
        XCTAssertNil(try typing.continuing(in: after, range: typing.caret, with: ""))
    }

    func testDeletionDoesNotResurrectAnchorAndUnverifiedResultCannotCreateContinuation() throws {
        let identity = try anchor(), range = NSRange(location: 0, length: 1)
        let before = try PinkhaSemanticText(text: "A", marks: [.init(anchor: identity, range: range)])
        let deleted = try before.replacing(range, with: "").after
        XCTAssertTrue(deleted.marks.isEmpty)
        XCTAssertNil(try PinkhaSemanticTypingContinuation(before: before, replacing: range, with: "", after: deleted))
        XCTAssertThrowsError(try PinkhaSemanticTypingContinuation(before: before, replacing: range, with: "C",
            after: PinkhaSemanticText(text: "C", marks: []))) {
            XCTAssertEqual($0 as? PinkhaSemanticTextAnchorError, .changedText)
        }
    }
}
