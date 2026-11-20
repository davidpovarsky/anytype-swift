import Foundation
import Services
import ProtobufMessages
import Testing
@testable import Anytype

@Suite
@MainActor
struct EditorDocumentOwnedBlockTests {
    @Test
    func forwardsOriginalBlockArgumentsAndReturnIdentities() async throws {
    let document = OwnedBlockTestDocument()
    let owner = try EditorDocumentWriteOwner(data: data(document), lifetimeDocument: document)
    let original = OwnedBlockAppleProbe(label: "forward")
    let service = DocumentOwnedBlockService(owner: owner, service: original)
    let appearance = BlockLink.Appearance(iconSize: .small, cardStyle: .text, description: .added,
        relations: [.type, .name, .type])
    var fields: BlockFields = ["title": .init(), "ordinal": .init(), "enabled": .init()]
    fields["title"]?.stringValue = "Exact \u{e9}"
    fields["ordinal"]?.numberValue = 3
    fields["enabled"]?.boolValue = false
    let info = BlockInformation(id: "client-block", content: .link(.init(targetBlockID: "retained-link", appearance: appearance)),
        backgroundColor: .ice, horizontalAlignment: .right, childrenIds: ["c2", "c1", "c2"],
        configurationData: .init(parentId: "parent", backgroundColor: .teal), fields: fields)
    let added = try await service.add(contextId: "owned", targetId: "target", info: info, position: .inner)
    let first = try await service.addFirstBlock(contextId: "owned", info: info)
    try await service.delete(contextId: "owned", blockIds: ["b2", "b1", "b2"])
    try await service.duplicate(contextId: "owned", targetId: "dup-target", blockIds: ["d2", "d1"], position: .left)
    try await service.move(contextId: "owned", blockIds: ["m2", "m1"], targetContextID: "owned",
        dropTargetID: "drop", position: .right)
    try await service.setAlign(objectId: "owned", blockIds: ["a2", "a1"], alignment: .justify)
    try await service.setBackgroundColor(objectId: "owned", blockIds: ["bg"], color: .orange)
    try await service.setFields(objectId: "owned", blockId: "field-block", fields: fields)
    try await service.setBlockColor(objectId: "owned", blockIds: ["t2", "t1"], color: .purple)
    try await service.replace(objectId: "owned", blockIds: ["old2", "old1"], targetId: "replacement")
    let replacement = try await service.replaceBlock(contextId: "owned", blockId: "old", info: info)
    try await service.move(objectId: "owned", blockId: "move-one", targetId: "target-one", position: .innerFirst)
    try await service.moveToPage(objectId: "owned", blockIds: ["p2", "p1"], pageId: "owned")
    try await service.setLinkAppearance(objectId: "owned", blockIds: ["l2", "l1"], appearance: appearance)
    try await service.changeMarkup(objectId: "owned", blockIds: ["mk2", "mk1"], markType: .linkToObject("literal-target"))
    let last = try await service.lastBlockId(from: "owned", spaceId: "owned-space")
    let expected: [OwnedBlockAppleInvocation] = [
        .init(operation: "add", context: "owned", targets: ["target"], position: "inner", info: info),
        .init(operation: "add-first", context: "owned", info: info),
        .init(operation: "delete", context: "owned", targets: ["b2", "b1", "b2"]),
        .init(operation: "duplicate", context: "owned", targets: ["d2", "d1"], target: "dup-target", position: "left"),
        .init(operation: "move-context", context: "owned", targets: ["m2", "m1"], target: "drop", destination: "owned", position: "right"),
        .init(operation: "align", context: "owned", targets: ["a2", "a1"], alignment: 3),
        .init(operation: "background", context: "owned", targets: ["bg"], color: .orange),
        .init(operation: "fields", context: "owned", targets: ["field-block"], fields: fields),
        .init(operation: "text-color", context: "owned", targets: ["t2", "t1"], color: .purple),
        .init(operation: "replace", context: "owned", targets: ["old2", "old1"], target: "replacement"),
        .init(operation: "replace-block", context: "owned", targets: ["old"], info: info),
        .init(operation: "move-block", context: "owned", targets: ["move-one"], target: "target-one", middlewarePosition: 7),
        .init(operation: "move-page", context: "owned", targets: ["p2", "p1"], destination: "owned"),
        .init(operation: "appearance", context: "owned", targets: ["l2", "l1"], appearance: appearance),
        .init(operation: "markup", context: "owned", targets: ["mk2", "mk1"], markup: .linkToObject("literal-target")),
        .init(operation: "last-block", context: "owned", space: "owned-space")
    ]
    let forwarded = await original.snapshot()
    #expect(forwarded.count == 16 && owner.pendingOperationCount == 0)
    #expect(added == "forward-original-block-id" && first == added && replacement == added
        && last == "forward-original-last-id")
    for (index, call) in expected.enumerated() {
        #expect(index < forwarded.count && forwarded[index] == call)
    }

    }

    @Test
    func refusesUnownedContextSpaceDestinationsAndObjectCreation() async throws {
        let document = OwnedBlockTestDocument()
        let owner = try makeOwner(document)
        let target = OwnedBlockAppleProbe(label: "scope")
        let service = DocumentOwnedBlockService(owner: owner, service: target)
        let foreign = await failure { try await service.delete(contextId: "foreign", blockIds: ["a"]) }
        let space = await failure { _ = try await service.lastBlockId(from: "owned", spaceId: "other-space") }
        let move = await authorityFailure {
            try await service.move(contextId: "owned", blockIds: ["a"], targetContextID: "other",
                dropTargetID: "target", position: .bottom)
        }
        let page = await authorityFailure {
            try await service.moveToPage(objectId: "owned", blockIds: ["a"], pageId: "other")
        }
        let promote = await authorityFailure {
            _ = try await service.convertChildrenToObjects(contextId: "owned", blocksIds: ["a"],
                typeUniqueKey: .note, templateId: "template")
        }
        let create = await authorityFailure {
            _ = try await service.createBlockLink(contextId: "owned", targetId: "target", spaceId: "owned-space",
                details: [.name("retained")], typeUniqueKey: .note, position: .bottom, templateId: "template")
        }
        #expect(foreign == .rejected(.wrongContext) && space == .rejected(.wrongContext))
        #expect(move == .separateDocumentAuthorityRequired && page == .separateDocumentAuthorityRequired)
        #expect(promote == .separateObjectAuthorityRequired && create == .separateObjectAuthorityRequired)
        let calls = await target.snapshot()
        #expect(calls.isEmpty && owner.pendingOperationCount == 0)
    }

    @Test
    func originalOwnedReadWorksWithoutEditAuthority() async throws {
        for mode in [DocumentMode.preview, .version("exact-version"), .handling] {
            let document = OwnedBlockTestDocument()
            document.mockMode = mode
            document.mockPermissions.canEditBlocks = false
            let owner = try makeOwner(document)
            let target = OwnedBlockAppleProbe(label: "readonly")
            let service = DocumentOwnedBlockService(owner: owner, service: target)
            let value = try await service.lastBlockId(from: "owned", spaceId: "owned-space")
            let denied = await failure { try await service.delete(contextId: "owned", blockIds: ["a"]) }
            #expect(value == "readonly-original-last-id")
            #expect(denied == .rejected(mode.isHandling ? .notEditable : .notHandling))
            let calls = await target.snapshot()
            #expect(calls == [.init(operation: "last-block", context: "owned", space: "owned-space")])
        }
    }

    @Test
    func admittedWriteAndReadCannotRegainOwnershipAfterCloseReopen() async throws {
        for isRead in [false, true] {
            let document = OwnedBlockTestDocument()
            var drains = 0
            let owner = try EditorDocumentWriteOwner(data: data(document), lifetimeDocument: document,
                onDrained: { drains += 1 })
            let gate = OwnedBlockAppleGate()
            let target = OwnedBlockAppleProbe(label: "held", gate: gate)
            let service = DocumentOwnedBlockService(owner: owner, service: target)
            let task = Task {
                await failure {
                    if isRead { _ = try await service.lastBlockId(from: "owned", spaceId: "owned-space") }
                    else { try await service.delete(contextId: "owned", blockIds: ["actual"]) }
                }
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
            let outcome = await task.value
            let calls = await target.snapshot()
            #expect(outcome == .completedWithoutOwnership(.retired) && calls.count == 1)
            #expect(owner.isDrained && drains == 1)
            let later = await failure { try await service.delete(contextId: "owned", blockIds: ["late"]) }
            #expect(later == .rejected(.retired))
        }
    }

    @Test
    func originalErrorsAndPredispatchCancellationArePreserved() async throws {
        let document = OwnedBlockTestDocument()
        let owner = try makeOwner(document)
        let originalError = OwnedBlockAppleProbe(label: "failure", fails: true)
        do {
            try await DocumentOwnedBlockService(owner: owner, service: originalError).delete(contextId: "owned", blockIds: ["a"])
            Issue.record("The original error was swallowed")
        } catch { #expect(error as? OwnedBlockAppleError == .deliberate) }
        let missing = OwnedBlockAppleProbe(label: "missing", missingLast: true)
        do {
            _ = try await DocumentOwnedBlockService(owner: owner, service: missing).lastBlockId(from: "owned", spaceId: "owned-space")
            Issue.record("The original lastBlockIdNotFound was swallowed")
        } catch {
            if case .lastBlockIdNotFound? = error as? BlockServiceError {} else {
                Issue.record("The original missing-block error was changed")
            }
        }
        let untouched = OwnedBlockAppleProbe(label: "cancelled")
        let service = DocumentOwnedBlockService(owner: owner, service: untouched)
        let task = Task { await failure { try await service.delete(contextId: "owned", blockIds: ["a"]) } }
        task.cancel()
        let cancelled = await task.value
        let errorCalls = await originalError.snapshot(), missingCalls = await missing.snapshot(), cancelledCalls = await untouched.snapshot()
        #expect(errorCalls.count == 1 && missingCalls.count == 1)
        #expect(cancelled == .rejected(.cancelled) && cancelledCalls.isEmpty && owner.pendingOperationCount == 0)
    }

    @Test
    func retiringOneOwnerDoesNotRetireAnotherOwnerOfSameDocument() async throws {
        let document = OwnedBlockTestDocument()
        let first = try makeOwner(document), second = try makeOwner(document)
        let target = OwnedBlockAppleProbe(label: "shared")
        first.retire()
        let denied = await failure {
            try await DocumentOwnedBlockService(owner: first, service: target).delete(contextId: "owned", blockIds: ["first"])
        }
        try await DocumentOwnedBlockService(owner: second, service: target).delete(contextId: "owned", blockIds: ["second"])
        let calls = await target.snapshot()
        #expect(denied == .rejected(.retired) && !second.isRetired)
        #expect(calls == [.init(operation: "delete", context: "owned", targets: ["second"])])
    }

    private func data(_ document: OwnedBlockTestDocument) -> EditorPageObject {
        .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode)
    }
    private func makeOwner(_ document: OwnedBlockTestDocument) throws -> EditorDocumentWriteOwner {
        try .init(data: data(document), lifetimeDocument: document)
    }
    private func failure(_ operation: () async throws -> Void) async -> EditorDocumentWriteError? {
        do { try await operation(); return nil } catch { return error as? EditorDocumentWriteError }
    }
    private func authorityFailure(_ operation: () async throws -> Void) async -> DocumentOwnedBlockServiceError? {
        do { try await operation(); return nil } catch { return error as? DocumentOwnedBlockServiceError }
    }
}

