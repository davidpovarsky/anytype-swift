import Foundation

public struct TorahReaderScrollDecision: Equatable, Sendable {
    public let shouldLoadPrevious: Bool
    public let shouldLoadNext: Bool

    public static let idle = TorahReaderScrollDecision(shouldLoadPrevious: false, shouldLoadNext: false)
    public static let loadPrevious = TorahReaderScrollDecision(shouldLoadPrevious: true, shouldLoadNext: false)
    public static let loadNext = TorahReaderScrollDecision(shouldLoadPrevious: false, shouldLoadNext: true)
}

@MainActor
public final class TorahReaderScrollStateMachine {
    public private(set) var isInitialLoaded = false
    public private(set) var isLoadingPrevious = false
    public private(set) var isLoadingNext = false
    public private(set) var isRestoringAnchor = false
    public private(set) var isTopTriggerArmed = false
    public private(set) var lastOffsetY: CGFloat = 0

    public let topTriggerThreshold: CGFloat
    public let topArmingThreshold: CGFloat
    public let bottomTriggerThreshold: CGFloat

    public init(topTriggerThreshold: CGFloat = 40, topArmingThreshold: CGFloat = 80, bottomTriggerThreshold: CGFloat = 200) {
        self.topTriggerThreshold = topTriggerThreshold
        self.topArmingThreshold = topArmingThreshold
        self.bottomTriggerThreshold = bottomTriggerThreshold
    }

    public func onInitialLoadComplete(hasPrevious: Bool, hasNext: Bool, isUnderfilled: Bool) -> TorahReaderScrollDecision {
        isInitialLoaded = true
        isLoadingPrevious = false
        isLoadingNext = false
        isRestoringAnchor = false
        isTopTriggerArmed = false
        lastOffsetY = 0
        if isUnderfilled && hasNext {
            isLoadingNext = true
            return .loadNext
        }
        return .idle
    }

    public func onScrollOffsetChanged(
        offsetY: CGFloat,
        contentHeight: CGFloat,
        containerHeight: CGFloat,
        hasPrevious: Bool,
        hasNext: Bool
    ) -> TorahReaderScrollDecision {
        guard isInitialLoaded, !isRestoringAnchor else { return .idle }
        let isScrollingUp = offsetY < lastOffsetY
        let isScrollingDown = offsetY > lastOffsetY
        if offsetY >= topArmingThreshold { isTopTriggerArmed = true }
        defer { lastOffsetY = offsetY }
        let isNearTop = offsetY <= topTriggerThreshold
        let isPullingDownAtEdge = offsetY < -25
        if hasPrevious && !isLoadingPrevious
            && (isTopTriggerArmed && isScrollingUp && isNearTop || isPullingDownAtEdge) {
            isLoadingPrevious = true
            isTopTriggerArmed = false
            return .loadPrevious
        }
        let distanceToBottom = contentHeight - containerHeight - offsetY
        if hasNext && !isLoadingNext && isScrollingDown && distanceToBottom <= bottomTriggerThreshold {
            isLoadingNext = true
            return .loadNext
        }
        return .idle
    }

    public func onPreviousLoadCompleted() { isLoadingPrevious = false; isRestoringAnchor = true }
    public func onAnchorRestorationCompleted() { isRestoringAnchor = false; isTopTriggerArmed = false }
    public func onPreviousLoadFailed() { isLoadingPrevious = false; isRestoringAnchor = false; isTopTriggerArmed = false }
    public func onNextLoadCompleted(requiresAnchorRestoration: Bool = false) {
        isLoadingNext = false
        isRestoringAnchor = requiresAnchorRestoration
    }
    public func onNextLoadFailed() { isLoadingNext = false }
}
