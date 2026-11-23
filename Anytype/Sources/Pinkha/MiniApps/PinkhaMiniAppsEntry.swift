import UIKit

@MainActor
enum PinkhaMiniAppsEntry {
    static func button(action: @escaping () -> Void) -> UIButton {
        var configuration = UIButton.Configuration.glassIOS26()
        configuration.image = UIImage(systemName: "square.grid.2x2")
        configuration.baseForegroundColor = .Control.primary
        let button = UIButton(configuration: configuration)
        button.accessibilityLabel = PinkhaMiniAppsStrings.title
        button.accessibilityIdentifier = "pinkha.miniapps.open"
        button.addAction(UIAction { _ in action() }, for: .touchUpInside)
        button.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            button.widthAnchor.constraint(equalToConstant: 44),
            button.heightAnchor.constraint(equalToConstant: 44)
        ])
        return button
    }

    static func selectionAction(textView: UITextView, range: NSRange) -> UIAction? {
        var responder: UIResponder? = textView
        while let current = responder {
            if let editor = current as? EditorPageController {
                return UIAction(title: PinkhaMiniAppsStrings.title,
                    image: UIImage(systemName: "square.grid.2x2"),
                    identifier: .init("pinkha.miniapps.selection")) { [weak editor] _ in
                    guard let editor else { return }
                    PinkhaMiniAppsCoordinator.shared.present(editor: editor, range: range)
                }
            }
            responder = current.next
        }
        return nil
    }
}
