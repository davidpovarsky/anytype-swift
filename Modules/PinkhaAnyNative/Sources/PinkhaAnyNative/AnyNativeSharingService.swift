import Foundation
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaSharing

/// The shared management UI calls Any's original signed ACL/coordinator API.
/// This adapter never manufactures membership, invite keys or a successful ACK.
@MainActor
public final class AnyNativeSharingService: PinkhaSpaceSharingService {
    public let scope: PinkhaSharingScope
    private let client: AnyHTTPClient
    private let session: AnyApplicationSession

    public init(owner: AnyNativeWorkspaceOwner) throws {
        scope = try .init(engine: .any, accountID: owner.workspace.accountID,
                          spaceID: owner.workspace.spaceID)
        client = owner.client
        session = owner.session
    }

    public func snapshot() async throws -> PinkhaSharingSnapshot {
        let client = client, scope = scope
        return try await session.perform { lease in
            try await Self.readSnapshot(client: client, scope: scope, lease: lease)
        }
    }

    public func createInvitation() async throws -> PinkhaSharingInvitation {
        let client = client, scope = scope
        return try await session.perform { lease in
            let before = try await Self.readSnapshot(client: client, scope: scope, lease: lease)
            guard before.capabilities.canCreateInvitation else { throw PinkhaSharingError.permissionDenied }
            let reply = try await client.requestJSON(method: "POST",
                path: ["v1", "spaces", scope.spaceID, "invites"], maximumResponseBytes: 128 * 1024,
                authorize: { try await lease.validate() })
            guard reply["spaceId"]?.string == scope.spaceID,
                  let token = reply["inviteToken"]?.string, !token.isEmpty else {
                throw PinkhaSharingError.writeUncertain
            }
            // The native mint returns a token, not a record ID. Read the original
            // custody-backed list before exposing a revocable invitation.
            let after = try await Self.readSnapshot(client: client, scope: scope, lease: lease)
            guard let invitation = after.invitations.first(where: { $0.shareValue == token }) else {
                throw PinkhaSharingError.writeUncertain
            }
            return invitation
        }
    }

    public func apply(_ mutation: PinkhaSharingMutation) async throws -> PinkhaSharingSnapshot {
        let client = client, scope = scope
        return try await session.perform { lease in
            let before = try await Self.readSnapshot(client: client, scope: scope, lease: lease)
            try mutation.validate(in: before)
            let base = ["v1", "spaces", scope.spaceID]
            let path: [String], body: AnyJSON?, method: String
            switch mutation {
            case let .approve(_, requestID, role):
                method = "POST"; path = base + ["acl", "accept"]
                body = .object(["requestRecordId": .string(requestID), "permission": .string(role.rawValue)])
            case let .decline(identity):
                method = "POST"; path = base + ["acl", "decline"]
                body = .object(["identity": .string(identity)])
            case let .changeRole(identity, role):
                method = "POST"; path = base + ["acl", "permissions"]
                body = .object(["changes": .array([.object([
                    "identity": .string(identity), "permission": .string(role.rawValue)])])])
            case let .remove(identity):
                method = "POST"; path = base + ["acl", "remove"]
                body = .object(["identities": .array([.string(identity)])])
            case let .revokeInvitation(id):
                method = "DELETE"; path = base + ["invites", id]; body = nil
            }
            _ = try await client.requestJSON(method: method, path: path, body: body,
                maximumResponseBytes: 128 * 1024, authorize: { try await lease.validate() })
            return try await Self.readSnapshot(client: client, scope: scope, lease: lease)
        }
    }

