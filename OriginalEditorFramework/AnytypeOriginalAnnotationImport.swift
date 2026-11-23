import Foundation
import CryptoKit
import SwiftProtobuf
@_spi(OriginalEditor) import ProtobufMessages

/// The immutable comparison tuple from the Host's newly committed preparation.
/// IDs and digests are data. They do not create an account, selected Space,
/// native destination, current source, saved-row ownership or acknowledgement.
public struct AnytypeOriginalAnnotationImportSource: Sendable, Equatable {
    public let namespace: String
    public let annotationUUID: UUID
    public let preparedSessionID: UUID
    public let attemptID: UUID
    public let savedRevision: Int64
    public let sourceDigest: String
    public let payloadDigest: String
    public let bodyDigest: String
    public let accountID: String
    public let spaceID: String

    public init(
        namespace: String,
        annotationUUID: UUID,
        preparedSessionID: UUID,
        attemptID: UUID,
        savedRevision: Int64,
        sourceDigest: String,
        payloadDigest: String,
        bodyDigest: String,
        accountID: String,
        spaceID: String
    ) throws {
        guard [namespace, accountID, spaceID].allSatisfy({
            !$0.isEmpty && $0.utf8.count <= 16_384 && !$0.utf8.contains(0)
        }), savedRevision >= 0,
              [sourceDigest, payloadDigest, bodyDigest].allSatisfy(Self.isDigest) else {
            throw AnytypeOriginalAnnotationImportError.invalidSource
        }
        self.namespace = namespace
        self.annotationUUID = annotationUUID
        self.preparedSessionID = preparedSessionID
        self.attemptID = attemptID
        self.savedRevision = savedRevision
        self.sourceDigest = sourceDigest
        self.payloadDigest = payloadDigest
        self.bodyDigest = bodyDigest
        self.accountID = accountID
        self.spaceID = spaceID
    }

    public static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.namespace.utf8.elementsEqual(rhs.namespace.utf8)
            && lhs.annotationUUID == rhs.annotationUUID
            && lhs.preparedSessionID == rhs.preparedSessionID
            && lhs.attemptID == rhs.attemptID
            && lhs.savedRevision == rhs.savedRevision
            && lhs.sourceDigest.utf8.elementsEqual(rhs.sourceDigest.utf8)
            && lhs.payloadDigest.utf8.elementsEqual(rhs.payloadDigest.utf8)
            && lhs.bodyDigest.utf8.elementsEqual(rhs.bodyDigest.utf8)
            && lhs.accountID.utf8.elementsEqual(rhs.accountID.utf8)
            && lhs.spaceID.utf8.elementsEqual(rhs.spaceID.utf8)
    }

    private static func isDigest(_ value: String) -> Bool {
        value.utf8.count == 64
            && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
}

public enum AnytypeOriginalAnnotationImportError: Error, Sendable, Equatable {
    case invalidSource
    case retiredSource
    case sourceAlreadyUsed
    case wrongSelectedSpace
    case savedBodyMismatch
}

/// A Host-owned PRE-IMPORT saved source. It has no existing-object binding.
/// The Host creates it only from its actual newly prepared saved-row owner and
/// synchronously retires it before any source/session/database replacement.
/// Decoding historical persistence cannot reconstruct its one-use claim.
@MainActor
public final class AnytypeOriginalAnnotationImportSourceLifetime {
    public nonisolated let source: AnytypeOriginalAnnotationImportSource
    internal nonisolated let lifetime = EditorDocumentWriteLifetime()
    private var claimed = false

    public init(source: AnytypeOriginalAnnotationImportSource) {
        self.source = source
    }

    public nonisolated var isCurrent: Bool { lifetime.token() != nil }

    public nonisolated func retire() {
        lifetime.markUnavailable()
    }

    fileprivate func claim() throws {
        guard isCurrent else { throw AnytypeOriginalAnnotationImportError.retiredSource }
        guard !claimed else { throw AnytypeOriginalAnnotationImportError.sourceAlreadyUsed }
        claimed = true
    }

