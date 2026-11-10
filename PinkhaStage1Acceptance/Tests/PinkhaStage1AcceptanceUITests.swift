import XCTest

/// Drives the original application against the custom Heart. Its fixture is
/// produced by the real native API suite in a freshly created simulator.
@MainActor
final class PinkhaNativeDerivedAcceptanceUITests: XCTestCase {
    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private var fixture: NativeDerivedFixture!

    override func setUpWithError() throws {
        continueAfterFailure = false
        let env = ProcessInfo.processInfo.environment
        XCTAssertEqual(env["PINKHA_NATIVE_UI_DISPOSABLE"], "1")
        guard env["PINKHA_NATIVE_UI_DISPOSABLE"] == "1" else {
            throw NSError(domain: "NativeDerivedDisposableFixtureRequired", code: 1)
        }
        fixture = try JSONDecoder().decode(NativeDerivedFixture.self, from: Data(try XCTUnwrap(env["PINKHA_NATIVE_UI_FIXTURE_JSON"]).utf8))
        XCTAssertEqual(fixture.documents.count, 3)
        XCTAssertEqual(Set(fixture.documents.values).count, 3)
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
    }

    func testNativePropertiesPickerChipsSetMembershipAndRelaunch() throws {
        for role in ["chiddush", "article", "research"] {
            let id = try XCTUnwrap(fixture.documents[role])
            try openProperties(id)
            for name in fixture.nativeProperties { XCTAssertTrue(propertyTitle(name).waitForExistence(timeout: 15)) }
            XCTAssertFalse(app.buttons["torah-property-ref"].exists, "The old display-only Properties row must not replace the original native row")
            XCTAssertFalse(app.staticTexts["הקשר תורני"].exists)
            try selectNativeProperty("מקור/ות", query: fixture.sourceQuery)
            XCTAssertTrue(app.staticTexts[fixture.sourceLabel].waitForExistence(timeout: 20))
            try selectNativeProperty("נושא", query: fixture.topicQuery)
            XCTAssertTrue(app.staticTexts[fixture.topicLabel].waitForExistence(timeout: 20))
            try selectNativeProperty("מילה / ערך", query: fixture.wordQuery)
            let wordLabel = try nativeValueText("מילה / ערך")
            screenshot("native-properties-\(role)-three-values")
            app.terminate()
            try openProperties(id)
            XCTAssertTrue(app.staticTexts[fixture.sourceLabel].waitForExistence(timeout: 20))
            XCTAssertTrue(app.staticTexts[fixture.topicLabel].waitForExistence(timeout: 20))
            XCTAssertEqual(try nativeValueText("מילה / ערך"), wordLabel)
            XCTAssertFalse(app.staticTexts.matching(NSPredicate(format: "label CONTAINS %@", "providerID")).firstMatch.exists)
            screenshot("native-properties-\(role)-relaunch")
            app.terminate()
        }
        for (role, typeId) in fixture.types {
            try openProperties(typeId)
            for name in fixture.nativeProperties { XCTAssertTrue(propertyTitle(name).waitForExistence(timeout: 15)) }
            screenshot("native-original-type-editor-\(role)")
            app.terminate()
        }
        try openProperties(fixture.manySourcesDocument)
        XCTAssertTrue(app.staticTexts["+11"].waitForExistence(timeout: 15))
        screenshot("native-original-property-twelve-source-chips")
        app.terminate()
        try open(fixture.setId)
        assertSetMembers(present: true)
        try enableNativeColumns()
        app.terminate()
        try open(fixture.setId)
        assertSetMembers(present: true)
        for name in fixture.nativeProperties { XCTAssertTrue(setTable.staticTexts[name].waitForExistence(timeout: 20)) }
        XCTAssertTrue(setTable.staticTexts[fixture.sourceLabel].firstMatch.waitForExistence(timeout: 20))
        XCTAssertTrue(setTable.staticTexts[fixture.topicLabel].firstMatch.exists)
        screenshot("native-set-three-live-members")
        // Change only the native Set predicate via its actual Torah picker.
        // None of the three documents links Genesis 1:2, so all must disappear.
        try replaceSourceFilter(query: "Genesis 1:2")
        app.terminate()
        try open(fixture.setId)
        assertSetMembers(present: false)
        screenshot("native-set-alternate-filter-empty")
        try replaceSourceFilter(query: fixture.sourceQuery)
        app.terminate()
        try open(fixture.setId)
        assertSetMembers(present: true)
        screenshot("native-set-members-after-relaunch")
    }

