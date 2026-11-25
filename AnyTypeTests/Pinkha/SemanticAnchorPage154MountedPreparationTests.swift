#if DEBUG && targetEnvironment(simulator) && PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
import XCTest
import AnytypeCore
import ProtobufMessages
import Services
import PinkhaKit
@testable import Anytype

/// New fixture preparation, independent of the boundary XCTest and its account.
final class SemanticAnchorPage154MountedPreparationTests: XCTestCase {
    @MainActor
    func testPrepareOwnedPage154MountedFixture() async throws {
        typealias Fixture = PinkhaSemanticAnchorMountedFixture
        let env = ProcessInfo.processInfo.environment
        try Fixture.require(env["PINKHA_SEMANTIC_MOUNTED_PREPARE"] == "1"
            && env["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1", "explicit-owned-preparation-required")
        let binding = try Fixture.binding(env)
        try Fixture.require(Container.shared.accountManager().account.id.isEmpty, "fresh-simulator-required")
        try Fixture.require(Bundle.main.object(forInfoDictionaryKey: "CompilationCondition") as? String == "DEBUG"
            && TargetsConstants.appGroup == "group.io.anytype.app.dev", "debug-app-group-required")
        let group = try XCTUnwrap(FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: TargetsConstants.appGroup))
        try Fixture.require(try group.resourceValues(forKeys: [.isDirectoryKey]).isDirectory == true, "app-group-unavailable")
        for name in [Fixture.fileName, Fixture.captureFileName, Fixture.reopenFileName] {
            try Fixture.require(!FileManager.default.fileExists(atPath: try Fixture.fileURL(name).path),
                "existing-fixture-or-result")
        }
        FeatureFlags.update(key: .logMiddlewareRequests, value: false)
        let handler = try XCTUnwrap(InvocationSettings.handler as? InvocationMesagesHandler)
        handler.enableLogger = false
        try Fixture.require(InvocationSettings.handler?.isLogEnabled == false, "middleware-logging-enabled")
        let version = try await ClientCommands.appGetVersion().invoke().version
        try Fixture.require(version == PinkhaHeartSemanticAnchorProfile.runtimeVersion, "actual-page154-runtime-required")
        var ownedDocument: (any BaseDocumentProtocol)?
        var accountCreated = false
        var accountStopped = false
        var appStopped = false
        do {
            Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)
            let auth = Container.shared.authService()
            let mnemonic = try await auth.createWallet()
            try Fixture.require(!mnemonic.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, "empty-wallet")
            try Container.shared.seedService().saveSeed(mnemonic)
            let saved = try Container.shared.seedService().obtainSeed()
            try Fixture.require(Data(saved.utf8) == Data(mnemonic.trimmingCharacters(in: .whitespacesAndNewlines).utf8),
                "private-seed-readback-differs")
            let account = try await auth.createAccount(name: "Mounted anchor disposable", iconOption: 1, imagePath: "")
            accountCreated = true
            let space = try await Container.shared.workspaceService().createSpace(
                name: "Mounted anchor disposable Space", iconOption: 1, accessType: .private,
                useCase: .none, withChat: false, spaceType: .regular)
            try Fixture.require(!account.id.isEmpty && !space.spaceID.isEmpty, "native-account-space-missing")
            _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: space.spaceID)
            _ = try await ClientCommands.workspaceOpen(.with { $0.spaceID = space.spaceID }).invoke()
            let lease = try PinkhaNativeReadLifetime.shared.lease(forOpenedSpaceID: space.spaceID)
            try Fixture.require(lease.accountID == account.id, "native-owner-differs")
            let page = try await Container.shared.objectActionsService().createObject(
                name: "Mounted anchor " + binding["nonce"]!, typeUniqueKey: .page,
                shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                spaceId: space.spaceID, origin: .none, templateId: nil)
            let document = Container.shared.openedDocumentProvider().document(objectId: page.id, spaceId: space.spaceID)
            ownedDocument = document
            try await document.open()
            let text = "Anchor"
            let excludedText = "Unselected " + binding["nonce"]!
            let existing = Anytype_Model_Block.Content.Text.Mark.with {
                $0.type = .bold; $0.range = .with { $0.from = 0; $0.to = 3 }
            }
            let block = Anytype_Model_Block.with {
                // Match the qualified native Page154 explicit-empty restrictions scope.
                $0.restrictions = .init()
                $0.text = .with {
                    $0.text = text; $0.style = .paragraph; $0.marks = .with { $0.marks = [existing] }
                }
            }
            let created = try await ClientCommands.blockCreate(.with {
                $0.contextID = page.id; $0.targetID = "header"; $0.position = .bottom; $0.block = block
            }).invoke()
            let excluded = try await ClientCommands.blockCreate(.with {
                $0.contextID = page.id; $0.targetID = created.blockID; $0.position = .bottom
                $0.block = .with {
                    $0.restrictions = .init()
                    $0.text = .with { $0.text = excludedText; $0.style = .paragraph }
                }
            }).invoke()
            let shown = try await ClientCommands.objectShow(.with {
                $0.spaceID = space.spaceID; $0.objectID = page.id; $0.contextID = page.id
            }).invoke()
            try Fixture.require(shown.objectView.rootID == page.id, "native-root-differs")
            let before = try XCTUnwrap(shown.objectView.blocks.first { $0.id == created.blockID })
            let excludedBefore = try XCTUnwrap(shown.objectView.blocks.first { $0.id == excluded.blockID })
            let fixture = Fixture(sourceSHA: binding["sourceSHA"]!, runID: binding["runID"]!,
                runAttempt: binding["runAttempt"]!, nonce: binding["nonce"]!, createdAt: Date(),
                preparationProcessID: ProcessInfo.processInfo.processIdentifier,
                accountID: account.id, spaceID: space.spaceID, objectID: page.id,
                blockID: created.blockID, excludedBlockID: excluded.blockID, text: text, excludedText: excludedText,
                beforeBlockBase64: try Fixture.bytes(before).base64EncodedString(),
                excludedBlockBase64: try Fixture.bytes(excludedBefore).base64EncodedString())
            _ = try fixture.beforeBlock(); _ = try fixture.excludedBlock()
            try Fixture.require(before.text.marks == block.text.marks, "existing-marks-differ")
            try await document.close()
            ownedDocument = nil
            _ = try await ClientCommands.accountStop(.with { $0.removeData = false }).invoke()
            accountStopped = true
            _ = try await ClientCommands.appShutdown().invoke()
            appStopped = true
            let data = try JSONEncoder().encode(fixture)
            try Fixture.require(data.count <= 65_536, "fixture-too-large")
            try data.write(to: Fixture.fileURL(Fixture.fileName), options: .withoutOverwriting)
            let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
            attachment.name = "pinkha-semantic-page154-mounted-fixture"; attachment.lifetime = .keepAlways
            add(attachment)
        } catch {
            if let ownedDocument { try? await ownedDocument.close() }
            if accountCreated && !accountStopped {
                _ = try? await ClientCommands.accountStop(.with { $0.removeData = false }).invoke()
            }
            if !appStopped { _ = try? await ClientCommands.appShutdown().invoke() }
            throw error
        }
    }
}

