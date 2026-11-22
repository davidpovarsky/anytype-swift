
import Foundation
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaTorahPresentation
import TorahInspectorCore

/// One complete canonical projection feeds every target in a document. The
/// application session fences both dispatch and delivery; Heart IDs never enter.
public struct AnySessionTorahAssociationRepository: TorahAssociationSnapshotRepository, Sendable {
    public let workspace: AnyTorahWorkspace
    private let session: AnyApplicationSession
    private let repository: AnyTorahAssociationRepository
    private let operations: any AnyTorahOperationStore

    public init(session: AnyApplicationSession, repository: AnyTorahAssociationRepository,
                operations: any AnyTorahOperationStore) throws {
        guard session.workspace == repository.workspace, operations.workspace == session.workspace else {
            throw AnyHostError.wrongWorkspace
        }
        workspace = session.workspace
        self.session = session; self.repository = repository; self.operations = operations
    }

    public func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord] {
        try check(spaceId)
        let repository = repository, operations = operations
        if operations is any AnyTorahObjectOperationReading {
            return try await session.perform { lease in
                let snapshot = try await repository.objectSnapshot(objectID: objectId, spaceID: spaceId)
                guard snapshot.conflicts.isEmpty else {
                    throw TorahAssociationRepositoryError.writeConflict("Canonical source identities conflict")
                }
                try await lease.validate(); return snapshot.records
            }
        }
        return try await session.perform { lease in
            let projection = try await operations.snapshot()
            try await lease.validate()
            guard projection.all.allSatisfy({ $0.operation.spaceID == spaceId }) else {
                throw TorahAssociationRepositoryError.targetOutsideSpace
            }
            var targets: Set<TorahAssociationTarget> = [.object(objectId: objectId)]
            for claim in projection.all where claim.operation.targetObjectID == objectId {
                let blockID = claim.operation.targetBlockID
                targets.insert(blockID.isEmpty ? .object(objectId: objectId) :
                    .block(objectId: objectId, blockId: blockID))
            }
            var records: [TorahStoredAssociationRecord] = []
            for target in targets.sorted(by: { ($0.blockId ?? "") < ($1.blockId ?? "") }) {
                try await lease.validate()
                do {
                    let snapshot = try await repository.snapshot(projection: projection, target: target, spaceID: spaceId)
                    guard snapshot.conflicts.isEmpty else {
                        throw TorahAssociationRepositoryError.writeConflict("Canonical source identities conflict")
                    }
                    records.append(contentsOf: snapshot.records)
                } catch TorahAssociationRepositoryError.targetNotFound where target.blockId != nil {
                    // Historical claims for a removed block cannot become live UI links.
                    continue
                }
            }
            try await lease.validate()
            return records
        }
    }

    public func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        try check(spaceId)
        let repository = repository
        return try await session.perform { lease in
            let values = try await repository.listDocumentAssociations(objectId: objectId, spaceId: spaceId)
            try await lease.validate(); return values
        }
    }

    public func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        try check(spaceId)
        let repository = repository
        return try await session.perform { lease in
            let values = try await repository.listBlockAssociations(objectId: objectId, blockId: blockId, spaceId: spaceId)
            try await lease.validate(); return values
        }
    }

    public func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget,
                               spaceId: String) async throws -> TorahAssociationItem {
        try await addAssociation(item, target: target, spaceId: spaceId, authorize: {})
    }

    public func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String,
                               authorize: @escaping TorahAssociationWriteAuthorization) async throws -> TorahAssociationItem {
        try check(spaceId)
        let repository = repository
        return try await session.perform { lease in
            try await repository.apply(item, target: target, spaceId: spaceId, authorize: {
                try await lease.validate()
                try await authorize()
            })
        }
    }

    public func upsertAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget,
                                  spaceId: String) async throws -> TorahAssociationItem {
        try await addAssociation(item, target: target, spaceId: spaceId)
    }

    public func updateAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget,
                                  spaceId: String) async throws -> TorahAssociationItem {
        try check(spaceId)
        let repository = repository
        return try await session.perform { lease in
            try await repository.apply(item, target: target, spaceId: spaceId,
                                       requireExisting: true, authorize: { try await lease.validate() })
        }
    }

    public func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String) async throws {
        try check(spaceId)
        let repository = repository
        try await session.perform { lease in
            try await repository.removeAssociation(associationId: associationId, target: target,
                                                     spaceId: spaceId, authorize: { try await lease.validate() })
        }
    }

    private func check(_ spaceId: String) throws {
        guard spaceId == workspace.spaceID else { throw TorahAssociationRepositoryError.targetOutsideSpace }
    }
}

/// Uses the existing T5 state machine. A partially confirmed Note keeps its exact
/// immutable plan for an explicit retry during this mounted editor lifetime.
@MainActor
public final class AnySessionTorahNotesService: TorahEditorNotesService {
    public let workspace: AnyTorahWorkspace
    public let objectID: String
    private let session: AnyApplicationSession
    private let notes: AnyTorahNotesService
    private let related: AnyTorahRelatedDocumentsService?
    private let nativeRelated: AnyNativeTorahRelatedPresentation?
    private var pending: [String: AnyTorahNoteCreationPlan] = [:]

