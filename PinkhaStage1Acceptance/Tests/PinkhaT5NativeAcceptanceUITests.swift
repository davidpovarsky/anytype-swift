import XCTest

/// Traverses the production Inspector and editor on the fresh native fixture.
/// Deep links establish ordinary document entry and reopen an unlinked Note;
/// every navigation claim from a related result uses its actual UI button.
@MainActor
final class PinkhaT5NativeAcceptanceUITests: XCTestCase {
    private struct Target: Decodable {
        let role: String
        let objectID: String
        let title: String
        let associationID: String
        let blockID: String?
        let blockText: String?
        let firstBlockID: String?
        let firstBlockText: String?
        let resultID: String
    }
    private struct PresentationProbe: Decodable {
        let objectID: String
        let blockID: String
        let text: String
    }
    private struct RetainedNote: Decodable {
        let objectID: String
        let blockID: String
        let actualText: String
    }
    private struct Fixture: Decodable {
        let protocolVersion: Int
        let token: String
        let appSourceSHA: String
        let runID: String
        let spaceID: String
        let providerID: String
        let canonicalReference: String
        let coverage: String
        let limitations: [String]
        let targets: [Target]
        let presentationProbe: PresentationProbe
    }
    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private let bodyPrefix = "pinkha.stage1.body."
    private let rowPrefix = "torah-inspector-related-row-"
    private var fixture: Fixture!
    private var observations: [[String: Any]] = []
    private var appLanguage: String { ProcessInfo.processInfo.environment["PINKHA_UI27_APP_LANGUAGE"] ?? "en" }

    override func setUpWithError() throws {
        continueAfterFailure = false
        let environment = ProcessInfo.processInfo.environment
        try require(environment["PINKHA_NATIVE_UI_DISPOSABLE"] == "1", "A fresh disposable native fixture is required")
        let language = environment["PINKHA_UI27_APP_LANGUAGE"]
        try require(language == "en" || language == "he", "Only the reviewed English/Hebrew selections are permitted")
        try require(language == "en" || environment["PINKHA_T5_UI_PRESENTATION_MODE"] == "R08",
                    "Hebrew requires the separately reported R08 selection")
        let raw = try XCTUnwrap(environment["PINKHA_T5_NATIVE_UI_FIXTURE_JSON"])
        fixture = try JSONDecoder().decode(Fixture.self, from: Data(raw.utf8))
        try require(fixture.protocolVersion == 1 && fixture.token == environment["PINKHA_T5_UI_TOKEN"], "Fixture attempt differs")
        try require(fixture.appSourceSHA == environment["PINKHA_T5_UI_APP_SHA"]
            && fixture.runID == environment["PINKHA_T5_UI_RUN_ID"], "Fixture source/run differs")
        try require(fixture.providerID == "sefaria" && fixture.canonicalReference == "Genesis 1:1", "Fixture source differs")
        try require(fixture.coverage == "indexedTargetsOnly" && fixture.limitations == ["indexFreshnessUnverified"],
                    "The fixture must retain its incomplete coverage disclosure")
        try require(Set(fixture.targets.map(\.role)) == ["page", "note", "writing", "block", "quote"]
            && Set(fixture.targets.map(\.objectID)).count == 5 && Set(fixture.targets.map(\.resultID)).count == 5,
                    "Five distinct native targets are required")
        app.launchEnvironment["PINKHA_STAGE1_ACCEPTANCE"] = "1"
        app.launchEnvironment["PINKHA_ACCEPTANCE_DOCUMENT_KIND"] = "pinkha"
        app.launchEnvironment["PINKHA_UI27_ROUTE_OBSERVATION"] = "1"
        app.launchArguments = ["-AppleLanguages", language == "he" ? "(he)" : "(en)",
                               "-AppleLocale", language == "he" ? "he_IL" : "en_US"]
    }

