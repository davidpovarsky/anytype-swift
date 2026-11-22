import Foundation
import SwiftUI
import Services

@MainActor
@Observable
final class PropertyOptionSettingsViewModel {

    var text: String
    var selectedColor: Color

    let colors: [Color]
    let configuration: PropertyOptionSettingsConfiguration

    @ObservationIgnored
    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol

    @ObservationIgnored
    private let completion: (_ optionParams: PropertyOptionParameters) -> Void
    
    init(
        configuration: PropertyOptionSettingsConfiguration,
        completion: @escaping (_ optionParams: PropertyOptionParameters) -> Void
    ) {
        self.text = configuration.option.text
        self.selectedColor = configuration.option.color
        self.configuration = configuration
        self.completion = completion
        self.colors = MiddlewareColor.allCasesWithoutDefault.map { Color.Dark.color(from: $0) }
    }
    
    func onColorSelected( _ color: Color) {
        try? withCurrentSource { selectedColor = color }
    }
    
    func onButtonTap() {
        guard (try? withCurrentSource {}) != nil else { return }
        switch configuration.mode {
        case let .create(data):
            create(with: data)
        case .edit:
            edit()
        }
    }

    private var originalEditorScope: OriginalEditorPropertyScope? {
        configuration.originalPropertyConfiguration?.originalEditorScope
    }

    private func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        if let scope = originalEditorScope { return try scope.withCurrent(operation) }
        return try operation()
    }

    private func schedule(_ operation: @escaping @MainActor @Sendable () async throws -> Void) {
        if let scope = originalEditorScope { scope.schedule(operation: operation) }
        else { Task { try await operation() } }
    }

    private func withActionCallback<Value>(_ operation: () throws -> Value) throws -> Value {
        if let scope = originalEditorScope { return try scope.withActionCallback(operation) }
        return try operation()
    }
    
    private func create(with data: PropertyOptionSettingsMode.CreateData) {
        schedule { [self] in
            if let original = configuration.originalPropertyConfiguration, original.preparedSession != nil {
                guard data.spaceId.utf8.elementsEqual(original.spaceId.utf8),
                      data.relationKey.utf8.elementsEqual(original.relationKey.utf8) else {
                    throw EditorDocumentWriteError.rejected(.wrongContext)
                }
            }
            let service = try originalEditorScope?.originalProperties(propertiesService) ?? propertiesService
            let optionId = try await service.addPropertyOption(
                spaceId: data.spaceId,
                propertyKey: data.relationKey,
                optionText: text,
                color: selectedColor.middlewareString()
            )
            
            guard let optionId else { return }

            if let scope = originalEditorScope {
                // Verify the original returned object in the same actual Space
                // before publishing its selection. This is a child prepared by
                // the original factory, never a relabeled page owner.
                try await scope.withSelectedObjects(ids: [optionId], requiredPermissions: [.editDetails]) {}
            }
            
            try withActionCallback {
                completion(
                    PropertyOptionParameters(
                        id: optionId,
                        text: text,
                        color: selectedColor
                    )
                )
            }
        }
    }
    
    private func edit() {
        schedule { [self] in
            let service = try originalEditorScope?.originalProperties(propertiesService) ?? propertiesService
            let operation: @MainActor @Sendable () async throws -> Void = { [self] in
                try await service.updatePropertyOption(
                    id: configuration.option.id,
                    text: text,
                    color: selectedColor.middlewareString()
                )
            }
            if let scope = originalEditorScope {
                try await scope.withSelectedObjects(ids: [configuration.option.id], requiredPermissions: [.editDetails], operation: operation)
            } else { try await operation() }
            try withCurrentSource {
                completion(
                    PropertyOptionParameters(
                        id: configuration.option.id,
                        text: text,
                        color: selectedColor
                    )
                )
            }
        }
    }
}
