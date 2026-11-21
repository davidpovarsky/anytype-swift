import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyGuardedOperationReadTests: XCTestCase {
    private let operationID = String(repeating: "1", count: 32)
    private func operation(object: String = "object", block: String = "", payload: String = "exact-תורה") throws -> AnyTorahOperation {
        try .init(operationID: operationID, spaceID: "space", authorID: "account", kind: .add,
            targetObjectID: object, targetBlockID: block, providerID: "sefaria", canonicalRef: "Genesis.1.1",
            payload: Data(payload.utf8), observed: [])
    }
    private func envelope(_ operations: [AnyTorahOperation], state: String = "liveDocument") throws -> [String: AnyJSON] {
        let variants = try operations.sorted { $0.claimID < $1.claimID }.map { operation -> AnyJSON in
            var row = try XCTUnwrap(operation.fields.object)
            row["id"] = .string(operation.recordID); row["creator"] = .string(operation.authorID)
            row["nativeChangeId"] = .string("native-change"); row["nativeACLHeadId"] = .string("native-acl")
            return .object(["record": .object(row), "canonicalBytes": .string(operation.canonicalBytes.base64EncodedString()),
                            "reachability": .string(state)])
        }
        return ["contract": .string(AnyGuardedTorahCapabilities.contract),
            "readContract": .string(AnyGuardedTorahOperationReadSnapshot.readContract), "version": .integer(1),
            "scope": .string("logical-operation-closure"), "spaceId": .string("space"), "rootObjectId": .string("root"),
            "dataset": .string(AnyGuardedTorahCapabilities.dataset), "operationId": .string(operationID),
            "complete": .bool(true), "outcome": .string(operations.isEmpty ? "absentInVerifiedLocalSnapshot" : "found"),
            "variants": .array(variants), "readiness": .object(["version": .integer(1), "state": .string("ready-local-snapshot"),
                "generation": .string(String(repeating: "a", count: 64))])]
    }
    private func decode(_ fields: [String: AnyJSON]) throws -> AnyGuardedTorahOperationReadSnapshot {
        try .init(response: .object(fields), expectedSpaceID: "space", expectedRootObjectID: "root", expectedOperationID: operationID)
    }
    func testCompleteConflictClosureRetainsBothExactCanonicalVariants() throws {
        let first = try operation(), second = try operation(object: "other", payload: "second")
        let result = try decode(envelope([first, second]))
        XCTAssertEqual(result.variants.map { $0.claim.id }, [first.claimID, second.claimID].sorted())
        XCTAssertEqual(Set(result.variants.map(\.canonicalBytes)), Set([first.canonicalBytes, second.canonicalBytes]))
        XCTAssertTrue(result.variants.allSatisfy { $0.provenance.creator == "account" && $0.provenance.aclHeadID == "native-acl" })
    }
    func testMissingBlockStatePreservesHistoryWithoutClaimingWholeObjectDeletion() throws {
        let op = try operation(block: "unreachable")
        let value = try decode(envelope([op], state: "unreachableBlock"))
        XCTAssertEqual(value.variants.first?.reachability, .unreachableBlock)
        XCTAssertEqual(value.variants.first?.canonicalBytes, op.canonicalBytes)
        for state in ["deleted", "missingObject", "unknown", "liveDocument"] {
            XCTAssertThrowsError(try decode(envelope([op], state: state)))
        }
    }
    func testTamperedCanonicalBytesIdentityAndProvenanceAreRejected() throws {
        let original = try envelope([operation()])
        for key in ["canonicalBytes", "id", "creator", "nativeChangeId", "nativeACLHeadId", "operationId"] {
            var fields = original
            var variant = try XCTUnwrap(fields["variants"]?.array?.first?.object)
            if key == "canonicalBytes" { variant[key] = .string(Data("forged".utf8).base64EncodedString()) } else {
                var row = try XCTUnwrap(variant["record"]?.object); row[key] = .string(""); variant["record"] = .object(row)
            }
            fields["variants"] = .array([.object(variant)])
            XCTAssertThrowsError(try decode(fields), key)
        }
    }
    func testAbsenceAndScopeAlwaysRequireAnExactCompleteNativeEnvelope() throws {
        let empty = try envelope([]); XCTAssertTrue(try decode(empty).absentInVerifiedLocalSnapshot)
        for (key, value) in [("complete", AnyJSON.bool(false)), ("outcome", .string("found")),
                             ("readContract", .string("other")), ("scope", .string("workspace")),
                             ("spaceId", .string("foreign")), ("rootObjectId", .string("other")),
                             ("readiness", .null)] {
            var changed = empty; changed[key] = value; XCTAssertThrowsError(try decode(changed), key)
        }
    }
    func testDuplicateUnsortedAndOversizedFullEnvelopesAreRejected() throws {
        var fields = try envelope([operation(), operation(object: "other")])
        let values = try XCTUnwrap(fields["variants"]?.array)
        fields["variants"] = .array(Array(values.reversed())); XCTAssertThrowsError(try decode(fields))
        fields["variants"] = .array([values[0], values[0]]); XCTAssertThrowsError(try decode(fields))
        fields = try envelope([])
        fields["unrecognizedTransportPadding"] = .string(String(repeating: "x", count: AnyGuardedTorahOperationReadSnapshot.maximumBytes))
        XCTAssertThrowsError(try decode(fields)) { XCTAssertEqual($0 as? AnyEngineError, .readLimit) }
    }
    func testRetainedRuntimeAndIncompleteCapabilityNeverActivateNewRead() throws {
        var fields: [String: AnyJSON] = [
            "contract": .string(AnyGuardedTorahCapabilities.contract), "bundleId": .string(AnyGuardedTorahCapabilities.bundleID),
            "module": .string(AnyGuardedTorahCapabilities.module), "dataset": .string(AnyGuardedTorahCapabilities.dataset),
            "dataVersion": .string(AnyGuardedTorahCapabilities.dataVersion), "allowedTargetTypes": .array([.string("page")]),
            "associationBlockDataset": .string("editor_blocks"), "nativeSemanticPayload": .string("canonical-associations-v2-single-record"),
            "nativeSignedClaims": .integer(1), "spaceWideOperationConflictDomain": .integer(1),
            "currentACLCommitFence": .integer(1), "targetTreeCommitFence": .integer(1),
            "nativeClaimsSnapshot": .integer(1), "nativeClaimsWatch": .integer(1),
            "nativeClaimsMaxRecords": .integer(10000), "nativeClaimsMaxBytes": .integer(16 * 1024 * 1024)]
        XCTAssertFalse(try AnyGuardedTorahCapabilities(response: .object(fields)).nativeAuthorizedOperationRead)
        fields["nativeAuthorizedOperationRead"] = .integer(1)
        XCTAssertFalse(try AnyGuardedTorahCapabilities(response: .object(fields)).nativeAuthorizedOperationRead)
        fields["authorizedOperationReadContract"] = .string(AnyGuardedTorahOperationReadSnapshot.readContract)
        fields["authorizedOperationReadMaxVariants"] = .integer(256)
        fields["authorizedOperationReadMaxBytes"] = .integer(4 * 1024 * 1024)
        XCTAssertTrue(try AnyGuardedTorahCapabilities(response: .object(fields)).nativeAuthorizedOperationRead)
        fields["authorizedOperationReadMaxBytes"] = .integer(4 * 1024 * 1024 + 1)
        XCTAssertFalse(try AnyGuardedTorahCapabilities(response: .object(fields)).nativeAuthorizedOperationRead)
    }
}
