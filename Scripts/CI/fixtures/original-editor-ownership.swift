import Foundation

final class OwnershipDocumentProbe: BaseDocumentProtocol, @unchecked Sendable {
    private struct State {
        var object: String
        var space: String
        var mode: DocumentMode
        var opened = true
        var locked = false
        var editable = true
    }
    private let lock = NSLock()
    private var state: State
    let lifecycle = DocumentLifecycleProbe()
    let infoContainer: any InfoContainerProtocol = FixtureInfo()
    let detailsStorage = ObjectDetailsStorage()
    init(object: String = "owned", space: String = "owned-space", mode: DocumentMode = .handling) {
        state = State(object: object, space: space, mode: mode)
    }
    private func read<Value>(_ body: (State) -> Value) -> Value {
        lock.lock(); defer { lock.unlock() }; return body(state)
    }
    func change(object: String? = nil, space: String? = nil, mode: DocumentMode? = nil,
                opened: Bool? = nil, locked: Bool? = nil, editable: Bool? = nil) {
        lock.lock(); defer { lock.unlock() }
        if let object { state.object = object }
        if let space { state.space = space }
        if let mode { state.mode = mode }
        if let opened { state.opened = opened }
        if let locked { state.locked = locked }
        if let editable { state.editable = editable }
    }
    var objectId: String { read { $0.object } }
    var spaceId: String { read { $0.space } }
    var mode: DocumentMode { read { $0.mode } }
    var isOpened: Bool { read { $0.opened } }
    var isLocked: Bool { read { $0.locked } }
    var permissions: ObjectPermissions { read { state in
        var value = ObjectPermissions(); value.canEditBlocks = state.editable; return value
    } }
    var children: [BlockInformation] { [] }
    var parsedProperties: ParsedProperties { ParsedProperties() }
    var isEmpty: Bool { false }
    var details: ObjectDetails? { nil }
    var syncStatus: SpaceSyncStatus? { nil }
    var syncPublisher: AnyPublisher<[BaseDocumentUpdate], Never> { AnyPublisher() }
    func subscibeFor(update: [BaseDocumentUpdate]) -> AnyPublisher<[BaseDocumentUpdate], Never> { AnyPublisher() }
    @MainActor func open() async throws { await lifecycle.record("open") }
    @MainActor func update() async throws { await lifecycle.record("update") }
    @MainActor func close() async throws { await lifecycle.record("close") }
}

actor OwnershipGate {
    private var entered = false
    private var released = false
    private var waiters: [CheckedContinuation<Void, Never>] = []
    private var pending: [CheckedContinuation<Void, Never>] = []
    func hold() async {
        entered = true
        let notices = waiters; waiters = []
        for notice in notices { notice.resume() }
        if !released { await withCheckedContinuation { pending.append($0) } }
    }
    func waitForEntry() async {
        if entered { return }
        await withCheckedContinuation { waiters.append($0) }
    }
    func release() {
        released = true
        let values = pending; pending = []
        for value in values { value.resume() }
    }
}

final class HeldOwnershipTextService: TextServiceProtocol {
    let gate: OwnershipGate
    let target: TextProbe
    init(gate: OwnershipGate, target: TextProbe) { self.gate = gate; self.target = target }
    func setText(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        await gate.hold()
        try await target.setText(contextId: contextId, blockId: blockId, middlewareString: middlewareString)
    }
    func setTextForced(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        try await target.setTextForced(contextId: contextId, blockId: blockId, middlewareString: middlewareString)
    }
    func setStyle(contextId: String, blockId: String, style: Style) async throws {
        try await target.setStyle(contextId: contextId, blockId: blockId, style: style)
    }
    func split(contextId: String, blockId: String, range: NSRange, style: Style, mode: SplitMode) async throws -> String {
        try await target.split(contextId: contextId, blockId: blockId, range: range, style: style, mode: mode)
    }
    func merge(contextId: String, firstBlockId: String, secondBlockId: String) async throws {
        try await target.merge(contextId: contextId, firstBlockId: firstBlockId, secondBlockId: secondBlockId)
    }
    func checked(contextId: String, blockId: String, newValue: Bool) async throws {
        try await target.checked(contextId: contextId, blockId: blockId, newValue: newValue)
    }
    func setTextIcon(contextId: String, blockId: String, imageObjectId: String, emojiUnicode: String) async throws {
        try await target.setTextIcon(contextId: contextId, blockId: blockId, imageObjectId: imageObjectId, emojiUnicode: emojiUnicode)
    }
}

