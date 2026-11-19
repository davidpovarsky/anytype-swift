import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyTorahOperationTests: XCTestCase {
    private func add(_ n: Int, _ payload: String = "value", target: String = "disposable-document") throws -> AnyTorahOperation {
        try AnyTorahOperation(
            operationID: String(format: "%032x", n), spaceID: "disposable-space",
            authorID: "disposable-account", kind: .add,
            targetObjectID: target, targetBlockID: "stable-block",
            providerID: "sefaria", canonicalRef: "Genesis.1.1", payload: Data(payload.utf8))
    }
    private func claim(_ op: AnyTorahOperation) throws -> AnyTorahClaim {
        try AnyTorahClaim(operation: op, creator: op.authorID)
    }
    private func remove(_ n: Int, _ observed: [String]) throws -> AnyTorahOperation {
        try AnyTorahOperation(
            operationID: String(format: "%032x", n), spaceID: "disposable-space",
            authorID: "disposable-account", kind: .remove,
            targetObjectID: "disposable-document", targetBlockID: "stable-block", observed: observed)
    }
    private func replace(_ n: Int, _ observed: [String]) throws -> AnyTorahOperation {
        try AnyTorahOperation(
            operationID: String(format: "%032x", n), spaceID: "disposable-space",
            authorID: "disposable-account", kind: .replace,
            targetObjectID: "disposable-document", targetBlockID: "stable-block",
            providerID: "sefaria", canonicalRef: "Genesis.1.2",
            payload: Data("replacement".utf8), observed: observed)
    }

    func testPinnedHeartGoldenVectorIsByteCompatible() throws {
        let op = try add(1, "א<>&\n")
        XCTAssertEqual(op.canonicalBytes.count, 188)
        XCTAssertEqual(op.claimID, "89344c7ac74f7d5df8ef2a94f9592a7ed86a9dccc47084f8ce27d98080c29263/3652b732b88752a35184fcf1af80f8d3e499fb5e5e4132a8064e6236a54cd589")
        XCTAssertEqual(op.recordID.count, 128)
        XCTAssertFalse(op.recordID.contains("/"))
        XCTAssertNotEqual(op.claimID, try add(1, "א<>&").claimID)
    }

    func testSHA256KnownAnswer() {
        XCTAssertEqual(AnyContentDigest.sha256(Data("abc".utf8)),
                       "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    }

    func testObservedSetCanonicalization() throws {
        let a = try add(1).claimID, b = try add(2).claimID
        XCTAssertEqual(try replace(3, [b, a, b]).claimID, try replace(3, [a, b]).claimID)
    }

    func testRequiredIdentifiersAndBoundsFailClosed() {
        XCTAssertThrowsError(try AnyTorahOperation(operationID: String(repeating: "A", count: 32),
            spaceID: "s", authorID: "a", kind: .add, targetObjectID: "o",
            providerID: "p", canonicalRef: "c", payload: Data([1])))
        XCTAssertThrowsError(try AnyTorahOperation(operationID: String(repeating: "0", count: 32),
            spaceID: "s", authorID: "a", kind: .replace, targetObjectID: "o",
            providerID: "p", canonicalRef: "c", payload: Data([1])))
        XCTAssertThrowsError(try AnyTorahOperation(operationID: String(repeating: "0", count: 32),
            spaceID: "s", authorID: "a", kind: .add, targetObjectID: "o",
            providerID: "p", canonicalRef: "c", payload: Data(repeating: 1, count: 65537)))
    }

    func testOpaquePayloadIncludingUnknownFieldsIsUnchanged() throws {
        let bytes = Data([0, 255, 10, 128])
        let op = try AnyTorahOperation(operationID: String(repeating: "a", count: 32),
            spaceID: "s", authorID: "a", kind: .add, targetObjectID: "o",
            providerID: "p", canonicalRef: "c", payload: bytes)
        var fields = try XCTUnwrap(op.fields.object)
        fields["id"] = .string("root/" + op.recordID)
        let decoded = try AnyTorahOperation.fromRecord(.object(fields), expectedSpaceID: "s")
        XCTAssertEqual(decoded.payload, bytes)
    }

    func testCodableCannotBypassOperationValidation() throws {
        let valid = try JSONEncoder().encode(add(1))
        XCTAssertEqual(try JSONDecoder().decode(AnyTorahOperation.self, from: valid), try add(1))
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: valid) as? [String: Any])
        object["version"] = 2
        XCTAssertThrowsError(try JSONDecoder().decode(AnyTorahOperation.self,
            from: JSONSerialization.data(withJSONObject: object)))
        object["version"] = 1
        object["operationID"] = "malformed"
        XCTAssertThrowsError(try JSONDecoder().decode(AnyTorahOperation.self,
            from: JSONSerialization.data(withJSONObject: object)))
    }

    func testNativeCreatorMustMatchCanonicalAuthor() throws {
        XCTAssertThrowsError(try AnyTorahClaim(operation: add(1), creator: "foreign"))
    }

    func testOfflineOperationIDVariantsAreBothQuarantinedAcrossTargets() throws {
        let a = try claim(add(1, "A"))
        let b = try claim(add(1, "B", target: "another-document"))
        let projection = try AnyTorahProjection(claims: [a, b])
        XCTAssertEqual(projection.conflicts.count, 1)
        XCTAssertTrue(projection.live.isEmpty)
        XCTAssertEqual(projection.all.count, 2)
        XCTAssertEqual(projection, try AnyTorahProjection(claims: [b, a, a]))
    }

    func testObservedRemovePreservesConcurrentUnseenAdd() throws {
        let a = try add(1), b = try add(2)
        let projection = try AnyTorahProjection(claims: [claim(remove(3, [a.claimID])), claim(a), claim(b)])
        XCTAssertEqual(projection.live.map(\.id), [b.claimID])
    }

    func testConcurrentReplacementsBothSurvive() throws {
        let a = try add(1)
        let first = try replace(2, [a.claimID]), second = try replace(3, [a.claimID])
        let projection = try AnyTorahProjection(claims: [claim(a), claim(first), claim(second)])
        XCTAssertEqual(Set(projection.live.map(\.id)), Set([first.claimID, second.claimID]))
    }

    func testRemovingTombstoneDoesNotResurrect() throws {
        let a = try add(1)
        let r = try remove(2, [a.claimID]), rr = try remove(3, [r.claimID])
        XCTAssertTrue(try AnyTorahProjection(claims: [claim(a), claim(r), claim(rr)]).live.isEmpty)
        XCTAssertTrue(try AnyTorahProjection(claims: [claim(r)]).live.isEmpty)
    }

    func testUnknownAndForeignTargetPredecessorsAreDistinct() throws {
        let a = try add(1, target: "foreign")
        let r = try remove(2, [a.claimID])
        XCTAssertThrowsError(try AnyTorahProjection(claims: [claim(a), claim(r)]))
        // Inbound out-of-order replay keeps the unknown predecessor tombstone.
        XCTAssertTrue(try AnyTorahProjection(claims: [claim(r)]).live.isEmpty)
    }

    func testReadLimitDoesNotReturnPartialProjection() throws {
        XCTAssertThrowsError(try AnyTorahProjection(claims: [claim(add(1)), claim(add(2))], limit: 1))
    }

    func testTamperedRecordHashFailsClosed() throws {
        let op = try add(1)
        var fields = try XCTUnwrap(op.fields.object)
        fields["id"] = .string(op.recordID)
        fields["payload"] = .string(Data("tampered".utf8).base64EncodedString())
        XCTAssertThrowsError(try AnyTorahOperation.fromRecord(.object(fields), expectedSpaceID: op.spaceID))
    }

    func testRecordCannotCrossSpaces() throws {
        let op = try add(1)
        var fields = try XCTUnwrap(op.fields.object)
        fields["id"] = .string(op.recordID)
        XCTAssertThrowsError(try AnyTorahOperation.fromRecord(.object(fields), expectedSpaceID: "other-space"))
    }

    func testOnlyLiteralLoopbackEndpointIsAccepted() throws {
        _ = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: "http://127.0.0.1:12345")), expectedAccountID: "a")
        for address in ["https://example.com", "http://0.0.0.0:12345", "http://localhost:12345",
                        "http://127.0.0.1:12345/?other=1"] {
            XCTAssertThrowsError(try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: address)), expectedAccountID: "a"))
        }
    }

    func testSchemaPreservesImmutableUndeletableIndexedClaims() throws {
        let part = try XCTUnwrap(AnyTorahSchema.bundle["parts"]?.array?.first)
        let draft = try XCTUnwrap(part["datasets"]?.array?.first?.object)
        XCTAssertEqual(draft["deleteBy"], .string("none"))
        XCTAssertEqual(draft["idRule"], .string("user"))
        XCTAssertEqual(draft["shared"], .bool(true))
        XCTAssertEqual(draft["indexes"]?.array?.count, 3)
        XCTAssertEqual(draft["fields"]?.array?.filter { $0["stamp"] == nil }
            .allSatisfy { $0["mutableBy"] == .string("never") }, true)
    }

    func testSchemaAdoptionRejectsMutableClaims() throws {
        let part = try XCTUnwrap(AnyTorahSchema.bundle["parts"]?.array?.first)
        var definition = try XCTUnwrap(part["datasets"]?.array?.first?.object)
        definition["module"] = .string("records")
        definition["collection"] = .string("root_claims")
        let valid = try AnyTorahSchema.verify(.object(definition), rootID: "root")
        XCTAssertEqual(valid, "root_claims")
        definition["deleteBy"] = .string("anyone")
        XCTAssertThrowsError(try AnyTorahSchema.verify(.object(definition), rootID: "root"))
    }
}
