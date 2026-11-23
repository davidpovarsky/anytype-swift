import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativePreparedInlineFileMigrationTests: XCTestCase, @unchecked Sendable {
    func testExactBytesAndMetadataSurviveTheWireAtBothSizeBounds() throws {
        for bytes in [Data(), Data((0..<4095).map { UInt8($0 % 256) })] {
            let intent = try makeIntent(name: "???? \"quoted\" ??", mime: "application/octet-stream", content: bytes)
            let body = try JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(intent.prepareBody))
            let specBytes = try XCTUnwrap(Data(base64Encoded: XCTUnwrap(body["specBase64"]?.string)))
            XCTAssertEqual(specBytes, intent.specBytes)
            XCTAssertEqual(AnyContentDigest.sha256(specBytes), intent.specSHA256)
            let spec = try JSONDecoder().decode(AnyJSON.self, from: specBytes)
            let content = try XCTUnwrap(Data(base64Encoded: XCTUnwrap(spec["content"]?.string)))
            XCTAssertEqual(content, bytes)
            XCTAssertEqual(spec["contentSHA256"]?.string, AnyContentDigest.sha256(bytes))
            XCTAssertEqual(spec["ownerObjectId"]?.string, "owning-document")
            XCTAssertEqual(spec["name"]?.string, intent.name)
            XCTAssertEqual(spec["mime"]?.string, intent.mime)
            XCTAssertEqual(intent.size, bytes.count)
            XCTAssertEqual(Set(try XCTUnwrap(spec.object).keys),
                           Set(["ownerObjectId", "name", "mime", "content", "contentSHA256"]))
            XCTAssertNil(body["canWrite"])
            XCTAssertNil(body["fileId"])
        }
        let emptyMetadata = try makeIntent(name: "", mime: "", content: Data())
        XCTAssertEqual(emptyMetadata.name, "")
        XCTAssertEqual(emptyMetadata.mime, "")
    }

    func testBoundedInputRejectsOversizeAndInvalidMetadataWithoutTruncation() throws {
        XCTAssertThrowsError(try makeIntent(content: Data(repeating: 1, count: 4096)))
        XCTAssertThrowsError(try makeIntent(name: String(repeating: "?", count: 513)))
        XCTAssertThrowsError(try makeIntent(mime: String(repeating: "x", count: 256)))
        XCTAssertThrowsError(try makeIntent(name: "bad\0name"))
        XCTAssertThrowsError(try makeIntent(mime: "bad\0mime"))
        XCTAssertThrowsError(try makeIntent(owner: ""))
        XCTAssertThrowsError(try makeIntent(owner: String(repeating: "x", count: 257)))
        XCTAssertThrowsError(try makeIntent(sourceKey: "invalid\nsource"))
        let boundary = try makeIntent(name: String(repeating: "?", count: 512),
                                      mime: String(repeating: "x", count: 255))
        XCTAssertEqual(boundary.name.utf8.count, 1024)
        XCTAssertEqual(boundary.mime.utf8.count, 255)
    }

    func testLogicalIdentityKeepsChangedInputAsACollisionAndSeparatesScopes() throws {
        let original = try makeIntent()
        for changed in [
            try makeIntent(name: "changed"),
            try makeIntent(owner: "different-owner"),
            try makeIntent(content: Data([9])),
            try makeIntent(binding: binding(digest: String(repeating: "f", count: 64)))
        ] {
            XCTAssertEqual(original.intentID, changed.intentID)
            XCTAssertTrue(original.specSHA256 != changed.specSHA256 ||
                          original.binding.planSHA256 != changed.binding.planSHA256)
        }
        let contexts = [
            try binding(account: "other-account"), try binding(space: "other-space"),
            try binding(store: "other-store"), try binding(plan: String(repeating: "d", count: 64))
        ]
        for context in contexts {
            XCTAssertNotEqual(original.intentID, try makeIntent(binding: context).intentID)
        }
        XCTAssertNotEqual(original.intentID, try makeIntent(sourceKey: "another-file").intentID)
        let object = try AnyPreparedMigrationIntent.object(binding: original.binding,
            sourceKey: original.sourceKey, typeID: "type-page", initialProperties: .object([:]))
        XCTAssertNotEqual(original.intentID, object.intentID)
    }

    func testCapabilitiesCannotAdvertiseAnUnboundedOrWrongScopeContract() throws {
        let intent = try makeIntent()
        let valid = InlineMigrationWire.capabilities(intent)
        let parsed = try AnyPreparedInlineFileCapabilities(valid, workspace: intent.binding.workspace)
        XCTAssertEqual(parsed.maximumInlineBytes, 4095)
        XCTAssertFalse(parsed.networkVerified)
        let mutations: [String: AnyJSON] = [
            "contract": .string("future-contract"), "inlineFile": .integer(0),
            "maximumInlineBytes": .integer(4096), "file": .integer(1),
            "accountId": .string("other-account"), "spaceId": .string("other-space"),
            "storeId": .string(""), "networkVerified": .null
        ]
        for (key, value) in mutations {
            var fields = try XCTUnwrap(valid.object); fields[key] = value
            XCTAssertThrowsError(try AnyPreparedInlineFileCapabilities(.object(fields),
                workspace: intent.binding.workspace), key)
        }
    }

    func testReceiptBindsOwnerContentEveryReservedIdentityAndStage() throws {
        let intent = try makeIntent()
        let valid = InlineMigrationWire.receipt(intent, stage: 0, outcome: "prepared")
        let parsed = try AnyPreparedInlineFileReceipt(valid, intent: intent)
        XCTAssertEqual(parsed.stage, .filePrepared)
        XCTAssertEqual(parsed.objectID, "reserved-payload-root")
        XCTAssertNotEqual(parsed.objectID, intent.ownerObjectID)
        XCTAssertEqual(parsed.recordIDs, [parsed.fileID])
        let mutations: [String: AnyJSON] = [
            "ownerObjectId": .string("other-owner"), "contentSHA256": .string(String(repeating: "f", count: 64)),
            "size": .integer(999), "kind": .string("object"),
            "specSHA256": .string(String(repeating: "f", count: 64)),
            "planSHA256": .string(String(repeating: "f", count: 64)),
            "accountId": .string("other-account"), "spaceId": .string("other-space"),
            "storeId": .string("other-store"), "sourceKey": .string("other-source"),
            "intentId": .string(String(repeating: "f", count: 64)),
            "fingerprint": .string("invalid"), "objectId": .string(""), "changeId": .string(""),
            "fileId": .string("different-file"), "recordIds": .array([]),
            "stage": .string("complete"), "outcome": .string("committed")
        ]
        for (key, value) in mutations {
            var fields = try XCTUnwrap(valid.object); fields[key] = value
            XCTAssertThrowsError(try AnyPreparedInlineFileReceipt(.object(fields), intent: intent), key)
        }
        for stage in [0, 1] {
            let obsolete = try AnyPreparedInlineFileReceipt(
                InlineMigrationWire.receipt(intent, stage: stage, outcome: "obsolete"), intent: intent)
            XCTAssertFalse(obsolete.isCompleteAndCurrent)
        }
    }

    func testPrepareUsesDedicatedRouteAndExactImmutableEnvelope() async throws {
        let intent = try makeIntent(), wire = InlineMigrationWire(try makeIntent())
        let client = try service(intent, wire)
        let prepared = try await client.prepare(intent, authorize: {})
        XCTAssertEqual(prepared.intent, intent)
        let calls = await wire.snapshot()
        let writes = calls.filter { $0.method == "PUT" }
        XCTAssertEqual(writes.count, 1)
        XCTAssertEqual(writes.first?.path, ["v1", "spaces", "space", "pinkha", "migration",
            "intents", intent.intentID, "inline-file", "prepare"])
        XCTAssertEqual(writes.first?.body, intent.prepareBody)
        XCTAssertTrue(calls.contains { $0.path.suffix(2) == ["inline-file", "capabilities"] })
        XCTAssertFalse(calls.contains { $0.method == "POST" })
    }

    func testCommitAdvancesTwoDurableStagesAndCompletedRetryDoesNotWrite() async throws {
        let intent = try makeIntent(), wire = InlineMigrationWire(try makeIntent())
        let client = try service(intent, wire)
        let prepared = try await client.prepare(intent, authorize: {})
        let complete = try await client.commit(prepared, authorize: {})
        XCTAssertTrue(complete.isCompleteAndCurrent)
        XCTAssertEqual(complete.objectID, prepared.objectID)
        XCTAssertEqual(complete.changeID, prepared.changeID)
        XCTAssertEqual(complete.fileID, prepared.fileID)
        XCTAssertEqual(complete.fingerprint, prepared.fingerprint)
        let retry = try await client.commit(prepared, authorize: {})
        XCTAssertEqual(retry, complete)
        let calls = await wire.snapshot()
        let writes = calls.filter { $0.method == "POST" }
        XCTAssertEqual(writes.count, 2)
        XCTAssertEqual(writes.first?.body, writes.last?.body)
        XCTAssertTrue(writes.allSatisfy { $0.path.suffix(2) == ["inline-file", "commit"] })
        XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        let stages = await wire.committedStages()
        XCTAssertEqual(stages, [1, 2])
    }

    func testLostAcknowledgementAtEitherStageReconcilesBeforeRemainingWrite() async throws {
        for lostStage in [1, 2] {
            let intent = try makeIntent(), wire = InlineMigrationWire(try makeIntent())
            let client = try service(intent, wire)
            let prepared = try await client.prepare(intent, authorize: {})
            await wire.loseAcknowledgement(at: lostStage)
            do {
                _ = try await client.commit(prepared, authorize: {})
                XCTFail("An uncertain native write was promoted to success.")
            } catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
            let before = await wire.snapshot()
            XCTAssertEqual(before.filter { $0.method == "POST" }.count, lostStage)
            let complete = try await client.commit(prepared, authorize: {})
            XCTAssertTrue(complete.isCompleteAndCurrent)
            XCTAssertEqual(complete.fileID, prepared.fileID)
            let calls = await wire.snapshot()
            XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 2)
            XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
            let stages = await wire.committedStages()
            XCTAssertEqual(stages, [1, 2])
        }
    }

    func testDeletedModifiedAndObsoleteNeverAllocateOrCommitAgain() async throws {
        for (stage, outcome) in [(2, "committed_deleted"), (2, "committed_modified"), (1, "obsolete")] {
            let intent = try makeIntent(), wire = InlineMigrationWire(try makeIntent())
            let client = try service(intent, wire)
            let prepared = try await client.prepare(intent, authorize: {})
            await wire.setState(stage: stage, outcome: outcome)
            do {
                _ = try await client.commit(prepared, authorize: {})
                XCTFail("A terminal file outcome was recreated.")
            } catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .terminalOutcome(outcome)) }
            let calls = await wire.snapshot()
            XCTAssertFalse(calls.contains { $0.method == "POST" })
            XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        }
    }

    func testChangedReservedIdentityOrRegressingStageStopsBeforeCommit() async throws {
        for mutation in [
            ["fingerprint": AnyJSON.string(String(repeating: "d", count: 64))],
            ["objectId": .string("changed-payload-root")],
            ["changeId": .string("changed-row-cid")],
            ["fileId": .string("changed-file"), "recordIds": .array([.string("changed-file")])]
        ] {
            let intent = try makeIntent(), wire = InlineMigrationWire(try makeIntent())
            let client = try service(intent, wire)
            let prepared = try await client.prepare(intent, authorize: {})
            await wire.mutateReceipt(mutation)
            do {
                _ = try await client.commit(prepared, authorize: {})
                XCTFail("A replacement identity was accepted.")
            } catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .changedIntent) }
            let calls = await wire.snapshot()
            XCTAssertFalse(calls.contains { $0.method == "POST" })
        }
        let intent = try makeIntent(), wire = InlineMigrationWire(try makeIntent())
        await wire.setState(stage: 1, outcome: "prepared")
        let client = try service(intent, wire)
        let rootCommitted = try await client.prepare(intent, authorize: {})
        await wire.setState(stage: 0, outcome: "prepared")
        do { _ = try await client.commit(rootCommitted, authorize: {}); XCTFail("Stage regressed.") }
        catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .changedIntent) }
        let calls = await wire.snapshot()
        XCTAssertFalse(calls.contains { $0.method == "POST" })
    }

    func testOwnerOrStoreChangeStopsBeforeTheNextDurableStage() async throws {
        let intent = try makeIntent(), authority = InlineMigrationAuthority()
        let wire = InlineMigrationWire(intent, afterCommit: { await authority.revoke() })
        let client = try service(intent, wire)
        let prepared = try await client.prepare(intent, authorize: { try await authority.check() })
        do {
            _ = try await client.commit(prepared, authorize: { try await authority.check() })
            XCTFail("Retired owner continued the file migration.")
        } catch { XCTAssertEqual(error as? AnyEngineError, .accountChanged) }
        let revokedCalls = await wire.snapshot()
        XCTAssertEqual(revokedCalls.filter { $0.method == "POST" }.count, 1)

        let replaced = InlineMigrationWire(intent)
        let replacementClient = try service(intent, replaced)
        let other = try await replacementClient.prepare(intent, authorize: {})
        await replaced.replaceStoreAfterCommit()
        do { _ = try await replacementClient.commit(other, authorize: {}); XCTFail("Store changed.") }
        catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .changedStore) }
        let replacedCalls = await replaced.snapshot()
        XCTAssertEqual(replacedCalls.filter { $0.method == "POST" }.count, 1)
    }

    func testNoProgressOrDisabledCapabilityDoesNotStartARetryLoop() async throws {
        let intent = try makeIntent(), wire = InlineMigrationWire(try makeIntent())
        let client = try service(intent, wire)
        let prepared = try await client.prepare(intent, authorize: {})
        await wire.forceNextStage(0)
        do { _ = try await client.commit(prepared, authorize: {}); XCTFail("No native progress.") }
        catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .incompleteCommit) }
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 1)

        let disabled = InlineMigrationWire(intent)
        let unavailable = try service(intent, disabled)
        await disabled.disableCapability()
        do { _ = try await unavailable.prepare(intent, authorize: {}); XCTFail("Unavailable route used.") }
        catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .unsupportedContract) }
        let blocked = await disabled.snapshot()
        XCTAssertFalse(blocked.contains { $0.method == "PUT" || $0.method == "POST" })
    }

    private func binding(account: String = "account", space: String = "space",
                         store: String = "persistent-store", plan: String = String(repeating: "a", count: 64),
                         digest: String = String(repeating: "b", count: 64)) throws -> AnyPreparedMigrationPlanBinding {
        try .init(workspace: .init(accountID: account, spaceID: space), storeID: store,
                  planID: plan, planSHA256: digest)
    }

    private func makeIntent(binding: AnyPreparedMigrationPlanBinding? = nil, sourceKey: String = "source-file",
                            owner: String = "owning-document", name: String = "file.txt",
                            mime: String = "text/plain", content: Data = Data([0, 1, 255])) throws -> AnyPreparedInlineFileIntent {
        try .init(binding: binding ?? self.binding(), sourceKey: sourceKey,
                  ownerObjectID: owner, name: name, mime: mime, content: content)
    }

    private func service(_ intent: AnyPreparedInlineFileIntent,
                         _ wire: InlineMigrationWire) throws -> AnyNativePreparedInlineFileMigration {
        try .init(capabilities: .init(InlineMigrationWire.capabilities(intent), workspace: intent.binding.workspace),
            request: { method, path, body, authorize in
                try await authorize()
                return try await wire.request(method: method, path: path, body: body)
            })
    }
}

