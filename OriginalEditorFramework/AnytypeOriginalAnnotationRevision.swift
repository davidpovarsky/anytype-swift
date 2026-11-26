import Foundation
import CryptoKit
import Services
import PinkhaKit
import Factory
import SwiftProtobuf
@_spi(OriginalEditor) import ProtobufMessages

public enum AnytypeOriginalAnnotationRevisionError: Error, Sendable, Equatable {
    case invalidResponse, unobservedResponse, wrongCurrentToken, staleNativeRevision
}

/// A revision observed under the original native ObjectTree lock. Display
/// fields are historical data; only this closed current-session instance can
/// prepare one conditional replacement. It is not a distributed lock or ACK.
@MainActor
public final class AnytypeOriginalAnnotationRevisionToken {
    public let objectID: String
    public let nativeHeads: [String]
    public let nativeRootSHA256: String
    fileprivate let archiveObjectID: String
    fileprivate let archiveHeads: [String]
    fileprivate let isArchived: Bool
    fileprivate let binding: AnytypeOriginalEditorBinding
    fileprivate let sourceCapture: EditorDocumentWriteCapture
    private let session: AnytypeOriginalEditorAccountSession
    private let sourceLifetime: AnytypeOriginalEditorSourceLifetime
    private let sourceIsCurrent: @MainActor (AnytypeOriginalEditorBinding) -> Bool
    private var claimed = false

    fileprivate init(actual: OriginalAnnotationRevisionObservation,
                     session: AnytypeOriginalEditorAccountSession,
                     binding: AnytypeOriginalEditorBinding,
                     sourceLifetime: AnytypeOriginalEditorSourceLifetime,
                     sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorBinding) -> Bool) throws {
        guard let archiveID = actual.value.archiveObjectID,
              let archiveHeads = actual.value.archiveHeads,
              actual.value.isArchived == false else {
            throw AnytypeOriginalAnnotationRevisionError.invalidResponse
        }
        self.archiveObjectID = archiveID; self.archiveHeads = archiveHeads; isArchived = false
        sourceCapture = try EditorDocumentWriteCapture(sourceLifetime.lifetime)
        objectID = actual.value.rootID
        nativeHeads = actual.value.heads ?? []
        nativeRootSHA256 = actual.value.rootSnapshotSHA256 ?? ""
        self.session = session; self.binding = binding
        self.sourceLifetime = sourceLifetime; self.sourceIsCurrent = sourceIsCurrent
    }

    fileprivate func claim(session: AnytypeOriginalEditorAccountSession,
                           source: AnytypeOriginalAnnotationImportSource) throws {
        try session.validateCurrent()
        try sourceCapture.validate()
        guard self.session === session, !claimed, sourceLifetime.isCurrent,
              sourceIsCurrent(binding),
              source.annotationUUID == binding.annotationUUID,
              source.savedRevision == binding.expectedRevision,
              source.sourceDigest.utf8.elementsEqual(binding.sourceWitnessSHA256.utf8),
              source.accountID.utf8.elementsEqual(binding.accountID.utf8),
              source.spaceID.utf8.elementsEqual(binding.spaceID.utf8) else {
            throw AnytypeOriginalAnnotationRevisionError.wrongCurrentToken
        }
        claimed = true
    }
}

/// Verified local native replacement and genuine post-write original export.
/// Only the actual closed native call can produce this value. Neither decoding
/// its bytes nor receiving an applied status grants current source authority
/// or proves visibility on another device.
public struct AnytypeOriginalAnnotationRevisionReceipt: Sendable {
    public let source: AnytypeOriginalAnnotationImportSource
    public let objectID: String
    public let nativeHeads: [String]
    public let nativeRootSHA256: String
    public let nativeWriteObserved: Bool
    public let nativeArchiveSHA256: String
    public let nativeResponseSHA256: String
    public let nativeResponseBytes: Data
    public let objectMappings: [AnytypeOriginalAnnotationImportReceipt.ObjectMapping]

    fileprivate init(actual: OriginalAnnotationRevisionObservation,
                     source: AnytypeOriginalAnnotationImportSource, responseBytes: Data) throws {
        guard ["applied", "unchanged"].contains(actual.value.status),
              let heads = actual.value.heads, let hash = actual.value.rootSnapshotSHA256,
              let archiveHash = actual.value.nativeArchiveSHA256 else {
            throw AnytypeOriginalAnnotationRevisionError.invalidResponse
        }
        self.source = source
        objectID = actual.value.rootID; nativeHeads = heads; nativeRootSHA256 = hash
        nativeWriteObserved = actual.value.nativeWriteObserved
        nativeArchiveSHA256 = archiveHash
        nativeResponseSHA256 = OriginalAnnotationRevisionWire.sha256(responseBytes)
        nativeResponseBytes = responseBytes
        objectMappings = (actual.value.mappings ?? []).map {
            .init(sourceSpaceID: $0.sourceSpaceID, sourceObjectID: $0.sourceObjectID, objectID: $0.objectID)
        }
    }
}

