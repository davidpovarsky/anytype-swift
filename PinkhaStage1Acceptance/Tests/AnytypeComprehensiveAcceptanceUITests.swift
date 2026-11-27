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

import CryptoKit

/// Additive G02 UI stages. The controller interleaves a read-only native
/// baseline/postflight on this same original, disposable NativeDerived fixture.
@MainActor
final class PinkhaTorahWordUnlinkAcceptanceUITests: XCTestCase {
    private struct Fixture: Decodable {
        struct TypeChoice: Decodable {
            let id: String
            let label: String
            let propertyName: String
            let sectionTitle: String
            let sectionExpandable: Bool
        }
        struct TypeMetadata: Decodable { let types: [String: TypeChoice] }
        let spaceId: String
        let documents: [String: String]
        let names: [String: String]
        let types: [String: String]
        let typeSwitch: TypeMetadata
        let nativeProperties: [String]
        let sourceQuery: String
        let sourceLabel: String
        let topicQuery: String
        let topicLabel: String
        let wordQuery: String
    }

    private struct Baseline: Decodable {
        struct Document: Decodable {
            let objectID: String
            let typeID: String
            let name: String
            let sourceLabel: String
            let topicLabel: String
            let wordRecordID: String
            let wordIdentity: String
            let wordLabel: String
            let tagPropertyName: String
            let tagID: String
            let tagName: String
        }
        let schema: String
        let nativeBaselineSHA256: String
        let seedUIReceiptSHA256: String
        let controller: [String: String]
        let spaceID: String
        let documents: [String: Document]
    }

    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private let roles = ["chiddush", "article", "research"]
    private let sourceName = "מקור/ות"
    private let topicName = "נושא"
    private let wordName = "מילה / ערך"
    private let emptyValue = "Select options"
    private var fixture: Fixture!
    private var controller = [String: String]()
    private var expandedSections = Set<String>()

    override func tearDownWithError() throws {
        if app.state != .notRunning { app.terminate() }
        guard app.wait(for: .notRunning, timeout: 15) else {
            let attachment = XCTAttachment(string: app.debugDescription)
            attachment.name = "word-unlink-owned-app-exit-failure-ax"
            attachment.lifetime = .keepAlways
            add(attachment)
            XCTFail("The owned App must exit before the next read-only native stage opens its store")
            throw NSError(domain: "PinkhaWordUnlinkOwnedAppExit", code: 1)
        }
        try super.tearDownWithError()
    }

    func testSeedOriginalWordUnlinkFixturesThroughProperties() throws {
        executionTimeAllowance = 900
        continueAfterFailure = false
        defer { attachState("seed-final") }
        try configure(phase: "seed")
        var documents = [String: [String: Any]]()
        for role in roles {
            try openProperties(role, cold: true)
            let source = try selectOrObserveCanonical(sourceName, query: fixture.sourceQuery,
                                                       expectedLabel: fixture.sourceLabel, role: role)
            let topic = try selectOrObserveCanonical(topicName, query: fixture.topicQuery,
                                                      expectedLabel: fixture.topicLabel, role: role)
            let word = try selectOrObserveCanonical(wordName, query: fixture.wordQuery,
                                                     expectedLabel: nil, role: role)
            let tagPropertyName = try seedOriginalTag(role: role)
            try openProperties(role, cold: true)
            let observed = try observeRetainedValues(role: role, wordLabel: word.label,
                                                     tagPropertyName: tagPropertyName, tagName: tagName(role))
            let value: [String: Any] = [
                "objectID": try XCTUnwrap(fixture.documents[role]),
                "typeID": try XCTUnwrap(fixture.types[role]),
                "name": try documentName(role),
                "sourceLabel": source.label, "topicLabel": topic.label, "wordLabel": word.label,
                "sourceAction": source.action, "topicAction": topic.action, "wordAction": word.action,
                "tagPropertyName": tagPropertyName, "tagName": tagName(role),
                "observedRows": observed, "appPID": try processID()
            ]
            documents[role] = value
            try record("seed-" + role, fields: ["role": role, "document": value])
        }
        // Labels here are actual UI observations. The next native stage must
        // resolve and retain the real canonical/Tag IDs before unlink can run.
        try record("seed-complete", fields: ["documents": documents,
                   "nativeIdentifiersEstablishedByThisUIStage": false])
    }

