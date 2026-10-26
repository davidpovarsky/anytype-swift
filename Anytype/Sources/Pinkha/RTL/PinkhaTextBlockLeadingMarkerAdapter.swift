import UIKit

@MainActor
enum PinkhaTextBlockLeadingMarkerAdapter {
    static func applyNumberAlignment(
        context: PinkhaTextBlockWritingContext?,
        content: BlockText,
        to leadingView: TextBlockLeadingView
    ) {
        guard content.contentType == .numbered,
              let numberedView = leadingView.numberedView,
              let label = firstLabel(in: numberedView) else {
            return
        }
        if content.number >= 20 {
            let isPinkhaRTL = context != nil
                && leadingView.effectiveUserInterfaceLayoutDirection == .rightToLeft
            label.textAlignment = isPinkhaRTL ? .natural : .left
        } else {
            label.textAlignment = .center
        }
    }

    private static func firstLabel(in view: UIView) -> UILabel? {
        if let label = view as? UILabel { return label }
        for subview in view.subviews {
            if let label = firstLabel(in: subview) { return label }
        }
        return nil
    }
}
