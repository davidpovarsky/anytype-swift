
import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// The explicit native Note classification is a collection declaration, never
/// inferred from ordinary page type. Creating the declaration is a separate
/// authorized bootstrap operation owned by the application composition.
public struct AnyNativeNoteMarker: Sendable, Equatable {
    public let workspace: AnyTorahWorkspace
    public let collectionID: String
    public static let xKey = "pinkha-note-v1"

    private init(workspace: AnyTorahWorkspace, collectionID: String) {
        self.workspace = workspace; self.collectionID = collectionID
    }

    public static func verify(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                              collectionID: String) async throws -> Self {
        guard client.expectedAccountID == workspace.accountID,
              AnyEditorBlock.validID(collectionID) else { throw AnyHostError.wrongWorkspace }
        let definition = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", workspace.spaceID, "collections", collectionID])
        guard definition["id"]?.string == collectionID,
              definition["xKey"]?.string == xKey else { throw AnyNativeCreationError.invalidIntent }
        return .init(workspace: workspace, collectionID: collectionID)
    }
}

/// Concrete native implementations of both original domain workflow seams.
/// All object and block effects share the host's protected creation journal.
public struct AnyNativeWorkflowBindings: AnyHierarchyObjectCreating, AnyTorahNoteDocumentEditing, Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient
    private let session: AnyApplicationSession
    private let objects: AnyNativeObjectCreator
    private let blocks: AnyNativeBlockCreator
    private let noteTypeID: String
    private let noteMarker: AnyNativeNoteMarker

    public init(client: AnyHTTPClient, session: AnyApplicationSession,
                objects: AnyNativeObjectCreator, blocks: AnyNativeBlockCreator,
                noteTypeID: String = "page", noteMarker: AnyNativeNoteMarker) throws {
        guard client.expectedAccountID == session.workspace.accountID,
              objects.workspace == session.workspace, blocks.workspace == session.workspace,
              noteMarker.workspace == session.workspace,
              AnyEditorBlock.validID(noteTypeID) else { throw AnyHostError.wrongWorkspace }
        self.workspace = session.workspace; self.client = client; self.session = session
        self.objects = objects; self.blocks = blocks
        self.noteTypeID = noteTypeID; self.noteMarker = noteMarker
    }

    public func ensureHierarchyObject(plan: AnyHierarchyCreationPlan,
        authorize: @escaping @Sendable () async throws -> Void) async throws -> String {
        guard plan.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        let intent = try AnyNativeObjectCreationIntent(workspace: workspace, mutationID: plan.mutationID,
            typeID: plan.typeID, collections: plan.collections, initialProperties: plan.initialProperties)
        let objects = objects
        return try await session.perform { lease in
            try await objects.ensureObject(intent) {
                try await lease.validate(); try await authorize()
            }
        }
    }

    public func ensureNoteObject(plan: AnyTorahNoteCreationPlan,
        authorize: @escaping AnyTorahNoteAuthorization) async throws -> String {
        guard plan.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        let objects = objects, client = client, noteMarker = noteMarker
        let intent = try AnyNativeObjectCreationIntent(
            workspace: workspace, mutationID: plan.objectIntentID, typeID: noteTypeID,
            collections: [noteMarker.collectionID],
            initialProperties: .object(["any": .object(["name": .string(plan.title)])]))
        return try await session.perform { lease in
            _ = try await AnyNativeNoteMarker.verify(client: client, workspace: lease.workspace,
                                                     collectionID: noteMarker.collectionID)
            return try await objects.ensureObject(intent) {
                try await lease.validate(); try await authorize()
            }
        }
    }

    public func ensureSourceLine(objectID: String, sourceLine: String, mutationID: String,
        authorize: @escaping AnyTorahNoteAuthorization) async throws {
        // A Note's initial source line has a stable intent independent of later
        // user content. Retrying it must not recompute a position/fingerprint.
        let intent = try AnyNativeBlockCreationIntent(workspace: workspace, mutationID: mutationID,
            objectID: objectID, type: "paragraph", text: sourceLine,
            style: .object(["pinkhaWritingDirection": .string("rightToLeft"),
                            "pinkhaTextAlignment": .string("natural")]),
            position: AnyLexicographicPosition.middle)
        let blocks = blocks
        _ = try await session.perform { lease in
            try await blocks.ensureBlock(intent) {
                try await lease.validate(); try await authorize()
            }
        }
    }
}