    func testChangedQueryPickerCancelThenWordUnlinkAndColdReopenForAllWritingTypes() throws {
        executionTimeAllowance = 600
        continueAfterFailure = false
        defer { attachState("unlink-final") }
        try configure(phase: "unlink")
        let baseline = try loadBaseline()
        var completed = [String: [String: Any]]()
        for role in roles {
            let expected = try XCTUnwrap(baseline.documents[role])
            try openProperties(role, cold: true)
            _ = try observeRetainedValues(role: role, wordLabel: expected.wordLabel,
                                           tagPropertyName: expected.tagPropertyName, tagName: expected.tagName)
            try openCanonicalPicker(wordName)
            try require(try selectedCanonicalLabel() == expected.wordLabel,
                        "The sole Word label differs from the native baseline for this exact document")
            let cancelQuery = "G02 cancel " + String((try XCTUnwrap(controller["TOKEN"])).prefix(8))
            try replaceSearch(nativeSearch, with: cancelQuery)
            try require(try selectedCanonicalLabel() == expected.wordLabel,
                        "Changing the query changed the existing Word before cancellation")
            let cancelPID = try processID()
            try record("cancel-query-" + role, fields: ["role": role, "query": cancelQuery,
                       "wordRecordIDFromNativeBaseline": expected.wordRecordID,
                       "wordIdentityFromNativeBaseline": expected.wordIdentity])
            try dismissChangedQueryPicker()
            let afterCancel = try observeRetainedValues(role: role, wordLabel: expected.wordLabel,
                                                         tagPropertyName: expected.tagPropertyName,
                                                         tagName: expected.tagName)
            try require(try processID() == cancelPID, "Cancellation restarted the App instead of closing the picker")
            try record("cancelled-" + role, fields: ["role": role, "observedRows": afterCancel,
                       "wordRecordIDFromNativeBaseline": expected.wordRecordID,
                       "cancelMechanism": "DISMISS_CHANGED_QUERY_PICKER_WITHOUT_LINK_OR_UNLINK"])

            try openCanonicalPicker(wordName)
            try require(try selectedCanonicalLabel() == expected.wordLabel,
                        "The exact baseline Word was not retained after closing its picker")
            let remove = associationStrip.buttons.matching(NSPredicate(format: "label == %@", "Remove link"))
            try require(remove.count == 1 && remove.firstMatch.isEnabled && remove.firstMatch.isHittable,
                        "Only the sole selected Word's original Remove link action may be invoked")
            remove.firstMatch.tap()
            // This original action commits immediately; there is no confirmation
            // dialog. A pending/error persistence strip must not count as saved.
            try require(associationStrip.waitForNonExistence(timeout: 30)
                        && nativeSearch.exists && app.alerts.count == 0,
                        "The original Word unlink did not finish or left a persistence error")
            let previousPID = try processID()
            try record("unlinked-warm-" + role, fields: ["role": role,
                       "wordRecordIDFromNativeBaseline": expected.wordRecordID,
                       "wordIdentityFromNativeBaseline": expected.wordIdentity,
                       "confirmationDialogExpected": false])
            try openProperties(role, cold: true)
            let currentPID = try processID()
            try require(currentPID != previousPID, "Cold reopen reused the previous App process")
            let after = try observeRetainedValues(role: role, wordLabel: emptyValue,
                                                   tagPropertyName: expected.tagPropertyName,
                                                   tagName: expected.tagName)
            try openCanonicalPicker(wordName)
            try require(associationStrip.waitForNonExistence(timeout: 15)
                        && !app.buttons["Remove link"].exists,
                        "The removed Word reappeared in the exact fixed-scope picker after cold reopen")
            let value: [String: Any] = [
                "objectID": expected.objectID, "typeID": expected.typeID, "name": expected.name,
                "wordRecordIDFromNativeBaseline": expected.wordRecordID,
                "wordIdentityFromNativeBaseline": expected.wordIdentity,
                "tagIDFromNativeBaseline": expected.tagID, "observedRows": after,
                "previousPID": previousPID, "appPID": currentPID
            ]
            completed[role] = value
            try record("cold-reopen-" + role, fields: ["role": role, "document": value])
        }
        try record("unlink-complete", fields: ["documents": completed,
                   "nativeBaselineSHA256": baseline.nativeBaselineSHA256,
                   "seedUIReceiptSHA256": baseline.seedUIReceiptSHA256,
                   "nativePersistencePostflightRequired": true])
    }

