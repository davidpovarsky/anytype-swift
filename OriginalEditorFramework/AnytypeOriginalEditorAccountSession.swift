import Foundation
import UIKit
import Observation
@preconcurrency import Combine
import AnytypeCore
import ProtobufMessages
import Services

/// A closed original account/selected-Space session. Identity is display data;
/// no public initializer accepts an account, Space, capture, seed or native path.
/// Host construction/import and the saved local source boundary remain separate.
@MainActor
public final class AnytypeOriginalEditorAccountSession {
    public struct Identity: Sendable, Equatable {
        public let accountID: String
        public let spaceID: String

        fileprivate init(selection: OriginalActiveSpaceSelection) {
            accountID = selection.accountID
            spaceID = selection.accountInfo.accountSpaceId
        }
    }

    public enum SessionError: Error {
        case runtimeAlreadyOwned
        case incompatibleDeployment
        case unsupportedBuildConfiguration
        case originalServiceUnavailable
        case retired
        case unavailableSpace
        case unobservedSchemaCompletion
        case closeRequiresExplicitRetry
    }

    /// Keep this handle while the account presentation is pending. A failed
    /// original Stop retains its exact owner and may only be retried explicitly.
    @MainActor
    public final class Presentation {
        public let viewController: UIViewController
        private let owner: OriginalEditorAccountRuntimeAttempt

        fileprivate init(
            viewController: UIViewController,
            owner: OriginalEditorAccountRuntimeAttempt
        ) {
            self.viewController = viewController
            self.owner = owner
        }

        public func close() async throws {
            try await owner.close(retrying: false)
        }

        public func retryClose() async throws {
            try await owner.close(retrying: true)
        }
    }

    public let identity: Identity
    private let owner: OriginalEditorAccountRuntimeAttempt
    private let selection: OriginalActiveSpaceSelection

    fileprivate init(
        owner: OriginalEditorAccountRuntimeAttempt,
        selection: OriginalActiveSpaceSelection
    ) throws {
        try owner.validateReadySelection(selection)
        self.owner = owner
        self.selection = selection
        identity = Identity(selection: selection)
    }

    /// Builds only the owned original presentation. Authentication begins when
    /// its controller actually appears. Deployment is not account authority.
    /// The synchronous handle cannot be lost to an async constructor cancellation.
    public static func makePresentation(
        appGroup: String,
        onReady: @escaping @MainActor (AnytypeOriginalEditorAccountSession) -> Void,
        onFailure: @escaping @MainActor (any Error) -> Void
    ) throws -> Presentation {
        let process = try OriginalEditorEmbeddedAccountProcess.acquire(appGroup: appGroup)
        let owner = try process.makeAttempt(onReady: onReady, onFailure: onFailure)
        let controller = OriginalEditorAccountHostingController(owner: owner)
        owner.attach(controller: controller)
        return Presentation(viewController: controller, owner: owner)
    }

    public func validateCurrent() throws {
        try owner.validate(session: self, selection: selection)
    }

    public func close() async throws {
        try await owner.close(retrying: false)
    }

    public func retryClose() async throws {
        try await owner.close(retrying: true)
    }

    /// Only a later reviewed internal Host/source intersection may consume this
    /// original selection. Returning display IDs cannot call this boundary.
    internal func currentOriginalSelection() throws -> OriginalActiveSpaceSelection {
        try validateCurrent()
        return selection
    }

    /// Narrow a real Host saved-source lifetime with this SAME already-selected
    /// runtime attempt. The original frozen tokens must still match; display
    /// identities cannot replace a retired account/selection/permission capture.
    internal func originalAnnotationImportSourceBinding(
        lifetime: EditorDocumentWriteLifetime,
        sourceIsCurrent: @escaping @MainActor () -> Bool
    ) throws -> EditorDocumentWriteSourceBinding {
        try validateCurrent()
        return try owner.makeAnnotationImportSourceBinding(
            session: self, selection: selection,
            sourceLifetime: lifetime, sourceIsCurrent: sourceIsCurrent
        )
    }
}

/// One immutable original middleware/environment installation per process.
/// It retains the registered original services; no Factory registration changes,
/// app delegate, standalone AppConfigurator or qualification runtime is used.
@MainActor
internal final class OriginalEditorEmbeddedAccountProcess {
    private static var installed: OriginalEditorEmbeddedAccountProcess?
    private static var installationStarted = false

