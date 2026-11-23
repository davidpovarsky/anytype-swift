import SwiftUI
@preconcurrency import Combine
import AnytypeCore
import Services
import DeepLinks

@MainActor
@Observable
final class ApplicationCoordinatorViewModel {

    @ObservationIgnored
    let originalEditorCaller: OriginalEditorAuthCaller?

    init(originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        self.originalEditorCaller = originalEditorCaller
    }

    private var originalAuthService: any AuthServiceProtocol {
        if let originalEditorCaller { return originalEditorCaller }
        return authService
    }

    private var acceptsOriginalUI: Bool { originalEditorCaller?.isCurrent ?? true }

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
        var result: AnyView?
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            if case let .pendingDeletion(deadline) = accountManager.account.status {
                result = DeletedAccountView(
                    deadline: deadline, originalEditorCaller: originalEditorCaller
                ).eraseToAnyView()
            } else {
                applicationStateService.state = .initial
            }
        }
        return result
    }
    
    func setDismissAllPresented(dismissAllPresented: DismissAllPresented) {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            self.dismissAllPresented = dismissAllPresented
        }
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
    

    /// The embedded process owner retains this task beyond presentation.
    /// Standalone callers keep the original zero-argument path above.
    func startAccountStateHandler(readiness: OriginalApplicationConsumerDemand) async {
        defer { readiness.end() }
        await withTaskCancellationHandler {
            guard !Task.isCancelled else { return }
            let publisher = await accountEventHandler.accountStatusPublisher
            guard !Task.isCancelled else { return }
            for await status in OriginalDemandObservingPublisher(
                upstream: publisher, readiness: readiness
            ).values {
                await handleAccountStatus(status)
            }
        } onCancel: {
            readiness.end()
        }
    }

    func startFileHandler(readiness: OriginalApplicationConsumerDemand) async {
        defer { readiness.end() }
        await withTaskCancellationHandler {
            guard !Task.isCancelled else { return }
            let publisher = await fileErrorEventHandler.fileLimitReachedPublisher
            guard !Task.isCancelled else { return }
            for await _ in OriginalDemandObservingPublisher(
                upstream: publisher, readiness: readiness
            ).values {
                handleFileLimitReachedError()
            }
        } onCancel: {
            readiness.end()
        }
    }

    // MARK: - Subscription handler

    private func handleAccountStatus(_ status: AccountStatus) async {
        do {
            try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                switch status {
                case .active:
                    break
                case .pendingDeletion:
                    applicationStateService.state = .delete
                case .deleted:
                    if basicUserInfoStorage.usersId.isNotEmpty {
                        if let originalEditorCaller {
                            try await originalEditorCaller.logout(removeData: true)
                            try originalEditorCaller.validateCurrent()
                        } else {
                            try? await authService.logout(removeData: true)
                        }
                        applicationStateService.state = .auth
                    }
                }
            }
        } catch {
            // A retired caller or failed original Stop cannot advance this UI.
        }
    }
    
    private func handleApplicationState(_ applicationState: ApplicationState) async {
        do {
            try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                await dismissAllPresented?(animated: false)
                try originalEditorCaller?.validateCurrent()
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
        } catch {
            // The original process owner retains closure and error reporting.
        }
    }
    
    // MARK: - Process

    private func loginProcess() async {
        guard acceptsOriginalUI else { return }
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
            try await originalAuthService.walletRecovery(mnemonic: seed)
            try originalEditorCaller?.validateCurrent()
            observeUI27Startup("wallet-recovery-completed")
            observeUI27Startup("select-call-begin")
            await selectAccount(id: userId)
            observeUI27Startup("select-call-returned")
        } catch {
            guard acceptsOriginalUI else { return }
            observeUI27Startup("login-error", error: error)
            applicationStateService.state = .auth
            observeUI27Startup("login-auth-assigned")
        }
    }
    
    func selectAccount(id: String) async {
        do {
            try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                await selectAccountInOriginalFlow(id: id)
            }
        } catch {
            // Retired presentation tasks cannot begin a later original startup.
        }
    }

    private func selectAccountInOriginalFlow(id: String) async {
        do {
            observeUI27Startup("select-auth-begin")
            let account = try await originalAuthService.selectAccount(id: id, preferredSpaceId: preferredSpaceId())
            try originalEditorCaller?.validateCurrent()
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
            try originalEditorCaller?.validateCurrent()
            observeUI27Startup("notification-registration-returned")
        } catch is CancellationError {
            observeUI27Startup("select-cancellation")
            // Ignore cancellations
        } catch SelectAccountError.accountStoreNotMigrated {
            guard acceptsOriginalUI else { return }
            observeUI27Startup("select-store-not-migrated")
            migrationData = MigrationModuleData(
                id: id,
                onFinish: { [weak self, caller = originalEditorCaller] in
                    try? OriginalEditorAuthCaller.withUIAction(caller) {
                        self?.selectAccountTaskId = id
                    }
                },
                originalEditorCaller: originalEditorCaller
            )
        } catch {
            guard acceptsOriginalUI else { return }
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
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            toastBarData = ToastBarData(Loc.FileStorage.limitError, type: .neutral)
        }
    }
}


