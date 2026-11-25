import UIKit
import Combine
import Services
import AnytypeCore


final class TextBlockContentView: UIView, BlockContentView, DynamicHeightView, FirstResponder {
    var isFirstResponderValueChangeHandler: ((Bool) -> Void)?
    
    // MARK: - DynamicHeightView
    var heightDidChanged: (() -> Void)?
    
    // MARK: - Views
    private let contentView = UIView()
    private let textContainerView = UIView()
    private(set) lazy var textView = CustomTextView()
    private(set) lazy var createEmptyBlockButton = EmptyToggleButtonBuilder.create { [weak self] in
        self?.actions?.createEmptyBlock()
    }
    private lazy var textBlockLeadingView = TextBlockLeadingView()
    private(set) lazy var torahAccessoryButton: TorahBlockAccessoryButton = {
        let button = TorahBlockAccessoryButton()
        button.addTarget(self, action: #selector(openTorahAccessory), for: .touchUpInside)
        return button
    }()
    
    private let mainStackView: UIStackView = makeMainStackView()
    
    private var topContentConstraint: NSLayoutConstraint?
    private var bottomContentnConstraint: NSLayoutConstraint?
    private var contentSpacingConstraint: NSLayoutConstraint?
    private var textTrailingConstraint: NSLayoutConstraint?
    private var textTrailingToTorahAccessoryConstraint: NSLayoutConstraint?
    private var torahAccessoryBottomConstraint: NSLayoutConstraint?
    private var focusSubscription: AnyCancellable?
    private var resetSubscription: AnyCancellable?
    private var configuredBlockId: String?
    var pinkhaMiniAppsBlockID: String? { configuredBlockId }
    private var focusContext: EditorCursorManager?
    private var pendingFocus: (id: UUID, position: BlockFocusPosition, requestId: UUID?)?
    private var focusLifetimeId = UUID()
    private var focusReadinessSubscriptions = [AnyCancellable]()
    private var torahAccessoryAction: (() -> Void)?
    
    private(set) var actions: TextBlockContentConfiguration.Actions?
    
    override init(frame: CGRect) {
        super.init(frame: frame)
        
        setupLayout()
    }
    
    required init?(coder: NSCoder) {
        super.init(coder: coder)
        
        setupLayout()
    }
    
    func update(with configuration: TextBlockContentConfiguration) {
        actions = configuration.actions
        applyNewConfiguration(configuration: configuration)
    }

    override func willMove(toWindow newWindow: UIWindow?) {
        if window != nil, window !== newWindow {
            cancelPendingFocus()
        }
        super.willMove(toWindow: newWindow)
    }

    override func didMoveToWindow() {
        super.didMoveToWindow()
        guard window != nil else { return }
        PinkhaTextDirectionUIKitAdapter.refreshAfterAttachment(in: textView.textView)
        observeFocusReadiness()
        schedulePendingFocus()
    }
    
    func update(with state: UICellConfigurationState) {
        textView.textView.isLockedForEditing = state.isLocked
        createEmptyBlockButton.isEnabled = !state.isLocked
        textBlockLeadingView.checkboxView?.isUserInteractionEnabled = !state.isLocked
        textBlockLeadingView.calloutIconView?.isUserInteractionEnabled = !state.isLocked
        textView.textView.isUserInteractionEnabled = state.isEditing
        if state.isLocked || !state.isEditing {
            cancelPendingFocus(observation: .cancelledState)
        }
    }

    func updateTorahAccessory(_ configuration: TorahBlockAccessoryConfiguration?) {
        torahAccessoryAction = configuration?.action
        torahAccessoryButton.isHidden = configuration == nil
        torahAccessoryButton.accessibilityLabel = configuration?.accessibilityLabel
        torahAccessoryButton.accessibilityValue = configuration?.accessibilityValue
        torahAccessoryButton.accessibilityIdentifier = configuration?.accessibilityIdentifier

        if configuration == nil {
            textTrailingToTorahAccessoryConstraint?.isActive = false
            torahAccessoryBottomConstraint?.isActive = false
            textTrailingConstraint?.isActive = true
        } else {
            textTrailingConstraint?.isActive = false
            textTrailingToTorahAccessoryConstraint?.isActive = true
            torahAccessoryBottomConstraint?.isActive = true
        }
        setNeedsLayout()
    }
    
    // MARK: - Setup views
    
    private func setupLayout() {
        textContainerView.addSubview(textBlockLeadingView) {
            $0.pinToSuperview(excluding: [.right])
        }
        textContainerView.addSubview(textView) {
            $0.pinToSuperview(excluding: [.left, .right])
            // For textBlockLeadingView is visible
            contentSpacingConstraint = $0.leading.equal(to: textBlockLeadingView.trailingAnchor, priority: .required)
            // For textBlockLeadingView is hidden
            $0.leading.equal(to: textContainerView.leadingAnchor, priority: .defaultHigh)
        }

        textTrailingConstraint = textView.trailingAnchor.constraint(equalTo: textContainerView.trailingAnchor)
        textTrailingConstraint?.isActive = true

        textContainerView.addSubview(torahAccessoryButton) {
            $0.top.equal(to: textContainerView.topAnchor)
            $0.trailing.equal(to: textContainerView.trailingAnchor)
            $0.size(TorahBlockAccessoryButton.hitTargetSize)
        }
        textTrailingToTorahAccessoryConstraint = textView.trailingAnchor.constraint(
            equalTo: torahAccessoryButton.leadingAnchor
        )
        torahAccessoryBottomConstraint = torahAccessoryButton.bottomAnchor.constraint(
            lessThanOrEqualTo: textContainerView.bottomAnchor
        )
        torahAccessoryButton.isHidden = true
            
        contentView.addSubview(textContainerView) {
            topContentConstraint = $0.top.equal(to: contentView.topAnchor)
            bottomContentnConstraint = $0.bottom.greaterThanOrEqual(to: contentView.bottomAnchor)
            $0.leading.equal(to: contentView.leadingAnchor)
            $0.trailing.equal(to: contentView.trailingAnchor)
        }
        
        createEmptyBlockButton.layoutUsing.anchors {
            $0.height.equal(to: 26)
        }
        
        mainStackView.addArrangedSubview(contentView)
        contentView.widthAnchor.constraint(equalTo: mainStackView.widthAnchor).isActive = true
        
        mainStackView.addArrangedSubview(createEmptyBlockButton)
        
        addSubview(mainStackView) {
            $0.pinToSuperview()
        }
    }
    
    // MARK: - Apply configuration
    
    /// Synchronous first-responder grab for the Enter-created row focus handoff. Runs right
    /// after the apply that inserted this cell — outside the dequeue pass, where a synchronous
    /// becomeFirstResponder is unsafe (see applyNewConfiguration).
    func takeFocus(at position: BlockFocusPosition) {
        requestFocus(position, requestId: focusContext?.registerFocusRequest(), deferred: false)
    }

    func didTakeNativeFocus() {
        recordFocus(.nativeBegan, requestId: focusContext?.focusRequestId)
        cancelPendingFocus(observation: nil)
        focusContext?.registerFocusRequest()
    }

    private func requestFocus(_ position: BlockFocusPosition, requestId: UUID?, deferred: Bool) {
        guard canReceiveFocus, let pendingId = retainFocus(position, requestId: requestId) else { return }
        if deferred {
            schedulePendingFocus()
        } else {
            applyPendingFocus(id: pendingId)
        }
    }

    private func retainFocus(_ position: BlockFocusPosition, requestId: UUID?) -> UUID? {
        guard configuredBlockId != nil else { return nil }
        if let focusContext {
            guard let requestId, focusContext.focusRequestId == requestId else { return nil }
        }
        let pendingId = UUID()
        focusLifetimeId = pendingId
        pendingFocus = (pendingId, position, requestId)
        recordFocus(.retained, requestId: requestId)
        observeFocusReadiness()
        return pendingId
    }

    private var canReceiveFocus: Bool {
        !textView.textView.isLockedForEditing && textView.textView.isUserInteractionEnabled && textView.textView.isEditable
    }

    private func schedulePendingFocus() {
        guard window != nil, let pendingId = pendingFocus?.id else { return }
        recordFocus(.scheduled, requestId: pendingFocus?.requestId)
        // Attachment can occur during dequeue too; delegate side effects must wait for its return.
        DispatchQueue.main.async { [weak self] in
            self?.applyPendingFocus(id: pendingId)
        }
    }

    private func cancelPendingFocus(observation: PinkhaStage1AcceptanceDiagnostics.FocusEvent? = .cancelledLifetime) {
        if let pendingFocus, let observation {
            recordFocus(observation, requestId: pendingFocus.requestId)
        }
        focusLifetimeId = UUID()
        pendingFocus = nil
        focusReadinessSubscriptions.removeAll()
    }

    private func observeFocusReadiness() {
        focusReadinessSubscriptions.removeAll()
        guard pendingFocus != nil, let window else { return }
        NotificationCenter.default.publisher(for: UIWindow.didBecomeKeyNotification, object: window)
            .sink { [weak self] _ in self?.schedulePendingFocus() }
            .store(in: &focusReadinessSubscriptions)
        if let scene = window.windowScene {
            NotificationCenter.default.publisher(for: UIScene.didActivateNotification, object: scene)
                .sink { [weak self] _ in self?.schedulePendingFocus() }
                .store(in: &focusReadinessSubscriptions)
        }
    }

    private func applyPendingFocus(id: UUID) {
        guard let pendingFocus, pendingFocus.id == id, focusLifetimeId == id else { return }
        if let focusContext, focusContext.focusRequestId != pendingFocus.requestId {
            cancelPendingFocus(observation: .cancelledSuperseded)
            return
        }
        guard canReceiveFocus else {
            cancelPendingFocus(observation: .cancelledState)
            return
        }
        guard let window, textView.textView.window === window, window.isKeyWindow,
              window.windowScene?.activationState == .foregroundActive else { return }
        recordFocus(.nativeAttempted, requestId: pendingFocus.requestId)
        // Consume before UIKit delegates run, so its successful begin-editing cannot replay a caret.
        self.pendingFocus = nil
        focusReadinessSubscriptions.removeAll()
        recordFocus(.consumed, requestId: pendingFocus.requestId)
        textView.textView.setFocus(pendingFocus.position)
        recordFocus(textView.textView.isFirstResponder ? .nativeAcquired : .nativeRefused,
                    requestId: pendingFocus.requestId)
        if !textView.textView.isFirstResponder, focusLifetimeId == id,
           focusContext?.focusRequestId == pendingFocus.requestId {
            // A native refusal is not success. Retain only this still-current request, and
            // wait for attachment/key/activation events; never loop or add a timed retry.
            self.pendingFocus = pendingFocus
            observeFocusReadiness()
        }
    }

    private func recordFocus(_ event: PinkhaStage1AcceptanceDiagnostics.FocusEvent, requestId: UUID?) {
        PinkhaStage1AcceptanceDiagnostics.recordFocus(
            event, in: textView.textView, requestID: requestId,
            ownerID: focusContext?.focusRequestId,
            ownerMatches: focusContext == nil || focusContext?.focusRequestId == requestId
        )
    }

    private func applyNewConfiguration(configuration: TextBlockContentConfiguration) {
        if configuredBlockId != configuration.blockId || focusContext !== configuration.focusContext {
            cancelPendingFocus()
        }
        configuredBlockId = configuration.blockId
        #if DEBUG && targetEnvironment(simulator)
        // Passive identity on the real original UITextView. No content or edit
        // behavior changes; reused views clear this qualification-only identity.
        if ProcessInfo.processInfo.environment["OTZARIA_ORIGINAL_EDITOR_QUALIFICATION"] == "owned-local-only" {
            let role: String
            switch configuration.content.contentType {
            case .text: role = "text"
            case .title: role = "title"
            default: role = "other"
            }
            textView.textView.accessibilityIdentifier = "original-editor-block-" + role + ":" + configuration.blockId
        } else {
            textView.textView.accessibilityIdentifier = nil
        }
        #endif
        focusContext = configuration.focusContext
        applyTextStorage(configuration.attributedString)

        textBlockLeadingView.update(blockId: configuration.blockId, style: TextBlockLeadingStyle(with: configuration))
        PinkhaTextBlockLeadingMarkerAdapter.applyNumberAlignment(
            context: configuration.pinkhaWritingContext,
            content: configuration.content,
            to: textBlockLeadingView
        )
    
        let restrictions = BlockRestrictionsBuilder.build(textContentType: configuration.content.contentType)
        TextBlockTextViewStyler.applyStyle(textView: textView, configuration: configuration, restrictions: restrictions)
        PinkhaTextDirectionUIKitAdapter.apply(
            context: configuration.pinkhaWritingContext,
            to: textView.textView
        )
        
        updateAllConstraint(configuration: configuration)
        textView.delegate = self
        
        let contentType = configuration.content.contentType
        let isToggleType = contentType == .toggle || contentType.isToggleHeader
        let displayPlaceholder = isToggleType && configuration.shouldDisplayPlaceholder
        UIView.performWithoutAnimation {
            createEmptyBlockButton.isHidden = !displayPlaceholder
            mainStackView.setNeedsLayout()
        }
        
        focusSubscription = configuration
            .focusPublisher
            .sink { [weak self] focus in
                guard let self else { return }
                // Editor focus senders are MainActor-bound. Capture ownership now, before the UI deferral.
                recordFocus(.publisherRequested, requestId: focusContext?.focusRequestId)
                requestFocus(focus, requestId: focusContext?.focusRequestId, deferred: true)
            }
        
        resetSubscription = configuration.resetPublisher.sink { [weak self] configuration in
            configuration.map {
                self?.applyNewConfiguration(configuration: $0)
            }
        }
        
        if let position = configuration.initialBlockFocusPosition {
            recordFocus(.initialRequested, requestId: configuration.initialFocusRequestId)
            // EditorContentView applies the cell state after its content configuration. Keep the
            // new request through that ordering; the state callback and execution both enforce it.
            if retainFocus(position, requestId: configuration.initialFocusRequestId) != nil {
                schedulePendingFocus()
            }
        }
    }

    /// Applies `incoming` to the text storage without needlessly rebuilding the keyboard's
    /// input session. Reconfiguring the cell being typed in (the fork-time identity-rebind
    /// refresh, a remote echo of the local text) with `setAttributedString` resets
    /// autocorrect's word buffer even when nothing changed, so:
    /// - identical characters, identical attributes: no write at all;
    /// - identical characters, different attributes: attributes are applied in place — an
    ///   attribute edit does not touch the word buffer. Characters are compared by `string`,
    ///   not `isEqual(to:)`: UIKit decorates live text with private attributes (e.g.
    ///   NSOriginalFont on font substitution), and a spuriously unequal comparison would
    ///   silently reinstate the session reset;
    /// - different characters: full write — except during an IME composition when `incoming`
    ///   is a stale prefix of the live text (the view is legitimately ahead by the uncommitted
    ///   marked text; the commit syncs view → model, so nothing is lost by skipping). A
    ///   genuinely different non-empty text (undo, a remote edit) still takes the write:
    ///   losing the composition is the lesser damage.
    private func applyTextStorage(_ incoming: NSAttributedString) {
        let liveTextView = textView.textView
        guard liveTextView.isFirstResponder else {
            liveTextView.textStorage.setAttributedString(incoming)
            return
        }
        let liveText: NSAttributedString = liveTextView.attributedText ?? NSAttributedString()
        if liveTextView.markedTextRange != nil {
            guard incoming.string.isNotEmpty, liveText.string.hasPrefix(incoming.string) else {
                setAttributedTextKeepingCaret(incoming, in: liveTextView)
                return
            }
            return
        }
        guard liveText.string == incoming.string else {
            setAttributedTextKeepingCaret(incoming, in: liveTextView)
            return
        }
        guard !liveText.isEqual(to: incoming) else { return }
        let storage = liveTextView.textStorage
        storage.beginEditing()
        incoming.enumerateAttributes(in: NSRange(location: 0, length: incoming.length), options: []) { attributes, range, _ in
            storage.setAttributes(attributes, range: range)
        }
        storage.endEditing()
    }

    /// Replacing the whole storage collapses the selection to the start of the block. While the
    /// view is first responder that reads as the caret jumping to the beginning — a paste is
    /// the common case: its response places the caret after the pasted text, then the middleware
    /// echo reconfigures the cell and the write drops it. Reinstating the offset (clamped to the
    /// new text) keeps the caret where the edit that caused the write left it.
    private func setAttributedTextKeepingCaret(_ incoming: NSAttributedString, in textView: UITextView) {
        let caret = textView.selectedRange
        textView.textStorage.setAttributedString(incoming)
        let location = min(caret.location, incoming.length)
        let length = min(caret.length, incoming.length - location)
        textView.selectedRange = NSRange(location: location, length: length)
    }

    private func updateAllConstraint(configuration: TextBlockContentConfiguration) {
        let contentInset = TextBlockLayout.contentInset(textBlockStyle: configuration.content.contentType)
        
        topContentConstraint?.constant = contentInset.top
        bottomContentnConstraint?.constant = -contentInset.bottom
        
        if textBlockLeadingView.isHidden {
            contentSpacingConstraint?.constant = 0
        } else if configuration.content.contentType == .title, configuration.isCheckable {
            contentSpacingConstraint?.constant = 8
        } else {
            contentSpacingConstraint?.constant = 4
        }
    }

    @objc private func openTorahAccessory() {
        torahAccessoryAction?()
    }
}

struct TorahBlockAccessoryConfiguration {
    let accessibilityLabel: String
    let accessibilityValue: String
    let accessibilityIdentifier: String
    let action: () -> Void
}

/// A block-local source ornament. Its visible glyph follows the native inline-icon scale while
/// the transparent control keeps the 44pt accessibility target. Unlike `UICellAccessory`, its
/// reserved width is deterministic and belongs to the text block's own layout.
final class TorahBlockAccessoryButton: UIButton {
    static let hitTargetSize = CGSize(width: 44, height: 44)
    static let visibleIconSize = CGSize(width: 20, height: 20)
    private(set) lazy var iconView = UIImageView(
        image: UIImage(asset: .CustomIcons.book)?.withRenderingMode(.alwaysTemplate)
    )

    init() {
        super.init(frame: .zero)

        tintColor = .Control.secondary
        backgroundColor = .clear
        iconView.tintColor = .Control.secondary
        iconView.contentMode = .scaleAspectFit
        iconView.isUserInteractionEnabled = false
        addSubview(iconView) {
            $0.size(Self.visibleIconSize)
            $0.center(in: self)
        }
        accessibilityTraits = .button
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override var intrinsicContentSize: CGSize { Self.hitTargetSize }

    override var isHighlighted: Bool {
        didSet {
            iconView.alpha = isHighlighted ? 0.5 : 1
        }
    }
}

private extension TextBlockContentView {
    
    static func makeMainStackView() -> UIStackView {
        let mainStackView = UIStackView()
        mainStackView.axis = .vertical
        mainStackView.alignment = .fill
        return mainStackView
    }
}