    deinit { lifetime.markUnavailable() }
}

/// Complete copied historical messages from the actual one-use original calls.
/// There is no public initializer, decoder, destination mapping or ACK receipt.
/// Serialized protobuf retains unknown fields; native wire ordering is not
/// promised. A nil message is unobserved and never proves absence of effects.
public struct AnytypeOriginalAnnotationImportHistory: Sendable {
    public enum CopyError: Sendable, Equatable {
        case callAlreadyInvoked
        case copyFailed
        case responseTooLarge
        case duplicateNativeResponse
        case unrecognizedCopyFailure
    }

    public let nativeResponseBytes: Data?
    public let nativeResponseCopyError: CopyError?
    public let cancellationResponseBytes: Data?
    public let cancellationResponseCopyError: CopyError?
    public let cancellationWasScheduled: Bool
    public let cancellationAwaitFailed: Bool

    fileprivate init(_ actual: OriginalAnnotationImportCallHistory) {
        let response = Self.copy(actual.response, failure: actual.responseCopyError)
        nativeResponseBytes = response.0
        nativeResponseCopyError = response.1
        let cancellation = Self.copy(actual.cancellationResponse, failure: actual.cancellationCopyError)
        cancellationResponseBytes = cancellation.0
        cancellationResponseCopyError = cancellation.1
        cancellationWasScheduled = actual.cancellationWasScheduled
        cancellationAwaitFailed = actual.cancellationAwaitFailed
    }

    private static func copy<MessageType: Message & Sendable>(
        _ message: MessageType?,
        failure: OriginalAnnotationImportHistoryError?
    ) -> (Data?, CopyError?) {
        if let failure {
            switch failure {
            case .callAlreadyInvoked: return (nil, .callAlreadyInvoked)
            case .copyFailed: return (nil, .copyFailed)
            case .responseTooLarge: return (nil, .responseTooLarge)
            case .duplicateNativeResponse: return (nil, .duplicateNativeResponse)
            @unknown default: return (nil, .unrecognizedCopyFailure)
            }
        }
        guard let message else { return (nil, nil) }
        do {
            let bytes = try message.serializedData()
            guard bytes.count <= 2 * 1_024 * 1_024 else { return (nil, .responseTooLarge) }
            return (bytes, nil)
        } catch {
            return (nil, .copyFailed)
        }
    }
}

/// Held independently of an awaiting UI task. The actual original native drain
/// owns this delivery until it has copied both histories and cleared its callback.
@MainActor
fileprivate final class OriginalAnnotationImportPublicDelivery {
    private(set) var history: AnytypeOriginalAnnotationImportHistory?
    private var deliver: (@MainActor @Sendable (AnytypeOriginalAnnotationImportHistory) -> Void)?

    init(deliver: @escaping @MainActor @Sendable (AnytypeOriginalAnnotationImportHistory) -> Void) {
        self.deliver = deliver
    }

    func receive(_ actual: OriginalAnnotationImportCallHistory) {
        // The concrete original owner already closes its drain exactly once.
        guard history == nil else { return }
        let observed = AnytypeOriginalAnnotationImportHistory(actual)
        history = observed
        let callback = deliver
        deliver = nil
        callback?(observed)
    }
}

/// One closed original Import/Cancel attempt. It cannot be decoded, recreated
/// from a history or supplied with a replacement native executor. The Host must
/// commit its exact dispatch_may_have_occurred transition before invoking it.
@MainActor
public final class AnytypeOriginalAnnotationImportAttempt {
    public enum CancellationScheduling: Sendable {
        case beforeInvocation
        case scheduled
        case alreadyScheduled
        case importDrained
    }

    public let source: AnytypeOriginalAnnotationImportSource
    private let sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime
    private let original: OriginalAnnotationImportAttempt
    private let delivery: OriginalAnnotationImportPublicDelivery

    fileprivate init(
        sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime,
        original: OriginalAnnotationImportAttempt,
        delivery: OriginalAnnotationImportPublicDelivery
    ) {
        source = sourceLifetime.source
        self.sourceLifetime = sourceLifetime
        self.original = original
        self.delivery = delivery
    }

