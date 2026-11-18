import XCTest

/// Exercises the real source reader, native quote insertion and UIKit drop path.
/// All account, Space and document IDs come from the native disposable fixture.
@MainActor
final class PinkhaTorahQuoteAcceptanceUITests: XCTestCase {
    private struct Fixture: Decodable {
        let spaceId: String
        let universalDocuments: [String: String]
        let manySourcesDocument: String
    }

    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private let sourceRef = "Genesis 1:1"
    private let bodyPrefix = "pinkha.stage1.body."
    private var fixture: Fixture!

    override func setUpWithError() throws {
        continueAfterFailure = false
        let env = ProcessInfo.processInfo.environment
        try require(env["PINKHA_NATIVE_UI_DISPOSABLE"] == "1", "A fresh disposable native fixture is required")
        try require(env["PINKHA_UI27_APP_LANGUAGE"] == "en", "This selection currently proves English UI only")
        let raw = try XCTUnwrap(env["PINKHA_NATIVE_UI_FIXTURE_JSON"])
        fixture = try JSONDecoder().decode(Fixture.self, from: Data(raw.utf8))
        try require(!fixture.spaceId.isEmpty && !fixture.manySourcesDocument.isEmpty, "Fixture identity is missing")
        try require(fixture.universalDocuments["page"] != fixture.manySourcesDocument,
                    "The source-bearing document must be distinct from the blank Page")
        app.launchEnvironment["PINKHA_STAGE1_ACCEPTANCE"] = "1"
        app.launchEnvironment["PINKHA_ACCEPTANCE_DOCUMENT_KIND"] = "pinkha"
        app.launchEnvironment["PINKHA_UI27_ROUTE_OBSERVATION"] = "1"
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
    }

    func testNativeQuoteUndoRedoDragAndRelaunch() throws {
        defer { attachEvidence("quote-drop-final") }
        try launchSourceDocument()
        let anchorText = "Wave15 drop anchor " + UUID().uuidString
        let anchorID = try createAnchor(anchorText)

        let reader = try openSourceReader()
        let sourceText = reader.label
        try require(!sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                    "The real provider must supply source text before insertion")
        try require(sourceText != sourceRef, "A reference label is not source text")
        try require(quoteRows(sourceText).count == 0, "The disposable document unexpectedly already contains this quote")
        attachEvidence("quote-reader-before-context-menu")

        reader.press(forDuration: 1.0)
        let insert = element(identifier: "torah-reader-insert-" + sourceRef)
        try require(insert.waitForExistence(timeout: 20) && insert.isHittable,
                    "The original Insert action was not available in the source context menu")
        insert.tap()
        try require(insert.waitForNonExistence(timeout: 20), "The insertion context menu did not finish dismissing")
        // Keep this Inspector lifetime alive until both native text and source
        // metadata are observable; dismissal intentionally cancels pending work.
        let originalIDs = try requireQuotes(sourceText, count: 1)
        try closeInspector()
        try require(try requireQuotes(sourceText, count: 1) == originalIDs,
                    "Closing the completed Inspector changed the native quote")
        let originalID = try XCTUnwrap(originalIDs.first)
        try requireBody(anchorID, text: anchorText)
        attachEvidence("quote-native-insert-and-citation")

        try performHistoryAction("editor-undo")
        try require(quoteRows(sourceText).firstMatch.waitForNonExistence(timeout: 20),
                    "One native Undo must remove the inserted quote")
        try require(element(identifier: "torah-linked-source-" + blockID(originalID)).waitForNonExistence(timeout: 20),
                    "Undo left a source ornament for the removed block")
        try requireBody(anchorID, text: anchorText)
        attachEvidence("quote-native-undo")

        try performHistoryAction("editor-redo")
        let restoredIDs = try requireQuotes(sourceText, count: 1)
        try require(restoredIDs == originalIDs, "Redo did not restore the quote's native block identity and citation")
        try requireBody(anchorID, text: anchorText)
        attachEvidence("quote-native-redo")
        try proveEditableFocus(on: originalID)

        // Two deliberate gestures of the same source must each insert exactly one
        // new block. A lifetime-wide payload deduplicator fails the second gesture.
        for count in 2...3 {
            let source = try openSourceReader()
            try require(source.label == sourceText, "The selected source changed between insertion gestures")
            let target = body(identifier: anchorID)
            try require(target.waitForExistence(timeout: 20) && target.isHittable,
                        "The existing native drop target is not reachable beside the Inspector")
            try require(source.isHittable, "The real draggable source row is not reachable")
            attachEvidence("quote-drag-\(count)-before")
            let start = source.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
            let end = target.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
            start.press(forDuration: 1.0, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.5)
            try closeInspector()
            let ids = try requireQuotes(sourceText, count: count)
            try require(ids.contains(originalID), "A drop replaced the existing quote")
            try requireBody(anchorID, text: anchorText)
            attachEvidence("quote-drag-\(count)-complete")
        }

        let savedIDs = try requireQuotes(sourceText, count: 3)
        XCUIDevice.shared.press(.home)
        try require(app.wait(for: .runningBackground, timeout: 20) || app.state == .runningBackgroundSuspended,
                    "The app did not enter the background")
        app.activate()
        try require(app.wait(for: .runningForeground, timeout: 20), "The app did not return to the foreground")
        try requireCurrentDocument()
        try require(try requireQuotes(sourceText, count: 3) == savedIDs,
                    "Background/foreground changed or duplicated quote blocks")
        try requireBody(anchorID, text: anchorText)
        attachEvidence("quote-background-foreground")

        try launchSourceDocument()
        let reopenedIDs = try requireQuotes(sourceText, count: 3)
        try require(reopenedIDs == savedIDs, "Relaunch changed quote identity or created duplicate writes")
        try requireBody(anchorID, text: anchorText)
        try proveEditableFocus(on: anchorID)
        attachEvidence("quote-reopened-native-blocks-and-citations")
    }

