import Foundation

@MainActor
public final class TorahInspectorRepository {
    public typealias TextFetcher = @Sendable (String, String?) async throws -> TorahTextDocument
    public typealias LinksFetcher = @Sendable (String, String?) async throws -> [TorahLinkedSource]
    public typealias TopicsFetcher = @Sendable (String, String?) async throws -> [TorahLinkedTopic]
    public typealias NotesFetcher = @Sendable (TorahInspectorSelection) async throws -> [TorahInspectorNote]
    public typealias SnippetsFetcher = @Sendable ([TorahLinkedSource]) async throws -> [TorahLinkedSource.ID: String]
    public typealias RelatedDocumentsFetcher = @Sendable (TorahInspectorSelection) async throws -> TorahRelatedDocumentsSnapshot

    private let textFetcher: TextFetcher
    private let linksFetcher: LinksFetcher
    private let topicsFetcher: TopicsFetcher
    private let notesFetcher: NotesFetcher
    private let snippetsFetcher: SnippetsFetcher
    private let relatedDocumentsFetcher: RelatedDocumentsFetcher
    public let documentCapacity: Int
    public let relationshipCapacity: Int
    public let snippetCapacity: Int

    private var documentCache: [String: TorahTextDocument] = [:]
    private var documentLRU: [String] = []
    private var canonicalAliases: [String: Set<String>] = [:]
    private var inFlightDocuments: [String: Task<TorahTextDocument, Error>] = [:]
    private var linksCache: [String: [TorahLinkedSource]] = [:]
    private var linksLRU: [String] = []
    private var inFlightLinks: [String: Task<[TorahLinkedSource], Error>] = [:]
    private var topicsCache: [String: [TorahLinkedTopic]] = [:]
    private var topicsLRU: [String] = []
    private var inFlightTopics: [String: Task<[TorahLinkedTopic], Error>] = [:]
    private var notesCache: [String: [TorahInspectorNote]] = [:]
    private var inFlightNotes: [String: Task<[TorahInspectorNote], Error>] = [:]
    private var snippetsCache: [TorahLinkedSource.ID: String] = [:]
    private var snippetsLRU: [TorahLinkedSource.ID] = []
    private var relatedDocumentsCache: [String: TorahRelatedDocumentsSnapshot] = [:]
    private var relatedDocumentsOwnerIsActive = true
    private var relatedDocumentsGeneration: [String: UUID] = [:]
    private var inFlightRelatedDocuments: [String: (id: UUID, task: Task<TorahRelatedDocumentsSnapshot, Error>)] = [:]

    public init(
        documentCapacity: Int = 30,
        relationshipCapacity: Int = 50,
        snippetCapacity: Int = 200,
        textFetcher: @escaping TextFetcher,
        linksFetcher: @escaping LinksFetcher = { _, _ in [] },
        topicsFetcher: @escaping TopicsFetcher = { _, _ in [] },
        notesFetcher: @escaping NotesFetcher = { _ in [] },
        snippetsFetcher: @escaping SnippetsFetcher = { _ in [:] },
        relatedDocumentsFetcher: @escaping RelatedDocumentsFetcher = { _ in .unavailable }
    ) {
        self.textFetcher = textFetcher
        self.linksFetcher = linksFetcher
        self.topicsFetcher = topicsFetcher
        self.notesFetcher = notesFetcher
        self.snippetsFetcher = snippetsFetcher
        self.relatedDocumentsFetcher = relatedDocumentsFetcher
        self.documentCapacity = max(0, documentCapacity)
        self.relationshipCapacity = max(0, relationshipCapacity)
        self.snippetCapacity = max(0, snippetCapacity)
    }

