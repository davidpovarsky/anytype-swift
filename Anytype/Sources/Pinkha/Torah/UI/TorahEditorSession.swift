import Foundation
import Observation
import PinkhaKit
import TorahInspectorCore
import TorahInspectorUI

@MainActor
@Observable
final class TorahEditorSession {
    enum SearchScope: String, CaseIterable, Identifiable, Hashable {
        case references
        case topics
        case words

        var id: Self { self }

        var title: String {
            switch self {
            case .references: "מקורות"
            case .topics: "נושאים"
            case .words: "מילים"
            }
        }
    }

    struct SearchResult: Identifiable, Hashable {
        let id: String
        let scope: SearchScope
        let providerValue: String
        let title: String
        let subtitle: String?
    }

    enum SessionError: LocalizedError {
        case mutationLocked
        case insertionUnavailable
        case staleDocument
        case noResolvedWord
        case partialInsertion

        var errorDescription: String? {
            switch self {
            case .mutationLocked:
                "כתיבה חסומה. יש להפעיל מצב ניסוי למסמך חד־פעמי חדש."
            case .insertionUnavailable:
                "העורך אינו מוכן עדיין להכנסת מקור."
            case .staleDocument:
                "יעד המסמך השתנה. הפעולה בוטלה ללא כתיבה."
            case .noResolvedWord:
                "לא נמצא ערך מילוני מתאים."
            case .partialInsertion:
                "הציטוט נוסף, אך שיוך המקור לא נשמר. אין לבצע ניסיון עיוור נוסף."
            }
        }
    }

    let spaceId: String
    let objectId: String
    let workspace: AnytypeTorahWorkspace
    let repository: TorahInspectorRepository

    var selection: TorahInspectorSelection?
    var selectedTool: TorahStudyTool = .commentaries
    var selectedDetent: TorahInspectorSheetDetent = .medium
    var isSearchPresented = false
    var searchScope: SearchScope = .references
    var searchQuery = ""
    var searchResults: [SearchResult] = []
    var isSearching = false
    var mutationOptIn = false
    var message: String?
    var associationTargetBlockId: String?
    var currentAssociations: [TorahAssociationItem] = []
    var persistenceState: TorahAssociationPersistenceState?

    private let associations: AnytypeTorahAssociationRepository
    private let notesService: AnytypeTorahNotesService
    private var insertionHandler: ((TorahSourceTransfer, String?) async throws -> String)?
    private var claimedDropIDs = Set<String>()
    private var openObjectHandler: ((String) -> Void)?

    init(spaceId: String, objectId: String) throws {
        let workspace = try AnytypeTorahWorkspace.sefaria()
        let associations = AnytypeTorahAssociationRepository()
        let notesService = AnytypeTorahNotesService(
            spaceId: spaceId,
            objectId: objectId,
            associations: associations
        )

        self.spaceId = spaceId
        self.objectId = objectId
        self.workspace = workspace
        self.associations = associations
        self.notesService = notesService
        self.repository = TorahInspectorRepositoryFactory.make(
            workspace: workspace,
            notesFetcher: { [notesService] selection in
                try await notesService.notes(for: selection)
            }
        )
    }

    var hostActions: TorahInspectorHostActions {
        TorahInspectorHostActions(
            onClose: { [weak self] in self?.selection = nil },
            onInsertSegment: { [weak self] transfer in
                Task { @MainActor in
                    await self?.insert(transfer, targetBlockId: nil)
                }
            },
            onOpenInNewTab: nil,
            onAddNote: { [weak self] selection, didChange in
                Task { @MainActor in
                    await self?.addNote(for: selection, didChange: didChange)
                }
            },
            onOpenNote: { [weak self] note, selection, _ in
                Task { @MainActor in
                    await self?.open(note: note, for: selection)
                }
            },
            onDeleteNote: { [weak self] note, selection, didChange in
                Task { @MainActor in
                    await self?.unlink(note: note, for: selection, didChange: didChange)
                }
            },
            showsCloseButton: true
        )
    }

    func installInsertionHandler(
        _ handler: @escaping (TorahSourceTransfer, String?) async throws -> String
    ) {
        insertionHandler = handler
    }

    func installOpenObjectHandler(_ handler: @escaping (String) -> Void) {
        openObjectHandler = handler
    }

    func enableMutations(
        disposableSpaceConfirmed: Bool,
        freshDocumentConfirmed: Bool,
        confirmation: String
    ) {
        mutationOptIn = TorahEditorSafetyPolicy.mutationIsAuthorized(
            disposableSpaceConfirmed: disposableSpaceConfirmed,
            freshDocumentConfirmed: freshDocumentConfirmed,
            confirmation: confirmation
        )
        if !mutationOptIn {
            message = SessionError.mutationLocked.localizedDescription
        }
    }

    func disableMutations() {
        mutationOptIn = false
    }

