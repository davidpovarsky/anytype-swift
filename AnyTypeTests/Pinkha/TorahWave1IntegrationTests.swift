import Foundation
import AnytypeCore
import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf
import Testing
import TorahInspectorCore
@testable import Anytype

/// Run alone in the freshly created CI simulator; never open an existing wallet.
@Suite("Wave 1 actual native query and host", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_WAVE1_ACCEPTANCE"] == "1"))
struct TorahWave1IntegrationTests {
    @MainActor
    @Test("Published V3, native cross-document query and host Note create/open/unlink")
    func realNativeQueryAndNoteLifecycle() async throws {
        Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)
        let auth = Container.shared.authService()
        let mnemonic = try await auth.createWallet()
        try #require(!mnemonic.isEmpty)
        // This in-process fixture needs no credential persistence or later wallet recovery.
        // Keep the real native wallet/account; never save its disposable seed to Keychain.
        _ = try await auth.createAccount(name: "Wave 1 disposable", iconOption: 1, imagePath: "")
        let space = try await Container.shared.workspaceService().createSpace(
            name: "Wave 1 disposable Space", iconOption: 1, accessType: .private,
            useCase: .none, withChat: false, spaceType: .regular
        )
        let spaceID = space.spaceID
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceID)
        let manifest = try await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: spaceID)
        // Note is a bundled, optional Type in this native baseline, not a system Type.
        // Match the existing universal-properties fixture's real Space installation.
        _ = try await ClientCommands.workspaceObjectListAdd(.with {
            $0.spaceID = spaceID; $0.objectIds = ["_otnote"]
        }).invoke()
        print("WAVE1_FIXTURE_READY native-account-space-schema-and-note-type")
        let writingTypeID = try #require(manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey])
        let writingType = ObjectType(details: try await show(writingTypeID, spaceID: spaceID))
        let associations = AnytypeTorahAssociationRepository()
        let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3")
        var documentIDs: [String] = []
        for type in [ObjectTypeUniqueKey.page, .note, writingType.uniqueKey] {
            let document = try await create(type: type, spaceID: spaceID)
            documentIDs.append(document.id)
            _ = try await associations.addAssociation(source.item, target: .object(objectId: document.id), spaceId: spaceID)
        }
        let otherVerse = try await create(type: .page, spaceID: spaceID)
        _ = try await observed("other-verse-association") {
            try await associations.addAssociation(
                T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:4").item,
                target: .object(objectId: otherVerse.id), spaceId: spaceID
            )
        }
        let selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 3:3")
        let session = TorahEditorSession(
            spaceId: spaceID, objectId: try #require(documentIDs.first),
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: associations
        )
        let baseline = Set(documentIDs)
        try await eventually {
            let result = try await observed("initial-index-poll") {
                try await session.repository.relatedDocuments(for: selection, forceRefresh: true)
            }
            return result.documents.count == 3 && Set(result.documents.map(\.objectID)) == baseline
        }
        let initial = try await observed("initial-index-snapshot") {
            try await session.repository.relatedDocuments(for: selection, forceRefresh: true)
        }
        #expect(initial.coverage == .indexedDocumentsOnly)
        #expect(Set(initial.limitations).isSuperset(of: [
            .blockAssociationsNotIndexed, .sourceQuotesNotIndexed, .indexFreshnessUnverified
        ]))
        #expect(initial.documents.allSatisfy { $0.spaceID == spaceID && $0.typeID?.isEmpty == false })
        #expect(!initial.documents.contains { $0.objectID == otherVerse.id })

        var openedID: String?
        session.installOpenObjectHandler { openedID = $0 }
        let addNote = try #require(session.hostActions.onAddNote)
        addNote(selection, {
            print("WAVE1_PHASE add-note-completion-callback utc=\(Date().timeIntervalSince1970) monotonic=\(ProcessInfo.processInfo.systemUptime) cancelled=\(Task.isCancelled)")
        })
        print("WAVE1_PHASE add-note-requested cancelled=\(Task.isCancelled)")
        try await eventually { openedID != nil }
        let noteID = try #require(openedID)
        #expect(!baseline.contains(noteID))
        let noteLinks = try await observed("created-note-associations") {
            try await associations.listDocumentAssociations(objectId: noteID, spaceId: spaceID)
        }
        #expect(noteLinks.contains(where: source.matches))
        try await eventually {
            let result = try await observed("linked-note-index-poll") {
                try await session.repository.relatedDocuments(for: selection, forceRefresh: true)
            }
            return result.documents.count == 4 && Set(result.documents.map(\.objectID)) == baseline.union([noteID])
        }
        let linked = try await observed("linked-note-index-snapshot") {
            try await session.repository.relatedDocuments(for: selection, forceRefresh: true)
        }
        let noteRow = try #require(linked.documents.first { $0.objectID == noteID })
        #expect(noteRow.kind == .note && noteRow.canUnlink)
        openedID = nil
        session.hostActions.onOpenRelatedDocument?(noteRow)
        #expect(openedID == noteID)
        let unlink = try #require(session.hostActions.onUnlinkRelatedDocument)
        unlink(noteRow, selection, {
            print("WAVE1_PHASE unlink-completion-callback utc=\(Date().timeIntervalSince1970) monotonic=\(ProcessInfo.processInfo.systemUptime) cancelled=\(Task.isCancelled)")
        })
        print("WAVE1_PHASE unlink-requested cancelled=\(Task.isCancelled)")
        try await eventually {
            let result = try await observed("unlinked-note-index-poll") {
                try await session.repository.relatedDocuments(for: selection, forceRefresh: true)
            }
            return result.documents.count == 3 && Set(result.documents.map(\.objectID)) == baseline
        }
        let retainedNote = try await observed("retained-note-show") {
            try await show(noteID, spaceID: spaceID)
        }
        #expect(!retainedNote.isDeleted && retainedNote.spaceId == spaceID)
        session.deactivateDocument()
    }

    @MainActor
    private func observed<Value>(_ operation: String, _ body: @MainActor () async throws -> Value) async throws -> Value {
        let started = ProcessInfo.processInfo.systemUptime
        print("WAVE1_PHASE begin=\(operation) utc=\(Date().timeIntervalSince1970) monotonic=\(started) cancelled=\(Task.isCancelled)")
        do {
            let value = try await body()
            print("WAVE1_PHASE end=\(operation) utc=\(Date().timeIntervalSince1970) elapsed=\(ProcessInfo.processInfo.systemUptime - started) cancelled=\(Task.isCancelled)")
            return value
        } catch {
            print("WAVE1_PHASE error=\(operation) type=\(String(reflecting: type(of: error))) utc=\(Date().timeIntervalSince1970) elapsed=\(ProcessInfo.processInfo.systemUptime - started) cancelled=\(Task.isCancelled)")
            throw error
        }
    }

    @MainActor
    private func create(type: ObjectTypeUniqueKey, spaceID: String) async throws -> ObjectDetails {
        do {
            let created = try await Container.shared.objectActionsService().createObject(
                name: "Wave 1 fixture", typeUniqueKey: type,
                shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                spaceId: spaceID, origin: .none, templateId: nil
            )
            print("WAVE1_CREATED_NATIVE_FIXTURE type=\(type.value)")
            return created
        } catch let error as Anytype_Rpc.Object.Create.Response.Error {
            print("WAVE1_NATIVE_CREATE_FAILED type=\(type.value) response=\((try? error.jsonString()) ?? "unavailable")")
            throw error
        }
    }

    private func show(_ id: String, spaceID: String) async throws -> ObjectDetails {
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = id; $0.objectID = id; $0.spaceID = spaceID
        }).invoke()
        return try ObjectDetails(protobufStruct: #require(response.objectView.details.first { $0.id == id }).details)
    }

    @MainActor
    private func eventually(_ predicate: () async throws -> Bool) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            do { if try await predicate() { return } }
            catch T5SpaceRelatedDocumentsError.indexUnavailable { }
            try await observed("eventually-poll-interval") {
                try await Task.sleep(for: .milliseconds(100))
            }
        } while clock.now < deadline
        Issue.record("Disposable native integration did not reach the expected state")
        throw T5SpaceRelatedDocumentsError.indexUnavailable
    }
}
