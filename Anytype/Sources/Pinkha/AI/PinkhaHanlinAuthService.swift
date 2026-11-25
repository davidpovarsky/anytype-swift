import PinkhaHanlinCore
import PinkhaSharing
import Foundation
import Factory
import Services
import HanlinHostContracts

/// Thin downstream decorator: native authentication remains the single authentication owner.
/// The existing remove-data choice is also the sole authority to erase Hanlin host metadata.
actor PinkhaHanlinAuthService: AuthServiceProtocol {
    private let base: any AuthServiceProtocol
    private let accounts = Container.shared.accountManager()
    private var bootstrap: any PinkhaSpaceBootstrapServiceProtocol { Container.shared.pinkhaBootstrapService() }
    private var changingAccount = false
    private var miniAppsChangeToken: UUID?

    init(base: any AuthServiceProtocol) { self.base = base }

    func createWallet() async throws -> String {
        try beginAccountChange(); defer { finishAccountChange() }
        try await prepareEngineAccountChange()
        await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
        return try await base.createWallet()
    }
    func walletRecovery(mnemonic: String) async throws {
        try beginAccountChange(); defer { finishAccountChange() }
        try await prepareEngineAccountChange()
        await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
        try await base.walletRecovery(mnemonic: mnemonic)
    }
    func accountRecover() async throws {
        try beginAccountChange(); defer { finishAccountChange() }
        try await prepareEngineAccountChange()
        await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
        try await base.accountRecover()
    }
    func mnemonicByEntropy(_ entropy: String) async throws -> String { try await base.mnemonicByEntropy(entropy) }

    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        try beginAccountChange(); defer { finishAccountChange() }
        try await prepareEngineAccountChange()
        await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
        try await PinkhaHanlinAccountOwner.shared.closeAccount(accounts.account.id, removeData: false)
        await bootstrap.quiesceAccountOperations()
        let account = try await base.createAccount(name: name, iconOption: iconOption, imagePath: imagePath)
        try await bootstrap.resumeAccountOperations()
        try await PinkhaHanlinAccountOwner.shared.accountDidOpen(account.id)
        try await PinkhaSharingAccountOwner.shared.didOpen(engine: .heart, accountID: account.id)
        return account
    }

    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        try beginAccountChange(); defer { finishAccountChange() }
        try await prepareEngineAccountChange()
        #if PINKHA_NATIVE_DERIVED && targetEnvironment(simulator)
        try PinkhaTypePreservationLaunchProof.captureBeforeAccountSelect(accountID: id)
        #endif
        await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
        try await PinkhaHanlinAccountOwner.shared.closeAccount(accounts.account.id, removeData: false)
        await bootstrap.quiesceAccountOperations()
        let account = try await base.selectAccount(id: id, preferredSpaceId: preferredSpaceId)
        try await bootstrap.resumeAccountOperations()
        try await PinkhaHanlinAccountOwner.shared.accountDidOpen(account.id)
        try await PinkhaSharingAccountOwner.shared.didOpen(engine: .heart, accountID: account.id)
        return account
    }

    func logout(removeData: Bool) async throws {
        try beginAccountChange(); defer { finishAccountChange() }
        try await prepareEngineAccountChange()
        await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
        try await PinkhaHanlinAccountOwner.shared.closeAccount(accounts.account.id, removeData: removeData)
        await bootstrap.quiesceAccountOperations()
        try await base.logout(removeData: removeData)
    }

    func deleteAccount() async throws -> AccountStatus {
        try beginAccountChange(); defer { finishAccountChange() }
        try await prepareEngineAccountChange()
        await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
        try await PinkhaHanlinAccountOwner.shared.closeAccount(accounts.account.id, removeData: false)
        return try await base.deleteAccount()
    }

    func restoreAccount() async throws -> AccountStatus {
        try beginAccountChange(); defer { finishAccountChange() }
        try await prepareEngineAccountChange()
        let status = try await base.restoreAccount()
        try await PinkhaHanlinAccountOwner.shared.accountDidOpen(accounts.account.id)
        try await PinkhaSharingAccountOwner.shared.didOpen(engine: .heart, accountID: accounts.account.id)
        return status
    }

    private func prepareEngineAccountChange() async throws {
        miniAppsChangeToken = try await PinkhaMiniAppsCoordinator.shared.prepareEngineAccountChange()
        #if PINKHA_DUAL_ENGINE_RUNTIME
        try await PinkhaEngineSceneOwner.shared.prepareHeartAccountChange()
        #endif
    }

    private func finishAccountChange() {
        changingAccount = false
        guard let token = miniAppsChangeToken else { return }
        miniAppsChangeToken = nil
        Task { @MainActor in
            PinkhaMiniAppsCoordinator.shared.resumeAfterAccountChange(token)
        }
    }

    private func beginAccountChange() throws {
        // Actor reentrancy must not select another account while removal awaits journal flushing,
        // then let the original logout act on that newly selected account.
        guard !changingAccount else { throw HanlinHostError.staleContext }
        changingAccount = true
    }
}
