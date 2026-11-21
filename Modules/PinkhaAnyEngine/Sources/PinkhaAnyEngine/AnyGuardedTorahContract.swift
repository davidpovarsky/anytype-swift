import Foundation

/// Capabilities belong to the compiled native module. A generic immutable
/// records bundle never implies native signature, current-ACL or target guards.
public struct AnyGuardedTorahCapabilities: Sendable, Equatable {
    public static let contract = "pinkha-torah-native-v1"
    public static let bundleID = "pinkha/torah-native/v1"
    public static let module = "pinkha_torah_native"
    public static let dataset = "pinkha_torah_claims_v1"
    public static let dataVersion = "pinkha-torah-native-claims-v1"
    public static let maximumRecords = 10000
    public static let maximumBytes = 16 * 1024 * 1024
    public let conditionalBlockPatch: Bool
    public let conditionalPropertiesSet: Bool
    public let nativeDocumentProperties: Bool
    public let nativeIndexedSourceQuery: Bool
    public let nativeRelatedVersion: Int
    public let nativeObjectClaimsSnapshot: Bool
    public let nativeObjectClaimsWatch: Bool
    public let nativeAuthorizedOperationRead: Bool

    public init(response: AnyJSON) throws {
        for (key, value) in [
            ("contract", Self.contract), ("bundleId", Self.bundleID),
            ("module", Self.module), ("dataset", Self.dataset),
            ("dataVersion", Self.dataVersion),
            ("associationBlockDataset", "editor_blocks"),
            ("nativeSemanticPayload", "canonical-associations-v2-single-record")
        ] {
            guard response[key]?.string == value else {
                throw AnyEngineError.incompatibleSchema("native " + key)
            }
        }
        guard response["allowedTargetTypes"]?.array == [.string("page")] else {
            throw AnyEngineError.incompatibleSchema("native target types")
        }
        for key in ["nativeSignedClaims", "spaceWideOperationConflictDomain",
                    "currentACLCommitFence", "targetTreeCommitFence",
                    "nativeClaimsSnapshot", "nativeClaimsWatch"] {
            guard response[key]?.integer == 1 else {
                throw AnyEngineError.incompatibleSchema("native " + key)
            }
        }
        guard response["nativeClaimsMaxRecords"]?.integer == Int64(Self.maximumRecords),
              response["nativeClaimsMaxBytes"]?.integer == Int64(Self.maximumBytes) else {
            throw AnyEngineError.incompatibleSchema("native snapshot bounds")
        }
        conditionalBlockPatch = response["conditionalBlockPatch"]?.integer == 1
        conditionalPropertiesSet = response["conditionalPropertiesSet"]?.integer == 1
        nativeDocumentProperties = response["nativeDocumentProperties"]?.integer == 1
        nativeIndexedSourceQuery = response["nativeIndexedSourceQuery"]?.integer == 1
        nativeRelatedVersion = response["nativeRelatedVersion"]?.integer == 1 ? 1 : 0
        nativeObjectClaimsSnapshot = response["nativeObjectClaimsSnapshot"]?.integer == 1
        nativeObjectClaimsWatch = response["nativeObjectClaimsWatch"]?.integer == 1
        nativeAuthorizedOperationRead = response["nativeAuthorizedOperationRead"]?.integer == 1
            && response["authorizedOperationReadContract"]?.string == AnyGuardedTorahOperationReadSnapshot.readContract
            && response["authorizedOperationReadMaxVariants"]?.integer == Int64(AnyGuardedTorahOperationReadSnapshot.maximumVariants)
            && response["authorizedOperationReadMaxBytes"]?.integer == Int64(AnyGuardedTorahOperationReadSnapshot.maximumBytes)
    }
}

/// Native provenance is returned by the compiled module, not accepted from an
/// operation payload. This API does not independently verify a signed envelope.
public struct AnyGuardedClaimProvenance: Sendable, Equatable {
    public let creator: String
    public let changeID: String
    public let aclHeadID: String
}


