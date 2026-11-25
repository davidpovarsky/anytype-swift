import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Four bounded semantic/wire controls plus one explicitly supplied original
/// native capture. Synthetic envelopes do not assert native source authority.
final class NativeDefinitionPlanTests: XCTestCase {
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
    /// Deliberately synthetic declaration-only envelopes for closed coverage
    /// controls. They are not full native bundle or current authority proofs.
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
        XCTAssertEqual(values.initialGroups.count, 1)
        let initial = try XCTUnwrap(values.initialGroups.first).fields.resolved(AnyDestinationPlanChecks.placeholder)
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
        XCTAssertEqual(values.deferredGroups.count, 1)
        guard case .object(let deferred) = try XCTUnwrap(values.deferredGroups.first).fields,
              deferred.count == 1 else { return XCTFail("Expected one deferred group") }
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
        XCTAssertFalse(plan.issues.contains { $0.field == "option" })
        XCTAssertEqual(plan.definitionCoverage.count, 2)
        XCTAssertFalse(plan.issues.contains { $0.field == "recommendedLayout/recommendations" })
        XCTAssertThrowsError(try plan.admittedSchemaItems())
        let binding = try AnyPreparedMigrationPlanBinding(workspace: .init(accountID: "destination", spaceID: "destination-space"),
            storeID: "native-store", planID: String(repeating: "c", count: 64), planSHA256: String(repeating: "d", count: 64))
        for item in plan.schemaItems { try item.operation.validateShape(binding: binding, sourceKey: item.sourceKey) }
        XCTAssertEqual(plan.schemaItems.filter { if case .partDefinition = $0.operation { true } else { false } }.map(\.expectedRecordCount), [2])
        XCTAssertFalse(plan.permitsDestinationWrites)
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

