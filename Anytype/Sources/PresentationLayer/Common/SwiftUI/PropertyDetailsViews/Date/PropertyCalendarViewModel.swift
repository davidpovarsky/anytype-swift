import Services
import Foundation

@MainActor
protocol PropertyCalendarOutput: AnyObject {
    func onOpenDateSelected(date: Date)
}

@MainActor
@Observable
final class PropertyCalendarViewModel {

    var date: Date
    var dismiss = false

    let config: PropertyModuleConfiguration

    @ObservationIgnored
    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol
    @ObservationIgnored
    @Injected(\.propertyDetailsStorage)
    private var propertyDetailsStorage: any PropertyDetailsStorageProtocol

    @ObservationIgnored
    private weak var output: (any PropertyCalendarOutput)?
    
    init(date: Date?, configuration: PropertyModuleConfiguration, output: (any PropertyCalendarOutput)?) {
        self.date = date ?? Date()
        self.config = configuration
        self.output = output
    }
    
    func dateChanged(_ newDate: Date) {
        guard (try? config.withCurrentOriginalProperty {}) != nil else { return }
        let date = newDate.trimTime() ??  newDate
        let value = date.timeIntervalSince1970
        self.date = newDate
        updateDateRelation(with: value)
    }
    
    func clear() {
        guard (try? config.withCurrentOriginalProperty {}) != nil else { return }
        updateDateRelation(with: 0)
        dismiss.toggle()
    }
    
    func onOpenCurrentDateSelected() {
        try? config.withCurrentOriginalProperty { output?.onOpenDateSelected(date: date) }
    }
    
    private func updateDateRelation(with value: Double) {
        let scope = config.originalEditorScope
        let operation: @MainActor @Sendable () async throws -> Void = { [self] in
            let service: any PropertiesServiceProtocol
            if let scope { service = try scope.originalProperties(propertiesService) }
            else { service = propertiesService }
            try await service.updateProperty(objectId: config.objectId, propertyKey: config.relationKey, value: value.protobufValue)
            let publish = {
                let relationDetails = try self.propertyDetailsStorage.relationsDetails(key: self.config.relationKey, spaceId: self.config.spaceId)
                AnytypeAnalytics.instance().logChangeOrDeleteRelationValue(
                    isEmpty: value.isZero,
                    format: relationDetails.format,
                    type: self.config.analyticsType,
                    key: relationDetails.analyticsKey
                )
            }
            if let scope { try scope.withCurrent(requiredPermissions: OriginalEditorPropertyScope.valuePermissions, publish) }
            else { try publish() }
        }
        if let scope { scope.schedule(operation: operation) }
        else { Task { try await operation() } }
    }
}
