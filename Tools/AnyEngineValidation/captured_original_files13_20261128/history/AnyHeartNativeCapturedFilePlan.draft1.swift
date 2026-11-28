import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyHeartNativeCapturedFilePlanError: Error, Equatable, Sendable {
    case sourceBinding, limit, duplicateIdentity, incompleteReferences
    case unsupportedHead(String, String), invalidVariant(String), ambiguousOwner(String)
    case changedProperty(String, String)
}

/// A closed attachment projection from a verified direct capture. Source file
/// heads, payload IDs and destination owners are different identities. The
/// original file head and its schema remain retained source, not editable
/// destination File-Type objects. This value grants no source or write authority.
public struct AnyHeartNativeCapturedFilePlan: Sendable {
    public static let contract = "pinkha-heart-captured-original-file-attachments-v1"

    public struct Entry: Sendable {
        public let sourceHeadID: String
        public let sourceHeadSnapshotSHA256: String
        public let sourceHeadViewSHA256: String
        public let sourcePayloadID: String
        public let sourceOwnerID: String
        public let ownerSourceKey: String
        public let sourceKey: String
        public let variantPath: String
        public let payloadPath: String
        public let payloadSHA256: String
        public let metadataSHA256: String
        public let size: Int64
        public let name: String
        public let mimeType: String

        public var reference: AnyDestinationReference {
            .mapped(sourceKey: sourceKey, slot: .fileID, encoding: .fileURI)
        }
        public var item: AnyDestinationMigrationItem {
            .init(sourceKey: sourceKey, sourceObjectID: sourceOwnerID,
                operation: .file(owner: .mapped(sourceKey: ownerSourceKey, slot: .objectID, encoding: .rawID),
                    name: name, mime: mimeType, size: size, contentSHA256: payloadSHA256))
        }
    }

    struct Variant: Sendable {
        let fileID: String
        let path: String
        let contentID: String
        let metadataID: String
        let name: String
        let mime: String
        let original: Bool
        let payloadPath: String
        let payloadSHA256: String
        let payloadBytes: Int
        let metadataPath: String
        let metadataSHA256: String
        let metadataBytes: Int
        let raw: AnyJSON
    }
    struct Owner: Sendable {
        let snapshot: AnyHeartNativeSnapshotView
        let sourceKey: String
    }
    private struct Use: Sendable {
        let ownerID: String
        let relationKey: String
        let snapshotSHA256: String
        let viewSHA256: String
        let value: AnyJSON
        let headIDs: [String]
    }
    private struct ReferenceRow: Sendable {
        let owner: String
        let field: String
        let target: String
        let payload: String
        var json: AnyJSON {
            .object(["OwnerObjectID": .string(owner), "Field": .string(field),
                "TargetObjectID": .string(target), "FileID": .string(payload), "LegacyFileID": .bool(false)])
        }
    }

    public let sourceAccountID: String
    public let sourceSpaceID: String
    public let captureManifestSHA256: String
    public let sourceWitnessSHA256: String
    public let catalogSHA256: String
    public let entries: [Entry]
    /// Includes only captured definition objects. Compiled descriptor bytes are
    /// already bound by catalogSHA256; they are not invented native heads.
    public let fileSchemaObjectIDs: [String]
    public let contentSHA256: String
    public var permitsDestinationWrites: Bool { false }
    public var activatesFileType: Bool { false }
    private let uses: [Use]

