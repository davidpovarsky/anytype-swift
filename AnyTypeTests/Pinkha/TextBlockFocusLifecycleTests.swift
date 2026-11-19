import Combine
import Services
import Testing
import UIKit
@testable import Anytype

@Suite("Native text block focus lifetime", .serialized)
@MainActor
struct TextBlockFocusLifecycleTests {
    @Test("A newly inserted row uses its collection's actual editing state for initial focus",
          arguments: [false, true])
    func insertedCellUsesCurrentEditingBeforeFocus(editing: Bool) async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let collection = TextBlockFocusCellCollection(
            configuration: cellConfiguration(configuration("inserted", cursor: cursor, subjects: subjects, initial: .end)),
            locked: false, editing: editing
        )
        fixture.attach(collection.view)
        await collection.display()
        let cell = try #require(collection.cell)
        let row = try #require(collection.row)
        #expect(cell.configurationState.isEditing == editing)
        #expect(row.textView.textView.isUserInteractionEnabled == editing)
        await finishMainQueueTurn()

        if editing {
            try #require(row.textView.textView.isFirstResponder,
                         "First insertion must deliver initial native focus without a second request")
            #expect(row.textView.textView.selectedRange == NSRange(
                location: row.textView.textView.text.utf16.count, length: 0
            ))
        } else {
            try #require(!row.textView.textView.isFirstResponder)
            collection.view.isEditing = true
            collection.view.layoutIfNeeded()
            await finishMainQueueTurn()
            #expect(cell.configurationState.isEditing)
            #expect(row.textView.textView.isUserInteractionEnabled)
            #expect(!row.textView.textView.isFirstResponder,
                    "Enabling the collection must not revive an initially denied focus request")
            row.takeFocus(at: .end)
            try #require(row.textView.textView.isFirstResponder,
                         "A fresh explicit request must follow the collection's new editable state")
        }
    }

    @Test("A reused collection cell applies the new owner's lock before its one-shot focus",
          arguments: [false, true])
    func reusedCellUsesCurrentLockBeforeFocus(newLocked: Bool) async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let collection = TextBlockFocusCellCollection(
            configuration: cellConfiguration(configuration("previous", cursor: cursor, subjects: subjects)),
            locked: !newLocked
        )
        fixture.attach(collection.view)
        await collection.display()
        let previousCell = try #require(collection.cell)
        let previousRow = try #require(collection.row)
        try #require(previousCell.configurationState.isEditing,
                     "The real collection must provide editing state before row reconfiguration")
        try #require(previousRow.textView.textView.isLockedForEditing == !newLocked)
        #expect(!previousRow.textView.textView.isFirstResponder)

        await collection.reconfigure(
            cellConfiguration(configuration("next", cursor: cursor, subjects: subjects, initial: .end)),
            locked: newLocked
        )
        let currentCell = try #require(collection.cell)
        let currentRow = try #require(collection.row)
        try #require(currentCell === previousCell && currentRow === previousRow,
                     "Exercise the reused UIKit cell and content view, not a replacement fixture")
        #expect(currentCell.isLocked == newLocked)
        #expect(currentRow.textView.textView.isLockedForEditing == newLocked)
        await finishMainQueueTurn()

        if newLocked {
            #expect(!currentRow.textView.textView.isFirstResponder)
            await collection.reconfigure(
                cellConfiguration(configuration("next", cursor: cursor, subjects: subjects)), locked: false
            )
            await finishMainQueueTurn()
            #expect(!currentRow.textView.textView.isFirstResponder,
                    "A genuine new-owner denial must not revive after an unlock without fresh intent")
        } else {
            try #require(currentRow.textView.textView.isFirstResponder,
                         "The new editable row must acquire native focus without a second focus request")
            #expect(currentRow.textView.textView.selectedRange == NSRange(
                location: currentRow.textView.textView.text.utf16.count, length: 0
            ))
        }
    }

    @Test("An initial request survives detached configuration and a same-row echo")
    func initialFocusWaitsForAttachment() async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let row = TextBlockContentView(frame: .zero)
        row.update(with: editingState(editing: false))
        row.update(with: configuration("initial", cursor: cursor, subjects: subjects, initial: .end))
        // The cell applies its new state after its content configuration.
        row.update(with: editingState())
        await finishMainQueueTurn()
        #expect(row.window == nil && !row.textView.textView.isFirstResponder)
        row.update(with: configuration("initial", cursor: cursor, subjects: subjects))
        fixture.attach(row)
        await finishMainQueueTurn()

        let textView = row.textView.textView
        try #require(textView.isFirstResponder, "Attachment must deliver the original request without a manual focus repair")
        #expect(textView.selectedRange == NSRange(location: textView.text.utf16.count, length: 0))
        textView.insertText("!")
        #expect(textView.text == "abc אבג!")
    }

    @Test("An attached request waits for its actual key window")
    func pendingFocusWaitsForKeyWindow() async throws {
        let fixture = try TextBlockFocusWindow(makeKey: false)
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let row = TextBlockContentView(frame: .zero)
        row.update(with: configuration("waiting-window", cursor: cursor, subjects: subjects, initial: .end))
        fixture.attach(row)
        await finishMainQueueTurn()
        try #require(row.window === fixture.window && !fixture.window.isKeyWindow)
        #expect(!row.textView.textView.isFirstResponder)

        fixture.window.makeKeyAndVisible()
        await finishMainQueueTurn()
        #expect(row.textView.textView.isFirstResponder)
        #expect(row.textView.textView.selectedRange == NSRange(location: row.textView.textView.text.utf16.count, length: 0))
    }

    @Test("A native refusal waits for a real readiness event without a busy retry")
    func refusedFocusWaitsForWindowReadiness() async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let row = TextBlockContentView(frame: .zero)
        row.update(with: configuration("refused", cursor: cursor, subjects: subjects, initial: .end))
        let originalDelegate = row.textView.textView.delegate
        let refusal = TextBlockFocusRefusingDelegate()
        row.textView.textView.delegate = refusal
        fixture.attach(row)
        await finishMainQueueTurn()
        try #require(refusal.beginAttempts == 1 && !row.textView.textView.isFirstResponder,
                     "The native delegate must actually reject the first responder attempt")
        await finishMainQueueTurn()
        #expect(refusal.beginAttempts == 1, "A refusal cannot start a queued or timed retry loop")

        row.textView.textView.delegate = originalDelegate
        let otherWindow = try TextBlockFocusWindow()
        defer { otherWindow.close() }
        try #require(otherWindow.window.isKeyWindow && !fixture.window.isKeyWindow)
        fixture.window.makeKeyAndVisible()
        await finishMainQueueTurn()
        #expect(row.textView.textView.isFirstResponder)
        #expect(row.textView.textView.selectedRange == NSRange(location: row.textView.textView.text.utf16.count, length: 0))
    }

    @Test("A synchronous Enter handoff supersedes the deferred caret request")
    func explicitHandoffDoesNotReplayInitialCaret() async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let row = TextBlockContentView(frame: .zero)
        row.update(with: configuration("enter", cursor: cursor, subjects: subjects, initial: .beginning))
        fixture.attach(row)
        row.takeFocus(at: .end)
        try #require(row.textView.textView.isFirstResponder)
        let laterCaret = NSRange(location: 2, length: 0)
        row.textView.textView.selectedRange = laterCaret
        await finishMainQueueTurn()

        #expect(row.textView.textView.isFirstResponder)
        #expect(row.textView.textView.selectedRange == laterCaret)
    }

    @Test("Rebind, detach and editor replacement invalidate the queued request",
          arguments: ["rebind", "detach", "editorContext"])
    func staleFocusDoesNotSurviveRowLifetime(change: String) async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let keeper = TextBlockContentView(frame: .zero)
        keeper.update(with: configuration("keeper", cursor: cursor, subjects: subjects))
        fixture.attach(keeper, y: 80)
        keeper.takeFocus(at: .end)
        try #require(keeper.textView.textView.isFirstResponder)

        let original = configuration("old", cursor: cursor, subjects: subjects)
        let wrapper = EditorContentView<TextBlockContentView>(configuration: cellConfiguration(original))
        fixture.attach(wrapper, y: 240)
        let row = try #require(wrapper.subviews.compactMap { $0 as? TextBlockContentView }.first)
        cursor.focus(at: "old", position: .beginning)
        switch change {
        case "rebind":
            wrapper.configuration = cellConfiguration(configuration("replacement", cursor: cursor, subjects: subjects))
        case "detach":
            wrapper.removeFromSuperview()
            fixture.attach(wrapper, y: 240)
        case "editorContext":
            let otherSubjects = FocusSubjectsHolder()
            let otherCursor = EditorCursorManager(focusSubjectHolder: otherSubjects)
            let replacement = configuration("old", cursor: otherCursor, subjects: otherSubjects)
            #expect(original != replacement, "Context identity must reach the cell even without a new initial request")
            wrapper.configuration = cellConfiguration(replacement)
        default:
            Issue.record("Unexpected lifecycle fixture")
            return
        }
        await finishMainQueueTurn()
        #expect(keeper.textView.textView.isFirstResponder)
        #expect(!row.textView.textView.isFirstResponder)

        row.takeFocus(at: .end)
        try #require(row.textView.textView.isFirstResponder, "The current binding still accepts a fresh explicit request")
        let laterCaret = NSRange(location: 2, length: 0)
        row.textView.textView.selectedRange = laterCaret
        await finishMainQueueTurn()
        #expect(row.textView.textView.selectedRange == laterCaret)
    }

    @Test("A later focus in the same editor cancels a detached row's request", arguments: [false, true])
    func laterFocusSupersedesDetachedRequest(useNativeEditing: Bool) async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let pending = TextBlockContentView(frame: .zero)
        pending.update(with: configuration("pending", cursor: cursor, subjects: subjects, initial: .beginning))
        let selected = TextBlockContentView(frame: .zero)
        selected.update(with: configuration("selected", cursor: cursor, subjects: subjects))
        fixture.attach(selected, y: 80)
        if useNativeEditing {
            try #require(selected.textView.textView.becomeFirstResponder())
        } else {
            cursor.focus(at: "selected", position: .end)
            await finishMainQueueTurn()
        }
        try #require(selected.textView.textView.isFirstResponder)
        let laterCaret = NSRange(location: 2, length: 0)
        selected.textView.textView.selectedRange = laterCaret
        fixture.attach(pending, y: 240)
        await finishMainQueueTurn()

        #expect(selected.textView.textView.isFirstResponder)
        #expect(selected.textView.textView.selectedRange == laterCaret)
        #expect(!pending.textView.textView.isFirstResponder)
    }

    @Test("A locked or nonediting state cancels rather than postpones a request", arguments: [false, true])
    func editingDenialCancelsPendingFocus(locked: Bool) async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let row = TextBlockContentView(frame: .zero)
        row.update(with: configuration("denied", cursor: cursor, subjects: subjects, initial: .beginning))
        fixture.attach(row)
        row.update(with: editingState(editing: locked, locked: locked))
        row.update(with: editingState())
        await finishMainQueueTurn()
        #expect(!row.textView.textView.isFirstResponder)

        row.takeFocus(at: .end)
        #expect(row.textView.textView.isFirstResponder)
        #expect(row.textView.textView.selectedRange == NSRange(location: row.textView.textView.text.utf16.count, length: 0))
    }

    @Test("setFocus on the current responder never schedules a later steal")
    func focusedTextViewDoesNotReplayResponderAcquisition() async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let first = UITextView(frame: CGRect(x: 20, y: 80, width: 320, height: 100))
        let second = UITextView(frame: CGRect(x: 20, y: 240, width: 320, height: 100))
        #expect(!first.isFirstResponder && !second.isFirstResponder)
        first.text = "first"
        second.text = "second"
        fixture.controller.view.addSubview(first)
        fixture.controller.view.addSubview(second)
        try #require(first.becomeFirstResponder())
        first.setFocus(.end)
        try #require(second.becomeFirstResponder())
        await finishMainQueueTurn()

        #expect(second.isFirstResponder)
        #expect(!first.isFirstResponder)
    }

    @Test("Old cancellation and caret callbacks do not revoke a newer Enter request")
    func consumedAndNewerFocusSurviveOldCallbacks() async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let old = TextBlockContentView(frame: .zero)
        old.update(with: configuration("old", cursor: cursor, subjects: subjects))
        fixture.attach(old, y: 80)
        old.takeFocus(at: .end)
        try #require(old.textView.textView.isFirstResponder)
        let next = TextBlockContentView(frame: .zero)
        next.update(with: configuration("next", cursor: cursor, subjects: subjects))
        fixture.attach(next, y: 240)

        cursor.blockFocus = BlockFocus(id: "old", position: .beginning)
        cursor.focus(at: "next", position: .end)
        cursor.blockFocus = nil
        cursor.didChangeCursorPosition(at: "old", position: .beginning)
        await finishMainQueueTurn()
        try #require(next.textView.textView.isFirstResponder)
        #expect(!old.textView.textView.isFirstResponder)
        #expect(next.textView.textView.selectedRange == NSRange(location: next.textView.textView.text.utf16.count, length: 0))

        cursor.blockFocus = BlockFocus(id: "next", position: .beginning)
        cursor.applyCurrentFocus()
        #expect(cursor.blockFocus == nil)
        await finishMainQueueTurn()
        #expect(next.textView.textView.isFirstResponder)
        #expect(next.textView.textView.selectedRange == NSRange(location: 0, length: 0))
    }

    @Test("Equal row content still delivers a new request, while a plain echo does not")
    func requestIdentityParticipatesInCellConfigurationEquality() async throws {
        let fixture = try TextBlockFocusWindow()
        defer { fixture.close() }
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let first = configuration("same", cursor: cursor, subjects: subjects, initial: .beginning)
        let wrapper = EditorContentView<TextBlockContentView>(configuration: cellConfiguration(first))
        wrapper.frame = CGRect(x: 20, y: 80, width: 320, height: 100)
        fixture.controller.view.addSubview(wrapper)
        fixture.controller.view.layoutIfNeeded()
        let row = try #require(wrapper.subviews.compactMap { $0 as? TextBlockContentView }.first)
        await finishMainQueueTurn()
        try #require(row.textView.textView.isFirstResponder)
        row.textView.textView.selectedRange = NSRange(location: 2, length: 0)

        let second = configuration("same", cursor: cursor, subjects: subjects, initial: .beginning)
        #expect(first != second)
        wrapper.configuration = cellConfiguration(second)
        await finishMainQueueTurn()
        #expect(row.textView.textView.selectedRange == NSRange(location: 0, length: 0))

        let laterCaret = NSRange(location: 2, length: 0)
        row.textView.textView.selectedRange = laterCaret
        wrapper.configuration = cellConfiguration(configuration("same", cursor: cursor, subjects: subjects))
        await finishMainQueueTurn()
        #expect(row.textView.textView.isFirstResponder)
        #expect(row.textView.textView.selectedRange == laterCaret)
    }

    private func configuration(
        _ blockId: String,
        cursor: EditorCursorManager,
        subjects: FocusSubjectsHolder,
        initial: BlockFocusPosition? = nil
    ) -> TextBlockContentConfiguration {
        if let initial { cursor.blockFocus = BlockFocus(id: blockId, position: initial) }
        let request = cursor.consumeBlockFocus(for: blockId)
        let defaults = TextBlockContentConfiguration.empty
        let font = UIFont.systemFont(ofSize: 17)
        return TextBlockContentConfiguration(
            blockId: blockId, content: .plain("abc אבג", contentType: .text),
            attributedString: NSAttributedString(string: "abc אבג", attributes: [.font: font]),
            placeholderAttributes: [:], typingAttributes: { _ in [.font: font] },
            textContainerInsets: .zero, alignment: .left,
            isCheckable: false, isToggled: false, isChecked: false, shouldDisplayPlaceholder: false,
            initialBlockFocusPosition: request?.position, initialFocusRequestId: request?.requestId,
            focusContext: cursor, focusPublisher: subjects.focusSubject(for: blockId).eraseToAnyPublisher(),
            resetPublisher: defaults.resetPublisher, actions: defaults.actions
        )
    }

    private func cellConfiguration(_ configuration: TextBlockContentConfiguration) -> CellBlockConfiguration<TextBlockContentConfiguration> {
        CellBlockConfiguration(
            blockConfiguration: configuration, currentConfigurationState: editingState(),
            dragConfiguration: nil, styleConfiguration: nil
        )
    }

    private func editingState(editing: Bool = true, locked: Bool = false) -> UICellConfigurationState {
        var state = UICellConfigurationState(traitCollection: UITraitCollection())
        state.isEditing = editing
        state.isLocked = locked
        return state
    }

    private func finishMainQueueTurn() async {
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            DispatchQueue.main.async { continuation.resume() }
        }
    }
}

