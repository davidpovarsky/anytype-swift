#if canImport(UIKit)
import UIKit
import DesignKit
import PinkhaAnyEngine
import PinkhaAnyHost

/// Render the existing native type/style with the original Anytype font catalog.
/// The received native record is never normalized or rewritten here.
@MainActor
enum AnyNativeTextTypography {
    static func font(for block: AnyEditorBlock, compatibleWith traits: UITraitCollection) -> UIFont {
        let style = style(for: block)
        // DesignKit supplies nominal bundled fonts. Start there on every render
        // so a font already scaled for a previous category is never scaled twice.
        return UIFontMetrics(forTextStyle: style.metrics).scaledFont(
            for: style.font.uiKitFont, compatibleWith: traits)
    }

    static func inlineFont(for block: AnyEditorBlock, base: UIFont,
                           bold: Bool, italic: Bool, code: Bool) -> UIFont {
        guard bold || italic || code else { return base }
        var traits = base.fontDescriptor.symbolicTraits
        if bold { traits.insert(.traitBold) }
        if italic { traits.insert(.traitItalic) }
        if code || base.isCode {
            // IBM Plex Mono has separate bundled resources for each face.
            // Register/select the exact original face before constructing it;
            // descriptor traits alone may resolve to an unregistered fallback.
            let face: FontConvertible
            switch (traits.contains(.traitBold), traits.contains(.traitItalic)) {
            case (true, true): face = FontFamily.IBMPlexMono.boldItalic
            case (true, false): face = FontFamily.IBMPlexMono.bold
            case (false, true): face = FontFamily.IBMPlexMono.italic
            case (false, false): face = FontFamily.IBMPlexMono.regular
            }
            return UIKitFontBuilder.uiKitFont(font: face, size: base.pointSize)
        }
        // The original markup path applies DesignKit's policy to its nominal
        // font: body emphasis is semibold, while heading emphasis stays bold.
        // A scaled body font does not equal UIFont.bodyRegular, so apply that
        // policy before restoring the already-scaled point size.
        var nominal = style(for: block).font.uiKitFont
        if bold { nominal = nominal.bold }
        if italic { nominal = nominal.italic }
        return UIFont(descriptor: nominal.fontDescriptor, size: base.pointSize)
    }

    private static func style(for block: AnyEditorBlock) -> (font: AnytypeFont, metrics: UIFont.TextStyle) {
        switch block.type {
        case "heading":
            let raw = block.native["style"]?["level"]
            let level: Int64?
            if let raw, case .number(let number) = raw { level = Int64(exactly: number) }
            else { level = raw?.integer }
            switch level {
            case 1: return (.title, .title1)
            case 3: return (.subheading, .headline)
            // Level 2 and legacy/unknown levels retain the previous title2 scale.
            // The catalog face, unlike a system title font, retains heading bold.
            default: return (.heading, .title2)
            }
        case "code": return (.codeBlock, .body)
        default: return (.bodyRegular, .body)
        }
    }
}
#endif
