import Foundation
import PinkhaAnyEngine

public enum AnyHeartSpaceDryRunError: Error, Equatable, Sendable {
    case invalidMapping(String), duplicateMapping(String), identityCollision(String), limit
}

/// A complete inventory of the supplied inspected archive and explicit mapping
/// proposals. It performs no IO, creates no native IDs, and cannot authorize
/// prepare/commit. Native census, snapshot admission and conversion are absent.
public struct AnyHeartSpaceMigrationDryRun: Sendable {
    public struct Identity: Hashable, Sendable {
        public enum Kind: String, CaseIterable, Sendable {
            case object, block, file, type, objectType, property, propertyUse
        }
        public let kind: Kind
        public let sourceSpaceID: String
        public let sourceObjectID: String?
        public let sourceID: String

        public init(kind: Kind, sourceSpaceID: String, sourceObjectID: String? = nil, sourceID: String) {
            self.kind = kind; self.sourceSpaceID = sourceSpaceID
            self.sourceObjectID = sourceObjectID; self.sourceID = sourceID
        }

        fileprivate var material: Data {
            AnyHeartSpaceMigrationDryRun.material([
                kind.rawValue, sourceSpaceID, sourceObjectID == nil ? "absent" : "present",
                sourceObjectID ?? "", sourceID
            ])
        }

        /// A report-local symbol, never a destination object/block/file ID.
        public var symbolicKey: String { AnyContentDigest.sha256(material) }

        public static func == (lhs: Self, rhs: Self) -> Bool { lhs.material == rhs.material }
        public func hash(into hasher: inout Hasher) { hasher.combine(material) }
    }

    public struct Mapping: Sendable {
        public let source: Identity
        public let destinationReference: String
        public init(source: Identity, destinationReference: String) {
            self.source = source; self.destinationReference = destinationReference
        }
    }

    public struct MappingDecision: Sendable {
        public enum Status: String, Sendable {
            case missing, proposedReferenceOnly, unboundSource, ambiguousSource, aliasedDestination
        }
        public let source: Identity
        public let destinationReference: String?
        public let status: Status
    }

    public struct Location: Equatable, Sendable {
        public let entryPath: String
        public let jsonPointer: String
    }

    public struct Payload: Sendable {
        public enum Classification: String, Sendable {
            case withinPreparedInlineByteBound, requiresOtherFileStorage, remoteOnly, missing
        }
        public let path: String?
        public let byteCount: Int?
        public let sha256: String?
        public let classification: Classification
    }

    public struct Entity: Sendable {
        public enum Disposition: String, Sendable {
            case requiresConversion, unsupportedSourceKind, requiresMapping
            case proposedReferenceOnly, unresolvedSourceIdentity
        }
        public let identity: Identity
        public let locations: [Location]
        /// Exact inspected typed values. Original bytes remain in archive.
        public let sourceValues: [AnyJSON]
        /// Source references only. This is not a native execution order.
        public let references: [Identity]
        public let parent: Identity?
        public let order: Int?
        public let payload: Payload?
        public let disposition: Disposition
        public let proposedDestinationReference: String?

        fileprivate func mapped(_ decision: MappingDecision) -> Self {
            let proposed = decision.status == .proposedReferenceOnly
            return Self(identity: identity, locations: locations, sourceValues: sourceValues,
                        references: references, parent: parent, order: order, payload: payload,
                        disposition: disposition == .unresolvedSourceIdentity ? .unresolvedSourceIdentity :
                            (proposed ? .proposedReferenceOnly : .requiresMapping),
                        proposedDestinationReference: proposed ? decision.destinationReference : nil)
        }
    }

    public struct RetainedEntry: Sendable {
        public let path: String
        public let byteCount: Int
        public let sha256: String
        public let identities: [Identity]
    }

    public struct Issue: Equatable, Sendable {
        public enum Code: String, Sendable {
            case mappingRequired, destinationReferenceUnverified, unboundMapping
            case ambiguousTypeIdentity, aliasedDestinationReference
            case sourceTypeDefinitionMissing, sourceTypeIdentityMissing
            case propertyIdentityUnresolved, propertyValueMissing, propertyConversionRequired
            case blockConversionRequired, unsupportedObjectKind
            case fileOwnerMappingRequired, inlineFileConversionRequired
            case fileStorageUnsupported, remoteFileRecoveryRequired, missingFileBytes
        }
        public let code: Code
        public let identity: Identity
    }

    public struct Coverage: Sendable {
        public let entitiesByKind: [Identity.Kind: Int]
        public let retainedEntryCount: Int
        public let retainedByteCount: Int
        public let suppliedMappingCount: Int
    }

