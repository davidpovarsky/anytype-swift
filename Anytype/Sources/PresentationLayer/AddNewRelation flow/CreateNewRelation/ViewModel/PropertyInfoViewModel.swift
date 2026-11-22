import Foundation
import SwiftUI
import Services
import PinkhaKit

@MainActor
@Observable
final class PropertyInfoViewModel {

    private var identityRevision: Int = 0
    private var isPerformingOriginalAction = false
    private var originalCreationStarted = false
    private(set) var createdOriginalProperty: PropertyDetails?

    var hasOriginalEditorScope: Bool { originalEditorScope != nil }
    var canEditTypeRestrictions: Bool { !isReadOnly && originalEditorScope == nil }

    var formatModel: NewPropertyFormatSectionView.Model {
        format.asViewModel
    }

    var objectTypesRestrictionModel: [NewPropertyRestrictionsSectionView.ObjectTypeModel]? {
        objectTypes.flatMap { $0.asViewModel }
    }

    var isSaveButtonActive: Bool {
        _ = identityRevision
        guard name.isNotEmpty else { return false }
        if originalEditorScope != nil {
            return !isReadOnly && !isPerformingOriginalAction && !originalCreationStarted && originalDefinitionIsCurrent
        }
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
            if originalEditorScope != nil {
                return !isReadOnly && !isPerformingOriginalAction && originalDefinitionIsCurrent
            }
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
    private let originalEditorScope: OriginalEditorPropertyScope?

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
        self.originalEditorScope = data.originalEditorScope
        self.isReadOnly = data.isReadOnly || (data.originalEditorScope == nil && !PinkhaTorahPropertyPolicy.shared.canEditPropertyDefinition(
            propertyId: data.mode.relationId ?? "", key: "", spaceId: data.spaceId
        ))
        
        self.name = data.name
        self.format = data.mode.format ?? SupportedPropertyFormat.object
        self.relationId = data.mode.relationId ?? ""
        handleFormatUpdate()
        data.mode.limitedObjectTypes.flatMap { updateTypesRestriction(objectTypeIds: $0) }
        if data.originalEditorScope == nil {
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
    
}

// MARK: - Internal functions

extension PropertyInfoViewModel {
    
    func didTapFormatSection() {
        if let scope = originalEditorScope {
            try? scope.withCurrent {
                guard !isReadOnly else { return }
                output?.didAskToShowPropertyFormats(selectedFormat: format, onSelect: { [weak self] format in
                    self?.updatePropertyFormat(format)
                })
            }
            return
        }
        guard PinkhaTorahPropertyPolicy.shared.canEditPropertyDefinition(propertyId: relationId, key: "", spaceId: spaceId) else { return }
        output?.didAskToShowPropertyFormats(selectedFormat: format, onSelect: { [weak self] format in
            self?.updatePropertyFormat(format)
        })
    }
    
    func didTapTypesRestrictionSection() {
        guard originalEditorScope == nil else { return }
        guard PinkhaTorahPropertyPolicy.shared.canEditPropertyDefinition(propertyId: relationId, key: "", spaceId: spaceId) else { return }
        output?.didAskToShowObjectTypesSearch(selectedObjectTypesIds: objectTypeIds, onSelect: { [weak self] ids in
            self?.updateTypesRestriction(objectTypeIds: ids)
        })
    }
    
    func didTapAddButton(onCompletion: (@MainActor @Sendable () -> Void)? = nil) {
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

        if let scope = originalEditorScope {
            saveOriginalProperty(relationDetails, scope: scope, onCompletion: onCompletion)
            return
        }
        
        switch mode {
        case .create:
            createRelation(relationDetails)
        case .edit:
            guard PinkhaTorahPropertyPolicy.shared.canEditPropertyDefinition(propertyId: relationId, key: "", spaceId: spaceId) else { return }
            updateRelation(relationDetails)
        }
    }
    
    func didTapDelete() async throws {
        if let scope = originalEditorScope {
            guard !isReadOnly, case let .edit(selectedId, _, _) = mode else {
                throw OriginalEditorPropertyModalError.invalidPropertyIdentity
            }
            try scope.requireModalTarget(target, spaceId: spaceId)
            let original = try OriginalObjectActionsServiceBinding.requireOriginal(objectActionsService)
            try await scope.withSelectedModalProperty(id: selectedId, requiredPermissions: [.archive]) { _, actual, _ in
                try await original.setArchive(objectIds: [actual.id], true)
            }
            try scope.withCurrent { toastData = ToastBarData(Loc.successfullyDeleted(name)) }
            return
        }
        guard case let .edit(relationId, _, _) = mode else { return }
        guard PinkhaTorahPropertyPolicy.shared.canDeletePropertyDefinition(propertyId: relationId, key: "", spaceId: spaceId) else { return }
        
        try await objectActionsService.setArchive(objectIds: [relationId], true)
        toastData = ToastBarData(Loc.successfullyDeleted(name))
    }

    func prepareDeleteAction(
        onCompletion: @escaping @MainActor @Sendable () -> Void
    ) -> (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard let scope = originalEditorScope else { return nil }
        return { [self] in
            scope.prepareAction(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
                try await self.didTapDelete()
                try scope.withCurrent { onCompletion() }
            }
        }
    }

    private var originalDefinitionIsCurrent: Bool {
        guard let scope = originalEditorScope else { return false }
        return (try? scope.withCurrent(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
            try scope.requireModalTarget(target, spaceId: spaceId)
        }) != nil
    }

    private func saveOriginalProperty(
        _ details: PropertyDetails, scope: OriginalEditorPropertyScope,
        onCompletion: (@MainActor @Sendable () -> Void)?
    ) {
        guard !isReadOnly, !isPerformingOriginalAction, !originalCreationStarted else { return }
        do {
            try scope.requireModalTarget(target, spaceId: spaceId)
            try scope.withCurrent(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
                isPerformingOriginalAction = true
            }
        } catch { reportOriginalFailure(scope); return }
        let action = scope.prepareAction(requiredPermissions: OriginalEditorPropertyScope.listPermissions) { [self] in
            guard let original = relationsInteractor as? PropertiesInteractor,
                  original.originalEditorScope === scope else {
                throw OriginalEditorPropertyModalError.unsupportedOriginalDelegate
            }
            let completed: PropertyDetails
            switch mode {
            case .create:
                // Do not automatically repeat an uncertain native creation.
                // Its original record is retained even if later attachment fails.
                try scope.withCurrent { originalCreationStarted = true }
                completed = try await original.createProperty(spaceId: spaceId, relation: details)
                try scope.withCurrent { createdOriginalProperty = completed }
                try await original.addPropertyToObject(objectId: scope.objectId, relation: completed)
            case .edit:
                completed = try await original.updateOriginalProperty(spaceId: spaceId, relation: details)
            }
            try scope.withActionCallback(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
                onSuccessfullAction(relationDetails: completed)
                onCompletion?()
            }
        }
        Task { [self] in
            do { try await action() }
            catch { reportOriginalFailure(scope) }
            try? scope.withCurrent { isPerformingOriginalAction = false }
        }
    }

    private func reportOriginalFailure(_ scope: OriginalEditorPropertyScope) {
        try? scope.withCurrent {
            toastData = ToastBarData(Loc.error, type: .failure)
        }
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
        if let scope = originalEditorScope {
            try? scope.withCurrent {
                guard !isReadOnly, mode.canEditRelationType else { return }
                format = newFormat
                handleFormatUpdate()
            }
            return
        }
        format = newFormat
        handleFormatUpdate()
    }
    
    func updateTypesRestriction(objectTypeIds: [String]) {
        if let scope = originalEditorScope {
            do {
                try scope.withCurrent {
                    guard objectTypeProvider is ObjectTypeProvider else {
                        throw OriginalEditorPropertyModalError.unsupportedOriginalDelegate
                    }
                    let originalTypes = try objectTypeIds.map { try objectTypeProvider.objectType(id: $0) }
                    guard originalTypes.allSatisfy({ $0.spaceId.utf8.elementsEqual(spaceId.utf8) }) else {
                        throw EditorDocumentWriteError.rejected(.wrongContext)
                    }
                    objectTypes = originalTypes
                }
            } catch { reportOriginalFailure(scope) }
            return
        }
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
