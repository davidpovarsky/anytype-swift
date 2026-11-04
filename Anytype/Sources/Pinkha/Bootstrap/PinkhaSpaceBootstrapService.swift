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
        return manifest
    }
}
