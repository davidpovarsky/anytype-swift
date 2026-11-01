import XCTest

@MainActor
final class PinkhaStage1AcceptanceUITests: XCTestCase {
    private enum DocumentKind: String, CaseIterable {
        case pinkha
        case note
        case page
    }

    private let app = XCUIApplication()
    private var expectsRTL: Bool {
        ProcessInfo.processInfo.environment["PINKHA_ACCEPTANCE_DIRECTION"] != "ltr"
    }
    private var appLanguage: String { expectsRTL ? "he" : "en" }
    private var deviceLanguage: String {
        ProcessInfo.processInfo.environment["PINKHA_ACCEPTANCE_DEVICE_LANGUAGE"]
            ?? (expectsRTL ? "en" : "he")
    }

    override func setUp() {
        continueAfterFailure = false
        app.launchEnvironment["PINKHA_STAGE1_ACCEPTANCE"] = "1"
        app.launchEnvironment["PINKHA_ACCEPTANCE_DEVICE_LANGUAGE"] = deviceLanguage
        app.launchArguments += [
            "-AppleLanguages", "(\(appLanguage))",
            "-AppleLocale", expectsRTL ? "he_IL" : "en_US"
        ]
    }

    func testAppWideDirectionPersistenceAndInteractiveBack() throws {
        XCTAssertNotEqual(
            appLanguage,
            deviceLanguage,
            "Acceptance must exercise mismatched app and device languages"
        )

        launch(document: .pinkha)
        completeFreshLocalOnlyOnboardingIfNeeded()

        for kind in DocumentKind.allCases {
            if kind != .pinkha {
                launch(document: kind)
            }
            try exerciseDocument(kind)
        }
    }

    func testMultiBlockEnterCreationAndTypingLifecycle() throws {
        XCTAssertNotEqual(
            appLanguage,
            deviceLanguage,
            "Acceptance must exercise mismatched app and device languages"
        )

        launch(document: .pinkha)
        completeFreshLocalOnlyOnboardingIfNeeded()

        for kind in DocumentKind.allCases {
            if kind != .pinkha {
                launch(document: kind)
            }
            try exerciseMultiBlockEnterLifecycle(kind)
        }
    }

    func testDocumentSourcesEntryOpensExistingSearch() throws {
        launch(document: .pinkha)
        completeFreshLocalOnlyOnboardingIfNeeded()
        for kind in DocumentKind.allCases {
            if kind != .pinkha { launch(document: kind) }
            openDocumentIfNeeded(kind)
            XCTAssertTrue(editorBody().waitForExistence(timeout: 60))
            let add = app.buttons["torah-document-sources-add"]
            XCTAssertTrue(add.waitForExistence(timeout: 20))
            XCTAssertEqual(app.buttons.matching(identifier: "torah-document-sources-add").count, 1)
            XCTAssertTrue(add.isHittable)
            attachScreenshot(named: "\(directionName)-\(kind.rawValue)-sources-entry")
            add.tap()
            let field = app.descendants(matching: .any)["torah-sources-search-field"].firstMatch
            XCTAssertTrue(field.waitForExistence(timeout: 20), "Sources must open the existing document search presenter")
            attachScreenshot(named: "\(directionName)-\(kind.rawValue)-sources-search")
        }
    }

    private func exerciseMultiBlockEnterLifecycle(_ kind: DocumentKind) throws {
        openDocumentIfNeeded(kind)
        var target = editorBody()
        XCTAssertTrue(target.waitForExistence(timeout: 60))
        target.tap()

        let token = UUID().uuidString.prefix(8)
        let lines = (1...5).map { index in
            expectsRTL ? "שורה \(index) בדיקה \(token)" : "Line \(index) test \(token)"
        }
        var typedBlockIDs = Set<String>()
        for line in lines {
            target.typeText(line)
            let typedRow = editorBody(containing: line)
            XCTAssertTrue(typedRow.waitForExistence(timeout: 20), "Entered line missing: \(line)")
            XCTAssertTrue(typedBlockIDs.insert(typedRow.identifier).inserted, "Enter reused a previously typed block")
            assertRuntimeDirection(on: typedRow, document: kind)

            typedRow.typeText("\n")
            target = app.textViews.matching(NSPredicate(
                format: "identifier BEGINSWITH %@ AND NOT (identifier IN %@) AND label CONTAINS %@",
                "pinkha.stage1.body.",
                Array(typedBlockIDs),
                "first-responder-true"
            )).firstMatch
            XCTAssertTrue(target.waitForExistence(timeout: 20), "Enter did not focus a distinct next block")
            assertRuntimeDirection(on: target, document: kind)
            let direction = expectsRTL ? "rtl" : "ltr"
            let side = expectsRTL ? "right" : "left"
            for fragment in ["typing-direction-\(direction)", "caret-side-\(side)"] {
                expectation(for: NSPredicate(format: "label CONTAINS %@", fragment), evaluatedWith: target)
            }
            waitForExpectations(timeout: 20)
            attachScreenshot(named: "\(directionName)-\(kind.rawValue)-enter-\(typedBlockIDs.count)")
        }
        XCTAssertEqual(typedBlockIDs.count, 5)

        launch(document: kind)
        openDocumentIfNeeded(kind)
        var reopenedIDs = Set<String>()
        for line in lines {
            let row = editorBody(containing: line)
            XCTAssertTrue(row.waitForExistence(timeout: 60), "Line did not survive relaunch: \(line)")
            XCTAssertTrue(reopenedIDs.insert(row.identifier).inserted)
            assertRuntimeDirection(on: row, document: kind)
        }
        XCTAssertEqual(reopenedIDs, typedBlockIDs, "Enter-created block identities changed after relaunch")
        attachScreenshot(named: "\(directionName)-\(kind.rawValue)-multiblock-reopened")
    }