    func presentSearch(targetBlockId: String?) {
        associationTargetBlockId = targetBlockId
        isSearchPresented = true
        Task { await refreshAssociations() }
    }

    func refreshAssociations() async {
        do {
            if let associationTargetBlockId {
                currentAssociations = try await associations.listBlockAssociations(
                    objectId: objectId,
                    blockId: associationTargetBlockId,
                    spaceId: spaceId
                )
            } else {
                currentAssociations = try await associations.listDocumentAssociations(
                    objectId: objectId,
                    spaceId: spaceId
                )
            }
        } catch {
            currentAssociations = []
            message = error.localizedDescription
        }
    }

    func unlinkAssociation(_ item: TorahAssociationItem) async {
        guard mutationOptIn else {
            message = SessionError.mutationLocked.localizedDescription
            return
        }
        persistenceState = .waiting
        do {
            persistenceState = .saving
            try await associations.removeAssociation(
                associationId: item.id,
                target: associationTargetBlockId.map {
                    .block(objectId: objectId, blockId: $0)
                } ?? .object(objectId: objectId),
                spaceId: spaceId
            )
            persistenceState = .saved
            await refreshAssociations()
        } catch let error as TorahAssociationRepositoryError {
            persistenceState = persistenceState(for: error)
            message = error.localizedDescription
        } catch {
            persistenceState = .error(error.localizedDescription)
            message = error.localizedDescription
        }
    }

    func openAssociation(_ item: TorahAssociationItem) {
        guard canOpenAssociation(item) else { return }
        selection = TorahInspectorSelection(
            providerID: item.providerID,
            canonicalRef: item.canonicalKey
        )
        selectedDetent = .medium
        isSearchPresented = false
    }

    func canOpenAssociation(_ item: TorahAssociationItem) -> Bool {
        guard case .ref = item.kind else { return false }
        return !item.canonicalKey.hasPrefix("anytype-note:") && !item.canonicalKey.isEmpty
    }

    func performSearch() async {
        let query = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard query.count >= 2 else {
            searchResults = []
            return
        }

        isSearching = true
        defer { isSearching = false }

        do {
            switch searchScope {
            case .references:
                searchResults = try await workspace.suggestReferences(query).map {
                    SearchResult(
                        id: "reference:\($0.id)",
                        scope: .references,
                        providerValue: $0.id,
                        title: $0.label,
                        subtitle: nil
                    )
                }
            case .topics:
                searchResults = try await workspace.suggestTopics(query).map {
                    SearchResult(
                        id: "topic:\($0.id)",
                        scope: .topics,
                        providerValue: $0.id,
                        title: $0.displayTitle,
                        subtitle: $0.labelEn
                    )
                }
            case .words:
                searchResults = try await workspace.suggestWords(query).map {
                    SearchResult(
                        id: "word:\($0.id)",
                        scope: .words,
                        providerValue: $0.surface,
                        title: $0.headword,
                        subtitle: $0.description ?? $0.lexicon
                    )
                }
            }
        } catch is CancellationError {
        } catch {
            searchResults = []
            message = error.localizedDescription
        }
    }

