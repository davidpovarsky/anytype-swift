import XCTest
import Foundation
import CryptoKit

/// Mounted production history, using only the normal account/document/editor UI.
/// No native fixture endpoint, history mutation, or replacement data source is used.
@MainActor
final class NativeHistoryTests: XCTestCase {
    private let versionPrefix = "any-native-history-version-"

    override func setUpWithError() throws { continueAfterFailure = false }

    func testSavedHebrewVersionsRemainReadOnlyAcrossCloseBackgroundAndColdReopen() throws {
        executionTimeAllowance = 1_800
        let scope = UUID(), suffix = String(UUID().uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "History Space " + suffix
        let documentName = "History Document " + suffix
        let firstText = "שלום 731", secondText = "שלום 864"
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createDocument(app, title: documentName)

        let addParagraph = app.buttons["any-native-add-paragraph"]
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                object: addParagraph, timeout: 60)
        addParagraph.tap()
        let blocks = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-block-"))
        let editor = blocks.firstMatch
        waitUntilEnabled(editor, timeout: 45)
        editor.tap(); editor.typeText(firstText)
        commitAndRequireText(app, editor: editor, text: firstText)
        XCTAssertEqual(blocks.count, 1)
        let blockIdentifier = editor.identifier

        // The first handle is learned from a real saved preview before the
        // second edit exists. A timestamp is never used as its identity/order.
        let first = try findSavedText(app, text: firstText, phase: "first-committed-version")
        closeHistory(app)
        XCTAssertEqual(editor.value as? String, firstText)
        XCTAssertEqual(editor.identifier, blockIdentifier)

        editor.tap(); editor.press(forDuration: 1.2)
        let selectAll = app.descendants(matching: .any).matching(NSPredicate(
            format: "label IN %@", ["Select All", "בחר הכל", "בחר הכול", "בחירת הכול"])).firstMatch
        tapWhenEnabled(selectAll)
        editor.typeText(secondText)
        commitAndRequireText(app, editor: editor, text: secondText)
        XCTAssertEqual(blocks.count, 1)
        XCTAssertEqual(editor.identifier, blockIdentifier)

        let second = try findSavedText(app, text: secondText, phase: "second-committed-version")
        XCTAssertNotEqual(first.version, second.version)
        closeHistory(app)
        XCTAssertEqual(editor.value as? String, secondText)

        // Our writes now remain frozen. Extra native metadata records may
        // legitimately appear, so compare only the two observed causal handles.
        openHistory(app)
        let committedOrder = try observeRelevantOrder(app, first: first.version, second: second.version)
        closeHistory(app)
        try openVersion(app, version: first.version, expectedText: firstText, phase: "old-preview-live-editor-unchanged")
        closeHistory(app)
        XCTAssertEqual(editor.value as? String, secondText)
        XCTAssertEqual(blocks.count, 1)
        XCTAssertEqual(editor.identifier, blockIdentifier)

        try openVersion(app, version: second.version, expectedText: secondText, phase: "before-background")
        XCUIDevice.shared.press(.home)
        XCTAssertTrue(app.wait(for: .runningBackground, timeout: 10))
        app.activate()
        let preview = app.descendants(matching: .any)
            .matching(identifier: "any-native-history-preview").firstMatch
        waitFor(NSPredicate(format: "exists == false"), object: preview.staticTexts[secondText], timeout: 60)
        // The app can retire the entire document owner on background. If the
        // old sheet remains mounted, its revoked presentation must be closed.
        if app.buttons["any-native-history-close"].exists { closeHistory(app) }
        waitFor(NSPredicate(format: "exists == true AND value == %@", secondText), object: editor, timeout: 60)
        try openVersion(app, version: second.version, expectedText: secondText, phase: "fresh-owner-after-background")
        closeHistory(app)
        XCTAssertEqual(editor.value as? String, secondText)

        app.terminate(); app.launch()
        tapWhenEnabled(app.buttons["any-native-saved-account"].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons[spaceName].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons[documentName].firstMatch, timeout: 60)
        waitFor(NSPredicate(format: "exists == true AND value == %@", secondText), object: editor, timeout: 60)
        XCTAssertEqual(editor.identifier, blockIdentifier)
        XCTAssertEqual(blocks.count, 1)
        openHistory(app)
        let reopenedOrder = try observeRelevantOrder(app, first: first.version, second: second.version)
        closeHistory(app)
        try openVersion(app, version: first.version, expectedText: firstText, phase: "cold-reopen-first-version")
        closeHistory(app)
        try openVersion(app, version: second.version, expectedText: secondText, phase: "cold-reopen-second-version")
        closeHistory(app)
        XCTAssertEqual(editor.value as? String, secondText)
        XCTAssertEqual(blocks.count, 1)
        XCTAssertTrue(app.buttons["any-native-document-sources"].exists)
        XCTAssertTrue(app.buttons["any-native-document-properties"].exists)
        XCTAssertTrue(app.buttons["any-native-hanlin"].exists)

        try attachJSON([
            "schema": 1,
            "method": "NativeHistoryTests/testSavedHebrewVersionsRemainReadOnlyAcrossCloseBackgroundAndColdReopen",
            "scope": scope.uuidString,
            "firstVersion": first.version, "secondVersion": second.version,
            "firstObservedRows": first.observedRows, "secondObservedRows": second.observedRows,
            "committedObservedRows": committedOrder, "coldReopenObservedRows": reopenedOrder,
            "firstTextSHA256": digest(firstText), "secondTextSHA256": digest(secondText),
            "liveBlockIdentifier": blockIdentifier,
            "liveEditorTextUnchangedAfterOldPreview": true,
            "revokedPreviewClearedAfterBackground": true,
            "savedVersionIdentityAndTextSurvivedColdReopen": true,
            "nativeCurrentReaderACLTransition": "NOT_RUN",
            "nativePaginationAndErrorResponses": "NOT_RUN",
            "nativeUnknownDatasetOrBlockFixture": "NOT_RUN",
            "historyWireTrafficCapture": "NOT_RUN",
            "physicalDevice": "NOT_RUN",
            "wholeAppParity": "NOT_PROVEN"
        ], name: "native-history-mounted-receipt")
    }

