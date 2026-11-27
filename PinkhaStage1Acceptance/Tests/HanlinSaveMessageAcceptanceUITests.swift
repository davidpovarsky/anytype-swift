import Foundation
import XCTest

/// The owner controller must first admit the built source/native artifacts,
/// requalify the retained account through the actual mounted editor, and open
/// the fresh fixture-bound Hanlin sheet in THIS running process. This test does
/// not launch/login, invent a native route, press a synthetic consent, or inject
/// a host/SDK/native result. It exercises the original shared UI controls.
@MainActor
final class HanlinSaveMessageAcceptanceUITests: XCTestCase {
    private var app: XCUIApplication!
    private var fixture: Fixture!

    override func setUpWithError() throws {
        continueAfterFailure = false
        let environment = ProcessInfo.processInfo.environment
        guard environment["PINKHA_HANLIN_SAVE_NATIVE_UI_TESTING"] == "1",
              environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1" else {
            throw NSError(domain: "HanlinSaveMessageNativeAcceptance", code: 1)
        }
        let bundleID = try XCTUnwrap(environment["PINKHA_HANLIN_SAVE_BUNDLE_ID"])
        guard !bundleID.isEmpty, bundleID.utf8.count <= 256,
              bundleID.utf8.allSatisfy({ (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || $0 == 45 || $0 == 46 }) else {
            throw NSError(domain: "HanlinSaveMessageNativeAcceptance", code: 2)
        }
        let json = try XCTUnwrap(environment["PINKHA_HANLIN_SAVE_FIXTURE_JSON"])
        XCTAssertLessThanOrEqual(json.utf8.count, 16_384)
        fixture = try JSONDecoder().decode(Fixture.self, from: Data(json.utf8))
        XCTAssertEqual(fixture.version, 1)
        XCTAssertEqual(fixture.sourceSHA, try XCTUnwrap(environment["PINKHA_HANLIN_SAVE_SOURCE_SHA"]))
        XCTAssertEqual(fixture.runID, try XCTUnwrap(environment["PINKHA_HANLIN_SAVE_RUN_ID"]))
        XCTAssertEqual(fixture.runAttempt, try XCTUnwrap(environment["PINKHA_HANLIN_SAVE_RUN_ATTEMPT"]))
        XCTAssertGreaterThan(fixture.processID, 0)
        XCTAssertTrue(["heart", "any"].contains(fixture.engine))
        XCTAssertGreaterThanOrEqual(Date().timeIntervalSince(fixture.createdAt), 0)
        XCTAssertLessThan(Date().timeIntervalSince(fixture.createdAt), 3_600)
        app = XCUIApplication(bundleIdentifier: bundleID)
        XCTAssertEqual(app.state, .runningForeground,
            "The controller must preserve the process whose mounted preparation produced this fixture")
    }

