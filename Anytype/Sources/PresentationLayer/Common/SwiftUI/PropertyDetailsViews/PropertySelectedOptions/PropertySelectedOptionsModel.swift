import Combine
import Services

@MainActor
protocol PropertySelectedOptionsModelProtocol {
    var config: PropertyModuleConfiguration { get }
    var selectedOptionsIdsPublisher: AnyPublisher<[String], Never> { get }
    
    func onClear() async throws
    func optionSelected(_ optionId: String) async throws
    func removeRelationOption(_ optionId: String) async throws
    func removeRelationOptionFromSelectedIfNeeded(_ optionId: String) async throws
}

@MainActor
final class PropertySelectedOptionsModel: PropertySelectedOptionsModelProtocol {
    
    @Published private var selectedOptionsIds: [String] = []
    var selectedOptionsIdsPublisher: AnyPublisher<[String], Never> { $selectedOptionsIds.eraseToAnyPublisher() }
    
    let config: PropertyModuleConfiguration
    
    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol
    @Injected(\.propertyDetailsStorage)
    private var propertyDetailsStorage: any PropertyDetailsStorageProtocol
    
    init(config: PropertyModuleConfiguration, selectedOptionsIds: [String]) {
        self.config = config
        self.selectedOptionsIds = selectedOptionsIds
    }
    
    func onClear() async throws {
        try await config.performOriginalPropertyAction { [self] in
            let service = try config.originalPropertiesService(propertiesService)
            try config.withCurrentOriginalProperty { selectedOptionsIds = [] }
            try await service.updateProperty(objectId: config.objectId, propertyKey: config.relationKey, value: [String]().protobufValue)
            try config.withCurrentOriginalProperty { logChanges() }
        }
    }
    
    func optionSelected(_ optionId: String) async throws {
        try await config.performOriginalPropertyAction { [self] in
            let service = try config.originalPropertiesService(propertiesService)
            try config.withCurrentOriginalProperty {
                switch config.selectionMode {
                case .single:
                    selectedOptionsIds = [optionId]
                case .multi:
                    handleMultiOptionSelected(optionId)
                }
            }
            try await service.updateProperty(
                objectId: config.objectId,
                propertyKey: config.relationKey,
                value: selectedOptionsIds.protobufValue
            )
            try config.withCurrentOriginalProperty { logChanges() }
        }
    }

    func removeRelationOption(_ optionId: String) async throws {
        try await config.performOriginalPropertyAction { [self] in
            let service = try config.originalPropertiesService(propertiesService)
            if let scope = config.originalEditorScope {
                try await scope.withSelectedObjects(ids: [optionId], requiredPermissions: [.editDetails, .archive]) {
                    try await service.removePropertyOptions(ids: [optionId])
                }
            } else {
                try await service.removePropertyOptions(ids: [optionId])
            }
            try config.withCurrentOriginalProperty {}
            try await removeRelationOptionFromSelectedIfNeeded(optionId)
        }
    }

    func removeRelationOptionFromSelectedIfNeeded(_ optionId: String) async throws {
        try await config.performOriginalPropertyAction { [self] in
            let service = try config.originalPropertiesService(propertiesService)
            let index = try config.withCurrentOriginalProperty { selectedOptionsIds.firstIndex(of: optionId) }
            if let index {
                try config.withCurrentOriginalProperty { selectedOptionsIds.remove(at: index) }
                try await service.updateProperty(
                    objectId: config.objectId,
                    propertyKey: config.relationKey,
                    value: selectedOptionsIds.protobufValue
                )
                try config.withCurrentOriginalProperty {}
            }
        }
    }
    
    private func handleMultiOptionSelected(_ optionId: String) {
        if let index = selectedOptionsIds.firstIndex(of: optionId) {
            selectedOptionsIds.remove(at: index)
        } else {
            selectedOptionsIds.append(optionId)
        }
    }
    
    private func logChanges() {
        Task {
            try config.withCurrentOriginalProperty {
                let relationDetails = try propertyDetailsStorage.relationsDetails(key: config.relationKey, spaceId: config.spaceId)
                AnytypeAnalytics.instance().logChangeOrDeleteRelationValue(
                    isEmpty: selectedOptionsIds.isEmpty,
                    format: relationDetails.format,
                    type: config.analyticsType,
                    key: relationDetails.analyticsKey
                )
            }
        }
    }
}
