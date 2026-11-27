#if canImport(UIKit)
import UIKit
import XCTest
@testable import PinkhaAnyUI

private final class RenderStorageEdits: NSObject, NSTextStorageDelegate {
    var changedCharacters = false
    func textStorage(_ textStorage: NSTextStorage, didProcessEditing editedMask: NSTextStorage.EditActions,
                     range editedRange: NSRange, changeInLength delta: Int) {
        changedCharacters = changedCharacters || editedMask.contains(.editedCharacters)
    }
}

@MainActor
final class AnyNativeTextRendererTests: XCTestCase {
    func testEqualNativeTextChangesAttributesWithoutReplacingCharactersOrSelection() {
        let input = UITextView()
        let text = "אב😀xyz"
        input.attributedText = NSAttributedString(string: text,
            attributes: [.foregroundColor: UIColor.red, .link: URL(string: "https://example.com")!])
        let selection = NSRange(location: 2, length: 2)
        input.selectedRange = selection
        let edits = RenderStorageEdits()
        input.textStorage.delegate = edits
        let paragraph = NSMutableParagraphStyle()
        paragraph.baseWritingDirection = .rightToLeft
        paragraph.alignment = .center
        let incoming = NSAttributedString(string: text,
            attributes: [.foregroundColor: UIColor.blue, .paragraphStyle: paragraph])

        XCTAssertTrue(AnyNativeTextRenderer.apply(incoming, to: input, isComposing: false))

        XCTAssertFalse(edits.changedCharacters)
        XCTAssertEqual(input.text, text)
        XCTAssertEqual(input.selectedRange, selection)
        XCTAssertNil(input.textStorage.attribute(.link, at: 0, effectiveRange: nil))
        let actual = input.textStorage.attribute(.paragraphStyle, at: 0, effectiveRange: nil) as? NSParagraphStyle
        XCTAssertEqual(actual?.baseWritingDirection, .rightToLeft)
        XCTAssertEqual(actual?.alignment, .center)
    }

    func testChangedNativeTextReplacesCharactersAndKeepsValidSelection() {
        let input = UITextView()
        input.text = "old native text"
        input.selectedRange = NSRange(location: 2, length: 5)
        let incoming = NSAttributedString(string: "new")
        XCTAssertTrue(AnyNativeTextRenderer.apply(incoming, to: input, isComposing: false))
        XCTAssertEqual(input.text, "new")
        XCTAssertEqual(input.selectedRange, NSRange(location: 2, length: 1))
    }

    func testMarkedTextKeepsCharactersSelectionAndAttributesUntilCommit() {
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "live marked buffer",
                                                  attributes: [.foregroundColor: UIColor.red])
        input.selectedRange = NSRange(location: 4, length: 3)
        let before = NSAttributedString(attributedString: input.attributedText)
        let selection = input.selectedRange
        let edits = RenderStorageEdits()
        input.textStorage.delegate = edits
        XCTAssertFalse(AnyNativeTextRenderer.apply(NSAttributedString(string: "older native text"),
                                                   to: input, isComposing: true))
        XCTAssertFalse(edits.changedCharacters)
        XCTAssertEqual(input.attributedText, before)
        XCTAssertEqual(input.selectedRange, selection)
    }
}
#endif
