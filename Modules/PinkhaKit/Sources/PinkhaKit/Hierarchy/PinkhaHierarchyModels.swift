import Foundation

/// Defines whether a node represents a folder or a writing document.
public enum PinkhaHierarchyNodeKind: String, Codable, Sendable, Equatable, Hashable {
    case folder
    case writingDocument
}

/// A raw, flat representation of an object in the hierarchy as loaded from persistence.
public struct PinkhaHierarchyRawItem: Sendable, Equatable, Hashable {
    public let objectId: String
    public let typeId: String
    public let title: String
    public let parentId: String?
    public let order: Double?
    public let kind: PinkhaHierarchyNodeKind

    public init(
        objectId: String,
        typeId: String,
        title: String,
        parentId: String?,
        order: Double?,
        kind: PinkhaHierarchyNodeKind
    ) {
        self.objectId = objectId
        self.typeId = typeId
        self.title = title
        self.parentId = parentId
        self.order = order
        self.kind = kind
    }
}

/// A domain node in the tree hierarchy with its ordered children.
public struct PinkhaHierarchyNode: Identifiable, Sendable, Equatable, Hashable {
    public let objectId: String
    public let typeId: String
    public var title: String
    public var parentId: String?
    public var order: Double?
    public let kind: PinkhaHierarchyNodeKind
    public var children: [PinkhaHierarchyNode]

    public var id: String { objectId }

    public init(
        objectId: String,
        typeId: String,
        title: String,
        parentId: String?,
        order: Double?,
        kind: PinkhaHierarchyNodeKind,
        children: [PinkhaHierarchyNode] = []
    ) {
        self.objectId = objectId
        self.typeId = typeId
        self.title = title
        self.parentId = parentId
        self.order = order
        self.kind = kind
        self.children = children
    }
}

/// An immutable snapshot of the hierarchy tree, providing indexed lookups and ancestor/descendant queries.
public struct PinkhaHierarchySnapshot: Sendable, Equatable {
    public let rootNodes: [PinkhaHierarchyNode]
    public let allNodes: [String: PinkhaHierarchyNode]

    public init(rootNodes: [PinkhaHierarchyNode], allNodes: [String: PinkhaHierarchyNode]) {
        self.rootNodes = rootNodes
        self.allNodes = allNodes
    }

    public static let empty = PinkhaHierarchySnapshot(rootNodes: [], allNodes: [:])

    public func node(for objectId: String) -> PinkhaHierarchyNode? {
        allNodes[objectId]
    }

    public func children(of parentId: String?) -> [PinkhaHierarchyNode] {
        if let parentId {
            return allNodes[parentId]?.children ?? []
        } else {
            return rootNodes
        }
    }

    /// Returns the sequence of ancestor nodes starting from direct parent up to root.
    public func ancestors(of objectId: String) -> [PinkhaHierarchyNode] {
        var result: [PinkhaHierarchyNode] = []
        var currentId = allNodes[objectId]?.parentId
        var visited = Set<String>()

        while let parentId = currentId, !visited.contains(parentId), let parent = allNodes[parentId] {
            visited.insert(parentId)
            result.append(parent)
            currentId = parent.parentId
        }
        return result
    }

    /// Returns all descendant object IDs for the given node recursively.
    public func descendantIds(of objectId: String) -> Set<String> {
        guard let node = allNodes[objectId] else { return [] }
        var result = Set<String>()
        func collect(_ current: PinkhaHierarchyNode) {
            for child in current.children {
                result.insert(child.objectId)
                collect(child)
            }
        }
        collect(node)
        return result
    }

    /// Checks if a node is a descendant of an ancestor candidate.
    public func isDescendant(nodeId: String, of ancestorId: String) -> Bool {
        descendantIds(of: ancestorId).contains(nodeId)
    }
}

/// Domain errors representing invalid hierarchy operations.
public enum PinkhaHierarchyError: Error, Sendable, Equatable {
    case selfParent(objectId: String)
    case cycleDetected(objectId: String, targetParentId: String)
    case nodeNotFound(objectId: String)
    case parentNotFound(parentId: String)
    case invalidNodeType(objectId: String)
}
