import Foundation

/// Shared policy only. Native adapters still own signed history, current ACL,
/// target eligibility, and the account/Space lifetime lease.
public enum TorahAuthorizedOperationReadContract {
    public static let identifier = "pinkha-authorized-operation-read-v1"
    public static let maximumVariants = 256
    public static let maximumResponseBytes = 4 * 1024 * 1024

    public static func validateOperationID(_ value: String) throws {
        guard hex(value, count: 32) else { throw TorahOperationReadError.invalidRequest }
    }

    static func hex(_ value: String, count: Int) -> Bool {
        value.utf8.count == count && value.utf8.allSatisfy {
            (48...57).contains($0) || (97...102).contains($0)
        }
    }

    static func text(_ value: String, maximum: Int = 1024) -> Bool {
        !value.isEmpty && value.utf8.count <= maximum && !value.utf8.contains(0)
    }

    static func exact(_ left: String, _ right: String) -> Bool {
        left.utf8.elementsEqual(right.utf8)
    }
}

public enum TorahOperationReadError: Error, Sendable, Equatable {
    case unsupportedContract
    case invalidRequest
    case historyUnavailable
    case targetStateUnavailable
    case permissionDenied
    case accountChanged
    case snapshotChanged
    case projectionBehind
    case readLimit
    case malformedNativeResponse
    case nativeFailure
}

public enum TorahOperationEngine: String, Sendable { case heart, any }

/// This binding is captured by an adapter from its owned engine lifetime. It
/// grants no authority and is never sent as a caller-supplied ACL assertion.
public struct TorahOperationReadScope: Sendable, Equatable {
    public let engine: TorahOperationEngine
    public let accountID: String
    public let spaceID: String
    public let sessionGeneration: UUID

    public init(engine: TorahOperationEngine, accountID: String, spaceID: String,
                sessionGeneration: UUID) throws {
        guard TorahAuthorizedOperationReadContract.text(accountID),
              TorahAuthorizedOperationReadContract.text(spaceID) else {
            throw TorahOperationReadError.invalidRequest
        }
        self.engine = engine; self.accountID = accountID
        self.spaceID = spaceID; self.sessionGeneration = sessionGeneration
    }

    public static func == (left: Self, right: Self) -> Bool {
        left.engine == right.engine && left.sessionGeneration == right.sessionGeneration
            && TorahAuthorizedOperationReadContract.exact(left.accountID, right.accountID)
            && TorahAuthorizedOperationReadContract.exact(left.spaceID, right.spaceID)
    }
}

/// An unreachable block belongs to a still-live eligible document. It is not a
/// claim that the block was deleted or ever existed. Whole missing objects and
/// malformed/ambiguous graphs are errors and cannot appear in a successful read.
public enum TorahOperationTargetReachability: String, Sendable, Equatable {
    case liveDocument
    case liveBlock
    case unreachableBlock
}

public struct TorahOperationReadProvenance: Sendable, Equatable {
    public let creator: String
    public let nativeChangeID: String
    public let nativeACLHeadID: String

    public init(creator: String, nativeChangeID: String, nativeACLHeadID: String) throws {
        guard [creator, nativeChangeID, nativeACLHeadID].allSatisfy({
            TorahAuthorizedOperationReadContract.text($0)
        }) else { throw TorahOperationReadError.malformedNativeResponse }
        self.creator = creator; self.nativeChangeID = nativeChangeID
        self.nativeACLHeadID = nativeACLHeadID
    }
}

/// Canonical identity/hash/signature validation belongs to the native decoder.
/// This value preserves its exact bytes and validates the shared release shape;
/// constructing it is not independent verification of a signed native change.
public struct TorahAuthorizedOperationVariant: Sendable, Equatable {
    public let claimID: String
    public let operationID: String
    public let spaceID: String
    public let authorID: String
    public let target: TorahAssociationTarget
    public let canonicalBytes: Data
    public let provenance: [TorahOperationReadProvenance]
    public let reachability: TorahOperationTargetReachability

