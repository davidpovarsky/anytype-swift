
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
        XCTAssertEqual(actualBytes, expectedBytes)
        XCTAssertEqual(Array(actual.utf16), Array(expected.utf16))
        XCTAssertEqual(Array(actualBytes.prefix(prefix.utf8.count)), Array(prefix.utf8))
        XCTAssertEqual(Array(actualBytes.suffix(suffix.utf8.count)), Array(suffix.utf8))
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
    }
}
// END_NATIVE_UNICODE_ANCHOR_REGRESSION_V1
