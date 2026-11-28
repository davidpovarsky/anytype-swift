import Foundation
import PinkhaKit
import PinkhaAnyEngine

public enum AnyHeartNativePinkhaSourceError: Error, Equatable, Sendable {
    case sourceBinding, ambiguousManifest, invalidManifest(String)
    case missingDefinition(String), malformedValue(String, String)
    case unknownObject(String), missingMapping(String), emptyCanonicalProperty
}

/// Resolves Pinkha's actual captured manifest against native definition IDs.
/// Display names never bind a property or document type. Raw source bytes and
/// absent/empty values stay available; this component grants no migration access.
public struct AnyHeartNativePinkhaSource: Sendable {
    public enum Role: Equatable, Sendable {
        case folder, bookFolder, writingDocument(String)
    }
    public struct Property: Sendable {
        public let objectID: String
        public let key: String
        public let format: AnyHeartNativeDefinitionCatalog.Format
        public let definitionSnapshotSHA256: String
    }
    public struct HierarchyEntry: Sendable {
        public let snapshot: AnyHeartNativeSnapshotView
        public let typeID: String
        public let role: Role
        public let originalParent: AnyJSON?
        public let parentObjectID: String?
        public let originalOrder: AnyJSON?
        public let order: Double?
    }
    public struct CanonicalDocument: Sendable {
        public let snapshot: AnyHeartNativeSnapshotView
        public let propertyKey: String
        /// Explicit empty string is distinct from an absent source property.
        public let sourceBytes: Data
        public let records: [TorahStoredAssociationRecord]
        public var sourceSHA256: String { AnyContentDigest.sha256(sourceBytes) }
    }
    public struct Issue: Equatable, Sendable {
        public let objectID: String
        public let field: String
        public let reason: String
    }

    public let sourceAccountID: String
    public let sourceSpaceID: String
    public let captureManifestSHA256: String
    public let sourceWitnessSHA256: String
    public let manifestObjectID: String
    public let manifestSnapshotSHA256: String
    public let manifestBytes: Data
    public let rawManifest: AnyJSON
    public let contentSHA256: String
    public let parentProperty: Property
    public let orderProperty: Property
    public let associationsProperty: Property
    public let folderTypeID: String
    public let bookFolderTypeID: String
    public let documentTypes: [String: String]
    public let defaultTemplates: [String: String]
    public let hierarchy: [HierarchyEntry]
    public let canonicalDocuments: [CanonicalDocument]
    public let issues: [Issue]
    private let capturedObjectIDs: Set<Data>
    public var permitsDestinationWrites: Bool { false }

    public static func discover(in bundle: AnyHeartNativeSpaceBundle) throws -> Self? {
        try discover(catalog: .init(bundle: bundle), snapshots: bundle.objects)
    }

    /// Detached control boundary. Only the verified outer bundle is public.
    static func discover(catalog: AnyHeartNativeDefinitionCatalog,
                         snapshots: [AnyHeartNativeSnapshotView]) throws -> Self? {
        guard snapshots.count <= 100_000,
              snapshots.allSatisfy({ exact($0.sourceSpaceID, catalog.sourceSpaceID) }),
              Set(snapshots.map { Data($0.sourceObjectID.utf8) }).count == snapshots.count,
              Set(snapshots.map(\.sourceObjectID)).count == snapshots.count else {
            throw AnyHeartNativePinkhaSourceError.sourceBinding
        }
        var candidates: [(AnyHeartNativeSnapshotView, Data, AnyJSON)] = []
        for snapshot in snapshots {
            // This matches the original store's legacy-name discovery. The
            // complete manifest's source identity is still required below.
            guard snapshot.details["name"]?.string == PinkhaSchemaRoles.manifestName ||
                    snapshot.uniqueKey == PinkhaSchemaRoles.manifestUniqueKey else { continue }
            guard let text = snapshot.details["description"]?.string,
                  !text.isEmpty, text.utf8.count <= 1_048_576 else { continue }
            let bytes = Data(text.utf8)
            guard let raw = try? JSONDecoder().decode(AnyJSON.self, from: bytes),
                  raw.object != nil, let space = raw["spaceId"]?.string,
                  exact(space, catalog.sourceSpaceID) else { continue }
            if let owner = raw["manifestObjectId"], owner != .null {
                guard let id = owner.string, exact(id, snapshot.sourceObjectID) else { continue }
            }
            candidates.append((snapshot, bytes, raw))
        }
        guard candidates.count <= 1 else { throw AnyHeartNativePinkhaSourceError.ambiguousManifest }
        guard let (snapshot, bytes, manifest) = candidates.first else { return nil }
        return try .init(catalog: catalog, snapshots: snapshots, manifestSnapshot: snapshot,
                         manifestBytes: bytes, rawManifest: manifest)
    }