    private nonisolated static func readSnapshot(client: AnyHTTPClient, scope: PinkhaSharingScope,
                                                 lease: AnyHostLease) async throws -> PinkhaSharingSnapshot {
        guard client.expectedAccountID == scope.accountID,
              lease.workspace.accountID == scope.accountID,
              lease.workspace.spaceID == scope.spaceID else { throw PinkhaSharingError.staleContext }
        let base = ["v1", "spaces", scope.spaceID]
        let me = try decodeMember(await client.requestJSON(method: "GET", path: base + ["members", "me"],
            maximumResponseBytes: 128 * 1024, authorize: { try await lease.validate() }))
        guard me.status == .active, me.role != .none else { throw PinkhaSharingError.permissionDenied }
        let response = try await client.requestJSON(method: "GET", path: base + ["members"],
            maximumResponseBytes: 8 * 1024 * 1024, authorize: { try await lease.validate() })
        guard let rows = response["members"]?.array, rows.count <= 10_000 else {
            throw PinkhaSharingError.invalidResponse
        }
        var members = try rows.map(decodeMember)
        guard Set(members.map(\.id)).count == members.count,
              let current = members.first(where: { $0.id == me.id }),
              current.role == me.role, current.status == me.status else {
            throw PinkhaSharingError.invalidResponse
        }
        let moderator = me.role == .owner || me.role == .admin
        if moderator {
            let response = try await client.requestJSON(method: "GET", path: base + ["members", "requests"],
                maximumResponseBytes: 8 * 1024 * 1024, authorize: { try await lease.validate() })
            guard let requests = response["requests"]?.array, requests.count <= 10_000 else {
                throw PinkhaSharingError.invalidResponse
            }
            var seen = Set<String>()
            for raw in requests {
                guard let id = raw["identity"]?.string, let record = raw["recordId"]?.string,
                      seen.insert(id).inserted else { throw PinkhaSharingError.invalidResponse }
                if let member = members.first(where: { $0.id == id }), member.status != .joining {
                    throw PinkhaSharingError.invalidResponse
                }
                members.removeAll { $0.id == id }
                members.append(try .init(id: id, name: raw["name"]?.string ?? "", role: .none,
                                         status: .joining, requestID: record))
            }
        }
        let responseInvites = try await client.requestJSON(method: "GET", path: base + ["invites"],
            maximumResponseBytes: 8 * 1024 * 1024, authorize: { try await lease.validate() })
        guard let inviteRows = responseInvites["invites"]?.array, inviteRows.count <= 10_000 else {
            throw PinkhaSharingError.invalidResponse
        }
        let invitations = try inviteRows.map { raw -> PinkhaSharingInvitation in
            guard let id = raw["recordId"]?.string else { throw PinkhaSharingError.invalidResponse }
            return try .init(id: id, shareValue: raw["inviteToken"]?.string)
        }
        let capabilities = try sharingCapabilities(currentMember: me, members: members, invitations: invitations)
        return try .init(scope: scope, currentIdentity: me.id, members: members,
                         invitations: invitations, capabilities: capabilities)
    }

    /// A projection of the current native snapshot, never mutation authority.
    /// Approval grants and existing-member transitions have distinct ACL rules.
    nonisolated static func sharingCapabilities(
        currentMember me: PinkhaSharingMember,
        members: [PinkhaSharingMember], invitations: [PinkhaSharingInvitation]
    ) throws -> PinkhaSharingCapabilities {
        let moderator = me.role == .owner || me.role == .admin
        let removable = Set(members.filter {
            $0.status == .active && $0.id != me.id && $0.role != .owner
                && (me.role == .owner || (me.role == .admin && $0.role != .admin))
        }.map(\.id))
        // Guest membership may be removed, but its role cannot be upgraded.
        let editableMembers = members.filter { removable.contains($0.id) && $0.role != .guest }
        let editable = Set(editableMembers.map(\.id))
        let approvalRoles: [PinkhaSharingRole] = me.role == .owner ? [.reader, .writer, .admin]
            : (me.role == .admin ? [.reader, .writer] : [])
        var memberRoleOptions: [String: [PinkhaSharingRole]] = [:]
        for member in editableMembers {
            // Both Owner and Admin may convert a current Reader to Guest.
            memberRoleOptions[member.id] = member.role == .reader ? [.guest] + approvalRoles : approvalRoles
        }
        return try PinkhaSharingCapabilities(
            canCreateInvitation: me.role == .owner && invitations.isEmpty,
            canRevokeInvitation: me.role == .owner,
            canApproveRequests: moderator, grantableRoles: approvalRoles,
            editableMemberIDs: editable, removableMemberIDs: removable,
            memberRoleOptions: memberRoleOptions)
    }

    private nonisolated static func decodeMember(_ value: AnyJSON) throws -> PinkhaSharingMember {
        guard let id = value["identity"]?.string,
              let role = value["permission"]?.string.flatMap(PinkhaSharingRole.init(rawValue:)),
              let status = value["status"]?.string.flatMap(PinkhaSharingMemberStatus.init(rawValue:)) else {
            throw PinkhaSharingError.invalidResponse
        }
        return try .init(id: id, name: value["name"]?.string ?? "", role: role, status: status,
                         requestID: value["requestRecordId"]?.string)
    }
}
