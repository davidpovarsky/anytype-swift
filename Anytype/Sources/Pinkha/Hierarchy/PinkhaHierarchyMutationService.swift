import Foundation
import PinkhaKit
import Services
import AnytypeCore
import SwiftProtobuf
import ProtobufMessages
import Factory

/// Service that executes hierarchy mutations (create folder, rename, move, reorder, safe delete)
/// against Anytype's object and property APIs.
final class PinkhaHierarchyMutationService: @unchecked Sendable {

    @Injected(\.objectActionsService)
    private var objectActionsService: any ObjectActionsServiceProtocol

    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol

    @Injected(\.objectTypeProvider)
    private var objectTypeProvider: any ObjectTypeProviderProtocol

    init() {}

    // MARK: - Folder Creation

    /// Creates a real Anytype Object using `manifest.folderTypeId`, assigning initial parent and order rank.
    func createFolder(
        name: String,
        parentId: String?,
        spaceId: String,
        manifest: PinkhaSpaceManifest,
        existingSiblings: [PinkhaHierarchyNode]
    ) async throws -> String {
        let order = PinkhaHierarchyOrdering.nextAppendRank(existingSiblings: existingSiblings)
        let type = try objectTypeProvider.objectType(id: manifest.folderTypeId)

        var fields: [String: Google_Protobuf_Value] = [
            BundledPropertyKey.name.rawValue: name.protobufValue,
            BundledPropertyKey.origin.rawValue: ObjectOrigin.none.rawValue.protobufValue,
            manifest.orderPropertyKey: order.protobufValue
        ]

        if let parentId, !parentId.isEmpty {
            fields[manifest.parentPropertyKey] = parentId.protobufValue
        }

        let details = Google_Protobuf_Struct(fields: fields)
        let response = try await ClientCommands.objectCreate(.with {
            $0.details = details
            $0.spaceID = spaceId
            $0.objectTypeUniqueKey = type.uniqueKey.value
        }).invoke(qos: .userInitiated)

        let createdDetails = try response.details.toDetails()
        return createdDetails.id
    }

    // MARK: - Folder Rename

    /// Renames a folder by updating its name property.
    func renameFolder(objectId: String, newName: String) async throws {
        try await propertiesService.updateProperty(
            objectId: objectId,
            propertyKey: BundledPropertyKey.name.rawValue,
            value: newName.protobufValue
        )
    }

    // MARK: - Move Node

    /// Moves an object (folder or document) to a new parent or to root.
    /// Validates cycles before writing, computes new sparse rank, and does not rewrite createdInContext.
    func move(
        objectId: String,
        newParentId: String?,
        spaceId: String,
        manifest: PinkhaSpaceManifest,
        snapshot: PinkhaHierarchySnapshot
    ) async throws {
        // Validate cycle prevention
        try PinkhaHierarchyMutationValidator.validateMove(objectId: objectId, newParentId: newParentId, in: snapshot)

        // Calculate new order under target parent
        let destinationSiblings = snapshot.children(of: newParentId).filter { $0.objectId != objectId }
        let newOrder = PinkhaHierarchyOrdering.nextAppendRank(existingSiblings: destinationSiblings)

        var details = [
            Anytype_Model_Detail.with {
                $0.key = manifest.orderPropertyKey
                $0.value = newOrder.protobufValue
            }
        ]

        if let newParentId, !newParentId.isEmpty {
            details.append(Anytype_Model_Detail.with {
                $0.key = manifest.parentPropertyKey
                $0.value = newParentId.protobufValue
            })
        } else {
            // Move to root: clear parent property
            details.append(Anytype_Model_Detail.with {
                $0.key = manifest.parentPropertyKey
                $0.value = Google_Protobuf_Value()
            })
        }

        _ = try await ClientCommands.objectSetDetails(.with {
            $0.contextID = objectId
            $0.details = details
        }).invoke(qos: .userInitiated)
    }

    // MARK: - Reorder Siblings

    /// Updates the order rank of an object.
    func updateOrder(objectId: String, newRank: Double, manifest: PinkhaSpaceManifest) async throws {
        try await propertiesService.updateProperty(
            objectId: objectId,
            propertyKey: manifest.orderPropertyKey,
            value: newRank.protobufValue
        )
    }

    /// Rebalances only the specified sibling group when ranks become dense.
    func rebalanceSiblings(siblings: [PinkhaHierarchyNode], manifest: PinkhaSpaceManifest) async throws {
        let rebalanced = PinkhaHierarchyOrdering.rebalanceRanks(siblings: siblings)
        for item in rebalanced {
            try await updateOrder(objectId: item.objectId, newRank: item.newRank, manifest: manifest)
        }
    }

    // MARK: - Safe Folder Deletion

    /// Safely deletes a folder by reparenting all its direct children to the deleted folder's parent
    /// before deleting the folder object itself. Never silently orphans user documents.
    func deleteFolderSafely(
        objectId: String,
        spaceId: String,
        manifest: PinkhaSpaceManifest,
        snapshot: PinkhaHierarchySnapshot
    ) async throws {
        guard let targetNode = snapshot.node(for: objectId) else {
            return
        }

        let directChildren = targetNode.children
        let destinationParentId = targetNode.parentId // nil if target was at root

        // Reparent all direct children to targetNode's parent
        for child in directChildren {
            var details: [Anytype_Model_Detail] = []
            if let dest = destinationParentId, !dest.isEmpty {
                details.append(Anytype_Model_Detail.with {
                    $0.key = manifest.parentPropertyKey
                    $0.value = dest.protobufValue
                })
            } else {
                details.append(Anytype_Model_Detail.with {
                    $0.key = manifest.parentPropertyKey
                    $0.value = Google_Protobuf_Value()
                })
            }

            _ = try await ClientCommands.objectSetDetails(.with {
                $0.contextID = child.objectId
                $0.details = details
            }).invoke(qos: .userInitiated)
        }

        // Delete the folder object itself
        try await objectActionsService.delete(objectIds: [objectId])
    }
}
