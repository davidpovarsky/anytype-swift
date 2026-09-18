import Foundation
import Combine
import PinkhaKit
import Services
import AnytypeCore
import SwiftProtobuf
import ProtobufMessages
import Factory
import Logger

/// Repository that manages loading and live synchronization of the Pinkha navigation hierarchy
/// backed by native Anytype Search and Subscription infrastructure.
@MainActor
final class PinkhaHierarchyRepository: ObservableObject {

    private static let log = EventLogger(category: "Pinkha")

    let spaceId: String
    private let manifest: PinkhaSpaceManifest

    @Injected(\.searchMiddleService)
    private var searchMiddleService: any SearchMiddleServiceProtocol

    @Injected(\.subscriptionStorageProvider)
    private var subscriptionStorageProvider: any SubscriptionStorageProviderProtocol

    private var subscriptionStorage: (any SubscriptionStorageProtocol)?
    private var subscriptionCancellable: AnyCancellable?
    private let subscriptionId: String

    @Published private(set) var snapshot: PinkhaHierarchySnapshot = .empty
    @Published private(set) var isLoading: Bool = false
    @Published private(set) var detailsMap: [String: ObjectDetails] = [:]

    init(spaceId: String, manifest: PinkhaSpaceManifest) {
        self.spaceId = spaceId
        self.manifest = manifest
        self.subscriptionId = "PinkhaHierarchy-\(spaceId)"
    }

    // MARK: - Subscriptions & Data Loading

    func start() async {
        guard subscriptionStorage == nil else { return }
        isLoading = true

        let storage = subscriptionStorageProvider.createSubscriptionStorage(subId: subscriptionId)
        self.subscriptionStorage = storage

        // Initial search load
        await reload()

        // Live subscription setup
        let typesToInclude: [String] = [manifest.folderTypeId] + Array(manifest.registeredDocumentTypes.values)
        let filters: [DataviewFilter] = .builder {
            SearchHelper.spaceIdFilter(spaceId)
            SearchHelper.isDeletedFilter(isDeleted: false)
            SearchHelper.isArchivedFilter(isArchived: false)
            SearchHelper.typeFilter(typesToInclude)
        }

        let searchData = SubscriptionData.Search(
            identifier: subscriptionId,
            spaceId: spaceId,
            sorts: [],
            filters: filters,
            limit: 0,
            keys: []
        )

        subscriptionCancellable = storage.statePublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] state in
                guard let self else { return }
                self.processDetails(state.items)
            }

        do {
            try await storage.startOrUpdateSubscription(data: .search(searchData))
        } catch {
            Self.log.error("Failed to start hierarchy subscription for space \(spaceId): \(error)")
            isLoading = false
        }
    }

    func stop() async {
        subscriptionCancellable?.cancel()
        subscriptionCancellable = nil
        do {
            try await subscriptionStorage?.stopSubscription()
        } catch {
            Self.log.error("Failed to stop hierarchy subscription for space \(spaceId): \(error)")
        }
        subscriptionStorage = nil
    }

    func reload() async {
        let typesToInclude: [String] = [manifest.folderTypeId] + Array(manifest.registeredDocumentTypes.values)
        let filters: [DataviewFilter] = .builder {
            SearchHelper.spaceIdFilter(spaceId)
            SearchHelper.isDeletedFilter(isDeleted: false)
            SearchHelper.isArchivedFilter(isArchived: false)
            SearchHelper.typeFilter(typesToInclude)
        }

        do {
            let details = try await searchMiddleService.search(
                spaceId: spaceId,
                filters: filters,
                sorts: [],
                fullText: "",
                keys: [],
                limit: 0
            )
            processDetails(details)
            isLoading = false
        } catch {
            Self.log.error("Failed to reload hierarchy for space \(spaceId): \(error)")
            isLoading = false
        }
    }

    // MARK: - Data Transformation

    private func processDetails(_ detailsList: [ObjectDetails]) {
        var rawItems: [PinkhaHierarchyRawItem] = []
        var newDetailsMap: [String: ObjectDetails] = [:]

        for details in detailsList {
            // Exclude manifest object itself
            if details.id == manifest.manifestObjectId {
                continue
            }
            // Exclude book folder objects from normal tree
            if !manifest.bookFolderTypeId.isEmpty && details.type == manifest.bookFolderTypeId {
                continue
            }

            let kind: PinkhaHierarchyNodeKind
            if details.type == manifest.folderTypeId {
                kind = .folder
            } else if manifest.isRegisteredDocumentType(typeId: details.type) {
                kind = .writingDocument
            } else {
                continue
            }

            let parentId = extractParentId(from: details, key: manifest.parentPropertyKey)
            let order = extractOrder(from: details, key: manifest.orderPropertyKey)
            let title = details.objectName.isEmpty ? details.name : details.objectName

            let raw = PinkhaHierarchyRawItem(
                objectId: details.id,
                typeId: details.type,
                title: title,
                parentId: parentId,
                order: order,
                kind: kind
            )
            rawItems.append(raw)
            newDetailsMap[details.id] = details
        }

        self.detailsMap = newDetailsMap
        self.snapshot = PinkhaHierarchyBuilder.build(items: rawItems)
    }

    private func extractParentId(from details: ObjectDetails, key: String) -> String? {
        guard !key.isEmpty, let value = details.values[key] else { return nil }
        if !value.stringValue.isEmpty {
            return value.stringValue
        }
        if case let .listValue(list) = value.kind, let first = list.values.first?.stringValue, !first.isEmpty {
            return first
        }
        return nil
    }

    private func extractOrder(from details: ObjectDetails, key: String) -> Double? {
        guard !key.isEmpty, let value = details.values[key] else { return nil }
        if case let .numberValue(num) = value.kind {
            return num
        }
        return details.doubleValue(for: key)
    }
}
