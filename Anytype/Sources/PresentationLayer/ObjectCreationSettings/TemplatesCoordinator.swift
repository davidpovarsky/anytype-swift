import UIKit
import SwiftUI
import Combine
import Services
import AnytypeCore

protocol TemplatesCoordinatorProtocol {
    @MainActor
    func showTemplatesPicker(
        document: some BaseDocumentProtocol,
        onSetAsDefaultTemplate: @escaping (String) -> Void
    )
    
    @MainActor
    func showTemplatesPicker(
        data: TemplatePickerViewModelData,
        onSetAsDefaultTemplate: @escaping (String) -> Void
    )
}

@MainActor
final class TemplatesCoordinator: TemplatesCoordinatorProtocol, ObjectSettingsCoordinatorOutput {
    
    @Injected(\.legacyNavigationContext)
    private var navigationContext: any NavigationContextProtocol
    @Injected(\.legacyToastPresenter)
    private var toastPresenter: any ToastPresenterProtocol

    private var onSetAsDefaultTemplate: ((String) -> Void)?
    private let ownedNavigationContext: (any NavigationContextProtocol)?
    private let documentWriteOwner: EditorDocumentWriteOwner?
    private let childPreparation: PreparedEditorChildPreparation?
    private let ownedSpaceId: String?

    private var activeNavigationContext: any NavigationContextProtocol {
        ownedNavigationContext ?? navigationContext
    }
    
    nonisolated init() {
        ownedNavigationContext = nil
        documentWriteOwner = nil
        childPreparation = nil
        ownedSpaceId = nil
    }

    private init(owner: EditorDocumentWriteOwner, childPreparation: PreparedEditorChildPreparation,
                 navigationContext: any NavigationContextProtocol, spaceId: String) {
        self.documentWriteOwner = owner
        self.childPreparation = childPreparation
        self.ownedNavigationContext = navigationContext
        self.ownedSpaceId = spaceId
    }

    static func bindOriginal(_ service: any TemplatesCoordinatorProtocol,
                             owner: EditorDocumentWriteOwner,
                             childPreparation: PreparedEditorChildPreparation,
                             navigationContext: any NavigationContextProtocol,
                             spaceId: String) throws -> any TemplatesCoordinatorProtocol {
        guard service is TemplatesCoordinator else { throw EditorDocumentWriteError.rejected(.unqualifiedDispatch) }
        try owner.performSynchronousOperation(spaceId: spaceId, requiresEditing: false) {}
        return TemplatesCoordinator(owner: owner, childPreparation: childPreparation,
                                    navigationContext: navigationContext, spaceId: spaceId)
    }
    
    @MainActor
    func showTemplatesPicker(
        document: some BaseDocumentProtocol,
        onSetAsDefaultTemplate: @escaping (String) -> Void
    ) {
        if let documentWriteOwner {
            guard (try? documentWriteOwner.performSynchronousOperation(
                contextId: document.objectId, spaceId: document.spaceId, requiresEditing: false,
                operation: { try documentWriteOwner.validateDocument(document) }
            )) != nil else { return }
        }
        let data = TemplatePickerViewModelData(
            mode: .objectTemplate(objectId: document.objectId),
            typeId: document.details?.objectType.id,
            spaceId: document.spaceId,
            defaultTemplateId: nil
        )
        showTemplatesPicker(data: data, onSetAsDefaultTemplate: onSetAsDefaultTemplate)
    }
    
    @MainActor
    func showTemplatesPicker(
        data: TemplatePickerViewModelData,
        onSetAsDefaultTemplate: @escaping (String) -> Void
    ) {
        if let documentWriteOwner {
            guard (try? documentWriteOwner.performSynchronousOperation(spaceId: data.spaceId, requiresEditing: false) {}) != nil else { return }
        }
        self.onSetAsDefaultTemplate = onSetAsDefaultTemplate
        let picker = TemplatePickerView(viewModel: .init(data: data, output: self, documentWriteOwner: self.documentWriteOwner))
        let hostViewController = UIHostingController(rootView: picker)
        hostViewController.modalPresentationStyle = .fullScreen
        activeNavigationContext.present(hostViewController, animated: true, completion: nil)
    }
}

extension TemplatesCoordinator: TemplatePickerViewModuleOutput {
    func onTemplatesChanged(_ templates: [ObjectDetails], completion: ([TemplatePickerData]) -> Void) {
        if let documentWriteOwner {
            guard (try? documentWriteOwner.validateOwnership()) != nil,
                  let ownedSpaceId,
                  templates.allSatisfy({ $0.spaceId.utf8.elementsEqual(ownedSpaceId.utf8) }) else { return }
        }
        let editorsViews = templates.map { template in
            let editorView = EditorPageCoordinatorView(
                data: EditorPageObject(
                    objectId: template.id,
                    spaceId: template.spaceId,
                    usecase: .embedded
                ),
                showHeader: false,
                childPreparation: childPreparation
            ).eraseToAnyView()
            return TemplatePickerData(template: template, editorView: editorView)
        }
        completion(editorsViews)
    }
    
    func selectionOptionsView(_ provider: some OptionsItemProvider) -> AnyView {
        SelectionOptionsView(viewModel: SelectionOptionsViewModel(itemProvider: provider))
            .eraseToAnyView()
    }

    func onClose() {
        activeNavigationContext.dismissTopPresented(animated: true, completion: nil)
    }
    
    // MARK: - ObjectSettingsCoordinatorOutput
    
    func closeEditor() {}
    
    func showEditorScreen(data: ScreenData) {}
    
    func didCreateLinkToItself(selfName: String, data: ScreenData) {}
    
    func didCreateTemplate(templateId: String) {}
    
    func didTapUseTemplateAsDefault(templateId: String) {
        if let documentWriteOwner {
            try? documentWriteOwner.performSynchronousDocumentAction(requiredPermissions: [.templateSetAsDefault]) {
                onSetAsDefaultTemplate?(templateId)
            }
        } else {
            onSetAsDefaultTemplate?(templateId)
        }
    }
    
    func didUndoRedo() {
        anytypeAssertionFailure("Undo/redo is not available")
    }
    
    func versionRestored(_ text: String) {
        toastPresenter.show(message: Loc.VersionHistory.Toast.message(text))
    }
}
