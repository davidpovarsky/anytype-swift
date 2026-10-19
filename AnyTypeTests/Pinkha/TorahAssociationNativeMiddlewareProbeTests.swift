import AnytypeCore
import Foundation
import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf
import Testing
@testable import Anytype

@Suite("T2-L real Anytype middleware prepare probe", .serialized)
struct TorahAssociationNativeMiddlewarePrepareTests {
    @Test("Phase 1 writes document and block associations through the native property")
    func prepareNativeState() async throws {
        let paths = try ProbePaths.make()
        try? FileManager.default.removeItem(at: paths.root)
        try? FileManager.default.removeItem(at: paths.state)

        let auth = Container.shared.authMiddleService()
        let mnemonic = try await auth.createWallet(rootPath: paths.root.path)
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
            templateId: nil,
            additionalDetails: [.description("non-Torah detail must survive")]
        )
        let blockIdA = try await Container.shared.blockService().addFirstBlock(
            contextId: document.id,
            info: .empty(
                id: "",
                content: .text(.plain("Non-Torah block content", contentType: .text))
            )
        )
        let blockIdB = try await Container.shared.blockService().add(
            contextId: document.id,
            targetId: blockIdA,
            info: .empty(
                id: "",
                content: .text(.plain("Second non-Torah block", contentType: .text))
            ),
            position: .bottom
        )

        let before = try await documentSnapshot(
            spaceId: spaceId,
            objectId: document.id,
            associationKey: manifest.documentAssociationsPropertyKey
        )
        #expect(before.blockIds.contains(blockIdA))
        #expect(before.blockIds.contains(blockIdB))
        #expect(before.name == "T2-L canonical document")
        #expect(before.description == "non-Torah detail must survive")
        #expect(before.associationValue == nil || before.associationValue == "")

        // Two repository instances model independent scenes/windows in one app
        // process. Both must use the same process-wide document mutation queue.
        let repositoryA = AnytypeTorahAssociationRepository()
        let repositoryB = AnytypeTorahAssociationRepository()
        var sourceA = association(id: "a-source", kind: .ref, reference: "Genesis 1:1")
        let wordB = association(id: "b-word", kind: .word, reference: "בראשית")
        let topicC = association(id: "c-topic", kind: .topic, reference: "creation")
        try await withThrowingTaskGroup(of: Void.self) { group in
            for (repository, item) in [(repositoryA, sourceA), (repositoryB, wordB), (repositoryA, topicC)] {
                group.addTask {
                    _ = try await repository.addAssociation(
                        item,
                        target: .object(objectId: document.id),
                        spaceId: spaceId
                    )
                }
            }
            try await group.waitForAll()
        }

        let sourceD = association(id: "d-source", kind: .ref, reference: "Genesis 1:4")
        sourceA.labelEn = "Genesis 1:1 (edited)"
        try await withThrowingTaskGroup(of: Void.self) { group in
            group.addTask {
                try await repositoryA.removeAssociation(
                    associationId: wordB.id,
                    target: .object(objectId: document.id),
                    spaceId: spaceId
                )
            }
            group.addTask {
                _ = try await repositoryB.addAssociation(
                    sourceD,
                    target: .object(objectId: document.id),
                    spaceId: spaceId
                )
            }
            group.addTask {
                _ = try await repositoryA.updateAssociation(
                    sourceA,
                    target: .object(objectId: document.id),
                    spaceId: spaceId
                )
            }
            try await group.waitForAll()
        }

        let blockSourceA = association(id: "block-a-source", kind: .ref, reference: "Exodus 3:2")
        let blockSourceB = association(id: "block-b-source", kind: .ref, reference: "Exodus 3:2")
        _ = try await repositoryA.addAssociation(
            blockSourceA,
            target: .block(objectId: document.id, blockId: blockIdA),
            spaceId: spaceId
        )
        _ = try await repositoryB.addAssociation(
            blockSourceB,
            target: .block(objectId: document.id, blockId: blockIdB),
            spaceId: spaceId
        )
        let deduplicatedRetry = try await repositoryA.addAssociation(
            association(id: "block-a-retry", kind: .ref, reference: "Exodus 3:2"),
            target: .block(objectId: document.id, blockId: blockIdA),
            spaceId: spaceId
        )
        #expect(deduplicatedRetry.id == blockSourceA.id)

