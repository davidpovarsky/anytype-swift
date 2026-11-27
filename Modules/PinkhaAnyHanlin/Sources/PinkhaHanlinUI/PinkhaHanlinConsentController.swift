#if canImport(UIKit)
import PinkhaHanlinCore
import UIKit

/// Anytype owns this small native permission sheet and its view lifecycle.
/// No system controller hierarchy is modified, and no model can supply a choice.
@MainActor
public final class PinkhaHanlinConsentController: UIViewController {
    public enum Purpose: String {
        case readContext = "read-context"
        case createPage = "create-page"
        case saveMessage = "save-message"
    }

    public let purpose: Purpose
    private let explanation: String
    private let allowTitle: String
    private let cancelTitle: String
    private let decision: PinkhaHanlinReadConsentDecision
    private let validate: @MainActor () throws -> Void

    public init(purpose: Purpose, title: String, explanation: String, allowTitle: String, cancelTitle: String,
         decision: PinkhaHanlinReadConsentDecision, validate: @escaping @MainActor () throws -> Void) {
        self.purpose = purpose
        self.explanation = explanation
        self.allowTitle = allowTitle
        self.cancelTitle = cancelTitle
        self.decision = decision
        self.validate = validate
        super.init(nibName: nil, bundle: nil)
        self.title = title
        modalPresentationStyle = .formSheet
        // Match the explicit Cancel/Allow behavior of the previous alert. A
        // cancelled swipe must not terminate a decision while leaving its UI.
        isModalInPresentation = true
        preferredContentSize = CGSize(width: 440, height: 420)
        sheetPresentationController?.detents = [.medium(), .large()]
        sheetPresentationController?.prefersGrabberVisible = false
    }

    @available(*, unavailable)
    public required init?(coder: NSCoder) { return nil }

    public override func viewDidLoad() {
        super.viewDidLoad()
        let identifier = "pinkha.hanlin.consent." + purpose.rawValue
        view.backgroundColor = .systemBackground
        view.accessibilityIdentifier = identifier
        view.accessibilityViewIsModal = true
        view.shouldGroupAccessibilityChildren = true

        let heading = UILabel()
        heading.text = title
        heading.font = .preferredFont(forTextStyle: .title2)
        heading.adjustsFontForContentSizeCategory = true
        heading.numberOfLines = 0
        heading.accessibilityTraits.insert(.header)
        heading.accessibilityIdentifier = identifier + ".title"
        let message = UILabel()
        message.text = explanation
        message.font = .preferredFont(forTextStyle: .body)
        message.adjustsFontForContentSizeCategory = true
        message.numberOfLines = 0
        message.accessibilityIdentifier = identifier + ".explanation"

        let allow = UIButton(type: .system)
        var allowConfiguration = UIButton.Configuration.filled()
        allowConfiguration.title = allowTitle
        allow.configuration = allowConfiguration
        allow.titleLabel?.adjustsFontForContentSizeCategory = true
        allow.titleLabel?.numberOfLines = 0
        allow.accessibilityIdentifier = identifier + ".allow"
        allow.addTarget(self, action: #selector(allowPressed), for: .touchUpInside)
        let cancel = UIButton(type: .system)
        var cancelConfiguration = UIButton.Configuration.plain()
        cancelConfiguration.title = cancelTitle
        cancel.configuration = cancelConfiguration
        cancel.titleLabel?.adjustsFontForContentSizeCategory = true
        cancel.accessibilityIdentifier = identifier + ".cancel"
        cancel.addTarget(self, action: #selector(cancelPressed), for: .touchUpInside)

        // A complete message may be 64 KiB. Keep its exact text scrollable and
        // both native decisions visible; reviewing it must not hide Cancel.
        let fixedDecisions = purpose == .saveMessage
        let stack = UIStackView(arrangedSubviews: fixedDecisions ? [heading, message] : [heading, message, allow, cancel])
        stack.axis = .vertical
        stack.spacing = 20
        stack.translatesAutoresizingMaskIntoConstraints = false
        let scroll = UIScrollView()
        scroll.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(scroll)
        scroll.addSubview(stack)
        var constraints = [
            scroll.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor),
            scroll.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor),
            scroll.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            stack.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor, constant: -24),
            stack.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor, constant: 24),
            stack.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor, constant: -24),
            stack.widthAnchor.constraint(equalTo: scroll.frameLayoutGuide.widthAnchor, constant: -48),
            allow.heightAnchor.constraint(greaterThanOrEqualToConstant: 44),
            cancel.heightAnchor.constraint(greaterThanOrEqualToConstant: 44)
        ]
        if fixedDecisions {
            let decisions = UIStackView(arrangedSubviews: [allow, cancel])
            decisions.axis = .vertical
            decisions.spacing = 12
            decisions.translatesAutoresizingMaskIntoConstraints = false
            view.addSubview(decisions)
            constraints += [
                decisions.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 24),
                decisions.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -24),
                decisions.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -24),
                scroll.bottomAnchor.constraint(equalTo: decisions.topAnchor, constant: -16)
            ]
        } else {
            constraints.append(scroll.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor))
        }
        NSLayoutConstraint.activate(constraints)
    }

    @objc private func allowPressed() {
        guard decision.isPending else { return }
        // Resolve while this actual control still owns the pending request.
        // A cancelled/stale owner cannot become authorized by a queued tap.
        decision.resolveAllow(validating: validate)
        dismiss(animated: true)
    }

    @objc private func cancelPressed() {
        decision.resolve(false)
        dismiss(animated: true)
    }

    public override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        // This also covers child-only programmatic dismissal while Chat stays
        // mounted. An already completed Allow is not overwritten.
        decision.resolve(false)
    }

    public override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        decision.resolve(false)
    }
}

#endif
