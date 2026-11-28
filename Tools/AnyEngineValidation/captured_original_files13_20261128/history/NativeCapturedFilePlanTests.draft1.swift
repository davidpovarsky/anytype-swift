import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Detached, explicitly synthetic controls for the captured generic-file
/// projection. Head/block JSON follows the pinned Heart constructors/protobuf;
/// descriptor rows and opaque PB/metadata/payload identities are test inputs.
/// These controls do not claim a genuine nonempty native capture, native
/// checksum verification, a destination upload, or current authority.
final class NativeCapturedFilePlanTests: XCTestCase {
    func testDistinctSourceHeadPayloadAndDocumentOwnerCreateOnePreparedFileItem() throws {
        let fixture = try FilePlanFixture()
        let plan = try fixture.makePlan()
        let entry = try XCTUnwrap(plan.entries.first)
        XCTAssertEqual(plan.entries.count, 1)
        XCTAssertEqual(entry.sourceHeadID, "file-head-a")
        XCTAssertEqual(entry.sourcePayloadID, "native-payload-a")
        XCTAssertEqual(entry.sourceOwnerID, "source-page")
        XCTAssertNotEqual(entry.sourceHeadID, entry.sourcePayloadID)
        XCTAssertNotEqual(entry.sourceHeadID, entry.sourceOwnerID)
        XCTAssertEqual(entry.item.sourceObjectID, fixture.owners[0].id)
        XCTAssertEqual(entry.item.expectedRecordCount, 1)
        XCTAssertEqual(entry.item.operation, .file(
            owner: .mapped(sourceKey: entry.ownerSourceKey, slot: .objectID, encoding: .rawID),
            name: "report.txt", mime: "text/plain", size: 8192,
            contentSHA256: fixture.variants[0].payloadSHA256))
        XCTAssertEqual(entry.reference, .mapped(sourceKey: entry.sourceKey, slot: .fileID, encoding: .fileURI))
        let page = try fixture.owners[0].decoded()
        XCTAssertEqual(try plan.value(snapshot: page, relationKey: "attachment",
                                     original: .string("file-head-a")),
                       .array([.reference(entry.reference)]))
        // Native checksum metadata is not the independently verified plaintext
        // SHA256; a false upload-checksum flag alone is not missing plaintext.
        XCTAssertNotEqual(fixture.variants[0].raw["NativeChecksum"]?.string, entry.payloadSHA256)
        XCTAssertEqual(fixture.variants[0].raw["UploadChecksumMatches"], .bool(false))
        XCTAssertTrue(plan.fileSchemaObjectIDs.contains("type-file"))
        XCTAssertFalse(plan.fileSchemaObjectIDs.contains("file-head-a"))
        XCTAssertFalse(plan.permitsDestinationWrites)
        XCTAssertFalse(plan.activatesFileType)
    }

    func testOrderedValuesPreserveRepeatedReferencesWithinOneOwner() throws {
        let fixture = try FilePlanFixture(headIDs: ["file-head-a", "file-head-b"],
            payloadIDs: ["native-payload-a", "native-payload-b"],
            scalarHead: "file-head-a", orderedHeads: ["file-head-b", "file-head-a", "file-head-b"])
        let plan = try fixture.makePlan()
        XCTAssertEqual(plan.entries.count, 2)
        let a = try XCTUnwrap(plan.entries.first { $0.sourceHeadID == "file-head-a" })
        let b = try XCTUnwrap(plan.entries.first { $0.sourceHeadID == "file-head-b" })
        XCTAssertNotEqual(a.sourceKey, b.sourceKey)
        XCTAssertEqual(a.payloadSHA256, b.payloadSHA256,
                       "Equal bytes in different source file identities are not collapsed")
        XCTAssertEqual(a.ownerSourceKey, b.ownerSourceKey)
        XCTAssertEqual(try plan.value(snapshot: fixture.owners[0].decoded(), relationKey: "attachmentList",
            original: .array(["file-head-b", "file-head-a", "file-head-b"].map(AnyJSON.string))),
            .array([.reference(b.reference), .reference(a.reference), .reference(b.reference)]))
        XCTAssertEqual(try plan.value(snapshot: fixture.owners[0].decoded(), relationKey: "attachment",
            original: .string("file-head-a")), .array([.reference(a.reference)]))
    }

