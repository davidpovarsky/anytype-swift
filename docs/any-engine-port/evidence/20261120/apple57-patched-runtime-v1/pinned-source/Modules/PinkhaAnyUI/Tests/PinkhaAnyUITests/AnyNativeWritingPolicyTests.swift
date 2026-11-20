import Foundation
import Testing
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaKit
@testable import PinkhaAnyUI

@Suite("Native code text retains literal bytes")
struct AnyNativeCodeTextTests {
    @Test func nativeCodeNeverTreatsMarkdownOrHTMLAsFormatting() throws {
        let source = "**שָׁלוֹם** <tag>&x 😀"
        let value = AnyInlineMarkdown(literal: source)
        #expect(value.display == source)
        #expect(value.isEditable)
        let range = (source as NSString).range(of: "😀")
        #expect(try value.replacing(displayRange: range, withLiteral: "\\new * text") ==
                "**שָׁלוֹם** <tag>&x \\new * text")
    }
    @Test func nativeCodeRejectsSurrogateSplitsAndInlineFormatCommands() throws {
        let value = AnyInlineMarkdown(literal: "א😀ב")
        #expect(throws: AnyInlineTextError.invalidUTF16Range) {
            try value.replacing(displayRange: NSRange(location: 2, length: 1), withLiteral: "")
        }
        #expect(throws: AnyInlineTextError.unsupportedFormattingChange) {
            try value.adding(.bold, to: NSRange(location: 0, length: 1))
        }
    }
}

@Suite("Preserved writing policy on native block markers")
struct AnyNativeWritingPolicyTests {
    private func block(alignment: String? = nil, explicit: Bool? = nil,
                       direction: String? = nil) throws -> AnyEditorBlock {
        var style: [String: AnyJSON] = ["futureStyle": .object(["untouched": .integer(9)])]
        if let alignment { style["pinkhaTextAlignment"] = .string(alignment) }
        if let explicit { style["pinkhaAlignmentWasExplicit"] = .bool(explicit) }
        if let direction { style["pinkhaWritingDirection"] = .string(direction) }
        return try .init(native: .object(["id": .string("block"), "type": .string("paragraph"),
            "text": .string("English"), "nav": .object(["parentId": .string(""), "pos": .string("PPPP")]),
            "style": .object(style), "_ver": .object(["text": .string("version")])]))
    }
    @Test func automaticAlignmentFollowsApplicationWhileContentKeepsOwnDirection() throws {
        let value = try block(alignment: "left")
        let original = value.native
        let result = AnyNativeWritingPolicy.resolve(block: value, visibleText: "English",
            interfaceDirection: .rightToLeft, detectedTextDirection: .leftToRight)
        #expect(result.baseWritingDirection == .leftToRight)
        #expect(result.alignment == .right)
        #expect(value.native == original)
    }
    @Test func explicitAlignmentAndUnambiguousCenterSurviveLocaleChanges() throws {
        let explicit = AnyNativeWritingPolicy.resolve(block: try block(alignment: "left", explicit: true),
            visibleText: "עברית", interfaceDirection: .rightToLeft, detectedTextDirection: .rightToLeft)
        #expect(explicit.alignment == .left)
        let center = AnyNativeWritingPolicy.resolve(block: try block(alignment: "center"),
            visibleText: "English", interfaceDirection: .rightToLeft, detectedTextDirection: .leftToRight)
        #expect(center.alignment == .center)
    }
    @Test func explicitNativeDirectionSurvivesEmptyParagraphWithoutChangingAlignmentDefault() throws {
        let result = AnyNativeWritingPolicy.resolve(block: try block(direction: "rightToLeft"),
            visibleText: "", interfaceDirection: .leftToRight, detectedTextDirection: nil)
        #expect(result.baseWritingDirection == .rightToLeft)
        #expect(result.alignment == .left)
    }
}
