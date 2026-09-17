import Foundation
import Testing
@testable import PinkhaKit

// MARK: - Mock Implementations (using Swift Actors)

actor MockManifestStore: PinkhaSpaceManifestStoreProtocol {
    var manifests: [String: PinkhaSpaceManifest] = [:]
    var saveCallCount = 0
    var loadCallCount = 0

    func loadManifest(spaceId: String) async throws -> PinkhaSpaceManifest? {
        loadCallCount += 1
        return manifests[spaceId]
    }

    func saveManifest(_ manifest: PinkhaSpaceManifest) async throws -> PinkhaSpaceManifest {
        saveCallCount += 1
        var toSave = manifest
        if toSave.manifestObjectId == nil {
            toSave.manifestObjectId = "obj_manifest_\(manifest.spaceId)"
        }
        manifests[manifest.spaceId] = toSave
        return toSave
    }

    func discoverManifestObjectId(spaceId: String) async throws -> String? {
        manifests[spaceId]?.manifestObjectId
    }

    func getManifest(spaceId: String) -> PinkhaSpaceManifest? {
        manifests[spaceId]
    }

    func getSaveCount() -> Int {
        saveCallCount
    }
}

actor MockPropertyService: PinkhaPropertyServiceProtocol {
    var createdProperties: [PinkhaPropertyDescriptor] = []
    var createCallCount = 0

    func createProperty(name: String, format: String, isHidden: Bool, spaceId: String) async throws -> PinkhaPropertyDescriptor {
        createCallCount += 1
        let id = "prop_id_\(createCallCount)"
        let key = "prop_key_\(name)"
        let desc = PinkhaPropertyDescriptor(id: id, key: key, name: name)
        createdProperties.append(desc)
        return desc
    }

    func validatePropertyExists(propertyId: String, spaceId: String) async throws -> Bool {
        createdProperties.contains(where: { $0.id == propertyId })
    }

    func addExistingProperty(_ prop: PinkhaPropertyDescriptor) {
        createdProperties.append(prop)
    }

    func removeProperty(id: String) {
        createdProperties.removeAll(where: { $0.id == id })
    }

    func getCreateCount() -> Int {
        createCallCount
    }
}

actor MockTypeService: PinkhaTypeServiceProtocol {
    var createdTypes: [PinkhaTypeDescriptor] = []
    var existingUnrelatedTypes: [PinkhaTypeDescriptor] = []
    var createCallCount = 0

    func createType(name: String, pluralName: String, spaceId: String) async throws -> PinkhaTypeDescriptor {
        createCallCount += 1
        let id = "type_id_\(createCallCount)"
        let desc = PinkhaTypeDescriptor(id: id, name: name)
        createdTypes.append(desc)
        return desc
    }

    func validateTypeExists(typeId: String, spaceId: String) async throws -> Bool {
        createdTypes.contains(where: { $0.id == typeId }) || existingUnrelatedTypes.contains(where: { $0.id == typeId })
    }

    func addExistingUnrelatedType(_ type: PinkhaTypeDescriptor) {
        existingUnrelatedTypes.append(type)
    }

    func addExistingType(_ type: PinkhaTypeDescriptor) {
        createdTypes.append(type)
    }

    func removeType(id: String) {
        createdTypes.removeAll(where: { $0.id == id })
    }

    func getCreateCount() -> Int {
        createCallCount
    }

    func containsType(id: String) -> Bool {
        createdTypes.contains(where: { $0.id == id })
    }
}

actor MockTemplateService: PinkhaTemplateServiceProtocol {
    var createdTemplates: [String: String] = [:] // typeId -> templateId
    var shouldFail = false
    var createCallCount = 0

    func setShouldFail(_ fail: Bool) {
        shouldFail = fail
    }

    func createAndAssignDefaultTemplate(typeId: String, spaceId: String) async throws -> String {
        if shouldFail {
            throw PinkhaBootstrapError.templateCreationFailed("Mock template creation failure")
        }
        createCallCount += 1
        let templateId = "tmpl_\(typeId)_\(createCallCount)"
        createdTemplates[typeId] = templateId
        return templateId
    }

    func validateTemplateExists(templateId: String, spaceId: String) async throws -> Bool {
        createdTemplates.values.contains(templateId)
    }

    func removeTemplate(id: String) {
        createdTemplates = createdTemplates.filter { $0.value != id }
    }

    func getCreateCount() -> Int {
        createCallCount
    }
}

