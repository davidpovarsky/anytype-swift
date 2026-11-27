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

        let hideObservation = NativeTypeHideObservation()
        @MainActor
        func observeHideViews() {
            let hiddenSection = objectPropertiesVM.sections.first {
                $0.id == PropertiesSection.Constants.hiddenPropertiesSectionId
            }
            hideObservation.hiddenOnDocument = hiddenSection?.relations.contains {
                $0.key == TorahNativePropertyDefinition.all[0].key
            } == true
            hideObservation.hiddenOnType = chiddushTypeVM.isRelationHidden(sourcesRowInType)
        }
        let hideBefore = try await typeHideCanonicalSnapshot(
            typeId: typeId, documentId: document.id, spaceId: spaceId,
            propertyId: sourcesRowInType.relation.id, propertyKey: sourcesRowInType.relation.key
        )
        observeHideViews()
        hideObservation.record(phase: .before, canonical: hideBefore)
        #expect(hideBefore.typeIdentityMatches && hideBefore.documentIdentityMatches)
        #expect(!hideBefore.hiddenOnType)
        #expect(hideBefore.recommendedOnType || hideBefore.featuredOnType)
        #expect(!hideBefore.attachedToDocument)

        // Use the same action as the context menu, exactly once. Its completion
        // and each rendered state are separate observations inside the same 30s wait.
        let hideTask = try #require(chiddushTypeVM.onRelationHide(sourcesRowInType))
        hideObservation.action = .pending
        let hideCompletion = Task { @MainActor in
            do {
                try await hideTask.value
                hideObservation.action = .succeeded
            } catch is CancellationError {
                hideObservation.action = .cancelled
            } catch {
                hideObservation.action = .failed
            }
        }
        defer {
            hideCompletion.cancel()
            hideTask.cancel()
        }

        // Preserve both original view assertions; successful RPC completion is
        // additionally required so a partially applied failed action cannot pass.
        do {
            try await eventually {
                observeHideViews()
                return hideObservation.hiddenOnDocument && hideObservation.hiddenOnType &&
                    hideObservation.action == .succeeded
            }
        } catch {
            let originalError = error
            observeHideViews()
            do {
                let after = try await typeHideCanonicalSnapshot(
                    typeId: typeId, documentId: document.id, spaceId: spaceId,
                    propertyId: sourcesRowInType.relation.id, propertyKey: sourcesRowInType.relation.key
                )
                hideObservation.record(phase: .failed, canonical: after)
            } catch {
                hideObservation.record(phase: .failed, canonical: nil)
            }
            throw originalError
        }
        let hideAfter = try await typeHideCanonicalSnapshot(
            typeId: typeId, documentId: document.id, spaceId: spaceId,
            propertyId: sourcesRowInType.relation.id, propertyKey: sourcesRowInType.relation.key
        )
        hideObservation.record(phase: .completed, canonical: hideAfter)
        #expect(hideAfter.typeIdentityMatches && hideAfter.documentIdentityMatches)
        #expect(hideAfter.hiddenOnType && !hideAfter.recommendedOnType && !hideAfter.featuredOnType)
        #expect(!hideAfter.attachedToDocument)

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

    private func typeHideCanonicalSnapshot(
        typeId: String, documentId: String, spaceId: String, propertyId: String, propertyKey: String
    ) async throws -> NativeTypeHideCanonicalSnapshot {
        let type = try await show(typeId, spaceId: spaceId)
        let object = try await show(documentId, spaceId: spaceId)
        let encoder = JSONEncoder()
        let typeLists = [type.recommendedRelations, type.recommendedFeaturedRelations, type.recommendedHiddenRelations]
        return NativeTypeHideCanonicalSnapshot(
            typeIdentityMatches: type.id == typeId && type.spaceId == spaceId,
            documentIdentityMatches: object.id == documentId && object.spaceId == spaceId && object.type == typeId,
            recommendedOnType: type.recommendedRelations.contains(propertyId),
            featuredOnType: type.recommendedFeaturedRelations.contains(propertyId),
            hiddenOnType: type.recommendedHiddenRelations.contains(propertyId),
            attachedToDocument: object.stringArrayValue(for: TorahNativePropertyDefinition.attachedPropertiesKey).contains(propertyKey),
            typeListCounts: typeLists.map(\.count),
            typeListsSHA256: SHA256.hash(data: try encoder.encode(typeLists)).map { String(format: "%02x", $0) }.joined()
        )
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

private struct NativeTypeHideCanonicalSnapshot: Codable {
    let typeIdentityMatches: Bool
    let documentIdentityMatches: Bool
    let recommendedOnType: Bool
    let featuredOnType: Bool
    let hiddenOnType: Bool
    let attachedToDocument: Bool
    let typeListCounts: [Int]
    let typeListsSHA256: String
}

@MainActor
private final class NativeTypeHideObservation {
    enum Action: String, Codable { case notStarted, pending, succeeded, failed, cancelled }
    enum Phase: String, Codable { case before, completed, failed }
    var action: Action = .notStarted
    var hiddenOnType = false
    var hiddenOnDocument = false

    func record(phase: Phase, canonical: NativeTypeHideCanonicalSnapshot?) {
        struct Observation: Encodable {
            let phase: Phase
            let action: Action
            let hiddenOnType: Bool
            let hiddenOnDocument: Bool
            let canonicalReadSucceeded: Bool
            let canonical: NativeTypeHideCanonicalSnapshot?
        }
        let value = Observation(
            phase: phase, action: action, hiddenOnType: hiddenOnType,
            hiddenOnDocument: hiddenOnDocument, canonicalReadSucceeded: canonical != nil, canonical: canonical
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        if let data = try? encoder.encode(value), let text = String(data: data, encoding: .utf8) {
            print("Native Type hide observation: \(text)")
        }
    }
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

    struct Directories: Codable, Equatable {
        let container: DirectoryIdentity
        let middleware: DirectoryIdentity
    }

    struct Inventory: Decodable, Equatable {
        let sha256: String
        let files: Int
        let bytes: Int
        let directories: Int
    }

    struct NativeOpenInventory: Codable, Equatable {
        let algorithm: String
        let sha256: String
        let files: Int
        let bytes: Int
        let directories: Int
    }

    struct PreopenProof: Codable {
        let schemaVersion: Int
        let status: String
        let binding: Binding
        let installationSHA256: String
        let baselineSHA256: String
        let fixtureSHA256: String
        let accountID: String
        let spaceID: String
        let subjectID: String
        let processID: Int32
        let directories: Directories
        let directoryBirthNanoseconds: [String: String]
        let nativeOpenInventory: NativeOpenInventory
    }

    struct StoppedProcessCheck: Decodable {
        let status: String
        let commandExitCode: Int
        let ownedAppMatches: Int
        let unresolvedAppMatches: Int
    }

    struct Installation: Decodable {
        let schemaVersion: Int
        let status: String
        let binding: Binding
        let baselineSHA256: String
        let fixtureSHA256: String
        let simulatorUDID: String
        let accountID: String
        let spaceID: String
        let subjectID: String
        let preparationPID: Int32
        let codeCarriersSHA256: String
        let installedBeforeCodeSHA256: String
        let installedAfterCodeSHA256: String
        let originalDirectories: Directories
        let currentDirectories: Directories
        let beforeInventory: Inventory
        let afterInventory: Inventory
        let nativeOpenInventory: NativeOpenInventory
        let directoryBirthNanoseconds: [String: String]
        let stoppedProcessChecks: [String: StoppedProcessCheck]
        let containerRelocated: Bool
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
        let installationSHA256: String
        let directoriesBefore: Directories
        let preopenProof: PreopenProof
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

    static func matchesController(_ actual: DirectoryIdentity, _ controller: DirectoryIdentity) throws {
        // Python/macOS and Foundation each retain their own creation-time
        // representation. No cross-language rounding tolerance replaces identity.
        try #require(actual.path == controller.path && actual.device == controller.device &&
                     actual.inode == controller.inode && controller.createdAt.isFinite && controller.createdAt > 0)
    }

    static func stateAtInstalledDirectories(_ original: State, _ current: Directories) -> State {
        .init(accountID: original.accountID, spaceID: original.spaceID, subjectID: original.subjectID,
              chiddushTypeID: original.chiddushTypeID, canonicalPropertyKey: original.canonicalPropertyKey,
              canonicalRaw: original.canonicalRaw, canonicalSHA256: original.canonicalSHA256,
              container: current.container, middleware: current.middleware, objects: original.objects,
              tagOption: original.tagOption)
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
        try #require(env["PINKHA_TYPE_PRESERVATION_MODE"] == "SIMULATOR_NORMAL_INSTALL_PREOPEN_PROOF")
        let binding = try binding()
        let input = try #require(env["PINKHA_TYPE_PRESERVATION_BASELINE_BASE64"])
        try #require(input.utf8.count <= 87_384)
        let data = try #require(Data(base64Encoded: input))
        try #require(data.count <= 65_536 && sha256(data) == env["PINKHA_TYPE_PRESERVATION_BASELINE_SHA256"])
        let baseline = try JSONDecoder().decode(Baseline.self, from: data)
        try #require(baseline.schemaVersion == 1 && baseline.binding == binding)
        let expected = baseline.state
        let installationInput = try #require(env["PINKHA_TYPE_PRESERVATION_INSTALLATION_BASE64"])
        try #require(installationInput.utf8.count <= 87_384)
        let installationData = try #require(Data(base64Encoded: installationInput))
        try #require(installationData.count <= 65_536 &&
                     sha256(installationData) == env["PINKHA_TYPE_PRESERVATION_INSTALLATION_SHA256"])
        let installation = try JSONDecoder().decode(Installation.self, from: installationData)
        try #require(installation.schemaVersion == 2 &&
                     installation.status == "PASS_STOPPED_NATIVE_STORE_UNCHANGED" &&
                     installation.binding == binding && installation.baselineSHA256 == sha256(data) &&
                     installation.preparationPID == baseline.preparationPID &&
                     installation.accountID == expected.accountID && installation.spaceID == expected.spaceID &&
                     installation.subjectID == expected.subjectID)
        try #require(installation.codeCarriersSHA256.count == 64 &&
                     installation.codeCarriersSHA256.allSatisfy(\.isHexDigit) &&
                     installation.installedBeforeCodeSHA256 == installation.codeCarriersSHA256 &&
                     installation.installedAfterCodeSHA256 == installation.codeCarriersSHA256)
        try #require(installation.beforeInventory == installation.afterInventory &&
                     installation.beforeInventory.files > 0 && installation.beforeInventory.bytes > 0 &&
                     installation.beforeInventory.directories >= 0 &&
                     installation.beforeInventory.sha256.count == 64 &&
                     installation.beforeInventory.sha256.allSatisfy(\.isHexDigit))
        try #require(Set(installation.stoppedProcessChecks.keys) ==
                     Set(["BEFORE_INVENTORY", "BEFORE_INSTALL", "AFTER_INSTALL", "AFTER_INVENTORY"]))
        try #require(installation.stoppedProcessChecks.values.allSatisfy {
            $0.status == "PASS_APP_NOT_RUNNING" && $0.commandExitCode == 0 &&
            $0.ownedAppMatches == 0 && $0.unresolvedAppMatches == 0
        })
        try matchesController(expected.container, installation.originalDirectories.container)
        try matchesController(expected.middleware, installation.originalDirectories.middleware)
        try #require(installation.containerRelocated ==
                     (installation.originalDirectories.container.path != installation.currentDirectories.container.path))
        // Startup captures every original stopped-store byte before AccountSelect.
        // A post-open inventory would include legitimate engine changes and could
        // not prove whether XCTest preserved the original store on installation.
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        while Container.shared.accountManager().account.id.isEmpty && clock.now < deadline {
            try await Task.sleep(for: .milliseconds(100))
        }
        try #require(Container.shared.accountManager().account.id == expected.accountID && !expected.accountID.isEmpty)
        let support = try supportURL()
        let preopenURL = support.appendingPathComponent("pinkha-type-preservation-preopen-" + binding.nonce + ".json")
        try #require(preopenURL.standardizedFileURL.resolvingSymlinksInPath().path == preopenURL.path)
        let preopenData = try Data(contentsOf: preopenURL)
        try #require(!preopenData.isEmpty && preopenData.count <= 65_536)
        let preopen = try JSONDecoder().decode(PreopenProof.self, from: preopenData)
        try #require(preopen.schemaVersion == 1 && preopen.status == "PASS_BEFORE_ACCOUNT_SELECT" &&
                     preopen.binding == binding && preopen.installationSHA256 == sha256(installationData) &&
                     preopen.baselineSHA256 == sha256(data) && preopen.fixtureSHA256 == installation.fixtureSHA256 &&
                     preopen.accountID == expected.accountID && preopen.spaceID == expected.spaceID &&
                     preopen.subjectID == expected.subjectID &&
                     preopen.processID == ProcessInfo.processInfo.processIdentifier &&
                     preopen.processID != baseline.preparationPID &&
                     preopen.directoryBirthNanoseconds == installation.directoryBirthNanoseconds &&
                     preopen.nativeOpenInventory == installation.nativeOpenInventory &&
                     preopen.nativeOpenInventory.algorithm == "sha256-length-framed-utf8-v1")
        let before = try directories()
        try #require(before.0 == preopen.directories.container && before.1 == preopen.directories.middleware)
        try #require(before.0.device == installation.currentDirectories.container.device &&
                     before.0.inode == installation.currentDirectories.container.inode &&
                     before.1.device == installation.currentDirectories.middleware.device &&
                     before.1.inode == installation.currentDirectories.middleware.inode)
        try #require(UUID(uuidString: installation.simulatorUDID) != nil &&
                     URL(fileURLWithPath: before.0.path).pathComponents.map { $0.lowercased() }
                        .contains(installation.simulatorUDID.lowercased()))
        let initialDirectories = Directories(container: before.0, middleware: before.1)
        let expectedAtCurrentRoot = stateAtInstalledDirectories(expected, initialDirectories)
        // The original identity files must survive the controlled install too.
        let preservedBaseline = try Data(contentsOf: support.appendingPathComponent(baselineName))
        let preservedFixture = try Data(contentsOf: support.appendingPathComponent("pinkha-native-derived-ui-fixture.json"))
        try #require(preservedBaseline.count <= 65_536 && sha256(preservedBaseline) == sha256(data) &&
                     preservedFixture.count <= 65_536 && sha256(preservedFixture) == installation.fixtureSHA256)
        let restored = try directories()
        try #require(restored.0 == before.0 && restored.1 == before.1)
        try validateCanonical(expected.canonicalRaw, subjectID: expected.subjectID, spaceID: expected.spaceID)
        let actual = try await readState(spaceID: expected.spaceID, subjectID: expected.subjectID,
            chiddushTypeID: expected.chiddushTypeID, canonicalKey: expected.canonicalPropertyKey,
            objectIDs: expected.objects.map(\.objectID),
            seedLinks: Dictionary(uniqueKeysWithValues: expected.objects.map { ($0.objectID, $0.seededLinks) }),
            tagID: expected.tagOption.objectID)
        try validateCanonical(actual.canonicalRaw, subjectID: expected.subjectID, spaceID: expected.spaceID)
        try #require(actual == expectedAtCurrentRoot)
        let after = try directories()
        try #require(after.0 == before.0 && after.1 == before.1)
        let pid = ProcessInfo.processInfo.processIdentifier
        try #require(pid != baseline.preparationPID)
        let receipt = Receipt(schemaVersion: 3, status: "PASS", scope: "FINAL_UI_TYPE_ROUNDTRIP",
                              binding: binding, baselineSHA256: sha256(data),
                              installationSHA256: sha256(installationData), directoriesBefore: initialDirectories,
                              preopenProof: preopen,
                              preparationPID: baseline.preparationPID,
                              postflightPID: pid, verifierCallsMutationAPI: false, state: actual)
        let path = try supportURL().appendingPathComponent("pinkha-type-preservation-result-" + binding.nonce + ".json")
        try #require(!FileManager.default.fileExists(atPath: path.path))
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try encoder.encode(receipt).write(to: path, options: .atomic)
    }
}

