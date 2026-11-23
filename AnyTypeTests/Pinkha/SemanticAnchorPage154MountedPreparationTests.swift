#if DEBUG && targetEnvironment(simulator) && PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
import Foundation
import XCTest
import AnytypeCore
import ProtobufMessages
import Services
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
#endif
