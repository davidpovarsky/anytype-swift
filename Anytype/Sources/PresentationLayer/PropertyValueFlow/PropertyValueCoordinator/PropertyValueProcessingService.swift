import Foundation
import AnytypeCore
import Services

@MainActor
protocol PropertyValueProcessingServiceProtocol {
    func handlePropertyValue(
        relation: Property,
        objectDetails: ObjectDetails,
        analyticsType: AnalyticsEventsRelationType
    ) -> PropertyValueData?
}

extension PropertyValueProcessingServiceProtocol {
    /// Configured embedding keeps the actual original processor and the same
    /// prepared document. Existing three-argument callers retain their route.
    func handlePropertyValue(
        relation: Property, objectDetails: ObjectDetails,
        analyticsType: AnalyticsEventsRelationType,
        preparedSession: PreparedEditorPageSession?
    ) -> PropertyValueData? {
        guard let preparedSession else {
            return handlePropertyValue(relation: relation, objectDetails: objectDetails, analyticsType: analyticsType)
        }
        guard let original = self as? PropertyValueProcessingService else { return nil }
        return original.handlePropertyValue(
            relation: relation, objectDetails: objectDetails, analyticsType: analyticsType,
            scope: OriginalEditorPropertyScope(
                preparedSession: preparedSession, objectId: objectDetails.id, spaceId: objectDetails.spaceId
            )
        )
    }
}

@MainActor
fileprivate final class PropertyValueProcessingService: PropertyValueProcessingServiceProtocol {
    
    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol
    @Injected(\.propertyDetailsStorage)
    private var propertyDetailsStorage: any PropertyDetailsStorageProtocol
    
    nonisolated init() {}
    
    func handlePropertyValue(
        relation: Property,
        objectDetails: ObjectDetails,
        analyticsType: AnalyticsEventsRelationType
    ) -> PropertyValueData? {
        handlePropertyValue(relation: relation, objectDetails: objectDetails, analyticsType: analyticsType, scope: nil)
    }

    fileprivate func handlePropertyValue(
        relation: Property, objectDetails: ObjectDetails,
        analyticsType: AnalyticsEventsRelationType, scope: OriginalEditorPropertyScope?
    ) -> PropertyValueData? {
        if let scope {
            do { try scope.withCurrent {} } catch { return nil }
        }
        switch relation {
        case .status, .tag, .object, .date, .file, .text, .number, .url, .email, .phone:
            return PropertyValueData(
                relation: relation,
                objectDetails: objectDetails, 
                analyticsType: analyticsType,
                preparedSession: scope?.preparedSession
            )
        case .checkbox(let checkbox):
            guard relation.isEditable else { return nil }
            let operation: @MainActor @Sendable () async throws -> Void = { [self] in
                let newValue = !checkbox.value
                let service: any PropertiesServiceProtocol
                if let scope { service = try scope.originalProperties(propertiesService) }
                else { service = propertiesService }
                try await service.updateProperty(objectId: objectDetails.id, propertyKey: checkbox.key, value: newValue.protobufValue)
                let publish = {
                    let relationDetails = try self.propertyDetailsStorage.relationsDetails(key: relation.key, spaceId: objectDetails.spaceId)
                    AnytypeAnalytics.instance().logChangeOrDeleteRelationValue(
                        isEmpty: !newValue,
                        format: relationDetails.format,
                        type: analyticsType,
                        key: relationDetails.analyticsKey
                    )
                }
                if let scope { try scope.withCurrent(requiredPermissions: OriginalEditorPropertyScope.valuePermissions, publish) }
                else { try publish() }
            }
            if let scope { scope.schedule(operation: operation) }
            else { Task { try await operation() } }
        case .unknown:
            return nil
        }
        
        return nil
    }
}

struct PropertyValueData: Identifiable {
    let id = UUID()
    let relation: Property
    let objectDetails: ObjectDetails
    let analyticsType: AnalyticsEventsRelationType
    let preparedSession: PreparedEditorPageSession?

    init(relation: Property, objectDetails: ObjectDetails,
         analyticsType: AnalyticsEventsRelationType,
         preparedSession: PreparedEditorPageSession? = nil) {
        self.relation = relation
        self.objectDetails = objectDetails
        self.analyticsType = analyticsType
        self.preparedSession = preparedSession
    }
}

extension Container {
    var propertyValueProcessingService: Factory<any PropertyValueProcessingServiceProtocol> {
        self { PropertyValueProcessingService() }.shared
    }
}