    func testOriginalSDKMessageSaveConsentAndNativeReadback() throws {
        try waitForPhase("AWAIT_SEND_CANCEL", timeout: 30)
        try requireFixture(try receipt())
        try pressSend()
        try waitForPhase("AWAIT_SAVE_CANCEL", timeout: 45)
        try pressOnlyEnabledSave()
        try nativeConsent(action: "cancel").tap()
        try waitForPhase("AWAIT_SEND_ALLOW", timeout: 45)
        let cancelled = try receipt()
        try requireFixture(cancelled)
        XCTAssertEqual(cancelled.attempts.count, 1)
        XCTAssertTrue(["notDispatched", "confirmedNoEffect"].contains(try XCTUnwrap(cancelled.attempts.first?.effect)))
        XCTAssertNil(cancelled.attempts.first?.journalIdentityKey)
        XCTAssertEqual(enabledSaves.count, 0, "The original cancelled message must not acquire another request ID")
        attachScreenshot("hanlin-save-native-cancelled")

        try pressSend()
        try waitForPhase("AWAIT_SAVE_ALLOW", timeout: 45)
        try pressOnlyEnabledSave()
        try nativeConsent(action: "allow").tap()
        try waitForPhase("CANCEL_RECEIPT_AND_NATIVE_SAVE_READBACK_PASS", timeout: 90)
        let result = try receipt()
        try requireFixture(result)
        XCTAssertEqual(result.attempts.count, 2)
        XCTAssertNil(result.failure)
        XCTAssertNotNil(result.finishedAt)
        let first = result.attempts[0], second = result.attempts[1]
        XCTAssertNotEqual(first.origin.messageID, second.origin.messageID)
        XCTAssertNotEqual(first.requestID, second.requestID)
        XCTAssertNotEqual(first.resultID, second.resultID)
        let runs = [first.origin.runID, second.origin.runID,
            try XCTUnwrap(first.executionRunID), try XCTUnwrap(second.executionRunID)]
        XCTAssertEqual(Set(runs).count, 4, "Both completed original responses and both original tool runs must be distinct")
        for attempt in result.attempts {
            let call = try XCTUnwrap(attempt.call)
            XCTAssertEqual(attempt.origin.session, result.session)
            XCTAssertEqual(call.session, result.session)
            XCTAssertEqual(call.runID, attempt.executionRunID)
            XCTAssertEqual(call.providerCallID, try XCTUnwrap(attempt.requestID).uuidString)
            XCTAssertEqual(call.step, 0)
            XCTAssertNotNil(attempt.resultID)
        }
        XCTAssertEqual(second.effect, "confirmedCommitted")
        XCTAssertEqual(try XCTUnwrap(second.journalIdentityKey).utf8.count, 64)
        XCTAssertEqual(try XCTUnwrap(second.journalProgressSHA256).utf8.count, 64)
        let body = try XCTUnwrap(result.nativeBodyReadback)
        XCTAssertNotEqual(Data(body.objectReference.utf8), Data(fixture.sourceObjectID.utf8))
        XCTAssertEqual(body.blockReferences.count, 4, "Heading, rich paragraph and two list items must survive the actual native read")
        XCTAssertEqual(Set(body.blockReferences.map { Data($0.utf8) }).count, body.blockReferences.count)
        XCTAssertEqual(body.manifestSHA256.utf8.count, 64)
        XCTAssertEqual(body.nativeReadbackSHA256.utf8.count, 64)
        if fixture.engine == "any" {
            let ack = try XCTUnwrap(result.atomicAcknowledgement)
            XCTAssertEqual(Set(ack.insertedReferences.map { Data($0.utf8) }), Set(body.blockReferences.map { Data($0.utf8) }))
            XCTAssertTrue(ack.updatedReferences.isEmpty && ack.deletedReferences.isEmpty)
            XCTAssertEqual(ack.unchangedBlocks, 0)
            XCTAssertEqual(ack.savedVersionSHA256, body.nativeVersionSHA256)
            XCTAssertEqual(ack.nativeReceiptSHA256.utf8.count, 64)
            XCTAssertEqual(try XCTUnwrap(body.nativeMarkdownSHA256).utf8.count, 64)
            XCTAssertGreaterThan(try XCTUnwrap(body.nativeMarkdownUTF8Bytes), 0)
        } else {
            XCTAssertNil(result.atomicAcknowledgement)
            XCTAssertNil(body.nativeVersionSHA256)
        }
        XCTAssertEqual(enabledSaves.count, 0)
        attachScreenshot("hanlin-save-original-sdk-and-native-readback")
        let attachment = XCTAttachment(data: try rawReceipt(), uniformTypeIdentifier: "public.json")
        attachment.name = "hanlin-save-source-bound-native-result"; attachment.lifetime = .keepAlways
        add(attachment)
        // Leave the account and native saved page intact for the owner. This
        // baseline does not claim cold reopen, Stop or replacement acceptance.
        app.buttons["pinkha.hanlin.close"].tap()
    }

