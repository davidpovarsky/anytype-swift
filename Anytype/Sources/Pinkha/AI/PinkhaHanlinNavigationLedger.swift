import Foundation
import HanlinHostContracts

/// Bounded presentation metadata only. An entry in this queue is never a UI mount acknowledgement.
@MainActor
final class PinkhaHanlinNavigationLedger {
    private let context: HanlinHostContext
    private var requests: [UUID: HanlinHostDestination] = [:]
    private var acknowledgements: [UUID: HanlinHostNavigationResult] = [:]

    init(context: HanlinHostContext) { self.context = context }

    func enqueue(_ destination: HanlinHostDestination) throws -> Bool {
        guard destination.context == context else { throw HanlinHostError.staleContext }
        if let previous = requests[destination.requestID] {
            guard previous == destination else { throw HanlinHostError.resultMismatch }
            return false
        }
        guard requests.count < 128 else { throw HanlinHostError.outputLimitExceeded }
        requests[destination.requestID] = destination
        return true
    }

    func result(for destination: HanlinHostDestination) throws -> HanlinHostNavigationResult {
        guard destination.context == context, requests[destination.requestID] == destination else {
            throw HanlinHostError.resultMismatch
        }
        return acknowledgements[destination.requestID] ?? .queued(requestID: destination.requestID, context: context)
    }

    /// Called by NativeAccess only AFTER its real controller/document/scene mount checks.
    func acknowledge(_ result: HanlinHostNavigationResult, for destination: HanlinHostDestination) throws {
        guard destination.context == context, requests[destination.requestID] == destination,
              result.presentationAcknowledged else { throw HanlinHostError.resultMismatch }
        try result.validate(for: destination)
        acknowledgements[destination.requestID] = result
    }
}
