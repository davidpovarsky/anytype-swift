import Foundation

/// One canonical association stored in the document-level v2 payload.
/// The complete Space/object/block location is explicit so block-scoped records
/// never need to be mirrored into replacement-style native block fields.
public struct TorahStoredAssociationRecord: Codable, Sendable, Equatable, Hashable {
    public var spaceId: String
    public var objectId: String
    public var blockId: String?
    public var item: TorahAssociationItem
    public var unknownFields: [String: TorahJSONValue]

    public init(
        location: TorahAssociationLocation,
        item: TorahAssociationItem,
        unknownFields: [String: TorahJSONValue] = [:]
    ) {
        self.spaceId = location.spaceId
        self.objectId = location.target.objectId
        self.blockId = location.target.blockId
        self.item = item
        self.unknownFields = unknownFields
    }

    public var location: TorahAssociationLocation {
        let target: TorahAssociationTarget = if let blockId {
            .block(objectId: objectId, blockId: blockId)
        } else {
            .object(objectId: objectId)
        }
        return TorahAssociationLocation(spaceId: spaceId, target: target)
    }

    private static let knownKeys: Set<String> = ["spaceId", "objectId", "blockId", "item"]

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: TorahDynamicCodingKey.self)
        spaceId = try container.decode(String.self, forKey: .key("spaceId"))
        objectId = try container.decode(String.self, forKey: .key("objectId"))
        blockId = try container.decodeIfPresent(String.self, forKey: .key("blockId"))
        item = try container.decode(TorahAssociationItem.self, forKey: .key("item"))
        unknownFields = try container.allKeys.reduce(into: [:]) { result, key in
            guard !Self.knownKeys.contains(key.stringValue) else { return }
            result[key.stringValue] = try container.decode(TorahJSONValue.self, forKey: key)
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: TorahDynamicCodingKey.self)
        try container.encode(spaceId, forKey: .key("spaceId"))
        try container.encode(objectId, forKey: .key("objectId"))
        try container.encodeIfPresent(blockId, forKey: .key("blockId"))
        try container.encode(item, forKey: .key("item"))
        for (key, value) in unknownFields where !Self.knownKeys.contains(key) {
            try container.encode(value, forKey: .key(key))
        }
    }
}

/// Canonical single-active-writer document payload. Version 1 remains a
/// read-only compatibility format through `TorahDocumentAssociationsPayload`.
public struct TorahCanonicalAssociationsPayload: Codable, Sendable, Equatable {
    public static let currentVersion = 2

    public var version: Int
    public var records: [TorahStoredAssociationRecord]
    public var unknownFields: [String: TorahJSONValue]

    public init(
        version: Int = currentVersion,
        records: [TorahStoredAssociationRecord],
        unknownFields: [String: TorahJSONValue] = [:]
    ) {
        self.version = version
        self.records = records
        self.unknownFields = unknownFields
    }

    private static let knownKeys: Set<String> = ["version", "records"]

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: TorahDynamicCodingKey.self)
        version = try container.decode(Int.self, forKey: .key("version"))
        records = try container.decode([TorahStoredAssociationRecord].self, forKey: .key("records"))
        unknownFields = try container.allKeys.reduce(into: [:]) { result, key in
            guard !Self.knownKeys.contains(key.stringValue) else { return }
            result[key.stringValue] = try container.decode(TorahJSONValue.self, forKey: key)
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: TorahDynamicCodingKey.self)
        try container.encode(version, forKey: .key("version"))
        try container.encode(records, forKey: .key("records"))
        for (key, value) in unknownFields where !Self.knownKeys.contains(key) {
            try container.encode(value, forKey: .key(key))
        }
    }
}

/// Pure target-aware collection policy for the canonical document payload.
public enum TorahCanonicalAssociationCollectionPolicy {
    public static func items(
        in payload: TorahCanonicalAssociationsPayload,
        at location: TorahAssociationLocation
    ) -> [TorahAssociationItem] {
        TorahAssociationCollectionPolicy.sorted(
            payload.records
                .filter { $0.location == location }
                .map(\.item)
        )
    }

    public static func adding(
        _ incoming: TorahAssociationItem,
        to payload: TorahCanonicalAssociationsPayload,
        at location: TorahAssociationLocation
    ) -> (payload: TorahCanonicalAssociationsPayload, item: TorahAssociationItem) {
        upserting(incoming, into: payload, at: location)
    }

    public static func upserting(
        _ incoming: TorahAssociationItem,
        into payload: TorahCanonicalAssociationsPayload,
        at location: TorahAssociationLocation
    ) -> (payload: TorahCanonicalAssociationsPayload, item: TorahAssociationItem) {
        let updatedItems = TorahAssociationCollectionPolicy.upserting(
            incoming,
            into: items(in: payload, at: location),
            location: location
        )
        let incomingIdentity = TorahAssociationIdentity(item: incoming, location: location)
        let stored = updatedItems.first {
            $0.id == incoming.id || TorahAssociationIdentity(item: $0, location: location) == incomingIdentity
        } ?? incoming
        return (replacingItems(updatedItems, in: payload, at: location), stored)
    }

    public static func updating(
        _ incoming: TorahAssociationItem,
        in payload: TorahCanonicalAssociationsPayload,
        at location: TorahAssociationLocation
    ) throws -> (payload: TorahCanonicalAssociationsPayload, item: TorahAssociationItem) {
        let updatedItems = try TorahAssociationCollectionPolicy.updating(
            incoming,
            in: items(in: payload, at: location)
        )
        let stored = updatedItems.first(where: { $0.id == incoming.id }) ?? incoming
        return (replacingItems(updatedItems, in: payload, at: location), stored)
    }

    public static func removing(
        id: String,
        from payload: TorahCanonicalAssociationsPayload,
        at location: TorahAssociationLocation
    ) -> TorahCanonicalAssociationsPayload {
        let updatedItems = TorahAssociationCollectionPolicy.removing(
            id: id,
            from: items(in: payload, at: location)
        )
        return replacingItems(updatedItems, in: payload, at: location)
    }

    private static func replacingItems(
        _ updatedItems: [TorahAssociationItem],
        in payload: TorahCanonicalAssociationsPayload,
        at location: TorahAssociationLocation
    ) -> TorahCanonicalAssociationsPayload {
        let existingForTarget = payload.records
            .filter { $0.location == location }
            .reduce(into: [String: TorahStoredAssociationRecord]()) { result, record in
                if result[record.item.id] == nil {
                    result[record.item.id] = record
                }
            }
        let untouched = payload.records.filter { $0.location != location }
        let replacements = updatedItems.map { item -> TorahStoredAssociationRecord in
            if var existing = existingForTarget[item.id] {
                existing.item = item
                return existing
            }
            return TorahStoredAssociationRecord(location: location, item: item)
        }
        var result = payload
        result.records = sorted(untouched + replacements)
        return result
    }

    private static func sorted(_ records: [TorahStoredAssociationRecord]) -> [TorahStoredAssociationRecord] {
        records.sorted { lhs, rhs in
            let left = [lhs.spaceId, lhs.objectId, lhs.blockId ?? "", lhs.item.id]
            let right = [rhs.spaceId, rhs.objectId, rhs.blockId ?? "", rhs.item.id]
            return left.lexicographicallyPrecedes(right)
        }
    }
}
