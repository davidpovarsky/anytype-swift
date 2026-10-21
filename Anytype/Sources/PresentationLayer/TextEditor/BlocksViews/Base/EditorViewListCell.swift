import UIKit

final class EditorViewListCell: UICollectionViewListCell, CustomTypesAccessable {
    private var torahAccessory: UICellAccessory?

    func setTorahAccessory(_ accessory: UICellAccessory?) {
        var updatedAccessories = accessories
        if let torahAccessory {
            updatedAccessories.removeAll { $0 == torahAccessory }
        }
        if let accessory {
            updatedAccessories.append(accessory)
        }
        torahAccessory = accessory
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
