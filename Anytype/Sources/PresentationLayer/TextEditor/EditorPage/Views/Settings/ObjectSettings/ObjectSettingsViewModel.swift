import Foundation
import Services
import UIKit
import FloatingPanel
import SwiftUI
import AnytypeCore
import DeepLinks

enum ObjectSettingsAction {
    case cover(ObjectCoverPickerAction)
    case icon(ObjectIconPickerAction)
}

@MainActor
protocol ObjectSettingsModelOutput: AnyObject, ObjectHeaderRouterProtocol, ObjectHeaderModuleOutput {
    func undoRedoAction(objectId: String)
    func relationsAction(document: some BaseDocumentProtocol)
    func showVersionHistory(document: some BaseDocumentProtocol)
    func showPublising(document: some BaseDocumentProtocol)
    func openPageAction(screenData: ScreenData)
    func linkToAction(document: some BaseDocumentProtocol, onSelect: @escaping (String) -> ())
    func closeEditorAction()
    func didCreateLinkToItself(selfName: String, data: ScreenData)
    func didCreateTemplate(templateId: String)
    func didTapUseTemplateAsDefault(templateId: String)
    func showInviteMembers(spaceId: String)
    func showEditInfo(document: some BaseDocumentProtocol)
}

@MainActor
@Observable
final class ObjectSettingsViewModel {

    // MARK: - Settings Dependencies

    @Injected(\.openedDocumentProvider) @ObservationIgnored
    private var openDocumentsProvider: any OpenedDocumentsProviderProtocol
    @Injected(\.propertiesService) @ObservationIgnored
    private var propertiesService: any PropertiesServiceProtocol
    @Injected(\.objectSettingsBuilder) @ObservationIgnored
    private var settingsBuilder: any ObjectSettingsBuilderProtocol
    @Injected(\.objectSettingsConflictManager) @ObservationIgnored
    private var conflictManager: any ObjectSettingsPrimitivesConflictManagerProtocol

    // MARK: - Actions Dependencies

    @Injected(\.objectActionsService) @ObservationIgnored
    private var service: any ObjectActionsServiceProtocol
    @Injected(\.blockService) @ObservationIgnored
    private var blockService: any BlockServiceProtocol
    @Injected(\.templatesService) @ObservationIgnored
    private var templatesService: any TemplatesServiceProtocol
    @Injected(\.documentsProvider) @ObservationIgnored
    private var documentsProvider: any DocumentsProviderProtocol
    @Injected(\.channelPinsService) @ObservationIgnored
    private var channelPinsService: any ChannelPinsServiceProtocol
    @Injected(\.personalFavoritesService) @ObservationIgnored
    private var personalFavoritesService: any PersonalFavoritesServiceProtocol
    @Injected(\.spaceViewsStorage) @ObservationIgnored
    private var workspaceStorage: any SpaceViewsStorageProtocol
    @Injected(\.universalLinkParser) @ObservationIgnored
    private var universalLinkParser: any UniversalLinkParserProtocol
    @Injected(\.deepLinkParser) @ObservationIgnored
    private var deepLinkParser: any DeepLinkParserProtocol
    @Injected(\.workspaceService) @ObservationIgnored
    private var workspaceService: any WorkspaceServiceProtocol
    @Injected(\.participantSpacesStorage) @ObservationIgnored
    private var participantSpacesStorage: any ParticipantSpacesStorageProtocol
    @ObservationIgnored
    private weak var output: (any ObjectSettingsModelOutput)?
    @ObservationIgnored
    private let preparedSession: PreparedEditorPageSession?

    @ObservationIgnored
    private lazy var document: any BaseDocumentProtocol = {
        preparedSession?.document ?? openDocumentsProvider.document(objectId: objectId, spaceId: spaceId)
    }()

    // Both widget documents exist only to resolve the pin and favorite states, and both
    // of those actions are filtered out of the quick capture menu. Quick capture also
    // never activates the space, so its per-space `AccountInfo` is legitimately absent -
    // opening them there would assert on every space switch to compute nothing.
    private enum PreparedWidgetKind: Hashable {
        case channel
        case personal
    }

    @ObservationIgnored
    private var preparedWidgetSessions: [PreparedWidgetKind: PreparedEditorPageSession] = [:]
    @ObservationIgnored
    private var activePreparedWidgetSubscriptions: Set<PreparedWidgetKind> = []

