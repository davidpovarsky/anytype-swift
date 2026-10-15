import Foundation

/// Bounded, Foundation-only normalization for Sefaria fields whose wire shape
/// may be a string or a nested array of strings. The original JSON is retained
/// separately by each provider; this helper only produces compact plain-text
/// previews for Core models.
enum SefariaJSONText {
    private static let maximumDepth = 8
    private static let maximumLength = 4_096
    private static let maximumNodes = 512

    static func preview(from value: Any?) -> String? {
        var fragments: [String] = []
        var visitedNodes = 0
        collectText(value, depth: 0, visitedNodes: &visitedNodes, fragments: &fragments)
        return boundedPlainText(fragments.joined(separator: " "))
    }

    static func lexicalDefinition(from row: [String: Any]) -> String? {
        if let flat = preview(from: row["definition"] ?? row["description"]) {
            return flat
        }
        if let content = row["content"] as? String {
            return boundedPlainText(content)
        }
        guard let content = row["content"] as? [String: Any] else { return nil }

        var definitions: [String] = []
        var visitedNodes = 0
        collectDefinitions(
            content,
            depth: 0,
            visitedNodes: &visitedNodes,
            definitions: &definitions
        )
        var seen = Set<String>()
        let unique = definitions.filter { seen.insert($0).inserted }
        return boundedPlainText(unique.joined(separator: " • "))
    }

    private static func collectText(
        _ value: Any?,
        depth: Int,
        visitedNodes: inout Int,
        fragments: inout [String]
    ) {
        guard depth <= maximumDepth, visitedNodes < maximumNodes else { return }
        visitedNodes += 1
        if let string = value as? String {
            if let text = boundedPlainText(string) { fragments.append(text) }
            return
        }
        guard let array = value as? [Any] else { return }
        for element in array {
            guard fragments.joined(separator: " ").count < maximumLength else { return }
            collectText(
                element,
                depth: depth + 1,
                visitedNodes: &visitedNodes,
                fragments: &fragments
            )
        }
    }

    private static func collectDefinitions(
        _ value: [String: Any],
        depth: Int,
        visitedNodes: inout Int,
        definitions: inout [String]
    ) {
        guard depth <= maximumDepth, visitedNodes < maximumNodes else { return }
        visitedNodes += 1
        if let definition = preview(from: value["definition"]) {
            definitions.append(definition)
        }
        guard let senses = value["senses"] as? [Any] else { return }
        for sense in senses {
            guard definitions.joined(separator: " • ").count < maximumLength,
                  let dictionary = sense as? [String: Any]
            else { continue }
            collectDefinitions(
                dictionary,
                depth: depth + 1,
                visitedNodes: &visitedNodes,
                definitions: &definitions
            )
        }
    }

    private static func boundedPlainText(_ value: String) -> String? {
        var text = value.replacingOccurrences(
            of: #"(?i)<\s*(br\s*/?|/?p|/?div|/?li)\b[^>]*>"#,
            with: " ",
            options: .regularExpression
        )
        text = text.replacingOccurrences(
            of: #"<[^>]+>"#,
            with: "",
            options: .regularExpression
        )
        text = decodeHTMLEntities(text)
        text = text.split(whereSeparator: \Character.isWhitespace).joined(separator: " ")
        guard !text.isEmpty else { return nil }
        return text.count > maximumLength ? String(text.prefix(maximumLength)) : text
    }

    private static func decodeHTMLEntities(_ value: String) -> String {
        var decoded = value
        let namedEntities = [
            "&nbsp;": " ",
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": "\"",
            "&#39;": "'",
            "&apos;": "'"
        ]
        for (entity, replacement) in namedEntities {
            decoded = decoded.replacingOccurrences(of: entity, with: replacement)
        }

        let pattern = #"&#(x?[0-9A-Fa-f]+);"#
        guard let expression = try? NSRegularExpression(pattern: pattern) else { return decoded }
        let range = NSRange(decoded.startIndex..<decoded.endIndex, in: decoded)
        for match in expression.matches(in: decoded, range: range).reversed() {
            guard let matchRange = Range(match.range(at: 0), in: decoded),
                  let valueRange = Range(match.range(at: 1), in: decoded)
            else { continue }
            let rawValue = String(decoded[valueRange])
            let radix = rawValue.hasPrefix("x") ? 16 : 10
            let digits = rawValue.hasPrefix("x") ? String(rawValue.dropFirst()) : rawValue
            guard let scalarValue = UInt32(digits, radix: radix),
                  let scalar = UnicodeScalar(scalarValue)
            else { continue }
            decoded.replaceSubrange(matchRange, with: String(scalar))
        }
        return decoded
    }
}
