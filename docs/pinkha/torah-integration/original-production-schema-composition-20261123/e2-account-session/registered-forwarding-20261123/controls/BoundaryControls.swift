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
    func accountRecover() async throws { try await perform("AccountRecover") }
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

@main
struct Controls {
    @MainActor
    static func main() async {
        do {
            try await untouchedAndLateCallback()
            try await ordinaryRecovery(cancelAwait: false)
            try await ordinaryRecovery(cancelAwait: true)
            try await beforeStartupAdmission()
            try await admittedBeforeNative()
            try await acceptedStopDuplicateAndCancel()
            try await failedStopRetry()
            try await parentLineage()
            try await namedCompletionAndBinding()
            try await synchronousHistoricalEffects()
            try await demandRetirement()
            try await standaloneAndConstructionRefusal()
            let result: [String: Any] = [
                "status": "PASS", "passed": Check.passed, "controls": Check.passed.count,
                "assertions": Check.assertions,
                "scope": "Exact Foundation wrapper/lifetime/capture/attempt/binding/demand source with explicit boundary doubles; no Combine/UIKit/Lib/native/account or deployment execution."
            ]
            print("RESULT_JSON " + String(data: try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]), encoding: .utf8)!)
        } catch {
            let result: [String: Any] = ["status": "FAIL", "passed": Check.passed,
                                       "assertions": Check.assertions, "error": String(reflecting: error)]
            print("RESULT_JSON " + String(data: try! JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]), encoding: .utf8)!)
            exit(1)
        }
    }

    @MainActor
    static func untouchedAndLateCallback() async throws {
        let base = AuthBoundaryDouble()
        let service = PinkhaHanlinAuthService(base: base)
        let caller = try await service.makeOriginalEditorCaller()
        let retired = Locked(false)
        let observation = caller.observeRetirement { retired.set(true) }
        let receipt = try await caller.closeAuthentication()
        try Check.that(Check.neverStarted(receipt), "untouched owner is drain-only")
        try Check.that(retired.get(), "retirement observer fires")
        try Check.that(await base.count("AccountStop") == 0, "no invented native Stop on untouched UI")
        try Check.that(await Check.rejected { try await caller.walletRecovery(mnemonic: "late") }, "late recovery rejects")
        try await caller.releaseAfterRuntimeDrain()
        let next = try await service.makeOriginalEditorCaller()
        var staleEffect = false
        try Check.that(await Check.rejected { try caller.withUIAction { staleEffect = true } }, "old callback cannot borrow replacement")
        try Check.that(!staleEffect && next.isCurrent, "new owner distinct and current")
        _ = try await next.closeAuthentication()
        try await next.releaseAfterRuntimeDrain()
        observation.cancel()
        Check.pass("untouched_close_and_frozen_late_callback")
    }

    @MainActor
    static func ordinaryRecovery(cancelAwait: Bool) async throws {
        let release = Gate()
        let base = AuthBoundaryDouble(wallet: release)
        let service = PinkhaHanlinAuthService(base: base)
        let caller = try await service.makeOriginalEditorCaller()
        let effect = Locked(false), closed = Locked(false)
        let retired = Gate()
        let observation = caller.observeRetirement { Task { await retired.open() } }
        let work = Task {
            try await caller.withUIOperation {
                try await caller.walletRecovery(mnemonic: "fixture")
                try caller.validateCurrent()
                effect.set(true)
            }
        }
        await base.walletEntered.wait()
        if cancelAwait { work.cancel() }
        let close = Task {
            let receipt = try await caller.closeAuthentication()
            closed.set(true)
            return receipt
        }
        await retired.wait()
        try await Check.briefObservation()
        try Check.that(!closed.get(), "close must retain actual admitted recovery")
        try Check.that(await base.nativeCount("WalletRecover") == 1, "actual original capture admission exercised")
        try Check.that(await Check.rejected { _ = try await caller.selectAccount(id: "late", preferredSpaceId: "") }, "late event startup rejected")
        await release.open()
        try Check.that(await Check.rejected { try await work.value }, "retired/canceled ordinary operation rejects continuation")
        try Check.that(Check.neverStarted(try await close.value), "ordinary wallet drain never claims native app stop")
        let stopCount = await base.count("AccountStop")
        try Check.that(!effect.get() && stopCount == 0, "no Seed-like continuation or fake Stop")
        try await caller.releaseAfterRuntimeDrain()
        observation.cancel()
        Check.pass(cancelAwait ? "ordinary_recovery_cancel_keeps_real_drain" : "ordinary_recovery_completion_keeps_real_drain")
    }

    @MainActor
    static func beforeStartupAdmission() async throws {
        let gate = Gate(), entered = Gate()
        let base = AuthBoundaryDouble()
        let service = PinkhaHanlinAuthService(base: base)
        let caller = try await service.makeOriginalEditorCaller()
        let work = Task {
            try await caller.withUIOperation {
                await entered.open()
                await gate.wait()
                _ = try await caller.selectAccount(id: "future", preferredSpaceId: "")
            }
        }
        await entered.wait()
        caller.retire()
        let close = Task { try await caller.closeAuthentication() }
        await gate.open()
        try Check.that(await Check.rejected { try await work.value }, "retirement before wrapper startup rejects")
        try Check.that(Check.neverStarted(try await close.value), "no admitted startup means drain-only")
        let selectCount = await base.count("AccountSelect")
        let stopCount = await base.count("AccountStop")
        try Check.that(selectCount == 0 && stopCount == 0, "no future native start or fake cancellation")
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("close_before_original_startup_admission")
    }

    @MainActor
    static func admittedBeforeNative() async throws {
        let gate = Gate()
        let base = AuthBoundaryDouble(startup: gate, startupBeforeNative: true, failStop: true)
        let service = PinkhaHanlinAuthService(base: base)
        let caller = try await service.makeOriginalEditorCaller()
        let startup = Task { try await caller.selectAccount(id: "future", preferredSpaceId: "") }
        await base.startupEntered.wait()
        try Check.that(await base.nativeCount("AccountSelect") == 0, "wrapper admission precedes modeled native registration")
        try Check.that(await Check.rejected { _ = try await caller.closeAuthentication() }, "ACCOUNT_IS_NOT_RUNNING is not successful Stop")
        try Check.that(await Check.rejected { _ = try await service.makeOriginalEditorCaller() }, "failed close retains exact owner")
        try Check.that(await Check.rejected { try await caller.releaseAfterRuntimeDrain() }, "failed close cannot release")
        await gate.open()
        try Check.that(await Check.rejected { _ = try await startup.value }, "retired queued start cannot gain admission")
        await base.setFailStop(false)
        try Check.that(Check.nativeStop(try await caller.retryCloseAuthentication()), "explicit same-owner Stop retry supplies actual successful completion")
        try Check.that(await base.count("AccountStop") == 2, "no blind Stop loop")
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("admitted_before_native_stop_failure_is_retained")
    }

    @MainActor
    static func acceptedStopDuplicateAndCancel() async throws {
        let startGate = Gate(), stopGate = Gate()
        let base = AuthBoundaryDouble(startup: startGate, stop: stopGate)
        let service = PinkhaHanlinAuthService(base: base)
        let caller = try await service.makeOriginalEditorCaller()
        let startup = Task { try await caller.selectAccount(id: "active", preferredSpaceId: "") }
        await base.startupEntered.wait()
        let close1 = Task { try await caller.closeAuthentication() }
        await base.stopEntered.wait()
        let close2 = Task { try await caller.closeAuthentication() }
        close1.cancel()
        try await Check.briefObservation()
        try Check.that(await base.count("AccountStop") == 1, "duplicate close shares retained original Stop")
        await stopGate.open()
        try await Check.briefObservation()
        try Check.that(await Check.rejected { try await caller.releaseAfterRuntimeDrain() }, "successful Stop alone does not release held startup")
        await startGate.open()
        try Check.that(await Check.rejected { _ = try await startup.value }, "retired native startup returns before close completes")
        let r1 = try await close1.value, r2 = try await close2.value
        try Check.that(Check.nativeStop(r1) && Check.nativeStop(r2), "caller cancellation cannot cancel retained close")
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("duplicate_close_cancel_keeps_stop_and_startup_drain")
    }

    @MainActor
    static func failedStopRetry() async throws {
        let gate = Gate()
        let base = AuthBoundaryDouble(startup: gate, failStop: true)
        let service = PinkhaHanlinAuthService(base: base)
        let caller = try await service.makeOriginalEditorCaller()
        let startup = Task { try await caller.selectAccount(id: "active", preferredSpaceId: "") }
        await base.startupEntered.wait()
        try Check.that(await Check.rejected { _ = try await caller.closeAuthentication() }, "failed Stop returns without falsely joining blocked startup")
        try Check.that(await base.nativeCount("AccountSelect") == 1, "failed Stop case has admitted native start")
        try Check.that(await Check.rejected { _ = try await caller.walletRecovery(mnemonic: "late") }, "failed close cannot renew authority")
        await base.setFailStop(false)
        let retry = Task { try await caller.retryCloseAuthentication() }
        try await Check.briefObservation()
        try Check.that(await base.count("AccountStop") == 2, "only explicit retry dispatches second Stop")
        await gate.open()
        _ = try? await startup.value
        try Check.that(Check.nativeStop(try await retry.value), "retry joins real startup release")
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("failed_stop_requires_same_owner_explicit_retry")
    }

    @MainActor
    static func parentLineage() async throws {
        let base = AuthBoundaryDouble()
        let service = PinkhaHanlinAuthService(base: base)
        let caller = try await service.makeOriginalEditorCaller()
        let parent = try OriginalAuthAttempt(kind: .ordinary)
        try await OriginalAuthRequestContext.$parent.withValue(parent) {
            try await caller.withUIOperation {
                try Check.that(OriginalAuthRequestContext.parent === parent, "UI lease preserves original parent")
                _ = try await caller.createAccount(name: "", iconOption: 0, imagePath: "")
            }
        }
        let actual = await base.retainedStartupParent()
        try Check.that(actual?.isCurrent == true, "successful original startup survives temporary UI lease")
        try Check.that(actual?.captures.contains(where: { $0.source === parent.captures.last?.source }) == true, "existing ancestor retained")
        parent.retire()
        try Check.that(actual?.isCurrent == false, "existing ancestor retirement still propagates")
        parent.finishOuter()
        try Check.that(Check.nativeStop(try await caller.closeAuthentication()), "historical close does not require retired parent authority")
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("original_parent_lineage_is_preserved")
    }

    @MainActor
    static func namedCompletionAndBinding() async throws {
        let service = PinkhaHanlinAuthService(base: AuthBoundaryDouble())
        let caller = try await service.makeOriginalEditorCaller()
        let completion = Locked<InvocationDispatchCompletion?>(nil)
        let admitted = Gate()
        let returned = Locked(false)
        let work = Task {
            let value = try await caller.withNamedNativeRPC("AccountMigrate") {
                guard let binding = InvocationDispatchContext.binding else { throw TestError.synthetic }
                let permit = try await binding.prepare(messageName: "AccountMigrate")
                completion.set(try permit.begin())
                await admitted.open()
                return 7
            }
            returned.set(true)
            return value
        }
        await admitted.wait()
        try await Check.briefObservation()
        try Check.that(!returned.get(), "Swift response alone does not complete named native operation")
        completion.get()?.finish()
        try Check.that(try await work.value == 7 && returned.get(), "exact actual Invocation release completes named operation")
        let foreign = InvocationDispatchBinding { _ in throw TestError.synthetic }
        let refused = await InvocationDispatchContext.$binding.withValue(foreign) {
            await Check.rejected { _ = try await caller.withNamedNativeRPC("AccountMigrate") { 9 } }
        }
        try Check.that(refused, "unrelated binding cannot be overwritten")
        try Check.that(await Check.rejected {
            try await caller.withNamedNativeRPC("AccountMigrate") {
                _ = try await InvocationDispatchContext.binding!.prepare(messageName: "AccountSelect")
            }
        }, "named binding rejects a different RPC")
        let completion2 = Locked<InvocationDispatchCompletion?>(nil), admitted2 = Gate()
        let work2 = Task {
            try await caller.withNamedNativeRPC("WorkspaceSetInfo") {
                let permit = try await InvocationDispatchContext.binding!.prepare(messageName: "WorkspaceSetInfo")
                completion2.set(try permit.begin())
                await admitted2.open()
            }
        }
        await admitted2.wait()
        caller.retire()
        completion2.get()?.finish()
        try Check.that(await Check.rejected { try await work2.value }, "post-drain retirement is revalidated")
        _ = try await caller.closeAuthentication()
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("named_rpc_actual_completion_and_binding_adversaries")
    }

    @MainActor
    static func synchronousHistoricalEffects() async throws {
        let service = PinkhaHanlinAuthService(base: AuthBoundaryDouble())
        let caller = try await service.makeOriginalEditorCaller()
        var historicalEffect = false
        let rejected = await Check.rejected {
            try caller.withUIAction {
                caller.retire()
                historicalEffect = true
            }
        }
        try Check.that(rejected && historicalEffect, "admitted synchronous effects may finish historically; no rollback claim")
        try Check.that(await Check.rejected { try caller.withUIAction { historicalEffect = false } }, "late picker-like callback rejects before mutation")
        try Check.that(historicalEffect, "historical effect was not silently erased")
        _ = try await caller.closeAuthentication()
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("synchronous_whole_action_historical_effect_boundary")
    }

    @MainActor
    static func demandRetirement() async throws {
        let service = PinkhaHanlinAuthService(base: AuthBoundaryDouble())
        let caller = try await service.makeOriginalEditorCaller()
        let lifetime = EditorDocumentWriteLifetime()
        let capture = try EditorDocumentWriteCapture(lifetime)
        let readiness = OriginalApplicationConsumerDemand { lifetime.markUnavailable() }
        let observation = caller.observeRetirement { readiness.end() }
        let wait = Task { try await readiness.waitUntilRequested() }
        caller.retire()
        try Check.that(await Check.rejected { try await wait.value }, "retirement terminates a pending real-consumer demand wait")
        readiness.didForwardPositiveDemand()
        try Check.that(await Check.rejected { try readiness.validateRequested() }, "late positive-demand acknowledgment cannot revive ended consumer")
        try Check.that(await Check.rejected { try capture.validate() }, "consumer restriction retires with exact readiness")
        let immediate = Locked(false)
        let lateObservation = caller.observeRetirement { immediate.set(true) }
        try Check.that(immediate.get(), "late observer sees same frozen retirement")
        _ = try await caller.closeAuthentication()
        try await caller.releaseAfterRuntimeDrain()
        observation.cancel(); lateObservation.cancel()
        Check.pass("consumer_demand_wait_retires_with_frozen_caller")
    }

    @MainActor
    static func standaloneAndConstructionRefusal() async throws {
        OriginalRuntimeEnvironment.deploymentMode = .standalone
        let base = AuthBoundaryDouble()
        let service = PinkhaHanlinAuthService(base: base)
        try Check.that(await Check.rejected { _ = try await service.makeOriginalEditorCaller() }, "standalone cannot mint embedded caller")
        try await service.walletRecovery(mnemonic: "fixture")
        _ = try await service.createAccount(name: "", iconOption: 0, imagePath: "")
        try await service.logout(removeData: false)
        let walletCount = await base.count("WalletRecover")
        let createCount = await base.count("AccountCreate")
        let stopCount = await base.count("AccountStop")
        try Check.that(walletCount == 1 && createCount == 1 && stopCount == 1, "original standalone registered methods remain")
        OriginalRuntimeEnvironment.deploymentMode = .embeddedEditor
        let fresh = PinkhaHanlinAuthService(base: AuthBoundaryDouble())
        let foreign = InvocationDispatchBinding { _ in throw TestError.synthetic }
        let rejected = await InvocationDispatchContext.$binding.withValue(foreign) {
            await Check.rejected { _ = try await fresh.makeOriginalEditorCaller() }
        }
        try Check.that(rejected, "unrelated construction binding refuses")
        let caller = try await fresh.makeOriginalEditorCaller()
        try Check.that(caller.isCurrent, "throwing construction did not strand owner")
        _ = try await caller.closeAuthentication()
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("standalone_defaults_and_construction_refusal")
    }
}
