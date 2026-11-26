import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyHeartNativePageCompositionError: Error, Equatable, Sendable {
    case sourceBinding, objectBindings, typeBinding, titleBinding
    case unrepresentedMetadata(String), relationDefinition(String), unsupportedDefinitions, unsupportedSource
}

/// Composes the current Page's exact title, present property values and ordered
/// body into the existing destination operations. This is not a whole-Space
/// census, history migration, source authority or permission to execute writes.
public struct AnyHeartNativePageComposition: Sendable {
    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let sourceSnapshotSHA256: String
    public let sourceViewSHA256: String
    public let sourceKey: String
    public let contentSHA256: String
    public let layout: AnyHeartNativePageLayout
    public let body: AnyHeartNativeTextBlockPlan
    public let values: AnyHeartNativeDefinitionPlan.Values
    public let presentDetailKeys: [String]
    public let items: [AnyDestinationMigrationItem]
    public let definitionIssues: [AnyHeartNativeDefinitionPlan.Issue]
    public let sourceIssues: [String]
    public var permitsDestinationWrites: Bool { false }

    public static func objectSourceKey(spaceID: String, objectID: String) -> String {
        // Length-prefixing keeps arbitrary UTF-8 identifiers unambiguous.
        let space = Data(spaceID.utf8), object = Data(objectID.utf8)
        var bytes = Data("pinkha-heart-native-object-v1:".utf8)
        bytes.append(Data("\(space.count):".utf8)); bytes.append(space)
        bytes.append(Data("\(object.count):".utf8)); bytes.append(object)
        return "heart-native-object:" + AnyContentDigest.sha256(bytes)
    }

    public init(bundle: AnyHeartNativeSpaceBundle, sourceObjectID: String,
                definitions: AnyHeartNativeDefinitionPlan,
                objects: [AnyHeartNativeDefinitionPlan.ObjectBinding],
                files: [AnyHeartNativeFileBinding] = []) throws {
        let catalog = definitions.catalog
        guard Data(bundle.sourceAccountID.utf8) == Data(catalog.sourceAccountID.utf8),
              Data(bundle.sourceSpaceID.utf8) == Data(catalog.sourceSpaceID.utf8),
              bundle.manifestSHA256 == catalog.captureManifestSHA256,
              bundle.sourceWitnessSHA256 == catalog.sourceWitnessSHA256 else {
            throw AnyHeartNativePageCompositionError.sourceBinding
        }
        let sourceObjects = Dictionary(uniqueKeysWithValues:
            bundle.objects.map { (Data($0.sourceObjectID.utf8), $0) })
        for binding in objects {
            guard let object = sourceObjects[Data(binding.sourceObjectID.utf8)],
                  object.nativeType == 16, object.objectTypes.count == 1,
                  definitions.type(sourceURL: object.objectTypes[0])?.definition.recommendedLayout == 0 else {
                throw AnyHeartNativePageCompositionError.objectBindings
            }
        }
        let rows = bundle.objects.filter { Data($0.sourceObjectID.utf8) == Data(sourceObjectID.utf8) }
        guard rows.count == 1, let snapshot = rows.first else {
            throw AnyHeartNativePageCompositionError.sourceBinding
        }
        var sourceIssues = bundle.issues.map { "bundle:" + $0.code + ":" + $0.field }
        if !bundle.sourceGaps.isEmpty { sourceIssues.append("source-gaps") }
        if !bundle.resolverUnmapped.isEmpty { sourceIssues.append("resolver-unmapped") }
        if !bundle.bundledDefinitionsUsed.isEmpty { sourceIssues.append("bundled-definition-fallback") }
        if !bundle.retainedOtherCollections.isEmpty, bundle.nativeStoreContext?.unmappedCollectionNames.isEmpty != true {
            sourceIssues.append("unmapped-native-collections")
        }
        try self.init(snapshot: snapshot, definitions: definitions, objects: objects,
                      files: files, sourceIssues: sourceIssues)
    }

