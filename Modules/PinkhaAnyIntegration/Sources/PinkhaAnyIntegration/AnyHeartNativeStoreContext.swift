import Foundation
import PinkhaAnyEngine

public enum AnyHeartNativeStoreContextError: Error, Equatable, Sendable {
    case invalidWitness, invalidBinding, inconsistentInventory, limit
}

/// Classifies only two closed native storage concerns. Their original bytes
/// stay in the bound private witness: Heart's local Space-created flag and an
/// empty, natively derived default key-value store. This is not user Collection
/// migration, native session authority, history validation or permission to write.
public struct AnyHeartNativeStoreContext: Sendable {
    public enum Kind: String, Sendable {
        case clientSpaceLifecycle
        case emptyDefaultKeyValue
    }
    public struct Collection: Sendable {
        public let name: String
        public let kind: Kind
        public let rowCount: Int
        public let encodedValueBytes: Int
        public let sourceSpaceCreated: Bool?
        public let sourceRowSHA256: String?
    }

    /// Exact native head identities, including retained settings/tombstones,
    /// ACL and the separately derived default KV head. This is a census of
    /// original source data, not semantic admission or an ACL translation.
    public struct HeadCensus: Sendable {
        public let sourceHeadIDs: [String]
        public let nativeACLID: String
        public let capturedACLRowCount: Int
        public let defaultKeyValueID: String?
    }

    public let headCensus: HeadCensus?
    public let sourceAccountID: String
    public let sourceSpaceID: String
    public let manifestSHA256: String
    public let sourceWitnessSHA256: String
    public let classifiedCollections: [Collection]
    public let unmappedCollectionNames: [String]
    public var permitsDestinationWrites: Bool { false }

    public func classification(named name: String) -> Collection? {
        classifiedCollections.first { Data($0.name.utf8) == Data(name.utf8) }
    }

    public init(bundle: AnyHeartNativeSpaceBundle, sourceRows: Data) throws {
        try self.init(sourceAccountID: bundle.sourceAccountID, sourceSpaceID: bundle.sourceSpaceID,
            manifest: bundle.rawManifest, manifestSHA256: bundle.manifestSHA256, sourceRows: sourceRows)
    }

