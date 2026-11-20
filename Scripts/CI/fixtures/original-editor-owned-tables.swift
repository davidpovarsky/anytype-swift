import Foundation

// Explicit protobuf boundary values; the original BlockPosition and BlocksSortType
// declarations and complete table protocol are compiled separately, unchanged.
public extension Anytype_Model_Block {
    enum Position: Sendable { case none, top, bottom, left, right, inner, replace, unrecognized }
}
public extension Anytype_Model_Block.Content {
    enum Dataview {
        public enum Sort {
            public enum TypeEnum: Sendable { case asc, desc }
        }
    }
}

struct OwnedTableInvocation: Equatable, Sendable {
    let operation: String
    let context: String
    var targets: [String] = []
    var dropTarget: String? = nil
    var position: String? = nil
    var rows: Int? = nil
    var columns: Int? = nil
    var sort: String? = nil
}

enum OwnedTableProbeError: Error, Equatable, Sendable { case deliberate }

actor OwnedTableServiceProbe: BlockTableServiceProtocol {
    let label: String
    let gate: OwnershipGate?
    let fails: Bool
    private var calls: [OwnedTableInvocation] = []

    init(label: String, gate: OwnershipGate? = nil, fails: Bool = false) {
        self.label = label
        self.gate = gate
        self.fails = fails
    }

    func snapshot() -> [OwnedTableInvocation] { calls }

    private func record(_ call: OwnedTableInvocation) async throws {
        await gate?.hold()
        calls.append(call)
        if fails { throw OwnedTableProbeError.deliberate }
    }

    func createTable(contextId: String, targetId: String, position: BlockPosition,
                     rowsCount: Int, columnsCount: Int) async throws -> String {
        try await record(.init(operation: "create", context: contextId, targets: [targetId],
            position: String(describing: position), rows: rowsCount, columns: columnsCount))
        return label + "-original-table-id"
    }
    func rowListFill(contextId: String, targetIds: [String]) async throws {
        try await record(.init(operation: "fill", context: contextId, targets: targetIds))
    }
    func insertColumn(contextId: String, targetId: String, position: BlockPosition) async throws {
        try await record(.init(operation: "insert-column", context: contextId, targets: [targetId], position: String(describing: position)))
    }
    func deleteColumn(contextId: String, targetId: String) async throws {
        try await record(.init(operation: "delete-column", context: contextId, targets: [targetId]))
    }
    func columnDuplicate(contextId: String, targetId: String) async throws {
        try await record(.init(operation: "duplicate-column", context: contextId, targets: [targetId]))
    }
    func columnSort(contextId: String, columnId: String, blocksSortType: BlocksSortType) async throws {
        try await record(.init(operation: "sort-column", context: contextId, targets: [columnId], sort: String(describing: blocksSortType)))
    }
    func columnMove(contextId: String, targetId: String, dropTargetID: String, position: BlockPosition) async throws {
        try await record(.init(operation: "move-column", context: contextId, targets: [targetId],
            dropTarget: dropTargetID, position: String(describing: position)))
    }
    func insertRow(contextId: String, targetId: String, position: BlockPosition) async throws {
        try await record(.init(operation: "insert-row", context: contextId, targets: [targetId], position: String(describing: position)))
    }
    func deleteRow(contextId: String, targetId: String) async throws {
        try await record(.init(operation: "delete-row", context: contextId, targets: [targetId]))
    }
    func rowDuplicate(contextId: String, targetId: String) async throws {
        try await record(.init(operation: "duplicate-row", context: contextId, targets: [targetId]))
    }
    func rowMove(contextId: String, targetId: String, dropTargetID: String, position: BlockPosition) async throws {
        try await record(.init(operation: "move-row", context: contextId, targets: [targetId],
            dropTarget: dropTargetID, position: String(describing: position)))
    }
    func clearContents(contextId: String, blockIds: [String]) async throws {
        try await record(.init(operation: "clear-contents", context: contextId, targets: blockIds))
    }
    func clearStyle(contextId: String, blocksIds: [String]) async throws {
        try await record(.init(operation: "clear-style", context: contextId, targets: blocksIds))
    }
}

struct FixtureTableServices: Sendable {
    let action = OwnedTableServiceProbe(label: "action")
    let builder = OwnedTableServiceProbe(label: "builder")
    let simple = OwnedTableServiceProbe(label: "simple")
}

