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
            format: "identifier == %@", "torah-sources-search-field"
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
            format: "identifier == %@", "torah-sources-search-field"
        )).firstMatch
        XCTAssertTrue(search.waitForExistence(timeout: 20))
        search.tap()
        let previous = (search.value as? String) ?? ""
        if !previous.isEmpty && previous != search.placeholderValue {
            search.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: previous.utf16.count))
        }
        let noMatch = "zzqvnonexistent123456789"
        search.typeText(noMatch)
        try requireEmbedded(search.value as? String == noMatch, "The original search field must contain the complete no-match query")
        let empty = app.descendants(matching: .any).matching(identifier: "torah-search-empty").firstMatch
        try requireEmbedded(empty.waitForExistence(timeout: 45), "A real no-match search should expose its empty state")
        let noMatchesMessage = empty.staticTexts.matching(NSPredicate(
            format: "label CONTAINS %@", "No matches found."
        )).firstMatch
        try requireEmbedded(noMatchesMessage.waitForExistence(timeout: 10) && noMatchesMessage.isHittable,
                            "The empty result must visibly explain that no matches were found")
        attach("document-sources-empty-search")
        search.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: noMatch.utf16.count))
        let idle = app.descendants(matching: .any).matching(identifier: "torah-search-idle").firstMatch
        try requireEmbedded(idle.waitForExistence(timeout: 20), "Clearing the search must restore its original prompt")
        try requireEmbedded(empty.waitForNonExistence(timeout: 20), "Clearing the search should leave the empty-result state")
        try requireEmbedded(!app.descendants(matching: .any).matching(identifier: "torah-search-error").firstMatch.exists,
                            "Clearing the search must not replace the empty result with an error")
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
        try app.dismissNativeTorahInspector()
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
        let targetID = [fixture.spaceId, fixture.manySourcesDocument, ""]
            .map { "\($0.utf8.count):\($0)" }.joined(separator: "|")
        let rows = app.buttons.matching(NSPredicate(
            format: "identifier == %@", "torah-inspector-related-row-" + targetID
        ))
        let linkedDocument = rows.firstMatch
        try requireEmbedded(linkedDocument.waitForExistence(timeout: 45),
                            "The canonical document source should appear in the current Space")
        try requireEmbedded(rows.count == 1, "The exact Space/document must have one indexed row")
        try requireEmbedded(linkedDocument.label.contains("UI27 source document"),
                            "The indexed row must retain the native title alongside its metadata")
        try requireEmbedded(linkedDocument.isHittable, "The indexed document row must be reachable")
        attach("inspector-indexed-document-results")
    }
    func testInspectorEmbeddedSearchOpenReturnAndDocumentLink() throws {
        defer { attachFinalEvidence() }
        try recordEntryEvidence()
        try openDocument(fixture.manySourcesDocument)
        let originalChips = Set(documentSourceChips.allElementsBoundByIndex.map(\.identifier))
        try requireEmbedded(!originalChips.isEmpty, "A real document source must exist before the embedded search")
        let reference = "Genesis 1:2"
        try requireEmbedded(!documentSourceChips.matching(NSPredicate(format: "label CONTAINS %@", reference)).firstMatch.exists,
                            "The new source is already linked in the supposedly fresh native fixture")

        var controls = try openEmbeddedSourceSearch()
        let result = try embeddedSourceResult(reference, search: controls.search)
        let resultID = result.identifier
        let suffix = String(resultID.dropFirst("torah-search-open-".count))
        try requireEmbedded(!suffix.isEmpty, "The provider result has no stable identity")
        let linkID = "torah-search-link-" + suffix
        let link = app.buttons.matching(NSPredicate(format: "identifier == %@", linkID)).firstMatch
        try requireEmbedded(link.waitForExistence(timeout: 20) && link.isEnabled,
                            "The existing document-link action is unavailable")
        try requireEmbedded(link.label.lowercased().contains("document") && !link.label.lowercased().contains("block"),
                            "Embedded search must expose an explicit document association target")
        attach("inspector-embedded-real-source-result")

        result.tap()
        let segment = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@", "torah-reader-segment-" + reference
        )).firstMatch
        try requireEmbedded(segment.waitForExistence(timeout: 60), "Open did not reach the real provider reader")
        try requireEmbedded(!segment.label.isEmpty && segment.label != reference,
                            "The provider reader must contain actual source text")
        try requireOneInspector()
        try requireEmbedded(!embeddedSearch.exists, "Reader navigation left the search destination on screen")
        attach("inspector-embedded-open-within-panel")

        try inspectorBack(controls.inspector)
        try requireEmbedded(embeddedSearch.waitForExistence(timeout: 20), "Native Back did not restore embedded search")
        try requireEmbedded(controls.search.value as? String == reference,
                            "Returning within the same panel lost the source query")
        try requireEmbedded(app.buttons.matching(NSPredicate(format: "identifier == %@", resultID)).firstMatch.waitForExistence(timeout: 30),
                            "Returning within the panel lost the provider results")
        try closeEmbeddedInspector(controls.inspector)
        try requireEmbedded(Set(documentSourceChips.allElementsBoundByIndex.map(\.identifier)) == originalChips,
                            "Opening a search result wrote an unrequested document association")
        attach("inspector-open-left-document-links-unchanged")

        controls = try openEmbeddedSourceSearch()
        _ = try embeddedSourceResult(reference, search: controls.search)
        let confirmedLink = app.buttons.matching(NSPredicate(format: "identifier == %@", linkID)).firstMatch
        try requireEmbedded(confirmedLink.waitForExistence(timeout: 20) && confirmedLink.isHittable,
                            "The matching provider result lost its document-link action")
        confirmedLink.tap()
        let strip = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@", "torah-existing-associations-strip"
        )).firstMatch
        let association = strip.buttons.matching(NSPredicate(format: "label CONTAINS %@", reference)).firstMatch
        try requireEmbedded(association.waitForExistence(timeout: 30),
                            "The native canonical association was not read back in the current document context")
        try requireOneInspector()
        try requireEmbedded(embeddedSearch.exists, "Linking unexpectedly changed the Inspector route")
        attach("inspector-embedded-document-link-readback")
        try closeEmbeddedInspector(controls.inspector)
        let newChip = documentSourceChips.matching(NSPredicate(format: "label CONTAINS %@", reference)).firstMatch
        try requireEmbedded(newChip.waitForExistence(timeout: 30), "The current document did not receive its new source chip")
        let linkedChips = Set(documentSourceChips.allElementsBoundByIndex.map(\.identifier))
        try requireEmbedded(linkedChips.count == originalChips.count + 1 && originalChips.isSubset(of: linkedChips),
                            "Linking replaced another source or created duplicate document associations")
        try requireEmbedded(!app.keyboards.firstMatch.exists, "Closing source search unexpectedly focused the editor keyboard")
        newChip.tap()
        let reopenFull = app.buttons["torah-inspector-open-full-source"]
        let reopenedSegment = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@", "torah-reader-segment-" + reference
        )).firstMatch
        let expand = app.buttons["torah-inspector-expand-medium"]
        if expand.waitForExistence(timeout: 5) { expand.tap() }
        if !reopenedSegment.waitForExistence(timeout: 5) {
            try requireEmbedded(reopenFull.waitForExistence(timeout: 30) && reopenFull.isHittable,
                                "The linked source did not expose its existing full-reader route")
            reopenFull.tap()
        }
        try requireEmbedded(reopenedSegment.waitForExistence(timeout: 60),
                            "Reopening the new document chip did not recover the same source")
        try requireOneInspector()
        attach("inspector-linked-source-reopened")
        try closeInspectorFromReader()
    }

    private var documentSourceChips: XCUIElementQuery {
        app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "torah-document-source-chip-"))
    }

    private var embeddedSearch: XCUIElement {
        app.descendants(matching: .any).matching(NSPredicate(format: "identifier == %@", "torah-sources-search-embedded")).firstMatch
    }

    private func requireOneInspector() throws {
        let panels = app.descendants(matching: .any).matching(NSPredicate(format: "identifier BEGINSWITH %@", "torah-inspector-sheet-"))
        try requireEmbedded(panels.firstMatch.waitForExistence(timeout: 30) && panels.count == 1,
                            "Exactly one native Inspector must contain the search/reader route")
        try requireEmbedded(!app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@", "torah-sources-search-standalone"
        )).firstMatch.exists, "Embedded search presented a second standalone search")
    }

    private func openEmbeddedSourceSearch() throws -> (inspector: XCUIElement, search: XCUIElement) {
        let original = documentSourceChips.matching(NSPredicate(format: "label CONTAINS %@", "Genesis 1:1")).firstMatch
        try requireEmbedded(original.waitForExistence(timeout: 30) && original.isHittable, "The original document source is unavailable")
        original.tap()
        try requireOneInspector()
        let entry = app.buttons.matching(NSPredicate(format: "identifier == %@ OR identifier == %@",
            "torah-inspector-search-entry", "torah-inspector-search-entry-peek")).firstMatch
        try requireEmbedded(entry.waitForExistence(timeout: 30) && entry.isHittable, "The existing Inspector search action is unavailable")
        entry.tap()
        try requireEmbedded(embeddedSearch.waitForExistence(timeout: 30), "The search action did not enter the same Inspector")
        try requireOneInspector()
        let field = app.textFields.matching(NSPredicate(format: "identifier == %@", "torah-sources-search-field")).firstMatch
        try requireEmbedded(field.waitForExistence(timeout: 20) && field.isHittable, "Embedded search field is unreachable")
        let panel = app.descendants(matching: .any).matching(NSPredicate(format: "identifier BEGINSWITH %@", "torah-inspector-sheet-")).firstMatch
        return (panel, field)
    }

    private func embeddedSourceResult(_ reference: String, search: XCUIElement) throws -> XCUIElement {
        search.tap()
        let previous = (search.value as? String) ?? ""
        if !previous.isEmpty && previous != search.placeholderValue {
            search.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: previous.utf16.count))
        }
        search.typeText(reference)
        let result = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND label == %@", "torah-search-open-", reference
        )).firstMatch
        try requireEmbedded(result.waitForExistence(timeout: 60) && result.isHittable,
                            "The real provider did not return the requested source")
        try requireEmbedded(!app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@", "torah-search-error"
        )).firstMatch.exists, "A provider failure cannot count as search acceptance")
        return result
    }

    private func inspectorBack(_ inspector: XCUIElement) throws {
        let candidates = inspector.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@ OR identifier == %@", "Search Torah sources", "Back", "Back"
        )).allElementsBoundByIndex.filter(\.isHittable)
        try requireEmbedded(candidates.count == 1, "The Inspector must expose exactly one existing native Back control")
        try XCTUnwrap(candidates.first).tap()
    }

    private func closeEmbeddedInspector(_ inspector: XCUIElement) throws {
        try inspectorBack(inspector)
        try requireEmbedded(embeddedSearch.waitForNonExistence(timeout: 20), "The embedded search did not leave its route")
        try closeInspectorFromReader()
    }

    private func closeInspectorFromReader() throws {
        try app.dismissNativeTorahInspector()
        try requireEmbedded(more.waitForExistence(timeout: 20) && more.isHittable, "Inspector dismissal did not restore document editing")
    }

    private func requireEmbedded(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
        guard try condition() else {
            throw NSError(domain: "PinkhaEmbeddedInspectorAcceptance", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: message])
        }
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
        if expectedPID == nil || Self.readyPID != expectedPID || app.alerts.count > 0 {
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
            // Preserve the runner's exact process; only continue the original
            // warning for its controller-bound, freshly prepared native fixture.
            try PinkhaDisposableStartupWarning.waitForNavigation(
                app, testCase: self, spaceID: fixture.spaceId,
                allowedLanes: ["inspector", "inspector-search"]
            )
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

extension XCUIApplication {
    /// Search replaces the visible Close button in the existing Kit toolbar.
    /// Exercise the native sheet pan, observing its live frame after each detent.
    @MainActor
    func dismissNativeTorahInspector() throws {
        let panels = descendants(matching: .any).matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-inspector-sheet-"
        ))
        guard panels.firstMatch.waitForExistence(timeout: 20), panels.count == 1 else {
            throw NSError(domain: "NativeInspectorDismissal", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "One real Inspector is required for native dismissal"])
        }
        // The source has exactly large, medium and peek detents. A pan may move
        // to the next detent first; observe it and make at most three real gestures.
        for _ in 0..<3 {
            let panel = panels.firstMatch
            let sheetFrame = panel.frame
            let appFrame = frame
            let inset = min(CGFloat(12), sheetFrame.height * 0.04)
            guard sheetFrame.width > 44, sheetFrame.height > 44,
                  sheetFrame.midX >= appFrame.minX, sheetFrame.midX <= appFrame.maxX,
                  appFrame.maxY - 12 > sheetFrame.minY + inset + 30 else {
                throw NSError(domain: "NativeInspectorDismissal", code: 2,
                              userInfo: [NSLocalizedDescriptionKey: "The observed native sheet has no reachable downward pan path"])
            }
            let start = panel.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0))
                .withOffset(CGVector(dx: 0, dy: inset))
            let end = coordinate(withNormalizedOffset: .zero).withOffset(CGVector(
                dx: sheetFrame.midX - appFrame.minX, dy: appFrame.height - 12
            ))
            start.press(forDuration: 0.05, thenDragTo: end, withVelocity: .fast, thenHoldForDuration: 0)
            if panels.firstMatch.waitForNonExistence(timeout: 5) { return }
        }
        throw NSError(domain: "NativeInspectorDismissal", code: 3,
                      userInfo: [NSLocalizedDescriptionKey: "The native Inspector remained after its bounded dismissal gestures"])
    }
}