    let appGroup: String
    let auth: PinkhaHanlinAuthService
    let accountEvents: AccountEventHandler
    let fileEvents: FileErrorEventHandler
    let participants: ParticipantSpacesStorage
    let activeSpace: ActiveSpaceManager
    let applicationState: ApplicationStateService

    private let middleware: MiddlewareHandlerConfigurator
    private let viewProviders: ViewProvidersConfigurator
    private let listener: MiddlewareEventsListener
    private let invocation: any InvocationMesagesHandlerProtocol
    private var activeAttempt: OriginalEditorAccountRuntimeAttempt?
    private var localAccountLease: OriginalEditorLocalAccountLease?

    private init(
        appGroup: String,
        auth: PinkhaHanlinAuthService,
        accountEvents: AccountEventHandler,
        fileEvents: FileErrorEventHandler,
        participants: ParticipantSpacesStorage,
        activeSpace: ActiveSpaceManager,
        applicationState: ApplicationStateService,
        middleware: MiddlewareHandlerConfigurator,
        viewProviders: ViewProvidersConfigurator,
        listener: MiddlewareEventsListener,
        invocation: any InvocationMesagesHandlerProtocol
    ) {
        self.appGroup = appGroup
        self.auth = auth
        self.accountEvents = accountEvents
        self.fileEvents = fileEvents
        self.participants = participants
        self.activeSpace = activeSpace
        self.applicationState = applicationState
        self.middleware = middleware
        self.viewProviders = viewProviders
        self.listener = listener
        self.invocation = invocation
    }

    static func acquire(appGroup: String) throws -> OriginalEditorEmbeddedAccountProcess {
        if let installed {
            guard installed.appGroup.utf8.elementsEqual(appGroup.utf8) else {
                throw AnytypeOriginalEditorAccountSession.SessionError.incompatibleDeployment
            }
            try installed.validateInstallation()
            return installed
        }
        guard !installationStarted, InvocationSettings.handler == nil,
              InvocationDispatchContext.binding == nil else {
            throw AnytypeOriginalEditorAccountSession.SessionError.runtimeAlreadyOwned
        }

        // This accessor creates no original service, account or repository.
        _ = try AnytypeOriginalEditorModule.inspectResources()
        #if DEBUG || RELEASE_NIGHTLY
        try OriginalRuntimeEnvironment.configureEmbedded(appGroup: appGroup, expectedTarget: .debug)
        #elseif RELEASE_ANYTYPE
        try OriginalRuntimeEnvironment.configureEmbedded(appGroup: appGroup, expectedTarget: .releaseAnytype)
        #else
        throw AnytypeOriginalEditorAccountSession.SessionError.unsupportedBuildConfiguration
        #endif

        // After a successful immutable deployment installation, an unexpected
        // service/handler failure keeps the process claimed; it is never reset.
        installationStarted = true
        guard OriginalRuntimeEnvironment.deploymentMode == .embeddedEditor,
              let auth = Container.shared.authService() as? PinkhaHanlinAuthService,
              let accountEvents = Container.shared.accountEventHandler() as? AccountEventHandler,
              let fileEvents = Container.shared.fileErrorEventHandler() as? FileErrorEventHandler,
              let participants = Container.shared.participantSpacesStorage() as? ParticipantSpacesStorage,
              let activeSpace = Container.shared.activeSpaceManager() as? ActiveSpaceManager,
              let applicationState = Container.shared.applicationStateService() as? ApplicationStateService,
              let listener = Container.shared.middlewareEventsListener() as? MiddlewareEventsListener,
              InvocationSettings.handler == nil else {
            throw AnytypeOriginalEditorAccountSession.SessionError.originalServiceUnavailable
        }

        let middleware = MiddlewareHandlerConfigurator()
        middleware.configure()
        guard let invocation = InvocationSettings.handler else {
            throw AnytypeOriginalEditorAccountSession.SessionError.originalServiceUnavailable
        }
        let viewProviders = ViewProvidersConfigurator()
        viewProviders.configure()
        listener.startListening()

        let process = OriginalEditorEmbeddedAccountProcess(
            appGroup: appGroup, auth: auth, accountEvents: accountEvents, fileEvents: fileEvents,
            participants: participants, activeSpace: activeSpace, applicationState: applicationState,
            middleware: middleware, viewProviders: viewProviders, listener: listener, invocation: invocation
        )
        installed = process
        try process.validateInstallation()
        return process
    }