// BEGIN_OWNED_TABLE_CONTROLS
// Appended into the same executed fixture as the preserved original lifetime controls.
@MainActor
private func exerciseOwnedTableServices(_ checks: BoundaryChecks) async throws {
    let document = LifetimeDocumentProbe()
    let owner = try EditorDocumentWriteOwner(data: lifetimeData(document), lifetimeDocument: document)
    let original = OwnedTableServiceProbe(label: "forward")
    let table = DocumentOwnedBlockTableService(owner: owner, service: original)
    let created = try await table.createTable(contextId: "owned", targetId: "first", position: .inner, rowsCount: 3, columnsCount: 5)
    try await table.rowListFill(contextId: "owned", targetIds: ["r2", "r1", "r2"])
    try await table.insertColumn(contextId: "owned", targetId: "c1", position: .left)
    try await table.deleteColumn(contextId: "owned", targetId: "c2")
    try await table.columnDuplicate(contextId: "owned", targetId: "c3")
    try await table.columnSort(contextId: "owned", columnId: "c4", blocksSortType: .desc)
    try await table.columnMove(contextId: "owned", targetId: "c5", dropTargetID: "c6", position: .right)
    try await table.insertRow(contextId: "owned", targetId: "r3", position: .top)
    try await table.deleteRow(contextId: "owned", targetId: "r4")
    try await table.rowDuplicate(contextId: "owned", targetId: "r5")
    try await table.rowMove(contextId: "owned", targetId: "r6", dropTargetID: "r7", position: .bottom)
    try await table.clearContents(contextId: "owned", blockIds: ["a2", "a1", "a2"])
    try await table.clearStyle(contextId: "owned", blocksIds: ["b2", "b1"])
    let expected: [OwnedTableInvocation] = [
        .init(operation: "create", context: "owned", targets: ["first"], position: "inner", rows: 3, columns: 5),
        .init(operation: "fill", context: "owned", targets: ["r2", "r1", "r2"]),
        .init(operation: "insert-column", context: "owned", targets: ["c1"], position: "left"),
        .init(operation: "delete-column", context: "owned", targets: ["c2"]),
        .init(operation: "duplicate-column", context: "owned", targets: ["c3"]),
        .init(operation: "sort-column", context: "owned", targets: ["c4"], sort: "desc"),
        .init(operation: "move-column", context: "owned", targets: ["c5"], dropTarget: "c6", position: "right"),
        .init(operation: "insert-row", context: "owned", targets: ["r3"], position: "top"),
        .init(operation: "delete-row", context: "owned", targets: ["r4"]),
        .init(operation: "duplicate-row", context: "owned", targets: ["r5"]),
        .init(operation: "move-row", context: "owned", targets: ["r6"], dropTarget: "r7", position: "bottom"),
        .init(operation: "clear-contents", context: "owned", targets: ["a2", "a1", "a2"]),
        .init(operation: "clear-style", context: "owned", targets: ["b2", "b1"])
    ]
    let forwarded = await original.snapshot()
    checks.expect(forwarded.count == 13 && owner.pendingOperationCount == 0, "table_all_thirteen_original_methods_finish_their_leases")
    checks.expect(created == "forward-original-table-id", "table_creation_returns_the_original_service_identity")
    for (index, call) in expected.enumerated() {
        checks.expect(index < forwarded.count && forwarded[index] == call, "table_exact_original_arguments_" + call.operation)
    }

    let foreign = await lifetimeFailure { try await table.deleteRow(contextId: "other", targetId: "r1") }
    let afterForeign = await original.snapshot()
    checks.expect(foreign == .rejected(.wrongContext) && afterForeign.count == 13, "table_foreign_context_is_refused_before_dispatch")

    let unicodeDocument = LifetimeDocumentProbe(object: "\u{e9}")
    let unicodeOwner = try EditorDocumentWriteOwner(data: lifetimeData(unicodeDocument), lifetimeDocument: unicodeDocument)
    let unicodeTarget = OwnedTableServiceProbe(label: "unicode")
    let unicodeTable = DocumentOwnedBlockTableService(owner: unicodeOwner, service: unicodeTarget)
    let unicodeError = await lifetimeFailure { try await unicodeTable.deleteRow(contextId: "e\u{301}", targetId: "row") }
    let unicodeCalls = await unicodeTarget.snapshot()
    checks.expect(unicodeError == .rejected(.wrongContext) && unicodeCalls.isEmpty, "table_context_preserves_exact_utf8_identity")

    let preview = LifetimeDocumentProbe(mode: .preview)
    let previewOwner = try EditorDocumentWriteOwner(data: lifetimeData(preview), lifetimeDocument: preview)
    let previewTarget = OwnedTableServiceProbe(label: "preview")
    let previewError = await lifetimeFailure {
        try await DocumentOwnedBlockTableService(owner: previewOwner, service: previewTarget).deleteRow(contextId: "owned", targetId: "row")
    }
    let previewCalls = await previewTarget.snapshot()
    checks.expect(previewError == .rejected(.notHandling) && previewCalls.isEmpty, "table_readonly_mode_cannot_mutate")

    let locked = LifetimeDocumentProbe()
    locked.isLocked = true
    let lockedOwner = try EditorDocumentWriteOwner(data: lifetimeData(locked), lifetimeDocument: locked)
    let lockedTarget = OwnedTableServiceProbe(label: "locked")
    let lockedError = await lifetimeFailure {
        try await DocumentOwnedBlockTableService(owner: lockedOwner, service: lockedTarget).deleteRow(contextId: "owned", targetId: "row")
    }
    let lockedCalls = await lockedTarget.snapshot()
    checks.expect(lockedError == .rejected(.notEditable) && lockedCalls.isEmpty, "table_locked_document_refuses_dispatch")

    let readonly = LifetimeDocumentProbe()
    _ = readonly.applyPermissionForFixture(false)
    let readonlyOwner = try EditorDocumentWriteOwner(data: lifetimeData(readonly), lifetimeDocument: readonly)
    let readonlyTarget = OwnedTableServiceProbe(label: "permission")
    let readonlyError = await lifetimeFailure {
        try await DocumentOwnedBlockTableService(owner: readonlyOwner, service: readonlyTarget).deleteRow(contextId: "owned", targetId: "row")
    }
    let readonlyCalls = await readonlyTarget.snapshot()
    checks.expect(readonlyError == .rejected(.notEditable) && readonlyCalls.isEmpty, "table_original_permission_refuses_dispatch")

    let heldDoc = LifetimeDocumentProbe()
    var drains = 0
    let heldOwner = try EditorDocumentWriteOwner(data: lifetimeData(heldDoc), lifetimeDocument: heldDoc, onDrained: { drains += 1 })
    let heldGate = OwnershipGate()
    let heldTarget = OwnedTableServiceProbe(label: "held", gate: heldGate)
    let heldTable = DocumentOwnedBlockTableService(owner: heldOwner, service: heldTarget)
    let heldOperation = Task { try await heldTable.createTable(contextId: "owned", targetId: "target", position: .bottom, rowsCount: 2, columnsCount: 4) }
    await heldGate.waitForEntry()
    heldOwner.retire()
    let duringCloseCount = heldOwner.pendingOperationCount
    await heldGate.release()
    let late = await lifetimeFailure { _ = try await heldOperation.value }
    let heldCalls = await heldTarget.snapshot()
    checks.expect(late == .completedWithoutOwnership(.retired) && heldCalls.count == 1
        && duringCloseCount == 1 && heldOwner.isDrained && drains == 1,
        "table_actual_admitted_creation_survives_retirement_with_explicit_late_outcome")
    let repeated = await lifetimeFailure { try await heldTable.deleteRow(contextId: "owned", targetId: "new") }
    let repeatCalls = await heldTarget.snapshot()
    checks.expect(repeated == .rejected(.retired) && repeatCalls.count == 1, "table_retirement_does_not_retry_or_admit_a_new_operation")

    let failingTarget = OwnedTableServiceProbe(label: "failure", fails: true)
    var originalError: OwnedTableProbeError?
    do { try await DocumentOwnedBlockTableService(owner: owner, service: failingTarget).clearContents(contextId: "owned", blockIds: ["a"]) }
    catch { originalError = error as? OwnedTableProbeError }
    let failureCalls = await failingTarget.snapshot()
    checks.expect(originalError == .deliberate && failureCalls.count == 1 && owner.pendingOperationCount == 0,
        "table_original_service_error_propagates_without_retry")

    let cancelledTarget = OwnedTableServiceProbe(label: "cancel-before")
    let cancelledTable = DocumentOwnedBlockTableService(owner: owner, service: cancelledTarget)
    let cancelledTask = Task {
        await lifetimeFailure { try await cancelledTable.deleteColumn(contextId: "owned", targetId: "c") }
    }
    cancelledTask.cancel()
    let cancelledError = await cancelledTask.value
    let cancelledCalls = await cancelledTarget.snapshot()
    checks.expect(cancelledError == .rejected(.cancelled) && cancelledCalls.isEmpty, "table_cancellation_before_dispatch_refuses_original_service")

    let cancelGate = OwnershipGate()
    let cancelTarget = OwnedTableServiceProbe(label: "cancel-after", gate: cancelGate)
    let cancelTable = DocumentOwnedBlockTableService(owner: owner, service: cancelTarget)
    let cancelAfter = Task {
        await lifetimeFailure { try await cancelTable.deleteColumn(contextId: "owned", targetId: "actual") }
    }
    await cancelGate.waitForEntry()
    cancelAfter.cancel()
    await cancelGate.release()
    let cancelAfterError = await cancelAfter.value
    let cancelAfterCalls = await cancelTarget.snapshot()
    checks.expect(cancelAfterError == .completedWithoutOwnership(.cancelled) && cancelAfterCalls.count == 1
        && owner.pendingOperationCount == 0, "table_cancellation_after_admission_does_not_claim_rollback")

    for mode in ["close", "permission"] {
        let abaDocument = LifetimeDocumentProbe()
        let abaOwner = try EditorDocumentWriteOwner(data: lifetimeData(abaDocument), lifetimeDocument: abaDocument)
        let abaGate = OwnershipGate()
        let abaTarget = OwnedTableServiceProbe(label: mode, gate: abaGate)
        let abaTable = DocumentOwnedBlockTableService(owner: abaOwner, service: abaTarget)
        let task = Task { try await abaTable.insertRow(contextId: "owned", targetId: "row", position: .bottom) }
        await abaGate.waitForEntry()
        if mode == "close" { try await abaDocument.close(); abaDocument.reopenForFixture() }
        else { _ = abaDocument.applyPermissionForFixture(false); _ = abaDocument.applyPermissionForFixture(true) }
        await abaGate.release()
        let outcome = await lifetimeFailure { try await task.value }
        let actual = await abaTarget.snapshot()
        checks.expect(outcome == .completedWithoutOwnership(.retired) && actual.count == 1 && abaOwner.isRetired,
            "table_" + mode + "_aba_keeps_the_actual_effect_and_refuses_renewed_ownership")
    }

    let targets = FixtureTableServices()
    let preparedDocument = LifetimeDocumentProbe()
    let prepared = try PreparedEditorPageSession(data: lifetimeData(preparedDocument), document: preparedDocument,
        textService: TextProbe(), services: fixtureServices(events: LocalPublisherProbe(), tableServices: targets))
    let selected: [(String, any BlockTableServiceProtocol, OwnedTableServiceProbe)] = [
        ("action", prepared.services.blockActionHandler.blockTableService, targets.action),
        ("builder", prepared.services.blockBuilder.tableService, targets.builder),
        ("simple", prepared.services.simpleTable.tableService, targets.simple)
    ]
    for (name, service, target) in selected {
        try await service.rowDuplicate(contextId: "owned", targetId: name)
        let actual = await target.snapshot()
        checks.expect(actual == [.init(operation: "duplicate-row", context: "owned", targets: [name])],
            "prepared_table_slot_preserves_its_own_original_service_" + name)
    }
    prepared.retire()
    var refused = 0
    for (_, service, target) in selected {
        let error = await lifetimeFailure { try await service.deleteRow(contextId: "owned", targetId: "late") }
        let actual = await target.snapshot()
        if error == .rejected(.retired) && actual.count == 1 { refused += 1 }
    }
    checks.expect(refused == 3 && prepared.owner.isDrained, "prepared_all_three_table_slots_share_the_same_host_retirement")

    let shared = LifetimeDocumentProbe()
    let first = try EditorDocumentWriteOwner(data: lifetimeData(shared), lifetimeDocument: shared)
    let second = try EditorDocumentWriteOwner(data: lifetimeData(shared), lifetimeDocument: shared)
    let sharedTarget = OwnedTableServiceProbe(label: "shared")
    first.retire()
    let firstError = await lifetimeFailure {
        try await DocumentOwnedBlockTableService(owner: first, service: sharedTarget).clearStyle(contextId: "owned", blocksIds: ["a"])
    }
    try await DocumentOwnedBlockTableService(owner: second, service: sharedTarget).clearStyle(contextId: "owned", blocksIds: ["b"])
    let sharedCalls = await sharedTarget.snapshot()
    checks.expect(firstError == .rejected(.retired) && sharedCalls == [.init(operation: "clear-style", context: "owned", targets: ["b"])]
        && !second.isRetired, "table_two_owners_share_the_service_without_sharing_retirement")
}
