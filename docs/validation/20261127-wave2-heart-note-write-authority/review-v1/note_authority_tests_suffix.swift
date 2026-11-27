
// These tests exercise the actual Heart service and canonical repository. Only
// the native store and the unrelated object/block creation services are controlled.
// Select this suite alone: .serialized does not serialize unrelated test suites.
import Factory
import AnytypeCore
import ProtobufMessages
import protocol PinkhaTorahPresentation.TorahEditorNotesService

@Suite("Heart Note repository dispatch authority", .serialized)
@MainActor
struct TorahNoteRepositoryAuthorityTests {
    enum CreationPhase: String, CaseIterable, Sendable { case source, origin }
    enum UnlinkPhase: String, CaseIterable, Sendable { case noteSource, noteOrigin, related }
    enum Retirement: String, CaseIterable, Sendable { case inspectorReopen, documentReopen }

    @Test("Create-note metadata rechecks the original presentation after the repository read",
          arguments: CreationPhase.allCases, Retirement.allCases)
    func noteCreationRejectsRetiredRepositoryDispatch(
        phase: CreationPhase, retirement: Retirement
    ) async throws {
        let fixture = try HeartNoteAuthorityFixture(
            seededNote: false, heldObjectID: phase == .source ? "note" : "origin", heldRead: 1)
        let protectedBefore = try await fixture.store.protectedRecords()
        fixture.startCreation()
        do {
            try await fixture.store.waitUntilHeld()
            let beforeRetirement = await fixture.store.rawValues()
            let writesBeforeRetirement = await fixture.store.writtenObjects()
            #expect(writesBeforeRetirement == (phase == .source ? [] : ["note"]))
            fixture.retire(retirement)
            await fixture.store.release()
            try await fixture.waitForCreationCompletion(1)

            // A successful earlier phase remains intact; this is not rollback.
            #expect(await fixture.store.rawValues() == beforeRetirement)
            #expect(await fixture.store.writtenObjects() == writesBeforeRetirement)
            #expect(fixture.didChange == 0)
            #expect(fixture.opened.isEmpty)
            #expect(fixture.session.message == HeartNoteAuthorityFixture.currentMessage)
            #expect(fixture.observedNotes.lastCreationRecoveryError is CancellationError)
            let partial = await fixture.services.counts()
            #expect(partial.created == 1 && partial.deleted == 0)
            #expect(partial.lines == (phase == .source ? 0 : 1))

            // A deliberate current action resumes the original pending Note.
            fixture.startCreation()
            try await fixture.waitForCreationCompletion(2)
            try await fixture.waitForOpenedNote()
            #expect(fixture.didChange == 1)
            #expect(fixture.opened == ["note"])
            #expect(fixture.openedBlocks == [nil])
            #expect(fixture.observedNotes.lastCreationRecoveryError == nil)
            let completed = await fixture.services.counts()
            #expect(completed.created == 1 && completed.lines == 1 && completed.deleted == 0)
            let note = try await fixture.repository.listDocumentAssociations(objectId: "note", spaceId: "space")
            let origin = try await fixture.repository.listDocumentAssociations(objectId: "origin", spaceId: "space")
            #expect(note.filter(fixture.source.matches).count == 1)
            #expect(origin.filter { $0.customMetadata?["anytypeNoteObjectId"] == "note" &&
                $0.customMetadata?["torahSelectionId"] == fixture.selection.id }.count == 1)
            #expect(try await fixture.store.protectedRecords() == protectedBefore)
        } catch {
            // Retire first, then release the only controlled suspension. The
            // observed real service completion bounds the unstructured UI action.
            fixture.session.deactivateDocument()
            await fixture.store.release()
            try? await fixture.waitForCreationCompletion(1)
            throw error
        }
    }

    @Test("Note and related-document unlink recheck authority inside their canonical write",
          arguments: UnlinkPhase.allCases, Retirement.allCases)
    func unlinkRejectsRetiredRepositoryDispatch(
        phase: UnlinkPhase, retirement: Retirement
    ) async throws {
        let fixture = try HeartNoteAuthorityFixture(
            seededNote: true, heldObjectID: phase == .noteOrigin ? "origin" : "note", heldRead: 2)
        let protectedBefore = try await fixture.store.protectedRecords()
        let request = Task { @MainActor in await fixture.unlink(phase) }
        do {
            try await fixture.store.waitUntilHeld()
            let beforeRetirement = await fixture.store.rawValues()
            let writesBeforeRetirement = await fixture.store.writtenObjects()
            #expect(writesBeforeRetirement == (phase == .noteOrigin ? ["note"] : []))
            fixture.retire(retirement)
            await fixture.store.release()
            await request.value

            #expect(await fixture.store.rawValues() == beforeRetirement)
            #expect(await fixture.store.writtenObjects() == writesBeforeRetirement)
            #expect(fixture.didChange == 0)
            #expect(fixture.session.message == HeartNoteAuthorityFixture.currentMessage)
            #expect(try await fixture.store.protectedRecords() == protectedBefore)

            // The current retry completes only the remaining selected links.
            await fixture.unlink(phase)
            #expect(fixture.didChange == 1)
            let note = try await fixture.repository.listDocumentAssociations(objectId: "note", spaceId: "space")
            let origin = try await fixture.repository.listDocumentAssociations(objectId: "origin", spaceId: "space")
            #expect(!note.contains(where: fixture.source.matches))
            #expect(origin.contains { $0.id == "origin-note" } == (phase == .related))
            #expect(try await fixture.store.protectedRecords() == protectedBefore)
            let counts = await fixture.services.counts()
            #expect(counts.created == 0 && counts.lines == 0 && counts.deleted == 0)
        } catch {
            request.cancel()
            fixture.session.deactivateDocument()
            await fixture.store.release()
            await request.value
            throw error
        }
    }
}

