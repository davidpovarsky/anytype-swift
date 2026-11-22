import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

final class HeartSpaceArchiveInspectionTests: XCTestCase {
    private typealias Entry = AnyHeartSpaceArchive.Entry

    private func entry(_ path: String, _ value: AnyJSON) throws -> Entry {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return Entry(path: path, bytes: try encoder.encode(value))
    }

    private func index(_ extra: [String: AnyJSON] = [:]) throws -> Entry {
        var object: [String: AnyJSON] = ["formatVersion": .string("2.0")]
        object.merge(extra) { _, new in new }
        return try entry("index.json", .object(object))
    }

    private func page(_ id: String = "page-source", path: String = "objects/page.anyblock.json",
                      extra: [String: AnyJSON] = [:]) throws -> Entry {
        var object: [String: AnyJSON] = ["formatVersion": .string("2.0"), "id": .string(id)]
        object.merge(extra) { _, new in new }
        return try entry(path, .object(object))
    }

    private func block(_ id: String, indent: Int64 = 0, extra: [String: AnyJSON] = [:]) -> AnyJSON {
        var object: [String: AnyJSON] = [
            "id": .string(id), "type": .string("paragraph"), "indent": .integer(indent), "text": .string("text")
        ]
        object.merge(extra) { _, new in new }
        return .object(object)
    }

    private func inspect(_ entries: [Entry], space: String = "source-space") throws -> AnyHeartSpaceArchive {
        try AnyHeartSpaceArchive(sourceSpaceID: space, entries: entries)
    }

    func testRetainsOriginalBytesUnknownFieldsAndExactLargeIntegerWithoutAdmittingWrites() throws {
        let integer: Int64 = 9_007_199_254_740_993
        let original = try page(extra: [
            "future": .object(["integer": .integer(integer), "opaque": .string("אבג")]),
            "blocks": .array([block("first")])
        ])
        let archive = try inspect([try index(), original])
        XCTAssertEqual(archive.originalEntries.first(where: { $0.path == original.path })?.bytes, original.bytes)
        XCTAssertEqual(archive.objects.first?.native["future"]?["integer"]?.integer, integer)
        XCTAssertEqual(archive.entrySHA256[original.path], AnyContentDigest.sha256(original.bytes))
        XCTAssertFalse(archive.permitsDestinationWrites)
        XCTAssertTrue(archive.issues.contains(where: { $0.code == .nativeSnapshotProofRequired }))
        XCTAssertTrue(archive.issues.contains(where: { $0.code == .nativeIdentityCensusRequired }))
        XCTAssertTrue(archive.issues.contains(where: { $0.code == .unknownEnvelopeField && $0.path.hasSuffix("/future") }))
    }

    func testRejectsUnsafePathsNonRegularEntriesAndPortablePathAliases() throws {
        for path in ["../object.json", "/object.json", "a//object.json", "a/./object.json",
                     "a/../object.json", "a\\object.json", "C:/object.json", "a./object.json",
                     "a /object.json", "a/\u{0000}object.json"] {
            XCTAssertThrowsError(try inspect([try index(), Entry(path: path, bytes: Data())]), path)
        }
        for kind: Entry.Kind in [.symbolicLink, .other] {
            XCTAssertThrowsError(try inspect([try index(), Entry(path: "native.dat", bytes: Data(), kind: kind)]))
        }
        XCTAssertThrowsError(try inspect([
            try index(), Entry(path: "Objects/A.bin", bytes: Data()), Entry(path: "objects/a.bin", bytes: Data())
        ]))
        XCTAssertThrowsError(try inspect([
            try index(), Entry(path: "é.bin", bytes: Data()), Entry(path: "e\u{0301}.bin", bytes: Data())
        ]))
    }

    func testRejectsDuplicateJSONKeysIncludingEscapedEquivalentSpellings() throws {
        for source in [
            #"{"formatVersion":"2.0","id":"one","id":"two"}"#,
            #"{"formatVersion":"2.0","id":"one","future":{"k":1,"\u006b":2}}"#
        ] {
            XCTAssertThrowsError(try inspect([
                try index(), Entry(path: "objects/duplicate.json", bytes: Data(source.utf8))
            ])) { error in
                guard case AnyTorahMigrationError.duplicateJSONKey = error else {
                    return XCTFail("Expected the original duplicate-key guard, got \(error)")
                }
            }
        }
    }

    func testRejectsNumericTokensThatTypedJSONWouldRound() throws {
        for token in ["18446744073709551615", "0.12345678901234567890123456789"] {
            let source = #"{"formatVersion":"2.0","id":"one","future":{"number":"# + token + "}}"
            XCTAssertThrowsError(try inspect([
                try index(), Entry(path: "objects/precision.json", bytes: Data(source.utf8))
            ])) { error in
                guard case AnyTorahMigrationError.numericPrecisionWouldChange = error else {
                    return XCTFail("Expected a precision refusal, got \(error)")
                }
            }
        }
    }

