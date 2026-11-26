import Foundation

/// A read-only, complete source plan for an explicit legacy cutover. Constructing
/// it never migrates data or supplies native authority. The Heart adapter must
/// compare these bytes to a property read under the actual native target lease.
public struct TorahLegacyAssociationCutoverPlan: Sendable, Equatable {
    public struct Fact: Sendable, Equatable {
        public let blockID: String
        public let providerID: String
        public let canonicalRef: String
        public let payload: Data

        fileprivate init(blockID: String, providerID: String, canonicalRef: String, payload: Data) {
            self.blockID = blockID
            self.providerID = providerID
            self.canonicalRef = canonicalRef
            self.payload = payload
        }

        public func canonicalBytes(spaceID: String, objectID: String) throws -> Data {
            guard TorahLegacyAssociationCutoverPlan.valid(spaceID, required: true, limit: 1_024),
                  TorahLegacyAssociationCutoverPlan.valid(objectID, required: true, limit: 1_024),
                  TorahLegacyAssociationCutoverPlan.valid(blockID, required: false, limit: 1_024),
                  TorahLegacyAssociationCutoverPlan.valid(providerID, required: true, limit: 256),
                  TorahLegacyAssociationCutoverPlan.valid(canonicalRef, required: true, limit: 4_096),
                  !payload.isEmpty, payload.count <= 65_536 else { throw TorahLegacyAssociationCutoverPlan.malformed }
            var result = Data("pinkha-torah-cutover-fact-v1\0".utf8)
            for text in [spaceID, objectID, blockID, providerID, canonicalRef] {
                TorahLegacyAssociationCutoverPlan.append(Data(text.utf8), to: &result)
            }
            TorahLegacyAssociationCutoverPlan.append(payload, to: &result)
            return result
        }
    }

    public static let version: UInt32 = 1
    public let spaceID: String
    public let objectID: String
    public let propertyKey: String
    public let valuePresent: Bool
    public let legacyValue: Data
    public let facts: [Fact]
    /// Retained also for an empty source: adding its first later association
    /// must not silently erase unknown canonical envelope metadata.
    public let envelopeUnknown: [String: TorahJSONValue]

    public init(spaceID: String, objectID: String, propertyKey: String, propertyValue: Data?) throws {
        guard Self.valid(spaceID, required: true, limit: 1_024),
              Self.valid(objectID, required: true, limit: 1_024),
              Self.valid(propertyKey, required: true, limit: 1_024),
              (propertyValue?.count ?? 0) <= 1_048_576 else { throw Self.malformed }
        let raw = propertyValue ?? Data()
        guard String(data: raw, encoding: .utf8) != nil else { throw Self.malformed }
        let codec = TorahAssociationPayloadCodec()
        let location = TorahAssociationLocation(spaceId: spaceID, target: .object(objectId: objectID))
        let decoded: TorahCanonicalAssociationsPayload
        if raw.isEmpty {
            decoded = .init(records: [])
        } else {
            decoded = try codec.decodeCanonicalDocument(raw, legacyLocation: location)
            try TorahSourceJSONGuard.validateCanonicalPayload(raw, decoded: decoded)
        }
        guard decoded.records.count <= 1_024 else { throw Self.malformed }
        let canonicalWhole = try codec.encodeCanonicalDocument(decoded)
        guard try codec.decodeCanonicalDocument(canonicalWhole, legacyLocation: location) == decoded else {
            throw Self.malformed
        }
        var identities = Set<Data>()
        var prepared: [(fact: Fact, frame: Data)] = []
        for record in decoded.records {
            guard TorahAuthorizedOperationReadContract.exact(record.spaceId, spaceID),
                  TorahAuthorizedOperationReadContract.exact(record.objectId, objectID),
                  record.blockId.map({ Self.valid($0, required: true, limit: 1_024) }) ?? true,
                  !record.item.id.isEmpty else { throw Self.malformed }
            var identity = Data()
            Self.append(Data((record.blockId ?? "").utf8), to: &identity)
            Self.append(Data(record.item.id.utf8), to: &identity)
            guard identities.insert(identity).inserted else { throw Self.malformed }
            // Invalid reserved metadata is never reclassified as an object link.
            _ = try TorahSemanticAnchorAssociation.decoding(record.item, location: record.location)
            let payload = try codec.encodeCanonicalDocument(.init(records: [record],
                                                                 unknownFields: decoded.unknownFields))
            let canonicalRef = record.item.canonicalKey.isEmpty ? record.item.externalID : record.item.canonicalKey
            let checked = try TorahImmutableAssociationContent(payload: payload, location: record.location,
                                                               providerID: record.item.providerID,
                                                               canonicalRef: canonicalRef)
            guard checked.record == record, checked.envelopeUnknown == decoded.unknownFields,
                  checked.canonicalPayload == payload else { throw Self.malformed }
            let fact = Fact(blockID: record.blockId ?? "", providerID: record.item.providerID,
                            canonicalRef: canonicalRef, payload: payload)
            prepared.append((fact, try fact.canonicalBytes(spaceID: spaceID, objectID: objectID)))
        }
        prepared.sort { $0.frame.lexicographicallyPrecedes($1.frame) }
        guard prepared.reduce(0, { $0 + $1.frame.count }) <= 4_194_304 else { throw Self.malformed }
        self.spaceID = spaceID
        self.objectID = objectID
        self.propertyKey = propertyKey
        valuePresent = propertyValue != nil
        legacyValue = raw
        facts = prepared.map(\.fact)
        envelopeUnknown = decoded.unknownFields
        _ = try canonicalBytes()
    }