    func validateInstallation() throws {
        guard Self.installed === self,
              OriginalRuntimeEnvironment.deploymentMode == .embeddedEditor,
              InvocationSettings.handler === invocation,
              (Container.shared.authService() as? PinkhaHanlinAuthService) === auth else {
            throw AnytypeOriginalEditorAccountSession.SessionError.originalServiceUnavailable
        }
    }

    func makeAttempt(
        onReady: @escaping @MainActor (AnytypeOriginalEditorAccountSession) -> Void,
        onFailure: @escaping @MainActor (any Error) -> Void
    ) throws -> OriginalEditorAccountRuntimeAttempt {
        try validateInstallation()
        guard activeAttempt == nil, localAccountLease == nil, InvocationDispatchContext.binding == nil else {
            throw AnytypeOriginalEditorAccountSession.SessionError.runtimeAlreadyOwned
        }
        let attempt = try OriginalEditorAccountRuntimeAttempt(
            process: self, onReady: onReady, onFailure: onFailure
        )
        activeAttempt = attempt
        return attempt
    }

    func validateOwner(_ attempt: OriginalEditorAccountRuntimeAttempt) throws {
        try validateInstallation()
        guard activeAttempt === attempt else {
            throw AnytypeOriginalEditorAccountSession.SessionError.retired
        }
    }

    func release(_ attempt: OriginalEditorAccountRuntimeAttempt) throws {
        try validateOwner(attempt)
        // The caller reaches release only after its genuine Stop receipt,
        // original task drain, FIFO fence and subscription cleanup. Retire the
        // old in-memory account too; display IDs must not seed a local session.
        Container.shared.accountManager().account = .empty
        activeAttempt = nil
    }

    func claimLocalAccount() throws -> OriginalEditorLocalAccountLease {
        try validateInstallation()
        guard activeAttempt == nil, localAccountLease == nil,
              InvocationDispatchContext.binding == nil else {
            throw AnytypeOriginalEditorAccountSession.SessionError.runtimeAlreadyOwned
        }
        let lease = OriginalEditorLocalAccountLease()
        localAccountLease = lease
        return lease
    }

    func validateLocalAccount(_ lease: OriginalEditorLocalAccountLease) throws {
        try validateInstallation()
        guard localAccountLease === lease, activeAttempt == nil else {
            throw AnytypeOriginalEditorAccountSession.SessionError.retired
        }
    }

    func releaseLocalAccount(_ lease: OriginalEditorLocalAccountLease) throws {
        try validateLocalAccount(lease)
        localAccountLease = nil
    }
}

/// Internal reference identity only. Neither persisted data nor a public
/// account/Space ID can acquire or replace the shared installation's owner.
@MainActor
internal final class OriginalEditorLocalAccountLease {
    fileprivate init() {}
}

@MainActor
private final class OriginalEditorAccountSchemaOperation {
    private(set) var history: OriginalAnnotationSchemaCallHistory?
    private(set) var deliveryCount = 0

    func record(_ history: OriginalAnnotationSchemaCallHistory) {
        deliveryCount += 1
        self.history = history
    }
}

/// Owns presentation/consumer tasks, not an alternative authentication engine.
/// Every authentication operation belongs to the one frozen original caller.
/// The local Lifetime only retires this facade and its pending UI continuations.
@MainActor
@Observable
internal final class OriginalEditorAccountRuntimeAttempt {
    internal private(set) var coordinator: ApplicationCoordinatorViewModel?
    internal private(set) var spaces: [SpaceView] = []
    internal private(set) var selectedSpaceID: String?
    internal private(set) var isProcessing = false
    internal private(set) var hasFailure = false
    internal private(set) var isClosing = false
    internal private(set) var closeFailed = false
    internal private(set) var isClosed = false

    @ObservationIgnored private let process: OriginalEditorEmbeddedAccountProcess
    @ObservationIgnored private let lifetime: EditorDocumentWriteLifetime
    @ObservationIgnored private let capture: EditorDocumentWriteCapture
    @ObservationIgnored private var caller: OriginalEditorAuthCaller?
    @ObservationIgnored private var callerRetirement: EditorDocumentWriteLifetime.Observation?
    @ObservationIgnored private var registrationRetirements: [EditorDocumentWriteLifetime.Observation] = []
    @ObservationIgnored private var accountRegistration: EditorDocumentWriteCapture?
    @ObservationIgnored private var fileRegistration: EditorDocumentWriteCapture?
    @ObservationIgnored private var accountDemand: OriginalApplicationConsumerDemand?
    @ObservationIgnored private var fileDemand: OriginalApplicationConsumerDemand?

