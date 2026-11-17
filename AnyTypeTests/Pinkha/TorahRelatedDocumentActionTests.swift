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
        session.installOpenObjectHandler { opened.append($0) }
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

    private func row(spaceID: String = "space") -> TorahRelatedDocument {
        TorahRelatedDocument(
            id: "related-row", spaceID: spaceID, objectID: "related", title: "Related",
            sourceReference: source.canonicalReference, canUnlink: true
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
    private var readCount = 0
    private var removals: [String] = []
    private var readIsHeld = false
    private var readWaiter: CheckedContinuation<Void, Never>?
    private var releaseContinuation: CheckedContinuation<Void, Never>?

    init(items: [String: [TorahAssociationItem]], heldRead: Int? = nil) {
        self.items = items
        self.heldRead = heldRead
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
        if readCount == heldRead {
            await withCheckedContinuation { continuation in
                releaseContinuation = continuation
                readIsHeld = true
                readWaiter?.resume()
                readWaiter = nil
            }
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
