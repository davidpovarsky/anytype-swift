import Foundation
import Services
import Testing
@testable import Anytype

@Suite
@MainActor
struct PreparedEditorLifetimeTests {
    @Test
    func observedPermissionLossCannotRenewTheCapturedLifetime() throws {
        let document = LifetimeTestDocument()
        let owner = try makeOwner(document)
        document.editorWriteLifetime.invalidate()
        document.mockPermissions.canEditBlocks = false
        document.mockPermissions.canEditBlocks = true
        #expect(owner.isRetired)
        let rejected = failure { try owner.validateOwnership() }
        #expect(rejected == .rejected(.retired))
        let fresh = try makeOwner(document)
        #expect(!fresh.isRetired)
    }

    @Test
    func closedThenReopenedDocumentCannotRenewTheCapturedLifetime() throws {
        let document = LifetimeTestDocument()
        let owner = try makeOwner(document)
        document.editorWriteLifetime.invalidate()
        document.mockIsOpened = false
        document.mockIsOpened = true
        let rejected = failure { try owner.validateOwnership() }
        #expect(rejected == .rejected(.retired))
        #expect(document.isOpened)
    }

    @Test
    func replacingTheLifetimeSourceIsRejected() throws {
        let document = LifetimeTestDocument()
        let owner = try makeOwner(document)
        document.editorWriteLifetime = EditorDocumentWriteLifetime()
        let rejected = failure { try owner.validateOwnership() }
        #expect(rejected == .rejected(.retired))
    }

    @Test
    func registrationCannotMissAnEarlierInvalidation() throws {
        let lifetime = EditorDocumentWriteLifetime()
        let token = try #require(lifetime.token())
        let counter = LifetimeCallbackCounter()
        lifetime.invalidate()
        let observation = lifetime.observe(token) { counter.increment() }
        #expect(counter.value == 1 && !lifetime.isCurrent(token))
        lifetime.invalidate()
        #expect(counter.value == 1)
        observation.cancel()
    }

    @Test
    func explicitRetirementDoesNotInvalidateAnotherOwnerOfTheSameDocument() throws {
        let document = LifetimeTestDocument()
        let first = try makeOwner(document)
        let second = try makeOwner(document)
        first.retire()
        try second.validateOwnership()
        #expect(first.isRetired && !second.isRetired && document.isOpened)
    }

    @Test
    func admittedWriteCompletionAfterRevocationIsReportedWithoutRollback() async throws {
        let document = LifetimeTestDocument()
        var drains = 0
        let owner = try EditorDocumentWriteOwner(
            data: data(document), lifetimeDocument: document, onDrained: { drains += 1 }
        )
        let gate = LifetimeAppleGate()
        let service = LifetimeAppleProbe(gate: gate)
        let writer = DocumentOwnedTextService(owner: owner, service: service)
        let operation = Task {
            try await writer.setText(contextId: "owned", blockId: "a", middlewareString: .init(text: "שלום"))
        }
        await gate.waitForEntry()
        document.editorWriteLifetime.invalidate()
        #expect(owner.isRetired && owner.pendingOperationCount == 1 && drains == 0)
        await gate.release()
        do {
            try await operation.value
            Issue.record("Revoked write ownership was returned as success")
        } catch {
            #expect(error as? EditorDocumentWriteError == .completedWithoutOwnership(.retired))
        }
        let calls = await service.calls
        #expect(calls == ["text"] && owner.isDrained && drains == 1)
    }

    @Test
    func alreadyAdmittedPublicationDrainsAndSubsequentPublicationIsRefused() async throws {
        let document = LifetimeTestDocument()
        var drains = 0
        let owner = try EditorDocumentWriteOwner(
            data: data(document), lifetimeDocument: document, onDrained: { drains += 1 }
        )
        let gate = LifetimeAppleGate()
        let target = LifetimeAppleProbe(gate: gate, holdPublication: true)
        let publisher = DocumentOwnedLocalEventPublisher(owner: owner, publisher: target)
        let operation = Task { await publisher.setStyle(contextId: "owned", blockId: "a") }
        await gate.waitForEntry()
        document.editorWriteLifetime.invalidate()
        #expect(owner.isRetired && owner.pendingOperationCount == 1)
        await gate.release()
        await operation.value
        await publisher.setText(contextId: "owned", blockId: "a", text: .init(text: "מאוחר"))
        let calls = await target.calls
        #expect(calls == ["event-style"] && owner.isDrained && drains == 1)
    }

