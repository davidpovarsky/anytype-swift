import Services

@MainActor
struct BlockActionServiceDependencies {
    let objectActionService: any ObjectActionsServiceProtocol
    let textServiceHandler: any TextServiceProtocol
    let blockService: any BlockServiceProtocol
    let bookmarkService: any BookmarkServiceProtocol
    let fileService: any FileActionsServiceProtocol
    let objectTypeProvider: any ObjectTypeProviderProtocol
    let keyboardInsertedBlocksStorage: any KeyboardInsertedBlocksStorageProtocol

    // Only a prepared external Host supplies the original document owner.
    // Ordinary app callers keep the original unbound Task behavior.
    var documentWriteOwner: EditorDocumentWriteOwner? = nil

    static func original() -> Self {
        Self(
            objectActionService: Container.shared.objectActionsService(),
            textServiceHandler: Container.shared.textServiceHandler(),
            blockService: Container.shared.blockService(),
            bookmarkService: Container.shared.bookmarkService(),
            fileService: Container.shared.fileActionsService(),
            objectTypeProvider: Container.shared.objectTypeProvider(),
            keyboardInsertedBlocksStorage: Container.shared.keyboardInsertedBlocksStorage()
        )
    }
}
