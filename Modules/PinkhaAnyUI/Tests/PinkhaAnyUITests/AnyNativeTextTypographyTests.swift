#if canImport(UIKit)
import UIKit
import XCTest
import DesignKit
import PinkhaAnyEngine
import PinkhaAnyHost
@testable import PinkhaAnyUI

@MainActor
final class AnyNativeTextTypographyTests: XCTestCase {
    func testNativeHeadingLevelsAndCodeUseOriginalAnytypeFacesAtBothSizes() throws {
        let large = UITraitCollection(preferredContentSizeCategory: .large)
        let accessible = UITraitCollection(preferredContentSizeCategory: .accessibilityExtraExtraExtraLarge)
        let cases: [(String, AnyJSON?, AnytypeFont)] = [
            ("heading", .integer(1), .title), ("heading", .integer(2), .heading),
            ("heading", .number(3), .subheading), ("code", nil, .codeBlock),
            ("paragraph", nil, .bodyRegular), ("quote", nil, .bodyRegular),
            ("heading", .number(2.5), .heading), ("heading", nil, .heading)
        ]
        var headingSizes = [CGFloat]()
        for (type, level, originalStyle) in cases {
            let block = try makeBlock(type: type, level: level)
            let before = block.native
            let nominal = AnyNativeTextTypography.font(for: block, compatibleWith: large)
            let scaled = AnyNativeTextTypography.font(for: block, compatibleWith: accessible)
            XCTAssertEqual(nominal.fontName, originalStyle.uiKitFont.fontName)
            XCTAssertEqual(nominal.pointSize, originalStyle.config.size, accuracy: 0.01)
            XCTAssertEqual(scaled.fontName, nominal.fontName)
            XCTAssertGreaterThan(scaled.pointSize, nominal.pointSize)
            if type == "heading" {
                XCTAssertTrue(nominal.fontDescriptor.symbolicTraits.contains(.traitBold))
                if headingSizes.count < 3 { headingSizes.append(nominal.pointSize) }
            }
            if type == "code" { XCTAssertTrue(nominal.isCode && scaled.isCode) }
            XCTAssertEqual(block.native, before, "Presentation must not normalize received native style")
        }
        XCTAssertEqual(headingSizes.count, 3)
        XCTAssertGreaterThan(headingSizes[0], headingSizes[1])
        XCTAssertGreaterThan(headingSizes[1], headingSizes[2])
    }

