import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyUI

@Suite("Native hierarchy display reconciles only across a fresh feed")
struct AnyHierarchyPresentationStateTests {
    private let workspace = try! AnyTorahWorkspace(accountID: "account", spaceID: "space")
    private let schema = try! AnyHierarchySchema(collectionID: "wiki", parentPropertyID: "parent",
                                                positionPropertyID: "pos", folderPropertyID: "folder")
    private func row(_ id: String = "doc", title: String = "Old", parent: String = "folder",
                     position: String = "PPPP", folder: Bool = false) -> AnyJSON {
        .object(["id": .string(id), "spaceId": .string("space"),
            "_ver": .object(["wiki": .object(["pos": .string("original-version")])]),
            "any": .object(["type": .string("page"), "name": .string(title),
                           "collections": .array([.string("wiki")])]),
            "wiki": .object(["parent": .string(parent), "pos": .string(position), "folder": .bool(folder)]),
            "future": .object(["keep": .string("unchanged")])])
    }
    private func snapshot(_ rows: [AnyJSON]) throws -> AnyHierarchySnapshot {
        try .init(workspace: workspace, schema: schema, rows: rows, allowedTypeIDs: ["page"])
    }

    @Test func oldQueuedFramesCannotEraseConfirmedRenameOrOverrideNewNativeTruth() throws {
        var state = AnyHierarchyPresentationState(workspace: workspace)
        let oldFeed = state.feed
        try state.receive(snapshot([row()]), feed: oldFeed)
        try state.rename(objectID: "doc", title: "Saved")
        state.settleAfterFeedReplacement("doc")
        // Even a value-equal old feed cannot provide the post-write read barrier.
        try state.receive(snapshot([row(title: "Saved")]), feed: oldFeed)
        #expect(state.hasPending("doc"))
        let fresh = state.beginFeed()
        try state.receive(snapshot([row(title: "Saved")]), feed: fresh)
        #expect(!state.hasPending("doc"))
        #expect(try !state.receive(snapshot([row()]), feed: oldFeed))
        #expect(state.itemsByID["doc"]?.title == "Saved")
        try state.receive(snapshot([row(title: "Later remote edit")]), feed: fresh)
        #expect(state.itemsByID["doc"]?.title == "Later remote edit")
    }

    @Test func moveToRootUsesNativeLexicalPositionWithoutCounterfeitingVersion() throws {
        var state = AnyHierarchyPresentationState(workspace: workspace)
        let original = row()
        try state.receive(snapshot([original]), feed: state.feed)
        let plan = try AnyHierarchyPlacementPlan(workspace: workspace, schema: schema, objectID: "doc",
            previousParentID: "folder", previousPosition: "PPPP", expectedVersion: original["_ver"]!,
            parentID: nil, position: "PPQY")
        try state.place(plan)
        #expect(state.children(of: nil).map(\.id) == ["doc"])
        #expect(state.itemsByID["doc"]?.position == "PPQY")
        #expect(state.itemsByID["doc"]?.native.parentID == "folder")
        #expect(state.snapshot?.nativeRows["doc"] == original)
        #expect(state.snapshot?.nativeRows["doc"]?["future"] == .object(["keep": .string("unchanged")]))
    }

    @Test func temporarilyMissingPendingRowIsRetainedUntilPostDispatchFreshRead() throws {
        var state = AnyHierarchyPresentationState(workspace: workspace)
        try state.receive(snapshot([row()]), feed: state.feed)
        try state.rename(objectID: "doc", title: "Local draft")
        try state.receive(snapshot([]), feed: state.feed)
        #expect(state.itemsByID["doc"]?.title == "Local draft")
        state.settleAfterFeedReplacement("doc")
        let fresh = state.beginFeed()
        try state.receive(snapshot([]), feed: fresh)
        #expect(state.items.isEmpty)
    }

    @Test func unrelatedRefreshDoesNotSettleStillRunningMutation() throws {
        var state = AnyHierarchyPresentationState(workspace: workspace)
        try state.receive(snapshot([row()]), feed: state.feed)
        try state.rename(objectID: "doc", title: "Pending")
        let refresh = state.beginFeed()
        try state.receive(snapshot([row(title: "Remote")]), feed: refresh)
        #expect(state.hasPending("doc"))
        #expect(state.itemsByID["doc"]?.title == "Pending")
        state.settleAfterFeedReplacement("doc")
        let postDispatch = state.beginFeed()
        try state.receive(snapshot([row(title: "Current native")]), feed: postDispatch)
        #expect(state.itemsByID["doc"]?.title == "Current native")
    }

    @Test func workspaceAndVerifiedSchemaAreRequiredForCurrentFeed() throws {
        var state = AnyHierarchyPresentationState(workspace: workspace)
        let old = state.feed
        try state.receive(snapshot([row()]), feed: old)
        let otherWorkspace = try AnyTorahWorkspace(accountID: "other", spaceID: "space")
        let foreign = try AnyHierarchySnapshot(workspace: otherWorkspace, schema: schema,
                                               rows: [row()], allowedTypeIDs: ["page"])
        #expect(throws: AnyEngineError.self) { try state.receive(foreign, feed: old) }
        let otherSchema = try AnyHierarchySchema(collectionID: "another", parentPropertyID: "p",
                                                 positionPropertyID: "o", folderPropertyID: "f")
        let changed = try AnyHierarchySnapshot(workspace: workspace, schema: otherSchema,
                                              rows: [], allowedTypeIDs: ["page"])
        #expect(throws: AnyHierarchyError.incompatibleSchema) { try state.receive(changed, feed: old) }
        _ = state.beginFeed()
        #expect(try !state.receive(foreign, feed: old))
    }
}