    private func configure(phase: String) throws {
        let environment = ProcessInfo.processInfo.environment
        try require(environment["PINKHA_G02_UI_PHASE"] == phase
                    && environment["PINKHA_NATIVE_UI_DISPOSABLE"] == "1"
                    && environment["PINKHA_UI27_APP_LANGUAGE"] == "en",
                    "This future G02 stage requires the bound disposable English Properties lane")
        let raw = try XCTUnwrap(environment["PINKHA_NATIVE_UI_FIXTURE_JSON"])
        fixture = try JSONDecoder().decode(Fixture.self, from: Data(raw.utf8))
        try require(!fixture.spaceId.isEmpty && Set(fixture.documents.keys) == Set(roles)
                    && Set(fixture.documents.values).count == 3
                    && Set(roles.compactMap { fixture.types[$0] }).count == 3
                    && Set([sourceName, topicName, wordName]).isSubset(of: Set(fixture.nativeProperties)),
                    "The three original writing documents and native Torah properties are required")
        for role in roles {
            let id = try XCTUnwrap(fixture.documents[role])
            let type = try XCTUnwrap(fixture.typeSwitch.types[role])
            try require(!id.isEmpty && type.id == fixture.types[role] && !type.label.isEmpty,
                        "Original Type metadata does not match this writing role")
            _ = try documentName(role)
        }
        for key in ["SOURCE_SHA", "RUN_ID", "RUN_ATTEMPT", "TOKEN", "SIMULATOR_UDID", "LANE",
                    "ADMISSION_SHA256", "PREPARATION_SHA256", "INVOCATION_SHA256",
                    "OWNED_SIMULATOR_SHA256", "FIXTURE_SHA256"] {
            controller[key] = try XCTUnwrap(environment["PINKHA_UI27_STARTUP_" + key])
        }
        try require(controller["LANE"] == "properties", "G02 must reuse the original Properties fixture lane")
        app.launchEnvironment["PINKHA_UI27_ROUTE_OBSERVATION"] = "1"
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
    }

    private func loadBaseline() throws -> Baseline {
        let environment = ProcessInfo.processInfo.environment
        let raw = try XCTUnwrap(environment["PINKHA_G02_BASELINE_UI_JSON"])
        let data = Data(raw.utf8)
        let expectedSHA = try XCTUnwrap(environment["PINKHA_G02_BASELINE_UI_SHA256"])
        try require(!data.isEmpty && data.count <= 65_536 && sha256(data) == expectedSHA,
                    "The actual native baseline UI handoff is missing or its bytes differ")
        let baseline = try JSONDecoder().decode(Baseline.self, from: data)
        try require(baseline.schema == "pinkha-g02-word-native-ui-baseline-v1"
                    && baseline.controller == controller && baseline.spaceID == fixture.spaceId
                    && Set(baseline.documents.keys) == Set(roles)
                    && isSHA256(baseline.nativeBaselineSHA256) && isSHA256(baseline.seedUIReceiptSHA256),
                    "Native baseline belongs to another original fixture, source, run or owned simulator")
        for role in roles {
            let value = try XCTUnwrap(baseline.documents[role])
            try require(value.objectID == fixture.documents[role] && value.typeID == fixture.types[role]
                        && value.name == (try documentName(role))
                        && value.sourceLabel == fixture.sourceLabel && value.topicLabel == fixture.topicLabel
                        && !value.wordRecordID.isEmpty && !value.wordIdentity.isEmpty && !value.wordLabel.isEmpty
                        && ["Tag", "Tags"].contains(value.tagPropertyName)
                        && !value.tagID.isEmpty && value.tagName == tagName(role),
                        "Native baseline values do not match the actual UI-seeded writing document")
        }
        let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
        attachment.name = "word-unlink-native-ui-baseline"
        attachment.lifetime = .keepAlways
        add(attachment)
        return baseline
    }

