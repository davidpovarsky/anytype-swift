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
                    || Self.normalized(topic.labelHe).contains(normalizedQuery)
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
        let decoded = Self.deduplicate(rows.compactMap(Self.decodeTopic))
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

        let title = SefariaJSON.localizedTitle(root["primaryTitle"] ?? root["titles"])
        return ResolvedTopic(
            slug: slug,
            labelHe: title.he ?? SefariaJSON.string(root, keys: ["he", "slug"]) ?? slug,
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

        let decoded = Self.deduplicate(rows.compactMap(Self.decodeTopic))
        guard !decoded.isEmpty else { throw TorahError.malformedResponse }
        try Task.checkCancellation()
        await cache.replace(
            topics: decoded,
            expiresAt: currentTime.addingTimeInterval(ttl)
        )
    }

    private static func decodeTopic(_ value: [String: Any]) -> TopicCandidate? {
        guard let slug = SefariaJSON.string(value, keys: ["slug", "key", "id"]) else { return nil }
        let title = SefariaJSON.localizedTitle(value["primaryTitle"] ?? value["title"])
        return TopicCandidate(
            id: slug,
            labelHe: title.he ?? SefariaJSON.string(value, keys: ["he", "title", "label"]) ?? slug,
            labelEn: title.en ?? SefariaJSON.string(value, keys: ["en"])
        )
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