    func testSourceHeaderSelectionAndOverflow() throws {
        try open(fixture.manySourcesDocument)
        let addSource = app.buttons["torah-document-sources-add"].firstMatch
        XCTAssertTrue(addSource.waitForExistence(timeout: 20))
        XCTAssertEqual(addSource.value as? String, "compact-icon")
        addSource.tap()
        let search = app.textFields.matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@", "torah-sources-search-sheet", "torah-sources-search-field"
        )).firstMatch
        XCTAssertTrue(search.waitForExistence(timeout: 20), "The compact + must open the existing source search")
        XCTAssertTrue(app.staticTexts["Document links"].firstMatch.waitForExistence(timeout: 15))
        screenshot("native-source-header-compact-add-opens-document-search")
        app.terminate()
        try open(fixture.manySourcesDocument)
        let overflow = app.buttons["torah-document-sources-more"].firstMatch
        XCTAssertTrue(overflow.waitForExistence(timeout: 20)); overflow.tap()
        screenshot("native-source-header-overflow-and-separate-add")
        app.terminate()
    }

    func testUniversalPageNoteCustomPropertiesAndMixedSet() throws {
        for role in ["page", "note", "custom"] {
            let id = try XCTUnwrap(fixture.universalDocuments[role])
            try open(id)
            XCTAssertFalse(app.buttons["torah-document-sources-add"].exists)
            try openProperties(id, expectsSources: false)
            for name in fixture.nativeProperties { XCTAssertFalse(propertyTitle(name).exists) }
            screenshot("universal-blank-" + role)
            for name in fixture.nativeProperties {
                let add = app.buttons["torah-object-add-property"].firstMatch
                XCTAssertTrue(add.waitForExistence(timeout: 20)); add.tap()
                let existing = propertyTitle(name)
                XCTAssertTrue(existing.waitForExistence(timeout: 20)); existing.tap()
                XCTAssertTrue(add.waitForExistence(timeout: 20))
                XCTAssertTrue(propertyTitle(name).waitForExistence(timeout: 20))
            }
            screenshot("universal-empty-native-rows-" + role)
            try selectNativeProperty("מקור/ות", query: fixture.sourceQuery)
            try selectNativeProperty("נושא", query: fixture.topicQuery)
            try selectNativeProperty("מילה / ערך", query: fixture.wordQuery)
            screenshot("universal-canonical-values-" + role)
            let tree = XCTAttachment(string: app.debugDescription)
            tree.name = "universal-property-accessibility-" + role
            tree.lifetime = .keepAlways; add(tree)
            app.terminate()
            try openProperties(id)
            XCTAssertTrue(app.staticTexts[fixture.sourceLabel].waitForExistence(timeout: 20))
            screenshot("universal-offline-reopen-" + role)
            app.terminate()
            try open(id)
            let headerAdd = app.buttons["torah-document-sources-add"].firstMatch
            XCTAssertTrue(headerAdd.waitForExistence(timeout: 20))
            XCTAssertEqual(headerAdd.value as? String, "compact-icon")
            screenshot("universal-selected-source-header-" + role)
            app.terminate()
        }
        for role in ["page", "note", "custom"] {
            try openProperties(try XCTUnwrap(fixture.universalTypes[role]), expectsSources: false)
            let add = app.buttons["torah-type-add-property"].firstMatch
            XCTAssertTrue(add.waitForExistence(timeout: 20)); add.tap()
            for name in fixture.nativeProperties { XCTAssertTrue(propertyTitle(name).waitForExistence(timeout: 20)) }
            screenshot("universal-native-Type-picker-" + role)
            propertyTitle("מקור/ות").tap()
            XCTAssertTrue(add.waitForExistence(timeout: 20))
            app.terminate()
        }
        try open(fixture.universalSetId)
        try enableNativeColumns()
        app.terminate()
        try open(fixture.universalSetId)
        XCTAssertTrue(setTable.waitForExistence(timeout: 30))
        for role in ["page", "note", "custom"] {
            XCTAssertTrue(setTable.staticTexts["Universal \(role) blank"].firstMatch.waitForExistence(timeout: 30))
        }
        screenshot("universal-mixed-native-filter-membership")
    }

    private var setTable: XCUIElement {
        app.descendants(matching: .any).matching(identifier: "set-table").firstMatch
    }

    private func assertSetMembers(present: Bool) {
        XCTAssertTrue(setTable.waitForExistence(timeout: 30))
        for title in fixture.names.values {
            let row = setTable.staticTexts[title].firstMatch
            if present { XCTAssertTrue(row.waitForExistence(timeout: 30), "Native Set omitted \(title)") }
            else { XCTAssertTrue(row.waitForNonExistence(timeout: 30), "Native Set included a nonmatching document") }
        }
    }

    private func openSetSettings(_ section: String) {
        let settings = app.buttons["set-view-settings"].firstMatch
        XCTAssertTrue(settings.waitForExistence(timeout: 15)); settings.tap()
        let row = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", section)).firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 15)); row.tap()
    }

    private func enableNativeColumns() throws {
        openSetSettings("Fields")
        for name in fixture.nativeProperties {
            let toggle = app.switches[name].firstMatch
            XCTAssertTrue(toggle.waitForExistence(timeout: 15))
            if toggle.value as? String == "0" { toggle.tap() }
            XCTAssertEqual(toggle.value as? String, "1")
        }
        screenshot("native-set-original-fields-switches")
    }

    private func replaceSourceFilter(query: String) throws {
        openSetSettings("Filters")
        let source = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", "מקור/ות")).firstMatch
        XCTAssertTrue(source.waitForExistence(timeout: 15)); source.tap()
        let search = app.textFields.matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@", "torah-native-set-filter-picker", "torah-sources-search-field"
        )).firstMatch
        XCTAssertTrue(search.waitForExistence(timeout: 15))
        let selected = app.buttons["torah-native-filter-selected-value"].firstMatch
        XCTAssertTrue(selected.waitForExistence(timeout: 15)); selected.tap()
        XCTAssertTrue(selected.waitForNonExistence(timeout: 10))
        search.tap(); search.typeText(query)
        let result = app.buttons[query].firstMatch
        XCTAssertTrue(result.waitForExistence(timeout: 45)); result.tap()
        XCTAssertTrue(selected.waitForExistence(timeout: 20))
        XCTAssertFalse(app.buttons["Link to document"].exists)
        screenshot("native-set-filter-selection-\(query)")
        app.buttons["torah-native-filter-apply"].tap()
        XCTAssertTrue(search.waitForNonExistence(timeout: 15))
    }

    private func open(_ id: String) throws {
        if app.state == .notRunning { app.launch() }
        var url = URLComponents()
        url.scheme = "anytype"; url.host = "object"
        url.queryItems = [URLQueryItem(name: "objectId", value: id), URLQueryItem(name: "spaceId", value: fixture.spaceId)]
        app.open(try XCTUnwrap(url.url))
        XCTAssertTrue(app.buttons["More"].firstMatch.waitForExistence(timeout: 45))
    }

    private func openProperties(_ id: String, expectsSources: Bool = true) throws {
        try open(id)
        app.buttons["More"].firstMatch.tap()
        let button = app.buttons["Properties"].firstMatch
        XCTAssertTrue(button.waitForExistence(timeout: 15)); button.tap()
        if expectsSources { XCTAssertTrue(propertyTitle("מקור/ות").waitForExistence(timeout: 20)) }
    }

    private func propertyTitle(_ name: String) -> XCUIElement {
        // One lazy query follows asynchronous sheet insertion without freezing
        // the element type before the original Menu row has appeared.
        app.descendants(matching: .any).matching(NSPredicate(
            format: "(elementType == %d OR elementType == %d) AND label == %@",
            XCUIElement.ElementType.button.rawValue, XCUIElement.ElementType.staticText.rawValue, name
        )).firstMatch
    }

    private func selectNativeProperty(_ name: String, query: String) throws {
        let title = propertyTitle(name)
        XCTAssertTrue(title.exists)
        // The original row has a name Menu and a separate value Button. Tap the
        // value area using its real name-column geometry, without adding a test
        // shortcut or altering the original Anytype row implementation.
        let x = min(app.frame.maxX - 24, title.frame.maxX + 28)
        app.coordinate(withNormalizedOffset: .zero)
            .withOffset(CGVector(dx: x, dy: title.frame.midY)).tap()
        // SwiftUI propagates the presentation identifier to the actual field.
        let search = app.textFields.matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@", "torah-native-property-editor", "torah-sources-search-field"
        )).firstMatch
        XCTAssertTrue(search.waitForExistence(timeout: 10)); search.tap(); search.typeText(query)
        let link = app.buttons["Link to document"].firstMatch
        XCTAssertTrue(link.waitForExistence(timeout: 45)); link.tap()
        XCTAssertTrue(app.buttons["Remove link"].firstMatch.waitForExistence(timeout: 30))
        // Dismiss the original iPad value popover through its outside region.
        app.coordinate(withNormalizedOffset: .zero)
            .withOffset(CGVector(dx: 16, dy: search.frame.midY)).tap()
        XCTAssertTrue(search.waitForNonExistence(timeout: 15))
        XCTAssertTrue(propertyTitle(name).exists)
    }

    private func screenshot(_ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }

    private func nativeValueText(_ name: String) throws -> String {
        let title = propertyTitle(name)
        let deadline = Date().addingTimeInterval(20)
        repeat {
            let values = app.staticTexts.allElementsBoundByIndex.filter {
                abs($0.frame.midY - title.frame.midY) < 22 && $0.frame.minX >= title.frame.maxX &&
                !$0.label.isEmpty && $0.label != name && $0.label != "Add"
            }
            if let value = values.first?.label {
                XCTAssertFalse(value.contains("torah1|")); return value
            }
            Thread.sleep(forTimeInterval: 0.1)
        } while Date() < deadline
        XCTFail("The original native Property row has no human value: \(name)")
        throw NSError(domain: "NativeDerivedMissingChip", code: 2)
    }
}