    private func openProperties(_ role: String, cold: Bool) throws {
        if cold {
            if app.state != .notRunning { app.terminate() }
            try require(app.wait(for: .notRunning, timeout: 15), "The owned App did not exit before cold open")
        }
        if app.state == .notRunning { app.launch() }
        try PinkhaDisposableStartupWarning.waitForNavigation(
            app, testCase: self, spaceID: fixture.spaceId, allowedLanes: ["properties"]
        )
        let id = try XCTUnwrap(fixture.documents[role])
        var route = URLComponents()
        route.scheme = "anytype"; route.host = "object"
        route.queryItems = [URLQueryItem(name: "objectId", value: id),
                            URLQueryItem(name: "spaceId", value: fixture.spaceId)]
        XCUIDevice.shared.system.open(try XCTUnwrap(route.url))
        let editors = app.otherElements.matching(identifier: "pinkha-ui27-editor:\(fixture.spaceId):\(id)")
        let title = try documentName(role)
        let names = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@ OR value == %@", title, title))
        let more = app.buttons.matching(NSPredicate(format: "label == %@ OR label == %@", "More", "x24/More")).firstMatch
        try wait(timeout: 45, reason: "The exact prepared Space, object and document title are not mounted") {
            editors.count == 1 && editors.firstMatch.isHittable && more.isHittable
                && names.allElementsBoundByIndex.contains { $0.isHittable } && self.app.alerts.count == 0
        }
        more.tap()
        let properties = app.buttons["Properties"].firstMatch
        try require(properties.waitForExistence(timeout: 15) && properties.isHittable,
                    "The original Properties action is unavailable")
        properties.tap()
        expandedSections.removeAll()
        try require(propertyTitle(sourceName).waitForExistence(timeout: 20), "The original Properties sheet did not open")
        try require(!app.buttons["torah-property-ref"].exists, "A legacy projection replaced the original native row")
    }

    private func selectOrObserveCanonical(_ property: String, query: String, expectedLabel: String?,
                                          role: String) throws -> (label: String, action: String) {
        try openCanonicalPicker(property)
        try replaceSearch(nativeSearch, with: query)
        // Observe an original earlier Properties selection if present. Otherwise
        // use the real fixed-scope provider picker, then capture its actual label.
        let links = app.buttons.matching(NSPredicate(format: "label == %@", "Link to document"))
        try wait(timeout: 45, reason: "The original fixed-scope picker produced neither a selection nor a link action") {
            self.associationStrip.buttons["Remove link"].exists
                || links.allElementsBoundByIndex.contains { $0.isEnabled && $0.isHittable }
        }
        let created = !associationStrip.buttons["Remove link"].exists
        if created {
            let link = try XCTUnwrap(links.allElementsBoundByIndex.first { $0.isEnabled && $0.isHittable })
            link.tap()
        }
        let label = try selectedCanonicalLabel()
        if let expectedLabel { try require(label == expectedLabel, "Canonical selected label differs from the original fixture") }
        try openProperties(role, cold: true)
        _ = try propertyValue(property, label: label)
        return (label, created ? "LINKED_THROUGH_ORIGINAL_PICKER" : "OBSERVED_EXISTING_SOLE_SELECTION")
    }

