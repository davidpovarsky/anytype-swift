import Foundation
import ProtobufMessages
import SwiftProtobuf
import ZIPFoundation

/// Pure comparison data only. Parsing caller bytes never creates native owner,
/// import-map, saved-state or commit authority. The closed held-read route below
/// is the only producer of a historical native comparison observation.
internal struct OriginalAnnotationNativeArchiveComparison: Sendable {
    internal enum Failure: Error, Sendable, Equatable {
        case unsupportedVersion
        case unsupportedEntry
        case invalidEntry
        case incompleteInventory
        case invalidNativeObject
        case duplicateNativeObject
        case duplicateNativeBlock
        case wrongSpace
        case wrongRoot
        case missingFileBytes
        case differentObjectGraph
        case differentFileInventory
        case differentNativeObject(String)
        case differentFile(String)
    }

    /// EXACT r14 core/pinkha/torah.LocalKeys. No other local, derived, creation,
    /// applied, identity, relation, type or native body field is excluded.
    static let excludedLocalDetailKeys: [String] = [
        "pinkhaTorahSources", "pinkhaTorahTopics", "pinkhaTorahWords",
        "_pinkhaTorahReady", "_pinkhaTorahLabels", "_pinkhaTorahProjectionVersion",
        "_pinkhaTorahCanonicalHash", "_pinkhaTorahState", "_pinkhaTorahCanonicalPropertyKey",
        "_pinkhaTorahCacheIntegrity", "_pinkhaTorahAttachedProperties"
    ]

    let rootID: String
    let spaceID: String
    let formatVersion: Int64
    let rootSnapshot: Anytype_Model_SmartBlockSnapshotBase
    let objectIDs: [String]
    let filePaths: [String]
    private let objects: [String: Data]
    private let files: [Data: Data]

