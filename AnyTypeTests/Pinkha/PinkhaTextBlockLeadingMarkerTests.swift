import PinkhaKit
import Services
import Testing
import UIKit
@testable import Anytype

@Suite("Numbered markers follow the mounted app direction", .serialized)
@MainActor
struct PinkhaTextBlockLeadingMarkerTests {
    @Test("Off-window configuration is refreshed after opposite-direction attachment", arguments: [false, true])
    func oppositeDirectionAttachmentRefreshesMarker(isRTL: Bool) throws {
        let marker = TextBlockLeadingView(frame: CGRect(x: 20, y: 80, width: 48, height: 40))
        marker.semanticContentAttribute = isRTL ? .forceLeftToRight : .forceRightToLeft
        configure(marker, number: 20, followsAppDirection: true)
        let label = try #require(firstLabel(in: try #require(marker.numberedView)))
        let initialAlignment = label.textAlignment
        let originalText = label.text
        let originalFont = label.font
        let originalColor = label.textColor
        #expect(initialAlignment == (isRTL ? .left : .natural))

        try withWindow(isRTL: isRTL) { controller in
            marker.semanticContentAttribute = .unspecified
            controller.view.addSubview(marker)
            controller.view.layoutIfNeeded()
            marker.layoutIfNeeded()

            #expect(marker.window != nil)
            #expect(marker.effectiveUserInterfaceLayoutDirection == (isRTL ? .rightToLeft : .leftToRight))
            #expect(firstLabel(in: marker.numberedView!) === label, "Attachment must retain the original Anytype marker")
            #expect(label.textAlignment == (isRTL ? .natural : .left))
            #expect(label.textAlignment != initialAlignment)
            #expect(label.text == originalText && label.font == originalFont && label.textColor == originalColor)
        }
    }

    @Test("Mounted direction changes preserve small numbers and clear reused non-numbered callbacks", arguments: [1, 20])
    func directionChangeAndReusePreserveMarkerPolicy(number: Int) throws {
        try withWindow(isRTL: false) { controller in
            let marker = TextBlockLeadingView(frame: CGRect(x: 20, y: 80, width: 48, height: 40))
            controller.view.addSubview(marker)
            configure(marker, number: number, followsAppDirection: true)
            let label = try #require(firstLabel(in: try #require(marker.numberedView)))
            let originalText = label.text

            controller.view.semanticContentAttribute = .forceRightToLeft
            marker.setNeedsLayout()
            marker.layoutIfNeeded()
            #expect(marker.effectiveUserInterfaceLayoutDirection == .rightToLeft)
            #expect(label.textAlignment == (number >= 20 ? .natural : .center))
            #expect(label.text == originalText)

            configure(marker, number: number, followsAppDirection: false)
            marker.setNeedsLayout()
            marker.layoutIfNeeded()
            #expect(firstLabel(in: marker.numberedView!) === label)
            #expect(label.textAlignment == (number >= 20 ? .left : .center),
                    "Rows without writing context retain the original Anytype policy")

            marker.update(blockId: "body", style: .body)
            PinkhaTextBlockLeadingMarkerAdapter.applyNumberAlignment(
                context: automaticContext, content: .empty(contentType: .text), to: marker)
            #expect(marker.onNumberedMarkerLayout == nil)
            #expect(marker.isHidden)
        }
    }

    private var automaticContext: PinkhaTextBlockWritingContext {
        PinkhaTextBlockWritingContext(origin: .ambiguousLegacyParagraph,
                                      persistedAlignment: .left, alignmentWasExplicit: false)
    }

    private func configure(_ marker: TextBlockLeadingView, number: Int, followsAppDirection: Bool) {
        marker.update(blockId: "numbered", style: .numbered(number))
        PinkhaTextBlockLeadingMarkerAdapter.applyNumberAlignment(
            context: followsAppDirection ? automaticContext : nil,
            content: BlockText.empty(contentType: .numbered).updated(number: number), to: marker)
    }

    private func firstLabel(in view: UIView) -> UILabel? {
        if let label = view as? UILabel { return label }
        return view.subviews.lazy.compactMap { firstLabel(in: $0) }.first
    }

    private func withWindow(isRTL: Bool, body: (UIViewController) throws -> Void) throws {
        let scene = try #require(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let previousKey = scene.windows.first(where: \.isKeyWindow)
        let window = UIWindow(windowScene: scene)
        let controller = UIViewController()
        controller.view.semanticContentAttribute = isRTL ? .forceRightToLeft : .forceLeftToRight
        window.rootViewController = controller
        window.makeKeyAndVisible()
        defer {
            window.isHidden = true
            window.rootViewController = nil
            previousKey?.makeKey()
        }
        try body(controller)
    }
}
