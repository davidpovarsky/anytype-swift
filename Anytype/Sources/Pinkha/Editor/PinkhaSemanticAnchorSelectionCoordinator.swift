#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
import UIKit
import Services
import PinkhaKit
import ProtobufMessages

/// Owns one visible selection and its explicit confirmation. Native mutation
/// occurs only in the Create action; a cancelled preview is read-only.
@MainActor
final class PinkhaSemanticAnchorSelectionCoordinator {
    private weak var editor: EditorPageController?
    private let service = AnytypeHeartSemanticAnchorService()
    private var epoch = UUID()
    private var activeID: UUID?
    private var preparation: Task<Void, Never>?
    private var confirmation: UIAlertController?
    private var observedLease: PinkhaNativeReadLease?
    private var leaseObserver: OwnerObserver?
    private(set) var lastVerifiedCapture: PinkhaHeartSemanticAnchorVerifiedCapture?

    init(editor: EditorPageController) { self.editor = editor }

    func bind(_ textView: TextViewWithPlaceholder) {
        textView.pinkhaSemanticAnchorAction = { [weak self, weak textView] range in
            guard let self, let textView else { return nil }
            return self.action(in: textView, range: range)
        }
        textView.pinkhaSemanticAnchorOpenURL = { [weak self] url in
            guard let self else { return }
            do { openSources(try PinkhaSemanticTextAnchor(markerURL: url)) }
            catch { presentMessage(PinkhaSemanticAnchorStrings.message(for: error)) }
        }
    }

    func invalidate() {
#if DEBUG && targetEnvironment(simulator)
        observeSourceEntry("coordinator-invalidate")
#endif
        epoch = UUID()
        activeID = nil
        preparation?.cancel()
        preparation = nil
        observedLease = nil
        leaseObserver = nil
        lastVerifiedCapture = nil
        let old = confirmation
        confirmation = nil
        old?.dismiss(animated: false)
    }

    func editorWillDisappear() {
        // Showing our own confirmation may produce an appearance callback.
        // A real detach/rebind still calls invalidate independently.
        if let confirmation, editor?.presentedViewController === confirmation { return }
        invalidate()
    }

    private func action(in textView: TextViewWithPlaceholder, range: NSRange) -> UIMenuElement? {
        if let source = sourceAction(in: textView, range: range) { return source }
        guard activeID == nil, let editor, let model = editor.viewModel,
              editor.presentedViewController == nil,
              editor.viewIfLoaded?.window != nil, textView.isFirstResponder,
              textView.isEditable, !textView.isLockedForEditing, textView.markedTextRange == nil,
              let content = textContentView(containing: textView),
              let binding = content.pinkhaSemanticAnchorContext,
              let info = model.document.infoContainer.get(id: binding.blockID),
              case let .text(blockText) = info.content,
              BlockRestrictionsBuilder.build(textContentType: blockText.contentType).canApplyOtherMarkup,
              blockText.contentType != .title, blockText.contentType != .description,
              model.document.mode.isHandling, model.document.isOpened,
              model.document.permissions.canEditBlocks, model.document.details?.isReadonly == false,
              case .editing = model.blocksStateManager.editingState else { return nil }
        let text = textView.textStorage.string
        guard text.utf8.count <= 65_536, range.location != NSNotFound, range.location >= 0,
              range.length > 0, range.location <= text.utf16.count,
              range.length <= text.utf16.count - range.location,
              let lease = try? PinkhaNativeReadLifetime.shared.lease(forOpenedSpaceID: model.document.spaceId)
        else { return nil }
        do { try observe(lease) } catch { return nil }
        let selection = Selection(epoch: epoch, model: model, textView: textView, contentView: content,
            blockID: binding.blockID, inputOwner: binding.owner, text: text, range: range, lease: lease)
        return UIAction(title: PinkhaSemanticAnchorStrings.create, image: UIImage(systemName: "pin"),
            identifier: .init("pinkha.semanticAnchor.capture")) { [weak self] _ in
                self?.prepare(selection)
            }
    }

