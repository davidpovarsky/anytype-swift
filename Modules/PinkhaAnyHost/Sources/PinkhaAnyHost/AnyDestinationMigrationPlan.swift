import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyDestinationMigrationError: Error, Equatable, Sendable {
    case invalidPlan(String)
    case incompleteCoverage(String)
    case unknownReference(String)
    case changedPlan
    case changedIdentity(String)
    case changedSource
    case journalUnavailable
    case journalCorrupt
    case alreadyExecuting
    case nativeTerminal(String, String)
    case unsupportedCapability(String)
    case payloadMismatch(String)
}

/// The outer native capture owns these identities. Per-object JSON alone
/// cannot establish an account, source checkpoint or complete source census.
public struct AnyDestinationSourceBinding: Codable, Equatable, Sendable {
    public let accountID: String
    public let spaceID: String
    public let witnessSHA256: String
    public let captureManifestSHA256: String
    public let semanticPlanSHA256: String
    public let sourceObjectIDs: [String]

    public init(accountID: String, spaceID: String, witnessSHA256: String,
                captureManifestSHA256: String, semanticPlanSHA256: String,
                sourceObjectIDs: [String]) throws {
        guard AnyDestinationPlanChecks.identity(accountID), AnyDestinationPlanChecks.identity(spaceID),
              [witnessSHA256, captureManifestSHA256, semanticPlanSHA256].allSatisfy(AnyDestinationPlanChecks.digest),
              !sourceObjectIDs.isEmpty, sourceObjectIDs.count <= AnyDestinationMigrationPlan.maximumItems,
              sourceObjectIDs.allSatisfy(AnyDestinationPlanChecks.identity),
              Set(sourceObjectIDs.map { Data($0.utf8) }).count == sourceObjectIDs.count else {
            throw AnyDestinationMigrationError.invalidPlan("source binding")
        }
        self.accountID = accountID; self.spaceID = spaceID; self.witnessSHA256 = witnessSHA256
        self.captureManifestSHA256 = captureManifestSHA256; self.semanticPlanSHA256 = semanticPlanSHA256
        self.sourceObjectIDs = sourceObjectIDs
    }

    private enum CodingKeys: String, CodingKey {
        case accountID, spaceID, witnessSHA256, captureManifestSHA256, semanticPlanSHA256, sourceObjectIDs
    }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(accountID: c.decode(String.self, forKey: .accountID),
                      spaceID: c.decode(String.self, forKey: .spaceID),
                      witnessSHA256: c.decode(String.self, forKey: .witnessSHA256),
                      captureManifestSHA256: c.decode(String.self, forKey: .captureManifestSHA256),
                      semanticPlanSHA256: c.decode(String.self, forKey: .semanticPlanSHA256),
                      sourceObjectIDs: c.decode([String].self, forKey: .sourceObjectIDs))
    }
}

/// A reference is explicit, including references used as property-map keys.
/// No text scanning, title matching, normalized identity lookup or replacement
/// of a source ID embedded in an arbitrary string is performed by the executor.
public enum AnyDestinationReference: Codable, Equatable, Sendable {
    public enum Slot: Codable, Equatable, Sendable {
        case objectID
        case record(index: Int)
        case fileID
    }
    public enum Encoding: String, Codable, Sendable { case rawID, anyURI }
    case native(String)
    case mapped(sourceKey: String, slot: Slot, encoding: Encoding)
}

public struct AnyDestinationField: Codable, Equatable, Sendable {
    public let key: AnyDestinationReference
    public let value: AnyDestinationValue
    public init(key: AnyDestinationReference, value: AnyDestinationValue) {
        self.key = key; self.value = value
    }
}

public indirect enum AnyDestinationValue: Codable, Equatable, Sendable {
    /// Literal JSON contains no identity substitution. The semantic mapper must
    /// represent every identity it intends to translate with `reference`.
    case literal(AnyJSON)
    case reference(AnyDestinationReference)
    case array([AnyDestinationValue])
    case object([AnyDestinationField])
}

