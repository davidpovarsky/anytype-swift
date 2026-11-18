import UIKit

/// Markdown listener unit tests need an editing text view without mounting a
/// window. Keep that test double local to their instances; overriding UITextView
/// globally corrupts the real editor's first-responder and caret lifecycle.
final class MarkdownTestTextView: UITextView {
    override var isFirstResponder: Bool { true }
}