    func testRawBlockArrayIndexIsRequiredEvenWhenNativeTreeOrderIsUnchanged() throws {
        var fixture = try FilePlanFixture()
        let before = try fixture.heads[0].decoded()
        var rows = try XCTUnwrap(fixture.heads[0].snapshot["blocks"]?.array)
        let originalIndex = try XCTUnwrap(rows.firstIndex { $0["id"] == .string("file") })
        let moved = rows.remove(at: originalIndex)
        rows.append(moved)
        try fixture.heads[0].setSnapshot("blocks", .array(rows))
        let after = try fixture.heads[0].decoded()
        XCTAssertEqual(before.depthFirstIDs, after.depthFirstIDs)
        let actualIndex = try XCTUnwrap(after.blocks.firstIndex { $0.id == "file" })
        XCTAssertNotEqual(actualIndex, originalIndex)
        XCTAssertNotEqual(after.depthFirstIDs.firstIndex(of: "file"), actualIndex)
        let exactRows = try fixture.nativeReferenceRows()
        XCTAssertTrue(exactRows.contains { $0["Field"] == .string("blocks[\(actualIndex)](file).file.targetObjectId") })
        XCTAssertEqual(try fixture.makePlan(references: exactRows).entries.count, 1)
        let stale = try fixture.mapReferenceRows(exactRows, field: "blocks[\(actualIndex)](file).file.targetObjectId") {
            var row = $0
            row["Field"] = .string("blocks[\(originalIndex)](file).file.targetObjectId")
            return row
        }
        expect(.incompleteReferences) { _ = try fixture.makePlan(references: stale) }
    }

    func testMissingForeignDuplicateAndLegacyReferenceRowsAreRefused() throws {
        let fixture = try FilePlanFixture()
        let exact = try fixture.nativeReferenceRows()
        XCTAssertEqual(exact.count, 3)
        for field in ["fileInfo.fileId", "details.attachment[0]"] {
            let missing = exact.filter { $0["Field"] != .string(field) }
            expect(.incompleteReferences) { _ = try fixture.makePlan(references: missing) }
        }
        let payloadAsHead = try fixture.mapReferenceRows(exact, field: "details.attachment[0]") {
            var row = $0; row["TargetObjectID"] = .string("native-payload-a"); return row
        }
        expect(.incompleteReferences) { _ = try fixture.makePlan(references: payloadAsHead) }
        let foreignOwner = try fixture.mapReferenceRows(exact, field: "details.attachment[0]") {
            var row = $0; row["OwnerObjectID"] = .string("foreign-page"); return row
        }
        expect(.incompleteReferences) { _ = try fixture.makePlan(references: foreignOwner) }
        let legacy = try fixture.mapReferenceRows(exact, field: "details.attachment[0]") {
            var row = $0; row["LegacyFileID"] = .bool(true); return row
        }
        expect(.incompleteReferences) { _ = try fixture.makePlan(references: legacy) }
        expect(.incompleteReferences) { _ = try fixture.makePlan(references: exact + [exact[0]]) }
        var unknown = try XCTUnwrap(exact[0].object)
        unknown["Unrecognized"] = .bool(true)
        expect(.incompleteReferences) {
            _ = try fixture.makePlan(references: [.object(unknown)] + Array(exact.dropFirst()))
        }
    }

