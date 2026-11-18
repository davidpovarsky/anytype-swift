import XCTest

@MainActor
private func waitForPinkhaNativeNavigation(_ app: XCUIApplication) -> Bool {
    // A restored Home or an existing native editor must be mounted before the
    // OS route is sent. A foreground launch screen alone is not readiness.
    let ready = app.descendants(matching: .any).matching(NSPredicate(
        format: "identifier == %@ OR label == %@ OR identifier == %@ OR label == %@ OR (elementType == %d AND (label == %@ OR label == %@))",
        "SpaceHub", "SpaceHub", "NewSpaceButton", "NewSpaceButton",
        XCUIElement.ElementType.button.rawValue, "More", "x24/More"
    )).firstMatch
    let observed = ready.waitForExistence(timeout: 120)
    XCTAssertTrue(observed, "The restored native navigation must be ready before opening a fixture")
    return observed
}

/// Drives the original application against the custom Heart. Its fixture is
/// produced by the real native API suite in a freshly created simulator.
@MainActor
final class PinkhaNativeDerivedAcceptanceUITests: XCTestCase {
    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private var fixture: NativeDerivedFixture!
    private var currentObjectID: String?

    override func setUpWithError() throws {
        continueAfterFailure = false
        if app.state != .notRunning { app.terminate() }
        let env = ProcessInfo.processInfo.environment
        XCTAssertEqual(env["PINKHA_NATIVE_UI_DISPOSABLE"], "1")
        guard env["PINKHA_NATIVE_UI_DISPOSABLE"] == "1" else {
            throw NSError(domain: "NativeDerivedDisposableFixtureRequired", code: 1)
        }
        fixture = try JSONDecoder().decode(NativeDerivedFixture.self, from: Data(try XCTUnwrap(env["PINKHA_NATIVE_UI_FIXTURE_JSON"]).utf8))
        XCTAssertEqual(fixture.documents.count, 3)
        XCTAssertEqual(Set(fixture.documents.values).count, 3)
        XCTAssertEqual(fixture.sourceHeaderCases.map(\.count), [0, 1, 2, 12])
        XCTAssertEqual(Set(fixture.sourceHeaderCases.map(\.objectId)).count, 4)
        XCTAssertEqual(fixture.sourceHeaderCases.last?.objectId, fixture.manySourcesDocument)
        currentObjectID = nil
        app.launchEnvironment["PINKHA_UI27_ROUTE_OBSERVATION"] = "1"
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
    }

