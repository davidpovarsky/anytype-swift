import Foundation
import Factory
import Services
import ProtobufMessages
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore

/// Heart-specific native I/O only. Reservation, timeout, cancellation and late
/// original-scope reconciliation are owned by the shared unchanged worker.
@MainActor
final class PinkhaHanlinCreatePageRunner {
    private let core: PinkhaHanlinCreateRunner<PinkhaHanlinCreateApproval, ObjectType>

    init(context: PinkhaHanlinCreatePageContext, journal: PinkhaHanlinWriteJournal) throws {
        let actions = Container.shared.objectActionsService()
        core = try .init(journal: journal,
            validatePlan: { _ = try context.validate($0) },
            validateAvailable: { _ = try context.validateCreationAvailability() },
            invalidate: { context.invalidate() },
            prepareDispatch: { plan, approval in
                guard InvocationSettings.handler?.isLogEnabled == false else { throw HanlinHostError.cancelled }
                return try approval.consume(for: plan, in: context)
            },
            dispatch: { plan, type, receive in
                let original = plan.identity.session.context
                let details = try await actions.createObject(name: plan.title, typeUniqueKey: type.uniqueKey,
                    shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                    spaceId: original.namespace.space, origin: .none, templateId: nil,
                    createdInContext: "", createdInContextRef: "", additionalDetails: [])
                guard !details.id.isEmpty, details.id.utf8.count <= 256,
                      details.spaceId.utf8.elementsEqual(original.namespace.space.utf8),
                      details.type.utf8.elementsEqual(type.id.utf8),
                      details.name.utf8.elementsEqual(plan.title.utf8),
                      details.resolvedLayoutValue == .basic,
                      !details.isDeleted, !details.isArchived, !details.isTemplate,
                      !details.isHidden, !details.isReadonly else { throw HanlinHostError.resultMismatch }
                try await receive(details.id)
            })
    }

    func execute(_ invocation: HanlinHostInvocation,
                 approval: PinkhaHanlinCreateApproval) async throws -> HanlinHostExecutionResult {
        try await core.execute(invocation, approval: approval)
    }
    func cancel(_ id: HanlinToolInvocationID) async { await core.cancel(id) }
    func receipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? { core.receipt(for: id) }
    func validateCreationAvailability() throws { try core.validateCreationAvailability() }
}
