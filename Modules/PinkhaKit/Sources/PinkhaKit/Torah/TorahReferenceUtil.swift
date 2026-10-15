import Foundation

public enum TorahReferenceUtil {
    public static func bookTitle(from reference: String) -> String {
        let trimmed = reference.trimmingCharacters(in: .whitespacesAndNewlines)
        let parts = trimmed.split(separator: " ")
        guard parts.count > 1 else { return trimmed }

        var bookParts: [Substring] = []
        for (index, part) in parts.enumerated() {
            let isRomanPrefix = index == 0 && ["I", "II", "III", "IV"].contains(part)
            if !isRomanPrefix, part.first?.isNumber == true { break }
            bookParts.append(part)
        }
        return bookParts.isEmpty ? trimmed : bookParts.joined(separator: " ")
    }

    /// A conservative syntactic fallback. Production section loading prefers
    /// the section identity returned by the text provider itself.
    public static func sectionRef(from reference: String) -> String {
        let trimmed = reference.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.contains("-"), let lastColon = trimmed.lastIndex(of: ":") else {
            return trimmed
        }
        return String(trimmed[..<lastColon]).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    public static func isSegmentRef(_ reference: String) -> Bool {
        reference.contains(":") && !reference.contains("-")
    }
}
