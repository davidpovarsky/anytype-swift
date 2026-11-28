import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativeImportedOrdinaryPropertyContextError: Error, Equatable, Sendable {
    case invalidReference
    case changedCheckpoint
    case missingCheckpoint
    case changedDefinition(String)
}

/// A closed locator for a separately completed Ordinary14 supplement. It binds
/// the original preservation locator and exact namespace; it grants no current
/// authority. The owner still admits the full original archive, current account,
/// native run, READ membership and existing application lease before private IO.
public struct AnyNativeImportedOrdinaryPropertyReference: Codable, Sendable {
    public static let version = "pinkha-native-imported-ordinary14-context-v1"
    public static let maximumBytes = 4096
    public static let partitionVersion = "pinkha-native-imported-ordinary14-partition-context-v2"
    public let contract: String
    public let checkpointScope: String
    public let preservationReferenceSHA256: String
    public let supplementPlanID: String
    public let supplementPlanSHA256: String
    public let supplementCheckpointSHA256: String
    public let namespaceOwnerID: String
    public let namespaceIntentID: String
    public let namespaceSHA256: String
    public let mappingsSHA256: String
    public private(set) var partition: AnyHeartNativeOrdinaryPropertyPartition? = nil
    public var hasSupplementalCheckpoint: Bool { partition?.newSourceObjectIDs.isEmpty != true }
    public var grantsNativeAuthority: Bool { false }

    /// Routing correspondence only. The plan and original mappings must come
    /// from the completed preservation checkpoint; no old operation is executed.
    public init(preservationReference: AnyNativeImportedContextReference,
                bundle: AnyHeartNativeSpaceBundle,
                completedPreservationPlan: AnyDestinationMigrationPlan,
                completedPreservationMappings: [AnyDestinationMigrationMapping],
                checkpoint: AnyDestinationSavedCheckpoint) throws {
        let supplement = try Self.supplement(preservationReference: preservationReference,
            bundle: bundle, plan: completedPreservationPlan, mappings: completedPreservationMappings)
        try Self.requireCheckpoint(checkpoint, supplement: supplement)
        contract = Self.version; checkpointScope = "completed-ordinary14-on-preservation"
        preservationReferenceSHA256 = AnyContentDigest.sha256(try preservationReference.encoded())
        supplementPlanID = supplement.plan.binding.planID
        supplementPlanSHA256 = supplement.plan.binding.planSHA256
        supplementCheckpointSHA256 = checkpoint.checkpointSHA256
        namespaceOwnerID = supplement.namespace.ownerID
        namespaceIntentID = supplement.namespace.intent.intentID
        namespaceSHA256 = AnyContentDigest.sha256(
            try AnyDestinationMigrationJournal.encoded(supplement.namespace))
        mappingsSHA256 = AnyContentDigest.sha256(
            try AnyDestinationMigrationJournal.encoded(checkpoint.mappings))
        try validate(); try Task.checkCancellation()
    }

