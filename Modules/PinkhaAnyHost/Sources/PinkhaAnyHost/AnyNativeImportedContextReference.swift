import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativeImportedContextError: Error, Equatable, Sendable {
    case invalidReference
    case changedCheckpoint
    case unavailableArchive
    case changedArchive
    case closed
}

/// Persist this bounded reference beside the application's existing migration
/// selection. The actual plan and receipts remain in the original private
/// migration journal; no display name, xKey search or saved native run is used.
public struct AnyNativeImportedContextReference: Codable, Sendable {
    public static let version = "pinkha-native-imported-context-v1"
    public static let capturedVersion = "pinkha-native-imported-context-v2"
    public static let maximumBytes = 32 * 1024 * 1024
    public let contract: String
    public let destinationNetworkID: String
    public let destinationAccountID: String
    public let destinationSpaceID: String
    public let storeID: String
    public let planID: String
    public let planSHA256: String
    public let checkpointSHA256: String
    public let sourceAccountID: String
    public let sourceSpaceID: String
    public let captureManifestSHA256: String
    public let sourceWitnessSHA256: String
    public let recoveredManifestSHA256: String?
    /// Absent in the unchanged v1 locator; exactly captured-complete in v2.
    public let definitionEvidence: String?
    public let archiveSourceKey: String
    public let archiveSHA256: String
    public let archiveBytes: Int64
    public let supplementalCanonicalDefinitions: [AnyDestinationCanonicalPropertyBinding]
    public let binding: AnyPreparedMigrationPlanBinding
    public var grantsNativeAuthority: Bool { false }

    /// Called after the existing executor returned its completed progress.
    /// The reference itself is still a locator; opening it performs current
    /// native READ, engine-run and original archive-receipt validation again.
    public init(networkID: String, preservation: AnyHeartNativeSourcePreservation,
                plan: AnyDestinationMigrationPlan, progress: AnyDestinationMigrationProgress,
                supplementalCanonicalDefinitions: [AnyDestinationCanonicalPropertyBinding] = []) throws {
        guard progress.allItemsReconciled, progress.totalItems == plan.items.count,
              progress.verificationIntents.count == plan.items.count,
              Self.sameBinding(progress.binding, plan.binding),
              try AnyDestinationMigrationJournal.encoded(progress.source) ==
                AnyDestinationMigrationJournal.encoded(plan.source) else {
            throw AnyNativeImportedContextError.invalidReference
        }
        try self.init(networkID: networkID, preservation: preservation, plan: plan,
            mappings: progress.mappings, supplementalCanonicalDefinitions: supplementalCanonicalDefinitions)
    }

    /// Backfills a locator from an already-existing completed journal without
    /// replaying migration. readCompletedCheckpoint supplies historical facts
    /// only; the later context open must still admit current native authority.
    public init(networkID: String, preservation: AnyHeartNativeSourcePreservation,
                checkpoint: AnyDestinationSavedCheckpoint,
                supplementalCanonicalDefinitions: [AnyDestinationCanonicalPropertyBinding] = []) throws {
        guard checkpoint.checkpointSHA256 == (try AnyDestinationSavedCheckpoint.fingerprint(
            plan: checkpoint.plan, mappings: checkpoint.mappings)) else {
            throw AnyNativeImportedContextError.changedCheckpoint
        }
        try self.init(networkID: networkID, preservation: preservation, plan: checkpoint.plan,
            mappings: checkpoint.mappings, supplementalCanonicalDefinitions: supplementalCanonicalDefinitions)
    }

