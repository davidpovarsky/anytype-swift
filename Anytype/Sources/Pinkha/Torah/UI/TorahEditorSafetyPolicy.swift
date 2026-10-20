import Foundation

enum TorahEditorDropOperation: Equatable {
    case copy
    case move
    case forbidden
}

enum TorahEditorSafetyPolicy {
    static func dropOperation(
        containsTorahSource: Bool,
        canMutate: Bool,
        canPlace: Bool
    ) -> TorahEditorDropOperation {
        guard canMutate, canPlace else { return .forbidden }
        if containsTorahSource {
            return .copy
        }
        return .move
    }
}
