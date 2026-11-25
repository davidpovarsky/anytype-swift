import Foundation
import PinkhaAnyEngine

public enum AnyHeartNativeDefinitionCatalogError: Error, Equatable, Sendable {
    case invalidBinding, limit
    case invalidDefinition(String, String)
    case duplicateObjectID(String)
}

/// The current definitions captured from native stores. Object IDs, unique
/// keys, type URLs and relation keys have distinct lookup namespaces. No
/// bundled template replaces a captured override, and no title is an identity.
public struct AnyHeartNativeDefinitionCatalog: Sendable {
    public enum Format: Int64, Sendable {
        case longText = 0, shortText = 1, number = 2, status = 3, date = 4
        case file = 5, checkbox = 6, url = 7, email = 8, phone = 9, emoji = 10
        case tag = 11, object = 100, relations = 101, map = 102
    }

    /// Source creation/import provenance on a captured definition. Heart writes
    /// addedDate as signed Unix seconds; it is not the destination createdAt.
    /// The original JSON value and original snapshot bytes remain authoritative.
    public struct SourceProvenance: Sendable {
        public let addedDateSeconds: Int64?
        public let originalAddedDate: AnyJSON?
        public init(snapshot: AnyHeartNativeSnapshotView) throws {
            guard [521, 528, 529].contains(snapshot.nativeType) else {
                throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(snapshot.sourceObjectID, "nativeType")
            }
            originalAddedDate = snapshot.details["addedDate"]
            if let value = originalAddedDate {
                guard let seconds = value.integer else {
                    throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(snapshot.sourceObjectID, "addedDate")
                }
                addedDateSeconds = seconds
            } else { addedDateSeconds = nil }
        }
    }

    public struct TypeDefinition: Sendable {
        public let snapshot: AnyHeartNativeSnapshotView
        public let sourceProvenance: SourceProvenance
        public let typeKey: String
        public let name: String
        public let description: String
        public let pluralName: String?
        public let recommendedLayout: Int64?
        public let recommendedRelations: [String]
        public let featuredRelations: [String]
        public let hiddenRelations: [String]
        public let fileRelations: [String]
        public var objectID: String { snapshot.sourceObjectID }
        public var typeURL: String { "ot-" + typeKey }
    }

    public struct Relation: Sendable {
        public let snapshot: AnyHeartNativeSnapshotView
        public let sourceProvenance: SourceProvenance
        public let relationKey: String
        public let name: String
        public let description: String
        public let rawFormat: Int64
        public let includeTime: Bool?
        public let maximumCount: Int64?
        public let readonlyValue: Bool?
        /// nil means absent; .null means the captured field explicitly held
        /// null. Empty strings, zero and false are never substituted here.
        public let defaultValue: AnyJSON?
        public let targetTypeIDs: [String]
        public var format: Format? { Format(rawValue: rawFormat) }
        public var objectID: String { snapshot.sourceObjectID }
    }

    public struct Option: Sendable {
        public let snapshot: AnyHeartNativeSnapshotView
        public let sourceProvenance: SourceProvenance
        public let relationKey: String
        public let name: String
        public let color: String
        public let orderID: String
        public var objectID: String { snapshot.sourceObjectID }
    }

    public struct Issue: Equatable, Sendable {
        public enum Kind: String, Sendable {
            case duplicateUniqueKey, duplicateRelationKey, relationKeyMismatch
            case unknownDetailField, unresolvedRecommendation, unresolvedTargetType
            case unresolvedOptionRelation, nativeSnapshotIssue, compiledDescriptorIssue, compiledTypeNotMapped
        }
        public let kind: Kind
        public let sourceObjectID: String
        public let field: String
    }

    public enum ResolvedRelation: Sendable {
        case captured(Relation)
        case compiled(AnyHeartNativeCompiledRelation)
    }