    public convenience init(
        provider: any TorahInspectorProvider,
        documentCapacity: Int = 30,
        relationshipCapacity: Int = 50
    ) {
        let providerID = provider.providerID
        self.init(
            documentCapacity: documentCapacity,
            relationshipCapacity: relationshipCapacity,
            textFetcher: { reference, requestedProviderID in
                guard requestedProviderID == nil || requestedProviderID == providerID else {
                    throw TorahError.missingProvider
                }
                return try await provider.fetchText(reference: reference, request: TorahTextRequest())
            },
            linksFetcher: { reference, requestedProviderID in
                guard requestedProviderID == nil || requestedProviderID == providerID else {
                    throw TorahError.missingProvider
                }
                return try await provider.links(for: reference)
            },
            topicsFetcher: { reference, requestedProviderID in
                guard requestedProviderID == nil || requestedProviderID == providerID else {
                    throw TorahError.missingProvider
                }
                return try await provider.topics(for: reference)
            },
            notesFetcher: { _ in [] }
        )
    }

    private func normalizedKey(providerID: String?, reference: String) -> String {
        "\(providerID ?? ""):\(reference)"
    }

    public func cachedDocument(for reference: String, providerID: String? = nil) -> TorahTextDocument? {
        let key = normalizedKey(providerID: providerID, reference: reference)
        guard let document = documentCache[key] else { return nil }
        touchDocument(canonicalKey: normalizedKey(providerID: document.providerID, reference: document.canonicalRef))
        return document
    }

    public func document(for reference: String, providerID: String? = nil) async throws -> TorahTextDocument {
        try Task.checkCancellation()
        if let cached = cachedDocument(for: reference, providerID: providerID) { return cached }
        let key = normalizedKey(providerID: providerID, reference: reference)
        if let inFlight = inFlightDocuments[key] {
            let document = try await inFlight.value
            try Task.checkCancellation()
            return document
        }

        let fetcher = textFetcher
        let task = Task<TorahTextDocument, Error> { try await fetcher(reference, providerID) }
        inFlightDocuments[key] = task
        do {
            let document = try await task.value
            inFlightDocuments.removeValue(forKey: key)
            storeDocument(document, requestedRef: reference, providerID: providerID)
            // A shared fetch may still serve another reader after this consumer leaves.
            try Task.checkCancellation()
            return document
        } catch {
            inFlightDocuments.removeValue(forKey: key)
            throw error
        }
    }

    private func storeDocument(_ document: TorahTextDocument, requestedRef: String, providerID: String?) {
        let effectiveProviderID = providerID ?? document.providerID
        let canonicalKey = normalizedKey(providerID: effectiveProviderID, reference: document.canonicalRef)
        var aliases: Set<String> = [
            canonicalKey,
            normalizedKey(providerID: effectiveProviderID, reference: requestedRef),
            normalizedKey(providerID: effectiveProviderID, reference: document.sectionRef),
            normalizedKey(providerID: effectiveProviderID, reference: document.requestedRef)
        ]
        if let existing = canonicalAliases[canonicalKey] { aliases.formUnion(existing) }
        canonicalAliases[canonicalKey] = aliases
        for alias in aliases { documentCache[alias] = document }
        touchDocument(canonicalKey: canonicalKey)
        while documentLRU.count > documentCapacity {
            let oldest = documentLRU.removeFirst()
            for alias in canonicalAliases.removeValue(forKey: oldest) ?? [] {
                documentCache.removeValue(forKey: alias)
            }
        }
    }

    private func touchDocument(canonicalKey: String) {
        documentLRU.removeAll { $0 == canonicalKey }
        documentLRU.append(canonicalKey)
    }

    public func cachedLinks(for reference: String, providerID: String? = nil) -> [TorahLinkedSource]? {
        linksCache[normalizedKey(providerID: providerID, reference: reference)]
    }

    public func links(for reference: String, providerID: String? = nil) async throws -> [TorahLinkedSource] {
        let key = normalizedKey(providerID: providerID, reference: reference)
        if let cached = linksCache[key] { Self.touchRelationship(key, lru: &linksLRU); return cached }
        if let inFlight = inFlightLinks[key] { return try await inFlight.value }
        let fetcher = linksFetcher
        let task = Task<[TorahLinkedSource], Error> { try await fetcher(reference, providerID) }
        inFlightLinks[key] = task
        do {
            let values = try await task.value
            inFlightLinks.removeValue(forKey: key)
            linksCache[key] = values
            Self.touchRelationship(key, lru: &linksLRU)
            Self.evictRelationships(cache: &linksCache, lru: &linksLRU, capacity: relationshipCapacity)
            return values
        } catch {
            inFlightLinks.removeValue(forKey: key)
            throw error
        }
    }

