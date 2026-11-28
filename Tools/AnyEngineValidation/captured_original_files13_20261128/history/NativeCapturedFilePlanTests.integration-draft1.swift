import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

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

    func makePlan(references: [AnyJSON]? = nil, accountID: String = FilePlanFixture.accountID) throws
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
        // Start with the generated tree order. The focused permutation test
        // moves the raw file row while retaining every native child-order edge,
        // making the captured array index differ from the depth-first index.
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

/// Synthetic full-bundle integration controls plus one mandatory exact original
/// zero-file regression. Synthetic receipt flags describe fixture wire shape,
/// not a native session, capture, upload, or signed destination completion.
final class NativeCapturedFileIntegrationTests: XCTestCase {
    func testFullBundleCreatesOwnerThenFileThenPropertyAndRetainsEveryFileHead() throws {
        let f = try CapturedFileBundleFixture(raw: FilePlanFixture.currentDocument())
        XCTAssertTrue(f.bundle.issues.isEmpty)
        XCTAssertNotNil(f.bundle.nativeStoreContext?.headCensus)
        let preservation = try AnyHeartNativeSourcePreservation(capturedBundle: f.bundle, archive: f.archive)
        let content = preservation.currentContent
        let files = try XCTUnwrap(content.capturedFiles)
        let entry = try XCTUnwrap(files.entries.first)
        XCTAssertEqual(files.entries.count, 1)
        XCTAssertEqual(preservation.retainedFileHeadIDs, ["file-head-a"])
        XCTAssertTrue(preservation.retainedFileSchemaIDs.contains("type-file"))
        XCTAssertFalse(preservation.retainedFileSchemaIDs.contains("rel-name"),
                       "The same captured name descriptor remains active for the Page")
        XCTAssertFalse(preservation.uninstantiatedDefinitionIDs.contains("type-file"))
        XCTAssertEqual(preservation.records.first { $0.sourceHeadID == "file-head-a" }?.role,
                       "retained-file-attachment-head")
        XCTAssertEqual(preservation.records.first { $0.sourceHeadID == "type-file" }?.role,
                       "retained-file-schema-type-definition")
        XCTAssertEqual(preservation.records.first { $0.sourceHeadID == "rel-name" }?.role,
                       "active-schema-relation-definition")
        let plan = try f.plan(preservation)
        try plan.requireExecutable() // inert contract validation; never execute
        let ownerIndex = try XCTUnwrap(plan.items.firstIndex { $0.sourceKey == entry.ownerSourceKey })
        let fileIndex = try XCTUnwrap(plan.items.firstIndex { $0.sourceKey == entry.sourceKey })
        let updateIndex = try XCTUnwrap(plan.items.firstIndex {
            guard case .propertyUpdate = $0.operation else { return false }
            return $0.sourceObjectID == entry.sourceOwnerID
        })
        XCTAssertLessThan(ownerIndex, fileIndex)
        XCTAssertLessThan(fileIndex, updateIndex)
        XCTAssertEqual(plan.items[fileIndex], entry.item)
        XCTAssertFalse(plan.items.contains {
            guard case .object = $0.operation else { return false }
            return $0.sourceObjectID == entry.sourceHeadID
        })
        XCTAssertEqual(Set(preservation.records.map(\.sourceHeadID)),
                       Set(try XCTUnwrap(f.bundle.nativeStoreContext?.headCensus).sourceHeadIDs))
        XCTAssertEqual(preservation.coverage.count, preservation.records.count)
        XCTAssertFalse(preservation.allImportedTypesUsable)
        XCTAssertFalse(preservation.permitsWholeSourceAdmission)
    }

