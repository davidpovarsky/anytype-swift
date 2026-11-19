import UIKit

final class EditorViewListCell: UICollectionViewListCell, CustomTypesAccessable {
    /// Apply this row's owner state before UIKit creates or reconfigures its content view.
    /// A reused cell's old lock must never cancel the new row's one-shot focus request.
    func setContentConfiguration(
        _ configuration: some UIContentConfiguration,
        isMoving: Bool,
        isLocked: Bool
    ) {
        self.isMoving = isMoving
        self.isLocked = isLocked
        contentConfiguration = configuration.updated(for: configurationState)
    }

    override func systemLayoutSizeFitting(_ targetSize: CGSize, withHorizontalFittingPriority horizontalFittingPriority: UILayoutPriority, verticalFittingPriority: UILayoutPriority) -> CGSize {
        let superSize = super.systemLayoutSizeFitting(
            targetSize,
            withHorizontalFittingPriority: .required,
            verticalFittingPriority: .fittingSizeLevel
        )
        
        return superSize
    }
    
    var isMoving: Bool = false {
        didSet {
            // Ensure that an update is performed whenever this property changes.
            if oldValue != isMoving {
                setNeedsUpdateConfiguration()
            }
        }
    }

    var isLocked: Bool = false {
        didSet {
            // Ensure that an update is performed whenever this property changes.
            if oldValue != isLocked {
                setNeedsUpdateConfiguration()
            }
        }
    }

    override var configurationState: UICellConfigurationState {
        var state = super.configurationState

        state.isMoving = isMoving
        state.isLocked = isLocked

        return state
    }
}