    private var status: XCUIElement { app.staticTexts["pinkha.hanlin.save-acceptance-status"].firstMatch }
    private var enabledSaves: XCUIElementQuery {
        app.buttons.matching(identifier: "hanlin-action-save-personal").matching(NSPredicate(format: "enabled == true"))
    }
    private func pressSend() throws {
        let button = app.buttons.matching(NSPredicate(format: "label == %@", "Send")).firstMatch
        try ready(button, timeout: 15)
        button.tap()
    }
    private func pressOnlyEnabledSave() throws {
        let button = enabledSaves.firstMatch
        try ready(button, timeout: 15)
        XCTAssertEqual(enabledSaves.count, 1)
        button.tap()
    }
    private func nativeConsent(action: String) throws -> XCUIElement {
        let button = app.buttons["pinkha.hanlin.consent.save-message." + action].firstMatch
        try ready(button, timeout: 20)
        let explanation = app.staticTexts["pinkha.hanlin.consent.save-message.explanation"].firstMatch
        XCTAssertTrue(explanation.exists)
        let bytes = Data(explanation.label.utf8)
        XCTAssertNotNil(bytes.range(of: Data(fixture.spaceID.utf8)))
        XCTAssertNotNil(bytes.range(of: Data(fixture.markdown.utf8)), "The original native prompt must show the complete actual message")
        attachScreenshot("hanlin-save-native-" + action + "-prompt")
        return button
    }
    private func ready(_ control: XCUIElement, timeout: TimeInterval) throws {
        let expectation = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true AND enabled == true AND hittable == true"), object: control)
        XCTAssertEqual(XCTWaiter.wait(for: [expectation], timeout: timeout), .completed)
    }
    private func waitForPhase(_ phase: String, timeout: TimeInterval) throws {
        let expectation = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true AND label IN %@",
            [phase, "NATIVE_SAVE_ACCEPTANCE_FAIL", "NATIVE_SAVE_EVIDENCE_WRITE_FAILED"]), object: status)
        XCTAssertEqual(XCTWaiter.wait(for: [expectation], timeout: timeout), .completed)
        XCTAssertEqual(status.label, phase)
    }
    private func receipt() throws -> Receipt {
        try JSONDecoder().decode(Receipt.self, from: rawReceipt())
    }
    private func rawReceipt() throws -> Data {
        let json = try XCTUnwrap(status.value as? String)
        XCTAssertLessThanOrEqual(json.utf8.count, 196_608)
        return Data(json.utf8)
    }
    private func requireFixture(_ receipt: Receipt) throws {
        XCTAssertEqual(receipt.fixture.fixtureID, fixture.fixtureID)
        XCTAssertEqual(receipt.fixture.sourceSHA, fixture.sourceSHA)
        XCTAssertEqual(receipt.fixture.runID, fixture.runID)
        XCTAssertEqual(receipt.fixture.runAttempt, fixture.runAttempt)
        XCTAssertEqual(receipt.fixture.preparationReceiptSHA256, fixture.preparationReceiptSHA256)
        XCTAssertEqual(receipt.processID, fixture.processID)
        XCTAssertEqual(receipt.fixture.engine, fixture.engine)
        XCTAssertEqual(receipt.session.context.namespace.account, fixture.accountID)
        XCTAssertEqual(receipt.session.context.namespace.space, fixture.spaceID)
        XCTAssertEqual(receipt.session.context.namespace.workspace, fixture.spaceID)
        XCTAssertEqual(receipt.session.context.objectReference, fixture.sourceObjectID)
        XCTAssertTrue(receipt.session.context.localeIdentifier.hasPrefix("en"), "This baseline uses the original English Send label")
    }
    private func attachScreenshot(_ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }

    private struct Fixture: Codable {
        let version: Int; let fixtureID: UUID; let createdAt: Date; let sourceSHA: String
        let runID: String; let runAttempt: String; let engine: String; let processID: Int32
        let accountID: String; let spaceID: String; let sourceObjectID: String
        let preparationReceiptSHA256: String
        var markdown: String { "# Hanlin " + fixtureID.uuidString + "\n\nשלום **bold** and *italic* with `code`.\n\n- first\n- second" }
    }
    private struct Namespace: Codable, Equatable { let app: String; let account: String; let workspace: String; let space: String }
    private struct Context: Codable, Equatable {
        let namespace: Namespace; let sceneID: UUID; let generation: UUID; let objectReference: String?
        let sourceRevision: String?; let localeIdentifier: String
    }
    private struct Session: Codable, Equatable { let id: UUID; let context: Context }
    private struct Origin: Codable { let session: Session; let runID: UUID; let messageID: UUID }
    private struct Call: Codable { let session: Session; let runID: UUID; let step: Int; let providerCallID: String }
    private struct Attempt: Codable {
        let origin: Origin; let requestID: UUID?; let executionRunID: UUID?; let call: Call?
        let resultID: UUID?; let effect: String?; let journalIdentityKey: String?; let journalProgressSHA256: String?
    }
    private struct Body: Codable {
        let manifestSHA256: String; let objectReference: String; let blockReferences: [String]
        let nativeReadbackSHA256: String; let nativeVersionSHA256: String?
        let nativeMarkdownSHA256: String?; let nativeMarkdownUTF8Bytes: Int?
    }
    private struct Ack: Codable {
        let insertedReferences: [String]; let updatedReferences: [String]; let deletedReferences: [String]
        let unchangedBlocks: Int64; let savedVersionSHA256: String; let nativeReceiptSHA256: String
    }
    private struct Receipt: Codable {
        let fixture: Fixture; let session: Session; let processID: Int32; let attempts: [Attempt]
        let nativeBodyReadback: Body?; let atomicAcknowledgement: Ack?; let finishedAt: Date?; let failure: String?
    }
}
