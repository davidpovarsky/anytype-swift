
import Foundation
import PinkhaKit

public enum AnyInlineTextError: Error, Equatable, Sendable {
    case unsupportedMarkup, invalidUTF16Range, selectionCrossesMarkup, unsupportedFormattingChange
}
public struct AnyInlineTraits: OptionSet, Sendable, Hashable {
    public let rawValue: UInt8
    public init(rawValue: UInt8) { self.rawValue = rawValue }
    public static let bold = Self(rawValue: 1), italic = Self(rawValue: 2)
    public static let strike = Self(rawValue: 4), code = Self(rawValue: 8)
}

/// Supported markup has an explicit UTF-16 source/display mapping. Unsupported
/// syntax stays intact and read-only. Rendered output never replaces raw source.
public struct AnyInlineMarkdown: Sendable, Equatable {
    public struct Run: Sendable, Equatable {
        public let displayRange: NSRange
        public let sourceRange: NSRange
        public let traits: AnyInlineTraits
        public let link: URL?
        let context: String
    }
    private struct Container: Sendable, Equatable {
        let displayRange: NSRange
        let sourceRange: NSRange
        let trait: AnyInlineTraits?
        let marker: String?
        let bodyRange: NSRange?
        let linkDestinationRange: NSRange?
        init(displayRange: NSRange, sourceRange: NSRange, trait: AnyInlineTraits? = nil,
             marker: String? = nil, bodyRange: NSRange? = nil, linkDestinationRange: NSRange? = nil) {
            self.displayRange = displayRange; self.sourceRange = sourceRange
            self.trait = trait; self.marker = marker; self.bodyRange = bodyRange
            self.linkDestinationRange = linkDestinationRange
        }
    }
    private let containers: [Container]
    private let literal: Bool
    public let source: String
    public let display: String
    public let runs: [Run]
    public let unsupportedReason: String?
    public var isEditable: Bool { unsupportedReason == nil }
    public init(_ source: String) {
        var parser = Parser(source: source)
        parser.parse(0, parser.units.count, traits: [], link: nil, context: "")
        literal = false
        self.source = source; display = parser.display
        runs = parser.runs; containers = parser.containers; unsupportedReason = parser.unsupported
    }
    /// Native code block text is literal; only ordinary text blocks contain
    /// inline Markdown. This avoids interpreting source code as formatting.
    public init(literal source: String) {
        self.literal = true; self.source = source; self.display = source
        self.containers = []; self.unsupportedReason = nil
        let range = NSRange(location: 0, length: source.utf16.count)
        self.runs = source.isEmpty ? [] : [.init(displayRange: range, sourceRange: range,
                                                traits: .code, link: nil, context: "literal")]
    }

