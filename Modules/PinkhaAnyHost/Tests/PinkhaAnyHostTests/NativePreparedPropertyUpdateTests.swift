import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativePreparedPropertyUpdateTests: XCTestCase, @unchecked Sendable {
    private func binding() throws -> AnyPreparedMigrationPlanBinding {
        try .init(workspace: .init(accountID: "account", spaceID: "space"), storeID: "store",
                  planID: String(repeating: "a", count: 64), planSHA256: String(repeating: "b", count: 64))
    }
    private func intent(source: String = "original-reference-values", sequence: Int64 = 7,
                        patch: [String: AnyJSON] = ["links": .array([.string("any://destination-b")])]) throws -> AnyPreparedPropertyUpdateIntent {
        try .init(binding: binding(), sourceKey: source, objectID: "destination-a", ownerID: "mapped-type",
                  patch: patch, expectedApplySequence: sequence)
    }
    private func service(_ wire: PropertyUpdateWire) throws -> AnyNativePreparedPropertyUpdate {
        .init(capabilities: try .init(PropertyUpdateWire.capabilities, workspace: binding().workspace),
              request: { method, path, body, authorize in
                  try await authorize()
                  return try await wire.send(method: method, path: path, body: body)
              })
    }

    func testImmutableRevisionAndSourceBytesBindOneLogicalIntent() throws {
        let a = try intent(), revised = try intent(sequence: 8)
        let changed = try intent(patch: ["links": .array([.string("any://destination-c")])])
        XCTAssertEqual(a.intentID, revised.intentID); XCTAssertEqual(a.intentID, changed.intentID)
        XCTAssertNotEqual(a.specSHA256, revised.specSHA256); XCTAssertNotEqual(a.specSHA256, changed.specSHA256)
        XCTAssertNotEqual(try intent(source: "\u{e9}").intentID, try intent(source: "e\u{301}").intentID)
        let bytes = try XCTUnwrap(a.prepareBody["specBase64"]?.string.flatMap { Data(base64Encoded: $0) })
        XCTAssertEqual(bytes, a.specBytes); XCTAssertEqual(AnyContentDigest.sha256(bytes), a.specSHA256)
        let decoded = try JSONDecoder().decode(AnyJSON.self, from: bytes)
        XCTAssertEqual(Set(try XCTUnwrap(decoded.object).keys), ["objectId", "ownerId", "patch", "expectedApplySeq"])
        XCTAssertEqual(decoded["expectedApplySeq"]?.integer, 7)
        XCTAssertEqual(decoded["patch"]?["links"], .array([.string("any://destination-b")]))
        XCTAssertEqual(decoded["objectId"]?.string, "destination-a")
    }

    func testNonSetMembershipAndUnboundedPatchesAreRefusedBeforeDispatch() throws {
        let refused: [[String: AnyJSON]] = [[:], ["unset": .null], ["a.b": .string("x")], ["a\0b": .bool(true)],
            Dictionary(uniqueKeysWithValues: (0..<129).map { ("k\($0)", .bool(true)) })]
        for patch in refused {
            XCTAssertThrowsError(try intent(patch: patch))
        }
        for sequence in [Int64(0), Int64(-1)] { XCTAssertThrowsError(try intent(sequence: sequence)) }
        for field in ["type", "collections", "template"] {
            XCTAssertThrowsError(try AnyPreparedPropertyUpdateIntent(binding: binding(), sourceKey: "s",
                objectID: "destination-a", ownerID: "any", patch: [field: .array([])], expectedApplySequence: 7))
        }
        XCTAssertThrowsError(try intent(patch: ["body": .string(String(repeating: "x", count: 262_145))]))
        XCTAssertThrowsError(try intent(patch: ["value": .number(.infinity)]))
        XCTAssertNoThrow(try intent(patch: Dictionary(uniqueKeysWithValues: (0..<128).map { ("k\($0)", .bool(true)) })))
    }

    func testReceiptRejectsForeignIdentityStageAndCanonicalSourceAlias() throws {
        let original = try intent()
        let good = PropertyUpdateWire.receipt(original, complete: false)
        for key in ["contract", "intentId", "storeId", "accountId", "spaceId", "planId", "planSHA256",
                    "sourceKey", "kind", "specSHA256", "fingerprint", "stage", "outcome", "objectId"] {
            var changed = good.object!; changed[key] = .string("wrong")
            XCTAssertThrowsError(try AnyPreparedPropertyUpdateReceipt(.object(changed), intent: original), key)
        }
        let refusedRecords: [[AnyJSON]] = [[], [.string("other")], [.string(original.objectID), .string(original.objectID)]]
        for records in refusedRecords {
            var changed = good.object!; changed["recordIds"] = .array(records)
            XCTAssertThrowsError(try AnyPreparedPropertyUpdateReceipt(.object(changed), intent: original))
        }
        for (stage, outcome) in [("complete", "prepared"), ("properties-prepared", "committed"), ("complete", "obsolete")] {
            var changed = good.object!; changed["stage"] = .string(stage); changed["outcome"] = .string(outcome)
            XCTAssertThrowsError(try AnyPreparedPropertyUpdateReceipt(.object(changed), intent: original))
        }
        let nfc = try intent(source: "\u{e9}")
        var changed = PropertyUpdateWire.receipt(nfc, complete: false).object!
        changed["sourceKey"] = .string("e\u{301}")
        XCTAssertThrowsError(try AnyPreparedPropertyUpdateReceipt(.object(changed), intent: nfc))
    }

    func testLostCommitAcknowledgementResumesOriginalSignedChangeWithoutAnotherPost() async throws {
        let original = try intent(), wire = PropertyUpdateWire(try intent())
        let first = try service(wire), prepared = try await first.prepare(original, authorize: {})
        await wire.loseNextAcknowledgement()
        do { _ = try await first.commit(prepared, authorize: {}); XCTFail("Lost ACK reported success") }
        catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        let reopened = try service(wire)
        let complete = try await reopened.commit(prepared, authorize: {})
        XCTAssertTrue(complete.isCompleteAndCurrent)
        XCTAssertEqual(complete.objectID, original.objectID); XCTAssertEqual(complete.changeID, prepared.changeID)
        XCTAssertEqual(complete.recordIDs, [original.objectID])
        let repeated = try await reopened.commit(prepared, authorize: {})
        XCTAssertEqual(repeated, complete)
        let calls = await wire.calls()
        XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 1)
        XCTAssertEqual(calls.first { $0.method == "PUT" }?.body, original.prepareBody)
        XCTAssertEqual(calls.first { $0.method == "POST" }.map { Array($0.path.suffix(2)) }, ["property-update", "commit"])
    }

    func testTerminalFieldsAndChangedSignedIdentityCannotBeOverwritten() async throws {
        for outcome in ["committed_modified", "committed_deleted", "obsolete"] {
            let original = try intent(), wire = PropertyUpdateWire(try intent()), client = try service(wire)
            let prepared = try await client.prepare(original, authorize: {})
            await wire.setTerminal(outcome)
            do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Terminal field overwritten") }
            catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .terminalOutcome(outcome)) }
            let calls = await wire.calls(); XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 0)
        }
        for key in ["fingerprint", "changeId"] {
            let original = try intent(), wire = PropertyUpdateWire(try intent()), client = try service(wire)
            let prepared = try await client.prepare(original, authorize: {})
            await wire.replaceReceiptField(key, with: key == "fingerprint" ? String(repeating: "e", count: 64) : "replacement-change")
            do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Changed native identity accepted") }
            catch { XCTAssertEqual(error as? AnyPreparedMigrationError, .changedIntent) }
            let calls = await wire.calls(); XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 0)
        }
    }

    func testStoreCapabilityAndOwnerAuthorityAreRecheckedAtDispatchBoundaries() async throws {
        for mode in ["store", "capability"] {
            let original = try intent(), wire = PropertyUpdateWire(try intent()), client = try service(wire)
            await wire.changeCapability(mode)
            do { _ = try await client.prepare(original, authorize: {}); XCTFail("Changed capability mutated store") }
            catch { XCTAssertEqual(error as? AnyPreparedMigrationError, mode == "store" ? .changedStore : .unsupportedContract) }
            let calls = await wire.calls(); XCTAssertEqual(calls.filter { $0.method != "GET" }.count, 0)
        }
        let original = try intent(), wire = PropertyUpdateWire(try intent()), authority = PropertyUpdateAuthority()
        let client = AnyNativePreparedPropertyUpdate(capabilities:
            try .init(PropertyUpdateWire.capabilities, workspace: binding().workspace),
            request: { method, path, body, authorize in
                try await authorize()
                let receipt = try await wire.send(method: method, path: path, body: body)
                if method == "PUT" { await authority.revoke() }
                return receipt
            })
        do { _ = try await client.prepare(original, authorize: { try await authority.check() }); XCTFail("Revoked receipt published") }
        catch { XCTAssertEqual(error as? AnyHostError, .wrongWorkspace) }
        let calls = await wire.calls(); XCTAssertEqual(calls.filter { $0.method == "PUT" }.count, 1)
        XCTAssertEqual(calls.filter { $0.method == "POST" }.count, 0)
    }
}

