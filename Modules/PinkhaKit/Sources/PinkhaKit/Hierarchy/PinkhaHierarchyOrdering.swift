import Foundation

/// Ordering policies and sparse rank calculation for Pinkha hierarchy siblings.
public enum PinkhaHierarchyOrdering {
    public static let initialRank: Double = 1000.0
    public static let defaultStep: Double = 1000.0
    public static let minSpacing: Double = 0.001

    /// Sorts an array of nodes using the canonical Pinkha ordering rule:
    /// 1. Nodes with explicit `order` ranks sort ascending by rank.
    /// 2. Nodes without an `order` rank (or with equal rank) sort by `title` (case-insensitive localized).
    /// 3. Final tie-breaker: `objectId` lexicographical ascending.
    public static func sort(nodes: [PinkhaHierarchyNode]) -> [PinkhaHierarchyNode] {
        nodes.sorted { lhs, rhs in
            isOrderedBefore(lhs: lhs, rhs: rhs)
        }
    }

    /// Sorts raw items using the canonical Pinkha ordering rule.
    public static func sort(rawItems: [PinkhaHierarchyRawItem]) -> [PinkhaHierarchyRawItem] {
        rawItems.sorted { lhs, rhs in
            isOrderedBefore(
                lhsOrder: lhs.order, lhsTitle: lhs.title, lhsId: lhs.objectId,
                rhsOrder: rhs.order, rhsTitle: rhs.title, rhsId: rhs.objectId
            )
        }
    }

    public static func isOrderedBefore(lhs: PinkhaHierarchyNode, rhs: PinkhaHierarchyNode) -> Bool {
        isOrderedBefore(
            lhsOrder: lhs.order, lhsTitle: lhs.title, lhsId: lhs.objectId,
            rhsOrder: rhs.order, rhsTitle: rhs.title, rhsId: rhs.objectId
        )
    }

    public static func isOrderedBefore(
        lhsOrder: Double?, lhsTitle: String, lhsId: String,
        rhsOrder: Double?, rhsTitle: String, rhsId: String
    ) -> Bool {
        switch (lhsOrder, rhsOrder) {
        case let (l?, r?):
            if abs(l - r) >= minSpacing {
                return l < r
            }
            // If ranks are virtually identical, fall back to title then ID
            let titleComparison = lhsTitle.localizedCaseInsensitiveCompare(rhsTitle)
            if titleComparison != .orderedSame {
                return titleComparison == .orderedAscending
            }
            return lhsId < rhsId

        case (_?, nil):
            // Ranked nodes appear before unranked nodes
            return true

        case (nil, _?):
            return false

        case (nil, nil):
            let titleComparison = lhsTitle.localizedCaseInsensitiveCompare(rhsTitle)
            if titleComparison != .orderedSame {
                return titleComparison == .orderedAscending
            }
            return lhsId < rhsId
        }
    }

    /// Calculates the rank to append a new item at the end of the existing siblings.
    public static func nextAppendRank(existingSiblings: [PinkhaHierarchyNode]) -> Double {
        let maxRank = existingSiblings.compactMap(\.order).max()
        guard let maxRank else {
            return initialRank
        }
        return maxRank + defaultStep
    }

    /// Calculates a midpoint rank between two existing sibling ranks.
    public static func rankBetween(before: Double?, after: Double?) -> Double {
        switch (before, after) {
        case let (b?, a?):
            return (b + a) / 2.0
        case let (b?, nil):
            return b + defaultStep
        case let (nil, a?):
            return a > defaultStep ? a - defaultStep : a / 2.0
        case (nil, nil):
            return initialRank
        }
    }

    /// Determines if a sibling group needs to be rebalanced (ranks too dense or non-monotonic).
    public static func shouldRebalance(siblings: [PinkhaHierarchyNode]) -> Bool {
        let ranked = siblings.compactMap(\.order)
        guard ranked.count > 1 else { return false }

        for i in 0..<(ranked.count - 1) {
            let diff = ranked[i + 1] - ranked[i]
            if diff <= minSpacing {
                return true
            }
        }
        return false
    }

    /// Rebalances only the given sibling group, assigning evenly spaced ranks (1000, 2000, 3000...).
    /// Returns the complete list of (objectId, newRank) pairs for the sibling group.
    public static func rebalanceRanks(siblings: [PinkhaHierarchyNode]) -> [(objectId: String, newRank: Double)] {
        let sorted = sort(nodes: siblings)
        return sorted.enumerated().map { index, node in
            (objectId: node.objectId, newRank: Double(index + 1) * defaultStep)
        }
    }
}