    func testNativePropertiesPickerChipsSetMembershipAndRelaunch() throws {
        executionTimeAllowance = 900
        for role in ["chiddush", "article", "research"] {
            let id = try XCTUnwrap(fixture.documents[role])
            try openProperties(id)
            for name in fixture.nativeProperties { XCTAssertTrue(propertyTitle(name).waitForExistence(timeout: 15)) }
            XCTAssertFalse(app.buttons["torah-property-ref"].exists, "The old display-only Properties row must not replace the original native row")
            XCTAssertFalse(app.staticTexts["הקשר תורני"].exists)
            try selectNativeProperty("מקור/ות", query: fixture.sourceQuery, expectedLabel: fixture.sourceLabel)
            expectNativeValue("מקור/ות", label: fixture.sourceLabel)
            try selectNativeProperty("נושא", query: fixture.topicQuery, expectedLabel: fixture.topicLabel)
            expectNativeValue("נושא", label: fixture.topicLabel)
            let wordLabel = try selectNativeProperty("מילה / ערך", query: fixture.wordQuery)
            expectNativeValue("מילה / ערך", label: wordLabel)
            screenshot("native-properties-\(role)-three-values")
            app.terminate()
            try openProperties(id)
            expectNativeValue("מקור/ות", label: fixture.sourceLabel)
            expectNativeValue("נושא", label: fixture.topicLabel)
            expectNativeValue("מילה / ערך", label: wordLabel)
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
        for name in fixture.nativeProperties { XCTAssertTrue(setLabel(name).waitForExistence(timeout: 20)) }
        XCTAssertTrue(setLabel(fixture.sourceLabel).waitForExistence(timeout: 20))
        XCTAssertTrue(setLabel(fixture.topicLabel).exists)
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
        for value in fixture.sourceHeaderCases where value.count < 12 {
            try open(value.objectId)
            try expectSourceHeader(value)
            screenshot("native-source-header-count-\(value.count)")
            app.terminate()
        }
        let many = try XCTUnwrap(fixture.sourceHeaderCases.first { $0.count == 12 })
        try open(fixture.manySourcesDocument)
        try expectSourceHeader(many)
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
        let visibleLabels = try expectSourceHeader(many)
        let overflow = app.buttons["torah-document-sources-more"].firstMatch
        XCTAssertTrue(overflow.waitForExistence(timeout: 20)); overflow.tap()
        try expectOverflowSources(Set(many.labels).subtracting(visibleLabels))
        screenshot("native-source-header-overflow-and-separate-add")
        app.terminate()
    }

    func testUniversalPageNoteCustomPropertiesAndMixedSet() throws {
        executionTimeAllowance = 900
        for role in ["page", "note", "custom"] {
            let id = try XCTUnwrap(fixture.universalDocuments[role])
            try open(id)
            XCTAssertFalse(app.buttons["torah-document-sources-add"].exists)
            try openProperties(id, expectsSources: false, alreadyOpen: true)
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
            try selectNativeProperty("מקור/ות", query: fixture.sourceQuery, expectedLabel: fixture.sourceLabel)
            try selectNativeProperty("נושא", query: fixture.topicQuery, expectedLabel: fixture.topicLabel)
            let wordLabel = try selectNativeProperty("מילה / ערך", query: fixture.wordQuery)
            screenshot("universal-canonical-values-" + role)
            let tree = XCTAttachment(string: app.debugDescription)
            tree.name = "universal-property-accessibility-" + role
            tree.lifetime = .keepAlways; add(tree)
            app.terminate()
            try openProperties(id)
            expectNativeValue("מקור/ות", label: fixture.sourceLabel)
            expectNativeValue("נושא", label: fixture.topicLabel)
            expectNativeValue("מילה / ערך", label: wordLabel)
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
            let typeID = try XCTUnwrap(fixture.universalTypes[role])
            try openProperties(typeID, expectsSources: false)
            let add = app.buttons["torah-type-add-property"].firstMatch
            XCTAssertTrue(add.waitForExistence(timeout: 20))
            for name in fixture.nativeProperties {
                XCTAssertFalse(propertyTitle(name).exists,
                               "Adding a property to the earlier document must not also configure its Type")
            }
            add.tap()
            for name in fixture.nativeProperties { XCTAssertTrue(propertyTitle(name).waitForExistence(timeout: 20)) }
            screenshot("universal-native-Type-picker-" + role)
            propertyTitle("מקור/ות").tap()
            XCTAssertTrue(add.waitForExistence(timeout: 20))
            app.terminate()
            try openProperties(typeID)
            XCTAssertTrue(propertyTitle("מקור/ות").waitForExistence(timeout: 20),
                          "The Type source property must survive a real cold reopen")
            screenshot("universal-native-Type-source-persisted-" + role)
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

    // Document/object flows already executed successfully in run 42801263371.
    // Resume only the unproven Type presentation and Set interactions.
    func testRemainingNativeSourceFilterEditing() throws {
        // The compiled native fixture already links the three P1 documents.
        // Reuse them for the remaining filter edits; do not replay successful
        // object pickers, writing columns, or mixed-Set column configuration.
        try open(fixture.universalSetId)
        assertUniversalSetMembers(present: true)
        try replaceSourceFilter(query: "Genesis 1:2")
        app.terminate()
        try open(fixture.universalSetId)
        assertUniversalSetMembers(present: false)
        screenshot("remaining-native-Set-nonmatching-filter-empty")
        try replaceSourceFilter(query: fixture.sourceQuery)
        app.terminate()
        try open(fixture.universalSetId)
        assertUniversalSetMembers(present: true)
        screenshot("remaining-native-Set-restored-filter-members")
    }

    func testRemainingUniversalTypePickersAndMixedSet() throws {
        let preserved = fixture.typeSwitch
        XCTAssertEqual(preserved.spaceId, fixture.spaceId)
        XCTAssertEqual(preserved.initialTypeId, fixture.types["chiddush"])
        XCTAssertEqual(preserved.values.map(\.kind), ["ref", "topic", "word"])
        var currentType = try XCTUnwrap(preserved.types["chiddush"])
        try openProperties(preserved.objectId)
        try expectTypeSwitchValues(preserved)
        _ = try typeValueButton(currentType, expandSection: true)
        captureTypeSwitch("initial-chiddush")
        for role in ["article", "research", "chiddush"] {
            let nextType = try XCTUnwrap(preserved.types[role])
            let current = try typeValueButton(currentType, expandSection: false)
            current.tap()
            // Use the original Type picker and its real search. Its native
            // choice ID is read from ObjectShow, not inferred from a label.
            let search = app.textFields.matching(NSPredicate(
                format: "identifier == %@", "pinkha-object-type-search-field"
            )).firstMatch
            try requireHittable([search], until: Date().addingTimeInterval(15),
                                diagnosticName: "type-switch-search-\(role)")
            XCTAssertTrue(search.isHittable)
            let previous = (search.value as? String).flatMap { $0 == "Search" ? nil : $0 } ?? ""
            setPropertySearch(search, previous: previous, text: nextType.label)
            let choices = app.buttons.matching(NSPredicate(
                format: "identifier == %@", "pinkha-object-type-choice:\(nextType.id)"
            ))
            let choice = choices.firstMatch
            try requireHittable([choice], until: Date().addingTimeInterval(20),
                                diagnosticName: "type-switch-choice-\(role)")
            XCTAssertEqual(choices.count, 1)
            XCTAssertTrue(choice.isHittable)
            XCTAssertTrue(choice.label.contains(nextType.label))
            choice.tap()
            XCTAssertTrue(choice.waitForNonExistence(timeout: 15))
            // Await the actual Type value before terminating the process. The
            // existing Properties model retains expansion for an unchanged section.
            _ = try typeValueButton(nextType, expandSection: nextType.sectionId != currentType.sectionId)
            captureTypeSwitch("changed-\(role)")
            app.terminate()
            try openProperties(preserved.objectId)
            try expectTypeSwitchValues(preserved)
            _ = try typeValueButton(nextType, expandSection: true)
            captureTypeSwitch("cold-reopen-\(role)")
            currentType = nextType
        }
        app.terminate()
        // The accepted real native fixture has already linked these P1 objects
        // through the canonical repository. Preserve the existing mixed-Set
        // assertions; the Type-switch document has a different source reference.
        try open(fixture.universalSetId)
        try enableNativeColumns()
        app.terminate()
        try open(fixture.universalSetId)
        for name in fixture.nativeProperties { XCTAssertTrue(setLabel(name).waitForExistence(timeout: 20)) }
        for role in ["page", "note", "custom"] {
            XCTAssertTrue(setLabel("Universal \(role) P1").waitForExistence(timeout: 30))
        }
        screenshot("remaining-universal-mixed-native-filter-membership")
    }

    private func expectTypeSwitchValues(_ preserved: NativeTypeSwitchFixture) throws {
        XCTAssertEqual(currentObjectID, preserved.objectId)
        for value in preserved.values {
            expectNativeValue(value.propertyName, label: value.label)
        }
    }

    private func typeValueButton(_ type: NativeTypeSwitchChoice, expandSection: Bool) throws -> XCUIElement {
        let deadline = Date().addingTimeInterval(20)
        let identity = "pinkha-properties-type-value:\(type.id)"
        let predicate = NSPredicate(format: "identifier == %@", identity)
        let choices = app.buttons.matching(predicate)
        let value = choices.firstMatch
        if expandSection && type.sectionExpandable &&
            !value.waitForExistence(timeout: min(2, max(0, deadline.timeIntervalSinceNow))) {
            let header = app.buttons.matching(NSPredicate(format: "label == %@", type.sectionTitle)).firstMatch
            try requireHittable([header], until: min(deadline, Date().addingTimeInterval(15)),
                                diagnosticName: "type-switch-section")
            XCTAssertTrue(header.isHittable)
            header.tap()
        }
        // One 20s budget covers section readiness, positioning and hit testing.
        // An on-screen value can be temporarily unhittable during animation;
        // this alone must never cause a swipe.
        var swipes = 0
        while Date() < deadline {
            if value.exists && value.isHittable && choices.count == 1 && Date() < deadline {
                XCTAssertEqual(choices.count, 1)
                XCTAssertTrue(value.isHittable)
                XCTAssertTrue(value.label.contains(type.label))
                return value
            }
            if value.exists && !value.isHittable && swipes < 4 {
                // Preserve the complete native identity in the container query.
                let scroll = app.scrollViews.containing(predicate).firstMatch
                if scroll.exists && scroll.isHittable {
                    let viewport = scroll.frame.intersection(app.frame)
                    let frame = value.frame
                    if !viewport.isEmpty && !frame.isEmpty && Date() < deadline {
                        if frame.maxY <= viewport.minY {
                            scroll.swipeDown()
                            swipes += 1
                        } else if frame.minY >= viewport.maxY {
                            scroll.swipeUp()
                            swipes += 1
                        }
                    }
                }
            }
            let remaining = deadline.timeIntervalSinceNow
            if remaining > 0 { Thread.sleep(forTimeInterval: min(0.1, remaining)) }
        }
        try failReadiness([value], diagnosticName: "type-switch-current-value",
                          message: "The exact native Type value did not become unique and hittable within its 20-second budget")
    }

    private func requireHittable(_ controls: [XCUIElement], until deadline: Date,
                                diagnosticName: String) throws {
        let expectations = controls.map {
            XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true AND hittable == true"), object: $0)
        }
        let remaining = deadline.timeIntervalSinceNow
        let result: XCTWaiter.Result = remaining > 0 && !controls.isEmpty
            ? XCTWaiter.wait(for: expectations, timeout: remaining) : .timedOut
        guard result == .completed, Date() <= deadline,
              controls.allSatisfy({ $0.exists && $0.isHittable }) else {
            try failReadiness(controls, diagnosticName: diagnosticName,
                              message: "The original native controls did not become hittable within their existing deadline")
        }
        for control in controls { XCTAssertTrue(control.exists); XCTAssertTrue(control.isHittable) }
    }

    private func failReadiness(_ controls: [XCUIElement], diagnosticName: String,
                               message: String) throws -> Never {
        let targets = controls.map(\.debugDescription).joined(separator: "\n\n")
        let hierarchy = XCTAttachment(string: "App:\n" + app.debugDescription + "\n\nTargets:\n" + targets)
        hierarchy.name = diagnosticName + "-failure-accessibility"
        hierarchy.lifetime = .keepAlways
        add(hierarchy)
        screenshot(diagnosticName + "-failure")
        XCTFail(message)
        throw NSError(domain: "NativePropertiesControlReadiness", code: 1)
    }

    private func captureTypeSwitch(_ phase: String) {
        screenshot("native-type-switch-\(phase)")
        let hierarchy = XCTAttachment(string: app.debugDescription)
        hierarchy.name = "native-type-switch-\(phase)-accessibility"
        hierarchy.lifetime = .keepAlways
        add(hierarchy)
    }

    private func setPropertySearch(_ search: XCUIElement, previous: String, text: String) {
        search.tap()
        if !previous.isEmpty {
            search.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: previous.utf16.count))
        }
        search.typeText(text)
    }

    private func hittablePropertyButton(_ name: String, exact: Bool = true) -> XCUIElement? {
        let deadline = Date().addingTimeInterval(20)
        repeat {
            let rows = app.buttons.matching(NSPredicate(format: exact ? "label == %@" : "label CONTAINS %@", name)).allElementsBoundByIndex
            if let row = rows.first(where: { $0.isHittable }) { return row }
            Thread.sleep(forTimeInterval: 0.2)
        } while Date() < deadline
        return nil
    }

    private var navigationMore: XCUIElement {
        app.buttons.matching(NSPredicate(format: "label == %@ OR label == %@", "More", "x24/More")).firstMatch
    }

    private var setTable: XCUIElement {
        app.descendants(matching: .any).matching(identifier: "set-table").firstMatch
    }

    private func setLabel(_ label: String) -> XCUIElement {
        setTable.descendants(matching: .any).matching(NSPredicate(format: "label == %@", label)).firstMatch
    }

    private func expectNativeValue(_ name: String, label: String, file: StaticString = #filePath, line: UInt = #line) {
        let deadline = Date().addingTimeInterval(20)
        repeat {
            let title = propertyTitle(name)
            if title.exists {
                let candidates = app.descendants(matching: .any).matching(NSPredicate(
                    format: "(elementType == %d OR elementType == %d) AND label == %@",
                    XCUIElement.ElementType.button.rawValue, XCUIElement.ElementType.staticText.rawValue, label
                )).allElementsBoundByIndex
                if candidates.contains(where: {
                    $0.isHittable && abs($0.frame.midY - title.frame.midY) < 22 && $0.frame.minX >= title.frame.maxX
                }) { return }
            }
            Thread.sleep(forTimeInterval: 0.2)
        } while Date() < deadline
        XCTFail("The original native row \(name) did not render \(label)", file: file, line: line)
    }

    private func assertSetMembers(present: Bool, matchingRoles: Set<String> = ["chiddush", "article", "research"]) {
        XCTAssertTrue(setTable.waitForExistence(timeout: 30))
        for (role, id) in fixture.documents {
            guard let title = fixture.names[id] else { XCTFail("Missing fixture title"); continue }
            let row = setLabel(title)
            if present && matchingRoles.contains(role) {
                XCTAssertTrue(row.waitForExistence(timeout: 30), "Native Set omitted \(title)")
            } else {
                XCTAssertTrue(row.waitForNonExistence(timeout: 30), "Native Set included a nonmatching document: \(title)")
            }
        }
    }

    private func assertUniversalSetMembers(present: Bool) {
        XCTAssertTrue(setTable.waitForExistence(timeout: 30))
        for role in ["page", "note", "custom"] {
            let linked = setLabel("Universal \(role) P1")
            if present { XCTAssertTrue(linked.waitForExistence(timeout: 30)) }
            else { XCTAssertTrue(linked.waitForNonExistence(timeout: 30)) }
            XCTAssertTrue(setLabel("Universal \(role) blank").waitForNonExistence(timeout: 30))
        }
    }

    private func openSetSettings(_ section: String) {
        let settings = app.buttons["set-view-settings"].firstMatch
        XCTAssertTrue(settings.waitForExistence(timeout: 15)); settings.tap()
        let row = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", section)).firstMatch
        guard row.waitForExistence(timeout: 15) else {
            print("Native Set settings hierarchy: " + app.debugDescription)
            XCTFail("Original Set settings section missing: \(section)")
            return
        }
        row.tap()
    }

    private func enableNativeColumns() throws {
        openSetSettings("Properties")
        for name in fixture.nativeProperties {
            let toggle = app.switches[name].firstMatch
            XCTAssertTrue(toggle.waitForExistence(timeout: 15))
            if toggle.value as? String == "0" {
                // SwiftUI's accessibility frame includes the text label.
                // Tap the native switch at its trailing edge.
                toggle.coordinate(withNormalizedOffset: CGVector(dx: 0.95, dy: 0.5)).tap()
            }
            let enabled = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value == %@", "1"), object: toggle)
            XCTAssertEqual(XCTWaiter.wait(for: [enabled], timeout: 15), .completed, "Native column did not enable: \(name)")
        }
        screenshot("native-set-original-fields-switches")
    }

    private func replaceSourceFilter(query: String) throws {
        openSetSettings("Filters")
        // The underlying Edit view also says "Filters, מקור/ות". Select the
        // actual foreground filter row instead of the first background match.
        let source = try XCTUnwrap(hittablePropertyButton("מקור/ות", exact: false))
        source.tap()
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
        // Initialize the restored account/window before cold-start deep links.
        // open(URL) alone can deliver the route before the editor is ready.
        if app.state == .notRunning { app.launch() }
        var url = URLComponents()
        url.scheme = "anytype"; url.host = "object"
        url.queryItems = [URLQueryItem(name: "objectId", value: id), URLQueryItem(name: "spaceId", value: fixture.spaceId)]
        guard waitForPinkhaNativeNavigation(app) else { return }
        XCUIDevice.shared.system.open(try XCTUnwrap(url.url))
        if id == fixture.setId || id == fixture.universalSetId {
            XCTAssertTrue(setTable.waitForExistence(timeout: 45))
        } else if fixture.types.values.contains(id) || fixture.universalTypes.values.contains(id) {
            let properties = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Properties,")).firstMatch
            try requireHittable([properties], until: Date().addingTimeInterval(45),
                                diagnosticName: "native-type-editor-properties")
        } else {
            let editor = app.otherElements.matching(NSPredicate(format: "identifier == %@", "pinkha-ui27-editor:\(fixture.spaceId):\(id)")).firstMatch
            try requireHittable([editor, navigationMore], until: Date().addingTimeInterval(45),
                                diagnosticName: "native-exact-document-navigation")
            XCTAssertTrue(editor.isHittable)
            XCTAssertTrue(navigationMore.isHittable)
        }
        currentObjectID = id
    }

    private func openProperties(_ id: String, expectsSources: Bool = true, alreadyOpen: Bool = false) throws {
        if !alreadyOpen { try open(id) }
        if fixture.types.values.contains(id) || fixture.universalTypes.values.contains(id) {
            let properties = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Properties,")).firstMatch
            try requireHittable([properties], until: Date().addingTimeInterval(20),
                                diagnosticName: "native-type-properties-open")
            properties.tap()
            if expectsSources { XCTAssertTrue(propertyTitle("מקור/ות").waitForExistence(timeout: 20)) }
            return
        }
        let menuDeadline = Date().addingTimeInterval(15)
        try requireHittable([navigationMore], until: menuDeadline,
                            diagnosticName: "native-document-more-open")
        navigationMore.tap()
        let button = app.buttons["Properties"].firstMatch
        try requireHittable([button], until: menuDeadline,
                            diagnosticName: "native-document-properties-open")
        button.tap()
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

    @discardableResult
    private func selectNativeProperty(_ name: String, query: String, expectedLabel: String? = nil) throws -> String {
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
        XCTAssertTrue(search.waitForExistence(timeout: 10))
        let previous = (search.value as? String) ?? ""
        // The canonical session can preserve a search between property sheets.
        // Clear actual content while leaving its placeholder untouched.
        setPropertySearch(search, previous: previous == search.placeholderValue ? "" : previous, text: query)
        XCTAssertFalse(app.buttons["Remove link"].firstMatch.exists,
                       "This fixed-scope fixture must begin without an existing association")
        print("Native Set fixture picker: property=\(name) query=\(query) actual=\(search.value ?? "nil")")
        let link = app.buttons["Link to document"].firstMatch
        guard link.waitForExistence(timeout: 45) else {
            print("Native picker failure hierarchy: " + app.debugDescription)
            XCTFail("Canonical picker did not offer a link for \(name): \(query)")
            throw NSError(domain: "NativeSetFixturePicker", code: 1)
        }
        link.tap()
        XCTAssertTrue(app.buttons["Remove link"].firstMatch.waitForExistence(timeout: 30))
        // Read the actual selected canonical item before dismissing its picker.
        // A word's localized label may be a lexicon description, not its query.
        // The property row is checked against this independent expectation after
        // a new App process loads the saved native value.
        let selectedLabel = try selectedCanonicalLabel(property: name)
        if let expectedLabel { XCTAssertEqual(selectedLabel, expectedLabel) }
        // The canonical mutation has completed. Cold-open the same actual
        // fixture on phone or pad and verify its persisted native property.
        // Interactive sheet dismissal remains a separate acceptance criterion.
        let objectID = try XCTUnwrap(currentObjectID)
        app.terminate()
        try openProperties(objectID)
        XCTAssertTrue(propertyTitle(name).waitForExistence(timeout: 15))
        expectNativeValue(name, label: selectedLabel)
        return selectedLabel
    }

    private func selectedCanonicalLabel(property name: String) throws -> String {
        let preview = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@", "torah-existing-associations-strip"
        )).firstMatch
        XCTAssertTrue(preview.waitForExistence(timeout: 15))
        let remove = preview.buttons.matching(NSPredicate(format: "label == %@", "Remove link"))
        XCTAssertEqual(remove.count, 1, "The fixed native scope must contain exactly the newly selected canonical item")
        let chips = preview.buttons.matching(NSPredicate(format: "label != %@", "Remove link"))
        XCTAssertEqual(chips.count, 1, "Read the selected canonical item, not a result row or a property placeholder")
        guard remove.count == 1, chips.count == 1 else {
            throw NSError(domain: "NativeCanonicalSelectionAmbiguous", code: 1)
        }
        let chip = chips.firstMatch
        let label = chip.label.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !label.isEmpty, !["Select options", "Add", name].contains(label),
              !label.contains("torah1|"), !chip.frame.isEmpty,
              preview.frame.intersects(chip.frame) else {
            XCTFail("The selected canonical item has no visible human label")
            throw NSError(domain: "NativeCanonicalSelectionLabelMissing", code: 1)
        }
        return label
    }

