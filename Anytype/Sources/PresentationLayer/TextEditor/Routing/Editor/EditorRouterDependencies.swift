import Services

@MainActor
struct EditorRouterDependencies {
    let navigationContext: any NavigationContextProtocol
    let templatesCoordinator: any TemplatesCoordinatorProtocol
    let setObjectCreationSettingsCoordinator: any SetObjectCreationSettingsCoordinatorProtocol
    let toastPresenter: any ToastPresenterProtocol
    let templateService: any TemplatesServiceProtocol
    var documentWriteOwner: EditorDocumentWriteOwner? = nil

    static func original(navigationContext: (any NavigationContextProtocol)? = nil) -> Self {
        Self(
            navigationContext: navigationContext ?? Container.shared.legacyNavigationContext(),
            templatesCoordinator: Container.shared.legacyTemplatesCoordinator(),
            setObjectCreationSettingsCoordinator: Container.shared.legacySetObjectCreationSettingsCoordinator(),
            toastPresenter: Container.shared.legacyToastPresenter(),
            templateService: Container.shared.templatesService()
        )
    }
}
