import Foundation

// These are explicit boundary doubles, not original UIKit, native middleware,
// Factory, account initialization, bootstrap or deployment qualification.
final class Locked<Value: Sendable>: @unchecked Sendable {
    private let lock = NSLock()
    private var value: Value
    init(_ value: Value) { self.value = value }
    func get() -> Value { lock.lock(); defer { lock.unlock() }; return value }
    func set(_ newValue: Value) { lock.lock(); value = newValue; lock.unlock() }
}
actor Gate {
    private var opened: Bool
    private var waiters: [CheckedContinuation<Void, Never>] = []
    init(open: Bool = false) { opened = open }
    func wait() async {
        if opened { return }
        await withCheckedContinuation { waiters.append($0) }
    }
    func open() {
        opened = true
        let old = waiters
        waiters.removeAll()
        for waiter in old { waiter.resume() }
    }
}
enum TestError: Error { case assertion(String), accountNotRunning, missingOriginalParent, synthetic }
enum HanlinHostError: Error { case staleContext }
enum AccountStatus: Sendable { case active }
struct AccountData: Sendable { let id: String }
enum OriginalRuntimeEnvironment {
    enum Mode: Sendable { case standalone, embeddedEditor }
    private static let storage = Locked<Mode>(.embeddedEditor)
    static var deploymentMode: Mode {
        get { storage.get() }
        set { storage.set(newValue) }
    }
}
final class AccountManagerDouble: Sendable { let account = AccountData(id: "original-account") }
protocol PinkhaSpaceBootstrapServiceProtocol: Sendable {
    func quiesceAccountOperations() async
    func resumeAccountOperations() async throws
}
actor BootstrapDouble: PinkhaSpaceBootstrapServiceProtocol {
    func quiesceAccountOperations() async {}
    func resumeAccountOperations() async throws {}
}
final class Container: Sendable {
    static let shared = Container()
    private let account = AccountManagerDouble()
    private let bootstrap = BootstrapDouble()
    func accountManager() -> AccountManagerDouble { account }
    func pinkhaBootstrapService() -> any PinkhaSpaceBootstrapServiceProtocol { bootstrap }
}
@MainActor
final class PinkhaHanlinAccountOwner {
    static let shared = PinkhaHanlinAccountOwner()
    func closeAccount(_ id: String, removeData: Bool) async throws {}
    func accountDidOpen(_ id: String) throws {}
}

actor AuthBoundaryDouble: AuthServiceProtocol {
    let walletEntered = Gate()
    let startupEntered = Gate()
    let stopEntered = Gate()
    let walletRelease: Gate?
    let startupRelease: Gate?
    let stopRelease: Gate?
    let startupBeforeNative: Bool
    private var failStop: Bool
    private var calls: [String: Int] = [:]
    private var native: [String: Int] = [:]
    private var startupParent: OriginalAuthAttempt?
    private var recoveryEntered = Gate()
    private var recoveryRelease: Gate?
    func configureRecovery(entered: Gate, release: Gate?) {
        recoveryEntered = entered; recoveryRelease = release
    }

    init(wallet: Gate? = nil, startup: Gate? = nil, stop: Gate? = nil,
         startupBeforeNative: Bool = false, failStop: Bool = false) {
        walletRelease = wallet
        startupRelease = startup
        stopRelease = stop
        self.startupBeforeNative = startupBeforeNative
        self.failStop = failStop
    }

    func setFailStop(_ value: Bool) { failStop = value }
    func count(_ name: String) -> Int { calls[name, default: 0] }
    func nativeCount(_ name: String) -> Int { native[name, default: 0] }
    func retainedStartupParent() -> OriginalAuthAttempt? { startupParent }

    private func perform(_ name: String, entered: Gate? = nil, release: Gate? = nil,
                         beforeNative: Bool = false, failure: Bool = false) async throws {
        calls[name, default: 0] += 1
        guard let parent = OriginalAuthRequestContext.parent else { throw TestError.missingOriginalParent }
        if name == "AccountCreate" || name == "AccountSelect" { startupParent = parent }
        if beforeNative {
            await entered?.open()
            await release?.wait()
        }
        try parent.validate()
        let binding = InvocationDispatchContext.binding ?? parent.startupBinding()
        let permit = try await binding.prepare(messageName: name)
        let completion = try permit.begin()
        native[name, default: 0] += 1
        defer { completion.finish() }
        if !beforeNative {
            await entered?.open()
            await release?.wait()
        }
        if failure { throw TestError.accountNotRunning }
    }

    func createWallet() async throws -> String { try await perform("WalletCreate"); return "fixture" }
    func walletRecovery(mnemonic: String) async throws {
        try await perform("WalletRecover", entered: walletEntered, release: walletRelease)
    }
    func accountRecover() async throws {
        let entered = recoveryEntered, release = recoveryRelease
        try await perform("AccountRecover", entered: entered, release: release)
    }
    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        try await perform("AccountCreate", entered: startupEntered, release: startupRelease, beforeNative: startupBeforeNative)
        return AccountData(id: "opened")
    }
    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        try await perform("AccountSelect", entered: startupEntered, release: startupRelease, beforeNative: startupBeforeNative)
        return AccountData(id: id)
    }
    func mnemonicByEntropy(_ entropy: String) async throws -> String {
        try await perform("WalletConvert")
        return "fixture"
    }
    func logout(removeData: Bool) async throws {
        try await perform("AccountStop", entered: stopEntered, release: stopRelease, failure: failStop)
    }
    func deleteAccount() async throws -> AccountStatus { try await perform("AccountDelete"); return .active }
    func restoreAccount() async throws -> AccountStatus { try await perform("AccountRevertDeletion"); return .active }
}

@MainActor
enum Check {
    static var assertions = 0
    static var passed: [String] = []
    static func that(_ value: Bool, _ message: String) throws {
        assertions += 1
        if !value { throw TestError.assertion(message) }
    }
    static func rejected(_ operation: @MainActor () async throws -> Void) async -> Bool {
        do { try await operation(); return false } catch { return true }
    }
    static func nativeStop(_ receipt: OriginalEditorAuthCloseReceipt) -> Bool {
        if case .nativeStopCompleted = receipt { return true }; return false
    }
    static func neverStarted(_ receipt: OriginalEditorAuthCloseReceipt) -> Bool {
        if case .neverStartedDrained = receipt { return true }; return false
    }
    static func briefObservation() async throws { try await Task.sleep(nanoseconds: 30_000_000) }
    static func pass(_ name: String) { passed.append(name); print("PASS " + name) }
}