    @ObservationIgnored private var startupTask: Task<Void, Never>?
    @ObservationIgnored private var accountTask: Task<Void, Never>?
    @ObservationIgnored private var fileTask: Task<Void, Never>?
    @ObservationIgnored private var applicationTask: Task<Void, Never>?
    @ObservationIgnored private var spacesTask: Task<Void, Never>?
    @ObservationIgnored private var selectionTask: Task<Void, Never>?
    @ObservationIgnored private var closeTask: Task<Void, Error>?
    @ObservationIgnored private var authenticationClose: OriginalEditorAuthCloseReceipt?
    @ObservationIgnored private var schemaOperation: OriginalEditorAccountSchemaOperation?
    @ObservationIgnored private var selectedSession: AnytypeOriginalEditorAccountSession?
    @ObservationIgnored private var selectionRetirements: [EditorDocumentWriteLifetime.Observation] = []
    @ObservationIgnored private var selectionRestrictions: [EditorDocumentWriteCapture] = []
    @ObservationIgnored private var schemaResponse: Anytype_Rpc.Annotation.Schema.Register.Response?
    @ObservationIgnored private var selectionStarted = false
    @ObservationIgnored private weak var controller: UIViewController?
    @ObservationIgnored private var onReady: (@MainActor (AnytypeOriginalEditorAccountSession) -> Void)?
    @ObservationIgnored private var onFailure: (@MainActor (any Error) -> Void)?

    fileprivate init(
        process: OriginalEditorEmbeddedAccountProcess,
        onReady: @escaping @MainActor (AnytypeOriginalEditorAccountSession) -> Void,
        onFailure: @escaping @MainActor (any Error) -> Void
    ) throws {
        self.process = process
        self.onReady = onReady
        self.onFailure = onFailure
        let lifetime = EditorDocumentWriteLifetime()
        self.lifetime = lifetime
        capture = try EditorDocumentWriteCapture(lifetime)
    }

    internal func attach(controller: UIViewController) {
        precondition(self.controller == nil)
        self.controller = controller
    }

    internal func presentationDidAppear() {
        guard startupTask == nil, !isClosed, !isClosing else { return }
        startupTask = Task { @MainActor [self] in
            do {
                try await prepareOriginalConsumers()
            } catch {
                reportFailure(error)
                requestClose()
            }
        }
    }

    internal func presentationDidDismiss() {
        // Ready account/session lifetime deliberately outlives the auth screen.
        // Pending authentication is retired synchronously and truly drained.
        guard selectedSession == nil else { return }
        requestClose()
    }

    private func validateStartup(requireDemand: Bool = false) throws {
        try process.validateOwner(self)
        try capture.validate()
        guard let caller else {
            throw AnytypeOriginalEditorAccountSession.SessionError.retired
        }
        try caller.validateCurrent()
        try accountRegistration?.validate()
        try fileRegistration?.validate()
        for restriction in selectionRestrictions { try restriction.validate() }
        if requireDemand {
            guard let accountRegistration, let fileRegistration,
                  let accountDemand, let fileDemand else {
                throw AnytypeOriginalEditorAccountSession.SessionError.retired
            }
            try accountRegistration.validate()
            try fileRegistration.validate()
            try accountDemand.validateRequested()
            try fileDemand.validateRequested()
        }
    }