private struct NativeDerivedFixture: Decodable {
    let spaceId: String
    let universalDocuments: [String: String]
    let universalTypes: [String: String]
    let universalSetId: String
    let documents: [String: String]
    let names: [String: String]
    let types: [String: String]
    let manySourcesDocument: String
    let setId: String
    let nativeProperties: [String]
    let sourceQuery: String
    let sourceLabel: String
    let topicQuery: String
    let topicLabel: String
    let wordQuery: String
}

@MainActor
final class PinkhaTorahPropertiesAcceptanceUITests: XCTestCase {
    private let app = XCUIApplication()
    private var spaceID = ""
    private var objectIDs: [String] = []
    private var sourceQuery = ""
    private var sourceLabel = ""
    private var topicQuery = ""
    private var topicLabel = ""
    private var nativePropertyLabels = [String: [String]]()

    override func setUpWithError() throws {
        continueAfterFailure = false
        let environment = ProcessInfo.processInfo.environment
        XCTAssertEqual(environment["PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED"], "1")
        guard environment["PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED"] == "1" else {
            throw NSError(domain: "PinkhaTorahPropertiesAcceptance", code: 1)
        }
        spaceID = try XCTUnwrap(environment["PINKHA_PROPERTIES_SPACE_ID"])
        objectIDs = try ["CHIDDUSH", "ARTICLE", "RESEARCH"].map {
            try XCTUnwrap(environment["PINKHA_PROPERTIES_\($0)_ID"])
        }
        sourceQuery = try XCTUnwrap(environment["PINKHA_PROPERTIES_SOURCE_QUERY"])
        sourceLabel = try XCTUnwrap(environment["PINKHA_PROPERTIES_SOURCE_LABEL"])
        topicQuery = try XCTUnwrap(environment["PINKHA_PROPERTIES_TOPIC_QUERY"])
        topicLabel = try XCTUnwrap(environment["PINKHA_PROPERTIES_TOPIC_LABEL"])
        let labelsJSON = try XCTUnwrap(environment["PINKHA_PROPERTIES_NATIVE_PROPERTY_LABELS"])
        nativePropertyLabels = try JSONDecoder().decode([String: [String]].self, from: Data(labelsJSON.utf8))
        XCTAssertFalse(spaceID.isEmpty)
        XCTAssertEqual(Set(objectIDs).count, 3)
        app.launchArguments += ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
    }

