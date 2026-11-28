import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// The exact selected definitions form one exhaustive partition. A reused row
/// names an original prepared intent and mapping; directory membership alone
/// cannot qualify a definition for reuse. This value grants no native authority.
public struct AnyHeartNativeOrdinaryPropertyPartition: Codable, Sendable {
    public let reusedSourceObjectIDs: [String]
    public let newSourceObjectIDs: [String]

    init(reused: [String], new: [String]) throws {
        reusedSourceObjectIDs = reused; newSourceObjectIDs = new
        try validate()
    }

    func validate() throws {
        let all = reusedSourceObjectIDs + newSourceObjectIDs
        guard all.count == 14, all.allSatisfy(AnyDestinationPlanChecks.identity),
              Set(all.map { Data($0.utf8) }).count == 14 else {
            throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
        }
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case reusedSourceObjectIDs, newSourceObjectIDs
    }

    public init(from decoder: any Decoder) throws {
        let all = try decoder.container(keyedBy: AnyOrdinaryPartitionCodingKey.self)
        guard Set(all.allKeys.map(\.stringValue)) == Set(CodingKeys.allCases.map(\.rawValue)) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
        }
        let c = try decoder.container(keyedBy: CodingKeys.self)
        reusedSourceObjectIDs = try c.decode([String].self, forKey: .reusedSourceObjectIDs)
        newSourceObjectIDs = try c.decode([String].self, forKey: .newSourceObjectIDs)
        try validate()
    }
}

/// Completes the SAME strict fourteen-definition capability when current-content
/// planning has already imported some of those definitions. The old strict
/// supplement constructor and its all-new plan bytes remain separate and intact.
/// No missing-only plan is created when every definition is already represented.
public struct AnyHeartNativeOrdinaryPropertyCompletionPlan: Sendable {
    public static let contract = "pinkha-heart-original-ordinary14-partition-v1"
    public let partition: AnyHeartNativeOrdinaryPropertyPartition
    public let namespace: AnyDestinationImportedPropertyNamespace
    public let missingPlan: AnyDestinationMigrationPlan?
    public let sourceRelations: [AnyHeartNativeDefinitionCatalog.Relation]
    public let outsideSliceIssues: [AnyHeartNativeDefinitionPlan.Issue]
    public let outsideSliceRelationObjectIDs: [String]
    public var permitsSourceAdmission: Bool { false }
    public var permitsDestinationWrites: Bool { false }

    struct ReusedDefinition: Sendable {
        let sourceKey: String
        let sourceObjectID: String
        let intent: AnyPreparedDefinitionIntent
        let mapping: AnyDestinationMigrationMapping
    }

    let preservation: AnyDestinationSavedCheckpoint
    let preservationDirectory: AnyNativeImportedDefinitionDirectory
    let reusedDefinitions: [ReusedDefinition]

