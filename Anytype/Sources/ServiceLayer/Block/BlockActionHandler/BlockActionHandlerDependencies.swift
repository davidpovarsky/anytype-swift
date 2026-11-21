import Services

@MainActor
struct BlockActionHandlerDependencies {
    let blockService: any BlockServiceProtocol
    let blockTableService: any BlockTableServiceProtocol
    let fileService: any FileActionsServiceProtocol
    let objectService: any ObjectActionsServiceProtocol
    let pasteboardBlockService: any PasteboardBlockServiceProtocol
    let bookmarkService: any BookmarkServiceProtocol
    let objectTypeProvider: any ObjectTypeProviderProtocol

    // Only a prepared external Host supplies the original document owner.
    // Ordinary app callers keep the original unbound Task behavior.
    var documentWriteOwner: EditorDocumentWriteOwner? = nil

    static func original() -> Self {
        Self(
            blockService: Container.shared.blockService(),
            blockTableService: Container.shared.blockTableService(),
            fileService: Container.shared.fileActionsService(),
            objectService: Container.shared.objectActionsService(),
            pasteboardBlockService: Container.shared.pasteboardBlockService(),
            bookmarkService: Container.shared.bookmarkService(),
            objectTypeProvider: Container.shared.objectTypeProvider()
        )
    }
}
