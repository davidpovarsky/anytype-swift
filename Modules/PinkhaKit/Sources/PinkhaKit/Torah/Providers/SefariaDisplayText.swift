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
    private static let entityPattern = #"&(?:#(?:[xX][0-9A-Fa-f]+|[0-9]+)|[A-Za-z]+);"#
    private static let namedEntities: [String: String] = [
        "nbsp": "\u{00A0}",
        "ensp": "\u{2002}",
        "emsp": "\u{2003}",
        "thinsp": "\u{2009}",
        "hairsp": "\u{200A}",
        "shy": "\u{00AD}",
        "lrm": "\u{200E}",
        "rlm": "\u{200F}",
        "amp": "&",
        "lt": "<",
        "gt": ">",
        "quot": "\"",
        "apos": "'",
        "ndash": "\u{2013}",
        "mdash": "\u{2014}",
        "hellip": "\u{2026}",
        "lsquo": "\u{2018}",
        "rsquo": "\u{2019}",
        "sbquo": "\u{201A}",
        "ldquo": "\u{201C}",
        "rdquo": "\u{201D}",
        "bdquo": "\u{201E}",
        "prime": "\u{2032}",
        "lsaquo": "\u{2039}",
        "rsaquo": "\u{203A}",
        "laquo": "\u{00AB}",
        "raquo": "\u{00BB}",
        "copy": "\u{00A9}",
        "reg": "\u{00AE}",
        "trade": "\u{2122}",
        "sect": "\u{00A7}",
        "para": "\u{00B6}",
        "middot": "\u{00B7}",
        "bull": "\u{2022}",
        "dagger": "\u{2020}",
        "ddagger": "\u{2021}",
        "permil": "\u{2030}",
        "cent": "\u{00A2}",
        "pound": "\u{00A3}",
        "yen": "\u{00A5}",
        "euro": "\u{20AC}",
        "deg": "\u{00B0}",
        "plusmn": "\u{00B1}",
        "times": "\u{00D7}",
        "divide": "\u{00F7}",
        "micro": "\u{00B5}",
        "frac14": "\u{00BC}",
        "frac12": "\u{00BD}",
        "frac34": "\u{00BE}"
    ]

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
                  !scalar.properties.isNoncharacterCodePoint,
                  isSafeDisplayScalar(scalar) else { return nil }
            return String(scalar)
        }

        if entity == "&Prime;" { return "\u{2033}" }
        let name = entity.dropFirst().dropLast().lowercased()
        return namedEntities[name]
    }

    private static func isSafeDisplayScalar(_ scalar: UnicodeScalar) -> Bool {
        switch scalar.value {
        case 0x0000...0x0008, 0x000B...0x000C, 0x000E...0x001F, 0x007F...0x009F:
            false
        case 0x202A...0x202E, 0x2066...0x2069:
            // Directional embeddings, overrides and isolates can reorder an
            // otherwise trustworthy Hebrew reference. Named LRM/RLM remain
            // supported as narrowly scoped provider-authored marks.
            false
        default:
            true
        }
    }
}
