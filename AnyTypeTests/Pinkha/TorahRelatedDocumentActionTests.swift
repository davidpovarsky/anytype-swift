import Foundation
import PinkhaKit
import Testing
import TorahInspectorCore
@testable import Anytype

@Suite("T5 related-document action lifetime and authority")
@MainActor
struct TorahRelatedDocumentActionTests {
    private let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3")
    private let selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 3:3")

    @Test("Related navigation rejects a foreign Space and callbacks from a previous document lifetime")
    func relatedNavigationRequiresCurrentSpaceAndLifetime() throws {
        let probe = T5ActionAssociationProbe(items: [:])
        let session = TorahEditorSession(
            spaceId: "space", objectId: "origin",
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: probe
        )
        var opened: [String] = []
        session.installOpenObjectHandler { objectID, _ in opened.append(objectID) }
        let originalAction = try #require(session.hostActions.onOpenRelatedDocument)

        originalAction(row(spaceID: "other-space"))
        #expect(opened.isEmpty)
        originalAction(row())
        #expect(opened == ["related"])
        session.deactivateDocument()
        originalAction(row())
        #expect(opened == ["related"])
        session.activateDocument()
        originalAction(row())
        #expect(opened == ["related"])
        session.hostActions.onOpenRelatedDocument?(row())
        #expect(opened == ["related", "related"])
    }

    @Test("Related block navigation preserves the exact target without opening its document as a fallback")
    func relatedNavigationPreservesBlockTarget() throws {
        let probe = T5ActionAssociationProbe(items: [:])
        let session = TorahEditorSession(
            spaceId: "space", objectId: "origin",
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: probe
        )
        var opened: [(objectID: String, blockID: String?)] = []
        session.installOpenObjectHandler { opened.append(($0, $1)) }
        let action = try #require(session.hostActions.onOpenRelatedDocument)

        action(row(blockID: "exact-quote-block"))
        #expect(opened.count == 1)
        #expect(opened[0].objectID == "related")
        #expect(opened[0].blockID == "exact-quote-block")
        action(row(blockID: ""))
        action(row(blockID: "related"))
        action(row(spaceID: "foreign", blockID: "exact-quote-block"))
        #expect(opened.count == 1)
        action(row())
        #expect(opened.count == 2)
        #expect(opened[1].objectID == "related" && opened[1].blockID == nil)
        session.deactivateDocument()
        action(row(blockID: "exact-quote-block"))
        #expect(opened.count == 2)
    }

    @Test("Replacing the root selection invalidates captured navigation and close callbacks")
    func changedRootSelectionRejectsCapturedCallbacks() throws {
        let probe = T5ActionAssociationProbe(items: [:])
        let session = TorahEditorSession(
            spaceId: "space", objectId: "origin",
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: probe
        )
        var opened: [String] = []
        session.installOpenObjectHandler { objectID, _ in opened.append(objectID) }
        session.selection = selection
        let previousActions = session.hostActions
        let replacement = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Exodus 1")
        session.selection = replacement

        previousActions.onOpenRelatedDocument?(row())
        previousActions.onClose?()
        #expect(opened.isEmpty)
        #expect(session.selection?.id == replacement.id)
        session.hostActions.onOpenRelatedDocument?(row())
        #expect(opened == ["related"])
    }

    @Test("Dismissed inspector callbacks cannot navigate or close a new presentation")
    func dismissedInspectorCallbacksAreRetired() throws {
        let probe = T5ActionAssociationProbe(items: [:])
        let session = TorahEditorSession(
            spaceId: "space", objectId: "origin",
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: probe
        )
        var opened: [String] = []
        session.installOpenObjectHandler { objectID, _ in opened.append(objectID) }
        session.openResolvedReferenceFromStandaloneSearch(selection)
        let dismissedActions = session.hostActions
        dismissedActions.onClose?()
        #expect(session.selection == nil)
        dismissedActions.onOpenRelatedDocument?(row())
        #expect(opened.isEmpty)

        session.openResolvedReferenceFromStandaloneSearch(selection)
        dismissedActions.onClose?()
        #expect(session.selection?.id == selection.id)
        session.hostActions.onOpenRelatedDocument?(row())
        #expect(opened == ["related"])
    }

