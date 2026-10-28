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
        completeFreshLocalOnlyOnboardingIfNeeded()

        let body = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "pinkha.stage1.body.")
        ).firstMatch
        guard body.waitForExistence(timeout: 300) else {
            attachScreenshot(named: "FAIL-production-editor-body-missing")
            XCTFail("Production editor body UITextView did not appear")
            return
        }
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

    private func completeFreshLocalOnlyOnboardingIfNeeded() {
        let join = button(namedAny: ["I am new here", "אני חדש כאן"])
        guard join.waitForExistence(timeout: 30) else {
            return
        }

        let labelledSettings = button(namedAny: ["Space settings", "הגדרות מרחב"])
        let settings = labelledSettings.exists ? labelledSettings : app.buttons.element(boundBy: 0)
        XCTAssertTrue(settings.waitForExistence(timeout: 5), "Network settings button did not appear")
        settings.tap()

        let localOnly = button(namedAny: ["Local-only", "מקומי בלבד"])
        XCTAssertTrue(localOnly.waitForExistence(timeout: 15), "Local-only network option did not appear")
        localOnly.tap()

        let acceptLocalOnly = button(namedAny: ["Yes, I accept risks", "הבנתי, המשך"])
        XCTAssertTrue(acceptLocalOnly.waitForExistence(timeout: 10), "Local-only confirmation did not appear")
        acceptLocalOnly.tap()

        // Querying the sheet accessibility node can block for minutes on the iPad simulator
        // while Anytype is applying the local-only network change. A direct application-level
        // dismissal exercises the same real UI gesture and worked on both form factors without
        // depending on a snapshot of the transient sheet hierarchy.
        app.swipeDown(velocity: .fast)
        XCTAssertTrue(join.waitForExistence(timeout: 15), "Authentication screen did not return")
        join.tap()

        let notNow = button(namedAny: ["Not now", "לא עכשיו"])
        XCTAssertTrue(notNow.waitForExistence(timeout: 240), "Local-only account creation did not finish")
        notNow.tap()

        let personaTitle = staticText(namedAny: ["Tell Us About Yourself", "ספר לנו על עצמך"])
        XCTAssertTrue(personaTitle.waitForExistence(timeout: 15), "Persona onboarding step did not appear")
        let skip = app.buttons["Skip"]
        XCTAssertTrue(skip.waitForExistence(timeout: 5), "Persona Skip button did not appear")
        skip.tap()

        let useCaseTitle = staticText(namedAny: [
            "What do you want to use Anytype for?",
            "לשם מה תרצה להשתמש ב-Anytype?"
        ])
        XCTAssertTrue(useCaseTitle.waitForExistence(timeout: 15), "Use-case onboarding step did not appear")
        XCTAssertTrue(skip.waitForExistence(timeout: 5), "Use-case Skip button did not appear")
        skip.tap()

        let defaultSpace = button(containingAny: ["My First Space", "המרחב הראשון שלי"])
        XCTAssertTrue(defaultSpace.waitForExistence(timeout: 90), "Local-only default Space did not appear")
        defaultSpace.tap()
        XCTAssertTrue(
            defaultSpace.waitForNonExistence(timeout: 30),
            "Tapping the default Space card did not leave Space Hub"
        )
        attachScreenshot(named: "real-space-opened-before-document")
    }

    private func button(namedAny labels: [String]) -> XCUIElement {
        app.buttons.matching(NSPredicate(format: "label IN %@", labels)).firstMatch
    }

    private func button(containingAny labels: [String]) -> XCUIElement {
        let predicates = labels.map { NSPredicate(format: "label CONTAINS %@", $0) }
        return app.buttons.matching(NSCompoundPredicate(orPredicateWithSubpredicates: predicates)).firstMatch
    }

    private func staticText(namedAny labels: [String]) -> XCUIElement {
        app.staticTexts.matching(NSPredicate(format: "label IN %@", labels)).firstMatch
    }

    private func attachScreenshot(named name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