    @Test
    func independentHostLifetimeRetiresOnlyItsOwnOwner() throws {
        let document = LifetimeTestDocument()
        let hostLifetime = EditorDocumentWriteLifetime()
        let first = try EditorDocumentWriteOwner(
            data: data(document), lifetimeDocument: document, sessionLifetime: hostLifetime
        )
        let second = try makeOwner(document)
        hostLifetime.invalidate()
        let rejected = failure { try first.validateOwnership() }
        #expect(rejected == .rejected(.retired))
        try second.validateOwnership()
        #expect(!second.isRetired && document.isOpened)
    }

    private func failure(_ operation: () throws -> Void) -> EditorDocumentWriteError? {
        do { try operation(); return nil }
        catch { return error as? EditorDocumentWriteError }
    }

    private func data(_ document: LifetimeTestDocument) -> EditorPageObject {
        .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode)
    }

    private func makeOwner(_ document: LifetimeTestDocument) throws -> EditorDocumentWriteOwner {
        try EditorDocumentWriteOwner(data: data(document), lifetimeDocument: document)
    }
}

/// An explicit original-document test boundary; BaseDocument's actual close and
/// permission mutation hooks are exercised separately by the source-bound driver.
private final class LifetimeTestDocument: MockBaseDocument, EditorDocumentWriteLifetimeProviding, @unchecked Sendable {
    var editorWriteLifetime = EditorDocumentWriteLifetime()

    init() {
        super.init(objectId: "owned", details: nil)
        mockSpaceId = "owned-space"
        mockMode = .handling
        mockPermissions.canEditBlocks = true
    }
}

private final class LifetimeCallbackCounter: @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0
    func increment() { lock.lock(); count += 1; lock.unlock() }
    var value: Int { lock.lock(); defer { lock.unlock() }; return count }
}

private actor LifetimeAppleGate {
    private var entered = false
    private var released = false
    private var waiters: [CheckedContinuation<Void, Never>] = []
    private var pending: [CheckedContinuation<Void, Never>] = []
    func hold() async {
        entered = true
        let observers = waiters; waiters = []
        for observer in observers { observer.resume() }
        if !released { await withCheckedContinuation { pending.append($0) } }
    }
    func waitForEntry() async {
        if entered { return }
        await withCheckedContinuation { waiters.append($0) }
    }
    func release() {
        released = true
        let observers = pending; pending = []
        for observer in observers { observer.resume() }
    }
}

private actor LifetimeAppleProbe: TextServiceProtocol, EditorLocalEventPublishing {
    let gate: LifetimeAppleGate
    let holdPublication: Bool
    private(set) var calls: [String] = []

    init(gate: LifetimeAppleGate, holdPublication: Bool = false) {
        self.gate = gate
        self.holdPublication = holdPublication
    }
    func setText(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        await gate.hold()
        calls.append("text")
    }
    func setTextForced(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws { calls.append("forced") }
    func setStyle(contextId: String, blockId: String, style: Style) async throws { calls.append("style") }
    func split(contextId: String, blockId: String, range: NSRange, style: Style, mode: SplitMode) async throws -> String {
        calls.append("split")
        return "created"
    }
    func merge(contextId: String, firstBlockId: String, secondBlockId: String) async throws { calls.append("merge") }
    func checked(contextId: String, blockId: String, newValue: Bool) async throws { calls.append("checked") }
    func setTextIcon(contextId: String, blockId: String, imageObjectId: String, emojiUnicode: String) async throws { calls.append("icon") }
    func refresh(contextId: String) async { calls.append("refresh") }
    func setStyle(contextId: String, blockId: String) async {
        if holdPublication { await gate.hold() }
        calls.append("event-style")
    }
    func setToggled(contextId: String, blockId: String) async { calls.append("toggle") }
    func setText(contextId: String, blockId: String, text: MiddlewareString) async { calls.append("event-text") }
    func setLoadingState(contextId: String, blockId: String) async { calls.append("loading") }
}
