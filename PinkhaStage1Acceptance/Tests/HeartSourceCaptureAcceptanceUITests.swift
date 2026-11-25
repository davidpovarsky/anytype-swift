import Foundation
import CryptoKit
import XCTest

/// Separate actual-app acceptance of the production source-capture lifecycle.
/// The controller admits E's sealed, disposable Heart account sequentially.
/// No test hook captures a source, creates a session or grants destination writes.
@MainActor
final class HeartSourceCaptureAcceptanceUITests: XCTestCase {
    private let app = XCUIApplication(bundleIdentifier: "io.anytype.app")
    private var fixture: Fixture!
    private var fixtureSHA256 = ""
    private var handoffSHA256 = ""
    private var deadline: TimeInterval = 0
    private var launch: [String: String] = [:]

    override func setUpWithError() throws {
        continueAfterFailure = false
        let env = ProcessInfo.processInfo.environment
        guard env["PINKHA_HEART_SOURCE_CAPTURE_TESTING"] == "1",
              env["PINKHA_SEMANTIC_MOUNTED_TESTING"] == "1",
              env["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1",
              let raw = env["PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON"],
              raw.utf8.count <= 65_536,
              let expiry = env["PINKHA_HEART_SOURCE_CAPTURE_DEADLINE_EPOCH"].flatMap(Double.init),
              expiry.isFinite, expiry > Date().timeIntervalSince1970,
              let handoff = env["PINKHA_HEART_SOURCE_CAPTURE_HANDOFF_SHA256"],
              Self.isDigest(handoff) else { throw Failure.admission("owned-fixture-handoff") }
        fixture = try JSONDecoder().decode(Fixture.self, from: Data(raw.utf8))
        fixtureSHA256 = SHA256.hash(data: Data(raw.utf8)).map { String(format: "%02x", $0) }.joined()
        guard fixtureSHA256 == env["PINKHA_HEART_SOURCE_CAPTURE_FIXTURE_SHA256"],
              fixture.sourceSHA.count == 40, fixture.preparationProcessID > 0,
              fixture.text == "Anchor", fixture.excludedText == "Unselected " + fixture.nonce,
              fixture.blockID != fixture.excludedBlockID,
              [fixture.accountID, fixture.spaceID, fixture.objectID, fixture.nonce].allSatisfy({
                  !$0.isEmpty && $0.utf8.count <= 4_096 && !$0.contains("\0")
              }) else { throw Failure.admission("fixture-binding") }
        deadline = expiry
        handoffSHA256 = handoff
        launch = [
            "PINKHA_SIMULATOR_UI_DISPOSABLE": "1",
            "PINKHA_HEART_SOURCE_CAPTURE_OBSERVER": "1",
            "PINKHA_SEMANTIC_MOUNTED_UI": "0",
            "PINKHA_UI27_ROUTE_OBSERVATION": "1"
        ]
        for (key, value) in [
            ("SOURCE_SHA", fixture.sourceSHA), ("RUN_ID", fixture.runID),
            ("RUN_ATTEMPT", fixture.runAttempt), ("NONCE", fixture.nonce)
        ] {
            guard env["PINKHA_SEMANTIC_MOUNTED_" + key] == value else {
                throw Failure.admission("fixture-" + key)
            }
            launch["PINKHA_SEMANTIC_MOUNTED_" + key] = value
        }
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        XCUIDevice.shared.orientation = .portrait
    }

    func testActualHeartSourceReviewCloseAndRecapture() throws {
        var receipt: [String: Any] = [
            "protocol": "pinkha-heart-source-capture-ui-v1",
            "status": "STARTED", "fixtureSHA256": fixtureSHA256,
            "handoffSHA256": handoffSHA256, "sourceSHA": fixture.sourceSHA,
            "runID": fixture.runID, "runAttempt": fixture.runAttempt,
            "nonce": fixture.nonce, "deadlineEpoch": deadline,
            "captures": [], "closeCompletions": 0,
            "scope": "actual-source-capture-review-close-recapture-only"
        ]
        defer { attachJSON(receipt, name: "heart-source-capture-ui") }
        do {
            if app.state != .notRunning { app.terminate() }
            app.launchEnvironment = launch
            app.launch()
            try require(app.wait(for: .runningForeground, timeout: remaining(30)), "app-foreground")
            let home = app.descendants(matching: .any).matching(NSPredicate(
                format: "identifier == %@ OR label == %@ OR identifier == %@ OR label == %@",
                "SpaceHub", "SpaceHub", "NewSpaceButton", "NewSpaceButton")).firstMatch
            try require(home.waitForExistence(timeout: remaining(60)), "original-home")
            // E has already accepted the exact middleware warning in its original
            // method. An unexpected warning is a new failure, never auto-dismissed.
            try require(!app.alerts["Warning"].exists && app.alerts.count == 0, "unexpected-startup-alert")
            try require(!element("pinkha.semanticAnchor.mounted-status").exists, "mounted-observer-active")
            try openOriginalFixtureSpace()
            try dismissOriginalChannelHomeOnboardingIfPresent()

            let first = try captureThroughMenu(ordinal: 1)
            receipt["captures"] = [first]
            try closeReview()
            receipt["closeCompletions"] = 1

            let second = try captureThroughMenu(ordinal: 2)
            receipt["captures"] = [first, second]
            try require(first["captureID"] as? String != second["captureID"] as? String, "capture-id-reused")
            try closeReview()
            receipt["closeCompletions"] = 2
            let selector = element("pinkha.engine.selector")
            try require(selector.isEnabled && selector.isHittable, "home-not-responsive-after-close")
            try require(selector.value as? String == "Heart", "source-engine-changed")
            screenshot("heart-source-capture-two-reviews-closed")
            receipt["status"] = "UI_PASS"
        } catch {
            receipt["status"] = "FAIL"
            receipt["error"] = String(describing: error)
            attachHierarchy("heart-source-capture-failure")
            screenshot("heart-source-capture-failure")
            throw error
        }
    }

    override func tearDownWithError() throws {
        // The independently verified controller retains the entire private account
        // and captured bundles. Never log out, delete an account or erase a device.
        if app.state != .notRunning { app.terminate() }
    }

    private func openOriginalFixtureSpace() throws {
        // The real source action is deliberately disabled at SpaceHub until a
        // workspace is open. Use the exact original preparation's visible space
        // button; the subsequent native review must still prove both IDs.
        let name = "Mounted anchor disposable Space"
        let matches = app.buttons.matching(NSPredicate(
            format: "label == %@ OR label ENDSWITH %@", name, ", " + name))
        try require(matches.firstMatch.waitForExistence(timeout: remaining(15)), "original-space-button")
        try require(matches.count == 1, "original-space-button-ambiguous")
        try tap(matches.firstMatch)
    }

    private func dismissOriginalChannelHomeOnboardingIfPresent() throws {
        // The original first-space flow presents this modal above the app's
        // engine header. Decline its optional home creation through its actual
        // UI; the subsequent source identity and capture assertions are unchanged.
        let prompt = app.staticTexts["Add a Channel Home?"]
        guard prompt.waitForExistence(timeout: try remaining(5)) else { return }
        let dismiss = app.buttons["Not now"]
        try require(dismiss.exists, "original-channel-home-decline-missing")
        try tap(dismiss)
        try require(prompt.waitForNonExistence(timeout: remaining(15)), "original-channel-home-remained")
    }

    private func captureThroughMenu(ordinal: Int) throws -> [String: Any] {
        let selector = element("pinkha.engine.selector")
        try require(selector.waitForExistence(timeout: remaining(15)), "engine-selector")
        try require(selector.value as? String == "Heart", "wrong-source-engine")
        try tap(selector)
        try tap(element("pinkha.engine.migration.review-source"))
        let status = element("heart-source-review-status")
        try require(status.waitForExistence(timeout: remaining(120)), "real-source-review-missing")
        try require(element("heart-source-review-pending-migration").exists, "missing-semantic-warning")
        try require(!element("heart-source-review-incomplete-census").exists, "incomplete-native-census")
        screenshot("heart-source-capture-\(ordinal)-review")

        try tap(try reveal("heart-source-review-identity"))
        let account = try identity("account")
        let space = try identity("space")
        let capture = try identity("capture-id")
        let fingerprint = try identity("fingerprint")
        try require(account.utf8.elementsEqual(fixture.accountID.utf8), "wrong-captured-account")
        try require(space.utf8.elementsEqual(fixture.spaceID.utf8), "wrong-captured-space")
        try require(!capture.isEmpty && capture.utf8.count <= 4_096, "invalid-capture-identity")
        try require(Self.isDigest(fingerprint), "invalid-native-fingerprint")
        let trees = try count("trees")
        let heads = try count("native-heads")
        var counts: [String: Int] = ["trees": trees, "nativeHeads": heads]
        for key in ["objects", "blocks", "types", "properties", "options", "files",
                    "definition-issues", "page-plans", "unmapped"] {
            counts[key] = try count(key)
        }
        let objects = try XCTUnwrap(counts["objects"])
        try require(objects > 0 && trees >= objects && heads > trees, "native-source-census")
        try require((counts["blocks"] ?? 0) > 0 && (counts["types"] ?? 0) > 0 &&
                    (counts["properties"] ?? 0) > 0, "empty-source-review")
        try require((counts["definition-issues"] ?? 0) > 0 && (counts["unmapped"] ?? 0) > 0,
                    "real-mapping-requirements-hidden")
        try require(!element("heart-source-review-incomplete-census").exists, "incomplete-native-census")
        screenshot("heart-source-capture-\(ordinal)-requirements")
        return [
            "ordinal": ordinal, "accountID": account, "spaceID": space,
            "captureID": capture, "manifestSHA256": fingerprint, "counts": counts,
            "destinationWrites": "not-requested-and-not-qualified-by-this-method"
        ]
    }

    private func closeReview() throws {
        let close = element("pinkha.engine.migration.close-review")
        try tap(close)
        try require(close.waitForNonExistence(timeout: remaining(30)), "native-close-not-completed")
        try require(!element("heart-source-review-status").exists, "review-remained")
        try require(app.alerts.count == 0, "close-failed")
    }

    private func count(_ suffix: String) throws -> Int {
        let row = try reveal("heart-source-review-" + suffix)
        guard let raw = row.value as? String, let value = Int(raw), value >= 0 else {
            throw Failure.admission("non-integer-count-" + suffix)
        }
        return value
    }

    private func identity(_ suffix: String) throws -> String {
        let row = try reveal("heart-source-review-" + suffix)
        let value = row.label
        try require(!value.isEmpty, "empty-identity-" + suffix)
        return value
    }

    private func reveal(_ id: String) throws -> XCUIElement {
        let candidate = element(id)
        // Only real list gestures; bounded forward traversal never fabricates AX
        // values or substitutes another source row. All requested rows are ordered.
        for _ in 0..<12 {
            _ = try remaining(1)
            if candidate.exists { return candidate }
            element("heart-source-review").swipeUp()
        }
        throw Failure.admission("missing-review-row-" + id)
    }

    private func element(_ id: String) -> XCUIElement {
        app.descendants(matching: .any).matching(identifier: id).firstMatch
    }

    private func tap(_ element: XCUIElement) throws {
        try require(element.waitForExistence(timeout: remaining(15)), "tap-missing")
        let ready = NSPredicate { _, _ in element.exists && element.isEnabled && element.isHittable }
        let expectation = XCTNSPredicateExpectation(predicate: ready, object: nil)
        try require(XCTWaiter.wait(for: [expectation], timeout: remaining(15)) == .completed, "tap-not-hittable")
        element.tap()
    }

    private func remaining(_ maximum: TimeInterval) throws -> TimeInterval {
        let value = deadline - Date().timeIntervalSince1970
        guard value > 0 else { throw Failure.admission("original-fixture-expired") }
        return min(maximum, value)
    }

    private func require(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
        guard try condition() else { throw Failure.admission(message) }
    }

    private nonisolated static func isDigest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }

    private func attachJSON(_ value: [String: Any], name: String) {
        guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]) else { return }
        let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }

    private func screenshot(_ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }

    private func attachHierarchy(_ name: String) {
        let attachment = XCTAttachment(string: app.debugDescription)
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }

    private enum Failure: Error { case admission(String) }
    private struct Fixture: Decodable {
        let sourceSHA: String; let runID: String; let runAttempt: String; let nonce: String
        let preparationProcessID: Int
        let accountID: String; let spaceID: String; let objectID: String
        let blockID: String; let excludedBlockID: String
        let text: String; let excludedText: String
    }
}