private actor PropertyUpdateAuthority {
    var active = true
    func revoke() { active = false }
    func check() throws { if !active { throw AnyHostError.wrongWorkspace } }
}

private actor PropertyUpdateWire {
    struct Call: Sendable { let method: String; let path: [String]; let body: AnyJSON? }
    let intent: AnyPreparedPropertyUpdateIntent
    var recorded: [Call] = [], complete = false, loseACK = false
    var terminal: String?, capabilityMode: String?, replaced: (String, String)?
    init(_ intent: AnyPreparedPropertyUpdateIntent) { self.intent = intent }
    func calls() -> [Call] { recorded }
    func loseNextAcknowledgement() { loseACK = true }
    func setTerminal(_ outcome: String) { terminal = outcome; complete = outcome != "obsolete" }
    func changeCapability(_ mode: String) { capabilityMode = mode }
    func replaceReceiptField(_ key: String, with value: String) { replaced = (key, value) }
    static let capabilities: AnyJSON = .object([
        "contract": .string(AnyNativePreparedPropertyUpdate.contract), "accountId": .string("account"),
        "spaceId": .string("space"), "storeId": .string("store"), "propertyUpdate": .integer(1),
        "maxPatchKeys": .integer(128), "networkVerified": .bool(false)
    ])
    static func receipt(_ intent: AnyPreparedPropertyUpdateIntent, complete: Bool, terminal: String? = nil) -> AnyJSON { .object([
        "contract": .string(AnyNativePreparedPropertyUpdate.contract), "intentId": .string(intent.intentID),
        "storeId": .string(intent.binding.storeID), "accountId": .string(intent.binding.workspace.accountID),
        "spaceId": .string(intent.binding.workspace.spaceID), "planId": .string(intent.binding.planID),
        "planSHA256": .string(intent.binding.planSHA256), "sourceKey": .string(intent.sourceKey),
        "kind": .string("propertyUpdate"), "specSHA256": .string(intent.specSHA256),
        "fingerprint": .string(String(repeating: "d", count: 64)), "stage": .string(complete ? "complete" : "properties-prepared"),
        "outcome": .string(terminal ?? (complete ? "committed" : "prepared")),
        "objectId": .string(intent.objectID), "changeId": .string("original-signed-change"),
        "recordIds": .array([.string(intent.objectID)])
    ]) }
    func send(method: String, path: [String], body: AnyJSON?) throws -> AnyJSON {
        recorded.append(.init(method: method, path: path, body: body))
        if path.last == "capabilities" {
            var value = Self.capabilities.object!
            if capabilityMode == "store" { value["storeId"] = .string("other-store") }
            if capabilityMode == "capability" { value["propertyUpdate"] = nil }
            return .object(value)
        }
        if method == "POST" {
            complete = true
            if loseACK { loseACK = false; throw AnyEngineError.writeUncertain }
        }
        var value = Self.receipt(intent, complete: complete, terminal: terminal).object!
        if let (key, field) = replaced { value[key] = .string(field) }
        return .object(value)
    }
}
