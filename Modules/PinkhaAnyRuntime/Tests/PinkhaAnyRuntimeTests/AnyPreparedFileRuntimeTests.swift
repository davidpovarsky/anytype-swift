#if PINKHA_PREPARED_FILE_MIGRATION_ACCEPTANCE
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
@testable import PinkhaAnyRuntime

/// One managed C-runtime/public-client full-file journey. The attachment is
/// observations only; an original passing XCTest and build lineage are required.
@MainActor
final class AnyPreparedFileRuntimeTests: XCTestCase {
    private struct Mounted: Sendable {
        let boot: AnyEmbeddedSession
        let client: AnyHTTPClient
        let owner: AnyApplicationSession
        let objects: AnyNativePreparedMigration
        let files: AnyNativePreparedFileMigration
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
            let prefix = "PINKHA_PREPARED_FILE_APPLE_"
            let source = environment[prefix + "SOURCE_SHA"] ?? ""
            let execution = environment[prefix + "EXECUTION_UUID"] ?? ""
            let nonce = environment[prefix + "NONCE"] ?? ""
            func lowercaseHex(_ value: String, count: Int) -> Bool {
                value.utf8.count == count && value.utf8.allSatisfy {
                    (48...57).contains($0) || (97...102).contains($0)
                }
            }
            try fullFileRequire(lowercaseHex(source, count: 40) && lowercaseHex(nonce, count: 32) &&
                UUID(uuidString: execution) != nil,
                "Exact source, real local execution UUID and owned nonce are required.")
            return .init(sourceSHA: source, executionID: execution, nonce: nonce)
        }
    }

    func testManagedFullFilesSurviveOrderlyReopenWithExactNativeBytes() async throws {
        executionTimeAllowance = 900
        let context = try Context.read()
        try fullFileRequire(AnyEmbeddedBuild.linked == .pinkhaPreparedFileMigrationCandidateV1,
                          "The separate full-file runtime candidate is required.")
        let runtime = AnyEmbeddedRuntime.shared
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(
            "pinkha-prepared-file-" + context.nonce, isDirectory: true)
        try fullFileRequire(!FileManager.default.fileExists(atPath: directory.path),
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
        var runtimeVersions: [String] = []
        var runtimeGenerations: [String] = []
        var ownerGenerations: [String] = []
        var journeyComplete = false
        var completedCleanup = false
        defer {
            attachProof(context, identity: identity, capabilities: capabilities, files: fileProofs,
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
            try fullFileRequire(client.hasManagedAuthorization, "Actual managed data authorization is required.")
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
                planID: AnyContentDigest.sha256(Data(("apple-full-file-plan|" + context.nonce).utf8)),
                planSHA256: AnyContentDigest.sha256(Data("full-file-cases:4096+2097152/v1".utf8)))
            // Each pending plan freezes its carrier head. Two real owners keep
            // the two preparations independent before the first orderly reopen.
            var ownerIDs: [String] = []
            for input in inputs {
                ownerIDs.append(try await createOwner(binding: binding,
                    sourceKey: "apple-full-file-owner-" + input.label + "-" + context.nonce,
                    title: "Disposable full file owner " + input.label, on: current))
            }
            try fullFileRequire(ownerIDs.count == 2 && Set(ownerIDs).count == 2,
                              "Each pending file requires its own actual native owner.")
            identity = [
                "accountId": .string(auth.accountID), "spaceId": .string(id),
                "storeId": .string(binding.storeID), "ownerObjectIds": .array(ownerIDs.map(AnyJSON.string)),
                "planId": .string(binding.planID), "planSHA256": .string(binding.planSHA256)
            ]
            capabilities = [
                "contract": .string(AnyNativePreparedFileMigration.contract),
                "maximumBytes": .integer(current.files.capabilities.maximumBytes),
                "networkVerified": .bool(current.files.capabilities.networkVerified)
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
                try fullFileRequire(prepared.stage == .filePrepared && prepared.outcome == .prepared,
                                  "A fresh file must begin at its noncommitted native stage.")
                try fullFileRequire(prepared.objectID != ownerID && prepared.recordIDs == [prepared.fileID],
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
            try fullFileRequire(Set(plans.map { $0.prepared.fileID }).count == 2 &&
                Set(plans.map { $0.intent.intentID }).count == 2, "The two native file cases must remain distinct.")

            current = try await reopen(current, runtime: runtime, directory: directory, mnemonic: auth.mnemonic)
            mounted = current
            runtimeVersions.append(current.boot.engineVersion)
            runtimeGenerations.append(current.boot.generation.uuidString)
            ownerGenerations.append(current.owner.generation.uuidString)
            var completedFiles: [AnyPreparedFileReceipt] = []
            for (index, plan) in plans.enumerated() {
                let known = try await prepare(plan.intent, fileURL: directory.appendingPathComponent("absent-source.bin"), on: current)
                try fullFileRequire(known == plan.prepared, "Known preparation must reconcile before reading a missing input file.")
                let recovered = try await status(plan.intent, on: current)
                try fullFileRequire(recovered == plan.prepared, "Prepared native bytes changed across orderly reopen.")
                fileProofs[index]["afterPreparedReopen"] = receiptObservation(recovered, on: current)
                let completed = try await commit(plan.prepared, on: current)
                try requireIdentity(completed, original: plan.prepared)
                try fullFileRequire(completed.isCompleteAndCurrent, "The actual full file did not complete.")
                let currentStatus = try await status(plan.intent, on: current)
                let retry = try await commit(plan.prepared, on: current)
                try fullFileRequire(currentStatus == completed && retry == completed,
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
            for (index, plan) in plans.enumerated() {
                let recovered = try await status(plan.intent, on: current)
                let retry = try await commit(plan.prepared, on: current)
                try fullFileRequire(recovered == completedFiles[index] && retry == completedFiles[index],
                                  "Completed native identity changed across the second orderly reopen.")
                fileProofs[index]["afterCommittedReopenStatus"] = receiptObservation(recovered, on: current)
                fileProofs[index]["afterCommittedReopenRetry"] = receiptObservation(retry, on: current)
                fileProofs[index]["reopenedRead"] = try await readback(current, receipt: recovered, input: plan.input)
            }
            try fullFileRequire(runtimeGenerations.count == 3 && Set(runtimeGenerations).count == 3 &&
                ownerGenerations.count == 3 && Set(ownerGenerations).count == 3,
                "Exactly three distinct runtime and application owner generations are required.")
            journeyComplete = true
            await current.owner.revokeAndDrain()
            _ = try await current.client.requestJSON(method: "DELETE", path: ["v1", "spaces", id])
            spaceID = nil
            _ = try await runtime.executeControl(.signOut, expectedGeneration: current.boot.generation)
            await runtime.stop(expectedGeneration: current.boot.generation)
            let stopped = await runtime.currentSession()
            try fullFileRequire(stopped == nil, "The owned native runtime did not stop.")
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
        try fullFileRequire(boot.engineVersion.hasPrefix("any v0.5.0-pinkha.prepared.file.1 "),
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
        try fullFileRequire(!account.isEmpty && !recovery.isEmpty, "Actual SDK authentication was incomplete.")
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
                try await lease.validate()
                return (objects, files)
            }
            try fullFileRequire(client.hasManagedAuthorization &&
                pair.0.capabilities.storeID == pair.1.capabilities.storeID &&
                pair.1.capabilities.maximumBytes == AnyPreparedFileIntent.maximumBytes && !pair.1.capabilities.networkVerified,
                "Managed native store or explicit full-file capability differs.")
            return .init(boot: boot, client: client, owner: owner, objects: pair.0, files: pair.1)
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
        try fullFileRequire(auth.accountID == old.owner.workspace.accountID &&
            boot.generation != old.boot.generation, "Native reopen changed the account or reused its runtime generation.")
        let current = try await mount(boot, workspace: old.owner.workspace)
        try fullFileRequire(current.owner.generation != old.owner.generation &&
            current.files.capabilities == old.files.capabilities &&
            current.objects.capabilities == old.objects.capabilities,
            "The reopened owner/store capability changed.")
        return current
    }

    private func createOwner(binding: AnyPreparedMigrationPlanBinding, sourceKey: String,
                             title: String, on value: Mounted) async throws -> String {
        let intent = try AnyPreparedMigrationIntent.object(binding: binding, sourceKey: sourceKey,
            typeID: "page", initialProperties: .object(["any": .object(["name": .string(title)])]))
        let prepared = try await value.owner.perform { lease in
            let receipt = try await value.objects.prepare(intent, authorize: { try await lease.validate() })
            try await lease.validate()
            return receipt
        }
        let completed = try await value.owner.perform { lease in
            let receipt = try await value.objects.commit(prepared, authorize: { try await lease.validate() })
            try await lease.validate()
            return receipt
        }
        try fullFileRequire(completed.isCompleteAndCurrent, "The actual native owner did not complete.")
        let ownerID = try XCTUnwrap(completed.objectID)
        let ownerRecord = try await request(value, suffix: ["objects", ownerID])
        try fullFileRequire(ownerRecord["record"] != nil, "The SDK-created owner is absent from ordinary native reads.")
        return ownerID
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
        try fullFileRequire(metadata["fileId"]?.string == receipt.fileID &&
            metadata["objectId"]?.string == receipt.intent.ownerObjectID &&
            metadata["size"]?.integer == Int64(input.content.count) &&
            metadata["inline"]?.bool != true &&
            metadata["cached"]?.bool == true && metadata["rootCid"]?.string == receipt.rootCID &&
            Data(observedName.utf8) == Data(input.name.utf8) && observedMIME == input.mime,
            "Ordinary native file metadata differs from the exact prepared input.")
        try fullFileRequire(status["fileId"]?.string == receipt.fileID &&
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
            let session = URLSession(configuration: configuration, delegate: FullFileReadRejectRedirects(), delegateQueue: nil)
            defer { session.invalidateAndCancel() }
            let (data, response) = try await session.data(for: request)
            try await value.client.checkAccount()
            try await lease.validate()
            try Task.checkCancellation()
            guard let http = response as? HTTPURLResponse else {
                throw FullFileRuntimeFailure(message: "Native content returned no HTTP response.")
            }
            try fullFileRequire(http.statusCode == 200 && http.url == request.url &&
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
        try fullFileRequire(value.intent == original.intent && value.fingerprint == original.fingerprint &&
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
                             runtimeVersions: [String], runtimeGenerations: [String], ownerGenerations: [String],
                             journeyComplete: Bool, completedCleanup: Bool) {
        let proof: AnyJSON = .object([
            "schema": .string("pinkha-prepared-file-file-apple-v1"),
            "status": .string("OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED"),
            "method": .string("AnyPreparedFileRuntimeTests/testManagedFullFilesSurviveOrderlyReopenWithExactNativeBytes"),
            "sourceSHA": .string(context.sourceSHA), "executionUUID": .string(context.executionID),
            "executionKind": .string("local-mac"), "nonce": .string(context.nonce),
            "expectedNativeManifestSHA256": .string("cd52276a06109562ce2265995016696d2cee7526b6619c95caab5bbc1d378077"),
            "expectedRuntimeVersion": .string("v0.5.0-pinkha.prepared.file.1"),
            "processId": .integer(Int64(ProcessInfo.processInfo.processIdentifier)),
            "runtimeVersions": .array(runtimeVersions.map(AnyJSON.string)),
            "runtimeGenerations": .array(runtimeGenerations.map(AnyJSON.string)),
            "ownerGenerations": .array(ownerGenerations.map(AnyJSON.string)),
            "identity": .object(identity), "capabilities": .object(capabilities),
            "files": .array(files.map(AnyJSON.object)),
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
            attachment.name = "pinkha-prepared-file-file-runtime-proof.json"
            attachment.lifetime = .keepAlways
            add(attachment)
        } catch {
            XCTFail("Full-file observations could not be encoded.")
        }
    }
}

private struct FullFileRuntimeFailure: Error, Sendable {
    let message: String
}

private func fullFileRequire(_ condition: Bool, _ message: String) throws {
    guard condition else { throw FullFileRuntimeFailure(message: message) }
}

/// A stateless delegate: credentials must never follow a content redirect.
private final class FullFileReadRejectRedirects: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}
#endif
