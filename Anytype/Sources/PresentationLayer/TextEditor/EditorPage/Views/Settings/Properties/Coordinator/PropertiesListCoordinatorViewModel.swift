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
        guard (try? withCurrentSource {
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
        // The original Type editor mutates a different existing document and
        // its schema. Its own prepared child is required before presentation.
        guard preparedSession == nil else { return }
        AnytypeAnalytics.instance().logScreenEditType(route: .object)
        objectTypeData = EditorTypeObject(objectId: typeId, spaceId: document.spaceId)
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
