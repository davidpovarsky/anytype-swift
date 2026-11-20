import SwiftUI

extension EnvironmentValues {
    @Entry var pageEditorAdditionalSafeAreaInsets: UIEdgeInsets = .zero
}

extension View {
    func pageEditorAdditionalSafeAreaInsets(_ insets: UIEdgeInsets) -> some View {
        environment(\.pageEditorAdditionalSafeAreaInsets, insets)
    }
}

struct EditorSwiftUIViewContainer: UIViewControllerRepresentable {
    
    @Environment(\.pageEditorAdditionalSafeAreaInsets) private var pageEditorAdditionalSafeAreaInsets
    @Environment(\.pageNavigationHiddenBackButton) private var pageNavigationHiddenBackButton
    @Environment(\.pinkhaHanlinRouteOwner) private var pinkhaHanlinRouteOwner
    
    let viewController: EditorPageController
    var preparedSession: PreparedEditorPageSession? = nil

    @MainActor
    final class Coordinator {
        let controller: EditorPageController
        let session: PreparedEditorPageSession?
        let hostLease: EditorDocumentWriteLifetime.Observation?

        init(controller: EditorPageController, session: PreparedEditorPageSession?) {
            self.controller = controller
            self.session = session
            do {
                self.hostLease = try session?.attachHost(controller: controller)
            } catch {
                session?.retire()
                self.hostLease = nil
            }
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(controller: viewController, session: preparedSession)
    }

    static func dismantleUIViewController(_ uiViewController: EditorPageController, coordinator: Coordinator) {
        guard coordinator.controller === uiViewController else { return }
        coordinator.hostLease?.cancel()
        coordinator.session?.retire(controller: uiViewController)
    }

    func makeUIViewController(context: Context) -> EditorPageController {
        viewController
    }
    
    func updateUIViewController(_ uiViewController: EditorPageController, context: Context) {
        viewController.additionalSafeAreaInsets = pageEditorAdditionalSafeAreaInsets
        viewController.setPageNavigationHiddenBackButton(pageNavigationHiddenBackButton)
        viewController.setPinkhaHanlinRouteOwner(pinkhaHanlinRouteOwner)
    }
}
