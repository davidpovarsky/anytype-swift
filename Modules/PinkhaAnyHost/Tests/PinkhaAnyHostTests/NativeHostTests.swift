import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativeSnapshotTests: XCTestCase {
    func block(_ id: String, parent: String = "", pos: String = "A", text: String? = "שלום",
               type: String = "paragraph", version: String = "v1", style: AnyJSON? = nil) -> AnyJSON {
        var value: [String: AnyJSON] = [
            "id": .string(id), "type": .string(type),
            "nav": .object(["parentId": .string(parent), "pos": .string(pos)]),
            "_ver": .object(["id": .string("create-" + id), "text": .string(version)])
        ]
        if let text { value["text"] = .string(text) }
        if let style { value["style"] = style }
        return .object(value)
    }
    func response(_ blocks: [AnyJSON], total: Int? = nil, more: Bool = false) -> AnyJSON {
        .object(["records": .array(blocks), "total": .integer(Int64(total ?? blocks.count)), "hasNext": .bool(more)])
    }
    func snapshot(_ blocks: [AnyJSON], dataset: String = "editor_blocks") throws -> AnyEditorSnapshot {
        try .init(spaceID: "space", objectID: "object", title: "כותרת", response: response(blocks), dataset: dataset)
    }

    func testTreeOrderUsesParentsThenStablePositionsAndIDs() throws {
        let result = try snapshot([block("z", pos: "B"), block("child", parent: "a"),
                                   block("b", pos: "A"), block("a", pos: "A")])
        XCTAssertEqual(result.depthFirstIDs, ["a", "child", "b", "z"])
    }
    func testOpaqueStyleAndExplicitRTLRemainInNativeBlock() throws {
        let style: AnyJSON = .object(["future": .object(["untouched": .bool(true)]),
            "pinkhaWritingDirection": .string("rightToLeft"), "pinkhaTextAlignment": .string("right")])
        let result = try snapshot([block("a", style: style)])
        XCTAssertEqual(result.blocks[0].native["style"], style)
        XCTAssertEqual(result.blocks[0].direction, .rightToLeft)
        XCTAssertEqual(result.blocks[0].alignment, .right)
    }
    func testEmptyNativeParagraphMayOmitText() throws {
        let result = try snapshot([block("a", text: nil)])
        XCTAssertEqual(result.blocks[0].text, "")
        XCTAssertEqual(try result.boundedText().blocks[0].inlineMarkdown, "")
    }
    func testUnreachableOrphanIsPreservedButNotExportedAsCompleteText() throws {
        let result = try snapshot([block("a"), block("orphan", parent: "deleted")])
        XCTAssertEqual(result.blocks.count, 2)
        XCTAssertEqual(result.unreachableIDs, ["orphan"])
        XCTAssertThrowsError(try result.boundedText()) { XCTAssertEqual($0 as? AnyHostError, .incompleteDocument) }
    }
    func testReachableEditPreservesUnrelatedOrphanAndRefusesOrphanTarget() throws {
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account")
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let store = try AnyEditorDocumentStore(client: client, workspace: workspace, allowedTypeIDs: ["page"])
        let orphan = block("orphan", parent: "deleted", text: "recoverable", version: "orphan-v1",
                           style: .object(["future": .bool(true)]))
        let source = try snapshot([block("live"), orphan])
        let read = AnyEditorRead(snapshot: source, markdown: "", nativeVersion: "whole-native-revision",
                                 engineStartedAt: "run1", generation: UUID())
        let edit = try store.prepareTextEdit(read, blockID: "live", inlineMarkdown: "edited")
        XCTAssertEqual(edit.blockID, "live")
        XCTAssertEqual(edit.expectedVersion, "whole-native-revision")
        XCTAssertEqual(edit.set, ["text": .string("edited")])
        XCTAssertEqual(source.blocks.first(where: { $0.id == "orphan" })?.native, orphan)
        XCTAssertThrowsError(try store.prepareTextEdit(read, blockID: "orphan", inlineMarkdown: "lost")) {
            XCTAssertEqual($0 as? AnyHostError, .invalidSelection)
        }
        let changed = try snapshot([block("live"), block("orphan", parent: "deleted", version: "orphan-v2")])
        XCTAssertNotEqual(source.revision, changed.revision)
        XCTAssertThrowsError(try source.boundedText())
    }
    func testCycleIsRetainedForRecoveryAndCannotReachTextExporter() throws {
        let result = try snapshot([block("a", parent: "b"), block("b", parent: "a")])
        XCTAssertEqual(result.unreachableIDs, ["a", "b"])
        XCTAssertThrowsError(try result.boundedText())
    }
    func testDuplicateBlockIdentityIsRejected() {
        XCTAssertThrowsError(try snapshot([block("a"), block("a")]))
    }
    func testTruncatedQueryCannotBecomeCompleteSnapshot() {
        XCTAssertThrowsError(try AnyEditorSnapshot(spaceID: "s", objectID: "o", title: "",
            response: response([block("a")], total: 2, more: true)))
    }
    func testTextProjectionLabelsMarkdownAndPreservesSelectedIDs() throws {
        let result = try snapshot([block("a", text: "**שלום**"), block("b", pos: "B", text: "second")])
        let text = try result.boundedText(selection: ["a"])
        XCTAssertEqual(text.blocks.map(\.reference), ["a"])
        XCTAssertEqual(text.blocks[0].inlineMarkdown, "**שלום**")
        XCTAssertEqual(text.coverage, "selectedTextBlocksInlineMarkdownOnly")
    }
    func testMissingDuplicateAndNonTextSelectionsAreRefused() throws {
        let result = try snapshot([block("a"), block("image", pos: "B", text: nil, type: "image")])
        XCTAssertThrowsError(try result.boundedText(selection: ["missing"]))
        XCTAssertThrowsError(try result.boundedText(selection: ["a", "a"]))
        XCTAssertThrowsError(try result.boundedText(selection: ["image"]))
    }
    func testUTF8ByteBudgetDoesNotTreatHebrewAsSingleByte() throws {
        let result = try snapshot([block("a", text: "שלום")])
        XCTAssertThrowsError(try result.boundedText(maximumBytes: 7))
        XCTAssertEqual(try result.boundedText(maximumBytes: 8).blocks.count, 1)
    }
    func testNativeStyleVersionChangesRevisionEvenWithSameText() throws {
        let a = try snapshot([block("a", version: "v1")])
        let b = try snapshot([block("a", version: "v2")])
        XCTAssertNotEqual(a.revision, b.revision)
    }
    func testSourceRevisionIncludesDataset() throws {
        let a = try snapshot([block("a")])
        let b = try snapshot([block("a")], dataset: "other_editor")
        XCTAssertNotEqual(a.revision, b.revision)
    }
    func testSourceRevisionIndependentOfQueryRowOrder() throws {
        let a = try snapshot([block("a"), block("b", pos: "B")])
        let b = try snapshot([block("b", pos: "B"), block("a")])
        XCTAssertEqual(a.revision, b.revision)
    }
    func testPrepareEditPreservesUneditedStyleAndCapturesExactInverse() throws {
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account")
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let store = try AnyEditorDocumentStore(client: client, workspace: workspace, allowedTypeIDs: ["page"])
        let source = try snapshot([block("a", style: .object(["future": .bool(true)]))])
        let read = AnyEditorRead(snapshot: source, markdown: "שלום", nativeVersion: "v1",
                                 engineStartedAt: "run1", generation: UUID())
        let edit = try store.prepareWritingStyle(read, blockID: "a", direction: .rightToLeft, alignment: .right)
        XCTAssertEqual(Set(edit.set.keys), ["style.pinkhaWritingDirection", "style.pinkhaTextAlignment", "style.pinkhaAlignmentWasExplicit"])
        XCTAssertEqual(edit.set["style.pinkhaAlignmentWasExplicit"], .bool(true))
        XCTAssertTrue(edit.inverseSet.isEmpty)
        XCTAssertEqual(Set(edit.inverseUnset), Set(edit.set.keys))
        XCTAssertNil(edit.set["style"])
    }
    func testOtherDatasetReadCannotPrepareMutationInThisStore() throws {
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account")
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let store = try AnyEditorDocumentStore(client: client, workspace: workspace, allowedTypeIDs: ["page"])
        let read = AnyEditorRead(snapshot: try snapshot([block("a")], dataset: "other"),
            markdown: "", nativeVersion: "v", engineStartedAt: "r", generation: UUID())
        XCTAssertThrowsError(try store.prepareTextEdit(read, blockID: "a", inlineMarkdown: "new"))
    }
}