    /// Internal pure semantic control boundary; detached fixtures cannot be
    /// presented as an admitted native bundle by production callers.
    init(snapshot: AnyHeartNativeSnapshotView, definitions: AnyHeartNativeDefinitionPlan,
         objects: [AnyHeartNativeDefinitionPlan.ObjectBinding],
         files: [AnyHeartNativeFileBinding] = [],
         sourceIssues: [String] = ["detached-semantic-control"]) throws {
        let catalog = definitions.catalog
        guard Data(snapshot.sourceSpaceID.utf8) == Data(catalog.sourceSpaceID.utf8) else {
            throw AnyHeartNativePageCompositionError.sourceBinding
        }
        let layout = try AnyHeartNativePageLayout(snapshot: snapshot)
        let body = try AnyHeartNativeTextBlockPlan(snapshot: snapshot, pageLayout: layout)
        guard snapshot.objectTypes.count == 1,
              let type = definitions.type(sourceURL: snapshot.objectTypes[0]),
              type.definition.recommendedLayout == 0 else {
            throw AnyHeartNativePageCompositionError.typeBinding
        }
        guard layout.title != nil, definitions.property(sourceKey: "name")?.isCanonicalName == true else {
            throw AnyHeartNativePageCompositionError.titleBinding
        }
        // An object-specific featured override is distinct from Type defaults.
        // It needs its own destination behavior and must not be silently erased.
        guard layout.featuredRelations == nil else {
            throw AnyHeartNativePageCompositionError.unrepresentedMetadata("featuredRelations")
        }
        for field in ["fileKeys", "extraRelations", "collections", "removedCollectionKeys", "fileInfo"] {
            if let value = snapshot.rawSnapshot[field],
               value != .null && value != .array([]) && value != .object([:]) {
                throw AnyHeartNativePageCompositionError.unrepresentedMetadata(field)
            }
        }
        if let key = snapshot.rawSnapshot["key"], key != .null && key != .string("") {
            throw AnyHeartNativePageCompositionError.unrepresentedMetadata("key")
        }
        if let timestamp = snapshot.rawSnapshot["originalCreatedTimestamp"],
           timestamp != .null && timestamp != .string("0") && timestamp != .integer(0) {
            throw AnyHeartNativePageCompositionError.unrepresentedMetadata("originalCreatedTimestamp")
        }
        var linkBytes = Set<Data>(), linkNames = Set<String>()
        for row in snapshot.relationLinks {
            guard let fields = row.object, Set(fields.keys) == ["key", "format"],
                  let key = fields["key"]?.string, let format = fields["format"]?.integer,
                  linkBytes.insert(Data(key.utf8)).inserted, linkNames.insert(key).inserted,
                  let relation = catalog.relation(key: key), relation.rawFormat == format else {
                throw AnyHeartNativePageCompositionError.relationDefinition("unmatched-or-ambiguous-link")
            }
        }
        var objectIDs = Set<Data>(), sourceKeys = Set<Data>(), languageKeys = Set<String>()
        for object in objects {
            guard objectIDs.insert(Data(object.sourceObjectID.utf8)).inserted,
                  sourceKeys.insert(Data(object.destinationSourceKey.utf8)).inserted,
                  languageKeys.insert(object.destinationSourceKey).inserted,
                  object.destinationSourceKey == Self.objectSourceKey(
                    spaceID: snapshot.sourceSpaceID, objectID: object.sourceObjectID) else {
                throw AnyHeartNativePageCompositionError.objectBindings
            }
        }
        let sourceKey = Self.objectSourceKey(spaceID: snapshot.sourceSpaceID, objectID: snapshot.sourceObjectID)
        guard objects.contains(where: {
            Data($0.sourceObjectID.utf8) == Data(snapshot.sourceObjectID.utf8) && $0.destinationSourceKey == sourceKey
        }) else { throw AnyHeartNativePageCompositionError.objectBindings }
        let detailKeys = snapshot.details.keys.sorted { Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8)) }
        // Every present detail is consumed; there is no caller-selected subset.
        let values = try definitions.values(snapshot: snapshot, relationKeys: detailKeys, objects: objects, files: files)
        // The scoped current-content schema actually owns an immutable facts
        // dataset. Historical fields count as consumed only when the concrete
        // source-fact operation is constructed and included below.
        let facts = try definitions.contentSelection.map { _ in
            try AnyHeartNativeSourceFacts.item(snapshot: snapshot, values: values, type: type, objectSourceKey: sourceKey)
        }
        let retainedDerivedKeys = facts == nil ? [] : values.nativeDerivedSourceValues.map(\.sourceRelationKey)
        guard Set(values.initialRelationKeys + values.deferredRelationKeys + values.nativeIdentityRelationKeys + retainedDerivedKeys) == Set(detailKeys) else {
            throw AnyHeartNativePageCompositionError.sourceBinding
        }
        var items = [AnyDestinationMigrationItem(sourceKey: sourceKey, sourceObjectID: snapshot.sourceObjectID,
            operation: .object(type: type.object, collections: definitions.propertyOwner.map { [$0] } ?? [],
                               initialProperties: values.initialProperties))]
        items.append(contentsOf: body.destinationItems(ownerSourceKey: sourceKey))
        if let facts { items.append(facts) }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        for group in values.deferredGroups {
            let ownerDigest = AnyContentDigest.sha256(try encoder.encode(group.owner))
            items.append(.init(sourceKey: sourceKey + ":references:" + ownerDigest,
                sourceObjectID: snapshot.sourceObjectID,
                operation: .propertyUpdate(
                    object: .mapped(sourceKey: sourceKey, slot: .objectID, encoding: .rawID),
                    owner: group.owner, patch: group.fields)))
        }
        struct Material: Encodable {
            let contract: String
            let spaceID: String
            let objectID: String
            let snapshotSHA256: String
            let viewSHA256: String
            let catalogSHA256: String
            let manifestSHA256: String
            let witnessSHA256: String
            let layoutSHA256: String
            let bodySHA256: String
            let presentDetailKeys: [String]
            let sourceIssues: [String]
            let items: [AnyDestinationMigrationItem]
        }
        let material = Material(contract: "pinkha-heart-native-page-composition-v1",
            spaceID: snapshot.sourceSpaceID, objectID: snapshot.sourceObjectID,
            snapshotSHA256: snapshot.snapshotSHA256, viewSHA256: snapshot.viewSHA256,
            catalogSHA256: catalog.contentSHA256, manifestSHA256: catalog.captureManifestSHA256,
            witnessSHA256: catalog.sourceWitnessSHA256, layoutSHA256: layout.contentSHA256,
            bodySHA256: body.contentSHA256, presentDetailKeys: detailKeys, sourceIssues: sourceIssues, items: items)
        let bytes = try encoder.encode(material)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        self.sourceSpaceID = snapshot.sourceSpaceID; self.sourceObjectID = snapshot.sourceObjectID
        self.sourceSnapshotSHA256 = snapshot.snapshotSHA256; self.sourceViewSHA256 = snapshot.viewSHA256
        self.sourceKey = sourceKey; self.contentSHA256 = AnyContentDigest.sha256(bytes)
        self.layout = layout; self.body = body; self.values = values
        self.presentDetailKeys = detailKeys; self.items = items; self.definitionIssues = definitions.issues
        self.sourceIssues = sourceIssues
    }

    /// Even these current-state operations remain unavailable while any
    /// captured schema behavior is unqualified. The enclosing destination plan
    /// must additionally cover the full native census and current authorization.
    public func admittedCurrentItems() throws -> [AnyDestinationMigrationItem] {
        guard sourceIssues.isEmpty else { throw AnyHeartNativePageCompositionError.unsupportedSource }
        guard definitionIssues.isEmpty else { throw AnyHeartNativePageCompositionError.unsupportedDefinitions }
        return items
    }

    /// Used only by the explicit dependency-closed current-content graph.
    /// The ordinary whole-bundle admission above remains unchanged, including
    /// the original missing compiled descriptor refusal.
    func admittedSelectedItems(_ selection: AnyHeartNativeContentSelection) throws -> [AnyDestinationMigrationItem] {
        guard Data(sourceSpaceID.utf8) == Data(selection.sourceSpaceID.utf8),
              let selected = selection.objects.first(where: { Data($0.sourceObjectID.utf8) == Data(sourceObjectID.utf8) }),
              selected.snapshotSHA256 == sourceSnapshotSHA256, selected.jsonViewSHA256 == sourceViewSHA256,
              sourceIssues == selection.retainedWholeSourceIssues else {
            throw AnyHeartNativePageCompositionError.unsupportedSource
        }
        guard definitionIssues.isEmpty else { throw AnyHeartNativePageCompositionError.unsupportedDefinitions }
        return items
    }
}
