import Foundation
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration

enum NativeArchiveProbe {
    static func run(url: URL, accountID: String, spaceID: String) async throws {
        let workspace = try AnyTorahWorkspace(accountID: accountID, spaceID: spaceID)
        let client = try AnyHTTPClient(baseURL: url, expectedAccountID: accountID)
        try await client.checkAccount()
        let base = ["v1", "spaces", spaceID]
        let store = try AnyGuardedTorahOperationStore(client: client, workspace: workspace)
        _ = try await store.repository.verifyCapabilities()
        try await store.repository.install { try await client.checkAccount() }
        var owned: [String] = []
        var checks: [String: Bool] = [:]
        func check(_ name: String, _ value: Bool) throws {
            guard value else { throw ProbeFailure.assertion(name) }
            checks[name] = true
        }
        func create(_ title: String) async throws -> String {
            let response = try await client.requestJSON(method: "POST",
                path: base + ["pinkha", "objects"], body: .object([
                    "type": .string("page"),
                    "initialProperties": .object(["any": .object(["name": .string(title)])])
                ]))
            return try response.requireString("objectId")
        }
        func createBlock(_ objectID: String) async throws -> String {
            let response = try await client.requestJSON(method: "POST",
                path: base + ["pinkha", "objects", objectID, "editor", "editor_blocks", "blocks"],
                body: .object(["type": .string("paragraph"), "text": .string("Native canonical archive proof"),
                    "style": .object(["futureArchiveStyle": .string("kept")])]))
            guard let id = response["recordIds"]?.array?.first?.string else {
                throw ProbeFailure.assertion("native_block_id")
            }
            return id
        }
        func cleanup() async -> [String] {
            var failures: [String] = []
            for id in owned {
                do { _ = try await client.requestJSON(method: "DELETE", path: base + ["objects", id]) }
                catch { failures.append(id) }
            }
            return failures
        }
        do {
            let source = try await create("Disposable canonical archive source " + UUID().uuidString)
            owned.append(source)
            let destination = try await create("Disposable canonical archive target " + UUID().uuidString)
            owned.append(destination)
            let sourceBlock = try await createBlock(source)
            let destinationBlock = try await createBlock(destination)
            let sourceRow = try await client.requestJSON(method: "GET", path: base + ["objects", source])
            let destinationRow = try await client.requestJSON(method: "GET", path: base + ["objects", destination])
            guard let sourceType = sourceRow["record"]?["any"]?["type"]?.string,
                  let destinationType = destinationRow["record"]?["any"]?["type"]?.string else {
                throw ProbeFailure.assertion("native_type")
            }
            let access = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace,
                                                      allowedTypeIDs: [sourceType, destinationType])
            let repository = try AnyTorahAssociationRepository(workspace: workspace, store: store, access: access)
            func item(_ id: String, block: Bool = false, removed: Bool = false) -> TorahAssociationItem {
                .init(id: id, kind: .ref, role: block ? .sourceQuote : .context, providerID: "sefaria",
                    externalID: removed ? "Exodus.1.1" : "Genesis.1.1",
                    canonicalKey: removed ? "Exodus 1:1" : "Genesis 1:1", labelHe: "Canonical archive",
                    unknownFields: ["futureArchive": .object(["kept": .string("exact")])])
            }
            let documentTarget = TorahAssociationTarget.object(objectId: source)
            _ = try await repository.addAssociation(item("document"), target: documentTarget, spaceId: spaceID)
            _ = try await repository.addAssociation(item("quote", block: true),
                target: .block(objectId: source, blockId: sourceBlock), spaceId: spaceID)
            var revised = item("document"); revised.labelEn = "Kept revision"
            _ = try await repository.updateAssociation(revised, target: documentTarget, spaceId: spaceID)
            _ = try await repository.addAssociation(item("removed", removed: true),
                target: documentTarget, spaceId: spaceID)
            try await repository.removeAssociation(associationId: "removed", target: documentTarget, spaceId: spaceID)
            let before = try await store.objectSnapshot(objectID: source)
            let beforeDestination = try await store.objectSnapshot(objectID: destination)
            try check("actual_native_history", before.projection.all.count == 5 && before.projection.live.count == 2)
            try check("empty_destination_precondition", beforeDestination.projection.all.isEmpty)

            let service = try AnyTorahArchiveService(workspace: workspace, store: store, access: access)
            let archive = try await service.export(objectID: source) { try await client.checkAccount() }
            let bytes = try archive.encodedData()
            let reopened = try AnyTorahArchive.decode(bytes)
            try check("complete_object_archive_scope",
                      archive.sourceSpaceID == spaceID && archive.sourceObjectID == source &&
                      archive.claimCount == 5 && archive.liveClaimCount == 2 && archive.conflictCount == 0)
            try check("canonical_export_roundtrip", try reopened.encodedData() == bytes)
            try check("raw_payload_bytes_preserved",
                      reopened.canonicalPayloads == before.projection.all.map(\.operation.payload))
            let afterExport = try await store.objectSnapshot(objectID: source)
            try check("export_does_not_rewrite_source",
                      before.projection == afterExport.projection &&
                      before.readinessGeneration == afterExport.readinessGeneration)

            do {
                _ = try reopened.prepareImport(workspace: workspace, targetObjectID: destination,
                    blockIDMap: [:], migrationKey: "archive-native-test")
                throw ProbeFailure.assertion("unmapped_block_refusal")
            } catch AnyEngineError.invalidIdentity(_) {
                checks["unmapped_block_refusal"] = true
            }
            try check("failed_plan_does_not_write",
                      try await store.objectSnapshot(objectID: destination).projection.all.isEmpty)
            let plan = try reopened.prepareImport(workspace: workspace, targetObjectID: destination,
                blockIDMap: [sourceBlock: destinationBlock], migrationKey: "archive-native-test")
            try check("source_bytes_and_audit_digest",
                      plan.sourceBytes == bytes && plan.sourceSHA256 == AnyContentDigest.sha256(bytes))
            try check("explicit_identity_map",
                      plan.operations.count == 2 && Set(plan.operations.map(\.targetBlockID)) == ["", destinationBlock] &&
                      plan.operations.allSatisfy { $0.targetObjectID == destination && $0.authorID == accountID })
            let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
            let first = try await executor.execute(plan) { try await client.checkAccount() }
            try check("native_import_confirmed", first.status == .complete && first.acknowledgedClaimIDs.count == 2)
            let retry = try await executor.execute(plan) { try await client.checkAccount() }
            try check("native_retry_is_idempotent",
                      retry.status == .complete && retry.acknowledgedClaimIDs.isEmpty && retry.alreadyPresentClaimIDs.count == 2)
            let afterDestination = try await store.objectSnapshot(objectID: destination)
            try check("only_live_associations_imported", afterDestination.projection.all.count == 2 &&
                      afterDestination.projection.live.count == 2)
            let importedDocument = try await repository.listDocumentAssociations(objectId: destination, spaceId: spaceID)
            let importedBlock = try await repository.listBlockAssociations(
                objectId: destination, blockId: destinationBlock, spaceId: spaceID)
            try check("metadata_and_revision_preserved",
                importedDocument.first?.id == "document" && importedDocument.first?.labelEn == "Kept revision" &&
                importedBlock.first?.id == "quote" &&
                importedBlock.first?.unknownFields["futureArchive"] == .object(["kept": .string("exact")]))
            let finalSource = try await store.objectSnapshot(objectID: source)
            try check("original_native_claims_untouched", finalSource.projection == before.projection)
            let leftovers = await cleanup()
            try check("owned_disposable_objects_cleaned", leftovers.isEmpty)
            let result: [String: Any] = ["status": "PASS", "count": checks.count,
                "checks": checks, "archiveSHA256": AnyContentDigest.sha256(bytes),
                "scope": "Real Swift canonical native archive export/import; explicit mapping; no full Heart editor/file migration"]
            let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
            print(String(decoding: data, as: UTF8.self))
        } catch {
            let leftovers = await cleanup()
            let result: [String: Any] = ["status": "FAIL", "count": checks.count,
                "checks": checks, "cleanupUnconfirmedCount": leftovers.count,
                "error": String(describing: error)]
            let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
            print(String(decoding: data, as: UTF8.self))
            throw error
        }
    }
}
