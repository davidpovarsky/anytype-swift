#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation
import SwiftProtobuf

public enum PinkhaNativeReadLifetimeError: Error, Equatable, Sendable {
    case noCurrentOwnedScope
    case retired
    case invalidByteBoundary
    case responseTooLarge
}

@MainActor
public protocol PinkhaNativeReadLeaseObserver: AnyObject, Sendable {
    func nativeReadLeaseDidRetire()
}

/// Created only after a successful native account response and Workspace.Open
/// in the same owned account lifetime. Callers cannot manufacture this lease.
@MainActor
public final class PinkhaNativeReadLease {
    public nonisolated let accountID: String
    public nonisolated let spaceID: String
    public nonisolated let generation: UUID
    private var active = true
    private var observers: [WeakObserver] = []

    fileprivate init(accountID: String, spaceID: String) {
        self.accountID = accountID; self.spaceID = spaceID; self.generation = UUID()
    }

    public func validate() throws {
        guard active else { throw PinkhaNativeReadLifetimeError.retired }
    }

    public func observeRetirement(_ observer: any PinkhaNativeReadLeaseObserver) throws {
        try validate()
        observers.removeAll { $0.value == nil }
        observers.append(WeakObserver(observer))
    }

    fileprivate func retire() {
        guard active else { return }
        active = false
        let old = observers; observers.removeAll()
        for observer in old { observer.value?.nativeReadLeaseDidRetire() }
    }

    private final class WeakObserver {
        weak var value: (any PinkhaNativeReadLeaseObserver)?
        init(_ value: any PinkhaNativeReadLeaseObserver) { self.value = value }
    }
}

/// Candidate-only observer of the existing generated Invocation boundary.
/// Native calls keep their original scheduling and cancellation behavior.
/// Revisions fence late completions; overlapping transitions fail closed rather
/// than assuming their dispatch/completion order identifies the current owner.
@MainActor
public final class PinkhaNativeReadLifetime {
    public static let shared = PinkhaNativeReadLifetime()

    enum Effect: Sendable {
        case account
        case openSpace(String)
        case closeSpace(String)
        case selectWorkspace
    }

    struct Transition: Sendable {
        let id: UUID
        let revision: UInt64
        let accountRevision: UInt64
        let workspaceRevision: UInt64
        let ownedAccountID: String?
        let activationEligible: Bool
        let effect: Effect
    }

    private var nextRevision: UInt64 = 0
    private var accountRevision: UInt64 = 0
    private var workspaceRevision: UInt64 = 0
    private var accountID: String?
    private var accountCalls: Set<UUID> = []
    private var workspaceCalls: Set<UUID> = []
    private var spaceRevisions: [Data: UInt64] = [:]
    private var spaceCalls: [Data: Set<UUID>] = [:]
    private var leases: [Data: PinkhaNativeReadLease] = [:]

    // Internal so focused tests can own isolated registries. Product callers
    // receive the singleton and its verified leases, never activation setters.
    init() {}

    public func lease(forOpenedSpaceID spaceID: String) throws -> PinkhaNativeReadLease {
        guard accountCalls.isEmpty, workspaceCalls.isEmpty, accountID != nil,
              let lease = leases[Data(spaceID.utf8)], spaceCalls[Data(spaceID.utf8)]?.isEmpty != false else {
            throw PinkhaNativeReadLifetimeError.noCurrentOwnedScope
        }
        try lease.validate()
        return lease
    }

