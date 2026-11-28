import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Component qualification of the new adapter, including the exact retained
/// native HTTP answer. It does not assert a new network grant or current quota.
final class NativeSharedSpacesLimitTests: XCTestCase {
    func testActualRetainedNativeAnswerPreservesQuotaAndNanosecondTimestamp() throws {
        // Exact165-byte response-5.json from account-limits-read1, independently
        // retrieved and joined to raw receipt aa61aadca348b2c89bc0321f6239a299c4d2fb3d62014366e1c4b707defef100.
        let raw = try XCTUnwrap(Data(base64Encoded:
            "eyJzdG9yYWdlIjp7ImxpbWl0Qnl0ZXMiOjAsInVzYWdlQnl0ZXMiOjIxMDcwLCJmZXRjaGVkQXQiOiIyMDI2LTExLTI3VDA1OjQyOjQ1LjU3OTQ3MjIwMVoifSwic2hhcmVkU3BhY2VzIjp7ImxpbWl0IjozLCJmZXRjaGVkQXQiOiIyMDI2LTExLTI3VDA1OjQyOjQ2LjM0MDEwODcxNloifX0K"))
        XCTAssertEqual(raw.count, 165)
        XCTAssertEqual(AnyContentDigest.sha256(raw), "ddfcf4e186e07a7658a9028c4e1870f389c31a1cf80442569aae89e10d7dacbe")
        let response = try JSONDecoder().decode(AnyJSON.self, from: raw)
        guard case .observed(let observation) = try AnyNativeSharedSpacesLimitStore.parse(response) else {
            return XCTFail("the actual native answer must remain present")
        }
        XCTAssertEqual(observation.limit, 3)
        XCTAssertEqual(Data(observation.fetchedAt.rawValue.utf8), Data("2026-11-27T05:42:46.340108716Z".utf8))
        // The account's separate zero-byte storage pool must not become its
        // shared-space allowance. This adapter does not interpret file quota.
        XCTAssertEqual(response["storage"]?["limitBytes"]?.integer, 0)
    }

    func testUnansweredPartAndObservedZeroRemainDistinct() throws {
        XCTAssertEqual(try AnyNativeSharedSpacesLimitStore.parse(.object([:])), .unavailable)
        XCTAssertEqual(try AnyNativeSharedSpacesLimitStore.parse(.object([
            "storage": .object(["limitBytes": .integer(0)])])), .unavailable)
        for limit in [Int64(0), Int64(UInt32.max)] {
            guard case .observed(let value) = try AnyNativeSharedSpacesLimitStore.parse(response(limit: .integer(limit))) else {
                return XCTFail("an observed limit cannot be erased")
            }
            XCTAssertEqual(Int64(value.limit), limit)
            XCTAssertEqual(value.fetchedAt.rawValue, time)
        }
    }

    func testMalformedPresentPartCannotBecomeUnknownOrRoundedLimit() throws {
        for value in [AnyJSON.null, .bool(false), .number(0.5), .integer(-1),
                      .integer(Int64(UInt32.max) + 1), .string("0"), .array([]), .object([:])] {
            XCTAssertThrowsError(try AnyNativeSharedSpacesLimitStore.parse(response(limit: value)))
        }
        for value in [AnyJSON.null, .array([]), .bool(false), .string("unavailable"),
                      .object(["limit": .integer(0)]), .object(["fetchedAt": .string(time)]),
                      .object(["limit": .integer(0), "fetchedAt": .string(time), "differentScope": .bool(true)]),
                      .object(["limit": .integer(0), "fetchedAt": .null])] {
            XCTAssertThrowsError(try AnyNativeSharedSpacesLimitStore.parse(.object(["sharedSpaces": value])))
        }
        for root in [AnyJSON.null, .array([]), .integer(0)] {
            XCTAssertThrowsError(try AnyNativeSharedSpacesLimitStore.parse(root))
        }
    }

    func testTimestampKeepsNativePrecisionAndRejectsInvalidDatesAndOffsets() throws {
        let accepted = ["2026-11-27T05:42:46Z", "2026-11-27T05:42:46.3Z",
            "2026-11-27T05:42:46.340108716Z", "2024-02-29T23:59:59.123456789+02:00",
            "2000-02-29T00:00:00-05:30", "2026-11-27T05:42:46.000000001Z"]
        for raw in accepted {
            XCTAssertEqual(Data(try AnyNativeRuntimeTimestamp(raw).rawValue.utf8), Data(raw.utf8))
        }
        XCTAssertNotEqual(try AnyNativeRuntimeTimestamp("2026-11-27T05:42:46.340108716Z"),
                          try AnyNativeRuntimeTimestamp("2026-11-27T05:42:46.340108717Z"))
        for raw in ["", "2026-11-27", "2026-11-27t05:42:46z", "2026-11-27T05:42:46.Z",
            "2026-11-27T05:42:46.1234567890Z", "2026-11-27T05:42:46.1", "2026-11-27T05:42:46Z ",
            "2026-11-27T05:42:46+24:00", "2026-11-27T05:42:46+02:60", "2026-11-27T05:42:46+0200",
            "2026-11-27T24:00:00Z", "2026-11-27T05:60:00Z", "2026-11-27T05:42:60Z",
            "2026-02-29T00:00:00Z", "1900-02-29T00:00:00Z", "2026-04-31T00:00:00Z",
            "2026-00-01T00:00:00Z", "2026-13-01T00:00:00Z", "2026-01-00T00:00:00Z"] {
            XCTAssertThrowsError(try AnyNativeRuntimeTimestamp(raw), raw)
        }
    }

    func testDestinationAccountIdentityUsesExactBytesBeforeAnyRequest() throws {
        let composed = "account-caf\u{00E9}"
        let decomposed = "account-cafe\u{0301}"
        XCTAssertEqual(composed, decomposed) // Demonstrates why String == is insufficient.
        XCTAssertNotEqual(Data(composed.utf8), Data(decomposed.utf8))
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: "http://127.0.0.1:1")),
            expectedAccountID: composed)
        XCTAssertThrowsError(try AnyNativeSharedSpacesLimitStore(client: client,
            workspace: .init(accountID: decomposed, spaceID: "space"))) {
            XCTAssertEqual($0 as? AnyHostError, .wrongWorkspace)
        }
        XCTAssertNoThrow(try AnyNativeSharedSpacesLimitStore(client: client,
            workspace: .init(accountID: composed, spaceID: "space")))
    }

    private let time = "2026-11-27T05:42:46.340108716Z"
    private func response(limit: AnyJSON) -> AnyJSON {
        .object(["sharedSpaces": .object(["limit": limit, "fetchedAt": .string(time)])])
    }
}
