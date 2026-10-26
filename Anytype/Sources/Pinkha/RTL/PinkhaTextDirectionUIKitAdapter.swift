import UIKit
import NaturalLanguage
import Factory
import PinkhaKit
import Services

struct PinkhaTextBlockWritingContext: Equatable, Hashable {
    let origin: PinkhaParagraphOrigin
    let persistedAlignment: PinkhaParagraphAlignment?
    let alignmentWasExplicit: Bool
}

@MainActor
enum PinkhaTextDirectionGate {
    static func isWritingDocument(_ document: some BaseDocumentProtocol) -> Bool {
        guard PinkhaRuntime.enabled,
              let typeId = document.details?.type,
              let manifest = Container.shared.pinkhaBootstrapService().manifest(forSpaceId: document.spaceId) else {
            return false
        }
        return manifest.isRegisteredDocumentType(typeId: typeId)
    }
}

@MainActor
enum PinkhaTextDirectionUIKitAdapter {
    static func context(
        document: some BaseDocumentProtocol,
        info: BlockInformation,
        text: String
    ) -> PinkhaTextBlockWritingContext? {
        let isPinkhaWritingDocument = PinkhaTextDirectionGate.isWritingDocument(document)
        PinkhaNavigationGestureBridge.setPinkhaWritingDocument(
            id: document.objectId,
            isPinkhaWritingDocument: isPinkhaWritingDocument
        )
        guard isPinkhaWritingDocument else { return nil }

        let hostAlignment: LayoutAlignment
        if info.textContent?.contentType == .title, let details = document.details {
            hostAlignment = details.objectAlignValue
        } else {
            hostAlignment = info.horizontalAlignment
        }

        if let sessionAlignment = PinkhaTextDirectionPersistence.sessionExplicitAlignment(
            blockId: info.id
        ) {
            return PinkhaTextBlockWritingContext(
                origin: .existingParagraph,
                persistedAlignment: sessionAlignment,
                alignmentWasExplicit: true
            )
        }

        let marker = marker(from: info.fields)
        switch marker {
        case let .explicit(alignment):
            return PinkhaTextBlockWritingContext(
                origin: .existingParagraph,
                persistedAlignment: alignment,
                alignmentWasExplicit: true
            )
        case let .automatic(direction):
            if !PinkhaAutomaticDirectionEligibility.markerMatchesStoredAlignment(
                marker: .automatic(direction),
                storedAlignment: hostAlignment.pinkhaAlignment
            ) {
                // The host alignment changed but the automatic marker did not. The safest
                // interpretation is a successful explicit alignment followed by a failed
                // metadata write; never overwrite that stored choice automatically.
                return PinkhaTextBlockWritingContext(
                    origin: .existingParagraph,
                    persistedAlignment: hostAlignment.pinkhaAlignment,
                    alignmentWasExplicit: true
                )
            }
            return PinkhaTextBlockWritingContext(
                origin: .existingParagraph,
                persistedAlignment: nil,
                alignmentWasExplicit: false
            )
        case nil:
            // Session registration is the only reliable proof that a marker-less block is
            // new. Text content alone is never used to infer consent to persist metadata.
            let isProvenNew = SessionCreatedBlockIdsStorage.shared.contains(info.id)
                || isLocallyFabricatedUnlinkedBlock(document: document, info: info)
            if isProvenNew, !text.isEmpty {
                PinkhaTextDirectionPersistence.scheduleInitialDirectionIfNeeded(
                    document: document,
                    info: info,
                    text: text
                )
            }
            let origin: PinkhaParagraphOrigin = isProvenNew
                ? .newParagraph
                : .ambiguousLegacyParagraph
            return PinkhaTextBlockWritingContext(
                origin: origin,
                persistedAlignment: hostAlignment.pinkhaAlignment,
                alignmentWasExplicit: false
            )
        }
    }

