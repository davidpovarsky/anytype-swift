import XCTest
import PinkhaKit
import PinkhaTorahPresentation

final class PresentationContractTests: XCTestCase {
    func testUncertainPersistenceDoesNotEqualSaved() {
        XCTAssertNotEqual(TorahAssociationPersistenceState.uncertain("unconfirmed"), .saved)
        XCTAssertEqual(TorahAssociationPersistenceState.conflict("changed"), .conflict("changed"))
    }
}