    func testOriginalPropertiesCanonicalLinkUnlinkAndRelaunchForAllWritingTypes() throws {
        for objectID in objectIDs {
            try openProperties(objectID: objectID)
            assertNativePropertiesPresent(objectID: objectID)
            let source = app.buttons["torah-property-ref"]
            let topic = app.buttons["torah-property-topic"]
            XCTAssertTrue(source.waitForExistence(timeout: 15))
            XCTAssertTrue(topic.exists)
            XCTAssertEqual(source.value as? String, "")
            XCTAssertEqual(topic.value as? String, "")

            try openPicker(row: topic, category: "Topics")
            try link(query: topicQuery)
            dismissPicker()
            expectValue(topicLabel, on: topic)
            XCTAssertEqual(source.value as? String, "")

            try openPicker(row: source, category: "Sources")
            try link(query: sourceQuery)
            dismissPicker()
            expectValue(sourceLabel, on: source)
            expectValue(topicLabel, on: topic)
            attachPropertiesScreenshot(name: "\(objectID)-linked")

            app.terminate()
            try openProperties(objectID: objectID)
            expectValue(sourceLabel, on: source)
            expectValue(topicLabel, on: topic)
            assertNativePropertiesPresent(objectID: objectID)

            try openPicker(row: source, category: "Sources")
            let remove = app.buttons["Remove link"].firstMatch
            XCTAssertTrue(remove.waitForExistence(timeout: 10))
            remove.tap()
            XCTAssertTrue(remove.waitForNonExistence(timeout: 15))
            dismissPicker()
            expectValue("", on: source)
            expectValue(topicLabel, on: topic)

            try openPicker(row: topic, category: "Topics")
            let removeTopic = app.buttons["Remove link"].firstMatch
            XCTAssertTrue(removeTopic.waitForExistence(timeout: 10))
            removeTopic.tap()
            XCTAssertTrue(removeTopic.waitForNonExistence(timeout: 15))
            dismissPicker()
            expectValue("", on: topic)
            attachPropertiesScreenshot(name: "\(objectID)-unlinked")
        }
    }