    func testRequiresSupportedVersionInIndexEveryDocumentAndPropertyDictionary() throws {
        XCTAssertThrowsError(try inspect([try index(["formatVersion": .string("2.1")])]))
        XCTAssertThrowsError(try inspect([try index(), try page(extra: ["formatVersion": .string("1.0")])]))
        XCTAssertThrowsError(try inspect([
            try index(["manifest": .object(["properties": .string("properties.json")])]),
            try entry("properties.json", .object(["formatVersion": .string("2.1"), "properties": .array([])]))
        ]))
    }

    func testRequiresExplicitUniqueObjectAndBlockIdentities() throws {
        XCTAssertThrowsError(try inspect([
            try index(), try entry("objects/no-id.json", .object(["formatVersion": .string("2.0")]))
        ]))
        XCTAssertThrowsError(try inspect([
            try index(), try page(), try page(path: "objects/copy.json")
        ]))
        XCTAssertThrowsError(try inspect([
            try index(), try page(extra: ["blocks": .array([block("same"), block("same")])])
        ]))
        XCTAssertThrowsError(try inspect([
            try index(), try page(extra: ["blocks": .array([.object(["type": .string("paragraph")])])])
        ]))
        XCTAssertThrowsError(try inspect([try index(), try page("_all_objects")]))
    }

    func testReconstructsFlatPreorderHierarchyAndRejectsInventedOrAmbiguousParents() throws {
        let archive = try inspect([
            try index(), try page(extra: ["blocks": .array([
                block("a"), block("b", indent: 1), block("c", indent: 2),
                block("d", indent: 1), block("e")
            ])])
        ])
        XCTAssertEqual(archive.objects[0].blocks.map(\.sourceID), ["a", "b", "c", "d", "e"])
        XCTAssertEqual(archive.objects[0].blocks.map(\.parentSourceID), [nil, "a", "b", "a", nil])
        for blocks in [
            [block("a", indent: 1)],
            [block("a"), block("b", indent: 2)],
            [block("a", extra: ["indent": .bool(true)])],
            [block("a", extra: ["indent": .number(0.5)])],
            [block("a", extra: ["children": .array([])])]
        ] {
            XCTAssertThrowsError(try inspect([try index(), try page(extra: ["blocks": .array(blocks)])]))
        }
    }

    func testPropertyLegendWinsWithoutDisplayNameCaseOrAmbiguityGuessing() throws {
        let definitions: [AnyJSON] = [
            .object(["internal_key": .string("custom-one"), "property": .string("Tag"),
                     "name": .string("First"), "format": .string("text")]),
            .object(["internal_key": .string("custom-two"), "property": .string("Tag"),
                     "name": .string("Second"), "format": .string("text")]),
            .object(["internal_key": .string("budget"), "property": .string("Budget"),
                     "name": .string("Caption"), "format": .string("number")])
        ]
        let archive = try inspect([
            try index(["manifest": .object(["properties": .string("properties.json")])]),
            try entry("properties.json", .object(["formatVersion": .string("2.0"), "properties": .array(definitions)])),
            try page(extra: [
                "properties": .object(["Tag": .string("value"), "Budget": .integer(5),
                                       "budget": .integer(7), "Caption": .integer(9)]),
                "property_internal_keys": .object(["Tag": .string("custom-two")])
            ]),
            try page("ambiguous-page", path: "objects/ambiguous.json",
                     extra: ["properties": .object(["Tag": .string("value")])])
        ])
        let object = try XCTUnwrap(archive.objects.first(where: { $0.sourceID == "page-source" }))
        XCTAssertEqual(object.propertyInternalKeys, ["Tag": "custom-two", "Budget": "budget"])
        XCTAssertEqual(archive.issues.filter { $0.code == .unresolvedProperty }.count, 3)
        let invalid = try page(extra: [
            "properties": .object(["Tag": .string("value")]),
            "property_internal_keys": .object(["Tag": .integer(1)])
        ])
        XCTAssertThrowsError(try inspect([try index(), invalid]))
    }

