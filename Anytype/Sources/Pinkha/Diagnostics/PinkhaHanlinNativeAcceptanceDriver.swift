import PinkhaHanlinCore
#if DEBUG && targetEnvironment(simulator)
import Foundation
@preconcurrency import Combine
import UIKit
import Factory
import AnytypeCore
import Services
import ProtobufMessages
import HanlinAgentCore
import HanlinHostContracts
import HanlinPlatformContracts

/// Disposable simulator diagnostic. XCTest still presses the production consent,
/// Cancel, Create page, Return and Close controls. This code cannot issue an approval.
@MainActor
final class PinkhaHanlinNativeAcceptanceDriver {
    private static var active: PinkhaHanlinNativeAcceptanceDriver?
    private let fixture: PinkhaHanlinNativeAcceptanceFixture
    private let host: PinkhaHanlinReadWriteHost
    private let presentation: PinkhaHanlinChatPresentation
    private weak var controller: PinkhaHanlinChatController?
    private weak var editor: EditorPageController?
    private weak var routeOwner: SpaceHubCoordinatorViewModel?
    private let rootPresenter: UIViewController
    private let statusLabel: UILabel
    private var task: Task<Void, Never>?
    private var receipt: Receipt
    private weak var scene: UIWindowScene?
    private var sceneSubscriptions: [AnyCancellable] = []
    private var presentations: [UUID: MountedPresentation] = [:]
    private var awaitingPresentation = false
    private var nextPresentation: MountedPresentation?

    @MainActor
    private final class MountedPresentation {
        let host: PinkhaHanlinReadWriteHost
        let presentation: PinkhaHanlinChatPresentation
        weak var controller: PinkhaHanlinChatController?
        weak var editor: EditorPageController?
        init(host: PinkhaHanlinReadWriteHost, presentation: PinkhaHanlinChatPresentation,
             controller: PinkhaHanlinChatController, editor: EditorPageController) {
            self.host = host; self.presentation = presentation
            self.controller = controller; self.editor = editor
        }
    }

    struct NavigationContext: Codable, Equatable {
        let app: String
        let account: String
        let workspace: String
        let space: String
        let sceneID: UUID
        let generation: UUID
        let objectReference: String?
        let selectionReferences: [String]
        let sourceRevision: String?

        init(_ context: HanlinHostContext) {
            app = context.namespace.app; account = context.namespace.account
            workspace = context.namespace.workspace; space = context.namespace.space
            sceneID = context.sceneID; generation = context.generation
            objectReference = context.objectReference; selectionReferences = context.selectionReferences
            sourceRevision = context.sourceRevision
        }
    }

    struct NativeReturnReceipt: Codable {
        let requestID: UUID
        let queuedRequestID: UUID
        let sessionID: UUID
        let context: NavigationContext
        let objectReference: String
        let blockReference: String?
        let presentationAcknowledged: Bool
    }

    struct SceneObservation: Codable {
        let event: String
        let observedAt: Date
        let sceneActivationState: Int?
        let phase: String
    }

    struct Receipt: Codable {
        let fixtureID: UUID
        let sourceSHA: String
        let runID: String
        let runAttempt: String
        let sessionID: UUID
        let navigationContext: NavigationContext
        let processID: Int32
        let startedAt: Date
        var finishedAt: Date?
        var phase = "STARTING"
        var checks: [String: Bool] = [:]
        var createdObjectID: String?
        var failure: String?
        var providerConfigured = false
        var nativeReturn: NativeReturnReceipt?
        var backgroundSessionID: UUID?
        var staleConsentSessionID: UUID?
        var freshSessionID: UUID?
        var sceneEventCounts: [String: Int] = [:]
        var sceneObservations: [SceneObservation] = []
        var backgroundCycleSceneDelta: [String: Int] = [:]
        var documentExitSceneDelta: [String: Int] = [:]
        var documentExitAttribution: String?
        var invalidationCauses: [String: String] = [:]
        var logoutRootState: String?
        var nativeAuthorityStage: String?
    }

    /// Observation only: records the first existing production invalidation call.
    /// This hook never invalidates a session, dismisses UI, or supplies consent.
    static func observedInvalidation(sessionID: UUID, cause: String) {
        guard let active, sessionID == active.host.session.id || active.presentations[sessionID] != nil else { return }
        if active.receipt.invalidationCauses[sessionID.uuidString] == nil {
            active.receipt.invalidationCauses[sessionID.uuidString] = cause
        }
    }