    init(archiveBytes: Data, rootID: String, spaceID: String,
         formatVersion: Int64, reportedObjectCount: Int32) throws {
        guard formatVersion == 1 else { throw Failure.unsupportedVersion }
        guard Self.identifier(rootID), Self.identifier(spaceID) else { throw Failure.wrongRoot }
        let layout = try OriginalAnnotationNativeArchiveLayout(archiveBytes)
        let archive = try Archive(data: archiveBytes, accessMode: .read)
        let indexed = Dictionary(uniqueKeysWithValues: layout.entries.map { ($0.pathBytes, $0) })
        var visited = Set<Data>()
        var objectBytes: [String: Data] = [:]
        var nativeObjects: [String: Anytype_Model_SmartBlockSnapshotBase] = [:]
        var binaryFiles: [Data: Data] = [:]
        var binaryNames: [String] = []
        var requiredFiles = Set<Data>()
        var options = BinaryDecodingOptions()
        options.discardUnknownFields = false
        options.messageDepthLimit = 100
        for entry in archive {
            let path = entry.path, pathBytes = Data(path.utf8)
            guard let item = indexed[pathBytes], visited.insert(pathBytes).inserted,
                  entry.type == .file,
                  entry.compressedSize == UInt64(item.compressedBytes),
                  entry.uncompressedSize == UInt64(item.uncompressedBytes),
                  entry.checksum == item.checksum else { throw Failure.invalidEntry }
            var bytes = Data()
            let crc = try archive.extract(entry, bufferSize: 16_384, skipCRC32: false) { chunk in
                guard chunk.count <= item.uncompressedBytes - bytes.count else {
                    throw OriginalAnnotationNativeArchiveLayout.Failure.sizeLimit
                }
                bytes.append(chunk)
            }
            guard bytes.count == item.uncompressedBytes, crc == item.checksum else {
                throw Failure.invalidEntry
            }
            if path.hasPrefix("files/") {
                guard path.split(separator: "/").count == 2 else { throw Failure.unsupportedEntry }
                binaryFiles[pathBytes] = bytes
                binaryNames.append(path)
                continue
            }
            guard path.hasSuffix(".pb"), path.split(separator: "/").count == 2 else {
                throw Failure.unsupportedEntry
            }
            try OriginalAnnotationNativeMapKeyGuard.validate(bytes)
            var wire = try OriginalAnnotationNativeSnapshotWire(serializedBytes: bytes, options: options)
            guard var snapshot = wire.snapshot, var body = snapshot.data, body.hasDetails,
                  let id = Self.string(body.details, "id"), Self.identifier(id),
                  let nativeSpace = Self.string(body.details, "spaceId") else {
                throw Failure.invalidNativeObject
            }
            guard nativeSpace.utf8.elementsEqual(spaceID.utf8) else { throw Failure.wrongSpace }
            guard nativeObjects[id] == nil else { throw Failure.duplicateNativeObject }
            let directory = try Self.directory(for: wire.sbType)
            guard path.utf8.elementsEqual("\(directory)/\(id).pb".utf8) else {
                throw Failure.invalidNativeObject
            }
            if wire.sbType == .fileObject {
                guard let file = Self.string(body.details, "source"), file.hasPrefix("files/"),
                      file.split(separator: "/").count == 2, body.hasFileInfo,
                      !body.fileInfo.fileID.isEmpty else { throw Failure.missingFileBytes }
                try OriginalAnnotationNativeArchiveLayout.validatePath(file)
                requiredFiles.insert(Data(file.utf8))
            }
            // Preserve original decoded data for strict metadata inspection.
            nativeObjects[id] = body
            var blockIDs = Set<Data>()
            for block in body.blocks {
                guard !block.id.isEmpty, blockIDs.insert(Data(block.id.utf8)).inserted else {
                    throw Failure.duplicateNativeBlock
                }
            }
            for block in body.blocks {
                guard block.childrenIds.allSatisfy({ blockIDs.contains(Data($0.utf8)) }) else {
                    throw Failure.invalidNativeObject
                }
            }
            // BlocksToSave is an inventory. Child order and all content remain
            // untouched; only inventory order is normalized by exact UTF-8 ID.
            body.blocks.sort { Data($0.id.utf8).lexicographicallyPrecedes(Data($1.id.utf8)) }
            for key in Self.excludedLocalDetailKeys {
                if let exactKey = body.details.fields.keys.first(where: { $0.utf8.elementsEqual(key.utf8) }) {
                    body.details.fields.removeValue(forKey: exactKey)
                }
            }
            snapshot.data = body
            wire.snapshot = snapshot
            objectBytes[id] = try Self.canonicalBytes(wire)
        }
        guard visited.count == layout.entries.count,
              visited == Set(indexed.keys), reportedObjectCount > 0,
              Int(reportedObjectCount) == objectBytes.count else { throw Failure.incompleteInventory }
        guard requiredFiles == Set(binaryFiles.keys) else { throw Failure.missingFileBytes }
        guard let root = nativeObjects[rootID] else { throw Failure.wrongRoot }
        self.rootID = rootID
        self.spaceID = spaceID
        self.formatVersion = formatVersion
        rootSnapshot = root
        objectIDs = objectBytes.keys.sorted()
        filePaths = binaryNames.sorted { Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8)) }
        objects = objectBytes
        files = binaryFiles
    }

    /// Equal means equal exported graph semantics and file bytes under the
    /// bounded supported codec. It never means that native state is atomic,
    /// still current, durably applied, or safe to acknowledge.
    func requireEqual(to observed: Self) throws {
        guard formatVersion == observed.formatVersion else { throw Failure.unsupportedVersion }
        guard rootID.utf8.elementsEqual(observed.rootID.utf8),
              spaceID.utf8.elementsEqual(observed.spaceID.utf8) else { throw Failure.wrongRoot }
        guard objects.keys.sorted() == observed.objects.keys.sorted() else {
            throw Failure.differentObjectGraph
        }
        guard Set(files.keys) == Set(observed.files.keys) else { throw Failure.differentFileInventory }
        for id in objectIDs {
            guard objects[id] == observed.objects[id] else { throw Failure.differentNativeObject(id) }
        }
        for path in filePaths {
            let key = Data(path.utf8)
            guard files[key] == observed.files[key] else { throw Failure.differentFile(path) }
        }
    }

    private static func canonicalBytes<M: Message>(_ message: M) throws -> Data {
        var options = BinaryEncodingOptions()
        options.useDeterministicOrdering = true
        // Deterministic protobuf bytes preserve exact UTF-8 text, unknown fields,
        // scalar values, ordered children, relation values and file metadata.
        return try message.serializedData(options: options)
    }

    private static func string(_ details: Google_Protobuf_Struct, _ key: String) -> String? {
        guard case .stringValue(let value)? = details.fields[key]?.kind else { return nil }
        return value
    }

    private static func identifier(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 512 && value.utf8.allSatisfy {
            (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0)
                || [45, 46, 58, 95].contains($0)
        }
    }

    private static func directory(for type: Anytype_Model_SmartBlockType) throws -> String {
        switch type {
        case .strelation: return "relations"
        case .strelationOption: return "relationsOptions"
        case .sttype: return "types"
        case .template: return "templates"
        case .fileObject: return "filesObjects"
        // Legacy raw-file exports have no supported complete file-byte contract.
        case .file, .UNRECOGNIZED(_): throw Failure.unsupportedEntry
        default: return "objects"
        }
    }
}
