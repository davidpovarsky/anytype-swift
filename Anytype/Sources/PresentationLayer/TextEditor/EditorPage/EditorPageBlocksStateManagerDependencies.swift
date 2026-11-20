import Services

@MainActor
struct EditorPageBlocksStateManagerDependencies {
    let blockService: any BlockServiceProtocol
    let pasteboardService: any PasteboardBlockDocumentServiceProtocol
    let documentsProvider: any DocumentsProviderProtocol
    let objectActionsService: any ObjectActionsServiceProtocol
    let toastPresenter: any ToastPresenterProtocol

    static func original() -> Self {
        Self(
            blockService: Container.shared.blockService(),
            pasteboardService: Container.shared.pasteboardBlockDocumentService(),
            documentsProvider: Container.shared.documentsProvider(),
            objectActionsService: Container.shared.objectActionsService(),
            toastPresenter: Container.shared.legacyToastPresenter()
        )
    }
}
