import Foundation

public struct TorahSourceNode: Identifiable, Hashable, Sendable {
    public let id: String
    public let labelHe: String
    public let labelEn: String?
    public let canonicalKey: String?
    public var children: [TorahSourceNode]
    public var descendantLeafCount: Int
    public var hasDirectLeaves: Bool

    public init(
        id: String,
        labelHe: String,
        labelEn: String? = nil,
        canonicalKey: String? = nil,
        children: [TorahSourceNode] = [],
        descendantLeafCount: Int = 0,
        hasDirectLeaves: Bool = false
    ) {
        self.id = id
        self.labelHe = labelHe
        self.labelEn = labelEn
        self.canonicalKey = canonicalKey
        self.children = children
        self.descendantLeafCount = descendantLeafCount
        self.hasDirectLeaves = hasDirectLeaves
    }
}

public struct TorahSourcePath: Hashable, Sendable {
    public let segments: [TorahSourceNode]

    public init(segments: [TorahSourceNode] = []) {
        self.segments = segments
    }

    public var current: TorahSourceNode? { segments.last }
    public var breadcrumbs: [String] { segments.map(\.labelHe) }
}

public struct TorahSourceHierarchy: Sendable {
    public let roots: [TorahSourceNode]
    public let providerID: String
    public let fetchedAt: Date

    public init(roots: [TorahSourceNode], providerID: String, fetchedAt: Date = Date()) {
        self.roots = roots
        self.providerID = providerID
        self.fetchedAt = fetchedAt
    }
}

public protocol TorahHierarchyProvider: Sendable {
    var providerID: String { get }
    func fetchHierarchy() async throws -> TorahSourceHierarchy
}

public extension TorahSourceNode {
    var compressedChildren: [TorahSourceNode] {
        if children.count == 1, !hasDirectLeaves, canonicalKey == nil {
            return [children[0].compressedTarget]
        }
        return children
    }

    var compressedTarget: TorahSourceNode {
        if children.count == 1, !hasDirectLeaves, canonicalKey == nil {
            return children[0].compressedTarget
        }
        return self
    }

    func compressedPath() -> TorahSourcePath {
        var segments = [self]
        var current = self
        while current.children.count == 1,
              !current.hasDirectLeaves,
              current.canonicalKey == nil {
            current = current.children[0]
            segments.append(current)
        }
        return TorahSourcePath(segments: segments)
    }
}

public extension TorahSourceHierarchy {
    func filtered(
        byAssociatedKeys associatedKeys: Set<String>,
        associationGroups: [(canonicalKey: String, labelHe: String, leafCount: Int)] = []
    ) -> TorahSourceHierarchy {
        let filteredRoots = roots.compactMap {
            $0.filtered(byAssociatedKeys: associatedKeys, associationGroups: associationGroups)
        }
        return TorahSourceHierarchy(
            roots: filteredRoots,
            providerID: providerID,
            fetchedAt: fetchedAt
        )
    }
}

private extension TorahSourceNode {
    func filtered(
        byAssociatedKeys keys: Set<String>,
        associationGroups: [(canonicalKey: String, labelHe: String, leafCount: Int)]
    ) -> TorahSourceNode? {
        if children.isEmpty {
            guard let canonicalKey else { return nil }

            func matchesBook(_ candidate: String) -> Bool {
                candidate == canonicalKey || TorahReferenceUtil.bookTitle(from: candidate) == canonicalKey
            }

            let matchingGroups = associationGroups.filter { matchesBook($0.canonicalKey) }
            let matchingKeys = matchingGroups.isEmpty
                ? keys.filter(matchesBook)
                : Set(matchingGroups.map(\.canonicalKey))
            guard !matchingKeys.isEmpty else { return nil }

            var childNodes: [TorahSourceNode] = []
            let directBookMatch = matchingKeys.contains(canonicalKey)
            let totalLeafCount: Int

            if matchingGroups.isEmpty {
                totalLeafCount = matchingKeys.count
                for key in matchingKeys where key != canonicalKey {
                    childNodes.append(TorahSourceNode(
                        id: "\(id)/\(key)",
                        labelHe: key,
                        labelEn: key,
                        canonicalKey: key,
                        descendantLeafCount: 1,
                        hasDirectLeaves: true
                    ))
                }
            } else {
                totalLeafCount = matchingGroups.reduce(0) { $0 + $1.leafCount }
                for group in matchingGroups where group.canonicalKey != canonicalKey {
                    childNodes.append(TorahSourceNode(
                        id: "\(id)/\(group.canonicalKey)",
                        labelHe: group.labelHe,
                        labelEn: group.canonicalKey,
                        canonicalKey: group.canonicalKey,
                        descendantLeafCount: group.leafCount,
                        hasDirectLeaves: true
                    ))
                }
            }

            childNodes.sort {
                if $0.labelHe != $1.labelHe { return $0.labelHe < $1.labelHe }
                return $0.id < $1.id
            }
            return TorahSourceNode(
                id: id,
                labelHe: labelHe,
                labelEn: labelEn,
                canonicalKey: canonicalKey,
                children: childNodes,
                descendantLeafCount: totalLeafCount,
                hasDirectLeaves: directBookMatch || childNodes.isEmpty
            )
        }

        let filteredChildren = children.compactMap {
            $0.filtered(byAssociatedKeys: keys, associationGroups: associationGroups)
        }
        guard !filteredChildren.isEmpty else { return nil }
        return TorahSourceNode(
            id: id,
            labelHe: labelHe,
            labelEn: labelEn,
            canonicalKey: canonicalKey,
            children: filteredChildren,
            descendantLeafCount: filteredChildren.reduce(0) { $0 + $1.descendantLeafCount },
            hasDirectLeaves: false
        )
    }
}
