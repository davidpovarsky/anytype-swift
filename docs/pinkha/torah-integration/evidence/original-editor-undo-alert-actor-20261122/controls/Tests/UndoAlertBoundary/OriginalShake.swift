import Foundation

@MainActor
final class EditorPageViewModel {
    let router: any EditorRouterProtocol
    let actionHandler: any BlockActionHandlerProtocol
    let objectActionsService: any ObjectActionsServiceProtocol
    let document: any BaseDocumentProtocol
    init(router: any EditorRouterProtocol, actionHandler: any BlockActionHandlerProtocol,
         objectActionsService: any ObjectActionsServiceProtocol, document: any BaseDocumentProtocol) {
        self.router = router
        self.actionHandler = actionHandler
        self.objectActionsService = objectActionsService
        self.document = document
    }
    func shakeMotionDidAppear() {
        router.showAlert(
            alertModel: .undoAlertModel(
                undoAction: { [weak self] in
                    guard let self = self else { return }
                    self.actionHandler.scheduleMutationTask {
                        try await self.objectActionsService.undo(objectId: self.document.objectId)
                    }
                }
            )
        )
    }
}
