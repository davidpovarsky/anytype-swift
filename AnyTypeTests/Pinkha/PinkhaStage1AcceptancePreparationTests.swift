import AnytypeCore
import PinkhaKit
import Services
import Testing
@testable import Anytype

@Suite("Pinkha Stage 1 real-app acceptance preparation", .serialized)
struct PinkhaStage1AcceptancePreparationTests {
    @Test("Creates disposable Pinkha, ordinary Note and ordinary Page documents")
    func prepareRealApplicationState() async throws {
        Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)

        let auth = Container.shared.authService()
        let mnemonic = try await auth.createWallet()
        try Container.shared.seedService().saveSeed(mnemonic)
        let account = try await auth.createAccount(
            name: "Pinkha Stage 1 Acceptance",
            iconOption: 1,
            imagePath: ""
        )
        #expect(!account.id.isEmpty)

        let workspace = try await Container.shared.workspaceService().createSpace(
            name: PinkhaStage1AcceptanceState.spaceName,
            iconOption: 1,
            accessType: .private,
            useCase: .none,
            withChat: false,
            spaceType: .regular
        )
        let spaceId = workspace.spaceID
        #expect(!spaceId.isEmpty)
        // Use the same activation path as SpaceLoadingContainer. Besides opening the Space,
        // this starts the real type/property subscriptions and records it as the active Space
        // for the subsequent application launch.
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceId)

        let manifest = try await Container.shared.pinkhaBootstrapService().bootstrapSpace(
            spaceId: spaceId
        )
        Container.shared.pinkhaBootstrapStateManager().setState(.ready(manifest), for: spaceId)
        let typeId = try #require(
            manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey]
        )
        let typeProvider = Container.shared.objectTypeProvider()
        for _ in 0..<50 where (try? typeProvider.objectType(id: typeId)) == nil {
            try await Task.sleep(for: .milliseconds(100))
        }
        _ = try typeProvider.objectType(id: typeId)
        let document = try await PinkhaHierarchyMutationService().createWritingDocument(
            typeId: typeId,
            parentId: nil,
            spaceId: spaceId,
            manifest: manifest,
            existingSiblings: []
        )
        try await Container.shared.propertiesService().updateProperty(
            objectId: document.id,
            propertyKey: BundledPropertyKey.name.rawValue,
            value: PinkhaStage1AcceptanceState.pinkhaDocumentTitle.protobufValue
        )

        let objectActions = Container.shared.objectActionsService()
        let note = try await objectActions.createObject(
            name: PinkhaStage1AcceptanceState.noteDocumentTitle,
            typeUniqueKey: .note,
            shouldDeleteEmptyObject: false,
            shouldSelectType: false,
            shouldSelectTemplate: false,
            spaceId: spaceId,
            origin: .none,
            templateId: nil
        )
        let page = try await objectActions.createObject(
            name: PinkhaStage1AcceptanceState.pageDocumentTitle,
            typeUniqueKey: .page,
            shouldDeleteEmptyObject: false,
            shouldSelectType: false,
            shouldSelectTemplate: false,
            spaceId: spaceId,
            origin: .none,
            templateId: nil
        )

        try PinkhaStage1AcceptanceState(
            spaceId: spaceId,
            pinkhaObjectId: document.id,
            noteObjectId: note.id,
            pageObjectId: page.id
        ).save()
        try await Container.shared.authMiddleService().preloadRemainingSpaces()

        print(
            "PINKHA_STAGE1_ACCEPTANCE_READY space=\(spaceId) "
            + "pinkha=\(document.id) note=\(note.id) page=\(page.id)"
        )
    }
}