    private func openProperties(objectID: String) throws {
        if app.state == .notRunning { app.launch() }
        var components = URLComponents()
        components.scheme = "anytype"
        components.host = "object"
        components.queryItems = [URLQueryItem(name: "objectId", value: objectID), URLQueryItem(name: "spaceId", value: spaceID)]
        app.open(try XCTUnwrap(components.url))
        let settings = app.buttons["More"].firstMatch
        XCTAssertTrue(settings.waitForExistence(timeout: 30))
        settings.tap()
        let properties = app.buttons["Properties"].firstMatch
        XCTAssertTrue(properties.waitForExistence(timeout: 10))
        properties.tap()
        XCTAssertTrue(app.buttons["torah-property-ref"].waitForExistence(timeout: 15))
    }

    private func openPicker(row: XCUIElement, category: String) throws {
        XCTAssertTrue(row.isEnabled)
        row.tap()
        let segment = app.segmentedControls.buttons[category]
        XCTAssertTrue(segment.waitForExistence(timeout: 10))
        XCTAssertEqual(segment.value as? String, "1")
        for title in ["Sources", "Topics", "Words"] {
            XCTAssertTrue(app.segmentedControls.buttons[title].exists)
        }
        XCTAssertEqual(app.textFields.firstMatch.value as? String, "Search Sefaria")
    }

    private func link(query: String) throws {
        let search = app.textFields.firstMatch
        search.tap()
        search.typeText(query)
        let link = app.buttons["Link to document"].firstMatch
        XCTAssertTrue(link.waitForExistence(timeout: 30))
        link.tap()
        XCTAssertTrue(app.buttons["Remove link"].firstMatch.waitForExistence(timeout: 30))
    }

    private func dismissPicker() {
        let picker = app.otherElements["torah-sources-search-sheet"].firstMatch
        XCTAssertTrue(picker.exists)
        picker.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.02))
            .press(forDuration: 0.05, thenDragTo: picker.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.95)))
        XCTAssertTrue(app.segmentedControls.firstMatch.waitForNonExistence(timeout: 15))
    }

    private func expectValue(_ value: String, on element: XCUIElement) {
        expectation(for: NSPredicate(format: "value == %@", value), evaluatedWith: element)
        waitForExpectations(timeout: 20)
    }

    private func assertNativePropertiesPresent(objectID: String) {
        let labels = nativePropertyLabels[objectID] ?? []
        XCTAssertFalse(labels.isEmpty)
        for label in labels { XCTAssertTrue(app.staticTexts[label].exists, "Original native property disappeared: \(label)") }
        XCTAssertFalse(app.staticTexts["הקשר תורני"].exists)
    }

    private func attachPropertiesScreenshot(name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}

@MainActor
final class PinkhaStage1AcceptanceUITests: XCTestCase {
    private enum DocumentKind: String, CaseIterable, Hashable {
        case pinkha
        case note
        case page
    }

    private let app = XCUIApplication()
    private var fixtureSpaceID = ""
    private var fixtureObjectIDs: [DocumentKind: String] = [:]
    private var expectsRTL: Bool {
        ProcessInfo.processInfo.environment["PINKHA_ACCEPTANCE_DIRECTION"] != "ltr"
    }
    private var appLanguage: String { expectsRTL ? "he" : "en" }
    private var deviceLanguage: String {
        ProcessInfo.processInfo.environment["PINKHA_ACCEPTANCE_DEVICE_LANGUAGE"]
            ?? (expectsRTL ? "en" : "he")
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
        let environment = ProcessInfo.processInfo.environment
        fixtureSpaceID = try XCTUnwrap(environment["PINKHA_ACCEPTANCE_SPACE_ID"], "Native fixture preparation must supply the disposable Space")
        let fixtureKeys: [(DocumentKind, String)] = [
            (.pinkha, "PINKHA_ACCEPTANCE_PINKHA_ID"),
            (.note, "PINKHA_ACCEPTANCE_NOTE_ID"),
            (.page, "PINKHA_ACCEPTANCE_PAGE_ID")
        ]
        for (kind, key) in fixtureKeys {
            fixtureObjectIDs[kind] = try XCTUnwrap(environment[key], "Missing prepared native \(kind.rawValue) fixture")
        }
        XCTAssertFalse(fixtureSpaceID.isEmpty)
        XCTAssertEqual(Set(fixtureObjectIDs.values).count, 3)
        app.launchEnvironment["PINKHA_STAGE1_ACCEPTANCE"] = "1"
        app.launchEnvironment["PINKHA_ACCEPTANCE_DEVICE_LANGUAGE"] = deviceLanguage
        app.launchArguments += [
            "-AppleLanguages", "(\(appLanguage))",
            "-AppleLocale", expectsRTL ? "he_IL" : "en_US"
        ]
    }