    private func editorBody(containing text: String) -> XCUIElement {
        app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value CONTAINS %@",
            "pinkha.stage1.body.",
            text
        )).firstMatch
    }

    private func exerciseDocument(_ kind: DocumentKind) throws {
        openDocumentIfNeeded(kind)
        let body = editorBody()
        guard body.waitForExistence(timeout: 300) else {
            attachScreenshot(named: "FAIL-\(kind.rawValue)-editor-body-missing")
            XCTFail("Production editor body UITextView did not appear for \(kind.rawValue)")
            return
        }
        body.tap()
        let enteredText = text(for: kind)
        body.typeText(enteredText)

        assertRuntimeDirection(on: body, document: kind)
        attachScreenshot(named: "\(directionName)-\(kind.rawValue)-entry")

        let window = app.windows.firstMatch
        XCTAssertTrue(window.exists)
        performInteractiveBack(
            in: window,
            body: body,
            startX: 0.50,
            cancelledEndX: expectsRTL ? 0.38 : 0.62,
            completedEndX: expectsRTL ? 0.05 : 0.95,
            evidencePrefix: "\(directionName)-\(kind.rawValue)-full-screen"
        )

        launch(document: kind)
        openDocumentIfNeeded(kind)
        let bodyAfterFullScreenPop = editorBody()
        XCTAssertTrue(bodyAfterFullScreenPop.waitForExistence(timeout: 60))
        assertRuntimeDirection(on: bodyAfterFullScreenPop, document: kind)

        performInteractiveBack(
            in: app.windows.firstMatch,
            body: bodyAfterFullScreenPop,
            startX: expectsRTL ? 0.995 : 0.005,
            cancelledEndX: expectsRTL ? 0.86 : 0.14,
            completedEndX: expectsRTL ? 0.18 : 0.82,
            evidencePrefix: "\(directionName)-\(kind.rawValue)-edge"
        )

        launch(document: kind)
        openDocumentIfNeeded(kind)
        let reopenedBody = editorBody()
        XCTAssertTrue(reopenedBody.waitForExistence(timeout: 60), "\(kind.rawValue) did not reopen")
        assertRuntimeDirection(on: reopenedBody, document: kind)
        XCTAssertTrue(
            String(describing: reopenedBody.value).contains(enteredText),
            "Entered text did not survive close and reopen for \(kind.rawValue)"
        )
        attachScreenshot(named: "\(directionName)-\(kind.rawValue)-reopened")
    }

    private func openDocumentIfNeeded(_ kind: DocumentKind) {
        let expectedTitle = documentTitle(for: kind)
        let titleField = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "pinkha.stage1.title.")
        ).firstMatch

        if titleField.exists {
            let currentTitle = String(describing: titleField.value)
            if currentTitle.contains(expectedTitle) {
                return
            }
            let back = button(namedAny: ["Back", "חזרה"])
            if back.exists {
                back.tap()
            }
        }

        let docButton = button(containingAny: [expectedTitle])
        if docButton.waitForExistence(timeout: 8) {
            docButton.tap()
            return
        }
        let docText = staticText(namedAny: [expectedTitle])
        if docText.waitForExistence(timeout: 5) {
            docText.tap()
            return
        }

        let searchButton = app.buttons.matching(
            NSPredicate(format: "identifier CONTAINS[c] 'search' OR label CONTAINS[c] 'search'")
        ).firstMatch
        if searchButton.waitForExistence(timeout: 4) {
            searchButton.tap()
            let searchField = app.textFields.firstMatch
            if searchField.waitForExistence(timeout: 8) {
                searchField.typeText(expectedTitle)
                let result = button(containingAny: [expectedTitle])
                if result.waitForExistence(timeout: 8) {
                    result.tap()
                    return
                }
            }
            let cancel = button(namedAny: ["Cancel", "ביטול"])
            if cancel.exists { cancel.tap() }
        }

        let createButton = app.buttons.matching(
            NSPredicate(format: "identifier CONTAINS[c] 'create' OR label CONTAINS[c] 'create'")
        ).firstMatch
        if createButton.waitForExistence(timeout: 8) {
            createButton.tap()
            switch kind {
            case .page:
                let pageOption = button(containingAny: ["Page", "עמוד"])
                if pageOption.waitForExistence(timeout: 6) {
                    pageOption.tap()
                }
            case .note:
                let noteOption = button(containingAny: ["Note", "פתק"])
                if noteOption.waitForExistence(timeout: 6) {
                    noteOption.tap()
                }
            case .pinkha:
                let moreOption = button(containingAny: ["More", "עוד"])
                if moreOption.waitForExistence(timeout: 6) {
                    moreOption.tap()
                }
                let chiddushOption = button(containingAny: ["חידוש", "Chiddush"])
                if chiddushOption.waitForExistence(timeout: 8) {
                    chiddushOption.tap()
                }
            }
            if titleField.waitForExistence(timeout: 10) {
                titleField.tap()
                titleField.typeText(expectedTitle + "\n")
            }
        }
    }

    private func documentTitle(for kind: DocumentKind) -> String {
        switch kind {
        case .pinkha:
            return "בדיקת RTL Stage 1"
        case .note:
            return "RTL Acceptance Ordinary Note"
        case .page:
            return "RTL Acceptance Ordinary Page"
        }
    }

    private func assertRuntimeDirection(
        on body: XCUIElement,
        document kind: DocumentKind
    ) {
        let direction = expectsRTL ? "rtl" : "ltr"
        let alignment = expectsRTL ? "right" : "left"
        let requiredFragments = [
            "document-\(kind.rawValue)",
            "app-language-\(appLanguage)",
            "device-language-requested-\(deviceLanguage)",
            "swiftui-\(direction)",
            "navigation-\(direction)",
            "uikit-\(direction)",
            "alignment-\(alignment)"
        ]
        let predicates = requiredFragments.map {
            NSPredicate(format: "label CONTAINS %@", $0)
        }
        expectation(
            for: NSCompoundPredicate(andPredicateWithSubpredicates: predicates),
            evaluatedWith: body
        )
        waitForExpectations(timeout: 20)
    }

    private func launch(document kind: DocumentKind) {
        if app.state != .notRunning {
            app.terminate()
        }
        app.launchEnvironment["PINKHA_ACCEPTANCE_DOCUMENT_KIND"] = kind.rawValue
        app.launch()
    }

    private func performInteractiveBack(
        in window: XCUIElement,
        body: XCUIElement,
        startX: CGFloat,
        cancelledEndX: CGFloat,
        completedEndX: CGFloat,
        evidencePrefix: String
    ) {
        let start = window.coordinate(withNormalizedOffset: CGVector(dx: startX, dy: 0.52))
        let cancelledEnd = window.coordinate(withNormalizedOffset: CGVector(dx: cancelledEndX, dy: 0.52))
        start.press(
            forDuration: 0.08,
            thenDragTo: cancelledEnd,
            withVelocity: .slow,
            thenHoldForDuration: 0.05
        )
        XCTAssertTrue(body.waitForExistence(timeout: 5), "A short back swipe should cancel and keep the editor")
        attachScreenshot(named: "\(evidencePrefix)-cancelled")

        let completedEnd = window.coordinate(withNormalizedOffset: CGVector(dx: completedEndX, dy: 0.52))
        start.press(
            forDuration: 0.08,
            thenDragTo: completedEnd,
            withVelocity: .slow,
            thenHoldForDuration: 0.05
        )
        XCTAssertTrue(body.waitForNonExistence(timeout: 12), "A completed interactive back swipe did not pop")
        attachScreenshot(named: "\(evidencePrefix)-completed")
    }

    private func editorBody() -> XCUIElement {
        app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "pinkha.stage1.body.")
        ).firstMatch
    }

    private func text(for kind: DocumentKind) -> String {
        if expectsRTL {
            return "טקסט \(kind.rawValue) בעברית"
        }
        return "English \(kind.rawValue) acceptance text"
    }

    private var directionName: String { expectsRTL ? "RTL" : "LTR" }

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

        app.swipeDown(velocity: .fast)
        XCTAssertTrue(join.waitForExistence(timeout: 15), "Authentication screen did not return")
        join.tap()

        let notNow = button(namedAny: ["Not now", "לא עכשיו"])
        XCTAssertTrue(notNow.waitForExistence(timeout: 240), "Local-only account creation did not finish")
        for _ in 0..<3 where notNow.exists {
            notNow.tap()
            if notNow.waitForNonExistence(timeout: 10) {
                break
            }
        }
        XCTAssertTrue(
            notNow.waitForNonExistence(timeout: 15),
            "Dismissing the recovery-key screen did not advance onboarding"
        )

        let personaTitle = staticText(namedAny: ["Tell Us About Yourself", "ספר לנו על עצמך"])
        XCTAssertTrue(personaTitle.waitForExistence(timeout: 30), "Persona onboarding step did not appear")
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
