// Original controller assertions retained, with host-neutral injected test adapters.
#if canImport(SwiftUI)
import Foundation
import PinkhaKit
import Testing
import TorahInspectorCore
@testable import PinkhaTorahPresentation

@Suite("Quote insertion gesture, lifetime and write authority")
@MainActor
struct SharedTorahQuoteInsertionTests {
    private let transfer = TorahSourceTransfer(
        providerID: "sefaria", canonicalRef: "Genesis 3:3", hebrewRef: nil,
        sectionRef: "Genesis 3", text: "Exact provider text", versionTitle: "Fixture",
        license: "CC0", direction: "rtl", retrievedAt: Date(timeIntervalSince1970: 1)
    )

    @Test("A delayed item provider cannot write after leaving and reopening the document")
    func delayedDropDoesNotRegainAuthorityOnReactivation() async throws {
        let fixture = try QuoteInsertionFixture()
        let delayed = fixture.session.makeExternalDropInsertionAction(targetBlockId: "anchor")
        fixture.session.deactivateDocument()
        fixture.session.activateDocument()
        fixture.session.message = "Current document"
        fixture.session.persistenceState = .saved

        await delayed(transfer)

        #expect(fixture.insertedBlocks.isEmpty)
        #expect(await fixture.store.writeCount() == 0)
        #expect(fixture.session.message == "Current document")
        #expect(fixture.session.persistenceState == .saved)
    }

    @Test("A captured Inspector action cannot insert for a replaced or dismissed selection", arguments: [false, true])
    func staleInspectorInsertionIsRejected(dismiss: Bool) async throws {
        let fixture = try QuoteInsertionFixture()
        let selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 3:3")
        fixture.session.openResolvedReferenceFromStandaloneSearch(selection)
        let delayed = fixture.session.makeInspectorSourceInsertionAction()
        if dismiss {
            fixture.session.hostActions.onClose?()
            #expect(fixture.session.selection == nil)
            fixture.session.openResolvedReferenceFromStandaloneSearch(selection)
        } else {
            fixture.session.selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Exodus 1")
        }

        await delayed(transfer)

        #expect(fixture.insertedBlocks.isEmpty)
        #expect(await fixture.store.writeCount() == 0)
    }

    @Test("Revoked edit authority stops insertion before a block is dispatched")
    func deniedDropDoesNotCreateTextOrMetadata() async throws {
        let fixture = try QuoteInsertionFixture()
        let action = fixture.session.makeExternalDropInsertionAction(targetBlockId: "anchor")
        fixture.permitsInsertion = false

        await action(transfer)

        #expect(fixture.insertedBlocks.isEmpty)
        #expect(await fixture.store.writeCount() == 0)
        #expect(fixture.session.persistenceState != .saved)
    }

