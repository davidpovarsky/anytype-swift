import Foundation
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration

enum ProbeFailure: Error { case configuration, assertion(String) }

@main
struct IntegrationProbe {
    static func main() async throws {
        let args = CommandLine.arguments
        guard args.count == 5, args[1] == "--disposable",
              let url = URL(string: args[2]) else { throw ProbeFailure.configuration }
        let workspace = try AnyTorahWorkspace(accountID: args[3], spaceID: args[4])
        let client = try AnyHTTPClient(baseURL: url, expectedAccountID: workspace.accountID)
        try await client.checkAccount()
        let base = ["v1", "spaces", workspace.spaceID]
        let suffix = UUID().uuidString
        var checks: [String: Bool] = [:]
        func check(_ name: String, _ condition: Bool) throws {
            guard condition else { throw ProbeFailure.assertion(name) }
            checks[name] = true
        }
        let created = try await client.requestJSON(method: "POST", path: base + ["objects"], body: .object([
            "type": .string("page"),
            "initialProperties": .object(["any": .object([
                "name": .string("Pinkha Any bridge disposable " + suffix)
            ])])
        ]))
        let objectID = try created.requireString("objectId")
        let fetched = try await client.requestJSON(method: "GET", path: base + ["objects", objectID])
        guard let typeID = fetched["record"]?["any"]?["type"]?.string else {
            throw ProbeFailure.assertion("native_type")
        }
        let access = try AnyHTTPTorahTargetAccess(
            client: client, workspace: workspace, allowedTypeIDs: [typeID])
        let store = try AnyNativeTorahOperationStore(client: client, workspace: workspace)
        try await store.repository.install()
        let repository = try AnyTorahAssociationRepository(workspace: workspace, store: store, access: access)
        let target = TorahAssociationTarget.object(objectId: objectID)
        try await access.validate(target, intent: .write)
        try check("real_native_target_membership", true)

        func item(_ id: String, role: TorahAssociationRole = .context) -> TorahAssociationItem {
            .init(id: id, kind: .ref, role: role, providerID: "sefaria", externalID: "Genesis.1.1",
                  canonicalKey: "Genesis 1:1", labelHe: "בראשית א:א",
                  unknownFields: ["probe": .object(["kept": .bool(true)])])
        }
        _ = try await repository.addAssociation(item("context"), target: target, spaceId: workspace.spaceID)
        let dedup = try await repository.addAssociation(item("retry-context"), target: target, spaceId: workspace.spaceID)
        try check("context_semantic_dedup_stable_id", dedup.id == "context")
        for id in ["quote-A", "quote-B"] {
            _ = try await repository.addAssociation(item(id, role: .sourceQuote), target: target, spaceId: workspace.spaceID)
        }
        let documents = try await repository.listDocumentAssociations(objectId: objectID, spaceId: workspace.spaceID)
        try check("separate_quote_instances", Set(documents.map(\.id)) == ["context", "quote-A", "quote-B"])

        let blockResult = try await client.requestJSON(
            method: "POST", path: base + ["objects", objectID, "editor", "editor_blocks", "blocks"],
            body: .object(["type": .string("paragraph"), "text": .string("בדיקת שמירת הקשרים")]))
        guard let blockID = blockResult["recordIds"]?.array?.first?.string else {
            throw ProbeFailure.assertion("native_block_id")
        }
        let blockTarget = TorahAssociationTarget.block(objectId: objectID, blockId: blockID)
        try await access.validate(blockTarget, intent: .write)
        _ = try await repository.addAssociation(item("block-context"), target: blockTarget, spaceId: workspace.spaceID)
        try check("block_scope", try await repository.listBlockAssociations(
            objectId: objectID, blockId: blockID, spaceId: workspace.spaceID).count == 1)

        var revised = item("context"); revised.labelEn = "Prepared native revision"
        guard let prepared = try await repository.prepareMutation(revised, target: target, spaceId: workspace.spaceID) else {
            throw ProbeFailure.assertion("prepared_mutation")
        }
        let restored = try JSONDecoder().decode(AnyTorahPreparedMutation.self, from: JSONEncoder().encode(prepared))
        _ = try await repository.commitPrepared(restored)
        _ = try await repository.commitPrepared(restored)
        let state = try await store.snapshot()
        try check("prepared_exact_retry", state.all.filter { $0.id == restored.operation.claimID }.count == 1)
        try await repository.removeAssociation(associationId: "quote-A", target: target, spaceId: workspace.spaceID)
        let remaining = try await repository.listDocumentAssociations(objectId: objectID, spaceId: workspace.spaceID)
        try check("observed_remove_keeps_other_quote", Set(remaining.map(\.id)) == ["context", "quote-B"])

        let legacyItem = TorahAssociationItem(
            id: "migration-quote", kind: .ref, role: .sourceQuote,
            providerID: "sefaria", externalID: "Exodus.1.1", canonicalKey: "Exodus 1:1",
            labelHe: "שמות א:א", unknownFields: ["futureItem": .number(7)])
        let legacy = TorahCanonicalAssociationsPayload(
            records: [.init(location: .init(spaceId: "legacy-space", target: .block(objectId: "legacy-object", blockId: "legacy-block")),
                            item: legacyItem, unknownFields: ["recordFuture": .string("kept")])],
            unknownFields: ["envelopeFuture": .array([.bool(true), .null])])
        let bytes = try TorahAssociationPayloadCodec().encodeCanonicalDocument(legacy)
        let plan = try AnyTorahMigrationPlan(
            sourceBytes: bytes, sourceSpaceID: "legacy-space", sourceObjectID: "legacy-object",
            workspace: workspace, targetObjectID: objectID,
            blockIDMap: ["legacy-block": blockID], migrationKey: "probe-" + suffix)
        let executor = try AnyTorahMigrationExecutor(workspace: workspace, store: store, access: access)
        let receipt = try await executor.execute(plan)
        let again = try await executor.execute(plan)
        try check("migration_complete_native_readback", receipt.status == .complete)
        try check("migration_retry_no_new_claim", again.status == .complete && again.acknowledgedClaimIDs.isEmpty)
        let imported = try await repository.listBlockAssociations(objectId: objectID, blockId: blockID, spaceId: workspace.spaceID)
        try check("migration_original_item_unchanged", imported.contains(legacyItem))
        try check("migration_original_bytes_retained", plan.sourceBytes == bytes)

        // A new repository instance proves no dependence on an in-memory shadow.
        let freshStore = try AnyNativeTorahOperationStore(client: client, workspace: workspace)
        let fresh = try AnyTorahAssociationRepository(workspace: workspace, store: freshStore, access: access)
        try check("fresh_adapter_reads_native_claims",
            try await fresh.listBlockAssociations(objectId: objectID, blockId: blockID, spaceId: workspace.spaceID) == imported)

        let wrong = try AnyHTTPClient(baseURL: url, expectedAccountID: "different-disposable-account")
        do {
            try await wrong.checkAccount()
            throw ProbeFailure.assertion("wrong_account_rejected")
        } catch AnyEngineError.accountChanged { checks["wrong_account_rejected"] = true }

        // Native orphan test: direct block deletion retains a child row, which
        // must not remain a valid association target merely because it exists.
        let parentResult = try await client.requestJSON(
            method: "POST", path: base + ["objects", objectID, "editor", "editor_blocks", "blocks"],
            body: .object(["type": .string("paragraph"), "text": .string("parent")]))
        guard let parentID = parentResult["recordIds"]?.array?.first?.string else { throw ProbeFailure.configuration }
        let childResult = try await client.requestJSON(
            method: "POST", path: base + ["objects", objectID, "editor", "editor_blocks", "blocks"],
            body: .object(["type": .string("paragraph"), "text": .string("child"),
                           "nav": .object(["parentId": .string(parentID)])]))
        guard let childID = childResult["recordIds"]?.array?.first?.string else { throw ProbeFailure.configuration }
        _ = try await client.requestJSON(method: "DELETE",
            path: base + ["objects", objectID, "editor", "editor_blocks", "blocks", parentID])
        do {
            try await access.validate(.block(objectId: objectID, blockId: childID), intent: .write)
            throw ProbeFailure.assertion("orphan_native_block_rejected")
        } catch TorahAssociationRepositoryError.targetNotFound { checks["orphan_native_block_rejected"] = true }

        struct Receipt: Codable {
            let scope: String
            let objectID: String
            let blockID: String
            let checks: [String: Bool]
            let limitations: [String]
        }
        let output = Receipt(scope: "standalone real Any/PinkhaKit adapter", objectID: objectID, blockID: blockID, checks: checks,
            limitations: ["No full iOS UI or physical-device acceptance", "No engine restart in this probe",
                          "No two-client sync proof", "Cross-object target/claim writes are not atomic"])
        let encoded = try JSONEncoder().encode(output)
        print(String(decoding: encoded, as: UTF8.self))
    }
}
