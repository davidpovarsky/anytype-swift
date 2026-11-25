import Foundation
import PinkhaAnyEngine

/// Display-only ordering for types from one exact imported definition catalog.
/// The native object IDs, eligibility proof and mutation policy are unchanged.
/// Unmarked types and different source catalogs retain their own slots.
struct AnyNativeImportedTypeOrder: Sendable {
    static let contract = "pinkha-heart-type-order-v1"
    static let contractKey = "heartTypeOrderContract"
    static let scopeKey = "heartTypeOrderScopeSHA256"
    static let valueKey = "heartTypeOrderValue"

    let scope: Data
    let sourceObjectID: Data
    /// nil is absent; an explicitly captured empty string remains present.
    let orderID: String?

    init?(owner: AnyNativePropertyOwner) throws {
        guard let metadata = owner.raw["meta"]?.object else { return nil }
        let claimed = Set(metadata.keys.filter { $0.hasPrefix("heartTypeOrder") })
        guard !claimed.isEmpty else { return nil }
        let allowed: Set<String> = [Self.contractKey, Self.scopeKey, Self.valueKey]
        guard !owner.builtIn, claimed.isSubset(of: allowed),
              metadata[Self.contractKey]?.string == Self.contract,
              let scope = metadata[Self.scopeKey]?.string, Self.digest(scope),
              let sourceID = metadata["heartSourceObjectID"]?.string,
              !sourceID.isEmpty, sourceID.utf8.count <= 4096, !sourceID.utf8.contains(0),
              let typeKey = metadata["heartTypeKey"]?.string,
              !typeKey.isEmpty, typeKey.utf8.count <= 4096, !typeKey.utf8.contains(0),
              metadata["heartUniqueKey"]?.string.map({ Data($0.utf8) }) == Data(("ot-" + typeKey).utf8),
              metadata["heartSnapshotSHA256"]?.string.map(Self.digest) == true,
              metadata["heartJSONViewSHA256"]?.string.map(Self.digest) == true else {
            throw AnyNativePropertyError.invalidCatalog
        }
        if let original = metadata[Self.valueKey] {
            guard let value = original.string, value.utf8.count <= 65_536 else {
                throw AnyNativePropertyError.invalidCatalog
            }
            orderID = value
        } else { orderID = nil }
        self.scope = Data(scope.utf8)
        sourceObjectID = Data(sourceID.utf8)
    }

    static func arranged(_ owners: [AnyNativePropertyOwner]) throws -> [AnyNativePropertyOwner] {
        var groups: [Data: [(index: Int, order: AnyNativeImportedTypeOrder)]] = [:]
        for (index, owner) in owners.enumerated() {
            if let order = try Self(owner: owner) {
                groups[order.scope, default: []].append((index, order))
            }
        }
        var result = owners
        for members in groups.values {
            guard Set(members.map { $0.order.sourceObjectID }).count == members.count else {
                throw AnyNativePropertyError.invalidCatalog
            }
            let sorted = members.sorted { left, right in
                let a = left.order.orderID ?? "", b = right.order.orderID ?? ""
                // Heart's actual default type query orders explicit ranks first,
                // with empty/absent values at the end. Keep the destination's
                // existing relative fallback order for ties and unranked rows.
                if a.isEmpty != b.isEmpty { return !a.isEmpty }
                let aBytes = Data(a.utf8), bBytes = Data(b.utf8)
                if aBytes != bBytes { return aBytes.lexicographicallyPrecedes(bBytes) }
                return left.index < right.index
            }
            for (slot, value) in zip(members, sorted) {
                result[slot.index] = owners[value.index]
            }
        }
        return result
    }

    private static func digest(_ value: String) -> Bool {
        value.utf8.count == 64 &&
            value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
}
