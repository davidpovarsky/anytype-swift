import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Eleven original Heart metadata definitions. These bindings expose the
/// captured values; they do not replace live system attributes in Any.
public struct AnyHeartOriginalMetadataBinding: Codable, Equatable, Sendable {
    public enum Role: String, Codable, CaseIterable, Sendable {
        case addedDate, createdInContext, globalName, importType, internalFlags
        case oldAnytypeID, origin, revision, sourceObject, timestamp, uniqueKey
    }
    public static let contract = "pinkha-heart-original-metadata-v1"
    public let role: Role
    public let evidence: AnyDestinationDefinitionEvidence
    public let readContract: String
    public var permitsDestinationWrites: Bool { false }
    public var provesCurrentSourceValues: Bool { false }

    public init(evidence: AnyDestinationDefinitionEvidence) throws {
        guard evidence.snapshot.nativeType == 521, evidence.snapshot.issues.isEmpty,
              let key = evidence.snapshot.details["relationKey"]?.string,
              let role = Role(rawValue: key),
              key.utf8.elementsEqual(role.rawValue.utf8),
              evidence.snapshot.uniqueKey.utf8.elementsEqual(("rel-" + role.rawValue).utf8),
              try AnyDestinationDefinitionChecks.bytes(.object(evidence.snapshot.details)) ==
                AnyDestinationDefinitionChecks.bytes(Self.descriptor(role)) else {
            throw AnyDestinationMigrationError.invalidPlan("original metadata definition")
        }
        self.role = role; self.evidence = evidence; self.readContract = Self.contract
    }

    public func requireSource(_ source: AnyDestinationSourceBinding) throws {
        try evidence.requireSource(source, objectID: evidence.sourceObjectID)
    }

    private enum CodingKeys: String, CodingKey { case role, evidence, readContract }
    public init(from decoder: any Decoder) throws {
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        let expectedRole = try fields.decode(Role.self, forKey: .role)
        let contract = try fields.decode(String.self, forKey: .readContract)
        try self.init(evidence: fields.decode(AnyDestinationDefinitionEvidence.self, forKey: .evidence))
        guard role == expectedRole, contract.utf8.elementsEqual(Self.contract.utf8) else {
            throw AnyDestinationMigrationError.invalidPlan("original metadata binding contract")
        }
    }

    private static func descriptor(_ role: Role) -> AnyJSON {
        let name: String, description: String, api: String
        let format: Int64, revision: Int64, hidden: Bool
        switch role {
        case .addedDate:
            (name, description, api, format, revision, hidden) =
                ("Added date", "Date when the file were added into the anytype", "added_date", 4, 1, false)
        case .createdInContext:
            (name, description, api, format, revision, hidden) =
                ("Created in context", "Object ID where the object was initially created", "created_in_context", 100, 1, false)
        case .globalName:
            (name, description, api, format, revision, hidden) =
                ("Global name", "Name of profile that the user could be mentioned by", "global_name", 1, 1, true)
        case .importType:
            (name, description, api, format, revision, hidden) =
                ("Import Type", "Import type, used to create object (notion, md and etc)", "import_type", 2, 0, false)
        case .internalFlags:
            (name, description, api, format, revision, hidden) =
                ("Internal flags", "Set of internal flags", "internal_flags", 2, 0, true)
        case .oldAnytypeID:
            (name, description, api, format, revision, hidden) = ("Old Anytype ID", "", "old_anytype_id", 0, 0, true)
        case .origin:
            (name, description, api, format, revision, hidden) =
                ("Origin", "Source of objects in Anytype (clipboard, import)", "origin", 2, 0, false)
        case .revision:
            (name, description, api, format, revision, hidden) = ("Revision", "Revision of system object", "revision", 2, 0, true)
        case .sourceObject:
            (name, description, api, format, revision, hidden) = ("Source object", "", "source_object", 100, 0, false)
        case .timestamp:
            (name, description, api, format, revision, hidden) =
                ("Timestamp", "Unix time representation of date object", "timestamp", 4, 0, true)
        case .uniqueKey:
            (name, description, api, format, revision, hidden) =
                ("Unique object key", "Unique key used to ensure object uniqueness within the space", "unique_key", 0, 0, true)
        }
        return .object([
            "apiObjectKey": .string(api), "name": .string(name), "description": .string(description),
            "internalFlags": .array([]), "isHidden": .bool(hidden), "layout": .integer(5), "origin": .integer(7),
            "revision": .integer(revision), "sourceObject": .string("_br" + role.rawValue),
            "relationKey": .string(role.rawValue), "relationFormat": .integer(format),
            "relationFormatIncludeTime": .bool(role == .addedDate), "relationFormatObjectTypes": .array([]),
            "relationDefaultValue": .null, "relationMaxCount": .integer(role == .internalFlags ? 0 : 1),
            "relationReadonlyValue": .bool(true)
        ])
    }
}

