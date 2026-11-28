import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public struct AnyNativeRuntimeScope: Equatable, Sendable {
    public let accountID: String
    public let networkID: String
    public let spaceID: String
    /// May be an admitted guest identity rather than the account's main key.
    public let authorityIdentity: String
    public let aclHeadID: String

    public static func == (a: Self, b: Self) -> Bool {
        [a.accountID, a.networkID, a.spaceID, a.authorityIdentity, a.aclHeadID].map { Data($0.utf8) } ==
        [b.accountID, b.networkID, b.spaceID, b.authorityIdentity, b.aclHeadID].map { Data($0.utf8) }
    }
}

public struct AnyNativeMemberLimits: Equatable, Sendable {
    public let readers: UInt32
    public let writers: UInt32
}

public struct AnyNativeCoordinatorObservation: Sendable {
    public let fetchedAt: AnyNativeRuntimeTimestamp
    /// Original coordinator enum label. It is not an Any/Heart sync ordinal.
    public let status: String
    public let isShared: Bool
    /// nil means the accepted coordinator answer omitted its Limits payload.
    public let limits: AnyNativeMemberLimits?
}

public enum AnyNativeAccessObservationReason: String, Sendable {
    case personalProvenanceUnavailable = "personal_provenance_unavailable"
    case nativePersonal = "native_personal"
    case nativeACLShared = "native_acl_shared"
    case coordinatorShared = "coordinator_shared"
    case nativePrivate = "native_private"
    case coordinatorUnavailable = "coordinator_unavailable"
}

public struct AnyNativeAccessObservation: Sendable {
    public let aclIsEmpty: Bool
    public let personalSpaceID: String?
    /// The complete original classification is unresolved without positive
    /// Personal provenance. Sharing observations remain available separately.
    public let value: AnyHeartSpaceAccessType?
    public let reason: AnyNativeAccessObservationReason
}

public struct AnyNativeSpaceRuntimeSnapshot: Sendable {
    public let scope: AnyNativeRuntimeScope
    public let generation: UUID
    public let engineStartedAt: String
    public let capturedAt: AnyNativeRuntimeTimestamp
    /// nil means no accepted coordinator answer has been retained.
    public let coordinator: AnyNativeCoordinatorObservation?
    public let access: AnyNativeAccessObservation
    public var permitsDestinationWrites: Bool { false }
}

/// These names preserve the original SDK domain. They are intentionally not
/// integer-cast into Heart's synced0/syncing1/error2/queued3 domain.
public enum AnyNativeObservedSyncState: String, Sendable {
    case unknown, offline, syncing, synced, error
}

public enum AnyNativeObjectSyncBasis: String, Sendable {
    case perObjectHooks = "per_object_hooks"
    case responsibleSpaceRound = "responsible_space_round"
    case unobserved
}

public enum AnyNativeObservedP2PState: String, Sendable {
    case unknown
    case notPossible = "notpossible"
    case notConnected = "notconnected"
    case connected, restricted
}

public struct AnyNativeObjectSyncObservation: Sendable {
    public let state: AnyNativeObservedSyncState
    public let basis: AnyNativeObjectSyncBasis
    /// Actual last-applied or inherited complete-space confirmation time.
    /// It is neither a new successful round trip nor Heart's syncDate.
    public let lastSyncAt: AnyNativeRuntimeTimestamp?
}

public struct AnyNativeSpaceSyncObservation: Sendable {
    public let spaceID: String
    public let state: AnyNativeObservedSyncState
    public let lastSyncedAt: AnyNativeRuntimeTimestamp?
    public let synced: Int64
    public let total: Int64
    public let networkPeers: Int64
    public let localPeers: Int64
    public let globalPeers: Int64
    public let p2p: AnyNativeObservedP2PState
    public let networkProtocolIncompatible: Bool
}

public struct AnyNativeObjectRuntimeSnapshot: Sendable {
    public let scope: AnyNativeRuntimeScope
    public let generation: UUID
    public let engineStartedAt: String
    public let objectID: String
    public let capturedAt: AnyNativeRuntimeTimestamp
    public let objectSync: AnyNativeObjectSyncObservation
    public let spaceSync: AnyNativeSpaceSyncObservation
    public var permitsDestinationWrites: Bool { false }
    /// A tracker sample alone does not prove that an object exists or establish
    /// its Type. Consumers retain their existing native target-access checks.
    public var provesObjectExistence: Bool { false }
}

