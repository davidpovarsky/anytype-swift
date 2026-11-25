#if canImport(SwiftUI)
import Foundation
import Observation
import SwiftUI
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost
import PinkhaTorahPresentation
import TorahInspectorCore
import TorahInspectorUI

@MainActor
public protocol AnyEditorMountedSurface: AnyObject {
    var sceneID: UUID { get }
    var isForegroundMounted: Bool { get }
    func isBlockVisible(_ id: String) -> Bool
    func reveal(blockID: String, selection: NSRange?)
    func dismissKeyboard()
    func captureActiveCompositionForRecovery()
}

public extension AnyEditorMountedSurface {
    func captureActiveCompositionForRecovery() {}
}

public enum AnyEditorWriteState: Equatable {
    case clean, pending, saving, saved
    case conflict(String), uncertain(String), failed(String)
}

private struct AnyBlockDraft: Sendable {
    var base: AnyEditorBlock
    var inlineMarkdown: String
    var selection: NSRange
    var revision: UInt64
}

enum AnyDocumentReadPurpose: Sendable, Equatable {
    case load, observation, mutationReadback
}

typealias AnyDocumentReadOperation = @Sendable (
    AnyDocumentReadPurpose, AnyEditorDocumentStore, String, AnyHostLease
) async throws -> AnyEditorRead

private struct AnyDocumentComposition {
    let blockID: String
    let owner: UUID
    let text: AnyNativeTextComposition
}

/// One mounted native document. All native work has an account/run lease; each
/// mutation additionally rechecks this UI epoch at the actual dispatch seam.
@MainActor @Observable
public final class AnyDocumentPresentation: Sendable {
    public let objectID: String
    public let workspace: AnyTorahWorkspace
    public let torah: TorahEditorSession
    public private(set) var read: AnyEditorRead?
    public private(set) var writeState = AnyEditorWriteState.clean
    public private(set) var canWrite = false
    public private(set) var isLoading = false
    public private(set) var isMounted = false
    public private(set) var selectedBlockIDs: [String] = []
    public private(set) var selectedTextRange = NSRange(location: 0, length: 0)
    public private(set) var focusedBlockID: String?
    public private(set) var contentRevision: UInt64 = 0
    public private(set) var textHistoryEpochs: [String: UInt64] = [:]
    public var message: String?
    public var showsProperties = false
    public var showsArchiveTransfer = false
    public var showsDraftReview = false
    public private(set) var requiresDraftReview = false
    public private(set) var isComposing = false
    public private(set) var isCreatingTextAnchor = false
    public var sourceDocuments: [TorahRelatedDocument] = []
    public var sourceDocumentsTitle: String?
    public private(set) var nativeProperties: AnyNativeDerivedDocumentProperties?
    public var onOpenObject: ((String, String?) -> Void)?
    private var navigation = AnyNativeDocumentNavigation()
    @ObservationIgnored public weak var surface: (any AnyEditorMountedSurface)?
    @ObservationIgnored public let client: AnyHTTPClient
    @ObservationIgnored public let nativeSession: AnyApplicationSession
    @ObservationIgnored public let documents: AnyEditorDocumentStore
    @ObservationIgnored public let objects: AnyNativeObjectCreator
    @ObservationIgnored public let blocks: AnyNativeBlockCreator
    @ObservationIgnored public let propertyStore: AnyNativePropertyStore?
    @ObservationIgnored public let noteMarker: AnyNativeNoteMarker
    @ObservationIgnored public let capabilities: AnyUIFoundationCapabilities
    @ObservationIgnored let operations: AnyGuardedTorahOperationStore
    @ObservationIgnored let index: AnyGuardedTorahIndex
    @ObservationIgnored let metadata: AnyHTTPTorahRelatedDocumentReader
    @ObservationIgnored let lifetime: AnyUIPresentationLifetime
    @ObservationIgnored private let recovery: AnyNativeLibraryRecovery
    @ObservationIgnored private var recoveryWasRestored = false
    @ObservationIgnored private var registration: UUID?
    @ObservationIgnored private var epoch = UUID()
    // The default still performs the real native read. Tests can delay delivery
    // of that result without replacing native storage, authorization or writes.
    @ObservationIgnored var editorReadOperation: AnyDocumentReadOperation = { _, documents, objectID, lease in
        try await documents.read(objectID: objectID, lease: lease)
    }
    @ObservationIgnored private var editorReadID = UUID()
    @ObservationIgnored private var loadingReadID: UUID?
    @ObservationIgnored private var nativePropertiesReadID = UUID()
    @ObservationIgnored private var nativeMutationID: UUID?
    @ObservationIgnored private var inFlightTextBlockID: String?
    @ObservationIgnored private var refreshAfterMutation = false
    @ObservationIgnored private var loadAfterMutation = false
    @ObservationIgnored private var saveAfterMutation = false
    @ObservationIgnored private var deferredReadTask: Task<Void, Never>?
    @ObservationIgnored private var streamSession: AnyStreamSession?
    @ObservationIgnored private var streamTasks: [Task<Void, Never>] = []
    @ObservationIgnored private var saveTask: Task<Void, Never>?
    @ObservationIgnored private var saving = false
    @ObservationIgnored private var drafts: [String: AnyBlockDraft] = [:]
    @ObservationIgnored private var composition: AnyDocumentComposition?
    @ObservationIgnored private var unmappedDrafts: [String: AnyNativeUnmappedTextDraft] = [:]
    @ObservationIgnored private var lastUndo: AnyPreparedBlockEdit?
    @ObservationIgnored private var semanticAnchorIntent: AnySemanticAnchorIntent?
    @ObservationIgnored private var semanticAnchorPreparationID: UUID?
    @ObservationIgnored private var semanticAnchorMutationID: UUID?
    @ObservationIgnored private var acknowledgedBlockVersions: [String: AnyJSON] = [:]
    @ObservationIgnored private var closingObservers: [Task<Void, Never>] = []
    @ObservationIgnored private var scopeInvalidators: [@Sendable () -> Void] = []
    @ObservationIgnored private var drainHandlers: [@MainActor () async -> Void] = []
    @ObservationIgnored private var revokeHandlers: [@MainActor () -> Void] = []

