import Services
import AnytypeCore

enum DocumentOwnedDetailsError: Error, Sendable {
    case unsupportedOriginalDelegate
}

/// Retains the original details implementation and binds its original object
/// and file dependencies to the prepared document's shared owner.
final class DocumentOwnedDetailsService: DetailsServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: DetailsService

    init(owner: EditorDocumentWriteOwner, service: DetailsService) {
        self.owner = owner
        self.service = service
    }

    @MainActor
    static func bindOriginal(_ service: any DetailsServiceProtocol,
                             owner: EditorDocumentWriteOwner,
                             preloads: DocumentOwnedFilePreloads,
                             staging: DocumentOwnedFileStaging) throws -> any DetailsServiceProtocol {
        guard let original = service as? DetailsService else {
            throw DocumentOwnedDetailsError.unsupportedOriginalDelegate
        }
        return try original.documentOwned(owner: owner, preloads: preloads, staging: staging)
    }

    func updateBundledDetails(objectId: String, bundledDetails: [BundledDetails]) async throws {
        try await owner.performMutation(contextId: objectId, requiredPermissions: [.editDetails]) { [service] in
            try await service.updateBundledDetails(objectId: objectId, bundledDetails: bundledDetails)
        }
    }

    func setLayout(objectId: String, detailsLayout: DetailsLayout) async throws {
        try await owner.performMutation(contextId: objectId, requiredPermissions: [.editDetails, .changeLayout]) { [service] in
            try await service.setLayout(objectId: objectId, detailsLayout: detailsLayout)
        }
    }

    func updateDetails(contextId: String, relationKey: String, value: DataviewGroupValue) async throws {
        try await owner.performMutation(contextId: contextId, requiredPermissions: [.editDetails, .editRelationValues]) { [service] in
            try await service.updateDetails(contextId: contextId, relationKey: relationKey, value: value)
        }
    }

    func setCover(objectId: String, spaceId: String, source: FileUploadingSource,
                  createdInContext: String, createdInContextRef: String) async throws {
        try await owner.performMutation(contextId: objectId, requiredPermissions: [.editDetails, .changeCover]) { [owner, service] in
            try await owner.performMutation(spaceId: spaceId, createdInContext: createdInContext) {
                try await service.setCover(objectId: objectId, spaceId: spaceId, source: source,
                    createdInContext: createdInContext, createdInContextRef: createdInContextRef)
            }
        }
    }

    func setCover(objectId: String, imageObjectId: String) async throws {
        try await owner.performMutation(contextId: objectId, requiredPermissions: [.editDetails, .changeCover]) { [service] in
            try await service.setCover(objectId: objectId, imageObjectId: imageObjectId)
        }
    }
}
