import Foundation
import CryptoKit
import PinkhaKit
import SwiftProtobuf
import ZIPFoundation
@_spi(OriginalEditor) import ProtobufMessages

public enum AnytypeOriginalAnnotationDocumentRole: String, Sendable, CaseIterable {
    case chiddush, article, research
}

public enum AnytypeOriginalAnnotationLifecycleAction: Sendable, Equatable {
    case archive
    case restore
    case promote(AnytypeOriginalAnnotationDocumentRole)
    case revertPromotion
    case replacePromotedDocument
}

public enum AnytypeOriginalAnnotationLifecycleError: Error, Sendable, Equatable {
    case invalidResponse, unobservedResponse, wrongCurrentObservation, unsupportedAction
}

/// A genuine original locked read. The root and Archive tokens are separate.
/// A promotion read additionally freezes the actual native manifest/type trees.
/// This value cannot be constructed/decoded by the Host and is not a network ACK.
public struct AnytypeOriginalAnnotationLifecycleObservation: Sendable {
    public let nativeCapture: AnytypeOriginalEditorSnapshotCapture
    public let textPreview: String
    public let fullPlainText: String
    public let objectID: String
    public let nativeHeads: [String]
    public let nativeRootSHA256: String
    public let archiveObjectID: String
    public let archiveHeads: [String]
    public let isArchived: Bool
    public let documentRole: AnytypeOriginalAnnotationDocumentRole?
    public let promotionRole: AnytypeOriginalAnnotationDocumentRole?
    public let nativeResponseBytes: Data
    public let nativeResponseSHA256: String
    fileprivate let actual: OriginalAnnotationLifecycleObservation
    fileprivate let ownership: OriginalAnnotationLifecycleOwnership

    @MainActor
    fileprivate init(actual: OriginalAnnotationLifecycleObservation,
                     capture: AnytypeOriginalEditorSnapshotCapture, responseBytes: Data,
                     session: AnytypeOriginalEditorAccountSession,
                     binding: AnytypeOriginalEditorBinding,
                     sourceLifetime: AnytypeOriginalEditorSourceLifetime,
                     sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorBinding) -> Bool) throws {
        let value = actual.value, core = value.core
        guard ["read_lifecycle", "read_promoted"].contains(core.status),
              let heads = core.heads, let hash = core.rootSnapshotSHA256,
              let archiveID = value.archiveObjectID, let archiveHeads = value.archiveHeads,
              let archived = value.isArchived else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        guard let native = actual.nativeArchive else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        let text = try OriginalEditorLocalAnnotationNativeBody.textProjection(
            root: native.rootSnapshot, rootID: core.rootID)
        nativeCapture = capture; textPreview = text.textPreview; fullPlainText = text.fullPlainText
        objectID = core.rootID
        nativeHeads = heads; nativeRootSHA256 = hash
        archiveObjectID = archiveID; self.archiveHeads = archiveHeads; isArchived = archived
        documentRole = value.documentRole.flatMap(AnytypeOriginalAnnotationDocumentRole.init(rawValue:))
        promotionRole = value.promotionRole.flatMap(AnytypeOriginalAnnotationDocumentRole.init(rawValue:))
        nativeResponseBytes = responseBytes
        nativeResponseSHA256 = OriginalAnnotationRevisionWire.sha256(responseBytes)
        self.actual = actual
        ownership = try OriginalAnnotationLifecycleOwnership(session: session, binding: binding,
            sourceLifetime: sourceLifetime, sourceIsCurrent: sourceIsCurrent)
    }
}

/// Actual original native lifecycle completion and full readback. Soft archive
/// is Archive collection membership; it is not a permanent-delete receipt.
public struct AnytypeOriginalAnnotationLifecycleReceipt: Sendable {
    public let source: AnytypeOriginalAnnotationImportSource
    public let action: AnytypeOriginalAnnotationLifecycleAction
    public let objectID: String
    public let nativeHeads: [String]
    public let nativeRootSHA256: String
    public let archiveObjectID: String
    public let archiveHeads: [String]
    public let isArchived: Bool
    public let documentRole: AnytypeOriginalAnnotationDocumentRole?
    public let wasUnchanged: Bool
    public let nativeApplyAttempted: Bool
    public let nativeWriteObserved: Bool
    public let nativeArchiveSHA256: String
    public let nativeResponseSHA256: String
    public let nativeResponseBytes: Data
    public let objectMappings: [AnytypeOriginalAnnotationImportReceipt.ObjectMapping]

    fileprivate init(actual: OriginalAnnotationLifecycleObservation,
                     source: AnytypeOriginalAnnotationImportSource,
                     action: AnytypeOriginalAnnotationLifecycleAction, responseBytes: Data) throws {
        let value = actual.value, core = value.core
        guard ["archived", "restored", "promoted", "reverted", "applied", "unchanged"].contains(core.status),
              actual.nativeArchive != nil, let heads = core.heads,
              let hash = core.rootSnapshotSHA256, let archiveHash = core.nativeArchiveSHA256,
              let archiveID = value.archiveObjectID, let archiveHeads = value.archiveHeads,
              let archived = value.isArchived else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        self.source = source; self.action = action; objectID = core.rootID
        nativeHeads = heads; nativeRootSHA256 = hash
        archiveObjectID = archiveID; self.archiveHeads = archiveHeads; isArchived = archived
        documentRole = value.documentRole.flatMap(AnytypeOriginalAnnotationDocumentRole.init(rawValue:))
        wasUnchanged = core.status == "unchanged"
        nativeApplyAttempted = core.nativeApplyAttempted; nativeWriteObserved = core.nativeWriteObserved
        nativeArchiveSHA256 = archiveHash; nativeResponseBytes = responseBytes
        nativeResponseSHA256 = OriginalAnnotationRevisionWire.sha256(responseBytes)
        objectMappings = (core.mappings ?? []).map {
            .init(sourceSpaceID: $0.sourceSpaceID, sourceObjectID: $0.sourceObjectID, objectID: $0.objectID)
        }
    }
}

/// Late native effects are retained independently of an expired Host/UI waiter.
/// Refusal, conflict, partial copy or cancellation never grants an accepted result.
public struct AnytypeOriginalAnnotationLifecycleHistory: Sendable {
    public let nativeResponseBytes: Data?
    public let nativeResponseCopyError: AnytypeOriginalAnnotationImportHistory.CopyError?
    public let cancellationResponseBytes: Data?
    public let cancellationResponseCopyError: AnytypeOriginalAnnotationImportHistory.CopyError?
    public let cancellationWasScheduled: Bool
    public let cancellationAwaitFailed: Bool
    public let nativeApplyAttempted: Bool?
    public let nativeWriteObserved: Bool?
    public let conflictObserved: Bool
    public let verifiedNativeReceipt: AnytypeOriginalAnnotationLifecycleReceipt?

