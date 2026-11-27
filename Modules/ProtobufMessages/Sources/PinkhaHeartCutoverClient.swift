#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation
import SwiftProtobuf
#if canImport(CryptoKit)
import CryptoKit
#else
import Crypto
#endif

public struct PinkhaHeartCutoverProfile: Sendable, Equatable {
    public let sourceManifestSHA256: String
    public let runtimeVersion: String

    /// Wave3 supplies the coherent native product identity, not an App version.
    /// A runtime that does not explicitly bind that source manifest is refused.
    public init(sourceManifestSHA256: String, runtimeVersion: String) throws {
        guard Self.hex(sourceManifestSHA256, bytes: 32),
              !runtimeVersion.isEmpty, runtimeVersion.utf8.count <= 1_024,
              !runtimeVersion.utf8.contains(0),
              Data(runtimeVersion.utf8).range(of: Data(sourceManifestSHA256.utf8)) != nil else {
            throw PinkhaHeartCutoverFailure(reason: .unsupportedRuntime)
        }
        self.sourceManifestSHA256 = sourceManifestSHA256
        self.runtimeVersion = runtimeVersion
    }

    static func hex(_ value: String, bytes: Int) -> Bool {
        value.utf8.count == bytes * 2 &&
            value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }

    // Exact original any-sync cidutil.NewCidFromBytes representation: CIDv1,
    // dag-cbor, SHA2-256 with a 32-byte digest, canonical lower-base32 without
    // padding. This checks identifier syntax, never a signature or live authority.
    static func nativeChangeID(_ value: String) -> Bool {
        let raw = Array(value.utf8)
        guard raw.count == 59, raw.first == 98 else { return false }
        var decoded: [UInt8] = []
        var accumulator: UInt32 = 0
        var bits = 0
        for byte in raw.dropFirst() {
            let digit: UInt32
            switch byte {
            case 97...122: digit = UInt32(byte - 97)
            case 50...55: digit = UInt32(byte - 50 + 26)
            default: return false
            }
            accumulator = (accumulator << 5) | digit
            bits += 5
            if bits >= 8 {
                bits -= 8
                decoded.append(UInt8((accumulator >> bits) & 255))
                accumulator &= (1 << bits) - 1
            }
        }
        return decoded.count == 36 && decoded.prefix(4).elementsEqual([1, 0x71, 0x12, 0x20]) &&
            bits == 2 && accumulator == 0
    }
}

/// Only a canonical native identifier and a claim bound to the exact frozen
/// content and author may cross a failed postflight fence. Disposition is retained
/// even for a collision; receipt presence is never a success or authority grant.
public struct PinkhaHeartCutoverDurableReceipt: Sendable, Equatable {
    public let disposition: Int
    public let claimID: String
    public let changeID: String

    fileprivate init?(disposition: Int, claimID: String, changeID: String) {
        let parts = claimID.split(separator: "/", omittingEmptySubsequences: false)
        guard (1...3).contains(disposition), parts.count == 2,
              PinkhaHeartCutoverProfile.hex(String(parts[0]), bytes: 32),
              PinkhaHeartCutoverProfile.hex(String(parts[1]), bytes: 32),
              disposition == 1 ? PinkhaHeartCutoverProfile.nativeChangeID(changeID) : changeID.isEmpty else { return nil }
        self.disposition = disposition; self.claimID = claimID; self.changeID = changeID
    }
}

public struct PinkhaHeartCutoverFailure: Error, Sendable, Equatable {
    public enum Reason: Sendable, Equatable {
        case retiredOwner
        case unsupportedRuntime
        case invalidRequest
        case invalidResponse
        case responseTooLarge
        case nativeRefusal
        case transportUncertain
        case callerCancelled
    }
    public enum WriteEffect: Sendable, Equatable {
        case notDispatched
        case uncertainAfterDispatch
        case nativeReceiptReceived
    }
    public let reason: Reason
    public let writeEffect: WriteEffect
    /// Exact dispatched wire digest. Callers retain their frozen request until
    /// reconciliation; private request bytes never cross a retired owner in errors.
    public let requestSHA256: String?
    public let nativeCode: Int?
    public let nativeIssues: [Int]
    public let durableReceipt: PinkhaHeartCutoverDurableReceipt?