@MainActor
private final class HeartNoteAuthorityFixture {
    static let currentMessage = "Current reopened presentation"
    let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3")
    let selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 3:3")
    let store: HeartNoteAuthorityStore
    let repository: AnytypeTorahAssociationRepository
    let services: HeartNoteCreationServices
    let observedNotes: HeartNoteObservedService
    let session: TorahEditorSession
    var didChange = 0
    var opened: [String] = []
    var openedBlocks: [String?] = []

    init(seededNote: Bool, heldObjectID: String, heldRead: Int) throws {
        let services = HeartNoteCreationServices()
        self.services = services
        let store = try HeartNoteAuthorityStore(
            seededNote: seededNote, selectionID: selection.id,
            heldObjectID: heldObjectID, heldRead: heldRead)
        self.store = store
        let repository = AnytypeTorahAssociationRepository(
            nativeStore: store, manifestProvider: ManifestProbe(spaceId: "space"),
            coordinator: TorahAssociationMutationCoordinator(),
            statusCenter: TorahAssociationPersistenceStatusCenter())
        self.repository = repository
        // Exact pinned Factory 2.3.1 resolves @Injected eagerly. Restore the
        // complete prior registration/cache state before the first await.
        let service: AnytypeTorahNotesService = {
            Container.shared.manager.push()
            defer { Container.shared.manager.pop() }
            Container.shared.objectActionsService.register { services }
            Container.shared.blockService.register { services }
            return AnytypeTorahNotesService(spaceId: "space", objectId: "origin", associations: repository)
        }()
        observedNotes = HeartNoteObservedService(service)
        session = TorahEditorSession(spaceId: "space", objectId: "origin",
            workspace: try AnytypeTorahWorkspace.sefaria(), associations: repository,
            notesService: observedNotes)
        session.installOpenObjectHandler { [weak self] object, block in
            self?.opened.append(object); self?.openedBlocks.append(block)
        }
        session.openResolvedReferenceFromStandaloneSearch(selection)
    }

    func retire(_ kind: TorahNoteRepositoryAuthorityTests.Retirement) {
        switch kind {
        case .inspectorReopen: session.hostActions.onClose?()
        case .documentReopen:
            session.deactivateDocument()
            session.activateDocument()
        }
        session.openResolvedReferenceFromStandaloneSearch(selection)
        session.message = Self.currentMessage
    }

    func startCreation() {
        guard let action = session.hostActions.onAddNote else {
            Issue.record("The original Add Note action is missing"); return
        }
        action(selection) { [weak self] in self?.didChange += 1 }
    }

