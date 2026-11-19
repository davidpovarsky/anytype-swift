import Foundation
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore
import PinkhaAnyEngine
import PinkhaAnyHost

@MainActor
private final class AnyHanlinCreateApproval {
    let identity: PinkhaHanlinWriteIdentity
    let eligibility: AnyHanlinPageEligibility
    private var consumed = false
    init(identity: PinkhaHanlinWriteIdentity, eligibility: AnyHanlinPageEligibility) {
        self.identity = identity; self.eligibility = eligibility
    }
    func consume(_ plan: PinkhaHanlinCreatePagePlan) throws -> AnyHanlinPageEligibility {
        guard !consumed, identity == plan.identity else { throw HanlinHostError.denied }
        consumed = true
        return eligibility
    }
}

private struct AnyHanlinPreparedCreation: Sendable {
    let intent: AnyNativeObjectCreationIntent
    let eligibility: AnyHanlinPageEligibility
}

@MainActor
final class AnyHanlinCreateBinding: PinkhaHanlinWriteBinding {
    private let access: AnyHanlinNativeAccess
    private let native: AnyApplicationSession
    private let creator: AnyNativeObjectCreator
    private let authority: AnyHanlinCreationAuthority
    private weak var owner: (any AnyHanlinCreationPresentationOwner)?
    private weak var presentation: (any PinkhaHanlinOwnedPresentation)?
    private var journal: PinkhaHanlinWriteJournal?
    private var runner: PinkhaHanlinCreateRunner<AnyHanlinCreateApproval, AnyHanlinPreparedCreation>?
    private let preflight = PinkhaHanlinWritePreflight()
    private let tool: HanlinHostTool
    private var opening = false
    private var decision: PinkhaHanlinReadConsentDecision?
    private var pendingID: HanlinToolInvocationID?

    init(access: AnyHanlinNativeAccess, native: AnyApplicationSession,
         creator: AnyNativeObjectCreator, authority: AnyHanlinCreationAuthority,
         owner: any AnyHanlinCreationPresentationOwner) throws {
        guard native.workspace == creator.workspace, native.workspace == authority.workspace else {
            throw HanlinHostError.invalidContext
        }
        self.access = access; self.native = native; self.creator = creator
        self.authority = authority; self.owner = owner
        self.tool = try PinkhaHanlinCreatePageTool.make()
    }

    func attach(_ presentation: any PinkhaHanlinOwnedPresentation) { self.presentation = presentation }

    var missingInstallation: [PinkhaHanlinWriteInstallationRequirement] {
        guard let presentation, PinkhaHanlinAccountOwner.shared.owns(presentation),
              presentation.session == access.session,
              let owner, (try? owner.validateSDKPresentation(for: access.session)) != nil else {
            return PinkhaHanlinWriteInstallationRequirement.missing
        }
        guard PinkhaHanlinAccountOwner.shared.isAvailable(account: access.session.context.namespace.account) else {
            return [.accountRemovalAndMetadataRetentionHook]
        }
        return []
    }

    func observeInvalidation(_ callback: @escaping @MainActor () -> Void) {
        access.observeInvalidation(callback)
    }

    func catalogTool() async throws -> HanlinHostTool? {
        guard missingInstallation.isEmpty else { return nil }
        do {
            _ = try await prepareOwner()
            return tool
        } catch {
            try Task.checkCancellation()
            return nil
        }
    }

