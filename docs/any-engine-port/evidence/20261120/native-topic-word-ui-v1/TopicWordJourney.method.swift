    func testTopicAndWordLinksDriveDerivedRelatedDocumentsAfterColdReopen() {
        let scope = UUID()
        let suffix = String(scope.uuidString.prefix(8))
        let app = makeApplication(scope: scope)
        let spaceName = "Topic Word UI Space " + suffix
        let documentA = "Topic Word Document A " + suffix
        let documentB = "Topic Word Document B " + suffix
        let linkedPrefix = "any-native-linked-source-"
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentA)
        waitUntilEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)

        // Resolve real public provider candidates through the retained search.
        // Topic and Word reader pages are intentionally not assumed here.
        tapWhenEnabled(app.buttons["any-native-document-sources"])
        let scopes = app.segmentedControls.firstMatch
        tapWhenEnabled(scopes.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "נושאים", "Topics")).firstMatch)
        let search = app.searchFields.firstMatch
        waitUntilEnabled(search)
        search.tap(); search.typeText("Shabbat")
        let topicResult = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@",
            "any-native-source-result-topic:", "shabbat")).firstMatch
        waitFor(NSPredicate(format: "exists == true"), object: topicResult, timeout: 60)
        let topicResultID = String(topicResult.identifier.dropFirst("any-native-source-result-".count))
        XCTAssertTrue(topicResultID.hasPrefix("topic:"))
        let topicIdentity = topicResult.value as? String ?? ""
        XCTAssertEqual(topicIdentity, "shabbat")
        let topicLinkID = "any-native-source-link-" + topicResultID
        tapWhenEnabled(app.buttons[topicLinkID], timeout: 60)
        let linkedTopicA = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@", linkedPrefix, topicIdentity)).firstMatch
        waitFor(NSPredicate(format: "exists == true"), object: linkedTopicA, timeout: 60)
        let topicAssociationA = String(linkedTopicA.identifier.dropFirst(linkedPrefix.count))
        let topicTitle = linkedTopicA.label
        XCTAssertFalse(topicAssociationA.isEmpty)
        XCTAssertFalse(topicTitle.isEmpty)

        // Changing the actual segmented category clears the previous query.
        // Capture the acknowledged canonical word, not a guessed lexical label.
        tapWhenEnabled(scopes.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מילים", "Words")).firstMatch)
        waitUntilEnabled(search)
        search.tap(); search.typeText("בראשית")
        let wordLink = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-source-link-word:")).firstMatch
        tapWhenEnabled(wordLink, timeout: 60)
        let linkedWordA = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND identifier != %@",
            linkedPrefix, linkedPrefix + topicAssociationA)).firstMatch
        waitFor(NSPredicate(format: "exists == true"), object: linkedWordA, timeout: 60)
        let wordAssociationA = String(linkedWordA.identifier.dropFirst(linkedPrefix.count))
        let wordTitle = linkedWordA.label
        let wordIdentity = linkedWordA.value as? String ?? ""
        XCTAssertFalse(wordAssociationA.isEmpty)
        XCTAssertNotEqual(wordAssociationA, topicAssociationA)
        XCTAssertFalse(wordTitle.isEmpty)
        XCTAssertFalse(wordIdentity.isEmpty)
        XCTAssertEqual(app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", linkedPrefix)).count, 2)
        tapWhenEnabled(app.buttons["any-native-source-search-done"])

        let topicMenuA = "any-native-derived-actions-" + topicAssociationA
        let wordMenuA = "any-native-derived-actions-" + wordAssociationA
        tapWhenEnabled(app.buttons["any-native-document-properties"])
        waitUntilEnabled(app.buttons[topicMenuA], timeout: 60)
        waitUntilEnabled(app.buttons[wordMenuA], timeout: 60)
        XCTAssertTrue(app.buttons[topicMenuA].label.contains(topicTitle))
        XCTAssertTrue(app.buttons[wordMenuA].label.contains(wordTitle))
        tapWhenEnabled(app.buttons["any-native-property-close"])

        // Create a second ordinary document and link the identical returned
        // Topic through the same public provider/UI, without linking the Word.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        createNamedItem(app, action: "any-native-new-document", title: documentB)
        waitUntilEnabled(app.buttons["any-native-add-paragraph"], timeout: 60)
        tapWhenEnabled(app.buttons["any-native-document-sources"])
        tapWhenEnabled(scopes.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "נושאים", "Topics")).firstMatch)
        waitUntilEnabled(search)
        search.tap(); search.typeText("Shabbat")
        tapWhenEnabled(app.buttons[topicLinkID], timeout: 60)
        let linkedTopicB = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND value == %@", linkedPrefix, topicIdentity)).firstMatch
        waitFor(NSPredicate(format: "exists == true"), object: linkedTopicB, timeout: 60)
        let topicAssociationB = String(linkedTopicB.identifier.dropFirst(linkedPrefix.count))
        let topicTitleB = linkedTopicB.label
        XCTAssertFalse(topicAssociationB.isEmpty)
        XCTAssertEqual(app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", linkedPrefix)).count, 1)
        tapWhenEnabled(app.buttons["any-native-source-search-done"])

        // The real derived-property menu queries the native Topic index. Both
        // committed documents must appear, then the normal owned-sheet route
        // must dismiss the child and parent before opening A's mounted editor.
        tapWhenEnabled(app.buttons["any-native-document-properties"])
        tapWhenEnabled(app.buttons["any-native-derived-actions-" + topicAssociationB], timeout: 60)
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מסמכים מקושרים", "Related documents")).firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[topicTitleB], timeout: 60)
        waitUntilEnabled(app.buttons[documentA].firstMatch, timeout: 60)
        waitUntilEnabled(app.buttons[documentB].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons[documentA].firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[documentA], timeout: 60)
        waitFor(NSPredicate(format: "exists == false"), object: app.buttons["any-native-property-close"], timeout: 30)
        waitUntilEnabled(app.buttons["any-native-document-properties"])

        tapWhenEnabled(app.buttons["any-native-document-properties"])
        waitUntilEnabled(app.buttons[topicMenuA], timeout: 60)
        tapWhenEnabled(app.buttons[wordMenuA], timeout: 60)
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מסמכים מקושרים", "Related documents")).firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[wordTitle], timeout: 60)
        waitUntilEnabled(app.buttons[documentA].firstMatch, timeout: 60)
        XCTAssertFalse(app.buttons[documentB].exists, "A Topic-only document must not enter the Word index.")

        // Reopen from disk without relinking. The exact canonical item IDs and
        // labels must remain present, and Word-related results remain distinct.
        reopenOwnedWorkspace(app, spaceName: spaceName)
        tapWhenEnabled(app.buttons[documentA].firstMatch, timeout: 60)
        tapWhenEnabled(app.buttons["any-native-document-properties"], timeout: 60)
        waitUntilEnabled(app.buttons[topicMenuA], timeout: 60)
        waitUntilEnabled(app.buttons[wordMenuA], timeout: 60)
        XCTAssertTrue(app.buttons[topicMenuA].label.contains(topicTitle))
        XCTAssertTrue(app.buttons[wordMenuA].label.contains(wordTitle))
        XCTAssertEqual(app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "any-native-derived-actions-")).count, 2)
        tapWhenEnabled(app.buttons[wordMenuA])
        tapWhenEnabled(app.buttons.matching(NSPredicate(
            format: "label == %@ OR label == %@", "מסמכים מקושרים", "Related documents")).firstMatch)
        waitFor(NSPredicate(format: "exists == true"), object: app.navigationBars[wordTitle], timeout: 60)
        waitUntilEnabled(app.buttons[documentA].firstMatch, timeout: 60)
        XCTAssertFalse(app.buttons[documentB].exists)
    }
