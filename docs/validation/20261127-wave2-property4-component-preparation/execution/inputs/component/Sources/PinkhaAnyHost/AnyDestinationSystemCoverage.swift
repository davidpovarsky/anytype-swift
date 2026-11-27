import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Retention records original system bytes only. It does not translate source
/// ACL membership, roles or history into destination permissions. Identity is
/// joined to the original manifest, never inferred from a caller-selected label.
enum AnyDestinationSystemCoverageChecks {
    static func require(source: AnyDestinationSourceBinding, sourceID: String,
                        kind: AnyDestinationCoverage.SystemKind, capturedRowCount: Int) throws {
        guard let bytes = source.definitionManifestBytes,
              AnyContentDigest.sha256(bytes) == source.captureManifestSHA256,
              (0...10_000_000).contains(capturedRowCount),
              source.definitionMembers[Data(sourceID.utf8)] == nil else {
            throw AnyDestinationMigrationError.invalidPlan("system preservation original manifest")
        }
        let manifest = try JSONDecoder().decode(AnyJSON.self, from: bytes)
        let receipt = manifest["Receipt"], inventory = receipt?["Inventory"]
        let native = receipt?["Source"]?["source"]?["native"]
        let idHash = AnyContentDigest.sha256(Data(sourceID.utf8))
        guard inventory?["Version"] == .string("native-tree-identity-inventory-v2"),
              inventory?["AllHeadRowsAccounted"] == .bool(true),
              receipt?["AllNativeHeadRowsAccounted"] == .bool(true),
              native?["Version"] == .string("native-localstore-witness-v1"),
              native?["Encoding"] == .string("anyenc-v1.0.3-decoded-value-roundtrip-v1"),
              native?["Authority"] == .string("heart-owned-local-store-v1"),
              native?["WitnessSHA256"] == .string(source.witnessSHA256),
              let trees = manifest["Trees"]?.array,
              !trees.contains(where: { $0["ObjectID"]?.string.map { Data($0.utf8) == Data(sourceID.utf8) } == true }),
              let collections = native?["CollectionCoverage"]?.array else {
            throw AnyDestinationMigrationError.invalidPlan("system preservation native source")
        }
        let matching = collections.filter { $0["NameSHA256"] == .string(idHash) }
        guard matching.count == 1, let collection = matching.first,
              let fields = collection.object,
              Set(fields.keys) == ["NameSHA256", "Rows", "EncodedValueBytes", "UnresolvedCollection"],
              collection["Rows"] == .integer(Int64(capturedRowCount)),
              let encodedBytes = collection["EncodedValueBytes"]?.integer, encodedBytes >= 0,
              collection["UnresolvedCollection"]?.bool != nil else {
            throw AnyDestinationMigrationError.invalidPlan("system preservation original row count")
        }
        switch kind {
        case .nativeACL:
            guard capturedRowCount > 0,
                  receipt?["Source"]?["source"]?["aclIdSHA256"] == .string(idHash) else {
                throw AnyDestinationMigrationError.invalidPlan("system preservation native ACL identity")
            }
        case .emptyNativeKeyValue:
            let expectedID = try AnyHeartNativeStoreContext.defaultKeyValueCollectionID(spaceID: source.spaceID)
            guard Data(sourceID.utf8) == Data(expectedID.utf8),
                  capturedRowCount == 0, encodedBytes == 0,
                  inventory?["KeyValueStores"] == .integer(1), inventory?["KeyValueRows"] == .integer(0),
                  let retained = manifest["RetainedOtherCollections"]?.array else {
                throw AnyDestinationMigrationError.invalidPlan("system preservation native KV identity")
            }
            let matching = retained.filter { $0["Name"]?.string.map { Data($0.utf8) == Data(expectedID.utf8) } == true }
            guard matching.count == 1, let original = matching.first,
                  let fields = original.object, Set(fields.keys) == ["Name", "Rows", "Bytes"],
                  original["Rows"] == .integer(0), original["Bytes"] == .integer(0) else {
                throw AnyDestinationMigrationError.invalidPlan("system preservation nonempty or unbound KV")
            }
        }
    }
}
