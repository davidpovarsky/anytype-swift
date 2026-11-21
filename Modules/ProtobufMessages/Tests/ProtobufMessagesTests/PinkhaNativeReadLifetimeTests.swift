#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation
import SwiftProtobuf
import XCTest
@testable import ProtobufMessages

@MainActor
final class PinkhaNativeReadLifetimeTests: XCTestCase {
    func testOnlySuccessfulOwnedAccountAndSpaceOpenCreateLease() throws {
        let owner = PinkhaNativeReadLifetime()
        XCTAssertThrowsError(try owner.lease(forOpenedSpaceID: "space"))
        let unowned = beginOpen(owner, "space")
        owner.completedInvocation(unowned, response: opened())
        XCTAssertThrowsError(try owner.lease(forOpenedSpaceID: "space"))
        establishAccount(owner)
        let failed = beginOpen(owner, "space")
        owner.failedInvocation(failed)
        owner.completedInvocation(failed, response: opened())
        XCTAssertThrowsError(try owner.lease(forOpenedSpaceID: "space"))
        owner.completedInvocation(beginOpen(owner, "space"), response: opened())
        let lease = try owner.lease(forOpenedSpaceID: "space")
        XCTAssertEqual(lease.accountID, "account")
        XCTAssertEqual(lease.spaceID, "space")
        try lease.validate()
    }

    func testRetirementPrecedesNativeCompletionAndNeverReactivatesOldLease() throws {
        let owner = PinkhaNativeReadLifetime()
        establishAccount(owner)
        owner.completedInvocation(beginOpen(owner, "space"), response: opened())
        let old = try owner.lease(forOpenedSpaceID: "space")
        let observer = RetirementObserver()
        try old.observeRetirement(observer)
        let stop = owner.beforeInvocation(name: "AccountStop", request: Anytype_Rpc.Account.Stop.Request())
        XCTAssertEqual(observer.count, 1)
        XCTAssertThrowsError(try old.validate())
        owner.failedInvocation(stop)
        owner.completedInvocation(stop, response: selected("other-account"))
        XCTAssertThrowsError(try owner.lease(forOpenedSpaceID: "space"))
        establishAccount(owner)
        owner.completedInvocation(beginOpen(owner, "space"), response: opened())
        let reopened = try owner.lease(forOpenedSpaceID: "space")
        XCTAssertNotEqual(old.generation, reopened.generation)
        XCTAssertThrowsError(try old.validate())
        XCTAssertEqual(observer.count, 1)
    }

    func testOverlappingAccountSelectionsNeverActivateInEitherCompletionOrder() throws {
        for newerCompletesFirst in [false, true] {
            let owner = PinkhaNativeReadLifetime()
            let older = beginAccount(owner), newer = beginAccount(owner)
            if newerCompletesFirst {
                owner.completedInvocation(newer, response: selected("newer"))
                owner.completedInvocation(older, response: selected("older"))
            } else {
                owner.completedInvocation(older, response: selected("older"))
                owner.completedInvocation(newer, response: selected("newer"))
            }
            owner.completedInvocation(beginOpen(owner, "space"), response: opened())
            XCTAssertThrowsError(try owner.lease(forOpenedSpaceID: "space"))
            establishAccount(owner, "independently-selected")
            owner.completedInvocation(beginOpen(owner, "space"), response: opened())
            XCTAssertEqual(try owner.lease(forOpenedSpaceID: "space").accountID, "independently-selected")
        }
    }

    func testAccountAndSpaceOverlapCannotBindRegardlessOfDispatchOrCompletionOrder() {
        for accountBeginsFirst in [false, true] {
            for accountCompletesFirst in [false, true] {
                let owner = PinkhaNativeReadLifetime()
                establishAccount(owner)
                let account: PinkhaNativeReadLifetime.Transition?
                let space: PinkhaNativeReadLifetime.Transition?
                if accountBeginsFirst {
                    account = beginAccount(owner); space = beginOpen(owner, "space")
                } else {
                    space = beginOpen(owner, "space"); account = beginAccount(owner)
                }
                if accountCompletesFirst {
                    owner.completedInvocation(account, response: selected("new-account"))
                    owner.completedInvocation(space, response: opened())
                } else {
                    owner.completedInvocation(space, response: opened())
                    owner.completedInvocation(account, response: selected("new-account"))
                }
                owner.completedInvocation(beginOpen(owner, "space"), response: opened())
                XCTAssertThrowsError(try owner.lease(forOpenedSpaceID: "space"))
            }
        }
    }

    func testOverlappingSameSpaceOpensNeverActivateInEitherCompletionOrder() throws {
        for newerCompletesFirst in [false, true] {
            let owner = PinkhaNativeReadLifetime()
            establishAccount(owner)
            let older = beginOpen(owner, "space"), newer = beginOpen(owner, "space")
            if newerCompletesFirst {
                owner.completedInvocation(newer, response: opened())
                owner.completedInvocation(older, response: opened())
            } else {
                owner.completedInvocation(older, response: opened())
                owner.completedInvocation(newer, response: opened())
            }
            XCTAssertThrowsError(try owner.lease(forOpenedSpaceID: "space"))
            owner.completedInvocation(beginOpen(owner, "space"), response: opened())
            try owner.lease(forOpenedSpaceID: "space").validate()
        }
    }