    static func startIfRequested(host: PinkhaHanlinReadWriteHost,
                                 presentation: PinkhaHanlinChatPresentation,
                                 controller: PinkhaHanlinChatController,
                                 source: UIViewController?, routeOwner: SpaceHubCoordinatorViewModel?) {
        guard ProcessInfo.processInfo.environment["PINKHA_HANLIN_NATIVE_UI"] == "1" else { return }
        do {
            // viewDidAppear may repeat when an actual native alert disappears.
            if let active {
                if active.host.session == host.session || active.presentations[host.session.id] != nil { return }
                try active.captureNextPresentation(host: host, presentation: presentation,
                    controller: controller, source: source, routeOwner: routeOwner)
                return
            }
            guard active == nil, let editor = source as? EditorPageController, let routeOwner else {
                throw HanlinNativeAcceptanceError.invalidFixture
            }
            let fixture = try PinkhaHanlinNativeAcceptanceFixture.loadForUI()
            let driver = try Self(fixture: fixture, host: host, presentation: presentation,
                                  controller: controller, editor: editor, routeOwner: routeOwner)
            active = driver
            driver.task = Task { await driver.run() }
        } catch {
            if let window = controller.viewIfLoaded?.window {
                let label = makeStatusLabel(in: window)
                label.text = "FAIL_SETUP"
                label.accessibilityValue = "Native fixture setup rejected"
            }
        }
    }

    private init(fixture: PinkhaHanlinNativeAcceptanceFixture, host: PinkhaHanlinReadWriteHost,
                 presentation: PinkhaHanlinChatPresentation, controller: PinkhaHanlinChatController,
                 editor: EditorPageController, routeOwner: SpaceHubCoordinatorViewModel) throws {
        guard let window = editor.viewIfLoaded?.window, let root = window.rootViewController,
              window === controller.viewIfLoaded?.window,
              Container.shared.serverConfigurationStorage().currentConfiguration() == .localOnly,
              Container.shared.accountManager().account.id == fixture.accountID,
              host.session == presentation.session,
              host.session.context.namespace.app == "anytype",
              host.session.context.namespace.account == fixture.accountID,
              host.session.context.namespace.workspace == fixture.spaceID,
              host.session.context.namespace.space == fixture.spaceID,
              host.session.context.objectReference == fixture.sourceObjectID,
              host.session.context.selectionReferences.isEmpty,
              host.session.context.sourceRevision?.isEmpty == false,
              editor.viewModel?.document.objectId == fixture.sourceObjectID,
              !presentation.isConfigured else { throw HanlinNativeAcceptanceError.invalidFixture }
        self.fixture = fixture; self.host = host; self.presentation = presentation
        self.controller = controller; self.editor = editor; self.routeOwner = routeOwner
        self.rootPresenter = root
        self.statusLabel = Self.makeStatusLabel(in: window)
        self.receipt = Receipt(fixtureID: fixture.fixtureID, sourceSHA: fixture.sourceSHA,
            runID: fixture.runID, runAttempt: fixture.runAttempt, sessionID: host.session.id,
            navigationContext: NavigationContext(host.session.context),
            processID: ProcessInfo.processInfo.processIdentifier, startedAt: Date())
        self.scene = window.windowScene
        if let scene = window.windowScene { observeScene(scene) }
    }

    private func observeScene(_ scene: UIWindowScene) {
        let events: [(Foundation.Notification.Name, AnyObject?, String)] = [
            (UIScene.willDeactivateNotification, scene, "sceneWillDeactivate"),
            (UIScene.didEnterBackgroundNotification, scene, "sceneDidEnterBackground"),
            (UIScene.willEnterForegroundNotification, scene, "sceneWillEnterForeground"),
            (UIScene.didActivateNotification, scene, "sceneDidActivate"),
            (UIApplication.willResignActiveNotification, nil, "applicationWillResignActive"),
            (UIApplication.didBecomeActiveNotification, nil, "applicationDidBecomeActive")
        ]
        for (notification, object, key) in events {
            receipt.sceneEventCounts[key] = 0
            NotificationCenter.default.publisher(for: notification, object: object)
                .sink { [weak self] _ in
                    guard let self else { return }
                    receipt.sceneEventCounts[key, default: 0] += 1
                    receipt.sceneObservations.append(SceneObservation(event: key, observedAt: Date(),
                        sceneActivationState: self.scene?.activationState.rawValue, phase: receipt.phase))
                    do {
                        let data = try persistReceipt()
                        statusLabel.accessibilityValue = String(decoding: data, as: UTF8.self)
                    } catch {
                        // A later successful emit retains this failure, which the
                        // original final XCTAssertNil(receipt.failure) rejects.
                        receipt.failure = receipt.failure ?? "native_scene_observation_persistence_failed"
                    }
                }.store(in: &sceneSubscriptions)
        }
    }

