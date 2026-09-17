import Foundation

/// Repository protocol abstracting Anytype-backed storage for user-created Torah associations.
public protocol TorahAssociationRepository: Sendable {
    /// Lists all Torah associations attached to the specified document (whole-object scope).
    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem]

    /// Lists all Torah associations attached to a specific block within a document.
    func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem]

    /// Adds or replaces document-level associations.
    func setDocumentAssociations(objectId: String, items: [TorahAssociationItem], spaceId: String) async throws

    /// Adds or replaces block-level associations.
    func setBlockAssociations(objectId: String, blockId: String, items: [TorahAssociationItem], spaceId: String) async throws

    /// Removes a specific association from a document or block.
    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String) async throws
}
