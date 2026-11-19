import Foundation
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost

public struct AnyHanlinPageEligibility: Sendable, Equatable {
    public let fingerprint: String
    public let permission: String
    public let typeID: String
}

/// Engine-specific Page eligibility. Any's built-in page is intentionally
/// hidden in its type picker; the old Heart "hidden == false" condition would
/// incorrectly deny ordinary native pages. Its immutable built-in ID/xKey is
/// the eligibility boundary, followed by the current native member role.
public struct AnyHanlinCreationAuthority: Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard client.expectedAccountID == workspace.accountID else { throw AnyHostError.wrongWorkspace }
        self.client = client; self.workspace = workspace
    }

    public func inspect(lease: AnyHostLease) async throws -> AnyHanlinPageEligibility {
        guard lease.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        try await lease.validate()
        let capabilities = try await client.requestJSON(method: "GET",
            path: ["v1", "pinkha", "capabilities"], authorize: { try await lease.validate() })
        try Self.requireCurrentWriterCreation(capabilities)
        let member = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", workspace.spaceID, "members", "me"],
            authorize: { try await lease.validate() })
        guard member["identity"]?.string?.utf8.elementsEqual(workspace.accountID.utf8) == true,
              member["status"]?.string == "active",
              let role = member["permission"]?.string,
              ["owner", "admin", "writer"].contains(role) else { throw HanlinHostError.denied }
        let type = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", workspace.spaceID, "types", "page"],
            authorize: { try await lease.validate() })
        guard type["id"]?.string == "page", type["xKey"]?.string == "page",
              type["builtIn"]?.bool == true else { throw HanlinHostError.denied }
        try await lease.validate()
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let state: AnyJSON = .object(["member": member, "type": type,
            "currentWriterObjectCreate": .integer(1),
            "contract": .string(AnyGuardedTorahCapabilities.contract)])
        return .init(fingerprint: PinkhaHanlinCreatePagePlan.digest(try encoder.encode(state)),
                     permission: role, typeID: "page")
    }

    /// Membership/type inspection alone cannot fence native root/bootstrap storage.
    /// The versioned route must be implemented by the running managed engine.
    static func requireCurrentWriterCreation(_ capabilities: AnyJSON) throws {
        guard capabilities["contract"]?.string == AnyGuardedTorahCapabilities.contract,
              capabilities["currentWriterObjectCreate"]?.integer == 1 else {
            throw HanlinHostError.denied
        }
    }
}

public struct AnyHanlinCreatePagePrompt: Sendable {
    public let session: HanlinHostSession
    public let invocationID: String
    public let title: String
    public let spaceID: String
}

/// The actual mounted SDK UI presents an exact title/original Space prompt.
/// Each answer is revalidated by the native host; a model cannot mint approval.
@MainActor
public protocol AnyHanlinCreationPresentationOwner: AnyHanlinPresentationOwner {
    func validateSDKPresentation(for session: HanlinHostSession) throws
    func presentCreatePageConfirmation(_ prompt: AnyHanlinCreatePagePrompt,
                                      answer: @escaping @MainActor (Bool) -> Void) throws
}
