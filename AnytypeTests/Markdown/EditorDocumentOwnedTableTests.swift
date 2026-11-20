import Foundation
import Services
import Testing
@testable import Anytype

@Suite
@MainActor
struct EditorDocumentOwnedTableTests {
    @Test
    func forwardsAllThirteenOriginalTableMethodsAndTheirResult() async throws {
        let document = OwnedTableTestDocument()
        let owner = try makeOwner(document)
        let target = OwnedTableAppleProbe()
        let service = DocumentOwnedBlockTableService(owner: owner, service: target)
        let created = try await service.createTable(contextId: "owned", targetId: "first", position: .inner, rowsCount: 3, columnsCount: 5)
        try await service.rowListFill(contextId: "owned", targetIds: ["r2", "r1", "r2"])
        try await service.insertColumn(contextId: "owned", targetId: "c1", position: .left)
        try await service.deleteColumn(contextId: "owned", targetId: "c2")
        try await service.columnDuplicate(contextId: "owned", targetId: "c3")
        try await service.columnSort(contextId: "owned", columnId: "c4", blocksSortType: .desc)
        try await service.columnMove(contextId: "owned", targetId: "c5", dropTargetID: "c6", position: .right)
        try await service.insertRow(contextId: "owned", targetId: "r3", position: .top)
        try await service.deleteRow(contextId: "owned", targetId: "r4")
        try await service.rowDuplicate(contextId: "owned", targetId: "r5")
        try await service.rowMove(contextId: "owned", targetId: "r6", dropTargetID: "r7", position: .bottom)
        try await service.clearContents(contextId: "owned", blockIds: ["a2", "a1", "a2"])
        try await service.clearStyle(contextId: "owned", blocksIds: ["b2", "b1"])
        let calls = await target.calls
        #expect(created == "original-table-id")
        #expect(calls == [
            ["create", "owned", "first", "inner", "3", "5"],
            ["fill", "owned", "r2", "r1", "r2"],
            ["insert-column", "owned", "c1", "left"],
            ["delete-column", "owned", "c2"],
            ["duplicate-column", "owned", "c3"],
            ["sort-column", "owned", "c4", "desc"],
            ["move-column", "owned", "c5", "c6", "right"],
            ["insert-row", "owned", "r3", "top"],
            ["delete-row", "owned", "r4"],
            ["duplicate-row", "owned", "r5"],
            ["move-row", "owned", "r6", "r7", "bottom"],
            ["clear-contents", "owned", "a2", "a1", "a2"],
            ["clear-style", "owned", "b2", "b1"]
        ])
        #expect(owner.pendingOperationCount == 0)
    }

    @Test
    func refusesForeignContextAndReadonlyModeBeforeTheOriginalService() async throws {
        let document = OwnedTableTestDocument()
        let owner = try makeOwner(document)
        let target = OwnedTableAppleProbe()
        let service = DocumentOwnedBlockTableService(owner: owner, service: target)
        let foreign = await failure { try await service.deleteRow(contextId: "other", targetId: "r") }
        #expect(foreign == .rejected(.wrongContext))
        let readonly = OwnedTableTestDocument()
        readonly.mockMode = .preview
        let readonlyOwner = try makeOwner(readonly)
        let readonlyError = await failure {
            try await DocumentOwnedBlockTableService(owner: readonlyOwner, service: target)
                .deleteRow(contextId: "owned", targetId: "r")
        }
        #expect(readonlyError == .rejected(.notHandling))
        let calls = await target.calls
        #expect(calls.isEmpty)
    }

    @Test
    func admittedCreationAfterCloseRevocationIsNotReportedAsRollback() async throws {
        let document = OwnedTableTestDocument()
        var drains = 0
        let owner = try EditorDocumentWriteOwner(
            data: data(document), lifetimeDocument: document, onDrained: { drains += 1 }
        )
        let gate = OwnedTableAppleGate()
        let target = OwnedTableAppleProbe(gate: gate)
        let service = DocumentOwnedBlockTableService(owner: owner, service: target)
        let operation = Task {
            try await service.createTable(contextId: "owned", targetId: "first", position: .bottom, rowsCount: 2, columnsCount: 4)
        }
        await gate.waitForEntry()
        let close = document.editorWriteLifetime.beginClosing()
        document.mockIsOpened = false
        document.mockIsOpened = true
        document.editorWriteLifetime.confirmOpened()
        #expect(document.editorWriteLifetime.token() == nil && owner.pendingOperationCount == 1)
        close.cancel()
        document.editorWriteLifetime.confirmOpened()
        await gate.release()
        let outcome = await failure { _ = try await operation.value }
        #expect(outcome == .completedWithoutOwnership(.retired))
        let calls = await target.calls
        #expect(calls == [["create", "owned", "first", "bottom", "2", "4"]])
        #expect(owner.isDrained && drains == 1)
        let later = await failure { try await service.deleteRow(contextId: "owned", targetId: "late") }
        #expect(later == .rejected(.retired))
        let finalCalls = await target.calls
        #expect(finalCalls.count == 1)
    }

    @Test
    func twoOwnersDoNotShareRetirementAuthority() async throws {
        let document = OwnedTableTestDocument()
        let first = try makeOwner(document)
        let second = try makeOwner(document)
        let target = OwnedTableAppleProbe()
        first.retire()
        let rejected = await failure {
            try await DocumentOwnedBlockTableService(owner: first, service: target)
                .clearStyle(contextId: "owned", blocksIds: ["first"])
        }
        try await DocumentOwnedBlockTableService(owner: second, service: target)
            .clearStyle(contextId: "owned", blocksIds: ["second"])
        let calls = await target.calls
        #expect(rejected == .rejected(.retired) && !second.isRetired)
        #expect(calls == [["clear-style", "owned", "second"]])
    }

    @Test
    func originalServiceErrorAndPredispatchCancellationAreNotRetried() async throws {
        let document = OwnedTableTestDocument()
        let owner = try makeOwner(document)
        let failing = OwnedTableAppleProbe(fails: true)
        do {
            try await DocumentOwnedBlockTableService(owner: owner, service: failing)
                .deleteRow(contextId: "owned", targetId: "r")
            Issue.record("The original service failure was swallowed")
        } catch {
            #expect(error as? OwnedTableAppleError == .originalFailure)
        }
        let failedCalls = await failing.calls
        #expect(failedCalls == [["delete-row", "owned", "r"]])
        #expect(owner.pendingOperationCount == 0)

        let untouched = OwnedTableAppleProbe()
        let service = DocumentOwnedBlockTableService(owner: owner, service: untouched)
        let operation = Task {
            await failure { try await service.deleteColumn(contextId: "owned", targetId: "c") }
        }
        operation.cancel()
        let rejected = await operation.value
        let actual = await untouched.calls
        #expect(rejected == .rejected(.cancelled) && actual.isEmpty)
    }

    private func failure(_ operation: () async throws -> Void) async -> EditorDocumentWriteError? {
        do { try await operation(); return nil }
        catch { return error as? EditorDocumentWriteError }
    }

    private func data(_ document: OwnedTableTestDocument) -> EditorPageObject {
        .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode)
    }

    private func makeOwner(_ document: OwnedTableTestDocument) throws -> EditorDocumentWriteOwner {
        try EditorDocumentWriteOwner(data: data(document), lifetimeDocument: document)
    }
}

