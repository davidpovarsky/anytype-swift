import XCTest
import Foundation
import CryptoKit

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
        // A navigation transition can publish this enabled overlay before
        // UIKit has a usable hit point. Observe readiness before one real tap.
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: addParagraph, timeout: 60)
        let addControl = XCTAttachment(string:
            "enabled=\(addParagraph.isEnabled)\nhittable=\(addParagraph.isHittable)\nframe=\(addParagraph.frame)")
        addControl.name = "native-empty-paragraph-pre-tap-control"
        addControl.lifetime = .keepAlways; add(addControl)
        addParagraph.tap()

        let textViews = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-"))
        let editor = textViews.firstMatch
        waitForNativeEditorInput(app, editor)
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
        // Keep this diagnosis local to the one failed journey. It records no
        // labels, text, recovery phrase, screenshot or complete AX tree.
        func observeBackupControl(_ phase: String, row: XCUIElement, control: XCUIElement) {
            func state(_ element: XCUIElement) -> [String: Any] {
                guard element.exists else { return ["exists": false] }
                let rawValue = element.value as? String
                let value = rawValue == "0" || rawValue == "1" ? rawValue! : "unavailable"
                let frame = element.frame
                return ["exists": true, "enabled": element.isEnabled,
                        "hittable": element.isHittable, "value": value,
                        "frame": [frame.minX, frame.minY, frame.width, frame.height]]
            }
            let appState = app.state
            let record: [String: Any] = [
                "schemaVersion": 1, "phase": phase, "ownedScope": scope.uuidString,
                "utcEpochSeconds": Date().timeIntervalSince1970,
                "testRunnerPID": ProcessInfo.processInfo.processIdentifier,
                "appPIDSource": "Matching original XCTest synthesized-event attachment",
                "appState": appState.rawValue,
                "appRunningForeground": appState == .runningForeground,
                "windowCount": app.windows.count,
                "nativeSceneStateAvailable": false, "nativeResetReasonAvailable": false,
                "row": state(row), "control": state(control)
            ]
            let data = (try? JSONSerialization.data(withJSONObject: record, options: [.sortedKeys]))
                ?? Data("{\"diagnosticEncodingFailed\":true}".utf8)
            let observation = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
            observation.name = "native-backup-control-observation-" + phase
            observation.lifetime = .keepAlways
            add(observation)
        }

        tapWhenEnabled(app.buttons["any-native-account-create"])
        let backup = app.switches["any-native-backup-acknowledged"]
        do {
            let row = backup
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
            observeBackupControl("before-tap", row: row, control: control)
            control.tap()
            observeBackupControl("after-tap", row: row, control: control)
            waitFor(NSPredicate(format: "value == %@", "1"), object: control, timeout: 10)
            waitFor(NSPredicate(format: "value == %@", "1"), object: row, timeout: 10)
            observeBackupControl("acknowledged", row: row, control: control)
        }
        // Acknowledge through the same UI as a person; never read or print the
        // recovery phrase from the accessibility tree.
        tapWhenEnabled(app.buttons["any-native-backup-continue"])
        let spaceNameField = app.textFields["any-native-space-name"]
        waitUntilEnabled(spaceNameField)
        spaceNameField.tap()
        spaceNameField.typeText(String(spaceName))
        tapWhenEnabled(app.buttons["any-native-space-create"])
        tapWhenEnabled(app.buttons["any-native-workspace-setup"], timeout: 90)

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
        revealNativeProperty(app, app.buttons["any-native-property-name"])
        tapWhenEnabled(app.buttons["any-native-property-name"])
        let field = app.descendants(matching: .any).matching(identifier: "any-native-property-value-input").firstMatch
        waitUntilEnabled(field)
        field.tap(); field.press(forDuration: 1.2)
        let selectAll = app.descendants(matching: .any).matching(
            NSPredicate(format: "label == %@ OR label == %@ OR label == %@ OR label == %@",
                        "Select All", "בחר הכל", "בחר הכול", "בחירת הכול")).firstMatch
        tapWhenEnabled(selectAll)
        field.typeText(updatedName)
        tapWhenEnabled(app.buttons["any-native-property-save"])
        let nameRow = app.buttons["any-native-property-name"]
        waitFor(NSPredicate(format: "exists == true AND value == %@", updatedName), object: nameRow, timeout: 45)
        revealNativeProperty(app, type, scrollDown: true)
        XCTAssertEqual(type.value as? String, typeName)

        tapWhenEnabled(app.buttons["any-native-property-menu"])
        tapWhenEnabled(app.buttons["any-native-property-customize"])
        let visibility = app.switches["any-native-property-visibility-name"]
        revealNativeProperty(app, visibility, listID: "any-native-property-customization-list")
        XCTAssertEqual(visibility.value as? String, "1")
        toggleNativePropertyVisibility(visibility, expected: "1")
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
        guard moveHierarchyItemWithObservedTransition(app, source: oldRow,
                                                       destinationName: folderB) else { return }
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
        revealNativeProperty(app, type, scrollDown: true)
        XCTAssertEqual(type.value as? String, typeName)
        XCTAssertFalse(nameRow.exists)
        tapWhenEnabled(app.buttons["any-native-property-menu"])
        tapWhenEnabled(app.buttons["any-native-property-customize"])
        revealNativeProperty(app, visibility, listID: "any-native-property-customization-list")
        XCTAssertEqual(visibility.value as? String, "0", "Hidden preference survives native reopen.")
        toggleNativePropertyVisibility(visibility, expected: "0")
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND value == %@", "1"),
                object: visibility, timeout: 45)
        tapWhenEnabled(app.buttons["any-native-property-customization-close"])
        revealNativeProperty(app, nameRow)
        waitFor(NSPredicate(format: "exists == true AND value == %@", updatedName), object: nameRow, timeout: 45)
        revealNativeProperty(app, type, scrollDown: true)
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
        let segment = app.buttons["torah-reader-segment-" + reference]
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
        tapWhenEnabled(app.buttons["torah-reader-insert-" + reference])

        // The executed iPad sheet remains expanded after insertion and hides
        // the underlying editor from AX. Collapse its real header before
        // inspecting the quote. The badge still requires canonical readback.
        collapseInspectorForBackgroundRead(app)
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
        tapWhenEnabled(app.buttons[quoteBadgeIdentifier])
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
        let appLanguage = ProcessInfo.processInfo.environment["PINKHA_NATIVE_RTL_APP_LANGUAGE"] ?? "he"
        guard appLanguage == "he" || appLanguage == "en" else {
            XCTFail("The native RTL journey requires the exact app language he or en.")
            return
        }
        let hebrewApp = appLanguage == "he"
        let leftToRightStyle = hebrewApp
            ? "העיצוב השמור: כתיבה משמאל לימין, יישור טבעי"
            : "Saved style: Left to right, alignment Natural"
        let rightToLeftStyle = hebrewApp
            ? "העיצוב השמור: כתיבה מימין לשמאל, יישור טבעי"
            : "Saved style: Right to left, alignment Natural"
        let savedStyle = hebrewApp
            ? "העיצוב השמור: כתיבה מימין לשמאל, יישור למרכז"
            : "Saved style: Right to left, alignment Center"
        let centerTitle = hebrewApp ? "למרכז" : "Center"
        let naturalTitle = hebrewApp ? "טבעי" : "Natural"
        let scope = UUID()
        let suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        if !hebrewApp {
            app.launchArguments = [
                "--native-ui-tests", "--native-ui-test-scope", scope.uuidString,
                "-AppleLanguages", "(en,he)", "-AppleLocale", "en_US"
            ]
        }
        let spaceName = "Writing UI Space " + suffix
        let documentName = "Writing UI Document " + suffix
        let body = "שלום עולם, כיוון ויישור מפורשים 789"
        func recordSavedParagraph(_ phase: String) {
            let screenshot = XCTAttachment(screenshot: app.screenshot())
            screenshot.name = "NATIVE_RTL_" + appLanguage + "_" + phase
            screenshot.lifetime = .keepAlways
            add(screenshot)
        }
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
                            leftToRightStyle),
                object: options, timeout: 45)
        tapWhenEnabled(options)
        tapWhenEnabled(app.buttons["any-native-writing-direction-rtl"])
        waitFor(NSPredicate(format: "exists == true AND value == %@",
                            rightToLeftStyle),
                object: options, timeout: 45)
        tapWhenEnabled(options)
        tapWhenEnabled(app.buttons["any-native-text-alignment"])
        // UIKit exposes this nested menu by its visible localized title;
        // select the exact app-language title. Native readback remains the assertion.
        tapWhenEnabled(app.buttons[centerTitle])
        // This value comes only from the current native readback snapshot;
        // choosing the menu action does not update it optimistically.
        waitFor(NSPredicate(format: "exists == true AND value == %@", savedStyle),
                object: options, timeout: 45)
        XCTAssertEqual(app.textViews[blockIdentifier].value as? String, body)
        recordSavedParagraph("center_before_reopen")

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
        recordSavedParagraph("center_after_reopen")
        tapWhenEnabled(options)
        let rtl = app.buttons["any-native-writing-direction-rtl"]
        waitUntilEnabled(rtl)
        XCTAssertTrue(rtl.isSelected, "The reopened native direction must be selected.")
        XCTAssertFalse(app.buttons["any-native-writing-direction-ltr"].isSelected)
        tapWhenEnabled(app.buttons["any-native-text-alignment"])
        let center = app.buttons[centerTitle]
        waitUntilEnabled(center)
        XCTAssertTrue(center.isSelected, "The reopened explicit alignment must be selected.")
        let natural = app.buttons[naturalTitle]
        waitUntilEnabled(natural)
        XCTAssertFalse(natural.isSelected)
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
        let sourceRow = app.buttons[documentName].firstMatch
        let destination = app.buttons[folderName].firstMatch
        waitUntilEnabled(sourceRow, timeout: 60)
        waitUntilEnabled(destination)
        let rowIdentifier = sourceRow.identifier
        let folderIdentifier = destination.identifier
        XCTAssertTrue(rowIdentifier.hasPrefix("any-native-hierarchy-row-"))
        XCTAssertTrue(folderIdentifier.hasPrefix("any-native-hierarchy-row-"))
        XCTAssertNotEqual(rowIdentifier, folderIdentifier)
        waitFor(NSPredicate(format: "hittable == true"), object: destination, timeout: 20)
        let handleDeadline = ProcessInfo.processInfo.systemUptime + 20
        let sourceObjectID = String(rowIdentifier.dropFirst("any-native-hierarchy-row-".count))
        let handles = app.descendants(matching: .any)
            .matching(identifier: "any-native-hierarchy-drag-" + sourceObjectID)
        let source = handles.firstMatch
        let handleReady = NSPredicate { _, _ in
            handles.count == 1 && source.exists && source.isEnabled && source.isHittable
        }
        guard waitForObservedHierarchy(app, predicate: handleReady, object: app,
                timeout: max(0, handleDeadline - ProcessInfo.processInfo.systemUptime),
                phase: "source_drag_handle", source: source, destination: destination) else { return }
        let handleLabels = ["Drag " + documentName,
                            "\u{05D2}\u{05E8}\u{05D9}\u{05E8}\u{05D4} \u{05E9}\u{05DC} " + documentName]
        guard handleLabels.contains(source.label) else {
            XCTFail("The separate handle must describe the real drag action.")
            return
        }
        // Same native String payload, gesture, destination and readback contract.
        // Only the source is the dedicated handle outside the open/menu Button.
        recordNativeHierarchyTransition(app, phase: "before_drag_handle",
                                        source: source, destination: destination)
        guard handles.count == 1, source.exists, source.isEnabled, source.isHittable,
              handleLabels.contains(source.label),
              ProcessInfo.processInfo.systemUptime < handleDeadline else {
            XCTFail("The unique native drag handle changed before the original gesture.")
            return
        }
        source.press(forDuration: 1.1, thenDragTo: destination,
                     withVelocity: XCUIGestureVelocity(rawValue: 100),
                     thenHoldForDuration: 0.6)
        let movedRow = app.buttons[rowIdentifier]
        guard waitForObservedHierarchy(app,
                predicate: NSPredicate(format: "exists == false"), object: movedRow,
                timeout: 45, phase: "original_drag_row_disappearance",
                source: movedRow, destination: destination) else { return }
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

    func testSourceDragIntoNativeEditorPreservesTargetAndColdReopens() throws {
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
        try createNamedItemWithObservedTransition(app, action: "any-native-new-document", title: documentName)
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
        let segment = app.buttons["torah-reader-segment-" + reference]
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

        // The original run rendered the canonical badge while the expanded
        // inspector kept that background button outside its accessible scope.
        // Use the same real header collapse as the passing Inspector journey
        // before requiring the quote, native badge, and unchanged target.
        collapseInspectorForBackgroundRead(app)
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
        // The header collapse may dismiss the inspector completely. The cold
        // reopen below terminates the app from either supported collapsed state.

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
        let relatedList = app.descendants(matching: .any)
            .matching(identifier: "any-native-related-documents-list").firstMatch
        func relatedDocument(_ title: String) -> XCUIElement {
            relatedList.buttons.matching(NSPredicate(
                format: "identifier BEGINSWITH %@ AND label == %@",
                "any-native-related-document-", title)).firstMatch
        }
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
        revealNativeProperty(app, app.buttons[topicMenuA])
        revealNativeProperty(app, app.buttons[wordMenuA])
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
        let topicMenuB = app.buttons["any-native-derived-actions-" + topicAssociationB]
        revealNativeProperty(app, topicMenuB)
        tapWhenEnabled(topicMenuB)
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מסמכים מקושרים", "Related documents")).firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[topicTitleB], timeout: 60)
        waitFor(NSPredicate(format: "exists == true"), object: relatedList, timeout: 60)
        waitUntilEnabled(relatedDocument(documentA), timeout: 60)
        waitUntilEnabled(relatedDocument(documentB), timeout: 60)
        tapWhenEnabled(relatedDocument(documentA))
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[documentA], timeout: 60)
        waitFor(NSPredicate(format: "exists == false"), object: app.buttons["any-native-property-close"], timeout: 30)
        waitUntilEnabled(app.buttons["any-native-document-properties"])

        tapWhenEnabled(app.buttons["any-native-document-properties"])
        revealNativeProperty(app, app.buttons[topicMenuA])
        revealNativeProperty(app, app.buttons[wordMenuA])
        tapWhenEnabled(app.buttons[wordMenuA])
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מסמכים מקושרים", "Related documents")).firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[wordTitle], timeout: 60)
        waitFor(NSPredicate(format: "exists == true"), object: relatedList, timeout: 60)
        waitUntilEnabled(relatedDocument(documentA), timeout: 60)
        // The underlying navigation BackButton still names document B. Only
        // actual rows returned to the current native Word-results list count.
        XCTAssertFalse(relatedDocument(documentB).exists, "A Topic-only document must not enter the Word index.")

        // Reopen from disk without relinking. The exact canonical item IDs and
        // labels must remain present, and Word-related results remain distinct.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentA].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons["any-native-document-properties"], timeout: 60)
        revealNativeProperty(app, app.buttons[topicMenuA])
        revealNativeProperty(app, app.buttons[wordMenuA])
        XCTAssertTrue(app.buttons[topicMenuA].label.contains(topicTitle))
        XCTAssertTrue(app.buttons[wordMenuA].label.contains(wordTitle))
        XCTAssertEqual(app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-derived-actions-")).count, 2)
        tapWhenEnabled(app.buttons[wordMenuA])
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מסמכים מקושרים", "Related documents")).firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[wordTitle], timeout: 60)
        waitFor(NSPredicate(format: "exists == true"), object: relatedList, timeout: 60)
        waitUntilEnabled(relatedDocument(documentA), timeout: 60)
        XCTAssertFalse(relatedDocument(documentB).exists)
    }

    func testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen() async throws {
        let fixture = try HanlinMountedFixtureClient(environment: ProcessInfo.processInfo.environment)
        defer { fixture.close() }
        // This is an ordinary trusted HTTPS request. A missing fixture or untrusted
        // certificate fails before onboarding; there is no trust override or skip.
        try await fixture.requireReady()

        let scope = UUID(), suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Hanlin UI Space " + suffix
        let documentName = "Hanlin source " + suffix
        let cancelledTitle = "Hanlin cancelled " + suffix
        let approvedTitle = "Hanlin approved " + suffix
        let selectedText = "ש\u{05B8}\u{05C1}לו\u{05B9}ם 👩🏽‍💻 A " + suffix
        let unselectedText = "UNSELECTED_CANARY_" + scope.uuidString
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        try createNamedItemWithObservedTransition(app, action: "any-native-new-document", title: documentName)

        tapWhenEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        let blocks = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        let first = blocks.firstMatch
        waitUntilEnabled(first)
        let selectedIdentifier = first.identifier
        XCTAssertTrue(selectedIdentifier.hasPrefix("any-native-block-"))
        first.tap(); first.typeText(selectedText)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        waitForHanlinSourceSave(app)
        requireExactHanlinText(first, expected: selectedText)

        tapWhenEnabled(app.buttons["any-native-document-options"])
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "הוספת פסקה", "Add paragraph")).firstMatch)
        let second = blocks.matching(NSPredicate(
            format: "identifier != %@", selectedIdentifier)).firstMatch
        waitUntilEnabled(second, timeout: 60)
        let unselectedIdentifier = second.identifier
        XCTAssertNotEqual(unselectedIdentifier, selectedIdentifier)
        second.tap(); second.typeText(unselectedText)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        waitForHanlinSourceSave(app)
        requireExactHanlinText(second, expected: unselectedText)
        XCTAssertEqual(blocks.count, 2)

        // Cold opening removes prior in-memory typing/selection ownership. The
        // real Select block menu below, not a launch flag, establishes selection.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        let sourceRow = app.buttons[documentName].firstMatch
        waitUntilEnabled(sourceRow, timeout: 60)
        let objectPrefix = "any-native-hierarchy-row-"
        XCTAssertTrue(sourceRow.identifier.hasPrefix(objectPrefix))
        let objectID = String(sourceRow.identifier.dropFirst(objectPrefix.count))
        XCTAssertFalse(objectID.isEmpty)
        sourceRow.tap()
        let selected = app.textViews[selectedIdentifier]
        let unselected = app.textViews[unselectedIdentifier]
        waitUntilEnabled(selected, timeout: 60)
        requireExactHanlinText(selected, expected: selectedText)
        requireExactHanlinText(unselected, expected: unselectedText)
        XCTAssertEqual(blocks.count, 2)
        let options = app.buttons["any-native-document-options"]
        waitFor(NSPredicate(format: "value == %@ OR value == %@",
                            "אין בלוק נבחר", "No block selected"), object: options, timeout: 15)
        try selectHanlinBlockFromNativeMenu(app, textView: selected)
        waitFor(NSPredicate(format: "value == %@ OR value == %@",
                            "העיצוב השמור: כיוון אוטומטי, יישור טבעי",
                            "Saved style: Automatic direction, alignment Natural"),
                object: options, timeout: 15)

        let scenario = HanlinMountedFixtureScenario(
            selectedBlockID: String(selectedIdentifier.dropFirst("any-native-block-".count)),
            selectedText: selectedText, unselectedText: unselectedText,
            documentTitle: documentName, cancelledTitle: cancelledTitle,
            approvedTitle: approvedTitle, objectReference: objectID)
        try await fixture.register(scenario)

        tapWhenEnabled(app.buttons["any-native-hanlin"])
        try configureHanlinThroughNormalFields(app, fixture: fixture)
        let share = app.buttons["pinkha.hanlin.share-context"]
        tapWhenEnabled(share)
        tapWhenEnabled(app.buttons["pinkha.hanlin.consent.read-context.cancel"])
        waitUntilEnabled(share)
        sendHanlinPrompt(app, text: "Check the available actions without reading source text.")
        let denied = try await fixture.waitForPhase(1)
        XCTAssertEqual(denied.checks["denied_read_catalog_omits_read_tool"], true)
        XCTAssertEqual(denied.checks["denied_read_has_no_source_text"], true)
        waitForHanlinMarker(app, text: "PINKHA_HANLIN_DENIED_READ_CHECKED")

        tapWhenEnabled(share)
        tapWhenEnabled(app.buttons["pinkha.hanlin.consent.read-context.allow"])
        waitFor(NSPredicate(format: "exists == true AND enabled == false"),
                object: share, timeout: 20)
        sendHanlinPrompt(app, text: "Read only the selected block, then offer the cancelled draft page.")
        let read = try await fixture.waitForPhase(3)
        XCTAssertEqual(read.checks["selected_payload_exact_block_and_text"], true)
        XCTAssertEqual(read.checks["unselected_text_never_disclosed"], true)
        XCTAssertTrue(read.registeredObjectCompared)
        XCTAssertEqual(read.observedObjectSHA256, hanlinSHA256(objectID))
        let observedSpaceHash = try XCTUnwrap(read.observedSpaceSHA256)
        let cancelSpace = try requireHanlinCreationPrompt(app, title: cancelledTitle)
        XCTAssertEqual(hanlinSHA256(cancelSpace), observedSpaceHash)
        tapWhenEnabled(app.buttons["pinkha.hanlin.consent.create-page.cancel"])
        let cancelled = try await fixture.waitForPhase(4)
        XCTAssertEqual(cancelled.checks["cancel_creation_refused"], true)
        waitForHanlinMarker(app, text: "PINKHA_HANLIN_CANCELLED_CREATE_CHECKED")

        sendHanlinPrompt(app, text: "Offer the separately approved draft page.")
        let offered = try await fixture.waitForPhase(5)
        XCTAssertEqual(offered.checks["allowed_creation_new_exact_call"], true)
        let approvedSpace = try requireHanlinCreationPrompt(app, title: approvedTitle)
        XCTAssertEqual(approvedSpace, cancelSpace)
        XCTAssertEqual(hanlinSHA256(approvedSpace), observedSpaceHash)
        tapWhenEnabled(app.buttons["pinkha.hanlin.consent.create-page.allow"])
        let completed = try await fixture.waitForPhase(6)
        try completed.requireComplete()
        waitForHanlinMarker(app, text: "PINKHA_HANLIN_APPROVED_CREATE_CHECKED")
        try requireHanlinCreatedReceipt(app)
        let metadata = XCTAttachment(data: try JSONEncoder().encode(completed),
                                     uniformTypeIdentifier: "public.json")
        metadata.name = "hanlin-mounted-provider-sanitized-status"
        metadata.lifetime = .keepAlways
        add(metadata)
        tapWhenEnabled(app.buttons["pinkha.hanlin.close"])
        waitUntilEnabled(selected, timeout: 30)
        requireExactHanlinText(selected, expected: selectedText)
        requireExactHanlinText(unselected, expected: unselectedText)
        XCTAssertEqual(blocks.count, 2)

        // Native Hanlin pages are ordinary Pages, without Wiki membership. Use
        // the real All documents list and never invent an ID from the empty
        // successful model-facing tool result.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "כל המסמכים", "All documents")).firstMatch,
            timeout: 60)
        let approvedRows = app.buttons.matching(NSPredicate(format: "label == %@", approvedTitle))
        waitUntilEnabled(approvedRows.firstMatch, timeout: 60)
        waitUntilEnabled(app.buttons[documentName].firstMatch, timeout: 60)
        XCTAssertEqual(approvedRows.count, 1)
        XCTAssertFalse(app.buttons.matching(NSPredicate(format: "label == %@", cancelledTitle)).firstMatch.exists)
        approvedRows.firstMatch.tap()
        waitUntilEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        XCTAssertTrue(app.navigationBars[approvedTitle].exists)
        XCTAssertEqual(blocks.count, 0, "Title-only creation must not copy the selected source into the new page.")

        reopenOwnedWorkspace(app, spaceName: spaceName)
        let reopenedSource = app.buttons[documentName].firstMatch
        waitUntilEnabled(reopenedSource, timeout: 60)
        XCTAssertEqual(reopenedSource.identifier, objectPrefix + objectID)
        reopenedSource.tap()
        waitUntilEnabled(selected, timeout: 60)
        requireExactHanlinText(selected, expected: selectedText)
        requireExactHanlinText(unselected, expected: unselectedText)
        XCTAssertEqual(blocks.count, 2)
    }

    private func waitForHanlinSourceSave(_ app: XCUIApplication) {
        let status = app.descendants(matching: .any)
            .matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"),
                object: status, timeout: 45)
    }

    private func requireExactHanlinText(_ element: XCUIElement, expected: String,
                                       file: StaticString = #filePath, line: UInt = #line) {
        waitUntilEnabled(element, timeout: 30, file: file, line: line)
        guard let actual = element.value as? String else {
            XCTFail("The actual source text has no readable AX value.", file: file, line: line)
            return
        }
        // Swift String equality permits canonically equivalent Unicode; exact
        // UTF-8 equality also detects altered combining-mark order and emoji.
        XCTAssertEqual(Array(actual.utf8), Array(expected.utf8), file: file, line: line)
    }

    private func selectHanlinBlockFromNativeMenu(_ app: XCUIApplication, textView: XCUIElement) throws {
        let prefix = "any-native-block-"
        guard textView.identifier.hasPrefix(prefix) else {
            throw HanlinMountedFixtureError.unavailableBlockMenu
        }
        let nativeID = String(textView.identifier.dropFirst(prefix.count))
        guard !nativeID.isEmpty else { throw HanlinMountedFixtureError.unavailableBlockMenu }
        let cells = app.cells.containing(.textView, identifier: textView.identifier)
        let cell = cells.firstMatch
        waitUntilEnabled(cell)
        XCTAssertEqual(cells.count, 1)
        let menus = cell.buttons.matching(identifier: "any-native-block-menu-" + nativeID)
        XCTAssertEqual(menus.count, 1)
        let menu = menus.firstMatch
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: menu, timeout: 30)
        XCTAssertTrue(cell.frame.intersects(menu.frame))
        // The actual explicit row menu preserves native UITextView selection.
        // No coordinate or programmatic selection bypass is used.
        menu.tap()
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "בחירת בלוק", "Select block")).firstMatch)
    }

    private func configureHanlinThroughNormalFields(_ app: XCUIApplication,
                                                    fixture: HanlinMountedFixtureClient) throws {
        let endpoint = app.textFields["pinkha.hanlin.connection.endpoint"]
        let model = app.textFields["pinkha.hanlin.connection.model"]
        let key = app.secureTextFields["pinkha.hanlin.connection.credential"]
        waitUntilEnabled(endpoint)
        XCTAssertTrue(["כתובת API מסוג HTTPS", "HTTPS API endpoint"].contains(endpoint.label))
        endpoint.tap()
        endpoint.typeKey("a", modifierFlags: .command)
        endpoint.typeText(fixture.providerURL.absoluteString)
        XCTAssertEqual(endpoint.value as? String, fixture.providerURL.absoluteString)
        waitUntilEnabled(model)
        XCTAssertTrue(["מזהה המודל", "Model identifier"].contains(model.label))
        model.tap(); model.typeText(fixture.model)
        XCTAssertEqual(model.value as? String, fixture.model)
        waitUntilEnabled(key)
        XCTAssertTrue(["מפתח API", "API key"].contains(key.label))
        key.tap(); key.typeText(fixture.providerKey)
        tapWhenEnabled(app.buttons["pinkha.hanlin.connect"])
        waitUntilEnabled(hanlinComposerInput(app))
    }

    private func hanlinComposerInput(_ app: XCUIApplication) -> XCUIElement {
        // The wrapper identifies the canonical composer as a whole. SwiftUI may
        // retain that scope or propagate its identifier to descendants.
        let deadline = ProcessInfo.processInfo.systemUptime + 30
        let scopes = app.descendants(matching: .any)
            .matching(identifier: "pinkha.hanlin.composer")
        waitFor(NSPredicate(format: "exists == true"), object: scopes.firstMatch, timeout: 30)
        let inputRoles = NSPredicate(format: "elementType == %d OR elementType == %d",
            XCUIElement.ElementType.textField.rawValue, XCUIElement.ElementType.textView.rawValue)
        var inputs: [XCUIElement] = []
        func include(_ element: XCUIElement) {
            // Resolve by accessibility element, then use exact element equality.
            // Never collapse two different controls by frame, label or value.
            if !inputs.contains(where: { $0.isEqual(element) }) { inputs.append(element) }
        }
        for scope in scopes.allElementsBoundByAccessibilityElement {
            if scope.elementType == .textField || scope.elementType == .textView { include(scope) }
            for input in scope.descendants(matching: .any).matching(inputRoles)
                .allElementsBoundByAccessibilityElement {
                include(input)
            }
        }
        XCTAssertEqual(inputs.count, 1, "The identified Hanlin composer must expose one real input.")
        // continueAfterFailure=false stops an ambiguous/missing result above.
        // The empty-result expression remains scoped and cannot select another field.
        let input = inputs.first ?? scopes.matching(inputRoles).firstMatch
        waitUntilEnabled(input, timeout: max(0, deadline - ProcessInfo.processInfo.systemUptime))
        XCTAssertTrue(input.isHittable, "The mounted Hanlin input must accept a real tap.")
        return input
    }

    private func sendHanlinPrompt(_ app: XCUIApplication, text: String) {
        let input = hanlinComposerInput(app)
        waitUntilEnabled(input)
        input.tap(); input.typeText(text)
        let send = app.buttons.matching(NSPredicate(format: "label == %@", "Send"))
        XCTAssertEqual(send.count, 1)
        tapWhenEnabled(send.firstMatch, timeout: 30)
    }

    private func waitForHanlinMarker(_ app: XCUIApplication, text: String) {
        waitFor(NSPredicate(format: "exists == true"), object: app.staticTexts[text].firstMatch, timeout: 45)
    }

    private func requireHanlinCreationPrompt(_ app: XCUIApplication, title: String) throws -> String {
        let explanation = app.staticTexts["pinkha.hanlin.consent.create-page.explanation"]
        waitFor(NSPredicate(format: "exists == true AND label BEGINSWITH %@", title + "\n\n"),
                object: explanation, timeout: 45)
        let label = explanation.label
        guard label.hasPrefix(title + "\n\n"),
              let last = label.split(separator: "\n").last, !last.isEmpty,
              String(last) != title else { throw HanlinMountedFixtureError.invalidCreatePrompt }
        XCTAssertTrue(app.buttons["pinkha.hanlin.consent.create-page.cancel"].isHittable)
        XCTAssertTrue(app.buttons["pinkha.hanlin.consent.create-page.allow"].isHittable)
        return String(last)
    }

    private func requireHanlinCreatedReceipt(_ app: XCUIApplication) throws {
        let receipts = app.staticTexts.matching(NSPredicate(
            format: "label == %@ OR label == %@", "יצירת הדף אושרה.", "Page creation confirmed."))
        for _ in 0..<4 {
            if receipts.firstMatch.exists && receipts.firstMatch.isHittable {
                XCTAssertEqual(receipts.count, 1)
                return
            }
            let scroll = app.scrollViews.firstMatch
            guard scroll.exists && scroll.isHittable else {
                throw HanlinMountedFixtureError.unavailableReceipt
            }
            scroll.swipeUp()
        }
        throw HanlinMountedFixtureError.unavailableReceipt
    }

    private func hanlinSHA256(_ value: String) -> String {
        SHA256.hash(data: Data(value.utf8)).map { String(format: "%02x", $0) }.joined()
    }

    /// DIAGNOSTIC OBSERVATION ONLY. Reaching these capture points does not
    /// assert an exported file, a writable provider, an import, or a mapping.
    func testObserveCanonicalArchiveSystemPickers() throws {
        let scope = UUID(), suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Archive picker observation " + suffix
        let documentName = "Empty archive observation " + suffix
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentName)
        waitUntilEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        XCTAssertTrue(app.navigationBars[documentName].exists)
        XCTAssertEqual(app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-")).count, 0)
        try requireArchiveObservationPastOnboarding(app)
        openCanonicalArchiveObservationEntry(app)
        let export = app.buttons["any-native-archive-export"]
        tapWhenEnabled(export, timeout: 45)
        try captureCanonicalPickerObservation(app, coveredEntry: export, phase: "exporter")

        // End the uncommitted dialog without guessing an OS Save/Cancel label.
        // Reauthentication and the document entry are the normal existing UI.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentName].firstMatch, timeout: 60)
        waitUntilEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        XCTAssertTrue(app.navigationBars[documentName].exists)
        try requireArchiveObservationPastOnboarding(app)
        openCanonicalArchiveObservationEntry(app)
        let importer = app.buttons["any-native-archive-import"]
        tapWhenEnabled(importer, timeout: 45)
        try captureCanonicalPickerObservation(app, coveredEntry: importer, phase: "importer")
        // defer terminates this second uncommitted picker. No URL is selected,
        // no sandbox file is supplied, and no prepare/import action is invoked.
    }

    private func openCanonicalArchiveObservationEntry(_ app: XCUIApplication) {
        tapWhenEnabled(app.buttons["any-native-document-options"])
        tapWhenEnabled(app.buttons["any-native-canonical-transfer"])
        waitUntilEnabled(app.buttons["any-native-archive-export"], timeout: 45)
        // This existing button becomes enabled only after the actual transfer
        // model has mounted with the native writable document authority.
        waitUntilEnabled(app.buttons["any-native-archive-import"], timeout: 45)
    }

    private func requireArchiveObservationPastOnboarding(_ app: XCUIApplication) throws {
        guard app.state == .runningForeground,
              !app.buttons["any-native-account-create"].exists,
              !app.switches["any-native-backup-acknowledged"].exists,
              !app.buttons["any-native-backup-continue"].exists,
              !app.secureTextFields["any-native-account-restore-phrase"].exists else {
            // Do not capture a tree or screenshot of onboarding/recovery.
            throw CanonicalPickerObservationError.onboardingOrRecoveryVisible
        }
    }

    private func captureCanonicalPickerObservation(_ app: XCUIApplication,
                                                     coveredEntry: XCUIElement,
                                                     phase: String) throws {
        try requireArchiveObservationPastOnboarding(app)
        // Poll only the real app-owned initiating control. No OS-provider name,
        // Save/Cancel control, directory, or filename is assumed. Disabled-but-
        // still-visible export preparation is not accepted as modal coverage.
        let expectation = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == false OR (enabled == true AND hittable == false)"),
            object: coveredEntry)
        let coverage = XCTWaiter.wait(for: [expectation], timeout: 45)
        try requireArchiveObservationPastOnboarding(app)
        // AX queries and screenshot collection use XCTest's normal automation
        // quiescence. There are no timed taps or fabricated system-picker state.
        let tree = app.debugDescription
        try requireArchiveObservationPastOnboarding(app)
        let maximumBytes = 131_072
        let utf8 = Data(tree.utf8)
        let bounded = String(decoding: utf8.prefix(maximumBytes), as: UTF8.self)
        let ax = XCTAttachment(string: bounded)
        ax.name = "OBSERVATION_ONLY_" + phase + "_private_app_AX"
        ax.lifetime = .keepAlways
        add(ax)
        let image = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        image.name = "OBSERVATION_ONLY_" + phase + "_private_screen"
        image.lifetime = .keepAlways
        add(image)
        let metadata = XCTAttachment(string:
            "scope=observation_only_not_export_import_or_mapping_acceptance\n" +
            "phase=" + phase + "\n" +
            "appOwnedEntryCovered=" + String(coverage == .completed) + "\n" +
            "axOriginalBytes=" + String(utf8.count) + "\n" +
            "axCapturedBytes=" + String(min(utf8.count, maximumBytes)) + "\n" +
            "privateArtifactRequiresScreening=true\n" +
            "systemPickerIdentityAndWritableDestinationNotAsserted=true\n" +
            "noUserSaveSelectionOrImportWasInvoked=true\n")
        metadata.name = "OBSERVATION_ONLY_" + phase + "_scope"
        metadata.lifetime = .keepAlways
        add(metadata)
        guard coverage == .completed else {
            // Preserve the actual post-action observation but fail the diagnostic
            // if the normal entry never becomes covered. This is not a skip.
            throw CanonicalPickerObservationError.entryDidNotPresentAnotherSurface
        }
    }

    private func waitForNativeEditorInput(_ app: XCUIApplication, _ editor: XCUIElement,
                                          file: StaticString = #filePath, line: UInt = #line) {
        let expectation = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == true AND enabled == true"), object: editor)
        let result = XCTWaiter.wait(for: [expectation], timeout: 30)
        if result != .completed {
            // Capture only this disposable document after the backup/recovery
            // surfaces are gone. This attachment is diagnosis, never acceptance.
            do {
                try requireArchiveObservationPastOnboarding(app)
                let tree = String(decoding: app.debugDescription.utf8.prefix(131_072), as: UTF8.self)
                try requireArchiveObservationPastOnboarding(app)
                let state = XCTAttachment(string: tree)
                state.name = "FAILED_EDITOR_PRIVATE_post_onboarding_AX"
                state.lifetime = .keepAlways; add(state)
                let screen = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
                screen.name = "FAILED_EDITOR_PRIVATE_post_onboarding_screen"
                screen.lifetime = .keepAlways; add(screen)
            } catch {
                let refusal = XCTAttachment(string: "Post-onboarding capture guard refused; no UI contents captured.")
                refusal.name = "FAILED_EDITOR_capture_refused"; refusal.lifetime = .keepAlways; add(refusal)
            }
        }
        XCTAssertEqual(result, .completed, "The actual native editor did not appear after adding a paragraph.",
                       file: file, line: line)
    }

    private func collapseInspectorForBackgroundRead(_ app: XCUIApplication,
                                                    file: StaticString = #filePath, line: UInt = #line) {
        let sheet = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-inspector-sheet-")).firstMatch
        waitUntilEnabled(sheet, timeout: 30, file: file, line: line)
        // These are normal sheet-header drags, scoped to the retained presenter's
        // actual AX element. No direct selection binding or test-only dismissal.
        for _ in 0..<2 {
            if !sheet.exists || sheet.identifier == "torah-inspector-sheet-peek" { return }
            let header = sheet.navigationBars.firstMatch
            waitUntilEnabled(header, timeout: 10, file: file, line: line)
            let start = header.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.25))
            let end = app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.9))
            start.press(forDuration: 0.15, thenDragTo: end)
        }
        waitFor(NSPredicate(format: "exists == false OR identifier == %@", "torah-inspector-sheet-peek"),
                object: sheet, timeout: 10, file: file, line: line)
    }

    private func revealNativeProperty(_ app: XCUIApplication, _ target: XCUIElement,
                                      listID: String = "any-native-properties-list", scrollDown: Bool = false,
                                      file: StaticString = #filePath, line: UInt = #line) {
        let list = app.descendants(matching: .any).matching(identifier: listID).firstMatch
        waitUntilEnabled(list, timeout: 30, file: file, line: line)
        for _ in 0..<8 {
            if target.exists && target.isEnabled && target.isHittable { return }
            if scrollDown { list.swipeDown() } else { list.swipeUp() }
        }
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: target, timeout: 10, file: file, line: line)
    }

    private func toggleNativePropertyVisibility(_ row: XCUIElement, expected: String,
                                                file: StaticString = #filePath, line: UInt = #line) {
        // The same iPad AX shape already observed for the backup Toggle: a
        // semantic row can contain a separate physical switch control.
        let children = row.descendants(matching: .switch)
        let control = children.count == 1 ? children.firstMatch : row
        XCTAssertLessThanOrEqual(children.count, 1, file: file, line: line)
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true AND value == %@", expected),
                object: control, timeout: 10, file: file, line: line)
        control.tap()
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

    // BEGIN_FAILED_CREATE_TRANSITION_CANDIDATE_451483
    // Test-runner-only transition/hittability candidate. The original run does
    // not establish a duplicate identifier or a native creation failure.
    private enum NativeCreateTransitionError: Error {
        case unsupportedAction, controlNotReady(String), ambiguousControl(String)
        case controlChanged(String), nameSheetTransitionNotObserved
    }

    private func recordNativeCreateTransition(_ app: XCUIApplication, phase: String) {
        do {
            try requireArchiveObservationPastOnboarding(app)
            let identifiers = [
                "any-native-create-menu", "any-native-new-document",
                "any-native-new-note", "any-native-new-folder",
                "any-native-name-input", "any-native-name-confirm"
            ]
            var controls: [[String: Any]] = []
            for identifier in identifiers {
                let query = app.descendants(matching: .any).matching(identifier: identifier)
                let count = query.count
                var candidates: [[String: Any]] = []
                for element in query.allElementsBoundByIndex.prefix(12) {
                    let frame = element.frame
                    let numbers = [Double(frame.origin.x), Double(frame.origin.y),
                                   Double(frame.width), Double(frame.height)]
                    candidates.append([
                        "type": element.elementType.rawValue,
                        "label": element.label, "exists": element.exists,
                        "enabled": element.isEnabled, "hittable": element.isHittable,
                        "frame": numbers.allSatisfy(\.isFinite) ? numbers : [],
                        "frameFinite": numbers.allSatisfy(\.isFinite)
                    ])
                }
                controls.append(["identifier": identifier, "count": count,
                                 "candidates": candidates, "truncated": count > 12])
            }
            let data = try JSONSerialization.data(withJSONObject: [
                "schema": "native-create-transition-observation/v1",
                "phase": phase, "controls": controls,
                "duplicateIdentifierRootCauseEstablished": false
            ], options: [.sortedKeys])
            let metadata = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
            metadata.name = "NATIVE_CREATE_TRANSITION_" + phase + "_controls"
            metadata.lifetime = .keepAlways
            add(metadata)
            try requireArchiveObservationPastOnboarding(app)
            let tree = String(decoding: Data(app.debugDescription.utf8).prefix(131_072), as: UTF8.self)
            try requireArchiveObservationPastOnboarding(app)
            let ax = XCTAttachment(string: tree)
            ax.name = "NATIVE_CREATE_TRANSITION_" + phase + "_private_AX"
            ax.lifetime = .keepAlways
            add(ax)
            let screen = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
            screen.name = "NATIVE_CREATE_TRANSITION_" + phase + "_private_screen"
            screen.lifetime = .keepAlways
            add(screen)
        } catch {
            // Diagnostic unavailability cannot replace the first UI failure or
            // expose onboarding/recovery content.
            let unavailable = XCTAttachment(string: "Post-onboarding observation unavailable: " + phase)
            unavailable.name = "NATIVE_CREATE_TRANSITION_" + phase + "_observation_unavailable"
            unavailable.lifetime = .keepAlways
            add(unavailable)
        }
    }

    private func createNamedItemWithObservedTransition(_ app: XCUIApplication,
                                                       action: String, title: String) throws {
        guard action == "any-native-new-document" else {
            throw NativeCreateTransitionError.unsupportedAction
        }
        try requireArchiveObservationPastOnboarding(app)
        let fieldQuery = app.textFields.matching(identifier: "any-native-name-input")
        guard fieldQuery.count == 0 else {
            recordNativeCreateTransition(app, phase: "unexpected_existing_name_input")
            throw NativeCreateTransitionError.controlChanged("initial_name_input")
        }

        func stableReady(_ query: XCUIElementQuery, phase: String,
                         timeout: TimeInterval, labels: Set<String>? = nil) throws -> XCUIElement {
            var previousFrame: CGRect?
            var firstMatchingSample: TimeInterval?
            let predicate = NSPredicate { _, _ in
                guard query.count == 1 else {
                    previousFrame = nil; firstMatchingSample = nil
                    return false
                }
                let element = query.element(boundBy: 0)
                // Read the related attributes from one real accessibility
                // snapshot. Independent cross-process property reads can consume
                // this unchanged readiness budget before a second stable sample.
                guard element.exists, let snapshot = try? element.snapshot() else {
                    previousFrame = nil; firstMatchingSample = nil
                    return false
                }
                let frame = snapshot.frame
                guard snapshot.isEnabled, element.isHittable,
                      labels.map({ $0.contains(snapshot.label) }) ?? true,
                      !frame.isNull, !frame.isInfinite, frame.width > 0, frame.height > 0 else {
                    previousFrame = nil; firstMatchingSample = nil
                    return false
                }
                let now = ProcessInfo.processInfo.systemUptime
                if previousFrame == frame, let firstMatchingSample,
                   now - firstMatchingSample >= 0.15 { return true }
                if previousFrame != frame || firstMatchingSample == nil {
                    previousFrame = frame; firstMatchingSample = now
                }
                return false
            }
            let expectation = XCTNSPredicateExpectation(predicate: predicate, object: app)
            guard XCTWaiter.wait(for: [expectation], timeout: timeout) == .completed else {
                recordNativeCreateTransition(app, phase: phase + "_not_ready")
                if query.count > 1 { throw NativeCreateTransitionError.ambiguousControl(phase) }
                throw NativeCreateTransitionError.controlNotReady(phase)
            }
            guard query.count == 1 else {
                recordNativeCreateTransition(app, phase: phase + "_changed")
                throw NativeCreateTransitionError.controlChanged(phase)
            }
            return query.element(boundBy: 0)
        }

        let toolbar = try stableReady(app.buttons.matching(identifier: "any-native-create-menu"),
                                      phase: "toolbar", timeout: 60)
        toolbar.tap()
        let actionQuery = app.buttons.matching(identifier: action)
        let labels: Set<String> = [
            "New document",
            "\u{05DE}\u{05E1}\u{05DE}\u{05DA} \u{05D7}\u{05D3}\u{05E9}"
        ]
        let menuAction = try stableReady(actionQuery, phase: "menu_action", timeout: 30, labels: labels)
        let selectedFrame = menuAction.frame
        recordNativeCreateTransition(app, phase: "before_menu_action")
        guard actionQuery.count == 1, menuAction.exists, menuAction.isEnabled,
              menuAction.isHittable, menuAction.frame == selectedFrame,
              labels.contains(menuAction.label) else {
            recordNativeCreateTransition(app, phase: "menu_action_changed_before_tap")
            throw NativeCreateTransitionError.controlChanged("menu_action_before_tap")
        }
        menuAction.tap() // One actual UI action; no retap or backend fallback.

        let confirmQuery = app.buttons.matching(identifier: "any-native-name-confirm")
        let transition = NSPredicate { _, _ in
            let menu = actionQuery.firstMatch
            guard !menu.exists || !menu.isHittable,
                  fieldQuery.count == 1, confirmQuery.count == 1 else { return false }
            let field = fieldQuery.element(boundBy: 0)
            let confirm = confirmQuery.element(boundBy: 0)
            return field.exists && field.isEnabled && field.isHittable
                && confirm.exists && confirm.isEnabled && confirm.isHittable
        }
        let expectation = XCTNSPredicateExpectation(predicate: transition, object: app)
        guard XCTWaiter.wait(for: [expectation], timeout: 30) == .completed else {
            recordNativeCreateTransition(app, phase: "name_sheet_transition_not_observed")
            throw NativeCreateTransitionError.nameSheetTransitionNotObserved
        }
        recordNativeCreateTransition(app, phase: "name_sheet_ready")
        guard fieldQuery.count == 1, fieldQuery.firstMatch.isHittable else {
            recordNativeCreateTransition(app, phase: "name_input_changed_before_typing")
            throw NativeCreateTransitionError.controlChanged("name_input_before_typing")
        }
        let field = fieldQuery.element(boundBy: 0)
        field.tap()
        field.typeText(title)
        let confirm = try stableReady(confirmQuery, phase: "name_confirm", timeout: 30)
        confirm.tap()
    }
    // END_FAILED_CREATE_TRANSITION_CANDIDATE_451483


    // BEGIN_FAILED_HIERARCHY_OBSERVATION_CANDIDATE_451483
    private func recordNativeHierarchyTransition(_ app: XCUIApplication, phase: String,
                                                  source: XCUIElement, destination: XCUIElement) {
        do {
            try requireArchiveObservationPastOnboarding(app)
            func control(_ element: XCUIElement) -> [String: Any] {
                let exists = element.exists
                guard exists else { return ["exists": false, "propertiesResolved": false] }
                let frame = element.frame
                let numbers = [Double(frame.origin.x), Double(frame.origin.y),
                               Double(frame.width), Double(frame.height)]
                return [
                    "identifier": element.identifier, "label": element.label,
                    "type": element.elementType.rawValue, "exists": true, "propertiesResolved": true,
                    "enabled": element.isEnabled, "hittable": element.isHittable,
                    "frame": numbers.allSatisfy(\.isFinite) ? numbers : [],
                    "frameFinite": numbers.allSatisfy(\.isFinite)
                ]
            }
            let libraries = app.descendants(matching: .any).matching(identifier: "any-native-library")
            var states: [[String: Any]] = []
            for library in libraries.allElementsBoundByIndex.prefix(8) {
                var row = control(library)
                if row["exists"] as? Bool == true { row["value"] = library.value as? String ?? "" }
                states.append(row)
            }
            let record: [String: Any] = [
                "schema": "native-hierarchy-transition-observation/v1",
                "phase": phase, "source": control(source), "destination": control(destination),
                "libraryCount": libraries.count, "libraryStates": states,
                "visibleProgressIndicatorCount": app.progressIndicators.allElementsBoundByIndex.filter(\.exists).count,
                "alerts": app.alerts.allElementsBoundByIndex.prefix(8).map(control),
                "moveActionCount": app.buttons.matching(identifier: "any-native-hierarchy-move").count,
                "nativeOrGestureRootCauseEstablished": false
            ]
            let metadata = XCTAttachment(data: try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys]),
                                         uniformTypeIdentifier: "public.json")
            metadata.name = "NATIVE_HIERARCHY_TRANSITION_" + phase + "_controls"
            metadata.lifetime = .keepAlways
            add(metadata)
            try requireArchiveObservationPastOnboarding(app)
            let ax = XCTAttachment(string: String(decoding: Data(app.debugDescription.utf8).prefix(131_072), as: UTF8.self))
            ax.name = "NATIVE_HIERARCHY_TRANSITION_" + phase + "_private_AX"
            ax.lifetime = .keepAlways
            add(ax)
            try requireArchiveObservationPastOnboarding(app)
            let screen = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
            screen.name = "NATIVE_HIERARCHY_TRANSITION_" + phase + "_private_screen"
            screen.lifetime = .keepAlways
            add(screen)
        } catch {
            let unavailable = XCTAttachment(string: "Post-onboarding hierarchy observation unavailable: " + phase)
            unavailable.name = "NATIVE_HIERARCHY_TRANSITION_" + phase + "_observation_unavailable"
            unavailable.lifetime = .keepAlways
            add(unavailable)
        }
    }

    private func waitForObservedHierarchy(_ app: XCUIApplication, predicate: NSPredicate,
                                          object: Any, timeout: TimeInterval, phase: String,
                                          source: XCUIElement, destination: XCUIElement,
                                          file: StaticString = #filePath, line: UInt = #line) -> Bool {
        // Exactly one wait with the caller's original budget. Capture failure
        // evidence before XCTest reports the same first unmet UI predicate.
        let expectation = XCTNSPredicateExpectation(predicate: predicate, object: object)
        let result = XCTWaiter.wait(for: [expectation], timeout: timeout)
        guard result == .completed else {
            recordNativeHierarchyTransition(app, phase: phase + "_not_ready",
                                            source: source, destination: destination)
            XCTAssertEqual(result, .completed, "Expected UI state was not reached: " + phase,
                           file: file, line: line)
            return false
        }
        return true
    }

    private func moveHierarchyItemWithObservedTransition(_ app: XCUIApplication, source: XCUIElement,
                                                         destinationName: String) -> Bool {
        let move = app.buttons.matching(identifier: "any-native-hierarchy-move")
        let destinations = app.buttons.matching(NSPredicate(format: "label == %@", destinationName))
        let destination = destinations.firstMatch
        recordNativeHierarchyTransition(app, phase: "before_context_menu",
                                        source: source, destination: destination)
        guard waitForObservedHierarchy(app,
                predicate: NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: source, timeout: 30, phase: "source_for_context_menu",
                source: source, destination: destination) else { return false }
        source.press(forDuration: 1.1) // Original actual context-menu gesture.
        let menuReady = NSPredicate { _, _ in
            move.count == 1 && move.firstMatch.exists && move.firstMatch.isEnabled
                && move.firstMatch.isHittable
        }
        guard waitForObservedHierarchy(app, predicate: menuReady, object: app, timeout: 30,
                phase: "move_context_action", source: source, destination: destination) else { return false }
        recordNativeHierarchyTransition(app, phase: "before_move_action",
                                        source: source, destination: destination)
        guard move.count == 1, move.firstMatch.isHittable else {
            recordNativeHierarchyTransition(app, phase: "move_action_changed",
                                            source: source, destination: destination)
            XCTFail("Move context action changed before its single tap")
            return false
        }
        move.element(boundBy: 0).tap()
        let titles = ["Move to folder",
                      "\u{05D4}\u{05E2}\u{05D1}\u{05E8}\u{05D4} \u{05DC}\u{05EA}\u{05D9}\u{05E7}\u{05D9}\u{05D9}\u{05D4}"]
        let sheet = app.navigationBars.matching(NSPredicate(format: "identifier IN %@ OR label IN %@", titles, titles))
        let sheetReady = NSPredicate { _, _ in
            sheet.count == 1 && sheet.firstMatch.exists
                && destinations.count == 1 && destination.exists
                && destination.isEnabled && destination.isHittable
        }
        // The original destination lookup had 30 seconds. Sheet and folder
        // readiness share that same wait; no additional transition timeout.
        guard waitForObservedHierarchy(app, predicate: sheetReady, object: app, timeout: 30,
                phase: "move_sheet_destination", source: source, destination: destination) else { return false }
        recordNativeHierarchyTransition(app, phase: "before_move_destination",
                                        source: source, destination: destination)
        guard sheet.count == 1, sheet.firstMatch.exists, destinations.count == 1,
              destination.exists, destination.isEnabled, destination.isHittable else {
            recordNativeHierarchyTransition(app, phase: "move_destination_changed",
                                            source: source, destination: destination)
            XCTFail("Move sheet destination changed before its single tap")
            return false
        }
        destination.tap()
        return true
    }
    // END_FAILED_HIERARCHY_OBSERVATION_CANDIDATE_451483

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


    // BEGIN_CANONICAL_ARCHIVE_ROUNDTRIP_V1
    func testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies() throws {
        executionTimeAllowance = 1_800
        let scope = UUID()
        let suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Archive UI Space " + suffix
        let sourceName = "Archive source " + suffix
        let destinationName = "Archive destination " + suffix
        let reference = "Genesis 1:1"
        let sourceFile = "canonical-source-" + scope.uuidString + ".json"
        let destinationFile = "canonical-destination-" + scope.uuidString + ".json"
        let sourceColdFile = "canonical-source-cold-" + scope.uuidString + ".json"
        let destinationBody = "יעד לייבוא: הטקסט הזה נשמר 246 " + suffix

        func hash(_ text: String) -> String {
            SHA256.hash(data: Data(text.utf8)).map { String(format: "%02x", $0) }.joined()
        }
        func exactBody(_ element: XCUIElement, _ expected: String) -> String {
            waitFor(NSPredicate(format: "exists == true AND value == %@", expected),
                    object: element, timeout: 60)
            let actual = element.value as? String ?? ""
            XCTAssertEqual(Array(actual.utf8), Array(expected.utf8),
                           "Native readback must preserve every UTF-8 byte.")
            return actual
        }
        func returnToLibrary() {
            let back = app.navigationBars.buttons.matching(
                NSPredicate(format: "label == %@ OR label == %@", "ספרייה", "Library")).firstMatch
            tapWhenEnabled(back)
            waitUntilEnabled(app.buttons["any-native-create-menu"], timeout: 60)
        }

        enum FileJourneyError: Error {
            case controlNotReady(String), ambiguousControl(String), unexpectedFileName
        }
        func captureFilesState(_ phase: String) throws {
            try requireArchiveObservationPastOnboarding(app)
            let tree = String(decoding: Data(app.debugDescription.utf8).prefix(131_072), as: UTF8.self)
            try requireArchiveObservationPastOnboarding(app)
            let ax = XCTAttachment(string: tree)
            ax.name = "ARCHIVE_ROUNDTRIP_" + phase + "_private_AX"
            ax.lifetime = .keepAlways
            self.add(ax)
            let screenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
            screenshot.name = "ARCHIVE_ROUNDTRIP_" + phase + "_private_screen"
            screenshot.lifetime = .keepAlways
            self.add(screenshot)
        }
        func uniqueReady(_ query: XCUIElementQuery, phase: String,
                         timeout: TimeInterval = 30) throws -> XCUIElement {
            let expectation = XCTNSPredicateExpectation(
                predicate: NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: query.firstMatch)
            guard XCTWaiter.wait(for: [expectation], timeout: timeout) == .completed else {
                try captureFilesState(phase + "_NOT_READY")
                throw FileJourneyError.controlNotReady(phase)
            }
            guard query.count == 1 else {
                try captureFilesState(phase + "_AMBIGUOUS")
                throw FileJourneyError.ambiguousControl(phase)
            }
            return query.firstMatch
        }
        func requireArchiveFilesDirectory(phase: String) throws {
            // One total deadline includes every navigation query and action.
            // A missing/unreachable Exports location remains a real failure.
            let started = ProcessInfo.processInfo.systemUptime
            let deadline = started + 15
            var navigation: [String] = []
            var observedExports = false
            var pinkhaIconTarget: [String: Any] = [:]
            defer {
                let record: [String: Any] = [
                    "schema": "archive-files-directory-navigation/v1",
                    "phase": phase, "budgetSeconds": 15,
                    "elapsedSeconds": ProcessInfo.processInfo.systemUptime - started,
                    "attemptedActions": navigation, "observedExports": observedExports,
                    "pinkhaIconTarget": pinkhaIconTarget,
                    "fallbackOrRetry": false
                ]
                if let data = try? JSONSerialization.data(withJSONObject: record, options: [.sortedKeys]) {
                    let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
                    attachment.name = "ARCHIVE_ROUNDTRIP_" + phase + "_directory_navigation"
                    attachment.lifetime = .keepAlways
                    self.add(attachment)
                }
            }
            func fail(_ stage: String, ambiguous: Bool = false) throws -> Never {
                do { try captureFilesState(phase + "_" + stage) }
                catch {
                    let unavailable = XCTAttachment(string: "Post-onboarding Files observation unavailable.")
                    unavailable.name = "ARCHIVE_ROUNDTRIP_" + phase + "_observation_unavailable"
                    unavailable.lifetime = .keepAlways
                    self.add(unavailable)
                }
                if ambiguous { throw FileJourneyError.ambiguousControl(phase + "_" + stage) }
                throw FileJourneyError.controlNotReady(phase + "_" + stage)
            }
            func remaining(_ stage: String) throws -> TimeInterval {
                let value = deadline - ProcessInfo.processInfo.systemUptime
                guard value > 0 else { try fail(stage + "_directory_budget_exhausted") }
                return value
            }
            func ready(_ query: XCUIElementQuery, stage: String,
                       hittable: Bool = true) throws -> XCUIElement {
                let budget = try remaining(stage)
                let format = hittable
                    ? "exists == true AND enabled == true AND hittable == true"
                    : "exists == true"
                let expectation = XCTNSPredicateExpectation(predicate: NSPredicate(format: format),
                                                           object: query.firstMatch)
                guard XCTWaiter.wait(for: [expectation], timeout: budget) == .completed else {
                    try fail(stage + "_NOT_READY")
                }
                _ = try remaining(stage)
                guard query.count == 1 else { try fail(stage + "_AMBIGUOUS", ambiguous: true) }
                _ = try remaining(stage + "_resolved")
                return query.element(boundBy: 0)
            }
            let directory = app.buttons.matching(NSPredicate(
                format: "label == %@ OR label BEGINSWITH %@", "Exports", "Exports,"))
            if directory.count == 1, directory.firstMatch.exists,
               directory.firstMatch.isEnabled, directory.firstMatch.isHittable {
                _ = try remaining("already_exports")
                observedExports = true
                return
            }

            // This exact Cell is present in the original failed Files AX tree.
            let local = app.cells.matching(NSPredicate(format: "identifier IN %@", [
                "DOC.sidebar.item.On My iPad",
                "DOC.sidebar.item.\u{05D1}-iPad \u{05E9}\u{05DC}\u{05D9}"
            ]))
            let localControl = try ready(local, stage: "local_storage_sidebar")
            _ = try remaining("before_local_storage_sidebar_tap")
            navigation.append("local_storage_sidebar")
            localControl.tap()
            _ = try remaining("after_local_storage_sidebar")
            let browser = app.otherElements.matching(NSPredicate(
                format: "identifier BEGINSWITH %@",
                "DOC.browsingRoot Source: com.apple.FileProvider.LocalStorage, Title: "))
            let root = try ready(browser, stage: "local_storage_browser", hittable: false)
            func folder(_ name: String) -> XCUIElementQuery {
                root.cells.matching(NSPredicate(format: "label == %@ OR label BEGINSWITH %@", name, name + ","))
            }
            let pinkha = try ready(folder("Pinkha"), stage: "pinkha_folder")
            guard pinkha.identifier == "Pinkha, Container" else {
                try fail("pinkha_container_identity_changed")
            }
            // The original failed Files AX contains this single Image inside
            // the exact Pinkha Container cell. Target the icon itself once;
            // the cell center lies in the separate name area in that evidence.
            let icons = pinkha.descendants(matching: .image)
            let icon = try ready(icons, stage: "pinkha_folder_icon")
            _ = try remaining("before_pinkha_icon_geometry")
            let cellFrame = pinkha.frame
            let iconFrame = icon.frame
            let geometry = [cellFrame.minX, cellFrame.minY, cellFrame.width, cellFrame.height,
                            iconFrame.minX, iconFrame.minY, iconFrame.width, iconFrame.height]
            guard geometry.allSatisfy(\.isFinite),
                  cellFrame.width > 0, cellFrame.height > 0,
                  iconFrame.width > 0, iconFrame.height > 0,
                  cellFrame.contains(iconFrame) else {
                try fail("pinkha_icon_not_finitely_contained")
            }
            pinkhaIconTarget = [
                "type": icon.elementType.rawValue,
                "cellFrame": [cellFrame.minX, cellFrame.minY, cellFrame.width, cellFrame.height],
                "iconFrame": [iconFrame.minX, iconFrame.minY, iconFrame.width, iconFrame.height],
                "initialUniqueImageDescendant": true, "initialFrameContainedInCell": true
            ]
            guard icons.count == 1, pinkha.exists, pinkha.isEnabled, pinkha.isHittable,
                  icon.exists, icon.isEnabled, icon.isHittable,
                  pinkha.frame == cellFrame, icon.frame == iconFrame else {
                try fail("pinkha_icon_changed_before_tap")
            }
            _ = try remaining("before_pinkha_folder_icon_tap")
            navigation.append("pinkha_folder_icon_center")
            // Tap the center of the freshly observed icon bounds. The remote
            // Files Image's synthesized accessibility hit point did not enter
            // this folder in either original failed run; keep one real tap and
            // require the same breadcrumb/Exports navigation before proceeding.
            icon.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
            _ = try remaining("after_pinkha_folder")
            _ = try ready(app.buttons.matching(NSPredicate(
                format: "label == %@ OR label BEGINSWITH %@", "Pinkha", "Pinkha,")),
                stage: "pinkha_breadcrumb")
            let exports = try ready(folder("Exports"), stage: "exports_folder")
            _ = try remaining("before_exports_folder_tap")
            navigation.append("exports_folder")
            exports.tap()
            _ = try remaining("after_exports_folder")
            _ = try ready(directory, stage: "exports_breadcrumb")
            observedExports = true
        }
        func exportUsingFiles(named filename: String) throws {
            XCTAssertTrue(filename.hasSuffix(".json"))
            let basename = String(filename.dropLast(".json".count))
            tapWhenEnabled(app.buttons["any-native-archive-export"])
            // The old picker observation accepted only modal coverage. This
            // journey requires real, enabled system controls before any action.
            let saveQuery = app.buttons.matching(NSPredicate(
                format: "label IN %@", ["Save", "שמירה", "שמור"]))
            _ = try uniqueReady(saveQuery, phase: basename + "_save", timeout: 45)
            try requireArchiveFilesDirectory(phase: basename + "_export")
            let filenameField = try uniqueReady(app.textFields, phase: basename + "_filename")
            guard let currentName = filenameField.value as? String,
                  ["source-associations", "source-associations.json", basename, filename].contains(currentName) else {
                try captureFilesState(basename + "_UNEXPECTED_FILENAME")
                throw FileJourneyError.unexpectedFileName
            }
            filenameField.tap()
            filenameField.typeKey("a", modifierFlags: .command)
            filenameField.typeText(basename)
            waitFor(NSPredicate(format: "value == %@ OR value == %@", basename, filename),
                    object: filenameField, timeout: 10)
            try captureFilesState(basename + "_save_READY")
            try uniqueReady(saveQuery, phase: basename + "_save_after_name").tap()
            let exported = app.descendants(matching: .any)
                .matching(identifier: "any-native-archive-exported-file").firstMatch
            waitFor(NSPredicate(format: "exists == true AND value == %@", filename),
                    object: exported, timeout: 45)
            // The destination comes from the real successful Files callback,
            // independently of the requested directory and visible picker title.
            let folder = app.descendants(matching: .any)
                .matching(identifier: "any-native-archive-exported-directory").firstMatch
            waitFor(NSPredicate(format: "exists == true AND value == %@", "Exports"),
                    object: folder, timeout: 45)
        }
        func importUsingFiles(named filename: String) throws {
            let basename = String(filename.dropLast(".json".count))
            tapWhenEnabled(app.buttons["any-native-archive-import"])
            let cancelQuery = app.buttons.matching(NSPredicate(
                format: "label IN %@", ["Cancel", "ביטול"]))
            _ = try uniqueReady(cancelQuery, phase: basename + "_import_dialog", timeout: 15)
            try captureFilesState(basename + "_import_PRESENTED")
            try requireArchiveFilesDirectory(phase: basename + "_import")
            // Query actual Files rows/text. All names contain this test's UUID;
            // there is no injected URL, fake picker, or filesystem selection.
            let exactName = NSPredicate(format: "label == %@ OR label == %@", filename, basename)
            let rowName = NSPredicate(format: "label == %@ OR label == %@ OR label BEGINSWITH %@",
                                      filename, basename, basename + ",")
            let textQuery = app.staticTexts.matching(exactName)
            let cellQuery = app.cells.matching(rowName)
            let buttonQuery = app.buttons.matching(rowName)
            let choices = [textQuery.firstMatch, cellQuery.firstMatch, buttonQuery.firstMatch]
            let expectation = XCTNSPredicateExpectation(
                predicate: NSPredicate(format:
                    "SUBQUERY(SELF, $entry, $entry.exists == true AND $entry.enabled == true AND $entry.hittable == true).@count > 0"),
                object: choices)
            guard XCTWaiter.wait(for: [expectation], timeout: 45) == .completed else {
                try captureFilesState(basename + "_import_NOT_READY")
                throw FileJourneyError.controlNotReady("import_file")
            }
            // Prefer the visible filename. A cell and its filename can both be
            // exposed by Files, so uniqueness is required within the chosen role.
            let queries = [textQuery, cellQuery, buttonQuery]
            guard let query = queries.first(where: {
                $0.count == 1 && $0.firstMatch.exists && $0.firstMatch.isEnabled && $0.firstMatch.isHittable
            }) else {
                try captureFilesState(basename + "_import_AMBIGUOUS")
                throw FileJourneyError.ambiguousControl("import_file")
            }
            try captureFilesState(basename + "_import_READY")
            query.firstMatch.tap()
        }

        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: sourceName)
        waitUntilEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        tapWhenEnabled(app.buttons["any-native-document-sources"])
        let search = app.searchFields.firstMatch
        waitUntilEnabled(search)
        search.tap(); search.typeText(reference)
        let sourceResult = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@",
            "any-native-source-result-", reference)).firstMatch
        tapWhenEnabled(sourceResult, timeout: 60)
        let segment = app.buttons["torah-reader-segment-" + reference]
        waitUntilEnabled(segment, timeout: 60)
        let providerText = segment.label
        XCTAssertFalse(providerText.isEmpty)
        XCTAssertNotEqual(providerText, reference)
        segment.press(forDuration: 1.1)
        tapWhenEnabled(app.buttons["torah-reader-insert-" + reference])

        let blocks = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        let badges = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-sources-"))
        collapseInspectorForBackgroundRead(app)
        waitFor(NSPredicate(format: "exists == true"), object: badges.firstMatch, timeout: 60)
        XCTAssertEqual(blocks.count, 1)
        XCTAssertEqual(badges.count, 1)
        let sourceAssociationCount = badges.count
        let sourceEditorID = blocks.firstMatch.identifier
        let sourceBlockID = String(sourceEditorID.dropFirst("any-native-block-".count))
        XCTAssertFalse(sourceBlockID.isEmpty)
        XCTAssertEqual(badges.firstMatch.identifier, "any-native-block-sources-" + sourceBlockID)
        let sourceBody = exactBody(app.textViews[sourceEditorID], providerText)
        let peek = app.descendants(matching: .any)
            .matching(identifier: "torah-inspector-sheet-peek").firstMatch
        if peek.exists {
            // Search and Close are independent controls in the shared inspector.
            // Use the actual visible Close action; the original sheet-absence
            // and archive/export/import/readback assertions remain unchanged.
            let close = app.buttons["torah-inspector-peek-close"]
            tapWhenEnabled(close)
            waitFor(NSPredicate(format: "exists == false"), object: peek, timeout: 15)
        }
        openCanonicalArchiveObservationEntry(app)
        try exportUsingFiles(named: sourceFile)
        tapWhenEnabled(app.buttons["any-native-archive-close"])
        returnToLibrary()

        createNamedItem(app, action: "any-native-new-document", title: destinationName)
        let add = app.buttons["any-native-add-paragraph"]
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: add, timeout: 60)
        add.tap()
        waitUntilEnabled(blocks.firstMatch)
        blocks.firstMatch.tap(); blocks.firstMatch.typeText(destinationBody)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        let save = app.descendants(matching: .any).matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"), object: save, timeout: 45)
        XCTAssertEqual(blocks.count, 1)
        XCTAssertEqual(badges.count, 0)
        let destinationEditorID = blocks.firstMatch.identifier
        let destinationBlockID = String(destinationEditorID.dropFirst("any-native-block-".count))
        XCTAssertFalse(destinationBlockID.isEmpty)
        XCTAssertNotEqual(destinationBlockID, sourceBlockID)
        let destinationBefore = exactBody(app.textViews[destinationEditorID], destinationBody)

        openCanonicalArchiveObservationEntry(app)
        try importUsingFiles(named: sourceFile)
        let chosenFile = app.descendants(matching: .any).matching(identifier: "any-native-archive-file").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", sourceFile),
                object: chosenFile, timeout: 45)
        let prepare = app.buttons["any-native-archive-prepare"]
        waitFor(NSPredicate(format: "exists == true AND enabled == false"), object: prepare, timeout: 20)
        let mappingWasRequired = prepare.exists && !prepare.isEnabled
        let mapping = app.descendants(matching: .any)
            .matching(identifier: "any-native-archive-block-map-" + sourceBlockID).firstMatch
        tapWhenEnabled(mapping)
        let destinationLabel = destinationBody + " · " + String(destinationBlockID.prefix(8))
        tapWhenEnabled(app.buttons[destinationLabel].firstMatch)
        tapWhenEnabled(prepare)
        tapWhenEnabled(app.buttons["any-native-archive-confirm"])
        let receipt = app.descendants(matching: .any)
            .matching(identifier: "any-native-archive-import-result").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "complete"),
                object: receipt, timeout: 60)
        tapWhenEnabled(app.buttons["any-native-archive-close"])
        let destinationAfter = exactBody(app.textViews[destinationEditorID], destinationBody)
        waitFor(NSPredicate(format: "exists == true"),
                object: app.buttons["any-native-block-sources-" + destinationBlockID], timeout: 45)
        XCTAssertEqual(badges.count, 1)

        // One real process restart. Neither document is rewritten or relinked.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[destinationName].firstMatch, timeout: 60)
        let destinationCold = exactBody(app.textViews[destinationEditorID], destinationBody)
        waitFor(NSPredicate(format: "exists == true"),
                object: app.buttons["any-native-block-sources-" + destinationBlockID], timeout: 45)
        XCTAssertEqual(blocks.count, 1)
        XCTAssertEqual(badges.count, 1)
        let destinationColdAssociationCount = badges.count
        openCanonicalArchiveObservationEntry(app)
        try exportUsingFiles(named: destinationFile)
        tapWhenEnabled(app.buttons["any-native-archive-close"])
        returnToLibrary()
        tapWhenEnabled(app.buttons[sourceName].firstMatch, timeout: 60)
        let sourceCold = exactBody(app.textViews[sourceEditorID], sourceBody)
        waitFor(NSPredicate(format: "exists == true"),
                object: app.buttons["any-native-block-sources-" + sourceBlockID], timeout: 45)
        XCTAssertEqual(blocks.count, 1)
        XCTAssertEqual(badges.count, 1)
        openCanonicalArchiveObservationEntry(app)
        try exportUsingFiles(named: sourceColdFile)
        tapWhenEnabled(app.buttons["any-native-archive-close"])

        let proof: [String: Any] = [
            "schemaVersion": 1,
            "method": "NativeLaunchTests/testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies",
            "scopeUUID": scope.uuidString, "coldReopenObserved": true,
            "sourceFileName": sourceFile, "destinationFileName": destinationFile,
            "sourceColdFileName": sourceColdFile,
            "sourceBlockID": sourceBlockID, "destinationBlockID": destinationBlockID,
            "canonicalReference": reference, "mappingRequiredBeforePrepare": mappingWasRequired,
            "sourceAssociationCount": sourceAssociationCount,
            "destinationColdAssociationCount": destinationColdAssociationCount,
            "sourceBodySHA256": hash(sourceBody), "sourceColdBodySHA256": hash(sourceCold),
            "sourceBodyUTF8Count": sourceBody.utf8.count,
            "destinationBeforeBodySHA256": hash(destinationBefore),
            "destinationAfterBodySHA256": hash(destinationAfter),
            "destinationColdBodySHA256": hash(destinationCold),
            "destinationBodyUTF8Count": destinationCold.utf8.count
        ]
        let attachment = XCTAttachment(data: try JSONSerialization.data(withJSONObject: proof, options: [.sortedKeys]),
                                       uniformTypeIdentifier: "public.json")
        attachment.name = "native-canonical-archive-roundtrip-receipt"
        attachment.lifetime = .keepAlways
        self.add(attachment)
    }
    // END_CANONICAL_ARCHIVE_ROUNDTRIP_V1

    // BEGIN_NATIVE_CUSTOM_TYPE_UI_V1
    func testCustomCanonicalTypeTransitionPreservesNativeDocumentAcrossColdReopen() throws {
        let scope = UUID(), contract = "pinkha-native-custom-type-ui-v1"
        let suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let createFlag = "--native-ui-custom-type-fixture-v1"
        let auditFlag = "--native-ui-custom-type-audit-v1"
        let spaceName = "Custom Type UI Space " + suffix
        let documentName = "Custom Type UI Document " + suffix
        let initialBody = "שלום סוג מסמך מותאם ABC 482 " + suffix
        let appendedText = " — נשמר בסוג החדש 739"
        let finalBody = initialBody + appendedText
        let propertyValue = "ערך משותף " + suffix + " 864"

        enum JourneyError: Error { case fixture, receipt, missingIdentity }
        func fixture(_ phase: String) throws -> [String: Any] {
            let row = app.descendants(matching: .any)
                .matching(identifier: "any-native-ui-custom-type-fixture").firstMatch
            waitFor(NSPredicate(format: "exists == true AND (value BEGINSWITH %@ OR value BEGINSWITH %@)",
                                "ready|", "failed|"), object: row, timeout: 120)
            guard let value = row.value as? String, value.hasPrefix("ready|"),
                  value.utf8.count <= 32_774,
                  let result = try JSONSerialization.jsonObject(with: Data(value.dropFirst(6).utf8)) as? [String: Any],
                  result["contract"] as? String == contract, result["phase"] as? String == phase,
                  let seed = result["seed"] as? [String: Any],
                  seed["scopeUUID"] as? String == scope.uuidString,
                  seed["eligible"] as? Bool == true,
                  seed["canonicalEditorDataset"] as? String == "editor_blocks",
                  seed["nativeWrites"] as? Int == 3,
                  seed["documentWrites"] as? Int == 0,
                  seed["bodyWrites"] as? Int == 0,
                  seed["membershipWrites"] as? Int == 0,
                  result["nativeWritesThisProcess"] as? Int == (phase == "prepare" ? 3 : 0) else {
                throw JourneyError.fixture
            }
            return result
        }
        func identity(_ seed: [String: Any], _ key: String) throws -> String {
            guard let value = seed[key] as? String, !value.isEmpty, value.utf8.count <= 1024,
                  !value.contains("\0") else { throw JourneyError.missingIdentity }
            return value
        }
        func bodyObservation(_ editor: XCUIElement, expected: String) throws -> [String: Any] {
            waitFor(NSPredicate(format: "exists == true AND value == %@", expected), object: editor, timeout: 60)
            guard let actual = editor.value as? String, Array(actual.utf8) == Array(expected.utf8),
                  editor.identifier.hasPrefix("any-native-block-"),
                  editor.identifier.count > "any-native-block-".count else { throw JourneyError.receipt }
            XCTAssertEqual(Array(actual.utf8), Array(expected.utf8))
            return ["nativeBlockID": String(editor.identifier.dropFirst("any-native-block-".count)),
                    "sha256": SHA256.hash(data: Data(actual.utf8)).map { String(format: "%02x", $0) }.joined(),
                    "utf8Count": actual.utf8.count]
        }
        func saved() {
            let row = app.descendants(matching: .any).matching(identifier: "any-native-save-status").firstMatch
            waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"), object: row, timeout: 45)
        }

        app.launchArguments.append(createFlag)
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        let prepared = try fixture("prepare")
        guard let seed = prepared["seed"] as? [String: Any] else { throw JourneyError.fixture }
        let typeID = try identity(seed, "typeID"), typeName = try identity(seed, "typeName")
        let propertyID = try identity(seed, "propertyID"), pageName = try identity(seed, "pageTypeName")
        XCTAssertNotEqual(typeID, "page")
        XCTAssertNotEqual(typeName, pageName)
        let propertyIdentifier = "any-native-property-property:v1:\(typeID.utf8.count):\(typeID):\(propertyID.utf8.count):\(propertyID)"

        // Only the normal UI creates the Page/document/body and changes its Type.
        createNamedItem(app, action: "any-native-new-document", title: documentName)
        tapWhenEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        let blocks = app.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-"))
        waitForNativeEditorInput(app, blocks.firstMatch)
        blocks.firstMatch.tap(); blocks.firstMatch.typeText(initialBody)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        saved()
        XCTAssertEqual(blocks.count, 1)
        let beforeType = try bodyObservation(blocks.firstMatch, expected: initialBody)
        let blockID = try identity(beforeType, "nativeBlockID")

        tapWhenEnabled(app.buttons["any-native-document-properties"])
        let type = app.descendants(matching: .any).matching(identifier: "any-native-property-type").firstMatch
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND value == %@", pageName),
                object: type, timeout: 60)
        type.tap()
        tapWhenEnabled(app.buttons[typeName].firstMatch)
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND value == %@", typeName),
                object: type, timeout: 45)
        let property = app.buttons[propertyIdentifier]
        revealNativeProperty(app, property)
        tapWhenEnabled(property)
        let field = app.descendants(matching: .any).matching(identifier: "any-native-property-value-input").firstMatch
        waitUntilEnabled(field)
        field.tap(); field.typeText(propertyValue)
        tapWhenEnabled(app.buttons["any-native-property-save"])
        revealNativeProperty(app, property)
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND value == %@", propertyValue),
                object: property, timeout: 45)
        revealNativeProperty(app, type, scrollDown: true)
        XCTAssertEqual(type.value as? String, typeName)
        tapWhenEnabled(app.buttons["any-native-property-close"])
        let afterType = try bodyObservation(blocks.firstMatch, expected: initialBody)
        XCTAssertEqual(afterType["nativeBlockID"] as? String, blockID)
        XCTAssertEqual(blocks.count, 1)

        // Command-Down uses the editor's actual text input to append at the end.
        let editor = app.textViews["any-native-block-" + blockID]
        waitForNativeEditorInput(app, editor)
        editor.tap()
        editor.typeKey(XCUIKeyboardKey.downArrow, modifierFlags: .command)
        editor.typeText(appendedText)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        saved()
        let afterEdit = try bodyObservation(editor, expected: finalBody)
        XCTAssertEqual(blocks.count, 1)

        let back = app.navigationBars.buttons.matching(
            NSPredicate(format: "label == %@ OR label == %@", "ספרייה", "Library")).firstMatch
        tapWhenEnabled(back)
        let document = app.buttons[documentName].firstMatch
        waitUntilEnabled(document, timeout: 60)
        let rowIdentifier = document.identifier
        guard rowIdentifier.hasPrefix("any-native-hierarchy-row-"),
              rowIdentifier.count > "any-native-hierarchy-row-".count else { throw JourneyError.missingIdentity }
        let objectID = String(rowIdentifier.dropFirst("any-native-hierarchy-row-".count))

        // Fresh iOS process; the prepare flag is removed. The audit path only GETs
        // the original three definitions and requires zero native fixture writes.
        app.terminate()
        app.launchArguments.removeAll { $0 == createFlag }
        app.launchArguments.append(auditFlag)
        XCTAssertFalse(app.launchArguments.contains(createFlag))
        app.launch()
        tapWhenEnabled(app.buttons["any-native-saved-account"].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons[spaceName].firstMatch, timeout: 60)
        let reopened = try fixture("audit")
        guard let coldSeed = reopened["seed"] as? [String: Any],
              NSDictionary(dictionary: seed).isEqual(to: coldSeed),
              prepared["processID"] as? Int != reopened["processID"] as? Int,
              prepared["ownerGeneration"] as? String != reopened["ownerGeneration"] as? String else {
            throw JourneyError.receipt
        }
        let coldDocument = app.buttons[rowIdentifier]
        waitUntilEnabled(coldDocument, timeout: 60)
        XCTAssertEqual(coldDocument.label, documentName)
        coldDocument.tap()
        let afterCold = try bodyObservation(editor, expected: finalBody)
        XCTAssertEqual(afterCold["nativeBlockID"] as? String, blockID)
        XCTAssertEqual(blocks.count, 1)
        tapWhenEnabled(app.buttons["any-native-document-properties"])
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND value == %@", typeName),
                object: type, timeout: 60)
        let coldTypeName = type.value as? String ?? ""
        revealNativeProperty(app, property)
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND value == %@", propertyValue),
                object: property, timeout: 45)

        let receipt: [String: Any] = [
            "schemaVersion": 1, "contract": "pinkha-native-custom-type-ui-journey-v1",
            "method": "NativeLaunchTests/testCustomCanonicalTypeTransitionPreservesNativeDocumentAcrossColdReopen",
            "scopeUUID": scope.uuidString, "documentName": documentName, "objectID": objectID,
            "initialTypeID": "page", "initialTypeName": pageName,
            "selectedTypeID": typeID, "selectedTypeName": typeName,
            "coldTypeName": coldTypeName,
            "propertyID": propertyID, "propertyValue": propertyValue,
            "coldPropertyValue": property.value as? String ?? "",
            "beforeType": beforeType, "afterType": afterType, "afterEdit": afterEdit, "afterCold": afterCold,
            "prepare": prepared, "audit": reopened, "coldProcessReopen": true,
            "creationFlagRemoved": !app.launchArguments.contains(createFlag),
            "auditFlagPresent": app.launchArguments.filter { $0 == auditFlag }.count == 1,
            "blockCountBefore": 1, "blockCountAfter": blocks.count
        ]
        let attachment = XCTAttachment(data: try JSONSerialization.data(withJSONObject: receipt, options: [.sortedKeys]),
                                       uniformTypeIdentifier: "public.json")
        attachment.name = "native-custom-type-transition-receipt"
        attachment.lifetime = .keepAlways
        self.add(attachment)
    }
    // END_NATIVE_CUSTOM_TYPE_UI_V1

    func testNativeBinRestoreKeepsIdentityAndBodyAcrossColdReopen() throws {
        let scope = UUID(), suffix = String(UUID().uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Bin UI Space " + suffix
        let title = "מסמך לשחזור " + suffix
        let body = "Restore preserves mixed English ועברית 864"
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        try createNamedItemWithObservedTransition(app, action: "any-native-new-document", title: title)
        tapWhenEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        let blocks = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        waitUntilEnabled(blocks.firstMatch)
        blocks.firstMatch.tap(); blocks.firstMatch.typeText(body)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        let status = app.descendants(matching: .any).matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"), object: status, timeout: 45)
        let blockID = blocks.firstMatch.identifier
        reopenOwnedWorkspace(app, spaceName: spaceName)
        let row = app.buttons[title].firstMatch
        // The cold-open navigation must expose the actual Library before this
        // actions menu. An enabled row in a retained navigation view is not
        // evidence that the visible row can receive this real menu tap.
        let libraryToolbar = app.buttons["any-native-create-menu"]
        var binRowFrame: CGRect?
        var binRowReadySince: TimeInterval?
        let binRowReady = NSPredicate { _, _ in
            guard app.buttons.matching(NSPredicate(format: "label == %@", title)).count == 1,
                  row.exists, row.isEnabled, row.isHittable,
                  libraryToolbar.exists, libraryToolbar.isEnabled, libraryToolbar.isHittable,
                  let snapshot = try? row.snapshot() else {
                binRowFrame = nil; binRowReadySince = nil
                return false
            }
            let frame = snapshot.frame
            guard !frame.isNull, !frame.isInfinite, frame.width > 0, frame.height > 0 else {
                binRowFrame = nil; binRowReadySince = nil
                return false
            }
            let now = ProcessInfo.processInfo.systemUptime
            if binRowFrame == frame, let binRowReadySince, now - binRowReadySince >= 0.15 {
                return true
            }
            if binRowFrame != frame || binRowReadySince == nil {
                binRowFrame = frame; binRowReadySince = now
            }
            return false
        }
        guard XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: binRowReady, object: app)],
                            timeout: 60) == .completed else {
            recordNativeCreateTransition(app, phase: "bin_library_row_not_hittable")
            XCTFail("The original Bin row and Library toolbar must be stably hittable before opening its actions menu")
            return
        }
        recordNativeCreateTransition(app, phase: "bin_library_row_hittable")
        let rowID = row.identifier
        XCTAssertTrue(rowID.hasPrefix("any-native-hierarchy-row-"))
        let objectID = String(rowID.dropFirst("any-native-hierarchy-row-".count))
        let actions = app.buttons["any-native-hierarchy-actions-" + objectID]
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: actions, timeout: 30)
        actions.tap()
        tapWhenEnabled(app.buttons["any-native-hierarchy-archive"])
        confirmNativeBinRemoval(app)
        waitFor(NSPredicate(format: "exists == false"), object: app.buttons[rowID], timeout: 45)

        reopenOwnedWorkspace(app, spaceName: spaceName)
        XCTAssertFalse(app.buttons[rowID].exists)
        tapWhenEnabled(app.buttons["any-native-open-bin"])
        let archived = app.descendants(matching: .any).matching(identifier: "any-native-bin-item-" + objectID)
        waitUntilEnabled(archived.firstMatch, timeout: 45)
        XCTAssertEqual(archived.count, 1)
        XCTAssertTrue(archived.firstMatch.staticTexts[title].exists)
        tapWhenEnabled(app.buttons["any-native-bin-restore-" + objectID])
        waitFor(NSPredicate(format: "exists == false"), object: archived.firstMatch, timeout: 45)
        waitUntilEnabled(app.staticTexts["any-native-bin-empty"])

        reopenOwnedWorkspace(app, spaceName: spaceName)
        let restored = app.buttons.matching(identifier: rowID)
        waitUntilEnabled(restored.firstMatch, timeout: 60)
        XCTAssertEqual(restored.count, 1)
        XCTAssertEqual(restored.firstMatch.label, title)
        tapWhenEnabled(restored.firstMatch)
        waitFor(NSPredicate(format: "exists == true AND value == %@", body),
                object: app.textViews[blockID], timeout: 60)
        XCTAssertEqual(blocks.count, 1)
    }

    // BEGIN_NATIVE_BIN_CONFIRMATION_AX_PREPARATION_V1
    /// UIKit exposes the actual confirmation action as nested Buttons.
    /// Choose its unique leaf only inside the exact rendered confirmation Sheet.
    private func confirmNativeBinRemoval(_ app: XCUIApplication,
                                         file: StaticString = #filePath, line: UInt = #line) {
        let labels = ["העברה לסל המחזור", "Move to Bin"]
        let sheets = app.sheets.matching(NSPredicate(format: "label IN %@", labels))
        let menuAction = app.buttons["any-native-hierarchy-archive"]
        func usableFrame(_ frame: CGRect) -> Bool {
            frame.minX.isFinite && frame.minY.isFinite && frame.width.isFinite && frame.height.isFinite
                && frame.width > 0 && frame.height > 0
        }
        func confirmation() -> (sheetCount: Int, titleCount: Int, actionCount: Int,
                                leafActions: [XCUIElement], label: String) {
            let count = sheets.count
            guard count == 1 else { return (count, 0, 0, [], "") }
            let sheet = sheets.element(boundBy: 0)
            let label = sheet.label
            let titles = sheet.staticTexts.matching(NSPredicate(format: "label == %@", label))
            let actions = sheet.buttons.matching(NSPredicate(
                format: "identifier == %@ AND label == %@", "any-native-bin-confirm-remove", label))
            let leaves = actions.allElementsBoundByIndex.filter {
                $0.descendants(matching: .button).count == 0
            }
            return (count, titles.count, actions.count, leaves, label)
        }
        let ready = NSPredicate { _, _ in
            let current = confirmation()
            guard !menuAction.exists, current.sheetCount == 1, current.titleCount == 1,
                  current.leafActions.count == 1 else { return false }
            let action = current.leafActions[0]
            let frame = action.frame
            return action.isEnabled && action.isHittable && usableFrame(frame)
        }
        let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: ready, object: app)],
                                   timeout: 30)
        let ax = XCTAttachment(string: String(decoding: Data(app.debugDescription.utf8).prefix(131_072),
                                              as: UTF8.self))
        ax.name = "NATIVE_BIN_CONFIRMATION_private_AX"; ax.lifetime = .keepAlways; add(ax)
        let screen = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        screen.name = "NATIVE_BIN_CONFIRMATION_private_screen"; screen.lifetime = .keepAlways; add(screen)
        let current = confirmation()
        let action = current.leafActions.count == 1 ? current.leafActions[0] : nil
        let observed: [String: Any] = [
            "sheetCount": current.sheetCount, "sheetLabel": current.label,
            "titleCount": current.titleCount, "actionCount": current.actionCount,
            "leafActionCount": current.leafActions.count,
            "initiatingMenuActionPresent": menuAction.exists,
            "waitCompleted": result == .completed,
            "actionLabel": action?.label ?? "",
            "actionIdentifier": action?.identifier ?? "",
            "actionEnabled": action?.isEnabled ?? false,
            "actionHittable": action?.isHittable ?? false,
            "actionFrame": action.map { String(describing: $0.frame) } ?? ""
        ]
        if let data = try? JSONSerialization.data(withJSONObject: observed, options: [.sortedKeys]),
           let text = String(data: data, encoding: .utf8) {
            let control = XCTAttachment(string: text)
            control.name = "NATIVE_BIN_CONFIRMATION_control"; control.lifetime = .keepAlways; add(control)
        }
        XCTAssertEqual(result, .completed, "The unique native Bin confirmation was not ready.",
                       file: file, line: line)
        guard result == .completed else { return }
        let final = confirmation()
        guard !menuAction.exists, final.sheetCount == 1, final.titleCount == 1,
              final.leafActions.count == 1 else {
            XCTFail("The native Bin confirmation changed before the real tap.", file: file, line: line)
            return
        }
        let finalAction = final.leafActions[0]
        let frame = finalAction.frame
        guard finalAction.identifier == "any-native-bin-confirm-remove",
              finalAction.label == final.label, finalAction.isEnabled,
              finalAction.isHittable, usableFrame(frame) else {
            XCTFail("The native Bin confirmation action lost its actual hit frame.", file: file, line: line)
            return
        }
        finalAction.tap()
    }
    // END_NATIVE_BIN_CONFIRMATION_AX_PREPARATION_V1

    // BEGIN_NATIVE_LIBRARY_SEARCH_UI_V1
    func testLibrarySearchReplacementAndColdReopenUseCurrentQuery() throws {
        executionTimeAllowance = 900
        let scope = UUID()
        let suffix = scope.uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        let app = makeApplication(scope: scope)
        let spaceName = "Library search UI " + String(suffix.prefix(8))
        let alpha = (key: "alpha", query: "libraryalpha" + suffix,
                     title: "Library Alpha " + suffix,
                     body: "מסמך ראשון לחיפוש libraryalpha" + suffix)
        let beta = (key: "beta", query: "librarybeta" + suffix,
                    title: "Library Beta " + suffix,
                    body: "מסמך שני לחיפוש librarybeta" + suffix)
        let absentQuery = "libraryabsent" + suffix
        let library = app.descendants(matching: .any).matching(identifier: "any-native-library").firstMatch
        let blocks = app.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-"))
        var identities: [String: [String: String]] = [:]
        var queryExpected = ""
        var phase = "setup"
        var completedColdReopens = 0
        var complete = false

        func hash(_ text: String) -> String {
            SHA256.hash(data: Data(text.utf8)).map { String(format: "%02x", $0) }.joined()
        }
        func rows(_ title: String) -> XCUIElementQuery {
            // Search rows include the original title plus a native FTS snippet.
            // Scope the visible title query to the actual Library list.
            library.descendants(matching: .button).matching(NSPredicate(format: "label BEGINSWITH %@", title))
        }
        func capture(_ name: String) throws {
            try requireArchiveObservationPastOnboarding(app)
            let field = app.searchFields.firstMatch
            var record: [String: Any] = [
                "schema": "any-native-library-search-ui/v1", "phase": name,
                "ownedScope": scope.uuidString, "spaceName": spaceName,
                "requestedAppLanguage": "he", "queryExpected": queryExpected,
                "queryFieldExists": field.exists, "completedColdReopens": completedColdReopens,
                "nativeIdentityOrigin": "actual-mounted-hierarchy-and-editor-accessibility",
                "nativeReadExtraCallsByObserver": 0, "testStorageOverrides": false,
                "identities": identities
            ]
            if field.exists { record["queryObserved"] = field.value as? String ?? "" }
            else { record["queryObserved"] = NSNull() }
            if library.exists {
                record["visibleFixtureRows"] = [alpha.title, beta.title].flatMap { title in
                    rows(title).allElementsBoundByIndex.map { row in
                        ["label": row.label, "identifier": row.identifier, "hittable": row.isHittable] as [String: Any]
                    }
                }
            }
            record["visibleNativeBlocks"] = blocks.allElementsBoundByIndex.map { block in
                ["identifier": block.identifier, "bodySHA256": hash(block.value as? String ?? "")] as [String: Any]
            }
            let data = try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys])
            XCTAssertLessThanOrEqual(data.count, 65_536)
            let metadata = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
            metadata.name = "native-library-search-" + name
            metadata.lifetime = .keepAlways; add(metadata)
            let tree = String(decoding: Data(app.debugDescription.utf8).prefix(131_072), as: UTF8.self)
            try requireArchiveObservationPastOnboarding(app)
            let ax = XCTAttachment(string: tree)
            ax.name = "native-library-search-" + name + "-private-ax"
            ax.lifetime = .keepAlways; add(ax)
            let image = XCTAttachment(screenshot: app.screenshot())
            image.name = "native-library-search-" + name
            image.lifetime = .keepAlways; add(image)
        }
        func returnToLibrary() {
            let back = app.navigationBars.buttons.matching(NSPredicate(
                format: "label == %@ OR label == %@", "ספרייה", "Library")).firstMatch
            tapWhenEnabled(back)
            waitUntilEnabled(app.buttons["any-native-create-menu"], timeout: 60)
            waitFor(NSPredicate(format: "exists == true"), object: library, timeout: 30)
        }
        func createDocument(_ item: (key: String, query: String, title: String, body: String)) throws {
            try createNamedItemWithObservedTransition(app, action: "any-native-new-document", title: item.title)
            let addParagraph = app.buttons["any-native-add-paragraph"]
            waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                    object: addParagraph, timeout: 60)
            addParagraph.tap()
            let editor = blocks.firstMatch
            waitForNativeEditorInput(app, editor)
            editor.tap(); editor.typeText(item.body)
            tapWhenEnabled(app.buttons["any-native-editor-done"])
            let status = app.descendants(matching: .any).matching(identifier: "any-native-save-status").firstMatch
            waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"), object: status, timeout: 45)
            XCTAssertEqual(editor.value as? String, item.body)
            XCTAssertEqual(blocks.count, 1)
            let blockIdentifier = editor.identifier
            XCTAssertTrue(blockIdentifier.hasPrefix("any-native-block-"))
            returnToLibrary()
            let row = app.buttons.matching(NSPredicate(
                format: "identifier BEGINSWITH %@ AND label == %@", "any-native-hierarchy-row-", item.title))
            waitUntilEnabled(row.firstMatch, timeout: 45)
            XCTAssertEqual(row.count, 1)
            let hierarchyIdentifier = row.firstMatch.identifier
            XCTAssertGreaterThan(hierarchyIdentifier.count, "any-native-hierarchy-row-".count)
            identities[item.key] = ["title": item.title, "query": item.query,
                "hierarchyRowIdentifier": hierarchyIdentifier,
                "objectIDFromHierarchy": String(hierarchyIdentifier.dropFirst("any-native-hierarchy-row-".count)),
                "blockIdentifier": blockIdentifier, "bodySHA256": hash(item.body)]
        }
        func replaceQuery(_ value: String) {
            queryExpected = value
            waitFor(NSPredicate(format: "exists == true"), object: library, timeout: 30)
            let field = app.searchFields.firstMatch
            if !field.exists || !field.isHittable { library.swipeDown() }
            waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                    object: field, timeout: 30)
            field.tap()
            field.typeKey("a", modifierFlags: .command)
            field.typeText(XCUIKeyboardKey.delete.rawValue)
            if !value.isEmpty {
                field.typeText(value)
                waitFor(NSPredicate(format: "value == %@", value), object: field, timeout: 30)
            }
        }
        func expectResult(_ item: (key: String, query: String, title: String, body: String),
                          excluding other: (key: String, query: String, title: String, body: String)) throws -> XCUIElement {
            let matching = rows(item.title)
            waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                    object: matching.firstMatch, timeout: 60)
            XCTAssertEqual(matching.count, 1)
            XCTAssertEqual(app.searchFields.firstMatch.value as? String, item.query)
            XCTAssertEqual(app.alerts.count, 0, "The current Library query must not be covered by an error alert.")
            XCTAssertFalse(rows(other.title).firstMatch.exists, "The previous or unrelated query must not supply displayed rows.")
            let identity = try XCTUnwrap(identities[item.key])
            let hierarchyIdentifier = try XCTUnwrap(identity["hierarchyRowIdentifier"])
            XCTAssertFalse(app.buttons[hierarchyIdentifier].exists,
                           "The actual search result must replace the ordinary hierarchy section.")
            return matching.firstMatch
        }
        func verifyOpened(_ item: (key: String, query: String, title: String, body: String)) throws {
            let identity = try XCTUnwrap(identities[item.key])
            let blockIdentifier = try XCTUnwrap(identity["blockIdentifier"])
            let expectedBodySHA256 = try XCTUnwrap(identity["bodySHA256"])
            let editor = app.textViews[blockIdentifier]
            waitFor(NSPredicate(format: "exists == true AND value == %@", item.body), object: editor, timeout: 60)
            XCTAssertEqual(blocks.count, 1)
            XCTAssertEqual(hash(editor.value as? String ?? ""), expectedBodySHA256)
            let title = app.navigationBars.staticTexts.matching(NSPredicate(format: "label == %@", item.title)).firstMatch
            waitFor(NSPredicate(format: "exists == true"), object: title, timeout: 30)
            let status = app.descendants(matching: .any).matching(identifier: "any-native-save-status").firstMatch
            waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"), object: status, timeout: 45)
        }
        func expectClearedHierarchy() throws {
            for item in [alpha, beta] {
                let identity = try XCTUnwrap(identities[item.key])
                let identifier = try XCTUnwrap(identity["hierarchyRowIdentifier"])
                waitUntilEnabled(app.buttons[identifier], timeout: 45)
            }
            XCTAssertFalse(app.staticTexts["תוצאות חיפוש"].exists)
            XCTAssertFalse(app.staticTexts["לא נמצאו תוצאות"].exists)
        }

        app.launch()
        defer { app.terminate() }
        defer {
            if !complete {
                do { try capture("FAILED_" + phase) }
                catch {
                    let refusal = XCTAttachment(string: "Post-onboarding diagnostic unavailable: " + String(describing: error))
                    refusal.name = "native-library-search-diagnostic-unavailable"
                    refusal.lifetime = .keepAlways; add(refusal)
                }
            }
        }
        createOwnedWorkspace(app, spaceName: spaceName)
        try createDocument(alpha)
        try createDocument(beta)

        phase = "alpha-result"
        replaceQuery(alpha.query)
        _ = try expectResult(alpha, excluding: beta)
        try capture(phase)

        phase = "replacement-beta-result"
        replaceQuery(beta.query)
        _ = try expectResult(beta, excluding: alpha)
        try capture(phase)

        phase = "no-match"
        replaceQuery(absentQuery)
        waitFor(NSPredicate(format: "exists == true AND hittable == true"),
                object: app.staticTexts["לא נמצאו תוצאות"], timeout: 60)
        XCTAssertEqual(app.alerts.count, 0, "A failed search must not be accepted as the empty-result UI.")
        XCTAssertFalse(rows(alpha.title).firstMatch.exists)
        XCTAssertFalse(rows(beta.title).firstMatch.exists)
        try capture(phase)

        phase = "cleared-hierarchy"
        replaceQuery("")
        try expectClearedHierarchy()
        try capture(phase)

        phase = "opened-alpha"
        replaceQuery(alpha.query)
        try expectResult(alpha, excluding: beta).tap()
        try verifyOpened(alpha)
        try capture(phase)
        returnToLibrary()
        replaceQuery("")
        try expectClearedHierarchy()

        phase = "cold-beta-result"
        reopenOwnedWorkspace(app, spaceName: spaceName)
        completedColdReopens += 1
        try expectClearedHierarchy()
        replaceQuery(beta.query)
        _ = try expectResult(beta, excluding: alpha)
        try capture(phase)

        phase = "cold-opened-beta"
        try expectResult(beta, excluding: alpha).tap()
        try verifyOpened(beta)
        try capture(phase)
        complete = true
    }
    // END_NATIVE_LIBRARY_SEARCH_UI_V1

    private func makeApplication(scope: UUID = UUID()) -> XCUIApplication {
        let app = NativeApplicationUnderTest()
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


/// The existing native flows may run against the standalone acceptance app or
/// the original combined app. The latter uses its real, visible engine selector.
@MainActor
final class NativeApplicationUnderTest: XCUIApplication {
    override func launch() {
        super.launch()
        guard ProcessInfo.processInfo.environment["PINKHA_NATIVE_UI_UNIFIED_HOST"] == "1" else { return }
        let selector = buttons["pinkha.engine.selector"]
        guard selector.waitForExistence(timeout: 60) else {
            XCTFail("The real combined-host engine selector did not appear.")
            return
        }
        guard acknowledgeEmptyHeartDebugDisclosureIfPresent(selector) else { return }
        if selector.value as? String != "Any" {
            let ready = XCTNSPredicateExpectation(
                predicate: NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: selector)
            guard XCTWaiter.wait(for: [ready], timeout: 60) == .completed else {
                XCTFail("The real combined-host engine selector is not ready.")
                return
            }
            selector.tap()
            let chooseAny = buttons["pinkha.engine.select.any"]
            guard chooseAny.waitForExistence(timeout: 15), chooseAny.isHittable else {
                XCTFail("The actual Any engine menu item is unavailable.")
                return
            }
            chooseAny.tap()
        }
        let selected = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == true AND value == %@", "Any"),
            object: selector)
        XCTAssertEqual(XCTWaiter.wait(for: [selected], timeout: 60), .completed,
                       "The original host did not complete the actual Any engine transition.")
    }

    /// The original Debug Heart startup disclosure is real UI. A fresh isolated
    /// native journey has no Heart vault, so only its one-button empty-account
    /// shape is admitted; a loaded-account or unrelated alert must fail closed.
    private func acknowledgeEmptyHeartDebugDisclosureIfPresent(_ selector: XCUIElement) -> Bool {
        let alert = alerts.firstMatch
        if !selector.isHittable && !alert.exists {
            _ = alert.waitForExistence(timeout: 15)
        }
        guard alert.exists else { return true }
        let messages = [
            "You launch app with a unstable middleware. Don't use your production vault. Your vault may be broken.",
            "הפעלת את האפליקציה עם תווכה (middleware) לא יציבה. אל תשתמש בכספת הייצור שלך. הכספת עלולה להיפגם."
        ]
        let labels = [
            "I won't be using my production vault",
            "לא אשתמש בכספת הייצור שלי"
        ]
        let text = alert.staticTexts.matching(NSPredicate(format: "label IN %@", messages))
        let proceed = alert.buttons.matching(NSPredicate(format: "label IN %@", labels))
        guard alerts.count == 1, text.count == 1, alert.buttons.count == 1,
              proceed.count == 1, proceed.firstMatch.isEnabled, proceed.firstMatch.isHittable else {
            XCTFail("An unexpected alert blocked the isolated native journey; no account action was approved.")
            return false
        }
        XCTContext.runActivity(named: "Acknowledge original empty Heart Debug disclosure") { activity in
            let original = XCTAttachment(screenshot: screenshot())
            original.name = "unified-native-original-empty-heart-disclosure"
            original.lifetime = .keepAlways
            activity.add(original)
        }
        proceed.firstMatch.tap()
        guard alert.waitForNonExistence(timeout: 15) else {
            XCTFail("The original empty Heart Debug disclosure did not close after its actual button was tapped.")
            return false
        }
        return true
    }
}