    private func seedOriginalTag(role: String) throws -> String {
        try expandSection("Local")
        try expandSection("Hidden")
        var names = ["Tag", "Tags"].filter { propertyTitle($0).exists }
        if names.isEmpty {
            let add = app.buttons["torah-object-add-property"]
            try reveal(add)
            try require(add.isEnabled && add.isHittable, "The original Add property action is unavailable")
            add.tap()
            let search = app.textFields.matching(NSPredicate(format: "placeholderValue == %@", "Search or create new")).firstMatch
            try require(search.waitForExistence(timeout: 15), "The original property search did not open")
            try replaceSearch(search, with: "Tag")
            let existing = app.staticTexts["Existing properties"].firstMatch
            let choices = app.buttons.matching(NSPredicate(format: "label == %@ OR label == %@", "Tag", "Tags"))
            try wait(timeout: 30, reason: "The original existing Tag property is unavailable or ambiguous") {
                existing.exists && choices.allElementsBoundByIndex.filter {
                    $0.isEnabled && $0.isHittable && $0.frame.minY >= existing.frame.maxY
                }.count == 1
            }
            let choice = try XCTUnwrap(choices.allElementsBoundByIndex.first {
                $0.isEnabled && $0.isHittable && $0.frame.minY >= existing.frame.maxY
            })
            let name = choice.label
            choice.tap()
            try require(search.waitForNonExistence(timeout: 30), "Adding the original Tag property failed")
            try openProperties(role, cold: true)
            try expandSection("Local"); try expandSection("Hidden")
            names = [name].filter { propertyTitle($0).exists }
        }
        try require(names.count == 1, "The original Tag property must have one actual row")
        let name = try XCTUnwrap(names.first)
        let empty = try propertyValue(name, label: emptyValue)
        empty.tap()
        let navigation = app.navigationBars.matching(NSPredicate(format: "identifier == %@ OR label == %@", name, name)).firstMatch
        try require(navigation.waitForExistence(timeout: 15), "The original native Tag option list did not open")
        // No selected option is cleared or replaced. Seed one real native option
        // through its existing creation UI on this initially empty property.
        try require(!navigation.buttons["Clear"].exists, "This writing document unexpectedly already has Tag values")
        let create = app.buttons.matching(NSPredicate(format: "label == %@ AND hittable == true", "Create"))
        if create.count == 1 {
            create.firstMatch.tap()
        } else {
            // A nonempty native option list exposes its original search and
            // exact Create “name” row. Do not guess an icon's accessibility label.
            let fields = app.textFields.matching(NSPredicate(format: "hittable == true"))
            try require(create.count == 0 && fields.count == 1,
                        "The original Tag list has no unique native creation/search route")
            try replaceSearch(fields.firstMatch, with: tagName(role))
            let row = app.buttons.matching(NSPredicate(format: "label == %@", "Create “\(tagName(role))”"))
            try require(row.firstMatch.waitForExistence(timeout: 20) && row.count == 1
                        && row.firstMatch.isEnabled && row.firstMatch.isHittable,
                        "The original exact-name Tag creation row is unavailable")
            row.firstMatch.tap()
        }
        let field = app.textFields.matching(NSPredicate(format: "placeholderValue == %@", "Enter name...")).firstMatch
        try require(field.waitForExistence(timeout: 15) && field.isHittable, "The original Create option name field is unavailable")
        try replaceSearch(field, with: tagName(role))
        let save = app.buttons.matching(NSPredicate(format: "label == %@ AND hittable == true", "Create"))
        try require(save.count == 1 && save.firstMatch.isEnabled, "The original Create option action is unavailable or ambiguous")
        save.firstMatch.tap()
        try require(field.waitForNonExistence(timeout: 30), "The original native Tag option creation did not complete")
        let option = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", tagName(role)))
        try require(option.firstMatch.waitForExistence(timeout: 20)
                    && navigation.buttons["Clear"].waitForExistence(timeout: 20),
                    "The created native Tag was not selected by its original list")
        // The list's selectedOptionsIds publishes before updateProperty awaits.
        // Close only this observed Tag sheet, then await the parent document's
        // actual subscribed row before terminating its process.
        try dismissTagPicker(navigation)
        _ = try propertyValue(name, label: tagName(role))
        try openProperties(role, cold: true)
        try expandSection("Local"); try expandSection("Hidden")
        _ = try propertyValue(name, label: tagName(role))
        return name
    }