    func waitForCreationCompletion(_ count: Int) async throws {
        let clock = ContinuousClock()
        let end = clock.now.advanced(by: .seconds(3))
        while observedNotes.creationsCompleted < count {
            guard clock.now < end else { throw HeartNoteAuthorityFailure.deadline }
            try await Task.sleep(for: .milliseconds(5))
        }
    }

    func waitForOpenedNote() async throws {
        let clock = ContinuousClock()
        let end = clock.now.advanced(by: .seconds(3))
        while opened.isEmpty {
            guard clock.now < end else { throw HeartNoteAuthorityFailure.deadline }
            try await Task.sleep(for: .milliseconds(5))
        }
    }

    func unlink(_ phase: TorahNoteRepositoryAuthorityTests.UnlinkPhase) async {
        if phase == .related {
            let row = TorahRelatedDocument(id: "related-note", spaceID: "space", objectID: "note",
                title: "Note", sourceReference: source.canonicalReference, canUnlink: true)
            await session.unlink(document: row, for: selection) { [weak self] in self?.didChange += 1 }
        } else {
            let note = TorahInspectorNote(id: "origin-note", selectedText: source.canonicalReference,
                                           note: "Note", tag: "Anytype")
            await session.unlink(note: note, for: selection) { [weak self] in self?.didChange += 1 }
        }
    }
}

// This observer delegates every operation to the production Heart service. Its
// counter only permits the test to await the original UI action's service call.
@MainActor
private final class HeartNoteObservedService: TorahEditorNotesService {
    let original: AnytypeTorahNotesService
    var creationsCompleted = 0
    var lastCreationRecoveryError: (any Error)?
    init(_ original: AnytypeTorahNotesService) { self.original = original }
    func notes(for selection: TorahInspectorSelection) async throws -> [TorahInspectorNote] {
        try await original.notes(for: selection)
    }
    func relatedDocuments(for selection: TorahInspectorSelection) async throws -> TorahRelatedDocumentsSnapshot {
        try await original.relatedDocuments(for: selection)
    }
    func createNote(for selection: TorahInspectorSelection,
                    authorize: @escaping TorahAssociationWriteAuthorization) async throws -> T5NoteCreationOutcome {
        defer { creationsCompleted += 1 }
        let outcome = try await original.createNote(for: selection, authorize: authorize)
        lastCreationRecoveryError = outcome.recoveryError
        return outcome
    }
    func noteObjectId(noteId: String, for selection: TorahInspectorSelection) async throws -> String? {
        try await original.noteObjectId(noteId: noteId, for: selection)
    }
    func unlink(noteId: String, for selection: TorahInspectorSelection,
                authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        try await original.unlink(noteId: noteId, for: selection, authorize: authorize)
    }
    func unlink(document: TorahRelatedDocument, for selection: TorahInspectorSelection,
                authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        try await original.unlink(document: document, for: selection, authorize: authorize)
    }
}

private enum HeartNoteAuthorityFailure: Error { case deadline, unexpectedCall, invalidFixture }

