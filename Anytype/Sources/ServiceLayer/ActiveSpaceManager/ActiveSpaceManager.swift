import Foundation
import AnytypeCore
import Services
import AsyncTools
import ProtobufMessages

protocol ActiveSpaceManagerProtocol: AnyObject, Sendable {
    var workspaceInfoStream: AnyAsyncSequence<AccountInfo?> { get }
    var workspaceInfo: AccountInfo? { get }
    @discardableResult
    func setActiveSpace(spaceId: String?) async throws -> AccountInfo?
    func prepareSpaceForPreview(spaceId: String) async
    func prepareWidgets() async
    func startSubscription() async
    func stopSubscription() async
}

struct OriginalActiveSpaceSelection: Sendable {
    let accountID: String
    let accountInfo: AccountInfo

    private let attempt: OriginalActiveSpaceSelectionAttempt

    fileprivate init(attempt: OriginalActiveSpaceSelectionAttempt, info: AccountInfo) throws {
        try attempt.validateReturnedInfo(info)
        guard let accountID = attempt.accountID, attempt.spaceViewCapture != nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        self.accountID = accountID
        accountInfo = info
        self.attempt = attempt
        try validate()
    }

    func validate() throws {
        try attempt.validate()
        try attempt.validateReturnedInfo(accountInfo)
    }

    /// Registers only this actually selected Space's fixed annotation schema.
    /// The original account/selection/view generations and current subscription
    /// permissions remain internal. The response and drained history are
    /// historical observations, not a reusable write, body or ACK authority.
    @MainActor
    func registerOriginalAnnotationSchema(
        onDrained: @escaping @MainActor @Sendable (OriginalAnnotationSchemaCallHistory) -> Void
    ) async throws -> Anytype_Rpc.Annotation.Schema.Register.Response {
        try validate()
        guard let participants = Container.shared.participantsStorage() as? ParticipantsStorage,
              let spaceViews = Container.shared.spaceViewsStorage() as? SpaceViewsStorage else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        let spaceID = accountInfo.accountSpaceId
        let participant = try participants.currentParticipantEditPermission(spaceId: spaceID)
        let spaceView = try spaceViews.currentOriginalSpaceViewPermission(spaceId: spaceID)
        guard spaceView.originalSpaceView.id.utf8.elementsEqual(accountInfo.spaceViewId.utf8) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        let binding = try attempt.workspaceBinding()
        try validate()
        return try await binding.performOriginalAnnotationSchemaRegistration(
            expectedAccountID: accountID, spaceID: spaceID,
            participant: participant, spaceView: spaceView, onDrained: onDrained
        )
    }

    func capture(
        matching account: EditorDocumentWriteCapture, spaceId: String
    ) throws -> EditorDocumentWriteCapture {
        guard let original = attempt.accountCapture,
              original.source === account.source,
              original.token == account.token,
              accountInfo.accountSpaceId.utf8.elementsEqual(spaceId.utf8) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        try account.validate()
        try validate()
        return attempt.capture
    }
}

