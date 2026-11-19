
import Foundation
import Testing
@testable import PinkhaAnyUI

@Suite("Lossless inline Markdown and UTF-16 selection")
struct AnyInlineMarkdownTests {
    @Test func hebrewCombiningMarksAndEmojiKeepExactUTF16Mapping() throws {
        let source = "שָׁלוֹם 😀 עולם"
        let value = AnyInlineMarkdown(source)
        #expect(value.display == source)
        let range = (source as NSString).range(of: "😀")
        #expect(try value.sourceRange(for: range) == range)
        #expect(try value.replacing(displayRange: range, withLiteral: "📖") == "שָׁלוֹם 📖 עולם")
        #expect(throws: AnyInlineTextError.invalidUTF16Range) {
            try value.sourceRange(for: NSRange(location: range.location + 1, length: 0))
        }
    }

    @Test func editingInsideBoldKeepsOriginalDelimitersAndUnrelatedMarkup() throws {
        let value = AnyInlineMarkdown("before **שלום** and *world*")
        #expect(value.display == "before שלום and world")
        let range = (value.display as NSString).range(of: "שלום")
        #expect(try value.replacing(displayRange: range, withLiteral: "תורה") == "before **תורה** and *world*")
        #expect(value.runs.filter { NSIntersectionRange($0.displayRange, range).length > 0 }.allSatisfy { $0.traits == .bold })
    }

    @Test func aCrossMarkupEditIsRefusedInsteadOfRemovingUnselectedFormatting() {
        let value = AnyInlineMarkdown("a **bold** z")
        #expect(throws: AnyInlineTextError.selectionCrossesMarkup) {
            try value.replacing(displayRange: NSRange(location: 0, length: value.display.utf16.count), withLiteral: "x")
        }
        #expect(value.source == "a **bold** z")
    }

    @Test func literalInsertionEscapesSourceWhileKeepingDisplayedCharactersExact() throws {
        let value = AnyInlineMarkdown("אב")
        let inserted = "* [x] <y> & 😀"
        let source = try value.replacing(displayRange: NSRange(location: 1, length: 0), withLiteral: inserted)
        #expect(AnyInlineMarkdown(source).display == "א" + inserted + "ב")
        #expect(AnyInlineMarkdown(source).isEditable)
    }

    @Test func deletingWholeFormattedContentRemovesItsEmptyWrapper() throws {
        let value = AnyInlineMarkdown("a **bold** z")
        let range = (value.display as NSString).range(of: "bold")
        #expect(try value.replacing(displayRange: range, withLiteral: "") == "a  z")
    }

    @Test func unsupportedMarkupRemainsExactAndCannotBeFlattenedByEditing() {
        for source in ["<span>שלום</span>", "![photo](https://example.invalid/a.png)", "&amp;", "\u{60}\u{60}code\u{60}\u{60}"] {
            let value = AnyInlineMarkdown(source)
            #expect(value.source == source)
            #expect(!value.isEditable)
            #expect(throws: AnyInlineTextError.unsupportedMarkup) {
                try value.replacing(displayRange: .init(location: 0, length: 0), withLiteral: "x")
            }
        }
    }

    @Test func codeInsertionDoesNotIntroduceEscapesAndLinkEditsRetainDestination() throws {
        let code = AnyInlineMarkdown("\u{60}abc\u{60}")
        let result = try code.replacing(displayRange: .init(location: 1, length: 0), withLiteral: "*")
        #expect(result == "\u{60}a*bc\u{60}")
        #expect(AnyInlineMarkdown(result).display == "a*bc")
        let link = AnyInlineMarkdown("[שלום](https://example.invalid/source)")
        #expect(try link.replacing(displayRange: .init(location: 0, length: 4), withLiteral: "מקור") ==
            "[מקור](https://example.invalid/source)")
        #expect(link.runs.allSatisfy { $0.link?.absoluteString == "https://example.invalid/source" })
    }

    @Test func boldFormattingDoesNotChangeVisibleProviderText() throws {
        let value = AnyInlineMarkdown("פרק א")
        let result = try value.adding(.bold, to: NSRange(location: 0, length: 3))
        #expect(result == "**פרק** א")
        #expect(AnyInlineMarkdown(result).display == value.display)
    }
}
