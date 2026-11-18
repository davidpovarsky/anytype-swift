import Foundation
import PinkhaKit
import Testing
import TorahInspectorCore
@testable import Anytype

@Suite("Quote insertion gesture, lifetime and write authority")
@MainActor
struct TorahQuoteInsertionTests {
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
            fixture.session.inspectorDidDismiss()
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
                && $0.item.customMetadata["snapshotText"] == transfer.text
        })
        #expect(fixture.session.persistenceState == .saved)
    }

    @Test("Closing Inspector does not invalidate a drop already addressed to the active document")
    func dropLifetimeIsIndependentOfInspectorPresentation() async throws {
        let fixture = try QuoteInsertionFixture()
        fixture.session.selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 3")
        let action = fixture.session.makeExternalDropInsertionAction(targetBlockId: "anchor")
        fixture.session.inspectorDidDismiss()

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
        #expect(record.item.customMetadata["snapshotText"] == transfer.text)
        #expect(fixture.session.persistenceState == .saved)
    }
}

@MainActor
private final class QuoteInsertionFixture {
    let store: QuoteInsertionStore
    let repository: AnytypeTorahAssociationRepository
    let session: TorahEditorSession
    var permitsInsertion = true
    var insertedBlocks: [String] = []
    var insertionTargets: [String?] = []

    init(blockGate: QuoteInsertionSuspension? = nil, readGate: QuoteInsertionSuspension? = nil) throws {
        store = QuoteInsertionStore(readGate: readGate)
        repository = AnytypeTorahAssociationRepository(
            nativeStore: store, manifestProvider: QuoteInsertionManifest(),
            coordinator: TorahAssociationMutationCoordinator(),
            statusCenter: TorahAssociationPersistenceStatusCenter()
        )
        session = TorahEditorSession(
            spaceId: "space", objectId: "document",
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: repository
        )
        session.installInsertionEditingPolicy { [weak self] in self?.permitsInsertion == true }
        session.installInsertionHandler { [weak self] _, targetBlockID in
            guard let self else { throw CancellationError() }
            let blockID = "quote-\(insertedBlocks.count + 1)"
            insertedBlocks.append(blockID)
            insertionTargets.append(targetBlockID)
            await store.registerBlock(blockID)
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
            continuation = $0
            held = true
            waiter?.resume()
            waiter = nil
        }
    }

    func waitUntilHeld() async {
        if held { return }
        await withCheckedContinuation { waiter = $0 }
    }

    func release() {
        continuation?.resume()
        continuation = nil
    }
}

private actor QuoteInsertionStore: TorahAssociationNativeStore {
    private let readGate: QuoteInsertionSuspension?
    private var reads = 0
    private var writes = 0
    private var blocks: Set<String> = ["anchor"]
    private var value: String?

    init(readGate: QuoteInsertionSuspension?) { self.readGate = readGate }

    func registerBlock(_ id: String) { blocks.insert(id) }
    func writeCount() -> Int { writes }

    func readDocument(spaceId: String, objectId: String, propertyKey: String) async throws -> TorahAssociationNativeDocumentSnapshot {
        reads += 1
        let snapshot = TorahAssociationNativeDocumentSnapshot(
            spaceId: spaceId, objectId: objectId, isDeleted: false, isArchived: false,
            canWriteDetails: true, blockIds: blocks, propertyValue: value
        )
        if reads == 1, let readGate { await readGate.hold() }
        return snapshot
    }

    func writeDocumentProperty(objectId: String, propertyKey: String, value: String) async throws {
        writes += 1
        self.value = value
    }
}

private struct QuoteInsertionManifest: TorahAssociationManifestProvider {
    func manifest(spaceId: String) async throws -> PinkhaSpaceManifest {
        PinkhaSpaceManifest(
            spaceId: spaceId,
            documentAssociationsPropertyId: "canonical-id",
            documentAssociationsPropertyKey: "canonical-key",
            registeredDocumentTypes: [:]
        )
    }
}
