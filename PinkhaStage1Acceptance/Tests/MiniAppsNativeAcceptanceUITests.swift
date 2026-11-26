import Foundation
import CryptoKit
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
        XCTAssertEqual(fixture["sourceSHA"], environment["PINKHA_MINIAPPS_SOURCE_SHA"])
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
        // Deliver warm replay through the OS without XCTest launch semantics.
        let originalProcess = try sourceProcessIdentity()
        for requestID in requestIDs {
            var callback = URLComponents()
            callback.scheme = try XCTUnwrap(environment["PINKHA_MINIAPPS_SOURCE_SCHEME"])
            callback.host = "miniapps"
            callback.path = "/return"
            callback.queryItems = [URLQueryItem(name: "request", value: requestID)]
            let url = try XCTUnwrap(callback.url)
            for _ in 0..<2 {
                XCUIDevice.shared.system.open(url)
                XCTAssertTrue(source.wait(for: .runningForeground, timeout: 30))
                XCTAssertEqual(try sourceProcessIdentity(), originalProcess,
                    "Warm duplicate callbacks must not relaunch the source process")
            }
        }
        try expectNativeText()
        screenshot("miniapps-duplicate-callback")
        source.terminate()
    }

    private func openSource() throws {
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 30))
        // A real qualified custom middleware may present the original safety
        // warning before Space Hub. Continue only through its ordinary button;
        // all editor, callback, identity and cold-persistence assertions below
        // remain unchanged.
        let warning = source.alerts["Warning"].firstMatch
        if warning.waitForExistence(timeout: 3) {
            let proceed = warning.buttons["Continue with current vault"]
            XCTAssertTrue(proceed.waitForExistence(timeout: 10))
            XCTAssertTrue(proceed.isEnabled && proceed.isHittable)
            screenshot("miniapps-original-middleware-warning")
            proceed.tap()
            expectation(for: NSPredicate(format: "exists == false"), evaluatedWith: warning)
            waitForExpectations(timeout: 20)
        }
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
        let warmProcess = terminateSource ? nil : try sourceProcessIdentity()
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
        if let warmProcess {
            XCTAssertEqual(try sourceProcessIdentity(), warmProcess,
                "Warm MiniApps completion must return to the existing source process")
        }
    }

    private func sourceProcessIdentity() throws -> String {
        let entry = source.buttons["pinkha.miniapps.open"].firstMatch
        XCTAssertTrue(entry.waitForExistence(timeout: 30))
        let value = try XCTUnwrap(entry.value as? String)
        XCTAssertTrue(value.hasPrefix("pid:"))
        XCTAssertNotEqual(value, "pid:0")
        return value
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

    // Additional real file journey; the original five objectives are unchanged.
    func testNativeFilesRoundTripColdReopenCancelAndReplay() async throws {
        executionTimeAllowance = 540
        let environment = ProcessInfo.processInfo.environment
        let shared = URL(fileURLWithPath: try XCTUnwrap(environment["PINKHA_MINIAPPS_SHARED_BRIDGE"]))
        let archive = URL(fileURLWithPath: try XCTUnwrap(environment["PINKHA_MINIAPPS_FILE_ARCHIVE"]))
        XCTAssertEqual(fwDigest(try Data(contentsOf: archive)),
            environment["PINKHA_MINIAPPS_FILE_ARCHIVE_SHA256"])
        companion.launch()
        try fwInstall()
        source.launch()
        try openSource()

        let warmPID = try sourceProcessIdentity()
        let first = try await fwLaunch(shared)
        XCTAssertTrue(first.request.inputs.filter { $0.kind == "file" }.isEmpty)
        let firstText = "NativeFile" + UUID().uuidString.replacingOccurrences(of: "-", with: "")
        let secondText = "קובץ בעברית\n" + UUID().uuidString + "\nOriginal native file bytes"
        let editor = try await fwEditor()
        XCTAssertEqual(editor.value as? String, first.request.source.documentText,
            "The genuine new file starts with the captured original document")
        try await fwReplace(editor, with: firstText)
        try fwPress("fileworkshop.return")
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 90))
        XCTAssertEqual(try sourceProcessIdentity(), warmPID)
        let firstCompleted = try await fwAcknowledged(first.request.id, shared)
        let firstResult = try XCTUnwrap(firstCompleted.result)
        XCTAssertEqual(firstResult.status, "success")
        XCTAssertEqual(firstResult.items.count, 1)
        let firstFile = try XCTUnwrap(firstResult.items.first)
        XCTAssertEqual(firstFile.name, "document.txt")
        XCTAssertEqual(try fwBytes(firstFile, shared), Data(firstText.utf8))
        screenshot("miniapps-native-file-first-return")

        // A cold source reopen must export the actual stored original file.
        source.terminate()
        XCTAssertTrue(source.wait(for: .notRunning, timeout: 20))
        source.launch()
        try openSource()
        let second = try await fwLaunch(shared)
        let secondInputs = second.request.inputs.filter { $0.kind == "file" }
        XCTAssertEqual(secondInputs.count, 1)
        XCTAssertEqual(try fwBytes(XCTUnwrap(secondInputs.first), shared), Data(firstText.utf8))
        _ = try fwNativeBlocks(second.request, count: 1)
        let secondEditor = try await fwEditor()
        try await fwWait { secondEditor.value as? String == firstText }
        try await fwReplace(secondEditor, with: secondText)
        source.terminate()
        XCTAssertTrue(source.wait(for: .notRunning, timeout: 20))
        try fwPress("fileworkshop.return")
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 90),
            "The actual callback must cold launch the original source")
        let secondCompleted = try await fwAcknowledged(second.request.id, shared)
        let secondResult = try XCTUnwrap(secondCompleted.result)
        XCTAssertEqual(secondResult.status, "success")
        XCTAssertEqual(secondResult.items.count, 1)
        let secondFile = try XCTUnwrap(secondResult.items.first)
        XCTAssertEqual(secondFile.name, firstFile.name)
        XCTAssertNotEqual(secondFile.attachmentID, firstFile.attachmentID)
        XCTAssertEqual(try fwBytes(secondFile, shared), Data(secondText.utf8))
        screenshot("miniapps-native-file-cold-return")

        let third = try await fwLaunch(shared)
        let nativeIDs = try await fwVerifyBothFiles(third.request, shared, firstText, secondText)
        try fwPress("fileworkshop.cancel")
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 90))
        let thirdCompleted = try await fwAcknowledged(third.request.id, shared)
        let cancelled = try XCTUnwrap(thirdCompleted.result)
        XCTAssertEqual(cancelled.status, "cancelled")
        XCTAssertTrue(cancelled.items.isEmpty)
        var callback = try XCTUnwrap(URLComponents(
            url: XCTUnwrap(second.request.callbacks.success), resolvingAgainstBaseURL: false))
        callback.queryItems = (callback.queryItems ?? []) + [
            URLQueryItem(name: "request", value: second.request.id.uuidString)]
        let replayPID = try sourceProcessIdentity()
        for _ in 0..<2 {
            XCUIDevice.shared.system.open(try XCTUnwrap(callback.url))
            XCTAssertTrue(source.wait(for: .runningForeground, timeout: 60))
            XCTAssertEqual(try sourceProcessIdentity(), replayPID)
        }
        // Query the real original document again. The same two native blocks and
        // bytes must survive both cancellation and duplicate callback delivery.
        let fourth = try await fwLaunch(shared)
        let afterReplay = try await fwVerifyBothFiles(fourth.request, shared, firstText, secondText)
        XCTAssertEqual(afterReplay, nativeIDs)
        try fwPress("fileworkshop.cancel")
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 90))
        let fourthCompleted = try await fwAcknowledged(fourth.request.id, shared)
        XCTAssertEqual(fourthCompleted.result?.status, "cancelled")
        try expectNativeText()
        let report: [String: Any] = [
            "status": "REAL_NATIVE_FILE_UI_PASS",
            "sourceSHA": try XCTUnwrap(fixture["sourceSHA"]), "runID": try XCTUnwrap(fixture["runID"]),
            "documentID": try XCTUnwrap(fixture["objectID"]),
            "requestIDs": [first, second, third, fourth].map { $0.request.id.uuidString.lowercased() },
            "inputFileCounts": [0, 1, 2, 2],
            "firstSHA256": fwDigest(Data(firstText.utf8)), "secondSHA256": fwDigest(Data(secondText.utf8)),
            "nativeBlockIDs": nativeIDs.sorted(), "replayedCallbacks": 2,
            "nativeFilesSeeded": 0, "coldSourceReturn": true
        ]
        let name = try XCTUnwrap(environment["PINKHA_MINIAPPS_FILE_REPORT_NAME"])
        XCTAssertEqual(URL(fileURLWithPath: name).lastPathComponent, name)
        try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
            .write(to: shared.appendingPathComponent(name), options: .withoutOverwriting)
        screenshot("miniapps-native-file-cancel-replay-preserved")
        source.terminate()
    }

    private struct FWContent: Decodable {
        let text: String?; let kind: String; let attachmentID: UUID?; let name: String?
    }
    private struct FWSource: Decodable {
        let appID: String; let documentID: String?; let documentText: String?; let metadata: [String: String]
    }
    private struct FWCallbacks: Decodable { let success: URL? }
    private struct FWRequest: Decodable {
        let id: UUID; let appID: String; let source: FWSource; let inputs: [FWContent]; let callbacks: FWCallbacks
    }
    private struct FWResult: Decodable { let status: String; let items: [FWContent] }
    private struct FWRecord: Decodable { let request: FWRequest; let result: FWResult?; let acknowledged: Bool }

    private func fwDigest(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    private func fwWait(timeout: Duration = .seconds(45),
                        _ predicate: @MainActor () throws -> Bool) async throws {
        let clock = ContinuousClock(), deadline = clock.now.advanced(by: timeout)
        while try !predicate() {
            guard clock.now < deadline else {
                XCTFail("The original native file condition did not become true")
                throw NSError(domain: "OriginalNativeFileAcceptance", code: 1)
            }
            try await Task.sleep(for: .milliseconds(200))
        }
    }

    private func fwTap(_ element: XCUIElement) {
        XCTAssertEqual(companion.state, .runningForeground)
        XCTAssertTrue(element.exists && element.isHittable)
        element.tap()
    }

    private func fwInstall() throws {
        let card = companion.buttons["hanlin-package-card-File Workshop"].firstMatch
        XCTAssertFalse(card.exists, "Actual installation starts from the owned fresh companion")
        let add = companion.buttons["hanlin-apps-add"].firstMatch
        XCTAssertTrue(add.waitForExistence(timeout: 40)); fwTap(add)
        let input = companion.buttons["hanlin-import-script-package"].firstMatch
        XCTAssertTrue(input.waitForExistence(timeout: 20)); fwTap(input)
        let list = companion.collectionViews["hanlin-package-import-list"].firstMatch
        XCTAssertTrue(list.waitForExistence(timeout: 20))
        let archive = companion.buttons["FileWorkshop"].firstMatch
        for _ in 0..<10 { if archive.exists && archive.isHittable { break }; list.swipeUp() }
        fwTap(archive)
        let install = companion.buttons["hanlin-package-install"].firstMatch
        XCTAssertTrue(install.waitForExistence(timeout: 30) && install.isEnabled); fwTap(install)
        XCTAssertTrue(install.waitForNonExistence(timeout: 60))
        for id in ["hanlin-package-import-done", "hanlin-apps-add-done"] {
            let button = companion.buttons[id].firstMatch
            XCTAssertTrue(button.waitForExistence(timeout: 20)); fwTap(button)
        }
        for _ in 0..<10 { if card.exists { break }; companion.swipeUp() }
        XCTAssertTrue(card.waitForExistence(timeout: 20))
        screenshot("miniapps-file-workshop-real-install")
    }

    private func fwRecords(_ shared: URL) throws -> [FWRecord] {
        let directory = shared.appendingPathComponent("requests", isDirectory: true)
        let bundle = try XCTUnwrap(ProcessInfo.processInfo.environment["PINKHA_MINIAPPS_SOURCE_BUNDLE"])
        return try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
            .filter { $0.pathExtension == "json" }
            .map { try JSONDecoder().decode(FWRecord.self, from: Data(contentsOf: $0)) }
            .filter { $0.request.source.appID == bundle }
    }

    private func fwLaunch(_ shared: URL) async throws -> FWRecord {
        let before = Set(try fwRecords(shared).map { $0.request.id })
        let action = source.buttons["pinkha.miniapps.open"].firstMatch
        XCTAssertTrue(action.waitForExistence(timeout: 30) && action.isHittable); action.tap()
        let launch = source.buttons["miniapps-launch-org.itorah.miniapps.fileworkshop"].firstMatch
        if !launch.waitForExistence(timeout: 3) {
            let more = source.buttons["miniapps-more"].firstMatch
            XCTAssertTrue(more.waitForExistence(timeout: 15) && more.isHittable); more.tap()
        }
        XCTAssertTrue(launch.waitForExistence(timeout: 30) && launch.isHittable); launch.tap()
        XCTAssertTrue(companion.wait(for: .runningForeground, timeout: 60))
        _ = try await fwEditor()
        let added = try fwRecords(shared).filter { !before.contains($0.request.id) }
        XCTAssertEqual(added.count, 1)
        let record = try XCTUnwrap(added.first)
        XCTAssertEqual(record.request.appID, "org.itorah.miniapps.fileworkshop")
        XCTAssertEqual(record.request.source.documentID, fixture["objectID"])
        XCTAssertFalse(record.acknowledged); XCTAssertNil(record.result)
        return record
    }

    private func fwEditor() async throws -> XCUIElement {
        let editors = companion.textViews.matching(identifier: "fileworkshop.editor")
        try await fwWait(timeout: .seconds(60)) {
            editors.allElementsBoundByIndex.filter { $0.isHittable }.count == 1
        }
        return try XCTUnwrap(editors.allElementsBoundByIndex.first { $0.isHittable })
    }

    private func fwMenu(_ title: String) -> XCUIElement {
        let item = companion.menuItems[title].firstMatch
        return item.exists ? item : companion.buttons[title].firstMatch
    }

    private func fwReplace(_ editor: XCUIElement, with text: String) async throws {
        fwTap(editor)
        if editor.value as? String != "" {
            editor.press(forDuration: 1)
            if !fwMenu("Select All").waitForExistence(timeout: 5) {
                let select = fwMenu("Select")
                XCTAssertTrue(select.waitForExistence(timeout: 10)); fwTap(select)
            }
            let all = fwMenu("Select All")
            XCTAssertTrue(all.waitForExistence(timeout: 10)); fwTap(all)
            let cut = fwMenu("Cut")
            XCTAssertTrue(cut.waitForExistence(timeout: 10)); fwTap(cut)
            try await fwWait { editor.value as? String == "" }
        }
        editor.typeText(text)
        XCTAssertEqual(editor.value as? String, text)
    }

    private func fwPress(_ name: String) throws {
        let action = companion.buttons[name].firstMatch
        for _ in 0..<8 { if action.exists && action.isHittable { break }; companion.swipeUp() }
        fwTap(action)
    }

    private func fwAcknowledged(_ id: UUID, _ shared: URL) async throws -> FWRecord {
        try await fwWait(timeout: .seconds(90)) {
            try self.fwRecords(shared).first { $0.request.id == id }?.acknowledged == true
        }
        return try XCTUnwrap(try fwRecords(shared).first { $0.request.id == id })
    }

    private func fwBytes(_ file: FWContent, _ shared: URL) throws -> Data {
        XCTAssertEqual(file.kind, "file"); XCTAssertNil(file.text)
        let id = try XCTUnwrap(file.attachmentID)
        return try Data(contentsOf: shared.appendingPathComponent("attachments")
            .appendingPathComponent(id.uuidString.lowercased()))
    }

    private func fwNativeBlocks(_ request: FWRequest, count: Int) throws -> Set<String> {
        let raw = try XCTUnwrap(request.source.metadata["anytype.files.v1"])
        let mapping = try JSONDecoder().decode([String: String].self, from: Data(raw.utf8))
        XCTAssertEqual(mapping.count, count)
        XCTAssertEqual(Set(mapping.values).count, count)
        XCTAssertEqual(Set(mapping.keys.compactMap(UUID.init(uuidString:))),
            Set(request.inputs.filter { $0.kind == "file" }.compactMap { $0.attachmentID }))
        return Set(mapping.values)
    }

    private func fwVerifyBothFiles(_ request: FWRequest, _ shared: URL,
                                   _ first: String, _ second: String) async throws -> Set<String> {
        let files = request.inputs.filter { $0.kind == "file" }
        XCTAssertEqual(files.count, 2)
        XCTAssertEqual(Set(try files.map { try fwBytes($0, shared) }),
                       Set([Data(first.utf8), Data(second.utf8)]))
        let blocks = try fwNativeBlocks(request, count: 2)
        for file in files {
            let id = try XCTUnwrap(file.attachmentID)
            let action = companion.buttons["fileworkshop.source-" + id.uuidString].firstMatch
            for _ in 0..<8 { if action.exists && action.isHittable { break }; companion.swipeDown() }
            fwTap(action)
            let editor = try await fwEditor()
            let expected = try XCTUnwrap(String(data: fwBytes(file, shared), encoding: .utf8))
            try await fwWait { editor.value as? String == expected }
            screenshot("miniapps-native-file-byte-readback-" + id.uuidString)
        }
        return blocks
    }

}
