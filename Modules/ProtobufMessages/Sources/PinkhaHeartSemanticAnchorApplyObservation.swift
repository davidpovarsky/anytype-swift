#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation

/// Diagnostic values only. This carries no request, native reply, receipt,
/// account identity, content, authority, callback, or retry capability.
public struct PinkhaHeartSemanticAnchorApplyObservation: Sendable {
    public enum Phase: String, Equatable, Sendable {
        case checkingPreflight
        case readingRuntime
        case checkingRuntime
        case readingCurrent
        case checkingCurrent
        case consumed
        case checkingQueuedOwner
        case invokingNative
        case checkingCapturedOwner
        case decodingReply
        case validatingEvent
        case checkingEventOwner
        case creatingPublicationFence
        case publishing
        case checkingPublishedOwner
        case readingReadback
        case checkingReadbackOwner
        case validatingReadback
        case verified
    }

    public enum Failure: String, Equatable, Sendable {
        case invalidRequest
        case limitExceeded
        case selectionAlreadyLinked
        case changedDocument
        case retiredOwner
        case unsupportedRuntime
        case unavailablePublication
        case invalidReply
        case uncertain
        case nativeRefusal
        case cancellation
        case other
    }

    public static let maximumPhaseCount = 32
    public private(set) var phases: [Phase] = []
    public private(set) var phasesTruncated = false
    public private(set) var latestPhase: Phase?
    public private(set) var nativeReplyBytes: Int?
    public private(set) var decodedNativeOutcome: PinkhaHeartSemanticAnchorOutcome?
    public private(set) var nativeReceiptDecoded = false
    public private(set) var eventBytes: Int?
    public private(set) var publicationReturned: Bool?
    public private(set) var firstFailurePhase: Phase?
    public private(set) var firstFailure: Failure?

    public static func classify(_ error: Error) -> Failure {
        guard let semantic = error as? PinkhaHeartSemanticAnchorError else {
            return error is CancellationError ? .cancellation : .other
        }
        switch semantic {
        case .invalidRequest: return .invalidRequest
        case .limitExceeded: return .limitExceeded
        case .selectionAlreadyLinked: return .selectionAlreadyLinked
        case .changedDocument: return .changedDocument
        case .retiredOwner: return .retiredOwner
        case .unsupportedRuntime: return .unsupportedRuntime
        case .unavailablePublication: return .unavailablePublication
        case .invalidReply: return .invalidReply
        case .uncertain: return .uncertain
        case .nativeRefusal: return .nativeRefusal
        }
    }

    mutating func record(_ phase: Phase) {
        latestPhase = phase
        guard phases.count < Self.maximumPhaseCount else {
            phasesTruncated = true
            return
        }
        phases.append(phase)
    }

    mutating func recordNativeReply(bytes: Int) {
        nativeReplyBytes = bytes
    }

    mutating func recordDecodedReply(eventBytes: Int) {
        decodedNativeOutcome = .applied
        nativeReceiptDecoded = true
        self.eventBytes = eventBytes
    }

    mutating func recordPublication(_ returned: Bool) {
        publicationReturned = returned
    }

    /// Observe the original error before the existing uncertain conversion.
    /// The original throw/rethrow path remains owned by the client.
    mutating func recordFailure(_ error: Error) {
        guard firstFailure == nil else { return }
        firstFailurePhase = latestPhase
        firstFailure = Self.classify(error)
        if let semantic = error as? PinkhaHeartSemanticAnchorError,
           case .nativeRefusal(let outcome) = semantic {
            decodedNativeOutcome = outcome
        }
    }
}
#endif
