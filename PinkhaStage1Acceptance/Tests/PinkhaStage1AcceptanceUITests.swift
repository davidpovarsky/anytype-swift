import XCTest

@MainActor
final class PinkhaStage1AcceptanceUITests: XCTestCase {
    private enum DocumentKind: String, CaseIterable, Hashable {
        case pinkha
        case note
        case page
    }

    private let app = XCUIApplication()
    private var fixtureSpaceID = ""
    private var fixtureObjectIDs: [DocumentKind: String] = [:]
    private var expectsRTL: Bool {
        ProcessInfo.processInfo.environment["PINKHA_ACCEPTANCE_DIRECTION"] != "ltr"
    }
    private var appLanguage: String { expectsRTL ? "he" : "en" }
    private var deviceLanguage: String {
        ProcessInfo.processInfo.environment["PINKHA_ACCEPTANCE_DEVICE_LANGUAGE"]
            ?? (expectsRTL ? "en" : "he")
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
        let environment = ProcessInfo.processInfo.environment
        fixtureSpaceID = try XCTUnwrap(environment["PINKHA_ACCEPTANCE_SPACE_ID"], "Native fixture preparation must supply the disposable Space")
        let fixtureKeys: [(DocumentKind, String)] = [
            (.pinkha, "PINKHA_ACCEPTANCE_PINKHA_ID"),
            (.note, "PINKHA_ACCEPTANCE_NOTE_ID"),
            (.page, "PINKHA_ACCEPTANCE_PAGE_ID")
        ]
        for (kind, key) in fixtureKeys {
            fixtureObjectIDs[kind] = try XCTUnwrap(environment[key], "Missing prepared native \(kind.rawValue) fixture")
        }
        XCTAssertFalse(fixtureSpaceID.isEmpty)
        XCTAssertEqual(Set(fixtureObjectIDs.values).count, 3)
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

        for kind in DocumentKind.allCases {
            if kind != .pinkha {
                launch(document: kind)
            }
            try exerciseMultiBlockEnterLifecycle(kind)
        }
    }

    func testDocumentSourcesEntryOpensExistingSearch() throws {
        launch(document: .pinkha)
        for kind in DocumentKind.allCases {
            if kind != .pinkha { launch(document: kind) }
            openDocumentIfNeeded(kind)
            _ = editableBody()
            let add = app.buttons["torah-document-sources-add"]
            XCTAssertTrue(add.waitForExistence(timeout: 20))
            XCTAssertEqual(app.buttons.matching(identifier: "torah-document-sources-add").count, 1)
            XCTAssertTrue(add.isHittable)
            attachScreenshot(named: "\(directionName)-\(kind.rawValue)-sources-entry")
            add.tap()
            let field = app.descendants(matching: .any).matching(identifier: "torah-sources-search-field").firstMatch
            XCTAssertTrue(field.waitForExistence(timeout: 20), "Sources must open the existing document search presenter")
            attachScreenshot(named: "\(directionName)-\(kind.rawValue)-sources-search")
        }
    }

    private func exerciseMultiBlockEnterLifecycle(_ kind: DocumentKind) throws {
        openDocumentIfNeeded(kind)
        var target = editableBody(startNewTrailingBlock: true)
        target.tap()

        let token = UUID().uuidString.prefix(8)
        let lines = (1...5).map { index in
            let usesHebrew = expectsRTL ? !index.isMultiple(of: 2) : index.isMultiple(of: 2)
            return usesHebrew ? "שורה \(index) בדיקה \(token)" : "Line \(index) test \(token)"
        }
        var typedBlockIDs = Set<String>()
        for (index, line) in lines.enumerated() {
            target.typeText(line)
            let typedRow = editorBody(containing: line)
            XCTAssertTrue(typedRow.waitForExistence(timeout: 20), "Entered line missing: \(line)")
            XCTAssertTrue(typedBlockIDs.insert(typedRow.identifier).inserted, "Enter reused a previously typed block")
            assertRuntimeDirection(on: typedRow, document: kind)
            if index > 0 {
                let direction = expectsRTL ? "rtl" : "ltr"
                expectation(for: NSPredicate(format: "label CONTAINS %@", "accepted-first-insertion-\(direction)"), evaluatedWith: typedRow)
                waitForExpectations(timeout: 20)
            }

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
            for fragment in ["text-empty-true", "typing-direction-\(direction)", "caret-side-\(side)"] {
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
        var body = editableBody(startNewTrailingBlock: true)
        guard body.waitForExistence(timeout: 300) else {
            attachScreenshot(named: "FAIL-\(kind.rawValue)-editor-body-missing")
            XCTFail("Production editor body UITextView did not appear for \(kind.rawValue)")
            return
        }
        body.tap()
        let enteredText = text(for: kind)
        body.typeText(enteredText)
        body = editorBody(containing: enteredText)
        XCTAssertTrue(body.waitForExistence(timeout: 20))

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
        let bodyAfterFullScreenPop = editorBody(containing: enteredText)
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
        let reopenedBody = editorBody(containing: enteredText)
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
        let titleFields = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "pinkha.stage1.title.")
        )
        let identity = kind == .note ? editorBody(containing: expectedTitle) : app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@ AND value CONTAINS %@", "pinkha.stage1.title.", expectedTitle)
        ).firstMatch
        if identity.exists { return }

