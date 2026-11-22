import UIKit
import Services
import SwiftUI
import AnytypeCore

@MainActor
protocol SetObjectCreationSettingsCoordinatorProtocol: AnyObject, SetObjectCreationSettingsOutput {
    func showTemplateEditing(
        setting: ObjectCreationSetting,
        onTemplateSelection: (() -> Void)?,
        onSetAsDefaultTemplate: @escaping (String) -> Void,
        completion: (() -> Void)?
    )
}

@MainActor
final class SetObjectCreationSettingsCoordinator:
    SetObjectCreationSettingsCoordinatorProtocol,
    ObjectSettingsCoordinatorOutput,
    SetObjectCreationSettingsOutput
{
    @Injected(\.legacyNavigationContext)
    private var navigationContext: any NavigationContextProtocol
    @Injected(\.legacyToastPresenter)
    private var toastPresenter: any ToastPresenterProtocol
    
    private var useAsTemplateAction: ((String) -> Void)?
    private let ownedNavigationContext: (any NavigationContextProtocol)?
    private let documentWriteOwner: EditorDocumentWriteOwner?
    private let childPreparation: PreparedEditorChildPreparation?
    private let ownedContextId: String?

    private var activeNavigationContext: any NavigationContextProtocol {
        ownedNavigationContext ?? navigationContext
    }

    nonisolated init() {
        ownedNavigationContext = nil
        documentWriteOwner = nil
        childPreparation = nil
        ownedContextId = nil
    }

    private init(owner: EditorDocumentWriteOwner, childPreparation: PreparedEditorChildPreparation,
                 navigationContext: any NavigationContextProtocol, contextId: String) {
        self.documentWriteOwner = owner
        self.childPreparation = childPreparation
        self.ownedNavigationContext = navigationContext
        self.ownedContextId = contextId
    }

    static func bindOriginal(_ service: any SetObjectCreationSettingsCoordinatorProtocol,
                             owner: EditorDocumentWriteOwner,
                             childPreparation: PreparedEditorChildPreparation,
                             navigationContext: any NavigationContextProtocol,
                             contextId: String) throws -> any SetObjectCreationSettingsCoordinatorProtocol {
        guard service is SetObjectCreationSettingsCoordinator else { throw EditorDocumentWriteError.rejected(.unqualifiedDispatch) }
        try owner.performSynchronousOperation(contextId: contextId, requiresEditing: false) {}
        return SetObjectCreationSettingsCoordinator(owner: owner, childPreparation: childPreparation,
                                                    navigationContext: navigationContext, contextId: contextId)
    }
    
    func showTemplateEditing(
        setting: ObjectCreationSetting,
        onTemplateSelection: (() -> Void)?,
        onSetAsDefaultTemplate: @escaping (String) -> Void,
        completion: (() -> Void)?
    ) {
        if let documentWriteOwner, let childPreparation, let ownedContextId {
            scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: ownedContextId) { [self] in
                let data = EditorPageObject(objectId: setting.templateId, spaceId: setting.spaceId, usecase: .embedded)
                let session = try await childPreparation.prepare(data: data)
                do {
                    let model = try EditorPageCoordinatorViewModel(preparedSession: session, showHeader: false)
                    let controller = TemplateEditingViewController(
                        editorViewController: UIHostingController(rootView: EditorPageCoordinatorView(preparedModel: model)),
                        objectId: setting.templateId, spaceId: setting.spaceId, output: self,
                        onSelectTemplateTap: onTemplateSelection, preparedSession: session
                    )
                    try documentWriteOwner.performSynchronousOperation(spaceId: setting.spaceId, requiresEditing: false) {
                        useAsTemplateAction = onSetAsDefaultTemplate
                        activeNavigationContext.present(controller, completion: completion)
                    }
                } catch {
                    session.retire()
                    throw error
                }
            }
            return
        }
        let editorView = EditorPageCoordinatorView(
            data: EditorPageObject(
                objectId: setting.templateId,
                spaceId: setting.spaceId,
                usecase: .embedded
            ),
            showHeader: false
        )

        self.useAsTemplateAction = onSetAsDefaultTemplate

        let editingTemplateViewController = TemplateEditingViewController(
            editorViewController: UIHostingController(rootView: editorView),
            objectId: setting.templateId,
            spaceId: setting.spaceId,
            output: self,
            onSelectTemplateTap: onTemplateSelection
        )

        activeNavigationContext.present(editingTemplateViewController, completion: completion)
    }
    
    private func showTypesSearch(
        setDocument: some SetDocumentProtocol,
        onSelect: @escaping (ObjectType) -> ()
    ) {
        let view = ObjectTypeSearchView(
            title: Loc.changeType,
            spaceId: setDocument.spaceId,
            settings: .setByRelationNewObject
        ) { [weak self] type in
            self?.activeNavigationContext.dismissTopPresented()
            onSelect(type)
        }
        
        activeNavigationContext.presentSwiftUIView(view: view)
    }
    
    // MARK: - ObjectSettingsCoordinatorOutput
    func closeEditor() {
        activeNavigationContext.dismissTopPresented(animated: true, completion: nil)
    }
    
    func showEditorScreen(data: ScreenData) {}
    
    func didCreateLinkToItself(selfName: String, data: ScreenData) {
        anytypeAssertionFailure("Should be disabled in restrictions. Check template restrinctions")
    }
    
    func didCreateTemplate(templateId: String) {
        anytypeAssertionFailure("Should be disabled in restrictions. Check template restrinctions")
    }
    
    func didTapUseTemplateAsDefault(templateId: String) {
        if let documentWriteOwner {
            try? documentWriteOwner.performSynchronousDocumentAction(requiredPermissions: [.templateSetAsDefault]) {
                useAsTemplateAction?(templateId)
            }
        } else {
            useAsTemplateAction?(templateId)
        }
    }
    
    func didUndoRedo() {
        anytypeAssertionFailure("Undo/redo is not available")
    }
    
    func versionRestored(_ text: String) {
        toastPresenter.show(message: Loc.VersionHistory.Toast.message(text))
    }
    
    // MARK: - SetObjectCreationSettingsOutput
    
    func onObjectTypesSearchAction(setDocument: some SetDocumentProtocol, completion: @escaping (ObjectType) -> Void) {
        showTypesSearch(setDocument: setDocument, onSelect: completion)
    }
    
    func templateEditingHandler(
        setting: ObjectCreationSetting,
        onSetAsDefaultTemplate: @escaping (String) -> Void,
        onTemplateSelection: ((ObjectCreationSetting) -> Void)?
    ) {
        showTemplateEditing(
            setting: setting,
            onTemplateSelection: { [weak self] in
                self?.activeNavigationContext.dismissAllPresented(animated: true) {
                    onSetAsDefaultTemplate(setting.templateId)
                    onTemplateSelection?(setting)
                }
            },
            onSetAsDefaultTemplate: { [weak self] templateId in
                self?.activeNavigationContext.dismissTopPresented(animated: true, completion: {
                    onSetAsDefaultTemplate(templateId)
                })
            },
            completion: nil
        )
    }
}
