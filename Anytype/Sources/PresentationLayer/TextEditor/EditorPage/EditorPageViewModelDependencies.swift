import Services

@MainActor
struct EditorPageViewModelDependencies {
    let objectActionsService: any ObjectActionsServiceProtocol
    let objectTypeProvider: any ObjectTypeProviderProtocol
    let searchService: any SearchServiceProtocol
    let templatesSubscriptionService: any TemplatesSubscriptionServiceProtocol
    let accountManager: any AccountManagerProtocol
    let publishingService: any PublishingServiceProtocol
    let participantStorage: any ParticipantsStorageProtocol
    let publishedUrlBuilder: any PublishedUrlBuilderProtocol
    let keyboardInsertedBlocksStorage: any KeyboardInsertedBlocksStorageProtocol
    let blockService: any BlockServiceProtocol

    static func original() -> Self {
        Self(
            objectActionsService: Container.shared.objectActionsService(),
            objectTypeProvider: Container.shared.objectTypeProvider(),
            searchService: Container.shared.searchService(),
            templatesSubscriptionService: Container.shared.templatesSubscription(),
            accountManager: Container.shared.accountManager(),
            publishingService: Container.shared.publishingService(),
            participantStorage: Container.shared.participantsStorage(),
            publishedUrlBuilder: Container.shared.publishedUrlBuilder(),
            keyboardInsertedBlocksStorage: Container.shared.keyboardInsertedBlocksStorage(),
            blockService: Container.shared.blockService()
        )
    }
}
