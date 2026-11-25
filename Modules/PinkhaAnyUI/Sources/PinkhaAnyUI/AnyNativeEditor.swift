#if canImport(UIKit)
import Foundation
import UIKit
import SwiftUI
import UniformTypeIdentifiers
import NaturalLanguage
import PinkhaKit
import PinkhaAnyHost
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHanlin
import PinkhaHanlinUI
import PinkhaTorahPresentation
import TorahInspectorCore
import HanlinHostContracts

public struct AnyNativeEditor: UIViewControllerRepresentable {
    public let presentation: AnyDocumentPresentation
    public let revision: UInt64
    public init(presentation: AnyDocumentPresentation, revision: UInt64) {
        self.presentation = presentation; self.revision = revision
    }
    public func makeUIViewController(context: Context) -> AnyNativeEditorController {
        let controller = AnyNativeEditorController(presentation: presentation)
        controller.applyInterfaceDirection(context.environment.layoutDirection)
        return controller
    }
    public func updateUIViewController(_ controller: AnyNativeEditorController, context: Context) {
        controller.applyInterfaceDirection(context.environment.layoutDirection)
        controller.render()
    }
    public static func dismantleUIViewController(_ controller: AnyNativeEditorController, coordinator: ()) {
        controller.retireSemanticAnchorInteraction()
        controller.presentation.unmount()
    }
}

