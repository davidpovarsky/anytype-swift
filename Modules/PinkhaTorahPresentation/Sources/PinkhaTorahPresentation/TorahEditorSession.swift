// Shared extraction of the existing controller; see EXTRACTION.json.
#if canImport(SwiftUI)
import Foundation
import Loc
import Observation
import PinkhaKit
import TorahInspectorCore
import TorahInspectorUI

public struct TorahAssociationContext: Hashable, Sendable, Identifiable {
    public enum Scope: Hashable, Sendable {
        case document
        case block(String)
        case semantic(PinkhaSemanticTextAnchor)
    }

    public let spaceId: String
    public let objectId: String
    public let scope: Scope

    public init(spaceId: String, objectId: String, scope: Scope) {
        self.spaceId = spaceId; self.objectId = objectId; self.scope = scope
    }

    public var id: String {
        switch scope {
        case .document: "\(spaceId):\(objectId):document"
        case .block(let blockId): "\(spaceId):\(objectId):block:\(blockId)"
        case .semantic(let anchor): "\(spaceId):\(objectId):semantic:\(anchor.markerString)"
        }
    }

    public var blockId: String? {
        guard case .block(let blockId) = scope else { return nil }
        return blockId
    }

    public var semanticAnchor: PinkhaSemanticTextAnchor? {
        guard case .semantic(let anchor) = scope else { return nil }
        return anchor
    }

    /// Semantic metadata lives in the canonical object's existing payload.
    /// The durable target remains the marker identity, never this storage row.
    public var target: TorahAssociationTarget {
        switch scope {
        case .document, .semantic: .object(objectId: objectId)
        case .block(let blockId): .block(objectId: objectId, blockId: blockId)
        }
    }
}

public enum TorahAssociationDisplayFormatter {
    public static func prefersHebrew(_ locale: Locale) -> Bool {
        let language = locale.identifier
            .split(whereSeparator: { $0 == "_" || $0 == "-" })
            .first?
            .lowercased()
        return language == "he" || language == "iw"
    }

    public static func label(for item: TorahAssociationItem, locale: Locale) -> String {
        localized(
            hebrew: item.labelHe,
            english: item.labelEn,
            fallback: item.canonicalKey.isEmpty ? item.externalID : item.canonicalKey,
            locale: locale
        )
    }

    public static func localized(
        hebrew: String?,
        english: String?,
        fallback: String,
        locale: Locale
    ) -> String {
        let preferred = prefersHebrew(locale) ? hebrew : english
        let secondary = prefersHebrew(locale) ? english : hebrew
        return nonempty(preferred) ?? nonempty(secondary) ?? fallback
    }

    public static func containsHebrew(_ value: String) -> Bool {
        value.unicodeScalars.contains { (0x0590...0x05FF).contains(Int($0.value)) }
    }

    private static func nonempty(_ value: String?) -> String? {
        guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines),
              !trimmed.isEmpty else { return nil }
        return trimmed
    }
}

public typealias TorahSourceInsertionAction = @MainActor @Sendable (TorahSourceTransfer) async -> Void

@MainActor
@Observable
public final class TorahEditorSession {
    @MainActor
    private final class DropClaim {
        var used = false
    }

    private struct InsertionContext: Sendable {
        let documentEpoch: UInt
        let inspectorEpoch: UInt?
        let selectionID: String?
    }

    public enum PresentationHost: Equatable {
        case editor
        case properties
    }

    private struct PendingInspectorPresentation {
        let selection: TorahInspectorSelection
        let entryMode: TorahInspectorEntryMode
    }

    public enum SearchScope: String, CaseIterable, Identifiable, Hashable {
        case references
        case topics
        case words

        public var id: Self { self }

        public var title: String {
            switch self {
            case .references: Loc.Pinkha.Torah.sources
            case .topics: Loc.Pinkha.Torah.topics
            case .words: Loc.Pinkha.Torah.words
            }
        }
    }

    public struct SearchResult: Identifiable, Hashable {
        public let id: String
        public let scope: SearchScope
        public let providerValue: String
        public let labelHe: String?
        public let labelEn: String?
        public let fallbackTitle: String
        public let fallbackSubtitle: String?

