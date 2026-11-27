import Foundation
import UIKit
import SwiftUI
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaHanlinUI

typealias PinkhaHanlinChatPresentation = PinkhaHanlinUI.PinkhaHanlinChatPresentation
typealias PinkhaHanlinModelConfiguration = PinkhaHanlinUI.PinkhaHanlinModelConfiguration

/// Retained Heart composition only. Canonical UI, model execution, credentials,
/// message bounds, lifetime cleanup and receipts have one shared implementation.
extension PinkhaHanlinChatPresentation {
    convenience init(presenter: UIViewController, routeOwner: SpaceHubCoordinatorViewModel,
                     conversationID: UUID, locale: Locale) throws {
        #if DEBUG && targetEnvironment(simulator)
        let preparation = try PinkhaHanlinSaveMessageAcceptancePreparation.loadIfRequested(engine: .heart)
        let saveFixture = preparation == nil
            ? try PinkhaHanlinSaveMessageAcceptanceFixture.loadIfRequested(engine: .heart) : nil
        let saveAcceptance = preparation != nil || saveFixture != nil
            ? try PinkhaHanlinHeartSaveAcceptance(request: preparation, fixture: saveFixture, presenter: presenter) : nil
        let host: PinkhaHanlinReadWriteHost
        if saveFixture != nil {
            host = try PinkhaHanlinReadWriteHost.makeForSaveMessageAcceptance(presenter: presenter, routeOwner: routeOwner,
                conversationID: conversationID, locale: locale)
        } else {
            host = try PinkhaHanlinReadWriteHost.make(presenter: presenter, routeOwner: routeOwner,
                conversationID: conversationID, locale: locale)
        }
        #else
        let host = try PinkhaHanlinReadWriteHost.make(presenter: presenter, routeOwner: routeOwner,
            conversationID: conversationID, locale: locale)
        #endif
        let hooks = PinkhaHanlinPresentationHooks(
            didMount: { [weak presenter, weak routeOwner] presentation, controller in
                #if DEBUG && targetEnvironment(simulator)
                saveAcceptance?.didMount(host: host, presentation: presentation, controller: controller)
                PinkhaHanlinNativeAcceptanceDriver.startIfRequested(host: host, presentation: presentation,
                    controller: controller, source: presenter, routeOwner: routeOwner)
                PinkhaHanlinSelectionAcceptanceDriver.startIfRequested(host: host, presentation: presentation,
                    controller: controller, source: presenter)
                #endif
            },
            invalidated: { sessionID, cause in
                #if DEBUG && targetEnvironment(simulator)
                saveAcceptance?.invalidate()
                PinkhaHanlinNativeAcceptanceDriver.observedInvalidation(sessionID: sessionID, cause: cause)
                #endif
            })
        let appearance = PinkhaHanlinAppearance(secondary: Color.Text.secondary) { text, style in
            switch style {
            case .body: AnyView(AnytypeText(text, style: .bodyRegular))
            case .caption: AnyView(AnytypeText(text, style: .caption1Regular))
            }
        }
        try self.init(host: HeartHanlinPresentationHost(host), presenter: presenter,
                      appearance: appearance, hooks: hooks)
    }
}

@MainActor
private final class HeartHanlinPresentationHost: PinkhaHanlinPresentationHost {
    private let host: PinkhaHanlinReadWriteHost
    init(_ host: PinkhaHanlinReadWriteHost) { self.host = host }
    var session: HanlinHostSession { host.session }
    var integration: any HanlinHostIntegration { host }
    func install(_ presentation: PinkhaHanlinChatPresentation,
                 controller: PinkhaHanlinChatController) throws {
        try host.install(presentation, controller: controller)
    }
    func observeInvalidation(_ callback: @escaping @MainActor () -> Void) { host.observeInvalidation(callback) }
    func requestContextReadConsent() async throws { try await host.requestContextReadConsent() }
    func makeReturnHandoff(_ destination: HanlinHostDestination,
                          controller: PinkhaHanlinChatController) throws -> PinkhaHanlinNavigationHandoff {
        try host.makeReturnHandoff(destination, controller: controller)
    }
    func revokePresentation() { host.revokePresentation() }
    func invalidate() async { await host.invalidate() }
}