actor RaceCapableMockManifestStore: PinkhaSpaceManifestStoreProtocol {
    private var persistedManifests: [PinkhaSpaceManifest] = []
    private var loadCount = 0

    func loadManifest(spaceId: String) async throws -> PinkhaSpaceManifest? {
        loadCount += 1
        // Simulate race window: first 2 loads from concurrent clients both observe nil
        if loadCount <= 2 && persistedManifests.isEmpty {
            return nil
        }
        return getCanonicalManifest(spaceId: spaceId)
    }

    func saveManifest(_ manifest: PinkhaSpaceManifest) async throws -> PinkhaSpaceManifest {
        var toSave = manifest
        if toSave.manifestObjectId == nil {
            toSave.manifestObjectId = "obj_manifest_\(manifest.spaceId)_\(persistedManifests.count + 1)"
        }
        persistedManifests.append(toSave)
        return toSave
    }

    func discoverManifestObjectId(spaceId: String) async throws -> String? {
        getCanonicalManifest(spaceId: spaceId)?.manifestObjectId
    }

    func getCanonicalManifest(spaceId: String) -> PinkhaSpaceManifest? {
        let matching = persistedManifests.filter { $0.spaceId == spaceId }
        guard !matching.isEmpty else { return nil }
        return matching.sorted { m1, m2 in
            if m1.isComplete != m2.isComplete { return m1.isComplete }
            if m1.schemaVersion != m2.schemaVersion { return m1.schemaVersion > m2.schemaVersion }
            if m1.updatedAt != m2.updatedAt { return m1.updatedAt > m2.updatedAt }
            return (m1.manifestObjectId ?? "") < (m2.manifestObjectId ?? "")
        }.first
    }

    func allPersistedManifests() -> [PinkhaSpaceManifest] {
        persistedManifests
    }
}

// MARK: - Test Suite

@Suite("PinkhaSpaceBootstrapEngineTests")
struct PinkhaSpaceBootstrapEngineTests {

