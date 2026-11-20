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


    func testExplicitHebrewDirectionAndAlignmentSurviveColdReopen() {
        let scope = UUID()
        let suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Writing UI Space " + suffix
        let documentName = "Writing UI Document " + suffix
        let body = "שלום עולם, כיוון ויישור מפורשים 789"
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentName)
        tapWhenEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)

        let blocks = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        waitUntilEnabled(blocks.firstMatch)
        blocks.firstMatch.tap()
        blocks.firstMatch.typeText(body)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        let status = app.descendants(matching: .any)
            .matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"),
                object: status, timeout: 45)
        let blockIdentifier = blocks.firstMatch.identifier
        XCTAssertEqual(blocks.firstMatch.value as? String, body)
        XCTAssertEqual(blocks.count, 1)

        let options = app.buttons["any-native-document-options"]
        // A Hebrew paragraph can render RTL by detection alone. First force
        // the opposite persisted direction, then explicitly choose RTL.
        tapWhenEnabled(options)
        tapWhenEnabled(app.buttons["any-native-writing-direction-ltr"])
        waitFor(NSPredicate(format: "exists == true AND value == %@",
                            "העיצוב השמור: כתיבה משמאל לימין, יישור טבעי"),
                object: options, timeout: 45)
        tapWhenEnabled(options)
        tapWhenEnabled(app.buttons["any-native-writing-direction-rtl"])
        waitFor(NSPredicate(format: "exists == true AND value == %@",
                            "העיצוב השמור: כתיבה מימין לשמאל, יישור טבעי"),
                object: options, timeout: 45)
        tapWhenEnabled(options)
        tapWhenEnabled(app.buttons["any-native-text-alignment"])
        tapWhenEnabled(app.buttons["any-native-text-alignment-center"])
        let savedStyle = "העיצוב השמור: כתיבה מימין לשמאל, יישור למרכז"
        // This value comes only from the current native readback snapshot;
        // choosing the menu action does not update it optimistically.
        waitFor(NSPredicate(format: "exists == true AND value == %@", savedStyle),
                object: options, timeout: 45)
        XCTAssertEqual(app.textViews[blockIdentifier].value as? String, body)

        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentName].firstMatch, timeout: 60)
        let reopened = app.textViews[blockIdentifier]
        waitFor(NSPredicate(format: "exists == true AND value == %@", body),
                object: reopened, timeout: 60)
        XCTAssertEqual(blocks.count, 1)
        // Select the actual reopened block without editing or applying a style.
        reopened.tap()
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        waitFor(NSPredicate(format: "exists == true AND value == %@", savedStyle),
                object: options, timeout: 45)
        tapWhenEnabled(options)
        let rtl = app.buttons["any-native-writing-direction-rtl"]
        waitUntilEnabled(rtl)
        XCTAssertTrue(rtl.isSelected, "The reopened native direction must be selected.")
        XCTAssertFalse(app.buttons["any-native-writing-direction-ltr"].isSelected)
        tapWhenEnabled(app.buttons["any-native-text-alignment"])
        let center = app.buttons["any-native-text-alignment-center"]
        waitUntilEnabled(center)
        XCTAssertTrue(center.isSelected, "The reopened explicit alignment must be selected.")
        XCTAssertFalse(app.buttons["any-native-text-alignment-natural"].isSelected)
    }

    func testHierarchyDragIntoFolderPersistsAfterColdReopen() {
        let scope = UUID()
        let suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Drag UI Space " + suffix
        let folderName = "Drag destination " + suffix
        let documentName = "Drag document " + suffix
        let body = "מסמך שנגרר לתיקייה ושומר על תוכנו 246"
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-folder", title: folderName)
        waitUntilEnabled(app.buttons[folderName].firstMatch, timeout: 60)
        createNamedItem(app, action: "any-native-new-document", title: documentName)
        tapWhenEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        let blocks = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        waitUntilEnabled(blocks.firstMatch)
        blocks.firstMatch.tap()
        blocks.firstMatch.typeText(body)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        let status = app.descendants(matching: .any)
            .matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"),
                object: status, timeout: 45)
        let blockIdentifier = blocks.firstMatch.identifier

        reopenOwnedWorkspace(app, spaceName: spaceName)
        let source = app.buttons[documentName].firstMatch
        let destination = app.buttons[folderName].firstMatch
        waitUntilEnabled(source, timeout: 60)
        waitUntilEnabled(destination)
        waitFor(NSPredicate(format: "hittable == true"), object: source, timeout: 20)
        waitFor(NSPredicate(format: "hittable == true"), object: destination, timeout: 20)
        let rowIdentifier = source.identifier
        let folderIdentifier = destination.identifier
        XCTAssertTrue(rowIdentifier.hasPrefix("any-native-hierarchy-row-"))
        XCTAssertTrue(folderIdentifier.hasPrefix("any-native-hierarchy-row-"))
        XCTAssertNotEqual(rowIdentifier, folderIdentifier)
        // Exercise the production String drag payload and folder drop handler.
        // Do not invoke the Move context-menu action or a fixture/native API.
        source.press(forDuration: 1.1, thenDragTo: destination)
        let movedRow = app.buttons[rowIdentifier]
        waitFor(NSPredicate(format: "exists == false"), object: movedRow, timeout: 45)
        let library = app.descendants(matching: .any)
            .matching(identifier: "any-native-library").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "ready"),
                object: library, timeout: 45)
        XCTAssertFalse(movedRow.exists, "The acknowledged drop must remove the root row.")

        tapWhenEnabled(app.buttons[folderIdentifier])
        waitUntilEnabled(movedRow, timeout: 60)
        XCTAssertEqual(app.buttons.matching(identifier: rowIdentifier).count, 1)
        tapWhenEnabled(movedRow)
        waitFor(NSPredicate(format: "exists == true AND value == %@", body),
                object: app.textViews[blockIdentifier], timeout: 60)
        XCTAssertEqual(blocks.count, 1)

        reopenOwnedWorkspace(app, spaceName: spaceName)
        waitUntilEnabled(app.buttons[folderIdentifier], timeout: 60)
        XCTAssertFalse(movedRow.exists, "Cold reopen must keep the document out of the root.")
        tapWhenEnabled(app.buttons[folderIdentifier])
        waitUntilEnabled(movedRow, timeout: 60)
        XCTAssertEqual(app.buttons.matching(identifier: rowIdentifier).count, 1)
        tapWhenEnabled(movedRow)
        waitFor(NSPredicate(format: "exists == true AND value == %@", body),
                object: app.textViews[blockIdentifier], timeout: 60)
        XCTAssertEqual(blocks.count, 1)
    }

    func testSourceDragIntoNativeEditorPreservesTargetAndColdReopens() {
        let scope = UUID()
        let suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Source drag UI Space " + suffix
        let documentName = "Source drag UI Document " + suffix
        let targetText = "בלוק היעד נשאר במקומו ובזהותו " + suffix
        let reference = "Genesis 1:1"
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentName)
        tapWhenEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)

        let blocks = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        waitUntilEnabled(blocks.firstMatch)
        blocks.firstMatch.tap()
        blocks.firstMatch.typeText(targetText)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        let status = app.descendants(matching: .any)
            .matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"),
                object: status, timeout: 45)
        let targetIdentifier = blocks.firstMatch.identifier
        XCTAssertEqual(blocks.count, 1)
        XCTAssertEqual(app.textViews[targetIdentifier].value as? String, targetText)

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
        let providerText = segment.label
        XCTAssertFalse(providerText.isEmpty)
        XCTAssertNotEqual(providerText, reference)
        let target = app.textViews[targetIdentifier]
        let targetRow = app.cells.containing(.textView, identifier: targetIdentifier).firstMatch
        waitFor(NSPredicate(format: "exists == true AND hittable == true"),
                object: targetRow, timeout: 30)
        waitFor(NSPredicate(format: "hittable == true"), object: segment, timeout: 30)
        XCTAssertEqual(app.keyboards.count, 0)

        // Drop at the visible row's insertion boundary, outside its inner text
        // editor. This must use the real custom Torah transfer/table drop path,
        // not the Insert context menu or plain-string paste into UITextView.
        let appFrame = app.frame
        let rowFrame = targetRow.frame.intersection(appFrame)
        let readerFrame = segment.frame
        guard !rowFrame.isNull, rowFrame.width > 24, rowFrame.height > 8 else {
            XCTFail("The current native target row has no usable visible insertion band.")
            return
        }
        let inspector = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-inspector-sheet-")).firstMatch
        let inspectorFrame = inspector.exists ? inspector.frame.intersection(appFrame) : CGRect.null
        // The pinned iPadOS 27 presenter places this sheet physically RIGHT,
        // including in Hebrew. Semantic 'leading' would choose the wrong side.
        // A named container is useful as a boundary only when its current frame
        // contains the reader and actually describes a right-side sheet.
        let hasTrailingSheetFrame = !inspectorFrame.isNull
            && inspectorFrame.minX > appFrame.minX
            && inspectorFrame.contains(readerFrame)
        let insertionY = rowFrame.minY + min(2, rowFrame.height * 0.03)
        var insertionRight = rowFrame.maxX
        if hasTrailingSheetFrame && insertionY >= inspectorFrame.minY
            && insertionY <= inspectorFrame.maxY {
            insertionRight = min(insertionRight, inspectorFrame.minX)
        }
        let uncoveredWidth = insertionRight - rowFrame.minX
        guard uncoveredWidth > 24 else {
            XCTFail("The live inspector frame covers the target row's insertion band.")
            return
        }
        let insertionPoint = CGPoint(
            x: rowFrame.minX + min(12, uncoveredWidth * 0.25), y: insertionY)
        XCTAssertTrue(rowFrame.contains(insertionPoint))
        XCTAssertFalse(readerFrame.contains(insertionPoint))
        if hasTrailingSheetFrame {
            XCTAssertFalse(inspectorFrame.contains(insertionPoint))
        }
        // If SwiftUI exposes no trustworthy full-sheet AX frame, this remains
        // the physical-left/top layout fallback, with live target hittability
        // and reader exclusion above. It is not proof of an invisible sheet's
        // full bounds. Preserve the actual frames/mode for Apple diagnosis.
        let geometry = XCTAttachment(string:
            "mode=\(hasTrailingSheetFrame ? "named-trailing-sheet-frame" : "physical-right-layout-fallback")\n"
            + "app=\(appFrame)\nrow=\(rowFrame)\nreader=\(readerFrame)\n"
            + "inspector=\(inspectorFrame)\ndropPoint=\(insertionPoint)")
        geometry.name = "native-source-drag-live-geometry"; geometry.lifetime = .keepAlways
        add(geometry)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "native-source-drag-before-gesture"; screenshot.lifetime = .keepAlways
        add(screenshot)
        let dragStart = segment.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
        let insertionBoundary = app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(
            dx: insertionPoint.x - appFrame.minX, dy: insertionPoint.y - appFrame.minY))
        dragStart.press(forDuration: 1.1, thenDragTo: insertionBoundary)

        let quote = blocks.matching(NSPredicate(format: "value == %@", providerText)).firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", providerText),
                object: quote, timeout: 60)
        let quoteIdentifier = quote.identifier
        XCTAssertTrue(quoteIdentifier.hasPrefix("any-native-block-"))
        XCTAssertNotEqual(quoteIdentifier, targetIdentifier)
        let quoteBlockID = String(quoteIdentifier.dropFirst("any-native-block-".count))
        let badgeIdentifier = "any-native-block-sources-" + quoteBlockID
        let badge = app.buttons[badgeIdentifier]
        waitUntilEnabled(badge, timeout: 60)
        let sourceLabel = badge.label
        XCTAssertFalse(sourceLabel.isEmpty)
        XCTAssertEqual(blocks.count, 2, "The source drop must create one distinct native block.")
        XCTAssertEqual(target.value as? String, targetText, "A source transfer must not replace the target text.")
        XCTAssertLessThan(quote.frame.minY, target.frame.minY, "A targeted drop inserts before its native target.")
        XCTAssertEqual(app.keyboards.count, 0, "Dragging a source must not acquire editor focus.")
        tapWhenEnabled(app.buttons["torah-inspector-close"])

        // Reopen only after the separate canonical association badge appears.
        // The new quote, its source metadata and the original target must all
        // retain their acknowledged native identities without another gesture.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentName].firstMatch, timeout: 60)
        let reopenedQuote = app.textViews[quoteIdentifier]
        let reopenedTarget = app.textViews[targetIdentifier]
        waitFor(NSPredicate(format: "exists == true AND value == %@", providerText),
                object: reopenedQuote, timeout: 60)
        waitFor(NSPredicate(format: "exists == true AND value == %@", targetText),
                object: reopenedTarget, timeout: 45)
        waitUntilEnabled(app.buttons[badgeIdentifier], timeout: 45)
        XCTAssertEqual(app.buttons[badgeIdentifier].label, sourceLabel)
        XCTAssertEqual(blocks.count, 2)
        XCTAssertEqual(blocks.matching(NSPredicate(format: "value == %@", providerText)).count, 1)
        XCTAssertLessThan(reopenedQuote.frame.minY, reopenedTarget.frame.minY)
        XCTAssertEqual(app.keyboards.count, 0)
    }

    func testTopicAndWordLinksDriveDerivedRelatedDocumentsAfterColdReopen() {
        let scope = UUID()
        let suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Topic Word UI Space " + suffix
        let documentA = "Topic Word Document A " + suffix
        let documentB = "Topic Word Document B " + suffix
        let linkedPrefix = "any-native-linked-source-"
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentA)
        waitUntilEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)

        // Resolve real public provider candidates through the retained search.
        // Topic and Word reader pages are intentionally not assumed here.
        tapWhenEnabled(app.buttons["any-native-document-sources"])
        let scopes = app.segmentedControls.firstMatch
        tapWhenEnabled(scopes.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "נושאים", "Topics")).firstMatch)
        let search = app.searchFields.firstMatch
        waitUntilEnabled(search)
        search.tap(); search.typeText("Shabbat")
        let topicResult = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@",
            "any-native-source-result-topic:", "shabbat")).firstMatch
        waitFor(NSPredicate(format: "exists == true"), object: topicResult, timeout: 60)
        let topicResultID = String(topicResult.identifier.dropFirst("any-native-source-result-".count))
        XCTAssertTrue(topicResultID.hasPrefix("topic:"))
        let topicIdentity = topicResult.value as? String ?? ""
        XCTAssertEqual(topicIdentity, "shabbat")
        let topicLinkID = "any-native-source-link-" + topicResultID
        tapWhenEnabled(app.buttons[topicLinkID], timeout: 60)
        let linkedTopicA = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@", linkedPrefix, topicIdentity)).firstMatch
        waitFor(NSPredicate(format: "exists == true"), object: linkedTopicA, timeout: 60)
        let topicAssociationA = String(linkedTopicA.identifier.dropFirst(linkedPrefix.count))
        let topicTitle = linkedTopicA.label
        XCTAssertFalse(topicAssociationA.isEmpty)
        XCTAssertFalse(topicTitle.isEmpty)

        // Changing the actual segmented category clears the previous query.
        // Capture the acknowledged canonical word, not a guessed lexical label.
        tapWhenEnabled(scopes.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מילים", "Words")).firstMatch)
        waitUntilEnabled(search)
        search.tap(); search.typeText("בראשית")
        let wordLink = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-source-link-word:")).firstMatch
        tapWhenEnabled(wordLink, timeout: 60)
        let linkedWordA = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND identifier != %@",
            linkedPrefix, linkedPrefix + topicAssociationA)).firstMatch
        waitFor(NSPredicate(format: "exists == true"), object: linkedWordA, timeout: 60)
        let wordAssociationA = String(linkedWordA.identifier.dropFirst(linkedPrefix.count))
        let wordTitle = linkedWordA.label
        let wordIdentity = linkedWordA.value as? String ?? ""
        XCTAssertFalse(wordAssociationA.isEmpty)
        XCTAssertNotEqual(wordAssociationA, topicAssociationA)
        XCTAssertFalse(wordTitle.isEmpty)
        XCTAssertFalse(wordIdentity.isEmpty)
        XCTAssertEqual(app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", linkedPrefix)).count, 2)
        tapWhenEnabled(app.buttons["any-native-source-search-done"])

        let topicMenuA = "any-native-derived-actions-" + topicAssociationA
        let wordMenuA = "any-native-derived-actions-" + wordAssociationA
        tapWhenEnabled(app.buttons["any-native-document-properties"])
        waitUntilEnabled(app.buttons[topicMenuA], timeout: 60)
        waitUntilEnabled(app.buttons[wordMenuA], timeout: 60)
        XCTAssertTrue(app.buttons[topicMenuA].label.contains(topicTitle))
        XCTAssertTrue(app.buttons[wordMenuA].label.contains(wordTitle))
        tapWhenEnabled(app.buttons["any-native-property-close"])

        // Create a second ordinary document and link the identical returned
        // Topic through the same public provider/UI, without linking the Word.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentB)
        waitUntilEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        tapWhenEnabled(app.buttons["any-native-document-sources"])
        tapWhenEnabled(scopes.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "נושאים", "Topics")).firstMatch)
        waitUntilEnabled(search)
        search.tap(); search.typeText("Shabbat")
        tapWhenEnabled(app.buttons[topicLinkID], timeout: 60)
        let linkedTopicB = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@", linkedPrefix, topicIdentity)).firstMatch
        waitFor(NSPredicate(format: "exists == true"), object: linkedTopicB, timeout: 60)
        let topicAssociationB = String(linkedTopicB.identifier.dropFirst(linkedPrefix.count))
        let topicTitleB = linkedTopicB.label
        XCTAssertFalse(topicAssociationB.isEmpty)
        XCTAssertEqual(app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", linkedPrefix)).count, 1)
        tapWhenEnabled(app.buttons["any-native-source-search-done"])

        // The real derived-property menu queries the native Topic index. Both
        // committed documents must appear, then the normal owned-sheet route
        // must dismiss the child and parent before opening A's mounted editor.
        tapWhenEnabled(app.buttons["any-native-document-properties"])
        tapWhenEnabled(app.buttons["any-native-derived-actions-" + topicAssociationB], timeout: 60)
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מסמכים מקושרים", "Related documents")).firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[topicTitleB], timeout: 60)
        waitUntilEnabled(app.buttons[documentA].firstMatch, timeout: 60)
        waitUntilEnabled(app.buttons[documentB].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons[documentA].firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[documentA], timeout: 60)
        waitFor(NSPredicate(format: "exists == false"), object: app.buttons["any-native-property-close"], timeout: 30)
        waitUntilEnabled(app.buttons["any-native-document-properties"])

        tapWhenEnabled(app.buttons["any-native-document-properties"])
        waitUntilEnabled(app.buttons[topicMenuA], timeout: 60)
        tapWhenEnabled(app.buttons[wordMenuA], timeout: 60)
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מסמכים מקושרים", "Related documents")).firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[wordTitle], timeout: 60)
        waitUntilEnabled(app.buttons[documentA].firstMatch, timeout: 60)
        XCTAssertFalse(app.buttons[documentB].exists, "A Topic-only document must not enter the Word index.")

        // Reopen from disk without relinking. The exact canonical item IDs and
        // labels must remain present, and Word-related results remain distinct.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentA].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons["any-native-document-properties"], timeout: 60)
        waitUntilEnabled(app.buttons[topicMenuA], timeout: 60)
        waitUntilEnabled(app.buttons[wordMenuA], timeout: 60)
        XCTAssertTrue(app.buttons[topicMenuA].label.contains(topicTitle))
        XCTAssertTrue(app.buttons[wordMenuA].label.contains(wordTitle))
        XCTAssertEqual(app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-derived-actions-")).count, 2)
        tapWhenEnabled(app.buttons[wordMenuA])
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מסמכים מקושרים", "Related documents")).firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[wordTitle], timeout: 60)
        waitUntilEnabled(app.buttons[documentA].firstMatch, timeout: 60)
        XCTAssertFalse(app.buttons[documentB].exists)
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
        acknowledgeOwnedBackup(backup)
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

    private func acknowledgeOwnedBackup(_ row: XCUIElement) {
        waitUntilEnabled(row, timeout: 60)
        // The executed iOS 27 AX trees expose a SwiftUI Toggle row containing
        // a separate physical Switch. A row tap left all five owned accounts
        // unacknowledged; target that observed child control exactly once.
        let switches = row.descendants(matching: .switch)
        let control = switches.firstMatch
        waitUntilEnabled(control, timeout: 10)
        XCTAssertEqual(switches.count, 1, "Expected one physical backup switch")
        waitFor(NSPredicate(format: "hittable == true AND value == %@", "0"),
                object: control, timeout: 10)
        // Geometry only: never capture the recovery phrase or a complete tree.
        let frames = XCTAttachment(string: "row=\(row.frame)\ncontrol=\(control.frame)")
        frames.name = "native-backup-acknowledgement-control-frames"
        frames.lifetime = .keepAlways
        add(frames)
        control.tap()
        waitFor(NSPredicate(format: "value == %@", "1"), object: control, timeout: 10)
        waitFor(NSPredicate(format: "value == %@", "1"), object: row, timeout: 10)
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
