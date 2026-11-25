import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

/// Detached schema controls only. Synthetic protobuf bytes are never source authority.
@Suite("Captured Pinkha schema and canonical property composition")
struct NativePinkhaSourceTests {
    private let space = "captured-space"
    private func snapshot(_ id: String, nativeType: Int64 = 16, key: String = "",
                          types: [String] = [], details: [String: AnyJSON] = [:]) throws -> AnyHeartNativeSnapshotView {
        let pb = Data(("detached-schema-control:" + id).utf8)
        let raw: AnyJSON = .object(["Contract": .string("pinkha-native-snapshot-json-v1"),
            "SpaceID": .string(space), "ObjectID": .string(id), "NativeType": .integer(nativeType),
            "UniqueKey": .string(key), "SnapshotSHA256": .string(AnyContentDigest.sha256(pb)),
            "SnapshotBytes": .integer(Int64(pb.count)),
            "Snapshot": .object(["blocks": .array([]), "details": .object(details),
                "objectTypes": .array(types.map(AnyJSON.string)), "relationLinks": .array([])])])
        return try .init(jsonView: JSONEncoder().encode(raw), snapshotBytes: pb, sourceSpaceID: space, sourceObjectID: id)
    }
    private func manifest() -> [String: AnyJSON] {
        ["schemaVersion": .integer(1), "spaceId": .string(space), "manifestObjectId": .string("manifest"),
         "provisioningState": .string("complete"), "parentPropertyId": .string("pParent"),
         "parentPropertyKey": .string("kParent"), "orderPropertyId": .string("pOrder"),
         "orderPropertyKey": .string("kOrder"), "documentAssociationsPropertyId": .string("pAssociations"),
         "documentAssociationsPropertyKey": .string("kAssociations"), "folderTypeId": .string("tFolder"),
         "bookFolderTypeId": .string("tBook"), "registeredDocumentTypes": .object([
            "chiddush": .string("tChiddush"), "article": .string("tArticle"), "research": .string("tResearch")]),
         "defaultTemplateIds": .object(["chiddush": .string("templateC"), "article": .string("templateA"), "research": .string("templateR")]),
         "createdAt": .string("2026-11-25T00:00:00Z"), "updatedAt": .string("2026-11-25T00:00:01Z")]
    }
    private func rows(manifest: [String: AnyJSON]? = nil,
                      a: [String: AnyJSON] = [:], b: [String: AnyJSON] = [:]) throws -> [AnyHeartNativeSnapshotView] {
        var result: [AnyHeartNativeSnapshotView] = []
        for (id, key, format) in [("pParent", "kParent", 100), ("pOrder", "kOrder", 2), ("pAssociations", "kAssociations", 0)] {
            result.append(try snapshot(id, nativeType: 521, key: "rel-" + key,
                details: ["name": .string("Same misleading display name"), "relationKey": .string(key), "relationFormat": .integer(Int64(format))]))
        }
        for (id, key) in [("tFolder", "folder"), ("tBook", "book"), ("tChiddush", "chiddush"), ("tArticle", "article"), ("tResearch", "research")] {
            result.append(try snapshot(id, nativeType: 528, key: "ot-" + key,
                details: ["name": .string("Same misleading display name"), "recommendedLayout": .integer(0)]))
        }
        for id in ["templateC", "templateA", "templateR"] { result.append(try snapshot(id)) }
        let encoded = try JSONEncoder().encode(AnyJSON.object(manifest ?? self.manifest()))
        result.append(try snapshot("manifest", details: ["name": .string(PinkhaSchemaRoles.manifestName),
            "description": .string(String(decoding: encoded, as: UTF8.self)), "isHidden": .bool(true)]))
        result.append(try snapshot("folder", types: ["ot-folder"], details: ["kOrder": .integer(1000)]))
        result.append(try snapshot("doc-a", types: ["ot-chiddush"],
            details: ["kParent": .array([.string("folder")]), "kOrder": .integer(1000)].merging(a) { _, new in new }))
        result.append(try snapshot("doc-b", types: ["ot-article"],
            details: ["kParent": .string("folder"), "kOrder": .integer(2000)].merging(b) { _, new in new }))
        return result
    }
    private func discover(_ rows: [AnyHeartNativeSnapshotView]) throws -> AnyHeartNativePinkhaSource? {
        let catalog = try AnyHeartNativeDefinitionCatalog(sourceAccountID: "source-account", sourceSpaceID: space,
            captureManifestSHA256: String(repeating: "a", count: 64),
            sourceWitnessSHA256: String(repeating: "b", count: 64), snapshots: rows)
        return try .discover(catalog: catalog, snapshots: rows)
    }
    private func canonical(object: String = "doc-a", semantic: Bool = true) throws -> Data {
        let location = TorahAssociationLocation(spaceId: space, target: .object(objectId: object))
        var item = TorahAssociationItem(id: "source-item", kind: .ref, role: .context,
            providerID: "sefaria", externalID: "Genesis 1:1", canonicalKey: "Genesis.1.1",
            labelHe: "בראשית א׳ א׳", createdAt: Date(timeIntervalSince1970: 123),
            customMetadata: ["future": "unchanged"], unknownFields: ["preserved": .array([.null, .bool(false)])])
        if semantic {
            let anchor = try PinkhaSemanticTextAnchor(spaceID: space, objectID: object,
                id: UUID(uuidString: "79c52b11-36bc-4d22-a967-e8c04e123456")!)
            item = try TorahSemanticAnchorAssociation(anchor: anchor).attaching(to: item, location: location)
        }
        return try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(records: [
            .init(location: location, item: item, unknownFields: ["recordFuture": .string("retained")])
        ], unknownFields: ["envelopeFuture": .number(4)]))
    }

    @Test func manifestBindsExactNativeIDsAndRetainsLegacyParentRepresentation() throws {
        let source = try #require(try discover(rows()))
        #expect(source.parentProperty.objectID == "pParent" && source.parentProperty.key == "kParent")
        #expect(source.associationsProperty.format == .longText)
        #expect(source.hierarchy.count == 3 && source.canonicalDocuments.isEmpty)
        let a = try #require(source.hierarchy.first { $0.snapshot.sourceObjectID == "doc-a" })
        let b = try #require(source.hierarchy.first { $0.snapshot.sourceObjectID == "doc-b" })
        #expect(a.parentObjectID == "folder" && b.parentObjectID == "folder")
        #expect(a.originalParent == .array([.string("folder")]) && b.originalParent == .string("folder"))
        #expect(a.role == .writingDocument("chiddush") && b.order == 2000)
        #expect(source.issues.isEmpty && !source.permitsDestinationWrites)
    }

    @Test func capturedCanonicalBytesComposeStrictSemanticOwnerRemap() throws {
        let original = try canonical()
        let source = try #require(try discover(rows(a: ["kAssociations": .string(String(decoding: original, as: UTF8.self))])))
        #expect(source.canonicalDocuments.count == 1 && source.canonicalDocuments[0].sourceBytes == original)
        let destination = try AnyTorahWorkspace(accountID: "destination-account", spaceID: "destination-space")
        let plan = try source.canonicalPlan(sourceObjectID: "doc-a", workspace: destination,
            objectIDMap: ["doc-a": "destination-document"], blockIDMap: [:], migrationKey: "captured-source")
        #expect(plan.sourceBytes == original && plan.operations.count == 1)
        let location = TorahAssociationLocation(spaceId: destination.spaceID, target: .object(objectId: "destination-document"))
        let decoded = try TorahAssociationPayloadCodec().decodeCanonicalDocument(plan.operations[0].payload, legacyLocation: location)
        let record = try #require(decoded.records.first)
        let anchor = try #require(try TorahSemanticAnchorAssociation.decoding(record.item, location: location))
        #expect(anchor.anchor.id.uuidString.lowercased() == "79c52b11-36bc-4d22-a967-e8c04e123456")
        #expect(record.item.id == "source-item" && record.item.customMetadata?["future"] == "unchanged")
        #expect(record.unknownFields["recordFuture"] == .string("retained"))
        #expect(decoded.unknownFields["envelopeFuture"] == .number(4))
        #expect(throws: AnyHeartNativePinkhaSourceError.self) {
            try source.canonicalPlan(sourceObjectID: "doc-a", workspace: destination,
                objectIDMap: ["foreign-source": "destination-document"], blockIDMap: [:], migrationKey: "capture")
        }
    }

    @Test func absentAndExplicitEmptyCanonicalPropertiesStayDistinct() throws {
        let source = try #require(try discover(rows(a: ["kAssociations": .string("")])))
        #expect(source.canonicalDocuments.count == 1 && source.canonicalDocuments[0].snapshot.sourceObjectID == "doc-a")
        #expect(source.canonicalDocuments[0].sourceBytes.isEmpty && source.canonicalDocuments[0].records.isEmpty)
        #expect(source.hierarchy.count == 3)
        #expect(throws: AnyHeartNativePinkhaSourceError.self) {
            try source.canonicalPlan(sourceObjectID: "doc-a",
                workspace: AnyTorahWorkspace(accountID: "destination", spaceID: "destination"),
                objectIDMap: ["doc-a": "destination"], blockIDMap: [:], migrationKey: "capture")
        }
        #expect(throws: AnyHeartNativePinkhaSourceError.self) { try discover(rows(a: ["kAssociations": .null])) }
    }

    @Test func manifestAmbiguityAndIncompleteForeignFutureBindingsCannotChooseConvenientCopy() throws {
        var twice = try rows()
        var other = manifest(); other["manifestObjectId"] = .string("other-manifest")
        let payload = try JSONEncoder().encode(AnyJSON.object(other))
        twice.append(try snapshot("other-manifest", details: ["name": .string(PinkhaSchemaRoles.manifestName),
            "description": .string(String(decoding: payload, as: UTF8.self))]))
        #expect(throws: AnyHeartNativePinkhaSourceError.self) { try discover(twice) }
        for (field, value) in [("schemaVersion", AnyJSON.integer(2)), ("provisioningState", .string("inProgress")),
                               ("parentPropertyKey", .string("kOrder")), ("folderTypeId", .string("tArticle"))] {
            var changed = manifest(); changed[field] = value
            #expect(throws: AnyHeartNativePinkhaSourceError.self) { try discover(rows(manifest: changed)) }
        }
        var foreign = manifest(); foreign["spaceId"] = .string("foreign-space")
        #expect(try discover(rows(manifest: foreign)) == nil)
    }

    @Test func nameOnlyAndWrongPropertyDefinitionNeverIdentifySchemaRoles() throws {
        let none = try rows().filter { $0.sourceObjectID != "manifest" }
        #expect(try discover(none) == nil)
        var wrong = try rows().filter { $0.sourceObjectID != "pParent" }
        wrong.append(try snapshot("pParent", nativeType: 521, key: "rel-kParent",
            details: ["name": .string("הורה"), "relationKey": .string("kParent"), "relationFormat": .integer(0)]))
        #expect(throws: AnyHeartNativePinkhaSourceError.self) { try discover(wrong) }
        var missing = manifest(); missing["parentPropertyId"] = .string("missing-native-property")
        #expect(throws: AnyHeartNativePinkhaSourceError.self) { try discover(rows(manifest: missing)) }
    }

    @Test func malformedCanonicalOwnerAndMultipleParentsRemainRefused() throws {
        let foreign = try canonical(object: "other-document")
        #expect(throws: AnyHeartNativePinkhaSourceError.self) {
            try discover(rows(a: ["kAssociations": .string(String(decoding: foreign, as: UTF8.self))]))
        }
        #expect(throws: AnyHeartNativePinkhaSourceError.self) {
            try discover(rows(a: ["kParent": .array([.string("folder"), .string("doc-b")])]))
        }
        #expect(throws: AnyHeartNativePinkhaSourceError.self) { try discover(rows(a: ["kOrder": .bool(false)])) }
        #expect(throws: AnyHeartNativePinkhaSourceError.self) { try discover(rows(a: ["kOrder": .integer(9_007_199_254_740_993)])) }
    }

    @Test func unknownManifestFieldsAndHierarchyCyclesAreRetainedAsBlockers() throws {
        var manifest = manifest(); manifest["futureSetting"] = .object(["original": .bool(false)])
        let source = try #require(try discover(rows(manifest: manifest, a: ["kParent": .string("doc-b")], b: ["kParent": .string("doc-a")])))
        #expect(source.rawManifest["futureSetting"] == .object(["original": .bool(false)]))
        #expect(source.issues.contains { $0.reason == "unknown-manifest-field-retained" })
        #expect(source.issues.filter { $0.reason == "hierarchy-cycle-retained" }.count == 2)
        #expect(source.hierarchy.first { $0.snapshot.sourceObjectID == "doc-a" }?.parentObjectID == "doc-b")
        #expect(!source.permitsDestinationWrites)
    }

    @Test func duplicateReservedManifestKeysAndEmptyTemplateIdentityAreRejected() throws {
        var original = try rows().filter { $0.sourceObjectID != "manifest" }
        let good = String(decoding: try JSONEncoder().encode(AnyJSON.object(manifest())), as: UTF8.self)
        let duplicate = "{\"schemaVersion\":1," + good.dropFirst()
        original.append(try snapshot("manifest", details: ["name": .string(PinkhaSchemaRoles.manifestName),
            "description": .string(duplicate)]))
        do { _ = try discover(original); Issue.record("Duplicate source key was accepted") } catch {}
        var broken = manifest(); broken["defaultTemplateIds"] = .object(["chiddush": .string(""), "article": .string("templateA"), "research": .string("templateR")])
        #expect(throws: AnyHeartNativePinkhaSourceError.self) { try discover(rows(manifest: broken)) }
    }
}
