import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativePreparedImmutableRecordTests: XCTestCase, @unchecked Sendable {
    private func binding() throws -> AnyPreparedMigrationPlanBinding {
        try .init(workspace: .init(accountID: "account", spaceID: "space"), storeID: "store",
            planID: String(repeating: "a", count: 64), planSHA256: String(repeating: "b", count: 64))
    }
    private func intent(source: String = "source-facts", schema: AnyJSON = ImmutableRecordWire.schema,
                        values: [String: AnyJSON] = ["value": .string("מקור")]) throws -> AnyPreparedImmutableRecordIntent {
        try .init(binding: binding(), sourceKey: source, objectID: "object",
            schema: .init(schema, ownerTypeID: "owner", dataset: "owner_facts"), values: values)
    }
    private func service(_ wire: ImmutableRecordWire) throws -> AnyNativePreparedImmutableRecord {
        .init(capabilities: try .init(ImmutableRecordWire.capabilities, workspace: binding().workspace),
            request: { method, path, body, query, authorize in
                try await authorize()
                return try await wire.send(method: method, path: path, body: body, query: query)
            })
    }
    func testNativeSchemaRefusesMutableDeleteDynamicForeignAndCallerStampDeclarations() throws {
        let original = ImmutableRecordWire.schema
        for (key, value) in [("contract", AnyJSON.string("foreign")), ("ownerTypeId", .string("other")),
                             ("dataset", .string("other_facts")), ("schemaSHA256", .string("bad"))] {
            var bad = original.object!; bad[key] = value
            XCTAssertThrowsError(try intent(schema: .object(bad)), key)
        }
        for (key, value) in [("additionalProperties", AnyJSON.bool(true)), ("x-delete-by", .string("anyone")),
                             ("x-id", .string("user")), ("future-policy", .bool(true))] {
            var bad = original.object!, declaration = original["schema"]!.object!
            declaration[key] = value; bad["schema"] = .object(declaration)
            XCTAssertThrowsError(try intent(schema: .object(bad)), key)
        }
        for (key, value) in [("x-mutable-by", AnyJSON.string("any")), ("x-additive", .bool(true)),
                             ("x-scope", .string("local")), ("x-stamp", .string("modifyTime"))] {
            var bad = original.object!, declaration = original["schema"]!.object!
            var fields = declaration["properties"]!.object!, field = fields["value"]!.object!
            field[key] = value; fields["value"] = .object(field); declaration["properties"] = .object(fields)
            bad["schema"] = .object(declaration)
            XCTAssertThrowsError(try intent(schema: .object(bad)), key)
        }
    }
    func testExactSchemaSourceAndValuesBindOneIntentAndRejectForgedInput() throws {
        let original = try intent()
        var changed = ImmutableRecordWire.schema.object!; changed["schemaSHA256"] = .string(String(repeating: "f", count: 64))
        let newer = try intent(schema: .object(changed))
        XCTAssertEqual(original.intentID, newer.intentID); XCTAssertNotEqual(original.specSHA256, newer.specSHA256)
        XCTAssertNotEqual(try intent(source: "\u{e9}").intentID, try intent(source: "e\u{301}").intentID)
        for values: [String: AnyJSON] in [[:], ["extra": .string("x")],
            ["value": .string("x"), "by": .string("forged")],
            ["value": .string("x"), "at": .integer(1)], ["value": .number(.infinity)]] {
            XCTAssertThrowsError(try intent(values: values))
        }
        let decoded = try JSONDecoder().decode(AnyJSON.self, from: original.specBytes)
        XCTAssertEqual(decoded["schemaSHA256"]?.string, original.schema.nativeSHA256)
        XCTAssertEqual(decoded["values"], .object(["value": .string("מקור")]))
    }
    func testLostAcknowledgementReconcilesExactRecordWithoutSecondAppend() async throws {
        let original = try intent(), wire = ImmutableRecordWire(try intent()), first = try service(wire)
        let prepared = try await first.prepare(original, authorize: {})
        await wire.loseNextACK()
        do { _ = try await first.commit(prepared, authorize: {}); XCTFail("Lost ACK cannot report success") }
        catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        let reopened = try service(wire), complete = try await reopened.commit(prepared, authorize: {})
        XCTAssertTrue(complete.isCompleteAndCurrent); XCTAssertEqual(complete.recordIDs, prepared.recordIDs)
        XCTAssertEqual(complete.changeID, prepared.changeID)
        let posts = await wire.posts; XCTAssertEqual(posts, 1)
    }
    func testChangedSchemaStoreAndSignedIdentityRefuseBeforeAnotherMutation() async throws {
        for mode in ["schema", "store", "record", "change", "terminal"] {
            let original = try intent(), wire = ImmutableRecordWire(try intent()), client = try service(wire)
            let prepared = try await client.prepare(original, authorize: {})
            await wire.change(mode)
            do { _ = try await client.commit(prepared, authorize: {}); XCTFail("Changed native authority accepted: " + mode) }
            catch { }
            let posts = await wire.posts; XCTAssertEqual(posts, 0)
        }
    }
    func testCheckpointPreservesFullNativeSchemaAndOldNilEncoding() throws {
        let original = try intent()
        let entry = AnyDestinationJournalEntry(index: 0, sourceKey: original.sourceKey,
            itemSHA256: String(repeating: "a", count: 64), resolvedOperation: Data("{}".utf8),
            expectedApplySequence: nil, inlineContent: nil, intentID: original.intentID,
            specBytes: original.specBytes, specSHA256: original.specSHA256, immutableRecordSchema: original.schema)
        let data = try AnyDestinationMigrationJournal.encoded(entry)
        let restored = try JSONDecoder().decode(AnyDestinationJournalEntry.self, from: data)
        XCTAssertEqual(restored.immutableRecordSchema, original.schema)
        XCTAssertEqual(try AnyDestinationMigrationJournal.encoded(restored), data)
        let old = AnyDestinationJournalEntry(index: 0, sourceKey: original.sourceKey,
            itemSHA256: String(repeating: "a", count: 64), resolvedOperation: Data("{}".utf8),
            expectedApplySequence: nil, inlineContent: nil, intentID: original.intentID,
            specBytes: original.specBytes, specSHA256: original.specSHA256)
        let oldJSON = try JSONDecoder().decode(AnyJSON.self, from: AnyDestinationMigrationJournal.encoded(old))
        XCTAssertNil(oldJSON["immutableRecordSchema"])
    }
    func testReadbackComparesSourceFactsAndRequiresActualDerivedStamps() throws {
        let original = try intent()
        let row: AnyJSON = .object(["id": .string("record"), "value": .string("מקור"),
            "by": .string("native-signer"), "at": .object(["$date": .integer(1795642400000)])])
        let projection = try AnyDestinationMigrationVerifier.immutableRecordProjection(row, intent: original)
        XCTAssertEqual(projection["values"]?["value"], .string("מקור"))
        for key in ["value", "by", "at"] {
            var bad = row.object!; bad[key] = nil
            XCTAssertThrowsError(try AnyDestinationMigrationVerifier.immutableRecordProjection(.object(bad), intent: original), key)
        }
        var bad = row.object!; bad["value"] = .string("changed")
        XCTAssertThrowsError(try AnyDestinationMigrationVerifier.immutableRecordProjection(.object(bad), intent: original))
    }
    func testPlanRequiresOwnedImmutableDeclarationAndMatchingObjectType() throws {
        func plan(dynamic: Bool = false, wrongType: Bool = false) throws -> AnyDestinationMigrationPlan {
            let type: AnyDestinationReference = .mapped(sourceKey: "type", slot: .objectID, encoding: .rawID)
            let object: AnyDestinationReference = .mapped(sourceKey: "object", slot: .objectID, encoding: .rawID)
            let draft: AnyJSON = .object(["key": .string("facts"), "datasets": .array([.object([
                "key": .string("facts"), "module": .string("records"), "dynamic": .bool(dynamic),
                "deleteBy": .string("none"), "fields": .array([.object([
                    "key": .string("value"), "kind": .string("string"), "required": .bool(true)
                ])])
            ])])])
            let items: [AnyDestinationMigrationItem] = [
                .init(sourceKey: "type", sourceObjectID: "source-type", operation: .typeDefinition(.init(xKey: "immutable_type", name: "Original"))),
                .init(sourceKey: "part", sourceObjectID: "source-type", expectedRecordCount: 3, operation: .partDefinition(owner: type, draft: .literal(draft))),
                .init(sourceKey: "object", sourceObjectID: "source-object", operation: .object(type: wrongType ? .native("page") : type, collections: [], initialProperties: .literal(.object([:])))),
                .init(sourceKey: "facts", sourceObjectID: "source-object", operation: .immutableRecord(object: object, ownerType: type, datasetKey: "facts", values: .literal(.object(["value": .string("source")]))))
            ]
            let b = try binding()
            return try .init(source: .init(accountID: "source-account", spaceID: "source-space",
                witnessSHA256: String(repeating: "c", count: 64), captureManifestSHA256: String(repeating: "d", count: 64),
                semanticPlanSHA256: String(repeating: "e", count: 64), sourceObjectIDs: ["source-type", "source-object"]),
                workspace: b.workspace, storeID: b.storeID, planID: b.planID,
                coverage: [.init(sourceObjectID: "source-type", disposition: .mapped(itemSourceKeys: ["type", "part"])),
                           .init(sourceObjectID: "source-object", disposition: .mapped(itemSourceKeys: ["object", "facts"]))],
                items: items)
        }
        let good = try plan(); XCTAssertTrue(good.blockers.isEmpty)
        XCTAssertThrowsError(try plan(dynamic: true))
        XCTAssertThrowsError(try plan(wrongType: true))
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        XCTAssertEqual(try AnyDestinationMigrationPlan.decode(encoder.encode(good)).canonicalBytes, good.canonicalBytes)
    }
}

