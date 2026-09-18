import Foundation

/// Constructs an immutable, cycle-safe `PinkhaHierarchySnapshot` from flat `PinkhaHierarchyRawItem`s.
public enum PinkhaHierarchyBuilder {

    /// Builds a snapshot from a list of raw items.
    /// Safely handles self-parenting, cycles, or broken parent references.
    public static func build(items: [PinkhaHierarchyRawItem]) -> PinkhaHierarchySnapshot {
        guard !items.isEmpty else {
            return .empty
        }

        var itemMap: [String: PinkhaHierarchyRawItem] = [:]
        for item in items {
            itemMap[item.objectId] = item
        }

        // Clean sanitized parent IDs (break self-parents and cycles)
        var parentMap: [String: String?] = [:]
        for item in items {
            if let parentId = item.parentId {
                if parentId == item.objectId {
                    // Self-parenting: treat as root
                    parentMap[item.objectId] = nil
                } else if itemMap[parentId] == nil {
                    // Parent does not exist in items: treat as root
                    parentMap[item.objectId] = nil
                } else {
                    parentMap[item.objectId] = parentId
                }
            } else {
                parentMap[item.objectId] = nil
            }
        }

        // Detect and break multi-node cycles in parentMap
        for item in items {
            var visited = Set<String>()
            var curr = item.objectId
            while let p = parentMap[curr], let nextParent = p {
                if visited.contains(curr) {
                    // Cycle detected! Break cycle by moving item to root
                    parentMap[item.objectId] = nil
                    break
                }
                visited.insert(curr)
                curr = nextParent
            }
        }

        // Group children by sanitized parentId
        var childrenByParent: [String: [PinkhaHierarchyRawItem]] = [:]
        var rootItems: [PinkhaHierarchyRawItem] = []

        for item in items {
            let sanitizedParent = parentMap[item.objectId] ?? nil
            if let sanitizedParent {
                childrenByParent[sanitizedParent, default: []].append(item)
            } else {
                rootItems.append(item)
            }
        }

        // Sort root items
        let sortedRoots = PinkhaHierarchyOrdering.sort(rawItems: rootItems)

        var allNodes: [String: PinkhaHierarchyNode] = [:]

        func buildNode(from raw: PinkhaHierarchyRawItem) -> PinkhaHierarchyNode {
            let rawChildren = childrenByParent[raw.objectId] ?? []
            let sortedChildren = PinkhaHierarchyOrdering.sort(rawItems: rawChildren)
            let builtChildren = sortedChildren.map { buildNode(from: $0) }

            let node = PinkhaHierarchyNode(
                objectId: raw.objectId,
                typeId: raw.typeId,
                title: raw.title,
                parentId: parentMap[raw.objectId] ?? nil,
                order: raw.order,
                kind: raw.kind,
                children: builtChildren
            )
            allNodes[node.objectId] = node
            return node
        }

        let rootNodes = sortedRoots.map { buildNode(from: $0) }

        return PinkhaHierarchySnapshot(rootNodes: rootNodes, allNodes: allNodes)
    }
}
