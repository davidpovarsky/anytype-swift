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
    }

    func invalidate() {
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
#endif
