import Foundation

enum TorahEditorDropOperation: Equatable {
    case copy
    case move
    case forbidden
}

enum TorahEditorSafetyPolicy {
    static func mutationIsAuthorized(
        disposableSpaceConfirmed: Bool,
        freshDocumentConfirmed: Bool,
        confirmation: String
    ) -> Bool {
        disposableSpaceConfirmed
            && freshDocumentConfirmed
            && confirmation.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() == "DISPOSABLE"
    }

    static func dropOperation(
        containsTorahSource: Bool,
        mutationIsAuthorized: Bool,
        canPlace: Bool
    ) -> TorahEditorDropOperation {
        guard canPlace else { return .forbidden }
        if containsTorahSource {
            return mutationIsAuthorized ? .copy : .forbidden
        }
        return .move
    }
}