/// Native text selection and first-responder ownership stay in UIKit. The raw
/// inline Markdown and complete native style/version records stay in the model.
@MainActor
public final class AnyNativeEditorController: UIViewController, AnyEditorMountedSurface,
    UITableViewDelegate, UITextViewDelegate, UITableViewDropDelegate {
    public let presentation: AnyDocumentPresentation
    public let sceneID = UUID()
    private let table = UITableView(frame: .zero, style: .plain)
    private var dataSource: UITableViewDiffableDataSource<Int, String>!
    private var blockByID: [String: AnyEditorBlock] = [:]
    private var rendering = false
    private var previousIDs: [String] = []
    private var interfaceDirection: PinkhaLayoutDirection = .leftToRight
    private let conversationID = UUID()
    private weak var activeTextView: UITextView?
    private var compositionUndo: [ObjectIdentifier: (source: String, selection: NSRange)] = [:]
    private var semanticAnchorInteractionID: UUID?
    private var semanticAnchorPreparation: Task<Void, Never>?
    private var semanticAnchorConfirmation: UIAlertController?
    #if DEBUG
    private let semanticAnchorObservation = AnySemanticAnchorObservation.makeIfEnabled()
    #endif
    private var applyingSnapshot = false
    private var snapshotGeneration = UUID()
    private lazy var focus = AnyNativeFocusCoordinator(validate: { [weak self] intent in
        guard let self, self.presentation.isMounted, self.presentation.mountedOwnerID == intent.ownerID,
              self.presentation.canMutate, !self.presentation.isComposing,
              self.presentation.read?.snapshot.depthFirstIDs.contains(intent.blockID) == true,
              let block = self.presentation.read?.snapshot.blocks.first(where: { $0.id == intent.blockID }) else { return false }
        return block.native["_ver"] == intent.nativeVersion &&
            self.presentation.source(for: block).utf8.elementsEqual(intent.source.utf8)
    }, resolve: { [weak self] intent in
        guard let self, !self.applyingSnapshot, self.focusPresentationIsVisible,
              let path = self.dataSource?.indexPath(for: intent.blockID) else { return nil }
        self.table.scrollToRow(at: path, at: .middle, animated: false)
        self.table.layoutIfNeeded()
        guard let cell = self.table.cellForRow(at: path) as? AnyNativeBlockCell,
              cell.textView.blockID == intent.blockID, !cell.textView.isComposingMarkedText else { return nil }
        return cell.textView
    })

    public init(presentation: AnyDocumentPresentation) {
        self.presentation = presentation
        super.init(nibName: nil, bundle: nil)
    }
    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }

    public override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        view.semanticContentAttribute = interfaceDirection == .rightToLeft ? .forceRightToLeft : .forceLeftToRight
        table.translatesAutoresizingMaskIntoConstraints = false
        table.separatorStyle = .none
        table.keyboardDismissMode = .interactive
        table.rowHeight = UITableView.automaticDimension
        table.estimatedRowHeight = 68
        table.delegate = self; table.dropDelegate = self
        table.register(AnyNativeBlockCell.self, forCellReuseIdentifier: "block")
        table.accessibilityIdentifier = "any-native-editor-blocks"
        view.addSubview(table)
        NSLayoutConstraint.activate([
            table.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            table.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            table.topAnchor.constraint(equalTo: view.topAnchor),
            table.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
        dataSource = UITableViewDiffableDataSource<Int, String>(tableView: table) { [weak self] table, path, id in
            guard let self, let block = self.blockByID[id],
                  let cell = table.dequeueReusableCell(withIdentifier: "block", for: path) as? AnyNativeBlockCell else {
                return UITableViewCell()
            }
            self.configure(cell, block: block)
            return cell
        }
        #if DEBUG
        if let observation = semanticAnchorObservation {
            let label = observation.label
            label.translatesAutoresizingMaskIntoConstraints = false
            view.addSubview(label)
            NSLayoutConstraint.activate([
                label.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 2),
                label.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
                label.heightAnchor.constraint(equalToConstant: 10)
            ])
        }
        #endif
        render()
    }

    public override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        navigationController?.view.semanticContentAttribute = view.semanticContentAttribute
        // The current OS owns full-content back swiping and its leading edge.
        // Do not install the old engine's custom pan recognizer/delegate.
        navigationController?.interactiveContentPopGestureRecognizer?.isEnabled = true
        presentation.mount(surface: self)
        render()
        Task { [weak presentation] in await presentation?.load() }
    }

    public override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        if isMovingFromParent || isBeingDismissed || navigationController?.isBeingDismissed == true {
            retireSemanticAnchorInteraction()
            presentation.unmount()
        }
    }

    func applyInterfaceDirection(_ value: SwiftUI.LayoutDirection) {
        let direction: PinkhaLayoutDirection = value == .rightToLeft ? .rightToLeft : .leftToRight
        guard direction != interfaceDirection else { return }
        interfaceDirection = direction
        if isViewLoaded {
            view.semanticContentAttribute = direction == .rightToLeft ? .forceRightToLeft : .forceLeftToRight
            navigationController?.view.semanticContentAttribute = view.semanticContentAttribute
            for cell in table.visibleCells {
                (cell as? AnyNativeBlockCell)?.renderedSource = nil
            }
            render()
        }
    }

    public override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        focus.readinessChangedAfterUIUpdate(.layout)
    }

    private var focusPresentationIsVisible: Bool {
        guard isForegroundMounted else { return false }
        var current: UIViewController? = self
        while let controller = current {
            if controller.presentedViewController != nil { return false }
            current = controller.parent
        }
        return true
    }

    public var isForegroundMounted: Bool {
        isViewLoaded && view.window?.windowScene?.activationState == .foregroundActive &&
        !isMovingFromParent && !isBeingDismissed
    }

    public func isBlockVisible(_ id: String) -> Bool {
        guard isForegroundMounted, let path = dataSource.indexPath(for: id),
              table.indexPathsForVisibleRows?.contains(path) == true,
              let cell = table.cellForRow(at: path), cell.window != nil else { return false }
        return table.bounds.intersects(table.rectForRow(at: path))
    }

    public func reveal(blockID: String, selection: NSRange?) {
        if let selection, let block = presentation.read?.snapshot.blocks.first(where: { $0.id == blockID }) {
            focus.request(.init(blockID: blockID, ownerID: presentation.mountedOwnerID,
                nativeVersion: block.native["_ver"], source: presentation.source(for: block), selection: selection),
                attemptImmediately: false)
            focus.readinessChangedAfterUIUpdate(.layout)
        } else if let path = dataSource.indexPath(for: blockID) {
            table.scrollToRow(at: path, at: .middle, animated: false)
            table.layoutIfNeeded()
        }
    }

    public func dismissKeyboard() { focus.cancel(); view.endEditing(true) }

    public func captureActiveCompositionForRecovery() {
        focus.cancel()
        (activeTextView as? AnyNativeTextView)?.captureCompositionForRecovery()
    }

    public func render() {
        guard isViewLoaded, dataSource != nil else { return }
        // A diffable reload can retire the first responder, including when its
        // native block has moved or disappeared. Keep UIKit's marked buffer
        // mounted until it has been captured; its raw/base versions stay local.
        guard (activeTextView as? AnyNativeTextView)?.isComposingMarkedText != true else { return }
        let blocks = presentation.orderedBlocks
        let ids = blocks.map(\.id)
        if ids != previousIDs {
            if !focus.hasPending, let input = activeTextView as? AnyNativeTextView,
               input.isFirstResponder, let id = input.blockID, let old = blockByID[id] {
                focus.request(.init(blockID: id, ownerID: presentation.mountedOwnerID,
                    nativeVersion: old.native["_ver"], source: presentation.source(for: old),
                    selection: input.selectedRange), attemptImmediately: false)
            }
            blockByID = Dictionary(uniqueKeysWithValues: blocks.map { ($0.id, $0) })
            var snapshot = NSDiffableDataSourceSnapshot<Int, String>()
            snapshot.appendSections([0]); snapshot.appendItems(ids, toSection: 0)
            previousIDs = ids
            let generation = UUID(); snapshotGeneration = generation; applyingSnapshot = true
            dataSource.apply(snapshot, animatingDifferences: false) { [weak self] in
                guard let self, self.snapshotGeneration == generation else { return }
                self.applyingSnapshot = false
                self.configureVisibleCells()
                self.focus.readinessChangedAfterUIUpdate(.layout)
            }
        } else {
            blockByID = Dictionary(uniqueKeysWithValues: blocks.map { ($0.id, $0) })
            configureVisibleCells()
            focus.readinessChangedAfterUIUpdate(.layout)
        }
    }

    private func configureVisibleCells() {
        for cell in table.visibleCells {
            guard let cell = cell as? AnyNativeBlockCell, let id = cell.textView.blockID,
                  let block = blockByID[id] else { continue }
            configure(cell, block: block)
        }
        table.beginUpdates(); table.endUpdates()
        observeSemanticAnchors()
    }

    private func configure(_ cell: AnyNativeBlockCell, block: AnyEditorBlock) {
        guard !cell.textView.isComposingMarkedText else { return }
        let source = presentation.source(for: block)
        let renderedSource = presentation.unmappedDisplay(for: block.id) ?? source
        let projection = presentation.projection(for: block)
        let supported = ["paragraph", "heading", "list_item", "check_list_item", "code", "quote"].contains(block.type)
        cell.textView.blockID = block.id
        let historyEpoch = presentation.textHistoryEpochs[block.id, default: 0]
        if cell.renderedHistoryEpoch != historyEpoch { cell.textView.editHistory.removeAllActions() }
        cell.renderedHistoryEpoch = historyEpoch
        cell.textView.delegate = self
        configureComposition(cell.textView)
        cell.textView.onAttachmentReadiness = { [weak self] in self?.focus.readinessChangedAfterUIUpdate(.attachment) }
        cell.textView.accessibilityIdentifier = "any-native-block-" + block.id
        cell.textView.isEditable = supported && projection.isEditable && presentation.canMutate
        cell.textView.isSelectable = true
        cell.textView.inputAccessoryView = toolbar(for: cell.textView)
        let label = presentation.torah.linkedAssociationLabel(blockId: block.id)
        cell.sourceButton.isHidden = label == nil
        cell.sourceButton.accessibilityIdentifier = "any-native-block-sources-" + block.id
        cell.sourceButton.setTitle(label, for: .normal)
        cell.sourceAction = { [weak presentation] in presentation?.torah.openLinkedAssociations(blockId: block.id) }
        cell.stateLabel.isHidden = supported && projection.isEditable
        cell.stateLabel.text = supported ? AnyUIErrorText.text("תוכן זה מוצג לקריאה; העיצוב המקורי נשמר.",
            "This content is read-only; its original formatting is preserved.") :
            AnyUIErrorText.text("סוג בלוק זה טרם ניתן לעריכה כאן.", "This block type cannot be edited here yet.")
        cell.marker.text = AnyNativeBlockMarkerPolicy.marker(for: block)
        let selected = presentation.selectedBlockIDs.contains(block.id)
        cell.contentView.backgroundColor = selected ? UIColor.systemBlue.withAlphaComponent(0.045) : .clear
        if cell.renderedSource != renderedSource || cell.renderedNativeStyle != block.native["style"] {
            rendering = true
            let applied = AnyNativeTextRenderer.apply(attributed(projection, block: block),
                to: cell.textView, isComposing: cell.textView.isComposingMarkedText)
            rendering = false
            if applied {
                cell.renderedSource = renderedSource; cell.renderedNativeStyle = block.native["style"]
            }
        }
        var depth = 0, parent = block.parentID, seen = Set<String>()
        while !parent.isEmpty, let ancestor = blockByID[parent], seen.insert(parent).inserted {
            depth += 1; parent = ancestor.parentID
        }
        cell.indent.constant = CGFloat(min(depth, 12) * 16 + 12)
    }

    private func observeSemanticAnchors() {
        #if DEBUG
        guard let observer = semanticAnchorObservation else { return }
        let rendered = table.visibleCells.compactMap { cell -> AnySemanticAnchorObservation.RenderedBlock? in
            guard let cell = cell as? AnyNativeBlockCell, let id = cell.textView.blockID else { return nil }
            return .init(id: id, text: NSAttributedString(attributedString: cell.textView.attributedText),
                         selection: cell.textView.selectedRange,
                         isFirstResponder: cell.textView.isFirstResponder)
        }
        observer.update(presentation, rendered: rendered)
        #endif
    }

    private func configureComposition(_ textView: AnyNativeTextView) {
        textView.onMarkedBegin = { [weak self] input in
            guard let self, let id = input.blockID, let block = self.blockByID[id] else { return false }
            do {
                let source = self.presentation.source(for: block)
                let projection = self.presentation.projection(for: block)
                guard projection.display.utf8.elementsEqual(input.text.utf8) else { throw AnyHostError.changedDocument }
                try self.presentation.beginTextComposition(renderedBlock: block, source: source,
                                                            selection: input.selectedRange)
                self.focus.cancel()
                self.activeTextView = input
                self.compositionUndo[ObjectIdentifier(input)] = (source, input.selectedRange)
                if let toolbar = input.inputAccessoryView as? UIToolbar {
                    for item in toolbar.items ?? [] {
                        item.isEnabled = item.accessibilityIdentifier == "any-native-editor-done"
                    }
                }
                return true
            } catch { self.presentation.message = AnyUIErrorText.describe(error); return false }
        }
        textView.onMarkedProposal = { [weak self] input, display, selection in
            guard let self, let id = input.blockID else { return false }
            do {
                try self.presentation.stageTextComposition(blockID: id, display: display, selection: selection)
                return true
            } catch { self.presentation.message = AnyUIErrorText.describe(error); return false }
        }
        textView.onMarkedChanged = { [weak self] input in
            guard let self, let id = input.blockID else { return }
            do {
                try self.presentation.stageTextComposition(blockID: id, display: input.text,
                                                           selection: input.selectedRange)
            } catch { self.presentation.message = AnyUIErrorText.describe(error) }
        }
        textView.onMarkedEnd = { [weak self] input, allowSaving in
            guard let self, let id = input.blockID else { return }
            let before = self.compositionUndo.removeValue(forKey: ObjectIdentifier(input))
            let after = self.presentation.finishTextComposition(blockID: id, display: input.text,
                selection: input.selectedRange, allowSaving: allowSaving)
            if let before, let after, !before.source.utf8.elementsEqual(after.utf8), allowSaving {
                let finalSelection = input.selectedRange
                input.editHistory.registerUndo(withTarget: self) { owner in
                    owner.restoreText(before.source, blockID: id, selection: before.selection,
                                      inverse: after, inverseSelection: finalSelection)
                }
                input.editHistory.setActionName(AnyUIErrorText.text("עריכת טקסט", "Edit text"))
            }
            if allowSaving, self.presentation.isMounted { self.render() }
        }
    }

    private func attributed(_ projection: AnyInlineMarkdown, block: AnyEditorBlock) -> NSAttributedString {
        let paragraph = NSMutableParagraphStyle()
        let display = projection.isEditable ? projection.display : projection.source
        let detected: PinkhaLayoutDirection? = {
            guard !display.isEmpty,
                  let language = NLLanguageRecognizer.dominantLanguage(for: display)?.rawValue else { return nil }
            switch NSParagraphStyle.defaultWritingDirection(forLanguage: language) {
            case .rightToLeft: return .rightToLeft
            case .leftToRight: return .leftToRight
            default: return nil
            }
        }()
        let decision = AnyNativeWritingPolicy.resolve(block: block, visibleText: display,
            interfaceDirection: interfaceDirection, detectedTextDirection: detected)
        paragraph.baseWritingDirection = decision.baseWritingDirection == .rightToLeft ? .rightToLeft : .leftToRight
        switch decision.alignment {
        case .natural: paragraph.alignment = .natural
        case .left: paragraph.alignment = .left
        case .center: paragraph.alignment = .center
        case .right: paragraph.alignment = .right
        case .justified: paragraph.alignment = .justified
        }
        paragraph.lineSpacing = 3
        let base = UIFont.preferredFont(forTextStyle: block.type == "heading" ? .title2 : .body)
        let result = NSMutableAttributedString(string: display, attributes: [
            .font: base, .foregroundColor: UIColor.label, .paragraphStyle: paragraph])
        guard projection.isEditable else { return result }
        for run in projection.runs {
            var traits: UIFontDescriptor.SymbolicTraits = []
            if run.traits.contains(.bold) { traits.insert(.traitBold) }
            if run.traits.contains(.italic) { traits.insert(.traitItalic) }
            var font = base
            if run.traits.contains(.code) { font = .monospacedSystemFont(ofSize: base.pointSize, weight: .regular) }
            if let descriptor = font.fontDescriptor.withSymbolicTraits(traits) {
                font = UIFont(descriptor: descriptor, size: base.pointSize)
            }
            result.addAttribute(.font, value: font, range: run.displayRange)
            if run.traits.contains(.strike) { result.addAttribute(.strikethroughStyle, value: NSUnderlineStyle.single.rawValue, range: run.displayRange) }
            if let link = run.link { result.addAttribute(.link, value: link, range: run.displayRange) }
        }
        return result
    }

    public func textView(_ textView: UITextView, editMenuForTextIn range: NSRange,
                         suggestedActions: [UIMenuElement]) -> UIMenu? {
        guard let input = textView as? AnyNativeTextView,
              let action = semanticAnchorAction(input, range: range) else { return nil }
        return UIMenu(children: suggestedActions + [action])
    }

    @available(iOS 26.0, *)
    public func textView(_ textView: UITextView, editMenuForTextInRanges ranges: [NSValue],
                         suggestedActions: [UIMenuElement]) -> UIMenu? {
        // A disjoint selection must never silently become its union.
        guard ranges.count == 1 else { return nil }
        return self.textView(textView, editMenuForTextIn: ranges[0].rangeValue,
                             suggestedActions: suggestedActions)
    }

    private func semanticAnchorAction(_ input: AnyNativeTextView, range: NSRange) -> UIAction? {
        guard presentation.canMutate, !presentation.hasPendingEdits, semanticAnchorInteractionID == nil,
              presentedViewController == nil, input.window === viewIfLoaded?.window,
              input.isFirstResponder, !input.isComposingMarkedText, input.markedTextRange == nil,
              range.location != NSNotFound, range.location >= 0, range.length > 0,
              range.location <= input.textStorage.length,
              range.length <= input.textStorage.length - range.location,
              let id = input.blockID, let block = blockByID[id],
              ["paragraph", "heading", "list_item", "check_list_item", "quote"].contains(block.type),
              presentation.projection(for: block).display.utf8.elementsEqual(input.textStorage.string.utf8) else {
            return nil
        }
        return UIAction(title: PinkhaSemanticAnchorUI.text(.create), image: UIImage(systemName: "pin"),
                        identifier: .init("pinkha.semanticAnchor.capture")) { [weak self, weak input] _ in
            guard let self, let input else { return }
            self.prepareSemanticAnchor(input, range: range)
        }
    }

    private func prepareSemanticAnchor(_ input: AnyNativeTextView, range: NSRange) {
        guard semanticAnchorInteractionID == nil, presentedViewController == nil,
              input.isFirstResponder, input.selectedRange == range, let blockID = input.blockID else { return }
        let interactionID = UUID(), owner = presentation.mountedOwnerID
        let visibleText = input.textStorage.string
        semanticAnchorInteractionID = interactionID
        updateSelection(input)
        semanticAnchorPreparation = Task { @MainActor [weak self, weak input] in
            guard let self else { return }
            do {
                let intent = try await presentation.prepareSemanticAnchor(
                    blockID: blockID, range: range, visibleText: visibleText)
                guard let input, semanticAnchorInteractionID == interactionID,
                      presentation.mountedOwnerID == owner, input.isFirstResponder,
                      input.selectedRange == range, input.blockID == blockID,
                      input.window === viewIfLoaded?.window,
                      input.textStorage.string.utf8.elementsEqual(visibleText.utf8),
                      presentedViewController == nil, !Task.isCancelled else {
                    presentation.cancelSemanticAnchor(intent)
                    finishSemanticAnchorInteraction(interactionID)
                    return
                }
                semanticAnchorPreparation = nil
                let alert = PinkhaSemanticAnchorUI.confirmation(selectedText: intent.selectedText,
                    cancelled: { [weak self] in
                        self?.presentation.cancelSemanticAnchor(intent)
                        self?.semanticAnchorConfirmation = nil
                        self?.finishSemanticAnchorInteraction(interactionID)
                    }, willConfirm: { [weak self] in
                        self?.semanticAnchorConfirmation = nil
                    }, confirmed: { [weak self, weak input] in
                        self?.confirmSemanticAnchor(intent, input: input, visibleText: visibleText,
                                                    interactionID: interactionID)
                    })
                semanticAnchorConfirmation = alert
                present(alert, animated: true)
            } catch {
                guard semanticAnchorInteractionID == interactionID else { return }
                finishSemanticAnchorInteraction(interactionID)
                showSemanticAnchorMessage(Self.semanticAnchorMessage(error))
            }
        }
    }

    private func confirmSemanticAnchor(_ intent: AnySemanticAnchorIntent, input: AnyNativeTextView?,
                                       visibleText: String, interactionID: UUID) {
        guard semanticAnchorInteractionID == interactionID,
              presentation.mountedOwnerID == intent.owner, presentation.isMounted,
              let input, input.blockID == intent.blockID, input.window === viewIfLoaded?.window,
              input.textStorage.string.utf8.elementsEqual(visibleText.utf8) else {
            presentation.cancelSemanticAnchor(intent)
            finishSemanticAnchorInteraction(interactionID)
            return
        }
        // This task is not the preview task. Once a confirmed native write starts
        // it owns its receipt/readback and is never replaced by a retry.
        Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                _ = try await presentation.applySemanticAnchor(intent)
                guard semanticAnchorInteractionID == interactionID,
                      presentation.mountedOwnerID == intent.owner else { return }
                finishSemanticAnchorInteraction(interactionID)
                render()
                showSemanticAnchorMessage(PinkhaSemanticAnchorUI.text(.created))
            } catch {
                guard semanticAnchorInteractionID == interactionID else { return }
                finishSemanticAnchorInteraction(interactionID)
                showSemanticAnchorMessage(Self.semanticAnchorMessage(error))
            }
        }
    }

    private func finishSemanticAnchorInteraction(_ id: UUID) {
        guard semanticAnchorInteractionID == id else { return }
        semanticAnchorInteractionID = nil
        semanticAnchorPreparation = nil
    }

    fileprivate func retireSemanticAnchorInteraction() {
        semanticAnchorPreparation?.cancel()
        semanticAnchorPreparation = nil
        semanticAnchorInteractionID = nil
        let alert = semanticAnchorConfirmation
        semanticAnchorConfirmation = nil
        alert?.dismiss(animated: false)
    }

    private func showSemanticAnchorMessage(_ message: String) {
        guard presentation.isMounted, viewIfLoaded?.window != nil, presentedViewController == nil else { return }
        present(PinkhaSemanticAnchorUI.outcome(message), animated: true)
    }

    private static func semanticAnchorMessage(_ error: Error) -> String {
        if let anchor = error as? PinkhaSemanticTextAnchorError { return PinkhaSemanticAnchorUI.message(for: anchor) }
        switch error {
        case AnyHostError.invalidSelection: return PinkhaSemanticAnchorUI.text(.invalidSelection)
        case AnyHostError.changedDocument: return PinkhaSemanticAnchorUI.text(.changed)
        case AnyHostError.writeUncertain, AnyEngineError.writeUncertain:
            return PinkhaSemanticAnchorUI.text(.unconfirmed)
        case AnyHostError.sessionClosed, AnyHostError.engineRestarted, AnyEngineError.accountChanged,
             TorahAssociationRepositoryError.permissionDenied:
            return PinkhaSemanticAnchorUI.text(.unavailablePage)
        default: return PinkhaSemanticAnchorUI.text(.unavailable)
        }
    }

    public func textView(_ textView: UITextView, primaryActionFor textItem: UITextItem,
                         defaultAction: UIAction) -> UIAction? {
        guard case .link(let url) = textItem.content, PinkhaSemanticTextAnchor.isReservedMarkerURL(url) else { return defaultAction }
        return semanticAnchorNavigationAction(url)
    }

    public func textView(_ textView: UITextView, menuConfigurationFor textItem: UITextItem,
                         defaultMenu: UIMenu) -> UITextItem.MenuConfiguration? {
        guard case .link(let url) = textItem.content, PinkhaSemanticTextAnchor.isReservedMarkerURL(url) else {
            return UITextItem.MenuConfiguration(menu: defaultMenu)
        }
        let navigate = semanticAnchorNavigationAction(url)
        guard let anchor = try? PinkhaSemanticTextAnchor(markerURL: url),
              anchor.belongsTo(spaceID: presentation.workspace.spaceID, objectID: presentation.objectID) else {
            return UITextItem.MenuConfiguration(menu: UIMenu(children: [navigate]))
        }
        let copy = UIAction(title: PinkhaSemanticAnchorUI.text(.copyLink),
                            image: UIImage(systemName: "link")) { _ in
            UIPasteboard.general.url = url
        }
        return UITextItem.MenuConfiguration(menu: UIMenu(children: [navigate, copy]))
    }

    private func semanticAnchorNavigationAction(_ url: URL) -> UIAction {
        UIAction(title: PinkhaSemanticAnchorUI.text(.reveal),
                 image: UIImage(systemName: "scope")) { [weak self] _ in
            guard let self else { return }
            Task { @MainActor [weak self] in
                guard let self else { return }
                do {
                    let anchor = try PinkhaSemanticTextAnchor(markerURL: url)
                    let resolution = try await presentation.revealSemanticAnchor(anchor)
                    switch resolution {
                    case .resolved: render()
                    case .missing: showSemanticAnchorMessage(PinkhaSemanticAnchorUI.text(.missing))
                    case .ambiguous: showSemanticAnchorMessage(PinkhaSemanticAnchorUI.text(.ambiguous))
                    }
                } catch { showSemanticAnchorMessage(Self.semanticAnchorMessage(error)) }
            }
        }
    }

    public func textViewShouldBeginEditing(_ textView: UITextView) -> Bool { presentation.canMutate }

    public func textViewDidBeginEditing(_ textView: UITextView) {
        focus.userInteraction()
        activeTextView = textView
        updateSelection(textView)
    }

    public func textViewDidChangeSelection(_ textView: UITextView) {
        guard !rendering else { return }
        focus.userInteraction()
        updateSelection(textView)
    }

    public func textViewDidChange(_ textView: UITextView) {
        guard !rendering, let textView = textView as? AnyNativeTextView else { return }
        if textView.isComposingMarkedText {
            textView.captureMarkedBuffer()
            textView.finishCompositionIfNeeded()
            table.beginUpdates(); table.endUpdates()
        }
    }

    public func textViewDidEndEditing(_ textView: UITextView) {
        (textView as? AnyNativeTextView)?.finishCompositionIfNeeded()
        Task { [weak presentation] in await presentation?.flush() }
    }

    private func updateSelection(_ textView: UITextView) {
        guard let textView = textView as? AnyNativeTextView, let id = textView.blockID else { return }
        presentation.select(blockIDs: [id], focusedBlockID: id, range: textView.selectedRange)
        observeSemanticAnchors()
    }

    public func textView(_ textView: UITextView, shouldChangeTextIn range: NSRange,
                         replacementText text: String) -> Bool {
        guard !rendering, let textView = textView as? AnyNativeTextView,
              let id = textView.blockID, let block = blockByID[id] else { return false }
        focus.userInteraction()
        if textView.isComposingMarkedText {
            return textView.preflightReplacing(range, with: text)
        }
        do {
            let before = presentation.source(for: block)
            let projection = presentation.projection(for: block)
            let after = try projection.replacing(displayRange: range, withLiteral: text)
            let nextSelection = NSRange(location: range.location + text.utf16.count, length: 0)
            let previousSelection = textView.selectedRange
            try applyText(after, block: block, selection: nextSelection, textView: textView)
            textView.editHistory.registerUndo(withTarget: self) { owner in
                owner.restoreText(before, blockID: id, selection: previousSelection, inverse: after,
                                  inverseSelection: nextSelection)
            }
            textView.editHistory.setActionName(AnyUIErrorText.text("עריכת טקסט", "Edit text"))
        } catch { presentation.message = AnyUIErrorText.describe(error) }
        return false
    }

    private func applyText(_ source: String, block: AnyEditorBlock, selection: NSRange,
                           textView: AnyNativeTextView) throws {
        try presentation.changeText(blockID: block.id, source: source, displaySelection: selection,
                                    renderedBlock: block)
        rendering = true
        textView.attributedText = attributed(block.type == "code" ? AnyInlineMarkdown(literal: source) :
                                               AnyInlineMarkdown(source), block: block)
        textView.selectedRange = selection
        rendering = false
        if let path = dataSource.indexPath(for: block.id),
           let cell = table.cellForRow(at: path) as? AnyNativeBlockCell { cell.renderedSource = source }
        table.beginUpdates(); table.endUpdates()
    }

    private func restoreText(_ source: String, blockID: String, selection: NSRange,
                             inverse: String, inverseSelection: NSRange) {
        guard let block = blockByID[blockID], let path = dataSource.indexPath(for: blockID),
              let cell = table.cellForRow(at: path) as? AnyNativeBlockCell else { return }
        do {
            try applyText(source, block: block, selection: selection, textView: cell.textView)
            cell.textView.editHistory.registerUndo(withTarget: self) { owner in
                owner.restoreText(inverse, blockID: blockID, selection: inverseSelection,
                                  inverse: source, inverseSelection: selection)
            }
        } catch { presentation.message = AnyUIErrorText.describe(error) }
    }

    private func toolbar(for textView: AnyNativeTextView) -> UIToolbar {
        let toolbar = UIToolbar()
        func item(_ title: String, allowsCompositionCompletion: Bool = false,
                  _ body: @escaping @MainActor () -> Void) -> UIBarButtonItem {
            UIBarButtonItem(title: title, primaryAction: UIAction { [weak textView] _ in
                guard allowsCompositionCompletion || textView?.isComposingMarkedText != true else { return }
                body()
            })
        }
        let done = item(AnyUIErrorText.text("סיום", "Done"), allowsCompositionCompletion: true) { [weak self, weak textView] in
            self?.focus.cancel(); textView?.resignFirstResponder()
        }
        done.accessibilityIdentifier = "any-native-editor-done"
        let anchor = item(PinkhaSemanticAnchorUI.text(.title)) { [weak self, weak textView] in
            guard let self, let textView,
                  self.semanticAnchorAction(textView, range: textView.selectedRange) != nil else { return }
            self.prepareSemanticAnchor(textView, range: textView.selectedRange)
        }
        anchor.accessibilityIdentifier = "pinkha.semanticAnchor.capture"
        toolbar.items = [
            item("B") { [weak self, weak textView] in self?.format(.bold, textView: textView) },
            item("I") { [weak self, weak textView] in self?.format(.italic, textView: textView) },
            item("S") { [weak self, weak textView] in self?.format(.strike, textView: textView) },
            item("</>") { [weak self, weak textView] in self?.format(.code, textView: textView) },
            anchor,
            .flexibleSpace(),
            item("↶") { [weak textView] in textView?.editHistory.undo() },
            item("↷") { [weak textView] in textView?.editHistory.redo() },
            done
        ]
        toolbar.sizeToFit()
        return toolbar
    }

    private func format(_ trait: AnyInlineTraits, textView: AnyNativeTextView?) {
        guard let textView, !textView.isComposingMarkedText,
              let id = textView.blockID, let block = blockByID[id] else { return }
        focus.cancel()
        do {
            let before = presentation.source(for: block), selection = textView.selectedRange
            let after = try presentation.projection(for: block).toggling(trait, to: selection)
            try applyText(after, block: block, selection: selection, textView: textView)
            textView.editHistory.registerUndo(withTarget: self) { owner in
                owner.restoreText(before, blockID: id, selection: selection, inverse: after, inverseSelection: selection)
            }
        } catch { presentation.message = AnyUIErrorText.describe(error) }
    }

    public func tableView(_ tableView: UITableView, contextMenuConfigurationForRowAt indexPath: IndexPath,
                          point: CGPoint) -> UIContextMenuConfiguration? {
        guard let id = dataSource.itemIdentifier(for: indexPath) else { return nil }
        return UIContextMenuConfiguration(identifier: id as NSString, previewProvider: nil) { [weak self] _ in
            guard let self else { return UIMenu() }
            return UIMenu(children: [
                UIAction(title: AnyUIErrorText.text("מקורות לבלוק", "Block sources"), image: UIImage(systemName: "books.vertical")) { [weak presentation] _ in
                    presentation?.torah.presentSearch(scope: .block(id))
                },
                UIAction(title: AnyUIErrorText.text("בחירת בלוק", "Select block"), image: UIImage(systemName: "checkmark.circle")) { [weak presentation] _ in
                    guard let presentation else { return }
                    var selection = presentation.selectedBlockIDs
                    if selection.contains(id) { selection.removeAll { $0 == id } } else { selection.append(id) }
                    let order = presentation.read?.snapshot.depthFirstIDs ?? []
                    selection.sort { (order.firstIndex(of: $0) ?? 0) < (order.firstIndex(of: $1) ?? 0) }
                    presentation.select(blockIDs: selection, focusedBlockID: nil, range: .init(location: 0, length: 0))
                },
                UIAction(title: AnyUIErrorText.text("הוספת פסקה לפני", "Add paragraph before"), image: UIImage(systemName: "plus")) { [weak presentation] _ in
                    Task { await presentation?.addParagraph(before: id) }
                }
            ])
        }
    }

    public func scrollViewWillBeginDragging(_ scrollView: UIScrollView) { focus.cancel() }

    public func tableView(_ tableView: UITableView, canHandle session: any UIDropSession) -> Bool {
        session.hasItemsConforming(toTypeIdentifiers: [UTType.torahSource.identifier])
    }

    public func tableView(_ tableView: UITableView, dropSessionDidUpdate session: any UIDropSession,
                          withDestinationIndexPath destinationIndexPath: IndexPath?) -> UITableViewDropProposal {
        UITableViewDropProposal(operation: presentation.canMutate ? .copy : .forbidden,
                                intent: .insertAtDestinationIndexPath)
    }

    public func tableView(_ tableView: UITableView, performDropWith coordinator: any UITableViewDropCoordinator) {
        guard presentation.canMutate else { return }
        let target = coordinator.destinationIndexPath.flatMap { dataSource.itemIdentifier(for: $0) }
        // Capture the original document/action epoch before asynchronous decoding.
        let action = presentation.torah.makeExternalDropInsertionAction(targetBlockId: target)
        TorahSourceTransfer.decode(coordinator.items.map { $0.dragItem.itemProvider }) { transfer in
            Task { @MainActor in await action(transfer) }
        }
    }

    public func presentHanlin() {
        focus.cancel()
        Task { [weak self] in
            guard let self else { return }
            await presentation.flush()
            guard !presentation.hasPendingEdits else {
                presentation.message = AnyUIErrorText.changedDocument; return
            }
            do {
                let authority = try AnyHanlinCreationAuthority(client: presentation.client,
                                                               workspace: presentation.workspace)
                let creation = try AnyHanlinCreationServices(creator: presentation.objects,
                                                             authority: authority)
                let chat = try AnyHanlinPresentation.present(from: self, native: presentation.nativeSession,
                    documents: presentation.documents, sourceOwner: presentation,
                    conversationID: conversationID, creation: creation)
                presentation.installPresentationLifecycle(revoke: { [weak chat] in chat?.revoke() },
                                                           drain: { [weak chat] in await chat?.drain() })
            } catch { presentation.message = AnyUIErrorText.describe(error) }
        }
    }
}