    private func captureNextPresentation(host: PinkhaHanlinReadWriteHost, presentation: PinkhaHanlinChatPresentation,
                                         controller: PinkhaHanlinChatController, source: UIViewController?,
                                         routeOwner: SpaceHubCoordinatorViewModel?) throws {
        guard awaitingPresentation, nextPresentation == nil,
              let editor = source as? EditorPageController, let routeOwner, routeOwner === self.routeOwner,
              let scene, scene.activationState == .foregroundActive,
              controller.viewIfLoaded?.window?.windowScene === scene,
              editor.viewIfLoaded?.window?.windowScene === scene,
              Container.shared.serverConfigurationStorage().currentConfiguration() == .localOnly,
              Container.shared.accountManager().account.id == fixture.accountID,
              host.session == presentation.session, host.session.id != self.host.session.id,
              host.session.context.namespace == self.host.session.context.namespace,
              host.session.context.objectReference == fixture.sourceObjectID,
              host.session.context.selectionReferences.isEmpty,
              editor.viewModel?.document.objectId == fixture.sourceObjectID,
              !presentation.isConfigured, !presentation.readAllowed else {
            throw HanlinNativeAcceptanceError.invalidFixture
        }
        try presentation.validateInstallation(for: host.session)
        let mounted = MountedPresentation(host: host, presentation: presentation, controller: controller, editor: editor)
        presentations[host.session.id] = mounted
        nextPresentation = mounted
    }

    private func awaitPresentation(_ phase: String) async throws -> MountedPresentation {
        try require(nextPresentation == nil && !awaitingPresentation, "overlapping_native_presentation_expectations")
        awaitingPresentation = true
        defer { awaitingPresentation = false; nextPresentation = nil }
        try emit(phase)
        try await waitUntil { self.nextPresentation != nil }
        let mounted = try requireValue(nextPresentation, "missing_real_native_presentation")
        try mounted.presentation.validateInstallation(for: mounted.host.session)
        return mounted
    }

    private static func makeStatusLabel(in window: UIWindow) -> UILabel {
        let label = UILabel(frame: CGRect(x: 12, y: window.safeAreaInsets.top + 2,
                                         width: window.bounds.width - 24, height: 18))
        label.font = .monospacedSystemFont(ofSize: 10, weight: .regular)
        label.textAlignment = .center
        label.backgroundColor = .systemBackground
        label.textColor = .label
        label.isUserInteractionEnabled = false
        label.isAccessibilityElement = true
        label.accessibilityIdentifier = "pinkha.hanlin.native-acceptance-status"
        label.autoresizingMask = [.flexibleWidth, .flexibleBottomMargin]
        window.addSubview(label)
        return label
    }

