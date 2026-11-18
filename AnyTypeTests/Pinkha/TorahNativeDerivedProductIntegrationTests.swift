import Foundation
import CryptoKit
import AnytypeCore
import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf
import Testing
@testable import Anytype

/// This suite MUST run alone in a fresh test-host process with the custom Heart.
/// It creates a new local-only wallet and Space; it never opens an owner Space.
@Suite("Native Torah product integration", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_NATIVE_DERIVED_ACCEPTANCE"] == "1"))
struct TorahNativeDerivedProductIntegrationTests {
    @MainActor
    @Test("Real schema, canonical writes, native Set filters, columns and live membership")
    func originalProductPipeline() async throws {
        Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)
        let auth = Container.shared.authService()
        let mnemonic = try await auth.createWallet()
        try Container.shared.seedService().saveSeed(mnemonic)
        _ = try await auth.createAccount(
            name: "Native derived disposable acceptance", iconOption: 1, imagePath: ""
        )
        let space = try await Container.shared.workspaceService().createSpace(
            name: "Native Torah disposable test", iconOption: 1, accessType: .private,
            useCase: .none, withChat: false, spaceType: .regular
        )
        let spaceId = space.spaceID
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceId)
        let bootstrap = Container.shared.pinkhaBootstrapService()
        let manifest: PinkhaSpaceManifest
        do {
            let concurrent = try await withThrowingTaskGroup(of: PinkhaSpaceManifest.self) { group in
                for _ in 0..<8 { group.addTask { try await bootstrap.bootstrapSpace(spaceId: spaceId) } }
                var values: [PinkhaSpaceManifest] = []
                for try await value in group { values.append(value) }
                return values
            }
            manifest = try #require(concurrent.first)
            #expect(concurrent.allSatisfy { $0.manifestObjectId == manifest.manifestObjectId })
        } catch {
            // Only the newly created disposable Space is inspected. Print schema
            // metadata needed to diagnose an actual engine/app binding failure.
            let rows = try await Container.shared.searchMiddleService().search(
                spaceId: spaceId, filters: [.with {
                    $0.relationKey = "name"; $0.condition = .equal
                    $0.value = PinkhaSchemaRoles.manifestName.protobufValue
                }], keys: ["id", "description", TorahNativePropertyDefinition.engineVersionKey], limit: 0
            )
            print("Native disposable bootstrap manifest count: \(rows.count)")
            for row in rows {
                let parsed = try? PinkhaSpaceManifest.fromJSONString(row.stringValue(for: "description"))
                print("Native disposable binding: decoded=\(parsed != nil) complete=\(parsed?.isFullyProvisioned == true) version=\(row.intValue(for: TorahNativePropertyDefinition.engineVersionKey) ?? 0)")
                if let parsed {
                    let property = try await show(parsed.documentAssociationsPropertyId, spaceId: spaceId)
                    print("Native disposable canonical Property: format=\(property.intValue(for: "relationFormat") ?? -1) layout=\(property.intValue(for: "layout") ?? -1) keyMatches=\(property.stringValue(for: "relationKey") == parsed.documentAssociationsPropertyKey) spaceMatches=\(property.spaceId == spaceId)")
                }
            }
            throw error
        }
        let schema = AnytypeTorahNativePropertyProvisioningStore()
        // Verify that the single initial bootstrapSpace call already waited for engineVersion == 1,
        // installed all 3 native properties, and attached them to all 3 writing Types without needing a second bootstrap call.
        #expect(bootstrap.isNativeSchemaProvisioned(spaceId: spaceId))
        let engineVer = try await schema.engineVersion(spaceId: spaceId, manifestObjectId: #require(manifest.manifestObjectId))
        #expect(engineVer == 1)

        var nativeProperties: [PropertyDetails] = []
        for definition in TorahNativePropertyDefinition.all {
            let descriptor = try #require(try await schema.property(key: definition.key, spaceId: spaceId))
            #expect(descriptor.isReadOnlyValue)
            #expect(descriptor.format == TorahNativePropertyDefinition.wireFormat)
            nativeProperties.append(PropertyDetails(details: try await show(descriptor.id, spaceId: spaceId)))
        }
        let expectedNativeKeys = Set(TorahNativePropertyDefinition.all.map(\.key))
        let expectedNativeIds = Set(nativeProperties.map(\.id))

        for typeId in manifest.registeredDocumentTypes.values {
            let attached = try await schema.attachedPropertyIds(typeId: typeId, spaceId: spaceId)
            #expect(expectedNativeIds.isSubset(of: Set(attached)))
        }
        let again = try await bootstrap.bootstrapSpace(spaceId: spaceId)
        #expect(manifest.registeredDocumentTypes == again.registeredDocumentTypes)
        #expect(manifest.defaultTemplateIds == again.defaultTemplateIds)
        #expect(manifest.documentAssociationsPropertyId == again.documentAssociationsPropertyId)

        print("Native product stage: Page, Note, custom Type and mixed Set")
        let universal = try await verifyUniversalProperties(manifest: manifest, nativeProperties: nativeProperties)
        print("Native product stage: original writing-Type object rows")
        let typeId = try #require(manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey])
        let search = Container.shared.searchMiddleService()
        var indexedTypes: [ObjectType] = []
        try await eventually {
            let found = try await search.search(spaceId: spaceId,
                filters: [SearchHelper.layoutFilter([.objectType])],
                keys: ObjectType.subscriptionKeys.map(\.rawValue), limit: 0)
            indexedTypes = found.map(ObjectType.init(details:))
            return Set(manifest.registeredDocumentTypes.values).isSubset(of: Set(indexedTypes.map(\.id)))
        }
        let document = try await Container.shared.objectActionsService().createObject(
            name: "Canonical native integration", typeUniqueKey: #require(indexedTypes.first { $0.id == typeId }).uniqueKey,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceId, origin: .none, templateId: manifest.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey]
        )

        // =========================================================================
        // REAL UI PIPELINE PROOF 1: Fresh Zero-Association Document Properties Sheet
        // BaseDocument -> PropertiesBuilder -> ObjectPropertiesViewModel -> visibleSections
        // =========================================================================
        let openedDoc = Container.shared.openedDocumentProvider().document(objectId: document.id, spaceId: spaceId)
        try await openedDoc.open()
        let coordinatorVM = PropertiesListCoordinatorViewModel(document: openedDoc, output: nil)
        let objectPropertiesVM = ObjectPropertiesViewModel(document: openedDoc, output: coordinatorVM)
        let torahPropertiesModel = PinkhaTorahPropertiesModel(document: openedDoc, session: nil)
        let objectSubTask = Task { await objectPropertiesVM.setupSubscriptions() }
        let torahObsTask = Task { await torahPropertiesModel.observeDocument() }
        defer {
            objectSubTask.cancel()
            torahObsTask.cancel()
        }

        #expect(torahPropertiesModel.showsLegacyProjectionRows == false)
        try await eventually {
            let visibleRels = torahPropertiesModel.visibleSections(objectPropertiesVM.sections).flatMap(\.relations)
            let visibleKeys = Set(visibleRels.map(\.key))
            return openedDoc.permissions.canEditRelationValues &&
                expectedNativeKeys.isSubset(of: visibleKeys) &&
                visibleRels.filter { expectedNativeKeys.contains($0.key) }.allSatisfy(\.isEditable)
        }
        let freshVisibleRelations = torahPropertiesModel.visibleSections(objectPropertiesVM.sections).flatMap(\.relations)
        #expect(torahPropertiesModel.isEligible == true)
        #expect(!freshVisibleRelations.contains { $0.id == manifest.orderPropertyId || $0.key == manifest.orderPropertyKey })
        #expect(!freshVisibleRelations.contains { $0.id == manifest.documentAssociationsPropertyId || $0.key == manifest.documentAssociationsPropertyKey })

        for def in TorahNativePropertyDefinition.all {
            let row = try #require(freshVisibleRelations.first { $0.key == def.key })
            guard case .tag(let tagModel) = row else {
                Issue.record("Expected native .tag row in ObjectPropertiesViewModel for \(def.key), got \(row)")
                return
            }
            #expect(tagModel.isEditable == true)
            #expect(tagModel.selectedTags.isEmpty)
            // Tapping the empty native row routes through PropertiesListCoordinatorViewModel -> relationValueData
            objectPropertiesVM.handleTapOnRelation(row)
            #expect(coordinatorVM.relationValueData?.relation.key == def.key)
            #expect(coordinatorVM.relationValueData?.objectDetails.id == document.id)
        }

        // =========================================================================
        // REAL UI PIPELINE PROOF 2: Type Properties Editor (TypePropertiesViewModel)
        // for all 3 Torah Writing Types (חידוש, מאמר, מחקר)
        // =========================================================================
        print("Native product stage: original Type editors")
        var retainedTypeDocuments: [String: any BaseDocumentProtocol] = [:]
        for role in [PinkhaSchemaRoles.chiddushKey, PinkhaSchemaRoles.articleKey, PinkhaSchemaRoles.researchKey] {
            let roleTypeId = try #require(manifest.registeredDocumentTypes[role])
            let typeDoc = Container.shared.openedDocumentProvider().document(objectId: roleTypeId, spaceId: spaceId)
            try await typeDoc.open()
            retainedTypeDocuments[roleTypeId] = typeDoc
            let typeVM = TypePropertiesViewModel(document: typeDoc)
            let typeSubTask = Task { await typeVM.setupSubscriptions() }
            defer { typeSubTask.cancel() }

            try await eventually {
                let rowKeys = Set(typeVM.relationRows.compactMap { row -> String? in
                    if case .relation(let r) = row { return r.relation.key }
                    return nil
                })
                return typeVM.canEditPropertiesList && expectedNativeKeys.isSubset(of: rowKeys)
            }
            let typeRelRows = typeVM.relationRows.compactMap { row -> TypePropertiesRelationRow? in
                if case .relation(let r) = row { return r }
                return nil
            }
            #expect(!typeRelRows.contains { $0.relation.id == manifest.orderPropertyId || $0.relation.key == manifest.orderPropertyKey })
            #expect(!typeRelRows.contains { $0.relation.id == manifest.documentAssociationsPropertyId || $0.relation.key == manifest.documentAssociationsPropertyKey })
        }

        // =========================================================================
        // REAL UI PIPELINE PROOF 3: Hide, Add Property Search, and Reveal Without Duplicate
        // =========================================================================
        print("Native product stage: Type hide and reveal")
        let chiddushTypeDoc = try #require(retainedTypeDocuments[typeId])
        let chiddushTypeVM = TypePropertiesViewModel(document: chiddushTypeDoc)
        let chiddushTypeSubTask = Task { await chiddushTypeVM.setupSubscriptions() }
        defer { chiddushTypeSubTask.cancel() }

        try await eventually {
            chiddushTypeVM.relationRows.contains {
                if case .relation(let r) = $0 { return r.relation.key == TorahNativePropertyDefinition.all[0].key }
                return false
            }
        }
        let sourcesRowInType = try #require(chiddushTypeVM.relationRows.compactMap { row -> TypePropertiesRelationRow? in
            if case .relation(let r) = row, r.relation.key == TorahNativePropertyDefinition.all[0].key { return r }
            return nil
        }.first)

        // Hide מקור/ות on the Type
        chiddushTypeVM.onRelationHide(sourcesRowInType)

        // Verify both TypePropertiesViewModel and the open document's ObjectPropertiesViewModel move מקור/ות to Hidden
        try await eventually {
            let hiddenSection = objectPropertiesVM.sections.first {
                $0.id == PropertiesSection.Constants.hiddenPropertiesSectionId
            }
            let isHiddenOnDoc = hiddenSection?.relations.contains { $0.key == TorahNativePropertyDefinition.all[0].key } == true
            let isHiddenOnType = chiddushTypeVM.isRelationHidden(sourcesRowInType)
            return isHiddenOnDoc && isHiddenOnType
        }

        // Verify Add Property picker (PropertyCreationViewModel) when מקור/ות is hidden and the other 2 are visible:
        // excludedRelationsIds contains only visible IDs; hiddenRelationsIds contains the hidden מקור/ות ID.
        chiddushTypeVM.onAddRelationTap(section: .fieldsMenu)
        let searchData = try #require(chiddushTypeVM.relationsSearchData)
        #expect(searchData.hiddenRelationsIds.contains(sourcesRowInType.relation.id))
        #expect(!searchData.excludedRelationsIds.contains(sourcesRowInType.relation.id))

        let creationVM = PropertyCreationViewModel(data: searchData)
        await creationVM.search(text: "")
        let emptySearchExisting = creationVM.rows.flatMap(\.searchData).compactMap { item -> PropertyDetails? in
            if case .existing(let details) = item { return details }
            return nil
        }
        #expect(emptySearchExisting.contains { $0.id == sourcesRowInType.relation.id })
        #expect(creationVM.isInstalledButHidden(sourcesRowInType.relation.id))

        for query in ["מקור/ות", "מקורות", "Source"] {
            await creationVM.search(text: query)
            let queryExisting = creationVM.rows.flatMap(\.searchData).compactMap { item -> PropertyDetails? in
                if case .existing(let details) = item { return details }
                return nil
            }
            #expect(queryExisting.contains { $0.id == sourcesRowInType.relation.id })
        }

        // Reveal מקור/ות directly from the open document's ObjectPropertiesViewModel
        let hiddenDocRow = try #require(
            objectPropertiesVM.sections
                .first { $0.id == PropertiesSection.Constants.hiddenPropertiesSectionId }?
                .relations
                .first { $0.key == TorahNativePropertyDefinition.all[0].key }
        )
        objectPropertiesVM.revealHiddenRelation(hiddenDocRow)

        try await eventually {
            let hiddenSection = objectPropertiesVM.sections.first {
                $0.id == PropertiesSection.Constants.hiddenPropertiesSectionId
            }
            let stillHidden = hiddenSection?.relations.contains { $0.key == TorahNativePropertyDefinition.all[0].key } == true
            let visibleRels = torahPropertiesModel.visibleSections(objectPropertiesVM.sections).flatMap(\.relations)
            let backInVisible = expectedNativeKeys.isSubset(of: Set(visibleRels.map(\.key)))
            return !stillHidden && backInVisible && !chiddushTypeVM.isRelationHidden(sourcesRowInType)
        }

        let blockId = try await Container.shared.blockService().addFirstBlock(
            contextId: document.id, info: .empty(id: "", content: .text(.plain("Preserved block", contentType: .text)))
        )
        let source = item(id: "document-source", kind: .ref, key: "Genesis 1:1", label: "בראשית א:א")
        let topic = item(id: "document-topic", kind: .topic, key: "creation", label: "בריאה")
        let word = item(id: "document-word", kind: .word, key: "בראשית", label: "בראשית")
        let repository = AnytypeTorahAssociationRepository()
        for value in [source, topic, word] {
            _ = try await repository.addAssociation(value, target: .object(objectId: document.id), spaceId: spaceId)
        }
        _ = try await repository.addAssociation(
            item(id: "block-only", kind: .ref, key: "Exodus 3:2", label: "שמות ג:ב"),
            target: .block(objectId: document.id, blockId: blockId), spaceId: spaceId
        )
        let expected = [source, topic, word].map(TorahDerivedQueryProjection.identity)
        try await eventually {
            let details = try await show(document.id, spaceId: spaceId)
            return zip(TorahNativePropertyDefinition.all, expected).allSatisfy {
                details.stringArrayValue(for: $0.0.key) == [$0.1]
            }
        }
        let details = try await show(document.id, spaceId: spaceId)
        for (property, value) in zip(nativeProperties, [source, topic, word]) {
            guard case .tag(let rendered) = TorahNativePropertyPresentation.property(
                definition: property, details: details, isFeatured: false, valuesLocked: false
            ) else { Issue.record("Native column renderer missing"); return }
            #expect(rendered.selectedTags.map(\.text) == [value.labelHe])
        }
        let key = TorahNativePropertyDefinition.all[0].key
        let filter = DataviewFilter.with {
            $0.id = UUID().uuidString
            $0.relationKey = key
            $0.format = .tag
            $0.condition = .in
            $0.value = [expected[0]].protobufValue
        }
        let nativeSetResponse = try await ClientCommands.objectCreateSet(.with {
            $0.details = Google_Protobuf_Struct(fields: [BundledPropertyKey.name.rawValue: "Native Torah Set".protobufValue])
            $0.source = Array(manifest.registeredDocumentTypes.values)
            $0.spaceID = spaceId
            $0.withChat = false
        }).invoke()
        let nativeSet = try nativeSetResponse.details.toDetails()
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = nativeSet.id; $0.objectID = nativeSet.id; $0.spaceID = spaceId
        }).invoke()
        let dataview = try #require(response.objectView.blocks.first {
            if case .dataview = $0.content { return true }; return false
        })
        guard case .dataview(let data) = dataview.content else { Issue.record("Missing native Dataview"); return }
        let view = try #require(data.views.first)
        let dataviewService = Container.shared.dataviewService()
        // Prepare real, initially hidden native columns. The subsequent UI test
        // enables them through the original Fields switches, not a test seam.
        for property in nativeProperties {
            try await dataviewService.addRelation(objectId: nativeSet.id, blockId: dataview.id, relationDetails: property)
        }
        let table = try #require(view.asModel).updated(type: .table, options:
            view.relations.filter { !TorahNativePropertyDefinition.all.map(\.key).contains($0.key) }.map(\.asModel)
            + nativeProperties.map { DataviewRelationOption(key: $0.key, isVisible: false) }
        )
        try await dataviewService.updateView(objectId: nativeSet.id, blockId: dataview.id, view: table)
        try await Container.shared.dataviewService().addFilter(
            objectId: nativeSet.id, blockId: dataview.id, filter: filter, viewId: view.id
        )
        let rows = try await search.search(spaceId: spaceId, filters: [filter], keys: ["id", key], limit: 0)
        let expectedSpaceMembers = Set(universal.linkedDocuments.values).union([document.id])
        #expect(Set(rows.map(\.id)) == expectedSpaceMembers)
        let writingTypeFilter = DataviewFilter.with {
            $0.relationKey = "type"; $0.condition = .in
            $0.value = Array(manifest.registeredDocumentTypes.values).protobufValue
        }
        let writingRows = try await search.search(spaceId: spaceId, filters: [filter, writingTypeFilter], keys: ["id"], limit: 0)
        #expect(writingRows.map(\.id) == [document.id])

        // The same native subscription/storage stack used by the real Set.
        let subId = "native-derived-" + UUID().uuidString
        let storage = Container.shared.subscriptionStorageProvider().createSubscriptionStorage(subId: subId)
        let states = NativeMembershipStates()
        try await storage.startOrUpdateSubscription(data: .search(.init(
            identifier: subId, spaceId: spaceId, filters: [filter], limit: 100,
            keys: ["id", key, TorahNativePropertyDefinition.labelsKey], source: [typeId]
        ))) { state in await states.receive(state.items.map(\.id)) }
        try await eventually { await states.latest == [document.id] }
        try await repository.removeAssociation(associationId: source.id, target: .object(objectId: document.id), spaceId: spaceId)
        try await eventually { await states.latest == [] }
        _ = try await repository.addAssociation(source, target: .object(objectId: document.id), spaceId: spaceId)
        try await eventually { await states.latest == [document.id] }
        try await storage.stopSubscription()
        let final = try await ClientCommands.objectShow(.with {
            $0.contextID = document.id; $0.objectID = document.id; $0.spaceID = spaceId
        }).invoke()
        #expect(final.objectView.blocks.contains { $0.id == blockId })
        // Definitions, and no Tag options, share these relation keys.
        let registryRows = try await search.search(spaceId: spaceId, filters: [.with {
            $0.relationKey = "relationKey"; $0.condition = .in
            $0.value = TorahNativePropertyDefinition.all.map(\.key).protobufValue
        }], keys: ["id", "relationKey"], limit: 0)
        #expect(Set(registryRows.map(\.id)) == Set(nativeProperties.map(\.id)))
        // The next process drives the ORIGINAL application UI using this same
        // disposable account and real Objects. Keep only fixture IDs/labels in
        // its local handoff; the mnemonic and canonical payload are never copied.
        for value in [source, topic, word] {
            try await repository.removeAssociation(associationId: value.id, target: .object(objectId: document.id), spaceId: spaceId)
        }
        var fixtureDocuments = [PinkhaSchemaRoles.chiddushKey: document.id]
        var fixtureNames = [document.id: document.name]
        for role in [PinkhaSchemaRoles.articleKey, PinkhaSchemaRoles.researchKey] {
            let roleType = try #require(indexedTypes.first { $0.id == manifest.registeredDocumentTypes[role] })
            let created = try await Container.shared.objectActionsService().createObject(
                name: "Native \(role) document", typeUniqueKey: roleType.uniqueKey,
                shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                spaceId: spaceId, origin: .none, templateId: manifest.defaultTemplateIds[role]
            )
            fixtureDocuments[role] = created.id
            fixtureNames[created.id] = created.name

            // Verify fresh zero-association מאמר and מחקר documents in ObjectPropertiesViewModel
            let roleDoc = Container.shared.openedDocumentProvider().document(objectId: created.id, spaceId: spaceId)
            try await roleDoc.open()
            let roleObjVM = ObjectPropertiesViewModel(document: roleDoc, output: nil)
            let roleTorahModel = PinkhaTorahPropertiesModel(document: roleDoc, session: nil)
            let roleSubTask = Task { await roleObjVM.setupSubscriptions() }
            let roleObsTask = Task { await roleTorahModel.observeDocument() }
            defer {
                roleSubTask.cancel()
                roleObsTask.cancel()
            }
            try await eventually {
                let relKeys = Set(roleTorahModel.visibleSections(roleObjVM.sections).flatMap(\.relations).map(\.key))
                return expectedNativeKeys.isSubset(of: relKeys)
            }
        }
        let chipsDocument = try await Container.shared.objectActionsService().createObject(
            name: "Native twelve-source chips", typeUniqueKey: #require(indexedTypes.first { $0.id == typeId }).uniqueKey,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceId, origin: .none, templateId: manifest.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey]
        )
        for number in 1...12 {
            let reference = "Genesis 2:\(number)"
            _ = try await repository.addAssociation(
                item(id: "many-\(number)", kind: .ref, key: reference, label: reference),
                target: .object(objectId: chipsDocument.id), spaceId: spaceId
            )
        }
        try await eventually {
            try await show(chipsDocument.id, spaceId: spaceId).stringArrayValue(for: key).count == 12
        }
        // The header cases must not reuse writing documents that another UI
        // method mutates. They share only this freshly created disposable Space.
        var sourceHeaderCases = [[String: Any]]()
        for count in [0, 1, 2, 12] {
            let labels = (0..<count).map { "Genesis 2:\($0 + 1)" }
            let values = labels.enumerated().map { index, label in
                item(id: "header-\(count)-\(index)", kind: .ref, key: label, label: label)
            }
            let headerObjectID: String
            if count == 12 {
                headerObjectID = chipsDocument.id
            } else {
                let created = try await Container.shared.objectActionsService().createObject(
                    name: "Native source header count \(count)",
                    typeUniqueKey: #require(indexedTypes.first { $0.id == typeId }).uniqueKey,
                    shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                    spaceId: spaceId, origin: .none,
                    templateId: manifest.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey]
                )
                headerObjectID = created.id
                for value in values {
                    _ = try await repository.addAssociation(
                        value, target: .object(objectId: headerObjectID), spaceId: spaceId
                    )
                }
            }
            let expectedIdentities = Set(values.map(TorahDerivedQueryProjection.identity))
            try await eventually {
                let details = try await show(headerObjectID, spaceId: spaceId)
                let actual = details.stringArrayValue(for: key)
                return details.id == headerObjectID && details.spaceId == spaceId && details.type == typeId &&
                    actual.count == count && Set(actual) == expectedIdentities
            }
            sourceHeaderCases.append(["count": count, "objectId": headerObjectID, "labels": labels])
        }
        let afterMany = try await search.search(spaceId: spaceId, filters: [.with {
            $0.relationKey = "relationKey"; $0.condition = .in
            $0.value = TorahNativePropertyDefinition.all.map(\.key).protobufValue
        }], keys: ["id"], limit: 0)
        #expect(Set(afterMany.map(\.id)) == Set(nativeProperties.map(\.id)))

        // Defect A: Verify internal סדר (order) and canonical storage are both protected by policy while הורה is preserved
        let policy = PinkhaTorahPropertyPolicy.shared
        policy.invalidateCache(spaceId: spaceId)
        _ = await policy.awaitInternalIdentity(spaceId: spaceId)
        #expect(policy.isInternalProperty(propertyId: manifest.orderPropertyId, key: manifest.orderPropertyKey, spaceId: spaceId))
        #expect(policy.isOrderStorage(propertyId: manifest.orderPropertyId, key: manifest.orderPropertyKey, spaceId: spaceId))
        #expect(!policy.isCanonicalStorage(propertyId: manifest.orderPropertyId, key: manifest.orderPropertyKey, spaceId: spaceId))
        #expect(!policy.isInternalProperty(propertyId: manifest.parentPropertyId, key: manifest.parentPropertyKey, spaceId: spaceId))

        // Defect B: Verify catalog discoverability across empty, Hebrew, and English queries on eligible Type
        let chiddushType = try #require(indexedTypes.first { $0.id == typeId })
        let eligibleTarget = PropertiesModuleTarget.type(.recommendedRelations(chiddushType))
        let catalogAll = await PinkhaTorahNativePropertyCatalog.shared.searchNativeProperties(
            text: "", excludedIds: [], target: eligibleTarget, spaceId: spaceId
        )
        #expect(Set(catalogAll.map(\.id)) == Set(nativeProperties.map(\.id)))
        for query in ["מקור/ות", "מקורות", "נושא", "מילה / ערך", "Source(s)", "Sources", "Topic(s)", "Word / entry"] {
            let found = await PinkhaTorahNativePropertyCatalog.shared.searchNativeProperties(
                text: query, excludedIds: [], target: eligibleTarget, spaceId: spaceId
            )
            #expect(!found.isEmpty)
        }
        // Live Type switch (Chiddush -> Page -> Chiddush) on open document updates ObjectPropertiesViewModel live
        // while preserving canonical associations and restoring projections
        if let pageType = indexedTypes.first(where: { $0.uniqueKey == .page }) {
            let openChipsDoc = Container.shared.openedDocumentProvider().document(objectId: chipsDocument.id, spaceId: spaceId)
            try await openChipsDoc.open()
            let chipsObjVM = ObjectPropertiesViewModel(document: openChipsDoc, output: nil)
            let chipsTorahModel = PinkhaTorahPropertiesModel(document: openChipsDoc, session: nil)
            let chipsSubTask = Task { await chipsObjVM.setupSubscriptions() }
            let chipsObsTask = Task { await chipsTorahModel.observeDocument() }
            defer {
                chipsSubTask.cancel()
                chipsObsTask.cancel()
            }

            try await eventually {
                let keys = Set(chipsTorahModel.visibleSections(chipsObjVM.sections).flatMap(\.relations).map(\.key))
                return expectedNativeKeys.isSubset(of: keys)
            }

            let beforeCanonical = try await show(chipsDocument.id, spaceId: spaceId).stringValue(for: manifest.documentAssociationsPropertyKey)
            #expect(!beforeCanonical.isEmpty)
            try await Container.shared.objectActionsService().setObjectType(objectId: chipsDocument.id, typeUniqueKey: pageType.uniqueKey)
            let asPageDetails = try await show(chipsDocument.id, spaceId: spaceId)
            #expect(asPageDetails.stringValue(for: manifest.documentAssociationsPropertyKey) == beforeCanonical)
            let pageConfiguration = try await show(pageType.id, spaceId: spaceId)
            let visibleTypeIds = Set(pageConfiguration.recommendedRelations + pageConfiguration.recommendedFeaturedRelations)
                .subtracting(pageConfiguration.recommendedHiddenRelations)
            let typeKeys = Set(nativeProperties.filter { visibleTypeIds.contains($0.id) }.map(\.key))
            let attachedKeys = Set(asPageDetails.stringArrayValue(for: TorahNativePropertyDefinition.attachedPropertiesKey))
            let expectedPageKeys = typeKeys.union(attachedKeys)
            try await eventually {
                let keys = Set(chipsTorahModel.visibleSections(chipsObjVM.sections).flatMap(\.relations).map(\.key))
                return openChipsDoc.details?.type == pageType.id &&
                    keys.intersection(expectedNativeKeys) == expectedPageKeys && chipsTorahModel.isEligible &&
                    policy.presentsSources(on: openChipsDoc) == expectedPageKeys.contains(TorahNativePropertyDefinition.all[0].key)
            }

            try await Container.shared.objectActionsService().setObjectType(objectId: chipsDocument.id, typeUniqueKey: chiddushType.uniqueKey)
            try await eventually {
                let restored = try await show(chipsDocument.id, spaceId: spaceId)
                let keys = Set(chipsTorahModel.visibleSections(chipsObjVM.sections).flatMap(\.relations).map(\.key))
                return restored.stringValue(for: manifest.documentAssociationsPropertyKey) == beforeCanonical &&
                    restored.stringArrayValue(for: key).count == 12 &&
                    expectedNativeKeys.isSubset(of: keys) &&
                    chipsTorahModel.isEligible
            }
        }
        let reservedTypeSwitchIDs = Set(fixtureDocuments.values)
            .union(universal.documents.values).union(universal.linkedDocuments.values)
            .union(manifest.registeredDocumentTypes.values).union(universal.types.values)
            .union(sourceHeaderCases.compactMap { $0["objectId"] as? String })
            .union([nativeSet.id, universal.setId])
        let typeSwitchFixture = try await prepareTypeSwitchFixture(
            manifest: manifest, nativeProperties: nativeProperties, indexedTypes: indexedTypes,
            writingDocuments: fixtureDocuments, reservedIDs: reservedTypeSwitchIDs
        )
        let directory = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
        if ProcessInfo.processInfo.environment["PINKHA_PREPARE_TYPE_PRESERVATION"] == "1" {
            let subjectID = try #require(typeSwitchFixture["objectId"] as? String)
            try await NativeTypePreservation.prepare(
                subjectID: subjectID, spaceID: spaceId,
                chiddushTypeID: #require(typeSwitchFixture["initialTypeId"] as? String),
                canonicalKey: manifest.documentAssociationsPropertyKey,
                reservedIDs: reservedTypeSwitchIDs.union([subjectID])
            )
        }
        let fixture: [String: Any] = [
            "spaceId": spaceId, "documents": fixtureDocuments, "names": fixtureNames,
            "universalDocuments": universal.documents, "universalTypes": universal.types,
            "universalSetId": universal.setId,
            "types": manifest.registeredDocumentTypes, "manySourcesDocument": chipsDocument.id,
            "sourceHeaderCases": sourceHeaderCases,
            "typeSwitch": typeSwitchFixture,
            "setId": nativeSet.id, "nativeProperties": nativeProperties.map(\.name),
            "sourceQuery": "Genesis 1:1", "sourceLabel": "Genesis 1:1",
            "topicQuery": "Creation", "topicLabel": "Creation", "wordQuery": "בראשית"
        ]
        try JSONSerialization.data(withJSONObject: fixture, options: [.sortedKeys])
            .write(to: directory.appendingPathComponent("pinkha-native-derived-ui-fixture.json"), options: .atomic)
        print("NATIVE_DERIVED_PRODUCT_PIPELINE_PASS space=\(spaceId) document=\(document.id) set=\(nativeSet.id)")
    }

    @MainActor
    private func prepareTypeSwitchFixture(
        manifest: PinkhaSpaceManifest, nativeProperties: [PropertyDetails], indexedTypes: [ObjectType],
        writingDocuments: [String: String], reservedIDs: Set<String>
    ) async throws -> [String: Any] {
        let spaceId = manifest.spaceId
        let chiddushId = try #require(manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey])
        let chiddush = try #require(indexedTypes.first { $0.id == chiddushId })
        // This document is never a writing, header or Set fixture. Only the UI
        // changes its Type; preparation seeds real canonical associations once.
        let document = try await Container.shared.objectActionsService().createObject(
            name: "Native Type-switch preserved properties", typeUniqueKey: chiddush.uniqueKey,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceId, origin: .none, templateId: manifest.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey]
        )
        try #require(!reservedIDs.contains(document.id))
        let kinds = ["ref", "topic", "word"]
        let values = [
            item(id: "type-switch-source", kind: .ref, key: "Genesis 3:1", label: "Genesis 3:1"),
            item(id: "type-switch-topic", kind: .topic, key: "creation", label: "Creation"),
            item(id: "type-switch-word", kind: .word, key: "בראשית", label: "בראשית")
        ]
        try #require(nativeProperties.count == values.count)
        let repository = AnytypeTorahAssociationRepository()
        for value in values {
            _ = try await repository.addAssociation(value, target: .object(objectId: document.id), spaceId: spaceId)
        }
        let expectedIdentities = values.map(TorahDerivedQueryProjection.identity)
        try await eventually {
            let details = try await show(document.id, spaceId: spaceId)
            return details.id == document.id && details.spaceId == spaceId && details.type == chiddushId &&
                !details.stringValue(for: manifest.documentAssociationsPropertyKey).isEmpty &&
                zip(nativeProperties, expectedIdentities).allSatisfy {
                    details.stringArrayValue(for: $0.0.key) == [$0.1]
                }
        }
        let details = try await show(document.id, spaceId: spaceId)
        let persisted = try await repository.listDocumentAssociations(objectId: document.id, spaceId: spaceId)
        try #require(persisted.count == values.count)
        try #require(Set(persisted.map(TorahDerivedQueryProjection.identity)) == Set(expectedIdentities))
        var valueRecords = [[String: Any]]()
        var projectionReadback = [String: [String]]()
        for index in values.indices {
            let property = nativeProperties[index]
            let rendered = try #require(TorahNativePropertyPresentation.property(
                definition: property, details: details, isFeatured: false, valuesLocked: false
            ))
            guard case .tag(let tag) = rendered else {
                Issue.record("Type-switch native value did not use the original property renderer")
                throw NativeAcceptanceError.conditionTimeout("type-switch native renderer")
            }
            try #require(tag.selectedTags.count == 1)
            try #require(tag.selectedTags[0].text == values[index].labelHe)
            projectionReadback[property.key] = details.stringArrayValue(for: property.key)
            valueRecords.append([
                "kind": kinds[index], "canonicalKey": values[index].canonicalKey,
                "propertyKey": property.key, "propertyName": property.name,
                "identity": expectedIdentities[index], "label": tag.selectedTags[0].text
            ])
        }
        // Observe the real Type row/section for each writing Type, without
        // changing a Type through the API or making a hidden row visible in data.
        var typeRecords = [String: [String: Any]]()
        for role in [PinkhaSchemaRoles.chiddushKey, PinkhaSchemaRoles.articleKey, PinkhaSchemaRoles.researchKey] {
            let typeId = try #require(manifest.registeredDocumentTypes[role])
            let probeId: String
            if role == PinkhaSchemaRoles.chiddushKey { probeId = document.id }
            else { probeId = try #require(writingDocuments[role]) }
            let probe = Container.shared.openedDocumentProvider().document(objectId: probeId, spaceId: spaceId)
            try await probe.open()
            let model = ObjectPropertiesViewModel(document: probe, output: nil)
            let subscription = Task { await model.setupSubscriptions() }
            defer { subscription.cancel() }
            try await eventually {
                guard probe.details?.type == typeId, probe.permissions.canChangeType else { return false }
                let rows = model.sections.flatMap(\.relations).filter { $0.key == BundledPropertyKey.type.rawValue }
                guard rows.count == 1, case .object(let value) = rows[0] else { return false }
                return value.selectedObjects.count == 1 && value.selectedObjects[0].id == typeId
            }
            let section = try #require(model.sections.first {
                $0.relations.contains { $0.key == BundledPropertyKey.type.rawValue }
            })
            let row = try #require(section.relations.first { $0.key == BundledPropertyKey.type.rawValue })
            let typeDetails = try await show(typeId, spaceId: spaceId)
            try #require(typeDetails.id == typeId && typeDetails.spaceId == spaceId)
            let type = ObjectType(details: typeDetails)
            guard case .object(let typeValue) = row else {
                throw NativeAcceptanceError.conditionTimeout("type-switch Type row")
            }
            try #require(typeValue.selectedObjects.map(\.title) == [type.displayName])
            typeRecords[role] = [
                "id": type.id, "label": type.displayName, "propertyName": row.name,
                "sectionId": section.id, "sectionTitle": section.title, "sectionExpandable": section.isExpandable
            ]
        }
        let readback: [String: Any] = [
            "method": "ObjectShow", "objectId": details.id, "spaceId": details.spaceId,
            "typeId": details.type, "canonicalNonempty": !details.stringValue(for: manifest.documentAssociationsPropertyKey).isEmpty,
            "projections": projectionReadback
        ]
        return [
            "schemaVersion": 1, "objectId": document.id, "spaceId": spaceId,
            "name": document.name, "initialTypeId": details.type, "types": typeRecords,
            "values": valueRecords, "nativeReadback": readback
        ]
    }

    @MainActor
    private func verifyUniversalProperties(manifest: PinkhaSpaceManifest, nativeProperties: [PropertyDetails]) async throws -> (documents: [String: String], linkedDocuments: [String: String], types: [String: String], setId: String) {
        let spaceId = manifest.spaceId
        _ = try await ClientCommands.workspaceObjectListAdd(.with {
            $0.spaceID = spaceId; $0.objectIds = ["_otnote"]
        }).invoke()
        let custom = try await ClientCommands.objectCreateObjectType(.with {
            $0.spaceID = spaceId
            $0.details = Google_Protobuf_Struct(fields: ["name": "Universal custom Type".protobufValue, "recommendedLayout": DetailsLayout.note.rawValue.protobufValue])
        }).invoke()
        let customType = ObjectType(details: try await show(custom.objectID, spaceId: spaceId))
        let expectedKeys = Set(nativeProperties.map(\.key))
        var documents: [String: String] = [:]
        var linkedDocuments: [String: String] = [:]
        var types: [String: String] = [:]
        let search = Container.shared.searchMiddleService()
        let propertiesService = Container.shared.propertiesService()
        let repository = AnytypeTorahAssociationRepository()
        let targets: [(String, ObjectTypeUniqueKey)] = [
            ("page", .page), ("note", .note), ("custom", customType.uniqueKey)
        ]
        for (role, uniqueKey) in targets {
            let p1 = try await Container.shared.objectActionsService().createObject(
                name: "Universal \(role) P1", typeUniqueKey: uniqueKey,
                shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                spaceId: spaceId, origin: .none, templateId: nil
            )
            let p2 = try await Container.shared.objectActionsService().createObject(
                name: "Universal \(role) blank", typeUniqueKey: uniqueKey,
                shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                spaceId: spaceId, origin: .none, templateId: nil
            )
            let doc = Container.shared.openedDocumentProvider().document(objectId: p1.id, spaceId: spaceId)
            let other = Container.shared.openedDocumentProvider().document(objectId: p2.id, spaceId: spaceId)
            try await doc.open(); try await other.open()
            let typeId = try #require(doc.details?.type)
            let type = ObjectType(details: try await show(typeId, spaceId: spaceId))
            types[role] = typeId
            documents[role] = p2.id
            linkedDocuments[role] = p1.id
            await PinkhaTorahNativePropertyCatalog.shared.ensureSpaceAndTypeReady(spaceId: spaceId, typeId: typeId)
            try await eventually {
                doc.permissions.canEditRelationValues && other.permissions.canEditRelationValues
            }
            #expect(doc.parsedProperties.installed.allSatisfy { !expectedKeys.contains($0.key) })
            #expect(!PinkhaTorahPropertyPolicy.shared.presentsSources(on: doc))
            let coordinator = PropertiesListCoordinatorViewModel(document: doc, output: nil)
            let vm = ObjectPropertiesViewModel(document: doc, output: coordinator)
            let subscription = Task { await vm.setupSubscriptions() }
            defer { subscription.cancel() }
            vm.onAddPropertyTap()
            let picker = PropertyCreationViewModel(data: try #require(vm.relationsSearchData))
            await picker.search(text: "")
            let existing = picker.rows.flatMap(\.searchData).compactMap { item -> PropertyDetails? in
                if case .existing(let property) = item { return property }; return nil
            }
            #expect(Set(nativeProperties.map(\.id)).isSubset(of: Set(existing.map(\.id))))
            let typePicker = PropertyCreationViewModel(data: PropertiesSearchData(
                objectId: typeId, spaceId: spaceId, excludedRelationsIds: [],
                target: .type(.recommendedRelations(type)), onRelationSelect: { _, _ in }
            ))
            for query in ["", "מקורות", "נושא", "מילה", "Sources", "Topics", "Word"] {
                await typePicker.search(text: query)
                #expect(typePicker.rows.flatMap(\.searchData).contains { row in
                    if case .existing(let property) = row { return expectedKeys.contains(property.key) }; return false
                })
            }
            for property in nativeProperties { try await picker.addPropertyToObject(objectId: p1.id, relation: property) }
            try await eventually { expectedKeys.isSubset(of: Set(vm.sections.flatMap(\.relations).map(\.key))) }
            let unchanged = try await show(typeId, spaceId: spaceId)
            #expect(unchanged.recommendedRelations == type.recommendedRelations)
            #expect(unchanged.recommendedFeaturedRelations == type.recommendedFeaturedRelations)
            #expect(unchanged.recommendedHiddenRelations == type.recommendedHiddenRelations)
            #expect(other.parsedProperties.installed.allSatisfy { !expectedKeys.contains($0.key) })
            #expect(PinkhaTorahPropertyPolicy.shared.presentsSources(on: doc))
            for row in vm.sections.flatMap(\.relations) where expectedKeys.contains(row.key) {
                guard case .tag(let tag) = row else { Issue.record("Expected native empty tag row"); continue }
                #expect(tag.selectedTags.isEmpty && tag.isEditable)
                vm.handleTapOnRelation(row)
                #expect(coordinator.relationValueData?.relation.key == row.key)
            }
            let source = item(id: "universal-" + role, kind: .ref, key: "Genesis 1:1", label: "בראשית א:א")
            _ = try await repository.addAssociation(source, target: .object(objectId: p1.id), spaceId: spaceId)
            let filter = DataviewFilter.with {
                $0.relationKey = TorahNativePropertyDefinition.all[0].key; $0.format = .tag; $0.condition = .in
                $0.value = [TorahDerivedQueryProjection.identity(source)].protobufValue
            }
            try await eventually {
                let rows = try await search.search(spaceId: spaceId, filters: [filter, .with {
                    $0.relationKey = "type"; $0.condition = .in; $0.value = [typeId].protobufValue
                }], keys: ["id"], limit: 0)
                return rows.map(\.id) == [p1.id]
            }
            for property in nativeProperties {
                _ = try await ClientCommands.objectTypePropertyAdd(.with {
                    $0.objectTypeID = typeId; $0.key = property.key; $0.section = .recommended
                }).invoke()
            }
            let configured = try await show(typeId, spaceId: spaceId)
            #expect(Set(nativeProperties.map(\.id)).isSubset(of: Set(configured.recommendedRelations)))
            for property in nativeProperties {
                _ = try await ClientCommands.objectTypePropertyRemove(.with { $0.objectTypeID = typeId; $0.key = property.key }).invoke()
            }
            let restoredType = try await show(typeId, spaceId: spaceId)
            #expect(restoredType.recommendedRelations == type.recommendedRelations)
            #expect(restoredType.recommendedFeaturedRelations == type.recommendedFeaturedRelations)
            #expect(restoredType.recommendedHiddenRelations == type.recommendedHiddenRelations)
            PinkhaTorahNativePropertyCatalog.shared.recordUpdatedTypeRelations(
                typeId: typeId, spaceId: spaceId, recommendedIds: type.recommendedRelations,
                featuredIds: type.recommendedFeaturedRelations, hiddenIds: type.recommendedHiddenRelations
            )
            #expect(try await show(p1.id, spaceId: spaceId).stringArrayValue(for: TorahNativePropertyDefinition.attachedPropertiesKey).count == 3)
        }
        let mixed = try await ClientCommands.objectCreateSet(.with {
            $0.spaceID = spaceId; $0.source = Array(types.values)
            $0.details = Google_Protobuf_Struct(fields: ["name": "Universal Page Note custom Set".protobufValue])
        }).invoke()
        let mixedDoc = try mixed.details.toDetails()
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = mixedDoc.id; $0.objectID = mixedDoc.id; $0.spaceID = spaceId
        }).invoke()
        let block = try #require(response.objectView.blocks.first { if case .dataview = $0.content { return true }; return false })
        guard case .dataview(let data) = block.content else { throw NativeAcceptanceError.timeout }
        let view = try #require(data.views.first)
        let dataviewService = Container.shared.dataviewService()
        for property in nativeProperties {
            try await dataviewService.addRelation(objectId: mixedDoc.id, blockId: block.id, relationDetails: property)
        }
        let table = try #require(view.asModel).updated(type: .table, options:
            view.relations.filter { !expectedKeys.contains($0.key) }.map(\.asModel) + nativeProperties.map { DataviewRelationOption(key: $0.key, isVisible: false) }
        )
        try await dataviewService.updateView(objectId: mixedDoc.id, blockId: block.id, view: table)
        let filter = DataviewFilter.with {
            $0.id = UUID().uuidString; $0.relationKey = TorahNativePropertyDefinition.all[0].key
            $0.format = .tag; $0.condition = .in
            $0.value = [TorahDerivedQueryProjection.identity(item(id: "mixed", kind: .ref, key: "Genesis 1:1", label: "בראשית א:א"))].protobufValue
        }
        try await dataviewService.addFilter(objectId: mixedDoc.id, blockId: block.id, filter: filter, viewId: view.id)
        return (documents, linkedDocuments, types, mixedDoc.id)
    }

    private func show(_ id: String, spaceId: String) async throws -> ObjectDetails {
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = id; $0.objectID = id; $0.spaceID = spaceId
        }).invoke()
        return try ObjectDetails(protobufStruct: #require(response.objectView.details.first { $0.id == id }).details)
    }

    @MainActor
    private func eventually(file: StaticString = #fileID, line: UInt = #line, _ predicate: () async throws -> Bool) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(30))
        repeat {
            if try await predicate() { return }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        let location = "\(file):\(line)"
        print("Native acceptance timeout at \(location); real participant count=\(Container.shared.participantsStorage().participants.count)")
        throw NativeAcceptanceError.conditionTimeout(location)
    }

    private func item(id: String, kind: TorahAssociationKind, key: String, label: String) -> TorahAssociationItem {
        TorahAssociationItem(kind: kind, role: .context, providerID: "sefaria", externalID: key,
                             canonicalKey: key, labelHe: label, createdAt: Date())
    }
}

