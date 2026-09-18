import Foundation
import PinkhaKit
import Services
import AnytypeCore
import SwiftProtobuf
import ProtobufMessages
import Factory
import Logger

/// Service that executes hierarchy mutations (create folder, rename, move, reorder, safe delete)
/// against Anytype's object and property APIs.
final class PinkhaHierarchyMutationService: @unchecked Sendable {

    private static let log = EventLogger(category: "Pinkha")

    @Injected(\.objectActionsService)
    private var objectActionsService: any ObjectActionsServiceProtocol

    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol

    @Injected(\.objectTypeProvider)
    private var objectTypeProvider: any ObjectTypeProviderProtocol

    init() {}

    // MARK: - Folder Creation

    /// Creates a real Anytype Object using `manifest.folderTypeId`, assigning initial parent and order rank.
    /// Returns the fully-populated ObjectDetails so the UI can register it immediately.
    func createFolder(
        name: String,
        parentId: String?,
        spaceId: String,
        manifest: PinkhaSpaceManifest,
        existingSiblings: [PinkhaHierarchyNode]
    ) async throws -> ObjectDetails {
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

        var createdDetails = try response.details.toDetails()

        // Ensure returned ObjectDetails reflects type, name, order, and parent
        var localUpdates: [String: Google_Protobuf_Value] = [
            BundledPropertyKey.name.rawValue: name.protobufValue,
            manifest.orderPropertyKey: order.protobufValue
        ]
        if createdDetails.type.isEmpty {
            localUpdates[BundledPropertyKey.type.rawValue] = manifest.folderTypeId.protobufValue
        }
        if let parentId, !parentId.isEmpty {
            localUpdates[manifest.parentPropertyKey] = parentId.protobufValue
        }
        createdDetails = createdDetails.updated(by: localUpdates)

        Self.log.info("Created folder: objectId=\(createdDetails.id), typeId=\(createdDetails.type), expectedFolderTypeId=\(manifest.folderTypeId)")
        return createdDetails
    }

    // MARK: - Writing Document Creation

    /// Creates a writing document (חידוש, מאמר, מחקר) assigning canonical nextAppendRank from existing siblings.
    func createWritingDocument(
        typeId: String,
        parentId: String?,
        spaceId: String,
        manifest: PinkhaSpaceManifest,
        existingSiblings: [PinkhaHierarchyNode]
    ) async throws -> ObjectDetails {
        let type = try objectTypeProvider.objectType(id: typeId)
        let role = manifest.role(forTypeId: typeId) ?? ""
        let templateId = manifest.defaultTemplateIds[role] ?? type.defaultTemplateId

        let details = try await objectActionsService.createObject(
            name: "",
            typeUniqueKey: type.uniqueKey,
            shouldDeleteEmptyObject: true,
            shouldSelectType: false,
            shouldSelectTemplate: false,
            spaceId: spaceId,
            origin: .none,
            templateId: templateId
        )

        // Assign canonical append rank
        if !manifest.orderPropertyKey.isEmpty {
            let order = PinkhaHierarchyOrdering.nextAppendRank(existingSiblings: existingSiblings)
            var updateDetails: [Anytype_Model_Detail] = [
                Anytype_Model_Detail.with {
                    $0.key = manifest.orderPropertyKey
                    $0.value = order.protobufValue
                }
            ]
            var localUpdates: [String: Google_Protobuf_Value] = [
                manifest.orderPropertyKey: order.protobufValue
            ]
            if details.type.isEmpty {
                localUpdates[BundledPropertyKey.type.rawValue] = typeId.protobufValue
            }
            if let parentId, !parentId.isEmpty {
                updateDetails.append(Anytype_Model_Detail.with {
                    $0.key = manifest.parentPropertyKey
                    $0.value = parentId.protobufValue
                })
                localUpdates[manifest.parentPropertyKey] = parentId.protobufValue
            }
            _ = try await ClientCommands.objectSetDetails(.with {
                $0.contextID = details.id
                $0.details = updateDetails
            }).invoke(qos: .userInitiated)

            let updatedDetails = details.updated(by: localUpdates)
            Self.log.info("Created writing document: objectId=\(updatedDetails.id), typeId=\(updatedDetails.type)")
            return updatedDetails
        }

        Self.log.info("Created writing document: objectId=\(details.id), typeId=\(details.type)")
        return details
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
    ) async throws -> Double {
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

        Self.log.info("Moved node: objectId=\(objectId), newParentId=\(newParentId ?? "root"), newOrder=\(newOrder)")
        return newOrder
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
    /// before deleting the folder object itself. Re-ranks all moved children after destination siblings.
    /// Never silently orphans user documents or collides ranks.
    func deleteFolderSafely(
        objectId: String,
        spaceId: String,
        manifest: PinkhaSpaceManifest,
        snapshot: PinkhaHierarchySnapshot
    ) async throws {
        guard snapshot.node(for: objectId) != nil else {
            return
        }

        let plans = PinkhaHierarchyOrdering.planSafeFolderDeletion(targetFolderId: objectId, in: snapshot)

        // Execute all reparent and re-rank plans first
        for plan in plans {
            var details: [Anytype_Model_Detail] = [
                Anytype_Model_Detail.with {
                    $0.key = manifest.orderPropertyKey
                    $0.value = plan.newOrder.protobufValue
                }
            ]

            if let dest = plan.newParentId, !dest.isEmpty {
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
                $0.contextID = plan.objectId
                $0.details = details
            }).invoke(qos: .userInitiated)
        }

        // Only delete the folder object itself once all children have been safely reparented & re-ranked
        try await objectActionsService.delete(objectIds: [objectId])
    }
}
