import SwiftUI
import UIKit

@MainActor
enum PinkhaNavigationGestureBridge {
    static func update(
        controller: FullScreenSwipeNavigationController,
        layoutDirection: LayoutDirection
    ) {
        controller.view.semanticContentAttribute = layoutDirection == .rightToLeft
            ? .forceRightToLeft
            : .forceLeftToRight
        PinkhaStage1AcceptanceDiagnostics.record(
            layoutDirection: layoutDirection,
            navigationView: controller.view
        )
    }

    static func normalizedProgress(
        controller: FullScreenSwipeNavigationController,
        translationX: CGFloat,
        containerWidth: CGFloat
    ) -> CGFloat {
        switch controller.view.effectiveUserInterfaceLayoutDirection {
        case .leftToRight:
            return translationX / containerWidth
        case .rightToLeft:
            return -translationX / containerWidth
        @unknown default:
            return 0
        }
    }
}