/// Complete late history remains available even when the Swift waiter was
/// cancelled. Unknown native effects stay unknown; a refused/incomplete copy
/// never produces an accepted receipt or an implicit retry.
public struct AnytypeOriginalAnnotationRevisionHistory: Sendable {
    public let nativeResponseBytes: Data?
    public let nativeResponseCopyError: AnytypeOriginalAnnotationImportHistory.CopyError?
    public let cancellationResponseBytes: Data?
    public let cancellationResponseCopyError: AnytypeOriginalAnnotationImportHistory.CopyError?
    public let cancellationWasScheduled: Bool
    public let cancellationAwaitFailed: Bool
    public let nativeApplyAttempted: Bool?
    public let nativeWriteObserved: Bool?
    public let conflictObserved: Bool
    public let verifiedNativeReceipt: AnytypeOriginalAnnotationRevisionReceipt?

    @MainActor
    fileprivate init(actual: OriginalAnnotationImportCallHistory,
                     request: OriginalAnnotationRevisionRequest, requestBytes: Data,
                     source: AnytypeOriginalAnnotationImportSource,
                     desired: AnytypeOriginalEditorSnapshot) {
        let response = AnytypeOriginalAnnotationImportHistory.copy(
            actual.response, failure: actual.responseCopyError)
        nativeResponseBytes = response.0; nativeResponseCopyError = response.1
        let cancellation = AnytypeOriginalAnnotationImportHistory.copy(
            actual.cancellationResponse, failure: actual.cancellationCopyError)
        cancellationResponseBytes = cancellation.0
        cancellationResponseCopyError = cancellation.1
        cancellationWasScheduled = actual.cancellationWasScheduled
        cancellationAwaitFailed = actual.cancellationAwaitFailed
        let observed: OriginalAnnotationRevisionObservation?
        if let original = actual.response, response.0 != nil, response.1 == nil {
            observed = try? OriginalAnnotationRevisionObservation(response: original,
                request: request, requestBytes: requestBytes, accountID: source.accountID,
                spaceID: source.spaceID, desired: desired)
        } else { observed = nil }
        nativeApplyAttempted = observed?.value.nativeApplyAttempted
        nativeWriteObserved = observed?.value.nativeWriteObserved
        conflictObserved = observed?.value.status == "conflict"
            && observed?.value.nativeApplyAttempted == false
            && observed?.value.nativeWriteObserved == false
        if let observed, let bytes = response.0, !actual.cancellationWasScheduled,
           !actual.cancellationAwaitFailed, actual.cancellationResponse == nil,
           actual.cancellationCopyError == nil {
            verifiedNativeReceipt = try? AnytypeOriginalAnnotationRevisionReceipt(
                actual: observed, source: source, responseBytes: bytes)
        } else { verifiedNativeReceipt = nil }
    }
}

@MainActor
private final class OriginalAnnotationRevisionDelivery {
    private(set) var history: AnytypeOriginalAnnotationRevisionHistory?
    private let request: OriginalAnnotationRevisionRequest
    private let requestBytes: Data
    private let source: AnytypeOriginalAnnotationImportSource
    private let desired: AnytypeOriginalEditorSnapshot
    private var deliver: (@MainActor @Sendable (AnytypeOriginalAnnotationRevisionHistory) -> Void)?
    init(request: OriginalAnnotationRevisionRequest, requestBytes: Data,
         source: AnytypeOriginalAnnotationImportSource, desired: AnytypeOriginalEditorSnapshot,
         deliver: @escaping @MainActor @Sendable (AnytypeOriginalAnnotationRevisionHistory) -> Void) {
        self.request = request; self.requestBytes = requestBytes
        self.source = source; self.desired = desired; self.deliver = deliver
    }
    func receive(_ actual: OriginalAnnotationImportCallHistory) {
        guard history == nil else { return }
        let observed = AnytypeOriginalAnnotationRevisionHistory(actual: actual,
            request: request, requestBytes: requestBytes, source: source, desired: desired)
        history = observed
        let callback = deliver; deliver = nil; callback?(observed)
    }
}

