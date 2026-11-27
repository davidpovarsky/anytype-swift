import Foundation
import XCTest
@testable import PinkhaSharing

@MainActor
final class SharingPresentationTests: XCTestCase, @unchecked Sendable {
    func testRefreshRejectsForeignEngineAccountAndSpace() async throws {
        for engine in [PinkhaSharingEngine.heart, .any] {
            let expected = try scope(engine)
            let foreign = [
                try scope(engine == .heart ? .any : .heart),
                try scope(engine, account: "another-account"),
                try scope(engine, space: "another-space")
            ]
            for mismatched in foreign {
                try await withModel(expected: expected) { model, service in
                    XCTAssertNotNil(model.state?.invitations.first?.shareValue)
                    service.nextSnapshot = try self.snapshot(mismatched)
                    await model.refresh()
                    XCTAssertNil(model.state, "A rejected authority read must clear old invitations and controls.")
                    XCTAssertNotNil(model.problem)
                    XCTAssertFalse(model.busy)
                    XCTAssertEqual(service.writes, 0)
                }
            }
        }
    }

    func testMutationReadbackRejectsForeignScopeWithoutRepeatingWrite() async throws {
        try await withModel { model, service in
            service.mutationSnapshot = try self.snapshot(self.scope(.heart, space: "foreign-space"))
            model.apply(.changeRole(identity: "member", role: .reader))
            try await self.until { !model.busy }
            XCTAssertEqual(service.writes, 1)
            XCTAssertNil(model.state, "An unconfirmed mutation must not retain previous authority.")
            XCTAssertNotNil(model.problem)
            model.apply(.changeRole(identity: "member", role: .reader))
            try await self.until { !model.busy }
            XCTAssertEqual(service.writes, 1, "Readback failure must not automatically retry or leave stale grant controls.")
        }
    }

    func testInvitationReadbackRejectsForeignScopeWithoutRetry() async throws {
        try await withModel { model, service in
            service.nextSnapshot = try self.snapshot(self.scope(.heart, account: "foreign-account"))
            model.apply(nil)
            try await self.until { !model.busy }
            XCTAssertEqual(service.invitationsCreated, 1)
            XCTAssertNil(model.state)
            XCTAssertNotNil(model.problem)
            model.apply(nil)
            try await self.until { !model.busy }
            XCTAssertEqual(service.invitationsCreated, 1, "An uncertain invitation must not be recreated from stale UI state.")
        }
    }

    func testCurrentScopeReadbackKeepsUpdatedMembersVisible() async throws {
        try await withModel { model, service in
            service.mutationSnapshot = try self.snapshot(service.scope, memberRole: .reader)
            model.apply(.changeRole(identity: "member", role: .reader))
            try await self.until { !model.busy }
            XCTAssertEqual(service.writes, 1)
            XCTAssertEqual(model.state?.members.first(where: { $0.id == "member" })?.role, .reader)
            XCTAssertNil(model.problem)
        }
    }

    func testOldGenerationCannotClearReopenedSharingState() async throws {
        let expected = try scope()
        let service = PresentationService(scope: expected, snapshot: try snapshot(expected))
        let model = PinkhaSharingViewModel(service: service)
        let first = Task { await model.observe() }
        do {
            try await until { model.state != nil && !model.busy }
            service.suspendNextSnapshot = true
            let delayed = Task { await model.refresh() }
            try await until { service.pendingSnapshot != nil }
            model.close()
            first.cancel()
            await first.value
            service.nextSnapshot = try snapshot(expected, memberName: "Reopened member")
            let reopened = Task { await model.observe() }
            do {
                try await until { model.state?.members.contains(where: { $0.name == "Reopened member" }) == true && !model.busy }
                service.finishPending(try snapshot(scope(.any)))
                await delayed.value
                XCTAssertEqual(model.state?.members.first(where: { $0.id == "member" })?.name, "Reopened member")
                XCTAssertNil(model.problem)
            } catch {
                service.cancelPending()
                await delayed.value
                reopened.cancel()
                model.close()
                await reopened.value
                throw error
            }
            reopened.cancel()
            model.close()
            await reopened.value
        } catch {
            service.cancelPending()
            first.cancel()
            model.close()
            await first.value
            throw error
        }
    }

    private func scope(_ engine: PinkhaSharingEngine = .heart,
                       account: String = "account", space: String = "space") throws -> PinkhaSharingScope {
        try .init(engine: engine, accountID: account, spaceID: space)
    }

    private func snapshot(_ scope: PinkhaSharingScope, memberRole: PinkhaSharingRole = .writer,
                          memberName: String = "Member") throws -> PinkhaSharingSnapshot {
        try .init(scope: scope, currentIdentity: "owner", members: [
            .init(id: "owner", name: "Owner", role: .owner, status: .active),
            .init(id: "member", name: memberName, role: memberRole, status: .active)
        ], invitations: [.init(id: "invitation", shareValue: "synthetic-private-invitation")],
        capabilities: .init(canCreateInvitation: true, canRevokeInvitation: true,
                            canApproveRequests: true, grantableRoles: [.reader, .writer],
                            editableMemberIDs: ["member"], removableMemberIDs: ["member"]))
    }

    private func withModel(expected: PinkhaSharingScope? = nil,
                           _ body: @MainActor (PinkhaSharingViewModel, PresentationService) async throws -> Void) async throws {
        let identity = try expected ?? scope()
        let service = PresentationService(scope: identity, snapshot: try snapshot(identity))
        let model = PinkhaSharingViewModel(service: service)
        let observation = Task { await model.observe() }
        do {
            try await until { model.state != nil && !model.busy }
            try await body(model, service)
        } catch {
            observation.cancel()
            model.close()
            await observation.value
            throw error
        }
        observation.cancel()
        model.close()
        await observation.value
    }

    private enum ObservationTimeout: Error { case stateNotPublished }

    private func until(_ condition: @MainActor () -> Bool) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(3))
        while !condition() {
            guard clock.now < deadline else { throw ObservationTimeout.stateNotPublished }
            await Task.yield()
        }
    }
}

@MainActor
private final class PresentationService: PinkhaSpaceSharingService {
    let scope: PinkhaSharingScope
    var nextSnapshot: PinkhaSharingSnapshot
    var mutationSnapshot: PinkhaSharingSnapshot
    private(set) var writes = 0
    private(set) var invitationsCreated = 0
    var suspendNextSnapshot = false
    private(set) var pendingSnapshot: CheckedContinuation<PinkhaSharingSnapshot, Error>?

    init(scope: PinkhaSharingScope, snapshot: PinkhaSharingSnapshot) {
        self.scope = scope
        nextSnapshot = snapshot
        mutationSnapshot = snapshot
    }

    func snapshot() async throws -> PinkhaSharingSnapshot {
        if suspendNextSnapshot {
            suspendNextSnapshot = false
            return try await withCheckedThrowingContinuation { pendingSnapshot = $0 }
        }
        return nextSnapshot
    }

    func createInvitation() async throws -> PinkhaSharingInvitation {
        invitationsCreated += 1
        return try .init(id: "created-invitation", shareValue: "synthetic-private-created-invitation")
    }

    func apply(_ mutation: PinkhaSharingMutation) async throws -> PinkhaSharingSnapshot {
        writes += 1
        return mutationSnapshot
    }

    func finishPending(_ result: PinkhaSharingSnapshot) {
        let continuation = pendingSnapshot
        pendingSnapshot = nil
        continuation?.resume(returning: result)
    }

    func cancelPending() {
        let continuation = pendingSnapshot
        pendingSnapshot = nil
        continuation?.resume(throwing: CancellationError())
    }
}