extension AnyDocumentPresentation: AnyHanlinSourcePresentationOwner {
    public func currentScope() throws -> AnyHanlinPresentationScope {
        guard isMounted, lifetime.isActive, !hasPendingEdits,
              let surface, surface.isForegroundMounted, let read else { throw HanlinHostError.staleContext }
        return .init(accountID: workspace.accountID, spaceID: workspace.spaceID,
                     sceneID: surface.sceneID, ownerID: mountedOwnerID,
                     document: read.snapshot, selection: selectedBlockIDs)
    }

    public func install(session: HanlinHostSession, invalidate: @escaping @Sendable () -> Void) throws {
        _ = try currentScope()
        guard session.context.namespace.account == workspace.accountID,
              session.context.namespace.space == workspace.spaceID else { throw HanlinHostError.staleContext }
        try installSourceInvalidator(invalidate)
    }

    public func validateMounted(_ destination: HanlinHostDestination) throws {
        _ = try currentScope()
        guard destination.context.namespace.account == workspace.accountID,
              destination.context.namespace.space == workspace.spaceID,
              destination.objectReference == objectID, let surface else { throw HanlinHostError.staleContext }
        if let block = destination.blockReference {
            guard read?.snapshot.depthFirstIDs.contains(block) == true else { throw HanlinHostError.staleContext }
            surface.reveal(blockID: block, selection: nil)
            guard surface.isBlockVisible(block) else { throw HanlinHostError.staleContext }
        }
    }

