import Foundation
import ProtobufMessages
import SwiftProtobuf
import ZIPFoundation

private enum ControlFailure: Error { case failed(String) }

private struct NativeFixture {
    static let root = "root-object"
    static let space = "native-space"
    static let file = "file-object"
    static let metadataKeys = [
        "pinkhaTorahAnnotationProtocol", "pinkhaTorahAnnotationClassification",
        "pinkhaTorahAnnotationNamespace", "pinkhaTorahAnnotationUUID",
        "pinkhaTorahAnnotationCreationDestination", "pinkhaTorahAnnotationCreationAccount",
        "pinkhaTorahAnnotationCreationSpace", "pinkhaTorahAnnotationCreationMessageID",
        "pinkhaTorahAnnotationCreationMutationID", "pinkhaTorahAnnotationCreationRevision",
        "pinkhaTorahAnnotationCreationSourceDigest", "pinkhaTorahAnnotationCreationPayloadDigest",
        "pinkhaTorahAnnotationAppliedMessageID", "pinkhaTorahAnnotationAppliedMutationID",
        "pinkhaTorahAnnotationAppliedRevision", "pinkhaTorahAnnotationAppliedSourceDigest",
        "pinkhaTorahAnnotationAppliedPayloadDigest"
    ]
    static let localKeys = [
        "pinkhaTorahSources", "pinkhaTorahTopics", "pinkhaTorahWords", "_pinkhaTorahReady",
        "_pinkhaTorahLabels", "_pinkhaTorahProjectionVersion", "_pinkhaTorahCanonicalHash",
        "_pinkhaTorahState", "_pinkhaTorahCanonicalPropertyKey", "_pinkhaTorahCacheIntegrity",
        "_pinkhaTorahAttachedProperties"
    ]
    var root: OriginalAnnotationNativeSnapshotWire
    var file: OriginalAnnotationNativeSnapshotWire
    var fileBytes = Data("קובץ attachment English\n".utf8)

    init() {
        var details = Google_Protobuf_Struct()
        details.fields["id"] = Self.string(Self.root)
        details.fields["spaceId"] = Self.string(Self.space)
        details.fields["type"] = Self.list(["native-annotation-type"])
        details.fields["ordinaryDetail"] = Self.string("original detail")
        details.fields["lastModifiedDate"] = .with { $0.numberValue = 7 }
        for key in Self.metadataKeys { details.fields[key] = Self.string("fixed-" + key) }
        let rootBlock = Anytype_Model_Block.with {
            $0.id = Self.root
            $0.childrenIds = ["he-en-one", "en-he-two", "attachment"]
            $0.smartblock = .init()
        }
        let first = Anytype_Model_Block.with {
            $0.id = "he-en-one"
            $0.text = .with { $0.text = "שלום עולם — first English block"; $0.style = .paragraph }
        }
        let second = Anytype_Model_Block.with {
            $0.id = "en-he-two"
            $0.text = .with { $0.text = "Second English block — תורה"; $0.style = .paragraph }
        }
        let attachment = Anytype_Model_Block.with {
            $0.id = "attachment"
            $0.file = .with { $0.type = .file; $0.state = .done; $0.targetObjectID = Self.file; $0.name = "notes.txt" }
        }
        var body = Anytype_Model_SmartBlockSnapshotBase()
        body.details = details
        body.blocks = [rootBlock, first, second, attachment]
        body.objectTypes = ["ot-pinkhatorahannotationv1"]
        body.collections = .with { $0.fields["collection"] = Self.list(["member-one", "member-two"]) }
        body.relationLinks = [.with { $0.key = "ordinaryDetail"; $0.format = .longtext }]
        var snapshot = OriginalAnnotationNativeChangeSnapshotWire()
        snapshot.data = body
        root = OriginalAnnotationNativeSnapshotWire()
        root.sbType = .page
        root.snapshot = snapshot

        var fileBody = Anytype_Model_SmartBlockSnapshotBase()
        fileBody.details = .with {
            $0.fields["id"] = Self.string(Self.file)
            $0.fields["spaceId"] = Self.string(Self.space)
            $0.fields["source"] = Self.string("files/notes.txt")
        }
        fileBody.fileInfo = .with { $0.fileID = "native-file-content-id" }
        var fileSnapshot = OriginalAnnotationNativeChangeSnapshotWire()
        fileSnapshot.data = fileBody
        file = OriginalAnnotationNativeSnapshotWire()
        file.sbType = .fileObject
        file.snapshot = fileSnapshot
    }