    func testSharedPayloadSharedOwnerAndUnreferencedHeadsAreRefused() throws {
        var twoOwners = try FilePlanFixture()
        var second = try FilePlanFixture.page(id: "other-page", scalarHead: "file-head-a", orderedHeads: nil)
        // This is a second real source identity in the detached fixture, not a
        // destination ID or permission to attach one file to an arbitrary owner.
        XCTAssertNotEqual(second.id, twoOwners.owners[0].id)
        try second.setDetail("name", .string("Other source page"))
        twoOwners.owners.append(second)
        expect(.ambiguousOwner("file-head-a")) { _ = try twoOwners.makePlan() }

        let sharedPayload = try FilePlanFixture(headIDs: ["file-head-a", "file-head-b"],
            payloadIDs: ["native-payload-a", "native-payload-a"],
            scalarHead: "file-head-a", orderedHeads: ["file-head-b"])
        XCTAssertEqual(sharedPayload.variants.count, 1)
        expect(.ambiguousOwner("native-payload-a")) { _ = try sharedPayload.makePlan() }

        let unused = try FilePlanFixture(headIDs: ["file-head-a", "file-head-b"],
            payloadIDs: ["native-payload-a", "native-payload-b"],
            scalarHead: "file-head-a", orderedHeads: nil)
        expect(.ambiguousOwner("file-head-b")) { _ = try unused.makePlan() }

        var duplicateVariant = try FilePlanFixture()
        duplicateVariant.variants.append(duplicateVariant.variants[0])
        expect(.invalidVariant("native-payload-a")) { _ = try duplicateVariant.makePlan() }
    }

    func testOnlyClosedGenericFileHeadAndOriginalVariantAreAdmitted() throws {
        let original = try FilePlanFixture()
        var extraDetail = original
        try extraDetail.heads[0].setDetail("customBodyMetadata", .string("must remain unsupported"))
        expect(.unsupportedHead("file-head-a", "unrepresented detail")) { _ = try extraDetail.makePlan() }

        var image = original
        try image.heads[0].setDetail("layout", .integer(8))
        expect(.unsupportedHead("file-head-a", "identity or metadata")) { _ = try image.makePlan() }

        var legacy = original
        legacy.heads[0].nativeType = 256
        expect(.unsupportedHead("file-head-a", "legacy file head")) { _ = try legacy.makePlan() }

        var fileKeys = original
        try fileKeys.heads[0].setSnapshot("fileKeys", .object(["legacy": .string("key")]))
        expect(.unsupportedHead("file-head-a", "snapshot envelope")) { _ = try fileKeys.makePlan() }

        var alteredFileBlock = original
        var blocks = try XCTUnwrap(alteredFileBlock.heads[0].snapshot["blocks"]?.array)
        let index = try XCTUnwrap(blocks.firstIndex { $0["id"] == .string("file") })
        var block = try XCTUnwrap(blocks[index].object)
        var file = try XCTUnwrap(block["file"]?.object)
        file["size"] = .integer(8192) // native int64 JSON uses a decimal string
        block["file"] = .object(file); blocks[index] = .object(block)
        try alteredFileBlock.heads[0].setSnapshot("blocks", .array(blocks))
        expect(.unsupportedHead("file-head-a", "generated block:file")) { _ = try alteredFileBlock.makePlan() }

        for path in ["/image/0/", "/original", ""] {
            var nonGeneric = original
            nonGeneric.variants = [try FilePlanFixture.variant(payloadID: "native-payload-a", path: path)]
            expect(.invalidVariant("native-payload-a")) { _ = try nonGeneric.makePlan() }
        }
        var nonOriginal = original
        nonOriginal.variants = [try FilePlanFixture.variant(payloadID: "native-payload-a", original: false)]
        expect(.invalidVariant("native-payload-a")) { _ = try nonOriginal.makePlan() }

        var tooMany = original
        tooMany.variants = Array(repeating: original.variants[0], count: 4097)
        expect(.limit) { _ = try tooMany.makePlan() }
    }