    private init(catalog: AnyHeartNativeDefinitionCatalog, snapshots: [AnyHeartNativeSnapshotView],
                 manifestSnapshot: AnyHeartNativeSnapshotView,
                 manifestBytes: Data, rawManifest: AnyJSON) throws {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: manifestBytes, encoded: encoder.encode(rawManifest))
        guard manifestSnapshot.nativeType == 16,
              rawManifest["schemaVersion"]?.integer == Int64(PinkhaSpaceManifest.currentSchemaVersion),
              rawManifest["provisioningState"] == nil || rawManifest["provisioningState"] == .string("complete") else {
            throw AnyHeartNativePinkhaSourceError.invalidManifest("version, native kind or incomplete provisioning")
        }
        let byID = Dictionary(uniqueKeysWithValues: snapshots.map { (Data($0.sourceObjectID.utf8), $0) })
        func identifier(_ value: AnyJSON?, _ field: String) throws -> String {
            guard let id = value?.string, Self.validID(id) else {
                throw AnyHeartNativePinkhaSourceError.invalidManifest(field)
            }
            return id
        }
        func property(_ idField: String, _ keyField: String,
                      format: AnyHeartNativeDefinitionCatalog.Format) throws -> Property {
            let id = try identifier(rawManifest[idField], idField)
            let key = try identifier(rawManifest[keyField], keyField)
            guard let byID = catalog.relation(objectID: id), let byKey = catalog.relation(key: key),
                  Self.exact(byID.objectID, byKey.objectID), Self.exact(byID.relationKey, key),
                  byID.format == format else {
                throw AnyHeartNativePinkhaSourceError.missingDefinition(idField)
            }
            return .init(objectID: id, key: key, format: format,
                         definitionSnapshotSHA256: byID.snapshot.snapshotSHA256)
        }
        let parent = try property("parentPropertyId", "parentPropertyKey", format: .object)
        let order = try property("orderPropertyId", "orderPropertyKey", format: .number)
        let associations = try property("documentAssociationsPropertyId", "documentAssociationsPropertyKey", format: .longText)
        guard Set([parent.objectID, order.objectID, associations.objectID]).count == 3,
              Set([parent.key, order.key, associations.key]).count == 3 else {
            throw AnyHeartNativePinkhaSourceError.invalidManifest("aliased property roles")
        }
        let folder = try identifier(rawManifest["folderTypeId"], "folderTypeId")
        let book = try identifier(rawManifest["bookFolderTypeId"], "bookFolderTypeId")
        func roles(_ field: String) throws -> [String: String] {
            guard let values = rawManifest[field]?.object, values.count <= 128 else {
                throw AnyHeartNativePinkhaSourceError.invalidManifest(field)
            }
            return try values.reduce(into: [:]) { result, pair in
                guard Self.validID(pair.key), pair.key.utf8.count <= 128 else {
                    throw AnyHeartNativePinkhaSourceError.invalidManifest(field)
                }
                result[pair.key] = try identifier(pair.value, field + "." + pair.key)
            }
        }
        let types = try roles("registeredDocumentTypes"), templates = try roles("defaultTemplateIds")
        let required = [PinkhaSchemaRoles.chiddushKey, PinkhaSchemaRoles.articleKey, PinkhaSchemaRoles.researchKey]
        guard required.allSatisfy({ types[$0] != nil && templates[$0] != nil }),
              Set([folder, book] + Array(types.values)).count == 2 + types.count else {
            throw AnyHeartNativePinkhaSourceError.invalidManifest("missing or ambiguous type roles")
        }
        var typeRoles: [Data: Role] = [:]
        for (id, role) in [(folder, Role.folder), (book, .bookFolder)] +
                types.map({ ($0.value, Role.writingDocument($0.key)) }) {
            guard catalog.type(objectID: id) != nil else {
                throw AnyHeartNativePinkhaSourceError.missingDefinition("type role")
            }
            typeRoles[Data(id.utf8)] = role
        }
        for (role, id) in templates {
            guard types[role] != nil, byID[Data(id.utf8)] != nil else {
                throw AnyHeartNativePinkhaSourceError.missingDefinition("default template")
            }
        }
        let known: Set<String> = ["schemaVersion", "spaceId", "manifestObjectId", "provisioningState",
            "parentPropertyId", "parentPropertyKey", "orderPropertyId", "orderPropertyKey",
            "documentAssociationsPropertyId", "documentAssociationsPropertyKey",
            "folderTypeId", "bookFolderTypeId", "registeredDocumentTypes", "defaultTemplateIds",
            "createdAt", "updatedAt"]
        var issues = Set(rawManifest.object!.keys).subtracting(known).sorted().map {
            Issue(objectID: manifestSnapshot.sourceObjectID, field: $0, reason: "unknown-manifest-field-retained")
        }
        var entries: [HierarchyEntry] = [], documents: [CanonicalDocument] = []
        for snapshot in snapshots.sorted(by: { Data($0.sourceObjectID.utf8).lexicographicallyPrecedes(Data($1.sourceObjectID.utf8)) }) {
            if snapshot.objectTypes.count == 1,
               let type = catalog.type(url: snapshot.objectTypes[0]),
               let role = typeRoles[Data(type.objectID.utf8)] {
                let originalParent = snapshot.details[parent.key]
                let parentID = try Self.parentID(originalParent, objectID: snapshot.sourceObjectID, field: parent.key)
                let originalOrder = snapshot.details[order.key]
                let rank = try Self.rank(originalOrder, objectID: snapshot.sourceObjectID, field: order.key)
                entries.append(.init(snapshot: snapshot, typeID: type.objectID, role: role,
                    originalParent: originalParent, parentObjectID: parentID, originalOrder: originalOrder, order: rank))
                if let parentID, byID[Data(parentID.utf8)] == nil {
                    issues.append(.init(objectID: snapshot.sourceObjectID, field: parent.key, reason: "parent-outside-captured-source"))
                }
                if role == .bookFolder {
                    issues.append(.init(objectID: snapshot.sourceObjectID, field: "type", reason: "book-folder-needs-distinct-destination-behavior"))
                }
            }
            guard let value = snapshot.details[associations.key] else { continue }
            guard let text = value.string, text.utf8.count <= 16 * 1024 * 1024 else {
                throw AnyHeartNativePinkhaSourceError.malformedValue(snapshot.sourceObjectID, associations.key)
            }
            let bytes = Data(text.utf8)
            let records: [TorahStoredAssociationRecord]
            if text.isEmpty { records = [] } // Original Heart reader's explicit empty-string behavior.
            else {
                let location = TorahAssociationLocation(spaceId: catalog.sourceSpaceID,
                    target: .object(objectId: snapshot.sourceObjectID))
                let decoded = try TorahAssociationPayloadCodec().decodeCanonicalDocument(bytes, legacyLocation: location)
                try AnyTorahSourceJSONGuard.validateCanonicalPayload(bytes, decoded: decoded)
                guard decoded.records.allSatisfy({
                    Self.exact($0.spaceId, catalog.sourceSpaceID) && Self.exact($0.objectId, snapshot.sourceObjectID)
                }) else { throw AnyHeartNativePinkhaSourceError.malformedValue(snapshot.sourceObjectID, associations.key) }
                var stable = Set<String>(), semantic = Set<TorahAssociationIdentity>()
                for record in decoded.records {
                    guard !record.item.id.isEmpty, !record.item.providerID.isEmpty,
                          !record.item.canonicalKey.isEmpty || !record.item.externalID.isEmpty,
                          record.blockId == nil || snapshot.blocks.contains(where: { Self.exact($0.id, record.blockId!) }),
                          stable.insert("\((record.blockId ?? "").utf8.count):\(record.blockId ?? "")\(record.item.id.utf8.count):\(record.item.id)").inserted,
                          semantic.insert(.init(item: record.item, location: record.location)).inserted else {
                        throw AnyHeartNativePinkhaSourceError.malformedValue(snapshot.sourceObjectID, associations.key)
                    }
                    _ = try TorahSemanticAnchorAssociation.decoding(record.item, location: record.location)
                }
                records = decoded.records
            }
            documents.append(.init(snapshot: snapshot, propertyKey: associations.key, sourceBytes: bytes, records: records))
        }
        let entriesByID = Dictionary(uniqueKeysWithValues: entries.map { (Data($0.snapshot.sourceObjectID.utf8), $0) })
        for entry in entries {
            var visited = Set<Data>(), cursor: HierarchyEntry? = entry
            while let current = cursor {
                guard visited.insert(Data(current.snapshot.sourceObjectID.utf8)).inserted else {
                    issues.append(.init(objectID: entry.snapshot.sourceObjectID, field: parent.key, reason: "hierarchy-cycle-retained"))
                    break
                }
                cursor = current.parentObjectID.flatMap { entriesByID[Data($0.utf8)] }
            }
            if let parentID = entry.parentObjectID {
                if let target = entriesByID[Data(parentID.utf8)] {
                    if target.role != .folder {
                        issues.append(.init(objectID: entry.snapshot.sourceObjectID, field: parent.key, reason: "parent-is-not-ordinary-folder"))
                    }
                } else {
                    issues.append(.init(objectID: entry.snapshot.sourceObjectID, field: parent.key, reason: "parent-has-no-Pinkha-hierarchy-role"))
                }
            }
        }
        self.sourceAccountID = catalog.sourceAccountID; self.sourceSpaceID = catalog.sourceSpaceID
        self.captureManifestSHA256 = catalog.captureManifestSHA256; self.sourceWitnessSHA256 = catalog.sourceWitnessSHA256
        self.manifestObjectID = manifestSnapshot.sourceObjectID; self.manifestSnapshotSHA256 = manifestSnapshot.snapshotSHA256
        self.manifestBytes = manifestBytes; self.rawManifest = rawManifest
        self.parentProperty = parent; self.orderProperty = order; self.associationsProperty = associations
        self.folderTypeID = folder; self.bookFolderTypeID = book
        self.documentTypes = types; self.defaultTemplates = templates
        self.hierarchy = entries; self.canonicalDocuments = documents; self.issues = issues
        self.capturedObjectIDs = Set(byID.keys)
        let material: AnyJSON = .object(["contract": .string("pinkha-captured-schema-source-v1"),
            "catalog": .string(catalog.contentSHA256), "manifest": .string(AnyContentDigest.sha256(manifestBytes)),
            "snapshots": .array(snapshots.sorted { Data($0.sourceObjectID.utf8).lexicographicallyPrecedes(Data($1.sourceObjectID.utf8)) }.map {
                .object(["id": .string($0.sourceObjectID), "protobuf": .string($0.snapshotSHA256), "view": .string($0.viewSHA256)])
            })])
        contentSHA256 = AnyContentDigest.sha256(try encoder.encode(material))
    }

    /// Component plan from the exact captured native property. Caller must
    /// still establish current source authority and whole-source coverage.
    public func canonicalPlan(sourceObjectID: String, workspace: AnyTorahWorkspace,
                              objectIDMap: [String: String], blockIDMap: [String: String],
                              migrationKey: String) throws -> AnyTorahMigrationPlan {
        guard let document = canonicalDocuments.first(where: { Self.exact($0.snapshot.sourceObjectID, sourceObjectID) }) else {
            throw AnyHeartNativePinkhaSourceError.unknownObject(sourceObjectID)
        }
        guard !document.sourceBytes.isEmpty else { throw AnyHeartNativePinkhaSourceError.emptyCanonicalProperty }
        guard objectIDMap.allSatisfy({ capturedObjectIDs.contains(Data($0.key.utf8)) && Self.validID($0.value) }),
              Set(objectIDMap.values.map { Data($0.utf8) }).count == objectIDMap.count else {
            throw AnyHeartNativePinkhaSourceError.sourceBinding
        }
        guard let target = objectIDMap.first(where: { Self.exact($0.key, sourceObjectID) })?.value else {
            throw AnyHeartNativePinkhaSourceError.missingMapping(sourceObjectID)
        }
        return try .init(sourceBytes: document.sourceBytes, sourceSpaceID: sourceSpaceID, sourceObjectID: sourceObjectID,
            workspace: workspace, targetObjectID: target, blockIDMap: blockIDMap, objectIDMap: objectIDMap, migrationKey: migrationKey)
    }

    private static func parentID(_ value: AnyJSON?, objectID: String, field: String) throws -> String? {
        guard let value else { return nil }
        if let text = value.string {
            guard text.isEmpty || validID(text) else { throw AnyHeartNativePinkhaSourceError.malformedValue(objectID, field) }
            return text.isEmpty ? nil : text
        }
        if let rows = value.array {
            guard rows.count <= 1 else { throw AnyHeartNativePinkhaSourceError.malformedValue(objectID, field) }
            guard let first = rows.first else { return nil }
            guard let text = first.string, validID(text) else { throw AnyHeartNativePinkhaSourceError.malformedValue(objectID, field) }
            return text
        }
        throw AnyHeartNativePinkhaSourceError.malformedValue(objectID, field)
    }

    private static func rank(_ value: AnyJSON?, objectID: String, field: String) throws -> Double? {
        guard let value else { return nil }
        switch value {
        case .integer(let number):
            guard let result = Double(exactly: number) else { throw AnyHeartNativePinkhaSourceError.malformedValue(objectID, field) }
            return result
        case .number(let number):
            guard number.isFinite else { throw AnyHeartNativePinkhaSourceError.malformedValue(objectID, field) }
            return number
        default: throw AnyHeartNativePinkhaSourceError.malformedValue(objectID, field)
        }
    }
    private static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 &&
        value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }
    private static func exact(_ lhs: String, _ rhs: String) -> Bool { Data(lhs.utf8) == Data(rhs.utf8) }
}
