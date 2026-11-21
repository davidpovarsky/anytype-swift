import Foundation
import PinkhaKit
import SwiftProtobuf
import XCTest
@testable import PinkhaHeartEngine

final class HeartAuthorizedOperationCodecTests: XCTestCase {
    func testRequestContainsOnlyOwnedSpaceAndOperationIdentity() throws {
        let scope = try HeartReadFixture.scope()
        let bytes = try HeartAuthorizedOperationCodec.request(operationID: HeartReadFixture.operationID, scope: scope)
        let request = try HeartAuthorizedOperationCodec.Wire.Request(serializedBytes: bytes)
        XCTAssertEqual(request.protocolVersion, 1)
        XCTAssertEqual(request.spaceID, scope.spaceID)
        XCTAssertEqual(request.operationID, HeartReadFixture.operationID)
        XCTAssertEqual(request.unknownFields, UnknownStorage())
        XCTAssertThrowsError(try HeartAuthorizedOperationCodec.request(operationID: "bad", scope: scope))
        let foreign = try TorahOperationReadScope(engine: .any, accountID: "account", spaceID: "space", sessionGeneration: UUID())
        XCTAssertThrowsError(try HeartAuthorizedOperationCodec.request(operationID: HeartReadFixture.operationID, scope: foreign))
    }

    func testCompleteConflictPreservesOpaqueBytesTargetsAndNativeReceipts() throws {
        var response = try HeartReadFixture.response()
        var second = try HeartReadFixture.variant(payload: Data([0, 255, 0, 128]), block: "orphan")
        second.reachability = .unreachableBlock
        response.snapshot.variants.append(second)
        response.snapshot.variants.sort { $0.claimID < $1.claimID }
        let decoded = try HeartReadFixture.decode(response)
        XCTAssertTrue(decoded.conflicted)
        XCTAssertEqual(decoded.variants.map(\.canonicalBytes), response.snapshot.variants.map(\.canonicalBytes))
        XCTAssertEqual(decoded.variants.first { $0.target.blockId == "orphan" }?.reachability, .unreachableBlock)
        XCTAssertEqual(decoded.variants[0].provenance.first?.nativeChangeID, "native-change")
        XCTAssertEqual(decoded.variants[0].provenance.first?.nativeACLHeadID, "native-acl")
    }

    func testAbsenceRequiresCompleteNativeSnapshot() throws {
        var response = try HeartReadFixture.response()
        response.snapshot.variants = []
        response.snapshot.outcome = .absentInVerifiedLocalSnapshot
        XCTAssertEqual(try HeartReadFixture.decode(response).outcome, .absentInVerifiedLocalSnapshot)
        response.snapshot.complete = false
        XCTAssertThrowsError(try HeartReadFixture.decode(response))
        response.snapshot.complete = true
        response.snapshot.outcome = .found
        XCTAssertThrowsError(try HeartReadFixture.decode(response))
    }

    func testCanonicalMutationOrIdentityMismatchRejectsEntireClosure() throws {
        let original = try HeartReadFixture.response()
        var changed = original
        changed.snapshot.variants[0].canonicalBytes[changed.snapshot.variants[0].canonicalBytes.count - 5] ^= 1
        XCTAssertThrowsError(try HeartReadFixture.decode(changed))
        changed = original
        changed.snapshot.variants[0].authorID = "foreign"
        XCTAssertThrowsError(try HeartReadFixture.decode(changed))
        changed = original
        changed.snapshot.variants[0].target.blockID = "other"
        XCTAssertThrowsError(try HeartReadFixture.decode(changed))
        changed = original
        var invalid = try HeartReadFixture.variant(payload: Data([1, 2, 3]))
        invalid.claimID = String(repeating: "0", count: 64) + "/" + String(repeating: "f", count: 64)
        changed.snapshot.variants.append(invalid)
        changed.snapshot.variants.sort { $0.claimID < $1.claimID }
        XCTAssertThrowsError(try HeartReadFixture.decode(changed))
    }

    func testAuthorityBindingUsesExactUTF8() throws {
        let composed = "\u{e9}", decomposed = "e\u{301}"
        XCTAssertEqual(composed, decomposed)
        var response = try HeartReadFixture.response()
        response.snapshot.accountID = composed
        let scope = try HeartReadFixture.scope(account: decomposed)
        XCTAssertThrowsError(try HeartReadFixture.decode(response, scope: scope))
        response = try HeartReadFixture.response(author: composed)
        response.snapshot.variants[0].authorID = decomposed
        response.snapshot.variants[0].provenance[0].creator = decomposed
        XCTAssertThrowsError(try HeartReadFixture.decode(response))
    }

    func testDuplicateOrUnknownProvenanceCannotBeReleased() throws {
        var response = try HeartReadFixture.response()
        response.snapshot.variants[0].provenance.append(response.snapshot.variants[0].provenance[0])
        response.snapshot.variants[0].provenance[1].nativeAclHeadID = "different-acl-for-same-change"
        XCTAssertThrowsError(try HeartReadFixture.decode(response))
        response = try HeartReadFixture.response()
        response.snapshot.variants[0].provenance[0].creator = "foreign"
        XCTAssertThrowsError(try HeartReadFixture.decode(response))
        response = try HeartReadFixture.response()
        response.snapshot.variants[0].reachability = .UNRECOGNIZED(99)
        XCTAssertThrowsError(try HeartReadFixture.decode(response))
    }

