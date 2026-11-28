import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// A finite property-schema supplement rebuilt from the retained original
/// definitions. This is not the missing historical Ordinary14 source packet.
/// It creates only the fourteen selected definitions through the existing
/// migration executor; the original namespace operation is a read prerequisite.
public struct AnyHeartNativeOrdinaryPropertySupplement: Sendable {
    public static let contract = "pinkha-heart-original-ordinary14-supplement-v1"
    public static let relationKeys = [
        "aperture", "artist", "audioAlbum", "audioAlbumTrackNumber", "audioGenre",
        "audioLyrics", "camera", "cameraIso", "done", "exposure", "focalRatio",
        "releasedYear", "source", "tag"
    ]
    public let plan: AnyDestinationMigrationPlan
    public let namespace: AnyDestinationImportedPropertyNamespace
    public let sourceRelations: [AnyHeartNativeDefinitionCatalog.Relation]
    /// Other catalog issues remain visible and retain their original reasons.
    /// This component does not admit unsupported families or the whole Space.
    public let outsideSliceIssues: [AnyHeartNativeDefinitionPlan.Issue]
    public let outsideSliceRelationObjectIDs: [String]
    public var permitsSourceAdmission: Bool { false }
    public var permitsDestinationWrites: Bool { false }
    private let preservationDirectory: AnyNativeImportedDefinitionDirectory

