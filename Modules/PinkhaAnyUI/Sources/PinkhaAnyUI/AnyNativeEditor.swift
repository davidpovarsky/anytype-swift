#if canImport(UIKit)
import Foundation
import UIKit
import SwiftUI
import UniformTypeIdentifiers
import NaturalLanguage
import PinkhaKit
import PinkhaAnyHost
import PinkhaAnyEngine
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
        guard let path = dataSource.indexPath(for: blockID) else { return }
        table.scrollToRow(at: path, at: .middle, animated: false)
        table.layoutIfNeeded()
        if let selection, let cell = table.cellForRow(at: path) as? AnyNativeBlockCell,
           selection.location >= 0, NSMaxRange(selection) <= cell.textView.text.utf16.count {
            cell.textView.selectedRange = selection
            if cell.textView.isEditable { cell.textView.becomeFirstResponder() }
        }
    }

    public func dismissKeyboard() { view.endEditing(true) }

    public func render() {
        guard isViewLoaded, dataSource != nil else { return }
        let blocks = presentation.orderedBlocks
        blockByID = Dictionary(uniqueKeysWithValues: blocks.map { ($0.id, $0) })
        let ids = blocks.map(\.id)
        if ids != previousIDs {
            let firstResponderID = (activeTextView as? AnyNativeTextView)?.blockID
            let selection = activeTextView?.selectedRange
            let wasFirstResponder = activeTextView?.isFirstResponder == true
            var snapshot = NSDiffableDataSourceSnapshot<Int, String>()
            snapshot.appendSections([0]); snapshot.appendItems(ids, toSection: 0)
            previousIDs = ids
            dataSource.apply(snapshot, animatingDifferences: false) { [weak self] in
                guard let self else { return }
                self.configureVisibleCells()
                if wasFirstResponder, let id = firstResponderID, let path = self.dataSource.indexPath(for: id),
                   let cell = self.table.cellForRow(at: path) as? AnyNativeBlockCell {
                    if let selection, NSMaxRange(selection) <= cell.textView.text.utf16.count {
                        cell.textView.selectedRange = selection
                    }
                    cell.textView.becomeFirstResponder()
                }
            }
        } else { configureVisibleCells() }
    }

    private func configureVisibleCells() {
        for cell in table.visibleCells {
            guard let cell = cell as? AnyNativeBlockCell, let id = cell.textView.blockID,
                  let block = blockByID[id] else { continue }
            configure(cell, block: block)
        }
        table.beginUpdates(); table.endUpdates()
    }

    private func configure(_ cell: AnyNativeBlockCell, block: AnyEditorBlock) {
        let source = presentation.source(for: block)
        let projection = presentation.projection(for: block)
        let supported = ["paragraph", "heading", "list_item", "check_list_item", "code", "quote"].contains(block.type)
        cell.textView.blockID = block.id
        let historyEpoch = presentation.textHistoryEpochs[block.id, default: 0]
        if cell.renderedHistoryEpoch != historyEpoch { cell.textView.editHistory.removeAllActions() }
        cell.renderedHistoryEpoch = historyEpoch
        cell.textView.delegate = self
        cell.textView.accessibilityIdentifier = "any-native-block-" + block.id
        cell.textView.isEditable = supported && projection.isEditable && presentation.canMutate
        cell.textView.isSelectable = true
        cell.textView.inputAccessoryView = toolbar(for: cell.textView)
        let label = presentation.torah.linkedAssociationLabel(blockId: block.id)
        cell.sourceButton.isHidden = label == nil
        cell.sourceButton.setTitle(label, for: .normal)
        cell.sourceAction = { [weak presentation] in presentation?.torah.openLinkedAssociations(blockId: block.id) }
        cell.stateLabel.isHidden = supported && projection.isEditable
        cell.stateLabel.text = supported ? AnyUIErrorText.text("תוכן זה מוצג לקריאה; העיצוב המקורי נשמר.",
            "This content is read-only; its original formatting is preserved.") :
            AnyUIErrorText.text("סוג בלוק זה טרם ניתן לעריכה כאן.", "This block type cannot be edited here yet.")
        cell.marker.text = block.type == "quote" ? "❝" :
            (block.type == "list_item" ? "•" : (block.type == "check_list_item" ? "☐" : ""))
        let selected = presentation.selectedBlockIDs.contains(block.id)
        cell.contentView.backgroundColor = selected ? UIColor.systemBlue.withAlphaComponent(0.045) : .clear
        if cell.renderedSource != source || cell.renderedNativeStyle != block.native["style"] {
            let selection = cell.textView.selectedRange
            rendering = true
            cell.textView.attributedText = attributed(projection, block: block)
            if selection.location <= cell.textView.text.utf16.count {
                cell.textView.selectedRange = NSRange(location: selection.location,
                    length: min(selection.length, cell.textView.text.utf16.count - selection.location))
            }
            rendering = false
            cell.renderedSource = source; cell.renderedNativeStyle = block.native["style"]
        }
        var depth = 0, parent = block.parentID, seen = Set<String>()
        while !parent.isEmpty, let ancestor = blockByID[parent], seen.insert(parent).inserted {
            depth += 1; parent = ancestor.parentID
        }
        cell.indent.constant = CGFloat(min(depth, 12) * 16 + 12)
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

    public func textViewShouldBeginEditing(_ textView: UITextView) -> Bool { presentation.canMutate }

    public func textViewDidBeginEditing(_ textView: UITextView) {
        activeTextView = textView
        updateSelection(textView)
    }

    public func textViewDidChangeSelection(_ textView: UITextView) {
        guard !rendering else { return }
        updateSelection(textView)
    }

    private func updateSelection(_ textView: UITextView) {
        guard let textView = textView as? AnyNativeTextView, let id = textView.blockID else { return }
        presentation.select(blockIDs: [id], focusedBlockID: id, range: textView.selectedRange)
    }

    public func textView(_ textView: UITextView, shouldChangeTextIn range: NSRange,
                         replacementText text: String) -> Bool {
        guard !rendering, let textView = textView as? AnyNativeTextView,
              let id = textView.blockID, let block = blockByID[id] else { return false }
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
        try presentation.changeText(blockID: block.id, source: source, displaySelection: selection)
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
        func item(_ title: String, _ body: @escaping @MainActor () -> Void) -> UIBarButtonItem {
            UIBarButtonItem(title: title, primaryAction: UIAction { _ in body() })
        }
        toolbar.items = [
            item("B") { [weak self, weak textView] in self?.format(.bold, textView: textView) },
            item("I") { [weak self, weak textView] in self?.format(.italic, textView: textView) },
            item("S") { [weak self, weak textView] in self?.format(.strike, textView: textView) },
            item("</>") { [weak self, weak textView] in self?.format(.code, textView: textView) },
            .flexibleSpace(),
            item("↶") { [weak textView] in textView?.editHistory.undo() },
            item("↷") { [weak textView] in textView?.editHistory.redo() },
            item(AnyUIErrorText.text("סיום", "Done")) { [weak textView] in textView?.resignFirstResponder() }
        ]
        toolbar.sizeToFit()
        return toolbar
    }

    private func format(_ trait: AnyInlineTraits, textView: AnyNativeTextView?) {
        guard let textView, let id = textView.blockID, let block = blockByID[id] else { return }
        do {
            let before = presentation.source(for: block), selection = textView.selectedRange
            let after = try presentation.projection(for: block).adding(trait, to: selection)
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
        Task { [weak self] in
            guard let self else { return }
            await presentation.flush()
            guard !presentation.hasPendingEdits else {
                presentation.message = AnyUIErrorText.changedDocument; return
            }
            do {
                // Ordinary upstream object creation lacks the required current
                // writer commit fence. Enable creation only through the guarded
                // native capability/creator once its runtime contract is verified.
                let chat = try AnyHanlinPresentation.present(from: self, native: presentation.nativeSession,
                    documents: presentation.documents, sourceOwner: presentation,
                    conversationID: conversationID, creation: nil)
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

@MainActor
private final class AnyNativeTextView: UITextView {
    var blockID: String?
    let editHistory = UndoManager()
    override var undoManager: UndoManager? { editHistory }
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
        textView.blockID = nil; renderedSource = nil; renderedHistoryEpoch = nil; renderedNativeStyle = nil; sourceAction = nil
    }
}
#endif
