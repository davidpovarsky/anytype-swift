import Foundation
import TorahInspectorCore

public struct SefariaRelationshipProvider: RelationshipProvider {
    public let providerID = "sefaria"
    private let client: SefariaClient

    public init(client: SefariaClient = SefariaClient()) {
        self.client = client
    }

    public func links(for reference: String) async throws -> [TorahLinkedSource] {
        try Task.checkCancellation()
        let (data, response) = try await client.get(
            pathSegments: ["api", "links", reference],
            query: [URLQueryItem(name: "with_text", value: "1")]
        )
        try SefariaJSON.requireSuccess(response, operation: "links request")
        guard let rows = try SefariaJSON.object(from: data) as? [[String: Any]] else {
            throw TorahError.malformedResponse
        }

        var seen = Set<TorahLinkedSource.ID>()
        var values: [TorahLinkedSource] = []
        for row in rows {
            try Task.checkCancellation()
            guard let sourceRef = SefariaJSON.string(row, keys: ["sourceRef", "ref"]) else {
                continue
            }
            let collective = SefariaJSON.localizedTitle(row["collectiveTitle"])
            let anchors: [String]
            if let array = row["anchorRefExpanded"] as? [String] {
                anchors = array.filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            } else if let array = row["anchorRefs"] as? [String] {
                anchors = array.filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            } else if let single = SefariaJSON.string(row, keys: ["anchorRef"]) {
                anchors = [single]
            } else {
                anchors = []
            }

            let source = TorahLinkedSource(
                sourceRef: sourceRef,
                sourceHebrewRef: SefariaJSON.string(row, keys: ["sourceHeRef", "heRef"]),
                category: SefariaJSON.string(row, keys: ["category"]) ?? "Other",
                type: SefariaJSON.string(row, keys: ["type"]) ?? "link",
                collectiveTitle: collective.en,
                hebrewCollectiveTitle: collective.he,
                hebrewText: SefariaJSONText.preview(from: row["he"]),
                englishText: SefariaJSONText.preview(from: row["text"]),
                versionTitle: SefariaJSON.string(row, keys: ["versionTitle"]),
                hebrewVersionTitle: SefariaJSON.string(row, keys: ["heVersionTitle"]),
                license: SefariaJSON.string(row, keys: ["heLicense", "license"]),
                canonicalBookID: SefariaJSON.string(
                    row,
                    keys: ["index_title", "indexTitle", "sourceIndexTitle"]
                ),
                anchorRefs: anchors,
                rawProviderPayload: SefariaJSON.payload(row)
            )
            if seen.insert(source.id).inserted { values.append(source) }
        }
        if !rows.isEmpty, values.isEmpty { throw TorahError.malformedResponse }
        return values
    }

    public func topics(for reference: String) async throws -> [TorahLinkedTopic] {
        try Task.checkCancellation()
        let (data, response) = try await client.get(
            pathSegments: ["api", "ref-topic-links", reference],
            query: [URLQueryItem(name: "interface_lang", value: "english")]
        )
        try SefariaJSON.requireSuccess(response, operation: "topic links request")
        guard let rows = try SefariaJSON.object(from: data) as? [[String: Any]] else {
            throw TorahError.malformedResponse
        }

        var seen = Set<String>()
        var values: [TorahLinkedTopic] = []
        for row in rows {
            try Task.checkCancellation()
            guard let slug = SefariaJSON.string(row, keys: ["topic"]) else { continue }
            let normalizedSlug = slug.folding(
                options: [.caseInsensitive, .diacriticInsensitive],
                locale: Locale(identifier: "en")
            )
            guard seen.insert(normalizedSlug).inserted else { continue }

            let descriptions = row["descriptions"] as? [String: Any]
            let english = (descriptions?["en"] as? [String: Any]).flatMap {
                SefariaJSON.string($0, keys: ["title"])
            }
            let hebrew = (descriptions?["he"] as? [String: Any]).flatMap {
                SefariaJSON.string($0, keys: ["title"])
            }
            values.append(TorahLinkedTopic(
                slug: slug,
                titleHe: hebrew,
                titleEn: english,
                rawProviderPayload: SefariaJSON.payload(row)
            ))
        }
        if !rows.isEmpty, values.isEmpty { throw TorahError.malformedResponse }
        return values
    }
}