    func testActualSpaceClosureAndWorkspaceSelectionFencePendingOpen() {
        for closure in ["SpaceDelete", "SpaceJoinCancel", "WorkspaceSelect"] {
            let owner = PinkhaNativeReadLifetime()
            establishAccount(owner)
            let pending = beginOpen(owner, "space")
            let close: PinkhaNativeReadLifetime.Transition?
            switch closure {
            case "SpaceDelete": close = owner.beforeInvocation(name: closure,
                request: Anytype_Rpc.Space.Delete.Request.with { $0.spaceID = "space" })
            case "SpaceJoinCancel": close = owner.beforeInvocation(name: closure,
                request: Anytype_Rpc.Space.JoinCancel.Request.with { $0.spaceID = "space" })
            default: close = owner.beforeInvocation(name: closure, request: Anytype_Rpc.Workspace.Select.Request())
            }
            owner.failedInvocation(close)
            owner.completedInvocation(pending, response: opened())
            XCTAssertThrowsError(try owner.lease(forOpenedSpaceID: "space"))
        }
    }

    func testIndependentSpacesStayIndependentInsideOneVerifiedAccount() throws {
        let owner = PinkhaNativeReadLifetime()
        establishAccount(owner)
        let first = beginOpen(owner, "first"), second = beginOpen(owner, "second")
        owner.completedInvocation(second, response: opened())
        owner.completedInvocation(first, response: opened())
        let firstLease = try owner.lease(forOpenedSpaceID: "first")
        let secondLease = try owner.lease(forOpenedSpaceID: "second")
        let close = owner.beforeInvocation(name: "SpaceDelete",
            request: Anytype_Rpc.Space.Delete.Request.with { $0.spaceID = "first" })
        XCTAssertThrowsError(try firstLease.validate())
        try secondLease.validate()
        owner.failedInvocation(close)
        XCTAssertThrowsError(try owner.lease(forOpenedSpaceID: "first"))
        XCTAssertTrue(try owner.lease(forOpenedSpaceID: "second") === secondLease)
    }

    func testEveryExistingAccountTransitionRetiresBeforeDispatch() throws {
        let names = ["InitialSetParameters", "AppShutdown", "WalletCreate", "WalletRecover", "WalletConvert",
                     "AccountCreate", "AccountSelect", "AccountStop", "AccountRecover", "AccountDelete",
                     "AccountMigrate", "AccountMigrateCancel", "AccountMove", "AccountRecoverFromLegacyExport",
                     "AccountChangeNetworkConfigAndRestart"]
        for name in names {
            let owner = PinkhaNativeReadLifetime()
            establishAccount(owner)
            owner.completedInvocation(beginOpen(owner, "space"), response: opened())
            let lease = try owner.lease(forOpenedSpaceID: "space")
            let transition = owner.beforeInvocation(name: name, request: Anytype_Rpc.Account.Stop.Request())
            XCTAssertNotNil(transition, name)
            XCTAssertThrowsError(try lease.validate(), name)
            owner.failedInvocation(transition)
            XCTAssertThrowsError(try owner.lease(forOpenedSpaceID: "space"), name)
        }
    }

    func testByteResponseLimitIsDistinctFromMalformedEmptyResponse() throws {
        XCTAssertThrowsError(try PinkhaAuthorizedReadByteBridge.checkedResponse(Data())) {
            XCTAssertEqual($0 as? PinkhaNativeReadLifetimeError, .invalidByteBoundary)
        }
        XCTAssertThrowsError(try PinkhaAuthorizedReadByteBridge.checkedResponse(Data(count: 4 * 1024 * 1024 + 1))) {
            XCTAssertEqual($0 as? PinkhaNativeReadLifetimeError, .responseTooLarge)
        }
        let exact = Data([0x08, 0x01])
        XCTAssertEqual(try PinkhaAuthorizedReadByteBridge.checkedResponse(exact), exact)
    }

    private func beginAccount(_ owner: PinkhaNativeReadLifetime) -> PinkhaNativeReadLifetime.Transition? {
        owner.beforeInvocation(name: "AccountSelect", request: Anytype_Rpc.Account.Select.Request())
    }

    private func establishAccount(_ owner: PinkhaNativeReadLifetime, _ id: String = "account") {
        owner.completedInvocation(beginAccount(owner), response: selected(id))
    }

    private func beginOpen(_ owner: PinkhaNativeReadLifetime, _ id: String) -> PinkhaNativeReadLifetime.Transition? {
        owner.beforeInvocation(name: "WorkspaceOpen", request: Anytype_Rpc.Workspace.Open.Request.with { $0.spaceID = id })
    }

    private func selected(_ id: String) -> Anytype_Rpc.Account.Select.Response {
        .with { $0.account = .with { $0.id = id; $0.status.statusType = .active } }
    }

    private func opened() -> Anytype_Rpc.Workspace.Open.Response {
        .with { $0.info = .with { $0.workspaceObjectID = "native-workspace-object" } }
    }
}

@MainActor
private final class RetirementObserver: PinkhaNativeReadLeaseObserver {
    var count = 0
    func nativeReadLeaseDidRetire() { count += 1 }
}
#endif
