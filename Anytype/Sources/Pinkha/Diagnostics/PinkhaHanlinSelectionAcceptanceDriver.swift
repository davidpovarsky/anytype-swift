#if DEBUG && targetEnvironment(simulator)
import Foundation
import CryptoKit
import UIKit
import Factory
import AnytypeCore
import Services
import ProtobufMessages
import HanlinAgentCore
import HanlinHostContracts
import HanlinPlatformContracts

/// Observes a real selection-entry presentation. Never selects blocks, grants
/// consent, navigates, or invokes a mount acknowledgement on behalf of XCTest.
@MainActor
final class PinkhaHanlinSelectionAcceptanceDriver {
    typealias NavigationContext = PinkhaHanlinNativeAcceptanceDriver.NavigationContext
    typealias NativeReturnReceipt = PinkhaHanlinNativeAcceptanceDriver.NativeReturnReceipt

    struct ReadReceipt: Codable {
        let invocationID: String
        let objectReference: String
        let spaceReference: String
        let sourceRevision: String
        let title: String
        let blockReferences: [String]
        let textSHA256: String
        let coverage: String
        let effectState: String
        let metadataContentsCount: Int
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
        var phase = "STARTING"
        var checks: [String: Bool] = [:]
        var selectedRead: ReadReceipt?
        var nativeReturn: NativeReturnReceipt?
        var deniedReadAttempts = 0
        var deniedReadInvocationIDs: [String] = []
        var providerConfigured = false
        var failure: String?
        var finishedAt: Date?
    }

    static let requiredChecks: Set<String> = [
        "middleware_logging_disabled", "native_single_block_selection_context",
        "read_denied_before_native_consent", "native_selected_text_read", "unselected_text_excluded",
        "read_receipt_contains_metadata_only", "native_selected_block_mounted_on_return",
        "closed_selection_host_denies_read", "no_provider_configuration"
    ]

    private static var active: PinkhaHanlinSelectionAcceptanceDriver?
    private let fixture: PinkhaHanlinSelectionAcceptanceFixture
    private let host: PinkhaHanlinReadWriteHost
    private let presentation: PinkhaHanlinChatPresentation
    private weak var controller: PinkhaHanlinChatController?
    private weak var editor: EditorPageController?
    private weak var scene: UIWindowScene?
    private let statusLabel: UILabel
    private var receipt: Receipt
    private var task: Task<Void, Never>?

    static func startIfRequested(host: PinkhaHanlinReadWriteHost, presentation: PinkhaHanlinChatPresentation,
                                 controller: PinkhaHanlinChatController, source: UIViewController?) {
        let environment = ProcessInfo.processInfo.environment
        guard environment["PINKHA_HANLIN_SELECTION_UI"] == "1" else { return }
        do {
            guard environment["PINKHA_HANLIN_NATIVE_UI"] != "1" else { throw HanlinNativeAcceptanceError.invalidFixture }
            if let active {
                guard active.host.session == host.session else { throw HanlinNativeAcceptanceError.invalidFixture }
                return // Native consent alerts may repeat viewDidAppear.
            }
            guard let editor = source as? EditorPageController else { throw HanlinNativeAcceptanceError.invalidFixture }
            let fixture = try PinkhaHanlinSelectionAcceptanceFixture.loadForUI()
            let driver = try Self(fixture: fixture, host: host, presentation: presentation, controller: controller, editor: editor)
            active = driver
            driver.task = Task { await driver.run() }
        } catch {
            if let window = controller.viewIfLoaded?.window {
                let label = makeStatusLabel(in: window)
                label.text = "SELECTION_SETUP_FAIL"
                label.accessibilityValue = "Selected native fixture setup rejected"
            }
        }
    }