@MainActor
private final class TextBlockFocusCellCollection {
    let view: EditorCollectionView
    private var configuration: CellBlockConfiguration<TextBlockContentConfiguration>
    private var locked: Bool
    private var dataSource: UICollectionViewDiffableDataSource<Int, Int>?

    init(configuration: CellBlockConfiguration<TextBlockContentConfiguration>, locked: Bool, editing: Bool = true) {
        self.configuration = configuration
        self.locked = locked
        let layout = UICollectionViewFlowLayout()
        layout.itemSize = CGSize(width: 320, height: 80)
        view = EditorCollectionView(frame: .zero, collectionViewLayout: layout)
        view.isEditing = editing
        let registration = UICollectionView.CellRegistration<EditorViewListCell, Int> { [weak self] cell, _, _ in
            guard let self else { return }
            cell.setContentConfiguration(self.configuration, in: self.view, isMoving: false, isLocked: self.locked)
        }
        dataSource = UICollectionViewDiffableDataSource<Int, Int>(collectionView: view) { collectionView, indexPath, item in
            collectionView.dequeueConfiguredReusableCell(using: registration, for: indexPath, item: item)
        }
    }

    var cell: EditorViewListCell? {
        view.cellForItem(at: IndexPath(item: 0, section: 0)) as? EditorViewListCell
    }

