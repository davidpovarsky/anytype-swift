#if DEBUG && targetEnvironment(simulator)
import Foundation
import CryptoKit
import AnytypeCore
import HanlinMiniAppsBridge
import ProtobufMessages
import Services
import SwiftProtobuf
import Testing
import UIKit
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
            "sourceSHA": try #require(environment["PINKHA_MINIAPPS_SOURCE_SHA"]),
            "runID": try #require(environment["PINKHA_MINIAPPS_EXECUTION_ID"]),
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
            "sourceSHA": try #require(environment["PINKHA_MINIAPPS_SOURCE_SHA"]),
            "runID": try #require(environment["PINKHA_MINIAPPS_EXECUTION_ID"]), "requestIDs": [requestID, coldRequestID],
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
        try #require(fixture["sourceSHA"] == environment["PINKHA_MINIAPPS_SOURCE_SHA"] && fixture["runID"] == environment["PINKHA_MINIAPPS_EXECUTION_ID"])
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
            let selectionProof = try await verifyNestedTableSelection(editor: state.viewController,
                store: store, previousBlockID: siblingID, previousText: "Unchanged sibling")
            var proof: [String: Any] = ["status": "NATIVE_MINIAPPS_ADAPTER_PASS",
                "sourceSHA": try #require(environment["PINKHA_MINIAPPS_SOURCE_SHA"]),
                "runID": try #require(environment["PINKHA_MINIAPPS_EXECUTION_ID"]), "objectID": object.id,
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
            proof.merge(selectionProof) { _, new in new }
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

    /// Exercise the real native table cell plus its UIKit text component. This is
    /// adapter coverage, not a claim that an additional external UI journey ran.
    private func verifyNestedTableSelection(editor: EditorPageController, store: MiniAppBridgeStore,
                                           previousBlockID: String, previousText: String) async throws -> [String: Any] {
        let model = try #require(editor.viewModel as? EditorPageViewModel)
        let document = model.document
        let tableService = Container.shared.blockTableService()
        let tableID = try await tableService.createTable(contextId: document.objectId,
            targetId: previousBlockID, position: .bottom, rowsCount: 1, columnsCount: 1)
        let initial = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
        let table = try #require(initial.first { $0.id == tableID })
        let rows = try #require(initial.first {
            table.childrenIds.contains($0.id) && $0.content == .layout(.init(style: .tableRows))
        })
        let rowID = try #require(rows.childrenIds.first)
        try #require(rows.childrenIds.count == 1)
        try await tableService.rowListFill(contextId: document.objectId, targetIds: [rowID])
        let filled = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
        let row = try #require(filled.first { $0.id == rowID })
        let cell = try #require(filled.first {
            guard row.childrenIds.contains($0.id), case .text = $0.content else { return false }
            return true
        })
        let cellID = cell.id
        try #require(cellID != tableID && cellID != previousBlockID)
        let prefix = "Table prefix ", selected = "עברית 👨‍👩‍👧", suffix = " table suffix"
        let original = prefix + selected + suffix
        let returned = "נבחר 🙂"
        let expected = prefix + returned + suffix
        try await model.blockActionService.setText(contextId: document.objectId, blockId: cellID,
            middlewareString: .init(text: original, marks: .init()))

        editor.loadViewIfNeeded()
        let previous = TextBlockContentView(frame: .zero)
        var previousConfiguration = TextBlockContentConfiguration.empty
        previousConfiguration.blockId = previousBlockID
        previousConfiguration.content = .plain(previousText, contentType: .text)
        previousConfiguration.attributedString = NSAttributedString(string: previousText)
        previous.update(with: previousConfiguration)
        editor.view.addSubview(previous)
        editor.textBlockDidBeginEditing(firstResponderView: previous.textView.textView)
        // Native table cells have a second collection-cell boundary. Its text
        // component owns cellID; the outer table block must never be selected.
        let outerCell = UICollectionViewCell(frame: .zero)
        let nestedCell = UICollectionViewCell(frame: .zero)
        let selectedContent = TextBlockContentView(frame: .zero)
        var selectedConfiguration = TextBlockContentConfiguration.empty
        selectedConfiguration.blockId = cellID
        selectedConfiguration.content = .plain(original, contentType: .text)
        selectedConfiguration.attributedString = NSAttributedString(string: original)
        selectedContent.update(with: selectedConfiguration)
        editor.view.addSubview(outerCell)
        outerCell.contentView.addSubview(nestedCell)
        nestedCell.contentView.addSubview(selectedContent)
        defer {
            outerCell.removeFromSuperview()
            previous.removeFromSuperview()
            editor.blockDidFinishEditing()
        }
        let selectedView = selectedContent.textView.textView
        let range = (original as NSString).range(of: selected)
        selectedView.selectedRange = range
        try #require(editor.firstResponderView === previous.textView.textView)
        try #require(PinkhaMiniAppsEntry.selectionAction(textView: selectedView, range: range) != nil)
        let origin = try #require(PinkhaMiniAppsTextSelection(textView: selectedView, range: range, editor: editor))
        let context = try await PinkhaMiniAppsContext.capture(editor: editor, store: store, selection: origin)
        let captured = try #require(context.source.selection)
        try #require(captured.blockIDs == [cellID] && captured.text == selected)
        try #require(captured.location == range.location && captured.length == range.length)
        try #require(context.inputs.first?.text == selected)
        try #require(context.source.metadata["anytype.insertionAnchor"] == cellID)
        let before = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
        let tree = Dictionary(uniqueKeysWithValues: before.map { ($0.id, $0.childrenIds) })
        let request = MiniAppInvocation(appID: "nativeapp.textstudio", source: context.source,
            inputs: context.inputs, operation: .replaceSelection)
        let result = MiniAppResult(requestID: request.id, operation: .replaceSelection,
            items: [.init(kind: .text, text: returned)])
        _ = try store.enqueue(request)
        try store.complete(result)
        let preserved = try await PinkhaMiniAppsResultApplier.apply(
            request: request, result: result, editor: editor, store: store)
        let replayed = try await PinkhaMiniAppsResultApplier.apply(
            request: request, result: result, editor: editor, store: store)
        try #require(!preserved && !replayed)

        // A reused cell and a detached cell must each reject their original menu
        // token even though the old cached responder still belongs to this editor.
        selectedContent.update(with: previousConfiguration)
        try await requireUnavailableSelection(origin, editor: editor, store: store)
        selectedConfiguration.content = .plain(expected, contentType: .text)
        selectedConfiguration.attributedString = NSAttributedString(string: expected)
        selectedContent.update(with: selectedConfiguration)
        outerCell.removeFromSuperview()
        try await requireUnavailableSelection(origin, editor: editor, store: store)
        try await document.close()
        try await document.open()
        let persisted = try await PinkhaMiniAppsContext.nativeBlocks(document: document)
        try #require(Dictionary(uniqueKeysWithValues: persisted.map { ($0.id, $0.childrenIds) }) == tree)
        let persistedCell = try #require(persisted.first { $0.id == cellID })
        let previousCell = try #require(persisted.first { $0.id == previousBlockID })
        guard case .text(let actual) = persistedCell.content,
              case .text(let previousActual) = previousCell.content else {
            throw NSError(domain: "MiniAppsNativeAdapter", code: 2,
                userInfo: [NSLocalizedDescriptionKey: "Native table/previous text blocks disappeared"])
        }
        try #require(actual.text == expected && previousActual.text == previousText)
        try #require(try store.pendingResults(sourceAppID: PinkhaMiniAppsContext.sourceAppID).isEmpty)
        return ["nestedTableSelectionCaptured": true, "nestedTableReplacementPersisted": true,
                "expiredSelectionDidNotFallback": true, "nestedTableBlockID": tableID,
                "nestedTextBlockID": cellID, "nestedSelectionRequestID": request.id.uuidString.lowercased()]
    }

    private func requireUnavailableSelection(_ origin: PinkhaMiniAppsTextSelection,
                                            editor: EditorPageController, store: MiniAppBridgeStore) async throws {
        do {
            _ = try await PinkhaMiniAppsContext.capture(editor: editor, store: store, selection: origin)
        } catch PinkhaMiniAppsError.documentUnavailable {
            return
        }
        throw NSError(domain: "MiniAppsNativeAdapter", code: 3,
            userInfo: [NSLocalizedDescriptionKey: "An expired selection silently used another text view"])
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


    @Test("Read original Heart blocks and original receipts after real engine/account callback isolation")
    func verifyEngineAccountIsolationNativeHeartReadback() async throws {
        let environment = ProcessInfo.processInfo.environment
        try #require(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1")
        let fixture = try JSONDecoder().decode([String: String].self, from: Data(contentsOf: fixtureURL()))
        let name = try #require(environment["PINKHA_MINIAPPS_ISOLATION_REPORT_NAME"])
        try #require(URL(fileURLWithPath: name).lastPathComponent == name)
        let group = try #require(FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: "group.com.itorah.shared"))
        let bridge = group.appendingPathComponent("MiniAppsBridge/v1", isDirectory: true)
        try #require(bridge.standardizedFileURL.path == environment["PINKHA_MINIAPPS_SHARED_BRIDGE"])
        let raw = try Data(contentsOf: bridge.appendingPathComponent(name))
        try #require(raw.count < 64 * 1024)
        let report = try #require(JSONSerialization.jsonObject(with: raw) as? [String: Any])
        try #require(report["status"] as? String == "REAL_ENGINE_ACCOUNT_MINIAPPS_UI_PASS")
        try #require(report["sourceSHA"] as? String == fixture["sourceSHA"]
            && report["sourceSHA"] as? String == environment["PINKHA_MINIAPPS_SOURCE_SHA"])
        try #require(report["runID"] as? String == fixture["runID"]
            && report["runID"] as? String == environment["PINKHA_MINIAPPS_EXECUTION_ID"])
        let account = try #require(fixture["accountID"]), space = try #require(fixture["spaceID"])
        let object = try #require(fixture["objectID"])
        try #require(report["heartAccountID"] as? String == account
            && report["heartSpaceID"] as? String == space && report["heartDocumentID"] as? String == object)
        let heartRequestID = try #require(report["heartRequestID"] as? String)
        let anyRequestID = try #require(report["anyRequestID"] as? String)
        let heartID = try #require(UUID(uuidString: heartRequestID))
        let anyID = try #require(UUID(uuidString: anyRequestID))
        let text = try #require(report["heartReturnedText"] as? String)
        let foreignText = try #require(report["foreignAnyText"] as? String)
        let anyText = try #require(report["anyReturnedText"] as? String)
        let store = try MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared")
        let storedRequest = try store.request(id: heartID)
        let request = try #require(storedRequest)
        try #require(request.source.appID == PinkhaMiniAppsContext.sourceAppID)
        try #require(request.source.metadata["pinkha.engine"] == "heart")
        try #require(request.source.metadata["anytype.accountID"] == account
            && request.source.metadata["anytype.spaceID"] == space && request.source.documentID == object)

        let clock = ContinuousClock(), deadline = clock.now.advanced(by: .seconds(60))
        while Container.shared.accountManager().account.id != account && clock.now < deadline {
            try await Task.sleep(for: .milliseconds(100))
        }
        try #require(Container.shared.accountManager().account.id == account)
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: space)
        let view = try await Container.shared.objectLifecycleService().openForPreview(
            contextId: object, spaceId: space)
        try #require(view.rootID == object)
        let original = view.blocks.filter { $0.text.text == fixture["originalText"] }
        let warm = view.blocks.filter { $0.text.text == fixture["returnedText"] }
        let cold = view.blocks.filter { $0.text.text == fixture["coldReturnedText"] }
        let switched = view.blocks.filter { $0.text.text == text }
        try #require(original.count == 1 && original[0].id == fixture["blockID"])
        try #require(warm.count == 1 && cold.count == 1 && switched.count == 1)
        try #require(Set([original[0].id, warm[0].id, cold[0].id, switched[0].id]).count == 4)
        try #require(switched[0].fields.fields[PinkhaMiniAppsResultApplier.receiptField]?.stringValue
            == heartID.uuidString.lowercased() + ":0")
        try #require(view.blocks.allSatisfy { $0.text.text != foreignText && $0.text.text != anyText })
        let pending = try store.pendingResults(sourceAppID: PinkhaMiniAppsContext.sourceAppID)
        try #require(pending.allSatisfy { $0.requestID != heartID && $0.requestID != anyID })
        let proof: [String: Any] = [
            "status": "REAL_ENGINE_ACCOUNT_MINIAPPS_HEART_NATIVE_PASS",
            "sourceSHA": try #require(fixture["sourceSHA"]), "runID": try #require(fixture["runID"]),
            "uiReportSHA256": SHA256.hash(data: raw).map { String(format: "%02x", $0) }.joined(),
            "heartRequestID": heartID.uuidString.lowercased(), "anyRequestID": anyID.uuidString.lowercased(),
            "accountID": account, "spaceID": space, "objectID": object,
            "originalBlockID": original[0].id, "returnedBlockID": switched[0].id,
            "originalCount": original.count, "returnedCount": switched.count,
            "foreignContentAbsent": true, "nativeReadOnly": true
        ]
        let destination = try fixtureURL().deletingLastPathComponent()
            .appendingPathComponent("miniapps-engine-account-native-readback.json")
        try #require(!FileManager.default.fileExists(atPath: destination.path))
        try JSONSerialization.data(withJSONObject: proof, options: [.sortedKeys])
            .write(to: destination, options: .withoutOverwriting)
        print("MINIAPPS_ENGINE_ACCOUNT_NATIVE_READBACK_PASS")
    }

    private func fixtureURL() throws -> URL {
        try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
            appropriateFor: nil, create: true).appendingPathComponent("miniapps-native-fixture.json")
    }
}
#endif

