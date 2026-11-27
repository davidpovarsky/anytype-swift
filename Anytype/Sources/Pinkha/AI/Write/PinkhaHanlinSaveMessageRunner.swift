import Foundation
import Services
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaHanlinUI

/// Heart binding to the ONE shared original worker. The original consent/context
/// owner supplies the typed full-message approval; this file advertises no tool.
@MainActor
final class PinkhaHanlinSaveMessageRunner {
    private struct Prepared { let type: ObjectType; let body: PinkhaHanlinHeartSaveBody }
    private final class Preparation { var value: PinkhaHanlinHeartSaveBody? }
    private let core: PinkhaHanlinWriteRunner<PinkhaHanlinSaveMessagePlan, PinkhaHanlinCreateApproval, Prepared>

    init(context: PinkhaHanlinCreatePageContext, journal: PinkhaHanlinWriteJournal) throws {
        let preparation = Preparation()
        core = try .init(journal: journal,
            validatePlan: { _ = try context.validate($0) },
            validateAvailable: { _ = try context.validateCreationAvailability() },
            invalidate: { context.invalidate() },
            prepareDispatch: { plan, approval in
                guard let body = preparation.value else { throw HanlinHostError.unresolvedWrite }
                try body.manifest.validate(plan: plan)
                let type = try approval.consume(for: plan, in: context)
                preparation.value = nil
                return .init(type: type, body: body)
            },
            reserveMetadata: { plan in
                // Finish original non-speculative Markdown parsing/conversion
                // before the very first native operation. Unsupported structure
                // leaves only the original not-dispatched journal reservation.
                let conversion = try await PinkhaHanlinOriginalMarkdownSavePlanner.convert(plan)
                let body = try PinkhaHanlinHeartSaveBody(plan: plan, document: conversion.document)
                try await journal.reserveSaveMessage(.init(manifest: body.manifest))
                preparation.value = body
            },
            closeDispatch: { plan in
                preparation.value = nil
                try await journal.closeSaveMessageDispatch(for: plan.identity)
            },
            dispatch: { plan, prepared, authorizeNextEffect, receive in
                try await PinkhaHanlinHeartSaveMessageOperation.execute(plan: plan, type: prepared.type,
                    body: prepared.body, journal: journal, authorizeNextEffect: {
                        try authorizeNextEffect()
                        let live = try context.validate(plan)
                        guard live.id.utf8.elementsEqual(prepared.type.id.utf8) else {
                            throw HanlinHostError.staleContext
                        }
                    },
                    authorizeOriginalRead: {
                        let live = try context.validateNativeIdentity(plan.identity, requireUnexpired: false)
                        guard live.id.utf8.elementsEqual(prepared.type.id.utf8) else {
                            throw HanlinHostError.staleContext
                        }
                    },
                    receive: receive)
            })
    }

    func execute(_ invocation: HanlinHostInvocation,
                 approval: PinkhaHanlinCreateApproval) async throws -> HanlinHostExecutionResult {
        try await core.execute(invocation, approval: approval)
    }
    func cancel(_ id: HanlinToolInvocationID) async { await core.cancel(id) }
    func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult? {
        await core.drainCancelledInvocation(id)
    }
    func receipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? { core.receipt(for: id) }
    func validateCreationAvailability() throws { try core.validateCreationAvailability() }
}