        let quoteA = association(
            id: "quote-a",
            kind: .ref,
            role: .sourceQuote,
            reference: "Exodus 3:2",
            providerPayload: #"{"version":2,"excerpt":"first"}"#
        )
        let quoteB = association(
            id: "quote-b",
            kind: .ref,
            role: .sourceQuote,
            reference: "Exodus 3:2",
            providerPayload: #"{"version":2,"excerpt":"second"}"#
        )
        _ = try await repositoryA.addAssociation(
            quoteA,
            target: .block(objectId: document.id, blockId: blockIdA),
            spaceId: spaceId
        )
        _ = try await repositoryA.addAssociation(
            quoteB,
            target: .block(objectId: document.id, blockId: blockIdA),
            spaceId: spaceId
        )

        // The real middleware persists the write; this wrapper deliberately
        // drops only its acknowledgement. Repository reconciliation must reopen
        // the native property and return success without a duplicate retry.
        let lostAcknowledgement = association(
            id: "e-lost-ack",
            kind: .topic,
            reference: "revelation"
        )
        let reconciliationRepository = AnytypeTorahAssociationRepository(
            nativeStore: LostAcknowledgementNativeStore()
        )
        _ = try await reconciliationRepository.addAssociation(
            lostAcknowledgement,
            target: .object(objectId: document.id),
            spaceId: spaceId
        )

        let expectedDocument = [sourceA, topicC, sourceD, lostAcknowledgement].sorted { $0.id < $1.id }
        let expectedBlockA = [blockSourceA, quoteA, quoteB].sorted { $0.id < $1.id }
        let expectedBlockB = [blockSourceB]
        let documentItems = try await repositoryA.listDocumentAssociations(
            objectId: document.id,
            spaceId: spaceId
        )
        let blockItemsA = try await repositoryA.listBlockAssociations(
            objectId: document.id,
            blockId: blockIdA,
            spaceId: spaceId
        )
        let blockItemsB = try await repositoryB.listBlockAssociations(
            objectId: document.id,
            blockId: blockIdB,
            spaceId: spaceId
        )
        #expect(documentItems == expectedDocument)
        #expect(blockItemsA == expectedBlockA)
        #expect(blockItemsB == expectedBlockB)

        // Exercise exact native close/reopen, lifecycle transition and Space
        // switch before the separate process-relaunch phase.
        try await ClientCommands.objectClose(.with {
            $0.contextID = document.id
            $0.objectID = document.id
            $0.spaceID = spaceId
        }).invoke()
        try await ClientCommands.appSetDeviceState(.with { $0.deviceState = .background }).invoke()
        try await ClientCommands.appSetDeviceState(.with { $0.deviceState = .foreground }).invoke()
        let away = try await Container.shared.workspaceService().createSpace(
            name: "T2-L Away Space",
            iconOption: 2,
            accessType: .private,
            useCase: .none,
            withChat: false,
            spaceType: .regular
        )
        _ = try await Container.shared.workspaceService().workspaceOpen(spaceId: away.spaceID, withChat: false)
        _ = try await Container.shared.workspaceService().workspaceOpen(spaceId: spaceId, withChat: false)
        #expect(
            try await repositoryA.listDocumentAssociations(objectId: document.id, spaceId: spaceId)
                == expectedDocument
        )

        // Unsupported native values are fail-closed and byte-for-byte retained.
        let futureDocument = try await Container.shared.objectActionsService().createObject(
            name: "T2-L future payload guard",
            typeUniqueKey: .page,
            shouldDeleteEmptyObject: false,
            shouldSelectType: false,
            shouldSelectTemplate: false,
            spaceId: spaceId,
            origin: .none,
            templateId: nil
        )
        let futurePayload = #"{"records":[],"version":99}"#
        try await Container.shared.propertiesService().updateProperty(
            objectId: futureDocument.id,
            propertyKey: manifest.documentAssociationsPropertyKey,
            value: futurePayload.protobufValue
        )
        do {
            _ = try await repositoryA.addAssociation(
                association(id: "must-not-write", kind: .ref, reference: "Genesis 9:9"),
                target: .object(objectId: futureDocument.id),
                spaceId: spaceId
            )
            Issue.record("Future native payload was overwritten")
        } catch let error as TorahAssociationRepositoryError {
            #expect(error == .unsupportedPayloadVersion(99))
        }
        let guarded = try await documentSnapshot(
            spaceId: spaceId,
            objectId: futureDocument.id,
            associationKey: manifest.documentAssociationsPropertyKey
        )
        #expect(guarded.associationValue == futurePayload)

        await expectFailure(.targetNotFound) {
            _ = try await repositoryA.addAssociation(
                self.association(id: "stale-block", kind: .ref, reference: "Genesis 2:1"),
                target: .block(objectId: document.id, blockId: "deleted-or-stale-block"),
                spaceId: spaceId
            )
        }

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
            mnemonic: mnemonic,
            accountId: account.id,
            spaceId: spaceId,
            objectId: document.id,
            blockIdA: blockIdA,
            blockIdB: blockIdB,
            associationKey: manifest.documentAssociationsPropertyKey,
            expectedDocument: expectedDocument,
            expectedBlockA: expectedBlockA,
            expectedBlockB: expectedBlockB,
            blockBytes: before.blockBytes,
            name: before.name,
            description: before.description
        )
        try JSONEncoder().encode(state).write(to: paths.state, options: .atomic)

        try await Container.shared.authMiddleService().logout(removeData: false)
        #expect(FileManager.default.fileExists(atPath: paths.state.path))
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

    private func association(
        id: String,
        kind: TorahAssociationKind,
        role: TorahAssociationRole = .context,
        reference: String,
        providerPayload: String? = nil
    ) -> TorahAssociationItem {
        TorahAssociationItem(
            id: id,
            kind: kind,
            role: role,
            providerID: "sefaria",
            externalID: reference.replacingOccurrences(of: " ", with: "."),
            canonicalKey: reference,
            labelHe: "מקור בדיקה",
            labelEn: reference,
            rawInput: reference,
            providerPayload: providerPayload ?? #"{"provider":"sefaria","retained":true}"#,
            customMetadata: ["probe": "native"]
        )
    }

    private func expectFailure(
        _ expected: TorahAssociationRepositoryError,
        operation: () async throws -> Void
    ) async {
        do {
            try await operation()
            Issue.record("Guarded native operation unexpectedly succeeded")
        } catch let error as TorahAssociationRepositoryError {
            #expect(error == expected)
        } catch {
            Issue.record("Unexpected native error: \(error)")
        }
    }
}

