#if DEBUG && targetEnvironment(simulator)
import Foundation
import AnytypeCore
import HanlinMiniAppsBridge
import ProtobufMessages
import Services
import Testing
@testable import Anytype

@Suite("MiniApps original native disposable document", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_MINIAPPS_NATIVE_TESTING"] == "1"))
@MainActor
struct PinkhaMiniAppsNativePreparationTests {
    @Test("Create one real local account, Space and ordinary Page")
    func prepareMiniAppsDocument() async throws {
        let environment = ProcessInfo.processInfo.environment
        try #require(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1")
        try #require(Container.shared.accountManager().account.id.isEmpty)
        let expectedGroup = try #require(environment["PINKHA_MINIAPPS_NATIVE_GROUP"])
        try #require(TargetsConstants.appGroup == expectedGroup)
        try #require(Bundle.main.bundleIdentifier == environment["PINKHA_MINIAPPS_SOURCE_BUNDLE"])
        let originalGroup = try #require(FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: TargetsConstants.appGroup))
        try #require(try originalGroup.resourceValues(forKeys: [.isDirectoryKey]).isDirectory == true)
        _ = try MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared")
        let destination = try fixtureURL()
        try #require(!FileManager.default.fileExists(atPath: destination.path))

        FeatureFlags.update(key: .logMiddlewareRequests, value: false)
        let handler = try #require(InvocationSettings.handler as? InvocationMesagesHandler)
        handler.enableLogger = false
        Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)
        let auth = Container.shared.authService()
        let mnemonic = try await auth.createWallet()
        try #require(!mnemonic.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        let seed = Container.shared.seedService()
        try seed.saveSeed(mnemonic)
        try #require(try seed.obtainSeed() == mnemonic.trimmingCharacters(in: .whitespacesAndNewlines))
        let account = try await auth.createAccount(name: "MiniApps disposable", iconOption: 1, imagePath: "")
        let space = try await Container.shared.workspaceService().createSpace(
            name: "MiniApps disposable Space", iconOption: 1, accessType: .private,
            useCase: .none, withChat: false, spaceType: .regular)
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: space.spaceID)
        let nonce = UUID().uuidString
        let object = try await Container.shared.objectActionsService().createObject(
            name: "MiniApps native " + nonce, typeUniqueKey: .page,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: space.spaceID, origin: .none, templateId: nil)
        let document = Container.shared.openedDocumentProvider().document(objectId: object.id, spaceId: space.spaceID)
        try await document.open()
        let original = "Original MiniApps paragraph " + nonce
        let returned = "מיני אפליקציות 🙂 " + nonce
        let blockID = try await Container.shared.blockService().addFirstBlock(contextId: object.id,
            info: .empty(content: .text(.plain(original, contentType: .text))))
        let native = try await Container.shared.objectLifecycleService().openForPreview(
            contextId: object.id, spaceId: space.spaceID)
        try #require(native.blocks.contains { $0.id == blockID && $0.text.text == original })
        try await document.close()
        let fixture: [String: Any] = [
            "sourceSHA": try #require(environment["GITHUB_SHA"]),
            "runID": try #require(environment["GITHUB_RUN_ID"]),
            "accountID": account.id, "spaceID": space.spaceID, "objectID": object.id,
            "blockID": blockID, "originalText": original, "returnedText": returned,
            "coldReturnedText": "חזרה לאפליקציה שנסגרה 🙂 " + nonce
        ]
        try JSONSerialization.data(withJSONObject: fixture, options: [.sortedKeys])
            .write(to: destination, options: .withoutOverwriting)
        try await Container.shared.authMiddleService().preloadRemainingSpaces()
        print("MINIAPPS_NATIVE_FIXTURE_READY")
    }

    @Test("Verify actual saved Heart blocks after the two-app UI return and cold reopen")
    func verifyReturnedNativeDocument() async throws {
        let environment = ProcessInfo.processInfo.environment
        try #require(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1")
        let data = try Data(contentsOf: fixtureURL())
        let fixture = try #require(JSONSerialization.jsonObject(with: data) as? [String: String])
        let accountID = try #require(fixture["accountID"])
        let spaceID = try #require(fixture["spaceID"])
        let objectID = try #require(fixture["objectID"])
        let original = try #require(fixture["originalText"])
        let returned = try #require(fixture["returnedText"])
        let coldReturned = try #require(fixture["coldReturnedText"])
        let requestID = try #require(environment["PINKHA_MINIAPPS_REQUEST_ID"]).lowercased()
        let coldRequestID = try #require(environment["PINKHA_MINIAPPS_COLD_REQUEST_ID"]).lowercased()
        try #require(requestID != coldRequestID)
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        while Container.shared.accountManager().account.id != accountID && clock.now < deadline {
            try await Task.sleep(for: .milliseconds(100))
        }
        try #require(Container.shared.accountManager().account.id == accountID)
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceID)
        let view = try await Container.shared.objectLifecycleService().openForPreview(contextId: objectID, spaceId: spaceID)
        try #require(view.rootID == objectID)
        let originals = view.blocks.filter { $0.text.text == original }
        let results = view.blocks.filter { $0.text.text == returned }
        let coldResults = view.blocks.filter { $0.text.text == coldReturned }
        try #require(originals.count == 1 && originals[0].id == fixture["blockID"])
        try #require(results.count == 1 && coldResults.count == 1)
        try #require(results[0].id != coldResults[0].id)
        try #require(results[0].fields.fields[PinkhaMiniAppsResultApplier.receiptField]?.stringValue == requestID + ":0")
        try #require(coldResults[0].fields.fields[PinkhaMiniAppsResultApplier.receiptField]?.stringValue == coldRequestID + ":0")
        let store = try MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared")
        try #require(try store.pendingResults(sourceAppID: PinkhaMiniAppsContext.sourceAppID)
            .allSatisfy { ![requestID, coldRequestID].contains($0.requestID.uuidString.lowercased()) })
        let proof: [String: Any] = ["status": "NATIVE_HEART_READBACK_PASS",
            "sourceSHA": try #require(environment["GITHUB_SHA"]),
            "runID": try #require(environment["GITHUB_RUN_ID"]), "requestIDs": [requestID, coldRequestID],
            "objectID": objectID, "originalBlockID": originals[0].id, "returnedBlockID": results[0].id,
            "coldReturnedBlockID": coldResults[0].id,
            "originalCount": originals.count, "returnedCount": results.count, "coldReturnedCount": coldResults.count]
        let destination = try fixtureURL().deletingLastPathComponent().appendingPathComponent("miniapps-native-readback.json")
        try JSONSerialization.data(withJSONObject: proof, options: [.sortedKeys]).write(to: destination, options: .atomic)
        print("MINIAPPS_NATIVE_HEART_READBACK_PASS")
    }

    private func fixtureURL() throws -> URL {
        try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
            appropriateFor: nil, create: true).appendingPathComponent("miniapps-native-fixture.json")
    }
}
#endif
