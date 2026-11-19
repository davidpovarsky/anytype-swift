#if os(iOS)
import Foundation
import XCTest
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaAnyRuntime
import PinkhaAnyUI
import PinkhaTorahPresentation
import TorahInspectorCore
@testable import PinkhaAnyNative

/// Uses actual linked AnyLib, account/Space ownership, protected creation receipts,
/// native canonical operations and the original T5 and quote presentation flows.
/// The mounted surface and quoted source content are explicitly synthetic. Real
/// UIKit gestures and live Sefaria transport have separate acceptance lanes.
@MainActor
final class NativeTorahWorkflowTests: XCTestCase {
    func testNativeQuotesNotesRelatedIndexUnlinkAndRuntimeReopen() async throws {
        XCTAssertEqual(AnyEmbeddedBuild.linked, .pinkhaNativeV1)
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("native-torah-proof-" + UUID().uuidString, isDirectory: true)
        let credentialService = "io.pinkha.torah.native.tests." + UUID().uuidString
        let application = try AnyNativeApplication(dataDirectory: directory, credentialService: credentialService)
        var accountID: String?
        var ownedSpaceID: String?
        var activeLifetime: AnyUIPresentationLifetime?
        do {
            try await application.start(network: .official)
            let account = try await application.createAccount()
            accountID = account.id
            try await application.acknowledgeRecoveryBackup(accountID: account.id)
            let spaceID = try await application.createSpace(name: "Disposable native Torah workflow")
            ownedSpaceID = spaceID
            let owner = try await application.connectSpace(id: spaceID)
            let services = try await makeServices(owner, install: true)
            let beforePages = try await pageIDs(owner)
            let originIntent = try AnyNativeObjectCreationIntent(
                workspace: owner.workspace, mutationID: newIntentID(), typeID: "page",
                initialProperties: .object(["any": .object(["name": .string("מסמך בדיקת מקורות")])]))
            let originID = try await owner.session.perform { lease in
                try await owner.objects.ensureObject(originIntent) { try await lease.validate() }
            }
            let rootID = try await createBlock(owner, objectID: originID, parentID: "", text: "פסקה ראשית")
            let childID = try await createBlock(owner, objectID: originID, parentID: rootID, text: "פסקה מקוננת אחרונה")
            let lifetime = AnyUIPresentationLifetime()
            activeLifetime = lifetime
            let presentation = try AnyDocumentPresentation(
                client: owner.client, session: owner.session, objects: owner.objects, blocks: owner.blocks,
                capabilities: owner.capabilities, operations: services.operations,
                noteMarker: services.marker, objectID: originID, lifetime: lifetime,
                recovery: AnyNativeLibraryRecovery(workspace: owner.workspace))
            let surface = NativeTorahFixtureSurface()
            presentation.mount(surface: surface)
            await presentation.load()
            XCTAssertTrue(presentation.canMutate)
            XCTAssertEqual(presentation.orderedBlocks.map(\.id), [rootID, childID])

            let quoteText = "# שָׁלוֹם **מילולי**\n- שורה שנייה [ללא קישור](example)\n    הזחה נשמרת"
            let rawProvider = #"{"fixture":true,"future":{"exact":9007199254740991},"ref":"Genesis 1:1"}"#
            let transfer = TorahSourceTransfer(
                providerID: "sefaria", canonicalRef: "Genesis 1:1", hebrewRef: "בראשית א׳:א׳",
                sectionRef: "Genesis 1", text: quoteText, versionTitle: "Synthetic fixture",
                license: "CC0", direction: "rtl", rawProviderPayload: rawProvider,
                retrievedAt: Date(timeIntervalSince1970: 1_700_000_000))
            let firstDrop = presentation.torah.makeExternalDropInsertionAction(targetBlockId: nil)
            await firstDrop(transfer)
            XCTAssertEqual(presentation.torah.persistenceState, .saved)
            let afterFirst = try await read(owner, objectID: originID)
            let quote = try XCTUnwrap(afterFirst.snapshot.blocks.first { $0.type == "quote" })
            XCTAssertEqual(afterFirst.snapshot.blocks.count, 3)
            XCTAssertEqual(quote.parentID, rootID,
                           "Untargeted source insertion follows the last displayed block in its parent.")
            let child = try XCTUnwrap(afterFirst.snapshot.blocks.first { $0.id == childID })
            XCTAssertGreaterThan(quote.position, child.position)
            XCTAssertEqual(PinkhaAnyUI.AnyInlineMarkdown(quote.text).display, quoteText)
            XCTAssertEqual(quote.native["style"]?["pinkhaWritingDirection"], .string("rightToLeft"))
            XCTAssertTrue(surface.reveals.isEmpty, "Source insertion preserves the baseline setFocus:false behavior.")
            let quoteItems = try await owner.session.perform { lease in
                let items = try await services.associations.listBlockAssociations(
                    objectId: originID, blockId: quote.id, spaceId: spaceID)
                try await lease.validate()
                return items
            }
            XCTAssertEqual(quoteItems.count, 1)
            XCTAssertEqual(quoteItems.first?.role, .sourceQuote)
            XCTAssertEqual(quoteItems.first?.providerPayload, rawProvider)
            XCTAssertEqual(quoteItems.first?.customMetadata?["snapshotText"], quoteText)
            XCTAssertEqual(quoteItems.first?.customMetadata?["direction"], "rtl")

            await firstDrop(transfer)
            let duplicateDropRead = try await read(owner, objectID: originID)
            XCTAssertEqual(duplicateDropRead.snapshot.blocks.count, 3,
                           "A second delivery of one item-provider gesture cannot create another quote.")
            let secondDrop = presentation.torah.makeExternalDropInsertionAction(targetBlockId: childID)
            await secondDrop(transfer)
            XCTAssertEqual(presentation.torah.persistenceState, .saved)
            let afterSecond = try await read(owner, objectID: originID)
            let secondQuote = try XCTUnwrap(afterSecond.snapshot.blocks.first {
                $0.type == "quote" && $0.id != quote.id
            })
            XCTAssertEqual(afterSecond.snapshot.blocks.count, 4)
            XCTAssertEqual(secondQuote.parentID, rootID)
            XCTAssertLessThan(secondQuote.position, child.position)
            XCTAssertEqual(PinkhaAnyUI.AnyInlineMarkdown(secondQuote.text).display, quoteText)
            XCTAssertTrue(surface.reveals.isEmpty)

            let plan = try AnyTorahNoteCreationPlan(
                workspace: owner.workspace, originObjectID: originID, providerID: "sefaria",
                canonicalReference: "Genesis 1:1", selectionID: "native-fixture-selection",
                title: "הערה על בראשית א׳:א׳", createdAt: transfer.retrievedAt)
            let encodedPlan = try JSONEncoder().encode(plan)
            let outcome = try await owner.session.perform { lease in
                try await services.notes.createNote(plan: plan) { try await lease.validate() }
            }
            XCTAssertNil(outcome.recoveryError)
            let noteID = outcome.objectID
            let note = try await read(owner, objectID: noteID)
            XCTAssertEqual(note.snapshot.title, plan.title)
            XCTAssertEqual(note.snapshot.blocks.count, 1)
            XCTAssertEqual(note.snapshot.blocks.first?.text, plan.sourceLine)
            XCTAssertEqual(note.snapshot.blocks.first?.native["style"]?["pinkhaWritingDirection"], .string("rightToLeft"))
            let noteMetadata = try await owner.session.perform { lease in
                let value = try await services.reader.metadata(objectID: noteID)
                try await lease.validate(); return value
            }
            XCTAssertTrue(noteMetadata.isNote)
            let noteLinks = try await owner.session.perform { lease in
                let items = try await services.notes.noteItems(
                    originObjectID: originID, selectionID: plan.selectionID)
                try await lease.validate(); return items
            }
            XCTAssertEqual(noteLinks.count, 1)
            XCTAssertEqual(noteLinks.first?.id, plan.originAssociationID)
            XCTAssertEqual(noteLinks.first?.customMetadata?["anytypeNoteObjectId"], noteID)
            let afterPages = try await pageIDs(owner)
            XCTAssertEqual(afterPages.subtracting(beforePages), [originID, noteID])

            let related = try await owner.session.perform { lease in
                let result = try await services.related.snapshot(source: plan.source)
                try await lease.validate(); return result
            }
            XCTAssertEqual(related.documents.count, 3)
            XCTAssertTrue(related.limitations.isEmpty)
            XCTAssertTrue(related.documents.contains { $0.objectID == noteID && $0.kind == .note && $0.blockID == nil && $0.canUnlink })
            XCTAssertEqual(Set(related.documents.filter { $0.objectID == originID }.compactMap(\.blockID)),
                           [quote.id, secondQuote.id])
            XCTAssertTrue(related.documents.filter { $0.blockID != nil }.allSatisfy { !$0.canUnlink },
                          "A quote match must not expose destructive document unlink.")
            let pendingOldDrop = presentation.torah.makeExternalDropInsertionAction(targetBlockId: childID)
            await lifetime.drain()
            activeLifetime = nil
            await application.stop()

            // New native runtime generation and reopened protected journal.
            try await application.start(network: .official)
            _ = try await application.openSavedAccount(id: account.id)
            let reopened = try await application.connectSpace(id: spaceID)
            XCTAssertNotEqual(reopened.session.generation, owner.session.generation)
            let restored = try await makeServices(reopened, install: false)
            let replayedPlan = try JSONDecoder().decode(AnyTorahNoteCreationPlan.self, from: encodedPlan)
            XCTAssertEqual(replayedPlan.fingerprint, plan.fingerprint)
            let retried = try await reopened.session.perform { lease in
                try await restored.notes.createNote(plan: replayedPlan) { try await lease.validate() }
            }
            XCTAssertEqual(retried.objectID, noteID)
            XCTAssertNil(retried.recoveryError)
            let reopenedPages = try await pageIDs(reopened)
            XCTAssertEqual(reopenedPages, afterPages)
            let reopenedNote = try await read(reopened, objectID: noteID)
            XCTAssertEqual(reopenedNote.snapshot.blocks.map(\.id), note.snapshot.blocks.map(\.id))
            XCTAssertEqual(reopenedNote.snapshot.blocks.first?.text, plan.sourceLine)
            let reopenedOrigin = try await read(reopened, objectID: originID)
            XCTAssertEqual(reopenedOrigin.snapshot.blocks.count, 4)
            XCTAssertEqual(reopenedOrigin.snapshot.blocks.first { $0.id == quote.id }?.text, quote.text)
            await pendingOldDrop(transfer)
            let afterStaleDrop = try await read(reopened, objectID: originID)
            XCTAssertEqual(afterStaleDrop.snapshot.blocks.count, 4,
                           "A captured action cannot regain write authority after native reopen.")

            try await reopened.session.perform { lease in
                try await restored.notes.unlinkNote(
                    associationID: plan.originAssociationID, originObjectID: originID,
                    selectionID: plan.selectionID, source: plan.source) { try await lease.validate() }
            }
            let remainingLinks = try await reopened.session.perform { lease in
                let value = try await restored.notes.noteItems(
                    originObjectID: originID, selectionID: plan.selectionID)
                try await lease.validate(); return value
            }
            XCTAssertTrue(remainingLinks.isEmpty)
            let afterUnlinkPages = try await pageIDs(reopened)
            XCTAssertEqual(afterUnlinkPages, afterPages, "Unlinking keeps the Note object and its content.")
            let noteAfterUnlink = try await read(reopened, objectID: noteID)
            XCTAssertEqual(noteAfterUnlink.snapshot.blocks.map(\.id), note.snapshot.blocks.map(\.id))
            let relatedAfterUnlink = try await reopened.session.perform { lease in
                let value = try await restored.related.snapshot(source: plan.source)
                try await lease.validate(); return value
            }
            XCTAssertEqual(relatedAfterUnlink.documents.count, 2)
            XCTAssertEqual(Set(relatedAfterUnlink.documents.compactMap(\.blockID)), [quote.id, secondQuote.id])
            let retryAfterUnlink = try await reopened.session.perform { lease in
                try await restored.notes.createNote(plan: replayedPlan) { try await lease.validate() }
            }
            XCTAssertEqual(retryAfterUnlink.objectID, noteID)
            XCTAssertNotNil(retryAfterUnlink.recoveryError,
                            "Replaying a completed plan cannot resurrect an explicitly removed source.")
            let stillUnlinked = try await reopened.session.perform { lease in
                let value = try await restored.associations.listDocumentAssociations(
                    objectId: noteID, spaceId: spaceID)
                try await lease.validate(); return value
            }
            XCTAssertTrue(stillUnlinked.isEmpty)
            try await application.deleteSpace(id: spaceID)
            ownedSpaceID = nil
            try await application.signOut()
            try await application.removeSavedAccount(id: account.id)
            await application.stop()
            try await AnyProtectedCreationJournal.removeAccountData(accountID: account.id)
            try FileManager.default.removeItem(at: directory)
        } catch {
            await activeLifetime?.drain()
            if let ownedSpaceID { try? await application.deleteSpace(id: ownedSpaceID) }
            await application.stop()
            if let accountID {
                try? AnyNativeCredentialVault(service: credentialService).remove(accountID: accountID)
                try? await AnyProtectedCreationJournal.removeAccountData(accountID: accountID)
            }
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    private func newIntentID() -> String {
        UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    }

    private func makeServices(_ owner: AnyNativeWorkspaceOwner, install: Bool) async throws -> NativeTorahFixtureServices {
        let operations = try AnyGuardedTorahOperationStore(client: owner.client, workspace: owner.workspace)
        let marker: AnyNativeNoteMarker
        if install {
            marker = try await AnyNoteBootstrap.install(client: owner.client, session: owner.session)
            try await owner.session.perform { lease in
                try await operations.repository.install { try await lease.validate() }
            }
        } else {
            marker = try await AnyNoteBootstrap.read(client: owner.client, session: owner.session)
            _ = try await operations.repository.verifyCapabilities()
        }
        let access = try AnyHTTPTorahTargetAccess(client: owner.client, workspace: owner.workspace,
            allowedTypeIDs: owner.capabilities.allowedTargetTypes, documentTypePolicy: .nativeCanonicalEditorV1)
        let associations = try AnyTorahAssociationRepository(
            workspace: owner.workspace, store: operations, access: access)
        let workflow = try AnyNativeWorkflowBindings(client: owner.client, session: owner.session,
            objects: owner.objects, blocks: owner.blocks, noteMarker: marker)
        let notes = try AnyTorahNotesService(
            workspace: owner.workspace, associations: associations, documents: workflow, access: access)
        let reader = try AnyHTTPTorahRelatedDocumentReader(
            client: owner.client, workspace: owner.workspace,
            allowedTypeIDs: owner.capabilities.allowedTargetTypes,
            noteCollectionIDs: [marker.collectionID], documentTypePolicy: .nativeCanonicalEditorV1)
        let index = try AnyGuardedTorahIndex(client: owner.client, workspace: owner.workspace)
        let related = try AnyNativeTorahRelatedPresentation(index: index, reader: reader, associations: associations)
        return .init(operations: operations, marker: marker, associations: associations,
                     notes: notes, reader: reader, related: related)
    }

    private func createBlock(_ owner: AnyNativeWorkspaceOwner, objectID: String,
                             parentID: String, text: String) async throws -> String {
        let intent = try AnyNativeBlockCreationIntent(workspace: owner.workspace,
            mutationID: newIntentID(), objectID: objectID, type: "paragraph", text: text,
            parentID: parentID, position: AnyLexicographicPosition.middle)
        return try await owner.session.perform { lease in
            try await owner.blocks.ensureBlock(intent) { try await lease.validate() }
        }
    }

    private func read(_ owner: AnyNativeWorkspaceOwner, objectID: String) async throws -> AnyEditorRead {
        let documents = try AnyEditorDocumentStore(
            client: owner.client, workspace: owner.workspace,
            allowedTypeIDs: owner.capabilities.allowedTargetTypes, documentTypePolicy: .nativeCanonicalEditorV1)
        return try await owner.session.perform { try await documents.read(objectID: objectID, lease: $0) }
    }

    private func pageIDs(_ owner: AnyNativeWorkspaceOwner) async throws -> Set<String> {
        try await owner.session.perform { lease in
            let value = try await owner.client.requestJSON(method: "POST",
                path: ["v1", "spaces", owner.workspace.spaceID, "objects", "query"],
                body: .object(["filter": .object(["any.type": .object(["$eq": .string("page")])]),
                               "limit": .integer(1_000), "includeTotal": .bool(true)]),
                authorize: { try await lease.validate() })
            guard let records = value["records"]?.array,
                  value["total"]?.integer == Int64(records.count), value["hasNext"]?.bool == false,
                  records.count <= 1_000 else { throw AnyEngineError.unverifiedWrite }
            var ids = Set<String>()
            for record in records {
                guard let id = record["id"]?.string, !id.isEmpty,
                      record["spaceId"]?.string == owner.workspace.spaceID,
                      record["any"]?["type"]?.string == "page", ids.insert(id).inserted else {
                    throw AnyEngineError.unverifiedWrite
                }
            }
            try await lease.validate()
            return ids
        }
    }
}

@MainActor
private struct NativeTorahFixtureServices {
    let operations: AnyGuardedTorahOperationStore
    let marker: AnyNativeNoteMarker
    let associations: AnyTorahAssociationRepository
    let notes: AnyTorahNotesService
    let reader: AnyHTTPTorahRelatedDocumentReader
    let related: AnyNativeTorahRelatedPresentation
}

@MainActor
private final class NativeTorahFixtureSurface: AnyEditorMountedSurface {
    let sceneID = UUID()
    var isForegroundMounted = true
    private(set) var reveals: [String] = []
    func isBlockVisible(_ id: String) -> Bool { true }
    func reveal(blockID: String, selection: NSRange?) { reveals.append(blockID) }
    func dismissKeyboard() {}
}
#endif