private actor InlineMigrationAuthority {
    private var active = true
    func revoke() { active = false }
    func check() throws { if !active { throw AnyEngineError.accountChanged } }
}

/// Explicit transport model; these controls never claim native/HTTP execution.
private actor InlineMigrationWire {
    struct Call: Sendable { let method: String; let path: [String]; let body: AnyJSON? }
    private let intent: AnyPreparedInlineFileIntent
    private let afterCommit: (@Sendable () async -> Void)?
    private var calls: [Call] = []
    private var stage = 0
    private var outcome = "prepared"
    private var mutations: [String: AnyJSON] = [:]
    private var lostStage: Int?
    private var forcedStage: Int?
    private var changedStore = false
    private var replaceAfterCommit = false
    private var capabilityDisabled = false
    private var commits: [Int] = []

    init(_ intent: AnyPreparedInlineFileIntent, afterCommit: (@Sendable () async -> Void)? = nil) {
        self.intent = intent; self.afterCommit = afterCommit
    }

    func snapshot() -> [Call] { calls }
    func committedStages() -> [Int] { commits }
    func loseAcknowledgement(at stage: Int) { lostStage = stage }
    func setState(stage: Int, outcome: String) { self.stage = stage; self.outcome = outcome }
    func mutateReceipt(_ value: [String: AnyJSON]) { mutations = value }
    func forceNextStage(_ value: Int) { forcedStage = value }
    func replaceStoreAfterCommit() { replaceAfterCommit = true }
    func disableCapability() { capabilityDisabled = true }

    func request(method: String, path: [String], body: AnyJSON?) async throws -> AnyJSON {
        calls.append(.init(method: method, path: path, body: body))
        if path.last == "capabilities" {
            var result = Self.capabilities(intent).object!
            if changedStore { result["storeId"] = .string("replacement-store") }
            if capabilityDisabled { result["inlineFile"] = .integer(0) }
            return .object(result)
        }
        if method == "POST" {
            stage = forcedStage ?? min(stage + 1, 2)
            forcedStage = nil
            outcome = stage == 2 ? "committed" : "prepared"
            commits.append(stage)
            if replaceAfterCommit { changedStore = true }
            await afterCommit?()
            if lostStage == stage { lostStage = nil; throw AnyEngineError.writeUncertain }
        }
        var result = Self.receipt(intent, stage: stage, outcome: outcome).object!
        for (key, value) in mutations { result[key] = value }
        return .object(result)
    }

    static func capabilities(_ intent: AnyPreparedInlineFileIntent) -> AnyJSON { .object([
        "contract": .string(AnyNativePreparedInlineFileMigration.contract),
        "storeId": .string(intent.binding.storeID), "accountId": .string(intent.binding.workspace.accountID),
        "spaceId": .string(intent.binding.workspace.spaceID), "inlineFile": .integer(1),
        "maximumInlineBytes": .integer(4095), "file": .integer(0), "networkVerified": .bool(false)
    ]) }

    static func receipt(_ intent: AnyPreparedInlineFileIntent, stage: Int, outcome: String) -> AnyJSON { .object([
        "contract": .string(AnyNativePreparedInlineFileMigration.contract),
        "intentId": .string(intent.intentID), "storeId": .string(intent.binding.storeID),
        "accountId": .string(intent.binding.workspace.accountID), "spaceId": .string(intent.binding.workspace.spaceID),
        "planId": .string(intent.binding.planID), "planSHA256": .string(intent.binding.planSHA256),
        "sourceKey": .string(intent.sourceKey), "kind": .string("inlineFile"),
        "specSHA256": .string(intent.specSHA256), "fingerprint": .string(String(repeating: "c", count: 64)),
        "stage": .string(["file-prepared", "file-root-committed", "complete"][stage]),
        "outcome": .string(outcome), "objectId": .string("reserved-payload-root"),
        "changeId": .string("reserved-row-cid"), "fileId": .string("reserved-file-id"),
        "recordIds": .array([.string("reserved-file-id")]),
        "ownerObjectId": .string(intent.ownerObjectID), "contentSHA256": .string(intent.contentSHA256),
        "size": .integer(Int64(intent.size))
    ]) }
}
