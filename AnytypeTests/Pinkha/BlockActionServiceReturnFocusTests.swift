import AnytypeCore
import Combine
import Factory
import ProtobufMessages
import Services
import Testing
import UIKit
@testable import Anytype

@Suite("Return split preserves one focus owner", .serialized)
@MainActor
struct BlockActionServiceReturnFocusTests {
    @Test("An already rendered split row keeps the request published by the real service")
    func renderedSubscriberKeepsSplitRequest() async throws {
        let fixture = try ReturnSplitFixture()
        defer { fixture.close() }
        let previous = fixture.row(id: fixture.sourceID, text: fixture.sourceText)
        fixture.attach(previous, y: 80)
        previous.takeFocus(at: .end)
        try #require(previous.textView.textView.isFirstResponder)
        let destination = fixture.row(id: fixture.destinationID, text: "")
        fixture.attach(destination, y: 240)

        let observation = ReturnSplitObservation()
        let publication = fixture.subjects.focusSubject(for: fixture.destinationID).sink { _ in
            observation.publications += 1
            observation.publishedRequest = fixture.cursor.focusRequestId
            observation.pendingAtPublication = fixture.cursor.blockFocus?.requestId
            observation.callsAtPublication = fixture.textService.calls
        }
        defer { publication.cancel() }

        try await fixture.split()
        await finishMainQueueTurn()

        #expect(observation.publications == 1)
        let published = try #require(observation.publishedRequest)
        #expect(observation.pendingAtPublication == published,
                "Publishing must not manufacture a request that the next statement supersedes")
        #expect(observation.callsAtPublication == ["setText", "split"])
        fixture.expectSplitArguments()
        #expect(destination.textView.textView.isFirstResponder)
        #expect(!previous.textView.textView.isFirstResponder)
        #expect(destination.textView.textView.selectedRange == NSRange(location: 0, length: 0))
        #expect(fixture.insertions.consume(in: [fixture.destinationID]) == [fixture.destinationID])
    }

    @Test("The actual general event can render and consume the same pending split request")
    func laterRenderedRowConsumesSplitRequest() async throws {
        let fixture = try ReturnSplitFixture()
        defer { fixture.close() }
        let previous = fixture.row(id: fixture.sourceID, text: fixture.sourceText)
        fixture.attach(previous, y: 80)
        previous.takeFocus(at: .end)
        try #require(previous.textView.textView.isFirstResponder)
        let documentID = fixture.documentID
        let observation = ReturnSplitObservation()
        let publication = fixture.subjects.focusSubject(for: fixture.destinationID).sink { _ in
            observation.publications += 1
            observation.publishedRequest = fixture.cursor.focusRequestId
        }
        defer { publication.cancel() }
        let events = await EventBunchSubscribtion.default.addHandlerAwaiting { bunch in
            guard bunch.contextId == documentID else { return }
            let general = bunch.localEvents.contains { event in
                if case .general = event { return true }
                return false
            }
            guard general else { return }
            await MainActor.run {
                observation.generalEvents += 1
                observation.pendingAtRender = fixture.cursor.blockFocus?.requestId
                observation.insertedAtRender = fixture.insertions.consume(in: [fixture.destinationID])
                observation.destination = fixture.row(id: fixture.destinationID, text: "")
                if let destination = observation.destination {
                    fixture.attach(destination, y: 240)
                }
                observation.pendingAfterRender = fixture.cursor.blockFocus?.requestId
            }
        }
        defer { events.cancel() }

        try await fixture.split()
        await finishMainQueueTurn()

        #expect(observation.publications == 1)
        #expect(observation.generalEvents == 1)
        let published = try #require(observation.publishedRequest)
        #expect(observation.pendingAtRender == published)
        #expect(observation.pendingAfterRender == nil)
        #expect(observation.insertedAtRender == [fixture.destinationID])
        let destination = try #require(observation.destination)
        #expect(destination.textView.textView.isFirstResponder)
        #expect(!previous.textView.textView.isFirstResponder)
        #expect(fixture.cursor.consumeBlockFocus(for: fixture.destinationID) == nil)
        fixture.expectSplitArguments()
    }

    @Test("A genuinely later editor request still cancels the split row's deferred request")
    func laterRequestStillSupersedesSplitFocus() async throws {
        let fixture = try ReturnSplitFixture()
        defer { fixture.close() }
        let pending = fixture.row(id: fixture.destinationID, text: "")
        let selectedID = "selected-" + UUID().uuidString
        let selected = fixture.row(id: selectedID, text: "newer choice")
        fixture.attach(selected, y: 80)
        let observation = ReturnSplitObservation()
        let publication = fixture.subjects.focusSubject(for: fixture.destinationID).sink { _ in
            observation.publishedRequest = fixture.cursor.focusRequestId
        }
        defer { publication.cancel() }

        try await fixture.split()
        let splitRequest = try #require(observation.publishedRequest)
        fixture.cursor.focus(at: selectedID, position: .end)
        let newerRequest = try #require(fixture.cursor.focusRequestId)
        #expect(newerRequest != splitRequest)
        fixture.attach(pending, y: 240)
        await finishMainQueueTurn()

        #expect(selected.textView.textView.isFirstResponder)
        #expect(!pending.textView.textView.isFirstResponder,
                "The unchanged stale-request guard must reject a superseded request")
        let laterCaret = NSRange(location: 2, length: 0)
        selected.textView.textView.selectedRange = laterCaret
        await finishMainQueueTurn()
        #expect(selected.textView.textView.isFirstResponder)
        #expect(selected.textView.textView.selectedRange == laterCaret)
        #expect(!pending.textView.textView.isFirstResponder)
        fixture.expectSplitArguments()
        #expect(fixture.insertions.consume(in: [fixture.destinationID]) == [fixture.destinationID])
    }

    private func finishMainQueueTurn() async {
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            DispatchQueue.main.async { continuation.resume() }
        }
    }
}