private actor NativeRunStamp {
    var value = "run1"
    func set(_ next: String) { value = next }
}
private actor TestSignal {
    var open = false
    var waiters: [CheckedContinuation<Void, Never>] = []
    func wait() async {
        if open { return }
        await withCheckedContinuation { waiters.append($0) }
    }
    func signal() {
        open = true
        let pending = waiters; waiters.removeAll()
        for waiter in pending { waiter.resume() }
    }
}

@MainActor
final class NativeSessionTests: XCTestCase {
    private func session(stamp: NativeRunStamp) throws -> AnyApplicationSession {
        try .init(workspace: .init(accountID: "account", spaceID: "space"),
                  engineStartedAt: "run1", verifyRun: { await stamp.value })
    }
    func testLeaseCarriesOneWorkspaceAndGeneration() async throws {
        let owner = try session(stamp: NativeRunStamp())
        let generation = try await owner.perform { lease in
            XCTAssertEqual(lease.workspace.accountID, "account")
            XCTAssertEqual(lease.workspace.spaceID, "space")
            XCTAssertEqual(lease.engineStartedAt, "run1")
            return lease.generation
        }
        XCTAssertEqual(generation, owner.generation)
        await owner.revokeAndDrain()
    }
    func testRestartInvalidatesOpaqueEditorVersionsAndClosesSession() async throws {
        let stamp = NativeRunStamp()
        let owner = try session(stamp: stamp)
        await stamp.set("run2")
        do { _ = try await owner.perform { _ in "must not be delivered" }; XCTFail("restarted engine accepted") }
        catch { XCTAssertEqual(error as? AnyHostError, .engineRestarted) }
        let active = await owner.isActive
        XCTAssertFalse(active)
        await owner.revokeAndDrain()
    }
    func testRevocationCancelsDrainsAndSuppressesLatePayload() async throws {
        let owner = try session(stamp: NativeRunStamp())
        let entered = TestSignal(), ended = TestSignal()
        let pending = Task {
            try await owner.perform { _ in
                await entered.signal()
                do { try await Task.sleep(for: .seconds(10)) } catch {}
                await ended.signal()
                return "sensitive late payload"
            }
        }
        await entered.wait()
        await owner.revokeAndDrain()
        await ended.wait()
        do { _ = try await pending.value; XCTFail("revoked payload delivered") } catch {}
        do { _ = try await owner.perform { _ in true }; XCTFail("closed owner accepted work") }
        catch { XCTAssertEqual(error as? AnyHostError, .sessionClosed) }
    }
    func testFailedOperationDoesNotBlockDrain() async throws {
        let owner = try session(stamp: NativeRunStamp())
        do { _ = try await owner.perform { _ -> Bool in throw AnyHostError.invalidSelection }; XCTFail() } catch {}
        await owner.revokeAndDrain()
        let active = await owner.isActive
        XCTAssertFalse(active)
    }
}

