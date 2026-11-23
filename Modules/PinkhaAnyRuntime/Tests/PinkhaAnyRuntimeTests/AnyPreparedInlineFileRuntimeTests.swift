#if PINKHA_PREPARED_INLINE_MIGRATION_ACCEPTANCE
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
@testable import PinkhaAnyRuntime

/// One managed C-runtime/public-client inline-file journey. The attachment is
/// observations only; an original passing XCTest and build lineage are required.
@MainActor
final class AnyPreparedInlineFileRuntimeTests: XCTestCase {
    private struct Mounted: Sendable {
        let boot: AnyEmbeddedSession
        let client: AnyHTTPClient
        let owner: AnyApplicationSession
        let objects: AnyNativePreparedMigration
        let files: AnyNativePreparedInlineFileMigration
    }

    private struct Input: Sendable {
        let label: String
        let content: Data
        let name: String
        let mime: String
    }

    private struct Context: Sendable {
        let sourceSHA: String
        let runID: String
        let runAttempt: String
        let nonce: String

        static func read() throws -> Self {
            let environment = ProcessInfo.processInfo.environment
            let prefix = "PINKHA_PREPARED_INLINE_APPLE_"
            let source = environment[prefix + "SOURCE_SHA"] ?? ""
            let run = environment[prefix + "RUN_ID"] ?? ""
            let attempt = environment[prefix + "RUN_ATTEMPT"] ?? ""
            let nonce = environment[prefix + "NONCE"] ?? ""
            func lowercaseHex(_ value: String, count: Int) -> Bool {
                value.utf8.count == count &&
                value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
            }
            func positiveDecimal(_ value: String) -> Bool {
                !value.isEmpty && value.first != "0" &&
                value.utf8.allSatisfy { (48...57).contains($0) } &&
                UInt64(value).map { $0 > 0 } == true
            }
            try inlineRequire(lowercaseHex(source, count: 40) && lowercaseHex(nonce, count: 32) &&
                positiveDecimal(run) && positiveDecimal(attempt),
                "Exact source/run/attempt and owned nonce must be supplied in the test environment.")
            return .init(sourceSHA: source, runID: run, runAttempt: attempt, nonce: nonce)
        }
    }