struct HeldOwnershipPublication: EditorLocalEventPublishing {
    let gate: OwnershipGate
    let target: LocalPublisherProbe
    func setStyle(contextId: String, blockId: String) async {
        await gate.hold()
        await target.setStyle(contextId: contextId, blockId: blockId)
    }
    func refresh(contextId: String) async { await target.refresh(contextId: contextId) }
    func setToggled(contextId: String, blockId: String) async { await target.setToggled(contextId: contextId, blockId: blockId) }
    func setText(contextId: String, blockId: String, text: MiddlewareString) async {
        await target.setText(contextId: contextId, blockId: blockId, text: text)
    }
    func setLoadingState(contextId: String, blockId: String) async {
        await target.setLoadingState(contextId: contextId, blockId: blockId)
    }
}

@MainActor
private func ownershipData(_ document: OwnershipDocumentProbe) -> EditorPageObject {
    .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode)
}

@MainActor
private func ownerFailure(_ operation: () async throws -> Void) async -> EditorDocumentWriteError? {
    do { try await operation(); return nil }
    catch { return error as? EditorDocumentWriteError }
}

@main
struct OriginalEditorOwnershipFixture {
    @MainActor static func main() async throws {
        let result = BoundaryChecks()
        let document = OwnershipDocumentProbe()
        let owner = try EditorDocumentWriteOwner(data: ownershipData(document), document: document)
        let target = TextProbe()
        let writer = DocumentOwnedTextService(owner: owner, service: target)
        let body = MiddlewareString(text: "שלום English 👩🏽‍💻")
        let range = NSRange(location: 2, length: "👩🏽‍💻".utf16.count)
        try await writer.setText(contextId: "owned", blockId: "a", middlewareString: body)
        try await writer.setTextForced(contextId: "owned", blockId: "b", middlewareString: body)
        try await writer.setStyle(contextId: "owned", blockId: "a", style: .quote)
        let newBlock = try await writer.split(contextId: "owned", blockId: "a", range: range, style: .quote, mode: .fixture)
        try await writer.merge(contextId: "owned", firstBlockId: "a", secondBlockId: "b")
        try await writer.checked(contextId: "owned", blockId: "a", newValue: true)
        try await writer.setTextIcon(contextId: "owned", blockId: "a", imageObjectId: "image", emojiUnicode: "📖")
        let calls = await target.snapshot()
        result.expect(calls.map(\.operation) == ["text", "forced", "style", "split", "merge", "checked", "icon"],
                      "all_seven_original_text_operations_forwarded")
        result.expect(calls.allSatisfy { $0.context == "owned" } && calls[0].body?.text == body.text
                      && calls[3].range == range && newBlock == "injected-created-block",
                      "owned_payload_result_and_utf16_unchanged")
        result.expect(owner.isDrained && owner.pendingOperationCount == 0 && !owner.isRetired,
                      "successful_operations_release_their_leases")
        let foreign = await ownerFailure {
            try await writer.setText(contextId: "other", blockId: "a", middlewareString: body)
        }
        let afterForeign = await target.snapshot()
        result.expect(foreign == .rejected(.wrongContext) && afterForeign.count == 7,
                      "foreign_context_refused_before_original_service")
        let mutations: [(String, @MainActor (OwnershipDocumentProbe) -> Void, EditorDocumentWriteRejection)] = [
            ("object_changed", { $0.change(object: "other") }, .documentChanged),
            ("space_changed", { $0.change(space: "other") }, .documentChanged),
            ("mode_changed", { $0.change(mode: .preview) }, .documentChanged),
            ("document_closed", { $0.change(opened: false) }, .documentChanged),
            ("permission_revoked", { $0.change(editable: false) }, .notEditable),
            ("locked_with_stale_permission", { $0.change(locked: true) }, .notEditable),
        ]
        for (name, mutate, expected) in mutations {
            let current = OwnershipDocumentProbe()
            let currentOwner = try EditorDocumentWriteOwner(data: ownershipData(current), document: current)
            let destination = TextProbe()
            let currentWriter = DocumentOwnedTextService(owner: currentOwner, service: destination)
            mutate(current)
            let error = await ownerFailure {
                try await currentWriter.setText(contextId: "owned", blockId: "a", middlewareString: body)
            }
            let recorded = await destination.snapshot()
            result.expect(error == .rejected(expected) && recorded.isEmpty, name + "_before_dispatch")
        }
        for (name, mode) in [("preview", DocumentMode.preview), ("history", .version("revision"))] {
            let current = OwnershipDocumentProbe(mode: mode)
            let currentOwner = try EditorDocumentWriteOwner(data: ownershipData(current), document: current)
            let destination = TextProbe()
            let currentWriter = DocumentOwnedTextService(owner: currentOwner, service: destination)
            let error = await ownerFailure {
                try await currentWriter.setText(contextId: "owned", blockId: "a", middlewareString: body)
            }
            let recorded = await destination.snapshot()
            result.expect(error == .rejected(.notHandling) && recorded.isEmpty, name + "_write_refused")
        }
        let unicode = OwnershipDocumentProbe(object: "doc-é")
        let unicodeOwner = try EditorDocumentWriteOwner(data: ownershipData(unicode), document: unicode)
        let unicodeTarget = TextProbe()
        let unicodeWriter = DocumentOwnedTextService(owner: unicodeOwner, service: unicodeTarget)
        let unicodeError = await ownerFailure {
            try await unicodeWriter.setText(contextId: "doc-e\u{301}", blockId: "a", middlewareString: body)
        }
        let unicodeCalls = await unicodeTarget.snapshot()
        result.expect(unicodeError == .rejected(.wrongContext) && unicodeCalls.isEmpty, "context_is_byte_exact")
        let versioned = OwnershipDocumentProbe(mode: .version("é"))
        let versionOwner = try EditorDocumentWriteOwner(data: ownershipData(versioned), document: versioned)
        let versionEvents = LocalPublisherProbe()
        let versionPublisher = DocumentOwnedLocalEventPublisher(owner: versionOwner, publisher: versionEvents)
        versioned.change(mode: .version("e\u{301}"))
        await versionPublisher.setToggled(contextId: "owned", blockId: "a")
        result.expect(await versionEvents.snapshot().isEmpty, "history_mode_revision_is_byte_exact")

        var drainCalls = 0
        let heldDoc = OwnershipDocumentProbe()
        let heldOwner = try EditorDocumentWriteOwner(data: ownershipData(heldDoc), document: heldDoc, onDrained: { drainCalls += 1 })
        let gate = OwnershipGate(), heldTarget = TextProbe()
        let heldWriter = DocumentOwnedTextService(owner: heldOwner, service: HeldOwnershipTextService(gate: gate, target: heldTarget))
        let inFlight = Task { try await heldWriter.setText(contextId: "owned", blockId: "a", middlewareString: body) }
        await gate.waitForEntry()
        heldOwner.retire(); heldOwner.retire()
        result.expect(heldOwner.isRetired && heldOwner.pendingOperationCount == 1 && !heldOwner.isDrained && drainCalls == 0,
                      "retirement_retains_admitted_write_until_drain")
        let blocked = await ownerFailure { try await heldWriter.checked(contextId: "owned", blockId: "a", newValue: true) }
        result.expect(blocked == .rejected(.retired), "retired_owner_refuses_new_dispatch")
        await gate.release()
        let heldError = await ownerFailure { try await inFlight.value }
        let applied = await heldTarget.snapshot()
        result.expect(heldError == .completedWithoutOwnership(.retired) && applied.count == 1
                      && applied[0].body?.text == body.text, "completed_service_write_is_not_claimed_rolled_back")
        result.expect(heldOwner.isDrained && drainCalls == 1, "drain_callback_once_after_write_completion")
        heldOwner.retire()
        result.expect(drainCalls == 1, "duplicate_retirement_does_not_repeat_drain")
        result.expect(await heldDoc.lifecycle.snapshot().isEmpty, "retirement_never_opens_updates_or_closes_document")

        let failedDoc = OwnershipDocumentProbe()
        let failedOwner = try EditorDocumentWriteOwner(data: ownershipData(failedDoc), document: failedDoc)
        let failedTarget = TextProbe(failure: .deliberate)
        let failedWriter = DocumentOwnedTextService(owner: failedOwner, service: failedTarget)
        var originalError = false
        do { try await failedWriter.setStyle(contextId: "owned", blockId: "a", style: .text) }
        catch { originalError = (error as? TextProbeFailure) == .deliberate }
        result.expect(originalError && failedOwner.isDrained, "original_service_error_preserved_and_lease_released")

        let cancelledDoc = OwnershipDocumentProbe()
        let cancelledOwner = try EditorDocumentWriteOwner(data: ownershipData(cancelledDoc), document: cancelledDoc)
        let cancelledTarget = TextProbe()
        let cancelledWriter = DocumentOwnedTextService(owner: cancelledOwner, service: cancelledTarget)
        let cancelledTask = Task { try await cancelledWriter.setText(contextId: "owned", blockId: "a", middlewareString: body) }
        cancelledTask.cancel()
        let cancelledError = await ownerFailure { try await cancelledTask.value }
        let notDispatched = await cancelledTarget.snapshot()
        result.expect(cancelledError == .rejected(.cancelled) && notDispatched.isEmpty,
                      "pre_dispatch_cancellation_does_not_call_service")

        let duringDoc = OwnershipDocumentProbe()
        let duringOwner = try EditorDocumentWriteOwner(data: ownershipData(duringDoc), document: duringDoc)
        let duringGate = OwnershipGate(), duringTarget = TextProbe()
        let duringWriter = DocumentOwnedTextService(owner: duringOwner, service: HeldOwnershipTextService(gate: duringGate, target: duringTarget))
        let duringTask = Task { try await duringWriter.setText(contextId: "owned", blockId: "a", middlewareString: body) }
        await duringGate.waitForEntry()
        duringTask.cancel()
        await duringGate.release()
        let duringError = await ownerFailure { try await duringTask.value }
        let duringApplied = await duringTarget.snapshot()
        result.expect(duringError == .completedWithoutOwnership(.cancelled) && duringApplied.count == 1
                      && duringOwner.isDrained, "cancelled_after_actual_completion_not_retried_or_rolled_back")

        let permissionDoc = OwnershipDocumentProbe()
        let permissionOwner = try EditorDocumentWriteOwner(data: ownershipData(permissionDoc), document: permissionDoc)
        let permissionGate = OwnershipGate(), permissionTarget = TextProbe()
        let permissionWriter = DocumentOwnedTextService(owner: permissionOwner,
            service: HeldOwnershipTextService(gate: permissionGate, target: permissionTarget))
        let permissionTask = Task { try await permissionWriter.setText(contextId: "owned", blockId: "a", middlewareString: body) }
        await permissionGate.waitForEntry()
        permissionDoc.change(editable: false)
        await permissionGate.release()
        let permissionError = await ownerFailure { try await permissionTask.value }
        let permissionApplied = await permissionTarget.snapshot()
        result.expect(permissionError == .completedWithoutOwnership(.notEditable) && permissionApplied.count == 1,
                      "permission_loss_after_completion_has_distinct_error")

        let eventDoc = OwnershipDocumentProbe()
        let eventOwner = try EditorDocumentWriteOwner(data: ownershipData(eventDoc), document: eventDoc)
        let eventTarget = LocalPublisherProbe()
        let publisher = DocumentOwnedLocalEventPublisher(owner: eventOwner, publisher: eventTarget)
        await publisher.refresh(contextId: "owned")
        await publisher.setStyle(contextId: "owned", blockId: "a")
        await publisher.setToggled(contextId: "owned", blockId: "a")
        await publisher.setText(contextId: "owned", blockId: "a", text: body)
        await publisher.setLoadingState(contextId: "owned", blockId: "a")
        result.expect(await eventTarget.snapshot().count == 5, "all_original_event_types_forward_when_owned")
        await publisher.refresh(contextId: "foreign")
        eventOwner.retire()
        await publisher.setText(contextId: "owned", blockId: "a", text: body)
        result.expect(await eventTarget.snapshot().count == 5, "foreign_and_new_retired_publications_are_dropped")

        let previewDoc = OwnershipDocumentProbe(mode: .preview)
        previewDoc.change(editable: false)
        let previewOwner = try EditorDocumentWriteOwner(data: ownershipData(previewDoc), document: previewDoc)
        let previewEvents = LocalPublisherProbe()
        let previewPublisher = DocumentOwnedLocalEventPublisher(owner: previewOwner, publisher: previewEvents)
        await previewPublisher.setToggled(contextId: "owned", blockId: "a")
        await previewPublisher.setText(contextId: "owned", blockId: "a", text: body)
        let previewCalls = await previewEvents.snapshot()
        result.expect(previewCalls.map(\.operation) == ["toggle"], "readonly_presentation_toggle_preserved_without_text_edit")

        var publicationDrains = 0
        let publicationDoc = OwnershipDocumentProbe()
        let publicationOwner = try EditorDocumentWriteOwner(data: ownershipData(publicationDoc), document: publicationDoc,
            onDrained: { publicationDrains += 1 })
        let publicationGate = OwnershipGate(), publicationTarget = LocalPublisherProbe()
        let heldPublisher = DocumentOwnedLocalEventPublisher(owner: publicationOwner,
            publisher: HeldOwnershipPublication(gate: publicationGate, target: publicationTarget))
        let publishing = Task { await heldPublisher.setStyle(contextId: "owned", blockId: "a") }
        await publicationGate.waitForEntry()
        publicationOwner.retire()
        result.expect(publicationOwner.pendingOperationCount == 1 && publicationDrains == 0,
                      "admitted_publication_retained_during_retirement")
        await publicationGate.release(); await publishing.value
        let publishedAfterAdmission = await publicationTarget.snapshot()
        result.expect(publishedAfterAdmission.count == 1 && publicationOwner.isDrained && publicationDrains == 1,
                      "publication_drain_reports_actual_delivery_without_rollback")

        let otherDoc = OwnershipDocumentProbe(object: "other")
        let otherOwner = try EditorDocumentWriteOwner(data: ownershipData(otherDoc), document: otherDoc)
        let sharedTarget = TextProbe()
        let firstShared = DocumentOwnedTextService(owner: owner, service: sharedTarget)
        let secondShared = DocumentOwnedTextService(owner: otherOwner, service: sharedTarget)
        owner.retire()
        let firstError = await ownerFailure { try await firstShared.setText(contextId: "owned", blockId: "same", middlewareString: body) }
        try await secondShared.setText(contextId: "other", blockId: "same", middlewareString: body)
        let secondError = await ownerFailure { try await secondShared.setText(contextId: "owned", blockId: "same", middlewareString: body) }
        let separateCalls = await sharedTarget.snapshot()
        result.expect(firstError == .rejected(.retired) && secondError == .rejected(.wrongContext)
                      && separateCalls.count == 1 && separateCalls[0].context == "other", "two_owners_remain_independent_with_shared_service")
        let data = try JSONEncoder().encode(result.checks)
        print(String(decoding: data, as: UTF8.self))
        if result.checks.contains(where: { !$0.passed }) { throw BoundaryFixtureError.failed }
    }
}
