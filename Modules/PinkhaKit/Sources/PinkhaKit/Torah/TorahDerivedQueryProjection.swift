import Foundation

/// Read-only query identities for an engine feasibility probe. No native Property
/// registration or application rollout is implied by this value.
public struct TorahDerivedQueryProjection: Sendable, Equatable {
    public let sources: [String]
    public let topics: [String]
    public let words: [String]

    public init(records: [TorahStoredAssociationRecord], spaceId: String, objectId: String) {
        let projection = TorahDocumentPropertyProjection(records: records, spaceId: spaceId, objectId: objectId)
        sources = projection.sources.map(Self.identity).sorted()
        topics = projection.topics.map(Self.identity).sorted()
        words = projection.words.map(Self.identity).sorted()
    }

    public static func identity(_ item: TorahAssociationItem) -> String {
        let source = item.canonicalKey.isEmpty ? item.externalID : item.canonicalKey
        let parts = [item.kind.rawValue, item.providerID, source].map { value in
            let normalized = value.precomposedStringWithCanonicalMapping
            return "\(normalized.utf8.count):\(normalized)"
        }
        return "torah1|" + parts.joined(separator: "|")
    }
}
