import Foundation

/// A provider-owned reference suggestion. `id` is the value sent back to the
/// provider for resolution; `label` is display-only.
public struct ReferenceCandidate: Identifiable, Hashable, Sendable {
    public let id: String
    public let label: String

    public init(id: String, label: String) {
        self.id = id
        self.label = label
    }
}

/// A reference resolved by its source provider, including the provider's raw
/// response so future host layers do not need to reconstruct provenance.
public struct ResolvedReference: Hashable, Sendable {
    public let canonical: String
    public let labelHe: String
    public let labelEn: String?
    public let payload: String
    public let urlRef: String?
    public let nodeType: String?
    public let depth: Int?
    public let startIndexes: [Int]
    public let endIndexes: [Int]
    public let firstAvailableSectionRef: String?

    public init(
        canonical: String,
        labelHe: String,
        labelEn: String? = nil,
        payload: String = "{}",
        urlRef: String? = nil,
        nodeType: String? = nil,
        depth: Int? = nil,
        startIndexes: [Int] = [],
        endIndexes: [Int] = [],
        firstAvailableSectionRef: String? = nil
    ) {
        self.canonical = canonical
        self.labelHe = labelHe
        self.labelEn = labelEn
        self.payload = payload
        self.urlRef = urlRef
        self.nodeType = nodeType
        self.depth = depth
        self.startIndexes = startIndexes
        self.endIndexes = endIndexes
        self.firstAvailableSectionRef = firstAvailableSectionRef
    }

    /// Broad book/tractate references are browsable but must not masquerade as
    /// a precise source that can safely be embedded.
    public var isEmbeddableSource: Bool {
        guard nodeType == nil || nodeType == "JaggedArrayNode" else { return false }
        guard let depth else { return true }
        return !startIndexes.isEmpty && startIndexes.count >= max(1, depth - 1)
    }
}

public struct TopicCandidate: Identifiable, Hashable, Sendable {
    public let id: String
    /// The title returned for this autocomplete result in the response
    /// language. It is not duplicated into an unverified locale.
    public let displayTitle: String
    public let labelHe: String?
    public let labelEn: String?

    public init(
        id: String,
        displayTitle: String? = nil,
        labelHe: String? = nil,
        labelEn: String? = nil
    ) {
        self.id = id
        self.displayTitle = displayTitle ?? labelHe ?? labelEn ?? id
        self.labelHe = labelHe
        self.labelEn = labelEn
    }
}

public struct ResolvedTopic: Hashable, Sendable {
    public let slug: String
    public let displayTitle: String
    public let labelHe: String?
    public let labelEn: String?
    public let payload: String

    public init(
        slug: String,
        displayTitle: String? = nil,
        labelHe: String? = nil,
        labelEn: String? = nil,
        payload: String = "{}"
    ) {
        self.slug = slug
        self.displayTitle = displayTitle ?? labelHe ?? labelEn ?? slug
        self.labelHe = labelHe
        self.labelEn = labelEn
        self.payload = payload
    }
}

public struct WordCandidate: Identifiable, Hashable, Sendable {
    public let id: String
    public let surface: String
    public let headword: String
    public let lexicon: String
    public let description: String?
    public let payload: String

    public init(
        id: String,
        surface: String,
        headword: String,
        lexicon: String,
        description: String? = nil,
        payload: String = "{}"
    ) {
        self.id = id
        self.surface = surface
        self.headword = headword
        self.lexicon = lexicon
        self.description = description
        self.payload = payload
    }
}

public struct ResolvedWord: Hashable, Sendable {
    public let candidate: WordCandidate

    public init(candidate: WordCandidate) {
        self.candidate = candidate
    }
}

public struct TorahLexicalContext: Hashable, Sendable {
    public let canonicalReference: String?

    public init(canonicalReference: String? = nil) {
        self.canonicalReference = canonicalReference
    }
}
