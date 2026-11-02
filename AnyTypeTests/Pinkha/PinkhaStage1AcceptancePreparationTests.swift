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
        // Note is no longer a bundled system type in current Anytype. Provision the
        // native Note layout only in this disposable fixture Space, using original APIs.
        let noteType = try await Container.shared.typesService().createType(
            name: "Acceptance Native Note", pluralName: "Acceptance Native Notes",
            icon: nil, color: nil, spaceId: spaceId
        )
        try await Container.shared.propertiesService().updateProperty(
            objectId: noteType.id,
            propertyKey: BundledPropertyKey.recommendedLayout.rawValue,
            value: DetailsLayout.note.rawValue.protobufValue
        )
        let noteTemplateID = try await Container.shared.templatesService().createTemplateFromObjectType(
            objectTypeId: noteType.id, spaceId: spaceId
        )
        try await Container.shared.templatesService().setTemplateAsDefaultForType(
            objectTypeId: noteType.id, templateId: noteTemplateID
        )

        // Read this Space's real index directly; a UI cache can switch active Spaces.
        let indexClock = ContinuousClock()
        let indexDeadline = indexClock.now.advanced(by: .seconds(30))
        var indexedTypes = [ObjectType]()
        repeat {
            indexedTypes = try await Container.shared.searchMiddleService().search(
                spaceId: spaceId, filters: [SearchHelper.layoutFilter([.objectType])],
                keys: ObjectType.subscriptionKeys.map(\.rawValue), limit: 0
            ).map(ObjectType.init(details:))
            if indexedTypes.contains(where: { $0.id == typeId }),
               indexedTypes.contains(where: { $0.id == noteType.id }),
               indexedTypes.contains(where: { $0.uniqueKey == .page }) { break }
            try await Task.sleep(nanoseconds: 100_000_000)
        } while indexClock.now < indexDeadline
        let pinkhaType = try #require(indexedTypes.first { $0.id == typeId })
        let indexedNoteType = try #require(indexedTypes.first { $0.id == noteType.id })
        _ = try #require(indexedTypes.first { $0.uniqueKey == .page })
        #expect(indexedNoteType.recommendedLayout == .note)
        print("PINKHA_ACCEPTANCE_TYPES_READY pinkha=\(pinkhaType.id) note=\(indexedNoteType.id) builtinNotePresent=\(indexedTypes.contains { $0.uniqueKey == .note })")

        let objectActions = Container.shared.objectActionsService()
        let document = try await objectActions.createObject(
            name: PinkhaStage1AcceptanceState.pinkhaDocumentTitle,
            typeUniqueKey: pinkhaType.uniqueKey,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceId, origin: .none,
            templateId: manifest.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey]
        )
        await MainActor.run {
            PinkhaDocumentIdentityStorage.shared.registerCreated(objectId: document.id, spaceId: spaceId)
        }
        let note = try await objectActions.createObject(
            name: PinkhaStage1AcceptanceState.noteDocumentTitle,
            typeUniqueKey: indexedNoteType.uniqueKey,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceId, origin: .none, templateId: noteTemplateID
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