    func testFontRefreshRetainsHeadingEmphasisInlineCodeRTLSelectionAndMarkedBuffer() throws {
        let block = try makeBlock(type: "heading", level: .integer(1))
        let large = UITraitCollection(preferredContentSizeCategory: .large)
        let accessible = UITraitCollection(preferredContentSizeCategory: .accessibilityExtraExtraExtraLarge)
        let base = AnyNativeTextTypography.font(for: block, compatibleWith: large)
        let larger = AnyNativeTextTypography.font(for: block, compatibleWith: accessible)
        let unchanged = AnyNativeTextTypography.inlineFont(for: block, base: base, bold: false, italic: false, code: false)
        XCTAssertEqual(unchanged, base, "An unmarked run must retain the original heading face")
        let inline = AnyNativeTextTypography.inlineFont(for: block, base: larger, bold: false, italic: true, code: true)
        XCTAssertTrue(inline.isCode)
        XCTAssertEqual(inline.fontName, FontFamily.IBMPlexMono.boldItalic.name)
        XCTAssertTrue(inline.fontDescriptor.symbolicTraits.contains([.traitBold, .traitItalic]))
        XCTAssertEqual(inline.pointSize, larger.pointSize, accuracy: 0.01)
        let codeBlock = try makeBlock(type: "code", level: nil)
        let codeBase = AnyNativeTextTypography.font(for: codeBlock, compatibleWith: accessible)
        for (bold, italic, face) in [
            (true, false, FontFamily.IBMPlexMono.bold),
            (false, true, FontFamily.IBMPlexMono.italic),
            (true, true, FontFamily.IBMPlexMono.boldItalic)
        ] {
            let markedCode = AnyNativeTextTypography.inlineFont(for: codeBlock, base: codeBase, bold: bold, italic: italic, code: false)
            XCTAssertEqual(markedCode.fontName, face.name, "Each separate original bundled face must be available")
            XCTAssertEqual(markedCode.pointSize, codeBase.pointSize, accuracy: 0.01)
        }

        // Exercise the actual original markup policy at both sizes. Applying
        // .bold directly to a scaled body font would miss its semibold case.
        let bodyBlock = try makeBlock(type: "paragraph", level: nil)
        for category in [large, accessible] {
            let body = AnyNativeTextTypography.font(for: bodyBlock, compatibleWith: category)
            for (bold, italic, nominal) in [
                (true, false, UIFont.bodyRegular.bold),
                (false, true, UIFont.bodyRegular.italic),
                (true, true, UIFont.bodyRegular.bold.italic)
            ] {
                let markedBody = AnyNativeTextTypography.inlineFont(for: bodyBlock, base: body,
                    bold: bold, italic: italic, code: false)
                let expected = UIFont(descriptor: nominal.fontDescriptor, size: body.pointSize)
                XCTAssertEqual(markedBody, expected, "Body markup must retain the original DesignKit weight")
                XCTAssertEqual(markedBody.pointSize, body.pointSize, accuracy: 0.01)
            }
        }

        let input = AnyNativeTextView()
        input.blockID = "block"
        let text = "אב😀 code"
        let paragraph = NSMutableParagraphStyle()
        paragraph.baseWritingDirection = .rightToLeft
        paragraph.alignment = .center
        let link = try XCTUnwrap(URL(string: "https://example.com/native-typography"))
        func content(_ font: UIFont) -> NSAttributedString {
            NSAttributedString(string: text, attributes: [
                .font: font, .paragraphStyle: paragraph, .link: link,
                .strikethroughStyle: NSUnderlineStyle.single.rawValue
            ])
        }
        input.attributedText = content(base)
        let selection = NSRange(location: 2, length: 2)
        input.selectedRange = selection
        let edits = TypographyStorageEdits()
        input.textStorage.delegate = edits
        let update = content(inline)
        XCTAssertTrue(AnyNativeTextRenderer.apply(update, to: input, isComposing: false))
        XCTAssertFalse(edits.changedCharacters)
        XCTAssertEqual(input.text, text)
        XCTAssertEqual(input.selectedRange, selection)
        let attributes = input.textStorage.attributes(at: 0, effectiveRange: nil)
        XCTAssertEqual(attributes[.font] as? UIFont, inline)
        XCTAssertEqual(attributes[.link] as? URL, link)
        XCTAssertEqual(attributes[.strikethroughStyle] as? Int, NSUnderlineStyle.single.rawValue)
        let actualParagraph = try XCTUnwrap(attributes[.paragraphStyle] as? NSParagraphStyle)
        XCTAssertEqual(actualParagraph.baseWritingDirection, .rightToLeft)
        XCTAssertEqual(actualParagraph.alignment, .center)

        // The existing renderer's composition guard remains authoritative when
        // a size refresh coincides with an owned marked buffer.
        let before = NSAttributedString(attributedString: input.attributedText)
        XCTAssertFalse(AnyNativeTextRenderer.apply(content(base), to: input, isComposing: true))
        XCTAssertEqual(input.attributedText, before)
        XCTAssertEqual(input.selectedRange, selection)
        XCTAssertFalse(edits.changedCharacters)
    }

    private func makeBlock(type: String, level: AnyJSON?) throws -> AnyEditorBlock {
        var style: [String: AnyJSON] = ["pinkhaWritingDirection": .string("rtl"),
                                       "pinkhaTextAlignment": .string("center")]
        if let level { style["level"] = level }
        return try AnyEditorBlock(native: .object([
            "id": .string("block"), "type": .string(type), "text": .string("אב😀 code"),
            "style": .object(style), "nav": .object(["parentId": .string(""), "pos": .string("PPPP")]),
            "_ver": .object(["style": .string("native-version")])
        ]))
    }
}

private final class TypographyStorageEdits: NSObject, NSTextStorageDelegate {
    var changedCharacters = false
    func textStorage(_ textStorage: NSTextStorage, didProcessEditing editedMask: NSTextStorage.EditActions,
                     range editedRange: NSRange, changeInLength delta: Int) {
        changedCharacters = changedCharacters || editedMask.contains(.editedCharacters)
    }
}
#endif