    public init(claimID: String, operationID: String, spaceID: String, authorID: String,
                target: TorahAssociationTarget, canonicalBytes: Data,
                provenance: [TorahOperationReadProvenance],
                reachability: TorahOperationTargetReachability) throws {
        let parts = claimID.split(separator: "/", omittingEmptySubsequences: false)
        guard parts.count == 2, parts.allSatisfy({
            TorahAuthorizedOperationReadContract.hex(String($0), count: 64)
        }), TorahAuthorizedOperationReadContract.hex(operationID, count: 32),
           [spaceID, authorID, target.objectId].allSatisfy({
               TorahAuthorizedOperationReadContract.text($0)
           }), target.blockId.map({ TorahAuthorizedOperationReadContract.text($0) }) ?? true,
           !canonicalBytes.isEmpty, !provenance.isEmpty,
           provenance.count <= TorahAuthorizedOperationReadContract.maximumVariants,
           provenance.allSatisfy({ TorahAuthorizedOperationReadContract.exact($0.creator, authorID) }) else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        guard canonicalBytes.count <= TorahAuthorizedOperationReadContract.maximumResponseBytes else {
            throw TorahOperationReadError.readLimit
        }
        guard (target.blockId == nil) == (reachability == .liveDocument) else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        var seen = Set<Data>()
        for item in provenance {
            // Length framing avoids treating embedded separators as identity.
            let fields = [item.creator, item.nativeChangeID, item.nativeACLHeadID]
            let key = Data(fields.map { "\($0.utf8.count):\($0)" }.joined().utf8)
            guard seen.insert(key).inserted else { throw TorahOperationReadError.malformedNativeResponse }
        }
        self.claimID = claimID; self.operationID = operationID
        self.spaceID = spaceID; self.authorID = authorID; self.target = target
        self.canonicalBytes = canonicalBytes; self.provenance = provenance
        self.reachability = reachability
    }
}

public enum TorahOperationReadOutcome: String, Sendable, Equatable {
    case found
    case absentInVerifiedLocalSnapshot
}

public struct TorahAuthorizedOperationSnapshot: Sendable, Equatable {
    public let scope: TorahOperationReadScope
    public let operationID: String
    public let outcome: TorahOperationReadOutcome
    /// Opaque identity of the native local snapshot/authority. Not a causal or
    /// cross-replica clock, permission token, or reusable account authorization.
    public let nativeSnapshotToken: String
    public let variants: [TorahAuthorizedOperationVariant]
    public var conflicted: Bool { variants.count > 1 }

    public init(scope: TorahOperationReadScope, operationID: String,
                outcome: TorahOperationReadOutcome, nativeSnapshotToken: String,
                complete: Bool, variants: [TorahAuthorizedOperationVariant]) throws {
        try TorahAuthorizedOperationReadContract.validateOperationID(operationID)
        guard complete, TorahAuthorizedOperationReadContract.hex(nativeSnapshotToken, count: 64),
              variants.isEmpty == (outcome == .absentInVerifiedLocalSnapshot) else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        guard variants.count <= TorahAuthorizedOperationReadContract.maximumVariants else {
            throw TorahOperationReadError.readLimit
        }
        var seen = Set<String>()
        var logicalKey: Substring?
        // A second decoded-payload budget. Each adapter must also bound the
        // entire encoded native response, including fields and framing, to 4MiB.
        var totalBytes = 0
        for variant in variants {
            guard TorahAuthorizedOperationReadContract.exact(variant.spaceID, scope.spaceID),
                  variant.operationID == operationID, seen.insert(variant.claimID).inserted else {
                throw TorahOperationReadError.malformedNativeResponse
            }
            let key = variant.claimID.prefix(64)
            guard logicalKey == nil || key == logicalKey else {
                throw TorahOperationReadError.malformedNativeResponse
            }
            logicalKey = key
            totalBytes += variant.canonicalBytes.count
            totalBytes += variant.provenance.reduce(0) {
                $0 + $1.creator.utf8.count + $1.nativeChangeID.utf8.count + $1.nativeACLHeadID.utf8.count
            }
            guard totalBytes <= TorahAuthorizedOperationReadContract.maximumResponseBytes else {
                throw TorahOperationReadError.readLimit
            }
        }
        let ordered = variants.sorted { $0.claimID < $1.claimID }
        guard ordered.map(\.claimID) == variants.map(\.claimID) else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        self.scope = scope; self.operationID = operationID; self.outcome = outcome
        self.nativeSnapshotToken = nativeSnapshotToken; self.variants = variants
    }
}

/// Reads return one atomic, fully authorized closure. Errors release no partial
/// payload. Implementations must revalidate their owned lifetime after awaits.
public protocol TorahAuthorizedOperationReading: Sendable {
    var scope: TorahOperationReadScope { get }
    func readOperation(operationID: String) async throws -> TorahAuthorizedOperationSnapshot
}
