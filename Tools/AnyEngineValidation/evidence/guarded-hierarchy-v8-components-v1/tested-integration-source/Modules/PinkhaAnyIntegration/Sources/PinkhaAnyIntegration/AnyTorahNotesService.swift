import Foundation
import PinkhaKit
import PinkhaAnyEngine

public typealias AnyTorahNoteAuthorization = @Sendable () async throws -> Void

/// Host owns native editor details and the durable exact-create/write journal.
/// An ambiguous dispatch must remain unknown until native readback proves it;
/// neither method may recover by allocating a fresh object/block identity.
public protocol AnyTorahNoteDocumentEditing: Sendable {
    var workspace: AnyTorahWorkspace { get }
    func ensureNoteObject(plan: AnyTorahNoteCreationPlan,
                          authorize: @escaping AnyTorahNoteAuthorization) async throws -> String
    func ensureSourceLine(objectID: String, sourceLine: String, mutationID: String,
                          authorize: @escaping AnyTorahNoteAuthorization) async throws
}

public struct AnyTorahNoteCreationPlan: Codable, Sendable, Equatable {
    public let workspace: AnyTorahWorkspace
    public let planID: String
    public let originObjectID: String
    public let providerID: String
    public let canonicalReference: String
    public let selectionID: String
    public let title: String
    public let createdAt: Date

    public init(workspace: AnyTorahWorkspace,
                planID: String = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                originObjectID: String, providerID: String, canonicalReference: String,
                selectionID: String, title: String? = nil, createdAt: Date = Date()) throws {
        let source = T5SourceIdentity(providerID: providerID, canonicalReference: canonicalReference)
        let title = title ?? "הערה על \(source.canonicalReference)"
        guard planID.utf8.count == 32,
              planID.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
              [originObjectID, source.providerID, source.canonicalReference, selectionID, title]
                .allSatisfy({ !$0.isEmpty && $0.utf8.count <= 4096 && !$0.utf8.contains(0) }),
              originObjectID.utf8.count <= 1024, source.providerID.utf8.count <= 256,
              createdAt.timeIntervalSinceReferenceDate.isFinite,
              (-62_135_596_800...253_402_300_799).contains(createdAt.timeIntervalSince1970) else {
            throw AnyEngineError.invalidIdentity("note creation plan")
        }
        self.workspace = workspace
        self.planID = planID
        self.originObjectID = originObjectID
        self.providerID = source.providerID
        self.canonicalReference = source.canonicalReference
        self.selectionID = selectionID
        self.title = title
        self.createdAt = createdAt
    }

    public var source: T5SourceIdentity {
        .init(providerID: providerID, canonicalReference: canonicalReference)
    }
    public var sourceLine: String { "מקור: \(canonicalReference)" }
    public var objectIntentID: String { phaseID("note-object") }
    public var sourceLineMutationID: String { phaseID("source-line") }
    public var sourceOperationID: String { phaseID("source-association") }
    public var originOperationID: String { phaseID("origin-association") }
    public var sourceAssociationID: String { "note-source-" + sourceOperationID }
    public var originAssociationID: String { "note-origin-" + originOperationID }

    /// Bind a durable host receipt to the entire immutable intent.
    public var fingerprint: String {
        digest(["pinkha-any-note-plan-v1", workspace.accountID, workspace.spaceID,
                planID, originObjectID, providerID, canonicalReference, selectionID,
                title, String(createdAt.timeIntervalSinceReferenceDate.bitPattern)])
    }

    private func phaseID(_ phase: String) -> String {
        String(digest(["pinkha-any-note-phase-v1", workspace.accountID, workspace.spaceID,
                       planID, originObjectID, phase]).prefix(32))
    }
    private func digest(_ parts: [String]) -> String {
        AnyContentDigest.sha256(Data(parts.map { "\($0.utf8.count):\($0)" }.joined(separator: "|").utf8))
    }
    private enum CodingKeys: String, CodingKey {
        case workspace, planID, originObjectID, providerID, canonicalReference, selectionID, title, createdAt
    }
    public init(from decoder: any Decoder) throws {
        let value = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(workspace: value.decode(AnyTorahWorkspace.self, forKey: .workspace),
                      planID: value.decode(String.self, forKey: .planID),
                      originObjectID: value.decode(String.self, forKey: .originObjectID),
                      providerID: value.decode(String.self, forKey: .providerID),
                      canonicalReference: value.decode(String.self, forKey: .canonicalReference),
                      selectionID: value.decode(String.self, forKey: .selectionID),
                      title: value.decode(String.self, forKey: .title),
                      createdAt: value.decode(Date.self, forKey: .createdAt))
    }
}