    public func sourceRange(for range: NSRange) throws -> NSRange {
        try validateDisplayRange(range)
        if runs.isEmpty {
            guard source.isEmpty, range == NSRange(location: 0, length: 0) else {
                throw AnyInlineTextError.selectionCrossesMarkup
            }
            return .init(location: 0, length: 0)
        }
        func map(_ run: Run, _ offset: Int) throws -> Int {
            guard offset >= 0, offset <= run.displayRange.length else { throw AnyInlineTextError.invalidUTF16Range }
            if run.displayRange.length == run.sourceRange.length { return run.sourceRange.location + offset }
            if offset == 0 { return run.sourceRange.location }
            if offset == run.displayRange.length { return NSMaxRange(run.sourceRange) }
            throw AnyInlineTextError.selectionCrossesMarkup
        }
        if range.length == 0 {
            let run = runs.last(where: { $0.displayRange.location < range.location }) ?? runs[0]
            return .init(location: try map(run, range.location - run.displayRange.location), length: 0)
        }
        let selected = runs.filter { NSIntersectionRange($0.displayRange, range).length > 0 }
        guard let first = selected.first, let last = selected.last,
              selected.allSatisfy({ $0.context == first.context }) else { throw AnyInlineTextError.selectionCrossesMarkup }
        let begin = try map(first, range.location - first.displayRange.location)
        let end = try map(last, NSMaxRange(range) - last.displayRange.location)
        return .init(location: begin, length: end - begin)
    }
    public func replacing(displayRange: NSRange, withLiteral text: String) throws -> String {
        var range: NSRange
        do {
            range = try sourceRange(for: displayRange)
        } catch AnyInlineTextError.selectionCrossesMarkup {
            return try replacingAcrossMarkup(displayRange: displayRange, withLiteral: text)
        }
        if literal { return (source as NSString).replacingCharacters(in: range, with: text) }
        // A caret immediately outside a semantic marker must remain outside
        // it. Ordinary links keep their existing editing behavior. The native
        // source wrapper, not a saved selection offset, owns the anchor.
        var semanticBoundary = false
        if displayRange.length == 0 {
            for container in containers where container.trait == nil {
                guard runs.contains(where: { run in
                    Self.contains(container.sourceRange, run.sourceRange) &&
                    run.link.map(PinkhaSemanticTextAnchor.isReservedMarkerURL) == true
                }) else { continue }
                if displayRange.location == container.displayRange.location {
                    range = .init(location: container.sourceRange.location, length: 0)
                    semanticBoundary = true
                    break
                }
                if displayRange.location == NSMaxRange(container.displayRange) {
                    range = .init(location: NSMaxRange(container.sourceRange), length: 0)
                    semanticBoundary = true
                    break
                }
            }
        }
        if text.isEmpty, let wrapper = containers.filter({ $0.displayRange == displayRange })
            .max(by: { $0.sourceRange.length < $1.sourceRange.length }) { range = wrapper.sourceRange }
        let active = runs.first(where: { NSIntersectionRange($0.displayRange, displayRange).length > 0 })
            ?? runs.last(where: { $0.displayRange.location < displayRange.location }) ?? runs.first
        let replacement = !semanticBoundary && active?.traits.contains(.code) == true ? text : Self.escapeLiteral(text)
        let result = (source as NSString).replacingCharacters(in: range, with: replacement)
        let projected = AnyInlineMarkdown(result)
        let expected = (display as NSString).replacingCharacters(in: displayRange, with: text)
        guard projected.isEditable, projected.display.utf8.elementsEqual(expected.utf8) else {
            throw AnyInlineTextError.unsupportedFormattingChange
        }
        try validateSemanticReplacement(projected, range: displayRange, text: text)
        return result
    }

    /// Reconstructs current native markers; it never resolves from a prior
    /// offset or from matching visible words. Literal code blocks have none.
    public func semanticText() throws -> PinkhaSemanticText {
        guard isEditable else { throw AnyInlineTextError.unsupportedMarkup }
        let marks = try runs.compactMap { run -> PinkhaSemanticText.Mark? in
            guard let url = run.link, PinkhaSemanticTextAnchor.isReservedMarkerURL(url) else { return nil }
            return .init(anchor: try PinkhaSemanticTextAnchor(markerURL: url), range: run.displayRange)
        }
        return try .init(text: display, marks: marks)
    }

    /// Adds the canonical marker to the actual inline-Markdown field. All
    /// unrelated native bytes and displayed style/link attributes survive.
    /// Unknown/crossing syntax is refused rather than flattened to plain text.
    public func capturing(_ anchor: PinkhaSemanticTextAnchor, displayRange range: NSRange) throws -> String {
        guard !literal else { throw AnyInlineTextError.unsupportedFormattingChange }
        let before = try semanticText()
        let expected = try before.capturing(anchor, range: range,
            occupiedLinkRanges: runs.filter { $0.link != nil }.map(\.displayRange)).after
        var candidates = [NSRange]()
        if let direct = try? sourceRange(for: range) { candidates.append(direct) }
        if let formatted = try? formattingSourceRange(for: range), !candidates.contains(formatted) {
            candidates.append(formatted)
        }
        for span in candidates {
            let raw = (source as NSString).substring(with: span)
            let result = (source as NSString).replacingCharacters(in: span,
                with: "[" + raw + "](" + anchor.markerString + ")")
            let projected = AnyInlineMarkdown(result)
            guard projected.isEditable, projected.hasValidDelimiters,
                  let actual = try? projected.semanticText(), actual == expected else { continue }
            let original = styleMap(), changed = projected.styleMap()
            let compatible = original.indices.allSatisfy { index in
                var wanted = original[index]
                if NSLocationInRange(index, range) { wanted.link = anchor.markerString }
                return wanted == changed[index]
            }
            if compatible { return result }
        }
        throw AnyInlineTextError.selectionCrossesMarkup
    }