    /// The bundle reader calls this only after checking every original member.
    /// Detached component controls cannot manufacture a current native lease.
    init(sourceAccountID: String, sourceSpaceID: String, manifest: AnyJSON,
         manifestSHA256: String, sourceRows: Data) throws {
        guard !sourceAccountID.isEmpty, !sourceSpaceID.isEmpty, sourceSpaceID.utf8.count <= 4096,
              sourceRows.count <= 512 * 1024 * 1024 else { throw AnyHeartNativeStoreContextError.limit }
        let digest = AnyContentDigest.sha256(sourceRows)
        guard manifest["Contract"] == .string("pinkha-native-whole-source-bundle-v1"),
              let receipt = manifest["Receipt"], let native = receipt["Source"]?["source"]?["native"],
              let inventory = receipt["Inventory"],
              receipt["Source"]?["accountSHA256"] == .string(AnyContentDigest.sha256(Data(sourceAccountID.utf8))),
              native["Version"] == .string("native-localstore-witness-v1"),
              native["Encoding"] == .string("anyenc-v1.0.3-decoded-value-roundtrip-v1"),
              native["Authority"] == .string("heart-owned-local-store-v1"),
              native["SpaceSHA256"] == .string(AnyContentDigest.sha256(Data(sourceSpaceID.utf8))),
              native["WitnessSHA256"] == .string(digest),
              inventory["SourceWitnessSHA256"] == .string(digest),
              manifest["SourceRows"]?["Path"] == .string("native-source-rows.witness"),
              manifest["SourceRows"]?["SHA256"] == .string(digest),
              manifest["SourceRows"]?["Bytes"] == .integer(Int64(sourceRows.count)),
              let nativeCoverage = native["CollectionCoverage"]?.array,
              let retained = manifest["RetainedOtherCollections"]?.array,
              let aclHash = receipt["Source"]?["source"]?["aclIdSHA256"]?.string,
              Self.isDigest(aclHash), Self.isDigest(manifestSHA256) else {
            throw AnyHeartNativeStoreContextError.invalidBinding
        }
        var reader = Framed(sourceRows)
        guard try reader.bytes(maximum: 128) == Data("pinkha-localstore-witness-v1".utf8),
              try reader.bytes(maximum: 128) == Data("anyenc-v1.0.3-decoded-value-roundtrip-v1".utf8),
              try reader.bytes(maximum: 128) == Data("heart-owned-local-store-v1".utf8) else {
            throw AnyHeartNativeStoreContextError.invalidWitness
        }
        let nonce = try reader.bytes(maximum: 32)
        guard nonce.count == 32, native["OwnerSHA256"] == .string(AnyContentDigest.sha256(nonce)),
              try reader.bytes(maximum: 4096) == Data(sourceSpaceID.utf8) else {
            throw AnyHeartNativeStoreContextError.invalidBinding
        }
        let generation = try reader.number()
        guard generation <= UInt64(Int64.max),
              native["Generation"] == .integer(Int64(generation)),
              inventory["Generation"] == .integer(Int64(generation)) else {
            throw AnyHeartNativeStoreContextError.invalidBinding
        }
        let count = try reader.number()
        guard count <= 100_000, native["Collections"] == .integer(Int64(count)),
              nativeCoverage.count == Int(count) else {
            throw AnyHeartNativeStoreContextError.inconsistentInventory
        }
        struct Observed {
            let name: String
            let count: Int
            let bytes: Int
            let firstID: Data?
            let firstValue: Data?
        }
        var observed: [Data: Observed] = [:]
        var previousName: Data?, languageNames = Set<String>()
        var totalRows = 0, totalBytes = 0
        var nativeHeadIDs: [String] = [], nativeHeadStrings = Set<String>()
        for index in 0..<Int(count) {
            let rawName = try reader.bytes(maximum: 4096)
            guard let name = String(data: rawName, encoding: .utf8), !name.isEmpty,
                  Data(name.utf8) == rawName, languageNames.insert(name).inserted,
                  previousName.map({ $0.lexicographicallyPrecedes(rawName) }) ?? true else {
                throw AnyHeartNativeStoreContextError.invalidWitness
            }
            previousName = rawName
            let rawCount = try reader.number()
            guard rawCount <= 10_000_000, totalRows <= 10_000_000 - Int(rawCount) else {
                throw AnyHeartNativeStoreContextError.limit
            }
            let rowCount = Int(rawCount)
            if name == "heads", rowCount > 100_002 { throw AnyHeartNativeStoreContextError.limit }
            var previousID: Range<Int>?, byteCount = 0, firstID: Data?, firstValue: Data?
            for row in 0..<rowCount {
                let id = try reader.field(maximum: 16 * 1024 * 1024)
                let value = try reader.field(maximum: 512 * 1024 * 1024)
                guard !id.isEmpty,
                      previousID.map({ sourceRows[$0].lexicographicallyPrecedes(sourceRows[id]) }) ?? true else {
                    throw AnyHeartNativeStoreContextError.invalidWitness
                }
                previousID = id
                byteCount += value.count
                if name == "heads" {
                    let originalID = sourceRows[id]
                    guard originalID.count >= 3, originalID.count <= 4098,
                          originalID.first == 3, originalID.last == 0 else {
                        throw AnyHeartNativeStoreContextError.invalidWitness
                    }
                    let rawID = originalID.dropFirst().dropLast()
                    guard !rawID.contains(0), let decoded = String(data: rawID, encoding: .utf8),
                          !decoded.isEmpty, Data(decoded.utf8) == rawID,
                          nativeHeadStrings.insert(decoded).inserted else {
                        throw AnyHeartNativeStoreContextError.invalidWitness
                    }
                    nativeHeadIDs.append(decoded)
                }
                // Inspect only the one tiny closed lifecycle row. Every other
                // payload remains an unmodified slice of the private witness.
                if name == "_client", row == 0, id.count <= 128, value.count <= 256 {
                    firstID = Data(sourceRows[id]); firstValue = Data(sourceRows[value])
                }
            }
            let coverage = nativeCoverage[index]
            guard let fields = coverage.object,
                  Set(fields.keys) == ["NameSHA256", "Rows", "EncodedValueBytes", "UnresolvedCollection"],
                  coverage["NameSHA256"] == .string(AnyContentDigest.sha256(rawName)),
                  coverage["Rows"] == .integer(Int64(rowCount)),
                  coverage["EncodedValueBytes"] == .integer(Int64(byteCount)),
                  coverage["UnresolvedCollection"]?.bool != nil else {
                throw AnyHeartNativeStoreContextError.inconsistentInventory
            }
            observed[rawName] = Observed(name: name, count: rowCount, bytes: byteCount,
                                         firstID: firstID, firstValue: firstValue)
            totalRows += rowCount; totalBytes += byteCount
        }
        guard reader.isAtEnd, native["Rows"] == .integer(Int64(totalRows)),
              native["EncodedValueBytes"] == .integer(Int64(totalBytes)),
              inventory["OtherCollections"] == .integer(Int64(retained.count)) else {
            throw AnyHeartNativeStoreContextError.inconsistentInventory
        }
        let expectedOthers = Set(observed.keys.filter { name in
            ![Data("state".utf8), Data("heads".utf8), Data("changes".utf8)].contains(name) &&
                AnyContentDigest.sha256(name) != aclHash
        })
        let defaultKeyValueID = try Self.defaultKeyValueCollectionID(spaceID: sourceSpaceID)
        var retainedNames = Set<Data>(), retainedStrings = Set<String>(), retainedRows: Int64 = 0
        var classified: [Collection] = [], unmapped: [String] = []
        for value in retained {
            guard let fields = value.object, Set(fields.keys) == ["Name", "Rows", "Bytes"],
                  let name = value["Name"]?.string, let row = observed[Data(name.utf8)],
                  retainedNames.insert(Data(name.utf8)).inserted, retainedStrings.insert(name).inserted,
                  value["Rows"] == .integer(Int64(row.count)), value["Bytes"] == .integer(Int64(row.bytes)) else {
                throw AnyHeartNativeStoreContextError.inconsistentInventory
            }
            retainedRows += Int64(row.count)
            if name == "_client", row.count == 1,
               row.firstID == Self.clientRowID, let original = row.firstValue,
               let created = Self.clientFlag(original) {
                classified.append(.init(name: name, kind: .clientSpaceLifecycle, rowCount: row.count,
                    encodedValueBytes: row.bytes, sourceSpaceCreated: created,
                    sourceRowSHA256: AnyContentDigest.sha256(original)))
            } else if Data(name.utf8) == Data(defaultKeyValueID.utf8), row.count == 0, row.bytes == 0,
                      inventory["KeyValueStores"] == .integer(1), inventory["KeyValueRows"] == .integer(0) {
                classified.append(.init(name: name, kind: .emptyDefaultKeyValue, rowCount: 0,
                    encodedValueBytes: 0, sourceSpaceCreated: nil, sourceRowSHA256: nil))
            } else {
                unmapped.append(name)
            }
        }
        guard retainedNames == expectedOthers,
              inventory["OtherCollectionRows"] == .integer(retainedRows) else {
            throw AnyHeartNativeStoreContextError.inconsistentInventory
        }
        // Tiny detached classification controls may omit the tree inventory.
        // A complete captured bundle always has Trees; its head census must
        // join the exact original witness, never only the decoded snapshots.
        var census: HeadCensus?
        if let trees = manifest["Trees"]?.array {
            let aclCollections = observed.values.filter {
                AnyContentDigest.sha256(Data($0.name.utf8)) == aclHash
            }
            guard trees.count <= 100_000, aclCollections.count == 1,
                  let acl = aclCollections.first, acl.count > 0,
                  inventory["Version"] == .string("native-tree-identity-inventory-v2"),
                  inventory["AllHeadRowsAccounted"] == .bool(true),
                  receipt["AllNativeHeadRowsAccounted"] == .bool(true),
                  inventory["Trees"] == .integer(Int64(trees.count)),
                  let keyValueStores = inventory["KeyValueStores"]?.integer,
                  (0...1).contains(keyValueStores),
                  let keyValueRows = inventory["KeyValueRows"]?.integer, keyValueRows >= 0,
                  observed[Data("heads".utf8)]?.count == nativeHeadIDs.count else {
                throw AnyHeartNativeStoreContextError.inconsistentInventory
            }
            var expected = Set<Data>(), identities = Set<String>()
            for tree in trees {
                guard let id = tree["ObjectID"]?.string, !id.isEmpty, id.utf8.count <= 4096,
                      !id.utf8.contains(0), expected.insert(Data(id.utf8)).inserted,
                      identities.insert(id).inserted else {
                    throw AnyHeartNativeStoreContextError.inconsistentInventory
                }
            }
            guard expected.insert(Data(acl.name.utf8)).inserted,
                  identities.insert(acl.name).inserted else {
                throw AnyHeartNativeStoreContextError.inconsistentInventory
            }
            var keyValueID: String?
            if keyValueStores == 1 {
                guard let row = observed[Data(defaultKeyValueID.utf8)],
                      row.count == keyValueRows,
                      expected.insert(Data(defaultKeyValueID.utf8)).inserted,
                      identities.insert(defaultKeyValueID).inserted else {
                    throw AnyHeartNativeStoreContextError.inconsistentInventory
                }
                keyValueID = defaultKeyValueID
            } else if keyValueRows != 0 || observed[Data(defaultKeyValueID.utf8)] != nil {
                throw AnyHeartNativeStoreContextError.inconsistentInventory
            }
            guard expected == Set(nativeHeadIDs.map { Data($0.utf8) }),
                  expected.count == nativeHeadIDs.count else {
                throw AnyHeartNativeStoreContextError.inconsistentInventory
            }
            census = .init(sourceHeadIDs: nativeHeadIDs, nativeACLID: acl.name,
                capturedACLRowCount: acl.count, defaultKeyValueID: keyValueID)
        }
        headCensus = census
        self.sourceAccountID = sourceAccountID; self.sourceSpaceID = sourceSpaceID
        self.manifestSHA256 = manifestSHA256; sourceWitnessSHA256 = digest
        classifiedCollections = classified; unmappedCollectionNames = unmapped
    }

