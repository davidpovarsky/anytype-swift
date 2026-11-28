import Foundation

public enum PinkhaSharingEngine: String, Sendable, Hashable { case heart, any }

public enum PinkhaSharingError: Error, Equatable, Sendable {
    case invalidResponse, invalidInput, permissionDenied, staleContext, busy, writeUncertain
}

public struct PinkhaSharingScope: Sendable, Hashable {
    public let engine: PinkhaSharingEngine
    public let accountID: String
    public let spaceID: String

    public init(engine: PinkhaSharingEngine, accountID: String, spaceID: String) throws {
        guard Self.validID(accountID), Self.validID(spaceID) else { throw PinkhaSharingError.invalidInput }
        self.engine = engine
        self.accountID = accountID
        self.spaceID = spaceID
    }

    public static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1024 && !value.utf8.contains(0)
    }
}

public enum PinkhaSharingRole: String, Sendable, CaseIterable {
    case none, guest, reader, writer, admin, owner
}

public enum PinkhaSharingMemberStatus: String, Sendable {
    case unknown, joining, active, removed, declined, removing, canceled
}

public struct PinkhaSharingMember: Sendable, Equatable, Identifiable {
    public let id: String
    public let name: String
    public let role: PinkhaSharingRole
    public let status: PinkhaSharingMemberStatus
    public let requestID: String?

    public init(id: String, name: String, role: PinkhaSharingRole,
                status: PinkhaSharingMemberStatus, requestID: String? = nil) throws {
        guard PinkhaSharingScope.validID(id), name.utf8.count <= 16_384,
              requestID.map(PinkhaSharingScope.validID) ?? true else {
            throw PinkhaSharingError.invalidResponse
        }
        self.id = id
        self.name = name
        self.role = role
        self.status = status
        self.requestID = requestID
    }
}

/// The share value is private account data. Never include it in diagnostics.
public struct PinkhaSharingInvitation: Sendable, Equatable, Identifiable,
    CustomStringConvertible, CustomDebugStringConvertible {
    public let id: String
    public let shareValue: String?
    public init(id: String, shareValue: String?) throws {
        guard PinkhaSharingScope.validID(id),
              shareValue.map({ !$0.isEmpty && $0.utf8.count <= 16_384 && !$0.utf8.contains(0) }) ?? true else {
            throw PinkhaSharingError.invalidResponse
        }
        self.id = id
        self.shareValue = shareValue
    }
    public var description: String { "PinkhaSharingInvitation(redacted)" }
    public var debugDescription: String { description }
}

/// Capabilities control the UI; each native engine still authorizes every mutation.
public struct PinkhaSharingCapabilities: Sendable, Equatable {
    public let canCreateInvitation: Bool
    public let canRevokeInvitation: Bool
    public let canApproveRequests: Bool
    public let grantableRoles: [PinkhaSharingRole]
    public let editableMemberIDs: Set<String>
    public let removableMemberIDs: Set<String>
    /// Nil preserves the existing global role choices. A supplied map denies
    /// role changes for any member without an explicit entry.
    public let memberRoleOptions: [String: [PinkhaSharingRole]]?

    public init(canCreateInvitation: Bool, canRevokeInvitation: Bool,
                canApproveRequests: Bool, grantableRoles: [PinkhaSharingRole],
                editableMemberIDs: Set<String>, removableMemberIDs: Set<String>,
                memberRoleOptions: [String: [PinkhaSharingRole]]? = nil) throws {
        guard Set(grantableRoles).count == grantableRoles.count,
              !grantableRoles.contains(.owner), !grantableRoles.contains(.none),
              editableMemberIDs.allSatisfy(PinkhaSharingScope.validID),
              removableMemberIDs.allSatisfy(PinkhaSharingScope.validID) else {
            throw PinkhaSharingError.invalidResponse
        }
        if let memberRoleOptions {
            guard memberRoleOptions.keys.allSatisfy(PinkhaSharingScope.validID),
                  Set(memberRoleOptions.keys).isSubset(of: editableMemberIDs),
                  memberRoleOptions.values.allSatisfy({ roles in
                      Set(roles).count == roles.count
                          && !roles.contains(.owner) && !roles.contains(.none)
                  }) else {
                throw PinkhaSharingError.invalidResponse
            }
        }
        self.canCreateInvitation = canCreateInvitation
        self.canRevokeInvitation = canRevokeInvitation
        self.canApproveRequests = canApproveRequests
        self.grantableRoles = grantableRoles
        self.editableMemberIDs = editableMemberIDs
        self.removableMemberIDs = removableMemberIDs
        self.memberRoleOptions = memberRoleOptions
    }

