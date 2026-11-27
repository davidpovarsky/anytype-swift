import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Synthetic plans qualify routing/refusal logic only. Their invented native
/// receipts cannot pass the production store's live immutable-intent check.
final class NativeImportedDefinitionDirectoryTests: XCTestCase {
    func testTypePropertyOptionAndCanonicalAddressesKeepDistinctNativeIdentities() throws {
        let (plan, mappings) = try fixture()
        let directory = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: mappings)
        XCTAssertEqual(directory.entries.count, 5)
        XCTAssertTrue(directory.unresolvedSourceDefinitionIDs.isEmpty)
        XCTAssertFalse(directory.permitsSourceAdmission)
        let type = try XCTUnwrap(directory.definition(sourceObjectID: "native-type"))
        guard case .type(let typeID) = type.address else { return XCTFail("Type address") }
        XCTAssertEqual(typeID, mappings.first { $0.kind == "typeDefinition" }?.objectID)
        let property = try XCTUnwrap(directory.definition(sourceObjectID: "relation-a\u{301}"))
        guard case .property(let kind, let key) = property.address else { return XCTFail("Property address") }
        XCTAssertEqual(kind, .collection)
        XCTAssertEqual(key.ownerID, mappings.first { $0.kind == "collectionDefinition" }?.objectID)
        XCTAssertEqual(key.propertyID, mappings.first { $0.kind == "propertyDefinition" }?.recordIDs[0])
        XCTAssertNil(directory.definition(sourceObjectID: "relation-\u{e1}"))
        for id in ["firstOption", "secondOption"] {
            let option = try XCTUnwrap(directory.definition(sourceObjectID: id))
            guard case .option(let optionKind, let optionKey, let optionID) = option.address else { return XCTFail("Option address") }
            XCTAssertEqual(optionKind, kind)
            XCTAssertEqual(optionKey, key)
            XCTAssertEqual(optionID, id)
            XCTAssertEqual(option.originalDescriptor["meta"]?["heartSourceObjectID"], .string(id))
            XCTAssertFalse(option.permitsDestinationWrites)
        }
        let canonical = try XCTUnwrap(directory.definition(sourceObjectID: "native-name"))
        XCTAssertEqual(canonical.address, .property(ownerKind: .type, key: try .init(ownerID: "any", propertyID: "name")))
        XCTAssertNil(canonical.intent)
        XCTAssertEqual(canonical.originalDescriptor["scope"], .string("synced"))
    }

    func testArchiveTypeAndPropertyNamespaceCannotBecomeOriginalDefinitionEntries() throws {
        let (plan, _) = try fixture()
        let archive = AnyDestinationMigrationItem(sourceKey: "explicit-archive-not-an-original-type",
            sourceObjectID: "native-type", operation: .typeDefinition(.init(
                xKey: "retained_archive", name: "Original source archive",
                meta: .literal(.object(["preservationContract": .string("explicit-test-archive")])))))
        let coverage = plan.coverage.map { row -> AnyDestinationCoverage in
            if row.sourceObjectID == "native-type", case .mapped(let keys) = row.disposition {
                return .init(sourceObjectID: row.sourceObjectID, disposition: .mapped(itemSourceKeys: keys + [archive.sourceKey]))
            }
            return row
        }
        let augmented = try AnyDestinationMigrationPlan(source: plan.source, workspace: plan.binding.workspace,
            storeID: plan.binding.storeID, planID: plan.binding.planID, coverage: coverage, items: plan.items + [archive])
        let mappings = try syntheticMappings(augmented)
        let directory = try AnyNativeImportedDefinitionDirectory(plan: augmented, mappings: mappings)
        XCTAssertEqual(directory.entries.count, 5)
        let actual = try XCTUnwrap(directory.definition(sourceObjectID: "native-type"))
        guard case .type(let id) = actual.address else { return XCTFail("Type address") }
        XCTAssertNotEqual(id, mappings.last?.objectID)
        XCTAssertFalse(directory.entries.contains { $0.intent?.sourceKey == archive.sourceKey })
        XCTAssertFalse(directory.entries.contains { $0.intent?.kind == .collectionDefinition })
        XCTAssertFalse(directory.permitsSourceAdmission)
    }

    func testChangedMappingJoinsAndIntentIdentityRefuseBeforeAnyNativeRead() throws {
        let (plan, mappings) = try fixture()
        // Heart's original unique-key codec requires exactly two components.
        // A synthetic source ID containing a dash cannot be appended as-is.
        XCTAssertThrowsError(try catalog([try option("invalid-option", relation: "status", order: "A")])) { error in
            XCTAssertEqual(error as? AnyHeartNativeDefinitionCatalogError,
                           .invalidDefinition("invalid-option", "UniqueKey"))
        }
        XCTAssertThrowsError(try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: Array(mappings.dropLast())))
        XCTAssertThrowsError(try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: Array(mappings.reversed())))
        let index = try XCTUnwrap(mappings.firstIndex { $0.kind == "propertyDefinition" })
        let mutations: [(String, AnyJSON)] = [
            ("sourceKey", .string("foreign-key")), ("sourceObjectID", .string("relation-\u{e1}")),
            ("kind", .string("typeDefinition")), ("intentID", .string(String(repeating: "0", count: 64))),
            ("recordIDs", .array([])), ("signedChangeIDs", .array([])),
            ("fingerprint", .string("not-a-fingerprint"))
        ]
        for (key, value) in mutations {
            var changed = mappings
            var raw = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(changed[index])).object)
            raw[key] = value
            changed[index] = try JSONDecoder().decode(AnyDestinationMigrationMapping.self,
                from: AnyDestinationDefinitionChecks.bytes(.object(raw)))
            XCTAssertThrowsError(try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: changed), key)
        }
        XCTAssertNotEqual(AnyNativeImportedDefinitionAddress.type(objectID: "a\u{301}"),
                          .type(objectID: "\u{e1}"))
        XCTAssertNotEqual(AnyNativeImportedDefinitionAddress.option(ownerKind: .collection,
            key: try .init(ownerID: "owner", propertyID: "property"), optionID: "a\u{301}"),
            .option(ownerKind: .collection, key: try .init(ownerID: "owner", propertyID: "property"), optionID: "\u{e1}"))
    }

    func testRetainedOriginalDefinitionsResolveWithoutPromotingArchivedTypes() throws {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_NATIVE_DEFINITION_RETAINED"] else {
            throw XCTSkip("Requires the exact retained 182-operation plan and mapping artifacts.")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true)
        let planBytes = try Data(contentsOf: root.appendingPathComponent("source-preservation-plan.json"))
        let mappingBytes = try Data(contentsOf: root.appendingPathComponent("execute-mappings.json"))
        let plan = try AnyDestinationMigrationPlan.decode(planBytes)
        let mappings = try JSONDecoder().decode([AnyDestinationMigrationMapping].self, from: mappingBytes)
        let directory = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: mappings)
        XCTAssertEqual(mappings.count, 182)
        XCTAssertEqual(directory.entries.filter { if case .type = $0.address { true } else { false } }.count, 1)
        XCTAssertEqual(directory.entries.filter { if case .option = $0.address { true } else { false } }.count, 4)
        XCTAssertEqual(directory.entries.filter { entry in
            guard case .property = entry.address else { return false }
            return entry.intent?.kind == .propertyDefinition
        }.count, 7)
        XCTAssertFalse(directory.unresolvedSourceDefinitionIDs.isEmpty)
        XCTAssertFalse(directory.permitsSourceAdmission)
        XCTAssertFalse(directory.entries.contains { $0.intent?.sourceKey.hasPrefix("heart-source-catalog-") == true })
        XCTAssertEqual(try Data(contentsOf: root.appendingPathComponent("source-preservation-plan.json")), planBytes)
        XCTAssertEqual(try Data(contentsOf: root.appendingPathComponent("execute-mappings.json")), mappingBytes)
    }

    private func fixture() throws -> (AnyDestinationMigrationPlan, [AnyDestinationMigrationMapping]) {
        let status = try relation("relation-a\u{301}", key: "status", format: 3)
        let rows = [status, try type(extra: ["recommendedRelations": .array([.string(status.sourceObjectID)])]),
            try option("firstOption", relation: "status", order: "A"),
            try option("secondOption", relation: "status", order: "B"), try nativeName()]
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog(rows))
        XCTAssertTrue(mapper.issues.isEmpty)
        let plan = try boundPlan(rows: rows, mapper: mapper)
        return (plan, try syntheticMappings(plan))
    }

    private func syntheticMappings(_ plan: AnyDestinationMigrationPlan) throws -> [AnyDestinationMigrationMapping] {
        var byKey: [Data: AnyDestinationMigrationMapping] = [:]
        var result: [AnyDestinationMigrationMapping] = []
        for (index, item) in plan.items.enumerated() {
            let objectID: String
            switch item.operation {
            case .typeDefinition, .collectionDefinition: objectID = "explicit-fixture-root-\(index)"
            case .propertyDefinition(let owner, _, _, _, _, _, _, _), .partDefinition(let owner, _):
                objectID = try AnyDestinationMigrationVerifier.resolve(owner, in: byKey,
                    destinationSpaceID: plan.binding.workspace.spaceID)
            default: throw AnyNativeImportedDefinitionError.invalidMappings
            }
            let root = item.operation.kind == "typeDefinition" || item.operation.kind == "collectionDefinition"
            let records = root ? [objectID] : (0..<item.expectedRecordCount).map { "explicit-fixture-record-\(index)-\($0)" }
            let intent = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
                "pinkha-native-prepared-migration-intent/v1", plan.binding.workspace.accountID,
                plan.binding.workspace.spaceID, plan.binding.storeID, plan.binding.planID,
                item.sourceKey, item.operation.kind]))
            let mapping = AnyDestinationMigrationMapping(sourceKey: item.sourceKey, sourceObjectID: item.sourceObjectID,
                kind: item.operation.kind, intentID: intent, objectID: objectID, recordIDs: records, fileID: nil,
                fingerprint: AnyContentDigest.sha256(Data(("not-native:" + item.sourceKey).utf8)),
                signedChangeIDs: ["explicit-not-native-change-\(index)"],
                currentReceiptSHA256: AnyContentDigest.sha256(Data(("not-a-receipt:" + item.sourceKey).utf8)))
            byKey[Data(item.sourceKey.utf8)] = mapping; result.append(mapping)
        }
        return result
    }

    private func snapshot(_ id: String, type: Int64, key: String,
                          details: [String: AnyJSON], objectTypes: [String] = [],
                          protobufMarker: String = "") throws -> AnyHeartNativeSnapshotView {
        let pb = Data("synthetic-definition-wire-control:\(id)\(protobufMarker)".utf8)
        let value: AnyJSON = .object([
            "Contract": .string("pinkha-native-snapshot-json-v1"), "SpaceID": .string("source-space"),
            "ObjectID": .string(id), "NativeType": .integer(type), "UniqueKey": .string(key),
            "SnapshotSHA256": .string(AnyContentDigest.sha256(pb)), "SnapshotBytes": .integer(Int64(pb.count)),
            "Snapshot": .object(["blocks": .array([]), "details": .object(details),
                "objectTypes": .array(objectTypes.map(AnyJSON.string)), "relationLinks": .array([])]),
        ])
        return try .init(jsonView: JSONEncoder().encode(value), snapshotBytes: pb,
                         sourceSpaceID: "source-space", sourceObjectID: id)
    }

    private func relation(_ id: String, key: String, format: Int64,
                          extra: [String: AnyJSON] = [:]) throws -> AnyHeartNativeSnapshotView {
        var details: [String: AnyJSON] = ["name": .string("Captured \(key) — a\u{301}"),
            "description": .string("current definition"), "relationKey": .string(key),
            "relationFormat": .integer(format), "relationDefaultValue": .null,
            "relationMaxCount": .integer(format == 3 ? 1 : 0), "relationReadonlyValue": .bool(false),
            "relationFormatIncludeTime": .bool(true), "relationFormatObjectTypes": .array([])]
        details.merge(extra) { _, value in value }
        return try snapshot(id, type: 521, key: "rel-" + key, details: details)
    }

    private func type(_ id: String = "native-type", key: String = "owned",
                      extra: [String: AnyJSON] = [:]) throws -> AnyHeartNativeSnapshotView {
        var details: [String: AnyJSON] = ["name": .string("Current captured type"), "pluralName": .string("Types"),
            "recommendedLayout": .integer(0), "recommendedRelations": .array([]),
            "recommendedFeaturedRelations": .array([]), "recommendedHiddenRelations": .array([]),
            "recommendedFileRelations": .array([])]
        details.merge(extra) { _, value in value }
        return try snapshot(id, type: 528, key: "ot-" + key, details: details)
    }

    private func option(_ id: String, relation: String, order: String) throws -> AnyHeartNativeSnapshotView {
        try snapshot(id, type: 529, key: "opt-" + id,
            details: ["relationKey": .string(relation), "name": .string("Option \(id)"),
                "relationOptionColor": .string("blue"), "orderId": .string(order)])
    }

    private func catalog(_ rows: [AnyHeartNativeSnapshotView]) throws -> AnyHeartNativeDefinitionCatalog {
        try .init(sourceAccountID: "source-account", sourceSpaceID: "source-space",
            captureManifestSHA256: AnyContentDigest.sha256(try wireManifest(rows)),
            sourceWitnessSHA256: String(repeating: "b", count: 64), snapshots: rows)
    }

    private func wireManifest(_ rows: [AnyHeartNativeSnapshotView]) throws -> Data {
        let accountHash = AnyContentDigest.sha256(Data("source-account".utf8))
        let spaceHash = AnyContentDigest.sha256(Data("source-space".utf8))
        let witness = String(repeating: "b", count: 64)
        let objects = rows.sorted { Data($0.sourceObjectID.utf8).lexicographicallyPrecedes(Data($1.sourceObjectID.utf8)) }.map { row -> AnyJSON in
            let path = "snapshot-" + AnyContentDigest.sha256(Data(row.sourceObjectID.utf8))
            return .object(["ObjectID": .string(row.sourceObjectID), "NativeType": .integer(row.nativeType), "UniqueKey": .string(row.uniqueKey),
                "Snapshot": .object(["Path": .string(path + ".pb"), "SHA256": .string(row.snapshotSHA256), "Bytes": .integer(Int64(row.protobufBytes.count))]),
                "NativeJSONView": .object(["Path": .string(path + ".json"), "SHA256": .string(row.viewSHA256), "Bytes": .integer(Int64(row.jsonViewBytes.count))])])
        }
        return try AnyDestinationDefinitionChecks.bytes(.object([
            "Contract": .string("pinkha-native-whole-source-bundle-v1"), "Objects": .array(objects),
            "Receipt": .object(["Version": .string("loaded-account-native-space-source-v1"),
                "AccountSessionAuthorizedAtFinalCapture": .bool(true), "AllNativeHeadRowsAccounted": .bool(true),
                "CapturedSnapshotsBoundToUnchangedCheckpoint": .bool(true),
                "Inventory": .object(["SpaceSHA256": .string(spaceHash), "SourceWitnessSHA256": .string(witness)]),
                "Source": .object(["accountSHA256": .string(accountHash), "source": .object([
                    "accountSHA256": .string(accountHash), "spaceSHA256": .string(spaceHash),
                    "native": .object(["WitnessSHA256": .string(witness)])])])]),
        ]))
    }

    private func boundPlan(rows: [AnyHeartNativeSnapshotView], mapper: AnyHeartNativeDefinitionPlan,
                           items: [AnyDestinationMigrationItem]? = nil,
                           extraCoverage: [AnyDestinationCoverage]? = nil) throws -> AnyDestinationMigrationPlan {
        let items = items ?? mapper.schemaItems
        let manifest = try wireManifest(rows)
        let special = extraCoverage ?? mapper.definitionCoverage
        let specialIDs = Set(special.map { Data($0.sourceObjectID.utf8) })
        let ordinary = rows.filter { !specialIDs.contains(Data($0.sourceObjectID.utf8)) }.map { row in
            AnyDestinationCoverage(sourceObjectID: row.sourceObjectID, disposition: .mapped(itemSourceKeys:
                items.filter { Data($0.sourceObjectID.utf8) == Data(row.sourceObjectID.utf8) }.map(\.sourceKey)))
        }
        return try .init(source: .init(accountID: "source-account", spaceID: "source-space",
            witnessSHA256: String(repeating: "b", count: 64), captureManifestSHA256: AnyContentDigest.sha256(manifest),
            semanticPlanSHA256: mapper.catalog.contentSHA256, sourceObjectIDs: rows.map(\.sourceObjectID),
            definitionManifestBytes: manifest),
            workspace: .init(accountID: "destination-account", spaceID: "destination-space"), storeID: "destination-store",
            planID: String(repeating: "c", count: 64), coverage: ordinary + special, items: items)
    }

    private func nativeName(_ id: String = "native-name", overrides: [String: AnyJSON] = [:]) throws -> AnyHeartNativeSnapshotView {
        var fields: [String: AnyJSON] = ["name": .string("Name"), "description": .string("Name of the object"),
            "relationMaxCount": .integer(1), "relationFormatIncludeTime": .bool(false)]
        fields.merge(overrides) { _, value in value }
        return try relation(id, key: "name", format: 1, extra: fields)
    }
}
