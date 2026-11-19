import Foundation
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration

enum ProbeFailure: Error { case configuration, assertion(String) }

@main
struct IntegrationProbe {
    static func main() async throws {
        let args = CommandLine.arguments
        guard args.count == 5, args[1] == "--disposable",
              let url = URL(string: args[2]) else { throw ProbeFailure.configuration }
        func progress(_ name: String) {
            FileHandle.standardError.write(Data(("PHASE " + name + "\n").utf8))
        }
        progress("account")
        let workspace = try AnyTorahWorkspace(accountID: args[3], spaceID: args[4])
        let client = try AnyHTTPClient(baseURL: url, expectedAccountID: workspace.accountID)
        try await client.checkAccount()
        let base = ["v1", "spaces", workspace.spaceID]
        let suffix = UUID().uuidString
        var checks: [String: Bool] = [:]
        func check(_ name: String, _ condition: Bool) throws {
            guard condition else { throw ProbeFailure.assertion(name) }
            checks[name] = true
            progress("checked:" + name)
        }
        progress("create-synthetic-page")
        let created = try await client.requestJSON(method: "POST", path: base + ["objects"], body: .object([
            "type": .string("page"),
            "initialProperties": .object(["any": .object([
                "name": .string("Pinkha Any bridge disposable " + suffix)
            ])])
        ]))
        let objectID = try created.requireString("objectId")
        let fetched = try await client.requestJSON(method: "GET", path: base + ["objects", objectID])
        guard let typeID = fetched["record"]?["any"]?["type"]?.string else {
            throw ProbeFailure.assertion("native_type")
        }
        let access = try AnyHTTPTorahTargetAccess(
            client: client, workspace: workspace, allowedTypeIDs: [typeID])
        let store = try AnyNativeTorahOperationStore(client: client, workspace: workspace)
        progress("install-claims-bundle")
        try await store.repository.install()
        let repository = try AnyTorahAssociationRepository(workspace: workspace, store: store, access: access)
        let target = TorahAssociationTarget.object(objectId: objectID)
        try await access.validate(target, intent: .write)
        try check("real_native_target_membership", true)
        let observationSession = AnyStreamSession()
        progress("open-native-observer")
        let observation = try await repository.watch(
            target: target, spaceID: workspace.spaceID, session: observationSession)
        var observer = observation.makeAsyncIterator()
        guard let initial = try await observer.next() else { throw ProbeFailure.assertion("atomic_native_initial") }
        try check("atomic_native_initial", initial.initial && initial.snapshot.records.isEmpty)

        func item(_ id: String, role: TorahAssociationRole = .context) -> TorahAssociationItem {
            .init(id: id, kind: .ref, role: role, providerID: "sefaria", externalID: "Genesis.1.1",
                  canonicalKey: "Genesis 1:1", labelHe: "בראשית א:א",
                  unknownFields: ["probe": .object(["kept": .bool(true)])])
        }
        progress("append-context")
        _ = try await repository.addAssociation(item("context"), target: target, spaceId: workspace.spaceID)
        progress("await-native-observer-change")
        var sawContext = false
        for _ in 0..<128 {
            guard let update = try await observer.next() else { break }
            try await observationSession.requireActive(generation: update.generation)
            if update.snapshot.records.contains(where: { $0.item.id == "context" }) {
                sawContext = !update.initial
                break
            }
        }
        try check("native_observer_sees_domain_mutation", sawContext)
        await observationSession.invalidate()
        do {
            try await observationSession.requireActive(generation: initial.generation)
            throw ProbeFailure.assertion("native_observer_generation_invalidated")
        } catch AnyLiveQueryError.staleGeneration {
            checks["native_observer_generation_invalidated"] = true
        }
        let dedup = try await repository.addAssociation(item("retry-context"), target: target, spaceId: workspace.spaceID)
        try check("context_semantic_dedup_stable_id", dedup.id == "context")
        for id in ["quote-A", "quote-B"] {
            _ = try await repository.addAssociation(item(id, role: .sourceQuote), target: target, spaceId: workspace.spaceID)
        }
        let documents = try await repository.listDocumentAssociations(objectId: objectID, spaceId: workspace.spaceID)
        try check("separate_quote_instances", Set(documents.map(\.id)) == ["context", "quote-A", "quote-B"])

        progress("create-block")
        let blockResult = try await client.requestJSON(
            method: "POST", path: base + ["objects", objectID, "editor", "editor_blocks", "blocks"],
            body: .object(["type": .string("paragraph"), "text": .string("בדיקת שמירת הקשרים")]))
        guard let blockID = blockResult["recordIds"]?.array?.first?.string else {
            throw ProbeFailure.assertion("native_block_id")
        }
        let blockTarget = TorahAssociationTarget.block(objectId: objectID, blockId: blockID)
        try await access.validate(blockTarget, intent: .write)
        _ = try await repository.addAssociation(item("block-context"), target: blockTarget, spaceId: workspace.spaceID)
        try check("block_scope", try await repository.listBlockAssociations(
            objectId: objectID, blockId: blockID, spaceId: workspace.spaceID).count == 1)

        progress("prepare-native-mutation")
        var revised = item("context"); revised.labelEn = "Prepared native revision"
        guard let prepared = try await repository.prepareMutation(revised, target: target, spaceId: workspace.spaceID) else {
            throw ProbeFailure.assertion("prepared_mutation")
        }
        let restored = try JSONDecoder().decode(AnyTorahPreparedMutation.self, from: JSONEncoder().encode(prepared))
        _ = try await repository.commitPrepared(restored)
        _ = try await repository.commitPrepared(restored)
        let state = try await store.snapshot()
        try check("prepared_exact_retry", state.all.filter { $0.id == restored.operation.claimID }.count == 1)
        progress("remove-one-quote")
        try await repository.removeAssociation(associationId: "quote-A", target: target, spaceId: workspace.spaceID)
        let remaining = try await repository.listDocumentAssociations(objectId: objectID, spaceId: workspace.spaceID)
        try check("observed_remove_keeps_other_quote", Set(remaining.map(\.id)) == ["context", "quote-B"])

        let legacyItem = TorahAssociationItem(
            id: "migration-quote", kind: .ref, role: .sourceQuote,
            providerID: "sefaria", externalID: "Exodus.1.1", canonicalKey: "Exodus 1:1",
            labelHe: "שמות א:א", unknownFields: ["futureItem": .number(7)])
        let legacy = TorahCanonicalAssociationsPayload(
            records: [.init(location: .init(spaceId: "legacy-space", target: .block(objectId: "legacy-object", blockId: "legacy-block")),
                            item: legacyItem, unknownFields: ["recordFuture": .string("kept")])],
            unknownFields: ["envelopeFuture": .array([.bool(true), .null])])
        let bytes = try TorahAssociationPayloadCodec().encodeCanonicalDocument(legacy)
        let plan = try AnyTorahMigrationPlan(
            sourceBytes: bytes, sourceSpaceID: "legacy-space", sourceObjectID: "legacy-object",
            workspace: workspace, targetObjectID: objectID,
            blockIDMap: ["legacy-block": blockID], migrationKey: "probe-" + suffix)
        progress("migrate-native-associations")
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        let receipt = try await executor.execute(plan)
        let again = try await executor.execute(plan)
        try check("migration_complete_native_readback", receipt.status == .complete)
        try check("migration_retry_no_new_claim", again.status == .complete && again.acknowledgedClaimIDs.isEmpty)
        let imported = try await repository.listBlockAssociations(objectId: objectID, blockId: blockID, spaceId: workspace.spaceID)
        try check("migration_original_item_unchanged", imported.contains(legacyItem))
        try check("migration_original_bytes_retained", plan.sourceBytes == bytes)

        // A new repository instance proves no dependence on an in-memory shadow.
        progress("fresh-native-adapter")
        let freshStore = try AnyNativeTorahOperationStore(client: client, workspace: workspace)
        let fresh = try AnyTorahAssociationRepository(workspace: workspace, store: freshStore, access: access)
        try check("fresh_adapter_reads_native_claims",
            try await fresh.listBlockAssociations(objectId: objectID, blockId: blockID, spaceId: workspace.spaceID) == imported)

        let wrong = try AnyHTTPClient(baseURL: url, expectedAccountID: "different-disposable-account")
        do {
            try await wrong.checkAccount()
            throw ProbeFailure.assertion("wrong_account_rejected")
        } catch AnyEngineError.accountChanged { checks["wrong_account_rejected"] = true }

        // Native orphan test: direct block deletion retains a child row, which
        // must not remain a valid association target merely because it exists.
        progress("orphan-target")
        let parentResult = try await client.requestJSON(
            method: "POST", path: base + ["objects", objectID, "editor", "editor_blocks", "blocks"],
            body: .object(["type": .string("paragraph"), "text": .string("parent")]))
        guard let parentID = parentResult["recordIds"]?.array?.first?.string else { throw ProbeFailure.configuration }
        let childResult = try await client.requestJSON(
            method: "POST", path: base + ["objects", objectID, "editor", "editor_blocks", "blocks"],
            body: .object(["type": .string("paragraph"), "text": .string("child"),
                           "nav": .object(["parentId": .string(parentID)])]))
        guard let childID = childResult["recordIds"]?.array?.first?.string else { throw ProbeFailure.configuration }
        _ = try await client.requestJSON(method: "DELETE",
            path: base + ["objects", objectID, "editor", "editor_blocks", "blocks", parentID])
        do {
            try await access.validate(.block(objectId: objectID, blockId: childID), intent: .write)
            throw ProbeFailure.assertion("orphan_native_block_rejected")
        } catch TorahAssociationRepositoryError.targetNotFound { checks["orphan_native_block_rejected"] = true }


        progress("native-wiki-schema")
        let wiki = try await AnyHTTPHierarchyRecordStore.installWiki(client: client, workspace: workspace)
        let hierarchyStore = try AnyHTTPHierarchyRecordStore(client: client, workspace: workspace, schema: wiki)
        let hierarchy = try AnyHierarchyRepository(
            workspace: workspace, store: hierarchyStore, allowedTypeIDs: [typeID])
        // Fixture creation dispatches once. Production retry/journal acceptance is
        // separately owned by PinkhaAnyHost; this probe does not simulate it.
        func createWikiFixture(_ plan: AnyHierarchyCreationPlan) async throws -> String {
            let result = try await client.requestJSON(method: "POST", path: base + ["objects"],
                body: .object(["type": .string(plan.typeID),
                               "collections": .array(plan.collections.map(AnyJSON.string)),
                               "initialProperties": plan.initialProperties]))
            return try result.requireString("objectId")
        }
        let folderTitle = "תיקיית בדיקה " + suffix
        let folderPlan = try await hierarchy.prepareCreation(typeID: typeID, title: folderTitle, kind: .folder)
        let folderID = try await createWikiFixture(folderPlan)
        let firstPlan = try await hierarchy.prepareCreation(
            typeID: typeID, title: "ילד ראשון " + suffix, kind: .writingDocument, parentID: folderID)
        let firstID = try await createWikiFixture(firstPlan)
        let secondPlan = try await hierarchy.prepareCreation(
            typeID: typeID, title: "ילד שני " + suffix, kind: .writingDocument, parentID: folderID)
        let secondID = try await createWikiFixture(secondPlan)
        let tree = try await hierarchy.snapshot()
        try check("native_wiki_original_tree", tree.tree.children(of: folderID).map(\.objectId) == [firstID, secondID])

        let hierarchySession = AnyStreamSession()
        let hierarchyStream = try await hierarchy.watch(session: hierarchySession)
        var hierarchyObserver = hierarchyStream.makeAsyncIterator()
        guard let treeInitial = try await hierarchyObserver.next() else {
            throw ProbeFailure.assertion("native_wiki_atomic_initial")
        }
        try check("native_wiki_atomic_initial", treeInitial.initial && treeInitial.snapshot.itemsByID[folderID] != nil)
        let renamed = "תיקייה ששונתה " + suffix
        _ = try await hierarchy.rename(objectID: folderID, expectedTitle: folderTitle, newTitle: renamed)
        var sawRename = false
        for _ in 0..<128 {
            guard let update = try await hierarchyObserver.next() else { break }
            try await hierarchySession.requireActive(generation: update.generation)
            if update.snapshot.itemsByID[folderID]?.title == renamed {
                sawRename = !update.initial; break
            }
        }
        try check("native_wiki_live_rename", sawRename)
        await hierarchySession.invalidate()
        let reordered = try await hierarchy.prepareMove(
            objectID: secondID, parentID: folderID, beforeSiblingID: firstID)
        _ = try await hierarchy.commitPlacement(reordered)
        _ = try await hierarchy.commitPlacement(reordered)
        try check("native_wiki_order_and_exact_retry",
            try await hierarchy.snapshot().tree.children(of: folderID).map(\.objectId) == [secondID, firstID])
        do {
            _ = try await hierarchy.prepareMove(objectID: folderID, parentID: firstID)
            throw ProbeFailure.assertion("native_wiki_cycle_rejected")
        } catch PinkhaHierarchyError.cycleDetected {
            checks["native_wiki_cycle_rejected"] = true
        }
        let removal = try await hierarchy.removeFolderSafely(objectID: folderID)
        let afterRemoval = try await hierarchy.snapshot()
        try check("native_wiki_reparents_before_folder_bin",
            removal.complete && removal.folderArchived == true &&
            afterRemoval.itemsByID[firstID]?.parentID == nil && afterRemoval.itemsByID[firstID] != nil &&
            afterRemoval.itemsByID[secondID]?.parentID == nil && afterRemoval.itemsByID[secondID] != nil)
        let reopenedWiki = try await AnyHTTPHierarchyRecordStore.readSchema(client: client, workspace: workspace)
        let reopenedHierarchy = try AnyHierarchyRepository(workspace: workspace,
            store: AnyHTTPHierarchyRecordStore(client: client, workspace: workspace, schema: reopenedWiki),
            allowedTypeIDs: [typeID])
        try check("native_wiki_fresh_reader",
            try await reopenedHierarchy.snapshot().itemsByID[secondID]?.position == afterRemoval.itemsByID[secondID]?.position)

        progress("native-related-documents")
        let uniqueSource = T5SourceIdentity(providerID: "port-probe", canonicalReference: "synthetic-" + suffix)
        let firstSource = uniqueSource.item
        _ = try await repository.addAssociation(firstSource, target: target, spaceId: workspace.spaceID)
        _ = try await repository.addAssociation(uniqueSource.item, target: .object(objectId: firstID), spaceId: workspace.spaceID)
        var relatedQuote = uniqueSource.item; relatedQuote.id = "related-quote"; relatedQuote.role = .sourceQuote
        _ = try await repository.addAssociation(relatedQuote, target: target, spaceId: workspace.spaceID)
        let relatedBlock = uniqueSource.item
        _ = try await repository.addAssociation(relatedBlock, target: blockTarget, spaceId: workspace.spaceID)
        let metadata = try AnyHTTPTorahRelatedDocumentReader(
            client: client, workspace: workspace, allowedTypeIDs: [typeID])
        let related = try AnyTorahRelatedDocumentsService(
            workspace: workspace, operations: store, associations: repository, reader: metadata)
        let relatedResult = try await related.documents(source: uniqueSource)
        try check("native_t5_related_document_projection",
            Set(relatedResult.documents.matches.map(\.document.objectID)) == [objectID, firstID] &&
            !relatedResult.documents.isTruncated && !relatedResult.documents.hasStaleCandidates)
        try await related.unlinkDocument(objectID: objectID, source: uniqueSource)
        let afterRelatedUnlink = try await repository.listDocumentAssociations(
            objectId: objectID, spaceId: workspace.spaceID)
        let afterRelatedBlock = try await repository.listBlockAssociations(
            objectId: objectID, blockId: blockID, spaceId: workspace.spaceID)
        try check("native_t5_unlink_keeps_quote_and_block",
            afterRelatedUnlink.contains(where: { $0.id == relatedQuote.id }) &&
            !afterRelatedUnlink.contains(where: { $0.id == firstSource.id }) &&
            afterRelatedBlock.contains(where: { $0.id == relatedBlock.id }))
        try check("native_t5_refresh_after_unlink",
            try await related.documents(source: uniqueSource).documents.matches.map(\.document.objectID) == [firstID])

        struct Receipt: Codable {
            let scope: String
            let objectID: String
            let blockID: String
            let checks: [String: Bool]
            let limitations: [String]
        }
        let output = Receipt(scope: "standalone real Any/PinkhaKit adapter", objectID: objectID, blockID: blockID, checks: checks,
            limitations: ["No full iOS UI or physical-device acceptance", "No engine restart in this probe",
                          "No two-client sync proof", "Cross-object target/claim writes are not atomic"])
        let encoded = try JSONEncoder().encode(output)
        print(String(decoding: encoded, as: UTF8.self))
    }
}
