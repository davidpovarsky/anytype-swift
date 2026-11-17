import Foundation
import AnytypeCore
import Factory
import PinkhaKit
import Services
import TorahInspectorCore

@MainActor
final class AnytypeTorahNotesService {
    private enum MetadataKey {
        static let noteObjectId = "anytypeNoteObjectId"
        static let selectionId = "torahSelectionId"
    }

    let spaceId: String
    let objectId: String
    private let associations: any TorahAssociationRepository
    private let relatedDocumentsService: AnytypeTorahSpaceRelatedDocumentsService
    private let noteCreationFlow = T5NoteCreationFlow()

    @Injected(\.objectActionsService)
    private var objectActionsService: any ObjectActionsServiceProtocol
    @Injected(\.blockService)
    private var blockService: any BlockServiceProtocol

    init(
        spaceId: String,
        objectId: String,
        associations: any TorahAssociationRepository
    ) {
        self.spaceId = spaceId
        self.objectId = objectId
        self.associations = associations
        self.relatedDocumentsService = AnytypeTorahSpaceRelatedDocumentsService(associations: associations)
    }

    func notes(for selection: TorahInspectorSelection) async throws -> [TorahInspectorNote] {
        try await noteItems(for: selection).map { item in
            TorahInspectorNote(
                id: item.id,
                selectedText: selection.relationshipRef,
                note: item.labelHe,
                tag: "Anytype"
            )
        }
    }

    func relatedDocuments(
        for selection: TorahInspectorSelection
    ) async throws -> TorahRelatedDocumentsSnapshot {
        try await relatedDocumentsService.relatedDocuments(spaceID: spaceId, selection: selection)
    }

    func createNote(
        for selection: TorahInspectorSelection, authorize: @MainActor () throws -> Void
    ) async throws -> T5NoteCreationOutcome {
        try Task.checkCancellation()
        try authorize()
        let source = T5SourceIdentity(providerID: selection.providerID, canonicalReference: selection.relationshipRef)
        let title = "הערה על \(selection.relationshipRef)"
        return try await noteCreationFlow.create(
            source: source,
            createObject: { [self] in
                try authorize()
                let details = try await objectActionsService.createObject(
                    name: title,
                    typeUniqueKey: .note,
                    shouldDeleteEmptyObject: false,
                    shouldSelectType: false,
                    shouldSelectTemplate: false,
                    spaceId: spaceId,
                    origin: .none,
                    templateId: nil
                )
                return details.id
            },
            linkSource: { [self] noteObjectID in
                try authorize()
                _ = try await associations.addAssociation(
                    source.item, target: .object(objectId: noteObjectID), spaceId: spaceId
                )
            },
            addSourceLine: { [self] noteObjectID in
                try authorize()
                let sourceLine = BlockInformation.empty(
                    content: .text(.plain("מקור: \(selection.relationshipRef)", contentType: .text))
                )
                let lastBlockId = try await blockService.lastBlockId(from: noteObjectID, spaceId: spaceId)
                try Task.checkCancellation()
                try authorize()
                _ = try await blockService.add(
                    contextId: noteObjectID, targetId: lastBlockId, info: sourceLine, position: .bottom
                )
            },
            linkOrigin: { [self] noteObjectID in
                try authorize()
                let item = TorahAssociationItem(
                    kind: .ref,
                    role: .context,
                    providerID: selection.providerID,
                    externalID: noteObjectID,
                    canonicalKey: "anytype-note:\(noteObjectID)",
                    labelHe: title,
                    labelEn: "Note on \(selection.relationshipRef)",
                    createdAt: Date(),
                    customMetadata: [
                        MetadataKey.noteObjectId: noteObjectID,
                        MetadataKey.selectionId: selection.id
                    ]
                )
                _ = try await associations.addAssociation(
                    item, target: .object(objectId: objectId), spaceId: spaceId
                )
            }
        )
    }

    func noteObjectId(noteId: String, for selection: TorahInspectorSelection) async throws -> String? {
        try await noteItems(for: selection)
            .first { $0.id == noteId }?
            .customMetadata?[MetadataKey.noteObjectId]
    }

    func unlink(
        noteId: String, for selection: TorahInspectorSelection,
        authorize: @MainActor () throws -> Void
    ) async throws {
        try Task.checkCancellation()
        try authorize()
        let resolvedNoteID = try await noteObjectId(noteId: noteId, for: selection)
        try Task.checkCancellation()
        try authorize()
        guard let noteObjectID = resolvedNoteID else { return }
        let source = T5SourceIdentity(providerID: selection.providerID, canonicalReference: selection.relationshipRef)
        let sourceItems = try await associations.listDocumentAssociations(objectId: noteObjectID, spaceId: spaceId)
        for item in sourceItems where source.matches(item) {
            try Task.checkCancellation()
            try authorize()
            try await associations.removeAssociation(
                associationId: item.id, target: .object(objectId: noteObjectID), spaceId: spaceId
            )
        }
        try Task.checkCancellation()
        try authorize()
        try await associations.removeAssociation(
            associationId: noteId,
            target: .object(objectId: objectId),
            spaceId: spaceId
        )
    }

    func unlink(
        document: TorahRelatedDocument, for selection: TorahInspectorSelection,
        authorize: @MainActor () throws -> Void
    ) async throws {
        try await relatedDocumentsService.unlink(
            document: document, selection: selection, spaceID: spaceId, authorize: authorize
        )
    }

    private func noteItems(for selection: TorahInspectorSelection) async throws -> [TorahAssociationItem] {
        try await associations
            .listDocumentAssociations(objectId: objectId, spaceId: spaceId)
            .filter { item in
                item.customMetadata?[MetadataKey.noteObjectId]?.isEmpty == false
                    && item.customMetadata?[MetadataKey.selectionId] == selection.id
            }
    }
}
