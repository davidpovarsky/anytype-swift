import Services
@preconcurrency import Combine

enum DocumentOwnedHeaderError: Error, Sendable {
    case unsupportedOriginalDelegate
}

final class DocumentOwnedObjectHeaderUploadingService: ObjectHeaderUploadingServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: ObjectHeaderUploadingService

    init(owner: EditorDocumentWriteOwner, service: ObjectHeaderUploadingService) {
        self.owner = owner
        self.service = service
    }

    @MainActor
    static func bindOriginal(_ service: any ObjectHeaderUploadingServiceProtocol,
                             owner: EditorDocumentWriteOwner,
                             preloads: DocumentOwnedFilePreloads,
                             staging: DocumentOwnedFileStaging) throws -> any ObjectHeaderUploadingServiceProtocol {
        guard let original = service as? ObjectHeaderUploadingService else {
            throw DocumentOwnedHeaderError.unsupportedOriginalDelegate
        }
        return try original.documentOwned(owner: owner, preloads: preloads, staging: staging)
    }

    func coverUploadPublisher(objectId: String, spaceId: String) -> AnyPublisher<ObjectHeaderUpdate, Never> {
        // This is the original non-replaying publisher. Authorization is checked
        // at its actual send and again in the original MainActor view-model sink.
        service.coverUploadPublisher(objectId: objectId, spaceId: spaceId)
    }

    func handleCoverAction(objectId: String, spaceId: String, action: ObjectCoverPickerAction) async throws {
        try await owner.performMutation(spaceId: spaceId, createdInContext: objectId) { [service] in
            try await service.handleCoverAction(objectId: objectId, spaceId: spaceId, action: action)
        }
    }

    func handleIconAction(objectId: String, spaceId: String, action: ObjectIconPickerAction) async throws {
        try await owner.performMutation(spaceId: spaceId, createdInContext: objectId) { [service] in
            try await service.handleIconAction(objectId: objectId, spaceId: spaceId, action: action)
        }
    }
}