    @Test("One gesture is claimed once while a later intentional drop of the same payload succeeds")
    func dropDeduplicationIsPerGesture() async throws {
        let fixture = try QuoteInsertionFixture()
        let firstGesture = fixture.session.makeExternalDropInsertionAction(targetBlockId: "anchor")

        await firstGesture(transfer)
        await firstGesture(transfer)
        let secondGesture = fixture.session.makeExternalDropInsertionAction(targetBlockId: "anchor")
        await secondGesture(transfer)

        #expect(fixture.insertedBlocks == ["quote-1", "quote-2"])
        #expect(fixture.insertionTargets == ["anchor", "anchor"])
        #expect(await fixture.store.writeCount() == 2)
        let records = try await fixture.repository.listAssociationRecords(objectId: "document", spaceId: "space")
        #expect(Set(records.compactMap(\.blockId)) == ["quote-1", "quote-2"])
        #expect(records.allSatisfy {
            $0.spaceId == "space" && $0.objectId == "document"
                && $0.item.role == .sourceQuote
                && $0.item.customMetadata?["snapshotText"] == transfer.text
        })
        #expect(fixture.session.persistenceState == .saved)
    }

    @Test("Closing Inspector does not invalidate a drop already addressed to the active document")
    func dropLifetimeIsIndependentOfInspectorPresentation() async throws {
        let fixture = try QuoteInsertionFixture()
        fixture.session.selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 3")
        let action = fixture.session.makeExternalDropInsertionAction(targetBlockId: "anchor")
        fixture.session.hostActions.onClose?()
        #expect(fixture.session.selection == nil)

        await action(transfer)

        #expect(fixture.insertedBlocks.count == 1)
        #expect(await fixture.store.writeCount() == 1)
    }

    @Test("Revocation after block creation preserves text and reports a partial insertion")
    func revocationDuringBlockResponseStopsMetadata() async throws {
        let gate = QuoteInsertionSuspension()
        let fixture = try QuoteInsertionFixture(blockGate: gate)
        let action = fixture.session.makeExternalDropInsertionAction(targetBlockId: "anchor")
        let request = Task { await action(transfer) }
        await gate.waitUntilHeld()
        fixture.permitsInsertion = false
        await gate.release()
        await request.value

        #expect(fixture.insertedBlocks == ["quote-1"])
        #expect(await fixture.store.writeCount() == 0)
        #expect(fixture.session.persistenceState == .uncertain(
            TorahEditorSession.SessionError.partialInsertion.localizedDescription
        ))
    }

    @Test("A block response from a previous document lifetime cannot write metadata or replace new UI state")
    func lateBlockResponseDoesNotMutateTheNewLifetime() async throws {
        let gate = QuoteInsertionSuspension()
        let fixture = try QuoteInsertionFixture(blockGate: gate)
        let action = fixture.session.makeExternalDropInsertionAction(targetBlockId: "anchor")
        let request = Task { await action(transfer) }
        await gate.waitUntilHeld()
        fixture.session.deactivateDocument()
        fixture.session.activateDocument()
        fixture.session.message = "Current document"
        fixture.session.persistenceState = .saved
        await gate.release()
        await request.value

        #expect(fixture.insertedBlocks == ["quote-1"])
        #expect(await fixture.store.writeCount() == 0)
        #expect(fixture.session.message == "Current document")
        #expect(fixture.session.persistenceState == .saved)
    }

    @Test("A replaced Inspector cannot receive a late partial-insertion alert")
    func lateInspectorResponseDoesNotReplaceNewSelectionStatus() async throws {
        let gate = QuoteInsertionSuspension()
        let fixture = try QuoteInsertionFixture(blockGate: gate)
        fixture.session.selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 3")
        let action = fixture.session.makeInspectorSourceInsertionAction()
        let request = Task { await action(transfer) }
        await gate.waitUntilHeld()
        fixture.session.selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Exodus 1")
        fixture.session.message = "New Inspector"
        fixture.session.persistenceState = .saved
        await gate.release()
        await request.value

        #expect(await fixture.store.writeCount() == 0)
        #expect(fixture.session.message == "New Inspector")
        #expect(fixture.session.persistenceState == .saved)
    }

    @Test("Revocation or caller cancellation during the repository's native read stops its queued write", arguments: [false, true])
    func metadataWriteRevalidatesAfterSuspendedNativeRead(cancel: Bool) async throws {
        let gate = QuoteInsertionSuspension()
        let fixture = try QuoteInsertionFixture(readGate: gate)
        let action = fixture.session.makeExternalDropInsertionAction(targetBlockId: "anchor")
        let request = Task { await action(transfer) }
        await gate.waitUntilHeld()
        if cancel {
            request.cancel()
        } else {
            fixture.permitsInsertion = false
        }
        await gate.release()
        await request.value

        #expect(fixture.insertedBlocks == ["quote-1"])
        #expect(await fixture.store.writeCount() == 0)
        #expect(fixture.session.persistenceState == .uncertain(
            TorahEditorSession.SessionError.partialInsertion.localizedDescription
        ))
    }

    @Test("A completed quote keeps its canonical source and exact editable text")
    func inspectorInsertionPersistsConfirmedCanonicalMetadata() async throws {
        let fixture = try QuoteInsertionFixture()
        fixture.session.selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 3")
        await fixture.session.makeInspectorSourceInsertionAction()(transfer)

        let records = try await fixture.repository.listAssociationRecords(objectId: "document", spaceId: "space")
        let record = try #require(records.first)
        #expect(records.count == 1)
        #expect(record.blockId == "quote-1")
        #expect(record.item.canonicalKey == transfer.canonicalRef)
        #expect(record.item.providerID == transfer.providerID)
        #expect(record.item.customMetadata?["snapshotText"] == transfer.text)
        #expect(fixture.session.persistenceState == .saved)
    }
}


