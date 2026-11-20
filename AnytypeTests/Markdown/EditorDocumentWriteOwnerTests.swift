import Foundation
import Services
import Testing
@testable import Anytype

@Suite
@MainActor
struct EditorDocumentWriteOwnerTests {
    @Test
    func forwardsAllOriginalTextOperationsWithTheOwnedContext() async throws {
        let document = makeDocument()
        let owner = try makeOwner(document)
        let probe = DocumentOwnerProtocolProbe()
        let writer = DocumentOwnedTextService(owner: owner, service: probe)
        let text = MiddlewareString(text: "שלום English 👩🏽‍💻")
        let range = NSRange(location: 2, length: "👩🏽‍💻".utf16.count)
        let mode = try #require(TextServiceProtocol.SplitMode(rawValue: 0))
        try await writer.setText(contextId: "owned", blockId: "a", middlewareString: text)
        try await writer.setTextForced(contextId: "owned", blockId: "b", middlewareString: text)
        try await writer.setStyle(contextId: "owned", blockId: "a", style: .text)
        let created = try await writer.split(contextId: "owned", blockId: "a", range: range, style: .text, mode: mode)
        try await writer.merge(contextId: "owned", firstBlockId: "a", secondBlockId: "b")
        try await writer.checked(contextId: "owned", blockId: "a", newValue: true)
        try await writer.setTextIcon(contextId: "owned", blockId: "a", imageObjectId: "image", emojiUnicode: "📖")
        let calls = await probe.recorded()
        #expect(calls == [
            "text:owned:a", "forced:owned:b", "style:owned:a", "split:owned:a",
            "merge:owned:a:b", "checked:owned:a:true", "icon:owned:a:image:📖"
        ])
        let texts = await probe.texts
        let ranges = await probe.ranges
        #expect(texts.map(\.text) == [text.text, text.text])
        #expect(texts.allSatisfy { $0.marks == text.marks })
        #expect(ranges == [range])
        #expect(created == "new-block")
        #expect(owner.isDrained && owner.pendingOperationCount == 0 && !owner.isRetired)
    }

    @Test
    func refusesForeignContextReadonlyModeAndLivePermissionLossBeforeDispatch() async throws {
        let document = makeDocument()
        let owner = try makeOwner(document)
        let probe = DocumentOwnerProtocolProbe()
        let writer = DocumentOwnedTextService(owner: owner, service: probe)
        let foreign = await captureFailure {
            try await writer.setStyle(contextId: "foreign", blockId: "a", style: .text)
        }
        #expect(foreign == .rejected(.wrongContext))
        document.mockPermissions.canEditBlocks = false
        let denied = await captureFailure {
            try await writer.setStyle(contextId: "owned", blockId: "a", style: .text)
        }
        #expect(denied == .rejected(.notEditable))
        let preview = makeDocument(mode: .preview)
        let readonly = DocumentOwnedTextService(owner: try makeOwner(preview), service: probe)
        let previewError = await captureFailure {
            try await readonly.setStyle(contextId: "owned", blockId: "a", style: .text)
        }
        #expect(previewError == .rejected(.notHandling))
        let calls = await probe.recorded()
        #expect(calls.isEmpty)
    }

    @Test
    func rechecksOriginalDocumentIdentityModeAndOpenState() async throws {
        let changes: [@MainActor (MockBaseDocument) -> Void] = [
            { $0.mockObjectId = "other" },
            { $0.mockSpaceId = "other" },
            { $0.mockMode = .version("history") },
            { $0.mockIsOpened = false }
        ]
        for change in changes {
            let document = makeDocument()
            let owner = try makeOwner(document)
            let probe = DocumentOwnerProtocolProbe()
            let writer = DocumentOwnedTextService(owner: owner, service: probe)
            change(document)
            let failure = await captureFailure {
                try await writer.setStyle(contextId: "owned", blockId: "a", style: .text)
            }
            #expect(failure == .rejected(.documentChanged))
            let calls = await probe.recorded()
            #expect(calls.isEmpty)
        }
    }

    @Test
    func retirementDistinguishesAnAlreadyCompletedWriteFromADispatchRefusal() async throws {
        let document = makeDocument()
        var drained = 0
        let owner = try makeOwner(document, onDrained: { drained += 1 })
        let gate = DocumentOwnerTestGate()
        let probe = DocumentOwnerProtocolProbe(gate: gate)
        let writer = DocumentOwnedTextService(owner: owner, service: probe)
        let operation = Task {
            try await writer.setText(contextId: "owned", blockId: "a", middlewareString: .init(text: "שלום"))
        }
        await gate.waitForEntry()
        owner.retire()
        #expect(owner.pendingOperationCount == 1 && !owner.isDrained && drained == 0)
        let refused = await captureFailure {
            try await writer.setStyle(contextId: "owned", blockId: "a", style: .text)
        }
        #expect(refused == .rejected(.retired))
        await gate.release()
        let completed = await captureFailure { try await operation.value }
        #expect(completed == .completedWithoutOwnership(.retired))
        let calls = await probe.recorded()
        #expect(calls == ["text:owned:a"])
        #expect(owner.isDrained && drained == 1)
        owner.retire()
        #expect(drained == 1)
    }

    @Test
    func preservesServiceErrorsAndReleasesTheirLease() async throws {
        let document = makeDocument()
        let owner = try makeOwner(document)
        let probe = DocumentOwnerProtocolProbe(fails: true)
        let writer = DocumentOwnedTextService(owner: owner, service: probe)
        do {
            try await writer.setText(contextId: "owned", blockId: "a", middlewareString: .init(text: "שלום"))
            Issue.record("Original service error was swallowed")
        } catch {
            #expect(error as? DocumentOwnerProbeError == .expected)
        }
        #expect(owner.isDrained)
        let calls = await probe.recorded()
        #expect(calls == ["text:owned:a"])
    }

    @Test
    func retiringOneOwnerDoesNotAuthorizeOrRetireAnother() async throws {
        let firstDocument = makeDocument()
        let secondDocument = makeDocument(object: "second")
        let firstOwner = try makeOwner(firstDocument)
        let secondOwner = try makeOwner(secondDocument)
        let probe = DocumentOwnerProtocolProbe()
        let first = DocumentOwnedTextService(owner: firstOwner, service: probe)
        let second = DocumentOwnedTextService(owner: secondOwner, service: probe)
        firstOwner.retire()
        let retired = await captureFailure {
            try await first.setStyle(contextId: "owned", blockId: "a", style: .text)
        }
        let foreign = await captureFailure {
            try await second.setStyle(contextId: "owned", blockId: "a", style: .text)
        }
        try await second.setStyle(contextId: "second", blockId: "a", style: .text)
        #expect(retired == .rejected(.retired) && foreign == .rejected(.wrongContext))
        let calls = await probe.recorded()
        #expect(calls == ["style:second:a"])
        #expect(!secondOwner.isRetired && secondOwner.isDrained)
    }

    @Test
    func readonlyToggleRemainsPresentationalButRetiredEventsAreDropped() async throws {
        let document = makeDocument(mode: .preview)
        document.mockPermissions.canEditBlocks = false
        let owner = try makeOwner(document)
        let probe = DocumentOwnerProtocolProbe()
        let publisher = DocumentOwnedLocalEventPublisher(owner: owner, publisher: probe)
        await publisher.setToggled(contextId: "owned", blockId: "a")
        await publisher.setText(contextId: "owned", blockId: "a", text: .init(text: "שלום"))
        owner.retire()
        await publisher.setToggled(contextId: "owned", blockId: "a")
        let calls = await probe.recorded()
        #expect(calls == ["toggle:owned:a"])
    }

    @Test
    func retirementWaitsForAnAlreadyAdmittedPublicationToDrain() async throws {
        let document = makeDocument()
        var drained = 0
        let owner = try makeOwner(document, onDrained: { drained += 1 })
        let gate = DocumentOwnerTestGate()
        let probe = DocumentOwnerProtocolProbe(gate: gate, holdPublication: true)
        let publisher = DocumentOwnedLocalEventPublisher(owner: owner, publisher: probe)
        let operation = Task { await publisher.setStyle(contextId: "owned", blockId: "a") }
        await gate.waitForEntry()
        owner.retire()
        #expect(owner.pendingOperationCount == 1 && drained == 0)
        await gate.release()
        await operation.value
        let calls = await probe.recorded()
        #expect(calls == ["event:owned:a"])
        #expect(owner.isDrained && drained == 1)
    }

    private func makeDocument(object: String = "owned", mode: DocumentMode = .handling) -> MockBaseDocument {
        let document = MockBaseDocument(objectId: object, details: nil)
        document.mockSpaceId = "owned-space"
        document.mockMode = mode
        document.mockPermissions.canEditBlocks = true
        return document
    }

    private func makeOwner(
        _ document: MockBaseDocument, onDrained: (@MainActor () -> Void)? = nil
    ) throws -> EditorDocumentWriteOwner {
        try EditorDocumentWriteOwner(
            data: .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode),
            document: document, onDrained: onDrained
        )
    }

    private func captureFailure(_ operation: () async throws -> Void) async -> EditorDocumentWriteError? {
        do { try await operation(); return nil }
        catch { return error as? EditorDocumentWriteError }
    }
}