private actor NativeMembershipStates {
    private(set) var latest: [String]?
    func receive(_ ids: [String]) { latest = ids }
}
private enum NativeAcceptanceError: Error {
    case timeout
    case conditionTimeout(String)
}


/// Runs only after the real Type UI roundtrip, in a new host process. Unlike
/// preparation, this verifier never creates/restores/selects an account itself.
@Suite("Native Type roundtrip preservation", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_TYPE_PRESERVATION_POSTFLIGHT"] == "1"))
struct TorahStage2TypePreservationTests {
    @MainActor
    @Test("Existing account retains original canonical bytes, Tag and native links")
    func verifyExistingTypeRoundtrip() async throws {
        try await NativeTypePreservation.verify()
    }
}

private enum NativeTypePreservation {
    static let baselineName = "pinkha-type-preservation-baseline.json"
    static let disabledFlags = [
        "PINKHA_NATIVE_DERIVED_ACCEPTANCE", "PINKHA_PREPARE_TYPE_PRESERVATION",
        "PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION", "PINKHA_SIMULATOR_UI_DISPOSABLE",
        "PINKHA_HANLIN_NATIVE_PREPARATION", "PINKHA_PREPARE_HANLIN_SELECTION_UI",
        "PINKHA_PROPERTIES_PREPARE", "PINKHA_T5_UI_PREPARATION", "PINKHA_T5_APPLE_PAIR"
    ]

    struct Binding: Codable, Equatable {
        let sourceSHA: String
        let runID: String
        let runAttempt: String
        let nonce: String
    }

    struct DirectoryIdentity: Codable, Equatable {
        let path: String
        let device: String
        let inode: String
        let createdAt: Double
    }

    struct Link: Codable, Equatable {
        let blockID: String
        let targetID: String
    }

    struct ObjectState: Codable, Equatable {
        let objectID: String
        let spaceID: String
        let typeID: String
        let tags: [String]
        let links: [String]
        let backlinks: [String]
        let seededLinks: [Link]
    }

    struct TagOption: Codable, Equatable {
        let objectID: String
        let spaceID: String
        let name: String
        let relationKey: String
        let color: String
    }

    struct State: Codable, Equatable {
        let accountID: String
        let spaceID: String
        let subjectID: String
        let chiddushTypeID: String
        let canonicalPropertyKey: String
        let canonicalRaw: String
        let canonicalSHA256: String
        let container: DirectoryIdentity
        let middleware: DirectoryIdentity
        let objects: [ObjectState] // subject, outgoing peer, incoming peer
        let tagOption: TagOption
    }

    struct Baseline: Codable {
        let schemaVersion: Int
        let binding: Binding
        let preparationPID: Int32
        let state: State
    }

    struct Receipt: Codable {
        let schemaVersion: Int
        let status: String
        let scope: String
        let binding: Binding
        let baselineSHA256: String
        let preparationPID: Int32
        let postflightPID: Int32
        let verifierCallsMutationAPI: Bool
        let state: State
    }

    static func sha256(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    static func binding() throws -> Binding {
        let env = ProcessInfo.processInfo.environment
        func value(_ key: String) throws -> String {
            let value = try #require(env["PINKHA_TYPE_PRESERVATION_" + key])
            try #require(!value.isEmpty)
            return value
        }
        let result = Binding(sourceSHA: try value("SOURCE_SHA"), runID: try value("RUN_ID"),
                             runAttempt: try value("RUN_ATTEMPT"), nonce: try value("NONCE"))
        try #require(result.sourceSHA.count == 40 && result.sourceSHA.allSatisfy(\.isHexDigit))
        try #require(result.nonce.count == 32 && result.nonce.allSatisfy(\.isHexDigit))
        try #require(result.runID.allSatisfy(\.isNumber) && result.runAttempt.allSatisfy(\.isNumber))
        return result
    }

    static func supportURL() throws -> URL {
        try #require(FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first)
    }

    static func directory(_ url: URL) throws -> DirectoryIdentity {
        let canonical = url.standardizedFileURL.resolvingSymlinksInPath()
        let attributes = try FileManager.default.attributesOfItem(atPath: canonical.path)
        try #require(attributes[.type] as? FileAttributeType == .typeDirectory)
        let device = try #require(attributes[.systemNumber] as? NSNumber)
        let inode = try #require(attributes[.systemFileNumber] as? NSNumber)
        let created = try #require(attributes[.creationDate] as? Date)
        try #require(created.timeIntervalSince1970.isFinite && inode.uint64Value > 0)
        return .init(path: canonical.path, device: device.stringValue, inode: inode.stringValue,
                     createdAt: created.timeIntervalSince1970)
    }

    static func directories() throws -> (DirectoryIdentity, DirectoryIdentity) {
        let support = try supportURL()
        // Pure URLs: LocalRepoService's getter would create/update storage.
        return (try directory(support.deletingLastPathComponent().deletingLastPathComponent()),
                try directory(support.appendingPathComponent("Anytype/middleware-go")))
    }

    static func validateCanonical(_ raw: String, subjectID: String, spaceID: String) throws {
        let data = Data(raw.utf8)
        let envelope = try #require(JSONSerialization.jsonObject(with: data) as? [String: Any])
        try #require(envelope["version"] as? Int == 2)
        let payload = try TorahAssociationPayloadCodec().decodeCanonicalDocument(
            data, legacyLocation: .init(spaceId: spaceID, target: .object(objectId: subjectID)))
        try #require(payload.records.count == 3 && Set(payload.records.map { $0.item.id }).count == 3)
        try #require(payload.records.allSatisfy {
            $0.spaceId == spaceID && $0.objectId == subjectID && $0.blockId == nil &&
            !$0.item.id.isEmpty && $0.item.providerID == "sefaria" && $0.item.createdAt != nil
        })
        try #require(Set(payload.records.map { $0.item.kind.rawValue + ":" + $0.item.canonicalKey }) ==
                     Set(["ref:Genesis 3:1", "topic:creation", "word:בראשית"]))
    }

    @MainActor
    static func readState(spaceID: String, subjectID: String, chiddushTypeID: String,
                          canonicalKey: String, objectIDs: [String], seedLinks: [String: [Link]],
                          tagID: String) async throws -> State {
        try #require(objectIDs.count == 3 && objectIDs[0] == subjectID && Set(objectIDs).count == 3)
        var objects: [ObjectState] = []
        var canonicalRaw = ""
        for objectID in objectIDs {
            let response = try await ClientCommands.objectShow(.with {
                $0.contextID = objectID; $0.objectID = objectID; $0.spaceID = spaceID
            }).invoke()
            let details = try ObjectDetails(protobufStruct: #require(response.objectView.details.first {
                $0.id == objectID
            }).details)
            try #require(details.id == objectID && details.spaceId == spaceID)
            if objectID == subjectID { canonicalRaw = details.stringValue(for: canonicalKey) }
            let blocks = response.objectView.blocks
            try #require(Set(blocks.map(\.id)).count == blocks.count && blocks.count <= 1000)
            var reached = Set<String>(), pending = [objectID]
            while let current = pending.popLast() {
                if reached.contains(current) { continue }
                let block = try #require(blocks.first { $0.id == current })
                reached.insert(current)
                pending.append(contentsOf: block.childrenIds)
            }
            var observedLinks: [Link] = []
            for expected in seedLinks[objectID, default: []] {
                try #require(reached.contains(expected.blockID))
                let block = try #require(blocks.first { $0.id == expected.blockID })
                guard case .link(let link) = block.content else {
                    throw NativeAcceptanceError.conditionTimeout("preserved native link block")
                }
                observedLinks.append(.init(blockID: block.id, targetID: link.targetBlockID))
            }
            objects.append(.init(objectID: objectID, spaceID: details.spaceId, typeID: details.type,
                                 tags: details.stringArrayValue(for: "tag").sorted(),
                                 links: details.stringArrayValue(for: "links").sorted(),
                                 backlinks: details.stringArrayValue(for: "backlinks").sorted(),
                                 seededLinks: observedLinks))
        }
        let tagResponse = try await ClientCommands.objectShow(.with {
            $0.contextID = tagID; $0.objectID = tagID; $0.spaceID = spaceID
        }).invoke()
        let tag = try ObjectDetails(protobufStruct: #require(tagResponse.objectView.details.first {
            $0.id == tagID
        }).details)
        try #require(tag.id == tagID && tag.spaceId == spaceID && tag.stringValue(for: "relationKey") == "tag")
        let dirs = try directories()
        return .init(accountID: Container.shared.accountManager().account.id, spaceID: spaceID,
                     subjectID: subjectID, chiddushTypeID: chiddushTypeID, canonicalPropertyKey: canonicalKey,
                     canonicalRaw: canonicalRaw, canonicalSHA256: sha256(Data(canonicalRaw.utf8)),
                     container: dirs.0, middleware: dirs.1, objects: objects,
                     tagOption: .init(objectID: tag.id, spaceID: tag.spaceId, name: tag.name,
                                      relationKey: tag.stringValue(for: "relationKey"),
                                      color: tag.stringValue(for: "relationOptionColor")))
    }

    @MainActor
    static func prepare(subjectID: String, spaceID: String, chiddushTypeID: String,
                        canonicalKey: String, reservedIDs: Set<String>) async throws {
        let binding = try binding()
        let accountID = Container.shared.accountManager().account.id
        try #require(!accountID.isEmpty && reservedIDs.contains(subjectID))
        var peers: [String] = []
        for name in ["Type preservation outgoing peer", "Type preservation incoming peer"] {
            let object = try await Container.shared.objectActionsService().createObject(
                name: name, typeUniqueKey: .page, shouldDeleteEmptyObject: false,
                shouldSelectType: false, shouldSelectTemplate: false, spaceId: spaceID, origin: .none, templateId: nil)
            try #require(!reservedIDs.contains(object.id) && !peers.contains(object.id))
            peers.append(object.id)
        }
        let properties = Container.shared.propertiesService()
        let tagID = try #require(try await properties.addPropertyOption(
            spaceId: spaceID, propertyKey: "tag", optionText: "Original native Type-preservation Tag", color: nil))
        try #require(!tagID.isEmpty)
        try await properties.addProperties(objectId: subjectID, propertyKeys: ["tag"])
        try await properties.updateProperty(objectId: subjectID, propertyKey: "tag", value: [tagID].protobufValue)
        let blocks = Container.shared.blockService()
        let outgoing = try await blocks.addFirstBlock(contextId: subjectID, info: .empty(content: .link(.empty(targetBlockID: peers[0]))))
        let incoming = try await blocks.addFirstBlock(contextId: peers[1], info: .empty(content: .link(.empty(targetBlockID: subjectID))))
        let seedLinks = [subjectID: [Link(blockID: outgoing, targetID: peers[0])],
                         peers[1]: [Link(blockID: incoming, targetID: subjectID)]]
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(30))
        var accepted: State?
        repeat {
            let state = try await readState(spaceID: spaceID, subjectID: subjectID, chiddushTypeID: chiddushTypeID,
                                            canonicalKey: canonicalKey, objectIDs: [subjectID] + peers,
                                            seedLinks: seedLinks, tagID: tagID)
            if state.objects[0].typeID == chiddushTypeID && state.objects[0].tags == [tagID] &&
               state.objects[0].links.contains(peers[0]) && state.objects[1].backlinks.contains(subjectID) &&
               state.objects[2].links.contains(subjectID) && state.objects[0].backlinks.contains(peers[1]) &&
               state.objects[0].seededLinks == seedLinks[subjectID, default: []] && state.objects[2].seededLinks == seedLinks[peers[1], default: []] {
                accepted = state; break
            }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        let state = try #require(accepted)
        try #require(state.accountID == accountID)
        try validateCanonical(state.canonicalRaw, subjectID: subjectID, spaceID: spaceID)
        let baseline = Baseline(schemaVersion: 1, binding: binding,
                                preparationPID: ProcessInfo.processInfo.processIdentifier, state: state)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let data = try encoder.encode(baseline)
        try #require(data.count <= 65_536)
        let path = try supportURL().appendingPathComponent(baselineName)
        try #require(!FileManager.default.fileExists(atPath: path.path))
        try data.write(to: path, options: .atomic)
    }

    @MainActor
    static func verify() async throws {
        let env = ProcessInfo.processInfo.environment
        try #require(disabledFlags.allSatisfy { env[$0] == "0" })
        let binding = try binding()
        let input = try #require(env["PINKHA_TYPE_PRESERVATION_BASELINE_BASE64"])
        try #require(input.utf8.count <= 87_384)
        let data = try #require(Data(base64Encoded: input))
        try #require(data.count <= 65_536 && sha256(data) == env["PINKHA_TYPE_PRESERVATION_BASELINE_SHA256"])
        let baseline = try JSONDecoder().decode(Baseline.self, from: data)
        try #require(baseline.schemaVersion == 1 && baseline.binding == binding)
        let expected = baseline.state
        let before = try directories()
        try #require(before.0 == expected.container && before.1 == expected.middleware)
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        while Container.shared.accountManager().account.id.isEmpty && clock.now < deadline {
            try await Task.sleep(for: .milliseconds(100))
        }
        try #require(Container.shared.accountManager().account.id == expected.accountID && !expected.accountID.isEmpty)
        let restored = try directories()
        try #require(restored.0 == expected.container && restored.1 == expected.middleware)
        try validateCanonical(expected.canonicalRaw, subjectID: expected.subjectID, spaceID: expected.spaceID)
        let actual = try await readState(spaceID: expected.spaceID, subjectID: expected.subjectID,
            chiddushTypeID: expected.chiddushTypeID, canonicalKey: expected.canonicalPropertyKey,
            objectIDs: expected.objects.map(\.objectID),
            seedLinks: Dictionary(uniqueKeysWithValues: expected.objects.map { ($0.objectID, $0.seededLinks) }),
            tagID: expected.tagOption.objectID)
        try validateCanonical(actual.canonicalRaw, subjectID: expected.subjectID, spaceID: expected.spaceID)
        try #require(actual == expected)
        let after = try directories()
        try #require(after.0 == expected.container && after.1 == expected.middleware)
        let pid = ProcessInfo.processInfo.processIdentifier
        try #require(pid != baseline.preparationPID)
        let receipt = Receipt(schemaVersion: 1, status: "PASS", scope: "FINAL_UI_TYPE_ROUNDTRIP",
                              binding: binding, baselineSHA256: sha256(data), preparationPID: baseline.preparationPID,
                              postflightPID: pid, verifierCallsMutationAPI: false, state: actual)
        let path = try supportURL().appendingPathComponent("pinkha-type-preservation-result-" + binding.nonce + ".json")
        try #require(!FileManager.default.fileExists(atPath: path.path))
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try encoder.encode(receipt).write(to: path, options: .atomic)
    }
}
