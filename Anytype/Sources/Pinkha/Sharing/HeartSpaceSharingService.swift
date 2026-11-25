import Foundation
import Services
import DeepLinks
import PinkhaSharing

/// Heart's existing RPCs remain the only membership/invitation implementation.
/// The common UI reads its existing participant subscription; native RPCs
/// perform the final ACL and plan-limit authorization on every mutation.
@MainActor
final class HeartSpaceSharingService: PinkhaSpaceSharingService {
    let scope: PinkhaSharingScope
    private let readState: @MainActor () throws -> ([Participant], ParticipantSpaceViewData)
    private let workspace = Container.shared.workspaceService()
    private let accounts = Container.shared.accountManager()
    private let links = Container.shared.universalLinkParser()

    init(scope: PinkhaSharingScope,
         readState: @escaping @MainActor () throws -> ([Participant], ParticipantSpaceViewData)) throws {
        guard scope.engine == .heart else { throw PinkhaSharingError.invalidInput }
        self.scope = scope
        self.readState = readState
    }

    func snapshot() async throws -> PinkhaSharingSnapshot {
        try await PinkhaSharingAccountOwner.shared.perform(scope: scope) { @MainActor [self] in
            try await readSnapshot()
        }
    }

    func createInvitation() async throws -> PinkhaSharingInvitation {
        try await PinkhaSharingAccountOwner.shared.perform(scope: scope) { @MainActor [self] in
            let before = try await readSnapshot()
            guard before.capabilities.canCreateInvitation else { throw PinkhaSharingError.permissionDenied }
            try checkAccount()
            let invitation = try await workspace.generateInvite(spaceId: scope.spaceID, inviteType: .member,
                                                                  permissions: nil, shareWithinSpace: false)
            try checkAccount()
            guard invitation.hasLink else { throw PinkhaSharingError.writeUncertain }
            return try sharingInvitation(invitation)
        }
    }

    func apply(_ mutation: PinkhaSharingMutation) async throws -> PinkhaSharingSnapshot {
        try await PinkhaSharingAccountOwner.shared.perform(scope: scope) { @MainActor [self] in
            let before = try await readSnapshot()
            try mutation.validate(in: before)
            try checkAccount()
            switch mutation {
            case let .approve(identity, _, role):
                try await workspace.requestApprove(spaceId: scope.spaceID, identity: identity,
                                                   permissions: nativeRole(role))
            case let .decline(identity):
                try await workspace.requestDecline(spaceId: scope.spaceID, identity: identity)
            case let .changeRole(identity, role):
                try await workspace.participantPermissionsChange(spaceId: scope.spaceID, identity: identity,
                                                                 permissions: nativeRole(role))
            case let .remove(identity):
                try await workspace.participantRemove(spaceId: scope.spaceID, identity: identity)
            case .revokeInvitation:
                try await workspace.revokeInvite(spaceId: scope.spaceID)
            }
            try checkAccount()
            return try await readSnapshot()
        }
    }

    private func readSnapshot() async throws -> PinkhaSharingSnapshot {
        try checkAccount()
        let (participants, space) = try readState()
        guard space.spaceView.targetSpaceId == scope.spaceID, space.spaceView.isActive,
              let me = space.participant, me.status == .active, me.permission != .noPermissions,
              participants.allSatisfy({ $0.spaceId == scope.spaceID }) else {
            throw PinkhaSharingError.staleContext
        }
        var invitations: [PinkhaSharingInvitation] = []
        do {
            let invite = try await workspace.getCurrentInvite(spaceId: scope.spaceID)
            if invite.hasLink { invitations = [try sharingInvitation(invite)] }
        } catch let error as Anytype_Rpc.Space.InviteGetCurrent.Response.Error where error.code == .noActiveInvite {
            invitations = []
        }
        try checkAccount()
        // Subscription objects and native read receipts remain real observations;
        // no optimistic role change is made after the RPC returns.
        let members = try participants.map { participant in
            try PinkhaSharingMember(id: participant.identity,
                name: participant.localName.isEmpty ? participant.globalName : participant.localName,
                role: sharedRole(participant.permission), status: sharedStatus(participant.status),
                requestID: participant.status == .joining ? participant.id : nil)
        }
        let owner = me.permission == .owner
        let moderator = owner || me.permission == .admin
        let editable = Set(participants.filter {
            $0.status == .active && $0.identity != me.identity && space.canChangeRole(target: $0)
        }.map(\.identity))
        let removable = Set(participants.filter {
            $0.status == .active && space.canRemove(target: $0)
        }.map(\.identity))
        let capabilities = try PinkhaSharingCapabilities(
            canCreateInvitation: owner && invitations.isEmpty,
            canRevokeInvitation: owner, canApproveRequests: moderator,
            grantableRoles: owner ? [.reader, .writer, .admin] : (moderator ? [.reader, .writer] : []),
            editableMemberIDs: editable, removableMemberIDs: removable)
        return try .init(scope: scope, currentIdentity: me.identity, members: members,
                         invitations: invitations, capabilities: capabilities)
    }

    private func checkAccount() throws {
        try Task.checkCancellation()
        guard accounts.account.id == scope.accountID else { throw PinkhaSharingError.staleContext }
    }

    private func sharingInvitation(_ invitation: SpaceInvite) throws -> PinkhaSharingInvitation {
        guard invitation.hasLink,
              let url = links.createUrl(link: .invite(cid: invitation.cid, key: invitation.fileKey)) else {
            throw PinkhaSharingError.invalidResponse
        }
        return try .init(id: invitation.cid, shareValue: url.absoluteString)
    }

    private func nativeRole(_ value: PinkhaSharingRole) throws -> ParticipantPermissions {
        switch value {
        case .reader: .reader
        case .writer: .writer
        case .admin: .admin
        default: throw PinkhaSharingError.permissionDenied
        }
    }

    private func sharedRole(_ value: ParticipantPermissions) -> PinkhaSharingRole {
        switch value {
        case .reader: .reader
        case .writer: .writer
        case .admin: .admin
        case .owner: .owner
        case .noPermissions, .UNRECOGNIZED: .none
        }
    }

    private func sharedStatus(_ value: ParticipantStatus) -> PinkhaSharingMemberStatus {
        switch value {
        case .joining: .joining
        case .active: .active
        case .removed: .removed
        case .declined: .declined
        case .removing: .removing
        case .canceled: .canceled
        case .UNRECOGNIZED: .unknown
        }
    }
}
