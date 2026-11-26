import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Original source facts are immutable Records owned by the actual imported
/// Type. Their native creator/time are independently signed destination facts;
/// the historical source identities and values remain inside the original
/// byte-preserved snapshot and its explicit derived-field binding list.
public enum AnyHeartNativeSourceFacts {
    public static let contract = "pinkha-heart-native-source-facts-v1"
    public static let datasetKey = "heart_source_facts"

    static func definitionItem(type: AnyHeartNativeDefinitionPlan.TypeBinding) -> AnyDestinationMigrationItem {
        let ordinary = ["sourceObject", "sourceSnapshotBase64", "sourceViewJSON",
                        "sourceSnapshotSHA256", "sourceViewSHA256", "sourceDerivedBindingsJSON"]
        let fields: [AnyJSON] = ordinary.map {
            .object(["key": .string($0), "kind": .string("string"), "required": .bool(true)])
        } + [.object(["key": .string("importedBy"), "stamp": .string("creator")]),
             .object(["key": .string("importedAt"), "stamp": .string("createTime")])]
        return .init(sourceKey: type.sourceKey + ":source-facts-part", sourceObjectID: type.definition.objectID,
            expectedRecordCount: fields.count + 2,
            operation: .partDefinition(owner: type.object, draft: .literal(.object([
                "key": .string(datasetKey), "name": .string("Original source facts"),
                "datasets": .array([.object(["key": .string(datasetKey), "module": .string("records"),
                    "deleteBy": .string("none"), "fields": .array(fields)])]),
            ]))))
    }

    static func item(snapshot: AnyHeartNativeSnapshotView, values: AnyHeartNativeDefinitionPlan.Values,
                     type: AnyHeartNativeDefinitionPlan.TypeBinding, objectSourceKey: String) throws -> AnyDestinationMigrationItem {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        guard AnyContentDigest.sha256(snapshot.protobufBytes) == snapshot.snapshotSHA256,
              AnyContentDigest.sha256(snapshot.jsonViewBytes) == snapshot.viewSHA256,
              try AnyContentDigest.sha256(encoder.encode(AnyJSON.object(snapshot.details))) == values.originalDetailsSHA256,
              let view = String(data: snapshot.jsonViewBytes, encoding: .utf8) else {
            throw AnyDestinationMigrationError.changedSource
        }
        var seen = Set<Data>(), bindings: [AnyJSON] = []
        for fact in values.nativeDerivedSourceValues {
            guard seen.insert(Data(fact.sourceRelationKey.utf8)).inserted,
                  Data(fact.sourceObjectID.utf8) == Data(snapshot.sourceObjectID.utf8),
                  fact.snapshotSHA256 == snapshot.snapshotSHA256, fact.jsonViewSHA256 == snapshot.viewSHA256,
                  let role = AnyDestinationCanonicalPropertyBinding.DerivedRole(rawValue: fact.destinationPropertyID),
                  role.sourceKey == fact.sourceRelationKey,
                  let original = snapshot.details[fact.sourceRelationKey],
                  try AnyDestinationDefinitionChecks.bytes(original) == AnyDestinationDefinitionChecks.bytes(fact.originalValue) else {
                throw AnyDestinationMigrationError.changedSource
            }
            bindings.append(.object(["sourceRelationKey": .string(fact.sourceRelationKey),
                "nativePropertyID": .string(fact.destinationPropertyID), "originalValue": fact.originalValue]))
        }
        let bindingBytes = try encoder.encode(AnyJSON.object([
            "contract": .string(contract), "historicalValues": .array(bindings),
            "historicalAuthorIsDestinationSigner": .bool(false),
        ]))
        let bindingText = String(decoding: bindingBytes, as: UTF8.self)
        let fields: AnyJSON = .object([
            "sourceObject": .string(snapshot.sourceObjectID),
            "sourceSnapshotBase64": .string(snapshot.protobufBytes.base64EncodedString()),
            "sourceViewJSON": .string(view),
            "sourceSnapshotSHA256": .string(snapshot.snapshotSHA256),
            "sourceViewSHA256": .string(snapshot.viewSHA256),
            "sourceDerivedBindingsJSON": .string(bindingText),
        ])
        return .init(sourceKey: objectSourceKey + ":source-facts", sourceObjectID: snapshot.sourceObjectID,
            operation: .immutableRecord(object: .mapped(sourceKey: objectSourceKey, slot: .objectID, encoding: .rawID),
                ownerType: type.object, datasetKey: datasetKey, values: .literal(fields)))
    }
}