private actor HeartNoteAuthorityStore: TorahAssociationNativeStore {
    private var values: [String: String] = [:]
    private var reads: [String: Int] = [:]
    private var writes: [String] = []
    private let heldObjectID: String
    private let heldRead: Int
    private var held = false
    private var released = false
    private var continuation: CheckedContinuation<Void, Never>?

    init(seededNote: Bool, selectionID: String, heldObjectID: String, heldRead: Int) throws {
        self.heldObjectID = heldObjectID; self.heldRead = heldRead
        let codec = TorahAssociationPayloadCodec()
        for objectID in ["origin", "note"] {
            let location = TorahAssociationLocation(spaceId: "space", target: .object(objectId: objectID))
            let anchor = try PinkhaSemanticTextAnchor(spaceID: "space", objectID: objectID)
            var kept = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Exodus 1:1").item
            kept.id = "keep-semantic-" + objectID
            kept = try TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: kept, location: location)
            var quote = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3").item
            quote.id = "keep-quote-" + objectID; quote.role = .sourceQuote
            quote.customMetadata = ["snapshotText": "Original quoted text"]
            var records = [TorahStoredAssociationRecord(location: location, item: kept),
                TorahStoredAssociationRecord(location: .init(spaceId: "space",
                    target: .block(objectId: objectID, blockId: "quote-block")), item: quote)]
            if seededNote {
                let item: TorahAssociationItem
                if objectID == "note" {
                    var source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3").item
                    source.id = "selected-source"; item = source
                } else {
                    item = TorahAssociationItem(id: "origin-note", kind: .ref, role: .context,
                        providerID: "sefaria", externalID: "note", canonicalKey: "anytype-note:note",
                        labelHe: "Note", customMetadata: ["anytypeNoteObjectId": "note", "torahSelectionId": selectionID])
                }
                records.append(.init(location: location, item: item))
            }
            let data = try codec.encodeCanonicalDocument(.init(records: records,
                unknownFields: ["unrelated-native-field": .string("preserved-" + objectID)]))
            guard let raw = String(data: data, encoding: .utf8) else { throw HeartNoteAuthorityFailure.invalidFixture }
            values[objectID] = raw
        }
    }

    func readDocument(spaceId: String, objectId: String,
                      propertyKey: String) async throws -> TorahAssociationNativeDocumentSnapshot {
        guard spaceId == "space", propertyKey == "pinkha-associations", let value = values[objectId] else {
            throw HeartNoteAuthorityFailure.invalidFixture
        }
        reads[objectId, default: 0] += 1
        if objectId == heldObjectID, reads[objectId] == heldRead {
            held = true
            if !released { await withCheckedContinuation { continuation = $0 } }
            // Intentionally non-cooperative: the real repository must perform
            // its original post-read caller-authorization check.
        }
        return .init(spaceId: "space", objectId: objectId, isDeleted: false, isArchived: false,
            canWriteDetails: true, blockIds: ["quote-block"], propertyValue: value)
    }

    func writeDocumentProperty(objectId: String, propertyKey: String, value: String) throws {
        guard values[objectId] != nil, propertyKey == "pinkha-associations" else {
            throw HeartNoteAuthorityFailure.invalidFixture
        }
        writes.append(objectId); values[objectId] = value
    }
    func rawValues() -> [String: Data] { values.mapValues { Data($0.utf8) } }
    func writtenObjects() -> [String] { writes }
    func release() { released = true; continuation?.resume(); continuation = nil }
    func waitUntilHeld() async throws {
        let clock = ContinuousClock()
        let end = clock.now.advanced(by: .seconds(3))
        while !held {
            guard clock.now < end else { throw HeartNoteAuthorityFailure.deadline }
            try await Task.sleep(for: .milliseconds(5))
        }
    }
    func protectedRecords() throws -> [String: Data] {
        let codec = TorahAssociationPayloadCodec()
        var result: [String: Data] = [:]
        for (objectID, raw) in values {
            let payload = try codec.decodeCanonicalDocument(raw,
                legacyLocation: .init(spaceId: "space", target: .object(objectId: objectID)))
            result[objectID] = try codec.encodeCanonicalDocument(.init(
                records: payload.records.filter { $0.item.id.hasPrefix("keep-") },
                unknownFields: payload.unknownFields))
        }
        return result
    }
}

