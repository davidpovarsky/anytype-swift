import Foundation
import SwiftUI
import AnytypeCore
import Services

@MainActor
@Observable
final class EditorPageCoordinatorViewModel: EditorPageModuleOutput, PropertyValueCoordinatorOutput {

    let data: EditorPageObject
    let showHeader: Bool
    let torahSession: TorahEditorSession?
    var preparedState: EditorPageViewState?
    var preparationFailed = false
    @ObservationIgnored private let childPreparation: PreparedEditorChildPreparation?
    @ObservationIgnored private var preparationStarted = false
    @ObservationIgnored private var preparedSession: PreparedEditorPageSession?

    var hasQualifiedPreparation: Bool { childPreparation != nil || preparedSession != nil }
    var documentWriteOwner: EditorDocumentWriteOwner? { preparedEditorSession?.owner }
    var preparedEditorSession: PreparedEditorPageSession? {
        guard let preparedSession, preparedSession.hasExternalSourceBinding else { return nil }
        return preparedSession
    }
    @ObservationIgnored
    @Injected(\.propertyValueProcessingService)
    private var propertyValueProcessingService: any PropertyValueProcessingServiceProtocol

    var pageNavigation: PageNavigation?
    var dismiss = false
    var relationValueData: PropertyValueData?
    var toastBarData: ToastBarData?
    var codeLanguageData: CodeLanguageListData?
    var covertPickerData: BaseDocumentIdentifiable?
    var linkToObjectData: LinkToObjectSearchModuleData?
    var objectIconPickerData: ObjectIconPickerData?
    var textIconPickerData: TextIconPickerData?
    var blockObjectSearchData: BlockObjectSearchData?
    var undoRedoObjectId: StringIdentifiable?
    var relationsSearchData: PropertiesSearchData?
    var openUrlData: URL?
    var syncStatusSpaceId: StringIdentifiable?
    var cameraData: SimpleCameraData?
    
    init(
        data: EditorPageObject,
        showHeader: Bool,
        childPreparation: PreparedEditorChildPreparation? = nil
    ) {
        self.data = data
        self.showHeader = showHeader
        self.childPreparation = childPreparation
        // The external source already has a host-owned annotation lifetime.
        // Preserve the original Torah coordinator only for the original route.
        self.torahSession = childPreparation == nil
            ? try? TorahEditorSession(spaceId: data.spaceId, objectId: data.objectId)
            : nil
        self.torahSession?.installOpenObjectHandler { [weak self] objectId, blockId in
            guard let self else { return }
            pageNavigation?.open(
                .editor(.page(EditorPageObject(objectId: objectId, spaceId: data.spaceId, blockId: blockId)))
            )
        }
    }
    
    /// The external root owns this same original coordinator and its original
    /// modal flow. It consumes the existing prepared session without another
    /// document open, another source capture or a second assembly claim.
    init(preparedSession: PreparedEditorPageSession, showHeader: Bool) throws {
        self.data = preparedSession.data
        self.showHeader = showHeader
        self.childPreparation = nil
        self.torahSession = nil
        self.preparedSession = preparedSession
        self.preparationStarted = true
        self.preparedState = try EditorPageModuleAssembly().buildStateModel(
            preparedSession: preparedSession, output: self, showHeader: showHeader, torahSession: nil
        )
        try preparedSession.owner.validateOwnership()
    }

    /// Retain the prepared child across later user-created tasks. A failed or
    /// cancelled acquisition never falls back to an unbound legacy editor.
    func prepareQualifiedEditor() async {
        guard let childPreparation, !preparationStarted else { return }
        preparationStarted = true
        do {
            let session = try await childPreparation.prepare(data: data)
            preparedSession = session
            try Task.checkCancellation()
            let state = try EditorPageModuleAssembly().buildStateModel(
                preparedSession: session, output: self, showHeader: showHeader, torahSession: nil
            )
            try session.owner.validateOwnership()
            preparedState = state
        } catch {
            preparedSession?.retire()
            preparedSession = nil
            preparationFailed = true
        }
    }