    public func cachedTopics(for reference: String, providerID: String? = nil) -> [TorahLinkedTopic]? {
        topicsCache[normalizedKey(providerID: providerID, reference: reference)]
    }

    public func topics(for reference: String, providerID: String? = nil) async throws -> [TorahLinkedTopic] {
        let key = normalizedKey(providerID: providerID, reference: reference)
        if let cached = topicsCache[key] { Self.touchRelationship(key, lru: &topicsLRU); return cached }
        if let inFlight = inFlightTopics[key] { return try await inFlight.value }
        let fetcher = topicsFetcher
        let task = Task<[TorahLinkedTopic], Error> { try await fetcher(reference, providerID) }
        inFlightTopics[key] = task
        do {
            let values = try await task.value
            inFlightTopics.removeValue(forKey: key)
            topicsCache[key] = values
            Self.touchRelationship(key, lru: &topicsLRU)
            Self.evictRelationships(cache: &topicsCache, lru: &topicsLRU, capacity: relationshipCapacity)
            return values
        } catch {
            inFlightTopics.removeValue(forKey: key)
            throw error
        }
    }

    public func cachedNotes(for selection: TorahInspectorSelection) -> [TorahInspectorNote]? {
        notesCache[selection.id]
    }

    public func notes(for selection: TorahInspectorSelection) async throws -> [TorahInspectorNote] {
        let key = selection.id
        if let cached = notesCache[key] { return cached }
        if let inFlight = inFlightNotes[key] { return try await inFlight.value }
        let fetcher = notesFetcher
        let task = Task<[TorahInspectorNote], Error> { try await fetcher(selection) }
        inFlightNotes[key] = task
        do {
            let values = try await task.value
            inFlightNotes.removeValue(forKey: key)
            notesCache[key] = values
            return values
        } catch {
            inFlightNotes.removeValue(forKey: key)
            throw error
        }
    }

    public func invalidateNotes(for selection: TorahInspectorSelection? = nil) {
        notesCache.removeAll()
        for task in inFlightNotes.values { task.cancel() }
        inFlightNotes.removeAll()
        NotificationCenter.default.post(
            name: .torahInspectorNotesDidChange,
            object: self
        )
    }

    public func invalidateAllNotes() {
        invalidateNotes()
    }

    public func cachedSnippet(for sourceID: TorahLinkedSource.ID) -> String? {
        snippetsCache[sourceID]
    }

    public func fetchSnippets(for sources: [TorahLinkedSource]) async throws -> [TorahLinkedSource.ID: String] {
        var needed: [TorahLinkedSource] = []
        var results: [TorahLinkedSource.ID: String] = [:]
        for source in sources {
            if let cached = snippetsCache[source.id] {
                Self.touchRelationship(source.id, lru: &snippetsLRU)
                results[source.id] = cached
            } else if let inline = source.hebrewText ?? source.englishText, !inline.isEmpty {
                snippetsCache[source.id] = inline
                Self.touchRelationship(source.id, lru: &snippetsLRU)
                results[source.id] = inline
            } else {
                needed.append(source)
            }
        }
        guard !needed.isEmpty else { return results }

        let fetched = try await snippetsFetcher(needed)
        for (id, text) in fetched {
            snippetsCache[id] = text
            Self.touchRelationship(id, lru: &snippetsLRU)
            results[id] = text
        }
        Self.evictRelationships(cache: &snippetsCache, lru: &snippetsLRU, capacity: snippetCapacity)
        return results
    }

    public func invalidateSnippets() {
        snippetsCache.removeAll()
        snippetsLRU.removeAll()
    }

