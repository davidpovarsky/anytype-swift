import Foundation
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore
import PinkhaAnyEngine
import PinkhaAnyHost

@MainActor
final class AnyHanlinWriteApproval {
    let identity: PinkhaHanlinWriteIdentity
    let eligibility: AnyHanlinPageEligibility
    private var consumed = false
    init(identity: PinkhaHanlinWriteIdentity, eligibility: AnyHanlinPageEligibility) {
        self.identity = identity; self.eligibility = eligibility
    }
    func consume<Plan: PinkhaHanlinNativeWritePlan>(_ plan: Plan) throws -> AnyHanlinPageEligibility {
        guard !consumed, identity == plan.identity else { throw HanlinHostError.denied }
        consumed = true
        return eligibility
    }
}

/// One original live scope, mounted consent owner and prompt decision for both
/// native write routes. The parser and model cannot construct an approval.
@MainActor
final class AnyHanlinWriteContext {
    let access: AnyHanlinNativeAccess
    let native: AnyApplicationSession
    let creator: AnyNativeObjectCreator
    let authority: AnyHanlinCreationAuthority
    private weak var owner: (any AnyHanlinCreationPresentationOwner)?
    private weak var presentation: (any PinkhaHanlinOwnedPresentation)?
    private var decision: PinkhaHanlinReadConsentDecision?
    private var pendingID: HanlinToolInvocationID?
    var session: HanlinHostSession { access.session }

    init(access: AnyHanlinNativeAccess, native: AnyApplicationSession,
         creator: AnyNativeObjectCreator, authority: AnyHanlinCreationAuthority,
         owner: any AnyHanlinCreationPresentationOwner) throws {
        guard native.workspace == creator.workspace, native.workspace == authority.workspace else {
            throw HanlinHostError.invalidContext
        }
        self.access = access; self.native = native; self.creator = creator
        self.authority = authority; self.owner = owner
    }

    func attach(_ presentation: any PinkhaHanlinOwnedPresentation) { self.presentation = presentation }

    var missingInstallation: [PinkhaHanlinWriteInstallationRequirement] {
        guard let presentation, PinkhaHanlinAccountOwner.shared.owns(presentation),
              presentation.session == session,
              let owner, (try? owner.validateSDKPresentation(for: session)) != nil else {
            return PinkhaHanlinWriteInstallationRequirement.missing
        }
        guard PinkhaHanlinAccountOwner.shared.isAvailable(namespace: session.context.namespace) else {
            return [.accountRemovalAndMetadataRetentionHook]
        }
        return []
    }

    func observeInvalidation(_ callback: @escaping @MainActor () -> Void) {
        access.observeInvalidation(callback)
    }

    func validateConfirmationAvailability() throws {
        try validateAvailability()
        guard decision == nil else { throw HanlinHostError.denied }
    }

    func inspectEligibility() async throws -> AnyHanlinPageEligibility {
        let authority = authority
        let result = try await native.perform { lease in try await authority.inspect(lease: lease) }
        try validateAvailability()
        return result
    }

    func validateAvailability() throws {
        try Task.checkCancellation()
        guard missingInstallation.isEmpty, let owner else { throw HanlinHostError.denied }
        try access.validate(session.context)
        try owner.validateSDKPresentation(for: session)
    }

    func validate<Plan: PinkhaHanlinNativeWritePlan>(_ plan: Plan) throws {
        try validateNativeIdentity(plan.identity)
    }

    /// The deadline exception is only for original-scope late READS. Revoked
    /// account, scene, SDK presentation, Task or engine authority still denies.
    func validateNativeIdentity(_ identity: PinkhaHanlinWriteIdentity,
                                requireUnexpired: Bool = true) throws {
        try validateAvailability()
        guard identity.session == session, !requireUnexpired || identity.deadline > .now else {
            throw HanlinHostError.staleContext
        }
    }

    func requestConfirmation(_ plan: PinkhaHanlinCreatePagePlan,
        eligibility: AnyHanlinPageEligibility) async throws -> AnyHanlinWriteApproval {
        try await requestConfirmation(plan, eligibility: eligibility) { owner, answer in
            try owner.presentCreatePageConfirmation(.init(session: self.session,
                invocationID: plan.identity.invocationID.rawValue, title: plan.title,
                spaceID: self.session.context.namespace.space), answer: answer)
        }
    }