@MainActor
private final class QuoteInsertionFixture {
    let store: QuoteInsertionRepository
    var repository: QuoteInsertionRepository { store }
    let session: TorahEditorSession
    var permitsInsertion = true
    var insertedBlocks: [String] = []
    var insertionTargets: [String?] = []

    init(blockGate: QuoteInsertionSuspension? = nil, readGate: QuoteInsertionSuspension? = nil) throws {
        store = QuoteInsertionRepository(readGate: readGate)
        session = TorahEditorSession(
            spaceId: "space", objectId: "document",
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: store,
            notesService: NoNotesFixture()
        )
        session.installInsertionEditingPolicy { [weak self] in self?.permitsInsertion == true }
        session.installInsertionHandler { [weak self] _, targetBlockID in
            guard let self else { throw CancellationError() }
            let blockID = "quote-\(insertedBlocks.count + 1)"
            insertedBlocks.append(blockID)
            insertionTargets.append(targetBlockID)
            if let blockGate { await blockGate.hold() }
            return blockID
        }
    }
}

private actor QuoteInsertionSuspension {
    private var held = false
    private var waiter: CheckedContinuation<Void, Never>?
    private var continuation: CheckedContinuation<Void, Never>?
    func hold() async {
        await withCheckedContinuation {
            continuation = $0; held = true; waiter?.resume(); waiter = nil
        }
    }
    func waitUntilHeld() async {
        if held { return }
        await withCheckedContinuation { waiter = $0 }
    }
    func release() { continuation?.resume(); continuation = nil }
}

/// This is a UI-controller unit fixture, not native persistence evidence.
private actor QuoteInsertionRepository: TorahAssociationSnapshotRepository {
    private let readGate: QuoteInsertionSuspension?
    private var writes = 0
    private var didHold = false
    private var records: [TorahStoredAssociationRecord] = []
    init(readGate: QuoteInsertionSuspension?) { self.readGate = readGate }
    func writeCount() -> Int { writes }

    func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord] {
        records.filter { $0.spaceId == spaceId && $0.objectId == objectId }
    }
    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        records.filter { $0.spaceId == spaceId && $0.objectId == objectId && $0.blockId == nil }.map(\.item)
    }
    func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        records.filter { $0.spaceId == spaceId && $0.objectId == objectId && $0.blockId == blockId }.map(\.item)
    }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String,
                        authorize: @escaping TorahAssociationWriteAuthorization) async throws -> TorahAssociationItem {
        if !didHold, let readGate { didHold = true; await readGate.hold() }
        try Task.checkCancellation()
        try await authorize()
        records.append(TorahStoredAssociationRecord(location: .init(spaceId: spaceId, target: target), item: item))
        writes += 1
        return item
    }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        try await addAssociation(item, target: target, spaceId: spaceId, authorize: {})
    }
    func upsertAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        try await addAssociation(item, target: target, spaceId: spaceId)
    }
    func updateAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        try await addAssociation(item, target: target, spaceId: spaceId)
    }
    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String) async throws {
        records.removeAll { $0.spaceId == spaceId && $0.location.target == target && $0.item.id == associationId }
    }
}

@MainActor
private final class NoNotesFixture: TorahEditorNotesService {
    func notes(for selection: TorahInspectorSelection) async throws -> [TorahInspectorNote] { [] }
    func relatedDocuments(for selection: TorahInspectorSelection) async throws -> TorahRelatedDocumentsSnapshot { .unavailable }
    func createNote(for selection: TorahInspectorSelection, authorize: @escaping TorahAssociationWriteAuthorization) async throws -> T5NoteCreationOutcome { throw CancellationError() }
    func noteObjectId(noteId: String, for selection: TorahInspectorSelection) async throws -> String? { nil }
    func unlink(noteId: String, for selection: TorahInspectorSelection, authorize: @escaping TorahAssociationWriteAuthorization) async throws { throw CancellationError() }
    func unlink(document: TorahRelatedDocument, for selection: TorahInspectorSelection, authorize: @escaping TorahAssociationWriteAuthorization) async throws { throw CancellationError() }
}

#endif
