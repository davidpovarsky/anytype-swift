import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyHTTPClientTests: XCTestCase {
    func testHTTP200PartialRejectionIsFailure() {
        let data = Data(#"{"created":0,"rejections":[{"code":"upsert.immutable_field"}]}"#.utf8)
        XCTAssertThrowsError(try AnyHTTPClient.decodeResponse(status: 200, data: data)) {
            XCTAssertEqual($0 as? AnyEngineError, .writeRejected(["upsert.immutable_field"]))
        }
    }
    func testMalformedRejectionsNeverCountAsSuccess() {
        let data = Data(#"{"rejections":"not-an-array"}"#.utf8)
        XCTAssertThrowsError(try AnyHTTPClient.decodeResponse(status: 200, data: data))
    }
    func testNestedPageRejectionsAreFailure() {
        let data = Data(#"{"created":1,"pages":[{"rejections":[{"code":"record.rejected"}]}]}"#.utf8)
        XCTAssertThrowsError(try AnyHTTPClient.decodeResponse(status: 200, data: data)) {
            XCTAssertEqual($0 as? AnyEngineError, .writeRejected(["record.rejected"]))
        }
    }
    func testHTTPErrorKeepsMachineCodeWithoutEchoingPayload() {
        let data = Data(#"{"error":{"code":"space.forbidden","message":"sensitive source text"}}"#.utf8)
        XCTAssertThrowsError(try AnyHTTPClient.decodeResponse(status: 403, data: data)) {
            XCTAssertEqual($0 as? AnyEngineError, .http(status: 403, code: "space.forbidden"))
        }
    }
    func testRedirectIsNotDecodedAsSuccess() {
        XCTAssertThrowsError(try AnyHTTPClient.decodeResponse(status: 302, data: Data()))
    }
    func testEmptyRejectionsAreAllowed() throws {
        let data = Data(#"{"created":1,"rejections":[]}"#.utf8)
        XCTAssertEqual(try AnyHTTPClient.decodeResponse(status: 200, data: data)["created"], .integer(1))
    }
}