        guard let objectID = fixtureObjectIDs[kind] else {
            XCTFail("Missing prepared native document ID")
            return
        }
        var components = URLComponents()
        components.scheme = "anytype"
        components.host = "object"
        components.queryItems = [
            URLQueryItem(name: "objectId", value: objectID),
            URLQueryItem(name: "spaceId", value: fixtureSpaceID)
        ]
        guard let url = components.url else {
            XCTFail("Could not form the original native object deeplink")
            return
        }
        print("PINKHA_ACCEPTANCE_OPEN kind=\(kind.rawValue) space=\(fixtureSpaceID) object=\(objectID)")
        app.open(url)

        if kind == .note {
            // Native Note has no title. Wait for the previous Page to leave before seeding
            // the Note's first body through real input, never into the previous document.
            XCTAssertTrue(titleFields.firstMatch.waitForNonExistence(timeout: 60))
            let body = editableBody()
            if !identity.exists {
                body.tap()
                body.typeText(expectedTitle + "\n")
            }
        }
        XCTAssertTrue(identity.waitForExistence(timeout: 60), "Prepared native \(kind.rawValue) fixture did not open")
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
        let bodies = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "pinkha.stage1.body.")
        )
        // Keep the Note's stable first-line identity intact while editing later content.
        return bodies.element(boundBy: max(0, bodies.count - 1))
    }

    private func editableBody(startNewTrailingBlock: Bool = false) -> XCUIElement {
        let body = editorBody()
        if !startNewTrailingBlock, body.waitForExistence(timeout: 3) { return body }

        // A newly opened native document can contain metadata without a body row. The
        // original editor creates its virtual trailing row only after a tap below content.
        // Exercise that user path; never create a persisted fixture block or change focus.
        let editor = app.collectionViews.containing(.button, identifier: "torah-document-sources-add").firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 20))
        let contentBottom = editor.cells.allElementsBoundByIndex.map { $0.frame.maxY }.max() ?? editor.frame.minY
        let keyboard = app.keyboards.firstMatch
        let visibleBottom = keyboard.exists ? min(editor.frame.maxY, keyboard.frame.minY) : editor.frame.maxY
        XCTAssertGreaterThan(visibleBottom - contentBottom, 24, "A safe native empty area is required before tapping")
        let y = contentBottom + (visibleBottom - contentBottom) * 0.5
        editor.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(
            dx: editor.frame.width * 0.5, dy: y - editor.frame.minY
        )).tap()
        let created = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND label CONTAINS %@ AND label CONTAINS %@",
            "pinkha.stage1.body.", "first-responder-true", "text-empty-true"
        )).firstMatch
        XCTAssertTrue(created.waitForExistence(timeout: 20), "Native empty-area tap did not expose a trailing editor row")
        return created
    }

    private func text(for kind: DocumentKind) -> String {
        if expectsRTL {
            return "טקסט \(kind.rawValue) בעברית"
        }
        return "English \(kind.rawValue) acceptance text"
    }

    private var directionName: String { expectsRTL ? "RTL" : "LTR" }

    private func attachScreenshot(named name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
