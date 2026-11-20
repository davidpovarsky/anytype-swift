import Services

@MainActor
struct KeyboardActionHandlerDependencies {
    let blockService: any BlockServiceProtocol
    let keyboardInsertedBlocksStorage: any KeyboardInsertedBlocksStorageProtocol

    static func original() -> Self {
        Self(
            blockService: Container.shared.blockService(),
            keyboardInsertedBlocksStorage: Container.shared.keyboardInsertedBlocksStorage()
        )
    }
}
