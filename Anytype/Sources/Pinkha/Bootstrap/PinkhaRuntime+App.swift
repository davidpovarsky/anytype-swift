import Foundation
import Factory
import PinkhaKit

extension Container {
    public var pinkhaBootstrapService: Factory<any PinkhaSpaceBootstrapServiceProtocol> {
        self { PinkhaSpaceBootstrapService() }.singleton
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
}
