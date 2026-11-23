import Foundation
import Factory
import Services
import HanlinHostContracts

import AnytypeCore
import ProtobufMessages

/// Private forwarding ownership. The actual registered service remains the
/// implementation and no account/Space/source identity is accepted as authority.
private enum OriginalEditorAuthCallContext {
    @TaskLocal static var caller: OriginalEditorAuthCaller?
    @TaskLocal static var closing: OriginalEditorAuthCaller?
}

enum OriginalEditorAuthCloseReceipt: Sendable {
    case neverStartedDrained
    case nativeStopCompleted
}

private final class OriginalEditorAuthCallerState: @unchecked Sendable {
    private let lock = NSLock()
    let lifetime: EditorDocumentWriteLifetime
    let capture: EditorDocumentWriteCapture
    private var retired = false
    private var startupAdmitted = false
    private var stopRequired = false
    private var stopCompleted = false

    init() throws {
        let lifetime = EditorDocumentWriteLifetime()
        self.lifetime = lifetime
        capture = try EditorDocumentWriteCapture(lifetime)
    }

    func validate() throws {
        try Task.checkCancellation()
        lock.lock()
        let retired = retired
        lock.unlock()
        guard !retired else { throw HanlinHostError.staleContext }
        try capture.validate()
    }

    func retire() {
        lock.lock()
        retired = true
        lock.unlock()
        lifetime.markUnavailable()
    }

    /// Retirement and original wrapper admission are one synchronous boundary.
    /// This says nothing about the later Go beginStart registration.
    func makeAttempt(kind: OriginalAuthAttempt.Kind) throws -> OriginalAuthAttempt {
        lock.lock()
        defer { lock.unlock() }
        guard !retired else { throw HanlinHostError.staleContext }
        let attempt = try OriginalAuthAttempt(kind: kind, restricting: [capture])
        if kind == .startup {
            startupAdmitted = true
            stopRequired = true
            stopCompleted = false
        }
        return attempt
    }

    func admitForwarding() throws -> [EditorDocumentWriteLifetime.Observation] {
        lock.lock()
        defer { lock.unlock() }
        guard !retired else { throw HanlinHostError.staleContext }
        try Task.checkCancellation()
        return try EditorDocumentWriteCapture.acquireAll([capture])
    }

    var requiresNativeStop: Bool {
        lock.lock()
        defer { lock.unlock() }
        return stopRequired
    }

    func recordCompletedNativeStop() {
        lock.lock()
        stopRequired = false
        stopCompleted = true
        lock.unlock()
    }

    func drainedReceipt() throws -> OriginalEditorAuthCloseReceipt {
        lock.lock()
        defer { lock.unlock() }
        guard retired, !stopRequired else { throw HanlinHostError.staleContext }
        if startupAdmitted {
            guard stopCompleted else { throw HanlinHostError.staleContext }
            return .nativeStopCompleted
        }
        return stopCompleted ? .nativeStopCompleted : .neverStartedDrained
    }
}

/// Immutable per-presentation caller; its initializer and registered actor are
/// file-private. Escaped original callbacks retain this object explicitly.
final class OriginalEditorAuthCaller: AuthServiceProtocol, Sendable {
    fileprivate let service: PinkhaHanlinAuthService
    fileprivate let state: OriginalEditorAuthCallerState

    fileprivate init(service: PinkhaHanlinAuthService) throws {
        self.service = service
        state = try OriginalEditorAuthCallerState()
    }

    func validateCurrent() throws { try state.validate() }
    func retire() { state.retire() }

    var isCurrent: Bool {
        do { try validateCurrent(); return true }
        catch { return false }
    }

    func closeAuthentication() async throws -> OriginalEditorAuthCloseReceipt {
        try await service.closeOriginalEditorCaller(self, retry: false)
    }

    func retryCloseAuthentication() async throws -> OriginalEditorAuthCloseReceipt {
        try await service.closeOriginalEditorCaller(self, retry: true)
    }

    func releaseAfterRuntimeDrain() async throws {
        try await service.releaseOriginalEditorCaller(self)
    }

