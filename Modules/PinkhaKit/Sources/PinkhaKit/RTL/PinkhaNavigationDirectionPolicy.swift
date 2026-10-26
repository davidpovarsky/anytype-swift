import Foundation

public enum PinkhaPhysicalEdge: Sendable, Equatable {
    case left
    case right
}

public enum PinkhaNavigationDirectionPolicy {
    public static func backGestureStartEdge(
        layoutDirection: PinkhaLayoutDirection
    ) -> PinkhaPhysicalEdge {
        layoutDirection == .rightToLeft ? .right : .left
    }

    public static func backwardDistance(
        translationX: Double,
        layoutDirection: PinkhaLayoutDirection
    ) -> Double {
        switch layoutDirection {
        case .leftToRight:
            max(0, translationX)
        case .rightToLeft:
            max(0, -translationX)
        }
    }

    public static func normalizedBackProgress(
        translationX: Double,
        containerWidth: Double,
        layoutDirection: PinkhaLayoutDirection
    ) -> Double {
        guard containerWidth > 0 else { return 0 }
        return min(
            1,
            backwardDistance(
                translationX: translationX,
                layoutDirection: layoutDirection
            ) / containerWidth
        )
    }

    public static func shouldBeginBackGesture(
        navigationStackCount: Int,
        translationX: Double,
        translationY: Double,
        layoutDirection: PinkhaLayoutDirection,
        isTransitionInProgress: Bool,
        isInteractionBlocked: Bool
    ) -> Bool {
        guard navigationStackCount > 1 else { return false }
        guard !isTransitionInProgress, !isInteractionBlocked else { return false }
        guard abs(translationX) > abs(translationY) else { return false }
        return backwardDistance(
            translationX: translationX,
            layoutDirection: layoutDirection
        ) > 0
    }
}