// Test-runner-only fixture protocol. These types never enter the app target.
private enum HanlinMountedFixtureError: Error {
    case missingConfiguration, invalidConfiguration, invalidResponse
    case wrongFixtureContract, fixtureFailed(String), phaseDeadline(Int), unexpectedPhase(Int)
    case unavailableBlockMenu, invalidCreatePrompt, unavailableReceipt, incompleteProof
}

private struct HanlinMountedFixtureScenario: Encodable, Sendable {
    let selectedBlockID: String
    let selectedText: String
    let unselectedText: String
    let documentTitle: String
    let cancelledTitle: String
    let approvedTitle: String
    let objectReference: String
}

private struct HanlinMountedFixtureReady: Decodable, Sendable {
    let schema: Int
    let contract: String
    let ready: Bool
}

private struct HanlinMountedFixtureStatus: Codable, Sendable {
    let schema: Int
    let contract: String
    let runID: String
    let scope: String
    let state: String
    let complete: Bool
    let phase: Int
    let providerRequests: Int
    let responsesDelivered: Int
    let stopped: Bool
    let scenarioSHA256: String?
    let observedScopeSHA256: String?
    let observedObjectSHA256: String?
    let observedSpaceSHA256: String?
    let observedRevisionSHA256: String?
    let registeredObjectCompared: Bool
    let registeredSpaceCompared: Bool
    let checks: [String: Bool]
    let failureCode: String?
    let rejections: [String: Int]
    let requestMetadata: [RequestMetadata]