    // External sources never evaluate the original provider's untracked open
    // Task. The retained target is acquired through the existing child factory.
    private var widgetObject: (any BaseDocumentProtocol)? {
        preparedSession == nil ? legacyWidgetObject : preparedWidgetSessions[.channel]?.document
    }

    @ObservationIgnored
    private lazy var legacyWidgetObject: (any BaseDocumentProtocol)? = {
        guard !quickCapture else { return nil }
        guard let info = workspaceStorage.spaceInfo(spaceId: spaceId) else {
            anytypeAssertionFailure("info not found")
            return nil
        }
        return openDocumentsProvider.document(objectId: info.widgetsId, spaceId: spaceId)
    }()

    // Uses per-space `AccountInfo` from `workspaceStorage` (not the global
    // `accountManager.account.info`) because personal widgets are per-space and
    // the global info can race app launch with `AccountData.empty`.
    private var personalWidgetsObject: (any BaseDocumentProtocol)? {
        preparedSession == nil ? legacyPersonalWidgetsObject : preparedWidgetSessions[.personal]?.document
    }

    @ObservationIgnored
    private lazy var legacyPersonalWidgetsObject: (any BaseDocumentProtocol)? = {
        guard !quickCapture else { return nil }
        guard let info = workspaceStorage.spaceInfo(spaceId: spaceId) else {
            anytypeAssertionFailure("info not found for personal widgets")
            return nil
        }
        return openDocumentsProvider.document(
            objectId: info.personalWidgetsId,
            spaceId: spaceId
        )
    }()

    @ObservationIgnored
    let objectId: String
    @ObservationIgnored
    let spaceId: String
    @ObservationIgnored
    private let quickCapture: Bool

    // MARK: - Settings State

    var settings: [ObjectSetting] = []
    var showConflictAlert = false
    var isChat = false
    let spaceType: SpaceType?

    // MARK: - Actions State

    var objectActions: [ObjectAction] = []
    private var canManageChannelPins: Bool = false
    private var isSpaceOwner: Bool = false
    private var chatNotificationMode: SpacePushNotificationsMode?
    var toastData: ToastBarData?
    var dismiss = false
    var showDeleteChatConfirmation = false

    init(
        objectId: String,
        spaceId: String,
        output: some ObjectSettingsModelOutput,
        quickCapture: Bool = false,
        preparedSession: PreparedEditorPageSession? = nil
    ) {
        self.objectId = objectId
        self.spaceId = spaceId
        self.output = output
        self.quickCapture = quickCapture
        self.preparedSession = preparedSession

        let spaceView = Container.shared.spaceViewsStorage().spaceView(spaceId: spaceId)
        spaceType = spaceView?.spaceType
    }

    var hasPreparedSource: Bool { preparedSession != nil }

    /// Uses the exact prepared document and both original identity fields.
    /// This synchronous boundary also keeps late UI publication inside the
    /// captured account and source admissions.
    func withCurrentSource<Value>(
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        _ operation: () throws -> Value
    ) throws -> Value {
        guard let preparedSession else { return try operation() }
        return try preparedSession.owner.performSynchronousOperation(
            contextId: objectId, spaceId: spaceId, requiresEditing: false,
            requiredPermissions: requiredPermissions
        ) {
            try preparedSession.owner.validateDocument(document)
            guard document.objectId.utf8.elementsEqual(objectId.utf8),
                  document.spaceId.utf8.elementsEqual(spaceId.utf8) else {
                throw EditorDocumentWriteError.rejected(.wrongContext)
            }
            return try operation()
        }
    }

    /// An original completion that begins another write must retain its named
    /// mutation authority. Cache, toast and presentation-only publication keep
    /// using withCurrentSource and cannot upgrade a surrounding read scope.
    private func withActionCallback<Value>(
        requiredPermissions: Set<EditorDocumentWritePermission>,
        _ operation: () throws -> Value
    ) throws -> Value {
        guard let preparedSession else { return try operation() }
        return try preparedSession.owner.performSynchronousDocumentAction(
            contextId: objectId, spaceId: spaceId, requiredPermissions: requiredPermissions
        ) {
            try preparedSession.owner.validateDocument(document)
            guard document.objectId.utf8.elementsEqual(objectId.utf8),
                  document.spaceId.utf8.elementsEqual(spaceId.utf8) else {
                throw EditorDocumentWriteError.rejected(.wrongContext)
            }
            return try operation()
        }
    }