    private func run() async {
        do {
            try require(InvocationSettings.handler?.isLogEnabled == false, "middleware_logging_enabled")
            receipt.checks["middleware_logging_disabled"] = true
            _ = try await host.context(for: host.session)
            let initialCatalog = try await host.catalog(for: host.session.context)
            try require(!initialCatalog.tools.contains { $0.route.alias == "anytype_read_context_text" }, "read_advertised_without_consent")
            try await denied(host: host, invocation: makeReadInvocation())
            receipt.checks["read_denied_before_native_consent"] = true
            try emit("AWAIT_READ_CONSENT")
            // The UI test taps the existing Share context button and actual alert.
            try await waitUntil { self.presentation.readAllowed }
            try await waitUntil { self.controller?.presentedViewController == nil }
            try presentation.validateInstallation(for: host.session)
            let catalog = try await host.catalog(for: host.session.context)
            try require(Set(catalog.tools.map(\.route.alias)) == ["anytype_read_context_text", PinkhaHanlinCreatePagePlan.alias], "native_catalog_unavailable")
            let recording = RecordingHost(host: host)
            let dispatcher = HanlinHostDispatcher(host: recording)
            let runID = UUID()
            let limits = try HanlinToolInvocationLimits()
            let read = try await dispatcher.dispatch(alias: "anytype_read_context_text", argumentsJSON: "{}",
                providerCallID: "native-fixture-read", runID: runID, step: 0,
                session: host.session, catalog: catalog, limits: limits)
            try verifyRead(read)
            receipt.checks["real_native_context_text_read"] = true

            try emit("AWAIT_CANCEL_CREATE")
            let cancelled = try await dispatcher.dispatch(alias: PinkhaHanlinCreatePagePlan.alias,
                argumentsJSON: titleArguments(fixture.cancelledTitle), providerCallID: "native-fixture-cancel",
                runID: runID, step: 1, session: host.session, catalog: catalog, limits: limits)
            try require(cancelled.effectState == .notDispatched, "cancelled_creation_may_have_dispatched")
            guard case .failed = cancelled.result.outcome else { throw HanlinNativeAcceptanceError.failed("cancelled_creation_succeeded") }
            let cancelledCall = try requireValue(recording.invocations[cancelled.result.invocationID], "missing_cancelled_call")
            let cancelledPlan = try PinkhaHanlinCreatePagePlan(invocation: cancelledCall)
            let journal = try await PinkhaHanlinAccountOwner.shared.journal(for: host.session.context.namespace)
            try require(try await journal.receipt(for: cancelledPlan.identity) == nil, "cancelled_creation_reserved_a_write")
            receipt.checks["native_cancel_prevents_write"] = true

            // The native decision completes before UIKit finishes dismissing
            // its alert. Preserve the production no-covering-presentation gate.
            try await waitUntil { self.controller?.presentedViewController == nil }
            try emit("AWAIT_CONFIRM_CREATE")
            let created = try await dispatcher.dispatch(alias: PinkhaHanlinCreatePagePlan.alias,
                argumentsJSON: titleArguments(fixture.createdTitle), providerCallID: "native-fixture-create",
                runID: runID, step: 2, session: host.session, catalog: catalog, limits: limits)
            try require(created.effectState == .confirmedCommitted, "creation_not_confirmed")
            guard case .completed = created.result.outcome else { throw HanlinNativeAcceptanceError.failed("creation_not_completed") }
            let createdCall = try requireValue(recording.invocations[created.result.invocationID], "missing_created_call")
            let plan = try PinkhaHanlinCreatePagePlan(invocation: createdCall)
            let entry = try requireValue(try await journal.receipt(for: plan.identity), "missing_durable_commit")
            let objectID = try requireValue(entry.createdObjectReference, "missing_native_object_id")
            try require(entry.effect == .committed, "journal_not_committed")
            try await verifyNativeCreatedPage(objectID)
            receipt.createdObjectID = objectID
            receipt.checks["native_confirm_creates_exact_page"] = true
            receipt.checks["created_page_read_back_by_journal_id"] = true

            let dispatchCount = recording.executionCount
            let replay = try await dispatcher.dispatch(alias: PinkhaHanlinCreatePagePlan.alias,
                argumentsJSON: titleArguments(fixture.createdTitle), providerCallID: "native-fixture-create",
                runID: runID, step: 2, session: host.session, catalog: catalog, limits: limits)
            try require(replay == created && recording.executionCount == dispatchCount, "replay_dispatched_again")
            try await verifyNativeIndex(createdID: objectID)
            receipt.checks["replay_does_not_create_duplicate"] = true
            receipt.checks["cancelled_title_absent_from_native_index"] = true
            try require(!presentation.isConfigured, "provider_was_configured")
            receipt.checks["no_provider_configuration"] = true
            try require(presentation.returnReceipt == nil, "native_return_preceded_user_action")
            try emit("READY_TO_CLOSE")
            // XCTest presses Return. Observe only the receipt created by the
            // production dismissal callback; never invoke its acknowledgement.
            try await observeNativeReturn()
            try await denied(host: host, invocation: makeReadInvocation())
            try await denied(host: host, invocation: copyCreationForDeniedAttempt(createdCall))
            receipt.checks["closed_presentation_denies_read_and_create"] = true
            receipt.checks["native_return_mounted_original_document"] = true
            try await verifyNativeUILifetimes(createdCall: createdCall, createdID: objectID)
            // Fresh native consent in H4 must not rearm H1. Recheck while its
            // original account/Space/document still exist, before authority mutations.
            try await denied(host: host, invocation: makeReadInvocation())
            try await denied(host: host, invocation: copyCreationForDeniedAttempt(createdCall))
            try emit("CHECKING_NATIVE_AUTHORITY")
            try await verifyNativeAuthorityChanges()
            receipt.nativeAuthorityStage = "retained_commit_receipt"
            let retained = try await journal.receipt(for: plan.identity)
            try require(retained?.effect == .committed && retained?.createdObjectReference == objectID,
                        "ordinary_logout_lost_original_write_metadata")
            receipt.checks["original_commit_metadata_survives_logout"] = true
            receipt.finishedAt = Date()
            try emit("NATIVE_ACCEPTANCE_PASS")
        } catch {
            if case HanlinNativeAcceptanceError.failed(let reason) = error { receipt.failure = reason }
            else { receipt.failure = "native_operation_or_context_failed" }
            receipt.finishedAt = Date()
            try? emit("NATIVE_ACCEPTANCE_FAIL")
        }
    }

    private func observeNativeReturn() async throws {
        try await waitUntil {
            guard let handoff = self.presentation.returnReceipt else { return false }
            return handoff.state != .awaitingMount
        }
        let handoff = try requireValue(presentation.returnReceipt, "native_return_missing")
        try require(handoff.state == .mounted, "native_return_not_mounted")
        let result = try requireValue(handoff.receipt, "native_return_receipt_missing")
        let destination = handoff.destination
        try result.validate(for: destination)
        guard case .presented(let requestID, let context, let object, let block) = result else {
            throw HanlinNativeAcceptanceError.failed("native_return_only_queued")
        }
        try require(destination.context == host.session.context && context == host.session.context,
                    "native_return_context_changed")
        try require(requestID == destination.requestID && object == fixture.sourceObjectID
                    && destination.objectReference == fixture.sourceObjectID
                    && block == nil && destination.blockReference == nil
                    && context.selectionReferences.isEmpty,
                    "native_return_target_or_request_changed")
        try await waitUntil { self.controller?.presentingViewController == nil }
        guard let editor, let scene, scene.activationState == .foregroundActive,
              editor.viewModel?.document.objectId == fixture.sourceObjectID,
              editor.viewModel?.document.spaceId == fixture.spaceID,
              PinkhaHanlinNativeAccess.isMounted(editor, in: scene) else {
            throw HanlinNativeAcceptanceError.failed("native_return_original_editor_not_visible")
        }
        try require(receipt.nativeReturn == nil && NavigationContext(context) == receipt.navigationContext,
                    "native_return_original_metadata_changed")
        receipt.nativeReturn = NativeReturnReceipt(requestID: requestID, queuedRequestID: destination.requestID,
            sessionID: host.session.id, context: NavigationContext(context), objectReference: object,
            blockReference: block, presentationAcknowledged: result.presentationAcknowledged)
    }

