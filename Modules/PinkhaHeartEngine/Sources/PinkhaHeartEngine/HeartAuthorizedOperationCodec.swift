import Foundation
import PinkhaKit
import SwiftProtobuf

/// Decodes the generated additive Heart RPC. It verifies the immutable binary
/// identity envelope; signed history and current ACL authority remain native.
enum HeartAuthorizedOperationCodec {
    typealias Wire = Anytype_PinkhaTorahAuthorizedOperationRead

    static func request(operationID: String, scope: TorahOperationReadScope) throws -> Data {
        guard scope.engine == .heart else { throw TorahOperationReadError.invalidRequest }
        try TorahAuthorizedOperationReadContract.validateOperationID(operationID)
        var request = Wire.Request()
        request.protocolVersion = 1
        request.spaceID = scope.spaceID
        request.operationID = operationID
        let bytes = try request.serializedData()
        guard bytes.count <= 2048 else { throw TorahOperationReadError.invalidRequest }
        return bytes
    }

    static func decode(_ bytes: Data, operationID: String,
                       scope: TorahOperationReadScope) throws -> TorahAuthorizedOperationSnapshot {
        guard scope.engine == .heart else { throw TorahOperationReadError.invalidRequest }
        try TorahAuthorizedOperationReadContract.validateOperationID(operationID)
        guard bytes.count <= TorahAuthorizedOperationReadContract.maximumResponseBytes else {
            throw TorahOperationReadError.readLimit
        }
        let response: Wire.Response
        do { response = try Wire.Response(serializedBytes: bytes) }
        catch { throw TorahOperationReadError.malformedNativeResponse }
        guard response.unknownFields == UnknownStorage(), response.hasError,
              response.error.unknownFields == UnknownStorage() else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        guard response.protocolVersion == 1 else { throw TorahOperationReadError.unsupportedContract }
        if response.error.code != .null {
            guard !response.hasSnapshot else { throw TorahOperationReadError.malformedNativeResponse }
            throw nativeError(response.error.code)
        }
        guard response.hasSnapshot, response.error.description_p.isEmpty else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        let value = response.snapshot
        guard value.unknownFields == UnknownStorage(),
              exact(value.contract, TorahAuthorizedOperationReadContract.identifier),
              exact(value.accountID, scope.accountID), exact(value.spaceID, scope.spaceID),
              exact(value.operationID, operationID), value.complete else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        guard value.variants.count <= TorahAuthorizedOperationReadContract.maximumVariants else {
            throw TorahOperationReadError.readLimit
        }
        let outcome: TorahOperationReadOutcome
        switch value.outcome {
        case .found: outcome = .found
        case .absentInVerifiedLocalSnapshot: outcome = .absentInVerifiedLocalSnapshot
        default: throw TorahOperationReadError.malformedNativeResponse
        }
        // Build all variants before releasing any payload. One invalid variant
        // rejects the entire logical operation, including every other variant.
        let variants = try value.variants.map { try variant($0, operationID: operationID, scope: scope) }
        return try TorahAuthorizedOperationSnapshot(scope: scope, operationID: operationID,
            outcome: outcome, nativeSnapshotToken: value.nativeSnapshotToken,
            complete: value.complete, variants: variants)
    }

    private static func variant(_ value: Wire.Variant, operationID: String,
                                scope: TorahOperationReadScope) throws -> TorahAuthorizedOperationVariant {
        guard value.unknownFields == UnknownStorage(), value.hasTarget,
              value.target.unknownFields == UnknownStorage() else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        let canonical = try HeartNativeOperationCanonical(exactBytes: value.canonicalBytes)
        guard exact(value.claimID, canonical.claimID), exact(value.operationID, operationID),
              exact(value.operationID, canonical.operationID), exact(value.spaceID, scope.spaceID),
              exact(value.spaceID, canonical.spaceID), exact(value.authorID, canonical.authorID),
              exact(value.target.objectID, canonical.target.objectId),
              exact(value.target.blockID, canonical.target.blockId ?? "") else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        guard !value.provenance.isEmpty,
              value.provenance.count <= TorahAuthorizedOperationReadContract.maximumVariants else {
            throw TorahOperationReadError.malformedNativeResponse
        }
        var nativeChanges = Set<Data>()
        let provenance = try value.provenance.map { item in
            guard item.unknownFields == UnknownStorage(), exact(item.creator, canonical.authorID),
                  nativeChanges.insert(Data(item.nativeChangeID.utf8)).inserted else {
                throw TorahOperationReadError.malformedNativeResponse
            }
            return try TorahOperationReadProvenance(creator: item.creator,
                nativeChangeID: item.nativeChangeID, nativeACLHeadID: item.nativeAclHeadID)
        }
        let reachability: TorahOperationTargetReachability
        switch value.reachability {
        case .liveDocument: reachability = .liveDocument
        case .liveBlock: reachability = .liveBlock
        case .unreachableBlock: reachability = .unreachableBlock
        default: throw TorahOperationReadError.malformedNativeResponse
        }
        return try TorahAuthorizedOperationVariant(claimID: canonical.claimID,
            operationID: canonical.operationID, spaceID: canonical.spaceID, authorID: canonical.authorID,
            target: canonical.target, canonicalBytes: canonical.bytes, provenance: provenance,
            reachability: reachability)
    }

    private static func nativeError(_ code: Wire.Response.Error.Code) -> any Error {
        switch code {
        case .badInput: return TorahOperationReadError.invalidRequest
        case .unsupportedVersion: return TorahOperationReadError.unsupportedContract
        case .permissionDenied: return TorahOperationReadError.permissionDenied
        case .notLoggedIn, .accountChanged: return TorahOperationReadError.accountChanged
        case .targetStateUnavailable: return TorahOperationReadError.targetStateUnavailable
        case .historyUnavailable: return TorahOperationReadError.historyUnavailable
        case .snapshotChanged: return TorahOperationReadError.snapshotChanged
        case .projectionBehind: return TorahOperationReadError.projectionBehind
        case .readLimit: return TorahOperationReadError.readLimit
        case .cancelled: return CancellationError()
        case .unknownError, .deadlineExceeded: return TorahOperationReadError.nativeFailure
        case .null, .UNRECOGNIZED: return TorahOperationReadError.malformedNativeResponse
        }
    }

    private static func exact(_ left: String, _ right: String) -> Bool {
        HeartNativeOperationCanonical.exact(left, right)
    }
}
