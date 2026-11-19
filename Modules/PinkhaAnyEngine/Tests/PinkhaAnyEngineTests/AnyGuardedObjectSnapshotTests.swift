import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyGuardedObjectSnapshotTests: XCTestCase {
    private let firstGeneration = String(repeating: "a", count: 64)
    private let nextGeneration = String(repeating: "b", count: 64)

    private func operation(_ id: String, object: String = "object", block: String = "",
                           kind: AnyTorahOperation.Kind = .add, observed: [String] = []) throws -> AnyTorahOperation {
        try .init(operationID: String(repeating: id, count: 32), spaceID: "space", authorID: "account",
            kind: kind, targetObjectID: object, targetBlockID: block,
            providerID: kind == .remove ? "" : "sefaria", canonicalRef: kind == .remove ? "" : "Genesis.1.1",
            payload: kind == .remove ? Data() : Data("opaque-תורה".utf8), observed: observed)
    }
    private func row(_ operation: AnyTorahOperation) throws -> AnyJSON {
        var fields = try XCTUnwrap(operation.fields.object)
        fields["id"] = .string(operation.recordID)
        fields["creator"] = .string(operation.authorID)
        fields["nativeChangeId"] = .string("native-change")
        fields["nativeACLHeadId"] = .string("native-acl")
        return .object(fields)
    }
    private func envelope(_ operations: [AnyTorahOperation], reachable: [String] = [],
                          generation: String? = nil, limit: Int = 10000) throws -> AnyJSON {
        .object([
            "contract": .string(AnyGuardedTorahCapabilities.contract),
            "scope": .string("object-logical-closure"), "version": .integer(1),
            "spaceId": .string("space"), "rootObjectId": .string("native-root"),
            "dataset": .string(AnyGuardedTorahCapabilities.dataset),
            "targetObjectId": .string("object"), "complete": .bool(true), "limit": .integer(Int64(limit)),
            "records": .array(try operations.map(row)),
            "reachableClaimBlockIds": .array(reachable.map(AnyJSON.string)),
            "readiness": .object(["version": .integer(1), "state": .string("ready-local-snapshot"),
                                  "generation": .string(generation ?? firstGeneration)])
        ])
    }
    private func decode(_ value: AnyJSON, limit: Int = 10000) throws -> AnyGuardedTorahObjectSnapshot {
        try .init(response: value, expectedSpaceID: "space", expectedRootObjectID: "native-root",
                  expectedObjectID: "object", limit: limit)
    }
    private func frame(_ value: AnyJSON, generation: String? = nil) throws -> AnySSEFrame {
        .init(event: "snapshot", data: try JSONEncoder().encode(value), id: generation ?? firstGeneration)
    }

    func testForeignCollisionWitnessObservingOmittedForeignPredecessorMatchesWorkspaceFold() throws {
        let seed = try operation("1")
        let foreignPredecessor = try operation("2", object: "foreign")
        let foreignWitness = try operation("1", object: "foreign", kind: .replace,
                                           observed: [foreignPredecessor.claimID])
        let independent = try operation("3", block: "reachable")
        let closure = try decode(envelope([seed, foreignWitness, independent], reachable: ["reachable"]))
        let workspace = try AnyTorahProjection(claims: [seed, foreignWitness, independent, foreignPredecessor]
            .map { try .init(operation: $0, creator: $0.authorID) })
        XCTAssertEqual(closure.projection.live, workspace.live.filter { $0.operation.targetObjectID == "object" })
        XCTAssertEqual(closure.projection.conflicts, workspace.conflicts)
        XCTAssertEqual(closure.projection.pendingObserved, workspace.pendingObserved)
        XCTAssertEqual(closure.projection.all.count, 3)
        XCTAssertEqual(closure.projection.live.map(\.id), [independent.claimID])
        XCTAssertEqual(closure.reachableClaimBlockIDs, ["reachable"])
    }

    func testUnseededForeignRowCannotMasqueradeAsACompleteObjectClosure() throws {
        let seed = try operation("1"), foreign = try operation("2", object: "foreign")
        XCTAssertThrowsError(try decode(envelope([seed, foreign])))
        XCTAssertThrowsError(try decode(envelope([foreign])))
    }

    func testWrongTargetScopeVersionAndMissingReadinessFailClosed() throws {
        let original = try XCTUnwrap(envelope([operation("1")]).object)
        for (key, value) in [
            ("targetObjectId", AnyJSON.string("other")), ("scope", .string("workspace")),
            ("version", .integer(2)), ("complete", .bool(false)),
            ("spaceId", .string("other")), ("rootObjectId", .string("other")),
            ("readiness", .null)
        ] {
            var changed = original; changed[key] = value
            XCTAssertThrowsError(try decode(.object(changed)), key)
        }
    }

    func testReachabilityIsSortedUniqueSubsetOfThisObjectsClaimBlockHistory() throws {
        let first = try operation("1", block: "a"), second = try operation("2", block: "b")
        for invalid in [["a", "a"], ["b", "a"], [""], ["missing"], ["."]] {
            XCTAssertThrowsError(try decode(envelope([first, second], reachable: invalid)))
        }
        let value = try decode(envelope([first, second], reachable: ["a"]))
        XCTAssertEqual(value.reachableClaimBlockIDs, ["a"])
        // Orphan history remains available for conflict/removal semantics.
        XCTAssertEqual(value.projection.all.count, 2)
        XCTAssertEqual(value.projection.live.count, 2)
        var changed = try XCTUnwrap(envelope([first]).object)
        changed["reachableClaimBlockIds"] = .array([.integer(7)])
        XCTAssertThrowsError(try decode(.object(changed)))
    }

    func testEmptyEligibleObjectHasCompleteEmptyClosure() throws {
        let value = try decode(envelope([]))
        XCTAssertEqual(value.targetObjectID, "object")
        XCTAssertTrue(value.projection.all.isEmpty)
        XCTAssertTrue(value.reachableClaimBlockIDs.isEmpty)
    }

    func testObjectClosureCannotSatisfyWholeWorkspaceSnapshotContract() throws {
        let value = try envelope([operation("1")])
        XCTAssertThrowsError(try AnyGuardedTorahSnapshot(response: value, expectedSpaceID: "space",
                                                       expectedRootObjectID: "native-root"))
    }

    func testBoundAppliesToForeignWitnessesAndProvenanceIsStillRequired() throws {
        let seed = try operation("1"), witness = try operation("1", object: "foreign")
        XCTAssertThrowsError(try decode(envelope([seed, witness], limit: 1), limit: 1))
        var value = try XCTUnwrap(envelope([seed]).object)
        var invalidRow = try XCTUnwrap(row(seed).object)
        invalidRow["creator"] = .string("forged")
        value["records"] = .array([.object(invalidRow)])
        XCTAssertThrowsError(try decode(.object(value)))
    }

    func testWatchRequiresNewGenerationForReachabilityChangesAndKeepsHistory() throws {
        let op = try operation("1", block: "a")
        var window = AnyGuardedTorahObjectWatchWindow(spaceID: "space", rootID: "native-root",
                                                     objectID: "object", limit: 10000)
        let first = try XCTUnwrap(window.apply(frame(envelope([op], reachable: ["a"]))))
        XCTAssertTrue(first.initial)
        XCTAssertNil(try window.apply(frame(envelope([op], reachable: ["a"]))))
        XCTAssertThrowsError(try window.apply(frame(envelope([op], reachable: []))))
        let later = try XCTUnwrap(window.apply(frame(
            envelope([op], reachable: [], generation: nextGeneration), generation: nextGeneration)))
        XCTAssertFalse(later.initial)
        XCTAssertTrue(later.snapshot.reachableClaimBlockIDs.isEmpty)
        XCTAssertEqual(later.snapshot.projection.all.map(\.id), [op.claimID])
    }

    func testWatchRefusesLostHistoryWrongEventIDsAndTerminalAuthorityFailure() throws {
        let op = try operation("1")
        var window = AnyGuardedTorahObjectWatchWindow(spaceID: "space", rootID: "native-root",
                                                     objectID: "object", limit: 10000)
        _ = try window.apply(frame(envelope([op])))
        XCTAssertThrowsError(try window.apply(frame(
            envelope([], generation: nextGeneration), generation: nextGeneration)))
        XCTAssertThrowsError(try window.apply(frame(
            envelope([op], generation: nextGeneration), generation: firstGeneration)))
        XCTAssertThrowsError(try window.apply(.init(event: "error", data: Data("{}".utf8), id: nil)))
    }
}
