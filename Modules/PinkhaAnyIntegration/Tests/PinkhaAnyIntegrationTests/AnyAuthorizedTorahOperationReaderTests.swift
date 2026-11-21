import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaKit
@testable import PinkhaAnyIntegration

private actor AuthorizedReadGate {
    private var entered = false
    private var observer: CheckedContinuation<Void, Never>?
    private var continuation: CheckedContinuation<Void, Never>?
    func suspend() async {
        entered = true; observer?.resume(); observer = nil
        await withCheckedContinuation { continuation = $0 }
    }
    func waitUntilEntered() async {
        if entered { return }
        await withCheckedContinuation { observer = $0 }
    }
    func release() { continuation?.resume(); continuation = nil }
}

@MainActor
final class AnyAuthorizedTorahOperationReaderTests: XCTestCase {
    private let operationID = String(repeating: "1", count: 32)
    private func fixture() throws -> AnyGuardedTorahOperationReadSnapshot {
        let op = try AnyTorahOperation(operationID: operationID, spaceID: "space", authorID: "account",
            kind: .add, targetObjectID: "object", targetBlockID: "missing", providerID: "sefaria",
            canonicalRef: "Genesis.1.1", payload: Data([0, 255, 1]), observed: [])
        var row = try XCTUnwrap(op.fields.object)
        row["id"] = .string(op.recordID); row["creator"] = .string(op.authorID)
        row["nativeChangeId"] = .string("native-change"); row["nativeACLHeadId"] = .string("native-acl")
        return try .init(response: .object([
            "contract": .string(AnyGuardedTorahCapabilities.contract),
            "readContract": .string(AnyGuardedTorahOperationReadSnapshot.readContract), "version": .integer(1),
            "scope": .string("logical-operation-closure"), "spaceId": .string("space"), "rootObjectId": .string("root"),
            "dataset": .string(AnyGuardedTorahCapabilities.dataset), "operationId": .string(operationID),
            "complete": .bool(true), "outcome": .string("found"),
            "variants": .array([.object(["record": .object(row), "canonicalBytes": .string(op.canonicalBytes.base64EncodedString()),
                "reachability": .string("unreachableBlock")])]),
            "readiness": .object(["version": .integer(1), "state": .string("ready-local-snapshot"),
                                   "generation": .string(String(repeating: "a", count: 64))])]),
            expectedSpaceID: "space", expectedRootObjectID: "root", expectedOperationID: operationID)
    }
    func testMapsNativeReadToSharedScopeWithoutChangingBytesOrAuthority() async throws {
        let native = try fixture(), session = AnyStreamSession()
        let reader = try await AnyAuthorizedTorahOperationReader(workspace: .init(accountID: "account", spaceID: "space"),
            session: session, load: { _ in native })
        let result = try await reader.readOperation(operationID: operationID)
        XCTAssertEqual(result.scope, reader.scope)
        let generation = await session.generation
        XCTAssertEqual(result.scope.sessionGeneration, generation)
        XCTAssertEqual(result.variants.first?.canonicalBytes, native.variants.first?.canonicalBytes)
        XCTAssertEqual(result.variants.first?.reachability, .unreachableBlock)
        XCTAssertEqual(result.variants.first?.provenance.first?.nativeChangeID, "native-change")
        XCTAssertEqual(result.nativeSnapshotToken, native.readinessGeneration)
    }
    func testInvalidatedOrCancelledInFlightReadCannotReleaseAcquiredPrivatePayload() async throws {
        for invalidate in [true, false] {
            let gate = AuthorizedReadGate(), native = try fixture(), session = AnyStreamSession()
            let reader = try await AnyAuthorizedTorahOperationReader(workspace: .init(accountID: "account", spaceID: "space"),
                session: session, load: { _ in await gate.suspend(); return native })
            let id = operationID
            let task = Task { try await reader.readOperation(operationID: id) }
            await gate.waitUntilEntered()
            if invalidate { await session.invalidate() } else { task.cancel() }
            await gate.release()
            do { _ = try await task.value; XCTFail("stale private payload escaped") }
            catch { XCTAssertTrue(error is CancellationError || error as? TorahOperationReadError == .accountChanged) }
        }
    }
    func testInactiveSessionNeverCallsNativeLoaderAndErrorsHaveNoPayload() async throws {
        let session = AnyStreamSession(); await session.invalidate()
        let reader = try await AnyAuthorizedTorahOperationReader(workspace: .init(accountID: "account", spaceID: "space"),
            session: session, load: { _ in throw TorahOperationReadError.nativeFailure })
        do { _ = try await reader.readOperation(operationID: operationID); XCTFail("inactive session read") }
        catch { XCTAssertEqual(error as? TorahOperationReadError, .accountChanged) }
        for (code, expected) in [("pinkha.history_unavailable", TorahOperationReadError.historyUnavailable),
            ("bundle.not_ready", .historyUnavailable), ("pinkha.target_state_unavailable", .targetStateUnavailable),
            ("pinkha.snapshot_changed", .snapshotChanged), ("pinkha.read_limit", .readLimit)] {
            let active = AnyStreamSession()
            let reader = try await AnyAuthorizedTorahOperationReader(workspace: .init(accountID: "account", spaceID: "space"),
                session: active, load: { _ in throw AnyEngineError.http(status: 409, code: code) })
            do { _ = try await reader.readOperation(operationID: operationID); XCTFail("native failure became success") }
            catch { XCTAssertEqual(error as? TorahOperationReadError, expected) }
        }
    }
}