    var row: TextBlockContentView? {
        func find(in view: UIView) -> TextBlockContentView? {
            if let row = view as? TextBlockContentView { return row }
            for child in view.subviews {
                if let row = find(in: child) { return row }
            }
            return nil
        }
        return cell.flatMap { find(in: $0) }
    }

    func display() async {
        var snapshot = NSDiffableDataSourceSnapshot<Int, Int>()
        snapshot.appendSections([0])
        snapshot.appendItems([0])
        await apply(snapshot)
    }

    func reconfigure(_ configuration: CellBlockConfiguration<TextBlockContentConfiguration>, locked: Bool) async {
        self.configuration = configuration
        self.locked = locked
        guard var snapshot = dataSource?.snapshot() else { return }
        snapshot.reconfigureItems([0])
        await apply(snapshot)
    }

    private func apply(_ snapshot: NSDiffableDataSourceSnapshot<Int, Int>) async {
        guard let dataSource else { return }
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            dataSource.apply(snapshot, animatingDifferences: false) { continuation.resume() }
        }
        view.layoutIfNeeded()
    }
}

@MainActor
private final class TextBlockFocusWindow {
    let window: UIWindow
    let controller = UIViewController()

    init(makeKey: Bool = true) throws {
        let scene = try #require(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
            .first { $0.activationState == .foregroundActive })
        window = UIWindow(windowScene: scene)
        window.frame = CGRect(x: 0, y: 0, width: 390, height: 844)
        window.rootViewController = controller
        if makeKey {
            window.makeKeyAndVisible()
        } else {
            window.isHidden = false
        }
        controller.view.layoutIfNeeded()
    }

    func attach(_ row: UIView, y: CGFloat = 80) {
        row.frame = CGRect(x: 20, y: y, width: 320, height: 100)
        controller.view.addSubview(row)
        controller.view.layoutIfNeeded()
    }

    func close() {
        window.endEditing(true)
        window.isHidden = true
    }
}

@MainActor
private final class TextBlockFocusRefusingDelegate: NSObject, UITextViewDelegate {
    private(set) var beginAttempts = 0

    func textViewShouldBeginEditing(_ textView: UITextView) -> Bool {
        beginAttempts += 1
        return false
    }
}
