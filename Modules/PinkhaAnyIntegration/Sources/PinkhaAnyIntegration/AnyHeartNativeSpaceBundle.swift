import Foundation
import PinkhaAnyEngine

public enum AnyHeartNativeSpaceBundleError: Error, Equatable, Sendable {
    case invalidManifest, invalidMember(String), identityCollision, inconsistentInventory, limit
}

/// Reads the captured bundle's complete declared membership and detached views.
/// It verifies every original member, including opaque rows and file variants.
/// Source authority and semantic coverage remain separate from byte integrity.
public struct AnyHeartNativeSpaceBundle: Sendable {
    public struct Member: Equatable, Sendable {
        public let path: String
        public let sha256: String
        public let byteCount: Int
    }
    public struct Tree: Sendable {
        public let objectID: String
        public let nativeType: Int64
        public let status: String
        public let raw: AnyJSON
    }
    public struct FileVariant: Sendable {
        public let fileID: String
        public let variantPath: String
        public let contentID: String
        public let metadataID: String
        public let name: String
        public let mimeType: String
        public let isNativeOriginal: Bool
        public let payload: Member
        public let metadata: Member
        public let raw: AnyJSON
    }
    public struct Issue: Equatable, Sendable {
        public let code: String
        public let sourceID: String?
        public let field: String
    }

    public let sourceAccountID: String
    public let sourceSpaceID: String
    public let manifestSHA256: String
    public let sourceWitnessSHA256: String
    public let manifestBytes: Data
    public let rawManifest: AnyJSON
    public let receipt: AnyJSON
    public let sourceRows: Member
    public let trees: [Tree]
    public let objects: [AnyHeartNativeSnapshotView]
    public let fileVariants: [FileVariant]
    public let verifiedMembers: [Member]
    public let fileReferences: [AnyJSON]
    public let sourceGaps: [AnyJSON]
    public let resolverUnmapped: [AnyJSON]
    public let bundledDefinitionsUsed: [String]
    public let retainedOtherCollections: [AnyJSON]
    public let issues: [Issue]