public struct AnyGuardedTorahSnapshot: Sendable {
    public let spaceID: String
    public let rootObjectID: String
    public let readinessGeneration: String
    public let projection: AnyTorahProjection
    public let provenance: [String: AnyGuardedClaimProvenance]

    /// A full workspace snapshot never accepts an object closure as complete
    /// workspace state, even when its native records are otherwise canonical.
    public init(response: AnyJSON, expectedSpaceID: String,
                expectedRootObjectID: String, limit: Int = 10000) throws {
        guard response["scope"] == nil, response["targetObjectId"] == nil,
              response["reachableClaimBlockIds"] == nil else {
            throw AnyEngineError.invalidClaim("scoped snapshot is not a complete workspace")
        }
        let decoded = try AnyGuardedSnapshotRecords(response: response,
            expectedSpaceID: expectedSpaceID, expectedRootObjectID: expectedRootObjectID, limit: limit)
        spaceID = expectedSpaceID; rootObjectID = expectedRootObjectID
        readinessGeneration = decoded.generation
        projection = try AnyTorahProjection(claims: decoded.claims, limit: limit)
        provenance = decoded.provenance
    }
}

/// Exact object history plus every global variant of its seeded logical keys.
/// Witnesses stay in `projection.all` and conflicts. Only the requested object's
/// unconflicted claims can be live; witness filtering before folding is forbidden.
public struct AnyGuardedTorahObjectSnapshot: Sendable {
    public let spaceID: String
    public let rootObjectID: String
    public let targetObjectID: String
    public let reachableClaimBlockIDs: Set<String>
    public let readinessGeneration: String
    public let projection: AnyTorahProjection
    public let provenance: [String: AnyGuardedClaimProvenance]

    public init(response: AnyJSON, expectedSpaceID: String,
                expectedRootObjectID: String, expectedObjectID: String, limit: Int = 10000) throws {
        try Self.validateObjectID(expectedObjectID)
        guard response["scope"]?.string == "object-logical-closure",
              response["version"]?.integer == 1,
              response["targetObjectId"]?.string == expectedObjectID,
              let reachable = response["reachableClaimBlockIds"]?.array else {
            throw AnyEngineError.invalidClaim("native object snapshot scope")
        }
        let decoded = try AnyGuardedSnapshotRecords(response: response,
            expectedSpaceID: expectedSpaceID, expectedRootObjectID: expectedRootObjectID, limit: limit)
        let seeds = decoded.claims.filter { $0.operation.targetObjectID == expectedObjectID }
        let seededKeys = Set(seeds.map { $0.operation.logicalKey })
        // Foreign witnesses have meaning only as variants of a requested
        // object's key. They are quarantined before observed-remove folding,
        // so their unrelated predecessor chains need not be fetched.
        guard decoded.claims.allSatisfy({
            $0.operation.targetObjectID == expectedObjectID || seededKeys.contains($0.operation.logicalKey)
        }) else { throw AnyEngineError.invalidClaim("unseeded foreign collision witness") }
        let blocks = try reachable.map { value -> String in
            guard let id = value.string else { throw AnyEngineError.invalidClaim("reachable block ID") }
            try Self.validateObjectID(id)
            return id
        }
        let declared = seeds.map { $0.operation.targetBlockID }.filter { !$0.isEmpty }
        guard blocks.count == Set(blocks).count,
              blocks == blocks.sorted(by: { $0.utf8.lexicographicallyPrecedes($1.utf8) }),
              Set(blocks).isSubset(of: Set(declared)) else {
            throw AnyEngineError.invalidClaim("noncanonical native block reachability")
        }
        let projection = try AnyTorahProjection(claims: decoded.claims, limit: limit)
        guard projection.live.allSatisfy({ $0.operation.targetObjectID == expectedObjectID }) else {
            throw AnyEngineError.invalidClaim("foreign live claim in object closure")
        }
        self.spaceID = expectedSpaceID; self.rootObjectID = expectedRootObjectID
        self.targetObjectID = expectedObjectID
        self.reachableClaimBlockIDs = Set(blocks)
        self.readinessGeneration = decoded.generation
        self.projection = projection; self.provenance = decoded.provenance
    }