    func requestConfirmation(_ plan: PinkhaHanlinSaveMessagePlan,
        eligibility: AnyHanlinPageEligibility) async throws -> AnyHanlinWriteApproval {
        try await requestConfirmation(plan, eligibility: eligibility) { owner, answer in
            guard let owner = owner as? any AnyHanlinSaveMessagePresentationOwner else {
                throw HanlinHostError.denied
            }
            try owner.presentSaveMessageConfirmation(.init(session: self.session,
                invocationID: plan.identity.invocationID.rawValue, title: plan.title,
                markdown: plan.markdown, spaceID: self.session.context.namespace.space), answer: answer)
        }
    }

    private func requestConfirmation<Plan: PinkhaHanlinNativeWritePlan>(_ plan: Plan,
        eligibility: AnyHanlinPageEligibility,
        present: @MainActor (any AnyHanlinCreationPresentationOwner,
            @escaping @MainActor (Bool) -> Void) throws -> Void) async throws -> AnyHanlinWriteApproval {
        try validate(plan)
        guard decision == nil, let owner else { throw HanlinHostError.denied }
        let current = PinkhaHanlinReadConsentDecision()
        let confirmationCancellation = PinkhaHanlinRevocationFence()
        let cancelPrompt: @MainActor @Sendable () -> Void = { [weak self] in
            self?.cancelConfirmation(plan.identity.invocationID)
        }
        decision = current; pendingID = plan.identity.invocationID
        let timeout = Task { @MainActor [weak self, weak current] in
            do {
                try await Task.sleep(for: .seconds(max(0, plan.identity.deadline.timeIntervalSinceNow)))
                guard let self, let current, self.decision === current else { return }
                current.resolve(false)
                self.owner?.dismissPendingPrompts()
            } catch {}
        }
        defer {
            timeout.cancel()
            if decision === current { decision = nil; pendingID = nil }
        }
        let allowed: Bool = await withTaskCancellationHandler {
            await withCheckedContinuation { continuation in
                guard !Task.isCancelled, current.begin({ continuation.resume(returning: $0) }) else {
                    continuation.resume(returning: false); return
                }
                do {
                    try present(owner) { [weak self, weak current] answer in
                        guard let self, let current, self.decision === current else { return }
                        if answer {
                            current.resolveAllow {
                                guard !confirmationCancellation.isRevoked else { throw HanlinHostError.cancelled }
                                try self.validate(plan)
                            }
                        }
                        else { current.resolve(false) }
                    }
                } catch { current.resolve(false) }
            }
        } onCancel: {
            // Synchronous fence defeats a queued Allow before MainActor cleanup.
            confirmationCancellation.revoke()
            Task { @MainActor in cancelPrompt() }
        }
        guard !confirmationCancellation.isRevoked else { throw HanlinHostError.cancelled }
        try validate(plan)
        guard allowed, current.authorized else { throw HanlinHostError.denied }
        return .init(identity: plan.identity, eligibility: eligibility)
    }

    func cancelConfirmation(_ id: HanlinToolInvocationID) {
        guard pendingID == id else { return }
        decision?.revoke()
        owner?.dismissPendingPrompts()
    }

    func invalidate() {
        decision?.revoke(); owner?.dismissPendingPrompts(); access.invalidate()
    }
}

/// Both concrete runners use the original Core worker. This protocol shares
/// host readiness and drain wiring; it cannot replace native persistence.
@MainActor
protocol AnyHanlinWriteRunning: AnyObject {
    func execute(_ invocation: HanlinHostInvocation,
                 approval: AnyHanlinWriteApproval) async throws -> HanlinHostExecutionResult
    func cancel(_ id: HanlinToolInvocationID) async
    func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult?
    func receipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult?
    func validateCreationAvailability() throws
}

typealias AnyHanlinCreateBinding = AnyHanlinWriteBinding<PinkhaHanlinCreatePagePlan, AnyHanlinCreatePageRunner>
typealias AnyHanlinSaveBinding = AnyHanlinWriteBinding<PinkhaHanlinSaveMessagePlan, AnyHanlinSaveMessageRunner>

