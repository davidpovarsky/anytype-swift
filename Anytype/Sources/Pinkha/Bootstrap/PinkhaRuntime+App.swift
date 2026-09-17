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
}
