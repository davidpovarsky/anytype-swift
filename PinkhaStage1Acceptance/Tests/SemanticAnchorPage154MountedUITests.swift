import Foundation
import CryptoKit
import XCTest

/// Real UIKit selection/menu/UIAlert journey against a fresh native account.
/// No test code calls service.prepare/apply or sets a selection in the app process.
@MainActor
final class SemanticAnchorPage154MountedUITests: XCTestCase {
    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private var fixture: Fixture!
    private var environment: [String: String] = [:]

    override func setUpWithError() throws {
        continueAfterFailure = false
        let env = ProcessInfo.processInfo.environment
        XCTAssertEqual(env["PINKHA_SEMANTIC_MOUNTED_TESTING"], "1")
        XCTAssertEqual(env["PINKHA_SIMULATOR_UI_DISPOSABLE"], "1")
        guard env["PINKHA_SEMANTIC_MOUNTED_TESTING"] == "1",
              env["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1" else {
            throw Failure.invalidFixture
        }
        let raw = try XCTUnwrap(env["PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON"])
        XCTAssertLessThanOrEqual(raw.utf8.count, 65_536)
        fixture = try JSONDecoder().decode(Fixture.self, from: Data(raw.utf8))
        XCTAssertEqual(fixture.text, "Anchor")
        XCTAssertEqual(fixture.excludedText, "Unselected " + fixture.nonce)
        XCTAssertNotEqual(fixture.blockID, fixture.excludedBlockID)
        environment = ["PINKHA_SEMANTIC_MOUNTED_UI": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1",
            "PINKHA_UI27_ROUTE_OBSERVATION": "1"]
        for (key, value) in [
            ("SOURCE_SHA", fixture.sourceSHA), ("RUN_ID", fixture.runID),
            ("RUN_ATTEMPT", fixture.runAttempt), ("NONCE", fixture.nonce)
        ] {
            XCTAssertEqual(value, env["PINKHA_SEMANTIC_MOUNTED_" + key])
            environment["PINKHA_SEMANTIC_MOUNTED_" + key] = value
        }
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        XCUIDevice.shared.orientation = .portrait
    }

    func testActualTextSelectionCancelThenCreateAndColdReopen() throws {
        try launchAndOpen(phase: "capture")
        try waitForPhase("READY")
        let initial = try currentReceipt()
        try verifyOwner(initial)
        XCTAssertEqual(initial.preparations, 0)
        XCTAssertEqual(initial.applyAttempts, 0)
        let originalPID = initial.processID
        let originalGeneration = try XCTUnwrap(initial.generation)
        XCTAssertNotEqual(originalPID, fixture.preparationProcessID)

        try selectRealWordAndChooseAnchor()
        try waitForPhase("CANCEL_CONFIRMATION_VISIBLE")
        let first = try currentReceipt()
        XCTAssertEqual(first.preparations, 1)
        XCTAssertEqual(first.applyAttempts, 0)
        try requireSelection(first)
        let confirmation = app.alerts.firstMatch
        try requireHittable(confirmation)
        XCTAssertTrue(confirmation.staticTexts["Create an anchor for this text?"].exists)
        attach("semantic-anchor-actual-selection-and-cancel-confirmation")
        try tap(confirmation.buttons["Cancel"])
        try waitForPhase("CANCELLED_UNCHANGED")
        let cancelled = try currentReceipt()
        try verifyOwner(cancelled)
        XCTAssertEqual(cancelled.cancellations, 1)
        XCTAssertEqual(cancelled.applyAttempts, 0)
        XCTAssertEqual(cancelled.documentPublications, 0)
        let before = try XCTUnwrap(Data(base64Encoded: fixture.beforeBlockBase64))
        XCTAssertEqual(cancelled.cancelNativeBlockSHA256, digest(before))

        try selectRealWordAndChooseAnchor()
        try waitForPhase("CREATE_CONFIRMATION_VISIBLE")
        let second = try currentReceipt()
        XCTAssertEqual(second.preparations, 2)
        XCTAssertEqual(second.applyAttempts, 0)
        try requireSelection(second)
        try requireHittable(confirmation)
        attach("semantic-anchor-actual-create-confirmation")
        try tap(confirmation.buttons["Create text anchor"])
        try waitForPhase("PASS_CAPTURE_MOUNTED")
        let captured = try currentReceipt()
        try verifyOwner(captured)
        XCTAssertEqual(captured.processID, originalPID)
        XCTAssertEqual(captured.generation, originalGeneration)
        XCTAssertEqual(captured.preparations, 2)
        XCTAssertEqual(captured.cancellations, 1)
        XCTAssertEqual(captured.applyAttempts, 1)
        XCTAssertEqual(captured.documentPublications, 1)
        XCTAssertEqual(captured.publicationGeneration, originalGeneration)
        XCTAssertEqual(Set(captured.checks.keys), [
            "actualEditorAndInputMounted", "actualUserSelection", "cancelNativeUnchanged", "explicitApplyOnce",
            "ordinaryDocumentPublication", "renderedBeforeIndependentReadback", "nativeReceiptVerified",
            "nonMarkAndExcludedBlockUnchanged", "middlewareLoggingDisabled"
        ])
        XCTAssertTrue(captured.checks.values.allSatisfy { $0 })
        let native = try XCTUnwrap(captured.native)
        XCTAssertNotEqual(native.marker, try XCTUnwrap(captured.cancelledMarker))
        XCTAssertFalse(native.changeID.isEmpty)
        for hash in [native.nativeChangeSHA256, native.beforeTextMarksSHA256, native.afterTextMarksSHA256] {
            XCTAssertNotNil(hash.range(of: "^[0-9a-f]{64}$", options: .regularExpression))
        }
        try requireRendered(captured, marker: native.marker)
        try tap(app.alerts.firstMatch.buttons["Done"])
        try requireHittable(sourceText)
        XCTAssertEqual(sourceText.value as? String, fixture.text)
        XCTAssertTrue(app.textViews.matching(NSPredicate(format: "value == %@", fixture.excludedText)).firstMatch.exists)
        attachReceipt("semantic-anchor-mounted-capture-receipt", captured)
        attach("semantic-anchor-created-in-actual-editor")

        // New app process, same persisted account/page. No new Create action.
        app.terminate()
        XCTAssertTrue(app.wait(for: .notRunning, timeout: 20))
        try launchAndOpen(phase: "reopen")
        try waitForPhase("PASS_COLD_REOPEN_MOUNTED")
        let reopened = try currentReceipt()
        try verifyOwner(reopened)
        XCTAssertNotEqual(reopened.processID, originalPID)
        XCTAssertNotEqual(reopened.processID, fixture.preparationProcessID)
        XCTAssertEqual(reopened.captureProcessID, originalPID)
        XCTAssertNotEqual(reopened.generation, originalGeneration)
        XCTAssertEqual(reopened.native, native)
        XCTAssertEqual(reopened.afterBlockBase64, captured.afterBlockBase64)
        XCTAssertEqual(reopened.documentMarksBase64, captured.documentMarksBase64)
        XCTAssertEqual(reopened.preparations, 0)
        XCTAssertEqual(reopened.applyAttempts, 0)
        XCTAssertEqual(reopened.documentPublications, 0)
        XCTAssertNotNil(try XCTUnwrap(reopened.captureReceiptSHA256).range(of: "^[0-9a-f]{64}$", options: .regularExpression))
        XCTAssertEqual(Set(reopened.checks.keys), ["actualEditorAndInputMounted", "distinctColdProcessAndGeneration",
            "persistedNativeBlockIdentical", "renderedBeforeIndependentReadback", "excludedBlockUnchanged",
            "noNewApply", "middlewareLoggingDisabled"])
        XCTAssertTrue(reopened.checks.values.allSatisfy { $0 })
        try requireRendered(reopened, marker: native.marker)
        try requireHittable(sourceText)
        attachReceipt("semantic-anchor-mounted-cold-reopen-receipt", reopened)
        attach("semantic-anchor-persisted-in-cold-editor")
    }

    private var sourceText: XCUIElement {
        app.textViews.matching(NSPredicate(format: "value == %@", fixture.text)).firstMatch
    }
    private var status: XCUIElement { app.staticTexts["pinkha.semanticAnchor.mounted-status"].firstMatch }

    private func launchAndOpen(phase: String) throws {
        if app.state != .notRunning { app.terminate() }
        app.launchEnvironment = environment.merging(["PINKHA_SEMANTIC_MOUNTED_PHASE": phase]) { _, next in next }
        app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 30))
        let home = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ OR label == %@ OR identifier == %@ OR label == %@",
            "SpaceHub", "SpaceHub", "NewSpaceButton", "NewSpaceButton")).firstMatch
        try admitNativeStartup(home: home, phase: phase)
        var route = URLComponents()
        route.scheme = "anytype"; route.host = "object"
        route.queryItems = [URLQueryItem(name: "objectId", value: fixture.objectID),
                            URLQueryItem(name: "spaceId", value: fixture.spaceID)]
        XCUIDevice.shared.system.open(try XCTUnwrap(route.url))
        try requireHittable(sourceText, timeout: 45)
    }


    // One original 60-second startup admission budget. Synchronous XCTest
    // queries may return later; every successful admission is checked again.
    private func admitNativeStartup(home: XCUIElement, phase: String) throws {
        let started = ProcessInfo.processInfo.systemUptime
        let deadline = started + 60
        var trace: [String: Any] = [
            "protocol": "pinkha-page154-native-startup-warning-v1",
            "phase": phase, "sourceSHA": fixture.sourceSHA, "runID": fixture.runID, "runAttempt": fixture.runAttempt,
            "nonce": fixture.nonce, "budgetSeconds": 60, "continueTaps": 0,
            "status": "STARTED"
        ]
        func remaining() throws -> TimeInterval {
            let value = deadline - ProcessInfo.processInfo.systemUptime
            guard value > 0 else { throw StartupFailure.admission("startup-deadline") }
            return value
        }
        func require(_ condition: Bool, _ name: String) throws {
            guard condition else { throw StartupFailure.admission(name) }
            _ = try remaining()
        }
        func attachTrace() {
            trace["elapsedSeconds"] = ProcessInfo.processInfo.systemUptime - started
            if let data = try? JSONSerialization.data(withJSONObject: trace, options: [.sortedKeys]) {
                let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
                attachment.name = "semantic-anchor-native-startup-" + phase
                attachment.lifetime = .keepAlways
                add(attachment)
            }
        }
        defer { attachTrace() }
        do {
            try require(phase == "capture" || phase == "reopen", "unexpected-startup-phase")
            let alerts = app.alerts.matching(NSPredicate(format: "label == %@", "Warning"))
            let warning = alerts.firstMatch
            if phase == "capture" {
                try require(warning.waitForExistence(timeout: remaining()), "native-warning-missing")
                try require(alerts.count == 1 && app.alerts.count == 1, "native-warning-not-unique")
                let text = "You launch app with a unstable middleware. Don't use your production vault. Your vault may be broken."
                let messages = warning.staticTexts.matching(NSPredicate(format: "label == %@", text))
                let proceed = warning.buttons.matching(NSPredicate(format: "label == %@", "Continue with current vault"))
                let logout = warning.buttons.matching(NSPredicate(format: "label == %@", "Logout from current vault"))
                try require(messages.count == 1 && messages.firstMatch.exists, "native-warning-message-differs")
                try require(warning.buttons.count == 2 && proceed.count == 1 && logout.count == 1,
                            "native-warning-actions-differ")
                let button = proceed.firstMatch
                try require(button.exists && button.isEnabled && button.isHittable, "native-continue-not-hittable")
                trace["exactWarningObserved"] = true
                let hierarchy = XCTAttachment(string: app.debugDescription)
                hierarchy.name = "semantic-anchor-native-startup-warning-ax"
                hierarchy.lifetime = .keepAlways
                add(hierarchy)
                attach("semantic-anchor-native-startup-warning")
                _ = try remaining()
                button.tap()
                trace["continueTaps"] = 1
                _ = try remaining()
                try require(warning.waitForNonExistence(timeout: remaining()), "native-warning-not-dismissed")
            }
            try require(home.waitForExistence(timeout: remaining()), "home-not-ready")
            try require(!warning.exists, "native-warning-remained-or-returned")
            trace["admittedElapsedSeconds"] = 60 - (try remaining())
            trace["status"] = "HOME_READY"
        } catch {
            trace["status"] = "FAIL"
            trace["firstError"] = String(describing: error)
            throw error
        }
    }

    private enum StartupFailure: Error { case admission(String) }

    private func selectRealWordAndChooseAnchor() throws {
        try requireHittable(sourceText)
        // Native touch actions only. The observer independently requires the
        // actual selected UTF-16 range to cover exactly this single word.
        sourceText.tap()
        sourceText.doubleTap()
        let create = app.buttons["Create text anchor"].firstMatch
        try requireHittable(create)
        create.tap()
    }

    private func tap(_ element: XCUIElement) throws {
        try requireHittable(element); element.tap()
    }
    private func requireHittable(_ element: XCUIElement, timeout: TimeInterval = 20) throws {
        let expected = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true AND hittable == true"), object: element)
        XCTAssertEqual(XCTWaiter.wait(for: [expected], timeout: timeout), .completed)
    }
    private func waitForPhase(_ value: String) throws {
        let expected = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true AND label IN %@", [value, "MOUNTED_FAIL"]), object: status)
        XCTAssertEqual(XCTWaiter.wait(for: [expected], timeout: 45), .completed)
        XCTAssertEqual(status.label, value)
    }
    private func currentReceipt() throws -> Receipt {
        let raw = try XCTUnwrap(status.value as? String)
        XCTAssertLessThanOrEqual(raw.utf8.count, 65_536)
        return try JSONDecoder().decode(Receipt.self, from: Data(raw.utf8))
    }
    private func verifyOwner(_ value: Receipt) throws {
        XCTAssertEqual(value.protocolName, "pinkha-semantic-page154-mounted-v1")
        XCTAssertEqual(value.sourceSHA, fixture.sourceSHA); XCTAssertEqual(value.runID, fixture.runID)
        XCTAssertEqual(value.runAttempt, fixture.runAttempt); XCTAssertEqual(value.nonce, fixture.nonce)
        XCTAssertEqual(value.accountID, fixture.accountID); XCTAssertEqual(value.spaceID, fixture.spaceID)
        XCTAssertEqual(value.objectID, fixture.objectID); XCTAssertEqual(value.blockID, fixture.blockID)
        XCTAssertEqual(value.excludedBlockID, fixture.excludedBlockID)
        XCTAssertEqual(value.preparationProcessID, fixture.preparationProcessID)
        XCTAssertGreaterThan(value.processID, 0); XCTAssertNil(value.failure)
    }
    private func requireSelection(_ value: Receipt) throws {
        let selected = try XCTUnwrap(value.selection)
        XCTAssertEqual(selected.blockID, fixture.blockID)
        XCTAssertEqual(selected.location, 0); XCTAssertEqual(selected.length, fixture.text.utf16.count)
        XCTAssertEqual(selected.visibleTextSHA256, digest(Data(fixture.text.utf8)))
    }
    private func requireRendered(_ value: Receipt, marker: String) throws {
        let links = try XCTUnwrap(value.renderedLinks)
        XCTAssertEqual(links, [Link(marker: marker, location: 0, length: fixture.text.utf16.count)])
    }
    private func digest(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
    private func attach(_ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    private func attachReceipt(_ name: String, _ receipt: Receipt) {
        do {
            let attachment = XCTAttachment(data: try JSONEncoder().encode(receipt), uniformTypeIdentifier: "public.json")
            attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
        } catch { XCTFail("Could not attach the observed receipt") }
    }
    private enum Failure: Error { case invalidFixture }
    private struct Fixture: Decodable {
        let sourceSHA: String; let runID: String; let runAttempt: String; let nonce: String
        let preparationProcessID: Int
        let accountID: String; let spaceID: String; let objectID: String; let blockID: String; let excludedBlockID: String
        let text: String; let excludedText: String; let beforeBlockBase64: String
    }
    private struct Selection: Codable {
        let blockID: String; let location: Int; let length: Int; let visibleTextSHA256: String
    }
    private struct Link: Codable, Equatable { let marker: String; let location: Int; let length: Int }
    private struct Native: Codable, Equatable {
        let anchorID: String; let marker: String; let changeID: String; let nativeChangeSHA256: String
        let beforeTextMarksSHA256: String; let afterTextMarksSHA256: String
    }
    private struct Receipt: Codable {
        let protocolName: String
        let phase: String; let sourceSHA: String; let runID: String; let runAttempt: String; let nonce: String
        let accountID: String; let spaceID: String; let objectID: String; let blockID: String; let excludedBlockID: String
        let processID: Int; let preparationProcessID: Int; let captureProcessID: Int?
        let generation: String?; let publicationGeneration: String?
        let preparations: Int; let cancellations: Int; let applyAttempts: Int; let documentPublications: Int
        let selection: Selection?; let cancelledMarker: String?; let cancelNativeBlockSHA256: String?
        let native: Native?; let afterBlockBase64: String?; let documentMarksBase64: String?
        let renderedLinks: [Link]?; let captureReceiptSHA256: String?
        let checks: [String: Bool]; let failure: String?
        enum CodingKeys: String, CodingKey {
            case protocolName = "protocol"
            case phase, sourceSHA, runID, runAttempt, nonce, accountID, spaceID, objectID, blockID, excludedBlockID
            case processID, preparationProcessID, captureProcessID, generation, publicationGeneration
            case preparations, cancellations, applyAttempts, documentPublications, selection, cancelledMarker
            case cancelNativeBlockSHA256, native, afterBlockBase64, documentMarksBase64, renderedLinks
            case captureReceiptSHA256, checks, failure
        }
    }
}
