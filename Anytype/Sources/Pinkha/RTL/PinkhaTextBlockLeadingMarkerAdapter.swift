import Services
import UIKit

@MainActor
enum PinkhaTextBlockLeadingMarkerAdapter {
    private static let rtlMarkerConstraintIdentifier = "pinkha.numbered-marker.right"
    private static let rtlTextConstraintIdentifier = "pinkha.numbered-text.right-to-marker"

    static func applyNumberAlignment(
        context: PinkhaTextBlockWritingContext?,
        content: BlockText,
        to leadingView: TextBlockLeadingView
    ) {
        let isPinkhaRTL = content.contentType == .numbered
            && context != nil
            && leadingView.effectiveUserInterfaceLayoutDirection == .rightToLeft
        applyPhysicalMarkerSide(isPinkhaRTL: isPinkhaRTL, to: leadingView)

        guard content.contentType == .numbered,
              let numberedView = leadingView.numberedView,
              let label = firstLabel(in: numberedView) else {
            return
        }
        if content.number >= 20 {
            label.textAlignment = isPinkhaRTL ? .natural : .left
        } else {
            label.textAlignment = .center
        }
    }

    /// The host row pins its marker with physical left/right anchors, so changing only the
    /// label's alignment cannot move a Hebrew list number to the physical right. Replace those
    /// two layout relationships only while an exact Pinkha row is rendered in RTL, and restore
    /// the original constraints on reuse for Pinkha LTR or ordinary Anytype documents.
    private static func applyPhysicalMarkerSide(
        isPinkhaRTL: Bool,
        to leadingView: TextBlockLeadingView
    ) {
        guard let container = leadingView.superview,
              let textView = container.subviews.first(where: { $0 is CustomTextView }),
              let originalMarkerConstraint = container.constraints.first(where: {
                  connects($0, leadingView, .left, to: container, .left)
              }),
              let originalTextConstraint = container.constraints.first(where: {
                  connects($0, textView, .leading, to: leadingView, .trailing)
              }) else {
            return
        }

        let rtlMarkerConstraint = container.constraints.first {
            $0.identifier == rtlMarkerConstraintIdentifier
        } ?? {
            let constraint = leadingView.rightAnchor.constraint(equalTo: container.rightAnchor)
            constraint.identifier = rtlMarkerConstraintIdentifier
            return constraint
        }()
        let rtlTextConstraint = container.constraints.first {
            $0.identifier == rtlTextConstraintIdentifier
        } ?? {
            let constraint = textView.rightAnchor.constraint(
                equalTo: leadingView.leftAnchor,
                constant: -4
            )
            constraint.identifier = rtlTextConstraintIdentifier
            return constraint
        }()

        originalMarkerConstraint.isActive = !isPinkhaRTL
        originalTextConstraint.isActive = !isPinkhaRTL
        rtlMarkerConstraint.isActive = isPinkhaRTL
        rtlTextConstraint.isActive = isPinkhaRTL
    }

    private static func connects(
        _ constraint: NSLayoutConstraint,
        _ firstItem: AnyObject,
        _ firstAttribute: NSLayoutConstraint.Attribute,
        to secondItem: AnyObject,
        _ secondAttribute: NSLayoutConstraint.Attribute
    ) -> Bool {
        let forward = constraint.firstItem as AnyObject? === firstItem
            && constraint.firstAttribute == firstAttribute
            && constraint.secondItem as AnyObject? === secondItem
            && constraint.secondAttribute == secondAttribute
        let reverse = constraint.firstItem as AnyObject? === secondItem
            && constraint.firstAttribute == secondAttribute
            && constraint.secondItem as AnyObject? === firstItem
            && constraint.secondAttribute == firstAttribute
        return forward || reverse
    }

    private static func firstLabel(in view: UIView) -> UILabel? {
        if let label = view as? UILabel { return label }
        for subview in view.subviews {
            if let label = firstLabel(in: subview) { return label }
        }
        return nil
    }
}
