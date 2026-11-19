import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost

struct PropertyProbeFixture: Sendable {
    let typeID: String
    let collectionID: String
    let textPropertyID: String
    let numberPropertyID: String
    init(arguments: [String]) throws {
        func value(_ name: String) throws -> String {
            guard let index = arguments.firstIndex(of: name), arguments.indices.contains(index + 1),
                  !arguments[index + 1].hasPrefix("--") else { throw ProbeError.usage }
            return arguments[index + 1]
        }
        typeID = try value("--custom-type-id"); collectionID = try value("--collection-id")
        textPropertyID = try value("--text-property-id"); numberPropertyID = try value("--number-property-id")
    }
}

/// Actual production property/document/block APIs. The only test double is the
/// explicitly in-memory creation metadata journal; schema/ACL/CAS are real Any.
func runNativePropertyProbe(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                            owner: AnyApplicationSession, fixture: PropertyProbeFixture) async throws {
    let properties = try AnyNativePropertyStore(client: client, workspace: workspace, policy: .init())
    let documents = try AnyEditorDocumentStore(client: client, workspace: workspace, allowedTypeIDs: ["page"],
                                                documentTypePolicy: .nativeCanonicalEditorV1)
    let journal = CreationProbeJournal(workspace: workspace)
    let allocated = CreationProbeObjects()
    let objects = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
    let blocks = try AnyNativeBlockCreator(client: client, workspace: workspace, journal: journal,
                                           allowedTypeIDs: ["page"], documentTypePolicy: .nativeCanonicalEditorV1)
    let spacePath = ["v1", "spaces", workspace.spaceID]
    func cleanup() async throws {
        await owner.revokeAndDrain()
        for id in await allocated.values() {
            _ = try await client.requestJSON(method: "DELETE", path: spacePath + ["objects", id])
        }
    }
    do {
        var checks = try await owner.perform { lease -> [String] in
            var checks: [String] = []
            let catalog = try await properties.catalog(lease: lease)
            try require(catalog.selectableDocumentTypes.contains(where: { $0.id == fixture.typeID }) &&
                        !catalog.selectableDocumentTypes.contains(where: { $0.id == "any" }),
                        "custom document catalog eligibility")
            checks.append("native_custom_type_catalog_uses_canonical_definition_proof")
            let intent = try AnyNativeObjectCreationIntent(workspace: workspace, mutationID: creationProbeMutationID(),
                typeID: "page", initialProperties: .object(["any": .object([
                    "name": .string("בדיקת מאפיינים מקורית " + creationProbeMutationID())])]))
            let id = try await objects.ensureObject(intent, authorize: { try await lease.validate() },
                onNativeConfirmed: { id in await allocated.insert(id) })
            await allocated.insert(id)
            let block = try AnyNativeBlockCreationIntent(workspace: workspace, mutationID: creationProbeMutationID(),
                objectID: id, type: "paragraph", text: "**טקסט נשמר**", style: .object([
                    "futureStyle": .object(["preserved": .bool(true)])]), position: "PPPP")
            let blockID = try await blocks.ensureBlock(block, authorize: { try await lease.validate() })
            var snapshot = try await properties.read(objectID: id, lease: lease, catalog: catalog)
            let bodyBefore = try await documents.read(objectID: id, lease: lease)
            try require(bodyBefore.snapshot.depthFirstIDs == [blockID], "initial body")
            checks.append("synthetic_page_and_canonical_body_created_through_guarded_routes")

            let changedType = try await properties.apply(properties.prepareSetType(snapshot, typeID: fixture.typeID),
                lease: lease, authorize: { try await lease.validate() })
            snapshot = try propertyProbeVerified(changedType)
            let customBody = try await documents.read(objectID: id, lease: lease)
            try require(snapshot.currentTypeID == fixture.typeID &&
                customBody.snapshot.depthFirstIDs == [blockID] &&
                customBody.snapshot.blocks.first?.text == block.text &&
                customBody.snapshot.blocks.first?.native["style"]?["futureStyle"]?["preserved"]?.bool == true,
                "custom Type switch damaged body or required allowlist expansion")
            checks.append("type_switch_preserves_existing_body_and_exact_native_block_identity")

            guard let typeUndo = changedType.undo else { throw ProbeError.failed("missing verified type undo") }
            snapshot = try propertyProbeVerified(await properties.apply(typeUndo, lease: lease,
                authorize: { try await lease.validate() }))
            try require(snapshot.currentTypeID == "page", "type undo")
            snapshot = try propertyProbeVerified(await properties.apply(properties.prepareSetType(snapshot, typeID: fixture.typeID),
                lease: lease, authorize: { try await lease.validate() }))
            checks.append("type_undo_and_reapply_are_native_version_conditional")

            let child = try AnyNativeBlockCreationIntent(workspace: workspace, mutationID: creationProbeMutationID(),
                objectID: id, type: "quote", text: "בלוק בסוג מותאם", parentID: blockID, position: "PPPP")
            let childID = try await blocks.ensureBlock(child, authorize: { try await lease.validate() })
            let withChild = try await documents.read(objectID: id, lease: lease)
            try require(withChild.snapshot.depthFirstIDs == [blockID, childID], "new block on custom Type")
            checks.append("explicit_native_policy_allows_new_block_on_current_custom_document")

            snapshot = try await properties.read(objectID: id, lease: lease)
            do {
                _ = try properties.prepareSetType(snapshot, typeID: "any")
                throw ProbeError.failed("ineligible type entered picker write")
            } catch AnyNativePropertyError.unavailableDocumentType {}
            checks.append("non_document_type_refused_before_dispatch")

            snapshot = try propertyProbeVerified(await properties.apply(
                properties.prepareAttachCollection(snapshot, collectionID: fixture.collectionID), lease: lease,
                authorize: { try await lease.validate() }))
            let textKey = try AnyNativePropertyKey(ownerID: fixture.collectionID, propertyID: fixture.textPropertyID)
            let numberKey = try AnyNativePropertyKey(ownerID: fixture.collectionID, propertyID: fixture.numberPropertyID)
            let originalText = "ערך עברי — המקור והרישיון נשמרים"
            snapshot = try propertyProbeVerified(await properties.apply(properties.prepareSetValue(snapshot, key: textKey,
                value: .string(originalText)), lease: lease, authorize: { try await lease.validate() }))
            snapshot = try propertyProbeVerified(await properties.apply(properties.prepareSetValue(snapshot, key: numberKey,
                value: .number(42.5)), lease: lease, authorize: { try await lease.validate() }))
            try require(snapshot.raw[fixture.collectionID]?[fixture.textPropertyID]?.string == originalText &&
                        snapshot.raw[fixture.collectionID]?[fixture.numberPropertyID] == .number(42.5), "ordinary native property values")
            checks.append("collection_attach_and_typed_property_writes_have_verified_readback")

            snapshot = try propertyProbeVerified(await properties.apply(
                properties.prepareDetachCollection(snapshot, collectionID: fixture.collectionID), lease: lease,
                authorize: { try await lease.validate() }))
            try require(!snapshot.collectionIDs.contains(fixture.collectionID) &&
                snapshot.raw[fixture.collectionID]?[fixture.textPropertyID]?.string == originalText &&
                snapshot.raw[fixture.collectionID]?[fixture.numberPropertyID] == .number(42.5), "detach deleted orphan values")
            snapshot = try propertyProbeVerified(await properties.apply(
                properties.prepareAttachCollection(snapshot, collectionID: fixture.collectionID), lease: lease,
                authorize: { try await lease.validate() }))
            try require(snapshot.rows.first(where: { $0.id == textKey })?.value == .string(originalText), "reattach lost value")
            checks.append("detach_and_reattach_preserve_orphan_namespace_values")

            snapshot = try propertyProbeVerified(await properties.setVisibility(snapshot, key: .init(property: textKey),
                visible: false, lease: lease, authorize: { try await lease.validate() }))
            try require(snapshot.presentationAttached && snapshot.hiddenPropertyKeys.contains(textKey.visibilityKey) &&
                snapshot.raw[fixture.collectionID]?[fixture.textPropertyID]?.string == originalText, "hide removed business value")
            checks.append("hide_attaches_verified_preferences_without_deleting_business_values")

            let futureKey = "future:v99:העדפה-שאינה-מוכרת"
            let keys = snapshot.hiddenPropertyKeys.union([futureKey]).sorted()
            _ = try await client.requestJSON(method: "POST",
                path: spacePath + ["pinkha", "properties", id, "set", AnyNativePropertyStore.presentationCollectionID],
                body: .object(["patch": .object([AnyNativePropertyStore.hiddenPropertiesID: .array(keys.map(AnyJSON.string))]),
                    "ifVersion": snapshot.nativeVersion, "ifStartedAt": .string(lease.engineStartedAt)]),
                authorize: { try await lease.validate() })
            snapshot = try await properties.read(objectID: id, lease: lease)
            snapshot = try propertyProbeVerified(await properties.setVisibility(snapshot, key: .init(property: textKey),
                visible: true, lease: lease, authorize: { try await lease.validate() }))
            try require(snapshot.hiddenPropertyKeys == [futureKey] &&
                snapshot.raw[fixture.collectionID]?[fixture.textPropertyID]?.string == originalText, "show dropped unknown key/value")
            checks.append("show_preserves_unknown_future_visibility_keys")

            snapshot = try propertyProbeVerified(await properties.setVisibility(snapshot, key: .init(derived: .sources),
                visible: false, lease: lease, authorize: { try await lease.validate() }))
            try require(snapshot.hiddenPropertyKeys == [futureKey, AnyNativePropertyVisibilityKey(derived: .sources).rawValue] &&
                snapshot.raw[fixture.collectionID]?[fixture.textPropertyID]?.string == originalText,
                "derived visibility wrote business fields")
            checks.append("derived_source_visibility_stays_in_presentation_namespace")

            let textChange = try await properties.apply(properties.prepareSetValue(snapshot, key: textKey,
                value: .string("ערך זמני")), lease: lease, authorize: { try await lease.validate() })
            _ = try propertyProbeVerified(textChange)
            guard let valueUndo = textChange.undo else { throw ProbeError.failed("missing verified property undo") }
            snapshot = try propertyProbeVerified(await properties.apply(valueUndo, lease: lease,
                authorize: { try await lease.validate() }))
            try require(snapshot.raw[fixture.collectionID]?[fixture.textPropertyID]?.string == originalText &&
                snapshot.raw[fixture.collectionID]?[fixture.numberPropertyID] == .number(42.5), "property undo damaged sibling value")
            checks.append("verified_property_undo_preserves_unedited_sibling_fields")

            let stale = try properties.prepareSetValue(snapshot, key: numberKey, value: .number(99.0))
            snapshot = try propertyProbeVerified(await properties.apply(properties.prepareSetValue(snapshot, key: textKey,
                value: .string("שינוי מקביל")), lease: lease, authorize: { try await lease.validate() }))
            do {
                _ = try await properties.apply(stale, lease: lease, authorize: { try await lease.validate() })
                throw ProbeError.failed("stale property edit accepted")
            } catch AnyHostError.changedDocument {}
            let afterStale = try await properties.read(objectID: id, lease: lease)
            try require(afterStale.nativeVersion == snapshot.nativeVersion &&
                afterStale.raw[fixture.collectionID]?[fixture.numberPropertyID] == .number(42.5),
                "stale property fallback wrote")
            checks.append("stale_full_version_edit_refused_without_unconditional_fallback")

            let finalBody = try await documents.read(objectID: id, lease: lease)
            try require(finalBody.snapshot.depthFirstIDs == [blockID, childID] &&
                finalBody.snapshot.blocks.first(where: { $0.id == blockID })?.text == block.text &&
                finalBody.snapshot.blocks.first(where: { $0.id == blockID })?.native["style"]?["futureStyle"]?["preserved"]?.bool == true,
                "property workflow mutated canonical editor body")
            checks.append("complete_property_workflow_preserves_canonical_body_children_and_unknown_style")
            return checks
        }
        try await cleanup()
        checks.append("only_allocated_synthetic_page_removed")
        let result: AnyJSON = .object(["status": .string("PASS"), "count": .integer(Int64(checks.count)),
            "checks": .array(checks.map(AnyJSON.string)),
            "scope": .string("real v6 native property/type/collection/visibility/undo with production Host; in-memory creation metadata fixture; protected persistence separate")])
        print(String(decoding: try JSONEncoder().encode(result), as: UTF8.self))
    } catch {
        try? await cleanup()
        throw error
    }
}

private func propertyProbeVerified(_ receipt: AnyPropertyEditReceipt) throws -> AnyNativePropertySnapshot {
    guard receipt.readback == .verifiedCurrent, let snapshot = receipt.snapshot else {
        throw ProbeError.failed("property native acceptance lacked exact version readback")
    }
    return snapshot
}