    private func prepareOriginalConsumers() async throws {
        try process.validateOwner(self)
        try capture.validate()
        let caller = try await process.auth.makeOriginalEditorCaller()
        self.caller = caller
        // observe() checks under the original lifetime lock; an earlier
        // dismissal cannot disappear while the actor creates this caller.
        callerRetirement = lifetime.observe(capture.token) { caller.retire() }
        try validateStartup()

        let accountRegistration = try await process.accountEvents.startEmbeddedSubscription()
        self.accountRegistration = accountRegistration
        retainRegistration(accountRegistration)
        try validateStartup()

        let fileRegistration = try await process.fileEvents.startEmbeddedSubscription()
        self.fileRegistration = fileRegistration
        retainRegistration(fileRegistration)
        try validateStartup()

        let model = ApplicationCoordinatorViewModel(originalEditorCaller: caller)
        coordinator = model
        let lifetime = lifetime
        let consumerEnded: @Sendable () -> Void = { [weak self, lifetime] in
            lifetime.markUnavailable()
            Task { @MainActor [weak self] in self?.requestClose() }
        }
        let accountDemand = OriginalApplicationConsumerDemand(onEnd: consumerEnded)
        let fileDemand = OriginalApplicationConsumerDemand(onEnd: consumerEnded)
        self.accountDemand = accountDemand
        self.fileDemand = fileDemand
        accountTask = Task { @MainActor in
            await model.startAccountStateHandler(readiness: accountDemand)
        }
        fileTask = Task { @MainActor in
            await model.startFileHandler(readiness: fileDemand)
        }

        try await accountDemand.waitUntilRequested()
        try validateStartup()
        try accountDemand.validateRequested()
        try await fileDemand.waitUntilRequested()
        try validateStartup(requireDemand: true)

        // Actual original state, only after both genuine downstream demands.
        // Its published current value is consumed by this retained original task.
        process.applicationState.state = .launch
        applicationTask = Task { @MainActor [self] in
            await model.startAppStateHandler()
            if !isClosing && !isClosed { requestClose() }
        }
        spacesTask = Task { @MainActor [self] in
            for await rows in process.participants.activeParticipantSpacesPublisher.values {
                guard !Task.isCancelled else { return }
                do {
                    try validateStartup(requireDemand: true)
                    spaces = rows.filter {
                        $0.spaceView.isActive && $0.canEdit && $0.spaceView.spaceType == .regular
                    }.map(\.spaceView)
                } catch {
                    reportFailure(error)
                    requestClose()
                    return
                }
            }
            if !isClosing && !isClosed { requestClose() }
        }
    }

    private func retainRegistration(_ registration: EditorDocumentWriteCapture) {
        let lifetime = lifetime
        registrationRetirements.append(registration.source.observe(registration.token) { [weak self, lifetime] in
            lifetime.markUnavailable()
            Task { @MainActor [weak self] in self?.requestClose() }
        })
    }

    internal func select(_ requested: SpaceView) {
        guard !selectionStarted, !isClosing, !isClosed, !hasFailure else { return }
        do {
            try validateStartup(requireDemand: true)
            guard coordinator?.applicationState == .home else {
                throw AnytypeOriginalEditorAccountSession.SessionError.unavailableSpace
            }
            let rows = process.participants.activeParticipantSpaces.filter {
                $0.spaceView.id.utf8.elementsEqual(requested.id.utf8)
                    && $0.spaceView.targetSpaceId.utf8.elementsEqual(requested.targetSpaceId.utf8)
                    && $0.canEdit && $0.spaceView.spaceType == .regular
            }
            guard rows.count == 1 else {
                throw AnytypeOriginalEditorAccountSession.SessionError.unavailableSpace
            }
            selectionStarted = true
            isProcessing = true
            let actualSpace = rows[0].spaceView
            selectionTask = Task { @MainActor [self] in
                do {
                    try await selectOriginalSpace(actualSpace)
                } catch {
                    reportFailure(error)
                    requestClose()
                }
                isProcessing = false
            }
        } catch {
            reportFailure(error)
            requestClose()
        }
    }

