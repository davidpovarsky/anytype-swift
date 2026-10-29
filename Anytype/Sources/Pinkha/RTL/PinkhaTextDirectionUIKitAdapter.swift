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
    private static let layoutDelegates = NSMapTable<UITextView, PinkhaTextLayoutDelegate>.weakToStrongObjects()

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

    /// Applies display-only defaults. Existing text is aligned by line-fragment geometry, not
    /// paragraph attributes, so a language/layout refresh cannot enter host text-change
    /// callbacks or create document mutations. An empty editor receives only a typing default
    /// (plus its non-document placeholder alignment) so the insertion caret starts on the
    /// application-language side without rewriting text storage.
    static func apply(
        context: PinkhaTextBlockWritingContext?,
        to textView: UITextView
    ) {
        guard let context, textView.markedTextRange == nil else { return }

        let interfaceDirection = textView.effectiveUserInterfaceLayoutDirection.pinkhaDirection
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
        if context.alignmentWasExplicit || alignment == .center || alignment == .justified {
            removeDisplayAlignment(from: textView)
        } else {
            applyDisplayAlignment(alignment, to: textView)
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

    static func marker(from fields: BlockFields) -> PinkhaTextDirectionMarker? {
        guard let value = fields[PinkhaSchemaRoles.blockTextDirectionField],
              case let .stringValue(storedValue) = value.kind else {
            return nil
        }
        return PinkhaTextDirectionMarker(storedValue: storedValue)
    }

    static func visualAlignment(for textView: UITextView) -> NSTextAlignment {
        layoutDelegates.object(forKey: textView)?.alignment ?? textView.textAlignment
    }

    private static func applyDisplayAlignment(
        _ alignment: NSTextAlignment,
        to textView: UITextView
    ) {
        let layoutManager = textView.layoutManager
        let layoutDelegate: PinkhaTextLayoutDelegate
        if let existing = layoutDelegates.object(forKey: textView),
           layoutManager.delegate === existing {
            layoutDelegate = existing
        } else {
            // The Anytype editor does not install an NSLayoutManager delegate. Do not displace
            // an unexpected host delegate: that would trade directionality for lost behavior.
            guard layoutManager.delegate == nil else { return }
            layoutDelegate = PinkhaTextLayoutDelegate()
            layoutManager.delegate = layoutDelegate
            layoutDelegates.setObject(layoutDelegate, forKey: textView)
        }

        layoutDelegate.alignment = alignment

        if textView.textStorage.length == 0 {
            var typingAttributes = textView.typingAttributes
            let paragraphStyle = (
                typingAttributes[.paragraphStyle] as? NSParagraphStyle
            )?.mutableCopy() as? NSMutableParagraphStyle ?? NSMutableParagraphStyle()
            paragraphStyle.alignment = alignment
            typingAttributes[.paragraphStyle] = paragraphStyle
            textView.typingAttributes = typingAttributes

            // TextViewWithPlaceholder owns a direct UILabel child. Updating that presentation
            // object is intentionally separate from the document-backed text storage.
            textView.subviews.compactMap { $0 as? UILabel }.forEach {
                $0.textAlignment = alignment
            }
        }

        invalidateDisplayLayout(of: textView)
    }

    private static func removeDisplayAlignment(from textView: UITextView) {
        guard let layoutDelegate = layoutDelegates.object(forKey: textView),
              textView.layoutManager.delegate === layoutDelegate else { return }
        layoutDelegate.alignment = nil
        invalidateDisplayLayout(of: textView)
    }

    private static func invalidateDisplayLayout(of textView: UITextView) {
        let characterRange = NSRange(location: 0, length: textView.textStorage.length)
        textView.layoutManager.invalidateLayout(
            forCharacterRange: characterRange,
            actualCharacterRange: nil
        )
        textView.layoutManager.invalidateDisplay(forCharacterRange: characterRange)
        textView.setNeedsLayout()
    }
}

@MainActor
private final class PinkhaTextLayoutDelegate: NSObject, NSLayoutManagerDelegate {
    var alignment: NSTextAlignment?

    func layoutManager(
        _ layoutManager: NSLayoutManager,
        shouldSetLineFragmentRect lineFragmentRect: UnsafeMutablePointer<CGRect>,
        lineFragmentUsedRect: UnsafeMutablePointer<CGRect>,
        baselineOffset: UnsafeMutablePointer<CGFloat>,
        in textContainer: NSTextContainer,
        forGlyphRange glyphRange: NSRange
    ) -> Bool {
        guard let alignment, alignment == .left || alignment == .right else { return false }

        let fragment = lineFragmentRect.pointee
        var used = lineFragmentUsedRect.pointee
        guard used.width <= fragment.width else { return false }

        used.origin.x = alignment == .right
            ? fragment.maxX - used.width
            : fragment.minX
        lineFragmentUsedRect.pointee = used
        return true
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