/// Reuses the original T5 flow and source identity with one explicit new-engine
/// workspace. A fresh flow per execution retries every phase against the host's
/// durable idempotent editing boundary, avoiding a stale "line attempted" bit.
@MainActor
public final class AnyTorahNotesService {
    public let workspace: AnyTorahWorkspace
    private let associations: AnyTorahAssociationRepository
    private let documents: any AnyTorahNoteDocumentEditing
    private let access: any AnyTorahTargetAccess

    public init(workspace: AnyTorahWorkspace, associations: AnyTorahAssociationRepository,
                documents: any AnyTorahNoteDocumentEditing, access: any AnyTorahTargetAccess) throws {
        guard associations.workspace == workspace, documents.workspace == workspace,
              access.workspace == workspace else { throw AnyEngineError.invalidIdentity("mixed note workspace") }
        self.workspace = workspace
        self.associations = associations
        self.documents = documents
        self.access = access
    }

    public func createNote(plan: AnyTorahNoteCreationPlan,
                           authorize: @escaping AnyTorahNoteAuthorization = {}) async throws -> T5NoteCreationOutcome {
        guard plan.workspace == workspace else { throw TorahAssociationRepositoryError.targetOutsideSpace }
        try await authorize()
        try await access.validate(.object(objectId: plan.originObjectID), intent: .write)
        let flow = T5NoteCreationFlow()
        let outcome = try await flow.create(
            source: plan.source, authorize: { try Task.checkCancellation() },
            createObject: { [self] in
                try await authorize()
                try await access.validate(.object(objectId: plan.originObjectID), intent: .write)
                let id = try await documents.ensureNoteObject(plan: plan, authorize: authorize)
                guard !id.isEmpty else { throw AnyEngineError.unverifiedWrite }
                return id
            },
            linkSource: { [self] noteID in
                try await ensureSourceAssociation(plan: plan, noteID: noteID, authorize: authorize)
            },
            addSourceLine: { [self] noteID in
                try await authorize()
                try await access.validate(.object(objectId: noteID), intent: .write)
                try await documents.ensureSourceLine(
                    objectID: noteID, sourceLine: plan.sourceLine,
                    mutationID: plan.sourceLineMutationID, authorize: authorize)
            },
            linkOrigin: { [self] noteID in
                try await ensureOriginAssociation(plan: plan, noteID: noteID, authorize: authorize)
                try await authorize()
                try await verifyLinks(plan: plan, noteID: noteID)
            })
        return outcome
    }

    public func noteItems(originObjectID: String, selectionID: String) async throws -> [TorahAssociationItem] {
        let items = try await associations.listDocumentAssociations(
            objectId: originObjectID, spaceId: workspace.spaceID)
        let result = items.filter { $0.customMetadata?["torahSelectionId"] == selectionID &&
            $0.customMetadata?["anytypeNoteObjectId"]?.isEmpty == false }
        for item in result {
            guard let noteID = item.customMetadata?["anytypeNoteObjectId"],
                  item.kind == .ref, item.role == .context, item.externalID == noteID,
                  item.canonicalKey == "anytype-note:" + noteID else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
            try await access.validate(.object(objectId: noteID), intent: .read)
        }
        return result
    }

    /// Unlinks the requested source and origin association; never deletes the note.
    /// A partial failure throws and is safe to resume from the remaining live link.
    public func unlinkNote(associationID: String, originObjectID: String, selectionID: String,
                           source: T5SourceIdentity,
                           authorize: @escaping AnyTorahNoteAuthorization = {}) async throws {
        try await authorize()
        guard let link = try await noteItems(originObjectID: originObjectID, selectionID: selectionID)
            .first(where: { $0.id == associationID }),
              let noteID = link.customMetadata?["anytypeNoteObjectId"] else { return }
        try await access.validate(.object(objectId: originObjectID), intent: .write)
        try await access.validate(.object(objectId: noteID), intent: .write)
        let sourceItems = try await associations.listDocumentAssociations(
            objectId: noteID, spaceId: workspace.spaceID)
        for item in sourceItems where source.matches(item) {
            try await associations.removeAssociation(
                associationId: item.id, target: .object(objectId: noteID),
                spaceId: workspace.spaceID, authorize: authorize)
        }
        try await associations.removeAssociation(
            associationId: link.id, target: .object(objectId: originObjectID),
            spaceId: workspace.spaceID, authorize: authorize)
        try await authorize()
        let sourceAfter = try await associations.listDocumentAssociations(
            objectId: noteID, spaceId: workspace.spaceID)
        let originAfter = try await associations.listDocumentAssociations(
            objectId: originObjectID, spaceId: workspace.spaceID)
        guard !sourceAfter.contains(where: source.matches),
              !originAfter.contains(where: { $0.id == link.id }) else { throw AnyEngineError.unverifiedWrite }
    }

