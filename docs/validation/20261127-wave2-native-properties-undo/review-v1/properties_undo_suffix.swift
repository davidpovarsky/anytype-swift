
// BEGIN_NATIVE_PROPERTIES_CANCEL_UNDO_UI_V1
extension NativeLaunchTests {
    /// Real Name-property cancellation, native commit/Undo and cold readback.
    /// Reuses the original owned account, document and read-only body observer.
    @objc func testNativePropertyValueCancelAndUndoSurviveColdReopen() throws {
        executionTimeAllowance = 900
        let scope = UUID(), suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        app.launchEnvironment["PINKHA_NATIVE_ANCHOR_OBSERVATION"] = "1"
        let spaceName = "Property Undo Space " + suffix
        let originalName = "Property Original " + suffix
        let cancelledName = "Property Cancelled " + suffix
        let savedName = "Property Saved " + suffix
        let finalName = "Property Final " + suffix
        let body = "שלום מאפיינים 726 " + suffix
        var phase = "startup"
        var safeDocumentFixture = false
        var complete = false

        enum JourneyError: Error { case missingIdentity, unexpectedValue, captureUnavailable }

        func labels(_ values: [String]) -> NSPredicate {
            NSPredicate(format: "label IN %@", values)
        }
        func uniqueButton(_ query: XCUIElementQuery) throws -> XCUIElement {
            var selected: XCUIElement?
            let ready = NSPredicate { _, _ in
                let leaves = query.allElementsBoundByIndex.filter {
                    $0.exists && $0.isEnabled && $0.isHittable &&
                    $0.descendants(matching: .button).count == 0
                }
                guard leaves.count == 1 else { return false }
                selected = leaves[0]; return true
            }
            let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: ready, object: app)], timeout: 30)
            XCTAssertEqual(result, .completed, "One actual enabled Properties action is required at " + phase)
            guard result == .completed, let selected else { throw JourneyError.unexpectedValue }
            return selected
        }
        func byteValue(_ element: XCUIElement, expected: String) throws -> String {
            let ready = NSPredicate { _, _ in
                element.exists && element.isEnabled && element.isHittable &&
                (element.value as? String).map { Array($0.utf8) == Array(expected.utf8) } == true
            }
            waitFor(ready, object: element, timeout: 60)
            guard let value = element.value as? String, Array(value.utf8) == Array(expected.utf8) else {
                throw JourneyError.unexpectedValue
            }
            return value
        }
        let nameRow = app.buttons["any-native-property-name"]
        let typeRow = app.descendants(matching: .any).matching(identifier: "any-native-property-type").firstMatch
        let valueInput = app.descendants(matching: .any).matching(identifier: "any-native-property-value-input").firstMatch

        func openProperties() {
            tapWhenEnabled(app.buttons["any-native-document-properties"], timeout: 60)
            waitUntilEnabled(app.descendants(matching: .any).matching(identifier: "any-native-properties-list").firstMatch)
            waitUntilEnabled(typeRow)
        }
        func currentType() throws -> String {
            revealNativeProperty(app, typeRow, scrollDown: true)
            waitUntilEnabled(typeRow)
            guard let value = typeRow.value as? String, !value.isEmpty, value.utf8.count <= 1024 else {
                throw JourneyError.unexpectedValue
            }
            return value
        }
        func expectName(_ expected: String) throws {
            waitFor(NSPredicate(format: "exists == false"), object: valueInput, timeout: 60)
            guard !valueInput.exists else { throw JourneyError.unexpectedValue }
            revealNativeProperty(app, nameRow)
            _ = try byteValue(nameRow, expected: expected)
            XCTAssertFalse(valueInput.exists, "The real value editor must have dismissed.")
            XCTAssertFalse(app.alerts.firstMatch.exists)
        }
        func editName(from old: String, to new: String) throws {
            try expectName(old)
            nameRow.tap()
            _ = try byteValue(valueInput, expected: old)
            valueInput.tap()
            valueInput.typeKey("a", modifierFlags: .command)
            valueInput.typeText(XCUIKeyboardKey.delete.rawValue)
            valueInput.typeText(new)
            _ = try byteValue(valueInput, expected: new)
        }
        func capture(_ phaseName: String, expectedName: String, expectedType: String,
                     context: SemanticAnchorUIObservation) throws {
            phase = phaseName
            try expectName(expectedName)
            let observedType = try currentType()
            XCTAssertEqual(Array(observedType.utf8), Array(expectedType.utf8))
            try expectName(expectedName)
            guard safeDocumentFixture, app.state == .runningForeground,
                  !app.buttons["any-native-backup-continue"].exists,
                  !app.secureTextFields["any-native-account-restore-phrase"].exists else {
                throw JourneyError.captureUnavailable
            }
            let observedName = try byteValue(nameRow, expected: expectedName)
            let data = try JSONSerialization.data(withJSONObject: [
                "schema": "native-properties-cancel-undo-ui-v1", "phase": phaseName,
                "method": "testNativePropertyValueCancelAndUndoSurviveColdReopen",
                "ownedScope": scope.uuidString, "expectedName": expectedName, "observedName": observedName,
                "expectedType": expectedType, "observedType": observedType,
                "contextOrigin": "latest-original-read-only-native-body-observation-in-this-process",
                "appPID": context.pid, "documentGeneration": context.generation,
                "spaceSHA256": context.spaceSHA256, "objectSHA256": context.objectSHA256,
                "bodySHA256": Self.semanticHash(body), "valueEditorAbsent": !valueInput.exists,
                "testOnlyFixtureOrBypassMutations": 0, "directEngineCallsByTest": 0
            ], options: [.sortedKeys])
            let observation = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
            observation.name = "native-properties-undo-" + phaseName + "-observation"
            observation.lifetime = .keepAlways; add(observation)
            let tree = app.debugDescription
            guard tree.utf8.count <= 262_144 else { throw JourneyError.captureUnavailable }
            let ax = XCTAttachment(string: tree)
            ax.name = "native-properties-undo-" + phaseName + "-accessibility"
            ax.lifetime = .keepAlways; add(ax)
            let screenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
            screenshot.name = "native-properties-undo-" + phaseName + "-screenshot"
            screenshot.lifetime = .keepAlways; add(screenshot)
        }

        app.launch()
        defer {
            let marker = XCTAttachment(string: "phase=\(phase); complete=\(complete)")
            marker.name = "native-properties-undo-final-state"; marker.lifetime = .keepAlways; add(marker)
            // Never capture the recovery phrase or an account gate. This new
            // journey creates only its own document and never opens ShareLink.
            if safeDocumentFixture && app.state == .runningForeground &&
                !app.buttons["any-native-backup-continue"].exists &&
                !app.secureTextFields["any-native-account-restore-phrase"].exists {
                let tree = app.debugDescription
                if tree.utf8.count <= 262_144 {
                    let ax = XCTAttachment(string: tree)
                    ax.name = "native-properties-undo-final-accessibility"; ax.lifetime = .keepAlways; add(ax)
                } else {
                    XCTFail("Final owned Properties accessibility evidence exceeded the fixed bound.")
                }
                let shot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
                shot.name = "native-properties-undo-final-screenshot"; shot.lifetime = .keepAlways; add(shot)
            }
            app.terminate()
        }
        createOwnedWorkspace(app, spaceName: spaceName)
        try createNamedItemWithObservedTransition(app, action: "any-native-new-document", title: originalName)
        tapWhenEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        let editors = app.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-"))
        let editor = editors.firstMatch
        waitForNativeEditorInput(app, editor)
        editor.tap(); editor.typeText(body)
        semanticCommit(app, editor: editor, text: body)
        let initial = try semanticObservation(app, phase: "property-undo-initial-body") {
            $0.nativeMarkCount == 0 && $0.blocks.count == 1 && $0.blocks[0].textSHA256 == Self.semanticHash(body)
        }
        XCTAssertEqual(editors.count, 1)
        let blockIdentifier = editor.identifier
        guard blockIdentifier.hasPrefix("any-native-block-"),
              blockIdentifier.count > "any-native-block-".count else { throw JourneyError.missingIdentity }
        XCTAssertEqual(initial.blocks[0].blockSHA256, Self.semanticHash(String(blockIdentifier.dropFirst("any-native-block-".count))))
        safeDocumentFixture = true

        func sameBody(_ phaseName: String) throws -> SemanticAnchorUIObservation {
            phase = phaseName
            let actual = try semanticObservation(app, phase: phaseName) {
                $0.nativeMarkCount == 0 && $0.blocks.count == 1 &&
                $0.spaceSHA256 == initial.spaceSHA256 && $0.objectSHA256 == initial.objectSHA256 &&
                $0.blocks[0].blockSHA256 == initial.blocks[0].blockSHA256 &&
                $0.blocks[0].textSHA256 == Self.semanticHash(body) &&
                $0.blocks[0].sourceSHA256 == initial.blocks[0].sourceSHA256
            }
            XCTAssertEqual(editors.count, 1)
            XCTAssertEqual(editor.identifier, blockIdentifier)
            _ = try byteValue(editor, expected: body)
            return actual
        }
        func libraryDocument(expectedName: String, expectedIdentifier: String? = nil) throws -> XCUIElement {
            let query = app.buttons.matching(NSPredicate(
                format: "identifier BEGINSWITH %@ AND label == %@", "any-native-hierarchy-row-", expectedName))
            let row = try uniqueButton(query)
            if let expectedIdentifier { XCTAssertEqual(row.identifier, expectedIdentifier) }
            let objectID = String(row.identifier.dropFirst("any-native-hierarchy-row-".count))
            guard !objectID.isEmpty else { throw JourneyError.missingIdentity }
            XCTAssertEqual(Self.semanticHash(objectID), initial.objectSHA256)
            return row
        }

        openProperties()
        let typeName = try currentType()
        phase = "cancel-edited-name"
        try editName(from: originalName, to: cancelledName)
        try uniqueButton(app.navigationBars.buttons.matching(labels(["Cancel", "ביטול"]))).tap()
        try capture("cancel-restores-original-value", expectedName: originalName, expectedType: typeName, context: initial)

        phase = "save-name"
        try editName(from: originalName, to: savedName)
        tapWhenEnabled(app.buttons["any-native-property-save"])
        try capture("saved-name-readback", expectedName: savedName, expectedType: typeName, context: initial)
        phase = "undo-name"
        tapWhenEnabled(app.buttons["any-native-property-menu"])
        try uniqueButton(app.buttons.matching(labels(["Undo property change", "ביטול שינוי במאפיינים"]))).tap()
        try capture("undo-restores-original-value", expectedName: originalName, expectedType: typeName, context: initial)
        tapWhenEnabled(app.buttons["any-native-property-close"])
        let afterUndo = try sameBody("property-undo-before-cold")

        try uniqueButton(app.navigationBars.buttons.matching(labels(["Library", "ספרייה"]))).tap()
        let firstRow = try libraryDocument(expectedName: originalName)
        let documentIdentifier = firstRow.identifier
        phase = "cold-after-undo"
        reopenOwnedWorkspace(app, spaceName: spaceName)
        try libraryDocument(expectedName: originalName, expectedIdentifier: documentIdentifier).tap()
        let coldUndo = try sameBody("property-undo-cold-body")
        XCTAssertNotEqual(coldUndo.pid, afterUndo.pid)
        XCTAssertNotEqual(coldUndo.generation, afterUndo.generation)
        openProperties()
        try capture("cold-undo-persisted", expectedName: originalName, expectedType: typeName, context: coldUndo)

        // A newly mounted panel still admits a deliberate subsequent edit.
        phase = "save-after-cold-undo"
        try editName(from: originalName, to: finalName)
        tapWhenEnabled(app.buttons["any-native-property-save"])
        try capture("subsequent-save-readback", expectedName: finalName, expectedType: typeName, context: coldUndo)
        tapWhenEnabled(app.buttons["any-native-property-close"])
        let afterSave = try sameBody("property-subsequent-save-before-cold")
        phase = "cold-after-subsequent-save"
        reopenOwnedWorkspace(app, spaceName: spaceName)
        try libraryDocument(expectedName: finalName, expectedIdentifier: documentIdentifier).tap()
        let coldSave = try sameBody("property-subsequent-save-cold-body")
        XCTAssertNotEqual(coldSave.pid, afterSave.pid)
        XCTAssertNotEqual(coldSave.generation, afterSave.generation)
        openProperties()
        try capture("cold-subsequent-save-persisted", expectedName: finalName, expectedType: typeName, context: coldSave)
        complete = true
    }
}
// END_NATIVE_PROPERTIES_CANCEL_UNDO_UI_V1
