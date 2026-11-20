import Services

@MainActor
struct SimpleTableServiceDependencies {
    let tableService: any BlockTableServiceProtocol
    let pasteboardService: any PasteboardBlockDocumentServiceProtocol
    let defaultObjectService: any DefaultObjectCreationServiceProtocol
    let typesService: any TypesServiceProtocol

    static func original() -> Self {
        Self(
            tableService: Container.shared.blockTableService(),
            pasteboardService: Container.shared.pasteboardBlockDocumentService(),
            defaultObjectService: Container.shared.defaultObjectCreationService(),
            typesService: Container.shared.typesService()
        )
    }
}
