import Foundation
import Services
import Combine
import TorahInspectorCore

@MainActor
protocol EditorPageViewModelProtocol: AnyObject {
    var blocksStateManager: any EditorPageBlocksStateManagerProtocol { get }

    var document: any BaseDocumentProtocol { get }
    
    var modelsHolder: EditorMainItemModelsHolder { get }
    var actionHandler: any BlockActionHandlerProtocol { get }
    
    var router: any EditorRouterProtocol { get }
    var torahSession: TorahEditorSession? { get }
    
    func viewDidLoad()
    func viewWillAppear()
    func viewDidAppear()
    func viewWillDisappear()
    func viewDidDissapear()

    func shakeMotionDidAppear()

    func didSelectBlock(at indexPath: IndexPath)
    func didFinishEditing(blockId: String)

    func setupSubscriptions()
    
    func showTemplates()
    
    func cursorFocus(blockId: String)
    
    func tapOnEmptyPlace(isBelowContent: Bool)
    
    func showSyncStatusInfo()

    func showWidgets()

    func onPublishingBannerTap()

    func torahDropTargetBlockId(at indexPath: IndexPath?) -> String?
    func insertExternalTorahSource(_ transfer: TorahSourceTransfer, targetBlockId: String?) async
}
