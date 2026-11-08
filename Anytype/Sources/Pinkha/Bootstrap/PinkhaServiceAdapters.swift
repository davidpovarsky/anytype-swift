import Foundation
import PinkhaKit
import Services
import AnytypeCore
import Factory
import SwiftProtobuf
import ProtobufMessages

public final class AnytypePropertyServiceAdapter: PinkhaPropertyServiceProtocol, Sendable {
    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol

    public init() {}

    public func createProperty(name: String, format: String, isHidden: Bool, spaceId: String) async throws -> PinkhaPropertyDescriptor {
        let propFormat: PropertyFormat
        switch format {
        case "object": propFormat = .object
        case "number": propFormat = .number
        case "longText": propFormat = .longText
        default: propFormat = .shortText
        }

        let details = PropertyDetails(
            id: "",
            key: "",
            name: name,
            format: propFormat,
            isHidden: isHidden,
            isReadOnly: false,
            isReadOnlyValue: false,
            objectTypes: [],
            maxCount: 1,
            sourceObject: "",
            isDeleted: false,
            spaceId: spaceId
        )

        let created = try await propertiesService.createProperty(spaceId: spaceId, propertyDetails: details)
        return PinkhaPropertyDescriptor(id: created.id, key: created.key, name: created.name)
    }

    public func validatePropertyExists(propertyId: String, spaceId: String) async throws -> Bool {
        guard !propertyId.isEmpty else { return false }
        do {
            _ = try await ClientCommands.objectShow(.with {
                $0.contextID = propertyId
                $0.objectID = propertyId
                $0.spaceID = spaceId
            }).invoke(qos: .userInitiated, ignoreLogErrors: .objectDeleted)
            return true
        } catch {
            return false
        }
    }
}

public final class AnytypeTypeServiceAdapter: PinkhaTypeServiceProtocol, Sendable {
    @Injected(\.typesService)
    private var typesService: any TypesServiceProtocol
    @Injected(\.detailsService)
    private var detailsService: any DetailsServiceProtocol

    public init() {}

    public func createType(name: String, pluralName: String, spaceId: String) async throws -> PinkhaTypeDescriptor {
        let (icon, color): (CustomIcon?, CustomIconColor?) = {
            if name.contains("חידוש") || pluralName.contains("חידושים") {
                return (.bulb, .yellow)
            } else if name.contains("מאמר") || pluralName.contains("מאמרים") {
                return (.documentText, .blue)
            } else if name.contains("מחקר") || pluralName.contains("מחקרים") {
                return (.library, .purple)
            } else {
                return (nil, nil)
            }
        }()

        let created = try await typesService.createType(
            name: name,
            pluralName: pluralName,
            icon: icon,
            color: color,
            spaceId: spaceId
        )

        // Configure recommendedLayout as .basic on the Type so that default templates and documents
        // inherit .basic layout (which supports native icons and descriptions)
        try? await detailsService.updateBundledDetails(
            objectId: created.id,
            bundledDetails: [.recommendedLayout(DetailsLayout.basic.rawValue)]
        )

        return PinkhaTypeDescriptor(id: created.id, name: created.name)
    }

    public func validateTypeExists(typeId: String, spaceId: String) async throws -> Bool {
        guard !typeId.isEmpty else { return false }
        do {
            _ = try await ClientCommands.objectShow(.with {
                $0.contextID = typeId
                $0.objectID = typeId
                $0.spaceID = spaceId
            }).invoke(qos: .userInitiated, ignoreLogErrors: .objectDeleted)
            return true
        } catch {
            return false
        }
    }
}

public final class AnytypeTemplateServiceAdapter: PinkhaTemplateServiceProtocol, Sendable {
    @Injected(\.templatesService)
    private var templatesService: any TemplatesServiceProtocol
    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol

    public init() {}

    public func createAndAssignDefaultTemplate(typeId: String, spaceId: String) async throws -> String {
        let templateId = try await templatesService.createTemplateFromObjectType(
            objectTypeId: typeId,
            spaceId: spaceId
        )
        try await templatesService.setTemplateAsDefaultForType(
            objectTypeId: typeId,
            templateId: templateId
        )

        // Make description visible by default on the new default Torah template
        try? await propertiesService.toggleDescription(objectId: templateId, isOn: true)

        return templateId
    }

    public func validateTemplateExists(templateId: String, spaceId: String) async throws -> Bool {
        guard !templateId.isEmpty else { return false }
        do {
            _ = try await ClientCommands.objectShow(.with {
                $0.contextID = templateId
                $0.objectID = templateId
                $0.spaceID = spaceId
            }).invoke(qos: .userInitiated, ignoreLogErrors: .objectDeleted)
            return true
        } catch {
            return false
        }
    }
}
