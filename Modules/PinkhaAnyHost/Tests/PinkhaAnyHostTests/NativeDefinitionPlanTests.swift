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

    private func nativeDerived(_ role: AnyDestinationCanonicalPropertyBinding.DerivedRole,
                               participantID: String = "source-participant-type",
                               overrides: [String: AnyJSON] = [:]) throws -> AnyHeartNativeSnapshotView {
        let name: String, description: String
        switch role {
        case .author: name = "Created by"; description = "Human which created this object"
        case .createdAt: name = "Creation date"; description = "Date when the object was initially created"
        case .modifiedAt: name = "Last modified date"; description = "Date when the object was modified last time"
        case .modifiedBy: name = "Last modified by"; description = "Human who updated the object last time"
        }
        var fields: [String: AnyJSON] = ["name": .string(name), "description": .string(description),
            "relationMaxCount": .integer(1), "relationReadonlyValue": .bool(true),
            "relationFormatIncludeTime": .bool(role.isTimestamp),
            "relationFormatObjectTypes": .array(role.isTimestamp ? [] : [.string(participantID)])]
        fields.merge(overrides) { _, changed in changed }
        return try relation("derived-" + role.rawValue, key: role.sourceKey,
                            format: role.isTimestamp ? 4 : 100, extra: fields)
    }

    func testNativeDerivedDefinitionsBindActualNativeFieldsWithoutMutableShadows() throws {
        let roles: [AnyDestinationCanonicalPropertyBinding.DerivedRole] = [.author, .createdAt, .modifiedAt, .modifiedBy]
        let participant = try type("source-participant-type", key: "participant")
        let rows = try roles.map { try nativeDerived($0) } + [participant]
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog(rows))
        XCTAssertTrue(mapper.issues.isEmpty)
        for role in roles {
            let property = try XCTUnwrap(mapper.property(sourceKey: role.sourceKey))
            let binding = try XCTUnwrap(property.canonicalBinding)
            XCTAssertEqual(binding.derivedRole, role)
            XCTAssertNil(binding.identityRole)
            XCTAssertEqual(binding.ownerID, "any")
            XCTAssertEqual(binding.propertyID, role.rawValue)
            XCTAssertEqual(property.record, .native(role.rawValue))
            XCTAssertEqual(property.kind, role.isTimestamp ? "datetime" : "string")
            XCTAssertFalse(mapper.schemaItems.contains { $0.sourceObjectID == property.relation.objectID })
            XCTAssertNoThrow(try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(
                .object(["properties": .array([AnyDestinationCanonicalPropertyBinding.nativeDerivedDescriptor(role)])]),
                bindings: [binding]))
            var changed = try XCTUnwrap(AnyDestinationCanonicalPropertyBinding.nativeDerivedDescriptor(role).object)
            changed["scope"] = .string("synced")
            XCTAssertThrowsError(try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(
                .object(["properties": .array([.object(changed)])]), bindings: [binding]))
        }
        XCTAssertNoThrow(try boundPlan(rows: rows, mapper: mapper))
    }

    func testNativeDerivedSourceClocksAndParticipantsRemainHistoricalFacts() throws {
        let roles: [AnyDestinationCanonicalPropertyBinding.DerivedRole] = [.author, .createdAt, .modifiedAt, .modifiedBy]
        let participant = try type("source-participant-type", key: "participant")
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog(roles.map { try nativeDerived($0) } + [participant]))
        let originals: [String: AnyJSON] = ["creator": .array([.string("original-participant-א")]),
            "createdDate": .integer(-7), "lastModifiedDate": .integer(Int64.max), "lastModifiedBy": .array([])]
        let row = try snapshot("source-document", type: 16, key: "page", details: originals)
        let mapped = try mapper.values(snapshot: row, relationKeys: roles.map(\.sourceKey), objects: [])
        XCTAssertTrue(mapped.initialGroups.isEmpty)
        XCTAssertTrue(mapped.deferredGroups.isEmpty)
        XCTAssertTrue(mapped.nativeIdentityRelationKeys.isEmpty)
        XCTAssertEqual(mapped.nativeDerivedSourceValues.count, 4)
        for fact in mapped.nativeDerivedSourceValues {
            XCTAssertEqual(fact.originalValue, originals[fact.sourceRelationKey])
            XCTAssertEqual(fact.sourceObjectID, row.sourceObjectID)
            XCTAssertEqual(fact.snapshotSHA256, row.snapshotSHA256)
            XCTAssertEqual(fact.jsonViewSHA256, row.viewSHA256)
        }
        for bad in [AnyJSON.bool(false), .null, .array([.string("a"), .string("b")]), .array([.integer(2)])] {
            let invalid = try snapshot("source-document", type: 16, key: "page", details: ["creator": bad])
            XCTAssertThrowsError(try mapper.values(snapshot: invalid, relationKeys: ["creator"], objects: []))
        }
    }

    func testChangedDerivedDefinitionAndParticipantTypeCannotAcquireCanonicalCoverage() throws {
        let participant = try type("source-participant-type", key: "participant")
        let mutations: [[String: AnyJSON]] = [
            ["relationReadonlyValue": .bool(false)], ["relationFormatIncludeTime": .bool(true)],
            ["relationMaxCount": .integer(0)], ["relationFormatObjectTypes": .array([])],
            ["relationDefaultValue": .string("another-author")], ["description": .string("overridden")],
            ["unknownDerivedSemantics": .bool(true)]
        ]
        for overrides in mutations {
            let source = try nativeDerived(.author, overrides: overrides)
            let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog([source, participant]))
            XCTAssertNil(mapper.property(sourceKey: "creator"))
            XCTAssertFalse(mapper.schemaItems.contains { $0.sourceObjectID == source.sourceObjectID })
            XCTAssertThrowsError(try mapper.admittedSchemaItems())
        }
        let wrong = try type("source-participant-type", key: "page")
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog([nativeDerived(.author), wrong]))
        XCTAssertNil(mapper.property(sourceKey: "creator"))
        XCTAssertThrowsError(try mapper.admittedSchemaItems())
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


    func testTypeManualOrderRetainsAbsentEmptyAndExactRanksInPreparedMetadata() throws {
        let ranks: [String?] = [nil, "", "A", "a\u{301}", "\u{e1}"]
        let rows = try ranks.enumerated().map { index, rank in
            try type("ordered-\(index)", key: "kind\(index)",
                     extra: rank.map { ["orderId": .string($0)] } ?? [:])
        }
        let source = try catalog(rows)
        let plan = try AnyHeartNativeDefinitionPlan(catalog: source)
        XCTAssertTrue(source.issues.isEmpty)
        XCTAssertTrue(plan.issues.isEmpty)
        XCTAssertFalse(plan.permitsDestinationWrites)
        for (index, rank) in ranks.enumerated() {
            let definition = try XCTUnwrap(source.type(objectID: "ordered-\(index)"))
            XCTAssertEqual(definition.orderID.map { Data($0.utf8) }, rank.map { Data($0.utf8) })
            let item = try XCTUnwrap(plan.schemaItems.first {
                $0.sourceObjectID == definition.objectID &&
                    { if case .typeDefinition = $0.operation { return true }; return false }($0)
            })
            guard case .typeDefinition(let spec) = item.operation,
                  case .literal(let metadata) = spec.meta else { return XCTFail("prepared native type metadata") }
            XCTAssertEqual(metadata[AnyNativeImportedTypeOrder.contractKey],
                           .string(AnyNativeImportedTypeOrder.contract))
            XCTAssertEqual(metadata[AnyNativeImportedTypeOrder.scopeKey], .string(source.contentSHA256))
            XCTAssertEqual(metadata[AnyNativeImportedTypeOrder.valueKey], rank.map(AnyJSON.string))
            let captured = try JSONDecoder().decode(AnyJSON.self,
                from: Data(XCTUnwrap(metadata["heartDefinitionJSON"]?.string).utf8))
            XCTAssertEqual(captured["orderId"], rank.map(AnyJSON.string))
            XCTAssertEqual(definition.snapshot.details["orderId"], rank.map(AnyJSON.string))
        }
    }

    func testTypeManualOrderRejectsNonStringAndOverLimitNativeValues() throws {
        for malformed in [AnyJSON.null, .bool(true), .integer(1), .number(0.25),
                          .array([]), .object([:]), .string(String(repeating: "x", count: 65_537))] {
            XCTAssertThrowsError(try catalog([type(extra: ["orderId": malformed])]))
        }
    }

    func testFileDefinitionsMapOnlyBoundOriginalFilesAfterNativeCommitment() throws {
        let field = try relation("file-definition", key: "attachments", format: 5)
        let c = try catalog([field, type(extra: ["recommendedFileRelations": .array([.string(field.sourceObjectID)])])])
        let plan = try AnyHeartNativeDefinitionPlan(catalog: c)
        XCTAssertTrue(plan.issues.isEmpty)
        let property = try XCTUnwrap(plan.property(sourceKey: "attachments"))
        let raw = try defaultProperty(plan, binding: property)
        let descriptor = try XCTUnwrap(AnyNativePropertyDefinition(ownerID: "allocated-owner", raw: raw).fileFormat)
        XCTAssertTrue(descriptor.multiple)
        XCTAssertEqual(raw["xFormat"]?["links"], .string("links"))
        XCTAssertNil(raw["xFormat"]?["relation"])
        let a = fileBinding(catalog: c, id: "file-a"), b = fileBinding(catalog: c, id: "file-b")
        let page = try snapshot("page", type: 16, key: "", details: ["attachments": .array([.string(b.fileID), .string(a.fileID), .string(b.fileID)])])
        let values = try plan.values(snapshot: page, relationKeys: ["attachments"], objects: [], files: [a, b])
        XCTAssertTrue(values.initialGroups.isEmpty)
        XCTAssertEqual(values.deferredRelationKeys, ["attachments"])
        guard case .object(let fields) = try XCTUnwrap(values.deferredGroups.first).fields else { return XCTFail("Expected deferred files") }
        XCTAssertEqual(fields.first?.value, .array([.reference(b.reference), .reference(a.reference), .reference(b.reference)]))
        let item = try a.destinationItem(ownerSourceKey: "page")
        XCTAssertEqual(item.sourceObjectID, a.fileID)
        guard case .file(let owner, let name, let mime, let size, let digest) = item.operation else { return XCTFail("Expected a bound file operation") }
        XCTAssertEqual(owner, .mapped(sourceKey: "page", slot: .objectID, encoding: .rawID))
        XCTAssertEqual(name, a.name); XCTAssertEqual(mime, a.mimeType)
        XCTAssertEqual(size, a.size); XCTAssertEqual(digest, a.payloadSHA256)
        XCTAssertFalse(a.permitsDestinationWrites); XCTAssertFalse(plan.permitsDestinationWrites)
    }

    func testFileValuesRefuseMissingForeignDuplicateAndUnqualifiedRestrictions() throws {
        let field = try relation("file-definition", key: "attachments", format: 5,
            extra: ["relationMaxCount": .integer(1)])
        let c = try catalog([field, type()]), plan = try AnyHeartNativeDefinitionPlan(catalog: c)
        let file = fileBinding(catalog: c, id: "file")
        let page = try snapshot("page", type: 16, key: "", details: ["attachments": .array([.string(file.fileID)])])
        XCTAssertThrowsError(try plan.values(snapshot: page, relationKeys: ["attachments"], objects: []))
        XCTAssertThrowsError(try plan.values(snapshot: page, relationKeys: ["attachments"], objects: [], files: [file, file]))
        let foreign = fileBinding(catalog: c, id: "file", witness: String(repeating: "d", count: 64))
        XCTAssertThrowsError(try plan.values(snapshot: page, relationKeys: ["attachments"], objects: [], files: [foreign]))
        let tooMany = try snapshot("page", type: 16, key: "", details: ["attachments": .array([.string("file"), .string("file")])])
        XCTAssertThrowsError(try plan.values(snapshot: tooMany, relationKeys: ["attachments"], objects: [], files: [file]))
        let empty = try snapshot("page", type: 16, key: "", details: ["attachments": .array([])])
        XCTAssertNoThrow(try plan.values(snapshot: empty, relationKeys: ["attachments"], objects: []))
        let restricted = try relation("restricted", key: "images", format: 5,
            extra: ["relationFormatObjectTypes": .array([.string("native-type")])])
        let preview = try AnyHeartNativeDefinitionPlan(catalog: catalog([restricted, type()]))
        XCTAssertTrue(preview.issues.contains { $0.reason == "native-file-type-restriction-not-qualified" })
        XCTAssertThrowsError(try preview.admittedSchemaItems())
    }

    private func fileBinding(catalog: AnyHeartNativeDefinitionCatalog, id: String, witness: String? = nil) -> AnyHeartNativeFileBinding {
        // Deliberately detached component input, never native capture authority.
        .init(sourceAccountID: catalog.sourceAccountID, sourceSpaceID: catalog.sourceSpaceID,
            captureManifestSHA256: catalog.captureManifestSHA256, sourceWitnessSHA256: witness ?? catalog.sourceWitnessSHA256,
            fileID: id, variantPath: "original", payloadPath: "private-component-file", payloadSHA256: String(repeating: "c", count: 64),
            size: 4_097, name: "original.bin", mimeType: "application/octet-stream")
    }

    func testQualifiedDefaultMetadataPreservesAbsentEmptyAndExplicitCurrentValues() throws {
        let original = "native default e\u{301} — ברירת מחדל"
        let field = try relation("defaultText", key: "defaultText", format: 0,
            extra: ["relationMaxCount": .integer(1), "relationDefaultValue": .string(original)])
        let plan = try AnyHeartNativeDefinitionPlan(catalog: catalog([field, type()]))
        XCTAssertFalse(plan.issues.contains { $0.field == "relationDefaultValue" })
        let binding = try XCTUnwrap(plan.property(sourceKey: "defaultText"))
        let raw = try defaultProperty(plan, binding: binding)
        let definition = try AnyNativePropertyDefinition(ownerID: "namespace", raw: raw)
        let metadata = try XCTUnwrap(definition.importedDefaultMetadata)
        XCTAssertEqual(Data(try XCTUnwrap(metadata.value.string).utf8), Data(original.utf8))
        XCTAssertEqual(metadata.sourceObjectID, field.sourceObjectID)
        XCTAssertEqual(metadata.sourceSnapshotSHA256, field.snapshotSHA256)
        XCTAssertEqual(metadata.sourceJSONViewSHA256, field.viewSHA256)
        let rawDefinition = try JSONDecoder().decode(AnyJSON.self, from: Data(metadata.definitionJSON.utf8))
        XCTAssertEqual(try AnyDestinationDefinitionChecks.bytes(rawDefinition),
                       try AnyDestinationDefinitionChecks.bytes(.object(field.details)))
        for details: [String: AnyJSON] in [[:], ["defaultText": .string("")],
                                             ["defaultText": .string("explicit e\u{301}")]] {
            let row = try snapshot("page", type: 16, key: "", details: details)
            let values = try plan.values(snapshot: row, relationKeys: Array(details.keys), objects: [])
            if details.isEmpty {
                XCTAssertTrue(values.initialGroups.isEmpty)
                XCTAssertThrowsError(try plan.values(snapshot: row, relationKeys: ["defaultText"], objects: []))
            } else {
                let actual = try XCTUnwrap(values.initialGroups.first).fields.resolved(AnyDestinationPlanChecks.placeholder)
                let key = try AnyDestinationPlanChecks.placeholder(binding.record)
                XCTAssertEqual(try AnyDestinationDefinitionChecks.bytes(XCTUnwrap(actual[key])),
                               try AnyDestinationDefinitionChecks.bytes(XCTUnwrap(details["defaultText"])))
            }
        }
        XCTAssertFalse(plan.permitsDestinationWrites)
    }

    func testUnqualifiedDefaultKindsCardinalityAndReadonlyRemainBlocked() throws {
        for (format, overrides): (Int64, [String: AnyJSON]) in [
            (1, [:]), (2, [:]), (0, ["relationMaxCount": .integer(0)]),
            (0, ["relationMaxCount": .integer(2)]), (0, ["relationReadonlyValue": .bool(true)]),
            (0, ["relationDefaultValue": .integer(7)])] {
            var fields: [String: AnyJSON] = ["relationMaxCount": .integer(1),
                                           "relationDefaultValue": .string("source default")]
            fields.merge(overrides) { _, new in new }
            let source = try relation("default", key: "default", format: format, extra: fields)
            let plan = try AnyHeartNativeDefinitionPlan(catalog: catalog([source, type()]))
            XCTAssertTrue(plan.issues.contains { $0.field == "relationDefaultValue" })
            XCTAssertThrowsError(try plan.admittedSchemaItems())
        }
    }

    func testImportedDefaultContractRejectsChangedValueIdentityAndBehavior() throws {
        let field = try relation("defaultText", key: "defaultText", format: 0,
            extra: ["relationMaxCount": .integer(1), "relationDefaultValue": .string("e\u{301}")])
        let plan = try AnyHeartNativeDefinitionPlan(catalog: catalog([field, type()]))
        let raw = try defaultProperty(plan, binding: XCTUnwrap(plan.property(sourceKey: "defaultText")))
        func changedSource(_ key: String, _ value: AnyJSON) throws -> AnyJSON {
            var result = try XCTUnwrap(raw.object)
            var format = try XCTUnwrap(result["xFormat"]?.object)
            var source = try XCTUnwrap(format["pinkhaHeart"]?.object)
            source[key] = value; format["pinkhaHeart"] = .object(source); result["xFormat"] = .object(format)
            return .object(result)
        }
        for changed in [
            try changedSource("defaultValueJSON", .string("\"é\"")),
            try changedSource("defaultBehaviorContract", .string("future-auto-fill")),
            try changedSource("sourceUniqueKey", .string("rel-other")),
            try changedSource("snapshotSHA256", .string("not-a-digest"))] {
            XCTAssertThrowsError(try AnyNativePropertyDefinition(ownerID: "namespace", raw: changed))
        }
        var foreign = try XCTUnwrap(raw.object); foreign["scope"] = .string("local")
        XCTAssertThrowsError(try AnyNativePropertyDefinition(ownerID: "namespace", raw: .object(foreign)))
        // Older metadata remains available as raw source data without claiming
        // the new behavior contract. It does not create a default-value action.
        var old = try XCTUnwrap(raw.object), format = try XCTUnwrap(raw["xFormat"]?.object)
        var metadata = try XCTUnwrap(format["pinkhaHeart"]?.object)
        metadata.removeValue(forKey: "defaultBehaviorContract")
        format["pinkhaHeart"] = .object(metadata); old["xFormat"] = .object(format)
        XCTAssertNil(try AnyNativePropertyDefinition(ownerID: "namespace", raw: .object(old)).importedDefaultMetadata)
    }

    private func defaultProperty(_ plan: AnyHeartNativeDefinitionPlan,
                                 binding: AnyHeartNativeDefinitionPlan.PropertyBinding) throws -> AnyJSON {
        let item = try XCTUnwrap(plan.schemaItems.first { $0.sourceKey == binding.sourceKey })
        guard case .propertyDefinition(_, let kind, let name, let xKey, let description, let scope,
                                       .literal(let format)?, _) = item.operation else {
            throw AnyHeartNativeDefinitionPlanError.invalidValue(binding.sourceKey, "property definition required")
        }
        return .object(["id": .string("allocated-property"), "kind": .string(kind), "name": .string(name),
            "xKey": .string(xKey), "description": .string(description), "scope": .string(scope), "xFormat": format])
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


    private func nativeDescription(_ id: String = "native-description",
                                   overrides: [String: AnyJSON] = [:]) throws -> AnyHeartNativeSnapshotView {
        var fields: [String: AnyJSON] = ["name": .string("Description"), "description": .string(""),
            "relationMaxCount": .integer(1), "relationFormatIncludeTime": .bool(false)]
        fields.merge(overrides) { _, value in value }
        return try relation(id, key: "description", format: 0, extra: fields)
    }


    private func nativeIdentity(_ key: String, target: String? = nil,
                                overrides: [String: AnyJSON] = [:]) throws -> AnyHeartNativeSnapshotView {
        let captions = ["id": "Anytype ID", "spaceId": "Space ID", "type": "Object type"]
        let descriptions = ["id": "Link to itself. Used in databases", "spaceId": "Space belongs to",
                            "type": "Relation that stores the object's type"]
        var fields: [String: AnyJSON] = [
            "name": .string(try XCTUnwrap(captions[key])), "description": .string(try XCTUnwrap(descriptions[key])),
            "relationMaxCount": .integer(1), "relationFormatIncludeTime": .bool(false),
            "relationReadonlyValue": .bool(key != "id"),
            "relationFormatObjectTypes": .array(target.map { [.string($0)] } ?? []),
        ]
        fields.merge(overrides) { _, value in value }
        return try relation("native-system-property-" + key, key: key, format: 100, extra: fields)
    }

    func testCanonicalSystemIdentityDefinitionsUseOriginalNativeAddressesAndTargetEvidence() throws {
        let objectType = try type("native-type-definition", key: "objectType")
        let spaceType = try type("native-space-definition", key: "space")
        let id = try nativeIdentity("id"), space = try nativeIdentity("spaceId", target: spaceType.sourceObjectID)
        let typeRelation = try nativeIdentity("type", target: objectType.sourceObjectID)
        let rows = [id, space, typeRelation, objectType, spaceType]
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog(rows))
        for role in [AnyDestinationCanonicalPropertyBinding.IdentityRole.id, .spaceId, .type] {
            let property = try XCTUnwrap(mapper.property(sourceKey: role.rawValue))
            let canonical = try XCTUnwrap(property.canonicalBinding)
            XCTAssertEqual(canonical.identityRole, role)
            XCTAssertEqual(property.owner, .native("any")); XCTAssertEqual(property.record, .native(role.rawValue))
            XCTAssertFalse(mapper.schemaItems.contains { $0.sourceObjectID == property.relation.objectID })
            XCTAssertEqual(canonical.evidence.protobufBytes, property.relation.snapshot.protobufBytes)
            if role == .id { XCTAssertNil(canonical.targetTypeEvidence) }
            else {
                XCTAssertEqual(canonical.targetTypeEvidence?.sourceObjectID,
                               role == .spaceId ? spaceType.sourceObjectID : objectType.sourceObjectID)
            }
            let expected = AnyDestinationCanonicalPropertyBinding.nativeIdentityDescriptor(role)
            XCTAssertNoThrow(try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(
                .object(["properties": .array([expected])]), bindings: [canonical]))
            for field in ["id", "name", "description", "kind", "scope"] {
                var changed = try XCTUnwrap(expected.object); changed[field] = .string("changed")
                XCTAssertThrowsError(try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(
                    .object(["properties": .array([.object(changed)])]), bindings: [canonical]))
            }
            XCTAssertThrowsError(try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(
                .object(["properties": .array([expected, expected])]), bindings: [canonical]))
        }
        let plan = try boundPlan(rows: rows, mapper: mapper)
        XCTAssertEqual(try AnyDestinationMigrationPlan.decode(JSONEncoder().encode(plan)).binding.planSHA256,
                       plan.binding.planSHA256)
        XCTAssertFalse(mapper.permitsDestinationWrites)
    }

    func testCanonicalSystemIdentityConsumesOnlyMatchingContextWithoutPropertyWrites() throws {
        let objectType = try type("native-type-definition", key: "objectType")
        let spaceType = try type("native-space-definition", key: "space")
        let ownedType = try type()
        let rows = try [nativeIdentity("id"), nativeIdentity("spaceId", target: spaceType.sourceObjectID),
                        nativeIdentity("type", target: objectType.sourceObjectID)] + [objectType, spaceType, ownedType]
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog(rows))
        let objects: [AnyHeartNativeDefinitionPlan.ObjectBinding] = [.init(sourceObjectID: "document", destinationSourceKey: "mapped-document")]
        let values: [String: AnyJSON] = ["id": .string("document"), "spaceId": .array([.string("source-space")]),
                                       "type": .array([.string(ownedType.sourceObjectID)])]
        let document = try snapshot("document", type: 16, key: "", details: values, objectTypes: ["ot-owned"])
        let mapped = try mapper.values(snapshot: document, relationKeys: ["id", "spaceId", "type"], objects: objects)
        XCTAssertEqual(mapped.nativeIdentityRelationKeys, ["id", "spaceId", "type"])
        XCTAssertTrue(mapped.initialRelationKeys.isEmpty); XCTAssertTrue(mapped.deferredRelationKeys.isEmpty)
        XCTAssertTrue(mapped.initialGroups.isEmpty); XCTAssertTrue(mapped.deferredGroups.isEmpty)
        XCTAssertEqual(try mapped.initialProperties.resolved(AnyDestinationPlanChecks.placeholder), .object([:]))
        for role in ["id", "spaceId", "type"] {
            for invalid: AnyJSON in [.null, .string("foreign"), .array([]), .array([.string("document"), .string("document")])] {
                var changed = values; changed[role] = invalid
                let page = try snapshot("document", type: 16, key: "", details: changed, objectTypes: ["ot-owned"])
                XCTAssertThrowsError(try mapper.values(snapshot: page, relationKeys: [role], objects: objects))
            }
        }
        XCTAssertThrowsError(try mapper.values(snapshot: document, relationKeys: ["id"], objects: []))
        let wrongType = try snapshot("document", type: 16, key: "", details: values, objectTypes: ["ot-space"])
        XCTAssertThrowsError(try mapper.values(snapshot: wrongType, relationKeys: ["type"], objects: objects))
        let typeURL = try snapshot("document", type: 16, key: "", details: ["type": .string("ot-owned")], objectTypes: ["ot-owned"])
        XCTAssertEqual(try mapper.values(snapshot: typeURL, relationKeys: ["type"], objects: objects).nativeIdentityRelationKeys, ["type"])
        let raw: AnyJSON = .object(["objectId": .string("destination"), "record": .object([
            "id": .string("destination"), "spaceId": .string("destination-space"), "_applySeq": .integer(1)])])
        XCTAssertNoThrow(try AnyDestinationMigrationVerifier.objectRecord(raw, id: "destination", spaceID: "destination-space"))
        XCTAssertThrowsError(try AnyDestinationMigrationVerifier.objectRecord(raw, id: "document", spaceID: "destination-space"))
        XCTAssertThrowsError(try AnyDestinationMigrationVerifier.objectRecord(raw, id: "destination", spaceID: "source-space"))
    }

    func testCanonicalSystemIdentityOverridesAndForeignCapturedTargetTypeRefuse() throws {
        let target = try type("native-type-definition", key: "objectType")
        let relation = try nativeIdentity("type", target: target.sourceObjectID)
        let evidence = try AnyDestinationDefinitionEvidence(snapshot: relation)
        XCTAssertThrowsError(try AnyDestinationCanonicalPropertyBinding(evidence: evidence))
        let wrongTarget = try type(target.sourceObjectID, key: "space")
        XCTAssertThrowsError(try AnyDestinationCanonicalPropertyBinding(evidence: evidence,
            targetTypeEvidence: .init(snapshot: wrongTarget)))
        let canonical = try AnyDestinationCanonicalPropertyBinding(evidence: evidence, targetTypeEvidence: .init(snapshot: target))
        for mutation: [String: AnyJSON] in [
            ["name": .string("Overridden")], ["description": .string("Overridden")],
            ["relationReadonlyValue": .bool(false)], ["relationMaxCount": .integer(2)],
            ["relationDefaultValue": .array([])], ["relationFormatIncludeTime": .bool(true)],
            ["futureField": .bool(true)]] {
            let changed = try nativeIdentity("type", target: target.sourceObjectID, overrides: mutation)
            let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog([changed, target]))
            XCTAssertNil(mapper.property(sourceKey: "type"))
            XCTAssertTrue(mapper.issues.contains { $0.field == "canonical-type" })
            XCTAssertFalse(mapper.schemaItems.contains { $0.sourceObjectID == changed.sourceObjectID })
            XCTAssertThrowsError(try mapper.admittedSchemaItems())
        }
        var encoded = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(canonical)).object)
        encoded["propertyID"] = .string("id")
        XCTAssertThrowsError(try JSONDecoder().decode(AnyDestinationCanonicalPropertyBinding.self,
            from: AnyDestinationDefinitionChecks.bytes(.object(encoded))))
        let alteredTarget = try snapshot(target.sourceObjectID, type: 528, key: target.uniqueKey,
                                         details: target.details, protobufMarker: "-changed-native-original")
        let detached = try AnyHeartNativeDefinitionPlan(catalog: catalog([relation, alteredTarget]))
        XCTAssertThrowsError(try boundPlan(rows: [relation, target], mapper: detached))
    }

    func testCanonicalDescriptionSharesNativeNamespaceWithoutChangingTitleIdentity() throws {
        let name = try nativeName(), description = try nativeDescription()
        let sourceType = try type(extra: ["recommendedRelations": .array([.string(description.sourceObjectID), .string(name.sourceObjectID)])])
        let rows = [name, description, sourceType]
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog(rows))
        let binding = try XCTUnwrap(mapper.property(sourceKey: "description"))
        XCTAssertFalse(binding.isCanonicalName)
        XCTAssertTrue(try XCTUnwrap(mapper.property(sourceKey: "name")).isCanonicalName)
        XCTAssertEqual(binding.owner, .native("any")); XCTAssertEqual(binding.record, .native("description"))
        XCTAssertEqual(binding.kind, "string"); XCTAssertEqual(binding.format, "longtext")
        XCTAssertNil(mapper.propertyOwner)
        XCTAssertFalse(mapper.schemaItems.contains { $0.sourceObjectID == description.sourceObjectID })
        let plan = try boundPlan(rows: rows, mapper: mapper)
        XCTAssertEqual(try AnyDestinationMigrationPlan.decode(JSONEncoder().encode(plan)).binding.planSHA256, plan.binding.planSHA256)
        for details: [String: AnyJSON] in [
            ["name": .string("title")],
            ["name": .string("title"), "description": .string("")],
            ["name": .string("title"), "description": .string("e\u{301} — תיאור\nsecond line")]] {
            let source = try snapshot("page", type: 16, key: "", details: details)
            let values = try mapper.values(snapshot: source, relationKeys: details.keys.sorted(), objects: [])
            let actual = try values.initialProperties.resolved(AnyDestinationPlanChecks.placeholder)
            XCTAssertEqual(try AnyDestinationDefinitionChecks.bytes(XCTUnwrap(actual["any"])),
                           try AnyDestinationDefinitionChecks.bytes(.object(details)))
            XCTAssertEqual(values.initialGroups.count, 1)
        }
        let item = try XCTUnwrap(mapper.schemaItems.first { $0.sourceKey == mapper.types[0].sourceKey })
        guard case .typeDefinition(let seed) = item.operation else { return XCTFail("type") }
        let layout = try XCTUnwrap(seed.layout).resolved(AnyDestinationPlanChecks.placeholder)
        XCTAssertEqual(layout["config"]?["pinkhaHeart"]?["recommended"], .array([
            .object(["ownerId": .string("any"), "propertyId": .string("description")]),
            .object(["ownerId": .string("any"), "propertyId": .string("name")])]))
    }

    func testCanonicalDescriptionRefusesOverridesAndRequiresExactLiveDescriptor() throws {
        let original = try nativeDescription()
        let binding = try AnyDestinationCanonicalPropertyBinding(evidence: .init(snapshot: original))
        XCTAssertEqual(binding.nativeContract, AnyDestinationCanonicalPropertyBinding.descriptionContract)
        for override: [String: AnyJSON] in [
            ["relationDefaultValue": .string("override")], ["relationReadonlyValue": .bool(true)],
            ["relationMaxCount": .integer(2)], ["relationFormat": .integer(1)],
            ["name": .string("Another caption")], ["description": .string("Changed semantics")],
            ["futureSemantics": .bool(true)]] {
            let changed = try nativeDescription(overrides: override)
            let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog([changed, type()]))
            XCTAssertNil(mapper.property(sourceKey: "description"))
            XCTAssertTrue(mapper.issues.contains { $0.field == "canonical-description" })
            XCTAssertFalse(mapper.schemaItems.contains { $0.sourceObjectID == changed.sourceObjectID })
            XCTAssertThrowsError(try mapper.admittedSchemaItems())
        }
        let expected = AnyDestinationCanonicalPropertyBinding.nativeDescriptionDescriptor
        XCTAssertNoThrow(try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(
            .object(["properties": .array([expected])]), bindings: [binding]))
        for key in ["id", "name", "description", "kind", "scope", "xFormat"] {
            var changed = try XCTUnwrap(expected.object); changed[key] = .string("changed")
            XCTAssertThrowsError(try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(
                .object(["properties": .array([.object(changed)])]), bindings: [binding]))
        }
        XCTAssertThrowsError(try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(
            .object(["properties": .array([expected, expected])]), bindings: [binding]))
        XCTAssertThrowsError(try AnyDestinationDefinitionChecks.verifyNativeCanonicalProperties(
            .object(["properties": .array([AnyDestinationCanonicalPropertyBinding.nativeDescriptor])]), bindings: [binding]))
        var encoded = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(binding)).object)
        encoded["propertyID"] = .string("name")
        XCTAssertThrowsError(try JSONDecoder().decode(AnyDestinationCanonicalPropertyBinding.self,
            from: AnyDestinationDefinitionChecks.bytes(.object(encoded))))
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
        XCTAssertEqual(c.types.filter { $0.orderID != nil }.count, 1)
        XCTAssertEqual(custom.orderID.map { Data($0.utf8) }, custom.snapshot.details["orderId"]?.string.map { Data($0.utf8) })
        XCTAssertNotNil(custom.orderID)
        XCTAssertFalse(c.issues.contains { $0.kind == .unknownDetailField && $0.field == "orderId" })
        XCTAssertEqual(custom.featuredRelations, try ["text", "status"].map { try XCTUnwrap(labels[$0]).objectID })
        XCTAssertEqual(custom.recommendedRelations, try ["number", "date", "object", "tag"].map { try XCTUnwrap(labels[$0]).objectID })
        XCTAssertEqual(custom.hiddenRelations, [try XCTUnwrap(labels["checkbox"]).objectID])
        XCTAssertEqual(try XCTUnwrap(labels["object"]).targetTypeIDs, [custom.objectID])
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: c)
        for role in [AnyDestinationCanonicalPropertyBinding.DerivedRole.author, .createdAt, .modifiedAt, .modifiedBy] {
            let property = try XCTUnwrap(mapper.property(sourceKey: role.sourceKey))
            XCTAssertEqual(property.canonicalBinding?.derivedRole, role)
            XCTAssertFalse(mapper.schemaItems.contains { $0.sourceObjectID == property.relation.objectID })
        }
        let orderedItem = try XCTUnwrap(mapper.schemaItems.first {
            $0.sourceObjectID == custom.objectID &&
                { if case .typeDefinition = $0.operation { return true }; return false }($0)
        })
        guard case .typeDefinition(let orderedSpec) = orderedItem.operation,
              case .literal(let orderedMetadata) = orderedSpec.meta else { return XCTFail("original type order metadata") }
        XCTAssertEqual(orderedMetadata[AnyNativeImportedTypeOrder.valueKey], custom.snapshot.details["orderId"])
        XCTAssertEqual(orderedMetadata[AnyNativeImportedTypeOrder.scopeKey], .string(c.contentSHA256))
        for role in [AnyDestinationCanonicalPropertyBinding.IdentityRole.id, .spaceId, .type] {
            let property = try XCTUnwrap(mapper.property(sourceKey: role.rawValue))
            let canonical = try XCTUnwrap(property.canonicalBinding)
            XCTAssertEqual(canonical.identityRole, role)
            XCTAssertEqual(property.owner, .native("any")); XCTAssertEqual(property.record, .native(role.rawValue))
            XCTAssertFalse(mapper.schemaItems.contains { $0.sourceObjectID == property.relation.objectID })
            let source = try AnyDestinationSourceBinding(bundle: bundle, semanticPlanSHA256: c.contentSHA256,
                sourceObjectIDs: bundle.objects.map(\.sourceObjectID))
            XCTAssertNoThrow(try canonical.requireSource(source, objectID: property.relation.objectID))
        }
        let canonicalDescription = try XCTUnwrap(mapper.property(sourceKey: "description"))
        XCTAssertFalse(canonicalDescription.isCanonicalName)
        XCTAssertEqual(canonicalDescription.owner, .native("any"))
        XCTAssertEqual(canonicalDescription.record, .native("description"))
        XCTAssertEqual(canonicalDescription.canonicalBinding?.evidence.jsonViewBytes,
                       canonicalDescription.relation.snapshot.jsonViewBytes)
        XCTAssertFalse(mapper.schemaItems.contains { $0.sourceObjectID == canonicalDescription.relation.objectID })
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
        let capturedText = try XCTUnwrap(labels["text"])
        let textBinding = try XCTUnwrap(mapper.property(sourceKey: capturedText.relationKey))
        let defaultMetadata = try XCTUnwrap(AnyNativePropertyDefinition(ownerID: "allocated-namespace",
            raw: defaultProperty(mapper, binding: textBinding)).importedDefaultMetadata)
        XCTAssertEqual(try AnyDestinationDefinitionChecks.bytes(defaultMetadata.value),
                       try AnyDestinationDefinitionChecks.bytes(XCTUnwrap(capturedText.defaultValue)))
        XCTAssertEqual(Data(defaultMetadata.definitionJSON.utf8),
                       try AnyDestinationDefinitionChecks.bytes(.object(capturedText.snapshot.details)))
        XCTAssertFalse(mapper.issues.contains { $0.sourceObjectID == capturedText.objectID && $0.field == "relationDefaultValue" })
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
