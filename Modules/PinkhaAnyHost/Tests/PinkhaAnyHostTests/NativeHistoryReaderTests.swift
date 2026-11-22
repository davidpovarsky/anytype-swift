import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaKit
@testable import PinkhaAnyHost

final class NativeHistoryReaderTests: XCTestCase, @unchecked Sendable {
    func testReaderKeepsNativeOrderOpaqueFieldsAndReaderAuthority() async throws {
        let workspace = try workspace(), lease = lease(workspace)
        let response = page([change("later-causal", time: -1), change("earlier-causal", time: Int64.max)], cursor: "opaque+/cursor==")
        let wire = HistoryWire(workspace: workspace, response: response)
        let reader = reader(workspace, wire)
        let value = try await reader.page(lease: lease)
        XCTAssertEqual(value.changes.map(\.version), ["later-causal", "earlier-causal"])
        XCTAssertEqual(value.native, response)
        XCTAssertEqual(value.changes[1].native["unknown"]?["large"]?.integer, Int64.max)
        XCTAssertEqual(value.next?.workspace, workspace)
        XCTAssertEqual(value.next?.generation, lease.generation)
        XCTAssertEqual(value.next?.engineStartedAt, lease.engineStartedAt)
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.authority, 2)
        XCTAssertEqual(calls.requests.count, 1)
        XCTAssertEqual(calls.requests[0].path, ["v1", "spaces", "space", "objects", "object", "history"])
        XCTAssertEqual(calls.requests[0].query, ["limit": "50", "coalesce": "false"])
        XCTAssertEqual(calls.requests[0].limit, 1_048_576)
    }

    func testDenialBeforeAndAfterReadNeverReturnsPayload() async throws {
        for (mode, expectedRequests) in [(HistoryWire.Mode.denyBefore, 0), (.denyAfter, 1)] {
            let workspace = try workspace()
            let wire = HistoryWire(workspace: workspace, response: page([change("private")]), mode: mode)
            do {
                _ = try await reader(workspace, wire).page(lease: lease(workspace))
                XCTFail("Current-reader denial returned historical content")
            } catch { XCTAssertEqual(error as? AnyNativeHistoryError, .authorityUnavailable) }
            let calls = await wire.snapshot()
            XCTAssertEqual(calls.requests.count, expectedRequests)
        }
    }

    func testNativeDocumentGenerationChangeRejectsHistoricalReply() async throws {
        let workspace = try workspace()
        let wire = HistoryWire(workspace: workspace, response: page([change("private")]), mode: .changeAfter)
        do {
            _ = try await reader(workspace, wire).page(lease: lease(workspace))
            XCTFail("Changed native document dependencies returned history")
        } catch { XCTAssertEqual(error as? AnyNativeDocumentPolicyError, .dependenciesChanged) }
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.requests.count, 1)
        XCTAssertEqual(calls.authority, 2)
    }

    func testCursorCannotCrossObjectAccountSpaceGenerationOrRun() async throws {
        let workspace = try workspace(), lease = lease(workspace)
        let wire = HistoryWire(workspace: workspace, response: page([]))
        let contexts: [AnyNativeHistoryCursor] = [
            .init(workspace: try self.workspace(account: "other"), objectID: "object", generation: lease.generation, engineStartedAt: lease.engineStartedAt, value: "opaque"),
            .init(workspace: try self.workspace(space: "other"), objectID: "object", generation: lease.generation, engineStartedAt: lease.engineStartedAt, value: "opaque"),
            .init(workspace: workspace, objectID: "other", generation: lease.generation, engineStartedAt: lease.engineStartedAt, value: "opaque"),
            .init(workspace: workspace, objectID: "object", generation: UUID(), engineStartedAt: lease.engineStartedAt, value: "opaque"),
            .init(workspace: workspace, objectID: "object", generation: lease.generation, engineStartedAt: "old-run", value: "opaque")
        ]
        for cursor in contexts {
            do {
                _ = try await reader(workspace, wire).page(after: cursor, lease: lease)
                XCTFail("Foreign continuation was accepted")
            } catch { XCTAssertEqual(error as? AnyHostError, .wrongWorkspace) }
        }
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.requests.count, 0)
        XCTAssertEqual(calls.authority, 0)
    }

    func testDuplicateAndStalledPagesAreExplicitFailures() throws {
        let workspace = try workspace(), lease = lease(workspace)
        let previous = AnyNativeHistoryCursor(workspace: workspace, objectID: "object", generation: lease.generation,
                                              engineStartedAt: lease.engineStartedAt, value: "same")
        for response in [page([change("v"), change("v")]), page([], cursor: "more"), page([change("v")], cursor: "same")] {
            XCTAssertThrowsError(try AnyNativeHistoryPage(response: response, workspace: workspace, objectID: "object",
                                                         lease: lease, previous: previous)) {
                XCTAssertEqual($0 as? AnyNativeHistoryError, .paginationChanged)
            }
        }
    }

    func testVersionKeepsUnknownDatasetsBlockTypesAndIntegerValues() async throws {
        let workspace = try workspace()
        let opaque: AnyJSON = .object(["id": .string("native-opaque"), "large": .integer(Int64.max),
                                      "future": .object(["nested": .array([.null, .bool(true)])])])
        let block: AnyJSON = .object(["id": .string("block"), "type": .string("future_widget"), "text": .string("native text"),
            "nav": .object(["parentId": .string(""), "pos": .string("a")]),
            "style": .object(["future": opaque]), "_ver": .object(["text": .string("native-stamp")])])
        let response: AnyJSON = .object(["version": .string("v"), "futureEnvelope": opaque, "datasets": .array([
            .object(["dataset": .string("editor_blocks"), "records": .array([block])]),
            .object(["dataset": .string("future_dataset"), "records": .array([opaque]), "extra": .bool(true)])])])
        let wire = HistoryWire(workspace: workspace, response: response)
        let value = try await reader(workspace, wire).version("v", lease: lease(workspace))
        XCTAssertEqual(value.native, response)
        XCTAssertEqual(value.datasets[1].records, [opaque])
        XCTAssertEqual(value.editor?.blocks.first?.native, block)
        XCTAssertEqual(value.editor?.blocks.first?.type, "future_widget")
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.requests[0].path.last, "v")
        XCTAssertTrue(calls.requests[0].query.isEmpty)
        XCTAssertEqual(calls.requests[0].limit, 4 * 1024 * 1024)
    }

    func testMissingTruncatedOversizeAndPermissionRemainDistinct() async throws {
        let workspace = try workspace()
        let cases: [(AnyEngineError, AnyNativeHistoryError?)] = [
            (.http(status: 404, code: "history.version_not_found"), .versionNotFound),
            (.http(status: 404, code: "history.truncated"), .truncated),
            (.http(status: 413, code: "history.view_too_large"), .viewTooLarge),
            (.readLimit, .viewTooLarge), (.http(status: 404, code: "route.not_found"), .unavailable),
            (.http(status: 403, code: "permission.denied"), nil), (.http(status: 500, code: "unknown"), nil)
        ]
        for (failure, expected) in cases {
            let wire = HistoryWire(workspace: workspace, response: page([]), failure: failure)
            do {
                _ = try await reader(workspace, wire).version("v", lease: lease(workspace))
                XCTFail("Error became an empty successful version")
            } catch {
                if let expected { XCTAssertEqual(error as? AnyNativeHistoryError, expected) }
                else { XCTAssertEqual(error as? AnyEngineError, failure) }
            }
        }
    }

    func testVersionAndRecordBoundsDoNotPretendDataIsEmpty() throws {
        let workspace = try workspace()
        let row: AnyJSON = .object(["id": .string("r")])
        let tooMany: AnyJSON = .object(["version": .string("v"), "datasets": .array([
            .object(["dataset": .string("unknown"), "records": .array(Array(repeating: row, count: 10_001))])])])
        XCTAssertThrowsError(try AnyNativeHistoryVersion(response: tooMany, requestedVersion: "v", workspace: workspace, objectID: "object")) {
            XCTAssertEqual($0 as? AnyNativeHistoryError, .viewTooLarge)
        }
        XCTAssertThrowsError(try AnyNativeHistoryVersion(response: .object(["version": .string("other"), "datasets": .array([])]),
                                                         requestedVersion: "v", workspace: workspace, objectID: "object")) {
            XCTAssertEqual($0 as? AnyNativeHistoryError, .malformedResponse)
        }
    }

    func testRevokedSessionDoesNotDeliverAReplyThatIgnoresCancellation() async throws {
        let workspace = try workspace(), gate = HistoryReplyGate()
        let session = AnyApplicationSession(workspace: workspace, engineStartedAt: "run", verifyRun: { "run" })
        let proof = try historyProof(workspace)
        let reader = AnyNativeHistoryReader(workspace: workspace, objectID: "object",
            request: { _, _, _ in await gate.wait(); return .object(["changes": .array([])]) },
            authority: { proof })
        let read = Task { try await session.perform { try await reader.page(lease: $0) } }
        await gate.waitUntilEntered()
        let closing = Task { await session.revokeAndDrain() }
        while await session.isActive { await Task.yield() }
        await gate.release()
        do { _ = try await read.value; XCTFail("Revoked session delivered a stale reply") }
        catch { XCTAssertTrue(error is CancellationError || error as? AnyHostError == .sessionClosed) }
        await closing.value
    }

    private func workspace(account: String = "account", space: String = "space") throws -> AnyTorahWorkspace {
        try .init(accountID: account, spaceID: space)
    }
    private func lease(_ workspace: AnyTorahWorkspace) -> AnyHostLease {
        .init(workspace: workspace, generation: UUID(), engineStartedAt: "run", check: {})
    }
    private func reader(_ workspace: AnyTorahWorkspace, _ wire: HistoryWire) -> AnyNativeHistoryReader {
        .init(workspace: workspace, objectID: "object", request: { try await wire.request($0, $1, $2) },
              authority: { try await wire.authority() })
    }
    private func change(_ id: String, time: Int64 = 1) -> AnyJSON {
        .object(["version": .string(id), "author": .string("author"), "timestamp": .integer(time),
                 "dataset": .string("editor_blocks"), "groupSize": .integer(1),
                 "unknown": .object(["large": .integer(Int64.max)])])
    }
    private func page(_ changes: [AnyJSON], cursor: String = "") -> AnyJSON {
        .object(["changes": .array(changes), "cursor": .string(cursor)])
    }
}

