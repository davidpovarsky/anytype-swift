import Testing
@testable import PinkhaKit

@Suite("PinkhaHierarchyReconciliationTests")
struct PinkhaHierarchyReconciliationTests {

    private func makeFolder(id: String, title: String, parentId: String? = nil, order: Double = 1000.0) -> PinkhaHierarchyRawItem {
        PinkhaHierarchyRawItem(
            objectId: id,
            typeId: "folder",
            title: title,
            parentId: parentId,
            order: order,
            kind: .folder
        )
    }

    private func makeDoc(id: String, title: String, parentId: String? = nil, order: Double = 1000.0) -> PinkhaHierarchyRawItem {
        PinkhaHierarchyRawItem(
            objectId: id,
            typeId: "chiddush",
            title: title,
            parentId: parentId,
            order: order,
            kind: .writingDocument
        )
    }

    @Test("Exact real-device scenario: Folder created -> stale subscription [] arrives -> Folder remains visible -> subscription [Folder] arrives -> genuine removal [] removes Folder")
    func testRealDeviceStaleSubscriptionReconciliation() {
        let reconciler = PinkhaHierarchyReconciler()

        // 1. Initial subscription is empty
        let initialSnap = reconciler.receiveSubscription(items: [])
        #expect(initialSnap.rootNodes.isEmpty)
        #expect(reconciler.pendingCreatedItems.isEmpty)

        // 2. Folder creation returns Folder A
        let folderA = makeFolder(id: "folder_a", title: "Folder A", order: 1000.0)
        let immediateSnap = reconciler.registerPending(item: folderA)

        // Immediately visible in snapshot!
        #expect(immediateSnap.rootNodes.count == 1)
        #expect(immediateSnap.rootNodes.first?.objectId == "folder_a")
        #expect(reconciler.pendingCreatedItems["folder_a"] != nil)

        // 3. Stale subscription arrives: [] (Heart/search index hasn't indexed Folder A yet)
        let staleSnap = reconciler.receiveSubscription(items: [])

        // Folder A MUST STILL remain visible because it is pending!
        #expect(staleSnap.rootNodes.count == 1)
        #expect(staleSnap.rootNodes.first?.objectId == "folder_a")
        #expect(reconciler.pendingCreatedItems["folder_a"] != nil)

        // 4. Authoritative subscription state arrives: [Folder A]
        let confirmedSnap = reconciler.receiveSubscription(items: [folderA])

        // Folder A appears exactly once
        #expect(confirmedSnap.rootNodes.count == 1)
        #expect(confirmedSnap.rootNodes.first?.objectId == "folder_a")
        // Pending state is cleared!
        #expect(reconciler.pendingCreatedItems.isEmpty)
        #expect(reconciler.confirmedSubscriptionIds.contains("folder_a"))

        // 5. Genuine deletion later: []
        let deletedSnap = reconciler.receiveSubscription(items: [])

        // Now Folder A disappears cleanly
        #expect(deletedSnap.rootNodes.isEmpty)
    }

    @Test("Multiple pending folder creations are preserved across stale subscription updates")
    func testMultiplePendingFolderCreations() {
        let reconciler = PinkhaHierarchyReconciler()
        reconciler.receiveSubscription(items: [])

        let folder1 = makeFolder(id: "f1", title: "Folder 1", order: 1000.0)
        let folder2 = makeFolder(id: "f2", title: "Folder 2", order: 2000.0)

        reconciler.registerPending(item: folder1)
        let snap2 = reconciler.registerPending(item: folder2)

        #expect(snap2.rootNodes.count == 2)
        #expect(snap2.rootNodes[0].objectId == "f1")
        #expect(snap2.rootNodes[1].objectId == "f2")

        // Stale subscription with only f1
        let partialSnap = reconciler.receiveSubscription(items: [folder1])
        #expect(partialSnap.rootNodes.count == 2)
        #expect(reconciler.pendingCreatedItems["f1"] == nil) // f1 confirmed
        #expect(reconciler.pendingCreatedItems["f2"] != nil) // f2 still pending

        // Full subscription with f1 and f2
        let fullSnap = reconciler.receiveSubscription(items: [folder1, folder2])
        #expect(fullSnap.rootNodes.count == 2)
        #expect(reconciler.pendingCreatedItems.isEmpty)
    }