    private func selectOriginalSpace(_ space: SpaceView) async throws {
        try validateStartup(requireDemand: true)
        _ = try await process.activeSpace.setActiveSpace(spaceId: space.targetSpaceId)
        try validateStartup(requireDemand: true)
        let selected = try process.activeSpace.currentOriginalActiveSpaceSelection()
        try selected.validate()
        guard selected.accountInfo.accountSpaceId.utf8.elementsEqual(space.targetSpaceId.utf8),
              selected.accountInfo.spaceViewId.utf8.elementsEqual(space.id.utf8),
              let accountLifetime = Container.shared.accountManager().editorWriteLifetime else {
            throw AnytypeOriginalEditorAccountSession.SessionError.unavailableSpace
        }
        let accountCapture = try EditorDocumentWriteCapture(accountLifetime)
        let selectionCapture = try selected.capture(matching: accountCapture, spaceId: space.targetSpaceId)
        guard let participants = Container.shared.participantsStorage() as? ParticipantsStorage,
              let spaceViews = Container.shared.spaceViewsStorage() as? SpaceViewsStorage else {
            throw AnytypeOriginalEditorAccountSession.SessionError.originalServiceUnavailable
        }
        let participant = try participants.currentParticipantEditPermission(spaceId: space.targetSpaceId)
        let spaceView = try spaceViews.currentOriginalSpaceViewPermission(spaceId: space.targetSpaceId)
        let participantCapture = try participant.capture(matching: accountCapture, spaceId: space.targetSpaceId)
        let spaceViewCapture = try spaceView.capture(matching: accountCapture, spaceId: space.targetSpaceId)
        guard spaceView.originalSpaceView.id.utf8.elementsEqual(selected.accountInfo.spaceViewId.utf8) else {
            throw AnytypeOriginalEditorAccountSession.SessionError.unavailableSpace
        }
        // These are actual original permission/selection observations, frozen
        // under the same account capture. The picker supplies no authority.
        selectionRestrictions = [accountCapture, selectionCapture, participantCapture, spaceViewCapture]
        let lifetime = lifetime
        for restriction in selectionRestrictions {
            selectionRetirements.append(restriction.source.observe(restriction.token) { [weak self, lifetime] in
                lifetime.markUnavailable()
                Task { @MainActor [weak self] in self?.requestClose() }
            })
        }
        try validateStartup(requireDemand: true)
        try selected.validate()

        let operation = OriginalEditorAccountSchemaOperation()
        schemaOperation = operation
        let response = try await selected.registerOriginalAnnotationSchema { history in
            operation.record(history)
        }
        // The onDrained history above also retains failed/cancelled native
        // calls. Retain this normal return before later throwing currentness
        // checks; historical evidence alone never mints readiness.
        schemaResponse = response
        try validateStartup(requireDemand: true)
        try selected.validate()
        try validateReadySelection(selected)

        let session = try AnytypeOriginalEditorAccountSession(owner: self, selection: selected)
        selectedSession = session
        selectedSpaceID = selected.accountInfo.accountSpaceId
        try validate(session: session, selection: selected)
        let deliver = onReady
        onReady = nil
        deliver?(session)
    }

    fileprivate func validateReadySelection(_ selection: OriginalActiveSpaceSelection) throws {
        try validateStartup(requireDemand: true)
        try selection.validate()
        guard let operation = schemaOperation, let response = schemaResponse,
              operation.deliveryCount == 1,
              let history = operation.history, history.copyError == nil,
              let observed = history.response, observed == response,
              response.error.code == .null, response.hasRegistration,
              response.registration.appAdmitted,
              response.registration.schemaProtocol.utf8.elementsEqual(OriginalAnnotationNativeMetadata.protocolValue.utf8),
              response.registration.hasObservation,
              response.registration.observation.disposition.utf8.elementsEqual("MATCHING_SCHEMA_OBSERVED".utf8),
              response.registration.observation.hasTypeLayout,
              response.registration.observation.typeLayout.disposition.utf8.elementsEqual("MATCHING_SCHEMA_OBSERVED".utf8),
              response.registration.observation.accountIdentity.utf8.elementsEqual(selection.accountID.utf8),
              response.registration.observation.spaceID.utf8.elementsEqual(selection.accountInfo.accountSpaceId.utf8) else {
            throw AnytypeOriginalEditorAccountSession.SessionError.unobservedSchemaCompletion
        }
    }

    fileprivate func validate(
        session: AnytypeOriginalEditorAccountSession,
        selection: OriginalActiveSpaceSelection
    ) throws {
        try validateReadySelection(selection)
        guard selectedSession === session, !isClosing, !isClosed else {
            throw AnytypeOriginalEditorAccountSession.SessionError.retired
        }
    }