    @MainActor
    fileprivate init(actual: OriginalAnnotationImportCallHistory,
                     request: OriginalAnnotationLifecycleRequest, requestBytes: Data,
                     source: AnytypeOriginalAnnotationImportSource,
                     action: AnytypeOriginalAnnotationLifecycleAction,
                     desired: AnytypeOriginalEditorSnapshot?) {
        let response = AnytypeOriginalAnnotationImportHistory.copy(
            actual.response, failure: actual.responseCopyError)
        nativeResponseBytes = response.0; nativeResponseCopyError = response.1
        let cancellation = AnytypeOriginalAnnotationImportHistory.copy(
            actual.cancellationResponse, failure: actual.cancellationCopyError)
        cancellationResponseBytes = cancellation.0; cancellationResponseCopyError = cancellation.1
        cancellationWasScheduled = actual.cancellationWasScheduled
        cancellationAwaitFailed = actual.cancellationAwaitFailed
        let observed: OriginalAnnotationLifecycleObservation?
        if let original = actual.response, response.0 != nil, response.1 == nil {
            observed = try? OriginalAnnotationLifecycleObservation(response: original,
                request: request, requestBytes: requestBytes,
                accountID: source.accountID, spaceID: source.spaceID, desired: desired)
        } else { observed = nil }
        nativeApplyAttempted = observed?.value.core.nativeApplyAttempted
        nativeWriteObserved = observed?.value.core.nativeWriteObserved
        conflictObserved = observed?.value.core.status == "conflict"
            && observed?.value.core.nativeApplyAttempted == false
            && observed?.value.core.nativeWriteObserved == false
        if let observed, let bytes = response.0, !actual.cancellationWasScheduled,
           !actual.cancellationAwaitFailed, actual.cancellationResponse == nil,
           actual.cancellationCopyError == nil {
            verifiedNativeReceipt = try? AnytypeOriginalAnnotationLifecycleReceipt(
                actual: observed, source: source, action: action, responseBytes: bytes)
        } else { verifiedNativeReceipt = nil }
    }
}

/// Preparation is pure. Record the exact request/target/current saved source and
/// possible-dispatch witness durably BEFORE invoke. No automatic retry follows.
@MainActor
public final class AnytypeOriginalAnnotationLifecycleAttempt {
    public let source: AnytypeOriginalAnnotationImportSource
    public let action: AnytypeOriginalAnnotationLifecycleAction
    public let objectID: String
    public let requestBytes: Data
    public let requestSHA256: String
    private let sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime
    private let original: OriginalAnnotationImportAttempt
    private let delivery: OriginalAnnotationLifecycleDelivery

    fileprivate init(sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime,
                     action: AnytypeOriginalAnnotationLifecycleAction, objectID: String,
                     requestBytes: Data, original: OriginalAnnotationImportAttempt,
                     delivery: OriginalAnnotationLifecycleDelivery) {
        source = sourceLifetime.source; self.action = action; self.objectID = objectID
        self.requestBytes = requestBytes
        requestSHA256 = OriginalAnnotationRevisionWire.sha256(requestBytes)
        self.sourceLifetime = sourceLifetime; self.original = original; self.delivery = delivery
    }

    public var drainedHistory: AnytypeOriginalAnnotationLifecycleHistory? { delivery.history }
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

@MainActor
fileprivate final class OriginalAnnotationLifecycleOwnership {
    let binding: AnytypeOriginalEditorBinding
    let sourceCapture: EditorDocumentWriteCapture
    private let session: AnytypeOriginalEditorAccountSession
    private let sourceLifetime: AnytypeOriginalEditorSourceLifetime
    private let sourceIsCurrent: @MainActor (AnytypeOriginalEditorBinding) -> Bool
    private var claimed = false

    init(session: AnytypeOriginalEditorAccountSession, binding: AnytypeOriginalEditorBinding,
         sourceLifetime: AnytypeOriginalEditorSourceLifetime,
         sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorBinding) -> Bool) throws {
        sourceCapture = try EditorDocumentWriteCapture(sourceLifetime.lifetime)
        self.session = session; self.binding = binding
        self.sourceLifetime = sourceLifetime; self.sourceIsCurrent = sourceIsCurrent
    }

    func claim(session: AnytypeOriginalEditorAccountSession,
               source: AnytypeOriginalAnnotationImportSource) throws {
        try session.validateCurrent(); try sourceCapture.validate()
        guard self.session === session, !claimed, sourceLifetime.isCurrent, sourceIsCurrent(binding),
              source.namespace == "otzaria.local.annotation",
              source.annotationUUID == binding.annotationUUID,
              source.savedRevision == binding.expectedRevision,
              source.sourceDigest.utf8.elementsEqual(binding.sourceWitnessSHA256.utf8),
              source.accountID.utf8.elementsEqual(binding.accountID.utf8),
              source.spaceID.utf8.elementsEqual(binding.spaceID.utf8) else {
            throw AnytypeOriginalAnnotationLifecycleError.wrongCurrentObservation
        }
        claimed = true
    }
}

@MainActor
fileprivate final class OriginalAnnotationLifecycleDelivery {
    private(set) var history: AnytypeOriginalAnnotationLifecycleHistory?
    private let request: OriginalAnnotationLifecycleRequest
    private let bytes: Data
    private let source: AnytypeOriginalAnnotationImportSource
    private let action: AnytypeOriginalAnnotationLifecycleAction
    private let desired: AnytypeOriginalEditorSnapshot?
    private var deliver: (@MainActor @Sendable (AnytypeOriginalAnnotationLifecycleHistory) -> Void)?
    init(request: OriginalAnnotationLifecycleRequest, bytes: Data,
         source: AnytypeOriginalAnnotationImportSource, action: AnytypeOriginalAnnotationLifecycleAction,
         desired: AnytypeOriginalEditorSnapshot?,
         deliver: @escaping @MainActor @Sendable (AnytypeOriginalAnnotationLifecycleHistory) -> Void) {
        self.request = request; self.bytes = bytes; self.source = source; self.action = action
        self.desired = desired
        self.deliver = deliver
    }
    func receive(_ actual: OriginalAnnotationImportCallHistory) {
        guard history == nil else { return }
        let value = AnytypeOriginalAnnotationLifecycleHistory(actual: actual, request: request,
            requestBytes: bytes, source: source, action: action, desired: desired)
        history = value; let callback = deliver; deliver = nil; callback?(value)
    }
}

