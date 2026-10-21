import Foundation
import TorahInspectorCore

public struct SefariaLexicalProvider: LexicalProvider {
    public let providerID = "sefaria"
    private let client: SefariaClient

    public init(client: SefariaClient = SefariaClient()) {
        self.client = client
    }

    public func suggestWords(
        prefix: String,
        context: TorahLexicalContext?
    ) async throws -> [WordCandidate] {
        let trimmed = prefix.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return [] }
        do {
            return try await resolveWord(surface: trimmed, context: context).map(\.candidate)
        } catch TorahError.noResults {
            // Suggestions model absence as an empty collection. The explicit
            // resolve API retains its historical throwing contract below.
            return []
        }
    }

    public func resolveWord(
        surface: String,
        context: TorahLexicalContext?
    ) async throws -> [ResolvedWord] {
        try Task.checkCancellation()
        let trimmedSurface = surface.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedSurface.isEmpty else { throw TorahError.noResults }

        var query: [URLQueryItem] = []
        if let reference = context?.canonicalReference?.trimmingCharacters(in: .whitespacesAndNewlines),
           !reference.isEmpty {
            query.append(URLQueryItem(name: "lookup_ref", value: reference))
        }

        let (data, response) = try await client.get(
            pathSegments: ["api", "words", trimmedSurface],
            query: query
        )
        if response.statusCode == 404 { throw TorahError.noResults }
        try SefariaJSON.requireSuccess(response, operation: "lexical request")

        let object = try SefariaJSON.object(from: data)
        let rows: [[String: Any]]
        if let direct = object as? [[String: Any]] {
            rows = direct
        } else if let root = object as? [String: Any],
                  let nested = (root["results"] as? [[String: Any]])
                    ?? (root["entries"] as? [[String: Any]]) {
            rows = nested
        } else {
            throw TorahError.malformedResponse
        }

        var seen = Set<String>()
        var results: [ResolvedWord] = []
        for (index, row) in rows.enumerated() {
            try Task.checkCancellation()
            guard let headword = SefariaJSON.string(row, keys: ["headword", "head_word", "word"]) else {
                continue
            }
            let lexicon = SefariaJSON.string(
                row,
                keys: ["parent_lexicon", "lexicon", "lexiconName"]
            ) ?? "Sefaria Lexicon"
            let discriminator = SefariaJSON.string(row, keys: ["rid", "id", "entry_number"])
                ?? String(index)
            let identifier = [lexicon, headword, discriminator]
                .map(Self.normalized)
                .joined(separator: "|")
            guard seen.insert(identifier).inserted else { continue }

            results.append(ResolvedWord(candidate: WordCandidate(
                id: identifier,
                surface: trimmedSurface,
                headword: headword,
                lexicon: lexicon,
                description: SefariaJSONText.lexicalDefinition(from: row),
                payload: SefariaJSON.payload(row)
            )))
        }
        guard !results.isEmpty else {
            throw rows.isEmpty ? TorahError.noResults : TorahError.malformedResponse
        }
        return results
    }

    private static func normalized(_ value: String) -> String {
        value.folding(
            options: [.caseInsensitive, .diacriticInsensitive],
            locale: Locale(identifier: "he")
        )
    }
}
