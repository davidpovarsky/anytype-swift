import Foundation
import SwiftUI
import Services
import PinkhaKit

@MainActor
@Observable
final class PropertyInfoViewModel {

    private var identityRevision: Int = 0

    var formatModel: NewPropertyFormatSectionView.Model {
        format.asViewModel
    }

    var objectTypesRestrictionModel: [NewPropertyRestrictionsSectionView.ObjectTypeModel]? {
        objectTypes.flatMap { $0.asViewModel }
    }

    var isSaveButtonActive: Bool {
        _ = identityRevision
        guard name.isNotEmpty else { return false }
        switch mode {
        case .create:
            return true
        case .edit:
            return !isReadOnly && PinkhaTorahPropertyPolicy.shared.canEditPropertyDefinition(
                propertyId: relationId, key: "", spaceId: spaceId
            )
        }
    }

    var confirmButtonTitle: String {
        switch mode {
        case .create:
            Loc.create
        case .edit:
            Loc.save
        }
    }

    var title: String {
        switch mode {
        case .create:
            Loc.newField
        case .edit:
            Loc.editField
        }
    }

    var canShowMenu: Bool {
        _ = identityRevision
        switch mode {
        case .create:
            return false
        case .edit:
            return !isReadOnly && PinkhaTorahPropertyPolicy.shared.canDeletePropertyDefinition(
                propertyId: relationId, key: "", spaceId: spaceId
            )
        }
    }

    let mode: PropertyInfoViewMode
    let isReadOnly: Bool

    var name: String
    private var format: SupportedPropertyFormat
    private var objectTypes: [ObjectType]?
    var toastData: ToastBarData?

    @ObservationIgnored
    private let target: PropertiesModuleTarget
    @ObservationIgnored
    private let spaceId: String
    @ObservationIgnored
    private let relationId: String

    @ObservationIgnored
    @Injected(\.objectTypeProvider)
    private var objectTypeProvider: any ObjectTypeProviderProtocol
    @ObservationIgnored
    @Injected(\.objectActionsService)
    private var objectActionsService: any ObjectActionsServiceProtocol

    @ObservationIgnored
    private let relationsInteractor: any PropertiesInteractorProtocol
    @ObservationIgnored
    private weak var output: (any PropertyInfoModuleOutput)?
    
    init(
        data: PropertyInfoData,
        relationsInteractor: some PropertiesInteractorProtocol,
        output: (any PropertyInfoModuleOutput)?
    ) {
        self.spaceId = data.spaceId
        self.target = data.target
        self.relationsInteractor = relationsInteractor
        self.output = output
        self.mode = data.mode
        self.isReadOnly = data.isReadOnly || !PinkhaTorahPropertyPolicy.shared.canEditPropertyDefinition(
            propertyId: data.mode.relationId ?? "", key: "", spaceId: data.spaceId
        )
        
        self.name = data.name
        self.format = data.mode.format ?? SupportedPropertyFormat.object
        self.relationId = data.mode.relationId ?? ""
        handleFormatUpdate()
        data.mode.limitedObjectTypes.flatMap { updateTypesRestriction(objectTypeIds: $0) }
        NotificationCenter.default.addObserver(
            forName: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let self else { return }
            let notifiedSpace = notification.userInfo?["spaceId"] as? String
            if notifiedSpace == nil || notifiedSpace == self.spaceId {
                self.identityRevision &+= 1
            }
        }
    }
    
}

// MARK: - Internal functions

extension PropertyInfoViewModel {
    
    func didTapFormatSection() {
        guard PinkhaTorahPropertyPolicy.shared.canEditPropertyDefinition(propertyId: relationId, key: "", spaceId: spaceId) else { return }
        output?.didAskToShowPropertyFormats(selectedFormat: format, onSelect: { [weak self] format in
            self?.updatePropertyFormat(format)
        })
    }
    
    func didTapTypesRestrictionSection() {
        guard PinkhaTorahPropertyPolicy.shared.canEditPropertyDefinition(propertyId: relationId, key: "", spaceId: spaceId) else { return }
        output?.didAskToShowObjectTypesSearch(selectedObjectTypesIds: objectTypeIds, onSelect: { [weak self] ids in
            self?.updateTypesRestriction(objectTypeIds: ids)
        })
    }
    
