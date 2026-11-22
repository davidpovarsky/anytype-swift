import SwiftUI
import Services
import AnytypeCore

@MainActor
protocol PropertyValueCoordinatorOutput: AnyObject {
    func showEditorScreen(data: ScreenData)
}

@MainActor
@Observable
final class PropertyValueCoordinatorViewModel:
    ObjectPropertyListCoordinatorModuleOutput,
    TextPropertyActionButtonViewModelDelegate
{
    @ObservationIgnored
    @Injected(\.objectTypeProvider)
    private var objectTypeProvider: any ObjectTypeProviderProtocol
    @ObservationIgnored
    @Injected(\.objectDateByTimestampService)
    private var objectDateByTimestampService: any ObjectDateByTimestampServiceProtocol

    var mediumDetent: Bool = false
    private var identityRevision: Int = 0

    private let relation: Property
    private let objectDetails: ObjectDetails
    private let analyticsType: AnalyticsEventsRelationType
    private let preparedSession: PreparedEditorPageSession?
    private weak var output: (any PropertyValueCoordinatorOutput)?

    var toastBarData: ToastBarData?
    var safariUrl: URL?

    private var originalScope: OriginalEditorPropertyScope? {
        preparedSession.map {
            OriginalEditorPropertyScope(preparedSession: $0, objectId: objectDetails.id, spaceId: objectDetails.spaceId)
        }
    }

    private func publish(_ operation: () -> Void) {
        if let scope = originalScope { try? scope.withCurrent(operation) }
        else { operation() }
    }
    
    init(data: PropertyValueData, output: (any PropertyValueCoordinatorOutput)?) {
        self.relation = data.relation
        self.objectDetails = data.objectDetails
        self.analyticsType = data.analyticsType
        self.preparedSession = data.preparedSession
        self.output = output

        NotificationCenter.default.addObserver(
            forName: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let self else { return }
            let notifiedSpace = notification.userInfo?["spaceId"] as? String
            if notifiedSpace == nil || notifiedSpace == self.objectDetails.spaceId {
                self.publish { self.identityRevision &+= 1 }
            }
        }
    }
    
    func propertyModule() -> AnyView {
        if let scope = originalScope, (try? scope.withCurrent {}) == nil {
            return EmptyView().eraseToAnyView()
        }
        _ = identityRevision
        let status = PinkhaTorahPropertyPolicy.shared.internalIdentityStatus(spaceId: objectDetails.spaceId)
        switch status {
        case .loading:
            return ProgressView().eraseToAnyView()
        case .known(let identities):
            if identities.isInternal(propertyId: relation.id, key: relation.key) {
                return EmptyView().eraseToAnyView()
            }
        case .unavailable:
            if PinkhaTorahPropertyPolicy.shared.isInternalProperty(
                propertyId: relation.id, key: relation.key, spaceId: objectDetails.spaceId
            ) {
                return EmptyView().eraseToAnyView()
            }
        }
        if TorahNativePropertyPresentation.definition(relation.key) != nil {
            // This separate original Torah session must receive the retained
            // page authority before it may be created by the external Host.
            guard preparedSession == nil else { return EmptyView().eraseToAnyView() }
            mediumDetent = false
            return TorahNativePropertyEditorView(
                spaceId: objectDetails.spaceId, objectId: objectDetails.id,
                key: relation.key, canEdit: relation.isEditable
            ).eraseToAnyView()
        }
        switch relation {
        case .date(let date):
            return dateModule(date: date)
        case .status(let status):
            let configuration = PropertyModuleConfiguration(
                title: status.name,
                isEditable: relation.isEditable,
                relationKey: status.key,
                objectId: objectDetails.id,
                spaceId: objectDetails.spaceId,
                selectionMode: .single,
                analyticsType: analyticsType,
                preparedSession: preparedSession
            )
            mediumDetent = status.values.isNotEmpty || !relation.isEditable
            let selectedOptionsIds = status.values.compactMap { $0.id }
            return SelectPropertyListCoordinatorView(
                data: SelectPropertyListData(
                    style: .status,
                    configuration: configuration,
                    relationSelectedOptionsModel: PropertySelectedOptionsModel(
                        config: configuration,
                        selectedOptionsIds: selectedOptionsIds
                    )
                )
            ).eraseToAnyView()
        case .tag(let tag):
            let configuration = PropertyModuleConfiguration(
                title: tag.name,
                isEditable: relation.isEditable,
                relationKey: tag.key,
                objectId: objectDetails.id,
                spaceId: objectDetails.spaceId,
                selectionMode: .multi,
                analyticsType: analyticsType,
                preparedSession: preparedSession
            )
            mediumDetent = tag.selectedTags.isNotEmpty || !relation.isEditable
            let selectedOptionsIds = tag.selectedTags.compactMap { $0.id }
            return SelectPropertyListCoordinatorView(
                data: SelectPropertyListData(
                    style: .tag,
                    configuration: configuration,
                    relationSelectedOptionsModel: PropertySelectedOptionsModel(
                        config: configuration,
                        selectedOptionsIds: selectedOptionsIds
                    )
                )
            ).eraseToAnyView()
        case .object(let object):
            let configuration = PropertyModuleConfiguration(
                title: object.name,
                isEditable: relation.isEditable,
                relationKey: object.key,
                objectId: objectDetails.id,
                spaceId: objectDetails.spaceId,
                selectionMode: .multi,
                analyticsType: analyticsType,
                preparedSession: preparedSession
            )
            mediumDetent = object.selectedObjects.isNotEmpty || !relation.isEditable
            return ObjectPropertyListCoordinatorView(
                data: ObjectPropertyListData(
                    configuration: configuration,
                    interactor: ObjectPropertyListInteractor(
                        spaceId: configuration.spaceId,
                        limitedObjectTypes: obtainLimitedObjectTypes(with: object.limitedObjectTypes)
                    ),
                    relationSelectedOptionsModel: PropertySelectedOptionsModel(
                        config: configuration,
                        selectedOptionsIds: object.selectedObjects.compactMap { $0.id }
                    ),
                    preloadedReadOnlyOptions: object.links != nil
                        ? object.selectedObjects.map(ObjectPropertyOption.init(objectOption:))
                        : nil
                ),
                output: self
            ).eraseToAnyView()
        case .file(let file):
            let configuration = PropertyModuleConfiguration(
                title: file.name,
                isEditable: relation.isEditable,
                relationKey: file.key,
                objectId: objectDetails.id,
                spaceId: objectDetails.spaceId,
                selectionMode: .multi,
                analyticsType: analyticsType,
                preparedSession: preparedSession
            )
            mediumDetent = file.files.isNotEmpty || !relation.isEditable
            return ObjectPropertyListCoordinatorView(
                data: ObjectPropertyListData(
                    configuration: configuration,
                    interactor: FilePropertyListInteractor(
                        spaceId: configuration.spaceId
                    ),
                    relationSelectedOptionsModel: PropertySelectedOptionsModel(
                        config: configuration,
                        selectedOptionsIds: file.files.compactMap { $0.id }
                    )
                ),
                output: self
            ).eraseToAnyView()
        case .text(let text):
            return textPropertyEditingModule(
                value: text.value,
                name: text.name,
                relationKey: text.key,
                type: .text
            )
        case .number(let number):
            return textPropertyEditingModule(
                value: number.value,
                name: number.name,
                relationKey: number.key,
                type: .number
            )
        case .url(let url):
            return textPropertyEditingModule(
                value: url.value,
                name: url.name,
                relationKey: url.key,
                type: .url
            )
        case .email(let email):
            return textPropertyEditingModule(
                value: email.value,
                name: email.name,
                relationKey: email.key,
                type: .email
            )
        case .phone(let phone):
            return textPropertyEditingModule(
                value: phone.value,
                name: phone.name,
                relationKey: phone.key,
                type: .phone
            )
        case .unknown, .checkbox:
            anytypeAssertionFailure("There is no module for this relation", info: ["relation": relation.name])
            return EmptyView().eraseToAnyView()
        }
    }
    
    private func dateModule(date: Property.Date) -> AnyView {
        if date.isEditable {
            let dateValue = date.value?.date
            let configuration = PropertyModuleConfiguration(
                title: date.name,
                isEditable: relation.isEditable,
                relationKey: date.key,
                objectId: objectDetails.id,
                spaceId: objectDetails.spaceId,
                analyticsType: analyticsType,
                preparedSession: preparedSession
            )
            return PropertyCalendarCoordinatorView(
                date: dateValue,
                configuration: configuration
            ).eraseToAnyView()
        } else {
            let dateValue = date.value?.date ?? Date()
            return DateCoordinatorView(
                data: EditorDateObject(
                    date: dateValue,
                    spaceId: objectDetails.spaceId
                )
            ).applyDragIndicator().eraseToAnyView()
        }
    }
    
    private func textPropertyEditingModule(
        value: String?,
        name: String,
        relationKey: String,
        type: TextPropertyViewType
    ) -> AnyView {
        let configuration = PropertyModuleConfiguration(
            title: name,
            isEditable: relation.isEditable,
            relationKey: relationKey,
            objectId: objectDetails.id,
            spaceId: objectDetails.spaceId,
            analyticsType: analyticsType,
            preparedSession: preparedSession
        )
        
        return TextPropertyEditingView(
            data: TextPropertyEditingViewData(
                text: value,
                type: type,
                config: configuration,
                objectDetails: objectDetails,
                output: self
            )
        ).eraseToAnyView()
    }
    
    private func obtainLimitedObjectTypes(with typesIds: [String]) -> [ObjectType] {
        typesIds.compactMap { try? objectTypeProvider.objectType(id: $0) }
    }

    
    // MARK: - ObjectPropertyListCoordinatorModuleOutput
    
    func onObjectOpen(screenData: ScreenData) {
        publish { output?.showEditorScreen(data: screenData) }
    }
    
    // MARK: - TextPropertyActionButtonViewModelDelegate
    
    func canOpenUrl(_ url: URL) -> Bool {
        if let scope = originalScope {
            return (try? scope.withCurrent { UIApplication.shared.canOpenURL(url.urlByAddingHttpIfSchemeIsEmpty()) }) ?? false
        }
        return UIApplication.shared.canOpenURL(url.urlByAddingHttpIfSchemeIsEmpty())
    }
    
    func openUrl(_ url: URL) {
        publish { safariUrl = url }
    }
    
    func showActionSuccessMessage(_ text: String) {
        publish { toastBarData = ToastBarData(text, type: .success) }
    }
}
