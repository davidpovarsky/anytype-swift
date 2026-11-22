#if PINKHA_PREPARED_MIGRATION_ACCEPTANCE
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaAnyRuntime

/// One actual C-runtime, managed-HTTP and production-client journey. Native
/// storage is reopened in this same XCTest process; no OS crash, lost HTTP ACK,
/// network synchronization, inline-file route or full-Space import is claimed.
@MainActor
final class AnyPreparedMigrationRuntimeTests: XCTestCase {
    private struct Mounted: Sendable {
        let boot: AnyEmbeddedSession
        let client: AnyHTTPClient
        let owner: AnyApplicationSession
        let migration: AnyNativePreparedMigration
    }

    func testManagedPreparedObjectAndBlockSurviveOrderlyReopenAndRejectRevokedOwner() async throws {
        executionTimeAllowance = 900
        XCTAssertEqual(AnyEmbeddedBuild.linked, .pinkhaPreparedMigrationCandidateV1)
        let runtime = AnyEmbeddedRuntime.shared
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(
            "pinkha-prepared-migration-" + UUID().uuidString, isDirectory: true)
        let name = "הגירה מקומית — e\u{301}"
        let text = "שָׁלוֹם — עברית\nsecond e\u{301} 👩🏽‍💻\n"
        let style: AnyJSON = .object(["level": .integer(2)])
        var mounted: Mounted?
        var accountID: String?
        var spaceID: String?
        var observations: [AnyJSON] = []
        var generations: [String] = []
        var completed = false
        defer { attachProof(observations, generations: generations, completed: completed,
                            name: name, text: text) }
        do {
            let boot = try await runtime.start(dataDirectory: directory, network: .official, build: .linked)
            XCTAssertTrue(boot.engineVersion.hasPrefix("any v0.5.0-pinkha.prepared.1 "))
            let auth = try await authenticate(runtime, boot: boot)
            accountID = auth.accountID
            let firstClient = try boot.dataClient(expectedAccountID: auth.accountID)
            XCTAssertTrue(firstClient.hasManagedAuthorization)
            let space = try await firstClient.requestJSON(method: "POST", path: ["v1", "spaces"],
                body: .object(["name": .string("Disposable prepared migration Apple acceptance")]))
            let id = try XCTUnwrap(space["id"]?.string)
            spaceID = id
            let workspace = try AnyTorahWorkspace(accountID: auth.accountID, spaceID: id)
            var current = try await mount(boot, workspace: workspace)
            mounted = current
            generations.append(boot.generation.uuidString)
            let capabilities = current.migration.capabilities
            XCTAssertFalse(capabilities.networkVerified)
            let binding = try AnyPreparedMigrationPlanBinding(workspace: workspace,
                storeID: capabilities.storeID,
                planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)),
                planSHA256: AnyContentDigest.sha256(Data((name + "\n" + text).utf8)))
            let objectIntent = try AnyPreparedMigrationIntent.object(binding: binding,
                sourceKey: "disposable/source/object", typeID: "page",
                initialProperties: .object(["any": .object(["name": .string(name)])]))
            let root = try await prepare(objectIntent, on: current)
            XCTAssertEqual(root.stage, .rootPrepared)
            XCTAssertEqual(root.outcome, .prepared)
            let objectID = try XCTUnwrap(root.objectID)
            let rootChange = try XCTUnwrap(root.changeID)
            observations.append(observation("root-prepared", root, on: current))
            // Preparing signed bytes must not publish an ordinary object.
            do {
                _ = try await request(current, method: "GET", suffix: ["objects", objectID])
                XCTFail("Prepared root became visible before its native commit.")
            } catch let error as AnyEngineError {
                XCTAssertEqual(error, .http(status: 404, code: "object.not_found"))
            }
            let oldOwner = current.owner
            let oldMigration = current.migration
            let oldLease = try await oldOwner.perform { lease in lease }