    private func sourceAction(in textView: TextViewWithPlaceholder, range: NSRange) -> UIAction? {
        guard activeID == nil, let editor, let model = editor.viewModel,
              editor.presentedViewController == nil, editor.viewIfLoaded?.window != nil,
              textView.window === editor.viewIfLoaded?.window, textView.isFirstResponder,
              textView.markedTextRange == nil, model.document.isOpened,
              model.document.mode.isHandling, model.torahSession != nil,
              range.location != NSNotFound, range.location >= 0, range.length > 0,
              range.location <= textView.attributedText.length,
              range.length <= textView.attributedText.length - range.location else { return nil }
        guard let anchor = PinkhaSemanticAnchorUI.selectedAnchor(in: textView.attributedText, range: range,
            spaceID: model.document.spaceId, objectID: model.document.objectId) else { return nil }
#if DEBUG && targetEnvironment(simulator)
        PinkhaSemanticSourceEntryDiagnostics.recordInput("source-menu-input", textView: textView)
        observeSourceEntry("source-menu-built")
#endif
        return UIAction(title: PinkhaSemanticAnchorUI.text(.sources), image: UIImage(systemName: "books.vertical"),
            identifier: .init("pinkha.semanticAnchor.sources")) { [weak self] _ in
#if DEBUG && targetEnvironment(simulator)
                PinkhaSemanticSourceEntryDiagnostics.record("source-menu-handler", state: ["coordinatorPresent": self != nil])
#endif
                self?.openSources(anchor)
            }
    }

    private func openSources(_ anchor: PinkhaSemanticTextAnchor) {
#if DEBUG && targetEnvironment(simulator)
        observeSourceEntry("open-sources-guard")
#endif
        guard activeID == nil, let editor, let model = editor.viewModel,
              editor.presentedViewController == nil, editor.viewIfLoaded?.window != nil,
              model.document.mode.isHandling, model.document.isOpened,
              let session = model.torahSession else { return }
#if DEBUG && targetEnvironment(simulator)
        observeSourceEntry("open-sources-guard-admitted")
#endif
        Task { @MainActor [weak self, weak editor] in
            do {
#if DEBUG && targetEnvironment(simulator)
                self?.observeSourceEntry("shared-source-session-enter")
#endif
                try await session.presentSemanticAnchorSources(anchor)
#if DEBUG && targetEnvironment(simulator)
                self?.observeSourceEntry("shared-source-session-return")
#endif
            }
            catch {
#if DEBUG && targetEnvironment(simulator)
                self?.observeSourceEntry("shared-source-session-error", error: error)
#endif
                guard let self, let editor, editor.viewModel === model,
                      editor.viewIfLoaded?.window != nil else { return }
                presentMessage(PinkhaSemanticAnchorStrings.message(for: error))
            }
        }
    }

#if DEBUG && targetEnvironment(simulator)
    /// Read-only UI state for the owned source continuation. It does not acquire
    /// a lease, issue an engine call, change selection, dismiss a menu or retry.
    private func observeSourceEntry(_ stage: String, error: Error? = nil) {
        guard PinkhaSemanticSourceEntryDiagnostics.isEnabled else { return }
        let editor = self.editor
        let model = editor?.viewModel
        let presented = editor?.presentedViewController
        var state: [String: Any] = [
            "captureActive": activeID != nil,
            "epoch": epoch.uuidString.lowercased(),
            "editorPresent": editor != nil,
            "modelPresent": model != nil,
            "windowPresent": editor?.viewIfLoaded?.window != nil,
            "presentedControllerPresent": presented != nil,
            "documentIsHandling": model?.document.mode.isHandling ?? false,
            "documentIsOpened": model?.document.isOpened ?? false,
            "sessionPresent": model?.torahSession != nil,
            "searchPresented": model?.torahSession?.isSearchPresented ?? false
        ]
        if let editor { state["editorIdentity"] = String(describing: ObjectIdentifier(editor)) }
        if let model { state["modelIdentity"] = String(describing: ObjectIdentifier(model)) }
        if let session = model?.torahSession { state["sessionIdentity"] = String(describing: ObjectIdentifier(session)) }
        if let presented { state["presentedControllerType"] = String(reflecting: type(of: presented)) }
        if let error {
            state["errorType"] = String(reflecting: type(of: error))
            state["errorDomain"] = (error as NSError).domain
            state["errorCode"] = (error as NSError).code
            state["errorDescription"] = String(String(reflecting: error).prefix(256))
        }
        PinkhaSemanticSourceEntryDiagnostics.record(stage, state: state)
    }
#endif

