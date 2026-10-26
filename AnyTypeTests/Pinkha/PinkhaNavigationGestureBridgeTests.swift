import Testing
import SwiftUI
import UIKit
@testable import Anytype

@Suite("Pinkha navigation gesture bridge")
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

        PinkhaNavigationGestureBridge.setPinkhaWritingDocument(
            id: objectId,
            isPinkhaWritingDocument: true
        )
        #expect(PinkhaNavigationGestureBridge.requiresPublicEdgePop(controller: controller))
        #expect(controller.view.semanticContentAttribute == .forceRightToLeft)
        #expect(systemEdgeRecognizer(in: controller)?.edges == .right)

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: item,
            layoutDirection: .leftToRight
        )
        #expect(!PinkhaNavigationGestureBridge.requiresPublicEdgePop(controller: controller))
        #expect(controller.view.semanticContentAttribute == .unspecified)
        #expect(systemEdgeRecognizer(in: controller)?.edges == .left)

        PinkhaNavigationGestureBridge.setPinkhaWritingDocument(
            id: objectId,
            isPinkhaWritingDocument: false
        )
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
        fullScreenRecognizer.setTranslation(CGPoint(x: 40, y: 0), in: controller.view)
        #expect(controller.gestureRecognizerShouldBegin(fullScreenRecognizer))

        let objectId = "pinkha-public-edge-test"
        let item = editorItem(objectId: objectId)
        PinkhaNavigationGestureBridge.setPinkhaWritingDocument(
            id: objectId,
            isPinkhaWritingDocument: true
        )
        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: item,
            layoutDirection: .rightToLeft
        )

        #expect(!controller.gestureRecognizerShouldBegin(fullScreenRecognizer))
        #expect(systemRecognizer.edges == .right)
        #expect(systemRecognizer.delegate === originalSystemDelegate)
        #expect(systemRecognizer.cancelsTouchesInView == originalCancelsTouches)
        #expect(controller.view.gestureRecognizers?.count == originalGestureCount)

        PinkhaNavigationGestureBridge.update(
            controller: controller,
            topNavigationItem: item,
            layoutDirection: .leftToRight
        )
        #expect(controller.gestureRecognizerShouldBegin(fullScreenRecognizer))
        #expect(systemRecognizer.edges == .left)

        PinkhaNavigationGestureBridge.setPinkhaWritingDocument(
            id: objectId,
            isPinkhaWritingDocument: false
        )
    }

    @Test("Root, ordinary documents, and non-editor inspector destinations preserve host behavior")
    func rootAndNonPinkhaControls() {
        let controller = FullScreenSwipeNavigationController()
        controller.loadViewIfNeeded()
        let originalEdges = systemEdgeRecognizer(in: controller)?.edges
        let pan = UIPanGestureRecognizer()
        pan.setTranslation(CGPoint(x: 32, y: 0), in: controller.view)

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

        pan.setTranslation(CGPoint(x: -32, y: 0), in: controller.view)
        #expect(!controller.gestureRecognizerShouldBegin(pan))
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

        PinkhaNavigationGestureBridge.setPinkhaWritingDocument(
            id: objectId,
            isPinkhaWritingDocument: true
        )
        #expect(PinkhaNavigationGestureBridge.normalizedProgress(
            controller: controller,
            translationX: -80,
            containerWidth: 320
        ) == 0.25)

        PinkhaNavigationGestureBridge.setPinkhaWritingDocument(
            id: objectId,
            isPinkhaWritingDocument: false
        )
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