    func testTypedValuesPreserveOrderAndOriginalSchemaRefusals() throws {
        let raw = try FilePlanFixture.currentDocument(sizes: [8192, 8192])
        let f = try CapturedFileBundleFixture(raw: raw)
        let content = try AnyHeartNativeContentComposition(bundle: f.bundle)
        let files = try XCTUnwrap(content.capturedFiles)
        let page = try XCTUnwrap(content.pages.first)
        let a = try XCTUnwrap(files.entries.first { $0.sourceHeadID == "file-head-a" })
        let b = try XCTUnwrap(files.entries.first { $0.sourceHeadID == "file-head-b" })
        let list = try XCTUnwrap(content.definitions.property(sourceKey: "attachmentList"))
        let scalar = try XCTUnwrap(content.definitions.property(sourceKey: "attachment"))
        let fields = page.values.deferredGroups.flatMap { group -> [AnyDestinationField] in
            guard case .object(let fields) = group.fields else { return [] }
            return fields
        }
        XCTAssertEqual(fields.first { $0.key == scalar.record }?.value, .array([.reference(a.reference)]))
        XCTAssertEqual(fields.first { $0.key == list.record }?.value,
                       .array([.reference(b.reference), .reference(a.reference), .reference(b.reference)]))
        let snapshot = try XCTUnwrap(f.bundle.objects.first { $0.sourceObjectID == "source-page" })
        let owners = content.selection.objects.map {
            AnyHeartNativeDefinitionPlan.ObjectBinding(sourceObjectID: $0.sourceObjectID,
                destinationSourceKey: AnyHeartNativePageComposition.objectSourceKey(
                    spaceID: f.bundle.sourceSpaceID, objectID: $0.sourceObjectID))
        }
        XCTAssertThrowsError(try content.definitions.values(snapshot: snapshot,
            relationKeys: ["attachment"], objects: owners)) {
            XCTAssertEqual($0 as? AnyHeartNativeDefinitionPlanError,
                           .invalidValue("attachment", "bounded file array required"))
        }
        for (field, value, reason) in [
            ("relationMaxCount", AnyJSON.integer(2),
             "relationMaxCount:exact-positive-cardinality-not-represented-by-multiple-flag"),
            ("relationFormatObjectTypes", AnyJSON.array([.string("type-file")]),
             "relationFormatObjectTypes:native-file-type-restriction-not-qualified"),
            ("relationDefaultValue", AnyJSON.string("unqualified-default"),
             "relationDefaultValue:default-retained; destination-new-object-default-behavior-not-qualified")
        ] {
            var changed = raw
            let i = try XCTUnwrap(changed.definitions.firstIndex { $0.id == "rel-attachment" })
            try changed.definitions[i].setDetail(field, value)
            let rejected = try CapturedFileBundleFixture(raw: changed)
            XCTAssertThrowsError(try AnyHeartNativeSourcePreservation(
                capturedBundle: rejected.bundle, archive: rejected.archive)) {
                XCTAssertEqual($0 as? AnyHeartNativeDefinitionPlanError, .unsupported("rel-attachment", reason))
            }
        }
    }

    func testArchiveColdReconstructionKeepsPayloadAndRefusesMissingReference() throws {
        let raw = try FilePlanFixture.currentDocument()
        let f = try CapturedFileBundleFixture(raw: raw)
        let first = try AnyHeartNativeSourcePreservation(capturedBundle: f.bundle, archive: f.archive)
        let originalPlan = try f.plan(first)
        let restored = try AnyHeartNativePreservationArchive.restore(f.archive.bytes, expected: f.archive.binding)
        XCTAssertNil(restored.recoveredDefinitions)
        XCTAssertEqual(restored.bundle.manifestBytes, f.bundle.manifestBytes)
        let rebuiltArchive = try AnyHeartNativePreservationArchive(capturedBundle: restored.bundle,
            memberData: restored.capturedMemberData)
        XCTAssertEqual(rebuiltArchive.bytes, f.archive.bytes)
        let cold = try AnyHeartNativeSourcePreservation(capturedBundle: restored.bundle, archive: rebuiltArchive)
        XCTAssertEqual(try f.plan(cold).canonicalBytes, originalPlan.canonicalBytes)
        XCTAssertEqual(cold.currentContent.capturedFiles?.contentSHA256,
                       first.currentContent.capturedFiles?.contentSHA256)
        for member in f.bundle.verifiedMembers {
            XCTAssertEqual(try restored.capturedMemberData(member), f.members[member.path])
        }
        var refs = try raw.nativeReferenceRows()
        refs.removeAll { $0["Field"] == .string("fileInfo.fileId") }
        let incomplete = try CapturedFileBundleFixture(raw: raw, references: refs)
        XCTAssertTrue(incomplete.bundle.issues.isEmpty,
                      "Byte-complete bundle parsing is deliberately weaker than attachment semantics")
        XCTAssertThrowsError(try AnyHeartNativeSourcePreservation(
            capturedBundle: incomplete.bundle, archive: incomplete.archive)) {
            XCTAssertEqual($0 as? AnyHeartNativeCapturedFilePlanError, .incompleteReferences)
        }
        // This is cold evidence reconstruction only: no checkpoint mappings,
        // current lease, source session or native Completion is manufactured.
    }