    func testFileManifestBindsRealIdentityAndExactBytesEvenForJSONFileNames() throws {
        let bytes = Data([0, 1, 2, 255])
        let file = try page("file-source", path: "files/file.anyblock.json", extra: ["kind": .string("file_object")])
        let header = try index(["manifest": .object([
            "files": .object(["file-source": .string("data/payload.json")])
        ])])
        let archive = try inspect([header, file, Entry(path: "data/payload.json", bytes: bytes)])
        XCTAssertEqual(archive.objects.count, 1)
        XCTAssertEqual(archive.filePathsByObjectID, ["file-source": "data/payload.json"])
        XCTAssertEqual(archive.originalEntries.first(where: { $0.path == "data/payload.json" })?.bytes, bytes)
        XCTAssertTrue(archive.issues.contains(where: { $0.code == .nativeFileImportRequired }))
        XCTAssertThrowsError(try inspect([header, file]))
        let unresolved = try inspect([try index(), file])
        XCTAssertTrue(unresolved.issues.contains(where: { $0.code == .missingFileBytes }))
        XCTAssertFalse(unresolved.permitsDestinationWrites)
        // An intentionally opaque descriptor: retention is not validation of
        // its CID/key grammar, network custody or recoverability.
        let remote = Data(#"{"version":1,"cid":"remote-source","key":"opaque-key"}"#.utf8).base64EncodedString()
        let remoteOnly = try inspect([
            try index(["network_id": .string("unknown-source-network")]),
            try page("remote-file", path: "files/remote.json",
                     extra: ["kind": .string("file_object"), "file_remote": .string(remote)])
        ])
        XCTAssertTrue(remoteOnly.issues.contains(where: { $0.code == .remoteFileRecoveryRequired }))
        XCTAssertEqual(remoteOnly.objects.first?.native["file_remote"]?.string, remote)
        XCTAssertFalse(remoteOnly.permitsDestinationWrites)
        let invalidRemote = try inspect([
            try index(), try page("empty-remote", extra: ["kind": .string("file_object"), "file_remote": .string("")])
        ])
        XCTAssertEqual(invalidRemote.objects.first?.native["file_remote"]?.string, "")
        XCTAssertTrue(invalidRemote.issues.contains(where: { $0.code == .remoteFileRecoveryRequired }))
        XCTAssertFalse(invalidRemote.permitsDestinationWrites)
        XCTAssertThrowsError(try inspect([
            header, try page("file-source"), Entry(path: "data/payload.json", bytes: bytes)
        ]))
    }

    func testContentBindingIsOrderIndependentAndChangesWithAnySourceBytesOrSpace() throws {
        let first = [try index(), try page(), Entry(path: "opaque.dat", bytes: Data([1, 2]))]
        let a = try inspect(first)
        let b = try inspect(Array(first.reversed()))
        XCTAssertEqual(a.contentSHA256, b.contentSHA256)
        XCTAssertEqual(a.issues, b.issues)
        XCTAssertNotEqual(a.contentSHA256, try inspect(first, space: "other-space").contentSHA256)
        let changed = [first[0], first[1], Entry(path: "opaque.dat", bytes: Data([1, 3]))]
        XCTAssertNotEqual(a.contentSHA256, try inspect(changed).contentSHA256)
    }

    func testReportsUnresolvedExportUnknownManifestAndSchemaMetadataWithoutDiscardingIt() throws {
        let archive = try inspect([
            try index([
                "manifest": .object(["properties": .string("properties.json"), "future": .string("opaque")]),
                "unresolved": .object(["objects": .array([.string("not-present")])]),
                "homepage": .string("page-source")
            ]),
            try entry("properties.json", .object([
                "formatVersion": .string("2.0"), "properties": .array([]), "future": .integer(3)
            ])),
            try page(extra: [
                "kind": .string("object_type"), "internal_key": .string("native-type"),
                "type_settings": .object(["layout": .string("basic")]),
                "blocks": .array([block("table", extra: ["type": .string("table"), "future": .bool(true)])])
            ]),
            Entry(path: "extra.bin", bytes: Data([7]))
        ])
        for code: AnyHeartSpaceArchive.Issue.Code in [
            .unresolvedExport, .unknownEnvelopeField, .sourceMetadataMappingRequired,
            .unsupportedObjectKind, .unsupportedBlockType, .unboundEntry
        ] {
            XCTAssertTrue(archive.issues.contains(where: { $0.code == code }), code.rawValue)
        }
        XCTAssertEqual(archive.originalEntries.count, 4)
        XCTAssertFalse(archive.permitsDestinationWrites)
    }

    func testRetainedNativeSidecarsAreBytePreservedButNeverTreatedAsSnapshotProof() throws {
        let sidecar = Entry(path: "native/census.json", bytes: Data(#"{"claimedComplete":true}"#.utf8))
        let archive = try AnyHeartSpaceArchive(sourceSpaceID: "source-space",
            entries: [try index(), try page(), sidecar], retainedNativeSidecarPaths: [sidecar.path])
        XCTAssertEqual(archive.originalEntries.first(where: { $0.path == sidecar.path })?.bytes, sidecar.bytes)
        XCTAssertTrue(archive.issues.contains(where: { $0.code == .nativeSnapshotProofRequired }))
        XCTAssertTrue(archive.issues.contains(where: { $0.code == .nativeIdentityCensusRequired }))
        XCTAssertFalse(archive.permitsDestinationWrites)
        XCTAssertThrowsError(try AnyHeartSpaceArchive(sourceSpaceID: "source-space", entries: [try index()],
                                                       retainedNativeSidecarPaths: ["native/missing.json"]))
        XCTAssertThrowsError(try AnyHeartSpaceArchive(sourceSpaceID: "source-space", entries: [try index()],
                                                       retainedNativeSidecarPaths: ["index.json"]))
    }
}
