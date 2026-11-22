import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativePreparedMigrationTests: XCTestCase, @unchecked Sendable {
    func testLogicalIdentityDoesNotChangeWithPayloadOrPlanDigest() throws {
        let a = try intent(text: "original")
        let b = try intent(text: "changed")
        let c = try intent(planDigest: String(repeating: "f", count: 64), text: "original")
        XCTAssertEqual(a.intentID, b.intentID)
        XCTAssertEqual(a.intentID, c.intentID)
        XCTAssertNotEqual(a.specSHA256, b.specSHA256)
        XCTAssertNotEqual(a.binding.planSHA256, c.binding.planSHA256)
        XCTAssertEqual(a.specSHA256, c.specSHA256)
        let other = try intent(sourceKey: "source-block-2")
        XCTAssertNotEqual(a.intentID, other.intentID)
    }

    func testIdentitySeparatesAccountSpaceStorePlanAndKind() throws {
        let original = try intent()
        let contexts = [
            try binding(account: "other-account"), try binding(space: "other-space"),
            try binding(store: "other-store"), try binding(plan: String(repeating: "b", count: 64))
        ]
        for value in contexts {
            let changed = try AnyPreparedMigrationIntent.block(binding: value, sourceKey: "source-block",
                objectID: "target-object", type: "paragraph", text: "hello", position: "a0")
            XCTAssertNotEqual(original.intentID, changed.intentID)
        }
        let object = try AnyPreparedMigrationIntent.object(binding: original.binding,
            sourceKey: original.sourceKey, typeID: "type-page", initialProperties: .object([:]))
        XCTAssertNotEqual(original.intentID, object.intentID)
    }

    func testExactSpecificationBytesSurviveEnvelopeEncoding() throws {
        let value = try intent(text: "שלום \"quoted\" \\ path 🧪")
        let wireBytes = try JSONEncoder().encode(value.prepareBody)
        let decoded = try JSONDecoder().decode(AnyJSON.self, from: wireBytes)
        let encodedSpec = try XCTUnwrap(decoded["specBase64"]?.string)
        let exact = try XCTUnwrap(Data(base64Encoded: encodedSpec))
        XCTAssertEqual(exact, value.specBytes)
        XCTAssertEqual(AnyContentDigest.sha256(exact), value.specSHA256)
        XCTAssertEqual(decoded["specSHA256"]?.string, value.specSHA256)
        let spec = try JSONDecoder().decode(AnyJSON.self, from: exact)
        XCTAssertEqual(spec["text"]?.string, "שלום \"quoted\" \\ path 🧪")
        XCTAssertEqual(spec["objectId"]?.string, "target-object")
        XCTAssertEqual(spec["nav"]?["pos"]?.string, "a0")
        XCTAssertNil(decoded["spec"])
    }

    func testKnownTypedBoundsRejectUnsupportedAndUnboundedShapes() throws {
        let context = try binding()
        XCTAssertThrowsError(try AnyPreparedMigrationIntent.block(binding: context, sourceKey: "block",
            objectID: "target-object", type: "dataview", text: "", position: "a0"))
        XCTAssertThrowsError(try AnyPreparedMigrationIntent.block(binding: context, sourceKey: "block",
            objectID: "target-object", type: "paragraph", text: "", position: ""))
        XCTAssertThrowsError(try AnyPreparedMigrationIntent.block(binding: context, sourceKey: "block\nunsafe",
            objectID: "target-object", type: "paragraph", text: "", position: "a0"))
        XCTAssertThrowsError(try AnyPreparedMigrationIntent.object(binding: context, sourceKey: "object",
            typeID: "type-page", initialProperties: .object(["any": .object(["type": .string("foreign")])])))
        XCTAssertThrowsError(try binding(plan: "not-a-plan-id"))
    }

    func testCapabilitiesRequireExactScopeAndExplicitFileBoundary() throws {
        let value = try intent()
        let good = PreparedMigrationWire.capabilities(value)
        let capabilities = try AnyPreparedMigrationCapabilities(good, workspace: value.binding.workspace)
        XCTAssertFalse(capabilities.networkVerified)
        let replacements: [(String, AnyJSON)] = [
            ("accountId", .string("foreign")), ("spaceId", .string("foreign")),
            ("contract", .string("other")), ("file", .integer(1)),
            ("editorBlock", .integer(0)), ("networkVerified", .string("false"))
        ]
        for (key, replacement) in replacements {
            var changed = good.object!; changed[key] = replacement
            XCTAssertThrowsError(try AnyPreparedMigrationCapabilities(.object(changed), workspace: value.binding.workspace))
        }
    }

    func testReceiptCannotCrossIdentitySpecificationOrPlan() throws {
        let value = try intent(), good = PreparedMigrationWire.receipt(try intent())
        for key in ["contract", "intentId", "storeId", "accountId", "spaceId", "planId", "planSHA256",
                    "sourceKey", "kind", "specSHA256", "fingerprint", "stage", "outcome", "objectId"] {
            var changed = good.object!; changed[key] = .string("foreign")
            XCTAssertThrowsError(try AnyPreparedMigrationReceipt(.object(changed), intent: value), key)
        }
        var changed = good.object!; changed["recordIds"] = .array([.string("id"), .string("id")])
        XCTAssertThrowsError(try AnyPreparedMigrationReceipt(.object(changed), intent: value))
        changed = good.object!; changed["stage"] = .string("complete")
        XCTAssertThrowsError(try AnyPreparedMigrationReceipt(.object(changed), intent: value))
    }

    func testPrepareTransmitsOnlyTheExactBoundSpecification() async throws {
        let value = try intent(), wire = PreparedMigrationWire(try intent())
        let client = try service(value, wire)
        let prepared = try await client.prepare(value, authorize: {})
        XCTAssertEqual(prepared.intent, value)
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.map(\.method), ["GET", "PUT"])
        XCTAssertEqual(calls.last.map { Array($0.path.suffix(4)) }, ["intents", value.intentID, "block", "prepare"])
        XCTAssertEqual(calls.last?.body, value.prepareBody)
    }

    func testCommitChecksCurrentReceiptAndDispatchesOnlyOnce() async throws {
        let value = try intent(), wire = PreparedMigrationWire(try intent())
        let client = try service(value, wire)
        let prepared = try await client.prepare(value, authorize: {})
        let committed = try await client.commit(prepared, authorize: {})
        XCTAssertTrue(committed.isCompleteAndCurrent)
        let reconciled = try await client.commit(prepared, authorize: {})
        XCTAssertEqual(reconciled, committed)
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 1)
        XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        let body = try XCTUnwrap(calls.first { $0.method == "POST" }?.body)
        XCTAssertEqual(body["fingerprint"]?.string, prepared.fingerprint)
        XCTAssertEqual(body["planSHA256"]?.string, value.binding.planSHA256)
    }

    func testLostAcknowledgementReconcilesOriginalCommitWithoutAnotherPost() async throws {
        let value = try intent(), wire = PreparedMigrationWire(try intent())
        await wire.loseNextCommitAcknowledgement()
        let client = try service(value, wire)
        let prepared = try await client.prepare(value, authorize: {})
        do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Lost acknowledgement was reported as success") }
        catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        let recovered = try await client.commit(prepared, authorize: {})
        XCTAssertTrue(recovered.isCompleteAndCurrent)
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 1)
    }

    func testDeletedModifiedAndObsoleteNeverRecreateOrCommit() async throws {
        for outcome in ["committed_deleted", "committed_modified", "obsolete"] {
            let value = try intent(), wire = PreparedMigrationWire(try intent())
            let client = try service(value, wire)
            let prepared = try await client.prepare(value, authorize: {})
            await wire.setOutcome(outcome)
            do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Terminal outcome was overwritten") }
            catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .terminalOutcome(outcome)) }
            let calls = await wire.snapshot()
            XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 0)
            XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        }
    }

    func testChangedPersistentStoreStopsBeforePrepare() async throws {
        let value = try intent(), wire = PreparedMigrationWire(try intent())
        let client = try service(value, wire)
        await wire.changeStore()
        do { _ = try await client.prepare(value, authorize: {}); XCTFail("Foreign store accepted plan") }
        catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .changedStore) }
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.map(\.method), ["GET"])
    }

    func testChangedNativeFingerprintStopsBeforeCommit() async throws {
        let value = try intent(), wire = PreparedMigrationWire(try intent())
        let client = try service(value, wire)
        let prepared = try await client.prepare(value, authorize: {})
        await wire.changeFingerprint()
        do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Changed prepared envelope committed") }
        catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .changedIntent) }
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 0)
    }

    func testAuthorityLostAfterPrepareSuppressesReceiptButKeepsIdentityForRecovery() async throws {
        let value = try intent(), gate = PreparedMigrationAuthority()
        let wire = PreparedMigrationWire(value, afterPrepare: { await gate.revoke() })
        let client = try service(value, wire)
        do { _ = try await client.prepare(value, authorize: { try await gate.check() }); XCTFail("Revoked owner received receipt") }
        catch { XCTAssertEqual(error as? AnyEngineError, .accountChanged) }
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        let receipt = try await client.status(value, authorize: {})
        XCTAssertEqual(receipt.intent.intentID, value.intentID)
        XCTAssertFalse(receipt.isCompleteAndCurrent)
    }

    func testObjectCommitAdvancesThreeDurableStagesWithOneImmutableIdentity() async throws {
        let value = try objectIntent(), wire = PreparedMigrationWire(try objectIntent())
        let client = try service(value, wire)
        let prepared = try await client.prepare(value, authorize: {})
        XCTAssertEqual(prepared.stage, .rootPrepared)
        XCTAssertEqual(prepared.recordIDs, [])
        let complete = try await client.commit(prepared, authorize: {})
        XCTAssertTrue(complete.isCompleteAndCurrent)
        XCTAssertEqual(complete.objectID, prepared.objectID)
        XCTAssertEqual(complete.fingerprint, prepared.fingerprint)
        XCTAssertEqual(complete.recordIDs, [try XCTUnwrap(prepared.objectID)])
        XCTAssertNotEqual(complete.changeID, prepared.changeID)
        let calls = await wire.snapshot(), posts = calls.filter { $0.method == "POST" }
        XCTAssertEqual(posts.count, 3)
        let firstBody = try XCTUnwrap(posts.first?.body)
        XCTAssertEqual(posts.map(\.body), Array(repeating: Optional(firstBody), count: 3))
        XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        let again = try await client.commit(prepared, authorize: {})
        XCTAssertEqual(again, complete)
        let finalCalls = await wire.snapshot()
        XCTAssertEqual(finalCalls.filter { $0.method == "POST" }.count, 3)
    }

    func testObjectResumeUsesOnlyRemainingStagesAndLostAcknowledgementNeverCreatesAnotherRoot() async throws {
        for persistedStage in [1, 2] {
            let value = try objectIntent(), wire = PreparedMigrationWire(try objectIntent())
            let client = try service(value, wire)
            let prepared = try await client.prepare(value, authorize: {})
            await wire.resumeAtObjectStage(persistedStage)
            let complete = try await client.commit(prepared, authorize: {})
            XCTAssertTrue(complete.isCompleteAndCurrent)
            XCTAssertEqual(complete.objectID, prepared.objectID)
            let calls = await wire.snapshot()
            XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 3 - persistedStage)
            XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        }
        let value = try objectIntent(), wire = PreparedMigrationWire(try objectIntent())
        let client = try service(value, wire)
        let prepared = try await client.prepare(value, authorize: {})
        await wire.loseNextCommitAcknowledgement()
        do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Lost root ACK was acknowledged") }
        catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        let persisted = try await client.status(value, authorize: {})
        XCTAssertEqual(persisted.stage, .rootCommitted)
        XCTAssertEqual(persisted.changeID, prepared.changeID)
        let completed = try await client.commit(prepared, authorize: {})
        XCTAssertTrue(completed.isCompleteAndCurrent)
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 3)
        XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
    }

    func testObjectCommitRefusesNoProgressAndRegressingStagesWithoutRetryLoop() async throws {
        for (currentStage, returnedStage) in [(0, 0), (2, 1)] {
            let value = try objectIntent(), wire = PreparedMigrationWire(try objectIntent())
            let client = try service(value, wire)
            let prepared = try await client.prepare(value, authorize: {})
            await wire.resumeAtObjectStage(currentStage)
            await wire.forceNextObjectStage(returnedStage)
            do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Nonmonotonic stage was accepted") }
            catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .incompleteCommit) }
            let calls = await wire.snapshot()
            XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 1)
        }
    }

    func testObjectStagesRecheckOwnerAndPersistentStoreBeforeTheNextWrite() async throws {
        let value = try objectIntent(), gate = PreparedMigrationAuthority()
        let wire = PreparedMigrationWire(value, afterCommit: { await gate.revoke() })
        let client = try service(value, wire)
        let prepared = try await client.prepare(value, authorize: { try await gate.check() })
        do { _ = try await client.commit(prepared, authorize: { try await gate.check() }); XCTFail("Retired owner continued") }
        catch { XCTAssertEqual(error as? AnyEngineError, .accountChanged) }
        let revokedCalls = await wire.snapshot()
        XCTAssertEqual(revokedCalls.filter { $0.method == "POST" }.count, 1)

        let replacedWire = PreparedMigrationWire(value)
        let replacementClient = try service(value, replacedWire)
        let other = try await replacementClient.prepare(value, authorize: {})
        await replacedWire.replaceStoreAfterNextCommit()
        do { _ = try await replacementClient.commit(other, authorize: {}); XCTFail("Replacement store continued plan") }
        catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .changedStore) }
        let replacedCalls = await replacedWire.snapshot()
        XCTAssertEqual(replacedCalls.filter { $0.method == "POST" }.count, 1)
    }

    func testObjectStageCannotChangeItsFingerprintOrSignedRootIdentity() async throws {
        for changeFingerprint in [true, false] {
            let value = try objectIntent(), wire = PreparedMigrationWire(try objectIntent())
            let client = try service(value, wire)
            let prepared = try await client.prepare(value, authorize: {})
            await wire.corruptNextCommitIdentity(fingerprint: changeFingerprint)
            do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Changed stage identity was accepted") }
            catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .changedIntent) }
            let calls = await wire.snapshot()
            XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 1)
        }
    }

    private func binding(account: String = "account", space: String = "space", store: String = "persistent-store",
                         plan: String = String(repeating: "a", count: 64),
                         digest: String = String(repeating: "b", count: 64)) throws -> AnyPreparedMigrationPlanBinding {
        try .init(workspace: .init(accountID: account, spaceID: space), storeID: store, planID: plan, planSHA256: digest)
    }

    private func intent(sourceKey: String = "source-block", planDigest: String = String(repeating: "b", count: 64),
                        text: String = "hello") throws -> AnyPreparedMigrationIntent {
        try .block(binding: binding(digest: planDigest), sourceKey: sourceKey,
            objectID: "target-object", type: "paragraph", text: text, position: "a0")
    }

    private func objectIntent() throws -> AnyPreparedMigrationIntent {
        try .object(binding: binding(), sourceKey: "source-object",
                    typeID: "type-page", initialProperties: .object([:]))
    }

    private func service(_ value: AnyPreparedMigrationIntent, _ wire: PreparedMigrationWire) throws -> AnyNativePreparedMigration {
        try .init(capabilities: .init(PreparedMigrationWire.capabilities(value), workspace: value.binding.workspace),
            request: { method, path, body, authorize in
                try await authorize()
                return try await wire.request(method: method, path: path, body: body)
            })
    }
}