    public init(bundle: AnyHeartNativeSpaceBundle,
                completedPreservationPlan: AnyDestinationMigrationPlan,
                completedPreservationMappings: [AnyDestinationMigrationMapping]) throws {
        let namespace = try AnyDestinationImportedPropertyNamespace(
            completedPlan: completedPreservationPlan, mappings: completedPreservationMappings)
        let source = completedPreservationPlan.source
        guard Data(bundle.sourceAccountID.utf8) == Data(source.accountID.utf8),
              Data(bundle.sourceSpaceID.utf8) == Data(source.spaceID.utf8),
              bundle.manifestSHA256 == source.captureManifestSHA256,
              bundle.sourceWitnessSHA256 == source.witnessSHA256,
              bundle.manifestBytes == source.definitionManifestBytes else {
            throw AnyDestinationMigrationError.changedSource
        }
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: bundle)
        let definitions = try AnyHeartNativeDefinitionPlan(catalog: catalog)
        let originalDirectory = try AnyNativeImportedDefinitionDirectory(
            plan: completedPreservationPlan, mappings: completedPreservationMappings)
        var selected: [AnyHeartNativeDefinitionPlan.PropertyBinding] = []
        for key in Self.relationKeys {
            guard let relation = catalog.relation(key: key),
                  Data(relation.relationKey.utf8) == Data(key.utf8),
                  Data(relation.snapshot.uniqueKey.utf8) == Data(("rel-" + key).utf8),
                  relation.snapshot.nativeType == 521,
                  relation.readonlyValue == false, relation.defaultValue == .null,
                  relation.targetTypeIDs.isEmpty,
                  relation.snapshot.details["isHidden"] == .bool(false),
                  originalDirectory.definition(sourceObjectID: relation.objectID) == nil,
                  let property = definitions.property(sourceKey: key),
                  Data(property.relation.objectID.utf8) == Data(relation.objectID.utf8),
                  property.canonicalBinding == nil else {
                throw AnyDestinationMigrationError.invalidPlan("ordinary14 original definition: " + key)
            }
            let expected: (kind: String, format: String, maximumCount: Int64)
            switch key {
            case "audioAlbumTrackNumber", "cameraIso", "focalRatio", "releasedYear":
                expected = ("number", "number", 1)
            case "done": expected = ("boolean", "checkbox", 1)
            case "source": expected = ("string", "url", 1)
            case "tag": expected = ("array", "choice", 0)
            default: expected = ("string", "longtext", 1)
            }
            guard property.kind == expected.kind, property.format == expected.format,
                  relation.maximumCount == expected.maximumCount,
                  key != "tag" || catalog.options(relationKey: key).isEmpty else {
                throw AnyDestinationMigrationError.invalidPlan("ordinary14 original shape: " + key)
            }
            selected.append(property)
        }
        let selectedIDs = Set(selected.map { Data($0.relation.objectID.utf8) })
        guard selected.count == 14, selectedIDs.count == 14,
              definitions.issues.allSatisfy({ !selectedIDs.contains(Data($0.sourceObjectID.utf8)) }) else {
            throw AnyDestinationMigrationError.invalidPlan("ordinary14 selected definition issue")
        }
        var items: [AnyDestinationMigrationItem] = []
        for property in selected {
            let matches = definitions.schemaItems.filter {
                Data($0.sourceKey.utf8) == Data(property.sourceKey.utf8) &&
                Data($0.sourceObjectID.utf8) == Data(property.relation.objectID.utf8)
            }
            guard matches.count == 1, let item = matches.first,
                  case .propertyDefinition(_, let kind, let name, let xKey, let description,
                                           let scope, let format, let index) = item.operation else {
                throw AnyDestinationMigrationError.invalidPlan("ordinary14 exact schema operation")
            }
            items.append(.init(sourceKey: item.sourceKey, sourceObjectID: item.sourceObjectID,
                expectedRecordCount: item.expectedRecordCount,
                operation: .propertyDefinition(owner: .native(namespace.ownerID), kind: kind,
                    name: name, xKey: xKey, description: description, scope: scope,
                    xFormat: format, index: index)))
        }
        struct SemanticMaterial: Encodable {
            let contract: String
            let sourceAccountID: String
            let sourceSpaceID: String
            let sourceWitnessSHA256: String
            let captureManifestSHA256: String
            let originalNamespacePlanSHA256: String
            let originalNamespaceIntentID: String
            let items: [AnyDestinationMigrationItem]
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let semantic = try encoder.encode(SemanticMaterial(contract: Self.contract,
            sourceAccountID: source.accountID, sourceSpaceID: source.spaceID,
            sourceWitnessSHA256: source.witnessSHA256,
            captureManifestSHA256: source.captureManifestSHA256,
            originalNamespacePlanSHA256: namespace.binding.planSHA256,
            originalNamespaceIntentID: namespace.intent.intentID, items: items))
        let scopedSource = try AnyDestinationSourceBinding(bundle: bundle,
            semanticPlanSHA256: AnyContentDigest.sha256(semantic),
            sourceObjectIDs: selected.map(\.relation.objectID))
        // Stable logical ID: changed descriptor bytes change planSHA256, not
        // the native ledger identity into which a resumed write is reconciled.
        let planID = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            Self.contract, source.accountID, source.spaceID,
            namespace.binding.workspace.accountID, namespace.binding.workspace.spaceID,
            namespace.binding.storeID, namespace.intent.intentID
        ]))
        self.plan = try .init(source: scopedSource, workspace: namespace.binding.workspace,
            storeID: namespace.binding.storeID, planID: planID,
            coverage: items.map { .init(sourceObjectID: $0.sourceObjectID,
                                        disposition: .mapped(itemSourceKeys: [$0.sourceKey])) },
            items: items, importedPropertyNamespace: namespace)
        self.namespace = namespace
        sourceRelations = selected.map(\.relation)
        outsideSliceIssues = definitions.issues.filter {
            !selectedIDs.contains(Data($0.sourceObjectID.utf8))
        }
        outsideSliceRelationObjectIDs = catalog.relations.map(\.objectID).filter {
            !selectedIDs.contains(Data($0.utf8))
        }.sorted { Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8)) }
        preservationDirectory = originalDirectory
    }

    /// This returns routing correspondence only. AnyNativeImportedDefinitionStore
    /// verifies each selected native creation and original descriptor provenance
    /// under the current account/Space/run lease before delivering a definition.
    public func directory(mappings: [AnyDestinationMigrationMapping]) throws
        -> AnyNativeImportedDefinitionDirectory {
        let supplement = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: mappings)
        return try .init(preservation: preservationDirectory, propertySupplement: supplement)
    }
}