    private func verifyNativeUILifetimes(createdCall: HanlinHostInvocation, createdID: String) async throws {
        // H2 is opened through the existing product button, then explicitly
        // consented by XCTest. A host already denied before background is not proof.
        let background = try await awaitPresentation("AWAIT_BACKGROUND_PRESENTATION")
        receipt.backgroundSessionID = background.host.session.id
        try await requireFreshConsent(background)
        try emit("AWAIT_BACKGROUND_READ_CONSENT")
        try await readAfterNativeConsent(background)
        receipt.checks["background_presentation_had_live_read_access"] = true
        let beforeBackground = receipt.sceneEventCounts
        try emit("READY_FOR_BACKGROUND")
        // XCTest drives the actual Home/SpringBoard transition and app.activate().
        // This driver only observes notifications; it never posts scene events.
        try await waitUntil {
            self.receipt.sceneEventCounts["sceneDidEnterBackground", default: 0] > beforeBackground["sceneDidEnterBackground", default: 0]
                && self.receipt.sceneEventCounts["sceneDidActivate", default: 0] > beforeBackground["sceneDidActivate", default: 0]
                && self.scene?.activationState == .foregroundActive
                && background.controller?.presentingViewController == nil
        }
        receipt.backgroundCycleSceneDelta = sceneDelta(since: beforeBackground)
        try require(receipt.backgroundCycleSceneDelta["sceneWillEnterForeground", default: 0] > 0,
                    "foreground_notification_not_observed")
        receipt.checks["native_background_foreground_observed"] = true
        try await denied(host: background.host, invocation: makeReadInvocation(session: background.host.session))
        try await denied(host: background.host, invocation: copyCreationForDeniedAttempt(createdCall, session: background.host.session))
        try require(receipt.invalidationCauses[background.host.session.id.uuidString] != nil,
                    "background_invalidation_call_not_observed")
        receipt.checks["backgrounded_presentation_denies_read_and_create"] = true

        // H3 is a new, initially unconsented presentation. Its actual native
        // read alert is left pending while the production object URL is opened.
        let stale = try await awaitPresentation("AWAIT_STALE_CONSENT_PRESENTATION")
        receipt.staleConsentSessionID = stale.host.session.id
        try await requireFreshConsent(stale)
        try emit("AWAIT_STALE_READ_CONSENT")
        try await waitUntil {
            guard let prompt = stale.controller?.presentedViewController as? PinkhaHanlinConsentController else { return false }
            return prompt.purpose == .readContext && prompt.title == "Allow document text access?"
                && prompt.viewIfLoaded?.window != nil
        }
        try require(!stale.presentation.readAllowed, "pending_consent_was_already_allowed")
        let pendingAlert = stale.controller?.presentedViewController
        let beforeDocumentExit = receipt.sceneEventCounts
        try emit("READY_TO_LEAVE_WITH_PENDING_CONSENT")
        try await waitUntil {
            self.hasCurrentDocument(createdID)
                && stale.controller?.presentingViewController == nil
                && pendingAlert?.viewIfLoaded?.window == nil
                && self.scene?.activationState == .foregroundActive
        }
        receipt.documentExitSceneDelta = sceneDelta(since: beforeDocumentExit)
        receipt.documentExitAttribution = receipt.documentExitSceneDelta.values.contains(where: { $0 > 0 })
            ? "navigationWithSceneTransition" : "navigationWithoutSceneTransition"
        try require(!stale.presentation.readAllowed, "departed_document_received_pending_consent")
        try require(receipt.invalidationCauses[stale.host.session.id.uuidString] != nil,
                    "departed_presentation_invalidation_call_not_observed")
        receipt.checks["pending_read_consent_dismissed_on_document_exit"] = true
        try await denied(host: stale.host, invocation: makeReadInvocation(session: stale.host.session))
        try await denied(host: stale.host, invocation: copyCreationForDeniedAttempt(createdCall, session: stale.host.session))
        receipt.checks["departed_document_presentation_denies_read_and_create"] = true

        // H4 is mounted after XCTest returns to the exact original document.
        // The old presentation/consent cannot authorize this new lifetime.
        let fresh = try await awaitPresentation("AWAIT_FRESH_PRESENTATION")
        receipt.freshSessionID = fresh.host.session.id
        try await requireFreshConsent(fresh)
        receipt.checks["fresh_presentation_requires_new_native_consent"] = true
        try emit("AWAIT_FRESH_READ_CONSENT")
        try await readAfterNativeConsent(fresh)
        receipt.checks["fresh_presentation_reads_original_document_only"] = true
        try await verifyNativeIndex(createdID: createdID) // No denied create may duplicate the original page.
        try emit("READY_TO_CLOSE_FRESH")
        try await waitUntil { fresh.controller?.presentingViewController == nil }
        try await denied(host: fresh.host, invocation: makeReadInvocation(session: fresh.host.session))
        guard let editor = fresh.editor, editor.viewIfLoaded?.window?.windowScene === scene else {
            throw HanlinNativeAcceptanceError.failed("fresh_original_editor_unmounted")
        }
        self.editor = editor
    }