extension NativeSnapshotTests {
    func testNativeNestedStyleVersionTreeSurvivesAndInvalidatesRevision() throws {
        var before = block("a").object!
        before["_ver"] = .object(["id": .string("create"),
            "style": .object(["*": .string("create"), "pinkhaTextAlignment": .string("v1")])])
        var after = before
        after["_ver"] = .object(["style": .object(["pinkhaTextAlignment": .string("v2"), "*": .string("create")]),
                                "id": .string("create")])
        let a = try snapshot([.object(before)]), b = try snapshot([.object(after)])
        XCTAssertNotEqual(a.revision, b.revision)
        XCTAssertEqual(a.blocks[0].native["_ver"], before["_ver"])
    }
    func testNestedVersionMapOrderDoesNotChangeRevision() throws {
        var before = block("a").object!, after = before
        before["_ver"] = .object(["id": .string("v"), "style": .object(["*": .string("v"), "align": .string("w")])])
        after["_ver"] = .object(["style": .object(["align": .string("w"), "*": .string("v")]), "id": .string("v")])
        XCTAssertEqual(try snapshot([.object(before)]).revision, try snapshot([.object(after)]).revision)
    }
    func testMalformedNestedNativeVersionCannotBecomeRevision() {
        var invalid = block("a").object!
        invalid["_ver"] = .object(["style": .object(["align": .integer(4)])])
        XCTAssertThrowsError(try snapshot([.object(invalid)]))
    }
}
