import Foundation

public struct TorahDocumentPropertyProjection: Sendable, Equatable {
    public let sources: [TorahAssociationItem]
    public let topics: [TorahAssociationItem]
    public let words: [TorahAssociationItem]

    public init(records: [TorahStoredAssociationRecord], spaceId: String, objectId: String) {
        let location = TorahAssociationLocation(spaceId: spaceId, target: .object(objectId: objectId))
        var identities = Set<TorahAssociationIdentity>()
        var ids = Set<String>()
        let items = records.compactMap { record -> TorahAssociationItem? in
            let item = record.item
            guard record.location == location,
                  item.role == .context,
                  !item.canonicalKey.hasPrefix("anytype-note:"),
                  !ids.contains(item.id),
                  !identities.contains(TorahAssociationIdentity(item: item, location: location)) else { return nil }
            ids.insert(item.id)
            identities.insert(TorahAssociationIdentity(item: item, location: location))
            return item
        }
        sources = items.filter { $0.kind == .ref }
        topics = items.filter { $0.kind == .topic }
        words = items.filter { $0.kind == .word }
    }

    public subscript(kind: TorahAssociationKind) -> [TorahAssociationItem] {
        switch kind {
        case .ref: sources
        case .topic: topics
        case .word: words
        }
    }
}

public enum TorahDocumentPropertyEligibility {
    public static func includes(typeId: String, spaceId: String, manifest: PinkhaSpaceManifest?) -> Bool {
        guard let manifest, manifest.spaceId == spaceId, manifest.isComplete, !typeId.isEmpty else { return false }
        return [PinkhaSchemaRoles.chiddushKey, PinkhaSchemaRoles.articleKey, PinkhaSchemaRoles.researchKey]
            .contains { manifest.registeredDocumentTypes[$0] == typeId }
    }

    public static func isCanonicalProperty(id: String, key: String, spaceId: String, manifest: PinkhaSpaceManifest?) -> Bool {
        guard let manifest, manifest.spaceId == spaceId else { return false }
        return (!manifest.documentAssociationsPropertyId.isEmpty && id == manifest.documentAssociationsPropertyId)
            || (!manifest.documentAssociationsPropertyKey.isEmpty && key == manifest.documentAssociationsPropertyKey)
    }
}