public struct AnyDestinationRootDefinition: Codable, Equatable, Sendable {
    public let xKey: String
    public let name: String
    public let description: String
    public let iconCID: String
    public let layout: AnyDestinationValue?
    public let hidden: Bool
    public let meta: AnyDestinationValue
    public init(xKey: String, name: String, description: String = "", iconCID: String = "",
                layout: AnyDestinationValue? = nil, hidden: Bool = false,
                meta: AnyDestinationValue = .literal(.object([:]))) {
        self.xKey = xKey; self.name = name; self.description = description; self.iconCID = iconCID
        self.layout = layout; self.hidden = hidden; self.meta = meta
    }
}

/// Draft values are inert until the validated enclosing plan is constructed.
/// The order is definitions, objects, blocks, files, then property updates.
/// Every ordinary object identity therefore exists before a reference cycle is
/// committed, without changing its immutable creation specification.
public enum AnyDestinationMigrationOperation: Codable, Equatable, Sendable {
    case typeDefinition(AnyDestinationRootDefinition)
    case collectionDefinition(AnyDestinationRootDefinition)
    case propertyDefinition(owner: AnyDestinationReference, kind: String, name: String,
                            xKey: String, description: String, scope: String,
                            xFormat: AnyDestinationValue?, index: String?)
    case partDefinition(owner: AnyDestinationReference, draft: AnyDestinationValue)
    case object(type: AnyDestinationReference, collections: [AnyDestinationReference],
                initialProperties: AnyDestinationValue)
    case editorBlock(owner: AnyDestinationReference, dataset: String, type: String, text: String,
                     style: AnyDestinationValue, parent: AnyDestinationReference?, position: String)
    /// The locator and bytes are supplied separately. The immutable plan binds
    /// byte count and plaintext digest. All variants require separate items.
    case file(owner: AnyDestinationReference, name: String, mime: String,
              size: Int64, contentSHA256: String)
    /// One SET group per object/owner. The original revision is read and
    /// durably recorded by the executor before the first preparation request.
    case propertyUpdate(object: AnyDestinationReference, owner: AnyDestinationReference,
                        patch: AnyDestinationValue)

    var phase: Int {
        switch self {
        case .typeDefinition, .collectionDefinition, .propertyDefinition, .partDefinition: 0
        case .object: 1
        case .editorBlock: 2
        case .file: 3
        case .propertyUpdate: 4
        }
    }
    var kind: String {
        switch self {
        case .typeDefinition: "typeDefinition"
        case .collectionDefinition: "collectionDefinition"
        case .propertyDefinition: "propertyDefinition"
        case .partDefinition: "partDefinition"
        case .object: "object"
        case .editorBlock: "editorBlock"
        case .file(_, _, _, let size, _): size < 4096 ? "inlineFile" : "file"
        case .propertyUpdate: "propertyUpdate"
        }
    }
}

public struct AnyDestinationMigrationItem: Codable, Equatable, Sendable {
    public let sourceKey: String
    public let sourceObjectID: String
    public let expectedRecordCount: Int
    public let operation: AnyDestinationMigrationOperation
    public init(sourceKey: String, sourceObjectID: String, expectedRecordCount: Int = 1,
                operation: AnyDestinationMigrationOperation) {
        self.sourceKey = sourceKey; self.sourceObjectID = sourceObjectID
        self.expectedRecordCount = expectedRecordCount; self.operation = operation
    }
}

public struct AnyDestinationCoverage: Codable, Equatable, Sendable {
    /// These closed native-system cases preserve the original witness. A
    /// nonempty KV store, settings object, history or unknown application
    /// object cannot be silently placed in this category.
    public enum SystemKind: String, Codable, Sendable { case nativeACL, emptyNativeKeyValue }
    public enum Disposition: Codable, Equatable, Sendable {
        case mapped(itemSourceKeys: [String])
        case retainedSystem(kind: SystemKind, capturedRowCount: Int, witnessSHA256: String)
        case blocked(reasons: [String])
    }
    public let sourceObjectID: String
    public let disposition: Disposition
    public init(sourceObjectID: String, disposition: Disposition) {
        self.sourceObjectID = sourceObjectID; self.disposition = disposition
    }
}