            current = try await reopen(current, runtime: runtime, directory: directory, mnemonic: auth.mnemonic)
            mounted = current; generations.append(current.boot.generation.uuidString)
            XCTAssertEqual(current.migration.capabilities, capabilities)
            let recoveredRoot = try await prepare(objectIntent, on: current)
            XCTAssertEqual(recoveredRoot, root)
            // Two explicit one-stage native calls expose the durable object
            // boundaries. Final orchestration/retries use the product client.
            let rootCommitted = try await advanceOneNativeStage(root, on: current)
            XCTAssertEqual(rootCommitted.stage, .rootCommitted)
            XCTAssertEqual(rootCommitted.outcome, .prepared)
            XCTAssertEqual(rootCommitted.changeID, rootChange)
            requireIdentity(rootCommitted, original: root)
            observations.append(observation("root-committed", rootCommitted, on: current))

            current = try await reopen(current, runtime: runtime, directory: directory, mnemonic: auth.mnemonic)
            mounted = current; generations.append(current.boot.generation.uuidString)
            let rootStatus = try await status(objectIntent, on: current)
            XCTAssertEqual(rootStatus, rootCommitted)
            let bootstrap = try await advanceOneNativeStage(rootStatus, on: current)
            XCTAssertEqual(bootstrap.stage, .bootstrapPrepared)
            XCTAssertEqual(bootstrap.outcome, .prepared)
            let bootstrapChange = try XCTUnwrap(bootstrap.changeID)
            XCTAssertNotEqual(bootstrapChange, rootChange)
            requireIdentity(bootstrap, original: root)
            let rootOnly = try await request(current, method: "GET", suffix: ["objects", objectID])
            let rootOnlyRecord = try XCTUnwrap(rootOnly["record"]?.object)
            XCTAssertTrue(rootOnlyRecord["any"]?["name"]?.string?.isEmpty ?? true,
                          "Preparing bootstrap bytes applied their properties early.")
            observations.append(observation("bootstrap-prepared", bootstrap, on: current))

            current = try await reopen(current, runtime: runtime, directory: directory, mnemonic: auth.mnemonic)
            mounted = current; generations.append(current.boot.generation.uuidString)
            let bootstrapStatus = try await status(objectIntent, on: current)
            XCTAssertEqual(bootstrapStatus, bootstrap)
            let objectDone = try await commit(root, on: current)
            XCTAssertTrue(objectDone.isCompleteAndCurrent)
            requireIdentity(objectDone, original: root)
            XCTAssertEqual(objectDone.changeID, bootstrapChange)
            XCTAssertEqual(objectDone.recordIDs, [objectID])
            let objectReadback = try await requireObject(current, receipt: objectDone, name: name)
            observations.append(observation("object-complete", objectDone, on: current, readback: objectReadback))

            let blockIntent = try AnyPreparedMigrationIntent.block(binding: binding,
                sourceKey: "disposable/source/block", objectID: objectID,
                type: "heading", text: text, style: style, position: "m")
            let block = try await prepare(blockIntent, on: current)
            XCTAssertEqual(block.stage, .blockPrepared)
            XCTAssertEqual(block.outcome, .prepared)
            XCTAssertEqual(block.objectID, objectID)
            XCTAssertEqual(block.recordIDs.count, 1)
            _ = try XCTUnwrap(block.changeID)
            let empty = try await blocks(current, objectID: objectID)
            XCTAssertTrue(empty.isEmpty, "Prepared block bytes became a live body before commit.")
            observations.append(observation("block-prepared", block, on: current))

            current = try await reopen(current, runtime: runtime, directory: directory, mnemonic: auth.mnemonic)
            mounted = current; generations.append(current.boot.generation.uuidString)
            let recoveredBlock = try await status(blockIntent, on: current)
            XCTAssertEqual(recoveredBlock, block)
            let blockDone = try await commit(block, on: current)
            XCTAssertTrue(blockDone.isCompleteAndCurrent)
            requireIdentity(blockDone, original: block)
            XCTAssertEqual(blockDone.changeID, block.changeID)
            XCTAssertEqual(blockDone.recordIDs, block.recordIDs)
            let blockReadback = try await requireBlock(current, receipt: blockDone, text: text, style: style)
            observations.append(observation("block-complete", blockDone, on: current, readback: blockReadback))

