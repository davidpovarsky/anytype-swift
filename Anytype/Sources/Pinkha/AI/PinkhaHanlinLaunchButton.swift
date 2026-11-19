import SwiftUI
import UIKit
import Factory

struct PinkhaHanlinLaunchButton: View {
    let routeOwner: SpaceHubCoordinatorViewModel
    @State private var launcher = PinkhaHanlinLauncher()

    var body: some View {
        Button { launcher.open(routeOwner: routeOwner) } label: {
            Image(systemName: "sparkles")
                .foregroundStyle(Color.Control.primary)
                .frame(width: HomeBottomBarMetrics.controlHeight, height: HomeBottomBarMetrics.controlHeight)
                .contentShape(Circle())
        }
        .accessibilityActivationPoint(UnitPoint.center)
        .glassEffectInteractiveIOS26(in: Circle())
        .accessibilityLabel(PinkhaHanlinStrings.title)
        .accessibilityIdentifier("pinkha.hanlin.open")
        .background(PinkhaHanlinAnchor(launcher: launcher))
    }
}

private struct PinkhaHanlinAnchor: UIViewControllerRepresentable {
    let launcher: PinkhaHanlinLauncher
    func makeUIViewController(context: Context) -> UIViewController {
        let controller = UIViewController()
        controller.view.isUserInteractionEnabled = false
        launcher.anchor = controller
        return controller
    }
    func updateUIViewController(_ controller: UIViewController, context: Context) {}
}

/// Resolve only the actual button's mounted window. No application-global scene/window guessing.
@MainActor
private final class PinkhaHanlinLauncher {
    weak var anchor: UIViewController?

    func open(routeOwner: SpaceHubCoordinatorViewModel) {
        guard let window = anchor?.viewIfLoaded?.window,
              window.windowScene?.activationState == .foregroundActive,
              let root = window.rootViewController, root.presentedViewController == nil else { return }
        do {
            let editors = mountedEditors(in: root, window: window)
            guard editors.count <= 1 else { throw PinkhaHanlinLaunchError.ambiguousSource }
            let source: UIViewController = editors.first ?? root
            let presentation = try Container.shared.pinkhaHanlinPresentationBuilder().make(
                presenter: source, routeOwner: routeOwner, conversationID: UUID())
            let controller = PinkhaHanlinChatController(presentation: presentation)
            source.present(controller, animated: true) {
                if controller.viewIfLoaded?.window == nil { presentation.invalidate() }
            }
        } catch {
            let alert = UIAlertController(title: PinkhaHanlinStrings.title,
                message: PinkhaHanlinStrings.openFailed, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: PinkhaHanlinStrings.close, style: .cancel))
            root.present(alert, animated: true)
        }
    }

    private func mountedEditors(in controller: UIViewController, window: UIWindow) -> [EditorPageController] {
        guard controller.presentedViewController == nil, !controller.isBeingDismissed else { return [] }
        if let navigation = controller as? UINavigationController {
            return navigation.visibleViewController.map { mountedEditors(in: $0, window: window) } ?? []
        }
        if let tabs = controller as? UITabBarController {
            return tabs.selectedViewController.map { mountedEditors(in: $0, window: window) } ?? []
        }
        if let editor = controller as? EditorPageController, let view = editor.viewIfLoaded,
           view.window === window, !view.isHidden, view.alpha > 0,
           view.convert(view.bounds, to: window).intersects(window.bounds) { return [editor] }
        return controller.children.flatMap { mountedEditors(in: $0, window: window) }
    }
}

private enum PinkhaHanlinLaunchError: Error { case ambiguousSource }
