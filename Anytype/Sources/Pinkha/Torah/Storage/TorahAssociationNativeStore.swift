import Foundation
import PinkhaKit
import Services
import AnytypeCore
import Factory
import ProtobufMessages
import SwiftProtobuf

struct TorahAssociationNativeDocumentSnapshot: Sendable, Equatable {
    let spaceId: String
    let objectId: String
    let isDeleted: Bool
    let isArchived: Bool
    let canWriteDetails: Bool
    let blockIds: Set<String>
    let propertyValue: String?
}

protocol TorahAssociationNativeStore: Sendable {
    func readDocument(
        spaceId: String,
        objectId: String,
        propertyKey: String
    ) async throws -> TorahAssociationNativeDocumentSnapshot

    func writeDocumentProperty(
        objectId: String,
        propertyKey: String,
        value: String
    ) async throws
}

final class MiddlewareTorahAssociationNativeStore: TorahAssociationNativeStore, @unchecked Sendable {
    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol

    init() {}

    func readDocument(
        spaceId: String,
        objectId: String,
        propertyKey: String
    ) async throws -> TorahAssociationNativeDocumentSnapshot {
        let response: Anytype_Rpc.Object.Show.Response
        do {
            response = try await ClientCommands.objectShow(.with {
                $0.contextID = objectId
                $0.objectID = objectId
                $0.spaceID = spaceId
            }).invoke(qos: .userInitiated, ignoreLogErrors: .objectDeleted)
        } catch let error as Anytype_Rpc.Object.Show.Response.Error {
            switch error.code {
            case .notFound, .objectDeleted:
                throw TorahAssociationRepositoryError.targetNotFound
            case .anytypeNeedsUpgrade:
                throw TorahAssociationRepositoryError.backendFailure("Anytype middleware upgrade required")
            default:
                throw TorahAssociationRepositoryError.backendFailure(error.description_p)
            }
        } catch {
            throw TorahAssociationRepositoryError.backendFailure(error.localizedDescription)
        }

        guard let detailsStruct = response.objectView.details.first(where: { $0.id == objectId })?.details else {
            throw TorahAssociationRepositoryError.targetNotFound
        }

        let details: ObjectDetails
        do {
            details = try ObjectDetails(protobufStruct: detailsStruct)
        } catch {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }

        let restrictions = MiddlewareObjectRestrictionsConverter
            .convertObjectRestrictions(middlewareRestrictions: response.objectView.restrictions)
            .objectRestriction
        let canWriteDetails = !details.isReadonly && !restrictions.contains(.details)
        let rawValue = details.values[propertyKey]
        let propertyValue: String? = if let rawValue, case .stringValue(let value) = rawValue.kind {
            value
        } else {
            nil
        }

        return TorahAssociationNativeDocumentSnapshot(
            spaceId: details.spaceId,
            objectId: details.id,
            isDeleted: details.isDeleted,
            isArchived: details.isArchived,
            canWriteDetails: canWriteDetails,
            blockIds: Set(response.objectView.blocks.map(\.id)),
            propertyValue: propertyValue
        )
    }

    func writeDocumentProperty(
        objectId: String,
        propertyKey: String,
        value: String
    ) async throws {
        do {
            try await propertiesService.updateProperty(
                objectId: objectId,
                propertyKey: propertyKey,
                value: value.protobufValue
            )
        } catch {
            throw TorahAssociationRepositoryError.backendFailure(error.localizedDescription)
        }
    }
}

protocol TorahAssociationManifestProvider: Sendable {
    func manifest(spaceId: String) async throws -> PinkhaSpaceManifest
}

final class BootstrapTorahAssociationManifestProvider: TorahAssociationManifestProvider, Sendable {
    private let bootstrapService: any PinkhaSpaceBootstrapServiceProtocol

    init(
        bootstrapService: any PinkhaSpaceBootstrapServiceProtocol = Container.shared.pinkhaBootstrapService()
    ) {
        self.bootstrapService = bootstrapService
    }

    func manifest(spaceId: String) async throws -> PinkhaSpaceManifest {
        let manifest = try await bootstrapService.bootstrapSpace(spaceId: spaceId)
        guard manifest.spaceId == spaceId else {
            throw TorahAssociationRepositoryError.targetOutsideSpace
        }
        guard manifest.isFullyProvisioned,
              !manifest.documentAssociationsPropertyKey.isEmpty else {
            throw TorahAssociationRepositoryError.backendFailure("Pinkha Space manifest is incomplete")
        }
        return manifest
    }
}
