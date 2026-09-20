import Foundation
import Services
import PinkhaKit

/// Configuration helper that builds and validates the canonical key list requested
/// by the Pinkha hierarchy subscription and fallback reload search.
public enum PinkhaHierarchySubscriptionConfiguration {

    /// Returns the canonical key list for the hierarchy subscription and reload queries.
    /// Combines standard Anytype object list keys (`BundledPropertyKey.objectListKeys`) with
    /// the custom Pinkha parent and order keys from the space manifest.
    public static func hierarchyKeys(manifest: PinkhaSpaceManifest) -> [String] {
        hierarchyKeys(
            parentPropertyKey: manifest.parentPropertyKey,
            orderPropertyKey: manifest.orderPropertyKey
        )
    }

    /// Returns the canonical key list given explicit parent and order property keys.
    public static func hierarchyKeys(parentPropertyKey: String, orderPropertyKey: String) -> [String] {
        let standardKeys = BundledPropertyKey.objectListKeys.map(\.rawValue)
        let keys = PinkhaHierarchyKeyBuilder.buildKeys(
            standardKeys: standardKeys,
            parentPropertyKey: parentPropertyKey,
            orderPropertyKey: orderPropertyKey
        )
        assertValidHierarchyKeys(keys, parentPropertyKey: parentPropertyKey, orderPropertyKey: orderPropertyKey)
        return keys
    }

    /// Asserts that the key list includes all required standard keys and custom manifest keys.
    public static func assertValidHierarchyKeys(
        _ keys: [String],
        parentPropertyKey: String,
        orderPropertyKey: String
    ) {
        assert(keys.contains(BundledPropertyKey.id.rawValue), "Hierarchy subscription keys must include 'id'")
        assert(keys.contains(BundledPropertyKey.type.rawValue), "Hierarchy subscription keys must include 'type'")
        assert(keys.contains(BundledPropertyKey.name.rawValue), "Hierarchy subscription keys must include 'name'")
        if !parentPropertyKey.isEmpty {
            assert(keys.contains(parentPropertyKey), "Hierarchy subscription keys must include parentPropertyKey '\(parentPropertyKey)'")
        }
        if !orderPropertyKey.isEmpty {
            assert(keys.contains(orderPropertyKey), "Hierarchy subscription keys must include orderPropertyKey '\(orderPropertyKey)'")
        }
    }
}