    public func relatedDocuments(
        for selection: TorahInspectorSelection,
        forceRefresh: Bool = false
    ) async throws -> TorahRelatedDocumentsSnapshot {
        try Task.checkCancellation()
        guard relatedDocumentsOwnerIsActive else {
            throw TorahRelatedDocumentsAccessError.invalidated
        }
        let key = selection.id
        if forceRefresh { invalidateRelatedDocuments(for: selection) }
        if let cached = relatedDocumentsCache[key] { return cached }
        let flight: (id: UUID, task: Task<TorahRelatedDocumentsSnapshot, Error>)
        if let existing = inFlightRelatedDocuments[key] {
            flight = existing
        } else {
            let fetcher = relatedDocumentsFetcher
            flight = (UUID(), Task { try await fetcher(selection) })
            inFlightRelatedDocuments[key] = flight
            relatedDocumentsGeneration[key] = flight.id
        }
        do {
            let snapshot = try await flight.task.value
            guard relatedDocumentsOwnerIsActive else {
                throw TorahRelatedDocumentsAccessError.invalidated
            }
            guard relatedDocumentsGeneration[key] == flight.id else { throw CancellationError() }
            if inFlightRelatedDocuments[key]?.id == flight.id {
                inFlightRelatedDocuments.removeValue(forKey: key)
                relatedDocumentsCache[key] = snapshot
            }
            try Task.checkCancellation()
            return snapshot
        } catch {
            // A retired owner never returns its former cache. An old request
            // must not revoke a newer owner or a replacement request either.
            guard relatedDocumentsOwnerIsActive else {
                throw TorahRelatedDocumentsAccessError.invalidated
            }
            guard relatedDocumentsGeneration[key] == flight.id else {
                throw CancellationError()
            }
            if inFlightRelatedDocuments[key]?.id == flight.id {
                inFlightRelatedDocuments.removeValue(forKey: key)
            }
            if let accessFailure = error as? TorahRelatedDocumentsAccessError {
                discardRelatedDocuments(after: accessFailure)
            }
            throw error
        }
    }

    /// Synchronous lifetime barrier for this repository's account/Space owner.
    /// This is not a native ACL decision; the host must retire before changing
    /// or releasing that owner. Already-running work cannot republish afterward.
    public func retireRelatedDocuments() {
        guard relatedDocumentsOwnerIsActive else { return }
        relatedDocumentsOwnerIsActive = false
        discardRelatedDocuments(after: .invalidated)
    }

    /// Reactivating the same host starts without cached authority. Each result
    /// still has to pass the engine's current read and session fences.
    public func resumeRelatedDocuments() {
        guard !relatedDocumentsOwnerIsActive else { return }
        invalidateRelatedDocuments()
        relatedDocumentsOwnerIsActive = true
    }

    private func discardRelatedDocuments(after failure: TorahRelatedDocumentsAccessError) {
        invalidateRelatedDocuments()
        // Other selections mounted from this exact repository must drop their
        // previous rows even if they do not currently have a refresh in flight.
        NotificationCenter.default.post(
            name: .torahInspectorRelatedDocumentsAccessDidChange,
            object: self,
            userInfo: ["reason": failure.rawValue]
        )
    }

    public func invalidateRelatedDocuments(for selection: TorahInspectorSelection? = nil) {
        if let selection {
            relatedDocumentsCache.removeValue(forKey: selection.id)
            relatedDocumentsGeneration.removeValue(forKey: selection.id)
            inFlightRelatedDocuments.removeValue(forKey: selection.id)?.task.cancel()
        } else {
            relatedDocumentsCache.removeAll()
            relatedDocumentsGeneration.removeAll()
            for flight in inFlightRelatedDocuments.values { flight.task.cancel() }
            inFlightRelatedDocuments.removeAll()
        }
    }

    private static func touchRelationship(_ key: String, lru: inout [String]) {
        lru.removeAll { $0 == key }
        lru.append(key)
    }

    private static func evictRelationships<Value>(cache: inout [String: Value], lru: inout [String], capacity: Int) {
        while lru.count > capacity {
            cache.removeValue(forKey: lru.removeFirst())
        }
    }
}

extension Notification.Name {
    public static let torahInspectorNotesDidChange = Notification.Name("TorahInspectorNotesDidChangeNotification")
    public static let torahInspectorRelatedDocumentsAccessDidChange = Notification.Name("TorahInspectorRelatedDocumentsAccessDidChangeNotification")
}
