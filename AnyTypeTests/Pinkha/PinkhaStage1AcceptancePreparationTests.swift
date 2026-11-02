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

        // Join the production bootstrap owner instead of racing its asynchronous activation hook.
        PinkhaBootstrapHook.handleSpaceActivated(spaceId: spaceId)
        let manifest = try await Container.shared.pinkhaBootstrapStateManager().awaitReadiness(
            spaceId: spaceId, timeoutSeconds: 60
        )
        let typeId = try #require(
            manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey]
        )
        let typeProvider = Container.shared.objectTypeProvider()
        let indexClock = ContinuousClock()
        let indexDeadline = indexClock.now.advanced(by: .seconds(30))
        var typesAreIndexed = false
        repeat {
            let types = typeProvider.objectTypes(spaceId: spaceId)
            if types.contains(where: { $0.id == typeId }),
               let noteType = types.first(where: { $0.uniqueKey == .note }),
               let pageType = types.first(where: { $0.uniqueKey == .page }) {
                let expectedIDs = Set([typeId, noteType.id, pageType.id])
                let indexed = try await Container.shared.searchService().searchObjects(
                    spaceId: spaceId, objectIds: Array(expectedIDs)
                )
                typesAreIndexed = expectedIDs.isSubset(of: Set(indexed.map(\.id)))
                if typesAreIndexed { break }
            }
            try await Task.sleep(nanoseconds: 100_000_000)
        } while indexClock.now < indexDeadline
        try #require(typesAreIndexed, "Native Page/Note/Pinkha creation requires their types in this Space's index")
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

        // Verify real native document shapes independently of UI-test diagnostic labels.
        #expect(Set([document.id, note.id, page.id]).count == 3)
        let fixtures: [(String, DetailsLayout, Bool)] = [
            (document.id, .basic, true),
            (note.id, .note, false),
            (page.id, .basic, true)
        ]
        for (objectID, layout, hasTitle) in fixtures {
            let nativeDocument = Container.shared.documentsProvider().document(
                objectId: objectID, spaceId: spaceId, mode: .preview
            )
            try await nativeDocument.open()
            let details = try #require(nativeDocument.details)
            #expect(details.resolvedLayoutValue == layout)
            if objectID == document.id { #expect(details.type == typeId) }
            let tree = nativeDocument.infoContainer.recursiveChildren(of: objectID)
            let featuredCount = tree.filter { $0.content == .featuredRelations }.count
            let actualHasTitle = tree.contains { $0.textContent?.contentType == .title }
            #expect(featuredCount == 1)
            #expect(actualHasTitle == hasTitle)
            print("PINKHA_ACCEPTANCE_NATIVE_SHAPE object=\(objectID) layout=\(details.resolvedLayoutValue.rawValue) featuredRelations=\(featuredCount) title=\(actualHasTitle)")
            try await nativeDocument.close()
        }

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
