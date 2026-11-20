import Services
import UIKit
import AnytypeCore

struct SimpleTableDependenciesContainer {
    let stateManager: SimpleTableStateManager
    let viewModel: SimpleTableViewModel
}

@MainActor
final class SimpleTableDependenciesBuilder {
    let cursorManager: EditorCursorManager
    
    private let document: any BaseDocumentProtocol
    private let router: any EditorRouterProtocol
    private let handler: any BlockActionHandlerProtocol
    private let markdownListener: any MarkdownListener
    private let focusSubjectHolder: FocusSubjectsHolder
    private let responderScrollViewHelper: ResponderScrollViewHelper
    private let accessoryStateManager: any AccessoryViewStateManager
    private weak var moduleOutput: (any EditorPageModuleOutput)?
    
    private let tableService: any BlockTableServiceProtocol
    private let pasteboardService: any PasteboardBlockDocumentServiceProtocol
    private let defaultObjectService: any DefaultObjectCreationServiceProtocol
    private let typesService: any TypesServiceProtocol
    
    weak var mainEditorSelectionManager: (any SimpleTableSelectionHandler)?
    
    init(
        document: some BaseDocumentProtocol,
        router: some EditorRouterProtocol,
        handler: some BlockActionHandlerProtocol,
        markdownListener: some MarkdownListener,
        focusSubjectHolder: FocusSubjectsHolder,
        mainEditorSelectionManager: (any SimpleTableSelectionHandler)?,
        responderScrollViewHelper: ResponderScrollViewHelper,
        accessoryStateManager: some AccessoryViewStateManager,
        moduleOutput: (any EditorPageModuleOutput)?,
        dependencies: SimpleTableServiceDependencies = .original()
    ) {
        self.document = document
        self.router = router
        self.handler = handler
        self.markdownListener = markdownListener
        self.focusSubjectHolder = focusSubjectHolder
        self.mainEditorSelectionManager = mainEditorSelectionManager
        self.responderScrollViewHelper = responderScrollViewHelper
        self.accessoryStateManager = accessoryStateManager
        self.moduleOutput = moduleOutput
        self.tableService = dependencies.tableService
        self.pasteboardService = dependencies.pasteboardService
        self.defaultObjectService = dependencies.defaultObjectService
        self.typesService = dependencies.typesService
        
        self.cursorManager = EditorCursorManager(focusSubjectHolder: focusSubjectHolder)
    }

    func buildDependenciesContainer(blockInformation: BlockInformation) -> SimpleTableDependenciesContainer {
        let blockInformationProvider = BlockModelInfomationProvider(document: document, info: blockInformation)
        
        let selectionOptionHandler = SimpleTableSelectionOptionHandler(
            router: router,
            tableService: tableService,
            document: document,
            blockInformationProvider: blockInformationProvider,
            actionHandler: handler
        )

        let stateManager = SimpleTableStateManager(
            document: document,
            blockInformationProvider: blockInformationProvider,
            selectionOptionHandler: selectionOptionHandler,
            router: router,
            cursorManager: cursorManager,
            mainEditorSelectionManager: mainEditorSelectionManager
        )

        let cellsBuilder = SimpleTableCellsBuilder(
            document: document,
            router: router,
            handler: handler,
            pasteboardService: pasteboardService,
            markdownListener: markdownListener,
            cursorManager: cursorManager,
            focusSubjectHolder: focusSubjectHolder,
            responderScrollViewHelper: responderScrollViewHelper, 
            stateManager: stateManager,
            accessoryStateManager: accessoryStateManager,
            blockMarkupChanger: BlockMarkupChanger(),
            blockTableService: tableService,
            moduleOutput: moduleOutput
        )

        let viewModel = SimpleTableViewModel(
            document: document,
            tableBlockInfoProvider: BlockModelInfomationProvider(document: document, info: blockInformation),
            cellBuilder: cellsBuilder,
            stateManager: stateManager,
            cursorManager: cursorManager
        )

        return .init(stateManager: stateManager, viewModel: viewModel)
    }
}
