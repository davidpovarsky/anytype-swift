import Foundation
import PinkhaKit
import TorahInspectorCore

public typealias TorahAssociationWriteAuthorization = @MainActor @Sendable () throws -> Void

/// Canonical document snapshot and the original immediately-before-write guard.
public protocol TorahAssociationSnapshotRepository: TorahAssociationRepository {
    func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord]
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String,
                        authorize: @escaping TorahAssociationWriteAuthorization) async throws -> TorahAssociationItem
}

public enum TorahAssociationPersistenceState: Sendable, Equatable {
    case waiting
    case saving
    case saved
    case conflict(String)
    case uncertain(String)
    case error(String)
}

/// UI domain operations. The owning engine session supplies all persistence.
@MainActor
public protocol TorahEditorNotesService: AnyObject, Sendable {
    func notes(for selection: TorahInspectorSelection) async throws -> [TorahInspectorNote]
    func relatedDocuments(for selection: TorahInspectorSelection) async throws -> TorahRelatedDocumentsSnapshot
    func createNote(for selection: TorahInspectorSelection,
                    authorize: @escaping TorahAssociationWriteAuthorization) async throws -> T5NoteCreationOutcome
    func noteObjectId(noteId: String, for selection: TorahInspectorSelection) async throws -> String?
    func unlink(noteId: String, for selection: TorahInspectorSelection,
                authorize: @escaping TorahAssociationWriteAuthorization) async throws
    func unlink(document: TorahRelatedDocument, for selection: TorahInspectorSelection,
                authorize: @escaping TorahAssociationWriteAuthorization) async throws
}
