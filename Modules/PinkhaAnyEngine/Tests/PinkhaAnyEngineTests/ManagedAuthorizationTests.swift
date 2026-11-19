import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class ManagedAuthorizationTests: XCTestCase {
    func testManagedCapabilityCoversJSONAndSSEWithoutDebugDisclosure() throws {
        let secret = String(repeating: "b", count: 64)
        let authorization = try AnyHTTPAuthorization(token: secret)
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:12345")!,
                                       expectedAccountID: "synthetic", authorization: authorization)
        for path in [["v1", "auth"], ["v1", "health"], ["v1", "spaces", "space", "pinkha", "watch"]] {
            let request = try client.makeRequest(method: "GET", path: path, body: nil)
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-Any-Control-Token"), secret)
        }
        XCTAssertTrue(client.hasManagedAuthorization)
        XCTAssertFalse(String(describing: client).contains(secret))
        XCTAssertFalse(String(reflecting: client).contains(secret))
        XCTAssertFalse(String(describing: authorization).contains(secret))
        XCTAssertFalse(String(reflecting: authorization).contains(secret))
    }

    func testMalformedCapabilityCannotInjectHeadersAndStandaloneStaysExplicit() throws {
        for value in ["", String(repeating: "b", count: 63), String(repeating: "B", count: 64),
                      String(repeating: "a", count: 62) + "\\r\\n"] {
            XCTAssertThrowsError(try AnyHTTPAuthorization(token: value))
        }
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:12345")!, expectedAccountID: "synthetic")
        XCTAssertFalse(client.hasManagedAuthorization)
        XCTAssertNil(try client.makeRequest(method: "GET", path: ["v1", "health"], body: nil)
            .value(forHTTPHeaderField: "X-Any-Control-Token"))
    }
}
