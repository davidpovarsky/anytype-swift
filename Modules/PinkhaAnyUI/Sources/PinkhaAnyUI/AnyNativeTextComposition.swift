import Foundation

/// An input method edits a visible buffer while its original raw source stays
/// immutable. Each update is projected from that same baseline; a remote read
/// never becomes the base of an already visible local composition.
public struct AnyNativeTextComposition: Sendable, Equatable {
    public let baseline: AnyInlineMarkdown
    public let initialSelection: NSRange

    public init(source: String, literal: Bool = false, selection: NSRange) throws {
        let projection = literal ? AnyInlineMarkdown(literal: source) : AnyInlineMarkdown(source)
        guard source.utf8.count <= 65_536, projection.isEditable else {
            throw AnyInlineTextError.unsupportedMarkup
        }
        // A known multi-style selection can be replaced losslessly by the
        // shared codec even when it does not form one contiguous raw run.
        _ = try AnyInlineMarkdown(literal: projection.display).sourceRange(for: selection)
        self.baseline = projection; self.initialSelection = selection
    }

    public func source(display: String, selection: NSRange) throws -> String {
        guard display.utf8.count <= 65_536 else { throw AnyInlineTextError.unsupportedMarkup }
        _ = try AnyInlineMarkdown(literal: display).sourceRange(for: selection)
        if display.utf8.elementsEqual(baseline.display.utf8) { return baseline.source }
        let before = Array(baseline.display.utf16), after = Array(display.utf16)
        var prefix = 0
        while prefix < min(before.count, after.count), before[prefix] == after[prefix] { prefix += 1 }
        // Equal high surrogates do not make a valid replacement boundary.
        if !Self.boundary(prefix, in: before) || !Self.boundary(prefix, in: after) { prefix -= 1 }
        var beforeEnd = before.count, afterEnd = after.count
        while beforeEnd > prefix, afterEnd > prefix, before[beforeEnd - 1] == after[afterEnd - 1] {
            beforeEnd -= 1; afterEnd -= 1
        }
        // A shared low surrogate must remain part of the replacement too.
        if !Self.boundary(beforeEnd, in: before) || !Self.boundary(afterEnd, in: after) {
            beforeEnd += 1; afterEnd += 1
        }
        let range = NSRange(location: prefix, length: beforeEnd - prefix)
        let replacement = String(decoding: after[prefix..<afterEnd], as: UTF16.self)
        return try baseline.replacing(displayRange: range, withLiteral: replacement)
    }

    private static func boundary(_ offset: Int, in units: [UInt16]) -> Bool {
        guard offset > 0, offset < units.count else { return true }
        return !(0xD800...0xDBFF).contains(units[offset - 1]) || !(0xDC00...0xDFFF).contains(units[offset])
    }
}