    func testMalformedAndOversizedTransportCannotReleasePayload() throws {
        let scope = try HeartReadFixture.scope()
        for bytes in [Data(), Data([255]), Data(repeating: 0, count: TorahAuthorizedOperationReadContract.maximumResponseBytes + 1)] {
            XCTAssertThrowsError(try HeartAuthorizedOperationCodec.decode(bytes, operationID: HeartReadFixture.operationID, scope: scope))
        }
        var bytes = try HeartReadFixture.response().serializedData()
        // Unknown varint field99; native candidate protocol has no extension.
        bytes.append(contentsOf: [0x98, 0x06, 0x01])
        XCTAssertThrowsError(try HeartAuthorizedOperationCodec.decode(bytes, operationID: HeartReadFixture.operationID, scope: scope))
    }

    func testNativeFailureRequiresAbsentPayloadAndMapsStableReason() throws {
        var response = try HeartReadFixture.response()
        response.error.code = .permissionDenied
        XCTAssertThrowsError(try HeartReadFixture.decode(response)) { error in
            XCTAssertEqual(error as? TorahOperationReadError, .malformedNativeResponse)
        }
        response.clearSnapshot()
        XCTAssertThrowsError(try HeartReadFixture.decode(response)) { error in
            XCTAssertEqual(error as? TorahOperationReadError, .permissionDenied)
        }
        response.error.code = .historyUnavailable
        XCTAssertThrowsError(try HeartReadFixture.decode(response)) { error in
            XCTAssertEqual(error as? TorahOperationReadError, .historyUnavailable)
        }
        response.error.code = .UNRECOGNIZED(88)
        XCTAssertThrowsError(try HeartReadFixture.decode(response)) { error in
            XCTAssertEqual(error as? TorahOperationReadError, .malformedNativeResponse)
        }
    }

    func testCanonicalDecoderRejectsNoncanonicalObservedSetAndTrailingBytes() throws {
        let id = String(repeating: "1", count: 64) + "/" + String(repeating: "2", count: 64)
        let valid = HeartReadFixture.canonical(kind: "remove", payload: Data(), observed: [id])
        _ = try HeartNativeOperationCanonical(exactBytes: valid)
        XCTAssertThrowsError(try HeartNativeOperationCanonical(exactBytes: valid + Data([0])))
        XCTAssertThrowsError(try HeartNativeOperationCanonical(exactBytes:
            HeartReadFixture.canonical(kind: "remove", payload: Data(), observed: [id, id])))
        XCTAssertThrowsError(try HeartNativeOperationCanonical(exactBytes:
            HeartReadFixture.canonical(kind: "add", payload: Data(), observed: [])))
        XCTAssertThrowsError(try HeartNativeOperationCanonical(exactBytes: Data(valid.prefix(20))))
    }
}

enum HeartReadFixture {
    typealias Wire = HeartAuthorizedOperationCodec.Wire
    static let operationID = String(repeating: "1", count: 32)
    static func scope(account: String = "account") throws -> TorahOperationReadScope {
        try .init(engine: .heart, accountID: account, spaceID: "space", sessionGeneration: UUID())
    }
    static func canonical(kind: String = "add", author: String = "author", block: String = "block",
                          payload: Data = Data([0, 255, 1]), observed: [String] = []) -> Data {
        // Fixture encoder deliberately spells out the frozen native format.
        var result = Data("pinkha-t2-operation\0".utf8)
        result.append(contentsOf: [0, 0, 0, 1])
        for field in ["space", operationID, author, kind, "object", block,
                      kind == "remove" ? "" : "fixture", kind == "remove" ? "" : "fixture:read:1"] {
            frame(Data(field.utf8), into: &result)
        }
        frame(payload, into: &result)
        let count = UInt32(observed.count)
        result.append(contentsOf: [UInt8(count >> 24), UInt8((count >> 16) & 255), UInt8((count >> 8) & 255), UInt8(count & 255)])
        for item in observed { frame(Data(item.utf8), into: &result) }
        return result
    }
    private static func frame(_ data: Data, into result: inout Data) {
        let count = UInt32(data.count)
        result.append(contentsOf: [UInt8(count >> 24), UInt8((count >> 16) & 255), UInt8((count >> 8) & 255), UInt8(count & 255)])
        result.append(data)
    }
    static func variant(payload: Data = Data([0, 255, 1]), author: String = "author", block: String = "block") throws -> Wire.Variant {
        let bytes = canonical(author: author, block: block, payload: payload)
        let canonical = try HeartNativeOperationCanonical(exactBytes: bytes)
        var result = Wire.Variant()
        result.claimID = canonical.claimID; result.operationID = operationID
        result.spaceID = "space"; result.authorID = author
        result.target.objectID = "object"; result.target.blockID = block
        result.canonicalBytes = bytes
        var provenance = Wire.Provenance()
        provenance.creator = author; provenance.nativeChangeID = "native-change"
        provenance.nativeAclHeadID = "native-acl"
        result.provenance = [provenance]
        result.reachability = block.isEmpty ? .liveDocument : .liveBlock
        return result
    }
    static func response(author: String = "author") throws -> Wire.Response {
        var result = Wire.Response()
        result.protocolVersion = 1; result.error = .init()
        result.snapshot.contract = TorahAuthorizedOperationReadContract.identifier
        result.snapshot.accountID = "account"; result.snapshot.spaceID = "space"
        result.snapshot.operationID = operationID; result.snapshot.outcome = .found
        result.snapshot.complete = true; result.snapshot.nativeSnapshotToken = String(repeating: "a", count: 64)
        result.snapshot.variants = [try variant(author: author)]
        return result
    }
    static func decode(_ response: Wire.Response, scope: TorahOperationReadScope? = nil) throws -> TorahAuthorizedOperationSnapshot {
        try HeartAuthorizedOperationCodec.decode(response.serializedData(), operationID: operationID, scope: scope ?? self.scope())
    }
}