    @Test("Late Note and related-document failures cannot replace a new session message", arguments: [false, true])
    func lateUnlinkFailureIsIgnoredAfterDocumentLifetimeEnds(isNote: Bool) async throws {
        let probe = T5ActionAssociationProbe(items: [:], heldRead: 1, failingRead: 1)
        let session = TorahEditorSession(
            spaceId: "space", objectId: "origin",
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: probe
        )
        session.selection = selection
        var didChange = false
        let request = Task { @MainActor in
            if isNote {
                let note = TorahInspectorNote(id: "note-link", selectedText: "", note: "Note", tag: "Anytype")
                await session.unlink(note: note, for: selection) { didChange = true }
            } else {
                await session.unlink(document: row(), for: selection) { didChange = true }
            }
        }
        await probe.waitUntilReadIsHeld()
        session.deactivateDocument()
        session.activateDocument()
        session.message = "Current document message"
        await probe.releaseRead()
        await request.value

        #expect(session.message == "Current document message")
        #expect(!didChange)
        #expect(await probe.effects().removals.isEmpty)
    }

    @Test("Unlink rejects revoked authority before reading or mutating a related document")
    func unlinkRejectsDeniedAuthorityAtEntry() async throws {
        let probe = T5ActionAssociationProbe(items: ["related": [source.item]])
        let service = AnytypeTorahSpaceRelatedDocumentsService(associations: probe)
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await service.unlink(document: row(), selection: selection, spaceID: "space") {
                throw TorahAssociationRepositoryError.permissionDenied
            }
        }
        let effects = await probe.effects()
        #expect(effects.reads == 0)
        #expect(effects.removals.isEmpty)
    }

    @Test("A foreign-Space row is rejected before any association read")
    func unlinkRejectsForeignSpaceBeforeRead() async throws {
        let probe = T5ActionAssociationProbe(items: ["related": [source.item]])
        let service = AnytypeTorahSpaceRelatedDocumentsService(associations: probe)
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await service.unlink(document: row(spaceID: "other-space"), selection: selection, spaceID: "space", authorize: {})
        }
        let effects = await probe.effects()
        #expect(effects.reads == 0)
        #expect(effects.removals.isEmpty)
    }

    @Test("Revocation while a canonical read is pending prevents the following unlink")
    func unlinkRechecksAuthorityAfterSuspendedRead() async throws {
        let probe = T5ActionAssociationProbe(items: ["related": [source.item]], heldRead: 1)
        let service = AnytypeTorahSpaceRelatedDocumentsService(associations: probe)
        var permitted = true
        let request = Task { @MainActor in
            try await service.unlink(document: row(), selection: selection, spaceID: "space") {
                guard permitted else { throw TorahAssociationRepositoryError.permissionDenied }
            }
        }
        await probe.waitUntilReadIsHeld()
        permitted = false
        await probe.releaseRead()
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await request.value
        }
        #expect(await probe.effects().removals.isEmpty)
    }

    @Test("Cancellation after a noncooperative canonical read cannot dispatch unlink")
    func cancelledUnlinkDoesNotMutateAfterRead() async throws {
        let probe = T5ActionAssociationProbe(items: ["related": [source.item]], heldRead: 1)
        let service = AnytypeTorahSpaceRelatedDocumentsService(associations: probe)
        let request = Task { @MainActor in
            try await service.unlink(document: row(), selection: selection, spaceID: "space", authorize: {})
        }
        await probe.waitUntilReadIsHeld()
        request.cancel()
        await probe.releaseRead()
        await #expect(throws: CancellationError.self) {
            try await request.value
        }
        #expect(await probe.effects().removals.isEmpty)
    }

    @Test("Unlink removes only the selected canonical source")
    func unlinkRemovesOnlyTheSelectedCanonicalSource() async throws {
        let selected = source.item
        let other = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:4").item
        let probe = T5ActionAssociationProbe(items: ["related": [selected, other]])
        let service = AnytypeTorahSpaceRelatedDocumentsService(associations: probe)
        try await service.unlink(document: row(), selection: selection, spaceID: "space", authorize: {})
        #expect(await probe.effects().removals == [selected.id])
    }

    @Test("Note unlink rechecks authority after resolving the Note's canonical links")
    func noteUnlinkStopsBeforeBothSourceAndOriginMutationWhenRevoked() async throws {
        let originLink = TorahAssociationItem(
            id: "note-link", kind: .ref, role: .context, providerID: "sefaria",
            externalID: "related", canonicalKey: "anytype-note:related", labelHe: "Note",
            customMetadata: ["anytypeNoteObjectId": "related", "torahSelectionId": selection.id]
        )
        let probe = T5ActionAssociationProbe(
            items: ["origin": [originLink], "related": [source.item]], heldRead: 2
        )
        let service = AnytypeTorahNotesService(spaceId: "space", objectId: "origin", associations: probe)
        var permitted = true
        let request = Task { @MainActor in
            try await service.unlink(noteId: "note-link", for: selection) {
                guard permitted else { throw TorahAssociationRepositoryError.permissionDenied }
            }
        }
        await probe.waitUntilReadIsHeld()
        permitted = false
        await probe.releaseRead()
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await request.value
        }
        #expect(await probe.effects().removals.isEmpty)
    }

    private func row(spaceID: String = "space", blockID: String? = nil) -> TorahRelatedDocument {
        TorahRelatedDocument(
            id: "related-row", spaceID: spaceID, objectID: "related", title: "Related",
            sourceReference: source.canonicalReference, blockID: blockID, canUnlink: true
        )
    }
}