// Independent native verification after the separate real UI continuation.
// No test creates an account/anchor/association or mutates document content.
extension SemanticAnchorPage154MountedPreparationTests {
    @MainActor
    func testReadBackExistingSemanticSourceAfterActualUIEditAndColdReopen() async throws {
        try await readBackSemanticSourceContinuation(phase: "linked")
    }

    @MainActor
    func testReadBackSemanticSourceAbsenceAfterActualUIUnlinkAndColdReopen() async throws {
        try await readBackSemanticSourceContinuation(phase: "unlinked")
    }

    @MainActor
    private func readBackSemanticSourceContinuation(phase: String) async throws {
        typealias Fixture = PinkhaSemanticAnchorMountedFixture
        let env = ProcessInfo.processInfo.environment
        try Fixture.require(env["PINKHA_SEMANTIC_SOURCE_READBACK_PHASE"] == phase
            && env["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1"
            && env["PINKHA_SEMANTIC_MOUNTED_UI"] != "1", "explicit-owned-source-readback-required")
        let binding = try Fixture.binding(env)
        let fixtureBytes = try Data(contentsOf: Fixture.fileURL(Fixture.fileName))
        try Fixture.require(fixtureBytes.count <= 65_536
            && Fixture.digest(fixtureBytes) == env["PINKHA_SEMANTIC_MOUNTED_FIXTURE_SHA256"], "original-fixture-hash-differs")
        let fixture = try JSONDecoder().decode(Fixture.self, from: fixtureBytes)
        try Fixture.require(fixture.sourceSHA == binding["sourceSHA"] && fixture.runID == binding["runID"]
            && fixture.runAttempt == binding["runAttempt"] && fixture.nonce == binding["nonce"], "source-readback-owner-differs")
        try Fixture.require(Date().timeIntervalSince(fixture.createdAt) >= 0
            && Date().timeIntervalSince(fixture.createdAt) < 7_200, "source-readback-fixture-expired")
        try Fixture.require(fixture.text == "Anchor" && fixture.excludedText == "Unselected " + fixture.nonce,
                            "source-readback-fixture-shape")
        _ = try fixture.beforeBlock(); _ = try fixture.excludedBlock()
        let captureBytes = try Data(contentsOf: Fixture.fileURL(Fixture.captureFileName))
        let reopenBytes = try Data(contentsOf: Fixture.fileURL(Fixture.reopenFileName))
        try Fixture.require(captureBytes.count <= 65_536 && reopenBytes.count <= 65_536
            && Fixture.digest(captureBytes) == env["PINKHA_SEMANTIC_SOURCE_CAPTURE_SHA256"]
            && Fixture.digest(reopenBytes) == env["PINKHA_SEMANTIC_SOURCE_REOPEN_SHA256"], "original-mounted-receipt-hash-differs")
        let captured = try XCTUnwrap(JSONSerialization.jsonObject(with: captureBytes) as? [String: Any])
        let reopened = try XCTUnwrap(JSONSerialization.jsonObject(with: reopenBytes) as? [String: Any])
        for (value, expected) in [(captured, "PASS_CAPTURE_MOUNTED"), (reopened, "PASS_COLD_REOPEN_MOUNTED")] {
            try Fixture.require(value["phase"] as? String == expected && value["sourceSHA"] as? String == fixture.sourceSHA
                && value["nonce"] as? String == fixture.nonce && value["accountID"] as? String == fixture.accountID
                && value["spaceID"] as? String == fixture.spaceID && value["objectID"] as? String == fixture.objectID
                && value["blockID"] as? String == fixture.blockID, "mounted-acceptance-owner-differs")
            let checks = try XCTUnwrap(value["checks"] as? [String: Bool])
            try Fixture.require(!checks.isEmpty && checks.values.allSatisfy { $0 }, "mounted-acceptance-not-passed")
        }
        let originalNative = try XCTUnwrap(captured["native"] as? [String: String])
        try Fixture.require(originalNative == reopened["native"] as? [String: String], "mounted-native-identity-changed")
        let marker = try XCTUnwrap(originalNative["marker"])
        let anchor = try PinkhaSemanticTextAnchor(markerURL: XCTUnwrap(URL(string: marker)))
        try Fixture.require(anchor.belongsTo(spaceID: fixture.spaceID, objectID: fixture.objectID), "anchor-owner-differs")
        let uiRaw = try XCTUnwrap(env["PINKHA_SEMANTIC_SOURCE_UI_RECEIPT_JSON"])
        let uiBytes = Data(uiRaw.utf8)
        try Fixture.require(uiBytes.count <= 65_536
            && Fixture.digest(uiBytes) == env["PINKHA_SEMANTIC_SOURCE_UI_RECEIPT_SHA256"], "actual-ui-receipt-hash-differs")
        let ui = try XCTUnwrap(JSONSerialization.jsonObject(with: uiBytes) as? [String: Any])
        try Fixture.require(ui["protocol"] as? String == "heart-semantic-source-ui-continuation-v1"
            && ui["status"] as? String == "PASS_UI" && ui["phase"] as? String == phase
            && ui["sourceSHA"] as? String == fixture.sourceSHA && ui["nonce"] as? String == fixture.nonce
            && ui["accountID"] as? String == fixture.accountID && ui["spaceID"] as? String == fixture.spaceID
            && ui["objectID"] as? String == fixture.objectID && ui["blockID"] as? String == fixture.blockID
            && ui["expectedText"] as? String == "Changed" && ui["reference"] as? String == "Genesis 1:1"
            && ui["markerSHA256"] as? String == Fixture.digest(Data(marker.utf8)), "actual-ui-receipt-owner-or-target-differs")
        let output = try Fixture.fileURL("pinkha-semantic-source-" + phase + "-native-readback.json")
        try Fixture.require(!FileManager.default.fileExists(atPath: output.path), "source-readback-already-exists")
        FeatureFlags.update(key: .logMiddlewareRequests, value: false)
        let handler = try XCTUnwrap(InvocationSettings.handler as? InvocationMesagesHandler)
        handler.enableLogger = false
        try Fixture.require(InvocationSettings.handler?.isLogEnabled == false, "middleware-logging-enabled")
        let version = try await ClientCommands.appGetVersion().invoke().version
        try Fixture.require(version == PinkhaHeartSemanticAnchorProfile.runtimeVersion, "exact-native-runtime-required")

        // The normal app startup must reopen this existing account. There is no
        // wallet/account creation, migration, replacement or permission fallback.
        let deadline = ProcessInfo.processInfo.systemUptime + 60
        var admitted: PinkhaNativeReadLease?
        while ProcessInfo.processInfo.systemUptime < deadline {
            let accountID = Container.shared.accountManager().account.id
            try Fixture.require(accountID.isEmpty || accountID == fixture.accountID, "unexpected-active-account")
            if accountID == fixture.accountID,
               let lease = try? PinkhaNativeReadLifetime.shared.lease(forOpenedSpaceID: fixture.spaceID) {
                admitted = lease; break
            }
            try await Task.sleep(for: .milliseconds(100))
        }
        let lease = try XCTUnwrap(admitted, "Normal startup must reopen the existing native account and Space")
        try lease.validate()
        try Fixture.require(lease.accountID == fixture.accountID, "native-account-owner-differs")
        let document = Container.shared.openedDocumentProvider().document(objectId: fixture.objectID, spaceId: fixture.spaceID)
        var opened = false, stopped = false, shutdown = false
        do {
            try await document.open(); opened = true
            let first = try await ClientCommands.objectShow(.with {
                $0.spaceID = fixture.spaceID; $0.objectID = fixture.objectID; $0.contextID = fixture.objectID
            }).invoke()
            try lease.validate()
            try Fixture.require(first.objectView.rootID == fixture.objectID, "native-root-differs")
            let target = try XCTUnwrap(first.objectView.blocks.first { $0.id == fixture.blockID })
            let excluded = try XCTUnwrap(first.objectView.blocks.first { $0.id == fixture.excludedBlockID })
            try Fixture.require(target.text.text == "Changed" &&
                Fixture.bytes(excluded) == Fixture.bytes(fixture.excludedBlock()), "native-edit-or-excluded-block-differs")
            let marks = target.text.marks.marks.filter { $0.type == .link && $0.param == marker }
            try Fixture.require(marks.count == 1 && marks[0].range.from == 0 && marks[0].range.to == 7,
                                "original-marker-does-not-cover-complete-edited-text")
            let resolution = try await AnytypeHeartSemanticAnchorService().resolve(anchor, lease: lease)
            guard case .resolved(let fragments) = resolution else {
                throw SemanticAnchorMountedError.invariant("current-native-anchor-does-not-resolve")
            }
            try Fixture.require(fragments.count == 1 && fragments[0].blockID == fixture.blockID
                && fragments[0].text == "Changed" && fragments[0].range == NSRange(location: 0, length: 7),
                "current-native-resolution-differs")
            let repository = AnytypeTorahAssociationRepository()
            let records = try await repository.listAssociationRecords(objectId: fixture.objectID, spaceId: fixture.spaceID)
            let codec = TorahAssociationPayloadCodec()
            let canonical = try codec.encodeCanonicalDocument(.init(records: records))
            let location = TorahAssociationLocation(spaceId: fixture.spaceID, target: .object(objectId: fixture.objectID))
            if phase == "linked" {
                try Fixture.require(records.count == 1 && records[0].location == location, "native-source-record-count-or-storage-differs")
                let item = records[0].item
                let semantic = try XCTUnwrap(TorahSemanticAnchorAssociation.decoding(item, location: records[0].location))
                try Fixture.require(semantic.anchor == anchor && item.kind == .ref && item.providerID == "sefaria"
                    && item.canonicalKey == "Genesis 1:1" && item.externalID == "Genesis 1:1"
                    && !item.id.isEmpty, "native-source-identity-or-reference-differs")
            } else {
                let linkedURL = try Fixture.fileURL("pinkha-semantic-source-linked-native-readback.json")
                let linkedBytes = try Data(contentsOf: linkedURL)
                try Fixture.require(Fixture.digest(linkedBytes) == env["PINKHA_SEMANTIC_SOURCE_LINKED_READBACK_SHA256"],
                                    "accepted-linked-readback-hash-differs")
                let linked = try XCTUnwrap(JSONSerialization.jsonObject(with: linkedBytes) as? [String: Any])
                try Fixture.require(linked["status"] as? String == "PASS_NATIVE_READBACK"
                    && linked["phase"] as? String == "linked" && linked["sourceSHA"] as? String == fixture.sourceSHA
                    && linked["nonce"] as? String == fixture.nonce
                    && linked["markerSHA256"] as? String == Fixture.digest(Data(marker.utf8)), "accepted-linked-readback-owner-differs")
                try Fixture.require(records.isEmpty, "unlink-left-canonical-record-or-rewrote-target-metadata")
                try Fixture.require(linked["targetBlockSHA256"] as? String == Fixture.digest(Fixture.bytes(target)),
                                    "unlink-modified-native-text-or-mark")
            }
            let secondRecords = try await AnytypeTorahAssociationRepository().listAssociationRecords(
                objectId: fixture.objectID, spaceId: fixture.spaceID)
            try Fixture.require(codec.encodeCanonicalDocument(.init(records: secondRecords)) == canonical,
                                "canonical-records-changed-during-independent-readback")
            let second = try await ClientCommands.objectShow(.with {
                $0.spaceID = fixture.spaceID; $0.objectID = fixture.objectID; $0.contextID = fixture.objectID
            }).invoke()
            try lease.validate()
            let targetAgain = try XCTUnwrap(second.objectView.blocks.first { $0.id == fixture.blockID })
            let excludedAgain = try XCTUnwrap(second.objectView.blocks.first { $0.id == fixture.excludedBlockID })
            try Fixture.require(Fixture.bytes(targetAgain) == Fixture.bytes(target)
                && Fixture.bytes(excludedAgain) == Fixture.bytes(excluded), "native-blocks-changed-during-readback")
            let firstBytes = try Fixture.bytes(first), secondBytes = try Fixture.bytes(second)
            var receipt: [String: Any] = [
                "protocol": "heart-semantic-source-native-readback-v1", "status": "PASS_NATIVE_READBACK",
                "phase": phase, "sourceSHA": fixture.sourceSHA, "runID": fixture.runID,
                "runAttempt": fixture.runAttempt, "nonce": fixture.nonce, "accountID": fixture.accountID,
                "spaceID": fixture.spaceID, "objectID": fixture.objectID, "blockID": fixture.blockID,
                "processID": ProcessInfo.processInfo.processIdentifier, "generation": lease.generation.uuidString,
                "runtimeVersion": version, "markerSHA256": Fixture.digest(Data(marker.utf8)),
                "fixtureSHA256": Fixture.digest(fixtureBytes), "captureReceiptSHA256": Fixture.digest(captureBytes),
                "reopenReceiptSHA256": Fixture.digest(reopenBytes), "uiReceiptSHA256": Fixture.digest(uiBytes),
                "targetBlockSHA256": try Fixture.digest(Fixture.bytes(target)),
                "excludedBlockSHA256": try Fixture.digest(Fixture.bytes(excluded)),
                "canonicalRecordCount": records.count, "canonicalRecordsSHA256": Fixture.digest(canonical),
                "canonicalRecordsBase64": canonical.base64EncodedString(),
                "firstObjectShowBase64": firstBytes.base64EncodedString(), "firstObjectShowSHA256": Fixture.digest(firstBytes),
                "secondObjectShowBase64": secondBytes.base64EncodedString(), "secondObjectShowSHA256": Fixture.digest(secondBytes),
                "contentMutationCallsIssuedByTest": 0, "nativeCaptureOrApplyCallsIssuedByTest": 0,
                "readbackOrigin": "production ObjectShow, canonical repository and native semantic resolver"
            ]
            try await document.close(); opened = false
            _ = try await ClientCommands.accountStop(.with { $0.removeData = false }).invoke(); stopped = true
            _ = try await ClientCommands.appShutdown().invoke(); shutdown = true
            receipt["accountStoppedWithoutRemovingData"] = true; receipt["appShutdownCompleted"] = true
            let bytes = try JSONSerialization.data(withJSONObject: receipt, options: [.sortedKeys])
            try bytes.write(to: output, options: .withoutOverwriting)
            // Preserve raw independent native responses only in the owned app
            // sandbox for private retention. Routine xcresult attachments carry
            // hashes/counts; they must not publish the full object payload.
            var publicReceipt = receipt
            for key in ["canonicalRecordsBase64", "firstObjectShowBase64", "secondObjectShowBase64"] {
                publicReceipt.removeValue(forKey: key)
            }
            publicReceipt["privateReadbackSHA256"] = Fixture.digest(bytes)
            publicReceipt["privateReadbackBytes"] = bytes.count
            let publicBytes = try JSONSerialization.data(withJSONObject: publicReceipt, options: [.sortedKeys])
            let attachment = XCTAttachment(data: publicBytes, uniformTypeIdentifier: "public.json")
            attachment.name = "heart-semantic-source-native-" + phase
            attachment.lifetime = .keepAlways; add(attachment)
        } catch {
            if opened { try? await document.close() }
            if !stopped { _ = try? await ClientCommands.accountStop(.with { $0.removeData = false }).invoke() }
            if !shutdown { _ = try? await ClientCommands.appShutdown().invoke() }
            throw error
        }
    }
}
#endif