    fileprivate func makeAnnotationImportSourceBinding(
        session: AnytypeOriginalEditorAccountSession,
        selection: OriginalActiveSpaceSelection,
        sourceLifetime: EditorDocumentWriteLifetime,
        sourceIsCurrent: @escaping @MainActor () -> Bool
    ) throws -> EditorDocumentWriteSourceBinding {
        try validate(session: session, selection: selection)
        try capture.validate()
        // selectOriginalSpace freezes exactly account, selection, participant
        // and Space-view captures before the original schema registration.
        guard selectionRestrictions.count == 4,
              let originalAccount = selectionRestrictions.first,
              let actualAccount = Container.shared.accountManager().editorWriteLifetime,
              actualAccount === originalAccount.source else {
            throw AnytypeOriginalEditorAccountSession.SessionError.originalServiceUnavailable
        }
        let frozen = [capture] + selectionRestrictions
        for restriction in frozen { try restriction.validate() }
        let binding = try EditorDocumentWriteSourceBinding(
            lifetime: sourceLifetime,
            accountLifetime: actualAccount,
            additionalLifetimes: frozen.map(\.source),
            isCurrent: {
                guard (try? session.validateCurrent()) != nil else { return false }
                return sourceIsCurrent()
            }
        )
        // This constructor observes existing lifetimes. Require every observed
        // token to equal the already-held original token; a later generation
        // that looks like the same account/Space can never be recaptured here.
        for restriction in frozen {
            guard binding.captures.contains(where: {
                $0.source === restriction.source && $0.token == restriction.token
            }) else {
                throw AnytypeOriginalEditorAccountSession.SessionError.retired
            }
        }
        try binding.validate()
        return binding
    }

    private func reportFailure(_ error: any Error) {
        hasFailure = true
        onFailure?(error)
    }

    private func retireFacade() {
        lifetime.markUnavailable()
        caller?.retire()
        onReady = nil
        selectionTask?.cancel()
    }

    internal func requestClose() {
        retireFacade()
        guard !isClosed, !isClosing, !closeFailed else { return }
        _ = beginClose(retrying: false)
    }

    internal func requestRetryClose() {
        guard closeFailed, !isClosing, !isClosed else { return }
        _ = beginClose(retrying: true)
    }

    internal func close(retrying: Bool) async throws {
        retireFacade()
        if isClosed { return }
        let task: Task<Void, Error>
        if let closeTask, isClosing || !retrying {
            task = closeTask
        } else if closeFailed && !retrying {
            throw AnytypeOriginalEditorAccountSession.SessionError.closeRequiresExplicitRetry
        } else {
            task = beginClose(retrying: retrying && closeFailed)
        }
        // This task is never cancelled merely because an awaiting UI task is.
        try await task.value
    }

    private func beginClose(retrying: Bool) -> Task<Void, Error> {
        retireFacade()
        isClosing = true
        closeFailed = false
        let task = Task { @MainActor [self] in
            do {
                try await drainOwnedRuntime(retrying: retrying)
                isClosed = true
                isClosing = false
                spaces = []
                selectedSession = nil
                onFailure = nil
            } catch {
                isClosing = false
                closeFailed = true
                reportFailure(error)
                throw error
            }
        }
        closeTask = task
        return task
    }

    private func drainOwnedRuntime(retrying: Bool) async throws {
        // If caller construction is still pending, its actor has no throwing
        // path after installing without returning that exact caller. Startup
        // has no native authentication of its own; the separate original
        // app-state task is launched only after all readiness checks.
        if caller == nil, let startupTask { await startupTask.value }
        caller?.retire()

        if let caller, authenticationClose == nil {
            authenticationClose = try await (
                retrying ? caller.retryCloseAuthentication() : caller.closeAuthentication()
            )
        }

        // A failed Stop throws above. Never join a startup it may still own,
        // abandon its owner, or release the next attempt after such a failure.
        if let startupTask { await startupTask.value }
        if let selectionTask { await selectionTask.value }

        if caller != nil {
            // This original fence covers its accepted FIFO, not future native
            // events and not task cancellation. The actual Stop receipt is above.
            try await ServiceMessageHandlerAdapter.shared.waitForPendingEventDelivery()
        }

        accountTask?.cancel()
        fileTask?.cancel()
        applicationTask?.cancel()
        spacesTask?.cancel()
        accountDemand?.end()
        fileDemand?.end()
        if let accountTask { await accountTask.value }
        if let fileTask { await fileTask.value }
        if let applicationTask { await applicationTask.value }
        if let spacesTask { await spacesTask.value }

        // Account has a genuine original stop API. Stop only our still-current
        // registration. File has no stop API and remains process-owned.
        if let registration = accountRegistration, (try? registration.validate()) != nil {
            await process.accountEvents.stopSubscription()
        }
        callerRetirement?.cancel()
        for observation in registrationRetirements { observation.cancel() }
        for observation in selectionRetirements { observation.cancel() }

        if let caller {
            guard authenticationClose != nil else {
                throw AnytypeOriginalEditorAccountSession.SessionError.retired
            }
            try await caller.releaseAfterRuntimeDrain()
        }
        try process.release(self)
    }
}