    func testExactSourceViewsCatalogAndUTF8BindingsCannotBeSubstituted() throws {
        let fixture = try FilePlanFixture(headIDs: ["file-\u{e9}"],
            payloadIDs: ["native-payload-a"], scalarHead: "file-\u{e9}", orderedHeads: nil)
        let plan = try fixture.makePlan()
        let owner = try fixture.owners[0].decoded()
        XCTAssertEqual(plan.entries.count, 1)
        expect(.changedProperty("source-page", "attachment")) {
            _ = try plan.value(snapshot: owner, relationKey: "attachment",
                original: .string("file-e\u{301}"))
        }
        var changedView = fixture.owners[0]
        try changedView.setDetail("name", .string("Changed later source bytes"))
        expect(.changedProperty("source-page", "attachment")) {
            _ = try plan.value(snapshot: changedView.decoded(), relationKey: "attachment",
                original: .string("file-\u{e9}"))
        }
        var changedCatalog = fixture
        let relation = try XCTUnwrap(changedCatalog.definitions.firstIndex { $0.id == "rel-attachment" })
        try changedCatalog.definitions[relation].setDetail("description", .string("different captured descriptor"))
        let otherCatalog = try changedCatalog.catalog()
        expect(.sourceBinding) { try plan.require(catalog: otherCatalog) }

        let exact = try fixture.nativeReferenceRows()
        let normalizedTarget = try fixture.mapReferenceRows(exact, field: "details.attachment[0]") {
            var row = $0; row["TargetObjectID"] = .string("file-e\u{301}"); return row
        }
        expect(.incompleteReferences) { _ = try fixture.makePlan(references: normalizedTarget) }
        expect(.sourceBinding) { _ = try fixture.makePlan(accountID: "foreign-account") }
    }

    func testEmptyFileProjectionHasNoFileItemsOrRetainedFileSchema() throws {
        let empty = try FilePlanFixture(headIDs: [], payloadIDs: [], scalarHead: nil, orderedHeads: nil)
        let plan = try empty.makePlan()
        XCTAssertTrue(plan.entries.isEmpty)
        XCTAssertTrue(plan.fileSchemaObjectIDs.isEmpty)
        XCTAssertTrue(try empty.nativeReferenceRows().isEmpty)
        XCTAssertFalse(plan.permitsDestinationWrites)
        XCTAssertFalse(plan.activatesFileType)
        // Full zero-file/v1 encoding is a separate composition regression.
        // This pure empty projection alone does not assert those plan bytes.
    }

    private func expect(_ expected: AnyHeartNativeCapturedFilePlanError,
                        file: StaticString = #filePath, line: UInt = #line,
                        _ operation: () throws -> Void) {
        XCTAssertThrowsError(try operation(), file: file, line: line) { error in
            XCTAssertEqual(error as? AnyHeartNativeCapturedFilePlanError, expected, file: file, line: line)
        }
    }
}

private struct FilePlanFixture {
    static let accountID = "source-account"
    static let spaceID = "source-space"
    static let capture = String(repeating: "a", count: 64)
    static let witness = String(repeating: "b", count: 64)

    struct SourceRecord {
        let id: String
        var nativeType: Int64
        let uniqueKey: String
        var snapshot: AnyJSON

        func decoded() throws -> AnyHeartNativeSnapshotView {
            // These bytes are deliberately synthetic, not parsed protobuf.
            let canonical = try FilePlanFixture.encoded(snapshot)
            let opaque = Data(("synthetic-pb:" + id + ":" + AnyContentDigest.sha256(canonical)).utf8)
            let view: AnyJSON = .object([
                "Contract": .string("pinkha-native-snapshot-json-v1"),
                "SpaceID": .string(FilePlanFixture.spaceID), "ObjectID": .string(id),
                "NativeType": .integer(nativeType), "UniqueKey": .string(uniqueKey),
                "SnapshotSHA256": .string(AnyContentDigest.sha256(opaque)),
                "SnapshotBytes": .integer(Int64(opaque.count)), "Snapshot": snapshot,
            ])
            return try .init(jsonView: FilePlanFixture.encoded(view), snapshotBytes: opaque,
                sourceSpaceID: FilePlanFixture.spaceID, sourceObjectID: id)
        }