    public init(bundle: AnyHeartNativeSpaceBundle,
                preservation: AnyDestinationSavedCheckpoint,
                supplementalCanonicalDefinitions: [AnyDestinationCanonicalPropertyBinding] = []) throws {
        try Task.checkCancellation()
        let plan = preservation.plan
        guard preservation.checkpointSHA256 == (try AnyDestinationSavedCheckpoint.fingerprint(
                plan: plan, mappings: preservation.mappings)),
              preservation.intents.count == plan.items.count else {
            throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
        }
        let namespace = try AnyDestinationImportedPropertyNamespace(
            completedPlan: plan, mappings: preservation.mappings)
        let source = plan.source
        guard Data(bundle.sourceAccountID.utf8) == Data(source.accountID.utf8),
              Data(bundle.sourceSpaceID.utf8) == Data(source.spaceID.utf8),
              bundle.manifestSHA256 == source.captureManifestSHA256,
              bundle.sourceWitnessSHA256 == source.witnessSHA256,
              bundle.manifestBytes == source.definitionManifestBytes else {
            throw AnyDestinationMigrationError.changedSource
        }
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: bundle)
        let definitions = try AnyHeartNativeDefinitionPlan(catalog: catalog)
        let directory = try AnyNativeImportedDefinitionDirectory(plan: plan,
            mappings: preservation.mappings,
            supplementalCanonicalDefinitions: supplementalCanonicalDefinitions)
        var selected: [AnyHeartNativeDefinitionPlan.PropertyBinding] = []
        for key in AnyHeartNativeOrdinaryPropertySupplement.relationKeys {
            guard let relation = catalog.relation(key: key),
                  Data(relation.relationKey.utf8) == Data(key.utf8),
                  Data(relation.snapshot.uniqueKey.utf8) == Data(("rel-" + key).utf8),
                  relation.snapshot.nativeType == 521,
                  relation.readonlyValue == false, relation.defaultValue == .null,
                  relation.targetTypeIDs.isEmpty,
                  relation.snapshot.details["isHidden"] == .bool(false),
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
        var missing: [AnyDestinationMigrationItem] = []
        var reused: [ReusedDefinition] = []
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
            let expected = AnyDestinationMigrationItem(sourceKey: item.sourceKey,
                sourceObjectID: item.sourceObjectID, expectedRecordCount: item.expectedRecordCount,
                operation: .propertyDefinition(owner: .native(namespace.ownerID), kind: kind,
                    name: name, xKey: xKey, description: description, scope: scope,
                    xFormat: format, index: index))
            if let entry = directory.definition(sourceObjectID: item.sourceObjectID) {
                reused.append(try Self.requireReused(expected, entry: entry, namespace: namespace,
                    checkpoint: preservation))
            } else {
                // An unrecognized operation using this schema source key is
                // not absence and cannot justify allocating a second property.
                guard !plan.items.contains(where: {
                    Data($0.sourceKey.utf8) == Data(item.sourceKey.utf8)
                }) else {
                    throw AnyNativeImportedOrdinaryPropertyContextError.changedDefinition(item.sourceObjectID)
                }
                missing.append(expected)
            }
        }
        let partition = try AnyHeartNativeOrdinaryPropertyPartition(
            reused: reused.map(\.sourceObjectID), new: missing.map(\.sourceObjectID))
        let missingPlan: AnyDestinationMigrationPlan?
        if reused.isEmpty {
            // Preserve the strict legacy plan's ID, semantic material, source
            // order and full encoded bytes when all fourteen really are new.
            missingPlan = try AnyHeartNativeOrdinaryPropertySupplement(bundle: bundle,
                completedPreservationPlan: plan,
                completedPreservationMappings: preservation.mappings).plan
        } else if missing.isEmpty {
            missingPlan = nil
        } else {
            struct SemanticMaterial: Encodable {
                let contract: String
                let sourceAccountID: String
                let sourceSpaceID: String
                let sourceWitnessSHA256: String
                let captureManifestSHA256: String
                let originalNamespacePlanSHA256: String
                let originalNamespaceIntentID: String
                let originalCheckpointSHA256: String
                let partition: AnyHeartNativeOrdinaryPropertyPartition
                let items: [AnyDestinationMigrationItem]
            }
            let material = SemanticMaterial(contract: Self.contract,
                sourceAccountID: source.accountID, sourceSpaceID: source.spaceID,
                sourceWitnessSHA256: source.witnessSHA256,
                captureManifestSHA256: source.captureManifestSHA256,
                originalNamespacePlanSHA256: namespace.binding.planSHA256,
                originalNamespaceIntentID: namespace.intent.intentID,
                originalCheckpointSHA256: preservation.checkpointSHA256,
                partition: partition, items: missing)
            let semantic = try AnyDestinationMigrationJournal.encoded(material)
            let scopedSource = try AnyDestinationSourceBinding(bundle: bundle,
                semanticPlanSHA256: AnyContentDigest.sha256(semantic),
                sourceObjectIDs: missing.map(\.sourceObjectID))
            let planID = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
                Self.contract, source.accountID, source.spaceID,
                namespace.binding.workspace.accountID, namespace.binding.workspace.spaceID,
                namespace.binding.storeID, namespace.intent.intentID
            ]))
            missingPlan = try .init(source: scopedSource, workspace: namespace.binding.workspace,
                storeID: namespace.binding.storeID, planID: planID,
                coverage: missing.map { .init(sourceObjectID: $0.sourceObjectID,
                    disposition: .mapped(itemSourceKeys: [$0.sourceKey])) },
                items: missing, importedPropertyNamespace: namespace)
        }
        self.partition = partition; self.namespace = namespace; self.missingPlan = missingPlan
        self.preservation = preservation; preservationDirectory = directory; reusedDefinitions = reused
        sourceRelations = selected.map(\.relation)
        outsideSliceIssues = definitions.issues.filter {
            !selectedIDs.contains(Data($0.sourceObjectID.utf8))
        }
        outsideSliceRelationObjectIDs = catalog.relations.map(\.objectID).filter {
            !selectedIDs.contains(Data($0.utf8))
        }.sorted { Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8)) }
        try Task.checkCancellation()
    }

    private static func requireReused(_ expected: AnyDestinationMigrationItem,
                                      entry: AnyNativeImportedDefinitionEntry,
                                      namespace: AnyDestinationImportedPropertyNamespace,
                                      checkpoint: AnyDestinationSavedCheckpoint) throws -> ReusedDefinition {
        let plan = checkpoint.plan
        let matches = plan.items.indices.filter {
            Data(plan.items[$0].sourceKey.utf8) == Data(expected.sourceKey.utf8) &&
            Data(plan.items[$0].sourceObjectID.utf8) == Data(expected.sourceObjectID.utf8)
        }
        guard matches.count == 1, let index = matches.first,
              checkpoint.mappings.indices.contains(index), checkpoint.intents.indices.contains(index),
              !entry.canonical, let entryIntent = entry.intent, let entryMapping = entry.mapping,
              case .property(.collection, let key) = entry.address,
              Data(key.ownerID.utf8) == Data(namespace.ownerID.utf8),
              Data(entry.sourceObjectID.utf8) == Data(expected.sourceObjectID.utf8) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.changedDefinition(expected.sourceObjectID)
        }
        var mappings: [Data: AnyDestinationMigrationMapping] = [:]
        for mapping in checkpoint.mappings {
            guard mappings.updateValue(mapping, forKey: Data(mapping.sourceKey.utf8)) == nil else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
            }
        }
        let immutableMappings = mappings
        let actual = try plan.items[index].operation.resolved(
            destinationSpaceID: plan.binding.workspace.spaceID) {
                try AnyDestinationMigrationVerifier.resolve($0, in: immutableMappings,
                    destinationSpaceID: plan.binding.workspace.spaceID)
            }
        guard plan.items[index].expectedRecordCount == expected.expectedRecordCount,
              try AnyDestinationMigrationJournal.encoded(actual) ==
                AnyDestinationMigrationJournal.encoded(expected.operation) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.changedDefinition(expected.sourceObjectID)
        }
        let native = try AnyDestinationNativeIntent.make(expected.operation, binding: plan.binding,
            sourceKey: expected.sourceKey, sequence: nil, inlineContent: nil)
        let retained = checkpoint.intents[index], mapping = checkpoint.mappings[index]
        guard case .definition(let definition) = native, definition.kind == .propertyDefinition,
              case .definition(let recorded) = retained, recorded.kind == .propertyDefinition,
              native.identity.id == retained.identity.id,
              native.identity.spec == retained.identity.spec,
              native.identity.sha == retained.identity.sha,
              definition.intentID == entryIntent.intentID,
              definition.specBytes == entryIntent.specBytes,
              definition.specSHA256 == entryIntent.specSHA256,
              try AnyDestinationMigrationJournal.encoded(mapping) ==
                AnyDestinationMigrationJournal.encoded(entryMapping),
              Data(key.propertyID.utf8) == mapping.recordIDs.first.map({ Data($0.utf8) }),
              Data(mapping.objectID.utf8) == Data(namespace.ownerID.utf8) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.changedDefinition(expected.sourceObjectID)
        }
        return .init(sourceKey: expected.sourceKey, sourceObjectID: expected.sourceObjectID,
                     intent: definition, mapping: mapping)
    }

    func requireCheckpoint(_ checkpoint: AnyDestinationSavedCheckpoint) throws {
        guard let plan = missingPlan,
              AnyNativeImportedContextReference.sameBinding(checkpoint.plan.binding, plan.binding),
              try AnyDestinationMigrationJournal.encoded(checkpoint.plan) ==
                AnyDestinationMigrationJournal.encoded(plan),
              checkpoint.mappings.count == partition.newSourceObjectIDs.count,
              checkpoint.intents.count == plan.items.count,
              checkpoint.checkpointSHA256 == (try AnyDestinationSavedCheckpoint.fingerprint(
                plan: plan, mappings: checkpoint.mappings)) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
        }
        for index in plan.items.indices {
            let expected = try AnyDestinationNativeIntent.make(plan.items[index].operation,
                binding: plan.binding, sourceKey: plan.items[index].sourceKey,
                sequence: nil, inlineContent: nil)
            let actual = checkpoint.intents[index]
            guard case .definition(let definition) = expected, definition.kind == .propertyDefinition,
                  case .definition(let observed) = actual, observed.kind == .propertyDefinition,
                  expected.identity.id == actual.identity.id,
                  expected.identity.spec == actual.identity.spec,
                  expected.identity.sha == actual.identity.sha else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
            }
        }
        _ = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: checkpoint.mappings)
        try Task.checkCancellation()
    }

    /// Current sequential observations bracket completion. They do not make a
    /// global schema snapshot and do not turn retained mappings into authority.
    func observeDefinitions(sourceObjectIDs: [String],
                            directory: AnyNativeImportedDefinitionDirectory,
                            client: AnyHTTPClient, lease: AnyHostLease,
                            authorize: @escaping AnyDestinationAuthorization) async throws {
        let selected = Set(sourceRelations.map { Data($0.objectID.utf8) })
        guard sourceObjectIDs.allSatisfy({ selected.contains(Data($0.utf8)) }),
              Set(sourceObjectIDs.map { Data($0.utf8) }).count == sourceObjectIDs.count,
              AnyNativeImportedContextReference.sameBinding(directory.binding, namespace.binding) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
        }
        try await authorize()
        let driver = try await AnyDestinationNativeClients.open(client: client,
            plan: preservation.plan, authorize: authorize)
        try await namespace.observe(using: driver, authorize: authorize)
        let reader = try AnyNativeImportedDefinitionStore(client: client, workspace: lease.workspace)
        for sourceID in sourceObjectIDs {
            let expected: AnyPreparedMigrationPlanBinding
            if partition.reusedSourceObjectIDs.contains(where: { Data($0.utf8) == Data(sourceID.utf8) }) {
                expected = preservation.plan.binding
            } else if let missingPlan {
                expected = missingPlan.binding
            } else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedDefinition(sourceID)
            }
            try await authorize()
            let value = try await reader.read(sourceObjectID: sourceID, directory: directory, lease: lease)
            guard Data(value.workspace.accountID.utf8) == Data(lease.workspace.accountID.utf8),
                  Data(value.workspace.spaceID.utf8) == Data(lease.workspace.spaceID.utf8),
                  value.generation == lease.generation,
                  Data(value.engineStartedAt.utf8) == Data(lease.engineStartedAt.utf8),
                  value.matchesOriginalDescriptor, value.nativeCreationOutcome == "committed",
                  value.entry.intent.map({
                    AnyNativeImportedContextReference.sameBinding($0.binding, expected)
                  }) == true else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedDefinition(sourceID)
            }
            try await authorize()
        }
        try await namespace.observe(using: driver, authorize: authorize)
        try await authorize(); try Task.checkCancellation()
    }

    func directory(checkpoint: AnyDestinationSavedCheckpoint?) throws -> AnyNativeImportedDefinitionDirectory {
        guard let plan = missingPlan else {
            guard checkpoint == nil else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
            }
            return preservationDirectory
        }
        guard let checkpoint else { throw AnyNativeImportedOrdinaryPropertyContextError.missingCheckpoint }
        try requireCheckpoint(checkpoint)
        let additions = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: checkpoint.mappings)
        return try .init(preservation: preservationDirectory, propertySupplement: additions)
    }
}

private struct AnyOrdinaryPartitionCodingKey: CodingKey {
    let stringValue: String
    var intValue: Int? { nil }
    init?(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { return nil }
}
