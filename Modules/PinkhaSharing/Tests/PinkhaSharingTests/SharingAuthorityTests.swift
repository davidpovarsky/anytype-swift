import XCTest
@testable import PinkhaSharing

final class SharingAuthorityTests: XCTestCase, @unchecked Sendable {
    private func scope(_ engine: PinkhaSharingEngine = .heart, account: String = "same-account") throws -> PinkhaSharingScope {
        try .init(engine: engine, accountID: account, spaceID: "same-space")
    }

    private func snapshot() throws -> PinkhaSharingSnapshot {
        let members: [PinkhaSharingMember] = [
            try .init(id: "owner", name: "Owner", role: .owner, status: .active),
            try .init(id: "writer", name: "Writer", role: .writer, status: .active),
            try .init(id: "pending", name: "Pending", role: .none, status: .joining, requestID: "new-request")
        ]
        return try .init(scope: scope(), currentIdentity: "owner", members: members,
                         invitations: [try .init(id: "invite", shareValue: "private-share-token")],
                         capabilities: .init(canCreateInvitation: false, canRevokeInvitation: true,
                            canApproveRequests: true, grantableRoles: [.reader, .writer, .admin],
                            editableMemberIDs: ["writer"], removableMemberIDs: ["writer"]))
    }

    func testMutationRequiresCurrentRequestAndExplicitRoleAuthority() throws {
        let current = try snapshot()
        try PinkhaSharingMutation.approve(identity: "pending", requestID: "new-request", role: .reader).validate(in: current)
        XCTAssertThrowsError(try PinkhaSharingMutation.approve(identity: "pending", requestID: "old-request", role: .reader).validate(in: current))
        XCTAssertThrowsError(try PinkhaSharingMutation.approve(identity: "writer", requestID: "new-request", role: .reader).validate(in: current))
        XCTAssertThrowsError(try PinkhaSharingMutation.changeRole(identity: "writer", role: .owner).validate(in: current))
        XCTAssertThrowsError(try PinkhaSharingMutation.remove(identity: "owner").validate(in: current))
        XCTAssertThrowsError(try PinkhaSharingMutation.revokeInvitation(id: "foreign").validate(in: current))
        try PinkhaSharingMutation.changeRole(identity: "writer", role: .reader).validate(in: current)
        try PinkhaSharingMutation.remove(identity: "writer").validate(in: current)
    }

    func testSnapshotRejectsDuplicateMembersAndSelfEditing() throws {
        let current = try snapshot()
        XCTAssertThrowsError(try PinkhaSharingSnapshot(scope: current.scope, currentIdentity: current.currentIdentity,
            members: current.members + [current.members[0]], invitations: current.invitations, capabilities: current.capabilities))
        let invalid = try PinkhaSharingCapabilities(canCreateInvitation: true, canRevokeInvitation: true,
            canApproveRequests: true, grantableRoles: [.writer], editableMemberIDs: ["owner"], removableMemberIDs: [])
        XCTAssertThrowsError(try PinkhaSharingSnapshot(scope: current.scope, currentIdentity: "owner",
            members: current.members, invitations: current.invitations, capabilities: invalid))
    }

    func testInvitationDescriptionsDoNotExposeShareCapability() throws {
        let invitation = try PinkhaSharingInvitation(id: "invitation", shareValue: "private-share-token")
        XCTAssertFalse(String(describing: invitation).contains("private-share-token"))
        XCTAssertFalse(String(reflecting: invitation).contains("private-share-token"))
    }

    func testAccountDrainRejectsStaleCompletionAndKeepsOtherEngineActive() async throws {
        let owner = PinkhaSharingAccountOwner()
        let heart = try scope(), any = try scope(.any)
        try await owner.didOpen(engine: .heart, accountID: heart.accountID)
        try await owner.didOpen(engine: .any, accountID: any.accountID)
        let entered = Signal(), canceled = Signal(), release = Signal()
        let work = Task {
            try await owner.perform(scope: heart) {
                await entered.signal()
                return await withTaskCancellationHandler {
                    await release.wait()
                    return "stale value"
                } onCancel: {
                    Task { await canceled.signal() }
                }
            }
        }
        await entered.wait()
        let closing = Task { await owner.closeAndDrain(engine: .heart) }
        await canceled.wait()
        do {
            _ = try await owner.perform(scope: heart) { "must not run" }
            XCTFail("Closed Heart account accepted a new operation")
        } catch { XCTAssertEqual(error as? PinkhaSharingError, .staleContext) }
        let other = try await owner.perform(scope: any) { "Any remains active" }
        XCTAssertEqual(other, "Any remains active")
        await release.signal()
        do { _ = try await work.value; XCTFail("Stale completion escaped the account fence") }
        catch { XCTAssertTrue(error is CancellationError || error as? PinkhaSharingError == .staleContext) }
        await closing.value
        try await owner.didOpen(engine: .heart, accountID: "replacement")
        do {
            _ = try await owner.perform(scope: heart) { "must not run" }
            XCTFail("Old account reused the reopened engine")
        } catch { XCTAssertEqual(error as? PinkhaSharingError, .staleContext) }
    }
}

private actor Signal {
    private var ready = false
    private var waiting: [CheckedContinuation<Void, Never>] = []
    func wait() async {
        if ready { return }
        await withCheckedContinuation { waiting.append($0) }
    }
    func signal() {
        ready = true
        let callbacks = waiting
        waiting.removeAll()
        for callback in callbacks { callback.resume() }
    }
}

