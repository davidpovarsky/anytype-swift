import Foundation

public enum TorahAssociationRepositoryError: Error, Sendable, Equatable {
    case unsafeSnapshotReplacement
    case associationNotFound(String)
    case targetNotFound
    case targetOutsideSpace
    case permissionDenied
    case malformedCanonicalData
    case unsupportedPayloadVersion(Int)
    case writeConflict(String)
    case writeUncertain(String)
    case backendFailure(String)
}

/// Space-scoped association storage. Every mutating requirement changes one logical item only.
public protocol TorahAssociationRepository: Sendable {
    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem]
    func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem]

    @discardableResult
    func addAssociation(
        _ item: TorahAssociationItem,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws -> TorahAssociationItem

    @discardableResult
    func upsertAssociation(
        _ item: TorahAssociationItem,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws -> TorahAssociationItem

    @discardableResult
    func updateAssociation(
        _ item: TorahAssociationItem,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws -> TorahAssociationItem

    func removeAssociation(
        associationId: String,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws
}

public extension TorahAssociationRepository {
    /// Retained for source compatibility. A stale full snapshot is never accepted implicitly.
    @available(*, deprecated, message: "Use addAssociation/upsertAssociation/updateAssociation per item")
    func setDocumentAssociations(
        objectId: String,
        items: [TorahAssociationItem],
        spaceId: String
    ) async throws {
        throw TorahAssociationRepositoryError.unsafeSnapshotReplacement
    }

    /// Retained for source compatibility. A stale full snapshot is never accepted implicitly.
    @available(*, deprecated, message: "Use addAssociation/upsertAssociation/updateAssociation per item")
    func setBlockAssociations(
        objectId: String,
        blockId: String,
        items: [TorahAssociationItem],
        spaceId: String
    ) async throws {
        throw TorahAssociationRepositoryError.unsafeSnapshotReplacement
    }
}