/// A fully bound, bounded destination plan. A logical plan ID is stable; its
/// SHA binds the exact UTF-8 identities, source checkpoint, coverage and all
/// operation bytes. Decoding always reconstructs and validates this value.
public struct AnyDestinationMigrationPlan: Codable, Sendable {
    public static let version = "pinkha-destination-migration-plan-v1"
    public static let maximumItems = 100_000
    public static let maximumPlanBytes = 32 * 1024 * 1024
    public let source: AnyDestinationSourceBinding
    public let binding: AnyPreparedMigrationPlanBinding
    public let coverage: [AnyDestinationCoverage]
    public let items: [AnyDestinationMigrationItem]
    public let canonicalBytes: Data

    private struct Target: Codable {
        let accountID: String
        let spaceID: String
        let storeID: String
        let planID: String
    }
    private struct Content: Codable {
        let version: String
        let source: AnyDestinationSourceBinding
        let target: Target
        let coverage: [AnyDestinationCoverage]
        let items: [AnyDestinationMigrationItem]
    }

    public init(source: AnyDestinationSourceBinding, workspace: AnyTorahWorkspace,
                storeID: String, planID: String, coverage: [AnyDestinationCoverage],
                items: [AnyDestinationMigrationItem]) throws {
        let provisional = try AnyPreparedMigrationPlanBinding(workspace: workspace, storeID: storeID,
            planID: planID, planSHA256: String(repeating: "0", count: 64))
        try Self.validate(source: source, coverage: coverage, items: items, provisional: provisional)
        let content = Content(version: Self.version, source: source,
            target: Target(accountID: workspace.accountID, spaceID: workspace.spaceID, storeID: storeID, planID: planID),
            coverage: coverage, items: items)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(content)
        guard bytes.count <= Self.maximumPlanBytes else { throw AnyDestinationMigrationError.invalidPlan("plan size") }
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        self.source = source; self.coverage = coverage; self.items = items; self.canonicalBytes = bytes
        self.binding = try .init(workspace: workspace, storeID: storeID, planID: planID,
                                 planSHA256: AnyContentDigest.sha256(bytes))
    }

