import Foundation
import PinkhaAnyEngine

enum AnyDestinationImmutableRecordChecks {
    /// Only an explicit native Records declaration created by this plan may
    /// acquire immutable rows. Runtime schema/membership fencing is additional.
    static func requireOwnedDeclaration(items: [AnyDestinationMigrationItem],
                                        ownerType: AnyDestinationReference, datasetKey: String, values: AnyDestinationValue) throws {
        guard let supplied = try values.resolved(AnyDestinationPlanChecks.placeholder).object else {
            throw AnyDestinationMigrationError.invalidPlan("immutable record values")
        }
        var matched = 0
        for item in items {
            guard case .partDefinition(let owner, let draft) = item.operation, owner == ownerType else { continue }
            let value = try draft.resolved(AnyDestinationPlanChecks.placeholder)
            for dataset in value["datasets"]?.array ?? [] where dataset["key"] == .string(datasetKey) {
                guard dataset["module"] == .string("records"),
                      dataset["dynamic"] == nil || dataset["dynamic"] == .bool(false),
                      dataset["shared"] == nil || dataset["shared"] == .bool(false),
                      dataset["deleteBy"] == .string("none"),
                      dataset["idRule"] == nil || dataset["idRule"] == .string("auto"),
                      let fields = dataset["fields"]?.array, !fields.isEmpty, fields.count <= 128 else {
                    throw AnyDestinationMigrationError.invalidPlan("owned immutable dataset declaration")
                }
                var keys = Set<Data>(), callerKeys = Set<String>(), requiredKeys = Set<String>()
                for field in fields {
                    guard let key = field["key"]?.string, AnyPreparedImmutableRecordIntent.validField(key),
                          keys.insert(Data(key.utf8)).inserted,
                          field["mutableBy"] == nil || field["mutableBy"] == .string("never") else {
                        throw AnyDestinationMigrationError.invalidPlan("owned immutable field declaration")
                    }
                    switch field["stamp"]?.string {
                    case nil, "", "none":
                        callerKeys.insert(key)
                        if field["required"] == .bool(true) { requiredKeys.insert(key) }
                        guard field["scope"] == nil || field["scope"] == .string("synced"),
                              field["kind"]?.string != nil else {
                            throw AnyDestinationMigrationError.invalidPlan("owned immutable field scope")
                        }
                    case "creator", "createTime":
                        guard field["scope"] == nil || field["scope"] == .string("derived"),
                              field["required"] == nil || field["required"] == .bool(false) else {
                            throw AnyDestinationMigrationError.invalidPlan("owned immutable native stamp")
                        }
                    default: throw AnyDestinationMigrationError.invalidPlan("owned immutable native stamp")
                    }
                }
                guard Set(supplied.keys).isSubset(of: callerKeys), requiredKeys.isSubset(of: Set(supplied.keys)) else {
                    throw AnyDestinationMigrationError.invalidPlan("immutable required fields or forged native stamps")
                }
                matched += 1
            }
        }
        guard matched == 1 else { throw AnyDestinationMigrationError.invalidPlan("unique owned immutable dataset required") }
    }
}
