import Testing
import UIKit
import PinkhaKit
@testable import Anytype

@Suite("Pinkha UIKit text direction adapter", .serialized)
@MainActor
struct PinkhaTextDirectionUIKitAdapterTests {
    @Test("Hebrew styling preserves canonical text, selection, focus and the existing undo stack")
    func preservesEditingState() throws {
        let window = UIWindow(frame: CGRect(x: 0, y: 0, width: 390, height: 844))
        let controller = UIViewController()
        let textView = UndoTrackingTextView(frame: controller.view.bounds)
        controller.view.addSubview(textView)
        window.rootViewController = controller
        window.makeKeyAndVisible()

        textView.semanticContentAttribute = .forceRightToLeft
        textView.attributedText = NSAttributedString(string: "שלום עולם")
        textView.selectedRange = NSRange(location: 4, length: 3)
        let textBefore = textView.text
        let selectionBefore = textView.selectedRange
        let wasFirstResponder = textView.becomeFirstResponder()
        #expect(wasFirstResponder)

        let undoFlag = UndoFlagBox()
        textView.testUndoManager.registerUndo(withTarget: undoFlag) { target in
            target.reached = true
        }
        let couldUndoBefore = textView.testUndoManager.canUndo

        PinkhaTextDirectionUIKitAdapter.apply(context: pinkhaContext, to: textView)

        #expect(textView.text == textBefore)
        #expect(textView.selectedRange == selectionBefore)
        #expect(textView.isFirstResponder == wasFirstResponder)
        #expect(textView.textAlignment == .right)
        #expect(textView.testUndoManager.canUndo == couldUndoBefore)
        textView.testUndoManager.undo()
        #expect(undoFlag.reached)

        let style = try #require(textView.textStorage.attribute(
            .paragraphStyle,
            at: 0,
            effectiveRange: nil
        ) as? NSParagraphStyle)
        #expect(style.baseWritingDirection == .rightToLeft)
        #expect(style.alignment == .right)

        textView.resignFirstResponder()
        window.isHidden = true
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
        let typingAttributesBefore = textView.typingAttributes

        PinkhaTextDirectionUIKitAdapter.apply(context: pinkhaContext, to: textView)

        #expect(textView.attributedText == attributedBefore)
        #expect(textView.selectedRange == selectionBefore)
        #expect(textView.textAlignment == alignmentBefore)
        #expect(NSDictionary(dictionary: textView.typingAttributes).isEqual(
            NSDictionary(dictionary: typingAttributesBefore)
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

        PinkhaTextDirectionUIKitAdapter.apply(context: pinkhaContext, to: textView)

        let placeholder = try #require(textView.subviews.compactMap { $0 as? UILabel }.first)
        #expect(textView.textAlignment == .right)
        #expect(placeholder.textAlignment == .right)
        #expect(textView.selectedRange == NSRange(location: 0, length: 0))

        textView.semanticContentAttribute = .forceLeftToRight
        PinkhaTextDirectionUIKitAdapter.apply(context: pinkhaContext, to: textView)
        #expect(textView.textAlignment == .left)
        #expect(placeholder.textAlignment == .left)
    }

    @Test("Ordinary Anytype text is a strict no-op even in an RTL interface")
    func ordinaryAnytypeNoOp() {
        let textView = UITextView()
        textView.semanticContentAttribute = .forceRightToLeft
        textView.attributedText = NSAttributedString(string: "ordinary text")
        textView.textAlignment = .center
        textView.selectedRange = NSRange(location: 2, length: 4)
        let attributedBefore = textView.attributedText
        let typingBefore = textView.typingAttributes

        PinkhaTextDirectionUIKitAdapter.apply(context: nil, to: textView)

        #expect(textView.attributedText == attributedBefore)
        #expect(textView.textAlignment == .center)
        #expect(textView.selectedRange == NSRange(location: 2, length: 4))
        #expect(NSDictionary(dictionary: textView.typingAttributes).isEqual(
            NSDictionary(dictionary: typingBefore)
        ))
    }

    private var pinkhaContext: PinkhaTextBlockWritingContext {
        PinkhaTextBlockWritingContext(
            origin: .newParagraph,
            persistedAlignment: nil,
            alignmentWasExplicit: false
        )
    }
}

@MainActor
private final class UndoTrackingTextView: UITextView {
    let testUndoManager = UndoManager()
    override var undoManager: UndoManager? { testUndoManager }
}

private final class UndoFlagBox: NSObject {
    var reached = false
}