    public let sourceAccountID: String
    public let sourceSpaceID: String
    public let captureManifestSHA256: String
    public let sourceWitnessSHA256: String
    public let contentSHA256: String
    public let types: [TypeDefinition]
    public let relations: [Relation]
    public let options: [Option]
    /// Registry vocabulary captured by the native resolver; never object rows.
    public let compiledRelations: [AnyHeartNativeCompiledRelation]
    public let issues: [Issue]
    public var permitsDestinationWrites: Bool { false }

    private let typeIDs: [Data: Int]
    private let typeKeys: [Data: Int]
    private let relationIDs: [Data: Int]
    private let relationKeys: [Data: Int]
    private let optionIDs: [Data: Int]
    private let compiledRelationKeys: [Data: Int]
    private let capturedRelationKeys: Set<Data>

    public init(bundle: AnyHeartNativeSpaceBundle) throws {
        try self.init(sourceAccountID: bundle.sourceAccountID, sourceSpaceID: bundle.sourceSpaceID,
            captureManifestSHA256: bundle.manifestSHA256, sourceWitnessSHA256: bundle.sourceWitnessSHA256,
            snapshots: bundle.objects, compiledDefinitions: bundle.bundledDefinitions)
    }

    /// Internal fixture boundary. Production callers supply the admitted outer
    /// bundle; detached JSON views alone never establish account authority.
    init(sourceAccountID: String, sourceSpaceID: String, captureManifestSHA256: String,
         sourceWitnessSHA256: String, snapshots: [AnyHeartNativeSnapshotView],
         compiledDefinitions: [AnyHeartNativeBundledDefinition] = []) throws {
        guard Self.identifier(sourceAccountID), Self.identifier(sourceSpaceID),
              Self.digest(captureManifestSHA256), Self.digest(sourceWitnessSHA256) else {
            throw AnyHeartNativeDefinitionCatalogError.invalidBinding
        }
        guard snapshots.count <= 100_000, compiledDefinitions.count <= 1024 else {
            throw AnyHeartNativeDefinitionCatalogError.limit
        }
        var allIDs = Set<Data>(), languageIDs = Set<String>()
        let rows = try snapshots.sorted { Data($0.sourceObjectID.utf8).lexicographicallyPrecedes(Data($1.sourceObjectID.utf8)) }
            .map { row -> AnyHeartNativeSnapshotView in
                guard Data(row.sourceSpaceID.utf8) == Data(sourceSpaceID.utf8) else {
                    throw AnyHeartNativeDefinitionCatalogError.invalidBinding
                }
                guard allIDs.insert(Data(row.sourceObjectID.utf8)).inserted,
                      languageIDs.insert(row.sourceObjectID).inserted else {
                    throw AnyHeartNativeDefinitionCatalogError.duplicateObjectID(row.sourceObjectID)
                }
                return row
            }
        var types: [TypeDefinition] = [], relations: [Relation] = [], options: [Option] = []
        var issues: [Issue] = []
        var compiledIDs = Set<Data>(), compiledNames = Set<String>()
        let compiled = try compiledDefinitions.sorted {
            Data($0.identity.utf8).lexicographicallyPrecedes(Data($1.identity.utf8))
        }.map { source -> AnyHeartNativeBundledDefinition in
            guard compiledIDs.insert(Data(source.identity.utf8)).inserted,
                  compiledNames.insert(source.identity).inserted else {
                throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(source.identity, "duplicate-compiled-identity")
            }
            return source
        }
        let compiledRelations = try compiled.filter { $0.kind == .property }
            .map { try AnyHeartNativeCompiledRelation(source: $0) }
        for row in compiledRelations {
            for field in row.unknownFields {
                issues.append(.init(kind: .compiledDescriptorIssue,
                                    sourceObjectID: row.sourceIdentity, field: field))
            }
        }
        for row in compiled where row.kind == .type {
            issues.append(.init(kind: .compiledTypeNotMapped,
                                sourceObjectID: row.identity, field: "compiled-type-descriptor"))
        }
        var uniqueOwners: [Data: [String]] = [:]

        for row in rows where [521, 528, 529].contains(row.nativeType) {
            guard types.count + relations.count + options.count < 20_000 else {
                throw AnyHeartNativeDefinitionCatalogError.limit
            }
            let d = row.details
            let provenance = try SourceProvenance(snapshot: row)
            func string(_ field: String, required: Bool = false) throws -> String {
                guard let value = d[field] else {
                    if required { throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(row.sourceObjectID, field) }
                    return ""
                }
                guard let text = value.string, text.utf8.count <= 65_536 else {
                    throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(row.sourceObjectID, field)
                }
                return text
            }
            func optionalInteger(_ field: String) throws -> Int64? {
                guard let value = d[field] else { return nil }
                guard let number = value.integer else {
                    throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(row.sourceObjectID, field)
                }
                return number
            }
            func optionalBool(_ field: String) throws -> Bool? {
                guard let value = d[field] else { return nil }
                guard let flag = value.bool else {
                    throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(row.sourceObjectID, field)
                }
                return flag
            }
            func identifiers(_ field: String) throws -> [String] {
                guard let value = d[field] else { return [] }
                guard let list = value.array, list.count <= 20_000 else {
                    throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(row.sourceObjectID, field)
                }
                return try list.map {
                    guard let id = $0.string, Self.identifier(id) else {
                        throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(row.sourceObjectID, field)
                    }
                    return id
                }
            }
            guard Self.identifier(row.uniqueKey) else {
                throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(row.sourceObjectID, "UniqueKey")
            }
            uniqueOwners[Data(row.uniqueKey.utf8), default: []].append(row.sourceObjectID)
            let name = try string("name"), description = try string("description")
            let fields: Set<String>
            switch row.nativeType {
            case 528:
                let typeKey = try Self.key(row.uniqueKey, prefix: "ot", id: row.sourceObjectID)
                types.append(.init(snapshot: row, sourceProvenance: provenance, typeKey: typeKey, name: name, description: description,
                    pluralName: d["pluralName"] == nil ? nil : try string("pluralName"),
                    recommendedLayout: try optionalInteger("recommendedLayout"),
                    recommendedRelations: try identifiers("recommendedRelations"),
                    featuredRelations: try identifiers("recommendedFeaturedRelations"),
                    hiddenRelations: try identifiers("recommendedHiddenRelations"),
                    fileRelations: try identifiers("recommendedFileRelations")))
                fields = Self.typeFields
            case 521:
                let nativeKey = try Self.key(row.uniqueKey, prefix: "rel", id: row.sourceObjectID)
                let key = try string("relationKey", required: true)
                guard Self.identifier(key), let format = try optionalInteger("relationFormat") else {
                    throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(row.sourceObjectID, "relationKey/relationFormat")
                }
                if Data(nativeKey.utf8) != Data(key.utf8) {
                    issues.append(.init(kind: .relationKeyMismatch, sourceObjectID: row.sourceObjectID, field: "relationKey"))
                }
                relations.append(.init(snapshot: row, sourceProvenance: provenance, relationKey: key, name: name, description: description,
                    rawFormat: format, includeTime: try optionalBool("relationFormatIncludeTime"),
                    maximumCount: try optionalInteger("relationMaxCount"), readonlyValue: try optionalBool("relationReadonlyValue"),
                    defaultValue: d["relationDefaultValue"], targetTypeIDs: try identifiers("relationFormatObjectTypes")))
                fields = Self.relationFields
            default:
                _ = try Self.key(row.uniqueKey, prefix: "opt", id: row.sourceObjectID)
                let key = try string("relationKey", required: true)
                guard Self.identifier(key) else {
                    throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(row.sourceObjectID, "relationKey")
                }
                options.append(.init(snapshot: row, sourceProvenance: provenance, relationKey: key, name: name,
                    color: try string("relationOptionColor"), orderID: try string("orderId")))
                fields = Self.optionFields
            }
            for field in d.keys.sorted() where !fields.contains(field) {
                issues.append(.init(kind: .unknownDetailField, sourceObjectID: row.sourceObjectID, field: field))
            }
            for issue in row.issues {
                issues.append(.init(kind: .nativeSnapshotIssue, sourceObjectID: row.sourceObjectID,
                                    field: issue.kind.rawValue + ":" + issue.field))
            }
        }
        for ids in uniqueOwners.values where ids.count > 1 {
            for id in ids { issues.append(.init(kind: .duplicateUniqueKey, sourceObjectID: id, field: "UniqueKey")) }
        }
        func unambiguous(_ pairs: [(String, Int)]) -> [Data: Int] {
            var result: [Data: Int] = [:], duplicates = Set<Data>()
            for (text, index) in pairs {
                let key = Data(text.utf8)
                if result[key] != nil { duplicates.insert(key) }
                result[key] = index
            }
            for key in duplicates { result.removeValue(forKey: key) }
            return result
        }
        let typeIDs = unambiguous(types.enumerated().map { ($0.element.objectID, $0.offset) })
        let typeKeys = unambiguous(types.enumerated().map { ($0.element.typeKey, $0.offset) })
        let relationIDs = unambiguous(relations.enumerated().map { ($0.element.objectID, $0.offset) })
        let relationKeys = unambiguous(relations.enumerated().map { ($0.element.relationKey, $0.offset) })
        for relation in relations where relationKeys[Data(relation.relationKey.utf8)] == nil {
            issues.append(.init(kind: .duplicateRelationKey, sourceObjectID: relation.objectID, field: "relationKey"))
        }
        for type in types {
            for (field, ids) in [("recommendedRelations", type.recommendedRelations),
                ("recommendedFeaturedRelations", type.featuredRelations), ("recommendedHiddenRelations", type.hiddenRelations),
                ("recommendedFileRelations", type.fileRelations)] {
                for id in ids where relationIDs[Data(id.utf8)] == nil {
                    issues.append(.init(kind: .unresolvedRecommendation, sourceObjectID: type.objectID, field: field + ":" + id))
                }
            }
        }
        for relation in relations {
            for id in relation.targetTypeIDs where typeIDs[Data(id.utf8)] == nil {
                issues.append(.init(kind: .unresolvedTargetType, sourceObjectID: relation.objectID,
                                    field: "relationFormatObjectTypes:" + id))
            }
        }
        for option in options {
            guard let index = relationKeys[Data(option.relationKey.utf8)],
                  relations[index].format.map({ [.status, .tag].contains($0) }) == true else {
                issues.append(.init(kind: .unresolvedOptionRelation, sourceObjectID: option.objectID, field: "relationKey"))
                continue
            }
        }
        var boundFields: [String: AnyJSON] = [
            "contract": .string(compiled.isEmpty
                ? "pinkha-captured-definition-catalog-v1" : "pinkha-captured-definition-catalog-v2"),
            "account": .string(sourceAccountID), "space": .string(sourceSpaceID),
            "manifest": .string(captureManifestSHA256), "witness": .string(sourceWitnessSHA256),
            "definitions": .array(rows.filter { [521, 528, 529].contains($0.nativeType) }.map {
                .object(["id": .string($0.sourceObjectID), "pb": .string($0.snapshotSHA256), "json": .string($0.viewSHA256)])
            })
        ]
        if !compiled.isEmpty {
            boundFields["compiledDefinitions"] = .array(compiled.map {
                .object(["identity": .string($0.identity), "pb": .string($0.protobufSHA256),
                         "json": .string($0.jsonViewSHA256)])
            })
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        contentSHA256 = AnyContentDigest.sha256(try encoder.encode(AnyJSON.object(boundFields)))
        self.sourceAccountID = sourceAccountID; self.sourceSpaceID = sourceSpaceID
        self.captureManifestSHA256 = captureManifestSHA256; self.sourceWitnessSHA256 = sourceWitnessSHA256
        self.types = types; self.relations = relations; self.options = options; self.issues = issues
        self.compiledRelations = compiledRelations
        self.compiledRelationKeys = unambiguous(compiledRelations.enumerated().map { ($0.element.relationKey, $0.offset) })
        self.capturedRelationKeys = Set(relations.map { Data($0.relationKey.utf8) })
        self.typeIDs = typeIDs; self.typeKeys = typeKeys
        self.relationIDs = relationIDs; self.relationKeys = relationKeys
        self.optionIDs = unambiguous(options.enumerated().map { ($0.element.objectID, $0.offset) })
    }

    public func type(objectID: String) -> TypeDefinition? { typeIDs[Data(objectID.utf8)].map { types[$0] } }
    public func type(key: String) -> TypeDefinition? { typeKeys[Data(key.utf8)].map { types[$0] } }
    public func type(url: String) -> TypeDefinition? {
        guard let key = try? Self.key(url, prefix: "ot", id: "") else { return nil }
        return type(key: key)
    }
    public func relation(objectID: String) -> Relation? { relationIDs[Data(objectID.utf8)].map { relations[$0] } }
    public func relation(key: String) -> Relation? { relationKeys[Data(key.utf8)].map { relations[$0] } }
    public func compiledRelation(key: String) -> AnyHeartNativeCompiledRelation? {
        compiledRelationKeys[Data(key.utf8)].map { compiledRelations[$0] }
    }
    /// Native captured overrides take precedence. An ambiguous captured key
    /// refuses resolution instead of silently reverting to the compiled entry.
    public func resolvedRelation(key: String) -> ResolvedRelation? {
        if capturedRelationKeys.contains(Data(key.utf8)) {
            return relation(key: key).map(ResolvedRelation.captured)
        }
        return compiledRelation(key: key).map(ResolvedRelation.compiled)
    }
    public func option(objectID: String) -> Option? { optionIDs[Data(objectID.utf8)].map { options[$0] } }
    public func options(relationKey: String) -> [Option] {
        options.filter { Data($0.relationKey.utf8) == Data(relationKey.utf8) }
    }

    private static func key(_ raw: String, prefix: String, id: String) throws -> String {
        // Matches native domain.UnmarshalUniqueKey: exactly two components.
        let parts = raw.split(separator: "-", omittingEmptySubsequences: false)
        guard parts.count == 2, Data(parts[0].utf8) == Data(prefix.utf8), !parts[1].isEmpty else {
            throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(id, "UniqueKey")
        }
        return String(parts[1])
    }
    private static func identifier(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 && !value.utf8.contains(0)
    }
    private static func digest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    private static let commonFields: Set<String> = [
        "name", "description", "isHidden", "layout", "origin", "revision", "sourceObject", "apiObjectKey",
        "internalFlags", "iconEmoji", "iconImage", "createdDate", "creator", "lastModifiedDate", "lastModifiedBy",
        "isArchived", "isReadonly", "uniqueKey", "type", "id", "spaceId", "addedDate",
    ]
    private static let typeFields = commonFields.union([
        "pluralName", "iconName", "iconOption", "recommendedLayout", "recommendedRelations",
        "recommendedFeaturedRelations", "recommendedHiddenRelations", "recommendedFileRelations", "setOf", "smartblockTypes",
    ])
    private static let relationFields = commonFields.union([
        "relationKey", "relationFormat", "relationFormatIncludeTime", "relationFormatObjectTypes",
        "relationMaxCount", "relationReadonlyValue", "relationDefaultValue",
    ])
    private static let optionFields = commonFields.union(["relationKey", "relationOptionColor", "orderId"])
}