    private func dismissTagPicker(_ navigation: XCUIElement) throws {
        let frame = navigation.frame.intersection(app.frame)
        try require(navigation.isHittable && frame.width > 100 && frame.height > 20,
                    "The original foreground Tag sheet has no observed navigation bounds")
        let start = app.coordinate(withNormalizedOffset: .zero)
            .withOffset(CGVector(dx: frame.midX, dy: frame.minY + 6))
        let end = app.coordinate(withNormalizedOffset: .zero)
            .withOffset(CGVector(dx: frame.midX, dy: app.frame.maxY - 12))
        start.press(forDuration: 0.15, thenDragTo: end)
        try require(navigation.waitForNonExistence(timeout: 20)
                    && propertyTitle(sourceName).waitForExistence(timeout: 15) && app.alerts.count == 0,
                    "The original Tag picker did not return to its parent Properties sheet")
    }

    private func observeRetainedValues(role: String, wordLabel: String, tagPropertyName: String,
                                       tagName: String) throws -> [String: String] {
        try require(!nativeSearch.exists && app.alerts.count == 0, "A picker or alert obscures original Properties")
        try expandSection("Local"); try expandSection("Hidden")
        var observed = [String: String]()
        for (name, expected) in [(sourceName, fixture.sourceLabel), (topicName, fixture.topicLabel),
                                 (wordName, wordLabel), (tagPropertyName, tagName)] {
            observed[name] = try propertyValue(name, label: expected).label
        }
        let type = try XCTUnwrap(fixture.typeSwitch.types[role])
        if type.sectionExpandable { try expandSection(type.sectionTitle) }
        let values = app.buttons.matching(identifier: "pinkha-properties-type-value:" + type.id)
        try reveal(values.firstMatch)
        try require(values.count == 1 && values.firstMatch.isHittable && values.firstMatch.label.contains(type.label),
                    "The original writing Type changed or is not the exact native Type value")
        observed[type.propertyName] = values.firstMatch.label
        return observed
    }