    func testAppWideDirectionPersistenceAndInteractiveBack() throws {
        XCTAssertNotEqual(
            appLanguage,
            deviceLanguage,
            "Acceptance must exercise mismatched app and device languages"
        )

        launch(document: .pinkha)

        for kind in DocumentKind.allCases {
            if kind != .pinkha {
                launch(document: kind)
            }
            try exerciseDocument(kind)
        }
    }

    func testMultiBlockEnterCreationAndTypingLifecycle() throws {
        XCTAssertNotEqual(
            appLanguage,
            deviceLanguage,
            "Acceptance must exercise mismatched app and device languages"
        )

        launch(document: .pinkha)

        for kind in DocumentKind.allCases {
            if kind != .pinkha {
                launch(document: kind)
            }
            try exerciseMultiBlockEnterLifecycle(kind)
        }
    }

    func testDocumentSourcesEntryOpensExistingSearch() throws {
        launch(document: .pinkha)
        for kind in DocumentKind.allCases {
            if kind != .pinkha { launch(document: kind) }
            openDocumentIfNeeded(kind)
            _ = editableBody()
            let add = app.buttons["torah-document-sources-add"]
            XCTAssertTrue(add.waitForExistence(timeout: 20))
            XCTAssertEqual(app.buttons.matching(identifier: "torah-document-sources-add").count, 1)
            XCTAssertTrue(add.isHittable)
            attachScreenshot(named: "\(directionName)-\(kind.rawValue)-sources-entry")
            add.tap()
            // The native sheet's identifier propagates to its descendants in SwiftUI.
            // Match the actual editable field within that presentation, not an overridden ID.
            let field = app.textFields.matching(identifier: "torah-sources-search-sheet").firstMatch
            XCTAssertTrue(field.waitForExistence(timeout: 20), "Sources must open the existing document search presenter")
            XCTAssertTrue(app.staticTexts.matching(NSPredicate(
                format: "identifier == %@ AND label == %@", "torah-sources-search-sheet",
                expectsRTL ? "קישורים במסמך" : "Document links"
            )).firstMatch.exists, "The opened search must explicitly show document scope")
            attachScreenshot(named: "\(directionName)-\(kind.rawValue)-sources-search")
        }
    }

    private func exerciseMultiBlockEnterLifecycle(_ kind: DocumentKind) throws {
        openDocumentIfNeeded(kind)
        var target = editableBody(startNewTrailingBlock: true)
        target.tap()

        let token = UUID().uuidString.prefix(8)
        let lines = (1...5).map { index in
            let usesHebrew = expectsRTL ? !index.isMultiple(of: 2) : index.isMultiple(of: 2)
            return usesHebrew ? "שורה \(index) בדיקה \(token)" : "Line \(index) test \(token)"
        }
        var typedBlockIDs = Set<String>()
        for (index, line) in lines.enumerated() {
            target.typeText(line)
            let typedRow = editorBody(containing: line)
            XCTAssertTrue(typedRow.waitForExistence(timeout: 20), "Entered line missing: \(line)")
            XCTAssertTrue(typedBlockIDs.insert(typedRow.identifier).inserted, "Enter reused a previously typed block")
            assertRuntimeDirection(on: typedRow, document: kind)
            if index > 0 {
                let direction = expectsRTL ? "rtl" : "ltr"
                expectation(for: NSPredicate(format: "label CONTAINS %@", "accepted-first-insertion-\(direction)"), evaluatedWith: typedRow)
                waitForExpectations(timeout: 20)
            }

            typedRow.typeText("\n")
            target = app.textViews.matching(NSPredicate(
                format: "identifier BEGINSWITH %@ AND NOT (identifier IN %@) AND label CONTAINS %@",
                "pinkha.stage1.body.",
                Array(typedBlockIDs),
                "first-responder-true"
            )).firstMatch
            XCTAssertTrue(target.waitForExistence(timeout: 20), "Enter did not focus a distinct next block")
            assertRuntimeDirection(on: target, document: kind)
            let direction = expectsRTL ? "rtl" : "ltr"
            let side = expectsRTL ? "right" : "left"
            for fragment in ["text-empty-true", "typing-direction-\(direction)", "caret-side-\(side)"] {
                expectation(for: NSPredicate(format: "label CONTAINS %@", fragment), evaluatedWith: target)
            }
            waitForExpectations(timeout: 20)
            attachScreenshot(named: "\(directionName)-\(kind.rawValue)-enter-\(typedBlockIDs.count)")
        }
        XCTAssertEqual(typedBlockIDs.count, 5)

        launch(document: kind)
        openDocumentIfNeeded(kind)
        var reopenedIDs = Set<String>()
        for line in lines {
            let row = editorBody(containing: line)
            XCTAssertTrue(row.waitForExistence(timeout: 60), "Line did not survive relaunch: \(line)")
            XCTAssertTrue(reopenedIDs.insert(row.identifier).inserted)
            assertRuntimeDirection(on: row, document: kind)
        }
        XCTAssertEqual(reopenedIDs, typedBlockIDs, "Enter-created block identities changed after relaunch")
        attachScreenshot(named: "\(directionName)-\(kind.rawValue)-multiblock-reopened")
    }

