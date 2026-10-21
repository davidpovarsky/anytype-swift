import UIKit

final class EditorViewListCell: UICollectionViewListCell, CustomTypesAccessable {
    private var torahAccessoryIndex: Int?

    func setTorahAccessory(_ accessory: UICellAccessory?) {
        var updatedAccessories = accessories
        if let torahAccessoryIndex,
           updatedAccessories.indices.contains(torahAccessoryIndex) {
            updatedAccessories.remove(at: torahAccessoryIndex)
        }
        torahAccessoryIndex = nil
        if let accessory {
            torahAccessoryIndex = updatedAccessories.endIndex
            updatedAccessories.append(accessory)
        }
        accessories = updatedAccessories
    }

    override func prepareForReuse() {
        setTorahAccessory(nil)
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

        state.isMoving = isMoving
        state.isLocked = isLocked

        return state
    }
}
