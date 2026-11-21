import Foundation
import Combine
import SwiftUI
import ProtobufMessages
import Services
import AnytypeCore

actor AuthService: AuthServiceProtocol, Sendable {
    
    private let localRepoService: any LocalRepoServiceProtocol = Container.shared.localRepoService()
    private let loginStateService: any LoginStateServiceProtocol = Container.shared.loginStateService()
    private let accountManager: any AccountManagerProtocol = Container.shared.accountManager()
    private let appErrorLoggerConfiguration: any AppErrorLoggerConfigurationProtocol = Container.shared.appErrorLoggerConfiguration()
    private let serverConfigurationStorage: any ServerConfigurationStorageProtocol = Container.shared.serverConfigurationStorage()
    private let authMiddleService: any AuthMiddleServiceProtocol = Container.shared.authMiddleService()
    private let basicUserInfoStorage: any BasicUserInfoStorageProtocol = Container.shared.basicUserInfoStorage()

    private lazy var rootPath: String = {
        localRepoService.middlewareRepoPath
    }()
    
    func logout(removeData: Bool) async throws  {
        let transition = try beginEditorAccountTransition(rpcNames: ["AccountStop"])
        defer { finishEditorAccountTransition(transition) }
        try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
            try await authMiddleService.logout(removeData: removeData)
        }
        await loginStateService.cleanStateAfterLogout()
    }

    func createWallet() async throws -> String {
        let transition = try beginEditorAccountTransition(rpcNames: ["WalletCreate"])
        defer { finishEditorAccountTransition(transition) }
        return try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
            try await authMiddleService.createWallet(rootPath: rootPath)
        }
    }

    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        let transition = try beginEditorAccountTransition(rpcNames: ["AccountCreate"])
        var verifiedAccountID: String?
        defer { finishEditorAccountTransition(transition, verifiedAccountID: verifiedAccountID) }
        let start = CFAbsoluteTimeGetCurrent()
        
        await loginStateService.setupStateBeforeLoginOrAuth()
        
        let account = try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
            try await authMiddleService.createAccount(
                name: name,
                imagePath: imagePath,
                iconOption: iconOption,
                networkMode: serverConfigurationStorage.currentConfiguration().middlewareNetworkMode,
                joinStreamUrl: "",
                configPath: serverConfigurationStorage.currentConfigurationPath()?.path ?? ""
            )
        }

        let middleTime = Int(((CFAbsoluteTimeGetCurrent() - start) * 1_000)) // milliseconds
        
        let analyticsId = account.info.analyticsId
        AnytypeAnalytics.instance().setUserId(analyticsId)
        AnytypeAnalytics.instance().setNetworkId(account.info.networkId)
        AnytypeAnalytics.instance().logAccountCreate(analyticsId: analyticsId, middleTime: middleTime)
        AnytypeAnalytics.instance().logCreateSpace(spaceAccessType: .private, spaceType: .regular, route: .navigation)
        await appErrorLoggerConfiguration.setUserId(analyticsId)
        
        basicUserInfoStorage.usersId = account.id
        basicUserInfoStorage.analyticsId = account.info.analyticsId
        
        accountManager.account = account
        
        await loginStateService.setupStateAfterRegistration(account: account)
        verifiedAccountID = account.id
        return account
    }
    
    func walletRecovery(mnemonic: String) async throws {
        let transition = try beginEditorAccountTransition(rpcNames: ["WalletRecover"])
        defer { finishEditorAccountTransition(transition) }
        try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
            try await authMiddleService.walletRecovery(rootPath: rootPath, mnemonic: mnemonic)
        }
    }

    func accountRecover() async throws {
        let transition = try beginEditorAccountTransition(rpcNames: ["AccountRecover"])
        defer { finishEditorAccountTransition(transition) }
        try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
            try await authMiddleService.accountRecover()
        }
        await loginStateService.setupStateAfterAuth()
    }
    
    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        let transition = try beginEditorAccountTransition(rpcNames: ["AccountSelect"])
        var verifiedAccountID: String?
        defer { finishEditorAccountTransition(transition, verifiedAccountID: verifiedAccountID) }
        await loginStateService.setupStateBeforeLoginOrAuth()

        let account = try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
            try await authMiddleService.selectAccount(
                id: id,
                rootPath: rootPath,
                networkMode: serverConfigurationStorage.currentConfiguration().middlewareNetworkMode,
                joinStreamUrl: "",
                configPath: serverConfigurationStorage.currentConfigurationPath()?.path ?? "",
                preferredSpaceId: preferredSpaceId
            )
        }
        
        let analyticsId = account.info.analyticsId
        AnytypeAnalytics.instance().setUserId(analyticsId)
        AnytypeAnalytics.instance().setNetworkId(account.info.networkId)
        AnytypeAnalytics.instance().logAccountOpen(analyticsId: analyticsId)
        await appErrorLoggerConfiguration.setUserId(analyticsId)
        
        switch account.status {
        case .active, .pendingDeletion:
            await setupAccountData(account)
            verifiedAccountID = account.id
        case .deleted:
            await loginStateService.cleanStateAfterLogout()
        }
        
        return account
    }
    
    private func setupAccountData(_ account: AccountData) async {
        basicUserInfoStorage.usersId = account.id
        basicUserInfoStorage.analyticsId = account.info.analyticsId
        
        accountManager.account = account
        await loginStateService.setupStateAfterLoginOrAuth(account: accountManager.account)
    }
    
    func deleteAccount() async throws -> AccountStatus {
        let transition = try beginEditorAccountTransition(rpcNames: ["AccountDelete"])
        defer { finishEditorAccountTransition(transition) }
        return try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
            try await authMiddleService.deleteAccount()
        }
    }
    
    func restoreAccount() async throws -> AccountStatus {
        let transition = try beginEditorAccountTransition(rpcNames: ["AccountRevertDeletion"])
        defer { finishEditorAccountTransition(transition) }
        return try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
            try await authMiddleService.restoreAccount()
        }
    }
    
    private func beginEditorAccountTransition(rpcNames: Set<String>) throws -> EditorAccountWriteTransition? {
        // A document/read capability cannot be promoted into account control.
        guard InvocationDispatchContext.binding == nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        return accountManager.editorWriteLifetime.map {
            EditorAccountWriteTransition(lifetime: $0, rpcNames: rpcNames)
        }
    }

    private func finishEditorAccountTransition(
        _ transition: EditorAccountWriteTransition?,
        verifiedAccountID: String? = nil
    ) {
        let mayConfirm = !Task.isCancelled
        let manager = accountManager
        let userInfo = basicUserInfoStorage
        transition?.finish {
            guard mayConfirm, let expected = verifiedAccountID, !expected.isEmpty else { return false }
            return manager.account.id.utf8.elementsEqual(expected.utf8)
                && userInfo.usersId.utf8.elementsEqual(expected.utf8)
        }
    }

    func mnemonicByEntropy(_ entropy: String) async throws -> String {
        try await authMiddleService.mnemonicByEntropy(entropy)
    }
}
