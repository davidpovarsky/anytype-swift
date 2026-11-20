import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost

/// Real native production constructors with an explicitly in-memory metadata
/// fixture. This probe does not certify the Apple protected filesystem journal.
func runNativeCreationProbe(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                            owner: AnyApplicationSession) async throws {
    let capabilities = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"])
    try require(capabilities["contract"]?.string == "pinkha-torah-native-v1" &&
        capabilities["currentWriterObjectCreate"]?.integer == 1 &&
        capabilities["currentWriterBlockCreate"]?.integer == 1, "guarded creation capabilities")
    let journal = CreationProbeJournal(workspace: workspace)
    let allocated = CreationProbeObjects()
    let objects = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
    let blocks = try AnyNativeBlockCreator(client: client, workspace: workspace, journal: journal,
                                           allowedTypeIDs: ["page"])
    let documents = try AnyEditorDocumentStore(client: client, workspace: workspace, allowedTypeIDs: ["page"])
    let spacePath = ["v1", "spaces", workspace.spaceID]
    let nonce = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    let title = "בדיקת יצירה מקורית " + nonce
    let objectIntent = try AnyNativeObjectCreationIntent(workspace: workspace, mutationID: nonce,
        typeID: "page", initialProperties: .object(["any": .object(["name": .string(title)])]))

    @Sendable func objectIDs(named name: String) async throws -> Set<String> {
        let response = try await client.requestJSON(method: "POST", path: spacePath + ["objects", "query"],
            body: .object(["filter": .object(["any.name": .string(name)]),
                "limit": .integer(5), "includeTotal": .bool(true)]))
        guard response["hasNext"]?.bool == false, let rows = response["records"]?.array,
              response["total"]?.integer == Int64(rows.count),
              rows.allSatisfy({ $0["id"]?.string != nil }) else { throw ProbeError.failed("complete creation lookup") }
        return Set(rows.compactMap { $0["id"]?.string })
    }
    func cleanup() async throws {
        await owner.revokeAndDrain()
        for id in await allocated.values() {
            _ = try await client.requestJSON(method: "DELETE", path: spacePath + ["objects", id])
        }
    }
    do {
        var checks = try await owner.perform { lease -> [String] in
            var checks = ["exact_current_writer_creation_capabilities"]
            let id = try await objects.ensureObject(objectIntent, authorize: { try await lease.validate() },
                onNativeConfirmed: { confirmed in
                    await allocated.insert(confirmed)
                    try require(try await journal.lookup(objectIntent.identity) == .verified(confirmed),
                                "native object metadata precedes confirmation callback")
                })
            await allocated.insert(id)
            let original = try await documents.read(objectID: id, lease: lease)
            try require(original.snapshot.title == title && original.snapshot.blocks.isEmpty,
                        "exact titled empty native Page")
            checks.append("production_guarded_object_create_verified_original_scope")

            let reopened = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
            let retry = try await reopened.ensureObject(objectIntent, authorize: { try await lease.validate() })
            let retryIDs = try await objectIDs(named: title)
            try require(retry == id && retryIDs == [id],
                        "object exact retry created a duplicate")
            let afterRetry = try await documents.read(objectID: id, lease: lease)
            try require(afterRetry.nativeVersion == original.nativeVersion &&
                        afterRetry.snapshot.revision == original.snapshot.revision,
                        "object retry changed the original document")
            checks.append("object_retry_new_creator_same_metadata_has_one_native_id")

            let changedObject = try AnyNativeObjectCreationIntent(workspace: workspace, mutationID: nonce,
                typeID: "page", initialProperties: .object(["any": .object(["name": .string(title + " changed")])]))
            do {
                _ = try await objects.ensureObject(changedObject, authorize: { try await lease.validate() })
                throw ProbeError.failed("changed object intent reused mutation identity")
            } catch AnyNativeCreationError.contentConflict {}
            try require(try await objectIDs(named: title + " changed").isEmpty, "changed intent dispatched")
            checks.append("changed_object_intent_refused_before_native_create")

            let parentIntent = try AnyNativeBlockCreationIntent(workspace: workspace,
                mutationID: creationProbeMutationID(), objectID: id, type: "paragraph",
                text: "שלום **מקור**",
                style: .object(["pinkhaWritingDirection": .string("rightToLeft"),
                    "futureNativeStyle": .object(["preserved": .bool(true)])]), position: "PPPP")
            let parentID = try await blocks.ensureBlock(parentIntent, authorize: { try await lease.validate() },
                onNativeConfirmed: { confirmed in
                    try require(try await journal.lookup(parentIntent.identity) == .verified(confirmed),
                                "native block metadata precedes confirmation callback")
                })
            let initialBlock = try await documents.read(objectID: id, lease: lease)
            try require(initialBlock.snapshot.depthFirstIDs == [parentID] &&
                initialBlock.snapshot.blocks.first?.text == parentIntent.text &&
                initialBlock.snapshot.blocks.first?.native["style"]?["futureNativeStyle"]?["preserved"]?.bool == true,
                "native created block content/style/identity")
            checks.append("production_guarded_block_create_preserves_text_and_unknown_style")

            let reopenedBlocks = try AnyNativeBlockCreator(client: client, workspace: workspace, journal: journal,
                                                           allowedTypeIDs: ["page"])
            try require(try await reopenedBlocks.ensureBlock(parentIntent, authorize: { try await lease.validate() }) == parentID,
                        "block retry ID")
            let blockRetry = try await documents.read(objectID: id, lease: lease)
            try require(blockRetry.snapshot.depthFirstIDs == [parentID] &&
                        blockRetry.nativeVersion == initialBlock.nativeVersion, "block retry changed native history")
            checks.append("block_retry_new_creator_same_metadata_has_no_native_change")

            let changedBlock = try AnyNativeBlockCreationIntent(workspace: workspace,
                mutationID: parentIntent.mutationID, objectID: id, type: "paragraph",
                text: "different", style: parentIntent.style, position: parentIntent.position)
            do {
                _ = try await blocks.ensureBlock(changedBlock, authorize: { try await lease.validate() })
                throw ProbeError.failed("changed block intent reused mutation identity")
            } catch AnyNativeCreationError.contentConflict {}
            checks.append("changed_block_intent_refused_before_native_create")

            let childIntent = try AnyNativeBlockCreationIntent(workspace: workspace,
                mutationID: creationProbeMutationID(), objectID: id, type: "quote",
                text: "ציטוט מקורי", parentID: parentID, position: "PPPP")
            let childID = try await blocks.ensureBlock(childIntent, authorize: { try await lease.validate() })
            let tree = try await documents.read(objectID: id, lease: lease)
            try require(tree.snapshot.depthFirstIDs == [parentID, childID], "child canonical reachability")
            checks.append("guarded_child_creation_preserves_native_parent_identity")

            let prepared = try documents.prepareTextEdit(tree, blockID: parentID, inlineMarkdown: "עריכה מאוחרת")
            let edited = try await documents.apply(prepared, lease: lease)
            try require(edited.readback == .verifiedCurrent, "real later native edit")
            let beforePreservingRetry = try await documents.read(objectID: id, lease: lease)
            try require(try await blocks.ensureBlock(parentIntent, authorize: { try await lease.validate() }) == parentID,
                        "verified block retry lost ID")
            let preserved = try await documents.read(objectID: id, lease: lease)
            try require(preserved.nativeVersion == beforePreservingRetry.nativeVersion &&
                preserved.snapshot.depthFirstIDs == [parentID, childID] &&
                preserved.snapshot.blocks.first(where: { $0.id == parentID })?.text == "עריכה מאוחרת" &&
                preserved.snapshot.blocks.first(where: { $0.id == parentID })?.native["style"]?["futureNativeStyle"]?["preserved"]?.bool == true,
                "retry overwrote a later native edit")
            checks.append("verified_retry_preserves_later_editor_change_and_children")

            let denied = try AnyNativeObjectCreationIntent(workspace: workspace,
                mutationID: creationProbeMutationID(), typeID: "page",
                initialProperties: .object(["any": .object(["name": .string(title + " denied")])]))
            do {
                _ = try await objects.ensureObject(denied, authorize: { throw AnyHostError.sessionClosed })
                throw ProbeError.failed("revoked object creation dispatched")
            } catch AnyHostError.sessionClosed {}
            let deniedReceipt = try await journal.lookup(denied.identity)
            let deniedIDs = try await objectIDs(named: title + " denied")
            try require(deniedReceipt == nil && deniedIDs.isEmpty, "revoked creation reserved or wrote")
            checks.append("revocation_before_dispatch_neither_reserves_nor_creates")

            let recoveryTitle = title + " callback"
            let recovery = try AnyNativeObjectCreationIntent(workspace: workspace,
                mutationID: creationProbeMutationID(), typeID: "page",
                initialProperties: .object(["any": .object(["name": .string(recoveryTitle)])]))
            var knownID: String?
            do {
                _ = try await objects.ensureObject(recovery, authorize: { try await lease.validate() },
                    onNativeConfirmed: { confirmed in
                        await allocated.insert(confirmed)
                        throw ProbeError.failed("synthetic confirmation delivery failure")
                    })
                throw ProbeError.failed("failed confirmation reported success")
            } catch AnyNativeCreationError.createdObjectIncomplete(let id) { knownID = id }
            guard let knownID else { throw ProbeError.failed("confirmation failure discarded native ID") }
            try require(try await journal.lookup(recovery.identity) == .verified(knownID), "recovery receipt not retained")
            let recovered = try await reopened.ensureObject(recovery, authorize: { try await lease.validate() })
            let recoveryIDs = try await objectIDs(named: recoveryTitle)
            try require(recovered == knownID && recoveryIDs == [knownID],
                        "known-ID retry created a replacement root")
            checks.append("confirmation_failure_retains_known_object_id_without_redispatch")

            // The native block endpoint intentionally leaves text absent for
            // an empty paragraph; verify that exact production representation.
            let emptyIntent = try AnyNativeBlockCreationIntent(workspace: workspace,
                mutationID: creationProbeMutationID(), objectID: id, type: "paragraph", text: "",
                style: .object(["pinkhaWritingDirection": .string("natural"),
                    "pinkhaTextAlignment": .string("natural")]), position: "zzzz")
            let emptyID = try await blocks.ensureBlock(emptyIntent, authorize: { try await lease.validate() },
                onNativeConfirmed: { confirmed in
                    try require(try await journal.lookup(emptyIntent.identity) == .verified(confirmed),
                                "sparse empty paragraph was not verified before confirmation")
                })
            let withEmpty = try await documents.read(objectID: id, lease: lease)
            guard let empty = withEmpty.snapshot.blocks.first(where: { $0.id == emptyID }) else {
                throw ProbeError.failed("empty paragraph missing from native readback")
            }
            try require(withEmpty.snapshot.depthFirstIDs == [parentID, childID, emptyID] &&
                        empty.type == "paragraph" && empty.text.isEmpty && empty.native["text"] == nil &&
                        empty.native["style"] == emptyIntent.style &&
                        empty.parentID == emptyIntent.parentID && empty.position == emptyIntent.position,
                        "native sparse empty paragraph identity/content/style/placement")
            checks.append("empty_paragraph_native_sparse_text_is_verified")
            let emptyRetry = try await reopenedBlocks.ensureBlock(emptyIntent, authorize: { try await lease.validate() })
            let afterEmptyRetry = try await documents.read(objectID: id, lease: lease)
            try require(emptyRetry == emptyID && afterEmptyRetry.snapshot.depthFirstIDs == withEmpty.snapshot.depthFirstIDs &&
                        afterEmptyRetry.nativeVersion == withEmpty.nativeVersion &&
                        afterEmptyRetry.snapshot.revision == withEmpty.snapshot.revision,
                        "empty paragraph exact retry changed ID or native history")
            checks.append("empty_paragraph_exact_retry_preserves_id_and_native_history")

            let metadata = try await journal.metadata()
            try require(!String(decoding: metadata, as: UTF8.self).contains(title) &&
                        !String(decoding: metadata, as: UTF8.self).contains(parentIntent.text),
                        "business payload entered metadata journal")
            checks.append("fixture_journal_contains_identity_and_receipt_metadata_only")
            return checks
        }
        await owner.revokeAndDrain()
        do {
            _ = try await owner.perform { _ in true }
            throw ProbeError.failed("closed original lease owner accepted work")
        } catch AnyHostError.sessionClosed {}
        checks.append("closed_original_session_refuses_new_creation_work")
        try await cleanup()
        checks.append("only_allocated_synthetic_objects_removed")
        let output: AnyJSON = .object([
            "status": .string("PASS"),
            "scope": .string("real production native HTTP object/block creators; same-process metadata fixture; protected persistence and injected native partial failures are separate"),
            "checks": .array(checks.map(AnyJSON.string)), "count": .integer(Int64(checks.count)),
            "nativeObjectCreate": .integer(1), "nativeBlockCreate": .integer(1),
            "fixtureJournal": .string("in-memory-metadata-only")])
        print(String(decoding: try JSONEncoder().encode(output), as: UTF8.self))
    } catch {
        try? await cleanup()
        throw error
    }
}