    init(reason: Reason, nativeCode: Int? = nil, nativeIssues: [Int] = [],
         durableReceipt: PinkhaHeartCutoverDurableReceipt? = nil,
         writeEffect: WriteEffect = .notDispatched, requestSHA256: String? = nil) {
        self.reason = reason; self.nativeCode = nativeCode
        self.nativeIssues = nativeIssues; self.durableReceipt = durableReceipt
        self.writeEffect = writeEffect; self.requestSHA256 = requestSHA256
    }

    func afterDispatch(_ digest: String, reason replacement: Reason? = nil) -> Self {
        .init(reason: replacement ?? reason, nativeCode: nativeCode, nativeIssues: nativeIssues,
              durableReceipt: durableReceipt,
              writeEffect: durableReceipt == nil ? .uncertainAfterDispatch : .nativeReceiptReceived,
              requestSHA256: digest)
    }
}

enum PinkhaHeartCutoverMethod: String, Sendable {
    case sourceRead = "PinkhaTorahCutoverSourceRead"
    case read = "PinkhaTorahCutoverRead"
    case append = "PinkhaTorahCutoverAppend"
    case importFact = "PinkhaTorahCutoverImport"
    case associationAppend = "PinkhaTorahCutoverAssociationAppend"
}

@MainActor
struct PinkhaHeartCutoverIO {
    let runtimeVersion: @MainActor @Sendable () async throws -> String
    let invoke: @MainActor @Sendable (PinkhaHeartCutoverMethod, Data) async throws -> Data
}

/// Typed engine adapter. The existing lease is a Swift account-generation fence;
/// only the native handler grants current ACL, signer, source and target authority.
/// Reads never write, and no method automatically retries an ambiguous mutation.
@MainActor
public final class PinkhaHeartCutoverClient {
    private let io: PinkhaHeartCutoverIO
    public let profile: PinkhaHeartCutoverProfile
    private static let maximumReply = 4 * 1_024 * 1_024

    init(io: PinkhaHeartCutoverIO, profile: PinkhaHeartCutoverProfile) {
        self.io = io; self.profile = profile
    }

    public func source(_ scope: Anytype_PinkhaTorahCutover.Scope,
                       lease: PinkhaNativeReadLease) async throws -> Anytype_PinkhaTorahCutover.SourceSnapshot {
        let request = scope
        let data = try requestData(request, scope: request, lease: lease, maximum: 4_096)
        try await preflight(scope: request, lease: lease)
        let raw = try await io.invoke(.sourceRead, data)
        try validateOwner(request, lease)
        try Task.checkCancellation()
        let response = try decode(Anytype_PinkhaTorahCutover.SourceReadResponse.self, raw)
        try validateEnvelope(response.protocolVersion, hasError: response.hasError, error: response.error)
        guard response.hasSnapshot, response.snapshot.hasSource,
              bytesEqual(response.snapshot.source.key, request.propertyKey),
              response.snapshot.source.present || response.snapshot.source.value.isEmpty,
              response.snapshot.source.value.count <= 1_048_576,
              !response.snapshot.sourceHeads.isEmpty else {
            throw PinkhaHeartCutoverFailure(reason: .invalidResponse)
        }
        return response.snapshot
    }

    public func read(_ scope: Anytype_PinkhaTorahCutover.Scope,
                     lease: PinkhaNativeReadLease) async throws -> Anytype_PinkhaTorahCutover.Snapshot {
        let request = scope
        let data = try requestData(request, scope: request, lease: lease, maximum: 4_096)
        try await preflight(scope: request, lease: lease)
        let raw = try await io.invoke(.read, data)
        try validateOwner(request, lease)
        try Task.checkCancellation()
        let response = try decode(Anytype_PinkhaTorahCutover.ReadResponse.self, raw)
        try validateEnvelope(response.protocolVersion, hasError: response.hasError, error: response.error)
        guard response.hasSnapshot else { throw PinkhaHeartCutoverFailure(reason: .invalidResponse) }
        let snapshot = response.snapshot
        guard snapshot.completeLocal, snapshot.hasState, snapshot.hasSource,
              (1...5).contains(snapshot.state.status.rawValue),
              bytesEqual(snapshot.source.key, request.propertyKey),
              snapshot.source.present || snapshot.source.value.isEmpty,
              !snapshot.sourceHeads.isEmpty, !snapshot.metadataHeads.isEmpty, !snapshot.operationHeads.isEmpty else {
            throw PinkhaHeartCutoverFailure(reason: .invalidResponse)
        }
        if snapshot.state.hasPlan {
            guard bytesEqual(snapshot.state.plan.spaceID, request.spaceID),
                  bytesEqual(snapshot.state.plan.objectID, request.objectID),
                  bytesEqual(snapshot.state.plan.propertyKey, request.propertyKey) else {
                throw PinkhaHeartCutoverFailure(reason: .invalidResponse)
            }
        }
        return snapshot
    }

