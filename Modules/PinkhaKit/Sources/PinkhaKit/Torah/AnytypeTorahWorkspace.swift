import Foundation
import TorahInspectorCore

/// Reusable source-access facade. Despite its host-facing name, this type has
/// no dependency on Anytype storage, services, protobufs, or UI.
public final class AnytypeTorahWorkspace: Sendable {
    private let registry: TorahProviderRegistry

    public init(registry: TorahProviderRegistry) {
        self.registry = registry
    }

    public static func sefaria(
        transport: any TorahHTTPTransport = URLSessionTorahTransport(),
        baseURL: URL = URL(string: "https://www.sefaria.org")!,
        topicCache: any TorahTopicCache = InMemoryTorahTopicCache(),
        hierarchyCache: any TorahHierarchyCache = InMemoryTorahHierarchyCache(),
        cacheTTL: TimeInterval = 7 * 24 * 60 * 60
    ) throws -> AnytypeTorahWorkspace {
        let client = SefariaClient(transport: transport, baseURL: baseURL)
        let reference = SefariaReferenceProvider(client: client)
        let topic = SefariaTopicProvider(client: client, cache: topicCache, ttl: cacheTTL)
        let lexical = SefariaLexicalProvider(client: client)
        let text = SefariaTextProvider(client: client)
        let relationships = SefariaRelationshipProvider(client: client)
        let hierarchy = SefariaHierarchyProvider(client: client, cache: hierarchyCache, ttl: cacheTTL)
        let registry = try TorahProviderRegistry(
            referenceProviders: [reference],
            topicProviders: [topic],
            lexicalProviders: [lexical],
            textProviders: [text],
            relationshipProviders: [relationships],
            hierarchyProviders: [hierarchy],
            defaultProviderID: reference.providerID
        )
        return AnytypeTorahWorkspace(registry: registry)
    }

    public func suggestReferences(
        _ query: String,
        limit: Int = 12,
        providerID: String? = nil
    ) async throws -> [ReferenceCandidate] {
        try await registry.reference(providerID).suggestReferences(query: query, limit: limit)
    }

    public func resolveReference(
        _ input: String,
        providerID: String? = nil
    ) async throws -> ResolvedReference {
        try await registry.reference(providerID).resolveReference(input)
    }

    public func suggestTopics(
        _ query: String,
        limit: Int = 20,
        providerID: String? = nil
    ) async throws -> [TopicCandidate] {
        try await registry.topic(providerID).suggestTopics(query: query, limit: limit)
    }

    public func resolveTopic(
        _ id: String,
        providerID: String? = nil
    ) async throws -> ResolvedTopic {
        try await registry.topic(providerID).resolveTopic(id: id)
    }

    public func refreshTopicIndexIfNeeded(providerID: String? = nil) async throws {
        try await registry.topic(providerID).refreshTopicIndexIfNeeded()
    }

    public func suggestWords(
        _ query: String,
        context: TorahLexicalContext? = nil,
        providerID: String? = nil
    ) async throws -> [WordCandidate] {
        try await registry.lexical(providerID).suggestWords(prefix: query, context: context)
    }

    public func resolveWord(
        _ surface: String,
        context: TorahLexicalContext? = nil,
        providerID: String? = nil
    ) async throws -> [ResolvedWord] {
        try await registry.lexical(providerID).resolveWord(surface: surface, context: context)
    }

    public func fetchText(
        reference: String,
        providerID: String? = nil,
        request: TorahTextRequest = TorahTextRequest()
    ) async throws -> TorahTextDocument {
        try await registry.text(providerID).fetchText(reference: reference, request: request)
    }

    /// Uses provider-returned section metadata instead of guessing from colon
    /// placement, which is unsafe for ranges and non-biblical address schemes.
    public func fetchSectionText(
        reference: String,
        providerID: String? = nil,
        request: TorahTextRequest = TorahTextRequest()
    ) async throws -> TorahTextDocument {
        let exact = try await fetchText(
            reference: reference,
            providerID: providerID,
            request: request
        )
        guard exact.sectionRef != exact.canonicalRef,
              exact.sectionRef != exact.requestedRef
        else { return exact }
        return try await fetchText(
            reference: exact.sectionRef,
            providerID: providerID,
            request: request
        )
    }

    public func links(
        for reference: String,
        providerID: String? = nil
    ) async throws -> [TorahLinkedSource] {
        try await registry.relationship(providerID).links(for: reference)
    }

    public func topics(
        for reference: String,
        providerID: String? = nil
    ) async throws -> [TorahLinkedTopic] {
        try await registry.relationship(providerID).topics(for: reference)
    }

    public func fetchSourceHierarchy(
        providerID: String? = nil
    ) async throws -> TorahSourceHierarchy {
        try await registry.hierarchy(providerID).fetchHierarchy()
    }
}