// Per-member permissions are a source-level projection; native authorization remains final.
extension SharingAuthorityTests {
    func testPerMemberRoleOptionsPreserveLegacyAndDenyMissingTargets() throws {
        let legacy = try snapshot()
        XCTAssertNil(legacy.capabilities.memberRoleOptions)
        XCTAssertEqual(legacy.capabilities.rolesForMemberChange("writer"), legacy.capabilities.grantableRoles)
        try PinkhaSharingMutation.changeRole(identity: "writer", role: .reader).validate(in: legacy)
        XCTAssertTrue(legacy.capabilities.rolesForMemberChange("owner").isEmpty)

        let empty = try memberRoleSnapshot(options: [:])
        XCTAssertTrue(empty.capabilities.rolesForMemberChange("reader").isEmpty)
        XCTAssertThrowsError(try PinkhaSharingMutation.changeRole(identity: "reader", role: .writer).validate(in: empty)) {
            XCTAssertEqual($0 as? PinkhaSharingError, .permissionDenied)
        }
        let partial = try memberRoleSnapshot(options: ["reader": [.guest, .writer]])
        try PinkhaSharingMutation.changeRole(identity: "reader", role: .guest).validate(in: partial)
        XCTAssertTrue(partial.capabilities.rolesForMemberChange("writer").isEmpty)
        XCTAssertThrowsError(try PinkhaSharingMutation.changeRole(identity: "writer", role: .reader).validate(in: partial)) {
            XCTAssertEqual($0 as? PinkhaSharingError, .permissionDenied)
        }
    }

    func testPerMemberRoleChangesStaySeparateFromApprovalAndRemoval() throws {
        let current = try memberRoleSnapshot(options: [
            "reader": [.guest, .reader, .writer, .admin],
            "writer": [.reader, .writer, .admin],
            "admin": [.reader, .writer, .admin]
        ])
        try PinkhaSharingMutation.changeRole(identity: "reader", role: .guest).validate(in: current)
        try PinkhaSharingMutation.changeRole(identity: "writer", role: .admin).validate(in: current)
        XCTAssertThrowsError(try PinkhaSharingMutation.changeRole(identity: "writer", role: .guest).validate(in: current))
        XCTAssertThrowsError(try PinkhaSharingMutation.changeRole(identity: "guest", role: .reader).validate(in: current))
        XCTAssertTrue(current.capabilities.rolesForMemberChange("guest").isEmpty)
        try PinkhaSharingMutation.remove(identity: "guest").validate(in: current)
        XCTAssertThrowsError(try PinkhaSharingMutation.remove(identity: "owner").validate(in: current))
        try PinkhaSharingMutation.approve(identity: "pending", requestID: "current-request", role: .admin).validate(in: current)
        XCTAssertThrowsError(try PinkhaSharingMutation.approve(identity: "pending", requestID: "current-request", role: .guest).validate(in: current))
        XCTAssertThrowsError(try PinkhaSharingMutation.approve(identity: "pending", requestID: "old-request", role: .reader).validate(in: current))

        // The same confirmed target may no longer be a Reader at dispatch.
        let refreshed = try memberRoleSnapshot(options: ["reader": [.reader, .writer, .admin]], readerRole: .writer)
        XCTAssertThrowsError(try PinkhaSharingMutation.changeRole(identity: "reader", role: .guest).validate(in: refreshed)) {
            XCTAssertEqual($0 as? PinkhaSharingError, .permissionDenied)
        }
    }

    func testPerMemberRoleOptionsRejectMalformedEntries() throws {
        let malformed: [(String, [String: [PinkhaSharingRole]])] = [
            ("duplicate role", ["reader": [.writer, .writer]]),
            ("owner grant", ["reader": [.owner]]),
            ("none grant", ["reader": [.none]]),
            ("foreign member", ["foreign": [.writer]]),
            ("noneditable guest", ["guest": [.reader]]),
            ("self member", ["owner": [.writer]])
        ]
        for (label, options) in malformed {
            XCTAssertThrowsError(try memberRoleSnapshot(options: options), label) {
                XCTAssertEqual($0 as? PinkhaSharingError, .invalidResponse, label)
            }
        }
        let explicitlyClosed = try memberRoleSnapshot(options: ["reader": []])
        XCTAssertTrue(explicitlyClosed.capabilities.rolesForMemberChange("reader").isEmpty)
        XCTAssertThrowsError(try PinkhaSharingMutation.changeRole(identity: "reader", role: .writer).validate(in: explicitlyClosed))
    }

    private func memberRoleSnapshot(
        options: [String: [PinkhaSharingRole]]?, readerRole: PinkhaSharingRole = .reader
    ) throws -> PinkhaSharingSnapshot {
        let members: [PinkhaSharingMember] = [
            try .init(id: "owner", name: "Owner", role: .owner, status: .active),
            try .init(id: "reader", name: "Reader", role: readerRole, status: .active),
            try .init(id: "writer", name: "Writer", role: .writer, status: .active),
            try .init(id: "admin", name: "Admin", role: .admin, status: .active),
            try .init(id: "guest", name: "Guest", role: .guest, status: .active),
            try .init(id: "pending", name: "Pending", role: .none, status: .joining, requestID: "current-request")
        ]
        return try .init(scope: scope(.any), currentIdentity: "owner", members: members, invitations: [],
            capabilities: .init(canCreateInvitation: true, canRevokeInvitation: true,
                canApproveRequests: true, grantableRoles: [.reader, .writer, .admin],
                editableMemberIDs: ["reader", "writer", "admin"],
                removableMemberIDs: ["reader", "writer", "admin", "guest"], memberRoleOptions: options))
    }
}
