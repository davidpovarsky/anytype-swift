import SwiftUI
@preconcurrency import Combine
import AnytypeCore
import Services
import DeepLinks

@MainActor
@Observable
final class ApplicationCoordinatorViewModel {

    @Injected(\.authService) @ObservationIgnored
    private var authService: any AuthServiceProtocol
    @Injected(\.accountEventHandler) @ObservationIgnored
    private var accountEventHandler: any AccountEventHandlerProtocol
    @Injected(\.encryptionKeyEventHandler) @ObservationIgnored
    private var encryptionKeyEventHandler: any EncryptionKeyEventHandlerProtocol
    @Injected(\.applicationStateService) @ObservationIgnored
    private var applicationStateService: any ApplicationStateServiceProtocol
    @Injected(\.accountManager) @ObservationIgnored
    private var accountManager: any AccountManagerProtocol
    @Injected(\.seedService) @ObservationIgnored
    private var seedService: any SeedServiceProtocol
    @Injected(\.fileErrorEventHandler) @ObservationIgnored
    private var fileErrorEventHandler: any FileErrorEventHandlerProtocol
    @Injected(\.basicUserInfoStorage) @ObservationIgnored
    private var basicUserInfoStorage: any BasicUserInfoStorageProtocol
    @Injected(\.pushNotificationsPermissionService) @ObservationIgnored
    private var pushNotificationsPermissionService: any PushNotificationsPermissionServiceProtocol
    @Injected(\.appActionStorage) @ObservationIgnored
    private var appActionStorage: AppActionStorage

    @ObservationIgnored
    private var dismissAllPresented: DismissAllPresented?
    
    // MARK: - State
    
    var applicationState: ApplicationState = .initial
    var toastBarData: ToastBarData?
    var migrationData: MigrationModuleData?
    var selectAccountTaskId: String?

    func deleteAccount() -> AnyView? {
        if case let .pendingDeletion(deadline) = accountManager.account.status {
            return DeletedAccountView(deadline: deadline).eraseToAnyView()
        } else {
            applicationStateService.state = .initial
            return nil
        }

    }
    
    func setDismissAllPresented(dismissAllPresented: DismissAllPresented) {
        self.dismissAllPresented = dismissAllPresented
    }
    
    func startAppStateHandler() async {
        observeUI27Startup("state-consumer-start")
        for await state in applicationStateService.statePublisher.removeDuplicates().values {
            observeUI27Startup("state-consumed-entry", consumed: state)
            await handleApplicationState(state)
            observeUI27Startup("state-consumed-exit", consumed: state)
        }
        observeUI27Startup("state-consumer-ended")
    }
    
    func startAccountStateHandler() async {
        for await status in await accountEventHandler.accountStatusPublisher.values {
            await handleAccountStatus(status)
        }
    }
    
    func startEncryptionKeyEventHandler() async  {
        await encryptionKeyEventHandler.startSubscription()
    }

    func startFileHandler() async {
        for await _ in await fileErrorEventHandler.fileLimitReachedPublisher.values {
            handleFileLimitReachedError()
        }
    }
    
    // MARK: - Subscription handler

    private func handleAccountStatus(_ status: AccountStatus) async {
        switch status {
        case .active:
            break
        case .pendingDeletion:
            applicationStateService.state = .delete
        case .deleted:
            if basicUserInfoStorage.usersId.isNotEmpty {
                try? await authService.logout(removeData: true)
                applicationStateService.state = .auth
            }
        }
    }
    
    private func handleApplicationState(_ applicationState: ApplicationState) async {
        await dismissAllPresented?(animated: false)
        withAnimation(self.applicationState == .launch ? .default : .none) {
            self.applicationState = applicationState
        }
        
        switch applicationState {
        case .initial:
            break
        case .launch:
            await loginProcess()
        case .home:
            break
        case .auth:
            break
        case .delete:
            break
        }
    }
    
    // MARK: - Process

    private func loginProcess() async {
        observeUI27Startup("login-entry")
        let userId = basicUserInfoStorage.usersId
        guard userId.isNotEmpty else {
            observeUI27Startup("login-account-absent")
            applicationStateService.state = .auth
            return
        }

        do {
            observeUI27Startup("seed-read-begin")
            let seed = try seedService.obtainSeed()
            observeUI27Startup("seed-read-completed")
            observeUI27Startup("wallet-recovery-begin")
            try await authService.walletRecovery(mnemonic: seed)
            observeUI27Startup("wallet-recovery-completed")
            observeUI27Startup("select-call-begin")
            await selectAccount(id: userId)
            observeUI27Startup("select-call-returned")
        } catch {
            observeUI27Startup("login-error", error: error)
            applicationStateService.state = .auth
            observeUI27Startup("login-auth-assigned")
        }
    }
    
    func selectAccount(id: String) async {
        do {
            observeUI27Startup("select-auth-begin")
            let account = try await authService.selectAccount(id: id, preferredSpaceId: preferredSpaceId())
            observeUI27Startup("select-auth-returned")
            
            switch account.status {
            case .active:
                applicationStateService.state = .home
            case .pendingDeletion:
                applicationStateService.state = .delete
            case .deleted:
                applicationStateService.state = .auth
            }
            observeUI27Startup("select-state-assigned")
            
            observeUI27Startup("notification-registration-begin")
            await pushNotificationsPermissionService.registerForRemoteNotificationsIfNeeded()
            observeUI27Startup("notification-registration-returned")
        } catch is CancellationError {
            observeUI27Startup("select-cancellation")
            // Ignore cancellations
        } catch SelectAccountError.accountStoreNotMigrated {
            observeUI27Startup("select-store-not-migrated")
            migrationData = MigrationModuleData(
                id: id,
                onFinish: { [weak self] in
                    self?.selectAccountTaskId = id
                }
            )
        } catch {
            observeUI27Startup("select-error", error: error)
            applicationStateService.state = .auth
            observeUI27Startup("select-auth-assigned")
        }
    }

    private func observeUI27Startup(_ phase: String, consumed: ApplicationState? = nil, error: Error? = nil) {
        guard PinkhaUI27StartupDiagnostics.isEnabled else { return }
        PinkhaUI27StartupDiagnostics.record(phase, consumed: consumed, model: applicationState,
            service: applicationStateService.state, errorType: error.map { String(reflecting: type(of: $0)) },
            taskCancelled: Task.isCancelled)
    }

    // Space the middleware should load eagerly on AccountSelect, the rest are deferred.
    // A pending deeplink (url or push notification tap) is the only known cold start destination —
    // without one the app opens the Space Hub, so no space is preferred.
    private func preferredSpaceId() -> String {
        guard FeatureFlags.preferredSpaceOnColdStart,
              case let .deepLink(deepLink, _) = appActionStorage.action else { return "" }
        return deepLink.spaceId ?? ""
    }

    private func handleFileLimitReachedError() {
        toastBarData = ToastBarData(Loc.FileStorage.limitError, type: .neutral)
    }
}
