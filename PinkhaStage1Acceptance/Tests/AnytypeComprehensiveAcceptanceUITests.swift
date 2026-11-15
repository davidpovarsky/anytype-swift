import XCTest

/// Real-app UI checks. The runner must supply a freshly provisioned native fixture.
@MainActor
final class AnytypeComprehensiveAcceptanceUITests: XCTestCase {
    private struct Fixture: Decodable {
        let spaceId: String
        let universalDocuments: [String: String]
        let manySourcesDocument: String
    }

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
        if app.state != .notRunning { app.terminate() }
        XCTAssertFalse(fixture.spaceId.isEmpty)
        XCTAssertFalse(try XCTUnwrap(fixture.universalDocuments["page"]).isEmpty)
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
    }

    func testObjectAddPropertyButtonAndPickerSearch() throws {
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
    override func tearDownWithError() throws {
        if app.state == .runningForeground {
            attach("final-screen-\(name)")
            let hierarchy = XCTAttachment(string: app.debugDescription)
            hierarchy.name = "final-hierarchy-\(name)"
            hierarchy.lifetime = .keepAlways
            add(hierarchy)
        }
    }

    private func openPage() throws {
        try openDocument(try XCTUnwrap(fixture.universalDocuments["page"]))
    }

    private func openDocument(_ objectID: String) throws {
        if app.state == .notRunning { app.launch() }
        var url = URLComponents()
        url.scheme = "anytype"
        url.host = "object"
        url.queryItems = [
            URLQueryItem(name: "objectId", value: objectID),
            URLQueryItem(name: "spaceId", value: fixture.spaceId)
        ]
        app.open(try XCTUnwrap(url.url))
        XCTAssertTrue(more.waitForExistence(timeout: 45), "Disposable document did not open")
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
