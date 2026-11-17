import Foundation
import UIKit
import Factory

/// Stateless builder; no default/global account, scene, object, permission or writable catalog.
@MainActor
final class PinkhaHanlinPresentationBuilder {
    nonisolated init() {}

    func make(presenter: UIViewController, routeOwner: SpaceHubCoordinatorViewModel,
              conversationID: UUID, locale: Locale = .autoupdatingCurrent) throws -> PinkhaHanlinChatPresentation {
        try PinkhaHanlinChatPresentation(presenter: presenter, routeOwner: routeOwner,
            conversationID: conversationID, locale: locale)
    }
}

extension Container {
    var pinkhaHanlinPresentationBuilder: Factory<PinkhaHanlinPresentationBuilder> {
        self { PinkhaHanlinPresentationBuilder() }
    }
}