        mutating func setSnapshot(_ field: String, _ value: AnyJSON) throws {
            var fields = try XCTUnwrap(snapshot.object)
            fields[field] = value; snapshot = .object(fields)
        }

        mutating func setDetail(_ field: String, _ value: AnyJSON) throws {
            var details = try XCTUnwrap(snapshot["details"]?.object)
            details[field] = value
            try setSnapshot("details", .object(details))
        }
    }

    var definitions: [SourceRecord]
    var owners: [SourceRecord]
    var heads: [SourceRecord]
    var variants: [AnyHeartNativeCapturedFilePlan.Variant]

    init(headIDs: [String] = ["file-head-a"], payloadIDs: [String] = ["native-payload-a"],
         scalarHead: String? = "file-head-a", orderedHeads: [String]? = nil) throws {
        guard headIDs.count == payloadIDs.count else { throw FixtureError.invalid }
        var variants: [AnyHeartNativeCapturedFilePlan.Variant] = [], seen = Set<String>()
        for payload in payloadIDs where seen.insert(payload).inserted {
            variants.append(try Self.variant(payloadID: payload))
        }
        self.variants = variants
        heads = try zip(headIDs, payloadIDs).map { headID, payloadID in
            let variant = try XCTUnwrap(variants.first { $0.fileID == payloadID })
            return try Self.head(id: headID, variant: variant)
        }
        owners = [try Self.page(id: "source-page", scalarHead: scalarHead, orderedHeads: orderedHeads)]
        definitions = try Self.definitions()
    }

    func catalog() throws -> AnyHeartNativeDefinitionCatalog {
        try .init(sourceAccountID: Self.accountID, sourceSpaceID: Self.spaceID,
            captureManifestSHA256: Self.capture, sourceWitnessSHA256: Self.witness,
            snapshots: (definitions + owners + heads).map { try $0.decoded() })
    }

    func makePlan(references: [AnyJSON]? = nil, accountID: String = Self.accountID) throws
        -> AnyHeartNativeCapturedFilePlan {
        let catalog = try self.catalog()
        let snapshots = try (definitions + owners + heads).map { try $0.decoded() }
        let bindings = try owners.map { owner -> AnyHeartNativeCapturedFilePlan.Owner in
            .init(snapshot: try owner.decoded(), sourceKey: AnyHeartNativePageComposition.objectSourceKey(
                spaceID: Self.spaceID, objectID: owner.id))
        }
        return try .init(sourceAccountID: accountID, sourceSpaceID: Self.spaceID,
            captureManifestSHA256: Self.capture, sourceWitnessSHA256: Self.witness,
            snapshots: snapshots, variants: variants,
            references: try references ?? nativeReferenceRows(), owners: bindings, catalog: catalog)
    }

    /// Independent detached fixture transcription of native_file_references.go:
    /// self FileInfo, the actual raw array index, then each detail value index.
    /// It does not call the production planner or use a depth-first index.
    func nativeReferenceRows() throws -> [AnyJSON] {
        var rows: [AnyJSON] = []
        var payloadByHead: [Data: String] = [:]
        for head in heads {
            let payload = try XCTUnwrap(head.snapshot["fileInfo"]?["fileId"]?.string)
            payloadByHead[Data(head.id.utf8)] = payload
            rows.append(Self.reference(owner: head.id, field: "fileInfo.fileId", target: head.id, payload: payload))
            let blocks = try XCTUnwrap(head.snapshot["blocks"]?.array)
            let index = try XCTUnwrap(blocks.firstIndex { $0["id"] == .string("file") })
            rows.append(Self.reference(owner: head.id, field: "blocks[\(index)](file).file.targetObjectId",
                target: head.id, payload: payload))
        }
        for owner in owners {
            for key in ["attachment", "attachmentList"] {
                guard let value = owner.snapshot["details"]?[key] else { continue }
                let values = value.string.map { [AnyJSON.string($0)] } ?? value.array ?? []
                for (index, item) in values.enumerated() {
                    let id = try XCTUnwrap(item.string)
                    let payload = try XCTUnwrap(payloadByHead[Data(id.utf8)])
                    rows.append(Self.reference(owner: owner.id, field: "details.\(key)[\(index)]", target: id, payload: payload))
                }
            }
        }
        return Self.sortedReferences(rows)
    }