        public init(id: String, scope: SearchScope, providerValue: String,
                    labelHe: String?, labelEn: String?, fallbackTitle: String,
                    fallbackSubtitle: String?) {
            self.id = id; self.scope = scope; self.providerValue = providerValue
            self.labelHe = labelHe; self.labelEn = labelEn
            self.fallbackTitle = fallbackTitle; self.fallbackSubtitle = fallbackSubtitle
        }

        public func title(locale: Locale) -> String {
            TorahAssociationDisplayFormatter.localized(
                hebrew: labelHe,
                english: labelEn,
                fallback: fallbackTitle,
                locale: locale
            )
        }

        public func subtitle(locale: Locale) -> String? {
            let title = title(locale: locale)
            let alternate = TorahAssociationDisplayFormatter.prefersHebrew(locale) ? labelEn : labelHe
            guard let alternate,
                  !alternate.isEmpty,
                  alternate != title else { return fallbackSubtitle }
            return alternate
        }
    }

    public enum SearchState: Equatable {
        case idle
        case loading
        case results([SearchResult])
        case empty
        case error(String)

        public var results: [SearchResult] {
            guard case .results(let values) = self else { return [] }
            return values
        }
    }

    public enum SessionError: LocalizedError {
        case insertionUnavailable
        case staleDocument
        case noResolvedWord
        case partialInsertion

