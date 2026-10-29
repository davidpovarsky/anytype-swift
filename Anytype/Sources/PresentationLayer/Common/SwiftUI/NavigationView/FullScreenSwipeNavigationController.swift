import UIKit

final class FullScreenSwipeNavigationController: UINavigationController, UIGestureRecognizerDelegate {

    /// Fraction of the screen width the in-flight back swipe has covered.
    var onInteractivePopProgress: ((CGFloat) -> Void)?

    /// The swipe ended without UIKit driving a transition, so nobody else will report an outcome.
    var onInteractivePopAborted: (() -> Void)?

    override public func viewDidLoad() {
        super.viewDidLoad()
        setupFullScreenSwipe()
    }

    func setupFullScreenSwipe() {
        // The system edge swipe drives the same transition, so it has to report progress too.
        interactivePopGestureRecognizer?.addTarget(self, action: #selector(handleBackSwipe))

        guard let target = interactivePopGestureRecognizer?.delegate else { return }

        let selector = NSSelectorFromString("handleNavigationTransition:")
        if target.responds(to: selector) {
            let panGestureRecognizer = UIPanGestureRecognizer(
                target: target,
                action: selector
            )
            // Added after UIKit's own target, so by the time this runs the transition has begun.
            panGestureRecognizer.addTarget(self, action: #selector(handleBackSwipe))
            panGestureRecognizer.delegate = self
            self.view.addGestureRecognizer(panGestureRecognizer)
        }
    }

    @objc private func handleBackSwipe(_ recognizer: UIPanGestureRecognizer) {
        switch recognizer.state {
        case .began, .changed:
            let width = view.bounds.width
            guard width > 0 else { return }
            onInteractivePopProgress?(PinkhaNavigationGestureBridge.normalizedProgress(
                controller: self,
                translationX: recognizer.translation(in: view).x,
                containerWidth: width
            ))
        case .ended, .cancelled, .failed:
            // A live transition reports its own outcome through the transition coordinator.
            if transitionCoordinator == nil {
                onInteractivePopAborted?()
            }
        default:
            break
        }
    }

    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard viewControllers.count > 1 else { return false }

        guard let panGestureRecognizer = gestureRecognizer as? UIPanGestureRecognizer else { return false }

        let translationX = panGestureRecognizer.translation(in: panGestureRecognizer.view).x
        switch view.effectiveUserInterfaceLayoutDirection {
        case .leftToRight:
            return translationX > 0
        case .rightToLeft:
            return translationX < 0
        @unknown default:
            return false
        }
    }
}
