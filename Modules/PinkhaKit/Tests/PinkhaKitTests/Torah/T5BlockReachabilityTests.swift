import Foundation
import Testing
@testable import PinkhaKit

@Suite("T5 authorized block tree reachability")
struct T5BlockReachabilityTests {
    typealias Node = T5BlockReachability.Node

    @Test func reachableDescendantsExcludeRootAndOrphans() async throws {
        let result = try await T5BlockReachability.evaluate(spaceID: "S", rootID: "doc", nodes: [
            Node(id: "doc", childIDs: ["K"]), Node(id: "K", childIDs: ["Q"]), Node(id: "Q"),
            Node(id: "orphan", childIDs: ["missing-outside-tree"])
        ])
        #expect(result.isVerified)
        #expect(result.reachableBlockIDs == ["K", "Q"])
        #expect(result.unreachableNodeIDs == ["orphan"])
        #expect(result.rootID == "doc")
        #expect(result.spaceID == "S")
    }

    @Test func malformedReachableGraphsNeverYieldUsableTargets() async throws {
        let cases: [([Node], T5BlockReachability.Issue)] = [
            ([Node(id: "other")], .missingRoot),
            ([Node(id: "doc"), Node(id: "doc")], .duplicateNodeID),
            ([Node(id: "doc"), Node(id: "")], .emptyIdentifier),
            ([Node(id: "doc", childIDs: ["absent"])], .missingChild),
            ([Node(id: "doc", childIDs: ["K", "K"]), Node(id: "K")], .duplicateChildID),
            ([Node(id: "doc", childIDs: ["K"]), Node(id: "K", childIDs: ["doc"])], .cycle),
            ([Node(id: "doc", childIDs: ["K", "Q"]), Node(id: "K", childIDs: ["child"]),
              Node(id: "Q", childIDs: ["child"]), Node(id: "child")], .multipleParents)
        ]
        for (nodes, issue) in cases {
            let result = try await T5BlockReachability.evaluate(spaceID: "S", rootID: "doc", nodes: nodes)
            #expect(!result.isVerified)
            #expect(result.issues.contains(issue))
            #expect(result.reachableBlockIDs.isEmpty)
        }
    }

    @Test func scopeAndNodeBoundFailExplicitly() async throws {
        let invalidScope = try await T5BlockReachability.evaluate(spaceID: "", rootID: "doc", nodes: [Node(id: "doc")])
        #expect(invalidScope.issues == [.invalidScope])
        let bounded = try await T5BlockReachability.evaluate(spaceID: "S", rootID: "doc", nodes: [Node(id: "doc"), Node(id: "K")], nodeLimit: 1)
        #expect(bounded.issues == [.nodeLimitReached])
        #expect(bounded.reachableBlockIDs.isEmpty)
    }

    @Test func deepDocumentUsesIterativeTraversal() async throws {
        let nodes = (0..<2_000).map { index in
            Node(id: index == 0 ? "doc" : "b\(index)", childIDs: index == 1_999 ? [] : ["b\(index + 1)"])
        }
        let result = try await T5BlockReachability.evaluate(spaceID: "S", rootID: "doc", nodes: nodes)
        #expect(result.isVerified)
        #expect(result.reachableBlockIDs.count == 1_999)
        #expect(result.reachableBlockIDs.contains("b1999"))
    }

    @Test func cancelledEvaluationDoesNotPublishGraph() async {
        let task = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            return try await T5BlockReachability.evaluate(spaceID: "S", rootID: "doc", nodes: [Node(id: "doc")])
        }
        do {
            _ = try await task.value
            Issue.record("Cancelled graph evaluation published a result")
        } catch is CancellationError {
        } catch {
            Issue.record("Unexpected error: \(error)")
        }
    }

    @Test func wideTreeAndLargeMalformedChildListStayWithinTreeValidation() async throws {
        let children = (0..<2_048).map { "b\($0)" }
        let wide = try await T5BlockReachability.evaluate(
            spaceID: "S", rootID: "doc",
            nodes: [Node(id: "doc", childIDs: children)] + children.map { Node(id: $0) }
        )
        #expect(wide.isVerified)
        #expect(wide.reachableBlockIDs == Set(children))

        let malformed = try await T5BlockReachability.evaluate(
            spaceID: "S", rootID: "doc",
            nodes: [Node(id: "doc", childIDs: Array(repeating: "K", count: 50_000)), Node(id: "K")]
        )
        #expect(malformed.issues == [.duplicateChildID])
        #expect(malformed.reachableBlockIDs.isEmpty)
    }
}
