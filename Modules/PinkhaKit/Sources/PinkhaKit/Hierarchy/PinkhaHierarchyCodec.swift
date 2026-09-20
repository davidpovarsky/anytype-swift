import Foundation

/// Pure codec for Pinkha hierarchy property values, isolating Anytype Object Relation
/// encoding and decoding conventions from UI/app frameworks.
public enum PinkhaHierarchyCodec {

    /// Encodes a parent object ID into the canonical Object Relation array format.
    /// In Anytype, Object Relations are stored as an array of object IDs even with maxCount = 1.
    /// Returns `[parentId]` if non-empty, or an empty array `[]` representing root/clear parent.
    public static func encodeParentRelation(parentId: String?) -> [String] {
        guard let parentId, !parentId.isEmpty else {
            return []
        }
        return [parentId]
    }

    /// Decodes a parent object ID from either canonical Object Relation list values
    /// or legacy scalar string values (for backward compatibility with pre-fix items).
    ///
    /// - Parameters:
    ///   - listValues: An array of object IDs (canonical format).
    ///   - scalarValue: A single string value (legacy format).
    /// - Returns: The extracted parent ID if present and non-empty, otherwise nil.
    public static func decodeParentId(listValues: [String]?, scalarValue: String?) -> String? {
        // Priority 1: Canonical Object Relation list values
        if let listValues, let first = listValues.first, !first.isEmpty {
            return first
        }
        // Priority 2: Legacy scalar string value (backward-compatible)
        // TODO: [Migration] Remove scalar compatibility after legacy data migration is addressed.
        if let scalarValue, !scalarValue.isEmpty {
            return scalarValue
        }
        return nil
    }
}