    /// The provider reads the exact named member from the captured private
    /// directory. Large payload Data may be memory mapped; it is not retained
    /// by this reader. Every returned byte sequence is independently checked.
    public init(manifest: Data, sourceAccountID: String, sourceSpaceID: String,
                memberData: (Member) throws -> Data) throws {
        guard manifest.count <= 16 * 1024 * 1024,
              Self.validID(sourceAccountID), Self.validID(sourceSpaceID) else {
            throw AnyHeartNativeSpaceBundleError.limit
        }
        let root = try JSONDecoder().decode(AnyJSON.self, from: manifest)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: manifest, encoded: encoder.encode(root))
        guard let fields = root.object,
              root["Contract"]?.string == "pinkha-native-whole-source-bundle-v1",
              let receipt = root["Receipt"], receipt.object != nil,
              receipt["Version"]?.string == "loaded-account-native-space-source-v1",
              receipt["Inventory"]?["SpaceSHA256"]?.string == AnyContentDigest.sha256(Data(sourceSpaceID.utf8)),
              let witness = receipt["Inventory"]?["SourceWitnessSHA256"]?.string,
              Self.validSHA(witness) else { throw AnyHeartNativeSpaceBundleError.invalidManifest }
        // These are captured identities, not reusable session authority. The
        // executor separately rechecks the current source session/checkpoint.
        let accountHash = AnyContentDigest.sha256(Data(sourceAccountID.utf8))
        let spaceHash = AnyContentDigest.sha256(Data(sourceSpaceID.utf8))
        guard let account = receipt["Source"],
              account["version"]?.string == "loaded-account-native-witness-v1",
              account["accountAuthority"]?.string == "held-application-account-directory-lease-v1",
              account["sessionAuthority"]?.string == "validated-native-full-unassociated-session-v1",
              account["accountSHA256"]?.string == accountHash,
              let directoryHash = account["accountDirectorySHA256"]?.string, Self.validSHA(directoryHash),
              account["accountSessionAuthorizedAtCapture"]?.bool == true,
              account["nativeIdentityCensusRequired"]?.bool == true,
              let source = account["source"],
              source["version"]?.string == "loaded-native-acl-witness-v1",
              source["accountSHA256"]?.string == accountHash,
              source["spaceSHA256"]?.string == spaceHash,
              source["alreadyLoaded"]?.bool == true,
              source["aclReadAuthorizedAtCapture"]?.bool == true,
              let aclIDHash = source["aclIdSHA256"]?.string, Self.validSHA(aclIDHash),
              let aclHeadHash = source["aclHeadSHA256"]?.string, Self.validSHA(aclHeadHash),
              receipt["Inventory"]?["ACLHeadSHA256"]?.string == aclHeadHash,
              let native = source["native"],
              native["Version"]?.string == "native-localstore-witness-v1",
              native["SpaceSHA256"]?.string == spaceHash,
              native["WitnessSHA256"]?.string == witness,
              native["LocalDecodedRowsComplete"]?.bool == true,
              let generation = native["Generation"]?.integer, generation >= 0,
              receipt["Inventory"]?["Generation"]?.integer == generation else {
            throw AnyHeartNativeSpaceBundleError.invalidManifest
        }
        for flag in ["AccountSessionAuthorizedAtFinalCapture", "AllNativeHeadRowsAccounted",
                     "CapturedSnapshotsBoundToUnchangedCheckpoint",
                     "OriginalNativeHistoryRowsRetained"] {
            guard receipt[flag]?.bool == true else { throw AnyHeartNativeSpaceBundleError.invalidManifest }
        }
        let known: Set<String> = ["Contract", "Receipt", "SourceRows", "Trees", "Objects", "Files",
            "FileReferences", "Gaps", "ResolverUnmapped", "BundledDefinitionsUsed", "RetainedOtherCollections"]
        var issues = Set(fields.keys).subtracting(known).sorted().map {
            Issue(code: "unknown-manifest-field", sourceID: nil, field: $0)
        }
        var members: [Member] = [], paths = Set<String>(), totalVerifiedBytes = 0
        func verify(_ value: AnyJSON?, expectedPath: String, maximum: Int) throws -> (Member, Data) {
            guard let value, let row = value.object, Set(row.keys) == ["Path", "SHA256", "Bytes"],
                  value["Path"]?.string == expectedPath,
                  let hash = value["SHA256"]?.string, Self.validSHA(hash),
                  let count = value["Bytes"]?.integer, count >= 0, count <= Int64(maximum),
                  Self.validPath(expectedPath), paths.insert(expectedPath).inserted else {
                throw AnyHeartNativeSpaceBundleError.invalidMember(expectedPath)
            }
            guard count <= Int64(3 * 1024 * 1024 * 1024 - totalVerifiedBytes) else {
                throw AnyHeartNativeSpaceBundleError.limit
            }
            let member = Member(path: expectedPath, sha256: hash, byteCount: Int(count))
            let bytes = try memberData(member)
            guard bytes.count == member.byteCount, AnyContentDigest.sha256(bytes) == member.sha256 else {
                throw AnyHeartNativeSpaceBundleError.invalidMember(expectedPath)
            }
            totalVerifiedBytes += bytes.count; members.append(member)
            return (member, bytes)
        }
        let rows = try verify(root["SourceRows"], expectedPath: "native-source-rows.witness", maximum: 512 * 1024 * 1024).0
        let rawTrees = try Self.array(root["Trees"], maximum: 100_000)
        var treeIDs = Set<Data>(), treeStrings = Set<String>()
        let trees = try rawTrees.map { value -> Tree in
            guard let id = value["ObjectID"]?.string, Self.validID(id),
                  treeIDs.insert(Data(id.utf8)).inserted, treeStrings.insert(id).inserted,
                  let kind = value["NativeType"]?.integer, kind >= 0, kind <= Int64(Int32.max),
                  let status = value["Status"]?.string, !status.isEmpty else {
                throw AnyHeartNativeSpaceBundleError.identityCollision
            }
            if !["captured-current-snapshot", "native-tombstone-retained", "space-settings-retained"].contains(status) {
                issues.append(.init(code: "native-tree-semantic-gap", sourceID: id, field: status))
            }
            return .init(objectID: id, nativeType: kind, status: status, raw: value)
        }
        let treesByID = Dictionary(uniqueKeysWithValues: trees.map { (Data($0.objectID.utf8), $0) })
        let rawObjects = try Self.array(root["Objects"], maximum: 100_000)
        guard let resolverBound = receipt["IndexResolverSnapshotBound"]?.bool,
              rawObjects.isEmpty || resolverBound else { throw AnyHeartNativeSpaceBundleError.invalidManifest }
        let objectReceipts = try Self.array(receipt["Objects"], maximum: 100_000)
        var receiptsByHash: [String: AnyJSON] = [:]
        for row in objectReceipts {
            guard let hash = row["ObjectSHA256"]?.string, Self.validSHA(hash), receiptsByHash[hash] == nil else {
                throw AnyHeartNativeSpaceBundleError.inconsistentInventory
            }
            receiptsByHash[hash] = row
        }
        var objectIDs = Set<Data>(), objects: [AnyHeartNativeSnapshotView] = []
        var snapshotBytes = 0, jsonBytes = 0
        for raw in rawObjects {
            guard let id = raw["ObjectID"]?.string, Self.validID(id), objectIDs.insert(Data(id.utf8)).inserted,
                  let tree = treesByID[Data(id.utf8)],
                  ["captured-current-snapshot", "captured-store-backed-object-with-external-state"].contains(tree.status),
                  let nativeType = raw["NativeType"]?.integer, nativeType == tree.nativeType,
                  let key = raw["UniqueKey"]?.string else { throw AnyHeartNativeSpaceBundleError.inconsistentInventory }
            let idHash = AnyContentDigest.sha256(Data(id.utf8))
            let pb = try verify(raw["Snapshot"], expectedPath: "snapshot-" + idHash + ".pb", maximum: 8 * 1024 * 1024)
            let json = try verify(raw["NativeJSONView"], expectedPath: "snapshot-" + idHash + ".json", maximum: 32 * 1024 * 1024)
            snapshotBytes += pb.0.byteCount; jsonBytes += json.0.byteCount
            guard snapshotBytes <= 256 * 1024 * 1024, jsonBytes <= 256 * 1024 * 1024 else {
                throw AnyHeartNativeSpaceBundleError.limit
            }
            let view = try AnyHeartNativeSnapshotView(jsonView: json.1, snapshotBytes: pb.1,
                                                      sourceSpaceID: sourceSpaceID, sourceObjectID: id)
            guard view.nativeType == nativeType, Data(view.uniqueKey.utf8) == Data(key.utf8),
                  let nativeReceipt = receiptsByHash[idHash],
                  nativeReceipt["Version"]?.string == "native-raw-object-snapshot-v1",
                  nativeReceipt["SmartBlockType"]?.integer == nativeType,
                  nativeReceipt["SnapshotSHA256"]?.string == pb.0.sha256,
                  nativeReceipt["SnapshotBytes"]?.integer == Int64(pb.0.byteCount),
                  nativeReceipt["NativeIdentityBoundUnderTreeLock"]?.bool == true else {
                throw AnyHeartNativeSpaceBundleError.inconsistentInventory
            }
            objects.append(view)
            issues.append(contentsOf: view.issues.map {
                .init(code: "native-snapshot-" + $0.kind.rawValue, sourceID: id,
                      field: ($0.blockID.map { $0 + ":" } ?? "") + $0.field)
            })
        }
        let required = Set(trees.filter {
            ["captured-current-snapshot", "captured-store-backed-object-with-external-state"].contains($0.status)
        }.map { Data($0.objectID.utf8) })
        guard required == objectIDs, objectReceipts.count == objects.count else {
            throw AnyHeartNativeSpaceBundleError.inconsistentInventory
        }
        let rawFiles = try Self.array(root["Files"], maximum: 100_000)
        var fileIDs = Set<Data>(), fileStrings = Set<String>(), variants: [FileVariant] = []
        var payloadBytes = 0, metadataBytes = 0
        for file in rawFiles {
            guard let id = file["FileID"]?.string, Self.validID(id),
                  fileIDs.insert(Data(id.utf8)).inserted, fileStrings.insert(id).inserted else {
                throw AnyHeartNativeSpaceBundleError.identityCollision
            }
            let rawVariants = try Self.array(file["Variants"], maximum: 4096)
            guard !rawVariants.isEmpty else { throw AnyHeartNativeSpaceBundleError.inconsistentInventory }
            var variantPaths = Set<Data>(), variantStrings = Set<String>()
            for raw in rawVariants {
                guard let path = raw["Path"]?.string, path.utf8.count <= 4096, !path.contains("\0"),
                      variantPaths.insert(Data(path.utf8)).inserted, variantStrings.insert(path).inserted,
                      let contentID = raw["ContentID"]?.string, Self.validID(contentID),
                      let metadataID = raw["MetadataID"]?.string, Self.validID(metadataID),
                      let name = raw["Name"]?.string, name.utf8.count <= 4096,
                      let mime = raw["MIME"]?.string, mime.utf8.count <= 512,
                      let original = raw["NativeOriginalPath"]?.bool else {
                    throw AnyHeartNativeSpaceBundleError.invalidManifest
                }
                let variantHash = AnyContentDigest.sha256(Data((id + "\0" + path).utf8))
                let meta = try verify(raw["Metadata"], expectedPath: "metadata-" + variantHash + ".pb", maximum: 8 * 1024 * 1024).0
                let payload = try verify(raw["Payload"], expectedPath: AnyContentDigest.sha256(Data(id.utf8)) + "/" + variantHash + ".payload",
                                         maximum: 512 * 1024 * 1024).0
                payloadBytes += payload.byteCount; metadataBytes += meta.byteCount
                variants.append(.init(fileID: id, variantPath: path, contentID: contentID, metadataID: metadataID,
                    name: name, mimeType: mime, isNativeOriginal: original, payload: payload, metadata: meta, raw: raw))
            }
        }
        let references = try Self.array(root["FileReferences"], maximum: 100_000)
        let gaps = try Self.array(root["Gaps"], maximum: 100_000)
        let unmapped = try Self.array(root["ResolverUnmapped"], maximum: 100_000)
        let others = try Self.array(root["RetainedOtherCollections"], maximum: 100_000)
        let definitions = try Self.array(root["BundledDefinitionsUsed"], maximum: 100_000).map { value -> String in
            guard let id = value.string, Self.validID(id) else { throw AnyHeartNativeSpaceBundleError.invalidManifest }
            return id
        }
        let counts = ["NativeTrees": trees.count, "CapturedObjects": objects.count, "CapturedFiles": rawFiles.count,
            "FileReferences": references.count, "UnresolvedEntries": gaps.count, "ClosedResolverUnmapped": unmapped.count,
            "SnapshotBytes": snapshotBytes, "MetadataBytes": metadataBytes, "PlaintextBytes": payloadBytes,
            "Tombstones": trees.filter { $0.status == "native-tombstone-retained" }.count,
            "SettingsTrees": trees.filter { $0.status == "space-settings-retained" }.count,
            "UnsupportedTrees": trees.filter { !["captured-current-snapshot", "native-tombstone-retained", "space-settings-retained"].contains($0.status) }.count]
        for (key, count) in counts {
            guard receipt[key]?.integer == Int64(count) else { throw AnyHeartNativeSpaceBundleError.inconsistentInventory }
        }
        guard receipt["Inventory"]?["Trees"]?.integer == Int64(trees.count) else {
            throw AnyHeartNativeSpaceBundleError.inconsistentInventory
        }
        let allObjects = counts["UnsupportedTrees"] == 0
        let allFiles = allObjects && gaps.isEmpty && unmapped.isEmpty && references.allSatisfy {
            guard let id = $0["FileID"]?.string else { return false }
            return fileIDs.contains(Data(id.utf8))
        }
        guard receipt["AllCurrentObjectsCaptured"]?.bool == allObjects,
              receipt["CurrentFilePayloadCompleteness"]?.bool == allFiles else {
            throw AnyHeartNativeSpaceBundleError.inconsistentInventory
        }
        var otherNames = Set<Data>(), otherStrings = Set<String>(), otherRows: Int64 = 0
        for row in others {
            guard let name = row["Name"]?.string, Self.validID(name),
                  otherNames.insert(Data(name.utf8)).inserted, otherStrings.insert(name).inserted,
                  let rows = row["Rows"]?.integer, rows >= 0, rows <= 10_000_000,
                  let bytes = row["Bytes"]?.integer, bytes >= 0, bytes <= 3 * 1024 * 1024 * 1024 else {
                throw AnyHeartNativeSpaceBundleError.invalidManifest
            }
            otherRows += rows
            if rows > 0 {
                issues.append(.init(code: "retained-collection-requires-semantic-mapping", sourceID: name, field: "RetainedOtherCollections"))
            }
        }
        guard receipt["Inventory"]?["OtherCollections"]?.integer == Int64(others.count),
              receipt["Inventory"]?["OtherCollectionRows"]?.integer == otherRows else {
            throw AnyHeartNativeSpaceBundleError.inconsistentInventory
        }
        for row in gaps {
            issues.append(.init(code: "native-source-gap", sourceID: row["ObjectID"]?.string,
                                field: row["Reason"]?.string ?? "unrecognized-gap"))
        }
        if !unmapped.isEmpty { issues.append(.init(code: "closed-resolver-unmapped", sourceID: nil, field: "ResolverUnmapped")) }
        self.sourceAccountID = sourceAccountID
        self.sourceSpaceID = sourceSpaceID; manifestSHA256 = AnyContentDigest.sha256(manifest)
        sourceWitnessSHA256 = witness; manifestBytes = manifest; rawManifest = root; self.receipt = receipt
        sourceRows = rows; self.trees = trees; self.objects = objects; fileVariants = variants
        verifiedMembers = members; fileReferences = references; sourceGaps = gaps
        resolverUnmapped = unmapped; bundledDefinitionsUsed = definitions; retainedOtherCollections = others
        self.issues = issues
    }

    private static func validSHA(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    private static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 && value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }
    private static func validPath(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 && !value.hasPrefix("/") && !value.contains("\\") && !value.contains("\0") &&
        value.split(separator: "/", omittingEmptySubsequences: false).allSatisfy { !$0.isEmpty && $0 != "." && $0 != ".." }
    }
    private static func array(_ value: AnyJSON?, maximum: Int) throws -> [AnyJSON] {
        guard let value else { throw AnyHeartNativeSpaceBundleError.invalidManifest }
        if value == .null { return [] }
        guard let rows = value.array, rows.count <= maximum else { throw AnyHeartNativeSpaceBundleError.limit }
        return rows
    }
}
