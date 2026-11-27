import PinkhaHanlinCore
import PinkhaHanlinUI
import Testing
import UIKit

#if os(iOS) && DEBUG
/// Real native permission-sheet layout only. This does not grant native write
/// authority or claim mounted application/engine acceptance.
@Suite("Hanlin complete-message confirmation controls", .serialized)
@MainActor
struct HanlinSaveMessageConsentLayoutTests {
    @Test(arguments: [false, true])
    func maximumBodyKeepsOriginalCancelAndAllowVisible(hebrew: Bool) throws {
        let body = hebrew ? String(repeating: "א", count: 32_768) : String(repeating: "x", count: 65_536)
        let explanation = "Title\nOriginal Space\n\n" + body
        let decision = PinkhaHanlinReadConsentDecision()
        var resolved: Bool?
        var authorityChecks = 0
        #expect(decision.begin { resolved = $0 })
        let controller = PinkhaHanlinUI.PinkhaHanlinConsentController(purpose: .saveMessage,
            title: hebrew ? "לשמור את ההודעה בדף חדש?" : "Save the message in a new page?",
            explanation: explanation, allowTitle: hebrew ? "שמירת ההודעה" : "Save message",
            cancelTitle: hebrew ? "ביטול" : "Cancel", decision: decision,
            validate: { authorityChecks += 1 })
        controller.loadViewIfNeeded()
        controller.view.frame = CGRect(x: 0, y: 0, width: 390, height: 844)
        controller.view.semanticContentAttribute = hebrew ? .forceRightToLeft : .forceLeftToRight
        controller.view.setNeedsLayout()
        controller.view.layoutIfNeeded()
        let nodes = descendants(controller.view)
        let allowNode = nodes.first { $0.accessibilityIdentifier == "pinkha.hanlin.consent.save-message.allow" }
        let cancelNode = nodes.first { $0.accessibilityIdentifier == "pinkha.hanlin.consent.save-message.cancel" }
        let messageNode = nodes.first { $0.accessibilityIdentifier == "pinkha.hanlin.consent.save-message.explanation" }
        let allow = try #require(allowNode as? UIButton)
        let cancel = try #require(cancelNode as? UIButton)
        let message = try #require(messageNode as? UILabel)
        let scroll = try #require(nodes.first { $0 is UIScrollView } as? UIScrollView)
        #expect(message.text?.utf8.elementsEqual(explanation.utf8) == true)
        #expect(message.numberOfLines == 0)
        for button in [allow, cancel] {
            let frame = button.convert(button.bounds, to: controller.view)
            #expect(controller.view.bounds.contains(frame) && frame.height >= 44)
        }
        #expect(scroll.contentSize.height > scroll.bounds.height)
        #expect(scroll.frame.maxY < allow.convert(allow.bounds, to: controller.view).minY)
        cancel.sendActions(for: .touchUpInside)
        #expect(resolved == false && !decision.authorized && authorityChecks == 0)
        allow.sendActions(for: .touchUpInside)
        #expect(resolved == false && !decision.authorized && authorityChecks == 0)
    }

    private func descendants(_ view: UIView) -> [UIView] {
        [view] + view.subviews.flatMap(descendants)
    }
}
#endif
