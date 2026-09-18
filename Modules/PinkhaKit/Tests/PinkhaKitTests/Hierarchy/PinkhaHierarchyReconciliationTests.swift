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
}
