import Foundation
import PinkhaKit
import Services
import AnytypeCore
import Factory
import SwiftProtobuf
import ProtobufMessages

/// Canonical synced Anytype-backed manifest store.
/// Stores the PinkhaSpaceManifest as an internal hidden object within the Anytype Space.
/// Synchronizes across devices using Anytype's native CRDT sync engine without secondary local databases.
public final class PinkhaSpaceManifestStore: PinkhaSpaceManifestStoreProtocol, Sendable {

    @Injected(\.searchMiddleService)
    private var searchMiddleService: any SearchMiddleServiceProtocol

    public init() {}

    public func discoverManifestObjectId(spaceId: String) async throws -> String? {
        let filters: [DataviewFilter] = .builder {
            SearchHelper.uniqueKeyFilter(key: PinkhaSchemaRoles.manifestUniqueKey, include: true)
        }

        let results = try await searchMiddleService.search(
            spaceId: spaceId,
            filters: filters,
            sorts: [],
            fullText: ""
        )

        guard !results.isEmpty else {
            return nil
        }

        if results.count == 1 {
            return results[0].id
        }

        // Multi-client conflict reconciliation:
        // Decode candidate manifests and pick canonical one:
        // 1. Complete > InProgress
        // 2. Higher schemaVersion
        // 3. Most recently updated
        // 4. Deterministic ID tie-breaker
        var bestId = results[0].id
        var bestManifest: PinkhaSpaceManifest?

        for result in results {
            if let jsonString = result.values[BundledPropertyKey.description.rawValue]?.stringValue,
               let manifest = try? PinkhaSpaceManifest.fromJSONString(jsonString) {
                if let currentBest = bestManifest {
                    if isManifest(manifest, preferredOver: currentBest) {
                        bestManifest = manifest
                        bestId = result.id
                    }
                } else {
                    bestManifest = manifest
                    bestId = result.id
                }
            }
        }

        return bestId
    }

    private func isManifest(_ candidate: PinkhaSpaceManifest, preferredOver current: PinkhaSpaceManifest) -> Bool {
        if candidate.isComplete != current.isComplete {
            return candidate.isComplete
        }
        if candidate.schemaVersion != current.schemaVersion {
            return candidate.schemaVersion > current.schemaVersion
        }
        if candidate.updatedAt != current.updatedAt {
            return candidate.updatedAt > current.updatedAt
        }
        return (candidate.manifestObjectId ?? "") < (current.manifestObjectId ?? "")
    }

    public func loadManifest(spaceId: String) async throws -> PinkhaSpaceManifest? {
        guard let objectId = try await discoverManifestObjectId(spaceId: spaceId) else {
            return nil
        }

        let objectShow = try await ClientCommands.objectShow(.with {
            $0.contextID = objectId
            $0.objectID = objectId
            $0.spaceID = spaceId
        }).invoke(qos: .userInitiated, ignoreLogErrors: .objectDeleted)

        guard let details = objectShow.objectView.details.first(where: { $0.id == objectId })?.details,
              let objectDetails = try? ObjectDetails(protobufStruct: details) else {
            return nil
        }

        guard let jsonString = objectDetails.values[BundledPropertyKey.description.rawValue]?.stringValue,
              !jsonString.isEmpty else {
            return nil
        }

        var manifest = try PinkhaSpaceManifest.fromJSONString(jsonString)
        manifest.manifestObjectId = objectId
        return manifest
    }

    public func saveManifest(_ manifest: PinkhaSpaceManifest) async throws -> PinkhaSpaceManifest {
        var updated = manifest
        let jsonString = try manifest.toJSONString()

        let targetObjectId: String?
        if let currentId = manifest.manifestObjectId {
            targetObjectId = currentId
        } else {
            targetObjectId = try await discoverManifestObjectId(spaceId: manifest.spaceId)
        }

        if let existingObjectId = targetObjectId {
            updated.manifestObjectId = existingObjectId
            let payloadJson = try updated.toJSONString()

            _ = try await ClientCommands.objectSetDetails(.with {
                $0.contextID = existingObjectId
                $0.details = [
                    Anytype_Model_Detail.with {
                        $0.key = BundledPropertyKey.description.rawValue
                        $0.value = payloadJson.protobufValue
                    },
                    Anytype_Model_Detail.with {
                        $0.key = BundledPropertyKey.lastUsedDate.rawValue
                        $0.value = Date().protobufValue
                    }
                ]
            }).invoke(qos: .userInitiated)

            return updated
        } else {
            // Create new internal Anytype object in Space
            let fields: [String: Google_Protobuf_Value] = [
                BundledPropertyKey.name.rawValue: PinkhaSchemaRoles.manifestName.protobufValue,
                BundledPropertyKey.uniqueKey.rawValue: PinkhaSchemaRoles.manifestUniqueKey.protobufValue,
                BundledPropertyKey.description.rawValue: jsonString.protobufValue,
                BundledPropertyKey.isHidden.rawValue: true.protobufValue,
                BundledPropertyKey.origin.rawValue: ObjectOrigin.none.rawValue.protobufValue
            ]

            let response = try await ClientCommands.objectCreate(.with {
                $0.details = Google_Protobuf_Struct(fields: fields)
                $0.spaceID = manifest.spaceId
                $0.objectTypeUniqueKey = ObjectTypeUniqueKey.page.value
            }).invoke(qos: .userInitiated)

            let objectDetails = try response.details.toDetails()
            let objectId = objectDetails.id
            updated.manifestObjectId = objectId

            // Update with the final JSON containing its own manifestObjectId
            let finalJson = try updated.toJSONString()
            _ = try await ClientCommands.objectSetDetails(.with {
                $0.contextID = objectId
                $0.details = [
                    Anytype_Model_Detail.with {
                        $0.key = BundledPropertyKey.description.rawValue
                        $0.value = finalJson.protobufValue
                    }
                ]
            }).invoke(qos: .userInitiated)

            return updated
        }
    }
}