    func mapReferenceRows(_ rows: [AnyJSON], field: String,
        _ body: ([String: AnyJSON]) throws -> [String: AnyJSON]) throws -> [AnyJSON] {
        var found = 0
        let result = try rows.map { value -> AnyJSON in
            guard value["Field"] == .string(field) else { return value }
            found += 1; return .object(try body(XCTUnwrap(value.object)))
        }
        XCTAssertEqual(found, 1, "Fixture mutation must reach one exact native row")
        return Self.sortedReferences(result)
    }

    static func sortedReferences(_ rows: [AnyJSON]) -> [AnyJSON] {
        rows.sorted { lhs, rhs in
            for key in ["OwnerObjectID", "Field", "FileID"] {
                let a = lhs[key]?.string ?? "", b = rhs[key]?.string ?? ""
                if !a.utf8.elementsEqual(b.utf8) { return a.utf8.lexicographicallyPrecedes(b.utf8) }
            }
            return false
        }
    }

    static func reference(owner: String, field: String, target: String, payload: String) -> AnyJSON {
        .object(["OwnerObjectID": .string(owner), "Field": .string(field),
            "TargetObjectID": .string(target), "FileID": .string(payload), "LegacyFileID": .bool(false)])
    }

    static func variant(payloadID: String, path: String = "/0/", original: Bool = true) throws
        -> AnyHeartNativeCapturedFilePlan.Variant {
        let payload = Data(repeating: 0x41, count: 8192), metadata = Data("synthetic-native-metadata".utf8)
        let variantHash = AnyContentDigest.sha256(Data((payloadID + "\0" + path).utf8))
        let payloadPath = AnyContentDigest.sha256(Data(payloadID.utf8)) + "/" + variantHash + ".payload"
        let metadataPath = "metadata-" + variantHash + ".pb"
        let payloadSHA = AnyContentDigest.sha256(payload), metadataSHA = AnyContentDigest.sha256(metadata)
        let raw: AnyJSON = .object([
            "Path": .string(path), "ContentID": .string("synthetic-content-" + payloadID),
            "MetadataID": .string("synthetic-meta-" + payloadID), "Name": .string("report.txt"),
            "MIME": .string("text/plain"), "NativeOriginalPath": .bool(original),
            "NativeChecksum": .string("SYNTHETIC-BASE32-NATIVE-CHECKSUM"), "SourceChecksum": .string(""),
            "UploadChecksumMatches": .bool(false),
            "Payload": .object(["Path": .string(payloadPath), "SHA256": .string(payloadSHA), "Bytes": .integer(8192)]),
            "Metadata": .object(["Path": .string(metadataPath), "SHA256": .string(metadataSHA), "Bytes": .integer(Int64(metadata.count))]),
        ])
        return .init(fileID: payloadID, path: path, contentID: "synthetic-content-" + payloadID,
            metadataID: "synthetic-meta-" + payloadID, name: "report.txt", mime: "text/plain", original: original,
            payloadPath: payloadPath, payloadSHA256: payloadSHA, payloadBytes: payload.count,
            metadataPath: metadataPath, metadataSHA256: metadataSHA, metadataBytes: metadata.count, raw: raw)
    }

