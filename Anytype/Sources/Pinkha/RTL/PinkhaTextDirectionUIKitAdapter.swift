import NaturalLanguage
import PinkhaKit
import Services
import UIKit

struct PinkhaTextBlockWritingContext: Equatable, Hashable {
    let origin: PinkhaParagraphOrigin
    let persistedAlignment: PinkhaParagraphAlignment?
    let alignmentWasExplicit: Bool
    let blockId: String?
    let isTitle: Bool

    init(
        origin: PinkhaParagraphOrigin,
        persistedAlignment: PinkhaParagraphAlignment?,
        alignmentWasExplicit: Bool,
        blockId: String? = nil,
        isTitle: Bool = false
    ) {
        self.origin = origin
        self.persistedAlignment = persistedAlignment
        self.alignmentWasExplicit = alignmentWasExplicit
        self.blockId = blockId
        self.isTitle = isTitle
    }
}

@MainActor
enum PinkhaTextDirectionUIKitAdapter {
    private static let writingContexts = NSMapTable<UITextView, PinkhaWritingContextBox>.weakToStrongObjects()

    /// Builds presentation context for every Anytype document. Document identity, type,
    /// provenance, Pinkha registration and session-created status are deliberately absent.
    static func context(
        document: some BaseDocumentProtocol,
        info: BlockInformation,
        text _: String
    ) -> PinkhaTextBlockWritingContext? {
        let hostAlignment: LayoutAlignment
        if info.textContent?.contentType == .title, let details = document.details {
            hostAlignment = details.objectAlignValue
        } else {
            hostAlignment = info.horizontalAlignment
        }
        let isTitle = info.textContent?.contentType == .title

        if let sessionAlignment = PinkhaTextDirectionPersistence.sessionExplicitAlignment(
            blockId: info.id
        ) {
            return PinkhaTextBlockWritingContext(
                origin: .existingParagraph,
                persistedAlignment: sessionAlignment,
                alignmentWasExplicit: true,
                blockId: info.id,
                isTitle: isTitle
            )
        }

        switch marker(from: info.fields) {
        case let .explicit(alignment):
            return PinkhaTextBlockWritingContext(
                origin: .existingParagraph,
                persistedAlignment: alignment,
                alignmentWasExplicit: true,
                blockId: info.id,
                isTitle: isTitle
            )
        case .automatic:
            // Old automatic markers are historical defaults. The current application
            // language now owns the display default, and no migration write is generated.
            return PinkhaTextBlockWritingContext(
                origin: .existingParagraph,
                persistedAlignment: hostAlignment.pinkhaAlignment,
                alignmentWasExplicit: false,
                blockId: info.id,
                isTitle: isTitle
            )
        case nil:
            // Marker-less left/right values are unavoidably ambiguous. Treat them as old
            // defaults for reversible display adaptation; center/justify are preserved by
            // PinkhaWritingDirectionPolicy as unambiguous formatting choices.
            return PinkhaTextBlockWritingContext(
                origin: .ambiguousLegacyParagraph,
                persistedAlignment: hostAlignment.pinkhaAlignment,
                alignmentWasExplicit: false,
                blockId: info.id,
                isTitle: isTitle
            )
        }
    }

    /// Resolves the effective application-wide layout direction for this text view.
    /// Prefers container/ancestor attributes, then explicit view-level attributes, then inherited UIKit direction.
    static func effectiveInterfaceDirection(for textView: UITextView) -> PinkhaLayoutDirection {
        // The navigation container already receives the effective SwiftUI app layout direction.
        // The editor row inherits it once attached; never consult a last-used global window.
        var ancestor = textView.superview
        while let view = ancestor {
            switch view.semanticContentAttribute {
            case .forceRightToLeft: return .rightToLeft
            case .forceLeftToRight: return .leftToRight
            default: break
            }
            ancestor = view.superview
        }
        // Detached text views used by unit tests can retain an intentional explicit setting.
        switch textView.semanticContentAttribute {
        case .forceRightToLeft: return .rightToLeft
        case .forceLeftToRight: return .leftToRight
        default: break
        }
        return textView.effectiveUserInterfaceLayoutDirection == .rightToLeft
            ? .rightToLeft : .leftToRight
    }

