import Services

@MainActor
struct ObjectHeaderViewModelDependencies {
    let objectHeaderUploadingService: any ObjectHeaderUploadingServiceProtocol
    let documentWriteOwner: EditorDocumentWriteOwner?

    init(objectHeaderUploadingService: any ObjectHeaderUploadingServiceProtocol,
         documentWriteOwner: EditorDocumentWriteOwner? = nil) {
        self.objectHeaderUploadingService = objectHeaderUploadingService
        self.documentWriteOwner = documentWriteOwner
    }

    static func original() -> Self {
        Self(
            objectHeaderUploadingService: Container.shared.objectHeaderUploadingService()
        )
    }
}
