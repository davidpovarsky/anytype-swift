import Foundation
import Services
import Testing
@testable import Anytype

@Suite
struct EditorLocalEventPublisherTests {
    @Test
    func publishesToTheSuppliedOwnerAfterTheStyleWriteCompletes() async throws {
        let owner = EditorWriterEventProbe()
        let handler = TextServiceHandler(textService: owner, localEvents: owner)
        try await handler.setStyle(contextId: "annotation-one", blockId: "block", style: .text)
        let calls = await owner.snapshot()
        #expect(calls == ["write:annotation-one:block", "event:annotation-one:block"])
    }

    @Test
    func aFailedStyleWriteDoesNotPublish() async {
        let owner = EditorWriterEventProbe(failure: .expected)
        let handler = TextServiceHandler(textService: owner, localEvents: owner)
        do {
            try await handler.setStyle(contextId: "annotation-one", blockId: "block", style: .text)
            Issue.record("The original style failure was swallowed")
        } catch {
            #expect(error as? EditorWriterEventFailure == .expected)
        }
        let calls = await owner.snapshot()
        #expect(calls == ["write:annotation-one:block"])
    }

    @Test
    func cancellationDoesNotPublishOrRetry() async {
        let owner = EditorWriterEventProbe(failure: .cancelled)
        let handler = TextServiceHandler(textService: owner, localEvents: owner)
        do {
            try await handler.setStyle(contextId: "annotation-one", blockId: "block", style: .text)
            Issue.record("The original cancellation was swallowed")
        } catch {
            #expect(error is CancellationError)
        }
        let calls = await owner.snapshot()
        #expect(calls == ["write:annotation-one:block"])
    }

    @Test
    func splitStillLeavesPublicationToTheOriginalFocusOwner() async throws {
        let owner = EditorWriterEventProbe()
        let handler = TextServiceHandler(textService: owner, localEvents: owner)
        let mode = try #require(TextServiceProtocol.SplitMode(rawValue: 0))
        let block = try await handler.split(
            contextId: "annotation-one", blockId: "block", range: NSRange(location: 1, length: 2),
            style: .text, mode: mode
        )
        let calls = await owner.snapshot()
        #expect(block == "created-block")
        #expect(calls == ["split:annotation-one:block"])
    }

    @Test
    func separateEditorsDoNotShareTheInjectedEventOwner() async throws {
        let first = EditorWriterEventProbe(), second = EditorWriterEventProbe()
        let firstHandler = TextServiceHandler(textService: first, localEvents: first)
        let secondHandler = TextServiceHandler(textService: second, localEvents: second)
        try await firstHandler.setStyle(contextId: "annotation-one", blockId: "same-block", style: .text)
        try await secondHandler.setStyle(contextId: "annotation-two", blockId: "same-block", style: .text)
        let firstCalls = await first.snapshot(), secondCalls = await second.snapshot()
        #expect(firstCalls == ["write:annotation-one:same-block", "event:annotation-one:same-block"])
        #expect(secondCalls == ["write:annotation-two:same-block", "event:annotation-two:same-block"])
    }
}

private enum EditorWriterEventFailure: Error, Equatable {
    case expected
    case cancelled
}

private actor EditorWriterEventProbe: TextServiceProtocol, EditorLocalEventPublishing {
    let failure: EditorWriterEventFailure?
    private var calls: [String] = []

    init(failure: EditorWriterEventFailure? = nil) {
        self.failure = failure
    }

    func snapshot() -> [String] { calls }

    func setStyle(contextId: String, blockId: String, style: Style) throws {
        calls.append("write:\(contextId):\(blockId)")
        if failure == .cancelled { throw CancellationError() }
        if let failure { throw failure }
    }

    func split(contextId: String, blockId: String, range: NSRange, style: Style, mode: SplitMode) -> String {
        calls.append("split:\(contextId):\(blockId)")
        return "created-block"
    }

    func setStyle(contextId: String, blockId: String) {
        calls.append("event:\(contextId):\(blockId)")
    }

    func refresh(contextId: String) { calls.append("refresh:\(contextId)") }
    func setToggled(contextId: String, blockId: String) { calls.append("toggle:\(contextId):\(blockId)") }
    func setText(contextId: String, blockId: String, text: MiddlewareString) {
        calls.append("event-text:\(contextId):\(blockId)")
    }
    func setLoadingState(contextId: String, blockId: String) { calls.append("loading:\(contextId):\(blockId)") }
    func setText(contextId: String, blockId: String, middlewareString: MiddlewareString) {
        calls.append("text:\(contextId):\(blockId)")
    }
    func setTextForced(contextId: String, blockId: String, middlewareString: MiddlewareString) {
        calls.append("forced:\(contextId):\(blockId)")
    }
    func merge(contextId: String, firstBlockId: String, secondBlockId: String) {
        calls.append("merge:\(contextId):\(firstBlockId):\(secondBlockId)")
    }
    func checked(contextId: String, blockId: String, newValue: Bool) {
        calls.append("checked:\(contextId):\(blockId)")
    }
    func setTextIcon(contextId: String, blockId: String, imageObjectId: String, emojiUnicode: String) {
        calls.append("icon:\(contextId):\(blockId)")
    }
}