/// Preparation performs no native operation. The Host must durably record the
/// exact target/token/source and its possible-dispatch transition BEFORE invoke.
/// Replacing an existing remote root is never the fresh-import retry route.
@MainActor
public final class AnytypeOriginalAnnotationRevisionAttempt {
    public let source: AnytypeOriginalAnnotationImportSource
    public let objectID: String
    public let expectedNativeHeads: [String]
    public let expectedNativeRootSHA256: String
    public let requestSHA256: String
    /// Exact bounded JSON envelope; excludes the private native attempt secret.
    public let requestBytes: Data
    private let sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime
    private let original: OriginalAnnotationImportAttempt
    private let delivery: OriginalAnnotationRevisionDelivery

    fileprivate init(sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime,
                     token: AnytypeOriginalAnnotationRevisionToken, requestBytes: Data,
                     original: OriginalAnnotationImportAttempt,
                     delivery: OriginalAnnotationRevisionDelivery) {
        source = sourceLifetime.source
        objectID = token.objectID; expectedNativeHeads = token.nativeHeads
        expectedNativeRootSHA256 = token.nativeRootSHA256
        requestSHA256 = OriginalAnnotationRevisionWire.sha256(requestBytes)
        self.requestBytes = requestBytes
        self.sourceLifetime = sourceLifetime; self.original = original; self.delivery = delivery
    }

    public var drainedHistory: AnytypeOriginalAnnotationRevisionHistory? { delivery.history }
    public func invoke() async throws { _ = try await original.invoke() }

    @discardableResult
    public func requestCancellation() -> AnytypeOriginalAnnotationImportAttempt.CancellationScheduling {
        switch original.requestCancellation() {
        case .beforeInvocation: return .beforeInvocation
        case .scheduled: return .scheduled
        case .alreadyScheduled: return .alreadyScheduled
        case .importDrained: return .importDrained
        }
    }
    public func retire() { sourceLifetime.retire() }
    deinit { sourceLifetime.retire() }
}