#if DEBUG && targetEnvironment(simulator)
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyHost
@testable import PinkhaAnyUI

final class AnyMiniAppsResultValidationTests: XCTestCase {
    private func metadata(text: String, style: AnyJSON = .object([:])) throws -> AnyMiniAppsBlockMetadata {
        let value: AnyJSON = .object([
            "type": .string("paragraph"), "inlineMarkdown": .string(text), "style": style
        ])
        return try JSONDecoder().decode(AnyMiniAppsBlockMetadata.self, from: JSONEncoder().encode(value))
    }

    func testNativeMetadataRequiresExactInlineAndNestedStyleBytes() throws {
        let pairs = [("\u{00E9}", "e\u{0301}"),
                     ("\u{05E9}\u{05B8}\u{05C1}", "\u{05E9}\u{05C1}\u{05B8}")]
        for (stored, equivalent) in pairs {
            XCTAssertEqual(stored, equivalent)
            XCTAssertNotEqual(Data(stored.utf8), Data(equivalent.utf8))
            let style: AnyJSON = .object(["marks": .array([
                .object([stored: .string(stored)]), .bool(true), .integer(2), .null
            ])])
            let before = try metadata(text: "old", style: style)
            let snapshot = try before.snapshot(id: "block-original")
            let mutation = Anytype.PinkhaMiniAppsEditPlan.Mutation(before: snapshot,
                location: 0, length: 3, replacement: stored)
            let expected = try before.replacing(mutation)
            let exact = try metadata(text: stored, style: style)
            XCTAssertTrue(exact.matchesExactly(expected))
            XCTAssertFalse(try metadata(text: equivalent, style: style).matchesExactly(expected))
            let changedValue: AnyJSON = .object(["marks": .array([
                .object([stored: .string(equivalent)]), .bool(true), .integer(2), .null
            ])])
            XCTAssertFalse(try metadata(text: stored, style: changedValue).matchesExactly(expected))
            let changedKey: AnyJSON = .object(["marks": .array([
                .object([equivalent: .string(stored)]), .bool(true), .integer(2), .null
            ])])
            XCTAssertFalse(try metadata(text: stored, style: changedKey).matchesExactly(expected))
            let roundTrip = try JSONDecoder().decode(AnyMiniAppsBlockMetadata.self,
                from: AnyMiniAppsCodec.encode(exact))
            XCTAssertTrue(roundTrip.matchesExactly(expected))
        }
    }

