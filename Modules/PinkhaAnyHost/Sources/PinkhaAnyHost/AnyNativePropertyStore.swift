import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativePropertyError: Error, Equatable, Sendable {
    case invalidCatalog
    case invalidProperty
    case readOnly
    case changedDefinition
    case unavailableContract
    case unavailableDocumentType
    case presentationNotAttached
    /// The attachment was verified; the subsequent visibility CAS did not
    /// complete. Business values remain unchanged. Refresh before retry.
    case visibilityAttachmentCompleted
}

public struct AnyNativePropertyKey: Hashable, Sendable {
    public let ownerID: String
    public let propertyID: String
    public init(ownerID: String, propertyID: String) throws {
        guard AnyEditorBlock.validID(ownerID), AnyEditorBlock.validID(propertyID) else {
            throw AnyNativePropertyError.invalidProperty
        }
        self.ownerID = ownerID; self.propertyID = propertyID
    }
    /// Exact native IDs, length-framed to prevent separator/namespace ambiguity.
    public var visibilityKey: String {
        "property:v1:\(ownerID.utf8.count):\(ownerID):\(propertyID.utf8.count):\(propertyID)"
    }
}

public struct AnyNativePropertyVisibilityKey: Hashable, Sendable {
    public enum DerivedField: String, Sendable {
        case sources = "pinkhaSources", topics = "pinkhaTopics", words = "pinkhaWords"
    }
    public let rawValue: String
    let property: AnyNativePropertyKey?
    public init(property: AnyNativePropertyKey) {
        self.property = property; rawValue = property.visibilityKey
    }
    public init(derived field: DerivedField) {
        property = nil
        rawValue = "derived:v1:pinkha-torah-native-v1:" + field.rawValue
    }
}

/// Verified IDs supplied by hierarchy/Note composition, never display-name or
/// xKey guesses. Membership fields have dedicated operations.
public struct AnyNativePropertyPolicy: Equatable, Sendable {
    public let hiddenPropertyKeys: Set<AnyNativePropertyKey>
    public let managedPropertyKeys: Set<AnyNativePropertyKey>
    public let hiddenCollectionIDs: Set<String>
    public init(hiddenPropertyKeys: Set<AnyNativePropertyKey> = [],
                managedPropertyKeys: Set<AnyNativePropertyKey> = [],
                hiddenCollectionIDs: Set<String> = []) throws {
        guard hiddenCollectionIDs.allSatisfy(AnyEditorBlock.validID) else {
            throw AnyNativePropertyError.invalidProperty
        }
        self.hiddenPropertyKeys = hiddenPropertyKeys
        self.managedPropertyKeys = managedPropertyKeys
        self.hiddenCollectionIDs = hiddenCollectionIDs
    }
    func managed(_ key: AnyNativePropertyKey) -> Bool {
        managedPropertyKeys.contains(key) || hiddenCollectionIDs.contains(key.ownerID) ||
        key.ownerID == AnyNativePropertyStore.presentationCollectionID ||
        (key.ownerID == "any" && ["type", "collections", "template"].contains(key.propertyID))
    }
    public func isManagedCollection(_ id: String) -> Bool {
        hiddenCollectionIDs.contains(id) || managedPropertyKeys.contains(where: { $0.ownerID == id }) ||
        ["bin", "template", "miniapp", AnyNativePropertyStore.presentationCollectionID].contains(id)
    }
}

public struct AnyNativePropertyOwner: Equatable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let xKey: String?
    public let builtIn: Bool
    public let hidden: Bool
    public let documentEligible: Bool
    public let raw: AnyJSON
    public var isSelectableDocumentType: Bool {
        documentEligible && (!hidden || (builtIn && id == "page"))
    }
    init(raw: AnyJSON, documentEligible: Bool = false) throws {
        guard let id = raw["id"]?.string, AnyEditorBlock.validID(id),
              raw["name"] == nil || raw["name"]?.string != nil,
              raw["xKey"] == nil || raw["xKey"]?.string != nil,
              raw["builtIn"] == nil || raw["builtIn"]?.bool != nil,
              raw["hidden"] == nil || raw["hidden"]?.bool != nil else {
            throw AnyNativePropertyError.invalidCatalog
        }
        _ = try AnyHostCanonical.bytes(raw, maximumBytes: 131_072)
        self.id = id; self.name = raw["name"]?.string ?? id
        self.xKey = raw["xKey"]?.string; self.builtIn = raw["builtIn"]?.bool ?? false
        self.hidden = raw["hidden"]?.bool ?? false
        self.documentEligible = documentEligible; self.raw = raw
    }
}

public struct AnyNativePropertyCatalog: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let types: [AnyNativePropertyOwner]
    public let collections: [AnyNativePropertyOwner]
    public var selectableDocumentTypes: [AnyNativePropertyOwner] { types.filter(\.isSelectableDocumentType) }
    init(workspace: AnyTorahWorkspace, generation: UUID, engineStartedAt: String,
         types: [AnyNativePropertyOwner], collections: [AnyNativePropertyOwner]) throws {
        guard types.count <= 512, collections.count <= 512,
              Set(types.map(\.id)).count == types.count,
              Set(collections.map(\.id)).count == collections.count else {
            throw AnyNativePropertyError.invalidCatalog
        }
        // A compiled built-in may legitimately share a literal ID between the
        // type and collection catalogs; their two lists are not disjoint sets.
        self.workspace = workspace; self.generation = generation; self.engineStartedAt = engineStartedAt
        self.types = try AnyNativeImportedTypeOrder.arranged(types); self.collections = collections
    }
}

