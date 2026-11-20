import Foundation

// The original public protocol and forwarding value declarations are compiled.
// These are explicit non-RPC boundaries; protobuf runtime serialization,
// BlockContent rendering, and conversion/service execution are not replaced claims.
@preconcurrency
public protocol ProtobufEnumBoundary: RawRepresentable, Hashable, Sendable {
    init()
    init?(rawValue: Int)
    var rawValue: Int { get }
}
public enum SwiftProtobuf { public typealias Enum = ProtobufEnumBoundary }
public enum Google_Protobuf_Value: Hashable, Sendable {
    case string(String), number(Double), bool(Bool)
}
public enum BlockContent: Hashable, Sendable { case unsupported, link(BlockLink) }
public enum MentionObject: Hashable, Sendable { case noDetails(blockId: String) }
public struct Emoji: Hashable, Sendable { public let value: String }
public enum CoverType: Int, Sendable { case fixture = 1 }

struct OwnedBlockInvocation: Equatable, Sendable {
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
enum OwnedBlockProbeError: Error, Equatable, Sendable { case deliberate }

actor OwnedBlockServiceProbe: BlockServiceProtocol {
    let label: String
    let gate: OwnershipGate?
    let fails: Bool
    let missingLast: Bool
    private var calls: [OwnedBlockInvocation] = []

    init(label: String, gate: OwnershipGate? = nil, fails: Bool = false, missingLast: Bool = false) {
        self.label = label; self.gate = gate; self.fails = fails; self.missingLast = missingLast
    }
    func snapshot() -> [OwnedBlockInvocation] { calls }
    private func record(_ call: OwnedBlockInvocation) async throws {
        await gate?.hold()
        calls.append(call)
        if fails { throw OwnedBlockProbeError.deliberate }
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
struct FixtureBlockServices: Sendable {
    let action = OwnedBlockServiceProbe(label: "action")
    let handler = OwnedBlockServiceProbe(label: "handler")
    let keyboard = OwnedBlockServiceProbe(label: "keyboard")
    let state = OwnedBlockServiceProbe(label: "state")
    let builder = OwnedBlockServiceProbe(label: "builder")
    let viewModel = OwnedBlockServiceProbe(label: "viewModel")
}
// BEGIN_OWNED_BLOCK_CONTROLS

@MainActor
private func blockAuthorityFailure(_ operation: () async throws -> Void) async -> DocumentOwnedBlockServiceError? {
    do { try await operation(); return nil }
    catch { return error as? DocumentOwnedBlockServiceError }
}

@MainActor
private func exerciseOwnedBlockServices(_ checks: BoundaryChecks) async throws {
    let document = LifetimeDocumentProbe()
    let owner = try EditorDocumentWriteOwner(data: lifetimeData(document), lifetimeDocument: document)
    let original = OwnedBlockServiceProbe(label: "forward")
    let service = DocumentOwnedBlockService(owner: owner, service: original)
    let appearance = BlockLink.Appearance(iconSize: .small, cardStyle: .text, description: .added,
        relations: [.type, .name, .type])
    let fields: BlockFields = ["title": .string("Exact \u{e9}"), "ordinal": .number(3), "enabled": .bool(false)]
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
    let expected: [OwnedBlockInvocation] = [
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
    checks.expect(forwarded.count == 16 && owner.pendingOperationCount == 0, "block_all_sixteen_admitted_methods_finish_their_leases")
    checks.expect(added == "forward-original-block-id" && first == added && replacement == added
        && last == "forward-original-last-id", "block_original_mutation_and_read_return_identities_are_preserved")
    for (index, call) in expected.enumerated() {
        checks.expect(index < forwarded.count && forwarded[index] == call, "block_exact_original_arguments_" + call.operation)
    }

    let foreignSource = await lifetimeFailure { try await service.delete(contextId: "foreign", blockIds: ["a"]) }
    let afterForeign = await original.snapshot()
    checks.expect(foreignSource == .rejected(.wrongContext) && afterForeign.count == 16,
        "block_foreign_source_context_is_refused_before_service")
    let unicodeDocument = LifetimeDocumentProbe(object: "\u{e9}")
    let unicodeOwner = try EditorDocumentWriteOwner(data: lifetimeData(unicodeDocument), lifetimeDocument: unicodeDocument)
    let unicodeTarget = OwnedBlockServiceProbe(label: "unicode")
    let unicode = DocumentOwnedBlockService(owner: unicodeOwner, service: unicodeTarget)
    let unicodeSource = await lifetimeFailure { try await unicode.delete(contextId: "e\u{301}", blockIds: ["a"]) }
    let unicodeCalls = await unicodeTarget.snapshot()
    checks.expect(unicodeSource == .rejected(.wrongContext) && unicodeCalls.isEmpty, "block_source_identity_uses_exact_utf8")

    let foreignMove = await blockAuthorityFailure {
        try await service.move(contextId: "owned", blockIds: ["a"], targetContextID: "other", dropTargetID: "target", position: .bottom)
    }
    let foreignPage = await blockAuthorityFailure {
        try await service.moveToPage(objectId: "owned", blockIds: ["a"], pageId: "other")
    }
    let unicodeMove = await blockAuthorityFailure {
        try await unicode.move(contextId: "\u{e9}", blockIds: ["a"], targetContextID: "e\u{301}", dropTargetID: "target", position: .bottom)
    }
    let unicodePage = await blockAuthorityFailure {
        try await unicode.moveToPage(objectId: "\u{e9}", blockIds: ["a"], pageId: "e\u{301}")
    }
    let postDestination = await original.snapshot(), postUnicode = await unicodeTarget.snapshot()
    checks.expect(foreignMove == .separateDocumentAuthorityRequired && postDestination.count == 16,
        "block_move_to_foreign_document_requires_separate_authority")
    checks.expect(foreignPage == .separateDocumentAuthorityRequired && postDestination.count == 16,
        "block_move_to_foreign_page_requires_separate_authority")
    checks.expect(unicodeMove == .separateDocumentAuthorityRequired && postUnicode.isEmpty,
        "block_move_destination_does_not_normalize_unicode")
    checks.expect(unicodePage == .separateDocumentAuthorityRequired && postUnicode.isEmpty,
        "block_page_destination_does_not_normalize_unicode")

    let promote = await blockAuthorityFailure {
        _ = try await service.convertChildrenToObjects(contextId: "owned", blocksIds: ["child"],
            typeUniqueKey: .note, templateId: "retained-template")
    }
    let create = await blockAuthorityFailure {
        _ = try await service.createBlockLink(contextId: "owned", targetId: "target", spaceId: "owned-space",
            details: [.name("retained")], typeUniqueKey: .note, position: .bottom, templateId: "retained-template")
    }
    let postCreation = await original.snapshot()
    checks.expect(promote == .separateObjectAuthorityRequired && postCreation.count == 16,
        "block_promote_has_no_invented_object_authority_or_raw_fallback")
    checks.expect(create == .separateObjectAuthorityRequired && postCreation.count == 16,
        "block_create_link_has_no_invented_object_authority_or_raw_fallback")

    let foreignSpace = await lifetimeFailure { _ = try await service.lastBlockId(from: "owned", spaceId: "other-space") }
    let postSpace = await original.snapshot()
    checks.expect(foreignSpace == .rejected(.wrongContext) && postSpace.count == 16,
        "block_read_requires_exact_owned_space_before_original_object_show")

    for (label, mode) in [("preview", DocumentMode.preview), ("version", DocumentMode.version("exact-version"))] {
        let readonly = LifetimeDocumentProbe(mode: mode)
        let readonlyOwner = try EditorDocumentWriteOwner(data: lifetimeData(readonly), lifetimeDocument: readonly)
        let target = OwnedBlockServiceProbe(label: label)
        let readonlyService = DocumentOwnedBlockService(owner: readonlyOwner, service: target)
        let value = try await readonlyService.lastBlockId(from: "owned", spaceId: "owned-space")
        let actual = await target.snapshot()
        checks.expect(value == label + "-original-last-id"
            && actual == [.init(operation: "last-block", context: "owned", space: "owned-space")],
            "block_read_retains_original_nonmutating_semantics_in_" + label)
    }
    for state in ["locked", "no-permission"] {
        let readonly = LifetimeDocumentProbe()
        if state == "locked" { readonly.isLocked = true }
        else { _ = readonly.applyPermissionForFixture(false) }
        let readonlyOwner = try EditorDocumentWriteOwner(data: lifetimeData(readonly), lifetimeDocument: readonly)
        let target = OwnedBlockServiceProbe(label: state)
        let value = try await DocumentOwnedBlockService(owner: readonlyOwner, service: target)
            .lastBlockId(from: "owned", spaceId: "owned-space")
        let actual = await target.snapshot()
        checks.expect(value == state + "-original-last-id" && actual.count == 1,
            "block_read_does_not_require_edit_permission_" + state)
    }
    for state in ["preview", "locked", "no-permission"] {
        let restricted = LifetimeDocumentProbe(mode: state == "preview" ? .preview : .handling)
        if state == "locked" { restricted.isLocked = true }
        if state == "no-permission" { _ = restricted.applyPermissionForFixture(false) }
        let restrictedOwner = try EditorDocumentWriteOwner(data: lifetimeData(restricted), lifetimeDocument: restricted)
        let target = OwnedBlockServiceProbe(label: state)
        let denied = await lifetimeFailure {
            try await DocumentOwnedBlockService(owner: restrictedOwner, service: target).delete(contextId: "owned", blockIds: ["a"])
        }
        let actual = await target.snapshot()
        checks.expect(denied == .rejected(state == "preview" ? .notHandling : .notEditable) && actual.isEmpty,
            "block_write_denied_before_service_" + state)
    }

    let errorTarget = OwnedBlockServiceProbe(label: "error", fails: true)
    var unchangedError = false
    do { try await DocumentOwnedBlockService(owner: owner, service: errorTarget).delete(contextId: "owned", blockIds: ["a"]) }
    catch { unchangedError = (error as? OwnedBlockProbeError) == .deliberate }
    let errorCalls = await errorTarget.snapshot()
    checks.expect(unchangedError && errorCalls.count == 1 && owner.pendingOperationCount == 0,
        "block_original_mutation_error_is_not_rewritten_or_retried")
    let missing = OwnedBlockServiceProbe(label: "missing", missingLast: true)
    var originalMissing = false
    do { _ = try await DocumentOwnedBlockService(owner: owner, service: missing).lastBlockId(from: "owned", spaceId: "owned-space") }
    catch { if case .lastBlockIdNotFound? = error as? BlockServiceError { originalMissing = true } }
    let missingCalls = await missing.snapshot()
    checks.expect(originalMissing && missingCalls.count == 1 && owner.pendingOperationCount == 0,
        "block_original_last_block_not_found_error_is_preserved")

    for isRead in [false, true] {
        let label = isRead ? "read" : "mutation"
        let target = OwnedBlockServiceProbe(label: label)
        let bound = DocumentOwnedBlockService(owner: owner, service: target)
        let task = Task {
            await lifetimeFailure {
                if isRead { _ = try await bound.lastBlockId(from: "owned", spaceId: "owned-space") }
                else { try await bound.delete(contextId: "owned", blockIds: ["a"]) }
            }
        }
        task.cancel()
        let denied = await task.value, actual = await target.snapshot()
        checks.expect(denied == .rejected(.cancelled) && actual.isEmpty,
            "block_cancellation_before_" + label + "_does_not_dispatch")

        let gate = OwnershipGate()
        let held = OwnedBlockServiceProbe(label: label, gate: gate)
        let heldService = DocumentOwnedBlockService(owner: owner, service: held)
        let admitted = Task {
            await lifetimeFailure {
                if isRead { _ = try await heldService.lastBlockId(from: "owned", spaceId: "owned-space") }
                else { try await heldService.delete(contextId: "owned", blockIds: ["actual"]) }
            }
        }
        await gate.waitForEntry()
        admitted.cancel()
        await gate.release()
        let outcome = await admitted.value, calls = await held.snapshot()
        checks.expect(outcome == .completedWithoutOwnership(.cancelled) && calls.count == 1
            && owner.pendingOperationCount == 0, "block_cancellation_after_" + label + "_preserves_admitted_effect")
    }

    for isRead in [false, true] {
        let label = isRead ? "read" : "mutation"
        let heldDocument = LifetimeDocumentProbe()
        var drains = 0
        let heldOwner = try EditorDocumentWriteOwner(data: lifetimeData(heldDocument), lifetimeDocument: heldDocument,
            onDrained: { drains += 1 })
        let gate = OwnershipGate()
        let target = OwnedBlockServiceProbe(label: label, gate: gate)
        let bound = DocumentOwnedBlockService(owner: heldOwner, service: target)
        let task = Task {
            await lifetimeFailure {
                if isRead { _ = try await bound.lastBlockId(from: "owned", spaceId: "owned-space") }
                else { _ = try await bound.add(contextId: "owned", targetId: "target", info: info, position: .bottom) }
            }
        }
        await gate.waitForEntry()
        heldOwner.retire()
        let pending = heldOwner.pendingOperationCount
        await gate.release()
        let outcome = await task.value, calls = await target.snapshot()
        checks.expect(outcome == .completedWithoutOwnership(.retired) && calls.count == 1
            && pending == 1 && heldOwner.isDrained && drains == 1,
            "block_admitted_" + label + "_finishes_once_without_renewing_retired_ownership")
    }
    for mode in ["close", "permission"] {
        for isRead in [false, true] {
            let label = isRead ? "read" : "mutation"
            let abaDocument = LifetimeDocumentProbe()
            let abaOwner = try EditorDocumentWriteOwner(data: lifetimeData(abaDocument), lifetimeDocument: abaDocument)
            let gate = OwnershipGate()
            let target = OwnedBlockServiceProbe(label: label, gate: gate)
            let bound = DocumentOwnedBlockService(owner: abaOwner, service: target)
            let task = Task {
                await lifetimeFailure {
                    if isRead { _ = try await bound.lastBlockId(from: "owned", spaceId: "owned-space") }
                    else { try await bound.delete(contextId: "owned", blockIds: ["actual"]) }
                }
            }
            await gate.waitForEntry()
            if mode == "close" { try await abaDocument.close(); abaDocument.reopenForFixture() }
            else { _ = abaDocument.applyPermissionForFixture(false); _ = abaDocument.applyPermissionForFixture(true) }
            await gate.release()
            let outcome = await task.value, calls = await target.snapshot()
            checks.expect(outcome == .completedWithoutOwnership(.retired) && calls.count == 1 && abaOwner.isRetired,
                "block_" + mode + "_aba_preserves_actual_" + label + "_and_refuses_delivery")
        }
    }

    let targets = FixtureBlockServices()
    let preparedDocument = LifetimeDocumentProbe()
    let prepared = try PreparedEditorPageSession(data: lifetimeData(preparedDocument), document: preparedDocument,
        textService: TextProbe(), services: fixtureServices(events: LocalPublisherProbe(), blockServices: targets))
    let slots: [(String, any BlockServiceProtocol, OwnedBlockServiceProbe)] = [
        ("action", prepared.services.blockActionService.blockService, targets.action),
        ("handler", prepared.services.blockActionHandler.blockService, targets.handler),
        ("keyboard", prepared.services.keyboardHandler.blockService, targets.keyboard),
        ("state", prepared.services.blocksStateManager.blockService, targets.state),
        ("builder", prepared.services.blockBuilder.blockService, targets.builder),
        ("viewModel", prepared.services.viewModel.blockService, targets.viewModel)
    ]
    for (name, bound, target) in slots {
        try await bound.delete(contextId: "owned", blockIds: [name])
        let calls = await target.snapshot()
        checks.expect(calls == [.init(operation: "delete", context: "owned", targets: [name])],
            "prepared_block_slot_retains_its_original_service_" + name)
    }
    prepared.retire()
    for (name, bound, target) in slots {
        let outcome = await lifetimeFailure { try await bound.delete(contextId: "owned", blockIds: ["late"]) }
        let calls = await target.snapshot()
        checks.expect(outcome == .rejected(.retired) && calls.count == 1,
            "prepared_block_slot_is_retired_with_its_one_host_" + name)
    }

    let shared = LifetimeDocumentProbe()
    let firstOwner = try EditorDocumentWriteOwner(data: lifetimeData(shared), lifetimeDocument: shared)
    let secondOwner = try EditorDocumentWriteOwner(data: lifetimeData(shared), lifetimeDocument: shared)
    let sharedTarget = OwnedBlockServiceProbe(label: "shared")
    firstOwner.retire()
    let refused = await lifetimeFailure {
        try await DocumentOwnedBlockService(owner: firstOwner, service: sharedTarget).delete(contextId: "owned", blockIds: ["first"])
    }
    try await DocumentOwnedBlockService(owner: secondOwner, service: sharedTarget).delete(contextId: "owned", blockIds: ["second"])
    let sharedCalls = await sharedTarget.snapshot()
    checks.expect(refused == .rejected(.retired) && sharedCalls == [.init(operation: "delete", context: "owned", targets: ["second"])]
        && !secondOwner.isRetired, "block_two_owners_do_not_share_retirement_or_admission")

    checks.expect(BlockActionServiceDependencies.original().blockService === Container.shared.block,
        "block_original_default_factory_remains_the_unwrapped_original_service")
    let legacy = OwnedBlockServiceProbe(label: "legacy")
    try await legacy.moveToPage(objectId: "source", blockIds: ["a"], pageId: "unrelated")
    let promoted = try await legacy.convertChildrenToObjects(contextId: "source", blocksIds: ["a"],
        typeUniqueKey: .note, templateId: "template")
    let created = try await legacy.createBlockLink(contextId: "source", targetId: "target", spaceId: "space",
        details: [.name("original")], typeUniqueKey: .note, position: .bottom, templateId: "template")
    let legacyCalls = await legacy.snapshot()
    checks.expect(legacyCalls.count == 3 && legacyCalls[0].destination == "unrelated"
        && promoted == ["legacy-link-2", "legacy-link-1", "legacy-link-2"] && created == "legacy-original-object-id",
        "block_unwrapped_service_boundary_retains_foreign_move_and_original_creation_results")
}
