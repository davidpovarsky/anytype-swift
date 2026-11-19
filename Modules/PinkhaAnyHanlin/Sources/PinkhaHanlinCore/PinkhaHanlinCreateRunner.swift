import Foundation
import HanlinHostContracts
import HanlinPlatformContracts

/// Shared reservation/timeout/cancellation/late-receipt worker, extracted from
/// the original Heart host. Native wrappers supply only current UI validation,
/// single-use approval consumption and native object I/O. No SDK authority is
/// delegated to the I/O callback. A native worker is never cancelled after
/// dispatch because cancellation cannot prove rollback.
@MainActor
public final class PinkhaHanlinCreateRunner<Approval, Prepared> {
    public typealias Receipt = @MainActor @Sendable (String) async throws -> Void
    public typealias Dispatch = @MainActor (PinkhaHanlinCreatePagePlan, Prepared, @escaping Receipt) async throws -> Void
    private let journal: PinkhaHanlinWriteJournal
    private let logicalToolID: HanlinLogicalToolID
    private let validatePlan: @MainActor (PinkhaHanlinCreatePagePlan) throws -> Void
    private let validateAvailable: @MainActor () throws -> Void
    private let invalidateContext: @MainActor () -> Void
    private let prepareDispatch: @MainActor (PinkhaHanlinCreatePagePlan, Approval) throws -> Prepared
    private let dispatch: Dispatch
    private var active: Job?
    private var cancelled = Set<HanlinToolInvocationID>()
    private var receipts: [HanlinToolInvocationID: HanlinHostExecutionResult] = [:]

    @MainActor
    private final class Job {
        let plan: PinkhaHanlinCreatePagePlan
        let approval: Approval
        let dispatchDeadline: Date
        let cancellation = PinkhaHanlinRevocationFence()
        var dispatched = false
        var ended = false
        var receivedNativeResult = false
        var continuation: CheckedContinuation<HanlinHostExecutionResult, any Error>?
        var timer: Task<Void, Never>?

        init(plan: PinkhaHanlinCreatePagePlan, approval: Approval, dispatchDeadline: Date) {
            self.plan = plan; self.approval = approval; self.dispatchDeadline = dispatchDeadline
        }
        func complete(_ result: Result<HanlinHostExecutionResult, any Error>) {
            let continuation = continuation
            self.continuation = nil
            timer?.cancel(); timer = nil
            continuation?.resume(with: result)
        }
    }

    public init(journal: PinkhaHanlinWriteJournal,
                validatePlan: @escaping @MainActor (PinkhaHanlinCreatePagePlan) throws -> Void,
                validateAvailable: @escaping @MainActor () throws -> Void,
                invalidate: @escaping @MainActor () -> Void,
                prepareDispatch: @escaping @MainActor (PinkhaHanlinCreatePagePlan, Approval) throws -> Prepared,
                dispatch: @escaping Dispatch) throws {
        self.journal = journal; self.validatePlan = validatePlan
        self.validateAvailable = validateAvailable; self.invalidateContext = invalidate
        self.prepareDispatch = prepareDispatch; self.dispatch = dispatch
        self.logicalToolID = .init(providerInstanceID: try .init(validating: "anytype.host"),
                                   localToolID: try .init(validating: "create-page"))
    }

