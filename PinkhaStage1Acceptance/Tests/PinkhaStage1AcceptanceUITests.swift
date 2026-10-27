import XCTest

@MainActor
final class PinkhaStage1AcceptanceUITests: XCTestCase {
    private let app = XCUIApplication()
    private var expectsRTL: Bool {
        ProcessInfo.processInfo.environment["PINKHA_ACCEPTANCE_DIRECTION"] != "ltr"
    }

    override func setUp() {
        continueAfterFailure = false
        app.launchEnvironment["PINKHA_STAGE1_ACCEPTANCE"] = "1"
        if expectsRTL {
            app.launchArguments += [
                "-AppleLanguages", "(he)",
                "-AppleLocale", "he_IL",
                "-NSForceRightToLeftWritingDirection", "YES",
                "-NSForceRightToLeftLayoutDirection", "YES"
            ]
        } else {
            app.launchArguments += [
                "-AppleLanguages", "(en)",
                "-AppleLocale", "en_US",
                "-NSForceRightToLeftWritingDirection", "NO",
                "-NSForceRightToLeftLayoutDirection", "NO"
            ]
        }
    }

    func testEntryPersistenceAndInteractiveBackInRealDocument() throws {
        app.launch()

        let space = app.staticTexts["Pinkha Stage 1 RTL Acceptance"]
        XCTAssertTrue(space.waitForExistence(timeout: 45), "Disposable local-only Space did not appear")
        space.tap()

        let body = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "pinkha.stage1.body.")
        ).firstMatch
        XCTAssertTrue(body.waitForExistence(timeout: 45), "Production editor body UITextView did not appear")
        body.tap()
        let enteredText = expectsRTL
            ? "שלום עולם מתוך מסמך אמיתי"
            : "English text in a real Pinkha document"
        body.typeText(enteredText)

        let expectedDirection = expectsRTL ? "rtl" : "ltr"
        let expectedAlignment = expectsRTL ? "alignment-right" : "alignment-left"
        let expectedStyle = NSPredicate(
            format: "label CONTAINS %@ AND label CONTAINS %@",
            expectedDirection,
            expectedAlignment
        )
        expectation(for: expectedStyle, evaluatedWith: body)
        waitForExpectations(timeout: 15)
        attachScreenshot(named: expectsRTL ? "RTL-01-real-hebrew-entry" : "RTL-02-real-ltr-entry")

        let window = app.windows.firstMatch
        XCTAssertTrue(window.exists)
        let start = window.coordinate(withNormalizedOffset: CGVector(
            dx: expectsRTL ? 0.995 : 0.22,
            dy: 0.52
        ))
        let shortDrag = window.coordinate(withNormalizedOffset: CGVector(
            dx: expectsRTL ? 0.84 : 0.37,
            dy: 0.52
        ))
        start.press(
            forDuration: 0.08,
            thenDragTo: shortDrag,
            withVelocity: .slow,
            thenHoldForDuration: 0.05
        )
        XCTAssertTrue(body.waitForExistence(timeout: 5), "A short back swipe should cancel and keep the editor")
        attachScreenshot(named: expectsRTL ? "NAV-02-rtl-cancelled" : "NAV-03-ltr-cancelled")

        let completedDrag = window.coordinate(withNormalizedOffset: CGVector(
            dx: expectsRTL ? 0.18 : 0.86,
            dy: 0.52
        ))
        start.press(
            forDuration: 0.08,
            thenDragTo: completedDrag,
            withVelocity: .slow,
            thenHoldForDuration: 0.05
        )
        XCTAssertTrue(body.waitForNonExistence(timeout: 12), "A completed interactive back swipe did not pop")
        attachScreenshot(named: expectsRTL ? "NAV-01-rtl-completed" : "NAV-03-ltr-completed")

        let document = app.staticTexts["בדיקת RTL Stage 1"]
        XCTAssertTrue(document.waitForExistence(timeout: 20), "Created document was not visible after back")
        document.tap()

        let reopenedBody = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "pinkha.stage1.body.")
        ).firstMatch
        XCTAssertTrue(reopenedBody.waitForExistence(timeout: 30), "Document did not reopen")
        expectation(for: expectedStyle, evaluatedWith: reopenedBody)
        waitForExpectations(timeout: 15)
        XCTAssertTrue(
            String(describing: reopenedBody.value).contains(expectsRTL ? "שלום עולם" : "English text"),
            "Entered text did not survive close and reopen"
        )
        attachScreenshot(named: expectsRTL ? "RTL-03-reopened-persisted" : "RTL-04-ltr-reopened")
    }

    private func attachScreenshot(named name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
