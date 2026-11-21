import UIKit
import Services
import AnytypeCore
@preconcurrency import Combine

protocol ObjectHeaderUploadingServiceProtocol: AnyObject, Sendable {
    
    func coverUploadPublisher(objectId: String, spaceId: String) -> AnyPublisher<ObjectHeaderUpdate, Never>
    
    func handleCoverAction(
        objectId: String,
        spaceId: String,
        action: ObjectCoverPickerAction
    ) async throws
    
    func handleIconAction(objectId: String, spaceId: String, action: ObjectIconPickerAction) async throws
}

final class ObjectHeaderUploadingService: ObjectHeaderUploadingServiceProtocol, Sendable {
    
    private let detailsService: any DetailsServiceProtocol
    private let fileService: any FileActionsServiceProtocol
    private let unsplashService: any UnsplashServiceProtocol
    private let documentWriteOwner: EditorDocumentWriteOwner?

    init() {
        detailsService = Container.shared.detailsService()
        fileService = Container.shared.fileActionsService()
        unsplashService = Container.shared.unsplashService()
        documentWriteOwner = nil
    }

    private init(detailsService: any DetailsServiceProtocol, fileService: any FileActionsServiceProtocol,
                 unsplashService: any UnsplashServiceProtocol, owner: EditorDocumentWriteOwner) {
        self.detailsService = detailsService
        self.fileService = fileService
        self.unsplashService = unsplashService
        documentWriteOwner = owner
    }

    @MainActor
    func documentOwned(owner: EditorDocumentWriteOwner, preloads: DocumentOwnedFilePreloads,
                       staging: DocumentOwnedFileStaging) throws -> any ObjectHeaderUploadingServiceProtocol {
        try owner.validateOwnership()
        try staging.requireOwner(owner)
        let original = ObjectHeaderUploadingService(
            detailsService: try DocumentOwnedDetailsService.bindOriginal(
                detailsService, owner: owner, preloads: preloads, staging: staging
            ),
            fileService: try DocumentOwnedFileActionsService.bindOriginal(
                fileService, owner: owner, preloads: preloads, staging: staging
            ),
            unsplashService: DocumentOwnedUnsplashService(owner: owner, service: unsplashService),
            owner: owner
        )
        return DocumentOwnedObjectHeaderUploadingService(owner: owner, service: original)
    }
    
    private let coverUploadSubject = PassthroughSubject<(objectId: String, spaceId: String, update: ObjectHeaderUpdate), Never>()
    
    func coverUploadPublisher(objectId: String, spaceId: String) -> AnyPublisher<ObjectHeaderUpdate, Never> {
        if documentWriteOwner != nil {
            return coverUploadSubject.filter {
                $0.objectId.utf8.elementsEqual(objectId.utf8) && $0.spaceId.utf8.elementsEqual(spaceId.utf8)
            }.map { $0.update }.eraseToAnyPublisher()
        }
        return coverUploadSubject.filter { $0.objectId == objectId && $0.spaceId == spaceId }.map { $0.update }.eraseToAnyPublisher()
    }
    
