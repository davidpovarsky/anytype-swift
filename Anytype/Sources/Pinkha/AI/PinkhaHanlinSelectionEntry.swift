import SwiftUI
import UIKit
import Factory

extension EnvironmentValues {
    // Injected on the actual SpaceHub editor destination, including across its
    // separate UIHostingController root. No global coordinator lookup.
    @Entry var pinkhaHanlinRouteOwner: SpaceHubCoordinatorViewModel? = nil
}

/// Selection hides Home's bottom panel. Keep the native Done action and add a
/// direct entry without switching editing mode or clearing selected block IDs.
@MainActor
final class PinkhaHanlinSelectionControls: UIStackView {
    private let hanlinButton: UIButton
    private let miniAppsButton: UIButton

    init(doneButton: UIButton, onOpen: @escaping () -> Void, onMiniApps: @escaping () -> Void = {}) {
        miniAppsButton = PinkhaMiniAppsEntry.button(action: onMiniApps)
        var configuration = UIButton.Configuration.glassIOS26()
        configuration.image = UIImage(systemName: "sparkles")
        configuration.baseForegroundColor = .Control.primary
        let button = UIButton(configuration: configuration)
        button.accessibilityLabel = PinkhaHanlinStrings.title
        button.accessibilityIdentifier = "pinkha.hanlin.open.selection"
        button.addAction(UIAction { _ in onOpen() }, for: .touchUpInside)
        button.isHidden = true
        hanlinButton = button
        super.init(frame: .zero)
        axis = .horizontal
        alignment = .center
        spacing = EditorNavigationBarEditingControls.spacing
        addArrangedSubview(button)
        addArrangedSubview(miniAppsButton)
        addArrangedSubview(doneButton)
        // A hidden arranged view collapses to zero width; retain that behavior.
        let width = button.widthAnchor.constraint(equalToConstant: 44)
        width.priority = .defaultHigh
        NSLayoutConstraint.activate([width, button.heightAnchor.constraint(equalToConstant: 44)])
    }

    @available(*, unavailable)
    required init(coder: NSCoder) { fatalError("unavailable initializer") }

    func setAvailable(_ available: Bool) {
        hanlinButton.isHidden = !available
    }

    func setSelectionPresent(_ present: Bool) {
        hanlinButton.isEnabled = present
        miniAppsButton.isEnabled = present
    }
}

@MainActor
enum PinkhaHanlinSelectionEntry {
    static func open(editor: EditorPageController, routeOwner: SpaceHubCoordinatorViewModel) {
        guard let scene = editor.viewIfLoaded?.window?.windowScene,
              scene.activationState == .foregroundActive,
              PinkhaHanlinNativeAccess.isMounted(editor, in: scene),
              let model = editor.viewModel else { return }
        switch model.blocksStateManager.editingState {
        case .selecting(let blocks, _), .simpleTablesSelection(_, let blocks, _):
            guard !blocks.isEmpty else { return }
        default:
            return
        }
        do {
            let presentation = try Container.shared.pinkhaHanlinPresentationBuilder().make(
                presenter: editor, routeOwner: routeOwner, conversationID: UUID())
            let controller = PinkhaHanlinChatController(presentation: presentation)
            editor.present(controller, animated: true) {
                if controller.viewIfLoaded?.window == nil { presentation.invalidate() }
            }
        } catch {
            let alert = UIAlertController(title: PinkhaHanlinStrings.title,
                message: PinkhaHanlinStrings.openFailed, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: PinkhaHanlinStrings.close, style: .cancel))
            editor.present(alert, animated: true)
        }
    }
}