    func testCurrentSpaceRowsAndExactBlockNavigation() throws {
        try require(appLanguage == "en", "Core related-target acceptance retains its English selection")
        var status = "FAIL"
        defer { attachReceipt("related-targets", status: status) }
        try launch()
        for role in ["page", "note", "writing"] {
            let origin = try target(role)
            try enterObject(origin.objectID)
            try openRelatedDocuments()
            try requireRows(expected: baselineRows)
            try requirePartialCoverage()
            observations.append(["stage": "current-space-from-" + role,
                                 "originObjectID": origin.objectID, "actualRows": actualRows.sorted()])
            attachEvidence("t5-related-from-" + role)
            try closeInspector()
        }
        let origin = try target("writing")
        for role in ["block", "quote"] {
            let destination = try target(role)
            let blockID = try XCTUnwrap(destination.blockID)
            let text = try XCTUnwrap(destination.blockText)
            let firstID = try XCTUnwrap(destination.firstBlockID)
            let firstText = try XCTUnwrap(destination.firstBlockText)
            // Ordinary entry is a negative control. The target must really start
            // outside the viewport, so opening the correct document alone fails.
            try enterObject(destination.objectID)
            try requireBody(firstID, text: firstText, hittable: true)
            try require(!body(blockID).isHittable, "The distant target must be offscreen before block navigation")
            observations.append(["stage": role + "-control-offscreen", "objectID": destination.objectID,
                                 "blockID": blockID, "firstBlockID": firstID, "targetHittable": false])
            attachEvidence("t5-" + role + "-ordinary-entry-control")
            try enterObject(origin.objectID)
            try openRelatedDocuments()
            try requireRows(expected: baselineRows)
            let row = relatedRow(destination.resultID)
            try require(row.isHittable, "The intended native related result is not reachable")
            row.tap()
            try requireCurrentDocument(destination.objectID)
            try requireBody(blockID, text: text, hittable: true)
            observations.append(["stage": role + "-opened-from-inspector", "objectID": destination.objectID,
                                 "blockID": blockID, "resultID": destination.resultID,
                                 "targetHittable": body(blockID).isHittable, "actualText": body(blockID).value as? String ?? ""])
            attachEvidence("t5-" + role + "-exact-native-target")
        }
        status = "PASS"
    }

