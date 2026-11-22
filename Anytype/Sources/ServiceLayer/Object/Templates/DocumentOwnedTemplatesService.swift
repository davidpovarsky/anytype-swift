import Services

/// Keeps every original template operation in the original Services module.
/// Selected existing objects acquire their own original document owner, while
/// retaining the parent's captured account/source and pending-operation scope.
final class DocumentOwnedTemplatesService: TemplatesServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let childPreparation: PreparedEditorChildPreparation
    private let service: any TemplatesServiceProtocol
    private let spaceId: String

    @MainActor
    private init(owner: EditorDocumentWriteOwner, childPreparation: PreparedEditorChildPreparation,
                 service: any TemplatesServiceProtocol, spaceId: String) {
        self.owner = owner
        self.childPreparation = childPreparation
        self.service = service
        self.spaceId = spaceId
    }

    @MainActor
    static func bindOriginal(_ service: any TemplatesServiceProtocol,
                             owner: EditorDocumentWriteOwner,
                             childPreparation: PreparedEditorChildPreparation,
                             spaceId: String) throws -> any TemplatesServiceProtocol {
        try owner.performSynchronousOperation(spaceId: spaceId, requiresEditing: false) {}
        return try DocumentOwnedTemplatesService(
            owner: owner, childPreparation: childPreparation,
            service: OriginalTemplatesServiceSpaceBinding.bind(service, spaceId: spaceId),
            spaceId: spaceId
        )
    }

    func cloneTemplate(blockId: String) async throws {
        try await childPreparation.performMutation(data: .init(objectId: blockId, spaceId: spaceId), requiredPermissions: [.duplicate]) { [service] _ in
            try await service.cloneTemplate(blockId: blockId)
        }
    }

    func createTemplateFromObjectType(objectTypeId: String, spaceId: String) async throws -> String {
        try await owner.performSynchronousOperation(spaceId: spaceId, requiresEditing: false) {}
        return try await childPreparation.performMutation(
            data: .init(objectId: objectTypeId, spaceId: spaceId), requiredPermissions: [.editDetails]
        ) { [service] _ in
            try await service.createTemplateFromObjectType(objectTypeId: objectTypeId, spaceId: spaceId)
        }
    }

    func createTemplateFromObject(objectId: String) async throws -> String {
        try await childPreparation.performMutation(data: .init(objectId: objectId, spaceId: spaceId), requiredPermissions: [.makeAsTemplate]) { [service] _ in
            try await service.createTemplateFromObject(objectId: objectId)
        }
    }

    func deleteTemplate(templateId: String) async throws {
        try await childPreparation.performMutation(data: .init(objectId: templateId, spaceId: spaceId), requiredPermissions: [.archive]) { [service] _ in
            try await service.deleteTemplate(templateId: templateId)
        }
    }

    func setTemplateAsDefaultForType(objectTypeId: String, templateId: String) async throws {
        if templateId.isEmpty {
            try await childPreparation.performMutation(
                data: .init(objectId: objectTypeId, spaceId: spaceId), requiredPermissions: [.editDetails]
            ) { [service] _ in
                try await service.setTemplateAsDefaultForType(objectTypeId: objectTypeId, templateId: templateId)
            }
            return
        }
        // The selected template and the mutated type have different native
        // identities. Keep both actual owners in the same captured ancestry so
        // revoking the selected template also refuses the later type RPC.
        try await childPreparation.performMutation(
            data: .init(objectId: templateId, spaceId: spaceId), requiredPermissions: [.templateSetAsDefault]
        ) { [service, spaceId, childPreparation] selectedTemplateOwner in
            let typePreparation = try await childPreparation.deriving(owner: selectedTemplateOwner)
            try await typePreparation.performMutation(
                data: .init(objectId: objectTypeId, spaceId: spaceId), requiredPermissions: [.editDetails]
            ) { _ in
                try await service.setTemplateAsDefaultForType(objectTypeId: objectTypeId, templateId: templateId)
            }
        }
    }
}