    private enum CodingKeys: String, CodingKey { case content, planSHA256 }
    public func encode(to encoder: any Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(JSONDecoder().decode(Content.self, from: canonicalBytes), forKey: .content)
        try c.encode(binding.planSHA256, forKey: .planSHA256)
    }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let content = try c.decode(Content.self, forKey: .content)
        guard content.version == Self.version else { throw AnyDestinationMigrationError.invalidPlan("version") }
        let target = content.target
        try self.init(source: content.source,
            workspace: .init(accountID: target.accountID, spaceID: target.spaceID),
            storeID: target.storeID, planID: target.planID, coverage: content.coverage, items: content.items)
        guard try c.decode(String.self, forKey: .planSHA256) == binding.planSHA256 else {
            throw AnyDestinationMigrationError.changedPlan
        }
    }

    /// Use this entry point for untrusted persisted or transported JSON. It
    /// also rejects duplicate/colliding keys and lossy numeric representations.
    public static func decode(_ data: Data) throws -> Self {
        guard data.count <= Self.maximumPlanBytes + 1024 else { throw AnyDestinationMigrationError.invalidPlan("plan size") }
        let value = try JSONDecoder().decode(Self.self, from: data)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: data, encoded: encoder.encode(value))
        return value
    }

    public var blockers: [String] {
        coverage.flatMap { entry -> [String] in
            if case .blocked(let reasons) = entry.disposition { return reasons }
            return []
        }
    }

    func requireExecutable() throws {
        guard blockers.isEmpty else { throw AnyDestinationMigrationError.incompleteCoverage(blockers.joined(separator: "; ")) }
    }

    private static func validate(source: AnyDestinationSourceBinding, coverage: [AnyDestinationCoverage],
                                 items: [AnyDestinationMigrationItem], provisional: AnyPreparedMigrationPlanBinding) throws {
        guard !items.isEmpty, items.count <= maximumItems,
              coverage.count == source.sourceObjectIDs.count else {
            throw AnyDestinationMigrationError.invalidPlan("item or coverage count")
        }
        let sourceIDs = Set(source.sourceObjectIDs.map { Data($0.utf8) })
        var keys: [Data: Int] = [:]
        var lastPhase = 0
        var propertyGroups = Set<Data>()
        for (index, item) in items.enumerated() {
            guard AnyPreparedMigrationPlanBinding.validOpaque(item.sourceKey, maximum: 4096),
                  sourceIDs.contains(Data(item.sourceObjectID.utf8)),
                  keys[Data(item.sourceKey.utf8)] == nil,
                  (1...AnyPreparedDefinitionReceipt.maximumRecordIDs).contains(item.expectedRecordCount),
                  item.operation.phase >= lastPhase else {
                throw AnyDestinationMigrationError.invalidPlan("item identity/order")
            }
            if item.operation.kind != "partDefinition", item.expectedRecordCount != 1 {
                throw AnyDestinationMigrationError.invalidPlan("record count")
            }
            try item.operation.validateReferences { reference in
                try AnyDestinationPlanChecks.reference(reference)
                if case .mapped(let key, let slot, _) = reference {
                    guard let earlier = keys[Data(key.utf8)], earlier < index else {
                        throw AnyDestinationMigrationError.unknownReference(key)
                    }
                    let previous = items[earlier]
                    if case .record(let record) = slot, record >= previous.expectedRecordCount {
                        throw AnyDestinationMigrationError.invalidPlan("record reference bound")
                    }
                    if case .fileID = slot, previous.operation.kind != "file" && previous.operation.kind != "inlineFile" {
                        throw AnyDestinationMigrationError.invalidPlan("file reference kind")
                    }
                }
            }
            // Mutations may target only identities created by this plan. A
            // literal object ID in imported JSON cannot update an unrelated
            // existing destination object or mutate a preexisting schema.
            func mappedOwner(_ reference: AnyDestinationReference, kinds: Set<String>) throws {
                guard case .mapped(let key, .objectID, .rawID) = reference,
                      let owner = keys[Data(key.utf8)], kinds.contains(items[owner].operation.kind) else {
                    throw AnyDestinationMigrationError.invalidPlan("mutation owner must be created by this plan")
                }
            }
            switch item.operation {
            case .propertyDefinition(let owner, _, _, _, _, _, _, _), .partDefinition(let owner, _):
                try mappedOwner(owner, kinds: ["typeDefinition", "collectionDefinition"])
            case .editorBlock(let owner, _, _, _, _, _, _), .file(let owner, _, _, _, _):
                try mappedOwner(owner, kinds: ["object"])
            case .propertyUpdate(let object, let owner, let patch):
                try mappedOwner(object, kinds: ["object"])
                if case .native(let literal) = owner {
                    guard Data(literal.utf8) == Data("any".utf8) else {
                        throw AnyDestinationMigrationError.invalidPlan("property owner")
                    }
                } else { try mappedOwner(owner, kinds: ["typeDefinition", "collectionDefinition"]) }
                if case .mapped(let objectKey, _, _) = object,
                   let sourceIndex = keys[Data(objectKey.utf8)],
                   case .object(_, _, let initial) = items[sourceIndex].operation,
                   let created = try initial.resolved(AnyDestinationPlanChecks.placeholder).object,
                   let original = created[try AnyDestinationPlanChecks.placeholder(owner)]?.object,
                   let later = try patch.resolved(AnyDestinationPlanChecks.placeholder).object,
                   !Set(original.keys).isDisjoint(with: Set(later.keys)) {
                    throw AnyDestinationMigrationError.invalidPlan("property update replaces an immutable creation field")
                }
            default: break
            }
            // Run the existing production constructors against distinct inert
            // validation IDs. No source ID is submitted as a destination ID.
            try item.operation.validateShape(binding: provisional, sourceKey: item.sourceKey)
            if case .propertyUpdate(let object, let owner, _) = item.operation {
                let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
                let group = try encoder.encode([object, owner])
                guard propertyGroups.insert(group).inserted else {
                    throw AnyDestinationMigrationError.invalidPlan("duplicate property object/owner group")
                }
            }
            keys[Data(item.sourceKey.utf8)] = index; lastPhase = item.operation.phase
        }
        var covered = Set<Data>(), represented = Set<Data>()
        for entry in coverage {
            let id = Data(entry.sourceObjectID.utf8)
            guard sourceIDs.contains(id), covered.insert(id).inserted else {
                throw AnyDestinationMigrationError.invalidPlan("coverage identity")
            }
            switch entry.disposition {
            case .mapped(let itemKeys):
                guard !itemKeys.isEmpty else { throw AnyDestinationMigrationError.incompleteCoverage(entry.sourceObjectID) }
                for key in itemKeys {
                    let raw = Data(key.utf8)
                    guard let index = keys[raw], represented.insert(raw).inserted,
                          Data(items[index].sourceObjectID.utf8) == id else {
                        throw AnyDestinationMigrationError.invalidPlan("coverage mapping")
                    }
                }
            case .retainedSystem(let kind, let count, let witness):
                guard witness == source.witnessSHA256, count >= 0,
                      kind != .emptyNativeKeyValue || count == 0 else {
                    throw AnyDestinationMigrationError.invalidPlan("system preservation")
                }
            case .blocked(let reasons):
                guard !reasons.isEmpty, reasons.count <= 128,
                      reasons.allSatisfy({ AnyPreparedMigrationPlanBinding.validOpaque($0, maximum: 4096) }) else {
                    throw AnyDestinationMigrationError.invalidPlan("coverage blocker")
                }
            }
        }
        guard represented == Set(keys.keys) else { throw AnyDestinationMigrationError.invalidPlan("unaccounted operation") }
    }
}