            // A confirmed completed intent is reconciled after another native
            // SDK/store reopen. This is a retry, not simulated HTTP ACK loss.
            current = try await reopen(current, runtime: runtime, directory: directory, mnemonic: auth.mnemonic)
            mounted = current; generations.append(current.boot.generation.uuidString)
            let objectRetry = try await commit(root, on: current)
            let blockRetry = try await commit(block, on: current)
            XCTAssertEqual(objectRetry, objectDone)
            XCTAssertEqual(blockRetry, blockDone)
            let coldObjectReadback = try await requireObject(current, receipt: objectRetry, name: name)
            let coldBlockReadback = try await requireBlock(current, receipt: blockRetry, text: text, style: style)
            observations.append(observation("object-reconciled-after-reopen", objectRetry, on: current,
                readback: coldObjectReadback))
            observations.append(observation("block-reconciled-after-reopen", blockRetry, on: current,
                readback: coldBlockReadback))

            do {
                _ = try await oldMigration.commit(root, authorize: { try await oldLease.validate() })
                XCTFail("A retained revoked application lease authorized a migration retry.")
            } catch {
                XCTAssertEqual(error as? AnyHostError, .sessionClosed)
            }
            do {
                _ = try await oldOwner.perform { _ in true }
                XCTFail("The revoked application owner accepted new work.")
            } catch {
                XCTAssertEqual(error as? AnyHostError, .sessionClosed)
            }
            let finalStatus = try await status(blockIntent, on: current)
            XCTAssertEqual(finalStatus, blockDone)
            let finalRows = try await blocks(current, objectID: objectID)
            XCTAssertEqual(finalRows.count, 1)
            XCTAssertEqual(Set(generations).count, 6)
            observations.append(.object(["phase": .string("revoked-owner-refused"),
                "error": .string("AnyHostError.sessionClosed"),
                "authorityScope": .string("application-owner-lifetime; native ACL mutation not exercised")]))