    private func requireFreshConsent(_ mounted: MountedPresentation) async throws {
        try require(!mounted.presentation.readAllowed && !mounted.presentation.isConfigured,
                    "new_presentation_inherited_consent_or_provider")
        _ = try await mounted.host.context(for: mounted.host.session)
        let catalog = try await mounted.host.catalog(for: mounted.host.session.context)
        try require(Set(catalog.tools.map(\.route.alias)) == [PinkhaHanlinCreatePagePlan.alias],
                    "fresh_native_catalog_must_have_create_without_read")
        try await denied(host: mounted.host, invocation: makeReadInvocation(session: mounted.host.session))
    }

    private func readAfterNativeConsent(_ mounted: MountedPresentation) async throws {
        try await waitUntil { mounted.presentation.readAllowed && mounted.controller?.presentedViewController == nil }
        try mounted.presentation.validateInstallation(for: mounted.host.session)
        try require(!mounted.presentation.isConfigured, "lifecycle_provider_was_configured")
        let catalog = try await mounted.host.catalog(for: mounted.host.session.context)
        try require(Set(catalog.tools.map(\.route.alias)) == ["anytype_read_context_text", PinkhaHanlinCreatePagePlan.alias],
                    "consented_lifecycle_catalog_missing_read_or_create")
        let dispatcher = HanlinHostDispatcher(host: mounted.host)
        let read = try await dispatcher.dispatch(alias: "anytype_read_context_text", argumentsJSON: "{}",
            providerCallID: "native-lifecycle-read", runID: UUID(), step: 0,
            session: mounted.host.session, catalog: catalog, limits: try HanlinToolInvocationLimits())
        try verifyRead(read, receiptHost: mounted.host)
    }

    private func hasCurrentDocument(_ objectID: String) -> Bool {
        guard let screen = routeOwner?.navigationPath.path.last?.base as? EditorScreenData,
              case .page(let object) = screen else { return false }
        return object.objectId == objectID && object.spaceId == fixture.spaceID
    }

    private func sceneDelta(since previous: [String: Int]) -> [String: Int] {
        receipt.sceneEventCounts.reduce(into: [:]) { result, entry in
            result[entry.key] = entry.value - previous[entry.key, default: 0]
        }
    }

    private func verifyRead(_ result: HanlinHostExecutionResult, receiptHost: PinkhaHanlinReadWriteHost? = nil) throws {
        try require(result.effectState == .confirmedNoEffect, "read_effect_mismatch")
        guard case .completed(let content) = result.result.outcome, content.count == 1,
              case .text(let text) = content[0] else { throw HanlinNativeAcceptanceError.failed("read_payload_missing") }
        let snapshot = try JSONDecoder().decode(PinkhaHanlinTextSnapshot.self, from: Data(text.utf8))
        try require(snapshot.objectReference == fixture.sourceObjectID && snapshot.spaceReference == fixture.spaceID
                    && snapshot.title == fixture.sourceTitle && snapshot.coverage == "documentTextBlocksOnly"
                    && snapshot.blocks.contains { $0.reference == fixture.sourceBlockID && $0.text == fixture.sourceText },
                    "native_read_did_not_match_prepared_body")
        guard case .completed(let metadata) = (receiptHost ?? host).metadataReceipt(for: result.result.invocationID)?.result.outcome,
              metadata.isEmpty else { throw HanlinNativeAcceptanceError.failed("read_receipt_retained_payload") }
    }

