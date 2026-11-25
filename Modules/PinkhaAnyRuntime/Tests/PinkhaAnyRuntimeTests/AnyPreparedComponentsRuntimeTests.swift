#if PINKHA_PREPARED_COMPONENTS_ACCEPTANCE
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
@testable import PinkhaAnyRuntime

/// One managed C-runtime/public-client full-file journey. The attachment is
/// observations only; an original passing XCTest and build lineage are required.
@MainActor
final class AnyPreparedComponentsRuntimeTests: XCTestCase {
    private struct Mounted: Sendable {
        let boot: AnyEmbeddedSession
        let client: AnyHTTPClient
        let owner: AnyApplicationSession
        let objects: AnyNativePreparedMigration
        let files: AnyNativePreparedFileMigration
        let definitions: AnyNativePreparedDefinitionMigration
    }

    private struct DefinitionPlan: Sendable {
        let label: String
        let intent: AnyPreparedDefinitionIntent
        let prepared: AnyPreparedDefinitionReceipt
        let completed: AnyPreparedDefinitionReceipt
    }

    private struct Schema: Sendable {
        let plans: [DefinitionPlan]
        let typeID: String
        let collectionID: String
        let typePropertyID: String
        let collectionPropertyID: String
        let part: AnyPreparedDefinitionReceipt
    }

    private struct DocumentPlan: Sendable {
        let label: String
        let object: AnyPreparedMigrationReceipt
        let blockPrepared: AnyPreparedMigrationReceipt
        let block: AnyPreparedMigrationReceipt
        let typeValue: String
        let collectionValue: String
        let text: String
    }

    private struct Input: Sendable {
        let label: String
        let content: Data
        let name: String
        let mime: String
    }

    private struct Context: Sendable {
        let sourceSHA: String
        let executionID: String
        let nonce: String

        static func read() throws -> Self {
            let environment = ProcessInfo.processInfo.environment
            let prefix = "PINKHA_PREPARED_COMPONENTS_APPLE_"
            let source = environment[prefix + "SOURCE_SHA"] ?? ""
            let execution = environment[prefix + "EXECUTION_UUID"] ?? ""
            let nonce = environment[prefix + "NONCE"] ?? ""
            func lowercaseHex(_ value: String, count: Int) -> Bool {
                value.utf8.count == count && value.utf8.allSatisfy {
                    (48...57).contains($0) || (97...102).contains($0)
                }
            }
            try componentsRequire(lowercaseHex(source, count: 40) && lowercaseHex(nonce, count: 32) &&
                UUID(uuidString: execution) != nil,
                "Exact source, real local execution UUID and owned nonce are required.")
            return .init(sourceSHA: source, executionID: execution, nonce: nonce)
        }
    }