    private func originalObjectActions() throws -> any ObjectActionsServiceProtocol {
        guard preparedSession != nil else { return service }
        return try OriginalObjectActionsServiceBinding.requireOriginal(service)
    }

    private func originalProperties() throws -> any PropertiesServiceProtocol {
        guard preparedSession != nil else { return propertiesService }
        return try OriginalPropertiesServiceBinding.requireOriginal(propertiesService)
    }

    /// Called synchronously by the original menu/confirmation button before
    /// it creates its existing Task. No new owner or dispatch authority exists.
    func prepareAction(
        requiredPermissions: Set<EditorDocumentWritePermission>,
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) -> @MainActor @Sendable () async throws -> Void {
        guard let preparedSession else { return operation }
        do {
            let scheduled = try preparedSession.owner.scheduleDocumentAction(
                contextId: objectId, requiredPermissions: requiredPermissions
            )
            return { try await scheduled.run(operation: operation) }
        } catch {
            // The same Owner records rejected UI intent for the capture barrier.
            return { throw error }
        }
    }

    private func performAction<Value: Sendable>(
        requiredPermissions: Set<EditorDocumentWritePermission>,
        operation: @MainActor @Sendable () async throws -> Value
    ) async throws -> Value {
        guard let preparedSession else { return try await operation() }
        return try await preparedSession.owner.performDocumentAction(
            contextId: objectId, requiredPermissions: requiredPermissions
        ) { @MainActor [self] in
            try withCurrentSource {}
            return try await operation()
        }
    }

