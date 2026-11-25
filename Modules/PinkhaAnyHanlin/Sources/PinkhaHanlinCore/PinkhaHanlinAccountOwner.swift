import Foundation
import HanlinHostContracts

/// Persistence ownership uses the engine host namespace without altering a native account ID.
public enum PinkhaHanlinEngineNamespace {
    public static let heart = "anytype"
    public static var any: String {
        #if PINKHA_DUAL_ENGINE_RUNTIME
        return "anytype-any"
        #else
        // Preserve the separate NativeApp's existing private metadata namespace.
        return "anytype"
        #endif
    }
    public static func supports(_ app: String) -> Bool {
        app.utf8.elementsEqual(heart.utf8) || app.utf8.elementsEqual("anytype-any".utf8)
    }
}

/// Minimal real presentation lifetime contract shared by Heart and Any hosts.
@MainActor
public protocol PinkhaHanlinOwnedPresentation: AnyObject, Sendable {
    var session: HanlinHostSession { get }
    func invalidate()
    func revokeAndDrain() async
}

/// One implementation owns journals and revocation for both engines. A native account may
/// exist in both engines; closing one host must not revoke or erase the other's metadata.
@MainActor
public final class PinkhaHanlinAccountOwner {
    public static let shared = PinkhaHanlinAccountOwner()

    private struct AccountKey: Hashable {
        let app: Data
        let account: Data
        init(app: String, account: String) {
            self.app = Data(app.utf8); self.account = Data(account.utf8)
        }
        init(_ namespace: HanlinConversationNamespace) {
            self.init(app: namespace.app, account: namespace.account)
        }
    }
    private struct Presentation {
        weak var value: (any PinkhaHanlinOwnedPresentation)?
        let account: AccountKey
    }
    private struct Opening {
        let account: AccountKey
        let task: Task<PinkhaHanlinWriteJournal, Error>
    }
    private var presentations: [UUID: Presentation] = [:]
    private var journals: [String: Opening] = [:]
    private var closedAccounts = Set<AccountKey>()
    private var removingAccounts = Set<AccountKey>()
    private var drainingAccounts = Set<AccountKey>()
    private var inactiveEngines = Set<Data>()
    private var drainingEngines = Set<Data>()

    public func isAvailable(account: String, app: String = PinkhaHanlinEngineNamespace.heart) -> Bool {
        PinkhaHanlinEngineNamespace.supports(app) && !inactiveEngines.contains(Data(app.utf8)) &&
            !closedAccounts.contains(AccountKey(app: app, account: account))
    }

    public func isAvailable(namespace: HanlinConversationNamespace) -> Bool {
        isAvailable(account: namespace.account, app: namespace.app)
    }

    public func register(_ presentation: any PinkhaHanlinOwnedPresentation) throws {
        let namespace = presentation.session.context.namespace
        guard isAvailable(namespace: namespace) else { throw HanlinHostError.staleContext }
        presentations = presentations.filter { $0.value.value != nil }
        presentations[presentation.session.id] = .init(value: presentation, account: AccountKey(namespace))
    }

    public func unregister(_ id: UUID) { presentations[id] = nil }

    public func owns(_ presentation: any PinkhaHanlinOwnedPresentation) -> Bool {
        presentations[presentation.session.id]?.value === presentation
    }

    public func journal(for namespace: HanlinConversationNamespace) async throws -> PinkhaHanlinWriteJournal {
        guard isAvailable(namespace: namespace) else { throw HanlinHostError.staleContext }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let key = PinkhaHanlinCreatePagePlan.digest(try encoder.encode(namespace))
        let opening: Opening
        if let existing = journals[key] {
            opening = existing
        } else {
            let task = Task { try await PinkhaHanlinWriteJournal.open(namespace: namespace) }
            opening = .init(account: AccountKey(namespace), task: task)
            journals[key] = opening
        }
        let journal = try await opening.task.value
        guard isAvailable(namespace: namespace) else { throw HanlinHostError.staleContext }
        return journal
    }

    /// A hidden engine cannot admit a new AI presentation even if native
    /// authentication completes while the app is showing the other engine.
    public func deactivateEngine(_ app: String) async throws {
        guard PinkhaHanlinEngineNamespace.supports(app) else { throw HanlinHostError.staleContext }
        let key = Data(app.utf8)
        guard drainingEngines.insert(key).inserted else { throw HanlinHostError.staleContext }
        defer { drainingEngines.remove(key) }
        inactiveEngines.insert(key)
        let owned = presentations.values.filter { $0.account.app == key }.compactMap(\.value)
        for presentation in owned { presentation.invalidate() }
        for presentation in owned { await presentation.revokeAndDrain() }
    }

    public func activateEngine(_ app: String) throws {
        let key = Data(app.utf8)
        guard PinkhaHanlinEngineNamespace.supports(app), !drainingEngines.contains(key) else {
            throw HanlinHostError.staleContext
        }
        inactiveEngines.remove(key)
    }

    public func accountDidOpen(_ account: String, app: String = PinkhaHanlinEngineNamespace.heart) throws {
        let key = AccountKey(app: app, account: account)
        guard PinkhaHanlinEngineNamespace.supports(app), !removingAccounts.contains(key),
              !drainingAccounts.contains(key) else {
            throw HanlinHostError.staleContext
        }
        closedAccounts.remove(key)
    }

    /// Called before native logout/delete first suspends. Ordinary logout preserves all metadata.
    public func closeAccount(_ account: String, removeData: Bool,
                             app: String = PinkhaHanlinEngineNamespace.heart) async throws {
        guard !account.isEmpty else { return }
        guard PinkhaHanlinEngineNamespace.supports(app) else { throw HanlinHostError.staleContext }
        let key = AccountKey(app: app, account: account)
        guard drainingAccounts.insert(key).inserted else { throw HanlinHostError.staleContext }
        defer { drainingAccounts.remove(key) }
        closedAccounts.insert(key)
        let owned = presentations.values.filter { $0.account == key }.compactMap(\.value)
        // Revoke all presentations before the first suspension, then await each
        // concrete SDK/native owner before an engine or account may be replaced.
        for presentation in owned { presentation.invalidate() }
        for presentation in owned { await presentation.revokeAndDrain() }
        guard removeData else { return }
        guard removingAccounts.insert(key).inserted else { throw HanlinHostError.staleContext }
        defer { removingAccounts.remove(key) }
        let openings = journals.filter { $0.value.account == key }
        // A suspended open must finish and be poisoned before the matching namespace is unlinked.
        for (_, opening) in openings {
            if let journal = try? await opening.task.value { await journal.revokeForDataRemoval() }
        }
        try await PinkhaHanlinWriteJournal.removeAccountData(account, app: app)
        for (id, _) in openings { journals[id] = nil }
    }
}
