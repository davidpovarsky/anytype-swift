import Services
import Foundation

struct BlockFocus {
    let id: String
    let position: BlockFocusPosition
    let requestId = UUID()
}

enum EditorCursorFocusPolicy {
    case manual
    case firstEmptyTextBlock
    // Quick capture reopens a draft to keep writing: put the caret at the end of what
    // is already there, so the keyboard (and the type bar above it) always comes up
    case continueWriting
}

@MainActor
final class EditorCursorManager {
    private let focusSubjectHolder: FocusSubjectsHolder
    private let focusPolicy: EditorCursorFocusPolicy
    private var currentType: String?
    private var didAppearedOnce = false
    private var lastBlockFocus: BlockFocus?
    private var pendingBlockFocus: BlockFocus?

    private(set) var focusRequestId: UUID?

    var blockFocus: BlockFocus? {
        get { pendingBlockFocus }
        set {
            let previousRequestId = pendingBlockFocus?.requestId
            pendingBlockFocus = newValue
            if let newValue {
                focusRequestId = newValue.requestId
            } else if focusRequestId == previousRequestId {
                focusRequestId = nil
            }
        }
    }

    init(focusSubjectHolder: FocusSubjectsHolder, focusPolicy: EditorCursorFocusPolicy = .firstEmptyTextBlock) {
        self.focusSubjectHolder = focusSubjectHolder
        self.focusPolicy = focusPolicy
    }

    func didAppeared(with blocks: [EditorItem], type: String?) {
        currentType = type

        if !didAppearedOnce {
            setInitialFocus(blocks: blocks)
        }

        didAppearedOnce = true
    }

    func handleGeneralUpdate(with blocks: [EditorItem], type: String?) {
        guard didAppearedOnce, type != self.currentType else {
            return
        }

        self.currentType = type
        setInitialFocus(blocks: blocks)
    }

    func applyCurrentFocus(shouldInvalidateFocus: Bool = true) {
        guard let blockFocus = blockFocus else { return }
        guard blockFocus.requestId == focusRequestId else {
            pendingBlockFocus = nil
            return
        }
        let focusSubject = focusSubjectHolder.focusSubject(for: blockFocus.id)
        if shouldInvalidateFocus { pendingBlockFocus = nil }
        focusSubject.send(blockFocus.position)
    }

    /// Transfers ownership to a row configuration without cancelling its deferred focus.
    func consumeBlockFocus(for blockId: String) -> BlockFocus? {
        guard let focus = pendingBlockFocus, focus.id == blockId else { return nil }
        pendingBlockFocus = nil
        return focus.requestId == focusRequestId ? focus : nil
    }

    @discardableResult
    func registerFocusRequest() -> UUID {
        let requestId = UUID()
        focusRequestId = requestId
        return requestId
    }

    func focus(in textView: some TextViewManagingFocus, position: BlockFocusPosition) {
        registerFocusRequest()
        textView.setFocus(position)
    }
    
    func restoreLastFocus(at blockId: String) {
        
        guard let lastBlockFocus = lastBlockFocus, lastBlockFocus.id == blockId else { return }
        focus(at: lastBlockFocus.id, position: lastBlockFocus.position)
    }
    
    func focus(at blockId: String, position: BlockFocusPosition = .end) {
        registerFocusRequest()
        let focusSubject = focusSubjectHolder.focusSubject(for: blockId)

        focusSubject.send(position)
    }
    
    func didChangeCursorPosition(at blockId: String, position: BlockFocusPosition) {
        lastBlockFocus = BlockFocus(id: blockId, position: position)
    }

    // MARK: - Private

    private func setInitialFocus(blocks: [EditorItem]) {
        switch focusPolicy {
        case .manual:
            return
        case .firstEmptyTextBlock:
            setFocusOnFirstTextBlock(blocks: blocks)
        case .continueWriting:
            setFocusToContinueWriting(blocks: blocks)
        }
    }

    private func setFocusOnFirstTextBlock(blocks: [EditorItem]) {
        let firstModel = Array(blocks.prefix(3)).first(applying: { item -> (any BlockViewModelProtocol)? in
            if case let .block(blockViewModel) = item, blockViewModel.content.isText {
                return blockViewModel
            }

            return nil
        })

        if firstModel?.content.isEmpty ?? false {
            firstModel?.set(focus: .beginning)
        }
    }

    private func setFocusToContinueWriting(blocks: [EditorItem]) {
        let textModels = blocks.compactMap { item -> (any BlockViewModelProtocol)? in
            if case let .block(blockViewModel) = item, blockViewModel.content.isText {
                return blockViewModel
            }
            return nil
        }

        guard let lastNonEmpty = textModels.last(where: { !$0.content.isEmpty }) else {
            setFocusOnFirstTextBlock(blocks: blocks)
            return
        }
        // Prefer an empty block after the content over the end of the content itself
        let trailingEmpty = textModels.last.flatMap { $0.content.isEmpty ? $0 : nil }
        (trailingEmpty ?? lastNonEmpty).set(focus: .end)
    }
}