    struct RequestMetadata: Codable, Sendable {
        let round: Int
        let bytes: Int
        let sha256: String
        let messageCount: Int
        let toolCallCount: Int
        let toolResultCount: Int
    }

    static let checkNames: Set<String> = [
        "scenario_registered_once", "denied_read_catalog_omits_read_tool",
        "denied_read_has_no_source_text", "allowed_read_exact_schema",
        "read_original_call_identity", "selected_payload_exact_block_and_text",
        "selected_payload_scope_shape_valid", "unselected_text_never_disclosed",
        "cancel_creation_exact_title_call", "cancel_creation_refused",
        "allowed_creation_new_exact_call", "allowed_creation_empty_success",
        "six_provider_requests_completed"
    ]

    func validate(expectedRunID: String? = nil) throws {
        guard expectedRunID.map({ $0 == runID }) ?? true,
              schema == 1, contract == "pinkha-mounted-hanlin-provider-fixture-v1",
              scope == "test_provider_protocol_only_not_Apple_or_native_acceptance",
              UUID(uuidString: runID) != nil, (0...6).contains(phase),
              (0...6).contains(providerRequests), (0...6).contains(responsesDelivered),
              responsesDelivered <= phase, phase - responsesDelivered <= 1,
              Set(checks.keys) == Self.checkNames, !stopped else {
            throw HanlinMountedFixtureError.wrongFixtureContract
        }
        if let failureCode { throw HanlinMountedFixtureError.fixtureFailed(failureCode) }
        guard state != "failed" else { throw HanlinMountedFixtureError.incompleteProof }
    }

