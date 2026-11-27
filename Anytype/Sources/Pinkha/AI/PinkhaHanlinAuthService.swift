import PinkhaHanlinCore
import PinkhaSharing
import Foundation
import Factory
import Services
import HanlinHostContracts

/// Native Auth remains the single account owner. The original attempt lifetime
/// restricts this decorator's stages and admits the original Back/logout(false).
/// The existing remove-data choice remains the sole metadata-erasure authority.
actor PinkhaHanlinAuthService: AuthServiceProtocol {
    private let base: any AuthServiceProtocol
    private let accounts = Container.shared.accountManager()
    private var bootstrap: any PinkhaSpaceBootstrapServiceProtocol { Container.shared.pinkhaBootstrapService() }
    private var current: OriginalAuthAttempt?
    private var stopping: OriginalAuthAttempt?
    private var successfulStopRequired = false
    private var miniAppsChangeTokens = Set<UUID>()
    private var accountPublication: AccountPublication?

    /// Ownership of the actual existing presentation-open calls, not an account
    /// capability. Stop may join this task without waiting for native startup.
    private final class AccountPublication: Sendable {
        let attempt: OriginalAuthAttempt
        let task: Task<Void, Error>

        init(attempt: OriginalAuthAttempt, task: Task<Void, Error>) {
            self.attempt = attempt
            self.task = task
        }
    }

    init(base: any AuthServiceProtocol) { self.base = base }

    func createWallet() async throws -> String {
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            try await self.stage(attempt) { await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart) }
            return try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.createWallet() }
        }
    }

    func walletRecovery(mnemonic: String) async throws {
        let base = base
        try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            try await self.stage(attempt) { await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart) }
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.walletRecovery(mnemonic: mnemonic) }
        }
    }

    func accountRecover() async throws {
        let base = base
        try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            try await self.stage(attempt) { await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart) }
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.accountRecover() }
        }
    }

    func mnemonicByEntropy(_ entropy: String) async throws -> String {
        try await base.mnemonicByEntropy(entropy)
    }

    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        let base = base
        let bootstrap = bootstrap
        let previousAccount = accounts.account.id
        return try await perform(kind: .startup) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            try await self.stage(attempt) { await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart) }
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
            try await self.publishAccount(account.id, for: attempt)
            return account
        }
    }

    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        let base = base
        let bootstrap = bootstrap
        let previousAccount = accounts.account.id
        return try await perform(kind: .startup) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            #if PINKHA_NATIVE_DERIVED && targetEnvironment(simulator)
            try await self.stage(attempt) {
                try PinkhaTypePreservationLaunchProof.captureBeforeAccountSelect(accountID: id)
            }
            #endif
            try await self.stage(attempt) { await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart) }
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
            try await self.publishAccount(account.id, for: attempt)
            return account
        }
    }

    func logout(removeData: Bool) async throws {
        guard stopping == nil else { throw HanlinHostError.staleContext }
        let previous = current
        if let previous {
            // Only the original Back route may supersede an in-progress startup.
            // Native removal and unrelated account operations remain serialized.
            guard previous.kind == .startup, !removeData else { throw HanlinHostError.staleContext }
        }
        let pendingPublication = accountPublication
        if let pendingPublication {
            guard pendingPublication.attempt === previous else { throw HanlinHostError.staleContext }
        }
        let stop = try OriginalAuthAttempt(kind: .stop)
        stopping = stop
        previous?.retire()
        let originalAccount = accounts.account.id
        let bootstrap = bootstrap
        // Once accepted, this original Stop must outlive its UI caller. Retiring
        // the parent above also prevents a queued child startup from dispatching.
        let cleanup = Task { [self] in
            do {
                // A queued owner-open call must finish before the first close.
                // This task contains only Hanlin/Sharing publication, never the
                // native startup or Bootstrap work that real Stop must release.
                _ = await pendingPublication?.task.result
                try await prepareEngineAccountChange(stop)
                await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
                // Preserve journal revocation/removal before native data erasure.
                try await PinkhaHanlinAccountOwner.shared.closeAccount(originalAccount, removeData: removeData)
                // Real Stop precedes the retired startup and Bootstrap drain: it
                // may be the operation that releases AccountSelect/Create.
                try await OriginalAuthRequestContext.$parent.withValue(stop) {
                    try await base.logout(removeData: removeData)
                }
                await previous?.waitForDrain()
                await bootstrap.quiesceAccountOperations()
                // A presentation stage admitted before retirement can finish
                // late. Close its actual original state after that exact drain.
                await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
                try await PinkhaHanlinAccountOwner.shared.closeAccount(originalAccount, removeData: false)
                let finalAccount = accounts.account.id
                if !finalAccount.utf8.elementsEqual(originalAccount.utf8) {
                    try await PinkhaHanlinAccountOwner.shared.closeAccount(finalAccount, removeData: false)
                }
                successfulStopRequired = false
                stop.finishOuter()
                if stopping === stop { stopping = nil }
                resumeMiniAppsIfIdle()
            } catch {
                stop.retire()
                // A failed native Stop may still need an explicit retry to
                // release startup. Keep all real MiniApps holds and reject new
                // account work; do not wait for that startup before admitting retry.
                successfulStopRequired = true
                stop.finishOuter()
                if stopping === stop { stopping = nil }
                throw error
            }
        }
        try await cleanup.value
        try Task.checkCancellation()
    }

    func deleteAccount() async throws -> AccountStatus {
        let base = base
        let account = accounts.account.id
        return try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            try await self.stage(attempt) { await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart) }
            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.closeAccount(account, removeData: false)
            }
            return try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.deleteAccount() }
        }
    }

    func restoreAccount() async throws -> AccountStatus {
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            let status = try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.restoreAccount() }
            let account = self.accounts.account.id
            try await self.publishAccount(account, for: attempt)
            return status
        }
    }

    private func publishAccount(_ account: String, for attempt: OriginalAuthAttempt) async throws {
        try requireCurrent(attempt)
        guard accountPublication == nil else { throw HanlinHostError.staleContext }
        let task = Task<Void, Error> { [self] in
            try await stage(attempt) {
                // Retain the original same-turn MainActor check: retirement can
                // happen after a caller queues this hop but before it executes.
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account)
                }
            }
            try await stage(attempt) {
                try await PinkhaSharingAccountOwner.shared.didOpen(engine: .heart, accountID: account)
            }
        }
        let publication = AccountPublication(attempt: attempt, task: task)
        // No suspension precedes registration. A Stop sees this exact task or
        // sets stopping first, after which requireCurrent rejects registration.
        accountPublication = publication
        defer { if accountPublication === publication { accountPublication = nil } }
        try await task.value
        try requireCurrent(attempt)
    }

    private func prepareEngineAccountChange(_ attempt: OriginalAuthAttempt) async throws {
        try requirePreparationOwner(attempt)
        let token = try await PinkhaMiniAppsCoordinator.shared.prepareEngineAccountChange()
        // Retain the returned real hold even if Stop retired this attempt during
        // the await. Only the final idle/successful boundary may release it.
        miniAppsChangeTokens.insert(token)
        try requirePreparationOwner(attempt)
        #if PINKHA_DUAL_ENGINE_RUNTIME
        try await PinkhaEngineSceneOwner.shared.prepareHeartAccountChange()
        #endif
        try requirePreparationOwner(attempt)
    }

    private func requirePreparationOwner(_ attempt: OriginalAuthAttempt) throws {
        if attempt.kind == .stop {
            guard stopping === attempt else { throw HanlinHostError.staleContext }
            try attempt.validate()
        } else {
            try requireCurrent(attempt)
        }
    }

    private func resumeMiniAppsIfIdle() {
        guard current == nil, stopping == nil, !successfulStopRequired,
              !miniAppsChangeTokens.isEmpty else { return }
        let tokens = miniAppsChangeTokens
        miniAppsChangeTokens.removeAll()
        Task { @MainActor in
            for token in tokens { PinkhaMiniAppsCoordinator.shared.resumeAfterAccountChange(token) }
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
        let attempt = try OriginalAuthAttempt(kind: kind)
        current = attempt
        return try await withTaskCancellationHandler {
            do {
                let result = try await operation(attempt)
                try requireCurrent(attempt)
                attempt.finishOuter()
                if current === attempt { current = nil }
                resumeMiniAppsIfIdle()
                return result
            } catch {
                attempt.retire()
                attempt.finishOuter()
                await attempt.waitForDrain()
                if current === attempt { current = nil }
                resumeMiniAppsIfIdle()
                throw error
            }
        } onCancel: { attempt.retire() }
    }

    private func requireCurrent(_ attempt: OriginalAuthAttempt) throws {
        guard current === attempt, stopping == nil else { throw HanlinHostError.staleContext }
        try attempt.validate()
    }
}
