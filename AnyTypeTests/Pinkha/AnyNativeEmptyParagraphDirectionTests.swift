import Testing
import UIKit
@testable import PinkhaAnyUI

@Suite("Native empty paragraph presentation", .serialized)
@MainActor
struct AnyNativeEmptyParagraphDirectionTests {
    @Test("Empty native render retains paragraph direction and font through actual focus", arguments: [false, true])
    func emptyRenderAndFirstFocus(isRTL: Bool) throws {
        try withInput(isRTL: isRTL) { input in
            let font = UIFont.preferredFont(forTextStyle: .title2)
            input.configureEmptyParagraphPresentation(attributes(isRTL: isRTL, font: font), blockID: "current")
            #expect(AnyNativeTextRenderer.apply(NSAttributedString(string: ""), to: input, isComposing: false))
            input.restoreEmptyParagraphPresentation()
            let selection = input.selectedRange
            let undo = EmptyParagraphUndoProbe()
            input.editHistory.registerUndo(withTarget: undo) { $0.restored = true }

            try #require(input.becomeFirstResponder())
            input.layoutIfNeeded()
            let paragraph = try #require(input.typingAttributes[.paragraphStyle] as? NSParagraphStyle)
            #expect(paragraph.alignment == (isRTL ? .right : .left))
            #expect(paragraph.baseWritingDirection == (isRTL ? .rightToLeft : .leftToRight))
            #expect(paragraph.lineSpacing == 3)
            #expect(input.typingAttributes[.font] as? UIFont == font)
            #expect(input.textStorage.length == 0 && input.selectedRange == selection)
            let caret = input.caretRect(for: input.beginningOfDocument)
            try #require(caret.height > 0)
            #expect(isRTL ? caret.midX > input.bounds.midX : caret.midX < input.bounds.midX)

            // Explicit source alignment remains authoritative in an empty field.
            var centered = attributes(isRTL: isRTL, font: font)
            let style = NSMutableParagraphStyle()
            style.alignment = .center
            style.baseWritingDirection = isRTL ? .rightToLeft : .leftToRight
            centered[.paragraphStyle] = style
            input.configureEmptyParagraphPresentation(centered, blockID: "current")
            input.restoreEmptyParagraphPresentation()
            #expect(input.textAlignment == .center)
            #expect(input.textStorage.length == 0 && input.selectedRange == selection)
            input.editHistory.undo()
            #expect(undo.restored, "Presentation must not add a text undo operation")
        }
    }

    @Test("Empty typing and native selection resets retain unrelated attributes", arguments: [false, true])
    func emptyAttributeAndSelectionReset(isRTL: Bool) throws {
        try withInput(isRTL: isRTL) { input in
            input.configureEmptyParagraphPresentation(attributes(isRTL: isRTL), blockID: "current")
            input.restoreEmptyParagraphPresentation()
            try #require(input.becomeFirstResponder())
            let changed = NSMutableParagraphStyle()
            changed.alignment = isRTL ? .left : .right
            changed.baseWritingDirection = isRTL ? .leftToRight : .rightToLeft
            input.typingAttributes = [.paragraphStyle: changed, .underlineStyle: NSUnderlineStyle.single.rawValue]
            input.restoreEmptyParagraphPresentation()
            #expect(input.typingAttributes[.underlineStyle] as? Int == NSUnderlineStyle.single.rawValue)
            input.selectedRange = NSRange(location: 0, length: 0)
            input.restoreEmptyParagraphPresentation()
            let actual = try #require(input.typingAttributes[.paragraphStyle] as? NSParagraphStyle)
            #expect(actual.alignment == (isRTL ? .right : .left))
            #expect(actual.baseWritingDirection == (isRTL ? .rightToLeft : .leftToRight))
            #expect(input.textStorage.length == 0 && input.selectedRange == NSRange(location: 0, length: 0))
            #expect(!input.isRestoringEmptyParagraphPresentation)
        }
    }

