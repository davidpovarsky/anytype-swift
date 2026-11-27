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

#if os(macOS) || os(Linux)
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

/// Actual Host apply/readback through the original HTTP client and target checks.
/// The loopback server is a controlled reply fixture, not native-engine evidence.
@MainActor
final class NativeTextEditReadbackHTTPTests: XCTestCase {
    func testCanonicalEquivalentTextReadbackCannotCertifyWriteOrMintUndo() async throws {
        for (before, requested) in Self.unicodeInputs {
            let result = try await apply(before: before, requested: requested, exactReply: false)
            XCTAssertEqual(result.readback, .nativeAcceptedButCurrentStateUnverified)
            XCTAssertNil(result.undo)
        }
    }

    func testExactUnicodeTextReadbackRetainsVerifiedReceiptAndExactInverse() async throws {
        for (before, requested) in Self.unicodeInputs {
            let result = try await apply(before: before, requested: requested, exactReply: true)
            XCTAssertEqual(result.readback, .verifiedCurrent)
            let undo = try XCTUnwrap(result.undo)
            XCTAssertEqual(undo.expectedVersion, "editor-v2")
            XCTAssertEqual(undo.blockID, "block")
            XCTAssertEqual(Set(undo.set.keys), ["text"])
            XCTAssertTrue(undo.unset.isEmpty)
            let inverse = try XCTUnwrap(undo.set["text"]?.string)
            XCTAssertEqual(Array(inverse.utf8), Array(before.utf8))
            let redo = try XCTUnwrap(undo.inverseSet["text"]?.string)
            XCTAssertEqual(Array(redo.utf8), Array(requested.utf8))
        }
    }

    private static var unicodeInputs: [(String, String)] {
        let marker = "pinkha-anchor://v1/c3BhY2U/b2JqZWN0/00000000-0000-0000-0000-000000000001"
        func source(_ body: String) -> String { "[Before " + body + " after](" + marker + ")" }
        return [
            (source("\u{00e9}"), source("e\u{0301}")),
            (source("\u{05e9}\u{05b8}\u{05c1}"), source("\u{05e9}\u{05c1}\u{05b8}"))
        ]
    }

    private func apply(before: String, requested: String, exactReply: Bool) async throws -> AnyBlockEditReceipt {
        XCTAssertFalse(before.utf8.elementsEqual(requested.utf8))
        XCTAssertEqual(before, requested, "The fixture must exercise canonical equivalence with different raw bytes")
        let reply = exactReply ? requested : before
        let fixture = try TextReadbackHTTPFixture(before: before, requested: requested, reply: reply)
        defer { fixture.stop() }
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let store = try AnyEditorDocumentStore(client: fixture.client(), workspace: workspace, allowedTypeIDs: ["page"])
        let owner = try AnyApplicationSession(workspace: workspace, engineStartedAt: "run1", verifyRun: { "run1" })
        let values: (AnyEditorRead, AnyPreparedBlockEdit, AnyBlockEditReceipt, AnyEditorRead)
        do {
            values = try await owner.perform { lease in
                let initial = try await store.read(objectID: "object", lease: lease)
                let edit = try store.prepareTextEdit(initial, blockID: "block", inlineMarkdown: requested)
                let receipt = try await store.apply(edit, lease: lease)
                let observed = try await store.read(objectID: "object", lease: lease)
                return (initial, edit, receipt, observed)
            }
        } catch {
            await owner.revokeAndDrain()
            throw error
        }
        await owner.revokeAndDrain()
        let originalText = try XCTUnwrap(values.0.snapshot.blocks.first?.text)
        let preparedText = try XCTUnwrap(values.1.set["text"]?.string)
        let observedText = try XCTUnwrap(values.3.snapshot.blocks.first?.text)
        XCTAssertEqual(Array(originalText.utf8), Array(before.utf8))
        XCTAssertEqual(Array(preparedText.utf8), Array(requested.utf8))
        XCTAssertEqual(values.1.expectedVersion, "editor-v1")
        XCTAssertEqual(values.3.nativeVersion, "editor-v2")
        XCTAssertEqual(Array(observedText.utf8), Array(reply.utf8))
        XCTAssertEqual(values.2.nativeVersionID, "native-write-v2")
        let patches = try fixture.rows().filter { $0["method"]?.string == "PATCH" }
        XCTAssertEqual(patches.count, 1, "The real HTTP client must send the raw change exactly once")
        let patch = try XCTUnwrap(patches.first)
        XCTAssertEqual(patch["path"]?.string, "/v1/spaces/space/objects/object/editor/editor_blocks/blocks/block")
        let dispatched = try XCTUnwrap(patch["body"]?["set"]?["text"]?.string)
        XCTAssertEqual(Array(dispatched.utf8), Array(requested.utf8))
        XCTAssertEqual(patch["textUTF8"]?.array?.compactMap(\.integer), requested.utf8.map(Int64.init))
        XCTAssertEqual(patch["body"]?["ifVersion"]?.string, "editor-v1")
        XCTAssertEqual(patch["body"]?["ifStartedAt"]?.string, "run1")
        XCTAssertEqual(patch["body"]?["unset"], .array([]))
        return values.2
    }
}

