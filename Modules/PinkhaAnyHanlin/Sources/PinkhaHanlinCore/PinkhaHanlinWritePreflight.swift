import Foundation
import HanlinHostContracts
import HanlinPlatformContracts

@MainActor
public final class PinkhaHanlinWritePreflight {
    public init() {}
    private var receipts: [HanlinToolInvocationID: HanlinHostExecutionResult] = [:]

    public func execute<Preparation>(
        _ invocation: HanlinHostInvocation,
        prepare: @MainActor () async throws -> Preparation,
        dispatch: @MainActor (Preparation) async throws -> HanlinHostExecutionResult
    ) async throws -> HanlinHostExecutionResult {
        let prepared: Preparation
        do {
            prepared = try await prepare()
        } catch {
            let result = HanlinHostExecutionResult(
                result: .init(invocationID: invocation.request.id, logicalToolID: invocation.request.logicalToolID,
                    outcome: .failed(.init(code: safeCode(error),
                        userMessage: "Host operation unavailable or no longer authorized")), completedAt: .now),
                effectState: .notDispatched, context: invocation.session.context)
            receipts[invocation.request.id] = result.metadataReceipt()
            return result
        }
        return try await dispatch(prepared)
    }

    public func receipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? {
        receipts[id]
    }

    private func safeCode(_ error: Error) -> HanlinErrorCode {
        switch error {
        case is CancellationError, HanlinHostError.cancelled: .cancelled
        case HanlinHostError.deadlineExceeded: .timedOut
        case HanlinHostError.invalidArguments, PinkhaHanlinWriteError.invalidPlan: .invalidArguments
        case HanlinHostError.outputLimitExceeded: .resourceLimitExceeded
        case HanlinHostError.staleContext, HanlinHostError.denied: .permissionDenied
        default: .operationUnavailable
        }
    }
}