private final class OwnedBlockTestDocument: MockBaseDocument, EditorDocumentWriteLifetimeProviding, @unchecked Sendable {
    let editorWriteLifetime = EditorDocumentWriteLifetime()
    init() {
        super.init(objectId: "owned", details: nil)
        mockSpaceId = "owned-space"; mockMode = .handling; mockIsOpened = true
        mockPermissions.canEditBlocks = true
    }
}
private actor OwnedBlockAppleGate {
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
private struct OwnedBlockAppleInvocation: Equatable, Sendable {
    let operation: String
    let context: String
    var targets: [String] = []
    var target: String? = nil
    var destination: String? = nil
    var space: String? = nil
    var position: String? = nil
    var middlewarePosition: Int? = nil
    var info: BlockInformation? = nil
    var fields: BlockFields? = nil
    var alignment: Int? = nil
    var color: MiddlewareColor? = nil
    var appearance: BlockLink.Appearance? = nil
    var markup: MarkupType? = nil
    var objectType: String? = nil
    var template: String? = nil
}
private enum OwnedBlockAppleError: Error, Equatable, Sendable { case deliberate }

private actor OwnedBlockAppleProbe: BlockServiceProtocol {
    let label: String
    let gate: OwnedBlockAppleGate?
    let fails: Bool
    let missingLast: Bool
    private var calls: [OwnedBlockAppleInvocation] = []

    init(label: String, gate: OwnedBlockAppleGate? = nil, fails: Bool = false, missingLast: Bool = false) {
        self.label = label; self.gate = gate; self.fails = fails; self.missingLast = missingLast
    }
    func snapshot() -> [OwnedBlockAppleInvocation] { calls }
    private func record(_ call: OwnedBlockAppleInvocation) async throws {
        await gate?.hold()
        calls.append(call)
        if fails { throw OwnedBlockAppleError.deliberate }
    }

    func add(contextId: String, targetId: String, info: BlockInformation, position: BlockPosition) async throws -> String {
        try await record(.init(operation: "add", context: contextId, targets: [targetId], position: String(describing: position), info: info))
        return label + "-original-block-id"
    }

    func addFirstBlock(contextId: String, info: BlockInformation) async throws -> String {
        try await record(.init(operation: "add-first", context: contextId, info: info))
        return label + "-original-block-id"
    }

    func delete(contextId: String, blockIds: [String]) async throws {
        try await record(.init(operation: "delete", context: contextId, targets: blockIds))
    }

    func duplicate(contextId: String, targetId: String, blockIds: [String], position: BlockPosition) async throws {
        try await record(.init(operation: "duplicate", context: contextId, targets: blockIds, target: targetId, position: String(describing: position)))
    }

    func move(contextId: String, blockIds: [String], targetContextID: String, dropTargetID: String, position: BlockPosition) async throws {
        try await record(.init(operation: "move-context", context: contextId, targets: blockIds, target: dropTargetID, destination: targetContextID, position: String(describing: position)))
    }

    func setAlign(objectId: String, blockIds: [String], alignment: LayoutAlignment) async throws {
        try await record(.init(operation: "align", context: objectId, targets: blockIds, alignment: alignment.rawValue))
    }

    func setBackgroundColor(objectId: String, blockIds: [String], color: MiddlewareColor) async throws {
        try await record(.init(operation: "background", context: objectId, targets: blockIds, color: color))
    }

    func setFields(objectId: String, blockId: String, fields: BlockFields) async throws {
        try await record(.init(operation: "fields", context: objectId, targets: [blockId], fields: fields))
    }

    func setBlockColor(objectId: String, blockIds: [String], color: MiddlewareColor) async throws {
        try await record(.init(operation: "text-color", context: objectId, targets: blockIds, color: color))
    }

    func replace(objectId: String, blockIds: [String], targetId: String) async throws {
        try await record(.init(operation: "replace", context: objectId, targets: blockIds, target: targetId))
    }

    func replaceBlock(contextId: String, blockId: String, info: BlockInformation) async throws -> String {
        try await record(.init(operation: "replace-block", context: contextId, targets: [blockId], info: info))
        return label + "-original-block-id"
    }

    func move(objectId: String, blockId: String, targetId: String, position: Anytype_Model_Block.Position) async throws {
        try await record(.init(operation: "move-block", context: objectId, targets: [blockId], target: targetId, middlewarePosition: position.rawValue))
    }

    func moveToPage(objectId: String, blockIds: [String], pageId: String) async throws {
        try await record(.init(operation: "move-page", context: objectId, targets: blockIds, destination: pageId))
    }

    func setLinkAppearance(objectId: String, blockIds: [String], appearance: BlockLink.Appearance) async throws {
        try await record(.init(operation: "appearance", context: objectId, targets: blockIds, appearance: appearance))
    }

    func changeMarkup(objectId: String, blockIds: [String], markType: MarkupType) async throws {
        try await record(.init(operation: "markup", context: objectId, targets: blockIds, markup: markType))
    }

    func lastBlockId(from objectId: String, spaceId: String) async throws -> String {
        try await record(.init(operation: "last-block", context: objectId, space: spaceId))
        if missingLast { throw BlockServiceError.lastBlockIdNotFound }
        return label + "-original-last-id"
    }

    func convertChildrenToObjects(contextId: String, blocksIds: [String], typeUniqueKey: ObjectTypeUniqueKey, templateId: String) async throws -> [String] {
        try await record(.init(operation: "promote", context: contextId, targets: blocksIds, objectType: typeUniqueKey.value, template: templateId))
        return [label + "-link-2", label + "-link-1", label + "-link-2"]
    }

    func createBlockLink(contextId: String, targetId: String, spaceId: String, details: [BundledDetails], typeUniqueKey: ObjectTypeUniqueKey, position: BlockPosition, templateId: String) async throws -> String {
        try await record(.init(operation: "create-link", context: contextId, targets: [targetId], space: spaceId, position: String(describing: position), objectType: typeUniqueKey.value, template: templateId))
        return label + "-original-object-id"
    }
}
