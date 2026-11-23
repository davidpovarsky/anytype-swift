import Foundation
import Combine
import Services
import ProtobufMessages
import AnytypeCore

actor EventsListener: EventsListenerProtocol {
    
    // MARK: - Internal variables
    
    var onUpdatesReceive: (([DocumentUpdate]) -> Void)?
        
    // MARK: - Private variables
    
    private let objectId: String
    private let spaceId: String
     
    private let infoContainer: any InfoContainerProtocol
    
    private let middlewareConverter: MiddlewareEventConverter
    private let localConverter: LocalEventConverter
    private let mentionMarkupEventProvider: MentionMarkupEventProvider
    
    private var subscriptions = [AnyCancellable]()
    
    // MARK: - Initializers
    
    init(
        objectId: String,
        spaceId: String,
        infoContainer: some InfoContainerProtocol,
        restrictionsContainer: ObjectRestrictionsContainer,
        detailsStorage: ObjectDetailsStorage
    ) {
        self.objectId = objectId
        self.spaceId = spaceId
        self.infoContainer = infoContainer
        
        let informationCreator = BlockInformationCreator(
            validator: BlockValidator(),
            infoContainer: infoContainer
        )
        self.middlewareConverter = MiddlewareEventConverter(
            infoContainer: infoContainer,
            informationCreator: informationCreator,
            detailsStorage: detailsStorage,
            restrictionsContainer: restrictionsContainer
        )
        self.localConverter = LocalEventConverter(
            infoContainer: infoContainer
        )
        self.mentionMarkupEventProvider = MentionMarkupEventProvider(
            objectId: objectId,
            infoContainer: infoContainer,
            detailsStorage: detailsStorage
        )
    }
    
    // MARK: - EventsListenerProtocol
    
    nonisolated
    func startListening() {
        Task {
            await startListeningInternal()
        }
    }
    
    nonisolated
    func stopListening() {
        Task {
            await stopListeningInternal()
        }
    }
    
    nonisolated
    func setOnUpdateReceice(_ closure: @escaping @Sendable ([DocumentUpdate]) -> Void) {
        Task {
            await setOnUpdateReceiceInternal(closure)
        }
    }
    
    // MARK: - Private
    
    private func startListeningInternal() {
        subscribeMiddlewareEvents()
    }
    
    private func stopListeningInternal() {
        subscriptions = []
    }
    
    
    private func setOnUpdateReceiceInternal(_ closure: @escaping ([DocumentUpdate]) -> Void) {
        onUpdatesReceive = closure
    }
    
    private func subscribeMiddlewareEvents() {
        EventBunchSubscribtion.default.addHandler { [weak self] events in
            guard events.contextId == self?.objectId else { return }
            await self?.handle(events: events)
        }.store(in: &subscriptions)
    }
    
    private func handle(events: EventsBunch) {
#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
        if let fence = events.pinkhaSemanticPublication {
            guard let updates = fence.withCurrentDocumentState(spaceID: spaceId, objectID: objectId, {
                makeUpdates(events: events)
            }) else { return }
            // Subscriber callbacks may enqueue work. They run outside the state
            // lock and explicitly carry this owner into their later delivery.
            PinkhaHeartSemanticAnchorPublication.$current.withValue(fence) {
                receiveUpdates(updates)
            }
            return
        }
#endif
        receiveUpdates(makeUpdates(events: events))
    }

    private func makeUpdates(events: EventsBunch) -> [DocumentUpdate] {
        let middlewareUpdates = events.middlewareEvents.compactMap(\.value).compactMap { middlewareConverter.convert($0) }
        let localUpdates = events.localEvents.flatMap { localConverter.convert($0) }

        // Both walks below are O(document size). Mention texts depend on block
        // content and on details of mentioned objects; indentation metadata and
        // numbered-list values depend on block changes only. Classify in a single
        // early-exit pass instead of two scans over a merged array.
        var hasBlockUpdates = false
        var hasDetailsUpdates = false
        for update in [middlewareUpdates, localUpdates].joined() {
            hasBlockUpdates = hasBlockUpdates || update.affectsBlocks
            hasDetailsUpdates = hasDetailsUpdates || update.affectsDetails
            if hasBlockUpdates && hasDetailsUpdates { break }
        }

        let markupUpdates = hasBlockUpdates || hasDetailsUpdates
            ? mentionMarkupEventProvider.updateMentionsEvent()
            : []

        let builderUpdates: [DocumentUpdate] = hasBlockUpdates
            ? IndentationBuilder.build(container: infoContainer, id: objectId).map { .block(blockId: $0) }
            : []

        return middlewareUpdates + markupUpdates + localUpdates + builderUpdates
    }
    
    private func receiveUpdates(_ updates: [DocumentUpdate]) {
        guard updates.isNotEmpty else { return }
        onUpdatesReceive?(updates)
    }
}
