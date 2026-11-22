import Foundation
import PinkhaAnyEngine

public enum AnyHeartSpaceArchiveError: Error, Equatable, Sendable {
    case limit, unsafePath(String), duplicatePath(String), unsupportedEntry(String)
    case missingEntry(String), malformed(String), unsupportedVersion(String)
    case missingIdentity(String), duplicateIdentity(String), invalidHierarchy(String), missingFileBytes(String)
}

/// Bounded, byte-preserving inspection of a Heart AnyBlock 2.0 export.
/// This is not a generic importer or proof of an atomic/full native Space
/// snapshot. No inspection result authorizes destination writes.
public struct AnyHeartSpaceArchive: Sendable {
    public struct Entry: Sendable {
        public enum Kind: Equatable, Sendable { case regularFile, symbolicLink, other }
        public let path: String
        public let bytes: Data
        public let kind: Kind
        public init(path: String, bytes: Data, kind: Kind = .regularFile) {
            self.path = path; self.bytes = bytes; self.kind = kind
        }
    }

    public struct Block: Sendable {
        public let sourceID: String
        public let type: String
        public let parentSourceID: String?
        public let order: Int
        public let native: AnyJSON
    }

    public struct Object: Sendable {
        public let sourceID: String
        public let path: String
        public let kind: String
        public let typeInternalKey: String?
        public let native: AnyJSON
        public let blocks: [Block]
        /// Exact dictionary identities, with no display-name or case guessing.
        public let propertyInternalKeys: [String: String]
    }

    public struct Property: Sendable {
        public let internalKey: String
        public let spelling: String
        public let format: String
        public let native: AnyJSON
    }

    public struct Issue: Equatable, Sendable {
        public enum Code: String, Sendable {
            case nativeSnapshotProofRequired, nativeIdentityCensusRequired, unresolvedExport
            case unboundEntry, unknownEnvelopeField, unsupportedObjectKind, missingTypeIdentity
            case unresolvedProperty, unsupportedBlockType, inlineConversionRequired
            case nativeFileImportRequired, sourceMetadataMappingRequired, nativeSchemaMappingRequired
            case remoteFileRecoveryRequired, missingFileBytes
        }
        public let code: Code
        public let path: String
        public let identity: String?
    }

    public static let maximumEntries = 100_000
    public static let maximumTotalBytes = 512 * 1024 * 1024
    public static let maximumJSONBytes = 24 * 1024 * 1024
    public static let maximumDocumentCount = 20_000
    public static let maximumBlockCount = 100_000
    public let sourceSpaceID: String
    public let index: AnyJSON
    public let objects: [Object]
    public let properties: [Property]
    public let filePathsByObjectID: [String: String]
    /// All supplied regular files, including unknown JSON and original blobs.
    public let originalEntries: [Entry]
    public let entrySHA256: [String: String]
    public let contentSHA256: String
    public let issues: [Issue]

    /// AnyBlock may be a rolling projection and omits native root/wrapper
    /// identities, unused schema and metadata. A native snapshot/census
    /// adapter must establish complete source admission above this inspection.
    public var permitsDestinationWrites: Bool { false }

