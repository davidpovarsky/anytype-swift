import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// The immutable original definition and the current native LOCAL provider
/// have separate identities. A compiled _br identifier is never an object ID.
public struct AnyHeartLastOpenedBinding: Codable, Equatable, Sendable {
    public static let contract = "pinkha-heart-last-opened-provider-v1"
    public let evidence: AnyDestinationDefinitionEvidence
    public let readContract: String
    public var sourceHidden: Bool { false }
    public var sourceDeclaresReadonlyValue: Bool { true }
    public var nativeOwnerID: String { "any" }
    public var nativePropertyID: String { AnyNativePersonalNavigationStore.lastOpenedProperty }
    public var permitsArchivedValueReplay: Bool { false }

    public init(evidence: AnyDestinationDefinitionEvidence) throws {
        self.evidence = evidence
        self.readContract = Self.contract
        try validate()
    }

    public func requireSource(_ source: AnyDestinationSourceBinding) throws {
        try evidence.requireSource(source, objectID: evidence.sourceObjectID)
    }

    /// Qualifies the original signed catalog evidence. This does not replace
    /// live native membership/engine admission when reading or writing today.
    public func readOriginalDefinition(directory: AnyNativeImportedCatalogDirectory,
                                       client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                                       lease: AnyHostLease) async throws -> AnyNativeImportedCatalogSnapshot {
        try requireSource(directory.source)
        let snapshot = try await AnyNativeImportedCatalogStore(client: client, workspace: workspace)
            .read(sourceObjectID: evidence.sourceObjectID, directory: directory, lease: lease)
        guard snapshot.entry.evidence == evidence else {
            throw AnyNativeImportedCatalogError.changedSource(evidence.sourceObjectID)
        }
        try await lease.validate()
        return snapshot
    }

    private func validate() throws {
        let row = evidence.snapshot
        guard readContract.utf8.elementsEqual(Self.contract.utf8), row.nativeType == 521,
              row.uniqueKey.utf8.elementsEqual("rel-lastOpenedDate".utf8), row.issues.isEmpty,
              try AnyHostCanonical.bytes(.object(row.details), maximumBytes: 65_536) ==
                  AnyHostCanonical.bytes(Self.originalDescriptor, maximumBytes: 65_536) else {
            throw AnyDestinationMigrationError.invalidPlan("original last-opened descriptor")
        }
    }

    // The description typo, explicit null and empty arrays are original bytes
    // projected from captured JSON988a2796/PBf0081c0e; they are not rewritten.
    static let originalDescriptor: AnyJSON = .object([
        "apiObjectKey": .string("last_opened_date"),
        "description": .string("Date when the object was modified last opened"),
        "internalFlags": .array([]), "isHidden": .bool(false), "layout": .integer(5),
        "name": .string("Last opened date"), "origin": .integer(7),
        "relationDefaultValue": .null, "relationFormat": .integer(4),
        "relationFormatIncludeTime": .bool(true), "relationFormatObjectTypes": .array([]),
        "relationKey": .string("lastOpenedDate"), "relationMaxCount": .integer(1),
        "relationReadonlyValue": .bool(true), "revision": .integer(1),
        "sourceObject": .string("_brlastOpenedDate")
    ])

    private enum CodingKeys: String, CodingKey { case evidence, readContract }
    public init(from decoder: any Decoder) throws {
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        evidence = try fields.decode(AnyDestinationDefinitionEvidence.self, forKey: .evidence)
        readContract = try fields.decode(String.self, forKey: .readContract)
        try validate()
    }
}


/// The source-role consumer uses this facade. It verifies the actual imported
/// signed definition before accessing the current native provider. Object IDs
/// passed here are already translated native IDs; no source-ID mapping is
/// inferred from a catalog-carrier ID or a compiled _br descriptor.
public struct AnyPreparedHeartObjectOpen: Sendable {
    public var operationID: UUID { native.operationID }
    public var nativeObjectID: String { native.objectID }
    let native: AnyPreparedNativeObjectOpen
    let sourceBinding: AnyHeartLastOpenedBinding
}

public struct AnyHeartLastOpenedStore: Sendable {
    public let workspace: AnyTorahWorkspace
    public let sourceBinding: AnyHeartLastOpenedBinding
    private let directory: AnyNativeImportedCatalogDirectory
    private let client: AnyHTTPClient
    private let native: AnyNativePersonalNavigationStore

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                nativeBinding: AnyNativeAccountRunBinding,
                sourceBinding: AnyHeartLastOpenedBinding,
                directory: AnyNativeImportedCatalogDirectory) throws {
        guard AnyNativePersonalNavigationStore.sameWorkspace(directory.binding.workspace, workspace) else {
            throw AnyHostError.wrongWorkspace
        }
        try sourceBinding.requireSource(directory.source)
        self.workspace = workspace
        self.sourceBinding = sourceBinding
        self.directory = directory
        self.client = client
        self.native = try .init(client: client, workspace: workspace, binding: nativeBinding)
    }

    public func readCurrent(nativeObjectID: String, lease: AnyHostLease) async throws
        -> AnyNativeLastOpenedSnapshot {
        _ = try await original(lease)
        return try await native.readLastOpened(objectID: nativeObjectID, lease: lease)
    }

    public func prepareActualOpen(nativeObjectID: String, observedAt: Date = Date(),
                                  lease: AnyHostLease) async throws -> AnyPreparedHeartObjectOpen {
        _ = try await original(lease)
        let intent = try await native.prepareActualOpen(objectID: nativeObjectID,
                                                        observedAt: observedAt, lease: lease)
        return .init(native: intent, sourceBinding: sourceBinding)
    }

    public func commitActualOpen(
        _ intent: AnyPreparedHeartObjectOpen, lease: AnyHostLease,
        onAcknowledged: @escaping @Sendable (AnyNativeNavigationAcknowledgment) -> Void
    ) async throws -> AnyNativeOpenReceipt {
        guard intent.sourceBinding == sourceBinding else {
            throw AnyDestinationMigrationError.invalidPlan("last-opened source intent")
        }
        _ = try await original(lease)
        // No awaited work follows the native operation here. The mandatory
        // owner callback receives its ACK before the provider's own readback.
        return try await native.commitActualOpen(intent.native, lease: lease,
                                                 onAcknowledged: onAcknowledged)
    }

    public func acknowledgment(for operationID: UUID) async -> AnyNativeNavigationAcknowledgment? {
        await native.acknowledgment(for: operationID)
    }

    private func original(_ lease: AnyHostLease) async throws -> AnyNativeImportedCatalogSnapshot {
        try await sourceBinding.readOriginalDefinition(directory: directory, client: client,
                                                         workspace: workspace, lease: lease)
    }
}