    func testPreparedFileReadbackRequiresExactNameAndIdentityBytes() throws {
        let pairs = [("\u{00E9}", "e\u{0301}"),
                     ("\u{05E9}\u{05B8}\u{05C1}", "\u{05E9}\u{05C1}\u{05B8}")]
        for (stored, equivalent) in pairs {
            let fileID = "file-" + stored, objectID = "object-" + stored, name = stored + ".txt"
            let original: [String: AnyJSON] = [
                "fileId": .string(fileID), "objectId": .string(objectID),
                "size": .integer(4), "name": .string(name), "mime": .string("text/plain")
            ]
            XCTAssertNoThrow(try AnyMiniAppsResultApplier.validatePreparedFileMetadata(.object(original),
                fileID: fileID, objectID: objectID, size: 4, name: name, mime: "text/plain"))
            for (key, altered) in [("name", equivalent + ".txt"),
                                   ("fileId", "file-" + equivalent),
                                   ("objectId", "object-" + equivalent)] {
                var readback = original
                readback[key] = .string(altered)
                XCTAssertThrowsError(try AnyMiniAppsResultApplier.validatePreparedFileMetadata(.object(readback),
                    fileID: fileID, objectID: objectID, size: 4, name: name, mime: "text/plain")) { error in
                    guard let hostError = error as? AnyHostError, case .writeUncertain = hostError else {
                        return XCTFail("The known prepared write must remain uncertain: \(error)")
                    }
                }
            }
        }
    }