    // MARK: - EditorPageModuleOutput
    
    func showEditorScreen(data: ScreenData) {
        pageNavigation?.open(data)
    }
    
    func replaceEditorScreen(data: EditorScreenData) {
        pageNavigation?.replace(data)
    }
    
    func closeEditor() {
        dismiss.toggle()
    }
    
    
    func showRelationValueEditingView(document: some BaseDocumentProtocol, relation: Property) {
        guard let objectDetails = document.details else {
            anytypeAssertionFailure("Details not found")
            return
        }
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: relation.id, key: relation.key, spaceId: document.spaceId
        ) else { return }
        handlePropertyValue(relation: relation, objectDetails: objectDetails)
    }
    
    func showCoverPicker(document: some BaseDocumentProtocol) {
        covertPickerData = BaseDocumentIdentifiable(document: document)
    }
    
    func onSelectCodeLanguage(objectId: String, spaceId: String, blockId: String) {
        codeLanguageData = CodeLanguageListData(documentId: objectId, spaceId: spaceId, blockId: blockId)
    }
    
    func showLinkToObject(data: LinkToObjectSearchModuleData) {
        linkToObjectData = data
    }
    
    func showIconPicker(document: some BaseDocumentProtocol) {
        objectIconPickerData = ObjectIconPickerData(document: document)
    }
    
    func showTextIconPicker(data: TextIconPickerData) {
        textIconPickerData = data
    }
    
    func showBlockObjectSearch(data: BlockObjectSearchData) {
        blockObjectSearchData = data
    }
    
    func didUndoRedo() {
        undoRedoObjectId = data.objectId.identifiable
    }
    
    func versionRestored(_ text: String) {
        toastBarData = ToastBarData(Loc.VersionHistory.Toast.message(text), type: .neutral)
    }
    
    func showAddPropertyInfoView(document: some BaseDocumentProtocol, onSelect: @escaping (PropertyDetails, _ isNew: Bool) -> Void) {
        let scope = preparedEditorSession.map {
            OriginalEditorPropertyScope(preparedSession: $0, objectId: document.objectId,
                                        spaceId: document.spaceId, document: document)
        }
        guard !hasQualifiedPreparation || scope != nil else { return }
        if let scope {
            guard (try? scope.withCurrent(requiredPermissions: OriginalEditorPropertyScope.listPermissions, {})) != nil else { return }
        }
        guard let details = document.details else { return }
        let visibleInstalledIds = (
            document.parsedProperties.featuredProperties +
            document.parsedProperties.sidebarProperties +
            document.parsedProperties.conflictedProperties +
            document.parsedProperties.legacyFeaturedProperties
        ).map(\.id)
        let hiddenIds = Set(document.parsedProperties.hiddenProperties.map(\.id))
        relationsSearchData = PropertiesSearchData(
            objectId: details.type,
            spaceId: document.spaceId,
            excludedRelationsIds: visibleInstalledIds,
            hiddenRelationsIds: hiddenIds,
            target: .object(objectId: details.id),
            originalEditorScope: scope,
            onRelationSelect: onSelect
        )
    }
    
    func openUrl(_ url: URL) {
        openUrlData = url
    }
    
    func showFailureToast(message: String) {
        toastBarData = ToastBarData(message, type: .failure)
    }
    
    func showSyncStatusInfo(spaceId: String) {
        syncStatusSpaceId = spaceId.identifiable
    }

    func showCamera(_ data: SimpleCameraData) {
        cameraData = data
    }

    func onWidgetsSelected(spaceId: String) {
        let widgetData = HomeWidgetData(spaceId: spaceId)
        pageNavigation?.open(.alert(.widgets(widgetData)))
    }

    // MARK: - Private
    
    private func handlePropertyValue(relation: Property, objectDetails: ObjectDetails) {
        relationValueData = propertyValueProcessingService.handlePropertyValue(
            relation: relation,
            objectDetails: objectDetails,
            analyticsType: .block,
            preparedSession: preparedEditorSession
        )
    }
}

