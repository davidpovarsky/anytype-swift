import Foundation
import PinkhaKit
import PinkhaAnyIntegration

/// Uses the same full, bracketed native editor read and strict resolver as the
/// ordinary Any editor. It owns no fallback text search or cached marker list.
public struct AnyNativeTorahMigrationTargetAccess: AnyTorahSemanticTargetAccess, Sendable {
    public let workspace: AnyTorahWorkspace
    private let access: any AnyTorahTargetAccess
    private let documents: AnyEditorDocumentStore
    private let session: AnyApplicationSession

    public init(access: any AnyTorahTargetAccess, documents: AnyEditorDocumentStore,
                session: AnyApplicationSession) throws {
        guard access.workspace == documents.workspace, access.workspace == session.workspace else {
            throw AnyHostError.wrongWorkspace
        }
        workspace = access.workspace
        self.access = access; self.documents = documents; self.session = session
    }

    public func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) async throws {
        try await access.validate(target, intent: intent)
    }

    public func validateSemanticTarget(_ anchor: PinkhaSemanticTextAnchor) async throws {
        guard anchor.spaceID.utf8.elementsEqual(workspace.spaceID.utf8) else {
            throw PinkhaSemanticTextAnchorError.wrongDocument
        }
        let documents = documents
        let read = try await session.perform { lease in
            try await documents.read(objectID: anchor.objectID, lease: lease)
        }
        guard case .resolved(let fragments) = try AnySemanticAnchorDocument.resolve(anchor, read: read),
              !fragments.isEmpty else { throw AnyHostError.invalidSelection }
    }
}