    public static let maximumEntities = 300_000
    public static let maximumMappings = 60_000
    public let archive: AnyHeartSpaceArchive
    public let destination: AnyTorahWorkspace
    public let entities: [Entity]
    public let entries: [RetainedEntry]
    public let mappingDecisions: [MappingDecision]
    public let issues: [Issue]
    /// Every original inspection issue is retained, even after a mapping is
    /// proposed. A caller-supplied native sidecar is never source admission.
    public let inspectionIssues: [AnyHeartSpaceArchive.Issue]
    public let coverage: Coverage
    public let planSHA256: String
    public var permitsDestinationWrites: Bool { false }
    public var hasNativeSourceAdmission: Bool { false }

    public init(archive: AnyHeartSpaceArchive, destination: AnyTorahWorkspace,
                mappings: [Mapping] = []) throws {
        guard mappings.count <= Self.maximumMappings else { throw AnyHeartSpaceDryRunError.limit }
        var rows: [Identity: Entity] = [:], issues: [Issue] = []
        let space = archive.sourceSpaceID
        func identity(_ kind: Identity.Kind, _ id: String, owner: String? = nil) -> Identity {
            Identity(kind: kind, sourceSpaceID: space, sourceObjectID: owner, sourceID: id)
        }
        func add(_ id: Identity, locations: [Location], values: [AnyJSON] = [],
                 references: [Identity] = [], parent: Identity? = nil, order: Int? = nil,
                 payload: Payload? = nil, disposition: Entity.Disposition) throws {
            guard rows.count < Self.maximumEntities else { throw AnyHeartSpaceDryRunError.limit }
            guard rows[id] == nil else { throw AnyHeartSpaceDryRunError.identityCollision(id.symbolicKey) }
            rows[id] = Entity(identity: id, locations: locations, sourceValues: values,
                              references: references.sorted(by: Self.identityOrder), parent: parent,
                              order: order, payload: payload, disposition: disposition,
                              proposedDestinationReference: nil)
        }
        func issue(_ code: Issue.Code, _ id: Identity) { issues.append(Issue(code: code, identity: id)) }
        func location(_ path: String, _ pointer: String = "") -> Location {
            Location(entryPath: path, jsonPointer: pointer)
        }

        var typeSources: [Data: TypeSource] = [:]
        var propertyKeys: [Data: String] = [:]
        var propertyUses: [Data: [Identity]] = [:]
        let definitions = Dictionary(uniqueKeysWithValues: archive.properties.map { (Data($0.internalKey.utf8), $0) })
        let definitionOffsets = Dictionary(uniqueKeysWithValues: archive.properties.enumerated().map {
            (Data($0.element.internalKey.utf8), $0.offset)
        })
        let unsupportedBlockPaths = Set(archive.issues.filter { $0.code == .unsupportedBlockType }
            .map { Data($0.path.utf8) })
        for property in archive.properties { propertyKeys[Data(property.internalKey.utf8)] = property.internalKey }
        let dictionaryPath = archive.index["manifest"]?["properties"]?.string
        let byPath = Dictionary(uniqueKeysWithValues: archive.originalEntries.map { ($0.path, $0) })

        for object in archive.objects {
            let objectID = identity(.object, object.sourceID)
            let typeID: Identity
            if let key = object.typeInternalKey {
                typeID = identity(.type, key)
                let bytes = Data(key.utf8)
                var item = typeSources[bytes] ?? TypeSource(key: key)
                item.locations.append(location(object.path, "/type_internal_key"))
                typeSources[bytes] = item
            } else {
                typeID = identity(.objectType, object.sourceID)
                try add(typeID, locations: [location(object.path, "/type")],
                        values: object.native["type"].map { [$0] } ?? [],
                        references: [objectID], disposition: .requiresMapping)
            }
            try add(objectID, locations: [location(object.path)], values: [object.native],
                    references: [typeID],
                    disposition: object.kind == "page" ? .requiresConversion : .unsupportedSourceKind)
            if object.kind != "page" { issue(.unsupportedObjectKind, objectID) }
            if object.kind == "object_type" {
                if let key = object.native["internal_key"]?.string, !key.isEmpty {
                    let bytes = Data(key.utf8)
                    var item = typeSources[bytes] ?? TypeSource(key: key)
                    item.locations.append(location(object.path, "/internal_key"))
                    item.definitions.append(objectID); item.values.append(object.native)
                    typeSources[bytes] = item
                } else { issue(.sourceTypeIdentityMissing, objectID) }
            }
            for block in object.blocks {
                let id = identity(.block, block.sourceID, owner: object.sourceID)
                let parent = block.parentSourceID.map { identity(.block, $0, owner: object.sourceID) } ?? objectID
                let blockPointer = "/blocks/" + String(block.order)
                let unsupported = unsupportedBlockPaths.contains(Data((object.path + blockPointer).utf8))
                try add(id, locations: [location(object.path, blockPointer)],
                        values: [block.native], references: parent == objectID ? [objectID] : [objectID, parent],
                        parent: parent, order: block.order,
                        disposition: unsupported ? .unsupportedSourceKind : .requiresConversion)
                issue(.blockConversionRequired, id)
            }
            let values = object.native["properties"]?.object ?? [:]
            let legend = object.native["property_internal_keys"]?.object ?? [:]
            var spellings: [Data: String] = [:]
            for key in Array(values.keys) + Array(legend.keys) { spellings[Data(key.utf8)] = key }
            for spelling in spellings.values.sorted(by: Self.stringOrder) {
                let id = identity(.propertyUse, spelling, owner: object.sourceID)
                let declaredKey = legend[spelling]?.string
                // Swift String dictionary equality is canonically equivalent.
                // A native internal-key reference must match the original UTF-8.
                let resolvedKey = object.propertyInternalKeys[spelling].flatMap {
                    definitions[Data($0.utf8)] == nil ? nil : $0
                }
                let sourceKey = resolvedKey ?? declaredKey
                var references = [objectID]
                if let key = sourceKey {
                    let bytes = Data(key.utf8)
                    propertyKeys[bytes] = key
                    propertyUses[bytes, default: []].append(id)
                    references.append(identity(.property, key))
                }
                var locations: [Location] = []
                if values[spelling] != nil { locations.append(location(object.path, "/properties/" + Self.pointer(spelling))) }
                if legend[spelling] != nil { locations.append(location(object.path, "/property_internal_keys/" + Self.pointer(spelling))) }
                try add(id, locations: locations, values: values[spelling].map { [$0] } ?? [],
                        references: references,
                        disposition: resolvedKey == nil ? .unresolvedSourceIdentity : .requiresConversion)
                if resolvedKey == nil { issue(.propertyIdentityUnresolved, id) }
                if values[spelling] == nil { issue(.propertyValueMissing, id) }
                else { issue(.propertyConversionRequired, id) }
            }
            if object.kind == "file" || object.kind == "file_object" {
                let id = identity(.file, object.sourceID)
                let payload: Payload
                var locations = [location(object.path)]
                if let path = archive.filePathsByObjectID[object.sourceID],
                   let entry = byPath[path], let digest = archive.entrySHA256[path] {
                    let inline = entry.bytes.count < 4096
                    payload = Payload(path: path, byteCount: entry.bytes.count, sha256: digest,
                                      classification: inline ? .withinPreparedInlineByteBound : .requiresOtherFileStorage)
                    locations.append(location(path))
                    issue(inline ? .inlineFileConversionRequired : .fileStorageUnsupported, id)
                } else if object.native["file_remote"] != nil {
                    payload = Payload(path: nil, byteCount: nil, sha256: nil, classification: .remoteOnly)
                    issue(.remoteFileRecoveryRequired, id)
                } else {
                    payload = Payload(path: nil, byteCount: nil, sha256: nil, classification: .missing)
                    issue(.missingFileBytes, id)
                }
                try add(id, locations: locations, values: [object.native], references: [objectID],
                        payload: payload, disposition: .requiresConversion)
                // The file object's identity is not an inferred native owner.
                issue(.fileOwnerMappingRequired, id)
            }
        }

        var ambiguousTypes = Set<Identity>()
        for item in typeSources.values.sorted(by: { Self.stringOrder($0.key, $1.key) }) {
            let id = identity(.type, item.key)
            try add(id, locations: item.locations, values: item.values,
                    references: item.definitions, disposition: .requiresMapping)
            if item.definitions.count > 1 {
                ambiguousTypes.insert(id); issue(.ambiguousTypeIdentity, id)
            } else if item.definitions.isEmpty { issue(.sourceTypeDefinitionMissing, id) }
        }
        for key in propertyKeys.values.sorted(by: Self.stringOrder) {
            let bytes = Data(key.utf8), id = identity(.property, key)
            let definition = definitions[bytes]
            // An unresolved legend identity still has an explicit inventory row.
            var locations: [Location] = []
            if let path = dictionaryPath, definition != nil, let offset = definitionOffsets[bytes] {
                locations.append(location(path, "/properties/" + String(offset)))
            }
            let uses = propertyUses[bytes] ?? []
            if definition == nil {
                locations += uses.flatMap { rows[$0]?.locations ?? [] }
                issue(.propertyIdentityUnresolved, id)
            }
            try add(id, locations: locations, values: definition.map { [$0.native] } ?? [],
                    references: uses, disposition: definition == nil ? .unresolvedSourceIdentity : .requiresMapping)
        }

        var supplied: [Identity: Mapping] = [:]
        var targets: [Data: [Identity]] = [:]
        for mapping in mappings {
            let id = mapping.source
            guard [.type, .objectType, .property].contains(id.kind), id.sourceObjectID == nil,
                  Data(id.sourceSpaceID.utf8) == Data(space.utf8),
                  Self.validReference(id.sourceID), Self.validReference(mapping.destinationReference) else {
                throw AnyHeartSpaceDryRunError.invalidMapping(id.symbolicKey)
            }
            guard supplied[id] == nil else { throw AnyHeartSpaceDryRunError.duplicateMapping(id.symbolicKey) }
            supplied[id] = mapping
            // Assigning the same ordinary type to several untyped objects is
            // expected. Merging distinct schema identities requires review.
            if id.kind != .objectType {
                targets[Self.material([id.kind.rawValue, mapping.destinationReference]), default: []].append(id)
            }
        }
        let aliased = Set(targets.values.filter { $0.count > 1 }.flatMap { $0 })
        let mappable = Set(rows.keys.filter { [.type, .objectType, .property].contains($0.kind) })
        var decisions: [MappingDecision] = []
        for id in mappable.union(supplied.keys).sorted(by: Self.identityOrder) {
            let proposed = supplied[id]?.destinationReference
            let status: MappingDecision.Status
            if rows[id] == nil { status = .unboundSource; issue(.unboundMapping, id) }
            else if ambiguousTypes.contains(id) { status = .ambiguousSource; issue(.mappingRequired, id) }
            else if aliased.contains(id) { status = .aliasedDestination; issue(.aliasedDestinationReference, id) }
            else if proposed == nil { status = .missing; issue(.mappingRequired, id) }
            else { status = .proposedReferenceOnly; issue(.destinationReferenceUnverified, id) }
            let decision = MappingDecision(source: id, destinationReference: proposed, status: status)
            decisions.append(decision)
            if let row = rows[id] { rows[id] = row.mapped(decision) }
        }

        let entities = rows.values.sorted { Self.identityOrder($0.identity, $1.identity) }
        var locations: [Data: Set<Identity>] = [:]
        for row in entities {
            for location in row.locations {
                locations[Data(location.entryPath.utf8), default: []].insert(row.identity)
            }
        }
        var entries: [RetainedEntry] = []
        for entry in archive.originalEntries {
            guard let hash = archive.entrySHA256[entry.path] else {
                throw AnyHeartSpaceDryRunError.identityCollision("missing inspected entry digest")
            }
            entries.append(RetainedEntry(path: entry.path, byteCount: entry.bytes.count, sha256: hash,
                identities: (locations[Data(entry.path.utf8)] ?? []).sorted(by: Self.identityOrder)))
        }
        let orderedMappings = mappings.sorted {
            if $0.source != $1.source { return Self.identityOrder($0.source, $1.source) }
            return Self.stringOrder($0.destinationReference, $1.destinationReference)
        }
        let binding = ["pinkha-heart-space-migration-dry-run/v1", archive.contentSHA256,
                       destination.accountID, destination.spaceID] +
            orderedMappings.flatMap { [$0.source.symbolicKey, $0.destinationReference] }
        self.archive = archive; self.destination = destination
        self.entities = entities; self.entries = entries
        self.mappingDecisions = decisions
        self.issues = issues.sorted {
            if $0.identity != $1.identity { return Self.identityOrder($0.identity, $1.identity) }
            return $0.code.rawValue < $1.code.rawValue
        }
        self.inspectionIssues = archive.issues
        self.coverage = Coverage(entitiesByKind: Dictionary(grouping: entities, by: { $0.identity.kind }).mapValues(\.count),
            retainedEntryCount: entries.count, retainedByteCount: entries.reduce(0) { $0 + $1.byteCount },
            suppliedMappingCount: mappings.count)
        self.planSHA256 = AnyContentDigest.sha256(Self.material(binding))
    }

    private struct TypeSource {
        let key: String
        var locations: [Location] = []
        var definitions: [Identity] = []
        var values: [AnyJSON] = []
    }

    private static func validReference(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 &&
        value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }
    private static func pointer(_ value: String) -> String {
        value.replacingOccurrences(of: "~", with: "~0").replacingOccurrences(of: "/", with: "~1")
    }
    private static func stringOrder(_ lhs: String, _ rhs: String) -> Bool {
        Data(lhs.utf8).lexicographicallyPrecedes(Data(rhs.utf8))
    }
    private static func identityOrder(_ lhs: Identity, _ rhs: Identity) -> Bool {
        lhs.material.lexicographicallyPrecedes(rhs.material)
    }
    private static func material(_ values: [String]) -> Data {
        Data(values.map { "\($0.utf8.count):\($0)" }.joined(separator: "|").utf8)
    }
}
