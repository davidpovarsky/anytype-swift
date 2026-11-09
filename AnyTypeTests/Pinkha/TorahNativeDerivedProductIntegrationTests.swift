import Foundation
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
        let coordinatorVM = PropertiesListCoordinatorViewModel(
            data: .object(objectId: document.id),
            spaceId: spaceId,
            onRelationAddTap: { _, _, _ in }
        )
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
            return expectedNativeKeys.isSubset(of: visibleKeys)
        }
        let freshVisibleRelations = torahPropertiesModel.visibleSections(objectPropertiesVM.sections).flatMap(\.relations)
        #expect(torahPropertiesModel.isEligible == true)
        #expect(!freshVisibleRelations.contains { $0.id == manifest.orderPropertyId || $0.key == manifest.orderPropertyKey })
        #expect(!freshVisibleRelations.contains { $0.id == manifest.documentAssociationsPropertyId || $0.key == manifest.documentAssociationsPropertyKey })

        for def in TorahNativePropertyDefinition.all {
            let row = try #require(freshVisibleRelations.first { $0.key == def.key })
            guard case .tag(let tagModel) = row.type else {
                Issue.record("Expected native .tag row in ObjectPropertiesViewModel for \(def.key), got \(row.type)")
                return
            }
            #expect(tagModel.isEditable == true)
            #expect(tagModel.selectedTags.isEmpty)
            // Tapping the empty native row routes through PropertiesListCoordinatorViewModel -> relationValueData
            objectPropertiesVM.handleTapOnRelation(row)
            #expect(coordinatorVM.relationValueData?.relationKey == def.key)
            #expect(coordinatorVM.relationValueData?.document.objectId == document.id)
        }

        // =========================================================================
        // REAL UI PIPELINE PROOF 2: Type Properties Editor (TypePropertiesViewModel)
        // for all 3 Torah Writing Types (חידוש, מאמר, מחקר)
        // =========================================================================
        for role in [PinkhaSchemaRoles.chiddushKey, PinkhaSchemaRoles.articleKey, PinkhaSchemaRoles.researchKey] {
            let roleTypeId = try #require(manifest.registeredDocumentTypes[role])
            let typeDoc = Container.shared.openedDocumentProvider().document(objectId: roleTypeId, spaceId: spaceId)
            try await typeDoc.open()
            let typeVM = TypePropertiesViewModel(document: typeDoc)
            let typeSubTask = Task { await typeVM.setupSubscriptions() }
            defer { typeSubTask.cancel() }

            try await eventually {
                let rowKeys = Set(typeVM.relationRows.compactMap { row -> String? in
                    if case .relation(let r) = row { return r.relation.key }
                    return nil
                })
                return expectedNativeKeys.isSubset(of: rowKeys)
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
        let chiddushTypeDoc = Container.shared.openedDocumentProvider().document(objectId: typeId, spaceId: spaceId)
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
        chiddushTypeVM.onAddRelationTap(section: TypePropertiesSectionRow(id: "rec", title: " Properties", isFeatured: false, isHidden: false, isExpandable: false))
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
        #expect(rows.map(\.id) == [document.id])

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
            try await eventually {
                let keys = Set(chipsTorahModel.visibleSections(chipsObjVM.sections).flatMap(\.relations).map(\.key))
                return keys.isDisjoint(with: expectedNativeKeys) && !chipsTorahModel.isEligible
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
        let directory = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
        let fixture: [String: Any] = [
            "spaceId": spaceId, "documents": fixtureDocuments, "names": fixtureNames,
            "types": manifest.registeredDocumentTypes, "manySourcesDocument": chipsDocument.id,
            "setId": nativeSet.id, "nativeProperties": nativeProperties.map(\.name),
            "sourceQuery": "Genesis 1:1", "sourceLabel": "Genesis 1:1",
            "topicQuery": "Creation", "topicLabel": "Creation", "wordQuery": "בראשית"
        ]
        try JSONSerialization.data(withJSONObject: fixture, options: [.sortedKeys])
            .write(to: directory.appendingPathComponent("pinkha-native-derived-ui-fixture.json"), options: .atomic)
        print("NATIVE_DERIVED_PRODUCT_PIPELINE_PASS space=\(spaceId) document=\(document.id) set=\(nativeSet.id)")
    }

    private func show(_ id: String, spaceId: String) async throws -> ObjectDetails {
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = id; $0.objectID = id; $0.spaceID = spaceId
        }).invoke()
        return try ObjectDetails(protobufStruct: #require(response.objectView.details.first { $0.id == id }).details)
    }

    @MainActor
    private func eventually(_ predicate: () async throws -> Bool) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(30))
        repeat {
            if try await predicate() { return }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw NativeAcceptanceError.timeout
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
private enum NativeAcceptanceError: Error { case timeout }