    public func rolesForMemberChange(_ identity: String) -> [PinkhaSharingRole] {
        guard editableMemberIDs.contains(identity) else { return [] }
        if let memberRoleOptions { return memberRoleOptions[identity] ?? [] }
        return grantableRoles
    }
}

public struct PinkhaSharingSnapshot: Sendable, Equatable {
    public let scope: PinkhaSharingScope
    public let currentIdentity: String
    public let members: [PinkhaSharingMember]
    public let invitations: [PinkhaSharingInvitation]
    public let capabilities: PinkhaSharingCapabilities

    public init(scope: PinkhaSharingScope, currentIdentity: String,
                members: [PinkhaSharingMember], invitations: [PinkhaSharingInvitation],
                capabilities: PinkhaSharingCapabilities) throws {
        guard PinkhaSharingScope.validID(currentIdentity), members.count <= 10_000,
              invitations.count <= 10_000, Set(members.map(\.id)).count == members.count,
              Set(invitations.map(\.id)).count == invitations.count,
              let current = members.first(where: { $0.id == currentIdentity }),
              current.status == .active, current.role != .none else {
            throw PinkhaSharingError.invalidResponse
        }
        let editable = Set(members.filter { $0.id != currentIdentity && $0.role != .owner
            && $0.status == .active }.map(\.id))
        guard capabilities.editableMemberIDs.isSubset(of: editable),
              capabilities.removableMemberIDs.isSubset(of: editable) else {
            throw PinkhaSharingError.invalidResponse
        }
        self.scope = scope
        self.currentIdentity = currentIdentity
        self.members = members
        self.invitations = invitations
        self.capabilities = capabilities
    }
}

public enum PinkhaSharingMutation: Sendable, Equatable {
    case approve(identity: String, requestID: String, role: PinkhaSharingRole)
    case decline(identity: String)
    case changeRole(identity: String, role: PinkhaSharingRole)
    case remove(identity: String)
    case revokeInvitation(id: String)

    public func validate(in state: PinkhaSharingSnapshot) throws {
        let permissions = state.capabilities
        switch self {
        case let .approve(identity, requestID, role):
            guard permissions.canApproveRequests, permissions.grantableRoles.contains(role),
                  state.members.contains(where: { $0.id == identity && $0.status == .joining
                      && $0.requestID == requestID }) else { throw PinkhaSharingError.permissionDenied }
        case let .decline(identity):
            guard permissions.canApproveRequests,
                  state.members.contains(where: { $0.id == identity && $0.status == .joining }) else {
                throw PinkhaSharingError.permissionDenied
            }
        case let .changeRole(identity, role):
            guard permissions.rolesForMemberChange(identity).contains(role) else {
                throw PinkhaSharingError.permissionDenied
            }
        case let .remove(identity):
            guard permissions.removableMemberIDs.contains(identity) else {
                throw PinkhaSharingError.permissionDenied
            }
        case let .revokeInvitation(id):
            guard permissions.canRevokeInvitation, state.invitations.contains(where: { $0.id == id }) else {
                throw PinkhaSharingError.permissionDenied
            }
        }
    }
}

public struct PinkhaSharingJoinResult: Sendable, Equatable {
    public enum Status: Sendable { case active, awaitingApproval, loading }
    public let spaceID: String
    public let status: Status
    public init(spaceID: String, status: Status) throws {
        guard PinkhaSharingScope.validID(spaceID) else { throw PinkhaSharingError.invalidResponse }
        self.spaceID = spaceID
        self.status = status
    }
}

@MainActor
public protocol PinkhaSpaceSharingService: AnyObject, Sendable {
    var scope: PinkhaSharingScope { get }
    func snapshot() async throws -> PinkhaSharingSnapshot
    func createInvitation() async throws -> PinkhaSharingInvitation
    /// Return only real post-write state. Never optimistically change a member.
    func apply(_ mutation: PinkhaSharingMutation) async throws -> PinkhaSharingSnapshot
}
