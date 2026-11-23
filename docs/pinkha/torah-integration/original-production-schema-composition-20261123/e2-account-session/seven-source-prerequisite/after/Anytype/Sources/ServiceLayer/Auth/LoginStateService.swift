import Foundation
import ProtobufMessages
import AnytypeCore
import Services

protocol LoginStateServiceProtocol: AnyObject, Sendable {
    var isFirstLaunchAfterRegistration: Bool { get }
    var isFirstLaunchAfterAuthorization: Bool { get }
    func setupStateAfterLoginOrAuth(account: AccountData, source: OriginalAuthStartupSource) async throws
    func setupStateAfterAuth(attempt: OriginalAuthAttempt) async throws
    func setupStateAfterRegistration(account: AccountData, source: OriginalAuthStartupSource) async throws
    func cleanStateAfterLogout() async
    func setupStateBeforeLoginOrAuth(attempt: OriginalAuthAttempt) async throws
    func cancelStartup(attempt: OriginalAuthAttempt) async
}

actor LoginStateService: LoginStateServiceProtocol, Sendable {
    
    private let isFirstLaunchAfterRegistrationStorage = AtomicStorage(false)
    private let isFirstLaunchAfterAuthorizationStorage = AtomicStorage(false)
    
    nonisolated var isFirstLaunchAfterRegistration: Bool {
        isFirstLaunchAfterRegistrationStorage.value
    }
    
    nonisolated var isFirstLaunchAfterAuthorization: Bool {
        isFirstLaunchAfterAuthorizationStorage.value
    }
    
    private let objectTypeProvider: any ObjectTypeProviderProtocol = Container.shared.objectTypeProvider()
    private let middlewareConfigurationProvider: any MiddlewareConfigurationProviderProtocol = Container.shared.middlewareConfigurationProvider()
    private let expandedService: any ExpandedServiceProtocol = Container.shared.expandedService()
    private let membershipStatusStorage: any MembershipStatusStorageProtocol = Container.shared.membershipStatusStorage()
    private let propertyDetailsStorage: any PropertyDetailsStorageProtocol = Container.shared.propertyDetailsStorage()
    private let workspacesStorage: any SpaceViewsStorageProtocol = Container.shared.spaceViewsStorage()
    private let chatDetailsStorage: any ChatDetailsStorageProtocol = Container.shared.chatDetailsStorage()
    private let accountParticipantsStorage: any ParticipantsStorageProtocol = Container.shared.participantsStorage()
    private let objectsWithUnreadDiscussionsSubscription: any ObjectsWithUnreadDiscussionsSubscriptionProtocol = Container.shared.objectsWithUnreadDiscussionsSubscription()
    private let participantSpacesStorage: any ParticipantSpacesStorageProtocol = Container.shared.participantSpacesStorage()
    private let storeKitService: any StoreKitServiceProtocol = Container.shared.storeKitService()
    private let syncStatusStorage: any SyncStatusStorageProtocol = Container.shared.syncStatusStorage()
    private let p2pStatusStorage: any P2PStatusStorageProtocol = Container.shared.p2pStatusStorage()
    private let networkConnectionStatusDaemon: any NetworkConnectionStatusDaemonProtocol = Container.shared.networkConnectionStatusDaemon()
    private let userDefaults: any UserDefaultsStorageProtocol = Container.shared.userDefaultsStorage()
    private let activeSpaceManager: any ActiveSpaceManagerProtocol = Container.shared.activeSpaceManager()
    private let profileStorage: any ProfileStorageProtocol = Container.shared.profileStorage()
    private let basicUserInfoStorage: any BasicUserInfoStorageProtocol = Container.shared.basicUserInfoStorage()
    private let pushNotificationsPermissionService: any PushNotificationsPermissionServiceProtocol = Container.shared.pushNotificationsPermissionService()
    private let spaceIconForNotificationsHandler: any SpaceIconForNotificationsHandlerProtocol = Container.shared.spaceIconForNotificationsHandler()
    private let spaceFileUploadService: any SpaceFileUploadServiceProtocol = Container.shared.spaceFileUploadService()
    private let appIconBadgeService: any AppIconBadgeServiceProtocol = Container.shared.appIconBadgeService()
    private let chatMessagesPreviewsStorage: any ChatMessagesPreviewsStorageProtocol = Container.shared.chatMessagesPreviewsStorage()
    private let crossSpaceTypesStorage: any CrossSpaceTypesStorageProtocol = Container.shared.crossSpaceTypesStorage()
    private let crossSpaceParticipantsStorage: any CrossSpaceParticipantsStorageProtocol = Container.shared.crossSpaceParticipantsStorage()
    private let thermalProfilerTrigger: any ThermalProfilerTriggerProtocol = Container.shared.thermalProfilerTrigger()
    private let memoryPressureProfilerTrigger: any MemoryPressureProfilerTriggerProtocol = Container.shared.memoryPressureProfilerTrigger()
    private let debugProfileEventHandler: any DebugProfileEventHandlerProtocol = Container.shared.debugProfileEventHandler()
        
    // Every compound startup/stop state below is owned by this original actor.
    private var startup: Startup?
    private var accountSource: OriginalAuthStartupSource?
    private var stopping: Stopping?
    private var primaryRunning = false

    private final class Startup: Sendable {
        let attempt: OriginalAuthAttempt
        let tasks = StartupTasks()
        private let retirements: [EditorDocumentWriteLifetime.Observation]

        init(attempt: OriginalAuthAttempt) {
            self.attempt = attempt
            let tasks = self.tasks
            retirements = attempt.captures.map { value in
                value.source.observe(value.token) { tasks.cancel() }
            }
        }
        func retire() {
            attempt.retire()
            tasks.cancel()
        }
        deinit { tasks.cancel() }
    }

    /// Only handles/cancellation are shared with synchronous lifetime callbacks.
    /// Installation observes cancellation under the same lock; no await is held.
    private final class StartupTasks: @unchecked Sendable {
        private let lock = NSLock()
        private var cancelled = false
        private var primary: Task<Void, Error>?
        private var membership: Task<Void, Error>?

        func installPrimary(_ task: Task<Void, Error>) {
            lock.lock()
            primary = task
            let shouldCancel = cancelled
            lock.unlock()
            if shouldCancel { task.cancel() }
        }
        func installMembership(_ task: Task<Void, Error>) {
            lock.lock()
            membership = task
            let shouldCancel = cancelled
            lock.unlock()
            if shouldCancel { task.cancel() }
        }
        func cancel() {
            lock.lock()
            cancelled = true
            let primary = primary
            let membership = membership
            lock.unlock()
            primary?.cancel()
            membership?.cancel()
        }
        private func primaryTask() -> Task<Void, Error>? {
            lock.lock()
            defer { lock.unlock() }
            return primary
        }
        private func membershipTask() -> Task<Void, Error>? {
            lock.lock()
            defer { lock.unlock() }
            return membership
        }
        func drain() async {
            _ = try? await primaryTask()?.value
            // Primary may have installed the owned membership task before it
            // ended; read that handle only after actual primary completion.
            _ = try? await membershipTask()?.value
        }
    }

    /// Mutable fields are exclusively accessed on LoginStateService's actor.
    private final class Stopping: @unchecked Sendable {
        var clearAccountData: Bool
        var task: Task<Void, Never>?
        init(clearAccountData: Bool) { self.clearAccountData = clearAccountData }
    }

    private enum StartupPhase: Sendable {
        case before
        case login(AccountData, OriginalAuthStartupSource)
        case registration(AccountData, OriginalAuthStartupSource)
        var source: OriginalAuthStartupSource? {
            switch self {
            case .before: return nil
            case let .login(_, source), let .registration(_, source): return source
            }
        }
    }

    func setupStateBeforeLoginOrAuth(attempt: OriginalAuthAttempt) async throws {
        try attempt.validate()
        guard stopping == nil else { throw OriginalAuthFlowError.busy }
        if let previous = startup {
            guard previous.attempt !== attempt else { throw OriginalAuthFlowError.busy }
            await stopOwnedSubscriptions(clearAccountData: false)
            try attempt.validate()
        }
        guard startup == nil, stopping == nil else { throw OriginalAuthFlowError.busy }
        let owner = Startup(attempt: attempt)
        startup = owner
        try await runPrimary(owner, phase: .before)
    }

    func setupStateAfterLoginOrAuth(account: AccountData, source: OriginalAuthStartupSource) async throws {
        try await startAccountSubscriptions(account: account, source: source, registration: false)
    }

    func setupStateAfterRegistration(account: AccountData, source: OriginalAuthStartupSource) async throws {
        try await startAccountSubscriptions(account: account, source: source, registration: true)
    }

    private func startAccountSubscriptions(account: AccountData, source: OriginalAuthStartupSource, registration: Bool) async throws {
        try source.validate()
        guard let owner = startup, owner.attempt === source.attempt, accountSource == nil,
              account.id.utf8.elementsEqual(source.accountID.utf8), stopping == nil else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
        accountSource = source
        try await runPrimary(owner, phase: registration ? .registration(account, source) : .login(account, source))
    }

    func setupStateAfterAuth(attempt: OriginalAuthAttempt) async throws {
        try attempt.validate()
        guard stopping == nil else { throw OriginalAuthFlowError.busy }
        isFirstLaunchAfterAuthorizationStorage.value = true
        WidgetSwipeTip.isFirstSession = false
    }

    func cancelStartup(attempt: OriginalAuthAttempt) async {
        guard startup?.attempt === attempt else { return }
        await stopOwnedSubscriptions(clearAccountData: false)
    }

    func cleanStateAfterLogout() async {
        await stopOwnedSubscriptions(clearAccountData: true)
    }

    private func validate(_ owner: Startup, source: OriginalAuthStartupSource? = nil) throws {
        guard startup === owner, stopping == nil else { throw EditorDocumentWriteError.rejected(.retired) }
        try owner.attempt.validate()
        try source?.validate()
    }

    private func runPrimary(_ owner: Startup, phase: StartupPhase) async throws {
        try validate(owner, source: phase.source)
        guard !primaryRunning else { throw OriginalAuthFlowError.busy }
        primaryRunning = true
        let task = Task { [weak self] in
            guard let self else { throw EditorDocumentWriteError.rejected(.retired) }
            let admissions = try owner.attempt.admitStage()
            defer { for admission in admissions { admission.cancel() } }
            let binding = phase.source?.binding ?? owner.attempt.startupBinding()
            try await InvocationDispatchContext.$binding.withValue(binding) {
                try await self.runPhase(owner, phase: phase)
            }
        }
        owner.tasks.installPrimary(task)
        do {
            try await withTaskCancellationHandler {
                try await task.value
            } onCancel: { owner.retire() }
            if startup === owner { primaryRunning = false }
            try validate(owner, source: phase.source)
        } catch {
            if startup === owner { primaryRunning = false }
            throw error
        }
    }

    private func runPhase(_ owner: Startup, phase: StartupPhase) async throws {
        try validate(owner, source: phase.source)
        switch phase {
        case .before:
            await syncStatusStorage.startSubscription()
            try validate(owner)
            await p2pStatusStorage.startSubscription()
            try validate(owner)
        case let .login(account, source):
            middlewareConfigurationProvider.setupConfiguration(account: account)
            WidgetSwipeTip.isFirstSession = false
            try await startSubscriptions(owner, source: source)
        case let .registration(account, source):
            isFirstLaunchAfterRegistrationStorage.value = true
            WidgetSwipeTip.isFirstSession = true
            middlewareConfigurationProvider.setupConfiguration(account: account)
            try await startSubscriptions(owner, source: source)
        }
    }

    private func startSubscriptions(_ owner: Startup, source: OriginalAuthStartupSource) async throws {
        try validate(owner, source: source)
        await workspacesStorage.startSubscription()
        try validate(owner, source: source)
        await chatDetailsStorage.startSubscription()
        try validate(owner, source: source)
        await chatMessagesPreviewsStorage.startSubscription()
        try validate(owner, source: source)
        await accountParticipantsStorage.startSubscription()
        try validate(owner, source: source)
        await objectsWithUnreadDiscussionsSubscription.startSubscription()
        try validate(owner, source: source)
        await participantSpacesStorage.startSubscription()
        try validate(owner, source: source)
        if FeatureFlags.unifiedSearch {
            await crossSpaceTypesStorage.startSubscription()
            try validate(owner, source: source)
            await crossSpaceParticipantsStorage.startSubscription()
            try validate(owner, source: source)
        }
        await networkConnectionStatusDaemon.start()
        try validate(owner, source: source)
        if OriginalRuntimeEnvironment.deploymentMode == .standalone {
            await storeKitService.startListenForTransactions()
        }
        try validate(owner, source: source)
        await profileStorage.startSubscription()
        try validate(owner, source: source)
        await activeSpaceManager.startSubscription()
        try validate(owner, source: source)
        if OriginalRuntimeEnvironment.deploymentMode == .standalone {
            await spaceIconForNotificationsHandler.startUpdating()
        }
        try validate(owner, source: source)
        if OriginalRuntimeEnvironment.deploymentMode == .standalone {
            await appIconBadgeService.startUpdating()
        }
        try validate(owner, source: source)
        await thermalProfilerTrigger.startSubscription()
        try validate(owner, source: source)
        await memoryPressureProfilerTrigger.startSubscription()
        try validate(owner, source: source)
        await debugProfileEventHandler.startSubscription()
        try validate(owner, source: source)

        // Preserve the original asynchronous membership startup, now retaining
        // and draining its actual task before the original stop/clean methods.
        let task = Task { [weak self] in
            guard let self else { throw EditorDocumentWriteError.rejected(.retired) }
            let admissions = try owner.attempt.admitStage()
            defer { for admission in admissions { admission.cancel() } }
            try await InvocationDispatchContext.$binding.withValue(source.binding) {
                try await self.validate(owner, source: source)
                await self.membershipStatusStorage.startSubscription()
                try await self.validate(owner, source: source)
            }
        }
        owner.tasks.installMembership(task)
    }

    private func stopOwnedSubscriptions(clearAccountData: Bool) async {
        if let stop = stopping {
            if clearAccountData { stop.clearAccountData = true }
            await stop.task?.value
            return
        }
        let owner = startup
        owner?.retire()
        let stop = Stopping(clearAccountData: clearAccountData)
        stopping = stop
        let task = Task { [weak self] in
            guard let self else { return }
            await self.completeOwnedStop(owner: owner, stop: stop)
        }
        stop.task = task
        await task.value
    }

    // Actor isolation remains explicit after the unstructured task's awaits.
    // Mutable Stopping fields and the startup/account state belong to this actor.
    private func completeOwnedStop(owner: Startup?, stop: Stopping) async {
        await owner?.tasks.drain()
        // Auth's outer startup lease is finished before its error cleanup
        // requests this drain; native Stop is dispatched before logout joins.
        await owner?.attempt.waitForDrain()
        await stopSubscriptions()
        if stop.clearAccountData {
            await clearOriginalStateAfterLogout()
        }
        if startup === owner {
            startup = nil
            accountSource = nil
            primaryRunning = false
        }
        if stopping === stop { stopping = nil }
    }

    private func clearOriginalStateAfterLogout() async {
        // No old startup or membership start can write these values back after
        // its native drain and the original subscription stop sequence.
        basicUserInfoStorage.cleanUserIdAfterLogout()
        expandedService.clearData()
        middlewareConfigurationProvider.removeCachedConfiguration()
        pushNotificationsPermissionService.unregisterForRemoteNotifications()
        spaceFileUploadService.cancelAllUploads()
        await MainActor.run {
            Container.shared.chatActivityStore().clearAll()
        }
        userDefaults.cleanStateAfterLogout()
    }

    private func stopSubscriptions() async {
        await workspacesStorage.stopSubscription()
        await chatDetailsStorage.stopSubscription()
        await chatMessagesPreviewsStorage.stopSubscriptionAndClean()
        await propertyDetailsStorage.stopSubscription()
        await objectTypeProvider.stopSubscription()
        await accountParticipantsStorage.stopSubscription()
        await objectsWithUnreadDiscussionsSubscription.stopSubscription()
        await participantSpacesStorage.stopSubscription()
        await crossSpaceTypesStorage.stopSubscription()
        await crossSpaceParticipantsStorage.stopSubscription()
        await membershipStatusStorage.stopSubscriptionAndClean()
        await syncStatusStorage.stopSubscriptionAndClean()
        await p2pStatusStorage.stopSubscriptionAndClean()
        await networkConnectionStatusDaemon.stop()
        if OriginalRuntimeEnvironment.deploymentMode == .standalone {
            await storeKitService.stopListenForTransactions()
        }
        await profileStorage.stopSubscription()
        await activeSpaceManager.stopSubscription()
        if OriginalRuntimeEnvironment.deploymentMode == .standalone {
            await spaceIconForNotificationsHandler.stopUpdatingAndClearData()
        }
        if OriginalRuntimeEnvironment.deploymentMode == .standalone {
            await appIconBadgeService.stopUpdatingAndClearBadge()
        }
        await thermalProfilerTrigger.stopSubscriptionAndClean()
        await memoryPressureProfilerTrigger.stopSubscriptionAndClean()
        await debugProfileEventHandler.stopSubscriptionAndClean()
    }
}