    private init(fixture: PinkhaHanlinSelectionAcceptanceFixture, host: PinkhaHanlinReadWriteHost,
                 presentation: PinkhaHanlinChatPresentation, controller: PinkhaHanlinChatController,
                 editor: EditorPageController) throws {
        let base = fixture.base
        guard let window = editor.viewIfLoaded?.window, window === controller.viewIfLoaded?.window,
              let scene = window.windowScene, scene.activationState == .foregroundActive,
              Container.shared.serverConfigurationStorage().currentConfiguration() == .localOnly,
              Container.shared.accountManager().account.id == base.accountID,
              host.session == presentation.session,
              host.session.context.namespace.app == "anytype",
              host.session.context.namespace.account == base.accountID,
              host.session.context.namespace.workspace == base.spaceID,
              host.session.context.namespace.space == base.spaceID,
              host.session.context.objectReference == base.sourceObjectID,
              host.session.context.selectionReferences.map({ Data($0.utf8) }) == [Data(base.sourceBlockID.utf8)],
              host.session.context.sourceRevision?.isEmpty == false,
              editor.viewModel?.document.objectId == base.sourceObjectID,
              editor.viewModel?.document.spaceId == base.spaceID,
              !presentation.isConfigured else { throw HanlinNativeAcceptanceError.invalidFixture }
        self.fixture = fixture; self.host = host; self.presentation = presentation
        self.controller = controller; self.editor = editor; self.scene = scene
        self.statusLabel = Self.makeStatusLabel(in: window)
        self.receipt = Receipt(fixtureID: base.fixtureID, sourceSHA: base.sourceSHA, runID: base.runID,
            runAttempt: base.runAttempt, sessionID: host.session.id, navigationContext: NavigationContext(host.session.context),
            processID: ProcessInfo.processInfo.processIdentifier, startedAt: Date())
    }

    private static func makeStatusLabel(in window: UIWindow) -> UILabel {
        let label = UILabel(frame: CGRect(x: 8, y: window.safeAreaInsets.top + 6, width: max(1, window.bounds.width - 16), height: 20))
        label.font = .monospacedSystemFont(ofSize: 10, weight: .regular)
        label.backgroundColor = .systemBackground
        label.textColor = .label
        label.isUserInteractionEnabled = false
        label.isAccessibilityElement = true
        label.accessibilityIdentifier = "pinkha.hanlin.selection-acceptance-status"
        label.autoresizingMask = [.flexibleWidth, .flexibleBottomMargin]
        window.addSubview(label)
        return label
    }

    private func run() async {
        do {
            try require(InvocationSettings.handler?.isLogEnabled == false, "middleware_logging_enabled")
            receipt.checks["middleware_logging_disabled"] = true
            try requireOriginalSelection()
            _ = try await host.context(for: host.session)
            receipt.checks["native_single_block_selection_context"] = true
            let initial = try await host.catalog(for: host.session.context)
            try require(!initial.tools.contains { $0.route.alias == "anytype_read_context_text" }, "selection_read_advertised_without_consent")
            try await requireReadDenied()
            receipt.checks["read_denied_before_native_consent"] = true
            try emit("SELECTION_AWAIT_READ_CONSENT")
            // Only the real Share button and native Allow alert can satisfy this.
            try await waitUntil { self.presentation.readAllowed }
            try await waitUntil { self.controller?.presentedViewController == nil }
            try presentation.validateInstallation(for: host.session)
            try requireOriginalSelection()
            let catalog = try await host.catalog(for: host.session.context)
            let dispatcher = HanlinHostDispatcher(host: host)
            let result = try await dispatcher.dispatch(alias: "anytype_read_context_text", argumentsJSON: "{}",
                providerCallID: "native-selected-block-read", runID: UUID(), step: 0,
                session: host.session, catalog: catalog, limits: try HanlinToolInvocationLimits())
            try verifyRead(result)
            try require(presentation.returnReceipt == nil, "selected_return_preceded_user_action")
            try emit("SELECTION_READY_TO_RETURN")
            try await observeNativeReturn()
            try await requireReadDenied()
            // Use a second fresh valid invocation after yielding; a cached denial is insufficient.
            await Task.yield()
            try requireOriginalSelection()
            try await requireReadDenied()
            receipt.checks["closed_selection_host_denies_read"] = true
            try require(!presentation.isConfigured, "selection_provider_configured")
            receipt.checks["no_provider_configuration"] = true
            try require(Set(receipt.checks.keys) == Self.requiredChecks && receipt.checks.values.allSatisfy({ $0 }),
                        "selection_checks_incomplete")
            receipt.finishedAt = Date()
            try emit("HANLIN_SELECTION_ACCEPTANCE_PASS")
        } catch {
            if case HanlinNativeAcceptanceError.failed(let reason) = error { receipt.failure = reason }
            else { receipt.failure = "selected_native_operation_or_context_failed" }
            receipt.finishedAt = Date()
            try? emit("HANLIN_SELECTION_ACCEPTANCE_FAIL")
        }
    }