    private func screenshot(_ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }

    @discardableResult
    private func expectSourceHeader(_ value: NativeSourceHeaderCase) throws -> Set<String> {
        let expected = Set(value.labels)
        XCTAssertEqual(expected.count, value.count)
        let add = app.buttons["torah-document-sources-add"].firstMatch
        let more = app.buttons["torah-document-sources-more"].firstMatch
        let chips = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "torah-document-source-chip-"
        ))
        let deadline = Date().addingTimeInterval(20)
        repeat {
            let visible = chips.allElementsBoundByIndex
            let labels = Set(visible.map(\.label))
            let remainder = max(0, value.count - 2)
            let overflowMatches = remainder == 0 ? !more.exists :
                (more.exists && more.isHittable && more.label == "\(remainder) Sources")
            if visible.count == min(value.count, 2), labels.count == visible.count,
               labels.isSubset(of: expected), visible.allSatisfy({ $0.isHittable }),
               add.exists, add.isHittable,
               add.value as? String == (value.count == 0 ? "placeholder" : "compact-icon"),
               overflowMatches {
                return labels
            }
            Thread.sleep(forTimeInterval: 0.2)
        } while Date() < deadline
        XCTFail("The exact native document header did not render source count \(value.count)")
        throw NSError(domain: "NativeSourceHeaderCardinality", code: value.count)
    }

    private func expectOverflowSources(_ expected: Set<String>) throws {
        XCTAssertEqual(expected.count, 10)
        // The two document chips are excluded from this set. Only the actual
        // opened native Menu can expose the remaining ten fixture source labels.
        // A native Menu may scroll: require its exact contents and an actionable
        // visible choice, without requiring all ten rows in one viewport.
        let choices = app.buttons.matching(NSPredicate(format: "label IN %@", expected.sorted()))
        let deadline = Date().addingTimeInterval(20)
        repeat {
            let visible = choices.allElementsBoundByIndex
            if visible.count == expected.count, Set(visible.map(\.label)) == expected,
               visible.contains(where: { $0.isHittable }) { return }
            Thread.sleep(forTimeInterval: 0.2)
        } while Date() < deadline
        XCTFail("The source overflow Menu did not expose the exact ten remaining source choices")
        throw NSError(domain: "NativeSourceHeaderOverflow", code: 1)
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
    let sourceHeaderCases: [NativeSourceHeaderCase]
    let typeSwitch: NativeTypeSwitchFixture
    let setId: String
    let nativeProperties: [String]
    let sourceQuery: String
    let sourceLabel: String
    let topicQuery: String
    let topicLabel: String
    let wordQuery: String
}

