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
        // Full native identifiers may exceed XCTest's direct identifier-query
        // limit. Preserve every byte and use the exact predicate route.
        let editorID = "pinkha-ui27-editor:\(fixture.spaceID):\(fixture.sourceObjectID)"
        let editor = app.otherElements.matching(NSPredicate(format: "identifier == %@", editorID)).firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 45), "The exact prepared native editor must be mounted")
        XCTAssertTrue(editor.isHittable)
        let entry = app.buttons["pinkha.hanlin.open"].firstMatch
        XCTAssertTrue(entry.waitForExistence(timeout: 15))
        XCTAssertTrue(entry.isHittable, "The real Home-panel entry must remain reachable in this document")
        entry.tap()

        try waitForPhase("AWAIT_READ_CONSENT", timeout: 20)
        try chatButton(identifier: "pinkha.hanlin.share-context",
                       label: "Allow access to this document or selection").tap()
        let readAlert = app.alerts["Allow document text access?"].firstMatch
        XCTAssertTrue(readAlert.waitForExistence(timeout: 15))
        XCTAssertTrue(readAlert.buttons["Allow for this presentation"].isHittable)
        readAlert.buttons["Allow for this presentation"].tap()

        // Inspect the actual requested title AND original Space before each
        // decision. An old alert with the same title cannot satisfy the next step.
        let cancelled = try createAlert(for: fixture.cancelledTitle)
        attachScreenshot("hanlin-native-create-cancel-prompt")
        cancelled.buttons["Cancel"].tap()
        let confirmed = try createAlert(for: fixture.createdTitle)
        attachScreenshot("hanlin-native-create-confirm-prompt")
        confirmed.buttons["Create page"].tap()

        try waitForPhase("READY_TO_CLOSE", timeout: 45)
        let beforeClose = try currentReceipt()
        XCTAssertEqual(beforeClose.checks["real_native_context_text_read"], true)
        XCTAssertEqual(beforeClose.checks["native_confirm_creates_exact_page"], true)
        XCTAssertFalse(try XCTUnwrap(beforeClose.createdObjectID).isEmpty)
        XCTAssertFalse(beforeClose.providerConfigured)
        attachScreenshot("hanlin-native-read-and-create-complete")
        try chatButton(identifier: "pinkha.hanlin.close", label: "Close").tap()

        try waitForPhase("NATIVE_ACCEPTANCE_PASS", timeout: 90)
        let final = try currentReceipt()
        XCTAssertEqual(final.fixtureID, fixture.fixtureID)
        XCTAssertEqual(final.sourceSHA, fixture.sourceSHA)
        XCTAssertEqual(final.runID, fixture.runID)
        XCTAssertEqual(final.runAttempt, fixture.runAttempt)
        XCTAssertEqual(final.sessionID, beforeClose.sessionID)
        XCTAssertEqual(final.processID, beforeClose.processID)
        XCTAssertGreaterThan(final.processID, 0)
        XCTAssertEqual(final.createdObjectID, beforeClose.createdObjectID)
        XCTAssertNil(final.failure)
        XCTAssertFalse(final.providerConfigured)
        XCTAssertNotNil(final.finishedAt)
        XCTAssertEqual(Set(final.checks.keys), Self.requiredChecks)
        XCTAssertTrue(final.checks.values.allSatisfy { $0 })
        let attachment = XCTAttachment(data: try JSONEncoder().encode(final),
                                       uniformTypeIdentifier: "public.json")
        attachment.name = "hanlin-native-source-bound-result"
        attachment.lifetime = .keepAlways
        add(attachment)
        attachScreenshot("hanlin-native-authority-revocations-complete")
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
        XCTAssertTrue(button.waitForExistence(timeout: 10))
        XCTAssertTrue(button.isHittable)
        return button
    }

    private func createAlert(for title: String) throws -> XCUIElement {
        let alert = app.alerts["Create a new page?"].firstMatch
        XCTAssertTrue(alert.waitForExistence(timeout: 15))
        let exactOperation = alert.staticTexts.matching(NSPredicate(
            format: "label CONTAINS %@ AND label CONTAINS %@", title, fixture.spaceID
        )).firstMatch
        XCTAssertTrue(exactOperation.waitForExistence(timeout: 15), "The actual consent must name this title and original Space")
        XCTAssertTrue(alert.buttons["Cancel"].isHittable)
        XCTAssertTrue(alert.buttons["Create page"].isHittable)
        return alert
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
        "native_account_logout_denied", "original_commit_metadata_survives_logout"
    ]

    private struct Fixture: Decodable {
        let fixtureID: UUID
        let sourceSHA: String
        let runID: String
        let runAttempt: String
        let spaceID: String
        let alternateSpaceID: String
        let sourceObjectID: String
        let createdTitle: String
        let cancelledTitle: String
    }

    private struct Receipt: Codable {
        let fixtureID: UUID
        let sourceSHA: String
        let runID: String
        let runAttempt: String
        let sessionID: UUID
        let processID: Int32
        let startedAt: Date
        let finishedAt: Date?
        let phase: String
        let checks: [String: Bool]
        let createdObjectID: String?
        let failure: String?
        let providerConfigured: Bool
    }
}