    private func verifyNativeCreatedPage(_ objectID: String) async throws {
        let view = try await Container.shared.objectLifecycleService().openForPreview(contextId: objectID, spaceId: fixture.spaceID)
        let record = try requireValue(view.details.first { $0.id == objectID }, "native_created_details_missing")
        let details = ObjectDetails(id: record.id, values: record.details.fields)
        let pageTypes = Container.shared.objectTypeProvider().objectTypes(spaceId: fixture.spaceID).filter { $0.uniqueKey == .page }
        try require(pageTypes.count == 1 && view.rootID == objectID && details.id == objectID
                    && details.spaceId == fixture.spaceID && details.name == fixture.createdTitle
                    && details.type == pageTypes.first?.id && details.resolvedLayoutValue == .basic
                    && !details.isDeleted && !details.isArchived && !details.isReadonly && !details.isTemplate,
                    "native_created_page_mismatch")
    }

    private func verifyNativeIndex(createdID: String) async throws {
        let clock = ContinuousClock(); let deadline = clock.now.advanced(by: .seconds(20))
        repeat {
            let created = try await objects(named: fixture.createdTitle)
            if created.count == 1 && created.first?.id == createdID {
                try require(try await objects(named: fixture.cancelledTitle).isEmpty, "cancelled_creation_exists")
                return
            }
            try require(created.count <= 1, "duplicate_created_pages")
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw HanlinNativeAcceptanceError.failed("created_page_not_indexed")
    }

    private func objects(named name: String) async throws -> [ObjectDetails] {
        try await Container.shared.searchMiddleService().search(spaceId: fixture.spaceID,
            filters: [.with { $0.relationKey = "name"; $0.condition = .equal; $0.value = name.protobufValue }],
            keys: ["id", "spaceId", "name"], limit: 4)
    }

    private func verifyNativeAuthorityChanges() async throws {
        guard let editor, let routeOwner, let document = editor.viewModel?.document else {
            throw HanlinNativeAcceptanceError.failed("original_native_editor_unmounted")
        }
        // Each negative case starts with a distinct live authority that validates
        // before the real native change. An already-revoked fence cannot mask it.
        receipt.nativeAuthorityStage = "source_permission_authority"
        let permission = try PinkhaHanlinNativeAccess(presenter: editor, routeOwner: routeOwner,
            conversationID: UUID(), locale: Locale(identifier: "en"))
        try permission.validate(permission.session.context)
        try require(!document.isLocked && document.permissions.canEditBlocks, "source_initially_locked")
        try await Container.shared.objectActionsService().setLocked(true, objectId: fixture.sourceObjectID)
        try await waitUntil { document.isLocked && !document.permissions.canEditBlocks }
        try denied(permission)
        receipt.checks["native_source_permission_change_denied"] = true
        try await Container.shared.objectActionsService().setLocked(false, objectId: fixture.sourceObjectID)
        try await waitUntil { !document.isLocked && document.permissions.canEditBlocks }

        receipt.nativeAuthorityStage = "active_space_authority"
        let space = try PinkhaHanlinNativeAccess(presenter: rootPresenter, routeOwner: routeOwner,
            conversationID: UUID(), locale: Locale(identifier: "en"))
        try space.validate(space.session.context)
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: fixture.alternateSpaceID)
        try require(Container.shared.activeSpaceManager().workspaceInfo?.accountSpaceId == fixture.alternateSpaceID,
                    "native_space_did_not_change")
        try denied(space)
        receipt.checks["native_active_space_change_denied"] = true
        receipt.nativeAuthorityStage = "restore_original_space"
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: fixture.spaceID)
        receipt.nativeAuthorityStage = "await_restored_space_route"
        try await waitUntil {
            routeOwner.currentSpaceId == self.fixture.spaceID
                && Container.shared.activeSpaceManager().workspaceInfo?.accountSpaceId == self.fixture.spaceID
                && self.rootPresenter.viewIfLoaded?.window?.windowScene === self.scene
                && self.scene?.activationState == .foregroundActive
        }

        receipt.nativeAuthorityStage = "restored_account_authority"
        let account = try PinkhaHanlinNativeAccess(presenter: rootPresenter, routeOwner: routeOwner,
            conversationID: UUID(), locale: Locale(identifier: "en"))
        try account.validate(account.session.context)
        try require(Container.shared.accountManager().account.id == fixture.accountID, "foreign_account_before_logout")
        receipt.nativeAuthorityStage = "native_logout"
        try await Container.shared.authService().logout(removeData: false)
        receipt.nativeAuthorityStage = "logout_revocation"
        try require(!PinkhaHanlinAccountOwner.shared.isAvailable(account: fixture.accountID), "account_owner_not_revoked")
        try denied(account)
        receipt.checks["native_account_logout_denied"] = true

