import XCTest
import Foundation
import HanlinHostContracts
import PinkhaAnyHost
@testable import PinkhaAnyHanlin

final class AnyHanlinPlainTextTests: XCTestCase {
    func testFormatsHebrewAndNestedInlineContentAsPlainText() throws {
        XCTAssertEqual(try AnyHanlinPlainText.render("**שלום _עולם_** ~~נמחק~~"), "שלום עולם נמחק")
    }
    func testEscapesAndLinksUseExactEditorVisibleTextOnly() throws {
        let source = #"\*literal\* \& [label](https://example.invalid/secret)"#
        XCTAssertEqual(try AnyHanlinPlainText.render(source), "*literal* & label")
        XCTAssertEqual(try AnyHanlinPlainText.render(source), AnyInlineMarkdown(source).display)
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
    func testInlineBreaksPreserveVisibleSpacesAndLineBoundaries() throws {
        let source = "first  \nsecond\nthird"
        XCTAssertTrue(try AnyHanlinPlainText.render(source).utf8.elementsEqual(source.utf8))
    }
    func testSmartPunctuationDoesNotRewriteOriginalText() throws {
        XCTAssertEqual(try AnyHanlinPlainText.render(#""quoted" -- ---"#), #""quoted" -- ---"#)
    }
    func testUnsupportedInlineSyntaxFailsInsteadOfInventingVisibleText() throws {
        for source in ["before <b>unsafe</b> after", "&amp;", "![alt](private.png)",
                       "\u{60}\u{60}unsupported\u{60}\u{60}"] {
            XCTAssertThrowsError(try AnyHanlinPlainText.render(source)) {
                XCTAssertEqual($0 as? HanlinHostError, .invalidRecord)
            }
        }
    }
    func testByteLimitIsUTF8NotCharacterCount() throws {
        XCTAssertThrowsError(try AnyHanlinPlainText.render(String(repeating: "ש", count: 12_289)))
    }
    func testHeadingAndListLookingInlineTextKeepsItsLiteralPrefix() throws {
        for source in ["# שלום", "## עולם", "- שלום", "+ עולם", "1. ראשון", "---", "==="] {
            XCTAssertTrue(try AnyHanlinPlainText.render(source).utf8.elementsEqual(source.utf8))
        }
    }
    func testIndentationBlankLinesAndLineEndingsAreNotDocumentNormalized() throws {
        for source in ["    שָׁלוֹם 😀", "\tשלום", "  ראשון\n\n    שני",
                       "שורה  \r\n\tשנייה\r\n", "  "] {
            XCTAssertTrue(try AnyHanlinPlainText.render(source).utf8.elementsEqual(source.utf8))
        }
    }
    func testEscapedProviderQuotePreservesEveryVisibleCharacter() throws {
        let literal = "# שָׁלוֹם e\u{301} 😀\n- [מקור] &amp; *מילים* ![alt](literal.png)\n    1. סוף"
        let raw = AnyInlineMarkdown.escapeLiteral(literal)
        XCTAssertTrue(try AnyHanlinPlainText.render(raw).utf8.elementsEqual(literal.utf8))
        XCTAssertTrue(AnyInlineMarkdown(raw).display.utf8.elementsEqual(literal.utf8))
        XCTAssertNotEqual(raw, literal) // Stored escapes are syntax, never exported as extra characters.
    }
    func testToggledFormattingAndLinksUseTheSameProjectionAsTheEditor() throws {
        let original = AnyInlineMarkdown("**שָׁלוֹם** [קישור](https://example.invalid/a%20b?q=1&x=2)")
        let source = try original.toggling(.italic, to: .init(location: 0, length: original.display.utf16.count))
        XCTAssertTrue(try AnyHanlinPlainText.render(source).utf8.elementsEqual(original.display.utf8))
        XCTAssertTrue(AnyInlineMarkdown(source).runs.filter { $0.link != nil }
            .allSatisfy { $0.link?.absoluteString == "https://example.invalid/a%20b?q=1&x=2" })
    }
    func testEscapedCombiningDelimiterGraphemesRemainExactProviderText() throws {
        for literal in ["*\u{301}שלום*\u{301}", "_\u{301}שלום_\u{301}",
                        "\u{60}\u{301}שלום\u{60}\u{301}", "*\u{fe0f}שלום*\u{fe0f}"] {
            let raw = AnyInlineMarkdown.escapeLiteral(literal)
            XCTAssertTrue(try AnyHanlinPlainText.render(raw).utf8.elementsEqual(literal.utf8))
        }
    }

}
