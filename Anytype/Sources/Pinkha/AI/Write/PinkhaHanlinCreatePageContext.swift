import PinkhaHanlinCore
import Foundation
@preconcurrency import Combine
import Factory
import Observation
import Services
import ProtobufMessages
import UIKit
import HanlinHostContracts
import HanlinPlatformContracts

/// In-memory, one-use approval. Only this file's real mounted native confirmation may issue it.
/// It grants no SDK authority and cannot be decoded, persisted or constructed from model arguments.
@MainActor
final class PinkhaHanlinCreateApproval {
    private let identity: PinkhaHanlinWriteIdentity
    private let typeID: Data
    private var consumed = false

    fileprivate init(identity: PinkhaHanlinWriteIdentity, typeID: String) {
        self.identity = identity; self.typeID = Data(typeID.utf8)
    }

    func consume(for plan: PinkhaHanlinCreatePagePlan, in context: PinkhaHanlinCreatePageContext) throws -> ObjectType {
        guard !consumed, identity == plan.identity else { throw HanlinHostError.denied }
        let type = try context.validate(plan)
        guard Data(type.id.utf8) == typeID else { throw HanlinHostError.staleContext }
        consumed = true
        return type
    }
}

/// Real native preparation/confirmation. The original source editor remains the context authority;
/// the mounted SDK sheet owns prompts. The runner reserves durable metadata before native dispatch.
@MainActor
final class PinkhaHanlinCreatePageContext {
    let session: HanlinHostSession
    private let authority: PinkhaHanlinNativeAccess
    private weak var presenter: UIViewController?
    private let members = Container.shared.participantSpacesStorage()
    private let types = Container.shared.objectTypeProvider()
    private var subscriptions: [AnyCancellable] = []
    private var invalidated = false
    private var alert: PinkhaHanlinConsentController?
    private var decision: PinkhaHanlinReadConsentDecision?
    private var pendingPlan: PinkhaHanlinCreatePagePlan?

    init(presenter: UIViewController, routeOwner: SpaceHubCoordinatorViewModel,
         conversationID: UUID, locale: Locale) throws {
        let authority = try PinkhaHanlinNativeAccess(presenter: presenter, routeOwner: routeOwner,
            conversationID: conversationID, locale: locale)
        self.authority = authority; self.session = authority.session; self.presenter = presenter
        let recheck: @Sendable () -> Void = { [weak self] in
            Task { @MainActor in
                guard let self else { return }
                do {
                    if let plan = self.pendingPlan { _ = try self.validate(plan) }
                    else { try self.authority.validate(self.session.context) }
                }
                catch { self.invalidate() }
            }
        }
        Container.shared.accountManager().accountPublisher.sink { _ in recheck() }.store(in: &subscriptions)
        Container.shared.applicationStateService().statePublisher.sink { _ in recheck() }.store(in: &subscriptions)
        members.allParticipantSpacesPublisher.sink { _ in recheck() }.store(in: &subscriptions)
        types.syncPublisher.sink { _ in recheck() }.store(in: &subscriptions)
        withObservationTracking { _ = routeOwner.currentSpaceId } onChange: { [weak self] in
            Task { @MainActor in self?.invalidate() }
        }
        if let editor = presenter as? EditorPageController, let model = editor.viewModel {
            model.document.syncPublisher.sink { _ in recheck() }.store(in: &subscriptions)
            model.blocksStateManager.editorSelectedBlocks.sink { _ in recheck() }.store(in: &subscriptions)
        }
        if let scene = presenter.viewIfLoaded?.window?.windowScene {
            NotificationCenter.default.publisher(for: UIScene.willDeactivateNotification, object: scene)
                .sink { [weak self] _ in Task { @MainActor in self?.invalidate() } }.store(in: &subscriptions)
        }
    }

    func invalidate() {
        invalidated = true
        authority.invalidate()
        let owned = alert
        decision?.revoke()
        owned?.dismiss(animated: false)
    }

    func observeInvalidation(_ callback: @escaping @MainActor () -> Void) {
        authority.observeInvalidation(callback)
    }

    func installPromptOwner(_ controller: PinkhaHanlinChatController) throws {
        try authority.installPromptOwner(controller)
        presenter = controller
    }

    /// Future composition may reuse the accepted read adapter with THIS identical host session.
    /// It still advertises only read capabilities; this does not install a writable SDK catalog.
    func makeReadAdapter() throws -> PinkhaHanlinHostAdapter { try .init(access: authority) }

    func requestContextReadConsent() async throws { try await authority.requestContextReadConsent() }

    func cancelConfirmation(for id: HanlinToolInvocationID) {
        guard pendingPlan?.identity.invocationID == id else { return }
        let owned = alert
        decision?.revoke()
        owned?.dismiss(animated: false)
    }

    func targetDidMount(_ destination: HanlinHostDestination,
                        controller: EditorPageController) throws -> HanlinHostNavigationResult {
        try authority.acknowledgeMounted(destination, controller: controller)
    }

