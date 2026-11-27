import Services
import UIKit

@MainActor
enum PinkhaTextBlockLeadingMarkerAdapter {
    static func applyNumberAlignment(
        context: PinkhaTextBlockWritingContext?,
        content: BlockText,
        to leadingView: TextBlockLeadingView
    ) {
        guard content.contentType == .numbered else {
            leadingView.onNumberedMarkerLayout = nil
            return
        }

        let number = content.number
        let usesApplicationDirection = context != nil
        leadingView.onNumberedMarkerLayout = { [weak leadingView] in
            guard let leadingView, let numberedView = leadingView.numberedView,
                  let label = firstLabel(in: numberedView) else { return }
            let isRTL = usesApplicationDirection
                && leadingView.effectiveUserInterfaceLayoutDirection == .rightToLeft
            let alignment: NSTextAlignment = number >= 20
                ? (isRTL ? .natural : .left)
                : .center
            // Attribute changes can request another layout. An already-correct
            // marker must not keep invalidating that layout or touch its text.
            if label.textAlignment != alignment {
                label.textAlignment = alignment
            }
        }
        leadingView.onNumberedMarkerLayout?()
    }

    private static func firstLabel(in view: UIView) -> UILabel? {
        if let label = view as? UILabel { return label }
        for subview in view.subviews {
            if let label = firstLabel(in: subview) { return label }
        }
        return nil
    }
}
