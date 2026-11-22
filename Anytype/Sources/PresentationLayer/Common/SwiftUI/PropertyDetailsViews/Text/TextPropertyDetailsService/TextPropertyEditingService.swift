import Foundation
import Services

protocol TextPropertyEditingServiceProtocol: AnyObject, Sendable {
    func saveRelation(objectId: String, value: String, key: String, textType: TextPropertyViewType)
}

extension TextPropertyEditingServiceProtocol {
    @MainActor
    func saveRelation(objectId: String, value: String, key: String,
                      textType: TextPropertyViewType, originalEditorScope: OriginalEditorPropertyScope?) {
        guard let scope = originalEditorScope else {
            saveRelation(objectId: objectId, value: value, key: key, textType: textType)
            return
        }
        scope.schedule {
            guard let original = self as? TextPropertyEditingService else {
                throw OriginalPropertiesServiceBindingError.unsupportedOriginalDelegate
            }
            try scope.owner.performSynchronousOperation(contextId: objectId, spaceId: scope.spaceId,
                                                        requiresEditing: false) {}
            let service = try scope.originalProperties(original.service)
            try await original.writeRelation(objectId: objectId, value: value, key: key,
                                             textType: textType, service: service)
        }
    }
}

final class TextPropertyEditingService: TextPropertyEditingServiceProtocol, Sendable {

    fileprivate let service: any PropertiesServiceProtocol = Container.shared.propertiesService()
    
    private let numberFormatter = NumberFormatter.decimalWithNoSeparator
    
    // MARK: - TextRelationDetailsServiceProtocol
    
    func saveRelation(objectId: String, value: String, key: String, textType: TextPropertyViewType) {
        Task {
            try await writeRelation(objectId: objectId, value: value, key: key, textType: textType, service: service)
        }
    }

    /// Both routes execute the same original conversion and native service call.
    fileprivate func writeRelation(objectId: String, value: String, key: String,
                                   textType: TextPropertyViewType,
                                   service: any PropertiesServiceProtocol) async throws {
        switch textType {
        case .text:
            try await service.updateProperty(objectId: objectId, propertyKey: key, value: value.protobufValue)
        case .number, .numberOfDays:
            guard let number = numberFormatter.number(from: value)?.doubleValue else { return }
            try await service.updateProperty(objectId: objectId, propertyKey: key, value: number.protobufValue)
        case .phone, .email, .url:
            let value = value.replacing(" ", with: "")
            try await service.updateProperty(objectId: objectId, propertyKey: key, value: value.protobufValue)
        }
    }
}