    @Test("Marked and nonempty native text retain their own attributes and selection")
    func compositionAndNonemptyInputAreUntouched() throws {
        try withInput(isRTL: true) { input in
            input.configureEmptyParagraphPresentation(attributes(isRTL: true), blockID: "current")
            input.restoreEmptyParagraphPresentation()
            try #require(input.becomeFirstResponder())
            input.setMarkedText("אב", selectedRange: NSRange(location: 1, length: 0))
            try #require(input.isComposingMarkedText && input.markedTextRange != nil)
            let markedAttributes: [NSAttributedString.Key: Any] = [.font: UIFont.systemFont(ofSize: 26), .foregroundColor: UIColor.red]
            input.typingAttributes = markedAttributes
            let markedBefore = input.typingAttributes
            let before = NSAttributedString(attributedString: input.attributedText)
            let selection = input.selectedRange
            input.configureEmptyParagraphPresentation(attributes(isRTL: false), blockID: "current")
            input.restoreEmptyParagraphPresentation()
            #expect(NSDictionary(dictionary: input.typingAttributes).isEqual(NSDictionary(dictionary: markedBefore)))
            #expect(input.attributedText == before && input.selectedRange == selection)
            #expect(input.isComposingMarkedText && input.markedTextRange != nil)

            input.unmarkText()
            try #require(input.textStorage.length > 0)
            input.typingAttributes = markedAttributes
            let nonemptyBefore = input.typingAttributes
            input.restoreEmptyParagraphPresentation()
            #expect(NSDictionary(dictionary: input.typingAttributes).isEqual(NSDictionary(dictionary: nonemptyBefore)))
            #expect(input.text == before.string)
        }
    }

    @Test("A reused input rejects the retired block's empty presentation")
    func reuseClearsPriorBlockPresentation() throws {
        let input = AnyNativeTextView()
        input.blockID = "old"
        input.configureEmptyParagraphPresentation(attributes(isRTL: true), blockID: "old")
        input.restoreEmptyParagraphPresentation()
        input.blockID = "current"
        let current = attributes(isRTL: false)
        input.typingAttributes = current
        let currentBefore = input.typingAttributes
        input.configureEmptyParagraphPresentation(attributes(isRTL: true), blockID: "old")
        input.restoreEmptyParagraphPresentation()
        #expect(NSDictionary(dictionary: input.typingAttributes).isEqual(NSDictionary(dictionary: currentBefore)))
        input.configureEmptyParagraphPresentation(attributes(isRTL: true), blockID: "current")
        input.restoreEmptyParagraphPresentation()
        #expect((input.typingAttributes[.paragraphStyle] as? NSParagraphStyle)?.baseWritingDirection == .rightToLeft)
        input.blockID = nil
        input.typingAttributes = current
        let reusedBefore = input.typingAttributes
        input.restoreEmptyParagraphPresentation()
        #expect(NSDictionary(dictionary: input.typingAttributes).isEqual(NSDictionary(dictionary: reusedBefore)))
    }

    private func attributes(isRTL: Bool, font: UIFont = .preferredFont(forTextStyle: .body)) -> [NSAttributedString.Key: Any] {
        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = isRTL ? .right : .left
        paragraph.baseWritingDirection = isRTL ? .rightToLeft : .leftToRight
        paragraph.lineSpacing = 3
        return [.paragraphStyle: paragraph, .font: font, .foregroundColor: UIColor.label]
    }

    private func withInput(isRTL: Bool, body: (AnyNativeTextView) throws -> Void) throws {
        let scene = try #require(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let previousKey = scene.windows.first(where: \.isKeyWindow)
        let window = UIWindow(windowScene: scene)
        let controller = UIViewController()
        controller.view.semanticContentAttribute = isRTL ? .forceRightToLeft : .forceLeftToRight
        let input = AnyNativeTextView(frame: CGRect(x: 20, y: 80, width: 320, height: 120))
        input.blockID = "current"
        controller.view.addSubview(input)
        window.rootViewController = controller
        window.makeKeyAndVisible()
        controller.view.layoutIfNeeded()
        defer {
            input.unmarkText()
            input.resignFirstResponder()
            window.isHidden = true
            window.rootViewController = nil
            previousKey?.makeKey()
        }
        try body(input)
    }
}

private final class EmptyParagraphUndoProbe {
    var restored = false
}