    public init(session: AnyApplicationSession, objectID: String, notes: AnyTorahNotesService,
                related: AnyTorahRelatedDocumentsService) throws {
        guard !objectID.isEmpty, notes.workspace == session.workspace,
              related.workspace == session.workspace else { throw AnyHostError.wrongWorkspace }
        self.workspace = session.workspace; self.objectID = objectID
        self.session = session; self.notes = notes; self.related = related; self.nativeRelated = nil
    }

    public init(session: AnyApplicationSession, objectID: String, notes: AnyTorahNotesService,
                nativeRelated: AnyNativeTorahRelatedPresentation) throws {
        guard !objectID.isEmpty, notes.workspace == session.workspace,
              nativeRelated.workspace == session.workspace else { throw AnyHostError.wrongWorkspace }
        self.workspace = session.workspace; self.objectID = objectID
        self.session = session; self.notes = notes; self.related = nil; self.nativeRelated = nativeRelated
    }

    public func notes(for selection: TorahInspectorSelection) async throws -> [TorahInspectorNote] {
        let service = notes, objectID = objectID
        return try await session.perform { lease in
            let items = try await service.noteItems(originObjectID: objectID, selectionID: selection.id)
            try await lease.validate()
            return items.map { .init(id: $0.id, selectedText: selection.relationshipRef,
                                     note: $0.labelHe, tag: "Anytype") }
        }
    }

    public func relatedDocuments(for selection: TorahInspectorSelection) async throws -> TorahRelatedDocumentsSnapshot {
        do {
            let source = T5SourceIdentity(providerID: selection.providerID, canonicalReference: selection.relationshipRef)
            if let nativeRelated {
                return try await session.perform { lease in
                    let result = try await nativeRelated.snapshot(source: source)
                    try await lease.validate(); return result
                }
            }
            guard let related else { throw AnyHostError.incompleteDocument }
            return try await session.perform { lease in
                let output = try await related.documents(source: source)
                try await lease.validate()
                var limitations: [TorahRelatedDocumentsLimitation] = [
                    .blockAssociationsNotIndexed, .sourceQuotesNotIndexed, .indexFreshnessUnverified]
                if output.documents.isTruncated { limitations.append(.resultLimitReached) }
                if output.documents.hasStaleCandidates { limitations.append(.staleCandidates) }
                return .init(documents: output.documents.matches.map { match in
                    let document = match.document
                    return TorahRelatedDocument(id: match.id, spaceID: document.spaceID,
                        objectID: document.objectID, title: document.title,
                        sourceReference: source.canonicalReference,
                        kind: document.isNote ? .note : .document, typeID: document.typeID,
                        iconEmoji: document.iconEmoji, iconImageID: document.iconImageID,
                        updatedAt: document.updatedAt, canUnlink: document.canUnlink)
                }, coverage: .indexedDocumentsOnly, limitations: limitations)
            }
        } catch {
            if let failure = AnyTorahRelatedReadFailure.classify(
                error, ownerIsActive: await session.isActive
            ) {
                throw failure
            }
            throw error
        }
    }

    public func createNote(for selection: TorahInspectorSelection,
                           authorize: @escaping TorahAssociationWriteAuthorization) async throws -> T5NoteCreationOutcome {
        try authorize()
        let plan: AnyTorahNoteCreationPlan
        if let previous = pending[selection.id] { plan = previous }
        else {
            plan = try .init(workspace: workspace, originObjectID: objectID,
                             providerID: selection.providerID, canonicalReference: selection.relationshipRef,
                             selectionID: selection.id, title: "הערה על \(selection.relationshipRef)")
            pending[selection.id] = plan
        }
        let notes = notes
        let outcome = try await session.perform { lease in
            try await notes.createNote(plan: plan) {
                try await lease.validate()
                try await authorize()
            }
        }
        if outcome.recoveryError == nil { pending.removeValue(forKey: selection.id) }
        return outcome
    }

    public func noteObjectId(noteId: String, for selection: TorahInspectorSelection) async throws -> String? {
        let notes = notes, objectID = objectID
        return try await session.perform { lease in
            let items = try await notes.noteItems(originObjectID: objectID, selectionID: selection.id)
            try await lease.validate()
            return items.first { $0.id == noteId }?.customMetadata?["anytypeNoteObjectId"]
        }
    }

    public func unlink(noteId: String, for selection: TorahInspectorSelection,
                       authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        let notes = notes, objectID = objectID
        let source = T5SourceIdentity(providerID: selection.providerID, canonicalReference: selection.relationshipRef)
        try await session.perform { lease in
            try await notes.unlinkNote(associationID: noteId, originObjectID: objectID,
                                       selectionID: selection.id, source: source) {
                try await lease.validate(); try await authorize()
            }
        }
    }

    public func unlink(document: TorahRelatedDocument, for selection: TorahInspectorSelection,
                       authorize: @escaping TorahAssociationWriteAuthorization) async throws {
        guard document.spaceID == workspace.spaceID, document.blockID == nil,
              document.canUnlink else { throw TorahAssociationRepositoryError.permissionDenied }
        let source = T5SourceIdentity(providerID: selection.providerID, canonicalReference: selection.relationshipRef)
        if let nativeRelated {
            try await session.perform { lease in
                try await nativeRelated.unlink(document: document, source: source) {
                    try await lease.validate(); try await authorize()
                }
            }
            return
        }
        guard let related else { throw AnyHostError.incompleteDocument }
        try await session.perform { lease in
            try await related.unlinkDocument(objectID: document.objectID, source: source) {
                try await lease.validate(); try await authorize()
            }
        }
    }
}
