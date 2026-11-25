import Foundation
import PinkhaAnyIntegration
import PinkhaKit

public enum AnyHeartInlineConversionError: Error, Equatable, Sendable {
    case unsupportedMark(String), unsupportedLink, overlappingLinks, unrepresentableFormatting
}

/// Converts native semantic ranges to the actual destination parser, then
/// verifies every displayed UTF16 unit and attribute. Original archive/native
/// bytes remain separate. Unsupported semantics never become unstyled prose.
public struct AnyHeartInlineConversion: Sendable {
    public let inlineMarkdown: String
    public let sourceSHA256: String
    public let visibleText: String

    public init(_ source: AnyHeartInlineProjection) throws {
        try self.init(source, semanticScope: nil)
    }

    /// The enclosing native snapshot supplies the exact original document.
    /// Semantic markers are admitted only with that explicit source scope.
    init(_ source: AnyHeartInlineProjection, sourceSpaceID: String, sourceObjectID: String) throws {
        try self.init(source, semanticScope: (sourceSpaceID, sourceObjectID))
    }

    private init(_ source: AnyHeartInlineProjection, semanticScope: (spaceID: String, objectID: String)?) throws {
        sourceSHA256 = source.sourceSHA256; visibleText = source.text
        if source.literal { inlineMarkdown = source.text; return }
        struct Style: Equatable { var traits: AnyInlineTraits = []; var link: String? }
        var expected = Array(repeating: Style(), count: source.text.utf16.count)
        func trait(_ kind: AnyHeartInlineProjection.Mark.Kind) -> AnyInlineTraits? {
            switch kind { case .bold: .bold; case .italic: .italic; case .strike: .strike; case .code: .code; default: nil }
        }
        var links: [AnyHeartInlineProjection.Mark] = []
        for mark in source.marks {
            if let value = trait(mark.kind) {
                guard mark.parameter.isEmpty else { throw AnyHeartInlineConversionError.unrepresentableFormatting }
                for i in mark.start..<mark.end { expected[i].traits.insert(value) }
            } else if mark.kind == .link {
                guard let url = URL(string: mark.parameter),
                      !mark.parameter.contains("("), !mark.parameter.contains(")"),
                      !mark.parameter.contains(" "), !mark.parameter.contains("\\"),
                      mark.parameter.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }) else {
                    throw AnyHeartInlineConversionError.unsupportedLink
                }
                if PinkhaSemanticTextAnchor.isReservedMarkerURL(url) {
                    guard let semanticScope else { throw AnyHeartInlineConversionError.unsupportedLink }
                    let anchor = try PinkhaSemanticTextAnchor(markerURL: url)
                    guard anchor.belongsTo(spaceID: semanticScope.spaceID, objectID: semanticScope.objectID) else {
                        throw PinkhaSemanticTextAnchorError.wrongDocument
                    }
                } else if !["http", "https"].contains(url.scheme?.lowercased() ?? "") {
                    throw AnyHeartInlineConversionError.unsupportedLink
                }
                for i in mark.start..<mark.end {
                    guard expected[i].link == nil else { throw AnyHeartInlineConversionError.overlappingLinks }
                    expected[i].link = url.absoluteString
                }
                links.append(mark)
            } else {
                // Object/mention links require a complete scoped native
                // identity map; underline/colors need a destination renderer.
                throw AnyHeartInlineConversionError.unsupportedMark(mark.kind.rawValue)
            }
        }
        var candidate = AnyInlineMarkdown.escapeLiteral(source.text)
        do {
            let formatting = source.marks.filter { trait($0.kind) != nil }.sorted {
                let lp = $0.kind == .code ? 0 : 1, rp = $1.kind == .code ? 0 : 1
                return (lp, $0.start, -$0.end, $0.kind.rawValue) < (rp, $1.start, -$1.end, $1.kind.rawValue)
            }
            for mark in formatting {
                let value = trait(mark.kind)!
                let current = AnyInlineMarkdown(candidate)
                // A duplicate/overlapping same-kind mark is not toggled off.
                let covered = current.runs.filter { NSIntersectionRange($0.displayRange, mark.range).length > 0 }
                if covered.allSatisfy({ $0.traits.contains(value) }) { continue }
                candidate = try current.toggling(value, to: mark.range)
            }
            for mark in links.sorted(by: { $0.start > $1.start }) {
                let parsed = AnyInlineMarkdown(candidate)
                if let url = URL(string: mark.parameter), PinkhaSemanticTextAnchor.isReservedMarkerURL(url) {
                    // The shared capture codec can enclose multiple preserved
                    // style containers without flattening their native markup.
                    candidate = try parsed.capturing(PinkhaSemanticTextAnchor(markerURL: url), displayRange: mark.range)
                    continue
                }
                let span = try parsed.sourceRange(for: mark.range)
                let label = (candidate as NSString).substring(with: span)
                candidate = (candidate as NSString).replacingCharacters(in: span, with: "[" + label + "](" + mark.parameter + ")")
            }
        } catch { throw AnyHeartInlineConversionError.unrepresentableFormatting }
        let actual = AnyInlineMarkdown(candidate)
        guard actual.isEditable, actual.display.utf8.elementsEqual(source.text.utf8) else {
            throw AnyHeartInlineConversionError.unrepresentableFormatting
        }
        var observed = Array(repeating: Style(), count: source.text.utf16.count)
        for run in actual.runs {
            for index in run.displayRange.location..<NSMaxRange(run.displayRange) {
                observed[index] = .init(traits: run.traits, link: run.link?.absoluteString)
            }
        }
        guard observed == expected else { throw AnyHeartInlineConversionError.unrepresentableFormatting }
        inlineMarkdown = candidate
    }
}