    /// Migration changes only parser-owned semantic link destinations. The
    /// shared marker codec validates the original owner and emits the exact
    /// destination identity; literal text and ordinary links are untouched.
    public func remappingSemanticAnchors(sourceSpaceID: String, sourceObjectID: String,
                                         destinationSpaceID: String, destinationObjectID: String) throws -> String {
        guard isEditable else { throw AnyInlineTextError.unsupportedMarkup }
        if literal { return source }
        let original = try semanticText()
        func remap(_ anchor: PinkhaSemanticTextAnchor) throws -> PinkhaSemanticTextAnchor {
            guard anchor.belongsTo(spaceID: sourceSpaceID, objectID: sourceObjectID) else {
                throw PinkhaSemanticTextAnchorError.wrongDocument
            }
            return try .init(spaceID: destinationSpaceID, objectID: destinationObjectID, id: anchor.id)
        }
        var replacements: [(NSRange, String)] = []
        for container in containers {
            guard let range = container.linkDestinationRange else { continue }
            let raw = (source as NSString).substring(with: range)
            guard let url = URL(string: raw) else { throw PinkhaSemanticTextAnchorError.invalidMarker }
            if PinkhaSemanticTextAnchor.isReservedMarkerURL(url) {
                let anchor = try PinkhaSemanticTextAnchor(markerURL: url)
                replacements.append((range, try remap(anchor).markerString))
            }
        }
        if replacements.isEmpty {
            guard original.marks.isEmpty else { throw AnyInlineTextError.unsupportedMarkup }
            return source
        }
        let expected = try PinkhaSemanticText(text: original.text, marks: original.marks.map {
            .init(anchor: try remap($0.anchor), range: $0.range)
        })
        var result = source
        for (range, marker) in replacements.sorted(by: { $0.0.location > $1.0.location }) {
            result = (result as NSString).replacingCharacters(in: range, with: marker)
        }
        let projected = AnyInlineMarkdown(result)
        guard projected.isEditable, projected.display.utf8.elementsEqual(display.utf8),
              try projected.semanticText() == expected else {
            throw AnyInlineTextError.unsupportedFormattingChange
        }
        let expectedStyles = try styleMap().map { style -> DisplayStyle in
            var value = style
            if let raw = value.link, let url = URL(string: raw),
               PinkhaSemanticTextAnchor.isReservedMarkerURL(url) {
                value.link = try remap(PinkhaSemanticTextAnchor(markerURL: url)).markerString
            }
            return value
        }
        guard projected.styleMap() == expectedStyles else { throw AnyInlineTextError.unsupportedFormattingChange }
        return result
    }

    private func validateSemanticReplacement(_ projected: Self, range: NSRange, text: String) throws {
        let original = try semanticText()
        guard !original.marks.isEmpty else { return }
        let expected = try original.replacing(range, with: text).after
        guard try projected.semanticText() == expected else {
            throw AnyInlineTextError.unsupportedFormattingChange
        }
    }
    private struct ReplacementPiece {
        let raw: String
        let path: [Int]
    }

