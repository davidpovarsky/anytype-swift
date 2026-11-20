import Foundation
import Services
import Testing
@testable import Anytype

@Suite
struct TextServiceHandlerInjectionTests {
    @Test
    func preservesTextAndMarksOnBothOriginalTextOperations() async throws {
        let service = OriginalEditorTextServiceProbe()
        let handler = TextServiceHandler(textService: service)
        let text = MiddlewareString(text: "שלום English 👩🏽‍💻")
        try await handler.setText(contextId: "document", blockId: "first", middlewareString: text)
        try await handler.setTextForced(contextId: "document", blockId: "second", middlewareString: text)
        let calls = await service.recorded()
        #expect(calls.map(\.operation) == ["text", "forced"])
        #expect(calls.map(\.context) == ["document", "document"])
        #expect(calls.map(\.block) == ["first", "second"])
        for call in calls {
            #expect(call.text?.text == text.text)
            #expect(call.text?.marks == text.marks)
        }
    }

    @Test
    func preservesSplitResultAndUTF16Range() async throws {
        let service = OriginalEditorTextServiceProbe()
        let handler = TextServiceHandler(textService: service)
        let mode = try #require(TextServiceProtocol.SplitMode(rawValue: 0))
        let range = NSRange(location: 2, length: "👩🏽‍💻".utf16.count)
        let result = try await handler.split(
            contextId: "document", blockId: "block", range: range, style: .text, mode: mode
        )
        let calls = await service.recorded()
        let call = try #require(calls.first)
        #expect(result == "created-by-injected-service")
        #expect(call.operation == "split")
        #expect(call.context == "document")
        #expect(call.block == "block")
        #expect(call.range == range)
        #expect(call.style == .text)
        #expect(call.mode == mode)
    }

    @Test
    func forwardsCheckedMergeAndIconToTheSameInjectedService() async throws {
        let service = OriginalEditorTextServiceProbe()
        let handler = TextServiceHandler(textService: service)
        try await handler.checked(contextId: "document", blockId: "first", newValue: true)
        try await handler.merge(contextId: "document", firstBlockId: "first", secondBlockId: "second")
        try await handler.setTextIcon(
            contextId: "document", blockId: "first", imageObjectId: "image", emojiUnicode: "📖"
        )
        let calls = await service.recorded()
        try #require(calls.count == 3)
        #expect(calls.map(\.operation) == ["checked", "merge", "icon"])
        #expect(calls.allSatisfy { $0.context == "document" && $0.block == "first" })
        #expect(calls[0].payload == ["true"])
        #expect(calls[1].payload == ["second"])
        #expect(calls[2].payload == ["image", "📖"])
    }

    @Test
    func propagatesAStyleFailureWithoutTryingAnotherService() async {
        let service = OriginalEditorTextServiceProbe(fails: true)
        let handler = TextServiceHandler(textService: service)
        do {
            try await handler.setStyle(contextId: "document", blockId: "block", style: .text)
            Issue.record("The injected style failure was swallowed")
        } catch {
            #expect(error as? OriginalEditorTextProbeError == .expected)
        }
        let calls = await service.recorded()
        #expect(calls.count == 1)
        #expect(calls.first?.operation == "style")
    }

    @Test
    func keepsTwoEditorServiceInstancesSeparate() async throws {
        let first = OriginalEditorTextServiceProbe()
        let second = OriginalEditorTextServiceProbe()
        let firstHandler = TextServiceHandler(textService: first)
        let secondHandler = TextServiceHandler(textService: second)
        try await firstHandler.setText(contextId: "first-document", blockId: "block", middlewareString: .init(text: "א"))
        try await secondHandler.setText(contextId: "second-document", blockId: "block", middlewareString: .init(text: "ב"))
        let firstCalls = await first.recorded()
        let secondCalls = await second.recorded()
        #expect(firstCalls.count == 1 && firstCalls.first?.context == "first-document")
        #expect(secondCalls.count == 1 && secondCalls.first?.context == "second-document")
        #expect(firstCalls.first?.text?.text == "א")
        #expect(secondCalls.first?.text?.text == "ב")
    }
}

private enum OriginalEditorTextProbeError: Error, Equatable {
    case expected
}

private struct OriginalEditorTextCall: Sendable {
    let operation: String
    let context: String
    let block: String
    var payload: [String] = []
    var text: MiddlewareString?
    var range: NSRange?
    var style: TextServiceProtocol.Style?
    var mode: TextServiceProtocol.SplitMode?
}

private actor OriginalEditorTextServiceProbe: TextServiceProtocol {
    let fails: Bool
    private var calls: [OriginalEditorTextCall] = []

    init(fails: Bool = false) {
        self.fails = fails
    }

    func recorded() -> [OriginalEditorTextCall] { calls }

    func setText(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        calls.append(.init(operation: "text", context: contextId, block: blockId, text: middlewareString))
        try checkFailure()
    }

    func setTextForced(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        calls.append(.init(operation: "forced", context: contextId, block: blockId, text: middlewareString))
        try checkFailure()
    }

    func setStyle(contextId: String, blockId: String, style: Style) async throws {
        calls.append(.init(operation: "style", context: contextId, block: blockId, style: style))
        try checkFailure()
    }

    func split(contextId: String, blockId: String, range: NSRange, style: Style, mode: SplitMode) async throws -> String {
        calls.append(.init(operation: "split", context: contextId, block: blockId, range: range, style: style, mode: mode))
        try checkFailure()
        return "created-by-injected-service"
    }

    func checked(contextId: String, blockId: String, newValue: Bool) async throws {
        calls.append(.init(operation: "checked", context: contextId, block: blockId, payload: [String(newValue)]))
        try checkFailure()
    }

    func merge(contextId: String, firstBlockId: String, secondBlockId: String) async throws {
        calls.append(.init(operation: "merge", context: contextId, block: firstBlockId, payload: [secondBlockId]))
        try checkFailure()
    }

    func setTextIcon(contextId: String, blockId: String, imageObjectId: String, emojiUnicode: String) async throws {
        calls.append(.init(operation: "icon", context: contextId, block: blockId, payload: [imageObjectId, emojiUnicode]))
        try checkFailure()
    }

    private func checkFailure() throws {
        if fails { throw OriginalEditorTextProbeError.expected }
    }
}