private actor ImmutableRecordWire {
    static let capabilities: AnyJSON = .object([
        "contract": .string(AnyNativePreparedImmutableRecord.contract), "storeId": .string("store"),
        "accountId": .string("account"), "spaceId": .string("space"), "immutableRecord": .integer(1),
        "maxFields": .integer(128), "networkVerified": .bool(false)
    ])
    static let schema: AnyJSON = .object([
        "contract": .string(AnyNativePreparedImmutableRecord.contract), "ownerTypeId": .string("owner"),
        "dataset": .string("owner_facts"), "schemaSHA256": .string(String(repeating: "c", count: 64)),
        "schema": .object(["type": .string("object"), "additionalProperties": .bool(false),
            "x-delete-by": .string("none"), "required": .array([.string("value")]), "properties": .object([
                "value": .object(["type": .string("string"), "x-scope": .string("synced")]),
                "by": .object(["type": .string("string"), "x-scope": .string("derived"), "x-stamp": .string("creator")]),
                "at": .object(["type": .string("datetime"), "x-scope": .string("derived"), "x-stamp": .string("createTime")])
            ])])
    ])
    let intent: AnyPreparedImmutableRecordIntent
    var complete = false, loseACK = false, mode = ""
    var posts = 0
    init(_ intent: AnyPreparedImmutableRecordIntent) { self.intent = intent }
    func loseNextACK() { loseACK = true }
    func change(_ value: String) { mode = value }
    func send(method: String, path: [String], body: AnyJSON?, query: [String: String]) throws -> AnyJSON {
        if path.last == "capabilities" {
            var result = Self.capabilities.object!
            if mode == "store" { result["storeId"] = .string("other") }
            return .object(result)
        }
        if path.last == "schema" {
            guard query == ["ownerTypeId": "owner", "dataset": "owner_facts"] else { throw AnyHostError.wrongWorkspace }
            var result = Self.schema.object!
            if mode == "schema" { result["schemaSHA256"] = .string(String(repeating: "f", count: 64)) }
            return .object(result)
        }
        if method == "POST" {
            posts += 1; complete = true
            if loseACK { loseACK = false; throw AnyEngineError.writeUncertain }
        }
        return .object([
            "contract": .string(AnyNativePreparedImmutableRecord.contract), "intentId": .string(intent.intentID),
            "storeId": .string("store"), "accountId": .string("account"), "spaceId": .string("space"),
            "planId": .string(intent.binding.planID), "planSHA256": .string(intent.binding.planSHA256),
            "sourceKey": .string(intent.sourceKey), "kind": .string("immutableRecord"), "specSHA256": .string(intent.specSHA256),
            "fingerprint": .string(String(repeating: "d", count: 64)),
            "objectId": .string(intent.objectID), "changeId": .string(mode == "change" ? "changed" : "signed"),
            "recordIds": .array([.string(mode == "record" ? "changed" : "record")]),
            "stage": .string(complete ? "complete" : "immutable-record-prepared"),
            "outcome": .string(mode == "terminal" ? "obsolete" : (complete ? "committed" : "prepared"))
        ])
    }
}