    /// The domain emits framing only; the engine's standard SHA-256 provider
    /// computes the ID. No private hash implementation or native call is used.
    public func canonicalBytes() throws -> Data {
        var result = Data("pinkha-torah-legacy-cutover-v1\0".utf8)
        Self.appendUInt32(Self.version, to: &result)
        for text in [spaceID, objectID, propertyKey] { Self.append(Data(text.utf8), to: &result) }
        result.append(valuePresent ? 1 : 0)
        Self.append(legacyValue, to: &result)
        Self.appendUInt32(UInt32(facts.count), to: &result)
        for fact in facts {
            Self.append(try fact.canonicalBytes(spaceID: spaceID, objectID: objectID), to: &result)
        }
        guard result.count <= 4_194_304 else { throw Self.malformed }
        return result
    }

    /// Explicit typed wire for the native plan contract, not a persisted source
    /// replacement. The full original property's presence and bytes are kept.
    public func wireData() throws -> Data {
        struct WireFact: Encodable {
            let blockId: String
            let providerId: String
            let canonicalRef: String
            let payload: Data
        }
        struct Wire: Encodable {
            let version: UInt32
            let spaceId: String
            let objectId: String
            let propertyKey: String
            let valuePresent: Bool
            let legacyValue: Data
            let facts: [WireFact]
        }
        let wire = Wire(version: Self.version, spaceId: spaceID, objectId: objectID,
                        propertyKey: propertyKey, valuePresent: valuePresent, legacyValue: legacyValue,
                        facts: facts.map { .init(blockId: $0.blockID, providerId: $0.providerID,
                                                 canonicalRef: $0.canonicalRef, payload: $0.payload) })
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(wire)
    }

    private static var malformed: TorahAssociationRepositoryError { .malformedCanonicalData }
    private static func valid(_ value: String, required: Bool, limit: Int) -> Bool {
        (!required || !value.isEmpty) && value.utf8.count <= limit && !value.contains("\0")
    }
    private static func append(_ data: Data, to result: inout Data) {
        appendUInt32(UInt32(data.count), to: &result)
        result.append(data)
    }
    private static func appendUInt32(_ value: UInt32, to result: inout Data) {
        result.append(UInt8(truncatingIfNeeded: value >> 24))
        result.append(UInt8(truncatingIfNeeded: value >> 16))
        result.append(UInt8(truncatingIfNeeded: value >> 8))
        result.append(UInt8(truncatingIfNeeded: value))
    }
}
