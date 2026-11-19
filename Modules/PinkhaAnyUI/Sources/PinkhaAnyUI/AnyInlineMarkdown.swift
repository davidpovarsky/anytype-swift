
import Foundation

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
    private struct Container: Sendable, Equatable { let displayRange: NSRange; let sourceRange: NSRange }
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
        guard isEditable else { throw AnyInlineTextError.unsupportedMarkup }
        let count = display.utf16.count
        guard range.location >= 0, range.length >= 0, range.location <= count,
              range.length <= count - range.location,
              Self.boundary(range.location, in: display),
              Self.boundary(NSMaxRange(range), in: display) else { throw AnyInlineTextError.invalidUTF16Range }
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
        var range = try sourceRange(for: displayRange)
        if literal { return (source as NSString).replacingCharacters(in: range, with: text) }
        if text.isEmpty, let wrapper = containers.filter({ $0.displayRange == displayRange })
            .max(by: { $0.sourceRange.length < $1.sourceRange.length }) { range = wrapper.sourceRange }
        let active = runs.first(where: { NSIntersectionRange($0.displayRange, displayRange).length > 0 })
            ?? runs.last(where: { $0.displayRange.location < displayRange.location })
        let replacement = active?.traits.contains(.code) == true ? text : Self.escapeLiteral(text)
        let result = (source as NSString).replacingCharacters(in: range, with: replacement)
        let projected = AnyInlineMarkdown(result)
        let expected = (display as NSString).replacingCharacters(in: displayRange, with: text)
        guard projected.isEditable, projected.display == expected else {
            throw AnyInlineTextError.unsupportedFormattingChange
        }
        return result
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
    public static func escapeLiteral(_ value: String) -> String {
        let escaped: Set<Character> = ["\\", "*", "_", "~", "\u{60}", "[", "]", "<", ">", "&", "!"]
        return value.map { escaped.contains($0) ? "\\" + String($0) : String($0) }.joined()
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
                    if let url = URL(string: target), ["http", "https"].contains(url.scheme?.lowercased() ?? ""),
                       !target.contains("("), !target.contains(" "), link == nil {
                        let displayStart = display.utf16.count
                        parse(i + 1, labelEnd, traits: traits, link: url,
                              context: context + "/link\(i)", depth: depth + 1)
                        containers.append(.init(displayRange: .init(location: displayStart, length: display.utf16.count - displayStart),
                                                sourceRange: .init(location: i, length: urlEnd + 1 - i)))
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
                                            sourceRange: .init(location: i, length: finish + marker.count - i)))
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