    /// Retain this immutable request until its native outcome is reconciled.
    /// Every failure after dispatch explicitly states possible effect; none retries.
    public func append(_ request: Anytype_PinkhaTorahCutover.RecordRequest,
                       lease: PinkhaNativeReadLease) async throws -> Anytype_PinkhaTorahCutover.AppendReceipt {
        let frozen = request
        guard frozen.hasScope, PinkhaHeartCutoverProfile.hex(frozen.recordID, bytes: 16) else {
            throw PinkhaHeartCutoverFailure(reason: .invalidRequest)
        }
        let data = try requestData(frozen, scope: frozen.scope, lease: lease, maximum: Self.maximumReply)
        try await preflight(scope: frozen.scope, lease: lease)
        try Task.checkCancellation()
        let expectedClaim = try Self.claimIdentity(frozen, author: lease.accountID)
        return try await write(.append, data: data, scope: frozen.scope, lease: lease) { raw in
            let response = try self.decode(Anytype_PinkhaTorahCutover.AppendResponse.self, raw)
            let identity = response.protocolVersion == 1 && response.hasError && response.hasReceipt ? self.bare(
                response.receipt.disposition.rawValue, response.receipt.claimID, response.receipt.changeID, expected: expectedClaim) : nil
            if response.protocolVersion == 1 && response.hasError && response.hasReceipt {
                guard let identity else { throw PinkhaHeartCutoverFailure(reason: .invalidResponse) }
                if response.receipt.hasResolution {
                    guard try self.matches(response.receipt, frozen: frozen, lease: lease, identity: identity) else {
                        throw PinkhaHeartCutoverFailure(reason: .invalidResponse)
                    }
                }
            }
            try self.writePostflight(scope: frozen.scope, lease: lease, version: response.protocolVersion,
                hasError: response.hasError, error: response.error, identity: identity)
            guard response.hasReceipt, let identity, response.receipt.hasResolution,
                  response.receipt.disposition.rawValue != 3 else {
                throw PinkhaHeartCutoverFailure(reason: .invalidResponse, durableReceipt: identity)
            }
            return WriteAccepted(receipt: response.receipt, identity: identity)
        }
    }

    public func importFact(_ request: Anytype_PinkhaTorahCutover.OperationRequest,
                           lease: PinkhaNativeReadLease) async throws -> Anytype_Rpc.Pinkha.TorahOperations.AppendReceipt {
        try await operation(request, lease: lease, method: .importFact)
    }

    public func associationAppend(_ request: Anytype_PinkhaTorahCutover.OperationRequest,
                                  lease: PinkhaNativeReadLease) async throws -> Anytype_Rpc.Pinkha.TorahOperations.AppendReceipt {
        try await operation(request, lease: lease, method: .associationAppend)
    }

