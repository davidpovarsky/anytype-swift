import Foundation
import PinkhaKit
import Services
import AnytypeCore
import Factory

public protocol PinkhaSpaceBootstrapServiceProtocol: Sendable {
    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest
    /// The canonical associations repository does not depend on optional native schema installation.
    func bootstrapCanonicalSpace(spaceId: String) async throws -> PinkhaSpaceManifest
    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest?
    func isBootstrapped(spaceId: String) -> Bool
}

public extension PinkhaSpaceBootstrapServiceProtocol {
    /// Preserve compatibility with injected test implementations of the bootstrap protocol.
    func bootstrapCanonicalSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
        try await bootstrapSpace(spaceId: spaceId)
    }
}

public final class PinkhaSpaceBootstrapService: PinkhaSpaceBootstrapServiceProtocol, Sendable {
    private let engine: PinkhaSpaceBootstrapEngine
    private let nativeProperties: TorahNativeSchemaProvisioner?

    public init(
        store: any PinkhaSpaceManifestStoreProtocol = Container.shared.pinkhaSpaceManifestStore(),
        propertyService: any PinkhaPropertyServiceProtocol = Container.shared.pinkhaPropertyServiceAdapter(),
        typeService: any PinkhaTypeServiceProtocol = Container.shared.pinkhaTypeServiceAdapter(),
        templateService: any PinkhaTemplateServiceProtocol = Container.shared.pinkhaTemplateServiceAdapter(),
        migrator: PinkhaSchemaMigrator = Container.shared.pinkhaSchemaMigrator(),
        nativeProperties: TorahNativeSchemaProvisioner? = nil
    ) {
        self.engine = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propertyService,
            typeService: typeService,
            templateService: templateService,
            migrator: migrator
        )
        self.nativeProperties = nativeProperties
    }

    public func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? {
        engine.manifest(forSpaceId: spaceId)
    }

    public func isBootstrapped(spaceId: String) -> Bool {
        engine.isBootstrapped(spaceId: spaceId)
    }

    public func bootstrapCanonicalSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
        try await engine.bootstrapSpace(spaceId: spaceId)
    }

    public func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
        let manifest = try await bootstrapCanonicalSpace(spaceId: spaceId)
        if let nativeProperties {
            do {
                _ = try await nativeProperties.provision(manifest: manifest)
            } catch TorahNativeSchemaError.unsupportedEngine {
                // An older middleware retains the existing canonical picker;
                // never register non-derived fields against an incapable engine.
            }
        }
        await repairWritingTypesDefaultsIfNeeded(manifest: manifest)
        return manifest
    }

    private func repairWritingTypesDefaultsIfNeeded(manifest: PinkhaSpaceManifest) async {
        let typeKeysAndDefaults: [(String, CustomIcon, CustomIconColor)] = [
            (PinkhaSchemaRoles.chiddushKey, .bulb, .yellow),
            (PinkhaSchemaRoles.articleKey, .documentText, .blue),
            (PinkhaSchemaRoles.researchKey, .library, .purple)
        ]

        let detailsService: any DetailsServiceProtocol = Container.shared.detailsService()
        let propertiesService: any PropertiesServiceProtocol = Container.shared.propertiesService()

        for (roleKey, defaultIcon, defaultColor) in typeKeysAndDefaults {
            guard let typeId = manifest.registeredDocumentTypes[roleKey], !typeId.isEmpty else { continue }
            try? await detailsService.updateBundledDetails(
                objectId: typeId,
                bundledDetails: [
                    .recommendedLayout(DetailsLayout.basic.rawValue),
                    .iconName(defaultIcon.stringRepresentation),
                    .iconOption(defaultColor.iconOption)
                ]
            )

            if let templateId = manifest.defaultTemplateIds[roleKey], !templateId.isEmpty {
                try? await propertiesService.toggleDescription(objectId: templateId, isOn: true)
            }
        }
    }
}