private enum DocumentOwnerProbeError: Error, Equatable { case expected }

private actor DocumentOwnerTestGate {
    private var entered = false
    private var released = false
    private var observers: [CheckedContinuation<Void, Never>] = []
    private var pending: [CheckedContinuation<Void, Never>] = []

    func hold() async {
        entered = true
        let values = observers
        observers = []
        for value in values { value.resume() }
        if !released { await withCheckedContinuation { pending.append($0) } }
    }

    func waitForEntry() async {
        if entered { return }
        await withCheckedContinuation { observers.append($0) }
    }

    func release() {
        released = true
        let values = pending
        pending = []
        for value in values { value.resume() }
    }
}

private actor DocumentOwnerProtocolProbe: TextServiceProtocol, EditorLocalEventPublishing {
    private var calls: [String] = []
    private(set) var texts: [MiddlewareString] = []
    private(set) var ranges: [NSRange] = []
    let gate: DocumentOwnerTestGate?
    let holdPublication: Bool
    let fails: Bool

    init(gate: DocumentOwnerTestGate? = nil, holdPublication: Bool = false, fails: Bool = false) {
        self.gate = gate
        self.holdPublication = holdPublication
        self.fails = fails
    }

    func recorded() -> [String] { calls }

    func setText(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        if !holdPublication { await gate?.hold() }
        calls.append("text:\(contextId):\(blockId)")
        texts.append(middlewareString)
        if fails { throw DocumentOwnerProbeError.expected }
    }
    func setTextForced(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        calls.append("forced:\(contextId):\(blockId)")
        texts.append(middlewareString)
    }
    func setStyle(contextId: String, blockId: String, style: Style) async throws {
        calls.append("style:\(contextId):\(blockId)")
    }
    func split(contextId: String, blockId: String, range: NSRange, style: Style, mode: SplitMode) async throws -> String {
        calls.append("split:\(contextId):\(blockId)")
        ranges.append(range)
        return "new-block"
    }
    func merge(contextId: String, firstBlockId: String, secondBlockId: String) async throws {
        calls.append("merge:\(contextId):\(firstBlockId):\(secondBlockId)")
    }
    func checked(contextId: String, blockId: String, newValue: Bool) async throws {
        calls.append("checked:\(contextId):\(blockId):\(newValue)")
    }
    func setTextIcon(contextId: String, blockId: String, imageObjectId: String, emojiUnicode: String) async throws {
        calls.append("icon:\(contextId):\(blockId):\(imageObjectId):\(emojiUnicode)")
    }
    func refresh(contextId: String) async { calls.append("refresh:\(contextId)") }
    func setStyle(contextId: String, blockId: String) async {
        if holdPublication { await gate?.hold() }
        calls.append("event:\(contextId):\(blockId)")
    }
    func setToggled(contextId: String, blockId: String) async {
        calls.append("toggle:\(contextId):\(blockId)")
    }
    func setText(contextId: String, blockId: String, text: MiddlewareString) async {
        calls.append("event-text:\(contextId):\(blockId)")
    }
    func setLoadingState(contextId: String, blockId: String) async {
        calls.append("loading:\(contextId):\(blockId)")
    }
}