    public func presentHanlin() {
        (surface as? AnyNativeEditorController)?.presentHanlin()
    }
}

/// UIKit owns the marked range. The callbacks reserve/retain the original
/// source and preflight bounded visible buffers; they never replace attributed
/// text inside a composition. Internal visibility permits actual UIKit tests.
@MainActor
final class AnyNativeTextView: UITextView {
    var blockID: String?
    let editHistory = UndoManager()
    private(set) var isComposingMarkedText = false
    private var markedMutationDepth = 0
    private var recovering = false
    var onAttachmentReadiness: (() -> Void)?
    override func didMoveToWindow() {
        super.didMoveToWindow()
        if window != nil { onAttachmentReadiness?() }
    }
    var onMarkedBegin: ((AnyNativeTextView) -> Bool)?
    var onMarkedProposal: ((AnyNativeTextView, String, NSRange) -> Bool)?
    var onMarkedChanged: ((AnyNativeTextView) -> Void)?
    var onMarkedEnd: ((AnyNativeTextView, Bool) -> Void)?
    override var undoManager: UndoManager? { isComposingMarkedText ? nil : editHistory }

    override func setMarkedText(_ markedText: String?, selectedRange: NSRange) {
        if !isComposingMarkedText {
            guard markedText != nil else { super.setMarkedText(markedText, selectedRange: selectedRange); return }
            isComposingMarkedText = true
            guard onMarkedBegin?(self) ?? true else { isComposingMarkedText = false; return }
        }
        let range = markedTextRange.map {
            NSRange(location: offset(from: beginningOfDocument, to: $0.start),
                    length: offset(from: $0.start, to: $0.end))
        } ?? self.selectedRange
        let replacement = markedText ?? ""
        let relative = selectedRange.location == NSNotFound
            ? NSRange(location: replacement.utf16.count, length: 0) : selectedRange
        guard relative.location >= 0, relative.length >= 0,
              relative.location <= replacement.utf16.count,
              relative.length <= replacement.utf16.count - relative.location,
              preflightReplacing(range, with: replacement,
                  selection: NSRange(location: range.location + relative.location, length: relative.length)) else {
            if markedTextRange == nil { endComposition(allowSaving: false) }
            return
        }
        markedMutationDepth += 1
        super.setMarkedText(markedText, selectedRange: selectedRange)
        markedMutationDepth -= 1
        captureMarkedBuffer(); finishCompositionIfNeeded()
    }

