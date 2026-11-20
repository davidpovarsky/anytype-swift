import Foundation
import Services
import ProtobufMessages

enum DocumentOwnedBlockServiceError: Error, Sendable, Equatable {
    case separateDocumentAuthorityRequired
    case separateObjectAuthorityRequired
}

/// Original block operations for one prepared document. This seam does not
/// grant authority to mutate another document or create/promote an object.
final class DocumentOwnedBlockService: BlockServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: any BlockServiceProtocol

    init(owner: EditorDocumentWriteOwner, service: any BlockServiceProtocol) {
        self.owner = owner
        self.service = service
    }

    func add(contextId: String, targetId: String, info: BlockInformation, position: BlockPosition) async throws -> String {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.add(contextId: contextId, targetId: targetId, info: info, position: position)
        }
    }

    func addFirstBlock(contextId: String, info: BlockInformation) async throws -> String {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.addFirstBlock(contextId: contextId, info: info)
        }
    }

    func delete(contextId: String, blockIds: [String]) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.delete(contextId: contextId, blockIds: blockIds)
        }
    }

    func duplicate(contextId: String, targetId: String, blockIds: [String], position: BlockPosition) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.duplicate(contextId: contextId, targetId: targetId, blockIds: blockIds, position: position)
        }
    }

    func move(contextId: String, blockIds: [String], targetContextID: String, dropTargetID: String, position: BlockPosition) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            guard targetContextID.utf8.elementsEqual(contextId.utf8) else {
                throw DocumentOwnedBlockServiceError.separateDocumentAuthorityRequired
            }
            try await service.move(contextId: contextId, blockIds: blockIds, targetContextID: targetContextID, dropTargetID: dropTargetID, position: position)
        }
    }

    func setAlign(objectId: String, blockIds: [String], alignment: LayoutAlignment) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.setAlign(objectId: objectId, blockIds: blockIds, alignment: alignment)
        }
    }

    func setBackgroundColor(objectId: String, blockIds: [String], color: MiddlewareColor) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.setBackgroundColor(objectId: objectId, blockIds: blockIds, color: color)
        }
    }

    func setFields(objectId: String, blockId: String, fields: BlockFields) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.setFields(objectId: objectId, blockId: blockId, fields: fields)
        }
    }

    func setBlockColor(objectId: String, blockIds: [String], color: MiddlewareColor) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.setBlockColor(objectId: objectId, blockIds: blockIds, color: color)
        }
    }

    func replace(objectId: String, blockIds: [String], targetId: String) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.replace(objectId: objectId, blockIds: blockIds, targetId: targetId)
        }
    }

    func replaceBlock(contextId: String, blockId: String, info: BlockInformation) async throws -> String {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.replaceBlock(contextId: contextId, blockId: blockId, info: info)
        }
    }

    func move(objectId: String, blockId: String, targetId: String, position: Anytype_Model_Block.Position) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.move(objectId: objectId, blockId: blockId, targetId: targetId, position: position)
        }
    }

    func moveToPage(objectId: String, blockIds: [String], pageId: String) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            guard pageId.utf8.elementsEqual(objectId.utf8) else {
                throw DocumentOwnedBlockServiceError.separateDocumentAuthorityRequired
            }
            try await service.moveToPage(objectId: objectId, blockIds: blockIds, pageId: pageId)
        }
    }

    func setLinkAppearance(objectId: String, blockIds: [String], appearance: BlockLink.Appearance) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.setLinkAppearance(objectId: objectId, blockIds: blockIds, appearance: appearance)
        }
    }

    func changeMarkup(objectId: String, blockIds: [String], markType: MarkupType) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.changeMarkup(objectId: objectId, blockIds: blockIds, markType: markType)
        }
    }

    func lastBlockId(from objectId: String, spaceId: String) async throws -> String {
        try await owner.performRead(contextId: objectId, spaceId: spaceId) { [service] in
            try await service.lastBlockId(from: objectId, spaceId: spaceId)
        }
    }

    func convertChildrenToObjects(contextId: String, blocksIds: [String], typeUniqueKey: ObjectTypeUniqueKey, templateId: String) async throws -> [String] {
        try await owner.performMutation(contextId: contextId) { () async throws -> [String] in
            throw DocumentOwnedBlockServiceError.separateObjectAuthorityRequired
        }
    }

    func createBlockLink(contextId: String, targetId: String, spaceId: String, details: [BundledDetails], typeUniqueKey: ObjectTypeUniqueKey, position: BlockPosition, templateId: String) async throws -> String {
        try await owner.performMutation(contextId: contextId) { () async throws -> String in
            throw DocumentOwnedBlockServiceError.separateObjectAuthorityRequired
        }
    }
}
