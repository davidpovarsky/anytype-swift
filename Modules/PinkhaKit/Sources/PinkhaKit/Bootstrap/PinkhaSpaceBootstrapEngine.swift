import Foundation

public protocol PinkhaSpaceBootstrapEngineProtocol: Sendable {
    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest
    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest?
    func isBootstrapped(spaceId: String) -> Bool
}

/// Core bootstrap engine that orchestrates idempotent, crash-safe schema provisioning.
public final class PinkhaSpaceBootstrapEngine: PinkhaSpaceBootstrapEngineProtocol, Sendable {

    private final class CacheContainer: @unchecked Sendable {
        private let lock = NSLock()
        private var manifests: [String: PinkhaSpaceManifest] = [:]

        func get(_ spaceId: String) -> PinkhaSpaceManifest? {
            lock.lock()
            defer { lock.unlock() }
            return manifests[spaceId]
        }

        func set(_ spaceId: String, manifest: PinkhaSpaceManifest) {
            lock.lock()
            defer { lock.unlock() }
            manifests[spaceId] = manifest
        }
    }

    private let cache = CacheContainer()
    private let store: any PinkhaSpaceManifestStoreProtocol
    private let propertyService: any PinkhaPropertyServiceProtocol
    private let typeService: any PinkhaTypeServiceProtocol
    private let templateService: any PinkhaTemplateServiceProtocol
    private let migrator: PinkhaSchemaMigrator

    public init(
        store: any PinkhaSpaceManifestStoreProtocol,
        propertyService: any PinkhaPropertyServiceProtocol,
        typeService: any PinkhaTypeServiceProtocol,
        templateService: any PinkhaTemplateServiceProtocol,
        migrator: PinkhaSchemaMigrator = PinkhaSchemaMigrator()
    ) {
        self.store = store
        self.propertyService = propertyService
        self.typeService = typeService
        self.templateService = templateService
        self.migrator = migrator
    }

    public func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? {
        cache.get(spaceId)
    }

    public func isBootstrapped(spaceId: String) -> Bool {
        manifest(forSpaceId: spaceId)?.isFullyProvisioned == true
    }

    public func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
        guard PinkhaRuntime.enabled else {
            throw PinkhaBootstrapError.disabled
        }

        // 1. Fast path: check in-memory cache
        if let cached = cache.get(spaceId), cached.isFullyProvisioned {
            return cached
        }

        // 2. Load synced manifest from store
        var loadedManifest: PinkhaSpaceManifest?
        do {
            loadedManifest = try await store.loadManifest(spaceId: spaceId)
        } catch {
            throw PinkhaBootstrapError.manifestStoreError("Failed to load manifest: \(error.localizedDescription)")
        }

        // 3. Migrate if present
        if let existing = loadedManifest {
            do {
                loadedManifest = try migrator.migrate(manifest: existing)
            } catch let error as PinkhaSchemaMigrationError {
                throw PinkhaBootstrapError.migrationError(error)
            } catch {
                throw PinkhaBootstrapError.migrationError(.migrationFailed(error.localizedDescription))
            }
        }

        // 4. If fully provisioned and all IDs valid, cache and return
        if let existing = loadedManifest, existing.isFullyProvisioned {
            let valid = try await validateReferencedIds(existing, spaceId: spaceId)
            if valid {
                cache.set(spaceId, manifest: existing)
                return existing
            }
        }

        // 5. Initialize or resume manifest
        var manifest = loadedManifest ?? PinkhaSpaceManifest.initial(spaceId: spaceId)

        // If manifest has no objectId yet, save initial in-progress state to obtain object ID
        if manifest.manifestObjectId == nil {
            manifest = try await store.saveManifest(manifest)
        }

        // 6. Stepwise Property Provisioning (incremental save)
        if manifest.parentPropertyId.isEmpty || manifest.parentPropertyKey.isEmpty {
            let prop = try await propertyService.createProperty(
                name: "הורה",
                format: "object",
                isHidden: false,
                spaceId: spaceId
            )
            manifest.parentPropertyId = prop.id
            manifest.parentPropertyKey = prop.key
            manifest.updatedAt = Date()
            manifest = try await store.saveManifest(manifest)
        }

        if manifest.orderPropertyId.isEmpty || manifest.orderPropertyKey.isEmpty {
            let prop = try await propertyService.createProperty(
                name: "סדר",
                format: "number",
                isHidden: true,
                spaceId: spaceId
            )
            manifest.orderPropertyId = prop.id
            manifest.orderPropertyKey = prop.key
            manifest.updatedAt = Date()
            manifest = try await store.saveManifest(manifest)
        }

