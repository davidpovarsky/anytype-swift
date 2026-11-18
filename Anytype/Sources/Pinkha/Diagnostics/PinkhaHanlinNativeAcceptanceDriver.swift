#if DEBUG && targetEnvironment(simulator)
import Foundation
import UIKit
import Factory
import AnytypeCore
import Services
import ProtobufMessages
import HanlinAgentCore
import HanlinHostContracts
import HanlinPlatformContracts

/// Disposable simulator diagnostic. XCTest still presses the production consent,
/// Cancel, Create page and Close controls. This code cannot issue an approval.
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

    struct Receipt: Codable {
        let fixtureID: UUID
        let sourceSHA: String
        let runID: String
        let runAttempt: String
        let sessionID: UUID
        let processID: Int32
        let startedAt: Date
        var finishedAt: Date?
        var phase = "STARTING"
        var checks: [String: Bool] = [:]
        var createdObjectID: String?
        var failure: String?
        var providerConfigured = false
    }

    static func startIfRequested(host: PinkhaHanlinReadWriteHost,
                                 presentation: PinkhaHanlinChatPresentation,
                                 controller: PinkhaHanlinChatController,
                                 source: UIViewController?, routeOwner: SpaceHubCoordinatorViewModel?) {
        guard ProcessInfo.processInfo.environment["PINKHA_HANLIN_NATIVE_UI"] == "1" else { return }
        do {
            // viewDidAppear may repeat when an actual native alert disappears.
            if let active, active.host.session == host.session { return }
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
              host.session.context.namespace.account == fixture.accountID,
              host.session.context.namespace.space == fixture.spaceID,
              host.session.context.objectReference == fixture.sourceObjectID,
              host.session.context.selectionReferences.isEmpty,
              editor.viewModel?.document.objectId == fixture.sourceObjectID,
              !presentation.isConfigured else { throw HanlinNativeAcceptanceError.invalidFixture }
        self.fixture = fixture; self.host = host; self.presentation = presentation
        self.controller = controller; self.editor = editor; self.routeOwner = routeOwner
        self.rootPresenter = root
        self.statusLabel = Self.makeStatusLabel(in: window)
        self.receipt = Receipt(fixtureID: fixture.fixtureID, sourceSHA: fixture.sourceSHA,
            runID: fixture.runID, runAttempt: fixture.runAttempt, sessionID: host.session.id,
            processID: ProcessInfo.processInfo.processIdentifier, startedAt: Date())
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
            try emit("READY_TO_CLOSE")
            // Only the existing product Close button ends this presentation.
            try await waitUntil { self.controller?.presentingViewController == nil }
            try await denied(host: host, invocation: makeReadInvocation())
            try await denied(host: host, invocation: copyCreationForDeniedAttempt(createdCall))
            receipt.checks["closed_presentation_denies_read_and_create"] = true
            try emit("CHECKING_NATIVE_AUTHORITY")
            try await verifyNativeAuthorityChanges()
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

    private func verifyRead(_ result: HanlinHostExecutionResult) throws {
        try require(result.effectState == .confirmedNoEffect, "read_effect_mismatch")
        guard case .completed(let content) = result.result.outcome, content.count == 1,
              case .text(let text) = content[0] else { throw HanlinNativeAcceptanceError.failed("read_payload_missing") }
        let snapshot = try JSONDecoder().decode(PinkhaHanlinTextSnapshot.self, from: Data(text.utf8))
        try require(snapshot.objectReference == fixture.sourceObjectID && snapshot.spaceReference == fixture.spaceID
                    && snapshot.title == fixture.sourceTitle && snapshot.coverage == "documentTextBlocksOnly"
                    && snapshot.blocks.contains { $0.reference == fixture.sourceBlockID && $0.text == fixture.sourceText },
                    "native_read_did_not_match_prepared_body")
        guard case .completed(let metadata) = host.metadataReceipt(for: result.result.invocationID)?.result.outcome,
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

        let space = try PinkhaHanlinNativeAccess(presenter: rootPresenter, routeOwner: routeOwner,
            conversationID: UUID(), locale: Locale(identifier: "en"))
        try space.validate(space.session.context)
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: fixture.alternateSpaceID)
        try require(Container.shared.activeSpaceManager().workspaceInfo?.accountSpaceId == fixture.alternateSpaceID,
                    "native_space_did_not_change")
        try denied(space)
        receipt.checks["native_active_space_change_denied"] = true
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: fixture.spaceID)
        try await waitUntil { routeOwner.currentSpaceId == self.fixture.spaceID }

        let account = try PinkhaHanlinNativeAccess(presenter: rootPresenter, routeOwner: routeOwner,
            conversationID: UUID(), locale: Locale(identifier: "en"))
        try account.validate(account.session.context)
        try require(Container.shared.accountManager().account.id == fixture.accountID, "foreign_account_before_logout")
        try await Container.shared.authService().logout(removeData: false)
        try require(!PinkhaHanlinAccountOwner.shared.isAvailable(account: fixture.accountID), "account_owner_not_revoked")
        try denied(account)
        receipt.checks["native_account_logout_denied"] = true
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

    private func makeReadInvocation() throws -> HanlinHostInvocation {
        let id = try HanlinToolInvocationID(validating: UUID().uuidString.lowercased())
        return .init(request: .init(id: id,
            logicalToolID: .init(providerInstanceID: try .init(validating: "anytype.host"), localToolID: try .init(validating: "read-context-text")),
            aliasUsed: "anytype_read_context_text", descriptorRevision: try .init(1), routingTableRevision: .init(1),
            arguments: .object([:]), origin: .assistantModel, idempotencyKey: id.rawValue,
            deadline: Date().addingTimeInterval(30), limits: try .init()),
            session: host.session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
            writeGuarantee: .readOnly, originalArgumentsJSON: Data("{}".utf8))
    }

    private func copyCreationForDeniedAttempt(_ original: HanlinHostInvocation) throws -> HanlinHostInvocation {
        let id = try HanlinToolInvocationID(validating: UUID().uuidString.lowercased())
        return .init(request: .init(id: id, logicalToolID: original.request.logicalToolID,
            aliasUsed: original.request.aliasUsed, descriptorRevision: original.request.descriptorRevision,
            routingTableRevision: original.request.routingTableRevision, arguments: original.request.arguments,
            origin: .assistantModel, idempotencyKey: id.rawValue, deadline: Date().addingTimeInterval(30), limits: try .init()),
            session: host.session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
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
        receipt.providerConfigured = presentation.isConfigured
        let data = try JSONEncoder().encode(receipt)
        try data.write(to: PinkhaHanlinNativeAcceptanceFixture.fileURL(PinkhaHanlinNativeAcceptanceFixture.resultFileName), options: .atomic)
        statusLabel.text = phase
        statusLabel.accessibilityValue = String(decoding: data, as: UTF8.self)
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
