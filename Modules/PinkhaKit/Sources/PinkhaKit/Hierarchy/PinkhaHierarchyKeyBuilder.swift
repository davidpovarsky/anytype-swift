import Foundation

/// Pure builder that constructs the unified property key list required by the Pinkha hierarchy
/// subscription and search queries.
public enum PinkhaHierarchyKeyBuilder {

    /// Standard property keys that the hierarchy builder and reconciler require for every object.
    public static let requiredStandardKeys: [String] = [
        "id",
        "type",
        "name"
    ]

    /// Combines standard object list keys with custom Pinkha parent and order keys,
    /// deduplicating keys while preserving insertion order.
    ///
    /// - Parameters:
    ///   - standardKeys: The base object list keys (e.g. from BundledPropertyKey.objectListKeys).
    ///   - parentPropertyKey: The custom Pinkha parent relation property key (e.g. pinkha.parent).
    ///   - orderPropertyKey: The custom Pinkha order numeric property key (e.g. pinkha.order).
    /// - Returns: A deduplicated array of all keys required to reconstruct the hierarchy.
    public static func buildKeys(
        standardKeys: [String],
        parentPropertyKey: String,
        orderPropertyKey: String
    ) -> [String] {
        var keys = standardKeys
        if !parentPropertyKey.isEmpty {
            keys.append(parentPropertyKey)
        }
        if !orderPropertyKey.isEmpty {
            keys.append(orderPropertyKey)
        }

        var seen = Set<String>()
        return keys.filter { seen.insert($0).inserted }
    }
}