    private struct LocatedVersion {
        let version: String
        let observedRows: [String]
    }

    private func findSavedText(_ app: XCUIApplication, text: String, phase: String) throws -> LocatedVersion {
        openHistory(app)
        let identifiers = observedVersionIDs(app)
        guard !identifiers.isEmpty else { throw HistoryFailure.noVersions }
        // A fresh one-paragraph document needs only a bounded first-page scan.
        // This method deliberately does not claim native pagination acceptance.
        for version in identifiers.prefix(16) {
            revealVersion(app, version: version)
            tapWhenEnabled(app.buttons[versionPrefix + version])
            let preview = app.descendants(matching: .any)
                .matching(identifier: "any-native-history-preview").firstMatch
            waitUntilEnabled(preview)
            let loaded = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true"),
                                                    object: preview.staticTexts[text])
            _ = XCTWaiter.wait(for: [loaded], timeout: 20)
            if preview.staticTexts[text].exists {
                try attachJSON(["phase": phase, "version": version, "text": text,
                                "observedRows": identifiers], name: "native-history-" + phase)
                return .init(version: version, observedRows: identifiers)
            }
            closeHistory(app); openHistory(app)
        }
        throw HistoryFailure.savedTextNotFound
    }

    private func openVersion(_ app: XCUIApplication, version: String, expectedText: String, phase: String) throws {
        openHistory(app)
        revealVersion(app, version: version)
        tapWhenEnabled(app.buttons[versionPrefix + version])
        let preview = app.descendants(matching: .any)
            .matching(identifier: "any-native-history-preview").firstMatch
        waitFor(NSPredicate(format: "exists == true"), object: preview.staticTexts[expectedText], timeout: 45)
        XCTAssertFalse(app.descendants(matching: .any)
            .matching(identifier: "any-native-history-version-problem").firstMatch.exists)
        try attachJSON(["phase": phase, "version": version, "text": expectedText],
                       name: "native-history-" + phase)
    }

    private func observeRelevantOrder(_ app: XCUIApplication, first: String, second: String) throws -> [String] {
        var observed = observedVersionIDs(app)
        let list = app.descendants(matching: .any).matching(identifier: "any-native-history-list").firstMatch
        for _ in 0..<8 {
            if observed.contains(first) && observed.contains(second) { break }
            list.swipeUp()
            for id in observedVersionIDs(app) where !observed.contains(id) { observed.append(id) }
        }
        guard let earlier = observed.firstIndex(of: first), let later = observed.firstIndex(of: second) else {
            throw HistoryFailure.relevantVersionNotVisible
        }
        XCTAssertLessThan(later, earlier, "The later causal cut must precede the earlier cut in native newest-first order.")
        return observed
    }

    private func observedVersionIDs(_ app: XCUIApplication) -> [String] {
        var result: [String] = []
        for row in app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", versionPrefix)).allElementsBoundByIndex {
            let id = String(row.identifier.dropFirst(versionPrefix.count))
            if !id.isEmpty && !result.contains(id) { result.append(id) }
        }
        return result
    }

    private func revealVersion(_ app: XCUIApplication, version: String) {
        let row = app.buttons[versionPrefix + version]
        let list = app.descendants(matching: .any).matching(identifier: "any-native-history-list").firstMatch
        for _ in 0..<8 {
            if row.exists && row.isHittable { break }
            list.swipeUp()
        }
        waitFor(NSPredicate(format: "exists == true AND enabled == true AND hittable == true"), object: row, timeout: 10)
    }

    private func openHistory(_ app: XCUIApplication) {
        tapWhenEnabled(app.buttons["any-native-document-options"])
        tapWhenEnabled(app.buttons["any-native-document-history"])
        let rows = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", versionPrefix))
        waitFor(NSPredicate(format: "exists == true"), object: rows.firstMatch, timeout: 45)
        XCTAssertFalse(app.descendants(matching: .any)
            .matching(identifier: "any-native-history-problem").firstMatch.exists)
    }

    private func closeHistory(_ app: XCUIApplication) {
        tapWhenEnabled(app.buttons["any-native-history-close"])
        waitFor(NSPredicate(format: "exists == false"), object: app.buttons["any-native-history-close"], timeout: 20)
    }

    private func commitAndRequireText(_ app: XCUIApplication, editor: XCUIElement, text: String) {
        tapWhenEnabled(app.buttons["any-native-editor-done"])
        let status = app.descendants(matching: .any).matching(identifier: "any-native-save-status").firstMatch
        waitFor(NSPredicate(format: "exists == true AND value == %@", "saved"), object: status, timeout: 45)
        XCTAssertEqual(editor.value as? String, text)
    }

    private func createOwnedWorkspace(_ app: XCUIApplication, spaceName: String) {
        tapWhenEnabled(app.buttons["any-native-account-create"])
        let acknowledgement = app.switches["any-native-backup-acknowledged"]
        waitUntilEnabled(acknowledgement, timeout: 60)
        let controls = acknowledgement.descendants(matching: .switch)
        let control = controls.firstMatch
        waitUntilEnabled(control)
        XCTAssertEqual(controls.count, 1)
        waitFor(NSPredicate(format: "hittable == true AND value == %@", "0"), object: control, timeout: 10)
        control.tap()
        waitFor(NSPredicate(format: "value == %@", "1"), object: acknowledgement, timeout: 10)
        // Never inspect or attach the account recovery phrase.
        tapWhenEnabled(app.buttons["any-native-backup-continue"])
        let name = app.textFields["any-native-space-name"]
        waitUntilEnabled(name); name.tap(); name.typeText(spaceName)
        tapWhenEnabled(app.buttons["any-native-space-create"])
        tapWhenEnabled(app.buttons["any-native-workspace-setup"], timeout: 90)
    }

    private func createDocument(_ app: XCUIApplication, title: String) {
        tapWhenEnabled(app.buttons["any-native-create-menu"], timeout: 60)
        tapWhenEnabled(app.buttons["any-native-new-document"])
        let field = app.descendants(matching: .any).matching(identifier: "any-native-name-input").firstMatch
        waitUntilEnabled(field); field.tap(); field.typeText(title)
        tapWhenEnabled(app.buttons["any-native-name-confirm"])
    }

    private func makeApplication(scope: UUID) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["--native-ui-tests", "--native-ui-test-scope", scope.uuidString,
                               "-AppleLanguages", "(he,en)", "-AppleLocale", "he_IL"]
        return app
    }

    private func tapWhenEnabled(_ element: XCUIElement, timeout: TimeInterval = 30,
                                file: StaticString = #filePath, line: UInt = #line) {
        waitUntilEnabled(element, timeout: timeout, file: file, line: line); element.tap()
    }

    private func waitUntilEnabled(_ element: XCUIElement, timeout: TimeInterval = 30,
                                  file: StaticString = #filePath, line: UInt = #line) {
        waitFor(NSPredicate(format: "exists == true AND enabled == true"), object: element,
                timeout: timeout, file: file, line: line)
    }

    private func waitFor(_ predicate: NSPredicate, object: Any, timeout: TimeInterval,
                         file: StaticString = #filePath, line: UInt = #line) {
        let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: predicate, object: object)], timeout: timeout)
        XCTAssertEqual(result, .completed, "Expected native history UI state was not reached", file: file, line: line)
    }

    private func digest(_ text: String) -> String {
        SHA256.hash(data: Data(text.utf8)).map { String(format: "%02x", $0) }.joined()
    }

    private func attachJSON(_ value: [String: Any], name: String) throws {
        let attachment = XCTAttachment(data: try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]),
                                       uniformTypeIdentifier: "public.json")
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }

    private enum HistoryFailure: Error {
        case noVersions, savedTextNotFound, relevantVersionNotVisible
    }
}