    func requireComplete() throws {
        try validate()
        guard complete, state == "complete", phase == 6,
              providerRequests == 6, responsesDelivered == 6, requestMetadata.count == 6,
              checks.values.allSatisfy({ $0 }), registeredObjectCompared,
              rejections.values.allSatisfy({ $0 == 0 }),
              [scenarioSHA256, observedScopeSHA256, observedObjectSHA256,
               observedSpaceSHA256, observedRevisionSHA256].allSatisfy({
                  guard let value = $0 else { return false }
                  return value.count == 64 && value.utf8.allSatisfy {
                      (48...57).contains($0) || (97...102).contains($0)
                  }
              }) else { throw HanlinMountedFixtureError.incompleteProof }
    }
}

@MainActor
private final class HanlinMountedFixtureClient {
    let providerURL: URL
    let model: String
    let providerKey: String
    private let controlURL: URL
    private let controlToken: String
    private let session: URLSession
    private var registeredRunID: String?

    init(environment: [String: String]) throws {
        let prefix = "PINKHA_HANLIN_FIXTURE"
        guard let rawProvider = environment[prefix + "_URL"],
              let model = environment[prefix + "_MODEL"], !model.isEmpty,
              let key = environment[prefix + "_KEY"], !key.isEmpty,
              let rawControl = environment[prefix + "_CONTROL_URL"],
              let token = environment[prefix + "_CONTROL_TOKEN"], !token.isEmpty else {
            throw HanlinMountedFixtureError.missingConfiguration
        }
        guard let provider = URLComponents(string: rawProvider),
              let control = URLComponents(string: rawControl),
              provider.scheme == "https", control.scheme == "https",
              provider.host == "127.0.0.1", control.host == provider.host,
              provider.port != nil, control.port == provider.port,
              provider.path == "/v1", control.path == "/__fixture",
              provider.user == nil, provider.password == nil, provider.query == nil, provider.fragment == nil,
              control.user == nil, control.password == nil, control.query == nil, control.fragment == nil,
              let providerURL = provider.url, let controlURL = control.url else {
            throw HanlinMountedFixtureError.invalidConfiguration
        }
        self.providerURL = providerURL; self.controlURL = controlURL
        self.model = model; self.providerKey = key; self.controlToken = token
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 10
        configuration.timeoutIntervalForResource = 15
        configuration.httpShouldSetCookies = false
        // Default system certificate validation: no delegate, trust override,
        // URLProtocol replacement, proxy, or app-environment configuration.
        self.session = URLSession(configuration: configuration)
    }

