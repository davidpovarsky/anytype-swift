import Foundation

@MainActor
private func lifetimeData(_ document: LifetimeDocumentProbe) -> EditorPageObject {
    .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode)
}

@MainActor
private func lifetimeFailure(_ operation: () async throws -> Void) async -> EditorDocumentWriteError? {
    do { try await operation(); return nil }
    catch { return error as? EditorDocumentWriteError }
}

actor LifetimeCloseService {
    private(set) var calls: [String] = []
    var fails = false
    var closeGate: OwnershipGate?
    func setFailure(_ value: Bool) { fails = value }
    func holdOn(_ gate: OwnershipGate) { closeGate = gate }
    func close(contextId: String, spaceId: String) async throws {
        calls.append(contextId + ":" + spaceId)
        await closeGate?.hold()
        if fails { throw TextProbeFailure.deliberate }
    }
}

struct ObjectViewModel: Sendable {}
struct LifetimeViewModelSetter: Sendable { func objectViewUpdate(_ model: ObjectViewModel) {} }

struct LifetimeUserInfo: Sendable { let usersId: String }
struct LifetimeRestrictions: Sendable { var objectRestriction: [ObjectRestriction] = [] }

final class LifetimeDocumentProbe: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, @unchecked Sendable {
    private struct State {
        var opened = true
        var permissions = ObjectPermissions()
        var participantEditor = true
        var locked = false
        var lifetime = EditorDocumentWriteLifetime()
    }
    private let lock = NSLock()
    private var state: State
    let objectId: String
    let spaceId = "owned-space"
    let mode: DocumentMode
    let objectLifecycleService = LifetimeCloseService()
    let viewModelSetter = LifetimeViewModelSetter()
    let basicUserInfoStorage: LifetimeUserInfo
    let infoContainer: any InfoContainerProtocol = FixtureInfo()
    let detailsStorage = ObjectDetailsStorage()
    let objectRestrictions = LifetimeRestrictions()
    let lifecycle = DocumentLifecycleProbe()
    init(object: String = "owned", mode: DocumentMode = .handling, users: String = "fixture") {
        objectId = object; self.mode = mode
        basicUserInfoStorage = .init(usersId: users)
        var initial = State()
        initial.permissions = ObjectPermissions(details: ObjectDetails(id: object), isLocked: false,
            participantCanEdit: true, isVersionMode: mode.isVersion, objectRestrictions: [])
        state = initial
    }
    private func read<T>(_ body: (State) -> T) -> T {
        lock.lock(); defer { lock.unlock() }; return body(state)
    }
    private func write(_ body: (inout State) -> Void) {
        lock.lock(); defer { lock.unlock() }; body(&state)
    }
    var editorWriteLifetime: EditorDocumentWriteLifetime { read { $0.lifetime } }
    var isOpened: Bool {
        get { read { $0.opened } }
        set { write { $0.opened = newValue } }
    }
    var permissions: ObjectPermissions {
        get { read { $0.permissions } }
        set { write { $0.permissions = newValue } }
    }
    var participantIsEditor: Bool {
        get { read { $0.participantEditor } }
        set { write { $0.participantEditor = newValue } }
    }
    var isLocked: Bool {
        get { read { $0.locked } }
        set { write { $0.locked = newValue } }
    }
    var children: [BlockInformation] { [] }
    var parsedProperties: ParsedProperties { ParsedProperties() }
    var isEmpty: Bool { false }
    var details: ObjectDetails? { ObjectDetails(id: objectId) }
    var syncStatus: SpaceSyncStatus? { nil }
    var syncPublisher: AnyPublisher<[BaseDocumentUpdate], Never> { AnyPublisher() }
    func subscibeFor(update: [BaseDocumentUpdate]) -> AnyPublisher<[BaseDocumentUpdate], Never> { AnyPublisher() }
    @MainActor func open() async throws { await lifecycle.record("open") }
    @MainActor func update() async throws { await lifecycle.record("update") }
    @MainActor func reopenForFixture() { setupView(ObjectViewModel()) }
    @MainActor private func setupSubscriptions() {}
    private func triggerSync(updates: [DocumentUpdate]) { _ = triggerUpdatePermissions(updates: updates) }
    @MainActor func replaceLifetimeForFixture() { write { $0.lifetime = EditorDocumentWriteLifetime() } }
    @MainActor func applyPermissionForFixture(_ canEdit: Bool) -> [BaseDocumentUpdate] {
        participantIsEditor = canEdit
        return triggerUpdatePermissions(updates: [.restrictions])
    }
    @MainActor func irrelevantUpdateForFixture() -> [BaseDocumentUpdate] {
        triggerUpdatePermissions(updates: [.syncStatus])
    }
    // Exact source methods/close-event branch are appended by the driver below.
    // SOURCE_HOOKS
}