    public func execute(_ invocation: HanlinHostInvocation,
                 approval: Approval) async throws -> HanlinHostExecutionResult {
        let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation)
        try validatePlan(plan)
        guard active?.ended != false, receipts.count < 256,
              !cancelled.contains(invocation.request.id) else { throw HanlinHostError.denied }
        let job = Job(plan: plan, approval: approval, dispatchDeadline: min(plan.identity.deadline,
            Date().addingTimeInterval(Double(invocation.request.limits.timeoutMilliseconds) / 1_000)))
        active = job // One unfinished native worker per owner, including a timed-out worker.
        do { try await journal.reserve(plan.identity) }
        catch {
            job.ended = true
            throw HanlinHostError.unresolvedWrite // Sanitized; no native dispatch without a durable reservation.
        }
        let fence = job.cancellation
        let result = try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                job.continuation = continuation
                if Task.isCancelled { fence.revoke() }
                // These are deliberately unstructured: completion never joins a stalled native callback.
                Task { @MainActor in await self.run(job) }
                job.timer = Task { @MainActor in
                    do {
                        try await Task.sleep(for: .seconds(max(0, job.dispatchDeadline.timeIntervalSinceNow)))
                        fence.revoke()
                        await self.expire(job)
                    } catch {}
                }
            }
        } onCancel: {
            fence.revoke() // Synchronous fence also covers parent cancellation before queued worker entry.
            Task { @MainActor in await self.expire(job) }
        }
        // Original-scope metadata is durable/in-memory before suppressing a stale/cancelled delivery.
        try validatePlan(plan)
        if fence.isRevoked { throw HanlinHostError.cancelled }
        return result
    }

    public func cancel(_ id: HanlinToolInvocationID) async {
        if cancelled.count < 256 || cancelled.contains(id) { cancelled.insert(id) }
        else { invalidateContext() } // Exhaustion cannot silently drop a cancellation fence.
        guard let job = active, job.plan.identity.invocationID == id else { return }
        job.cancellation.revoke()
        await expire(job)
    }

    public func receipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? { receipts[id] }

    public func validateCreationAvailability() throws {
        guard active?.ended != false, receipts.count < 256 else { throw HanlinHostError.unresolvedWrite }
        try validateAvailable()
    }

    private func run(_ job: Job) async {
        defer { job.ended = true }
        do {
            // Last available host boundary after reservation's await and after MainActor queueing.
            guard !job.cancellation.isRevoked,
                  !cancelled.contains(job.plan.identity.invocationID),
                  job.dispatchDeadline > .now else { throw HanlinHostError.cancelled }
            let prepared = try prepareDispatch(job.plan, job.approval)
            job.dispatched = true
            try await dispatch(job.plan, prepared) { [self, job] objectID in
                // Native wrappers call this INSIDE their owned engine lease.
                // Original-scope journal persistence precedes lease/result delivery.
                guard !job.receivedNativeResult, !objectID.isEmpty, objectID.utf8.count <= 256 else {
                    throw HanlinHostError.resultMismatch
                }
                job.receivedNativeResult = true
                let entry = try await journal.record(.committed, identity: job.plan.identity,
                                                     createdObjectReference: objectID)
                finish(job, entry: entry)
            }
            guard job.receivedNativeResult else { throw HanlinHostError.unresolvedWrite }
        } catch {
            await retainOutcome(job, effect: job.dispatched ? .uncertain : .notDispatched)
        }
    }

    private func expire(_ job: Job) async {
        // Do not cancel/retarget/retry the native worker; it may later supply the authoritative ID.
        await retainOutcome(job, effect: job.dispatched ? .uncertain : .notDispatched)
    }

    private func retainOutcome(_ job: Job, effect: PinkhaHanlinWriteJournal.Effect) async {
        do {
            let entry = try await journal.record(effect, identity: job.plan.identity)
            finish(job, entry: entry)
        } catch {
            // The durable pre-dispatch reservation remains unresolved on storage failure. Never
            // release a business result or claim rollback/commit when the new receipt cannot be saved.
            let result = failure(job.plan.identity, effect: job.dispatched ? .uncertain : .notDispatched)
            if receipts[job.plan.identity.invocationID]?.effectState != .confirmedCommitted {
                receipts[job.plan.identity.invocationID] = result.metadataReceipt()
            }
            job.complete(.failure(HanlinHostError.unresolvedWrite))
        }
    }

    private func finish(_ job: Job, entry: PinkhaHanlinWriteJournal.Entry) {
        let identity = job.plan.identity
        let result: HanlinHostExecutionResult
        if entry.effect == .committed, entry.createdObjectReference != nil {
            // Opaque host receipt only; native object reference remains in scoped journal metadata.
            result = .init(result: .init(invocationID: identity.invocationID,
                logicalToolID: logicalToolID, outcome: .completed([]), completedAt: .now),
                effectState: .confirmedCommitted, context: identity.session.context,
                reconciliationReference: identity.key)
        } else {
            result = failure(identity, effect: entry.effect == .notDispatched ? .notDispatched : .uncertain)
        }
        // This may refine the ORIGINAL receipt after an early timeout, while completion stays single-shot.
        receipts[identity.invocationID] = result.metadataReceipt()
        job.complete(.success(result))
    }

    private func failure(_ identity: PinkhaHanlinWriteIdentity, effect: HanlinHostEffectState) -> HanlinHostExecutionResult {
        .init(result: .init(invocationID: identity.invocationID, logicalToolID: logicalToolID,
            outcome: .failed(.init(code: .operationUnavailable,
                userMessage: "Creation unavailable; reconcile the original scope before retrying")), completedAt: .now),
            effectState: effect, context: identity.session.context, reconciliationReference: identity.key)
    }

}