    func close() { session.invalidateAndCancel() }

    func requireReady() async throws {
        let value: HanlinMountedFixtureReady = try await request(
            "ready", method: "GET", body: nil, authenticated: false, status: 200)
        guard value.schema == 1, value.contract == "pinkha-mounted-hanlin-provider-fixture-v1",
              value.ready else { throw HanlinMountedFixtureError.wrongFixtureContract }
    }

    func register(_ scenario: HanlinMountedFixtureScenario) async throws {
        guard registeredRunID == nil else { throw HanlinMountedFixtureError.wrongFixtureContract }
        let value: HanlinMountedFixtureStatus = try await request("scenario", method: "POST",
            body: try JSONEncoder().encode(scenario), authenticated: true, status: 201)
        try value.validate()
        guard value.phase == 0, value.providerRequests == 0, value.responsesDelivered == 0,
              !value.complete, value.state == "running",
              value.checks["scenario_registered_once"] == true else {
            throw HanlinMountedFixtureError.incompleteProof
        }
        registeredRunID = value.runID
    }

    func waitForPhase(_ phase: Int, timeout: TimeInterval = 45) async throws -> HanlinMountedFixtureStatus {
        guard let expectedRunID = registeredRunID else {
            throw HanlinMountedFixtureError.wrongFixtureContract
        }
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            try Task.checkCancellation()
            let value: HanlinMountedFixtureStatus = try await request(
                "status", method: "GET", body: nil, authenticated: true, status: 200)
            try value.validate(expectedRunID: expectedRunID)
            if value.phase > phase { throw HanlinMountedFixtureError.unexpectedPhase(value.phase) }
            if value.phase == phase && value.responsesDelivered == phase { return value }
            // Five bounded 45-second waits allow at most 225 read-only polls, keeping
            // ready/register/provider/finalization requests below the fixture's
            // fixed 256-request cap without extending any deadline.
            try await Task.sleep(for: .seconds(1))
        }
        throw HanlinMountedFixtureError.phaseDeadline(phase)
    }

    private func request<T: Decodable>(_ route: String, method: String, body: Data?,
                                        authenticated: Bool, status: Int) async throws -> T {
        let url = controlURL.appendingPathComponent(route)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body
        if body != nil { request.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        if authenticated {
            request.setValue("Bearer " + controlToken, forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == status,
              http.url == url, data.count <= 131_072 else {
            throw HanlinMountedFixtureError.invalidResponse
        }
        return try JSONDecoder().decode(T.self, from: data)
    }
}

private enum CanonicalPickerObservationError: Error {
    case onboardingOrRecoveryVisible
    case entryDidNotPresentAnotherSurface
}


// BEGIN_NATIVE_SEMANTIC_ANCHOR_UI_V1
extension NativeLaunchTests {
    /// Normal account, document, UITextView selection, confirmation, typing and
    /// cold reopen. The opt-in observer reads native/UI values and cannot act.
    func testActualSemanticSelectionCancelCreateEditAndColdReopen() throws {
        executionTimeAllowance = 1_800
        let scope = UUID(), suffix = String(UUID().uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        app.launchEnvironment["PINKHA_NATIVE_ANCHOR_OBSERVATION"] = "1"
        let spaceName = "Anchor Space " + suffix, documentName = "Anchor Document " + suffix
        let firstText = "Anchor", editedText = "Changed"
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentName)

        let addParagraph = app.buttons["any-native-add-paragraph"]
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: addParagraph, timeout: 60)
        addParagraph.tap()
        let editors = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        let editor = editors.firstMatch
        waitForNativeEditorInput(app, editor)
        editor.tap(); editor.typeText(firstText)
        semanticCommit(app, editor: editor, text: firstText)
        XCTAssertEqual(editors.count, 1)
        let blockIdentifier = editor.identifier
        let initial = try semanticObservation(app, phase: "initial-saved") {
            $0.nativeMarkCount == 0 && $0.blocks.count == 1 &&
            $0.blocks[0].textSHA256 == Self.semanticHash(firstText)
        }

        try semanticSelectAll(app, editor: editor, length: firstText.utf16.count)
        tapWhenEnabled(app.buttons["pinkha.semanticAnchor.capture"])
        let confirmation = app.alerts.firstMatch
        waitUntilEnabled(confirmation)
        XCTAssertEqual(app.alerts.count, 1)
        XCTAssertTrue(confirmation.staticTexts[firstText].exists ||
                      confirmation.staticTexts.matching(NSPredicate(format: "label CONTAINS %@", firstText)).firstMatch.exists)
        tapWhenEnabled(confirmation.buttons.matching(NSPredicate(
            format: "label IN %@", ["Cancel", "ביטול"])).firstMatch)
        waitFor(NSPredicate(format: "exists == false"), object: confirmation, timeout: 15)
        let cancelled = try semanticObservation(app, phase: "cancel-without-native-mutation") {
            $0.nativeMarkCount == 0 && $0.nativeVersionSHA256 == initial.nativeVersionSHA256
        }
        XCTAssertEqual(cancelled.blocks[0].sourceSHA256, initial.blocks[0].sourceSHA256)
        XCTAssertEqual(editor.value as? String, firstText)

        // A fresh real selection and a new confirmation own the only capture.
        try semanticSelectAll(app, editor: editor, length: firstText.utf16.count)
        tapWhenEnabled(app.buttons["pinkha.semanticAnchor.capture"])
        waitUntilEnabled(confirmation)
        tapWhenEnabled(confirmation.buttons.matching(NSPredicate(
            format: "label IN %@", ["Create text anchor", "יצירת עוגן טקסט"])).firstMatch)
        let createdMessage = app.alerts.staticTexts.matching(NSPredicate(format: "label IN %@", [
            "The selected text now has an anchor.", "נוסף עוגן לטקסט שנבחר."
        ])).firstMatch
        waitUntilEnabled(createdMessage, timeout: 60)
        tapWhenEnabled(app.alerts.buttons.matching(NSPredicate(
            format: "label IN %@", ["Done", "סיום"])).firstMatch)
        waitFor(NSPredicate(format: "exists == false"), object: app.alerts.firstMatch, timeout: 15)
        let captured = try semanticObservation(app, phase: "native-and-rendered-anchor-created") {
            $0.nativeMarkCount == 1 && $0.blocks.count == 1 &&
            $0.blocks[0].nativeMarks.count == 1 &&
            $0.blocks[0].nativeMarks[0].location == 0 &&
            $0.blocks[0].nativeMarks[0].length == firstText.utf16.count &&
            $0.blocks[0].textSHA256 == Self.semanticHash(firstText)
        }
        XCTAssertNotEqual(captured.nativeVersionSHA256, initial.nativeVersionSHA256)
        XCTAssertEqual(captured.blocks[0].nativeMarks, captured.blocks[0].renderedMarks)
        let identity = captured.blocks[0].nativeMarks[0].identitySHA256
        XCTAssertEqual(editor.value as? String, firstText)
        XCTAssertEqual(editor.identifier, blockIdentifier)

        // Replacing marked characters through ordinary typing must preserve the
        // existing semantic identity and transform its live range/text.
        try semanticSelectAll(app, editor: editor, length: firstText.utf16.count)
        editor.typeText(editedText)
        semanticCommit(app, editor: editor, text: editedText)
        let edited = try semanticObservation(app, phase: "ordinary-ui-edit-preserved-identity") {
            $0.nativeMarkCount == 1 && $0.blocks.count == 1 &&
            $0.blocks[0].textSHA256 == Self.semanticHash(editedText) &&
            $0.blocks[0].nativeMarks.first?.identitySHA256 == identity &&
            $0.blocks[0].nativeMarks.first?.length == editedText.utf16.count
        }
        XCTAssertNotEqual(edited.nativeVersionSHA256, captured.nativeVersionSHA256)
        XCTAssertEqual(edited.blocks[0].nativeMarks, edited.blocks[0].renderedMarks)
        XCTAssertEqual(edited.blocks[0].nativeMarks[0].textSHA256, Self.semanticHash(editedText))

        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentName].firstMatch, timeout: 60)
        waitForNativeEditorInput(app, editor)
        waitFor(NSPredicate(format: "value == %@", editedText), object: editor, timeout: 60)
        let reopened = try semanticObservation(app, phase: "fresh-process-native-and-ui-reopen") {
            $0.nativeMarkCount == 1 && $0.blocks.count == 1 &&
            $0.blocks[0].textSHA256 == Self.semanticHash(editedText) &&
            $0.blocks[0].nativeMarks.first?.identitySHA256 == identity
        }
        XCTAssertNotEqual(reopened.pid, edited.pid)
        XCTAssertNotEqual(reopened.generation, edited.generation)
        XCTAssertEqual(reopened.spaceSHA256, initial.spaceSHA256)
        XCTAssertEqual(reopened.objectSHA256, initial.objectSHA256)
        XCTAssertEqual(reopened.blocks[0].sourceSHA256, edited.blocks[0].sourceSHA256)
        XCTAssertEqual(reopened.blocks[0].nativeMarks, edited.blocks[0].nativeMarks)
        XCTAssertEqual(reopened.blocks[0].nativeMarks, reopened.blocks[0].renderedMarks)
        XCTAssertEqual(editors.count, 1)
        XCTAssertEqual(editor.identifier, blockIdentifier)
        let screenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        screenshot.name = "native-semantic-anchor-cold-reopen-owned-document"
        screenshot.lifetime = .keepAlways
        add(screenshot)
    }

    /// Production Sefaria search and canonical source writes through the real
    /// selected-text menu. The observer hashes only already-read native data.
    func testSemanticSourceLinkSurvivesEditAndColdReopen() throws {
        executionTimeAllowance = 1_800
        let scope = UUID(), suffix = String(UUID().uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        app.launchEnvironment["PINKHA_NATIVE_ANCHOR_OBSERVATION"] = "1"
        let spaceName = "Source Anchor Space " + suffix
        let documentName = "Source Anchor Document " + suffix
        let firstText = "Anchor", editedText = "Changed", reference = "Genesis 1:1"
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentName)
        tapWhenEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        let editor = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-")).firstMatch
        waitForNativeEditorInput(app, editor)
        editor.tap(); editor.typeText(firstText)
        semanticCommit(app, editor: editor, text: firstText)
        try semanticSelectAll(app, editor: editor, length: firstText.utf16.count)
        tapWhenEnabled(app.buttons["pinkha.semanticAnchor.capture"])
        let confirmation = app.alerts.firstMatch
        waitUntilEnabled(confirmation)
        tapWhenEnabled(confirmation.buttons.matching(NSPredicate(
            format: "label IN %@", ["Create text anchor", "יצירת עוגן טקסט"])).firstMatch)
        waitUntilEnabled(app.alerts.staticTexts.matching(NSPredicate(format: "label IN %@", [
            "The selected text now has an anchor.", "נוסף עוגן לטקסט שנבחר."
        ])).firstMatch, timeout: 60)
        tapWhenEnabled(app.alerts.buttons.matching(NSPredicate(
            format: "label IN %@", ["Done", "סיום"])).firstMatch)
        let captured = try semanticObservation(app, phase: "source-target-native-anchor-created") {
            $0.nativeMarkCount == 1 && $0.blocks.count == 1 &&
            $0.blocks[0].nativeMarks.first?.length == firstText.utf16.count &&
            $0.semanticSources?.isEmpty == true
        }
        let identity = try XCTUnwrap(captured.blocks.first?.nativeMarks.first?.identitySHA256)

        try semanticSelectAll(app, editor: editor, length: firstText.utf16.count)
        try semanticOpenSelectedSources(app)
        let search = app.searchFields.firstMatch
        waitUntilEnabled(search)
        XCTAssertTrue(app.navigationBars.matching(NSPredicate(format: "identifier IN %@ OR label IN %@", [
            "Sources for anchored text", "מקורות לטקסט המעוגן"
        ], ["Sources for anchored text", "מקורות לטקסט המעוגן"])).firstMatch.exists)
        search.tap(); search.typeText(reference)
        let result = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND value == %@",
            "any-native-source-result-", reference)).firstMatch
        waitUntilEnabled(result, timeout: 60)
        let resultID = String(result.identifier.dropFirst("any-native-source-result-".count))
        tapWhenEnabled(app.buttons["any-native-source-link-" + resultID])
        let linked = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND value == %@",
            "any-native-linked-source-", reference))
        waitUntilEnabled(linked.firstMatch, timeout: 60)
        XCTAssertEqual(linked.count, 1)
        let linkedID = linked.firstMatch.identifier
        tapWhenEnabled(app.buttons["any-native-source-search-done"])
        let stored = try semanticObservation(app, phase: "source-link-canonical-native-readback") {
            $0.sourceReadOrigin == "TorahEditorSession.associationRecords" &&
            $0.semanticSources?.count == 1 &&
            $0.semanticSources?.first?.identitySHA256 == identity &&
            $0.semanticSources?.first?.canonicalSHA256 == Self.semanticHash(reference) &&
            $0.semanticSources?.first?.resolution == "resolved"
        }
        let association = try XCTUnwrap(stored.semanticSources?.first)
        XCTAssertEqual(stored.blocks[0].nativeMarks, captured.blocks[0].nativeMarks)

        try semanticSelectAll(app, editor: editor, length: firstText.utf16.count)
        editor.typeText(editedText)
        semanticCommit(app, editor: editor, text: editedText)
        let edited = try semanticObservation(app, phase: "source-link-follows-real-text-edit") {
            $0.blocks.count == 1 && $0.blocks[0].textSHA256 == Self.semanticHash(editedText) &&
            $0.blocks[0].nativeMarks.first?.identitySHA256 == identity &&
            $0.blocks[0].nativeMarks.first?.length == editedText.utf16.count &&
            $0.semanticSources == [association]
        }

        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentName].firstMatch, timeout: 60)
        waitForNativeEditorInput(app, editor)
        let reopened = try semanticObservation(app, phase: "source-link-fresh-process-native-reopen") {
            $0.blocks.count == 1 && $0.blocks[0].textSHA256 == Self.semanticHash(editedText) &&
            $0.semanticSources == [association]
        }
        XCTAssertNotEqual(reopened.pid, edited.pid)
        XCTAssertNotEqual(reopened.generation, edited.generation)
        XCTAssertEqual(reopened.spaceSHA256, captured.spaceSHA256)
        XCTAssertEqual(reopened.objectSHA256, captured.objectSHA256)
        XCTAssertEqual(reopened.blocks[0].sourceSHA256, edited.blocks[0].sourceSHA256)
        XCTAssertEqual(reopened.blocks[0].nativeMarks, edited.blocks[0].nativeMarks)

        try semanticSelectAll(app, editor: editor, length: editedText.utf16.count)
        try semanticOpenSelectedSources(app)
        waitUntilEnabled(app.buttons[linkedID], timeout: 60)
        XCTAssertEqual(app.buttons[linkedID].value as? String, reference)
        let associationID = String(linkedID.dropFirst("any-native-linked-source-".count))
        let unlink = app.buttons["any-native-source-unlink-" + associationID]
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"), object: unlink, timeout: 30)
        XCTAssertGreaterThanOrEqual(unlink.frame.width, 44)
        XCTAssertGreaterThanOrEqual(unlink.frame.height, 44)
        tapWhenEnabled(unlink)
        waitFor(NSPredicate(format: "exists == false"), object: app.buttons[linkedID], timeout: 60)
        tapWhenEnabled(app.buttons["any-native-source-search-done"])
        let unlinked = try semanticObservation(app, phase: "source-unlink-keeps-native-text-and-marker") {
            $0.semanticSources?.isEmpty == true && $0.nativeMarkCount == 1 &&
            $0.blocks.count == 1 && $0.blocks[0].textSHA256 == Self.semanticHash(editedText) &&
            $0.blocks[0].nativeMarks.first?.identitySHA256 == identity
        }
        XCTAssertEqual(unlinked.blocks[0].sourceSHA256, reopened.blocks[0].sourceSHA256)
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentName].firstMatch, timeout: 60)
        let removed = try semanticObservation(app, phase: "source-unlink-fresh-process-readback") {
            $0.semanticSources?.isEmpty == true && $0.nativeMarkCount == 1 &&
            $0.blocks.count == 1 && $0.blocks[0].textSHA256 == Self.semanticHash(editedText) &&
            $0.blocks[0].nativeMarks.first?.identitySHA256 == identity
        }
        XCTAssertNotEqual(removed.pid, unlinked.pid)
        XCTAssertEqual(removed.blocks[0].sourceSHA256, unlinked.blocks[0].sourceSHA256)
        let screenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        screenshot.name = "native-semantic-source-link-and-unlink-cold-reopen"
        screenshot.lifetime = .keepAlways
        add(screenshot)
    }

    private func semanticOpenSelectedSources(_ app: XCUIApplication) throws {
        // The retained original UIKit link-menu hierarchy contains this exact
        // action as a native Button, but does not expose UIAction.identifier.
        // Require one real, enabled, hittable action; never replace the complete
        // native selection witness or invoke the application through a hook.
        let labels = ["Sources for anchored text", "מקורות לטקסט המעוגן"]
        let predicate = NSPredicate(format: "label IN %@", labels)
        var selected: XCUIElement?
        let ready = NSPredicate { _, _ in
            let matches = app.buttons.matching(predicate).allElementsBoundByIndex
                + app.descendants(matching: .menuItem).matching(predicate).allElementsBoundByIndex
            let actions = matches.filter { $0.exists && $0.isEnabled && $0.isHittable }
            guard actions.count == 1 else { return false }
            selected = actions[0]
            return true
        }
        let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: ready, object: app)], timeout: 30)
        XCTAssertEqual(result, .completed, "The selected anchor must expose one real Sources menu action")
        guard result == .completed, let selected else { throw SemanticAnchorUIError.originalComparisonUnavailable }
        XCTAssertTrue(selected.exists && selected.isEnabled && selected.isHittable)
        XCTAssertTrue(labels.contains(selected.label))
        selected.tap()
    }

    private func semanticCommit(_ app: XCUIApplication, editor: XCUIElement, text: String) {
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        let status = app.descendants(matching: .any).matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"), object: status, timeout: 60)
        waitFor(NSPredicate(format: "value == %@", text), object: editor, timeout: 30)
    }

    private func semanticSelectAll(_ app: XCUIApplication, editor: XCUIElement, length: Int) throws {
        editor.tap()
        let focused = try semanticObservation(app, phase: "actual-uikit-selection-before-reselection") {
            $0.blocks.count == 1 && $0.blocks[0].isFirstResponder
        }
        if focused.blocks[0].selectionLength > 0 {
            // Cancel correctly preserves UIKit's selection. A tap in the empty
            // paragraph area can keep that selection; a real physical arrow
            // key collapses it through UIKit's native text-input system.
            // No selection is set through the observer or an app test hook.
            editor.typeKey(.rightArrow, modifierFlags: [])
            _ = try semanticObservation(app, phase: "actual-uikit-caret-before-reselection") {
                $0.blocks.count == 1 && $0.blocks[0].isFirstResponder &&
                $0.blocks[0].selectionLength == 0
            }
        }
        editor.press(forDuration: 1.2)
        let action = app.descendants(matching: .any).matching(NSPredicate(
            format: "label IN %@", ["Select All", "בחר הכל", "בחר הכול", "בחירת הכול"])).firstMatch
        // A native long press can itself select this entire one-word paragraph;
        // UIKit then omits the redundant Select All item. Either path must still
        // satisfy the same complete, actual UIKit range witness below.
        if action.waitForExistence(timeout: 3) { tapWhenEnabled(action) }
        _ = try semanticObservation(app, phase: "actual-uikit-selected-range") {
            $0.blocks.count == 1 && $0.blocks[0].isFirstResponder &&
            $0.blocks[0].selectionLocation == 0 && $0.blocks[0].selectionLength == length
        }
    }

    private func semanticObservation(_ app: XCUIApplication, phase: String,
        predicate: @escaping (SemanticAnchorUIObservation) -> Bool) throws -> SemanticAnchorUIObservation {
        let element = app.descendants(matching: .any)
            .matching(identifier: "any-native-semantic-anchor-observation").firstMatch
        var matched: SemanticAnchorUIObservation?
        let condition = NSPredicate { _, _ in
            guard element.exists, let value = element.value as? String,
                  let data = value.data(using: .utf8), data.count <= 24_576,
                  let observation = try? JSONDecoder().decode(SemanticAnchorUIObservation.self, from: data),
                  observation.state == "MATCHED", observation.mode == "read-only",
                  observation.engineCalls == 0, observation.mutations == 0, observation.selectionChanges == 0,
                  observation.nativeMarkCount == observation.renderedMarkCount,
                  predicate(observation) else { return false }
            matched = observation
            return true
        }
        let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: condition, object: element)], timeout: 60)
        XCTAssertEqual(result, .completed, "Original native/rendered comparison failed at " + phase)
        guard result == .completed, let matched else { throw SemanticAnchorUIError.originalComparisonUnavailable }
        let attachment = XCTAttachment(data: try JSONEncoder().encode(matched), uniformTypeIdentifier: "public.json")
        attachment.name = "native-semantic-anchor-" + phase
        attachment.lifetime = .keepAlways
        add(attachment)
        return matched
    }

    private static func semanticHash(_ value: String) -> String {
        SHA256.hash(data: Data(value.utf8)).map { String(format: "%02x", $0) }.joined()
    }
}