    func testManagedDefinitionsBlocksAndFullFilesSurviveReopen() async throws {
        executionTimeAllowance = 900
        let context = try Context.read()
        try componentsRequire(AnyEmbeddedBuild.linked == .pinkhaPreparedComponentsCandidateV1,
                          "The separate full-file runtime candidate is required.")
        let runtime = AnyEmbeddedRuntime.shared
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(
            "pinkha-prepared-components-" + context.nonce, isDirectory: true)
        try componentsRequire(!FileManager.default.fileExists(atPath: directory.path),
                          "A fresh owned native data directory is required.")
        let inputs: [Input] = [
            .init(label: "minimum", content: Data((0..<4096).map { UInt8($0 % 256) }),
                  name: "minimum.bin", mime: "application/octet-stream"),
            .init(label: "two-mib", content: Data((0..<(2 << 20)).map { UInt8($0 % 251) }),
                  name: "קובץ e\u{301} 🧪.bin", mime: "application/octet-stream")
        ]
        var mounted: Mounted?
        var accountID: String?
        var spaceID: String?
        var identity: [String: AnyJSON] = [:]
        var capabilities: [String: AnyJSON] = [:]
        var fileProofs: [[String: AnyJSON]] = []
        var definitionProofs: [[String: AnyJSON]] = []
        var documentProofs: [[String: AnyJSON]] = []
        var schemaReads: [AnyJSON] = []
        var runtimeVersions: [String] = []
        var runtimeGenerations: [String] = []
        var ownerGenerations: [String] = []
        var journeyComplete = false
        var completedCleanup = false
        defer {
            attachProof(context, identity: identity, capabilities: capabilities, files: fileProofs,
                definitions: definitionProofs, documents: documentProofs, schemaReads: schemaReads,
                runtimeVersions: runtimeVersions, runtimeGenerations: runtimeGenerations,
                ownerGenerations: ownerGenerations, journeyComplete: journeyComplete,
                completedCleanup: completedCleanup)
        }
        do {
            let boot = try await runtime.start(dataDirectory: directory, network: .official, build: .linked)
            try requireVersion(boot)
            let auth = try await authenticate(runtime, boot: boot)
            accountID = auth.accountID
            let client = try boot.dataClient(expectedAccountID: auth.accountID)
            try componentsRequire(client.hasManagedAuthorization, "Actual managed data authorization is required.")
            let space = try await client.requestJSON(method: "POST", path: ["v1", "spaces"],
                body: .object(["name": .string("Disposable full-file Apple acceptance")]))
            let id = try XCTUnwrap(space["id"]?.string)
            spaceID = id
            let workspace = try AnyTorahWorkspace(accountID: auth.accountID, spaceID: id)
            var current = try await mount(boot, workspace: workspace)
            mounted = current
            runtimeVersions.append(current.boot.engineVersion)
            runtimeGenerations.append(current.boot.generation.uuidString)
            ownerGenerations.append(current.owner.generation.uuidString)
            let binding = try AnyPreparedMigrationPlanBinding(workspace: workspace,
                storeID: current.files.capabilities.storeID,
                planID: AnyContentDigest.sha256(Data(("apple-native-components-plan|" + context.nonce).utf8)),
                planSHA256: AnyContentDigest.sha256(Data("definitions+parts+properties+objects+blocks+files:4096+2097152/v1".utf8)))
            let schema = try await createDefinitions(binding: binding, nonce: context.nonce, on: current)
            for plan in schema.plans {
                definitionProofs.append([
                    "label": .string(plan.label), "kind": .string(plan.intent.kind.rawValue),
                    "sourceKey": .string(plan.intent.sourceKey), "intentId": .string(plan.intent.intentID),
                    "specBase64": .string(plan.intent.specBytes.base64EncodedString()),
                    "specSHA256": .string(plan.intent.specSHA256),
                    "prepared": definitionObservation(plan.prepared, on: current),
                    "committed": definitionObservation(plan.completed, on: current)
                ])
            }
            schemaReads.append(try await readSchema(schema, nonce: context.nonce, on: current))
            // The document and block are complete before a pending file freezes
            // its actual native owner head. Each pending file has a distinct owner.
            var ownerIDs: [String] = []
            var documents: [DocumentPlan] = []
            for input in inputs {
                let document = try await createDocument(binding: binding, label: input.label,
                    nonce: context.nonce, schema: schema, on: current)
                documents.append(document)
                let ownerID = try XCTUnwrap(document.object.objectID)
                ownerIDs.append(ownerID)
                documentProofs.append([
                    "label": .string(input.label), "ownerObjectId": .string(ownerID),
                    "objectIntent": migrationIntentObservation(document.object.intent),
                    "blockIntent": migrationIntentObservation(document.block.intent),
                    "objectCommitted": migrationObservation(document.object, on: current),
                    "blockPrepared": migrationObservation(document.blockPrepared, on: current),
                    "blockCommitted": migrationObservation(document.block, on: current),
                    "expectedTypeValueUTF8Base64": .string(Data(document.typeValue.utf8).base64EncodedString()),
                    "expectedCollectionValueUTF8Base64": .string(Data(document.collectionValue.utf8).base64EncodedString()),
                    "expectedBlockTextUTF8Base64": .string(Data(document.text.utf8).base64EncodedString()),
                    "currentRead": try await readDocument(document, schema: schema, on: current)
                ])
            }
            try componentsRequire(ownerIDs.count == 2 && Set(ownerIDs).count == 2,
                              "Each pending file requires its own actual native owner.")
            identity = [
                "accountId": .string(auth.accountID), "spaceId": .string(id),
                "storeId": .string(binding.storeID), "ownerObjectIds": .array(ownerIDs.map(AnyJSON.string)),
                "planId": .string(binding.planID), "planSHA256": .string(binding.planSHA256)
            ]
            capabilities = [
                "contract": .string(AnyNativePreparedFileMigration.contract),
                "maximumBytes": .integer(current.files.capabilities.maximumBytes),
                "networkVerified": .bool(current.files.capabilities.networkVerified),
                "definitionsContract": .string(AnyNativePreparedDefinitionMigration.contract),
                "supportsParts": .bool(current.definitions.capabilities.supportsParts),
                "maximumDefinitionRecordIDs": .integer(Int64(AnyPreparedDefinitionReceipt.maximumRecordIDs))
            ]
            var plans: [(input: Input, intent: AnyPreparedFileIntent,
                         prepared: AnyPreparedFileReceipt)] = []
            for (index, input) in inputs.enumerated() {
                let ownerID = ownerIDs[index]
                let intent = try AnyPreparedFileIntent(binding: binding,
                    sourceKey: "apple-full-file-" + input.label + "-" + context.nonce,
                    ownerObjectID: ownerID, name: input.name, mime: input.mime, size: Int64(input.content.count),
                    contentSHA256: AnyContentDigest.sha256(input.content))
                let fileURL = directory.appendingPathComponent("source-" + input.label + ".bin")
                try input.content.write(to: fileURL, options: .atomic)
                let prepared = try await prepare(intent, fileURL: fileURL, on: current)
                try componentsRequire(prepared.stage == .filePrepared && prepared.outcome == .prepared,
                                  "A fresh file must begin at its noncommitted native stage.")
                try componentsRequire(prepared.objectID != ownerID && prepared.recordIDs == [prepared.fileID],
                                  "Payload root, owning object and file record identities were conflated.")
                plans.append((input, intent, prepared))
                fileProofs.append([
                    "label": .string(input.label), "sourceKey": .string(intent.sourceKey),
                    "intentId": .string(intent.intentID), "ownerObjectId": .string(ownerID),
                    "specBase64": .string(intent.specBytes.base64EncodedString()),
                    "specSHA256": .string(intent.specSHA256), "expectedSize": .integer(Int64(input.content.count)),
                    "expectedContentSHA256": .string(AnyContentDigest.sha256(input.content)),
                    "nameUTF8Base64": .string(Data(input.name.utf8).base64EncodedString()),
                    "mime": .string(input.mime), "prepared": receiptObservation(prepared, on: current)
                ])
            }
            try componentsRequire(Set(plans.map { $0.prepared.fileID }).count == 2 &&
                Set(plans.map { $0.intent.intentID }).count == 2, "The two native file cases must remain distinct.")

            current = try await reopen(current, runtime: runtime, directory: directory, mnemonic: auth.mnemonic)
            mounted = current
            runtimeVersions.append(current.boot.engineVersion)
            runtimeGenerations.append(current.boot.generation.uuidString)
            ownerGenerations.append(current.owner.generation.uuidString)
            try await reconcileDefinitions(schema, phase: "afterFirstReopen", on: current, into: &definitionProofs)
            try await reconcileDocuments(documents, schema: schema, phase: "afterFirstReopen", on: current, into: &documentProofs)
            schemaReads.append(try await readSchema(schema, nonce: context.nonce, on: current))
            var completedFiles: [AnyPreparedFileReceipt] = []
            for (index, plan) in plans.enumerated() {
                let known = try await prepare(plan.intent, fileURL: directory.appendingPathComponent("absent-source.bin"), on: current)
                try componentsRequire(known == plan.prepared, "Known preparation must reconcile before reading a missing input file.")
                let recovered = try await status(plan.intent, on: current)
                try componentsRequire(recovered == plan.prepared, "Prepared native bytes changed across orderly reopen.")
                fileProofs[index]["afterPreparedReopen"] = receiptObservation(recovered, on: current)
                let completed = try await commit(plan.prepared, on: current)
                try requireIdentity(completed, original: plan.prepared)
                try componentsRequire(completed.isCompleteAndCurrent, "The actual full file did not complete.")
                let currentStatus = try await status(plan.intent, on: current)
                let retry = try await commit(plan.prepared, on: current)
                try componentsRequire(currentStatus == completed && retry == completed,
                                  "Current status or explicit retry changed the committed native file.")
                completedFiles.append(completed)
                fileProofs[index]["committed"] = receiptObservation(completed, on: current)
                fileProofs[index]["currentStatus"] = receiptObservation(currentStatus, on: current)
                fileProofs[index]["retry"] = receiptObservation(retry, on: current)
                fileProofs[index]["currentRead"] = try await readback(current, receipt: completed, input: plan.input)
            }

            current = try await reopen(current, runtime: runtime, directory: directory, mnemonic: auth.mnemonic)
            mounted = current
            runtimeVersions.append(current.boot.engineVersion)
            runtimeGenerations.append(current.boot.generation.uuidString)
            ownerGenerations.append(current.owner.generation.uuidString)
            try await reconcileDefinitions(schema, phase: "afterSecondReopen", on: current, into: &definitionProofs)
            try await reconcileDocuments(documents, schema: schema, phase: "afterSecondReopen", on: current, into: &documentProofs)
            schemaReads.append(try await readSchema(schema, nonce: context.nonce, on: current))
            for (index, plan) in plans.enumerated() {
                let recovered = try await status(plan.intent, on: current)
                let retry = try await commit(plan.prepared, on: current)
                try componentsRequire(recovered == completedFiles[index] && retry == completedFiles[index],
                                  "Completed native identity changed across the second orderly reopen.")
                fileProofs[index]["afterCommittedReopenStatus"] = receiptObservation(recovered, on: current)
                fileProofs[index]["afterCommittedReopenRetry"] = receiptObservation(retry, on: current)
                fileProofs[index]["reopenedRead"] = try await readback(current, receipt: recovered, input: plan.input)
            }
            try componentsRequire(runtimeGenerations.count == 3 && Set(runtimeGenerations).count == 3 &&
                ownerGenerations.count == 3 && Set(ownerGenerations).count == 3,
                "Exactly three distinct runtime and application owner generations are required.")
            journeyComplete = true
            await current.owner.revokeAndDrain()
            _ = try await current.client.requestJSON(method: "DELETE", path: ["v1", "spaces", id])
            spaceID = nil
            _ = try await runtime.executeControl(.signOut, expectedGeneration: current.boot.generation)
            await runtime.stop(expectedGeneration: current.boot.generation)
            let stopped = await runtime.currentSession()
            try componentsRequire(stopped == nil, "The owned native runtime did not stop.")
            try FileManager.default.removeItem(at: directory)
            completedCleanup = true
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

    private func requireVersion(_ boot: AnyEmbeddedSession) throws {
        try componentsRequire(boot.engineVersion.hasPrefix("any v0.5.0-pinkha.prepared.components.1 "),
                          "An exact full-file candidate version token is required.")
    }

    private func authenticate(_ runtime: AnyEmbeddedRuntime, boot: AnyEmbeddedSession,
                              mnemonic: String? = nil) async throws -> (accountID: String, mnemonic: String) {
        let fields: AnyJSON = mnemonic.map { .object(["mnemonic": .string($0), "index": .integer(1)]) }
            ?? .object([:])
        let data = try await runtime.executeControl(.authenticate,
            jsonBody: JSONEncoder().encode(fields), expectedGeneration: boot.generation)
        let value = try JSONDecoder().decode(AnyJSON.self, from: data)
        let account = try XCTUnwrap(value["accountId"]?.string)
        let recovery = try XCTUnwrap(mnemonic ?? value["mnemonic"]?.string)
        try componentsRequire(!account.isEmpty && !recovery.isEmpty, "Actual SDK authentication was incomplete.")
        // Recovery phrase, managed token and raw authentication response stay in memory.
        return (account, recovery)
    }

    private func mount(_ boot: AnyEmbeddedSession, workspace: AnyTorahWorkspace) async throws -> Mounted {
        try requireVersion(boot)
        let client = try boot.dataClient(expectedAccountID: workspace.accountID)
        let owner = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        do {
            let pair = try await owner.perform { lease in
                let objects = try await AnyNativePreparedMigration.open(client: client, workspace: workspace,
                    authorize: { try await lease.validate() })
                let files = try await AnyNativePreparedFileMigration.open(client: client, workspace: workspace,
                    authorize: { try await lease.validate() })
                let definitions = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace,
                    authorize: { try await lease.validate() })
                try await lease.validate()
                return (objects, files, definitions)
            }
            try componentsRequire(client.hasManagedAuthorization &&
                pair.0.capabilities.storeID == pair.1.capabilities.storeID &&
                pair.1.capabilities.maximumBytes == AnyPreparedFileIntent.maximumBytes && !pair.1.capabilities.networkVerified &&
                pair.2.capabilities.storeID == pair.0.capabilities.storeID && pair.2.capabilities.supportsParts &&
                !pair.2.capabilities.networkVerified,
                "Managed native store or explicit full-file capability differs.")
            return .init(boot: boot, client: client, owner: owner, objects: pair.0, files: pair.1, definitions: pair.2)
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
        try requireVersion(boot)
        let auth = try await authenticate(runtime, boot: boot, mnemonic: mnemonic)
        try componentsRequire(auth.accountID == old.owner.workspace.accountID &&
            boot.generation != old.boot.generation, "Native reopen changed the account or reused its runtime generation.")
        let current = try await mount(boot, workspace: old.owner.workspace)
        try componentsRequire(current.owner.generation != old.owner.generation &&
            current.files.capabilities == old.files.capabilities &&
            current.objects.capabilities == old.objects.capabilities &&
            current.definitions.capabilities == old.definitions.capabilities,
            "The reopened owner/store capability changed.")
        return current
    }

    private func createDefinitions(binding: AnyPreparedMigrationPlanBinding, nonce: String,
                                   on value: Mounted) async throws -> Schema {
        let type = try await createDefinition(label: "type", intent: .type(binding: binding,
            sourceKey: "apple-native-definition-type-" + nonce, xKey: "apple-type-" + nonce,
            name: "סוג מסמך מועבר", layout: .object(["type": .string("page")]),
            meta: .object(["migrationFixture": .bool(true)])), on: value)
        let collection = try await createDefinition(label: "collection", intent: .collection(binding: binding,
            sourceKey: "apple-native-definition-collection-" + nonce, xKey: "apple-collection-" + nonce,
            name: "אוסף מועבר"), on: value)
        let draft: AnyJSON = .object([
            "key": .string("content"), "name": .string("תוכן"), "pos": .string("m"),
            "ui": .object(["type": .string("document")]),
            "datasets": .array([
                .object(["module": .string("editor"), "key": .string("editor_blocks")]),
                .object(["module": .string("records"), "key": .string("notes"),
                    "displayName": .string("הערות"),
                    "fields": .array([
                        .object(["key": .string("title"), "name": .string("Title"), "kind": .string("string"),
                                 "required": .bool(true), "mutableBy": .string("any")]),
                        .object(["key": .string("score"), "kind": .string("number"), "mutableBy": .string("any")])
                    ]),
                    "indexes": .array([.object(["key": .string("title_index"), "fields": .array([.string("title")])])])
                ])
            ])
        ])
        let part = try await createDefinition(label: "part", intent: .part(binding: binding,
            sourceKey: "apple-native-definition-part-" + nonce, ownerID: type.completed.objectID,
            draft: draft), on: value)
        try componentsRequire(part.prepared.stage == .partPrepared && part.prepared.recordIDs.count == 6 &&
            part.completed.recordIDs == part.prepared.recordIDs && part.completed.changeID == part.prepared.changeID,
            "The actual part, two dataset heads, two fields and index must keep one original signed batch.")
        let typeProperty = try await createDefinition(label: "type-property", intent: .property(binding: binding,
            sourceKey: "apple-native-definition-type-property-" + nonce, ownerID: type.completed.objectID,
            kind: .string, name: "מקור", xKey: "source_ref"), on: value)
        let collectionProperty = try await createDefinition(label: "collection-property", intent: .property(binding: binding,
            sourceKey: "apple-native-definition-collection-property-" + nonce, ownerID: collection.completed.objectID,
            kind: .string, name: "קבוצה", xKey: "source_group"), on: value)
        return .init(plans: [type, collection, part, typeProperty, collectionProperty],
            typeID: type.completed.objectID, collectionID: collection.completed.objectID,
            typePropertyID: try XCTUnwrap(typeProperty.completed.recordIDs.first),
            collectionPropertyID: try XCTUnwrap(collectionProperty.completed.recordIDs.first), part: part.completed)
    }

    private func createDefinition(label: String, intent: AnyPreparedDefinitionIntent,
                                  on value: Mounted) async throws -> DefinitionPlan {
        let prepared = try await value.owner.perform { lease in
            let result = try await value.definitions.prepare(intent, authorize: { try await lease.validate() })
            try await lease.validate()
            return result
        }
        try componentsRequire(prepared.outcome == .prepared, "A new definition must reserve before append.")
        let completed = try await value.owner.perform { lease in
            let result = try await value.definitions.commit(prepared, authorize: { try await lease.validate() })
            try await lease.validate()
            return result
        }
        try componentsRequire(completed.isCompleteAndCurrent && prepared.objectID == completed.objectID &&
            prepared.fingerprint == completed.fingerprint, "The actual native definition did not complete with its original identity.")
        return .init(label: label, intent: intent, prepared: prepared, completed: completed)
    }

    private func reconcileDefinitions(_ schema: Schema, phase: String, on value: Mounted,
                                      into observations: inout [[String: AnyJSON]]) async throws {
        for (index, plan) in schema.plans.enumerated() {
            let pair = try await value.owner.perform { lease in
                let status = try await value.definitions.status(plan.intent, authorize: { try await lease.validate() })
                let retry = try await value.definitions.commit(plan.prepared, authorize: { try await lease.validate() })
                try await lease.validate()
                return (status, retry)
            }
            try componentsRequire(pair.0 == plan.completed && pair.1 == plan.completed,
                "A reopened definition must retain every original record ID and signed change.")
            observations[index][phase + "Status"] = definitionObservation(pair.0, on: value)
            observations[index][phase + "Retry"] = definitionObservation(pair.1, on: value)
        }
    }

    private func definitionObservation(_ receipt: AnyPreparedDefinitionReceipt, on value: Mounted) -> AnyJSON {
        .object([
            "runtimeGeneration": .string(value.boot.generation.uuidString),
            "ownerGeneration": .string(value.owner.generation.uuidString),
            "stage": .string(receipt.stage.rawValue), "outcome": .string(receipt.outcome.rawValue),
            "fingerprint": .string(receipt.fingerprint), "objectId": .string(receipt.objectID),
            "changeId": .string(receipt.changeID), "recordIds": .array(receipt.recordIDs.map(AnyJSON.string))
        ])
    }

    private func readSchema(_ schema: Schema, nonce: String, on value: Mounted) async throws -> AnyJSON {
        let type = try await request(value, suffix: ["types", schema.typeID])
        let collection = try await request(value, suffix: ["collections", schema.collectionID])
        let typeProperties = try await request(value, suffix: ["types", schema.typeID, "properties"])
        let collectionProperties = try await request(value, suffix: ["collections", schema.collectionID, "properties"])
        let partResult = try await request(value, suffix: ["types", schema.typeID, "parts"])
        try componentsRequire(type["id"]?.string == schema.typeID && type["xKey"]?.string == "apple-type-" + nonce &&
            type["name"]?.string == "סוג מסמך מועבר" && type["builtIn"]?.bool != true &&
            collection["id"]?.string == schema.collectionID && collection["xKey"]?.string == "apple-collection-" + nonce &&
            collection["name"]?.string == "אוסף מועבר" && collection["builtIn"]?.bool != true,
            "Ordinary native type/collection reads differ from the actual custom definitions.")
        let typeProperty = try XCTUnwrap(typeProperties["properties"]?.array?.first { $0["id"]?.string == schema.typePropertyID })
        let collectionProperty = try XCTUnwrap(collectionProperties["properties"]?.array?.first { $0["id"]?.string == schema.collectionPropertyID })
        try componentsRequire(typeProperty["kind"]?.string == "string" && typeProperty["xKey"]?.string == "source_ref" &&
            collectionProperty["kind"]?.string == "string" && collectionProperty["xKey"]?.string == "source_group",
            "Ordinary native custom property identity/kind differs.")
        let parts = try XCTUnwrap(partResult["parts"]?.array)
        try componentsRequire(parts.count == 1, "The migrated type must contain exactly one actual native part.")
        let part = parts[0]
        let datasets = try XCTUnwrap(part["datasets"]?.array)
        try componentsRequire(part["id"]?.string == schema.part.recordIDs[0] && part["key"]?.string == "content" &&
            part["name"]?.string == "תוכן" && part["ui"]?["type"]?.string == "document" && datasets.count == 2,
            "Ordinary compiled part shape differs from its original atomic declaration.")
        let editor = try XCTUnwrap(datasets.first { $0["key"]?.string == "editor_blocks" })
        let notes = try XCTUnwrap(datasets.first { $0["key"]?.string == "notes" })
        let fields = try XCTUnwrap(notes["fields"]?.array)
        let indexes = try XCTUnwrap(notes["indexes"]?.array)
        let title = try XCTUnwrap(fields.first { $0["key"]?.string == "title" })
        let score = try XCTUnwrap(fields.first { $0["key"]?.string == "score" })
        let index = try XCTUnwrap(indexes.first { $0["key"]?.string == "title_index" })
        let notesCollection = try XCTUnwrap(notes["collection"]?.string)
        try componentsRequire(editor["id"]?.string == schema.part.recordIDs[1] && editor["collection"]?.string == "editor_blocks" &&
            editor["module"]?.string == "editor" && editor["invalid"]?.bool != true &&
            notes["id"]?.string == schema.part.recordIDs[2] && notes["module"]?.string == "records" &&
            notes["invalid"]?.bool != true && !notesCollection.isEmpty && fields.count == 2 && indexes.count == 1 &&
            title["id"]?.string == schema.part.recordIDs[3] && title["kind"]?.string == "string" && title["required"]?.bool == true &&
            score["id"]?.string == schema.part.recordIDs[4] && score["kind"]?.string == "number" &&
            index["id"]?.string == schema.part.recordIDs[5] && index["invalid"]?.bool != true &&
            index["fields"]?.array == [.string("title")],
            "Compiled native datasets/fields/indexes lost their original ordered identities or declarations.")
        return .object([
            "runtimeGeneration": .string(value.boot.generation.uuidString), "ownerGeneration": .string(value.owner.generation.uuidString),
            "typeId": type["id"]!, "typeXKey": type["xKey"]!, "typeName": type["name"]!,
            "collectionId": collection["id"]!, "collectionXKey": collection["xKey"]!, "collectionName": collection["name"]!,
            "typePropertyId": typeProperty["id"]!, "typePropertyKind": typeProperty["kind"]!, "typePropertyXKey": typeProperty["xKey"]!,
            "collectionPropertyId": collectionProperty["id"]!, "collectionPropertyKind": collectionProperty["kind"]!,
            "collectionPropertyXKey": collectionProperty["xKey"]!,
            "partId": part["id"]!, "partKey": part["key"]!, "partName": part["name"]!,
            "editorDatasetId": editor["id"]!, "notesDatasetId": notes["id"]!, "notesCollection": .string(notesCollection),
            "titleFieldId": title["id"]!, "scoreFieldId": score["id"]!, "titleIndexId": index["id"]!
        ])
    }

    private func createDocument(binding: AnyPreparedMigrationPlanBinding, label: String, nonce: String,
                                schema: Schema, on value: Mounted) async throws -> DocumentPlan {
        let typeValue = "מקור e\u{301} " + label
        let collectionValue = "קבוצה " + label
        let text = "שלום e\u{301} 🧪 — migrated custom type " + label
        let intent = try AnyPreparedMigrationIntent.object(binding: binding,
            sourceKey: "apple-native-document-" + label + "-" + nonce,
            typeID: schema.typeID, collections: [schema.collectionID],
            initialProperties: .object([
                "any": .object(["name": .string("Migrated document " + label)]),
                schema.typeID: .object([schema.typePropertyID: .string(typeValue)]),
                schema.collectionID: .object([schema.collectionPropertyID: .string(collectionValue)])
            ]))
        let completed = try await value.owner.perform { lease in
            let prepared = try await value.objects.prepare(intent, authorize: { try await lease.validate() })
            let result = try await value.objects.commit(prepared, authorize: { try await lease.validate() })
            try await lease.validate()
            return result
        }
        try componentsRequire(completed.isCompleteAndCurrent, "The actual custom-type document did not complete.")
        let ownerID = try XCTUnwrap(completed.objectID)
        let blockIntent = try AnyPreparedMigrationIntent.block(binding: binding,
            sourceKey: "apple-native-block-" + label + "-" + nonce, objectID: ownerID,
            type: "paragraph", text: text, position: "m")
        let pair = try await value.owner.perform { lease in
            let prepared = try await value.objects.prepare(blockIntent, authorize: { try await lease.validate() })
            let committed = try await value.objects.commit(prepared, authorize: { try await lease.validate() })
            try await lease.validate()
            return (prepared, committed)
        }
        try componentsRequire(pair.0.stage == .blockPrepared && pair.1.isCompleteAndCurrent &&
            pair.0.recordIDs == pair.1.recordIDs && pair.0.changeID == pair.1.changeID && pair.1.recordIDs.count == 1,
            "The actual migrated document block did not retain its signed reservation.")
        return .init(label: label, object: completed, blockPrepared: pair.0, block: pair.1,
                     typeValue: typeValue, collectionValue: collectionValue, text: text)
    }

    private func reconcileDocuments(_ plans: [DocumentPlan], schema: Schema, phase: String, on value: Mounted,
                                    into observations: inout [[String: AnyJSON]]) async throws {
        for (index, plan) in plans.enumerated() {
            for (label, original) in [("Object", plan.object), ("Block", plan.block)] {
                let pair = try await value.owner.perform { lease in
                    let status = try await value.objects.status(original.intent, authorize: { try await lease.validate() })
                    let retry = try await value.objects.commit(original, authorize: { try await lease.validate() })
                    try await lease.validate()
                    return (status, retry)
                }
                try componentsRequire(pair.0 == original && pair.1 == original,
                    "A reopened native document or editor block changed its original identity.")
                observations[index][phase + label + "Status"] = migrationObservation(pair.0, on: value)
                observations[index][phase + label + "Retry"] = migrationObservation(pair.1, on: value)
            }
            observations[index][phase + "Read"] = try await readDocument(plan, schema: schema, on: value)
        }
    }

    private func readDocument(_ plan: DocumentPlan, schema: Schema, on value: Mounted) async throws -> AnyJSON {
        let ownerID = try XCTUnwrap(plan.object.objectID)
        let object = try await request(value, suffix: ["objects", ownerID])
        let record = try XCTUnwrap(object["record"])
        let typeValue = try XCTUnwrap(record[schema.typeID]?[schema.typePropertyID]?.string)
        let collectionValue = try XCTUnwrap(record[schema.collectionID]?[schema.collectionPropertyID]?.string)
        try componentsRequire(object["objectId"]?.string == ownerID && Data(typeValue.utf8) == Data(plan.typeValue.utf8) &&
            Data(collectionValue.utf8) == Data(plan.collectionValue.utf8),
            "Ordinary native document read lost its migrated type/collection property bytes.")
        let response = try await value.owner.perform { lease in
            let result = try await value.client.requestJSON(method: "POST",
                path: ["v1", "spaces", value.owner.workspace.spaceID, "query"],
                body: .object(["objectId": .string(ownerID), "dataset": .string("editor_blocks"),
                    "sort": .array([.string("nav.pos"), .string("id")]), "limit": .integer(2), "includeTotal": .bool(true)]),
                maximumResponseBytes: 65_536, authorize: { try await lease.validate() })
            try await lease.validate()
            return result
        }
        let rows = try XCTUnwrap(response["records"]?.array)
        try componentsRequire(rows.count == 1 && response["total"]?.integer == 1 && response["hasNext"]?.bool == false,
            "The migrated custom type must contain exactly its one native editor block.")
        let row = rows[0]
        let text = try XCTUnwrap(row["text"]?.string)
        try componentsRequire(row["id"]?.string == plan.block.recordIDs[0] && row["type"]?.string == "paragraph" &&
            Data(text.utf8) == Data(plan.text.utf8) && row["nav"]?["parentId"]?.string == "" && row["nav"]?["pos"]?.string == "m",
            "Ordinary native block read changed its exact text or hierarchy.")
        return .object([
            "runtimeGeneration": .string(value.boot.generation.uuidString), "ownerGeneration": .string(value.owner.generation.uuidString),
            "objectId": .string(ownerID), "typeValueUTF8Base64": .string(Data(typeValue.utf8).base64EncodedString()),
            "collectionValueUTF8Base64": .string(Data(collectionValue.utf8).base64EncodedString()),
            "blockId": row["id"]!, "blockType": row["type"]!, "blockTextUTF8Base64": .string(Data(text.utf8).base64EncodedString()),
            "parentId": row["nav"]!["parentId"]!, "position": row["nav"]!["pos"]!,
            "blockCount": .integer(Int64(rows.count))
        ])
    }

    private func migrationIntentObservation(_ intent: AnyPreparedMigrationIntent) -> AnyJSON {
        .object(["kind": .string(intent.kind.rawValue), "sourceKey": .string(intent.sourceKey),
            "intentId": .string(intent.intentID), "specBase64": .string(intent.specBytes.base64EncodedString()),
            "specSHA256": .string(intent.specSHA256)])
    }

    private func migrationObservation(_ receipt: AnyPreparedMigrationReceipt, on value: Mounted) -> AnyJSON {
        .object([
            "runtimeGeneration": .string(value.boot.generation.uuidString), "ownerGeneration": .string(value.owner.generation.uuidString),
            "stage": .string(receipt.stage.rawValue), "outcome": .string(receipt.outcome.rawValue),
            "fingerprint": .string(receipt.fingerprint), "objectId": .string(receipt.objectID ?? ""),
            "changeId": .string(receipt.changeID ?? ""), "recordIds": .array(receipt.recordIDs.map(AnyJSON.string))
        ])
    }

    private func prepare(_ intent: AnyPreparedFileIntent, fileURL: URL, on value: Mounted) async throws -> AnyPreparedFileReceipt {
        try await value.owner.perform { lease in
            let receipt = try await value.files.prepare(intent, fileURL: fileURL, authorize: { try await lease.validate() })
            try await lease.validate()
            return receipt
        }
    }

    private func status(_ intent: AnyPreparedFileIntent, on value: Mounted) async throws -> AnyPreparedFileReceipt {
        try await value.owner.perform { lease in
            let receipt = try await value.files.status(intent, authorize: { try await lease.validate() })
            try await lease.validate()
            return receipt
        }
    }

    private func commit(_ receipt: AnyPreparedFileReceipt, on value: Mounted) async throws -> AnyPreparedFileReceipt {
        try await value.owner.perform { lease in
            let result = try await value.files.commit(receipt, authorize: { try await lease.validate() })
            try await lease.validate()
            return result
        }
    }

    private func request(_ value: Mounted, suffix: [String]) async throws -> AnyJSON {
        try await value.owner.perform { lease in
            let result = try await value.client.requestJSON(method: "GET",
                path: ["v1", "spaces", value.owner.workspace.spaceID] + suffix,
                maximumResponseBytes: 65_536, authorize: { try await lease.validate() })
            try await lease.validate()
            return result
        }
    }

    private func readback(_ value: Mounted, receipt: AnyPreparedFileReceipt,
                          input: Input) async throws -> AnyJSON {
        let path = ["files", receipt.fileID]
        let metadata = try await request(value, suffix: path)
        let status = try await request(value, suffix: path + ["status"])
        let observedName = metadata["name"]?.string ?? ""
        let observedMIME = metadata["mime"]?.string ?? ""
        try componentsRequire(metadata["fileId"]?.string == receipt.fileID &&
            metadata["objectId"]?.string == receipt.intent.ownerObjectID &&
            metadata["size"]?.integer == Int64(input.content.count) &&
            metadata["inline"]?.bool != true &&
            metadata["cached"]?.bool == true && metadata["rootCid"]?.string == receipt.rootCID &&
            Data(observedName.utf8) == Data(input.name.utf8) && observedMIME == input.mime,
            "Ordinary native file metadata differs from the exact prepared input.")
        try componentsRequire(status["fileId"]?.string == receipt.fileID &&
            status["objectId"]?.string == receipt.intent.ownerObjectID &&
            status["cached"]?.bool == true && receipt.localFileComplete,
            "Ordinary native full file is not locally complete and cached.")
        let content = try await value.owner.perform { lease in
            try await value.client.checkAccount()
            try await lease.validate()
            try Task.checkCancellation()
            var request = value.boot.authenticatedRead(path:
                "spaces/" + value.owner.workspace.spaceID + "/files/" + receipt.fileID + "/content")
            request.httpMethod = "GET"
            request.timeoutInterval = 30
            request.setValue("application/octet-stream", forHTTPHeaderField: "Accept")
            let configuration = URLSessionConfiguration.ephemeral
            configuration.httpShouldSetCookies = false
            configuration.urlCache = nil
            configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
            let session = URLSession(configuration: configuration, delegate: ComponentsReadRejectRedirects(), delegateQueue: nil)
            defer { session.invalidateAndCancel() }
            let (data, response) = try await session.data(for: request)
            try await value.client.checkAccount()
            try await lease.validate()
            try Task.checkCancellation()
            guard let http = response as? HTTPURLResponse else {
                throw ComponentsRuntimeFailure(message: "Native content returned no HTTP response.")
            }
            try componentsRequire(http.statusCode == 200 && http.url == request.url &&
                http.mimeType == "application/octet-stream" && data.count == input.content.count &&
                data == input.content && AnyContentDigest.sha256(data) == receipt.intent.contentSHA256,
                "Ordinary native content bytes or response identity differs.")
            return AnyJSON.object([
                "httpStatus": .integer(Int64(http.statusCode)), "mediaType": .string(http.mimeType ?? ""),
                "byteCount": .integer(Int64(data.count)), "sha256": .string(AnyContentDigest.sha256(data))
            ])
        }
        return .object([
            "runtimeGeneration": .string(value.boot.generation.uuidString),
            "ownerGeneration": .string(value.owner.generation.uuidString),
            "metadata": metadata, "status": status, "content": content
        ])
    }

    private func requireIdentity(_ value: AnyPreparedFileReceipt,
                                 original: AnyPreparedFileReceipt) throws {
        try componentsRequire(value.intent == original.intent && value.fingerprint == original.fingerprint &&
            value.objectID == original.objectID && value.changeID == original.changeID &&
            value.fileID == original.fileID && value.recordIDs == original.recordIDs && value.rootCID == original.rootCID,
            "Native signed payload/change/file identity changed across commit.")
    }

    private func receiptObservation(_ receipt: AnyPreparedFileReceipt, on value: Mounted) -> AnyJSON {
        .object([
            "runtimeGeneration": .string(value.boot.generation.uuidString),
            "ownerGeneration": .string(value.owner.generation.uuidString),
            "stage": .string(receipt.stage.rawValue), "outcome": .string(receipt.outcome.rawValue),
            "fingerprint": .string(receipt.fingerprint), "payloadObjectId": .string(receipt.objectID),
            "changeId": .string(receipt.changeID), "fileId": .string(receipt.fileID),
            "rootCid": .string(receipt.rootCID), "localFileComplete": .bool(receipt.localFileComplete),
            "networkVerified": .bool(receipt.networkVerified),
            "recordIds": .array(receipt.recordIDs.map(AnyJSON.string))
        ])
    }

    private func attachProof(_ context: Context, identity: [String: AnyJSON],
                             capabilities: [String: AnyJSON], files: [[String: AnyJSON]],
                             definitions: [[String: AnyJSON]], documents: [[String: AnyJSON]], schemaReads: [AnyJSON],
                             runtimeVersions: [String], runtimeGenerations: [String], ownerGenerations: [String],
                             journeyComplete: Bool, completedCleanup: Bool) {
        let proof: AnyJSON = .object([
            "schema": .string("pinkha-prepared-components-apple-v1"),
            "status": .string("OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED"),
            "method": .string("AnyPreparedComponentsRuntimeTests/testManagedDefinitionsBlocksAndFullFilesSurviveReopen"),
            "sourceSHA": .string(context.sourceSHA), "executionUUID": .string(context.executionID),
            "executionKind": .string("local-mac"), "nonce": .string(context.nonce),
            "expectedNativeManifestSHA256": .string("1f66de41a97a3dba34846f69379ea321fe6999ba065fd5a7caeb482c2e960994"),
            "expectedRuntimeVersion": .string("v0.5.0-pinkha.prepared.components.1"),
            "processId": .integer(Int64(ProcessInfo.processInfo.processIdentifier)),
            "runtimeVersions": .array(runtimeVersions.map(AnyJSON.string)),
            "runtimeGenerations": .array(runtimeGenerations.map(AnyJSON.string)),
            "ownerGenerations": .array(ownerGenerations.map(AnyJSON.string)),
            "identity": .object(identity), "capabilities": .object(capabilities),
            "files": .array(files.map(AnyJSON.object)),
            "definitions": .array(definitions.map(AnyJSON.object)),
            "documents": .array(documents.map(AnyJSON.object)), "schemaReads": .array(schemaReads),
            "orderlyReopenCount": .integer(Int64(max(0, runtimeGenerations.count - 1))),
            "journeyComplete": .bool(journeyComplete), "completedCleanup": .bool(completedCleanup),
            "limits": .object([
                "restartKind": .string("orderly-native-sdk-store-same-xctest-process"),
                "osProcessCrash": .string("NOT_RUN"), "lostHTTPAcknowledgement": .string("NOT_INJECTED"),
                "networkSynchronization": .string("NOT_RUN"), "SSEDelivery": .string("NOT_EVALUATED_TRANSIENT"),
                "fullSpaceMigration": .string("NOT_PROVEN")
            ])
        ])
        do {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            let data = try encoder.encode(proof)
            guard data.count <= 65_536 else { XCTFail("Full-file observation attachment exceeded its bound."); return }
            let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
            attachment.name = "pinkha-prepared-components-runtime-proof.json"
            attachment.lifetime = .keepAlways
            add(attachment)
        } catch {
            XCTFail("Full-file observations could not be encoded.")
        }
    }
}

private struct ComponentsRuntimeFailure: Error, Sendable {
    let message: String
}

private func componentsRequire(_ condition: Bool, _ message: String) throws {
    guard condition else { throw ComponentsRuntimeFailure(message: message) }
}

/// A stateless delegate: credentials must never follow a content redirect.
private final class ComponentsReadRejectRedirects: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}
#endif
