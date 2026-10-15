import Foundation

/// Exact logical location. Space is part of the key even when object IDs happen to match.
public struct TorahAssociationLocation: Sendable, Equatable, Hashable {
    public let spaceId: String
    public let target: TorahAssociationTarget

    public init(spaceId: String, target: TorahAssociationTarget) {
        self.spaceId = spaceId
        self.target = target
    }
}

/// Deterministic semantic identity used for idempotency and local merge policy.
public struct TorahAssociationIdentity: Sendable, Equatable, Hashable {
    public let spaceId: String
    public let objectId: String
    public let blockId: String?
    public let kind: TorahAssociationKind
    public let role: TorahAssociationRole
    public let providerID: String
    public let sourceIdentity: String
    public let instanceIdentity: String?

    public init(item: TorahAssociationItem, location: TorahAssociationLocation) {
        spaceId = Self.exact(location.spaceId)
        objectId = Self.exact(location.target.objectId)
        blockId = location.target.blockId.map(Self.exact)
        kind = item.kind
        role = item.role
        providerID = Self.exact(item.providerID)
        sourceIdentity = Self.exact(item.canonicalKey.isEmpty ? item.externalID : item.canonicalKey)
        // Context links deduplicate semantically. Quotes are separate captured excerpts unless
        // a retry carries the same stable association ID.
        instanceIdentity = item.role == .sourceQuote ? Self.exact(item.id) : nil
    }

    public var storageKey: String {
        [
            spaceId, objectId, blockId ?? "", kind.rawValue, role.rawValue,
            providerID, sourceIdentity, instanceIdentity ?? ""
        ].map(Self.lengthPrefixed).joined(separator: "|")
    }

    private static func exact(_ value: String) -> String {
        value.precomposedStringWithCanonicalMapping
    }

    private static func lengthPrefixed(_ value: String) -> String {
        "\(value.utf8.count):\(value)"
    }
}

/// Pure collection semantics for deterministic tests and adapters backed by a proven atomic store.
public enum TorahAssociationCollectionPolicy {
    public static func adding(
        _ incoming: TorahAssociationItem,
        to items: [TorahAssociationItem],
        location: TorahAssociationLocation
    ) -> [TorahAssociationItem] {
        upserting(incoming, into: items, location: location)
    }

    public static func upserting(
        _ incoming: TorahAssociationItem,
        into items: [TorahAssociationItem],
        location: TorahAssociationLocation
    ) -> [TorahAssociationItem] {
        let incomingIdentity = TorahAssociationIdentity(item: incoming, location: location)
        var result = items
        if let index = result.firstIndex(where: {
            $0.id == incoming.id || TorahAssociationIdentity(item: $0, location: location) == incomingIdentity
        }) {
            result[index] = merging(existing: result[index], incoming: incoming)
        } else {
            result.append(incoming)
        }
        return sorted(result)
    }

    public static func updating(
        _ incoming: TorahAssociationItem,
        in items: [TorahAssociationItem]
    ) throws -> [TorahAssociationItem] {
        guard let index = items.firstIndex(where: { $0.id == incoming.id }) else {
            throw TorahAssociationRepositoryError.associationNotFound(incoming.id)
        }
        var result = items
        result[index] = merging(existing: result[index], incoming: incoming)
        return sorted(result)
    }

    public static func removing(id: String, from items: [TorahAssociationItem]) -> [TorahAssociationItem] {
        sorted(items.filter { $0.id != id })
    }

    public static func sorted(_ items: [TorahAssociationItem]) -> [TorahAssociationItem] {
        items.sorted { lhs, rhs in
            switch (lhs.createdAt, rhs.createdAt) {
            case let (left?, right?) where left != right: return left < right
            case (_?, nil): return true
            case (nil, _?): return false
            default: return lhs.id < rhs.id
            }
        }
    }

    private static func merging(
        existing: TorahAssociationItem,
        incoming: TorahAssociationItem
    ) -> TorahAssociationItem {
        var merged = incoming
        merged.id = existing.id
        merged.createdAt = incoming.createdAt ?? existing.createdAt
        merged.rawInput = incoming.rawInput ?? existing.rawInput
        merged.providerPayload = incoming.providerPayload ?? existing.providerPayload
        merged.customMetadata = (existing.customMetadata ?? [:]).merging(incoming.customMetadata ?? [:]) { _, new in new }
        if merged.customMetadata?.isEmpty == true { merged.customMetadata = nil }
        merged.unknownFields = existing.unknownFields.merging(incoming.unknownFields) { _, new in new }
        return merged
    }
}
