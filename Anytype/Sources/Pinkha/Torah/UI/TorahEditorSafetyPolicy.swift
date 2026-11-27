import Foundation

enum TorahEditorDropOperation: Equatable {
    case copy
    case move
    case forbidden
}

enum TorahEditorSafetyPolicy {
    /// A source quote needs authority for both text and canonical metadata.
    /// The preview and both dispatch guards must require the same authority.
    static func canInsertSource(
        canEditBlocks: Bool,
        canEditRelationValues: Bool,
        isReadonly: Bool?
    ) -> Bool {
        canEditBlocks && canEditRelationValues && isReadonly == false
    }

    static func dropOperation(
        containsTorahSource: Bool,
        canEditBlocks: Bool,
        canEditRelationValues: Bool,
        isReadonly: Bool?,
        canPlace: Bool
    ) -> TorahEditorDropOperation {
        let canMutate = containsTorahSource
            ? canInsertSource(
                canEditBlocks: canEditBlocks,
                canEditRelationValues: canEditRelationValues,
                isReadonly: isReadonly
            )
            : canEditBlocks
        return dropOperation(
            containsTorahSource: containsTorahSource,
            canMutate: canMutate,
            canPlace: canPlace
        )
    }

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
