#if DEBUG && targetEnvironment(simulator)
import Foundation
import AnytypeCore
import ProtobufMessages
import Services
import Testing
@testable import Anytype

@Suite("Hanlin SDK06 real native disposable fixture", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_HANLIN_NATIVE_PREPARATION"] == "1"))
@MainActor
struct HanlinNativeAcceptancePreparationTests {
    @Test("Prepare native SDK read/create fixture without an AI provider")
    func prepareRealHostFixture() async throws {
        let environment = ProcessInfo.processInfo.environment
        try #require(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1")
        try #require(environment["PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION"] == "1")
        let sourceSHA = try #require(environment["PINKHA_HANLIN_NATIVE_SOURCE_SHA"])
        let runID = try #require(environment["PINKHA_HANLIN_NATIVE_RUN_ID"])
        let runAttempt = try #require(environment["PINKHA_HANLIN_NATIVE_RUN_ATTEMPT"])
        try #require(sourceSHA.count == 40 && sourceSHA.allSatisfy(\.isHexDigit))
        try #require(UInt64(runID).map { $0 > 0 } == true && UInt64(runAttempt).map { $0 > 0 } == true)
        try #require(Container.shared.accountManager().account.id.isEmpty,
                     "This preparation requires a fresh simulator with no existing account")
        try #require(Bundle.main.object(forInfoDictionaryKey: "CompilationCondition") as? String == "DEBUG")
        try #require(TargetsConstants.appGroup == "group.io.anytype.app.dev")
        let sharedContainer = try #require(FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: TargetsConstants.appGroup))
        try #require(try sharedContainer.resourceValues(forKeys: [.isDirectoryKey]).isDirectory == true)
        print("PINKHA_HANLIN_SHARED_GROUP_AVAILABLE group=\(TargetsConstants.appGroup) pid=\(ProcessInfo.processInfo.processIdentifier) source=\(sourceSHA) run=\(runID)")
        for name in [PinkhaHanlinNativeAcceptanceFixture.fileName,
                     PinkhaHanlinNativeAcceptanceFixture.resultFileName] {
            let path = try PinkhaHanlinNativeAcceptanceFixture.fileURL(name).path
            try #require(!FileManager.default.fileExists(atPath: path))
        }

        // Use the existing feature setting and real handler, never a no-op event
        // handler. Logging must be off before creating the disposable wallet and
        // remain off in the subsequent cold UI process for native write admission.
        FeatureFlags.update(key: .logMiddlewareRequests, value: false)
        let handler = try #require(InvocationSettings.handler as? InvocationMesagesHandler)
        handler.enableLogger = false
        try #require(InvocationSettings.handler?.isLogEnabled == false)
        try await SimulatorAcceptancePreparationTests().prepareRealUIFixture()
        try #require(Container.shared.serverConfigurationStorage().currentConfiguration() == .localOnly)

        let originalURL = try PinkhaHanlinNativeAcceptanceFixture.fileURL("pinkha-simulator-ui27-fixture.json")
        let original = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: originalURL)) as? [String: Any])
        let spaceID = try #require(original["spaceId"] as? String)
        let pages = try #require(original["universalDocuments"] as? [String: String])
        let sourceID = try #require(pages["page"])
        let accountID = Container.shared.accountManager().account.id
        try #require(!accountID.isEmpty)

        let nonce = UUID()
        let body = "Hanlin native body " + nonce.uuidString
        let document = Container.shared.openedDocumentProvider().document(objectId: sourceID, spaceId: spaceID)
        try await document.open()
        let sourceTitle = try #require(document.details?.name)
        let blockID = try await Container.shared.blockService().addFirstBlock(
            contextId: sourceID, info: .empty(id: "", content: .text(.plain(body, contentType: .text)))
        )
        let view = try await Container.shared.objectLifecycleService().openForPreview(contextId: sourceID, spaceId: spaceID)
        try #require(view.rootID == sourceID)
        try #require(view.blocks.contains { block in
            guard block.id == blockID, let converted = BlockInformationConverter.convert(block: block),
                  case .text(let content) = converted.content else { return false }
            return content.text == body
        })
        try await document.close()

        let alternate = try await Container.shared.workspaceService().createSpace(
            name: "Hanlin native alternate " + nonce.uuidString, iconOption: 1, accessType: .private,
            useCase: .none, withChat: false, spaceType: .regular
        )
        try #require(!alternate.spaceID.isEmpty && alternate.spaceID != spaceID)
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceID)
        let fixture = PinkhaHanlinNativeAcceptanceFixture(
            fixtureID: nonce, createdAt: Date(), sourceSHA: sourceSHA, runID: runID, runAttempt: runAttempt,
            accountID: accountID, spaceID: spaceID, alternateSpaceID: alternate.spaceID,
            sourceObjectID: sourceID, sourceTitle: sourceTitle, sourceBlockID: blockID, sourceText: body,
            createdTitle: "Hanlin native created " + nonce.uuidString,
            cancelledTitle: "Hanlin native cancelled " + nonce.uuidString
        )
        try fixture.save()
        print("PINKHA_HANLIN_NATIVE_FIXTURE_READY fixture=\(nonce.uuidString) source=\(sourceSHA) run=\(runID)")
    }
}
#endif