    /// Rewrite only the intersected known containers. Untouched leaf source
    /// and link destinations are copied verbatim; the first selected run
    /// supplies insertion attributes, as in an edit within one style.
    private func replacingAcrossMarkup(displayRange range: NSRange, withLiteral text: String) throws -> String {
        try validateDisplayRange(range)
        guard !literal, range.length > 0, text.utf8.count <= 65_536 else {
            throw AnyInlineTextError.unsupportedFormattingChange
        }
        guard let firstSelected = runs.first(where: {
            NSIntersectionRange($0.displayRange, range).length > 0
        }) else { throw AnyInlineTextError.selectionCrossesMarkup }
        var sourceSpan = try formattingSourceRange(for: range)
        for container in containers where NSIntersectionRange(container.displayRange, range).length > 0 {
            sourceSpan = NSUnionRange(sourceSpan, container.sourceRange)
        }
        let fragmentRuns = runs.filter { Self.contains(sourceSpan, $0.sourceRange) }
        guard let first = fragmentRuns.first, let last = fragmentRuns.last,
              first.displayRange.location <= range.location,
              NSMaxRange(last.displayRange) >= NSMaxRange(range) else {
            throw AnyInlineTextError.selectionCrossesMarkup
        }
        let byID = Dictionary(uniqueKeysWithValues: containers.map { ($0.sourceRange.location, $0) })
        let sourceText = source as NSString
        func path(for run: Run) throws -> [Int] {
            try run.context.split(separator: "/").map { component in
                let digits = component.hasPrefix("link") ? component.dropFirst(4) : component
                guard let id = Int(digits), let container = byID[id],
                      Self.contains(sourceSpan, container.sourceRange) else {
                    throw AnyInlineTextError.selectionCrossesMarkup
                }
                return id
            }
        }
        func piece(_ run: Run, _ selected: NSRange) throws -> ReplacementPiece {
            func mapped(_ position: Int) throws -> Int {
                let offset = position - run.displayRange.location
                guard offset >= 0, offset <= run.displayRange.length else {
                    throw AnyInlineTextError.invalidUTF16Range
                }
                if run.displayRange.length == run.sourceRange.length { return run.sourceRange.location + offset }
                if offset == 0 { return run.sourceRange.location }
                if offset == run.displayRange.length { return NSMaxRange(run.sourceRange) }
                throw AnyInlineTextError.selectionCrossesMarkup
            }
            let start = try mapped(selected.location), end = try mapped(NSMaxRange(selected))
            return ReplacementPiece(raw: sourceText.substring(with: .init(location: start, length: end - start)),
                                    path: try path(for: run))
        }
        func serialize(_ pieces: [ReplacementPiece], markers: [AnyInlineTraits: String]) throws -> String {
            var output = "", active = [Int]()
            func delimiter(_ id: Int, opening: Bool) throws -> String {
                guard let container = byID[id], let body = container.bodyRange else {
                    throw AnyInlineTextError.selectionCrossesMarkup
                }
                if let trait = container.trait, let marker = markers[trait] { return marker }
                let span = opening
                    ? NSRange(location: container.sourceRange.location,
                              length: body.location - container.sourceRange.location)
                    : NSRange(location: NSMaxRange(body),
                              length: NSMaxRange(container.sourceRange) - NSMaxRange(body))
                return sourceText.substring(with: span)
            }
            for piece in pieces {
                var shared = 0
                while shared < active.count && shared < piece.path.count && active[shared] == piece.path[shared] {
                    shared += 1
                }
                for id in active.dropFirst(shared).reversed() { output += try delimiter(id, opening: false) }
                for id in piece.path.dropFirst(shared) { output += try delimiter(id, opening: true) }
                output += piece.raw
                active = piece.path
            }
            for id in active.reversed() { output += try delimiter(id, opening: false) }
            return output
        }
        // Require exact reconstruction before editing; invisible or unknown
        // source constructs cannot be dropped by a partial representation.
        let originalPieces = try fragmentRuns.map { try piece($0, $0.displayRange) }
        let originalFragment = sourceText.substring(with: sourceSpan)
        guard try serialize(originalPieces, markers: [:]).utf8.elementsEqual(originalFragment.utf8) else {
            throw AnyInlineTextError.selectionCrossesMarkup
        }
        var pieces = [ReplacementPiece]()
        for run in fragmentRuns where run.displayRange.location < range.location {
            let end = min(NSMaxRange(run.displayRange), range.location)
            pieces.append(try piece(run, .init(location: run.displayRange.location,
                                              length: end - run.displayRange.location)))
        }
        if !text.isEmpty {
            let raw = firstSelected.traits.contains(.code) ? text : Self.escapeLiteral(text)
            pieces.append(.init(raw: raw, path: try path(for: firstSelected)))
        }
        for run in fragmentRuns where NSMaxRange(run.displayRange) > NSMaxRange(range) {
            let start = max(run.displayRange.location, NSMaxRange(range))
            pieces.append(try piece(run, .init(location: start, length: NSMaxRange(run.displayRange) - start)))
        }
        // Try only a bounded set of equivalent known emphasis delimiters.
        let choices: [[AnyInlineTraits: String]] = [
            [:], [.bold: "**", .italic: "_"], [.bold: "__", .italic: "*"],
            [.bold: "**", .italic: "*"], [.bold: "__", .italic: "_"]
        ]
        let inherited = DisplayStyle(traits: firstSelected.traits, link: firstSelected.link?.absoluteString)
        for choice in choices {
            let candidate = sourceText.replacingCharacters(in: sourceSpan, with: try serialize(pieces, markers: choice))
            if validatesReplacement(candidate, range: range, text: text, inherited: inherited) {
                try validateSemanticReplacement(Self(candidate), range: range, text: text)
                return candidate
            }
        }
        throw AnyInlineTextError.unsupportedFormattingChange
    }

    private func validatesReplacement(_ candidate: String, range: NSRange, text: String,
                                      inherited: DisplayStyle) -> Bool {
        let projected = AnyInlineMarkdown(candidate)
        let expectedText = (display as NSString).replacingCharacters(in: range, with: text)
        guard projected.isEditable, projected.hasValidDelimiters,
              projected.display.utf8.elementsEqual(expectedText.utf8) else { return false }
        let previous = styleMap()
        let expectedStyles = Array(previous.prefix(range.location))
            + Array(repeating: inherited, count: text.utf16.count)
            + Array(previous.dropFirst(NSMaxRange(range)))
        return expectedStyles == projected.styleMap()
    }