    /// Available only after both real original native calls have drained.
    /// A thrown await, cancellation response or elapsed timeout cannot set it.
    public var drainedHistory: AnytypeOriginalAnnotationImportHistory? { delivery.history }

    /// Dispatches the exact privately prepared typed request once. Native errors
    /// still throw. A cancelled waiter still receives complete late history
    /// through the separately owned onDrained callback; no retry is created.
    public func invoke() async throws {
        _ = try await original.invoke()
    }

    /// Local scheduling information only. NOT_OBSERVED from native cancellation
    /// is historical data in onDrained and cannot substitute for real drain.
    @discardableResult
    public func requestCancellation() -> CancellationScheduling {
        switch original.requestCancellation() {
        case .beforeInvocation: return .beforeInvocation
        case .scheduled: return .scheduled
        case .alreadyScheduled: return .alreadyScheduled
        case .importDrained: return .importDrained
        }
    }

    public func retire() {
        sourceLifetime.retire()
    }

    deinit { sourceLifetime.retire() }
}

extension AnytypeOriginalEditorAccountSession {
    /// Preparation performs no RPC. The selected account/Space, registration,
    /// subscription permissions and original account runtime remain genuine.
    /// The Host supplies its original prepared saved-row lifetime and a pure
    /// synchronous observation of that SAME owner; IDs alone are not currentness.
    ///
    /// After this returns, the Host commits its existing possible-dispatch
    /// transition. Only its actual still-owned recorded outcome may call
    /// invoke on this handle. A recordedWithoutOwnership outcome is retained
    /// without dispatch, without automatic abandonment or a replacement attempt.
    @MainActor
    public func prepareAnnotationImport(
        snapshot: AnytypeOriginalEditorSnapshot,
        sourceLifetime: AnytypeOriginalAnnotationImportSourceLifetime,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalAnnotationImportSource) -> Bool,
        onDrained: @escaping @MainActor @Sendable (AnytypeOriginalAnnotationImportHistory) -> Void
    ) throws -> AnytypeOriginalAnnotationImportAttempt {
        try sourceLifetime.claim()
        do {
            try Task.checkCancellation()
            let source = sourceLifetime.source
            let selection = try currentOriginalSelection()
            guard selection.accountID.utf8.elementsEqual(source.accountID.utf8),
                  selection.accountInfo.accountSpaceId.utf8.elementsEqual(source.spaceID.utf8) else {
                throw AnytypeOriginalAnnotationImportError.wrongSelectedSpace
            }
            let bodyDigest = SHA256.hash(data: snapshot.bodyBytes)
                .map { String(format: "%02x", $0) }.joined()
            guard bodyDigest.utf8.elementsEqual(source.bodyDigest.utf8),
                  snapshot.provenance.annotationUUID == source.annotationUUID,
                  snapshot.provenance.sourceWitnessSHA256.utf8.elementsEqual(source.sourceDigest.utf8) else {
                throw AnytypeOriginalAnnotationImportError.savedBodyMismatch
            }
            // The framed capture's account/root/revision remain historical
            // input. The actual selected target and saved-row revision above
            // are separate; no historical revision is promoted into a live CAS.
            let binding = try originalAnnotationImportSourceBinding(
                lifetime: sourceLifetime.lifetime,
                sourceIsCurrent: {
                    sourceLifetime.isCurrent && sourceIsCurrent(source)
                }
            )
            let delivery = OriginalAnnotationImportPublicDelivery(deliver: onDrained)
            let original = try binding.prepareOriginalAnnotationImport(
                selection: selection,
                sourceSpaceID: snapshot.provenance.spaceID,
                sourceRootID: snapshot.provenance.objectID,
                archive: snapshot.nativeArchiveBytes,
                onDrained: { delivery.receive($0) }
            )
            try validateCurrent()
            try binding.validate()
            return AnytypeOriginalAnnotationImportAttempt(
                sourceLifetime: sourceLifetime, original: original, delivery: delivery
            )
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }
}
