#if DEBUG && targetEnvironment(simulator) && PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
import CryptoKit
import XCTest
import SwiftProtobuf
import AnytypeCore
import PinkhaKit
import ProtobufMessages
import Services
@testable import Anytype

/// One full-App consumer of the separately built production Page154 framework.
/// The original native Page2 methods are retained separately and are not run here.
final class SemanticAnchorPage154NativeAcceptanceTests: XCTestCase {
    private enum Failure: Error { case invariant(String) }
    private let expectedVersion = "pinkha-semantic-anchor-native-page-candidate-v1-2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"

    @MainActor
    func testActualPage154FactoryPublishesNativeAnchorIntoOpenedDocument() async throws {
        let env = ProcessInfo.processInfo.environment
        try require(env["PINKHA_SEMANTIC_PAGE154_APPLE_CONSUMER"] == "1", "explicit-candidate-required")
        let binding = try readBinding(env)
        try require(Container.shared.accountManager().account.id.isEmpty, "fresh-owned-simulator-required")
        try require(Bundle.main.object(forInfoDictionaryKey: "CompilationCondition") as? String == "DEBUG",
                    "debug-app-host-required")
        try require(TargetsConstants.appGroup == "group.io.anytype.app.dev", "owned-debug-app-group-required")
        let shared = try XCTUnwrap(FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: TargetsConstants.appGroup))
        try require(try shared.resourceValues(forKeys: [.isDirectoryKey]).isDirectory == true, "app-group-unavailable")
        FeatureFlags.update(key: .logMiddlewareRequests, value: false)
        let handler = try XCTUnwrap(InvocationSettings.handler as? InvocationMesagesHandler)
        handler.enableLogger = false
        try require(InvocationSettings.handler?.isLogEnabled == false, "middleware-logging-must-be-disabled")
        let version = try await ClientCommands.appGetVersion().invoke().version
        try require(Data(version.utf8) == Data(expectedVersion.utf8), "actual-page154-runtime-required")

