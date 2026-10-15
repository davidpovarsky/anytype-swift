import TorahInspectorCore

public protocol ReferenceProvider: Sendable {
    var providerID: String { get }
    func suggestReferences(query: String, limit: Int) async throws -> [ReferenceCandidate]
    func resolveReference(_ input: String) async throws -> ResolvedReference
}

public protocol TopicProvider: Sendable {
    var providerID: String { get }
    func suggestTopics(query: String, limit: Int) async throws -> [TopicCandidate]
    func resolveTopic(id: String) async throws -> ResolvedTopic
    func refreshTopicIndexIfNeeded() async throws
}

public protocol LexicalProvider: Sendable {
    var providerID: String { get }
    func suggestWords(prefix: String, context: TorahLexicalContext?) async throws -> [WordCandidate]
    func resolveWord(surface: String, context: TorahLexicalContext?) async throws -> [ResolvedWord]
}
