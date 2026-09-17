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
        let templateId = "tmpl_\(typeId)"
        createdTemplates[typeId] = templateId
        return templateId
    }

    func validateTemplateExists(templateId: String, spaceId: String) async throws -> Bool {
        createdTemplates.values.contains(templateId)
    }

    func getCreateCount() -> Int {
        createCallCount
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

    // 5. Two service instances sharing persisted state converge on the same manifest
    @Test("Two service instances converge on same manifest")
    func testTwoInstancesConverge() async throws {
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
}