private struct NativeSourceHeaderCase: Decodable {
    let count: Int
    let objectId: String
    let labels: [String]
}

private struct NativeTypeSwitchFixture: Decodable {
    let objectId: String
    let spaceId: String
    let initialTypeId: String
    let types: [String: NativeTypeSwitchChoice]
    let values: [NativeTypeSwitchValue]
}

private struct NativeTypeSwitchChoice: Decodable {
    let id: String
    let label: String
    let propertyName: String
    let sectionId: String
    let sectionTitle: String
    let sectionExpandable: Bool
}

private struct NativeTypeSwitchValue: Decodable {
    let kind: String
    let propertyName: String
    let label: String
}

@MainActor
final class PinkhaTorahPropertiesAcceptanceUITests: XCTestCase {
    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private let sourceName = "מקור/ות"
    private let topicName = "נושא"
    private let emptyNativeValue = "Select options"
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
        app.launchEnvironment["PINKHA_UI27_ROUTE_OBSERVATION"] = "1"
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
    }

    func testOriginalPropertiesCanonicalLinkUnlinkAndRelaunchForAllWritingTypes() throws {
        for objectID in objectIDs {
            try reopenProperties(objectID: objectID)
            assertNativePropertiesPresent(objectID: objectID)
            try expectNativeValue(emptyNativeValue, property: sourceName)
            try expectNativeValue(emptyNativeValue, property: topicName)

            try openNativePicker(property: topicName, value: emptyNativeValue)
            try link(query: topicQuery, expectedLabel: topicLabel)
            try reopenProperties(objectID: objectID)
            try expectNativeValue(topicLabel, property: topicName)
            try expectNativeValue(emptyNativeValue, property: sourceName)

            try openNativePicker(property: sourceName, value: emptyNativeValue)
            try link(query: sourceQuery, expectedLabel: sourceLabel)
            try reopenProperties(objectID: objectID)
            try expectNativeValue(sourceLabel, property: sourceName)
            try expectNativeValue(topicLabel, property: topicName)
            assertNativePropertiesPresent(objectID: objectID)
            attachPropertiesScreenshot(name: "\(objectID)-native-linked-after-relaunch")

            try openNativePicker(property: sourceName, value: sourceLabel)
            unlink(expectedLabel: sourceLabel)
            try reopenProperties(objectID: objectID)
            try expectNativeValue(emptyNativeValue, property: sourceName)
            try expectNativeValue(topicLabel, property: topicName)

            try openNativePicker(property: topicName, value: topicLabel)
            unlink(expectedLabel: topicLabel)
            try reopenProperties(objectID: objectID)
            try expectNativeValue(emptyNativeValue, property: sourceName)
            try expectNativeValue(emptyNativeValue, property: topicName)
            assertNativePropertiesPresent(objectID: objectID)
            attachPropertiesScreenshot(name: "\(objectID)-native-unlinked-after-relaunch")
        }
    }

    private func reopenProperties(objectID: String) throws {
        // Reopen after each completed canonical mutation to verify persistence.
        // This also avoids an iPad-only outside-popover dismissal assumption.
        if app.state != .notRunning { app.terminate() }
        app.launch()
        var components = URLComponents()
        components.scheme = "anytype"
        components.host = "object"
        components.queryItems = [URLQueryItem(name: "objectId", value: objectID), URLQueryItem(name: "spaceId", value: spaceID)]
        guard waitForPinkhaNativeNavigation(app) else { return }
        XCUIDevice.shared.system.open(try XCTUnwrap(components.url))
        let editor = app.otherElements.matching(NSPredicate(format: "identifier == %@", "pinkha-ui27-editor:\(spaceID):\(objectID)")).firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 45), "The exact disposable document must be mounted")
        XCTAssertTrue(editor.isHittable)
        let settings = app.buttons.matching(NSPredicate(format: "label == %@ OR label == %@", "More", "x24/More")).firstMatch
        XCTAssertTrue(settings.waitForExistence(timeout: 30))
        settings.tap()
        let properties = app.buttons["Properties"].firstMatch
        XCTAssertTrue(properties.waitForExistence(timeout: 10))
        properties.tap()
        XCTAssertTrue(propertyTitle(sourceName).waitForExistence(timeout: 15))
        XCTAssertTrue(propertyTitle(topicName).exists)
        XCTAssertFalse(app.buttons["torah-property-ref"].exists, "Acceptance must use the original native property rows")
    }

    private var nativeSearch: XCUIElement {
        app.textFields.matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@",
            "torah-native-property-editor", "torah-sources-search-field"
        )).firstMatch
    }

    private func propertyTitle(_ name: String) -> XCUIElement {
        app.descendants(matching: .any).matching(NSPredicate(
            format: "(elementType == %d OR elementType == %d) AND label == %@",
            XCUIElement.ElementType.button.rawValue, XCUIElement.ElementType.staticText.rawValue, name
        )).firstMatch
    }

    private func openNativePicker(property: String, value: String) throws {
        let nativeValue = try findNativeValue(value, property: property)
        XCTAssertTrue(nativeValue.isEnabled)
        nativeValue.tap()
        XCTAssertTrue(nativeSearch.waitForExistence(timeout: 15))
        // Native property editors fix the source/topic scope themselves. The old
        // projection row's three-way segmented picker is no longer this contract.
        XCTAssertFalse(app.segmentedControls.firstMatch.exists)
    }

    private func link(query: String, expectedLabel: String) throws {
        let search = nativeSearch
        let previous = (search.value as? String) ?? ""
        search.tap()
        if !previous.isEmpty && previous != search.placeholderValue {
            search.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: previous.utf16.count))
        }
        search.typeText(query)
        let link = app.buttons["Link to document"].firstMatch
        XCTAssertTrue(link.waitForExistence(timeout: 45))
        link.tap()
        // The preview appears after the canonical repository mutation returns.
        XCTAssertTrue(app.buttons.matching(NSPredicate(format: "label == %@", expectedLabel)).firstMatch.waitForExistence(timeout: 30))
        XCTAssertTrue(app.buttons["Remove link"].firstMatch.waitForExistence(timeout: 30))
    }

    private func unlink(expectedLabel: String) {
        XCTAssertTrue(app.buttons.matching(NSPredicate(format: "label == %@", expectedLabel)).firstMatch.waitForExistence(timeout: 20))
        let remove = app.buttons["Remove link"].firstMatch
        XCTAssertTrue(remove.waitForExistence(timeout: 20))
        XCTAssertEqual(app.buttons.matching(NSPredicate(format: "label == %@", "Remove link")).count, 1,
                       "The fixed native scope must contain exactly the fixture association")
        remove.tap()
        XCTAssertTrue(remove.waitForNonExistence(timeout: 20))
    }

    private func findNativeValue(_ value: String, property: String) throws -> XCUIElement {
        let title = propertyTitle(property)
        XCTAssertTrue(title.waitForExistence(timeout: 15))
        let candidates = app.descendants(matching: .any).matching(NSPredicate(
            format: "(elementType == %d OR elementType == %d) AND label == %@",
            XCUIElement.ElementType.button.rawValue, XCUIElement.ElementType.staticText.rawValue, value
        ))
        let deadline = Date().addingTimeInterval(20)
        repeat {
            let titleFrame = title.frame
            if let match = candidates.allElementsBoundByIndex.first(where: {
                let frame = $0.frame
                return $0.isHittable && abs(frame.midY - titleFrame.midY) < 22 && frame.minX >= titleFrame.maxX
            }) { return match }
            Thread.sleep(forTimeInterval: 0.2)
        } while Date() < deadline
        XCTFail("The original native \(property) row did not render \(value)")
        throw NSError(domain: "PinkhaCanonicalNativeValueMissing", code: 1)
    }

    private func expectNativeValue(_ value: String, property: String) throws {
        _ = try findNativeValue(value, property: property)
    }

    private func assertNativePropertiesPresent(objectID: String) {
        let labels = nativePropertyLabels[objectID] ?? []
        XCTAssertFalse(labels.isEmpty)
        for label in labels { XCTAssertTrue(propertyTitle(label).exists, "Original native property disappeared: \(label)") }
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
        app.launchEnvironment["PINKHA_UI27_ROUTE_OBSERVATION"] = "1"
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
        // Native preparation attaches Sources through Add Property to these
        // ordinary Note/Page fixtures; blank documents remain header-free.
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
            let field = app.textFields.matching(NSPredicate(
                format: "identifier == %@ OR identifier == %@", "torah-sources-search-sheet", "torah-sources-search-field"
            )).firstMatch
            XCTAssertTrue(field.waitForExistence(timeout: 20), "Sources must open the existing document search presenter")
            XCTAssertTrue(app.staticTexts.matching(NSPredicate(
                format: "label == %@", expectsRTL ? "קישורים במסמך" : "Document links"
            )).firstMatch.waitForExistence(timeout: 15), "The opened search must explicitly show document scope")
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
        guard let objectID = fixtureObjectIDs[kind] else {
            XCTFail("Missing prepared native document ID")
            return
        }
        let editorMatches = app.otherElements.matching(NSPredicate(
            format: "identifier == %@", "pinkha-ui27-editor:\(fixtureSpaceID):\(objectID)"
        ))
        let editor = editorMatches.firstMatch
        if identity.exists && editor.exists {
            XCTAssertEqual(editorMatches.count, 1)
            XCTAssertTrue(editor.isHittable)
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
        guard waitForPinkhaNativeNavigation(app) else { return }
        XCUIDevice.shared.system.open(url)
        XCTAssertTrue(editor.waitForExistence(timeout: 45), "The exact native Space and document must be mounted")
        XCTAssertEqual(editorMatches.count, 1)
        XCTAssertTrue(editor.isHittable)

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