    public func adding(_ trait: AnyInlineTraits, to range: NSRange) throws -> String {
        guard !literal, range.length > 0 else { throw AnyInlineTextError.unsupportedFormattingChange }
        let sourceRange = try self.sourceRange(for: range)
        guard !runs.filter({ NSIntersectionRange($0.displayRange, range).length > 0 })
            .contains(where: { $0.traits.contains(trait) }) else { throw AnyInlineTextError.unsupportedFormattingChange }
        let marker: String
        switch trait {
        case .bold: marker = "**"
        case .italic: marker = "*"
        case .strike: marker = "~~"
        case .code:
            let selected = (source as NSString).substring(with: sourceRange)
            guard !selected.contains("\u{60}"), !selected.contains("\\") else { throw AnyInlineTextError.unsupportedFormattingChange }
            marker = "\u{60}"
        default: throw AnyInlineTextError.unsupportedFormattingChange
        }
        let result = (source as NSString).replacingCharacters(in: sourceRange,
            with: marker + (source as NSString).substring(with: sourceRange) + marker)
        let projected = AnyInlineMarkdown(result)
        guard projected.isEditable, projected.display == display else {
            throw AnyInlineTextError.unsupportedFormattingChange
        }
        return result
    }
    /// Toggle the selected known inline style, preserving visible text, links,
    /// all unrelated traits and the original bytes outside the affected span.
    /// Whole known containers may be selected together. A partial crossing or
    /// a split that Markdown cannot represent exactly is refused explicitly.
    /// The existing adding() API retains its original add-only contract.
    public func toggling(_ trait: AnyInlineTraits, to range: NSRange) throws -> String {
        guard !literal, [.bold, .italic, .strike, .code].contains(trait) else {
            throw AnyInlineTextError.unsupportedFormattingChange
        }
        try validateDisplayRange(range)
        guard range.length > 0 else { throw AnyInlineTextError.unsupportedFormattingChange }
        let selected = runs.filter { NSIntersectionRange($0.displayRange, range).length > 0 }
        guard !selected.isEmpty else { throw AnyInlineTextError.unsupportedFormattingChange }
        for container in containers where NSIntersectionRange(container.displayRange, range).length > 0 {
            guard Self.contains(range, container.displayRange) || Self.contains(container.displayRange, range) else {
                throw AnyInlineTextError.selectionCrossesMarkup
            }
        }
        let removing = selected.allSatisfy { $0.traits.contains(trait) }
        let formattedRange = try formattingSourceRange(for: range)

        if removing {
            let enclosing = containers.filter {
                $0.trait == trait && Self.contains($0.displayRange, range)
            }.max { $0.sourceRange.length < $1.sourceRange.length }
            if let enclosing, let body = enclosing.bodyRange, let originalMarker = enclosing.marker {
                let selectedSource = enclosing.displayRange == range ? body : formattedRange
                guard Self.contains(body, selectedSource) else {
                    throw AnyInlineTextError.selectionCrossesMarkup
                }
                let prefix = (source as NSString).substring(with: .init(
                    location: body.location, length: selectedSource.location - body.location))
                let suffix = (source as NSString).substring(with: .init(
                    location: NSMaxRange(selectedSource), length: NSMaxRange(body) - NSMaxRange(selectedSource)))
                let middle = trait == .code
                    ? Self.escapeLiteral((display as NSString).substring(with: range))
                    : removingDelimiters(in: selectedSource, trait: trait)
                for marker in Self.markers(for: trait, preferred: originalMarker) {
                    func wrapped(_ text: String) -> String { text.isEmpty ? "" : marker + text + marker }
                    let replacement = wrapped(prefix) + middle + wrapped(suffix)
                    let candidate = (source as NSString).replacingCharacters(
                        in: enclosing.sourceRange, with: replacement)
                    if validatesToggle(candidate, trait: trait, range: range, removing: true) { return candidate }
                }
            } else {
                let replacement = removingDelimiters(in: formattedRange, trait: trait)
                let candidate = (source as NSString).replacingCharacters(in: formattedRange, with: replacement)
                if validatesToggle(candidate, trait: trait, range: range, removing: true) { return candidate }
            }
        } else {
            var spans = [NSRange]()
            if let direct = try? sourceRange(for: range) { spans.append(direct) }
            if !spans.contains(formattedRange) { spans.append(formattedRange) }
            for span in spans {
                // Code is literal visible content. Copying escaped source into
                // backticks would otherwise invent visible backslash characters.
                let selectedSource = trait == .code
                    ? (display as NSString).substring(with: range)
                    : removingDelimiters(in: span, trait: trait)
                for marker in Self.markers(for: trait) {
                    let candidate = (source as NSString).replacingCharacters(
                        in: span, with: marker + selectedSource + marker)
                    if validatesToggle(candidate, trait: trait, range: range, removing: false) { return candidate }
                }
            }
        }
        throw AnyInlineTextError.unsupportedFormattingChange
    }