    private func operation(_ request: Anytype_PinkhaTorahCutover.OperationRequest, lease: PinkhaNativeReadLease,
                           method: PinkhaHeartCutoverMethod) async throws -> Anytype_Rpc.Pinkha.TorahOperations.AppendReceipt {
        let frozen = request
        guard frozen.hasScope, PinkhaHeartCutoverProfile.hex(frozen.operationID, bytes: 16) else {
            throw PinkhaHeartCutoverFailure(reason: .invalidRequest)
        }
        let data = try requestData(frozen, scope: frozen.scope, lease: lease, maximum: Self.maximumReply)
        try await preflight(scope: frozen.scope, lease: lease)
        try Task.checkCancellation()
        let expectedClaim = try Self.claimIdentity(frozen, author: lease.accountID)
        return try await write(method, data: data, scope: frozen.scope, lease: lease) { raw in
            let response = try self.decode(Anytype_PinkhaTorahCutover.OperationResponse.self, raw)
            let identity = response.protocolVersion == 1 && response.hasError && response.hasReceipt ? self.bare(
                response.receipt.disposition.rawValue, response.receipt.claimID, response.receipt.changeID, expected: expectedClaim) : nil
            if response.protocolVersion == 1 && response.hasError && response.hasReceipt {
                guard let identity else { throw PinkhaHeartCutoverFailure(reason: .invalidResponse) }
                if response.receipt.hasResolution {
                    guard try self.matches(response.receipt, frozen: frozen, lease: lease, identity: identity) else {
                        throw PinkhaHeartCutoverFailure(reason: .invalidResponse)
                    }
                }
            }
            try self.writePostflight(scope: frozen.scope, lease: lease, version: response.protocolVersion,
                hasError: response.hasError, error: response.error, identity: identity)
            guard response.hasReceipt, let identity, response.receipt.hasResolution,
                  response.receipt.disposition.rawValue != 3 else {
                throw PinkhaHeartCutoverFailure(reason: .invalidResponse, durableReceipt: identity)
            }
            return WriteAccepted(receipt: response.receipt, identity: identity)
        }
    }

    private struct WriteAccepted<Receipt: Message & Sendable>: Sendable {
        let receipt: Receipt
        let identity: PinkhaHeartCutoverDurableReceipt
    }

    private func write<Receipt: Message & Sendable>(_ method: PinkhaHeartCutoverMethod, data: Data,
        scope: Anytype_PinkhaTorahCutover.Scope, lease: PinkhaNativeReadLease,
        decodeReply: @escaping @MainActor @Sendable (Data) throws -> WriteAccepted<Receipt>) async throws -> Receipt {
        let digest = Self.digest(data)
        try validateOwner(scope, lease)
        try Task.checkCancellation()
        // The synchronous, validated handoff into this owned task is the write's
        // cancellation boundary. Cancellation before handoff is refused above;
        // after handoff the write may run, and its acknowledgement is retained.
        // It never authorizes publishing private resolution to a cancelled caller.
        let owned = Task { @MainActor in
            try self.validateOwner(scope, lease)
            let raw: Data
            do { raw = try await self.io.invoke(method, data) }
            catch { throw PinkhaHeartCutoverFailure(reason: .transportUncertain).afterDispatch(digest) }
            do { return try decodeReply(raw) }
            catch let failure as PinkhaHeartCutoverFailure { throw failure.afterDispatch(digest) }
            catch { throw PinkhaHeartCutoverFailure(reason: .invalidResponse).afterDispatch(digest) }
        }
        let accepted: WriteAccepted<Receipt>
        do { accepted = try await owned.value }
        catch let failure as PinkhaHeartCutoverFailure {
            if Task.isCancelled && failure.writeEffect != .notDispatched {
                throw failure.afterDispatch(digest, reason: .callerCancelled)
            }
            throw failure
        }
        // Recheck on the ORIGINAL caller task, after the child completed. The
        // child does not inherit subsequent caller cancellation, and the owner
        // can retire while this caller is queued to resume on MainActor.
        do { try validateOwner(scope, lease) }
        catch {
            throw PinkhaHeartCutoverFailure(reason: .retiredOwner, nativeCode: 0,
                durableReceipt: accepted.identity).afterDispatch(digest)
        }
        guard !Task.isCancelled else {
            throw PinkhaHeartCutoverFailure(reason: .callerCancelled, nativeCode: 0,
                durableReceipt: accepted.identity).afterDispatch(digest)
        }
        return accepted.receipt
    }

    private func preflight(scope: Anytype_PinkhaTorahCutover.Scope, lease: PinkhaNativeReadLease) async throws {
        try Task.checkCancellation()
        try validateOwner(scope, lease)
        let observed = try await io.runtimeVersion()
        try validateOwner(scope, lease)
        guard bytesEqual(observed, profile.runtimeVersion) else {
            throw PinkhaHeartCutoverFailure(reason: .unsupportedRuntime)
        }
        try Task.checkCancellation()
    }

