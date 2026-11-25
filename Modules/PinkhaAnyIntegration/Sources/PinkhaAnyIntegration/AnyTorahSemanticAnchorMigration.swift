import Foundation
import PinkhaKit
import PinkhaAnyEngine

/// Remaps only the versioned semantic target's owner through the shared strict
/// codec. Legacy associations and all unrelated metadata remain unchanged.
public enum AnyTorahSemanticAnchorMigration {
    public static func remapping(_ item: TorahAssociationItem, source: TorahAssociationLocation,
                                 destination: TorahAssociationLocation) throws -> TorahAssociationItem {
        guard let semantic = try TorahSemanticAnchorAssociation.decoding(item, location: source) else {
            return item
        }
        guard let raw = item.customMetadata?[TorahSemanticAnchorAssociation.metadataKey] else {
            throw PinkhaSemanticTextAnchorError.invalidMarker
        }
        let bytes = Data(raw.utf8)
        // The common decoder deliberately tolerates unknown fields for reads.
        // Migration must not erase any such future reserved content. Check both
        // duplicate keys and the exact represented v1 field census before writes.
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        let value = try JSONDecoder().decode(AnyJSON.self, from: bytes)
        guard let fields = value.object, Set(fields.keys) == ["version", "marker"] else {
            throw PinkhaSemanticTextAnchorError.invalidMarker
        }
        guard destination.target.blockId == nil else { throw PinkhaSemanticTextAnchorError.wrongDocument }
        let anchor = try PinkhaSemanticTextAnchor(spaceID: destination.spaceId,
            objectID: destination.target.objectId, id: semantic.anchor.id)
        var result = item
        result.customMetadata?.removeValue(forKey: TorahSemanticAnchorAssociation.metadataKey)
        return try TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: result, location: destination)
    }
}