@MainActor
final class AnyHanlinWriteBinding<Plan: PinkhaHanlinNativeWritePlan,
    Runner: AnyHanlinWriteRunning>: PinkhaHanlinWriteBinding {
    private let context: AnyHanlinWriteContext
    private let tool: HanlinHostTool
    private let requestConfirmation: @MainActor (Plan, AnyHanlinPageEligibility) async throws -> AnyHanlinWriteApproval
    private let makeRunner: @MainActor (PinkhaHanlinWriteJournal) throws -> Runner
    private var journal: PinkhaHanlinWriteJournal?
    private var runner: Runner?
    private var opening = false
    private let preflight = PinkhaHanlinWritePreflight()

    init(context: AnyHanlinWriteContext, tool: HanlinHostTool,
         requestConfirmation: @escaping @MainActor (Plan, AnyHanlinPageEligibility) async throws -> AnyHanlinWriteApproval,
         makeRunner: @escaping @MainActor (PinkhaHanlinWriteJournal) throws -> Runner) {
        self.context = context; self.tool = tool
        self.requestConfirmation = requestConfirmation; self.makeRunner = makeRunner
    }
    func attach(_ presentation: any PinkhaHanlinOwnedPresentation) { context.attach(presentation) }
    var missingInstallation: [PinkhaHanlinWriteInstallationRequirement] { context.missingInstallation }
    func observeInvalidation(_ callback: @escaping @MainActor () -> Void) { context.observeInvalidation(callback) }

    func catalogTool() async throws -> HanlinHostTool? {
        guard missingInstallation.isEmpty else { return nil }
        do { _ = try await prepareOwner(); return tool }
        catch { try Task.checkCancellation(); return nil }
    }

    func execute(_ invocation: HanlinHostInvocation, cancellation: PinkhaHanlinRevocationFence,
                 progress: @escaping HanlinHostProgressHandler) async throws -> HanlinHostExecutionResult {
        try await preflight.execute(invocation, prepare: {
            let plan = try Plan(invocation: invocation)
            let eligibility = try await prepareOwner()
            guard let journal, let runner else { throw HanlinHostError.denied }
            try check(plan, cancellation: cancellation)
            await progress(try .init(invocationID: invocation.request.id, sequence: 1,
                timestamp: .now, fractionCompleted: 0, message: "Awaiting confirmation"))
            try check(plan, cancellation: cancellation)
            let approval = try await requestConfirmation(plan, eligibility)
            try check(plan, cancellation: cancellation)
            let current = try await context.inspectEligibility()
            guard current == eligibility else { throw HanlinHostError.staleContext }
            try await journal.validateCreationAvailability(namespace: context.session.context.namespace)
            try check(plan, cancellation: cancellation)
            return (runner, approval)
        }, dispatch: { prepared in try await prepared.0.execute(invocation, approval: prepared.1) })
    }

    private func prepareOwner() async throws -> AnyHanlinPageEligibility {
        try context.validateConfirmationAvailability()
        let eligibility = try await context.inspectEligibility()
        try context.validateAvailability()
        if journal == nil {
            guard !opening else { throw HanlinHostError.denied }
            opening = true
            defer { opening = false }
            let opened = try await PinkhaHanlinAccountOwner.shared.journal(for: context.session.context.namespace)
            try context.validateAvailability()
            try await opened.validateCreationAvailability(namespace: context.session.context.namespace)
            try context.validateAvailability()
            let runner = try makeRunner(opened)
            self.journal = opened; self.runner = runner
        }
        guard let journal, let runner else { throw HanlinHostError.denied }
        try runner.validateCreationAvailability()
        try await journal.validateCreationAvailability(namespace: context.session.context.namespace)
        try context.validateAvailability()
        try runner.validateCreationAvailability()
        return eligibility
    }

    private func check(_ plan: Plan, cancellation: PinkhaHanlinRevocationFence) throws {
        guard !cancellation.isRevoked else { throw HanlinHostError.cancelled }
        try context.validate(plan)
    }
    func cancel(_ id: HanlinToolInvocationID) async {
        context.cancelConfirmation(id)
        await runner?.cancel(id)
    }
    func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult? {
        let retained = await runner?.drainCancelledInvocation(id)
        return retained?.metadataReceipt() ?? preflight.receipt(for: id)?.metadataReceipt()
    }
    func invalidate() { context.invalidate() }
    func requestContextReadConsent() async throws { try await context.access.requestContextReadConsent() }
    func metadataReceipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? {
        preflight.receipt(for: id) ?? runner?.receipt(for: id)?.metadataReceipt()
    }
}

