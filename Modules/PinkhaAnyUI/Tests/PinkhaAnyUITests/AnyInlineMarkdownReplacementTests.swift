import Foundation
import Testing
@testable import PinkhaAnyUI

@Suite("Bounded replacement across native inline formatting")
struct AnyInlineMarkdownReplacementTests {
    @Test func partialBoldToPlainReplacementKeepsUnselectedStyles() throws {
        let value = AnyInlineMarkdown("**ab** cd")
        let output = try value.replacing(displayRange: .init(location: 1, length: 3), withLiteral: "Z")
        #expect(output == "**aZ**d")
        let rendered = AnyInlineMarkdown(output)
        #expect(rendered.display == "aZd")
        #expect(rendered.runs.filter { $0.displayRange.location < 2 }.allSatisfy { $0.traits == .bold })
        #expect(rendered.runs.last?.traits.isEmpty == true)
    }
    @Test func crossingStrongAndItalicPreservesHebrewAndUnicodeBytes() throws {
        let value = AnyInlineMarkdown("left **אבגד** _הוזח_ right")
        let range = (value.display as NSString).range(of: "גד הו")
        let inserted = "😀e\u{301}"
        let output = try value.replacing(displayRange: range, withLiteral: inserted)
        #expect(output.utf8.elementsEqual(("left **אב" + inserted + "**_זח_ right").utf8))
        #expect(AnyInlineMarkdown(output).display.utf8.elementsEqual(("left אב" + inserted + "זח right").utf8))
    }
    @Test func deletionPreservesAdjacentSurvivingStylesAndOriginalMarkers() throws {
        let value = AnyInlineMarkdown("a **bc** *de* f")
        let range = (value.display as NSString).range(of: "c d")
        let output = try value.replacing(displayRange: range, withLiteral: "")
        #expect(output == "a **b***e* f")
        let rendered = AnyInlineMarkdown(output)
        #expect(rendered.display == "a be f")
        let bold = (rendered.display as NSString).range(of: "b")
        let italic = (rendered.display as NSString).range(of: "e")
        #expect(rendered.runs.filter { NSIntersectionRange($0.displayRange, bold).length > 0 }
            .allSatisfy { $0.traits == .bold })
        #expect(rendered.runs.filter { NSIntersectionRange($0.displayRange, italic).length > 0 }
            .allSatisfy { $0.traits == .italic })
    }
    @Test func nestedLinkLabelReplacementKeepsItsExactDestinationAndUnselectedLabel() throws {
        let url = "https://example.invalid/a%20b?q=1&x=2"
        let value = AnyInlineMarkdown("pre [**ab**cd](" + url + ") post")
        let output = try value.replacing(displayRange: (value.display as NSString).range(of: "bc"), withLiteral: "Z")
        #expect(output == "pre [**aZ**d](" + url + ") post")
        #expect(AnyInlineMarkdown(output).runs.compactMap(\.link).allSatisfy { $0.absoluteString == url })
    }
    @Test func plainIntoLinkReplacementRetainsTheUnselectedLinkedSuffix() throws {
        let url = "https://example.invalid/a%20b?q=1&x=2"
        let value = AnyInlineMarkdown("pre [label](" + url + ") post")
        let output = try value.replacing(displayRange: (value.display as NSString).range(of: "e la"), withLiteral: "Z")
        #expect(output == "prZ[bel](" + url + ") post")
        let rendered = AnyInlineMarkdown(output)
        #expect(rendered.display == "prZbel post")
        #expect(rendered.runs.filter { $0.displayRange.location < 3 }.allSatisfy { $0.link == nil })
    }
    @Test func wholeKnownSelectionInheritsFirstStyleAndEscapesReplacementLiterally() throws {
        let value = AnyInlineMarkdown("**bold** _italic_ ~~strike~~")
        let output = try value.replacing(displayRange: .init(location: 0, length: value.display.utf16.count),
                                         withLiteral: "*literal*")
        let rendered = AnyInlineMarkdown(output)
        #expect(rendered.display == "*literal*")
        #expect(rendered.runs.allSatisfy { $0.traits == .bold && $0.link == nil })
    }
    @Test func rawSourceOutsideAffectedContainersRemainsByteExact() throws {
        let value = AnyInlineMarkdown(#"\*left\* **ab** cd [tail](https://example.invalid/A%2fb?q=1&x=2)"#)
        let output = try value.replacing(displayRange: (value.display as NSString).range(of: "b c"), withLiteral: "Z")
        #expect(output.utf8.elementsEqual(#"\*left\* **aZ**d [tail](https://example.invalid/A%2fb?q=1&x=2)"#.utf8))
    }
    @Test func unrepresentableStyledWhitespaceIsExplicitlyRefused() {
        let value = AnyInlineMarkdown("**ab cd** ef")
        #expect(throws: AnyInlineTextError.unsupportedFormattingChange) {
            try value.replacing(displayRange: (value.display as NSString).range(of: "cd e"), withLiteral: "")
        }
        #expect(value.source == "**ab cd** ef")
    }
    @Test func unknownSyntaxAndSplitSurrogateRemainRefusedWithoutChangingSource() {
        for source in ["<b>ab</b> cd", "![alt](https://example.invalid/a) cd", "&amp; cd"] {
            let value = AnyInlineMarkdown(source)
            #expect(throws: AnyInlineTextError.unsupportedMarkup) {
                try value.replacing(displayRange: .init(location: 0, length: value.display.utf16.count), withLiteral: "x")
            }
            #expect(value.source == source)
        }
        let value = AnyInlineMarkdown("**😀ab** cd")
        #expect(throws: AnyInlineTextError.invalidUTF16Range) {
            try value.replacing(displayRange: .init(location: 1, length: 4), withLiteral: "x")
        }
    }
    @Test func caretAtStartOfCodeSpanInsertsLiteralWithoutInventingBackslashes() throws {
        let value = AnyInlineMarkdown("\u{60}ab\u{60}")
        let output = try value.replacing(displayRange: .init(location: 0, length: 0), withLiteral: "*")
        #expect(output == "\u{60}*ab\u{60}")
        #expect(AnyInlineMarkdown(output).display == "*ab")
    }
}
