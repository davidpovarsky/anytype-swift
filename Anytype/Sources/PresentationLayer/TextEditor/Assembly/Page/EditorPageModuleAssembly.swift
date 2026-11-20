import Foundation
import SwiftUI
import Services

@MainActor
protocol EditorPageModuleAssemblyProtocol: AnyObject {
    func buildStateModel(
        data: EditorPageObject,
        output: (any EditorPageModuleOutput)?,
        showHeader: Bool,
        torahSession: TorahEditorSession?
    ) -> EditorPageViewState

    func buildStateModel(
        data: EditorPageObject,
        preparedDocument: any BaseDocumentProtocol,
        output: (any EditorPageModuleOutput)?,
        showHeader: Bool,
        torahSession: TorahEditorSession?
    ) throws -> EditorPageViewState

    func buildStateModel(
        data: EditorPageObject,
        preparedDocument: any BaseDocumentProtocol,
        services: EditorPageServiceDependencies,
        output: (any EditorPageModuleOutput)?,
        showHeader: Bool,
        torahSession: TorahEditorSession?
    ) throws -> EditorPageViewState
}

@MainActor
final class EditorPageModuleAssembly: EditorPageModuleAssemblyProtocol {
    
    @Injected(\.openedDocumentProvider)
    private var documentService: any OpenedDocumentsProviderProtocol
    
    nonisolated init() {}
    
    func buildStateModel(
        data: EditorPageObject,
        output: (any EditorPageModuleOutput)?,
        showHeader: Bool,
        torahSession: TorahEditorSession?
    ) -> EditorPageViewState {
        assembleStateModel(
            data: data,
            output: output,
            showHeader: showHeader,
            torahSession: torahSession,
            services: nil,
            resolveDocument: {
                documentService.document(
                    objectId: data.objectId,
                    spaceId: data.spaceId,
                    mode: data.mode
                )
            }
        )
    }

    func buildStateModel(
        data: EditorPageObject,
        preparedDocument: any BaseDocumentProtocol,
        output: (any EditorPageModuleOutput)?,
        showHeader: Bool,
        torahSession: TorahEditorSession?
    ) throws -> EditorPageViewState {
        try PreparedEditorPageDocument.validate(data: data, document: preparedDocument)
        return assembleStateModel(
            data: data,
            output: output,
            showHeader: showHeader,
            torahSession: torahSession,
            services: nil,
            resolveDocument: { preparedDocument }
        )
    }

    func buildStateModel(
        data: EditorPageObject,
        preparedDocument: any BaseDocumentProtocol,
        services: EditorPageServiceDependencies,
        output: (any EditorPageModuleOutput)?,
        showHeader: Bool,
        torahSession: TorahEditorSession?
    ) throws -> EditorPageViewState {
        try PreparedEditorPageDocument.validate(data: data, document: preparedDocument)
        return assembleStateModel(
            data: data,
            output: output,
            showHeader: showHeader,
            torahSession: torahSession,
            services: services,
            resolveDocument: { preparedDocument }
        )
    }

    private func assembleStateModel(
        data: EditorPageObject,
        output: (any EditorPageModuleOutput)?,
        showHeader: Bool,
        torahSession: TorahEditorSession?,
        services: EditorPageServiceDependencies?,
        resolveDocument: @MainActor () -> any BaseDocumentProtocol
    ) -> EditorPageViewState {
        let simpleTableMenuViewModel = SimpleTableMenuViewModel()
        let blocksOptionViewModel = SelectionOptionsViewModel(itemProvider: nil)
        
        let blocksSelectionOverlayView = buildBlocksSelectionOverlayView(
            simleTableMenuViewModel: simpleTableMenuViewModel,
            blockOptionsViewViewModel: blocksOptionViewModel
        )

        let bottomNavigationManager = EditorBottomNavigationManager()
        
        let controller = EditorPageController(
            blocksSelectionOverlayView: blocksSelectionOverlayView,
            bottomNavigationManager: bottomNavigationManager,
            showHeader: showHeader
        )

        let document = resolveDocument()
        let router = EditorRouter(
            viewController: controller,
            document: document,
            output: output,
            dependencies: services?.router ?? .original()
        )

        let viewModel = buildViewModel(
            scrollView: controller.collectionView,
            viewInput: controller,
            document: document,
            router: router,
            blocksOptionViewModel: blocksOptionViewModel,
            simpleTableMenuViewModel: simpleTableMenuViewModel,
            blocksSelectionOverlayViewModel: blocksSelectionOverlayView.viewModel,
            bottomNavigationManager: bottomNavigationManager,
            configuration: EditorPageViewModelConfiguration(
                blockId: data.blockId,
                usecase: data.usecase,
                quickCapture: data.quickCapture,
                headerHint: data.headerHint
            ),
            torahSession: torahSession,
            output: output,
            services: services
        )

        bottomNavigationManager.output = viewModel

        controller.viewModel = viewModel
        
        return EditorPageViewState(viewController: controller, model: viewModel)
    }
    