    private func requireOriginalSelection() throws {
        guard let model = editor?.viewModel,
              model.document.objectId == fixture.base.sourceObjectID,
              model.document.spaceId == fixture.base.spaceID,
              case .selecting(let ids, _) = model.blocksStateManager.editingState,
              ids.map({ Data($0.utf8) }) == [Data(fixture.base.sourceBlockID.utf8)] else {
            throw HanlinNativeAcceptanceError.failed("actual_native_single_selection_changed")
        }
    }

    private func verifyRead(_ result: HanlinHostExecutionResult) throws {
        let base = fixture.base
        try require(result.effectState == .confirmedNoEffect, "selected_read_effect_mismatch")
        guard case .completed(let contents) = result.result.outcome, contents.count == 1,
              case .text(let text) = contents[0] else { throw HanlinNativeAcceptanceError.failed("selected_read_payload_missing") }
        let snapshot = try JSONDecoder().decode(PinkhaHanlinTextSnapshot.self, from: Data(text.utf8))
        try require(snapshot.objectReference == base.sourceObjectID && snapshot.spaceReference == base.spaceID
                    && snapshot.title == base.sourceTitle && snapshot.sourceRevision == host.session.context.sourceRevision
                    && snapshot.coverage == "selectedTextBlocksOnly" && snapshot.blocks.count == 1,
                    "selected_read_scope_mismatch")
        let selected = try requireValue(snapshot.blocks.first, "selected_read_block_missing")
        try require(selected.reference.utf8.elementsEqual(base.sourceBlockID.utf8) && selected.text == base.sourceText,
                    "selected_read_body_mismatch")
        try require(!snapshot.blocks.contains { $0.reference == fixture.excludedBlockID || $0.text.contains(fixture.excludedText) },
                    "unselected_native_text_leaked")
        guard case .completed(let metadata) = host.metadataReceipt(for: result.result.invocationID)?.result.outcome,
              metadata.isEmpty else { throw HanlinNativeAcceptanceError.failed("selected_read_receipt_retained_payload") }
        receipt.selectedRead = ReadReceipt(invocationID: result.result.invocationID.rawValue,
            objectReference: snapshot.objectReference, spaceReference: snapshot.spaceReference, sourceRevision: snapshot.sourceRevision,
            title: snapshot.title, blockReferences: snapshot.blocks.map(\.reference),
            textSHA256: SHA256.hash(data: Data(selected.text.utf8)).map { String(format: "%02x", $0) }.joined(),
            coverage: snapshot.coverage, effectState: "confirmedNoEffect", metadataContentsCount: metadata.count)
        receipt.checks["native_selected_text_read"] = true
        receipt.checks["unselected_text_excluded"] = true
        receipt.checks["read_receipt_contains_metadata_only"] = true
    }