enum AnyDestinationPlanChecks {
    static func identity(_ value: String) -> Bool {
        AnyPreparedMigrationPlanBinding.validOpaque(value, maximum: 4096)
    }
    static func digest(_ value: String) -> Bool { AnyNativeCreationIdentity.isHex(value, count: 64) }
    static func reference(_ value: AnyDestinationReference) throws {
        switch value {
        case .native(let id):
            guard identity(id), id.utf8.count <= 4096 else { throw AnyDestinationMigrationError.invalidPlan("literal key") }
        case .mapped(let sourceKey, let slot, _):
            guard identity(sourceKey) else { throw AnyDestinationMigrationError.invalidPlan("reference key") }
            if case .record(let index) = slot, !(0..<2048).contains(index) {
                throw AnyDestinationMigrationError.invalidPlan("reference slot")
            }
        }
    }
    static func placeholder(_ value: AnyDestinationReference) throws -> String {
        try reference(value)
        switch value {
        case .native(let value): return value
        case .mapped(let key, let slot, let encoding):
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            let token = AnyContentDigest.sha256(try encoder.encode(slot) + Data(key.utf8))
            return (encoding == .anyURI ? "any://" : "") + "validation-" + token
        }
    }
}

extension AnyDestinationValue {
    func references(_ visit: (AnyDestinationReference) throws -> Void, depth: Int = 0) throws {
        guard depth <= 32 else { throw AnyDestinationMigrationError.invalidPlan("value depth") }
        switch self {
        case .literal(let value):
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            let bytes = try encoder.encode(value)
            guard bytes.count <= 1_048_576 else { throw AnyDestinationMigrationError.invalidPlan("value size") }
            try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        case .reference(let reference): try visit(reference)
        case .array(let values):
            guard values.count <= 65_536 else { throw AnyDestinationMigrationError.invalidPlan("array bound") }
            for value in values { try value.references(visit, depth: depth + 1) }
        case .object(let fields):
            guard fields.count <= 65_536 else { throw AnyDestinationMigrationError.invalidPlan("field bound") }
            for field in fields { try visit(field.key); try field.value.references(visit, depth: depth + 1) }
        }
    }

    func resolved(_ resolve: (AnyDestinationReference) throws -> String) throws -> AnyJSON {
        switch self {
        case .literal(let value): return value
        case .reference(let reference): return .string(try resolve(reference))
        case .array(let values): return .array(try values.map { try $0.resolved(resolve) })
        case .object(let fields):
            var object: [String: AnyJSON] = [:]
            var bytes = Set<Data>()
            for field in fields {
                let key = try resolve(field.key)
                // Swift String dictionaries use canonical equivalence. Refuse
                // a collision rather than merging distinct UTF-8 field names.
                guard bytes.insert(Data(key.utf8)).inserted, object[key] == nil else {
                    throw AnyDestinationMigrationError.invalidPlan("resolved field collision")
                }
                object[key] = try field.value.resolved(resolve)
            }
            return .object(object)
        }
    }
}

