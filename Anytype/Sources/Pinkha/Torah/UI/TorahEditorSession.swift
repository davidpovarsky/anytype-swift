import Foundation
import Observation
import PinkhaKit
import TorahInspectorCore
import TorahInspectorUI

struct TorahAssociationContext: Hashable, Sendable, Identifiable {
    enum Scope: Hashable, Sendable {
        case document
        case block(String)
    }

    let spaceId: String
    let objectId: String
    let scope: Scope

    var id: String {
        switch scope {
        case .document: "\(spaceId):\(objectId):document"
        case .block(let blockId): "\(spaceId):\(objectId):block:\(blockId)"
        }
    }

    var blockId: String? {
        guard case .block(let blockId) = scope else { return nil }
        return blockId
    }

    var target: TorahAssociationTarget {
        switch scope {
        case .document: .object(objectId: objectId)
        case .block(let blockId): .block(objectId: objectId, blockId: blockId)
        }
    }
}

enum TorahAssociationDisplayFormatter {
    static func prefersHebrew(_ locale: Locale) -> Bool {
        let language = locale.identifier
            .split(whereSeparator: { $0 == "_" || $0 == "-" })
            .first?
            .lowercased()
        return language == "he" || language == "iw"
    }

    static func label(for item: TorahAssociationItem, locale: Locale) -> String {
        localized(
            hebrew: item.labelHe,
            english: item.labelEn,
            fallback: item.canonicalKey.isEmpty ? item.externalID : item.canonicalKey,
            locale: locale
        )
    }

    static func localized(
        hebrew: String?,
        english: String?,
        fallback: String,
        locale: Locale
    ) -> String {
        let preferred = prefersHebrew(locale) ? hebrew : english
        let secondary = prefersHebrew(locale) ? english : hebrew
        return nonempty(preferred) ?? nonempty(secondary) ?? fallback
    }

    static func containsHebrew(_ value: String) -> Bool {
        value.unicodeScalars.contains { (0x0590...0x05FF).contains(Int($0.value)) }
    }

    private static func nonempty(_ value: String?) -> String? {
        guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines),
              !trimmed.isEmpty else { return nil }
        return trimmed
    }
}

@MainActor
@Observable
final class TorahEditorSession {
    private struct PendingInspectorPresentation {
        let selection: TorahInspectorSelection
        let entryMode: TorahInspectorEntryMode
    }

    enum SearchScope: String, CaseIterable, Identifiable, Hashable {
        case references
        case topics
        case words

        var id: Self { self }

        var title: String {
            switch self {
            case .references: Loc.Pinkha.Torah.sources
            case .topics: Loc.Pinkha.Torah.topics
            case .words: Loc.Pinkha.Torah.words
            }
        }
    }

    struct SearchResult: Identifiable, Hashable {
        let id: String
        let scope: SearchScope
        let providerValue: String
        let labelHe: String?
        let labelEn: String?
        let fallbackTitle: String
        let fallbackSubtitle: String?

        func title(locale: Locale) -> String {
            TorahAssociationDisplayFormatter.localized(
                hebrew: labelHe,
                english: labelEn,
                fallback: fallbackTitle,
                locale: locale
            )
        }

        func subtitle(locale: Locale) -> String? {
            let title = title(locale: locale)
            let alternate = TorahAssociationDisplayFormatter.prefersHebrew(locale) ? labelEn : labelHe
            guard let alternate,
                  !alternate.isEmpty,
                  alternate != title else { return fallbackSubtitle }
            return alternate
        }
    }

    enum SearchState: Equatable {
        case idle
        case loading
        case results([SearchResult])
        case empty
        case error(String)

        var results: [SearchResult] {
            guard case .results(let values) = self else { return [] }
            return values
        }
    }

    enum SessionError: LocalizedError {
        case insertionUnavailable
        case staleDocument
        case noResolvedWord
        case partialInsertion

