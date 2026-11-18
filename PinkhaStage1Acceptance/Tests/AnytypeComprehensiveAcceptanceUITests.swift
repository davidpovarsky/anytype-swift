import XCTest

/// Real-app UI checks. The runner must supply a freshly provisioned native fixture.
@MainActor
final class AnytypeComprehensiveAcceptanceUITests: XCTestCase {
    private struct Fixture: Decodable {
        let spaceId: String
        let universalDocuments: [String: String]
        let manySourcesDocument: String
    }

    private static var readyPID: Int?
    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private var fixture: Fixture!

    override func setUpWithError() throws {
        continueAfterFailure = false
        let env = ProcessInfo.processInfo.environment
        guard env["PINKHA_NATIVE_UI_DISPOSABLE"] == "1" else {
            throw NSError(domain: "DisposableNativeFixtureRequired", code: 1)
        }
        let json = try XCTUnwrap(env["PINKHA_NATIVE_UI_FIXTURE_JSON"])
        fixture = try JSONDecoder().decode(Fixture.self, from: Data(json.utf8))
        XCTAssertFalse(fixture.spaceId.isEmpty)
        XCTAssertFalse(try XCTUnwrap(fixture.universalDocuments["page"]).isEmpty)
    }

    func testObjectAddPropertyButtonAndPickerSearch() throws {
        defer { attachFinalEvidence() }
        try recordEntryEvidence()
        try openPageProperties()
        let add = app.buttons["torah-object-add-property"]
        XCTAssertTrue(add.waitForExistence(timeout: 20))
        XCTAssertTrue(add.isHittable)
        XCTAssertFalse(add.label.isEmpty)
        attach("object-properties-add-button-visual-review")
        add.tap()
        let search = app.textFields.firstMatch
        XCTAssertTrue(search.waitForExistence(timeout: 20))
        XCTAssertTrue(search.isHittable)
        attach("object-add-property-empty-search")
        search.tap()
        search.typeText("מקור")
        let source = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", "מקור/ות")).firstMatch
        XCTAssertTrue(source.waitForExistence(timeout: 30), "Native source property should be discoverable by Hebrew search")
        attach("object-add-property-hebrew-search")
    }