private enum SemanticAnchorUIError: Error { case originalComparisonUnavailable }

private struct SemanticAnchorUIObservation: Codable {
    struct Source: Codable, Equatable {
        let identitySHA256: String
        let associationSHA256: String
        let canonicalSHA256: String
        let recordSHA256: String
        let resolution: String
    }
    let sourceReadOrigin: String?
    let semanticSources: [Source]?
    struct Mark: Codable, Equatable {
        let identitySHA256: String
        let location: Int
        let length: Int
        let textSHA256: String
    }
    struct Block: Codable {
        let blockSHA256: String
        let textSHA256: String
        let sourceSHA256: String
        let utf16Length: Int
        let nativeMarks: [Mark]
        let renderedMarks: [Mark]
        let selectionLocation: Int
        let selectionLength: Int
        let isFirstResponder: Bool
    }
    let schema: String
    let state: String
    let mode: String
    let pid: Int
    let generation: String
    let spaceSHA256: String
    let objectSHA256: String
    let nativeVersionSHA256: String
    let engineCalls: Int
    let mutations: Int
    let selectionChanges: Int
    let nativeMarkCount: Int
    let renderedMarkCount: Int
    let blocks: [Block]
}
// END_NATIVE_SEMANTIC_ANCHOR_UI_V1


extension NativeLaunchTests {
    // BEGIN_NATIVE_SHARING_OWNER_UI_V1
    /// Exercise the shared permissions screen against the real Any account and
    /// signed invitation store. No invitation token or recovery phrase is read.
    func testNativeSharingInvitationConfirmationCancellationAndColdReopen() throws {
        executionTimeAllowance = 900
        let scope = UUID()
        let app = makeApplication(scope: scope)
        let spaceName = "Sharing UI Space " + String(scope.uuidString.prefix(8))
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)

        func uniqueButton(_ query: XCUIElementQuery, timeout: TimeInterval = 30) -> XCUIElement {
            let ready = NSPredicate { _, _ in
                let leaves = query.allElementsBoundByIndex.filter {
                    $0.descendants(matching: .button).count == 0
                }
                return leaves.count == 1 && leaves[0].exists
                    && leaves[0].isEnabled && leaves[0].isHittable
            }
            waitFor(ready, object: app, timeout: timeout)
            let leaves = query.allElementsBoundByIndex.filter {
                $0.descendants(matching: .button).count == 0
            }
            XCTAssertEqual(leaves.count, 1, "One rendered, actionable sharing control is required.")
            return leaves.first ?? query.firstMatch
        }
        func identifier(_ value: String) -> XCUIElementQuery {
            app.buttons.matching(identifier: value)
        }
        func labels(_ values: [String]) -> NSPredicate {
            NSPredicate(format: "label IN %@", values)
        }
        let createID = "pinkha.sharing.createInvitation"
        let shareID = "pinkha.sharing.shareInvitation"
        let revokeLabels = ["ביטול הזמנה", "Revoke invitation"]
        let closeLabels = ["סגירה", "Close"]

        func assertOwner() {
            let owner = app.staticTexts.matching(labels(["בעלים", "owner"])).firstMatch
            let you = app.staticTexts.matching(labels(["אתה", "You"])).firstMatch
            waitUntilEnabled(owner, timeout: 30)
            waitUntilEnabled(you, timeout: 30)
            XCTAssertFalse(app.staticTexts.matching(labels([
                "לא ניתן לרענן. בדוק את החיבור ונסה שוב.",
                "Unable to refresh. Check the connection and try again.",
                "לא ניתן לאמת את ביצוע הפעולה. רענן לפני ניסיון נוסף.",
                "The action could not be confirmed. Refresh before trying again."
            ])).firstMatch.exists)
        }
        func openSharing() {
            uniqueButton(identifier("any-native-members"), timeout: 60).tap()
            let screen = app.descendants(matching: .any)
                .matching(identifier: "pinkha.sharing.members").firstMatch
            waitUntilEnabled(screen, timeout: 30)
            // SwiftUI renders the navigation title as a static-text descendant;
            // the enclosing navigation bar need not carry that title as its label.
            let titles = app.navigationBars.staticTexts.matching(labels([
                "חברים והזמנות", "Members and invitations"
            ]))
            waitFor(NSPredicate { _, _ in
                let visible = titles.allElementsBoundByIndex.filter {
                    $0.exists && $0.isEnabled && $0.isHittable
                }
                return visible.count == 1
            }, object: app, timeout: 30)
            XCTAssertEqual(titles.allElementsBoundByIndex.filter {
                $0.exists && $0.isEnabled && $0.isHittable
            }.count, 1, "One visible localized members-and-invitations title is required.")
            assertOwner()
        }
        func assertInvitation(_ present: Bool) {
            let expected = NSPredicate { _, _ in
                let share = identifier(shareID).allElementsBoundByIndex.filter {
                    $0.descendants(matching: .button).count == 0
                }
                let revoke = app.buttons.matching(labels(revokeLabels))
                    .allElementsBoundByIndex.filter {
                        $0.descendants(matching: .button).count == 0
                    }
                let create = identifier(createID).allElementsBoundByIndex.filter {
                    $0.descendants(matching: .button).count == 0
                }
                if present {
                    return share.count == 1 && revoke.count == 1
                        && share[0].isEnabled && revoke[0].isEnabled && create.isEmpty
                }
                return share.isEmpty && revoke.isEmpty && create.count == 1
                    && create[0].isEnabled
            }
            waitFor(expected, object: app, timeout: 60)
            assertOwner()
        }
        func confirm(_ accepted: Bool, message: [String]) {
            let alert = app.alerts.firstMatch
            waitUntilEnabled(alert, timeout: 30)
            XCTAssertEqual(app.alerts.count, 1)
            XCTAssertTrue(alert.staticTexts.matching(labels([
                "אישור שינוי גישה", "Confirm access change"
            ])).firstMatch.exists)
            XCTAssertTrue(alert.staticTexts.matching(labels(message)).firstMatch.exists)
            uniqueButton(alert.buttons.matching(labels(accepted
                ? ["אישור", "Confirm"] : ["ביטול", "Cancel"]))).tap()
            waitFor(NSPredicate(format: "exists == false"), object: alert, timeout: 30)
        }
        func coldOpenSharing() {
            uniqueButton(app.navigationBars.buttons.matching(labels(closeLabels))).tap()
            waitFor(NSPredicate(format: "exists == false"),
                    object: app.descendants(matching: .any)
                        .matching(identifier: "pinkha.sharing.members").firstMatch, timeout: 30)
            reopenOwnedWorkspace(app, spaceName: spaceName)
            openSharing()
        }
        func checkpoint(_ phase: String) {
            // The screen contains controls and membership, not the invitation's
            // secret payload. Never request its ShareLink or a complete AX tree.
            let attachment = XCTAttachment(string: phase)
            attachment.name = "native-sharing-owner-stage"
            attachment.lifetime = .keepAlways
            add(attachment)
        }

        let createMessage = [
            "ליצור הזמנה שתאפשר לבקש גישה למרחב הזה?",
            "Create an invitation that allows someone to request access to this space?"
        ]
        let revokeMessage = [
            "לבטל את ההזמנה הזו? לא יהיה אפשר לבקש להצטרף באמצעותה.",
            "Revoke this invitation? It will no longer allow requests to join."
        ]
        openSharing()
        assertInvitation(false)
        uniqueButton(identifier(createID)).tap()
        confirm(false, message: createMessage)
        assertInvitation(false)
        coldOpenSharing()
        assertInvitation(false)
        checkpoint("create-cancelled-and-absent-after-new-app-process")

        uniqueButton(identifier(createID)).tap()
        confirm(true, message: createMessage)
        assertInvitation(true)
        coldOpenSharing()
        assertInvitation(true)
        checkpoint("confirmed-invitation-retained-after-new-app-process")

        uniqueButton(app.buttons.matching(labels(revokeLabels))).tap()
        confirm(false, message: revokeMessage)
        assertInvitation(true)
        coldOpenSharing()
        assertInvitation(true)
        checkpoint("revocation-cancelled-and-invitation-retained-after-new-app-process")

        uniqueButton(app.buttons.matching(labels(revokeLabels))).tap()
        confirm(true, message: revokeMessage)
        assertInvitation(false)
        coldOpenSharing()
        assertInvitation(false)
        checkpoint("confirmed-revocation-retained-after-new-app-process")
    }
    // END_NATIVE_SHARING_OWNER_UI_V1

}

// BEGIN_NATIVE_MINIAPPS_CROSS_APP_UI_V1
extension NativeLaunchTests {
    /// A fresh controller-owned simulator uses the ordinary app storage and
    /// Keychain configuration so an OS callback after process termination does
    /// not depend on test-only launch arguments.
    func testAnyMiniAppsTextStudioWarmAndColdReturnPersistInNativeDocument() throws {
        executionTimeAllowance = 900
        XCTAssertEqual(ProcessInfo.processInfo.environment["PINKHA_SIMULATOR_UI_DISPOSABLE"], "1")
        XCTAssertEqual(ProcessInfo.processInfo.environment["PINKHA_NATIVE_UI_UNIFIED_HOST"], "1")
        let app = NativeApplicationUnderTest()
        app.launchArguments = ["--native-ui-test-scope", UUID().uuidString,
                               "-AppleLanguages", "(he,en)", "-AppleLocale", "he_IL"]
        app.launchEnvironment["PINKHA_NATIVE_ANCHOR_OBSERVATION"] = "1"
        app.launchEnvironment["PINKHA_NATIVE_ANCHOR_OBSERVATION_NORMAL_STORAGE"] = "1"
        app.launchEnvironment["PINKHA_SIMULATOR_UI_DISPOSABLE"] = "1"
        XCTAssertFalse(app.launchArguments.contains("--native-ui-tests"))
        let companion = XCUIApplication(bundleIdentifier: "com.itorah.hanlinminiapps")
        let suffix = String(UUID().uuidString.prefix(8))
        let spaceName = "MiniApps Space " + suffix
        let documentName = "MiniApps native " + suffix
        let initialText = "מקור Any " + suffix
        let warmText = "MiniApps warm שלום " + suffix
        let coldText = "MiniApps cold תורה " + suffix

        func tapReady(_ element: XCUIElement, timeout: TimeInterval = 45) {
            waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                    object: element, timeout: timeout)
            element.tap()
        }
        func screenshot(_ name: String) {
            let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
            attachment.name = name
            attachment.lifetime = .keepAlways
            add(attachment)
        }
        func expectRendered(_ texts: [String]) {
            for text in texts {
                let matches = app.textViews.matching(NSPredicate(
                    format: "identifier BEGINSWITH %@ AND value == %@", "any-native-block-", text))
                waitFor(NSPredicate(format: "exists == true AND value == %@", text),
                        object: matches.firstMatch, timeout: 60)
                XCTAssertEqual(matches.count, 1, "The actual editor must contain one exact returned paragraph")
            }
            XCTAssertEqual(app.textViews.matching(
                NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-")).count, texts.count)
        }
        func openSavedAccountAndSpace() {
            let saved = app.buttons.matching(identifier: "any-native-saved-account")
            waitUntilEnabled(saved.firstMatch, timeout: 60)
            XCTAssertEqual(saved.count, 1, "The fresh simulator owns exactly one real native account")
            tapReady(saved.firstMatch)
            tapReady(app.buttons[spaceName].firstMatch, timeout: 60)
        }
        func roundTrip(_ text: String, cold: Bool) {
            tapReady(app.buttons["any-native-document-options"])
            tapReady(app.buttons["any-native-miniapps"])
            let launch = app.buttons["miniapps-launch-nativeapp.textstudio"].firstMatch
            tapReady(launch)
            XCTAssertTrue(companion.wait(for: .runningForeground, timeout: 45))
            let input = companion.textViews["miniapps.textstudio.editor"].firstMatch
            waitUntilEnabled(input, timeout: 45)
            XCTAssertEqual(input.value as? String ?? "", "",
                           "A toolbar insert must not send unselected native document content")
            if cold {
                app.terminate()
                XCTAssertTrue(app.wait(for: .notRunning, timeout: 15))
                XCTAssertTrue(companion.wait(for: .runningForeground, timeout: 15))
            }
            tapReady(input)
            input.typeText(text)
            XCTAssertEqual(input.value as? String, text)
            screenshot(cold ? "any-miniapps-real-companion-cold" : "any-miniapps-real-companion-warm")
            tapReady(companion.buttons["miniapps.textstudio.return"])
            // Only the companion's real callback may foreground the source.
            // Do not call launch(), activate() or open() to aid that transition.
            XCTAssertTrue(app.wait(for: .runningForeground, timeout: 45))
            if cold {
                // The native account gate still requires the user's ordinary
                // selection after a new process; a URL cannot authenticate it.
                // No document is selected manually: the retained request must
                // route its exact document only after that native account opens.
                openSavedAccountAndSpace()
            }
        }

        companion.launch()
        XCTAssertTrue(companion.wait(for: .runningForeground, timeout: 45))
        waitUntilEnabled(companion.buttons["hanlin-apps-add"].firstMatch, timeout: 45)
        XCTAssertTrue(companion.descendants(matching: .any)
            .matching(identifier: "hanlin-package-card-Text Studio").firstMatch.waitForExistence(timeout: 30))
        app.launch()
        defer { app.terminate(); companion.terminate() }
        waitUntilEnabled(app.buttons["any-native-account-create"], timeout: 60)
        XCTAssertEqual(app.buttons.matching(identifier: "any-native-saved-account").count, 0)
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentName)
        tapReady(app.buttons["any-native-add-paragraph"], timeout: 60)
        let editor = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-")).firstMatch
        waitForNativeEditorInput(app, editor)
        tapReady(editor)
        editor.typeText(initialText)
        semanticCommit(app, editor: editor, text: initialText)
        let initialHash = Self.semanticHash(initialText)
        let warmHash = Self.semanticHash(warmText)
        let coldHash = Self.semanticHash(coldText)
        let initial = try semanticObservation(app, phase: "miniapps-original-native-before-launch") {
            $0.blocks.count == 1 && $0.blocks[0].textSHA256 == initialHash
        }
        XCTAssertEqual(initial.nativeMarkCount, 0)
        let initialBlock = initial.blocks[0].blockSHA256

        roundTrip(warmText, cold: false)
        expectRendered([initialText, warmText])
        let warm = try semanticObservation(app, phase: "miniapps-warm-native-and-editor-readback") {
            $0.spaceSHA256 == initial.spaceSHA256 && $0.objectSHA256 == initial.objectSHA256 &&
            $0.blocks.count == 2 &&
            Set($0.blocks.map(\.textSHA256)) == Set([initialHash, warmHash]) &&
            $0.blocks.contains { $0.blockSHA256 == initialBlock && $0.textSHA256 == initialHash }
        }
        XCTAssertEqual(initial.pid, warm.pid)
        XCTAssertEqual(Set(warm.blocks.map(\.blockSHA256)).count, 2)
        XCTAssertNotEqual(initial.nativeVersionSHA256, warm.nativeVersionSHA256)
        screenshot("any-miniapps-warm-original-native-document")

        roundTrip(coldText, cold: true)
        expectRendered([initialText, warmText, coldText])
        screenshot("any-miniapps-cold-callback-after-normal-account-selection")

        app.terminate()
        XCTAssertTrue(app.wait(for: .notRunning, timeout: 15))
        app.launch()
        openSavedAccountAndSpace()
        let row = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND label == %@", "any-native-hierarchy-row-", documentName))
        waitUntilEnabled(row.firstMatch, timeout: 60)
        XCTAssertEqual(row.count, 1)
        tapReady(row.firstMatch)
        expectRendered([initialText, warmText, coldText])
        let reopened = try semanticObservation(app, phase: "miniapps-second-cold-native-persistence") {
            $0.spaceSHA256 == initial.spaceSHA256 && $0.objectSHA256 == initial.objectSHA256 &&
            $0.blocks.count == 3 &&
            Set($0.blocks.map(\.textSHA256)) == Set([initialHash, warmHash, coldHash]) &&
            Set(warm.blocks.map(\.blockSHA256)).isSubset(of: Set($0.blocks.map(\.blockSHA256)))
        }
        XCTAssertNotEqual(initial.pid, reopened.pid)
        XCTAssertNotEqual(initial.generation, reopened.generation)
        XCTAssertNotEqual(warm.nativeVersionSHA256, reopened.nativeVersionSHA256)
        XCTAssertEqual(Set(reopened.blocks.map(\.blockSHA256)).count, 3)
        XCTAssertEqual(reopened.nativeMarkCount, 0)
        screenshot("any-miniapps-second-cold-native-and-editor-readback")
        let report: [String: Any] = [
            "schema": "any-miniapps-real-cross-app-ui/v1",
            "fixtureUsesNormalAppStorage": true,
            "testStorageOverrides": false,
            "actualCompanionReturns": 2,
            "sourceTerminatedBeforeSecondReturn": true,
            "manualSourceLaunchForCallback": false,
            "ordinaryAccountSelectionAfterColdCallback": true,
            "manualDocumentSelectionForCallback": false,
            "nativeReadOrigin": "original-runtime-readback-and-mounted-editor",
            "nativeReadExtraCallsByObserver": 0,
            "sameSpaceSHA256": initial.spaceSHA256,
            "sameObjectSHA256": initial.objectSHA256,
            "originalBlockPreserved": reopened.blocks.contains { $0.blockSHA256 == initialBlock && $0.textSHA256 == initialHash },
            "nativeParagraphCount": reopened.blocks.count,
            "initialProcessID": initial.pid,
            "finalProcessID": reopened.pid
        ]
        let attachment = XCTAttachment(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]),
                                       uniformTypeIdentifier: "public.json")
        attachment.name = "any-miniapps-real-cross-app-original-result"
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
// END_NATIVE_MINIAPPS_CROSS_APP_UI_V1
// BEGIN_NATIVE_ACCESSIBILITY_FUTURE_V1
// Future test-only tranche. Its controller must bind the actual App/UI products,
// descriptor, device, account scope and pre/post simctl preference readbacks.
// An environment assertion is not evidence that an OS preference took effect.
@MainActor
extension NativeLaunchTests {
    @objc func testNativeLibraryAndEditorAccessibilityAuditAtRequestedContentSize() throws {
        executionTimeAllowance = 900
        let context = try NativeAccessibilityInvocation.read(
            method: "testNativeLibraryAndEditorAccessibilityAuditAtRequestedContentSize")
        guard #available(iOS 17.0, *) else {
            throw NativeAccessibilityFailure.unsupportedRuntime
        }
        let app = accessibilityApplication(context)
        var reachedEnd = false
        defer {
            finishAccessibilityInvocation(app, context: context, reachedEnd: reachedEnd)
        }
        app.launch()
        let fixture = try createAccessibilityFixture(app, context: context)
        let back = app.navigationBars.buttons.matching(NSPredicate(
            format: "label IN %@", ["ספרייה", "Library"])).firstMatch
        tapWhenEnabled(back)
        waitUntilEnabled(app.buttons["any-native-create-menu"], timeout: 60)
        let row = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND label == %@",
            "any-native-hierarchy-row-", fixture.documentName))
        waitUntilEnabled(row.firstMatch, timeout: 45)
        XCTAssertEqual(row.count, 1)
        let rowIdentifier = row.firstMatch.identifier
        guard rowIdentifier.count > "any-native-hierarchy-row-".count else {
            throw NativeAccessibilityFailure.changedFixture("libraryObjectIdentity")
        }
        try captureAccessibility(app, context: context, fixture: fixture, phase: "library-before-audit",
                                 extra: ["hierarchyRowIdentifier": rowIdentifier])
        try auditNativeAccessibility(app, context: context, fixture: fixture, phase: "library")

        tapWhenEnabled(app.buttons[rowIdentifier], timeout: 45)
        let editor = app.textViews[fixture.blockIdentifier]
        waitFor(NSPredicate(format: "exists == true AND value == %@", fixture.body),
                object: editor, timeout: 60)
        let blocks = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        XCTAssertEqual(blocks.count, 1)
        XCTAssertEqual(editor.identifier, fixture.blockIdentifier)
        XCTAssertEqual(Self.semanticHash(editor.value as? String ?? ""), Self.semanticHash(fixture.body))
        try captureAccessibility(app, context: context, fixture: fixture, phase: "editor-before-audit",
                                 extra: ["hierarchyRowIdentifier": rowIdentifier])
        try auditNativeAccessibility(app, context: context, fixture: fixture, phase: "editor")
        try captureAccessibility(app, context: context, fixture: fixture, phase: "audits-returned",
                                 extra: ["hierarchyRowIdentifier": rowIdentifier,
                                         "auditTypes": "all",
                                         "acceptanceAuthority": "original-xctest-result-and-visual-review"])
        reachedEnd = true
    }

    @objc func testNativeVoiceOverTraversalSpeaksCurrentNativeContent() throws {
        executionTimeAllowance = 900
        let context = try NativeAccessibilityInvocation.read(
            method: "testNativeVoiceOverTraversalSpeaksCurrentNativeContent")
        guard #available(iOS 27.0, *) else {
            throw NativeAccessibilityFailure.unsupportedRuntime
        }
        guard context.contentSize == "large" else {
            throw NativeAccessibilityFailure.invalidInvocation("voiceOverCellContentSize")
        }
        let app = accessibilityApplication(context)
        var reachedEnd = false
        defer {
            finishAccessibilityInvocation(app, context: context, reachedEnd: reachedEnd)
        }
        app.launch()
        let fixture = try createAccessibilityFixture(app, context: context)
        try captureAccessibility(app, context: context, fixture: fixture, phase: "voiceover-before-enable")
        try observeNativeVoiceOver(app, context: context, fixture: fixture)
        reachedEnd = true
    }

    private func accessibilityApplication(_ context: NativeAccessibilityInvocation) -> XCUIApplication {
        let app = makeApplication(scope: context.ownedScope)
        if context.appLanguage == "en" {
            app.launchArguments = [
                "--native-ui-tests", "--native-ui-test-scope", context.ownedScope.uuidString,
                "-AppleLanguages", "(en,he)", "-AppleLocale", "en_US"
            ]
        }
        return app
    }

    private func createAccessibilityFixture(_ app: XCUIApplication,
                                             context: NativeAccessibilityInvocation) throws -> NativeAccessibilityFixture {
        let suffix = String(context.ownedScope.uuidString.prefix(8))
        let spaceName = "Accessibility Space " + suffix
        let documentName = "Accessibility Document " + suffix
        let body = "שלום נגישות. Native speech marker."
        createOwnedWorkspace(app, spaceName: spaceName)
        try createNamedItemWithObservedTransition(app, action: "any-native-new-document", title: documentName)
        let addParagraph = app.buttons["any-native-add-paragraph"]
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: addParagraph, timeout: 60)
        addParagraph.tap()
        let blocks = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        let editor = blocks.firstMatch
        waitForNativeEditorInput(app, editor)
        editor.tap()
        editor.typeText(body)
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        let status = app.descendants(matching: .any).matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"), object: status, timeout: 45)
        XCTAssertEqual(editor.value as? String, body)
        XCTAssertEqual(blocks.count, 1)
        XCTAssertEqual(app.keyboards.count, 0)
        guard editor.identifier.count > "any-native-block-".count,
              editor.identifier.hasPrefix("any-native-block-") else {
            throw NativeAccessibilityFailure.changedFixture("nativeBlockIdentity")
        }
        try requireArchiveObservationPastOnboarding(app)
        return NativeAccessibilityFixture(spaceName: spaceName, documentName: documentName,
                                          body: body, blockIdentifier: editor.identifier)
    }

    @available(iOS 17.0, *)
    private func auditNativeAccessibility(_ app: XCUIApplication,
                                          context: NativeAccessibilityInvocation,
                                          fixture: NativeAccessibilityFixture, phase: String) throws {
        var issues: [[String: String]] = []
        defer {
            do {
                try accessibilityJSON(["schema": "native-accessibility-audit-observation/v1",
                    "invocation": context.dictionary, "phase": phase, "auditTypes": "all",
                    "ignoredIssues": 0, "issues": issues],
                    name: "native-accessibility-" + phase + "-audit")
            } catch {
                XCTFail("Could not retain the actual accessibility audit observations: \(error)")
            }
        }
        try requireArchiveObservationPastOnboarding(app)
        // Returning false preserves every original XCTest audit issue as failure.
        // No element exclusions, ignored issue types, or expected-failure wrapper.
        try app.performAccessibilityAudit(for: .all) { issue in
            issues.append([
                "auditType": String(describing: issue.auditType),
                "compactDescription": issue.compactDescription,
                "detailedDescription": issue.detailedDescription
            ])
            return false
        }
    }

    @available(iOS 27.0, *)
    private func observeNativeVoiceOver(_ app: XCUIApplication,
                                        context: NativeAccessibilityInvocation,
                                        fixture: NativeAccessibilityFixture) throws {
        let service = XCUIDevice.shared.voiceOverService
        guard !service.isEnabled else {
            // A pre-existing setting is not ours to change.
            throw NativeAccessibilityFailure.voiceOverAlreadyEnabled
        }
        var enableAttempted = false
        var enabledObserved = false
        var completedTraversal = false
        var trace: [[String: Any]] = []
        let maximumSearchForwardMoves = 24
        let traversalSeconds: TimeInterval = 60
        var traversalStarted: TimeInterval?
        let marker = "native speech marker"
        func normalized(_ text: String) -> String {
            text.lowercased().split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
        }
        defer {
            var cleanupFailures: [String] = []
            var disabledObserved = false
            if enableAttempted {
                do {
                    try service.disable()
                    disabledObserved = !service.isEnabled
                    if !disabledObserved { cleanupFailures.append("VoiceOver remained enabled after disable().") }
                } catch {
                    cleanupFailures.append("VoiceOver disable() threw: \(error)")
                }
            }
            do {
                try captureAccessibility(app, context: context, fixture: fixture, phase: "voiceover-trace",
                    extra: ["initialVoiceOverEnabled": false,
                            "enableAttempted": enableAttempted, "enabledObserved": enabledObserved,
                            "disabledObserved": disabledObserved, "completedTraversal": completedTraversal,
                            "cleanupFailures": cleanupFailures, "trace": trace,
                            "maximumSearchForwardMoves": maximumSearchForwardMoves,
                            "maximumForwardMoves": maximumSearchForwardMoves + 1,
                            "maximumSpeechOperations": maximumSearchForwardMoves + 5,
                            "traversalBudgetSeconds": traversalSeconds,
                            "traversalElapsedSeconds": traversalStarted.map {
                                ProcessInfo.processInfo.systemUptime - $0
                            } ?? 0,
                            "speechMatchRule": "normalized utterance contains the fixture phrase: " + marker,
                            "focusedAccessibilityIdentifierObserved": false,
                            "acceptanceAuthority": "original-xctest-result-and-visual-review"])
            } catch {
                cleanupFailures.append("Could not retain VoiceOver observations: \(error)")
            }
            if !cleanupFailures.isEmpty {
                XCTFail(cleanupFailures.joined(separator: "\n"))
            }
        }
        enableAttempted = true
        try service.enable()
        enabledObserved = service.isEnabled
        guard enabledObserved else {
            throw NativeAccessibilityFailure.voiceOverDidNotEnable
        }
        traversalStarted = ProcessInfo.processInfo.systemUptime
        func observe(_ action: String, _ operation: () throws -> XCUIVoiceOverService.Output) throws -> String {
            guard let started = traversalStarted,
                  ProcessInfo.processInfo.systemUptime - started <= traversalSeconds else {
                throw NativeAccessibilityFailure.traversalBudgetExhausted
            }
            let before = ProcessInfo.processInfo.systemUptime
            let output: XCUIVoiceOverService.Output
            do {
                output = try operation()
            } catch {
                trace.append(["action": action, "error": String(describing: error),
                              "elapsedSeconds": ProcessInfo.processInfo.systemUptime - started])
                throw error
            }
            let after = ProcessInfo.processInfo.systemUptime
            guard output.utterance.utf8.count <= 16_384 else {
                trace.append(["action": action, "utteranceUTF8Bytes": output.utterance.utf8.count,
                              "utteranceSHA256": Self.semanticHash(output.utterance),
                              "elapsedSeconds": after - started,
                              "error": "Speech exceeded the finite evidence budget."])
                throw NativeAccessibilityFailure.speechEvidenceBudgetExceeded
            }
            trace.append(["action": action, "utterance": output.utterance,
                          "operationSeconds": after - before, "elapsedSeconds": after - started])
            guard after - started <= traversalSeconds else {
                throw NativeAccessibilityFailure.traversalBudgetExhausted
            }
            guard !output.utterance.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                throw NativeAccessibilityFailure.emptySpeech
            }
            return normalized(output.utterance)
        }
        var current = try observe("currentSpeech.initial") { try service.currentSpeech() }
        var moves = 0
        while !current.contains(marker), moves < maximumSearchForwardMoves {
            moves += 1
            current = try observe("moveForward.search.\(moves)") { try service.moveForward() }
        }
        guard current.contains(marker) else {
            throw NativeAccessibilityFailure.fixtureSpeechNotReached
        }
        let atTarget = try observe("currentSpeech.target") { try service.currentSpeech() }
        guard atTarget.contains(marker) else {
            throw NativeAccessibilityFailure.fixtureSpeechChanged
        }
        let next = try observe("moveForward.afterTarget") { try service.moveForward() }
        guard !next.contains(marker), next != atTarget else {
            throw NativeAccessibilityFailure.speechDidNotAdvance
        }
        let returned = try observe("moveBackward.returnToTarget") { try service.moveBackward() }
        guard returned.contains(marker) else {
            throw NativeAccessibilityFailure.fixtureSpeechDidNotReturn
        }
        let confirmed = try observe("currentSpeech.returnedTarget") { try service.currentSpeech() }
        guard confirmed.contains(marker) else {
            throw NativeAccessibilityFailure.fixtureSpeechChanged
        }
        // The public Output contains utterance only. These are real forward/
        // backward speech observations, not proof of an accessibility identifier.
        try captureAccessibility(app, context: context, fixture: fixture, phase: "voiceover-returned",
                                 extra: ["observedUtterance": confirmed,
                                         "focusedAccessibilityIdentifierObserved": false])
        completedTraversal = true
    }

    private func captureAccessibility(_ app: XCUIApplication, context: NativeAccessibilityInvocation,
                                       fixture: NativeAccessibilityFixture, phase: String,
                                       extra: [String: Any] = [:]) throws {
        try requireArchiveObservationPastOnboarding(app)
        var report: [String: Any] = [
            "schema": "native-accessibility-ui-observation/v1", "phase": phase,
            "invocation": context.dictionary, "runnerProcessID": ProcessInfo.processInfo.processIdentifier,
            "runnerSimulatorUDID": ProcessInfo.processInfo.environment["SIMULATOR_UDID"] ?? "",
            "appLaunchArguments": app.launchArguments,
            "spaceName": fixture.spaceName, "documentName": fixture.documentName,
            "blockIdentifier": fixture.blockIdentifier, "bodySHA256": Self.semanticHash(fixture.body),
            "actualOSPreferencesAuthority": "bound-controller-pre-and-post-readbacks",
            "visualReview": "PENDING"
        ]
        for (key, value) in extra { report[key] = value }
        try accessibilityJSON(report, name: "native-accessibility-" + phase)
        let tree = String(decoding: app.debugDescription.utf8.prefix(131_072), as: UTF8.self)
        try requireArchiveObservationPastOnboarding(app)
        let ax = XCTAttachment(string: tree)
        ax.name = "native-accessibility-" + phase + "-private-ax"
        ax.lifetime = .keepAlways
        add(ax)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "native-accessibility-" + phase
        screenshot.lifetime = .keepAlways
        add(screenshot)
    }

    private func accessibilityJSON(_ object: [String: Any], name: String) throws {
        let data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func finishAccessibilityInvocation(_ app: XCUIApplication,
                                               context: NativeAccessibilityInvocation, reachedEnd: Bool) {
        var failures: [String] = []
        do {
            // This final diagnostic deliberately covers startup, onboarding and
            // failure screens on this qualified disposable device/account.
            // Keep it private: never publish these AX or PNG contents to Git.
            let prefix = "PRIVATE-native-accessibility-final-" + (context.dictionary["method"] ?? "")
            let tree = String(decoding: app.debugDescription.utf8.prefix(131_072), as: UTF8.self)
            let ax = XCTAttachment(string: tree)
            ax.name = prefix + "-ax"
            ax.lifetime = .keepAlways
            add(ax)
            let screenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
            screenshot.name = prefix + "-screen"
            screenshot.lifetime = .keepAlways
            add(screenshot)
            try accessibilityJSON([
                "schema": "native-accessibility-private-final/v1",
                "invocation": context.dictionary, "caseReachedEnd": reachedEnd,
                "appStateBeforeTermination": String(describing: app.state),
                "runnerSimulatorUDID": ProcessInfo.processInfo.environment["SIMULATOR_UDID"] ?? "",
                "captureRequiresCompletedOnboarding": false,
                "contentsPrivate": true, "captureBeforeTermination": true
            ], name: prefix + "-context")
        } catch {
            failures.append("The final private accessibility UI capture failed: \(error)")
        }
        app.terminate()
        if !app.wait(for: .notRunning, timeout: 15) {
            failures.append("The owned accessibility App did not terminate.")
        }
        if !failures.isEmpty {
            XCTFail(failures.joined(separator: "\n"))
        }
    }
}