    func testRetainedZeroFileV1PlanIsUnchangedByTheNewAttachmentHooks() throws {
        let f = try retained()
        XCTAssertTrue(f.restored.bundle.fileVariants.isEmpty)
        XCTAssertTrue(f.restored.bundle.fileReferences.isEmpty)
        let archive = try AnyHeartNativePreservationArchive(bundle: f.restored.bundle, recovered: f.recovered,
            memberData: f.restored.capturedMemberData, recoveredMemberData: f.restored.recoveredMemberData)
        XCTAssertEqual(archive.bytes, f.archiveBytes)
        let preservation = try AnyHeartNativeSourcePreservation(bundle: f.restored.bundle,
            recoveredDefinitions: f.recovered, archive: archive)
        XCTAssertNil(preservation.currentContent.capturedFiles)
        XCTAssertTrue(preservation.retainedFileHeadIDs.isEmpty)
        XCTAssertTrue(preservation.retainedFileSchemaIDs.isEmpty)
        let plan = try preservation.preservationPlan(workspace: f.plan.binding.workspace,
            storeID: f.plan.binding.storeID, planID: f.plan.binding.planID)
        XCTAssertEqual(plan.canonicalBytes, f.planBytes)
        XCTAssertEqual(plan.items.count, 182)
        try requireRetainedInputsUnchanged(f)
    }

