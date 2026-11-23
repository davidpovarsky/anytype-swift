import Foundation
import XCTest

@MainActor
final class MiniAppsNativeAcceptanceUITests: XCTestCase {
    private var source: XCUIApplication!
    private let companion = XCUIApplication(bundleIdentifier: "com.itorah.hanlinminiapps")
    private var fixture: [String: String] = [:]

    override func setUpWithError() throws {
        continueAfterFailure = false
        let environment = ProcessInfo.processInfo.environment
        XCTAssertEqual(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"], "1")
        fixture = try JSONDecoder().decode([String: String].self,
            from: Data(try XCTUnwrap(environment["PINKHA_MINIAPPS_FIXTURE_JSON"]).utf8))
        XCTAssertEqual(fixture["sourceSHA"], environment["GITHUB_SHA"])
        source = XCUIApplication(bundleIdentifier: try XCTUnwrap(environment["PINKHA_MINIAPPS_SOURCE_BUNDLE"]))
        source.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        source.launchEnvironment["PINKHA_UI27_ROUTE_OBSERVATION"] = "1"
        XCUIDevice.shared.orientation = .portrait
    }

    func testNativeEditorPickerTextStudioReturnAndColdReopen() throws {
        executionTimeAllowance = 360
        companion.launch()
        XCTAssertTrue(companion.wait(for: .runningForeground, timeout: 30))
        XCTAssertTrue(companion.buttons["hanlin-apps-add"].firstMatch.waitForExistence(timeout: 30),
            "The producer must finish publishing the shared catalog before the source picker opens")
        XCTAssertTrue(companion.descendants(matching: .any)["hanlin-package-card-Text Studio"].firstMatch
            .waitForExistence(timeout: 15))
        source.launch()
        try openSource()
        try returnThroughTextStudio(text: XCTUnwrap(fixture["returnedText"]), terminateSource: false)
        try expectNativeText(keys: ["originalText", "returnedText"])
        screenshot("miniapps-original-editor-warm-return")
        try returnThroughTextStudio(text: XCTUnwrap(fixture["coldReturnedText"]), terminateSource: true)
        try expectNativeText()
        screenshot("miniapps-original-editor-cold-callback")
        source.terminate()
        XCTAssertTrue(source.wait(for: .notRunning, timeout: 15))
        source.launch()
        try openSource()
        try expectNativeText()
        screenshot("miniapps-cold-document-reopen")
        source.terminate()
    }

    func testDuplicateCallbackDoesNotInsertAgain() throws {
        let environment = ProcessInfo.processInfo.environment
        let requestIDs = [try XCTUnwrap(environment["PINKHA_MINIAPPS_REQUEST_ID"]),
                          try XCTUnwrap(environment["PINKHA_MINIAPPS_COLD_REQUEST_ID"])]
        source.launch()
        try openSource()
        for requestID in requestIDs {
            var callback = URLComponents()
            callback.scheme = try XCTUnwrap(environment["PINKHA_MINIAPPS_SOURCE_SCHEME"])
            callback.host = "miniapps"
            callback.path = "/return"
            callback.queryItems = [URLQueryItem(name: "request", value: requestID)]
            let url = try XCTUnwrap(callback.url)
            XCUIDevice.shared.system.open(url)
            XCUIDevice.shared.system.open(url)
        }
        try expectNativeText()
        screenshot("miniapps-duplicate-callback")
        source.terminate()
    }

    private func openSource() throws {
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 30))
        let ready = source.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ OR label == %@ OR identifier == %@ OR label == %@ OR identifier == %@",
            "SpaceHub", "SpaceHub", "NewSpaceButton", "NewSpaceButton", "pinkha.miniapps.open")).firstMatch
        XCTAssertTrue(ready.waitForExistence(timeout: 60))
        var route = URLComponents()
        route.scheme = "anytype"
        route.host = "object"
        route.queryItems = [URLQueryItem(name: "objectId", value: try XCTUnwrap(fixture["objectID"])),
                            URLQueryItem(name: "spaceId", value: try XCTUnwrap(fixture["spaceID"]))]
        XCUIDevice.shared.system.open(try XCTUnwrap(route.url))
        XCTAssertTrue(source.buttons["pinkha.miniapps.open"].firstMatch.waitForExistence(timeout: 30))
    }

    private func returnThroughTextStudio(text: String, terminateSource: Bool) throws {
        let grid = source.buttons["pinkha.miniapps.open"].firstMatch
        XCTAssertTrue(grid.waitForExistence(timeout: 30))
        XCTAssertTrue(grid.isHittable)
        grid.tap()
        let textStudio = source.buttons["miniapps-launch-nativeapp.textstudio"].firstMatch
        XCTAssertTrue(textStudio.waitForExistence(timeout: 30),
            "The producer must publish its catalog into the actual common App Group")
        screenshot(terminateSource ? "miniapps-cold-shared-picker" : "miniapps-warm-shared-picker")
        textStudio.tap()
        XCTAssertTrue(companion.wait(for: .runningForeground, timeout: 30))
        let input = companion.textViews["miniapps.textstudio.editor"].firstMatch
        XCTAssertTrue(input.waitForExistence(timeout: 30))
        XCTAssertEqual(input.value as? String ?? "", "", "Each toolbar insertion starts with independent empty input")
        if terminateSource {
            source.terminate()
            XCTAssertTrue(source.wait(for: .notRunning, timeout: 15))
            XCTAssertTrue(companion.wait(for: .runningForeground, timeout: 15))
        }
        input.tap()
        input.typeText(text)
        screenshot(terminateSource ? "miniapps-cold-external-textstudio" : "miniapps-warm-external-textstudio")
        let returnText = companion.buttons["miniapps.textstudio.return"]
        XCTAssertTrue(returnText.waitForExistence(timeout: 15))
        returnText.tap()
        // The cold case intentionally receives no manual source.launch/openSource aid.
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 45))
    }

    private func expectNativeText(keys: [String] = ["originalText", "returnedText", "coldReturnedText"]) throws {
        for key in keys {
            let text = try XCTUnwrap(fixture[key])
            let visible = source.descendants(matching: .any).matching(
                NSPredicate(format: "value == %@ OR label == %@", text, text)).firstMatch
            XCTAssertTrue(visible.waitForExistence(timeout: 45), "The original editor must render " + key)
        }
    }

    private func screenshot(_ name: String) {
        let image = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        image.name = name
        image.lifetime = .keepAlways
        add(image)
    }
}