extension AnytypeOriginalEditorAccountSession {
    /// Reads the actual original object and obtains its nonempty causal heads
    /// under the original lock. This mounts no remote editor and writes no body.
    public func readOriginalAnnotation(
        binding: AnytypeOriginalEditorBinding,
        sourceLifetime: AnytypeOriginalEditorSourceLifetime,
        maximumBodyBytes: Int,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorBinding) -> Bool
    ) async throws -> AnytypeOriginalAnnotationReadReceipt {
        try validateCurrent()
        guard identity.accountID.utf8.elementsEqual(binding.accountID.utf8),
              identity.spaceID.utf8.elementsEqual(binding.spaceID.utf8) else {
            throw AnytypeOriginalAnnotationImportError.wrongSelectedSpace
        }
        try sourceLifetime.claim(for: binding)
        do {
            try Task.checkCancellation()
            let frozen = try originalAnnotationImportSourceBinding(
                lifetime: sourceLifetime.lifetime,
                sourceIsCurrent: { sourceLifetime.isCurrent && sourceIsCurrent(binding) })
            let request = OriginalAnnotationRevisionRequest(read: binding)
            let bytes = try OriginalAnnotationRevisionWire.encode(request)
            let drained = OriginalAnnotationRevisionReadDrain()
            let original = try frozen.prepareOriginalAnnotationRevision(
                selection: currentOriginalSelection(), sourceSpaceID: binding.spaceID,
                sourceRootID: binding.objectID, envelope: bytes,
                onDrained: { drained.receive($0) })
            do { _ = try await original.invoke() }
            catch { await drained.wait(); throw error }
            await drained.wait()
            try Task.checkCancellation(); try validateCurrent(); try frozen.validate()
            guard drained.count == 1, let history = drained.history,
                  history.responseCopyError == nil, let response = history.response,
                  !history.cancellationWasScheduled, !history.cancellationAwaitFailed,
                  history.cancellationResponse == nil, history.cancellationCopyError == nil else {
                throw AnytypeOriginalAnnotationRevisionError.unobservedResponse
            }
            let observed = try OriginalAnnotationRevisionObservation(response: response,
                request: request, requestBytes: bytes, accountID: binding.accountID,
                spaceID: binding.spaceID, desired: nil)
            guard observed.value.status == "read" else {
                throw AnytypeOriginalAnnotationRevisionError.staleNativeRevision
            }
            let copied = try response.serializedData()
            guard copied.count <= OriginalAnnotationRevisionWire.maximumEnvelopeBytes else {
                throw AnytypeOriginalAnnotationRevisionError.invalidResponse
            }
            let capture = try observed.makeCapture(binding: binding, maximumBodyBytes: maximumBodyBytes,
                responseBytes: copied)
            let token = try AnytypeOriginalAnnotationRevisionToken(actual: observed, session: self,
                binding: binding, sourceLifetime: sourceLifetime, sourceIsCurrent: sourceIsCurrent)
            return try AnytypeOriginalAnnotationReadReceipt(actual: capture, binding: binding,
                maximumBodyBytes: maximumBodyBytes, revisionToken: token, nativeResponseBytes: copied)
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }

    /// Uses only a current token minted by this SAME original account session.
    /// The native engine compares that token immediately before original Apply
    /// under its own ObjectTree lock. Cross-peer visibility is a separate proof.
    public func prepareAnnotationReplacement(
        snapshot: AnytypeOriginalEditorSnapshot,
        revisionToken: AnytypeOriginalAnnotationRevisionToken,
        sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalAnnotationImportSource) -> Bool,
        onDrained: @escaping @MainActor @Sendable (AnytypeOriginalAnnotationRevisionHistory) -> Void
    ) throws -> AnytypeOriginalAnnotationRevisionAttempt {
        try sourceLifetime.claim()
        do {
            try Task.checkCancellation()
            let source = sourceLifetime.source
            let selection = try currentOriginalSelection()
            guard source.namespace == "otzaria.local.annotation",
                  selection.accountID.utf8.elementsEqual(source.accountID.utf8),
                  selection.accountInfo.accountSpaceId.utf8.elementsEqual(source.spaceID.utf8),
                  snapshot.provenance.annotationUUID == source.annotationUUID,
                  snapshot.provenance.hostProfileID.utf8.elementsEqual(revisionToken.binding.hostProfileID.utf8),
                  snapshot.provenance.capturedAgainstRevision < Int64.max,
                  snapshot.provenance.capturedAgainstRevision + 1 == source.savedRevision,
                  OriginalAnnotationRevisionWire.sha256(snapshot.bodyBytes).utf8.elementsEqual(source.bodyDigest.utf8) else {
                throw AnytypeOriginalAnnotationImportError.savedBodyMismatch
            }
            try revisionToken.claim(session: self, source: source)
            let frozen = try originalAnnotationImportSourceBinding(
                lifetime: sourceLifetime.lifetime,
                sourceIsCurrent: { sourceLifetime.isCurrent && sourceIsCurrent(source) })
                .requiringCapturedSource(revisionToken.sourceCapture)
            let request = OriginalAnnotationRevisionRequest(replacing: revisionToken, snapshot: snapshot)
            let bytes = try OriginalAnnotationRevisionWire.encode(request)
            let delivery = OriginalAnnotationRevisionDelivery(request: request, requestBytes: bytes,
                source: source, desired: snapshot, deliver: onDrained)
            let original = try frozen.prepareOriginalAnnotationRevision(selection: selection,
                sourceSpaceID: snapshot.provenance.spaceID, sourceRootID: snapshot.provenance.objectID,
                envelope: bytes, onDrained: { delivery.receive($0) })
            try validateCurrent(); try frozen.validate()
            return AnytypeOriginalAnnotationRevisionAttempt(sourceLifetime: sourceLifetime,
                token: revisionToken, requestBytes: bytes, original: original, delivery: delivery)
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }
}

@MainActor
private final class OriginalAnnotationRevisionReadDrain {
    private(set) var history: OriginalAnnotationImportCallHistory?
    private(set) var count = 0
    private var waiter: CheckedContinuation<Void, Never>?
    func receive(_ value: OriginalAnnotationImportCallHistory) {
        count += 1
        if history == nil { history = value }
        let continuation = waiter; waiter = nil; continuation?.resume()
    }
    func wait() async {
        if count > 0 { return }
        await withCheckedContinuation { waiter = $0 }
    }
}