    private func prepare(_ selection: Selection) {
        guard activeID == nil, owns(selection, focused: true), let editor,
              editor.presentedViewController == nil else { return }
        let id = UUID()
        activeID = id
        preparation = Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                let anchor = try PinkhaSemanticTextAnchor(
                    spaceID: selection.spaceID, objectID: selection.objectID)
                let pending = try await service.prepareVisibleSelection(anchor: anchor,
                    blockID: selection.blockID, visibleText: selection.text, selection: selection.range,
                    lease: selection.lease)
                try Task.checkCancellation()
                guard activeID == id, owns(selection, focused: true) else { finish(id); return }
                preparation = nil
                presentConfirmation(selection, pending: pending, id: id)
            } catch {
                guard activeID == id, owns(selection, focused: false) else { finish(id); return }
                finish(id)
                presentMessage(PinkhaSemanticAnchorStrings.message(for: error))
            }
        }
    }

    private func presentConfirmation(_ selection: Selection,
                                     pending: PinkhaHeartSemanticAnchorPending, id: UUID) {
        guard let editor, editor.presentedViewController == nil else { finish(id); return }
#if DEBUG && targetEnvironment(simulator)
        if let textView = selection.textView {
            PinkhaSemanticAnchorMountedObserver.prepared(editor: editor, textView: textView,
                blockID: selection.blockID, range: selection.range, pending: pending, lease: selection.lease)
        }
#endif
        // The client already validated the complete native text and grapheme range.
        let selected = (selection.text as NSString).substring(with: selection.range)
        let alert = PinkhaSemanticAnchorUI.confirmation(selectedText: selected,
            cancelled: { [weak self] in
                self?.confirmation = nil
                self?.finish(id)
#if DEBUG && targetEnvironment(simulator)
                if let editor = self?.editor { PinkhaSemanticAnchorMountedObserver.cancelled(editor: editor) }
#endif
            }, willConfirm: { [weak self] in
                self?.confirmation = nil
            }, confirmed: { [weak self] in
                self?.apply(selection, pending: pending, id: id)
            })
        confirmation = alert
        editor.present(alert, animated: true)
    }

    private func apply(_ selection: Selection, pending: PinkhaHeartSemanticAnchorPending, id: UUID) {
        guard activeID == id, owns(selection, focused: false) else { finish(id); return }
#if DEBUG && targetEnvironment(simulator)
        if let editor { PinkhaSemanticAnchorMountedObserver.applyQueued(editor: editor, pending: pending) }
#endif
        Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                let capture = try await service.apply(pending)
                guard activeID == id, owns(selection, focused: false),
                      capture.generation == selection.lease.generation else { finish(id); return }
                lastVerifiedCapture = capture
#if DEBUG && targetEnvironment(simulator)
                if let editor { PinkhaSemanticAnchorMountedObserver.verified(editor: editor, capture: capture) }
#endif
                finish(id)
                presentMessage(PinkhaSemanticAnchorStrings.created)
            } catch {
#if DEBUG && targetEnvironment(simulator)
                if let editor { PinkhaSemanticAnchorMountedObserver.applyFailed(editor: editor, pending: pending, error: error) }
#endif
                guard activeID == id, owns(selection, focused: false) else { finish(id); return }
                finish(id)
                presentMessage(PinkhaSemanticAnchorStrings.message(for: error))
            }
        }
    }

    private func owns(_ selection: Selection, focused: Bool) -> Bool {
        guard selection.epoch == epoch, let editor, let model = editor.viewModel,
              model === selection.model, let textView = selection.textView,
              let contentView = selection.contentView,
              let binding = contentView.pinkhaSemanticAnchorContext,
              binding.owner == selection.inputOwner,
              binding.blockID.utf8.elementsEqual(selection.blockID.utf8),
              editor.viewIfLoaded?.window != nil, textView.window === editor.viewIfLoaded?.window,
              model.document.mode.isHandling, model.document.isOpened,
              model.document.permissions.canEditBlocks, model.document.details?.isReadonly == false,
              model.document.spaceId.utf8.elementsEqual(selection.spaceID.utf8),
              model.document.objectId.utf8.elementsEqual(selection.objectID.utf8),
              textView.textStorage.string.utf8.elementsEqual(selection.text.utf8),
              (try? selection.lease.validate()) != nil else { return false }
        if focused {
            return textView.isFirstResponder && textView.selectedRange == selection.range
                && textView.markedTextRange == nil
        }
        return true
    }

    private func finish(_ id: UUID) {
        guard activeID == id else { return }
        activeID = nil
        epoch = UUID()
        preparation = nil
    }

    private func presentMessage(_ message: String) {
        guard let editor, editor.viewIfLoaded?.window != nil,
              editor.presentedViewController == nil else { return }
        let alert = PinkhaSemanticAnchorUI.outcome(message) { [weak self] in
            self?.confirmation = nil
        }
        confirmation = alert
        editor.present(alert, animated: true)
    }

    private func observe(_ lease: PinkhaNativeReadLease) throws {
        if observedLease?.generation == lease.generation { return }
        let observer = OwnerObserver(owner: self, generation: lease.generation)
        try lease.observeRetirement(observer)
        observedLease = lease
        leaseObserver = observer
    }

    private func retired(_ generation: UUID) {
        guard observedLease?.generation == generation else { return }
        invalidate()
    }

    private func textContentView(containing textView: UITextView) -> TextBlockContentView? {
        var current = textView.superview
        while let view = current {
            if let content = view as? TextBlockContentView,
               content.textView.textView === textView { return content }
            current = view.superview
        }
        return nil
    }

    @MainActor
    private final class OwnerObserver: PinkhaNativeReadLeaseObserver {
        weak var owner: PinkhaSemanticAnchorSelectionCoordinator?
        let generation: UUID
        init(owner: PinkhaSemanticAnchorSelectionCoordinator, generation: UUID) {
            self.owner = owner; self.generation = generation
        }
        func nativeReadLeaseDidRetire() { owner?.retired(generation) }
    }

    @MainActor
    private final class Selection {
        let epoch: UUID
        let model: any EditorPageViewModelProtocol
        weak var textView: TextViewWithPlaceholder?
        weak var contentView: TextBlockContentView?
        let spaceID: String
        let objectID: String
        let blockID: String
        let inputOwner: ObjectIdentifier
        let text: String
        let range: NSRange
        let lease: PinkhaNativeReadLease

        init(epoch: UUID, model: any EditorPageViewModelProtocol, textView: TextViewWithPlaceholder,
             contentView: TextBlockContentView, blockID: String, inputOwner: ObjectIdentifier,
             text: String, range: NSRange, lease: PinkhaNativeReadLease) {
            self.epoch = epoch; self.model = model; self.textView = textView; self.contentView = contentView
            spaceID = model.document.spaceId; objectID = model.document.objectId
            self.blockID = blockID; self.inputOwner = inputOwner
            self.text = text; self.range = range; self.lease = lease
        }
    }
}