    private func forward<Value: Sendable>(
        _ operation: @Sendable (PinkhaHanlinAuthService) async throws -> Value
    ) async throws -> Value {
        try validateCurrent()
        if let existing = OriginalEditorAuthCallContext.caller, existing !== self {
            throw HanlinHostError.staleContext
        }
        let admissions = try state.admitForwarding()
        defer { for admission in admissions { admission.cancel() } }
        return try await OriginalEditorAuthCallContext.$caller.withValue(self) {
            try await operation(service)
        }
    }

    func createWallet() async throws -> String {
        try await forward { try await $0.createWallet() }
    }

    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        try await forward { try await $0.createAccount(name: name, iconOption: iconOption, imagePath: imagePath) }
    }

    func walletRecovery(mnemonic: String) async throws {
        try await forward { try await $0.walletRecovery(mnemonic: mnemonic) }
    }

    func accountRecover() async throws {
        try await forward { try await $0.accountRecover() }
    }

    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        try await forward { try await $0.selectAccount(id: id, preferredSpaceId: preferredSpaceId) }
    }

    func mnemonicByEntropy(_ entropy: String) async throws -> String {
        try await forward { try await $0.mnemonicByEntropy(entropy) }
    }

    func logout(removeData: Bool) async throws {
        try await forward { try await $0.logout(removeData: removeData) }
    }

    func deleteAccount() async throws -> AccountStatus {
        try await forward { try await $0.deleteAccount() }
    }

    func restoreAccount() async throws -> AccountStatus {
        try await forward { try await $0.restoreAccount() }
    }

    /// Hold the original lifetime across the complete UI operation, including
    /// its Seed/default-space/state continuation after an Auth service returns.
    /// Preserve the preexisting Auth parent; the temporary view task must not
    /// become a new ancestor of a successful original LoginState startup source.
    @MainActor
    func withUIOperation(_ operation: @MainActor () async throws -> Void) async throws {
        let attempt = try state.makeAttempt(kind: .ordinary)
        let admissions = try attempt.admitStage()
        try await withTaskCancellationHandler {
            do {
                try await OriginalEditorAuthCallContext.$caller.withValue(self) {
                    try await operation()
                }
                try attempt.validate()
                for admission in admissions { admission.cancel() }
                attempt.finishOuter()
            } catch {
                attempt.retire()
                for admission in admissions { admission.cancel() }
                attempt.finishOuter()
                await attempt.waitForDrain()
                throw error
            }
        } onCancel: { attempt.retire() }
    }

    @MainActor
    func withUIAction(_ operation: @MainActor () throws -> Void) throws {
        let attempt = try state.makeAttempt(kind: .ordinary)
        let admissions = try attempt.admitStage()
        defer {
            for admission in admissions { admission.cancel() }
            attempt.finishOuter()
        }
        try operation()
        try attempt.validate()
    }

    @MainActor
    static func withUIOperation(
        _ caller: OriginalEditorAuthCaller?,
        _ operation: @MainActor () async throws -> Void
    ) async throws {
        if let caller { try await caller.withUIOperation(operation) }
        else { try await operation() }
    }

    @MainActor
    static func withUIAction(
        _ caller: OriginalEditorAuthCaller?,
        _ operation: @MainActor () throws -> Void
    ) throws {
        if let caller { try caller.withUIAction(operation) }
        else { try operation() }
    }

    /// The four auxiliary original services invoke outside AuthService. Their
    /// actual named native return owns the lease, even after early await cancel.
    /// A preexisting unrelated binding is rejected, never silently replaced.
    @MainActor
    func withNamedNativeRPC<Value: Sendable>(
        _ rpcName: String,
        _ operation: @MainActor () async throws -> Value
    ) async throws -> Value {
        guard InvocationDispatchContext.binding == nil else { throw HanlinHostError.staleContext }
        let attempt = try state.makeAttempt(kind: .ordinary)
        let admissions = try attempt.admitStage()
        return try await withTaskCancellationHandler {
            do {
                let value = try await InvocationDispatchContext.$binding.withValue(
                    Self.namedBinding(attempt, names: [rpcName])
                ) { try await operation() }
                try attempt.validate()
                for admission in admissions { admission.cancel() }
                attempt.finishOuter()
                return value
            } catch {
                attempt.retire()
                for admission in admissions { admission.cancel() }
                attempt.finishOuter()
                await attempt.waitForDrain()
                throw error
            }
        } onCancel: { attempt.retire() }
    }

    fileprivate static func namedBinding(
        _ attempt: OriginalAuthAttempt, names: Set<String>
    ) -> InvocationDispatchBinding {
        InvocationDispatchBinding(committedEvents: { nil }) { name in
            guard names.contains(name) else { throw HanlinHostError.staleContext }
            try attempt.validate()
            return InvocationDispatchPermit {
                try attempt.validate()
                let admissions = try EditorDocumentWriteCapture.acquireAll(attempt.captures)
                return InvocationDispatchCompletion {
                    for admission in admissions { admission.cancel() }
                }
            }
        }
    }
}


