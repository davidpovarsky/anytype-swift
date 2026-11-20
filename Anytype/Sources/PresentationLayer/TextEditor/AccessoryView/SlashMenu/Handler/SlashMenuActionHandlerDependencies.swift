import Services

@MainActor
struct SlashMenuActionHandlerDependencies {
    let pasteboardService: any PasteboardBlockDocumentServiceProtocol
    let objectDateByTimestampService: any ObjectDateByTimestampServiceProtocol

    static func original() -> Self {
        Self(
            pasteboardService: Container.shared.pasteboardBlockDocumentService(),
            objectDateByTimestampService: Container.shared.objectDateByTimestampService()
        )
    }
}
