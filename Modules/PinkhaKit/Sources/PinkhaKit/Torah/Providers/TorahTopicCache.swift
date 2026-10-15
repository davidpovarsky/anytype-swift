import Foundation

public protocol TorahTopicCache: Sendable {
    func topics(now: Date) async -> [TopicCandidate]?
    func replace(topics: [TopicCandidate], expiresAt: Date) async
    func removeAll() async
}

/// Discardable external metadata cache. It never contains user associations.
public actor InMemoryTorahTopicCache: TorahTopicCache {
    private var cachedTopics: [TopicCandidate] = []
    private var expiresAt: Date?

    public init() {}

    public func topics(now: Date) -> [TopicCandidate]? {
        guard let expiresAt, expiresAt > now else {
            cachedTopics = []
            self.expiresAt = nil
            return nil
        }
        return cachedTopics
    }

    public func replace(topics: [TopicCandidate], expiresAt: Date) {
        cachedTopics = topics
        self.expiresAt = expiresAt
    }

    public func removeAll() {
        cachedTopics = []
        expiresAt = nil
    }
}