    /// A partial overlap has a real missing-only checkpoint. An all-present
    /// partition binds the original checkpoint and has no second completion.
    /// All-new input delegates to the exact legacy v1 constructor.
    public init(preservationReference: AnyNativeImportedContextReference,
                bundle: AnyHeartNativeSpaceBundle,
                preservationCheckpoint: AnyDestinationSavedCheckpoint,
                supplementalCheckpoint: AnyDestinationSavedCheckpoint?) throws {
        let completion = try Self.completion(preservationReference: preservationReference,
            bundle: bundle, checkpoint: preservationCheckpoint)
        if completion.partition.reusedSourceObjectIDs.isEmpty {
            guard let supplementalCheckpoint else {
                throw AnyNativeImportedOrdinaryPropertyContextError.missingCheckpoint
            }
            self = try Self(preservationReference: preservationReference, bundle: bundle,
                completedPreservationPlan: preservationCheckpoint.plan,
                completedPreservationMappings: preservationCheckpoint.mappings,
                checkpoint: supplementalCheckpoint)
            return
        }
        let checkpoint: AnyDestinationSavedCheckpoint
        if completion.missingPlan != nil {
            guard let supplementalCheckpoint else {
                throw AnyNativeImportedOrdinaryPropertyContextError.missingCheckpoint
            }
            try completion.requireCheckpoint(supplementalCheckpoint)
            checkpoint = supplementalCheckpoint
            checkpointScope = "completed-missing-ordinary14-on-preservation"
        } else {
            guard supplementalCheckpoint == nil else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
            }
            checkpoint = preservationCheckpoint
            checkpointScope = "ordinary14-already-imported-in-preservation"
        }
        contract = Self.partitionVersion
        partition = completion.partition
        preservationReferenceSHA256 = AnyContentDigest.sha256(try preservationReference.encoded())
        supplementPlanID = checkpoint.plan.binding.planID
        supplementPlanSHA256 = checkpoint.plan.binding.planSHA256
        supplementCheckpointSHA256 = checkpoint.checkpointSHA256
        namespaceOwnerID = completion.namespace.ownerID
        namespaceIntentID = completion.namespace.intent.intentID
        namespaceSHA256 = AnyContentDigest.sha256(
            try AnyDestinationMigrationJournal.encoded(completion.namespace))
        mappingsSHA256 = AnyContentDigest.sha256(
            try AnyDestinationMigrationJournal.encoded(checkpoint.mappings))
        try validate(); try Task.checkCancellation()
    }

    public func binding(preservation: AnyNativeImportedContextReference) throws
        -> AnyPreparedMigrationPlanBinding {
        try validate()
        guard AnyContentDigest.sha256(try preservation.encoded()) == preservationReferenceSHA256,
              hasSupplementalCheckpoint ? supplementPlanID != preservation.planID :
                (supplementPlanID == preservation.planID &&
                 supplementPlanSHA256 == preservation.planSHA256 &&
                 supplementCheckpointSHA256 == preservation.checkpointSHA256) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
        }
        return try .init(workspace: preservation.binding.workspace, storeID: preservation.storeID,
            planID: supplementPlanID, planSHA256: supplementPlanSHA256)
    }

    public func encoded() throws -> Data {
        try validate()
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(self)
        guard bytes.count <= Self.maximumBytes else { throw AnyEngineError.readLimit }
        return bytes
    }

    public static func decode(_ bytes: Data) throws -> Self {
        guard !bytes.isEmpty, bytes.count <= maximumBytes else { throw AnyEngineError.readLimit }
        let value = try JSONDecoder().decode(Self.self, from: bytes)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: value.encoded())
        return value
    }

    private func validate() throws {
        if Self.same(contract, Self.version) {
            guard partition == nil,
                  Self.same(checkpointScope, "completed-ordinary14-on-preservation") else {
                throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
            }
        } else {
            guard Self.same(contract, Self.partitionVersion), let partition,
                  !partition.reusedSourceObjectIDs.isEmpty else {
                throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
            }
            try partition.validate()
            let expected = partition.newSourceObjectIDs.isEmpty
                ? "ordinary14-already-imported-in-preservation"
                : "completed-missing-ordinary14-on-preservation"
            guard Self.same(checkpointScope, expected) else {
                throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
            }
        }
        guard AnyEditorBlock.validID(namespaceOwnerID),
              [preservationReferenceSHA256, supplementPlanID, supplementPlanSHA256,
               supplementCheckpointSHA256, namespaceIntentID, namespaceSHA256, mappingsSHA256]
                .allSatisfy(AnyDestinationPlanChecks.digest) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
        }
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case contract, checkpointScope, preservationReferenceSHA256
        case supplementPlanID, supplementPlanSHA256, supplementCheckpointSHA256
        case namespaceOwnerID, namespaceIntentID, namespaceSHA256, mappingsSHA256, partition
    }

    public init(from decoder: any Decoder) throws {
        let all = try decoder.container(keyedBy: AnyImportedOrdinaryPropertyCodingKey.self)
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let contract = try c.decode(String.self, forKey: .contract)
        let keys = Set(CodingKeys.allCases.map(\.rawValue))
        let expectedKeys = Self.same(contract, Self.version) ? keys.subtracting(["partition"]) : keys
        guard Set(all.allKeys.map(\.stringValue)) == expectedKeys else {
            throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
        }
        self.contract = contract
        checkpointScope = try c.decode(String.self, forKey: .checkpointScope)
        preservationReferenceSHA256 = try c.decode(String.self, forKey: .preservationReferenceSHA256)
        supplementPlanID = try c.decode(String.self, forKey: .supplementPlanID)
        supplementPlanSHA256 = try c.decode(String.self, forKey: .supplementPlanSHA256)
        supplementCheckpointSHA256 = try c.decode(String.self, forKey: .supplementCheckpointSHA256)
        namespaceOwnerID = try c.decode(String.self, forKey: .namespaceOwnerID)
        namespaceIntentID = try c.decode(String.self, forKey: .namespaceIntentID)
        namespaceSHA256 = try c.decode(String.self, forKey: .namespaceSHA256)
        mappingsSHA256 = try c.decode(String.self, forKey: .mappingsSHA256)
        if !Self.same(contract, Self.version) {
            partition = try c.decode(AnyHeartNativeOrdinaryPropertyPartition.self, forKey: .partition)
        }
        try validate()
    }

    static func completion(preservationReference: AnyNativeImportedContextReference,
                           bundle: AnyHeartNativeSpaceBundle,
                           checkpoint: AnyDestinationSavedCheckpoint) throws
        -> AnyHeartNativeOrdinaryPropertyCompletionPlan {
        let plan = checkpoint.plan, source = plan.source
        guard AnyNativeImportedContextReference.sameBinding(plan.binding, preservationReference.binding),
              checkpoint.checkpointSHA256 == preservationReference.checkpointSHA256,
              try AnyDestinationSavedCheckpoint.fingerprint(plan: plan, mappings: checkpoint.mappings) ==
                preservationReference.checkpointSHA256,
              Self.same(source.accountID, preservationReference.sourceAccountID),
              Self.same(source.spaceID, preservationReference.sourceSpaceID),
              source.captureManifestSHA256 == preservationReference.captureManifestSHA256,
              source.witnessSHA256 == preservationReference.sourceWitnessSHA256 else {
            throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
        }
        return try AnyHeartNativeOrdinaryPropertyCompletionPlan(bundle: bundle, preservation: checkpoint,
            supplementalCanonicalDefinitions: preservationReference.supplementalCanonicalDefinitions)
    }

    static func supplement(preservationReference: AnyNativeImportedContextReference,
                           bundle: AnyHeartNativeSpaceBundle,
                           plan: AnyDestinationMigrationPlan,
                           mappings: [AnyDestinationMigrationMapping]) throws
        -> AnyHeartNativeOrdinaryPropertySupplement {
        try Task.checkCancellation()
        let source = plan.source
        guard AnyNativeImportedContextReference.sameBinding(plan.binding, preservationReference.binding),
              try AnyDestinationSavedCheckpoint.fingerprint(plan: plan, mappings: mappings) ==
                preservationReference.checkpointSHA256,
              Self.same(source.accountID, preservationReference.sourceAccountID),
              Self.same(source.spaceID, preservationReference.sourceSpaceID),
              source.captureManifestSHA256 == preservationReference.captureManifestSHA256,
              source.witnessSHA256 == preservationReference.sourceWitnessSHA256 else {
            throw AnyNativeImportedOrdinaryPropertyContextError.invalidReference
        }
        // The existing builder binds the complete original namespace plan,
        // original receipt/mapping, source bytes and all fourteen descriptors.
        return try AnyHeartNativeOrdinaryPropertySupplement(bundle: bundle,
            completedPreservationPlan: plan, completedPreservationMappings: mappings)
    }

    static func requireCheckpoint(_ checkpoint: AnyDestinationSavedCheckpoint,
                                  supplement: AnyHeartNativeOrdinaryPropertySupplement) throws {
        let plan = supplement.plan
        guard AnyNativeImportedContextReference.sameBinding(checkpoint.plan.binding, plan.binding),
              try AnyDestinationMigrationJournal.encoded(checkpoint.plan) ==
                AnyDestinationMigrationJournal.encoded(plan),
              checkpoint.plan.items.count == 14, checkpoint.mappings.count == 14,
              checkpoint.intents.count == 14,
              checkpoint.checkpointSHA256 == (try AnyDestinationSavedCheckpoint.fingerprint(
                plan: checkpoint.plan, mappings: checkpoint.mappings)) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
        }
        for index in plan.items.indices {
            let item = plan.items[index]
            let operation = try item.operation.resolved(destinationSpaceID: plan.binding.workspace.spaceID) {
                reference in
                switch reference {
                case .native(let id): return id
                case .mapped: throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
                }
            }
            let expected = try AnyDestinationNativeIntent.make(operation, binding: plan.binding,
                sourceKey: item.sourceKey, sequence: nil, inlineContent: nil)
            let actual = checkpoint.intents[index]
            guard case .definition(let definition) = expected,
                  case .definition(let actualDefinition) = actual,
                  definition.kind == .propertyDefinition,
                  actualDefinition.kind == .propertyDefinition,
                  definition.expectedOwnerID.map({ Data($0.utf8) }) == Data(supplement.namespace.ownerID.utf8),
                  actualDefinition.expectedOwnerID.map({ Data($0.utf8) }) == Data(supplement.namespace.ownerID.utf8),
                  expected.identity.id == actual.identity.id,
                  expected.identity.spec == actual.identity.spec,
                  expected.identity.sha == actual.identity.sha else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
            }
        }
        _ = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: checkpoint.mappings)
        try Task.checkCancellation()
    }

    static func same(_ a: String, _ b: String) -> Bool { Data(a.utf8) == Data(b.utf8) }
}