    static func string(_ value: String) -> Google_Protobuf_Value { .with { $0.stringValue = value } }
    static func list(_ values: [String]) -> Google_Protobuf_Value {
        .with { $0.listValue = .with { $0.values = values.map(string) } }
    }
    mutating func editRoot(_ edit: (inout Anytype_Model_SmartBlockSnapshotBase) throws -> Void) rethrows {
        var snapshot = root.snapshot!, body = snapshot.data!
        try edit(&body)
        snapshot.data = body
        root.snapshot = snapshot
    }
    mutating func editFile(_ edit: (inout Anytype_Model_SmartBlockSnapshotBase) -> Void) {
        var snapshot = file.snapshot!, body = snapshot.data!
        edit(&body)
        snapshot.data = body
        file.snapshot = snapshot
    }

    func entries() throws -> [(String, Data)] {
        let rootDirectory = root.sbType == .template ? "templates" : "objects"
        return [("\(rootDirectory)/\(Self.root).pb", try root.serializedData()),
                ("filesObjects/\(Self.file).pb", try file.serializedData()), ("files/notes.txt", fileBytes)]
    }
    func archive(reverse: Bool = false, compression: CompressionMethod = .deflate) throws -> Data {
        let values = try entries()
        return try Self.archive(reverse ? Array(values.reversed()) : values, compression: compression)
    }
    static func archive(_ entries: [(String, Data)], compression: CompressionMethod = .deflate) throws -> Data {
        let archive = try Archive(data: Data(), accessMode: .create)
        for (path, bytes) in entries {
            try archive.addEntry(with: path, type: .file, uncompressedSize: Int64(bytes.count),
                                 modificationDate: Date(timeIntervalSince1970: 1_700_000_000),
                                 compressionMethod: compression) { position, count in
                let lower = Int(position)
                return bytes.subdata(in: lower..<min(bytes.count, lower + count))
            }
        }
        guard let bytes = archive.data else { throw ControlFailure.failed("missing in-memory ZIP") }
        return bytes
    }
    func comparison(reverse: Bool = false, compression: CompressionMethod = .deflate) throws -> OriginalAnnotationNativeArchiveComparison {
        try Self.comparison(archive(reverse: reverse, compression: compression))
    }
    static func comparison(_ bytes: Data, version: Int64 = 1, count: Int32 = 2) throws -> OriginalAnnotationNativeArchiveComparison {
        try OriginalAnnotationNativeArchiveComparison(archiveBytes: bytes, rootID: Self.root,
                                                       spaceID: Self.space, formatVersion: version,
                                                       reportedObjectCount: count)
    }

    // Fixture construction only: append an unsupported field to the first
    // actual map-entry message without letting the lossy decoder erase it.
    static func extendMessage(_ data: Data, path: [Int], suffix: Data) throws -> Data {
        guard let wanted = path.first else { return data + suffix }
        let bytes = Array(data)
        var cursor = 0
        func number() throws -> UInt64 {
            var value: UInt64 = 0
            for index in 0..<10 {
                guard cursor < bytes.count else { throw ControlFailure.failed("fixture wire truncation") }
                let byte = bytes[cursor]; cursor += 1
                value |= UInt64(byte & 127) << (index * 7)
                if byte & 128 == 0 { return value }
            }
            throw ControlFailure.failed("fixture varint")
        }
        func encoded(_ number: UInt64) -> Data {
            var value = number, result = Data()
            while value >= 128 { result.append(UInt8(value & 127) | 128); value >>= 7 }
            result.append(UInt8(value)); return result
        }
        while cursor < bytes.count {
            let start = cursor, tag = try number()
            switch tag & 7 {
            case 0: _ = try number()
            case 1: cursor += 8
            case 5: cursor += 4
            case 2:
                let count = Int(try number()), lower = cursor, upper = cursor + count
                guard upper <= bytes.count else { throw ControlFailure.failed("fixture message truncation") }
                if Int(tag >> 3) == wanted {
                    let changed = try extendMessage(Data(bytes[lower..<upper]), path: Array(path.dropFirst()), suffix: suffix)
                    return Data(bytes[..<start]) + encoded(tag) + encoded(UInt64(changed.count)) + changed + Data(bytes[upper...])
                }
                cursor = upper
            default: throw ControlFailure.failed("fixture wire type")
            }
        }
        throw ControlFailure.failed("fixture field not found")
    }
}

