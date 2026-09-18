import Foundation
import Combine
import PinkhaKit
import Services
import AnytypeCore
import SwiftProtobuf
import ProtobufMessages
import Factory

/// Repository that manages loading and live synchronization of the Pinkha navigation hierarchy
/// backed by native Anytype Search and Subscription infrastructure.
@MainActor
public final class PinkhaHierarchyRepository: ObservableObject {

    public let spaceId: String
    private let manifest: PinkhaSpaceManifest

    @Injected(\.searchMiddleService)
    private var searchMiddleService: any SearchMiddleServiceProtocol

    @Injected(\.subscriptionStorageProvider)
    private var subscriptionStorageProvider: any SubscriptionStorageProviderProtocol

    private var subscriptionStorage: (any SubscriptionStorageProtocol)?
    private var subscriptionCancellable: AnyCancellable?
    private let subscriptionId: String

    @Published public private(set) var snapshot: PinkhaHierarchySnapshot = .empty
    @Published public private(set) var isLoading: Bool = false
    @Published public private(set) var detailsMap: [String: ObjectDetails] = [:]

    public init(spaceId: String, manifest: PinkhaSpaceManifest) {
        self.spaceId = spaceId
        self.manifest = manifest
        self.subscriptionId = "PinkhaHierarchy-\(spaceId)"
    }

    // MARK: - Subscriptions & Data Loading

    public func start() async {
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
            limit: 1000,
            keys: []
        )

        subscriptionCancellable = storage.statePublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] state in
                guard let self else { return }
                self.processDetails(state.items)
            }

        try? await storage.startOrUpdateSubscription(data: .search(searchData))
    }

    public func stop() async {
        subscriptionCancellable?.cancel()
        subscriptionCancellable = nil
        try? await subscriptionStorage?.stopSubscription()
        subscriptionStorage = nil
    }

    public func reload() async {
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
                limit: 1000
            )
            processDetails(details)
            isLoading = false
        } catch {
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
        if value.hasNumberValue {
            return value.numberValue
        }
        return details.doubleValue(for: key)
    }
}