/// Historical routing for the exact fourteen committed definitions. New rows
/// retain their supplemental binding; reused rows retain the original binding.
/// Current namespace, definition and lease observations happen on every use.
public struct AnyNativeImportedOrdinaryPropertyContext: Sendable {
    public let reference: AnyNativeImportedOrdinaryPropertyReference
    public let savedPlan: AnyDestinationMigrationPlan
    public let mappings: [AnyDestinationMigrationMapping]
    public let namespace: AnyDestinationImportedPropertyNamespace
    public let sourceObjectIDs: [String]
    public var provesCurrentNativeState: Bool { false }
    public var permitsMigrationReplay: Bool { false }
    public var permitsSourceAdmission: Bool { false }
    private let propertyDirectory: AnyNativeImportedDefinitionDirectory?
    private let intents: [AnyDestinationNativeIntent]

    init(reference: AnyNativeImportedOrdinaryPropertyReference,
         preservationReference: AnyNativeImportedContextReference,
         bundle: AnyHeartNativeSpaceBundle,
         completedPreservationPlan: AnyDestinationMigrationPlan,
         completedPreservationMappings: [AnyDestinationMigrationMapping],
         checkpoint: AnyDestinationSavedCheckpoint,
         preservationCheckpoint: AnyDestinationSavedCheckpoint? = nil) throws {
        if reference.partition != nil {
            guard let preservationCheckpoint,
                  try AnyDestinationMigrationJournal.encoded(preservationCheckpoint.plan) ==
                    AnyDestinationMigrationJournal.encoded(completedPreservationPlan),
                  try AnyDestinationMigrationJournal.encoded(preservationCheckpoint.mappings) ==
                    AnyDestinationMigrationJournal.encoded(completedPreservationMappings) else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
            }
            let completion = try AnyNativeImportedOrdinaryPropertyReference.completion(
                preservationReference: preservationReference, bundle: bundle,
                checkpoint: preservationCheckpoint)
            let additional = reference.hasSupplementalCheckpoint ? checkpoint : nil
            let expected = try AnyNativeImportedOrdinaryPropertyReference(
                preservationReference: preservationReference, bundle: bundle,
                preservationCheckpoint: preservationCheckpoint, supplementalCheckpoint: additional)
            guard try reference.encoded() == expected.encoded() else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
            }
            self.reference = reference
            namespace = completion.namespace
            sourceObjectIDs = completion.sourceRelations.map(\.objectID)
            if let plan = completion.missingPlan {
                try completion.requireCheckpoint(checkpoint)
                savedPlan = plan; mappings = checkpoint.mappings; intents = checkpoint.intents
                propertyDirectory = try AnyNativeImportedDefinitionDirectory(
                    plan: plan, mappings: checkpoint.mappings)
            } else {
                savedPlan = preservationCheckpoint.plan
                mappings = preservationCheckpoint.mappings; intents = preservationCheckpoint.intents
                propertyDirectory = nil
            }
            try requireCheckpoint(checkpoint)
            try Task.checkCancellation()
        } else {
            let expected = try AnyNativeImportedOrdinaryPropertyReference(
                preservationReference: preservationReference, bundle: bundle,
                completedPreservationPlan: completedPreservationPlan,
                completedPreservationMappings: completedPreservationMappings, checkpoint: checkpoint)
            guard try reference.encoded() == expected.encoded() else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
            }
            let supplement = try AnyNativeImportedOrdinaryPropertyReference.supplement(
                preservationReference: preservationReference, bundle: bundle,
                plan: completedPreservationPlan, mappings: completedPreservationMappings)
            self.reference = reference; savedPlan = checkpoint.plan; mappings = checkpoint.mappings
            namespace = supplement.namespace; sourceObjectIDs = supplement.sourceRelations.map(\.objectID)
            propertyDirectory = try AnyNativeImportedDefinitionDirectory(plan: checkpoint.plan,
                mappings: checkpoint.mappings)
            intents = checkpoint.intents
            try Task.checkCancellation()
        }
    }

    var expectedSupplementalBinding: AnyPreparedMigrationPlanBinding? {
        reference.hasSupplementalCheckpoint ? savedPlan.binding : nil
    }

    func expectedCreationBinding(sourceObjectID: String) throws -> AnyPreparedMigrationPlanBinding {
        guard sourceObjectIDs.contains(where: { Data($0.utf8) == Data(sourceObjectID.utf8) }) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.changedDefinition(sourceObjectID)
        }
        if reference.partition?.reusedSourceObjectIDs.contains(where: {
            Data($0.utf8) == Data(sourceObjectID.utf8)
        }) == true {
            return namespace.binding
        }
        return savedPlan.binding
    }

    func merging(into preservation: AnyNativeImportedDefinitionDirectory) throws
        -> AnyNativeImportedDefinitionDirectory {
        guard AnyNativeImportedContextReference.sameBinding(preservation.binding, namespace.binding),
              try AnyDestinationMigrationJournal.encoded(preservation.source) ==
                AnyDestinationMigrationJournal.encoded(namespace.source) else {
            throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
        }
        guard let propertyDirectory else { return preservation }
        return try .init(preservation: preservation, propertySupplement: propertyDirectory)
    }

    func requirePreservation(_ reference: AnyNativeImportedContextReference,
                             checkpoint: AnyDestinationSavedCheckpoint) throws {
        _ = try self.reference.binding(preservation: reference)
        guard checkpoint.checkpointSHA256 == reference.checkpointSHA256,
              AnyNativeImportedContextReference.sameBinding(checkpoint.plan.binding, namespace.binding),
              try AnyDestinationMigrationJournal.encoded(checkpoint.plan) == namespace.originalPlanBytes,
              try AnyDestinationSavedCheckpoint.fingerprint(
                plan: checkpoint.plan, mappings: checkpoint.mappings) == reference.checkpointSHA256 else {
            throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
        }
    }

    func requireCheckpoint(_ checkpoint: AnyDestinationSavedCheckpoint) throws {
        guard checkpoint.checkpointSHA256 == reference.supplementCheckpointSHA256,
              AnyNativeImportedContextReference.sameBinding(checkpoint.plan.binding, savedPlan.binding),
              try AnyDestinationMigrationJournal.encoded(checkpoint.plan) ==
                AnyDestinationMigrationJournal.encoded(savedPlan),
              try AnyDestinationMigrationJournal.encoded(checkpoint.mappings) ==
                AnyDestinationMigrationJournal.encoded(mappings),
              checkpoint.intents.count == intents.count else {
            throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
        }
        for (actual, expected) in zip(checkpoint.intents, intents) {
            guard actual.identity.id == expected.identity.id,
                  actual.identity.spec == expected.identity.spec,
                  actual.identity.sha == expected.identity.sha else {
                throw AnyNativeImportedOrdinaryPropertyContextError.changedCheckpoint
            }
        }
        try Task.checkCancellation()
    }

    /// The production caller supplies real typed definition reads and the
    /// existing account/run/READ/lease admission. There is no prepare/commit
    /// call. Sequential equal observations are not an atomic whole-Space proof.
    func observe(using driver: any AnyDestinationNativeDriving,
                 authorize: @escaping AnyDestinationAuthorization,
                 readDefinition: @escaping @Sendable (String) async throws -> Void) async throws {
        try await authorize()
        try await namespace.observe(using: driver, authorize: authorize)
        for sourceID in sourceObjectIDs {
            try await authorize()
            try await readDefinition(sourceID)
            try await authorize()
        }
        try await namespace.observe(using: driver, authorize: authorize)
        try await authorize(); try Task.checkCancellation()
    }
}

private struct AnyImportedOrdinaryPropertyCodingKey: CodingKey {
    let stringValue: String
    var intValue: Int? { nil }
    init?(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { return nil }
}