@MainActor
private func session(
    _ document: LifetimeDocumentProbe,
    text: any TextServiceProtocol = TextProbe(),
    events: any EditorLocalEventPublishing = LocalPublisherProbe()
) throws -> PreparedEditorPageSession {
    try PreparedEditorPageSession(data: lifetimeData(document), document: document,
        textService: text, services: fixtureServices(events: events))
}

@main
struct OriginalEditorLifetimeFixture {
    @MainActor static func main() async throws {
        let checks = BoundaryChecks()
        let body = MiddlewareString(text: "שלום English 👩🏽‍💻")

        let source = EditorDocumentWriteLifetime()
        let token = source.token()!
        let observer = CallbackRecorder()
        let subscription = source.observe(token) { observer.add() }
        source.invalidate(); source.invalidate()
        checks.expect(!source.isCurrent(token) && observer.value == 1, "source_invalidation_is_synchronous_and_observer_is_one_use")
        subscription.cancel()
        let late = source.observe(token) { observer.add() }
        checks.expect(observer.value == 2, "registration_after_invalidation_cannot_lose_revocation")
        late.cancel()
        let current = source.token()!
        let cancelled = source.observe(current) { observer.add() }
        cancelled.cancel(); source.invalidate()
        checks.expect(observer.value == 2, "cancelled_observation_does_not_deliver")
        let reentrant = source.observe(source.token()!) { _ = source.token(); observer.add() }
        source.invalidate()
        checks.expect(observer.value == 3, "invalidation_callbacks_run_outside_the_state_lock")
        reentrant.cancel()

        let unavailable = EditorDocumentWriteLifetime(isAvailable: false)
        let initiallyRefused = unavailable.token() == nil
        unavailable.confirmOpened()
        checks.expect(initiallyRefused && unavailable.token() != nil,
            "unopened_lifetime_requires_explicit_open_confirmation")

        let leaseLifetime = EditorDocumentWriteLifetime()
        let priorLeaseToken = leaseLifetime.token()!
        let firstCloseLease = leaseLifetime.beginClosing()
        let secondCloseLease = leaseLifetime.beginClosing()
        leaseLifetime.confirmOpened()
        checks.expect(leaseLifetime.token() == nil && !leaseLifetime.isCurrent(priorLeaseToken),
            "overlapping_closes_refuse_open_confirmation")
        firstCloseLease.cancel(); firstCloseLease.cancel()
        leaseLifetime.confirmOpened()
        checks.expect(leaseLifetime.token() == nil,
            "one_close_lease_or_duplicate_release_cannot_end_another_close")
        secondCloseLease.cancel()
        let stillUnavailable = leaseLifetime.token() == nil
        leaseLifetime.confirmOpened()
        checks.expect(stillUnavailable && leaseLifetime.token() != nil,
            "close_completion_requires_a_later_explicit_open_confirmation")

        for mode in ["close", "permission"] {
            let document = LifetimeDocumentProbe()
            var drains = 0
            let owner = try EditorDocumentWriteOwner(data: lifetimeData(document), lifetimeDocument: document,
                onDrained: { drains += 1 })
            let gate = OwnershipGate(), destination = TextProbe()
            let writer = DocumentOwnedTextService(owner: owner,
                service: HeldOwnershipTextService(gate: gate, target: destination))
            let operation = Task { try await writer.setText(contextId: "owned", blockId: "a", middlewareString: body) }
            await gate.waitForEntry()
            if mode == "close" {
                try await document.close()
                document.reopenForFixture()
            } else {
                _ = document.applyPermissionForFixture(false)
                _ = document.applyPermissionForFixture(true)
            }
            checks.expect(owner.isRetired && document.isOpened && document.permissions.canEditBlocks,
                mode + "_restore_does_not_renew_retained_authority")
            let denied = await lifetimeFailure {
                try await writer.checked(contextId: "owned", blockId: "a", newValue: true)
            }
            checks.expect(denied == .rejected(.retired) && owner.pendingOperationCount == 1,
                mode + "_aba_refuses_new_dispatch_while_old_write_is_held")
            await gate.release()
            let completed = await lifetimeFailure { try await operation.value }
            let actual = await destination.snapshot()
            checks.expect(completed == .completedWithoutOwnership(.retired) && actual.count == 1
                          && owner.isDrained && drains == 1,
                mode + "_aba_preserves_actual_admitted_write_and_drains_once")
            let fresh = try EditorDocumentWriteOwner(data: lifetimeData(document), lifetimeDocument: document)
            let freshWriter = DocumentOwnedTextService(owner: fresh, service: destination)
            try await freshWriter.checked(contextId: "owned", blockId: "a", newValue: true)
            let renewed = await destination.snapshot()
            checks.expect(renewed.count == 2 && !fresh.isRetired, mode + "_recovery_requires_an_explicit_fresh_owner")
        }

        for mode in ["close", "permission"] {
            let document = LifetimeDocumentProbe()
            var drains = 0
            let owner = try EditorDocumentWriteOwner(data: lifetimeData(document), lifetimeDocument: document,
                onDrained: { drains += 1 })
            let gate = OwnershipGate(), destination = LocalPublisherProbe()
            let publisher = DocumentOwnedLocalEventPublisher(owner: owner,
                publisher: HeldOwnershipPublication(gate: gate, target: destination))
            let operation = Task { await publisher.setStyle(contextId: "owned", blockId: "a") }
            await gate.waitForEntry()
            if mode == "close" {
                try await document.close(); document.reopenForFixture()
            } else {
                _ = document.applyPermissionForFixture(false); _ = document.applyPermissionForFixture(true)
            }
            checks.expect(owner.isRetired && owner.pendingOperationCount == 1 && drains == 0,
                mode + "_aba_invalidates_publication_authority_before_actor_notification")
            await gate.release(); await operation.value
            await publisher.setText(contextId: "owned", blockId: "a", text: body)
            let events = await destination.snapshot()
            checks.expect(events.count == 1 && owner.isRetired && owner.isDrained && drains == 1,
                mode + "_aba_records_prior_delivery_but_refuses_new_publication")
        }

        let closingDocument = LifetimeDocumentProbe()
        let closingGate = OwnershipGate()
        await closingDocument.objectLifecycleService.holdOn(closingGate)
        let closing = Task { try await closingDocument.close() }
        await closingGate.waitForEntry()
        let attemptedTarget = TextProbe()
        var admittedDuringClose = false
        do {
            let attempted = try session(closingDocument, text: attemptedTarget)
            try await attempted.services.blockActionService.textServiceHandler.checked(
                contextId: "owned", blockId: "a", newValue: true)
            admittedDuringClose = true
        } catch {}
        let attemptedCalls = await attemptedTarget.snapshot()
        checks.expect(!admittedDuringClose && attemptedCalls.isEmpty && closingDocument.isOpened,
            "fresh_prepared_session_cannot_dispatch_while_original_close_is_awaiting")
        closingDocument.reopenForFixture()
        checks.expect(closingDocument.isOpened && closingDocument.editorWriteLifetime.token() == nil,
            "original_setup_view_cannot_admit_while_a_close_is_pending")
        await closingGate.release()
        try await closing.value
        checks.expect(!closingDocument.isOpened && closingDocument.editorWriteLifetime.token() == nil,
            "original_close_completion_does_not_replay_an_earlier_open_confirmation")
        closingDocument.reopenForFixture()
        let recoveredSession = try session(closingDocument, text: attemptedTarget)
        try await recoveredSession.services.blockActionService.textServiceHandler.checked(
            contextId: "owned", blockId: "a", newValue: true)
        let recoveredCalls = await attemptedTarget.snapshot()
        checks.expect(closingDocument.isOpened && recoveredCalls.count == 1,
            "a_later_original_setup_view_admits_only_a_fresh_prepared_session")

        let eventDocument = LifetimeDocumentProbe()
        let eventOwner = try EditorDocumentWriteOwner(data: lifetimeData(eventDocument), lifetimeDocument: eventDocument)
        eventDocument.emitCloseEventForFixture()
        eventDocument.reopenForFixture()
        checks.expect(eventOwner.isRetired, "original_close_event_invalidates_without_relying_on_sync_publisher")

        let failedDocument = LifetimeDocumentProbe()
        let failedOwner = try EditorDocumentWriteOwner(data: lifetimeData(failedDocument), lifetimeDocument: failedDocument)
        await failedDocument.objectLifecycleService.setFailure(true)
        var closeError = false
        do { try await failedDocument.close() } catch { closeError = error as? TextProbeFailure == .deliberate }
        checks.expect(closeError && failedDocument.isOpened && failedOwner.isRetired,
            "failed_original_close_propagates_error_and_does_not_renew_old_owner")
        let freshAfterFailure = await lifetimeFailure { _ = try session(failedDocument) }
        let failedCloseCalls = await failedDocument.objectLifecycleService.calls
        checks.expect(freshAfterFailure == .rejected(.retired) && failedCloseCalls.count == 1,
            "failed_close_does_not_infer_new_authority_or_retry_the_original_rpc")

        let noop = LifetimeDocumentProbe(mode: .preview)
        let noopToken = noop.editorWriteLifetime.token()!
        try await noop.close()
        let noopCalls = await noop.objectLifecycleService.calls
        checks.expect(noopCalls.isEmpty && noop.editorWriteLifetime.isCurrent(noopToken),
            "original_preview_close_guard_has_no_new_lifetime_effect")

        let irrelevant = LifetimeDocumentProbe()
        let unchangedToken = irrelevant.editorWriteLifetime.token()!
        let irrelevantRows = irrelevant.irrelevantUpdateForFixture()
        checks.expect(irrelevantRows.isEmpty && irrelevant.editorWriteLifetime.isCurrent(unchangedToken),
            "unrelated_document_update_does_not_revoke_editing")

        let replacedDocument = LifetimeDocumentProbe()
        let replacedOwner = try EditorDocumentWriteOwner(data: lifetimeData(replacedDocument), lifetimeDocument: replacedDocument)
        replacedDocument.replaceLifetimeForFixture()
        let replacedError = await lifetimeFailure { try replacedOwner.validateOwnership() }
        checks.expect(replacedError == .rejected(.retired), "replacement_lifetime_source_cannot_silently_renew_owner")

        let raw = TextProbe(), ownedEvents = LocalPublisherProbe()
        let preparedDoc = LifetimeDocumentProbe()
        let prepared = try session(preparedDoc, text: raw, events: ownedEvents)
        let builder = FixturePreparedAssembly()
        let state = try builder.buildStateModel(preparedSession: prepared, output: nil, showHeader: true, torahSession: nil)
        checks.expect(builder.document === preparedDoc && state.preparedSession === prepared
                      && builder.data == lifetimeData(preparedDoc),
            "prepared_assembly_passes_same_original_document_and_state")
        checks.expect(prepared.services.blockActionService.blockService === fixtureMarker
                      && prepared.services.blockBuilder.blockService === fixtureMarker
                      && prepared.services.router.templateService === fixtureMarker,
            "prepared_session_preserves_other_explicit_service_instances")
        try await prepared.services.blockActionService.textServiceHandler.setStyle(contextId: "owned", blockId: "a", style: .text)
        let rawCalls = await raw.snapshot(), localCalls = await ownedEvents.snapshot()
        checks.expect(rawCalls.count == 1 && localCalls.count == 1 && localCalls[0].operation == "style",
            "original_text_handler_and_local_events_share_the_prepared_owner")
        let lifecycleCalls = await preparedDoc.lifecycle.snapshot()
        let nativeFallback = await Container.shared.nativeText.snapshot()
        checks.expect(lifecycleCalls.isEmpty && nativeFallback.isEmpty,
            "prepared_assembly_never_reopens_document_or_uses_global_text_fallback")

        let container = FixturePreparedContainer(viewController: state.viewController, preparedSession: prepared)
        let coordinator = container.makeCoordinator()
        let otherController = EditorPageController()
        FixturePreparedContainer.dismantleUIViewController(otherController, coordinator: coordinator)
        checks.expect(!prepared.owner.isRetired, "foreign_controller_cleanup_does_not_retire_bound_editor")
        FixturePreparedContainer.dismantleUIViewController(state.viewController, coordinator: coordinator)
        let retiredText = await lifetimeFailure {
            try await prepared.services.blockActionService.textServiceHandler.setStyle(contextId: "owned", blockId: "a", style: .text)
        }
        checks.expect(retiredText == .rejected(.retired), "exact_original_controller_dismantle_retires_prepared_writer")

        let leaseDoc = LifetimeDocumentProbe()
        let leaseSession = try session(leaseDoc)
        let leaseState = try FixturePreparedAssembly().buildStateModel(preparedSession: leaseSession, output: nil, showHeader: true, torahSession: nil)
        var leaseCoordinator: FixturePreparedContainer.Coordinator? =
            FixturePreparedContainer(viewController: leaseState.viewController, preparedSession: leaseSession).makeCoordinator()
        let beforeRelease = !leaseSession.owner.isRetired && leaseCoordinator != nil
        leaseCoordinator = nil
        checks.expect(beforeRelease && leaseSession.owner.isRetired,
            "host_coordinator_release_revokes_its_lease_without_a_dismantle_callback")

        let sharedDoc = LifetimeDocumentProbe()
        let first = try session(sharedDoc), second = try session(sharedDoc)
        first.retire()
        try await second.services.blockActionService.textServiceHandler.checked(contextId: "owned", blockId: "a", newValue: true)
        checks.expect(first.owner.isRetired && !second.owner.isRetired && sharedDoc.isOpened,
            "retiring_one_prepared_host_does_not_revoke_another_same_document_host")

        let duplicate = try session(LifetimeDocumentProbe())
        let duplicateBuilder = FixturePreparedAssembly()
        _ = try duplicateBuilder.buildStateModel(preparedSession: duplicate, output: nil, showHeader: true, torahSession: nil)
        let duplicateError = await lifetimeFailure {
            _ = try duplicateBuilder.buildStateModel(preparedSession: duplicate, output: nil, showHeader: true, torahSession: nil)
        }
        checks.expect(duplicateError == .rejected(.invalidLease) && duplicate.owner.isRetired,
            "a_second_assembly_cannot_reuse_one_prepared_owner")

        let binding = try session(LifetimeDocumentProbe())
        try binding.claimAssembly()
        var originalController: EditorPageController? = EditorPageController()
        try binding.bind(controller: originalController!)
        originalController = nil
        let rebound = await lifetimeFailure { try binding.bind(controller: EditorPageController()) }
        checks.expect(rebound == .rejected(.invalidLease),
            "released_controller_does_not_make_one_use_binding_available_again")

        let duplicateHost = try session(LifetimeDocumentProbe())
        let duplicateHostState = try FixturePreparedAssembly().buildStateModel(preparedSession: duplicateHost, output: nil, showHeader: true, torahSession: nil)
        let duplicateContainer = FixturePreparedContainer(viewController: duplicateHostState.viewController, preparedSession: duplicateHost)
        let originalHost = duplicateContainer.makeCoordinator()
        let secondHost = duplicateContainer.makeCoordinator()
        checks.expect(originalHost.hostLease != nil && secondHost.hostLease == nil && duplicateHost.owner.isRetired,
            "duplicate_host_registration_fails_closed")

        let releasedDoc = LifetimeDocumentProbe()
        var releasedSession: PreparedEditorPageSession? = try session(releasedDoc)
        weak var weakSession = releasedSession
        let retainedWriter = releasedSession!.services.blockActionService.textServiceHandler
        releasedSession = nil
        let releasedError = await lifetimeFailure {
            try await retainedWriter.checked(contextId: "owned", blockId: "a", newValue: true)
        }
        checks.expect(weakSession == nil && releasedError == .rejected(.retired) && releasedDoc.isOpened,
            "released_session_invalidates_retained_writer_without_closing_document")

        let racingDoc = LifetimeDocumentProbe()
        let racingSession = try session(racingDoc)
        let racingBuilder = FixturePreparedAssembly()
        racingBuilder.duringBuild = {
            _ = racingDoc.applyPermissionForFixture(false)
            _ = racingDoc.applyPermissionForFixture(true)
        }
        let raceError = await lifetimeFailure {
            _ = try racingBuilder.buildStateModel(preparedSession: racingSession, output: nil, showHeader: true, torahSession: nil)
        }
        checks.expect(raceError == .rejected(.retired) && racingSession.owner.isRetired,
            "revocation_during_original_state_construction_prevents_prepared_binding")

        let data = try JSONEncoder().encode(checks.checks)
        guard CommandLine.arguments.count == 2 else { throw BoundaryFixtureError.failed }
        try data.write(to: URL(fileURLWithPath: CommandLine.arguments[1]), options: .atomic)
        print(String(decoding: data, as: UTF8.self))
        if checks.checks.contains(where: { !$0.passed }) { throw BoundaryFixtureError.failed }
    }
}
