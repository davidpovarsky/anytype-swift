import Foundation
import Combine
import SwiftUI
import ProtobufMessages
import Services
import AnytypeCore

/// Private original-flow restriction. It is never an account capability or a
/// replacement for AccountManager's one frozen account capture.
enum OriginalAuthRequestContext {
    @TaskLocal static var parent: OriginalAuthAttempt?
}

enum OriginalAuthFlowError: Error {
    case busy
    case successfulStopRequired
}

/// One actual original Auth/Hanlin operation. The original Lifetime supplies
/// synchronous retirement, admission and actual-operation drain; no new account
/// generation or asynchronous cancellation flag is introduced.
final class OriginalAuthAttempt: Sendable {
    enum Kind: Equatable, Sendable { case startup, ordinary, stop }
    let kind: Kind
    let captures: [EditorDocumentWriteCapture]
    private let lifetime: EditorDocumentWriteLifetime
    private let outer: EditorDocumentWriteLifetime.Observation
    private let parent: OriginalAuthAttempt?
    private let parentObservations: [EditorDocumentWriteLifetime.Observation]

    init(kind: Kind, parent: OriginalAuthAttempt? = OriginalAuthRequestContext.parent) throws {
        try Task.checkCancellation()
        try parent?.validate()
        let lifetime = EditorDocumentWriteLifetime()
        let capture = try EditorDocumentWriteCapture(lifetime)
        guard let outer = lifetime.admitOperation(capture.token) else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
        self.kind = kind
        self.lifetime = lifetime
        self.outer = outer
        self.parent = parent
        captures = (parent?.captures ?? []) + [capture]
        parentObservations = (parent?.captures ?? []).map { value in
            value.source.observe(value.token) { lifetime.markUnavailable() }
        }
    }

    func validate() throws {
        try Task.checkCancellation()
        for capture in captures { try capture.validate() }
    }

    var isCurrent: Bool {
        captures.allSatisfy { $0.source.isCurrent($0.token) }
    }

    func retire() { lifetime.markUnavailable() }
    func finishOuter() { outer.cancel() }
    func waitForDrain() async { await lifetime.waitForOperationsToDrain() }

    func admitStage() throws -> [EditorDocumentWriteLifetime.Observation] {
        try validate()
        return try EditorDocumentWriteCapture.acquireAll(captures)
    }

    /// Startup native calls are tracked by this exact attempt, not added to the
    /// account-operation drain which AccountStop itself must wait before dispatch.
    func startupBinding(validating: @escaping @Sendable () throws -> Void = {}) -> InvocationDispatchBinding {
        InvocationDispatchBinding(committedEvents: { nil }) { [self] _ in
            try validate()
            try validating()
            return InvocationDispatchPermit { [self] in
                try validate()
                try validating()
                let admissions = try EditorDocumentWriteCapture.acquireAll(captures)
                return InvocationDispatchCompletion {
                    for admission in admissions { admission.cancel() }
                }
            }
        }
    }

    deinit {
        retire()
        finishOuter()
    }
}

/// Constructed only here after the native transition's actual release. It
/// restricts the original subscription sequence; it grants no editor readiness,
/// selected-Space permission, schema authority or identity/body receipt.
final class OriginalAuthStartupSource: Sendable {
    let attempt: OriginalAuthAttempt
    let accountID: String
    private let account: EditorDocumentWriteCapture
    private let manager: any AccountManagerProtocol
    private let userInfo: any BasicUserInfoStorageProtocol
    private let accountRetirement: EditorDocumentWriteLifetime.Observation

    fileprivate init(
        accountID: String,
        attempt: OriginalAuthAttempt,
        manager: any AccountManagerProtocol,
        userInfo: any BasicUserInfoStorageProtocol
    ) throws {
        try attempt.validate()
        guard !accountID.isEmpty,
              manager.account.id.utf8.elementsEqual(accountID.utf8),
              userInfo.usersId.utf8.elementsEqual(accountID.utf8),
              let lifetime = manager.editorWriteLifetime else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
        // Exactly the first capture; no token polling or delayed recapture.
        let account = try EditorDocumentWriteCapture(lifetime)
        self.account = account
        self.accountID = accountID
        self.attempt = attempt
        self.manager = manager
        self.userInfo = userInfo
        accountRetirement = lifetime.observe(account.token) { attempt.retire() }
        try validate()
    }

