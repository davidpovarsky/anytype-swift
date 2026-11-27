import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Native graph values remain separate from SDK property values. In particular,
/// a link index result never becomes a mutable custom property named `links`.
public enum AnyNativeComputedRelationValue: Sendable {
    case outgoing(AnyNativeLinksSnapshot)
    case incoming(AnyNativeBacklinksSnapshot)
}

public struct AnyNativeComputedRelationSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let objectID: String
    public let binding: AnyHeartNativeComputedRelationBinding
    public let value: AnyNativeComputedRelationValue
    public var permitsDestinationWrites: Bool { false }
}

/// The source definition selects an exact read-only provider. The current
/// session owns account, Space and process authorization. The binding is not a
/// migration receipt, a write grant or evidence that a historical graph has
/// already been restored; consumers must keep those distinct.
public struct AnyNativeComputedRelationStore: Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard Data(client.expectedAccountID.utf8) == Data(workspace.accountID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        self.client = client
        self.workspace = workspace
    }

    public func read(_ binding: AnyHeartNativeComputedRelationBinding,
                     objectID: String, lease: AnyHostLease) async throws -> AnyNativeComputedRelationSnapshot {
        guard Data(lease.workspace.accountID.utf8) == Data(workspace.accountID.utf8),
              Data(lease.workspace.spaceID.utf8) == Data(workspace.spaceID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        guard AnyEditorBlock.validID(objectID) else { throw AnyNativePropertyError.invalidProperty }
        try await lease.validate()
        let provider = AnyNativeObjectLinks(client: client)
        let value: AnyNativeComputedRelationValue
        switch binding.role {
        case .outgoingLinks:
            value = .outgoing(try await provider.links(spaceID: workspace.spaceID,
                objectID: objectID, selection: .object, kind: nil, limit: 500,
                requireComplete: true, authorize: { try await lease.validate() }))
        case .backlinks:
            value = .incoming(try await provider.backlinks(spaceID: workspace.spaceID,
                objectID: objectID, selection: .object, kind: nil, limit: 500,
                requireComplete: true, authorize: { try await lease.validate() }))
        }
        try await lease.validate()
        return .init(workspace: workspace, generation: lease.generation,
            engineStartedAt: lease.engineStartedAt, objectID: objectID, binding: binding, value: value)
    }
}
