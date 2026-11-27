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


    /// Real companion callbacks across both engines and two independent Any
    /// accounts. All accounts, Spaces and documents are made by ordinary UI.
    /// Only request/ACK records and our own report are read from the shared store.
    func testPendingReturnsRespectEngineAndAccountAcrossColdReopen() async throws {
        executionTimeAllowance = 1_500
        let environment = ProcessInfo.processInfo.environment
        let shared = URL(fileURLWithPath: try XCTUnwrap(environment["PINKHA_MINIAPPS_SHARED_BRIDGE"]))
        let suffix = UUID().uuidString
        let bSpace = "MiniApps B " + suffix, bTitle = "Foreign account " + suffix
        let aSpace = "MiniApps A " + suffix, aTitle = "Original account " + suffix
        let bText = "Untouched native B " + suffix, aText = "Original native A " + suffix
        let heartText = "Heart return after switch " + suffix
        let anyText = "Any return after account switch " + suffix

        companion.launch()
        XCTAssertTrue(companion.buttons["hanlin-apps-add"].firstMatch.waitForExistence(timeout: 30))
        source.launch()
        try openSource()
        try await isolationSelectEngine("any")
        let bBlock = try await isolationCreateAnyDocument(space: bSpace, title: bTitle, text: bText)
        let bBefore = try await isolationLaunch(shared, engine: "any",
            appID: "org.itorah.miniapps.fileworkshop")
        let bScope = try isolationScope(bBefore.request, engine: "any")
        XCTAssertNotEqual(bScope.account, fixture["accountID"])
        XCTAssertEqual(bBefore.request.source.documentText, bText)
        try fwPress("fileworkshop.cancel")
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 60))
        let bCancelled = try await fwAcknowledged(bBefore.request.id, shared)
        XCTAssertEqual(bCancelled.result?.status, "cancelled")
        try await isolationAnyRows([bText], originalBlock: bBlock)

        // A Heart result must survive a genuine switch to the other engine and
        // its independently selected account. No manual Heart navigation helps
        // the return after the actual companion button is pressed.
        try await isolationSelectEngine("heart")
        try openSource()
        let heart = try await isolationLaunch(shared, engine: "heart", appID: "nativeapp.textstudio")
        let heartScope = try isolationScope(heart.request, engine: "heart")
        XCTAssertEqual(heartScope.account, fixture["accountID"])
        XCTAssertEqual(heartScope.space, fixture["spaceID"])
        XCTAssertEqual(heart.request.source.documentID, fixture["objectID"])
        try isolationFillTextStudio(heartText)
        source.activate()
        try await isolationSelectEngine("any")
        try await isolationAnyRows([bText], originalBlock: bBlock)
        XCTAssertNil(try isolationRecord(heart.request.id, shared).result)
        companion.activate()
        try isolationReturnTextStudio()
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 90))
        try await isolationRequireEngine("heart")
        try expectNativeText()
        try isolationRequireVisibleText(heartText)
        let heartSaved = try await fwAcknowledged(heart.request.id, shared)
        XCTAssertEqual(heartSaved.result?.status, "success")
        XCTAssertEqual(heartSaved.result?.items.compactMap(\.text), [heartText])
        screenshot("miniapps-pending-heart-return-after-any-account")

        try await isolationSelectEngine("any")
        try await isolationAnyRows([bText], originalBlock: bBlock)
        try await isolationSignOutAny()
        let aBlock = try await isolationCreateAnyDocument(space: aSpace, title: aTitle, text: aText)
        let pending = try await isolationLaunch(shared, engine: "any", appID: "nativeapp.textstudio")
        let aScope = try isolationScope(pending.request, engine: "any")
        XCTAssertNotEqual(aScope.account, bScope.account)
        XCTAssertNotEqual(aScope.space, bScope.space)
        XCTAssertNotEqual(pending.request.source.documentID, bBefore.request.source.documentID)
        XCTAssertEqual(pending.request.source.documentText, aText)
        try isolationFillTextStudio(anyText)

        // Retire A through its real UI and reopen B while the genuine MiniApp
        // still owns A's original unfinished invocation.
        source.activate()
        try await isolationSignOutAny()
        try await isolationOpenAny(account: bScope.account, space: bSpace, title: bTitle)
        try await isolationAnyRows([bText], originalBlock: bBlock)
        try await isolationSelectEngine("heart")
        try isolationRequireVisibleText(heartText)
        companion.activate()
        try isolationReturnTextStudio()
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 90))
        try await isolationRequireEngine("any")
        try await isolationAnyRows([bText], originalBlock: bBlock)
        try await fwWait(timeout: .seconds(45)) {
            try self.isolationRecord(pending.request.id, shared).result?.status == "success"
        }
        try await isolationRequireUnacknowledged(pending.request.id, shared)
        let foreignWarm = try isolationPendingSnapshot(pending.request.id, shared, selectedAccount: bScope.account)
        screenshot("miniapps-foreign-account-result-pending")

        // A fresh process must retain the actual result without writing to B or
        // acknowledging A just because the correct engine became active.
        source.terminate()
        XCTAssertTrue(source.wait(for: .notRunning, timeout: 20))
        source.launch()
        try await isolationSelectEngine("any")
        try await isolationOpenAny(account: bScope.account, space: bSpace, title: bTitle)
        try await isolationAnyRows([bText], originalBlock: bBlock)
        try await isolationRequireUnacknowledged(pending.request.id, shared)
        let foreignCold = try isolationPendingSnapshot(pending.request.id, shared, selectedAccount: bScope.account)
        screenshot("miniapps-foreign-account-cold-result-still-pending")

        // Only the original account/Space/document may consume the result.
        try await isolationSignOutAny()
        try await isolationOpenAny(account: aScope.account, space: aSpace, title: aTitle)
        let aSavedBlocks = try await isolationAnyRows([aText, anyText], originalBlock: aBlock)
        let completed = try await fwAcknowledged(pending.request.id, shared)
        XCTAssertEqual(completed.result?.status, "success")
        XCTAssertEqual(completed.result?.items.compactMap(\.text), [anyText])
        screenshot("miniapps-original-account-consumed-once")

        // Replays are actual OS callbacks while the other engine is visible.
        let replay = try isolationCallback(pending.request)
        for _ in 0..<2 {
            try await isolationSelectEngine("heart")
            XCUIDevice.shared.system.open(replay)
            XCTAssertTrue(source.wait(for: .runningForeground, timeout: 90))
            try await isolationRequireEngine("any")
            let replayedBlocks = try await isolationAnyRows([aText, anyText], originalBlock: aBlock)
            XCTAssertEqual(replayedBlocks, aSavedBlocks)
        }
        source.terminate()
        XCTAssertTrue(source.wait(for: .notRunning, timeout: 20))
        source.launch()
        try await isolationSelectEngine("any")
        try await isolationOpenAny(account: aScope.account, space: aSpace, title: aTitle)
        let coldBlocks = try await isolationAnyRows([aText, anyText], originalBlock: aBlock)
        XCTAssertEqual(coldBlocks, aSavedBlocks)
        XCTAssertTrue(try isolationRecord(pending.request.id, shared).acknowledged)

        // Capture B again through its normal MiniApp picker after a real cold
        // reopen. This is an original native read, not an AX-only comparison.
        try await isolationSignOutAny()
        try await isolationOpenAny(account: bScope.account, space: bSpace, title: bTitle)
        try await isolationAnyRows([bText], originalBlock: bBlock)
        let bAfter = try await isolationLaunch(shared, engine: "any",
            appID: "org.itorah.miniapps.fileworkshop")
        XCTAssertEqual(try isolationScope(bAfter.request, engine: "any").account, bScope.account)
        XCTAssertEqual(bAfter.request.source.documentID, bBefore.request.source.documentID)
        XCTAssertEqual(bAfter.request.source.documentText, bBefore.request.source.documentText)
        for key in ["anytype.accountID", "anytype.spaceID", "anytype.blocks", "anytype.nativeVersion"] {
            XCTAssertEqual(bAfter.request.source.metadata[key], bBefore.request.source.metadata[key],
                "No native write may be attributed to the foreign account: " + key)
        }
        try fwPress("fileworkshop.cancel")
        XCTAssertTrue(source.wait(for: .runningForeground, timeout: 60))
        let bAfterCancelled = try await fwAcknowledged(bAfter.request.id, shared)
        XCTAssertEqual(bAfterCancelled.result?.status, "cancelled")
        try await isolationAnyRows([bText], originalBlock: bBlock)
        try await isolationSelectEngine("heart")
        try openSource()
        try expectNativeText()
        try isolationRequireVisibleText(heartText)

        let report: [String: Any] = [
            "status": "REAL_ENGINE_ACCOUNT_MINIAPPS_UI_PASS",
            "sourceSHA": try XCTUnwrap(fixture["sourceSHA"]), "runID": try XCTUnwrap(fixture["runID"]),
            "heartRequestID": heart.request.id.uuidString.lowercased(),
            "anyRequestID": pending.request.id.uuidString.lowercased(),
            "foreignReadRequestIDs": [bBefore, bAfter].map { $0.request.id.uuidString.lowercased() },
            "heartAccountID": heartScope.account, "heartSpaceID": heartScope.space,
            "heartDocumentID": try XCTUnwrap(heart.request.source.documentID), "heartReturnedText": heartText,
            "originalAnyAccountID": aScope.account, "foreignAnyAccountID": bScope.account,
            "anyDocumentID": try XCTUnwrap(pending.request.source.documentID),
            "foreignDocumentID": try XCTUnwrap(bBefore.request.source.documentID),
            "originalAnyText": aText, "anyReturnedText": anyText, "foreignAnyText": bText,
            "originalAnyBlock": aBlock, "foreignAnyBlock": bBlock, "savedAnyBlocks": aSavedBlocks,
            "foreignAccountRejectedBeforeAndAfterColdReopen": true,
            "foreignPendingObservations": [foreignWarm, foreignCold],
            "foreignNativeBlocksAndVersionUnchanged": true,
            "replayedCallbacks": 2, "sourceColdReopens": 2,
            "syntheticRequests": 0, "syntheticResults": 0, "directNativeTestMutations": 0
        ]
        let name = try XCTUnwrap(environment["PINKHA_MINIAPPS_ISOLATION_REPORT_NAME"])
        XCTAssertEqual(URL(fileURLWithPath: name).lastPathComponent, name)
        try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
            .write(to: shared.appendingPathComponent(name), options: .withoutOverwriting)
        screenshot("miniapps-engine-account-isolation-final-heart")
        source.terminate()
    }

    private func isolationTap(_ control: XCUIElement, timeout: TimeInterval = 60) throws {
        let predicate = NSPredicate(format: "exists == true AND enabled == true AND hittable == true")
        let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: predicate, object: control)], timeout: timeout)
        XCTAssertEqual(result, .completed)
        guard result == .completed else { throw NSError(domain: "MiniAppsIsolation", code: 1) }
        control.tap()
    }

    private func isolationSelectEngine(_ engine: String) async throws {
        let selector = source.buttons["pinkha.engine.selector"]
        XCTAssertTrue(selector.waitForExistence(timeout: 60))
        let display = engine == "heart" ? "Heart" : "Any"
        if selector.value as? String != display {
            try isolationTap(selector)
            try isolationTap(source.buttons["pinkha.engine.select." + engine])
        }
        try await isolationRequireEngine(engine)
    }

    private func isolationRequireEngine(_ engine: String) async throws {
        let selector = source.buttons["pinkha.engine.selector"]
        let display = engine == "heart" ? "Heart" : "Any"
        try await fwWait(timeout: .seconds(90)) {
            selector.exists && selector.isEnabled && selector.value as? String == display
        }
    }

    @discardableResult
    private func isolationAnyRows(_ texts: [String], originalBlock: String) async throws -> [String] {
        let rows = source.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-"))
        try await fwWait(timeout: .seconds(90)) {
            let actual = rows.allElementsBoundByIndex
            return actual.count == texts.count && Set(actual.compactMap { $0.value as? String }) == Set(texts)
                && actual.allSatisfy { $0.isHittable }
        }
        let ids = rows.allElementsBoundByIndex.map(\.identifier)
        XCTAssertEqual(Set(ids).count, texts.count)
        XCTAssertTrue(ids.contains(originalBlock))
        return ids.sorted()
    }

    private func isolationCreateAnyDocument(space: String, title: String, text: String) async throws -> String {
        try isolationTap(source.buttons["any-native-account-create"], timeout: 90)
        let row = source.switches["any-native-backup-acknowledged"]
        XCTAssertTrue(row.waitForExistence(timeout: 90))
        let switches = row.descendants(matching: .switch)
        XCTAssertEqual(switches.count, 1)
        XCTAssertEqual(switches.firstMatch.value as? String, "0")
        try isolationTap(switches.firstMatch)
        try await fwWait { row.value as? String == "1" }
        // Never read or attach the recovery phrase or a complete AX tree here.
        try isolationTap(source.buttons["any-native-backup-continue"])
        let name = source.textFields["any-native-space-name"]
        try isolationTap(name); name.typeText(space)
        try isolationTap(source.buttons["any-native-space-create"])
        try isolationTap(source.buttons["any-native-workspace-setup"], timeout: 120)
        try isolationTap(source.buttons["any-native-create-menu"], timeout: 90)
        try isolationTap(source.buttons["any-native-new-document"])
        let titleField = source.descendants(matching: .any).matching(identifier: "any-native-name-input").firstMatch
        try isolationTap(titleField); titleField.typeText(title)
        try isolationTap(source.buttons["any-native-name-confirm"])
        try isolationTap(source.buttons["any-native-add-paragraph"], timeout: 90)
        let rows = source.textViews.matching(NSPredicate(format: "identifier BEGINSWITH %@", "any-native-block-"))
        try isolationTap(rows.firstMatch); rows.firstMatch.typeText(text)
        try isolationTap(source.buttons["any-native-editor-done"])
        let status = source.descendants(matching: .any).matching(identifier: "any-native-save-status").firstMatch
        try await fwWait { status.exists && status.value as? String == "saved" }
        XCTAssertEqual(rows.count, 1)
        XCTAssertEqual(rows.firstMatch.value as? String, text)
        return rows.firstMatch.identifier
    }

    private func isolationSignOutAny() async throws {
        let close = source.buttons["any-native-close-workspace"]
        if !close.exists || !close.isHittable {
            let back = source.navigationBars.buttons.matching(NSPredicate(
                format: "label == %@ OR label == %@", "Library", "ספרייה")).firstMatch
            try isolationTap(back)
        }
        try isolationTap(close)
        try isolationTap(source.buttons["any-native-account-sign-out"])
        try await fwWait(timeout: .seconds(90)) {
            self.source.buttons["any-native-account-create"].exists
                && self.source.buttons["any-native-account-create"].isEnabled
        }
    }

    private func isolationOpenAny(account: String, space: String, title: String) async throws {
        let accounts = source.buttons.matching(identifier: "any-native-saved-account")
            .matching(NSPredicate(format: "label CONTAINS %@", String(account.suffix(8))))
        XCTAssertTrue(accounts.firstMatch.waitForExistence(timeout: 90))
        XCTAssertEqual(accounts.count, 1, "The original saved-account selector must resolve exactly")
        try isolationTap(accounts.firstMatch)
        try isolationTap(source.buttons[space].firstMatch, timeout: 90)
        try isolationTap(source.buttons[title].firstMatch, timeout: 90)
    }

    private func isolationLaunch(_ shared: URL, engine: String, appID: String) async throws -> FWRecord {
        let before = Set(try fwRecords(shared).map { $0.request.id })
        if engine == "any" {
            try isolationTap(source.buttons["any-native-document-options"])
            try isolationTap(source.buttons["any-native-miniapps"])
        } else {
            try isolationTap(source.buttons["pinkha.miniapps.open"].firstMatch)
        }
        let launch = source.buttons["miniapps-launch-" + appID].firstMatch
        if !launch.waitForExistence(timeout: 3) {
            try isolationTap(source.buttons["miniapps-more"].firstMatch)
        }
        try isolationTap(launch)
        XCTAssertTrue(companion.wait(for: .runningForeground, timeout: 60))
        if appID == "nativeapp.textstudio" {
            XCTAssertTrue(companion.textViews["miniapps.textstudio.editor"].firstMatch.waitForExistence(timeout: 60))
        } else {
            _ = try await fwEditor()
        }
        let added = try fwRecords(shared).filter { !before.contains($0.request.id) }
        XCTAssertEqual(added.count, 1)
        let record = try XCTUnwrap(added.first)
        XCTAssertEqual(record.request.appID, appID)
        _ = try isolationScope(record.request, engine: engine)
        XCTAssertFalse(record.acknowledged); XCTAssertNil(record.result)
        return record
    }

    private func isolationScope(_ request: FWRequest, engine: String) throws -> (account: String, space: String) {
        XCTAssertEqual(request.source.metadata["pinkha.engine"], engine)
        let account = try XCTUnwrap(request.source.metadata["anytype.accountID"])
        let space = try XCTUnwrap(request.source.metadata["anytype.spaceID"])
        XCTAssertFalse(account.isEmpty); XCTAssertFalse(space.isEmpty)
        XCTAssertFalse(try XCTUnwrap(request.source.documentID).isEmpty)
        return (account, space)
    }

    private func isolationRecord(_ id: UUID, _ shared: URL) throws -> FWRecord {
        try XCTUnwrap(try fwRecords(shared).first { $0.request.id == id })
    }

    private func isolationFillTextStudio(_ text: String) throws {
        let input = companion.textViews["miniapps.textstudio.editor"].firstMatch
        XCTAssertTrue(input.waitForExistence(timeout: 30))
        XCTAssertEqual(input.value as? String, "")
        try isolationTap(input); input.typeText(text)
        XCTAssertEqual(input.value as? String, text)
    }

    private func isolationReturnTextStudio() throws {
        try isolationTap(companion.buttons["miniapps.textstudio.return"])
    }

    private func isolationRequireVisibleText(_ text: String) throws {
        let visible = source.descendants(matching: .any).matching(
            NSPredicate(format: "value == %@ OR label == %@", text, text)).firstMatch
        XCTAssertTrue(visible.waitForExistence(timeout: 90))
    }

    private func isolationRequireUnacknowledged(_ id: UUID, _ shared: URL) async throws {
        let clock = ContinuousClock(), deadline = clock.now.advanced(by: .seconds(5))
        repeat {
            let record = try isolationRecord(id, shared)
            XCTAssertEqual(record.result?.status, "success")
            XCTAssertFalse(record.acknowledged, "Foreign account must leave the actual return pending")
            try await Task.sleep(for: .milliseconds(200))
        } while clock.now < deadline
    }

    private func isolationPendingSnapshot(_ id: UUID, _ shared: URL,
                                          selectedAccount: String) throws -> [String: Any] {
        let path = shared.appendingPathComponent("requests")
            .appendingPathComponent(id.uuidString.lowercased() + ".json")
        let raw = try Data(contentsOf: path)
        let actual = try JSONDecoder().decode(FWRecord.self, from: raw)
        XCTAssertEqual(actual.request.id, id)
        XCTAssertEqual(actual.result?.status, "success")
        XCTAssertFalse(actual.acknowledged)
        XCTAssertNotEqual(actual.request.source.metadata["anytype.accountID"], selectedAccount)
        return ["recordJSON": try XCTUnwrap(String(data: raw, encoding: .utf8)),
                "recordSHA256": fwDigest(raw), "selectedAccountID": selectedAccount,
                "observedAt": Date().timeIntervalSince1970]
    }

    private func isolationCallback(_ request: FWRequest) throws -> URL {
        var callback = try XCTUnwrap(URLComponents(
            url: XCTUnwrap(request.callbacks.success), resolvingAgainstBaseURL: false))
        callback.queryItems = (callback.queryItems ?? []).filter { $0.name != "request" } +
            [URLQueryItem(name: "request", value: request.id.uuidString)]
        return try XCTUnwrap(callback.url)
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