private struct NativeAccessibilityFixture {
    let spaceName: String
    let documentName: String
    let body: String
    let blockIdentifier: String
}

private struct NativeAccessibilityInvocation {
    let dictionary: [String: String]
    let ownedScope: UUID
    var appLanguage: String { dictionary["appLanguage"]! }
    var contentSize: String { dictionary["contentSize"]! }

    static func read(method: String) throws -> Self {
        let environment = ProcessInfo.processInfo.environment
        guard environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1",
              let raw = environment["PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_JSON"],
              raw.utf8.count <= 16_384,
              let bytes = raw.data(using: .utf8),
              let fields = try JSONSerialization.jsonObject(with: bytes) as? [String: String] else {
            throw NativeAccessibilityFailure.invalidInvocation("missingQualifiedContext")
        }
        let keys: Set<String> = ["schema", "runID", "appSourceCommit", "uiSourceCommit",
            "simulatorUDID", "ownedScope", "method", "appLanguage", "osLanguage",
            "contentSize", "appearance", "deviceFamily", "settingsReadbackSHA256"]
        let digest = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
        func hex(_ value: String?, count: Int) -> Bool {
            guard let value, value.count == count else { return false }
            return value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
        }
        guard Set(fields.keys) == keys,
              fields["schema"] == "native-accessibility-invocation/v1",
              fields["method"] == method,
              let scopeValue = fields["ownedScope"], let scope = UUID(uuidString: scopeValue),
              let runValue = fields["runID"], UUID(uuidString: runValue) != nil,
              let deviceValue = fields["simulatorUDID"], let device = UUID(uuidString: deviceValue),
              let observedDeviceValue = environment["SIMULATOR_UDID"],
              UUID(uuidString: observedDeviceValue) == device,
              fields["appLanguage"].map({ ["he", "en"].contains($0) }) == true,
              fields["osLanguage"].map({ ["he", "en"].contains($0) }) == true,
              fields["contentSize"].map({
                  ["large", "accessibility-extra-extra-extra-large"].contains($0)
              }) == true,
              fields["appearance"].map({ ["light", "dark"].contains($0) }) == true,
              fields["deviceFamily"].map({ ["iphone", "ipad"].contains($0) }) == true,
              hex(fields["appSourceCommit"], count: 40), hex(fields["uiSourceCommit"], count: 40),
              hex(fields["settingsReadbackSHA256"], count: 64),
              environment["PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_SHA256"] == digest else {
            throw NativeAccessibilityFailure.invalidInvocation("contextBindingMismatch")
        }
        // The closed external controller supplies and verifies these identities.
        // This parser does not independently attest source or preference state.
        return Self(dictionary: fields, ownedScope: scope)
    }
}

private enum NativeAccessibilityFailure: Error {
    case invalidInvocation(String)
    case unsupportedRuntime
    case changedFixture(String)
    case voiceOverAlreadyEnabled
    case voiceOverDidNotEnable
    case traversalBudgetExhausted
    case emptySpeech
    case speechEvidenceBudgetExceeded
    case fixtureSpeechNotReached
    case fixtureSpeechChanged
    case speechDidNotAdvance
    case fixtureSpeechDidNotReturn
}
// END_NATIVE_ACCESSIBILITY_FUTURE_V1

// BEGIN_NATIVE_STYLED_BLOCK_ACCEPTANCE_FUTURE_V1
import UIKit

extension NativeLaunchTests {
    /// Each small document fits the original complete-visible-snapshot observer
    /// on iPhone as well as iPad. One account/Space and one cold reopen serve all
    /// nine actual menu actions; this does not repeat the accepted drag journey.
    @objc func testTypedBlockMenusPersistAllNineKindsAndColdReopen() throws {
        executionTimeAllowance = 1_800
        let context = try styledContext(method: "testTypedBlockMenusPersistAllNineKindsAndColdReopen")
        let app = styledApplication(context)
        var reachedEnd = false
        defer { finishAccessibilityInvocation(app, context: context, reachedEnd: reachedEnd) }
        app.launch()
        let suffix = String(context.ownedScope.uuidString.prefix(8))
        let spaceName = "Styled Space " + suffix
        createOwnedWorkspace(app, spaceName: spaceName)
        var documents: [NativeStyledDocument] = []
        var firstPID: Int?
        var spaceHash: String?
        for (index, choice) in NativeStyledChoice.allCases.enumerated() {
            let title = "Styled " + String(index + 1) + " " + suffix
            try createNamedItemWithObservedTransition(app, action: "any-native-new-document", title: title)
            let block = try createStyledBlock(app, context: context, choice: choice,
                existing: [], body: "אב7", phase: "choice-" + choice.rawValue)
            let read = try styledReadback(app, phase: "choice-" + choice.rawValue + "-saved", count: 1) {
                Self.matches($0, blocks: [block], appLanguage: context.appLanguage,
                             category: UIContentSizeCategory.large.rawValue, nominal: true)
            }
            if let firstPID { XCTAssertEqual(read.value.original.pid, firstPID) }
            else { firstPID = read.value.original.pid }
            if let spaceHash { XCTAssertEqual(read.value.original.spaceSHA256, spaceHash) }
            else { spaceHash = read.value.original.spaceSHA256 }
            try captureStyled(app, context: context, read: read, phase: "choice-" + choice.rawValue + "-saved")
            returnToStyledLibrary(app)
            let row = try styledLibraryRow(app, title: title)
            let objectID = String(row.identifier.dropFirst("any-native-hierarchy-row-".count))
            XCTAssertEqual(read.value.original.objectSHA256, Self.semanticHash(objectID))
            documents.append(.init(title: title, rowIdentifier: row.identifier,
                                   objectSHA256: read.value.original.objectSHA256, blocks: [block]))
        }

        // Exercise the separate original UIKit menu surface once. Its complete
        // nine-choice menu is checked before the representative insertion.
        var first = try XCTUnwrap(documents.first)
        tapWhenEnabled(app.buttons[first.rowIdentifier], timeout: 60)
        let original = try XCTUnwrap(first.blocks.first)
        let inserted = try createStyledBlock(app, context: context, choice: .heading3,
            existing: first.blocks, body: "ת8", before: original.identifier, phase: "before-menu")
        first.blocks.insert(inserted, at: 0)
        let before = try styledReadback(app, phase: "before-menu-saved", count: 2) {
            $0.original.objectSHA256 == first.objectSHA256 &&
            Self.matches($0, blocks: first.blocks, appLanguage: context.appLanguage,
                         category: UIContentSizeCategory.large.rawValue, nominal: true)
        }
        XCTAssertEqual(before.value.original.blocks.map(\.blockSHA256), first.blocks.map { Self.blockHash($0.identifier) })
        XCTAssertLessThan(app.textViews[inserted.identifier].frame.minY, app.textViews[original.identifier].frame.minY)
        try captureStyled(app, context: context, read: before, phase: "before-menu-saved")
        documents[0] = first

        // This is the sole cold-reopen phase for the complete catalog.
        let originalPID = try XCTUnwrap(firstPID)
        let originalSpaceHash = try XCTUnwrap(spaceHash)
        reopenOwnedWorkspace(app, spaceName: spaceName)
        for document in documents {
            tapWhenEnabled(app.buttons[document.rowIdentifier], timeout: 60)
            let lastBlock = try XCTUnwrap(document.blocks.last)
            let read = try styledReadback(app, phase: "cold-" + lastBlock.choice.rawValue,
                                         count: document.blocks.count) {
                $0.original.pid != originalPID && $0.original.spaceSHA256 == originalSpaceHash &&
                $0.original.objectSHA256 == document.objectSHA256 &&
                Self.matches($0, blocks: document.blocks, appLanguage: context.appLanguage,
                             category: UIContentSizeCategory.large.rawValue, nominal: true)
            }
            for block in document.blocks { try requireStyledMarker(app, block: block) }
            try captureStyled(app, context: context, read: read,
                phase: "cold-" + lastBlock.choice.rawValue,
                extra: ["hierarchyRowIdentifier": document.rowIdentifier,
                        "objectIDFromOriginalHierarchy": String(document.rowIdentifier.dropFirst("any-native-hierarchy-row-".count))])
            returnToStyledLibrary(app)
        }
        XCTAssertEqual(documents.count, 9)
        reachedEnd = true
    }

    /// The existing, sole NativeUI controller must change the owned simulator's
    /// setting in response to the private runner rendezvous. No launch override,
    /// settings UI assumption, app hook, or native mutation simulates this change.
    @objc func testNativeStyledTypographyRefreshesLiveAtAccessibilitySize() throws {
        executionTimeAllowance = 900
        let context = try styledContext(method: "testNativeStyledTypographyRefreshesLiveAtAccessibilitySize")
        let app = styledApplication(context)
        var reachedEnd = false
        defer { finishAccessibilityInvocation(app, context: context, reachedEnd: reachedEnd) }
        app.launch()
        let suffix = String(context.ownedScope.uuidString.prefix(8))
        createOwnedWorkspace(app, spaceName: "Live Type Space " + suffix)
        try createNamedItemWithObservedTransition(app, action: "any-native-new-document",
                                                 title: "Live Type " + suffix)
        var blocks: [NativeStyledBlock] = []
        for (choice, body) in [(NativeStyledChoice.heading1, "אב"), (.code, "A7"), (.paragraph, "")] {
            blocks.append(try createStyledBlock(app, context: context, choice: choice,
                existing: blocks, body: body, phase: "live-" + choice.rawValue))
        }
        let baseline = try styledReadback(app, phase: "live-large-before", count: 3) {
            $0.original.blocks.allSatisfy { !$0.isFirstResponder } &&
            Self.matches($0, blocks: blocks, appLanguage: context.appLanguage,
                         category: UIContentSizeCategory.large.rawValue, nominal: true)
        }
        try captureStyled(app, context: context, read: baseline, phase: "live-large-before")
        let rendezvous = try NativeTypographyRendezvous(context: context)
        let expandedReceipt = try rendezvous.request("accessibility-extra-extra-extra-large", phase: "expanded",
                                                     before: baseline)
        let expanded = try styledReadback(app, phase: "live-accessibility", count: 3) {
            Self.sameNativeAndSelection($0, baseline.value) &&
            Self.matches($0, blocks: blocks, appLanguage: context.appLanguage,
                         category: UIContentSizeCategory.accessibilityExtraExtraExtraLarge.rawValue,
                         nominal: false) && Self.fontsAreLarger($0, than: baseline.value)
        }
        try captureStyled(app, context: context, read: expanded, phase: "live-accessibility",
                          extra: ["controllerReadback": expandedReceipt])
        let restoredReceipt = try rendezvous.request("large", phase: "restored", before: expanded)
        let restored = try styledReadback(app, phase: "live-large-restored", count: 3) {
            Self.sameNativeAndSelection($0, baseline.value) &&
            Self.matches($0, blocks: blocks, appLanguage: context.appLanguage,
                         category: UIContentSizeCategory.large.rawValue, nominal: true) &&
            Self.fontsEqual($0, baseline.value)
        }
        try captureStyled(app, context: context, read: restored, phase: "live-large-restored",
                          extra: ["controllerReadback": restoredReceipt,
                                  "baselineObservationSHA256": Self.styledHash(baseline.raw),
                                  "baselineAppPID": baseline.value.original.pid,
                                  "restoredAppPID": restored.value.original.pid])
        reachedEnd = true
    }

    private func styledContext(method: String) throws -> NativeAccessibilityInvocation {
        let context = try NativeAccessibilityInvocation.read(method: method)
        guard context.contentSize == "large",
              context.dictionary["appSourceCommit"] == context.dictionary["uiSourceCommit"] else {
            throw NativeStyledFailure.invalidContext
        }
        return context
    }

    private func styledApplication(_ context: NativeAccessibilityInvocation) -> XCUIApplication {
        let app = accessibilityApplication(context)
        app.launchEnvironment["PINKHA_NATIVE_ANCHOR_OBSERVATION"] = "1"
        app.launchEnvironment["PINKHA_NATIVE_TYPOGRAPHY_OBSERVATION"] = "1"
        return app
    }

    private func createStyledBlock(_ app: XCUIApplication, context: NativeAccessibilityInvocation,
        choice: NativeStyledChoice, existing: [NativeStyledBlock], body: String,
        before: String? = nil, phase: String) throws -> NativeStyledBlock {
        if app.keyboards.firstMatch.exists { tapWhenEnabled(app.buttons["any-native-editor-done"]) }
        if let before {
            let blockID = String(before.dropFirst("any-native-block-".count))
            tapWhenEnabled(app.buttons["any-native-block-menu-" + blockID])
            tapWhenEnabled(app.buttons[context.appLanguage == "he" ? "הוספת בלוק לפני" : "Add block before"])
        } else {
            tapWhenEnabled(app.buttons["any-native-document-options"])
            tapWhenEnabled(app.buttons["any-native-add-block-menu"])
        }
        for item in NativeStyledChoice.allCases {
            let row = app.buttons.matching(NSPredicate(format: "label == %@", item.title(context.appLanguage)))
            waitUntilEnabled(row.firstMatch)
            XCTAssertEqual(row.count, 1, "The actual menu must contain exactly one of each published choice.")
        }
        tapWhenEnabled(app.buttons.matching(NSPredicate(format: "label == %@", choice.title(context.appLanguage))).firstMatch)
        let oldIDs = existing.map(\.identifier)
        let candidates = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND NOT identifier IN %@", "any-native-block-", oldIDs))
        waitForNativeEditorInput(app, candidates.firstMatch)
        XCTAssertEqual(candidates.count, 1)
        let editor = candidates.firstMatch
        let identifier = editor.identifier
        guard identifier.count > "any-native-block-".count else { throw NativeStyledFailure.missingBlockIdentity }
        editor.tap()
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        tapWhenEnabled(app.buttons["any-native-document-options"])
        tapWhenEnabled(app.buttons["any-native-writing-direction-rtl"])
        let empty = try styledReadback(app, phase: phase + "-empty-rtl", count: existing.count + 1) {
            Self.matchesOne($0, identifier: identifier, choice: choice, body: "", nativeStyleJSON: nil,
                            appLanguage: context.appLanguage,
                            category: UIContentSizeCategory.large.rawValue, nominal: true)
        }
        try captureStyled(app, context: context, read: empty, phase: phase + "-empty-rtl")
        if !body.isEmpty {
            editor.tap(); editor.typeText(body)
            tapWhenEnabled(app.buttons["any-native-editor-done"])
        }
        if app.keyboards.firstMatch.exists { tapWhenEnabled(app.buttons["any-native-editor-done"]) }
        let saved = try styledReadback(app, phase: phase + "-filled", count: existing.count + 1) {
            Self.matchesOne($0, identifier: identifier, choice: choice, body: body, nativeStyleJSON: nil,
                            appLanguage: context.appLanguage,
                            category: UIContentSizeCategory.large.rawValue, nominal: true)
        }
        let observed = try XCTUnwrap(saved.value.presentations.first { $0.blockSHA256 == Self.blockHash(identifier) })
        let result = NativeStyledBlock(choice: choice, identifier: identifier, body: body,
                                      nativeStyleJSON: observed.textPresentation.nativeStyleJSON)
        try requireStyledMarker(app, block: result)
        return result
    }

    private func returnToStyledLibrary(_ app: XCUIApplication) {
        let back = app.navigationBars.buttons.matching(NSPredicate(format: "label IN %@", ["ספרייה", "Library"]))
        tapWhenEnabled(back.firstMatch)
        waitUntilEnabled(app.buttons["any-native-create-menu"], timeout: 60)
    }