// The production service still chooses .note and invokes the original source
// line phase. No native object/HTTP/engine acceptance is inferred from this stub.
private actor HeartNoteCreationServices: ObjectActionsServiceProtocol, BlockServiceProtocol {
    struct Counts: Sendable { let created: Int; let lines: Int; let deleted: Int }
    private var created = 0
    private var lines = 0
    private var deleted = 0
    func counts() -> Counts { .init(created: created, lines: lines, deleted: deleted) }
    func createObject(name: String, typeUniqueKey: ObjectTypeUniqueKey,
        shouldDeleteEmptyObject: Bool, shouldSelectType: Bool, shouldSelectTemplate: Bool,
        spaceId: String, origin: ObjectOrigin, templateId: String?, createdInContext: String,
        createdInContextRef: String, additionalDetails: [BundledDetails]) async throws -> ObjectDetails {
        guard typeUniqueKey == .note, spaceId == "space", !shouldDeleteEmptyObject,
              !shouldSelectType, !shouldSelectTemplate, templateId == nil,
              createdInContext.isEmpty, createdInContextRef.isEmpty, additionalDetails.isEmpty else {
            throw HeartNoteAuthorityFailure.unexpectedCall
        }
        created += 1
        return ObjectDetails(id: "note", values: [BundledPropertyKey.name.rawValue: name.protobufValue])
    }
    func lastBlockId(from objectId: String, spaceId: String) async throws -> String {
        guard objectId == "note", spaceId == "space" else { throw HeartNoteAuthorityFailure.unexpectedCall }
        return "note-header"
    }
    func add(contextId: String, targetId: String, info: BlockInformation, position: BlockPosition) async throws -> String {
        guard contextId == "note", targetId == "note-header", position == .bottom else {
            throw HeartNoteAuthorityFailure.unexpectedCall
        }
        lines += 1; return "note-source-line"
    }
    func delete(objectIds: [String]) async throws { deleted += 1; throw HeartNoteAuthorityFailure.unexpectedCall }
    func setArchive(objectIds: [String], _ isArchived: Bool) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setPin(objectIds: [String], _ isPinned: Bool) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setLocked(_ isLocked: Bool, objectId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func updateLayout(contextID: String, value: Int) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func duplicate(objectId: String) async throws -> String { throw HeartNoteAuthorityFailure.unexpectedCall }
    func applyTemplate(objectId: String, templateId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func updateBundledDetails(contextID: String, details: [BundledDetails]) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func updateDetails(contextId: String, relationKey: String, value: DataviewGroupValue) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setInternalFlags(contextId: String, internalFlags: [Int]) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func addObjectsToCollection(contextId: String, objectIds: [String]) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setObjectType(objectId: String, typeUniqueKey: ObjectTypeUniqueKey) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setObjectSetType(objectId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setObjectCollectionType(objectId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setSource(objectId: String, source: [String]) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func undo(objectId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func redo(objectId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func move(dashboadId: String, blockId: String, dropPositionblockId: String, position: Anytype_Model_Block.Position) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func createSet(name: String, iconEmoji: Emoji?, setOfObjectType: String, spaceId: String) async throws -> ObjectDetails { throw HeartNoteAuthorityFailure.unexpectedCall }
    func addFirstBlock(contextId: String, info: BlockInformation) async throws -> String { throw HeartNoteAuthorityFailure.unexpectedCall }
    func delete(contextId: String, blockIds: [String]) async throws { deleted += 1; throw HeartNoteAuthorityFailure.unexpectedCall }
    func duplicate(contextId: String, targetId: String, blockIds: [String], position: BlockPosition) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func move(contextId: String, blockIds: [String], targetContextID: String, dropTargetID: String, position: BlockPosition) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setAlign(objectId: String, blockIds: [String], alignment: LayoutAlignment) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setBackgroundColor(objectId: String, blockIds: [String], color: MiddlewareColor) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setFields(objectId: String, blockId: String, fields: BlockFields) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setBlockColor(objectId: String, blockIds: [String], color: MiddlewareColor) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func replace(objectId: String, blockIds: [String], targetId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func replaceBlock(contextId: String, blockId: String, info: BlockInformation) async throws -> String { throw HeartNoteAuthorityFailure.unexpectedCall }
    func move(objectId: String, blockId: String, targetId: String, position: Anytype_Model_Block.Position) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func moveToPage(objectId: String, blockIds: [String], pageId: String) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func setLinkAppearance(objectId: String, blockIds: [String], appearance: BlockLink.Appearance) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func changeMarkup(objectId: String, blockIds: [String], markType: MarkupType) async throws { throw HeartNoteAuthorityFailure.unexpectedCall }
    func convertChildrenToObjects(contextId: String, blocksIds: [String], typeUniqueKey: ObjectTypeUniqueKey, templateId: String) async throws -> [String] { throw HeartNoteAuthorityFailure.unexpectedCall }
    func createBlockLink(contextId: String, targetId: String, spaceId: String, details: [BundledDetails], typeUniqueKey: ObjectTypeUniqueKey, position: BlockPosition, templateId: String) async throws -> String { throw HeartNoteAuthorityFailure.unexpectedCall }
}