fileprivate struct OriginalAnnotationRevisionRequest: Encodable {
    let schema = 1
    let operation: String
    let targetRootID: String
    let annotationUUID: UUID
    let expectedHeads: [String]?
    let expectedRootSHA256: String?
    let expectedArchiveID: String?
    let expectedArchiveHeads: [String]?
    let expectedIsArchived: Bool?
    let desiredArchive: Data?
    let desiredArchiveSHA256: String?
    enum CodingKeys: String, CodingKey {
        case schema, operation
        case targetRootID = "target_root_id", annotationUUID = "annotation_uuid"
        case expectedHeads = "expected_heads", expectedRootSHA256 = "expected_root_sha256"
        case expectedArchiveID = "expected_archive_id", expectedArchiveHeads = "expected_archive_heads"
        case expectedIsArchived = "expected_is_archived"
        case desiredArchive = "desired_archive", desiredArchiveSHA256 = "desired_archive_sha256"
    }
    init(read binding: AnytypeOriginalEditorBinding) {
        operation = "read"; targetRootID = binding.objectID; annotationUUID = binding.annotationUUID
        expectedHeads = nil; expectedRootSHA256 = nil
        expectedArchiveID = nil; expectedArchiveHeads = nil; expectedIsArchived = nil
        desiredArchive = nil; desiredArchiveSHA256 = nil
    }
    @MainActor init(replacing token: AnytypeOriginalAnnotationRevisionToken,
                    snapshot: AnytypeOriginalEditorSnapshot) {
        operation = "replace"; targetRootID = token.objectID
        annotationUUID = token.binding.annotationUUID
        expectedHeads = token.nativeHeads; expectedRootSHA256 = token.nativeRootSHA256
        expectedArchiveID = token.archiveObjectID; expectedArchiveHeads = token.archiveHeads
        expectedIsArchived = token.isArchived
        desiredArchive = snapshot.nativeArchiveBytes; desiredArchiveSHA256 = snapshot.nativeArchiveSHA256
    }
}

internal struct OriginalAnnotationRevisionResult: Decodable, Sendable {
    struct Mapping: Decodable, Sendable {
        let sourceSpaceID: String, sourceObjectID: String, objectID: String
        enum CodingKeys: String, CodingKey {
            case sourceSpaceID = "source_space_id", sourceObjectID = "source_object_id", objectID = "object_id"
        }
    }
    let schema: Int
    let operation: String, status: String, accountID: String, spaceID: String, rootID: String
    let annotationUUID: UUID
    let beforeHeads: [String]?
    let heads: [String]?
    let rootSnapshotSHA256: String?
    let archiveObjectID: String?
    let archiveHeads: [String]?
    let isArchived: Bool?
    let nativeArchive: Data?
    let nativeArchiveSHA256: String?
    let sourceArchiveSHA256: String?
    let mappings: [Mapping]?
    let nativeWriteObserved: Bool
    let nativeApplyAttempted: Bool
    enum CodingKeys: String, CodingKey {
        case schema, operation, status, heads, mappings
        case accountID = "account_id", spaceID = "space_id", rootID = "root_id", annotationUUID = "annotation_uuid"
        case beforeHeads = "before_heads", rootSnapshotSHA256 = "root_snapshot_sha256"
        case archiveObjectID = "archive_object_id", archiveHeads = "archive_heads", isArchived = "is_archived"
        case nativeArchive = "native_archive", nativeArchiveSHA256 = "native_archive_sha256"
        case sourceArchiveSHA256 = "source_archive_sha256", nativeWriteObserved = "native_write_observed"
        case nativeApplyAttempted = "native_apply_attempted"
    }
}

