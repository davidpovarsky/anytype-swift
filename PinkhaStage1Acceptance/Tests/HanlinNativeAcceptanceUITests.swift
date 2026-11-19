import Foundation
import XCTest

/// Requires a fresh disposable simulator populated by the separate real native
/// preparation test. The app's Debug-only driver calls the actual host/SDK;
/// this XCTest presses only production UI controls and native consent actions.
@MainActor
final class HanlinNativeAcceptanceUITests: XCTestCase {
    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private var fixture: Fixture!

    override func setUpWithError() throws {
        continueAfterFailure = false
        let environment = ProcessInfo.processInfo.environment
        XCTAssertEqual(environment["PINKHA_HANLIN_NATIVE_UI_TESTING"], "1")
        XCTAssertEqual(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"], "1")
        guard environment["PINKHA_HANLIN_NATIVE_UI_TESTING"] == "1",
              environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1" else {
            throw NSError(domain: "HanlinNativeAcceptance", code: 1)
        }
        let json = try XCTUnwrap(environment["PINKHA_HANLIN_NATIVE_FIXTURE_JSON"])
        XCTAssertLessThanOrEqual(json.utf8.count, 16_384)
        fixture = try JSONDecoder().decode(Fixture.self, from: Data(json.utf8))
        XCTAssertEqual(fixture.sourceSHA, try XCTUnwrap(environment["PINKHA_HANLIN_NATIVE_SOURCE_SHA"]))
        XCTAssertEqual(fixture.runID, try XCTUnwrap(environment["PINKHA_HANLIN_NATIVE_RUN_ID"]))
        XCTAssertEqual(fixture.runAttempt, try XCTUnwrap(environment["PINKHA_HANLIN_NATIVE_RUN_ATTEMPT"]))
        XCTAssertEqual(fixture.sourceSHA.count, 40)
        XCTAssertTrue(fixture.sourceSHA.allSatisfy(\.isHexDigit))
        XCTAssertFalse(fixture.accountID.isEmpty)
        XCTAssertNotEqual(fixture.spaceID, fixture.alternateSpaceID)
        XCTAssertFalse(fixture.sourceObjectID.isEmpty)
        XCTAssertEqual(fixture.createdTitle, "Hanlin native created " + fixture.fixtureID.uuidString)
        XCTAssertEqual(fixture.cancelledTitle, "Hanlin native cancelled " + fixture.fixtureID.uuidString)

        app.launchEnvironment = [
            "PINKHA_HANLIN_NATIVE_UI": "1",
            "PINKHA_SIMULATOR_UI_DISPOSABLE": "1",
            "PINKHA_HANLIN_NATIVE_FIXTURE_ID": fixture.fixtureID.uuidString,
            "PINKHA_HANLIN_NATIVE_SOURCE_SHA": fixture.sourceSHA,
            "PINKHA_HANLIN_NATIVE_RUN_ID": fixture.runID,
            "PINKHA_HANLIN_NATIVE_RUN_ATTEMPT": fixture.runAttempt,
            "PINKHA_UI27_ROUTE_OBSERVATION": "1"
        ]
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        XCUIDevice.shared.orientation = .portrait
    }

