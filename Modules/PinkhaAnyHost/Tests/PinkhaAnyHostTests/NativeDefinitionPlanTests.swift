import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Four bounded semantic/wire controls plus one explicitly supplied original
/// native capture. Synthetic envelopes do not assert native source authority.
final class NativeDefinitionPlanTests: XCTestCase {
    private func snapshot(_ id: String, type: Int64, key: String,
                          details: [String: AnyJSON], objectTypes: [String] = []) throws -> AnyHeartNativeSnapshotView {
        let pb = Data("synthetic-definition-wire-control:\(id)".utf8)
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
            captureManifestSHA256: String(repeating: "a", count: 64),
            sourceWitnessSHA256: String(repeating: "b", count: 64), snapshots: rows)
    }

    func testCapturedOverridesIdentityNamespacesAndOrderedRecommendationsAreExact() throws {
        let decomposed = "e\u{301}", composed = "é"
        let text = try relation("native-text", key: decomposed, format: 0,
            extra: ["relationDefaultValue": .string("captured override — " + decomposed)])
        let other = try relation("native-other", key: composed, format: 1)
        let sourceType = try type(extra: ["recommendedRelations": .array([.string(other.sourceObjectID), .string(text.sourceObjectID)]),
            "recommendedFeaturedRelations": .array([.string(text.sourceObjectID)]),
            "recommendedHiddenRelations": .array([.string(other.sourceObjectID)])])
        let c = try catalog([text, other, sourceType])
        XCTAssertTrue(c.issues.isEmpty)
        XCTAssertEqual(c.type(objectID: sourceType.sourceObjectID)?.typeKey, "owned")
        XCTAssertEqual(c.type(key: "owned")?.objectID, sourceType.sourceObjectID)
        XCTAssertEqual(c.type(url: "ot-owned")?.objectID, sourceType.sourceObjectID)
        XCTAssertNil(c.type(key: sourceType.sourceObjectID))
        XCTAssertNil(c.type(url: "owned"))
        XCTAssertEqual(c.relation(key: decomposed)?.objectID, text.sourceObjectID)
        XCTAssertEqual(c.relation(key: composed)?.objectID, other.sourceObjectID)
        XCTAssertNotEqual(Data(decomposed.utf8), Data(composed.utf8))
        XCTAssertEqual(c.types[0].recommendedRelations, [other.sourceObjectID, text.sourceObjectID])
        XCTAssertEqual(c.types[0].featuredRelations, [text.sourceObjectID])
        XCTAssertEqual(c.relation(objectID: text.sourceObjectID)?.defaultValue,
                       .string("captured override — " + decomposed))
        XCTAssertEqual(c.relation(objectID: text.sourceObjectID)?.snapshot.jsonViewBytes, text.jsonViewBytes)
        XCTAssertFalse(c.permitsDestinationWrites)
        XCTAssertEqual(c.contentSHA256, try catalog([sourceType, other, text]).contentSHA256)
    }

    func testAmbiguousKeysAndUnknownFieldsRemainExplicitAndCannotAdmitWrites() throws {
        let first = try relation("first", key: "shared", format: 0)
        let second = try relation("second", key: "shared", format: 0, extra: ["futureSemanticField": .bool(true)])
        let c = try catalog([first, second, type(extra: ["recommendedRelations": .array([.string("missing")])])])
        XCTAssertNil(c.relation(key: "shared"))
        XCTAssertEqual(c.relations.count, 2)
        XCTAssertEqual(c.issues.filter { $0.kind == .duplicateUniqueKey }.count, 2)
        XCTAssertEqual(c.issues.filter { $0.kind == .duplicateRelationKey }.count, 2)
        XCTAssertTrue(c.issues.contains { $0.kind == .unknownDetailField && $0.field == "futureSemanticField" })
        XCTAssertTrue(c.issues.contains { $0.kind == .unresolvedRecommendation })
        let plan = try AnyHeartNativeDefinitionPlan(catalog: c)
        XCTAssertThrowsError(try plan.admittedSchemaItems())
        XCTAssertThrowsError(try catalog([first, first]))
        let bad = try snapshot("bad", type: 528, key: "rel-owned", details: [:])
        XCTAssertThrowsError(try catalog([bad]))
        let colliding = try catalog([type("first-type", key: "same"), type("second-type", key: "same")])
        XCTAssertNil(colliding.type(key: "same"))
        XCTAssertEqual(colliding.types.count, 2)
    }

    func testTypedValuesPreserveEmptyFalseZeroChoiceOrderAndDeferredObjectReferences() throws {
        let rows = try [relation("text-id", key: "text", format: 0),
            relation("number-id", key: "number", format: 2), relation("check-id", key: "check", format: 6),
            relation("date-id", key: "date", format: 4), relation("status-id", key: "status", format: 3),
            relation("tags-id", key: "tags", format: 11), relation("object-id", key: "object", format: 100,
                extra: ["relationFormatObjectTypes": .array([.string("native-type")])]),
            option("statusA", relation: "status", order: "b1"),
            option("tagA", relation: "tags", order: "z1"), option("tagB", relation: "tags", order: "a1"), type()]
        let plan = try AnyHeartNativeDefinitionPlan(catalog: catalog(rows))
        let details: [String: AnyJSON] = ["text": .string(""), "number": .integer(0), "check": .bool(false),
            "date": .integer(1_795_533_300), "status": .array([]),
            "tags": .array([.string("tagA"), .string("tagB")]), "object": .array([.string("other-doc")])]
        let source = try snapshot("doc", type: 16, key: "", details: details, objectTypes: ["ot-owned"])
        let values = try plan.values(snapshot: source, relationKeys: ["text", "number", "check", "date", "status", "tags", "object"],
            objects: [.init(sourceObjectID: "other-doc", destinationSourceKey: "prepared-other-doc")])
        let initial = try values.initial.resolved(AnyDestinationPlanChecks.placeholder)
        func field(_ key: String) throws -> AnyJSON? {
            initial[try AnyDestinationPlanChecks.placeholder(XCTUnwrap(plan.property(sourceKey: key)).record)]
        }
        XCTAssertEqual(try field("text"), .string(""))
        XCTAssertEqual(try field("number"), .integer(0))
        XCTAssertEqual(try field("check"), .bool(false))
        XCTAssertEqual(try field("date"), .object(["$date": .integer(1_795_533_300_000)]))
        XCTAssertEqual(try field("status"), .array([]))
        XCTAssertEqual(try field("tags"), .array([.string("tagA"), .string("tagB")]))
        XCTAssertEqual(values.deferredRelationKeys, ["object"])
        guard case .object(let deferred) = values.deferred, deferred.count == 1 else { return XCTFail("Expected one deferred group") }
        XCTAssertEqual(deferred[0].value, .array([.reference(.mapped(sourceKey: "prepared-other-doc", slot: .objectID, encoding: .anyURI))]))
        XCTAssertFalse(values.initialRelationKeys.contains("object"))
        XCTAssertEqual(plan.type(sourceURL: "ot-owned")?.definition.objectID, "native-type")
        XCTAssertThrowsError(try plan.values(snapshot: source, relationKeys: ["object"], objects: []))
        let wrongChoice = try snapshot("doc", type: 16, key: "", details: ["status": .array([.string("tagA")])])
        XCTAssertThrowsError(try plan.values(snapshot: wrongChoice, relationKeys: ["status"], objects: []))
        let null = try snapshot("doc", type: 16, key: "", details: ["text": .null])
        XCTAssertThrowsError(try plan.values(snapshot: null, relationKeys: ["text"], objects: []))
        let fraction = try snapshot("doc", type: 16, key: "", details: ["date": .number(1.25)])
        XCTAssertThrowsError(try plan.values(snapshot: fraction, relationKeys: ["date"], objects: []))
    }

    func testDefinitionDraftsBindOwnersOptionsTypeHandlesAndExplicitSemanticGaps() throws {
        let sourceType = try type(extra: ["recommendedFeaturedRelations": .array([.string("tag-id")])])
        let c = try catalog([sourceType, relation("tag-id", key: "tag", format: 11),
            option("later", relation: "tag", order: "z"), option("earlier", relation: "tag", order: "a"),
            relation("ref-id", key: "ref", format: 100,
                extra: ["relationFormatObjectTypes": .array([.string(sourceType.sourceObjectID)])]),
            relation("default-id", key: "default", format: 0, extra: ["relationDefaultValue": .string("native default")])])
        let plan = try AnyHeartNativeDefinitionPlan(catalog: c)
        let tag = try XCTUnwrap(plan.property(sourceKey: "tag"))
        let item = try XCTUnwrap(plan.schemaItems.first { $0.sourceKey == tag.sourceKey })
        guard case .propertyDefinition(let owner, let kind, _, _, _, _, let descriptor, _) = item.operation,
              let descriptor, case .literal(let format) = descriptor else { return XCTFail("Expected native property descriptor") }
        XCTAssertEqual(owner, plan.propertyOwner)
        XCTAssertEqual(kind, "array")
        XCTAssertEqual(format["type"], .string("choice"))
        XCTAssertEqual(format["options"]?["later"]?["pos"], .string("z"))
        XCTAssertEqual(format["options"]?["earlier"]?["pos"], .string("a"))
        XCTAssertEqual(format["pinkhaHeart"]?["relationKey"], .string("tag"))
        let reference = try XCTUnwrap(plan.property(sourceKey: "ref"))
        let referenceItem = try XCTUnwrap(plan.schemaItems.first { $0.sourceKey == reference.sourceKey })
        guard case .propertyDefinition(_, _, _, _, _, _, let referenceDescriptor, _) = referenceItem.operation,
              let referenceDescriptor, case .literal(let referenceFormat) = referenceDescriptor else { return XCTFail("Expected relation descriptor") }
        XCTAssertEqual(referenceFormat["relation"]?["targetTypes"], .array([.string(plan.types[0].xKey)]))
        XCTAssertNotEqual(plan.types[0].xKey, sourceType.sourceObjectID)
        XCTAssertTrue(plan.issues.contains { $0.field == "relationDefaultValue" })
        XCTAssertTrue(plan.issues.contains { $0.field == "option" })
        XCTAssertTrue(plan.issues.contains { $0.field == "recommendedLayout/recommendations" })
        XCTAssertThrowsError(try plan.admittedSchemaItems())
        let binding = try AnyPreparedMigrationPlanBinding(workspace: .init(accountID: "destination", spaceID: "destination-space"),
            storeID: "native-store", planID: String(repeating: "c", count: 64), planSHA256: String(repeating: "d", count: 64))
        for item in plan.schemaItems { try item.operation.validateShape(binding: binding, sourceKey: item.sourceKey) }
        XCTAssertEqual(plan.schemaItems.filter { if case .partDefinition = $0.operation { true } else { false } }.map(\.expectedRecordCount), [2])
        XCTAssertFalse(plan.permitsDestinationWrites)
    }

    func testOriginalNativeCaptureProvidesAllCurrentDefinitionRowsWithoutBundledSubstitution() throws {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_NATIVE_CAPTURE_FIXTURE"] else {
            throw XCTSkip("Original independently retained native fixture required")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true).resolvingSymlinksInPath().standardizedFileURL
        func bytes(_ relative: String, under directory: URL) throws -> Data {
            let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
            guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
                  parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
                throw AnyHeartNativeDefinitionCatalogError.invalidBinding
            }
            let p = directory.appendingPathComponent(relative).resolvingSymlinksInPath().standardizedFileURL
            guard p.path.hasPrefix(directory.path + "/"),
                  try p.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else {
                throw AnyHeartNativeDefinitionCatalogError.invalidBinding
            }
            return try Data(contentsOf: p, options: [.mappedIfSafe])
        }
        let contextBytes = try bytes("fixture-context.json", under: root)
        XCTAssertEqual(AnyContentDigest.sha256(contextBytes), "5357d52f5e76b604a40d7a5f2b1bc002e19bc864c419a45f90128bfa965d5850")
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        let directory = root.appendingPathComponent("source-bundle", isDirectory: true)
        let manifest = try bytes("manifest.json", under: directory)
        XCTAssertEqual(AnyContentDigest.sha256(manifest), "2a1a02987204321aaa1c8cf9f0c7f413f4b50dbce87280d82499c4f9bc7be238")
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try bytes($0.path, under: directory) }
        let c = try AnyHeartNativeDefinitionCatalog(bundle: bundle)
        XCTAssertEqual(c.types.count, 19)
        XCTAssertEqual(c.relations.count, 119)
        XCTAssertEqual(c.options.count, 0)
        for definition in c.types {
            XCTAssertEqual(c.type(objectID: definition.objectID)?.snapshot.protobufBytes, definition.snapshot.protobufBytes)
            XCTAssertEqual(c.type(url: definition.typeURL)?.objectID, definition.objectID)
            XCTAssertEqual(c.type(key: definition.typeKey)?.objectID, definition.objectID)
            XCTAssertNil(c.type(key: definition.objectID))
            XCTAssertEqual(definition.recommendedRelations, definition.snapshot.details["recommendedRelations"]?.array?.compactMap(\.string))
        }
        for relation in c.relations {
            XCTAssertEqual(c.relation(key: relation.relationKey)?.objectID, relation.objectID)
            XCTAssertEqual(relation.defaultValue, relation.snapshot.details["relationDefaultValue"])
            XCTAssertEqual(Data(relation.name.utf8), Data(try XCTUnwrap(relation.snapshot.details["name"]?.string).utf8))
        }
        let plan = try AnyHeartNativeDefinitionPlan(catalog: c)
        XCTAssertEqual(plan.types.count, 19)
        XCTAssertGreaterThan(plan.properties.count, 0)
        XCTAssertFalse(plan.issues.isEmpty)
        XCTAssertThrowsError(try plan.admittedSchemaItems())
        XCTAssertFalse(c.permitsDestinationWrites)
        XCTAssertEqual(bundle.receipt["SemanticCompleteness"], .bool(false))
        XCTAssertEqual(AnyContentDigest.sha256(try bytes("manifest.json", under: directory)), bundle.manifestSHA256)
        print("CAPTURED_NATIVE_DEFINITION_CATALOG types=19 relations=119 options=0 originals_unchanged=true destination_writes=false")
    }
}
