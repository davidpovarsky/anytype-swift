import Foundation
import PinkhaKit
import Services
import AnytypeCore
import Factory

public enum PinkhaBootstrapError: Error {
    case disabled
    case propertyCreationFailed(String)
    case typeCreationFailed(String)
    case templateCreationFailed(String)
}

public protocol PinkhaSpaceBootstrapServiceProtocol: Sendable {
    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest
    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest?
    func isBootstrapped(spaceId: String) -> Bool
}

public final class PinkhaSpaceBootstrapService: PinkhaSpaceBootstrapServiceProtocol, @unchecked Sendable {
    private let lock = NSLock()
    private var cachedManifests: [String: PinkhaSpaceManifest] = [:]

    @Injected(\.typesService)
    private var typesService: any TypesServiceProtocol

    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol

    @Injected(\.templatesService)
    private var templatesService: any TemplatesServiceProtocol

    public init() {}

    public func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? {
        lock.lock()
        defer { lock.unlock() }
        return cachedManifests[spaceId]
    }

    public func isBootstrapped(spaceId: String) -> Bool {
        manifest(forSpaceId: spaceId) != nil
    }

    public func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
        guard PinkhaRuntime.enabled else {
            throw PinkhaBootstrapError.disabled
        }

        lock.lock()
        if let existing = cachedManifests[spaceId] {
            lock.unlock()
            return existing
        }
        lock.unlock()

        // 1. Query existing object types in the space
        let existingTypes = try await typesService.searchObjectTypes(
            text: "",
            includePins: true,
            includeLists: true,
            includeBookmarks: true,
            includeFiles: true,
            includeChat: true,
            includeTemplates: true,
            incudeNotForCreation: true,
            spaceId: spaceId
        )

        // 2. Resolve or create required Properties
        // Parent property (object relation)
        let parentProp = try await resolveOrCreateProperty(
            name: "הורה",
            format: .object,
            isHidden: false,
            spaceId: spaceId
        )

        // Sibling order property (sparse numeric rank)
        let orderProp = try await resolveOrCreateProperty(
            name: "סדר",
            format: .number,
            isHidden: true,
            spaceId: spaceId
        )

        // Document-level Torah associations property (JSON payload)
        let assocProp = try await resolveOrCreateProperty(
            name: "הקשר תורני",
            format: .longText,
            isHidden: true,
            spaceId: spaceId
        )

        // 3. Resolve or create internal navigation types
        let folderType = try await resolveOrCreateType(
            name: PinkhaSchemaRoles.folderDefaultName,
            pluralName: "תיקיות",
            existingTypes: existingTypes,
            spaceId: spaceId
        )

        let bookFolderType = try await resolveOrCreateType(
            name: PinkhaSchemaRoles.bookFolderDefaultName,
            pluralName: "תיקיות ספרים",
            existingTypes: existingTypes,
            spaceId: spaceId
        )

        // 4. Resolve or create default writing types
        let chiddushType = try await resolveOrCreateWritingType(
            name: PinkhaSchemaRoles.chiddushDefaultName,
            pluralName: "חידושים",
            existingTypes: existingTypes,
            spaceId: spaceId
        )

        let articleType = try await resolveOrCreateWritingType(
            name: PinkhaSchemaRoles.articleDefaultName,
            pluralName: "מאמרים",
            existingTypes: existingTypes,
            spaceId: spaceId
        )

        let researchType = try await resolveOrCreateWritingType(
            name: PinkhaSchemaRoles.researchDefaultName,
            pluralName: "מחקרים",
            existingTypes: existingTypes,
            spaceId: spaceId
        )

        // 5. Build and cache Manifest
        let manifest = PinkhaSpaceManifest(
            schemaVersion: PinkhaSpaceManifest.currentSchemaVersion,
            spaceId: spaceId,
            parentPropertyId: parentProp.id,
            parentPropertyKey: parentProp.key,
            orderPropertyId: orderProp.id,
            orderPropertyKey: orderProp.key,
            documentAssociationsPropertyId: assocProp.id,
            documentAssociationsPropertyKey: assocProp.key,
            folderTypeId: folderType.id,
            bookFolderTypeId: bookFolderType.id,
            registeredDocumentTypes: [
                PinkhaSchemaRoles.chiddushKey: chiddushType.id,
                PinkhaSchemaRoles.articleKey: articleType.id,
                PinkhaSchemaRoles.researchKey: researchType.id
            ]
        )

        lock.lock()
        cachedManifests[spaceId] = manifest
        lock.unlock()

        return manifest
    }

    // MARK: - Private Helpers

    private func resolveOrCreateProperty(
        name: String,
        format: PropertyFormat,
        isHidden: Bool,
        spaceId: String
    ) async throws -> PropertyDetails {
        let details = PropertyDetails(
            id: "",
            key: "",
            name: name,
            format: format,
            isHidden: isHidden,
            isReadOnly: false,
            isReadOnlyValue: false,
            objectTypes: [],
            maxCount: 1,
            sourceObject: "",
            isDeleted: false,
            spaceId: spaceId
        )
        return try await propertiesService.createProperty(spaceId: spaceId, propertyDetails: details)
    }

    private func resolveOrCreateType(
        name: String,
        pluralName: String,
        existingTypes: [ObjectDetails],
        spaceId: String
    ) async throws -> ObjectType {
        if let existing = existingTypes.first(where: { $0.name == name && !$0.isDeleted }) {
            return ObjectType(details: existing)
        }
        return try await typesService.createType(
            name: name,
            pluralName: pluralName,
            icon: nil,
            color: nil,
            spaceId: spaceId
        )
    }

    private func resolveOrCreateWritingType(
        name: String,
        pluralName: String,
        existingTypes: [ObjectDetails],
        spaceId: String
    ) async throws -> ObjectType {
        if let existing = existingTypes.first(where: { $0.name == name && !$0.isDeleted }) {
            return ObjectType(details: existing)
        }

        let createdType = try await typesService.createType(
            name: name,
            pluralName: pluralName,
            icon: nil,
            color: nil,
            spaceId: spaceId
        )

        // Create and set default template for new writing type
        do {
            let templateId = try await templatesService.createTemplateFromObjectType(
                objectTypeId: createdType.id,
                spaceId: spaceId
            )
            try await templatesService.setTemplateAsDefaultForType(
                objectTypeId: createdType.id,
                templateId: templateId
            )
        } catch {
            // Non-fatal: template can be attached or customized subsequently
        }

        return createdType
    }
}
