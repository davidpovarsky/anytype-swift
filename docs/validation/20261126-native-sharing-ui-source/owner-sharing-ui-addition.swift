extension NativeLaunchTests {
    // BEGIN_NATIVE_SHARING_OWNER_UI_V1
    /// Exercise the shared permissions screen against the real Any account and
    /// signed invitation store. No invitation token or recovery phrase is read.
    func testNativeSharingInvitationConfirmationCancellationAndColdReopen() throws {
        executionTimeAllowance = 900
        let scope = UUID()
        let app = makeApplication(scope: scope)
        let spaceName = "Sharing UI Space " + String(scope.uuidString.prefix(8))
        app.launch()
        defer { app.terminate() }
        createOwnedWorkspace(app, spaceName: spaceName)

        func uniqueButton(_ query: XCUIElementQuery, timeout: TimeInterval = 30) -> XCUIElement {
            let ready = NSPredicate { _, _ in
                let leaves = query.allElementsBoundByIndex.filter {
                    $0.descendants(matching: .button).count == 0
                }
                return leaves.count == 1 && leaves[0].exists
                    && leaves[0].isEnabled && leaves[0].isHittable
            }
            waitFor(ready, object: app, timeout: timeout)
            let leaves = query.allElementsBoundByIndex.filter {
                $0.descendants(matching: .button).count == 0
            }
            XCTAssertEqual(leaves.count, 1, "One rendered, actionable sharing control is required.")
            return leaves.first ?? query.firstMatch
        }
        func identifier(_ value: String) -> XCUIElementQuery {
            app.buttons.matching(identifier: value)
        }
        func labels(_ values: [String]) -> NSPredicate {
            NSPredicate(format: "label IN %@", values)
        }
        let createID = "pinkha.sharing.createInvitation"
        let shareID = "pinkha.sharing.shareInvitation"
        let revokeLabels = ["ביטול הזמנה", "Revoke invitation"]
        let closeLabels = ["סגירה", "Close"]

        func assertOwner() {
            let owner = app.staticTexts.matching(labels(["בעלים", "owner"])).firstMatch
            let you = app.staticTexts.matching(labels(["אתה", "You"])).firstMatch
            waitUntilEnabled(owner, timeout: 30)
            waitUntilEnabled(you, timeout: 30)
            XCTAssertFalse(app.staticTexts.matching(labels([
                "לא ניתן לרענן. בדוק את החיבור ונסה שוב.",
                "Unable to refresh. Check the connection and try again.",
                "לא ניתן לאמת את ביצוע הפעולה. רענן לפני ניסיון נוסף.",
                "The action could not be confirmed. Refresh before trying again."
            ])).firstMatch.exists)
        }
        func openSharing() {
            uniqueButton(identifier("any-native-members"), timeout: 60).tap()
            let screen = app.descendants(matching: .any)
                .matching(identifier: "pinkha.sharing.members").firstMatch
            waitUntilEnabled(screen, timeout: 30)
            waitUntilEnabled(app.navigationBars.matching(labels([
                "חברים והזמנות", "Members and invitations"
            ])).firstMatch, timeout: 30)
            assertOwner()
        }
        func assertInvitation(_ present: Bool) {
            let expected = NSPredicate { _, _ in
                let share = identifier(shareID).allElementsBoundByIndex.filter {
                    $0.descendants(matching: .button).count == 0
                }
                let revoke = app.buttons.matching(labels(revokeLabels))
                    .allElementsBoundByIndex.filter {
                        $0.descendants(matching: .button).count == 0
                    }
                let create = identifier(createID).allElementsBoundByIndex.filter {
                    $0.descendants(matching: .button).count == 0
                }
                if present {
                    return share.count == 1 && revoke.count == 1
                        && share[0].isEnabled && revoke[0].isEnabled && create.isEmpty
                }
                return share.isEmpty && revoke.isEmpty && create.count == 1
                    && create[0].isEnabled
            }
            waitFor(expected, object: app, timeout: 60)
            assertOwner()
        }
        func confirm(_ accepted: Bool, message: [String]) {
            let alert = app.alerts.firstMatch
            waitUntilEnabled(alert, timeout: 30)
            XCTAssertEqual(app.alerts.count, 1)
            XCTAssertTrue(alert.staticTexts.matching(labels([
                "אישור שינוי גישה", "Confirm access change"
            ])).firstMatch.exists)
            XCTAssertTrue(alert.staticTexts.matching(labels(message)).firstMatch.exists)
            uniqueButton(alert.buttons.matching(labels(accepted
                ? ["אישור", "Confirm"] : ["ביטול", "Cancel"]))).tap()
            waitFor(NSPredicate(format: "exists == false"), object: alert, timeout: 30)
        }
        func coldOpenSharing() {
            uniqueButton(app.navigationBars.buttons.matching(labels(closeLabels))).tap()
            waitFor(NSPredicate(format: "exists == false"),
                    object: app.descendants(matching: .any)
                        .matching(identifier: "pinkha.sharing.members").firstMatch, timeout: 30)
            reopenOwnedWorkspace(app, spaceName: spaceName)
            openSharing()
        }
        func checkpoint(_ phase: String) {
            // The screen contains controls and membership, not the invitation's
            // secret payload. Never request its ShareLink or a complete AX tree.
            let attachment = XCTAttachment(string: phase)
            attachment.name = "native-sharing-owner-stage"
            attachment.lifetime = .keepAlways
            add(attachment)
        }

        let createMessage = [
            "ליצור הזמנה שתאפשר לבקש גישה למרחב הזה?",
            "Create an invitation that allows someone to request access to this space?"
        ]
        let revokeMessage = [
            "לבטל את ההזמנה הזו? לא יהיה אפשר לבקש להצטרף באמצעותה.",
            "Revoke this invitation? It will no longer allow requests to join."
        ]
        openSharing()
        assertInvitation(false)
        uniqueButton(identifier(createID)).tap()
        confirm(false, message: createMessage)
        assertInvitation(false)
        coldOpenSharing()
        assertInvitation(false)
        checkpoint("create-cancelled-and-absent-after-new-app-process")

        uniqueButton(identifier(createID)).tap()
        confirm(true, message: createMessage)
        assertInvitation(true)
        coldOpenSharing()
        assertInvitation(true)
        checkpoint("confirmed-invitation-retained-after-new-app-process")

        uniqueButton(app.buttons.matching(labels(revokeLabels))).tap()
        confirm(false, message: revokeMessage)
        assertInvitation(true)
        coldOpenSharing()
        assertInvitation(true)
        checkpoint("revocation-cancelled-and-invitation-retained-after-new-app-process")

        uniqueButton(app.buttons.matching(labels(revokeLabels))).tap()
        confirm(true, message: revokeMessage)
        assertInvitation(false)
        coldOpenSharing()
        assertInvitation(false)
        checkpoint("confirmed-revocation-retained-after-new-app-process")
    }
    // END_NATIVE_SHARING_OWNER_UI_V1

}

