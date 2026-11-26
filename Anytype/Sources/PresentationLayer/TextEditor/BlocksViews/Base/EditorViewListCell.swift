import UIKit

final class EditorViewListCell: UICollectionViewListCell, CustomTypesAccessable {
    private weak var owningCollectionView: UICollectionView?

    /// Apply this row's owner state before UIKit creates or reconfigures its content view.
    /// A reused cell's old lock must never cancel the new row's one-shot focus request.
    func setContentConfiguration(
        _ configuration: some UIContentConfiguration,
        in collectionView: UICollectionView,
        isMoving: Bool,
        isLocked: Bool
    ) {
        owningCollectionView = collectionView
        self.isMoving = isMoving
        self.isLocked = isLocked
        contentConfiguration = configuration.updated(for: configurationState)
    }

    /// Called by the owning collection's display lifecycle, after configuration.
    /// Nested text blocks retain their own cursor owner; no request is synthesized.
    func resumePendingTextFocusAfterDisplay() {
        guard let owningCollectionView, window != nil,
              window === owningCollectionView.window,
              owningCollectionView.indexPath(for: self) != nil else { return }
        var remaining = [contentView]
        while let view = remaining.popLast() {
            if let row = view as? TextBlockContentView {
                row.resumePendingFocusAfterDisplay()
            } else {
                remaining.append(contentsOf: view.subviews)
            }
        }
    }

    override func prepareForReuse() {
        owningCollectionView = nil
        super.prepareForReuse()
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

        if let owningCollectionView {
            state.isEditing = owningCollectionView.isEditing
        }
        state.isMoving = isMoving
        state.isLocked = isLocked

        return state
    }
}