    public init(bundle: AnyHeartNativeSpaceBundle, catalog: AnyHeartNativeDefinitionCatalog,
                selection: AnyHeartNativeContentSelection) throws {
        try selection.require(catalog)
        let snapshots = Dictionary(uniqueKeysWithValues: bundle.objects.map { (Data($0.sourceObjectID.utf8), $0) })
        let owners = try selection.objects.map { selected -> Owner in
            guard let snapshot = snapshots[Data(selected.sourceObjectID.utf8)],
                  snapshot.snapshotSHA256 == selected.snapshotSHA256,
                  snapshot.viewSHA256 == selected.jsonViewSHA256 else {
                throw AnyHeartNativeCapturedFilePlanError.sourceBinding
            }
            return .init(snapshot: snapshot, sourceKey: AnyHeartNativePageComposition.objectSourceKey(
                spaceID: bundle.sourceSpaceID, objectID: snapshot.sourceObjectID))
        }
        let variants = bundle.fileVariants.map { value in
            Variant(fileID: value.fileID, path: value.variantPath, contentID: value.contentID,
                metadataID: value.metadataID, name: value.name, mime: value.mimeType, original: value.isNativeOriginal,
                payloadPath: value.payload.path, payloadSHA256: value.payload.sha256, payloadBytes: value.payload.byteCount,
                metadataPath: value.metadata.path, metadataSHA256: value.metadata.sha256, metadataBytes: value.metadata.byteCount,
                raw: value.raw)
        }
        try self.init(sourceAccountID: bundle.sourceAccountID, sourceSpaceID: bundle.sourceSpaceID,
            captureManifestSHA256: bundle.manifestSHA256, sourceWitnessSHA256: bundle.sourceWitnessSHA256,
            snapshots: bundle.objects, variants: variants, references: bundle.fileReferences,
            owners: owners, catalog: catalog)
    }