    public init(client: AnyHTTPClient, session: AnyApplicationSession,
                objects: AnyNativeObjectCreator, blocks: AnyNativeBlockCreator,
                capabilities: AnyUIFoundationCapabilities,
                operations: AnyGuardedTorahOperationStore, noteMarker: AnyNativeNoteMarker,
                objectID: String, lifetime: AnyUIPresentationLifetime,
                recovery: AnyNativeLibraryRecovery,
                hierarchySchema: AnyHierarchySchema? = nil,
                sourceWorkspace: AnytypeTorahWorkspace? = nil) throws {
        guard operations.workspace == session.workspace, noteMarker.workspace == session.workspace,
              objects.workspace == session.workspace, blocks.workspace == session.workspace,
              client.expectedAccountID == session.workspace.accountID, !objectID.isEmpty else {
            throw AnyHostError.wrongWorkspace
        }
        try lifetime.requireActive()
        try recovery.requireWorkspace(session.workspace)
        self.recovery = recovery
        self.objectID = objectID; self.workspace = session.workspace
        self.client = client; self.nativeSession = session; self.objects = objects; self.blocks = blocks
        self.capabilities = capabilities; self.operations = operations; self.lifetime = lifetime
        self.noteMarker = noteMarker
        self.propertyStore = try hierarchySchema.map {
            try AnyNativePropertyStore(client: client, workspace: session.workspace,
                policy: AnyNativePropertyPolicies.workspace(schema: $0, noteMarker: noteMarker))
        }
        let documents = try AnyEditorDocumentStore(client: client, workspace: session.workspace,
                                                   allowedTypeIDs: capabilities.allowedTargetTypes,
                                                   documentTypePolicy: .nativeCanonicalEditorV1)
        self.documents = documents
        let access = try AnyHTTPTorahTargetAccess(client: client, workspace: session.workspace,
                                                 allowedTypeIDs: capabilities.allowedTargetTypes,
                                                   documentTypePolicy: .nativeCanonicalEditorV1)
        let associations = try AnyTorahAssociationRepository(workspace: session.workspace,
                                                             store: operations, access: access)
        let workflow = try AnyNativeWorkflowBindings(client: client, session: session, objects: objects,
                                                      blocks: blocks, noteMarker: noteMarker)
        let noteService = try AnyTorahNotesService(workspace: session.workspace, associations: associations,
                                                   documents: workflow, access: access)
        let metadata = try AnyHTTPTorahRelatedDocumentReader(client: client, workspace: session.workspace,
            allowedTypeIDs: capabilities.allowedTargetTypes, noteCollectionIDs: [noteMarker.collectionID],
            documentTypePolicy: .nativeCanonicalEditorV1)
        self.metadata = metadata
        let index = try AnyGuardedTorahIndex(client: client, workspace: session.workspace)
        self.index = index
        let nativeRelated = try AnyNativeTorahRelatedPresentation(index: index, reader: metadata,
                                                                   associations: associations)
        let notes = try AnySessionTorahNotesService(session: session, objectID: objectID,
            notes: noteService, nativeRelated: nativeRelated)
        let adapter = try AnySessionTorahAssociationRepository(session: session,
            repository: associations, operations: operations)
        self.torah = TorahEditorSession(spaceId: session.workspace.spaceID, objectId: objectID,
            workspace: try sourceWorkspace ?? .sefaria(), associations: adapter, notesService: notes)
        torah.installAssociationEditingPolicy { [weak self] in self?.canMutate == true }
        torah.installInsertionEditingPolicy { [weak self] in self?.canMutate == true }
        torah.installInsertionHandler { [weak self] transfer, target in
            guard let self else { throw AnyHostError.sessionClosed }
            return try await self.insertQuote(transfer, before: target)
        }
        torah.installOpenObjectHandler { [weak self] id, blockID in
            self?.requestOpenObject(id, blockID: blockID)
        }
        torah.installAssociationSnapshotHandler { [weak self] _ in self?.contentRevision &+= 1 }
        torah.installSemanticAnchorResolver { [weak self] anchor in
            guard let self else { throw AnyHostError.sessionClosed }
            return try await self.inspectSemanticAnchor(anchor)
        }
        registration = try lifetime.register(revoke: { [weak self] in self?.revoke() },
                                              drain: { [weak self] in await self?.drain() })
    }

    var mountedOwnerID: UUID { epoch }
    var pendingDeferredEditorRead: Task<Void, Never>? { deferredReadTask }
    public var writeStatusAccessibilityValue: String {
        switch writeState {
        case .clean: "clean"
        case .pending: "pending"
        case .saving: "saving"
        case .saved: "saved"
        case .conflict: "conflict"
        case .uncertain: "uncertain"
        case .failed: "failed"
        }
    }
    public var title: String { read?.snapshot.title ?? "" }
    public var isNavigating: Bool { navigation.isPending }
    public var canMutate: Bool { isMounted && lifetime.isActive && canWrite && !isNavigating && !requiresDraftReview && !isComposing && !isCreatingTextAnchor && surface?.isForegroundMounted == true }
    public var hasPendingEdits: Bool { !drafts.isEmpty || !unmappedDrafts.isEmpty || isComposing || saving }
    public var orderedBlocks: [AnyEditorBlock] {
        guard let snapshot = read?.snapshot else { return [] }
        let byID = Dictionary(uniqueKeysWithValues: snapshot.blocks.map { ($0.id, $0) })
        return snapshot.depthFirstIDs.compactMap { byID[$0] }
    }

    public func source(for block: AnyEditorBlock) -> String { drafts[block.id]?.inlineMarkdown ?? block.text }
    public func projection(for block: AnyEditorBlock) -> AnyInlineMarkdown {
        if let buffer = unmappedDrafts[block.id] { return .init(literal: buffer.display) }
        return block.type == "code" ? .init(literal: source(for: block)) : .init(source(for: block))
    }

    func unmappedDisplay(for blockID: String) -> String? { unmappedDrafts[blockID]?.display }

    public func mount(surface: any AnyEditorMountedSurface) {
        guard lifetime.isActive, !isNavigating else { return }
        if !isMounted {
            epoch = UUID()
            retireEditorReads()
        }
        self.surface = surface; isMounted = true
        torah.activateDocument()
    }

    /// The normal Note/related-document route closes the actual owned sheets
    /// before changing the NavigationStack. A push alone does not remove the
    /// source editor from its parent or dismiss its presented inspector.
    public func requestOpenObject(_ objectID: String, blockID: String?) {
        let ownerID = epoch
        do {
            try requireMounted(ownerID)
            guard !isNavigating, !showsArchiveTransfer, !showsDraftReview,
                  AnyEditorBlock.validID(objectID),
                  blockID.map(AnyEditorBlock.validID) ?? true else { return }
            let host: AnyNativeNavigationHost = torah.presentationHost == .properties ? .properties : .editor
            let dismissals = AnyNativeDocumentNavigation.dismissalOrder(
                inspectorHost: torah.selection == nil ? nil : host,
                searchHost: torah.isSearchPresented ? host : nil,
                showsProperties: showsProperties, showsSourceDocuments: sourceDocumentsTitle != nil)
            guard navigation.begin(ownerID: ownerID,
                                   route: .init(objectID: objectID, blockID: blockID),
                                   dismissals: dismissals) else { return }
            // Retire captured source actions now; their native durable receipts
            // retain their original scope. No pending draft is auto-saved.
            torah.deactivateDocument()
            invalidateSourceScope()
            continueNavigation(ownerID: ownerID)
        } catch {
            navigation.cancel()
            message = AnyUIErrorText.describe(error)
        }
    }

    func ownedPresentationDidDismiss(_ sheet: AnyNativeNavigationDismissal, ownerID: UUID) {
        guard navigation.isOwned(by: ownerID) else { return }
        do {
            try requireMounted(ownerID)
            guard navigation.didDismiss(sheet, ownerID: ownerID) else { return }
            continueNavigation(ownerID: ownerID)
        } catch { unmount() }
    }

    private func continueNavigation(ownerID: UUID) {
        guard navigation.isOwned(by: ownerID) else { return }
        do {
            try requireMounted(ownerID)
            switch navigation.nextDismissal {
            case .editorInspector, .propertyInspector: torah.selection = nil
            case .editorSearch, .propertySearch: torah.isSearchPresented = false
            case .properties: showsProperties = false
            case .sourceDocuments: sourceDocumentsTitle = nil
            case nil:
                guard let route = navigation.take(ownerID: ownerID) else { return }
                let open = onOpenObject
                // Revoke the old mounted scope synchronously before publishing
                // a new route; reopening it later creates a fresh owner epoch.
                unmount()
                open?(route.objectID, route.blockID)
            }
        } catch { unmount() }
    }

