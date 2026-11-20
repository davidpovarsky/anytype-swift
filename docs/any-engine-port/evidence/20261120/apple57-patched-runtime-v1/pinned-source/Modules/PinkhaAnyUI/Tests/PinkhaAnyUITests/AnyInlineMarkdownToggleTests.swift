import Foundation
import Testing
@testable import PinkhaAnyUI

@Suite("Reversible inline styles preserve native text and untouched markup")
struct AnyInlineMarkdownToggleTests {
    @Test func aSelectedWholeStyleCanBeRemovedAndAddedAgain() throws {
        for (source, trait) in [("**שלום**", AnyInlineTraits.bold),
                                ("_שלום_", .italic), ("~~שלום~~", .strike),
                                ("\u{60}שלום\u{60}", .code)] {
            let value = AnyInlineMarkdown(source)
            let range = NSRange(location: 0, length: value.display.utf16.count)
            let unstyled = try value.toggling(trait, to: range)
            #expect(unstyled == "שלום")
            let restored = AnyInlineMarkdown(try AnyInlineMarkdown(unstyled).toggling(trait, to: range))
            #expect(restored.display.utf8.elementsEqual(value.display.utf8))
            #expect(restored.runs.allSatisfy { $0.traits == trait })
        }
    }

    @Test func addOnlyAPIStillRejectsAlreadyStyledText() {
        let value = AnyInlineMarkdown("**existing**")
        #expect(throws: AnyInlineTextError.unsupportedFormattingChange) {
            try value.adding(.bold, to: .init(location: 0, length: 8))
        }
    }

    @Test func partialStrongRemovalKeepsBothUnselectedSidesStyled() throws {
        let value = AnyInlineMarkdown("before **אבגדהו** after")
        let range = (value.display as NSString).range(of: "גד")
        let result = try value.toggling(.bold, to: range)
        #expect(result == "before **אב**גד**הו** after")
        let projected = AnyInlineMarkdown(result)
        #expect(projected.display == value.display)
        #expect(try projected.sourceRange(for: range) == (result as NSString).range(of: "גד"))
        let outside = projected.runs.filter { NSIntersectionRange($0.displayRange, range).length == 0 }
        #expect(outside.filter { "אבהו".contains(projected.display.substring($0.displayRange)) }
            .allSatisfy { $0.traits.contains(.bold) })
    }

    @Test func underscoreSplitUsesRepresentableStrongDelimiters() throws {
        let value = AnyInlineMarkdown("__abcdef__")
        let result = try value.toggling(.bold, to: .init(location: 2, length: 2))
        #expect(result == "**ab**cd**ef**")
        #expect(AnyInlineMarkdown(result).display == "abcdef")
    }

    @Test func mixedSelectionAppliesStyleAndKeepsNestedStylesAndExactLinkDestination() throws {
        let original = "plain **bold** _italic_ [קישור](https://example.invalid/a%20b?q=1&x=2)"
        let value = AnyInlineMarkdown(original)
        let range = NSRange(location: 0, length: value.display.utf16.count)
        let added = try value.toggling(.bold, to: range)
        #expect(added == "**plain bold _italic_ [קישור](https://example.invalid/a%20b?q=1&x=2)**")
        let marked = AnyInlineMarkdown(added)
        #expect(marked.runs.allSatisfy { $0.traits.contains(.bold) })
        let italicRange = (value.display as NSString).range(of: "italic")
        #expect(marked.runs.filter { NSIntersectionRange($0.displayRange, italicRange).length > 0 }
            .allSatisfy { $0.traits == [.bold, .italic] })
        #expect(marked.runs.compactMap(\.link).allSatisfy {
            $0.absoluteString == "https://example.invalid/a%20b?q=1&x=2"
        })
        let removed = try marked.toggling(.bold, to: range)
        #expect(removed == "plain bold _italic_ [קישור](https://example.invalid/a%20b?q=1&x=2)")
    }

    @Test func removingOuterMarkPreservesNestedKnownFormattingBytes() throws {
        let value = AnyInlineMarkdown("left **a _ב_ \u{60}c*d\u{60}** right")
        let range = (value.display as NSString).range(of: "a ב c*d")
        #expect(try value.toggling(.bold, to: range) == "left a _ב_ \u{60}c*d\u{60} right")
    }

    @Test func linkLabelStyleRemovalDoesNotTouchDestinationOrOtherSource() throws {
        let source = #"left [**שָׁלוֹם 😀**](https://example.invalid/a%20b?q=1&x=2) \*literal\* right"#
        let value = AnyInlineMarkdown(source)
        let range = (value.display as NSString).range(of: "שָׁלוֹם 😀")
        let output = try value.toggling(.bold, to: range)
        #expect(output == #"left [שָׁלוֹם 😀](https://example.invalid/a%20b?q=1&x=2) \*literal\* right"#)
        #expect(AnyInlineMarkdown(output).display.utf8.elementsEqual(value.display.utf8))
    }

    @Test func codeRemovalEscapesLiteralMarkdownAndCanRoundTrip() throws {
        let source = #"\u{60}a*b_c\d\u{60}"#.replacingOccurrences(of: #"\u{60}"#, with: "\u{60}")
        let value = AnyInlineMarkdown(source)
        let range = NSRange(location: 0, length: value.display.utf16.count)
        let plain = try value.toggling(.code, to: range)
        #expect(plain == #"a\*b\_c\\d"#)
        #expect(AnyInlineMarkdown(plain).display == #"a*b_c\d"#)
        #expect(try AnyInlineMarkdown(plain).toggling(.code, to: range) == source)
    }

    @Test func nestedAdditionChoosesARepresentableMarkerWithoutFlatteningExistingBold() throws {
        let value = AnyInlineMarkdown("**שלום**")
        let result = try value.toggling(.italic, to: .init(location: 0, length: 4))
        #expect(AnyInlineMarkdown(result).display == "שלום")
        #expect(AnyInlineMarkdown(result).runs.allSatisfy { $0.traits == [.bold, .italic] })
        #expect(result.contains("שלום"))
        #expect(try AnyInlineMarkdown(result).toggling(.italic, to: .init(location: 0, length: 4)) == "**שלום**")
    }

    @Test func partialCrossingOfKnownContainerIsExplicitlyRefused() {
        let value = AnyInlineMarkdown("ab **cd** ef")
        #expect(throws: AnyInlineTextError.selectionCrossesMarkup) {
            try value.toggling(.bold, to: .init(location: 1, length: 3))
        }
        #expect(value.source == "ab **cd** ef")
    }

    @Test func aWhitespaceSplitCannotSilentlyRemoveUnselectedStyle() {
        let value = AnyInlineMarkdown("**one two**")
        #expect(throws: AnyInlineTextError.unsupportedFormattingChange) {
            try value.toggling(.bold, to: .init(location: 4, length: 3))
        }
        #expect(value.source == "**one two**")
    }

    @Test func unsupportedSyntaxAndLiteralBlocksRemainUnchanged() {
        for source in ["<b>שלום</b>", "&amp;", "![image](https://example.invalid/a)"] {
            let value = AnyInlineMarkdown(source)
            #expect(throws: AnyInlineTextError.unsupportedMarkup) {
                try value.toggling(.bold, to: .init(location: 0, length: 1))
            }
            #expect(value.source == source)
        }
        let literal = AnyInlineMarkdown(literal: "**source code**")
        #expect(throws: AnyInlineTextError.unsupportedFormattingChange) {
            try literal.toggling(.bold, to: .init(location: 0, length: 2))
        }
    }

    @Test func UTF16SurrogateBoundaryAndInvalidTraitsAreRefused() {
        let value = AnyInlineMarkdown("**😀שלום**")
        for range in [NSRange(location: 1, length: 1),
                      .init(location: NSNotFound, length: 1), .init(location: -1, length: 1)] {
            #expect(throws: AnyInlineTextError.invalidUTF16Range) {
                try value.toggling(.bold, to: range)
            }
        }
        #expect(throws: AnyInlineTextError.unsupportedFormattingChange) {
            try value.toggling([.bold, .italic], to: .init(location: 0, length: 2))
        }
        #expect(throws: AnyInlineTextError.unsupportedFormattingChange) {
            try value.toggling(.bold, to: .init(location: 0, length: 0))
        }
    }

    @Test func canonicallyEquivalentUnicodeIsNotRewritten() throws {
        let literal = "e\u{301} שָׁלוֹם 😀"
        let value = AnyInlineMarkdown("prefix **" + literal + "** suffix")
        let range = (value.display as NSString).range(of: literal)
        let result = try value.toggling(.bold, to: range)
        #expect(result.utf8.elementsEqual(("prefix " + literal + " suffix").utf8))
    }
    @Test func combiningMarksCannotHideLiteralMarkdownDelimitersFromEscaping() throws {
        for literal in ["*\u{301}שלום*\u{301}", "_\u{301}שלום_\u{301}",
                        "\u{60}\u{301}שלום\u{60}\u{301}", "*\u{fe0f}שלום*\u{fe0f}"] {
            let projected = AnyInlineMarkdown(AnyInlineMarkdown.escapeLiteral(literal))
            #expect(projected.isEditable)
            #expect(projected.display.utf8.elementsEqual(literal.utf8))
            #expect(projected.runs.allSatisfy { $0.traits.isEmpty && $0.link == nil })
            let inserted = try AnyInlineMarkdown("אב").replacing(
                displayRange: .init(location: 1, length: 0), withLiteral: literal)
            #expect(AnyInlineMarkdown(inserted).display.utf8.elementsEqual(("א" + literal + "ב").utf8))
        }
    }

}

private extension String {
    func substring(_ range: NSRange) -> String { (self as NSString).substring(with: range) }
}