    func openReference(_ result: SearchResult) async {
        guard result.scope == .references else { return }
        do {
            let resolved = try await workspace.resolveReference(result.providerValue)
            let canonical = resolved.isEmbeddableSource
                ? resolved.canonical
                : resolved.firstAvailableSectionRef
            guard let canonical, !canonical.isEmpty else {
                throw TorahError.referenceTooBroad
            }
            selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: canonical)
            selectedDetent = .medium
            isSearchPresented = false
        } catch {
            message = error.localizedDescription
        }
    }

    func link(_ result: SearchResult) async {
        guard mutationOptIn else {
            message = SessionError.mutationLocked.localizedDescription
            return
        }

        do {
            let item = try await associationItem(for: result)
            persistenceState = .waiting
            persistenceState = .saving
            _ = try await associations.addAssociation(
                item,
                target: associationTargetBlockId.map {
                    .block(objectId: objectId, blockId: $0)
                } ?? .object(objectId: objectId),
                spaceId: spaceId
            )
            persistenceState = .saved
            await refreshAssociations()
            message = "השיוך נשמר במסמך הניסוי."
        } catch let error as TorahAssociationRepositoryError {
            persistenceState = persistenceState(for: error)
            message = error.localizedDescription
        } catch {
            persistenceState = .error(error.localizedDescription)
            message = error.localizedDescription
        }
    }

    func insertExternalDrop(_ transfer: TorahSourceTransfer, targetBlockId: String?) async {
        let dropID = "\(transfer.id):\(transfer.retrievedAt.timeIntervalSinceReferenceDate)"
        guard claimedDropIDs.insert(dropID).inserted else { return }
        await insert(transfer, targetBlockId: targetBlockId)
    }

    private func insert(_ transfer: TorahSourceTransfer, targetBlockId: String?) async {
        guard mutationOptIn else {
            message = SessionError.mutationLocked.localizedDescription
            return
        }
        guard let insertionHandler else {
            message = SessionError.insertionUnavailable.localizedDescription
            return
        }

        do {
            persistenceState = .waiting
            let blockId = try await insertionHandler(transfer, targetBlockId)
            let item = TorahAssociationItem(
                kind: .ref,
                role: .sourceQuote,
                providerID: transfer.providerID,
                externalID: transfer.canonicalRef,
                canonicalKey: transfer.canonicalRef,
                labelHe: transfer.hebrewRef ?? transfer.canonicalRef,
                labelEn: transfer.canonicalRef,
                providerPayload: transfer.rawProviderPayload,
                createdAt: transfer.retrievedAt,
                customMetadata: [
                    "snapshotText": transfer.text,
                    "sectionRef": transfer.sectionRef ?? "",
                    "versionTitle": transfer.versionTitle ?? "",
                    "license": transfer.license ?? ""
                ]
            )
            do {
                persistenceState = .saving
                _ = try await associations.addAssociation(
                    item,
                    target: .block(objectId: objectId, blockId: blockId),
                    spaceId: spaceId
                )
                persistenceState = .saved
                message = "הציטוט והמקור נוספו למסמך."
            } catch {
                persistenceState = .uncertain(SessionError.partialInsertion.localizedDescription)
                message = SessionError.partialInsertion.localizedDescription
            }
        } catch {
            persistenceState = .error(error.localizedDescription)
            message = error.localizedDescription
        }
    }

    private func associationItem(for result: SearchResult) async throws -> TorahAssociationItem {
        switch result.scope {
        case .references:
            let resolved = try await workspace.resolveReference(result.providerValue)
            return TorahAssociationItem(
                kind: .ref,
                role: .context,
                providerID: "sefaria",
                externalID: resolved.canonical,
                canonicalKey: resolved.canonical,
                labelHe: resolved.labelHe,
                labelEn: resolved.labelEn,
                rawInput: searchQuery,
                providerPayload: resolved.payload,
                createdAt: Date()
            )
        case .topics:
            let resolved = try await workspace.resolveTopic(result.providerValue)
            return TorahAssociationItem(
                kind: .topic,
                role: .context,
                providerID: "sefaria",
                externalID: resolved.slug,
                canonicalKey: resolved.slug,
                labelHe: resolved.labelHe ?? resolved.displayTitle,
                labelEn: resolved.labelEn,
                rawInput: searchQuery,
                providerPayload: resolved.payload,
                createdAt: Date()
            )
        case .words:
            guard let resolved = try await workspace.resolveWord(result.providerValue).first else {
                throw SessionError.noResolvedWord
            }
            return TorahAssociationItem(
                kind: .word,
                role: .context,
                providerID: "sefaria",
                externalID: resolved.candidate.id,
                canonicalKey: resolved.candidate.headword,
                labelHe: resolved.candidate.headword,
                labelEn: resolved.candidate.description,
                rawInput: searchQuery,
                providerPayload: resolved.candidate.payload,
                createdAt: Date(),
                customMetadata: ["lexicon": resolved.candidate.lexicon]
            )
        }
    }

    private func addNote(
        for selection: TorahInspectorSelection,
        didChange: @escaping TorahInspectorHostActions.NotesDidChange
    ) async {
        guard mutationOptIn else {
            message = SessionError.mutationLocked.localizedDescription
            return
        }
        do {
            _ = try await notesService.createNote(for: selection)
            repository.invalidateNotes(for: selection)
            didChange()
        } catch {
            message = error.localizedDescription
        }
    }

    private func open(note: TorahInspectorNote, for selection: TorahInspectorSelection) async {
        do {
            guard let objectId = try await notesService.noteObjectId(noteId: note.id, for: selection) else {
                throw SessionError.staleDocument
            }
            openObjectHandler?(objectId)
        } catch {
            message = error.localizedDescription
        }
    }

    private func unlink(
        note: TorahInspectorNote,
        for selection: TorahInspectorSelection,
        didChange: @escaping TorahInspectorHostActions.NotesDidChange
    ) async {
        guard mutationOptIn else {
            message = SessionError.mutationLocked.localizedDescription
            return
        }
        do {
            try await notesService.unlink(noteId: note.id, for: selection)
            repository.invalidateNotes(for: selection)
            didChange()
        } catch {
            message = error.localizedDescription
        }
    }

    private func persistenceState(
        for error: TorahAssociationRepositoryError
    ) -> TorahAssociationPersistenceState {
        switch error {
        case .writeConflict(let message): .conflict(message)
        case .writeUncertain(let message): .uncertain(message)
        default: .error(error.localizedDescription)
        }
    }
}