    func makeReturnHandoff(_ destination: HanlinHostDestination,
                           controller: PinkhaHanlinChatController) throws -> PinkhaHanlinNavigationHandoff {
        try authority.makeReturnHandoff(destination, controller: controller)
    }

    func validate(_ plan: PinkhaHanlinCreatePagePlan) throws -> ObjectType {
        try Task.checkCancellation()
        guard !invalidated, plan.identity.session == session, plan.identity.deadline > .now else {
            throw HanlinHostError.staleContext
        }
        return try validateCreationAvailability()
    }

    /// Same native authority/eligibility as execution, without fabricating a model invocation for a catalog.
    func validateCreationAvailability() throws -> ObjectType {
        try Task.checkCancellation()
        guard !invalidated else { throw HanlinHostError.staleContext }
        guard InvocationSettings.handler?.isLogEnabled == false else { throw HanlinHostError.denied }
        try authority.validate(session.context)
        guard let member = members.participantSpaceView(spaceId: session.context.namespace.space),
              member.canEdit, member.spaceView.isActive,
              member.spaceView.targetSpaceId.utf8.elementsEqual(session.context.namespace.space.utf8),
              let participant = member.participant, participant.status == .active,
              participant.identity.utf8.elementsEqual(session.context.namespace.account.utf8),
              participant.spaceId.utf8.elementsEqual(session.context.namespace.space.utf8) else { throw HanlinHostError.denied }
        switch participant.permission {
        case .owner, .admin, .writer: break
        default: throw HanlinHostError.denied
        }
        // Exact standard Page ONLY. No fallback type, preparation/provisioning, default template or Torah schema.
        let candidates = types.objectTypes(spaceId: session.context.namespace.space).filter {
            $0.uniqueKey.value.utf8.elementsEqual(ObjectTypeUniqueKey.page.value.utf8)
                && $0.spaceId.utf8.elementsEqual(session.context.namespace.space.utf8)
        }
        guard candidates.count == 1, let type = candidates.first,
              !type.id.isEmpty, type.id.utf8.count <= 256,
              !type.hidden, !type.readonly, !type.isArchived, !type.isDeleted,
              type.canCreateObjectOfThisType, type.recommendedLayout == .basic else { throw HanlinHostError.denied }
        return type
    }

    func validateConfirmationAvailability() throws {
        _ = try validateCreationAvailability()
        guard decision == nil, let presenter, presenter.presentedViewController == nil,
              presenter.viewIfLoaded?.window != nil, !presenter.isBeingDismissed else { throw HanlinHostError.denied }
    }

    func requestConfirmation(for plan: PinkhaHanlinCreatePagePlan) async throws -> PinkhaHanlinCreateApproval {
        let type = try validate(plan)
        guard decision == nil, let presenter, presenter.presentedViewController == nil,
              let member = members.participantSpaceView(spaceId: session.context.namespace.space) else { throw HanlinHostError.denied }
        let current = PinkhaHanlinReadConsentDecision() // Starts denied for EACH exact operation.
        let hebrew = Locale(identifier: session.context.localeIdentifier).language.languageCode?.identifier == "he"
        let timeout = Task { @MainActor [weak self, weak current] in
            do {
                try await Task.sleep(for: .seconds(max(0, plan.identity.deadline.timeIntervalSinceNow)))
                guard let self, let current, self.decision === current else { return }
                let owned = self.alert
                current.resolve(false)
                owned?.dismiss(animated: false)
            } catch {}
        }
        defer { timeout.cancel() }
        let allowed = await withTaskCancellationHandler {
            await withCheckedContinuation { continuation in
                guard !Task.isCancelled, !invalidated, current.begin({ [weak self] allowed in
                    self?.decision = nil; self?.alert = nil; self?.pendingPlan = nil
                    continuation.resume(returning: allowed)
                }) else { continuation.resume(returning: false); return }
                decision = current
                pendingPlan = plan
                let title = hebrew ? "ליצור דף חדש?" : "Create a new page?"
                // Exact title and ORIGINAL native Space are visible to the user; neither is logged/persisted.
                let message = "\(plan.title)\n\n\(member.spaceView.name)\n\(session.context.namespace.space)"
                let alert = PinkhaHanlinConsentController(purpose: .createPage,
                    title: title, explanation: message,
                    allowTitle: hebrew ? "יצירת דף" : "Create page",
                    cancelTitle: hebrew ? "ביטול" : "Cancel", decision: current) { [weak self] in
                        guard let self else { throw HanlinHostError.staleContext }
                        let live = try self.validate(plan)
                        guard live.id.utf8.elementsEqual(type.id.utf8) else { throw HanlinHostError.staleContext }
                }
                self.alert = alert
                presenter.present(alert, animated: true) { [weak current, weak alert] in
                    if alert?.viewIfLoaded?.window == nil { current?.resolve(false) }
                }
            }
        } onCancel: { [weak self] in Task { @MainActor in self?.invalidate() } }
        let live = try validate(plan)
        guard allowed, live.id.utf8.elementsEqual(type.id.utf8) else { throw HanlinHostError.denied }
        return .init(identity: plan.identity, typeID: live.id)
    }
}