#if DEBUG && targetEnvironment(simulator)
/// Private diagnostics only. The original mounted observer remains disabled in
/// this continuation, and no original fixture/capture/readback file is touched.
@MainActor
enum PinkhaSemanticSourceEntryDiagnostics {
    private static let context: [String: String]? = {
        let env = ProcessInfo.processInfo.environment
        guard env["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1",
              env["PINKHA_SEMANTIC_MOUNTED_UI"] == "0" else { return nil }
        var binding: [String: String] = [:]
        for (key, suffix, pattern) in [
            ("sourceSHA", "SOURCE_SHA", "^[0-9a-f]{40}$"),
            ("runID", "RUN_ID", "^[0-9]+$"),
            ("runAttempt", "RUN_ATTEMPT", "^[1-9][0-9]*$"),
            ("nonce", "NONCE", "^[0-9a-f]{32}$")
        ] {
            guard let value = env["PINKHA_SEMANTIC_MOUNTED_" + suffix],
                  value.range(of: pattern, options: .regularExpression) != nil else { return nil }
            binding[key] = value
        }
        return binding
    }()
    private static var events: [[String: Any]] = []
    static var isEnabled: Bool { context != nil }

    static func recordInput(_ stage: String, textView: UITextView) {
        guard isEnabled else { return }
        let gestures = (textView.gestureRecognizers ?? []).compactMap { recognizer -> [String: Any]? in
            guard recognizer is UILongPressGestureRecognizer else { return nil }
            return ["type": String(reflecting: type(of: recognizer)), "enabled": recognizer.isEnabled,
                    "state": recognizer.state.rawValue]
        }
        record(stage, state: ["inputIdentity": String(describing: ObjectIdentifier(textView)),
            "firstResponder": textView.isFirstResponder, "windowPresent": textView.window != nil,
            "selectedLength": textView.selectedRange.length, "editable": textView.isEditable,
            "longPressRecognizers": gestures])
    }

    static func record(_ stage: String, state: [String: Any]) {
        guard let context, events.count < 64 else { return }
        let event: [String: Any] = ["stage": stage, "uptime": ProcessInfo.processInfo.systemUptime, "state": state]
        events.append(event)
        let processID = ProcessInfo.processInfo.processIdentifier
        var value: [String: Any] = [
            "protocol": "pinkha-heart-semantic-source-entry-observation-v1",
            "processID": processID, "events": events,
            "maximumEvents": 64, "capacityReached": events.count == 64,
            "extraEngineCalls": 0, "selectionChanges": 0, "menuDismissals": 0,
            "automaticRetries": 0, "originalMountedObserverEnabled": false
        ]
        for (key, entry) in context { value[key] = entry }
        guard JSONSerialization.isValidJSONObject(value),
              let bytes = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]),
              bytes.count <= 65_536,
              let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else { return }
        let file = directory.appendingPathComponent("pinkha-semantic-source-entry-\(processID).json")
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            try bytes.write(to: file, options: .atomic)
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file.path)
        } catch {
            // Observation failure must not become a product retry or success.
            // The collector requires the original file before making a claim.
        }
    }
}
#endif
#endif