    private func ensureSourceAssociation(plan: AnyTorahNoteCreationPlan, noteID: String,
                                         authorize: @escaping AnyTorahNoteAuthorization) async throws {
        try await authorize()
        try await access.validate(.object(objectId: noteID), intent: .write)
        let before = try await associations.listDocumentAssociations(objectId: noteID, spaceId: workspace.spaceID)
        if before.contains(where: plan.source.matches) { return }
        var item = plan.source.item
        item.id = plan.sourceAssociationID
        item.createdAt = plan.createdAt
        _ = try await associations.apply(
            item, target: .object(objectId: noteID), spaceId: workspace.spaceID,
            operationID: plan.sourceOperationID, authorize: authorize)
        let after = try await associations.listDocumentAssociations(objectId: noteID, spaceId: workspace.spaceID)
        guard after.contains(where: plan.source.matches) else { throw AnyEngineError.unverifiedWrite }
    }

    private func ensureOriginAssociation(plan: AnyTorahNoteCreationPlan, noteID: String,
                                         authorize: @escaping AnyTorahNoteAuthorization) async throws {
        try await authorize()
        try await access.validate(.object(objectId: noteID), intent: .read)
        let before = try await associations.listDocumentAssociations(
            objectId: plan.originObjectID, spaceId: workspace.spaceID)
        if before.contains(where: { matchesOrigin($0, plan: plan, noteID: noteID) }) { return }
        guard !before.contains(where: { $0.id == plan.originAssociationID }) else {
            throw TorahAssociationRepositoryError.writeConflict("Note origin identity changed")
        }
        let item = TorahAssociationItem(
            id: plan.originAssociationID, kind: .ref, role: .context,
            providerID: plan.providerID, externalID: noteID, canonicalKey: "anytype-note:" + noteID,
            labelHe: plan.title, labelEn: "Note on " + plan.canonicalReference, createdAt: plan.createdAt,
            customMetadata: ["anytypeNoteObjectId": noteID, "torahSelectionId": plan.selectionID])
        _ = try await associations.apply(
            item, target: .object(objectId: plan.originObjectID), spaceId: workspace.spaceID,
            operationID: plan.originOperationID, authorize: authorize)
        let after = try await associations.listDocumentAssociations(
            objectId: plan.originObjectID, spaceId: workspace.spaceID)
        guard after.contains(where: { matchesOrigin($0, plan: plan, noteID: noteID) }) else {
            throw AnyEngineError.unverifiedWrite
        }
    }

    private func verifyLinks(plan: AnyTorahNoteCreationPlan, noteID: String) async throws {
        try await access.validate(.object(objectId: noteID), intent: .read)
        let source = try await associations.listDocumentAssociations(objectId: noteID, spaceId: workspace.spaceID)
        let origin = try await associations.listDocumentAssociations(
            objectId: plan.originObjectID, spaceId: workspace.spaceID)
        guard source.contains(where: plan.source.matches),
              origin.contains(where: { matchesOrigin($0, plan: plan, noteID: noteID) }) else {
            throw AnyEngineError.unverifiedWrite
        }
    }

    private func matchesOrigin(_ item: TorahAssociationItem, plan: AnyTorahNoteCreationPlan, noteID: String) -> Bool {
        item.kind == .ref && item.role == .context && item.providerID == plan.providerID &&
        item.externalID == noteID && item.canonicalKey == "anytype-note:" + noteID &&
        item.customMetadata?["anytypeNoteObjectId"] == noteID &&
        item.customMetadata?["torahSelectionId"] == plan.selectionID
    }
}