    func testCanonicalNameHasOneNativeAddressAndMixedOwnerValuesPreserveAbsence() throws {
        let name = try nativeName(), done = try relation("native-done", key: "done", format: 6)
        let sourceType = try type(extra: ["recommendedRelations": .array([.string(name.sourceObjectID), .string(done.sourceObjectID)]),
            "recommendedFeaturedRelations": .array([.string(done.sourceObjectID), .string(name.sourceObjectID)])])
        let rows = [name, done, sourceType]
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog(rows))
        let binding = try XCTUnwrap(mapper.property(sourceKey: "name"))
        XCTAssertTrue(binding.isCanonicalName)
        XCTAssertEqual(binding.owner, .native("any")); XCTAssertEqual(binding.record, .native("name"))
        XCTAssertFalse(mapper.schemaItems.contains { $0.sourceObjectID == name.sourceObjectID })
        let plan = try boundPlan(rows: rows, mapper: mapper)
        let decoded = try AnyDestinationMigrationPlan.decode(JSONEncoder().encode(plan))
        XCTAssertEqual(decoded.binding.planSHA256, plan.binding.planSHA256)
        guard case .canonicalProperty(let original) = mapper.definitionCoverage[0].disposition else { return XCTFail("canonical evidence") }
        XCTAssertEqual(original.evidence.protobufBytes, name.protobufBytes)
        XCTAssertEqual(original.evidence.jsonViewBytes, name.jsonViewBytes)
        let document = try snapshot("doc", type: 16, key: "", details: ["name": .string("כותרת — a\u{301}"), "done": .bool(false)])
        let values = try mapper.values(snapshot: document, relationKeys: ["name", "done"], objects: [])
        XCTAssertEqual(values.initialGroups.count, 2)
        let props = try values.initialProperties.resolved(AnyDestinationPlanChecks.placeholder)
        XCTAssertEqual(props["any"]?["name"], .string("כותרת — a\u{301}"))
        let doneBinding = try XCTUnwrap(mapper.property(sourceKey: "done"))
        XCTAssertEqual(props[try AnyDestinationPlanChecks.placeholder(doneBinding.owner)]?[try AnyDestinationPlanChecks.placeholder(doneBinding.record)], .bool(false))
        XCTAssertTrue(values.deferredGroups.isEmpty)
        let absent = try snapshot("doc", type: 16, key: "", details: ["name": .string("")])
        let onlyName = try mapper.values(snapshot: absent, relationKeys: ["name"], objects: [])
        XCTAssertEqual(try onlyName.initialProperties.resolved(AnyDestinationPlanChecks.placeholder), .object(["any": .object(["name": .string("")])]))
        XCTAssertThrowsError(try mapper.values(snapshot: absent, relationKeys: ["name", "done"], objects: []))
        let item = try XCTUnwrap(mapper.schemaItems.first { $0.sourceKey == mapper.types[0].sourceKey })
        guard case .typeDefinition(let seed) = item.operation else { return XCTFail("type") }
        let layout = try XCTUnwrap(seed.layout).resolved(AnyDestinationPlanChecks.placeholder)
        let presentation = try XCTUnwrap(layout["config"]?["pinkhaHeart"])
        XCTAssertEqual(presentation["contract"], .string("pinkha-heart-native-type-presentation-v2"))
        XCTAssertEqual(presentation["sourceRecommendedLayout"], .integer(0))
        XCTAssertEqual(presentation["recommended"]?.array?.first, .object(["ownerId": .string("any"), "propertyId": .string("name")]))
        XCTAssertEqual(presentation["featured"]?.array?.last, .object(["ownerId": .string("any"), "propertyId": .string("name")]))
    }

    func testCanonicalNameOverridesShadowingAndChangedNativeContractsRefuse() throws {
        let name = try nativeName(), text = try relation("text", key: "text", format: 0)
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog([name, text]))
        let overrides: [[String: AnyJSON]] = [["relationDefaultValue": .string("override")],
            ["relationReadonlyValue": .bool(true)], ["relationMaxCount": .integer(2)],
            ["relationFormat": .integer(0)], ["relationFormatIncludeTime": .bool(true)],
            ["name": .string("Custom caption")], ["futureSemantics": .bool(true)]]
        for override in overrides {
            let changed = try nativeName(overrides: override)
            let preview = try AnyHeartNativeDefinitionPlan(catalog: catalog([changed, text]))
            XCTAssertNil(preview.property(sourceKey: "name"))
            XCTAssertFalse(preview.schemaItems.contains { $0.sourceObjectID == changed.sourceObjectID })
            XCTAssertThrowsError(try preview.admittedSchemaItems())
        }
        let shadow = AnyDestinationMigrationItem(sourceKey: "shadow", sourceObjectID: name.sourceObjectID,
            operation: .collectionDefinition(.init(xKey: "shadow", name: "Unrelated")))
        XCTAssertThrowsError(try boundPlan(rows: [name, text], mapper: mapper, items: [shadow] + mapper.schemaItems))
        let duplicate = try nativeName("second-name")
        let duplicateCoverage = try AnyDestinationCoverage(sourceObjectID: duplicate.sourceObjectID,
            disposition: .canonicalProperty(.init(evidence: .init(snapshot: duplicate))))
        XCTAssertThrowsError(try boundPlan(rows: [name, text, duplicate], mapper: mapper,
            extraCoverage: mapper.definitionCoverage + [duplicateCoverage]))
        let good = AnyDestinationCanonicalPropertyBinding.nativeDescriptor
        XCTAssertNoThrow(try AnyDestinationDefinitionChecks.verifyNativeNameProperties(.object(["properties": .array([good])])))
        for key in ["id", "name", "description", "kind", "scope", "xFormat"] {
            var altered = try XCTUnwrap(good.object); altered[key] = .string("changed")
            XCTAssertThrowsError(try AnyDestinationDefinitionChecks.verifyNativeNameProperties(.object(["properties": .array([.object(altered)])])))
        }
        XCTAssertThrowsError(try AnyDestinationDefinitionChecks.verifyNativeNameProperties(.object(["properties": .array([good, good])])))
        XCTAssertThrowsError(try AnyDestinationDefinitionChecks.verifyNativeNameProperties(.object(["properties": .array([])])))
        XCTAssertThrowsError(try AnyDestinationDefinitionEvidence(sourceSpaceID: name.sourceSpaceID,
            sourceObjectID: name.sourceObjectID, protobufBytes: name.protobufBytes + Data([0]), jsonViewBytes: name.jsonViewBytes))
    }

    func testEmbeddedOptionCoverageBindsExactOwnerPathValueAndSourceBytes() throws {
        let relation = try relation("tag-source", key: "tag", format: 11)
        let other = try self.relation("other-source", key: "other", format: 11)
        let option = try option("optionSource", relation: "tag", order: "b-actual")
        let rows = [relation, other, option]
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog(rows))
        let valid = try boundPlan(rows: rows, mapper: mapper)
        XCTAssertEqual(try AnyDestinationMigrationPlan.decode(JSONEncoder().encode(valid)).binding.planSHA256, valid.binding.planSHA256)
        guard case .embeddedOption(let owner, let evidence, let digest) = mapper.definitionCoverage[0].disposition else { return XCTFail("option coverage") }
        XCTAssertEqual(evidence.snapshotSHA256, option.snapshotSHA256)
        XCTAssertEqual(evidence.viewSHA256, option.viewSHA256)
        XCTAssertEqual(evidence.protobufBytes, option.protobufBytes)
        let wrongOwner = try XCTUnwrap(mapper.property(sourceKey: "other")).sourceKey
        XCTAssertThrowsError(try boundPlan(rows: rows, mapper: mapper,
            extraCoverage: [.init(sourceObjectID: option.sourceObjectID,
                disposition: .embeddedOption(propertySourceKey: wrongOwner, evidence: evidence, descriptorSHA256: digest))]))
        for variant in ["renamed", "wrong-path", "wrong-provenance", "wrong-kind"] {
            let changed = mapper.schemaItems.map { item -> AnyDestinationMigrationItem in
                guard item.sourceKey == owner,
                      case .propertyDefinition(let o, let kind, let name, let key, let desc, let scope, .literal(let xf)?, let index) = item.operation,
                      var format = xf.object, var options = format["options"]?.object,
                      var value = options[option.sourceObjectID]?.object else { return item }
                switch variant {
                case "renamed": value["name"] = .string("same id, different value")
                case "wrong-provenance": value["meta"] = .object([:])
                case "wrong-path": options.removeValue(forKey: option.sourceObjectID)
                default: break
                }
                if variant == "wrong-path" { options["another-id"] = .object(value) }
                else { options[option.sourceObjectID] = .object(value) }
                format["options"] = .object(options)
                return .init(sourceKey: item.sourceKey, sourceObjectID: item.sourceObjectID,
                    operation: .propertyDefinition(owner: o, kind: variant == "wrong-kind" ? "string" : kind,
                        name: name, xKey: key, description: desc, scope: scope, xFormat: .literal(.object(format)), index: index))
            }
            XCTAssertThrowsError(try boundPlan(rows: rows, mapper: mapper, items: changed), variant)
        }
        XCTAssertThrowsError(try boundPlan(rows: rows, mapper: mapper,
            extraCoverage: mapper.definitionCoverage + mapper.definitionCoverage))
        let shadow = AnyDestinationMigrationItem(sourceKey: "option-shadow", sourceObjectID: option.sourceObjectID,
            operation: .collectionDefinition(.init(xKey: "shadow-option", name: "Unrelated")))
        XCTAssertThrowsError(try boundPlan(rows: rows, mapper: mapper, items: mapper.schemaItems + [shadow]))
        let changedOption = try snapshot(option.sourceObjectID, type: 529, key: "opt-optionSource",
            details: ["relationKey": .string("tag"), "name": .string("different capture"), "relationOptionColor": .string("blue"), "orderId": .string("b-actual")])
        XCTAssertThrowsError(try boundPlan(rows: rows, mapper: mapper,
            extraCoverage: [.init(sourceObjectID: option.sourceObjectID, disposition: .embeddedOption(propertySourceKey: owner,
                evidence: try .init(snapshot: changedOption), descriptorSHA256: digest))]))
    }

    func testDetachedReplacementEvidenceAndUnrepresentedOptionStateAreRefused() throws {
        let property = try relation("tagSource", key: "tag", format: 11)
        let original = try option("optionSource", relation: "tag", order: "m")
        let rows = [property, original]
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog(rows))
        let valid = try boundPlan(rows: rows, mapper: mapper)
        let forged = try snapshot(original.sourceObjectID, type: 529, key: original.uniqueKey,
            details: ["relationKey": .string("tag"), "name": .string("forged self-consistent value"),
                "relationOptionColor": .string("red"), "orderId": .string("z")], protobufMarker: ":different-pb")
        XCTAssertNotEqual(forged.snapshotSHA256, original.snapshotSHA256)
        XCTAssertNotEqual(forged.viewSHA256, original.viewSHA256)
        let forgedMapper = try AnyHeartNativeDefinitionPlan(catalog: catalog([property, forged]))
        // The forged descriptor, PB and JSON agree with one another. Only the
        // original outer declaration distinguishes them from admitted source.
        XCTAssertThrowsError(try boundPlan(rows: rows, mapper: forgedMapper))
        let noManifest = try AnyDestinationSourceBinding(accountID: valid.source.accountID,
            spaceID: valid.source.spaceID, witnessSHA256: valid.source.witnessSHA256,
            captureManifestSHA256: valid.source.captureManifestSHA256, semanticPlanSHA256: valid.source.semanticPlanSHA256,
            sourceObjectIDs: valid.source.sourceObjectIDs)
        XCTAssertThrowsError(try AnyDestinationMigrationPlan(source: noManifest, workspace: valid.binding.workspace,
            storeID: valid.binding.storeID, planID: valid.binding.planID, coverage: valid.coverage, items: valid.items))
        XCTAssertThrowsError(try AnyDestinationSourceBinding(accountID: valid.source.accountID,
            spaceID: valid.source.spaceID, witnessSHA256: valid.source.witnessSHA256,
            captureManifestSHA256: valid.source.captureManifestSHA256, semanticPlanSHA256: valid.source.semanticPlanSHA256,
            sourceObjectIDs: valid.source.sourceObjectIDs, definitionManifestBytes: try wireManifest([property, forged])))
        for key in ["isArchived", "isHidden", "isReadonly", "futureOptionSemantics"] {
            var details = original.details; details[key] = .bool(true)
            let row = try snapshot(original.sourceObjectID, type: 529, key: original.uniqueKey, details: details)
            XCTAssertThrowsError(try AnyDestinationDefinitionChecks.optionDescriptor(.init(snapshot: row), relationObjectID: property.sourceObjectID), key)
            let preview = try AnyHeartNativeDefinitionPlan(catalog: catalog([property, row]))
            XCTAssertTrue(preview.definitionCoverage.isEmpty)
            XCTAssertThrowsError(try preview.admittedSchemaItems())
        }
    }

    func testCapturedDefinitionHiddenDefaultsKeepTitleAndTypeHiddenSeparate() throws {
        let name = try nativeName(overrides: ["isHidden": .bool(true)])
        let hidden = try relation("hiddenField", key: "hiddenField", format: 0, extra: ["isHidden": .bool(true)])
        let shown = try relation("shownField", key: "shownField", format: 6, extra: ["isHidden": .bool(false)])
        let sourceType = try type(extra: ["recommendedHiddenRelations": .array([.string(shown.sourceObjectID)])])
        let rows = [name, hidden, shown, sourceType]
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog(rows))
        let title = try XCTUnwrap(mapper.property(sourceKey: "name"))
        XCTAssertEqual(title.sourceHidden, true); XCTAssertEqual(title.canonicalBinding?.sourceHidden, true)
        XCTAssertEqual(title.owner, .native("any")); XCTAssertEqual(title.record, .native("name"))
        XCTAssertNoThrow(try boundPlan(rows: rows, mapper: mapper))
        let item = try XCTUnwrap(mapper.schemaItems.first { $0.sourceKey == mapper.types[0].sourceKey })
        guard case .typeDefinition(let seed) = item.operation else { return XCTFail("type") }
        let config = try XCTUnwrap(seed.layout).resolved(AnyDestinationPlanChecks.placeholder)["config"]?["pinkhaHeart"]
        let ordinaryHidden = try XCTUnwrap(mapper.property(sourceKey: "hiddenField"))
        let explicitTypeHidden = try XCTUnwrap(mapper.property(sourceKey: "shownField"))
        XCTAssertEqual(config?["hidden"], .array([try explicitTypeHidden.address.resolved(AnyDestinationPlanChecks.placeholder)]))
        XCTAssertEqual(config?["definitionHidden"]?.array, try [ordinaryHidden, title].map { try $0.address.resolved(AnyDestinationPlanChecks.placeholder) })
        let document = try snapshot("doc", type: 16, key: "", details: ["name": .string("Visible title"),
            "hiddenField": .string("present hidden value"), "shownField": .bool(false)])
        let values = try mapper.values(snapshot: document, relationKeys: ["name", "hiddenField", "shownField"], objects: [])
        let properties = try values.initialProperties.resolved(AnyDestinationPlanChecks.placeholder)
        XCTAssertEqual(properties["any"]?["name"], .string("Visible title"))
        XCTAssertEqual(properties[try AnyDestinationPlanChecks.placeholder(ordinaryHidden.owner)]?[try AnyDestinationPlanChecks.placeholder(ordinaryHidden.record)], .string("present hidden value"))
        for state in [AnyJSON.null, .string("true")] {
            XCTAssertThrowsError(try AnyDestinationCanonicalPropertyBinding(evidence: .init(snapshot: nativeName(overrides: ["isHidden": state]))))
        }
        for field in ["isArchived", "isReadonly"] {
            let inactive = try relation("inactive", key: "inactive", format: 0, extra: [field: .bool(true)])
            let preview = try AnyHeartNativeDefinitionPlan(catalog: catalog([inactive]))
            XCTAssertNil(preview.property(sourceKey: "inactive")); XCTAssertThrowsError(try preview.admittedSchemaItems())
        }
    }

    func testDefinitionAddedDateIsExactSourceProvenanceAndMalformedValuesRefuse() throws {
        let property = try relation("tagSource", key: "tag", format: 11,
            extra: ["addedDate": .integer(1_795_533_300)])
        var details = try option("optionSource", relation: "tag", order: "captured-order").details
        details["addedDate"] = .integer(0)
        let choice = try snapshot("optionSource", type: 529, key: "opt-optionSource", details: details)
        let sourceType = try type(extra: ["addedDate": .integer(-1)])
        let c = try catalog([property, choice, sourceType])
        XCTAssertTrue(c.issues.isEmpty)
        XCTAssertEqual(c.relations[0].sourceProvenance.addedDateSeconds, 1_795_533_300)
        XCTAssertEqual(c.options[0].sourceProvenance.addedDateSeconds, 0)
        XCTAssertEqual(c.types[0].sourceProvenance.addedDateSeconds, -1)
        let descriptor = try AnyDestinationDefinitionChecks.optionDescriptor(.init(snapshot: choice), relationObjectID: property.sourceObjectID)
        XCTAssertEqual(descriptor["meta"]?["heartSourceAddedDateSeconds"], .integer(0))
        XCTAssertEqual(descriptor["meta"]?["heartSourceAddedDateContract"], .string("pinkha-heart-source-added-date-seconds-v1"))
        XCTAssertEqual(descriptor["pos"], .string("captured-order"))
        XCTAssertNil(descriptor["createdAt"])
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: c)
        let propertyKey = try XCTUnwrap(mapper.property(sourceKey: "tag")).sourceKey
        let item = try XCTUnwrap(mapper.schemaItems.first { $0.sourceKey == propertyKey })
        guard case .propertyDefinition(_, _, _, _, _, _, .literal(let format)?, _) = item.operation else {
            return XCTFail("native property operation")
        }
        XCTAssertEqual(format["pinkhaHeart"]?["sourceAddedDateSeconds"], property.details["addedDate"])
        XCTAssertNil(format["createdAt"])
        for malformed in [AnyJSON.null, .bool(true), .string("1795533300"), .number(0.25), .array([]), .object([:])] {
            for original in [property, choice, sourceType] {
                var changed = original.details; changed["addedDate"] = malformed
                let row = try snapshot(original.sourceObjectID, type: original.nativeType, key: original.uniqueKey, details: changed)
                XCTAssertThrowsError(try catalog([row]))
                if row.nativeType == 529 {
                    XCTAssertThrowsError(try AnyDestinationDefinitionChecks.optionDescriptor(.init(snapshot: row), relationObjectID: property.sourceObjectID))
                }
            }
        }
        var future = choice.details; future["futureAddedDateSemantics"] = .bool(true)
        let unknown = try snapshot(choice.sourceObjectID, type: 529, key: choice.uniqueKey, details: future)
        XCTAssertTrue(try catalog([property, unknown]).issues.contains { $0.kind == .unknownDetailField })
        XCTAssertThrowsError(try AnyDestinationDefinitionChecks.optionDescriptor(.init(snapshot: unknown), relationObjectID: property.sourceObjectID))
        let absent = try option("absentOption", relation: "tag", order: "a")
        XCTAssertNil(try AnyDestinationDefinitionChecks.optionDescriptor(.init(snapshot: absent), relationObjectID: property.sourceObjectID)["meta"]?["heartSourceAddedDateSeconds"])
    }

    /// Original immutable bytes from a native method whose final fixture
    /// assertion failed. This diagnostic does not promote that method to PASS.
    func testOriginalCustomCaptureMapsCurrentChoicesAndValuesWithoutPromotingSourceAcceptance() throws {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE"] else {
            throw XCTSkip("Original independently retained custom fixture required")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true).resolvingSymlinksInPath().standardizedFileURL
        func bytes(_ relative: String, under directory: URL) throws -> Data {
            let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
            guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
                  parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
                throw AnyHeartNativeDefinitionCatalogError.invalidBinding
            }
            let file = directory.appendingPathComponent(relative).resolvingSymlinksInPath().standardizedFileURL
            guard file.path.hasPrefix(directory.path + "/"),
                  try file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else {
                throw AnyHeartNativeDefinitionCatalogError.invalidBinding
            }
            return try Data(contentsOf: file, options: [.mappedIfSafe])
        }
        let contextBytes = try bytes("fixture-context.json", under: root)
        XCTAssertEqual(AnyContentDigest.sha256(contextBytes), "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a")
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        XCTAssertEqual(context["customSchemaAcceptanceStatus"], .string("FAIL"))
        XCTAssertEqual(context["readOnlyDiagnosticFixture"], .bool(true))
        XCTAssertEqual(context["sourceAdmissionPromoted"], .bool(false))
        let directory = root.appendingPathComponent("bundle", isDirectory: true)
        let manifest = try bytes("manifest.json", under: directory)
        XCTAssertEqual(AnyContentDigest.sha256(manifest), "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4")
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try bytes($0.path, under: directory) }
        let c = try AnyHeartNativeDefinitionCatalog(bundle: bundle)
        XCTAssertEqual(bundle.objects.count, 156)
        XCTAssertEqual(c.types.count, 20); XCTAssertEqual(c.relations.count, 126); XCTAssertEqual(c.options.count, 4)
        XCTAssertFalse(c.issues.contains { $0.kind == .unknownDetailField && $0.field == "addedDate" })
        let definitions = c.relations.filter { $0.name.hasPrefix("Owned source ") }
        XCTAssertEqual(definitions.count, 7)
        let labels = Dictionary(uniqueKeysWithValues: definitions.map { (String($0.name.dropFirst("Owned source ".count)), $0) })
        let custom = try XCTUnwrap(c.types.first { $0.name == "Owned native schema — סוג" })
        XCTAssertEqual(custom.featuredRelations, try ["text", "status"].map { try XCTUnwrap(labels[$0]).objectID })
        XCTAssertEqual(custom.recommendedRelations, try ["number", "date", "object", "tag"].map { try XCTUnwrap(labels[$0]).objectID })
        XCTAssertEqual(custom.hiddenRelations, [try XCTUnwrap(labels["checkbox"]).objectID])
        XCTAssertEqual(try XCTUnwrap(labels["object"]).targetTypeIDs, [custom.objectID])
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: c)
        let binding = try AnyDestinationSourceBinding(bundle: bundle, semanticPlanSHA256: c.contentSHA256,
            sourceObjectIDs: bundle.objects.map(\.sourceObjectID))
        XCTAssertEqual(mapper.definitionCoverage.filter { if case .embeddedOption = $0.disposition { return true }; return false }.count, 4)
        for option in c.options {
            XCTAssertNotNil(option.sourceProvenance.addedDateSeconds)
            XCTAssertEqual(option.sourceProvenance.originalAddedDate, option.snapshot.details["addedDate"])
            let property = try XCTUnwrap(mapper.property(sourceKey: option.relationKey))
            let evidence = try AnyDestinationDefinitionEvidence(snapshot: option.snapshot)
            try evidence.requireSource(binding, objectID: option.objectID)
            let descriptor = try AnyDestinationDefinitionChecks.optionDescriptor(evidence, relationObjectID: property.relation.objectID)
            XCTAssertEqual(descriptor["pos"], option.snapshot.details["orderId"])
            XCTAssertEqual(descriptor["name"], option.snapshot.details["name"])
            XCTAssertEqual(descriptor["meta"]?["heartSourceAddedDateSeconds"], option.snapshot.details["addedDate"])
            let item = try XCTUnwrap(mapper.schemaItems.first { $0.sourceKey == property.sourceKey })
            guard case .propertyDefinition(_, _, _, _, _, _, .literal(let format)?, _) = item.operation else {
                return XCTFail("native choice operation")
            }
            XCTAssertEqual(format["options"]?[option.objectID], descriptor)
            XCTAssertEqual(format["pinkhaHeart"]?["sourceAddedDateSeconds"], property.relation.snapshot.details["addedDate"])
        }
        XCTAssertNotEqual(try XCTUnwrap(c.options.first { $0.name == "הושלם" }).orderID, "b1")
        XCTAssertNotEqual(try XCTUnwrap(c.options.first { $0.name == "תג שני" }).orderID, "b2")
        let docs = bundle.objects.filter { $0.nativeType == 16 }
        XCTAssertEqual(docs.count, 2)
        let first = try XCTUnwrap(docs.first { $0.details["name"] == .string("Owned typed document A") })
        let second = try XCTUnwrap(docs.first { $0.details["name"] == .string("Owned typed document B") })
        XCTAssertEqual(first.uniqueKey, "page"); XCTAssertEqual(second.uniqueKey, "page")
        for doc in docs {
            let keys = try ["text", "number", "checkbox", "date", "status", "tag", "object"].map { try XCTUnwrap(labels[$0]).relationKey }
            let values = try mapper.values(snapshot: doc, relationKeys: ["name"] + keys,
                objects: [.init(sourceObjectID: first.sourceObjectID, destinationSourceKey: "fixture-document-A"),
                          .init(sourceObjectID: second.sourceObjectID, destinationSourceKey: "fixture-document-B")])
            XCTAssertEqual(values.initialGroups.count, 2)
            let canonical = try XCTUnwrap(values.initialGroups.first { $0.owner == .native("any") })
            XCTAssertEqual(try canonical.fields.resolved(AnyDestinationPlanChecks.placeholder)["name"], doc.details["name"])
            let scalar = try XCTUnwrap(values.initialGroups.first { $0.owner != .native("any") }).fields.resolved(AnyDestinationPlanChecks.placeholder)
            for label in ["text", "number", "checkbox", "status", "tag"] {
                let key = try XCTUnwrap(labels[label]).relationKey
                let address = try AnyDestinationPlanChecks.placeholder(XCTUnwrap(mapper.property(sourceKey: key)).record)
                XCTAssertEqual(scalar[address], doc.details[key])
            }
            let dateKey = try XCTUnwrap(labels["date"]).relationKey
            let dateAddress = try AnyDestinationPlanChecks.placeholder(XCTUnwrap(mapper.property(sourceKey: dateKey)).record)
            XCTAssertEqual(scalar[dateAddress], .object(["$date": .integer(try XCTUnwrap(doc.details[dateKey]?.integer) * 1_000)]))
            XCTAssertEqual(values.deferredRelationKeys, [try XCTUnwrap(labels["object"]).relationKey])
        }
        XCTAssertTrue(mapper.issues.contains { $0.sourceObjectID == labels["text"]?.objectID && $0.field == "relationDefaultValue" })
        XCTAssertThrowsError(try mapper.admittedSchemaItems())
        XCTAssertFalse(mapper.permitsDestinationWrites)
        XCTAssertEqual(AnyContentDigest.sha256(try bytes("manifest.json", under: directory)), bundle.manifestSHA256)
        print("NATIVE_CUSTOM_CAPTURE_DIAGNOSTIC snapshots=156 types=20 relations=126 options=4 source_method=FAIL destination_writes=false originals_unchanged=true")
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
        let name = try XCTUnwrap(plan.property(sourceKey: "name"))
        XCTAssertTrue(name.isCanonicalName)
        XCTAssertEqual(name.sourceHidden, true)
        XCTAssertEqual(name.owner, .native("any")); XCTAssertEqual(name.record, .native("name"))
        XCTAssertFalse(plan.schemaItems.contains { $0.sourceObjectID == name.relation.objectID })
        XCTAssertEqual(name.canonicalBinding?.evidence.jsonViewBytes, name.relation.snapshot.jsonViewBytes)
        let sourceBinding = try AnyDestinationSourceBinding(bundle: bundle, semanticPlanSHA256: c.contentSHA256,
            sourceObjectIDs: bundle.objects.map(\.sourceObjectID))
        XCTAssertNoThrow(try name.canonicalBinding?.evidence.requireSource(sourceBinding, objectID: name.relation.objectID))
        XCTAssertGreaterThan(plan.properties.count, 0)
        XCTAssertFalse(plan.issues.isEmpty)
        XCTAssertThrowsError(try plan.admittedSchemaItems())
        XCTAssertFalse(c.permitsDestinationWrites)
        XCTAssertEqual(bundle.receipt["SemanticCompleteness"], .bool(false))
        XCTAssertEqual(AnyContentDigest.sha256(try bytes("manifest.json", under: directory)), bundle.manifestSHA256)
        print("CAPTURED_NATIVE_DEFINITION_CATALOG types=19 relations=119 options=0 originals_unchanged=true destination_writes=false")
    }
}