/// Native Auth remains the account owner. These exact attempts only restrict
/// the existing Hanlin shutdown/resume calls and admit original Back cancellation.
actor PinkhaHanlinAuthService: AuthServiceProtocol {
    private let base: any AuthServiceProtocol
    private let accounts = Container.shared.accountManager()
    private var bootstrap: any PinkhaSpaceBootstrapServiceProtocol { Container.shared.pinkhaBootstrapService() }
    private var current: OriginalAuthAttempt?
    private var stopping: OriginalAuthAttempt?
    private var successfulStopRequired = false
    private var originalEditorCaller: OriginalEditorAuthCaller?
    private var originalEditorCloseTask: Task<OriginalEditorAuthCloseReceipt, Error>?
    private var originalEditorCloseResult: OriginalEditorAuthCloseReceipt?
    private var originalEditorCloseFailed = false
    private var originalEditorStopTask: Task<Void, Error>?

    init(base: any AuthServiceProtocol) { self.base = base }

    /// All throwing work precedes owner installation; no await or validation
    /// after assignment can strand a caller not returned to the presentation.
    func makeOriginalEditorCaller() throws -> OriginalEditorAuthCaller {
        guard OriginalRuntimeEnvironment.deploymentMode == .embeddedEditor,
              originalEditorCaller == nil, current == nil, stopping == nil,
              !successfulStopRequired, InvocationDispatchContext.binding == nil else {
            throw HanlinHostError.staleContext
        }
        let caller = try OriginalEditorAuthCaller(service: self)
        originalEditorCaller = caller
        return caller
    }

    private func originalEditorAdmissionCaller(allowHistoricalClose: Bool = false) throws -> OriginalEditorAuthCaller? {
        guard OriginalRuntimeEnvironment.deploymentMode == .embeddedEditor else { return nil }
        guard let caller = originalEditorCaller,
              OriginalEditorAuthCallContext.caller === caller else {
            throw HanlinHostError.staleContext
        }
        if allowHistoricalClose, OriginalEditorAuthCallContext.closing === caller,
           originalEditorCloseTask != nil {
            return caller
        }
        try caller.validateCurrent()
        return caller
    }

    fileprivate func closeOriginalEditorCaller(
        _ caller: OriginalEditorAuthCaller, retry: Bool
    ) async throws -> OriginalEditorAuthCloseReceipt {
        guard originalEditorCaller === caller else { throw HanlinHostError.staleContext }
        if retry {
            guard originalEditorCloseFailed, let previousClose = originalEditorCloseTask else {
                throw HanlinHostError.staleContext
            }
            originalEditorCloseFailed = false
            _ = await previousClose.result
            guard originalEditorCaller === caller, originalEditorCloseResult == nil else {
                throw HanlinHostError.staleContext
            }
            originalEditorCloseTask = nil
        }
        if let existing = originalEditorCloseTask { return try await existing.value }
        caller.retire()
        let previous = current
        let cleanup = Task { [self] in
            do {
                if let alreadyStopping = originalEditorStopTask {
                    // The same historical Stop already owns the native call.
                    // Its result includes actual Stop drain, not UI await cancel.
                    try await alreadyStopping.value
                } else if caller.state.requiresNativeStop || successfulStopRequired {
                    guard InvocationDispatchContext.binding == nil else { throw HanlinHostError.staleContext }
                    // Historical cancellation does not need renewed current-write
                    // authority from the retired UI parent.
                    try await OriginalAuthRequestContext.$parent.withValue(nil) {
                        try await OriginalEditorAuthCallContext.$caller.withValue(caller) {
                            try await OriginalEditorAuthCallContext.$closing.withValue(caller) {
                                try await logout(removeData: false)
                            }
                        }
                    }
                }
                // A failed Stop exits above: do not join a possibly blocked
                // native startup or declare stopped after ACCOUNT_IS_NOT_RUNNING.
                await previous?.waitForDrain()
                await caller.state.lifetime.waitForOperationsToDrain()
                guard originalEditorCaller === caller, current == nil,
                      stopping == nil, !successfulStopRequired else {
                    throw HanlinHostError.staleContext
                }
                let receipt = try caller.state.drainedReceipt()
                originalEditorCloseResult = receipt
                return receipt
            } catch {
                originalEditorCloseFailed = true
                throw error
            }
        }
        originalEditorCloseTask = cleanup
        return try await cleanup.value
    }

    /// Called only by the original process owner after its additional FIFO,
    /// selected-operation and consumer-task joins. This method grants none of
    /// those facts and cannot release a failed or pending authentication close.
    fileprivate func releaseOriginalEditorCaller(_ caller: OriginalEditorAuthCaller) async throws {
        guard originalEditorCaller === caller, originalEditorCloseResult != nil,
              !originalEditorCloseFailed, !successfulStopRequired else {
            throw HanlinHostError.staleContext
        }
        await caller.state.lifetime.waitForOperationsToDrain()
        guard originalEditorCaller === caller, originalEditorCloseResult != nil,
              current == nil, stopping == nil, !successfulStopRequired else {
            throw HanlinHostError.staleContext
        }
        originalEditorCaller = nil
        originalEditorCloseTask = nil
        originalEditorCloseResult = nil
        originalEditorCloseFailed = false
        originalEditorStopTask = nil
    }



    func createWallet() async throws -> String {
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.createWallet() }
        }
    }

    func walletRecovery(mnemonic: String) async throws {
        let base = base
        try await perform(kind: .ordinary) { attempt in
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.walletRecovery(mnemonic: mnemonic) }
        }
    }

    func accountRecover() async throws {
        let base = base
        try await perform(kind: .ordinary) { attempt in
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.accountRecover() }
        }
    }

    func mnemonicByEntropy(_ entropy: String) async throws -> String {
        guard OriginalRuntimeEnvironment.deploymentMode == .embeddedEditor else {
            return try await base.mnemonicByEntropy(entropy)
        }
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            guard InvocationDispatchContext.binding == nil else { throw HanlinHostError.staleContext }
            return try await OriginalAuthRequestContext.$parent.withValue(attempt) {
                try await InvocationDispatchContext.$binding.withValue(
                    OriginalEditorAuthCaller.namedBinding(attempt, names: ["WalletConvert"])
                ) { try await base.mnemonicByEntropy(entropy) }
            }
        }
    }

    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        let base = base
        let bootstrap = bootstrap
        let previousAccount = accounts.account.id
        return try await perform(kind: .startup) { attempt in
            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.closeAccount(previousAccount, removeData: false)
            }
            try await self.stage(attempt) { await bootstrap.quiesceAccountOperations() }
            let account = try await self.stage(attempt) {
                try await OriginalAuthRequestContext.$parent.withValue(attempt) {
                    try await base.createAccount(name: name, iconOption: iconOption, imagePath: imagePath)
                }
            }
            try await self.stage(attempt) { try await bootstrap.resumeAccountOperations() }
            try await self.stage(attempt) {
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account.id)
                }
            }
            return account
        }
    }

    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        let base = base
        let bootstrap = bootstrap
        let previousAccount = accounts.account.id
        return try await perform(kind: .startup) { attempt in
            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.closeAccount(previousAccount, removeData: false)
            }
            try await self.stage(attempt) { await bootstrap.quiesceAccountOperations() }
            let account = try await self.stage(attempt) {
                try await OriginalAuthRequestContext.$parent.withValue(attempt) {
                    try await base.selectAccount(id: id, preferredSpaceId: preferredSpaceId)
                }
            }
            try await self.stage(attempt) { try await bootstrap.resumeAccountOperations() }
            try await self.stage(attempt) {
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account.id)
                }
            }
            return account
        }
    }

    func logout(removeData: Bool) async throws {
        guard stopping == nil else { throw HanlinHostError.staleContext }
        let originalCaller = try originalEditorAdmissionCaller(allowHistoricalClose: true)
        let previous = current
        if let previous {
            // Keep the existing busy rejection for destructive overlap. Only
            // the real Back/logout(false) route supersedes a pending startup.
            guard previous.kind == .startup, !removeData else { throw HanlinHostError.staleContext }
        }
        let stop = try OriginalAuthAttempt(kind: .stop)
        stopping = stop
        previous?.retire() // synchronous, also revokes the child's Auth attempt
        let originalAccount = accounts.account.id
        let bootstrap = bootstrap
        // This accepted Stop must outlive cancellation of its UI caller. Its
        // native child is the operation that releases any retired startup.
        let cleanup = Task { [self] in
            do {
                // True removal keeps the original journal poison/flush/removal
                // before native erasure. This path never overlaps a startup.
                try await PinkhaHanlinAccountOwner.shared.closeAccount(originalAccount, removeData: removeData)
                // Dispatch real original Stop before joining any retired startup
                // or bootstrap stage. It can cancel native AccountSelect/Create.
                try await OriginalAuthRequestContext.$parent.withValue(stop) {
                    try await base.logout(removeData: removeData)
                }
                await previous?.waitForDrain()
                await bootstrap.quiesceAccountOperations()
                // An operation admitted before retirement may drain after Stop
                // began. Reclose its non-destructive presentation state afterwards.
                try await PinkhaHanlinAccountOwner.shared.closeAccount(originalAccount, removeData: false)
                let finalAccount = accounts.account.id
                if !finalAccount.utf8.elementsEqual(originalAccount.utf8) {
                    try await PinkhaHanlinAccountOwner.shared.closeAccount(finalAccount, removeData: false)
                }
                successfulStopRequired = false
                stop.finishOuter()
                if let originalCaller {
                    await stop.waitForDrain()
                    originalCaller.state.recordCompletedNativeStop()
                    originalEditorStopTask = nil
                }
                if stopping === stop { stopping = nil }
            } catch {
                stop.retire()
                // Do not join a native startup after Stop failed: another Stop
                // must remain admissible to release that retired operation.
                successfulStopRequired = true
                stop.finishOuter()
                if originalCaller != nil {
                    await stop.waitForDrain()
                    originalEditorStopTask = nil
                }
                if stopping === stop { stopping = nil }
                throw error
            }
        }
        if originalCaller != nil { originalEditorStopTask = cleanup }
        try await cleanup.value
        try Task.checkCancellation()
    }

    func deleteAccount() async throws -> AccountStatus {
        let base = base
        let account = accounts.account.id
        return try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.closeAccount(account, removeData: false)
            }
            return try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.deleteAccount() }
        }
    }

    func restoreAccount() async throws -> AccountStatus {
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            let status = try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.restoreAccount() }
            let account = self.accounts.account.id
            try await self.stage(attempt) {
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account)
                }
            }
            return status
        }
    }

    private func stage<Value: Sendable>(
        _ attempt: OriginalAuthAttempt,
        operation: @escaping @Sendable () async throws -> Value
    ) async throws -> Value {
        try requireCurrent(attempt)
        let admissions = try attempt.admitStage()
        defer { for admission in admissions { admission.cancel() } }
        let result = try await operation()
        try requireCurrent(attempt)
        return result
    }

    private func perform<Value: Sendable>(
        kind: OriginalAuthAttempt.Kind,
        operation: @escaping @Sendable (OriginalAuthAttempt) async throws -> Value
    ) async throws -> Value {
        guard current == nil, stopping == nil, !successfulStopRequired else { throw HanlinHostError.staleContext }
        let attempt: OriginalAuthAttempt
        if let caller = try originalEditorAdmissionCaller() {
            attempt = try caller.state.makeAttempt(kind: kind)
        } else {
            attempt = try OriginalAuthAttempt(kind: kind)
        }
        current = attempt
        return try await withTaskCancellationHandler {
            do {
                let result = try await operation(attempt)
                try requireCurrent(attempt)
                attempt.finishOuter()
                if current === attempt { current = nil }
                return result
            } catch {
                attempt.retire()
                attempt.finishOuter()
                await attempt.waitForDrain()
                if current === attempt { current = nil }
                throw error
            }
        } onCancel: { attempt.retire() }
    }

    private func requireCurrent(_ attempt: OriginalAuthAttempt) throws {
        guard current === attempt, stopping == nil else { throw HanlinHostError.staleContext }
        try attempt.validate()
    }
}
