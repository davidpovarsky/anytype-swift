import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf
import Testing
import UIKit
@testable import Anytype

@Suite("App-wide UIKit text direction adapter", .serialized)
@MainActor
struct PinkhaTextDirectionUIKitAdapterTests {
    @Test("Language rendering changes alignment without text, attribute, selection or callback writes")
    func languageRenderingIsDisplayOnly() throws {
        let textView = UndoTrackingTextView(frame: CGRect(x: 0, y: 0, width: 320, height: 120))
        let observer = TextMutationObserver()
        textView.delegate = observer
        textView.textStorage.delegate = observer
        textView.semanticContentAttribute = .forceRightToLeft
        let hostParagraphStyle = NSMutableParagraphStyle()
        hostParagraphStyle.alignment = .left
        textView.attributedText = NSAttributedString(
            string: "English text",
            attributes: [
                .font: UIFont.systemFont(ofSize: 17),
                .paragraphStyle: hostParagraphStyle
            ]
        )
        textView.selectedRange = NSRange(location: 4, length: 3)
        textView.typingAttributes = [.font: UIFont.systemFont(ofSize: 17)]
        observer.reset()

        let attributedBefore = textView.attributedText
        let selectionBefore = textView.selectedRange
        let typingBefore = textView.typingAttributes
        let undoFlag = UndoFlagBox()
        textView.testUndoManager.registerUndo(withTarget: undoFlag) { $0.reached = true }
        let couldUndoBefore = textView.testUndoManager.canUndo

        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)
        textView.layoutManager.ensureLayout(for: textView.textContainer)

