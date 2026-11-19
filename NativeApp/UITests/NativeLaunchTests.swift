import XCTest

@MainActor
final class NativeLaunchTests: XCTestCase {
    func testFreshNativeExecutableShowsAccountAndRecoveryEntryPoints() {
        let app = XCUIApplication()
        app.launchArguments = ["--native-ui-tests"]
        app.launch()
        XCTAssertTrue(app.buttons["יצירת חשבון חדש"].waitForExistence(timeout: 30))
        XCTAssertTrue(app.secureTextFields["ביטוי שחזור"].exists)
        XCTAssertTrue(app.buttons["שחזור"].exists)
        app.terminate()
    }

    func testBackgroundAndForegroundReopenTheOwnedRuntime() {
        let app = XCUIApplication()
        app.launchArguments = ["--native-ui-tests"]
        app.launch()
        XCTAssertTrue(app.buttons["יצירת חשבון חדש"].waitForExistence(timeout: 30))
        XCUIDevice.shared.press(.home)
        app.activate()
        XCTAssertTrue(app.buttons["יצירת חשבון חדש"].waitForExistence(timeout: 30))
        XCTAssertTrue(app.secureTextFields["ביטוי שחזור"].exists)
        app.terminate()
    }
}
