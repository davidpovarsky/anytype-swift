import Foundation
import Services
import AnytypeCore
import SwiftUI

@MainActor
@Observable
final class ObjectSettingsCoordinatorViewModel:
    ObjectSettingsModelOutput,
    PropertyValueCoordinatorOutput,
    ObjectVersionModuleOutput
{

    let objectId: String
    let spaceId: String
    @ObservationIgnored
    let preparedSession: PreparedEditorPageSession?
    private weak var output: (any ObjectSettingsCoordinatorOutput)?

    var coverPickerData: BaseDocumentIdentifiable?
    var objectIconPickerData: ObjectIconPickerData?
    var blockObjectSearchData: BlockObjectSearchData?
    var relationsListData: PropertiesListData?
    var versionHistoryData: VersionHistoryData?
    var publishingData: PublishToWebViewData?
    var chatEditData: ChatCreateScreenData?
    var dismiss = false
    
    init(objectId: String, spaceId: String, output: (any ObjectSettingsCoordinatorOutput)?,
         preparedSession: PreparedEditorPageSession? = nil) {
        self.objectId = objectId
        self.spaceId = spaceId
        self.output = output
        self.preparedSession = preparedSession
    }
    
    private func publish(document: (any BaseDocumentProtocol)? = nil, _ operation: () -> Void) {
        guard let preparedSession else { operation(); return }
        try? preparedSession.owner.performSynchronousOperation(
            contextId: objectId, spaceId: spaceId, requiresEditing: false
        ) {
            try preparedSession.owner.validateDocument(document ?? preparedSession.document)
            operation()
        }
    }

    // MARK: - ObjectSettingsModelOutput
    
    func undoRedoAction(objectId: String) {
        publish {
            withAnimation(nil) {
                dismiss.toggle()
            }
            output?.didUndoRedo()
        }
    }
    
    func showCoverPicker(document: some BaseDocumentProtocol) {
        publish(document: document) {
            coverPickerData = BaseDocumentIdentifiable(document: document)
        }
    }
    
    func showIconPicker(document: some BaseDocumentProtocol) {
        publish(document: document) {
            objectIconPickerData = ObjectIconPickerData(document: document)
        }
    }
    
    func relationsAction(document: some BaseDocumentProtocol) {
        publish(document: document) {
            AnytypeAnalytics.instance().logScreenObjectRelation()
            relationsListData = PropertiesListData(document: document)
        }
    }
    
    func showVersionHistory(document: some BaseDocumentProtocol) {
        publish(document: document) {
            guard let details = document.details else { return }
            versionHistoryData = VersionHistoryData(
                objectId: document.objectId,
                spaceId: document.spaceId,
                isListType: details.isList,
                canRestore: document.permissions.canRestoreVersionHistory
            )
        }
    }
    
    func showPublising(document: some BaseDocumentProtocol) {
        publish(document: document) {
            publishingData = PublishToWebViewData(objectId: document.objectId, spaceId: document.spaceId)
        }
    }
    
    func openPageAction(screenData: ScreenData) {
        publish {
            output?.showEditorScreen(data: screenData)
        }
    }
    
    func linkToAction(document: some BaseDocumentProtocol, onSelect: @escaping (String) -> ()) {
        publish(document: document) {
            let excludedLayouts = DetailsLayout.fileAndMediaLayouts + [.set, .participant, .objectType]
            blockObjectSearchData = BlockObjectSearchData(
                title: Loc.linkTo,
                spaceId: document.spaceId,
                excludedObjectIds: [document.objectId],
                excludedLayouts: excludedLayouts,
                onSelect: { details in
                    onSelect(details.id)
                }
            )
        }
    }
    
    func closeEditorAction() {
        publish {
            output?.closeEditor()
        }
    }
    
    func didCreateLinkToItself(selfName: String, data: ScreenData) {
        publish {
            output?.didCreateLinkToItself(selfName: selfName, data: data)
        }
    }
    
    func didCreateTemplate(templateId: String) {
        publish {
            output?.didCreateTemplate(templateId: templateId)
        }
    }
    
    func didTapUseTemplateAsDefault(templateId: String) {
        guard let preparedSession else {
            output?.didTapUseTemplateAsDefault(templateId: templateId)
            return
        }
        try? preparedSession.owner.performSynchronousDocumentAction(
            contextId: objectId, spaceId: spaceId, requiredPermissions: [.templateSetAsDefault]
        ) {
            try preparedSession.owner.validateDocument(preparedSession.document)
            output?.didTapUseTemplateAsDefault(templateId: templateId)
        }
    }

    func showInviteMembers(spaceId: String) {
        publish {
            output?.showInviteMembers(spaceId: spaceId)
        }
    }

    func showEditInfo(document: some BaseDocumentProtocol) {
        publish(document: document) {
            guard let details = document.details else { return }
            chatEditData = ChatCreateScreenData(
                spaceId: document.spaceId,
                mode: .edit(
                    objectId: details.id,
                    currentName: details.name,
                    currentIcon: details.objectIconImage
                ),
                analyticsRoute: .navigation
            )
        }
    }

    // MARK: - PropertyValueCoordinatorOutput
    
    func showEditorScreen(data: ScreenData) {
        Task { @MainActor in
            publish {
                dismiss.toggle()
                output?.showEditorScreen(data: data)
            }
        }
    }
    
    // MARK: - ObjectVersionModuleOutput
    
    func versionRestored(_ text: String) {
        publish {
            dismiss.toggle()
            output?.versionRestored(text)
        }
    }
}
