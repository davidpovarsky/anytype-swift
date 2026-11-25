import UIKit

extension CustomTextView: UITextViewDelegate {    
    func textView(_ textView: UITextView, shouldChangeTextIn range: NSRange, replacementText text: String) -> Bool {
        guard let delegate = delegate else { return true }
        
        let range = textView.attributedText.rangeWithoutMention(range)
        let keyAction = CustomTextView.KeyboardAction
            .build(attributedText: textView.attributedText, range: range, replacement: text)

        if let keyAction = keyAction {
            delegate.keyboardAction(keyAction)
            return false
        } else {
            return delegate.shouldChangeText(range: range, replacementText: text)
        }
    }

    func textViewDidChangeSelection(_ textView: UITextView) {
        (textView as? TextViewWithPlaceholder)?.trackSelectionAnchor()
        if textView.isFirstResponder {
            delegate?.changeCaretPosition(textView.selectedRange)
        }
    }

    func textViewShouldBeginEditing(_ textView: UITextView) -> Bool {
        PinkhaStage1AcceptanceDiagnostics.recordNativeFocus(.shouldBeginEntered, in: textView)
        delegate?.willBeginEditing()
        PinkhaStage1AcceptanceDiagnostics.recordNativeFocus(.shouldBeginAllowed, in: textView)
        return true
    }

    func textViewDidBeginEditing(_ textView: UITextView) {
        PinkhaStage1AcceptanceDiagnostics.recordNativeFocus(.delegateDidBegin, in: textView)
        delegate?.didBeginEditing()
    }

    func textViewDidChange(_ textView: UITextView) {
        delegate?.textViewDidChangeText(textView)
    }
    
    func textView(
        _ textView: UITextView,
        shouldInteractWith URL: URL,
        in characterRange: NSRange,
        interaction: UITextItemInteraction
    ) -> Bool {
        if !textView.isFirstResponder && interaction == .invokeDefaultAction {
            delegate?.openURL(URL)
        }
        return false
    }
    
    func textViewDidEndEditing(_ textView: UITextView) {
        PinkhaStage1AcceptanceDiagnostics.recordNativeFocus(.delegateDidEnd, in: textView)
        delegate?.didEndEditing()
    }

    func textView(_ textView: UITextView, editMenuForTextIn range: NSRange, suggestedActions: [UIMenuElement]) -> UIMenu? {
        // Keep only standard edit menu to avoid iOS 26 floating issue with "more" button
        let standardEdit = suggestedActions.first { ($0 as? UIMenu)?.identifier == .standardEdit }
        var actions: [UIMenuElement] = standardEdit.map { [$0] } ?? suggestedActions
        var responder: UIResponder? = textView
        while let current = responder {
            if let editor = current as? EditorPageController {
                if let action = editor.originalExternalMiniAppsAction(textView: textView, range: range) {
                    actions.append(action)
                }
                break
            }
            responder = current.next
        }
        return UIMenu(children: actions)
    }
}