import PinkhaTorahPresentation

/// G02 observes the three original writing Objects after real Properties UI.
/// It never creates, restores or selects an account, provisions schema, or calls
/// an association/property mutation. Files written here are test evidence only.
@Suite("G02 original writing Properties readback", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_G02_NATIVE_READBACK"] == "1"))
struct TorahWritingPropertiesReadbackTests {
    @MainActor
    @Test("Read the actual baseline or verify exactly one document Word unlink per writing Object")
    func observeOriginalWritingProperties() async throws {
        try await G02WritingPropertiesReadback.observe()
    }
}

private enum G02WritingPropertiesReadback {
    static let roles = ["chiddush", "article", "research"]
    static let controllerKeys = [
        "SOURCE_SHA", "RUN_ID", "RUN_ATTEMPT", "TOKEN", "SIMULATOR_UDID", "LANE",
        "ADMISSION_SHA256", "PREPARATION_SHA256", "INVOCATION_SHA256",
        "OWNED_SIMULATOR_SHA256", "FIXTURE_SHA256"
    ]
    // These clocks can change during ordinary opening and the confirmed unlink.
    // Their original/current values remain in the full snapshots and receipt.
    static let clockKeys: Set<String> = ["lastModifiedDate", "lastOpenedDate", "lastUsedDate"]
    // Exact8ac core/pinkha/torahindex/index.go derives this from canonical bytes.
    static let canonicalHashKey = "_pinkhaTorahCanonicalHash"
    static let maximumReceiptBytes = 4 * 1_024 * 1_024

    struct Fixture: Decodable {
        struct ReservedTypeSubject: Decodable { let objectId: String }
        let spaceId: String
        let documents: [String: String]
        let names: [String: String]
        let types: [String: String]
        let sourceLabel: String
        let topicLabel: String
        let typeSwitch: ReservedTypeSubject
    }

    struct Seed: Decodable {
        struct Document: Decodable {
            let objectID: String
            let typeID: String
            let name: String
            let sourceLabel: String
            let topicLabel: String
            let wordLabel: String
            let tagPropertyName: String
            let tagName: String
        }
        let schema: String
        let phase: String
        let spaceID: String
        let controller: [String: String]
        let documents: [String: Document]
    }

    struct Unlink: Decodable {
        struct Document: Decodable {
            let objectID: String
            let typeID: String
            let name: String
            let wordRecordIDFromNativeBaseline: String
            let wordIdentityFromNativeBaseline: String
            let tagIDFromNativeBaseline: String
            let previousPID: Int32
            let appPID: Int32
        }
        let schema: String
        let phase: String
        let spaceID: String
        let controller: [String: String]
        let nativeBaselineSHA256: String
        let seedUIReceiptSHA256: String
        let nativePersistencePostflightRequired: Bool
        let documents: [String: Document]
    }

    struct NativeObject: Codable {
        let objectID: String
        let spaceID: String
        let typeID: String
        let name: String
        let fields: [String: TorahJSONValue]
        let protobufDetailsJSON: String
        let protobufDetailsSHA256: String
    }

    struct Document: Codable {
        let native: NativeObject
        let canonicalRaw: String
        let canonicalSHA256: String
        let projections: [String: [String]]
        let tag: NativeObject
    }

    struct State: Codable {
        let accountID: String
        let spaceID: String
        let canonicalPropertyKey: String
        let canonicalPropertyID: String
        let tagProperty: NativeObject
        let documents: [String: Document]
    }

    struct Receipt: Codable {
        let schema: String
        let status: String
        let phase: String
        let controller: [String: String]
        let fixtureSHA256: String
        let seedUIReceiptSHA256: String
        let nativeBaselineSHA256: String?
        let unlinkUIReceiptSHA256: String?
        let processID: Int32
        let directories: NativeTypePreservation.Directories
        let verifierCallsMutationAPI: Bool
        let scope: String
        let permittedClockKeys: [String]
        let state: State
    }

    struct UIBaseline: Encodable {
        struct Document: Encodable {
            let objectID: String
            let typeID: String
            let name: String
            let sourceLabel: String
            let topicLabel: String
            let wordRecordID: String
            let wordIdentity: String
            let wordLabel: String
            let tagPropertyName: String
            let tagID: String
            let tagName: String
        }
        let schema: String
        let nativeBaselineSHA256: String
        let seedUIReceiptSHA256: String
        let controller: [String: String]
        let spaceID: String
        let documents: [String: Document]
    }

    static func sha256(_ data: Data) -> String { NativeTypePreservation.sha256(data) }

    static func input(_ name: String, maximum: Int = 262_144) throws -> Data {
        let raw = try #require(ProcessInfo.processInfo.environment[name])
        let data = Data(raw.utf8)
        try #require(!data.isEmpty && data.count <= maximum)
        return data
    }

    static func hashedInput(_ name: String) throws -> Data {
        let data = try input(name)
        try #require(sha256(data) == ProcessInfo.processInfo.environment[name.replacingOccurrences(of: "_JSON", with: "_SHA256")])
        return data
    }

    static func controller() throws -> [String: String] {
        let env = ProcessInfo.processInfo.environment
        var result = [String: String]()
        for key in controllerKeys {
            let value = try #require(env["PINKHA_UI27_STARTUP_" + key])
            try #require(!value.isEmpty)
            result[key] = value
        }
        let source = try #require(result["SOURCE_SHA"])
        let token = try #require(result["TOKEN"])
        let udid = try #require(result["SIMULATOR_UDID"])
        try #require(source.count == 40 && source.allSatisfy(\.isHexDigit))
        try #require(token.count == 32 && token.allSatisfy(\.isHexDigit))
        try #require(UUID(uuidString: udid) != nil && env["SIMULATOR_UDID"] == udid)
        try #require(result["LANE"] == "properties")
        for key in ["RUN_ID", "RUN_ATTEMPT"] {
            let value = try #require(result[key])
            try #require(value.allSatisfy(\.isNumber))
        }
        for key in controllerKeys where key.hasSuffix("SHA256") {
            let value = try #require(result[key])
            try #require(value.count == 64 && value.allSatisfy(\.isHexDigit))
        }
        return result
    }

    static func write<T: Encodable>(_ value: T, to url: URL) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let data = try encoder.encode(value)
        try #require(!data.isEmpty && data.count <= maximumReceiptBytes)
        try #require(!FileManager.default.fileExists(atPath: url.path))
        try data.write(to: url, options: .atomic)
        return data
    }

    static func payload(_ document: Document) throws -> TorahCanonicalAssociationsPayload {
        let data = Data(document.canonicalRaw.utf8)
        try #require(!data.isEmpty && data.count <= 1_048_576 && sha256(data) == document.canonicalSHA256)
        let envelope = try JSONDecoder().decode([String: TorahJSONValue].self, from: data)
        try #require(envelope["version"] == .number(2))
        let location = TorahAssociationLocation(spaceId: document.native.spaceID,
            target: .object(objectId: document.native.objectID))
        let value = try TorahAssociationPayloadCodec().decodeCanonicalDocument(data, legacyLocation: location)
        try #require(value.records.count <= 1_000 && Set(value.records.map { $0.item.id }).count == value.records.count)
        try #require(value.records.allSatisfy {
            $0.spaceId == document.native.spaceID && $0.objectId == document.native.objectID &&
            !$0.item.id.isEmpty && ($0.blockId == nil || $0.blockId?.isEmpty == false)
        })
        return value
    }

    static func documentItems(_ document: Document) throws -> [TorahAssociationItem] {
        try payload(document).records.filter { $0.blockId == nil }.map(\.item)
    }

    static func item(_ kind: TorahAssociationKind, in document: Document) throws -> TorahAssociationItem {
        let values = try documentItems(document).filter { $0.kind == kind }
        try #require(values.count == 1)
        let value = try #require(values.first)
        try #require(value.providerID == "sefaria" && value.createdAt != nil)
        return value
    }

    static func labels(_ document: Document) throws -> [String: TorahJSONValue] {
        let raw = try #require(document.native.fields[TorahNativePropertyDefinition.labelsKey])
        guard case .string(let json) = raw else {
            throw NativeAcceptanceError.conditionTimeout("G02 native derived label JSON string")
        }
        return try JSONDecoder().decode([String: TorahJSONValue].self, from: Data(json.utf8))
    }

    static func stableFields(_ object: NativeObject, excluding keys: Set<String> = []) throws -> [String: TorahJSONValue] {
        let data = Data(object.protobufDetailsJSON.utf8)
        try #require(sha256(data) == object.protobufDetailsSHA256)
        let decoded = try JSONDecoder().decode([String: TorahJSONValue].self, from: data)
        try #require(decoded == object.fields)
        for key in clockKeys {
            switch object.fields[key] {
            case nil, .null?: break
            case .number(let value)?: try #require(value.isFinite && value >= 0)
            default: throw NativeAcceptanceError.conditionTimeout("G02 malformed native clock: " + key)
            }
        }
        return object.fields.filter { !clockKeys.contains($0.key) && !keys.contains($0.key) }
    }

    @MainActor
    static func readObject(_ objectID: String, spaceID: String) async throws -> (NativeObject, ObjectDetails) {
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = objectID; $0.objectID = objectID; $0.spaceID = spaceID
        }).invoke()
        let rows = response.objectView.details.filter { $0.id == objectID }
        try #require(rows.count == 1)
        let row = try #require(rows.first)
        let details = try ObjectDetails(protobufStruct: row.details)
        try #require(details.id == objectID && details.spaceId == spaceID)
        let raw = try row.details.jsonUTF8Data()
        try #require(!raw.isEmpty && raw.count <= 1_048_576)
        let fields = try JSONDecoder().decode([String: TorahJSONValue].self, from: raw)
        let text = try #require(String(data: raw, encoding: .utf8))
        return (.init(objectID: details.id, spaceID: details.spaceId, typeID: details.type,
                      name: details.name, fields: fields, protobufDetailsJSON: text,
                      protobufDetailsSHA256: sha256(raw)), details)
    }

    @MainActor
    static func readState(fixture: Fixture) async throws -> State {
        let accountID = Container.shared.accountManager().account.id
        try #require(!accountID.isEmpty)
        let loadedManifest = try await PinkhaSpaceManifestStore().loadManifest(spaceId: fixture.spaceId)
        let manifest = try #require(loadedManifest)
        try #require(manifest.spaceId == fixture.spaceId && manifest.isFullyProvisioned)
        try #require(roles.allSatisfy { manifest.registeredDocumentTypes[$0] == fixture.types[$0] })
        let descriptorValue = try await AnytypeTorahNativePropertyProvisioningStore().property(key: "tag", spaceId: fixture.spaceId)
        let descriptor = try #require(descriptorValue)
        let (tagProperty, propertyDetails) = try await readObject(descriptor.id, spaceID: fixture.spaceId)
        try #require(propertyDetails.stringValue(for: "relationKey") == "tag")
        var documents = [String: Document]()
        for role in roles {
            let objectID = try #require(fixture.documents[role])
            let (native, details) = try await readObject(objectID, spaceID: fixture.spaceId)
            let tags = details.stringArrayValue(for: "tag")
            try #require(tags.count == 1)
            let tagID = try #require(tags.first)
            let (tag, tagDetails) = try await readObject(tagID, spaceID: fixture.spaceId)
            try #require(tagDetails.stringValue(for: "relationKey") == "tag")
            let canonicalRaw = details.stringValue(for: manifest.documentAssociationsPropertyKey)
            let projections = Dictionary(uniqueKeysWithValues: TorahNativePropertyDefinition.all.map {
                ($0.key, details.stringArrayValue(for: $0.key))
            })
            documents[role] = .init(native: native, canonicalRaw: canonicalRaw,
                canonicalSHA256: sha256(Data(canonicalRaw.utf8)), projections: projections, tag: tag)
        }
        try #require(Container.shared.accountManager().account.id == accountID)
        return .init(accountID: accountID, spaceID: fixture.spaceId,
            canonicalPropertyKey: manifest.documentAssociationsPropertyKey,
            canonicalPropertyID: manifest.documentAssociationsPropertyId,
            tagProperty: tagProperty, documents: documents)
    }

    static func validate(_ state: State, fixture: Fixture, seed: Seed, phase: String) throws {
        try #require(Set(state.documents.keys) == Set(roles) && state.spaceID == fixture.spaceId)
        try #require(!state.canonicalPropertyKey.isEmpty && !state.canonicalPropertyID.isEmpty)
        try #require(Set(state.documents.values.map { $0.tag.objectID }).count == roles.count)
        for role in roles {
            let document = try #require(state.documents[role])
            let observed = try #require(seed.documents[role])
            let native = document.native
            try #require(native.objectID == observed.objectID && native.spaceID == fixture.spaceId &&
                         native.typeID == observed.typeID && native.name == observed.name)
            try #require(document.tag.name == observed.tagName && state.tagProperty.name == observed.tagPropertyName)
            try #require(native.fields["tag"] == .array([.string(document.tag.objectID)]))
            try #require(native.fields[state.canonicalPropertyKey] == .string(document.canonicalRaw))
            _ = try stableFields(native)
            _ = try stableFields(document.tag)
            let source = try item(.ref, in: document)
            let topic = try item(.topic, in: document)
            try #require(source.canonicalKey == "Genesis 1:1" && topic.canonicalKey == "creation")
            try #require(TorahAssociationDisplayFormatter.label(for: source, locale: Locale(identifier: "en")) == observed.sourceLabel)
            try #require(TorahAssociationDisplayFormatter.label(for: topic, locale: Locale(identifier: "en")) == observed.topicLabel)
            let values = try documentItems(document)
            try #require(values.count == (phase == "baseline" ? 3 : 2))
            try #require(values.allSatisfy { $0.role == .context })
            try #require(native.fields[canonicalHashKey] == .string(document.canonicalSHA256))
            try #require(native.fields[TorahNativePropertyDefinition.readinessKey] == .bool(true) &&
                         native.fields[TorahNativePropertyDefinition.statusKey] == .string("READY") &&
                         native.fields[TorahNativePropertyDefinition.engineVersionKey] == .number(1))
            if phase == "baseline" {
                let word = try item(.word, in: document)
                try #require(TorahAssociationDisplayFormatter.label(for: word, locale: Locale(identifier: "en")) == observed.wordLabel)
            } else {
                try #require(!values.contains { $0.kind == .word })
            }
            for definition in TorahNativePropertyDefinition.all {
                let expected = values.filter { $0.kind == definition.kind }.map(TorahDerivedQueryProjection.identity).sorted()
                try #require(document.projections[definition.key] == expected)
                let raw = native.fields[definition.key]
                if expected.isEmpty {
                    // Exact8ac clears absent projection keys; the original
                    // smartblock adapter reinserts null for attached Properties.
                    try #require(raw == nil || raw == .null || raw == .array([]))
                } else {
                    try #require(raw == .array(expected.map { .string($0) }))
                }
            }
            _ = try labels(document)
        }
        _ = try stableFields(state.tagProperty)
    }

    static func uiBaseline(_ receipt: Receipt, hash: String) throws -> UIBaseline {
        var documents = [String: UIBaseline.Document]()
        for role in roles {
            let value = try #require(receipt.state.documents[role])
            let source = try item(.ref, in: value)
            let topic = try item(.topic, in: value)
            let word = try item(.word, in: value)
            let locale = Locale(identifier: "en")
            documents[role] = .init(objectID: value.native.objectID, typeID: value.native.typeID, name: value.native.name,
                sourceLabel: TorahAssociationDisplayFormatter.label(for: source, locale: locale),
                topicLabel: TorahAssociationDisplayFormatter.label(for: topic, locale: locale),
                wordRecordID: word.id, wordIdentity: TorahDerivedQueryProjection.identity(word),
                wordLabel: TorahAssociationDisplayFormatter.label(for: word, locale: locale),
                tagPropertyName: receipt.state.tagProperty.name, tagID: value.tag.objectID, tagName: value.tag.name)
        }
        return .init(schema: "pinkha-g02-word-native-ui-baseline-v1", nativeBaselineSHA256: hash,
            seedUIReceiptSHA256: receipt.seedUIReceiptSHA256, controller: receipt.controller,
            spaceID: receipt.state.spaceID, documents: documents)
    }

    static func compare(_ baseline: State, _ actual: State, unlink: Unlink) throws {
        try #require(actual.accountID == baseline.accountID && actual.spaceID == baseline.spaceID &&
                     actual.canonicalPropertyKey == baseline.canonicalPropertyKey &&
                     actual.canonicalPropertyID == baseline.canonicalPropertyID)
        let expectedProperty = try stableFields(baseline.tagProperty)
        let actualProperty = try stableFields(actual.tagProperty)
        try #require(expectedProperty == actualProperty)
        let wordDefinition = try #require(TorahNativePropertyDefinition.all.first { $0.kind == .word })
        let changedKeys: Set<String> = [baseline.canonicalPropertyKey, wordDefinition.key,
                                       TorahNativePropertyDefinition.labelsKey, canonicalHashKey]
        for role in roles {
            let before = try #require(baseline.documents[role])
            let after = try #require(actual.documents[role])
            let ui = try #require(unlink.documents[role])
            let word = try item(.word, in: before)
            let identity = TorahDerivedQueryProjection.identity(word)
            try #require(ui.objectID == before.native.objectID && ui.typeID == before.native.typeID &&
                         ui.name == before.native.name && ui.wordRecordIDFromNativeBaseline == word.id &&
                         ui.wordIdentityFromNativeBaseline == identity && ui.tagIDFromNativeBaseline == before.tag.objectID)
            try #require(ui.previousPID > 0 && ui.appPID > 0 && ui.previousPID != ui.appPID)
            try #require(ProcessInfo.processInfo.processIdentifier != ui.previousPID &&
                         ProcessInfo.processInfo.processIdentifier != ui.appPID)
            let beforeFields = try stableFields(before.native, excluding: changedKeys)
            let afterFields = try stableFields(after.native, excluding: changedKeys)
            try #require(beforeFields == afterFields)
            let beforeTag = try stableFields(before.tag)
            let afterTag = try stableFields(after.tag)
            try #require(beforeTag == afterTag && before.tag.objectID == after.tag.objectID)
            let originalPayload = try payload(before)
            let actualPayload = try payload(after)
            let survivors = originalPayload.records.filter { !($0.blockId == nil && $0.item.id == word.id) }
            try #require(survivors.count + 1 == originalPayload.records.count)
            try #require(actualPayload.version == originalPayload.version &&
                         actualPayload.unknownFields == originalPayload.unknownFields && actualPayload.records == survivors)
            // Compare raw JSON values too, retaining every unknown record/item
            // field and timestamp representation outside the removed record.
            var rawExpected = try JSONDecoder().decode([String: TorahJSONValue].self, from: Data(before.canonicalRaw.utf8))
            let rawActual = try JSONDecoder().decode([String: TorahJSONValue].self, from: Data(after.canonicalRaw.utf8))
            guard case .array(let records)? = rawExpected["records"] else {
                throw NativeAcceptanceError.conditionTimeout("G02 canonical records array")
            }
            let retainedRecords = records.filter { record in
                guard case .object(let fields) = record, case .object(let item)? = fields["item"] else { return true }
                return !(item["id"] == .string(word.id) && (fields["blockId"] == nil || fields["blockId"] == .null))
            }
            try #require(retainedRecords.count + 1 == records.count)
            rawExpected["records"] = .array(retainedRecords)
            try #require(rawActual == rawExpected)
            var expectedLabels = try labels(before)
            try #require(expectedLabels.removeValue(forKey: identity) != nil)
            let actualLabels = try labels(after)
            try #require(actualLabels == expectedLabels)
        }
    }

    @MainActor
    static func observe() async throws {
        let env = ProcessInfo.processInfo.environment
        try #require(NativeTypePreservation.disabledFlags.allSatisfy { env[$0] == "0" })
        try #require(env["PINKHA_TYPE_PRESERVATION_POSTFLIGHT"] == "0")
        let phase = try #require(env["PINKHA_G02_NATIVE_PHASE"])
        try #require(["baseline", "postflight"].contains(phase))
        let controller = try controller()
        let token = try #require(controller["TOKEN"])
        let fixtureData = try input("PINKHA_NATIVE_UI_FIXTURE_JSON", maximum: 65_536)
        try #require(sha256(fixtureData) == controller["FIXTURE_SHA256"])
        let fixture = try JSONDecoder().decode(Fixture.self, from: fixtureData)
        try #require(!fixture.spaceId.isEmpty && Set(fixture.documents.keys) == Set(roles) &&
                     Set(fixture.documents.values).count == roles.count &&
                     Set(roles.compactMap { fixture.types[$0] }).count == roles.count)
        try #require(!fixture.documents.values.contains("") && !roles.contains { fixture.types[$0]?.isEmpty != false })
        try #require(!fixture.typeSwitch.objectId.isEmpty && !fixture.documents.values.contains(fixture.typeSwitch.objectId))
        let seedData = try hashedInput("PINKHA_G02_SEED_UI_JSON")
        let seed = try JSONDecoder().decode(Seed.self, from: seedData)
        try #require(seed.schema == "pinkha-g02-word-ui-observation-v1" && seed.phase == "seed-complete" &&
                     seed.spaceID == fixture.spaceId && seed.controller == controller && Set(seed.documents.keys) == Set(roles))
        for role in roles {
            let value = try #require(seed.documents[role])
            try #require(value.objectID == fixture.documents[role] && value.typeID == fixture.types[role] &&
                         value.name == fixture.names[value.objectID] && value.sourceLabel == fixture.sourceLabel &&
                         value.topicLabel == fixture.topicLabel && !value.wordLabel.isEmpty &&
                         ["Tag", "Tags"].contains(value.tagPropertyName) &&
                         value.tagName == "G02 " + role + " " + String(token.prefix(8)))
        }
        let support = try NativeTypePreservation.supportURL()
        let installedFixture = try Data(contentsOf: support.appendingPathComponent("pinkha-native-derived-ui-fixture.json"))
        try #require(installedFixture == fixtureData)
        let beforeDirectories = try NativeTypePreservation.directories()
        let directories = NativeTypePreservation.Directories(container: beforeDirectories.0, middleware: beforeDirectories.1)
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        while Container.shared.accountManager().account.id.isEmpty && clock.now < deadline {
            try await Task.sleep(for: .milliseconds(100))
        }
        let state = try await readState(fixture: fixture)
        let baselineURL = support.appendingPathComponent("pinkha-g02-word-native-baseline-" + token + ".json")
        let baselineSHA = phase == "postflight" ? env["PINKHA_G02_BASELINE_SHA256"] : nil
        let unlinkData: Data?
        if phase == "postflight" { unlinkData = try hashedInput("PINKHA_G02_UNLINK_UI_JSON") }
        else { unlinkData = nil }
        func receipt(status: String) -> Receipt {
            .init(schema: "pinkha-g02-word-native-readback-v1", status: status, phase: phase,
                controller: controller, fixtureSHA256: sha256(fixtureData), seedUIReceiptSHA256: sha256(seedData),
                nativeBaselineSHA256: baselineSHA, unlinkUIReceiptSHA256: unlinkData.map(sha256),
                processID: ProcessInfo.processInfo.processIdentifier, directories: directories,
                verifierCallsMutationAPI: false, scope: "THREE_WRITING_OBJECTS_PROPERTIES_NOT_WHOLE_STORE_BYTES",
                permittedClockKeys: clockKeys.sorted(), state: state)
        }
        // Preserve the actual observations even when a following comparison fails.
        _ = try write(receipt(status: "OBSERVED_NATIVE_STATE_NOT_ACCEPTANCE"),
            to: support.appendingPathComponent("pinkha-g02-word-native-" + phase + "-observed-" + token + ".json"))
        try validate(state, fixture: fixture, seed: seed, phase: phase)
        let afterDirectories = try NativeTypePreservation.directories()
        try #require(afterDirectories.0 == beforeDirectories.0 && afterDirectories.1 == beforeDirectories.1)
        let finalFixture = try Data(contentsOf: support.appendingPathComponent("pinkha-native-derived-ui-fixture.json"))
        try #require(finalFixture == fixtureData)
        if phase == "baseline" {
            let baseline = receipt(status: "PASS_BASELINE_READ_ONLY")
            let data = try write(baseline, to: baselineURL)
            let ui = try uiBaseline(baseline, hash: sha256(data))
            _ = try write(ui, to: support.appendingPathComponent("pinkha-g02-word-ui-baseline-" + token + ".json"))
        } else {
            let originalData = try Data(contentsOf: baselineURL)
            try #require(!originalData.isEmpty && originalData.count <= maximumReceiptBytes && sha256(originalData) == baselineSHA)
            let baseline = try JSONDecoder().decode(Receipt.self, from: originalData)
            try #require(baseline.schema == "pinkha-g02-word-native-readback-v1" &&
                         baseline.status == "PASS_BASELINE_READ_ONLY" && baseline.phase == "baseline" &&
                         baseline.controller == controller && baseline.fixtureSHA256 == sha256(fixtureData) &&
                         baseline.seedUIReceiptSHA256 == sha256(seedData) && !baseline.verifierCallsMutationAPI &&
                         baseline.processID > 0 && baseline.processID != ProcessInfo.processInfo.processIdentifier)
            let rawUnlink = try #require(unlinkData)
            let unlink = try JSONDecoder().decode(Unlink.self, from: rawUnlink)
            try #require(unlink.schema == "pinkha-g02-word-ui-observation-v1" && unlink.phase == "unlink-complete" &&
                         unlink.spaceID == fixture.spaceId && unlink.controller == controller &&
                         unlink.nativeBaselineSHA256 == sha256(originalData) && unlink.seedUIReceiptSHA256 == sha256(seedData) &&
                         unlink.nativePersistencePostflightRequired && Set(unlink.documents.keys) == Set(roles))
            try validate(baseline.state, fixture: fixture, seed: seed, phase: "baseline")
            try compare(baseline.state, state, unlink: unlink)
            _ = try write(receipt(status: "PASS_EXACT_DOCUMENT_WORD_UNLINK_NATIVE_READBACK"),
                to: support.appendingPathComponent("pinkha-g02-word-native-postflight-" + token + ".json"))
        }
    }
}
