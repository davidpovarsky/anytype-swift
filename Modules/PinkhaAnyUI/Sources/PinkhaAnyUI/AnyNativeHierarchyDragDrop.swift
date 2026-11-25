#if canImport(UIKit) && canImport(SwiftUI)
import SwiftUI
import UIKit
import PinkhaAnyHost

/// The local token retains the original session identity. A drag from a retired
/// account/window cannot be reinterpreted as a write in the newly mounted Space.
@MainActor
private final class AnyHierarchyLocalDrag: NSObject {
    let session: AnyApplicationSession
    let objectID: String
    init(session: AnyApplicationSession, objectID: String) {
        self.session = session
        self.objectID = objectID
    }
}

@MainActor
struct AnyNativeHierarchyDragHandle: UIViewRepresentable {
    let session: AnyApplicationSession
    let objectID: String
    let title: String
    let canDrag: @MainActor () -> Bool

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    func makeUIView(context: Context) -> UIImageView {
        let view = UIImageView(image: UIImage(systemName: "line.3.horizontal"))
        view.contentMode = .center
        view.tintColor = .secondaryLabel
        view.isUserInteractionEnabled = true
        view.isAccessibilityElement = true
        view.accessibilityTraits = .button
        let interaction = UIDragInteraction(delegate: context.coordinator)
        interaction.isEnabled = true
        view.addInteraction(interaction)
        updateUIView(view, context: context)
        return view
    }

    func updateUIView(_ view: UIImageView, context: Context) {
        context.coordinator.parent = self
        view.accessibilityLabel = AnyUIErrorText.text("גרירה של ", "Drag ") + title
        view.accessibilityHint = AnyUIErrorText.text("גרירה לתיקייה כדי להעביר את הפריט.",
                                                   "Drag into a folder to move this item.")
        view.accessibilityIdentifier = "any-native-hierarchy-drag-" + objectID
    }

    final class Coordinator: NSObject, UIDragInteractionDelegate {
        var parent: AnyNativeHierarchyDragHandle
        init(parent: AnyNativeHierarchyDragHandle) { self.parent = parent }

        func dragInteraction(_ interaction: UIDragInteraction,
                             itemsForBeginning session: any UIDragSession) -> [UIDragItem] {
            guard parent.canDrag() else { return [] }
            let payload = "pinkha-any-node|\(parent.session.workspace.spaceID)|\(parent.objectID)"
            let item = UIDragItem(itemProvider: NSItemProvider(object: payload as NSString))
            item.localObject = AnyHierarchyLocalDrag(session: parent.session, objectID: parent.objectID)
            return [item]
        }

        func dragInteraction(_ interaction: UIDragInteraction,
                             sessionAllowsMoveOperation session: any UIDragSession) -> Bool { true }

        func dragInteraction(_ interaction: UIDragInteraction,
                             sessionIsRestrictedToDraggingApplication session: any UIDragSession) -> Bool { true }
    }
}

/// UIKit owns the row drop surface directly. SwiftUI List's collection-view
/// drag/reorder delegate must not replace folder drops with a no-op insertion.
@MainActor
struct AnyNativeHierarchyDropRow<Content: View>: UIViewControllerRepresentable {
    let session: AnyApplicationSession
    let canDrop: @MainActor (String) -> Bool
    let performDrop: @MainActor (String) -> Void
    let content: Content

    init(session: AnyApplicationSession,
         canDrop: @escaping @MainActor (String) -> Bool,
         performDrop: @escaping @MainActor (String) -> Void,
         @ViewBuilder content: () -> Content) {
        self.session = session
        self.canDrop = canDrop
        self.performDrop = performDrop
        self.content = content()
    }

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    func makeUIViewController(context: Context) -> UIHostingController<Content> {
        let controller = UIHostingController(rootView: content)
        controller.view.backgroundColor = .clear
        controller.safeAreaRegions = []
        controller.sizingOptions = [.intrinsicContentSize]
        controller.view.addInteraction(UIDropInteraction(delegate: context.coordinator))
        return controller
    }

    func updateUIViewController(_ controller: UIHostingController<Content>, context: Context) {
        context.coordinator.parent = self
        controller.rootView = content
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiViewController: UIHostingController<Content>,
                      context: Context) -> CGSize? {
        guard let width = proposal.width, width > 0, width.isFinite else { return nil }
        return uiViewController.sizeThatFits(in: CGSize(width: width, height: .greatestFiniteMagnitude))
    }

    final class Coordinator: NSObject, UIDropInteractionDelegate {
        var parent: AnyNativeHierarchyDropRow
        init(parent: AnyNativeHierarchyDropRow) { self.parent = parent }

        private func accepted(_ session: any UIDropSession) -> AnyHierarchyLocalDrag? {
            guard session.localDragSession != nil, session.items.count == 1,
                  let value = session.items[0].localObject as? AnyHierarchyLocalDrag,
                  value.session === parent.session, parent.canDrop(value.objectID) else { return nil }
            return value
        }

        func dropInteraction(_ interaction: UIDropInteraction, canHandle session: any UIDropSession) -> Bool {
            accepted(session) != nil
        }

        func dropInteraction(_ interaction: UIDropInteraction,
                             sessionDidUpdate session: any UIDropSession) -> UIDropProposal {
            UIDropProposal(operation: accepted(session) == nil ? .forbidden : .move)
        }

        func dropInteraction(_ interaction: UIDropInteraction, performDrop session: any UIDropSession) {
            guard let value = accepted(session) else { return }
            // This only dispatches the existing native move. Its real readback
            // remains the sole authority that removes/reorders the visible row.
            parent.performDrop(value.objectID)
        }
    }
}
#endif
