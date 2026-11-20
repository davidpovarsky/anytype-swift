import Services

@MainActor
struct BlockViewModelBuilderDependencies {
    let tableService: any BlockTableServiceProtocol
    let detailsService: any DetailsServiceProtocol
    let audioSessionService: any AudioSessionServiceProtocol
    let objectTypeProvider: any ObjectTypeProviderProtocol
    let pasteboardService: any PasteboardBlockDocumentServiceProtocol
    let blockService: any BlockServiceProtocol

    static func original() -> Self {
        Self(
            tableService: Container.shared.blockTableService(),
            detailsService: Container.shared.detailsService(),
            audioSessionService: Container.shared.audioSessionService(),
            objectTypeProvider: Container.shared.objectTypeProvider(),
            pasteboardService: Container.shared.pasteboardBlockDocumentService(),
            blockService: Container.shared.blockService()
        )
    }
}