        let glyphRange = textView.layoutManager.glyphRange(for: textView.textContainer)
        #expect(glyphRange.length > 0)
        let fragment = textView.layoutManager.lineFragmentRect(
            forGlyphAt: glyphRange.location,
            effectiveRange: nil
        )
        let used = textView.layoutManager.lineFragmentUsedRect(
            forGlyphAt: glyphRange.location,
            effectiveRange: nil
        )

        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .right)
        #expect(abs(used.maxX - fragment.maxX) < 0.5)
        #expect(textView.attributedText == attributedBefore)
        #expect(textView.selectedRange == selectionBefore)
        #expect(NSDictionary(dictionary: textView.typingAttributes).isEqual(
            NSDictionary(dictionary: typingBefore)
        ))
        #expect(observer.textChangeCount == 0)
        #expect(observer.storageEditCount == 0)
        #expect(textView.testUndoManager.canUndo == couldUndoBefore)

        textView.semanticContentAttribute = .forceLeftToRight
        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)
        textView.layoutManager.ensureLayout(for: textView.textContainer)
        let leftUsed = textView.layoutManager.lineFragmentUsedRect(
            forGlyphAt: glyphRange.location,
            effectiveRange: nil
        )
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .left)
        #expect(abs(leftUsed.minX - fragment.minX) < 0.5)
        #expect(textView.attributedText == attributedBefore)
        #expect(observer.textChangeCount == 0)
        #expect(observer.storageEditCount == 0)

        textView.testUndoManager.undo()
        #expect(undoFlag.reached)
    }

    @Test("An active marked-text composition is left byte-for-byte untouched")
    func activeIMECompositionIsUntouched() throws {
        let window = UIWindow(frame: CGRect(x: 0, y: 0, width: 390, height: 844))
        let controller = UIViewController()
        let textView = UITextView(frame: controller.view.bounds)
        controller.view.addSubview(textView)
        window.rootViewController = controller
        window.makeKeyAndVisible()
        textView.semanticContentAttribute = .forceRightToLeft
        textView.textAlignment = .center
        textView.text = "abc"
        textView.selectedRange = NSRange(location: 3, length: 0)
        #expect(textView.becomeFirstResponder())
        textView.setMarkedText("אב", selectedRange: NSRange(location: 2, length: 0))
        _ = try #require(textView.markedTextRange)

        let attributedBefore = textView.attributedText
        let selectionBefore = textView.selectedRange
        let alignmentBefore = textView.textAlignment
        let typingBefore = textView.typingAttributes

        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)

        #expect(textView.attributedText == attributedBefore)
        #expect(textView.selectedRange == selectionBefore)
        #expect(textView.textAlignment == alignmentBefore)
        #expect(NSDictionary(dictionary: textView.typingAttributes).isEqual(
            NSDictionary(dictionary: typingBefore)
        ))
        textView.unmarkText()
        textView.resignFirstResponder()
        window.isHidden = true
    }

    @Test("A reused empty row keeps placeholder and caret alignment synchronized")
    func placeholderAndCaretAlignment() throws {
        let textView = TextViewWithPlaceholder(frame: .zero, textContainer: nil)
        textView.semanticContentAttribute = .forceRightToLeft
        textView.update(placeholder: NSAttributedString(string: "כתוב כאן"))
        let observer = TextMutationObserver()
        textView.delegate = observer
        textView.textStorage.delegate = observer
        observer.reset()

        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)

        let placeholder = try #require(textView.subviews.compactMap { $0 as? UILabel }.first)
        let paragraphStyle = try #require(
            textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle
        )
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .right)
        #expect(paragraphStyle.alignment == .right)
        #expect(placeholder.textAlignment == .right)
        #expect(textView.selectedRange == NSRange(location: 0, length: 0))
        #expect(textView.attributedText.length == 0)
        #expect(observer.textChangeCount == 0)
        #expect(observer.storageEditCount == 0)

        textView.semanticContentAttribute = .forceLeftToRight
        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)
        let updatedParagraphStyle = try #require(
            textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle
        )
        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .left)
        #expect(updatedParagraphStyle.alignment == .left)
        #expect(placeholder.textAlignment == .left)
        #expect(observer.textChangeCount == 0)
        #expect(observer.storageEditCount == 0)
    }

    @Test("Ordinary Note and Page receive the same application-direction context", arguments: [
        "ordinary-note-type",
        "ordinary-page-type"
    ])
    func ordinaryDocumentsAreNotGated(typeId: String) throws {
        let blockId = "block-\(typeId)"
        let info = makeInfo(blockId: blockId)
        let document = makeDocument(typeId: typeId, blockId: blockId, info: info)

        let context = try #require(PinkhaTextDirectionUIKitAdapter.context(
            document: document,
            info: info,
            text: "ordinary text"
        ))

        #expect(context.origin == .ambiguousLegacyParagraph)
        #expect(context.blockId == blockId)
        #expect(!context.alignmentWasExplicit)
    }

    @Test("Content direction stays natural while default alignment follows app language")
    func contentDirectionAndDefaultAlignmentAreIndependent() {
        let textView = UITextView()
        textView.semanticContentAttribute = .forceLeftToRight
        textView.attributedText = NSAttributedString(string: "שלום")

        PinkhaTextDirectionUIKitAdapter.apply(context: automaticContext, to: textView)

        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .left)
        #expect(PinkhaTextDirectionUIKitAdapter.detectedDirection(
            for: textView.text,
            fallback: .leftToRight
        ) == .rightToLeft)
    }

    @Test("Explicit alignment remains unchanged when application direction changes")
    func explicitAlignmentWins() {
        let textView = UITextView()
        textView.semanticContentAttribute = .forceRightToLeft
        textView.textAlignment = .left
        let explicitLeft = PinkhaTextBlockWritingContext(
            origin: .existingParagraph,
            persistedAlignment: .left,
            alignmentWasExplicit: true
        )

        PinkhaTextDirectionUIKitAdapter.apply(context: explicitLeft, to: textView)

        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .left)
    }

    @Test("Old automatic markers no longer override the current application language")
    func oldAutomaticMarkerUsesCurrentLanguage() throws {
        let blockId = "automatic-marker"
        var fields = BlockFields()
        fields[PinkhaSchemaRoles.blockTextDirectionField] = Google_Protobuf_Value(
            stringValue: PinkhaTextDirectionMarker.automatic(.rightToLeft).storedValue
        )
        let info = makeInfo(blockId: blockId, alignment: .right, fields: fields)
        let document = makeDocument(typeId: "ordinary-page", blockId: blockId, info: info)
        let context = try #require(PinkhaTextDirectionUIKitAdapter.context(
            document: document,
            info: info,
            text: ""
        ))
        let textView = UITextView()
        textView.semanticContentAttribute = .forceLeftToRight

        PinkhaTextDirectionUIKitAdapter.apply(context: context, to: textView)

        #expect(PinkhaTextDirectionUIKitAdapter.visualAlignment(for: textView) == .left)
        #expect(!context.alignmentWasExplicit)
    }

    private var automaticContext: PinkhaTextBlockWritingContext {
        PinkhaTextBlockWritingContext(
            origin: .ambiguousLegacyParagraph,
            persistedAlignment: .left,
            alignmentWasExplicit: false
        )
    }

    private func makeDocument(
        typeId: String,
        blockId: String,
        info: BlockInformation
    ) -> MockBaseDocument {
        let details = ObjectDetails(
            id: "document-\(typeId)",
            values: [
                BundledPropertyKey.type.rawValue: Google_Protobuf_Value(stringValue: typeId)
            ]
        )
        let document = MockBaseDocument(objectId: details.id, details: details)
        document.mockSpaceId = "ordinary-space"
        let container = InfoContainerMock()
        container.getReturnInfo[blockId] = info
        document.mockInfoContainer = container
        return document
    }

    private func makeInfo(
        blockId: String,
        alignment: LayoutAlignment = .left,
        fields: BlockFields = [:]
    ) -> BlockInformation {
        BlockInformation(
            id: blockId,
            content: .text(.plain("ordinary text", contentType: .text)),
            backgroundColor: nil,
            horizontalAlignment: alignment,
            childrenIds: [],
            configurationData: BlockInformationMetadata(backgroundColor: .default),
            fields: fields
        )
    }
}

@MainActor
private final class UndoTrackingTextView: UITextView {
    let testUndoManager = UndoManager()
    override var undoManager: UndoManager? { testUndoManager }
}

@MainActor
private final class TextMutationObserver: NSObject, UITextViewDelegate, NSTextStorageDelegate {
    private(set) var textChangeCount = 0
    private(set) var storageEditCount = 0

    func reset() {
        textChangeCount = 0
        storageEditCount = 0
    }

    func textViewDidChange(_ textView: UITextView) {
        textChangeCount += 1
    }

    nonisolated func textStorage(
        _ textStorage: NSTextStorage,
        didProcessEditing editedMask: NSTextStorage.EditActions,
        range editedRange: NSRange,
        changeInLength delta: Int
    ) {
        MainActor.assumeIsolated {
            storageEditCount += 1
        }
    }
}

private final class UndoFlagBox: NSObject {
    var reached = false
}
