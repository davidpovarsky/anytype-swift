#if canImport(UIKit)
import UIKit
import SwiftUI
import HanlinHostContracts
import PinkhaHanlinCore

/// Native presentation I/O only. The canonical SDK integration and shared Core
/// remain responsible for permissions, replay, receipts and cancellation.
@MainActor
public protocol PinkhaHanlinPresentationHost: AnyObject, Sendable {
    var session: HanlinHostSession { get }
    var integration: any HanlinHostIntegration { get }
    func install(_ presentation: PinkhaHanlinChatPresentation,
                 controller: PinkhaHanlinChatController) throws
    func observeInvalidation(_ callback: @escaping @MainActor () -> Void)
    func requestContextReadConsent() async throws
    func makeReturnHandoff(_ destination: HanlinHostDestination,
                          controller: PinkhaHanlinChatController) throws -> PinkhaHanlinNavigationHandoff
    func revokePresentation()
    func invalidate() async
}

@MainActor
public struct PinkhaHanlinPresentationHooks {
    public var didMount: @MainActor (PinkhaHanlinChatPresentation, PinkhaHanlinChatController) -> Void
    public var invalidated: @MainActor (UUID, String) -> Void
    public init(
        didMount: @escaping @MainActor (PinkhaHanlinChatPresentation, PinkhaHanlinChatController) -> Void = { _, _ in },
        invalidated: @escaping @MainActor (UUID, String) -> Void = { _, _ in }
    ) {
        self.didMount = didMount; self.invalidated = invalidated
    }
}

public enum PinkhaHanlinLabelStyle: Equatable, Sendable { case body, caption }

/// Keeps the retained application's label design while the native application
/// can use semantic system text. Canonical Hanlin message/composer UI is shared.
@MainActor
public struct PinkhaHanlinAppearance {
    public let label: @MainActor (String, PinkhaHanlinLabelStyle) -> AnyView
    public let secondary: Color

    public init(secondary: Color,
                label: @escaping @MainActor (String, PinkhaHanlinLabelStyle) -> AnyView) {
        self.secondary = secondary; self.label = label
    }
    public static var system: Self {
        .init(secondary: .secondary) { text, style in
            AnyView(Text(text).font(style == .caption ? .caption : .body))
        }
    }
}
#endif
