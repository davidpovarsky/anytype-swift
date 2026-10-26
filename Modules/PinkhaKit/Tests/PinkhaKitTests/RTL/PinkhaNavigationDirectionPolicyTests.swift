import Testing
@testable import PinkhaKit

@Suite("Pinkha navigation direction policy")
struct PinkhaNavigationDirectionPolicyTests {
    @Test("Back starts at the semantic leading edge")
    func semanticBackEdge() {
        #expect(PinkhaNavigationDirectionPolicy.backGestureStartEdge(
            layoutDirection: .leftToRight
        ) == .left)
        #expect(PinkhaNavigationDirectionPolicy.backGestureStartEdge(
            layoutDirection: .rightToLeft
        ) == .right)
    }

    @Test("Back progress normalizes the correct physical direction")
    func directionAwareProgress() {
        #expect(PinkhaNavigationDirectionPolicy.normalizedBackProgress(
            translationX: 80,
            containerWidth: 320,
            layoutDirection: .leftToRight
        ) == 0.25)
        #expect(PinkhaNavigationDirectionPolicy.normalizedBackProgress(
            translationX: -80,
            containerWidth: 320,
            layoutDirection: .rightToLeft
        ) == 0.25)
        #expect(PinkhaNavigationDirectionPolicy.normalizedBackProgress(
            translationX: 80,
            containerWidth: 320,
            layoutDirection: .rightToLeft
        ) == 0)
        #expect(PinkhaNavigationDirectionPolicy.normalizedBackProgress(
            translationX: 640,
            containerWidth: 320,
            layoutDirection: .leftToRight
        ) == 1)
    }

    @Test("Gesture begins only for an available horizontal back transition")
    func beginGuards() {
        #expect(shouldBegin(stackCount: 2, x: 50, y: 5, direction: .leftToRight))
        #expect(shouldBegin(stackCount: 2, x: -50, y: 5, direction: .rightToLeft))
        #expect(!shouldBegin(stackCount: 1, x: 50, y: 5, direction: .leftToRight))
        #expect(!shouldBegin(stackCount: 2, x: -50, y: 5, direction: .leftToRight))
        #expect(!shouldBegin(stackCount: 2, x: 5, y: 50, direction: .leftToRight))
        #expect(!shouldBegin(
            stackCount: 2,
            x: 50,
            y: 5,
            direction: .leftToRight,
            isTransitionInProgress: true
        ))
        #expect(!shouldBegin(
            stackCount: 2,
            x: 50,
            y: 5,
            direction: .leftToRight,
            isInteractionBlocked: true
        ))
    }

    @Test("Zero-width containers never report progress")
    func invalidContainerWidth() {
        #expect(PinkhaNavigationDirectionPolicy.normalizedBackProgress(
            translationX: 80,
            containerWidth: 0,
            layoutDirection: .leftToRight
        ) == 0)
    }

    private func shouldBegin(
        stackCount: Int,
        x: Double,
        y: Double,
        direction: PinkhaLayoutDirection,
        isTransitionInProgress: Bool = false,
        isInteractionBlocked: Bool = false
    ) -> Bool {
        PinkhaNavigationDirectionPolicy.shouldBeginBackGesture(
            navigationStackCount: stackCount,
            translationX: x,
            translationY: y,
            layoutDirection: direction,
            isTransitionInProgress: isTransitionInProgress,
            isInteractionBlocked: isInteractionBlocked
        )
    }
}
