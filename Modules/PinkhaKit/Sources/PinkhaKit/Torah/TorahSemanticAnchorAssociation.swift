import Foundation

/// A versioned semantic target stored in the association's existing native
/// payload. Its stable identity lives in native text markup; the enclosing
/// object is only the payload's storage address. No selected range or historical
/// block ID is persisted as a locator. The association item retains its own ID.
public struct TorahSemanticAnchorAssociation: Sendable, Equatable, Hashable {
    public static let metadataKey = "pinkha.semanticTextAnchor"
    public let anchor: PinkhaSemanticTextAnchor

    private struct Payload: Codable {
        let version: Int
        let marker: String
    }

    public init(anchor: PinkhaSemanticTextAnchor) {
        self.anchor = anchor
    }

    public static func hasReservedMetadata(_ item: TorahAssociationItem) -> Bool {
        item.customMetadata?[metadataKey] != nil
    }

    /// Absence is a legacy object/block association. Invalid, future, foreign,
    /// or block-owned metadata is an explicit error, never a document fallback.
    public static func decoding(_ item: TorahAssociationItem,
                                location: TorahAssociationLocation) throws -> Self? {
        guard let raw = item.customMetadata?[metadataKey] else { return nil }
        guard raw.utf8.count <= 4_096 else { throw PinkhaSemanticTextAnchorError.limitExceeded }
        let payload = try JSONDecoder().decode(Payload.self, from: Data(raw.utf8))
        guard payload.version == PinkhaSemanticTextAnchor.currentVersion else {
            throw PinkhaSemanticTextAnchorError.unsupportedVersion
        }
        guard let url = URL(string: payload.marker) else { throw PinkhaSemanticTextAnchorError.invalidMarker }
        let anchor = try PinkhaSemanticTextAnchor(markerURL: url)
        guard location.target.blockId == nil,
              anchor.belongsTo(spaceID: location.spaceId, objectID: location.target.objectId) else {
            throw PinkhaSemanticTextAnchorError.wrongDocument
        }
        return Self(anchor: anchor)
    }

    public func attaching(to item: TorahAssociationItem,
                          location: TorahAssociationLocation) throws -> TorahAssociationItem {
        guard location.target.blockId == nil,
              anchor.belongsTo(spaceID: location.spaceId, objectID: location.target.objectId) else {
            throw PinkhaSemanticTextAnchorError.wrongDocument
        }
        if let previous = try Self.decoding(item, location: location), previous != self {
            throw PinkhaSemanticTextAnchorError.selectionAlreadyLinked
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let data = try encoder.encode(Payload(version: PinkhaSemanticTextAnchor.currentVersion,
                                             marker: anchor.markerString))
        guard let encoded = String(data: data, encoding: .utf8) else {
            throw PinkhaSemanticTextAnchorError.invalidMarker
        }
        var result = item
        var metadata = result.customMetadata ?? [:]
        metadata[Self.metadataKey] = encoded
        result.customMetadata = metadata
        return result
    }

    /// Shared collection identity keeps separate phrases distinct even if they
    /// cite the same source. Unknown metadata cannot deduplicate with a legacy
    /// whole-object link. Unchanged legacy items keep exactly their prior key.
    static func identity(_ item: TorahAssociationItem, location: TorahAssociationLocation) -> String? {
        guard let raw = item.customMetadata?[metadataKey] else { return nil }
        if let decoded = try? decoding(item, location: location) { return decoded.anchor.markerString }
        return "unresolved-semantic-target:" + Data(raw.utf8).base64EncodedString()
    }
}