    static func apply(
        context: PinkhaTextBlockWritingContext?,
        to textView: UITextView
    ) {
        guard let context else { return }

        let interfaceDirection = textView.effectiveUserInterfaceLayoutDirection.pinkhaDirection
        let decision = PinkhaWritingDirectionPolicy.resolve(
            PinkhaWritingDirectionInput(
                context: .pinkhaWritingDocument,
                origin: context.origin,
                isEmpty: textView.text.isEmpty,
                interfaceDirection: interfaceDirection,
                detectedTextDirection: resolvedDirection(
                    in: textView,
                    fallback: interfaceDirection
                ),
                persistedAlignment: context.persistedAlignment,
                alignmentWasExplicit: context.alignmentWasExplicit
            )
        )
        guard let decision else { return }

        let alignment = decision.alignment.nsTextAlignment
        let writingDirection = decision.baseWritingDirection.nsWritingDirection

        // Never touch paragraph, alignment or typing state while an IME composition is
        // active. The next model echo/configuration applies the same decision after commit.
        guard textView.markedTextRange == nil else { return }

        // These properties also drive the empty-state caret and placeholder. The
        // TextViewWithPlaceholder override keeps its label synchronized on reused rows.
        textView.textAlignment = alignment

        if textView.textStorage.length > 0 {
            applyParagraphStyle(
                to: textView.textStorage,
                writingDirection: writingDirection,
                alignment: alignment
            )
        }

        var typingAttributes = textView.typingAttributes
        let typingStyle = mutableParagraphStyle(from: typingAttributes[.paragraphStyle])
        typingStyle.baseWritingDirection = writingDirection
        typingStyle.alignment = alignment
        typingAttributes[.paragraphStyle] = typingStyle
        textView.typingAttributes = typingAttributes
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

    private static func resolvedDirection(
        in textView: UITextView,
        fallback: PinkhaLayoutDirection
    ) -> PinkhaLayoutDirection? {
        guard !textView.text.isEmpty else { return nil }
        switch textView.baseWritingDirection(
            for: textView.beginningOfDocument,
            in: .forward
        ) {
        case .rightToLeft: return .rightToLeft
        case .leftToRight: return .leftToRight
        case .natural: return detectedDirection(for: textView.text, fallback: fallback)
        @unknown default: return detectedDirection(for: textView.text, fallback: fallback)
        }
    }

    static func marker(from fields: BlockFields) -> PinkhaTextDirectionMarker? {
        guard let value = fields[PinkhaSchemaRoles.blockTextDirectionField],
              case let .stringValue(storedValue) = value.kind else {
            return nil
        }
        return PinkhaTextDirectionMarker(storedValue: storedValue)
    }

    static func isLocallyFabricatedUnlinkedBlock(
        document: some BaseDocumentProtocol,
        info: BlockInformation
    ) -> Bool {
        // The virtual trailing row is inserted into InfoContainer before it exists in the
        // middleware, but it is intentionally not attached to its parent's children yet.
        // This is safe as a display-only new-row signal. Persistence still independently
        // requires SessionCreatedBlockIdsStorage after successful materialization.
        guard let parentId = info.configurationData.parentId,
              let parent = document.infoContainer.get(id: parentId) else {
            return false
        }
        return !parent.childrenIds.contains(info.id)
    }

    static func attributedDirection(
        in attributedText: NSAttributedString
    ) -> PinkhaLayoutDirection? {
        guard attributedText.length > 0,
              let style = attributedText.attribute(
                .paragraphStyle,
                at: 0,
                effectiveRange: nil
              ) as? NSParagraphStyle else {
            return nil
        }
        switch style.baseWritingDirection {
        case .rightToLeft: return .rightToLeft
        case .leftToRight: return .leftToRight
        case .natural: return nil
        @unknown default: return nil
        }
    }

    private static func applyParagraphStyle(
        to storage: NSTextStorage,
        writingDirection: NSWritingDirection,
        alignment: NSTextAlignment
    ) {
        let fullRange = NSRange(location: 0, length: storage.length)
        var replacements = [(NSRange, NSMutableParagraphStyle)]()
        storage.enumerateAttribute(.paragraphStyle, in: fullRange) { value, range, _ in
            let style = mutableParagraphStyle(from: value)
            style.baseWritingDirection = writingDirection
            style.alignment = alignment
            replacements.append((range, style))
        }

        storage.beginEditing()
        for (range, style) in replacements {
            storage.addAttribute(.paragraphStyle, value: style, range: range)
        }
        storage.endEditing()
    }

    private static func mutableParagraphStyle(from value: Any?) -> NSMutableParagraphStyle {
        if let style = value as? NSParagraphStyle,
           let copy = style.mutableCopy() as? NSMutableParagraphStyle {
            return copy
        }
        return NSMutableParagraphStyle()
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

private extension PinkhaLayoutDirection {
    var nsWritingDirection: NSWritingDirection {
        self == .rightToLeft ? .rightToLeft : .leftToRight
    }
}

private extension UIUserInterfaceLayoutDirection {
    var pinkhaDirection: PinkhaLayoutDirection {
        self == .rightToLeft ? .rightToLeft : .leftToRight
    }
}
