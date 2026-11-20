import Services

@MainActor
struct EditorRouterDependencies {
    let navigationContext: any NavigationContextProtocol
    let templatesCoordinator: any TemplatesCoordinatorProtocol
    let setObjectCreationSettingsCoordinator: any SetObjectCreationSettingsCoordinatorProtocol
    let toastPresenter: any ToastPresenterProtocol
    let templateService: any TemplatesServiceProtocol

    static func original() -> Self {
        Self(
            navigationContext: Container.shared.legacyNavigationContext(),
            templatesCoordinator: Container.shared.legacyTemplatesCoordinator(),
            setObjectCreationSettingsCoordinator: Container.shared.legacySetObjectCreationSettingsCoordinator(),
            toastPresenter: Container.shared.legacyToastPresenter(),
            templateService: Container.shared.templatesService()
        )
    }
}