    func execute(_ invocation: HanlinHostInvocation, cancellation: PinkhaHanlinRevocationFence,
                 progress: @escaping HanlinHostProgressHandler) async throws -> HanlinHostExecutionResult {
        try await preflight.execute(invocation, prepare: {
            let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation)
            let eligibility = try await prepareOwner()
            guard let journal, let runner else { throw HanlinHostError.denied }
            try check(plan, cancellation: cancellation)
            await progress(try .init(invocationID: invocation.request.id, sequence: 1,
                timestamp: .now, fractionCompleted: 0, message: "Awaiting confirmation"))
            try check(plan, cancellation: cancellation)
            let approval = try await requestConfirmation(plan, eligibility: eligibility)
            try check(plan, cancellation: cancellation)
            let current = try await inspectEligibility()
            guard current == eligibility else { throw HanlinHostError.staleContext }
            try await journal.validateCreationAvailability(namespace: access.session.context.namespace)
            try check(plan, cancellation: cancellation)
            return (runner, approval)
        }, dispatch: { prepared in
            try await prepared.0.execute(invocation, approval: prepared.1)
        })
    }

    private func prepareOwner() async throws -> AnyHanlinPageEligibility {
        try validateAvailability()
        guard decision == nil else { throw HanlinHostError.denied }
        let eligibility = try await inspectEligibility()
        try validateAvailability()
        if journal == nil {
            guard !opening else { throw HanlinHostError.denied }
            opening = true
            defer { opening = false }
            let opened = try await PinkhaHanlinAccountOwner.shared.journal(for: access.session.context.namespace)
            try validateAvailability()
            try await opened.validateCreationAvailability(namespace: access.session.context.namespace)
            try validateAvailability()
            let native = native, creator = creator, authority = authority
            let worker = try PinkhaHanlinCreateRunner<AnyHanlinCreateApproval, AnyHanlinPreparedCreation>(
                journal: opened, validatePlan: { [weak self] plan in
                    guard let self else { throw HanlinHostError.staleContext }
                    try self.validate(plan)
                },
                validateAvailable: { [weak self] in
                    guard let self else { throw HanlinHostError.staleContext }
                    try self.validateAvailability()
                },
                invalidate: { [weak self] in self?.invalidate() },
                prepareDispatch: { [weak self] plan, approval in
                    guard let self else { throw HanlinHostError.staleContext }
                    try self.validate(plan)
                    let eligibility = try approval.consume(plan)
                    let mutation = Self.mutationID(plan.identity)
                    let intent = try AnyNativeObjectCreationIntent(workspace: native.workspace,
                        mutationID: mutation, typeID: "page", collections: [],
                        initialProperties: .object(["any": .object(["name": .string(plan.title)])]))
                    return AnyHanlinPreparedCreation(intent: intent, eligibility: eligibility)
                },
                dispatch: { [weak self] plan, prepared, receive in
                    guard let self else { throw HanlinHostError.staleContext }
                    // The shared worker owns this operation independently of the
                    // foreground SDK waiter. Session drain awaits native receipt
                    // plus original Hanlin journal commit, even after cancellation.
                    _ = try await native.perform { lease in
                        do {
                            return try await creator.ensureObject(prepared.intent, authorize: {
                                try await lease.validate()
                                let current = try await authority.inspect(lease: lease)
                                guard current == prepared.eligibility else { throw HanlinHostError.staleContext }
                                try await MainActor.run { try self.validate(plan) }
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
                                try await opened.recordKnownIncompleteObject(knownID, identity: plan.identity)
                            }
                            throw error
                        }
                    }
                })
            self.journal = opened; self.runner = worker
        }
        guard let journal, let runner else { throw HanlinHostError.denied }
        try runner.validateCreationAvailability()
        try await journal.validateCreationAvailability(namespace: access.session.context.namespace)
        try validateAvailability()
        try runner.validateCreationAvailability()
        return eligibility
    }

    private func inspectEligibility() async throws -> AnyHanlinPageEligibility {
        let authority = authority
        let result = try await native.perform { lease in try await authority.inspect(lease: lease) }
        try validateAvailability()
        return result
    }

    private func validateAvailability() throws {
        try Task.checkCancellation()
        guard missingInstallation.isEmpty, let owner else { throw HanlinHostError.denied }
        try access.validate(access.session.context)
        try owner.validateSDKPresentation(for: access.session)
    }

    private func validate(_ plan: PinkhaHanlinCreatePagePlan) throws {
        try validateAvailability()
        guard plan.identity.session == access.session, plan.identity.deadline > .now else {
            throw HanlinHostError.staleContext
        }
    }

    private func check(_ plan: PinkhaHanlinCreatePagePlan, cancellation: PinkhaHanlinRevocationFence) throws {
        guard !cancellation.isRevoked else { throw HanlinHostError.cancelled }
        try validate(plan)
    }

    private func requestConfirmation(_ plan: PinkhaHanlinCreatePagePlan,
                                     eligibility: AnyHanlinPageEligibility) async throws -> AnyHanlinCreateApproval {
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
                let prompt = AnyHanlinCreatePagePrompt(session: access.session,
                    invocationID: plan.identity.invocationID.rawValue, title: plan.title,
                    spaceID: access.session.context.namespace.space)
                do {
                    try owner.presentCreatePageConfirmation(prompt) { [weak self, weak current] answer in
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

    private func cancelConfirmation(_ id: HanlinToolInvocationID) {
        guard pendingID == id else { return }
        decision?.revoke()
        owner?.dismissPendingPrompts()
    }

    func cancel(_ id: HanlinToolInvocationID) async {
        cancelConfirmation(id)
        await runner?.cancel(id)
    }
    func invalidate() {
        decision?.revoke(); owner?.dismissPendingPrompts(); access.invalidate()
    }
    func requestContextReadConsent() async throws { try await access.requestContextReadConsent() }
    func metadataReceipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? {
        preflight.receipt(for: id) ?? runner?.receipt(for: id)?.metadataReceipt()
    }

    static func mutationID(_ identity: PinkhaHanlinWriteIdentity) -> String {
        // This immutable operation identity can never mint a new native retry ID.
        String(PinkhaHanlinCreatePagePlan.digest(
            Data(("pinkha-any-hanlin-create/v1" + "\0" + identity.key).utf8)).prefix(32))
    }
}