    func handleCoverAction(
        objectId: String,
        spaceId: String,
        action: ObjectCoverPickerAction
    ) async throws {
        switch action {
        case .setCover(let coverSource):
            switch coverSource {
            case let .color(colorName):
                AnytypeAnalytics.instance().logSetCover()
                try? await detailsService.updateBundledDetails(
                    objectId: objectId,
                    bundledDetails: [.coverType(CoverType.color), .coverId(colorName)]
                )
            case let .gradient(gradientName):
                AnytypeAnalytics.instance().logSetCover()
                try? await detailsService.updateBundledDetails(
                    objectId: objectId,
                    bundledDetails: [.coverType(CoverType.gradient), .coverId(gradientName)]
                )
            case let .upload(itemProvider):
                let safeSendableItemProvider = itemProvider.sendable()
                guard let data = try? await fileService.createFileData(source: .itemProvider(safeSendableItemProvider.value)) else {
                    anytypeAssertionFailure("Can't load image from item provider")
                    return
                }
                
                try await publishCoverUpdate(objectId: objectId, spaceId: spaceId, update: .coverUploading(.bundleImagePath(data.path)))
                
                AnytypeAnalytics.instance().logSetCover()
                
                try await detailsService.setCover(
                    objectId: objectId,
                    spaceId: spaceId,
                    source: .itemProvider(safeSendableItemProvider.value),
                    createdInContext: objectId,
                    createdInContextRef: BundledPropertyKey.coverId.rawValue
                )
            case let .unsplash(unsplashItem):
                AnytypeAnalytics.instance().logSetCover()
                
                try await publishCoverUpdate(objectId: objectId, spaceId: spaceId, update: .coverUploading(.remotePreviewURL(unsplashItem.url)))
                
                let imageObjectId = try await unsplashService.downloadImage(
                    spaceId: spaceId,
                    id: unsplashItem.id,
                    createdInContext: objectId,
                    createdInContextRef: BundledPropertyKey.coverId.rawValue
                )
                try await detailsService.setCover(objectId: objectId, imageObjectId: imageObjectId)
            }
        case .removeCover:
            AnytypeAnalytics.instance().logRemoveCover()
            try? await detailsService.updateBundledDetails(
                objectId: objectId,
                bundledDetails: [.coverType(CoverType.none), .coverId("")]
            )
        }
    }
    
    func handleIconAction(objectId: String, spaceId: String, action: ObjectIconPickerAction) async throws {
        switch action {
        case .setIcon(let iconSource):
            switch iconSource {
            case .emoji(let emojiUnicode):
                AnytypeAnalytics.instance().logSetIcon()
                try await detailsService.updateBundledDetails(
                    objectId: objectId,
                    bundledDetails: BundledDetails.iconDetails(iconEmoji: emojiUnicode)
                )
            case .upload(let itemProvider):
                AnytypeAnalytics.instance().logSetIcon()
                let safeSendableItemProvider = itemProvider.sendable()
                let data = try await fileService.createFileData(source: .itemProvider(safeSendableItemProvider.value))
                let fileDetails = try await fileService.uploadFileObject(
                    spaceId: spaceId,
                    data: data,
                    origin: .none,
                    createdInContext: objectId,
                    createdInContextRef: BundledPropertyKey.iconImage.rawValue
                )
                try await detailsService.updateBundledDetails(
                    objectId: objectId,
                    bundledDetails: BundledDetails.iconDetails(objectId: fileDetails.id)
                )
            case let .customIcon(data):
                AnytypeAnalytics.instance().logSetIcon()
                try await detailsService.updateBundledDetails(
                    objectId: objectId,
                    bundledDetails: BundledDetails.iconDetails(iconName: data.icon.stringRepresentation, iconOption: data.color.iconOption)
                )
            }
        case .removeIcon:
            AnytypeAnalytics.instance().logRemoveIcon()
            try await detailsService.updateBundledDetails(
                objectId: objectId,
                bundledDetails: BundledDetails.iconDetails()
            )
        }
    }

    /// The check and actual subject emission share one MainActor turn. A later
    /// scheduler hop is checked separately by the original header view model.
    private func publishCoverUpdate(objectId: String, spaceId: String,
                                    update: ObjectHeaderUpdate) async throws {
        guard let owner = documentWriteOwner else {
            coverUploadSubject.send((objectId, spaceId, update))
            return
        }
        try await MainActor.run {
            try owner.performSynchronousOperation(contextId: objectId, spaceId: spaceId,
                                                   requiresEditing: true,
                                                   requiredPermissions: [.editDetails, .changeCover]) {
                coverUploadSubject.send((objectId, spaceId, update))
            }
        }
    }

}