    private func styledLibraryRow(_ app: XCUIApplication, title: String) throws -> XCUIElement {
        let row = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND label == %@",
            "any-native-hierarchy-row-", title))
        waitUntilEnabled(row.firstMatch, timeout: 45)
        XCTAssertEqual(row.count, 1)
        guard row.firstMatch.identifier.count > "any-native-hierarchy-row-".count else {
            throw NativeStyledFailure.missingObjectIdentity
        }
        return row.firstMatch
    }

    private func requireStyledMarker(_ app: XCUIApplication, block: NativeStyledBlock) throws {
        let editor = app.textViews[block.identifier]
        if block.body.isEmpty {
            waitUntilEnabled(editor)
            // Match the original empty-editor helper: UIKit may expose nil for
            // an empty value. The paired native/rendered UTF-16 length is zero.
            XCTAssertEqual(editor.value as? String ?? "", "")
        } else {
            waitFor(NSPredicate(format: "exists == true AND value == %@", block.body), object: editor, timeout: 45)
        }
        if let marker = block.choice.marker {
            let row = app.tables["any-native-editor-blocks"].cells.containing(.textView, identifier: block.identifier)
            XCTAssertEqual(row.count, 1)
            XCTAssertEqual(row.firstMatch.staticTexts.matching(NSPredicate(format: "label == %@", marker)).count, 1)
        }
    }

    private func styledReadback(_ app: XCUIApplication, phase: String, count: Int,
        predicate: @escaping (NativeStyledSnapshot) -> Bool) throws -> NativeStyledReadback {
        let elements = app.descendants(matching: .any).matching(identifier: "any-native-semantic-anchor-observation")
        var accepted: NativeStyledReadback?
        var last: Data?
        let condition = NSPredicate { _, _ in
            guard elements.count == 1, let text = elements.firstMatch.value as? String,
                  let raw = text.data(using: .utf8), raw.count <= 24_576 else { return false }
            last = raw
            guard let snapshot = try? JSONDecoder().decode(NativeStyledSnapshot.self, from: raw),
                  snapshot.original.schema == "any-semantic-anchor-native-rendered/v1",
                  snapshot.original.state == "MATCHED", snapshot.original.mode == "read-only",
                  snapshot.original.engineCalls == 0, snapshot.original.mutations == 0,
                  snapshot.original.selectionChanges == 0,
                  snapshot.original.nativeMarkCount == 0, snapshot.original.renderedMarkCount == 0,
                  snapshot.original.blocks.count == count, snapshot.presentations.count == count,
                  snapshot.original.blocks.map(\.blockSHA256) == snapshot.presentations.map(\.blockSHA256),
                  snapshot.presentations.allSatisfy({ $0.textPresentation.schema == "native-mounted-text-presentation/v1"
                      && $0.textPresentation.assignedUIFontOnly
                      && $0.textPresentation.fontReadOrigin == "mounted-UITextView-attributedText-and-typingAttributes"
                      && $0.textPresentation.nativeReadOrigin == "AnyDocumentPresentation.read.snapshot.blocks" }),
                  predicate(snapshot) else { return false }
            accepted = .init(raw: raw, value: snapshot)
            return true
        }
        let state = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: condition, object: app)], timeout: 60)
        guard state == .completed, let accepted else {
            if let last {
                let attachment = XCTAttachment(data: last, uniformTypeIdentifier: "public.json")
                attachment.name = "PRIVATE-native-styled-" + phase + "-FAILED-observation"
                attachment.lifetime = .keepAlways; add(attachment)
            }
            throw NativeStyledFailure.observation(phase)
        }
        return accepted
    }

    private func captureStyled(_ app: XCUIApplication, context: NativeAccessibilityInvocation,
        read: NativeStyledReadback, phase: String, extra: [String: Any] = [:]) throws {
        try requireArchiveObservationPastOnboarding(app)
        let native = XCTAttachment(data: read.raw, uniformTypeIdentifier: "public.json")
        native.name = "PRIVATE-native-styled-" + phase + "-native"; native.lifetime = .keepAlways; add(native)
        var report: [String: Any] = ["schema": "native-styled-ui-observation/v1", "phase": phase,
            "invocation": context.dictionary, "nativeObservationSHA256": Self.styledHash(read.raw),
            "appPIDFromOriginalObserver": read.value.original.pid, "appLaunchArguments": app.launchArguments,
            "runnerProcessID": ProcessInfo.processInfo.processIdentifier,
            "visualReview": "PENDING", "fontClaim": "Assigned UIFont, not per-glyph fallback face"]
        report["visibleBlocks"] = app.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-"))
            .allElementsBoundByIndex.map { element in
                ["identifier": element.identifier, "value": element.value as? String ?? "",
                 "frame": NSStringFromCGRect(element.frame)]
            }
        for (key, value) in extra { report[key] = value }
        try accessibilityJSON(report, name: "PRIVATE-native-styled-" + phase + "-context")
        let ax = XCTAttachment(string: String(decoding: app.debugDescription.utf8.prefix(131_072), as: UTF8.self))
        ax.name = "PRIVATE-native-styled-" + phase + "-ax"; ax.lifetime = .keepAlways; add(ax)
        let screen = XCTAttachment(screenshot: app.screenshot())
        screen.name = "PRIVATE-native-styled-" + phase + "-screen"; screen.lifetime = .keepAlways; add(screen)
    }

    private static func blockHash(_ identifier: String) -> String {
        semanticHash(String(identifier.dropFirst("any-native-block-".count)))
    }
    private static func styledHash(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
    private static func matches(_ value: NativeStyledSnapshot, blocks: [NativeStyledBlock], appLanguage: String, category: String,
                                nominal: Bool) -> Bool {
        value.original.blocks.map(\.blockSHA256) == blocks.map { blockHash($0.identifier) } &&
        blocks.allSatisfy { matchesOne(value, identifier: $0.identifier, choice: $0.choice, body: $0.body,
            nativeStyleJSON: $0.nativeStyleJSON, appLanguage: appLanguage, category: category, nominal: nominal) }
    }
    private static func matchesOne(_ value: NativeStyledSnapshot, identifier: String, choice: NativeStyledChoice,
        body: String, nativeStyleJSON: String?, appLanguage: String, category: String, nominal: Bool) -> Bool {
        let hash = blockHash(identifier)
        guard let block = value.original.blocks.first(where: { $0.blockSHA256 == hash }),
              let report = value.presentations.first(where: { $0.blockSHA256 == hash })?.textPresentation,
              block.sourceSHA256 == semanticHash(body), block.textSHA256 == semanticHash(body),
              block.utf16Length == body.utf16.count, block.nativeMarks.isEmpty, block.renderedMarks.isEmpty,
              report.nativeType == choice.nativeType, report.nativeStylePresent,
              report.contentSizeCategory == category,
              nativeStyleJSON.map({ $0 == report.nativeStyleJSON }) ?? true,
              let bytes = report.nativeStyleJSON.data(using: .utf8),
              let style = try? JSONDecoder().decode(NativeStyledNativeStyle.self, from: bytes),
              style.pinkhaWritingDirection == "rightToLeft", style.pinkhaTextAlignment == "natural",
              style.level == choice.level, style.ordered == choice.ordered,
              style.number == (choice == .numberedList ? 1 : nil),
              style.checked == (choice == .checklist ? false : nil), style.lang == nil else { return false }
        func fontMatches(_ font: NativeStyledFont?) -> Bool {
            guard let font, font.name == choice.fontName, font.bold == (choice.level != nil), !font.italic,
                  font.pointSize.isFinite, font.pointSize > 0 else { return false }
            // The already-qualified large-category baseline equals this original
            // nominal size. Require every expanded run (or the empty field's
            // typing font), not just the first run, to grow past that baseline.
            return nominal ? abs(font.pointSize - choice.nominalSize) < 0.01
                : font.pointSize > choice.nominalSize
        }
        func paragraphMatches(_ paragraph: NativeStyledParagraph?) -> Bool {
            // Original PinkhaWritingDirectionPolicy resolves a natural native
            // alignment to the effective application direction, independently
            // of the explicit RTL writing direction, including empty fields.
            paragraph?.baseWritingDirection == NSWritingDirection.rightToLeft.rawValue &&
            paragraph?.alignment == (appLanguage == "he" ? NSTextAlignment.right : .left).rawValue
        }
        if body.isEmpty {
            return report.fontRuns.isEmpty && fontMatches(report.typingFont) && paragraphMatches(report.typingParagraph)
        }
        var offset = 0
        for run in report.fontRuns {
            guard run.location == offset, run.length > 0, fontMatches(run.font), paragraphMatches(run.paragraph) else { return false }
            offset += run.length
        }
        return offset == body.utf16.count
    }
    private static func sameNativeAndSelection(_ lhs: NativeStyledSnapshot, _ rhs: NativeStyledSnapshot) -> Bool {
        guard lhs.original.pid == rhs.original.pid, lhs.original.spaceSHA256 == rhs.original.spaceSHA256,
              lhs.original.objectSHA256 == rhs.original.objectSHA256,
              lhs.original.nativeVersionSHA256 == rhs.original.nativeVersionSHA256,
              lhs.original.generation == rhs.original.generation,
              lhs.original.blocks.count == rhs.original.blocks.count else { return false }
        return zip(lhs.original.blocks, rhs.original.blocks).allSatisfy { a, b in
            a.blockSHA256 == b.blockSHA256 && a.sourceSHA256 == b.sourceSHA256 && a.textSHA256 == b.textSHA256 &&
            a.selectionLocation == b.selectionLocation && a.selectionLength == b.selectionLength &&
            a.isFirstResponder == b.isFirstResponder
        }
    }
    private static func fontsAreLarger(_ lhs: NativeStyledSnapshot, than rhs: NativeStyledSnapshot) -> Bool {
        zip(lhs.presentations, rhs.presentations).allSatisfy { a, b in
            let current = a.textPresentation.primaryFont, previous = b.textPresentation.primaryFont
            return current?.name == previous?.name && current.map { f in previous.map { f.pointSize > $0.pointSize } ?? false } == true
        }
    }
    private static func fontsEqual(_ lhs: NativeStyledSnapshot, _ rhs: NativeStyledSnapshot) -> Bool {
        zip(lhs.presentations, rhs.presentations).allSatisfy { $0.textPresentation.primaryFont == $1.textPresentation.primaryFont }
    }
}

private enum NativeStyledChoice: String, CaseIterable {
    case paragraph, heading1 = "heading-1", heading2 = "heading-2", heading3 = "heading-3"
    case bulletedList = "bulleted-list", numberedList = "numbered-list", checklist, quote, code
    var nativeType: String {
        switch self {
        case .heading1, .heading2, .heading3: "heading"
        case .bulletedList, .numberedList: "list_item"
        case .checklist: "check_list_item"
        default: rawValue
        }
    }
    var level: Int? { switch self { case .heading1: 1; case .heading2: 2; case .heading3: 3; default: nil } }
    var ordered: Bool? { switch self { case .bulletedList: false; case .numberedList: true; default: nil } }
    // These acceptance expectations are pinned to original DesignKit source,
    // not derived from the new renderer under test.
    var fontName: String { self == .code ? "IBMPlexMono" : level == nil ? "Inter" : "Inter_Bold" }
    var nominalSize: Double { switch self { case .heading1: 28; case .heading2: 22; case .code: 15; default: 17 } }
    var marker: String? {
        switch self { case .bulletedList: "•"; case .numberedList: "1."; case .checklist: "☐"; case .quote: "❝"; default: nil }
    }
    func title(_ language: String) -> String {
        switch self {
        case .paragraph: language == "he" ? "טקסט" : "Text"
        case .heading1: language == "he" ? "כותרת 1" : "Heading 1"
        case .heading2: language == "he" ? "כותרת 2" : "Heading 2"
        case .heading3: language == "he" ? "כותרת 3" : "Heading 3"
        case .bulletedList: language == "he" ? "רשימה עם תבליטים" : "Bulleted list"
        case .numberedList: language == "he" ? "רשימה ממוספרת" : "Numbered list"
        case .checklist: language == "he" ? "רשימת משימות" : "Checklist"
        case .quote: language == "he" ? "ציטוט" : "Quote"
        case .code: language == "he" ? "קוד" : "Code"
        }
    }
}

private struct NativeStyledBlock {
    let choice: NativeStyledChoice
    let identifier: String
    let body: String
    let nativeStyleJSON: String
}
private struct NativeStyledDocument {
    let title: String
    let rowIdentifier: String
    let objectSHA256: String
    var blocks: [NativeStyledBlock]
}
private struct NativeStyledNativeStyle: Decodable {
    let level: Int?
    let ordered: Bool?
    let number: Int?
    let checked: Bool?
    let lang: String?
    let pinkhaWritingDirection: String?
    let pinkhaTextAlignment: String?
}
private struct NativeStyledFont: Codable, Equatable {
    let name: String
    let family: String
    let pointSize: Double
    let bold: Bool
    let italic: Bool
}
private struct NativeStyledParagraph: Codable, Equatable {
    let baseWritingDirection: Int
    let alignment: Int
}
private struct NativeStyledTextPresentation: Decodable {
    struct Run: Decodable { let location: Int; let length: Int; let font: NativeStyledFont?; let paragraph: NativeStyledParagraph? }
    let schema: String
    let nativeType: String
    let nativeStylePresent: Bool
    let nativeStyleJSON: String
    let contentSizeCategory: String
    let fontReadOrigin: String
    let nativeReadOrigin: String
    let assignedUIFontOnly: Bool
    let fontRuns: [Run]
    let typingFont: NativeStyledFont?
    let typingParagraph: NativeStyledParagraph?
    var primaryFont: NativeStyledFont? { fontRuns.first?.font ?? typingFont }
}
private struct NativeStyledSnapshot: Decodable {
    struct Block: Decodable { let blockSHA256: String; let textPresentation: NativeStyledTextPresentation }
    let original: SemanticAnchorUIObservation
    let presentations: [Block]
    private enum CodingKeys: String, CodingKey { case blocks }
    init(from decoder: any Decoder) throws {
        original = try SemanticAnchorUIObservation(from: decoder)
        presentations = try decoder.container(keyedBy: CodingKeys.self).decode([Block].self, forKey: .blocks)
    }
}
private struct NativeStyledReadback { let raw: Data; let value: NativeStyledSnapshot }

/// Private test-runner I/O only. The existing sole controller must retain the
/// request, actual simctl command/readback and response. It must restore the
/// original category in its finally path if XCTest fails before normal restore.
private struct NativeTypographyRendezvous {
    let context: NativeAccessibilityInvocation
    let directory: URL
    init(context: NativeAccessibilityInvocation) throws {
        self.context = context
        let base = try XCTUnwrap(FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first)
        directory = base.appendingPathComponent("PinkhaNativeTypographyAcceptance", isDirectory: true)
            .appendingPathComponent(context.ownedScope.uuidString, isDirectory: true)
        guard !FileManager.default.fileExists(atPath: directory.path) else { throw NativeStyledFailure.staleRendezvous }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true,
                                               attributes: [.posixPermissions: 0o700])
    }
    @MainActor
    func request(_ size: String, phase: String, before: NativeStyledReadback) throws -> [String: Any] {
        guard (phase == "expanded" && size == "accessibility-extra-extra-extra-large") ||
              (phase == "restored" && size == "large") else { throw NativeStyledFailure.invalidContext }
        let requestURL = directory.appendingPathComponent(phase + "-request.json")
        let responseURL = directory.appendingPathComponent(phase + "-response.json")
        guard !FileManager.default.fileExists(atPath: requestURL.path),
              !FileManager.default.fileExists(atPath: responseURL.path) else { throw NativeStyledFailure.staleRendezvous }
        let nonce = UUID().uuidString
        let request: [String: Any] = ["schema": "native-typography-live-request/v1", "phase": phase,
            "requestNonce": nonce, "invocation": context.dictionary, "requestedContentSize": size,
            "runnerProcessID": ProcessInfo.processInfo.processIdentifier,
            "runnerBundleID": Bundle.main.bundleIdentifier ?? "",
            "appPIDFromOriginalObserver": before.value.original.pid,
            "nativeObservationJSON": String(decoding: before.raw, as: UTF8.self),
            "nativeObservationSHA256": Self.hash(before.raw)]
        let raw = try JSONSerialization.data(withJSONObject: request, options: [.sortedKeys])
        guard raw.count <= 65_536 else { throw NativeStyledFailure.rendezvousBounds }
        let temporary = directory.appendingPathComponent(nonce + ".request.tmp")
        try raw.write(to: temporary, options: .withoutOverwriting)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: temporary.path)
        try FileManager.default.moveItem(at: temporary, to: requestURL)
        let ready = NSPredicate { _, _ in FileManager.default.fileExists(atPath: responseURL.path) }
        guard XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: ready, object: NSObject())], timeout: 60) == .completed else {
            throw NativeStyledFailure.controllerDidNotRespond(phase)
        }
        let info = try responseURL.resourceValues(forKeys: [.isSymbolicLinkKey, .fileSizeKey, .isRegularFileKey])
        guard info.isSymbolicLink == false, info.isRegularFile == true,
              let count = info.fileSize, count > 0, count <= 16_384 else { throw NativeStyledFailure.rendezvousBounds }
        let bytes = try Data(contentsOf: responseURL)
        guard let reply = try JSONSerialization.jsonObject(with: bytes) as? [String: String],
              Set(reply.keys) == ["schema", "phase", "requestNonce", "requestSHA256", "simulatorUDID",
                                  "contentSize", "readback", "readbackSHA256", "status"],
              reply["schema"] == "native-typography-live-response/v1", reply["phase"] == phase,
              reply["requestNonce"] == nonce, reply["requestSHA256"] == Self.hash(raw),
              reply["simulatorUDID"] == context.dictionary["simulatorUDID"], reply["contentSize"] == size,
              reply["status"] == "APPLIED_AND_READ_BACK", let readback = reply["readback"],
              readback.trimmingCharacters(in: .whitespacesAndNewlines) == size,
              reply["readbackSHA256"] == Self.hash(Data(readback.utf8)) else { throw NativeStyledFailure.invalidControllerResponse }
        // The response is a coordination receipt only. The test still requires
        // actual mounted UIKit category/font changes in the original App PID.
        return ["requestSHA256": Self.hash(raw), "responseSHA256": Self.hash(bytes), "response": reply]
    }
    private static func hash(_ raw: Data) -> String {
        SHA256.hash(data: raw).map { String(format: "%02x", $0) }.joined()
    }
}

private enum NativeStyledFailure: Error {
    case invalidContext, missingBlockIdentity, missingObjectIdentity, observation(String)
    case staleRendezvous, rendezvousBounds, controllerDidNotRespond(String), invalidControllerResponse
}
// END_NATIVE_STYLED_BLOCK_ACCEPTANCE_FUTURE_V1

// BEGIN_NATIVE_UNICODE_ANCHOR_REGRESSION_V1
extension NativeLaunchTests {
    /// Ordinary UIKit typing must not discard a raw NFC-to-NFD change as a
    /// canonically equal no-op. This does not exercise marked-input IME.
    func testCanonicallyEquivalentLatinTypingPreservesNativeAnchorAndColdReopen() throws {
        executionTimeAllowance = 1_800
        try assertUnicodeAnchorTypingAndColdReopen(
            caseID: "latin-nfc-nfd", beforeBody: "\u{00e9}", afterBody: "e\u{0301}")
    }

    /// Hebrew combining marks can change exact stored bytes without changing
    /// canonical String equality or the UTF-16 length.
    func testCanonicallyEquivalentHebrewTypingPreservesNativeAnchorAndColdReopen() throws {
        executionTimeAllowance = 1_800
        try assertUnicodeAnchorTypingAndColdReopen(
            caseID: "hebrew-mark-order", beforeBody: "\u{05e9}\u{05b8}\u{05c1}",
            afterBody: "\u{05e9}\u{05c1}\u{05b8}")
    }

    private func assertUnicodeAnchorTypingAndColdReopen(
        caseID: String, beforeBody: String, afterBody: String
    ) throws {
        let prefix = "Before ", suffix = " after"
        let before = prefix + beforeBody + suffix, after = prefix + afterBody + suffix
        XCTAssertFalse(before.utf8.elementsEqual(after.utf8))
        XCTAssertTrue(before.precomposedStringWithCanonicalMapping.utf8.elementsEqual(
            after.precomposedStringWithCanonicalMapping.utf8))
        let scope = UUID(), nameSuffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        app.launchEnvironment["PINKHA_NATIVE_ANCHOR_OBSERVATION"] = "1"
        let spaceName = "Unicode Anchor Space " + nameSuffix
        let documentName = "Unicode Anchor Document " + nameSuffix
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        try createNamedItemWithObservedTransition(app, action: "any-native-new-document", title: documentName)
        let addParagraph = app.buttons["any-native-add-paragraph"]
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: addParagraph, timeout: 60)
        addParagraph.tap()
        let editors = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        let editor = editors.firstMatch
        waitForNativeEditorInput(app, editor)
        editor.tap(); editor.typeText(before)
        semanticCommit(app, editor: editor, text: before)
        let blockIdentifier = editor.identifier
        XCTAssertEqual(editors.count, 1)
        let initial = try semanticObservation(app, phase: caseID + "-before") {
            $0.nativeMarkCount == 0 && $0.blocks.count == 1 &&
            $0.blocks[0].textSHA256 == Self.semanticHash(before) &&
            $0.blocks[0].utf16Length == before.utf16.count
        }

        // The guard text belongs to this one selected anchor. Both guards must
        // retain their exact bytes when the canonically equivalent body changes.
        // This full-range regression does not claim partial-range acceptance.
        try semanticSelectAll(app, editor: editor, length: before.utf16.count)
        tapWhenEnabled(app.buttons["pinkha.semanticAnchor.capture"])
        let confirmation = app.alerts.firstMatch
        waitUntilEnabled(confirmation)
        XCTAssertEqual(app.alerts.count, 1)
        tapWhenEnabled(confirmation.buttons.matching(NSPredicate(
            format: "label IN %@", ["Create text anchor", "יצירת עוגן טקסט"])).firstMatch)
        waitUntilEnabled(app.alerts.staticTexts.matching(NSPredicate(format: "label IN %@", [
            "The selected text now has an anchor.", "נוסף עוגן לטקסט שנבחר."
        ])).firstMatch, timeout: 60)
        tapWhenEnabled(app.alerts.buttons.matching(NSPredicate(
            format: "label IN %@", ["Done", "סיום"])).firstMatch)
        waitFor(NSPredicate(format: "exists == false"), object: app.alerts.firstMatch, timeout: 15)
        let captured = try semanticObservation(app, phase: caseID + "-captured") {
            $0.nativeMarkCount == 1 && $0.blocks.count == 1 &&
            $0.blocks[0].textSHA256 == Self.semanticHash(before) &&
            $0.blocks[0].utf16Length == before.utf16.count &&
            $0.blocks[0].nativeMarks.count == 1 &&
            $0.blocks[0].nativeMarks[0].location == 0 &&
            $0.blocks[0].nativeMarks[0].length == before.utf16.count &&
            $0.blocks[0].nativeMarks[0].textSHA256 == Self.semanticHash(before)
        }
        let mark = try XCTUnwrap(captured.blocks.first?.nativeMarks.first)
        XCTAssertEqual(captured.blocks[0].nativeMarks, captured.blocks[0].renderedMarks)
        XCTAssertNotEqual(captured.nativeVersionSHA256, initial.nativeVersionSHA256)
        XCTAssertEqual(captured.blocks[0].blockSHA256, initial.blocks[0].blockSHA256)
        try attachExactUnicodeAnchorValue(app, editor: editor, phase: caseID + "-captured",
            expected: before, prefix: prefix, suffix: suffix)

        // Use the original actual UIKit selection witness and keyboard path.
        // A visible value alone is not an acknowledgement: the following
        // observer refuses pending drafts and compares the native read to the
        // rendered text using exact semantic-text bytes.
        try semanticSelectAll(app, editor: editor, length: before.utf16.count)
        editor.typeText(after)
        semanticCommit(app, editor: editor, text: after)
        let edited = try semanticObservation(app, phase: caseID + "-edited-native") {
            $0.nativeMarkCount == 1 && $0.blocks.count == 1 &&
            $0.blocks[0].textSHA256 == Self.semanticHash(after) &&
            $0.blocks[0].utf16Length == after.utf16.count &&
            $0.blocks[0].nativeMarks.count == 1 &&
            $0.blocks[0].nativeMarks[0].identitySHA256 == mark.identitySHA256 &&
            $0.blocks[0].nativeMarks[0].location == 0 &&
            $0.blocks[0].nativeMarks[0].length == after.utf16.count &&
            $0.blocks[0].nativeMarks[0].textSHA256 == Self.semanticHash(after)
        }
        XCTAssertNotEqual(edited.nativeVersionSHA256, captured.nativeVersionSHA256)
        XCTAssertNotEqual(edited.blocks[0].sourceSHA256, captured.blocks[0].sourceSHA256)
        XCTAssertEqual(edited.blocks[0].blockSHA256, captured.blocks[0].blockSHA256)
        XCTAssertEqual(edited.spaceSHA256, captured.spaceSHA256)
        XCTAssertEqual(edited.objectSHA256, captured.objectSHA256)
        XCTAssertEqual(edited.blocks[0].nativeMarks, edited.blocks[0].renderedMarks)
        XCTAssertEqual(Array(editor.identifier.utf8), Array(blockIdentifier.utf8))
        try attachExactUnicodeAnchorValue(app, editor: editor, phase: caseID + "-edited-native",
            expected: after, prefix: prefix, suffix: suffix)

        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentName].firstMatch, timeout: 60)
        waitForNativeEditorInput(app, editor)
        let reopened = try semanticObservation(app, phase: caseID + "-cold-native") {
            $0.nativeMarkCount == 1 && $0.blocks.count == 1 &&
            $0.blocks[0].textSHA256 == Self.semanticHash(after) &&
            $0.blocks[0].utf16Length == after.utf16.count &&
            $0.blocks[0].nativeMarks.count == 1 &&
            $0.blocks[0].nativeMarks[0].identitySHA256 == mark.identitySHA256 &&
            $0.blocks[0].nativeMarks[0].location == 0 &&
            $0.blocks[0].nativeMarks[0].length == after.utf16.count &&
            $0.blocks[0].nativeMarks[0].textSHA256 == Self.semanticHash(after)
        }
        XCTAssertNotEqual(reopened.pid, edited.pid)
        XCTAssertNotEqual(reopened.generation, edited.generation)
        XCTAssertEqual(reopened.spaceSHA256, initial.spaceSHA256)
        XCTAssertEqual(reopened.objectSHA256, initial.objectSHA256)
        XCTAssertEqual(reopened.blocks[0].blockSHA256, initial.blocks[0].blockSHA256)
        XCTAssertEqual(reopened.blocks[0].sourceSHA256, edited.blocks[0].sourceSHA256)
        XCTAssertEqual(reopened.blocks[0].nativeMarks, edited.blocks[0].nativeMarks)
        XCTAssertEqual(reopened.blocks[0].nativeMarks, reopened.blocks[0].renderedMarks)
        XCTAssertEqual(Array(editor.identifier.utf8), Array(blockIdentifier.utf8))
        XCTAssertEqual(editors.count, 1)
        try attachExactUnicodeAnchorValue(app, editor: editor, phase: caseID + "-cold-native",
            expected: after, prefix: prefix, suffix: suffix)
    }

    private func attachExactUnicodeAnchorValue(
        _ app: XCUIApplication, editor: XCUIElement, phase: String,
        expected: String, prefix: String, suffix: String
    ) throws {
        try requireArchiveObservationPastOnboarding(app)
        let actual = try XCTUnwrap(editor.value as? String)
        let actualBytes = Array(actual.utf8), expectedBytes = Array(expected.utf8)
        let evidence: [String: Any] = [
            "schema": "native-unicode-anchor-exact-ui/v1", "phase": phase,
            "expectedUTF8": expectedBytes, "actualUTF8": actualBytes,
            "expectedUTF16": Array(expected.utf16), "actualUTF16": Array(actual.utf16),
            "prefixUTF8": Array(prefix.utf8), "suffixUTF8": Array(suffix.utf8),
            "blockIdentifierSHA256": Self.semanticHash(editor.identifier),
            "observationOrigin": "actual-XCUIElement-value-after-original-native-observation",
            "inputPath": "ordinary-UIKit-typing", "markedInputIMEVerified": false
        ]
        let data = try JSONSerialization.data(withJSONObject: evidence, options: [.sortedKeys])
        let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
        attachment.name = "native-unicode-anchor-" + phase
        attachment.lifetime = .keepAlways; add(attachment)
        let screen = XCTAttachment(screenshot: app.screenshot())
        screen.name = "native-unicode-anchor-" + phase + "-screen"
        screen.lifetime = .keepAlways; add(screen)
        XCTAssertEqual(actualBytes, expectedBytes)
        XCTAssertEqual(Array(actual.utf16), Array(expected.utf16))
        XCTAssertEqual(Array(actualBytes.prefix(prefix.utf8.count)), Array(prefix.utf8))
        XCTAssertEqual(Array(actualBytes.suffix(suffix.utf8.count)), Array(suffix.utf8))
    }
}
// END_NATIVE_UNICODE_ANCHOR_REGRESSION_V1
