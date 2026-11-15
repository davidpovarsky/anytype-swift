import Foundation
import AnytypeCore
import PinkhaKit
import ProtobufMessages
import Services
import Testing
@testable import Anytype

/// Only for a fresh, signed simulator test host and a disposable local-only account.
@Suite("Simulator UI27 disposable fixture", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION"] == "1"))
struct SimulatorAcceptancePreparationTests {
    private enum PreparationError: Error {
        case disposableConfirmationMissing
        case emptyMnemonic
        case keychainReadbackMismatch
        case existingFixture
        case missingCanonicalLink
    }

    @MainActor
    @Test("Prepare real local account and source-bearing documents for UI smoke")
    func prepareRealUIFixture() async throws {
        guard ProcessInfo.processInfo.environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1" else {
            throw PreparationError.disposableConfirmationMissing
        }
        let directory = try FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true)
        let destination = directory.appendingPathComponent("pinkha-simulator-ui27-fixture.json")
        guard !FileManager.default.fileExists(atPath: destination.path) else {
            throw PreparationError.existingFixture
        }

        Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)
        let auth = Container.shared.authService()
        let mnemonic = try await auth.createWallet()
        guard !mnemonic.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw PreparationError.emptyMnemonic
        }
        let seedService = Container.shared.seedService()
        try seedService.saveSeed(mnemonic)
        let readback = try seedService.obtainSeed()
        guard readback == mnemonic.trimmingCharacters(in: .whitespacesAndNewlines) else {
            // Never place a mnemonic in an assertion, diagnostic, or fixture artifact.
            throw PreparationError.keychainReadbackMismatch
        }
        print("UI27_PREP wallet_created keychain_readback=matched")
        let account = try await auth.createAccount(name: "UI27 disposable", iconOption: 1, imagePath: "")
        _ = try #require(!account.id.isEmpty)
        let space = try await Container.shared.workspaceService().createSpace(
            name: "UI27 disposable Space", iconOption: 1, accessType: .private,
            useCase: .none, withChat: false, spaceType: .regular
        )
        let spaceID = space.spaceID
        _ = try #require(!spaceID.isEmpty)
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceID)
        print("UI27_PREP account_created space=\(spaceID)")
        let bootstrap = Container.shared.pinkhaBootstrapService()
        let manifest = try await bootstrap.bootstrapSpace(spaceId: spaceID)
        _ = try #require(bootstrap.isNativeSchemaProvisioned(spaceId: spaceID))
        let writingTypeID = try #require(manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey])
        print("UI27_PREP bootstrap_ready space=\(spaceID) writingType=\(writingTypeID)")

        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = writingTypeID; $0.objectID = writingTypeID; $0.spaceID = spaceID
        }).invoke()
        let typeDetails = try #require(response.objectView.details.first { $0.id == writingTypeID })
        let writingType = ObjectType(details: try ObjectDetails(protobufStruct: typeDetails.details))
        let objects = Container.shared.objectActionsService()
        let page = try await objects.createObject(
            name: "UI27 blank Page", typeUniqueKey: .page,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceID, origin: .none, templateId: nil
        )
        let document = try await objects.createObject(
            name: "UI27 source document", typeUniqueKey: writingType.uniqueKey,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceID, origin: .none,
            templateId: manifest.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey]
        )
        _ = try #require(!page.id.isEmpty && !document.id.isEmpty && page.id != document.id)
        print("UI27_PREP objects_created page=\(page.id) sourceDocument=\(document.id)")
        let source = TorahAssociationItem(kind: .ref, role: .context, providerID: "sefaria",
            externalID: "Genesis 1:1", canonicalKey: "Genesis 1:1", labelHe: "בראשית א:א",
            labelEn: "Genesis 1:1", createdAt: Date())
        let repository = AnytypeTorahAssociationRepository()
        _ = try await repository.addAssociation(source, target: .object(objectId: document.id), spaceId: spaceID)
        let saved = try await repository.listDocumentAssociations(objectId: document.id, spaceId: spaceID)
        guard saved.contains(where: { $0.id == source.id }) else {
            throw PreparationError.missingCanonicalLink
        }
        print("UI27_PREP canonical_source_saved object=\(document.id)")

        let fixture: [String: Any] = [
            "spaceId": spaceID,
            "universalDocuments": ["page": page.id],
            "manySourcesDocument": document.id
        ]
        let data = try JSONSerialization.data(withJSONObject: fixture, options: [.sortedKeys])
        try data.write(to: destination, options: .withoutOverwriting)
        print("UI27_PREP fixture_ready space=\(spaceID) page=\(page.id) sourceDocument=\(document.id)")
    }
}
