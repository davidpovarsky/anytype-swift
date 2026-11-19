import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyHanlin

final class NativeCreationCapabilityTests: XCTestCase {
    func testPageEligibilityRequiresExactNativeCurrentWriterCreationVersion() throws {
        let contract = AnyGuardedTorahCapabilities.contract
        for value in [AnyJSON.null, .bool(true), .integer(0), .integer(2), .string("1")] {
            XCTAssertThrowsError(try AnyHanlinCreationAuthority.requireCurrentWriterCreation(
                .object(["contract": .string(contract), "currentWriterObjectCreate": value])))
        }
        XCTAssertThrowsError(try AnyHanlinCreationAuthority.requireCurrentWriterCreation(
            .object(["contract": .string("generic"), "currentWriterObjectCreate": .integer(1)])))
        XCTAssertNoThrow(try AnyHanlinCreationAuthority.requireCurrentWriterCreation(
            .object(["contract": .string(contract), "currentWriterObjectCreate": .integer(1)])))
    }
}
