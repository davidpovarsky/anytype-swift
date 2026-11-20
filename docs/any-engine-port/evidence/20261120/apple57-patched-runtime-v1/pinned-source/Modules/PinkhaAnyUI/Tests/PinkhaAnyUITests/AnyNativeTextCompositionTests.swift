import Foundation
import Testing
@testable import PinkhaAnyUI

@Suite("Marked text projects from one immutable raw source")
struct AnyNativeTextCompositionTests {
    @Test func repeatedHebrewCombiningUpdatesPreserveBoldAndOriginalSource() throws {
        let value = try AnyNativeTextComposition(source: "**ש**", selection: .init(location: 1, length: 0))
        #expect(try value.source(display: "שָ", selection: .init(location: 2, length: 0)) == "**שָ**")
        #expect(try value.source(display: "שָׁ", selection: .init(location: 3, length: 0)) == "**שָׁ**")
        #expect(value.baseline.source == "**ש**")
    }
    @Test func sharedSurrogatesDoNotSplitTheReplacementBoundary() throws {
        let value = try AnyNativeTextComposition(source: "**😀**", selection: .init(location: 0, length: 2))
        #expect(try value.source(display: "😃", selection: .init(location: 2, length: 0)) == "**😃**")
        let sharedLow = String(UnicodeScalar(0x1FA00)!)
        #expect(try value.source(display: sharedLow, selection: .init(location: 2, length: 0)) == "**" + sharedLow + "**")
    }
    @Test func codeRemainsLiteralAndOrdinaryInputIsEscaped() throws {
        let code = try AnyNativeTextComposition(source: "a*", literal: true, selection: .init(location: 2, length: 0))
        #expect(try code.source(display: "a*[b]", selection: .init(location: 5, length: 0)) == "a*[b]")
        let plain = try AnyNativeTextComposition(source: "a", selection: .init(location: 1, length: 0))
        #expect(try plain.source(display: "a*[b]", selection: .init(location: 5, length: 0)) == "a\\*\\[b\\]")
    }
    @Test func cancellationKeepsExactLinkAndEscapeSpelling() throws {
        let raw = "[אב](https://example.test/a) \\*"
        let value = try AnyNativeTextComposition(source: raw, selection: .init(location: 0, length: 0))
        #expect(try value.source(display: value.baseline.display, selection: .init(location: 0, length: 0)).utf8.elementsEqual(raw.utf8))
    }
    @Test func knownStyleSelectionPreservesUnselectedTraitsAndOriginalSource() throws {
        let value = try AnyNativeTextComposition(source: "**ab** cd", selection: .init(location: 1, length: 3))
        let result = try value.source(display: "aZd", selection: .init(location: 2, length: 0))
        #expect(result == "**aZ**d")
        let projected = AnyInlineMarkdown(result)
        #expect(projected.display == "aZd")
        #expect(projected.runs.filter { $0.displayRange.location < 2 }.allSatisfy { $0.traits.contains(.bold) })
        #expect(projected.runs.filter { $0.displayRange.location >= 2 }.allSatisfy { !$0.traits.contains(.bold) })
        #expect(value.baseline.source == "**ab** cd")
    }
    @Test func unknownMarkupAndInvalidUTF16StayExplicit() throws {
        #expect(throws: AnyInlineTextError.unsupportedMarkup) {
            try AnyNativeTextComposition(source: "<b>ab</b>", selection: .init(location: 0, length: 0))
        }
        #expect(throws: AnyInlineTextError.invalidUTF16Range) {
            try AnyNativeTextComposition(source: "**😀**", selection: .init(location: 1, length: 0))
        }
        let value = try AnyNativeTextComposition(source: "**ab** cd", selection: .init(location: 0, length: 0))
        #expect(throws: AnyInlineTextError.invalidUTF16Range) {
            try value.source(display: "😀", selection: .init(location: 1, length: 0))
        }
    }

}
