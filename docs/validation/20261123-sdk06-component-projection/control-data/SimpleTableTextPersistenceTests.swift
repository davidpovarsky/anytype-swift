import AnytypeCore
import Combine
import Services
import Testing
import UIKit
@testable import Anytype

@Suite("Table text shared persistence", .serialized)
@MainActor
struct SimpleTableTextPersistenceTests {
    @Test("A table delegate freezes text before its view is reused", .tags(.pinkhaSDK06Pending23))
    func acceptedSnapshotSurvivesViewReuse() async throws {
        let fixture = SimpleTableTextFixture()
        let entered = SimpleTableTextGate()
        let release = SimpleTableTextGate()
        fixture.nativeWrite = { _, _ in
            entered.open()
            await release.wait()
        }
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "accepted table text אבג")
        fixture.handler.textBlockActions().textViewDidChangeText(input)
        #expect(fixture.handler.hasPendingTextChanges)
        input.attributedText = NSAttributedString(string: "another row")
        await entered.wait()
        #expect(fixture.writes.map(\.value.text) == ["accepted table text אבג"])
        release.open()
        try await fixture.handler.changeText(attributedString:
            NSAttributedString(string: "accepted table text אבג").sendable())
        #expect(!fixture.handler.hasPendingTextChanges)
        #expect(fixture.writes.count == 1)
    }

    @Test("Later table drafts coalesce behind the in-flight native acknowledgement", .tags(.pinkhaSDK06Pending23))
    func laterDraftKeepsTheLatestAcceptedSnapshot() async throws {
        let fixture = SimpleTableTextFixture()
        let firstEntered = SimpleTableTextGate()
        let release = SimpleTableTextGate()
        let nextEntered = SimpleTableTextGate()
        fixture.nativeWrite = { _, value in
            if value.text == "first" {
                firstEntered.open()
                await release.wait()
            } else {
                nextEntered.open()
            }
        }
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "first")
        let actions = fixture.handler.textBlockActions()
        actions.textViewDidChangeText(input)
        await firstEntered.wait()
        input.attributedText = NSAttributedString(string: "second")
        actions.textViewDidChangeText(input)
        input.attributedText = NSAttributedString(string: "latest")
        actions.textViewDidChangeText(input)
        input.attributedText = NSAttributedString(string: "reused row")
        #expect(fixture.writes.count == 1)
        release.open()
        await nextEntered.wait()
        #expect(fixture.writes.map(\.value.text) == ["first", "latest"])
        try await fixture.handler.changeText(attributedString: NSAttributedString(string: "latest").sendable())
        #expect(!fixture.handler.hasPendingTextChanges)
    }

    @Test("Native rejection retains the table draft until an actual retry succeeds", .tags(.pinkhaSDK06Pending23))
    func nativeRejectionKeepsTheTableDirty() async throws {
        let fixture = SimpleTableTextFixture()
        let text = NSAttributedString(string: "retry table text").sendable()
        fixture.nativeWrite = { _, _ in throw SimpleTableTextFailure.rejected }
        do {
            try await fixture.handler.changeText(attributedString: text)
            Issue.record("The table must report the native rejection")
        } catch SimpleTableTextFailure.rejected {
            // Expected native failure.
        }
        #expect(fixture.handler.hasPendingTextChanges)
        fixture.nativeWrite = { _, _ in }
        try await fixture.handler.changeText(attributedString: text)
        #expect(fixture.writes.map(\.value.text) == ["retry table text", "retry table text"])
        #expect(!fixture.handler.hasPendingTextChanges)
    }

    @Test("Ending a search-owned table edit commits the captured local buffer", .tags(.pinkhaSDK06Pending23))
    func defocusCommitsTheDeferredSearchBuffer() async throws {
        let fixture = SimpleTableTextFixture()
        let entered = SimpleTableTextGate()
        let release = SimpleTableTextGate()
        fixture.nativeWrite = { _, _ in
            entered.open()
            await release.wait()
        }
        fixture.handler.accessoryState = .search
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "@local table search")
        let actions = fixture.handler.textBlockActions()
        actions.textViewDidChangeText(input)
        #expect(fixture.handler.hasPendingTextChanges)
        for _ in 0..<10 { await Task.yield() }
        #expect(fixture.writes.isEmpty)
        actions.textViewDidEndEditing(input)
        input.attributedText = NSAttributedString(string: "reused after defocus")
        await entered.wait()
        #expect(fixture.writes.map(\.value.text) == ["@local table search"])
        release.open()
        try await fixture.handler.changeText(attributedString:
            NSAttributedString(string: "@local table search").sendable())
        #expect(!fixture.handler.hasPendingTextChanges)
    }

    @Test("Rebinding a nonforking table handler retires the previous row draft", .tags(.pinkhaSDK06Pending23))
    func rowRebindCannotWriteIntoTheNewOwner() async throws {
        let fixture = SimpleTableTextFixture()
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "old private row")
        fixture.handler.textBlockActions().textViewDidChangeText(input)
        #expect(fixture.handler.hasPendingTextChanges)
        let replacement = SimpleTableTextFixture.info(id: "new-table-cell", text: "")
        fixture.container.getReturnInfo[replacement.id] = replacement
        fixture.handler.info = replacement
        #expect(!fixture.handler.hasPendingTextChanges)
        try await fixture.handler.changeText(attributedString: NSAttributedString(string: "new row").sendable())
        #expect(fixture.writes.map(\.blockId) == ["new-table-cell"])
        #expect(fixture.writes.map(\.value.text) == ["new row"])
        #expect(!fixture.handler.hasPendingTextChanges)
    }

    @Test("A table structural key waits for the pending text acknowledgement", .tags(.pinkhaSDK06Pending23))
    func structuralKeyWaitsForAcceptedText() async throws {
        let entered = SimpleTableTextGate()
        let release = SimpleTableTextGate()
        let keyExecuted = SimpleTableTextGate()
        var events: [String] = []
        let fixture = SimpleTableTextFixture(onKeyboardAction: {
            events.append("keyboard")
            keyExecuted.open()
        })
        fixture.nativeWrite = { _, _ in
            events.append("native-start")
            entered.open()
            await release.wait()
            events.append("native-ack")
        }
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "before table key")
        let actions = fixture.handler.textBlockActions()
        actions.textViewDidChangeText(input)
        await entered.wait()
        actions.handleKeyboardAction(.delete, input)
        #expect(events == ["native-start"])
        release.open()
        await keyExecuted.wait()
        #expect(events == ["native-start", "native-ack", "keyboard"])
        #expect(fixture.writes.count == 1)
        #expect(!fixture.handler.hasPendingTextChanges)
    }

    @Test("Explicit replacements claim dirty ownership before publishing their live value",
          .tags(.pinkhaSDK06Pending23), arguments: [false, true])
    func replacementClaimsPendingOwnershipBeforePublication(asyncEntry: Bool) async throws {
        let fixture = SimpleTableTextFixture()
        let entered = SimpleTableTextGate()
        let release = SimpleTableTextGate()
        fixture.nativeWrite = { _, _ in entered.open(); await release.wait() }
        var pendingAtPublication: [Bool] = []
        var publishedText: [String] = []
        let subscription = fixture.handler.resetSubject.sink { value in
            pendingAtPublication.append(fixture.handler.hasPendingTextChanges)
            publishedText.append(value?.string ?? "<model refresh>")
        }
        let replacement = NSAttributedString(string: "explicit replacement")
        let writer: Task<Void, any Error>?
        if asyncEntry {
            writer = Task { try await fixture.handler.setNewText(attributedString: replacement.sendable()) }
        } else {
            writer = nil
            fixture.handler.updateTextForLinkToUrl(
                newText: replacement, range: .zero, originalText: NSAttributedString(string: "before"))
            #expect(fixture.handler.hasPendingTextChanges)
            #expect(pendingAtPublication == [true], "The synchronous callback must accept the edit in this turn")
        }
        await entered.wait()
        #expect(pendingAtPublication == [true])
        #expect(publishedText == ["explicit replacement"])
        release.open()
        if let writer { try await writer.value }
        else { try await fixture.handler.changeText(attributedString: replacement.sendable()) }
        #expect(!fixture.handler.hasPendingTextChanges)
        withExtendedLifetime(subscription) {}
    }

    @Test("Markdown styling publishes synchronously and joins the same native writer", .tags(.pinkhaSDK06Pending23))
    func markdownStyleWaitsForEarlierNativeWrite() async throws {
        let markdown = SimpleTableMarkdownListener()
        let fixture = SimpleTableTextFixture(markdownListener: markdown)
        let entered = SimpleTableTextGate()
        let release = SimpleTableTextGate()
        fixture.nativeWrite = { _, value in
            if value.text == "before style" { entered.open(); await release.wait() }
        }
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "before style")
        let actions = fixture.handler.textBlockActions()
        actions.textViewDidChangeText(input)
        await entered.wait()
        let styled = NSAttributedString(string: "styled text")
        fixture.markupChanger.setMarkupStubReturnString = styled
        markdown.change = .addStyle(
            .bold, text: input.attributedText, range: NSRange(location: 0, length: 4),
            focusRange: NSRange(location: styled.length, length: 0))
        var pendingAtPublication: [Bool] = []
        let subscription = fixture.handler.resetSubject.sink { value in
            pendingAtPublication.append(fixture.handler.hasPendingTextChanges)
            if let value { input.attributedText = value }
        }
        #expect(!actions.textViewShouldReplaceText(input, " ", NSRange(location: input.attributedText.length, length: 0)))
        #expect(input.text == "styled text")
        #expect(pendingAtPublication == [true])
        #expect(fixture.markupChanger.setMarkupNumberOfCalls == 1)
        #expect(fixture.writes.map(\.value.text) == ["before style"])
        release.open()
        try await fixture.handler.changeText(attributedString: styled.sendable())
        #expect(fixture.writes.map(\.value.text) == ["before style", "styled text"])
        #expect(!fixture.handler.hasPendingTextChanges)
        withExtendedLifetime(subscription) {}
    }

    @Test("Markdown structural commands keep their captured text before subsequent typing",
          .tags(.pinkhaSDK06Pending23), arguments: [false, true])
    func markdownCommandsKeepCapturedTextBeforeLaterTyping(addBlock: Bool) async throws {
        let markdown = SimpleTableMarkdownListener()
        let fixture = SimpleTableTextFixture(markdownListener: markdown)
        fixture.service.turnIntoStub = true
        fixture.service.addStub = true
        let entered = SimpleTableTextGate()
        let release = SimpleTableTextGate()
        fixture.nativeWrite = { _, value in
            if value.text == "before command" { entered.open(); await release.wait() }
        }
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "before command")
        let actions = fixture.handler.textBlockActions()
        actions.textViewDidChangeText(input)
        await entered.wait()
        let captured = NSAttributedString(string: "command text")
        markdown.change = addBlock
            ? .addBlock(type: .divider(.line), text: captured)
            : .turnInto(.header, text: captured)
        var publications: [String] = []
        let subscription = fixture.handler.resetSubject.sink { value in
            publications.append(value?.string ?? "<model refresh>")
            if let value { input.attributedText = value }
        }
        #expect(!actions.textViewShouldReplaceText(input, " ", NSRange(location: input.attributedText.length, length: 0)))
        #expect(input.text == "command text")
        #expect(fixture.handler.hasPendingTextChanges)
        input.attributedText = NSAttributedString(string: "command text plus later typing")
        actions.textViewDidChangeText(input)
        release.open()
        try await fixture.handler.changeText(attributedString: input.attributedText.sendable())
        #expect(fixture.writes.map(\.value.text) == [
            "before command", "command text", "command text plus later typing"])
        #expect(input.text == "command text plus later typing")
        #expect(publications == ["command text"], "A late command must not publish an older snapshot")
        #expect(fixture.service.turnIntoNumberOfCalls == (addBlock ? 0 : 1))
        #expect(fixture.service.addNumberOfCalls == (addBlock ? 1 : 0))
        if addBlock { #expect(fixture.service.addTargetBlockId == "table-text-cell") }
        else { #expect(fixture.service.turnIntoBlockId == "table-text-cell") }
        #expect(!fixture.handler.hasPendingTextChanges)
        withExtendedLifetime(subscription) {}
    }

    @Test("An in-flight markdown add cannot continue after row ownership changes, even if the ID returns",
          .tags(.pinkhaSDK06Pending23), arguments: [false, true])
    func markdownAddBlockDoesNotContinueAfterOwnerRebind(returnToOriginalID: Bool) async throws {
        let markdown = SimpleTableMarkdownListener()
        let fixture = SimpleTableTextFixture(markdownListener: markdown)
        fixture.service.addStub = true
        let entered = SimpleTableTextGate()
        let release = SimpleTableTextGate()
        fixture.nativeWrite = { _, value in
            if value.text == "retired command text" { entered.open(); await release.wait() }
        }
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "---")
        markdown.change = .addBlock(type: .divider(.line), text: NSAttributedString(string: "retired command text"))
        #expect(!fixture.handler.textBlockActions().textViewShouldReplaceText(input, " ", NSRange(location: 3, length: 0)))
        await entered.wait()
        let other = SimpleTableTextFixture.info(id: "another-table-cell", text: "")
        fixture.container.getReturnInfo[other.id] = other
        fixture.handler.info = other
        if returnToOriginalID {
            fixture.handler.info = SimpleTableTextFixture.info(id: "table-text-cell", text: "")
        }
        let currentID = fixture.handler.info.id
        release.open()
        try await fixture.handler.changeText(attributedString: NSAttributedString(string: "current owner text").sendable())
        #expect(fixture.service.addNumberOfCalls == 0)
        #expect(fixture.writes.map(\.blockId) == ["table-text-cell", currentID])
        #expect(fixture.writes.map(\.value.text) == ["retired command text", "current owner text"])
        #expect(!fixture.handler.hasPendingTextChanges)
    }

    @Test("A queued markdown type change is retired before it can touch a newly bound row", .tags(.pinkhaSDK06Pending23))
    func queuedMarkdownCommandIsRetiredWhenRowChanges() async throws {
        let markdown = SimpleTableMarkdownListener()
        let fixture = SimpleTableTextFixture(markdownListener: markdown)
        fixture.service.turnIntoStub = true
        let entered = SimpleTableTextGate()
        let release = SimpleTableTextGate()
        fixture.nativeWrite = { _, value in
            if value.text == "old in flight" { entered.open(); await release.wait() }
        }
        let input = UITextView()
        input.attributedText = NSAttributedString(string: "old in flight")
        let actions = fixture.handler.textBlockActions()
        actions.textViewDidChangeText(input)
        await entered.wait()
        markdown.change = .turnInto(.header, text: NSAttributedString(string: "retired header"))
        #expect(!actions.textViewShouldReplaceText(input, " ", NSRange(location: input.attributedText.length, length: 0)))
        let next = SimpleTableTextFixture.info(id: "next-table-cell", text: "")
        fixture.container.getReturnInfo[next.id] = next
        fixture.handler.info = next
        release.open()
        try await fixture.handler.changeText(attributedString: NSAttributedString(string: "new row").sendable())
        #expect(fixture.service.turnIntoNumberOfCalls == 0)
        #expect(fixture.writes.map(\.value.text) == ["old in flight", "new row"])
        #expect(fixture.writes.map(\.blockId) == ["table-text-cell", "next-table-cell"])
    }
}