/// A read-only binding for creating a Bookmark with an already installed Type.
/// It is not write authority: callers still use the original creator, journal,
/// current member/lease checks, and native readback.
public struct AnyNativeBookmarkCreationBinding: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let typeID: String
    public let sourceURLKey: AnyNativePropertyKey
    private let definitionFingerprint: String

    public static func isCandidate(_ type: AnyNativePropertyOwner) -> Bool {
        type.isSelectableDocumentType && !type.builtIn &&
            type.raw["layout"]?["type"] == .string("bookmark") &&
            type.raw["layout"]?["config"]?["pinkhaHeart"]?["contract"] ==
                .string(AnyNativeImportedTypePresentation.bookmarkContract) &&
            type.raw["layout"]?["config"]?["pinkhaHeart"]?["sourceRecommendedLayout"] == .integer(11)
    }

    /// The existing Properties/Link policy, shared with creation. The original
    /// Anytype URL input validates first; storage retains the supplied text.
    public static func websiteURL(_ text: String) -> URL? {
        guard !text.isEmpty, text.utf8.count <= 8192,
              text == text.trimmingCharacters(in: .whitespacesAndNewlines),
              let parts = URLComponents(string: text),
              let scheme = parts.scheme?.lowercased(), ["http", "https"].contains(scheme),
              let host = parts.host, !host.isEmpty, parts.user == nil, parts.password == nil,
              let url = parts.url else { return nil }
        return url
    }

    init(catalog: AnyNativePropertyCatalog, typeID: String,
         definitions: [AnyNativePropertyDefinition], policy: AnyNativePropertyPolicy) throws {
        guard let type = catalog.types.first(where: { $0.id == typeID }), Self.isCandidate(type),
              let ownerID = type.raw["layout"]?["config"]?["pinkhaHeart"]?["propertyOwnerId"]?.string,
              let owner = catalog.collections.first(where: { $0.id == ownerID && !$0.builtIn }),
              !policy.isManagedCollection(ownerID), !policy.hiddenCollectionIDs.contains(ownerID),
              definitions.count <= 4096, Set(definitions.map(\.key)).count == definitions.count else {
            throw AnyNativePropertyError.invalidCatalog
        }
        let relevant = definitions.filter { ["any", typeID, ownerID].contains($0.key.ownerID) }
        // These are proposed memberships and empty new-object values, never a
        // fabricated current record. The original descriptor validator owns all
        // imported role/definition/layout checks.
        guard let presentation = try AnyNativeImportedTypePresentation(type: type, catalog: catalog,
            collectionIDs: [ownerID], definitions: relevant, raw: .object([:])),
              let key = presentation.sourceURLKey,
              !presentation.defaultHiddenKeys.contains(key.visibilityKey),
              !policy.hiddenPropertyKeys.contains(key), !policy.managed(key),
              key.ownerID != AnyNativePropertyStore.presentationCollectionID,
              relevant.contains(where: { $0.key.ownerID == "any" && $0.key.propertyID == "name" &&
                  $0.kind == .string && $0.scope == "synced" }) else {
            throw AnyNativePropertyError.readOnly
        }
        let proof: AnyJSON = .object([
            "type": type.raw, "owner": owner.raw,
            "definitions": .array(relevant.sorted {
                AnyNativePropertyStore.utf8Less($0.key.visibilityKey, $1.key.visibilityKey)
            }.map { .object(["ownerId": .string($0.key.ownerID), "definition": $0.raw]) })
        ])
        self.workspace = catalog.workspace; self.generation = catalog.generation
        self.engineStartedAt = catalog.engineStartedAt; self.typeID = typeID; self.sourceURLKey = key
        self.definitionFingerprint = AnyContentDigest.sha256(try AnyHostCanonical.bytes(proof, maximumBytes: 4_194_304))
    }

    public func requireMatching(_ current: Self) throws {
        guard workspace == current.workspace, generation == current.generation,
              engineStartedAt == current.engineStartedAt else { throw AnyHostError.wrongWorkspace }
        guard typeID == current.typeID, sourceURLKey == current.sourceURLKey,
              definitionFingerprint == current.definitionFingerprint else { throw AnyHostError.changedDocument }
    }

    /// Adds the source value exactly once, without a second Name/URL namespace,
    /// Note marker, preview metadata, schema mutation, or an editor block.
    public func makeIntent(frame: AnyNativeBookmarkCreationFrame,
                           mutationID: String, collections: [String],
                           initialProperties: AnyJSON, sourceURL: String) throws -> AnyNativeObjectCreationIntent {
        guard frame.workspace.accountID.utf8.elementsEqual(workspace.accountID.utf8),
              frame.workspace.spaceID.utf8.elementsEqual(workspace.spaceID.utf8),
              frame.typeID.utf8.elementsEqual(typeID.utf8),
              frame.propertyOwnerID.utf8.elementsEqual(sourceURLKey.ownerID.utf8),
              frame.propertyID.utf8.elementsEqual(sourceURLKey.propertyID.utf8),
              Self.websiteURL(sourceURL) != nil, !sourceURL.utf8.contains(0),
              var groups = initialProperties.object, groups[sourceURLKey.ownerID] == nil,
              Set(collections).count == collections.count,
              !collections.contains(sourceURLKey.ownerID),
              let name = groups["any"]?["name"]?.string,
              name.utf8.count <= 4096, !name.utf8.contains(0) else {
            throw AnyNativeCreationError.invalidIntent
        }
        guard frame.canWrite else { throw AnyNativePropertyError.readOnly }
        let expectedCollections = Set(collections + [sourceURLKey.ownerID]).sorted {
            $0.utf8.lexicographicallyPrecedes($1.utf8)
        }
        guard frame.collections.count == expectedCollections.count,
              zip(frame.collections, expectedCollections).allSatisfy({ $0.0.utf8.elementsEqual($0.1.utf8) }) else {
            throw AnyNativeCreationError.invalidIntent
        }
        groups[sourceURLKey.ownerID] = .object([sourceURLKey.propertyID: .string(sourceURL)])
        // Only the genuine native reader supplies this immutable frame. The
        // original creator rechecks capability/authority at eventual dispatch.
        return try frame.makeCreationIntent(mutationID: mutationID, initialProperties: .object(groups))
    }

    public func requireCreated(_ snapshot: AnyNativePropertySnapshot, intent: AnyNativeObjectCreationIntent,
                               objectID: String, policy: AnyNativePropertyPolicy) throws {
        guard intent.workspace == workspace, intent.typeID == typeID,
              intent.bookmarkDefinitionFrame != nil,
              snapshot.workspace == workspace, snapshot.objectID == objectID,
              snapshot.currentTypeID == typeID, snapshot.canWrite,
              Set(intent.collections).isSubset(of: Set(snapshot.collectionIDs)),
              let expected = intent.initialProperties[sourceURLKey.ownerID]?[sourceURLKey.propertyID]?.string,
              let actual = snapshot.bookmarkSourceRow?.value?.string,
              actual.utf8.elementsEqual(expected.utf8), snapshot.bookmarkSourceURL != nil,
              let expectedName = intent.initialProperties["any"]?["name"]?.string,
              let actualName = snapshot.raw["any"]?["name"]?.string,
              actualName.utf8.elementsEqual(expectedName.utf8) else {
            throw AnyNativeCreationError.createdObjectIncomplete(objectID)
        }
        let current = try Self(catalog: snapshot.catalog, typeID: snapshot.currentTypeID,
                               definitions: Array(snapshot.definitions.values), policy: policy)
        try requireMatching(current)
    }
}