        public var errorDescription: String? {
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

    public let spaceId: String
    public let objectId: String
    public let workspace: AnytypeTorahWorkspace
    public let repository: TorahInspectorRepository

    public var selection: TorahInspectorSelection?
    public var selectedTool: TorahStudyToolID = .commentaries
    public var selectedDetent: TorahInspectorSheetDetent = .medium
    public var isSearchPresented = false
    public private(set) var presentationHost: PresentationHost = .editor
    public var searchScope: SearchScope = .references
    public var searchQuery = ""
    public private(set) var searchState: SearchState = .idle
    public var message: String?
    public private(set) var associationContext: TorahAssociationContext
    public var currentAssociations: [TorahAssociationItem] = []
    public private(set) var documentAssociations: [TorahAssociationItem] = []
    public private(set) var associationRecords: [TorahStoredAssociationRecord] = []
    public private(set) var associationsByBlockId: [String: [TorahAssociationItem]] = [:]
    public var persistenceState: TorahAssociationPersistenceState?
    public var inspectorEntryMode: TorahInspectorEntryMode = .sourceReader

    private let associations: any TorahAssociationSnapshotRepository
    private let notesService: any TorahEditorNotesService
    private var insertionHandler: ((TorahSourceTransfer, String?) async throws -> String)?
    private var documentActionEpoch: UInt = 0
    private var insertionEditingPolicy: () -> Bool = { true }
    private var openObjectHandler: ((String, String?) -> Void)?
    private var associationSnapshotHandler: ((Set<String>) -> Void)?
    private var associationSnapshotEpoch: UInt = 0
    private var searchRequestEpoch: UInt = 0
    private var noteActionEpoch: UInt = 0
    private var isCreatingNote = false
    private var effectiveLocale = Locale.autoupdatingCurrent
    private var pendingInspectorPresentation: PendingInspectorPresentation?
    private var pendingSearchContext: TorahAssociationContext?
    private var isActiveDocument = true
    private var associationEditingPolicy: () -> Bool = { true }
    private var semanticAnchorResolver: TorahSemanticAnchorResolutionHandler?

    public init(
        spaceId: String,
        objectId: String,
        workspace: AnytypeTorahWorkspace,
        associations: any TorahAssociationSnapshotRepository,
        notesService: any TorahEditorNotesService
    ) {
        self.spaceId = spaceId
        self.objectId = objectId
        self.workspace = workspace
        self.associations = associations
        self.notesService = notesService
        self.associationContext = TorahAssociationContext(
            spaceId: spaceId, objectId: objectId, scope: .document
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

    public var associationTargetBlockId: String? { associationContext.blockId }

    public var documentAssociationContext: TorahAssociationContext {
        TorahAssociationContext(spaceId: spaceId, objectId: objectId, scope: .document)
    }

    public var visibleDocumentAssociations: [TorahAssociationItem] {
        documentAssociations.filter { !Self.isNoteAssociation($0) }
    }

    public var documentPropertyProjection: TorahDocumentPropertyProjection {
        TorahDocumentPropertyProjection(records: associationRecords, spaceId: spaceId, objectId: objectId)
    }

    public var canEditAssociations: Bool { isActiveDocument && associationEditingPolicy() }

    public func installAssociationEditingPolicy(_ policy: @escaping () -> Bool) {
        associationEditingPolicy = policy
    }

    public func installSemanticAnchorResolver(_ resolver: @escaping TorahSemanticAnchorResolutionHandler) {
        semanticAnchorResolver = resolver
    }

    /// Opening sources is read-only. A later Link resolves again and performs
    /// the repository's final dispatch authorization and canonical readback.
    public func presentSemanticAnchorSources(_ anchor: PinkhaSemanticTextAnchor) async throws {
        let context = TorahAssociationContext(spaceId: spaceId, objectId: objectId, scope: .semantic(anchor))
        try await requireResolvedSemanticAnchor(for: context)
        presentSearch(scope: context.scope)
    }

    private func requireResolvedSemanticAnchor(for context: TorahAssociationContext) async throws {
        try validate(context: context)
        guard let anchor = context.semanticAnchor else { return }
        guard let resolver = semanticAnchorResolver else { throw TorahSemanticAnchorResolutionError.unavailable }
        let epoch = documentActionEpoch
        let resolution = try await resolver(anchor)
        try Task.checkCancellation()
        try validate(context: context)
        guard epoch == documentActionEpoch else { throw SessionError.staleDocument }
        switch resolution {
        case .resolved(let fragments):
            guard !fragments.isEmpty else { throw TorahSemanticAnchorResolutionError.missing }
        case .missing: throw TorahSemanticAnchorResolutionError.missing
        case .ambiguous: throw TorahSemanticAnchorResolutionError.ambiguous
        }
    }

    public var linkedBlockIDs: Set<String> { Set(associationsByBlockId.keys) }

    public var hostActions: TorahInspectorHostActions {
        let actionEpoch = noteActionEpoch
        let inspectorSelectionID = selection?.id
        let insertSource = makeInspectorSourceInsertionAction()
        return TorahInspectorHostActions(
            onClose: { [weak self] in
                guard let self, self.isCurrentNoteAction(epoch: actionEpoch, selectionID: inspectorSelectionID) else { return }
                self.inspectorDidDismiss()
            },
            onInsertSegment: { [weak self] transfer in
                Task { @MainActor in
                    guard let self, self.isCurrentNoteAction(epoch: actionEpoch, selectionID: inspectorSelectionID) else { return }
                    await insertSource(transfer)
                }
            },
            onOpenInNewTab: nil,
            onAddNote: { [weak self] selection, didChange in
                Task { @MainActor in
                    guard let self, self.isCurrentNoteAction(epoch: actionEpoch, selectionID: inspectorSelectionID) else { return }
                    await self.addNote(for: selection, didChange: didChange)
                }
            },
            onOpenNote: { [weak self] note, selection, _ in
                Task { @MainActor in
                    guard let self, self.isCurrentNoteAction(epoch: actionEpoch, selectionID: inspectorSelectionID) else { return }
                    await self.open(note: note, for: selection)
                }
            },
            onDeleteNote: { [weak self] note, selection, didChange in
                Task { @MainActor in
                    guard let self, self.isCurrentNoteAction(epoch: actionEpoch, selectionID: inspectorSelectionID) else { return }
                    await self.unlink(note: note, for: selection, didChange: didChange)
                }
            },
            noteActionUnlinksSource: true,
            onOpenRelatedDocument: { [weak self] document in
                self?.openRelatedDocument(document, actionEpoch: actionEpoch, inspectorSelectionID: inspectorSelectionID)
            },
            onUnlinkRelatedDocument: { [weak self] document, selection, didChange in
                Task { @MainActor in
                    guard let self, self.isCurrentNoteAction(epoch: actionEpoch, selectionID: inspectorSelectionID) else { return }
                    await self.unlink(document: document, for: selection, didChange: didChange)
                }
            },
            showsCloseButton: true
        )
    }

    public func installInsertionHandler(
        _ handler: @escaping (TorahSourceTransfer, String?) async throws -> String
    ) {
        insertionHandler = handler
    }

    public func installInsertionEditingPolicy(_ policy: @escaping () -> Bool) {
        insertionEditingPolicy = policy
    }

    public func installOpenObjectHandler(_ handler: @escaping (String, String?) -> Void) {
        openObjectHandler = handler
    }

    public func installAssociationSnapshotHandler(_ handler: @escaping (Set<String>) -> Void) {
        associationSnapshotHandler = handler
    }

    public func updateEffectiveLocale(_ locale: Locale) {
        guard effectiveLocale.identifier != locale.identifier else { return }
        effectiveLocale = locale
        associationSnapshotHandler?(linkedBlockIDs)
    }

    public func activateDocument() {
        isActiveDocument = true
        repository.resumeRelatedDocuments()
    }

    public func deactivateDocument() {
        isActiveDocument = false
        documentActionEpoch &+= 1
        noteActionEpoch &+= 1
        repository.retireRelatedDocuments()
        searchRequestEpoch &+= 1
        associationSnapshotEpoch &+= 1
        isSearchPresented = false
        selection = nil
        pendingSearchContext = nil
        pendingInspectorPresentation = nil
    }

    /// The native property sheet owns its inspector while preserving the same
    /// search/selection state machine. An active modal is never moved implicitly.
    public func activatePresentationHost(_ host: PresentationHost) {
        guard isActiveDocument, selection == nil, !isSearchPresented else { return }
        presentationHost = host
    }

    public func presentSearch(
        scope: TorahAssociationContext.Scope,
        initialCategory: SearchScope = .references,
        host: PresentationHost = .editor
    ) {
        guard isActiveDocument else { return }
        presentationHost = host
        searchScope = initialCategory
        searchQuery = ""
        searchState = .idle
        searchRequestEpoch &+= 1
        let context = TorahAssociationContext(spaceId: spaceId, objectId: objectId, scope: scope)
        pendingInspectorPresentation = nil
        if selection != nil {
            pendingSearchContext = context
            selection = nil
            return
        }
        beginSearchPresentation(context: context)
    }

    public func dismissPropertiesPresentation() {
        guard presentationHost == .properties else { return }
        isSearchPresented = false
        selection = nil
        pendingSearchContext = nil
        pendingInspectorPresentation = nil
        presentationHost = .editor
    }

    private func beginSearchPresentation(context: TorahAssociationContext) {
        associationContext = context
        currentAssociations = visibleAssociations(for: context)
        isSearchPresented = true
        Task { await refreshAssociations(for: context) }
    }

    public func searchDidDismiss() {
        guard let pending = pendingInspectorPresentation else { return }
        pendingInspectorPresentation = nil
        inspectorEntryMode = pending.entryMode
        selectedDetent = .medium
        selection = pending.selection
    }

    private func inspectorDidDismiss() {
        noteActionEpoch &+= 1
        selection = nil
        guard let context = pendingSearchContext else { return }
        pendingSearchContext = nil
        beginSearchPresentation(context: context)
    }

    private func presentInspector(
        selection nextSelection: TorahInspectorSelection,
        entryMode: TorahInspectorEntryMode
    ) {
        noteActionEpoch &+= 1
        repository.invalidateRelatedDocuments(for: nextSelection)
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

    public func refreshAssociations() async {
        await refreshAssociations(for: associationContext)
    }

    public func refreshAssociationSnapshot() async {
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

    public func associationSnapshot(
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

    public func unlinkAssociation(_ item: TorahAssociationItem) async {
        let context = associationContext
        do {
            _ = try await unlinkAssociation(item, from: context)
        } catch {}
    }

    public func unlinkAssociation(
        _ item: TorahAssociationItem,
        from context: TorahAssociationContext,
        isCurrentRequest: @escaping @MainActor @Sendable () -> Bool = { true }
    ) async throws -> [TorahAssociationItem] {
        let epoch = documentActionEpoch
        let authorize: TorahAssociationWriteAuthorization = { [weak self] in
            guard let self, self.documentActionEpoch == epoch, isCurrentRequest() else { throw CancellationError() }
            try Task.checkCancellation()
            try self.validate(context: context)
            guard self.canEditAssociations else { throw TorahAssociationRepositoryError.permissionDenied }
        }
        do {
            try authorize()
            persistenceState = .waiting
            if let anchor = context.semanticAnchor {
                guard try TorahSemanticAnchorAssociation.decoding(item,
                    location: .init(spaceId: context.spaceId, target: context.target))?.anchor == anchor else {
                    throw PinkhaSemanticTextAnchorError.wrongDocument
                }
            }
            persistenceState = .saving
            try await associations.removeAssociation(
                associationId: item.id,
                target: context.target,
                spaceId: context.spaceId,
                authorize: authorize
            )
            try authorize()
            let values = try await associationSnapshot(for: context)
            try authorize()
            let location = TorahAssociationLocation(spaceId: context.spaceId, target: context.target)
            guard !associationRecords.contains(where: { $0.location == location && $0.item.id == item.id }) else {
                // Inspect the complete canonical records, not the semantic
                // filter: changed metadata cannot masquerade as removal.
                throw TorahAssociationRepositoryError.writeUncertain("Removed source remains in canonical readback")
            }
            persistenceState = .saved
            return values
        } catch {
            if documentActionEpoch == epoch && isActiveDocument && isCurrentRequest() { recordAssociationError(error) }
            throw error
        }
    }

    public func openDocumentAssociation(_ item: TorahAssociationItem) {
        guard isActiveDocument else { return }
        let visible = visibleDocumentAssociations
        guard let currentItem = visible.first(where: { $0.id == item.id }) else {
            Task { @MainActor in
                await refreshAssociationSnapshot()
            }
            return
        }
        let context: TorahAssociationContext
        do {
            let location = TorahAssociationLocation(spaceId: spaceId, target: .object(objectId: objectId))
            if let semantic = try TorahSemanticAnchorAssociation.decoding(currentItem, location: location) {
                context = .init(spaceId: spaceId, objectId: objectId, scope: .semantic(semantic.anchor))
            } else { context = documentAssociationContext }
        } catch {
            recordAssociationError(error)
            return
        }
        associationContext = context
        currentAssociations = visibleAssociations(for: context)
        if canOpenAssociation(currentItem) {
            openAssociation(currentItem)
        } else {
            presentSearch(scope: context.scope)
        }
    }

    public func openAssociation(_ item: TorahAssociationItem) {
        guard canOpenAssociation(item) else { return }
        presentInspector(
            selection: Self.inspectorSelection(for: item),
            entryMode: .relationships
        )
    }

    public func openLinkedAssociations(blockId: String) {
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

    public func linkedAssociationCount(blockId: String) -> Int {
        visibleAssociations(
            for: TorahAssociationContext(spaceId: spaceId, objectId: objectId, scope: .block(blockId))
        ).count
    }

    public func linkedAssociationLabel(blockId: String) -> String? {
        let context = TorahAssociationContext(spaceId: spaceId, objectId: objectId, scope: .block(blockId))
        guard let item = visibleAssociations(for: context).first else { return nil }
        return TorahAssociationDisplayFormatter.label(for: item, locale: effectiveLocale)
    }

    public func canOpenAssociation(_ item: TorahAssociationItem) -> Bool {
        guard case .ref = item.kind else { return false }
        return !item.canonicalKey.hasPrefix("anytype-note:") && !item.canonicalKey.isEmpty
    }

    public static func inspectorSelection(for item: TorahAssociationItem) -> TorahInspectorSelection {
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

    public func performSearch(debounce: Duration = .zero) async {
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

    public func search(query: String, scope: SearchScope) async throws -> [SearchResult] {
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

    public func openReference(_ result: SearchResult) async {
        guard result.scope == .references else { return }
        do {
            let nextSelection = try await resolveReference(result)
            presentInspector(selection: nextSelection, entryMode: .sourceReader)
        } catch {
            message = error.localizedDescription
        }
    }

    public func resolveReference(_ result: SearchResult) async throws -> TorahInspectorSelection {
        guard result.scope == .references else {
            throw TorahError.referenceTooBroad
        }
        let resolved = try await workspace.resolveReference(result.providerValue)
        try Task.checkCancellation()
        return try Self.inspectorSelection(for: resolved)
    }

    public func openResolvedReferenceFromStandaloneSearch(_ selection: TorahInspectorSelection) {
        presentInspector(selection: selection, entryMode: .sourceReader)
    }

    public static func inspectorSelection(for resolved: ResolvedReference) throws -> TorahInspectorSelection {
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

    public func link(_ result: SearchResult) async {
        let context = associationContext
        do {
            _ = try await link(result, to: context, rawQuery: searchQuery)
        } catch {}
    }

    public func link(
        _ result: SearchResult,
        to context: TorahAssociationContext,
        rawQuery: String,
        isCurrentRequest: @escaping @MainActor @Sendable () -> Bool = { true }
    ) async throws -> [TorahAssociationItem] {
        let frozenContext = context
        let frozenResult = result
        let frozenRawQuery = rawQuery
        let epoch = documentActionEpoch
        let authorize: TorahAssociationWriteAuthorization = { [weak self] in
            guard let self, self.documentActionEpoch == epoch, isCurrentRequest() else {
                throw CancellationError()
            }
            try Task.checkCancellation()
            try self.validate(context: frozenContext)
            guard self.canEditAssociations else { throw TorahAssociationRepositoryError.permissionDenied }
        }
        do {
            try authorize()
            persistenceState = .waiting
            try validate(context: frozenContext)
            guard canEditAssociations else { throw TorahAssociationRepositoryError.permissionDenied }
            guard isCurrentRequest() else { throw CancellationError() }
            var item = try await associationItem(
                for: frozenResult,
                rawQuery: frozenRawQuery
            )
            try Task.checkCancellation()
            try validate(context: frozenContext)
            guard canEditAssociations else { throw TorahAssociationRepositoryError.permissionDenied }
            guard isCurrentRequest() else { throw CancellationError() }
            try await requireResolvedSemanticAnchor(for: frozenContext)
            if let anchor = frozenContext.semanticAnchor {
                item = try TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: item,
                    location: .init(spaceId: frozenContext.spaceId, target: frozenContext.target))
            }
            try authorize()
            persistenceState = .saving
            let stored = try await associations.addAssociation(
                item,
                target: frozenContext.target,
                spaceId: frozenContext.spaceId,
                authorize: authorize
            )
            try authorize()
            let values = try await associationSnapshot(for: frozenContext)
            try authorize()
            if let anchor = frozenContext.semanticAnchor {
                // A successful transport reply does not prove the semantic
                // target or canonical metadata survived the actual write.
                let matches = values.filter { $0.id == stored.id }
                let codec = TorahAssociationPayloadCodec()
                guard matches.count == 1, let actual = matches.first,
                      try codec.encodeDocument(.init(items: [actual])) == codec.encodeDocument(.init(items: [stored])),
                      try TorahSemanticAnchorAssociation.decoding(actual,
                        location: .init(spaceId: frozenContext.spaceId, target: frozenContext.target))?.anchor == anchor
                else { throw TorahSemanticAnchorResolutionError.writeUnconfirmed }
                do { try await requireResolvedSemanticAnchor(for: frozenContext) }
                catch { throw TorahSemanticAnchorResolutionError.writeUnconfirmed }
                try authorize()
            }
            persistenceState = .saved
            return values
        } catch {
            if documentActionEpoch == epoch && isActiveDocument && isCurrentRequest() { recordAssociationError(error) }
            throw error
        }
    }

    /// Capture this action before loading an asynchronous item provider. A new
    /// drop gets a new claim, so a later deliberate drop of the same text works.
    public func makeExternalDropInsertionAction(targetBlockId: String?) -> TorahSourceInsertionAction {
        let context = InsertionContext(documentEpoch: documentActionEpoch, inspectorEpoch: nil, selectionID: nil)
        let authorize = insertionAuthorization(context: context)
        let claim = DropClaim()
        return { [weak self] transfer in
            guard let self, !claim.used else { return }
            claim.used = true
            await self.insert(transfer, targetBlockId: targetBlockId, context: context, authorize: authorize)
        }
    }

    public func makeInspectorSourceInsertionAction() -> TorahSourceInsertionAction {
        let context = InsertionContext(
            documentEpoch: documentActionEpoch, inspectorEpoch: noteActionEpoch, selectionID: selection?.id
        )
        let authorize = insertionAuthorization(context: context)
        return { [weak self] transfer in
            await self?.insert(transfer, targetBlockId: nil, context: context, authorize: authorize)
        }
    }

    private func isCurrentInsertion(_ context: InsertionContext) -> Bool {
        guard isActiveDocument, documentActionEpoch == context.documentEpoch else { return false }
        guard let inspectorEpoch = context.inspectorEpoch else { return true }
        return noteActionEpoch == inspectorEpoch && selection?.id == context.selectionID
    }

    private func insertionAuthorization(context: InsertionContext) -> TorahAssociationWriteAuthorization {
        return { [weak self] in
            try Task.checkCancellation()
            guard let self, self.isCurrentInsertion(context) else { throw CancellationError() }
            guard self.insertionEditingPolicy() else {
                throw TorahAssociationRepositoryError.permissionDenied
            }
        }
    }

    private func insert(
        _ transfer: TorahSourceTransfer,
        targetBlockId: String?,
        context: InsertionContext,
        authorize: @escaping TorahAssociationWriteAuthorization
    ) async {
        do {
            try authorize()
            guard let insertionHandler else { throw SessionError.insertionUnavailable }
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
                // The block may already be committed. Revalidate before the
                // separate metadata write; never delete user text as rollback.
                try authorize()
                persistenceState = .saving
                _ = try await associations.addAssociation(
                    item,
                    target: .block(objectId: objectId, blockId: blockId),
                    spaceId: spaceId,
                    authorize: authorize
                )
                guard isCurrentInsertion(context) else { return }
                persistenceState = .saved
                await refreshAssociationSnapshot()
            } catch {
                guard isCurrentInsertion(context) else { return }
                persistenceState = .uncertain(SessionError.partialInsertion.localizedDescription)
                message = SessionError.partialInsertion.localizedDescription
            }
        } catch is CancellationError {
            // A retired action must not replace the current document's status.
        } catch {
            guard isCurrentInsertion(context) else { return }
            persistenceState = .error(error.localizedDescription)
            message = error.localizedDescription
        }
    }

    /// Resolves a picker selection without reading or mutating associations.
    /// Used by native Set filters, whose target is a predicate, not a document.
    public func resolveAssociationSelection(
        _ result: SearchResult,
        rawQuery: String
    ) async throws -> TorahAssociationItem {
        try await associationItem(for: result, rawQuery: rawQuery)
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
        guard isActiveDocument, canEditAssociations, !isCreatingNote else { return }
        isCreatingNote = true
        defer { isCreatingNote = false }
        let requestEpoch = noteActionEpoch
        let inspectorSelectionID = self.selection?.id
        let authorize = noteMutationAuthorization()
        do {
            let outcome = try await notesService.createNote(for: selection, authorize: authorize)
            try authorize()
            await refreshAssociationSnapshot()
            repository.invalidateNotes(for: selection)
            repository.invalidateRelatedDocuments(for: selection)
            guard isActiveDocument, noteActionEpoch == requestEpoch,
                  self.selection?.id == inspectorSelectionID, !Task.isCancelled else { return }
            didChange()
            if let error = outcome.recoveryError { message = error.localizedDescription }
            openObjectHandler?(outcome.objectID, nil)
        } catch {
            repository.invalidateRelatedDocuments(for: selection)
            if isCurrentNoteAction(epoch: requestEpoch, selectionID: inspectorSelectionID) {
                recordAssociationError(error)
            }
        }
    }

    private func open(note: TorahInspectorNote, for selection: TorahInspectorSelection) async {
        guard isActiveDocument, !Task.isCancelled else { return }
        let requestEpoch = noteActionEpoch
        let inspectorSelectionID = self.selection?.id
        do {
            guard let objectId = try await notesService.noteObjectId(noteId: note.id, for: selection) else {
                throw SessionError.staleDocument
            }
            try Task.checkCancellation()
            guard isActiveDocument, noteActionEpoch == requestEpoch,
                  self.selection?.id == inspectorSelectionID else { return }
            openObjectHandler?(objectId, nil)
        } catch {
            if isCurrentNoteAction(epoch: requestEpoch, selectionID: inspectorSelectionID) {
                recordAssociationError(error)
            }
        }
    }

    private func openRelatedDocument(
        _ document: TorahRelatedDocument, actionEpoch: UInt, inspectorSelectionID: String?
    ) {
        guard isCurrentNoteAction(epoch: actionEpoch, selectionID: inspectorSelectionID),
              document.spaceID == spaceId, !document.objectID.isEmpty else { return }
        if let blockID = document.blockID {
            guard !blockID.isEmpty, blockID != document.objectID else { return }
        }
        // This dispatches an exact navigation request; only the destination
        // editor can confirm that the requested block was actually displayed.
        openObjectHandler?(document.objectID, document.blockID)
    }

    private func isCurrentNoteAction(epoch: UInt, selectionID: String?) -> Bool {
        isActiveDocument && noteActionEpoch == epoch && selection?.id == selectionID && !Task.isCancelled
    }

    private func noteMutationAuthorization() -> TorahAssociationWriteAuthorization {
        let requestEpoch = noteActionEpoch
        let inspectorSelectionID = selection?.id
        return { [weak self] in
            try Task.checkCancellation()
            guard let self, self.isActiveDocument, self.noteActionEpoch == requestEpoch,
                  self.selection?.id == inspectorSelectionID else { throw CancellationError() }
            guard self.canEditAssociations else { throw TorahAssociationRepositoryError.permissionDenied }
        }
    }

    public func unlink(
        note: TorahInspectorNote,
        for selection: TorahInspectorSelection,
        didChange: @escaping TorahInspectorHostActions.NotesDidChange
    ) async {
        let requestEpoch = noteActionEpoch
        let inspectorSelectionID = self.selection?.id
        let authorize = noteMutationAuthorization()
        do {
            try await notesService.unlink(noteId: note.id, for: selection, authorize: authorize)
            try authorize()
            await refreshAssociationSnapshot()
            repository.invalidateNotes(for: selection)
            repository.invalidateRelatedDocuments(for: selection)
            try authorize()
            didChange()
        } catch {
            if isCurrentNoteAction(epoch: requestEpoch, selectionID: inspectorSelectionID) {
                recordAssociationError(error)
            }
        }
    }

    public func unlink(
        document: TorahRelatedDocument,
        for selection: TorahInspectorSelection,
        didChange: @escaping TorahInspectorHostActions.NotesDidChange
    ) async {
        let requestEpoch = noteActionEpoch
        let inspectorSelectionID = self.selection?.id
        let authorize = noteMutationAuthorization()
        do {
            try await notesService.unlink(document: document, for: selection, authorize: authorize)
            try authorize()
            await refreshAssociationSnapshot()
            repository.invalidateNotes(for: selection)
            repository.invalidateRelatedDocuments(for: selection)
            try authorize()
            didChange()
        } catch {
            if isCurrentNoteAction(epoch: requestEpoch, selectionID: inspectorSelectionID) {
                recordAssociationError(error)
            }
        }
    }

    private func apply(records: [TorahStoredAssociationRecord]) {
        repository.invalidateRelatedDocuments()
        let previousBlockIDs = linkedBlockIDs
        let relevant = records.filter { $0.spaceId == spaceId && $0.objectId == objectId }
        associationRecords = relevant
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
            items = documentAssociations.filter { !TorahSemanticAnchorAssociation.hasReservedMetadata($0) }
        case .block(let blockId):
            items = associationsByBlockId[blockId] ?? []
        case .semantic(let anchor):
            items = associationRecords.compactMap { record in
                guard record.blockId == nil,
                      let semantic = try? TorahSemanticAnchorAssociation.decoding(record.item, location: record.location),
                      semantic.anchor == anchor else { return nil }
                return record.item
            }
        }
        return items.filter { !Self.isNoteAssociation($0) }
    }

    public func cachedAssociations(for context: TorahAssociationContext) -> [TorahAssociationItem] {
        guard context.spaceId == spaceId, context.objectId == objectId else { return [] }
        return visibleAssociations(for: context)
    }

    public func reportSearchError(_ error: Error) {
        guard !(error is CancellationError) else { return }
        if let torahError = error as? TorahError {
            message = TorahStrings.message(for: torahError, locale: effectiveLocale)
        } else {
            message = error.localizedDescription
        }
    }

    public func searchMessage(for error: Error) -> String {
        if let torahError = error as? TorahError {
            return TorahStrings.message(for: torahError, locale: effectiveLocale)
        }
        return Loc.Pinkha.Torah.Error.backendFailure
    }

    public func validateSearchContext(_ context: TorahAssociationContext) throws {
        try validate(context: context)
    }

    private func validate(context: TorahAssociationContext) throws {
        guard isActiveDocument,
              context.spaceId == spaceId,
              context.objectId == objectId else {
            throw SessionError.staleDocument
        }
        if let anchor = context.semanticAnchor,
           !anchor.belongsTo(spaceID: spaceId, objectID: objectId) {
            throw PinkhaSemanticTextAnchorError.wrongDocument
        }
    }

    private func recordAssociationError(_ error: Error) {
        guard !(error is CancellationError) else { return }
        if error as? TorahSemanticAnchorResolutionError == .writeUnconfirmed {
            persistenceState = .uncertain(error.localizedDescription)
            message = error.localizedDescription
        } else if let repositoryError = error as? TorahAssociationRepositoryError {
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
#endif