    func beforeInvocation<Request: Message & Sendable>(name: String, request: Request) -> Transition? {
        let effect: Effect
        switch name {
        case "InitialSetParameters", "AppShutdown", "WalletCreate", "WalletRecover", "WalletConvert",
             "AccountCreate", "AccountSelect", "AccountStop", "AccountRecover", "AccountDelete",
             "AccountMigrate", "AccountMigrateCancel", "AccountMove", "AccountRecoverFromLegacyExport",
             "AccountChangeNetworkConfigAndRestart":
            effect = .account
        case "WorkspaceOpen":
            guard let value = request as? Anytype_Rpc.Workspace.Open.Request else { return nil }
            effect = .openSpace(value.spaceID)
        case "SpaceDelete":
            guard let value = request as? Anytype_Rpc.Space.Delete.Request else { return nil }
            effect = .closeSpace(value.spaceID)
        case "SpaceJoinCancel":
            guard let value = request as? Anytype_Rpc.Space.JoinCancel.Request else { return nil }
            effect = .closeSpace(value.spaceID)
        case "WorkspaceSelect": effect = .selectWorkspace
        default: return nil
        }
        precondition(nextRevision < UInt64.max, "Native lifetime revision exhausted")
        nextRevision += 1
        let revision = nextRevision, id = UUID()
        let ownedAccountID = accountCalls.isEmpty && workspaceCalls.isEmpty ? accountID : nil
        let activationEligible: Bool
        // Eligibility is fixed before the native call starts. Draining older
        // calls later cannot prove the order of native mutations: continuations
        // can resume in a different order than the engine changed its owner.
        switch effect {
        case .account:
            activationEligible = accountCalls.isEmpty && workspaceCalls.isEmpty && spaceCalls.isEmpty
            accountRevision = revision; accountID = nil; accountCalls.insert(id)
            retireAllSpaces()
        case .openSpace(let spaceID):
            let key = Data(spaceID.utf8)
            activationEligible = ownedAccountID != nil && spaceCalls[key]?.isEmpty != false
            spaceRevisions[key] = revision
            spaceCalls[key, default: []].insert(id)
            leases.removeValue(forKey: key)?.retire()
        case .closeSpace(let spaceID):
            activationEligible = false
            let key = Data(spaceID.utf8)
            spaceRevisions[key] = revision
            spaceCalls[key, default: []].insert(id)
            leases.removeValue(forKey: key)?.retire()
        case .selectWorkspace:
            activationEligible = false
            workspaceRevision = revision; workspaceCalls.insert(id)
            retireAllSpaces()
        }
        return .init(id: id, revision: revision, accountRevision: accountRevision,
                     workspaceRevision: workspaceRevision, ownedAccountID: ownedAccountID,
                     activationEligible: activationEligible, effect: effect)
    }

    func failedInvocation(_ transition: Transition?) {
        guard let transition else { return }
        _ = finishTracking(transition)
        // Retirement is permanent, even when native teardown/open fails.
    }

    func completedInvocation<Response: Message & ResultWithError & Sendable>(_ transition: Transition?, response: Response) {
        guard let transition else { return }
        guard finishTracking(transition) else { return }
        guard response.error.isNull else { return }
        switch transition.effect {
        case .account:
            guard transition.activationEligible, transition.revision == accountRevision,
                  transition.revision == nextRevision, accountCalls.isEmpty,
                  workspaceCalls.isEmpty, spaceCalls.isEmpty else { return }
            let nativeAccount: Anytype_Model_Account?
            if let result = response as? Anytype_Rpc.Account.Create.Response, result.hasAccount {
                nativeAccount = result.account
            } else if let result = response as? Anytype_Rpc.Account.Select.Response, result.hasAccount {
                nativeAccount = result.account
            } else {
                // Recover/move/restart responses do not assert an owned account
                // identity. A later actual Account.Select must establish it.
                nativeAccount = nil
            }
            guard let nativeAccount, Self.validID(nativeAccount.id),
                  [.active, .pendingDeletion].contains(nativeAccount.status.statusType) else { return }
            accountID = nativeAccount.id
        case .openSpace(let spaceID):
            let key = Data(spaceID.utf8)
            guard transition.activationEligible, transition.accountRevision == accountRevision,
                  transition.workspaceRevision == workspaceRevision,
                  spaceRevisions[key] == transition.revision, accountCalls.isEmpty, workspaceCalls.isEmpty,
                  spaceCalls[key]?.isEmpty != false, let accountID, Self.validID(spaceID),
                  let ownedAccountID = transition.ownedAccountID, ownedAccountID.utf8.elementsEqual(accountID.utf8),
                  let opened = response as? Anytype_Rpc.Workspace.Open.Response, opened.hasInfo else { return }
            // Workspace.Open's native schema does not echo SpaceID. The owned
            // immutable request, successful typed response and unchanged native
            // account lifetime jointly bind this exact accepted SpaceID.
            leases[key] = PinkhaNativeReadLease(accountID: accountID, spaceID: spaceID)
        case .closeSpace, .selectWorkspace:
            break
        }
    }

    private func finishTracking(_ transition: Transition) -> Bool {
        switch transition.effect {
        case .account: return accountCalls.remove(transition.id) != nil
        case .selectWorkspace: return workspaceCalls.remove(transition.id) != nil
        case .openSpace(let spaceID), .closeSpace(let spaceID):
            let key = Data(spaceID.utf8)
            let removed = spaceCalls[key]?.remove(transition.id) != nil
            if spaceCalls[key]?.isEmpty == true { spaceCalls.removeValue(forKey: key) }
            return removed
        }
    }

    private func retireAllSpaces() {
        let old = Array(leases.values)
        leases.removeAll()
        for lease in old { lease.retire() }
    }

    private static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1024 && !value.utf8.contains(0)
    }
}
#endif
