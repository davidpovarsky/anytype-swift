import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// A captured Heart definition selecting a runtime provider. It is never a
/// custom property alias, an archived value, or a grant to change permissions.
public struct AnyHeartNativeRuntimeRelationBinding: Codable, Equatable, Sendable {
    public static let contract = "pinkha-heart-runtime-relation-v1"

    public enum Scope: String, Codable, Sendable { case account, space, object }

    public enum Role: String, CaseIterable, Codable, Sendable {
        case readersLimit, writersLimit, sharedSpacesLimit
        case syncDate, syncError, syncStatus
        case spaceAccessType, spaceDashboardId

        public var scope: Scope {
            switch self {
            case .sharedSpacesLimit: .account
            case .readersLimit, .writersLimit, .spaceAccessType, .spaceDashboardId: .space
            case .syncDate, .syncError, .syncStatus: .object
            }
        }

        /// These two source definitions are writable. A runtime read binding
        /// preserves that fact; its own read operation grants no mutation.
        public var sourceDeclaresReadonlyValue: Bool {
            self != .spaceAccessType && self != .spaceDashboardId
        }

        var name: String {
            switch self {
            case .readersLimit: "Readers limit"
            case .writersLimit: "Writers limit"
            case .sharedSpacesLimit: "Shared spaces limit"
            case .syncDate: "Sync date"
            case .syncError: "Sync error"
            case .syncStatus: "Sync status"
            case .spaceAccessType: "Space access type"
            case .spaceDashboardId: "Space Dashboard ID"
            }
        }

        var description: String {
            switch self {
            case .syncDate: "Object sync date"
            case .syncError: "Object sync error"
            case .syncStatus: "Object sync status"
            case .spaceAccessType: "Space access type, see enum model.SpaceAccessType"
            case .spaceDashboardId: "Space Dashboard object ID"
            default: name
            }
        }

        var apiObjectKey: String {
            switch self {
            case .readersLimit: "readers_limit"
            case .writersLimit: "writers_limit"
            case .sharedSpacesLimit: "shared_spaces_limit"
            case .syncDate: "sync_date"
            case .syncError: "sync_error"
            case .syncStatus: "sync_status"
            case .spaceAccessType: "space_access_type"
            case .spaceDashboardId: "space_dashboard_id"
            }
        }

        var capturedDescriptor: AnyJSON {
            .object([
                "apiObjectKey": .string(apiObjectKey), "description": .string(description),
                "internalFlags": .array([]), "isHidden": .bool(true), "layout": .integer(5),
                "name": .string(name), "origin": .integer(7), "relationDefaultValue": .null,
                "relationFormat": .integer(self == .syncDate ? 4 : self == .spaceDashboardId ? 100 : 2),
                "relationFormatIncludeTime": .bool(self == .syncDate),
                "relationFormatObjectTypes": .array([]), "relationKey": .string(rawValue),
                "relationMaxCount": .integer(1), "relationReadonlyValue": .bool(sourceDeclaresReadonlyValue),
                "revision": .integer(self == .syncDate ? 1 : 0),
                "sourceObject": .string("_br" + rawValue),
            ])
        }
    }

    public let evidence: AnyDestinationDefinitionEvidence
    public let role: Role
    public let readContract: String
    public var sourceRelationKey: String { role.rawValue }
    public var sourceHidden: Bool { true }
    public var scope: Scope { role.scope }
    public var permitsDestinationWrites: Bool { false }

    public init(evidence: AnyDestinationDefinitionEvidence) throws {
        self.evidence = evidence
        guard let key = evidence.snapshot.details["relationKey"]?.string,
              let role = Role(rawValue: key), key.utf8.elementsEqual(role.rawValue.utf8) else {
            throw AnyDestinationMigrationError.invalidPlan("unknown runtime source relation")
        }
        self.role = role
        readContract = Self.contract
        try validate()
    }

    func requireSource(_ source: AnyDestinationSourceBinding, objectID: String) throws {
        try evidence.requireSource(source, objectID: objectID)
    }

    private func validate() throws {
        let row = evidence.snapshot
        guard readContract.utf8.elementsEqual(Self.contract.utf8), row.nativeType == 521,
              row.uniqueKey.utf8.elementsEqual(("rel-" + role.rawValue).utf8), row.issues.isEmpty,
              try AnyHostCanonical.bytes(.object(row.details), maximumBytes: 65_536) ==
                    AnyHostCanonical.bytes(role.capturedDescriptor, maximumBytes: 65_536) else {
            throw AnyDestinationMigrationError.invalidPlan("runtime source relation descriptor differs")
        }
    }

    private enum CodingKeys: String, CodingKey { case evidence, role, readContract }

    public init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        evidence = try container.decode(AnyDestinationDefinitionEvidence.self, forKey: .evidence)
        role = try container.decode(Role.self, forKey: .role)
        readContract = try container.decode(String.self, forKey: .readContract)
        try validate()
    }
}

/// The original numeric domains come from Heart's model, not Any's SyncState
/// ordinals. A provider must prove a semantic conversion before returning one.
public enum AnyHeartObjectSyncStatus: Int64, Codable, Sendable {
    case synced = 0, syncing = 1, error = 2, queued = 3
}

public enum AnyHeartObjectSyncError: Int64, Codable, Sendable {
    case none = 0, incompatibleVersion = 2, network = 3, oversized = 4
}

public enum AnyHeartSpaceAccessType: Int64, Codable, Sendable {
    case `private` = 0, personal = 1, shared = 2
}
