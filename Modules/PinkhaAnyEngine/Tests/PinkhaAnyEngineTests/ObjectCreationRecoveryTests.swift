import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class ObjectCreationRecoveryTests: XCTestCase {
    private func envelope(stage: String = "root-stored", cleanup: String = "not-attempted",
                          object: String = "created-object") -> AnyJSON {
        .object(["error": .object(["code": .string("pinkha.object_create_uncertain"),
            "message": .string("not diagnostic content"),
            "details": .object(["spaceId": .string("space"), "objectId": .string(object),
                "creationStage": .string(stage), "cleanup": .string(cleanup), "outcome": .string("uncertain")])])])
    }
    func testExactNativePartialFailureCarriesOnlyValidatedRecoveryMetadata() throws {
        let body = try JSONEncoder().encode(envelope())
        do { _ = try AnyHTTPClient.decodeResponse(status: 503, data: body); XCTFail("partial creation accepted") }
        catch let recovery as AnyObjectCreationUncertain {
            XCTAssertEqual(recovery.spaceID, "space")
            XCTAssertEqual(recovery.objectID, "created-object")
            XCTAssertEqual(recovery.stage, .rootStored)
            XCTAssertEqual(String(reflecting: recovery), "AnyObjectCreationUncertain(recovery metadata redacted)")
        }
    }
    func testMalformedOrDifferentFailureCannotInventRecoverableObjectIdentity() throws {
        for value in [envelope(stage: "unknown"), envelope(cleanup: "deleted"), envelope(object: "../foreign")] {
            do { _ = try AnyHTTPClient.decodeResponse(status: 503, data: JSONEncoder().encode(value)); XCTFail() }
            catch let error as AnyEngineError {
                XCTAssertEqual(error, .http(status: 503, code: "pinkha.object_create_uncertain"))
            }
        }
        XCTAssertNil(AnyObjectCreationUncertain.decode(status: 403, response: envelope()))
    }
    func testLateAccountSwitchRetainsIDOnlyForDedicatedOriginalSpaceCreateRoute() {
        let result = AnyJSON.object(["objectId": .string("created-object")])
        let recovery = AnyObjectCreationUncertain.lostConfirmation(method: "POST",
            path: ["v1", "spaces", "original-space", "pinkha", "objects"], response: result)
        XCTAssertEqual(recovery?.spaceID, "original-space")
        XCTAssertEqual(recovery?.stage, .bootstrapStored)
        XCTAssertNil(AnyObjectCreationUncertain.lostConfirmation(method: "GET",
            path: ["v1", "spaces", "original-space", "pinkha", "objects"], response: result))
        XCTAssertNil(AnyObjectCreationUncertain.lostConfirmation(method: "POST",
            path: ["v1", "spaces", "original-space", "objects"], response: result))
        XCTAssertNil(AnyObjectCreationUncertain.lostConfirmation(method: "POST",
            path: ["v1", "spaces", "original-space", "pinkha", "objects"], response: .object([:])))
    }
}
