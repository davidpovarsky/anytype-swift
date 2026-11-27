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
    private var bootstrap: any PinkhaSpaceBootstrapServiceProtocol {
        #if DEBUG
        if let acceptanceOwners { return acceptanceOwners.bootstrap }
        #endif
        return Container.shared.pinkhaBootstrapService()
    }
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

    #if DEBUG
    /// Component-test effects only. The actual decorator/attempt/stage/Stop
    /// implementations remain the subject; this does not qualify a native account.
    struct AcceptanceOwners: Sendable {
        let accountManager: AccountManager
        let bootstrap: any PinkhaSpaceBootstrapServiceProtocol
        let prepareMiniApps: @Sendable () async throws -> UUID
        let resumeMiniApps: @MainActor @Sendable (UUID) -> Void
        let prepareEngine: @Sendable () async throws -> Void
        let closeSharing: @Sendable () async -> Void
        let openSharing: @Sendable (String) async throws -> Void
        let closeHanlin: @Sendable (String, Bool) async throws -> Void
        let beforeHanlinPublication: @Sendable () async -> Void
        let openHanlin: @MainActor @Sendable (String) throws -> Void
    }

    private var acceptanceOwners: AcceptanceOwners?

    init(base: any AuthServiceProtocol, acceptanceOwners: AcceptanceOwners) {
        self.base = base
        self.acceptanceOwners = acceptanceOwners
    }
    #endif

    private var originalAccountID: String {
        #if DEBUG
        if let acceptanceOwners { return acceptanceOwners.accountManager.account.id }
        #endif
        return accounts.account.id
    }

    private func closeSharingAccount() async {
        #if DEBUG
        if let acceptanceOwners { await acceptanceOwners.closeSharing(); return }
        #endif
        await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
    }

    private func closeHanlinAccount(_ account: String, removeData: Bool) async throws {
        #if DEBUG
        if let acceptanceOwners { try await acceptanceOwners.closeHanlin(account, removeData); return }
        #endif
        try await PinkhaHanlinAccountOwner.shared.closeAccount(account, removeData: removeData)
    }

    func createWallet() async throws -> String {
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            try await self.stage(attempt) { await self.closeSharingAccount() }
            return try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.createWallet() }
        }
    }

    func walletRecovery(mnemonic: String) async throws {
        let base = base
        try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            try await self.stage(attempt) { await self.closeSharingAccount() }
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.walletRecovery(mnemonic: mnemonic) }
        }
    }

    func accountRecover() async throws {
        let base = base
        try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            try await self.stage(attempt) { await self.closeSharingAccount() }
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.accountRecover() }
        }
    }

    func mnemonicByEntropy(_ entropy: String) async throws -> String {
        try await base.mnemonicByEntropy(entropy)
    }

    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        let base = base
        let bootstrap = bootstrap
        let previousAccount = originalAccountID
        return try await perform(kind: .startup) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            try await self.stage(attempt) { await self.closeSharingAccount() }
            try await self.stage(attempt) {
                try await self.closeHanlinAccount(previousAccount, removeData: false)
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
        let previousAccount = originalAccountID
        return try await perform(kind: .startup) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            #if PINKHA_NATIVE_DERIVED && targetEnvironment(simulator)
            try await self.stage(attempt) {
                try PinkhaTypePreservationLaunchProof.captureBeforeAccountSelect(accountID: id)
            }
            #endif
            try await self.stage(attempt) { await self.closeSharingAccount() }
            try await self.stage(attempt) {
                try await self.closeHanlinAccount(previousAccount, removeData: false)
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
        let originalAccount = originalAccountID
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
                await self.closeSharingAccount()
                // Preserve journal revocation/removal before native data erasure.
                try await closeHanlinAccount(originalAccount, removeData: removeData)
                // Real Stop precedes the retired startup and Bootstrap drain: it
                // may be the operation that releases AccountSelect/Create.
                try await OriginalAuthRequestContext.$parent.withValue(stop) {
                    try await base.logout(removeData: removeData)
                }
                await previous?.waitForDrain()
                await bootstrap.quiesceAccountOperations()
                // A presentation stage admitted before retirement can finish
                // late. Close its actual original state after that exact drain.
                await self.closeSharingAccount()
                try await closeHanlinAccount(originalAccount, removeData: false)
                let finalAccount = originalAccountID
                if !finalAccount.utf8.elementsEqual(originalAccount.utf8) {
                    try await closeHanlinAccount(finalAccount, removeData: false)
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
        let account = originalAccountID
        return try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            try await self.stage(attempt) { await self.closeSharingAccount() }
            try await self.stage(attempt) {
                try await self.closeHanlinAccount(account, removeData: false)
            }
            return try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.deleteAccount() }
        }
    }

    func restoreAccount() async throws -> AccountStatus {
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) { try await self.prepareEngineAccountChange(attempt) }
            let status = try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.restoreAccount() }
            let account = await self.originalAccountID
            try await self.publishAccount(account, for: attempt)
            return status
        }
    }

    private func publishAccount(_ account: String, for attempt: OriginalAuthAttempt) async throws {
        try requireCurrent(attempt)
        guard accountPublication == nil else { throw HanlinHostError.staleContext }
        #if DEBUG
        let acceptanceOwners = acceptanceOwners
        #endif
        let task = Task<Void, Error> { [self] in
            try await stage(attempt) {
                #if DEBUG
                // Pause only the original incoming MainActor publication hop.
                // Retirement is still checked inside that actual hop below.
                await acceptanceOwners?.beforeHanlinPublication()
                #endif
                // Retain the original same-turn MainActor check: retirement can
                // happen after a caller queues this hop but before it executes.
                try await MainActor.run {
                    try attempt.validate()
                    #if DEBUG
                    if let acceptanceOwners { try acceptanceOwners.openHanlin(account); return }
                    #endif
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account)
                }
            }
            try await stage(attempt) {
                #if DEBUG
                if let acceptanceOwners { try await acceptanceOwners.openSharing(account); return }
                #endif
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
        let token: UUID
        #if DEBUG
        if let acceptanceOwners {
            token = try await acceptanceOwners.prepareMiniApps()
        } else {
            token = try await PinkhaMiniAppsCoordinator.shared.prepareEngineAccountChange()
        }
        #else
        token = try await PinkhaMiniAppsCoordinator.shared.prepareEngineAccountChange()
        #endif
        // Retain the returned real hold even if Stop retired this attempt during
        // the await. Only the final idle/successful boundary may release it.
        miniAppsChangeTokens.insert(token)
        try requirePreparationOwner(attempt)
        #if PINKHA_DUAL_ENGINE_RUNTIME
        #if DEBUG
        if let acceptanceOwners { try await acceptanceOwners.prepareEngine() }
        else { try await PinkhaEngineSceneOwner.shared.prepareHeartAccountChange() }
        #else
        try await PinkhaEngineSceneOwner.shared.prepareHeartAccountChange()
        #endif
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
        #if DEBUG
        let acceptanceOwners = acceptanceOwners
        #endif
        Task { @MainActor in
            for token in tokens {
                #if DEBUG
                if let acceptanceOwners { acceptanceOwners.resumeMiniApps(token); continue }
                #endif
                PinkhaMiniAppsCoordinator.shared.resumeAfterAccountChange(token)
            }
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