    /// Applies native presentation alignment after the host styler, so TextKit computes
    /// glyphs, selection hit testing and the editable caret together. Paragraph alignment
    /// is a UIKit rendering attribute: the original AttributedTextConverter serializes
    /// only text/marks, and this path never calls a document action or editing delegate.
    /// Active IME composition is left untouched; empty rows receive typing defaults only.
    static func apply(
        context: PinkhaTextBlockWritingContext?,
        to textView: UITextView
    ) {
        if context == nil || (textView.textStorage.length == 0 && context?.blockId != writingContexts.object(forKey: textView)?.context.blockId) {
            PinkhaStage1AcceptanceDiagnostics.resetInsertionEvidence(in: textView)
        }
        if let context {
            writingContexts.setObject(PinkhaWritingContextBox(context, textView: textView), forKey: textView)
        } else {
            writingContexts.removeObject(forKey: textView)
        }
        guard let context, textView.markedTextRange == nil else { return }

        let interfaceDirection = effectiveInterfaceDirection(for: textView)
        let targetSemanticAttribute: UISemanticContentAttribute = interfaceDirection == .rightToLeft
            ? .forceRightToLeft
            : .forceLeftToRight
        if textView.semanticContentAttribute != targetSemanticAttribute {
            textView.semanticContentAttribute = targetSemanticAttribute
        }

        let decision = PinkhaWritingDirectionPolicy.resolve(
            PinkhaWritingDirectionInput(
                isEmpty: textView.text.isEmpty,
                interfaceDirection: interfaceDirection,
                detectedTextDirection: detectedDirection(
                    for: textView.text,
                    fallback: interfaceDirection
                ),
                persistedAlignment: context.persistedAlignment,
                alignmentWasExplicit: context.alignmentWasExplicit
            )
        )

        let alignment = decision.alignment.nsTextAlignment
        if !context.alignmentWasExplicit && alignment != .center && alignment != .justified {
            applyDisplayAlignment(alignment, decision: decision, to: textView)
        }

        if PinkhaStage1AcceptanceState.isEnabled, let blockId = context.blockId {
            let role = context.isTitle ? "title" : "body"
            textView.accessibilityIdentifier = "pinkha.stage1.\(role).\(blockId)"
            textView.accessibilityLabel = PinkhaStage1AcceptanceDiagnostics.textViewLabel(
                decision: decision,
                origin: context.origin,
                textView: textView
            )
        }
    }

    static func detectedDirection(
        for text: String,
        fallback: PinkhaLayoutDirection
    ) -> PinkhaLayoutDirection? {
        guard !text.isEmpty else { return nil }
        guard let language = NLLanguageRecognizer.dominantLanguage(for: text)?.rawValue else {
            return fallback
        }
        switch NSParagraphStyle.defaultWritingDirection(forLanguage: language) {
        case .rightToLeft: return .rightToLeft
        case .leftToRight: return .leftToRight
        case .natural: return fallback
        @unknown default: return fallback
        }
    }

    static func prepareForEditing(in textView: UITextView) {
        guard let context = writingContexts.object(forKey: textView)?.context else { return }
        if textView.textStorage.length == 0 {
            apply(context: context, to: textView)
        } else if PinkhaStage1AcceptanceState.isEnabled {
            let decision = PinkhaWritingDirectionPolicy.resolve(
                PinkhaWritingDirectionInput(
                    isEmpty: false,
                    interfaceDirection: effectiveInterfaceDirection(for: textView),
                    detectedTextDirection: detectedDirection(
                        for: textView.text,
                        fallback: effectiveInterfaceDirection(for: textView)
                    ),
                    persistedAlignment: context.persistedAlignment,
                    alignmentWasExplicit: context.alignmentWasExplicit
                )
            )
            textView.accessibilityLabel = PinkhaStage1AcceptanceDiagnostics.textViewLabel(
                decision: decision,
                origin: context.origin,
                textView: textView
            )
        }
    }

    /// Configuration can occur off-window, before the native row inherits app direction.
    /// Reapply the cached presentation context at attachment, before original focus runs.
    static func refreshAfterAttachment(in textView: UITextView) {
        guard let context = writingContexts.object(forKey: textView)?.context else { return }
        apply(context: context, to: textView)
    }