/// One original downstream consumer's initial demand and terminal state.
/// This is an internal startup barrier, not an account or write capability.
final class OriginalApplicationConsumerDemand: @unchecked Sendable {
    enum ReadinessError: Error {
        case consumerEnded
        case demandNotForwarded
        case alreadyWaiting
    }

    private enum State {
        case waiting
        case requested
        case ended
    }

    private let lock = NSLock()
    private var state: State = .waiting
    private var waiter: CheckedContinuation<Void, Error>?
    private let onEnd: @Sendable () -> Void

    init(onEnd: @escaping @Sendable () -> Void = {}) {
        self.onEnd = onEnd
    }

    /// Called only after a positive request returned from the original
    /// upstream subscription. Completion/cancellation during that call wins.
    func didForwardPositiveDemand() {
        lock.lock()
        guard case .waiting = state else {
            lock.unlock()
            return
        }
        state = .requested
        let continuation = waiter
        waiter = nil
        lock.unlock()
        continuation?.resume()
    }

    func end() {
        lock.lock()
        guard case .ended = state else {
            state = .ended
            let continuation = waiter
            waiter = nil
            lock.unlock()
            continuation?.resume(throwing: ReadinessError.consumerEnded)
            onEnd()
            return
        }
        lock.unlock()
    }

    /// A synchronous admission fact, checked again after every startup await.
    /// It does not claim continuous demand or change AsyncPublisher buffering.
    func validateRequested() throws {
        lock.lock()
        defer { lock.unlock() }
        switch state {
        case .requested: return
        case .waiting: throw ReadinessError.demandNotForwarded
        case .ended: throw ReadinessError.consumerEnded
        }
    }

    func waitUntilRequested() async throws {
        try await withTaskCancellationHandler {
            try Task.checkCancellation()
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                lock.lock()
                switch state {
                case .waiting:
                    guard waiter == nil else {
                        lock.unlock()
                        continuation.resume(throwing: ReadinessError.alreadyWaiting)
                        return
                    }
                    waiter = continuation
                    lock.unlock()
                case .requested:
                    lock.unlock()
                    continuation.resume()
                case .ended:
                    lock.unlock()
                    continuation.resume(throwing: ReadinessError.consumerEnded)
                }
            }
            try Task.checkCancellation()
            try validateRequested()
        } onCancel: {
            self.end()
        }
    }
}

/// An observation-only forwarder around the actual publisher. It adds no
/// buffering, scheduling, values, replay or demand.
struct OriginalDemandObservingPublisher<Upstream: Publisher>: Publisher {
    typealias Output = Upstream.Output
    typealias Failure = Upstream.Failure

    let upstream: Upstream
    let readiness: OriginalApplicationConsumerDemand

    func receive<S: Subscriber>(subscriber: S) where S.Input == Output, S.Failure == Failure {
        upstream.receive(subscriber: OriginalDemandObservingSubscriber(
            downstream: subscriber, readiness: readiness
        ))
    }
}

private final class OriginalDemandObservingSubscriber<Downstream: Subscriber>: Subscriber {
    typealias Input = Downstream.Input
    typealias Failure = Downstream.Failure

    private let downstream: Downstream
    private let readiness: OriginalApplicationConsumerDemand

    init(downstream: Downstream, readiness: OriginalApplicationConsumerDemand) {
        self.downstream = downstream
        self.readiness = readiness
    }

    func receive(subscription: any Subscription) {
        downstream.receive(subscription: OriginalDemandObservingSubscription(
            upstream: subscription, readiness: readiness
        ))
    }

    func receive(_ input: Input) -> Subscribers.Demand {
        downstream.receive(input)
    }

    func receive(completion: Subscribers.Completion<Failure>) {
        readiness.end()
        downstream.receive(completion: completion)
    }
}

private final class OriginalDemandObservingSubscription: Subscription {
    private let upstream: any Subscription
    private let readiness: OriginalApplicationConsumerDemand

    init(upstream: any Subscription, readiness: OriginalApplicationConsumerDemand) {
        self.upstream = upstream
        self.readiness = readiness
    }

    func request(_ demand: Subscribers.Demand) {
        upstream.request(demand)
        if demand > .none {
            readiness.didForwardPositiveDemand()
        }
    }

    func cancel() {
        readiness.end()
        upstream.cancel()
    }
}
