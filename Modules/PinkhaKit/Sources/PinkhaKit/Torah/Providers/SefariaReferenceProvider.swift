import Foundation
import TorahInspectorCore

public struct SefariaReferenceProvider: ReferenceProvider {
    public let providerID = "sefaria"
    private let client: SefariaClient

    public init(client: SefariaClient = SefariaClient()) {
        self.client = client
    }

    public func suggestReferences(query: String, limit: Int) async throws -> [ReferenceCandidate] {
        try Task.checkCancellation()
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else { return [] }

        let (data, response) = try await client.get(
            pathSegments: ["api", "name", trimmedQuery],
            query: [
                URLQueryItem(name: "type", value: "ref"),
                URLQueryItem(name: "limit", value: String(max(0, limit)))
            ]
        )
        try SefariaJSON.requireSuccess(response, operation: "reference search")
        guard let root = try SefariaJSON.object(from: data) as? [String: Any] else {
            throw TorahError.malformedResponse
        }

        let completionObjects: [[String: Any]]
        if let values = root["completion_objects"] as? [[String: Any]] {
            completionObjects = values
        } else if root["completion_objects"] == nil {
            completionObjects = []
        } else {
            throw TorahError.malformedResponse
        }

        var candidates: [ReferenceCandidate] = []
        var seen = Set<String>()
        func normalizedID(_ value: String) -> String {
            value.trimmingCharacters(in: .whitespacesAndNewlines)
                .folding(options: [.caseInsensitive, .diacriticInsensitive], locale: Locale(identifier: "en"))
        }

        if root["is_ref"] as? Bool == true,
           let exactRef = SefariaJSON.string(root, keys: ["ref", "normalized"]) {
            let match = completionObjects.first { value in
                guard let key = SefariaJSON.string(value, keys: ["key"]) else { return false }
                return normalizedID(key) == normalizedID(exactRef)
            }
            let label = SefariaJSON.string(root, keys: ["heRef", "hebrew", "he_ref", "hebrew_ref"])
                ?? match.flatMap { SefariaJSON.string($0, keys: ["title"]) }
                ?? trimmedQuery
            candidates.append(ReferenceCandidate(id: exactRef, label: label))
            seen.insert(normalizedID(exactRef))
        }

        for value in completionObjects {
            try Task.checkCancellation()
            guard let key = SefariaJSON.string(value, keys: ["key"]) else { continue }
            guard seen.insert(normalizedID(key)).inserted else { continue }
            candidates.append(ReferenceCandidate(
                id: key,
                label: SefariaJSON.string(value, keys: ["title"]) ?? key
            ))
        }

        return limit > 0 ? Array(candidates.prefix(limit)) : candidates
    }

    public func resolveReference(_ input: String) async throws -> ResolvedReference {
        try Task.checkCancellation()
        let trimmedInput = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedInput.isEmpty else { throw TorahError.invalidReference }

        let (data, response) = try await client.get(pathSegments: ["api", "ref", trimmedInput])
        if response.statusCode == 404 { throw TorahError.invalidReference }
        try SefariaJSON.requireSuccess(response, operation: "reference resolution")

        guard let root = try SefariaJSON.object(from: data) as? [String: Any] else {
            throw TorahError.malformedResponse
        }
        guard root["is_ref"] as? Bool == true else { throw TorahError.invalidReference }
        guard let canonical = SefariaJSON.string(root, keys: ["normalized", "ref"]) else {
            throw TorahError.malformedResponse
        }

        let navigation = root["navigation_refs"] as? [String: Any]
        return ResolvedReference(
            canonical: canonical,
            labelHe: SefariaJSON.string(root, keys: ["hebrew", "heRef"]) ?? canonical,
            labelEn: SefariaJSON.string(root, keys: ["ref", "normalized"]) ?? canonical,
            payload: SefariaJSON.payload(root),
            urlRef: SefariaJSON.string(root, keys: ["url_ref", "url"]),
            nodeType: SefariaJSON.string(root, keys: ["node_type"]),
            depth: root["depth"] as? Int,
            startIndexes: root["start_indexes"] as? [Int] ?? [],
            endIndexes: root["end_indexes"] as? [Int] ?? [],
            firstAvailableSectionRef: navigation.flatMap {
                SefariaJSON.string($0, keys: ["first_available_section_ref"])
            }
        )
    }
}