    /// Detached source controls use this pure boundary. The production entry
    /// above accepts only the complete verified bundle and current selection.
    init(sourceAccountID: String, sourceSpaceID: String, captureManifestSHA256: String,
         sourceWitnessSHA256: String, snapshots: [AnyHeartNativeSnapshotView], variants: [Variant],
         references: [AnyJSON], owners: [Owner], catalog: AnyHeartNativeDefinitionCatalog) throws {
        guard Self.same(sourceAccountID, catalog.sourceAccountID), Self.same(sourceSpaceID, catalog.sourceSpaceID),
              captureManifestSHA256 == catalog.captureManifestSHA256,
              sourceWitnessSHA256 == catalog.sourceWitnessSHA256 else {
            throw AnyHeartNativeCapturedFilePlanError.sourceBinding
        }
        guard snapshots.count <= 100_000, variants.count <= 4096, references.count <= 100_000,
              owners.count <= 100_000 else { throw AnyHeartNativeCapturedFilePlanError.limit }
        var byID: [Data: AnyHeartNativeSnapshotView] = [:], names = Set<String>()
        for snapshot in snapshots {
            guard Self.same(snapshot.sourceSpaceID, sourceSpaceID),
                  byID.updateValue(snapshot, forKey: Data(snapshot.sourceObjectID.utf8)) == nil,
                  names.insert(snapshot.sourceObjectID).inserted else {
                throw AnyHeartNativeCapturedFilePlanError.duplicateIdentity
            }
        }
        var ownerByID: [Data: Owner] = [:], ownerNames = Set<String>(), ownerKeys = Set<String>()
        for owner in owners {
            let snapshot = owner.snapshot
            guard let original = byID[Data(snapshot.sourceObjectID.utf8)],
                  original.snapshotSHA256 == snapshot.snapshotSHA256, original.viewSHA256 == snapshot.viewSHA256,
                  snapshot.nativeType == 16, snapshot.objectTypes.count == 1, snapshot.issues.isEmpty,
                  let type = catalog.type(url: snapshot.objectTypes[0]),
                  type.recommendedLayout == 0 || type.recommendedLayout == 11,
                  Self.same(owner.sourceKey, AnyHeartNativePageComposition.objectSourceKey(
                    spaceID: sourceSpaceID, objectID: snapshot.sourceObjectID)),
                  ownerByID.updateValue(owner, forKey: Data(snapshot.sourceObjectID.utf8)) == nil,
                  ownerNames.insert(snapshot.sourceObjectID).inserted, ownerKeys.insert(owner.sourceKey).inserted else {
                throw AnyHeartNativeCapturedFilePlanError.sourceBinding
            }
        }
        var variantByID: [Data: Variant] = [:], payloadNames = Set<String>(), total = 0
        for variant in variants {
            try Self.validate(variant)
            guard variantByID.updateValue(variant, forKey: Data(variant.fileID.utf8)) == nil,
                  payloadNames.insert(variant.fileID).inserted else {
                throw AnyHeartNativeCapturedFilePlanError.invalidVariant(variant.fileID)
            }
            guard variant.payloadBytes <= AnyHeartNativePreservationArchive.maximumBytes - total else {
                throw AnyHeartNativeCapturedFilePlanError.limit
            }
            total += variant.payloadBytes
        }
        var heads: [Data: AnyHeartNativeSnapshotView] = [:], headPayloads: [Data: String] = [:]
        var schemaIDs = Set<Data>(), expected: [ReferenceRow] = []
        for snapshot in snapshots {
            let info = snapshot.rawSnapshot["fileInfo"]
            if snapshot.nativeType != 533 && (info == nil || info == .null || info == .object([:])) {
                continue
            }
            guard snapshot.nativeType == 533,
                  let payload = info?["fileId"]?.string,
                  let variant = variantByID[Data(payload.utf8)] else {
                throw AnyHeartNativeCapturedFilePlanError.unsupportedHead(snapshot.sourceObjectID, "fileInfo")
            }
            let dependencies = try Self.validateHead(snapshot, variant: variant, catalog: catalog)
            guard headPayloads.updateValue(snapshot.sourceObjectID, forKey: Data(payload.utf8)) == nil else {
                throw AnyHeartNativeCapturedFilePlanError.ambiguousOwner(payload)
            }
            heads[Data(snapshot.sourceObjectID.utf8)] = snapshot
            schemaIDs.formUnion(dependencies.map { Data($0.utf8) })
            expected.append(.init(owner: snapshot.sourceObjectID, field: "fileInfo.fileId",
                target: snapshot.sourceObjectID, payload: payload))
            guard let index = snapshot.blocks.firstIndex(where: { Self.same($0.id, "file") }) else {
                throw AnyHeartNativeCapturedFilePlanError.unsupportedHead(snapshot.sourceObjectID, "file block")
            }
            expected.append(.init(owner: snapshot.sourceObjectID, field: "blocks[\(index)](file).file.targetObjectId",
                target: snapshot.sourceObjectID, payload: payload))
        }
        guard heads.count == variants.count else { throw AnyHeartNativeCapturedFilePlanError.incompleteReferences }
        var uses: [Use] = [], referring: [Data: Set<Data>] = [:]
        for owner in owners.sorted(by: { Self.less($0.snapshot.sourceObjectID, $1.snapshot.sourceObjectID) }) {
            let snapshot = owner.snapshot
            for key in snapshot.details.keys.sorted(by: Self.less) {
                guard let relation = catalog.relation(key: key) else {
                    throw AnyHeartNativeCapturedFilePlanError.changedProperty(snapshot.sourceObjectID, key)
                }
                guard relation.format == .file else { continue }
                let value = snapshot.details[key]!
                let rows: [AnyJSON]
                if let scalar = value.string { rows = [.string(scalar)] }
                else if let array = value.array, array.count <= 20_000 { rows = array }
                else { throw AnyHeartNativeCapturedFilePlanError.changedProperty(snapshot.sourceObjectID, key) }
                let headIDs = try rows.map { row -> String in
                    guard let head = row.string, let captured = heads[Data(head.utf8)],
                          Self.same(head, captured.sourceObjectID) else {
                        throw AnyHeartNativeCapturedFilePlanError.changedProperty(snapshot.sourceObjectID, key)
                    }
                    return head
                }
                for (index, head) in headIDs.enumerated() {
                    let payload = heads[Data(head.utf8)]!.rawSnapshot["fileInfo"]!["fileId"]!.string!
                    referring[Data(head.utf8), default: []].insert(Data(snapshot.sourceObjectID.utf8))
                    expected.append(.init(owner: snapshot.sourceObjectID, field: "details.\(key)[\(index)]",
                        target: head, payload: payload))
                }
                uses.append(.init(ownerID: snapshot.sourceObjectID, relationKey: key,
                    snapshotSHA256: snapshot.snapshotSHA256, viewSHA256: snapshot.viewSHA256,
                    value: value, headIDs: headIDs))
            }
        }
        var entries: [Entry] = []
        for head in heads.values.sorted(by: { Self.less($0.sourceObjectID, $1.sourceObjectID) }) {
            let id = Data(head.sourceObjectID.utf8)
            guard let referents = referring[id], referents.count == 1, let ownerID = referents.first,
                  let owner = ownerByID[ownerID],
                  let payload = head.rawSnapshot["fileInfo"]?["fileId"]?.string,
                  let variant = variantByID[Data(payload.utf8)] else {
                throw AnyHeartNativeCapturedFilePlanError.ambiguousOwner(head.sourceObjectID)
            }
            let sourceKey = "heart-captured-file:" + AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
                Self.contract, sourceSpaceID, captureManifestSHA256, head.sourceObjectID,
                payload, variant.path, owner.snapshot.sourceObjectID,
            ]))
            entries.append(.init(sourceHeadID: head.sourceObjectID, sourceHeadSnapshotSHA256: head.snapshotSHA256,
                sourceHeadViewSHA256: head.viewSHA256, sourcePayloadID: payload,
                sourceOwnerID: owner.snapshot.sourceObjectID, ownerSourceKey: owner.sourceKey, sourceKey: sourceKey,
                variantPath: variant.path, payloadPath: variant.payloadPath, payloadSHA256: variant.payloadSHA256,
                metadataSHA256: variant.metadataSHA256, size: Int64(variant.payloadBytes),
                name: variant.name, mimeType: variant.mime))
        }
        let actualRows = try references.map { value -> AnyJSON in
            guard let row = value.object,
                  Set(row.keys) == ["OwnerObjectID", "Field", "TargetObjectID", "FileID", "LegacyFileID"],
                  value["LegacyFileID"]?.bool == false,
                  let owner = value["OwnerObjectID"]?.string, let field = value["Field"]?.string,
                  let target = value["TargetObjectID"]?.string, let payload = value["FileID"]?.string,
                  Self.identity(owner), Self.identity(target), Self.identity(payload),
                  !field.isEmpty, field.utf8.count <= 16_384 else {
                throw AnyHeartNativeCapturedFilePlanError.incompleteReferences
            }
            return value
        }
        let expectedRows = expected.sorted {
            if !Self.same($0.owner, $1.owner) { return Self.less($0.owner, $1.owner) }
            if !Self.same($0.field, $1.field) { return Self.less($0.field, $1.field) }
            return Self.less($0.payload, $1.payload)
        }.map(\.json)
        guard try Self.bytes(.array(actualRows)) == Self.bytes(.array(expectedRows)) else {
            throw AnyHeartNativeCapturedFilePlanError.incompleteReferences
        }
        let schema = schemaIDs.map { String(decoding: $0, as: UTF8.self) }.sorted(by: Self.less)
        let material: AnyJSON = .object([
            "contract": .string(Self.contract), "sourceAccountID": .string(sourceAccountID),
            "sourceSpaceID": .string(sourceSpaceID), "captureManifestSHA256": .string(captureManifestSHA256),
            "sourceWitnessSHA256": .string(sourceWitnessSHA256), "catalogSHA256": .string(catalog.contentSHA256),
            "heads": .array(entries.map { entry in .object([
                "sourceHeadID": .string(entry.sourceHeadID),
                "snapshotSHA256": .string(entry.sourceHeadSnapshotSHA256), "viewSHA256": .string(entry.sourceHeadViewSHA256),
                "sourcePayloadID": .string(entry.sourcePayloadID), "sourceOwnerID": .string(entry.sourceOwnerID),
                "ownerSourceKey": .string(entry.ownerSourceKey), "sourceKey": .string(entry.sourceKey),
                "variantPath": .string(entry.variantPath), "payloadPath": .string(entry.payloadPath),
                "payloadSHA256": .string(entry.payloadSHA256), "metadataSHA256": .string(entry.metadataSHA256),
                "size": .integer(entry.size), "name": .string(entry.name), "mime": .string(entry.mimeType),
            ]) }),
            "fileSchemaObjectIDs": .array(schema.map(AnyJSON.string)), "references": .array(expectedRows),
        ])
        self.sourceAccountID = sourceAccountID; self.sourceSpaceID = sourceSpaceID
        self.captureManifestSHA256 = captureManifestSHA256; self.sourceWitnessSHA256 = sourceWitnessSHA256
        catalogSHA256 = catalog.contentSHA256; self.entries = entries; self.uses = uses
        fileSchemaObjectIDs = schema; contentSHA256 = AnyContentDigest.sha256(try Self.bytes(material))
    }

    func require(catalog: AnyHeartNativeDefinitionCatalog) throws {
        guard Self.same(sourceAccountID, catalog.sourceAccountID), Self.same(sourceSpaceID, catalog.sourceSpaceID),
              captureManifestSHA256 == catalog.captureManifestSHA256,
              sourceWitnessSHA256 == catalog.sourceWitnessSHA256, catalogSHA256 == catalog.contentSHA256 else {
            throw AnyHeartNativeCapturedFilePlanError.sourceBinding
        }
    }

    func value(snapshot: AnyHeartNativeSnapshotView, relationKey: String, original: AnyJSON) throws -> AnyDestinationValue {
        guard let use = uses.first(where: {
            Self.same($0.ownerID, snapshot.sourceObjectID) && Self.same($0.relationKey, relationKey)
        }), Self.same(snapshot.sourceSpaceID, sourceSpaceID),
            snapshot.snapshotSHA256 == use.snapshotSHA256, snapshot.viewSHA256 == use.viewSHA256,
            try Self.bytes(original) == Self.bytes(use.value) else {
            throw AnyHeartNativeCapturedFilePlanError.changedProperty(snapshot.sourceObjectID, relationKey)
        }
        return .array(try use.headIDs.map { id in
            guard let entry = entries.first(where: {
                Self.same($0.sourceHeadID, id) && Self.same($0.sourceOwnerID, snapshot.sourceObjectID)
            }) else { throw AnyHeartNativeCapturedFilePlanError.changedProperty(snapshot.sourceObjectID, relationKey) }
            return .reference(entry.reference)
        })
    }

    private static func validate(_ variant: Variant) throws {
        let hash = AnyContentDigest.sha256(Data((variant.fileID + "\0" + variant.path).utf8))
        let expectedPayload = AnyContentDigest.sha256(Data(variant.fileID.utf8)) + "/" + hash + ".payload"
        let expectedMetadata = "metadata-" + hash + ".pb"
        guard identity(variant.fileID), identity(variant.contentID), identity(variant.metadataID),
              variant.path.utf8.count <= 4096, !variant.path.utf8.contains(0), variant.original,
              variant.name.utf8.count <= 1024, variant.mime.utf8.count <= 255,
              !variant.name.utf8.contains(0), !variant.mime.utf8.contains(0),
              variant.payloadBytes >= 0, variant.payloadBytes <= AnyHeartNativePreservationArchive.maximumBytes,
              variant.metadataBytes > 0, variant.metadataBytes <= 8 * 1024 * 1024,
              AnyNativeCreationIdentity.isHex(variant.payloadSHA256, count: 64),
              AnyNativeCreationIdentity.isHex(variant.metadataSHA256, count: 64),
              same(variant.payloadPath, expectedPayload), same(variant.metadataPath, expectedMetadata),
              let raw = variant.raw.object,
              Set(raw.keys) == ["Path", "ContentID", "MetadataID", "Name", "MIME", "NativeChecksum",
                "SourceChecksum", "NativeOriginalPath", "UploadChecksumMatches", "Payload", "Metadata"],
              variant.raw["NativeChecksum"]?.string?.utf8.count ?? Int.max <= 4096,
              variant.raw["SourceChecksum"]?.string?.utf8.count ?? Int.max <= 4096,
              variant.raw["UploadChecksumMatches"]?.bool != nil else {
            throw AnyHeartNativeCapturedFilePlanError.invalidVariant(variant.fileID)
        }
        let expected: AnyJSON = .object([
            "Path": .string(variant.path), "ContentID": .string(variant.contentID), "MetadataID": .string(variant.metadataID),
            "Name": .string(variant.name), "MIME": .string(variant.mime), "NativeOriginalPath": .bool(true),
            "NativeChecksum": variant.raw["NativeChecksum"]!, "SourceChecksum": variant.raw["SourceChecksum"]!,
            "UploadChecksumMatches": variant.raw["UploadChecksumMatches"]!,
            "Payload": .object(["Path": .string(expectedPayload), "SHA256": .string(variant.payloadSHA256),
                "Bytes": .integer(Int64(variant.payloadBytes))]),
            "Metadata": .object(["Path": .string(expectedMetadata), "SHA256": .string(variant.metadataSHA256),
                "Bytes": .integer(Int64(variant.metadataBytes))]),
        ])
        guard try bytes(variant.raw) == bytes(expected) else {
            throw AnyHeartNativeCapturedFilePlanError.invalidVariant(variant.fileID)
        }
    }

    private static func validateHead(_ snapshot: AnyHeartNativeSnapshotView, variant: Variant,
                                     catalog: AnyHeartNativeDefinitionCatalog) throws -> [String] {
        let id = snapshot.sourceObjectID, details = snapshot.details
        func reject(_ field: String) -> AnyHeartNativeCapturedFilePlanError { .unsupportedHead(id, field) }
        guard snapshot.nativeType == 533, snapshot.uniqueKey.isEmpty, snapshot.issues.isEmpty,
              snapshot.objectTypes.count == 1, let type = catalog.type(url: snapshot.objectTypes[0]),
              same(type.typeKey, "file"), type.recommendedLayout == 6,
              details["layout"]?.integer == 6, details["fileIndexingStatus"]?.integer == 1,
              details["isReadonly"]?.bool == false,
              let name = details["name"]?.string, let ext = details["fileExt"]?.string,
              let mime = details["fileMimeType"]?.string,
              let size = details["sizeInBytes"]?.integer, size == Int64(variant.payloadBytes),
              let added = details["addedDate"]?.integer,
              let modified = details["lastModifiedDate"]?.integer,
              same(name + (ext.isEmpty ? "" : "." + ext), variant.name), same(mime, variant.mime),
              details["fileId"]?.string.map({ same($0, variant.fileID) }) == true else { throw reject("identity or metadata") }
        _ = modified
        let stringFields: Set<String> = ["name", "fileExt", "fileMimeType", "fileId", "fileSourceChecksum",
            "id", "spaceId", "uniqueKey", "apiObjectKey", "sourceObject"]
        let integerFields: Set<String> = ["layout", "fileIndexingStatus", "sizeInBytes", "addedDate", "createdDate",
            "lastModifiedDate", "origin", "importType", "revision", "syncStatus", "syncError", "fileBackupStatus"]
        let participantFields: Set<String> = ["creator", "lastModifiedBy"]
        let falseFields: Set<String> = ["isReadonly", "isArchived", "isHidden", "isHiddenDiscovery", "done"]
        let emptyTextFields: Set<String> = ["description", "iconEmoji", "iconImage", "iconName"]
        let listFields: Set<String> = ["fileVariantIds", "fileVariantPaths", "fileVariantChecksums",
            "fileVariantMills", "fileVariantKeys", "fileVariantOptions"]
        let allowed = stringFields.union(integerFields).union(participantFields).union(falseFields)
            .union(emptyTextFields).union(listFields)
            .union(["type", "fileVariantWidths", "featuredRelations", "internalFlags", "layoutAlign", "iconOption"])
        guard Set(details.keys).isSubset(of: allowed) else { throw reject("unrepresented detail") }
        var dependencies = Set<Data>([Data(type.objectID.utf8)])
        for key in details.keys {
            guard let relation = catalog.relation(key: key) else { throw reject("missing descriptor:" + key) }
            dependencies.insert(Data(relation.objectID.utf8))
            let value = details[key]!
            if stringFields.contains(key) {
                guard let text = value.string, text.utf8.count <= 16_384, !text.utf8.contains(0) else { throw reject(key) }
            } else if integerFields.contains(key) {
                guard value.integer != nil else { throw reject(key) }
            } else if participantFields.contains(key) {
                let ids = value.string.map { [$0] } ?? value.array?.compactMap(\.string)
                guard let ids, ids.count <= 1, value.array == nil || value.array?.count == ids.count,
                      ids.allSatisfy(identity) else { throw reject(key) }
            } else if falseFields.contains(key) {
                guard value.bool == false else { throw reject(key) }
            } else if emptyTextFields.contains(key) {
                guard value.string?.isEmpty == true else { throw reject(key) }
            } else if listFields.contains(key) {
                guard let rows = value.array, rows.count == 1, let text = rows[0].string,
                      text.utf8.count <= 16_384, !text.utf8.contains(0) else { throw reject(key) }
            } else if key == "type" {
                let ids = value.string.map { [$0] } ?? value.array?.compactMap(\.string)
                guard let ids, ids.count == 1, value.array == nil || value.array?.count == 1,
                      same(ids[0], snapshot.objectTypes[0]) else { throw reject(key) }
            } else if key == "fileVariantWidths" {
                guard value == .array([.integer(0)]) else { throw reject(key) }
            } else if key == "layoutAlign" || key == "iconOption" {
                guard value.integer == 0 else { throw reject(key) }
            } else {
                guard value == .array([]) else { throw reject(key) }
            }
        }
        if let nativeID = details["id"]?.string, !same(nativeID, id) { throw reject("id") }
        if let space = details["spaceId"]?.string, !same(space, snapshot.sourceSpaceID) { throw reject("spaceId") }
        if let unique = details["uniqueKey"]?.string, !unique.isEmpty { throw reject("uniqueKey") }
        let raw = snapshot.rawSnapshot
        guard let rawFields = raw.object,
              Set(rawFields.keys) == ["blocks", "details", "fileKeys", "extraRelations", "objectTypes",
                "collections", "removedCollectionKeys", "relationLinks", "key", "originalCreatedTimestamp", "fileInfo"],
              emptyObject(raw["fileKeys"]), raw["extraRelations"] == .array([]),
              emptyObject(raw["collections"]), raw["removedCollectionKeys"] == .array([]),
              raw["key"] == .string(""), decimal(raw["originalCreatedTimestamp"]) != nil,
              let info = raw["fileInfo"]?.object, Set(info.keys) == ["fileId", "encryptionKeys"],
              info["fileId"]?.string.map({ same($0, variant.fileID) }) == true,
              let encryption = info["encryptionKeys"]?.array, encryption.count <= 1 else { throw reject("snapshot envelope") }
        var encryptionKey = ""
        if let row = encryption.first {
            guard let fields = row.object, Set(fields.keys) == ["path", "key"],
                  row["path"]?.string.map({ same($0, variant.path) }) == true,
                  let key = row["key"]?.string, key.utf8.count <= 16_384, !key.utf8.contains(0) else {
                throw reject("encryption key")
            }
            encryptionKey = key
        }
        let expectedArrays: [String: AnyJSON] = [
            "fileVariantIds": .array([.string(variant.contentID)]),
            "fileVariantPaths": .array([.string(variant.path)]),
            "fileVariantChecksums": .array([variant.raw["NativeChecksum"]!]),
            "fileVariantKeys": .array([.string(encryptionKey)]),
            "fileVariantWidths": .array([.integer(0)]),
        ]
        for (key, value) in expectedArrays {
            guard let actual = details[key], try bytes(actual) == bytes(value) else { throw reject(key) }
        }
        guard let sourceChecksum = details["fileSourceChecksum"],
              try bytes(sourceChecksum) == bytes(variant.raw["SourceChecksum"]!),
              details["fileVariantMills"]?.array?.count == 1,
              details["fileVariantOptions"]?.array?.count == 1 else { throw reject("variant metadata") }
        var links = Set<Data>(), linkNames = Set<String>()
        for row in snapshot.relationLinks {
            guard let fields = row.object, Set(fields.keys) == ["key", "format"],
                  let key = row["key"]?.string, let format = row["format"]?.integer,
                  links.insert(Data(key.utf8)).inserted, linkNames.insert(key).inserted,
                  let relation = catalog.relation(key: key), relation.rawFormat == format else {
                throw reject("relation link")
            }
            dependencies.insert(Data(relation.objectID.utf8))
        }
        guard catalog.issues.allSatisfy({ !dependencies.contains(Data($0.sourceObjectID.utf8)) }) else {
            throw reject("descriptor issue")
        }
        let optionalRelations = ["sizeInBytes", "origin", "importType", "addedDate"].filter {
            (details[$0]?.integer ?? 0) != 0
        }
        let rootChildren = ["header", "file", "info", "description", "fileExt"] + optionalRelations
        var expectedIDs = Set<Data>(([id, "header", "title", "featuredRelations"] + Array(rootChildren.dropFirst())).map { Data($0.utf8) })
        guard expectedIDs.count == rootChildren.count + 3,
              snapshot.blocks.count == expectedIDs.count else { throw reject("block census") }
        let restrictions: AnyJSON = .object(["read": .bool(false), "edit": .bool(true),
            "remove": .bool(true), "drag": .bool(true), "dropOn": .bool(true)])
        for block in snapshot.blocks {
            let blockID = Data(block.id.utf8)
            guard expectedIDs.remove(blockID) != nil, let fields = block.raw.object,
                  let kind = block.contentKind,
                  Set(fields.keys) == Set(["id", "fields", "restrictions", "childrenIds", "backgroundColor",
                    "align", "verticalAlign", kind]),
                  block.raw["restrictions"] == restrictions,
                  block.raw["backgroundColor"] == .string(""),
                  block.raw["align"] == .integer(0), block.raw["verticalAlign"] == .integer(0) else {
                throw reject("block metadata")
            }
            let expectedChildren: [String]
            let expectedKind: String
            let expectedContent: AnyJSON
            if same(block.id, id) {
                expectedChildren = rootChildren; expectedKind = "smartblock"; expectedContent = .object([:])
            } else if same(block.id, "header") {
                expectedChildren = ["title", "featuredRelations"]; expectedKind = "layout"
                expectedContent = .object(["style": .integer(3)])
            } else if same(block.id, "title") {
                expectedChildren = []; expectedKind = "text"
                expectedContent = textContent(text: "", style: 7, marks: block.content?["marks"] ?? .null)
                guard emptyMarks(block.content?["marks"]),
                      block.raw["fields"] == .object(["_detailsKey": .array([.string("name"), .string("done")])]) else {
                    throw reject("title")
                }
            } else if same(block.id, "featuredRelations") {
                expectedChildren = []; expectedKind = "featuredRelations"; expectedContent = .object([:])
            } else if same(block.id, "file") {
                expectedChildren = []; expectedKind = "file"
                expectedContent = .object(["hash": .string(""), "name": .string(name), "type": .integer(1),
                    "mime": .string(mime), "size": .string(String(size)), "addedAt": .string(String(added)),
                    "targetObjectId": .string(id), "state": .integer(2), "style": .integer(0)])
            } else if same(block.id, "info") {
                expectedChildren = []; expectedKind = "text"
                expectedContent = textContent(text: "File Information", style: 0, marks: .object(["marks": .array([
                    .object(["range": .object(["from": .integer(0), "to": .integer(16)]),
                        "type": .integer(3), "param": .string("")]),
                ])]))
            } else {
                expectedChildren = []; expectedKind = "relation"; expectedContent = .object(["key": .string(block.id)])
            }
            guard same(kind, expectedKind),
                  block.childIDs.map({ Data($0.utf8) }) == expectedChildren.map({ Data($0.utf8) }),
                  let content = block.content, try bytes(content) == bytes(expectedContent),
                  same(block.id, "title") || emptyObject(block.raw["fields"]) else {
                throw reject("generated block:" + block.id)
            }
        }
        guard expectedIDs.isEmpty else { throw reject("block census") }
        return dependencies.map { String(decoding: $0, as: UTF8.self) }.sorted(by: less)
    }

    private static func textContent(text: String, style: Int64, marks: AnyJSON) -> AnyJSON {
        .object(["text": .string(text), "style": .integer(style), "marks": marks, "checked": .bool(false),
            "color": .string(""), "iconEmoji": .string(""), "iconImage": .string("")])
    }
    private static func emptyMarks(_ value: AnyJSON?) -> Bool {
        value == .null || value == .object(["marks": .array([])])
    }
    private static func emptyObject(_ value: AnyJSON?) -> Bool { value == .null || value == .object([:]) }
    private static func decimal(_ value: AnyJSON?) -> Int64? {
        guard let text = value?.string, let integer = Int64(text), same(String(integer), text) else { return nil }
        return integer
    }
    private static func bytes(_ value: AnyJSON) throws -> Data { try AnyDestinationDefinitionChecks.bytes(value) }
    private static func same(_ lhs: String, _ rhs: String) -> Bool { lhs.utf8.elementsEqual(rhs.utf8) }
    private static func less(_ lhs: String, _ rhs: String) -> Bool { lhs.utf8.lexicographicallyPrecedes(rhs.utf8) }
    private static func identity(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 &&
        value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }
}
