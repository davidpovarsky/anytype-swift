import Foundation
import SwiftUI
import AnytypeCore

struct DismissAllPresented: Equatable {

    private weak var window: UIWindow?
    private weak var scopedRoot: UIViewController?

    init(window: UIWindow?) {
        self.window = window
    }

    init(rootViewController: UIViewController?) {
        self.scopedRoot = rootViewController
    }

    func callAsFunction(animated: Bool = true) async {
        await withCheckedContinuation { continuation in
            Task { @MainActor [weak window, weak scopedRoot] in
                if let scopedRoot {
                    // Dismiss descendants only; never dismiss the embedded
                    // account presentation or a host window's controller.
                    guard scopedRoot.presentedViewController != nil else {
                        continuation.resume()
                        return
                    }
                    scopedRoot.dismiss(animated: animated) { continuation.resume() }
                } else if let root = window?.rootViewController,
                   !FeatureFlags.fixAvatarTapFreeze || root.presentedViewController != nil {
                    root.dismiss(animated: animated, completion: {
                        continuation.resume()
                    })
                } else {
                    continuation.resume()
                }
            }
        }
    }
}

extension EnvironmentValues {
    @Entry var dismissAllPresented = DismissAllPresented(window: nil)
}

extension View {
    func setPresentedDismissEnv(window: UIWindow?) -> some View {
        environment(\.dismissAllPresented, DismissAllPresented(window: window))
    }
}

extension View {
    func setPresentedDismissEnv(rootViewController: UIViewController?) -> some View {
        environment(\.dismissAllPresented, DismissAllPresented(rootViewController: rootViewController))
    }
}