    @Test("Writing document optimistic creation and subfolder placement")
    func testWritingDocumentOptimisticCreation() {
        let reconciler = PinkhaHierarchyReconciler()
        let folder = makeFolder(id: "f1", title: "Folder 1", order: 1000.0)
        reconciler.receiveSubscription(items: [folder])

        // Optimistically create document inside folder
        let doc = makeDoc(id: "doc1", title: "Chiddush 1", parentId: "f1", order: 1000.0)
        let snap = reconciler.registerPending(item: doc)

        #expect(snap.rootNodes.count == 1)
        #expect(snap.node(for: "f1")?.children.count == 1)
        #expect(snap.node(for: "f1")?.children.first?.objectId == "doc1")

        // Stale subscription returns only folder
        let staleSnap = reconciler.receiveSubscription(items: [folder])
        #expect(staleSnap.node(for: "f1")?.children.count == 1)
        #expect(staleSnap.node(for: "f1")?.children.first?.objectId == "doc1")
    }

    @Test("Duplicate IDs are strictly deduplicated and never rendered twice")
    func testDuplicateIdsDeduplicated() {
        let reconciler = PinkhaHierarchyReconciler()
        let folder = makeFolder(id: "f1", title: "Folder 1", order: 1000.0)

        // Pending and subscription both present with same ID
        reconciler.registerPending(item: folder)
        let snap = reconciler.receiveSubscription(items: [folder, folder])

        #expect(snap.allNodes.count == 1)
        #expect(snap.rootNodes.count == 1)
    }

    @Test("Optimistic rename, order, and move mutations")
    func testOptimisticMutations() {
        let reconciler = PinkhaHierarchyReconciler()
        let folder1 = makeFolder(id: "f1", title: "Old Title", order: 1000.0)
        let folder2 = makeFolder(id: "f2", title: "Folder 2", order: 2000.0)
        reconciler.receiveSubscription(items: [folder1, folder2])

        // 1. Rename
        let renamedSnap = reconciler.applyOptimisticRename(objectId: "f1", newTitle: "New Title")
        #expect(renamedSnap.node(for: "f1")?.title == "New Title")

        // 2. Order
        let reorderedSnap = reconciler.applyOptimisticOrder(objectId: "f1", newRank: 3000.0)
        #expect(reorderedSnap.rootNodes.last?.objectId == "f1")

        // 3. Move
        let movedSnap = reconciler.applyOptimisticMove(objectId: "f1", newParentId: "f2")
        #expect(movedSnap.rootNodes.count == 1)
        #expect(movedSnap.node(for: "f2")?.children.first?.objectId == "f1")

        // 4. Delete
        let deletedSnap = reconciler.applyOptimisticDelete(objectId: "f1")
        #expect(deletedSnap.node(for: "f1") == nil)
    }

    @Test("A. Rename stale frame: old title in subscription kept as new until confirmed by value")
    func testRenameStaleFramePreservesOptimisticTitleUntilValueConfirmed() {
        let reconciler = PinkhaHierarchyReconciler()
        let oldItem = makeFolder(id: "f1", title: "Old Title")
        reconciler.receiveSubscription(items: [oldItem])
        #expect(reconciler.currentSnapshot.node(for: "f1")?.title == "Old Title")

        // Optimistically rename to "New Title"
        reconciler.applyOptimisticRename(objectId: "f1", newTitle: "New Title")
        #expect(reconciler.currentSnapshot.node(for: "f1")?.title == "New Title")
        #expect(reconciler.optimisticMutations["f1"] == .rename(title: "New Title"))

        // Stale subscription frame arrives still containing old title
        let staleItem = makeFolder(id: "f1", title: "Old Title")
        let staleSnap = reconciler.receiveSubscription(items: [staleItem])

        // VISIBLE state MUST remain "New Title"
        #expect(staleSnap.node(for: "f1")?.title == "New Title")
        // Mutation MUST remain pending
        #expect(reconciler.optimisticMutations["f1"] == .rename(title: "New Title"))

        // Confirmed subscription frame arrives with "New Title"
        let confirmedItem = makeFolder(id: "f1", title: "New Title")
        let confirmedSnap = reconciler.receiveSubscription(items: [confirmedItem])

        // Visible state is "New Title" and mutation is cleared
        #expect(confirmedSnap.node(for: "f1")?.title == "New Title")
        #expect(reconciler.optimisticMutations["f1"] == nil)
    }