@MainActor
private final class ReturnSplitObservation {
    var publications = 0
    var generalEvents = 0
    var publishedRequest: UUID?
    var pendingAtPublication: UUID?
    var pendingAtRender: UUID?
    var pendingAfterRender: UUID?
    var callsAtPublication = [String]()
    var insertedAtRender = [String]()
    var destination: TextBlockContentView?
}

@MainActor
private final class ReturnSplitFixture {
    let documentID: String
    let sourceID: String
    let destinationID: String
    let sourceText = "typed before Return"
    let subjects: FocusSubjectsHolder
    let cursor: EditorCursorManager
    let textService: ReturnSplitTextService
    let insertions: any KeyboardInsertedBlocksStorageProtocol
    let window: UIWindow
    let controller: UIViewController
    private weak var previousKeyWindow: UIWindow?
    private let models: EditorMainItemModelsHolder
    private let actionService: BlockActionService
    private var closed = false

    init() throws {
        let scene = try #require(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
            .first { $0.activationState == .foregroundActive })
        let documentID = "return-focus-document-" + UUID().uuidString
        let sourceID = "return-focus-source-" + UUID().uuidString
        let destinationID = "return-focus-destination-" + UUID().uuidString
        let subjects = FocusSubjectsHolder()
        let cursor = EditorCursorManager(focusSubjectHolder: subjects)
        let textService = ReturnSplitTextService(createdID: destinationID)
        let models = EditorMainItemModelsHolder()
        let window = UIWindow(windowScene: scene)
        let controller = UIViewController()
        let insertions = Container.shared.keyboardInsertedBlocksStorage()
        Container.shared.manager.push()
        Container.shared.textServiceHandler.register { textService }
        let actionService = BlockActionService(
            documentId: documentID, modelsHolder: models, cursorManager: cursor
        )
        self.documentID = documentID
        self.sourceID = sourceID
        self.destinationID = destinationID
        self.subjects = subjects
        self.cursor = cursor
        self.textService = textService
        self.models = models
        self.window = window
        self.controller = controller
        self.insertions = insertions
        self.actionService = actionService
        previousKeyWindow = scene.windows.first { $0.isKeyWindow }
        window.frame = CGRect(x: 0, y: 0, width: 390, height: 844)
        window.rootViewController = controller
        window.makeKeyAndVisible()
        controller.view.layoutIfNeeded()
    }

    func split() async throws {
        try await actionService.setAndSplit(
            NSAttributedString(string: sourceText).sendable(),
            blockId: sourceID,
            mode: .bottom,
            range: NSRange(location: sourceText.utf16.count, length: 0),
            newBlockContentType: .text
        )
    }

    func expectSplitArguments() {
        #expect(textService.calls == ["setText", "split"])
        #expect(textService.setContext == documentID)
        #expect(textService.setBlock == sourceID)
        #expect(textService.writtenText == sourceText)
        #expect(textService.splitContext == documentID)
        #expect(textService.splitBlock == sourceID)
        #expect(textService.splitRange == NSRange(location: sourceText.utf16.count, length: 0))
        #expect(textService.splitStyle == .text)
        #expect(textService.splitMode == .bottom)
        #expect(SessionCreatedBlockIdsStorage.shared.contains(destinationID))
    }

    func row(id: String, text: String) -> TextBlockContentView {
        let request = cursor.consumeBlockFocus(for: id)
        let defaults = TextBlockContentConfiguration.empty
        let font = UIFont.systemFont(ofSize: 17)
        let configuration = TextBlockContentConfiguration(
            blockId: id, content: .plain(text, contentType: .text),
            attributedString: NSAttributedString(string: text, attributes: [.font: font]),
            placeholderAttributes: [:], typingAttributes: { _ in [.font: font] },
            textContainerInsets: .zero, alignment: .left,
            isCheckable: false, isToggled: false, isChecked: false, shouldDisplayPlaceholder: false,
            initialBlockFocusPosition: request?.position, initialFocusRequestId: request?.requestId,
            focusContext: cursor, focusPublisher: subjects.focusSubject(for: id).eraseToAnyPublisher(),
            resetPublisher: defaults.resetPublisher, actions: defaults.actions
        )
        let row = TextBlockContentView(frame: .zero)
        row.update(with: configuration)
        var state = UICellConfigurationState(traitCollection: UITraitCollection())
        state.isEditing = true
        state.isLocked = false
        row.update(with: state)
        return row
    }

    func attach(_ row: UIView, y: CGFloat) {
        row.frame = CGRect(x: 20, y: y, width: 320, height: 100)
        controller.view.addSubview(row)
        controller.view.layoutIfNeeded()
    }

    func close() {
        guard !closed else { return }
        closed = true
        window.endEditing(true)
        window.isHidden = true
        previousKeyWindow?.makeKeyAndVisible()
        _ = insertions.consume(in: [destinationID])
        Container.shared.manager.pop()
    }
}

