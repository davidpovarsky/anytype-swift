import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

/// These descriptors are explicitly synthetic semantic controls. They do not
/// stand in for a native capture, account session or destination admission.
final class CompiledRelationResolverTests: XCTestCase {
    private func descriptor(_ key: String, fields: [String: AnyJSON] = [:],
                            marker: String = "") throws -> AnyHeartNativeBundledDefinition {
        let protobuf = Data(("synthetic-compiled-relation:" + key + marker).utf8)
        var definition: [String: AnyJSON] = ["id": .string("_br" + key), "key": .string(key)]
        definition.merge(fields) { _, value in value }
        let view: AnyJSON = .object([
            "Contract": .string("pinkha-native-bundled-definition-json-v1"),
            "Kind": .string("property"), "Key": .string(key),
            "ProtobufMessage": .string("anytype.model.Relation"),
            "ProtobufSHA256": .string(AnyContentDigest.sha256(protobuf)),
            "ProtobufBytes": .integer(Int64(protobuf.count)), "Definition": .object(definition),
        ])
        return try .init(kind: "property", key: key, protobufMessage: "anytype.model.Relation",
                         protobuf: protobuf, jsonView: JSONEncoder().encode(view))
    }
    private func captured(_ id: String, key: String) throws -> AnyHeartNativeSnapshotView {
        let protobuf = Data(("synthetic-captured-relation:" + id).utf8)
        let view: AnyJSON = .object([
            "Contract": .string("pinkha-native-snapshot-json-v1"), "SpaceID": .string("source-space"),
            "ObjectID": .string(id), "NativeType": .integer(521), "UniqueKey": .string("rel-" + key),
            "SnapshotSHA256": .string(AnyContentDigest.sha256(protobuf)),
            "SnapshotBytes": .integer(Int64(protobuf.count)),
            "Snapshot": .object(["blocks": .array([]), "objectTypes": .array([]),
                "relationLinks": .array([]), "details": .object([
                    "relationKey": .string(key), "relationFormat": .integer(1),
                    "name": .string("Actual captured override"), "relationDefaultValue": .string("owned"),
                ])]),
        ])
        return try .init(jsonView: JSONEncoder().encode(view), snapshotBytes: protobuf,
                         sourceSpaceID: "source-space", sourceObjectID: id)
    }
    private func catalog(_ rows: [AnyHeartNativeSnapshotView] = [],
                         compiled: [AnyHeartNativeBundledDefinition]) throws -> AnyHeartNativeDefinitionCatalog {
        try .init(sourceAccountID: "source-account", sourceSpaceID: "source-space",
                  captureManifestSHA256: String(repeating: "a", count: 64),
                  sourceWitnessSHA256: String(repeating: "b", count: 64),
                  snapshots: rows, compiledDefinitions: compiled)
    }

    func testNativeProto3ScalarDefaultsDoNotInventAnAbsentValueOrObject() throws {
        let source = try descriptor("homepage")
        let row = try AnyHeartNativeCompiledRelation(source: source)
        XCTAssertEqual(row.relationKey, "homepage")
        XCTAssertEqual(row.sourceIdentity, "property:homepage")
        XCTAssertEqual(row.rawFormat, 0); XCTAssertEqual(row.format, .longText)
        XCTAssertEqual(row.maximumCount, 0); XCTAssertEqual(row.scope, 0)
        XCTAssertEqual(row.dataSource, 0); XCTAssertEqual(row.revision, 0)
        XCTAssertFalse(row.hidden); XCTAssertFalse(row.readonlyValue)
        XCTAssertFalse(row.readonlyDefinition); XCTAssertFalse(row.multiple); XCTAssertFalse(row.includeTime)
        XCTAssertTrue(row.targetTypeIDs.isEmpty); XCTAssertTrue(row.selectDictionary.isEmpty)
        XCTAssertNil(row.defaultValue)
        XCTAssertEqual(row.source.protobufBytes, source.protobufBytes)
        XCTAssertEqual(row.source.jsonViewBytes, source.jsonViewBytes)
        let c = try catalog(compiled: [source])
        XCTAssertEqual(c.relations.count, 0)
        XCTAssertNil(c.relation(objectID: "_brhomepage"))
        XCTAssertNil(c.relation(key: "homepage"))
        XCTAssertNotNil(c.compiledRelation(key: "homepage"))
        guard case .compiled(let resolved)? = c.resolvedRelation(key: "homepage") else {
            return XCTFail("Compiled vocabulary must remain separate from native objects")
        }
        XCTAssertEqual(resolved.sourceIdentity, source.identity)
        XCTAssertFalse(c.permitsDestinationWrites)
    }

