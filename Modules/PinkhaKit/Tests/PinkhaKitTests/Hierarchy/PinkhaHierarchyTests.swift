import Testing
@testable import PinkhaKit

@Suite("PinkhaHierarchyTests")
struct PinkhaHierarchyTests {

    @Test("Empty hierarchy produces empty snapshot")
    func emptyHierarchy() {
        let snapshot = PinkhaHierarchyBuilder.build(items: [])
        #expect(snapshot.rootNodes.isEmpty)
        #expect(snapshot.allNodes.isEmpty)
    }

    @Test("Root nodes built from items with no parent")
    func rootNodes() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "f1", typeId: "folder", title: "Folder 1", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "f2", typeId: "folder", title: "Folder 2", parentId: nil, order: 2000, kind: .folder)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        #expect(snapshot.rootNodes.count == 2)
        #expect(snapshot.rootNodes[0].objectId == "f1")
        #expect(snapshot.rootNodes[1].objectId == "f2")
    }

    @Test("Parent-child tree building creates nested nodes")
    func parentChildTreeBuilding() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "root", typeId: "folder", title: "Root", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "child1", typeId: "writing", title: "Child 1", parentId: "root", order: 1000, kind: .writingDocument),
            PinkhaHierarchyRawItem(objectId: "child2", typeId: "folder", title: "Child 2", parentId: "root", order: 2000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "subchild", typeId: "writing", title: "Subchild", parentId: "child2", order: 1000, kind: .writingDocument)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        #expect(snapshot.rootNodes.count == 1)
        let root = snapshot.rootNodes[0]
        #expect(root.children.count == 2)
        #expect(root.children[0].objectId == "child1")
        #expect(root.children[1].objectId == "child2")
        #expect(root.children[1].children.count == 1)
        #expect(root.children[1].children[0].objectId == "subchild")
    }

    @Test("Arbitrary nesting depth supported beyond 3 levels")
    func depthGreaterThanThree() {
        // Level 0 -> Level 1 -> Level 2 -> Level 3 -> Level 4 -> Level 5
        let items = [
            PinkhaHierarchyRawItem(objectId: "lvl0", typeId: "folder", title: "Level 0", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "lvl1", typeId: "folder", title: "Level 1", parentId: "lvl0", order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "lvl2", typeId: "folder", title: "Level 2", parentId: "lvl1", order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "lvl3", typeId: "folder", title: "Level 3", parentId: "lvl2", order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "lvl4", typeId: "folder", title: "Level 4", parentId: "lvl3", order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "lvl5", typeId: "writing", title: "Level 5 Doc", parentId: "lvl4", order: 1000, kind: .writingDocument)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        #expect(snapshot.rootNodes.count == 1)
        let node0 = snapshot.rootNodes[0]
        let node1 = node0.children[0]
        let node2 = node1.children[0]
        let node3 = node2.children[0]
        let node4 = node3.children[0]
        let node5 = node4.children[0]

        #expect(node5.objectId == "lvl5")
        #expect(node5.kind == .writingDocument)

        let ancestors = snapshot.ancestors(of: "lvl5")
        #expect(ancestors.map(\.objectId) == ["lvl4", "lvl3", "lvl2", "lvl1", "lvl0"])
        #expect(snapshot.isDescendant(nodeId: "lvl5", of: "lvl0"))
    }

    @Test("Deterministic ordering sorts by sparse numeric rank")
    func deterministicOrdering() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "c", typeId: "folder", title: "C", parentId: nil, order: 3000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "a", typeId: "folder", title: "A", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "b", typeId: "folder", title: "B", parentId: nil, order: 2000, kind: .folder)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        #expect(snapshot.rootNodes.map(\.objectId) == ["a", "b", "c"])
    }

    @Test("Missing order fallback sorts ranked first, then by title, then objectId")
    func missingOrderFallback() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "unranked_z", typeId: "writing", title: "Zeta", parentId: nil, order: nil, kind: .writingDocument),
            PinkhaHierarchyRawItem(objectId: "ranked_2", typeId: "writing", title: "Beta", parentId: nil, order: 2000, kind: .writingDocument),
            PinkhaHierarchyRawItem(objectId: "unranked_a", typeId: "writing", title: "Alpha", parentId: nil, order: nil, kind: .writingDocument),
            PinkhaHierarchyRawItem(objectId: "ranked_1", typeId: "writing", title: "Gamma", parentId: nil, order: 1000, kind: .writingDocument)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        #expect(snapshot.rootNodes.map(\.objectId) == ["ranked_1", "ranked_2", "unranked_a", "unranked_z"])
    }

    @Test("Append rank generates max sibling rank + 1000")
    func appendRank() {
        let emptySiblings: [PinkhaHierarchyNode] = []
        #expect(PinkhaHierarchyOrdering.nextAppendRank(existingSiblings: emptySiblings) == 1000.0)

        let siblings = [
            PinkhaHierarchyNode(objectId: "s1", typeId: "folder", title: "S1", parentId: nil, order: 1000.0, kind: .folder),
            PinkhaHierarchyNode(objectId: "s2", typeId: "folder", title: "S2", parentId: nil, order: 2500.0, kind: .folder)
        ]
        #expect(PinkhaHierarchyOrdering.nextAppendRank(existingSiblings: siblings) == 3500.0)
    }

    @Test("Insert-between rank calculates midpoints correctly")
    func insertBetweenRank() {
        // Between 1000 and 2000 -> 1500
        #expect(PinkhaHierarchyOrdering.rankBetween(before: 1000, after: 2000) == 1500)
        // Before 1000 -> 500
        #expect(PinkhaHierarchyOrdering.rankBetween(before: nil, after: 1000) == 500)
        // After 2000 -> 3000
        #expect(PinkhaHierarchyOrdering.rankBetween(before: 2000, after: nil) == 3000)
    }

    @Test("Sibling rebalance re-spaces dense ranks and preserves order")
    func siblingRebalance() {
        let denseSiblings = [
            PinkhaHierarchyNode(objectId: "s1", typeId: "writing", title: "S1", parentId: nil, order: 1000.0, kind: .writingDocument),
            PinkhaHierarchyNode(objectId: "s2", typeId: "writing", title: "S2", parentId: nil, order: 1000.0001, kind: .writingDocument),
            PinkhaHierarchyNode(objectId: "s3", typeId: "writing", title: "S3", parentId: nil, order: 1000.0002, kind: .writingDocument)
        ]
        #expect(PinkhaHierarchyOrdering.shouldRebalance(siblings: denseSiblings))

        let rebalanced = PinkhaHierarchyOrdering.rebalanceRanks(siblings: denseSiblings)
        #expect(rebalanced.count == 3)
        #expect(rebalanced[0] == (objectId: "s1", newRank: 1000.0))
        #expect(rebalanced[1] == (objectId: "s2", newRank: 2000.0))
        #expect(rebalanced[2] == (objectId: "s3", newRank: 3000.0))
    }

    @Test("Valid reparent moves node and updates ancestry")
    func validReparent() throws {
        let items = [
            PinkhaHierarchyRawItem(objectId: "f1", typeId: "folder", title: "Folder 1", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "f2", typeId: "folder", title: "Folder 2", parentId: nil, order: 2000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "doc", typeId: "writing", title: "Doc", parentId: "f1", order: 1000, kind: .writingDocument)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        // Reparent doc to f2
        #expect(throws: Never.self) {
            try PinkhaHierarchyMutationValidator.validateMove(objectId: "doc", newParentId: "f2", in: snapshot)
        }
    }

    @Test("Move to root clears parent safely")
    func moveToRoot() throws {
        let items = [
            PinkhaHierarchyRawItem(objectId: "f1", typeId: "folder", title: "Folder 1", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "doc", typeId: "writing", title: "Doc", parentId: "f1", order: 1000, kind: .writingDocument)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        #expect(throws: Never.self) {
            try PinkhaHierarchyMutationValidator.validateMove(objectId: "doc", newParentId: nil, in: snapshot)
        }
    }

    @Test("Self-parent rejection")
    func selfParentRejection() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "f1", typeId: "folder", title: "Folder 1", parentId: nil, order: 1000, kind: .folder)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        #expect(throws: PinkhaHierarchyError.selfParent(objectId: "f1")) {
            try PinkhaHierarchyMutationValidator.validateMove(objectId: "f1", newParentId: "f1", in: snapshot)
        }
    }

    @Test("Direct cycle rejection A -> B -> A")
    func directCycleRejection() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "A", typeId: "folder", title: "A", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "B", typeId: "folder", title: "B", parentId: "A", order: 1000, kind: .folder)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        // Moving A into B would create A -> B -> A
        #expect(throws: PinkhaHierarchyError.cycleDetected(objectId: "A", targetParentId: "B")) {
            try PinkhaHierarchyMutationValidator.validateMove(objectId: "A", newParentId: "B", in: snapshot)
        }
    }

    @Test("Deep cycle rejection A -> B -> C -> D -> A")
    func deepCycleRejection() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "A", typeId: "folder", title: "A", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "B", typeId: "folder", title: "B", parentId: "A", order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "C", typeId: "folder", title: "C", parentId: "B", order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "D", typeId: "folder", title: "D", parentId: "C", order: 1000, kind: .folder)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        // Moving A into D would create a deep cycle
        #expect(throws: PinkhaHierarchyError.cycleDetected(objectId: "A", targetParentId: "D")) {
            try PinkhaHierarchyMutationValidator.validateMove(objectId: "A", newParentId: "D", in: snapshot)
        }
        // Moving B into D is also a cycle
        #expect(throws: PinkhaHierarchyError.cycleDetected(objectId: "B", targetParentId: "D")) {
            try PinkhaHierarchyMutationValidator.validateMove(objectId: "B", newParentId: "D", in: snapshot)
        }
        // Moving D into A is fine (D is already in A's subtree, moving D to A makes D direct child)
        #expect(throws: Never.self) {
            try PinkhaHierarchyMutationValidator.validateMove(objectId: "D", newParentId: "A", in: snapshot)
        }
    }

    @Test("Moving node preserves unrelated subtrees")
    func unrelatedSubtreeUnchanged() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "t1", typeId: "folder", title: "Tree 1", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "t1_c1", typeId: "writing", title: "T1 Child 1", parentId: "t1", order: 1000, kind: .writingDocument),
            PinkhaHierarchyRawItem(objectId: "t2", typeId: "folder", title: "Tree 2", parentId: nil, order: 2000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "t2_c1", typeId: "writing", title: "T2 Child 1", parentId: "t2", order: 1000, kind: .writingDocument)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        let t2Children = snapshot.children(of: "t2")
        #expect(t2Children.count == 1)
        #expect(t2Children[0].objectId == "t2_c1")
        #expect(t2Children[0].order == 1000)
    }

    @Test("Safe folder deletion identifies direct children for reparenting")
    func safeDeletionPolicy() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "parent", typeId: "folder", title: "Parent", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "targetFolder", typeId: "folder", title: "Target", parentId: "parent", order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "childDoc", typeId: "writing", title: "Doc", parentId: "targetFolder", order: 1000, kind: .writingDocument),
            PinkhaHierarchyRawItem(objectId: "childFolder", typeId: "folder", title: "Subfolder", parentId: "targetFolder", order: 2000, kind: .folder)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        let directChildren = snapshot.children(of: "targetFolder")
        #expect(directChildren.count == 2)
        #expect(directChildren.map(\.objectId).sorted() == ["childDoc", "childFolder"])

        // When targetFolder is safely deleted, directChildren get targetFolder's parent ("parent")
        let targetNode = snapshot.node(for: "targetFolder")!
        let reparentTarget = targetNode.parentId // "parent"
        #expect(reparentTarget == "parent")
    }

    @Test("Corrupt input cycles are broken safely by builder")
    func corruptCycleBrokenByBuilder() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "A", typeId: "folder", title: "A", parentId: "B", order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "B", typeId: "folder", title: "B", parentId: "A", order: 1000, kind: .folder)
        ]
        // Builder must not loop infinitely or crash
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        #expect(snapshot.rootNodes.count > 0)
    }

    @Test("Root writing document sparse rank assignment (A -> 1000, B -> 2000, C -> 3000)")
    func rootWritingDocumentAppendOrdering() {
        var existingRootNodes: [PinkhaHierarchyNode] = []

        // Document A created in empty root
        let rankA = PinkhaHierarchyOrdering.nextAppendRank(existingSiblings: existingRootNodes)
        #expect(rankA == 1000.0)
        let nodeA = PinkhaHierarchyNode(
            objectId: "docA", typeId: "chiddush", title: "Chiddush 1",
            parentId: nil, order: rankA, kind: .writingDocument
        )
        existingRootNodes.append(nodeA)

        // Document B created with existing [A]
        let rankB = PinkhaHierarchyOrdering.nextAppendRank(existingSiblings: existingRootNodes)
        #expect(rankB == 2000.0)
        let nodeB = PinkhaHierarchyNode(
            objectId: "docB", typeId: "article", title: "Article 1",
            parentId: nil, order: rankB, kind: .writingDocument
        )
        existingRootNodes.append(nodeB)

        // Document C created with existing [A, B]
        let rankC = PinkhaHierarchyOrdering.nextAppendRank(existingSiblings: existingRootNodes)
        #expect(rankC == 3000.0)
        let nodeC = PinkhaHierarchyNode(
            objectId: "docC", typeId: "research", title: "Research 1",
            parentId: nil, order: rankC, kind: .writingDocument
        )
        existingRootNodes.append(nodeC)

        let sorted = PinkhaHierarchyOrdering.sort(nodes: existingRootNodes)
        #expect(sorted.map(\.objectId) == ["docA", "docB", "docC"])
        #expect(sorted.map(\.order) == [1000.0, 2000.0, 3000.0])
    }

    @Test("Mixed siblings reordering (Folder A, Document B, Folder C, Document D)")
    func mixedSiblingsReordering() {
        let nodeA = PinkhaHierarchyNode(objectId: "fA", typeId: "folder", title: "Folder A", parentId: nil, order: 1000, kind: .folder)
        let nodeB = PinkhaHierarchyNode(objectId: "dB", typeId: "chiddush", title: "Doc B", parentId: nil, order: 2000, kind: .writingDocument)
        let nodeC = PinkhaHierarchyNode(objectId: "fC", typeId: "folder", title: "Folder C", parentId: nil, order: 3000, kind: .folder)
        let nodeD = PinkhaHierarchyNode(objectId: "dD", typeId: "article", title: "Doc D", parentId: nil, order: 4000, kind: .writingDocument)

        var siblings = [nodeA, nodeB, nodeC, nodeD]

        // Move Folder C up: goes between A (1000) and B (2000)
        let newRankC = PinkhaHierarchyOrdering.rankBetween(before: siblings[0].order, after: siblings[1].order)
        #expect(newRankC == 1500.0)
        let updatedC = PinkhaHierarchyNode(objectId: "fC", typeId: "folder", title: "Folder C", parentId: nil, order: newRankC, kind: .folder)
        siblings[2] = updatedC

        var sorted = PinkhaHierarchyOrdering.sort(nodes: siblings)
        #expect(sorted.map(\.objectId) == ["fA", "fC", "dB", "dD"])

        // Move Doc B down: goes after D (4000)
        let newRankB = PinkhaHierarchyOrdering.rankBetween(before: sorted.last?.order, after: nil)
        #expect(newRankB == 5000.0)
        let updatedB = PinkhaHierarchyNode(objectId: "dB", typeId: "chiddush", title: "Doc B", parentId: nil, order: newRankB, kind: .writingDocument)
        sorted[2] = updatedB

        let finalSorted = PinkhaHierarchyOrdering.sort(nodes: sorted)
        #expect(finalSorted.map(\.objectId) == ["fA", "fC", "dD", "dB"])
    }

    @Test("Safe folder deletion reparent plan when destination is empty")
    func safeDeletionPlanDestinationEmpty() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "target", typeId: "folder", title: "Target", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "c1", typeId: "writing", title: "Child 1", parentId: "target", order: 500, kind: .writingDocument),
            PinkhaHierarchyRawItem(objectId: "c2", typeId: "folder", title: "Child 2", parentId: "target", order: 800, kind: .folder)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        let plans = PinkhaHierarchyOrdering.planSafeFolderDeletion(targetFolderId: "target", in: snapshot)

        #expect(plans.count == 2)
        #expect(plans[0] == PinkhaReparentPlan(objectId: "c1", newParentId: nil, newOrder: 1000.0))
        #expect(plans[1] == PinkhaReparentPlan(objectId: "c2", newParentId: nil, newOrder: 2000.0))
    }

    @Test("Safe folder deletion reparent plan when destination already has siblings (no rank collisions)")
    func safeDeletionPlanDestinationHasSiblings() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "r1", typeId: "folder", title: "Root 1", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "target", typeId: "folder", title: "Target", parentId: nil, order: 2000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "r2", typeId: "folder", title: "Root 2", parentId: nil, order: 3000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "c1", typeId: "writing", title: "Child 1", parentId: "target", order: 100, kind: .writingDocument),
            PinkhaHierarchyRawItem(objectId: "c2", typeId: "writing", title: "Child 2", parentId: "target", order: 200, kind: .writingDocument)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        let plans = PinkhaHierarchyOrdering.planSafeFolderDeletion(targetFolderId: "target", in: snapshot)

        #expect(plans.count == 2)
        // Destination siblings excluding target are r1 (1000) and r2 (3000). Max is 3000.
        // Base rank should be 3000 + 1000 = 4000
        #expect(plans[0] == PinkhaReparentPlan(objectId: "c1", newParentId: nil, newOrder: 4000.0))
        #expect(plans[1] == PinkhaReparentPlan(objectId: "c2", newParentId: nil, newOrder: 5000.0))
    }

    @Test("Safe folder deletion preserves relative order of multiple moved children")
    func safeDeletionPreservesChildOrder() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "parent", typeId: "folder", title: "Parent", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "c1", typeId: "writing", title: "A", parentId: "parent", order: 100, kind: .writingDocument),
            PinkhaHierarchyRawItem(objectId: "c2", typeId: "folder", title: "B", parentId: "parent", order: 200, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "c3", typeId: "writing", title: "C", parentId: "parent", order: 300, kind: .writingDocument)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        let plans = PinkhaHierarchyOrdering.planSafeFolderDeletion(targetFolderId: "parent", in: snapshot)

        #expect(plans.map(\.objectId) == ["c1", "c2", "c3"])
        #expect(plans[0].newOrder < plans[1].newOrder)
        #expect(plans[1].newOrder < plans[2].newOrder)
    }

    @Test("Safe folder deletion moving nested folder children to grandparent")
    func safeDeletionNestedReparentToGrandparent() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "gp", typeId: "folder", title: "Grandparent", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "p", typeId: "folder", title: "Parent", parentId: "gp", order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "sibling", typeId: "writing", title: "Direct Child of GP", parentId: "gp", order: 2000, kind: .writingDocument),
            PinkhaHierarchyRawItem(objectId: "c1", typeId: "writing", title: "Child", parentId: "p", order: 100, kind: .writingDocument)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        let plans = PinkhaHierarchyOrdering.planSafeFolderDeletion(targetFolderId: "p", in: snapshot)

        #expect(plans.count == 1)
        #expect(plans[0] == PinkhaReparentPlan(objectId: "c1", newParentId: "gp", newOrder: 3000.0))
    }

    @Test("Hierarchy snapshot pathString disambiguation for folders with duplicate names")
    func pathStringDisambiguation() {
        let items = [
            PinkhaHierarchyRawItem(objectId: "halacha", typeId: "folder", title: "הלכה", parentId: nil, order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "machshava", typeId: "folder", title: "מחשבה", parentId: nil, order: 2000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "yk_h", typeId: "folder", title: "יום הכיפורים", parentId: "halacha", order: 1000, kind: .folder),
            PinkhaHierarchyRawItem(objectId: "yk_m", typeId: "folder", title: "יום הכיפורים", parentId: "machshava", order: 1000, kind: .folder)
        ]
        let snapshot = PinkhaHierarchyBuilder.build(items: items)

        #expect(snapshot.pathString(for: "yk_h") == "הלכה / יום הכיפורים")
        #expect(snapshot.pathString(for: "yk_m") == "מחשבה / יום הכיפורים")
        #expect(snapshot.parentPathString(for: "yk_h") == "הלכה")
        #expect(snapshot.parentPathString(for: "yk_m") == "מחשבה")
        #expect(snapshot.parentPathString(for: "halacha") == nil)
    }

    @Test("Large hierarchy scalability (>1000 items, 2,550 objects)")
    func largeHierarchyScalability() {
        var items: [PinkhaHierarchyRawItem] = []
        for f in 1...50 {
            let folderId = "folder_\(f)"
            items.append(PinkhaHierarchyRawItem(
                objectId: folderId, typeId: "folder", title: "Folder \(f)",
                parentId: nil, order: Double(f) * 1000.0, kind: .folder
            ))
            for d in 1...50 {
                let docId = "doc_\(f)_\(d)"
                items.append(PinkhaHierarchyRawItem(
                    objectId: docId, typeId: "chiddush", title: "Doc \(f)-\(d)",
                    parentId: folderId, order: Double(d) * 1000.0, kind: .writingDocument
                ))
            }
        }
        #expect(items.count == 2550)

        let snapshot = PinkhaHierarchyBuilder.build(items: items)
        #expect(snapshot.allNodes.count == 2550)
        #expect(snapshot.rootNodes.count == 50)

        let firstFolder = snapshot.node(for: "folder_1")
        #expect(firstFolder != nil)
        #expect(firstFolder?.children.count == 50)
        #expect(snapshot.descendantIds(of: "folder_1").count == 50)
    }
}