    private func requestData<M: Message>(_ request: M, scope: Anytype_PinkhaTorahCutover.Scope,
                                        lease: PinkhaNativeReadLease, maximum: Int) throws -> Data {
        try validateOwner(scope, lease)
        guard scope.protocolVersion == 1,
              [scope.spaceID, scope.objectID, scope.propertyKey].allSatisfy({
                  !$0.isEmpty && $0.utf8.count <= 1_024 && !$0.utf8.contains(0)
              }) else { throw PinkhaHeartCutoverFailure(reason: .invalidRequest) }
        let data = try request.serializedData()
        guard !data.isEmpty, data.count <= maximum else {
            throw PinkhaHeartCutoverFailure(reason: .invalidRequest)
        }
        return data
    }

    private func validateOwner(_ scope: Anytype_PinkhaTorahCutover.Scope, _ lease: PinkhaNativeReadLease) throws {
        do { try lease.validate() }
        catch { throw PinkhaHeartCutoverFailure(reason: .retiredOwner) }
        guard bytesEqual(scope.spaceID, lease.spaceID) else {
            throw PinkhaHeartCutoverFailure(reason: .retiredOwner)
        }
    }

    private func writePostflight(scope: Anytype_PinkhaTorahCutover.Scope, lease: PinkhaNativeReadLease,
                                version: UInt32, hasError: Bool, error nativeError: Anytype_PinkhaTorahCutover.Error,
                                identity: PinkhaHeartCutoverDurableReceipt?) throws {
        // Even an otherwise valid native success cannot publish private history
        // through a Swift owner that retired while the native call was in flight.
        do { try validateOwner(scope, lease) }
        catch {
            let validEnvelope = version == 1 && hasError
            throw PinkhaHeartCutoverFailure(reason: .retiredOwner,
                nativeCode: validEnvelope ? nativeError.code.rawValue : nil,
                nativeIssues: validEnvelope ? nativeError.issues.map(\.rawValue) : [],
                durableReceipt: identity)
        }
        try validateEnvelope(version, hasError: hasError, error: nativeError, identity: identity)
    }

    private func validateEnvelope(_ version: UInt32, hasError: Bool, error: Anytype_PinkhaTorahCutover.Error,
                                  identity: PinkhaHeartCutoverDurableReceipt? = nil) throws {
        guard version == 1, hasError else {
            throw PinkhaHeartCutoverFailure(reason: .invalidResponse, durableReceipt: identity)
        }
        guard error.code.rawValue == 0 else {
            throw PinkhaHeartCutoverFailure(reason: .nativeRefusal, nativeCode: error.code.rawValue,
                nativeIssues: error.issues.map(\.rawValue), durableReceipt: identity)
        }
        guard error.issues.isEmpty else {
            throw PinkhaHeartCutoverFailure(reason: .invalidResponse, durableReceipt: identity)
        }
    }

    private func decode<M: Message>(_ type: M.Type, _ data: Data) throws -> M {
        guard data.count <= Self.maximumReply else { throw PinkhaHeartCutoverFailure(reason: .responseTooLarge) }
        guard !data.isEmpty else { throw PinkhaHeartCutoverFailure(reason: .invalidResponse) }
        do { return try M(serializedBytes: data) }
        catch { throw PinkhaHeartCutoverFailure(reason: .invalidResponse) }
    }

    private func bare(_ disposition: Int, _ claimID: String, _ changeID: String,
                      expected: String) -> PinkhaHeartCutoverDurableReceipt? {
        guard bytesEqual(claimID, expected) else { return nil }
        return .init(disposition: disposition, claimID: claimID, changeID: changeID)
    }

    // Exact existing native claim-key framing, with the platform SHA-256 provider.
    // This is request correlation, never signature verification or native authority.
    static func claimKey(metadata: Bool, spaceID: String, id: String) -> String {
        let domain = metadata ? "pinkha-torah-cutover-key-v1" : "pinkha-t2-operation-key-v1"
        var frame = Data((domain + "\0").utf8)
        for text in [spaceID, id] {
            let raw = Data(text.utf8)
            var length = UInt32(raw.count).bigEndian
            withUnsafeBytes(of: &length) { frame.append(contentsOf: $0) }
            frame.append(raw)
        }
        return digest(frame)
    }

