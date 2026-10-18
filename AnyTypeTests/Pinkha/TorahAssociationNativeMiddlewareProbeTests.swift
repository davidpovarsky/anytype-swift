import AnytypeCore
import Foundation
import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf
import Testing
@testable import Anytype

@Suite("T2-L real Anytype middleware persistence probe", .serialized)
struct TorahAssociationNativeMiddlewareProbeTests {
    @Test(
        "Phase 1 writes document and block associations through the native property",
        .enabled(if: ProcessInfo.processInfo.environment["PINKHA_T2L_NATIVE_PROBE_PHASE"] == "prepare")
    )
    func prepareNativeState() async throws {
        let paths = try ProbePaths.make()
        try? FileManager.default.removeItem(at: paths.root)
        try? FileManager.default.removeItem(at: paths.state)

        let auth = Container.shared.authMiddleService()
        _ = try await auth.createWallet(rootPath: paths.root.path)
        let account = try await auth.createAccount(
            name: "Pinkha T2-L Probe",
            imagePath: "",
            iconOption: 1,
            networkMode: .localOnly,
            joinStreamUrl: "",
            configPath: nil
        )
        #expect(!account.id.isEmpty)

        let workspace = try await Container.shared.workspaceService().createSpace(
            name: "Pinkha T2-L Disposable Space",
            iconOption: 1,
            accessType: .private,
            useCase: .none,
            withChat: false,
            spaceType: .regular
        )
        let spaceId = workspace.spaceID
        #expect(!spaceId.isEmpty)
        _ = try await Container.shared.workspaceService().workspaceOpen(spaceId: spaceId, withChat: false)

        let manifest = try await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: spaceId)
        #expect(manifest.isFullyProvisioned)

        let document = try await Container.shared.objectActionsService().createObject(
            name: "T2-L canonical document",
            typeUniqueKey: .page,
            shouldDeleteEmptyObject: false,
            shouldSelectType: false,
            shouldSelectTemplate: false,
            spaceId: spaceId,
            origin: .none,
            additionalDetails: [.description("non-Torah detail must survive")]
        )
        let blockId = try await Container.shared.blockService().addFirstBlock(
            contextId: document.id,
            info: .empty(
                id: "",
                content: .text(.plain("Non-Torah block content", contentType: .text))
            )
        )

        let before = try await documentSnapshot(
            spaceId: spaceId,
            objectId: document.id,
            associationKey: manifest.documentAssociationsPropertyKey
        )
        #expect(before.blockIds.contains(blockId))
        #expect(before.name == "T2-L canonical document")
        #expect(before.description == "non-Torah detail must survive")
        #expect(before.associationValue == nil || before.associationValue == "")

        let repository = AnytypeTorahAssociationRepository()
        var documentItem = association(id: "document-final", reference: "Genesis 1:1")
        _ = try await repository.addAssociation(
            documentItem,
            target: .object(objectId: document.id),
            spaceId: spaceId
        )
        documentItem.labelEn = "Genesis 1:1 (edited)"
        _ = try await repository.updateAssociation(
            documentItem,
            target: .object(objectId: document.id),
            spaceId: spaceId
        )

        let removed = association(id: "document-removed", reference: "Genesis 1:2")
        _ = try await repository.addAssociation(
            removed,
            target: .object(objectId: document.id),
            spaceId: spaceId
        )
        try await repository.removeAssociation(
            associationId: removed.id,
            target: .object(objectId: document.id),
            spaceId: spaceId
        )

        let blockItem = association(id: "block-final", reference: "Exodus 3:2")
        _ = try await repository.addAssociation(
            blockItem,
            target: .block(objectId: document.id, blockId: blockId),
            spaceId: spaceId
        )

        let documentItems = try await repository.listDocumentAssociations(
            objectId: document.id,
            spaceId: spaceId
        )
        let blockItems = try await repository.listBlockAssociations(
            objectId: document.id,
            blockId: blockId,
            spaceId: spaceId
        )
        #expect(documentItems == [documentItem])
        #expect(blockItems == [blockItem])

        let after = try await documentSnapshot(
            spaceId: spaceId,
            objectId: document.id,
            associationKey: manifest.documentAssociationsPropertyKey
        )
        #expect(after.blockBytes == before.blockBytes)
        #expect(after.name == before.name)
        #expect(after.description == before.description)
        #expect(after.associationValue?.contains(#""version":2"#) == true)