    override func unmarkText() {
        markedMutationDepth += 1
        super.unmarkText()
        markedMutationDepth -= 1
        captureMarkedBuffer(); finishCompositionIfNeeded()
    }

    override func insertText(_ text: String) {
        guard isComposingMarkedText else { super.insertText(text); return }
        markedMutationDepth += 1
        super.insertText(text)
        markedMutationDepth -= 1
        captureMarkedBuffer(); finishCompositionIfNeeded()
    }

    override func deleteBackward() {
        guard isComposingMarkedText else { super.deleteBackward(); return }
        markedMutationDepth += 1
        super.deleteBackward()
        markedMutationDepth -= 1
        captureMarkedBuffer(); finishCompositionIfNeeded()
    }

    override func resignFirstResponder() -> Bool {
        if isComposingMarkedText { unmarkText() }
        return super.resignFirstResponder()
    }

    func preflightReplacing(_ range: NSRange, with replacement: String,
                            selection: NSRange? = nil) -> Bool {
        let current = self.text ?? ""
        guard range.location >= 0, range.length >= 0, range.location <= current.utf16.count,
              range.length <= current.utf16.count - range.location else { return false }
        let next = (current as NSString).replacingCharacters(in: range, with: replacement)
        let selection = selection ?? NSRange(location: range.location + replacement.utf16.count, length: 0)
        return onMarkedProposal?(self, next, selection) ?? true
    }

