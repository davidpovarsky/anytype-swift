import Foundation
import Services
@preconcurrency import Combine

protocol ParticipantsSubscriptionProtocol: AnyObject {
    var participantsPublisher: AnyPublisher<[Participant], Never> { get }
}

extension ParticipantsSubscriptionProtocol {
    var activeParticipantsPublisher: AnyPublisher<[Participant], Never> {
        participantsPublisher.map { $0.filter { $0.status == .active } }.eraseToAnyPublisher()
    }
    
    var withoutRemovingParticipantsPublisher: AnyPublisher<[Participant], Never> {
        participantsPublisher.map { $0.filter { $0.status != .removing } }.eraseToAnyPublisher()
    }
}

actor ParticipantsSubscription: ParticipantsSubscriptionProtocol {
    
    // MARK: - DI
    
    private let subscriptionStorageProvider: any SubscriptionStorageProviderProtocol = Container.shared.subscriptionStorageProvider()
    private let subscriptionStorage: any SubscriptionStorageProtocol
    private let subId: String
    
    nonisolated let participantsPublisher: AnyPublisher<[Participant], Never>
    
    init(spaceId: String) {
        let subId = "ParticipantsSubscription-\(UUID())-\(spaceId)"
        self.subId = subId
        self.subscriptionStorage = subscriptionStorageProvider.createSubscriptionStorage(subId: subId)
        self.participantsPublisher = subscriptionStorage.statePublisher
            .map { $0.items.compactMap { try? Participant(details: $0) } }
            .eraseToAnyPublisher()
        Task {
            try await startSubscription(spaceId: spaceId)
        }
    }

    /// The prepared route uses this same original actor and subscription body,
    /// but awaits startup instead of spawning a task before admission exists.
    private init(subId: String, originalStorage: SubscriptionStorage) {
        self.subId = subId
        self.subscriptionStorage = originalStorage
        self.participantsPublisher = originalStorage.statePublisher
            .map { $0.items.compactMap { try? Participant(details: $0) } }
            .eraseToAnyPublisher()
    }

    @MainActor
    static func prepareOriginal(
        spaceId: String, owner: EditorDocumentWriteOwner
    ) async throws -> ParticipantsSubscription {
        let subscription = try owner.performSynchronousOperation(
            spaceId: spaceId, requiresEditing: false
        ) {
            guard let accountDispatch = try owner.childSourceBinding().committedEventBinding,
                  let provider = Container.shared.subscriptionStorageProvider() as? SubscriptionStorageProvider else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
            let subId = "ParticipantsSubscription-\(UUID())-\(spaceId)"
            let storage = try provider.createOriginalAccountBoundStorage(
                subId: subId, accountDispatch: accountDispatch
            )
            return ParticipantsSubscription(subId: subId, originalStorage: storage)
        }
        try await owner.performRead(
            spaceId: spaceId, rpcNames: ["ObjectSearchSubscribe"],
            onDrained: { [subscription] in withExtendedLifetime(subscription) {} }
        ) {
            try await subscription.startSubscription(spaceId: spaceId)
        }
        return subscription
    }
    
    
    // MARK: - Private
    
    private func startSubscription(spaceId: String) async throws {
        
        let sort = SearchHelper.sort(
            relation: BundledPropertyKey.name,
            type: .asc
        )
        
        let filters: [DataviewFilter] = .builder {
            SearchHelper.notHiddenFilters(hideHiddenDescoveryFiles: false)
            SearchHelper.layoutFilter([.participant])
            SearchHelper.participantStatusFilter(.active, .joining, .removing)
        }
        
        let searchData: SubscriptionData = .search(
            SubscriptionData.Search(
                identifier: subId,
                spaceId: spaceId,
                sorts: [sort],
                filters: filters,
                limit: 0,
                offset: 0,
                keys: Participant.subscriptionKeys.map { $0.rawValue }
            )
        )
        
        try await subscriptionStorage.startOrUpdateSubscription(data: searchData)
    }
}
