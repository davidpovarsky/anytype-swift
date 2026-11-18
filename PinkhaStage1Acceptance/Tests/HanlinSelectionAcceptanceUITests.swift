import Foundation
import CryptoKit
import XCTest

/// Independent disposable account. Uses native long-press, the real selection
/// entry, real consent and Return; no text-selection or mount test backdoor.
@MainActor
final class HanlinSelectionAcceptanceUITests: XCTestCase {
    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private var fixture: Fixture!

    override func setUpWithError() throws {
        continueAfterFailure = false
        let environment = ProcessInfo.processInfo.environment
        XCTAssertEqual(environment["PINKHA_HANLIN_SELECTION_UI_TESTING"], "1")
        XCTAssertEqual(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"], "1")
        guard environment["PINKHA_HANLIN_SELECTION_UI_TESTING"] == "1",
              environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1" else {
            throw NSError(domain: "HanlinSelectionAcceptance", code: 1)
        }
        let json = try XCTUnwrap(environment["PINKHA_HANLIN_SELECTION_FIXTURE_JSON"])
        XCTAssertLessThanOrEqual(json.utf8.count, 16_384)
        fixture = try JSONDecoder().decode(Fixture.self, from: Data(json.utf8))
        let base = fixture.base
        XCTAssertEqual(base.sourceSHA, try XCTUnwrap(environment["PINKHA_HANLIN_SELECTION_SOURCE_SHA"]))
        XCTAssertEqual(base.runID, try XCTUnwrap(environment["PINKHA_HANLIN_SELECTION_RUN_ID"]))
        XCTAssertEqual(base.runAttempt, try XCTUnwrap(environment["PINKHA_HANLIN_SELECTION_RUN_ATTEMPT"]))
        XCTAssertFalse(base.accountID.isEmpty)
        XCTAssertNotEqual(base.sourceBlockID, fixture.excludedBlockID)
        XCTAssertEqual(base.sourceText, "Hanlin native body " + base.fixtureID.uuidString)
        XCTAssertEqual(fixture.excludedText, "Hanlin unselected body " + base.fixtureID.uuidString)
        app.launchEnvironment = [
            "PINKHA_HANLIN_SELECTION_UI": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1",
            "PINKHA_HANLIN_SELECTION_FIXTURE_ID": base.fixtureID.uuidString,
            "PINKHA_HANLIN_SELECTION_SOURCE_SHA": base.sourceSHA,
            "PINKHA_HANLIN_SELECTION_RUN_ID": base.runID,
            "PINKHA_HANLIN_SELECTION_RUN_ATTEMPT": base.runAttempt,
            "PINKHA_UI27_ROUTE_OBSERVATION": "1"
        ]
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        XCUIDevice.shared.orientation = .portrait
    }