private actor T5ActionAssociationProbe: AnytypeTorahAssociationSnapshotRepository {
    struct Effects: Sendable {
        let reads: Int
        let removals: [String]
    }

    private let items: [String: [TorahAssociationItem]]
    private let heldRead: Int?
    private let failingRead: Int?
    private var readCount = 0
    private var removals: [String] = []
    private var readIsHeld = false
    private var readWaiter: CheckedContinuation<Void, Never>?
    private var releaseContinuation: CheckedContinuation<Void, Never>?

    init(items: [String: [TorahAssociationItem]], heldRead: Int? = nil, failingRead: Int? = nil) {
        self.items = items
        self.heldRead = heldRead
        self.failingRead = failingRead
    }

    func waitUntilReadIsHeld() async {
        if readIsHeld { return }
        await withCheckedContinuation { readWaiter = $0 }
    }

    func releaseRead() {
        releaseContinuation?.resume()
        releaseContinuation = nil
    }

    func effects() -> Effects {
        Effects(reads: readCount, removals: removals)
    }

    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        readCount += 1
        let currentRead = readCount
        if currentRead == heldRead {
            await withCheckedContinuation { continuation in
                releaseContinuation = continuation
                readIsHeld = true
                readWaiter?.resume()
                readWaiter = nil
            }
        }
        if currentRead == failingRead {
            throw TorahAssociationRepositoryError.backendFailure("Delayed canonical read failure")
        }
        return items[objectId] ?? []
    }

    func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord] {
        []
    }

    func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        []
    }

    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String) async throws {
        removals.append(associationId)
    }

    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw TorahAssociationRepositoryError.backendFailure("Unexpected add")
    }

    func upsertAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw TorahAssociationRepositoryError.backendFailure("Unexpected upsert")
    }

    func updateAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw TorahAssociationRepositoryError.backendFailure("Unexpected update")
    }
}
