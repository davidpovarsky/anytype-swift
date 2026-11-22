import Foundation
import Services
import AnytypeCore

enum ObjectCoverPickerAction {
    enum CoverSource {
        case color(colorName: String)
        case gradient(gradientName: String)
        case upload(itemProvider: NSItemProvider)
        case unsplash(unsplashItem: UnsplashItem)
    }

    case setCover(CoverSource)
    case removeCover
}

struct BaseDocumentIdentifiable: Identifiable {
    let document: any BaseDocumentProtocol

    var id: String { document.objectId }
}

extension BaseDocumentProtocol {
    var identifiable: BaseDocumentIdentifiable {
        BaseDocumentIdentifiable(document: self)
    }
}

@MainActor
@Observable
final class ObjectCoverPickerViewModel {

    let mediaPickerContentType: MediaPickerContentType = .images
    var isRemoveButtonAvailable: Bool {
        (try? withCurrentDocument { document.details?.documentCover != nil }) ?? false
    }

    // MARK: - Private variables
    @ObservationIgnored
    private let objectHeaderUploadingService: any ObjectHeaderUploadingServiceProtocol
    @ObservationIgnored
    let documentWriteOwner: EditorDocumentWriteOwner?

    @ObservationIgnored
    private let document: any BaseDocumentProtocol
        
    // MARK: - Initializer
    
    init(data: BaseDocumentIdentifiable, dependencies: ObjectHeaderViewModelDependencies = .original()) {
        self.document = data.document
        self.objectHeaderUploadingService = dependencies.objectHeaderUploadingService
        self.documentWriteOwner = dependencies.documentWriteOwner
    }

    func performCurrentPresentation(_ operation: () -> Void) {
        try? withCurrentDocument(operation)
    }

    private func withCurrentDocument<Value>(_ operation: () throws -> Value) throws -> Value {
        guard let documentWriteOwner else { return try operation() }
        return try documentWriteOwner.performSynchronousOperation(
            contextId: document.objectId, spaceId: document.spaceId, requiresEditing: false
        ) {
            try documentWriteOwner.validateDocument(document)
            return try operation()
        }
    }
}

extension ObjectCoverPickerViewModel {
    
    func setColor(_ colorName: String) {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: document.objectId,
                                       requiredPermissions: [.editDetails, .changeCover]) { [self] in
            try withCurrentDocument { }
            try await objectHeaderUploadingService.handleCoverAction(
                objectId: document.objectId,
                spaceId: document.spaceId,
                action: .setCover(.color(colorName: colorName))
            )
        }
    }
    
    func setGradient(_ gradientName: String) {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: document.objectId,
                                       requiredPermissions: [.editDetails, .changeCover]) { [self] in
            try withCurrentDocument { }
            try await objectHeaderUploadingService.handleCoverAction(
                objectId: document.objectId,
                spaceId: document.spaceId,
                action: .setCover(.gradient(gradientName: gradientName))
            )
        }
    }
    
    func uploadImage(from itemProvider: NSItemProvider) {
        let safeItemProvoder = itemProvider.sendable()
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: document.objectId,
                                       requiredPermissions: [.editDetails, .changeCover]) { [self] in
            try withCurrentDocument { }
            try await objectHeaderUploadingService.handleCoverAction(
                objectId: document.objectId,
                spaceId: document.spaceId,
                action: .setCover(.upload(itemProvider: safeItemProvoder.value))
            )
        }
    }

    func uploadUnplashCover(unsplashItem: UnsplashItem) {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: document.objectId,
                                       requiredPermissions: [.editDetails, .changeCover]) { [self] in
            try withCurrentDocument { }
            try await objectHeaderUploadingService.handleCoverAction(
                objectId: document.objectId,
                spaceId: document.spaceId,
                action: .setCover(.unsplash(unsplashItem: unsplashItem))
            )
        }
    }
    
    func removeCover() {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: document.objectId,
                                       requiredPermissions: [.editDetails, .changeCover]) { [self] in
            try withCurrentDocument { }
            try await objectHeaderUploadingService.handleCoverAction(
                objectId: document.objectId,
                spaceId: document.spaceId,
                action: .removeCover
            )
        }
    }
}