        // Complete the original Settings logout owner's route, after the real
        // service succeeded. Leaving SpaceHub mounted is not a completed UI logout.
        // InitialCoordinator decides the next root; do not force an auth screen.
        receipt.nativeAuthorityStage = "logout_root_route"
        let applicationState = Container.shared.applicationStateService()
        applicationState.state = .initial
        try await waitUntil { applicationState.state == .auth }
        receipt.logoutRootState = "auth"
    }

    private func denied(_ authority: PinkhaHanlinNativeAccess) throws {
        do {
            try authority.validate(authority.session.context)
            throw HanlinNativeAcceptanceError.failed("stale_native_authority_accepted")
        } catch HanlinHostError.staleContext {}
    }

    private func denied(host: PinkhaHanlinReadWriteHost, invocation: HanlinHostInvocation) async throws {
        do {
            let result = try await host.execute(invocation) { _ in }
            try require(result.effectState == .notDispatched, "denied_operation_may_have_dispatched")
            guard case .failed = result.result.outcome else { throw HanlinNativeAcceptanceError.failed("denied_operation_completed") }
        } catch HanlinHostError.staleContext {}
          catch HanlinHostError.denied {}
    }

    private func makeReadInvocation(session: HanlinHostSession? = nil) throws -> HanlinHostInvocation {
        let id = try HanlinToolInvocationID(validating: UUID().uuidString.lowercased())
        return .init(request: .init(id: id,
            logicalToolID: .init(providerInstanceID: try .init(validating: "anytype.host"), localToolID: try .init(validating: "read-context-text")),
            aliasUsed: "anytype_read_context_text", descriptorRevision: try .init(1), routingTableRevision: .init(1),
            arguments: .object([:]), origin: .assistantModel, idempotencyKey: id.rawValue,
            deadline: Date().addingTimeInterval(30), limits: try .init()),
            session: session ?? host.session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
            writeGuarantee: .readOnly, originalArgumentsJSON: Data("{}".utf8))
    }

    private func copyCreationForDeniedAttempt(_ original: HanlinHostInvocation, session: HanlinHostSession? = nil) throws -> HanlinHostInvocation {
        let id = try HanlinToolInvocationID(validating: UUID().uuidString.lowercased())
        return .init(request: .init(id: id, logicalToolID: original.request.logicalToolID,
            aliasUsed: original.request.aliasUsed, descriptorRevision: original.request.descriptorRevision,
            routingTableRevision: original.request.routingTableRevision, arguments: original.request.arguments,
            origin: .assistantModel, idempotencyKey: id.rawValue, deadline: Date().addingTimeInterval(30), limits: try .init()),
            session: session ?? host.session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
            writeGuarantee: .independentObjectCreation, originalArgumentsJSON: original.originalArgumentsJSON)
    }

    private func titleArguments(_ title: String) throws -> String {
        String(decoding: try HanlinJSONValue.object(["title": .string(title)]).canonicalJSONData(), as: UTF8.self)
    }

    private func waitUntil(_ condition: () -> Bool) async throws {
        let clock = ContinuousClock(); let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            if condition() { return }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw HanlinNativeAcceptanceError.failed("native_ui_or_state_timeout")
    }

    private func emit(_ phase: String) throws {
        receipt.phase = phase
        receipt.providerConfigured = presentation.isConfigured || presentations.values.contains { $0.presentation.isConfigured }
        let data = try persistReceipt()
        statusLabel.text = phase
        statusLabel.accessibilityValue = String(decoding: data, as: UTF8.self)
    }

    private func persistReceipt() throws -> Data {
        let data = try JSONEncoder().encode(receipt)
        try data.write(to: PinkhaHanlinNativeAcceptanceFixture.fileURL(PinkhaHanlinNativeAcceptanceFixture.resultFileName), options: .atomic)
        return data
    }

    private func require(_ condition: Bool, _ reason: String) throws {
        if !condition { throw HanlinNativeAcceptanceError.failed(reason) }
    }

    private func requireValue<T>(_ value: T?, _ reason: String) throws -> T {
        guard let value else { throw HanlinNativeAcceptanceError.failed(reason) }
        return value
    }

    /// Observe the canonical dispatch envelope without changing any SDK/host call,
    /// context, catalog, permission, result, or cancellation behavior.
    @MainActor
    private final class RecordingHost: HanlinHostIntegration {
        nonisolated let apiVersion = HanlinAPIVersion(major: 1, minor: 0)
        let host: PinkhaHanlinReadWriteHost
        var invocations: [HanlinToolInvocationID: HanlinHostInvocation] = [:]
        var executionCount = 0
        init(host: PinkhaHanlinReadWriteHost) { self.host = host }
        func context(for session: HanlinHostSession) async throws -> HanlinHostContext { try await host.context(for: session) }
        func catalog(for context: HanlinHostContext) async throws -> HanlinHostCatalog { try await host.catalog(for: context) }
        func execute(_ invocation: HanlinHostInvocation, progress: @escaping HanlinHostProgressHandler) async throws -> HanlinHostExecutionResult {
            executionCount += 1
            invocations[invocation.request.id] = invocation
            return try await host.execute(invocation, progress: progress)
        }
        func cancel(_ invocation: HanlinToolInvocationID) async { await host.cancel(invocation) }
        func open(_ destination: HanlinHostDestination) async throws -> HanlinHostNavigationResult { try await host.open(destination) }
    }
}
#endif
