import Foundation
import Testing
import TorahInspectorCore
@testable import PinkhaKit

@Suite("Sefaria topic and lexical providers")
struct SefariaTopicLexicalProviderTests {
    @Test("Topic index is lazy, cached with TTL, searchable in Hebrew, and deduplicated")
    func topicCacheAndHebrewSearch() async throws {
        let baseDate = Date(timeIntervalSince1970: 1_000)
        let indexURL = "https://www.sefaria.org/api/topics?limit=0&minify=1"
        let indexJSON = #"{"topics":[{"slug":"creation","primaryTitle":{"he":"בריאה","en":"Creation"}},{"slug":"creation","primaryTitle":{"he":"כפול","en":"Duplicate"}},{"slug":"light","primaryTitle":{"he":"אור","en":"Light"}}]}"#
        let cache = InMemoryTorahTopicCache()
        let transport = MockTorahHTTPTransport(responses: [
            indexURL: MockHTTPResponse(json: indexJSON)
        ])
        let provider = SefariaTopicProvider(
            client: SefariaClient(transport: transport),
            cache: cache,
            ttl: 60,
            now: { baseDate }
        )

        #expect(await transport.urls().isEmpty)
        try await provider.refreshTopicIndexIfNeeded()
        try await provider.refreshTopicIndexIfNeeded()
        let matches = try await provider.suggestTopics(query: "בריא", limit: 10)

        #expect(matches == [TopicCandidate(id: "creation", labelHe: "בריאה", labelEn: "Creation")])
        #expect(await transport.urls() == [indexURL])
    }

    @Test("Expired topic cache retries after failure and only successful refresh is stored")
    func topicExpiryFailureAndRetry() async throws {
        let cache = InMemoryTorahTopicCache()
        let oldDate = Date(timeIntervalSince1970: 2_000)
        await cache.replace(
            topics: [TopicCandidate(id: "old", labelHe: "ישן")],
            expiresAt: oldDate.addingTimeInterval(10)
        )
        let laterDate = oldDate.addingTimeInterval(20)
        let indexURL = "https://www.sefaria.org/api/topics?limit=0&minify=1"

        let failingTransport = MockTorahHTTPTransport(responses: [
            indexURL: MockHTTPResponse(statusCode: 503, json: #"{"error":"temporary"}"#)
        ])
        let failingProvider = SefariaTopicProvider(
            client: SefariaClient(transport: failingTransport),
            cache: cache,
            ttl: 60,
            now: { laterDate }
        )
        await #expect(throws: TorahError.self) {
            try await failingProvider.refreshTopicIndexIfNeeded()
        }
        #expect(await cache.topics(now: laterDate) == nil)

        let retryTransport = MockTorahHTTPTransport(responses: [
            indexURL: MockHTTPResponse(json: #"[{"slug":"prayer","primaryTitle":{"he":"תפילה","en":"Prayer"}}]"#)
        ])
        let retryProvider = SefariaTopicProvider(
            client: SefariaClient(transport: retryTransport),
            cache: cache,
            ttl: 60,
            now: { laterDate }
        )
        try await retryProvider.refreshTopicIndexIfNeeded()
        #expect(await cache.topics(now: laterDate)?.map(\.id) == ["prayer"])
    }

    @Test("Topic search falls back to Name API and topic resolution preserves raw payload")
    func remoteTopicSearchAndResolve() async throws {
        let searchURL = "https://www.sefaria.org/api/name/Prayer?type=Topic&limit=5"
        let resolveURL = "https://www.sefaria.org/api/v2/topics/prayer"
        let transport = MockTorahHTTPTransport(responses: [
            searchURL: MockHTTPResponse(json: #"{"completion_objects":[{"slug":"prayer","primaryTitle":{"he":"תפילה","en":"Prayer"}}]}"#),
            resolveURL: MockHTTPResponse(json: #"{"slug":"prayer","primaryTitle":{"he":"תפילה","en":"Prayer"},"description":"topic"}"#)
        ])
        let provider = SefariaTopicProvider(
            client: SefariaClient(transport: transport),
            cache: InMemoryTorahTopicCache()
        )

        #expect(try await provider.suggestTopics(query: "Prayer", limit: 5).first?.id == "prayer")
        let resolved = try await provider.resolveTopic(id: "prayer")
        #expect(resolved.slug == "prayer")
        #expect(resolved.labelHe == "תפילה")
        #expect(resolved.labelEn == "Prayer")
        #expect(resolved.payload.contains("description"))
    }

    @Test("Empty topic query returns without network access")
    func emptyTopicQuery() async throws {
        let transport = MockTorahHTTPTransport(responses: [:])
        let provider = SefariaTopicProvider(client: SefariaClient(transport: transport))
        #expect(try await provider.suggestTopics(query: " ", limit: 10).isEmpty)
        #expect(await transport.urls().isEmpty)
    }

    @Test("Lexical lookup preserves context, diacritics, ambiguity and stable dictionary IDs")
    func lexicalContextAndIdentity() async throws {
        let surface = "שַׁעַר"
        let expectedURL = try SefariaClient().makeURL(
            pathSegments: ["api", "words", surface],
            query: [URLQueryItem(name: "lookup_ref", value: "Deuteronomy 6:9")]
        ).absoluteString
        let payload = #"[{"headword":"שַׁעַר","parent_lexicon":"BDB","rid":"1","definition":"gate"},{"headword":"שַׁעַר","parent_lexicon":"Jastrow","rid":"2","definition":"entrance"}]"#
        let transport = MockTorahHTTPTransport(responses: [
            expectedURL: MockHTTPResponse(json: payload)
        ])
        let provider = SefariaLexicalProvider(client: SefariaClient(transport: transport))

        let values = try await provider.resolveWord(
            surface: surface,
            context: TorahLexicalContext(canonicalReference: "Deuteronomy 6:9")
        )

        #expect(values.count == 2)
        #expect(Set(values.map(\.candidate.lexicon)) == ["BDB", "Jastrow"])
        #expect(Set(values.map(\.candidate.id)).count == 2)
        #expect(values.allSatisfy { $0.candidate.surface == surface })
        #expect(await transport.urls() == [expectedURL])
        #expect(expectedURL.contains("lookup_ref="))
    }

    @Test("Lexical lookup without context omits lookup_ref and empty results are noResults")
    func lexicalNoContextAndNoResults() async throws {
        let url = try SefariaClient().makeURL(pathSegments: ["api", "words", "שלום"]).absoluteString
        let transport = MockTorahHTTPTransport(responses: [
            url: MockHTTPResponse(json: "[]")
        ])
        let provider = SefariaLexicalProvider(client: SefariaClient(transport: transport))
        await #expect(throws: TorahError.noResults) {
            _ = try await provider.resolveWord(surface: "שלום", context: nil)
        }
        #expect(!url.contains("lookup_ref"))
    }
}