    static func page(id: String, scalarHead: String?, orderedHeads: [String]?) throws -> SourceRecord {
        var details: [String: AnyJSON] = ["name": .string("Source page")]
        if let scalarHead { details["attachment"] = .string(scalarHead) }
        if let orderedHeads { details["attachmentList"] = .array(orderedHeads.map(AnyJSON.string)) }
        let root = block(id: id, kind: "smartblock", content: .object([:]), children: [])
        return .init(id: id, nativeType: 16, uniqueKey: "", snapshot: envelope(
            details: details, objectTypes: ["ot-page"], blocks: [root], relationLinks: [], fileInfo: .null))
    }

    static func head(id: String, variant: AnyHeartNativeCapturedFilePlan.Variant) throws -> SourceRecord {
        let details: [String: AnyJSON] = [
            "name": .string("report"), "fileExt": .string("txt"), "fileMimeType": .string("text/plain"),
            "fileId": .string(variant.fileID), "layout": .integer(6), "fileIndexingStatus": .integer(1),
            "sizeInBytes": .integer(Int64(variant.payloadBytes)), "addedDate": .integer(1_700_000_000),
            "lastModifiedDate": .integer(1_700_000_001), "isReadonly": .bool(false),
            "description": .string(""), "featuredRelations": .array([]),
            "fileVariantIds": .array([.string(variant.contentID)]),
            "fileVariantPaths": .array([.string(variant.path)]),
            "fileVariantChecksums": .array([variant.raw["NativeChecksum"]!]),
            "fileVariantMills": .array([.string("/blob")]), "fileVariantKeys": .array([.string("fixture-key")]),
            "fileVariantOptions": .array([.string("{}")]), "fileVariantWidths": .array([.integer(0)]),
            "fileSourceChecksum": variant.raw["SourceChecksum"]!,
        ]
        let rootChildren = ["header", "file", "info", "description", "fileExt", "sizeInBytes", "addedDate"]
        // This raw serialization order intentionally differs from tree order:
        // native_reference's file index is 4, while depth-first index is 4 too
        // initially; the focused permutation test makes those indices diverge.
        let blocks: [AnyJSON] = [
            block(id: id, kind: "smartblock", content: .object([:]), children: rootChildren),
            block(id: "header", kind: "layout", content: .object(["style": .integer(3)]), children: ["title", "featuredRelations"]),
            block(id: "title", kind: "text", content: text("", style: 7, marks: .null), children: [],
                fields: .object(["_detailsKey": .array([.string("name"), .string("done")])])),
            block(id: "featuredRelations", kind: "featuredRelations", content: .object([:]), children: []),
            block(id: "file", kind: "file", content: .object([
                "hash": .string(""), "name": .string("report"), "type": .integer(1), "mime": .string("text/plain"),
                "size": .string(String(variant.payloadBytes)), "addedAt": .string("1700000000"),
                "targetObjectId": .string(id), "state": .integer(2), "style": .integer(0),
            ]), children: []),
            block(id: "info", kind: "text", content: text("File Information", style: 0, marks: .object([
                "marks": .array([.object(["range": .object(["from": .integer(0), "to": .integer(16)]),
                    "type": .integer(3), "param": .string("")])]),
            ])), children: []),
            block(id: "description", kind: "relation", content: .object(["key": .string("description")]), children: []),
            block(id: "fileExt", kind: "relation", content: .object(["key": .string("fileExt")]), children: []),
            block(id: "sizeInBytes", kind: "relation", content: .object(["key": .string("sizeInBytes")]), children: []),
            block(id: "addedDate", kind: "relation", content: .object(["key": .string("addedDate")]), children: []),
        ]
        let links = details.keys.sorted().map {
            AnyJSON.object(["key": .string($0), "format": .integer(format($0))])
        }
        return .init(id: id, nativeType: 533, uniqueKey: "", snapshot: envelope(
            details: details, objectTypes: ["ot-file"], blocks: blocks, relationLinks: links,
            fileInfo: .object(["fileId": .string(variant.fileID), "encryptionKeys": .array([
                .object(["path": .string(variant.path), "key": .string("fixture-key")]),
            ])])))
    }

