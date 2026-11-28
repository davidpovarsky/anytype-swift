import Foundation
import XCTest
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
@testable import PinkhaAnyEngine

final class NativeAccountRunBindingTests: XCTestCase {
    private let firstRun = String(repeating: "a", count: 64)
    private let secondRun = String(repeating: "b", count: 64)

    func testExactServerTupleIsTypedAndDiagnosticsRedactItsIdentity() throws {
        let binding = try AnyNativeAccountRunBinding.decode(wire(), expectedAccountID: "alice",
            expectedNetworkID: "network")
        XCTAssertEqual(binding.accountID, "alice")
        XCTAssertEqual(binding.networkID, "network")
        XCTAssertEqual(binding.runID, firstRun)
        XCTAssertFalse(String(describing: binding).contains("alice"))
        XCTAssertFalse(String(reflecting: binding).contains(firstRun))
        var request = URLRequest(url: try XCTUnwrap(URL(string: "http://127.0.0.1:1")))
        binding.apply(to: &request)
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-Any-Expected-Account-Id"), "alice")
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-Any-Expected-Run-Id"), firstRun)
    }

    func testUnknownMissingAndMistypedWireFieldsNeverBecomeAuthority() throws {
        for value in [
            wire(extra: ["futureAuthority": .bool(true)]),
            wire(extra: ["contract": .string("legacy-v0")]),
            wire(extra: ["accountId": .integer(1)]),
            wire(extra: ["networkId": .null]),
            wire(extra: ["runId": .bool(true)])
        ] {
            XCTAssertThrowsError(try AnyNativeAccountRunBinding.decode(value,
                expectedAccountID: "alice", expectedNetworkID: "network"))
        }
        var missing = try XCTUnwrap(wire().object)
        missing.removeValue(forKey: "runId")
        XCTAssertThrowsError(try AnyNativeAccountRunBinding.decode(.object(missing),
            expectedAccountID: "alice", expectedNetworkID: "network"))
    }

    func testAccountAndNetworkComparisonPreserveOpaqueUTF8Identity() throws {
        let composed = "caf\u{00E9}", decomposed = "cafe\u{0301}"
        XCTAssertEqual(composed, decomposed)
        XCTAssertThrowsError(try AnyNativeAccountRunBinding.decode(wire(account: composed),
            expectedAccountID: decomposed, expectedNetworkID: "network")) {
            XCTAssertEqual($0 as? AnyEngineError, .accountChanged)
        }
        XCTAssertThrowsError(try AnyNativeAccountRunBinding.decode(wire(network: composed),
            expectedAccountID: "alice", expectedNetworkID: decomposed)) {
            XCTAssertEqual($0 as? AnyEngineError, .accountChanged)
        }
        let first = try AnyNativeAccountRunBinding(accountID: composed, networkID: "network", runID: firstRun)
        let second = try AnyNativeAccountRunBinding(accountID: decomposed, networkID: "network", runID: firstRun)
        XCTAssertNotEqual(first, second)
    }

    func testSameAccountAfterRebootHasDifferentAuthority() throws {
        let old = try AnyNativeAccountRunBinding.decode(wire(), expectedAccountID: "alice",
            expectedNetworkID: "network")
        let new = try AnyNativeAccountRunBinding.decode(wire(run: secondRun), expectedAccountID: "alice",
            expectedNetworkID: "network")
        XCTAssertNotEqual(old, new)
        XCTAssertThrowsError(try old.requireResponse(response(run: secondRun))) {
            XCTAssertEqual($0 as? AnyEngineError, .writeUncertain)
        }
    }

    func testMalformedRunAndHeaderInjectionIdentitiesAreRejected() throws {
        for run in ["", String(firstRun.dropLast()), firstRun + "a",
                    String(repeating: "A", count: 64), String(repeating: "z", count: 64)] {
            XCTAssertThrowsError(try AnyNativeAccountRunBinding(accountID: "alice",
                networkID: "network", runID: run))
        }
        for identity in ["", "alice\r\nOther: value", "account name", String(repeating: "a", count: 4097)] {
            XCTAssertThrowsError(try AnyNativeAccountRunBinding(accountID: identity,
                networkID: "network", runID: firstRun))
            XCTAssertThrowsError(try AnyNativeAccountRunBinding(accountID: "alice",
                networkID: identity, runID: firstRun))
        }
    }

    func testOnlyDedicatedNativeBoundMutationPathsAreAccepted() throws {
        let settings = ["v1", "pinkha", "bound", "spaces", "space", "settings"]
        let property = ["v1", "pinkha", "bound", "spaces", "space", "properties", "object", "set", "any"]
        try AnyNativeAccountRunBinding.requireRoute(method: "PATCH", path: settings)
        try AnyNativeAccountRunBinding.requireRoute(method: "POST", path: property)
        for (method, path) in [
            ("PATCH", ["v1", "spaces", "space", "settings"]),
            ("POST", ["v1", "spaces", "space", "properties", "object", "set", "any"]),
            ("GET", settings), ("POST", settings), ("PATCH", property),
            ("POST", property + ["extra"]),
            ("POST", Array(property.dropLast()) + ["mutable-owner"]),
            ("PATCH", ["v1", "pinkha", "bound", "spaces", "", "settings"]),
            ("PATCH", ["v1", "pinkha", "bound", "spaces", "..", "settings"])
        ] {
            XCTAssertThrowsError(try AnyNativeAccountRunBinding.requireRoute(method: method, path: path))
        }
    }

    func testEverySuccessfulAcknowledgmentMustNameTheCapturedEngine() throws {
        let binding = try AnyNativeAccountRunBinding(accountID: "alice", networkID: "network", runID: firstRun)
        try binding.requireResponse(response())
        for altered in [
            response(account: "bob"), response(run: secondRun), response(contract: "legacy-v0"),
            response(omitting: "X-Any-Binding-Contract"),
            response(omitting: "X-Any-Bound-Account-Id"),
            response(omitting: "X-Any-Bound-Run-Id")
        ] {
            XCTAssertThrowsError(try binding.requireResponse(altered)) {
                XCTAssertEqual($0 as? AnyEngineError, .writeUncertain)
            }
        }
    }

    private func wire(account: String = "alice", network: String = "network", run: String? = nil,
                      extra: [String: AnyJSON] = [:]) -> AnyJSON {
        var fields: [String: AnyJSON] = [
            "contract": .string(AnyNativeAccountRunBinding.contract),
            "accountId": .string(account), "networkId": .string(network),
            "runId": .string(run ?? firstRun)
        ]
        fields.merge(extra) { _, replacement in replacement }
        return .object(fields)
    }

    private func response(account: String = "alice", run: String? = nil,
                          contract: String = AnyNativeAccountRunBinding.contract,
                          omitting: String? = nil) -> HTTPURLResponse {
        var headers = ["X-Any-Binding-Contract": contract, "X-Any-Bound-Account-Id": account,
                       "X-Any-Bound-Run-Id": run ?? firstRun]
        if let omitting { headers.removeValue(forKey: omitting) }
        return HTTPURLResponse(url: URL(string: "http://127.0.0.1:1")!, statusCode: 204,
            httpVersion: "HTTP/1.1", headerFields: headers)!
    }
}
