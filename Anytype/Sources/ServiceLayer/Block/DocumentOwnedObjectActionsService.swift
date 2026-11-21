import Services
import ProtobufMessages
import AnytypeCore

/// The original object service remains the sole implementation. This adapter
/// carries the prepared document's owner into every actual Invocation dispatch.
struct DocumentOwnedObjectActionsService: ObjectActionsServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: any ObjectActionsServiceProtocol

    init(owner: EditorDocumentWriteOwner, service: any ObjectActionsServiceProtocol) {
        self.owner = owner
        self.service = service
    }

    func createObject(name: String, typeUniqueKey: ObjectTypeUniqueKey,
                      shouldDeleteEmptyObject: Bool, shouldSelectType: Bool, shouldSelectTemplate: Bool,
                      spaceId: String, origin: ObjectOrigin, templateId: String?,
                      createdInContext: String, createdInContextRef: String,
                      additionalDetails: [BundledDetails]) async throws -> ObjectDetails {
        try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) { [service] in
            try await service.createObject(name: name, typeUniqueKey: typeUniqueKey,
                shouldDeleteEmptyObject: shouldDeleteEmptyObject, shouldSelectType: shouldSelectType,
                shouldSelectTemplate: shouldSelectTemplate, spaceId: spaceId, origin: origin,
                templateId: templateId, createdInContext: createdInContext,
                createdInContextRef: createdInContextRef, additionalDetails: additionalDetails)
        }
    }

    func delete(objectIds: [String]) async throws {
        let context = try singleOwnedContext(objectIds)
        try await owner.performMutation(contextId: context) { [service] in try await service.delete(objectIds: objectIds) }
    }

    func setArchive(objectIds: [String], _ isArchived: Bool) async throws {
        let context = try singleOwnedContext(objectIds)
        try await owner.performMutation(contextId: context) { [service] in
            try await service.setArchive(objectIds: objectIds, isArchived)
        }
    }

    func setPin(objectIds: [String], _ isPinned: Bool) async throws {
        let context = try singleOwnedContext(objectIds)
        try await owner.performMutation(contextId: context) { [service] in
            try await service.setPin(objectIds: objectIds, isPinned)
        }
    }

    func setLocked(_ isLocked: Bool, objectId: String) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.setLocked(isLocked, objectId: objectId)
        }
    }

    func updateLayout(contextID: String, value: Int) async throws {
        try await owner.performMutation(contextId: contextID) { [service] in
            try await service.updateLayout(contextID: contextID, value: value)
        }
    }

    func duplicate(objectId: String) async throws -> String {
        try await owner.performMutation(contextId: objectId) { [service] in try await service.duplicate(objectId: objectId) }
    }

    func applyTemplate(objectId: String, templateId: String) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.applyTemplate(objectId: objectId, templateId: templateId)
        }
    }

    func updateBundledDetails(contextID: String, details: [BundledDetails]) async throws {
        try await owner.performMutation(contextId: contextID) { [service] in
            try await service.updateBundledDetails(contextID: contextID, details: details)
        }
    }

    func updateDetails(contextId: String, relationKey: String, value: DataviewGroupValue) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.updateDetails(contextId: contextId, relationKey: relationKey, value: value)
        }
    }

    func setInternalFlags(contextId: String, internalFlags: [Int]) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.setInternalFlags(contextId: contextId, internalFlags: internalFlags)
        }
    }

    func addObjectsToCollection(contextId: String, objectIds: [String]) async throws {
        // Listed IDs are references added to the owned collection, not separate
        // mutation contexts. Preserve the original service's reference behavior.
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.addObjectsToCollection(contextId: contextId, objectIds: objectIds)
        }
    }

    func setObjectType(objectId: String, typeUniqueKey: ObjectTypeUniqueKey) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.setObjectType(objectId: objectId, typeUniqueKey: typeUniqueKey)
        }
    }

    func setObjectSetType(objectId: String) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in try await service.setObjectSetType(objectId: objectId) }
    }

    func setObjectCollectionType(objectId: String) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.setObjectCollectionType(objectId: objectId)
        }
    }

    func setSource(objectId: String, source: [String]) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in
            try await service.setSource(objectId: objectId, source: source)
        }
    }

    func undo(objectId: String) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in try await service.undo(objectId: objectId) }
    }

    func redo(objectId: String) async throws {
        try await owner.performMutation(contextId: objectId) { [service] in try await service.redo(objectId: objectId) }
    }

    func move(dashboadId: String, blockId: String, dropPositionblockId: String,
              position: Anytype_Model_Block.Position) async throws {
        try await owner.performMutation(contextId: dashboadId) { [service] in
            try await service.move(dashboadId: dashboadId, blockId: blockId,
                                   dropPositionblockId: dropPositionblockId, position: position)
        }
    }

    func createSet(name: String, iconEmoji: Emoji?, setOfObjectType: String, spaceId: String) async throws -> ObjectDetails {
        try await owner.performMutation(spaceId: spaceId) { [service] in
            try await service.createSet(name: name, iconEmoji: iconEmoji, setOfObjectType: setOfObjectType, spaceId: spaceId)
        }
    }

    private func singleOwnedContext(_ ids: [String]) throws -> String {
        guard let first = ids.first, !first.isEmpty,
              ids.allSatisfy({ $0.utf8.elementsEqual(first.utf8) }) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        return first
    }
}