    private func validateDisplayRange(_ range: NSRange) throws {
        guard isEditable else { throw AnyInlineTextError.unsupportedMarkup }
        let count = display.utf16.count
        guard range.location >= 0, range.length >= 0, range.location <= count,
              range.length <= count - range.location,
              Self.boundary(range.location, in: display),
              Self.boundary(NSMaxRange(range), in: display) else {
            throw AnyInlineTextError.invalidUTF16Range
        }
    }

    private static func contains(_ outer: NSRange, _ inner: NSRange) -> Bool {
        outer.location <= inner.location && NSMaxRange(outer) >= NSMaxRange(inner)
    }

    /// Extends only across wrappers whose complete displayed content was
    /// selected. A link destination or another mark cannot be cut in half.
    private func formattingSourceRange(for range: NSRange) throws -> NSRange {
        let selected = runs.filter { NSIntersectionRange($0.displayRange, range).length > 0 }
        guard let first = selected.first, let last = selected.last else {
            throw AnyInlineTextError.selectionCrossesMarkup
        }
        func offset(_ run: Run, _ value: Int) throws -> Int {
            let local = value - run.displayRange.location
            guard local >= 0, local <= run.displayRange.length else {
                throw AnyInlineTextError.invalidUTF16Range
            }
            if run.displayRange.length == run.sourceRange.length { return run.sourceRange.location + local }
            if local == 0 { return run.sourceRange.location }
            if local == run.displayRange.length { return NSMaxRange(run.sourceRange) }
            throw AnyInlineTextError.selectionCrossesMarkup
        }
        var begin = try offset(first, range.location)
        var end = try offset(last, NSMaxRange(range))
        for container in containers where Self.contains(range, container.displayRange) {
            begin = min(begin, container.sourceRange.location)
            end = max(end, NSMaxRange(container.sourceRange))
        }
        return .init(location: begin, length: end - begin)
    }

    private func removingDelimiters(in range: NSRange, trait: AnyInlineTraits) -> String {
        let value = NSMutableString(string: (source as NSString).substring(with: range))
        var removals = [NSRange]()
        for container in containers where container.trait == trait && Self.contains(range, container.sourceRange) {
            guard let marker = container.marker else { continue }
            let width = marker.utf16.count
            removals.append(.init(location: container.sourceRange.location - range.location, length: width))
            removals.append(.init(location: NSMaxRange(container.sourceRange) - width - range.location, length: width))
        }
        for removal in removals.sorted(by: { $0.location > $1.location }) {
            value.deleteCharacters(in: removal)
        }
        return value as String
    }

    private static func markers(for trait: AnyInlineTraits, preferred: String? = nil) -> [String] {
        let values: [String]
        switch trait {
        case .bold: values = ["**", "__"]
        case .italic: values = ["*", "_"]
        case .strike: values = ["~~"]
        case .code: values = ["\u{60}"]
        default: return []
        }
        guard let preferred, values.contains(preferred) else { return values }
        return [preferred] + values.filter { $0 != preferred }
    }

    private struct DisplayStyle: Equatable {
        var traits: AnyInlineTraits = []
        var link: String?
    }

    private func styleMap() -> [DisplayStyle] {
        var result = Array(repeating: DisplayStyle(), count: display.utf16.count)
        for run in runs {
            let style = DisplayStyle(traits: run.traits, link: run.link?.absoluteString)
            for index in run.displayRange.location..<NSMaxRange(run.displayRange) { result[index] = style }
        }
        return result
    }

    private func validatesToggle(_ candidate: String, trait: AnyInlineTraits,
                                 range: NSRange, removing: Bool) -> Bool {
        let projected = AnyInlineMarkdown(candidate)
        guard projected.isEditable, projected.display.utf8.elementsEqual(display.utf8),
              projected.hasValidDelimiters else { return false }
        let original = styleMap(), changed = projected.styleMap()
        guard original.count == changed.count else { return false }
        for index in original.indices {
            var expected = original[index]
            if NSLocationInRange(index, range) {
                if removing { expected.traits.remove(trait) }
                else { expected.traits.insert(trait) }
            }
            guard expected == changed[index] else { return false }
        }
        return true
    }