    /// Read-only evidence, deferred until UIKit has finished focus/selection restoration.
    /// This never applies styles, changes selection or participates in editing delegates.
    static func recordEditingDiagnostics(in textView: UITextView) {
        guard PinkhaStage1AcceptanceState.isEnabled,
              let context = writingContexts.object(forKey: textView)?.context else { return }
        let direction = effectiveInterfaceDirection(for: textView)
        let decision = PinkhaWritingDirectionPolicy.resolve(PinkhaWritingDirectionInput(
            isEmpty: textView.text.isEmpty,
            interfaceDirection: direction,
            detectedTextDirection: detectedDirection(for: textView.text, fallback: direction),
            persistedAlignment: context.persistedAlignment,
            alignmentWasExplicit: context.alignmentWasExplicit
        ))
        textView.accessibilityLabel = PinkhaStage1AcceptanceDiagnostics.textViewLabel(
            decision: decision, origin: context.origin, textView: textView
        )
    }

    static func marker(from fields: BlockFields) -> PinkhaTextDirectionMarker? {
        guard let value = fields[PinkhaSchemaRoles.blockTextDirectionField],
              case let .stringValue(storedValue) = value.kind else {
            return nil
        }
        return PinkhaTextDirectionMarker(storedValue: storedValue)
    }

    static func visualAlignment(for textView: UITextView) -> NSTextAlignment {
        textView.textAlignment
    }

    private static func applyDisplayAlignment(
        _ alignment: NSTextAlignment,
        decision: PinkhaWritingDirectionDecision,
        to textView: UITextView
    ) {
        // Use the same native property as TextBlockTextViewStyler. Repositioning only a
        // layout-manager cache leaves UITextView's actual input geometry on the old side.
        // This setter changes presentation paragraph attributes, never stored alignment.
        if textView.textAlignment != alignment {
            textView.textAlignment = alignment
        }

        if textView.textStorage.length == 0 {
            var typingAttributes = textView.typingAttributes
            let paragraphStyle = (
                typingAttributes[.paragraphStyle] as? NSParagraphStyle
            )?.mutableCopy() as? NSMutableParagraphStyle ?? NSMutableParagraphStyle()
            paragraphStyle.alignment = alignment
            paragraphStyle.baseWritingDirection = decision.baseWritingDirection == .rightToLeft
                ? .rightToLeft
                : .leftToRight
            typingAttributes[.paragraphStyle] = paragraphStyle
            textView.typingAttributes = typingAttributes
        }

        // TextViewWithPlaceholder owns a direct UILabel child; it is not document storage.
        textView.subviews.compactMap { $0 as? UILabel }.forEach {
            $0.textAlignment = alignment
        }
    }
}

private final class PinkhaWritingContextBox {
    let context: PinkhaTextBlockWritingContext
    private var diagnosticObservers = [NSObjectProtocol]()

    @MainActor
    init(_ context: PinkhaTextBlockWritingContext, textView: UITextView) {
        self.context = context
        guard PinkhaStage1AcceptanceState.isEnabled else { return }
        for name in [UITextView.textDidBeginEditingNotification, UITextView.textDidChangeNotification, UITextView.textDidEndEditingNotification] {
            diagnosticObservers.append(NotificationCenter.default.addObserver(
                forName: name, object: textView, queue: .main
            ) { [weak textView] _ in
                DispatchQueue.main.async { [weak textView] in
                    guard let textView else { return }
                    PinkhaTextDirectionUIKitAdapter.recordEditingDiagnostics(in: textView)
                }
            })
        }
    }

    deinit {
        for observer in diagnosticObservers { NotificationCenter.default.removeObserver(observer) }
    }
}

private extension LayoutAlignment {
    var pinkhaAlignment: PinkhaParagraphAlignment {
        switch self {
        case .left: .left
        case .center: .center
        case .right: .right
        case .justify: .justified
        case .UNRECOGNIZED: .left
        }
    }
}

private extension PinkhaParagraphAlignment {
    var nsTextAlignment: NSTextAlignment {
        switch self {
        case .left: .left
        case .center: .center
        case .right: .right
        case .justified: .justified
        case .natural: .natural
        }
    }
}

private extension UIUserInterfaceLayoutDirection {
    var pinkhaDirection: PinkhaLayoutDirection {
        self == .rightToLeft ? .rightToLeft : .leftToRight
    }
}
