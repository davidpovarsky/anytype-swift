import Foundation
import XCTest
@testable import PinkhaKit

final class TorahAuthorizedOperationReadTests: XCTestCase {
    private let operationID = String(repeating: "1", count: 32)
    private let token = String(repeating: "a", count: 64)
    private func scope(_ space: String = "space") throws -> TorahOperationReadScope {
        try .init(engine: .any, accountID: "account", spaceID: space, sessionGeneration: UUID())
    }
    private func variant(_ digit: String = "2", space: String = "space", block: String? = nil,
                         state: TorahOperationTargetReachability = .liveDocument,
                         author: String = "account", creator: String = "account",
                         bytes: Data = Data([0, 255, 1])) throws -> TorahAuthorizedOperationVariant {
        try .init(claimID: String(repeating: "1", count: 64) + "/" + String(repeating: digit, count: 64),
            operationID: operationID, spaceID: space, authorID: author,
            target: .init(objectId: "object", blockId: block), canonicalBytes: bytes,
            provenance: [.init(creator: creator, nativeChangeID: "change", nativeACLHeadID: "acl")],
            reachability: state)
    }
    func testCompleteConflictClosurePreservesExactCanonicalBytesAndProvenance() throws {
        let values = try [variant("2"), variant("3", block: "missing-block", state: .unreachableBlock)]
        let result = try TorahAuthorizedOperationSnapshot(scope: scope(), operationID: operationID,
            outcome: .found, nativeSnapshotToken: token, complete: true, variants: values)
        XCTAssertTrue(result.conflicted)
        XCTAssertEqual(result.variants[0].canonicalBytes, Data([0, 255, 1]))
        XCTAssertEqual(result.variants[1].reachability, .unreachableBlock)
        XCTAssertEqual(result.variants[1].provenance.first?.nativeACLHeadID, "acl")
    }
    func testAbsenceRequiresCompleteVerifiedLocalSnapshotAndNeverMissingPayload() throws {
        _ = try TorahAuthorizedOperationSnapshot(scope: scope(), operationID: operationID,
            outcome: .absentInVerifiedLocalSnapshot, nativeSnapshotToken: token, complete: true, variants: [])
        for (outcome, complete, values) in [
            (TorahOperationReadOutcome.found, true, [TorahAuthorizedOperationVariant]()),
            (.absentInVerifiedLocalSnapshot, true, [try variant()]),
            (.absentInVerifiedLocalSnapshot, false, [])
        ] {
            XCTAssertThrowsError(try TorahAuthorizedOperationSnapshot(scope: scope(), operationID: operationID,
                outcome: outcome, nativeSnapshotToken: token, complete: complete, variants: values))
        }
    }
    func testRejectsPartialScopeDuplicateAndUnsortedClosures() throws {
        for values in [try [variant(space: "foreign")], try [variant(), variant()], try [variant("3"), variant("2")]] {
            XCTAssertThrowsError(try TorahAuthorizedOperationSnapshot(scope: scope(), operationID: operationID,
                outcome: .found, nativeSnapshotToken: token, complete: true, variants: values))
        }
        XCTAssertThrowsError(try variant(block: "block", state: .liveDocument))
        XCTAssertThrowsError(try variant(state: .unreachableBlock))
        XCTAssertThrowsError(try variant(creator: "foreign"))
    }
    func testAuthorityIdentityUsesExactUTF8InsteadOfUnicodeEquivalentSpelling() throws {
        let composed = "\u{e9}", decomposed = "e\u{301}", generation = UUID()
        XCTAssertEqual(composed, decomposed)
        let first = try TorahOperationReadScope(engine: .any, accountID: composed, spaceID: "space", sessionGeneration: generation)
        let other = try TorahOperationReadScope(engine: .any, accountID: decomposed, spaceID: "space", sessionGeneration: generation)
        XCTAssertNotEqual(first, other)
        XCTAssertThrowsError(try variant(author: composed, creator: decomposed))
        XCTAssertThrowsError(try TorahAuthorizedOperationSnapshot(scope: scope(composed), operationID: operationID,
            outcome: .found, nativeSnapshotToken: token, complete: true, variants: [variant(space: decomposed)]))
    }
    func testInvalidOperationIdentityAndBoundedResponseFailClosed() throws {
        for value in ["", "1", String(repeating: "A", count: 32), String(repeating: "0", count: 33)] {
            XCTAssertThrowsError(try TorahAuthorizedOperationReadContract.validateOperationID(value))
        }
        XCTAssertThrowsError(try variant(bytes: Data(repeating: 1, count: TorahAuthorizedOperationReadContract.maximumResponseBytes + 1)))
        let large = try variant(bytes: Data(repeating: 1, count: TorahAuthorizedOperationReadContract.maximumResponseBytes))
        XCTAssertThrowsError(try TorahAuthorizedOperationSnapshot(scope: scope(), operationID: operationID,
            outcome: .found, nativeSnapshotToken: token, complete: true, variants: [large]))
    }
}