    private func editorBody(containing text: String) -> XCUIElement {
        app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value CONTAINS %@",
            "pinkha.stage1.body.",
            text
        )).firstMatch
    }

    private func exerciseDocument(_ kind: DocumentKind) throws {
        openDocumentIfNeeded(kind)
        var body = editableBody(startNewTrailingBlock: true)
        guard body.waitForExistence(timeout: 300) else {
            attachScreenshot(named: "FAIL-\(kind.rawValue)-editor-body-missing")
            XCTFail("Production editor body UITextView did not appear for \(kind.rawValue)")
            return
        }
        body.tap()
        let enteredText = text(for: kind)
        body.typeText(enteredText)
        body = editorBody(containing: enteredText)
        XCTAssertTrue(body.waitForExistence(timeout: 20))

        assertRuntimeDirection(on: body, document: kind)
        attachScreenshot(named: "\(directionName)-\(kind.rawValue)-entry")

        let window = app.windows.firstMatch
        XCTAssertTrue(window.exists)
        performInteractiveBack(
            in: window,
            body: body,
            startX: 0.50,
            cancelledEndX: expectsRTL ? 0.38 : 0.62,
            completedEndX: expectsRTL ? 0.05 : 0.95,
            evidencePrefix: "\(directionName)-\(kind.rawValue)-full-screen"
        )

        launch(document: kind)
        openDocumentIfNeeded(kind)
        let bodyAfterFullScreenPop = editorBody(containing: enteredText)
        XCTAssertTrue(bodyAfterFullScreenPop.waitForExistence(timeout: 60))
        assertRuntimeDirection(on: bodyAfterFullScreenPop, document: kind)

        performInteractiveBack(
            in: app.windows.firstMatch,
            body: bodyAfterFullScreenPop,
            startX: expectsRTL ? 0.995 : 0.005,
            cancelledEndX: expectsRTL ? 0.86 : 0.14,
            completedEndX: expectsRTL ? 0.18 : 0.82,
            evidencePrefix: "\(directionName)-\(kind.rawValue)-edge"
        )

        launch(document: kind)
        openDocumentIfNeeded(kind)
        let reopenedBody = editorBody(containing: enteredText)
        XCTAssertTrue(reopenedBody.waitForExistence(timeout: 60), "\(kind.rawValue) did not reopen")
        assertRuntimeDirection(on: reopenedBody, document: kind)
        XCTAssertTrue(
            String(describing: reopenedBody.value).contains(enteredText),
            "Entered text did not survive close and reopen for \(kind.rawValue)"
        )
        attachScreenshot(named: "\(directionName)-\(kind.rawValue)-reopened")
    }

    private func openDocumentIfNeeded(_ kind: DocumentKind) {
        let expectedTitle = documentTitle(for: kind)
        let titleFields = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "pinkha.stage1.title.")
        )
        let identity = kind == .note ? editorBody(containing: expectedTitle) : app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@ AND value CONTAINS %@", "pinkha.stage1.title.", expectedTitle)
        ).firstMatch
        if identity.exists { return }

        guard let objectID = fixtureObjectIDs[kind] else {
            XCTFail("Missing prepared native document ID")
            return
        }
        var components = URLComponents()
        components.scheme = "anytype"
        components.host = "object"
        components.queryItems = [
            URLQueryItem(name: "objectId", value: objectID),
            URLQueryItem(name: "spaceId", value: fixtureSpaceID)
        ]
        guard let url = components.url else {
            XCTFail("Could not form the original native object deeplink")
            return
        }
        print("PINKHA_ACCEPTANCE_OPEN kind=\(kind.rawValue) space=\(fixtureSpaceID) object=\(objectID)")
        app.open(url)

        if kind == .note {
            // Native Note has no title. Wait for the previous Page to leave before seeding
            // the Note's first body through real input, never into the previous document.
            XCTAssertTrue(titleFields.firstMatch.waitForNonExistence(timeout: 60))
            let body = editableBody()
            if !identity.exists {
                body.tap()
                body.typeText(expectedTitle + "\n")
            }
        }
        XCTAssertTrue(identity.waitForExistence(timeout: 60), "Prepared native \(kind.rawValue) fixture did not open")
    }

    private func documentTitle(for kind: DocumentKind) -> String {
        switch kind {
        case .pinkha:
            return "בדיקת RTL Stage 1"
        case .note:
            return "RTL Acceptance Ordinary Note"
        case .page:
            return "RTL Acceptance Ordinary Page"
        }
    }

    private func assertRuntimeDirection(
        on body: XCUIElement,
        document kind: DocumentKind
    ) {
        let direction = expectsRTL ? "rtl" : "ltr"
        let alignment = expectsRTL ? "right" : "left"
        let requiredFragments = [
            "document-\(kind.rawValue)",
            "app-language-\(appLanguage)",
            "device-language-requested-\(deviceLanguage)",
            "swiftui-\(direction)",
            "navigation-\(direction)",
            "uikit-\(direction)",
            "alignment-\(alignment)"
        ]
        let predicates = requiredFragments.map {
            NSPredicate(format: "label CONTAINS %@", $0)
        }
        expectation(
            for: NSCompoundPredicate(andPredicateWithSubpredicates: predicates),
            evaluatedWith: body
        )
        waitForExpectations(timeout: 20)
    }

    private func launch(document kind: DocumentKind) {
        if app.state != .notRunning {
            app.terminate()
        }
        app.launchEnvironment["PINKHA_ACCEPTANCE_DOCUMENT_KIND"] = kind.rawValue
        app.launch()
    }

    private func performInteractiveBack(
        in window: XCUIElement,
        body: XCUIElement,
        startX: CGFloat,
        cancelledEndX: CGFloat,
        completedEndX: CGFloat,
        evidencePrefix: String
    ) {
        let start = window.coordinate(withNormalizedOffset: CGVector(dx: startX, dy: 0.52))
        let cancelledEnd = window.coordinate(withNormalizedOffset: CGVector(dx: cancelledEndX, dy: 0.52))
        start.press(
            forDuration: 0.08,
            thenDragTo: cancelledEnd,
            withVelocity: .slow,
            thenHoldForDuration: 0.5
        )
        XCTAssertTrue(body.waitForExistence(timeout: 5), "A short back swipe should cancel and keep the editor")
        attachScreenshot(named: "\(evidencePrefix)-cancelled")

        let completedEnd = window.coordinate(withNormalizedOffset: CGVector(dx: completedEndX, dy: 0.52))
        start.press(
            forDuration: 0.08,
            thenDragTo: completedEnd,
            withVelocity: .slow,
            thenHoldForDuration: 0.05
        )
        XCTAssertTrue(body.waitForNonExistence(timeout: 12), "A completed interactive back swipe did not pop")
        attachScreenshot(named: "\(evidencePrefix)-completed")
    }

    private func editorBody() -> XCUIElement {
        let bodies = app.textViews.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "pinkha.stage1.body.")
        )
        // Keep the Note's stable first-line identity intact while editing later content.
        return bodies.element(boundBy: max(0, bodies.count - 1))
    }

    private func editableBody(startNewTrailingBlock: Bool = false) -> XCUIElement {
        let body = editorBody()
        if !startNewTrailingBlock, body.waitForExistence(timeout: 3) { return body }

        // A newly opened native document can contain metadata without a body row. The
        // original editor creates its virtual trailing row only after a tap below content.
        // Exercise that user path; never create a persisted fixture block or change focus.
        let editor = app.collectionViews.containing(.button, identifier: "torah-document-sources-add").firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 20))
        let contentBottom = editor.cells.allElementsBoundByIndex.map { $0.frame.maxY }.max() ?? editor.frame.minY
        let keyboard = app.keyboards.firstMatch
        let visibleBottom = keyboard.exists ? min(editor.frame.maxY, keyboard.frame.minY) : editor.frame.maxY
        XCTAssertGreaterThan(visibleBottom - contentBottom, 24, "A safe native empty area is required before tapping")
        let y = contentBottom + (visibleBottom - contentBottom) * 0.5
        editor.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(
            dx: editor.frame.width * 0.5, dy: y - editor.frame.minY
        )).tap()
        let created = app.textViews.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND label CONTAINS %@ AND label CONTAINS %@",
            "pinkha.stage1.body.", "first-responder-true", "text-empty-true"
        )).firstMatch
        XCTAssertTrue(created.waitForExistence(timeout: 20), "Native empty-area tap did not expose a trailing editor row")
        return created
    }

    private func text(for kind: DocumentKind) -> String {
        if expectsRTL {
            return "טקסט \(kind.rawValue) בעברית"
        }
        return "English \(kind.rawValue) acceptance text"
    }

    private var directionName: String { expectsRTL ? "RTL" : "LTR" }

    private func attachScreenshot(named name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