    private static let clientRowID = Data([3]) + Data("space".utf8) + Data([0])
    private static func clientFlag(_ original: Data) -> Bool? {
        // Original anystorage.clientStorage.modifyState creates id first, then
        // created. Type codes and EOS are pinned to any-store v1.0.3 anyenc.
        let prefix = Data([7]) + Data("id".utf8) + Data([0]) + clientRowID +
            Data("created".utf8) + Data([0])
        if original == prefix + Data([4, 0]) { return false }
        if original == prefix + Data([5, 0]) { return true }
        return nil
    }

    /// Original StorageHeader{spaceId:1, storageName:2} protobuf -> SHA2-256 ->
    /// CIDv1 DAG-CBOR -> lower-case unpadded base32. No caller-selected store ID.
    public static func defaultKeyValueCollectionID(spaceID: String) throws -> String {
        let space = Data(spaceID.utf8)
        guard !space.isEmpty, space.count <= 4096 else { throw AnyHeartNativeStoreContextError.limit }
        var protobuf = Data([0x0a])
        var count = UInt64(space.count)
        while count >= 128 { protobuf.append(UInt8(count & 127) | 128); count >>= 7 }
        protobuf.append(UInt8(count)); protobuf.append(space)
        protobuf.append(contentsOf: [0x12, 7]); protobuf.append(Data("default".utf8))
        let hex = Array(AnyContentDigest.sha256(protobuf).utf8)
        func digit(_ byte: UInt8) -> UInt8 { byte >= 97 ? byte - 87 : byte - 48 }
        var cid = Data([1, 0x71, 0x12, 0x20])
        for i in stride(from: 0, to: hex.count, by: 2) { cid.append(digit(hex[i]) << 4 | digit(hex[i + 1])) }
        let alphabet = Array("abcdefghijklmnopqrstuvwxyz234567".utf8)
        var output = Data([98]), bits = 0, buffer: UInt32 = 0
        for byte in cid {
            buffer = (buffer << 8) | UInt32(byte); bits += 8
            while bits >= 5 {
                bits -= 5; output.append(alphabet[Int((buffer >> UInt32(bits)) & 31)])
            }
            buffer &= (1 << UInt32(bits)) - 1
        }
        if bits > 0 { output.append(alphabet[Int((buffer << UInt32(5 - bits)) & 31)]) }
        return String(decoding: output, as: UTF8.self)
    }

    private static func isDigest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }

    private struct Framed {
        let data: Data
        var offset = 0
        init(_ bytes: Data) { data = bytes; offset = bytes.startIndex }
        var isAtEnd: Bool { offset == data.endIndex }
        mutating func field(maximum: Int) throws -> Range<Int> {
            guard data.endIndex - offset >= 8 else { throw AnyHeartNativeStoreContextError.invalidWitness }
            var size: UInt64 = 0
            for byte in data[offset..<(offset + 8)] { size = (size << 8) | UInt64(byte) }
            offset += 8
            guard size <= UInt64(maximum), size <= UInt64(data.endIndex - offset) else {
                throw AnyHeartNativeStoreContextError.invalidWitness
            }
            let range = offset..<(offset + Int(size)); offset = range.upperBound
            return range
        }
        mutating func bytes(maximum: Int) throws -> Data {
            let range = try field(maximum: maximum)
            return Data(data[range])
        }
        mutating func number() throws -> UInt64 {
            let range = try field(maximum: 8)
            guard range.count == 8 else { throw AnyHeartNativeStoreContextError.invalidWitness }
            return data[range].reduce(0) { ($0 << 8) | UInt64($1) }
        }
    }
}
