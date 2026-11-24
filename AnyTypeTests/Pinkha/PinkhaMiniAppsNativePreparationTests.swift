#if DEBUG && targetEnvironment(simulator)
import Foundation
import CryptoKit
import AnytypeCore
import HanlinMiniAppsBridge
import ProtobufMessages
import Services
import SwiftProtobuf
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

    @Test("Apply selected text, preserve newer native content, and upload/read back a real file")
    func applySelectedTextAndPreserveNewerNativeContent() async throws {
        let environment = ProcessInfo.processInfo.environment
        try #require(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1")
        let fixture = try JSONDecoder().decode([String: String].self, from: Data(contentsOf: fixtureURL()))
        try #require(fixture["sourceSHA"] == environment["GITHUB_SHA"] && fixture["runID"] == environment["GITHUB_RUN_ID"])
        let accountID = try #require(fixture["accountID"])
        let spaceID = try #require(fixture["spaceID"])
        let clock = ContinuousClock(), deadline = clock.now.advanced(by: .seconds(45))
        while Container.shared.accountManager().account.id != accountID && clock.now < deadline {
            try await Task.sleep(for: .milliseconds(100))
        }
        try #require(Container.shared.accountManager().account.id == accountID)
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceID)
        let object = try await Container.shared.objectActionsService().createObject(
            name: "MiniApps native adapter " + UUID().uuidString, typeUniqueKey: .page,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceID, origin: .none, templateId: nil)
        let state = EditorPageModuleAssembly().buildStateModel(
            data: .init(objectId: object.id, spaceId: spaceID), output: nil, showHeader: true, torahSession: nil)
        let document = state.model.document
        try await document.open()
        do {
            // This method tests the native adapter, not another producer/UI journey.
            // Its mailbox is isolated within the actual entitled shared container.
            let shared = try #require(FileManager.default.containerURL(
                forSecurityApplicationGroupIdentifier: "group.com.itorah.shared"))
            let mailbox = shared.appendingPathComponent("native-adapter-" + UUID().uuidString, isDirectory: true)
            let store = try MiniAppBridgeStore(containerURL: mailbox)
            defer { try? FileManager.default.removeItem(at: mailbox) }
            let prefix = "Prefix ", selected = "עברית 👨‍👩‍👧", suffix = " suffix"
            let original = prefix + selected + suffix
            let replacement = "חדש 🙂"
            let expected = prefix + replacement + suffix
            let blockID = try await Container.shared.blockService().addFirstBlock(contextId: object.id,
                info: .empty(content: .text(.plain(original, contentType: .text))))
            let childID = try await Container.shared.blockService().add(contextId: object.id, targetId: blockID,
                info: .empty(content: .text(.plain("Unchanged child", contentType: .text))), position: .inner)
            let siblingID = try await Container.shared.blockService().add(contextId: object.id, targetId: blockID,
                info: .empty(content: .text(.plain("Unchanged sibling", contentType: .text))), position: .bottom)
            let prefixMark = Anytype_Model_Block.Content.Text.Mark.with {
                $0.type = .bold; $0.range = NSRange(location: 0, length: prefix.utf16.count).asMiddleware
            }
            let suffixMark = Anytype_Model_Block.Content.Text.Mark.with {
                $0.type = .italic
                $0.range = NSRange(location: (prefix + selected).utf16.count, length: suffix.utf16.count).asMiddleware
            }
            let marks = Anytype_Model_Block.Content.Text.Marks.with { $0.marks = [prefixMark, suffixMark] }
            try await state.model.blockActionService.setText(contextId: object.id, blockId: blockID,
                middlewareString: .init(text: original, marks: marks))
            let before = try await Container.shared.objectLifecycleService().openForPreview(
                contextId: object.id, spaceId: spaceID)
            let originalBlock = try #require(before.blocks.first { $0.id == blockID })
            try #require(originalBlock.text.text == original && originalBlock.text.marks == marks)
            try #require(originalBlock.childrenIds == [childID])
            let tree = Dictionary(uniqueKeysWithValues: before.blocks.map { ($0.id, $0.childrenIds) })
            let request = try await selectionRequest(editor: state.viewController, store: store,
                blockID: blockID, expectedText: original, selectedText: selected)
            let result = MiniAppResult(requestID: request.id, operation: .replaceSelection,
                items: [.init(kind: .text, text: replacement)])
            _ = try store.enqueue(request)
            try store.complete(result)
            let preserved = try await PinkhaMiniAppsResultApplier.apply(
                request: request, result: result, editor: state.viewController, store: store)
            try #require(!preserved)
            let replaced = try await Container.shared.objectLifecycleService().openForPreview(
                contextId: object.id, spaceId: spaceID)
            let replacementBlock = try #require(replaced.blocks.first { $0.id == blockID })
            var shiftedSuffix = suffixMark
            shiftedSuffix.range = NSRange(location: (prefix + replacement).utf16.count, length: suffix.utf16.count).asMiddleware
            let expectedMarks = Anytype_Model_Block.Content.Text.Marks.with { $0.marks = [prefixMark, shiftedSuffix] }
            try #require(replacementBlock.text.text == expected && replacementBlock.text.marks == expectedMarks)
            try #require(replacementBlock.text.style == originalBlock.text.style)
            try #require(Dictionary(uniqueKeysWithValues: replaced.blocks.map { ($0.id, $0.childrenIds) }) == tree)
            try #require(replaced.blocks.first(where: { $0.id == childID })?.text.text == "Unchanged child")
            try #require(replaced.blocks.first(where: { $0.id == siblingID })?.text.text == "Unchanged sibling")

            let conflictRequest = try await selectionRequest(editor: state.viewController, store: store,
                blockID: blockID, expectedText: expected, selectedText: replacement)
            let newerText = expected + " — subsequent native edit"
            try await state.model.blockActionService.setText(contextId: object.id, blockId: blockID,
                middlewareString: .init(text: newerText, marks: expectedMarks))
            let replayed = try await PinkhaMiniAppsResultApplier.apply(
                request: request, result: result, editor: state.viewController, store: store)
            try #require(!replayed)
            let afterReplay = try await Container.shared.objectLifecycleService().openForPreview(
                contextId: object.id, spaceId: spaceID)
            try #require(afterReplay.blocks.first(where: { $0.id == blockID })?.text.text == newerText)
            try #require(Dictionary(uniqueKeysWithValues: afterReplay.blocks.map { ($0.id, $0.childrenIds) }) == tree)
            let alternate = "Preserved MiniApps result " + UUID().uuidString
            let conflictResult = MiniAppResult(requestID: conflictRequest.id, operation: .replaceSelection,
                items: [.init(kind: .text, text: alternate)])
            _ = try store.enqueue(conflictRequest)
            try store.complete(conflictResult)
            let conflictPreserved = try await PinkhaMiniAppsResultApplier.apply(
                request: conflictRequest, result: conflictResult, editor: state.viewController, store: store)
            try #require(conflictPreserved)
            let conflictReplayed = try await PinkhaMiniAppsResultApplier.apply(
                request: conflictRequest, result: conflictResult, editor: state.viewController, store: store)
            try #require(conflictReplayed)
            try #require(try store.pendingResults(sourceAppID: PinkhaMiniAppsContext.sourceAppID).isEmpty)
            try await document.close()
            try await document.open()
            let persisted = try await Container.shared.objectLifecycleService().openForPreview(
                contextId: object.id, spaceId: spaceID)
            let current = try #require(persisted.blocks.first { $0.id == blockID })
            try #require(current.text.text == newerText && current.text.marks == expectedMarks)
            try #require(current.childrenIds == [childID] && current.text.style == originalBlock.text.style)
            try #require(persisted.blocks.first(where: { $0.id == childID })?.text.text == "Unchanged child")
            try #require(persisted.blocks.first(where: { $0.id == siblingID })?.text.text == "Unchanged sibling")
            let preservedOutputs = persisted.blocks.filter { $0.text.text == alternate }
            try #require(preservedOutputs.count == 1 && persisted.blocks.count == before.blocks.count + 1)
            let outputID = preservedOutputs[0].id
            try #require(Set(persisted.blocks.map(\.id)).subtracting([outputID]) == Set(before.blocks.map(\.id)))
            try #require(preservedOutputs[0].fields.fields[PinkhaMiniAppsResultApplier.receiptField]?.stringValue
                == conflictRequest.id.uuidString.lowercased() + ":0")
            for (id, children) in tree {
                let actual = try #require(persisted.blocks.first { $0.id == id })
                try #require(actual.childrenIds.filter { $0 != outputID } == children)
            }
            // Exercise the original native file upload, not a manufactured upload result.
            let fileBytes = Data(("MiniApps native attachment עברית 🙂 " + UUID().uuidString + "\n").utf8)
            let attachment = try store.writeAttachment(fileBytes, name: "miniapps-native-fixture.txt",
                typeIdentifier: "public.plain-text")
            let fileContext = try await PinkhaMiniAppsContext.capture(editor: state.viewController, store: store)
            let fileRequest = MiniAppInvocation(appID: "hanlin.fixture.native-attachment",
                source: fileContext.source, operation: .insert)
            let fileResult = MiniAppResult(requestID: fileRequest.id, operation: .insert, items: [attachment])
            _ = try store.enqueue(fileRequest)
            try store.complete(fileResult)
            let filePreserved = try await PinkhaMiniAppsResultApplier.apply(
                request: fileRequest, result: fileResult, editor: state.viewController, store: store)
            try #require(!filePreserved)
            let fileReplayed = try await PinkhaMiniAppsResultApplier.apply(
                request: fileRequest, result: fileResult, editor: state.viewController, store: store)
            try #require(!fileReplayed)
            try await document.close()
            try await document.open()
            let fileView = try await Container.shared.objectLifecycleService().openForPreview(
                contextId: object.id, spaceId: spaceID)
            let fileMarker = fileRequest.id.uuidString.lowercased() + ":0"
            let nativeFiles = fileView.blocks.filter {
                $0.fields.fields[PinkhaMiniAppsResultApplier.receiptField]?.stringValue == fileMarker
            }
            try #require(nativeFiles.count == 1 && fileView.blocks.count == before.blocks.count + 2)
            let nativeFile = try #require(BlockInformationConverter.convert(block: nativeFiles[0]))
            guard case .file(let content) = nativeFile.content else {
                throw NSError(domain: "MiniAppsNativeAdapter", code: 1,
                    userInfo: [NSLocalizedDescriptionKey: "The actual native upload is not a file block"])
            }
            try #require(content.state == .done && !content.metadata.targetObjectId.isEmpty)
            try #require(Set(fileView.blocks.map(\.id)).subtracting([nativeFile.id]) == Set(persisted.blocks.map(\.id)))
            let untouchedText = try #require(fileView.blocks.first { $0.id == blockID })
            try #require(untouchedText.text.text == newerText && untouchedText.text.marks == expectedMarks)
            try #require(untouchedText.childrenIds == [childID])
            let fileURL = try #require(ContentUrlBuilder.fileUrl(fileId: content.metadata.targetObjectId))
            let (actualBytes, response) = try await URLSession.shared.data(from: fileURL)
            let http = try #require(response as? HTTPURLResponse)
            try #require((200..<300).contains(http.statusCode) && actualBytes == fileBytes)
            try #require(try store.pendingResults(sourceAppID: PinkhaMiniAppsContext.sourceAppID).isEmpty)
            let proof: [String: Any] = ["status": "NATIVE_MINIAPPS_ADAPTER_PASS",
                "sourceSHA": try #require(environment["GITHUB_SHA"]),
                "runID": try #require(environment["GITHUB_RUN_ID"]), "objectID": object.id,
                "blockID": blockID, "childID": childID, "siblingID": siblingID,
                "requestIDs": [request.id.uuidString.lowercased(), conflictRequest.id.uuidString.lowercased(),
                               fileRequest.id.uuidString.lowercased()],
                "preservedOutputBlockID": outputID, "preservedOutputCount": preservedOutputs.count,
                "replacementPreservedBlockID": true, "replacementPreservedTree": true,
                "nativeMarksPreserved": true, "replayPreservedNewerText": true,
                "conflictPreservedNewerText": true, "producerRoundTrips": 0,
                "nativeAttachmentUploaded": true, "nativeAttachmentByteReadback": true,
                "nativeAttachmentCount": nativeFiles.count, "nativeAttachmentBlockID": nativeFile.id,
                "nativeAttachmentObjectID": content.metadata.targetObjectId,
                "nativeAttachmentBytes": actualBytes.count,
                "nativeAttachmentSHA256": SHA256.hash(data: actualBytes).map { String(format: "%02x", $0) }.joined()]
            let destination = try fixtureURL().deletingLastPathComponent()
                .appendingPathComponent("miniapps-native-adapter-readback.json")
            try JSONSerialization.data(withJSONObject: proof, options: [.sortedKeys]).write(to: destination, options: .atomic)
            try await document.close()
            print("MINIAPPS_NATIVE_ADAPTER_READBACK_PASS")
        } catch {
            try? await document.close()
            throw error
        }
    }

    private func selectionRequest(editor: EditorPageController, store: MiniAppBridgeStore,
                                  blockID: String, expectedText: String, selectedText: String) async throws -> MiniAppInvocation {
        let context = try await PinkhaMiniAppsContext.capture(editor: editor, store: store)
        let source = context.source
        let data = Data(try #require(source.metadata["anytype.blocks"]).utf8)
        let snapshots = try JSONDecoder().decode([PinkhaMiniAppsBlockSnapshot].self, from: data)
        try #require(snapshots.first(where: { $0.id == blockID })?.text == expectedText)
        let range = (expectedText as NSString).range(of: selectedText)
        try #require(range.location != NSNotFound && range.length > 0)
        var metadata = source.metadata
        metadata["anytype.insertionAnchor"] = blockID
        return MiniAppInvocation(appID: "nativeapp.textstudio", source: .init(
            appID: source.appID, displayName: source.displayName, documentID: source.documentID,
            documentTitle: source.documentTitle, revision: source.revision,
            selection: .init(location: range.location, length: range.length, text: selectedText, blockIDs: [blockID]),
            documentText: source.documentText, kind: source.kind, locator: source.locator,
            sceneID: source.sceneID, metadata: metadata), inputs: [.init(kind: .text, text: selectedText)],
            operation: .replaceSelection)
    }

    private func fixtureURL() throws -> URL {
        try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
            appropriateFor: nil, create: true).appendingPathComponent("miniapps-native-fixture.json")
    }
}
#endif