    func validate() throws {
        try attempt.validate()
        try account.validate()
        guard manager.editorWriteLifetime === account.source,
              manager.account.id.utf8.elementsEqual(accountID.utf8),
              userInfo.usersId.utf8.elementsEqual(accountID.utf8) else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
    }

    var binding: InvocationDispatchBinding {
        attempt.startupBinding { [self] in try validate() }
    }
}

actor AuthService: AuthServiceProtocol, Sendable {
    private let localRepoService: any LocalRepoServiceProtocol = Container.shared.localRepoService()
    private let loginStateService: any LoginStateServiceProtocol = Container.shared.loginStateService()
    private let accountManager: any AccountManagerProtocol = Container.shared.accountManager()
    private let appErrorLoggerConfiguration: any AppErrorLoggerConfigurationProtocol = Container.shared.appErrorLoggerConfiguration()
    private let serverConfigurationStorage: any ServerConfigurationStorageProtocol = Container.shared.serverConfigurationStorage()
    private let authMiddleService: any AuthMiddleServiceProtocol = Container.shared.authMiddleService()
    private let basicUserInfoStorage: any BasicUserInfoStorageProtocol = Container.shared.basicUserInfoStorage()

    private lazy var rootPath: String = { localRepoService.middlewareRepoPath }()
    private var current: OriginalAuthAttempt?
    private var stopping: OriginalAuthAttempt?
    private var successfulStopRequired = false

    private enum StartupRequest: Sendable {
        case create(name: String, iconOption: Int, imagePath: String)
        case select(id: String, preferredSpaceID: String)
        var rpcName: String {
            switch self {
            case .create: return "AccountCreate"
            case .select: return "AccountSelect"
            }
        }
    }

    func createWallet() async throws -> String {
        let service = authMiddleService
        let path = rootPath
        return try await performOrdinaryRPC(rpcNames: ["WalletCreate"]) { _ in
            try await service.createWallet(rootPath: path)
        }
    }

    func walletRecovery(mnemonic: String) async throws {
        let service = authMiddleService
        let path = rootPath
        try await performOrdinaryRPC(rpcNames: ["WalletRecover"]) { _ in
            try await service.walletRecovery(rootPath: path, mnemonic: mnemonic)
        }
    }

    func accountRecover() async throws {
        let service = authMiddleService
        let login = loginStateService
        try await performOrdinaryRPC(rpcNames: ["AccountRecover"]) { attempt in
            try await service.accountRecover()
            try attempt.validate()
            try await login.setupStateAfterAuth(attempt: attempt)
        }
    }

    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        try await startAccount(.create(name: name, iconOption: iconOption, imagePath: imagePath))
    }

    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        try await startAccount(.select(id: id, preferredSpaceID: preferredSpaceId))
    }

    private func startAccount(_ request: StartupRequest) async throws -> AccountData {
        let (attempt, transition) = try begin(kind: .startup, rpcNames: [request.rpcName])
        let start = CFAbsoluteTimeGetCurrent()
        return try await withTaskCancellationHandler {
            do {
                try requireCurrent(attempt)
                try await loginStateService.setupStateBeforeLoginOrAuth(attempt: attempt)
                try requireCurrent(attempt)
                let account = try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
                    switch request {
                    case let .create(name, iconOption, imagePath):
                        return try await authMiddleService.createAccount(
                            name: name, imagePath: imagePath, iconOption: iconOption,
                            networkMode: serverConfigurationStorage.currentConfiguration().middlewareNetworkMode,
                            joinStreamUrl: "",
                            configPath: serverConfigurationStorage.currentConfigurationPath()?.path ?? ""
                        )
                    case let .select(id, preferredSpaceID):
                        return try await authMiddleService.selectAccount(
                            id: id, rootPath: rootPath,
                            networkMode: serverConfigurationStorage.currentConfiguration().middlewareNetworkMode,
                            joinStreamUrl: "",
                            configPath: serverConfigurationStorage.currentConfigurationPath()?.path ?? "",
                            preferredSpaceId: preferredSpaceID
                        )
                    }
                }
                try requireCurrent(attempt)

                let analyticsID = account.info.analyticsId
                AnytypeAnalytics.instance().setUserId(analyticsID)
                AnytypeAnalytics.instance().setNetworkId(account.info.networkId)
                switch request {
                case .create:
                    let middleTime = Int(((CFAbsoluteTimeGetCurrent() - start) * 1_000))
                    AnytypeAnalytics.instance().logAccountCreate(analyticsId: analyticsID, middleTime: middleTime)
                    AnytypeAnalytics.instance().logCreateSpace(spaceAccessType: .private, spaceType: .regular, route: .navigation)
                case .select:
                    AnytypeAnalytics.instance().logAccountOpen(analyticsId: analyticsID)
                }
                await appErrorLoggerConfiguration.setUserId(analyticsID)
                try requireCurrent(attempt)

                if case .select = request, account.status == .deleted {
                    await transition?.finishAndWaitForRelease()
                    try requireCurrent(attempt)
                    // Deleted-account cleanup retires this same startup. End
                    // its outer lease before the LoginState owned drain.
                    attempt.finishOuter()
                    await loginStateService.cleanStateAfterLogout()
                    guard current === attempt, stopping == nil else {
                        throw EditorDocumentWriteError.rejected(.retired)
                    }
                    try Task.checkCancellation()
                    finish(attempt)
                    return account
                }

                guard !account.id.isEmpty else { throw EditorDocumentWriteError.rejected(.retired) }
                basicUserInfoStorage.usersId = account.id
                basicUserInfoStorage.analyticsId = account.info.analyticsId
                accountManager.account = account

                // The original Invocation resumes its Swift caller before the
                // native completion's defer. Wait for the actual release effects.
                await finishAndWait(transition, attempt: attempt, accountID: account.id)
                try requireCurrent(attempt)
                let source = try OriginalAuthStartupSource(
                    accountID: account.id, attempt: attempt,
                    manager: accountManager, userInfo: basicUserInfoStorage
                )
                switch request {
                case .create:
                    try await loginStateService.setupStateAfterRegistration(account: account, source: source)
                case .select:
                    try await loginStateService.setupStateAfterLoginOrAuth(account: account, source: source)
                }
                try requireCurrent(attempt)
                try source.validate()
                finish(attempt)
                return account
            } catch {
                attempt.retire()
                // This actor still owns the same startup; no later auth request
                // can be admitted while it or Stop is cleaning this attempt.
                if current === attempt { accountManager.editorWriteLifetime?.markUnavailable() }
                await transition?.finishAndWaitForRelease()
                attempt.finishOuter()
                await loginStateService.cancelStartup(attempt: attempt)
                await attempt.waitForDrain()
                finish(attempt)
                throw error
            }
        } onCancel: {
            // Covers cancellation before handler installation as well as a
            // callback on another task; no actor hop precedes retirement.
            attempt.retire()
        }
    }

    func logout(removeData: Bool) async throws {
        guard InvocationDispatchContext.binding == nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        guard stopping == nil else { throw OriginalAuthFlowError.busy }
        let previous = current
        if let previous {
            // Preserve the existing destructive overlap rejection. Only the
            // original Back/logout(false) path can cancel a pending startup.
            guard previous.kind == .startup, !removeData else { throw OriginalAuthFlowError.busy }
        }
        let stop = try OriginalAuthAttempt(kind: .stop)
        stopping = stop
        previous?.retire()
        let transition = accountManager.editorWriteLifetime.map {
            EditorAccountWriteTransition(lifetime: $0, rpcNames: ["AccountStop"], attemptCaptures: stop.captures)
        }
        // Once accepted, Stop owns cleanup independently of the caller. A caller
        // cancellation must not revoke the only native RPC that can release the
        // retired startup's AccountSelect/Create callback.
        let cleanup = Task { [self] in
            do {
                // Real original Stop is invoked BEFORE any retired-start drain await.
                // AccountStop(false) may return while that start is still cleaning.
                try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
                    try await authMiddleService.logout(removeData: removeData)
                }
                await previous?.waitForDrain()
                await loginStateService.cleanStateAfterLogout()
                await transition?.finishAndWaitForRelease()
                successfulStopRequired = false
                stop.finishOuter()
                if stopping === stop { stopping = nil }
            } catch {
                stop.retire()
                await transition?.finishAndWaitForRelease()
                // A failed Stop may leave the retired native startup pending.
                // Keep its cleanup owned by that attempt and admit another Stop;
                // joining it here would prevent the retry needed to release it.
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
        let service = authMiddleService
        return try await performOrdinaryRPC(rpcNames: ["AccountDelete"]) { _ in try await service.deleteAccount() }
    }

    func restoreAccount() async throws -> AccountStatus {
        let service = authMiddleService
        return try await performOrdinaryRPC(rpcNames: ["AccountRevertDeletion"]) { _ in try await service.restoreAccount() }
    }

    private func performOrdinaryRPC<Value: Sendable>(
        rpcNames: Set<String>,
        operation: @escaping @Sendable (OriginalAuthAttempt) async throws -> Value
    ) async throws -> Value {
        let (attempt, transition) = try begin(kind: .ordinary, rpcNames: rpcNames)
        return try await withTaskCancellationHandler {
            do {
                let result = try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
                    try await operation(attempt)
                }
                try requireCurrent(attempt)
                await transition?.finishAndWaitForRelease()
                try requireCurrent(attempt)
                finish(attempt)
                return result
            } catch {
                attempt.retire()
                await transition?.finishAndWaitForRelease()
                attempt.finishOuter()
                await attempt.waitForDrain()
                finish(attempt)
                throw error
            }
        } onCancel: { attempt.retire() }
    }

    private func begin(kind: OriginalAuthAttempt.Kind, rpcNames: Set<String>) throws -> (OriginalAuthAttempt, EditorAccountWriteTransition?) {
        guard InvocationDispatchContext.binding == nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        guard current == nil, stopping == nil else { throw OriginalAuthFlowError.busy }
        guard !successfulStopRequired else { throw OriginalAuthFlowError.successfulStopRequired }
        let accountLifetime = accountManager.editorWriteLifetime
        if kind == .startup, accountLifetime == nil {
            // A replacement provider without the original account lifetime
            // cannot begin this capture-qualified startup.
            throw EditorDocumentWriteError.rejected(.retired)
        }
        let attempt = try OriginalAuthAttempt(kind: kind)
        let transition = accountLifetime.map {
            EditorAccountWriteTransition(lifetime: $0, rpcNames: rpcNames, attemptCaptures: attempt.captures)
        }
        current = attempt
        return (attempt, transition)
    }

    private func requireCurrent(_ attempt: OriginalAuthAttempt) throws {
        guard current === attempt, stopping == nil else { throw EditorDocumentWriteError.rejected(.retired) }
        try attempt.validate()
    }

    private func finish(_ attempt: OriginalAuthAttempt) {
        attempt.finishOuter()
        if current === attempt { current = nil }
    }

    private func finishAndWait(_ transition: EditorAccountWriteTransition?, attempt: OriginalAuthAttempt, accountID: String) async {
        let manager = accountManager
        let userInfo = basicUserInfoStorage
        await transition?.finishAndWaitForRelease {
            attempt.isCurrent && !accountID.isEmpty &&
                manager.account.id.utf8.elementsEqual(accountID.utf8) &&
                userInfo.usersId.utf8.elementsEqual(accountID.utf8)
        }
    }

    func mnemonicByEntropy(_ entropy: String) async throws -> String {
        try await authMiddleService.mnemonicByEntropy(entropy)
    }
}