    @Test("B. Order stale frame: old order rank in subscription kept as new until confirmed by value")
    func testOrderStaleFramePreservesOptimisticRankUntilValueConfirmed() {
        let reconciler = PinkhaHierarchyReconciler()
        let f1 = makeFolder(id: "f1", title: "Folder 1", order: 1000.0)
        let f2 = makeFolder(id: "f2", title: "Folder 2", order: 2000.0)
        reconciler.receiveSubscription(items: [f1, f2])

        // Optimistically reorder f1 after f2 (rank 3000.0)
        reconciler.applyOptimisticOrder(objectId: "f1", newRank: 3000.0)
        #expect(reconciler.currentSnapshot.rootNodes.last?.objectId == "f1")
        #expect(reconciler.optimisticMutations["f1"] == .order(newRank: 3000.0))

        // Stale frame arrives still reporting rank 1000.0
        let staleF1 = makeFolder(id: "f1", title: "Folder 1", order: 1000.0)
        let staleSnap = reconciler.receiveSubscription(items: [staleF1, f2])

        // Visible state remains 3000.0 (f1 after f2)
        #expect(staleSnap.rootNodes.last?.objectId == "f1")
        #expect(reconciler.optimisticMutations["f1"] == .order(newRank: 3000.0))

        // Confirmed frame arrives with rank 3000.0
        let confirmedF1 = makeFolder(id: "f1", title: "Folder 1", order: 3000.0)
        let confirmedSnap = reconciler.receiveSubscription(items: [confirmedF1, f2])

        #expect(confirmedSnap.rootNodes.last?.objectId == "f1")
        #expect(reconciler.optimisticMutations["f1"] == nil)
    }

    @Test("C. Move stale frame: old parent in subscription kept under destination until confirmed by value")
    func testMoveStaleFramePreservesOptimisticParentAndRankUntilValueConfirmed() {
        let reconciler = PinkhaHierarchyReconciler()
        let folderA = makeFolder(id: "fA", title: "Folder A", order: 1000.0)
        let folderB = makeFolder(id: "fB", title: "Folder B", order: 2000.0)
        let doc = makeDoc(id: "d1", title: "Doc 1", parentId: "fA", order: 1000.0)
        reconciler.receiveSubscription(items: [folderA, folderB, doc])

        #expect(reconciler.currentSnapshot.node(for: "fA")?.children.first?.objectId == "d1")

        // Optimistically move doc to folderB with order 2500.0
        reconciler.applyOptimisticMove(objectId: "d1", newParentId: "fB", newRank: 2500.0)
        #expect(reconciler.currentSnapshot.node(for: "fB")?.children.first?.objectId == "d1")
        #expect(reconciler.currentSnapshot.node(for: "fA")?.children.isEmpty == true)
        #expect(reconciler.optimisticMutations["d1"] == .move(newParentId: "fB", newRank: 2500.0))

        // Stale subscription frame arrives with doc still under folderA
        let staleDoc = makeDoc(id: "d1", title: "Doc 1", parentId: "fA", order: 1000.0)
        let staleSnap = reconciler.receiveSubscription(items: [folderA, folderB, staleDoc])

        // Visible state MUST remain under folderB
        #expect(staleSnap.node(for: "fB")?.children.first?.objectId == "d1")
        #expect(staleSnap.node(for: "fA")?.children.isEmpty == true)
        #expect(reconciler.optimisticMutations["d1"] == .move(newParentId: "fB", newRank: 2500.0))

        // Confirmed subscription frame arrives with parentId = "fB" and order = 2500.0
        let confirmedDoc = makeDoc(id: "d1", title: "Doc 1", parentId: "fB", order: 2500.0)
        let confirmedSnap = reconciler.receiveSubscription(items: [folderA, folderB, confirmedDoc])

        #expect(confirmedSnap.node(for: "fB")?.children.first?.objectId == "d1")
        #expect(reconciler.optimisticMutations["d1"] == nil)
    }