private func historyProof(_ workspace: AnyTorahWorkspace, generation: String = String(repeating: "a", count: 64)) throws -> AnyNativeDocumentTargetProof {
    try .init(response: .object([
        "contract": .string("pinkha-torah-native-v1"), "version": .integer(1),
        "policy": .string("canonical-editor-module-v1"), "spaceId": .string(workspace.spaceID),
        "objectId": .string("object"), "typeId": .string("document"), "eligible": .bool(true),
        "canonicalEditorDataset": .string("editor_blocks"), "collections": .array([]), "canWrite": .bool(false),
        "readiness": .object(["version": .integer(1), "state": .string("ready-local-snapshot"), "generation": .string(generation)])
    ]), workspace: workspace, objectID: "object", intent: .read)
}

private actor HistoryWire {
    enum Mode: Sendable, Equatable { case stable, denyBefore, denyAfter, changeAfter }
    struct Request: Sendable { let path: [String]; let query: [String: String]; let limit: Int }
    let workspace: AnyTorahWorkspace, response: AnyJSON, mode: Mode, failure: AnyEngineError?
    var requests: [Request] = [], authorityCount = 0
    init(workspace: AnyTorahWorkspace, response: AnyJSON, mode: Mode = .stable, failure: AnyEngineError? = nil) {
        self.workspace = workspace; self.response = response; self.mode = mode; self.failure = failure
    }
    func request(_ path: [String], _ query: [String: String], _ limit: Int) throws -> AnyJSON {
        requests.append(.init(path: path, query: query, limit: limit))
        if let failure { throw failure }
        return response
    }
    func authority() throws -> AnyNativeDocumentTargetProof {
        authorityCount += 1
        if mode == .denyBefore || (mode == .denyAfter && authorityCount > 1) {
            throw TorahAssociationRepositoryError.permissionDenied
        }
        return try historyProof(workspace, generation: String(repeating: mode == .changeAfter && authorityCount > 1 ? "b" : "a", count: 64))
    }
    func snapshot() -> (requests: [Request], authority: Int) { (requests, authorityCount) }
}

private actor HistoryReplyGate {
    private var entered = false, reply: CheckedContinuation<Void, Never>?, enteredWaiter: CheckedContinuation<Void, Never>?
    func wait() async {
        entered = true; enteredWaiter?.resume(); enteredWaiter = nil
        await withCheckedContinuation { reply = $0 }
    }
    func waitUntilEntered() async {
        if entered { return }
        await withCheckedContinuation { enteredWaiter = $0 }
    }
    func release() { reply?.resume(); reply = nil }
}