        var errorDescription: String? {
            switch self {
            case .insertionUnavailable:
                Loc.Pinkha.Torah.Error.insertionUnavailable
            case .staleDocument:
                Loc.Pinkha.Torah.Error.staleDocument
            case .noResolvedWord:
                Loc.Pinkha.Torah.Error.noResolvedWord
            case .partialInsertion:
                Loc.Pinkha.Torah.Error.partialInsertion
            }
        }
    }

    let spaceId: String
    let objectId: String
    let workspace: AnytypeTorahWorkspace
    let repository: TorahInspectorRepository

    var selection: TorahInspectorSelection?
    var selectedTool: TorahStudyToolID = .commentaries
    var selectedDetent: TorahInspectorSheetDetent = .medium
    var isSearchPresented = false
    var searchScope: SearchScope = .references
    var searchQuery = ""
    private(set) var searchState: SearchState = .idle
    var message: String?
    private(set) var associationContext: TorahAssociationContext
    var currentAssociations: [TorahAssociationItem] = []
    private(set) var documentAssociations: [TorahAssociationItem] = []
    private(set) var associationsByBlockId: [String: [TorahAssociationItem]] = [:]
    var persistenceState: TorahAssociationPersistenceState?
    var inspectorEntryMode: TorahInspectorEntryMode = .sourceReader