private enum SimpleTableTextFailure: Error {
    case rejected
    case unexpectedPasteboardUse
}

@MainActor
private final class SimpleTableTextFixture {
    struct Write {
        let blockId: String
        let value: MiddlewareString
    }

    let container: InfoContainerMock
    let service: BlockActionServiceMock
    let document: MockBaseDocument
    let nativeHandler: BlockActionHandler
    let markupChanger: BlockMarkupChangerMock
    let handler: SimpleTablesTextBlockActionHandler
    private let pasteboard: SimpleTableUnusedPasteboard
    var writes: [Write] = []
    var nativeWrite: @MainActor (String, MiddlewareString) async throws -> Void = { _, _ in }

    init(
        markdownListener: SimpleTableMarkdownListener? = nil,
        onKeyboardAction: @escaping @MainActor () -> Void = {}
    ) {
        let markupChanger = BlockMarkupChangerMock()
        let pasteboard = SimpleTableUnusedPasteboard()
        let container = InfoContainerMock()
        let service = BlockActionServiceMock()
        let details = ObjectDetails(id: "table-text-test-document", values: [:])
        let document = MockBaseDocument(objectId: details.id, details: details)
        document.mockSpaceId = "table-text-test-space"
        document.mockInfoContainer = container
        let initial = Self.info(id: "table-text-cell", text: "")
        container.getReturnInfo[initial.id] = initial
        let native = BlockActionHandler(
            document: document, markupChanger: markupChanger, service: service)
        self.container = container
        self.service = service
        self.document = document
        self.nativeHandler = native
        self.markupChanger = markupChanger
        self.pasteboard = pasteboard
        let subjects = FocusSubjectsHolder()
        handler = SimpleTablesTextBlockActionHandler(
            document: document, info: initial,
            focusSubject: PassthroughSubject<BlockFocusPosition, Never>(),
            actionHandler: native, pasteboardService: pasteboard,
            markdownListener: markdownListener ?? SimpleTableMarkdownListener(),
            cursorManager: EditorCursorManager(focusSubjectHolder: subjects),
            accessoryViewStateManager: SimpleTableUnusedAccessory(),
            markupChanger: markupChanger,
            responderScrollViewHelper: ResponderScrollViewHelper(scrollView: UIScrollView()),
            showObject: { _ in }, openURL: { _ in }, onShowStyleMenu: { _ in },
            onEnterSelectionMode: { _ in }, onSelectUndoRedo: {}, showTextIconPicker: {},
            showWaitingView: { _ in }, hideWaitingView: {},
            onKeyboardAction: { _ in onKeyboardAction() }, openLinkToObject: { _ in })
        service.onSetText = { [weak self] _, blockId, value in
            guard let self else { throw SimpleTableTextFailure.rejected }
            writes.append(Write(blockId: blockId, value: value))
            container.getReturnInfo[blockId] = Self.info(id: blockId, text: value.text)
            try await nativeWrite(blockId, value)
        }
    }

