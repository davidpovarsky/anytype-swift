import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyGuardedTorahTests: XCTestCase {
    private let root = "native-root"
    private let generation = String(repeating: "a", count: 64)

    private func capabilities() -> [String: AnyJSON] {
        [
            "contract": .string(AnyGuardedTorahCapabilities.contract),
            "bundleId": .string(AnyGuardedTorahCapabilities.bundleID),
            "module": .string(AnyGuardedTorahCapabilities.module),
            "dataset": .string(AnyGuardedTorahCapabilities.dataset),
            "dataVersion": .string(AnyGuardedTorahCapabilities.dataVersion),
            "allowedTargetTypes": .array([.string("page")]),
            "associationBlockDataset": .string("editor_blocks"),
            "nativeSemanticPayload": .string("canonical-associations-v2-single-record"),
            "nativeSignedClaims": .integer(1), "spaceWideOperationConflictDomain": .integer(1),
            "currentACLCommitFence": .integer(1), "targetTreeCommitFence": .integer(1),
            "nativeClaimsSnapshot": .integer(1), "nativeClaimsWatch": .integer(1),
            "nativeClaimsMaxRecords": .integer(10000), "nativeClaimsMaxBytes": .integer(16 * 1024 * 1024),
            "conditionalBlockPatch": .integer(1), "conditionalPropertiesSet": .integer(1),
            "nativeDocumentProperties": .integer(1), "nativeIndexedSourceQuery": .integer(1),
            "nativeRelatedVersion": .integer(1)
        ]
    }

    private func operation(id: String = String(repeating: "1", count: 32), target: String = "object",
                           payload: String = "תורה", kind: AnyTorahOperation.Kind = .add,
                           observed: [String] = []) throws -> AnyTorahOperation {
        try .init(operationID: id, spaceID: "space", authorID: "account", kind: kind,
            targetObjectID: target, providerID: kind == .remove ? "" : "sefaria",
            canonicalRef: kind == .remove ? "" : "Genesis.1.1",
            payload: kind == .remove ? Data() : Data(payload.utf8), observed: observed)
    }
    private func row(_ operation: AnyTorahOperation) throws -> AnyJSON {
        var value = try XCTUnwrap(operation.fields.object)
        value["id"] = .string(operation.recordID)
        value["creator"] = .string(operation.authorID)
        value["nativeChangeId"] = .string("native-change")
        value["nativeACLHeadId"] = .string("native-acl")
        return .object(value)
    }
    private func response(_ rows: [AnyJSON], limit: Int = 10000,
                          generation: String? = nil) -> AnyJSON {
        .object([
            "contract": .string(AnyGuardedTorahCapabilities.contract),
            "spaceId": .string("space"), "rootObjectId": .string(root),
            "dataset": .string(AnyGuardedTorahCapabilities.dataset),
            "complete": .bool(true), "limit": .integer(Int64(limit)),
            "records": .array(rows), "readiness": .object([
                "version": .integer(1), "state": .string("ready-local-snapshot"),
                "generation": .string(generation ?? self.generation)
            ])
        ])
    }
    private func decode(_ response: AnyJSON, limit: Int = 10000) throws -> AnyGuardedTorahSnapshot {
        try .init(response: response, expectedSpaceID: "space", expectedRootObjectID: root, limit: limit)
    }
    private func frame(_ response: AnyJSON, id: String? = nil) throws -> AnySSEFrame {
        .init(event: "snapshot", data: try JSONEncoder().encode(response), id: id ?? generation)
    }

    func testNativeCapabilitiesRequireCompiledContractAndAllAuthorityFlags() throws {
        let result = try AnyGuardedTorahCapabilities(response: .object(capabilities()))
        XCTAssertTrue(result.conditionalBlockPatch)
        XCTAssertTrue(result.conditionalPropertiesSet)
        XCTAssertTrue(result.nativeIndexedSourceQuery)
        for key in ["nativeSignedClaims", "spaceWideOperationConflictDomain", "currentACLCommitFence",
                    "targetTreeCommitFence", "nativeClaimsSnapshot", "nativeClaimsWatch"] {
            for value in [AnyJSON.bool(true), .integer(0), .integer(2), .null] {
                var altered = capabilities(); altered[key] = value
                XCTAssertThrowsError(try AnyGuardedTorahCapabilities(response: .object(altered)), key)
            }
        }
    }
    func testGenericBundleAndUnknownNativeVersionsNeverActivateNativeLane() throws {
        for key in ["contract", "bundleId", "module", "dataset", "dataVersion", "nativeSemanticPayload"] {
            var altered = capabilities(); altered[key] = .string("generic-or-unreviewed")
            XCTAssertThrowsError(try AnyGuardedTorahCapabilities(response: .object(altered)), key)
        }
        var altered = capabilities(); altered["nativeClaimsMaxRecords"] = .integer(9999)
        XCTAssertThrowsError(try AnyGuardedTorahCapabilities(response: .object(altered)))
        altered = capabilities(); altered["allowedTargetTypes"] = .array([.string("other")])
        XCTAssertThrowsError(try AnyGuardedTorahCapabilities(response: .object(altered)))
    }
    func testNativeSnapshotRetainsCanonicalPayloadAndDerivedProvenance() throws {
        let op = try operation()
        let value = try decode(response([row(op)]))
        XCTAssertEqual(value.projection.all.map(\.id), [op.claimID])
        XCTAssertEqual(value.projection.live.first?.operation.payload, op.payload)
        XCTAssertEqual(value.provenance[op.claimID]?.creator, "account")
        XCTAssertEqual(value.provenance[op.claimID]?.changeID, "native-change")
        XCTAssertEqual(value.provenance[op.claimID]?.aclHeadID, "native-acl")
    }
    func testNativeSnapshotRejectsIncompleteWrongScopeAndLegacyRowIDs() throws {
        let record = try row(operation())
        for (key, value) in [
            ("spaceId", AnyJSON.string("other")), ("rootObjectId", .string("other")),
            ("dataset", .string("generic")), ("complete", .bool(false)), ("limit", .integer(9999))
        ] {
            var object = try XCTUnwrap(response([record]).object); object[key] = value
            XCTAssertThrowsError(try decode(.object(object)), key)
        }
        var legacy = try XCTUnwrap(record.object)
        legacy["id"] = .string(root + "/" + (try operation()).recordID)
        XCTAssertThrowsError(try decode(response([.object(legacy)])))
    }
    func testNativeSnapshotRejectsMalformedReadinessAndUnboundedLimits() throws {
        var value = try XCTUnwrap(response([]).object)
        value["readiness"] = .object(["version": .integer(1),
            "state": .string("incomplete"), "generation": .string(generation)])
        XCTAssertThrowsError(try decode(.object(value)))
        XCTAssertThrowsError(try decode(response([], generation: "not-a-native-generation")))
        XCTAssertThrowsError(try decode(response([], limit: 0), limit: 0))
        XCTAssertThrowsError(try decode(response([], limit: 10001), limit: 10001))
    }
    func testNativeSnapshotRejectsDuplicateRowsAndExcessCount() throws {
        let row = try row(operation())
        XCTAssertThrowsError(try decode(response([row, row])))
        let second = try self.row(operation(id: String(repeating: "2", count: 32)))
        XCTAssertThrowsError(try decode(response([row, second], limit: 1), limit: 1))
    }
    func testNativeSnapshotRejectsForgedCreatorAndAbsentNativeReceipt() throws {
        let record = try row(operation())
        for (key, value) in [
            ("creator", AnyJSON.string("forged")), ("nativeChangeId", .string("")),
            ("nativeACLHeadId", .null), ("_objectId", .string("foreign-root")),
            ("payload", .string(Data("changed".utf8).base64EncodedString()))
        ] {
            var altered = try XCTUnwrap(record.object); altered[key] = value
            XCTAssertThrowsError(try decode(response([.object(altered)])), key)
        }
    }
    func testNativeSnapshotQuarantinesCrossTargetLogicalCollision() throws {
        let one = try operation(), other = try operation(target: "another-object")
        let snapshot = try decode(response([row(one), row(other)]))
        XCTAssertEqual(snapshot.projection.all.count, 2)
        XCTAssertTrue(snapshot.projection.live.isEmpty)
        XCTAssertEqual(snapshot.projection.conflicts[one.logicalKey]?.count, 2)
    }
    func testNativeSnapshotPreservesObservedRemoveAndUnseenAdd() throws {
        let one = try operation(), unseen = try operation(id: String(repeating: "2", count: 32))
        let remove = try operation(id: String(repeating: "3", count: 32), kind: .remove, observed: [one.claimID])
        let snapshot = try decode(response([row(remove), row(unseen), row(one)]))
        XCTAssertEqual(snapshot.projection.live.map(\.id), [unseen.claimID])
        XCTAssertTrue(snapshot.projection.pendingObserved.isEmpty)
    }
    func testNativeByteBoundRejectsOversizedEnvelopeBeforeProjection() throws {
        var value = try XCTUnwrap(response([]).object)
        value["futureMetadata"] = .string(String(repeating: "x", count: 16 * 1024 * 1024))
        XCTAssertThrowsError(try decode(.object(value))) {
            XCTAssertEqual($0 as? AnyEngineError, .readLimit)
        }
    }
    func testNativeFullStateWatchRequiresMatchingEventGeneration() throws {
        var window = AnyGuardedTorahWatchWindow(spaceID: "space", rootID: root, limit: 10000)
        XCTAssertThrowsError(try window.apply(frame(response([]), id: String(repeating: "b", count: 64))))
        XCTAssertThrowsError(try window.apply(.init(event: "snapshot",
            data: JSONEncoder().encode(response([])))))
    }
    func testNativeWatchStartsAtomicAndCoalescesIdenticalGeneration() throws {
        var window = AnyGuardedTorahWatchWindow(spaceID: "space", rootID: root, limit: 10000)
        let initial = try frame(response([]))
        XCTAssertTrue(try XCTUnwrap(window.apply(initial)).initial)
        XCTAssertNil(try window.apply(initial))
        let nextGeneration = String(repeating: "b", count: 64)
        let next = try XCTUnwrap(window.apply(frame(
            response([row(operation())], generation: nextGeneration), id: nextGeneration)))
        XCTAssertFalse(next.initial)
        XCTAssertEqual(next.snapshot.projection.live.count, 1)
    }
    func testNativeWatchRejectsMissingImmutableClaimsAndReusedGeneration() throws {
        let row = try row(operation())
        var window = AnyGuardedTorahWatchWindow(spaceID: "space", rootID: root, limit: 10000)
        _ = try window.apply(frame(response([row])))
        let nextGeneration = String(repeating: "b", count: 64)
        XCTAssertThrowsError(try window.apply(frame(response([], generation: nextGeneration), id: nextGeneration)))
        var empty = AnyGuardedTorahWatchWindow(spaceID: "space", rootID: root, limit: 10000)
        _ = try empty.apply(frame(response([])))
        XCTAssertThrowsError(try empty.apply(frame(response([row]))))
    }
    func testNativeErrorAndDeltaEventsInvalidateFullStateWatch() {
        for event in ["error", "changes", "ready", "message"] {
            var window = AnyGuardedTorahWatchWindow(spaceID: "space", rootID: root, limit: 10000)
            XCTAssertThrowsError(try window.apply(.init(event: event, data: Data("{}".utf8))))
        }
    }
    func testSSEParserRetainsEventIDWithoutInventingResumeState() throws {
        var parser = AnySSEParser()
        let values = try parser.feed(Data("id: native-generation\nevent: snapshot\ndata: {}\n\nevent: snapshot\ndata: {}\n\n".utf8))
        XCTAssertEqual(values.map(\.id), ["native-generation", nil])
        XCTAssertThrowsError(try parser.feed(Data("id: bad\0id\n\n".utf8)))
    }
    func testQueryItemsEncodeHebrewAndCannotChangeEndpointOrPath() throws {
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:12345")!, expectedAccountID: "account")
        let identity = "6:תורה/?&redirect=http://example.invalid#fragment"
        let request = try client.makeRequest(method: "GET", path: ["v1", "spaces", "space", "pinkha", "related"],
            body: nil, query: ["identity": identity, "limit": "100"])
        let url = try XCTUnwrap(request.url)
        let parts = try XCTUnwrap(URLComponents(url: url, resolvingAgainstBaseURL: false))
        XCTAssertEqual(parts.host, "127.0.0.1")
        XCTAssertEqual(parts.port, 12345)
        XCTAssertEqual(parts.path, "/v1/spaces/space/pinkha/related")
        XCTAssertNil(parts.fragment)
        XCTAssertEqual(parts.queryItems?.first(where: { $0.name == "identity" })?.value, identity)
    }
}