fileprivate final class OriginalActiveSpaceSelectionAttempt: Sendable {
    let requestedSpaceID: String?
    let accountID: String?
    let accountCapture: EditorDocumentWriteCapture?
    let capture: EditorDocumentWriteCapture
    let spaceViewCapture: EditorDocumentWriteCapture?
    let retainedCaptures: [EditorDocumentWriteCapture]

    private let retainedRetirement: [EditorDocumentWriteLifetime.Observation]
    private let spaceView: OriginalSpaceViewPermission?
    private let accountRetirement: EditorDocumentWriteLifetime.Observation?
    private let viewRetirement: EditorDocumentWriteLifetime.Observation?

    init(
        spaceId: String?,
        accountManager: any AccountManagerProtocol,
        workspaceStorage: any SpaceViewsStorageProtocol,
        retaining retainedCaptures: [EditorDocumentWriteCapture] = []
    ) throws {
        let lifetime = EditorDocumentWriteLifetime()
        requestedSpaceID = spaceId
        capture = try EditorDocumentWriteCapture(lifetime)
        self.retainedCaptures = retainedCaptures
        for captured in retainedCaptures { try captured.validate() }
        retainedRetirement = retainedCaptures.map { captured in
            captured.source.observe(captured.token) { lifetime.markUnavailable() }
        }
        if let spaceId {
            guard !spaceId.isEmpty,
                  accountManager is AccountManager,
                  let accountLifetime = accountManager.editorWriteLifetime else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
            let capturedAccount = try EditorDocumentWriteCapture(accountLifetime)
            let account = accountManager.account
            try capturedAccount.validate()
            guard !account.id.isEmpty else {
                throw EditorDocumentWriteError.rejected(.wrongContext)
            }
            accountID = account.id
            accountCapture = capturedAccount

            let view = (workspaceStorage as? SpaceViewsStorage).flatMap {
                try? $0.currentOriginalSpaceViewPermission(spaceId: spaceId)
            }
            let capturedView = try view?.capture(matching: capturedAccount, spaceId: spaceId)
            spaceView = view
            spaceViewCapture = capturedView
            accountRetirement = capturedAccount.source.observe(capturedAccount.token) {
                lifetime.markUnavailable()
            }
            viewRetirement = capturedView.map { value in
                value.source.observe(value.token) { lifetime.markUnavailable() }
            }
        } else {
            accountID = nil
            accountCapture = nil
            spaceView = nil
            spaceViewCapture = nil
            accountRetirement = nil
            viewRetirement = nil
        }
        try validate()
    }

    func validate() throws {
        try Task.checkCancellation()
        try capture.validate()
        try accountCapture?.validate()
        try spaceViewCapture?.validate()
        for captured in retainedCaptures { try captured.validate() }
    }

    func retainsExactly(_ expected: [EditorDocumentWriteCapture]) -> Bool {
        retainedCaptures.count == expected.count && zip(retainedCaptures, expected).allSatisfy { pair in
            pair.0.source === pair.1.source && pair.0.token == pair.1.token
        }
    }

    func validateReturnedInfo(_ info: AccountInfo) throws {
        try validate()
        guard let requestedSpaceID,
              info.accountSpaceId.utf8.elementsEqual(requestedSpaceID.utf8),
              !info.spaceViewId.isEmpty else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        if let spaceView {
            guard spaceView.originalSpaceView.targetSpaceId.utf8.elementsEqual(requestedSpaceID.utf8),
                  spaceView.originalSpaceView.id.utf8.elementsEqual(info.spaceViewId.utf8) else {
                throw EditorDocumentWriteError.rejected(.wrongContext)
            }
            try spaceView.validate()
        }
    }

    @MainActor
    func workspaceBinding() throws -> EditorDocumentWriteSourceBinding {
        try validate()
        guard let accountCapture, requestedSpaceID != nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        let additional = (spaceViewCapture.map { [$0.source] } ?? []) + retainedCaptures.map(\.source)
        let binding = try EditorDocumentWriteSourceBinding(
            lifetime: capture.source,
            accountLifetime: accountCapture.source,
            additionalLifetimes: additional,
            isCurrent: { (try? self.validate()) != nil }
        )
        let expected = [capture] + (spaceViewCapture.map { [$0] } ?? []) + retainedCaptures + [accountCapture]
        guard binding.captures.count == expected.count,
              zip(binding.captures, expected).allSatisfy({ pair in
                  pair.0.source === pair.1.source && pair.0.token == pair.1.token
              }) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        try validate()
        try binding.validate()
        return binding
    }

    func retire() {
        capture.source.markUnavailable()
        accountRetirement?.cancel()
        viewRetirement?.cancel()
        for observation in retainedRetirement { observation.cancel() }
    }

    deinit {
        retire()
    }
}

private final class OriginalActiveSpaceSubscriptionAttempt: Sendable {}