    @Test("D. Delete: optimistic delete remains hidden across stale subscription containing item")
    func testDeleteStaleFrameHidesObjectUntilAbsenceConfirmed() {
        let reconciler = PinkhaHierarchyReconciler()
        let folder = makeFolder(id: "f1", title: "Folder 1")
        reconciler.receiveSubscription(items: [folder])
        #expect(reconciler.currentSnapshot.rootNodes.count == 1)

        // Optimistically delete folder
        reconciler.applyOptimisticDelete(objectId: "f1")
        #expect(reconciler.currentSnapshot.rootNodes.isEmpty)
        #expect(reconciler.optimisticMutations["f1"] == .delete)

        // Stale subscription still contains folder
        let staleSnap = reconciler.receiveSubscription(items: [folder])

        // Folder MUST remain hidden
        #expect(staleSnap.rootNodes.isEmpty)
        // Delete mutation MUST remain pending
        #expect(reconciler.optimisticMutations["f1"] == .delete)

        // Authoritative subscription no longer contains folder
        let confirmedSnap = reconciler.receiveSubscription(items: [])

        // Deletion confirmed and mutation cleared
        #expect(confirmedSnap.rootNodes.isEmpty)
        #expect(reconciler.optimisticMutations["f1"] == nil)
    }

    @Test("E. Pending created writing document: intermediate frame without parent/order preserves pending item")
    func testPendingCreatedWritingDocumentPreservesStateAcrossIntermediateFrame() {
        let reconciler = PinkhaHierarchyReconciler()
        let folderB = makeFolder(id: "fB", title: "Folder B", order: 1000.0)
        reconciler.receiveSubscription(items: [folderB])

        // Pending created item has parent = fB and order = 3000.0
        let pendingDoc = makeDoc(id: "doc1", title: "Chiddush 1", parentId: "fB", order: 3000.0)
        reconciler.registerPending(item: pendingDoc)

        #expect(reconciler.currentSnapshot.node(for: "fB")?.children.first?.objectId == "doc1")
        #expect(reconciler.currentSnapshot.node(for: "fB")?.children.first?.order == 3000.0)
        #expect(reconciler.pendingCreatedItems["doc1"] != nil)

        // Intermediate subscription frame arrives:
        // Backend indexed objectId and type, but parentId and order have not arrived yet (parent=nil, order=nil)
        let intermediateDoc = PinkhaHierarchyRawItem(
            objectId: "doc1",
            typeId: "chiddush",
            title: "Chiddush 1",
            parentId: nil,
            order: nil,
            kind: .writingDocument
        )
        let intermediateSnap = reconciler.receiveSubscription(items: [folderB, intermediateDoc])

        // Pending item MUST remain authoritative! Not downgraded to root or nil order!
        #expect(reconciler.pendingCreatedItems["doc1"] != nil)
        #expect(intermediateSnap.node(for: "fB")?.children.first?.objectId == "doc1")
        #expect(intermediateSnap.node(for: "fB")?.children.first?.order == 3000.0)

        // Later subscription arrives with full custom details: parent = fB, order = 3000.0
        let completeDoc = makeDoc(id: "doc1", title: "Chiddush 1", parentId: "fB", order: 3000.0)
        let completeSnap = reconciler.receiveSubscription(items: [folderB, completeDoc])

        // Pending creation clears cleanly
        #expect(reconciler.pendingCreatedItems["doc1"] == nil)
        #expect(completeSnap.node(for: "fB")?.children.first?.objectId == "doc1")
        #expect(completeSnap.node(for: "fB")?.children.first?.order == 3000.0)
    }
}
