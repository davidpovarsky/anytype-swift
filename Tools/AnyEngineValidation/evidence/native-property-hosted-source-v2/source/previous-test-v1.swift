#if os(iOS)
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaAnyRuntime
import PinkhaAnyNative

/// Actual iOS AnyLib, normal application authentication and a fresh owned Space.
/// The private workflow below is mechanically extracted from PropertyProbe.swift:
/// its fifteen ordered business checks, native calls and strict receipts remain.
/// Its creation journal is the original in-memory metadata fixture; protected
/// persistence and UIKit gestures have their own acceptance tests.
@MainActor
final class NativePropertyWorkflowTests: XCTestCase {
    func testOriginalFifteenPropertyAssertionsOnRealNativeLibrary() async throws {
        XCTAssertEqual(AnyEmbeddedBuild.linked, .pinkhaNativeV1,
                       "This acceptance must link the source-verified patched Any library.")
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("native-property-proof-" + UUID().uuidString, isDirectory: true)
        let credentialService = "io.pinkha.property.native.tests." + UUID().uuidString
        let application = try AnyNativeApplication(dataDirectory: directory, credentialService: credentialService)
        var accountID: String?
        var ownedSpaceID: String?
        do {
            try await application.start(network: .official)
            let account = try await application.createAccount()
            accountID = account.id
            try await application.acknowledgeRecoveryBackup(accountID: account.id)
            let spaceID = try await application.createSpace(name: "Disposable iOS native property acceptance")
            ownedSpaceID = spaceID
            let owner = try await application.connectSpace(id: spaceID)
            let fixture = try await makeFixture(owner: owner)
            let completed = try await NativePropertyWorkflowProbe.runNativePropertyProbe(
                client: owner.client, workspace: owner.workspace, owner: owner.session, fixture: fixture)
            XCTAssertEqual(completed, Self.expectedChecks,
                           "Every original property assertion must complete in the original order.")
            try await application.deleteSpace(id: spaceID)
            ownedSpaceID = nil
            try await application.signOut()
            try await application.removeSavedAccount(id: account.id)
            await application.stop()
            try await AnyProtectedCreationJournal.removeAccountData(accountID: account.id)
            try FileManager.default.removeItem(at: directory)
        } catch {
            if let ownedSpaceID { try? await application.deleteSpace(id: ownedSpaceID) }
            await application.stop()
            if let accountID {
                try? AnyNativeCredentialVault(service: credentialService).remove(accountID: accountID)
                try? await AnyProtectedCreationJournal.removeAccountData(accountID: accountID)
            }
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    /// Same real Type/Collection requests as the executed native Property15
    /// fixture builder. IDs are returned by native APIs, never invented here.
    private func makeFixture(owner: AnyNativeWorkspaceOwner) async throws -> NativePropertyWorkflowProbe.PropertyProbeFixture {
        let client = owner.client
        let spacePath = ["v1", "spaces", owner.workspace.spaceID]
        let nonce = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        return try await owner.session.perform { lease in
            let type = try await client.requestJSON(method: "POST", path: spacePath + ["types"],
                body: .object(["name": .string("Native property canonical document"),
                               "xKey": .string("native_prop_type_" + nonce)]),
                authorize: { try await lease.validate() })
            let typeID = try type.requireString("typeId")
            _ = try await client.requestJSON(method: "POST", path: spacePath + ["types", typeID, "parts"],
                body: .object(["key": .string("body"),
                               "datasets": .array([.object(["module": .string("editor")])])]),
                authorize: { try await lease.validate() })
            let policy = try await client.requestJSON(method: "GET",
                path: spacePath + ["pinkha", "document-types", typeID],
                authorize: { try await lease.validate() })
            try NativePropertyWorkflowProbe.require(policy["eligible"] == .bool(true) &&
                policy["canonicalEditorDataset"] == .string("editor_blocks"),
                "actual custom Type does not declare a canonical editor")
            let collection = try await client.requestJSON(method: "POST", path: spacePath + ["collections"],
                body: .object(["name": .string("Native property preserved values"),
                               "xKey": .string("native_prop_values_" + nonce)]),
                authorize: { try await lease.validate() })
            let collectionID = try collection.requireString("collectionId")
            let text = try await client.requestJSON(method: "POST",
                path: spacePath + ["collections", collectionID, "properties"],
                body: .object(["name": .string("Text value"), "xKey": .string("text_value"),
                               "kind": .string("string"), "scope": .string("synced")]),
                authorize: { try await lease.validate() })
            let number = try await client.requestJSON(method: "POST",
                path: spacePath + ["collections", collectionID, "properties"],
                body: .object(["name": .string("Number value"), "xKey": .string("number_value"),
                               "kind": .string("number"), "scope": .string("synced")]),
                authorize: { try await lease.validate() })
            return try NativePropertyWorkflowProbe.PropertyProbeFixture(arguments: [
                "--custom-type-id", typeID, "--collection-id", collectionID,
                "--text-property-id", text.requireString("propId"),
                "--number-property-id", number.requireString("propId")])
        }
    }

    private static let expectedChecks: [String] = [
        "native_custom_type_catalog_uses_canonical_definition_proof",
        "synthetic_page_and_canonical_body_created_through_guarded_routes",
        "type_switch_preserves_existing_body_and_exact_native_block_identity",
        "type_undo_and_reapply_are_native_version_conditional",
        "explicit_native_policy_allows_new_block_on_current_custom_document",
        "non_document_type_refused_before_dispatch",
        "collection_attach_and_typed_property_writes_have_verified_readback",
        "detach_and_reattach_preserve_orphan_namespace_values",
        "hide_attaches_verified_preferences_without_deleting_business_values",
        "show_preserves_unknown_future_visibility_keys",
        "derived_source_visibility_stays_in_presentation_namespace",
        "verified_property_undo_preserves_unedited_sibling_fields",
        "stale_full_version_edit_refused_without_unconditional_fallback",
        "complete_property_workflow_preserves_canonical_body_children_and_unknown_style",
        "only_allocated_synthetic_page_removed"
    ]
}

// Test-only namespace. There is no executable @main, transport override,
// production API hook, mock HTTP response, or alternate acknowledgment rule.
private enum NativePropertyWorkflowProbe {
    enum ProbeError: Error { case usage, failed(String) }
    nonisolated static func require(_ value: Bool, _ label: String) throws {
        guard value else { throw ProbeError.failed(label) }
    }

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
    nonisolated static func runNativePropertyProbe(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                                owner: AnyApplicationSession, fixture: PropertyProbeFixture) async throws -> [String] {
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
                    body: snapshot.fence.requestBody(patch: [
                        AnyNativePropertyStore.hiddenPropertiesID: .array(keys.map(AnyJSON.string))]),
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
            return checks
        } catch {
            try? await cleanup()
            throw error
        }
    }

    private nonisolated static func propertyProbeVerified(_ receipt: AnyPropertyEditReceipt) throws -> AnyNativePropertySnapshot {
        guard receipt.readback == .verifiedCurrent, let snapshot = receipt.snapshot else {
            throw ProbeError.failed("property native acceptance lacked exact version readback")
        }
        return snapshot
    }

    nonisolated static func creationProbeMutationID() -> String {
        UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    }
    actor CreationProbeObjects {
        private var ids: Set<String> = []
        func insert(_ id: String) { ids.insert(id) }
        func values() -> [String] { ids.sorted() }
    }
    actor CreationProbeJournal: AnyNativeCreationJournaling {
        nonisolated let workspace: AnyTorahWorkspace
        private struct Entry: Codable { let identity: AnyNativeCreationIdentity; var state: AnyNativeCreationState }
        private var entries: [String: Entry] = [:]
        init(workspace: AnyTorahWorkspace) { self.workspace = workspace }
        func reserve(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationReservation {
            guard identity.workspace == workspace else { throw AnyHostError.wrongWorkspace }
            if let entry = entries[identity.key] {
                guard entry.identity == identity else { throw AnyNativeCreationError.contentConflict }
                return .init(state: entry.state, ownsDispatch: false)
            }
            entries[identity.key] = .init(identity: identity, state: .reserved)
            return .init(state: .reserved, ownsDispatch: true)
        }
        func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) throws {
            guard var entry = entries[identity.key], entry.identity == identity else {
                throw AnyNativeCreationError.contentConflict
            }
            if let old = entry.state.objectID, state.objectID != old { throw AnyNativeCreationError.contentConflict }
            if case .verified = entry.state {
                guard state == entry.state else { throw AnyNativeCreationError.contentConflict }
            }
            entry.state = state; entries[identity.key] = entry
        }
        func lookup(_ identity: AnyNativeCreationIdentity) throws -> AnyNativeCreationState? {
            guard identity.workspace == workspace else { throw AnyHostError.wrongWorkspace }
            guard let entry = entries[identity.key] else { return nil }
            guard entry.identity == identity else { throw AnyNativeCreationError.contentConflict }
            return entry.state
        }
        func metadata() throws -> Data {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            return try encoder.encode(entries)
        }
    }
}
#endif
