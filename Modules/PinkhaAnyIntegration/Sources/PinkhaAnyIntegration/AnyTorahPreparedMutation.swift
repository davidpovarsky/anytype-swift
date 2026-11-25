import Foundation
import PinkhaKit
import PinkhaAnyEngine

/// Persist this entire value for an exact retry, not merely operationID.
/// It freezes payload and observed predecessors before the first dispatch.
public struct AnyTorahPreparedMutation: Codable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let operation: AnyTorahOperation

    public init(workspace: AnyTorahWorkspace, operation: AnyTorahOperation) throws {
        guard operation.spaceID == workspace.spaceID, operation.authorID == workspace.accountID else {
            throw AnyEngineError.invalidIdentity("prepared mutation workspace")
        }
        if operation.kind != .remove {
            let target: TorahAssociationTarget = operation.targetBlockID.isEmpty
                ? .object(objectId: operation.targetObjectID)
                : .block(objectId: operation.targetObjectID, blockId: operation.targetBlockID)
            let location = TorahAssociationLocation(spaceId: workspace.spaceID, target: target)
            _ = try AnyTorahSourceJSONGuard.preservingMigrationErrors {
                try TorahImmutableAssociationContent(
                    payload: operation.payload, location: location,
                    providerID: operation.providerID, canonicalRef: operation.canonicalRef)
            }
        }
        self.workspace = workspace
        self.operation = operation
    }

    private enum CodingKeys: String, CodingKey { case workspace, operation }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(workspace: values.decode(AnyTorahWorkspace.self, forKey: .workspace),
                      operation: values.decode(AnyTorahOperation.self, forKey: .operation))
    }
}
