import SwiftUI
import Services
import AnytypeCore

struct PropertiesListData: Identifiable {
    let document: any BaseDocumentProtocol
    var id: String { document.objectId }
}

@MainActor
@Observable
final class PropertiesListCoordinatorViewModel:
    PropertiesListModuleOutput,
    PropertyValueCoordinatorOutput
{
    var relationValueData: PropertyValueData?
    var relationsSearchData: PropertiesSearchData?
    var objectTypeData: EditorTypeObject?
    var showTypePicker = false
    var typePropertiesToast: ToastBarData?

    private(set) var preparedTypePropertiesSession: PreparedEditorPageSession?
    @ObservationIgnored
    private var typePreparationTask: Task<Void, Never>?

    let document: any BaseDocumentProtocol

    @ObservationIgnored
    let preparedSession: PreparedEditorPageSession?

    @ObservationIgnored
    @Injected(\.propertyValueProcessingService)
    private var propertyValueProcessingService: any PropertyValueProcessingServiceProtocol
    @ObservationIgnored
    @Injected(\.objectActionsService)
    private var objectActionsService: any ObjectActionsServiceProtocol

    @ObservationIgnored
    private weak var output: (any PropertyValueCoordinatorOutput)?

    init(document: some BaseDocumentProtocol, output: (any PropertyValueCoordinatorOutput)?,
         preparedSession: PreparedEditorPageSession? = nil) {
        self.document = document
        self.output = output
        self.preparedSession = preparedSession
    }

    private var originalEditorScope: OriginalEditorPropertyScope? {
        preparedSession.map {
            OriginalEditorPropertyScope(preparedSession: $0, objectId: document.objectId,
                                        spaceId: document.spaceId, document: document)
        }
    }

    private func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        if let scope = originalEditorScope { return try scope.withCurrent(operation) }
        return try operation()
    }
    
    // MARK: - PropertiesListModuleOutput
    
    func editRelationValueAction(document: some BaseDocumentProtocol, relationKey: String) {
        if let scope = originalEditorScope {
            editOriginalRelationValue(document: document, relationKey: relationKey, scope: scope)
            return
        }
        guard (try? withCurrentSource { () -> Void in
            try preparedSession?.owner.validateDocument(document)
        }) != nil else { return }
        let relation = document.parsedProperties.installed.first { $0.key == relationKey }
        guard let relation = relation else {
            anytypeAssertionFailure("Relation not found")
            return
        }
        
        guard let objectDetails = document.details else {
            anytypeAssertionFailure("Detaiils not found")
            return
        }
        
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: relation.id, key: relation.key, spaceId: document.spaceId
        ) else { return }
        handlePropertyValue(relation: relation, objectDetails: objectDetails)
    }

    /// Resolve canonical identity through the original current-account reader.
    /// No prepared value tap enters the policy's implicit bootstrap path.
    private func editOriginalRelationValue(
        document candidate: any BaseDocumentProtocol, relationKey: String,
        scope: OriginalEditorPropertyScope
    ) {
        do {
            let selected = try scope.withCurrent {
                try scope.owner.validateDocument(candidate)
                guard !relationKey.isEmpty, !relationKey.utf8.contains(0),
                      let relation = document.parsedProperties.installed.first(where: {
                          $0.key.utf8.elementsEqual(relationKey.utf8)
                      }) else {
                    throw EditorDocumentWriteError.rejected(.wrongContext)
                }
                return relation
            }
            let writesCheckbox: Bool
            if case .checkbox = selected { writesCheckbox = selected.isEditable }
            else { writesCheckbox = false }

            let operation: @MainActor @Sendable () async throws -> Void = { [self] in
                let identity = try await scope.loadModalPropertyIdentity()
                let present = {
                    try scope.owner.validateDocument(self.document)
                    guard let current = self.document.parsedProperties.installed.first(where: {
                        $0.key.utf8.elementsEqual(relationKey.utf8)
                    }), current.id.utf8.elementsEqual(selected.id.utf8),
                        current.key.utf8.elementsEqual(selected.key.utf8), current == selected,
                        let details = self.document.details,
                        details.id.utf8.elementsEqual(scope.objectId.utf8),
                        details.spaceId.utf8.elementsEqual(scope.spaceId.utf8) else {
                        throw EditorDocumentWriteError.rejected(.documentChanged)
                    }
                    try scope.requireOriginalPropertyValue(
                        propertyId: current.id, key: current.key, identity: identity
                    )
                    self.handlePropertyValue(relation: current, objectDetails: details)
                }
                if writesCheckbox {
                    // The original processor synchronously registers its real
                    // checkbox write; a publication read cannot authorize it.
                    try scope.withActionCallback(present)
                } else {
                    try scope.withCurrent(present)
                }
            }
            // Reserve the actual editable-checkbox action at the UI callback,
            // before the asynchronous canonical read or original Task starts.
            let action = writesCheckbox
                ? scope.prepareAction(operation: operation)
                : operation
            Task { [weak self] in
                do { try await action() }
                catch { self?.reportOriginalPropertyFailure(scope: scope) }
            }
        } catch { reportOriginalPropertyFailure(scope: scope) }
    }

    private func reportOriginalPropertyFailure(scope: OriginalEditorPropertyScope) {
        try? scope.withCurrent {
            typePropertiesToast = ToastBarData(Loc.error, type: .failure)
        }
    }
    
    private func handlePropertyValue(relation: Property, objectDetails: ObjectDetails) {
        guard (try? withCurrentSource {}) != nil else { return }
        if relation.key == BundledPropertyKey.type.rawValue && document.permissions.canChangeType {
            showTypePicker = true
        } else {
            relationValueData = propertyValueProcessingService.handlePropertyValue(
                relation: relation,
                objectDetails: objectDetails,
                analyticsType: .menu,
                preparedSession: preparedSession
            )
        }
    }
    
    func showTypeRelationsView(typeId: String) {
        if let scope = originalEditorScope {
            guard typePreparationTask == nil, objectTypeData == nil,
                  preparedTypePropertiesSession == nil else { return }
            do {
                try scope.withCurrent {}
                guard !typeId.isEmpty, !typeId.utf8.contains(0) else {
                    throw EditorDocumentWriteError.rejected(.wrongContext)
                }
                // Capture the current ancestry before the asynchronous open.
                // The selected type gets its own original document and owner.
                let preparation = try PreparedEditorChildPreparation(owner: scope.owner)
                let typeData = EditorTypeObject(objectId: typeId, spaceId: document.spaceId)
                typePreparationTask = Task { [weak self] in
                    guard let self else { return }
                    defer { typePreparationTask = nil }
                    do {
                        let child = try await preparation.prepare(
                            data: .init(objectId: typeId, spaceId: typeData.spaceId),
                            requiredPermissions: OriginalEditorPropertyScope.listPermissions
                        )
                        do {
                            try Task.checkCancellation()
                            try withCurrentSource {
                                self.preparedTypePropertiesSession = child
                                self.objectTypeData = typeData
                                AnytypeAnalytics.instance().logScreenEditType(route: .object)
                            }
                        } catch {
                            child.retire()
                            if preparedTypePropertiesSession === child {
                                preparedTypePropertiesSession = nil
                                objectTypeData = nil
                            }
                            throw error
                        }
                    } catch {
                        try? withCurrentSource {
                            self.typePropertiesToast = ToastBarData(Loc.error, type: .failure)
                        }
                    }
                }
            } catch {
                try? withCurrentSource {
                    typePropertiesToast = ToastBarData(Loc.error, type: .failure)
                }
            }
            return
        }
        AnytypeAnalytics.instance().logScreenEditType(route: .object)
        objectTypeData = EditorTypeObject(objectId: typeId, spaceId: document.spaceId)
    }

    func cancelTypePreparation() {
        typePreparationTask?.cancel()
    }

    func didDismissTypeProperties() {
        cancelTypePreparation()
        preparedTypePropertiesSession?.retire()
        preparedTypePropertiesSession = nil
    }
    
    func onTypeSelected(_ type: ObjectType) {
        guard (try? withCurrentSource { showTypePicker = false }) != nil else { return }
        let operation: @MainActor @Sendable () async throws -> Void = { [self] in
            let service = preparedSession?.services.viewModel.objectActionsService ?? objectActionsService
            try await service.setObjectType(objectId: document.objectId, typeUniqueKey: type.uniqueKey)
            try withCurrentSource {
                AnytypeAnalytics.instance().logChangeObjectType(type.analyticsType, route: .relationsList)
            }
        }
        if let scope = originalEditorScope {
            scope.schedule(requiredPermissions: [.editDetails, .changeType], operation: operation)
        } else { Task { try await operation() } }
    }
    
    // MARK: - PropertyValueCoordinatorOutput
    
    func showEditorScreen(data: ScreenData) {
        try? withCurrentSource { output?.showEditorScreen(data: data) }
    }
}