    func testPreparedFileReadbackPreservesRequiredTypesSizeAndMIME() throws {
        let original: [String: AnyJSON] = [
            "fileId": .string("file-original"), "objectId": .string("object-original"),
            "size": .integer(4), "name": .string("result.txt"), "mime": .string("text/plain")
        ]
        func validate(_ fields: [String: AnyJSON]) throws {
            try AnyMiniAppsResultApplier.validatePreparedFileMetadata(.object(fields),
                fileID: "file-original", objectID: "object-original", size: 4,
                name: "result.txt", mime: "text/plain")
        }
        XCTAssertNoThrow(try validate(original))
        for key in ["fileId", "objectId", "size", "name", "mime"] {
            var absent = original
            absent.removeValue(forKey: key)
            XCTAssertThrowsError(try validate(absent))
            var wrongType = original
            wrongType[key] = .null
            XCTAssertThrowsError(try validate(wrongType))
        }
        var changedSize = original
        changedSize["size"] = .integer(5)
        XCTAssertThrowsError(try validate(changedSize))
        var changedMIME = original
        changedMIME["mime"] = .string("application/octet-stream")
        XCTAssertThrowsError(try validate(changedMIME))
    }
}
#endif

#if DEBUG && targetEnvironment(simulator)
@MainActor
final class PinkhaMiniAppsHeartDispatchTests: XCTestCase {
    private enum ProbeFailure: Error { case lostReply }