    private func openCanonicalPicker(_ property: String) throws {
        let title = propertyTitle(property)
        try reveal(title)
        try require(title.isHittable, "The original canonical property row is not hittable")
        let x = min(app.frame.maxX - 24, title.frame.maxX + 28)
        app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: x, dy: title.frame.midY)).tap()
        try require(nativeSearch.waitForExistence(timeout: 15) && nativeSearch.isHittable
                    && app.segmentedControls.count == 0,
                    "The original fixed-scope native property picker did not open")
    }

    private var nativeSearch: XCUIElement {
        app.textFields.matching(NSPredicate(format: "identifier == %@ OR identifier == %@",
                                           "torah-native-property-editor", "torah-sources-search-field")).firstMatch
    }

    private var associationStrip: XCUIElement {
        app.descendants(matching: .any).matching(identifier: "torah-existing-associations-strip").firstMatch
    }

    private func selectedCanonicalLabel() throws -> String {
        try require(associationStrip.waitForExistence(timeout: 30), "The selected canonical preview is unavailable")
        let remove = associationStrip.buttons.matching(NSPredicate(format: "label == %@", "Remove link"))
        let chips = associationStrip.buttons.matching(NSPredicate(format: "label != %@", "Remove link"))
        try wait(timeout: 30, reason: "The fixed-scope picker must contain exactly one real selected item") {
            remove.count == 1 && chips.count == 1 && remove.firstMatch.isHittable && chips.firstMatch.isHittable
        }
        let label = chips.firstMatch.label.trimmingCharacters(in: .whitespacesAndNewlines)
        try require(!label.isEmpty && ![emptyValue, sourceName, topicName, wordName].contains(label)
                    && !label.contains("torah1|"), "The actual selected canonical item has no human label")
        return label
    }

    private func dismissChangedQueryPicker() throws {
        let search = nativeSearch
        let containers = app.otherElements.matching(NSPredicate(format: "identifier == %@ OR identifier == %@",
            "torah-native-property-editor", "torah-native-property-picker")).allElementsBoundByIndex.filter {
                $0.exists && $0.frame.contains(search.frame) && $0.frame.height > search.frame.height * 2
            }
        let frames = Set(containers.map { NSStringFromCGRect($0.frame) })
        try require(frames.count == 1, "The original native picker has no unambiguous observed sheet bounds")
        let panel = try XCTUnwrap(containers.first)
        let frame = panel.frame.intersection(app.frame)
        try require(frame.width > 100 && frame.height > 120 && frame.minY + 6 < search.frame.minY,
                    "There is no observed sheet chrome above the actual search field for cancellation")
        let start = app.coordinate(withNormalizedOffset: .zero)
            .withOffset(CGVector(dx: frame.midX, dy: frame.minY + 6))
        let end = app.coordinate(withNormalizedOffset: .zero)
            .withOffset(CGVector(dx: frame.midX, dy: app.frame.maxY - 12))
        start.press(forDuration: 0.15, thenDragTo: end)
        try require(search.waitForNonExistence(timeout: 20) && app.alerts.count == 0,
                    "The changed-query picker did not dismiss through its original sheet gesture")
    }

    private func propertyTitle(_ name: String) -> XCUIElement {
        app.descendants(matching: .any).matching(NSPredicate(
            format: "(elementType == %d OR elementType == %d) AND label == %@",
            XCUIElement.ElementType.button.rawValue, XCUIElement.ElementType.staticText.rawValue, name)).firstMatch
    }

    private func propertyValue(_ name: String, label: String) throws -> XCUIElement {
        let title = propertyTitle(name)
        try reveal(title)
        let candidates = app.descendants(matching: .any).matching(NSPredicate(
            format: "(elementType == %d OR elementType == %d) AND label == %@",
            XCUIElement.ElementType.button.rawValue, XCUIElement.ElementType.staticText.rawValue, label))
        try wait(timeout: 20, reason: "The original \(name) row did not render \(label)") {
            title.isHittable && candidates.allElementsBoundByIndex.contains {
                $0.isHittable && abs($0.frame.midY - title.frame.midY) < 22 && $0.frame.minX >= title.frame.maxX
            }
        }
        return try XCTUnwrap(candidates.allElementsBoundByIndex.first {
            $0.isHittable && abs($0.frame.midY - title.frame.midY) < 22 && $0.frame.minX >= title.frame.maxX
        })
    }

    private func expandSection(_ title: String) throws {
        guard !title.isEmpty, !expandedSections.contains(title) else { return }
        let header = app.buttons.matching(NSPredicate(format: "label == %@", title)).firstMatch
        guard header.exists else { return }
        try reveal(header)
        try require(header.isHittable, "The original Properties section is not hittable: " + title)
        header.tap()
        expandedSections.insert(title)
    }

    private func reveal(_ element: XCUIElement) throws {
        let deadline = Date().addingTimeInterval(20)
        var swipes = 0
        while Date() < deadline {
            if element.exists && element.isHittable { return }
            let scrolls = app.scrollViews.allElementsBoundByIndex.filter {
                $0.isHittable && $0.frame.height > 150 && $0.frame.width > 150
            }
            if scrolls.count == 1 && swipes < 4 {
                let scroll = scrolls[0]
                let viewport = scroll.frame.intersection(app.frame)
                if element.exists && element.frame.maxY <= viewport.minY {
                    scroll.swipeDown(); swipes += 1
                } else if !element.exists || element.frame.minY >= viewport.maxY {
                    scroll.swipeUp(); swipes += 1
                }
            }
            Thread.sleep(forTimeInterval: 0.1)
        }
        throw NSError(domain: "PinkhaWordUnlinkControl", code: 1,
                      userInfo: [NSLocalizedDescriptionKey: "The original control did not become hittable: " + element.debugDescription])
    }

    private func replaceSearch(_ search: XCUIElement, with value: String) throws {
        try require(search.exists && search.isHittable, "The actual editable text field is not hittable")
        let current = (search.value as? String).flatMap { $0 == search.placeholderValue ? nil : $0 } ?? ""
        search.tap()
        if !current.isEmpty {
            // Reuse the original native UI replacement gesture; tapping alone
            // does not establish that the caret is at the end of the field.
            search.typeKey("a", modifierFlags: .command)
            search.typeText(XCUIKeyboardKey.delete.rawValue)
        }
        search.typeText(value)
        try wait(timeout: 10, reason: "The original editable field did not contain the requested text") {
            search.value as? String == value
        }
    }

    private func documentName(_ role: String) throws -> String {
        let id = try XCTUnwrap(fixture.documents[role])
        let name = try XCTUnwrap(fixture.names[id])
        try require(!name.isEmpty, "The original prepared document name is empty")
        return name
    }

    private func tagName(_ role: String) -> String {
        "G02 " + role + " " + String((controller["TOKEN"] ?? "").prefix(8))
    }

    private func processID() throws -> Int {
        let text = app.debugDescription
        let expression = try NSRegularExpression(pattern: "\\A\\s*(?:Attributes:\\s*)?Application,\\s*0x[0-9a-fA-F]+,\\s*pid:\\s*([0-9]+)")
        let match = try XCTUnwrap(expression.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)))
        let digits = try XCTUnwrap(Range(match.range(at: 1), in: text))
        let value = try XCTUnwrap(Int(text[digits]))
        try require(value > 0, "The actual App process ID is invalid")
        return value
    }

    private func record(_ phase: String, fields: [String: Any]) throws {
        var receipt = fields
        receipt["schema"] = "pinkha-g02-word-ui-observation-v1"
        receipt["phase"] = phase
        receipt["spaceID"] = fixture.spaceId
        receipt["controller"] = controller
        receipt["evidenceScope"] = "OBSERVED_UI_ONLY_NATIVE_BASELINE_AND_POSTFLIGHT_SEPARATE"
        receipt["controllerProvenance"] = "CONTROLLER_OWNED_SIMULATOR_AFTER_ORIGINAL_NATIVE_PREPARATION"
        receipt["observedAtUTC"] = ISO8601DateFormatter().string(from: Date())
        let data = try JSONSerialization.data(withJSONObject: receipt, options: [.sortedKeys])
        let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
        attachment.name = "word-unlink-" + phase
        attachment.lifetime = .keepAlways
        add(attachment)
        attachState(phase)
    }

    private func attachState(_ phase: String) {
        let hierarchy = XCTAttachment(string: app.debugDescription)
        hierarchy.name = "word-unlink-" + phase + "-ax"
        hierarchy.lifetime = .keepAlways
        add(hierarchy)
        if app.state == .runningForeground {
            let screenshot = XCTAttachment(screenshot: app.screenshot())
            screenshot.name = "word-unlink-" + phase + "-visual"
            screenshot.lifetime = .keepAlways
            add(screenshot)
        }
    }

    private func wait(timeout: TimeInterval, reason: String, until condition: @escaping () -> Bool) throws {
        let expectation = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in condition() }, object: app)
        try require(XCTWaiter.wait(for: [expectation], timeout: timeout) == .completed && condition(), reason)
    }

    private func sha256(_ value: Data) -> String {
        SHA256.hash(data: value).map { String(format: "%02x", $0) }.joined()
    }

    private func isSHA256(_ value: String) -> Bool {
        value.range(of: "\\A[0-9a-f]{64}\\z", options: .regularExpression) != nil
    }

    private func require(_ condition: @autoclosure () throws -> Bool, _ reason: String) throws {
        guard try condition() else {
            throw NSError(domain: "PinkhaWordUnlinkAcceptance", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: reason])
        }
    }
}
