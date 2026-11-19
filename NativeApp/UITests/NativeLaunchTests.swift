import XCTest

/// Real executable + linked AnyLib. Every test uses a fresh debug-only data and
/// Keychain namespace; the long flow reopens that same owned namespace.
@MainActor
final class NativeLaunchTests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testFreshNativeExecutableShowsAccountAndRecoveryEntryPoints() {
        let app = makeApplication()
        app.launch()
        defer { app.terminate() }
        waitUntilEnabled(app.buttons["any-native-account-create"])
        XCTAssertTrue(app.secureTextFields["any-native-account-restore-phrase"].exists)
        XCTAssertTrue(app.buttons["any-native-account-restore"].exists)
        XCTAssertFalse(app.buttons["any-native-account-restore"].isEnabled)
    }

    func testBackgroundAndForegroundReopenTheOwnedRuntime() {
        let app = makeApplication()
        app.launch()
        defer { app.terminate() }
        waitUntilEnabled(app.buttons["any-native-account-create"])
        XCUIDevice.shared.press(.home)
        XCTAssertTrue(app.wait(for: .runningBackground, timeout: 10))
        app.activate()
        waitUntilEnabled(app.buttons["any-native-account-create"])
        XCTAssertTrue(app.secureTextFields["any-native-account-restore-phrase"].exists)
    }

    func testCreateEditHanlinConsentBackgroundAndColdReopen() {
        let scope = UUID()
        let app = makeApplication(scope: scope)
        let spaceName = "Native UI Space " + String(scope.uuidString.prefix(8))
        let documentName = "Native UI Document " + String(scope.uuidString.prefix(8))
        let text = "שלום עולם Native 123"
        app.launch()
        defer { app.terminate() }

        createOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons["any-native-create-menu"], timeout: 60)
        tapWhenEnabled(app.buttons["any-native-new-document"])

        let title = app.descendants(matching: .any)
            .matching(identifier: "any-native-name-input").firstMatch
        waitUntilEnabled(title)
        title.tap()
        title.typeText(String(documentName))
        tapWhenEnabled(app.buttons["any-native-name-confirm"])

        let addParagraph = app.buttons["any-native-add-paragraph"]
        // Native library creation opens its confirmed new document.
        tapWhenEnabled(addParagraph, timeout: 60)

        let textViews = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-"))
        let editor = textViews.firstMatch
        waitUntilEnabled(editor)
        editor.tap()
        editor.typeText(text)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        let status = app.descendants(matching: .any)
            .matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"),
                object: status, timeout: 45)
        XCTAssertEqual(editor.value as? String, text)
        XCTAssertEqual(textViews.count, 1)

        // Exercise the actual shared UIKit consent UI without configuring an
        // external AI provider or sending document text to a model.
        tapWhenEnabled(app.buttons["any-native-hanlin"])
        let share = app.buttons["pinkha.hanlin.share-context"]
        tapWhenEnabled(share)
        tapWhenEnabled(app.buttons["pinkha.hanlin.consent.read-context.cancel"])
        waitUntilEnabled(share)
        share.tap()
        tapWhenEnabled(app.buttons["pinkha.hanlin.consent.read-context.allow"])
        waitFor(NSPredicate(format: "exists == true AND enabled == false"),
                object: share, timeout: 20)
        tapWhenEnabled(app.buttons["pinkha.hanlin.close"])
        tapWhenEnabled(app.buttons["any-native-hanlin"])
        waitUntilEnabled(app.buttons["pinkha.hanlin.share-context"])
        tapWhenEnabled(app.buttons["pinkha.hanlin.close"])

        // The new presentation owner must recover its scoped navigation while
        // the native account/runtime is reauthenticated in the foreground.
        XCUIDevice.shared.press(.home)
        XCTAssertTrue(app.wait(for: .runningBackground, timeout: 10))
        app.activate()
        waitFor(NSPredicate(format: "exists == true AND value == %@", text),
                object: textViews.firstMatch, timeout: 60)
        XCTAssertEqual(textViews.count, 1)

        // Cold reopen verifies the native committed text and Keychain identity;
        // it makes no claim about process-persistent unsaved draft recovery.
        app.terminate()
        app.launch()
        tapWhenEnabled(app.buttons["any-native-saved-account"].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons[String(spaceName)].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons[String(documentName)].firstMatch, timeout: 60)
        waitFor(NSPredicate(format: "exists == true AND value == %@", text),
                object: textViews.firstMatch, timeout: 60)
        XCTAssertEqual(textViews.count, 1)
        XCTAssertTrue(app.buttons["any-native-document-sources"].exists)
        XCTAssertTrue(app.buttons["any-native-document-properties"].exists)
        XCTAssertTrue(app.buttons["any-native-hanlin"].exists)
    }

    func testHierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType() {
        let scope = UUID()
        let suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Hierarchy UI Space " + suffix
        let folderA = "Folder A " + suffix, folderB = "Folder B " + suffix
        let originalName = "Native hierarchy draft " + suffix
        let updatedName = "Native renamed document " + suffix
        let body = "שלום היררכיה ומאפיינים 456"
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)

        createNamedItem(app, action: "any-native-new-folder", title: folderA)
        waitUntilEnabled(app.buttons[folderA].firstMatch, timeout: 60)
        createNamedItem(app, action: "any-native-new-folder", title: folderB)
        waitUntilEnabled(app.buttons[folderB].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons[folderA].firstMatch)
        createNamedItem(app, action: "any-native-new-document", title: originalName)
        tapWhenEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        let blocks = app.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-"))
        waitUntilEnabled(blocks.firstMatch)
        blocks.firstMatch.tap(); blocks.firstMatch.typeText(body)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        let status = app.descendants(matching: .any).matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"), object: status, timeout: 45)
        XCTAssertEqual(blocks.firstMatch.value as? String, body)
        XCTAssertEqual(blocks.count, 1)

        tapWhenEnabled(app.buttons["any-native-document-properties"])
        let type = app.descendants(matching: .any).matching(identifier: "any-native-property-type").firstMatch
        waitUntilEnabled(type)
        let typeName = type.value as? String ?? ""
        XCTAssertFalse(typeName.isEmpty, "The actual native Type must have an accessible selected value.")
        type.tap()
        tapWhenEnabled(app.buttons[typeName].firstMatch)
        // The fresh workspace has Page only. Choosing its actual catalog entry
        // exercises the picker without inventing a custom Type seed or claiming
        // a second-Type transition that this UI has not created.
        tapWhenEnabled(app.buttons["any-native-property-name"])
        let field = app.descendants(matching: .any).matching(identifier: "any-native-property-value-input").firstMatch
        waitUntilEnabled(field)
        field.tap(); field.press(forDuration: 1.2)
        let selectAll = app.descendants(matching: .any).matching(
            NSPredicate(format: "label == %@ OR label == %@ OR label == %@", "Select All", "בחר הכל", "בחר הכול")).firstMatch
        tapWhenEnabled(selectAll)
        field.typeText(updatedName)
        tapWhenEnabled(app.buttons["any-native-property-save"])
        let nameRow = app.buttons["any-native-property-name"]
        waitFor(NSPredicate(format: "exists == true AND value == %@", updatedName), object: nameRow, timeout: 45)
        XCTAssertEqual(type.value as? String, typeName)

        tapWhenEnabled(app.buttons["any-native-property-menu"])
        tapWhenEnabled(app.buttons["any-native-property-customize"])
        let visibility = app.switches["any-native-property-visibility-name"]
        waitUntilEnabled(visibility)
        XCTAssertEqual(visibility.value as? String, "1")
        visibility.tap()
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND value == %@", "0"),
                object: visibility, timeout: 45)
        tapWhenEnabled(app.buttons["any-native-property-customization-close"])
        waitFor(NSPredicate(format: "exists == false"), object: nameRow, timeout: 20)
        tapWhenEnabled(app.buttons["any-native-property-close"])

        // A cold reopen and the actual user move sheet test persisted hierarchy,
        // not an optimistic-only row or a direct HTTP fixture mutation.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[folderA].firstMatch)
        let oldRow = app.buttons[updatedName].firstMatch
        waitUntilEnabled(oldRow)
        oldRow.press(forDuration: 1.1)
        tapWhenEnabled(app.buttons["any-native-hierarchy-move"])
        tapWhenEnabled(app.buttons[folderB].firstMatch)
        waitFor(NSPredicate(format: "exists == false"), object: oldRow, timeout: 45)
        let library = app.descendants(matching: .any).matching(identifier: "any-native-library").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "ready"), object: library, timeout: 45)
        XCTAssertFalse(oldRow.exists, "The acknowledged move must still remove the old-parent row.")
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[folderB].firstMatch)
        tapWhenEnabled(app.buttons[updatedName].firstMatch)
        waitFor(NSPredicate(format: "exists == true AND value == %@", body), object: blocks.firstMatch, timeout: 60)
        XCTAssertEqual(blocks.count, 1)

        tapWhenEnabled(app.buttons["any-native-document-properties"])
        waitUntilEnabled(type)
        XCTAssertEqual(type.value as? String, typeName)
        XCTAssertFalse(nameRow.exists)
        tapWhenEnabled(app.buttons["any-native-property-menu"])
        tapWhenEnabled(app.buttons["any-native-property-customize"])
        waitUntilEnabled(visibility)
        XCTAssertEqual(visibility.value as? String, "0", "Hidden preference survives native reopen.")
        visibility.tap()
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND value == %@", "1"),
                object: visibility, timeout: 45)
        tapWhenEnabled(app.buttons["any-native-property-customization-close"])
        waitFor(NSPredicate(format: "exists == true AND value == %@", updatedName), object: nameRow, timeout: 45)
        XCTAssertEqual(type.value as? String, typeName)
        tapWhenEnabled(app.buttons["any-native-property-close"])
        XCTAssertEqual(blocks.firstMatch.value as? String, body)
    }

    func testSourceInspectorQuoteAndNoteSurviveColdReopen() {
        let scope = UUID()
        let suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Torah UI Space " + suffix
        let documentName = "Torah UI Document " + suffix
        let reference = "Genesis 1:1"
        let noteName = "הערה על " + reference
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentName)
        waitUntilEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)

        // Use the retained production provider facade and the actual pinned
        // inspector. No seed data, injected transfer, or replacement search.
        tapWhenEnabled(app.buttons["any-native-document-sources"])
        let search = app.searchFields.firstMatch
        waitUntilEnabled(search)
        search.tap(); search.typeText(reference)
        let result = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@",
            "any-native-source-result-", reference)).firstMatch
        tapWhenEnabled(result, timeout: 60)
        let segment = app.buttons["torah-reader-segment-sefaria:" + reference]
        waitUntilEnabled(segment, timeout: 60)
        // Embedded search is the same retained presenter inside the pinned
        // inspector's navigation stack, not another host-owned modal sheet.
        tapWhenEnabled(app.buttons["torah-inspector-search-entry"])
        waitUntilEnabled(search)
        search.tap(); search.typeText(reference)
        tapWhenEnabled(result, timeout: 60)
        waitUntilEnabled(segment, timeout: 60)
        XCTAssertFalse(app.buttons["any-native-source-search-done"].exists)
        let providerText = segment.label
        XCTAssertFalse(providerText.isEmpty)
        XCTAssertNotEqual(providerText, reference)
        segment.press(forDuration: 1.1)
        tapWhenEnabled(app.buttons["torah-reader-insert-sefaria:" + reference])

        // The inspector allows background interaction. A real source badge is
        // exposed only after canonical association readback, so the next source
        // action cannot race ahead of that separate metadata write.
        let sourceBadges = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-sources-"))
        waitFor(NSPredicate(format: "exists == true"), object: sourceBadges.firstMatch, timeout: 60)
        let blocks = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        waitFor(NSPredicate(format: "exists == true AND value == %@", providerText),
                object: blocks.firstMatch, timeout: 45)
        XCTAssertEqual(blocks.count, 1)
        XCTAssertEqual(sourceBadges.count, 1)
        XCTAssertEqual(app.keyboards.count, 0, "Source insertion must not acquire editor focus.")
        let quoteIdentifier = blocks.firstMatch.identifier
        let quoteBlockID = String(quoteIdentifier.dropFirst("any-native-block-".count))
        let quoteBadgeIdentifier = "any-native-block-sources-" + quoteBlockID
        XCTAssertEqual(sourceBadges.firstMatch.identifier, quoteBadgeIdentifier)

        // Open the quote's retained association, then use the real Notes tool.
        // The normal T5 action creates and navigates to the native Note.
        tapWhenEnabled(segment)
        selectInspectorTool(app, hebrew: "הערות", english: "Notes")
        tapWhenEnabled(app.buttons["torah-inspector-add-note"], timeout: 60)
        waitFor(NSPredicate(format: "exists == true"),
                object: app.navigationBars[noteName], timeout: 60)
        let sourceLine = blocks.matching(NSPredicate(format: "value CONTAINS %@", reference)).firstMatch
        waitFor(NSPredicate(format: "exists == true"), object: sourceLine, timeout: 45)
        let noteSourceIdentifier = sourceLine.identifier
        let noteSourceText = sourceLine.value as? String ?? ""
        XCTAssertFalse(noteSourceText.isEmpty)
        tapWhenEnabled(app.buttons["any-native-document-sources"])
        let linkedReference = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@",
            "any-native-linked-source-", reference)).firstMatch
        tapWhenEnabled(linkedReference, timeout: 45)
        tapWhenEnabled(segment, timeout: 60)
        selectInspectorTool(app, hebrew: "במסמכים", english: "In Documents")
        let originRelated = relatedDocumentRow(app, title: documentName)
        let noteRelated = relatedDocumentRow(app, title: noteName)
        waitFor(NSPredicate(format: "exists == true"), object: originRelated, timeout: 60)
        waitFor(NSPredicate(format: "exists == true"), object: noteRelated, timeout: 60)

        // Reopen the same owned account and Space from disk. The original
        // quote ID/text, the origin's Note backlink, and the Note's source
        // context must all survive without issuing a second create action.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentName].firstMatch, timeout: 60)
        let reopenedQuote = app.textViews[quoteIdentifier]
        waitFor(NSPredicate(format: "exists == true AND value == %@", providerText),
                object: reopenedQuote, timeout: 60)
        XCTAssertEqual(blocks.count, 1)
        tapWhenEnabled(app.buttons[quoteBadgeIdentifier], timeout: 45)
        selectInspectorTool(app, hebrew: "הערות", english: "Notes")
        let notes = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND label == %@",
            "torah-inspector-note-", noteName))
        waitUntilEnabled(notes.firstMatch, timeout: 60)
        XCTAssertEqual(notes.count, 1, "Cold reopen must expose exactly the committed Note backlink.")
        notes.firstMatch.tap()
        waitFor(NSPredicate(format: "exists == true"),
                object: app.navigationBars[noteName], timeout: 60)
        waitFor(NSPredicate(format: "exists == true AND value == %@", noteSourceText),
                object: app.textViews[noteSourceIdentifier], timeout: 45)
        tapWhenEnabled(app.buttons["any-native-document-sources"])
        tapWhenEnabled(linkedReference, timeout: 45)
        tapWhenEnabled(segment, timeout: 60)
        selectInspectorTool(app, hebrew: "במסמכים", english: "In Documents")
        waitFor(NSPredicate(format: "exists == true"), object: originRelated, timeout: 60)
        waitFor(NSPredicate(format: "exists == true"), object: noteRelated, timeout: 60)
    }

    private func selectInspectorTool(_ app: XCUIApplication, hebrew: String, english: String) {
        let tools = app.descendants(matching: .any)
            .matching(identifier: "torah-inspector-tools").firstMatch
        waitUntilEnabled(tools, timeout: 60)
        tapWhenEnabled(tools.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", hebrew, english)).firstMatch)
    }

    private func relatedDocumentRow(_ app: XCUIApplication, title: String) -> XCUIElement {
        app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND label CONTAINS %@",
            "torah-inspector-related-row-", title)).firstMatch
    }

    private func createOwnedWorkspace(_ app: XCUIApplication, spaceName: String) {
        tapWhenEnabled(app.buttons["any-native-account-create"])
        let backup = app.switches["any-native-backup-acknowledged"]
        waitUntilEnabled(backup, timeout: 60)
        backup.tap()
        // Acknowledge through the same UI as a person; never read or print the
        // recovery phrase from the accessibility tree.
        tapWhenEnabled(app.buttons["any-native-backup-continue"])
        let spaceNameField = app.textFields["any-native-space-name"]
        waitUntilEnabled(spaceNameField)
        spaceNameField.tap()
        spaceNameField.typeText(String(spaceName))
        tapWhenEnabled(app.buttons["any-native-space-create"])
        tapWhenEnabled(app.buttons["any-native-workspace-setup"], timeout: 90)
    }

    private func createNamedItem(_ app: XCUIApplication, action: String, title: String) {
        tapWhenEnabled(app.buttons["any-native-create-menu"], timeout: 60)
        tapWhenEnabled(app.buttons[action])
        let field = app.descendants(matching: .any).matching(identifier: "any-native-name-input").firstMatch
        waitUntilEnabled(field)
        field.tap(); field.typeText(title)
        tapWhenEnabled(app.buttons["any-native-name-confirm"])
    }

    private func reopenOwnedWorkspace(_ app: XCUIApplication, spaceName: String) {
        app.terminate(); app.launch()
        tapWhenEnabled(app.buttons["any-native-saved-account"].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons[spaceName].firstMatch, timeout: 60)
    }

    private func makeApplication(scope: UUID = UUID()) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = [
            "--native-ui-tests", "--native-ui-test-scope", scope.uuidString,
            "-AppleLanguages", "(he,en)", "-AppleLocale", "he_IL"
        ]
        return app
    }

    private func tapWhenEnabled(_ element: XCUIElement, timeout: TimeInterval = 30,
                                file: StaticString = #filePath, line: UInt = #line) {
        waitUntilEnabled(element, timeout: timeout, file: file, line: line)
        element.tap()
    }

    private func waitUntilEnabled(_ element: XCUIElement, timeout: TimeInterval = 30,
                                  file: StaticString = #filePath, line: UInt = #line) {
        waitFor(NSPredicate(format: "exists == true AND enabled == true"),
                object: element, timeout: timeout, file: file, line: line)
    }

    private func waitFor(_ predicate: NSPredicate, object: Any, timeout: TimeInterval,
                         file: StaticString = #filePath, line: UInt = #line) {
        let expectation = XCTNSPredicateExpectation(predicate: predicate, object: object)
        XCTAssertEqual(XCTWaiter.wait(for: [expectation], timeout: timeout), .completed,
                       "Expected UI state was not reached", file: file, line: line)
    }
}
