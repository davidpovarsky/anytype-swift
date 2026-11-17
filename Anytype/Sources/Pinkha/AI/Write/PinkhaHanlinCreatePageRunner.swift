import Foundation
import Factory
import Services
import ProtobufMessages
import HanlinHostContracts
import HanlinPlatformContracts

/// A host-private write component, NOT installed in the accepted read-only SDK adapter/catalog.
/// A future composition owner must obtain actual confirmation and call this with the SAME invocation.
/// The native worker is never cancelled after dispatch: native cancellation cannot prove rollback.
@MainActor
final class PinkhaHanlinCreatePageRunner {
    private let context: PinkhaHanlinCreatePageContext
    private let journal: PinkhaHanlinWriteJournal
    private let logicalToolID: HanlinLogicalToolID
    private let actions = Container.shared.objectActionsService()
    private var active: Job?
    private var cancelled = Set<HanlinToolInvocationID>()
    private var receipts: [HanlinToolInvocationID: HanlinHostExecutionResult] = [:]

    @MainActor
    private final class Job {
        let plan: PinkhaHanlinCreatePagePlan
        let approval: PinkhaHanlinCreateApproval
        let dispatchDeadline: Date
        let cancellation = PinkhaHanlinRevocationFence()
        var dispatched = false
        var ended = false
        var continuation: CheckedContinuation<HanlinHostExecutionResult, any Error>?
        var timer: Task<Void, Never>?

        init(plan: PinkhaHanlinCreatePagePlan, approval: PinkhaHanlinCreateApproval, dispatchDeadline: Date) {
            self.plan = plan; self.approval = approval; self.dispatchDeadline = dispatchDeadline
        }
        func complete(_ result: Result<HanlinHostExecutionResult, any Error>) {
            let continuation = continuation
            self.continuation = nil
            timer?.cancel(); timer = nil
            continuation?.resume(with: result)
        }
    }

    init(context: PinkhaHanlinCreatePageContext, journal: PinkhaHanlinWriteJournal) throws {
        self.context = context; self.journal = journal
        self.logicalToolID = .init(providerInstanceID: try .init(validating: "anytype.host"),
                                   localToolID: try .init(validating: "create-page"))
    }

    func execute(_ invocation: HanlinHostInvocation,
                 approval: PinkhaHanlinCreateApproval) async throws -> HanlinHostExecutionResult {
        let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation)
        _ = try context.validate(plan)
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
        _ = try context.validate(plan)
        if fence.isRevoked { throw HanlinHostError.cancelled }
        return result
    }

    func cancel(_ id: HanlinToolInvocationID) async {
        if cancelled.count < 256 || cancelled.contains(id) { cancelled.insert(id) }
        else { context.invalidate() } // Exhaustion cannot silently drop a cancellation fence.
        guard let job = active, job.plan.identity.invocationID == id else { return }
        job.cancellation.revoke()
        await expire(job)
    }

    func receipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? { receipts[id] }

    func validateCreationAvailability() throws {
        guard active?.ended != false, receipts.count < 256 else { throw HanlinHostError.unresolvedWrite }
        _ = try context.validateCreationAvailability()
    }

    private func run(_ job: Job) async {
        defer { job.ended = true }
        do {
            // Last available host boundary after reservation's await and after MainActor queueing.
            guard !job.cancellation.isRevoked,
                  !cancelled.contains(job.plan.identity.invocationID),
                  job.dispatchDeadline > .now,
                  InvocationSettings.handler?.isLogEnabled == false else { throw HanlinHostError.cancelled }
            let type = try job.approval.consume(for: job.plan, in: context)
            job.dispatched = true
            let original = job.plan.identity.session.context
            let details = try await actions.createObject(name: job.plan.title, typeUniqueKey: type.uniqueKey,
                shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                spaceId: original.namespace.space, origin: .none, templateId: nil,
                createdInContext: "", createdInContextRef: "", additionalDetails: [])
            // The returned ID is native-authoritative. Never derive/find a created ID from the title.
            guard !details.id.isEmpty, details.id.utf8.count <= 256,
                  details.spaceId.utf8.elementsEqual(original.namespace.space.utf8),
                  details.type.utf8.elementsEqual(type.id.utf8),
                  details.name.utf8.elementsEqual(job.plan.title.utf8),
                  details.resolvedLayoutValue == .basic,
                  !details.isDeleted, !details.isArchived, !details.isTemplate,
                  !details.isHidden, !details.isReadonly else { throw HanlinHostError.resultMismatch }
            let entry = try await journal.record(.committed, identity: job.plan.identity,
                                                 createdObjectReference: details.id)
            finish(job, entry: entry)
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