        if manifest.documentAssociationsPropertyId.isEmpty || manifest.documentAssociationsPropertyKey.isEmpty {
            let prop = try await propertyService.createProperty(
                name: "הקשר תורני",
                format: "longText",
                isHidden: true,
                spaceId: spaceId
            )
            manifest.documentAssociationsPropertyId = prop.id
            manifest.documentAssociationsPropertyKey = prop.key
            manifest.updatedAt = Date()
            manifest = try await store.saveManifest(manifest)
        }

        // 7. Stepwise Type Provisioning (incremental save, never adopt by display name)
        if manifest.folderTypeId.isEmpty {
            let type = try await typeService.createType(
                name: PinkhaSchemaRoles.folderDefaultName,
                pluralName: "תיקיות",
                spaceId: spaceId
            )
            manifest.folderTypeId = type.id
            manifest.updatedAt = Date()
            manifest = try await store.saveManifest(manifest)
        }

        if manifest.bookFolderTypeId.isEmpty {
            let type = try await typeService.createType(
                name: PinkhaSchemaRoles.bookFolderDefaultName,
                pluralName: "תיקיות ספרים",
                spaceId: spaceId
            )
            manifest.bookFolderTypeId = type.id
            manifest.updatedAt = Date()
            manifest = try await store.saveManifest(manifest)
        }

        if manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey] == nil {
            let type = try await typeService.createType(
                name: PinkhaSchemaRoles.chiddushDefaultName,
                pluralName: "חידושים",
                spaceId: spaceId
            )
            manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey] = type.id
            manifest.updatedAt = Date()
            manifest = try await store.saveManifest(manifest)
        }

        if manifest.registeredDocumentTypes[PinkhaSchemaRoles.articleKey] == nil {
            let type = try await typeService.createType(
                name: PinkhaSchemaRoles.articleDefaultName,
                pluralName: "מאמרים",
                spaceId: spaceId
            )
            manifest.registeredDocumentTypes[PinkhaSchemaRoles.articleKey] = type.id
            manifest.updatedAt = Date()
            manifest = try await store.saveManifest(manifest)
        }

        if manifest.registeredDocumentTypes[PinkhaSchemaRoles.researchKey] == nil {
            let type = try await typeService.createType(
                name: PinkhaSchemaRoles.researchDefaultName,
                pluralName: "מחקרים",
                spaceId: spaceId
            )
            manifest.registeredDocumentTypes[PinkhaSchemaRoles.researchKey] = type.id
            manifest.updatedAt = Date()
            manifest = try await store.saveManifest(manifest)
        }

        // 8. Stepwise Default Templates (do NOT catch/swallow errors, record template IDs)
        for (role, typeId) in [
            (PinkhaSchemaRoles.chiddushKey, manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey]!),
            (PinkhaSchemaRoles.articleKey, manifest.registeredDocumentTypes[PinkhaSchemaRoles.articleKey]!),
            (PinkhaSchemaRoles.researchKey, manifest.registeredDocumentTypes[PinkhaSchemaRoles.researchKey]!)
        ] {
            if manifest.defaultTemplateIds[role] == nil {
                do {
                    let templateId = try await templateService.createAndAssignDefaultTemplate(
                        typeId: typeId,
                        spaceId: spaceId
                    )
                    manifest.defaultTemplateIds[role] = templateId
                    manifest.updatedAt = Date()
                    manifest = try await store.saveManifest(manifest)
                } catch {
                    // Do not mark complete; throw so caller knows template creation failed!
                    throw PinkhaBootstrapError.templateCreationFailed("Failed to create template for role \(role): \(error.localizedDescription)")
                }
            }
        }

        // 9. Mark Complete and Persist
        manifest.provisioningState = .complete
        manifest.updatedAt = Date()
        manifest = try await store.saveManifest(manifest)

        cache.set(spaceId, manifest: manifest)
        return manifest
    }

    private func validateReferencedIds(_ manifest: PinkhaSpaceManifest, spaceId: String) async throws -> Bool {
        guard try await propertyService.validatePropertyExists(propertyId: manifest.parentPropertyId, spaceId: spaceId),
              try await propertyService.validatePropertyExists(propertyId: manifest.orderPropertyId, spaceId: spaceId),
              try await propertyService.validatePropertyExists(propertyId: manifest.documentAssociationsPropertyId, spaceId: spaceId) else {
            return false
        }

        guard try await typeService.validateTypeExists(typeId: manifest.folderTypeId, spaceId: spaceId),
              try await typeService.validateTypeExists(typeId: manifest.bookFolderTypeId, spaceId: spaceId) else {
            return false
        }

        for (_, typeId) in manifest.registeredDocumentTypes {
            guard try await typeService.validateTypeExists(typeId: typeId, spaceId: spaceId) else {
                return false
            }
        }

        for (_, templateId) in manifest.defaultTemplateIds {
            guard try await templateService.validateTemplateExists(templateId: templateId, spaceId: spaceId) else {
                return false
            }
        }

        return true
    }
}