    static func info(id: String, text: String) -> BlockInformation {
        BlockInformation(
            id: id, content: .text(.plain(text, contentType: .text)),
            backgroundColor: nil, horizontalAlignment: .left, childrenIds: [],
            configurationData: BlockInformationMetadata(backgroundColor: .default), fields: [:])
    }
}

@MainActor
private final class SimpleTableTextGate {
    private var isOpen = false
    private var waiters: [CheckedContinuation<Void, Never>] = []

    func wait() async {
        if isOpen { return }
        await withCheckedContinuation { waiters.append($0) }
    }

    func open() {
        isOpen = true
        let pending = waiters
        waiters.removeAll()
        for waiter in pending { waiter.resume() }
    }
}

@MainActor
private final class SimpleTableUnusedAccessory: AccessoryViewStateManager {
    func willBeginEditing(with configuration: TextViewAccessoryConfiguration) {}
    func didBeginEdition(with configuration: TextViewAccessoryConfiguration) {}
    func didEndEditing(with configuration: TextViewAccessoryConfiguration) {}
    func textDidChange(changeType: TextChangeType) {}
    func selectionDidChange(range: NSRange) {}
}

private final class SimpleTableUnusedPasteboard: PasteboardBlockDocumentServiceProtocol {
    var hasValidURL: Bool { false }
    func pasteInsideBlock(
        objectId: String, spaceId: String, focusedBlockId: String, range: NSRange,
        handleLongOperation: @escaping () -> Void,
        completion: @escaping @MainActor (PasteboardPasteResult?) -> Void
    ) { fatalError("Pasteboard is outside this text persistence fixture") }
    func pasteInSelectedBlocks(
        objectId: String, spaceId: String, selectedBlockIds: [String],
        handleLongOperation: @escaping () -> Void,
        completion: @escaping @MainActor (PasteboardPasteResult?) -> Void
    ) { fatalError("Pasteboard is outside this text persistence fixture") }
    func copy(
        document: some BaseDocumentProtocol, blocksIds: [String], selectedTextRange: NSRange
    ) async throws { throw SimpleTableTextFailure.unexpectedPasteboardUse }
    func cut(
        document: some BaseDocumentProtocol, blocksIds: [String], selectedTextRange: NSRange
    ) async throws { throw SimpleTableTextFailure.unexpectedPasteboardUse }
}

@MainActor
private final class SimpleTableMarkdownListener: MarkdownListener {
    var change: MarkdownChange?
    func markdownChange(textView: UITextView, replacementText: String, range: NSRange) -> MarkdownChange? {
        change
    }
}
