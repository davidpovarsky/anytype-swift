import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativePreparedDefinitionMigrationTests: XCTestCase, @unchecked Sendable {
    private func binding(digest: String = String(repeating: "b", count: 64)) throws -> AnyPreparedMigrationPlanBinding {
        try .init(workspace: .init(accountID: "account", spaceID: "space"), storeID: "store",
                  planID: String(repeating: "a", count: 64), planSHA256: digest)
    }
    private func root(source: String = "source-type", name: String = "סוג מסמך") throws -> AnyPreparedDefinitionIntent {
        try .type(binding: binding(), sourceKey: source, xKey: "migrated_type", name: name,
                  layout: .object(["type": .string("page")]), meta: .object(["vendor-owner": .string("source")]))
    }
    private func service(_ intent: AnyPreparedDefinitionIntent, _ wire: DefinitionWire) throws -> AnyNativePreparedDefinitionMigration {
        .init(capabilities: try .init(DefinitionWire.capabilities(intent), workspace: intent.binding.workspace),
              request: { method, path, body, authorize in
                  try await authorize()
                  return try await wire.send(method: method, path: path, body: body)
              })
    }

    func testLogicalIdentityAndExactSpecificationRemainSeparate() throws {
        let a = try root(), b = try root(name: "Changed"), c = try AnyPreparedDefinitionIntent.type(
            binding: binding(digest: String(repeating: "c", count: 64)), sourceKey: a.sourceKey,
            xKey: "migrated_type", name: "סוג מסמך", layout: .object(["type": .string("page")]),
            meta: .object(["vendor-owner": .string("source")]))
        XCTAssertEqual(a.intentID, b.intentID); XCTAssertEqual(a.intentID, c.intentID)
        XCTAssertNotEqual(a.specSHA256, b.specSHA256); XCTAssertEqual(a.specSHA256, c.specSHA256)
        let collection = try AnyPreparedDefinitionIntent.collection(binding: binding(),
            sourceKey: a.sourceKey, xKey: "migrated_type", name: "סוג מסמך")
        XCTAssertNotEqual(a.intentID, collection.intentID)
        let nfc = try root(source: "\u{e9}"), nfd = try root(source: "e\u{301}")
        XCTAssertNotEqual(nfc.intentID, nfd.intentID)
        let spec = try XCTUnwrap(a.prepareBody["specBase64"]?.string.flatMap { Data(base64Encoded: $0) })
        XCTAssertEqual(spec, a.specBytes); XCTAssertEqual(AnyContentDigest.sha256(spec), a.specSHA256)
        let decoded = try JSONDecoder().decode(AnyJSON.self, from: spec)
        XCTAssertEqual(decoded["type"]?["name"]?.string, "סוג מסמך")
        XCTAssertNil(decoded["ownerObjectId"]); XCTAssertNil(decoded["objectId"])
    }

    func testSeedsRefuseUnboundedOrForeignCreationFields() throws {
        let b = try binding()
        XCTAssertThrowsError(try AnyPreparedDefinitionIntent.type(binding: b, sourceKey: "s", xKey: "", name: "x"))
        XCTAssertThrowsError(try AnyPreparedDefinitionIntent.type(binding: b, sourceKey: "s", xKey: "x", name: "x",
                                                                 meta: .object(["a.b": .bool(true)])))
        XCTAssertThrowsError(try AnyPreparedDefinitionIntent.type(binding: b, sourceKey: "s", xKey: "x", name: "x",
                                                                 meta: .object(["a": .array([])])))
        XCTAssertThrowsError(try AnyPreparedDefinitionIntent.type(binding: b, sourceKey: "s", xKey: "x", name: "x",
                                                                 layout: .array([])))
        XCTAssertThrowsError(try AnyPreparedDefinitionIntent.property(binding: b, sourceKey: "s", ownerID: "",
                                                                     kind: .string, name: "x"))
        XCTAssertThrowsError(try AnyPreparedDefinitionIntent.part(binding: b, sourceKey: "s", ownerID: "type",
            draft: .object(["key": .string("editor"), "replacementId": .string("forged")])) )
        XCTAssertThrowsError(try AnyPreparedDefinitionIntent.collection(binding: b, sourceKey: "s", xKey: "x",
                                                                        name: String(repeating: "x", count: 262_145)))
    }

    func testReceiptBindsEveryIdentityAndNativeStage() throws {
        let intent = try root(), good = DefinitionWire.receipt(try root(), phase: 0)
        for key in ["contract", "intentId", "storeId", "accountId", "spaceId", "planId", "planSHA256",
                    "sourceKey", "kind", "specSHA256", "fingerprint", "stage", "outcome"] {
            var changed = good.object!; changed[key] = .string("wrong")
            XCTAssertThrowsError(try AnyPreparedDefinitionReceipt(.object(changed), intent: intent), key)
        }
        var changed = good.object!; changed["recordIds"] = .array([.string("forged")])
        XCTAssertThrowsError(try AnyPreparedDefinitionReceipt(.object(changed), intent: intent))
        changed = good.object!; changed["changeId"] = .string("other-root")
        XCTAssertThrowsError(try AnyPreparedDefinitionReceipt(.object(changed), intent: intent))
        changed = good.object!; changed["stage"] = .string("complete")
        XCTAssertThrowsError(try AnyPreparedDefinitionReceipt(.object(changed), intent: intent))
        let nfc = try root(source: "\u{e9}")
        changed = DefinitionWire.receipt(nfc, phase: 0).object!; changed["sourceKey"] = .string("e\u{301}")
        XCTAssertThrowsError(try AnyPreparedDefinitionReceipt(.object(changed), intent: nfc))
    }

    func testThreeRootStagesAndLostAcknowledgementKeepOriginalIDs() async throws {
        let intent = try root(), wire = DefinitionWire(try root())
        let client = try service(intent, wire)
        let prepared = try await client.prepare(intent, authorize: {})
        await wire.loseAcknowledgement(at: 1)
        do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Lost ACK became success") }
        catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        let reopened = try service(intent, wire)
        let complete = try await reopened.commit(prepared, authorize: {})
        XCTAssertTrue(complete.isCompleteAndCurrent)
        XCTAssertEqual(complete.objectID, prepared.objectID)
        XCTAssertEqual(complete.recordIDs, [prepared.objectID])
        let again = try await reopened.commit(prepared, authorize: {})
        XCTAssertEqual(again, complete)
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 3)
        XCTAssertEqual(calls.first { $0.method == "PUT" }?.body, intent.prepareBody)
        XCTAssertEqual(calls.first { $0.method == "POST" }.map { Array($0.path.suffix(2)) }, ["definition", "commit"])
    }

    func testPropertyAndAtomicPartReuseCompleteOrderedRecordIDs() async throws {
        let intents = [
            try AnyPreparedDefinitionIntent.property(binding: binding(), sourceKey: "property", ownerID: "mapped-type",
                kind: .string, name: "שם", xKey: "original_property", xFormat: .object(["type": .string("text")])),
            try AnyPreparedDefinitionIntent.part(binding: binding(), sourceKey: "part", ownerID: "mapped-type",
                draft: .object(["key": .string("editor"), "datasets": .array([])]))
        ]
        for intent in intents {
            let wire = DefinitionWire(intent)
            let actual = try service(intent, wire)
            let prepared = try await actual.prepare(intent, authorize: {})
            let done = try await actual.commit(prepared, authorize: {})
            XCTAssertTrue(done.isCompleteAndCurrent)
            XCTAssertEqual(done.objectID, "mapped-type"); XCTAssertEqual(done.recordIDs, prepared.recordIDs)
            XCTAssertEqual(done.changeID, prepared.changeID)
            let calls = await wire.snapshot(); XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 1)
        }
    }

    func testChangedStoreOrMissingPartCapabilityStopsBeforeMutation() async throws {
        let intent = try root(), wire = DefinitionWire(try root())
        let actual = try service(intent, wire)
        await wire.changeStore()
        do { _ = try await actual.prepare(intent, authorize: {}); XCTFail("Changed store accepted") }
        catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .changedStore) }
        let calls = await wire.snapshot(); XCTAssertEqual(calls.filter { $0.method != "GET" }.count, 0)
        let part = try AnyPreparedDefinitionIntent.part(binding: binding(), sourceKey: "part", ownerID: "mapped-type",
                                                      draft: .object(["key": .string("editor")]))
        let noParts = DefinitionWire(part); await noParts.disableParts()
        let partClient = try service(part, noParts)
        do { _ = try await partClient.prepare(part, authorize: {}); XCTFail("Unadvertised part accepted") }
        catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .unsupportedContract) }
        let partCalls = await noParts.snapshot(); XCTAssertEqual(partCalls.filter { $0.method != "GET" }.count, 0)
    }

    func testTerminalOutcomesAndChangedBatchCannotRecreateDefinitions() async throws {
        for outcome in ["committed_deleted", "committed_modified", "obsolete"] {
            let intent = try root(), wire = DefinitionWire(try root())
            let client = try service(intent, wire)
            let prepared = try await client.prepare(intent, authorize: {})
            await wire.terminal(outcome)
            do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Terminal definition overwritten") }
            catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .terminalOutcome(outcome)) }
            let calls = await wire.snapshot(); XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 0)
        }
        let part = try AnyPreparedDefinitionIntent.part(binding: binding(), sourceKey: "part", ownerID: "mapped-type",
                                                      draft: .object(["key": .string("editor")]))
        let wire = DefinitionWire(part)
        let actual = try service(part, wire)
        let prepared = try await actual.prepare(part, authorize: {})
        await wire.reorderRecords()
        do { _ = try await actual.commit(prepared, authorize: {}); XCTFail("Reordered signed IDs accepted") }
        catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .changedIntent) }
        let calls = await wire.snapshot(); XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 0)
    }

    func testRevokedOwnerAfterDispatchCannotPublishReceipt() async throws {
        let intent = try root(), wire = DefinitionWire(try root()), gate = DefinitionAuthority()
        let client = AnyNativePreparedDefinitionMigration(capabilities:
            try .init(DefinitionWire.capabilities(intent), workspace: intent.binding.workspace),
            request: { method, path, body, authorize in
                try await authorize()
                let result = try await wire.send(method: method, path: path, body: body)
                if method == "PUT" { await gate.revoke() }
                return result
            })
        do { _ = try await client.prepare(intent, authorize: { try await gate.check() }); XCTFail("Revoked receipt published") }
        catch { XCTAssertEqual(error as? AnyHostError, .wrongWorkspace) }
        let calls = await wire.snapshot()
        XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 0)
    }
}