func creationProbeMutationID() -> String {
    UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
}
actor CreationProbeObjects {
    private var ids: Set<String> = []
    func insert(_ id: String) { ids.insert(id) }
    func values() -> [String] { ids.sorted() }
}
actor CreationProbeJournal: AnyNativeCreationJournaling {
    nonisolated let workspace: AnyTorahWorkspace
    private struct Entry: Codable { let identity: AnyNativeCreationIdentity; var state: AnyNativeCreationState }
    private var entries: [String: Entry] = [:]
    init(workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func reserve(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
        guard identity.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        if let entry = entries[identity.key] {
            guard entry.identity == identity else { throw AnyNativeCreationError.contentConflict }
            return .init(state: entry.state, ownsDispatch: false)
        }
        entries[identity.key] = .init(identity: identity, state: .reserved)
        return .init(state: .reserved, ownsDispatch: true)
    }
    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
        guard var entry = entries[identity.key], entry.identity == identity else {
            throw AnyNativeCreationError.contentConflict
        }
        if let old = entry.state.objectID, state.objectID != old { throw AnyNativeCreationError.contentConflict }
        if case .verified = entry.state {
            guard state == entry.state else { throw AnyNativeCreationError.contentConflict }
        }
        entry.state = state; entries[identity.key] = entry
    }
    func lookup(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
        guard identity.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        guard let entry = entries[identity.key] else { return nil }
        guard entry.identity == identity else { throw AnyNativeCreationError.contentConflict }
        return entry.state
    }
    func metadata() throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(entries)
    }
}
