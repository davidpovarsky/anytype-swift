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
    private let associations: AnytypeTorahAssociationRepository

    @Injected(\.objectActionsService)
    private var objectActionsService: any ObjectActionsServiceProtocol
    @Injected(\.blockService)
    private var blockService: any BlockServiceProtocol

    init(
        spaceId: String,
        objectId: String,
        associations: AnytypeTorahAssociationRepository
    ) {
        self.spaceId = spaceId
        self.objectId = objectId
        self.associations = associations
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

    func createNote(for selection: TorahInspectorSelection) async throws -> TorahInspectorNote {
        let title = "הערה על \(selection.relationshipRef)"
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

        let sourceLine = BlockInformation.empty(
            content: .text(.plain("מקור: \(selection.relationshipRef)", contentType: .text))
        )
        let lastBlockId = try await blockService.lastBlockId(from: details.id, spaceId: spaceId)
        _ = try await blockService.add(
            contextId: details.id,
            targetId: lastBlockId,
            info: sourceLine,
            position: .bottom
        )

        let item = TorahAssociationItem(
            kind: .ref,
            role: .context,
            providerID: selection.providerID,
            externalID: details.id,
            canonicalKey: "anytype-note:\(details.id)",
            labelHe: title,
            labelEn: "Note on \(selection.relationshipRef)",
            createdAt: Date(),
            customMetadata: [
                MetadataKey.noteObjectId: details.id,
                MetadataKey.selectionId: selection.id
            ]
        )

        do {
            let saved = try await associations.addAssociation(
                item,
                target: .object(objectId: objectId),
                spaceId: spaceId
            )
            return TorahInspectorNote(
                id: saved.id,
                selectedText: selection.relationshipRef,
                note: title,
                tag: "Anytype"
            )
        } catch {
            try? await objectActionsService.delete(objectIds: [details.id])
            throw error
        }
    }

    func noteObjectId(noteId: String, for selection: TorahInspectorSelection) async throws -> String? {
        try await noteItems(for: selection)
            .first { $0.id == noteId }?
            .customMetadata?[MetadataKey.noteObjectId]
    }

    func unlink(noteId: String, for selection: TorahInspectorSelection) async throws {
        guard try await noteItems(for: selection).contains(where: { $0.id == noteId }) else { return }
        try await associations.removeAssociation(
            associationId: noteId,
            target: .object(objectId: objectId),
            spaceId: spaceId
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