/// Additive G03 coverage using the original twelve-source Properties fixture.
/// The original Inspector cases and native preparation remain unchanged.
@MainActor
final class PinkhaTorahSourceOverflowAcceptanceUITests: XCTestCase {
    private struct Fixture: Decodable {
        struct Header: Decodable {
            let count: Int
            let objectId: String
            let labels: [String]
        }
        let spaceId: String
        let manySourcesDocument: String
        let sourceHeaderCases: [Header]
    }

    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")

    override func tearDownWithError() throws {
        if app.state != .notRunning { app.terminate() }
        // Match the original Properties lane's exclusive owned-App lifecycle.
        // Do not leave its store open for the next original native host stage.
        guard app.wait(for: .notRunning, timeout: 15) else {
            let hierarchy = XCTAttachment(string: app.debugDescription)
            hierarchy.name = "source-overflow-owned-app-exit-failure-ax"
            hierarchy.lifetime = .keepAlways
            add(hierarchy)
            XCTFail("The owned App did not exit after the source-overflow case")
            return
        }
    }

    func testHiddenSourceSelectionOpensExactReferenceAndReturnsToDocument() throws {
        executionTimeAllowance = 480
        continueAfterFailure = false
        defer { attachOverflowState("final") }
        let environment = ProcessInfo.processInfo.environment
        try requireOverflow(environment["PINKHA_NATIVE_UI_DISPOSABLE"] == "1"
                            && environment["PINKHA_UI27_APP_LANGUAGE"] == "en",
                            "This case requires the original disposable English Properties lane")
        let raw = try XCTUnwrap(environment["PINKHA_NATIVE_UI_FIXTURE_JSON"])
        let fixture = try JSONDecoder().decode(Fixture.self, from: Data(raw.utf8))
        try requireOverflow(!fixture.spaceId.isEmpty && !fixture.manySourcesDocument.isEmpty,
                            "The original fixture has no Space or source-bearing document")
        let headers = fixture.sourceHeaderCases.filter { $0.count == 12 }
        try requireOverflow(headers.count == 1, "The original twelve-source fixture is not unique")
        let many = try XCTUnwrap(headers.first)
        let expected = Set((1...12).map { "Genesis 2:\($0)" })
        try requireOverflow(many.objectId == fixture.manySourcesDocument
                            && many.labels.count == 12 && Set(many.labels) == expected,
                            "The unchanged native preparation must supply its exact twelve canonical references")

        if app.state != .notRunning { app.terminate() }
        try requireOverflow(app.wait(for: .notRunning, timeout: 15), "The previous owned App did not exit")
        app.launchEnvironment["PINKHA_UI27_ROUTE_OBSERVATION"] = "1"
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
        // The existing helper validates raw fixture bytes, original preparation,
        // admission, owned simulator and actual source/run before any Continue.
        try PinkhaDisposableStartupWarning.waitForNavigation(
            app, testCase: self, spaceID: fixture.spaceId, allowedLanes: ["properties"]
        )
        var route = URLComponents()
        route.scheme = "anytype"
        route.host = "object"
        route.queryItems = [URLQueryItem(name: "objectId", value: fixture.manySourcesDocument),
                            URLQueryItem(name: "spaceId", value: fixture.spaceId)]
        XCUIDevice.shared.system.open(try XCTUnwrap(route.url))
        try requireOverflowDocument(fixture)
        let before = try sourceHeader(expected: expected)
        let hidden = expected.subtracting(before.values)
        try requireOverflow(hidden.count == 10 && inspectorPanels.count == 0,
                            "The selected source must come from the hidden ten with no previous Inspector")
        let readerRows = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-reader-segment-"
        ))
        try requireOverflow(readerRows.count == 0,
                            "A previous reader cannot supply the later selected-segment assertion")

        app.buttons["torah-document-sources-more"].tap()
        let choices = app.buttons.matching(NSPredicate(format: "label IN %@", hidden.sorted()))
        let menuReady = NSPredicate { _, _ in
            let rows = choices.allElementsBoundByIndex
            return rows.count == 10 && Set(rows.map(\.label)) == hidden
                && rows.contains { $0.isEnabled && $0.isHittable }
        }
        try requireOverflow(XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: menuReady, object: app)],
                                           timeout: 20) == .completed,
                            "The original overflow Menu did not expose the exact ten hidden sources")
        let observedMenu = choices.allElementsBoundByIndex.map(\.label).sorted()
        let choice = try XCTUnwrap(choices.allElementsBoundByIndex
            .filter { $0.isEnabled && $0.isHittable }.sorted { $0.label < $1.label }.first)
        let selectedReference = choice.label
        let selectedRows = choices.matching(NSPredicate(format: "label == %@", selectedReference))
        try requireOverflow(hidden.contains(selectedReference) && !before.values.contains(selectedReference)
                            && selectedRows.count == 1 && selectedRows.firstMatch.isHittable,
                            "The chosen unique source was not one of the hidden ten actual Menu rows")
        try recordOverflow("menu-choice", fixture: fixture, before: before, hidden: hidden,
                           selectedReference: selectedReference, observedMenu: observedMenu)
        selectedRows.firstMatch.tap()

        try requireOverflow(inspectorPanels.firstMatch.waitForExistence(timeout: 30)
                            && inspectorPanels.count == 1,
                            "The hidden source did not open exactly one original Inspector")
        let inspector = inspectorPanels.firstMatch
        // The current App opens relationships at medium. Kit9058 resolves the
        // preferred segment before publishing this native navigation title.
        // Checking a verse anywhere in the later full chapter would be weaker.
        let navigation = inspector.navigationBars.firstMatch
        try requireOverflow(navigation.waitForExistence(timeout: 60) && inspector.navigationBars.count == 1,
                            "The selected segment's native navigation is unavailable")
        let heading = navigation.staticTexts.matching(NSPredicate(format: "label == %@", selectedReference))
        try requireOverflow(heading.firstMatch.waitForExistence(timeout: 60)
                            && heading.count == 1 && heading.firstMatch.isHittable,
                            "The Inspector resolved a different canonical segment from the selected hidden row")
        let observedHeading = heading.firstMatch.label
        try requireOverflow(readerRows.count == 0, "The initial selection bypassed its segment relationships route")
        let fullSource = inspector.buttons["torah-inspector-open-full-source"]
        try requireOverflow(fullSource.waitForExistence(timeout: 30)
                            && fullSource.isEnabled && fullSource.isHittable,
                            "The resolved segment has no reachable original full-source action")
        try recordOverflow("selected-reference", fixture: fixture, before: before, hidden: hidden,
                           selectedReference: selectedReference, observedMenu: observedMenu,
                           observedHeading: observedHeading)
        fullSource.tap()
        let segmentID = "torah-reader-segment-" + selectedReference
        let segments = app.descendants(matching: .any).matching(NSPredicate(format: "identifier == %@", segmentID))
        try requireOverflow(segments.firstMatch.waitForExistence(timeout: 60) && segments.count == 1,
                            "The full reader did not recover the selected canonical segment")
        let segment = segments.firstMatch
        let text = segment.label.trimmingCharacters(in: .whitespacesAndNewlines)
        try requireOverflow(segment.isHittable && !text.isEmpty && text != selectedReference
                            && inspectorPanels.count == 1 && app.alerts.count == 0,
                            "The selected reader segment must expose reachable real source text")
        try recordOverflow("reader-content", fixture: fixture, before: before, hidden: hidden,
                           selectedReference: selectedReference, observedMenu: observedMenu,
                           observedHeading: observedHeading, readerIdentifier: segment.identifier,
                           readerText: text)

        try app.dismissNativeTorahInspector()
        try requireOverflow(inspectorPanels.count == 0 && readerRows.count == 0,
                            "The source Inspector did not dismiss completely")
        try requireOverflowDocument(fixture)
        let after = try sourceHeader(expected: expected)
        try requireOverflow(after == before && !app.keyboards.firstMatch.exists,
                            "Source navigation changed the document chips or unexpectedly focused its keyboard")
        try recordOverflow("returned-document", fixture: fixture, before: before, hidden: hidden,
                           selectedReference: selectedReference, observedMenu: observedMenu,
                           observedHeading: observedHeading, after: after)
    }

    private var inspectorPanels: XCUIElementQuery {
        app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-inspector-sheet-"
        ))
    }

    private func requireOverflowDocument(_ fixture: Fixture) throws {
        let identifier = "pinkha-ui27-editor:\(fixture.spaceId):\(fixture.manySourcesDocument)"
        let editors = app.otherElements.matching(NSPredicate(format: "identifier == %@", identifier))
        let more = app.buttons.matching(NSPredicate(format: "label == %@ OR label == %@", "More", "x24/More")).firstMatch
        let title = app.descendants(matching: .any).matching(NSPredicate(
            format: "label == %@ OR value == %@", "Native twelve-source chips", "Native twelve-source chips"
        )).firstMatch
        let ready = NSPredicate { _, _ in
            editors.count == 1 && editors.firstMatch.isHittable && more.exists && more.isHittable
                && title.exists && title.isHittable && self.app.alerts.count == 0
        }
        try requireOverflow(XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: ready, object: app)],
                                           timeout: 45) == .completed,
                            "The visible document does not match the exact native fixture Space, object and title")
    }

    private func sourceHeader(expected: Set<String>) throws -> [String: String] {
        let chips = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "torah-document-source-chip-"))
        let overflow = app.buttons["torah-document-sources-more"]
        let add = app.buttons["torah-document-sources-add"]
        let ready = NSPredicate { _, _ in
            let rows = chips.allElementsBoundByIndex
            return rows.count == 2 && Set(rows.map(\.identifier)).count == 2
                && Set(rows.map(\.label)).count == 2 && Set(rows.map(\.label)).isSubset(of: expected)
                && rows.allSatisfy { !$0.identifier.isEmpty && $0.isHittable }
                && overflow.exists && overflow.isHittable && overflow.label == "10 Sources"
                && add.exists && add.isHittable && add.value as? String == "compact-icon"
        }
        try requireOverflow(XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: ready, object: app)],
                                           timeout: 20) == .completed,
                            "The unchanged native two-chip/ten-overflow source header did not render")
        var observed: [String: String] = [:]
        for row in chips.allElementsBoundByIndex {
            try requireOverflow(observed[row.identifier] == nil, "The source header contains duplicate chip identity")
            observed[row.identifier] = row.label
        }
        return observed
    }

    private func recordOverflow(_ phase: String, fixture: Fixture, before: [String: String], hidden: Set<String>,
                                selectedReference: String, observedMenu: [String], observedHeading: String = "",
                                readerIdentifier: String = "", readerText: String = "",
                                after: [String: String] = [:]) throws {
        let environment = ProcessInfo.processInfo.environment
        let keys = ["SOURCE_SHA", "RUN_ID", "RUN_ATTEMPT", "SIMULATOR_UDID", "LANE", "ADMISSION_SHA256",
                    "PREPARATION_SHA256", "INVOCATION_SHA256", "OWNED_SIMULATOR_SHA256", "FIXTURE_SHA256"]
        var controller: [String: String] = [:]
        for key in keys { controller[key] = try XCTUnwrap(environment["PINKHA_UI27_STARTUP_" + key]) }
        let value: [String: Any] = [
            "schema": "pinkha-source-overflow-ui-observation-v1", "phase": phase,
            "spaceID": fixture.spaceId, "objectID": fixture.manySourcesDocument,
            "controllerProvenance": "CONTROLLER_OWNED_SIMULATOR_AFTER_ORIGINAL_NATIVE_PREPARATION",
            "controller": controller, "selectedReference": selectedReference,
            "visibleBefore": before, "hiddenReferences": hidden.sorted(), "observedMenu": observedMenu,
            "observedSelectedHeading": observedHeading, "readerIdentifier": readerIdentifier,
            "readerText": readerText, "visibleAfter": after,
            "associationMutationRequestedByThisCase": false, "evidenceScope": "OBSERVED_UI_ONLY"
        ]
        let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
        attachment.name = "source-overflow-" + phase
        attachment.lifetime = .keepAlways
        add(attachment)
        attachOverflowState(phase)
    }

    private func attachOverflowState(_ phase: String) {
        let hierarchy = XCTAttachment(string: app.debugDescription)
        hierarchy.name = "source-overflow-" + phase + "-ax"
        hierarchy.lifetime = .keepAlways
        add(hierarchy)
        if app.state == .runningForeground {
            let screenshot = XCTAttachment(screenshot: app.screenshot())
            screenshot.name = "source-overflow-" + phase + "-visual"
            screenshot.lifetime = .keepAlways
            add(screenshot)
        }
    }

    private func requireOverflow(_ value: @autoclosure () -> Bool, _ reason: String) throws {
        guard value() else {
            throw NSError(domain: "PinkhaSourceOverflowAcceptance", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: reason])
        }
    }
}