extension AnytypeOriginalEditorAccountSession {
    /// Reads the real dedicated Annotation and its Archive membership. Request a
    /// promotion role only when explicitly preparing that role's native type.
    public func readOriginalAnnotationLifecycle(
        binding: AnytypeOriginalEditorBinding,
        sourceLifetime: AnytypeOriginalEditorSourceLifetime,
        promotionRole: AnytypeOriginalAnnotationDocumentRole?,
        maximumBodyBytes: Int,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorBinding) -> Bool
    ) async throws -> AnytypeOriginalAnnotationLifecycleObservation {
        try await readLifecycle(binding: binding, sourceLifetime: sourceLifetime,
            documentRole: nil, promotionRole: promotionRole, maximumBodyBytes: maximumBodyBytes,
            sourceIsCurrent: sourceIsCurrent)
    }

    /// A separate original manifest-bound Document verifier. The Annotation-only
    /// read/replace APIs keep refusing promoted objects.
    public func readOriginalPromotedDocument(
        binding: AnytypeOriginalEditorBinding,
        documentRole: AnytypeOriginalAnnotationDocumentRole,
        sourceLifetime: AnytypeOriginalEditorSourceLifetime,
        maximumBodyBytes: Int,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorBinding) -> Bool
    ) async throws -> AnytypeOriginalAnnotationLifecycleObservation {
        try await readLifecycle(binding: binding, sourceLifetime: sourceLifetime,
            documentRole: documentRole, promotionRole: nil, maximumBodyBytes: maximumBodyBytes,
            sourceIsCurrent: sourceIsCurrent)
    }

    private func readLifecycle(
        binding: AnytypeOriginalEditorBinding,
        sourceLifetime: AnytypeOriginalEditorSourceLifetime,
        documentRole: AnytypeOriginalAnnotationDocumentRole?,
        promotionRole: AnytypeOriginalAnnotationDocumentRole?,
        maximumBodyBytes: Int,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorBinding) -> Bool
    ) async throws -> AnytypeOriginalAnnotationLifecycleObservation {
        try validateCurrent()
        guard identity.accountID.utf8.elementsEqual(binding.accountID.utf8),
              identity.spaceID.utf8.elementsEqual(binding.spaceID.utf8) else {
            throw AnytypeOriginalAnnotationImportError.wrongSelectedSpace
        }
        try sourceLifetime.claim(for: binding)
        do {
            try Task.checkCancellation()
            let frozen = try originalAnnotationImportSourceBinding(lifetime: sourceLifetime.lifetime,
                sourceIsCurrent: { sourceLifetime.isCurrent && sourceIsCurrent(binding) })
            let request = OriginalAnnotationLifecycleRequest(read: binding,
                documentRole: documentRole, promotionRole: promotionRole)
            let bytes = try request.encoded()
            let drained = OriginalAnnotationLifecycleReadDrain()
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
                throw AnytypeOriginalAnnotationLifecycleError.unobservedResponse
            }
            let observed = try OriginalAnnotationLifecycleObservation(response: response,
                request: request, requestBytes: bytes, accountID: binding.accountID,
                spaceID: binding.spaceID)
            guard observed.value.core.status == request.operation else {
                throw AnytypeOriginalAnnotationLifecycleError.unobservedResponse
            }
            let copied = try response.serializedData()
            guard copied.count <= OriginalAnnotationRevisionWire.maximumEnvelopeBytes else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
            let capture = try observed.makeCapture(binding: binding,
                maximumBodyBytes: maximumBodyBytes, responseBytes: copied)
            try frozen.validate()
            return try AnytypeOriginalAnnotationLifecycleObservation(actual: observed,
                capture: capture, responseBytes: copied, session: self, binding: binding,
                sourceLifetime: sourceLifetime, sourceIsCurrent: sourceIsCurrent)
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }

    /// Only this SAME account session's live observation can prepare the request.
    /// The original native engine conditionally compares BOTH root and Archive
    /// tokens; promotion also compares the actual manifest/type witness.
    public func prepareAnnotationLifecycle(
        action: AnytypeOriginalAnnotationLifecycleAction,
        observation: AnytypeOriginalAnnotationLifecycleObservation,
        sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalAnnotationImportSource) -> Bool,
        onDrained: @escaping @MainActor @Sendable (AnytypeOriginalAnnotationLifecycleHistory) -> Void
    ) throws -> AnytypeOriginalAnnotationLifecycleAttempt {
        try prepareLifecycle(action: action, observation: observation, desired: nil,
            sourceLifetime: sourceLifetime, sourceIsCurrent: sourceIsCurrent, onDrained: onDrained)
    }

    /// A saved local Annotation is applied to the SAME manifest-bound native
    /// Document through the original native typed conversion. No remote draft is
    /// opened, and the strict Annotation read/import validator remains unchanged.
    public func preparePromotedDocumentReplacement(
        snapshot: AnytypeOriginalEditorSnapshot,
        observation: AnytypeOriginalAnnotationLifecycleObservation,
        sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalAnnotationImportSource) -> Bool,
        onDrained: @escaping @MainActor @Sendable (AnytypeOriginalAnnotationLifecycleHistory) -> Void
    ) throws -> AnytypeOriginalAnnotationLifecycleAttempt {
        try prepareLifecycle(action: .replacePromotedDocument, observation: observation, desired: snapshot,
            sourceLifetime: sourceLifetime, sourceIsCurrent: sourceIsCurrent, onDrained: onDrained)
    }

    private func prepareLifecycle(
        action: AnytypeOriginalAnnotationLifecycleAction,
        observation: AnytypeOriginalAnnotationLifecycleObservation,
        desired: AnytypeOriginalEditorSnapshot?,
        sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalAnnotationImportSource) -> Bool,
        onDrained: @escaping @MainActor @Sendable (AnytypeOriginalAnnotationLifecycleHistory) -> Void
    ) throws -> AnytypeOriginalAnnotationLifecycleAttempt {
        try sourceLifetime.claim()
        do {
            try Task.checkCancellation()
            let source = sourceLifetime.source
            let selected = try currentOriginalSelection()
            guard selected.accountID.utf8.elementsEqual(source.accountID.utf8),
                  selected.accountInfo.accountSpaceId.utf8.elementsEqual(source.spaceID.utf8) else {
                throw AnytypeOriginalAnnotationImportError.wrongSelectedSpace
            }
            if let desired {
                guard action == .replacePromotedDocument,
                      source.namespace == "otzaria.local.annotation",
                      observation.actual.value.core.operation == "read_promoted",
                      observation.documentRole != nil, !observation.isArchived,
                      desired.provenance.annotationUUID == source.annotationUUID,
                      desired.provenance.hostProfileID.utf8.elementsEqual(observation.ownership.binding.hostProfileID.utf8),
                      desired.provenance.capturedAgainstRevision < Int64.max,
                      desired.provenance.capturedAgainstRevision + 1 == source.savedRevision,
                      OriginalAnnotationRevisionWire.sha256(desired.bodyBytes).utf8.elementsEqual(source.bodyDigest.utf8) else {
                    throw AnytypeOriginalAnnotationImportError.savedBodyMismatch
                }
                let saved = try AnytypeOriginalEditorLocalAnnotationSource(
                    hostProfileID: desired.provenance.hostProfileID,
                    annotationUUID: desired.provenance.annotationUUID,
                    expectedRevision: desired.provenance.capturedAgainstRevision,
                    sourceWitnessSHA256: desired.provenance.sourceWitnessSHA256,
                    payloadSHA256: nil)
                try OriginalEditorLocalAnnotationNativeBody.requireAnnotation(desired, source: saved)
            } else if action == .replacePromotedDocument {
                throw AnytypeOriginalAnnotationLifecycleError.unsupportedAction
            }
            try observation.ownership.claim(session: self, source: source)
            let frozen = try originalAnnotationImportSourceBinding(lifetime: sourceLifetime.lifetime,
                sourceIsCurrent: { sourceLifetime.isCurrent && sourceIsCurrent(source) })
                .requiringCapturedSource(observation.ownership.sourceCapture)
            let request = try OriginalAnnotationLifecycleRequest(action: action, observation: observation, desired: desired)
            let bytes = try request.encoded()
            let delivery = OriginalAnnotationLifecycleDelivery(request: request, bytes: bytes,
                source: source, action: action, desired: desired, deliver: onDrained)
            let original = try frozen.prepareOriginalAnnotationRevision(selection: selected,
                sourceSpaceID: desired?.provenance.spaceID ?? source.spaceID,
                sourceRootID: desired?.provenance.objectID ?? observation.objectID,
                envelope: bytes, onDrained: { delivery.receive($0) })
            try validateCurrent(); try frozen.validate()
            return AnytypeOriginalAnnotationLifecycleAttempt(sourceLifetime: sourceLifetime,
                action: action, objectID: observation.objectID, requestBytes: bytes,
                original: original, delivery: delivery)
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }
}

