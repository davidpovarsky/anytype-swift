#if canImport(SwiftUI)
import Foundation
import PinkhaKit
import Testing
import TorahInspectorCore
@testable import PinkhaTorahPresentation

@Suite("Shared related-document owner lifetime")
@MainActor
struct SharedRelatedDocumentsLifetimeTests {
    @Test
    func documentRetirementFencesRelatedCacheUntilExplicitReactivation() async throws {
        let notes = LifetimeRelatedNotes()
        let session = TorahEditorSession(
            spaceId: "space", objectId: "document",
            workspace: try AnytypeTorahWorkspace.sefaria(),
            associations: LifetimeUnusedAssociations(), notesService: notes
        )
        let selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 1")
        let first = try await session.repository.relatedDocuments(for: selection)
        #expect(first.documents.first?.title == "Version 1")
        #expect(try await session.repository.relatedDocuments(for: selection) == first)
        #expect(notes.calls == 1)

        session.deactivateDocument()
        do {
            _ = try await session.repository.relatedDocuments(for: selection)
            Issue.record("The shared session retained related-read authority after leaving its document")
        } catch TorahRelatedDocumentsAccessError.invalidated { }
        #expect(notes.calls == 1)

        session.activateDocument()
        let fresh = try await session.repository.relatedDocuments(for: selection)
        #expect(fresh.documents.first?.title == "Version 2")
        #expect(notes.calls == 2)
    }
}

/// Controller wiring evidence only; no native persistence or ACL proof.
@MainActor
private final class LifetimeRelatedNotes: TorahEditorNotesService {
    var calls = 0
    func relatedDocuments(for selection: TorahInspectorSelection) async throws -> TorahRelatedDocumentsSnapshot {
        calls += 1
        return .init(documents: [
            .init(id: "related", spaceID: "space", objectID: "related", title: "Version " + String(calls),
                  sourceReference: selection.relationshipRef)
        ], coverage: .indexedDocumentsOnly)
    }
    func notes(for selection: TorahInspectorSelection) async throws -> [TorahInspectorNote] { [] }
    func createNote(for selection: TorahInspectorSelection,
                    authorize: @escaping TorahAssociationWriteAuthorization) async throws -> T5NoteCreationOutcome {
        throw CancellationError()
    }
    func noteObjectId(noteId: String, for selection: TorahInspectorSelection) async throws -> String? { nil }
    func unlink(noteId: String, for selection: TorahInspectorSelection,
                authorize: @escaping TorahAssociationWriteAuthorization) async throws { throw CancellationError() }
    func unlink(document: TorahRelatedDocument, for selection: TorahInspectorSelection,
                authorize: @escaping TorahAssociationWriteAuthorization) async throws { throw CancellationError() }
}

private actor LifetimeUnusedAssociations: TorahAssociationSnapshotRepository {
    func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord] { [] }
    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] { [] }
    func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem] { [] }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String,
                        authorize: @escaping TorahAssociationWriteAuthorization) async throws -> TorahAssociationItem {
        throw CancellationError()
    }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw CancellationError()
    }
    func upsertAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw CancellationError()
    }
    func updateAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        throw CancellationError()
    }
    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String) async throws {
        throw CancellationError()
    }
}
#endif