    private func request(id: UUID = UUID(), account: String = "account-original",
                         space: String = "space-original", document: String = "document-original",
                         engine: String = "heart") throws -> MiniAppInvocation {
        let block = Anytype.PinkhaMiniAppsBlockSnapshot(id: "block-original", text: "old", marks: Data())
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return .init(id: id, appID: "miniapps-component", source: .init(
            appID: "io.anytype.app.dev", displayName: "Synthetic component", documentID: document,
            documentText: block.text, metadata: [
                "pinkha.engine": engine, "anytype.accountID": account, "anytype.spaceID": space,
                "anytype.blocks": String(decoding: try encoder.encode([block]), as: UTF8.self)
            ]), createdAt: Date(timeIntervalSince1970: 1_700_000_000))
    }

    private func result(_ request: MiniAppInvocation, operation: MiniAppOperation = .replaceDocument,
                        text: String = "\u{00E9}") -> MiniAppResult {
        .init(requestID: request.id, operation: operation, items: [.init(kind: .text, text: text)])
    }

    private func supportDirectory() throws -> URL {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("miniapps-dispatch-component-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                               attributes: [.posixPermissions: 0o700])
        return directory
    }

    func testLostTextReplyRemainsFencedAfterOriginalJournalReopen() async throws {
        let support = try supportDirectory()
        defer { try? FileManager.default.removeItem(at: support) }
        let invocation = try request(), returned = result(invocation)
        let journal = try PinkhaMiniAppsJournal(request: invocation, testingSupportDirectory: support)
        var plan = try PinkhaMiniAppsResultApplier.resumePlan(request: invocation, result: returned, journal: journal)
        let mutation = try XCTUnwrap(plan.mutations.first)
        var writes = 0
        var observedBody = mutation.before
        do {
            try await PinkhaMiniAppsResultApplier.dispatch(.mutation, key: mutation.before.id,
                plan: &plan, journal: journal, validate: {}, operation: { () async throws -> Void in
                    writes += 1
                    observedBody = .init(id: mutation.before.id, text: try XCTUnwrap(mutation.afterText), marks: Data())
                    throw ProbeFailure.lostReply
                })
            XCTFail("The original post-dispatch failure must escape")
        } catch ProbeFailure.lostReply { }
        XCTAssertEqual(writes, 1)

        let reopenedJournal = try PinkhaMiniAppsJournal(request: invocation, testingSupportDirectory: support)
        var reopened = try PinkhaMiniAppsResultApplier.resumePlan(
            request: invocation, result: returned, journal: reopenedJournal)
        XCTAssertEqual(reopened.requestID, invocation.id)
        XCTAssertFalse(reopened.completed)
        XCTAssertTrue(reopened.appliedBlocks.isEmpty)
        XCTAssertThrowsError(try PinkhaMiniAppsResultApplier.replayDecision(mutation: mutation,
            current: mutation.before, plan: reopened, expectedMarks: Data()))
        let equivalent = Anytype.PinkhaMiniAppsBlockSnapshot(id: mutation.before.id,
            text: "e\u{0301}", marks: Data())
        XCTAssertThrowsError(try PinkhaMiniAppsResultApplier.replayDecision(mutation: mutation,
            current: equivalent, plan: reopened, expectedMarks: Data()))
        XCTAssertThrowsError(try PinkhaMiniAppsResultApplier.preserveResult(returned, in: &reopened))
        XCTAssertTrue(reopened.additions.isEmpty)
        do {
            try await PinkhaMiniAppsResultApplier.dispatch(.mutation, key: mutation.before.id,
                plan: &reopened, journal: reopenedJournal, validate: {}, operation: { writes += 1 })
            XCTFail("An uncertain original mutation must not be sent again")
        } catch PinkhaMiniAppsError.resultNotSaved { }
        XCTAssertEqual(writes, 1)

        XCTAssertEqual(try PinkhaMiniAppsResultApplier.replayDecision(mutation: mutation,
            current: observedBody, plan: reopened, expectedMarks: Data()), .alreadyApplied)
        XCTAssertEqual(writes, 1)
    }

    func testLostFallbackInsertionAndUploadRepliesCannotRepeat() async throws {
        for kind in [PinkhaMiniAppsResultApplier.DispatchKind.insertion, .upload] {
            let support = try supportDirectory()
            defer { try? FileManager.default.removeItem(at: support) }
            let invocation = try request()
            let returned: MiniAppResult
            switch kind {
            case .insertion: returned = result(invocation)
            case .upload:
                returned = .init(requestID: invocation.id, operation: .insert,
                    items: [.init(kind: .file, attachmentID: UUID(), typeIdentifier: "public.data", name: "result.bin")])
            case .mutation: return XCTFail("This control covers append and upload uncertainty")
            }
            let journal = try PinkhaMiniAppsJournal(request: invocation, testingSupportDirectory: support)
            var plan = try PinkhaMiniAppsResultApplier.resumePlan(request: invocation, result: returned, journal: journal)
            let key = invocation.id.uuidString.lowercased() + ":0"
            switch kind {
            case .insertion:
                let mutation = try XCTUnwrap(plan.mutations.first)
                let newer = Anytype.PinkhaMiniAppsBlockSnapshot(id: mutation.before.id,
                    text: "a later user edit", marks: Data())
                XCTAssertEqual(try PinkhaMiniAppsResultApplier.replayDecision(mutation: mutation,
                    current: newer, plan: plan, expectedMarks: Data()), .preserveNewerContent)
                try PinkhaMiniAppsResultApplier.preserveResult(returned, in: &plan)
                XCTAssertTrue(plan.mutations.isEmpty)
                XCTAssertEqual(plan.additions.count, 1)
            case .upload:
                let inserted = try await PinkhaMiniAppsResultApplier.dispatch(.insertion, key: key,
                    plan: &plan, journal: journal, validate: {}, operation: { "original-file-block" })
                XCTAssertEqual(inserted, "original-file-block")
            case .mutation: return XCTFail("This control covers append and upload uncertainty")
            }
            var effects = 0
            do {
                try await PinkhaMiniAppsResultApplier.dispatch(kind, key: key, plan: &plan,
                    journal: journal, validate: {}, operation: { () async throws -> Void in
                        effects += 1
                        throw ProbeFailure.lostReply
                    })
                XCTFail("The original unknown effect must stay failed")
            } catch ProbeFailure.lostReply { }
            let reopenedJournal = try PinkhaMiniAppsJournal(request: invocation, testingSupportDirectory: support)
            var reopened = try PinkhaMiniAppsResultApplier.resumePlan(
                request: invocation, result: returned, journal: reopenedJournal)
            XCTAssertFalse(reopened.completed)
            XCTAssertTrue(reopened.insertedBlocks.isEmpty)
            do {
                try await PinkhaMiniAppsResultApplier.dispatch(kind, key: key, plan: &reopened,
                    journal: reopenedJournal, validate: {}, operation: { effects += 1 })
                XCTFail("The second native call must remain forbidden")
            } catch PinkhaMiniAppsError.resultNotSaved { }
            XCTAssertEqual(effects, 1)
            let preserved = reopened.preservedNewerContent
            let additionCount = reopened.additions.count
            XCTAssertThrowsError(try PinkhaMiniAppsResultApplier.preserveResult(returned, in: &reopened))
            XCTAssertEqual(reopened.preservedNewerContent, preserved)
            XCTAssertEqual(reopened.additions.count, additionCount)
        }
    }

    func testLegacyUnfinishedAndDifferentOwnerRecordsCannotAuthorizeEffects() throws {
        let support = try supportDirectory()
        defer { try? FileManager.default.removeItem(at: support) }
        let invocation = try request(), returned = result(invocation)
        let journal = try PinkhaMiniAppsJournal(request: invocation, testingSupportDirectory: support)
        XCTAssertNil(try journal.load())
        try Data([0xFF]).write(to: journal.url, options: .atomic)
        XCTAssertThrowsError(try PinkhaMiniAppsResultApplier.resumePlan(request: invocation,
            result: returned, journal: journal)) { error in
                XCTAssertTrue(error is DecodingError)
            }
        var legacy = try PinkhaMiniAppsEditPlanner.make(request: invocation, result: returned)
        let originalShape = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(legacy)) as? [String: Any])
        XCTAssertNil(originalShape["heartDispatch"])
        try journal.save(legacy)
        XCTAssertThrowsError(try PinkhaMiniAppsResultApplier.resumePlan(request: invocation, result: returned, journal: journal))
        legacy.completed = true
        try journal.save(legacy)
        XCTAssertTrue(try PinkhaMiniAppsResultApplier.resumePlan(
            request: invocation, result: returned, journal: journal).completed)

