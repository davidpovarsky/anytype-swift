import Foundation
import Testing
import PinkhaKit
@testable import PinkhaAnyHost

@Suite("Any native inline semantic-marker codec")
struct AnySemanticAnchorCodecTests {
    private func anchor(_ number: Int = 1) throws -> PinkhaSemanticTextAnchor {
        try .init(spaceID: "space-א", objectID: "object-1", id: UUID(uuidString:
            "00000000-0000-0000-0000-00000000000\(number)")!)
    }

    @Test func capturesStyledHebrewAndReopensThePersistedNativeField() throws {
        let source = "lead **שָׁלוֹם** _world_ [web](https://example.com/path) 😀"
        let original = AnyInlineMarkdown(source)
        let range = (original.display as NSString).range(of: "שָׁלוֹם world")
        let marker = try anchor()
        let native = try original.capturing(marker, displayRange: range)
        let reopened = AnyInlineMarkdown(native)
        #expect(reopened.isEditable)
        #expect(reopened.display.utf8.elementsEqual(original.display.utf8))
        #expect(try reopened.semanticText().marks == [.init(anchor: marker, range: range)])
        #expect(native.contains("[web](https://example.com/path)"))
        #expect(reopened.runs.contains { $0.traits == .bold && $0.link?.absoluteString == marker.markerString })
        #expect(reopened.runs.contains { $0.traits == .italic && $0.link?.absoluteString == marker.markerString })
        // Saved bytes contain native link markup, not a separately persisted offset.
        #expect(native.contains(marker.markerString))
    }

    @Test func editsBeforeWithinAfterAndAtBothBoundariesUseSharedSemantics() throws {
        let marker = try anchor()
        var projection = AnyInlineMarkdown(try AnyInlineMarkdown("aa שלום zz").capturing(marker,
            displayRange: .init(location: 3, length: 4)))
        for (range, input) in [
            (NSRange(location: 0, length: 0), "😀"),
            (NSRange(location: 5, length: 0), "before"),
            (NSRange(location: 13, length: 0), "ב"),
            (NSRange(location: 16, length: 0), "after"),
            (NSRange(location: 23, length: 0), "!")
        ] {
            let expected = try projection.semanticText().replacing(range, with: input).after
            projection = AnyInlineMarkdown(try projection.replacing(displayRange: range, withLiteral: input))
            #expect(try projection.semanticText() == expected)
        }
    }

    @Test func nativeMarkerSurvivesFormattingReplacementDeletionAndExactUndoBytes() throws {
        let marker = try anchor()
        let captured = try AnyInlineMarkdown("left שלום right").capturing(marker,
            displayRange: .init(location: 5, length: 4))
        let styled = try AnyInlineMarkdown(captured).toggling(.bold, to: .init(location: 5, length: 4))
        let changed = try AnyInlineMarkdown(styled).replacing(displayRange: .init(location: 6, length: 2), withLiteral: "XX")
        #expect(try AnyInlineMarkdown(changed).semanticText().marks.first?.anchor == marker)
        #expect(try AnyInlineMarkdown(styled).semanticText() == AnyInlineMarkdown(captured).semanticText())
        let deleted = try AnyInlineMarkdown(changed).replacing(displayRange: .init(location: 5, length: 4), withLiteral: "")
        #expect(try AnyInlineMarkdown(deleted).semanticText().marks.isEmpty)
        // The editor's existing native undo captures raw source, including the marker.
        #expect(try AnyInlineMarkdown(captured).semanticText().marks.first?.anchor == marker)
    }

    @Test func reservedMalformedAndFutureMarkersStayExplicitlyUnsupported() throws {
        let valid = try anchor().markerString
        for value in [valid + "?redirect=1", valid.replacingOccurrences(of: "://v1/", with: "://v2/"),
                      "pinkha-anchor://v1/invalid", "other-app://target"] {
            let projection = AnyInlineMarkdown("[phrase](\(value))")
            #expect(!projection.isEditable)
            #expect(throws: (any Error).self) { try projection.semanticText() }
        }
        #expect(AnyInlineMarkdown("[web](https://example.com)").isEditable)
    }

    @Test func capturesNeverReplaceExistingLinksOrSplitEmojiNiqqudOrUnknownSyntax() throws {
        let marker = try anchor()
        let linked = AnyInlineMarkdown("[שלום](https://example.com)")
        #expect(throws: (any Error).self) {
            try linked.capturing(marker, displayRange: .init(location: 0, length: 4))
        }
        for (value, range) in [("😀 word", NSRange(location: 1, length: 1)),
                               ("שָ word", NSRange(location: 0, length: 1)),
                               ("<b>word</b>", NSRange(location: 0, length: 4))] {
            #expect(throws: (any Error).self) { try AnyInlineMarkdown(value).capturing(marker, displayRange: range) }
        }
        let code = AnyInlineMarkdown(literal: "שלום")
        #expect(throws: (any Error).self) { try code.capturing(marker, displayRange: .init(location: 0, length: 4)) }
    }

    @Test func aPastedLiteralCannotCreateOrCloneAnAnchor() throws {
        let marker = try anchor()
        let copied = "[שלום](\(marker.markerString))"
        let inserted = try AnyInlineMarkdown("plain ").replacing(displayRange: .init(location: 6, length: 0),
            withLiteral: copied)
        let result = AnyInlineMarkdown(inserted)
        #expect(result.display == "plain " + copied)
        #expect(try result.semanticText().marks.isEmpty)
    }
}