    private init(networkID: String, preservation: AnyHeartNativeSourcePreservation,
                 plan: AnyDestinationMigrationPlan, mappings: [AnyDestinationMigrationMapping],
                 supplementalCanonicalDefinitions: [AnyDestinationCanonicalPropertyBinding]) throws {
        let expected = try preservation.preservationPlan(workspace: plan.binding.workspace,
            storeID: plan.binding.storeID, planID: plan.binding.planID)
        guard expected.canonicalBytes == plan.canonicalBytes else {
            throw AnyNativeImportedContextError.invalidReference
        }
        _ = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: mappings,
            supplementalCanonicalDefinitions: supplementalCanonicalDefinitions)
        _ = try AnyNativeImportedCatalogDirectory(plan: plan, mappings: mappings)
        contract = preservation.definitionEvidence.kind == .recoveredOriginal ? Self.version : Self.capturedVersion
        definitionEvidence = preservation.definitionEvidence.kind == .capturedComplete
            ? AnyHeartNativeDefinitionEvidence.Kind.capturedComplete.rawValue : nil
        destinationNetworkID = networkID
        destinationAccountID = plan.binding.workspace.accountID
        destinationSpaceID = plan.binding.workspace.spaceID
        storeID = plan.binding.storeID; planID = plan.binding.planID; planSHA256 = plan.binding.planSHA256
        binding = plan.binding
        checkpointSHA256 = try AnyDestinationSavedCheckpoint.fingerprint(plan: plan, mappings: mappings)
        let source = preservation.archive.binding
        sourceAccountID = source.accountID; sourceSpaceID = source.spaceID
        captureManifestSHA256 = source.captureManifestSHA256
        sourceWitnessSHA256 = source.sourceWitnessSHA256
        recoveredManifestSHA256 = source.recoveredManifestSHA256
        archiveSourceKey = preservation.archiveItemSourceKey
        archiveSHA256 = preservation.archive.sha256; archiveBytes = Int64(preservation.archive.bytes.count)
        self.supplementalCanonicalDefinitions = supplementalCanonicalDefinitions
        try validate()
    }

    public func encoded() throws -> Data {
        try validate()
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(self)
        guard bytes.count <= Self.maximumBytes else { throw AnyEngineError.readLimit }
        return bytes
    }

    /// Use for persisted/untrusted bytes. Besides the closed typed fields, the
    /// existing guard rejects duplicate/colliding keys and numeric loss.
    public static func decode(_ bytes: Data) throws -> Self {
        guard !bytes.isEmpty, bytes.count <= maximumBytes else { throw AnyEngineError.readLimit }
        let value = try JSONDecoder().decode(Self.self, from: bytes)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: value.encoded())
        return value
    }

    func expectedArchiveBinding() throws -> AnyHeartNativePreservationArchive.Binding {
        if Data(contract.utf8) == Data(Self.version.utf8) {
            guard definitionEvidence == nil, let recoveredManifestSHA256 else {
                throw AnyNativeImportedContextError.invalidReference
            }
            return try .init(expectedAccountID: sourceAccountID, expectedSpaceID: sourceSpaceID,
                captureManifestSHA256: captureManifestSHA256, sourceWitnessSHA256: sourceWitnessSHA256,
                recoveredManifestSHA256: recoveredManifestSHA256)
        }
        guard Data(contract.utf8) == Data(Self.capturedVersion.utf8),
              definitionEvidence == AnyHeartNativeDefinitionEvidence.Kind.capturedComplete.rawValue,
              recoveredManifestSHA256 == nil else { throw AnyNativeImportedContextError.invalidReference }
        return try .init(expectedAccountID: sourceAccountID, expectedSpaceID: sourceSpaceID,
            capturedManifestSHA256: captureManifestSHA256, sourceWitnessSHA256: sourceWitnessSHA256)
    }

    private func validate() throws {
        guard [Self.version, Self.capturedVersion].contains(where: { Data($0.utf8) == Data(contract.utf8) }),
              AnyPreparedMigrationPlanBinding.validOpaque(destinationNetworkID, maximum: 4096),
              AnyPreparedMigrationPlanBinding.validOpaque(archiveSourceKey, maximum: 4096),
              [checkpointSHA256, archiveSHA256].allSatisfy(AnyDestinationPlanChecks.digest),
              (4096...Int64(AnyHeartNativePreservationArchive.maximumBytes)).contains(archiveBytes),
              supplementalCanonicalDefinitions.count <= 9,
              Self.sameBinding(binding, try .init(
                workspace: .init(accountID: destinationAccountID, spaceID: destinationSpaceID),
                storeID: storeID, planID: planID, planSHA256: planSHA256)) else {
            throw AnyNativeImportedContextError.invalidReference
        }
        _ = try expectedArchiveBinding()
        var seen = Set<Data>()
        for value in supplementalCanonicalDefinitions {
            try value.validate()
            guard seen.insert(Data(value.evidence.sourceObjectID.utf8)).inserted else {
                throw AnyNativeImportedContextError.invalidReference
            }
        }
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case contract, destinationNetworkID, destinationAccountID, destinationSpaceID
        case storeID, planID, planSHA256, checkpointSHA256
        case sourceAccountID, sourceSpaceID, captureManifestSHA256, sourceWitnessSHA256, recoveredManifestSHA256
        case definitionEvidence
        case archiveSourceKey, archiveSHA256, archiveBytes, supplementalCanonicalDefinitions
    }

    public init(from decoder: any Decoder) throws {
        let all = try decoder.container(keyedBy: AnyImportedContextCodingKey.self)
        let c = try decoder.container(keyedBy: CodingKeys.self)
        contract = try c.decode(String.self, forKey: .contract)
        let expectedKeys: Set<String>
        if Data(contract.utf8) == Data(Self.version.utf8) {
            expectedKeys = Set(CodingKeys.allCases.map(\.rawValue)).subtracting(["definitionEvidence"])
        } else if Data(contract.utf8) == Data(Self.capturedVersion.utf8) {
            expectedKeys = Set(CodingKeys.allCases.map(\.rawValue)).subtracting(["recoveredManifestSHA256"])
        } else { throw AnyNativeImportedContextError.invalidReference }
        guard Set(all.allKeys.map(\.stringValue)) == expectedKeys else {
            throw AnyNativeImportedContextError.invalidReference
        }
        destinationNetworkID = try c.decode(String.self, forKey: .destinationNetworkID)
        destinationAccountID = try c.decode(String.self, forKey: .destinationAccountID)
        destinationSpaceID = try c.decode(String.self, forKey: .destinationSpaceID)
        storeID = try c.decode(String.self, forKey: .storeID)
        planID = try c.decode(String.self, forKey: .planID)
        planSHA256 = try c.decode(String.self, forKey: .planSHA256)
        checkpointSHA256 = try c.decode(String.self, forKey: .checkpointSHA256)
        sourceAccountID = try c.decode(String.self, forKey: .sourceAccountID)
        sourceSpaceID = try c.decode(String.self, forKey: .sourceSpaceID)
        captureManifestSHA256 = try c.decode(String.self, forKey: .captureManifestSHA256)
        sourceWitnessSHA256 = try c.decode(String.self, forKey: .sourceWitnessSHA256)
        if Data(contract.utf8) == Data(Self.version.utf8) {
            recoveredManifestSHA256 = try c.decode(String.self, forKey: .recoveredManifestSHA256)
            definitionEvidence = nil
        } else {
            recoveredManifestSHA256 = nil
            definitionEvidence = try c.decode(String.self, forKey: .definitionEvidence)
        }
        archiveSourceKey = try c.decode(String.self, forKey: .archiveSourceKey)
        archiveSHA256 = try c.decode(String.self, forKey: .archiveSHA256)
        archiveBytes = try c.decode(Int64.self, forKey: .archiveBytes)
        supplementalCanonicalDefinitions = try c.decode([AnyDestinationCanonicalPropertyBinding].self,
                                                         forKey: .supplementalCanonicalDefinitions)
        binding = try .init(workspace: .init(accountID: destinationAccountID, spaceID: destinationSpaceID),
                            storeID: storeID, planID: planID, planSHA256: planSHA256)
        try validate()
    }

    static func sameBinding(_ a: AnyPreparedMigrationPlanBinding,
                            _ b: AnyPreparedMigrationPlanBinding) -> Bool {
        Data(a.workspace.accountID.utf8) == Data(b.workspace.accountID.utf8) &&
        Data(a.workspace.spaceID.utf8) == Data(b.workspace.spaceID.utf8) &&
        Data(a.storeID.utf8) == Data(b.storeID.utf8) &&
        Data(a.planID.utf8) == Data(b.planID.utf8) && a.planSHA256 == b.planSHA256
    }
}

private struct AnyImportedContextCodingKey: CodingKey {
    let stringValue: String
    var intValue: Int? { nil }
    init?(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { return nil }
}