    private func launchSourceDocument() throws {
        if app.state != .notRunning { app.terminate() }
        app.launch()
        let ready = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ OR label == %@ OR identifier == %@ OR label == %@ OR (elementType == %d AND (label == %@ OR label == %@))",
            "SpaceHub", "SpaceHub", "NewSpaceButton", "NewSpaceButton",
            XCUIElement.ElementType.button.rawValue, "More", "x24/More"
        )).firstMatch
        try require(ready.waitForExistence(timeout: 120), "Native Home did not become ready before document routing")
        var url = URLComponents()
        url.scheme = "anytype"
        url.host = "object"
        url.queryItems = [
            URLQueryItem(name: "spaceId", value: fixture.spaceId),
            URLQueryItem(name: "objectId", value: fixture.manySourcesDocument)
        ]
        XCUIDevice.shared.system.open(try XCTUnwrap(url.url))
        try requireCurrentDocument()
        try require(app.buttons["torah-document-sources-add"].waitForExistence(timeout: 30),
                    "The prepared native document lost its Sources property")
    }

    private func requireCurrentDocument() throws {
        let id = "pinkha-ui27-editor:\(fixture.spaceId):\(fixture.manySourcesDocument)"
        let matches = app.descendants(matching: .any).matching(NSPredicate(format: "identifier == %@", id))
        try require(matches.firstMatch.waitForExistence(timeout: 45) && matches.count == 1,
                    "Exactly one editor must match the disposable Space and document")
        try require(matches.firstMatch.isHittable, "The intended native editor is obscured")
    }

    private func createAnchor(_ text: String) throws -> String {
        let existing = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@", bodyPrefix, ""
        )).firstMatch
        if existing.exists && existing.isHittable {
            existing.tap()
        } else {
            let editor = app.collectionViews.containing(.button, identifier: "torah-document-sources-add").firstMatch
            try require(editor.waitForExistence(timeout: 20), "The production editor collection is missing")
            let bottom = editor.cells.allElementsBoundByIndex.map { $0.frame.maxY }.max() ?? editor.frame.minY
            let keyboard = app.keyboards.firstMatch
            let visibleBottom = keyboard.exists ? min(editor.frame.maxY, keyboard.frame.minY) : editor.frame.maxY
            try require(visibleBottom - bottom > 24, "No visible native trailing-block insertion area")
            editor.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(
                dx: editor.frame.width * 0.5, dy: bottom + (visibleBottom - bottom) * 0.5 - editor.frame.minY
            )).tap()
        }
        let focused = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND label CONTAINS %@ AND label CONTAINS %@",
            bodyPrefix, "first-responder-true", "text-empty-true"
        )).firstMatch
        try require(focused.waitForExistence(timeout: 20), "Native input did not focus an empty body")
        focused.typeText(text)
        let anchor = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@", bodyPrefix, text
        )).firstMatch
        try require(anchor.waitForExistence(timeout: 20), "Typing did not create the native anchor block")
        try require(!blockID(anchor.identifier).isEmpty, "The typed block has no stable native identity")
        return anchor.identifier
    }

    private func openSourceReader() throws -> XCUIElement {
        let chip = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-document-source-chip-"
        )).firstMatch
        try require(chip.waitForExistence(timeout: 30) && chip.isHittable, "The existing source chip is not available")
        chip.tap()
        let sheet = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-inspector-sheet-"
        )).firstMatch
        try require(sheet.waitForExistence(timeout: 30), "The source chip did not present the real Inspector")
        let expand = app.buttons["torah-inspector-expand-medium"]
        if expand.exists { expand.tap() }
        let row = element(identifier: "torah-reader-segment-" + sourceRef)
        let fullSource = app.buttons["torah-inspector-open-full-source"]
        let readerRoute = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@",
            "torah-reader-segment-" + sourceRef, "torah-inspector-open-full-source"
        )).firstMatch
        try require(readerRoute.waitForExistence(timeout: 60),
                    "The provider did not expose the reader or its full-source route")
        if !row.exists {
            try require(fullSource.isHittable, "The full-source route is not reachable")
            fullSource.tap()
        }
        try require(row.waitForExistence(timeout: 60) && row.isHittable, "The canonical source segment did not load")
        return row
    }

    private func closeInspector() throws {
        let close = app.buttons.matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@", "torah-inspector-close", "torah-inspector-peek-close"
        )).firstMatch
        try require(close.waitForExistence(timeout: 20) && close.isHittable, "The real Inspector close control is missing")
        close.tap()
        let sheet = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-inspector-sheet-"
        )).firstMatch
        try require(sheet.waitForNonExistence(timeout: 20), "The Inspector dismissal animation did not complete")
        try requireCurrentDocument()
    }

    private func quoteRows(_ text: String) -> XCUIElementQuery {
        app.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND value == %@", bodyPrefix, text))
    }

    private func requireQuotes(_ text: String, count: Int) throws -> Set<String> {
        try require(count > 0, "Quote count must be positive")
        try require(quoteRows(text).element(boundBy: count - 1).waitForExistence(timeout: 30),
                    "Expected exactly \(count) native quote blocks")
        let rows = quoteRows(text).allElementsBoundByIndex
        let ids = Set(rows.map(\.identifier))
        try require(ids.count == count, "Quote blocks reused one native identity")
        for row in rows {
            let id = blockID(row.identifier)
            try require(!id.isEmpty, "A quote is missing its native block identifier")
            let citation = app.buttons.matching(NSPredicate(format: "identifier == %@", "torah-linked-source-" + id)).firstMatch
            try require(citation.waitForExistence(timeout: 20), "The quote text has no confirmed block-local source metadata")
            try require(citation.value as? String == "1", "One quote should expose exactly one canonical source")
            try require(citation.label.contains(sourceRef), "The quote's source metadata does not name the selected canonical reference")
        }
        return ids
    }

    private func performHistoryAction(_ identifier: String) throws {
        let more = app.buttons.matching(NSPredicate(format: "label == %@ OR label == %@", "More", "x24/More")).firstMatch
        try require(more.waitForExistence(timeout: 20) && more.isHittable, "Native document actions are not available")
        more.tap()
        let menu = app.buttons["editor-object-action-undoredo"]
        if !menu.waitForExistence(timeout: 5) {
            let nested = app.buttons.matching(NSPredicate(format: "label == %@", "More"))
                .allElementsBoundByIndex.first(where: \.isHittable)
            try require(nested != nil, "The native Undo/Redo menu was not exposed")
            nested?.tap()
        }
        try require(menu.waitForExistence(timeout: 20) && menu.isHittable, "The native Undo/Redo action is missing")
        menu.tap()
        let action = app.buttons[identifier]
        try require(action.waitForExistence(timeout: 20) && action.isHittable, "The requested native history control is missing")
        action.tap()
        // Anytype's existing SheetView dismisses on its transparent background.
        // Compute a point above the observed sheet content, rather than changing
        // navigation or invoking the history service directly from the test.
        let window = app.windows.firstMatch
        let top = window.frame.minY + 80
        try require(action.frame.minY > top + 40, "The history sheet leaves no safe background dismissal target")
        window.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(
            dx: window.frame.width * 0.5, dy: (top + action.frame.minY) * 0.5 - window.frame.minY
        )).tap()
        try require(action.waitForNonExistence(timeout: 20), "The history sheet did not dismiss")
        try requireCurrentDocument()
    }

    private func proveEditableFocus(on identifier: String) throws {
        let row = body(identifier: identifier)
        try require(row.waitForExistence(timeout: 20) && row.isHittable, "The saved native text is not editable")
        row.tap()
        let focus = XCTNSPredicateExpectation(predicate: NSPredicate(
            format: "label CONTAINS %@ AND NOT (label CONTAINS %@)",
            "first-responder-true", "caret-side-unavailable"
        ), object: row)
        try require(XCTWaiter.wait(for: [focus], timeout: 20) == .completed,
                    "The real UITextView did not restore focus and a visible caret")
        try require(app.keyboards.firstMatch.waitForExistence(timeout: 20), "The system keyboard is not available after refocusing")
    }

    private func requireBody(_ identifier: String, text: String) throws {
        let row = body(identifier: identifier)
        try require(row.waitForExistence(timeout: 20) && row.value as? String == text,
                    "An unrelated user-typed native block changed or disappeared")
    }

    private func body(identifier: String) -> XCUIElement {
        app.textViews.matching(NSPredicate(format: "identifier == %@", identifier)).firstMatch
    }

    private func blockID(_ identifier: String) -> String {
        identifier.hasPrefix(bodyPrefix) ? String(identifier.dropFirst(bodyPrefix.count)) : ""
    }

    private func element(identifier: String) -> XCUIElement {
        app.descendants(matching: .any).matching(NSPredicate(format: "identifier == %@", identifier)).firstMatch
    }

    private func require(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
        guard try condition() else {
            throw NSError(domain: "PinkhaNativeQuoteAcceptance", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: message])
        }
    }

    private func attachEvidence(_ name: String) {
        let hierarchy = XCTAttachment(string: app.debugDescription)
        hierarchy.name = name + "-accessibility"
        hierarchy.lifetime = .keepAlways
        add(hierarchy)
        if app.state == .runningForeground {
            let screenshot = XCTAttachment(screenshot: app.screenshot())
            screenshot.name = name
            screenshot.lifetime = .keepAlways
            add(screenshot)
        }
    }
}