    func captureMarkedBuffer() {
        guard isComposingMarkedText else { return }
        onMarkedChanged?(self)
    }

    func finishCompositionIfNeeded() {
        guard isComposingMarkedText, markedMutationDepth == 0, markedTextRange == nil else { return }
        endComposition(allowSaving: !recovering)
    }

    func captureCompositionForRecovery() {
        guard isComposingMarkedText else { return }
        recovering = true
        captureMarkedBuffer()
        markedMutationDepth += 1
        super.unmarkText()
        markedMutationDepth -= 1
        endComposition(allowSaving: false)
        recovering = false
    }

    private func endComposition(allowSaving: Bool) {
        guard isComposingMarkedText else { return }
        captureMarkedBuffer()
        isComposingMarkedText = false
        onMarkedEnd?(self, allowSaving)
    }
}

@MainActor
private final class AnyNativeBlockCell: UITableViewCell {
    let textView = AnyNativeTextView()
    let marker = UILabel()
    let sourceButton = UIButton(type: .system)
    let stateLabel = UILabel()
    var sourceAction: (() -> Void)?
    var renderedSource: String?
    var renderedHistoryEpoch: UInt64?
    var renderedNativeStyle: PinkhaAnyEngine.AnyJSON?
    var indent: NSLayoutConstraint!