    private func makeEngine(
        store: MockManifestStore = MockManifestStore(),
        propService: MockPropertyService = MockPropertyService(),
        typeService: MockTypeService = MockTypeService(),
        templateService: MockTemplateService = MockTemplateService(),
        migrator: PinkhaSchemaMigrator = PinkhaSchemaMigrator()
    ) -> (PinkhaSpaceBootstrapEngine, MockManifestStore, MockPropertyService, MockTypeService, MockTemplateService) {
        let engine = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService,
            migrator: migrator
        )
        return (engine, store, propService, typeService, templateService)
    }

    // 1. Fresh Space bootstrap provisions schema and persists manifest
    @Test("Fresh space bootstrap provisions schema and persists manifest")
    func testFreshBootstrapProvisionsSchema() async throws {
        let (engine, store, propService, typeService, templateService) = makeEngine()
        let spaceId = "space_fresh_001"

        let manifest = try await engine.bootstrapSpace(spaceId: spaceId)

        #expect(manifest.isFullyProvisioned)
        #expect(manifest.provisioningState == .complete)
        #expect(manifest.spaceId == spaceId)
        #expect(manifest.manifestObjectId != nil)

        // 3 properties created
        let propCount = await propService.getCreateCount()
        #expect(propCount == 3)
        #expect(!manifest.parentPropertyId.isEmpty)
        #expect(!manifest.orderPropertyId.isEmpty)
        #expect(!manifest.documentAssociationsPropertyId.isEmpty)

        // 5 types created: folder, bookFolder, chiddush, article, research
        let typeCount = await typeService.getCreateCount()
        #expect(typeCount == 5)
        #expect(!manifest.folderTypeId.isEmpty)
        #expect(!manifest.bookFolderTypeId.isEmpty)
        #expect(manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey] != nil)
        #expect(manifest.registeredDocumentTypes[PinkhaSchemaRoles.articleKey] != nil)
        #expect(manifest.registeredDocumentTypes[PinkhaSchemaRoles.researchKey] != nil)

        // 3 templates created for writing types
        let tmplCount = await templateService.getCreateCount()
        #expect(tmplCount == 3)
        #expect(manifest.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey] != nil)
        #expect(manifest.defaultTemplateIds[PinkhaSchemaRoles.articleKey] != nil)
        #expect(manifest.defaultTemplateIds[PinkhaSchemaRoles.researchKey] != nil)

        // Saved to store
        let stored = await store.getManifest(spaceId: spaceId)
        #expect(stored != nil)
        #expect(stored == manifest)
    }

    // 2. Second bootstrap in same service returns identical IDs with zero new creations
    @Test("Second bootstrap in same service reuses cache and creates nothing new")
    func testSecondBootstrapInSameService() async throws {
        let (engine, store, propService, typeService, templateService) = makeEngine()
        let spaceId = "space_cached_002"

        let first = try await engine.bootstrapSpace(spaceId: spaceId)
        let propsAfterFirst = await propService.getCreateCount()
        let typesAfterFirst = await typeService.getCreateCount()
        let tmplsAfterFirst = await templateService.getCreateCount()
        let savesAfterFirst = await store.getSaveCount()

        let second = try await engine.bootstrapSpace(spaceId: spaceId)

        #expect(first == second)
        let propsAfterSecond = await propService.getCreateCount()
        let typesAfterSecond = await typeService.getCreateCount()
        let tmplsAfterSecond = await templateService.getCreateCount()
        let savesAfterSecond = await store.getSaveCount()

        #expect(propsAfterSecond == propsAfterFirst)
        #expect(typesAfterSecond == typesAfterFirst)
        #expect(tmplsAfterSecond == tmplsAfterFirst)
        #expect(savesAfterSecond == savesAfterFirst) // Cache hit: no extra saves
    }

    // 3. New service instance reads the same persisted manifest (simulating app restart)
    @Test("New service instance reads same persisted manifest and creates zero new schema")
    func testNewServiceInstanceReadsPersistedManifest() async throws {
        let store = MockManifestStore()
        let propService = MockPropertyService()
        let typeService = MockTypeService()
        let templateService = MockTemplateService()
        let spaceId = "space_restart_003"

        // Engine 1 provisions
        let engine1 = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )
        let initialManifest = try await engine1.bootstrapSpace(spaceId: spaceId)

        let initialPropsCount = await propService.getCreateCount()
        let initialTypesCount = await typeService.getCreateCount()
        let initialTmplsCount = await templateService.getCreateCount()

        // Engine 2 (fresh instance with empty in-memory cache)
        let engine2 = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )
        let reloadedManifest = try await engine2.bootstrapSpace(spaceId: spaceId)

        #expect(reloadedManifest == initialManifest)
        #expect(reloadedManifest.parentPropertyId == initialManifest.parentPropertyId)
        #expect(reloadedManifest.orderPropertyId == initialManifest.orderPropertyId)
        #expect(reloadedManifest.folderTypeId == initialManifest.folderTypeId)
        #expect(reloadedManifest.registeredDocumentTypes == initialManifest.registeredDocumentTypes)
        #expect(reloadedManifest.defaultTemplateIds == initialManifest.defaultTemplateIds)

        // Zero new creations
        let propsCountAfter = await propService.getCreateCount()
        let typesCountAfter = await typeService.getCreateCount()
        let tmplsCountAfter = await templateService.getCreateCount()

        #expect(propsCountAfter == initialPropsCount)
        #expect(typesCountAfter == initialTypesCount)
        #expect(tmplsCountAfter == initialTmplsCount)
    }

    // 4. Simulated restart returns identical Property IDs and Type IDs
    @Test("Simulated restart returns identical Property IDs and Type IDs")
    func testSimulatedRestartIdenticalIds() async throws {
        let store = MockManifestStore()
        let propService = MockPropertyService()
        let typeService = MockTypeService()
        let templateService = MockTemplateService()
        let spaceId = "space_sim_004"

        let engine1 = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )
        let m1 = try await engine1.bootstrapSpace(spaceId: spaceId)

        // Simulate app shutdown and restart
        let engineAfterRestart = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )
        let m2 = try await engineAfterRestart.bootstrapSpace(spaceId: spaceId)

        #expect(m1.parentPropertyId == m2.parentPropertyId)
        #expect(m1.orderPropertyId == m2.orderPropertyId)
        #expect(m1.documentAssociationsPropertyId == m2.documentAssociationsPropertyId)
        #expect(m1.folderTypeId == m2.folderTypeId)
        #expect(m1.bookFolderTypeId == m2.bookFolderTypeId)
        #expect(m1.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey] == m2.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey])
    }

    // 5. Sequential two instances sharing persisted state reuse existing manifest
    @Test("Sequential two instances reuse existing manifest")
    func testSequentialTwoInstancesReuseExistingManifest() async throws {
        let store = MockManifestStore()
        let propService = MockPropertyService()
        let typeService = MockTypeService()
        let templateService = MockTemplateService()
        let spaceId = "space_converge_005"

        let clientA = PinkhaSpaceBootstrapEngine(store: store, propertyService: propService, typeService: typeService, templateService: templateService)
        let clientB = PinkhaSpaceBootstrapEngine(store: store, propertyService: propService, typeService: typeService, templateService: templateService)

        let manifestA = try await clientA.bootstrapSpace(spaceId: spaceId)
        let manifestB = try await clientB.bootstrapSpace(spaceId: spaceId)

        #expect(manifestA == manifestB)
        #expect(clientB.manifest(forSpaceId: spaceId) == manifestA)
    }

    // 6. No duplicate Property creation after manifest exists
    @Test("Zero duplicate property creations after manifest exists")
    func testNoDuplicatePropertyCreation() async throws {
        let (engine, _, propService, _, _) = makeEngine()
        let spaceId = "space_prop_dedup_006"

        _ = try await engine.bootstrapSpace(spaceId: spaceId)
        let count1 = await propService.getCreateCount()
        #expect(count1 == 3)

        _ = try await engine.bootstrapSpace(spaceId: spaceId)
        let count2 = await propService.getCreateCount()
        #expect(count2 == 3)
    }

    // 7. No duplicate Type creation after manifest exists
    @Test("Zero duplicate type creations after manifest exists")
    func testNoDuplicateTypeCreation() async throws {
        let (engine, _, _, typeService, _) = makeEngine()
        let spaceId = "space_type_dedup_007"

        _ = try await engine.bootstrapSpace(spaceId: spaceId)
        let count1 = await typeService.getCreateCount()
        #expect(count1 == 5)

        _ = try await engine.bootstrapSpace(spaceId: spaceId)
        let count2 = await typeService.getCreateCount()
        #expect(count2 == 5)
    }

    // 8. Unrelated user Type named "חידוש" is NOT adopted as Pinkha's Type
    @Test("Existing unrelated user type named חידוש is not adopted")
    func testUnrelatedUserTypeNotAdopted() async throws {
        let typeService = MockTypeService()
        // Simulate pre-existing user-created type named "חידוש"
        let userChiddushType = PinkhaTypeDescriptor(id: "user_custom_type_999", name: "חידוש")
        await typeService.addExistingUnrelatedType(userChiddushType)

        let (engine, _, _, _, _) = makeEngine(typeService: typeService)
        let spaceId = "space_unrelated_008"

        let manifest = try await engine.bootstrapSpace(spaceId: spaceId)
        let pinkhaChiddushId = manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey]

        // Pinkha created its own type and did NOT adopt the user's type
        #expect(pinkhaChiddushId != userChiddushType.id)
        #expect(pinkhaChiddushId != nil)
        let containsPinkha = await typeService.containsType(id: pinkhaChiddushId!)
        #expect(containsPinkha)
    }

    // 9. Interrupted/partial bootstrap resumes without duplicate provisioning
    @Test("Partial bootstrap resumes cleanly from missing steps")
    func testPartialBootstrapResumes() async throws {
        let store = MockManifestStore()
        let propService = MockPropertyService()
        let typeService = MockTypeService()
        let templateService = MockTemplateService()
        let spaceId = "space_resume_009"

        // Simulate interrupted state: manifest was saved with properties and 1 type, then process died
        var partialManifest = PinkhaSpaceManifest.initial(spaceId: spaceId)
        partialManifest.manifestObjectId = "obj_manifest_\(spaceId)"
        partialManifest.parentPropertyId = "existing_parent_prop"
        partialManifest.parentPropertyKey = "key_parent"
        partialManifest.orderPropertyId = "existing_order_prop"
        partialManifest.orderPropertyKey = "key_order"
        partialManifest.documentAssociationsPropertyId = "existing_assoc_prop"
        partialManifest.documentAssociationsPropertyKey = "key_assoc"
        partialManifest.folderTypeId = "existing_folder_type"
        _ = try await store.saveManifest(partialManifest)

        // Register the partial existing IDs in mock validators
        await propService.addExistingProperty(PinkhaPropertyDescriptor(id: "existing_parent_prop", key: "key_parent", name: "הורה"))
        await propService.addExistingProperty(PinkhaPropertyDescriptor(id: "existing_order_prop", key: "key_order", name: "סדר"))
        await propService.addExistingProperty(PinkhaPropertyDescriptor(id: "existing_assoc_prop", key: "key_assoc", name: "הקשר תורני"))
        await typeService.addExistingType(PinkhaTypeDescriptor(id: "existing_folder_type", name: "תיקייה"))

        let engine = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )

        let completedManifest = try await engine.bootstrapSpace(spaceId: spaceId)

        #expect(completedManifest.isFullyProvisioned)
        // Properties were NOT recreated!
        let propCreateCount = await propService.getCreateCount()
        #expect(propCreateCount == 0)
        #expect(completedManifest.parentPropertyId == "existing_parent_prop")
        #expect(completedManifest.folderTypeId == "existing_folder_type")

        // Missing types and templates were created
        #expect(!completedManifest.bookFolderTypeId.isEmpty)
        #expect(completedManifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey] != nil)
        #expect(completedManifest.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey] != nil)
    }

    // 10. Template creation failure does not report success
    @Test("Template creation failure throws error and preserves inProgress state")
    func testTemplateFailureDoesNotReportSuccess() async throws {
        let templateService = MockTemplateService()
        await templateService.setShouldFail(true)

        let (engine, store, _, _, _) = makeEngine(templateService: templateService)
        let spaceId = "space_fail_tmpl_010"

        await #expect(throws: PinkhaBootstrapError.self) {
            _ = try await engine.bootstrapSpace(spaceId: spaceId)
        }

        // Manifest in store should NOT be marked complete
        let stored = await store.getManifest(spaceId: spaceId)
        #expect(stored?.provisioningState == .inProgress)
        #expect(stored?.isComplete == false)
    }

    // 11. Schema migration is applied and validated
    @Test("Schema migration validates current schema version")
    func testSchemaMigration() throws {
        let migrator = PinkhaSchemaMigrator()
        let manifest = PinkhaSpaceManifest(spaceId: "space_mig_011")

        let migrated = try migrator.migrate(manifest: manifest)
        #expect(migrated.schemaVersion == PinkhaSpaceManifest.currentSchemaVersion)
    }

    // 12. Newer unsupported schema is rejected and not overwritten
    @Test("Unsupported newer schema version throws error and is not overwritten")
    func testUnsupportedNewerSchemaRejected() async throws {
        let store = MockManifestStore()
        let spaceId = "space_future_012"

        // Store a manifest with schemaVersion = 99
        var futureManifest = PinkhaSpaceManifest(spaceId: spaceId)
        futureManifest.schemaVersion = 99
        _ = try await store.saveManifest(futureManifest)

        let (engine, _, _, _, _) = makeEngine(store: store)

        await #expect(throws: PinkhaBootstrapError.self) {
            _ = try await engine.bootstrapSpace(spaceId: spaceId)
        }

        // Verify the store was NOT overwritten
        let storedAfter = await store.getManifest(spaceId: spaceId)
        #expect(storedAfter?.schemaVersion == 99)
    }

    // 13. Concurrent bootstraps select a canonical manifest in store
    @Test("Concurrent bootstraps select a canonical manifest in store")
    func testConcurrentBootstrapsSelectCanonicalManifest() async throws {
        let store = RaceCapableMockManifestStore()
        let propService = MockPropertyService()
        let typeService = MockTypeService()
        let templateService = MockTemplateService()
        let spaceId = "space_concurrent_013"

        let clientA = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )
        let clientB = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )

        // Run both clients concurrently, modeling true simultaneous bootstrap
        async let runA = clientA.bootstrapSpace(spaceId: spaceId)
        async let runB = clientB.bootstrapSpace(spaceId: spaceId)

        let (manifestA, manifestB) = try await (runA, runB)

        #expect(manifestA.isFullyProvisioned)
        #expect(manifestB.isFullyProvisioned)

        // When queried from store afterwards, reconciliation returns a single canonical manifest
        let canonical = try await store.loadManifest(spaceId: spaceId)
        #expect(canonical != nil)
        #expect(canonical?.isFullyProvisioned == true)

        let allManifests = await store.allPersistedManifests()
        #expect(allManifests.count >= 2)
    }

    // 14. Invalid reference repair: missing parent property recreated only
    @Test("Repair missing parent property recreates only parent property")
    func testRepairMissingParentPropertyRecreatesOnlyParentProperty() async throws {
        let (engine, store, propService, typeService, templateService) = makeEngine()
        let spaceId = "space_repair_parent_014"

        let initial = try await engine.bootstrapSpace(spaceId: spaceId)
        #expect(initial.isFullyProvisioned)
        let initialPropCount = await propService.getCreateCount()
        let initialTypeCount = await typeService.getCreateCount()
        let initialTmplCount = await templateService.getCreateCount()

        // Delete parent property from space
        await propService.removeProperty(id: initial.parentPropertyId)

        // New engine instance without in-memory cache
        let engine2 = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )

        let repaired = try await engine2.bootstrapSpace(spaceId: spaceId)
        #expect(repaired.isFullyProvisioned)
        #expect(repaired.parentPropertyId != initial.parentPropertyId)
        #expect(repaired.orderPropertyId == initial.orderPropertyId)
        #expect(repaired.documentAssociationsPropertyId == initial.documentAssociationsPropertyId)
        #expect(repaired.folderTypeId == initial.folderTypeId)

        let newPropCount = await propService.getCreateCount()
        let newTypeCount = await typeService.getCreateCount()
        let newTmplCount = await templateService.getCreateCount()

        // Exactly 1 new property created, 0 new types, 0 new templates
        #expect(newPropCount == initialPropCount + 1)
        #expect(newTypeCount == initialTypeCount)
        #expect(newTmplCount == initialTmplCount)
    }

    // 15. Invalid reference repair: missing order property recreated only
    @Test("Repair missing order property recreates only order property")
    func testRepairMissingOrderPropertyRecreatesOnlyOrderProperty() async throws {
        let (engine, store, propService, typeService, templateService) = makeEngine()
        let spaceId = "space_repair_order_015"

        let initial = try await engine.bootstrapSpace(spaceId: spaceId)
        #expect(initial.isFullyProvisioned)
        let initialPropCount = await propService.getCreateCount()

        // Delete order property
        await propService.removeProperty(id: initial.orderPropertyId)

        let engine2 = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )

        let repaired = try await engine2.bootstrapSpace(spaceId: spaceId)
        #expect(repaired.isFullyProvisioned)
        #expect(repaired.orderPropertyId != initial.orderPropertyId)
        #expect(repaired.parentPropertyId == initial.parentPropertyId)
        #expect(repaired.documentAssociationsPropertyId == initial.documentAssociationsPropertyId)

        let newPropCount = await propService.getCreateCount()
        #expect(newPropCount == initialPropCount + 1)
    }

    // 16. Invalid reference repair: missing Torah associations property recreated only
    @Test("Repair missing Torah associations property recreates only Torah property")
    func testRepairMissingTorahPropertyRecreatesOnlyTorahProperty() async throws {
        let (engine, store, propService, typeService, templateService) = makeEngine()
        let spaceId = "space_repair_torah_016"

        let initial = try await engine.bootstrapSpace(spaceId: spaceId)
        #expect(initial.isFullyProvisioned)
        let initialPropCount = await propService.getCreateCount()

        // Delete associations property
        await propService.removeProperty(id: initial.documentAssociationsPropertyId)

        let engine2 = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )

        let repaired = try await engine2.bootstrapSpace(spaceId: spaceId)
        #expect(repaired.isFullyProvisioned)
        #expect(repaired.documentAssociationsPropertyId != initial.documentAssociationsPropertyId)
        #expect(repaired.parentPropertyId == initial.parentPropertyId)
        #expect(repaired.orderPropertyId == initial.orderPropertyId)

        let newPropCount = await propService.getCreateCount()
        #expect(newPropCount == initialPropCount + 1)
    }

    // 17. Invalid reference repair: missing folder type recreated only
    @Test("Repair missing folder type recreates only folder type")
    func testRepairMissingFolderTypeRecreatesOnlyFolderType() async throws {
        let (engine, store, propService, typeService, templateService) = makeEngine()
        let spaceId = "space_repair_folder_017"

        let initial = try await engine.bootstrapSpace(spaceId: spaceId)
        #expect(initial.isFullyProvisioned)
        let initialPropCount = await propService.getCreateCount()
        let initialTypeCount = await typeService.getCreateCount()

        // Delete folder type
        await typeService.removeType(id: initial.folderTypeId)

        let engine2 = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )

        let repaired = try await engine2.bootstrapSpace(spaceId: spaceId)
        #expect(repaired.isFullyProvisioned)
        #expect(repaired.folderTypeId != initial.folderTypeId)
        #expect(repaired.bookFolderTypeId == initial.bookFolderTypeId)

        let newPropCount = await propService.getCreateCount()
        let newTypeCount = await typeService.getCreateCount()
        #expect(newPropCount == initialPropCount)
        #expect(newTypeCount == initialTypeCount + 1)
    }

    // 18. Invalid reference repair: missing writing type recreates type and template only
    @Test("Repair missing writing type recreates writing type and template")
    func testRepairMissingWritingTypeRecreatesTypeAndTemplate() async throws {
        let (engine, store, propService, typeService, templateService) = makeEngine()
        let spaceId = "space_repair_writing_018"

        let initial = try await engine.bootstrapSpace(spaceId: spaceId)
        #expect(initial.isFullyProvisioned)
        let chiddushId = initial.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey]!
        let initialPropCount = await propService.getCreateCount()
        let initialTypeCount = await typeService.getCreateCount()
        let initialTmplCount = await templateService.getCreateCount()

        // Delete chiddush type
        await typeService.removeType(id: chiddushId)

        let engine2 = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )

        let repaired = try await engine2.bootstrapSpace(spaceId: spaceId)
        #expect(repaired.isFullyProvisioned)
        #expect(repaired.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey] != chiddushId)
        #expect(repaired.registeredDocumentTypes[PinkhaSchemaRoles.articleKey] == initial.registeredDocumentTypes[PinkhaSchemaRoles.articleKey])

        let newPropCount = await propService.getCreateCount()
        let newTypeCount = await typeService.getCreateCount()
        let newTmplCount = await templateService.getCreateCount()

        // 0 new properties, exactly 1 new type (chiddush), 1 new template (for chiddush)
        #expect(newPropCount == initialPropCount)
        #expect(newTypeCount == initialTypeCount + 1)
        #expect(newTmplCount == initialTmplCount + 1)
    }

    // 19. Invalid reference repair: missing default template recreates template only
    @Test("Repair missing default template recreates only template")
    func testRepairMissingTemplateRecreatesOnlyTemplate() async throws {
        let (engine, store, propService, typeService, templateService) = makeEngine()
        let spaceId = "space_repair_template_019"

        let initial = try await engine.bootstrapSpace(spaceId: spaceId)
        #expect(initial.isFullyProvisioned)
        let articleTmplId = initial.defaultTemplateIds[PinkhaSchemaRoles.articleKey]!
        let initialPropCount = await propService.getCreateCount()
        let initialTypeCount = await typeService.getCreateCount()
        let initialTmplCount = await templateService.getCreateCount()

        // Delete article template
        await templateService.removeTemplate(id: articleTmplId)

        let engine2 = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )

        let repaired = try await engine2.bootstrapSpace(spaceId: spaceId)
        #expect(repaired.isFullyProvisioned)
        #expect(repaired.defaultTemplateIds[PinkhaSchemaRoles.articleKey] != articleTmplId)
        #expect(repaired.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey] == initial.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey])

        let newPropCount = await propService.getCreateCount()
        let newTypeCount = await typeService.getCreateCount()
        let newTmplCount = await templateService.getCreateCount()

        // 0 new properties, 0 new types, exactly 1 new template
        #expect(newPropCount == initialPropCount)
        #expect(newTypeCount == initialTypeCount)
        #expect(newTmplCount == initialTmplCount + 1)
    }

    // 20. Decisive convergence: cached loser engine re-bootstrap converges on canonical manifest
    @Test("Decisive convergence: cached-loser engines re-bootstrap to same canonical manifest without new schema")
    func testCachedLoserEngineConvergesOnCanonicalManifest() async throws {
        let store = RaceCapableMockManifestStore()
        let propService = MockPropertyService()
        let typeService = MockTypeService()
        let templateService = MockTemplateService()
        let spaceId = "space_decisive_convergence_020"

        let clientA = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )
        let clientB = PinkhaSpaceBootstrapEngine(
            store: store,
            propertyService: propService,
            typeService: typeService,
            templateService: templateService
        )

        // 1. Initial concurrent bootstrap: both engines bootstrap against empty store
        async let runA = clientA.bootstrapSpace(spaceId: spaceId)
        async let runB = clientB.bootstrapSpace(spaceId: spaceId)
        let (initialA, initialB) = try await (runA, runB)

        #expect(initialA.isFullyProvisioned)
        #expect(initialB.isFullyProvisioned)

        // Store selected one canonical winner
        let canonicalWinner = try await store.loadManifest(spaceId: spaceId)
        #expect(canonicalWinner != nil)

        let propCountAfterInitial = await propService.getCreateCount()
        let typeCountAfterInitial = await typeService.getCreateCount()
        let tmplCountAfterInitial = await templateService.getCreateCount()

        // 2. WITHOUT recreating either engine instance, call bootstrapSpace again on BOTH
        let convergedA = try await clientA.bootstrapSpace(spaceId: spaceId)
        let convergedB = try await clientB.bootstrapSpace(spaceId: spaceId)

        // 3. Both must now return the EXACT SAME canonical manifest
        #expect(convergedA == convergedB)
        #expect(convergedA == canonicalWinner)
        #expect(convergedB == canonicalWinner)

        #expect(convergedA.manifestObjectId == canonicalWinner?.manifestObjectId)
        #expect(convergedA.parentPropertyId == canonicalWinner?.parentPropertyId)
        #expect(convergedA.orderPropertyId == canonicalWinner?.orderPropertyId)
        #expect(convergedA.documentAssociationsPropertyId == canonicalWinner?.documentAssociationsPropertyId)
        #expect(convergedA.folderTypeId == canonicalWinner?.folderTypeId)
        #expect(convergedA.bookFolderTypeId == canonicalWinner?.bookFolderTypeId)
        #expect(convergedA.registeredDocumentTypes == canonicalWinner?.registeredDocumentTypes)
        #expect(convergedA.defaultTemplateIds == canonicalWinner?.defaultTemplateIds)

        // 4. Verify no new schema objects were created during this convergence pass
        let propCountAfterConvergence = await propService.getCreateCount()
        let typeCountAfterConvergence = await typeService.getCreateCount()
        let tmplCountAfterConvergence = await templateService.getCreateCount()

        #expect(propCountAfterConvergence == propCountAfterInitial)
        #expect(typeCountAfterConvergence == typeCountAfterInitial)
        #expect(tmplCountAfterConvergence == tmplCountAfterInitial)
    }
}