private actor DefinitionAuthority {
    var active = true
    func revoke() { active = false }
    func check() throws { if !active { throw AnyHostError.wrongWorkspace } }
}

private actor DefinitionWire {
    struct Call: Sendable { let method: String; let path: [String]; let body: AnyJSON? }
    let intent: AnyPreparedDefinitionIntent
    var phase = 0, calls: [Call] = [], lostAt: Int?, terminalOutcome: String?, changedStore = false
    var parts = true, reversed = false
    init(_ intent: AnyPreparedDefinitionIntent) { self.intent = intent }
    func snapshot() -> [Call] { calls }
    func loseAcknowledgement(at phase: Int) { lostAt = phase }
    func changeStore() { changedStore = true }
    func disableParts() { parts = false }
    func reorderRecords() { reversed = true }
    func terminal(_ outcome: String) { terminalOutcome = outcome; phase = outcome == "obsolete" ? 0 : 3 }
    static func capabilities(_ intent: AnyPreparedDefinitionIntent) -> AnyJSON { .object([
        "contract": .string(AnyNativePreparedDefinitionMigration.contract),
        "accountId": .string(intent.binding.workspace.accountID), "spaceId": .string(intent.binding.workspace.spaceID),
        "storeId": .string(intent.binding.storeID), "typeDefinition": .integer(1),
        "collectionDefinition": .integer(1), "propertyDefinition": .integer(1), "partDefinition": .integer(1),
        "networkVerified": .bool(false)
    ]) }
    static func receipt(_ intent: AnyPreparedDefinitionIntent, phase: Int,
                        outcome: String? = nil, reversed: Bool = false) -> AnyJSON {
        let root = intent.kind == .typeDefinition || intent.kind == .collectionDefinition
        let object = intent.expectedOwnerID ?? "native-definition-root"
        let stage = root ? ["definition-root-prepared", "definition-root-committed",
                            "definition-bootstrap-prepared", "complete"][phase] :
            (phase == 3 ? "complete" : intent.kind == .propertyDefinition ? "definition-property-prepared" : "definition-part-prepared")
        var records = root ? (phase < 2 ? [] : [object]) :
            (intent.kind == .propertyDefinition ? ["native-property"] : ["native-part", "native-dataset", "native-field", "native-index"])
        if reversed { records.reverse() }
        return .object([
            "contract": .string(AnyNativePreparedDefinitionMigration.contract), "intentId": .string(intent.intentID),
            "accountId": .string(intent.binding.workspace.accountID), "spaceId": .string(intent.binding.workspace.spaceID),
            "storeId": .string(intent.binding.storeID), "planId": .string(intent.binding.planID),
            "planSHA256": .string(intent.binding.planSHA256), "sourceKey": .string(intent.sourceKey),
            "kind": .string(intent.kind.rawValue), "specSHA256": .string(intent.specSHA256),
            "fingerprint": .string(String(repeating: "d", count: 64)), "stage": .string(stage),
            "outcome": .string(outcome ?? (phase == 3 ? "committed" : "prepared")),
            "objectId": .string(object), "changeId": .string(root && phase < 2 ? object : "native-signed-change"),
            "recordIds": .array(records.map(AnyJSON.string))
        ])
    }
    func send(method: String, path: [String], body: AnyJSON?) throws -> AnyJSON {
        calls.append(.init(method: method, path: path, body: body))
        if path.last == "capabilities" {
            var value = Self.capabilities(intent).object!
            if changedStore { value["storeId"] = .string("other-store") }
            if !parts { value["partDefinition"] = nil }
            return .object(value)
        }
        if method == "POST" {
            phase = intent.kind == .typeDefinition || intent.kind == .collectionDefinition ? min(phase + 1, 3) : 3
            if lostAt == phase { lostAt = nil; throw AnyEngineError.writeUncertain }
        }
        return Self.receipt(intent, phase: phase, outcome: terminalOutcome, reversed: reversed)
    }
}