@main
private struct NativeBodySemanticControls {
    static func main() throws {
        let fixture = NativeFixture()
        let reference = try fixture.comparison()
        var outcomes: [[String: String]] = []
        func check(_ name: String, _ body: () throws -> Void) throws {
            // Preserve individual outcomes even if a later new case fails.
            // The runner retains stderr verbatim; stdout is the final JSON.
            do {
                try body()
                let outcome = ["name": name, "status": "PASS"]
                outcomes.append(outcome)
                FileHandle.standardError.write(try JSONSerialization.data(withJSONObject: outcome, options: [.sortedKeys]) + Data([10]))
            } catch {
                let outcome = ["name": name, "status": "FAIL", "error": String(describing: error)]
                FileHandle.standardError.write(try JSONSerialization.data(withJSONObject: outcome, options: [.sortedKeys]) + Data([10]))
                throw error
            }
        }
        func mismatch(_ other: NativeFixture, _ expected: OriginalAnnotationNativeArchiveComparison.Failure) throws {
            do {
                try reference.requireEqual(to: other.comparison())
            } catch let error as OriginalAnnotationNativeArchiveComparison.Failure {
                guard error == expected else { throw ControlFailure.failed("unexpected mismatch: \(error)") }
                return
            }
            throw ControlFailure.failed("changed full native graph compared equal")
        }
        func rejects(_ bytes: Data, _ expected: OriginalAnnotationNativeArchiveComparison.Failure,
                     version: Int64 = 1, count: Int32 = 2) throws {
            do { _ = try NativeFixture.comparison(bytes, version: version, count: count) }
            catch let error as OriginalAnnotationNativeArchiveComparison.Failure {
                guard error == expected else { throw ControlFailure.failed("unexpected rejection: \(error)") }
                return
            }
            throw ControlFailure.failed("unsupported archive accepted")
        }

        try check("mixed Hebrew/English two-block graph and actual attachment bytes compare equal") {
            try reference.requireEqual(to: fixture.comparison())
        }
        try check("ZIP member ordering does not replace native graph semantics") {
            try reference.requireEqual(to: fixture.comparison(reverse: true))
        }
        try check("compression/container hash differences preserve equal graph semantics") {
            guard try fixture.archive(compression: .none) != fixture.archive(compression: .deflate) else {
                throw ControlFailure.failed("test did not change the container")
            }
            try reference.requireEqual(to: fixture.comparison(compression: .none))
        }
        try check("block inventory ordering is independent of ordered children") {
            var changed = fixture
            changed.editRoot { $0.blocks.reverse() }
            try reference.requireEqual(to: changed.comparison())
        }
        try check("only the exact eleven original r14 local keys are excluded") {
            var changed = fixture
            changed.editRoot { body in
                for key in NativeFixture.localKeys { body.details.fields[key] = NativeFixture.string("local-change") }
            }
            try reference.requireEqual(to: changed.comparison())
        }
        try check("all seventeen creation/applied metadata values remain compared") {
            for key in NativeFixture.metadataKeys {
                var changed = fixture
                changed.editRoot { $0.details.fields[key] = NativeFixture.string("changed") }
                try mismatch(changed, .differentNativeObject(NativeFixture.root))
            }
        }
        try check("Unicode-equivalent local-key spelling is not an exact-key exclusion") {
            var changed = fixture
            changed.editRoot { $0.details.fields["_pinkhaTorahCanonicalPropertyKey"] = NativeFixture.string("must-remain") }
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("ordinary detail changes remain visible") {
            var changed = fixture
            changed.editRoot { $0.details.fields["ordinaryDetail"] = NativeFixture.string("changed") }
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("ordinary native timestamp is not silently excluded") {
            var changed = fixture
            changed.editRoot { $0.details.fields["lastModifiedDate"] = .with { $0.numberValue = 8 } }
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("real text content mutation is rejected") {
            var changed = fixture
            changed.editRoot { $0.blocks[1].text.text += " changed" }
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("child order remains part of body semantics") {
            var changed = fixture
            changed.editRoot { $0.blocks[0].childrenIds.reverse() }
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("collection membership order remains part of snapshot semantics") {
            var changed = fixture
            changed.editRoot { $0.collections.fields["collection"] = NativeFixture.list(["member-two", "member-one"]) }
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("attachment bytes cannot be replaced by matching metadata") {
            var changed = fixture
            changed.fileBytes.append(0)
            try mismatch(changed, .differentFile("files/notes.txt"))
        }
        try check("native file info remains part of the complete graph") {
            var changed = fixture
            changed.editFile { $0.fileInfo.fileID = "different-content-id" }
            try mismatch(changed, .differentNativeObject(NativeFixture.file))
        }
        try check("object references are not guessed or remapped") {
            var changed = fixture
            changed.editRoot { $0.blocks[3].file.targetObjectID = "another-object" }
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("native object type semantics remain compared") {
            var changed = fixture
            changed.editRoot { $0.objectTypes = ["ot-another-type"] }
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("relation link formats remain compared") {
            var changed = fixture
            changed.editRoot { $0.relationLinks[0].format = .number }
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("native smartblock type wrapper remains compared") {
            var changed = fixture
            changed.root.sbType = .template
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("snapshot heads are preserved rather than ignored") {
            var changed = fixture
            changed.root.snapshot!.logHeads["log"] = "head"
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("snapshot-level file keys remain compared") {
            var changed = fixture
            var key = OriginalAnnotationNativeFileKeysWire()
            key.hash = "native-file-hash"
            key.keys = ["path": "key"]
            changed.root.snapshot!.fileKeys = [key]
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("unknown wrapper fields survive decoding and change equality") {
            var changed = fixture
            changed.root = try .init(serializedBytes: fixture.root.serializedData() + Data([0xa0, 0x06, 0x01]))
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("unknown nested block fields survive decoding and change equality") {
            var changed = fixture
            try changed.editRoot { body in
                body.blocks[1] = try .init(serializedBytes: body.blocks[1].serializedData() + Data([0xa0, 0x06, 0x01]))
            }
            try mismatch(changed, .differentNativeObject(NativeFixture.root))
        }
        try check("missing attachment file bytes refuse the archive") {
            try rejects(NativeFixture.archive(Array(try fixture.entries().prefix(2))), .missingFileBytes)
        }
        try check("the original reported object count must match the whole graph") {
            try rejects(fixture.archive(), .incompleteInventory, count: 3)
        }
        try check("unsupported snapshot body version stays unproven") {
            try rejects(fixture.archive(), .unsupportedVersion, version: 2)
        }
        try check("a dependent native object cannot silently disappear") {
            let rootOnly = [("objects/\(NativeFixture.root).pb", try fixture.root.serializedData())]
            let missing = try NativeFixture.comparison(NativeFixture.archive(rootOnly), count: 1)
            do { try reference.requireEqual(to: missing) }
            catch OriginalAnnotationNativeArchiveComparison.Failure.differentObjectGraph { return }
            throw ControlFailure.failed("different dependency graph compared equal")
        }
        try check("wrong root Space is rejected from actual snapshot details") {
            var changed = fixture
            changed.editRoot { $0.details.fields["spaceId"] = NativeFixture.string("other-space") }
            try rejects(changed.archive(), .wrongSpace)
        }
        try check("duplicate block identities cannot be normalized away") {
            var changed = fixture
            changed.editRoot { $0.blocks.append($0.blocks[1]) }
            try rejects(changed.archive(), .duplicateNativeBlock)
        }
        try check("map-entry unknown field is rejected by the full ZIP/protobuf path before decoder loss") {
            var entries = try fixture.entries()
            let raw = entries[0].1
            let extended = try NativeFixture.extendMessage(raw, path: [2, 2, 2, 1], suffix: Data([0x18, 0x01]))
            // Confirm the pinned underlying decoder itself would erase this
            // difference; acceptance must come from our pre-decode guard.
            guard try OriginalAnnotationNativeSnapshotWire(serializedBytes: raw)
                == OriginalAnnotationNativeSnapshotWire(serializedBytes: extended) else {
                throw ControlFailure.failed("pinned decoder no longer has the audited map-entry behavior")
            }
            entries[0].1 = extended
            do { _ = try NativeFixture.comparison(NativeFixture.archive(entries)) }
            catch OriginalAnnotationNativeMapKeyGuard.Failure.unsupportedMapEntry { return }
            throw ControlFailure.failed("lossy map entry reached comparison")
        }
        try check("compressed member CRC is checked against actual extracted bytes") {
            var bytes = try fixture.archive()
            let inventory = try OriginalAnnotationNativeArchiveLayout(bytes)
            guard let first = inventory.entries.first, first.checksum != 0 else {
                throw ControlFailure.failed("fixture CRC is zero")
            }
            let end = bytes.count - 22
            let central = (0..<4).reduce(0) { $0 | Int(bytes[end + 16 + $1]) << ($1 * 8) }
            bytes.replaceSubrange((first.localOffset + 14)..<(first.localOffset + 18), with: [0, 0, 0, 0])
            bytes.replaceSubrange((central + 16)..<(central + 20), with: [0, 0, 0, 0])
            try rejects(bytes, .invalidEntry)
        }
        let report: [String: Any] = [
            "status": "PASS_NEW_NATIVE_ARCHIVE_SEMANTIC_CONTROLS", "tests_run": outcomes.count,
            "tests": outcomes, "native_executions": 0, "prior_controls_rerun": 0,
            "scope": "Real pinned SwiftProtobuf and ZIPFoundation over exact original generated model types and new production comparator; synthetic original-format fixtures; no engine/Owner/atomic/mapping/ACK acceptance"
        ]
        print(String(decoding: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), as: UTF8.self))
    }
}