/// The optional, scoped native runtime-state contract. All current authority
/// work stays in the native read guard; this adapter also fences its account,
/// network, Space and host lifetime before delivery. It creates no local state.
public struct AnyNativeRuntimeStateStore: Sendable {
    public let workspace: AnyTorahWorkspace
    public let expectedNetworkID: String
    private let client: AnyHTTPClient

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace, expectedNetworkID: String) throws {
        guard client.expectedAccountID.utf8.elementsEqual(workspace.accountID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        guard Self.validIdentity(expectedNetworkID) else {
            throw AnyEngineError.invalidIdentity("runtime network")
        }
        self.client = client
        self.workspace = workspace
        self.expectedNetworkID = expectedNetworkID
    }

    public func space(lease: AnyHostLease) async throws -> AnyNativeSpaceRuntimeSnapshot {
        try await validate(lease)
        let raw = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", workspace.spaceID, "runtime-state"],
            maximumResponseBytes: 32_768, authorize: { try await validate(lease) })
        let snapshot = try Self.parseSpace(raw, workspace: workspace,
            expectedNetworkID: expectedNetworkID, lease: lease)
        try await validate(lease)
        return snapshot
    }

    public func object(_ objectID: String, lease: AnyHostLease) async throws -> AnyNativeObjectRuntimeSnapshot {
        guard AnyEditorBlock.validID(objectID) else { throw AnyHostError.invalidDocument(objectID) }
        try await validate(lease)
        let raw = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", workspace.spaceID, "objects", objectID, "runtime-state"],
            maximumResponseBytes: 32_768, authorize: { try await validate(lease) })
        let snapshot = try Self.parseObject(raw, objectID: objectID, workspace: workspace,
            expectedNetworkID: expectedNetworkID, lease: lease)
        try await validate(lease)
        return snapshot
    }

    static func parseSpace(_ raw: AnyJSON, workspace: AnyTorahWorkspace,
                           expectedNetworkID: String, lease: AnyHostLease) throws -> AnyNativeSpaceRuntimeSnapshot {
        try requireLeaseScope(lease, workspace: workspace)
        let row = try fields(raw, ["contract", "scope", "capturedAt", "coordinator", "access"])
        try requireExact(row["contract"], "pinkha-space-runtime-state-v1")
        let scope = try scope(row["scope"], workspace: workspace, expectedNetworkID: expectedNetworkID)
        let capturedAt = try timestamp(row["capturedAt"])
        let coordinator = try coordinator(row["coordinator"])
        let access = try access(row["access"], scope: scope, coordinator: coordinator)
        return .init(scope: scope, generation: lease.generation, engineStartedAt: lease.engineStartedAt,
            capturedAt: capturedAt, coordinator: coordinator, access: access)
    }

    static func parseObject(_ raw: AnyJSON, objectID: String, workspace: AnyTorahWorkspace,
                            expectedNetworkID: String, lease: AnyHostLease) throws -> AnyNativeObjectRuntimeSnapshot {
        try requireLeaseScope(lease, workspace: workspace)
        guard AnyEditorBlock.validID(objectID) else { throw AnyHostError.invalidDocument(objectID) }
        let row = try fields(raw, ["contract", "scope", "objectId", "capturedAt", "objectSync", "spaceSync"])
        try requireExact(row["contract"], "pinkha-object-runtime-state-v1")
        try requireExact(row["objectId"], objectID)
        let scope = try scope(row["scope"], workspace: workspace, expectedNetworkID: expectedNetworkID)
        let object = try fields(row["objectSync"], ["state", "basis", "lastSyncAt"])
        guard let state = object["state"]?.string.flatMap(AnyNativeObservedSyncState.init(rawValue:)),
              let basis = object["basis"]?.string.flatMap(AnyNativeObjectSyncBasis.init(rawValue:)) else {
            throw AnyEngineError.malformedResponse("native object sync domain")
        }
        let lastSyncAt = try optionalTimestamp(object["lastSyncAt"])
        if basis == .unobserved && (state != .unknown || lastSyncAt != nil) {
            throw AnyEngineError.malformedResponse("unobserved object sync contradiction")
        }
        if basis == .responsibleSpaceRound && (state != .synced || lastSyncAt == nil) {
            throw AnyEngineError.malformedResponse("responsible-space sync confirmation missing")
        }
        return .init(scope: scope, generation: lease.generation, engineStartedAt: lease.engineStartedAt,
            objectID: objectID, capturedAt: try timestamp(row["capturedAt"]),
            objectSync: .init(state: state, basis: basis, lastSyncAt: lastSyncAt),
            spaceSync: try spaceSync(row["spaceSync"], spaceID: workspace.spaceID))
    }

    private func validate(_ lease: AnyHostLease) async throws {
        try Self.requireLeaseScope(lease, workspace: workspace)
        try await lease.validate()
        try Task.checkCancellation()
    }

    private static func requireLeaseScope(_ lease: AnyHostLease, workspace: AnyTorahWorkspace) throws {
        guard lease.workspace.accountID.utf8.elementsEqual(workspace.accountID.utf8),
              lease.workspace.spaceID.utf8.elementsEqual(workspace.spaceID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
    }

    private static func validIdentity(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1024 && !value.utf8.contains(0)
    }

    private static func fields(_ raw: AnyJSON?, _ keys: Set<String>) throws -> [String: AnyJSON] {
        guard let row = raw?.object, Set(row.keys) == keys else {
            throw AnyEngineError.malformedResponse("native runtime object fields")
        }
        return row
    }

    private static func identity(_ raw: AnyJSON?) throws -> String {
        guard let value = raw?.string, validIdentity(value) else {
            throw AnyEngineError.malformedResponse("native runtime identity")
        }
        return value
    }

    private static func requireExact(_ raw: AnyJSON?, _ expected: String) throws {
        guard let actual = raw?.string, actual.utf8.elementsEqual(expected.utf8) else {
            throw AnyEngineError.malformedResponse("native runtime identity or contract differs")
        }
    }

    private static func timestamp(_ raw: AnyJSON?) throws -> AnyNativeRuntimeTimestamp {
        guard let value = raw?.string else { throw AnyEngineError.malformedResponse("native runtime time") }
        return try .init(value)
    }

    private static func optionalTimestamp(_ raw: AnyJSON?) throws -> AnyNativeRuntimeTimestamp? {
        if case .some(.null) = raw { return nil }
        return try timestamp(raw)
    }

    private static func count(_ raw: AnyJSON?) throws -> Int64 {
        guard let value = raw?.integer, value >= 0 else { throw AnyEngineError.malformedResponse("native runtime count") }
        return value
    }

    private static func memberLimit(_ raw: AnyJSON?) throws -> UInt32 {
        guard let value = raw?.integer, let bounded = UInt32(exactly: value) else {
            throw AnyEngineError.malformedResponse("native member limit")
        }
        return bounded
    }

    private static func scope(_ raw: AnyJSON?, workspace: AnyTorahWorkspace,
                              expectedNetworkID: String) throws -> AnyNativeRuntimeScope {
        guard validIdentity(expectedNetworkID) else { throw AnyEngineError.invalidIdentity("runtime network") }
        let row = try fields(raw, ["accountId", "networkId", "spaceId", "authorityIdentity", "aclHeadId"])
        try requireExact(row["accountId"], workspace.accountID)
        try requireExact(row["spaceId"], workspace.spaceID)
        try requireExact(row["networkId"], expectedNetworkID)
        return try .init(accountID: identity(row["accountId"]), networkID: identity(row["networkId"]),
            spaceID: identity(row["spaceId"]), authorityIdentity: identity(row["authorityIdentity"]),
            aclHeadID: identity(row["aclHeadId"]))
    }

    private static func coordinator(_ raw: AnyJSON?) throws -> AnyNativeCoordinatorObservation? {
        if case .some(.null) = raw { return nil }
        let row = try fields(raw, ["fetchedAt", "status", "isShared", "limits"])
        guard let status = row["status"]?.string, !status.isEmpty, status.utf8.count <= 128,
              !status.utf8.contains(0), let shared = row["isShared"]?.bool else {
            throw AnyEngineError.malformedResponse("native coordinator answer")
        }
        let limits: AnyNativeMemberLimits?
        if row["limits"] == .null { limits = nil }
        else {
            let values = try fields(row["limits"], ["readersLimit", "writersLimit"])
            limits = try .init(readers: memberLimit(values["readersLimit"]), writers: memberLimit(values["writersLimit"]))
        }
        return try .init(fetchedAt: timestamp(row["fetchedAt"]), status: status, isShared: shared, limits: limits)
    }

    private static func access(_ raw: AnyJSON?, scope: AnyNativeRuntimeScope,
                               coordinator: AnyNativeCoordinatorObservation?) throws -> AnyNativeAccessObservation {
        let row = try fields(raw, ["aclIsEmpty", "personalSpaceId", "value", "reason"])
        guard let empty = row["aclIsEmpty"]?.bool,
              let reason = row["reason"]?.string.flatMap(AnyNativeAccessObservationReason.init(rawValue:)) else {
            throw AnyEngineError.malformedResponse("native access evidence")
        }
        let personal: String?
        if row["personalSpaceId"] == .null { personal = nil }
        else { personal = try identity(row["personalSpaceId"]) }
        let value: AnyHeartSpaceAccessType?
        if row["value"] == .null { value = nil }
        else {
            guard let ordinal = row["value"]?.integer, let typed = AnyHeartSpaceAccessType(rawValue: ordinal) else {
                throw AnyEngineError.malformedResponse("native access value")
            }
            value = typed
        }
        switch (value, reason) {
        case (nil, .personalProvenanceUnavailable):
            guard personal == nil else { throw AnyEngineError.malformedResponse("native Personal provenance contradiction") }
        case (.some(.personal), .nativePersonal):
            guard let personal, personal.utf8.elementsEqual(scope.spaceID.utf8) else {
                throw AnyEngineError.malformedResponse("native Personal identity")
            }
        case (.some(.shared), .nativeACLShared):
            try requireOtherPersonal(personal, spaceID: scope.spaceID)
            guard !empty else { throw AnyEngineError.malformedResponse("native shared ACL contradiction") }
        case (.some(.shared), .coordinatorShared):
            try requireOtherPersonal(personal, spaceID: scope.spaceID)
            guard empty, coordinator?.isShared == true else {
                throw AnyEngineError.malformedResponse("native coordinator sharing contradiction")
            }
        case (.some(.private), .nativePrivate):
            try requireOtherPersonal(personal, spaceID: scope.spaceID)
            guard empty, coordinator?.isShared == false else {
                throw AnyEngineError.malformedResponse("native private evidence missing")
            }
        case (nil, .coordinatorUnavailable):
            try requireOtherPersonal(personal, spaceID: scope.spaceID)
            guard empty, coordinator == nil else {
                throw AnyEngineError.malformedResponse("native coordinator absence contradiction")
            }
        default: throw AnyEngineError.malformedResponse("native access reason and value differ")
        }
        return .init(aclIsEmpty: empty, personalSpaceID: personal, value: value, reason: reason)
    }

    private static func requireOtherPersonal(_ personal: String?, spaceID: String) throws {
        guard let personal, !personal.utf8.elementsEqual(spaceID.utf8) else {
            throw AnyEngineError.malformedResponse("native non-Personal provenance missing")
        }
    }

    private static func spaceSync(_ raw: AnyJSON?, spaceID: String) throws -> AnyNativeSpaceSyncObservation {
        let row = try fields(raw, ["spaceId", "state", "lastSyncedAt", "synced", "total", "networkPeers",
            "localPeers", "globalPeers", "p2p", "networkProtocolIncompatible"])
        try requireExact(row["spaceId"], spaceID)
        guard let state = row["state"]?.string.flatMap(AnyNativeObservedSyncState.init(rawValue:)),
              let p2p = row["p2p"]?.string.flatMap(AnyNativeObservedP2PState.init(rawValue:)),
              let incompatible = row["networkProtocolIncompatible"]?.bool else {
            throw AnyEngineError.malformedResponse("native space sync domain")
        }
        let synced = try count(row["synced"]), total = try count(row["total"])
        guard synced <= total else { throw AnyEngineError.malformedResponse("native space sync count contradiction") }
        return try .init(spaceID: spaceID, state: state, lastSyncedAt: optionalTimestamp(row["lastSyncedAt"]),
            synced: synced, total: total, networkPeers: count(row["networkPeers"]),
            localPeers: count(row["localPeers"]), globalPeers: count(row["globalPeers"]), p2p: p2p,
            networkProtocolIncompatible: incompatible)
    }
}