public struct AnyNativePropertyDefinition: Equatable, Sendable {
    public enum Kind: String, Sendable { case string, number, boolean, null, array, object, datetime }
    public let key: AnyNativePropertyKey
    public let name: String
    public let kind: Kind?
    public let rawKind: String
    public let scope: String
    public let xFormat: AnyJSON?
    public let raw: AnyJSON
    public let importedDefaultMetadata: AnyNativeImportedDefaultMetadata?
    public let fileFormat: AnyNativeFilePropertyFormat?
    public var isSyncedWritableKind: Bool { scope == "synced" && kind != nil }
    init(ownerID: String, raw: AnyJSON) throws {
        guard let id = raw["id"]?.string, let kind = raw["kind"]?.string,
              !kind.isEmpty, kind.utf8.count <= 128,
              raw["name"] == nil || raw["name"]?.string != nil,
              raw["scope"] == nil || raw["scope"]?.string != nil else {
            throw AnyNativePropertyError.invalidProperty
        }
        _ = try AnyHostCanonical.bytes(raw, maximumBytes: 131_072)
        self.key = try .init(ownerID: ownerID, propertyID: id)
        self.name = raw["name"]?.string ?? id
        self.kind = Kind(rawValue: kind); self.rawKind = kind
        self.scope = raw["scope"]?.string ?? "synced"
        self.xFormat = raw["xFormat"]; self.raw = raw
        self.importedDefaultMetadata = try AnyNativeImportedDefaultMetadata(property: raw)
        self.fileFormat = try AnyNativeFilePropertyFormat(property: raw)
    }
    func accepts(_ value: AnyJSON) -> Bool {
        // Null is the native unset request; it is never a whole-record replace.
        if value == .null { return true }
        if let fileFormat { return (try? fileFormat.references(in: value)) != nil }
        switch kind {
        case .string: return value.string != nil
        case .number: return value.integer != nil || { if case .number(let n) = value { return n.isFinite }; return false }()
        case .boolean: return value.bool != nil
        case .array: return value.array != nil
        case .object: return value.object != nil
        case .datetime:
            guard let map = value.object, Set(map.keys) == ["$date"], let date = map["$date"] else { return false }
            return date.string != nil || date.integer != nil
        case .null, nil: return false
        }
    }
}

public struct AnyNativePropertyRow: Sendable, Identifiable {
    public var id: AnyNativePropertyKey { definition.key }
    public let definition: AnyNativePropertyDefinition
    public let value: AnyJSON?
    public let isReadOnly: Bool
    public let isVisible: Bool
}

public struct AnyNativePropertySnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let objectID: String
    public let generation: UUID
    public let fence: AnyConditionalPropertyFence
    public var engineStartedAt: String { fence.engineStartedAt }
    public var applySequence: Int64 { fence.applySequence }
    public let currentTypeID: String
    public let collectionIDs: [String]
    public let raw: AnyJSON
    public var nativeVersion: AnyJSON { fence.nativeVersion }
    public let catalog: AnyNativePropertyCatalog
    public let rows: [AnyNativePropertyRow]
    public let importedPresentation: AnyNativeImportedTypePresentation?
    /// The URL role is usable only through its verified, currently visible native row.
    public var bookmarkSourceRow: AnyNativePropertyRow? {
        guard let key = importedPresentation?.sourceURLKey else { return nil }
        return rows.first { $0.id == key && $0.isVisible }
    }
    /// Opening is a user action. Unsupported values remain unchanged in raw storage.
    public var bookmarkSourceURL: URL? {
        guard let text = bookmarkSourceRow?.value?.string else { return nil }
        return AnyNativeBookmarkCreationBinding.websiteURL(text)
    }
    /// Effective hidden keys: persisted keys (including unknown future keys),
    /// or explicit imported-Type defaults until preferences are first stored.
    /// A hide/show mutation composes from this set and carries the native version.
    public let hiddenPropertyKeys: Set<String>
    public let presentationAttached: Bool
    public let canWrite: Bool
    let definitions: [AnyNativePropertyKey: AnyNativePropertyDefinition]
}

public struct AnyPreparedPropertyEdit: Sendable {
    public let objectID: String
    public let ownerID: String
    public let patch: [String: AnyJSON]
    /// Copied unchanged from the caller's snapshot, including its original run.
    public let fence: AnyConditionalPropertyFence
    public var nativeVersion: AnyJSON { fence.nativeVersion }
    public var applySequence: Int64 { fence.applySequence }
    public var engineStartedAt: String { fence.engineStartedAt }
    public let generation: UUID
    let workspace: AnyTorahWorkspace
    let policy: AnyNativePropertyPolicy
    let expectedDefinitions: [AnyNativePropertyKey: AnyJSON]
    let typeDestination: String?
    let collectionDestination: String?
    let visibilityOnly: Bool
    let membershipOnly: Bool
    let inversePatch: [String: AnyJSON]

    /// A fresh read validates this prepared intent; it never supplies new tokens.
    func requireMatchingRecord(_ record: AnyJSON) throws {
        guard record["id"]?.string == objectID,
              record["spaceId"]?.string == workspace.spaceID,
              let current = try? AnyConditionalPropertyFence(
                record: record, engineStartedAt: engineStartedAt),
              current == fence else { throw AnyHostError.changedDocument }
    }
}

public struct AnyPropertyEditReceipt: Sendable {
    public enum Readback: String, Sendable {
        case verifiedCurrent
        case nativeAcceptedButCurrentStateUnverified
    }
    public let objectID: String
    public let readback: Readback
    public let snapshot: AnyNativePropertySnapshot?
    /// Available only after exact native-version readback; applying it remains a
    /// conditional write and refuses intervening changes.
    public let undo: AnyPreparedPropertyEdit?
}