    func testAddNoteEditOpenUnlinkAndRetainAfterRelaunch() throws {
        try require(appLanguage == "en", "Core Note acceptance retains its English selection")
        var status = "FAIL"
        defer { attachReceipt("note-lifecycle", status: status) }
        try launch()
        let origin = try target("writing")
        try enterObject(origin.objectID)
        try openRelatedDocuments()
        try requireRows(expected: baselineRows)
        let add = app.buttons["torah-inspector-related-add-note"]
        try require(add.waitForExistence(timeout: 20) && add.isHittable && add.isEnabled, "The real Add note to source action is unavailable")
        try require(add.label == "Add note to source", "The source Note action has an ambiguous label")
        add.tap()
        let noteID = try waitForNewNoteEditor()
        let bodyText = "T5 Note edited through native UI " + fixture.token
        let editedBlockID = try typeNewBody(bodyText)
        try requireBody(editedBlockID, text: bodyText, hittable: true)
        observations.append(["stage": "note-created-and-edited", "objectID": noteID,
                             "blockID": editedBlockID, "actualText": body(editedBlockID).value as? String ?? ""])
        attachEvidence("t5-created-note-native-editor")
        try nativeBack(to: origin.objectID)
        try openRelatedDocuments()
        let noteRow = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND identifier CONTAINS %@", rowPrefix, noteID)).firstMatch
        try require(noteRow.waitForExistence(timeout: 45), "The UI-created Note did not join the canonical source results")
        let noteResultID = String(noteRow.identifier.dropFirst(rowPrefix.count))
        try require(!noteResultID.isEmpty, "The created Note result has no stable identity")
        let linkedRows = baselineRows.union([rowPrefix + noteResultID])
        try requireRows(expected: linkedRows)
        observations.append(["stage": "note-visible-in-current-space", "objectID": noteID,
                             "resultID": noteResultID, "actualRows": actualRows.sorted()])
        try require(noteRow.isHittable, "The created Note's result is not reachable")
        noteRow.tap()
        try requireCurrentDocument(noteID)
        try requireBody(editedBlockID, text: bodyText, hittable: true)
        observations.append(["stage": "note-opened-from-inspector", "objectID": noteID,
                             "resultID": noteResultID, "blockID": editedBlockID])
        attachEvidence("t5-note-opened-from-related-result")
        try nativeBack(to: origin.objectID)
        try openRelatedDocuments()
        try requireRows(expected: linkedRows)
        let unlinkRow = relatedRow(noteResultID)
        try require(unlinkRow.isHittable, "The Note result cannot expose its real context menu")
        unlinkRow.press(forDuration: 1.0)
        let unlink = app.buttons.matching(NSPredicate(format: "identifier == %@",
            "torah-inspector-related-unlink-" + noteResultID)).firstMatch
        try require(unlink.waitForExistence(timeout: 20) && unlink.isHittable, "The source unlink action is missing")
        try require(unlink.label == "Unlink source", "The menu must describe unlinking, not document deletion")
        attachEvidence("t5-note-unlink-menu")
        unlink.tap()
        try require(unlink.waitForNonExistence(timeout: 20), "The unlink menu did not dismiss")
        try require(unlinkRow.waitForNonExistence(timeout: 45), "The removed source relationship remained visible")
        try requireRows(expected: baselineRows)
        observations.append(["stage": "note-unlinked", "objectID": noteID, "actualRows": actualRows.sorted()])
        attachEvidence("t5-note-unlinked-current-results")
        try closeInspector()
        try launch()
        try enterObject(origin.objectID)
        try openRelatedDocuments()
        try requireRows(expected: baselineRows)
        observations.append(["stage": "unlinked-list-after-relaunch", "actualRows": actualRows.sorted()])
        attachEvidence("t5-source-results-after-relaunch")
        try closeInspector()
        // An unlinked Note is intentionally absent from this source's results.
        // Reopen that exact observed native object through ordinary navigation.
        try enterObject(noteID)
        try requireBody(editedBlockID, text: bodyText, hittable: true)
        let sourceChip = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND label CONTAINS %@",
            "torah-document-source-chip-", fixture.canonicalReference)).firstMatch
        try require(!sourceChip.exists, "The unlinked Note regained the canonical source after relaunch")
        body(editedBlockID).tap()
        try wait(for: body(editedBlockID), predicate: NSPredicate(format: "label CONTAINS %@", "first-responder-true"),
                 timeout: 20, message: "The retained Note is not editable")
        try require(app.keyboards.firstMatch.waitForExistence(timeout: 20), "The retained Note did not open the keyboard")
        observations.append(["stage": "note-retained-after-relaunch", "objectID": noteID,
                             "blockID": editedBlockID, "actualText": body(editedBlockID).value as? String ?? "",
                             "sourceChipExists": sourceChip.exists, "editable": true])
        attachEvidence("t5-unlinked-note-retained-and-editable")
        status = "PASS"
    }

    /// Read-only R08 extension. Appearance is set/read back by simctl outside the
    /// App; original screenshots still require visual review. AX is not VoiceOver.
    func testHebrewRelatedRowsLongTitlesAndReadOnlyNavigation() throws {
        let environment = ProcessInfo.processInfo.environment
        let appearance = try XCTUnwrap(environment["PINKHA_T5_UI_APPEARANCE"])
        try require(appLanguage == "he" && ["light", "dark"].contains(appearance), "Exact Hebrew appearance selection required")
        let scope = "r08-he-" + appearance
        var status = "FAIL"
        defer { attachReceipt(scope, status: status) }
        let raw = try XCTUnwrap(environment["PINKHA_T5_R08_RETAINED_NOTE_JSON"])
        let retained = try JSONDecoder().decode(RetainedNote.self, from: Data(raw.utf8))
        try require(!retained.objectID.isEmpty && !retained.blockID.isEmpty
                    && !fixture.targets.contains { $0.objectID == retained.objectID }, "The original core Note identity is required")
        try launch()
        let origin = try target("writing")
        try enterObject(origin.objectID)
        try openRelatedDocuments(associationID: origin.associationID)
        try requireRows(expected: baselineRows)
        try requirePartialCoverage()
        let add = app.buttons["torah-inspector-related-add-note"]
        try require(add.label == "הוסף הערה למקור" && add.isEnabled, "The actual source action is not localized to Hebrew")
        var rows: [[String: Any]] = []
        for destination in fixture.targets {
            let row = relatedRow(destination.resultID)
            try revealRelatedRow(row)
            try require(row.label.contains(destination.title) && row.isEnabled, "The actual accessibility label lost the complete native title")
            let frame = row.frame
            try require(frame.width >= 160 && frame.height >= 44 && frame.height <= 160,
                        "The native related row is not a compact reachable control at the fixed Large content size")
            rows.append(["role": destination.role, "resultID": destination.resultID,
                         "actualLabel": row.label, "hittable": row.isHittable, "enabled": row.isEnabled,
                         "frame": frameValue(frame)])
            if destination.role == "page" || destination.role == "writing" {
                try require(destination.title.count >= 160, "The actual native title does not exercise wrapping")
                attachEvidence("t5-" + scope + "-long-title-" + destination.role)
            }
        }
        observations.append(["stage": "r08-related-rows", "originObjectID": origin.objectID,
                             "actualRows": actualRows.sorted(), "rows": rows,
                             "addNoteLabel": add.label, "appFrame": frameValue(app.frame)])
        let page = try target("page")
        let row = relatedRow(page.resultID)
        try revealRelatedRow(row)
        row.tap()
        let probe = fixture.presentationProbe
        try require(probe.objectID == page.objectID, "The presentation probe belongs to another native Page")
        try requireCurrentDocument(page.objectID)
        try requireBody(probe.blockID, text: probe.text, hittable: true)
        let direction = body(probe.blockID).label
        let fields = Set(direction.split(separator: ";").map(String.init))
        try require(Set(["app-language-he", "swiftui-rtl", "navigation-rtl", "uikit-rtl", "content-rtl"]).isSubset(of: fields),
                    "Actual App/editor direction observations do not prove Hebrew RTL")
        observations.append(["stage": "r08-native-rtl-navigation", "objectID": page.objectID,
                             "blockID": probe.blockID, "resultID": page.resultID,
                             "actualText": body(probe.blockID).value as? String ?? "", "actualDirectionLabel": direction])
        attachEvidence("t5-" + scope + "-native-rtl-navigation")
        // The core-created Note is already unlinked. Ordinary navigation here
        // is a read-only preservation check, not a related-result navigation claim.
        try enterObject(retained.objectID)
        try requireBody(retained.blockID, text: retained.actualText, hittable: true)
        // This fresh core Note had exactly one source and the core unlinked it.
        // Hebrew source labels differ from the English canonical reference.
        let chips = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "torah-document-source-chip-"))
        try require(chips.count == 0, "R08 found a source link restored on the core Note")
        observations.append(["stage": "r08-retained-unlinked-note", "objectID": retained.objectID,
                             "blockID": retained.blockID, "actualText": body(retained.blockID).value as? String ?? "",
                             "sourceChipExists": chips.firstMatch.exists, "sourceChipCount": chips.count])
        attachEvidence("t5-" + scope + "-retained-unlinked-note")
        try enterObject(origin.objectID)
        try openRelatedDocuments(associationID: origin.associationID)
        try requireRows(expected: baselineRows)
        observations.append(["stage": "r08-related-rows-after-return", "originObjectID": origin.objectID,
                             "actualRows": actualRows.sorted()])
        status = "PASS"
    }

    private func frameValue(_ frame: CGRect) -> [String: Double] {
        ["x": Double(frame.minX), "y": Double(frame.minY), "width": Double(frame.width), "height": Double(frame.height)]
    }
    private func revealRelatedRow(_ row: XCUIElement) throws {
        let scroll = app.scrollViews.containing(NSPredicate(format: "elementType == %d AND identifier == %@",
            XCUIElement.ElementType.button.rawValue, row.identifier)).firstMatch
        try require(scroll.waitForExistence(timeout: 20), "The actual Inspector scroll container is missing")
        for _ in 0..<8 {
            let frame = row.frame
            let visible = scroll.frame.intersection(app.frame)
            if row.isHittable && frame.width > 0 && frame.height > 0
                && visible.insetBy(dx: -1, dy: -1).contains(frame) { return }
            if frame.minY < visible.minY { scroll.swipeDown() } else { scroll.swipeUp() }
        }
        throw NSError(domain: "PinkhaT5NativeUI", code: 2,
                      userInfo: [NSLocalizedDescriptionKey: "The real related row did not become fully visible after bounded scrolling"])
    }

    private var baselineRows: Set<String> { Set(fixture.targets.map { rowPrefix + $0.resultID }) }
    private var actualRows: Set<String> {
        Set(app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", rowPrefix)).allElementsBoundByIndex.map(\.identifier))
    }
    private func target(_ role: String) throws -> Target { try XCTUnwrap(fixture.targets.first { $0.role == role }) }
    private func relatedRow(_ id: String) -> XCUIElement {
        app.buttons.matching(NSPredicate(format: "identifier == %@", rowPrefix + id)).firstMatch
    }
    private func body(_ id: String) -> XCUIElement {
        app.textViews.matching(NSPredicate(format: "identifier == %@", bodyPrefix + id)).firstMatch
    }
    private func requireRows(expected: Set<String>) throws {
        let rows = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", rowPrefix))
        try require(!expected.isEmpty && rows.element(boundBy: expected.count - 1).waitForExistence(timeout: 45),
                    "The expected current-Space rows did not appear")
        try require(rows.count == expected.count && actualRows == expected,
                    "The actual current-Space rows differ or contain duplicates")
    }
    private func requirePartialCoverage() throws {
        let notice = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ AND label CONTAINS %@", "torah-inspector-related-documents-unavailable",
            appLanguage == "he" ? "מסמכים ובלוקים שנוספו לאינדקס במרחב זה; ייתכן שהתוצאות אינן מלאות."
                : "Indexed documents and blocks in this Space; results may be incomplete")).firstMatch
        try require(notice.waitForExistence(timeout: 20), "Expanded results lost their incomplete-coverage disclosure")
    }
    private func launch() throws {
        if app.state != .notRunning { app.terminate() }
        app.launch()
        let ready = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ OR label == %@ OR identifier == %@ OR label == %@ OR (elementType == %d AND (label == %@ OR label == %@))",
            "SpaceHub", "SpaceHub", "NewSpaceButton", "NewSpaceButton", XCUIElement.ElementType.button.rawValue, "More", "x24/More")).firstMatch
        try require(ready.waitForExistence(timeout: 120), "Native Home did not become ready")
    }
    private func enterObject(_ id: String) throws {
        var url = URLComponents()
        url.scheme = "anytype"
        url.host = "object"
        url.queryItems = [URLQueryItem(name: "spaceId", value: fixture.spaceID), URLQueryItem(name: "objectId", value: id)]
        XCUIDevice.shared.system.open(try XCTUnwrap(url.url))
        try requireCurrentDocument(id)
    }
    private func requireCurrentDocument(_ id: String) throws {
        let identifier = "pinkha-ui27-editor:\(fixture.spaceID):\(id)"
        let editors = app.descendants(matching: .any).matching(NSPredicate(format: "identifier == %@", identifier))
        try wait(for: editors.firstMatch, predicate: NSPredicate(format: "exists == true AND hittable == true"),
                 timeout: 45, message: "The native editor does not match the actual Space and object")
        try require(editors.count == 1, "Exactly one editor must match the actual Space and object")
    }
    private func openRelatedDocuments(associationID: String? = nil) throws {
        let chip = associationID.map { id in
            app.buttons.matching(NSPredicate(format: "identifier == %@", "torah-document-source-chip-" + id)).firstMatch
        }
            ?? app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND label CONTAINS %@",
                "torah-document-source-chip-", fixture.canonicalReference)).firstMatch
        try require(chip.waitForExistence(timeout: 30) && chip.isHittable, "The native canonical source chip is unavailable")
        chip.tap()
        let expand = app.buttons["torah-inspector-expand-medium"]
        if expand.waitForExistence(timeout: 10) { expand.tap() }
        let documents = app.buttons[appLanguage == "he" ? "במסמכים" : "In Documents"].firstMatch
        if !documents.exists || !documents.isHittable {
            let tools = app.buttons["torah-inspector-show-tools"]
            try require(tools.waitForExistence(timeout: 30) && tools.isHittable, "The existing Inspector tools are unavailable")
            tools.tap()
        }
        try require(documents.waitForExistence(timeout: 30) && documents.isHittable, "The real In Documents tab is unavailable")
        documents.tap()
        try require(app.buttons["torah-inspector-related-add-note"].waitForExistence(timeout: 30), "The related-document panel did not load")
    }
    private func closeInspector() throws { try app.dismissNativeTorahInspector() }
    private func nativeBack(to id: String) throws {
        let buttons = app.buttons.matching(NSPredicate(format: "label == %@", "Back")).allElementsBoundByIndex.filter(\.isHittable)
        try require(buttons.count == 1, "Exactly one existing native Back control is required")
        try XCTUnwrap(buttons.first).tap()
        try requireCurrentDocument(id)
    }
    private func waitForNewNoteEditor() throws -> String {
        let prefix = "pinkha-ui27-editor:\(fixture.spaceID):"
        let original = fixture.targets.map { prefix + $0.objectID }
        let editors = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND NOT (identifier IN %@)", prefix, original))
        try wait(for: editors.firstMatch, predicate: NSPredicate(format: "exists == true AND hittable == true"),
                 timeout: 45, message: "The real Add Note action did not open a new editor")
        try require(editors.count == 1, "The Note action opened ambiguous native editor identities")
        let actual = String(editors.firstMatch.identifier.dropFirst(prefix.count))
        try require(!actual.isEmpty, "The new native Note has no identity")
        return actual
    }
    private func typeNewBody(_ text: String) throws -> String {
        let empty = app.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND value == %@", bodyPrefix, "")).firstMatch
        if empty.exists && empty.isHittable {
            empty.tap()
        } else {
            let editor = app.collectionViews.containing(.button, identifier: "torah-document-sources-add").firstMatch
            try require(editor.waitForExistence(timeout: 20), "The native Note editor collection is unavailable")
            let bottom = editor.cells.allElementsBoundByIndex.map { $0.frame.maxY }.max() ?? editor.frame.minY
            let keyboard = app.keyboards.firstMatch
            let visibleBottom = keyboard.exists ? min(editor.frame.maxY, keyboard.frame.minY) : editor.frame.maxY
            try require(visibleBottom - bottom > 24, "No visible native trailing-block insertion area")
            editor.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: editor.frame.width * 0.5,
                dy: bottom + (visibleBottom - bottom) * 0.5 - editor.frame.minY)).tap()
        }
        let focused = app.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND label CONTAINS %@ AND label CONTAINS %@",
            bodyPrefix, "first-responder-true", "text-empty-true")).firstMatch
        try require(focused.waitForExistence(timeout: 20), "Native input did not focus an empty Note block")
        focused.typeText(text)
        let typed = app.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND value == %@", bodyPrefix, text)).firstMatch
        try require(typed.waitForExistence(timeout: 20), "Real typing did not create the Note body")
        let id = String(typed.identifier.dropFirst(bodyPrefix.count))
        try require(!id.isEmpty, "The edited Note block has no native identity")
        return id
    }
    private func requireBody(_ id: String, text: String, hittable: Bool) throws {
        let predicate = NSPredicate(format: "exists == true AND value == %@", text)
        try wait(for: body(id), predicate: predicate, timeout: 30, message: "The exact native block/text is missing")
        if hittable {
            try wait(for: body(id), predicate: NSPredicate(format: "hittable == true"),
                     timeout: 20, message: "The exact native block is outside the visible editor")
        }
    }
    private func wait(for element: XCUIElement, predicate: NSPredicate, timeout: TimeInterval, message: String) throws {
        let expectation = XCTNSPredicateExpectation(predicate: predicate, object: element)
        try require(XCTWaiter.wait(for: [expectation], timeout: timeout) == .completed, message)
    }
    nonisolated private func require(_ condition: Bool, _ message: String) throws {
        guard condition else { throw NSError(domain: "PinkhaT5NativeUI", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
    }
    private func attachEvidence(_ name: String) {
        let tree = XCTAttachment(string: app.debugDescription)
        tree.name = name + "-accessibility"
        tree.lifetime = .keepAlways
        add(tree)
        if app.state == .runningForeground {
            let screenshot = XCTAttachment(screenshot: app.screenshot())
            screenshot.name = name
            screenshot.lifetime = .keepAlways
            add(screenshot)
        }
    }
    private func attachReceipt(_ name: String, status: String) {
        attachEvidence("t5-" + name + "-final")
        var receipt: [String: Any] = ["protocolVersion": 1, "status": status, "scope": name,
            "token": fixture?.token ?? "", "appSourceSHA": fixture?.appSourceSHA ?? "", "runID": fixture?.runID ?? "",
            "spaceID": fixture?.spaceID ?? "", "observations": observations,
            "coverage": "indexedTargetsOnly", "productLookupFlag": "OFF", "physicalDeviceAccepted": false]
        if name.hasPrefix("r08-") {
            receipt["requestedAppLanguage"] = appLanguage
            receipt["requestedAppearance"] = ProcessInfo.processInfo.environment["PINKHA_T5_UI_APPEARANCE"] ?? ""
            receipt["voiceOverStatus"] = "NOT_RUN"
            receipt["visualReviewStatus"] = "PENDING"
            receipt["dynamicTypeScope"] = "fixed-large-only"
        }
        if let data = try? JSONSerialization.data(withJSONObject: receipt, options: [.sortedKeys]) {
            let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
            attachment.name = "t5-native-ui-" + name + "-receipt"
            attachment.lifetime = .keepAlways
            add(attachment)
        }
    }
}
