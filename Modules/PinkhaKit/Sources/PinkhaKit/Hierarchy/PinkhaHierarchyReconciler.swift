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

        var incomingMap: [String: PinkhaHierarchyRawItem] = [:]
        for item in items {
            incomingMap[item.objectId] = item
            confirmedSubscriptionIds.insert(item.objectId)
        }

        // 1. Semantic confirmation of optimistic mutations by value
        for (id, mutation) in optimisticMutations {
            guard let subItem = incomingMap[id] else {
                // Item is ABSENT from the authoritative subscription:
                // If the mutation was delete, deletion is confirmed!
                if case .delete = mutation {
                    optimisticMutations.removeValue(forKey: id)
                }
                // For rename, order, move: item not present in subscription yet, keep mutation pending
                continue
            }

            // Item IS present in the incoming subscription:
            switch mutation {
            case .rename(let expectedTitle):
                let subTitle = subItem.title.trimmingCharacters(in: .whitespacesAndNewlines)
                let expTitle = expectedTitle.trimmingCharacters(in: .whitespacesAndNewlines)
                if subTitle == expTitle {
                    optimisticMutations.removeValue(forKey: id)
                }
                // Else stale subscription frame still has old title -> keep mutation pending

            case .order(let expectedRank):
                if let subOrder = subItem.order, abs(subOrder - expectedRank) < 0.0001 {
                    optimisticMutations.removeValue(forKey: id)
                }
                // Else stale subscription frame still has old order -> keep mutation pending

            case .move(let expectedParentId, let expectedRank):
                let subParent = (subItem.parentId?.isEmpty == false) ? subItem.parentId : nil
                let expParent = (expectedParentId?.isEmpty == false) ? expectedParentId : nil
                let parentMatches = (subParent == expParent)

                let rankMatches: Bool
                if let expectedRank {
                    rankMatches = (subItem.order != nil && abs(subItem.order! - expectedRank) < 0.0001)
                } else {
                    rankMatches = true
                }

                if parentMatches && rankMatches {
                    optimisticMutations.removeValue(forKey: id)
                }
                // Else stale subscription frame still has old parent/order -> keep mutation pending

            case .delete:
                // Item IS STILL present in the incoming subscription!
                // Do NOT clear; keep mutation pending so the item remains hidden until genuinely absent
                break
            }
        }

        // 2. Semantic confirmation of pending created items by value
        for (id, pending) in pendingCreatedItems {
            guard let subItem = incomingMap[id] else {
                // Item not in subscription at all -> keep pending
                continue
            }

            let typeMatches = (subItem.typeId == pending.typeId)

            let subParent = (subItem.parentId?.isEmpty == false) ? subItem.parentId : nil
            let pendingParent = (pending.parentId?.isEmpty == false) ? pending.parentId : nil
            let parentMatches = (subParent == pendingParent)

            let orderMatches: Bool
            if let pendingOrder = pending.order {
                orderMatches = (subItem.order != nil && abs(subItem.order! - pendingOrder) < 0.0001)
            } else {
                orderMatches = (subItem.order == nil)
            }

            let titleMatches: Bool
            if !pending.title.isEmpty {
                titleMatches = (subItem.title.trimmingCharacters(in: .whitespacesAndNewlines) == pending.title.trimmingCharacters(in: .whitespacesAndNewlines))
            } else {
                titleMatches = true
            }

            if typeMatches && parentMatches && orderMatches && titleMatches {
                // Subscription has fully confirmed the created object and all its properties!
                pendingCreatedItems.removeValue(forKey: id)
            }
            // Else intermediate/stale frame (e.g. object exists before order/parent properties written)
            // -> keep pending item authoritative
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

        // 2. Overlay pending created items that are still pending.
        // Pending created items take precedence over intermediate/incomplete subscription frames!
        for (id, pendingItem) in pendingCreatedItems {
            mergedItems[id] = pendingItem
        }

        // 3. Overlay optimistic mutations
        for (id, mutation) in optimisticMutations {
            switch mutation {
            case .delete:
                mergedItems.removeValue(forKey: id)
            case .rename(let newTitle):
                if let item = mergedItems[id] {
                    mergedItems[id] = PinkhaHierarchyRawItem(
                        objectId: item.objectId,
                        typeId: item.typeId,
                        title: newTitle,
                        parentId: item.parentId,
                        order: item.order,
                        kind: item.kind
                    )
                }
            case .order(let newRank):
                if let item = mergedItems[id] {
                    mergedItems[id] = PinkhaHierarchyRawItem(
                        objectId: item.objectId,
                        typeId: item.typeId,
                        title: item.title,
                        parentId: item.parentId,
                        order: newRank,
                        kind: item.kind
                    )
                }
            case .move(let newParentId, let newRank):
                if let item = mergedItems[id] {
                    mergedItems[id] = PinkhaHierarchyRawItem(
                        objectId: item.objectId,
                        typeId: item.typeId,
                        title: item.title,
                        parentId: newParentId,
                        order: newRank ?? item.order,
                        kind: item.kind
                    )
                }
            }
        }

        let snapshot = PinkhaHierarchyBuilder.build(items: Array(mergedItems.values))
        self.currentSnapshot = snapshot
        return snapshot
    }
}