extension AnyDestinationMigrationOperation {
    func validateReferences(_ visit: (AnyDestinationReference) throws -> Void) throws {
        switch self {
        case .typeDefinition(let seed), .collectionDefinition(let seed):
            try seed.meta.references(visit); try seed.layout?.references(visit)
        case .propertyDefinition(let owner, _, _, _, _, _, let format, _):
            try visit(owner); try format?.references(visit)
        case .partDefinition(let owner, let draft): try visit(owner); try draft.references(visit)
        case .object(let type, let collections, let properties):
            try visit(type); for collection in collections { try visit(collection) }; try properties.references(visit)
        case .editorBlock(let owner, _, _, _, let style, let parent, _):
            try visit(owner); if let parent { try visit(parent) }; try style.references(visit)
        case .file(let owner, _, _, _, _): try visit(owner)
        case .propertyUpdate(let object, let owner, let patch):
            try visit(object); try visit(owner); try patch.references(visit)
        }
    }

    func validateShape(binding: AnyPreparedMigrationPlanBinding, sourceKey: String) throws {
        let resolve = AnyDestinationPlanChecks.placeholder
        switch self {
        case .typeDefinition(let seed):
            _ = try AnyPreparedDefinitionIntent.type(binding: binding, sourceKey: sourceKey, xKey: seed.xKey,
                name: seed.name, description: seed.description, iconCID: seed.iconCID,
                layout: seed.layout?.resolved(resolve), hidden: seed.hidden, meta: seed.meta.resolved(resolve))
        case .collectionDefinition(let seed):
            guard seed.layout == nil else { throw AnyDestinationMigrationError.invalidPlan("collection layout") }
            _ = try AnyPreparedDefinitionIntent.collection(binding: binding, sourceKey: sourceKey, xKey: seed.xKey,
                name: seed.name, description: seed.description, iconCID: seed.iconCID,
                hidden: seed.hidden, meta: seed.meta.resolved(resolve))
        case .propertyDefinition(let owner, let kind, let name, let xKey, let description, let scope, let format, let index):
            guard let kind = AnyPreparedDefinitionIntent.PropertyKind(rawValue: kind),
                  let scope = AnyPreparedDefinitionIntent.PropertyScope(rawValue: scope) else {
                throw AnyDestinationMigrationError.invalidPlan("property vocabulary")
            }
            _ = try AnyPreparedDefinitionIntent.property(binding: binding, sourceKey: sourceKey, ownerID: resolve(owner),
                kind: kind, name: name, xKey: xKey, description: description, scope: scope,
                xFormat: format?.resolved(resolve), index: index)
        case .partDefinition(let owner, let draft):
            _ = try AnyPreparedDefinitionIntent.part(binding: binding, sourceKey: sourceKey,
                                                     ownerID: resolve(owner), draft: draft.resolved(resolve))
        case .object(let type, let collections, let properties):
            _ = try AnyPreparedMigrationIntent.object(binding: binding, sourceKey: sourceKey,
                typeID: resolve(type), collections: collections.map(resolve), initialProperties: properties.resolved(resolve))
        case .editorBlock(let owner, let dataset, let type, let text, let style, let parent, let position):
            _ = try AnyPreparedMigrationIntent.block(binding: binding, sourceKey: sourceKey, objectID: resolve(owner),
                dataset: dataset, type: type, text: text, style: style.resolved(resolve),
                parentID: parent.map(resolve) ?? "", position: position)
        case .file(let owner, let name, let mime, let size, let digest):
            guard (0...AnyPreparedFileIntent.maximumBytes).contains(size), AnyDestinationPlanChecks.digest(digest) else {
                throw AnyDestinationMigrationError.invalidPlan("file bounds")
            }
            _ = try AnyPreparedFileIntent(binding: binding, sourceKey: sourceKey, ownerObjectID: resolve(owner),
                name: name, mime: mime, size: max(4096, size), contentSHA256: digest)
        case .propertyUpdate(let object, let owner, let patch):
            guard let values = try patch.resolved(resolve).object else {
                throw AnyDestinationMigrationError.invalidPlan("property patch")
            }
            _ = try AnyPreparedPropertyUpdateIntent(binding: binding, sourceKey: sourceKey,
                objectID: resolve(object), ownerID: resolve(owner), patch: values, expectedApplySequence: 1)
        }
    }
}