    static func definitions() throws -> [SourceRecord] {
        // These are synthetic captured descriptors. No registry descriptor is
        // converted into a native head, and no actual native override is claimed.
        let keys = ["name", "attachment", "attachmentList", "fileExt", "fileMimeType", "fileId",
            "layout", "fileIndexingStatus", "sizeInBytes", "addedDate", "lastModifiedDate", "isReadonly",
            "description", "featuredRelations", "fileVariantIds", "fileVariantPaths", "fileVariantChecksums",
            "fileVariantMills", "fileVariantKeys", "fileVariantOptions", "fileVariantWidths", "fileSourceChecksum"]
        var rows = keys.map { key in
            SourceRecord(id: "rel-" + key, nativeType: 521, uniqueKey: "rel-" + key, snapshot: envelope(
                details: ["name": .string(key), "description": .string(""),
                    "relationKey": .string(key), "relationFormat": .integer(format(key)),
                    "relationMaxCount": .integer(key == "attachment" ? 1 : 0),
                    "relationReadonlyValue": .bool(false), "relationDefaultValue": .null,
                    "relationFormatObjectTypes": .array([])],
                objectTypes: [], blocks: [], relationLinks: [], fileInfo: .null))
        }
        for (id, key, layout) in [("type-page", "page", Int64(0)), ("type-file", "file", Int64(6))] {
            rows.append(.init(id: id, nativeType: 528, uniqueKey: "ot-" + key, snapshot: envelope(
                details: ["name": .string(key), "description": .string(""), "recommendedLayout": .integer(layout)],
                objectTypes: [], blocks: [], relationLinks: [], fileInfo: .null)))
        }
        return rows
    }

    static func format(_ key: String) -> Int64 {
        if key == "attachment" || key == "attachmentList" { return 5 }
        if key == "isReadonly" { return 6 }
        if ["layout", "fileIndexingStatus", "sizeInBytes", "fileVariantWidths"].contains(key) { return 2 }
        if ["addedDate", "lastModifiedDate"].contains(key) { return 4 }
        if key == "featuredRelations" { return 100 }
        return 0
    }

    static func envelope(details: [String: AnyJSON], objectTypes: [String], blocks: [AnyJSON],
                         relationLinks: [AnyJSON], fileInfo: AnyJSON) -> AnyJSON {
        .object(["blocks": .array(blocks), "details": .object(details), "fileKeys": .object([:]),
            "extraRelations": .array([]), "objectTypes": .array(objectTypes.map(AnyJSON.string)),
            "collections": .object([:]), "removedCollectionKeys": .array([]),
            "relationLinks": .array(relationLinks), "key": .string(""),
            "originalCreatedTimestamp": .string("1700000000"), "fileInfo": fileInfo])
    }

    static func block(id: String, kind: String, content: AnyJSON, children: [String],
                      fields: AnyJSON = .null) -> AnyJSON {
        .object(["id": .string(id), "fields": fields,
            "restrictions": .object(["read": .bool(false), "edit": .bool(true), "remove": .bool(true),
                "drag": .bool(true), "dropOn": .bool(true)]),
            "childrenIds": .array(children.map(AnyJSON.string)), "backgroundColor": .string(""),
            "align": .integer(0), "verticalAlign": .integer(0), kind: content])
    }

    static func text(_ value: String, style: Int64, marks: AnyJSON) -> AnyJSON {
        .object(["text": .string(value), "style": .integer(style), "marks": marks, "checked": .bool(false),
            "color": .string(""), "iconEmoji": .string(""), "iconImage": .string("")])
    }

    static func encoded(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    enum FixtureError: Error { case invalid }
}
