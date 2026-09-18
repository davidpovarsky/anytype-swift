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
/// backed by native Anytype Subscription infrastructure as the single authoritative stream.
///
/// Uses PinkhaHierarchyReconciler to guarantee instantaneous presentation of locally-created
/// folders/documents and prevent stale subscription frames from erasing pending objects.
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

    private let reconciler = PinkhaHierarchyReconciler()

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

        // Attach live subscription listener BEFORE starting subscription
        subscriptionCancellable = storage.statePublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] state in
                guard let self else { return }
                self.processSubscriptionDetails(state.items)
                self.isLoading = false
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

    /// Explicit fallback/recovery reload. Not called routinely during normal operation.
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
            processSubscriptionDetails(details)
            isLoading = false
        } catch {
            Self.log.error("Failed to reload hierarchy for space \(spaceId): \(error)")
            isLoading = false
        }
    }

    // MARK: - Immediate Presentation & Reconciliation

    /// Registers a newly created folder or document immediately into local presentation state,
    /// rebuilding the snapshot instantly without waiting for backend search indexing.
    func registerPendingCreated(details: ObjectDetails) {
        detailsMap[details.id] = details

        guard let rawItem = makeRawItem(from: details) else {
            Self.log.error("Failed to convert created object to hierarchy raw item: id=\(details.id), type=\(details.type)")
            return
        }

        Self.log.info("Registering pending created object: id=\(rawItem.objectId), kind=\(rawItem.kind), title=\(rawItem.title)")
        self.snapshot = reconciler.registerPending(item: rawItem)
    }

    /// Applies an optimistic rename to local presentation state.
    func applyOptimisticRename(objectId: String, newName: String) {
        if let existing = detailsMap[objectId] {
            detailsMap[objectId] = existing.updated(by: [BundledPropertyKey.name.rawValue: newName.protobufValue])
        }
        self.snapshot = reconciler.applyOptimisticRename(objectId: objectId, newTitle: newName)
    }

    /// Applies an optimistic order change to local presentation state.
    func applyOptimisticOrder(objectId: String, newOrder: Double) {
        if let existing = detailsMap[objectId] {
            detailsMap[objectId] = existing.updated(by: [manifest.orderPropertyKey: newOrder.protobufValue])
        }
        self.snapshot = reconciler.applyOptimisticOrder(objectId: objectId, newRank: newOrder)
    }

    /// Applies an optimistic move (reparent + optional rank) to local presentation state.
    func applyOptimisticMove(objectId: String, newParentId: String?, newOrder: Double? = nil) {
        if let existing = detailsMap[objectId] {
            var updates: [String: Google_Protobuf_Value] = [:]
            if let newParentId, !newParentId.isEmpty {
                updates[manifest.parentPropertyKey] = newParentId.protobufValue
            } else {
                updates[manifest.parentPropertyKey] = "".protobufValue
            }
            if let newOrder {
                updates[manifest.orderPropertyKey] = newOrder.protobufValue
            }
            detailsMap[objectId] = existing.updated(by: updates)
        }
        self.snapshot = reconciler.applyOptimisticMove(objectId: objectId, newParentId: newParentId, newRank: newOrder)
    }

    /// Applies an optimistic deletion to local presentation state.
    func applyOptimisticDelete(objectId: String) {
        detailsMap.removeValue(forKey: objectId)
        self.snapshot = reconciler.applyOptimisticDelete(objectId: objectId)
    }

    // MARK: - Data Transformation & Subscription Processing

    private func processSubscriptionDetails(_ detailsList: [ObjectDetails]) {
        Self.log.info("Subscription update: received \(detailsList.count) items for space \(spaceId)")

        var rawItems: [PinkhaHierarchyRawItem] = []
        var newDetailsMap: [String: ObjectDetails] = [:]

        // Check and log presence of currently pending items
        let pendingIds = Set(reconciler.pendingCreatedItems.keys)
        if !pendingIds.isEmpty {
            Self.log.info("Active pending objects before reconciliation: \(pendingIds)")
        }

        for details in detailsList {
            // Exclude manifest object itself
            if details.id == manifest.manifestObjectId {
                Self.log.debug("Excluded manifest object: \(details.id)")
                continue
            }
            // Exclude book folder objects from normal tree
            if !manifest.bookFolderTypeId.isEmpty && details.type == manifest.bookFolderTypeId {
                Self.log.debug("Excluded book folder object: \(details.id)")
                continue
            }

            guard let raw = makeRawItem(from: details) else {
                Self.log.debug("Excluded item id=\(details.id), type=\(details.type): unrecognized type (expected folder=\(manifest.folderTypeId))")
                continue
            }

            if pendingIds.contains(details.id) {
                Self.log.info("Pending object confirmed in subscription: id=\(details.id), type=\(details.type), kind=\(raw.kind)")
            }

            rawItems.append(raw)
            newDetailsMap[details.id] = details
        }

        // Retain detailsMap entries for any pending created items not yet in subscription
        for (pendingId, pendingItem) in reconciler.pendingCreatedItems {
            if newDetailsMap[pendingId] == nil, let cached = detailsMap[pendingId] {
                newDetailsMap[pendingId] = cached
                Self.log.info("Retaining pending object not yet in subscription: id=\(pendingId), kind=\(pendingItem.kind)")
            }
        }

        self.detailsMap = newDetailsMap
        self.snapshot = reconciler.receiveSubscription(items: rawItems)
    }

    private func makeRawItem(from details: ObjectDetails) -> PinkhaHierarchyRawItem? {
        let kind: PinkhaHierarchyNodeKind
        if details.type == manifest.folderTypeId {
            kind = .folder
        } else if manifest.isRegisteredDocumentType(typeId: details.type) {
            kind = .writingDocument
        } else {
            return nil
        }

        let parentId = extractParentId(from: details, key: manifest.parentPropertyKey)
        let order = extractOrder(from: details, key: manifest.orderPropertyKey)
        let title = details.objectName.isEmpty ? details.name : details.objectName

        return PinkhaHierarchyRawItem(
            objectId: details.id,
            typeId: details.type,
            title: title,
            parentId: parentId,
            order: order,
            kind: kind
        )
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