private final class OwnedTableTestDocument: MockBaseDocument, EditorDocumentWriteLifetimeProviding, @unchecked Sendable {
    let editorWriteLifetime = EditorDocumentWriteLifetime()

    init() {
        super.init(objectId: "owned", details: nil)
        mockSpaceId = "owned-space"
        mockMode = .handling
        mockIsOpened = true
        mockPermissions.canEditBlocks = true
    }
}

private enum OwnedTableAppleError: Error, Equatable, Sendable { case originalFailure }

private actor OwnedTableAppleGate {
    private var entered = false
    private var released = false
    private var observers: [CheckedContinuation<Void, Never>] = []
    private var pending: [CheckedContinuation<Void, Never>] = []
    func hold() async {
        entered = true
        let values = observers; observers = []
        for value in values { value.resume() }
        if !released { await withCheckedContinuation { pending.append($0) } }
    }
    func waitForEntry() async {
        if entered { return }
        await withCheckedContinuation { observers.append($0) }
    }
    func release() {
        released = true
        let values = pending; pending = []
        for value in values { value.resume() }
    }
}

private actor OwnedTableAppleProbe: BlockTableServiceProtocol {
    let gate: OwnedTableAppleGate?
    let fails: Bool
    private(set) var calls: [[String]] = []
    init(gate: OwnedTableAppleGate? = nil, fails: Bool = false) {
        self.gate = gate
        self.fails = fails
    }
    private func record(_ call: [String]) throws {
        calls.append(call)
        if fails { throw OwnedTableAppleError.originalFailure }
    }
    func createTable(contextId: String, targetId: String, position: BlockPosition, rowsCount: Int, columnsCount: Int) async throws -> String {
        await gate?.hold()
        try record(["create", contextId, targetId, String(describing: position), String(rowsCount), String(columnsCount)])
        return "original-table-id"
    }
    func rowListFill(contextId: String, targetIds: [String]) async throws { try record(["fill", contextId] + targetIds) }
    func insertColumn(contextId: String, targetId: String, position: BlockPosition) async throws {
        try record(["insert-column", contextId, targetId, String(describing: position)])
    }
    func deleteColumn(contextId: String, targetId: String) async throws { try record(["delete-column", contextId, targetId]) }
    func columnDuplicate(contextId: String, targetId: String) async throws { try record(["duplicate-column", contextId, targetId]) }
    func columnSort(contextId: String, columnId: String, blocksSortType: BlocksSortType) async throws {
        try record(["sort-column", contextId, columnId, String(describing: blocksSortType)])
    }
    func columnMove(contextId: String, targetId: String, dropTargetID: String, position: BlockPosition) async throws {
        try record(["move-column", contextId, targetId, dropTargetID, String(describing: position)])
    }
    func insertRow(contextId: String, targetId: String, position: BlockPosition) async throws {
        try record(["insert-row", contextId, targetId, String(describing: position)])
    }
    func deleteRow(contextId: String, targetId: String) async throws { try record(["delete-row", contextId, targetId]) }
    func rowDuplicate(contextId: String, targetId: String) async throws { try record(["duplicate-row", contextId, targetId]) }
    func rowMove(contextId: String, targetId: String, dropTargetID: String, position: BlockPosition) async throws {
        try record(["move-row", contextId, targetId, dropTargetID, String(describing: position)])
    }
    func clearContents(contextId: String, blockIds: [String]) async throws { try record(["clear-contents", contextId] + blockIds) }
    func clearStyle(contextId: String, blocksIds: [String]) async throws { try record(["clear-style", contextId] + blocksIds) }
}