    func testPrivatePayloadDispatchUsesExactMembersAndPreservesInlineFullBoundary() throws {
        let raw = try FilePlanFixture.currentDocument(sizes: [4095, 4096])
        let f = try CapturedFileBundleFixture(raw: raw)
        let preservation = try AnyHeartNativeSourcePreservation(capturedBundle: f.bundle, archive: f.archive)
        let plan = try f.plan(preservation)
        let files = try XCTUnwrap(preservation.currentContent.capturedFiles)
        XCTAssertEqual(files.entries.map { $0.item.operation.kind }, ["inlineFile", "file"])
        let fm = FileManager.default
        let base = fm.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("pinkha-captured-file-hooks-" + UUID().uuidString, isDirectory: true)
        try fm.createDirectory(at: base, withIntermediateDirectories: false,
                               attributes: [.posixPermissions: 0o700])
        defer { try? fm.removeItem(at: base) }
        let captureParent = base.appendingPathComponent("capture", isDirectory: true)
        let capture = captureParent.appendingPathComponent("native-source-fixture", isDirectory: true)
        let journal = base.appendingPathComponent("journal", isDirectory: true)
        let payload = base.appendingPathComponent("payload", isDirectory: true)
        for path in [captureParent, capture, journal, payload] {
            try fm.createDirectory(at: path, withIntermediateDirectories: false,
                                   attributes: [.posixPermissions: 0o700])
        }
        let captureFiles = f.members.merging(["manifest.json": f.bundle.manifestBytes]) { _, _ in
            preconditionFailure("Fixture manifest must not be a declared capture member")
        }
        for (name, bytes) in captureFiles {
            let path = capture.appendingPathComponent(name, isDirectory: false)
            let parent = path.deletingLastPathComponent()
            if parent != capture {
                try fm.createDirectory(at: parent, withIntermediateDirectories: true,
                                       attributes: [.posixPermissions: 0o700])
            }
            try bytes.write(to: path, options: [.withoutOverwriting])
            try fm.setAttributes([.posixPermissions: 0o400], ofItemAtPath: path.path)
        }
        let descriptorBytes = try FilePlanFixture.encoded(.object([
            "contract": .string(AnyHeartNativeCaptureDescriptor.contract), "requestID": .string("fixture"),
            "sourceAccountID": .string(f.bundle.sourceAccountID), "sourceSpaceID": .string(f.bundle.sourceSpaceID),
            "privateBundleDirectory": .string(capture.path), "manifestSHA256": .string(f.bundle.manifestSHA256),
            "sourceRowsSHA256": .string(f.bundle.sourceWitnessSHA256),
            "nativeTrees": .integer(Int64(f.bundle.trees.count)), "capturedObjects": .integer(Int64(f.bundle.objects.count)),
            "capturedFiles": .integer(2), "accountSessionAuthorizedAtCapture": .bool(true),
            "capturedSnapshotsBoundToCheckpoint": .bool(true), "currentFilePayloadCompleteness": .bool(true),
            "originalNativeHistoryRowsRetained": .bool(true), "permitsDestinationWrites": .bool(false)
        ]))
        let descriptor = try AnyHeartNativeCaptureDescriptor(data: descriptorBytes,
            expectedAccountID: f.bundle.sourceAccountID, expectedSpaceID: f.bundle.sourceSpaceID,
            expectedRequestID: "fixture")
        let captured = try descriptor.loadPreservationSource(under: captureParent)
        do {
            let storage = try AnyHeartMigrationPrivateStorage(captureParent: captureParent,
                captureDirectory: capture.path, journalParent: journal, payloadParent: payload, planBinding: plan.binding)
            let first = try storage.materializeCapturedFiles(files, captured: captured)
            XCTAssertEqual(Set(first.keys), Set(files.entries.map { Data($0.sourceKey.utf8) }))
            var identity: [Data: (UInt64, UInt64)] = [:]
            for entry in files.entries {
                let url = try XCTUnwrap(first[Data(entry.sourceKey.utf8)])
                var info = stat()
                XCTAssertEqual(lstat(url.path, &info), 0)
                XCTAssertEqual(info.st_mode & mode_t(0o7777), mode_t(0o400))
                XCTAssertEqual(info.st_nlink, 1)
                identity[Data(entry.sourceKey.utf8)] = (UInt64(info.st_dev), UInt64(info.st_ino))
                XCTAssertEqual(try Data(contentsOf: url), f.members[entry.payloadPath])
                XCTAssertNotEqual(url.path, capture.appendingPathComponent(entry.payloadPath).path)
            }
            let second = try storage.materializeCapturedFiles(files, captured: captured)
            XCTAssertEqual(first, second)
            for (key, url) in second {
                var info = stat()
                XCTAssertEqual(lstat(url.path, &info), 0)
                XCTAssertEqual(UInt64(info.st_dev), identity[key]?.0)
                XCTAssertEqual(UInt64(info.st_ino), identity[key]?.1)
            }
            var changed = raw
            try changed.owners[0].setDetail("name", .string("A different captured owner view"))
            let other = try CapturedFileBundleFixture(raw: changed)
            let otherPlan = try XCTUnwrap(AnyHeartNativeContentComposition(bundle: other.bundle).capturedFiles)
            let namesBefore = try fm.contentsOfDirectory(atPath: payload.path).sorted()
            XCTAssertThrowsError(try storage.materializeCapturedFiles(otherPlan, captured: captured)) {
                XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .privateStorage)
            }
            XCTAssertEqual(try fm.contentsOfDirectory(atPath: payload.path).sorted(), namesBefore)
            try storage.validate()
        }
        for (name, bytes) in captureFiles {
            XCTAssertEqual(try Data(contentsOf: capture.appendingPathComponent(name)), bytes)
        }
        // These are local synthetic private-storage effects. No actual
        // prepared-file request, native owner or cloud durability is asserted.
    }

    private struct Retained {
        let archiveBytes: Data
        let planBytes: Data
        let plan: AnyDestinationMigrationPlan
        let restored: AnyHeartNativePreservationArchive.Restored
        let recovered: AnyHeartNativeRecoveredDefinitions
    }

    private func retained() throws -> Retained {
        let archiveBytes = try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_ARCHIVE", bytes: 1_634_696,
            sha256: "5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463")
        let planBytes = try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_PLAN", bytes: 1_823_803,
            sha256: "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930")
        let plan = try AnyDestinationMigrationPlan.decode(planBytes)
        XCTAssertEqual(plan.items.count, 182)
        let files = plan.items.compactMap { item -> (Int64, String)? in
            guard case .file(_, _, let mime, let size, let sha) = item.operation,
                  mime == AnyHeartNativePreservationArchive.mimeType else { return nil }
            return (size, sha)
        }
        XCTAssertEqual(files.count, 1)
        let expectedFile = try XCTUnwrap(files.first)
        XCTAssertEqual(expectedFile.0, Int64(archiveBytes.count))
        XCTAssertEqual(expectedFile.1, AnyContentDigest.sha256(archiveBytes))
        // Actual catalog values are .object expressions with a mapped URI.
        // Select the unique type declaration's literal contract/source metadata.
        let metadataRows = plan.items.compactMap { item -> [String: AnyJSON]? in
            guard case .typeDefinition(let draft) = item.operation,
                  case .literal(let value) = draft.meta, let fields = value.object,
                  fields["preservationContract"] == .string(AnyHeartNativeSourcePreservation.contract),
                  fields["sourceCaptureManifestSHA256"] == .string(plan.source.captureManifestSHA256)
            else { return nil }
            return fields
        }
        XCTAssertEqual(metadataRows.count, 1)
        let metadata = try XCTUnwrap(metadataRows.first)
        let recovery = try XCTUnwrap(metadata["sourceRecoveryManifestSHA256"]?.string)
        let binding = try AnyHeartNativePreservationArchive.Binding(
            expectedAccountID: plan.source.accountID, expectedSpaceID: plan.source.spaceID,
            captureManifestSHA256: plan.source.captureManifestSHA256,
            sourceWitnessSHA256: plan.source.witnessSHA256, recoveredManifestSHA256: recovery)
        let restored = try AnyHeartNativePreservationArchive.restore(archiveBytes, expected: binding)
        return .init(archiveBytes: archiveBytes, planBytes: planBytes, plan: plan, restored: restored,
                     recovered: try XCTUnwrap(restored.recoveredDefinitions))
    }

    private func requireRetainedInputsUnchanged(_ value: Retained) throws {
        XCTAssertEqual(try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_ARCHIVE", bytes: 1_634_696,
            sha256: "5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463"), value.archiveBytes)
        XCTAssertEqual(try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_PLAN", bytes: 1_823_803,
            sha256: "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930"), value.planBytes)
    }

    /// Reads only a later controller's two exact private fixture inputs. No
    /// original loose-member tree, journal, account or network is consulted.
    private func fixedInput(_ variable: String, bytes expectedBytes: Int, sha256: String) throws -> Data {
        guard let path = ProcessInfo.processInfo.environment[variable] else {
            throw XCTSkip("Required retained original input is not supplied; selected admission must reject a skip.")
        }
        let fd = open(path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        guard fd >= 0 else { throw AnyHeartNativePreservationError.binding }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        var before = stat(), after = stat(), named = stat()
        guard fstat(fd, &before) == 0,
              before.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG),
              before.st_nlink == 1, before.st_size == Int64(expectedBytes),
              expectedBytes <= AnyHeartNativePreservationArchive.maximumBytes else {
            throw AnyHeartNativePreservationError.binding
        }
        var data = Data()
        while data.count <= expectedBytes {
            let part = try handle.read(upToCount: min(65_536, expectedBytes + 1 - data.count)) ?? Data()
            if part.isEmpty { break }; data.append(part)
        }
        guard data.count == expectedBytes, AnyContentDigest.sha256(data) == sha256,
              fstat(fd, &after) == 0, lstat(path, &named) == 0,
              sameFile(before, after), sameFile(before, named) else {
            throw AnyHeartNativePreservationError.binding
        }
        try handle.close()
        return data
    }

    private func sameFile(_ a: stat, _ b: stat) -> Bool {
        guard a.st_dev == b.st_dev, a.st_ino == b.st_ino, a.st_mode == b.st_mode,
              a.st_uid == b.st_uid, a.st_gid == b.st_gid, a.st_nlink == b.st_nlink,
              a.st_size == b.st_size else { return false }
        #if canImport(Darwin)
        return a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
            a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
        #else
        return a.st_mtim.tv_sec == b.st_mtim.tv_sec && a.st_mtim.tv_nsec == b.st_mtim.tv_nsec &&
            a.st_ctim.tv_sec == b.st_ctim.tv_sec && a.st_ctim.tv_nsec == b.st_ctim.tv_nsec
        #endif
    }

}