    func testExplicitEmptyFalseZeroAndNullDefaultsRemainDistinct() throws {
        let values: [AnyJSON] = [.null, .bool(false), .integer(0), .string(""), .array([]), .object([:])]
        for value in values {
            let source = try descriptor("owned", fields: ["defaultValue": value])
            let row = try AnyHeartNativeCompiledRelation(source: source)
            XCTAssertEqual(row.defaultValue, value)
            XCTAssertNotNil(row.defaultValue)
        }
        let row = try AnyHeartNativeCompiledRelation(source: descriptor("owned", fields: [
            "name": .string("כותרת a\u{301}"), "description": .string("Original"),
            "format": .integer(4), "includeTime": .bool(true), "maxCount": .integer(1),
            "readOnlyRelation": .bool(true), "readOnly": .bool(false),
            "scope": .integer(1), "dataSource": .integer(2), "hidden": .bool(true),
            "multi": .bool(true), "objectTypes": .array([.string("ot-page")]),
            "revision": .string("9223372036854775807"), "creator": .string("creator"),
        ]))
        XCTAssertEqual(row.format, .date); XCTAssertEqual(row.maximumCount, 1)
        XCTAssertTrue(row.includeTime); XCTAssertTrue(row.readonlyDefinition)
        XCTAssertFalse(row.readonlyValue); XCTAssertTrue(row.hidden); XCTAssertTrue(row.multiple)
        XCTAssertEqual(row.targetTypeIDs, ["ot-page"])
        XCTAssertEqual(row.revision, Int64.max); XCTAssertEqual(row.scope, 1); XCTAssertEqual(row.dataSource, 2)
        XCTAssertEqual(Data(row.name.utf8), Data("כותרת a\u{301}".utf8))
    }

    func testMalformedKnownFieldsRefuseAndFutureFieldsStayExplicitIssues() throws {
        for (key, value) in [
            ("format", AnyJSON.string("0")), ("maxCount", .integer(Int64(Int32.max) + 1)),
            ("includeTime", .integer(0)), ("readOnly", .null), ("scope", .string("type")),
            ("objectTypes", .array([.integer(1)])), ("selectDict", .array([.string("option")])),
            ("revision", .integer(1)), ("revision", .string("01")), ("revision", .string("+1")),
            ("revision", .string("9223372036854775808")),
        ] {
            XCTAssertThrowsError(try AnyHeartNativeCompiledRelation(
                source: descriptor("owned", fields: [key: value])), key)
        }
        let source = try descriptor("owned", fields: ["futureSemantics": .object(["live": .bool(true)])])
        let c = try catalog(compiled: [source])
        XCTAssertEqual(c.compiledRelations.first?.unknownFields, ["futureSemantics"])
        XCTAssertTrue(c.issues.contains { $0.kind == .compiledDescriptorIssue && $0.field == "futureSemantics" })
        XCTAssertEqual(c.compiledRelations.first?.source.definition["futureSemantics"],
                       .object(["live": .bool(true)]))
    }

    func testCapturedOverrideWinsAndAmbiguousCaptureCannotFallBack() throws {
        let source = try descriptor("owned", fields: ["name": .string("Compiled original"), "format": .integer(0)])
        let override = try captured("captured-relation", key: "owned")
        let c = try catalog([override], compiled: [source])
        guard case .captured(let selected)? = c.resolvedRelation(key: "owned") else {
            return XCTFail("Current native object must take precedence over the registry")
        }
        XCTAssertEqual(selected.objectID, "captured-relation")
        XCTAssertEqual(selected.defaultValue, .string("owned"))
        XCTAssertEqual(c.compiledRelation(key: "owned")?.name, "Compiled original")
        let ambiguous = try catalog([override, captured("second-capture", key: "owned")], compiled: [source])
        XCTAssertNil(ambiguous.resolvedRelation(key: "owned"))
        XCTAssertTrue(ambiguous.issues.contains { $0.kind == .duplicateRelationKey })
        XCTAssertThrowsError(try catalog(compiled: [source, source]))
        XCTAssertNil(c.resolvedRelation(key: "missing"))
    }

    func testCompiledWireIdentityChangesCatalogBindingWithoutInventingNativeRows() throws {
        let first = try descriptor("owned", fields: ["name": .string("Title")])
        let changed = try descriptor("owned", fields: ["name": .string("Title")], marker: "-wire-revision")
        let a = try catalog(compiled: [first]), b = try catalog(compiled: [changed])
        XCTAssertNotEqual(a.contentSHA256, b.contentSHA256)
        XCTAssertTrue(a.relations.isEmpty); XCTAssertTrue(b.relations.isEmpty)
        XCTAssertFalse(a.permitsDestinationWrites); XCTAssertFalse(b.permitsDestinationWrites)
        let two = try descriptor("second", fields: ["name": .string("Second")])
        XCTAssertEqual(try catalog(compiled: [first, two]).contentSHA256,
                       try catalog(compiled: [two, first]).contentSHA256)
    }
}
