import Foundation
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaAnyHost

/// Any's native body adapter uses the ONE original shared cancellation worker.
/// The original context and approval own installation, consent and scope. A pure
/// original-parser conversion service supplies data only, never native authority.
@MainActor
final class AnyHanlinSaveMessageRunner {
    private struct Prepared: Sendable {
        let eligibility: AnyHanlinPageEligibility
        let body: AnyHanlinAtomicSaveBody
    }
    private final class Preparation { var value: AnyHanlinAtomicSaveBody? }
    private let core: PinkhaHanlinWriteRunner<PinkhaHanlinSaveMessagePlan, AnyHanlinWriteApproval, Prepared>

    init(context: AnyHanlinWriteContext, journal: PinkhaHanlinWriteJournal,
         documents: AnyEditorDocumentStore, services: AnyHanlinSaveMessageServices) throws {
        let preparation = Preparation()
        let operation = try AnyHanlinAtomicSaveMessageOperation(session: context.session,
            native: context.native, client: services.client, creator: context.creator,
            authority: context.authority, documents: documents, markdown: services.body)
        core = try .init(journal: journal,
            validatePlan: { try context.validate($0) },
            validateAvailable: { try context.validateAvailability() },
            invalidate: { context.invalidate() },
            prepareDispatch: { plan, approval in
                guard let body = preparation.value else { throw HanlinHostError.unresolvedWrite }
                try body.manifest.validate(plan: plan)
                let eligibility = try approval.consume(plan)
                preparation.value = nil
                return .init(eligibility: eligibility, body: body)
            },
            reserveMetadata: { plan in
                let conversion = try await services.convert(plan)
                let body = try AnyHanlinAtomicSaveBody(plan: plan, conversion: conversion)
                try await journal.reserveSaveMessage(.init(manifest: body.manifest))
                preparation.value = body
            },
            closeDispatch: { plan in
                preparation.value = nil
                try await journal.closeSaveMessageDispatch(for: plan.identity)
            },
            dispatch: { plan, prepared, authorizeNextEffect, receive in
                try await operation.execute(plan: plan, body: prepared.body, eligibility: prepared.eligibility,
                    journal: journal, authorizeNextEffect: { try await authorizeNextEffect() },
                    authorizeOriginalRead: {
                        try await context.validateNativeIdentity(plan.identity, requireUnexpired: false)
                    }, receiveFinalRoot: { id in try await receive(id) })
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
