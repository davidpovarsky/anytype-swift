public enum PinkhaTextDirectionMarker: Sendable, Equatable {
    case automatic(PinkhaLayoutDirection)
    case explicit(PinkhaParagraphAlignment)

    public init?(storedValue: String) {
        switch storedValue {
        case "automatic:ltr": self = .automatic(.leftToRight)
        case "automatic:rtl": self = .automatic(.rightToLeft)
        case "explicit:left": self = .explicit(.left)
        case "explicit:center": self = .explicit(.center)
        case "explicit:right": self = .explicit(.right)
        case "explicit:justified": self = .explicit(.justified)
        case "explicit:natural": self = .explicit(.natural)
        default: return nil
        }
    }

    public var storedValue: String {
        switch self {
        case .automatic(.leftToRight): "automatic:ltr"
        case .automatic(.rightToLeft): "automatic:rtl"
        case .explicit(.left): "explicit:left"
        case .explicit(.center): "explicit:center"
        case .explicit(.right): "explicit:right"
        case .explicit(.justified): "explicit:justified"
        case .explicit(.natural): "explicit:natural"
        }
    }
}

public enum PinkhaAutomaticDirectionEligibility {
    public static func shouldPersist(
        marker: PinkhaTextDirectionMarker?,
        isSessionCreatedBlock: Bool
    ) -> Bool {
        switch marker {
        case .explicit:
            false
        case .automatic:
            true
        case nil:
            isSessionCreatedBlock
        }
    }

    public static func markerMatchesStoredAlignment(
        marker: PinkhaTextDirectionMarker?,
        storedAlignment: PinkhaParagraphAlignment
    ) -> Bool {
        guard case let .automatic(direction) = marker else { return true }
        let expected: PinkhaParagraphAlignment = direction == .rightToLeft ? .right : .left
        return storedAlignment == expected
    }
}