    func testManagedInlineFilesSurviveOrderlyReopenWithExactNativeBytes() async throws {
        executionTimeAllowance = 900
        let context = try Context.read()
        try inlineRequire(AnyEmbeddedBuild.linked == .pinkhaPreparedInlineMigrationCandidateV1,
                          "The separate inline-file runtime candidate is required.")
        let runtime = AnyEmbeddedRuntime.shared
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(
            "pinkha-prepared-inline-" + context.nonce, isDirectory: true)
        try inlineRequire(!FileManager.default.fileExists(atPath: directory.path),
                          "A fresh owned native data directory is required.")
        let inputs: [Input] = [
            .init(label: "empty", content: Data(), name: "", mime: ""),
            .init(label: "maximum", content: Data((0..<4095).map { UInt8($0 % 256) }),
                  name: "\u{05E7}\u{05D5}\u{05D1}\u{05E5} e\u{301} \u{1F9EA}.bin",
                  mime: "application/octet-stream")
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
            try inlineRequire(client.hasManagedAuthorization, "Actual managed data authorization is required.")
            let space = try await client.requestJSON(method: "POST", path: ["v1", "spaces"],
                body: .object(["name": .string("Disposable inline-file Apple acceptance")]))
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
                planID: AnyContentDigest.sha256(Data(("apple-inline-plan|" + context.nonce).utf8)),
                planSHA256: AnyContentDigest.sha256(Data("inline-file-cases:empty+4095/v1".utf8)))
            // Each pending plan freezes its carrier head. Two real owners keep
            // the two preparations independent before the first orderly reopen.
            var ownerIDs: [String] = []
            for input in inputs {
                ownerIDs.append(try await createOwner(binding: binding,
                    sourceKey: "apple-inline-owner-" + input.label + "-" + context.nonce,
                    title: "Disposable inline file owner " + input.label, on: current))
            }
            try inlineRequire(ownerIDs.count == 2 && Set(ownerIDs).count == 2,
                              "Each pending file requires its own actual native owner.")
            identity = [
                "accountId": .string(auth.accountID), "spaceId": .string(id),
                "storeId": .string(binding.storeID), "ownerObjectIds": .array(ownerIDs.map(AnyJSON.string)),
                "planId": .string(binding.planID), "planSHA256": .string(binding.planSHA256)
            ]
            capabilities = [
                "contract": .string(AnyNativePreparedInlineFileMigration.contract),
                "maximumInlineBytes": .integer(Int64(current.files.capabilities.maximumInlineBytes)),
                "networkVerified": .bool(current.files.capabilities.networkVerified)
            ]
            var plans: [(input: Input, intent: AnyPreparedInlineFileIntent,
                         prepared: AnyPreparedInlineFileReceipt)] = []
            for (index, input) in inputs.enumerated() {
                let ownerID = ownerIDs[index]
                let intent = try AnyPreparedInlineFileIntent(binding: binding,
                    sourceKey: "apple-inline-" + input.label + "-" + context.nonce,
                    ownerObjectID: ownerID, name: input.name, mime: input.mime, content: input.content)
                let prepared = try await prepare(intent, on: current)
                try inlineRequire(prepared.stage == .filePrepared && prepared.outcome == .prepared,
                                  "A fresh file must begin at its noncommitted native stage.")
                try inlineRequire(prepared.objectID != ownerID && prepared.recordIDs == [prepared.fileID],
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
            try inlineRequire(Set(plans.map { $0.prepared.fileID }).count == 2 &&
                Set(plans.map { $0.intent.intentID }).count == 2, "The two native file cases must remain distinct.")

            current = try await reopen(current, runtime: runtime, directory: directory, mnemonic: auth.mnemonic)
            mounted = current
            runtimeVersions.append(current.boot.engineVersion)
            runtimeGenerations.append(current.boot.generation.uuidString)
            ownerGenerations.append(current.owner.generation.uuidString)
            var completedFiles: [AnyPreparedInlineFileReceipt] = []
            for (index, plan) in plans.enumerated() {
                let recovered = try await status(plan.intent, on: current)
                try inlineRequire(recovered == plan.prepared, "Prepared native bytes changed across orderly reopen.")
                fileProofs[index]["afterPreparedReopen"] = receiptObservation(recovered, on: current)
                let completed = try await commit(plan.prepared, on: current)
                try requireIdentity(completed, original: plan.prepared)
                try inlineRequire(completed.isCompleteAndCurrent, "The actual inline file did not complete.")
                let currentStatus = try await status(plan.intent, on: current)
                let retry = try await commit(plan.prepared, on: current)
                try inlineRequire(currentStatus == completed && retry == completed,
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
                try inlineRequire(recovered == completedFiles[index] && retry == completedFiles[index],
                                  "Completed native identity changed across the second orderly reopen.")
                fileProofs[index]["afterCommittedReopenStatus"] = receiptObservation(recovered, on: current)
                fileProofs[index]["afterCommittedReopenRetry"] = receiptObservation(retry, on: current)
                fileProofs[index]["reopenedRead"] = try await readback(current, receipt: recovered, input: plan.input)
            }
            try inlineRequire(runtimeGenerations.count == 3 && Set(runtimeGenerations).count == 3 &&
                ownerGenerations.count == 3 && Set(ownerGenerations).count == 3,
                "Exactly three distinct runtime and application owner generations are required.")
            journeyComplete = true
            await current.owner.revokeAndDrain()
            _ = try await current.client.requestJSON(method: "DELETE", path: ["v1", "spaces", id])
            spaceID = nil
            _ = try await runtime.executeControl(.signOut, expectedGeneration: current.boot.generation)
            await runtime.stop(expectedGeneration: current.boot.generation)
            let stopped = await runtime.currentSession()
            try inlineRequire(stopped == nil, "The owned native runtime did not stop.")
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
        try inlineRequire(boot.engineVersion.hasPrefix("any v0.5.0-pinkha.prepared.inline.1 "),
                          "An exact inline-file candidate version token is required.")
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
        try inlineRequire(!account.isEmpty && !recovery.isEmpty, "Actual SDK authentication was incomplete.")
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
                let files = try await AnyNativePreparedInlineFileMigration.open(client: client, workspace: workspace,
                    authorize: { try await lease.validate() })
                try await lease.validate()
                return (objects, files)
            }
            try inlineRequire(client.hasManagedAuthorization &&
                pair.0.capabilities.storeID == pair.1.capabilities.storeID &&
                pair.1.capabilities.maximumInlineBytes == 4095 && !pair.1.capabilities.networkVerified,
                "Managed native store or explicit inline capability differs.")
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
        try inlineRequire(auth.accountID == old.owner.workspace.accountID &&
            boot.generation != old.boot.generation, "Native reopen changed the account or reused its runtime generation.")
        let current = try await mount(boot, workspace: old.owner.workspace)
        try inlineRequire(current.owner.generation != old.owner.generation &&
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
        try inlineRequire(completed.isCompleteAndCurrent, "The actual native owner did not complete.")
        let ownerID = try XCTUnwrap(completed.objectID)
        let ownerRecord = try await request(value, suffix: ["objects", ownerID])
        try inlineRequire(ownerRecord["record"] != nil, "The SDK-created owner is absent from ordinary native reads.")
        return ownerID
    }

    private func prepare(_ intent: AnyPreparedInlineFileIntent, on value: Mounted) async throws -> AnyPreparedInlineFileReceipt {
        try await value.owner.perform { lease in
            let receipt = try await value.files.prepare(intent, authorize: { try await lease.validate() })
            try await lease.validate()
            return receipt
        }
    }

    private func status(_ intent: AnyPreparedInlineFileIntent, on value: Mounted) async throws -> AnyPreparedInlineFileReceipt {
        try await value.owner.perform { lease in
            let receipt = try await value.files.status(intent, authorize: { try await lease.validate() })
            try await lease.validate()
            return receipt
        }
    }

    private func commit(_ receipt: AnyPreparedInlineFileReceipt, on value: Mounted) async throws -> AnyPreparedInlineFileReceipt {
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

    private func readback(_ value: Mounted, receipt: AnyPreparedInlineFileReceipt,
                          input: Input) async throws -> AnyJSON {
        let path = ["files", receipt.fileID]
        let metadata = try await request(value, suffix: path)
        let status = try await request(value, suffix: path + ["status"])
        let observedName = metadata["name"]?.string ?? ""
        let observedMIME = metadata["mime"]?.string ?? ""
        try inlineRequire(metadata["fileId"]?.string == receipt.fileID &&
            metadata["objectId"]?.string == receipt.intent.ownerObjectID &&
            metadata["size"]?.integer == Int64(input.content.count) &&
            metadata["inline"]?.bool == true && metadata["durable"]?.bool == true &&
            metadata["cached"]?.bool == true && metadata["rootCid"] == nil &&
            Data(observedName.utf8) == Data(input.name.utf8) && observedMIME == input.mime,
            "Ordinary native file metadata differs from the exact prepared input.")
        try inlineRequire(status["fileId"]?.string == receipt.fileID &&
            status["objectId"]?.string == receipt.intent.ownerObjectID &&
            status["state"]?.string == "durable" && status["cached"]?.bool == true,
            "Ordinary native file status is not durable and locally cached.")
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
            let session = URLSession(configuration: configuration, delegate: InlineReadRejectRedirects(), delegateQueue: nil)
            defer { session.invalidateAndCancel() }
            let (data, response) = try await session.data(for: request)
            try await value.client.checkAccount()
            try await lease.validate()
            try Task.checkCancellation()
            guard let http = response as? HTTPURLResponse else {
                throw InlineRuntimeFailure(message: "Native content returned no HTTP response.")
            }
            try inlineRequire(http.statusCode == 200 && http.url == request.url &&
                http.mimeType == "application/octet-stream" && data.count <= 4095 &&
                data == input.content && AnyContentDigest.sha256(data) == receipt.intent.contentSHA256,
                "Ordinary native content bytes or response identity differs.")
            return AnyJSON.object([
                "httpStatus": .integer(Int64(http.statusCode)), "mediaType": .string(http.mimeType ?? ""),
                "byteCount": .integer(Int64(data.count)), "sha256": .string(AnyContentDigest.sha256(data)),
                "base64": .string(data.base64EncodedString())
            ])
        }
        return .object([
            "runtimeGeneration": .string(value.boot.generation.uuidString),
            "ownerGeneration": .string(value.owner.generation.uuidString),
            "metadata": metadata, "status": status, "content": content
        ])
    }

    private func requireIdentity(_ value: AnyPreparedInlineFileReceipt,
                                 original: AnyPreparedInlineFileReceipt) throws {
        try inlineRequire(value.intent == original.intent && value.fingerprint == original.fingerprint &&
            value.objectID == original.objectID && value.changeID == original.changeID &&
            value.fileID == original.fileID && value.recordIDs == original.recordIDs,
            "Native signed payload/change/file identity changed across commit.")
    }

    private func receiptObservation(_ receipt: AnyPreparedInlineFileReceipt, on value: Mounted) -> AnyJSON {
        .object([
            "runtimeGeneration": .string(value.boot.generation.uuidString),
            "ownerGeneration": .string(value.owner.generation.uuidString),
            "stage": .string(receipt.stage.rawValue), "outcome": .string(receipt.outcome.rawValue),
            "fingerprint": .string(receipt.fingerprint), "payloadObjectId": .string(receipt.objectID),
            "changeId": .string(receipt.changeID), "fileId": .string(receipt.fileID),
            "recordIds": .array(receipt.recordIDs.map(AnyJSON.string))
        ])
    }

    private func attachProof(_ context: Context, identity: [String: AnyJSON],
                             capabilities: [String: AnyJSON], files: [[String: AnyJSON]],
                             runtimeVersions: [String], runtimeGenerations: [String], ownerGenerations: [String],
                             journeyComplete: Bool, completedCleanup: Bool) {
        let proof: AnyJSON = .object([
            "schema": .string("pinkha-prepared-inline-file-apple-v1"),
            "status": .string("OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED"),
            "method": .string("AnyPreparedInlineFileRuntimeTests/testManagedInlineFilesSurviveOrderlyReopenWithExactNativeBytes"),
            "sourceSHA": .string(context.sourceSHA), "runID": .string(context.runID),
            "runAttempt": .string(context.runAttempt), "nonce": .string(context.nonce),
            "expectedNativeManifestSHA256": .string("86598a7046ef135fa5dd2d0c2e559750f89ed8517fe4c1c753ce4457c13a009b"),
            "expectedRuntimeVersion": .string("v0.5.0-pinkha.prepared.inline.1"),
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
            guard data.count <= 65_536 else { XCTFail("Inline-file observation attachment exceeded its bound."); return }
            let attachment = XCTAttachment(data: data, uniformTypeIdentifier: "public.json")
            attachment.name = "pinkha-prepared-inline-file-runtime-proof.json"
            attachment.lifetime = .keepAlways
            add(attachment)
        } catch {
            XCTFail("Inline-file observations could not be encoded.")
        }
    }
}

private struct InlineRuntimeFailure: Error, Sendable {
    let message: String
}

private func inlineRequire(_ condition: Bool, _ message: String) throws {
    guard condition else { throw InlineRuntimeFailure(message: message) }
}

/// A stateless delegate: credentials must never follow a content redirect.
private final class InlineReadRejectRedirects: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}
#endif