    /// Foreign channel/Space writers and not-yet-bound modal writers are not
    /// authorized by a page Owner. Keep their original nil route and visible
    /// menu entries; the prepared Host must fail closed until the exact target
    /// and its original service graph are qualified separately.
    private func requireQualifiedTarget() throws {
        guard let preparedSession else { return }
        try preparedSession.owner.performSynchronousOperation(
            contextId: objectId, spaceId: spaceId
        ) {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
    }

    // MARK: - Subscriptions

    func startDocumentTask() async {
        guard (try? withCurrentSource {}) != nil else { return }
        async let documentSub: () = startDocumentSubscription()
        async let widgetSub: () = startWidgetDocSubscription(kind: .channel)
        async let personalWidgetSub: () = startWidgetDocSubscription(kind: .personal)
        async let participantSub: () = startParticipantSpaceViewSubscription()
        async let spaceViewSub: () = startSpaceViewSubscription()
        _ = await (documentSub, widgetSub, personalWidgetSub, participantSub, spaceViewSub)
    }

    private func startDocumentSubscription() async {
        for await _ in document.syncPublisher.receiveOnMain().values {
            guard (try? withCurrentSource {}) != nil else { return }
            updateSettings()
            updateActions()
        }
    }

    private func startWidgetDocSubscription(kind: PreparedWidgetKind) async {
        guard let preparedSession else {
            await startWidgetDocSubscription(kind == .channel ? widgetObject : personalWidgetsObject)
            return
        }
        guard !quickCapture, activePreparedWidgetSubscriptions.insert(kind).inserted else { return }
        defer { activePreparedWidgetSubscriptions.remove(kind) }
        do {
            let targetId = try withCurrentSource { try originalWidgetID(kind: kind) }
            let childPreparation = try PreparedEditorChildPreparation(owner: preparedSession.owner)
            let session = try await childPreparation.prepare(data: EditorPageObject(
                objectId: targetId, spaceId: spaceId, mode: .handling, usecase: .embedded
            ))
            defer {
                session.retire()
                if preparedWidgetSessions[kind] === session {
                    preparedWidgetSessions[kind] = nil
                }
            }
            try Task.checkCancellation()
            try withCurrentSource {
                try validatePreparedWidget(session, kind: kind)
                preparedWidgetSessions[kind] = session
                updateActions()
            }
            for await _ in session.document.syncPublisher.values {
                try Task.checkCancellation()
                try withCurrentSource {
                    try validatePreparedWidget(session, kind: kind)
                    updateActions()
                }
            }
        } catch {
            // Acquisition failure never falls back to a cached/raw-open target.
            // The visible original action rejects until this actual target is
            // acquired; an attempted write still enters the parent failure latch.
            return
        }
    }

    private func originalWidgetID(kind: PreparedWidgetKind) throws -> String {
        guard workspaceStorage is SpaceViewsStorage,
              let info = workspaceStorage.spaceInfo(spaceId: spaceId) else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        let targetId = kind == .channel ? info.widgetsId : info.personalWidgetsId
        guard !targetId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !targetId.utf8.elementsEqual(objectId.utf8) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        return targetId
    }

    private func validatePreparedWidget(
        _ session: PreparedEditorPageSession, kind: PreparedWidgetKind
    ) throws {
        let targetId = try originalWidgetID(kind: kind)
        try session.owner.performSynchronousOperation(
            contextId: targetId, spaceId: spaceId, requiresEditing: false
        ) {
            try session.owner.validateDocument(session.document)
            guard session.document.isOpened, session.document.mode.isHandling,
                  session.data.objectId.utf8.elementsEqual(targetId.utf8),
                  session.data.spaceId.utf8.elementsEqual(spaceId.utf8),
                  session.document.objectId.utf8.elementsEqual(targetId.utf8),
                  session.document.spaceId.utf8.elementsEqual(spaceId.utf8) else {
                throw EditorDocumentWriteError.rejected(.wrongContext)
            }
        }
    }

    private func startWidgetDocSubscription(_ doc: (any BaseDocumentProtocol)?) async {
        guard let doc else { return }
        for await _ in doc.syncPublisher.values {
            guard (try? withCurrentSource {}) != nil else { return }
            updateActions()
        }
    }

    private func startParticipantSpaceViewSubscription() async {
        for await participantSpaceView in participantSpacesStorage.participantSpaceViewPublisher(spaceId: spaceId).values {
            guard (try? withCurrentSource {
                canManageChannelPins = participantSpaceView.canManageChannelPins
                isSpaceOwner = participantSpaceView.isOwner
                updateActions()
            }) != nil else { return }
        }
    }

    private func startSpaceViewSubscription() async {
        for await spaceView in workspaceStorage.spaceViewPublisher(spaceId: spaceId).values {
            guard (try? withCurrentSource {
                chatNotificationMode = spaceView.effectiveNotificationMode(for: objectId)
                updateSettings()
            }) != nil else { return }
        }
    }

    private func updateSettings() {
        try? withCurrentSource {
            if let details = document.details {
                settings = settingsBuilder.build(
                    details: details,
                    permissions: document.permissions,
                    spaceType: spaceType,
                    chatNotificationMode: chatNotificationMode
                )
                isChat = details.resolvedLayoutValue.isChat
            }
        }
    }

    private func updateActions() {
        try? withCurrentSource {
            guard let details = document.details else {
                objectActions = []
                return
            }

            let isPinnedToWidgets = widgetObject?.widgetBlockIdFor(targetObjectId: objectId).isNotNil ?? false
            let isFavorited = personalWidgetsObject?.containsWidgetFor(objectId: objectId) ?? false

            objectActions = ObjectAction.buildActions(
                details: details,
                isLocked: document.isLocked,
                isPinnedToWidgets: isPinnedToWidgets,
                isFavorited: isFavorited,
                canManageChannelPins: canManageChannelPins,
                permissions: document.permissions,
                spaceType: spaceType,
                isSpaceOwner: isSpaceOwner
            )
        }
    }

    func onTapIconPicker() {
        try? withCurrentSource(requiredPermissions: [.changeIcon]) {
            output?.showIconPicker(document: document)
        }
    }
    
    func onTapCoverPicker() {
        try? withCurrentSource(requiredPermissions: [.changeCover]) {
            output?.showCoverPicker(document: document)
        }
    }
    
    func onTapRelations() {
        try? withCurrentSource { output?.relationsAction(document: document) }
    }
    
    func onTapHistory() {
        do {
            try withCurrentSource {
                // The original set-version renderer still needs its own
                // prepared set session. Never mount it with a page owner.
                if preparedSession != nil, document.details?.isList != false {
                    throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
                }
                output?.showVersionHistory(document: document)
            }
        } catch { }
    }
    
    func onTapDescription() async throws {
        try await performAction(requiredPermissions: [.toggleDescription]) { [self] in
            guard let details = document.details else { return }
            let descriptionIsOn = details.featuredRelations.contains(where: { $0 == BundledPropertyKey.description.rawValue })
            let properties = try originalProperties()
            try await properties.toggleDescription(objectId: document.objectId, isOn: !descriptionIsOn)
        }
    }
    
    func onTapPrefillName() async throws {
        try await performAction(requiredPermissions: [.editDetails]) { [self] in
            guard let details = document.details else { return }
            let newValue = details.isTemplateNamePrefilled ? 0 : 1
            let actions = try originalObjectActions()
            try await actions.updateBundledDetails(
                contextID: document.objectId,
                details: [.templateNamePrefillType(newValue)]
            )
        }
    }

    func onTapResolveConflict() {
        try? withCurrentSource { showConflictAlert.toggle() }
    }
    
    func onTapResolveConflictApprove() async throws {
        try await performAction(requiredPermissions: [.changeLayout, .editPropertiesList]) { [self] in
            guard let details = document.details else { return }
            let conflicts = preparedSession == nil ? conflictManager
                : try OriginalObjectSettingsConflictManagerBinding.requireOriginal(conflictManager)
            try await conflicts.resolveConflicts(details: details)
            try withCurrentSource { AnytypeAnalytics.instance().logResetToTypeDefault() }
        }
    }
    
    func onTapPublishing() {
        do {
            try requireQualifiedTarget()
            try withCurrentSource(requiredPermissions: [.publish]) {
                if let details = document.details {
                    AnytypeAnalytics.instance().logClickShareObject(objectType: details.objectType.analyticsType)
                }
                output?.showPublising(document: document)
            }
        } catch { }
    }

    func changeNotificationMode(_ mode: SpacePushNotificationsMode) async throws {
        try requireQualifiedTarget()
        try await workspaceService.pushNotificationSetChatMode(
            spaceId: spaceId,
            chatIds: [objectId],
            mode: mode
        )
        AnytypeAnalytics.instance().logChangeMessageNotificationState(
            type: mode.analyticsValue,
            route: .chatSettings,
            uxType: .chat
        )
        dismiss.toggle()
    }

    // MARK: - Object Actions

    func changeArchiveState() async throws {
        try await performAction(requiredPermissions: [.archive]) { [self] in
            guard let details = document.details else { return }
            let isArchived = !details.isArchived
            AnytypeAnalytics.instance().logMoveToBin(isArchived)
            let actions = try originalObjectActions()
            try await actions.setArchive(objectIds: [objectId], isArchived)
            if isArchived {
                try withCurrentSource {
                    dismiss.toggle()
                    output?.closeEditorAction()
                }
            }
        }
    }

    func changePinState() async throws {
        try requireQualifiedTarget()
        // TODO: IOS-5864 No dedicated pin/unpin analytics event exists today.
        // Add `logPinObject` / `logUnpinObject` (or a unified `logChangePinState(pinned:)`)
        // once product confirms the event shape. Reorder already has `logReorderWidget`.
        guard let widgetObject else {
            anytypeAssertionFailure("Widget object not found")
            return
        }

        guard let details = document.details else {
            anytypeAssertionFailure("Details object not found")
            return
        }

        // Per-object-type layout: a Set pins as `.view` with limit 6, a regular page
        // pins as `.link` with limit 0, etc. Preserved from the pre-IOS-5864 shape so
        // Object Settings pin semantics stay richer than the widget-menu flow (which
        // always uses `.link`/`0`).
        guard let layout = details.availableWidgetLayout.first else {
            anytypeAssertionFailure("Default layout not found")
            return
        }

        let wasPinned = widgetObject.widgetBlockIdFor(targetObjectId: details.id).isNotNil

        try await channelPinsService.toggle(
            objectId: details.id,
            channelWidgetsObject: widgetObject,
            layout: layout,
            limit: layout.limits.first ?? 0
        )

        toastData = ToastBarData(wasPinned ? Loc.unpinned : Loc.pinned)
        dismiss.toggle()
    }

    func changeFavoriteState() async throws {
        if preparedSession != nil {
            try await changePreparedFavoriteState()
            return
        }
        // TODO: IOS-5864 No dedicated favorite/unfavorite analytics event exists today.
        // Add `logFavoriteObject` / `logUnfavoriteObject` (or a unified
        // `logChangeFavoriteState(favorited:)`) once product confirms the event shape.
        // Reorder of My Favorites is already covered via `logReorderWidget(source: .personalFavorites)`.
        guard let details = document.details else {
            anytypeAssertionFailure("Details object not found")
            return
        }
        guard let personalWidgetsObject else {
            anytypeAssertionFailure("personalWidgetsObject not found for favorite toggle")
            return
        }
        let wasFavorited = personalWidgetsObject.containsWidgetFor(objectId: details.id)
        try await personalFavoritesService.toggle(objectId: details.id, personalWidgetsObject: personalWidgetsObject)
        toastData = ToastBarData(wasFavorited ? Loc.unfavorited : Loc.favorited)
        dismiss.toggle()
    }

    private func changePreparedFavoriteState() async throws {
        try await performAction(requiredPermissions: [.applyUneditableActions]) { [self] in
            let session = try withCurrentSource {
                guard let session = preparedWidgetSessions[.personal] else {
                    throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
                }
                try validatePreparedWidget(session, kind: .personal)
                return session
            }
            let service = try PersonalFavoritesService.requireOriginal(personalFavoritesService)
            let wasFavorited = try await session.owner.performMutation(
                contextId: session.data.objectId,
                onDrained: { [session] in withExtendedLifetime(session) {} }
            ) { @MainActor [self] in
                try withCurrentSource(requiredPermissions: [.applyUneditableActions]) {
                    try validatePreparedWidget(session, kind: .personal)
                    guard let details = document.details,
                          details.id.utf8.elementsEqual(objectId.utf8),
                          details.isVisibleLayout(spaceType: spaceType),
                          !details.isTemplate,
                          details.resolvedLayoutValue != .participant else {
                        throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
                    }
                }
                let wasFavorited = session.document.containsWidgetFor(objectId: objectId)
                try await service.toggle(objectId: objectId, personalWidgetsObject: session.document)
                return wasFavorited
            }
            try withCurrentSource {
                try validatePreparedWidget(session, kind: .personal)
                toastData = ToastBarData(wasFavorited ? Loc.unfavorited : Loc.favorited)
                dismiss.toggle()
            }
        }
    }

    func changeLockState() async throws {
        try await performAction(requiredPermissions: [.lock]) { [self] in
            let isCurrentlyLocked = document.isLocked
            AnytypeAnalytics.instance().logLockPage(!isCurrentlyLocked)
            let actions = try originalObjectActions()
            try await actions.setLocked(!isCurrentlyLocked, objectId: objectId)
            try withCurrentSource {
                toastData = ToastBarData(isCurrentlyLocked ? Loc.unlocked : Loc.locked)
                dismiss.toggle()
            }
        }
    }

    func duplicateAction() async throws {
        try await performAction(requiredPermissions: [.duplicate]) { [self] in
            guard let details = document.details else { return }
            AnytypeAnalytics.instance().logDuplicateObject(count: 1, objectType: details.objectType.analyticsType)
            let actions = try originalObjectActions()
            let duplicatedId = try await actions.duplicate(objectId: objectId)
            try withCurrentSource {
                let newDetails = ObjectDetails(id: duplicatedId, values: details.values)
                dismiss.toggle()
                output?.openPageAction(screenData: newDetails.screenData())
            }
        }
    }

    func linkItselfAction() {
        do {
            // A selected foreign target still needs its own acquired Owner.
            try requireQualifiedTarget()
            try withCurrentSource {
                guard let currentObjectId = document.details?.id else { return }
                let spaceId = document.spaceId
                let onObjectSelection: (String) -> Void = { [weak self] objectId in
                    self?.onObjectSelection(objectId: objectId, spaceId: spaceId, currentObjectId: currentObjectId)
                }
                output?.linkToAction(document: document, onSelect: onObjectSelection)
            }
        } catch { }
    }

    func makeAsTemplate() async throws {
        try await performAction(requiredPermissions: [.makeAsTemplate]) { [self] in
            guard let details = document.details else { return }
            let templates = preparedSession?.services.router.templateService ?? templatesService
            let templateId = try await templates.createTemplateFromObject(objectId: details.id)
            try withCurrentSource {
                AnytypeAnalytics.instance().logTemplateCreate(objectType: details.objectType.analyticsType)
                output?.didCreateTemplate(templateId: templateId)
            }
        }
    }

    func templateToggleDefaultState() async throws {
        try withActionCallback(requiredPermissions: [.templateSetAsDefault]) {
            guard let details = document.details,
                  let targetObjectType = details.targetObjectTypeValue else { return }
            let isCurrentlyDefault = targetObjectType.defaultTemplateId == details.id
            let newTemplateId = isCurrentlyDefault ? "" : details.id
            output?.didTapUseTemplateAsDefault(templateId: newTemplateId)
        }
    }

    func deleteAction() async throws {
        try await performAction(requiredPermissions: [.delete]) { [self] in
            guard let details = document.details else { return }
            AnytypeAnalytics.instance().logDeletion(count: 1, route: .bin)
            let actions = try originalObjectActions()
            try await actions.delete(objectIds: [details.id])
            try withCurrentSource {
                dismiss.toggle()
                output?.closeEditorAction()
            }
        }
    }

    func copyLinkAction() async throws {
        guard let details = try withCurrentSource(requiredPermissions: [.share], { document.details }) else { return }
        let invite: SpaceInvite?
        if let preparedSession {
            let workspace = workspaceService
            invite = try? await preparedSession.owner.performRead(
                contextId: objectId, spaceId: spaceId, rpcNames: ["SpaceInviteGetCurrent"],
                requiredPermissions: [.share]
            ) {
                try await workspace.getCurrentInvite(spaceId: details.spaceId)
            }
        } else {
            invite = try? await workspaceService.getCurrentInvite(spaceId: details.spaceId)
        }
        try withCurrentSource(requiredPermissions: [.share]) {
            let hasLink = invite?.hasLink ?? false
            let link = universalLinkParser.createUrl(link: .object(objectId: details.id, spaceId: details.spaceId, cid: hasLink ? invite?.cid : nil, key: hasLink ? invite?.fileKey : nil))
            UIPasteboard.general.string = link?.absoluteString
            toastData = ToastBarData(Loc.copied)
            dismiss.toggle()
        }
    }

    func copyDeepLinkAction() async throws {
        try withCurrentSource {
            guard let details = document.details else { return }
            let link = deepLinkParser.createUrl(
                deepLink: .object(objectId: details.id, spaceId: details.spaceId, cid: nil, key: nil),
                scheme: .main
            )
            UIPasteboard.general.string = link?.absoluteString
            toastData = ToastBarData(Loc.copied)
            dismiss.toggle()
        }
    }

    func undoRedoAction() {
        try? withCurrentSource(requiredPermissions: [.undoRedo]) {
            output?.undoRedoAction(objectId: objectId)
        }
    }

    func inviteMembersAction() {
        do {
            try requireQualifiedTarget()
            try withCurrentSource {
                output?.showInviteMembers(spaceId: spaceId)
                dismiss.toggle()
            }
        } catch { }
    }

    func editInfoAction() {
        do {
            try requireQualifiedTarget()
            try withCurrentSource(requiredPermissions: [.editDetails]) {
                output?.showEditInfo(document: document)
            }
        } catch { }
    }

    // MARK: - Private Action Helpers

    private func onObjectSelection(objectId: String, spaceId: String, currentObjectId: String) {
        guard (try? requireQualifiedTarget()) != nil else { return }
        Task { @MainActor in
            let targetDocument = documentsProvider.document(objectId: objectId, spaceId: spaceId, mode: .preview)
            try? await targetDocument.open()
            guard let id = targetDocument.children.last?.id,
                  let details = targetDocument.details else { return }

            if details.isCollection {
                try await service.addObjectsToCollection(
                    contextId: objectId,
                    objectIds: [currentObjectId]
                )
                onLinkItselfToObjectHandler(data: details.screenData())
                AnytypeAnalytics.instance().logLinkToObject(type: .collection)
            } else {
                let info = BlockInformation.emptyLink(targetId: currentObjectId)
                AnytypeAnalytics.instance().logCreateBlock(type: info.content.type, spaceId: details.spaceId)
                let _ = try await blockService.add(
                    contextId: objectId,
                    targetId: id,
                    info: info,
                    position: .bottom
                )
                onLinkItselfToObjectHandler(data: details.screenData())
                AnytypeAnalytics.instance().logLinkToObject(type: .object)
            }
        }
    }

    private func onLinkItselfToObjectHandler(data: ScreenData) {
        guard let documentName = document.details?.name else { return }
        output?.didCreateLinkToItself(selfName: documentName, data: data)
    }
}