internal enum OriginalAnnotationRevisionWire {
    static let maximumEnvelopeBytes = 2 * 1_024 * 1_024
    static let maximumArchiveBytes = 1_024 * 1_024
    static let protocolName = "pinkha.annotation.revision.v1"
    static func sha256(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
    static func digest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    static func identifier(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 16_384 && !value.utf8.contains(0)
    }
    static func heads(_ value: [String]) -> Bool {
        !value.isEmpty && value.count <= 64
            && value.allSatisfy { identifier($0) && $0.utf8.count <= 512 }
            && zip(value, value.dropFirst()).allSatisfy { $0.0.utf8.lexicographicallyPrecedes($0.1.utf8) }
    }
    fileprivate static func encode(_ value: OriginalAnnotationRevisionRequest) throws -> Data {
        guard identifier(value.targetRootID) else { throw AnytypeOriginalAnnotationRevisionError.invalidResponse }
        if value.operation == "replace" {
            guard let heads = value.expectedHeads, self.heads(heads),
                  let hash = value.expectedRootSHA256, digest(hash),
                  let archiveID = value.expectedArchiveID, identifier(archiveID),
                  !archiveID.utf8.elementsEqual(value.targetRootID.utf8),
                  let archiveHeads = value.expectedArchiveHeads, self.heads(archiveHeads),
                  value.expectedIsArchived == false,
                  let archive = value.desiredArchive, !archive.isEmpty, archive.count <= maximumArchiveBytes,
                  value.desiredArchiveSHA256 == sha256(archive) else {
                throw AnytypeOriginalAnnotationRevisionError.invalidResponse
            }
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let bytes = try encoder.encode(value)
        guard bytes.count <= maximumEnvelopeBytes else { throw AnytypeOriginalAnnotationRevisionError.invalidResponse }
        return bytes
    }
}

fileprivate struct OriginalAnnotationRevisionObservation {
    let value: OriginalAnnotationRevisionResult
    let report: Anytype_Model_ExportReport?
    let nativeArchive: OriginalAnnotationNativeArchiveComparison?

    init(response: Anytype_Rpc.Annotation.Import.Response,
         request: OriginalAnnotationRevisionRequest, requestBytes: Data,
         accountID: String, spaceID: String, desired: AnytypeOriginalEditorSnapshot?) throws {
        guard response.importProtocol == OriginalAnnotationRevisionWire.protocolName,
              response.registered, response.operationDone, response.copyDisposition == .complete,
              response.hasReadback, response.readback.stage == 4,
              response.readback.accountID.utf8.elementsEqual(accountID.utf8),
              response.readback.spaceID.utf8.elementsEqual(spaceID.utf8),
              response.readback.rootID.utf8.elementsEqual(request.targetRootID.utf8),
              response.readback.sourceArchiveSha256 == Data(SHA256.hash(data: requestBytes)),
              !response.readback.nativeArchive.isEmpty,
              response.readback.nativeArchive.count <= OriginalAnnotationRevisionWire.maximumEnvelopeBytes,
              response.readback.nativeArchiveSha256 == Data(SHA256.hash(data: response.readback.nativeArchive)) else {
            throw AnytypeOriginalAnnotationRevisionError.invalidResponse
        }
        let value = try JSONDecoder().decode(OriginalAnnotationRevisionResult.self, from: response.readback.nativeArchive)
        guard value.schema == 1, value.operation == request.operation,
              value.accountID.utf8.elementsEqual(accountID.utf8),
              value.spaceID.utf8.elementsEqual(spaceID.utf8),
              value.rootID.utf8.elementsEqual(request.targetRootID.utf8),
              value.annotationUUID == request.annotationUUID,
              ["read", "applied", "unchanged", "conflict", "applied_unconfirmed", "refused"].contains(value.status),
              (value.sourceArchiveSHA256 ?? "") == (request.desiredArchiveSHA256 ?? "") else {
            throw AnytypeOriginalAnnotationRevisionError.invalidResponse
        }
        self.value = value
        let accepted = ["read", "applied", "unchanged"].contains(value.status)
        if !accepted {
            if value.status == "conflict" {
                guard response.readback.observed,
                      !value.nativeApplyAttempted, !value.nativeWriteObserved,
                      let heads = value.heads, OriginalAnnotationRevisionWire.heads(heads),
                      value.beforeHeads == heads, let hash = value.rootSnapshotSHA256,
                      OriginalAnnotationRevisionWire.digest(hash),
                      let archiveID = value.archiveObjectID, OriginalAnnotationRevisionWire.identifier(archiveID),
                      let archiveHeads = value.archiveHeads, OriginalAnnotationRevisionWire.heads(archiveHeads),
                      value.isArchived != nil else {
                    throw AnytypeOriginalAnnotationRevisionError.invalidResponse
                }
            }
            report = nil; nativeArchive = nil
            return
        }
        guard response.error.code == .null, !response.nativeErrorPresent, response.nativeErrorCategory == .none,
              !response.cancellationRequested, response.readback.observed,
              response.readback.hasExportReport, response.readback.exportReport.status == .success,
              response.readback.exportReport.succeed > 0, response.readback.exportReport.objectErrors == 0,
              response.readback.exportReport.fileErrors == 0, response.readback.exportReport.issues.isEmpty,
              let heads = value.heads, OriginalAnnotationRevisionWire.heads(heads),
              let before = value.beforeHeads, OriginalAnnotationRevisionWire.heads(before),
              let hash = value.rootSnapshotSHA256, OriginalAnnotationRevisionWire.digest(hash),
              let bytes = value.nativeArchive, !bytes.isEmpty, bytes.count <= OriginalAnnotationRevisionWire.maximumArchiveBytes,
              value.nativeArchiveSHA256 == OriginalAnnotationRevisionWire.sha256(bytes),
              let archiveID = value.archiveObjectID, OriginalAnnotationRevisionWire.identifier(archiveID),
              !archiveID.utf8.elementsEqual(value.rootID.utf8),
              let archiveHeads = value.archiveHeads, OriginalAnnotationRevisionWire.heads(archiveHeads),
              value.isArchived == false else {
            throw AnytypeOriginalAnnotationRevisionError.invalidResponse
        }
        if request.operation == "read" {
            guard value.status == "read", !value.nativeApplyAttempted, !value.nativeWriteObserved,
                  before == heads else { throw AnytypeOriginalAnnotationRevisionError.invalidResponse }
        } else {
            guard request.operation == "replace", before == request.expectedHeads,
                  archiveID == request.expectedArchiveID, archiveHeads == request.expectedArchiveHeads,
                  request.expectedIsArchived == false else {
                throw AnytypeOriginalAnnotationRevisionError.invalidResponse
            }
            if value.status == "applied" {
                guard value.nativeApplyAttempted, value.nativeWriteObserved, heads != before else {
                    throw AnytypeOriginalAnnotationRevisionError.invalidResponse
                }
            } else {
                guard value.status == "unchanged", !value.nativeApplyAttempted, !value.nativeWriteObserved,
                      heads == before, hash == request.expectedRootSHA256 else {
                    throw AnytypeOriginalAnnotationRevisionError.invalidResponse
                }
            }
        }
        let report = response.readback.exportReport
        let actual = try OriginalAnnotationNativeArchiveComparison(archiveBytes: bytes, rootID: value.rootID,
            spaceID: spaceID, formatVersion: AnytypeOriginalEditorSnapshot.formatVersion,
            reportedObjectCount: report.succeed)
        guard let mappings = value.mappings, !mappings.isEmpty, mappings.count <= 8_192,
              mappings.allSatisfy({ OriginalAnnotationRevisionWire.identifier($0.sourceSpaceID)
                && OriginalAnnotationRevisionWire.identifier($0.sourceObjectID)
                && OriginalAnnotationRevisionWire.identifier($0.objectID) }),
              Set(mappings.map { Data($0.sourceObjectID.utf8) }).count == mappings.count,
              Set(mappings.map { Data($0.objectID.utf8) }).count == mappings.count else {
            throw AnytypeOriginalAnnotationRevisionError.invalidResponse
        }
        if let desired {
            let source = try OriginalEditorLocalAnnotationNativeBody.decoded(desired)
            let savedSource = try AnytypeOriginalEditorLocalAnnotationSource(
                hostProfileID: desired.provenance.hostProfileID,
                annotationUUID: desired.provenance.annotationUUID,
                expectedRevision: desired.provenance.capturedAgainstRevision,
                sourceWitnessSHA256: desired.provenance.sourceWitnessSHA256, payloadSHA256: nil)
            try OriginalEditorLocalAnnotationNativeBody.requireMarkers(actual.rootSnapshot.details,
                source: savedSource, transportOriginHostProfileID: desired.provenance.transportOriginHostProfileID)
            guard mappings.allSatisfy({ $0.sourceSpaceID.utf8.elementsEqual(desired.provenance.spaceID.utf8) }),
                  Set(mappings.map { Data($0.sourceObjectID.utf8) }) == Set(source.objectIDs.map { Data($0.utf8) }),
                  Set(mappings.map { Data($0.objectID.utf8) }).isSubset(of: Set(actual.objectIDs.map { Data($0.utf8) })),
                  mappings.filter({ $0.sourceObjectID == desired.provenance.objectID && $0.objectID == value.rootID }).count == 1 else {
                throw AnytypeOriginalAnnotationRevisionError.invalidResponse
            }
        } else {
            guard mappings.allSatisfy({ $0.sourceSpaceID.utf8.elementsEqual(spaceID.utf8)
                    && $0.sourceObjectID.utf8.elementsEqual($0.objectID.utf8) }),
                  Set(mappings.map { Data($0.objectID.utf8) }) == Set(actual.objectIDs.map { Data($0.utf8) }) else {
                throw AnytypeOriginalAnnotationRevisionError.invalidResponse
            }
        }
        self.report = report; nativeArchive = actual
    }

    func makeCapture(binding: AnytypeOriginalEditorBinding, maximumBodyBytes: Int,
                     responseBytes: Data) throws -> AnytypeOriginalEditorSnapshotCapture {
        guard value.status == "read", let report, let bytes = value.nativeArchive,
              nativeArchive != nil else { throw AnytypeOriginalAnnotationRevisionError.invalidResponse }
        let directory = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        let archiveURL = directory.appendingPathComponent("original-native.zip")
        let reportBytes = try report.serializedData()
        try bytes.write(to: archiveURL, options: .withoutOverwriting)
        try reportBytes.write(to: directory.appendingPathComponent("native-export-report.pb"), options: .withoutOverwriting)
        try responseBytes.write(to: directory.appendingPathComponent("native-revision-response.pb"), options: .withoutOverwriting)
        let snapshot = try AnytypeOriginalEditorSnapshot.frame(archive: bytes, reportBytes: reportBytes,
            responseCount: report.succeed, binding: binding, maximumBodyBytes: maximumBodyBytes)
        return .init(snapshot: snapshot, retainedArchiveURL: archiveURL, retainedDirectoryURL: directory)
    }
}


// MARK: - Original selected-account copy discovery

/// A fresh original search observation for one canonical annotation UUID.
/// This value grants no write authority and cannot be decoded into a read,
/// replacement token or remote acknowledgement. The chosen root must still
/// pass the existing original native revision/read boundary.
public struct AnytypeOriginalAnnotationDiscoveredCopy: Sendable, Equatable {
    public let accountID: String
    public let spaceID: String
    public let objectID: String
    public let annotationUUID: UUID

    fileprivate init(candidate: TorahAnnotationNativeCandidate) {
        accountID = candidate.identity.scope.account
        spaceID = candidate.identity.scope.space
        objectID = candidate.identity.objectID
        annotationUUID = candidate.identity.scope.annotationUUID
    }
}

private enum OriginalAnnotationDiscoveryError: Error {
    case unexpectedScope, tooManyCopies, duplicateObject
}

extension AnytypeOriginalEditorAccountSession {
    /// Finds the existing shared roots after a canonical note arrives on a
    /// second Host through its original annotation import or sync path. It
    /// reuses the exact Host row lifetime and selected original account. No
    /// object is created, adopted by display name, or marked as delivered.
    public func discoverOriginalAnnotationCopies(
        sourceLifetime: AnytypeOriginalEditorLocalAnnotationSourceLifetime,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorLocalAnnotationSource) -> Bool
    ) async throws -> [AnytypeOriginalAnnotationDiscoveredCopy] {
        try sourceLifetime.claim()
        defer { sourceLifetime.retire() }
        try validateCurrent()
        let source = sourceLifetime.source
        let frozen = try originalAnnotationImportSourceBinding(
            lifetime: sourceLifetime.lifetime,
            sourceIsCurrent: { sourceLifetime.isCurrent && sourceIsCurrent(source) })
        let original = try OriginalSearchMiddleServiceBinding.requireOriginal(
            Container.shared.searchMiddleService())
        let accountID = identity.accountID
        let spaceID = identity.spaceID
        let keys = OriginalAnnotationMetadataField.allCases.map(\.rawValue)
            + ["id", "spaceId", "type", "isArchived", "isDeleted"]
        let filters: [DataviewFilter] = [
            .with {
                $0.relationKey = OriginalAnnotationMetadataField.annotationUUID.rawValue
                $0.condition = .equal
                $0.value = source.annotationUUID.uuidString.protobufValue
            },
            .with {
                $0.relationKey = OriginalAnnotationMetadataField.schemaProtocol.rawValue
                $0.condition = .equal
                $0.value = OriginalAnnotationNativeMetadata.protocolValue.protobufValue
            },
            .with {
                $0.relationKey = OriginalAnnotationMetadataField.namespace.rawValue
                $0.condition = .equal
                $0.value = "otzaria.local.annotation".protobufValue
            }
        ]
        let records = try await frozen.performRead(rpcNames: ["ObjectSearch"]) {
            try await original.search(spaceId: spaceID, filters: filters, keys: keys, limit: 65)
        }
        try Task.checkCancellation()
        try frozen.validate()
        try validateCurrent()
        guard records.count <= 64 else { throw OriginalAnnotationDiscoveryError.tooManyCopies }
        var seen = Set<String>()
        var result: [AnytypeOriginalAnnotationDiscoveredCopy] = []
        for record in records {
            let candidate = try OriginalAnnotationNativeMetadata.decode(
                .with { $0.fields = record.values }, rootID: record.id)
            let scope = candidate.identity.scope
            guard scope.account.utf8.elementsEqual(accountID.utf8),
                  scope.space.utf8.elementsEqual(spaceID.utf8),
                  scope.namespace == "otzaria.local.annotation",
                  scope.annotationUUID == source.annotationUUID else {
                throw OriginalAnnotationDiscoveryError.unexpectedScope
            }
            guard seen.insert(candidate.identity.objectID).inserted else {
                throw OriginalAnnotationDiscoveryError.duplicateObject
            }
            // Archived/promoted roots keep their separate explicit lifecycle.
            // Receive must never silently unarchive or reclassify a document.
            guard candidate.objectState == .present, candidate.classification == .annotation else { continue }
            result.append(.init(candidate: candidate))
        }
        return result.sorted { $0.objectID.utf8.lexicographicallyPrecedes($1.objectID.utf8) }
    }
}