/// A complete, explicitly synthetic native bundle shape. No source authority
/// is claimed by its receipt booleans or its opaque protobuf/witness values.
private struct CapturedFileBundleFixture {
    let bundle: AnyHeartNativeSpaceBundle
    let members: [String: Data]
    let archive: AnyHeartNativePreservationArchive

    init(raw: FilePlanFixture, references supplied: [AnyJSON]? = nil) throws {
        let records = raw.definitions + raw.owners + raw.heads
        let snapshots = try records.map { try $0.decoded() }
        let acl = "fixture-native-acl"
        let headIDs = (records.map(\.id) + [acl]).sorted { $0.utf8.lexicographicallyPrecedes($1.utf8) }
        let nonce = Data(repeating: 0x52, count: 32)
        func u64(_ value: UInt64) -> Data {
            Data(stride(from: 56, through: 0, by: -8).map { UInt8((value >> UInt64($0)) & 255) })
        }
        func field(_ data: Data) -> Data { u64(UInt64(data.count)) + data }
        func number(_ value: Int) -> Data { field(u64(UInt64(value))) }
        let collections: [(String, [(Data, Data)])] = [
            ("fixture-native-acl", [(Data([3]) + Data("fixture-row".utf8) + Data([0]), Data([7, 0]))]),
            ("heads", headIDs.map { (Data([3]) + Data($0.utf8) + Data([0]), Data([7, 0])) })
        ]
        var witness = field(Data("pinkha-localstore-witness-v1".utf8)) +
            field(Data("anyenc-v1.0.3-decoded-value-roundtrip-v1".utf8)) +
            field(Data("heart-owned-local-store-v1".utf8)) + field(nonce) +
            field(Data(FilePlanFixture.spaceID.utf8)) + number(1) + number(collections.count)
        var coverage: [AnyJSON] = [], rowCount = 0, valueBytes = 0
        for (name, rows) in collections {
            witness.append(field(Data(name.utf8))); witness.append(number(rows.count))
            var count = 0
            for (key, value) in rows {
                witness.append(field(key)); witness.append(field(value)); count += value.count
            }
            coverage.append(.object(["NameSHA256": .string(AnyContentDigest.sha256(Data(name.utf8))),
                "Rows": .integer(Int64(rows.count)), "EncodedValueBytes": .integer(Int64(count)),
                "UnresolvedCollection": .bool(false)]))
            rowCount += rows.count; valueBytes += count
        }
        var members: [String: Data] = ["native-source-rows.witness": witness]
        func member(_ path: String, _ bytes: Data) -> AnyJSON {
            .object(["Path": .string(path), "SHA256": .string(AnyContentDigest.sha256(bytes)),
                     "Bytes": .integer(Int64(bytes.count))])
        }
        var objects: [AnyJSON] = [], trees: [AnyJSON] = [], objectReceipts: [AnyJSON] = []
        var snapshotBytes = 0
        for snapshot in snapshots {
            let digest = AnyContentDigest.sha256(Data(snapshot.sourceObjectID.utf8))
            let stem = "snapshot-" + digest
            members[stem + ".pb"] = snapshot.protobufBytes
            members[stem + ".json"] = snapshot.jsonViewBytes
            objects.append(.object(["ObjectID": .string(snapshot.sourceObjectID), "NativeType": .integer(snapshot.nativeType),
                "UniqueKey": .string(snapshot.uniqueKey), "Snapshot": member(stem + ".pb", snapshot.protobufBytes),
                "NativeJSONView": member(stem + ".json", snapshot.jsonViewBytes)]))
            trees.append(.object(["ObjectID": .string(snapshot.sourceObjectID), "NativeType": .integer(snapshot.nativeType),
                                  "Status": .string("captured-current-snapshot")]))
            objectReceipts.append(.object(["ObjectSHA256": .string(digest),
                "Version": .string("native-raw-object-snapshot-v1"), "SmartBlockType": .integer(snapshot.nativeType),
                "SnapshotSHA256": .string(snapshot.snapshotSHA256), "SnapshotBytes": .integer(Int64(snapshot.protobufBytes.count)),
                "NativeIdentityBoundUnderTreeLock": .bool(true)]))
            snapshotBytes += snapshot.protobufBytes.count
        }
        var files: [AnyJSON] = [], payloadBytes = 0, metadataBytes = 0
        for variant in raw.variants {
            let payload = Data(repeating: 0x41, count: variant.payloadBytes)
            let metadata = Data("synthetic-native-metadata".utf8)
            guard AnyContentDigest.sha256(payload) == variant.payloadSHA256,
                  AnyContentDigest.sha256(metadata) == variant.metadataSHA256 else {
                throw FilePlanFixture.FixtureError.invalid
            }
            members[variant.payloadPath] = payload; members[variant.metadataPath] = metadata
            payloadBytes += payload.count; metadataBytes += metadata.count
            files.append(.object(["FileID": .string(variant.fileID), "Variants": .array([variant.raw])]))
        }
        let references = try supplied ?? raw.nativeReferenceRows()
        let witnessSHA = AnyContentDigest.sha256(witness)
        let accountSHA = AnyContentDigest.sha256(Data(FilePlanFixture.accountID.utf8))
        let spaceSHA = AnyContentDigest.sha256(Data(FilePlanFixture.spaceID.utf8))
        let aclHeadSHA = AnyContentDigest.sha256(Data("synthetic-acl-head".utf8))
        let native: AnyJSON = .object([
            "Version": .string("native-localstore-witness-v1"),
            "Encoding": .string("anyenc-v1.0.3-decoded-value-roundtrip-v1"),
            "Authority": .string("heart-owned-local-store-v1"), "OwnerSHA256": .string(AnyContentDigest.sha256(nonce)),
            "SpaceSHA256": .string(spaceSHA), "WitnessSHA256": .string(witnessSHA), "Generation": .integer(1),
            "Collections": .integer(Int64(collections.count)), "CollectionCoverage": .array(coverage),
            "Rows": .integer(Int64(rowCount)), "EncodedValueBytes": .integer(Int64(valueBytes)),
            "LocalDecodedRowsComplete": .bool(true)
        ])
        let inventory: AnyJSON = .object([
            "Version": .string("native-tree-identity-inventory-v2"), "SpaceSHA256": .string(spaceSHA),
            "SourceWitnessSHA256": .string(witnessSHA), "ACLHeadSHA256": .string(aclHeadSHA),
            "Generation": .integer(1), "Trees": .integer(Int64(trees.count)), "AllHeadRowsAccounted": .bool(true),
            "OtherCollections": .integer(0), "OtherCollectionRows": .integer(0),
            "KeyValueStores": .integer(0), "KeyValueRows": .integer(0)
        ])
        let source: AnyJSON = .object([
            "version": .string("loaded-account-native-witness-v1"),
            "accountAuthority": .string("held-application-account-directory-lease-v1"),
            "sessionAuthority": .string("validated-native-full-unassociated-session-v1"),
            "accountSHA256": .string(accountSHA),
            "accountDirectorySHA256": .string(AnyContentDigest.sha256(Data("synthetic-private-directory".utf8))),
            "accountSessionAuthorizedAtCapture": .bool(true), "nativeIdentityCensusRequired": .bool(true),
            "source": .object(["version": .string("loaded-native-acl-witness-v1"),
                "accountSHA256": .string(accountSHA), "spaceSHA256": .string(spaceSHA),
                "alreadyLoaded": .bool(true), "aclReadAuthorizedAtCapture": .bool(true),
                "aclIdSHA256": .string(AnyContentDigest.sha256(Data(acl.utf8))),
                "aclHeadSHA256": .string(aclHeadSHA), "native": native])
        ])
        let receipt: AnyJSON = .object([
            "Version": .string("loaded-account-native-space-source-v1"), "Source": source, "Inventory": inventory,
            "AccountSessionAuthorizedAtFinalCapture": .bool(true), "AllNativeHeadRowsAccounted": .bool(true),
            "CapturedSnapshotsBoundToUnchangedCheckpoint": .bool(true), "OriginalNativeHistoryRowsRetained": .bool(true),
            "IndexResolverSnapshotBound": .bool(true), "Objects": .array(objectReceipts),
            "NativeTrees": .integer(Int64(trees.count)), "CapturedObjects": .integer(Int64(objects.count)),
            "CapturedFiles": .integer(Int64(files.count)), "FileReferences": .integer(Int64(references.count)),
            "UnresolvedEntries": .integer(0), "ClosedResolverUnmapped": .integer(0),
            "SnapshotBytes": .integer(Int64(snapshotBytes)), "MetadataBytes": .integer(Int64(metadataBytes)),
            "PlaintextBytes": .integer(Int64(payloadBytes)), "Tombstones": .integer(0), "SettingsTrees": .integer(0),
            "UnsupportedTrees": .integer(0), "AllCurrentObjectsCaptured": .bool(true),
            "CurrentFilePayloadCompleteness": .bool(true), "PermitsDestinationWrites": .bool(false)
        ])
        let manifest = try FilePlanFixture.encoded(.object([
            "Contract": .string("pinkha-native-whole-source-bundle-v1"), "Receipt": receipt,
            "SourceRows": member("native-source-rows.witness", witness),
            "Trees": .array(trees), "Objects": .array(objects), "Files": .array(files),
            "FileReferences": .array(references), "Gaps": .array([]), "ResolverUnmapped": .array([]),
            "BundledDefinitionsUsed": .array([]), "BundledDefinitions": .array([]), "RetainedOtherCollections": .array([])
        ]))
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: FilePlanFixture.accountID, sourceSpaceID: FilePlanFixture.spaceID) {
                try XCTUnwrap(members[$0.path])
            }
        self.bundle = bundle; self.members = members
        archive = try AnyHeartNativePreservationArchive(capturedBundle: bundle) {
            try XCTUnwrap(members[$0.path])
        }
    }

    func plan(_ preservation: AnyHeartNativeSourcePreservation) throws -> AnyDestinationMigrationPlan {
        try preservation.preservationPlan(workspace: .init(accountID: "destination-account", spaceID: "destination-space"),
            storeID: "synthetic-store", planID: String(repeating: "7", count: 64))
    }
}