    static func validateObjectID(_ value: String) throws {
        guard !value.isEmpty, value.utf8.count <= 1024, !value.utf8.contains(0),
              value != ".", value != ".." else { throw AnyEngineError.invalidIdentity("native object") }
    }
}

public struct AnyGuardedTorahObjectLiveSnapshot: Sendable {
    public let generation: UUID
    public let snapshot: AnyGuardedTorahObjectSnapshot
    public let initial: Bool
    public init(generation: UUID, snapshot: AnyGuardedTorahObjectSnapshot, initial: Bool) {
        self.generation = generation; self.snapshot = snapshot; self.initial = initial
    }
}

/// One decoder owns canonical records/provenance and envelope bounds for both
/// native read scopes. Scope-specific completeness checks remain above.
struct AnyGuardedSnapshotRecords {
    let generation: String
    let claims: [AnyTorahClaim]
    let provenance: [String: AnyGuardedClaimProvenance]

    init(response: AnyJSON, expectedSpaceID: String,
         expectedRootObjectID: String, limit: Int) throws {
        guard (1...AnyGuardedTorahCapabilities.maximumRecords).contains(limit),
              response["complete"]?.bool == true,
              response["limit"]?.integer == Int64(limit),
              let records = response["records"]?.array, records.count <= limit else {
            throw AnyEngineError.readLimit
        }
        guard response["contract"]?.string == AnyGuardedTorahCapabilities.contract,
              response["spaceId"]?.string == expectedSpaceID, !expectedSpaceID.isEmpty,
              response["rootObjectId"]?.string == expectedRootObjectID, !expectedRootObjectID.isEmpty,
              response["dataset"]?.string == AnyGuardedTorahCapabilities.dataset,
              response["readiness"]?["version"]?.integer == 1,
              response["readiness"]?["state"]?.string == "ready-local-snapshot",
              let generation = response["readiness"]?["generation"]?.string,
              generation.utf8.count == 64, generation.utf8.allSatisfy({
                (48...57).contains($0) || (97...102).contains($0)
              }) else { throw AnyEngineError.invalidClaim("native snapshot scope or readiness") }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        guard try encoder.encode(response).count <= AnyGuardedTorahCapabilities.maximumBytes else {
            throw AnyEngineError.readLimit
        }
        var seen = Set<String>()
        var metadata: [String: AnyGuardedClaimProvenance] = [:]
        let claims = try records.map { row -> AnyTorahClaim in
            let operation = try AnyTorahOperation.fromRecord(row, expectedSpaceID: expectedSpaceID)
            guard row["id"]?.string == operation.recordID, seen.insert(operation.recordID).inserted else {
                throw AnyEngineError.invalidClaim("duplicate or noncanonical native record ID")
            }
            if let owner = row["_objectId"] {
                guard owner.string == expectedRootObjectID else { throw AnyEngineError.invalidClaim("foreign native root") }
            }
            let creator = try row.requireString("creator")
            let change = try row.requireString("nativeChangeId")
            let acl = try row.requireString("nativeACLHeadId")
            guard [change, acl].allSatisfy({
                !$0.isEmpty && $0.utf8.count <= 1024 && !$0.utf8.contains(0)
            }) else { throw AnyEngineError.invalidClaim("missing native provenance") }
            let claim = try AnyTorahClaim(operation: operation, creator: creator)
            metadata[claim.id] = .init(creator: creator, changeID: change, aclHeadID: acl)
            return claim
        }
        self.generation = generation; self.claims = claims; self.provenance = metadata
    }
}