    /// CommonMark's Unicode flanking rules prevent a seemingly successful
    /// toggle from manufacturing literal stars/underscores in another renderer.
    /// Unsupported whitespace splits remain explicit; they are not normalized.
    private var hasValidDelimiters: Bool {
        let units = Array(source.utf16)
        func scalar(at index: Int) -> UnicodeScalar? {
            guard units.indices.contains(index) else { return nil }
            let first = units[index]
            if (0xD800...0xDBFF).contains(first), units.indices.contains(index + 1),
               (0xDC00...0xDFFF).contains(units[index + 1]) {
                return UnicodeScalar(0x10000 + (UInt32(first) - 0xD800) * 0x400 + UInt32(units[index + 1]) - 0xDC00)
            }
            return UnicodeScalar(first)
        }
        func before(_ index: Int) -> UnicodeScalar? {
            let position = index - 1
            if units.indices.contains(position), (0xDC00...0xDFFF).contains(units[position]),
               position > 0, (0xD800...0xDBFF).contains(units[position - 1]) {
                return scalar(at: position - 1)
            }
            return scalar(at: position)
        }
        func flanking(at start: Int, width: Int) -> (left: Bool, right: Bool, beforePunctuation: Bool, afterPunctuation: Bool) {
            let previous = before(start), next = scalar(at: start + width)
            let previousWhitespace = previous.map { CharacterSet.whitespacesAndNewlines.contains($0) } ?? true
            let nextWhitespace = next.map { CharacterSet.whitespacesAndNewlines.contains($0) } ?? true
            let punctuation = CharacterSet.punctuationCharacters.union(.symbols)
            let previousPunctuation = previous.map { punctuation.contains($0) } ?? false
            let nextPunctuation = next.map { punctuation.contains($0) } ?? false
            let left = !nextWhitespace && (!nextPunctuation || previousWhitespace || previousPunctuation)
            let right = !previousWhitespace && (!previousPunctuation || nextWhitespace || nextPunctuation)
            return (left, right, previousPunctuation, nextPunctuation)
        }
        for container in containers {
            guard let trait = container.trait, trait != .code, let marker = container.marker else { continue }
            let width = marker.utf16.count
            let opening = flanking(at: container.sourceRange.location, width: width)
            let closing = flanking(at: NSMaxRange(container.sourceRange) - width, width: width)
            guard opening.left, closing.right else { return false }
            if marker.first == "_" {
                guard !opening.right || opening.beforePunctuation,
                      !closing.left || closing.afterPunctuation else { return false }
            }
        }
        return true
    }