extension AnyHanlinWriteBinding where Plan == PinkhaHanlinCreatePagePlan, Runner == AnyHanlinCreatePageRunner {
    convenience init(context: AnyHanlinWriteContext) throws {
        self.init(context: context, tool: try PinkhaHanlinCreatePageTool.make(),
            requestConfirmation: { try await context.requestConfirmation($0, eligibility: $1) },
            makeRunner: { try AnyHanlinCreatePageRunner(context: context, journal: $0) })
    }
    convenience init(access: AnyHanlinNativeAccess, native: AnyApplicationSession,
        creator: AnyNativeObjectCreator, authority: AnyHanlinCreationAuthority,
        owner: any AnyHanlinCreationPresentationOwner) throws {
        try self.init(context: .init(access: access, native: native, creator: creator,
                                    authority: authority, owner: owner))
    }
    static func mutationID(_ identity: PinkhaHanlinWriteIdentity) -> String {
        // This immutable operation identity can never mint a new native retry ID.
        String(PinkhaHanlinCreatePagePlan.digest(
            Data(("pinkha-any-hanlin-create/v1" + "\0" + identity.key).utf8)).prefix(32))
    }
}

extension AnyHanlinWriteBinding where Plan == PinkhaHanlinSaveMessagePlan, Runner == AnyHanlinSaveMessageRunner {
    convenience init(context: AnyHanlinWriteContext, documents: AnyEditorDocumentStore,
                     services: AnyHanlinSaveMessageServices) throws {
        self.init(context: context, tool: try PinkhaHanlinSaveMessageTool.make(),
            requestConfirmation: { try await context.requestConfirmation($0, eligibility: $1) },
            makeRunner: { try AnyHanlinSaveMessageRunner(context: context, journal: $0,
                documents: documents, services: services) })
    }
}

extension AnyHanlinSaveMessageRunner: AnyHanlinWriteRunning {}

private struct AnyHanlinPreparedCreation: Sendable {
    let intent: AnyNativeObjectCreationIntent
    let eligibility: AnyHanlinPageEligibility
}

/// The original title-only native operation, moved intact behind the same
/// context. Known incomplete roots remain journaled before its lease drains.
@MainActor
final class AnyHanlinCreatePageRunner: AnyHanlinWriteRunning {
    private let core: PinkhaHanlinCreateRunner<AnyHanlinWriteApproval, AnyHanlinPreparedCreation>
    init(context: AnyHanlinWriteContext, journal: PinkhaHanlinWriteJournal) throws {
        let native = context.native, creator = context.creator, authority = context.authority
        core = try PinkhaHanlinCreateRunner<AnyHanlinWriteApproval, AnyHanlinPreparedCreation>(
            journal: journal, validatePlan: { plan in
                try context.validate(plan)
            },
            validateAvailable: {
                try context.validateAvailability()
            },
            invalidate: { context.invalidate() },
            prepareDispatch: { plan, approval in
                try context.validate(plan)
                let eligibility = try approval.consume(plan)
                let mutation = AnyHanlinCreateBinding.mutationID(plan.identity)
                let intent = try AnyNativeObjectCreationIntent(workspace: native.workspace,
                    mutationID: mutation, typeID: "page", collections: [],
                    initialProperties: .object(["any": .object(["name": .string(plan.title)])]))
                return AnyHanlinPreparedCreation(intent: intent, eligibility: eligibility)
            },
            dispatch: { plan, prepared, receive in
                // The shared worker owns this operation independently of the
                // foreground SDK waiter. Session drain awaits native receipt
                // plus original Hanlin journal commit, even after cancellation.
                _ = try await native.perform { lease in
                    do {
                        return try await creator.ensureObject(prepared.intent, authorize: {
                            try await lease.validate()
                            let current = try await authority.inspect(lease: lease)
                            guard current == prepared.eligibility else { throw HanlinHostError.staleContext }
                            try await MainActor.run { try context.validate(plan) }
                        }, onNativeConfirmed: { id in
                            try await receive(id)
                        })
                    } catch {
                        // Preserve a known native root BEFORE this original
                        // lease can drain. Partial/bootstrap/readback failure
                        // must never call the confirmed receipt callback.
                        let knownID: String?
                        if let failure = error as? AnyNativeCreationError,
                           case .createdObjectIncomplete(let id) = failure {
                            knownID = id
                        } else {
                            knownID = try await creator.recordedObjectID(for: prepared.intent)
                        }
                        if let knownID {
                            try await journal.recordKnownIncompleteObject(knownID, identity: plan.identity)
                        }
                        throw error
                    }
                }
            })
    }
    func execute(_ invocation: HanlinHostInvocation,
                 approval: AnyHanlinWriteApproval) async throws -> HanlinHostExecutionResult {
        try await core.execute(invocation, approval: approval)
    }
    func cancel(_ id: HanlinToolInvocationID) async { await core.cancel(id) }
    func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult? {
        await core.drainCancelledInvocation(id)
    }
    func receipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? { core.receipt(for: id) }
    func validateCreationAvailability() throws { try core.validateCreationAvailability() }
}
