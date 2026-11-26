import UIKit


@MainActor
final class TextViewAttributeSelectionInteraction: NSObject {
    
    private weak var textView: UITextView?
    private let attributeKey: NSAttributedString.Key
    private let numberOfTapsRequired: Int
    private let tapHandler: any TextViewAttributeSelectionHandler
    private var selectionRecognizer: UITapGestureRecognizer?
    
    init(
        textView: UITextView,
        attributeKey: NSAttributedString.Key,
        numberOfTapsRequired: Int,
        tapHandler: some TextViewAttributeSelectionHandler
    ) {
        self.textView = textView
        self.attributeKey = attributeKey
        self.numberOfTapsRequired = numberOfTapsRequired
        self.tapHandler = tapHandler
    }
    
    private func attributeRectsForTap() -> [CGRect]? {
        guard let textView = textView,
              let ranges = textView.attributedText.rangesWith(attribute: attributeKey) else {
            return nil
        }
        let glyphRanges = ranges.map { range in
            textView.layoutManager.glyphRange(
                forCharacterRange: range,
                actualCharacterRange: nil
            )
        }
        let boundingRects = glyphRanges.map { range -> CGRect in
            textView.layoutManager.boundingRect(
                forGlyphRange: range,
                in: textView.textContainer
            )
        }
        let containerInset = textView.textContainerInset
        let additionalHeight = (containerInset.top + containerInset.bottom) / 2
        return boundingRects.map { rect in
            CGRect(
                origin: rect.origin,
                size: CGSize(
                    width: rect.width,
                    height: rect.height + additionalHeight
                )
            )
        }
    }
    
    @objc private func handle(gestureRecognizer: UITapGestureRecognizer) {
        guard let textView,
              gestureRecognizer === selectionRecognizer,
              gestureRecognizer.view === textView,
              gestureRecognizer.state == .ended else { return }
        tapHandler.didSelect(
            attributeKey,
            in: textView,
            recognizer: gestureRecognizer
        )
    }
}

extension TextViewAttributeSelectionInteraction: UIInteraction {

    var view: UIView? {
        selectionRecognizer?.view
    }

    func willMove(to view: UIView?) {
        // An interaction removed from a reused input must not leave its
        // recognizer or a failure dependency attached to the previous view.
        if let selectionRecognizer {
            selectionRecognizer.view?.removeGestureRecognizer(selectionRecognizer)
        }
        selectionRecognizer = nil
    }

    func didMove(to view: UIView?) {
        guard let textView, view === textView else { return }
        let gestureRecognizer = UITapGestureRecognizer(
            target: self,
            action: #selector(handle)
        )
        gestureRecognizer.numberOfTapsRequired = numberOfTapsRequired
        gestureRecognizer.delegate = self
        selectionRecognizer = gestureRecognizer
        textView.addGestureRecognizer(gestureRecognizer)
    }
}

extension TextViewAttributeSelectionInteraction: UIGestureRecognizerDelegate {

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        guard let textView,
              gestureRecognizer === selectionRecognizer,
              gestureRecognizer.view === textView,
              let rects = attributeRectsForTap() else { return false }
        // Resolve ownership from the first touch. Unlinked text must not wait
        // for a link double tap to fail before its normal editing gesture.
        let point = touch.location(in: textView)
        return rects.contains { $0.contains(point) }
    }

    func gestureRecognizer(
        _ gestureRecognizer: UIGestureRecognizer,
        shouldBeRequiredToFailBy otherGestureRecognizer: UIGestureRecognizer
    ) -> Bool {
        guard attributeKey == .link, numberOfTapsRequired == 2,
              let textView,
              gestureRecognizer === selectionRecognizer,
              gestureRecognizer.view === textView,
              gestureRecognizer !== otherGestureRecognizer,
              let otherView = otherGestureRecognizer.view,
              otherView === textView || otherView.isDescendant(of: textView) else {
            return false
        }
        // UIKit otherwise invokes a link on the first tap while our second
        // tap selects it. The pending navigation can then cover the edit menu.
        // Give this exact input's link selection priority using public failure
        // requirements; an ordinary single tap still proceeds when it fails.
        if let singleTap = otherGestureRecognizer as? UITapGestureRecognizer,
           singleTap.numberOfTapsRequired == 1,
           singleTap.numberOfTouchesRequired == 1 {
            return true
        }
        // UITextInteraction explicitly exposes its native text gestures for
        // this purpose. Do not identify private UIKit recognizer classes or
        // interfere with another input, row, or parent scrolling gesture.
        return textView.interactions.compactMap { $0 as? UITextInteraction }.contains { interaction in
            interaction.textInput === textView &&
                interaction.gesturesForFailureRequirements.contains { $0 === otherGestureRecognizer }
        }
    }
    
    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard let textView,
              gestureRecognizer === selectionRecognizer,
              gestureRecognizer.view === textView,
              let rects = attributeRectsForTap() else {
            return false
        }
        let tapLocation = gestureRecognizer.location(in: textView)
        return rects.contains { rect in rect.contains(tapLocation) }
    }
    
    func gestureRecognizer(
        _ gestureRecognizer: UIGestureRecognizer,
        shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer
    ) -> Bool {
        false
    }
    
    func gestureRecognizer(
        _ gestureRecognizer: UIGestureRecognizer,
        shouldRequireFailureOf otherGestureRecognizer: UIGestureRecognizer
    ) -> Bool {
        false
    }
}