    func didTapAddButton() {
        let relationDetails = PropertyDetails(
            id: relationId,
            key: "",
            name: name,
            format: format.asPropertyFormat,
            isHidden: false,
            isReadOnly: false,
            isReadOnlyValue: false,
            objectTypes: objectTypeIds,
            maxCount: 0,
            sourceObject: "",
            isDeleted: false,
            spaceId: ""
        )
        
        switch mode {
        case .create:
            createRelation(relationDetails)
        case .edit:
            guard PinkhaTorahPropertyPolicy.shared.canEditPropertyDefinition(propertyId: relationId, key: "", spaceId: spaceId) else { return }
            updateRelation(relationDetails)
        }
    }
    
    func didTapDelete() async throws {
        guard case let .edit(relationId, _, _) = mode else { return }
        guard PinkhaTorahPropertyPolicy.shared.canDeletePropertyDefinition(propertyId: relationId, key: "", spaceId: spaceId) else { return }
        
        try await objectActionsService.setArchive(objectIds: [relationId], true)
        toastData = ToastBarData(Loc.successfullyDeleted(name))
    }
    
    private func createRelation(_ relationDetails: PropertyDetails) {
        // Prevent forging or overwriting genuinely reserved native property keys or internal storage ID/key
        if TorahNativePropertyDefinition.definition(for: relationDetails.key) != nil ||
           PinkhaTorahPropertyPolicy.shared.isInternalProperty(propertyId: relationDetails.id, key: relationDetails.key, spaceId: spaceId) {
            return
        }

        Task {
            let createdRelation = try await relationsInteractor.createProperty(spaceId: spaceId, relation: relationDetails)
            
            switch target {
            case .type(let data):
                try await relationsInteractor.addPropertyToType(relation: createdRelation, isFeatured: data.isFeatured)
            case let .dataview(objectId, activeViewId, typeDetails):
                try await relationsInteractor.addPropertyToDataview(objectId: objectId, relation: createdRelation, activeViewId: activeViewId, typeDetails: typeDetails)
            case .object(let targetObjectId):
                try await relationsInteractor.addPropertyToObject(objectId: targetObjectId, relation: createdRelation)
            case .library:
                break
            }
            
            onSuccessfullAction(relationDetails: createdRelation)
        }
    }
    
    private func updateRelation(_ details: PropertyDetails) {
        guard PinkhaTorahPropertyPolicy.shared.canEditPropertyDefinition(propertyId: details.id, key: details.key, spaceId: spaceId) else { return }
        Task {
            try await relationsInteractor.updateProperty(spaceId: spaceId, relation: details)
            onSuccessfullAction(relationDetails: details)
        }
    }
    
    private func onSuccessfullAction(relationDetails: PropertyDetails) {
        let text = switch mode {
        case .create:
            Loc.Fields.created(relationDetails.name)
        case .edit:
            Loc.Fields.updated(relationDetails.name)
        }
        
        toastData = ToastBarData(text)
        UINotificationFeedbackGenerator().notificationOccurred(.success)
        output?.didPressConfirm(relationDetails)
    }
}

// MARK: - PropertyInfoModuleInput

extension PropertyInfoViewModel: PropertyInfoModuleInput {
    
    func updatePropertyFormat(_ newFormat: SupportedPropertyFormat) {
        format = newFormat
        handleFormatUpdate()
    }
    
    func updateTypesRestriction(objectTypeIds: [String]) {
        objectTypes = objectTypeIds.compactMap {
            try? objectTypeProvider.objectType(id: $0)
        }
    }
    
}

// MARK: - Private extension

private extension PropertyInfoViewModel {
    
    func handleFormatUpdate() {
        objectTypes = format == .object ? [] : nil
    }
    
    var objectTypeIds: [String] {
        objectTypes?.map { $0.id } ?? []
    }
    
}

// MARK: - SupportedPropertyFormat private extension

private extension SupportedPropertyFormat {
    
    var asViewModel: NewPropertyFormatSectionView.Model {
        NewPropertyFormatSectionView.Model(icon: self.iconAsset, title: self.title)
    }
    
    var asPropertyFormat: PropertyFormat {
        switch self {
        case .text: return .longText
        case .tag: return .tag
        case .status: return .status
        case .number: return .number
        case .date: return .date
        case .file: return .file
        case .object: return .object
        case .checkbox: return .checkbox
        case .url: return .url
        case .email: return .email
        case .phone: return .phone
        }
    }
}

// MARK: - Array private extension

private extension Array where Element == ObjectType {
    
    var asViewModel: [NewPropertyRestrictionsSectionView.ObjectTypeModel] {
        map {
            NewPropertyRestrictionsSectionView.ObjectTypeModel(
                id: $0.id,
                icon: $0.icon,
                title: $0.displayName
            )
        }
    }
    
}
