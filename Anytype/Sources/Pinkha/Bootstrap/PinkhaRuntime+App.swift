import Foundation
import Factory
import PinkhaKit

extension Container {
    public var pinkhaBootstrapService: Factory<any PinkhaSpaceBootstrapServiceProtocol> {
        self {
            PinkhaSpaceBootstrapService(nativeProperties: TorahNativeSchemaProvisioner(
                store: AnytypeTorahNativePropertyProvisioningStore()
            ))
        }.singleton
    }

    public var pinkhaSchemaMigrator: Factory<PinkhaSchemaMigrator> {
        self { PinkhaSchemaMigrator() }.singleton
    }

    public var pinkhaSpaceManifestStore: Factory<any PinkhaSpaceManifestStoreProtocol> {
        self { PinkhaSpaceManifestStore() }.singleton
    }

    public var pinkhaPropertyServiceAdapter: Factory<any PinkhaPropertyServiceProtocol> {
        self { AnytypePropertyServiceAdapter() }.singleton
    }

    public var pinkhaTypeServiceAdapter: Factory<any PinkhaTypeServiceProtocol> {
        self { AnytypeTypeServiceAdapter() }.singleton
    }

    public var pinkhaTemplateServiceAdapter: Factory<any PinkhaTemplateServiceProtocol> {
        self { AnytypeTemplateServiceAdapter() }.singleton
    }

    public var pinkhaBootstrapStateManager: Factory<PinkhaBootstrapStateManager> {
        self { PinkhaBootstrapStateManager() }.singleton
    }

    public var pinkhaTorahPropertyPolicy: Factory<PinkhaTorahPropertyPolicy> {
        self { PinkhaTorahPropertyPolicy.shared }.singleton
    }

    public var pinkhaTorahNativePropertyCatalog: Factory<PinkhaTorahNativePropertyCatalog> {
        self { PinkhaTorahNativePropertyCatalog.shared }.singleton
    }
}
