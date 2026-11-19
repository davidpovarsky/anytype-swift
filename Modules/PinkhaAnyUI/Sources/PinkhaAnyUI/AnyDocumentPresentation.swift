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

/// One mounted native document. All native work has an account/run lease; each
/// mutation additionally rechecks this UI epoch at the actual dispatch seam.
@MainActor @Observable
public final class AnyDocumentPresentation {
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
    public var sourceDocuments: [TorahRelatedDocument] = []
    public var sourceDocumentsTitle: String?
    public private(set) var nativeProperties: AnyNativeDerivedDocumentProperties?
    public var onOpenObject: ((String, String?) -> Void)?
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
    @ObservationIgnored private var streamSession: AnyStreamSession?
    @ObservationIgnored private var streamTasks: [Task<Void, Never>] = []
    @ObservationIgnored private var saveTask: Task<Void, Never>?
    @ObservationIgnored private var saving = false
    @ObservationIgnored private var drafts: [String: AnyBlockDraft] = [:]
    @ObservationIgnored private var lastUndo: AnyPreparedBlockEdit?
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
        torah.installOpenObjectHandler { [weak self] id, blockID in self?.onOpenObject?(id, blockID) }
        torah.installAssociationSnapshotHandler { [weak self] _ in self?.contentRevision &+= 1 }
        registration = try lifetime.register(revoke: { [weak self] in self?.revoke() },
                                              drain: { [weak self] in await self?.drain() })
    }

    var mountedOwnerID: UUID { epoch }
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
    public var canMutate: Bool { isMounted && lifetime.isActive && canWrite && !requiresDraftReview && surface?.isForegroundMounted == true }
    public var hasPendingEdits: Bool { !drafts.isEmpty || saving }
    public var orderedBlocks: [AnyEditorBlock] {
        guard let snapshot = read?.snapshot else { return [] }
        let byID = Dictionary(uniqueKeysWithValues: snapshot.blocks.map { ($0.id, $0) })
        return snapshot.depthFirstIDs.compactMap { byID[$0] }
    }

    public func source(for block: AnyEditorBlock) -> String { drafts[block.id]?.inlineMarkdown ?? block.text }
    public func projection(for block: AnyEditorBlock) -> AnyInlineMarkdown {
        block.type == "code" ? .init(literal: source(for: block)) : .init(source(for: block))
    }

    public func mount(surface: any AnyEditorMountedSurface) {
        guard lifetime.isActive else { return }
        if !isMounted { epoch = UUID() }
        self.surface = surface; isMounted = true
        torah.activateDocument()
    }

    public func load() async {
        guard lifetime.isActive, !isLoading else { return }
        isLoading = true
        defer { isLoading = false }
        let requestEpoch = epoch
        do {
            let documents = documents, objectID = objectID, client = client
            let result = try await nativeSession.perform { lease in
                let value = try await documents.read(objectID: objectID, lease: lease)
                let member = try await client.requestJSON(method: "GET",
                    path: ["v1", "spaces", lease.workspace.spaceID, "members", "me"])
                try AnyHTTPTorahTargetAccess.validateMember(member, workspace: lease.workspace, intent: .read)
                let writable = ["owner", "admin", "writer"].contains(member["permission"]?.string ?? "")
                try await lease.validate()
                return (value, writable)
            }
            guard lifetime.isActive, requestEpoch == epoch else { return }
            accept(result.0); canWrite = result.1
            await torah.refreshAssociationSnapshot()
            try await refreshNativeProperties(expectedEpoch: requestEpoch)
            if streamSession == nil { startObservation() }
        } catch {
            guard requestEpoch == epoch, lifetime.isActive else { return }
            message = AnyUIErrorText.describe(error)
        }
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

    public func changeText(blockID: String, source: String, displaySelection: NSRange) throws {
        try requireMounted(epoch)
        guard canWrite, !requiresDraftReview, source.utf8.count <= 65_536,
              let block = read?.snapshot.blocks.first(where: { $0.id == blockID }),
              read?.snapshot.depthFirstIDs.contains(blockID) == true,
              (block.type == "code" || AnyInlineMarkdown(source).isEditable) else { throw AnyHostError.invalidSelection }
        var draft = drafts[blockID] ?? .init(base: block, inlineMarkdown: block.text,
                                             selection: displaySelection, revision: 0)
        draft.inlineMarkdown = source; draft.selection = displaySelection; draft.revision &+= 1
        var candidate = drafts
        if source == draft.base.text { candidate.removeValue(forKey: blockID) }
        else { candidate[blockID] = draft }
        // Retain the exact source/base before accepting the visible edit.
        try captureRecovery(candidate)
        drafts = candidate
        select(blockIDs: selectedBlockIDs.contains(blockID) ? selectedBlockIDs : [blockID],
               focusedBlockID: blockID, range: displaySelection)
        writeState = drafts.isEmpty ? .clean : .pending
        contentRevision &+= 1
        saveTask?.cancel()
        saveTask = Task { [weak self] in
            do { try await Task.sleep(for: .milliseconds(450)) } catch { return }
            await self?.flush()
        }
    }

    public func flush() async {
        guard !saving, !drafts.isEmpty, canMutate else { return }
        saving = true; writeState = .saving
        defer { saving = false; retainRecovery() }
        let requestEpoch = epoch
        while let (id, draft) = drafts.sorted(by: { $0.key < $1.key }).first {
            do {
                try requireMounted(requestEpoch)
                let documents = documents, objectID = objectID
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
                    let readback = try await documents.read(objectID: objectID, lease: lease)
                    guard let saved = readback.snapshot.blocks.first(where: { $0.id == id }),
                          saved.text == draft.inlineMarkdown else { throw AnyHostError.writeUncertain }
                    return (receipt, readback, saved)
                }
                try requireMounted(requestEpoch)
                if var latest = drafts[id] {
                    if latest.revision == draft.revision { drafts.removeValue(forKey: id) }
                    else { latest.base = result.2; drafts[id] = latest }
                }
                lastUndo = result.0.undo
                acknowledgedBlockVersions[id] = result.2.native["_ver"]
                accept(result.1)
                writeState = drafts.isEmpty ? .saved : .saving
            } catch {
                guard requestEpoch == epoch, lifetime.isActive else { return }
                switch error {
                case AnyHostError.changedDocument: writeState = .conflict(AnyUIErrorText.changedDocument)
                case AnyHostError.writeUncertain, AnyEngineError.writeUncertain:
                    writeState = .uncertain(AnyUIErrorText.uncertainWrite)
                default: writeState = .failed(AnyUIErrorText.describe(error))
                }
                return
            }
        }
    }

    public func discardLocalDrafts() {
        saveTask?.cancel(); drafts.removeAll(); lastUndo = nil
        requiresDraftReview = false
        retainRecovery()
        writeState = .clean; contentRevision &+= 1
    }

    public var localDraftTextForCopy: String {
        let visible = orderedBlocks.map { source(for: $0) }
        let visibleIDs = Set(orderedBlocks.map(\.id))
        let detached = drafts.filter { !visibleIDs.contains($0.key) }
            .sorted { $0.key < $1.key }.map { $0.value.inlineMarkdown }
        return (visible + detached).joined(separator: "\n\n")
    }

    public var recoveredDrafts: [AnyNativeRecoveredBlockDraft] {
        drafts.sorted { $0.key < $1.key }.compactMap { _, value in
            try? .init(base: value.base, inlineMarkdown: value.inlineMarkdown,
                       selection: value.selection, revision: value.revision)
        }
    }

    public func resumeRecoveredDrafts() async {
        guard requiresDraftReview else { return }
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

    private func captureRecovery(_ values: [String: AnyBlockDraft]? = nil) throws {
        guard recoveryWasRestored else { return }
        let values = values ?? drafts
        let records = try values.values.map {
            try AnyNativeRecoveredBlockDraft(base: $0.base, inlineMarkdown: $0.inlineMarkdown,
                                              selection: $0.selection, revision: $0.revision)
        }
        try recovery.save(.init(workspace: workspace, objectID: objectID, drafts: records,
            selectedBlockIDs: selectedBlockIDs, focusedBlockID: focusedBlockID, selection: selectedTextRange))
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
            selectedBlockIDs = saved.selectedBlockIDs.filter { reachable.contains($0) }
            focusedBlockID = saved.focusedBlockID.flatMap { reachable.contains($0) ? $0 : nil }
            selectedTextRange = saved.selection
            if let id = focusedBlockID, let current = byID[id],
               NSMaxRange(selectedTextRange) > projection(for: current).display.utf16.count {
                selectedTextRange = .init(location: 0, length: 0)
            }
            requiresDraftReview = !drafts.isEmpty
            writeState = requiresDraftReview ? .conflict(AnyUIErrorText.recoveredDrafts) : .clean
            retainRecovery()
        } catch { message = AnyUIErrorText.describe(error); canWrite = false; requiresDraftReview = true }
    }

    public func undoLastNativeEdit() async {
        guard !hasPendingEdits, let undo = lastUndo else { return }
        let requestEpoch = epoch
        do {
            let documents = documents, authorize = mutationAuthorization(requestEpoch)
            let receipt = try await nativeSession.perform { lease in
                try await documents.apply(undo, lease: lease, authorize: authorize)
            }
            try requireMounted(requestEpoch)
            guard receipt.readback == .verifiedCurrent else { throw AnyHostError.writeUncertain }
            lastUndo = receipt.undo
            await refreshEditor(expectedEpoch: requestEpoch)
        } catch { message = AnyUIErrorText.describe(error) }
    }

    public func setWritingStyle(direction: AnyWritingDirection, alignment: AnyTextAlignment) async {
        await flush()
        guard !hasPendingEdits, !selectedBlockIDs.isEmpty else { return }
        let requestEpoch = epoch
        do {
            for id in selectedBlockIDs {
                let documents = documents, objectID = objectID, authorize = mutationAuthorization(requestEpoch)
                _ = try await nativeSession.perform { lease in
                    let current = try await documents.read(objectID: objectID, lease: lease)
                    let edit = try documents.prepareWritingStyle(current, blockID: id,
                                                                   direction: direction, alignment: alignment)
                    let receipt = try await documents.apply(edit, lease: lease, authorize: authorize)
                    guard receipt.readback == .verifiedCurrent else { throw AnyHostError.writeUncertain }
                    return receipt
                }
                try requireMounted(requestEpoch)
            }
            await refreshEditor(expectedEpoch: requestEpoch)
        } catch { message = AnyUIErrorText.describe(error) }
    }

    public func addParagraph(before targetID: String? = nil) async {
        do {
            let id = try await createBlock(type: "paragraph", text: "", before: targetID,
                                           direction: .natural)
            focusedBlockID = id; selectedBlockIDs = [id]; selectedTextRange = .init(location: 0, length: 0)
            surface?.reveal(blockID: id, selection: selectedTextRange)
        } catch { message = AnyUIErrorText.describe(error) }
    }

    private func insertQuote(_ transfer: TorahSourceTransfer, before targetID: String?) async throws -> String {
        let direction: AnyWritingDirection = transfer.direction == "rtl" ? .rightToLeft :
            (transfer.direction == "ltr" ? .leftToRight : .natural)
        // Markdown escaping changes storage syntax only. The visible editable
        // quote remains precisely the provider's text; citation is metadata.
        let text = AnyInlineMarkdown.escapeLiteral(transfer.text)
        return try await createBlock(type: "quote", text: text, before: targetID, direction: direction)
    }

    private func createBlock(type: String, text: String, before targetID: String?,
                             direction: AnyWritingDirection) async throws -> String {
        await flush()
        guard !hasPendingEdits else { throw AnyHostError.changedDocument }
        let requestEpoch = epoch
        try requireMounted(requestEpoch)
        guard canWrite else { throw TorahAssociationRepositoryError.permissionDenied }
        let documents = documents, objectID = objectID, blocks = blocks
        let authorize = mutationAuthorization(requestEpoch)
        let id = try await nativeSession.perform { lease in
            let current = try await documents.read(objectID: objectID, lease: lease)
            let byID = Dictionary(uniqueKeysWithValues: current.snapshot.blocks.map { ($0.id, $0) })
            let parentID: String
            let previous: String?
            let next: String?
            if let targetID {
                guard current.snapshot.depthFirstIDs.contains(targetID), let target = byID[targetID] else {
                    throw AnyHostError.invalidSelection
                }
                parentID = target.parentID
                let siblings = current.snapshot.blocks.filter { $0.parentID == parentID }
                    .sorted { $0.position == $1.position ? $0.id < $1.id : $0.position < $1.position }
                guard let offset = siblings.firstIndex(where: { $0.id == targetID }) else {
                    throw AnyHostError.invalidSelection
                }
                previous = offset > 0 ? siblings[offset - 1].position : nil
                next = target.position
            } else {
                parentID = ""
                previous = current.snapshot.blocks.filter { $0.parentID.isEmpty }.map(\.position).max()
                next = nil
            }
            let position = try AnyLexicographicPosition.between(after: previous, before: next)
            let intent = try AnyNativeBlockCreationIntent(workspace: lease.workspace,
                mutationID: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                objectID: objectID, type: type, text: text,
                style: .object(["pinkhaWritingDirection": .string(direction.rawValue),
                                "pinkhaTextAlignment": .string("natural")]),
                parentID: parentID, position: position)
            return try await blocks.ensureBlock(intent) {
                try await lease.validate(); try await authorize()
            }
        }
        try requireMounted(requestEpoch)
        await refreshEditor(expectedEpoch: requestEpoch)
        return id
    }

    public func showDocuments(with item: TorahAssociationItem) async {
        let requestEpoch = epoch
        do {
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
            sourceDocuments = output.0
            sourceDocumentsTitle = TorahAssociationDisplayFormatter.label(for: item, locale: .autoupdatingCurrent)
            if !output.1 { message = AnyUIErrorText.incompleteIndex }
        } catch { message = AnyUIErrorText.describe(error) }
    }

    private func refreshEditor(expectedEpoch: UUID) async {
        do {
            let documents = documents, objectID = objectID
            let value = try await nativeSession.perform { try await documents.read(objectID: objectID, lease: $0) }
            guard expectedEpoch == epoch, lifetime.isActive else { return }
            accept(value)
        } catch {
            guard expectedEpoch == epoch, lifetime.isActive else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    private func refreshNativeProperties(expectedEpoch: UUID) async throws {
        let index = index, objectID = objectID
        let value = try await nativeSession.perform { lease in
            let result = try await index.documentProperties(objectID: objectID)
            try await lease.validate(); return result
        }
        guard expectedEpoch == epoch, lifetime.isActive else { return }
        nativeProperties = value
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
        retainRecovery()
        guard isMounted else { return }
        isMounted = false; epoch = UUID()
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