        let state = ProbeState(
            rootPath: paths.root.path,
            accountId: account.id,
            spaceId: spaceId,
            objectId: document.id,
            blockId: blockId,
            associationKey: manifest.documentAssociationsPropertyKey,
            expectedDocument: documentItem,
            expectedBlock: blockItem,
            blockBytes: before.blockBytes,
            name: before.name,
            description: before.description
        )
        try JSONEncoder().encode(state).write(to: paths.state, options: .atomic)

        try await Container.shared.authMiddleService().logout(removeData: false)
        #expect(FileManager.default.fileExists(atPath: paths.state.path))
    }

    @Test(
        "Phase 2 reopens after host termination and reads the exact native state",
        .enabled(if: ProcessInfo.processInfo.environment["PINKHA_T2L_NATIVE_PROBE_PHASE"] == "relaunch")
    )
    func reopenNativeStateAfterHostTermination() async throws {
        let paths = try ProbePaths.make()
        let state = try JSONDecoder().decode(ProbeState.self, from: Data(contentsOf: paths.state))

        _ = try await Container.shared.authMiddleService().selectAccount(
            id: state.accountId,
            rootPath: state.rootPath,
            networkMode: .localOnly,
            joinStreamUrl: "",
            configPath: nil,
            preferredSpaceId: state.spaceId
        )
        _ = try await Container.shared.workspaceService().workspaceOpen(spaceId: state.spaceId, withChat: false)

        let repository = AnytypeTorahAssociationRepository()
        let documentItems = try await repository.listDocumentAssociations(
            objectId: state.objectId,
            spaceId: state.spaceId
        )
        let blockItems = try await repository.listBlockAssociations(
            objectId: state.objectId,
            blockId: state.blockId,
            spaceId: state.spaceId
        )
        #expect(documentItems == [state.expectedDocument])
        #expect(blockItems == [state.expectedBlock])

        let reopened = try await documentSnapshot(
            spaceId: state.spaceId,
            objectId: state.objectId,
            associationKey: state.associationKey
        )
        #expect(reopened.blockBytes == state.blockBytes)
        #expect(reopened.name == state.name)
        #expect(reopened.description == state.description)
        #expect(reopened.associationValue?.contains(#""version":2"#) == true)

        try await Container.shared.authMiddleService().logout(removeData: true)
        try? FileManager.default.removeItem(at: paths.state)
    }

    private func documentSnapshot(
        spaceId: String,
        objectId: String,
        associationKey: String
    ) async throws -> DocumentProbeSnapshot {
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = objectId
            $0.objectID = objectId
            $0.spaceID = spaceId
        }).invoke(qos: .userInitiated)
        let detailsStruct = try #require(
            response.objectView.details.first(where: { $0.id == objectId })?.details
        )
        let details = try ObjectDetails(protobufStruct: detailsStruct)
        return DocumentProbeSnapshot(
            blockIds: Set(response.objectView.blocks.map(\.id)),
            blockBytes: try response.objectView.blocks.map {
                try $0.serializedData().base64EncodedString()
            },
            name: details.values[BundledPropertyKey.name.rawValue]?.stringValue ?? "",
            description: details.values[BundledPropertyKey.description.rawValue]?.stringValue ?? "",
            associationValue: details.values[associationKey]?.stringValue
        )
    }

    private func association(id: String, reference: String) -> TorahAssociationItem {
        TorahAssociationItem(
            id: id,
            kind: .ref,
            role: .context,
            providerID: "sefaria",
            externalID: reference.replacingOccurrences(of: " ", with: "."),
            canonicalKey: reference,
            labelHe: "מקור בדיקה",
            labelEn: reference
        )
    }
}

private struct DocumentProbeSnapshot: Sendable {
    let blockIds: Set<String>
    let blockBytes: [String]
    let name: String
    let description: String
    let associationValue: String?
}

private struct ProbeState: Codable, Sendable {
    let rootPath: String
    let accountId: String
    let spaceId: String
    let objectId: String
    let blockId: String
    let associationKey: String
    let expectedDocument: TorahAssociationItem
    let expectedBlock: TorahAssociationItem
    let blockBytes: [String]
    let name: String
    let description: String
}

private struct ProbePaths {
    let root: URL
    let state: URL

    static func make() throws -> ProbePaths {
        let applicationSupport = try FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        return ProbePaths(
            root: applicationSupport.appendingPathComponent("pinkha-t2l-native-probe-repository", isDirectory: true),
            state: applicationSupport.appendingPathComponent("pinkha-t2l-native-probe-state.json")
        )
    }
}