    func testRealSelectedBlockReadAndReturn() throws {
        if app.state != .notRunning { app.terminate() }
        app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 30))
        let home = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ OR label == %@ OR identifier == %@ OR label == %@",
            "SpaceHub", "SpaceHub", "NewSpaceButton", "NewSpaceButton")).firstMatch
        XCTAssertTrue(home.waitForExistence(timeout: 45))
        var route = URLComponents()
        route.scheme = "anytype"; route.host = "object"
        route.queryItems = [URLQueryItem(name: "objectId", value: fixture.base.sourceObjectID),
                            URLQueryItem(name: "spaceId", value: fixture.base.spaceID)]
        XCUIDevice.shared.system.open(try XCTUnwrap(route.url))
        try requireOriginalEditor()
        let selectedText = app.textViews.matching(NSPredicate(format: "value == %@", fixture.base.sourceText)).firstMatch
        let otherText = app.textViews.matching(NSPredicate(format: "value == %@", fixture.excludedText)).firstMatch
        XCTAssertTrue(selectedText.waitForExistence(timeout: 20))
        XCTAssertTrue(otherText.waitForExistence(timeout: 20))
        XCTAssertTrue(selectedText.isHittable)
        // The production collection recognizer selects the block at this real
        // touch location when the long press ends. A word-only selection fails
        // the required selection toolbar and the driver's exact native context.
        selectedText.press(forDuration: 0.6)
        let entry = app.buttons["pinkha.hanlin.open.selection"].firstMatch
        try requireHittable(entry)
        attachScreenshot("hanlin-selected-block-native-selection")
        entry.tap()

        try waitForPhase("SELECTION_AWAIT_READ_CONSENT")
        let initial = try currentReceipt()
        try verifyContext(initial)
        XCTAssertEqual(initial.deniedReadAttempts, 1)
        XCTAssertEqual(initial.deniedReadInvocationIDs.count, 1)
        XCTAssertNil(initial.selectedRead)
        XCTAssertNil(initial.nativeReturn)
        let share = app.buttons.matching(NSPredicate(
            format: "identifier == %@ OR label == %@", "pinkha.hanlin.share-context", "Allow access to this document or selection")).firstMatch
        try requireHittable(share)
        share.tap()
        let alert = app.alerts["Allow document text access?"].firstMatch
        XCTAssertTrue(alert.waitForExistence(timeout: 15))
        let allow = alert.buttons["Allow for this presentation"]
        try requireHittable(allow)
        attachScreenshot("hanlin-selected-block-native-read-consent")
        allow.tap()
        try waitForPhase("SELECTION_READY_TO_RETURN")
        let read = try currentReceipt()
        try verifyContext(read)
        XCTAssertEqual(read.sessionID, initial.sessionID)
        XCTAssertEqual(read.processID, initial.processID)
        XCTAssertEqual(read.navigationContext, initial.navigationContext)
        XCTAssertNil(read.nativeReturn)
        try verifyRead(try XCTUnwrap(read.selectedRead), context: read.navigationContext)
        let returnButton = app.buttons.matching(NSPredicate(
            format: "identifier == %@ OR label == %@", "pinkha.hanlin.return-to-source", "Return to document")).firstMatch
        try requireHittable(returnButton)
        returnButton.tap()

        try waitForPhase("HANLIN_SELECTION_ACCEPTANCE_PASS")
        try requireOriginalEditor()
        try requireHittable(entry)
        XCTAssertTrue(selectedText.exists)
        XCTAssertGreaterThan(selectedText.frame.width, 0)
        XCTAssertGreaterThan(selectedText.frame.height, 0)
        XCTAssertTrue(selectedText.frame.intersects(app.frame))
        let final = try currentReceipt()
        try verifyContext(final)
        XCTAssertEqual(final.sessionID, initial.sessionID)
        XCTAssertEqual(final.processID, initial.processID)
        XCTAssertEqual(final.navigationContext, initial.navigationContext)
        XCTAssertEqual(final.selectedRead, read.selectedRead)
        XCTAssertEqual(final.deniedReadAttempts, 3)
        XCTAssertEqual(final.deniedReadInvocationIDs.count, 3)
        XCTAssertEqual(Set(final.deniedReadInvocationIDs).count, 3)
        XCTAssertEqual(final.deniedReadInvocationIDs.first, initial.deniedReadInvocationIDs.first)
        XCTAssertNil(final.failure)
        XCTAssertNotNil(final.finishedAt)
        let returned = try XCTUnwrap(final.nativeReturn)
        XCTAssertEqual(returned.requestID, returned.queuedRequestID)
        XCTAssertEqual(returned.sessionID, initial.sessionID)
        XCTAssertEqual(returned.context, initial.navigationContext)
        XCTAssertEqual(returned.objectReference, fixture.base.sourceObjectID)
        XCTAssertEqual(returned.blockReference, fixture.base.sourceBlockID)
        XCTAssertTrue(returned.presentationAcknowledged)
        let checks: Set<String> = [
            "middleware_logging_disabled", "native_single_block_selection_context",
            "read_denied_before_native_consent", "native_selected_text_read", "unselected_text_excluded",
            "read_receipt_contains_metadata_only", "native_selected_block_mounted_on_return",
            "closed_selection_host_denies_read", "no_provider_configuration"
        ]
        XCTAssertEqual(Set(final.checks.keys), checks)
        XCTAssertTrue(final.checks.values.allSatisfy { $0 })
        let attachment = XCTAttachment(data: try JSONEncoder().encode(final), uniformTypeIdentifier: "public.json")
        attachment.name = "hanlin-selected-block-source-bound-result"; attachment.lifetime = .keepAlways
        add(attachment)
        attachScreenshot("hanlin-selected-block-original-mount-and-closed-authority")
    }

    private func verifyContext(_ value: Receipt) throws {
        let base = fixture.base
        XCTAssertEqual(value.fixtureID, base.fixtureID)
        XCTAssertEqual(value.sourceSHA, base.sourceSHA)
        XCTAssertEqual(value.runID, base.runID)
        XCTAssertEqual(value.runAttempt, base.runAttempt)
        XCTAssertGreaterThan(value.processID, 0)
        XCTAssertFalse(value.providerConfigured)
        let context = value.navigationContext
        XCTAssertEqual(context.app, "anytype")
        XCTAssertEqual(context.account, base.accountID)
        XCTAssertEqual(context.workspace, base.spaceID)
        XCTAssertEqual(context.space, base.spaceID)
        XCTAssertEqual(context.objectReference, base.sourceObjectID)
        XCTAssertEqual(context.selectionReferences, [base.sourceBlockID])
        XCTAssertEqual(context.sourceRevision.count, 64)
        XCTAssertTrue(context.sourceRevision.allSatisfy(\.isHexDigit))
    }

    private func verifyRead(_ value: ReadReceipt, context: NavigationContext) throws {
        XCTAssertFalse(value.invocationID.isEmpty)
        XCTAssertEqual(value.objectReference, fixture.base.sourceObjectID)
        XCTAssertEqual(value.spaceReference, fixture.base.spaceID)
        XCTAssertEqual(value.sourceRevision, context.sourceRevision)
        XCTAssertEqual(value.title, fixture.base.sourceTitle)
        XCTAssertEqual(value.blockReferences, [fixture.base.sourceBlockID])
        XCTAssertFalse(value.blockReferences.contains(fixture.excludedBlockID))
        let expected = SHA256.hash(data: Data(fixture.base.sourceText.utf8)).map { String(format: "%02x", $0) }.joined()
        XCTAssertEqual(value.textSHA256, expected)
        XCTAssertEqual(value.coverage, "selectedTextBlocksOnly")
        XCTAssertEqual(value.effectState, "confirmedNoEffect")
        XCTAssertEqual(value.metadataContentsCount, 0)
    }

    private func requireOriginalEditor() throws {
        let id = "pinkha-ui27-editor:\(fixture.base.spaceID):\(fixture.base.sourceObjectID)"
        let editor = app.otherElements.matching(NSPredicate(format: "identifier == %@", id)).firstMatch
        try requireHittable(editor, timeout: 45)
    }

    private func requireHittable(_ element: XCUIElement, timeout: TimeInterval = 15) throws {
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true AND hittable == true"), object: element)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: timeout), .completed)
    }

    private var status: XCUIElement { app.staticTexts["pinkha.hanlin.selection-acceptance-status"].firstMatch }

    private func waitForPhase(_ phase: String) throws {
        let expected = NSPredicate(format: "exists == true AND label IN %@",
                                  [phase, "SELECTION_SETUP_FAIL", "HANLIN_SELECTION_ACCEPTANCE_FAIL"])
        XCTAssertEqual(XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: expected, object: status)], timeout: 45), .completed)
        XCTAssertEqual(status.label, phase)
    }

    private func currentReceipt() throws -> Receipt {
        let json = try XCTUnwrap(status.value as? String)
        return try JSONDecoder().decode(Receipt.self, from: Data(json.utf8))
    }

    private func attachScreenshot(_ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }

    private struct Fixture: Decodable {
        let base: BaseFixture
        let excludedBlockID: String
        let excludedText: String
    }
    private struct BaseFixture: Decodable {
        let fixtureID: UUID
        let sourceSHA: String
        let runID: String
        let runAttempt: String
        let accountID: String
        let spaceID: String
        let sourceObjectID: String
        let sourceTitle: String
        let sourceBlockID: String
        let sourceText: String
    }
    private struct NavigationContext: Codable, Equatable {
        let app: String
        let account: String
        let workspace: String
        let space: String
        let sceneID: UUID
        let generation: UUID
        let objectReference: String
        let selectionReferences: [String]
        let sourceRevision: String
    }
    private struct ReadReceipt: Codable, Equatable {
        let invocationID: String
        let objectReference: String
        let spaceReference: String
        let sourceRevision: String
        let title: String
        let blockReferences: [String]
        let textSHA256: String
        let coverage: String
        let effectState: String
        let metadataContentsCount: Int
    }
    private struct NativeReturnReceipt: Codable {
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
        let phase: String
        let checks: [String: Bool]
        let selectedRead: ReadReceipt?
        let nativeReturn: NativeReturnReceipt?
        let deniedReadAttempts: Int
        let deniedReadInvocationIDs: [String]
        let providerConfigured: Bool
        let failure: String?
        let finishedAt: Date?
    }
}
