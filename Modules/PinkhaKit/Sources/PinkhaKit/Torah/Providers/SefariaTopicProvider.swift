import Foundation
import TorahInspectorCore

public struct SefariaTopicProvider: TopicProvider {
    public let providerID = "sefaria"
    private let client: SefariaClient
    private let cache: any TorahTopicCache
    private let ttl: TimeInterval
    private let now: @Sendable () -> Date

    public init(
        client: SefariaClient = SefariaClient(),
        cache: any TorahTopicCache = InMemoryTorahTopicCache(),
        ttl: TimeInterval = 7 * 24 * 60 * 60,
        now: @escaping @Sendable () -> Date = Date.init
    ) {
        self.client = client
        self.cache = cache
        self.ttl = max(1, ttl)
        self.now = now
    }

    public func suggestTopics(query: String, limit: Int) async throws -> [TopicCandidate] {
        try Task.checkCancellation()
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else { return [] }

        if let cached = await cache.topics(now: now()) {
            let normalizedQuery = Self.normalized(trimmedQuery)
            let matches = cached.filter { topic in
                Self.normalized(topic.id).contains(normalizedQuery)
                    || Self.normalized(topic.displayTitle).contains(normalizedQuery)
                    || topic.labelHe.map { Self.normalized($0).contains(normalizedQuery) } == true
                    || topic.labelEn.map { Self.normalized($0).contains(normalizedQuery) } == true
            }
            if !matches.isEmpty {
                return limit > 0 ? Array(matches.prefix(limit)) : matches
            }
        }

        let (data, response) = try await client.get(
            pathSegments: ["api", "name", trimmedQuery],
            query: [
                URLQueryItem(name: "type", value: "Topic"),
                URLQueryItem(name: "limit", value: String(max(0, limit)))
            ]
        )
        try SefariaJSON.requireSuccess(response, operation: "topic search")
        guard let root = try SefariaJSON.object(from: data) as? [String: Any],
              let rows = root["completion_objects"] as? [[String: Any]]
        else { throw TorahError.malformedResponse }
        let responseLanguage = SefariaJSON.string(root, keys: ["lang", "language"])
        let decoded = Self.deduplicate(rows.compactMap {
            Self.decodeTopic($0, responseLanguage: responseLanguage)
        })
        if !rows.isEmpty, decoded.isEmpty { throw TorahError.malformedResponse }
        return limit > 0 ? Array(decoded.prefix(limit)) : decoded
    }

    public func resolveTopic(id: String) async throws -> ResolvedTopic {
        try Task.checkCancellation()
        let slugInput = id.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !slugInput.isEmpty else { throw TorahError.noResults }
        let (data, response) = try await client.get(pathSegments: ["api", "v2", "topics", slugInput])
        if response.statusCode == 404 { throw TorahError.noResults }
        try SefariaJSON.requireSuccess(response, operation: "topic resolution")
        guard let root = try SefariaJSON.object(from: data) as? [String: Any],
              let slug = SefariaJSON.string(root, keys: ["slug"])
        else { throw TorahError.malformedResponse }

        let title = Self.localizedTitles(
            primaryTitle: root["primaryTitle"],
            titles: root["titles"]
        )
        return ResolvedTopic(
            slug: slug,
            displayTitle: title.en ?? title.he ?? slug,
            labelHe: title.he ?? SefariaJSON.string(root, keys: ["he"]),
            labelEn: title.en ?? SefariaJSON.string(root, keys: ["en"]),
            payload: SefariaJSON.payload(root)
        )
    }

    public func refreshTopicIndexIfNeeded() async throws {
        try Task.checkCancellation()
        let currentTime = now()
        if await cache.topics(now: currentTime) != nil { return }

        let (data, response) = try await client.get(
            pathSegments: ["api", "topics"],
            query: [
                URLQueryItem(name: "limit", value: "0"),
                URLQueryItem(name: "minify", value: "1")
            ]
        )
        try SefariaJSON.requireSuccess(response, operation: "topic index request")
        let object = try SefariaJSON.object(from: data)
        let rows: [[String: Any]]
        if let direct = object as? [[String: Any]] {
            rows = direct
        } else if let root = object as? [String: Any], let nested = root["topics"] as? [[String: Any]] {
            rows = nested
        } else {
            throw TorahError.malformedResponse
        }

        let decoded = Self.deduplicate(rows.compactMap {
            Self.decodeTopic($0, responseLanguage: nil)
        })
        guard !decoded.isEmpty else { throw TorahError.malformedResponse }
        try Task.checkCancellation()
        await cache.replace(
            topics: decoded,
            expiresAt: currentTime.addingTimeInterval(ttl)
        )
    }

    private static func decodeTopic(
        _ value: [String: Any],
        responseLanguage: String?
    ) -> TopicCandidate? {
        guard let slug = SefariaJSON.string(value, keys: ["slug", "key", "id"]) else { return nil }
        let localized = localizedTitles(
            primaryTitle: value["primaryTitle"] ?? (value["title"] as? [String: Any]),
            titles: value["titles"]
        )
        let displayTitle = SefariaJSON.string(value, keys: ["title", "label"])
            ?? localized.en
            ?? localized.he
            ?? slug
        let language = SefariaJSON.string(value, keys: ["lang", "language"])
            ?? responseLanguage
        var labelHe = localized.he ?? SefariaJSON.string(value, keys: ["he"])
        var labelEn = localized.en ?? SefariaJSON.string(value, keys: ["en"])
        if labelHe == nil, labelEn == nil {
            if language?.lowercased() == "he" || containsHebrew(displayTitle) {
                labelHe = displayTitle
            } else if language?.lowercased() == "en" || !displayTitle.isEmpty {
                labelEn = displayTitle
            }
        }
        return TopicCandidate(
            id: slug,
            displayTitle: displayTitle,
            labelHe: labelHe,
            labelEn: labelEn
        )
    }

    private static func localizedTitles(
        primaryTitle: Any?,
        titles: Any?
    ) -> (he: String?, en: String?) {
        let primary = SefariaJSON.localizedTitle(primaryTitle)
        guard let rows = titles as? [[String: Any]] else { return primary }

        func title(language: String) -> String? {
            let matching = rows.filter {
                SefariaJSON.string($0, keys: ["lang", "language"])?.lowercased() == language
            }
            let preferred = matching.first { $0["primary"] as? Bool == true }
                ?? matching.first { $0["is_primary"] as? Bool == true }
                ?? matching.first
            return preferred.flatMap { SefariaJSON.string($0, keys: ["text", "title"]) }
        }

        return (primary.he ?? title(language: "he"), primary.en ?? title(language: "en"))
    }

    private static func containsHebrew(_ value: String) -> Bool {
        value.unicodeScalars.contains { (0x0590...0x05FF).contains($0.value) }
    }

    private static func deduplicate(_ topics: [TopicCandidate]) -> [TopicCandidate] {
        var seen = Set<String>()
        return topics.filter { seen.insert(normalized($0.id)).inserted }
    }

    private static func normalized(_ value: String) -> String {
        value.folding(
            options: [.caseInsensitive, .diacriticInsensitive],
            locale: Locale(identifier: "he")
        )
    }
}