    public static func escapeLiteral(_ value: String) -> String {
        // Delimiters can share a grapheme with a combining mark or variation
        // selector. Escape the ASCII scalar without rewriting that cluster.
        let escaped: Set<UnicodeScalar> = ["\\", "*", "_", "~", "\u{60}", "[", "]", "<", ">", "&", "!"]
        return value.unicodeScalars.map { escaped.contains($0) ? "\\" + String($0) : String($0) }.joined()
    }
    private static func boundary(_ position: Int, in value: String) -> Bool {
        let units = Array(value.utf16)
        guard position > 0 && position < units.count else { return true }
        return !(0xD800...0xDBFF).contains(units[position - 1]) || !(0xDC00...0xDFFF).contains(units[position])
    }
    private struct Parser {
        let units: [UInt16]
        var display = ""
        var runs: [Run] = []
        var containers: [Container] = []
        var unsupported: String?
        init(source: String) {
            units = Array(source.utf16)
            if source.utf8.count > 65_536 { unsupported = "oversizedInlineText" }
        }
        func matches(_ marker: [UInt16], at i: Int, end: Int) -> Bool {
            i + marker.count <= end && Array(units[i..<i + marker.count]) == marker
        }
        func closing(_ marker: [UInt16], after start: Int, end: Int) -> Int? {
            var i = start
            while i + marker.count <= end {
                if units[i] == 92 { i += min(2, end - i); continue }
                if matches(marker, at: i, end: end) { return i }
                i += 1
            }
            return nil
        }
        mutating func emit(_ start: Int, _ end: Int, text: String? = nil,
                           traits: AnyInlineTraits, link: URL?, context: String) {
            let text = text ?? String(decoding: units[start..<end], as: UTF16.self)
            let offset = display.utf16.count; display += text
            runs.append(.init(displayRange: .init(location: offset, length: text.utf16.count),
                sourceRange: .init(location: start, length: end - start), traits: traits, link: link, context: context))
        }
        mutating func parse(_ start: Int, _ end: Int, traits: AnyInlineTraits, link: URL?, context: String, depth: Int = 0) {
            guard depth <= 32 else {
                unsupported = "nestedInlineMarkup"; emit(start, end, traits: traits, link: link, context: context); return
            }
            var i = start
            while i < end {
                if units[i] == 92, i + 1 < end, (33...126).contains(units[i + 1]),
                   !((48...57).contains(units[i + 1]) || (65...90).contains(units[i + 1]) || (97...122).contains(units[i + 1])) {
                    emit(i, i + 2, text: String(decoding: [units[i + 1]], as: UTF16.self),
                         traits: traits, link: link, context: context); i += 2; continue
                }
                if units[i] == 60 || units[i] == 38 { unsupported = "htmlOrEntityMarkup" }
                if units[i] == 33, i + 1 < end, units[i + 1] == 91 { unsupported = "inlineMedia" }
                if units[i] == 91, let labelEnd = closing([93, 40], after: i + 1, end: end),
                   let urlEnd = closing([41], after: labelEnd + 2, end: end) {
                    let target = String(decoding: units[(labelEnd + 2)..<urlEnd], as: UTF16.self)
                    if let url = URL(string: target),
                       (["http", "https"].contains(url.scheme?.lowercased() ?? "") ||
                         (try? PinkhaSemanticTextAnchor(markerURL: url)) != nil),
                       !target.contains("("), !target.contains(" "), link == nil {
                        let displayStart = display.utf16.count
                        parse(i + 1, labelEnd, traits: traits, link: url,
                              context: context + "/link\(i)", depth: depth + 1)
                        containers.append(.init(displayRange: .init(location: displayStart, length: display.utf16.count - displayStart),
                                                sourceRange: .init(location: i, length: urlEnd + 1 - i),
                                                bodyRange: .init(location: i + 1, length: labelEnd - i - 1),
                                                linkDestinationRange: .init(location: labelEnd + 2, length: urlEnd - labelEnd - 2)))
                        i = urlEnd + 1; continue
                    }
                    unsupported = "unsupportedLinkMarkup"
                }
                if units[i] == 96, i + 1 < end, units[i + 1] == 96 { unsupported = "multiBacktickCodeSpan" }
                if (units[i] == 42 || units[i] == 95), i + 2 < end,
                   units[i + 1] == units[i], units[i + 2] == units[i] { unsupported = "ambiguousEmphasis" }
                let options: [([UInt16], AnyInlineTraits)] = [
                    ([42, 42], .bold), ([95, 95], .bold), ([126, 126], .strike),
                    ([42], .italic), ([95], .italic), ([96], .code)]
                var consumed = false
                for (marker, trait) in options where matches(marker, at: i, end: end) {
                    let body = i + marker.count
                    guard let finish = closing(marker, after: body, end: end), finish > body else { continue }
                    if (marker == [95] || marker == [95, 95]), i > start,
                       let scalar = UnicodeScalar(units[i - 1]), CharacterSet.alphanumerics.contains(scalar) {
                        unsupported = "ambiguousUnderscoreMarkup"
                    }
                    let childContext = context + "/\(i)"
                    let displayStart = display.utf16.count
                    if trait == .code {
                        if units[body..<finish].contains(10) || units[body] == 32 || units[finish - 1] == 32 {
                            unsupported = "normalizedCodeSpan"
                        }
                        emit(body, finish, traits: traits.union(trait), link: link, context: childContext)
                    } else {
                        parse(body, finish, traits: traits.union(trait), link: link,
                              context: childContext, depth: depth + 1)
                    }
                    containers.append(.init(displayRange: .init(location: displayStart, length: display.utf16.count - displayStart),
                                            sourceRange: .init(location: i, length: finish + marker.count - i),
                                            trait: trait, marker: String(decoding: marker, as: UTF16.self),
                                            bodyRange: .init(location: body, length: finish - body)))
                    i = finish + marker.count; consumed = true; break
                }
                if consumed { continue }
                let length = (0xD800...0xDBFF).contains(units[i]) && i + 1 < end &&
                    (0xDC00...0xDFFF).contains(units[i + 1]) ? 2 : 1
                emit(i, i + length, traits: traits, link: link, context: context); i += length
            }
        }
    }
}
