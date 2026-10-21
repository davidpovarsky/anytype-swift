import Foundation

/// Converts Sefaria's display-oriented HTML fragments into safe plain text.
///
/// Full source segments deliberately use a separate path from the bounded
/// preview normalizer: this helper never truncates, never flattens multiple
/// segments, and never mutates the raw provider payload retained by callers.
enum SefariaDisplayText {
    private static let structuralTagPattern =
        #"(?i)<\s*/?\s*(?:br|p|div|li|ul|ol|blockquote|h[1-6])\b[^>]*>"#
    private static let inlineTagPattern =
        #"(?i)<\s*/?\s*(?:a|abbr|b|bdi|bdo|cite|code|del|em|i|ins|mark|q|s|small|span|strong|sub|sup|time|u)\b[^>]*>"#
    private static let adjacentInlineTagsPattern =
        #"(?i)</\s*(?:a|abbr|b|bdi|bdo|cite|code|del|em|i|ins|mark|q|s|small|span|strong|sub|sup|time|u)\s*>\s*<\s*(?:a|abbr|b|bdi|bdo|cite|code|del|em|i|ins|mark|q|s|small|span|strong|sub|sup|time|u)\b[^>]*>"#
    private static let entityPattern = #"&(?:#(?:x[0-9A-Fa-f]+|[0-9]+)|[A-Za-z]+);"#

    static func fullSegment(_ value: String) -> String {
        guard value.contains("<") || value.contains("&") || value.contains("\r") else {
            return value
        }

        var text = value.replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")

        // Strip only a conservative allow-list of actual provider markup.
        // Entity-escaped angle brackets are decoded afterwards and therefore
        // remain visible literals instead of being mistaken for executable HTML.
        text = text.replacingOccurrences(
            of: adjacentInlineTagsPattern,
            with: " ",
            options: .regularExpression
        )
        text = text.replacingOccurrences(
            of: structuralTagPattern,
            with: "\n",
            options: .regularExpression
        )
        text = text.replacingOccurrences(
            of: inlineTagPattern,
            with: "",
            options: .regularExpression
        )

        // Two passes handle the bounded double-escaping seen in provider data
        // (`&amp;nbsp;`) without repeatedly interpreting arbitrary user text.
        for _ in 0..<2 {
            let decoded = decodeEntities(in: text)
            guard decoded != text else { break }
            text = decoded
        }

        let lines = text.split(separator: "\n", omittingEmptySubsequences: false)
            .map { line in
                line.trimmingCharacters(in: .whitespaces)
            }
        text = lines.joined(separator: "\n")
        text = text.replacingOccurrences(
            of: #"\n{3,}"#,
            with: "\n\n",
            options: .regularExpression
        )
        return text.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func decodeEntities(in value: String) -> String {
        guard let expression = try? NSRegularExpression(pattern: entityPattern) else {
            return value
        }

        var decoded = value
        let range = NSRange(value.startIndex..<value.endIndex, in: value)
        for match in expression.matches(in: value, range: range).reversed() {
            guard let sourceRange = Range(match.range, in: value) else { continue }
            let entity = String(value[sourceRange])
            guard let replacement = replacement(for: entity),
                  let destinationRange = Range(match.range, in: decoded) else { continue }
            decoded.replaceSubrange(destinationRange, with: replacement)
        }
        return decoded
    }

    private static func replacement(for entity: String) -> String? {
        if entity.hasPrefix("&#") {
            let raw = entity.dropFirst(2).dropLast()
            let isHex = raw.first == "x" || raw.first == "X"
            let digits = isHex ? raw.dropFirst() : raw[...]
            guard let scalarValue = UInt32(digits, radix: isHex ? 16 : 10),
                  let scalar = UnicodeScalar(scalarValue),
                  !scalar.properties.isNoncharacterCodePoint else { return nil }
            return String(scalar)
        }

        return switch entity.lowercased() {
        case "&nbsp;": "\u{00A0}"
        case "&amp;": "&"
        case "&lt;": "<"
        case "&gt;": ">"
        case "&quot;": "\""
        case "&apos;": "'"
        default: nil
        }
    }
}