public struct AnyNativePropertyStore: Sendable {
    public static let presentationCollectionID = "pinkha_presentation_v1"
    public static let hiddenPropertiesID = "hiddenProperties"
    public let workspace: AnyTorahWorkspace
    public let policy: AnyNativePropertyPolicy
    private let client: AnyHTTPClient
    private let documents: AnyNativeDocumentPolicyClient

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                policy: AnyNativePropertyPolicy) throws {
        guard client.expectedAccountID == workspace.accountID else { throw AnyHostError.wrongWorkspace }
        self.client = client; self.workspace = workspace; self.policy = policy
        self.documents = try .init(client: client, workspace: workspace)
    }

    /// Complete bounded display catalog. Each selectable Type has native
    /// canonical-editor proof; this result never grants future write authority.
    public func catalog(lease: AnyHostLease) async throws -> AnyNativePropertyCatalog {
        try await validate(lease)
        let caps = try await capabilities(lease: lease)
        try Self.requireCapability(caps, "nativeDocumentTypePolicy")
        async let typesResponse = client.requestJSON(method: "GET", path: spacePath + ["types"],
            query: ["includeHidden": "true"], authorize: { try await lease.validate() })
        async let collectionsResponse = client.requestJSON(method: "GET", path: spacePath + ["collections"],
            query: ["includeHidden": "true"], authorize: { try await lease.validate() })
        let (typeBody, collectionBody) = try await (typesResponse, collectionsResponse)
        guard let typeValues = typeBody["types"]?.array, let collectionValues = collectionBody["collections"]?.array,
              typeValues.count <= 512, collectionValues.count <= 512 else { throw AnyEngineError.readLimit }
        _ = try AnyHostCanonical.bytes(typeBody, maximumBytes: 4_194_304)
        _ = try AnyHostCanonical.bytes(collectionBody, maximumBytes: 4_194_304)
        let metadata = try typeValues.map { try AnyNativePropertyOwner(raw: $0) }
        var eligible: [String: Bool] = [:]
        // Bound concurrent requests and total work; no unbounded schema fanout.
        for start in stride(from: 0, to: metadata.count, by: 8) {
            let chunk = Array(metadata[start..<min(start + 8, metadata.count)])
            let batch = try await withThrowingTaskGroup(of: (String, Bool).self) { group in
                for entry in chunk {
                    group.addTask {
                        let proof = try await typeProof(entry.id, lease: lease)
                        return (entry.id, proof)
                    }
                }
                var values: [(String, Bool)] = []
                for try await item in group { values.append(item) }
                return values
            }
            for (id, value) in batch { eligible[id] = value }
        }
        let types = try metadata.map { try AnyNativePropertyOwner(raw: $0.raw, documentEligible: eligible[$0.id] == true) }
        let collections = try collectionValues.map { try AnyNativePropertyOwner(raw: $0) }
        try await validate(lease)
        return try .init(workspace: workspace, generation: lease.generation, engineStartedAt: lease.engineStartedAt,
                         types: types, collections: collections)
    }

    /// Read-only selection of an existing imported Bookmark schema. No missing
    /// Type, Collection or field is installed while the user opens or submits UI.
    public func bookmarkCreationBinding(typeID: String, lease: AnyHostLease) async throws -> AnyNativeBookmarkCreationBinding {
        try await validate(lease)
        let catalog = try await self.catalog(lease: lease)
        guard let type = catalog.types.first(where: { $0.id == typeID }),
              AnyNativeBookmarkCreationBinding.isCandidate(type),
              let ownerID = type.raw["layout"]?["config"]?["pinkhaHeart"]?["propertyOwnerId"]?.string,
              AnyEditorBlock.validID(ownerID),
              catalog.collections.contains(where: { $0.id == ownerID && !$0.builtIn }),
              !policy.isManagedCollection(ownerID), !policy.hiddenCollectionIDs.contains(ownerID) else {
            throw AnyNativePropertyError.unavailableDocumentType
        }
        var definitions = try await propertyDefinitions(ownerID: "any", collection: false, lease: lease)
        definitions += try await propertyDefinitions(ownerID: typeID, collection: false, lease: lease)
        definitions += try await propertyDefinitions(ownerID: ownerID, collection: true, lease: lease)
        let binding = try AnyNativeBookmarkCreationBinding(catalog: catalog, typeID: typeID,
                                                           definitions: definitions, policy: policy)
        try Task.checkCancellation()
        try await validate(lease)
        return binding
    }

    /// Raw namespaces and unknown/orphan values are retained. Definitions only
    /// describe controls; the native conditional route revalidates them at append.
    public func read(objectID: String, lease: AnyHostLease,
                     catalog providedCatalog: AnyNativePropertyCatalog? = nil) async throws -> AnyNativePropertySnapshot {
        try await validate(lease)
        guard AnyEditorBlock.validID(objectID) else { throw AnyNativePropertyError.invalidProperty }
        let catalog: AnyNativePropertyCatalog
        if let providedCatalog { catalog = providedCatalog }
        else { catalog = try await self.catalog(lease: lease) }
        guard catalog.workspace == workspace, catalog.generation == lease.generation,
              catalog.engineStartedAt == lease.engineStartedAt else { throw AnyHostError.wrongWorkspace }
        let caps = try await capabilities(lease: lease)
        try Self.requireCapability(caps, "nativeDocumentTypePolicy")
        for _ in 0..<3 {
            let target = try await targetProof(objectID, write: false, lease: lease)
            let first = try await record(objectID, lease: lease)
            let parts = try Self.membership(first)
            do { try target.requireMatchingRecord(first) }
            catch AnyNativeDocumentPolicyError.dependenciesChanged { continue }
            var definitions: [AnyNativePropertyDefinition] = []
            definitions += try await propertyDefinitions(ownerID: "any", collection: false, lease: lease)
            if parts.typeID != "any" {
                definitions += try await propertyDefinitions(ownerID: parts.typeID, collection: false, lease: lease)
            }
            for id in parts.collections {
                // A removed Collection declaration leaves its business values
                // stored. Such orphan data is visible through raw, never writable.
                do { definitions += try await propertyDefinitions(ownerID: id, collection: true, lease: lease) }
                catch AnyEngineError.http(let status, _) where status == 404 { continue }
            }
            guard definitions.count <= 4096 else { throw AnyEngineError.readLimit }
            if parts.collections.contains(Self.presentationCollectionID) {
                try await verifyPresentation(caps: caps, lease: lease)
            }
            let second = try await record(objectID, lease: lease)
            guard first == second else { continue }
            let finalTarget = try await targetProof(objectID, write: false, lease: lease)
            do { try finalTarget.requireMatchingRecord(second) }
            catch AnyNativeDocumentPolicyError.dependenciesChanged { continue }
            try await validate(lease)
            return try Self.materialize(raw: second, objectID: objectID, catalog: catalog,
                                        definitions: definitions, policy: policy,
                                        canWrite: finalTarget.canWrite)
        }
        throw AnyHostError.changedDocument
    }

    public func prepareSetValue(_ snapshot: AnyNativePropertySnapshot, key: AnyNativePropertyKey,
                                value: AnyJSON) throws -> AnyPreparedPropertyEdit {
        try validate(snapshot)
        guard let definition = snapshot.definitions[key], definition.isSyncedWritableKind,
              !policy.managed(key), !policy.hiddenPropertyKeys.contains(key) else {
            throw AnyNativePropertyError.readOnly
        }
        guard definition.accepts(value) else { throw AnyNativePropertyError.invalidProperty }
        _ = try AnyHostCanonical.bytes(value, maximumBytes: 131_072)
        return prepared(snapshot, ownerID: key.ownerID, patch: [key.propertyID: value],
                        expected: [key: definition.raw])
    }

    public func prepareSetType(_ snapshot: AnyNativePropertySnapshot,
                               typeID: String) throws -> AnyPreparedPropertyEdit {
        try validate(snapshot)
        guard snapshot.catalog.types.contains(where: { $0.id == typeID && $0.isSelectableDocumentType }) else {
            throw AnyNativePropertyError.unavailableDocumentType
        }
        let key = try AnyNativePropertyKey(ownerID: "any", propertyID: "type")
        guard let definition = snapshot.definitions[key], definition.isSyncedWritableKind else {
            throw AnyNativePropertyError.readOnly
        }
        return prepared(snapshot, ownerID: "any", patch: ["type": .string(typeID)],
            expected: [key: definition.raw], typeDestination: typeID, membershipOnly: true)
    }

    public func prepareAttachCollection(_ snapshot: AnyNativePropertySnapshot,
                                        collectionID: String) throws -> AnyPreparedPropertyEdit {
        try prepareMembership(snapshot, collectionID: collectionID, attach: true, presentation: false)
    }

    public func prepareDetachCollection(_ snapshot: AnyNativePropertySnapshot,
                                        collectionID: String) throws -> AnyPreparedPropertyEdit {
        try prepareMembership(snapshot, collectionID: collectionID, attach: false, presentation: false)
    }

    public func prepareVisibility(_ snapshot: AnyNativePropertySnapshot,
                                  key: AnyNativePropertyVisibilityKey,
                                  visible: Bool) throws -> AnyPreparedPropertyEdit {
        try validate(snapshot)
        guard snapshot.presentationAttached else { throw AnyNativePropertyError.presentationNotAttached }
        if let property = key.property {
            guard snapshot.definitions[property] != nil,
                  !policy.hiddenPropertyKeys.contains(property),
                  !policy.hiddenCollectionIDs.contains(property.ownerID),
                  property.ownerID != Self.presentationCollectionID else { throw AnyNativePropertyError.readOnly }
        }
        let preference = try AnyNativePropertyKey(ownerID: Self.presentationCollectionID, propertyID: Self.hiddenPropertiesID)
        guard let definition = snapshot.definitions[preference],
              definition.kind == .array, definition.scope == "synced" else {
            throw AnyNativePropertyError.unavailableContract
        }
        var keys = snapshot.hiddenPropertyKeys
        if visible { keys.remove(key.rawValue) } else { keys.insert(key.rawValue) }
        try Self.validateHiddenKeys(Array(keys))
        return prepared(snapshot, ownerID: preference.ownerID,
            patch: [preference.propertyID: .array(keys.sorted(by: Self.utf8Less).map(AnyJSON.string))],
            expected: [preference: definition.raw], visibilityOnly: true)
    }

    public func setVisibility(_ snapshot: AnyNativePropertySnapshot,
                              key: AnyNativePropertyVisibilityKey, visible: Bool,
                              lease: AnyHostLease,
                              authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyPropertyEditReceipt {
        try validate(snapshot)
        var current = snapshot
        var attached = false
        if !snapshot.presentationAttached {
            let caps = try await capabilities(lease: lease)
            try await verifyPresentation(caps: caps, lease: lease)
            let edit = try prepareMembership(snapshot, collectionID: Self.presentationCollectionID,
                                             attach: true, presentation: true)
            let receipt = try await apply(edit, lease: lease, authorize: authorize)
            guard receipt.readback == .verifiedCurrent, let after = receipt.snapshot else {
                throw AnyHostError.writeUncertain
            }
            current = after; attached = true
        }
        do { return try await apply(prepareVisibility(current, key: key, visible: visible),
                                    lease: lease, authorize: authorize) }
        catch {
            if attached { throw AnyNativePropertyError.visibilityAttachmentCompleted }
            throw error
        }
    }

    public func apply(_ edit: AnyPreparedPropertyEdit, lease: AnyHostLease,
                      authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyPropertyEditReceipt {
        try await authorize(); try await validate(lease)
        guard edit.workspace == workspace, edit.policy == policy, edit.generation == lease.generation,
              edit.engineStartedAt == lease.engineStartedAt else { throw AnyHostError.wrongWorkspace }
        let caps = try await capabilities(lease: lease)
        try Self.requireCapability(caps, "conditionalPropertiesSet")
        try Self.requireCapability(caps, "conditionalPropertiesApplySeq")
        try Self.requireCapability(caps, "conditionalMembershipSet")
        try Self.requireCapability(caps, "nativeDocumentTypePolicy")
        _ = try await targetProof(edit.objectID, write: true, lease: lease)
        if let type = edit.typeDestination {
            try Self.requireCapability(caps, "nativeDocumentMembership")
            guard try await typeProof(type, lease: lease) else { throw AnyNativePropertyError.unavailableDocumentType }
        }
        if edit.visibilityOnly || edit.collectionDestination == Self.presentationCollectionID {
            try await verifyPresentation(caps: caps, lease: lease)
        }
        // For ordinary custom owners, inspect current membership to choose the
        // exact definition surface; a catalog row alone cannot authorize it.
        let current = try await record(edit.objectID, lease: lease)
        try edit.requireMatchingRecord(current)
        let membership = try Self.membership(current)
        let isCollection = edit.ownerID != "any" && edit.ownerID != membership.typeID &&
            membership.collections.contains(edit.ownerID)
        let definitions = try await propertyDefinitions(ownerID: edit.ownerID, collection: isCollection, lease: lease)
        let currentDefs = Dictionary(uniqueKeysWithValues: definitions.map { ($0.key, $0.raw) })
        guard edit.expectedDefinitions.allSatisfy({ currentDefs[$0.key] == $0.value }) else {
            throw AnyNativePropertyError.changedDefinition
        }
        if let collection = edit.collectionDestination {
            _ = try await client.requestJSON(method: "GET", path: spacePath + ["collections", collection],
                authorize: { try await lease.validate() })
        }
        let result: AnyJSON
        do {
            result = try await client.requestJSON(method: "POST",
                path: spacePath + ["pinkha", "properties", edit.objectID, "set", edit.ownerID],
                body: edit.fence.requestBody(patch: edit.patch),
                authorize: { try await lease.validate(); try await authorize() })
        } catch AnyEngineError.http(let status, let code) where status == 409 &&
            ["pinkha.properties.conflict", "pinkha.properties.engine_restarted",
             "properties.conflict", "properties.engine_restarted"].contains(code) {
            throw AnyHostError.changedDocument
        } catch AnyEngineError.writeUncertain {
            throw AnyHostError.writeUncertain
        }
        let accepted = try Self.acceptedFence(result, original: edit.fence)
        let readback = try? await read(objectID: edit.objectID, lease: lease)
        try await validate(lease)
        return receipt(for: edit, accepted: accepted, readback: readback)
    }

    /// A success response without an exact native record fence cannot certify
    /// an already-dispatched write. Empty fenced no-ops are a separate workflow.
    static func acceptedFence(_ result: AnyJSON, original: AnyConditionalPropertyFence) throws -> AnyConditionalPropertyFence {
        guard result["engineStartedAt"]?.string == original.engineStartedAt,
              let version = result["propertiesVersion"], let sequence = result["applySeq"]?.integer,
              sequence > original.applySequence,
              let accepted = try? AnyConditionalPropertyFence(
                nativeVersion: version, applySequence: sequence, engineStartedAt: original.engineStartedAt) else {
            throw AnyHostError.writeUncertain
        }
        return accepted
    }

    /// Only the exact acknowledged snapshot can create an Undo. A later
    /// commutative update may leave _ver unchanged while changing _applySeq.
    func receipt(for edit: AnyPreparedPropertyEdit, accepted: AnyConditionalPropertyFence,
                 readback: AnyNativePropertySnapshot?) -> AnyPropertyEditReceipt {
        var verified: AnyNativePropertySnapshot?
        if let readback,
           readback.workspace == edit.workspace, readback.objectID == edit.objectID,
           readback.generation == edit.generation,
           accepted.engineStartedAt == edit.engineStartedAt,
           readback.fence == accepted,
           edit.patch.allSatisfy({ property, value in
               let current = readback.raw[edit.ownerID]?[property]
               return Self.nativeValueMatches(current, requested: value)
           }) {
            verified = readback
        }
        var undo: AnyPreparedPropertyEdit?
        if let verified, edit.expectedDefinitions.allSatisfy({ verified.definitions[$0.key]?.raw == $0.value }) {
            undo = prepared(verified, ownerID: edit.ownerID, patch: edit.inversePatch,
                expected: edit.expectedDefinitions,
                typeDestination: edit.typeDestination == nil ? nil : edit.inversePatch["type"]?.string,
                visibilityOnly: edit.visibilityOnly, membershipOnly: edit.membershipOnly)
        }
        return .init(objectID: edit.objectID,
            readback: verified == nil ? .nativeAcceptedButCurrentStateUnverified : .verifiedCurrent,
            snapshot: verified, undo: undo)
    }

    private func prepareMembership(_ snapshot: AnyNativePropertySnapshot, collectionID: String,
                                   attach: Bool, presentation: Bool) throws -> AnyPreparedPropertyEdit {
        try validate(snapshot)
        guard AnyEditorBlock.validID(collectionID),
              (presentation ? collectionID == Self.presentationCollectionID : !policy.isManagedCollection(collectionID)) else {
            throw AnyNativePropertyError.readOnly
        }
        if attach {
            guard let collection = snapshot.catalog.collections.first(where: { $0.id == collectionID }),
                  presentation || !collection.hidden else { throw AnyNativePropertyError.invalidCatalog }
        } else {
            guard snapshot.collectionIDs.contains(collectionID) else { throw AnyNativePropertyError.invalidProperty }
        }
        let key = try AnyNativePropertyKey(ownerID: "any", propertyID: "collections")
        guard let definition = snapshot.definitions[key], definition.kind == .array, definition.scope == "synced" else {
            throw AnyNativePropertyError.readOnly
        }
        var ids = Set(snapshot.collectionIDs)
        if attach { ids.insert(collectionID) } else { ids.remove(collectionID) }
        return prepared(snapshot, ownerID: "any", patch: ["collections": .array(ids.sorted(by: Self.utf8Less).map(AnyJSON.string))],
            expected: [key: definition.raw], collectionDestination: attach ? collectionID : nil, membershipOnly: true)
    }

    private func prepared(_ snapshot: AnyNativePropertySnapshot, ownerID: String, patch: [String: AnyJSON],
                          expected: [AnyNativePropertyKey: AnyJSON], typeDestination: String? = nil,
                          collectionDestination: String? = nil, visibilityOnly: Bool = false,
                          membershipOnly: Bool = false) -> AnyPreparedPropertyEdit {
        .init(objectID: snapshot.objectID, ownerID: ownerID, patch: patch, fence: snapshot.fence,
              generation: snapshot.generation, workspace: workspace, policy: policy,
              expectedDefinitions: expected, typeDestination: typeDestination,
              collectionDestination: collectionDestination, visibilityOnly: visibilityOnly, membershipOnly: membershipOnly,
              inversePatch: Dictionary(uniqueKeysWithValues: patch.keys.map { ($0, snapshot.raw[ownerID]?[$0] ?? .null) }))
    }

    private func validate(_ snapshot: AnyNativePropertySnapshot) throws {
        guard snapshot.workspace == workspace, snapshot.catalog.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        guard snapshot.canWrite else { throw AnyNativePropertyError.readOnly }
        guard snapshot.fence == (try AnyConditionalPropertyFence(
            record: snapshot.raw, engineStartedAt: snapshot.catalog.engineStartedAt)) else {
            throw AnyHostError.changedDocument
        }
    }
    private func validate(_ lease: AnyHostLease) async throws {
        guard lease.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        try await lease.validate()
    }
    private var spacePath: [String] { ["v1", "spaces", workspace.spaceID] }
    private func capabilities(lease: AnyHostLease) async throws -> AnyJSON {
        try await validate(lease)
        let value = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"],
            authorize: { try await lease.validate() })
        guard value["contract"]?.string == "pinkha-torah-native-v1" else {
            throw AnyNativePropertyError.unavailableContract
        }
        return value
    }
    static func requireCapability(_ value: AnyJSON, _ key: String) throws {
        guard value["contract"]?.string == "pinkha-torah-native-v1", value[key]?.integer == 1 else {
            throw AnyNativePropertyError.unavailableContract
        }
    }
    private func typeProof(_ id: String, lease: AnyHostLease) async throws -> Bool {
        try await validate(lease)
        let proof = try await documents.type(id)
        try await validate(lease)
        return proof.eligible
    }
    private func targetProof(_ id: String, write: Bool, lease: AnyHostLease) async throws -> AnyNativeDocumentTargetProof {
        try await validate(lease)
        let proof = try await documents.target(id, intent: write ? .write : .read)
        try await validate(lease)
        return proof
    }
    private func record(_ id: String, lease: AnyHostLease) async throws -> AnyJSON {
        let result = try await client.requestJSON(method: "GET", path: spacePath + ["properties", id],
            authorize: { try await lease.validate() })
        guard let row = result["record"], row["id"]?.string == id,
              row["spaceId"]?.string == workspace.spaceID, let version = row["_ver"],
              version.object != nil else { throw AnyNativePropertyError.invalidProperty }
        _ = try AnyHostCanonical.bytes(row, maximumBytes: 4_194_304)
        _ = try AnyConditionalPropertyFence(record: row, engineStartedAt: lease.engineStartedAt)
        return row
    }
    private func propertyDefinitions(ownerID: String, collection: Bool, lease: AnyHostLease) async throws -> [AnyNativePropertyDefinition] {
        let result = try await client.requestJSON(method: "GET",
            path: spacePath + [collection ? "collections" : "types", ownerID, "properties"],
            authorize: { try await lease.validate() })
        guard let values = result["properties"]?.array, values.count <= 1024 else { throw AnyEngineError.readLimit }
        _ = try AnyHostCanonical.bytes(result, maximumBytes: 2_097_152)
        let definitions = try values.map { try AnyNativePropertyDefinition(ownerID: ownerID, raw: $0) }
        guard Set(definitions.map(\.key)).count == definitions.count else { throw AnyNativePropertyError.invalidProperty }
        return definitions
    }
    private func verifyPresentation(caps: AnyJSON, lease: AnyHostLease) async throws {
        try Self.requireCapability(caps, "nativePropertyPresentation")
        guard caps["propertyPresentationCollection"]?.string == Self.presentationCollectionID,
              caps["propertyPresentationHiddenProperty"]?.string == Self.hiddenPropertiesID,
              caps["propertyPresentationMaxKeys"]?.integer == 512,
              caps["propertyPresentationMaxKeyBytes"]?.integer == 4096 else {
            throw AnyNativePropertyError.unavailableContract
        }
        let result = try await client.requestJSON(method: "GET", path: spacePath + ["collections", Self.presentationCollectionID],
            authorize: { try await lease.validate() })
        guard result["id"]?.string == Self.presentationCollectionID, result["builtIn"]?.bool == true,
              result["hidden"]?.bool == true else { throw AnyNativePropertyError.unavailableContract }
        // Registered collections intentionally omit xKey in the pinned SDK.
        let definitions = try await propertyDefinitions(ownerID: Self.presentationCollectionID, collection: true, lease: lease)
        guard definitions.count == 1, let hidden = definitions.first, hidden.key.propertyID == Self.hiddenPropertiesID,
              hidden.kind == .array, hidden.scope == "synced",
              hidden.xFormat?["type"]?.string == "pinkha-property-visibility-v1" else {
            throw AnyNativePropertyError.unavailableContract
        }
    }
    static func membership(_ row: AnyJSON) throws -> (typeID: String, collections: [String]) {
        guard let typeID = row["any"]?["type"]?.string, AnyEditorBlock.validID(typeID),
              row["any"]?["collections"] == nil || row["any"]?["collections"]?.array != nil else {
            throw AnyNativePropertyError.invalidProperty
        }
        let values = row["any"]?["collections"]?.array ?? []
        guard values.count <= 512, values.allSatisfy({ $0.string.map(AnyEditorBlock.validID) == true }) else {
            throw AnyNativePropertyError.invalidProperty
        }
        let ids = values.compactMap(\.string)
        guard Set(ids).count == ids.count, !ids.contains("bin"), !ids.contains("template") else {
            throw AnyNativePropertyError.invalidProperty
        }
        return (typeID, ids)
    }
    static func validateHiddenKeys(_ keys: [String]) throws {
        guard keys.count <= 512, Set(keys).count == keys.count,
              keys.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 4096 && !$0.utf8.contains(0) }) else {
            throw AnyNativePropertyError.invalidProperty
        }
    }
    static func utf8Less(_ lhs: String, _ rhs: String) -> Bool { lhs.utf8.lexicographicallyPrecedes(rhs.utf8) }


    /// Compare the value actually represented on the native JSON wire. Integer
    /// versus integral Double encoding and RFC3339 timezone/millisecond
    /// canonicalization must not turn a valid write into a false uncertain state.
    static func nativeValueMatches(_ actual: AnyJSON?, requested: AnyJSON) -> Bool {
        if requested == .null { return actual == nil }
        guard let actual else { return false }
        return nativeEquivalent(actual, requested, depth: 0)
    }
    private static func nativeEquivalent(_ lhs: AnyJSON, _ rhs: AnyJSON, depth: Int) -> Bool {
        // Traverse containers before scalar equality so Unicode-equivalent text
        // cannot bypass the wire-value check. The same ceiling now also bounds
        // identical container traversal; prepared/read validation checks the full value.
        guard depth <= 32 else { return false }
        switch (lhs, rhs) {
        case (.string(let a), .string(let b)):
            return a.utf8.elementsEqual(b.utf8)
        case (.integer(let integer), .number(let number)), (.number(let number), .integer(let integer)):
            return Int64(exactly: number) == integer
        case (.array(let a), .array(let b)):
            return a.count == b.count && zip(a, b).allSatisfy { nativeEquivalent($0.0, $0.1, depth: depth + 1) }
        case (.object(let a), .object(let b)):
            let aKeys = a.keys.sorted { $0.utf8.lexicographicallyPrecedes($1.utf8) }
            let bKeys = b.keys.sorted { $0.utf8.lexicographicallyPrecedes($1.utf8) }
            guard aKeys.count == bKeys.count,
                  zip(aKeys, bKeys).allSatisfy({ $0.0.utf8.elementsEqual($0.1.utf8) }) else { return false }
            if Set(a.keys) == ["$date"], let aDate = a["$date"], let bDate = b["$date"],
               let first = nativeDateMilliseconds(aDate), let second = nativeDateMilliseconds(bDate) {
                return first == second
            }
            return a.allSatisfy { key, value in
                guard let other = b[key] else { return false }
                return nativeEquivalent(value, other, depth: depth + 1)
            }
        default: return lhs == rhs
        }
    }
    private static func nativeDateMilliseconds(_ value: AnyJSON) -> Int64? {
        if let milliseconds = value.integer { return milliseconds }
        guard let value = value.string, value.utf8.count <= 128,
              let regex = try? NSRegularExpression(pattern: #"^(.*T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})$"#),
              let match = regex.firstMatch(in: value, range: NSRange(value.startIndex..., in: value)),
              let base = Range(match.range(at: 1), in: value), let zone = Range(match.range(at: 3), in: value) else { return nil }
        let fraction = Range(match.range(at: 2), in: value).map { String(value[$0]) } ?? ""
        let milliseconds = String((fraction + "000").prefix(3))
        let normalized = String(value[base]) + "." + milliseconds + String(value[zone])
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        guard let date = formatter.date(from: normalized) else { return nil }
        return Int64(exactly: (date.timeIntervalSince1970 * 1000).rounded())
    }

    static func materialize(raw: AnyJSON, objectID: String, catalog: AnyNativePropertyCatalog,
                            definitions: [AnyNativePropertyDefinition],
                            policy: AnyNativePropertyPolicy, canWrite: Bool = true) throws -> AnyNativePropertySnapshot {
        guard raw["id"]?.string == objectID, raw["spaceId"]?.string == catalog.workspace.spaceID,
              let version = raw["_ver"], version.object != nil,
              definitions.count <= 4096, Set(definitions.map(\.key)).count == definitions.count else {
            throw AnyNativePropertyError.invalidProperty
        }
        _ = try AnyHostCanonical.bytes(raw, maximumBytes: 4_194_304)
        let fence = try AnyConditionalPropertyFence(record: raw, engineStartedAt: catalog.engineStartedAt)
        let membership = try membership(raw)
        let imported = try AnyNativeImportedTypePresentation(
            type: catalog.types.first { $0.id == membership.typeID }, catalog: catalog,
            collectionIDs: membership.collections, definitions: definitions, raw: raw)
        var hidden: [String] = []
        if let value = raw[Self.presentationCollectionID]?[Self.hiddenPropertiesID] {
            guard let values = value.array, values.allSatisfy({ $0.string != nil }) else {
                throw AnyNativePropertyError.invalidProperty
            }
            hidden = values.compactMap(\.string)
            try validateHiddenKeys(hidden)
        } else if let imported {
            // An attached presentation collection can still lack its first
            // preference value. Keep defaults until the explicit array is stored;
            // an explicit empty array then persistently means "show all".
            hidden = Array(imported.defaultHiddenKeys)
        }
        let hiddenSet = Set(hidden)
        let rootMetadata: Set<String> = ["id", "author", "spaceId", "createdAt", "modifiedAt", "modifiedBy"]
        let orderedDefinitions = imported?.ordered(definitions) ?? definitions.sorted {
            $0.key.ownerID == $1.key.ownerID ?
                utf8Less($0.key.propertyID, $1.key.propertyID) : utf8Less($0.key.ownerID, $1.key.ownerID)
        }
        let rows = orderedDefinitions.map { definition in
            let key = definition.key
            let value = key.ownerID == "any" && definition.scope == "derived" && rootMetadata.contains(key.propertyID) ?
                raw[key.propertyID] : raw[key.ownerID]?[key.propertyID]
            return AnyNativePropertyRow(definition: definition, value: value,
                isReadOnly: !canWrite || !definition.isSyncedWritableKind || policy.managed(key) || policy.hiddenPropertyKeys.contains(key),
                isVisible: !hiddenSet.contains(key.visibilityKey) && !policy.hiddenPropertyKeys.contains(key) &&
                    !policy.hiddenCollectionIDs.contains(key.ownerID) && key.ownerID != Self.presentationCollectionID)
        }
        return .init(workspace: catalog.workspace, objectID: objectID, generation: catalog.generation,
            fence: fence, currentTypeID: membership.typeID,
            collectionIDs: membership.collections, raw: raw, catalog: catalog, rows: rows,
            importedPresentation: imported,
            hiddenPropertyKeys: hiddenSet, presentationAttached: membership.collections.contains(Self.presentationCollectionID), canWrite: canWrite,
            definitions: Dictionary(uniqueKeysWithValues: definitions.map { ($0.key, $0) }))
    }
}