    static func digest(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    private func sameSet(_ left: [String], _ right: [String]) -> Bool {
        Set(left.map { Data($0.utf8) }) == Set(right.map { Data($0.utf8) })
    }

    private func sameMessages<M: Message>(_ left: [M], _ right: [M]) throws -> Bool {
        try Set(left.map { try $0.serializedData() }) == Set(right.map { try $0.serializedData() })
    }

    private func matches(_ receipt: Anytype_PinkhaTorahCutover.AppendReceipt,
        frozen: Anytype_PinkhaTorahCutover.RecordRequest, lease: PinkhaNativeReadLease,
        identity: PinkhaHeartCutoverDurableReceipt) throws -> Bool {
        let resolution = receipt.resolution
        guard bytesEqual(resolution.recordID, frozen.recordID), !resolution.conflict,
              resolution.claims.count == 1, let claim = resolution.claims.first,
              bytesEqual(claim.claimID, identity.claimID), bytesEqual(claim.digest, String(identity.claimID.suffix(64))),
              claim.hasRecord else { return false }
        let record = claim.record
        guard record.version == 1, bytesEqual(record.spaceID, frozen.scope.spaceID),
              bytesEqual(record.objectID, frozen.scope.objectID), bytesEqual(record.recordID, frozen.recordID),
              bytesEqual(record.authorID, lease.accountID), record.kind == frozen.kind,
              bytesEqual(record.planID, frozen.planID), record.hasPlan == frozen.hasPlan,
              bytesEqual(record.factID, frozen.factID), bytesEqual(record.importClaimID, frozen.importClaimID),
              sameSet(record.sourceHeads, frozen.sourceHeads), sameSet(record.importRecords, frozen.importRecords),
              try sameMessages(record.imported, frozen.imported),
              try sameMessages(record.nativeChanges, frozen.nativeChanges) else { return false }
        if record.hasPlan {
            let plan = record.plan, expected = frozen.plan
            guard plan.version == expected.version, bytesEqual(plan.spaceID, expected.spaceID),
                  bytesEqual(plan.objectID, expected.objectID), bytesEqual(plan.propertyKey, expected.propertyKey),
                  plan.valuePresent == expected.valuePresent, plan.legacyValue == expected.legacyValue,
                  try sameMessages(plan.facts, expected.facts) else { return false }
        }
        return true
    }

    private func matches(_ receipt: Anytype_Rpc.Pinkha.TorahOperations.AppendReceipt,
        frozen: Anytype_PinkhaTorahCutover.OperationRequest, lease: PinkhaNativeReadLease,
        identity: PinkhaHeartCutoverDurableReceipt) throws -> Bool {
        let resolution = receipt.resolution
        guard bytesEqual(resolution.operationID, frozen.operationID), !resolution.conflict,
              resolution.claims.count == 1, let claim = resolution.claims.first,
              bytesEqual(claim.claimID, identity.claimID), bytesEqual(claim.digest, String(identity.claimID.suffix(64))),
              claim.hasOperation else { return false }
        let operation = claim.operation
        return operation.version == 1 && bytesEqual(operation.spaceID, frozen.scope.spaceID) &&
            bytesEqual(operation.operationID, frozen.operationID) && bytesEqual(operation.authorID, lease.accountID) &&
            operation.kind == frozen.kind && bytesEqual(operation.target.objectID, frozen.scope.objectID) &&
            bytesEqual(operation.target.blockID, frozen.blockID) &&
            bytesEqual(operation.source.providerID, frozen.source.providerID) &&
            bytesEqual(operation.source.canonicalRef, frozen.source.canonicalRef) &&
            operation.payload == frozen.payload && sameSet(operation.observedClaimIds, frozen.observedClaimIds)
    }

    private func bytesEqual(_ left: String, _ right: String) -> Bool {
        left.utf8.elementsEqual(right.utf8)
    }
}
#endif
