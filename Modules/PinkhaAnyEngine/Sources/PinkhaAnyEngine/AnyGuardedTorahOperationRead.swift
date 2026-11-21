import Foundation

/// An additive read contract; no existing native capability is sufficient to
/// activate it. The retained v9 runtime deliberately does not advertise it.
public struct AnyGuardedTorahOperationReadSnapshot: Sendable {
    public static let readContract = "pinkha-authorized-operation-read-v1"
    public static let maximumVariants = 256
    public static let maximumBytes = 4 * 1024 * 1024

    public enum Reachability: String, Sendable { case liveDocument, liveBlock, unreachableBlock }
    public struct Variant: Sendable {
        public let claim: AnyTorahClaim
        public let canonicalBytes: Data
        public let provenance: AnyGuardedClaimProvenance
        public let reachability: Reachability
    }

    public let spaceID: String
    public let rootObjectID: String
    public let operationID: String
    public let readinessGeneration: String
    public let variants: [Variant]
    public var absentInVerifiedLocalSnapshot: Bool { variants.isEmpty }

    public init(response: AnyJSON, expectedSpaceID: String,
                expectedRootObjectID: String, expectedOperationID: String) throws {
        try Self.validateOperationID(expectedOperationID)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        guard try encoder.encode(response).count <= Self.maximumBytes,
              let values = response["variants"]?.array, values.count <= Self.maximumVariants else {
            throw AnyEngineError.readLimit
        }
        guard response["contract"]?.string == AnyGuardedTorahCapabilities.contract,
              response["readContract"]?.string == Self.readContract,
              response["version"]?.integer == 1,
              response["scope"]?.string == "logical-operation-closure",
              response["spaceId"]?.string?.utf8.elementsEqual(expectedSpaceID.utf8) == true,
              response["rootObjectId"]?.string?.utf8.elementsEqual(expectedRootObjectID.utf8) == true,
              response["dataset"]?.string == AnyGuardedTorahCapabilities.dataset,
              response["operationId"]?.string == expectedOperationID,
              response["complete"]?.bool == true,
              response["outcome"]?.string == (values.isEmpty ? "absentInVerifiedLocalSnapshot" : "found"),
              !expectedSpaceID.isEmpty, !expectedRootObjectID.isEmpty else {
            throw AnyEngineError.invalidClaim("authorized operation read scope")
        }
        // Reuse the canonical/provenance decoder. A synthetic envelope is only
        // a decoder input; it does not assert whole-workspace completeness.
        let records = try values.map { value -> AnyJSON in
            guard let record = value["record"] else {
                throw AnyEngineError.invalidClaim("authorized operation record")
            }
            return record
        }
        let decoded = try AnyGuardedSnapshotRecords(response: .object([
            "contract": .string(AnyGuardedTorahCapabilities.contract),
            "spaceId": .string(expectedSpaceID), "rootObjectId": .string(expectedRootObjectID),
            "dataset": .string(AnyGuardedTorahCapabilities.dataset),
            "complete": .bool(true), "limit": .integer(Int64(Self.maximumVariants)),
            "records": .array(records), "readiness": response["readiness"] ?? .null
        ]), expectedSpaceID: expectedSpaceID, expectedRootObjectID: expectedRootObjectID,
           limit: Self.maximumVariants)
        let variants = try zip(values, decoded.claims).map { value, claim -> Variant in
            let operation = claim.operation
            guard operation.operationID == expectedOperationID,
                  operation.spaceID.utf8.elementsEqual(expectedSpaceID.utf8),
                  let raw = value["canonicalBytes"]?.string,
                  let bytes = Data(base64Encoded: raw), bytes.base64EncodedString() == raw,
                  bytes == operation.canonicalBytes,
                  let rawState = value["reachability"]?.string,
                  let state = Reachability(rawValue: rawState),
                  (operation.targetBlockID.isEmpty) == (state == .liveDocument),
                  let provenance = decoded.provenance[claim.id],
                  provenance.creator.utf8.elementsEqual(operation.authorID.utf8) else {
                throw AnyEngineError.invalidClaim("authorized operation bytes, provenance or target state")
            }
            return .init(claim: claim, canonicalBytes: bytes, provenance: provenance, reachability: state)
        }
        let ids = variants.map { $0.claim.id }
        guard ids == ids.sorted(), Set(ids).count == ids.count,
              Set(variants.map { $0.claim.operation.logicalKey }).count <= 1 else {
            throw AnyEngineError.invalidClaim("authorized operation logical closure")
        }
        self.spaceID = expectedSpaceID; self.rootObjectID = expectedRootObjectID
        self.operationID = expectedOperationID; self.variants = variants
        self.readinessGeneration = decoded.generation
    }

    static func validateOperationID(_ value: String) throws {
        guard value.utf8.count == 32, value.utf8.allSatisfy({
            (48...57).contains($0) || (97...102).contains($0)
        }) else { throw AnyEngineError.invalidOperation("operationID must be 32 lowercase hex characters") }
    }
}

extension AnyGuardedTorahClaimsRepository {
    public func readOperation(operationID: String) async throws -> AnyGuardedTorahOperationReadSnapshot {
        try AnyGuardedTorahOperationReadSnapshot.validateOperationID(operationID)
        try Task.checkCancellation()
        let capabilities = try await verifyCapabilities()
        guard capabilities.nativeAuthorizedOperationRead else {
            throw AnyEngineError.incompatibleSchema("nativeAuthorizedOperationRead")
        }
        let root = try await storageRoot()
        let response = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", spaceID, "pinkha", "operations", operationID],
            maximumResponseBytes: AnyGuardedTorahOperationReadSnapshot.maximumBytes)
        try Task.checkCancellation()
        return try .init(response: response, expectedSpaceID: spaceID,
                         expectedRootObjectID: root, expectedOperationID: operationID)
    }
}
