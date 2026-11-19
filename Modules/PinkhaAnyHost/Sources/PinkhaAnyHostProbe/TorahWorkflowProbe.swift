import Foundation
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost

/// Runs the original T5 flow and production native bootstrap/constructors against
/// a real disposable Any Space. The creation receipt fixture is IN MEMORY.
/// Session reconnection here is not a process restart or Apple journal proof.
@MainActor
func runNativeTorahWorkflowProbe(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                                 owner: AnyApplicationSession) async throws {
    var checks: [String] = []
    let allocated = CreationProbeObjects()
    let journal = CreationProbeJournal(workspace: workspace)
    let documents = try AnyEditorDocumentStore(client: client, workspace: workspace,
        allowedTypeIDs: ["page"], documentTypePolicy: .nativeCanonicalEditorV1)
    let objects = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
    let blocks = try AnyNativeBlockCreator(client: client, workspace: workspace, journal: journal,
        allowedTypeIDs: ["page"], documentTypePolicy: .nativeCanonicalEditorV1)
    let operations = try AnyGuardedTorahOperationStore(client: client, workspace: workspace)
    let access = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace,
        allowedTypeIDs: ["page"], documentTypePolicy: .nativeCanonicalEditorV1)
    let associations = try AnyTorahAssociationRepository(
        workspace: workspace, store: operations, access: access)
    let index = try AnyGuardedTorahIndex(client: client, workspace: workspace)
    let base = ["v1", "spaces", workspace.spaceID]
    var reopened: AnyApplicationSession?

    func cleanup() async throws {
        await owner.revokeAndDrain()
        await reopened?.revokeAndDrain()
        for id in await allocated.values() {
            _ = try await client.requestJSON(method: "DELETE", path: base + ["objects", id])
        }
    }

    do {
        let capability = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"])
        try require(capability["currentWriterObjectCreate"]?.integer == 1 &&
                    capability["currentWriterBlockCreate"]?.integer == 1 &&
                    capability["nativeDocumentTypePolicy"]?.integer == 1,
                    "current native creation and document proof capabilities")
        checks.append("actual_native_creation_and_document_policy_capabilities")
        let marker = try await AnyNativeNoteBootstrap.install(client: client, session: owner)
        let markerRead = try await AnyNativeNoteBootstrap.read(client: client, session: owner)
        try require(marker == markerRead, "production native Note bootstrap/read agreement")
        checks.append("production_native_note_marker_bootstrap_and_read")
        try await owner.perform { lease in
            try await operations.repository.install { try await lease.validate() }
        }
        checks.append("guarded_canonical_store_explicit_installation")
        let reader = try AnyHTTPTorahRelatedDocumentReader(client: client, workspace: workspace,
            allowedTypeIDs: ["page"], noteCollectionIDs: [marker.collectionID],
            documentTypePolicy: .nativeCanonicalEditorV1)
        let workflow = try AnyNativeWorkflowBindings(client: client, session: owner,
            objects: objects, blocks: blocks, noteMarker: marker)
        let notes = try AnyTorahNotesService(
            workspace: workspace, associations: associations, documents: workflow, access: access)
        let originIntent = try AnyNativeObjectCreationIntent(workspace: workspace,
            mutationID: creationProbeMutationID(), typeID: "page",
            initialProperties: .object(["any": .object(["name": .string("ניסוי T5 native " + creationProbeMutationID())])]))
        let originID = try await owner.perform { lease in
            try await objects.ensureObject(originIntent, authorize: { try await lease.validate() },
                onNativeConfirmed: { await allocated.insert($0) })
        }
        await allocated.insert(originID)
        let plan = try AnyTorahNoteCreationPlan(workspace: workspace, originObjectID: originID,
            providerID: "sefaria", canonicalReference: "Genesis 1:1",
            selectionID: "native-probe-selection", createdAt: Date(timeIntervalSince1970: 1_700_000_000))
        let quoteText = "שָׁלוֹם — מקור ניסוי"
        let quoteIntent = try AnyNativeBlockCreationIntent(workspace: workspace,
            mutationID: creationProbeMutationID(), objectID: originID, type: "quote",
            text: quoteText, style: .object(["pinkhaWritingDirection": .string("rightToLeft")]),
            position: AnyLexicographicPosition.middle)
        let quoteID = try await owner.perform { lease in
            try await blocks.ensureBlock(quoteIntent) { try await lease.validate() }
        }
        var quoteItem = plan.source.item
        quoteItem.id = "fixture-quote-" + creationProbeMutationID()
        quoteItem.role = .sourceQuote
        quoteItem.createdAt = plan.createdAt
        quoteItem.providerPayload = #"{"fixture":true,"future":{"precision":9007199254740991}}"#
        quoteItem.customMetadata = ["snapshotText": quoteText, "direction": "rtl"]
        let immutableQuoteItem = quoteItem
        _ = try await owner.perform { lease in
            try await associations.apply(immutableQuoteItem,
                target: .block(objectId: originID, blockId: quoteID), spaceId: workspace.spaceID,
                authorize: { try await lease.validate() })
        }
        checks.append("real_guarded_origin_quote_and_canonical_fixture_association")

        let outcome = try await owner.perform { lease in
            try await notes.createNote(plan: plan) { try await lease.validate() }
        }
        await allocated.insert(outcome.objectID)
        try require(outcome.recoveryError == nil, "complete production native T5 create")
        let noteID = outcome.objectID
        let noteRead = try await owner.perform { try await documents.read(objectID: noteID, lease: $0) }
        try require(noteRead.snapshot.title == plan.title && noteRead.snapshot.blocks.count == 1 &&
                    noteRead.snapshot.blocks.first?.text == plan.sourceLine &&
                    noteRead.snapshot.blocks.first?.direction == .rightToLeft,
                    "exact Note title/source line/RTL")
        checks.append("original_t5_flow_creates_one_native_note_and_source_line")
        let metadata = try await reader.metadata(objectID: noteID)
        try require(metadata.isNote && metadata.objectID == noteID && metadata.canUnlink,
                    "native marker classifies the actual Note")
        checks.append("production_native_note_classification_and_current_permissions")
        let sourceItems = try await associations.listDocumentAssociations(objectId: noteID, spaceId: workspace.spaceID)
        try require(sourceItems.count == 1 && sourceItems.first?.id == plan.sourceAssociationID &&
                    sourceItems.allSatisfy(plan.source.matches), "one canonical source context")
        checks.append("canonical_note_source_context_native_readback")
        let originLinks = try await notes.noteItems(originObjectID: originID, selectionID: plan.selectionID)
        try require(originLinks.count == 1 && originLinks.first?.id == plan.originAssociationID &&
                    originLinks.first?.customMetadata?["anytypeNoteObjectId"] == noteID,
                    "one original Note backlink")
        checks.append("canonical_origin_note_backlink_native_readback")
        let related = try await index.related(to: plan.source)
        try require(related.readiness.complete && related.targets.count == 2 &&
                    related.targets.contains { $0.target.objectId == noteID && $0.target.blockId == nil && $0.canSafelyUnlink } &&
                    related.targets.contains { $0.target.objectId == originID && $0.target.blockId == quoteID && !$0.canSafelyUnlink },
                    "native related index combines Note context and quote")
        checks.append("native_related_index_note_and_quote_with_safe_unlink_scope")
        let derived = try await index.documentProperties(objectID: noteID)
        try require(derived.readiness.complete && derived.sourceIdentities == [plan.source.indexValue],
                    "native source property for the Note")
        checks.append("native_derived_source_property_matches_original_t5_identity")

        FileHandle.standardError.write(Data("T5_PROGRESS before_retry_claims.begin\n".utf8))
        let beforeRetryClaims = try await operations.snapshot().all.count
        FileHandle.standardError.write(Data("T5_PROGRESS before_retry_claims.end\n".utf8))
        FileHandle.standardError.write(Data("T5_PROGRESS second_create_note.begin\n".utf8))
        let completedAgain = try await owner.perform { lease in
            try await notes.createNote(plan: plan) { try await lease.validate() }
        }
        FileHandle.standardError.write(Data("T5_PROGRESS second_create_note.end\n".utf8))
        FileHandle.standardError.write(Data("T5_PROGRESS after_retry_document_read.begin\n".utf8))
        let afterRetry = try await owner.perform { try await documents.read(objectID: noteID, lease: $0) }
        FileHandle.standardError.write(Data("T5_PROGRESS after_retry_document_read.end\n".utf8))
        FileHandle.standardError.write(Data("T5_PROGRESS after_retry_claims.begin\n".utf8))
        let afterRetryClaims = try await operations.snapshot().all.count
        FileHandle.standardError.write(Data("T5_PROGRESS after_retry_claims.end\n".utf8))
        try require(completedAgain.objectID == noteID && completedAgain.recoveryError == nil &&
                    beforeRetryClaims == afterRetryClaims &&
                    noteRead.snapshot.blocks.map(\.id) == afterRetry.snapshot.blocks.map(\.id) &&
                    noteRead.nativeVersion == afterRetry.nativeVersion, "same-plan exact retry")
        checks.append("same_plan_retry_preserves_native_ids_history_and_claim_count")
        guard let sourceBlockID = noteRead.snapshot.blocks.first?.id else { throw ProbeError.failed("missing source line") }
        let laterText = "עריכה מאוחרת של ההערה נשמרת"
        let edit = try documents.prepareTextEdit(afterRetry, blockID: sourceBlockID, inlineMarkdown: laterText)
        let editReceipt = try await owner.perform { try await documents.apply(edit, lease: $0) }
        try require(editReceipt.readback == .verifiedCurrent, "later user text persisted")
        checks.append("later_note_edit_committed_through_native_conditional_write")

        await owner.revokeAndDrain()
        do {
            _ = try await owner.perform { _ in true }
            throw ProbeError.failed("revoked source session accepted work")
        } catch AnyHostError.sessionClosed {}
        checks.append("old_native_application_session_remains_revoked")
        let newOwner = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        reopened = newOwner
        let newMarker = try await AnyNativeNoteBootstrap.read(client: client, session: newOwner)
        try require(newMarker == marker, "reconnected Note marker")
        let newObjects = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
        let newBlocks = try AnyNativeBlockCreator(client: client, workspace: workspace, journal: journal,
            allowedTypeIDs: ["page"], documentTypePolicy: .nativeCanonicalEditorV1)
        let newWorkflow = try AnyNativeWorkflowBindings(client: client, session: newOwner,
            objects: newObjects, blocks: newBlocks, noteMarker: newMarker)
        let newNotes = try AnyTorahNotesService(
            workspace: workspace, associations: associations, documents: newWorkflow, access: access)
        let decodedPlan = try JSONDecoder().decode(AnyTorahNoteCreationPlan.self, from: JSONEncoder().encode(plan))
        let reconnected = try await newOwner.perform { lease in
            try await newNotes.createNote(plan: decodedPlan) { try await lease.validate() }
        }
        let retained = try await newOwner.perform { try await documents.read(objectID: noteID, lease: $0) }
        try require(reconnected.objectID == noteID && reconnected.recoveryError == nil &&
                    retained.snapshot.blocks.count == 1 && retained.snapshot.blocks.first?.id == sourceBlockID &&
                    retained.snapshot.blocks.first?.text == laterText,
                    "reconnected production workflow kept later user content")
        checks.append("reconnected_t5_workflow_reuses_receipt_and_preserves_later_edit")

        try await newOwner.perform { lease in
            try await newNotes.unlinkNote(associationID: plan.originAssociationID, originObjectID: originID,
                selectionID: plan.selectionID, source: plan.source) { try await lease.validate() }
        }
        try require(try await newNotes.noteItems(originObjectID: originID, selectionID: plan.selectionID).isEmpty,
                    "origin association removed")
        try require(try await associations.listDocumentAssociations(objectId: noteID, spaceId: workspace.spaceID).isEmpty,
                    "source association removed")
        let remainingNote = try await newOwner.perform { try await documents.read(objectID: noteID, lease: $0) }
        try require(remainingNote.snapshot.blocks.first?.text == laterText &&
                    remainingNote.snapshot.blocks.first?.id == sourceBlockID, "unlink deleted or rewrote Note body")
        checks.append("t5_unlink_removes_both_links_without_deleting_note_or_content")
        let remainingQuote = try await associations.listBlockAssociations(
            objectId: originID, blockId: quoteID, spaceId: workspace.spaceID)
        try require(remainingQuote == [immutableQuoteItem], "unlink changed unrelated quote provenance")
        checks.append("unlink_preserves_exact_source_quote_payload_and_metadata")
        let remainingRelated = try await index.related(to: plan.source)
        try require(remainingRelated.readiness.complete && remainingRelated.targets.count == 1 &&
                    remainingRelated.targets.first?.target.blockId == quoteID,
                    "related native index still exposes quote without removed Note")
        checks.append("native_related_index_rebuilds_after_safe_unlink")
        let afterRemoveRetry = try await newOwner.perform { lease in
            try await newNotes.createNote(plan: decodedPlan) { try await lease.validate() }
        }
        try require(afterRemoveRetry.objectID == noteID && afterRemoveRetry.recoveryError != nil,
                    "old completed Note plan resurrected an explicitly removed link")
        try require(try await associations.listDocumentAssociations(objectId: noteID, spaceId: workspace.spaceID).isEmpty,
                    "source context resurrected")
        checks.append("old_completed_plan_cannot_resurrect_removed_source_context")

        try await cleanup()
        checks.append("only_owned_synthetic_origin_and_note_cleaned_up")
        let result: AnyJSON = .object([
            "status": .string("PASS"), "count": .integer(Int64(checks.count)),
            "scope": .string("production_t5_native_workflow_with_memory_creation_journal"),
            "protectedAppleJournal": .bool(false), "engineProcessRestart": .bool(false),
            "checks": .array(checks.map(AnyJSON.string))])
        print(String(decoding: try JSONEncoder().encode(result), as: UTF8.self))
    } catch {
        try? await cleanup()
        let result: AnyJSON = .object([
            "status": .string("FAIL"), "count": .integer(Int64(checks.count)),
            "scope": .string("production_t5_native_workflow_with_memory_creation_journal"),
            "protectedAppleJournal": .bool(false), "engineProcessRestart": .bool(false),
            "checks": .array(checks.map(AnyJSON.string))])
        print(String(decoding: try JSONEncoder().encode(result), as: UTF8.self))
        throw error
    }
}