        var document: (any BaseDocumentProtocol)?
        var accountCreated = false
        var accountStopped = false
        var appStopped = false
        var diagnostic: [String: Any] = [
            "protocol": "pinkha-semantic-page154-apple-consumer-v1",
            "status": "IN_PROGRESS", "binding": binding, "phase": "ACCOUNT"
        ]
        do {
            Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)
            let auth = Container.shared.authService()
            let mnemonic = try await auth.createWallet()
            try require(!mnemonic.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, "empty-native-wallet")
            try Container.shared.seedService().saveSeed(mnemonic)
            let saved = try Container.shared.seedService().obtainSeed()
            try require(Data(saved.utf8) == Data(mnemonic.trimmingCharacters(in: .whitespacesAndNewlines).utf8),
                        "private-seed-readback-differs")
            let account = try await auth.createAccount(name: "Page154 disposable", iconOption: 1, imagePath: "")
            accountCreated = true
            try require(!account.id.isEmpty, "native-account-missing")
            let space = try await Container.shared.workspaceService().createSpace(
                name: "Page154 disposable Space", iconOption: 1, accessType: .private,
                useCase: .none, withChat: false, spaceType: .regular)
            let spaceID = space.spaceID
            try require(!spaceID.isEmpty, "native-space-missing")
            _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceID)
            // This ordinary native response is the owner/Space lease boundary.
            _ = try await ClientCommands.workspaceOpen(.with { $0.spaceID = spaceID }).invoke()
            let lease = try PinkhaNativeReadLifetime.shared.lease(forOpenedSpaceID: spaceID)
            try require(lease.accountID == account.id && lease.spaceID == spaceID, "actual-owner-lease-differs")
            try lease.validate()

            let page = try await Container.shared.objectActionsService().createObject(
                name: "Page154 " + binding["nonce"]!, typeUniqueKey: .page,
                shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                spaceId: spaceID, origin: .none, templateId: nil)
            try require(!page.id.isEmpty, "native-page-missing")
            let opened = Container.shared.openedDocumentProvider().document(objectId: page.id, spaceId: spaceID)
            document = opened
            try await opened.open()
            try require(opened.isOpened && opened.objectId == page.id && opened.spaceId == spaceID,
                        "actual-open-document-identity-differs")
            diagnostic["phase"] = "NATIVE_BLOCK"

            let text = "\u{05DC}\u{05E4}\u{05E0}\u{05D9} e\u{0301} \u{1F469}\u{1F3FD}\u{200D}\u{1F4BB} \u{05E1}\u{05D5}\u{05E3}"
            let selected = "e\u{0301} \u{1F469}\u{1F3FD}\u{200D}\u{1F4BB}"
            let range = (text as NSString).range(of: selected)
            try require(range == NSRange(location: 5, length: 10), "deterministic-unicode-range-differs")
            let existing = Anytype_Model_Block.Content.Text.Mark.with {
                $0.type = .bold; $0.range = .with { $0.from = 0; $0.to = 4 }
            }
            let block = Anytype_Model_Block.with {
                // Page154's native proof has this explicit scope; nil identity is not claimed.
                $0.restrictions = .init()
                $0.text = .with {
                    $0.text = text; $0.style = .paragraph
                    $0.marks = .with { $0.marks = [existing] }
                }
            }
            let created = try await ClientCommands.blockCreate(.with {
                $0.contextID = page.id; $0.targetID = "header"; $0.position = .bottom; $0.block = block
            }).invoke()
            let blockID = created.blockID
            try require(!blockID.isEmpty, "native-block-missing")
            let before = try await nativeBlock(spaceID: spaceID, objectID: page.id, blockID: blockID)
            try require(before.hasRestrictions && before.restrictions == .init(), "explicit-empty-restrictions-required")
            try require(Data(before.text.text.utf8) == Data(text.utf8), "native-before-text-bytes-differ")
            try require(try bytes(before.text.marks) == bytes(block.text.marks), "native-existing-marks-differ")
            let beforeDocument = try documentText(opened, blockID)
            try require(Data(beforeDocument.text.utf8) == Data(text.utf8)
                        && (try bytes(beforeDocument.marks)) == bytes(before.text.marks),
                        "ordinary-block-create-event-not-applied")

            let anchor = try PinkhaSemanticTextAnchor(spaceID: spaceID, objectID: page.id)
            let plan = try PinkhaHeartSemanticAnchorPlan(spaceID: spaceID, objectID: page.id,
                anchorID: anchor.id.uuidString.lowercased(), range: range, nativeBlock: before)
            let service = AnytypeHeartSemanticAnchorService()
            let pending = try service.prepare(anchor: anchor, nativeBlock: before, selection: range)
            diagnostic["phase"] = "ACTUAL_FACTORY_APPLY"
            // Exactly one public Apply. This test never invokes a fixture or injectable IO.
            let capture = try await service.apply(pending)
            try lease.validate()
            try require(capture.generation == lease.generation, "verified-owner-generation-differs")
            let result = capture.receipt
            try require(result.spaceID == spaceID && result.objectID == page.id
                        && result.blockID == blockID && result.anchorID == anchor.id.uuidString.lowercased(),
                        "actual-native-receipt-identity-differs")
            try require(Data(result.marker.utf8) == Data(anchor.markerString.utf8), "actual-canonical-marker-differs")

            // Observe the existing BaseDocument state before this test's independent readback.
            // No alternate event handler, synthetic event, reducer, or document refresh is used.
            let published = try documentText(opened, blockID)
            let after = try await nativeBlock(spaceID: spaceID, objectID: page.id, blockID: blockID)
            let beforeSnapshot = try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: before)
            let afterSnapshot = try PinkhaHeartSemanticAnchorSnapshot(nativeBlock: after)
            let planned = try plan.request.plannedSnapshot()
            try require(afterSnapshot.hasSameMarks(as: planned), "native-after-marks-differ")
            try require(beforeSnapshot.digest == result.beforeTextMarksSHA256
                        && afterSnapshot.digest == result.afterTextMarksSHA256,
                        "actual-native-receipt-digests-differ")
            try require(Data(published.text.utf8) == Data(text.utf8)
                        && (try bytes(published.marks)) == bytes(after.text.marks),
                        "ordinary-native-event-not-applied-to-opened-document")
            var restored = after
            restored.text.marks = before.text.marks
            try require(try bytes(restored) == bytes(before), "native-non-mark-block-bytes-changed")
            let currentHandler = try XCTUnwrap(InvocationSettings.handler as? InvocationMesagesHandler)
            try require(currentHandler === handler, "ordinary-handler-replaced")

            diagnostic = [
                "protocol": "pinkha-semantic-page154-apple-consumer-v1",
                "status": "PASS_ACTUAL_APP_FACTORY_EVENT_AND_READBACK",
                "binding": binding,
                "runtime": ["version": version, "manifestSHA256": PinkhaHeartSemanticAnchorProfile.sourceManifestSHA256,
                            "producerRunID": "45098093058", "processID": Int(ProcessInfo.processInfo.processIdentifier)],
                "identity": ["accountID": account.id, "spaceID": spaceID, "objectID": page.id,
                             "blockID": blockID, "anchorID": anchor.id.uuidString.lowercased(),
                             "ownerGeneration": lease.generation.uuidString.lowercased()],
                "selection": ["location": range.location, "length": range.length,
                              "textUTF8Base64": Data(text.utf8).base64EncodedString(),
                              "selectedUTF8Base64": Data(selected.utf8).base64EncodedString()],
                "native": ["beforeBlockBase64": try bytes(before).base64EncodedString(),
                           "afterBlockBase64": try bytes(after).base64EncodedString(),
                           "receipt": receiptJSON(result)],
                "document": ["spaceID": opened.spaceId, "objectID": opened.objectId,
                             "beforeTextUTF8Base64": Data(beforeDocument.text.utf8).base64EncodedString(),
                             "afterTextUTF8Base64": Data(published.text.utf8).base64EncodedString(),
                             "beforeMarksBase64": try bytes(beforeDocument.marks).base64EncodedString(),
                             "afterMarksBase64": try bytes(published.marks).base64EncodedString()],
                "publication": ["handler": "InvocationMesagesHandler", "serviceApplyCalls": 1,
                                "ownerGeneration": capture.generation.uuidString.lowercased(),
                                "documentObservedBeforeIndependentReadback": true],
                "limits": ["mountedEditorAcceptance": "NOT_RUN", "AppleColdReopen": "NOT_RUN",
                           "independentStoredNativeChangeBytes": "NOT_EXPORTED",
                           "physicalDevice": "NOT_RUN", "fullProductAcceptance": false]
            ]
            try await opened.close()
            try require(!opened.isOpened, "ordinary-document-close-incomplete")
            document = nil
            _ = try await ClientCommands.accountStop(.with { $0.removeData = false }).invoke()
            accountStopped = true
            do {
                try lease.validate()
                throw Failure.invariant("owner-lease-not-retired-after-account-stop")
            } catch PinkhaNativeReadLifetimeError.retired { }
            do {
                _ = try await ClientCommands.accountPreloadRemainingSpaces().invoke(ignoreLogErrors: .accountIsNotRunning)
                throw Failure.invariant("native-account-still-running")
            } catch let error as Anytype_Rpc.Account.PreloadRemainingSpaces.Response.Error
                        where error.code == .accountIsNotRunning { }
            _ = try await ClientCommands.appShutdown().invoke()
            appStopped = true
            diagnostic["cleanup"] = ["documentClosed": true, "accountStopped": true,
                                     "accountNotRunning": true, "leaseRetired": true, "appShutdown": true]
            try attach(diagnostic)
        } catch {
            if let document { try? await document.close() }
            if accountCreated && !accountStopped {
                _ = try? await ClientCommands.accountStop(.with { $0.removeData = false }).invoke()
            }
            if !appStopped { _ = try? await ClientCommands.appShutdown().invoke() }
            diagnostic["status"] = "FAIL_ACTUAL_APP_CONSUMER"
            diagnostic["errorType"] = String(reflecting: type(of: error))
            try? attach(diagnostic)
            throw error
        }
    }

    @MainActor
    private func nativeBlock(spaceID: String, objectID: String, blockID: String) async throws -> Anytype_Model_Block {
        let response = try await ClientCommands.objectShow(.with {
            $0.spaceID = spaceID; $0.objectID = objectID; $0.contextID = objectID
        }).invoke()
        try require(response.objectView.rootID == objectID, "actual-object-show-root-differs")
        let blocks = response.objectView.blocks.filter { $0.id == blockID }
        try require(blocks.count == 1, "actual-object-show-block-identity-differs")
        return blocks[0]
    }

    private func documentText(_ document: any BaseDocumentProtocol, _ blockID: String) throws -> BlockText {
        guard let value = document.infoContainer.get(id: blockID), case .text(let text) = value.content else {
            throw Failure.invariant("opened-document-native-text-missing")
        }
        return text
    }

    private func bytes<T: SwiftProtobuf.Message>(_ value: T) throws -> Data {
        var options = BinaryEncodingOptions(); options.useDeterministicOrdering = true
        return try value.serializedData(options: options)
    }

    private func require(_ value: Bool, _ label: String) throws {
        if !value { throw Failure.invariant(label) }
    }

    private func readBinding(_ env: [String: String]) throws -> [String: String] {
        var result: [String: String] = [:]
        for (key, suffix, pattern) in [
            ("sourceSHA", "SOURCE_SHA", "^[0-9a-f]{40}$"), ("runID", "RUN_ID", "^[1-9][0-9]*$"),
            ("runAttempt", "RUN_ATTEMPT", "^[1-9][0-9]*$"), ("nonce", "NONCE", "^[0-9a-f]{32}$")
        ] {
            let value = env["PINKHA_SEMANTIC_PAGE154_" + suffix] ?? ""
            try require(value.range(of: pattern, options: .regularExpression) != nil, "invalid-binding-" + key)
            result[key] = value
        }
        return result
    }

    private func receiptJSON(_ value: PinkhaHeartSemanticAnchorReceipt) -> [String: Any] {
        ["version": value.version, "spaceID": value.spaceID, "objectID": value.objectID,
         "blockID": value.blockID, "anchorID": value.anchorID, "marker": value.marker,
         "changeID": value.changeID, "nativeChangeSHA256": value.nativeChangeSHA256,
         "beforeTextMarksSHA256": value.beforeTextMarksSHA256,
         "afterTextMarksSHA256": value.afterTextMarksSHA256]
    }

    private func attach(_ value: [String: Any]) throws {
        let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        try require(data.count <= 65_536, "observation-exceeds-bound")
        let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
        attachment.name = "pinkha-semantic-page154-native-observation"
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
#endif
