import Testing
import SwiftUI
import UIKit
@testable import Anytype

@Suite("Pinkha navigation gesture bridge", .serialized)
@MainActor
struct PinkhaNavigationGestureBridgeTests {
    @Test("Only an exact Pinkha document with active RTL interface requires edge pop")
    func exactDocumentAndActiveOverrideGate() {
        let controller = FullScreenSwipeNavigationController()
        controller.loadViewIfNeeded()
        let objectId = "pinkha-nav-test"
        let item = AnyHashable(EditorScreenData.page(EditorPageObject(
            objectId: objectId,
            spaceId: "space"
        )))

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: item,
            layoutDirection: .rightToLeft
        )
        #expect(!PinkhaNavigationGestureBridge.requiresPublicEdgePop(controller: controller))

        PinkhaDocumentIdentityStorage.shared.registerConfirmed(
            objectId: objectId,
            spaceId: "space"
        )
        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: item,
            layoutDirection: .rightToLeft
        )
        #expect(PinkhaNavigationGestureBridge.requiresPublicEdgePop(controller: controller))
        #expect(controller.view.semanticContentAttribute == .forceRightToLeft)
        #expect(controller.interactivePopGestureRecognizer?.isEnabled == false)
        if #available(iOS 26.0, *) {
            #expect(controller.interactiveContentPopGestureRecognizer?.isEnabled == true)
        }

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: item,
            layoutDirection: .leftToRight
        )
        #expect(!PinkhaNavigationGestureBridge.requiresPublicEdgePop(controller: controller))
        #expect(controller.view.semanticContentAttribute == .unspecified)
        #expect(controller.interactivePopGestureRecognizer?.isEnabled == true)
    }

    @Test("Pinkha RTL blocks only the custom recognizer and preserves UIKit's public transition driver")
    func publicEdgeDriverIsExclusive() throws {
        let controller = FullScreenSwipeNavigationController()
        controller.loadViewIfNeeded()
        controller.setViewControllers([UIViewController(), UIViewController()], animated: false)
        let systemRecognizer = try #require(systemEdgeRecognizer(in: controller))
        let originalSystemDelegate = systemRecognizer.delegate
        let originalCancelsTouches = systemRecognizer.cancelsTouchesInView
        let originalGestureCount = controller.view.gestureRecognizers?.count
        let fullScreenRecognizer = try #require(controller.view.gestureRecognizers?.first {
            $0 !== systemRecognizer && $0.delegate === controller && $0 is UIPanGestureRecognizer
        } as? UIPanGestureRecognizer)
        let positivePan = TranslationPanGestureRecognizer(translation: CGPoint(x: 40, y: 0))
        #expect(controller.gestureRecognizerShouldBegin(positivePan))

        let objectId = "pinkha-public-edge-test"
        let item = editorItem(objectId: objectId)
        PinkhaDocumentIdentityStorage.shared.registerConfirmed(
            objectId: objectId,
            spaceId: "space"
        )
        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: item,
            layoutDirection: .rightToLeft
        )

        #expect(!controller.gestureRecognizerShouldBegin(positivePan))
        #expect(!systemRecognizer.isEnabled)
        #expect(systemRecognizer.delegate === originalSystemDelegate)
        #expect(systemRecognizer.cancelsTouchesInView == originalCancelsTouches)
        #expect(controller.view.gestureRecognizers?.count == originalGestureCount)
        #expect(controller.view.gestureRecognizers?.contains { $0 === fullScreenRecognizer } == true)

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: item,
            layoutDirection: .leftToRight
        )
        #expect(controller.gestureRecognizerShouldBegin(positivePan))
        #expect(systemRecognizer.isEnabled)
    }

    @Test("Root, ordinary documents, and non-editor inspector destinations preserve host behavior")
    func rootAndNonPinkhaControls() {
        let controller = FullScreenSwipeNavigationController()
        controller.loadViewIfNeeded()
        let originalEdges = systemEdgeRecognizer(in: controller)?.edges
        let pan = TranslationPanGestureRecognizer(translation: CGPoint(x: 32, y: 0))

        controller.setViewControllers([UIViewController()], animated: false)
        #expect(!controller.gestureRecognizerShouldBegin(pan))

        controller.pushViewController(UIViewController(), animated: false)
        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: AnyHashable("inspector"),
            layoutDirection: .rightToLeft
        )
        #expect(controller.gestureRecognizerShouldBegin(pan))
        #expect(systemEdgeRecognizer(in: controller)?.edges == originalEdges)

        let reversePan = TranslationPanGestureRecognizer(translation: CGPoint(x: -32, y: 0))
        #expect(!controller.gestureRecognizerShouldBegin(reversePan))
    }

    @Test("RTL Pinkha progress is normalized while ordinary progress is unchanged")
    func progressGate() {
        let controller = FullScreenSwipeNavigationController()
        controller.loadViewIfNeeded()
        let objectId = "pinkha-progress-test"
        let item = AnyHashable(EditorScreenData.page(EditorPageObject(
            objectId: objectId,
            spaceId: "space"
        )))

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: item,
            layoutDirection: .rightToLeft
        )
        #expect(PinkhaNavigationGestureBridge.normalizedProgress(
            controller: controller,
            translationX: -80,
            containerWidth: 320
        ) == -0.25)

        PinkhaDocumentIdentityStorage.shared.registerConfirmed(
            objectId: objectId,
            spaceId: "space"
        )
        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: item,
            layoutDirection: .rightToLeft
        )
        #expect(PinkhaNavigationGestureBridge.normalizedProgress(
            controller: controller,
            translationX: -80,
            containerWidth: 320
        ) == 0.25)
    }

    private func editorItem(objectId: String) -> AnyHashable {
        AnyHashable(EditorScreenData.page(EditorPageObject(
            objectId: objectId,
            spaceId: "space"
        )))
    }

    private func systemEdgeRecognizer(
        in controller: FullScreenSwipeNavigationController
    ) -> UIScreenEdgePanGestureRecognizer? {
        controller.interactivePopGestureRecognizer as? UIScreenEdgePanGestureRecognizer
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