    private func buildViewModel(
        scrollView: UIScrollView,
        viewInput: some EditorPageViewInput,
        document: some BaseDocumentProtocol,
        router: EditorRouter,
        blocksOptionViewModel: SelectionOptionsViewModel,
        simpleTableMenuViewModel: SimpleTableMenuViewModel,
        blocksSelectionOverlayViewModel: BlocksSelectionOverlayViewModel,
        bottomNavigationManager: some EditorBottomNavigationManagerProtocol,
        configuration: EditorPageViewModelConfiguration,
        torahSession: TorahEditorSession?,
        output: (any EditorPageModuleOutput)?,
        services: EditorPageServiceDependencies?
    ) -> EditorPageViewModel {
        let modelsHolder = EditorMainItemModelsHolder()
        let markupChanger = BlockMarkupChanger()
        let focusSubjectHolder = FocusSubjectsHolder()
        let rowIdentityMap = BlockRowIdentityMap()
        let blockCollectionController = EditorBlockCollectionController(viewInput: viewInput)

        let cursorManager = EditorCursorManager(
            focusSubjectHolder: focusSubjectHolder,
            focusPolicy: configuration.quickCapture ? .continueWriting : .firstEmptyTextBlock
        )
        let forkRebinder = BlockForkRebinder(
            modelsHolder: modelsHolder,
            rowIdentityMap: rowIdentityMap,
            infoContainer: document.infoContainer,
            focusSubjectHolder: focusSubjectHolder,
            cursorManager: cursorManager,
            collectionController: blockCollectionController
        )
        let blockActionService = BlockActionService(
            documentId: document.objectId,
            modelsHolder: modelsHolder,
            cursorManager: cursorManager,
            dependencies: services?.blockActionService ?? .original(),
            localEvents: services?.localEvents ?? OriginalEditorLocalEventPublisher()
        )
        let keyboardHandler = KeyboardActionHandler(
            documentId: document.objectId,
            spaceId: document.spaceId,
            service: blockActionService,
            toggleStorage: ToggleStorage.shared,
            container: document.infoContainer,
            modelsHolder: modelsHolder,
            editorCollectionController: .init(viewInput: viewInput),
            dependencies: services?.keyboardHandler ?? .original()
        )
        
        let actionHandler = BlockActionHandler(
            document: document,
            markupChanger: markupChanger,
            service: blockActionService,
            dependencies: services?.blockActionHandler ?? .original(),
            localEvents: services?.localEvents ?? OriginalEditorLocalEventPublisher()
        )
        
        let blocksStateManager = EditorPageBlocksStateManager(
            document: document,
            modelsHolder: modelsHolder,
            blocksSelectionOverlayViewModel: blocksSelectionOverlayViewModel,
            actionHandler: actionHandler,
            router: router,
            initialEditingState: document.mode.isHandling ? .editing : .readonly,
            viewInput: viewInput,
            bottomNavigationManager: bottomNavigationManager,
            torahSession: torahSession,
            dependencies: services?.blocksStateManager ?? .original()
        )
 
        let accessoryState = AccessoryViewBuilder.accessoryState(
            actionHandler: actionHandler,
            router: router,
            document: document,
            quickCapture: configuration.quickCapture
        )
        
        let markdownListener = MarkdownListenerImpl(
            internalListeners: [
                BeginingOfTextMarkdownListener(),
                InlineMarkdownListener()
            ]
        )
        
        let headerModel = ObjectHeaderViewModel(
            document: document,
            targetObjectId: document.objectId,
            configuration: configuration,
            output: output,
            dependencies: services?.header ?? .original()
        )
        setupHeaderModelActions(headerModel: headerModel, using: router)
        
        let responderScrollViewHelper = ResponderScrollViewHelper(scrollView: scrollView)
        
        let simpleTableDependenciesBuilder = SimpleTableDependenciesBuilder(
            document: document,
            router: router,
            handler: actionHandler,
            markdownListener: markdownListener,
            focusSubjectHolder: focusSubjectHolder,
            mainEditorSelectionManager: blocksStateManager,
            responderScrollViewHelper: responderScrollViewHelper,
            accessoryStateManager: accessoryState.0,
            moduleOutput: output,
            dependencies: services?.simpleTable ?? .original()
        )
        
        let mediaBlockActionsProvider = MediaBlockActionsProvider(
            handler: actionHandler,
            router: router
        )
        
        let slashMenuActionHandler = SlashMenuActionHandler(
            document: document,
            actionHandler: actionHandler,
            router: router,
            cursorManager: cursorManager,
            mediaBlockActionsProvider: mediaBlockActionsProvider,
            dependencies: services?.slashMenu ?? .original()
        )
        
        let blocksConverter = BlockViewModelBuilder(
            document: document,
            handler: actionHandler,
            router: router,
            markdownListener: markdownListener,
            simpleTableDependenciesBuilder: simpleTableDependenciesBuilder,
            subjectsHolder: focusSubjectHolder,
            infoContainer: document.infoContainer,
            modelsHolder: modelsHolder,
            rowIdentityMap: rowIdentityMap,
            forkRebinder: forkRebinder,
            blockCollectionController: blockCollectionController,
            accessoryStateManager: accessoryState.0,
            cursorManager: cursorManager,
            keyboardActionHandler: keyboardHandler,
            markupChanger: BlockMarkupChanger(),
            slashMenuActionHandler: slashMenuActionHandler,
            mediaBlockActionsProvider: mediaBlockActionsProvider,
            editorPageBlocksStateManager: blocksStateManager,
            torahSession: torahSession,
            output: output,
            dependencies: services?.blockBuilder ?? .original()
        )
        
        blocksStateManager.blocksSelectionOverlayViewModel = blocksSelectionOverlayViewModel
        blocksStateManager.blocksOptionViewModel = blocksOptionViewModel
        
        let editorPageTemplatesHandler = EditorPageTemplatesHandler()
        
        let viewModel = EditorPageViewModel(
            document: document,
            viewInput: viewInput,
            router: router,
            modelsHolder: modelsHolder,
            blockBuilder: blocksConverter,
            forkRebinder: forkRebinder,
            actionHandler: actionHandler,
            headerModel: headerModel,
            blocksStateManager: blocksStateManager,
            cursorManager: cursorManager,
            editorPageTemplatesHandler: editorPageTemplatesHandler,
            configuration: configuration,
            blockActionService: blockActionService,
            torahSession: torahSession,
            output: output,
            dependencies: services?.viewModel ?? .original()
        )

        accessoryState.1.onTypeSelected = { [weak viewModel] typeSelection in
            Task {
                try await viewModel?.onChangeType(typeSelection: typeSelection)
            }
        }

        return viewModel
    }
    
    private func buildBlocksSelectionOverlayView(
        simleTableMenuViewModel: SimpleTableMenuViewModel,
        blockOptionsViewViewModel: SelectionOptionsViewModel
    ) -> BlocksSelectionOverlayView {
        let blocksOptionView = SelectionOptionsView(viewModel: blockOptionsViewViewModel)
        let blocksSelectionOverlayViewModel = BlocksSelectionOverlayViewModel()
        
        return BlocksSelectionOverlayView(
            viewModel: blocksSelectionOverlayViewModel,
            blocksOptionView: blocksOptionView,
            simpleTablesOptionView: SimpleTableMenuView(viewModel: simleTableMenuViewModel)
        )
    }
    
    private func setupHeaderModelActions(headerModel: ObjectHeaderViewModel, using router: some ObjectHeaderRouterProtocol) {
        headerModel.onIconPickerTap = { [weak router] document in
            router?.showIconPicker(document: document)
        }
    }
}

