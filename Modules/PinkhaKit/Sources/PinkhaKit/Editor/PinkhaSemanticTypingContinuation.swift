import Foundation

/// A live text-input continuation, never a stored anchor locator. A replacement
/// that begins inside a mark keeps the next characters of that uninterrupted
/// typing action inside it. An independently placed caret retains the ordinary
/// outside-boundary rule. The adapter must retire this value on selection,
/// focus, composition, owner or exact native-source changes.
public struct PinkhaSemanticTypingContinuation: Sendable {
    public struct Replacement: Sendable, Equatable {
        public let range: NSRange
        public let text: String
        public init(range: NSRange, text: String) { self.range = range; self.text = text }
    }

    private let expected: PinkhaSemanticText
    private let insertedRange: NSRange
    private let anchor: PinkhaSemanticTextAnchor

    public var caret: NSRange { .init(location: NSMaxRange(insertedRange), length: 0) }

    /// The exact existing edit rule must already have accepted the input. No
    /// marker is added, guessed from nearby text, or recovered from an offset.
    public init?(before: PinkhaSemanticText, replacing range: NSRange,
                 with text: String, after: PinkhaSemanticText) throws {
        guard try before.replacing(range, with: text).after == after else {
            throw PinkhaSemanticTextAnchorError.changedText
        }
        guard !text.isEmpty else { return nil }
        let inserted = NSRange(location: range.location, length: text.utf16.count)
        let covering = after.marks.filter {
            $0.range.location <= inserted.location && NSMaxRange($0.range) >= NSMaxRange(inserted)
        }
        guard covering.count == 1, let mark = covering.first else { return nil }
        expected = after; insertedRange = inserted; anchor = mark.anchor
    }

    /// Reexpress only an immediately consecutive caret insertion as a normal
    /// nonempty replacement of the text this action just inserted. The original
    /// shared replacement rule then verifies all marks and native adapters keep
    /// their complete source/version/owner CAS and unchanged write path.
    public func continuing(in current: PinkhaSemanticText, range: NSRange,
                           with text: String) throws -> Replacement? {
        try PinkhaSemanticText.validate(range, in: current.text)
        guard !text.isEmpty, current == expected, range == caret,
              current.marks.contains(where: {
                  $0.anchor == anchor && $0.range.location <= insertedRange.location &&
                  NSMaxRange($0.range) >= NSMaxRange(insertedRange)
              }) else { return nil }
        let prior = (current.text as NSString).substring(with: insertedRange)
        return .init(range: insertedRange, text: prior + text)
    }
}