@Suite("T2-L real Anytype middleware relaunch probe", .serialized)
struct TorahAssociationNativeMiddlewareRelaunchTests {
    @Test("Phase 2 reopens after host termination and reads the exact native state")
    func reopenNativeStateAfterHostTermination() async throws {
        let paths = try ProbePaths.make()
        let state = try JSONDecoder().decode(ProbeState.self, from: Data(contentsOf: paths.state))

        let auth = Container.shared.authMiddleService()
        try await auth.walletRecovery(rootPath: state.rootPath, mnemonic: state.mnemonic)
        _ = try await auth.selectAccount(
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
            blockId: state.blockIdA,
            spaceId: state.spaceId
        )
        let blockItemsB = try await repository.listBlockAssociations(
            objectId: state.objectId,
            blockId: state.blockIdB,
            spaceId: state.spaceId
        )
        #expect(documentItems == state.expectedDocument)
        #expect(blockItems == state.expectedBlockA)
        #expect(blockItemsB == state.expectedBlockB)

        let reopened = try await documentSnapshot(
            spaceId: state.spaceId,
            objectId: state.objectId,
            associationKey: state.associationKey
        )
        #expect(reopened.blockBytes == state.blockBytes)
        #expect(reopened.name == state.name)
        #expect(reopened.description == state.description)
        #expect(reopened.associationValue?.contains(#""version":2"#) == true)

        try await auth.logout(removeData: true)
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
    let mnemonic: String
    let accountId: String
    let spaceId: String
    let objectId: String
    let blockIdA: String
    let blockIdB: String
    let associationKey: String
    let expectedDocument: [TorahAssociationItem]
    let expectedBlockA: [TorahAssociationItem]
    let expectedBlockB: [TorahAssociationItem]
    let blockBytes: [String]
    let name: String
    let description: String
}

private struct LostAcknowledgementNativeStore: TorahAssociationNativeStore {
    private let base = MiddlewareTorahAssociationNativeStore()

    func readDocument(
        spaceId: String,
        objectId: String,
        propertyKey: String
    ) async throws -> TorahAssociationNativeDocumentSnapshot {
        try await base.readDocument(spaceId: spaceId, objectId: objectId, propertyKey: propertyKey)
    }

    func writeDocumentProperty(objectId: String, propertyKey: String, value: String) async throws {
        try await base.writeDocumentProperty(objectId: objectId, propertyKey: propertyKey, value: value)
        throw LostAcknowledgementError.simulatedAfterNativeCommit
    }
}

private enum LostAcknowledgementError: Error {
    case simulatedAfterNativeCommit
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
