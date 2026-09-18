import Foundation

/// Pure domain reconciler that maintains the visible hierarchy snapshot by combining
/// authoritative live subscription items with locally pending created or mutated items.
///
/// Guarantees:
/// 1. Newly created objects appear in the visible snapshot immediately (0ms UI latency).
/// 2. Stale subscription frames arriving before backend indexing cannot erase pending objects.
/// 3. Once an object is confirmed in the authoritative subscription, it is cleared from pending.
/// 4. Deduplication is strictly enforced by objectId.
public final class PinkhaHierarchyReconciler: @unchecked Sendable {

    /// Locally created items that have not yet been observed in an authoritative subscription update.
    public private(set) var pendingCreatedItems: [String: PinkhaHierarchyRawItem] = [:]

    /// Locally applied mutations (rename, order, move, deletion) awaiting subscription confirmation.
    public private(set) var optimisticMutations: [String: PinkhaOptimisticMutation] = [:]

    /// The latest items confirmed by the authoritative subscription.
    public private(set) var lastSubscriptionItems: [PinkhaHierarchyRawItem] = []

    /// Set of object IDs that were confirmed in a subscription update at least once.
    public private(set) var confirmedSubscriptionIds: Set<String> = []

    /// Current visible snapshot.
    public private(set) var currentSnapshot: PinkhaHierarchySnapshot = .empty

    public init() {}

    // MARK: - Optimistic Mutation Enum

    public enum PinkhaOptimisticMutation: Sendable, Equatable {
        case rename(title: String)
        case order(newRank: Double)
        case move(newParentId: String?, newRank: Double?)
        case delete
    }

    // MARK: - Registration & Live Subscription Updates

    /// Registers a newly created item. Immediately adds it to pending items and rebuilds the visible snapshot.
    @discardableResult
    public func registerPending(item: PinkhaHierarchyRawItem) -> PinkhaHierarchySnapshot {
        pendingCreatedItems[item.objectId] = item
        // Clear any prior optimistic deletion if object is re-created
        optimisticMutations.removeValue(forKey: item.objectId)
        return rebuildSnapshot()
    }

    /// Receives authoritative items from the live subscription stream and reconciles with pending items.
    @discardableResult
    public func receiveSubscription(items: [PinkhaHierarchyRawItem]) -> PinkhaHierarchySnapshot {
        lastSubscriptionItems = items

        // For any item observed in the authoritative subscription:
        // Clear it from pendingCreatedItems and remove matching optimistic mutations
        for item in items {
            pendingCreatedItems.removeValue(forKey: item.objectId)
            confirmedSubscriptionIds.insert(item.objectId)
            optimisticMutations.removeValue(forKey: item.objectId)
        }

        return rebuildSnapshot()
    }

    // MARK: - Local Optimistic Mutations

    /// Applies an optimistic rename to an existing item until subscription confirmation.
    @discardableResult
    public func applyOptimisticRename(objectId: String, newTitle: String) -> PinkhaHierarchySnapshot {
        optimisticMutations[objectId] = .rename(title: newTitle)
        if var pending = pendingCreatedItems[objectId] {
            pending = PinkhaHierarchyRawItem(
                objectId: pending.objectId,
                typeId: pending.typeId,
                title: newTitle,
                parentId: pending.parentId,
                order: pending.order,
                kind: pending.kind
            )
            pendingCreatedItems[objectId] = pending
        }
        return rebuildSnapshot()
    }

    /// Applies an optimistic order change until subscription confirmation.
    @discardableResult
    public func applyOptimisticOrder(objectId: String, newRank: Double) -> PinkhaHierarchySnapshot {
        optimisticMutations[objectId] = .order(newRank: newRank)
        if var pending = pendingCreatedItems[objectId] {
            pending = PinkhaHierarchyRawItem(
                objectId: pending.objectId,
                typeId: pending.typeId,
                title: pending.title,
                parentId: pending.parentId,
                order: newRank,
                kind: pending.kind
            )
            pendingCreatedItems[objectId] = pending
        }
        return rebuildSnapshot()
    }

    /// Applies an optimistic move (reparent + optional rank change) until subscription confirmation.
    @discardableResult
    public func applyOptimisticMove(objectId: String, newParentId: String?, newRank: Double? = nil) -> PinkhaHierarchySnapshot {
        optimisticMutations[objectId] = .move(newParentId: newParentId, newRank: newRank)
        if var pending = pendingCreatedItems[objectId] {
            pending = PinkhaHierarchyRawItem(
                objectId: pending.objectId,
                typeId: pending.typeId,
                title: pending.title,
                parentId: newParentId,
                order: newRank ?? pending.order,
                kind: pending.kind
            )
            pendingCreatedItems[objectId] = pending
        }
        return rebuildSnapshot()
    }

    /// Applies an optimistic deletion until subscription confirmation.
    @discardableResult
    public func applyOptimisticDelete(objectId: String) -> PinkhaHierarchySnapshot {
        pendingCreatedItems.removeValue(forKey: objectId)
        optimisticMutations[objectId] = .delete
        return rebuildSnapshot()
    }

    // MARK: - Snapshot Construction

    @discardableResult
    public func rebuildSnapshot() -> PinkhaHierarchySnapshot {
        var mergedItems: [String: PinkhaHierarchyRawItem] = [:]

        // 1. Authoritative subscription items
        for item in lastSubscriptionItems {
            mergedItems[item.objectId] = item
        }

        // 2. Overlay pending created items that are not yet present in the subscription
        for (id, pendingItem) in pendingCreatedItems {
            if mergedItems[id] == nil {
                mergedItems[id] = pendingItem
            }
        }

        // 3. Overlay optimistic mutations
        for (id, mutation) in optimisticMutations {
            guard var item = mergedItems[id] else { continue }
            switch mutation {
            case .rename(let newTitle):
                item = PinkhaHierarchyRawItem(
                    objectId: item.objectId,
                    typeId: item.typeId,
                    title: newTitle,
                    parentId: item.parentId,
                    order: item.order,
                    kind: item.kind
                )
                mergedItems[id] = item
            case .order(let newRank):
                item = PinkhaHierarchyRawItem(
                    objectId: item.objectId,
                    typeId: item.typeId,
                    title: item.title,
                    parentId: item.parentId,
                    order: newRank,
                    kind: item.kind
                )
                mergedItems[id] = item
            case .move(let newParentId, let newRank):
                item = PinkhaHierarchyRawItem(
                    objectId: item.objectId,
                    typeId: item.typeId,
                    title: item.title,
                    parentId: newParentId,
                    order: newRank ?? item.order,
                    kind: item.kind
                )
                mergedItems[id] = item
            case .delete:
                mergedItems.removeValue(forKey: id)
            }
        }

        let snapshot = PinkhaHierarchyBuilder.build(items: Array(mergedItems.values))
        self.currentSnapshot = snapshot
        return snapshot
    }
}