@MainActor
private final class ReturnSplitTextService: TextServiceProtocol {
    let createdID: String
    private(set) var calls = [String]()
    private(set) var setContext: String?
    private(set) var setBlock: String?
    private(set) var writtenText: String?
    private(set) var splitContext: String?
    private(set) var splitBlock: String?
    private(set) var splitRange: NSRange?
    private(set) var splitStyle: BlockText.Style?
    private(set) var splitMode: Anytype_Rpc.Block.Split.Request.Mode?

    init(createdID: String) {
        self.createdID = createdID
    }

    func setText(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        calls.append("setText")
        setContext = contextId
        setBlock = blockId
        writtenText = middlewareString.text
    }

    func split(contextId: String, blockId: String, range: NSRange, style: BlockText.Style, mode: Anytype_Rpc.Block.Split.Request.Mode) async throws -> String {
        calls.append("split")
        splitContext = contextId
        splitBlock = blockId
        splitRange = range
        splitStyle = style
        splitMode = mode
        return createdID
    }

    func checked(contextId: String, blockId: String, newValue: Bool) async throws {
        throw UnexpectedReturnRPC.called("checked")
    }

    func merge(contextId: String, firstBlockId: String, secondBlockId: String) async throws {
        throw UnexpectedReturnRPC.called("merge")
    }

    func setStyle(contextId: String, blockId: String, style: BlockText.Style) async throws {
        throw UnexpectedReturnRPC.called("setStyle")
    }

    func setTextForced(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        throw UnexpectedReturnRPC.called("setTextForced")
    }

    func setTextIcon(contextId: String, blockId: String, imageObjectId: String, emojiUnicode: String) async throws {
        throw UnexpectedReturnRPC.called("setTextIcon")
    }
}

private enum UnexpectedReturnRPC: Error {
    case called(String)
}
