import Foundation
import PinkhaAnyEngine

/// Immutable wire plan shared by the production archive path and its bounded
/// request-contract tests. This value never authorizes or dispatches a write.
struct AnyHierarchyArchiveRequest: Sendable {
    let path: [String]
    let body: AnyJSON
    let fence: AnyConditionalPropertyFence
    let isNoop: Bool

    init(record: AnyJSON, objectID: String, workspace: AnyTorahWorkspace,
         schema: AnyHierarchySchema, archived: Bool, engineStartedAt: String,
         capabilities: AnyJSON) throws {
        guard capabilities["contract"]?.string == "pinkha-torah-native-v1",
              capabilities["conditionalPropertiesSet"]?.integer == 1,
              capabilities["conditionalMembershipSet"]?.integer == 1,
              capabilities["conditionalPropertiesApplySeq"]?.integer == 1 else {
            throw AnyEngineError.incompatibleSchema("conditional hierarchy membership fence unavailable")
        }
        guard AnyHierarchySchema.validID(objectID),
              record["id"]?.string == objectID,
              record["spaceId"]?.string == workspace.spaceID,
              let values = record["any"]?["collections"]?.array,
              values.allSatisfy({ $0.string.map(AnyHierarchySchema.validID) == true }),
              Set(values.compactMap(\.string)).count == values.count,
              values.contains(.string(schema.collectionID)),
              !values.contains(.string("template")) else {
            throw AnyHierarchyError.malformedRow(objectID)
        }
        let captured = try AnyConditionalPropertyFence(record: record, engineStartedAt: engineStartedAt)
        var memberships = values
        if archived {
            if !memberships.contains(.string("bin")) { memberships.append(.string("bin")) }
        } else {
            memberships.removeAll { $0 == .string("bin") }
        }
        let unchanged = memberships == values
        if unchanged {
            guard capabilities["conditionalPropertiesNoop"]?.integer == 1 else {
                throw AnyEngineError.incompatibleSchema("conditional hierarchy no-op unavailable")
            }
        }
        self.path = ["v1", "spaces", workspace.spaceID, "pinkha", "properties", objectID, "set", "any"]
        self.fence = captured
        self.isNoop = unchanged
        self.body = captured.requestBody(patch: unchanged ? [:] : ["collections": .array(memberships)])
    }
}