        let fresh = try request()
        let freshResult = result(fresh)
        let freshJournal = try PinkhaMiniAppsJournal(request: fresh, testingSupportDirectory: support)
        let bound = try PinkhaMiniAppsResultApplier.resumePlan(request: fresh, result: freshResult, journal: freshJournal)
        try freshJournal.save(bound)
        let changedOwners = [
            try request(id: fresh.id, account: "account-replacement"),
            try request(id: fresh.id, space: "space-replacement"),
            try request(id: fresh.id, document: "document-replacement"),
            try request(id: fresh.id, engine: "any")
        ]
        for replacement in changedOwners {
            let replacementJournal = try PinkhaMiniAppsJournal(request: replacement, testingSupportDirectory: support)
            try replacementJournal.save(bound)
            XCTAssertThrowsError(try PinkhaMiniAppsResultApplier.resumePlan(
                request: replacement, result: freshResult, journal: replacementJournal))
        }
        XCTAssertThrowsError(try PinkhaMiniAppsResultApplier.resumePlan(request: fresh,
            result: result(fresh, text: "e\u{0301}"), journal: freshJournal))
    }

    func testCancellationAfterDurableFencePreventsTheOriginalEffect() async throws {
        let support = try supportDirectory()
        defer { try? FileManager.default.removeItem(at: support) }
        let invocation = try request(), returned = result(invocation)
        let journal = try PinkhaMiniAppsJournal(request: invocation, testingSupportDirectory: support)
        var plan = try PinkhaMiniAppsResultApplier.resumePlan(request: invocation, result: returned, journal: journal)
        let mutation = try XCTUnwrap(plan.mutations.first)
        var validations = 0, effects = 0
        do {
            try await PinkhaMiniAppsResultApplier.dispatch(.mutation, key: mutation.before.id,
                plan: &plan, journal: journal, validate: {
                    validations += 1
                    if validations == 2 { throw CancellationError() }
                }, operation: { effects += 1 })
            XCTFail("The original authority cancellation must escape before native work")
        } catch is CancellationError { }
        XCTAssertEqual(validations, 2)
        XCTAssertEqual(effects, 0)
        let reopenedJournal = try PinkhaMiniAppsJournal(request: invocation, testingSupportDirectory: support)
        let reopened = try PinkhaMiniAppsResultApplier.resumePlan(
            request: invocation, result: returned, journal: reopenedJournal)
        XCTAssertFalse(reopened.completed)
        XCTAssertThrowsError(try PinkhaMiniAppsResultApplier.replayDecision(mutation: mutation,
            current: mutation.before, plan: reopened, expectedMarks: Data()))
    }
}
#endif