private enum TextReadbackFixtureFailure: Error { case invalidFixture }

/// Same owned Python/loopback and stdin-EOF pattern as the existing Engine HTTP tests.
/// Each new private directory and every raw reply/dispatch remain available for review.
private final class TextReadbackHTTPFixture: @unchecked Sendable {
    private let directory: URL
    private let process = Process()
    private let control = Pipe()
    private var stderr: FileHandle?
    private var port = 0
    private var stopped = false

    init(before: String, requested: String, reply: String) throws {
        directory = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("pinkha-host-text-readback-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        // A setgid parent can add02000. Normalize only this newly created owned
        // directory, then retain the existing exact mode/owner admission.
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: directory.path)
        let attributes = try FileManager.default.attributesOfItem(atPath: directory.path)
        guard directory.resolvingSymlinksInPath().path == directory.path,
              attributes[.type] as? FileAttributeType == .typeDirectory,
              (attributes[.posixPermissions] as? NSNumber)?.intValue == 0o700,
              (attributes[.ownerAccountID] as? NSNumber)?.uint32Value == geteuid() else {
            throw TextReadbackFixtureFailure.invalidFixture
        }
        let config: AnyJSON = .object(["before": .string(before), "requested": .string(requested), "reply": .string(reply)])
        try JSONEncoder().encode(config).write(to: directory.appendingPathComponent("config.json"))
        let script = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("Fixtures/editor_text_readback_server.py")
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", script.path, directory.path]
        process.standardInput = control
        guard fcntl(control.fileHandleForWriting.fileDescriptor, F_SETFD, FD_CLOEXEC) == 0 else {
            throw TextReadbackFixtureFailure.invalidFixture
        }
        let log = directory.appendingPathComponent("stderr.log")
        guard FileManager.default.createFile(atPath: log.path, contents: nil,
            attributes: [.posixPermissions: 0o600]) else { throw TextReadbackFixtureFailure.invalidFixture }
        stderr = try FileHandle(forWritingTo: log)
        process.standardOutput = FileHandle.nullDevice
        process.standardError = stderr
        print("Host text readback fixture evidence: " + directory.path)
        do {
            try process.run()
            try control.fileHandleForReading.close()
            let deadline = Date().addingTimeInterval(5)
            let ready = directory.appendingPathComponent("port.json")
            while !FileManager.default.fileExists(atPath: ready.path) {
                guard process.isRunning, Date() < deadline else { throw TextReadbackFixtureFailure.invalidFixture }
                Thread.sleep(forTimeInterval: 0.01)
            }
            port = try JSONDecoder().decode(Int.self, from: Data(contentsOf: ready))
            guard (1...65_535).contains(port) else { throw TextReadbackFixtureFailure.invalidFixture }
        } catch { stop(); throw error }
    }

    deinit { try? control.fileHandleForWriting.close() }

    func client() throws -> AnyHTTPClient {
        try .init(baseURL: URL(string: "http://127.0.0.1:\(port)")!, expectedAccountID: "account")
    }

    func rows() throws -> [AnyJSON] {
        try JSONDecoder().decode([AnyJSON].self, from: Data(contentsOf: directory.appendingPathComponent("dispatch.json")))
    }

    func stop(file: StaticString = #filePath, line: UInt = #line) {
        guard !stopped else { return }
        stopped = true
        do { try control.fileHandleForWriting.close() }
        catch { XCTFail("Owned fixture stdin close failed; evidence: " + directory.path, file: file, line: line) }
        let deadline = Date().addingTimeInterval(3)
        while process.isRunning && Date() < deadline { Thread.sleep(forTimeInterval: 0.01) }
        guard process.processIdentifier > 0, !process.isRunning else {
            XCTFail("Owned fixture did not exit after EOF; evidence retained: " + directory.path, file: file, line: line)
            return
        }
        process.waitUntilExit()
        XCTAssertEqual(process.terminationReason, .exit, file: file, line: line)
        XCTAssertEqual(process.terminationStatus, 0, file: file, line: line)
        do {
            try stderr?.synchronize(); try stderr?.close()
            let start = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: directory.appendingPathComponent("fixture-start.json")))
            let end = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: directory.appendingPathComponent("fixture-exit.json")))
            XCTAssertEqual(start["pid"]?.integer, Int64(process.processIdentifier), file: file, line: line)
            XCTAssertEqual(end["pid"]?.integer, Int64(process.processIdentifier), file: file, line: line)
            XCTAssertEqual(end["stopReason"]?.string, "stdin-eof", file: file, line: line)
        } catch { XCTFail("Owned fixture closure evidence unavailable: " + directory.path, file: file, line: line) }
    }
}
#endif