    func testRealNativeConsentCreatePageAndAuthorityRevocation() throws {
        // This lane intentionally cold-launches the actual prepared app. It does
        // not claim process reuse with an earlier Inspector acceptance lane.
        if app.state != .notRunning { app.terminate() }
        app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 30))
        let home = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ OR label == %@ OR identifier == %@ OR label == %@",
            "SpaceHub", "SpaceHub", "NewSpaceButton", "NewSpaceButton"
        )).firstMatch
        XCTAssertTrue(home.waitForExistence(timeout: 45), "The actual Home must finish its native account/Space handshake")
        var route = URLComponents()
        route.scheme = "anytype"
        route.host = "object"
        route.queryItems = [URLQueryItem(name: "objectId", value: fixture.sourceObjectID),
                            URLQueryItem(name: "spaceId", value: fixture.spaceID)]
        XCUIDevice.shared.system.open(try XCTUnwrap(route.url))
        // The first entry uses the same exact document and touch-readiness
        // requirements as later presentations, within the existing 45s + 15s.
        try openHanlinOnOriginalDocument()

        try waitForPhase("AWAIT_READ_CONSENT", timeout: 20)
        try chatButton(identifier: "pinkha.hanlin.share-context",
                       label: "Allow access to this document or selection").tap()
        let readAlert = try readConsentPrompt()
        readAlert.buttons["pinkha.hanlin.consent.read-context.allow"].tap()

        // Inspect the actual requested title AND original Space before each
        // decision. An old alert with the same title cannot satisfy the next step.
        let cancelled = try createAlert(for: fixture.cancelledTitle)
        attachScreenshot("hanlin-native-create-cancel-prompt")
        cancelled.buttons["pinkha.hanlin.consent.create-page.cancel"].tap()
        let confirmed = try createAlert(for: fixture.createdTitle)
        attachScreenshot("hanlin-native-create-confirm-prompt")
        confirmed.buttons["pinkha.hanlin.consent.create-page.allow"].tap()

        try waitForPhase("READY_TO_CLOSE", timeout: 45)
        let beforeClose = try currentReceipt()
        XCTAssertEqual(beforeClose.checks["real_native_context_text_read"], true)
        XCTAssertEqual(beforeClose.checks["native_confirm_creates_exact_page"], true)
        XCTAssertFalse(try XCTUnwrap(beforeClose.createdObjectID).isEmpty)
        XCTAssertFalse(beforeClose.providerConfigured)
        XCTAssertNil(beforeClose.nativeReturn, "A queued request or retained editor is not a native return receipt")
        attachScreenshot("hanlin-native-read-and-create-complete")
        let nativeReturn = try verifyNativeReturn(before: beforeClose)
        try verifyBackgroundAndPendingConsent(createdObjectID: try XCTUnwrap(beforeClose.createdObjectID))

        try waitForPhase("NATIVE_ACCEPTANCE_PASS", timeout: 90)
        try requireLoggedOutRoot()
        let final = try currentReceipt()
        XCTAssertEqual(final.logoutRootState, "auth")
        XCTAssertEqual(final.fixtureID, fixture.fixtureID)
        XCTAssertEqual(final.sourceSHA, fixture.sourceSHA)
        XCTAssertEqual(final.runID, fixture.runID)
        XCTAssertEqual(final.runAttempt, fixture.runAttempt)
        XCTAssertEqual(final.sessionID, beforeClose.sessionID)
        XCTAssertEqual(final.processID, beforeClose.processID)
        XCTAssertGreaterThan(final.processID, 0)
        XCTAssertEqual(final.createdObjectID, beforeClose.createdObjectID)
        XCTAssertEqual(final.navigationContext, beforeClose.navigationContext)
        XCTAssertEqual(final.nativeReturn, nativeReturn, "Later presentations must preserve the original return metadata")
        XCTAssertNil(final.failure)
        XCTAssertFalse(final.providerConfigured)
        XCTAssertNotNil(final.finishedAt)
        XCTAssertEqual(Set(final.checks.keys), Self.requiredChecks)
        XCTAssertTrue(final.checks.values.allSatisfy { $0 })
        let sessions = [final.sessionID, try XCTUnwrap(final.backgroundSessionID),
                        try XCTUnwrap(final.staleConsentSessionID), try XCTUnwrap(final.freshSessionID)]
        XCTAssertEqual(Set(sessions).count, 4, "Each UI presentation must have fresh authority")
        XCTAssertEqual(Set(final.invalidationCauses.keys), Set(sessions.map(\.uuidString)))
        XCTAssertTrue(final.invalidationCauses.values.allSatisfy {
            ["nativeAuthorityChanged", "presentationRemoved", "interactivePresentationDismissal", "explicitCloseOrOwner"].contains($0)
        })
        XCTAssertEqual(Set(final.sceneEventCounts.keys), Self.sceneEventKeys)
        XCTAssertEqual(Set(final.backgroundCycleSceneDelta.keys), Self.sceneEventKeys)
        XCTAssertEqual(Set(final.documentExitSceneDelta.keys), Self.sceneEventKeys)
        XCTAssertTrue(final.sceneEventCounts.values.allSatisfy { $0 >= 0 })
        XCTAssertTrue(final.backgroundCycleSceneDelta.values.allSatisfy { $0 >= 0 })
        XCTAssertTrue(final.documentExitSceneDelta.values.allSatisfy { $0 >= 0 })
        for event in Self.sceneEventKeys {
            XCTAssertGreaterThanOrEqual(final.sceneEventCounts[event, default: -1], final.backgroundCycleSceneDelta[event, default: 0])
            XCTAssertGreaterThanOrEqual(final.sceneEventCounts[event, default: -1], final.documentExitSceneDelta[event, default: 0])
        }
        for event in ["sceneDidEnterBackground", "sceneWillEnterForeground", "sceneDidActivate"] {
            XCTAssertGreaterThan(final.backgroundCycleSceneDelta[event, default: 0], 0)
        }
        XCTAssertEqual(final.documentExitAttribution,
            final.documentExitSceneDelta.values.contains(where: { $0 > 0 })
                ? "navigationWithSceneTransition" : "navigationWithoutSceneTransition")
        let attachment = XCTAttachment(data: try JSONEncoder().encode(final),
                                       uniformTypeIdentifier: "public.json")
        attachment.name = "hanlin-native-source-bound-result"
        attachment.lifetime = .keepAlways
        add(attachment)
        attachScreenshot("hanlin-native-authority-revocations-complete")
    }

    private func requireLoggedOutRoot() throws {
        // These are the exact English labels of the two original PrimaryAuthView
        // actions. Observe them; do not create an account or supply credentials.
        let login = app.buttons.matching(NSPredicate(format: "label == %@", "I already have a key"))
        let join = app.buttons.matching(NSPredicate(format: "label == %@", "I am new here"))
        try requireReady(controls: [login.firstMatch, join.firstMatch], timeout: 20,
                         diagnosticName: "hanlin-native-logged-out-root")
        XCTAssertEqual(login.count, 1)
        XCTAssertEqual(join.count, 1)
        XCTAssertEqual(app.staticTexts.matching(NSPredicate(format: "label == %@", "Add a Channel Home?")).count, 0,
                       "No retired Space picker may remain over the auth root")
        XCTAssertEqual(app.staticTexts.matching(NSPredicate(format: "label == %@", "Error: not logged in (unknownError)")).count, 0,
                       "Retired bootstrap work must not reach middleware after logout")
        let home = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@", "SpaceHub", "NewSpaceButton"))
        XCTAssertEqual(home.count, 0, "The old authenticated Space root must be unmounted")
        let originalEditor = "pinkha-ui27-editor:\(fixture.spaceID):\(fixture.sourceObjectID)"
        XCTAssertFalse(app.otherElements.matching(NSPredicate(
            format: "identifier == %@", originalEditor)).firstMatch.exists,
            "The original source editor must not remain mounted after logout")
    }

    private func verifyNativeReturn(before: Receipt) throws -> NativeReturnReceipt {
        let original = before.navigationContext
        XCTAssertEqual(original.app, "anytype")
        XCTAssertEqual(original.account, fixture.accountID)
        XCTAssertEqual(original.workspace, fixture.spaceID)
        XCTAssertEqual(original.space, fixture.spaceID)
        XCTAssertEqual(original.objectReference, fixture.sourceObjectID)
        XCTAssertTrue(original.selectionReferences.isEmpty, "This fixture proves document return only")
        XCTAssertFalse(try XCTUnwrap(original.sourceRevision).isEmpty)
        try chatButton(identifier: "pinkha.hanlin.return-to-source", label: "Return to document").tap()
        try waitForPhase("AWAIT_BACKGROUND_PRESENTATION", timeout: 20)
        try requireMountedDocument(fixture.sourceObjectID)
        let after = try currentReceipt()
        let nativeReturn = try XCTUnwrap(after.nativeReturn)
        XCTAssertEqual(after.sessionID, before.sessionID)
        XCTAssertEqual(after.processID, before.processID)
        XCTAssertEqual(after.navigationContext, original)
        XCTAssertEqual(nativeReturn.sessionID, before.sessionID)
        XCTAssertEqual(nativeReturn.requestID, nativeReturn.queuedRequestID)
        XCTAssertEqual(nativeReturn.context, original)
        XCTAssertEqual(nativeReturn.objectReference, fixture.sourceObjectID)
        XCTAssertNil(nativeReturn.blockReference)
        XCTAssertTrue(nativeReturn.presentationAcknowledged)
        XCTAssertEqual(after.checks["native_return_mounted_original_document"], true)
        XCTAssertEqual(after.checks["closed_presentation_denies_read_and_create"], true)
        XCTAssertFalse(after.providerConfigured)
        attachScreenshot("hanlin-native-original-document-return")
        return nativeReturn
    }

    private func verifyBackgroundAndPendingConsent(createdObjectID: String) throws {
        try waitForPhase("AWAIT_BACKGROUND_PRESENTATION", timeout: 20)
        try openHanlinOnOriginalDocument()
        try waitForPhase("AWAIT_BACKGROUND_READ_CONSENT", timeout: 20)
        try allowNativeReadConsent()
        try waitForPhase("READY_FOR_BACKGROUND", timeout: 30)
        let beforeBackground = try currentReceipt()
        XCTAssertEqual(beforeBackground.checks["background_presentation_had_live_read_access"], true)
        XCTAssertNotNil(beforeBackground.backgroundSessionID)
        attachScreenshot("hanlin-native-before-background")

        XCUIDevice.shared.press(.home)
        XCTAssertTrue(app.wait(for: .runningBackground, timeout: 10) || app.state == .runningBackgroundSuspended,
                      "The actual app must leave the foreground without being terminated")
        app.activate()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 20))
        try waitForPhase("AWAIT_STALE_CONSENT_PRESENTATION", timeout: 30)
        let returned = try currentReceipt()
        XCTAssertEqual(returned.processID, beforeBackground.processID, "activate must preserve the tested process")
        XCTAssertEqual(returned.backgroundSessionID, beforeBackground.backgroundSessionID)
        XCTAssertEqual(returned.checks["native_background_foreground_observed"], true)
        XCTAssertEqual(returned.checks["backgrounded_presentation_denies_read_and_create"], true)
        attachScreenshot("hanlin-native-foreground-old-authority-denied")

        try openHanlinOnOriginalDocument()
        try waitForPhase("AWAIT_STALE_READ_CONSENT", timeout: 20)
        try chatButton(identifier: "pinkha.hanlin.share-context",
                       label: "Allow access to this document or selection").tap()
        let oldAlert = try readConsentPrompt()
        try waitForPhase("READY_TO_LEAVE_WITH_PENDING_CONSENT", timeout: 20)
        let pending = try currentReceipt()
        attachScreenshot("hanlin-native-pending-consent-before-document-exit")
        // Do not press Allow or manufacture a response. The ordinary object URL
        // traverses SpaceHub's native dismiss-all-presented and document route.
        try openDocument(createdObjectID)
        XCTAssertFalse(oldAlert.exists, "The old native consent must not cover the new document")
        try waitForPhase("AWAIT_FRESH_PRESENTATION", timeout: 30)
        let departed = try currentReceipt()
        XCTAssertEqual(departed.staleConsentSessionID, pending.staleConsentSessionID)
        XCTAssertEqual(departed.processID, pending.processID)
        XCTAssertEqual(departed.checks["pending_read_consent_dismissed_on_document_exit"], true)
        XCTAssertEqual(departed.checks["departed_document_presentation_denies_read_and_create"], true)
        attachScreenshot("hanlin-native-new-document-old-consent-denied")

        try openDocument(fixture.sourceObjectID)
        try openHanlinOnOriginalDocument()
        try waitForPhase("AWAIT_FRESH_READ_CONSENT", timeout: 20)
        let fresh = try currentReceipt()
        XCTAssertEqual(fresh.checks["fresh_presentation_requires_new_native_consent"], true)
        XCTAssertNotEqual(fresh.freshSessionID, fresh.staleConsentSessionID)
        try allowNativeReadConsent()
        try waitForPhase("READY_TO_CLOSE_FRESH", timeout: 30)
        XCTAssertEqual(try currentReceipt().checks["fresh_presentation_reads_original_document_only"], true)
        attachScreenshot("hanlin-native-fresh-original-document-consent")
        try chatButton(identifier: "pinkha.hanlin.close", label: "Close").tap()
    }

    private func openHanlinOnOriginalDocument() throws {
        try requireMountedDocument(fixture.sourceObjectID)
        let button = app.buttons["pinkha.hanlin.open"].firstMatch
        try requireReady(controls: [button], timeout: 15,
                         diagnosticName: "hanlin-native-entry-readiness")
        button.tap()
    }

    private func allowNativeReadConsent() throws {
        try chatButton(identifier: "pinkha.hanlin.share-context",
                       label: "Allow access to this document or selection").tap()
        let alert = try readConsentPrompt()
        alert.buttons["pinkha.hanlin.consent.read-context.allow"].tap()
    }

    private func openDocument(_ objectID: String) throws {
        var route = URLComponents()
        route.scheme = "anytype"; route.host = "object"
        route.queryItems = [URLQueryItem(name: "objectId", value: objectID),
                            URLQueryItem(name: "spaceId", value: fixture.spaceID)]
        XCUIDevice.shared.system.open(try XCTUnwrap(route.url))
        try requireMountedDocument(objectID)
    }

    private func requireMountedDocument(_ objectID: String) throws {
        let identifier = "pinkha-ui27-editor:\(fixture.spaceID):\(objectID)"
        // Keep the full native identifier; direct identifier queries have a
        // length limit that these real Space/object identities can exceed.
        let editor = app.otherElements.matching(NSPredicate(format: "identifier == %@", identifier)).firstMatch
        try requireReady(controls: [editor], timeout: 45,
                         diagnosticName: "hanlin-native-editor-readiness")
    }

    private var status: XCUIElement {
        app.staticTexts["pinkha.hanlin.native-acceptance-status"].firstMatch
    }

    private func waitForPhase(_ phase: String, timeout: TimeInterval) throws {
        let expected = NSPredicate(format: "exists == true AND label IN %@",
                                   [phase, "NATIVE_ACCEPTANCE_FAIL", "FAIL_SETUP"])
        let expectation = XCTNSPredicateExpectation(predicate: expected, object: status)
        let result = XCTWaiter.wait(for: [expectation], timeout: timeout)
        XCTAssertEqual(result, .completed, "Native phase \(phase) was not reached")
        XCTAssertEqual(status.label, phase, "Native diagnostic failed: \(status.value ?? "no receipt")")
    }

    private func currentReceipt() throws -> Receipt {
        let value = try XCTUnwrap(status.value as? String)
        return try JSONDecoder().decode(Receipt.self, from: Data(value.utf8))
    }

    private func chatButton(identifier: String, label: String) throws -> XCUIElement {
        // SwiftUI may propagate its root identifier. Both alternatives refer to
        // the same explicit production control; no coordinate or consent bypass.
        let button = app.buttons.matching(NSPredicate(format: "identifier == %@ OR label == %@",
                                                       identifier, label)).firstMatch
        try requireReady(controls: [button], timeout: 10,
                         diagnosticName: "hanlin-native-chat-control-readiness")
        return button
    }

    private func readConsentPrompt() throws -> XCUIElement {
        let identifier = "pinkha.hanlin.consent.read-context"
        let prompt = app.otherElements[identifier].firstMatch
        let title = prompt.staticTexts[identifier + ".title"]
        let allow = prompt.buttons[identifier + ".allow"]
        try requireReady(controls: [allow], existing: [prompt, title], timeout: 15,
                         diagnosticName: "hanlin-native-read-consent-readiness")
        XCTAssertEqual(title.label, "Allow document text access?")
        XCTAssertEqual(allow.label, "Allow for this presentation")
        return prompt
    }

    private func createAlert(for title: String) throws -> XCUIElement {
        let identifier = "pinkha.hanlin.consent.create-page"
        let alert = app.otherElements[identifier].firstMatch
        let promptTitle = alert.staticTexts[identifier + ".title"]
        try requireReady(controls: [], existing: [alert, promptTitle], timeout: 15,
                         diagnosticName: "hanlin-native-create-prompt-readiness")
        XCTAssertEqual(promptTitle.label, "Create a new page?")
        let exactOperation = alert.staticTexts.matching(NSPredicate(
            format: "label CONTAINS %@ AND label CONTAINS %@", title, fixture.spaceID
        )).firstMatch
        let cancel = alert.buttons[identifier + ".cancel"]
        let allow = alert.buttons[identifier + ".allow"]
        // Reuse the existing second 15s window for this exact operation and
        // both choices; readiness does not replace title/Space/label assertions.
        try requireReady(controls: [cancel, allow], existing: [exactOperation], timeout: 15,
                         diagnosticName: "hanlin-native-create-operation-readiness")
        XCTAssertTrue(exactOperation.exists, "The actual consent must name this title and original Space")
        XCTAssertEqual(cancel.label, "Cancel")
        XCTAssertEqual(allow.label, "Create page")
        return alert
    }

    /// All expectations share one caller-owned deadline. Existence alone can
    /// precede hit testing during native navigation or presentation transitions.
    private func requireReady(controls: [XCUIElement], existing: [XCUIElement] = [],
                              timeout: TimeInterval, diagnosticName: String) throws {
        let touchReady = controls.map {
            XCTNSPredicateExpectation(
                predicate: NSPredicate(format: "exists == true AND hittable == true"), object: $0)
        }
        let present = existing.map {
            XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true"), object: $0)
        }
        let result = XCTWaiter.wait(for: touchReady + present, timeout: timeout)
        if result != .completed {
            let queries = (controls + existing).map(\.debugDescription).joined(separator: "\n\n")
            let attachment = XCTAttachment(string: "App:\n" + app.debugDescription + "\n\nTargets:\n" + queries)
            attachment.name = diagnosticName
            attachment.lifetime = .keepAlways
            add(attachment)
            attachScreenshot(diagnosticName + "-failure")
        }
        XCTAssertEqual(result, .completed,
                       "The exact native controls must become ready within their existing \(timeout)-second budget")
        for control in controls { XCTAssertTrue(control.isHittable) }
    }

    private func attachScreenshot(_ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private static let requiredChecks: Set<String> = [
        "middleware_logging_disabled", "read_denied_before_native_consent",
        "real_native_context_text_read", "native_cancel_prevents_write",
        "native_confirm_creates_exact_page", "created_page_read_back_by_journal_id",
        "replay_does_not_create_duplicate", "cancelled_title_absent_from_native_index",
        "no_provider_configuration", "closed_presentation_denies_read_and_create",
        "native_source_permission_change_denied", "native_active_space_change_denied",
        "native_account_logout_denied", "original_commit_metadata_survives_logout",
        "background_presentation_had_live_read_access", "native_background_foreground_observed",
        "backgrounded_presentation_denies_read_and_create", "pending_read_consent_dismissed_on_document_exit",
        "departed_document_presentation_denies_read_and_create", "fresh_presentation_requires_new_native_consent",
        "fresh_presentation_reads_original_document_only", "native_return_mounted_original_document"
    ]

    private static let sceneEventKeys: Set<String> = [
        "sceneWillDeactivate", "sceneDidEnterBackground", "sceneWillEnterForeground", "sceneDidActivate",
        "applicationWillResignActive", "applicationDidBecomeActive"
    ]

    private struct Fixture: Decodable {
        let fixtureID: UUID
        let sourceSHA: String
        let runID: String
        let runAttempt: String
        let accountID: String
        let spaceID: String
        let alternateSpaceID: String
        let sourceObjectID: String
        let createdTitle: String
        let cancelledTitle: String
    }

    private struct NavigationContext: Codable, Equatable {
        let app: String
        let account: String
        let workspace: String
        let space: String
        let sceneID: UUID
        let generation: UUID
        let objectReference: String?
        let selectionReferences: [String]
        let sourceRevision: String?
    }

    private struct NativeReturnReceipt: Codable, Equatable {
        let requestID: UUID
        let queuedRequestID: UUID
        let sessionID: UUID
        let context: NavigationContext
        let objectReference: String
        let blockReference: String?
        let presentationAcknowledged: Bool
    }

    private struct Receipt: Codable {
        let fixtureID: UUID
        let sourceSHA: String
        let runID: String
        let runAttempt: String
        let sessionID: UUID
        let navigationContext: NavigationContext
        let processID: Int32
        let startedAt: Date
        let finishedAt: Date?
        let phase: String
        let checks: [String: Bool]
        let createdObjectID: String?
        let failure: String?
        let providerConfigured: Bool
        let nativeReturn: NativeReturnReceipt?
        let backgroundSessionID: UUID?
        let staleConsentSessionID: UUID?
        let freshSessionID: UUID?
        let sceneEventCounts: [String: Int]
        let backgroundCycleSceneDelta: [String: Int]
        let documentExitSceneDelta: [String: Int]
        let documentExitAttribution: String?
        let invalidationCauses: [String: String]
        let logoutRootState: String?
    }
}