    public init(sourceSpaceID: String, entries: [Entry], indexPath: String = "index.json",
                retainedNativeSidecarPaths: Set<String> = []) throws {
        guard !sourceSpaceID.isEmpty, sourceSpaceID.utf8.count <= 4096,
              sourceSpaceID.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }),
              !entries.isEmpty, entries.count <= Self.maximumEntries else { throw AnyHeartSpaceArchiveError.limit }
        try Self.validatePath(indexPath)
        var byPath: [String: Data] = [:], portablePaths = Set<String>(), total = 0
        for entry in entries {
            try Self.validatePath(entry.path)
            guard entry.kind == .regularFile else { throw AnyHeartSpaceArchiveError.unsupportedEntry(entry.path) }
            let portable = entry.path.precomposedStringWithCanonicalMapping.lowercased()
            guard byPath[entry.path] == nil, portablePaths.insert(portable).inserted else {
                throw AnyHeartSpaceArchiveError.duplicatePath(entry.path)
            }
            guard entry.bytes.count <= Self.maximumTotalBytes - total else { throw AnyHeartSpaceArchiveError.limit }
            total += entry.bytes.count; byPath[entry.path] = entry.bytes
        }
        for path in retainedNativeSidecarPaths {
            try Self.validatePath(path)
            guard byPath[path] != nil, path != indexPath else { throw AnyHeartSpaceArchiveError.missingEntry(path) }
        }
        func read(_ path: String) throws -> AnyJSON {
            guard let bytes = byPath[path] else { throw AnyHeartSpaceArchiveError.missingEntry(path) }
            return try Self.json(bytes)
        }
        let index = try read(indexPath)
        try Self.version(index, path: indexPath)
        guard index.object != nil, index["id"] == nil else { throw AnyHeartSpaceArchiveError.malformed(indexPath) }
        var issues: [Issue] = [
            .init(code: .nativeSnapshotProofRequired, path: indexPath, identity: sourceSpaceID),
            .init(code: .nativeIdentityCensusRequired, path: indexPath, identity: sourceSpaceID)
        ]
        let manifest = try Self.objectField(index, "manifest", path: indexPath)
        for key in manifest.keys.sorted() where !["properties", "files"].contains(key) {
            issues.append(.init(code: .unknownEnvelopeField, path: indexPath + "/manifest/" + key, identity: nil))
        }
        if let unresolved = index["unresolved"], !Self.isEmptyContainer(unresolved) {
            issues.append(.init(code: .unresolvedExport, path: indexPath + "/unresolved", identity: nil))
        }
        var usedPaths: Set<String> = [indexPath]
        usedPaths.formUnion(retainedNativeSidecarPaths)
        var properties: [Property] = [], dictionaryPath: String?
        if let reference = manifest["properties"] {
            guard let path = reference.string else { throw AnyHeartSpaceArchiveError.malformed(indexPath + "/manifest/properties") }
            try Self.validatePath(path)
            guard usedPaths.insert(path).inserted else { throw AnyHeartSpaceArchiveError.duplicatePath(path) }
            dictionaryPath = path
            let dictionary = try read(path)
            try Self.version(dictionary, path: path)
            guard let values = dictionary["properties"]?.array, values.count <= 20_000 else {
                throw AnyHeartSpaceArchiveError.malformed(path)
            }
            var keys = Set<String>()
            for (offset, value) in values.enumerated() {
                let location = path + "/properties/" + String(offset)
                guard let key = value["internal_key"]?.string, !key.isEmpty,
                      let spelling = value["property"]?.string, !spelling.isEmpty,
                      let format = value["format"]?.string, !format.isEmpty, value.object != nil else {
                    throw AnyHeartSpaceArchiveError.missingIdentity(location)
                }
                guard keys.insert(key).inserted else { throw AnyHeartSpaceArchiveError.duplicateIdentity(key) }
                properties.append(.init(internalKey: key, spelling: spelling, format: format, native: value))
                issues.append(.init(code: .nativeSchemaMappingRequired, path: location, identity: key))
            }
            for key in dictionary.object!.keys.sorted() where !["$schema", "formatVersion", "properties"].contains(key) {
                issues.append(.init(code: .unknownEnvelopeField, path: path + "/" + key, identity: nil))
            }
        }
        var filePaths: [String: String] = [:]
        if let field = manifest["files"] {
            guard let values = field.object else { throw AnyHeartSpaceArchiveError.malformed(indexPath + "/manifest/files") }
            for id in values.keys.sorted() {
                let value = values[id]!
                guard !id.isEmpty, let path = value.string else { throw AnyHeartSpaceArchiveError.malformed(indexPath + "/manifest/files") }
                try Self.validatePath(path)
                guard usedPaths.insert(path).inserted else { throw AnyHeartSpaceArchiveError.duplicatePath(path) }
                guard byPath[path] != nil else { throw AnyHeartSpaceArchiveError.missingFileBytes(id) }
                filePaths[id] = path
            }
        }
        let byKey = Dictionary(uniqueKeysWithValues: properties.map { ($0.internalKey, $0) })
        let bySpelling = Dictionary(grouping: properties, by: \.spelling)
        var objects: [Object] = [], identities = Set<String>(), totalBlocks = 0
        for path in byPath.keys.sorted() where !usedPaths.contains(path) {
            guard path.lowercased().hasSuffix(".json") else {
                issues.append(.init(code: .unboundEntry, path: path, identity: nil)); continue
            }
            let value = try read(path)
            try Self.version(value, path: path)
            guard let id = value["id"]?.string, !id.isEmpty, !id.hasPrefix("_"), id.utf8.count <= 4096,
                  value.object != nil else { throw AnyHeartSpaceArchiveError.missingIdentity(path) }
            guard identities.insert(id).inserted else { throw AnyHeartSpaceArchiveError.duplicateIdentity(id) }
            guard objects.count < Self.maximumDocumentCount else { throw AnyHeartSpaceArchiveError.limit }
            let kind: String
            if let field = value["kind"] {
                guard let text = field.string, !text.isEmpty else { throw AnyHeartSpaceArchiveError.malformed(path + "/kind") }
                kind = text
            } else { kind = "page" }
            if kind != "page" { issues.append(.init(code: .unsupportedObjectKind, path: path + "/kind", identity: id)) }
            let typeKey = value["type_internal_key"]?.string
            if value["type"] != nil && (typeKey == nil || typeKey?.isEmpty == true) {
                issues.append(.init(code: .missingTypeIdentity, path: path + "/type_internal_key", identity: id))
            }
            if let typeKey {
                guard !typeKey.isEmpty, value["type"]?.string != nil else {
                    throw AnyHeartSpaceArchiveError.malformed(path + "/type_internal_key")
                }
                issues.append(.init(code: .nativeSchemaMappingRequired, path: path + "/type_internal_key", identity: typeKey))
            }
            var propertyKeys: [String: String] = [:]
            let legend = try Self.objectField(value, "property_internal_keys", path: path)
            let values = try Self.objectField(value, "properties", path: path)
            for spelling in legend.keys.sorted() {
                guard let identity = legend[spelling]?.string, !identity.isEmpty else {
                    throw AnyHeartSpaceArchiveError.missingIdentity(path + "/property_internal_keys/" + spelling)
                }
                if values[spelling] == nil {
                    issues.append(.init(code: .sourceMetadataMappingRequired,
                        path: path + "/property_internal_keys/" + spelling, identity: identity))
                }
            }
            for spelling in values.keys.sorted() {
                let key: String?
                if let explicit = legend[spelling] {
                    guard let identity = explicit.string, !identity.isEmpty else {
                        throw AnyHeartSpaceArchiveError.missingIdentity(path + "/property_internal_keys/" + spelling)
                    }
                    key = identity
                } else {
                    let candidates = bySpelling[spelling] ?? []
                    key = candidates.count == 1 ? candidates.first?.internalKey : nil
                }
                if let key, byKey[key] != nil {
                    propertyKeys[spelling] = key
                    issues.append(.init(code: .nativeSchemaMappingRequired, path: path + "/properties/" + spelling, identity: key))
                } else { issues.append(.init(code: .unresolvedProperty, path: path + "/properties/" + spelling, identity: key)) }
            }
            let blocks = try Self.blocks(value, path: path)
            guard blocks.count <= Self.maximumBlockCount - totalBlocks else { throw AnyHeartSpaceArchiveError.limit }
            totalBlocks += blocks.count
            for block in blocks {
                let location = path + "/blocks/" + String(block.order)
                if !["paragraph", "heading_1", "heading_2", "heading_3", "quote", "code",
                     "bulleted_list_item", "numbered_list_item", "checkbox"].contains(block.type) {
                    issues.append(.init(code: .unsupportedBlockType, path: location, identity: block.sourceID))
                }
                if let text = block.native["text"]?.string, !text.isEmpty, block.type != "code" {
                    issues.append(.init(code: .inlineConversionRequired, path: location + "/text", identity: block.sourceID))
                }
                if !Set(block.native.object!.keys).subtracting(["id", "type", "indent", "text"]).isEmpty {
                    issues.append(.init(code: .sourceMetadataMappingRequired, path: location, identity: block.sourceID))
                }
            }
            let known: Set<String> = ["$schema", "formatVersion", "id", "kind", "type", "type_internal_key",
                "properties", "property_internal_keys", "blocks"]
            for key in value.object!.keys.sorted() where !known.contains(key) {
                issues.append(.init(code: .unknownEnvelopeField, path: path + "/" + key, identity: id))
            }
            objects.append(.init(sourceID: id, path: path, kind: kind, typeInternalKey: typeKey,
                native: value, blocks: blocks, propertyInternalKeys: propertyKeys))
        }
        let objectByID = Dictionary(uniqueKeysWithValues: objects.map { ($0.sourceID, $0) })
        for id in filePaths.keys.sorted() {
            let path = filePaths[id]!
            guard let object = objectByID[id], ["file_object", "file"].contains(object.kind) else {
                throw AnyHeartSpaceArchiveError.malformed(indexPath + "/manifest/files/" + id)
            }
            issues.append(.init(code: .nativeFileImportRequired, path: path, identity: id))
        }
        for object in objects where ["file_object", "file"].contains(object.kind) && filePaths[object.sourceID] == nil {
            // A remote-only AnyBlock bundle is a valid source projection.
            // Retain its opaque recovery metadata, without treating a CID or
            // remote encryption material as proof that bytes were recovered.
            if let remote = object.native["file_remote"] {
                guard remote.string != nil else {
                    throw AnyHeartSpaceArchiveError.malformed(object.path + "/file_remote")
                }
                issues.append(.init(code: .remoteFileRecoveryRequired,
                    path: object.path + "/file_remote", identity: object.sourceID))
            } else {
                issues.append(.init(code: .missingFileBytes, path: object.path, identity: object.sourceID))
            }
            issues.append(.init(code: .nativeFileImportRequired, path: object.path, identity: object.sourceID))
        }
        if dictionaryPath == nil && objects.contains(where: { !($0.native["properties"]?.object ?? [:]).isEmpty }) {
            issues.append(.init(code: .unresolvedProperty, path: indexPath + "/manifest/properties", identity: nil))
        }
        for key in index.object!.keys.sorted() where !["$schema", "formatVersion", "manifest", "unresolved"].contains(key) {
            issues.append(.init(code: .sourceMetadataMappingRequired, path: indexPath + "/" + key, identity: sourceSpaceID))
        }
        let hashes = byPath.mapValues(AnyContentDigest.sha256)
        let material = (["pinkha-heart-space-archive/v1", sourceSpaceID] + byPath.keys.sorted().flatMap {
            [$0, String(byPath[$0]!.count), hashes[$0]!]
        }).map { "\($0.utf8.count):\($0)" }.joined(separator: "|")
        self.sourceSpaceID = sourceSpaceID; self.index = index; self.objects = objects
        self.properties = properties; self.filePathsByObjectID = filePaths
        self.originalEntries = entries.sorted { $0.path < $1.path }; self.entrySHA256 = hashes
        self.contentSHA256 = AnyContentDigest.sha256(Data(material.utf8))
        self.issues = issues.sorted {
            ($0.path, $0.code.rawValue, $0.identity ?? "") < ($1.path, $1.code.rawValue, $1.identity ?? "")
        }
    }

    private static func validatePath(_ path: String) throws {
        let components = path.split(separator: "/", omittingEmptySubsequences: false)
        guard !path.isEmpty, path.utf8.count <= 4096, !path.contains("\\"), !path.contains(":"),
              path.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }),
              components.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." && !$0.hasSuffix(".") && !$0.hasSuffix(" ") }) else {
            throw AnyHeartSpaceArchiveError.unsafePath(path)
        }
    }

    private static func json(_ bytes: Data) throws -> AnyJSON {
        guard !bytes.isEmpty, bytes.count <= maximumJSONBytes else { throw AnyHeartSpaceArchiveError.limit }
        // Detect duplicates before Foundation collapses keys, then reject
        // numeric loss while retaining the original bytes independently.
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        let value = try JSONDecoder().decode(AnyJSON.self, from: bytes)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: JSONEncoder().encode(value))
        return value
    }

    private static func version(_ value: AnyJSON, path: String) throws {
        guard value["formatVersion"]?.string == "2.0" else { throw AnyHeartSpaceArchiveError.unsupportedVersion(path) }
    }

    private static func objectField(_ value: AnyJSON, _ key: String, path: String) throws -> [String: AnyJSON] {
        guard let field = value[key] else { return [:] }
        guard let object = field.object else { throw AnyHeartSpaceArchiveError.malformed(path + "/" + key) }
        return object
    }

    private static func isEmptyContainer(_ value: AnyJSON) -> Bool {
        if let array = value.array { return array.isEmpty }
        if let object = value.object { return object.isEmpty }
        return false
    }

    private static func blocks(_ value: AnyJSON, path: String) throws -> [Block] {
        guard let field = value["blocks"] else { return [] }
        guard let values = field.array, values.count <= maximumBlockCount else {
            throw AnyHeartSpaceArchiveError.malformed(path + "/blocks")
        }
        var identities = Set<String>(), parents: [String] = [], result: [Block] = []
        for (order, block) in values.enumerated() {
            let location = path + "/blocks/" + String(order)
            guard block.object != nil, let id = block["id"]?.string, (1...64).contains(id.utf8.count),
                  id.utf8.allSatisfy({ (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || $0 == 95 || $0 == 45 }),
                  let type = block["type"]?.string, !type.isEmpty else { throw AnyHeartSpaceArchiveError.missingIdentity(location) }
            guard identities.insert(id).inserted else { throw AnyHeartSpaceArchiveError.duplicateIdentity(location) }
            let indent: Int
            if let field = block["indent"] {
                guard let value = field.integer, (0...32).contains(value) else { throw AnyHeartSpaceArchiveError.invalidHierarchy(location) }
                indent = Int(value)
            } else { indent = 0 }
            guard indent <= parents.count, block["children"] == nil else { throw AnyHeartSpaceArchiveError.invalidHierarchy(location) }
            let parent = indent == 0 ? nil : parents[indent - 1]
            parents = Array(parents.prefix(indent)); parents.append(id)
            result.append(.init(sourceID: id, type: type, parentSourceID: parent, order: order, native: block))
        }
        return result
    }
}
