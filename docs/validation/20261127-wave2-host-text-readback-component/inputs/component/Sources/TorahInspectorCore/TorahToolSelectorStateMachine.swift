import Foundation

public enum TorahToolSelectorVisibility: Equatable, Sendable {
    case visible
    case collapsed
}

/// A direction-aware selector state machine with deliberately separated
/// thresholds so tiny scroll jitter cannot flap the toolbar.
public struct TorahToolSelectorStateMachine: Equatable, Sendable {
    public private(set) var visibility: TorahToolSelectorVisibility = .visible
    public private(set) var lastOffset: CGFloat = 0
    public let collapseDistance: CGFloat
    public let revealDistance: CGFloat
    private var downwardTravel: CGFloat = 0
    private var upwardTravel: CGFloat = 0

    public init(collapseDistance: CGFloat = 54, revealDistance: CGFloat = 28) {
        self.collapseDistance = collapseDistance
        self.revealDistance = revealDistance
    }

    public mutating func update(
        offset: CGFloat,
        contentHeight: CGFloat,
        viewportHeight: CGFloat
    ) -> TorahToolSelectorVisibility {
        guard contentHeight > viewportHeight + collapseDistance else {
            visibility = .visible
            resetTravel(at: offset)
            return visibility
        }
        if offset <= 8 {
            visibility = .visible
            resetTravel(at: offset)
            return visibility
        }
        let delta = offset - lastOffset
        if delta > 0 {
            downwardTravel += delta
            upwardTravel = 0
            if downwardTravel >= collapseDistance { visibility = .collapsed }
        } else if delta < 0 {
            upwardTravel += -delta
            downwardTravel = 0
            if upwardTravel >= revealDistance { visibility = .visible }
        }
        lastOffset = offset
        return visibility
    }

    public mutating func revealManually() {
        visibility = .visible
        downwardTravel = 0
        upwardTravel = 0
    }

    private mutating func resetTravel(at offset: CGFloat) {
        lastOffset = offset
        downwardTravel = 0
        upwardTravel = 0
    }
}