    private let associations: any AnytypeTorahAssociationSnapshotRepository
    private let notesService: AnytypeTorahNotesService
    private var insertionHandler: ((TorahSourceTransfer, String?) async throws -> String)?
    private var claimedDropIDs = Set<String>()
    private var openObjectHandler: ((String) -> Void)?
    private var associationSnapshotHandler: ((Set<String>) -> Void)?
    private var associationSnapshotEpoch: UInt = 0
    private var searchRequestEpoch: UInt = 0
    private var effectiveLocale = Locale.autoupdatingCurrent
    private var pendingInspectorPresentation: PendingInspectorPresentation?
    private var pendingSearchContext: TorahAssociationContext?
    private var isActiveDocument = true

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
        self.associationContext = TorahAssociationContext(
            spaceId: spaceId,
            objectId: objectId,
            scope: .document
        )
        self.notesService = notesService
        self.repository = TorahInspectorRepositoryFactory.make(
            workspace: workspace,
            notesFetcher: { [notesService] selection in
                try await notesService.notes(for: selection)
            },
            relatedDocumentsFetcher: { [notesService] selection in
                try await notesService.relatedDocuments(for: selection)
            }
        )
    }

    init(
        spaceId: String,
        objectId: String,
        workspace: AnytypeTorahWorkspace,
        associations: any AnytypeTorahAssociationSnapshotRepository
    ) {
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
        self.associationContext = TorahAssociationContext(
            spaceId: spaceId,
            objectId: objectId,
            scope: .document
        )
        self.repository = TorahInspectorRepositoryFactory.make(
            workspace: workspace,
            notesFetcher: { [notesService] selection in
                try await notesService.notes(for: selection)
            },
            relatedDocumentsFetcher: { [notesService] selection in
                try await notesService.relatedDocuments(for: selection)
            }
        )
    }

    var associationTargetBlockId: String? { associationContext.blockId }

    var documentAssociationContext: TorahAssociationContext {
        TorahAssociationContext(spaceId: spaceId, objectId: objectId, scope: .document)
    }

    var visibleDocumentAssociations: [TorahAssociationItem] {
        documentAssociations.filter { !Self.isNoteAssociation($0) }
    }

    var linkedBlockIDs: Set<String> { Set(associationsByBlockId.keys) }

    var hostActions: TorahInspectorHostActions {
        TorahInspectorHostActions(
            onClose: { [weak self] in self?.inspectorDidDismiss() },
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
            onOpenRelatedDocument: { [weak self] document in
                self?.openObjectHandler?(document.objectID)
            },
            onUnlinkRelatedDocument: { [weak self] document, selection, didChange in
                Task { @MainActor in
                    await self?.unlink(document: document, for: selection, didChange: didChange)
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

    func installAssociationSnapshotHandler(_ handler: @escaping (Set<String>) -> Void) {
        associationSnapshotHandler = handler
    }

    func updateEffectiveLocale(_ locale: Locale) {
        guard effectiveLocale.identifier != locale.identifier else { return }
        effectiveLocale = locale
        associationSnapshotHandler?(linkedBlockIDs)
    }

    func activateDocument() {
        isActiveDocument = true
    }

    func deactivateDocument() {
        isActiveDocument = false
        searchRequestEpoch &+= 1
        associationSnapshotEpoch &+= 1
    }

    func presentSearch(scope: TorahAssociationContext.Scope) {
        let context = TorahAssociationContext(spaceId: spaceId, objectId: objectId, scope: scope)
        pendingInspectorPresentation = nil
        if selection != nil {
            pendingSearchContext = context
            selection = nil
            return
        }
        beginSearchPresentation(context: context)
    }

    private func beginSearchPresentation(context: TorahAssociationContext) {
        associationContext = context
        currentAssociations = visibleAssociations(for: context)
        isSearchPresented = true
        Task { await refreshAssociations(for: context) }
    }

    func searchDidDismiss() {
        guard let pending = pendingInspectorPresentation else { return }
        pendingInspectorPresentation = nil
        inspectorEntryMode = pending.entryMode
        selectedDetent = .medium
        selection = pending.selection
    }

    private func inspectorDidDismiss() {
        selection = nil
        guard let context = pendingSearchContext else { return }
        pendingSearchContext = nil
        beginSearchPresentation(context: context)
    }

    private func presentInspector(
        selection nextSelection: TorahInspectorSelection,
        entryMode: TorahInspectorEntryMode
    ) {
        pendingSearchContext = nil
        if isSearchPresented {
            pendingInspectorPresentation = PendingInspectorPresentation(
                selection: nextSelection,
                entryMode: entryMode
            )
            isSearchPresented = false
            return
        }
        inspectorEntryMode = entryMode
        selectedDetent = .medium
        selection = nextSelection
    }

    func refreshAssociations() async {
        await refreshAssociations(for: associationContext)
    }

    func refreshAssociationSnapshot() async {
        await refreshAssociations(for: associationContext)
    }

    private func refreshAssociations(for context: TorahAssociationContext) async {
        do {
            let values = try await associationSnapshot(for: context)
            guard associationContext == context else { return }
            currentAssociations = values
        } catch is CancellationError {
        } catch let error as TorahAssociationRepositoryError {
            guard associationContext == context else { return }
            message = localizedMessage(for: error)
        } catch {
            guard associationContext == context else { return }
            message = error.localizedDescription
        }
    }

    func associationSnapshot(
        for context: TorahAssociationContext
    ) async throws -> [TorahAssociationItem] {
        try validate(context: context)
        associationSnapshotEpoch &+= 1
        let requestEpoch = associationSnapshotEpoch
        let records = try await associations.listAssociationRecords(
            objectId: context.objectId,
            spaceId: context.spaceId
        )
        try Task.checkCancellation()
        try validate(context: context)
        guard associationSnapshotEpoch == requestEpoch else {
            throw CancellationError()
        }
        apply(records: records)
        let values = visibleAssociations(for: context)
        if associationContext == context {
            currentAssociations = values
        }
        return values
    }

    func unlinkAssociation(_ item: TorahAssociationItem) async {
        let context = associationContext
        do {
            _ = try await unlinkAssociation(item, from: context)
        } catch {}
    }

    func unlinkAssociation(
        _ item: TorahAssociationItem,
        from context: TorahAssociationContext
    ) async throws -> [TorahAssociationItem] {
        try validate(context: context)
        persistenceState = .waiting
        do {
            persistenceState = .saving
            try await associations.removeAssociation(
                associationId: item.id,
                target: context.target,
                spaceId: context.spaceId
            )
            try validate(context: context)
            persistenceState = .saved
            return try await associationSnapshot(for: context)
        } catch {
            recordAssociationError(error)
            throw error
        }
    }

    func openAssociation(_ item: TorahAssociationItem) {
        guard canOpenAssociation(item) else { return }
        presentInspector(
            selection: Self.inspectorSelection(for: item),
            entryMode: .relationships
        )
    }

    func openLinkedAssociations(blockId: String) {
        let context = TorahAssociationContext(
            spaceId: spaceId,
            objectId: objectId,
            scope: .block(blockId)
        )
        let items = visibleAssociations(for: context)
        let references = items.filter { canOpenAssociation($0) }
        if items.count == 1, let reference = references.first {
            associationContext = context
            currentAssociations = items
            openAssociation(reference)
        } else {
            presentSearch(scope: .block(blockId))
        }
    }

    func linkedAssociationCount(blockId: String) -> Int {
        visibleAssociations(
            for: TorahAssociationContext(spaceId: spaceId, objectId: objectId, scope: .block(blockId))
        ).count
    }

    func linkedAssociationLabel(blockId: String) -> String? {
        let context = TorahAssociationContext(spaceId: spaceId, objectId: objectId, scope: .block(blockId))
        guard let item = visibleAssociations(for: context).first else { return nil }
        return TorahAssociationDisplayFormatter.label(for: item, locale: effectiveLocale)
    }

    func canOpenAssociation(_ item: TorahAssociationItem) -> Bool {
        guard case .ref = item.kind else { return false }
        return !item.canonicalKey.hasPrefix("anytype-note:") && !item.canonicalKey.isEmpty
    }

    static func inspectorSelection(for item: TorahAssociationItem) -> TorahInspectorSelection {
        let canonical = item.canonicalKey
        let displayMetadata = TorahReferenceDisplayMetadata(
            english: item.labelEn,
            hebrew: item.labelHe
        )
        let explicitSection = item.customMetadata?["sectionRef"]?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        if TorahReferenceUtil.isSegmentRef(canonical) {
            let section = if let explicitSection, !explicitSection.isEmpty {
                explicitSection
            } else {
                TorahReferenceUtil.sectionRef(from: canonical)
            }
            return TorahInspectorSelection(
                providerID: item.providerID,
                canonicalRef: section,
                preferredSegmentRef: canonical,
                scope: .segment,
                displayMetadata: displayMetadata
            )
        }
        return TorahInspectorSelection(
            providerID: item.providerID,
            canonicalRef: canonical,
            scope: .section,
            displayMetadata: displayMetadata
        )
    }

    func performSearch(debounce: Duration = .zero) async {
        searchRequestEpoch &+= 1
        let requestEpoch = searchRequestEpoch
        let query = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        let scope = searchScope
        guard query.count >= 2 else {
            searchState = .idle
            return
        }

        searchState = .loading

        do {
            if debounce > .zero {
                try await Task.sleep(for: debounce)
            }
            try Task.checkCancellation()
            let results = try await search(query: query, scope: scope)
            try Task.checkCancellation()
            guard isCurrentSearch(requestEpoch, query: query, scope: scope) else { return }
            searchState = results.isEmpty ? .empty : .results(results)
        } catch is CancellationError {
            guard isCurrentSearch(requestEpoch, query: query, scope: scope) else { return }
            searchState = .idle
        } catch TorahError.noResults {
            guard isCurrentSearch(requestEpoch, query: query, scope: scope) else { return }
            searchState = .empty
        } catch {
            guard isCurrentSearch(requestEpoch, query: query, scope: scope) else { return }
            let localized = if let torahError = error as? TorahError {
                TorahStrings.message(for: torahError, locale: effectiveLocale)
            } else {
                Loc.Pinkha.Torah.Error.backendFailure
            }
            searchState = .error(localized)
        }
    }

    func search(query: String, scope: SearchScope) async throws -> [SearchResult] {
        switch scope {
        case .references:
            try await workspace.suggestReferences(query).map {
                let isHebrew = TorahAssociationDisplayFormatter.containsHebrew($0.label)
                return SearchResult(
                    id: "reference:\($0.id)",
                    scope: .references,
                    providerValue: $0.id,
                    labelHe: isHebrew ? $0.label : nil,
                    labelEn: isHebrew ? $0.id : $0.label,
                    fallbackTitle: $0.label,
                    fallbackSubtitle: nil
                )
            }
        case .topics:
            try await workspace.suggestTopics(query).map {
                SearchResult(
                    id: "topic:\($0.id)",
                    scope: .topics,
                    providerValue: $0.id,
                    labelHe: $0.labelHe,
                    labelEn: $0.labelEn,
                    fallbackTitle: $0.displayTitle,
                    fallbackSubtitle: nil
                )
            }
        case .words:
            try await workspace.suggestWords(query).map {
                let isHebrew = TorahAssociationDisplayFormatter.containsHebrew($0.headword)
                return SearchResult(
                    id: "word:\($0.id)",
                    scope: .words,
                    providerValue: $0.surface,
                    labelHe: isHebrew ? $0.headword : nil,
                    labelEn: isHebrew ? $0.description : $0.headword,
                    fallbackTitle: $0.headword,
                    fallbackSubtitle: $0.lexicon
                )
            }
        }
    }

    private func isCurrentSearch(
        _ requestEpoch: UInt,
        query: String,
        scope: SearchScope
    ) -> Bool {
        searchRequestEpoch == requestEpoch
            && searchQuery.trimmingCharacters(in: .whitespacesAndNewlines) == query
            && searchScope == scope
    }

    func openReference(_ result: SearchResult) async {
        guard result.scope == .references else { return }
        do {
            let nextSelection = try await resolveReference(result)
            presentInspector(selection: nextSelection, entryMode: .sourceReader)
        } catch {
            message = error.localizedDescription
        }
    }

    func resolveReference(_ result: SearchResult) async throws -> TorahInspectorSelection {
        guard result.scope == .references else {
            throw TorahError.referenceTooBroad
        }
        let resolved = try await workspace.resolveReference(result.providerValue)
        try Task.checkCancellation()
        return try Self.inspectorSelection(for: resolved)
    }

    func openResolvedReferenceFromStandaloneSearch(_ selection: TorahInspectorSelection) {
        presentInspector(selection: selection, entryMode: .sourceReader)
    }

    static func inspectorSelection(for resolved: ResolvedReference) throws -> TorahInspectorSelection {
        let displayMetadata = TorahReferenceDisplayMetadata(
            english: resolved.labelEn,
            hebrew: resolved.labelHe
        )
        guard resolved.isEmbeddableSource else {
            guard let sectionRef = resolved.firstAvailableSectionRef, !sectionRef.isEmpty else {
                throw TorahError.referenceTooBroad
            }
            return TorahInspectorSelection(
                providerID: "sefaria",
                canonicalRef: sectionRef,
                scope: .section,
                displayMetadata: displayMetadata
            )
        }

        if TorahReferenceUtil.isSegmentRef(resolved.canonical) {
            let sectionRef = TorahReferenceUtil.sectionRef(from: resolved.canonical)
            return TorahInspectorSelection(
                providerID: "sefaria",
                canonicalRef: sectionRef,
                preferredSegmentRef: resolved.canonical,
                scope: .segment,
                displayMetadata: displayMetadata
            )
        }

        return TorahInspectorSelection(
            providerID: "sefaria",
            canonicalRef: resolved.canonical,
            scope: .section,
            displayMetadata: displayMetadata
        )
    }

    func link(_ result: SearchResult) async {
        let context = associationContext
        do {
            _ = try await link(result, to: context, rawQuery: searchQuery)
        } catch {}
    }

    func link(
        _ result: SearchResult,
        to context: TorahAssociationContext,
        rawQuery: String
    ) async throws -> [TorahAssociationItem] {
        let frozenContext = context
        let frozenResult = result
        let frozenRawQuery = rawQuery
        try validate(context: frozenContext)
        persistenceState = .waiting
        do {
            let item = try await associationItem(
                for: frozenResult,
                rawQuery: frozenRawQuery
            )
            try Task.checkCancellation()
            try validate(context: frozenContext)
            persistenceState = .saving
            _ = try await associations.addAssociation(
                item,
                target: frozenContext.target,
                spaceId: frozenContext.spaceId
            )
            try validate(context: frozenContext)
            persistenceState = .saved
            return try await associationSnapshot(for: frozenContext)
        } catch {
            recordAssociationError(error)
            throw error
        }
    }

    func insertExternalDrop(_ transfer: TorahSourceTransfer, targetBlockId: String?) async {
        let dropID = "\(transfer.id):\(transfer.retrievedAt.timeIntervalSinceReferenceDate)"
        guard claimedDropIDs.insert(dropID).inserted else { return }
        await insert(transfer, targetBlockId: targetBlockId)
    }

    private func insert(_ transfer: TorahSourceTransfer, targetBlockId: String?) async {
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
                labelHe: transfer.hebrewRef ?? "",
                labelEn: transfer.canonicalRef,
                providerPayload: transfer.rawProviderPayload,
                createdAt: transfer.retrievedAt,
                customMetadata: [
                    "snapshotText": transfer.text,
                    "sectionRef": transfer.sectionRef ?? "",
                    "versionTitle": transfer.versionTitle ?? "",
                    "license": transfer.license ?? "",
                    "direction": transfer.direction ?? ""
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
                await refreshAssociationSnapshot()
            } catch {
                persistenceState = .uncertain(SessionError.partialInsertion.localizedDescription)
                message = SessionError.partialInsertion.localizedDescription
            }
        } catch {
            persistenceState = .error(error.localizedDescription)
            message = error.localizedDescription
        }
    }

    private func associationItem(
        for result: SearchResult,
        rawQuery: String
    ) async throws -> TorahAssociationItem {
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
                rawInput: rawQuery,
                providerPayload: resolved.payload,
                createdAt: Date(),
                customMetadata: TorahReferenceUtil.isSegmentRef(resolved.canonical)
                    ? ["sectionRef": TorahReferenceUtil.sectionRef(from: resolved.canonical)]
                    : nil
            )
        case .topics:
            let resolved = try await workspace.resolveTopic(result.providerValue)
            return TorahAssociationItem(
                kind: .topic,
                role: .context,
                providerID: "sefaria",
                externalID: resolved.slug,
                canonicalKey: resolved.slug,
                labelHe: resolved.labelHe ?? "",
                labelEn: resolved.labelEn ?? (
                    TorahAssociationDisplayFormatter.containsHebrew(resolved.displayTitle)
                        ? nil
                        : resolved.displayTitle
                ),
                rawInput: rawQuery,
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
                labelHe: TorahAssociationDisplayFormatter.containsHebrew(resolved.candidate.headword)
                    ? resolved.candidate.headword
                    : "",
                labelEn: TorahAssociationDisplayFormatter.containsHebrew(resolved.candidate.headword)
                    ? resolved.candidate.description
                    : resolved.candidate.headword,
                rawInput: rawQuery,
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
        do {
            _ = try await notesService.createNote(for: selection)
            await refreshAssociationSnapshot()
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
        do {
            try await notesService.unlink(noteId: note.id, for: selection)
            await refreshAssociationSnapshot()
            repository.invalidateNotes(for: selection)
            didChange()
        } catch {
            message = error.localizedDescription
        }
    }

    private func unlink(
        document: TorahRelatedDocument,
        for selection: TorahInspectorSelection,
        didChange: @escaping TorahInspectorHostActions.NotesDidChange
    ) async {
        do {
            try await notesService.unlink(document: document, for: selection)
            await refreshAssociationSnapshot()
            repository.invalidateNotes(for: selection)
            repository.invalidateRelatedDocuments(for: selection)
            didChange()
        } catch {
            message = error.localizedDescription
        }
    }

    private func apply(records: [TorahStoredAssociationRecord]) {
        let previousBlockIDs = linkedBlockIDs
        let relevant = records.filter { $0.spaceId == spaceId && $0.objectId == objectId }
        documentAssociations = relevant
            .filter { $0.blockId == nil }
            .map(\.item)

        associationsByBlockId = Dictionary(
            grouping: relevant.compactMap { record -> (String, TorahAssociationItem)? in
                guard let blockId = record.blockId else { return nil }
                return (blockId, record.item)
            },
            by: { $0.0 }
        ).mapValues { values in
            values.map(\.1)
        }
        associationSnapshotHandler?(previousBlockIDs.union(linkedBlockIDs))
    }

    private func visibleAssociations(for context: TorahAssociationContext) -> [TorahAssociationItem] {
        let items: [TorahAssociationItem]
        switch context.scope {
        case .document:
            items = documentAssociations
        case .block(let blockId):
            items = associationsByBlockId[blockId] ?? []
        }
        return items.filter { !Self.isNoteAssociation($0) }
    }

    func cachedAssociations(for context: TorahAssociationContext) -> [TorahAssociationItem] {
        guard context.spaceId == spaceId, context.objectId == objectId else { return [] }
        return visibleAssociations(for: context)
    }

    func reportSearchError(_ error: Error) {
        guard !(error is CancellationError) else { return }
        if let torahError = error as? TorahError {
            message = TorahStrings.message(for: torahError, locale: effectiveLocale)
        } else {
            message = error.localizedDescription
        }
    }

    func searchMessage(for error: Error) -> String {
        if let torahError = error as? TorahError {
            return TorahStrings.message(for: torahError, locale: effectiveLocale)
        }
        return Loc.Pinkha.Torah.Error.backendFailure
    }

    func validateSearchContext(_ context: TorahAssociationContext) throws {
        try validate(context: context)
    }

    private func validate(context: TorahAssociationContext) throws {
        guard isActiveDocument,
              context.spaceId == spaceId,
              context.objectId == objectId else {
            throw SessionError.staleDocument
        }
    }

    private func recordAssociationError(_ error: Error) {
        guard !(error is CancellationError) else { return }
        if let repositoryError = error as? TorahAssociationRepositoryError {
            persistenceState = persistenceState(for: repositoryError)
            message = localizedMessage(for: repositoryError)
        } else {
            persistenceState = .error(error.localizedDescription)
            message = error.localizedDescription
        }
    }

    private static func isNoteAssociation(_ item: TorahAssociationItem) -> Bool {
        item.canonicalKey.hasPrefix("anytype-note:")
    }

    private func persistenceState(
        for error: TorahAssociationRepositoryError
    ) -> TorahAssociationPersistenceState {
        switch error {
        case .writeConflict: .conflict(localizedMessage(for: error))
        case .writeUncertain: .uncertain(localizedMessage(for: error))
        default: .error(localizedMessage(for: error))
        }
    }

    private func localizedMessage(for error: TorahAssociationRepositoryError) -> String {
        switch error {
        case .permissionDenied:
            Loc.Pinkha.Torah.Error.permissionDenied
        case .targetNotFound, .targetOutsideSpace, .associationNotFound:
            Loc.Pinkha.Torah.Error.targetUnavailable
        case .malformedCanonicalData:
            Loc.Pinkha.Torah.Error.invalidStoredData
        case .unsupportedPayloadVersion:
            Loc.Pinkha.Torah.Error.unsupportedStoredData
        case .writeConflict:
            Loc.Pinkha.Torah.Error.conflictingWrite
        case .writeUncertain:
            Loc.Pinkha.Torah.Error.uncertainWrite
        case .backendFailure, .unsafeSnapshotReplacement:
            Loc.Pinkha.Torah.Error.backendFailure
        }
    }
}