private extension FilePlanFixture {
    static func currentDocument(sizes: [Int] = [8192]) throws -> Self {
        guard sizes.count == 1 || sizes.count == 2, sizes.allSatisfy({ $0 > 0 && $0 <= 8192 }) else {
            throw FixtureError.invalid
        }
        let heads = sizes.count == 1 ? ["file-head-a"] : ["file-head-a", "file-head-b"]
        let payloads = sizes.count == 1 ? ["native-payload-a"] : ["native-payload-a", "native-payload-b"]
        var raw = try Self(headIDs: heads, payloadIDs: payloads, scalarHead: "file-head-a",
                           orderedHeads: sizes.count == 1 ? nil : ["file-head-b", "file-head-a", "file-head-b"])
        raw.variants = try zip(payloads, sizes).map { try variant(payloadID: $0.0, byteCount: $0.1) }
        raw.heads = try zip(heads, raw.variants).map { try head(id: $0.0, variant: $0.1) }
        for (key, format, name, description) in [
            ("name", Int64(1), "Name", "Name of the object"), ("description", Int64(0), "Description", "")
        ] {
            let index = try XCTUnwrap(raw.definitions.firstIndex { $0.id == "rel-" + key })
            for (field, value) in [("name", AnyJSON.string(name)), ("description", .string(description)),
                                   ("relationFormat", .integer(format)), ("relationMaxCount", .integer(1)),
                                   ("relationFormatIncludeTime", .bool(false))] {
                try raw.definitions[index].setDetail(field, value)
            }
        }
        // The shared name descriptor is now the actual canonical shorttext
        // shape, so its captured file-head relation link must match that format.
        for index in raw.heads.indices {
            let links = try XCTUnwrap(raw.heads[index].snapshot["relationLinks"]?.array).map { value -> AnyJSON in
                guard value["key"] == .string("name") else { return value }
                return .object(["key": .string("name"), "format": .integer(1)])
            }
            try raw.heads[index].setSnapshot("relationLinks", .array(links))
        }
        func block(_ id: String, kind: String, content: AnyJSON, children: [String],
                   restrictions: [String: Bool], fields: AnyJSON = .null) throws -> AnyJSON {
            var row = try XCTUnwrap(Self.block(id: id, kind: kind, content: content,
                                              children: children, fields: fields).object)
            row["restrictions"] = .object(restrictions.mapValues(AnyJSON.bool))
            return .object(row)
        }
        let rootRestrictions = ["read": false, "edit": false, "remove": false, "drag": false, "dropOn": false]
        let headerRestrictions = ["read": false, "edit": true, "remove": true, "drag": true, "dropOn": true]
        let boundRestrictions = ["read": false, "edit": false, "remove": true, "drag": true, "dropOn": true]
        let blocks = try [
            block("source-page", kind: "smartblock", content: .object([:]), children: ["header"],
                  restrictions: rootRestrictions),
            block("header", kind: "layout", content: .object(["style": .integer(3)]), children: ["title", "featuredRelations"],
                  restrictions: headerRestrictions),
            block("title", kind: "text", content: text("", style: 7, marks: .null), children: [],
                  restrictions: boundRestrictions, fields: .object(["_detailsKey": .array([.string("name"), .string("done")])])),
            block("featuredRelations", kind: "featuredRelations", content: .object([:]), children: [],
                  restrictions: boundRestrictions)
        ]
        try raw.owners[0].setSnapshot("blocks", .array(blocks))
        try raw.owners[0].setSnapshot("originalCreatedTimestamp", .string("0"))
        return raw
    }

    static func variant(payloadID: String, byteCount: Int) throws -> AnyHeartNativeCapturedFilePlan.Variant {
        let original = try variant(payloadID: payloadID)
        let payload = Data(repeating: 0x41, count: byteCount), digest = AnyContentDigest.sha256(payload)
        var fields = try XCTUnwrap(original.raw.object)
        fields["Payload"] = .object(["Path": .string(original.payloadPath),
            "SHA256": .string(digest), "Bytes": .integer(Int64(byteCount))])
        return .init(fileID: original.fileID, path: original.path, contentID: original.contentID,
            metadataID: original.metadataID, name: original.name, mime: original.mime, original: original.original,
            payloadPath: original.payloadPath, payloadSHA256: digest, payloadBytes: byteCount,
            metadataPath: original.metadataPath, metadataSHA256: original.metadataSHA256,
            metadataBytes: original.metadataBytes, raw: .object(fields))
    }
}
