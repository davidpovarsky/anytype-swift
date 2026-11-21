#if canImport(UIKit)
import UIKit
import PinkhaKit

/// The caller resolves pending local drafts before rendering. Equal text keeps
/// UIKit's live character storage and selection; only presentation attributes
/// change. A marked-text buffer always retains ownership of its characters.
@MainActor
enum AnyNativeTextRenderer {
    @discardableResult
    static func apply(_ incoming: NSAttributedString, to input: UITextView,
                      isComposing: Bool) -> Bool {
        let action = PinkhaTextInputRenderPolicy.action(
            incoming: incoming.string, live: input.text ?? "",
            isComposing: isComposing, hasPendingLocalChanges: false)
        guard action != .preserve else { return false }
        let selection = input.selectedRange
        switch action {
        case .preserve:
            return false
        case .updateAttributes:
            let storage = input.textStorage
            storage.beginEditing()
            incoming.enumerateAttributes(in: NSRange(location: 0, length: incoming.length), options: []) { attributes, range, _ in
                storage.setAttributes(attributes, range: range)
            }
            storage.endEditing()
        case .replace:
            input.attributedText = incoming
        }
        if selection.location <= input.textStorage.length {
            input.selectedRange = NSRange(location: selection.location,
                length: min(selection.length, input.textStorage.length - selection.location))
        }
        return true
    }
}
#endif