    public func load() async {
        guard lifetime.isActive else { return }
        guard !saving else { loadAfterMutation = true; return }
        guard !isLoading else { return }
        let requestEpoch = epoch, requestID = UUID()
        editorReadID = requestID; loadingReadID = requestID; isLoading = true
        defer {
            if loadingReadID == requestID {
                loadingReadID = nil; isLoading = false
            }
        }
        do {
            let documents = documents, objectID = objectID, client = client
            let readOperation = editorReadOperation
            let result = try await nativeSession.perform { lease in
                let value = try await readOperation(.load, documents, objectID, lease)
                let member = try await client.requestJSON(method: "GET",
                    path: ["v1", "spaces", lease.workspace.spaceID, "members", "me"])
                try AnyHTTPTorahTargetAccess.validateMember(member, workspace: lease.workspace, intent: .read)
                let writable = ["owner", "admin", "writer"].contains(member["permission"]?.string ?? "")
                try await lease.validate()
                return (value, writable)
            }
            guard mayPublishRead(requestID, owner: requestEpoch) else { return }
            accept(result.0); canWrite = result.1
            await torah.refreshAssociationSnapshot()
            guard mayPublishRead(requestID, owner: requestEpoch) else { return }
            try await refreshNativeProperties(expectedEpoch: requestEpoch, editorRequestID: requestID)
            guard mayPublishRead(requestID, owner: requestEpoch) else { return }
            if streamSession == nil { startObservation() }
        } catch {
            guard mayPublishRead(requestID, owner: requestEpoch) else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    private func mayPublishRead(_ requestID: UUID, owner: UUID) -> Bool {
        owner == epoch && lifetime.isActive && editorReadID == requestID &&
            !saving && !Task.isCancelled
    }

    private func retireEditorReads() {
        editorReadID = UUID()
        loadingReadID = nil; isLoading = false
    }

    /// Only one native edit can own presentation receipts at a time. Text input
    /// remains enabled; its newer draft revisions are rebased after the receipt.
    private func beginNativeMutation(owner: UUID) throws -> UUID {
        try requireMounted(owner)
        guard !saving else { throw AnyHostError.changedDocument }
        let id = UUID()
        nativeMutationID = id; saving = true
        if loadingReadID != nil { loadAfterMutation = true }
        retireEditorReads()
        return id
    }

    private func ownsNativeMutation(_ id: UUID, owner: UUID) -> Bool {
        nativeMutationID == id && epoch == owner && lifetime.isActive
    }

    private func finishNativeMutation(_ id: UUID, owner: UUID, completed: Bool) {
        guard ownsNativeMutation(id, owner: owner) else { return }
        nativeMutationID = nil; inFlightTextBlockID = nil; saving = false
        // Also retire reads that were started while native work was pending.
        retireEditorReads()
        if isComposing { writeState = .pending }
        retainRecovery()
        let reload = loadAfterMutation, refresh = refreshAfterMutation
        let resumeSave = saveAfterMutation && completed
        loadAfterMutation = false; refreshAfterMutation = false; saveAfterMutation = false
        if reload || refresh {
            deferredReadTask?.cancel()
            deferredReadTask = Task { [weak self] in
                guard let self, epoch == owner, lifetime.isActive, !Task.isCancelled else { return }
                if reload { await load() }
                else { await refreshEditor(expectedEpoch: owner) }
            }
        }
        if resumeSave, !drafts.isEmpty, !isComposing { scheduleSave() }
    }

    private func acceptAcknowledged(_ value: AnyEditorRead, blockID: String?,
                                    undo: AnyPreparedBlockEdit?) {
        retireEditorReads()
        if let blockID, let block = value.snapshot.blocks.first(where: { $0.id == blockID }) {
            acknowledgedBlockVersions[blockID] = block.native["_ver"]
        }
        accept(value)
        // A later native change may have occurred after the verified receipt.
        // Retain Undo only when this exact read still has the receipt's version.
        lastUndo = undo?.expectedVersion == value.nativeVersion ? undo : nil
    }

    private func accept(_ value: AnyEditorRead) {
        if let previous = read {
            if previous.snapshot.revision != value.snapshot.revision { invalidateSourceScope() }
            let prior = Dictionary(uniqueKeysWithValues: previous.snapshot.blocks.map { ($0.id, $0) })
            for block in value.snapshot.blocks {
                if let before = prior[block.id], before.native["_ver"] != block.native["_ver"],
                   acknowledgedBlockVersions[block.id] != block.native["_ver"] {
                    textHistoryEpochs[block.id, default: 0] &+= 1
                    lastUndo = nil
                }
            }
        }
        read = value
        restoreRecoveryIfNeeded(value.snapshot)
        let byID = Dictionary(uniqueKeysWithValues: value.snapshot.blocks.map { ($0.id, $0) })
        for (id, draft) in drafts {
            guard let native = byID[id], native.native["_ver"] == draft.base.native["_ver"],
                  native.text == draft.base.text else {
                if !saving { writeState = .conflict(AnyUIErrorText.changedDocument) }
                continue
            }
        }
        let reachable = Set(value.snapshot.depthFirstIDs)
        if !Set(selectedBlockIDs).isSubset(of: reachable) {
            selectedBlockIDs = []; focusedBlockID = nil; invalidateSourceScope()
        }
        contentRevision &+= 1
    }

    public func select(blockIDs: [String], focusedBlockID: String?, range: NSRange) {
        guard Set(blockIDs).count == blockIDs.count,
              Set(blockIDs).isSubset(of: Set(read?.snapshot.depthFirstIDs ?? [])) else { return }
        if selectedBlockIDs != blockIDs { invalidateSourceScope() }
        selectedBlockIDs = blockIDs; self.focusedBlockID = focusedBlockID; selectedTextRange = range
        retainRecovery()
    }

    /// Prepare an anchor from an unchanged mounted selection and a real current
    /// native read. Preview/Cancel never flush drafts or issue a write.
    public func prepareSemanticAnchor(blockID: String, range: NSRange,
                                      visibleText: String) async throws -> AnySemanticAnchorIntent {
        let owner = epoch, requestID = UUID()
        try requireMounted(owner)
        guard canMutate, !hasPendingEdits, semanticAnchorIntent == nil,
              selectedBlockIDs == [blockID], focusedBlockID == blockID,
              selectedTextRange == range, range.location != NSNotFound,
              range.location >= 0, range.length > 0,
              range.location <= visibleText.utf16.count,
              range.length <= visibleText.utf16.count - range.location,
              let original = read,
              let block = original.snapshot.blocks.first(where: { $0.id == blockID }),
              projection(for: block).display.utf8.elementsEqual(visibleText.utf8) else {
            throw AnyHostError.invalidSelection
        }
        semanticAnchorPreparationID = requestID
        defer {
            if semanticAnchorPreparationID == requestID { semanticAnchorPreparationID = nil }
        }
        let documents = documents, objectID = objectID
        let capture = try await nativeSession.perform { lease in
            let current = try await documents.read(objectID: objectID, lease: lease)
            guard current.generation == original.generation,
                  current.engineStartedAt == original.engineStartedAt,
                  current.nativeVersion == original.nativeVersion,
                  current.snapshot.revision == original.snapshot.revision else {
                throw AnyHostError.changedDocument
            }
            let anchor = try PinkhaSemanticTextAnchor(spaceID: lease.workspace.spaceID, objectID: objectID)
            return try AnySemanticAnchorCapture(read: current, blockID: blockID, range: range, anchor: anchor)
        }
        try Task.checkCancellation()
        try requireMounted(owner)
        guard semanticAnchorPreparationID == requestID, canMutate, !hasPendingEdits,
              selectedBlockIDs == [blockID], focusedBlockID == blockID, selectedTextRange == range,
              let latest = read else { throw AnyHostError.changedDocument }
        _ = try capture.prepare(current: latest, documents: documents)
        let intent = AnySemanticAnchorIntent(owner: owner, capture: capture,
            selectedText: (visibleText as NSString).substring(with: range))
        semanticAnchorIntent = intent
        return intent
    }

    public func cancelSemanticAnchor(_ intent: AnySemanticAnchorIntent) {
        guard semanticAnchorIntent === intent else { return }
        semanticAnchorIntent = nil
        intent.consumed = true
    }

    /// Only the explicit confirmation calls this method. The existing native
    /// conditional PATCH, account lease and final dispatch authorization remain
    /// the only write path; a lost/uncertain reply is never automatically retried.
    public func applySemanticAnchor(_ intent: AnySemanticAnchorIntent) async throws -> PinkhaSemanticTextAnchor {
        try Task.checkCancellation()
        try requireMounted(intent.owner)
        guard semanticAnchorIntent === intent, !intent.consumed,
              canMutate, !hasPendingEdits else { throw AnyHostError.changedDocument }
        let mutationID = try beginNativeMutation(owner: intent.owner)
        intent.consumed = true
        semanticAnchorIntent = nil
        semanticAnchorMutationID = mutationID
        isCreatingTextAnchor = true
        writeState = .saving
        var completed = false
        defer {
            if semanticAnchorMutationID == mutationID {
                semanticAnchorMutationID = nil
                isCreatingTextAnchor = false
            }
            finishNativeMutation(mutationID, owner: intent.owner, completed: completed)
        }
        do {
            let documents = documents, objectID = objectID, capture = intent.capture
            let owner = intent.owner, readOperation = editorReadOperation
            let authorize: @Sendable () async throws -> Void = { [weak self] in
                guard let self else { throw AnyHostError.sessionClosed }
                try await self.requireSemanticAnchorMutation(mutationID, owner: owner)
            }
            let result = try await nativeSession.perform { lease in
                let current = try await documents.read(objectID: objectID, lease: lease)
                let edit = try capture.prepare(current: current, documents: documents)
                let receipt = try await documents.apply(edit, lease: lease, authorize: authorize)
                guard receipt.readback == .verifiedCurrent else { throw AnyHostError.writeUncertain }
                let readback = try await readOperation(.mutationReadback, documents, objectID, lease)
                try capture.verifyReadback(readback)
                return (receipt, readback)
            }
            try requireSemanticAnchorMutation(mutationID, owner: owner)
            acceptAcknowledged(result.1, blockID: intent.blockID, undo: result.0.undo)
            writeState = .saved
            completed = true
            return intent.anchor
        } catch {
            if ownsNativeMutation(mutationID, owner: intent.owner) {
                switch error {
                case AnyHostError.changedDocument: writeState = .conflict(AnyUIErrorText.changedDocument)
                case AnyHostError.writeUncertain, AnyEngineError.writeUncertain:
                    writeState = .uncertain(AnyUIErrorText.uncertainWrite)
                default: writeState = .failed(AnyUIErrorText.describe(error))
                }
            }
            throw error
        }
    }

    private func requireSemanticAnchorMutation(_ mutationID: UUID, owner: UUID) throws {
        try requireMounted(owner)
        guard ownsNativeMutation(mutationID, owner: owner),
              semanticAnchorMutationID == mutationID, canWrite,
              drafts.isEmpty, unmappedDrafts.isEmpty, !isComposing, !requiresDraftReview else {
            throw AnyHostError.changedDocument
        }
    }

    /// Read-only source linking validation. It cannot publish a display read,
    /// navigate, change selection, write a marker, or retry any native mutation.
    public func inspectSemanticAnchor(_ anchor: PinkhaSemanticTextAnchor) async throws
        -> PinkhaSemanticTextAnchorResolver.Resolution {
        let owner = epoch
        try requireMounted(owner)
        guard !hasPendingEdits, !isLoading, !isCreatingTextAnchor else { throw AnyHostError.changedDocument }
        guard anchor.belongsTo(spaceID: workspace.spaceID, objectID: objectID) else {
            throw PinkhaSemanticTextAnchorError.wrongDocument
        }
        let documents = documents, objectID = objectID
        let current = try await nativeSession.perform {
            try await documents.read(objectID: objectID, lease: $0)
        }
        try Task.checkCancellation()
        try requireMounted(owner)
        guard !hasPendingEdits, !isLoading, !isCreatingTextAnchor else { throw AnyHostError.changedDocument }
        return try AnySemanticAnchorDocument.resolve(anchor, read: current)
    }

    /// Resolve only from a newly authorized full native document. The shared
    /// resolver reports missing/ambiguous markers rather than searching old text
    /// or trusting an old offset; valid split fragments stay in native order.
    @discardableResult
    public func revealSemanticAnchor(_ anchor: PinkhaSemanticTextAnchor) async throws
        -> PinkhaSemanticTextAnchorResolver.Resolution {
        let owner = epoch, requestID = UUID()
        try requireMounted(owner)
        guard !hasPendingEdits, !isLoading else { throw AnyHostError.changedDocument }
        guard anchor.belongsTo(spaceID: workspace.spaceID, objectID: objectID) else {
            throw PinkhaSemanticTextAnchorError.wrongDocument
        }
        editorReadID = requestID
        let documents = documents, objectID = objectID
        let current = try await nativeSession.perform {
            try await documents.read(objectID: objectID, lease: $0)
        }
        try requireMounted(owner)
        guard mayPublishRead(requestID, owner: owner), !hasPendingEdits else {
            throw AnyHostError.changedDocument
        }
        let resolution = try AnySemanticAnchorDocument.resolve(anchor, read: current)
        accept(current)
        if case .resolved(let fragments) = resolution, let first = fragments.first {
            select(blockIDs: fragments.map(\.blockID), focusedBlockID: first.blockID, range: first.range)
            surface?.reveal(blockID: first.blockID, selection: first.range)
        }
        return resolution
    }

    public func changeText(blockID: String, source: String, displaySelection: NSRange,
                           renderedBlock: AnyEditorBlock) throws {
        try requireMounted(epoch)
        guard canWrite, !requiresDraftReview, !isComposing, !isCreatingTextAnchor, source.utf8.count <= 65_536,
              let block = read?.snapshot.blocks.first(where: { $0.id == blockID }),
              read?.snapshot.depthFirstIDs.contains(blockID) == true,
              renderedBlock.id == blockID,
              (block.type == "code" || AnyInlineMarkdown(source).isEditable) else { throw AnyHostError.invalidSelection }
        if drafts[blockID] == nil {
            guard renderedBlock.native["_ver"] == block.native["_ver"], renderedBlock.text == block.text else {
                throw AnyHostError.changedDocument
            }
        }
        var draft = drafts[blockID] ?? .init(base: block, inlineMarkdown: block.text,
                                             selection: displaySelection, revision: 0)
        draft.inlineMarkdown = source; draft.selection = displaySelection; draft.revision &+= 1
        var candidate = drafts
        if source == draft.base.text, inFlightTextBlockID != blockID {
            candidate.removeValue(forKey: blockID)
        }
        else { candidate[blockID] = draft }
        // Retain the exact source/base before accepting the visible edit.
        try captureRecovery(candidate)
        drafts = candidate
        select(blockIDs: selectedBlockIDs.contains(blockID) ? selectedBlockIDs : [blockID],
               focusedBlockID: blockID, range: displaySelection)
        writeState = drafts.isEmpty ? .clean : .pending
        contentRevision &+= 1
        scheduleSave()
    }

    private func scheduleSave() {
        // Once the debounce has entered flush, it owns a real native receipt.
        // Later typing must queue another revision, not cancel that write.
        guard !saving else { saveAfterMutation = true; return }
        saveTask?.cancel()
        saveTask = Task { [weak self] in
            do { try await Task.sleep(for: .milliseconds(450)) } catch { return }
            await self?.flush()
        }
    }

    /// Called before UIKit creates its first marked range. Reserve a new local
    /// revision now, so an earlier in-flight save cannot erase this input.
    func beginTextComposition(renderedBlock: AnyEditorBlock, source: String,
                              selection: NSRange) throws {
        try requireMounted(epoch)
        guard canMutate, composition == nil, unmappedDrafts.isEmpty,
              let current = read?.snapshot.blocks.first(where: { $0.id == renderedBlock.id }),
              read?.snapshot.depthFirstIDs.contains(renderedBlock.id) == true,
              source.utf8.elementsEqual(self.source(for: renderedBlock).utf8) else {
            throw AnyHostError.invalidSelection
        }
        if drafts[current.id] == nil {
            guard current.native["_ver"] == renderedBlock.native["_ver"], current.text == renderedBlock.text else {
                throw AnyHostError.changedDocument
            }
        }
        let text = try AnyNativeTextComposition(source: source, literal: current.type == "code", selection: selection)
        var draft = drafts[current.id] ?? .init(base: current, inlineMarkdown: source, selection: selection, revision: 0)
        draft.revision &+= 1; draft.selection = selection
        var candidate = drafts; candidate[current.id] = draft
        try captureRecovery(candidate)
        drafts = candidate
        composition = .init(blockID: current.id, owner: epoch, text: text)
        isComposing = true
        if !saving { saveTask?.cancel() }
        invalidateSourceScope()
        writeState = .pending; contentRevision &+= 1
    }

    /// Preflights each proposed buffer before UIKit accepts it, then records
    /// the actual buffer after UIKit's input operation. No native write occurs.
    func stageTextComposition(blockID: String, display: String, selection: NSRange) throws {
        guard let composition, composition.blockID == blockID,
              var draft = drafts[blockID], display.utf8.count <= 65_536 else {
            throw AnyNativeRecoveryError.invalidSnapshot
        }
        _ = try AnyInlineMarkdown(literal: display).sourceRange(for: selection)
        var candidate = drafts, unmapped = unmappedDrafts
        do {
            draft.inlineMarkdown = try composition.text.source(display: display, selection: selection)
            draft.selection = selection; draft.revision &+= 1
            candidate[blockID] = draft; unmapped.removeValue(forKey: blockID)
        } catch is AnyInlineTextError {
            // Keep the visible composition without flattening links/unknown
            // markup into a newly writable native source.
            unmapped[blockID] = try .init(base: draft.base, baselineSource: composition.text.baseline.source,
                display: display, selection: selection, reason: "inlineCompositionCannotMapLosslessly")
        }
        try captureRecovery(candidate, unmapped: unmapped)
        drafts = candidate; unmappedDrafts = unmapped
        selectedBlockIDs = [blockID]; focusedBlockID = blockID; selectedTextRange = selection
        contentRevision &+= 1
    }

    @discardableResult
    func finishTextComposition(blockID: String, display: String, selection: NSRange,
                               allowSaving: Bool) -> String? {
        guard let active = composition, active.blockID == blockID else { return nil }
        do { try stageTextComposition(blockID: blockID, display: display, selection: selection) }
        catch {
            // Accepted UIKit text must remain visible/copyable if an unexpected
            // post-input failure occurs. Do not substitute the previous source.
            if let draft = drafts[blockID], let buffer = try? AnyNativeUnmappedTextDraft(
                base: draft.base, baselineSource: active.text.baseline.source,
                display: display, selection: .init(location: display.utf16.count, length: 0),
                reason: "compositionRecoveryFailed") {
                unmappedDrafts[blockID] = buffer
            }
            message = AnyUIErrorText.describe(error)
        }
        composition = nil; isComposing = false
        if unmappedDrafts[blockID] == nil, let draft = drafts[blockID],
           draft.inlineMarkdown == draft.base.text, inFlightTextBlockID != blockID {
            drafts.removeValue(forKey: blockID)
        }
        let output = unmappedDrafts[blockID] == nil ? drafts[blockID]?.inlineMarkdown ?? active.text.baseline.source : nil
        if !unmappedDrafts.isEmpty {
            requiresDraftReview = true; writeState = .conflict(AnyUIErrorText.unmappedComposition)
        } else { writeState = drafts.isEmpty ? .clean : .pending }
        retainRecovery(); contentRevision &+= 1
        if allowSaving, active.owner == epoch, canMutate { scheduleSave() }
        return output
    }

    public func flush() async {
        guard !drafts.isEmpty, canMutate else { return }
        guard !saving else { saveAfterMutation = true; return }
        let requestEpoch = epoch
        let mutationID: UUID
        do { mutationID = try beginNativeMutation(owner: requestEpoch) }
        catch { return }
        var completed = false
        writeState = .saving
        defer { finishNativeMutation(mutationID, owner: requestEpoch, completed: completed) }
        while let (id, draft) = drafts.sorted(by: { $0.key < $1.key }).first {
            guard !isComposing, unmappedDrafts.isEmpty else { return }
            do {
                try requireMounted(requestEpoch)
                guard ownsNativeMutation(mutationID, owner: requestEpoch) else { return }
                inFlightTextBlockID = id
                let documents = documents, objectID = objectID
                let readOperation = editorReadOperation
                let authorize = mutationAuthorization(requestEpoch)
                let result = try await nativeSession.perform { lease in
                    let current = try await documents.read(objectID: objectID, lease: lease)
                    guard let native = current.snapshot.blocks.first(where: { $0.id == id }),
                          current.snapshot.depthFirstIDs.contains(id),
                          native.native["_ver"] == draft.base.native["_ver"],
                          native.text == draft.base.text else { throw AnyHostError.changedDocument }
                    let edit = try documents.prepareTextEdit(current, blockID: id,
                                                              inlineMarkdown: draft.inlineMarkdown)
                    let receipt = try await documents.apply(edit, lease: lease, authorize: authorize)
                    guard receipt.readback == .verifiedCurrent else { throw AnyHostError.writeUncertain }
                    let readback = try await readOperation(.mutationReadback, documents, objectID, lease)
                    guard let saved = readback.snapshot.blocks.first(where: { $0.id == id }),
                          saved.text == draft.inlineMarkdown else { throw AnyHostError.writeUncertain }
                    return (receipt, readback, saved)
                }
                try requireMounted(requestEpoch)
                guard ownsNativeMutation(mutationID, owner: requestEpoch) else { return }
                inFlightTextBlockID = nil
                if var latest = drafts[id] {
                    if latest.revision == draft.revision { drafts.removeValue(forKey: id) }
                    else { latest.base = result.2; drafts[id] = latest }
                }
                acceptAcknowledged(result.1, blockID: id, undo: result.0.undo)
                writeState = drafts.isEmpty ? .saved : .saving
            } catch {
                guard ownsNativeMutation(mutationID, owner: requestEpoch) else { return }
                inFlightTextBlockID = nil
                switch error {
                case AnyHostError.changedDocument: writeState = .conflict(AnyUIErrorText.changedDocument)
                case AnyHostError.writeUncertain, AnyEngineError.writeUncertain:
                    writeState = .uncertain(AnyUIErrorText.uncertainWrite)
                default: writeState = .failed(AnyUIErrorText.describe(error))
                }
                return
            }
        }
        completed = true
    }

    public func discardLocalDrafts() {
        guard !isComposing else { return }
        saveTask?.cancel(); drafts.removeAll(); lastUndo = nil
        unmappedDrafts.removeAll()
        requiresDraftReview = false
        retainRecovery()
        writeState = .clean; contentRevision &+= 1
    }

    public var localDraftTextForCopy: String {
        let visible = orderedBlocks.map { unmappedDrafts[$0.id]?.display ?? source(for: $0) }
        let visibleIDs = Set(orderedBlocks.map(\.id))
        let detached = drafts.filter { !visibleIDs.contains($0.key) }
            .sorted { $0.key < $1.key }.map { unmappedDrafts[$0.key]?.display ?? $0.value.inlineMarkdown }
        let additional = unmappedDrafts.filter { !visibleIDs.contains($0.key) && drafts[$0.key] == nil }
            .sorted { $0.key < $1.key }.map { $0.value.display }
        return (visible + detached + additional).joined(separator: "\n\n")
    }

    public var recoveredDrafts: [AnyNativeRecoveredBlockDraft] {
        drafts.sorted { $0.key < $1.key }.compactMap { _, value in
            try? .init(base: value.base, inlineMarkdown: value.inlineMarkdown,
                       selection: value.selection, revision: value.revision)
        }
    }

    public func resumeRecoveredDrafts() async {
        guard requiresDraftReview, unmappedDrafts.isEmpty, !isComposing else { return }
        await load()
        guard let current = read?.snapshot, isMounted, lifetime.isActive else { return }
        let byID = Dictionary(uniqueKeysWithValues: current.blocks.map { ($0.id, $0) })
        for item in recoveredDrafts {
            switch AnyNativeDraftReconciliation.evaluate(item, current: byID[item.blockID],
                                                        reachable: current.depthFirstIDs.contains(item.blockID)) {
            case .alreadyStored: drafts.removeValue(forKey: item.blockID)
            case .requiresReview: break
            case .conflict:
                writeState = .conflict(AnyUIErrorText.changedDocument)
                retainRecovery()
                return
            }
        }
        requiresDraftReview = false
        showsDraftReview = false
        writeState = drafts.isEmpty ? .saved : .pending
        retainRecovery()
        await flush()
    }

    public var recoveredUnmappedDrafts: [AnyNativeUnmappedTextDraft] {
        unmappedDrafts.values.sorted { $0.blockID < $1.blockID }
    }

    private func captureRecovery(_ values: [String: AnyBlockDraft]? = nil,
                                 unmapped: [String: AnyNativeUnmappedTextDraft]? = nil) throws {
        guard recoveryWasRestored else { return }
        let values = values ?? drafts
        let records = try values.values.map {
            try AnyNativeRecoveredBlockDraft(base: $0.base, inlineMarkdown: $0.inlineMarkdown,
                                              selection: $0.selection, revision: $0.revision)
        }
        try recovery.save(.init(workspace: workspace, objectID: objectID, drafts: records,
            selectedBlockIDs: selectedBlockIDs, focusedBlockID: focusedBlockID, selection: selectedTextRange,
            unmappedDrafts: Array((unmapped ?? unmappedDrafts).values)))
    }

    private func retainRecovery() {
        do { try captureRecovery() }
        catch { message = AnyUIErrorText.describe(error) }
    }

    private func restoreRecoveryIfNeeded(_ snapshot: AnyEditorSnapshot) {
        guard !recoveryWasRestored else { return }
        recoveryWasRestored = true
        do {
            guard let saved = try recovery.document(objectID, workspace: workspace) else { return }
            guard snapshot.spaceID == workspace.spaceID, snapshot.objectID == objectID,
                  snapshot.dataset == saved.dataset else { throw AnyNativeRecoveryError.wrongWorkspace }
            let byID = Dictionary(uniqueKeysWithValues: snapshot.blocks.map { ($0.id, $0) })
            let reachable = Set(snapshot.depthFirstIDs)
            for item in saved.drafts {
                let state = AnyNativeDraftReconciliation.evaluate(item, current: byID[item.blockID],
                                                                 reachable: reachable.contains(item.blockID))
                guard state != .alreadyStored else { continue }
                let base = try AnyEditorBlock(native: item.baseNative)
                drafts[item.blockID] = .init(base: base, inlineMarkdown: item.inlineMarkdown,
                                              selection: item.selection, revision: item.revision)
                textHistoryEpochs[item.blockID, default: 0] &+= 1
            }
            unmappedDrafts = Dictionary(uniqueKeysWithValues: saved.unmappedDrafts.map { ($0.blockID, $0) })
            selectedBlockIDs = saved.selectedBlockIDs.filter { reachable.contains($0) }
            focusedBlockID = saved.focusedBlockID.flatMap { reachable.contains($0) ? $0 : nil }
            selectedTextRange = saved.selection
            if let id = focusedBlockID, let current = byID[id],
               NSMaxRange(selectedTextRange) > projection(for: current).display.utf16.count {
                selectedTextRange = .init(location: 0, length: 0)
            }
            requiresDraftReview = !drafts.isEmpty || !unmappedDrafts.isEmpty
            writeState = requiresDraftReview ? .conflict(AnyUIErrorText.recoveredDrafts) : .clean
            retainRecovery()
        } catch { message = AnyUIErrorText.describe(error); canWrite = false; requiresDraftReview = true }
    }

    public func undoLastNativeEdit() async {
        guard !hasPendingEdits, canMutate, let undo = lastUndo else { return }
        let requestEpoch = epoch
        let mutationID: UUID
        do { mutationID = try beginNativeMutation(owner: requestEpoch) }
        catch { return }
        var completed = false
        defer { finishNativeMutation(mutationID, owner: requestEpoch, completed: completed) }
        do {
            let documents = documents, objectID = objectID
            let authorize = mutationAuthorization(requestEpoch), readOperation = editorReadOperation
            let result = try await nativeSession.perform { lease in
                let receipt = try await documents.apply(undo, lease: lease, authorize: authorize)
                guard receipt.readback == .verifiedCurrent else { throw AnyHostError.writeUncertain }
                let current = try await readOperation(.mutationReadback, documents, objectID, lease)
                return (receipt, current)
            }
            try requireMounted(requestEpoch)
            guard ownsNativeMutation(mutationID, owner: requestEpoch) else { return }
            acceptAcknowledged(result.1, blockID: undo.blockID, undo: result.0.undo)
            completed = true
        } catch {
            guard ownsNativeMutation(mutationID, owner: requestEpoch) else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    public func setWritingStyle(direction: AnyWritingDirection? = nil, alignment: AnyTextAlignment? = nil) async {
        let requestEpoch = epoch
        await flush()
        guard requestEpoch == epoch, !hasPendingEdits, canMutate, !selectedBlockIDs.isEmpty else { return }
        let mutationID: UUID
        do { mutationID = try beginNativeMutation(owner: requestEpoch) }
        catch { return }
        var completed = false
        defer { finishNativeMutation(mutationID, owner: requestEpoch, completed: completed) }
        do {
            let selected = selectedBlockIDs
            for id in selected {
                let documents = documents, objectID = objectID, authorize = mutationAuthorization(requestEpoch)
                let readOperation = editorReadOperation
                let result = try await nativeSession.perform { lease in
                    let current = try await documents.read(objectID: objectID, lease: lease)
                    guard let block = current.snapshot.blocks.first(where: { $0.id == id }) else {
                        throw AnyHostError.invalidSelection
                    }
                    let edit = try documents.prepareWritingStyle(current, blockID: id,
                        direction: direction ?? block.direction ?? .natural,
                        alignment: alignment ?? block.alignment ?? .natural)
                    let receipt = try await documents.apply(edit, lease: lease, authorize: authorize)
                    guard receipt.readback == .verifiedCurrent else { throw AnyHostError.writeUncertain }
                    let readback = try await readOperation(.mutationReadback, documents, objectID, lease)
                    return (receipt, readback)
                }
                try requireMounted(requestEpoch)
                guard ownsNativeMutation(mutationID, owner: requestEpoch) else { return }
                acceptAcknowledged(result.1, blockID: id, undo: result.0.undo)
            }
            completed = true
        } catch {
            guard ownsNativeMutation(mutationID, owner: requestEpoch) else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    func recordEditorDiagnostic(_ phase: AnyNativeEditorDiagnostics.Phase,
                                request: UUID? = nil, expectedOwner: UUID? = nil,
                                errorType: String? = nil) {
        AnyNativeEditorDiagnostics.record(phase, request: request,
            ownerMatches: expectedOwner.map { $0 == epoch },
            mounted: isMounted, active: lifetime.isActive, saving: saving, errorType: errorType,
            canMutate: canMutate, canWrite: canWrite, navigating: isNavigating,
            draftReview: requiresDraftReview, composing: isComposing,
            foreground: surface?.isForegroundMounted)
    }

    public func addParagraph(before targetID: String? = nil) async {
        let requestEpoch = epoch, diagnosticRequest = UUID()
        recordEditorDiagnostic(.addParagraphEntered, request: diagnosticRequest, expectedOwner: requestEpoch)
        do {
            let id = try await createBlock(type: "paragraph", text: "", before: targetID,
                                           direction: .natural, diagnosticRequest: diagnosticRequest)
            try requireMounted(requestEpoch)
            focusedBlockID = id; selectedBlockIDs = [id]; selectedTextRange = .init(location: 0, length: 0)
            surface?.reveal(blockID: id, selection: selectedTextRange)
            AnyNativeEditorDiagnostics.record(.addParagraphCompleted, request: diagnosticRequest,
                ownerMatches: requestEpoch == epoch, mounted: isMounted, active: lifetime.isActive, saving: saving)
        } catch {
            recordEditorDiagnostic(.addParagraphFailed, request: diagnosticRequest, expectedOwner: requestEpoch,
                                   errorType: String(reflecting: type(of: error)))
            guard requestEpoch == epoch, lifetime.isActive else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    private func insertQuote(_ transfer: TorahSourceTransfer, before targetID: String?) async throws -> String {
        let direction: AnyWritingDirection = transfer.direction == "rtl" ? .rightToLeft :
            (transfer.direction == "ltr" ? .leftToRight : .natural)
        // Markdown escaping changes storage syntax only. The visible editable
        // quote remains precisely the provider's text; citation is metadata.
        let text = AnyInlineMarkdown.escapeLiteral(transfer.text)
        return try await createBlock(type: "quote", text: text, before: targetID, direction: direction,
                                     untargetedPlacement: .afterLastVisibleBlock)
    }

    private func createBlock(type: String, text: String, before targetID: String?,
                             direction: AnyWritingDirection,
                             untargetedPlacement: AnyNativeBlockInsertionPolicy = .endOfRoot,
                             diagnosticRequest: UUID = UUID()) async throws -> String {
        let requestEpoch = epoch
        await flush()
        AnyNativeEditorDiagnostics.record(.flushCompleted, request: diagnosticRequest,
            ownerMatches: requestEpoch == epoch, mounted: isMounted, active: lifetime.isActive, saving: saving)
        try requireMounted(requestEpoch)
        guard !hasPendingEdits else { throw AnyHostError.changedDocument }
        guard canWrite else { throw TorahAssociationRepositoryError.permissionDenied }
        let mutationID = try beginNativeMutation(owner: requestEpoch)
        var completed = false
        defer { finishNativeMutation(mutationID, owner: requestEpoch, completed: completed) }
        AnyNativeEditorDiagnostics.record(.mutationReserved, request: diagnosticRequest,
            ownerMatches: true, mounted: isMounted, active: lifetime.isActive, saving: saving)
        let documents = documents, objectID = objectID, blocks = blocks
        let authorize = mutationAuthorization(requestEpoch), readOperation = editorReadOperation
        let result = try await nativeSession.perform { lease in
            let current = try await documents.read(objectID: objectID, lease: lease)
            await AnyNativeEditorDiagnostics.record(.prewriteReadCompleted, request: diagnosticRequest)
            let placement = try AnyNativeBlockInsertionPosition.resolve(snapshot: current.snapshot,
                policy: targetID.map(AnyNativeBlockInsertionPolicy.beforeBlock) ?? untargetedPlacement)
            let intent = try AnyNativeBlockCreationIntent(workspace: lease.workspace,
                mutationID: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                objectID: objectID, type: type, text: text,
                style: .object(["pinkhaWritingDirection": .string(direction.rawValue),
                                "pinkhaTextAlignment": .string("natural")]),
                parentID: placement.parentID, position: placement.position)
            let id = try await blocks.ensureBlock(intent) {
                try await lease.validate(); try await authorize()
            }
            await AnyNativeEditorDiagnostics.record(.nativeCreationVerified, request: diagnosticRequest)
            let readback = try await readOperation(.mutationReadback, documents, objectID, lease)
            guard readback.snapshot.depthFirstIDs.contains(id) else { throw AnyHostError.writeUncertain }
            await AnyNativeEditorDiagnostics.record(.mutationReadbackVerified, request: diagnosticRequest)
            return (id, readback)
        }
        try requireMounted(requestEpoch)
        guard ownsNativeMutation(mutationID, owner: requestEpoch) else { throw AnyHostError.sessionClosed }
        acceptAcknowledged(result.1, blockID: nil, undo: nil)
        AnyNativeEditorDiagnostics.record(.readbackPublished, request: diagnosticRequest,
            ownerMatches: requestEpoch == epoch, mounted: isMounted, active: lifetime.isActive, saving: saving)
        completed = true
        return result.0
    }

    public func showDocuments(with item: TorahAssociationItem) async {
        let requestEpoch = epoch
        do {
            try requireMounted(requestEpoch)
            guard showsProperties, !isNavigating, torah.selection == nil,
                  !torah.isSearchPresented, sourceDocumentsTitle == nil else { return }
            let index = index, metadata = metadata
            let output = try await nativeSession.perform { lease in
                let initial = try await index.documents(with: item)
                var rows: [TorahRelatedDocument] = []
                for id in initial.objectIDs {
                    let value = try await metadata.metadata(objectID: id)
                    rows.append(.init(id: id, spaceID: lease.workspace.spaceID, objectID: id,
                        title: value.title, sourceReference: item.canonicalKey,
                        kind: value.isNote ? .note : .document, typeID: value.typeID, canUnlink: false))
                }
                let final = try await index.documents(with: item)
                guard initial.readiness == final.readiness, initial.objectIDs == final.objectIDs else {
                    throw AnyHostError.changedDocument
                }
                try await lease.validate()
                return (rows, final.readiness.complete)
            }
            try requireMounted(requestEpoch)
            guard showsProperties, !isNavigating, torah.selection == nil,
                  !torah.isSearchPresented, sourceDocumentsTitle == nil else { return }
            sourceDocuments = output.0
            sourceDocumentsTitle = TorahAssociationDisplayFormatter.label(for: item, locale: .autoupdatingCurrent)
            if !output.1 { message = AnyUIErrorText.incompleteIndex }
        } catch { message = AnyUIErrorText.describe(error) }
    }

    func refreshEditor(expectedEpoch: UUID) async {
        guard expectedEpoch == epoch, lifetime.isActive else { return }
        guard !saving else { refreshAfterMutation = true; return }
        let requestID = UUID()
        editorReadID = requestID
        do {
            let documents = documents, objectID = objectID, readOperation = editorReadOperation
            let value = try await nativeSession.perform {
                try await readOperation(.observation, documents, objectID, $0)
            }
            guard mayPublishRead(requestID, owner: expectedEpoch) else { return }
            accept(value)
        } catch {
            guard mayPublishRead(requestID, owner: expectedEpoch) else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    private func refreshNativeProperties(expectedEpoch: UUID, editorRequestID: UUID? = nil) async throws {
        guard expectedEpoch == epoch, lifetime.isActive else { return }
        if let editorRequestID, !mayPublishRead(editorRequestID, owner: expectedEpoch) { return }
        let requestID = UUID()
        nativePropertiesReadID = requestID
        do {
            let index = index, objectID = objectID
            let value = try await nativeSession.perform { lease in
                let result = try await index.documentProperties(objectID: objectID)
                try await lease.validate(); return result
            }
            guard expectedEpoch == epoch, lifetime.isActive, nativePropertiesReadID == requestID else { return }
            if let editorRequestID, !mayPublishRead(editorRequestID, owner: expectedEpoch) { return }
            nativeProperties = value
        } catch {
            guard expectedEpoch == epoch, lifetime.isActive, nativePropertiesReadID == requestID else { return }
            if let editorRequestID, !mayPublishRead(editorRequestID, owner: expectedEpoch) { return }
            throw error
        }
    }

    private func startObservation() {
        guard streamSession == nil, lifetime.isActive else { return }
        let stream = AnyStreamSession(generation: nativeSession.generation)
        streamSession = stream
        let requestEpoch = epoch
        streamTasks.append(Task { [weak self] in
            guard let self else { return }
            do {
                let query: AnyJSON = .object([
                    "objectId": .string(objectID), "dataset": .string(documents.dataset),
                    // A bounded live window requires a stable native order.
                    // The editor still renders the snapshot's hierarchy order.
                    "sort": .array([.string("id")]),
                    "limit": .integer(10_001), "includeTotal": .bool(true)])
                let updates = try await client.subscribeQuery(spaceID: workspace.spaceID,
                    query: query, streamSession: stream, maximumRecords: 10_000, requireComplete: true)
                for try await _ in updates {
                    guard epoch == requestEpoch, lifetime.isActive else { return }
                    await refreshEditor(expectedEpoch: requestEpoch)
                }
            } catch {
                guard epoch == requestEpoch, lifetime.isActive, !Task.isCancelled else { return }
                message = AnyUIErrorText.describe(error)
            }
        })
        streamTasks.append(Task { [weak self] in
            guard let self else { return }
            do {
                let updates = try await operations.watchObject(objectID: objectID, session: stream, limit: capabilities.maximumClaimRecords)
                for try await update in updates {
                    try await stream.requireActive(generation: update.generation)
                    guard epoch == requestEpoch, lifetime.isActive else { return }
                    await torah.refreshAssociationSnapshot()
                    try await refreshNativeProperties(expectedEpoch: requestEpoch)
                }
            } catch {
                guard epoch == requestEpoch, lifetime.isActive, !Task.isCancelled else { return }
                message = AnyUIErrorText.describe(error)
            }
        })
    }

    public func retryObservation() async {
        await stopObservation()
        await load()
    }

    private func stopObservation() async {
        let stream = streamSession; streamSession = nil
        let tasks = streamTasks; streamTasks = []
        for task in tasks { task.cancel() }
        await stream?.invalidate()
        for task in tasks { await task.value }
    }

    func mutationAuthorization(_ expected: UUID) -> @Sendable () async throws -> Void {
        { [weak self] in
            guard let self else { throw AnyHostError.sessionClosed }
            try await self.requireMounted(expected)
        }
    }

    func requireMounted(_ expected: UUID) throws {
        try lifetime.requireActive()
        guard isMounted, epoch == expected, surface?.isForegroundMounted == true else {
            throw AnyHostError.sessionClosed
        }
    }

    func installSourceInvalidator(_ invalidate: @escaping @Sendable () -> Void) throws {
        try requireMounted(epoch)
        scopeInvalidators.append(invalidate)
    }

    func installPresentationLifecycle(revoke: @escaping @MainActor () -> Void,
                                      drain: @escaping @MainActor () async -> Void) {
        revokeHandlers.append(revoke); drainHandlers.append(drain)
    }

    private func invalidateSourceScope() {
        let callbacks = scopeInvalidators; scopeInvalidators.removeAll()
        for callback in callbacks { callback() }
    }

    public func unmount() {
        navigation.cancel()
        surface?.captureActiveCompositionForRecovery()
        retainRecovery()
        guard isMounted else { return }
        isMounted = false; epoch = UUID()
        semanticAnchorIntent = nil; semanticAnchorPreparationID = nil
        semanticAnchorMutationID = nil; isCreatingTextAnchor = false
        retireEditorReads()
        nativeMutationID = nil; inFlightTextBlockID = nil; saving = false
        loadAfterMutation = false; refreshAfterMutation = false; saveAfterMutation = false
        deferredReadTask?.cancel()
        if let task = deferredReadTask { closingObservers.append(task) }
        deferredReadTask = nil
        torah.deactivateDocument()
        invalidateSourceScope()
        for callback in revokeHandlers { callback() }
        saveTask?.cancel()
        let oldStream = streamSession; streamSession = nil
        let oldTasks = streamTasks; streamTasks = []
        for task in oldTasks { task.cancel() }
        closingObservers.append(Task {
            await oldStream?.invalidate()
            for task in oldTasks { await task.value }
        })
        surface = nil
    }

    public func revoke() {
        unmount()
        canWrite = false
        for callback in revokeHandlers { callback() }
    }

    public func drain() async {
        revoke()
        let save = saveTask; saveTask = nil
        await save?.value
        await stopObservation()
        let closing = closingObservers; closingObservers = []
        for task in closing { await task.value }
        let handlers = drainHandlers; drainHandlers = []
        for handler in handlers { await handler() }
        revokeHandlers = []
    }
}

public enum AnyUIErrorText {
    public static var unmappedComposition: String {
        text("הטקסט שהוקלד נשמר להעתקה ולבדיקה. אי אפשר לשלב אותו בעיצוב הקיים ללא שינוי העיצוב.",
             "Your typed text is retained for copying and review. It cannot be merged into the existing formatting losslessly.")
    }
    public static var recoveredDrafts: String {
        text("נשמרו שינויים מקומיים מההפעלה הקודמת. יש לבדוק אותם מול הגרסה הנוכחית לפני המשך שמירה.",
             "Local edits were recovered from the previous session. Review them against the current version before saving.")
    }
    public static var changedDocument: String {
        text("המסמך השתנה. השינויים המקומיים נשמרו לעריכה; טען את הגרסה הנוכחית לפני ניסיון נוסף.",
             "The document changed. Your local edits are retained; review the current version before retrying.")
    }
    public static var uncertainWrite: String {
        text("הפעולה נשלחה אך לא התקבל אישור מלא. בדוק את התוצאה לפני ניסיון נוסף.",
             "The operation was sent but its result could not be fully confirmed. Review the result before retrying.")
    }
    public static var incompleteIndex: String {
        text("יש נתוני מקור שעדיין אינם ניתנים לפענוח או שנמצאים בהתנגשות. הרשימה אינה מלאה.",
             "Some source data is unsupported or conflicted. This list is incomplete.")
    }
    public static func describe(_ error: any Error) -> String {
        switch error {
        case AnyHostError.changedDocument: return changedDocument
        case AnyHostError.writeUncertain, AnyEngineError.writeUncertain: return uncertainWrite
        case AnyHostError.sessionClosed, AnyHostError.engineRestarted, AnyEngineError.accountChanged:
            return text("המסמך אינו פעיל עוד. פתח אותו מחדש כדי להמשיך.", "This document session is no longer active. Reopen it to continue.")
        case TorahAssociationRepositoryError.permissionDenied:
            return text("אין הרשאת עריכה למסמך זה.", "You do not have permission to edit this document.")
        default: return error.localizedDescription
        }
    }
    public static func text(_ hebrew: String, _ english: String) -> String {
        Locale.autoupdatingCurrent.language.languageCode?.identifier == "he" ? hebrew : english
    }
}
#endif