    private func observeNativeReturn() async throws {
        try await waitUntil { self.presentation.returnReceipt.map { $0.state != .awaitingMount } ?? false }
        let handoff = try requireValue(presentation.returnReceipt, "selected_return_missing")
        try require(handoff.state == .mounted, "selected_return_not_mounted")
        let result = try requireValue(handoff.receipt, "selected_return_receipt_missing")
        let destination = handoff.destination
        try result.validate(for: destination)
        guard case .presented(let requestID, let context, let object, let block) = result else {
            throw HanlinNativeAcceptanceError.failed("selected_return_only_queued")
        }
        let base = fixture.base
        try require(context == host.session.context && destination.context == context
                    && requestID == destination.requestID && object == base.sourceObjectID
                    && destination.objectReference == base.sourceObjectID
                    && block == base.sourceBlockID && destination.blockReference == base.sourceBlockID,
                    "selected_return_identity_changed")
        try await waitUntil { self.controller?.presentingViewController == nil }
        try requireOriginalSelection()
        guard let editor, let scene, scene.activationState == .foregroundActive,
              PinkhaHanlinNativeAccess.isMounted(editor, in: scene),
              let item = editor.dataSource.snapshot().itemIdentifiers.first(where: {
                  guard case .block(let mounted) = $0 else { return false }
                  return mounted.info.id.utf8.elementsEqual(base.sourceBlockID.utf8)
              }), let index = editor.dataSource.indexPath(for: item),
              editor.collectionView.indexPathsForVisibleItems.contains(index),
              let cell = editor.collectionView.cellForItem(at: index),
              cell.window?.windowScene === scene,
              cell.convert(cell.bounds, to: editor.collectionView).intersects(editor.collectionView.bounds) else {
            throw HanlinNativeAcceptanceError.failed("selected_return_actual_block_not_visible")
        }
        try require(receipt.nativeReturn == nil && NavigationContext(context) == receipt.navigationContext,
                    "selected_return_context_changed")
        receipt.nativeReturn = NativeReturnReceipt(requestID: requestID, queuedRequestID: destination.requestID,
            sessionID: host.session.id, context: NavigationContext(context), objectReference: object,
            blockReference: block, presentationAcknowledged: result.presentationAcknowledged)
        receipt.checks["native_selected_block_mounted_on_return"] = true
    }

    private func requireReadDenied() async throws {
        let id = try HanlinToolInvocationID(validating: UUID().uuidString.lowercased())
        let invocation = HanlinHostInvocation(request: .init(id: id,
            logicalToolID: .init(providerInstanceID: try .init(validating: "anytype.host"), localToolID: try .init(validating: "read-context-text")),
            aliasUsed: "anytype_read_context_text", descriptorRevision: try .init(1), routingTableRevision: .init(1),
            arguments: .object([:]), origin: .assistantModel, idempotencyKey: id.rawValue,
            deadline: Date().addingTimeInterval(30), limits: try .init()),
            session: host.session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
            writeGuarantee: .readOnly, originalArgumentsJSON: Data("{}".utf8))
        do {
            let result = try await host.execute(invocation) { _ in }
            try require(result.effectState == .notDispatched, "denied_selected_read_may_have_dispatched")
            guard case .failed = result.result.outcome else { throw HanlinNativeAcceptanceError.failed("denied_selected_read_completed") }
        } catch HanlinHostError.staleContext {}
          catch HanlinHostError.denied {}
        receipt.deniedReadAttempts += 1
        receipt.deniedReadInvocationIDs.append(id.rawValue)
    }

    private func waitUntil(_ condition: () -> Bool) async throws {
        let clock = ContinuousClock(); let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            if condition() { return }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw HanlinNativeAcceptanceError.failed("selected_native_ui_or_state_timeout")
    }

    private func emit(_ phase: String) throws {
        receipt.phase = phase
        receipt.providerConfigured = presentation.isConfigured
        let data = try JSONEncoder().encode(receipt)
        try data.write(to: PinkhaHanlinNativeAcceptanceFixture.fileURL(PinkhaHanlinSelectionAcceptanceFixture.resultFileName), options: .atomic)
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
}
#endif
