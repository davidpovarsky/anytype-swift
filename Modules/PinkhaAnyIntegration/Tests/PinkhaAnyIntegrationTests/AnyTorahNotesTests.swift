import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

private actor NoteOperationStore: AnyTorahOperationStore {
    nonisolated let workspace: AnyTorahWorkspace
    private var claims: [AnyTorahClaim] = []
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func snapshot() throws -> AnyTorahProjection { try .init(claims: claims) }
    func append(_ operation: AnyTorahOperation,
                authorize: @escaping @Sendable () async throws -> Void) async throws {
        try await authorize()
        if claims.contains(where: { $0.id == operation.claimID }) { return }
        guard !claims.contains(where: { $0.operation.logicalKey == operation.logicalKey }) else {
            throw AnyEngineError.collision(operation.logicalKey)
        }
        claims.append(try .init(operation: operation, creator: workspace.accountID))
    }
    func count() -> Int { claims.count }
}

private actor NoteAccess: AnyTorahTargetAccess {
    nonisolated let workspace: AnyTorahWorkspace
    private var allowed = true
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func revoke() { allowed = false }
    func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) throws {
        guard allowed else { throw TorahAssociationRepositoryError.permissionDenied }
        guard ["origin", "note"].contains(target.objectId) else { throw TorahAssociationRepositoryError.targetNotFound }
    }
}

/// Explicit dependency fixture: this models the required host journal contract.
/// Native editor creation/conditional-write proof belongs to PinkhaAnyHost.
private actor NoteDocuments: AnyTorahNoteDocumentEditing {
    nonisolated let workspace: AnyTorahWorkspace
    private var fingerprint: String?
    private var creations = 0
    private var lineFailures = 0
    private var lines: [String: String] = [:]
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func failNextLine() { lineFailures += 1 }
    func counts() -> (objects: Int, lines: Int) { (creations, lines.count) }
    func ensureNoteObject(plan: AnyTorahNoteCreationPlan,
                          authorize: @escaping AnyTorahNoteAuthorization) async throws -> String {
        try await authorize()
        if let fingerprint {
            guard fingerprint == plan.fingerprint else { throw AnyEngineError.collision(plan.objectIntentID) }
        } else { fingerprint = plan.fingerprint; creations += 1 }
        return "note"
    }
    func ensureSourceLine(objectID: String, sourceLine: String, mutationID: String,
                          authorize: @escaping AnyTorahNoteAuthorization) async throws {
        try await authorize()
        guard objectID == "note" else { throw AnyEngineError.unverifiedWrite }
        if lineFailures > 0 { lineFailures -= 1; throw AnyEngineError.unverifiedWrite }
        if let existing = lines[mutationID] {
            guard existing == sourceLine else { throw AnyEngineError.collision(mutationID) }
        } else { lines[mutationID] = sourceLine }
    }
}

@Suite("Original T5 flow on explicit native note boundaries")
@MainActor
struct AnyTorahNotesTests {
    private func fixture() throws -> (AnyTorahWorkspace, NoteOperationStore, NoteAccess, NoteDocuments, AnyTorahAssociationRepository, AnyTorahNotesService) {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let store = NoteOperationStore(workspace)
        let access = NoteAccess(workspace)
        let documents = NoteDocuments(workspace)
        let repository = try AnyTorahAssociationRepository(workspace: workspace, store: store, access: access)
        let service = try AnyTorahNotesService(
            workspace: workspace, associations: repository, documents: documents, access: access)
        return (workspace, store, access, documents, repository, service)
    }
    private func plan(_ workspace: AnyTorahWorkspace) throws -> AnyTorahNoteCreationPlan {
        try .init(workspace: workspace, planID: String(repeating: "a", count: 32),
                  originObjectID: "origin", providerID: "sefaria", canonicalReference: "Genesis 1:1",
                  selectionID: "source-selection", createdAt: Date(timeIntervalSince1970: 1_700_000_000.125))
    }

