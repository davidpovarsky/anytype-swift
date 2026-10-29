import Testing
import SwiftUI
import UIKit
@testable import Anytype

@Suite("Pinkha navigation gesture bridge", .serialized)
@MainActor
struct PinkhaNavigationGestureBridgeTests {
    @Test("Application direction is the only bridge input and preserves original recognizers")
    func applicationDirectionPreservesOriginalRecognizers() throws {
        let controller = FullScreenSwipeNavigationController()
        controller.loadViewIfNeeded()
        controller.setViewControllers([UIViewController(), UIViewController()], animated: false)

        let edgeRecognizer = try #require(controller.interactivePopGestureRecognizer)
        let originalEdgeEnabled = edgeRecognizer.isEnabled
        let originalEdgeDelegate = edgeRecognizer.delegate
        let originalFullScreenRecognizer = try #require(fullScreenRecognizer(in: controller))
        let originalContentRecognizer: UIGestureRecognizer?
        let originalContentEnabled: Bool?
        if #available(iOS 26.0, *) {
            originalContentRecognizer = controller.interactiveContentPopGestureRecognizer
            originalContentEnabled = originalContentRecognizer?.isEnabled
        } else {
            originalContentRecognizer = nil
            originalContentEnabled = nil
        }

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            layoutDirection: .rightToLeft
        )

        #expect(controller.view.semanticContentAttribute == .forceRightToLeft)
        #expect(controller.view.effectiveUserInterfaceLayoutDirection == .rightToLeft)
        #expect(edgeRecognizer.isEnabled == originalEdgeEnabled)
        #expect(edgeRecognizer.delegate === originalEdgeDelegate)
        #expect(controller.view.gestureRecognizers?.contains {
            $0 === originalFullScreenRecognizer
        } == true)
        if #available(iOS 26.0, *) {
            if let originalContentRecognizer {
                #expect(controller.interactiveContentPopGestureRecognizer === originalContentRecognizer)
            } else {
                #expect(controller.interactiveContentPopGestureRecognizer == nil)
            }
            #expect(controller.interactiveContentPopGestureRecognizer?.isEnabled == originalContentEnabled)
        }

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            layoutDirection: .leftToRight
        )

        #expect(controller.view.semanticContentAttribute == .forceLeftToRight)
        #expect(controller.view.effectiveUserInterfaceLayoutDirection == .leftToRight)
        #expect(edgeRecognizer.isEnabled == originalEdgeEnabled)
        #expect(controller.view.gestureRecognizers?.contains {
            $0 === originalFullScreenRecognizer
        } == true)
    }

    @Test("Live stack depth and effective direction decide original full-screen eligibility")
    func liveStackAndDirectionDecideEligibility() {
        let controller = FullScreenSwipeNavigationController()
        controller.loadViewIfNeeded()
        let rightwardPan = TranslationPanGestureRecognizer(translation: CGPoint(x: 32, y: 0))
        let leftwardPan = TranslationPanGestureRecognizer(translation: CGPoint(x: -32, y: 0))

        controller.setViewControllers([UIViewController()], animated: false)
        PinkhaNavigationGestureBridge.update(
            controller: controller,
            layoutDirection: .leftToRight
        )
        #expect(!controller.gestureRecognizerShouldBegin(rightwardPan))

        controller.pushViewController(UIViewController(), animated: false)
        #expect(controller.gestureRecognizerShouldBegin(rightwardPan))
        #expect(!controller.gestureRecognizerShouldBegin(leftwardPan))

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            layoutDirection: .rightToLeft
        )
        #expect(!controller.gestureRecognizerShouldBegin(rightwardPan))
        #expect(controller.gestureRecognizerShouldBegin(leftwardPan))
    }

    @Test("Progress follows effective application direction without document gates")
    func progressFollowsEffectiveDirection() {
        let controller = FullScreenSwipeNavigationController()
        controller.loadViewIfNeeded()

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            layoutDirection: .leftToRight
        )
        #expect(PinkhaNavigationGestureBridge.normalizedProgress(
            controller: controller,
            translationX: 80,
            containerWidth: 320
        ) == 0.25)

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            layoutDirection: .rightToLeft
        )
        #expect(PinkhaNavigationGestureBridge.normalizedProgress(
            controller: controller,
            translationX: -80,
            containerWidth: 320
        ) == 0.25)
    }

    private func fullScreenRecognizer(
        in controller: FullScreenSwipeNavigationController
    ) -> UIPanGestureRecognizer? {
        controller.view.gestureRecognizers?.first {
            $0 !== controller.interactivePopGestureRecognizer &&
            $0.delegate === controller &&
            $0 is UIPanGestureRecognizer
        } as? UIPanGestureRecognizer
    }
}

private final class TranslationPanGestureRecognizer: UIPanGestureRecognizer {
    private let reportedTranslation: CGPoint

    init(translation: CGPoint) {
        reportedTranslation = translation
        super.init(target: nil, action: nil)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func translation(in view: UIView?) -> CGPoint {
        reportedTranslation
    }
}