public enum AnyHeartOriginalMetadataValue: Sendable {
    /// The original snapshot exists but contains no such relation key.
    case absent
    /// Preserves null, false, zero, empty text and empty arrays distinctly.
    case present(AnyJSON)
}

public struct AnyHeartOriginalMetadataSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let binding: AnyHeartOriginalMetadataBinding
    public let sourceObjectID: String
    public let value: AnyHeartOriginalMetadataValue
    public let catalog: AnyNativeImportedCatalogSnapshot
    public let definitionCatalog: AnyNativeImportedCatalogSnapshot
    public var permitsDestinationWrites: Bool { false }
    public var provesCurrentSourceValues: Bool { false }
    public var originalHistoryReconstructed: Bool { false }

    static func project(_ role: AnyHeartOriginalMetadataBinding.Role,
                        snapshot: AnyHeartNativeSnapshotView) -> AnyHeartOriginalMetadataValue {
        guard let field = snapshot.details.first(where: { $0.key.utf8.elementsEqual(role.rawValue.utf8) }) else { return .absent }
        return .present(field.value)
    }
}

/// Uses the same complete catalog reader for original Pages, definitions and
/// contexts. A missing snapshot is an explicit error rather than an empty set
/// of metadata. The complete captured snapshot stays available in `catalog`.
public struct AnyHeartOriginalMetadataStore: Sendable {
    public let workspace: AnyTorahWorkspace
    private let catalog: AnyNativeImportedCatalogStore

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        self.workspace = workspace
        self.catalog = try .init(client: client, workspace: workspace)
    }

    public func read(_ binding: AnyHeartOriginalMetadataBinding, sourceObjectID: String,
                     directory: AnyNativeImportedCatalogDirectory, lease: AnyHostLease) async throws -> AnyHeartOriginalMetadataSnapshot {
        try binding.requireSource(directory.source)
        // The role's original definition is independently bound to its current
        // immutable catalog row, not only to a saved client-side descriptor.
        let definition = try await catalog.read(sourceObjectID: binding.evidence.sourceObjectID,
            directory: directory, lease: lease)
        guard let definitionEvidence = definition.entry.evidence, definitionEvidence == binding.evidence else {
            throw AnyNativeImportedCatalogError.changedSource(binding.evidence.sourceObjectID)
        }
        let original = try await catalog.read(sourceObjectID: sourceObjectID, directory: directory, lease: lease)
        guard let evidence = original.entry.evidence else { throw AnyNativeImportedCatalogError.snapshotNotCaptured(sourceObjectID) }
        try await lease.validate()
        try Task.checkCancellation()
        return .init(workspace: workspace, generation: lease.generation, engineStartedAt: lease.engineStartedAt,
            binding: binding, sourceObjectID: sourceObjectID,
            value: AnyHeartOriginalMetadataSnapshot.project(binding.role, snapshot: evidence.snapshot),
            catalog: original, definitionCatalog: definition)
    }
}
