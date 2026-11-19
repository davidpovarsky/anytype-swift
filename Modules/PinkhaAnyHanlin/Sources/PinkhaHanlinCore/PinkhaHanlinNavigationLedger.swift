import Foundation
import HanlinHostContracts

/// Bounded presentation metadata only. An entry in this queue is never a UI mount acknowledgement.
@MainActor
public final class PinkhaHanlinNavigationLedger {
    private let context: HanlinHostContext
    private var requests: [UUID: HanlinHostDestination] = [:]
    private var acknowledgements: [UUID: HanlinHostNavigationResult] = [:]
    private var handoffs = Set<UUID>()

    public init(context: HanlinHostContext) { self.context = context }

    public func enqueue(_ destination: HanlinHostDestination) throws -> Bool {
        guard destination.context == context else { throw HanlinHostError.staleContext }
        if let previous = requests[destination.requestID] {
            guard Self.exact(previous, destination) else { throw HanlinHostError.resultMismatch }
            return false
        }
        guard requests.count < 128 else { throw HanlinHostError.outputLimitExceeded }
        requests[destination.requestID] = destination
        return true
    }

    public func result(for destination: HanlinHostDestination) throws -> HanlinHostNavigationResult {
        guard destination.context == context, let request = requests[destination.requestID],
              Self.exact(request, destination) else {
            throw HanlinHostError.resultMismatch
        }
        return acknowledgements[destination.requestID] ?? .queued(requestID: destination.requestID, context: context)
    }

    /// Called by NativeAccess only AFTER its real controller/document/scene mount checks.
    public func acknowledge(_ result: HanlinHostNavigationResult, for destination: HanlinHostDestination) throws {
        guard destination.context == context, let request = requests[destination.requestID],
              Self.exact(request, destination),
              result.presentationAcknowledged else { throw HanlinHostError.resultMismatch }
        try result.validate(for: destination)
        acknowledgements[destination.requestID] = result
    }

    /// The original UI owner consumes a queued identity once, before dismissing Chat.
    /// The callback must independently validate the real mounted target; it grants no host access.
    public func makeHandoff(for destination: HanlinHostDestination, timeout: Duration = .seconds(10),
                     now: @escaping @MainActor () -> ContinuousClock.Instant = { ContinuousClock.now },
                     validateMounted: @escaping @MainActor () throws -> HanlinHostNavigationResult) throws
        -> PinkhaHanlinNavigationHandoff {
        guard case .queued = try result(for: destination),
              handoffs.insert(destination.requestID).inserted else { throw HanlinHostError.resultMismatch }
        return PinkhaHanlinNavigationHandoff(destination: destination, timeout: timeout, now: now,
            validateMounted: validateMounted, recordAcknowledgement: { [self] result in
                try acknowledge(result, for: destination)
            })
    }

    private static func exact(_ left: HanlinHostDestination, _ right: HanlinHostDestination) -> Bool {
        left.requestID == right.requestID && left.context == right.context
            && left.objectReference.utf8.elementsEqual(right.objectReference.utf8)
            && left.blockReference.map({ Data($0.utf8) }) == right.blockReference.map({ Data($0.utf8) })
    }
}

/// A short-lived native UI receipt, separate from the SDK session that closes before dismissal.
/// It can record metadata once; it cannot read, write, reopen Chat or revive a revoked session.
@MainActor
public final class PinkhaHanlinNavigationHandoff {
    public enum State: Equatable { case awaitingMount, mounted, cancelled }

    public let destination: HanlinHostDestination
    public private(set) var state = State.awaitingMount
    public private(set) var receipt: HanlinHostNavigationResult?
    private let now: @MainActor () -> ContinuousClock.Instant
    private let deadline: ContinuousClock.Instant
    private var validateMounted: (@MainActor () throws -> HanlinHostNavigationResult)?
    private var recordAcknowledgement: (@MainActor (HanlinHostNavigationResult) throws -> Void)?
    private var outcome: Result<HanlinHostNavigationResult, Error>?
    private var expiry: Task<Void, Never>?

    fileprivate init(destination: HanlinHostDestination, timeout: Duration,
                     now: @escaping @MainActor () -> ContinuousClock.Instant,
                     validateMounted: @escaping @MainActor () throws -> HanlinHostNavigationResult,
                     recordAcknowledgement: @escaping @MainActor (HanlinHostNavigationResult) throws -> Void) {
        self.destination = destination
        self.now = now
        self.deadline = now().advanced(by: timeout)
        self.validateMounted = validateMounted
        self.recordAcknowledgement = recordAcknowledgement
        expiry = Task { @MainActor [weak self] in
            do { try await Task.sleep(for: timeout) } catch { return }
            self?.cancel()
        }
    }

    deinit { expiry?.cancel() }

    /// UIKit's completion only triggers this check. It is not itself proof of presentation.
    public func acknowledgeMounted() throws -> HanlinHostNavigationResult {
        if let outcome { return try outcome.get() }
        guard now() < deadline, let validateMounted else {
            cancel()
            throw HanlinHostError.staleContext
        }
        // Consume before invoking native validation, including its error path.
        self.validateMounted = nil
        expiry?.cancel()
        expiry = nil
        do {
            let result = try validateMounted()
            if let outcome { return try outcome.get() } // A reentrant cancellation cannot be overwritten.
            guard now() < deadline else { throw HanlinHostError.staleContext }
            guard result.presentationAcknowledged else { throw HanlinHostError.resultMismatch }
            try result.validate(for: destination)
            guard let recordAcknowledgement else { throw HanlinHostError.staleContext }
            self.recordAcknowledgement = nil
            try recordAcknowledgement(result)
            receipt = result
            state = .mounted
            outcome = .success(result)
            return result
        } catch {
            recordAcknowledgement = nil
            state = .cancelled
            outcome = .failure(error)
            throw error
        }
    }

    public func cancel() {
        guard outcome == nil else { return }
        validateMounted = nil
        recordAcknowledgement = nil
        expiry?.cancel()
        expiry = nil
        state = .cancelled
        outcome = .failure(HanlinHostError.staleContext)
    }
}