    func testDocumentSourceSearchPresentation() throws {
        defer { attachFinalEvidence() }
        try recordEntryEvidence()
        try openDocument(fixture.manySourcesDocument)
        let add = app.buttons["torah-document-sources-add"]
        XCTAssertTrue(add.waitForExistence(timeout: 20), "Fixture must have Sources attached")
        XCTAssertTrue(add.isHittable)
        add.tap()
        let search = app.textFields.matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@", "torah-sources-search-field", "torah-sources-search-sheet"
        )).firstMatch
        XCTAssertTrue(search.waitForExistence(timeout: 20))
        XCTAssertTrue(app.staticTexts["Document links"].waitForExistence(timeout: 20))
        attach("document-sources-sheet-visual-review")
    }

    func testDocumentSourceSearchEmptyAndClear() throws {
        defer { attachFinalEvidence() }
        try recordEntryEvidence()
        try openDocument(fixture.manySourcesDocument)
        let add = app.buttons["torah-document-sources-add"]
        XCTAssertTrue(add.waitForExistence(timeout: 20))
        add.tap()
        let search = app.textFields.matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@", "torah-sources-search-field", "torah-sources-search-sheet"
        )).firstMatch
        XCTAssertTrue(search.waitForExistence(timeout: 20))
        search.tap()
        let previous = (search.value as? String) ?? ""
        if !previous.isEmpty && previous != search.placeholderValue {
            search.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: previous.utf16.count))
        }
        let noMatch = "zzqvnonexistent123456789"
        search.typeText(noMatch)
        let empty = app.descendants(matching: .any).matching(identifier: "torah-search-empty").firstMatch
        XCTAssertTrue(empty.waitForExistence(timeout: 45), "A real no-match search should expose its empty state")
        attach("document-sources-empty-search")
        search.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: noMatch.utf16.count))
        XCTAssertTrue(empty.waitForNonExistence(timeout: 20), "Clearing the search should leave the empty-result state")
        attach("document-sources-search-cleared")
    }
    func testSourceChipOpensAndClosesInspector() throws {
        defer { attachFinalEvidence() }
        try recordEntryEvidence()
        try openDocument(fixture.manySourcesDocument)
        let chip = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-document-source-chip-"
        )).firstMatch
        XCTAssertTrue(chip.waitForExistence(timeout: 30))
        XCTAssertTrue(chip.isHittable)
        chip.tap()
        let inspector = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-inspector-sheet-"
        )).firstMatch
        XCTAssertTrue(inspector.waitForExistence(timeout: 30), "Source chip must open the original Inspector")
        attach("source-chip-inspector-open")
        let close = app.buttons.matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@", "torah-inspector-close", "torah-inspector-peek-close"
        )).firstMatch
        XCTAssertTrue(close.waitForExistence(timeout: 20))
        XCTAssertTrue(close.isHittable)
        close.tap()
        XCTAssertTrue(inspector.waitForNonExistence(timeout: 20))
        XCTAssertTrue(more.waitForExistence(timeout: 20), "Closing Inspector should return to the document")
        attach("source-chip-inspector-closed")
    }
    func testInspectorShowsIndexedRelatedDocument() throws {
        defer { attachFinalEvidence() }
        try recordEntryEvidence()
        try openDocument(fixture.manySourcesDocument)
        let chip = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-document-source-chip-"
        )).firstMatch
        XCTAssertTrue(chip.waitForExistence(timeout: 30))
        chip.tap()
        let expand = app.buttons["torah-inspector-expand-medium"]
        if expand.waitForExistence(timeout: 10) { expand.tap() }
        let showTools = app.buttons["torah-inspector-show-tools"]
        if showTools.exists && showTools.isHittable { showTools.tap() }
        let documents = app.buttons["In Documents"].firstMatch
        XCTAssertTrue(documents.waitForExistence(timeout: 30), "The existing Inspector must expose its document tool")
        documents.tap()
        let add = app.buttons["torah-inspector-related-add-note"]
        XCTAssertTrue(add.waitForExistence(timeout: 30), "Document tool must expose the real Note action")
        let linkedDocument = app.buttons["UI27 source document"].firstMatch
        XCTAssertTrue(linkedDocument.waitForExistence(timeout: 45), "The canonical document source should appear in the current Space")
        XCTAssertTrue(linkedDocument.isHittable)
        attach("inspector-indexed-document-results")
    }
    private func recordEntryEvidence() throws {
        let hierarchy = app.debugDescription
        attachHierarchy(hierarchy, name: "entry-hierarchy")
        XCTAssertEqual(app.state, .runningForeground, "Runner must prelaunch the actual app in the foreground")
        guard let expected = ProcessInfo.processInfo.environment["PINKHA_UI27_EXPECTED_APP_PID"] else { return }
        let expectedPID = try XCTUnwrap(Int(expected), "Expected app PID must be a positive integer")
        XCTAssertGreaterThan(expectedPID, 0)
        let expression = try NSRegularExpression(pattern: "\\A\\s*(?:Attributes:\\s*)?Application,\\s*0x[0-9a-fA-F]+,\\s*pid:\\s*([0-9]+)")
        let range = NSRange(hierarchy.startIndex..., in: hierarchy)
        let match = try XCTUnwrap(expression.firstMatch(in: hierarchy, range: range), "Target application PID missing from hierarchy")
        let pidRange = try XCTUnwrap(Range(match.range(at: 1), in: hierarchy))
        XCTAssertEqual(Int(hierarchy[pidRange]), expectedPID, "Target app PID must match the runner's verified process")
    }

    private func attachHierarchy(_ description: String, name: String) {
        let hierarchy = XCTAttachment(string: description)
        hierarchy.name = name
        hierarchy.lifetime = .keepAlways
        add(hierarchy)
    }

    private func attachFinalEvidence() {
        let finalHierarchy = app.debugDescription
        attachHierarchy(finalHierarchy, name: "final-hierarchy")
        if let expected = ProcessInfo.processInfo.environment["PINKHA_UI27_EXPECTED_APP_PID"] {
            let expression = try? NSRegularExpression(pattern: "\\A\\s*(?:Attributes:\\s*)?Application,\\s*0x[0-9a-fA-F]+,\\s*pid:\\s*([0-9]+)")
            let range = NSRange(finalHierarchy.startIndex..., in: finalHierarchy)
            let match = expression?.firstMatch(in: finalHierarchy, range: range)
            let pidRange = match.flatMap { Range($0.range(at: 1), in: finalHierarchy) }
            let actual = pidRange.flatMap { Int(finalHierarchy[$0]) }
            XCTAssertEqual(actual, Int(expected), "Final target app PID must match the runner's verified process")
            XCTAssertNotNil(actual, "Final target application PID missing from hierarchy")
        }
        guard app.state == .runningForeground else { return }
        attach("final-screen")
    }

    private func openPage() throws {
        try openDocument(try XCTUnwrap(fixture.universalDocuments["page"]))
    }

    private func openDocument(_ objectID: String) throws {
        XCTAssertEqual(app.state, .runningForeground, "Runner must prelaunch the actual app in the foreground")
        // Wait for a source-backed home control, or an already-open editor from a
        // preceding smoke method. A foreground LaunchView alone is not readiness.
        let home = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ OR label == %@ OR identifier == %@ OR label == %@",
            "SpaceHub", "SpaceHub", "NewSpaceButton", "NewSpaceButton"
        )).firstMatch
        let expectedPID = ProcessInfo.processInfo.environment["PINKHA_UI27_EXPECTED_APP_PID"].flatMap(Int.init)
        if expectedPID == nil || Self.readyPID != expectedPID {
            let waitStart = ProcessInfo.processInfo.systemUptime
            let startedAt = Date()
            defer {
                let formatter = ISO8601DateFormatter()
                let details = "expectedAppPID=\(expectedPID.map { String($0) } ?? "not-supplied"); waitStartedUTC=\(formatter.string(from: startedAt)); waitEndedUTC=\(formatter.string(from: Date())); elapsedSeconds=\(ProcessInfo.processInfo.systemUptime - waitStart); homeObserved=\(home.exists); editorMoreObserved=\(more.exists)"
                let attachment = XCTAttachment(string: details)
                attachment.name = "startup-readiness-timing"
                attachment.lifetime = .keepAlways
                add(attachment)
            }
            if !more.exists {
                guard home.waitForExistence(timeout: 120) else {
                    // Throw so Swift unwinds both timing and final-evidence defers.
                    // XCTest still records the missing readiness as a failed test.
                    throw NSError(domain: "UI27Readiness", code: 1, userInfo: [
                        NSLocalizedDescriptionKey: "Restored home did not become ready before the deep link"
                    ])
                }
            }
            Self.readyPID = expectedPID
        }
        var url = URLComponents()
        url.scheme = "anytype"
        url.host = "object"
        url.queryItems = [
            URLQueryItem(name: "objectId", value: objectID),
            URLQueryItem(name: "spaceId", value: fixture.spaceId)
        ]
        // Route through the OS without entering XCUIApplication's launch handshake.
        // The runner already launched and verified this app process; assertions below
        // still require its exact disposable Space, object, title, and hittable editor.
        XCUIDevice.shared.system.open(try XCTUnwrap(url.url))
        XCTAssertTrue(more.waitForExistence(timeout: 45), "Disposable document did not open")
        let editorIdentity = "pinkha-ui27-editor:\(fixture.spaceId):\(objectID)"
        let editor = app.descendants(matching: .any).matching(NSPredicate(format: "identifier == %@", editorIdentity)).firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 45),
                      "The mounted editor must match the requested disposable Space and object")
        XCTAssertEqual(app.descendants(matching: .any).matching(NSPredicate(format: "identifier == %@", editorIdentity)).count, 1,
                       "Exactly one mounted editor must match the disposable Space and object")
        XCTAssertTrue(editor.isHittable, "The expected editor identity must be visible and current")
        XCTAssertTrue(more.isHittable, "Document controls must not be blocked by a previous sheet")
        let title = objectID == fixture.manySourcesDocument ? "UI27 source document" : "UI27 blank Page"
        let actualTitle = app.descendants(matching: .any).matching(NSPredicate(
            format: "label == %@ OR value == %@", title, title
        )).firstMatch
        XCTAssertTrue(actualTitle.waitForExistence(timeout: 45), "Expected disposable document title was not visible")
    }

    private func openPageProperties() throws {
        try openPage()
        more.tap()
        let properties = app.buttons["Properties"].firstMatch
        XCTAssertTrue(properties.waitForExistence(timeout: 20))
        properties.tap()
    }

    private var more: XCUIElement {
        app.buttons.matching(NSPredicate(format: "label == %@ OR label == %@", "More", "x24/More")).firstMatch
    }

    private func attach(_ name: String) {
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = name
        shot.lifetime = .keepAlways
        add(shot)
    }
}