    override init(style: UITableViewCell.CellStyle, reuseIdentifier: String?) {
        super.init(style: style, reuseIdentifier: reuseIdentifier)
        selectionStyle = .none
        textView.isScrollEnabled = false
        textView.backgroundColor = .clear
        textView.textContainerInset = UIEdgeInsets(top: 7, left: 0, bottom: 7, right: 0)
        textView.adjustsFontForContentSizeCategory = true
        textView.autocorrectionType = .default
        marker.font = .preferredFont(forTextStyle: .body)
        marker.textColor = .secondaryLabel
        marker.setContentHuggingPriority(.required, for: .horizontal)
        sourceButton.titleLabel?.font = .preferredFont(forTextStyle: .caption1)
        sourceButton.contentHorizontalAlignment = .leading
        sourceButton.addAction(UIAction { [weak self] _ in self?.sourceAction?() }, for: .touchUpInside)
        stateLabel.font = .preferredFont(forTextStyle: .caption2)
        stateLabel.textColor = .secondaryLabel; stateLabel.numberOfLines = 0
        let row = UIStackView(arrangedSubviews: [marker, textView])
        row.axis = .horizontal; row.spacing = 8; row.alignment = .top
        let stack = UIStackView(arrangedSubviews: [row, sourceButton, stateLabel])
        stack.axis = .vertical; stack.spacing = 2; stack.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(stack)
        indent = stack.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 12)
        NSLayoutConstraint.activate([indent, stack.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -12),
            stack.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 4),
            stack.bottomAnchor.constraint(equalTo: contentView.bottomAnchor, constant: -4)])
    }
    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
    override func prepareForReuse() {
        super.prepareForReuse()
        textView.editHistory.removeAllActions()
        textView.onAttachmentReadiness = nil
        textView.blockID = nil; renderedSource = nil; renderedHistoryEpoch = nil; renderedNativeStyle = nil; sourceAction = nil
    }
}
#endif
