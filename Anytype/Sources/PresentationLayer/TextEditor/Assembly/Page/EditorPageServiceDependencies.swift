@MainActor
struct EditorPageServiceDependencies {
    let blockActionService: BlockActionServiceDependencies
    let blockActionHandler: BlockActionHandlerDependencies
    let keyboardHandler: KeyboardActionHandlerDependencies
    let blocksStateManager: EditorPageBlocksStateManagerDependencies
    let blockBuilder: BlockViewModelBuilderDependencies
    let simpleTable: SimpleTableServiceDependencies
    let slashMenu: SlashMenuActionHandlerDependencies
    let header: ObjectHeaderViewModelDependencies
    let router: EditorRouterDependencies
    let viewModel: EditorPageViewModelDependencies
    let localEvents: any EditorLocalEventPublishing
}
