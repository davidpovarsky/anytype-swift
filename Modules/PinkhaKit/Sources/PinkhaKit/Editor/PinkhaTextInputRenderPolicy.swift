/// One rendering rule for every Pinkha editor. Native adapters decide whether a
/// local change is still pending; this policy does not guess from text prefixes
/// or pretend that an engine acknowledged a write.
public enum PinkhaTextInputRenderAction: Equatable, Sendable {
    case preserve
    case updateAttributes
    case replace
}

public enum PinkhaTextInputRenderPolicy {
    public static func action(
        incoming: String,
        live: String,
        isComposing: Bool,
        hasPendingLocalChanges: Bool
    ) -> PinkhaTextInputRenderAction {
        // Even an empty native snapshot must not destroy UIKit's marked buffer.
        if isComposing { return .preserve }
        // Swift String equality normalizes Unicode. Storage offsets do not: a
        // canonically equivalent string can still have different UTF-16 ranges.
        if incoming.utf8.elementsEqual(live.utf8) { return .updateAttributes }
        if hasPendingLocalChanges { return .preserve }
        return .replace
    }
}
