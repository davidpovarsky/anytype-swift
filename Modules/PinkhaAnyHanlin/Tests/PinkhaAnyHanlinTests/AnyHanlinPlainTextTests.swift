import XCTest
import Foundation
import HanlinHostContracts
@testable import PinkhaAnyHanlin

final class AnyHanlinPlainTextTests: XCTestCase {
    func testFormatsHebrewAndNestedInlineContentAsPlainText() throws {
        XCTAssertEqual(try AnyHanlinPlainText.render("**שלום _עולם_** ~~נמחק~~"), "שלום עולם נמחק")
    }
    func testEscapesEntitiesLinksAndImagesUseVisibleTextOnly() throws {
        XCTAssertEqual(try AnyHanlinPlainText.render(#"\*literal\* &amp; [label](https://example.invalid/secret) ![alt](private.png)"#),
                       "*literal* & label alt")
    }
    func testCodeSpanContentDoesNotRetainFormattingBackticks() throws {
        let tick = String(UnicodeScalar(96))
        XCTAssertEqual(try AnyHanlinPlainText.render("before \(tick)a < b && c\(tick) after"), "before a < b && c after")
    }
    func testNativeCodeBlockIsLiteralWithoutMarkdownInterpretation() throws {
        let tick = String(UnicodeScalar(96))
        let source = "**literal** <xml>\n\(tick)code\(tick) &amp;"
        XCTAssertEqual(try AnyHanlinPlainText.render(source, literalCode: true), source)
    }
    func testHardAndSoftBreaksRemainVisibleTextBoundaries() throws {
        XCTAssertEqual(try AnyHanlinPlainText.render("first  \nsecond\nthird"), "first\nsecond\nthird")
    }
    func testSmartPunctuationDoesNotRewriteOriginalText() throws {
        XCTAssertEqual(try AnyHanlinPlainText.render(#""quoted" -- ---"#), #""quoted" -- ---"#)
    }
    func testUnsupportedHTMLFailsInsteadOfLeakingMarkupAsPlainText() throws {
        XCTAssertThrowsError(try AnyHanlinPlainText.render("before <b>unsafe</b> after"))
    }
    func testByteLimitIsUTF8NotCharacterCount() throws {
        XCTAssertThrowsError(try AnyHanlinPlainText.render(String(repeating: "ש", count: 12_289)))
    }
}