@MainActor
fileprivate final class OriginalAnnotationLifecycleReadDrain {
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

fileprivate struct OriginalAnnotationLifecycleRequest: Encodable, Sendable {
    let schema = 1
    let operation: String
    let targetRootID: String
    let annotationUUID: UUID
    var expectedHeads: [String]?
    var expectedRootSHA256: String?
    var expectedArchiveID: String?
    var expectedArchiveHeads: [String]?
    var expectedIsArchived: Bool?
    var documentRole: String?
    var promotionRole: String?
    var expectedManifestID: String?
    var expectedManifestSHA256: String?
    var expectedManifestHeads: [String]?
    var expectedDestinationTypeID: String?
    var expectedDestinationTypeUniqueKey: String?
    var expectedDestinationTypeHeads: [String]?
    var expectedAnnotationTypeID: String?
    var expectedAnnotationTypeUniqueKey: String?
    var expectedAnnotationTypeHeads: [String]?
    var desiredArchive: Data?
    var desiredArchiveSHA256: String?

    enum CodingKeys: String, CodingKey {
        case schema, operation
        case targetRootID = "target_root_id", annotationUUID = "annotation_uuid"
        case expectedHeads = "expected_heads", expectedRootSHA256 = "expected_root_sha256"
        case expectedArchiveID = "expected_archive_id", expectedArchiveHeads = "expected_archive_heads"
        case expectedIsArchived = "expected_is_archived", documentRole = "document_role"
        case promotionRole = "promotion_role", expectedManifestID = "expected_manifest_id"
        case expectedManifestSHA256 = "expected_manifest_sha256", expectedManifestHeads = "expected_manifest_heads"
        case expectedDestinationTypeID = "expected_destination_type_id"
        case expectedDestinationTypeUniqueKey = "expected_destination_type_unique_key"
        case expectedDestinationTypeHeads = "expected_destination_type_heads"
        case expectedAnnotationTypeID = "expected_annotation_type_id"
        case expectedAnnotationTypeUniqueKey = "expected_annotation_type_unique_key"
        case expectedAnnotationTypeHeads = "expected_annotation_type_heads"
        case desiredArchive = "desired_archive", desiredArchiveSHA256 = "desired_archive_sha256"
    }

    init(read binding: AnytypeOriginalEditorBinding,
         documentRole: AnytypeOriginalAnnotationDocumentRole?,
         promotionRole: AnytypeOriginalAnnotationDocumentRole?) {
        operation = documentRole == nil ? "read_lifecycle" : "read_promoted"
        targetRootID = binding.objectID; annotationUUID = binding.annotationUUID
        self.documentRole = documentRole?.rawValue; self.promotionRole = promotionRole?.rawValue
    }

    @MainActor
    init(action: AnytypeOriginalAnnotationLifecycleAction,
         observation: AnytypeOriginalAnnotationLifecycleObservation,
         desired: AnytypeOriginalEditorSnapshot?) throws {
        let actual = observation.actual.value
        targetRootID = observation.objectID
        annotationUUID = observation.ownership.binding.annotationUUID
        expectedHeads = observation.nativeHeads; expectedRootSHA256 = observation.nativeRootSHA256
        expectedArchiveID = observation.archiveObjectID; expectedArchiveHeads = observation.archiveHeads
        expectedIsArchived = observation.isArchived
        switch action {
        case .archive:
            operation = "archive"; documentRole = observation.documentRole?.rawValue
        case .restore:
            operation = "restore"; documentRole = observation.documentRole?.rawValue
        case .promote(let role):
            guard observation.documentRole == nil, observation.promotionRole == role,
                  !observation.isArchived, actual.core.operation == "read_lifecycle" else {
                throw AnytypeOriginalAnnotationLifecycleError.unsupportedAction
            }
            operation = "promote"; promotionRole = role.rawValue
        case .revertPromotion, .replacePromotedDocument:
            guard let role = observation.documentRole, !observation.isArchived,
                  actual.core.operation == "read_promoted" else {
                throw AnytypeOriginalAnnotationLifecycleError.unsupportedAction
            }
            documentRole = role.rawValue
            operation = action == .revertPromotion ? "revert_promotion" : "replace_promoted"
            if action == .replacePromotedDocument {
                guard let desired else { throw AnytypeOriginalAnnotationLifecycleError.unsupportedAction }
                desiredArchive = desired.nativeArchiveBytes; desiredArchiveSHA256 = desired.nativeArchiveSHA256
            }
        }
        if ["promote", "revert_promotion", "replace_promoted"].contains(operation) {
            expectedManifestID = actual.manifestObjectID; expectedManifestSHA256 = actual.manifestSHA256
            expectedManifestHeads = actual.manifestHeads; expectedDestinationTypeID = actual.promotionTypeID
            expectedDestinationTypeUniqueKey = actual.promotionTypeUniqueKey
            expectedDestinationTypeHeads = actual.promotionTypeHeads
            expectedAnnotationTypeID = actual.annotationTypeID
            expectedAnnotationTypeUniqueKey = actual.annotationTypeUniqueKey
            expectedAnnotationTypeHeads = actual.annotationTypeHeads
        }
    }

    func encoded() throws -> Data {
        guard OriginalAnnotationRevisionWire.identifier(targetRootID) else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        if ["archive", "restore", "promote", "revert_promotion", "replace_promoted"].contains(operation) {
            guard let heads = expectedHeads, OriginalAnnotationRevisionWire.heads(heads),
                  let hash = expectedRootSHA256, OriginalAnnotationRevisionWire.digest(hash),
                  let archive = expectedArchiveID, OriginalAnnotationRevisionWire.identifier(archive),
                  !archive.utf8.elementsEqual(targetRootID.utf8),
                  let archiveHeads = expectedArchiveHeads, OriginalAnnotationRevisionWire.heads(archiveHeads),
                  expectedIsArchived != nil else { throw AnytypeOriginalAnnotationLifecycleError.invalidResponse }
            if ["promote", "revert_promotion", "replace_promoted"].contains(operation) {
                guard (operation == "promote" ? documentRole == nil : promotionRole == nil),
                      let role = promotionRole ?? documentRole,
                      AnytypeOriginalAnnotationDocumentRole(rawValue: role) != nil,
                      let manifest = expectedManifestID, OriginalAnnotationRevisionWire.identifier(manifest),
                      let sha = expectedManifestSHA256, OriginalAnnotationRevisionWire.digest(sha),
                      let manifestHeads = expectedManifestHeads, OriginalAnnotationRevisionWire.heads(manifestHeads),
                      let type = expectedDestinationTypeID, OriginalAnnotationRevisionWire.identifier(type),
                      let key = expectedDestinationTypeUniqueKey, OriginalAnnotationRevisionWire.identifier(key),
                      let typeHeads = expectedDestinationTypeHeads, OriginalAnnotationRevisionWire.heads(typeHeads),
                      let annotationType = expectedAnnotationTypeID, OriginalAnnotationRevisionWire.identifier(annotationType),
                      expectedAnnotationTypeUniqueKey == OriginalAnnotationNativeMetadata.originalTypeUniqueKey,
                      let annotationHeads = expectedAnnotationTypeHeads, OriginalAnnotationRevisionWire.heads(annotationHeads),
                      !annotationType.utf8.elementsEqual(type.utf8),
                      expectedIsArchived == false else {
                    throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
                }
            }
        }
        if operation == "replace_promoted" {
            guard let bytes = desiredArchive, !bytes.isEmpty,
                  bytes.count <= OriginalAnnotationRevisionWire.maximumArchiveBytes,
                  desiredArchiveSHA256 == OriginalAnnotationRevisionWire.sha256(bytes) else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
        } else if desiredArchive != nil || desiredArchiveSHA256 != nil {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let bytes = try encoder.encode(self)
        guard bytes.count <= OriginalAnnotationRevisionWire.maximumEnvelopeBytes else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        return bytes
    }
}

fileprivate struct OriginalAnnotationLifecycleResult: Decodable, Sendable {
    let core: OriginalAnnotationRevisionResult
    let archiveObjectID: String?
    let archiveHeads: [String]?
    let isArchived: Bool?
    let mutationObjectID: String?
    let beforeMutationHeads: [String]?
    let mutationHeads: [String]?
    let classification: String?
    let documentRole: String?
    let documentTypeID: String?
    let documentTypeUniqueKey: String?
    let manifestObjectID: String?
    let manifestSHA256: String?
    let manifestJSON: String?
    let manifestHeads: [String]?
    let promotionRole: String?
    let promotionTypeID: String?
    let promotionTypeUniqueKey: String?
    let promotionTypeHeads: [String]?
    let annotationTypeID: String?
    let annotationTypeUniqueKey: String?
    let annotationTypeHeads: [String]?
    enum CodingKeys: String, CodingKey {
        case archiveObjectID = "archive_object_id", archiveHeads = "archive_heads", isArchived = "is_archived"
        case mutationObjectID = "mutation_object_id", beforeMutationHeads = "before_mutation_heads"
        case mutationHeads = "mutation_heads", classification, documentRole = "document_role"
        case documentTypeID = "document_type_id", documentTypeUniqueKey = "document_type_unique_key"
        case manifestObjectID = "manifest_object_id", manifestSHA256 = "manifest_sha256", manifestJSON = "manifest_json"
        case manifestHeads = "manifest_heads", promotionRole = "promotion_role", promotionTypeID = "promotion_type_id"
        case promotionTypeUniqueKey = "promotion_type_unique_key", promotionTypeHeads = "promotion_type_heads"
        case annotationTypeID = "annotation_type_id", annotationTypeUniqueKey = "annotation_type_unique_key"
        case annotationTypeHeads = "annotation_type_heads"
    }
    init(from decoder: Swift.Decoder) throws {
        core = try OriginalAnnotationRevisionResult(from: decoder)
        let c = try decoder.container(keyedBy: CodingKeys.self)
        archiveObjectID = try c.decodeIfPresent(String.self, forKey: .archiveObjectID)
        archiveHeads = try c.decodeIfPresent([String].self, forKey: .archiveHeads)
        isArchived = try c.decodeIfPresent(Bool.self, forKey: .isArchived)
        mutationObjectID = try c.decodeIfPresent(String.self, forKey: .mutationObjectID)
        beforeMutationHeads = try c.decodeIfPresent([String].self, forKey: .beforeMutationHeads)
        mutationHeads = try c.decodeIfPresent([String].self, forKey: .mutationHeads)
        classification = try c.decodeIfPresent(String.self, forKey: .classification)
        documentRole = try c.decodeIfPresent(String.self, forKey: .documentRole)
        documentTypeID = try c.decodeIfPresent(String.self, forKey: .documentTypeID)
        documentTypeUniqueKey = try c.decodeIfPresent(String.self, forKey: .documentTypeUniqueKey)
        manifestObjectID = try c.decodeIfPresent(String.self, forKey: .manifestObjectID)
        manifestSHA256 = try c.decodeIfPresent(String.self, forKey: .manifestSHA256)
        manifestJSON = try c.decodeIfPresent(String.self, forKey: .manifestJSON)
        manifestHeads = try c.decodeIfPresent([String].self, forKey: .manifestHeads)
        promotionRole = try c.decodeIfPresent(String.self, forKey: .promotionRole)
        promotionTypeID = try c.decodeIfPresent(String.self, forKey: .promotionTypeID)
        promotionTypeUniqueKey = try c.decodeIfPresent(String.self, forKey: .promotionTypeUniqueKey)
        promotionTypeHeads = try c.decodeIfPresent([String].self, forKey: .promotionTypeHeads)
        annotationTypeID = try c.decodeIfPresent(String.self, forKey: .annotationTypeID)
        annotationTypeUniqueKey = try c.decodeIfPresent(String.self, forKey: .annotationTypeUniqueKey)
        annotationTypeHeads = try c.decodeIfPresent([String].self, forKey: .annotationTypeHeads)
    }
}

fileprivate struct OriginalAnnotationLifecycleObservation: Sendable {
    let value: OriginalAnnotationLifecycleResult
    let report: Anytype_Model_ExportReport?
    let nativeArchive: OriginalAnnotationNativeArchiveComparison?
    let originHostProfileID: String?

    init(response: Anytype_Rpc.Annotation.Import.Response,
         request: OriginalAnnotationLifecycleRequest, requestBytes: Data,
         accountID: String, spaceID: String, desired: AnytypeOriginalEditorSnapshot? = nil) throws {
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
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        let result = try JSONDecoder().decode(OriginalAnnotationLifecycleResult.self,
            from: response.readback.nativeArchive)
        let core = result.core
        guard core.schema == 1, core.operation == request.operation,
              core.accountID.utf8.elementsEqual(accountID.utf8),
              core.spaceID.utf8.elementsEqual(spaceID.utf8),
              core.rootID.utf8.elementsEqual(request.targetRootID.utf8),
              core.annotationUUID == request.annotationUUID,
              (core.sourceArchiveSHA256 ?? "") == (request.desiredArchiveSHA256 ?? ""),
              ["read_lifecycle", "read_promoted", "archived", "restored", "promoted", "reverted",
               "applied", "unchanged", "conflict", "applied_unconfirmed", "refused"].contains(core.status) else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        value = result
        let accepted = ["read_lifecycle", "read_promoted", "archived", "restored",
                        "promoted", "reverted", "applied", "unchanged"].contains(core.status)
        if !accepted {
            if core.status == "conflict" {
                guard response.readback.observed, !core.nativeApplyAttempted, !core.nativeWriteObserved,
                      let heads = core.heads, OriginalAnnotationRevisionWire.heads(heads),
                      core.beforeHeads == heads, let hash = core.rootSnapshotSHA256,
                      OriginalAnnotationRevisionWire.digest(hash),
                      let archive = result.archiveObjectID, OriginalAnnotationRevisionWire.identifier(archive),
                      let archiveHeads = result.archiveHeads, OriginalAnnotationRevisionWire.heads(archiveHeads),
                      result.isArchived != nil else {
                    throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
                }
            }
            report = nil; nativeArchive = nil; originHostProfileID = nil
            return
        }
        guard response.error.code == .null, !response.nativeErrorPresent, response.nativeErrorCategory == .none,
              !response.cancellationRequested, response.readback.observed,
              response.readback.hasExportReport, response.readback.exportReport.status == .success,
              response.readback.exportReport.succeed > 0, response.readback.exportReport.objectErrors == 0,
              response.readback.exportReport.fileErrors == 0, response.readback.exportReport.issues.isEmpty,
              let heads = core.heads, OriginalAnnotationRevisionWire.heads(heads),
              let before = core.beforeHeads, OriginalAnnotationRevisionWire.heads(before),
              let hash = core.rootSnapshotSHA256, OriginalAnnotationRevisionWire.digest(hash),
              let bytes = core.nativeArchive, !bytes.isEmpty,
              bytes.count <= OriginalAnnotationRevisionWire.maximumArchiveBytes,
              core.nativeArchiveSHA256 == OriginalAnnotationRevisionWire.sha256(bytes),
              let archiveID = result.archiveObjectID, OriginalAnnotationRevisionWire.identifier(archiveID),
              !archiveID.utf8.elementsEqual(core.rootID.utf8),
              let archiveHeads = result.archiveHeads, OriginalAnnotationRevisionWire.heads(archiveHeads),
              let archived = result.isArchived else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        try Self.requireOperation(result, request: request)
        let report = response.readback.exportReport
        let actual = try OriginalAnnotationNativeArchiveComparison(archiveBytes: bytes,
            rootID: core.rootID, spaceID: spaceID,
            formatVersion: AnytypeOriginalEditorSnapshot.formatVersion,
            reportedObjectCount: report.succeed)
        guard let mappings = core.mappings, !mappings.isEmpty, mappings.count <= 8_192,
              mappings.allSatisfy({ OriginalAnnotationRevisionWire.identifier($0.sourceSpaceID)
                && OriginalAnnotationRevisionWire.identifier($0.sourceObjectID)
                && OriginalAnnotationRevisionWire.identifier($0.objectID) }),
              Set(mappings.map { Data($0.sourceObjectID.utf8) }).count == mappings.count,
              Set(mappings.map { Data($0.objectID.utf8) }).count == mappings.count else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        if request.operation == "replace_promoted" {
            guard let desired else { throw AnytypeOriginalAnnotationLifecycleError.invalidResponse }
            let source = try OriginalEditorLocalAnnotationNativeBody.decoded(desired)
            guard request.desiredArchive == desired.nativeArchiveBytes,
                  mappings.allSatisfy({ $0.sourceSpaceID.utf8.elementsEqual(desired.provenance.spaceID.utf8) }),
                  Set(mappings.map { Data($0.sourceObjectID.utf8) }) == Set(source.objectIDs.map { Data($0.utf8) }),
                  Set(mappings.map { Data($0.objectID.utf8) }).isSubset(of: Set(actual.objectIDs.map { Data($0.utf8) })),
                  mappings.filter({ $0.sourceObjectID.utf8.elementsEqual(desired.provenance.objectID.utf8)
                    && $0.objectID.utf8.elementsEqual(core.rootID.utf8) }).count == 1 else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
        } else {
            guard desired == nil,
                  mappings.allSatisfy({ $0.sourceSpaceID.utf8.elementsEqual(spaceID.utf8)
                    && $0.sourceObjectID.utf8.elementsEqual($0.objectID.utf8) }),
                  Set(mappings.map { Data($0.objectID.utf8) }) == Set(actual.objectIDs.map { Data($0.utf8) }) else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
        }
        let details = actual.rootSnapshot.details
        let field = OriginalEditorLocalAnnotationNativeBody.string
        let prefix = "otzaria.local.draft:"
        guard field(details, OriginalAnnotationMetadataField.schemaProtocol.rawValue)
                == OriginalAnnotationNativeMetadata.protocolValue,
              field(details, OriginalAnnotationMetadataField.namespace.rawValue) == "otzaria.local.annotation",
              OriginalEditorLocalAnnotationNativeBody.annotationUUIDMatches(
                field(details, OriginalAnnotationMetadataField.annotationUUID.rawValue), expected: core.annotationUUID),
              let destination = field(details, OriginalAnnotationMetadataField.creationDestination.rawValue),
              destination.utf8.starts(with: prefix.utf8) else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        let origin = String(destination.dropFirst(prefix.count))
        guard !origin.isEmpty, origin.utf8.count <= 512, !origin.utf8.contains(0),
              try Self.nativeBool(details, key: "isArchived") == archived,
              try Self.nativeBool(details, key: "isDeleted") == false else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        let type = try Self.rootType(archive: bytes, root: actual.rootSnapshot, spaceID: spaceID)
        if result.classification == "annotation" {
            guard (result.documentRole ?? "").isEmpty,
                  (result.documentTypeID ?? "").isEmpty, (result.documentTypeUniqueKey ?? "").isEmpty,
                  field(details, OriginalAnnotationMetadataField.classification.rawValue) == "annotation",
                  type.uniqueKey.utf8.elementsEqual(OriginalAnnotationNativeMetadata.originalTypeUniqueKey.utf8),
                  actual.rootSnapshot.objectTypes.count == 1,
                  actual.rootSnapshot.objectTypes[0].utf8.elementsEqual(type.uniqueKey.utf8) else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
        } else if result.classification == "promoted_document" {
            guard let role = result.documentRole, AnytypeOriginalAnnotationDocumentRole(rawValue: role) != nil,
                  field(details, OriginalAnnotationMetadataField.classification.rawValue)?.utf8.elementsEqual(role.utf8) == true,
                  result.documentTypeID?.utf8.elementsEqual(type.objectID.utf8) == true,
                  result.documentTypeUniqueKey?.utf8.elementsEqual(type.uniqueKey.utf8) == true,
                  actual.rootSnapshot.objectTypes.count == 1,
                  actual.rootSnapshot.objectTypes[0].utf8.elementsEqual(type.uniqueKey.utf8),
                  actual.rootSnapshot.key.isEmpty else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
        } else { throw AnytypeOriginalAnnotationLifecycleError.invalidResponse }
        let role = request.promotionRole ?? request.documentRole
        if let role {
            try Self.requireManifest(result, role: role, spaceID: spaceID)
            guard let annotationTypeID = result.annotationTypeID,
                  OriginalAnnotationRevisionWire.identifier(annotationTypeID),
                  result.annotationTypeUniqueKey == OriginalAnnotationNativeMetadata.originalTypeUniqueKey,
                  let annotationHeads = result.annotationTypeHeads, OriginalAnnotationRevisionWire.heads(annotationHeads),
                  let documentTypeID = result.promotionTypeID,
                  !annotationTypeID.utf8.elementsEqual(documentTypeID.utf8) else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
            // Both schemas are exported by the original native exporter from
            // genuinely discovered and locked native IDs, including after revert.
            let annotationType = try Self.nativeType(archive: bytes, objectID: annotationTypeID, spaceID: spaceID)
            let documentType = try Self.nativeType(archive: bytes, objectID: documentTypeID, spaceID: spaceID)
            guard annotationType.uniqueKey == result.annotationTypeUniqueKey,
                  documentType.uniqueKey == result.promotionTypeUniqueKey,
                  result.classification != "annotation" || type.objectID == annotationTypeID else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
            if result.classification == "promoted_document" {
                guard result.documentRole == role,
                      result.documentTypeID == result.promotionTypeID,
                      result.documentTypeUniqueKey == result.promotionTypeUniqueKey else {
                    throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
                }
            }
        } else {
            guard (result.documentRole ?? "").isEmpty, (result.promotionRole ?? "").isEmpty,
                  (result.manifestObjectID ?? "").isEmpty, (result.manifestJSON ?? "").isEmpty else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
        }
        self.report = report; nativeArchive = actual; originHostProfileID = origin
    }

    private static func requireOperation(_ value: OriginalAnnotationLifecycleResult,
                                         request: OriginalAnnotationLifecycleRequest) throws {
        let core = value.core
        switch request.operation {
        case "read_lifecycle", "read_promoted":
            guard core.status == request.operation, !core.nativeApplyAttempted, !core.nativeWriteObserved,
                  core.beforeHeads == core.heads, (value.mutationObjectID ?? "").isEmpty,
                  (value.beforeMutationHeads ?? []).isEmpty, (value.mutationHeads ?? []).isEmpty,
                  value.classification == (request.operation == "read_promoted" ? "promoted_document" : "annotation"),
                  (value.documentRole ?? "") == (request.documentRole ?? "") else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
        case "archive", "restore":
            let target = request.operation == "archive"
            guard core.beforeHeads == request.expectedHeads,
                  core.rootSnapshotSHA256 == request.expectedRootSHA256,
                  value.archiveObjectID == request.expectedArchiveID,
                  value.isArchived == target,
                  value.mutationObjectID == value.archiveObjectID,
                  value.beforeMutationHeads == request.expectedArchiveHeads,
                  value.mutationHeads == value.archiveHeads,
                  (value.documentRole ?? "") == (request.documentRole ?? ""),
                  value.classification == (request.documentRole == nil ? "annotation" : "promoted_document") else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
            if core.status == "unchanged" {
                guard !core.nativeApplyAttempted, !core.nativeWriteObserved,
                      request.expectedIsArchived == target, core.heads == core.beforeHeads,
                      value.archiveHeads == request.expectedArchiveHeads else {
                    throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
                }
            } else {
                guard core.status == (target ? "archived" : "restored"),
                      request.expectedIsArchived != target, core.nativeApplyAttempted, core.nativeWriteObserved,
                      value.archiveHeads != request.expectedArchiveHeads else {
                    throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
                }
            }
        case "promote", "revert_promotion":
            let promotion = request.operation == "promote"
            guard core.status == (promotion ? "promoted" : "reverted"),
                  core.nativeApplyAttempted, core.nativeWriteObserved,
                  core.beforeHeads == request.expectedHeads,
                  value.mutationObjectID == core.rootID, value.beforeMutationHeads == request.expectedHeads,
                  value.mutationHeads == core.heads, core.heads != core.beforeHeads,
                  value.archiveObjectID == request.expectedArchiveID,
                  value.archiveHeads == request.expectedArchiveHeads, request.expectedIsArchived == false,
                  value.isArchived == false,
                  value.classification == (promotion ? "promoted_document" : "annotation"),
                  (value.documentRole ?? "") == (promotion ? request.promotionRole ?? "" : ""),
                  promotion || ((value.documentTypeID ?? "").isEmpty && (value.documentTypeUniqueKey ?? "").isEmpty) else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
            try requireTypePreconditions(value, request: request)
        case "replace_promoted":
            guard core.beforeHeads == request.expectedHeads,
                  value.mutationObjectID == core.rootID,
                  value.beforeMutationHeads == request.expectedHeads,
                  value.mutationHeads == core.heads,
                  value.archiveObjectID == request.expectedArchiveID,
                  value.archiveHeads == request.expectedArchiveHeads,
                  request.expectedIsArchived == false, value.isArchived == false,
                  value.classification == "promoted_document",
                  value.documentRole == request.documentRole,
                  value.documentTypeID == request.expectedDestinationTypeID,
                  value.documentTypeUniqueKey == request.expectedDestinationTypeUniqueKey else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
            try requireTypePreconditions(value, request: request)
            if core.status == "applied" {
                guard core.nativeApplyAttempted, core.nativeWriteObserved,
                      core.heads != core.beforeHeads else {
                    throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
                }
            } else {
                guard core.status == "unchanged", !core.nativeApplyAttempted, !core.nativeWriteObserved,
                      core.heads == core.beforeHeads, core.rootSnapshotSHA256 == request.expectedRootSHA256 else {
                    throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
                }
            }
        default: throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
    }

    private static func requireTypePreconditions(_ value: OriginalAnnotationLifecycleResult,
                                                 request: OriginalAnnotationLifecycleRequest) throws {
        guard value.manifestObjectID == request.expectedManifestID,
              value.manifestSHA256 == request.expectedManifestSHA256,
              value.manifestHeads == request.expectedManifestHeads,
              value.promotionTypeID == request.expectedDestinationTypeID,
              value.promotionTypeUniqueKey == request.expectedDestinationTypeUniqueKey,
              value.promotionTypeHeads == request.expectedDestinationTypeHeads,
              value.annotationTypeID == request.expectedAnnotationTypeID,
              value.annotationTypeUniqueKey == request.expectedAnnotationTypeUniqueKey,
              value.annotationTypeHeads == request.expectedAnnotationTypeHeads else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
    }

    private static func requireManifest(_ value: OriginalAnnotationLifecycleResult,
                                        role: String, spaceID: String) throws {
        guard let id = value.manifestObjectID, OriginalAnnotationRevisionWire.identifier(id),
              let raw = value.manifestJSON, !raw.isEmpty, raw.utf8.count <= 131_072,
              let hash = value.manifestSHA256, OriginalAnnotationRevisionWire.digest(hash),
              hash == OriginalAnnotationRevisionWire.sha256(Data(raw.utf8)),
              let heads = value.manifestHeads, OriginalAnnotationRevisionWire.heads(heads),
              value.promotionRole == role,
              let type = value.promotionTypeID, OriginalAnnotationRevisionWire.identifier(type),
              let key = value.promotionTypeUniqueKey, OriginalAnnotationRevisionWire.identifier(key),
              key.hasPrefix("ot-"), let typeHeads = value.promotionTypeHeads,
              OriginalAnnotationRevisionWire.heads(typeHeads) else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        // Reuse the actual shared schema/model; never create a parallel manifest.
        let manifest = try PinkhaSpaceManifest.fromJSONString(raw)
        let roles = AnytypeOriginalAnnotationDocumentRole.allCases.map(\.rawValue)
        let roleTypes = roles.compactMap { manifest.registeredDocumentTypes[$0] }
        guard manifest.schemaVersion == PinkhaSpaceManifest.currentSchemaVersion,
              manifest.spaceId.utf8.elementsEqual(spaceID.utf8),
              manifest.manifestObjectId.map({ $0.isEmpty || $0.utf8.elementsEqual(id.utf8) }) ?? true,
              manifest.isFullyProvisioned, roleTypes.count == roles.count,
              roleTypes.allSatisfy({ OriginalAnnotationRevisionWire.identifier($0)
                && !$0.utf8.elementsEqual(id.utf8) && !$0.utf8.elementsEqual(value.core.rootID.utf8) }),
              Set(roleTypes.map { Data($0.utf8) }).count == roles.count,
              manifest.registeredDocumentTypes[role]?.utf8.elementsEqual(type.utf8) == true,
              roles.allSatisfy({ manifest.defaultTemplateIds[$0].map(OriginalAnnotationRevisionWire.identifier) ?? false }),
              [manifest.parentPropertyId, manifest.parentPropertyKey, manifest.orderPropertyId,
               manifest.orderPropertyKey, manifest.documentAssociationsPropertyId,
               manifest.documentAssociationsPropertyKey, manifest.folderTypeId,
               manifest.bookFolderTypeId].allSatisfy(OriginalAnnotationRevisionWire.identifier) else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
    }

    private static func nativeBool(_ details: Google_Protobuf_Struct, key: String) throws -> Bool {
        guard let value = details.fields[key] else { return false }
        guard case .boolValue(let flag)? = value.kind else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        return flag
    }

    private static func rootType(archive bytes: Data, root: Anytype_Model_SmartBlockSnapshotBase,
                                 spaceID: String) throws -> (objectID: String, uniqueKey: String) {
        guard let id = OriginalEditorLocalAnnotationNativeBody.annotationTypeID(root.details),
              OriginalAnnotationRevisionWire.identifier(id), !id.contains("/") else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        return try nativeType(archive: bytes, objectID: id, spaceID: spaceID)
    }

    private static func nativeType(archive bytes: Data, objectID id: String,
                                   spaceID: String) throws -> (objectID: String, uniqueKey: String) {
        guard OriginalAnnotationRevisionWire.identifier(id), !id.contains("/") else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        let archive = try Archive(data: bytes, accessMode: .read)
        guard let entry = archive["types/" + id + ".pb"] else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        var data = Data()
        _ = try archive.extract(entry, bufferSize: 16_384, skipCRC32: false) { chunk in
            guard data.count + chunk.count <= OriginalAnnotationNativeArchiveLayout.maximumExpandedBytes else {
                throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
            }
            data.append(chunk)
        }
        try OriginalAnnotationNativeMapKeyGuard.validate(data)
        let wire = try OriginalAnnotationNativeSnapshotWire(serializedBytes: data)
        guard wire.sbType == .sttype, let model = wire.snapshot?.data,
              OriginalEditorLocalAnnotationNativeBody.string(model.details, "id")?.utf8.elementsEqual(id.utf8) == true,
              OriginalEditorLocalAnnotationNativeBody.string(model.details, "spaceId")?.utf8.elementsEqual(spaceID.utf8) == true,
              let key = OriginalEditorLocalAnnotationNativeBody.string(model.details, "uniqueKey"),
              OriginalAnnotationRevisionWire.identifier(key),
              try nativeBool(model.details, key: "isArchived") == false,
              try nativeBool(model.details, key: "isDeleted") == false,
              try nativeBool(model.details, key: "isUninstalled") == false else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        return (id, key)
    }

    func makeCapture(binding: AnytypeOriginalEditorBinding, maximumBodyBytes: Int,
                     responseBytes: Data) throws -> AnytypeOriginalEditorSnapshotCapture {
        guard ["read_lifecycle", "read_promoted"].contains(value.core.status),
              let report, let bytes = value.core.nativeArchive,
              nativeArchive != nil, let originHostProfileID else {
            throw AnytypeOriginalAnnotationLifecycleError.invalidResponse
        }
        let directory = try OriginalEditorArchiveFiles.makeOwnedDirectory()
        let archive = directory.appendingPathComponent("original-native.zip")
        let reportBytes = try report.serializedData()
        try bytes.write(to: archive, options: .withoutOverwriting)
        try reportBytes.write(to: directory.appendingPathComponent("native-export-report.pb"), options: .withoutOverwriting)
        try responseBytes.write(to: directory.appendingPathComponent("native-lifecycle-response.pb"), options: .withoutOverwriting)
        let snapshot = try AnytypeOriginalEditorSnapshot.frame(archive: bytes,
            reportBytes: reportBytes, responseCount: report.succeed, binding: binding,
            maximumBodyBytes: maximumBodyBytes, transportOriginHostProfileID: originHostProfileID)
        return .init(snapshot: snapshot, retainedArchiveURL: archive, retainedDirectoryURL: directory)
    }
}