            await current.owner.revokeAndDrain()
            _ = try await current.client.requestJSON(method: "DELETE", path: ["v1", "spaces", id])
            spaceID = nil
            _ = try await runtime.executeControl(.signOut, expectedGeneration: current.boot.generation)
            await runtime.stop(expectedGeneration: current.boot.generation)
            try FileManager.default.removeItem(at: directory)
            completed = true
        } catch {
            await mounted?.owner.revokeAndDrain()
            if let accountID, let spaceID, let boot = await runtime.currentSession(),
               let client = try? boot.dataClient(expectedAccountID: accountID) {
                _ = try? await client.requestJSON(method: "DELETE", path: ["v1", "spaces", spaceID])
            }
            await runtime.stop()
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    private func authenticate(_ runtime: AnyEmbeddedRuntime, boot: AnyEmbeddedSession,
                              mnemonic: String? = nil) async throws -> (accountID: String, mnemonic: String) {
        let fields: AnyJSON = mnemonic.map { .object(["mnemonic": .string($0), "index": .integer(1)]) }
            ?? .object([:])
        let bytes = try await runtime.executeControl(.authenticate,
            jsonBody: JSONEncoder().encode(fields), expectedGeneration: boot.generation)
        let value = try JSONDecoder().decode(AnyJSON.self, from: bytes)
        let accountID = try XCTUnwrap(value["accountId"]?.string)
        let secret = try XCTUnwrap(mnemonic ?? value["mnemonic"]?.string)
        XCTAssertFalse(secret.isEmpty)
        // Neither the response, recovery phrase nor managed token is attached.
        return (accountID, secret)
    }

    private func mount(_ boot: AnyEmbeddedSession, workspace: AnyTorahWorkspace) async throws -> Mounted {
        let client = try boot.dataClient(expectedAccountID: workspace.accountID)
        let owner = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        do {
            let migration = try await owner.perform { lease in
                try await AnyNativePreparedMigration.open(client: client, workspace: workspace,
                    authorize: { try await lease.validate() })
            }
            XCTAssertTrue(client.hasManagedAuthorization)
            return .init(boot: boot, client: client, owner: owner, migration: migration)
        } catch {
            await owner.revokeAndDrain()
            throw error
        }
    }

    private func reopen(_ old: Mounted, runtime: AnyEmbeddedRuntime, directory: URL,
                        mnemonic: String) async throws -> Mounted {
        await old.owner.revokeAndDrain()
        await runtime.stop(expectedGeneration: old.boot.generation)
        let boot = try await runtime.start(dataDirectory: directory, network: .official, build: .linked)
        let auth = try await authenticate(runtime, boot: boot, mnemonic: mnemonic)
        XCTAssertEqual(auth.accountID, old.owner.workspace.accountID)
        XCTAssertNotEqual(boot.generation, old.boot.generation)
        let value = try await mount(boot, workspace: old.owner.workspace)
        XCTAssertNotEqual(value.owner.generation, old.owner.generation)
        XCTAssertEqual(value.migration.capabilities, old.migration.capabilities)
        return value
    }

    private func prepare(_ intent: AnyPreparedMigrationIntent, on value: Mounted) async throws -> AnyPreparedMigrationReceipt {
        try await value.owner.perform { lease in
            try await value.migration.prepare(intent, authorize: { try await lease.validate() })
        }
    }

    private func status(_ intent: AnyPreparedMigrationIntent, on value: Mounted) async throws -> AnyPreparedMigrationReceipt {
        try await value.owner.perform { lease in
            try await value.migration.status(intent, authorize: { try await lease.validate() })
        }
    }

    private func commit(_ receipt: AnyPreparedMigrationReceipt, on value: Mounted) async throws -> AnyPreparedMigrationReceipt {
        try await value.owner.perform { lease in
            try await value.migration.commit(receipt, authorize: { try await lease.validate() })
        }
    }

    private func advanceOneNativeStage(_ receipt: AnyPreparedMigrationReceipt,
                                       on value: Mounted) async throws -> AnyPreparedMigrationReceipt {
        let intent = receipt.intent
        let reply = try await request(value, method: "POST", suffix:
            ["pinkha", "migration", "intents", intent.intentID, "commit"], body: .object([
                "contract": .string(AnyNativePreparedMigration.contract),
                "storeId": .string(intent.binding.storeID), "planId": .string(intent.binding.planID),
                "planSHA256": .string(intent.binding.planSHA256), "fingerprint": .string(receipt.fingerprint)]))
        let typed = try await status(intent, on: value)
        XCTAssertEqual(reply["stage"]?.string, typed.stage.rawValue)
        XCTAssertEqual(reply["outcome"]?.string, typed.outcome.rawValue)
        XCTAssertEqual(reply["fingerprint"]?.string, typed.fingerprint)
        XCTAssertEqual(reply["objectId"]?.string, typed.objectID)
        XCTAssertEqual(reply["changeId"]?.string, typed.changeID)
        XCTAssertEqual(reply["specSHA256"]?.string, intent.specSHA256)
        return typed
    }

    private func request(_ value: Mounted, method: String, suffix: [String], body: AnyJSON? = nil,
                         query: [String: String] = [:]) async throws -> AnyJSON {
        try await value.owner.perform { lease in
            try await value.client.requestJSON(method: method,
                path: ["v1", "spaces", value.owner.workspace.spaceID] + suffix,
                body: body, query: query, maximumResponseBytes: 131_072,
                authorize: { try await lease.validate() })
        }
    }

    private func blocks(_ value: Mounted, objectID: String) async throws -> [AnyJSON] {
        let result = try await request(value, method: "POST", suffix: ["query"], body: .object([
            "objectId": .string(objectID), "dataset": .string("editor_blocks"),
            "sort": .array([.string("nav.pos"), .string("id")]),
            "limit": .integer(2), "includeTotal": .bool(true)]))
        let rows = try XCTUnwrap(result["records"]?.array)
        XCTAssertEqual(result["hasNext"]?.bool, false)
        XCTAssertEqual(result["total"]?.integer, Int64(rows.count))
        return rows
    }

    private func requireObject(_ value: Mounted, receipt: AnyPreparedMigrationReceipt, name: String) async throws -> AnyJSON {
        let objectID = try XCTUnwrap(receipt.objectID)
        let result = try await request(value, method: "GET", suffix: ["properties", objectID])
        let row = try XCTUnwrap(result["record"])
        XCTAssertEqual(row["any"]?["type"]?.string, "page")
        XCTAssertEqual(Data(try XCTUnwrap(row["any"]?["name"]?.string).utf8), Data(name.utf8))
        let historical = try await historicalRecord(value, receipt: receipt,
            dataset: "objects", recordID: objectID)
        XCTAssertEqual(historical["any"]?["type"]?.string, "page")
        XCTAssertEqual(Data(try XCTUnwrap(historical["any"]?["name"]?.string).utf8), Data(name.utf8))
        let provenance = try await requireProvenance(value, receipt: receipt, dataset: "objects", recordID: objectID)
        return .object(["dataset": .string("objects"), "recordId": .string(objectID),
            "currentNameUTF8SHA256": .string(AnyContentDigest.sha256(Data(try XCTUnwrap(row["any"]?["name"]?.string).utf8))),
            "historicalNameUTF8SHA256": .string(AnyContentDigest.sha256(Data(try XCTUnwrap(historical["any"]?["name"]?.string).utf8))),
            "nativeHistoryEntry": provenance])
    }

    private func requireBlock(_ value: Mounted, receipt: AnyPreparedMigrationReceipt,
                              text: String, style: AnyJSON) async throws -> AnyJSON {
        let objectID = try XCTUnwrap(receipt.objectID)
        let blockID = try XCTUnwrap(receipt.recordIDs.first)
        let rows = try await blocks(value, objectID: objectID)
        XCTAssertEqual(rows.count, 1, "Retry must not create a second native block.")
        let row = try XCTUnwrap(rows.first)
        let historical = try await historicalRecord(value, receipt: receipt,
            dataset: "editor_blocks", recordID: blockID)
        for record in [row, historical] {
            XCTAssertEqual(record["id"]?.string, blockID)
            XCTAssertEqual(record["type"]?.string, "heading")
            XCTAssertEqual(Data(try XCTUnwrap(record["text"]?.string).utf8), Data(text.utf8))
            XCTAssertEqual(record["style"], style)
            XCTAssertEqual(record["nav"]?["parentId"]?.string, "")
            XCTAssertEqual(record["nav"]?["pos"]?.string, "m")
        }
        let provenance = try await requireProvenance(value, receipt: receipt, dataset: "editor_blocks", recordID: blockID)
        return .object(["dataset": .string("editor_blocks"), "recordId": .string(blockID),
            "currentBodyUTF8SHA256": .string(AnyContentDigest.sha256(Data(try XCTUnwrap(row["text"]?.string).utf8))),
            "historicalBodyUTF8SHA256": .string(AnyContentDigest.sha256(Data(try XCTUnwrap(historical["text"]?.string).utf8))),
            "currentRecordCount": .integer(Int64(rows.count)), "nativeHistoryEntry": provenance])
    }

    private func historicalRecord(_ value: Mounted, receipt: AnyPreparedMigrationReceipt,
                                  dataset: String, recordID: String) async throws -> AnyJSON {
        let objectID = try XCTUnwrap(receipt.objectID)
        let changeID = try XCTUnwrap(receipt.changeID)
        let result = try await request(value, method: "GET", suffix: ["objects", objectID,
            "history", changeID, "datasets", dataset, "records", recordID])
        XCTAssertEqual(result["version"]?.string, changeID)
        XCTAssertEqual(result["dataset"]?.string, dataset)
        XCTAssertEqual(result["recordId"]?.string, recordID)
        XCTAssertEqual(result["exists"]?.bool, true)
        if let deleted = result["deleted"] { XCTAssertEqual(deleted.bool, false) }
        return try XCTUnwrap(result["record"])
    }

    private func requireProvenance(_ value: Mounted, receipt: AnyPreparedMigrationReceipt,
                                   dataset: String, recordID: String) async throws -> AnyJSON {
        let objectID = try XCTUnwrap(receipt.objectID)
        let changeID = try XCTUnwrap(receipt.changeID)
        let result = try await request(value, method: "GET", suffix: ["objects", objectID, "history"],
            query: ["dataset": dataset, "recordId": recordID, "limit": "200", "coalesce": "false"])
        if let cursor = result["cursor"] { XCTAssertEqual(cursor.string, "") }
        let changes = try XCTUnwrap(result["changes"]?.array)
        let original = changes.filter { $0["version"]?.string == changeID }
        XCTAssertEqual(original.count, 1, "The exact prepared native change must appear once in history.")
        let change = try XCTUnwrap(original.first)
        XCTAssertEqual(change["author"]?.string, value.owner.workspace.accountID)
        let touched = try XCTUnwrap(change["touched"]?.array)
        XCTAssertTrue(touched.contains { $0["dataset"]?.string == dataset && $0["recordId"]?.string == recordID })
        return change
    }

    private func requireIdentity(_ value: AnyPreparedMigrationReceipt, original: AnyPreparedMigrationReceipt) {
        XCTAssertEqual(value.intent, original.intent)
        XCTAssertEqual(value.fingerprint, original.fingerprint)
        XCTAssertEqual(value.objectID, original.objectID)
    }

    private func observation(_ phase: String, _ receipt: AnyPreparedMigrationReceipt, on value: Mounted,
                             readback: AnyJSON? = nil) -> AnyJSON {
        .object(["phase": .string(phase), "runtimeVersion": .string(value.boot.engineVersion),
            "engineGeneration": .string(value.boot.generation.uuidString),
            "ownerGeneration": .string(value.owner.generation.uuidString),
            "contract": .string(AnyNativePreparedMigration.contract),
            "intentId": .string(receipt.intent.intentID), "fingerprint": .string(receipt.fingerprint),
            "specSHA256": .string(receipt.intent.specSHA256), "stage": .string(receipt.stage.rawValue),
            "outcome": .string(receipt.outcome.rawValue), "objectId": receipt.objectID.map(AnyJSON.string) ?? .null,
            "changeId": receipt.changeID.map(AnyJSON.string) ?? .null,
            "recordIds": .array(receipt.recordIDs.map(AnyJSON.string)),
            "accountId": .string(value.owner.workspace.accountID), "spaceId": .string(value.owner.workspace.spaceID),
            "storeId": .string(receipt.intent.binding.storeID),
            "planId": .string(receipt.intent.binding.planID), "planSHA256": .string(receipt.intent.binding.planSHA256),
            "readback": readback ?? .null])
    }

    private func attachProof(_ observations: [AnyJSON], generations: [String], completed: Bool,
                             name: String, text: String) {
        let proof: AnyJSON = .object([
            "status": .string("OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED"),
            "completedCleanup": .bool(completed), "processId": .integer(Int64(ProcessInfo.processInfo.processIdentifier)),
            "runtimeGenerations": .array(generations.map(AnyJSON.string)), "observations": .array(observations),
            "nameUTF8SHA256": .string(AnyContentDigest.sha256(Data(name.utf8))),
            "bodyUTF8SHA256": .string(AnyContentDigest.sha256(Data(text.utf8))),
            "restartKind": .string("orderly native SDK/store reopen within one XCTest OS process"),
            "osProcessCrash": .string("NOT_RUN"), "lostHTTPAcknowledgement": .string("NOT_INJECTED"),
            "networkSynchronization": .string("NOT_RUN"), "nativeACLMutation": .string("NOT_RUN"),
            "inlineFiles": .string("NOT_RUN_NO_HTTP_ROUTE"), "fullSpaceMigration": .string("NOT_PROVEN")])
        do {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            let bytes = try encoder.encode(proof)
            guard bytes.count <= 32_768 else { XCTFail("Prepared migration proof exceeded its bound."); return }
            let attachment = XCTAttachment(data: bytes, uniformTypeIdentifier: "public.json")
            attachment.name = "pinkha-prepared-migration-runtime-proof.json"
            attachment.lifetime = .keepAlways
            add(attachment)
        } catch { XCTFail("Prepared migration proof could not be encoded.") }
    }
}
#endif