actor ActiveSpaceManager: ActiveSpaceManagerProtocol, Sendable {
    
    // MARK: - DI
    
    @Injected(\.spaceViewsStorage)
    private var workspaceStorage: any SpaceViewsStorageProtocol
    @Injected(\.workspaceService)
    private var workspaceService: any WorkspaceServiceProtocol
    @Injected(\.accountManager)
    private var accountManager: any AccountManagerProtocol
    
    // MARK: - State
    private var workspaceSubscription: Task<Void, Never>?
    private var workspaceSubscriptionAttempt: OriginalActiveSpaceSubscriptionAttempt?
    private var activeSpaceId: String?
    private var spaceIsLoading: Bool = false
    private let workspaceInfoStreamInternal = AsyncToManyStream<AccountInfo?>()
    private let workspaceInfoStorage = AtomicStorage<AccountInfo?>(nil)
    private let selectedSpaceStorage = AtomicStorage<OriginalActiveSpaceSelection?>(nil)
    private var selectionAttempt: OriginalActiveSpaceSelectionAttempt?
    private var setActiveSpaceTask: Task<AccountInfo?, any Error>?
    private var stopOperation: Task<Void, Never>?
    
    @Injected(\.objectTypeProvider)
    private var objectTypeProvider: any ObjectTypeProviderProtocol
    @Injected(\.propertyDetailsStorage)
    private var propertyDetailsStorage: any PropertyDetailsStorageProtocol
    @Injected(\.widgetsObjectsStorage)
    private var widgetsObjectsStorage: any WidgetsObjectsStorageProtocol
    @Injected(\.spaceRecencyStorage)
    private var spaceRecencyStorage: any SpaceRecencyStorageProtocol

    init() {}

    deinit {
        selectionAttempt?.retire()
        workspaceSubscription?.cancel()
    }
    
    nonisolated var workspaceInfoStream: AnyAsyncSequence<AccountInfo?> {
        workspaceInfoStreamInternal.eraseToAnyAsyncSequence()
    }
    
    nonisolated var workspaceInfo: AccountInfo? {
        workspaceInfoStorage.value
    }

    nonisolated func currentOriginalActiveSpaceSelection() throws -> OriginalActiveSpaceSelection {
        guard let selection = selectedSpaceStorage.value else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        try selection.validate()
        return selection
    }
    
    @discardableResult
    func setActiveSpace(spaceId: String?) async throws -> AccountInfo? {
        try await selectActiveSpace(spaceId: spaceId, retaining: [])
    }

    /// Internal original localOnly batch composition. These already captured
    /// sources remain in WorkspaceOpen and subsequent schema GCD admissions.
    /// Ordinary app selection does not acquire this additional ownership.
    func setActiveSpaceForLocalAnnotationBatch(
        spaceId: String, retaining captures: [EditorDocumentWriteCapture]
    ) async throws -> AccountInfo? {
        guard !captures.isEmpty else { throw EditorDocumentWriteError.rejected(.unqualifiedDispatch) }
        return try await selectActiveSpace(spaceId: spaceId, retaining: captures)
    }

    private func selectActiveSpace(spaceId: String?,
                                   retaining captures: [EditorDocumentWriteCapture]) async throws -> AccountInfo? {
        try Task.checkCancellation()
        for captured in captures { try captured.validate() }
        guard stopOperation == nil, InvocationDispatchContext.binding == nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        if activeSpaceId == spaceId,
           let selectionAttempt,
           selectionAttempt.retainsExactly(captures),
           (try? selectionAttempt.validate()) != nil,
           let setActiveSpaceTask {
            let value = try await setActiveSpaceTask.value
            try Task.checkCancellation()
            try selectionAttempt.validate()
            // A successful cached WorkspaceOpen does not imply that the later
            // asynchronous Bootstrap succeeded. An explicit selection retries
            // its failed claim; ready/in-flight Bootstrap remains single-owner.
            if let spaceId {
                PinkhaBootstrapHook.handleSpaceActivated(spaceId: spaceId)
            }
            return value
        }

        let attempt = try OriginalActiveSpaceSelectionAttempt(
            spaceId: spaceId, accountManager: accountManager, workspaceStorage: workspaceStorage,
            retaining: captures
        )
        let previous = setActiveSpaceTask
        selectionAttempt?.retire()
        selectedSpaceStorage.value = nil
        selectionAttempt = attempt
        activeSpaceId = spaceId
        let task = Task { [self] in
            if let previous { _ = await previous.result }
            return try await performSelection(attempt)
        }
        setActiveSpaceTask = task
        let value = try await task.value
        try Task.checkCancellation()
        try attempt.validate()
        return value
    }
    
    func startSubscription() {
        guard workspaceSubscription == nil, stopOperation == nil else { return }
        let attempt = OriginalActiveSpaceSubscriptionAttempt()
        workspaceSubscriptionAttempt = attempt
        workspaceSubscription = Task { [weak self, workspaceStorage] in
            for await workspaces in workspaceStorage.allSpaceViewsPublisher.values {
                await self?.handleSpaces(workspaces: workspaces, subscription: attempt)
            }
        }
    }
    
    func stopSubscription() async {
        if let stopOperation {
            await stopOperation.value
            return
        }
        workspaceSubscriptionAttempt = nil
        workspaceSubscription?.cancel()
        workspaceSubscription = nil
        selectionAttempt?.retire()
        selectionAttempt = nil
        selectedSpaceStorage.value = nil
        activeSpaceId = nil
        spaceIsLoading = false
        workspaceInfoStreamInternal.send(nil)
        workspaceInfoStorage.value = nil

        let previous = setActiveSpaceTask
        let operation = Task { [self] in
            if let previous { _ = await previous.result }
            await clearSharedActiveSpace()
        }
        stopOperation = operation
        await operation.value
        setActiveSpaceTask = nil
        stopOperation = nil
    }
    
    func prepareSpaceForPreview(spaceId: String) async {
        await objectTypeProvider.prepareData(spaceId: spaceId)
        await propertyDetailsStorage.prepareData(spaceId: spaceId)
    }

    func prepareWidgets() async {
        guard stopOperation == nil,
              let attempt = selectionAttempt,
              let info = workspaceInfoStorage.value,
              info.accountSpaceId == attempt.requestedSpaceID,
              (try? attempt.validateReturnedInfo(info)) != nil else { return }
        await widgetsObjectsStorage.prepare(info: info)
    }
    
    // MARK: - Private

    private func performSelection(_ attempt: OriginalActiveSpaceSelectionAttempt) async throws -> AccountInfo? {
        try requireCurrent(attempt)
        spaceIsLoading = true
        defer {
            if selectionAttempt === attempt { spaceIsLoading = false }
        }
        do {
            guard let spaceId = attempt.requestedSpaceID else {
                workspaceInfoStreamInternal.send(nil)
                workspaceInfoStorage.value = nil
                await clearSharedActiveSpace()
                try requireCurrent(attempt)
                return nil
            }
            let binding = try await attempt.workspaceBinding()
            try requireCurrent(attempt)
            let service = workspaceService
            let info = try await binding.performOperation(rpcNames: ["WorkspaceOpen"]) {
                try await service.workspaceOpenForOriginalSelection(spaceId: spaceId)
            }
            await attempt.capture.source.waitForOperationsToDrain()
            try requireCurrent(attempt)
            try attempt.validateReturnedInfo(info)
            let selection = try attempt.spaceViewCapture.map { _ in
                try OriginalActiveSpaceSelection(attempt: attempt, info: info)
            }

            workspaceStorage.addSpaceInfo(spaceId: spaceId, info: info)
            spaceRecencyStorage.markInteraction(spaceId: spaceId)
            await widgetsObjectsStorage.prepare(info: info)
            try requireCurrent(attempt)
            await objectTypeProvider.startSubscription(spaceId: spaceId)
            try requireCurrent(attempt)
            await propertyDetailsStorage.startSubscription(spaceId: spaceId)
            try requireCurrent(attempt)
            
            PinkhaBootstrapHook.handleSpaceActivated(spaceId: spaceId)
            
            logSwitchSpace(spaceId: spaceId)
            
            try selection?.validate()
            selectedSpaceStorage.value = selection
            workspaceInfoStreamInternal.send(info)
            workspaceInfoStorage.value = info
            return info
        } catch {
            await attempt.capture.source.waitForOperationsToDrain()
            if selectionAttempt === attempt {
                attempt.retire()
                selectionAttempt = nil
                selectedSpaceStorage.value = nil
                activeSpaceId = nil
                workspaceInfoStreamInternal.send(nil)
                workspaceInfoStorage.value = nil
                await clearSharedActiveSpace()
            }
            throw error
        }
    }

    private func requireCurrent(_ attempt: OriginalActiveSpaceSelectionAttempt) throws {
        guard stopOperation == nil, selectionAttempt === attempt else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
        try attempt.validate()
    }
    
    private func handleSpaces(
        workspaces: [SpaceView], subscription: OriginalActiveSpaceSubscriptionAttempt
    ) async {
        guard workspaceSubscriptionAttempt === subscription else { return }
        guard let activeSpaceId,
              let currentView = workspaces.first(where: { $0.targetSpaceId == activeSpaceId }),
              (currentView.isLoading && spaceIsLoading) || currentView.isActive else {
            _ = try? await setActiveSpace(spaceId: nil)
            return
        }
    }
    
    private var latestNonNilSpaceId: String?
    private func logSwitchSpace(spaceId: String?) {
        guard spaceId.isNotNil else { return }
        guard latestNonNilSpaceId.isNotNil else {
            latestNonNilSpaceId = spaceId
            return
        }
        
        if latestNonNilSpaceId != spaceId {
            latestNonNilSpaceId = spaceId
            AnytypeAnalytics.instance().logSwitchSpace()
        }
    }
    
    private func clearSharedActiveSpace() async {
        await widgetsObjectsStorage.clear()
        await objectTypeProvider.stopSubscription()
        await propertyDetailsStorage.stopSubscription()
    }
}