private actor PreparedMigrationAuthority {
    private var allowed = true
    func revoke() { allowed = false }
    func check() throws { if !allowed { throw AnyEngineError.accountChanged } }
}

private actor PreparedMigrationWire {
    struct Call: Sendable { let method: String; let path: [String]; let body: AnyJSON? }
    private let intent: AnyPreparedMigrationIntent
    private let afterPrepare: (@Sendable () async -> Void)?
    private let afterCommit: (@Sendable () async -> Void)?
    private var calls: [Call] = []
    private var outcome = "prepared"
    private var fingerprint = String(repeating: "c", count: 64)
    private var changedStore = false
    private var loseAcknowledgement = false
    private var objectStage = 0
    private var forcedObjectStage: Int?
    private var replaceStoreAfterCommit = false
    private var corruptFingerprint = false
    private var corruptChangeID = false

    init(_ intent: AnyPreparedMigrationIntent, afterPrepare: (@Sendable () async -> Void)? = nil,
         afterCommit: (@Sendable () async -> Void)? = nil) {
        self.intent = intent; self.afterPrepare = afterPrepare; self.afterCommit = afterCommit
    }
    func snapshot() -> [Call] { calls }
    func setOutcome(_ value: String) { outcome = value }
    func changeStore() { changedStore = true }
    func changeFingerprint() { fingerprint = String(repeating: "d", count: 64) }
    func loseNextCommitAcknowledgement() { loseAcknowledgement = true }
    func resumeAtObjectStage(_ value: Int) {
        objectStage = value; outcome = value == 3 ? "committed" : "prepared"
    }
    func forceNextObjectStage(_ value: Int) { forcedObjectStage = value }
    func replaceStoreAfterNextCommit() { replaceStoreAfterCommit = true }
    func corruptNextCommitIdentity(fingerprint: Bool) {
        corruptFingerprint = fingerprint; corruptChangeID = !fingerprint
    }

    func request(method: String, path: [String], body: AnyJSON?) async throws -> AnyJSON {
        calls.append(.init(method: method, path: path, body: body))
        if path.last == "capabilities" {
            var value = Self.capabilities(intent).object!
            if changedStore { value["storeId"] = .string("replaced-store") }
            return .object(value)
        }
        if method == "PUT" { await afterPrepare?() }
        if method == "POST" {
            if intent.kind == .object {
                objectStage = forcedObjectStage ?? min(objectStage + 1, 3)
                outcome = objectStage == 3 ? "committed" : "prepared"
            } else { outcome = "committed" }
            if replaceStoreAfterCommit { changedStore = true }
            if corruptFingerprint { fingerprint = String(repeating: "d", count: 64) }
            await afterCommit?()
            if loseAcknowledgement { loseAcknowledgement = false; throw AnyEngineError.writeUncertain }
        }
        var value = Self.receipt(intent, stage: objectStage).object!
        value["fingerprint"] = .string(fingerprint)
        value["outcome"] = .string(outcome)
        if method == "POST" && corruptChangeID { value["changeId"] = .string("another-signed-change") }
        if outcome.hasPrefix("committed") { value["stage"] = .string("complete") }
        return .object(value)
    }

    static func capabilities(_ intent: AnyPreparedMigrationIntent) -> AnyJSON { .object([
        "contract": .string(AnyNativePreparedMigration.contract), "storeId": .string(intent.binding.storeID),
        "accountId": .string(intent.binding.workspace.accountID), "spaceId": .string(intent.binding.workspace.spaceID),
        "object": .integer(1), "editorBlock": .integer(1), "file": .integer(0), "networkVerified": .bool(false)
    ]) }

    static func receipt(_ intent: AnyPreparedMigrationIntent, stage: Int = 0) -> AnyJSON {
        let isObject = intent.kind == .object
        let stageName = isObject ? ["root-prepared", "root-committed", "bootstrap-prepared", "complete"][stage] : "block-prepared"
        let change = isObject ? (stage < 2 ? "original-signed-root" : "original-signed-bootstrap") : "original-signed-change"
        let records: [AnyJSON] = isObject ? (stage < 2 ? [] : [.string("target-object")]) : [.string("original-derived-record")]
        return .object([
        "contract": .string(AnyNativePreparedMigration.contract), "intentId": .string(intent.intentID),
        "storeId": .string(intent.binding.storeID), "accountId": .string(intent.binding.workspace.accountID),
        "spaceId": .string(intent.binding.workspace.spaceID), "planId": .string(intent.binding.planID),
        "planSHA256": .string(intent.binding.planSHA256), "sourceKey": .string(intent.sourceKey),
        "kind": .string(intent.kind.rawValue), "specSHA256": .string(intent.specSHA256),
        "fingerprint": .string(String(repeating: "c", count: 64)), "stage": .string(stageName),
        "outcome": .string("prepared"), "objectId": .string("target-object"),
        "changeId": .string(change), "recordIds": .array(records)
    ])
    }
}
