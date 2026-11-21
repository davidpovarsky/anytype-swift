import Foundation
import Services
import AnytypeCore

final class DetailsService: DetailsServiceProtocol, Sendable {
    
    private let service: any ObjectActionsServiceProtocol
    private let fileService: any FileActionsServiceProtocol

    init() {
        service = Container.shared.objectActionsService()
        fileService = Container.shared.fileActionsService()
    }

    private init(service: any ObjectActionsServiceProtocol, fileService: any FileActionsServiceProtocol) {
        self.service = service
        self.fileService = fileService
    }

    @MainActor
    func documentOwned(owner: EditorDocumentWriteOwner, preloads: DocumentOwnedFilePreloads,
                       staging: DocumentOwnedFileStaging) throws -> any DetailsServiceProtocol {
        try owner.validateOwnership()
        try staging.requireOwner(owner)
        let original = DetailsService(
            service: DocumentOwnedObjectActionsService(owner: owner, service: service),
            fileService: try DocumentOwnedFileActionsService.bindOriginal(
                fileService, owner: owner, preloads: preloads, staging: staging
            )
        )
        return DocumentOwnedDetailsService(owner: owner, service: original)
    }
    
    // MARK: - DetailsServiceProtocol

    func updateBundledDetails(objectId: String, bundledDetails: [BundledDetails]) async throws {
        try await service.updateBundledDetails(contextID: objectId, details: bundledDetails)
    }
    
    func updateDetails(contextId: String, relationKey: String, value: DataviewGroupValue) async throws {
        try await service.updateDetails(contextId: contextId, relationKey: relationKey, value: value)
    }

    func setLayout(objectId: String, detailsLayout: DetailsLayout) async throws {
        try await service.updateLayout(contextID: objectId, value: detailsLayout.rawValue)
    }
    
    func setCover(objectId: String, spaceId: String, source: FileUploadingSource, createdInContext: String, createdInContextRef: String) async throws {
        let data = try await fileService.createFileData(source: source)
        let fileDetails = try await fileService.uploadFileObject(spaceId: spaceId, data: data, origin: .none, createdInContext: createdInContext, createdInContextRef: createdInContextRef)
        try await setCover(objectId: objectId, imageObjectId: fileDetails.id)
    }
    
    func setCover(objectId: String, imageObjectId: String) async throws {
        try await updateBundledDetails(
            objectId: objectId,
            bundledDetails: [.coverType(CoverType.uploadedImage), .coverId(imageObjectId)]
        )
    }
}