    @Test func planRoundTripKeepsEntireIntentAndPhaseIdentities() throws {
        let (workspace, _, _, _, _, _) = try fixture()
        let original = try plan(workspace)
        let reopened = try JSONDecoder().decode(AnyTorahNoteCreationPlan.self, from: JSONEncoder().encode(original))
        #expect(reopened == original)
        #expect(reopened.fingerprint == original.fingerprint)
        #expect(Set([original.objectIntentID, original.sourceLineMutationID,
                     original.sourceOperationID, original.originOperationID]).count == 4)
        #expect(original.sourceLine == "מקור: Genesis 1:1")
    }

    @Test func failedSourceLineRetriesEveryPhaseWithoutDuplicatePageOrLinks() async throws {
        let (workspace, store, _, documents, repository, service) = try fixture()
        let plan = try plan(workspace)
        await documents.failNextLine()
        let partial = try await service.createNote(plan: plan)
        #expect(partial.objectID == "note")
        #expect(partial.recoveryError != nil)
        #expect(try await repository.listDocumentAssociations(objectId: "origin", spaceId: "space").isEmpty)
        let completed = try await service.createNote(plan: plan)
        #expect(completed.recoveryError == nil)
        #expect(await documents.counts().objects == 1)
        #expect(await documents.counts().lines == 1)
        #expect(await store.count() == 2)
        #expect(try await service.noteItems(originObjectID: "origin", selectionID: "source-selection").count == 1)
    }

    @Test func repeatingCompletedPlanIsIdempotent() async throws {
        let (workspace, store, _, documents, _, service) = try fixture()
        let plan = try plan(workspace)
        for _ in 0..<3 { #expect(try await service.createNote(plan: plan).recoveryError == nil) }
        #expect(await documents.counts().objects == 1)
        #expect(await documents.counts().lines == 1)
        #expect(await store.count() == 2)
    }

    @Test func existingSourceAssociationAndUserMetadataAreNotOverwritten() async throws {
        let (workspace, _, _, _, repository, service) = try fixture()
        let plan = try plan(workspace)
        var existing = plan.source.item
        existing.id = "existing-source"
        existing.labelHe = "User-edited label"
        existing.unknownFields = ["future": .string("preserved")]
        _ = try await repository.addAssociation(existing, target: .object(objectId: "note"), spaceId: "space")
        #expect(try await service.createNote(plan: plan).recoveryError == nil)
        let after = try await repository.listDocumentAssociations(objectId: "note", spaceId: "space")
        #expect(after == [existing])
    }

    @Test func retryCannotResurrectSourceLinkRemovedAfterCompletion() async throws {
        let (workspace, store, _, documents, repository, service) = try fixture()
        let plan = try plan(workspace)
        #expect(try await service.createNote(plan: plan).recoveryError == nil)
        try await repository.removeAssociation(
            associationId: plan.sourceAssociationID, target: .object(objectId: "note"), spaceId: "space")
        let retried = try await service.createNote(plan: plan)
        #expect(retried.objectID == "note")
        #expect(retried.recoveryError != nil)
        #expect(try await repository.listDocumentAssociations(objectId: "note", spaceId: "space").isEmpty)
        #expect(await documents.counts().objects == 1)
        #expect(await store.count() == 3)
    }

    @Test func unlinkKeepsTheNativeNoteAndUnrelatedSourceOrQuote() async throws {
        let (workspace, _, _, documents, repository, service) = try fixture()
        let plan = try plan(workspace)
        #expect(try await service.createNote(plan: plan).recoveryError == nil)
        var unrelated = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Exodus 2:2").item
        unrelated.id = "unrelated"
        var quote = plan.source.item
        quote.id = "quote"
        quote.role = .sourceQuote
        for item in [unrelated, quote] {
            _ = try await repository.addAssociation(item, target: .object(objectId: "note"), spaceId: "space")
        }
        try await service.unlinkNote(associationID: plan.originAssociationID,
            originObjectID: "origin", selectionID: plan.selectionID, source: plan.source)
        let remaining = try await repository.listDocumentAssociations(objectId: "note", spaceId: "space")
        #expect(Set(remaining.map(\.id)) == ["unrelated", "quote"])
        #expect(try await repository.listDocumentAssociations(objectId: "origin", spaceId: "space").isEmpty)
        #expect(await documents.counts().objects == 1)
    }

    @Test func revokedOriginPreventsAnyNoteCreation() async throws {
        let (workspace, store, access, documents, _, service) = try fixture()
        await access.revoke()
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            _ = try await service.createNote(plan: plan(workspace))
        }
        #expect(await documents.counts().objects == 0)
        #expect(await store.count() == 0)
    }

    @Test func removeRechecksCallerAuthorityAtAppend() async throws {
        let (workspace, store, _, _, repository, _) = try fixture()
        let item = try plan(workspace).source.item
        _ = try await repository.addAssociation(item, target: .object(objectId: "note"), spaceId: "space")
        actor Authorization {
            private var calls = 0
            func validate() throws {
                calls += 1
                if calls > 1 { throw TorahAssociationRepositoryError.permissionDenied }
            }
        }
        let authorization = Authorization()
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await repository.removeAssociation(
                associationId: item.id, target: .object(objectId: "note"), spaceId: "space") {
                    try await authorization.validate()
                }
        }
        #expect(await store.count() == 1)
    }
}
