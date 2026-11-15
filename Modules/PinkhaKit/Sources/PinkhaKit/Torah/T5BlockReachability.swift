import Foundation

public enum T5BlockReachability {
    public struct Node: Equatable, Sendable {
        public let id: String
        public let childIDs: [String]

        public init(id: String, childIDs: [String] = []) {
            self.id = id
            self.childIDs = childIDs
        }
    }

    public enum Issue: Hashable, Sendable {
        case invalidScope
        case nodeLimitReached
        case emptyIdentifier
        case duplicateNodeID
        case missingRoot
        case missingChild
        case duplicateChildID
        case multipleParents
        case cycle
    }

    public struct Result: Equatable, Sendable {
        public let spaceID: String
        public let rootID: String
        public let reachableBlockIDs: Set<String>
        public let unreachableNodeIDs: Set<String>
        public let issues: Set<Issue>

        public var isVerified: Bool { issues.isEmpty }
    }

    public static func evaluate(
        spaceID: String, rootID: String, nodes: [Node], nodeLimit: Int = 20_000
    ) async throws -> Result {
        try Task.checkCancellation()
        var issues = Set<Issue>()
        guard !spaceID.isEmpty, !rootID.isEmpty else {
            return Result(spaceID: spaceID, rootID: rootID, reachableBlockIDs: [], unreachableNodeIDs: [], issues: [.invalidScope])
        }
        guard nodes.count <= max(1, nodeLimit) else {
            return Result(spaceID: spaceID, rootID: rootID, reachableBlockIDs: [], unreachableNodeIDs: [], issues: [.nodeLimitReached])
        }
        var index: [String: Node] = [:]
        for (offset, node) in nodes.enumerated() {
            if offset.isMultiple(of: 128) {
                await Task.yield()
                try Task.checkCancellation()
            }
            if node.id.isEmpty { issues.insert(.emptyIdentifier) }
            if index.updateValue(node, forKey: node.id) != nil { issues.insert(.duplicateNodeID) }
        }
        if index[rootID] == nil { issues.insert(.missingRoot) }
        guard issues.isEmpty else {
            return Result(spaceID: spaceID, rootID: rootID, reachableBlockIDs: [], unreachableNodeIDs: Set(index.keys), issues: issues)
        }
        var stack: [(id: String, exiting: Bool)] = [(rootID, false)]
        var active = Set<String>()
        var reached = Set<String>()
        var completed = Set<String>()
        var parentCounts: [String: Int] = [:]
        var operations = 0
        walk: while let frame = stack.popLast() {
            operations += 1
            if operations.isMultiple(of: 128) {
                await Task.yield()
                try Task.checkCancellation()
            }
            if frame.exiting {
                active.remove(frame.id)
                completed.insert(frame.id)
                continue
            }
            if active.contains(frame.id) { issues.insert(.cycle); break }
            if completed.contains(frame.id) { continue }
            guard let node = index[frame.id] else { issues.insert(.missingChild); break }
            active.insert(frame.id)
            reached.insert(frame.id)
            stack.append((frame.id, true))
            var children = Set<String>()
            for child in node.childIDs.reversed() {
                operations += 1
                if operations.isMultiple(of: 128) {
                    await Task.yield()
                    try Task.checkCancellation()
                }
                // A malformed edge invalidates the tree; stop before an unbounded
                // duplicate or dangling child list can consume further work.
                if child.isEmpty { issues.insert(.emptyIdentifier); break walk }
                guard children.insert(child).inserted else { issues.insert(.duplicateChildID); break walk }
                guard index[child] != nil else { issues.insert(.missingChild); break walk }
                parentCounts[child, default: 0] += 1
                if parentCounts[child, default: 0] > 1 { issues.insert(.multipleParents); break walk }
                if active.contains(child) { issues.insert(.cycle); break walk }
                stack.append((child, false))
            }
        }
        try Task.checkCancellation()
        let unreachable = Set(index.keys).subtracting(reached)
        reached.remove(rootID)
        return Result(
            spaceID: spaceID, rootID: rootID,
            reachableBlockIDs: issues.isEmpty ? reached : [],
            unreachableNodeIDs: unreachable, issues: issues
        )
    }
}
