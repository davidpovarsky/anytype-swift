import Foundation
import UIKit
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore

/// UIKit ownership stays in the application. Routing, replay protection and
/// original-scope receipts use the same shared implementation as the Any host.
@MainActor
final class PinkhaHanlinReadWriteHost: HanlinHostCancellationDrainSource {
    nonisolated let apiVersion = HanlinAPIVersion(major: 1, minor: 0)
    let session: HanlinHostSession
    private let router: PinkhaHanlinHostRouter
    private let write: PinkhaHanlinCreateBinding?
    private let saveMessage: PinkhaHanlinSaveBinding?
    private let installation: PinkhaHanlinHeartWriteInstallation?

    static func make(presenter: UIViewController, routeOwner: SpaceHubCoordinatorViewModel,
                     conversationID: UUID, locale: Locale = .autoupdatingCurrent) throws -> PinkhaHanlinReadWriteHost {
        let context = try PinkhaHanlinCreatePageContext(presenter: presenter, routeOwner: routeOwner,
            conversationID: conversationID, locale: locale)
        return try make(context: context, includeSaveMessage: false)
    }

    private init(read: PinkhaHanlinHostAdapter, session: HanlinHostSession,
                 installation: PinkhaHanlinHeartWriteInstallation?,
                 write: PinkhaHanlinCreateBinding?, saveMessage: PinkhaHanlinSaveBinding?) throws {
        self.session = session; self.installation = installation
        self.write = write; self.saveMessage = saveMessage
        self.router = try .init(read: read, session: session, write: write, saveMessage: saveMessage)
    }

    private static func make(context: PinkhaHanlinCreatePageContext,
                             includeSaveMessage: Bool) throws -> PinkhaHanlinReadWriteHost {
        let installation = PinkhaHanlinHeartWriteInstallation(context: context)
        let write = PinkhaHanlinCreateBinding(installation: installation,
            tool: try PinkhaHanlinCreatePageTool.make(),
            validatePlan: { _ = try context.validate($0) },
            requestConfirmation: { try await context.requestConfirmation(for: $0) })
        let saveMessage: PinkhaHanlinSaveBinding?
        if includeSaveMessage {
            saveMessage = PinkhaHanlinSaveBinding(installation: installation,
                tool: try PinkhaHanlinSaveMessageTool.make(),
                validatePlan: { _ = try context.validate($0) },
                requestConfirmation: { try await context.requestConfirmation(for: $0) })
        } else { saveMessage = nil }
        return try .init(read: context.makeReadAdapter(), session: context.session,
                         installation: installation, write: write, saveMessage: saveMessage)
    }

    /// Explicit production save composition with the original Heart context.
    /// Native eligibility, mounted consent and the protected shared worker
    /// remain authoritative. Ordinary make stays read/create-only until the
    /// separately reviewed production entry is admitted.
    static func makeForSavingMessages(presenter: UIViewController,
        routeOwner: SpaceHubCoordinatorViewModel, conversationID: UUID,
        locale: Locale = .autoupdatingCurrent) throws -> PinkhaHanlinReadWriteHost {
        let context = try PinkhaHanlinCreatePageContext(presenter: presenter, routeOwner: routeOwner,
            conversationID: conversationID, locale: locale)
        return try make(context: context, includeSaveMessage: true)
    }

    #if DEBUG
    static func readOnlyForTesting(read: PinkhaHanlinHostAdapter,
                                   session: HanlinHostSession) throws -> PinkhaHanlinReadWriteHost {
        try .init(read: read, session: session, installation: nil, write: nil, saveMessage: nil)
    }

    /// Existing native acceptance uses the same production composition.
    /// The real fixture, body and authority admission remain with its caller.
    static func makeForSaveMessageAcceptance(presenter: UIViewController,
        routeOwner: SpaceHubCoordinatorViewModel, conversationID: UUID,
        locale: Locale = .autoupdatingCurrent) throws -> PinkhaHanlinReadWriteHost {
        try makeForSavingMessages(presenter: presenter, routeOwner: routeOwner,
            conversationID: conversationID, locale: locale)
    }
    #endif

    var missingWriteInstallation: [PinkhaHanlinWriteInstallationRequirement] { router.missingWriteInstallation }

    func install(_ owner: PinkhaHanlinChatPresentation, controller: PinkhaHanlinChatController) throws {
        try router.validateCurrentSession(owner.session)
        guard let installation, write != nil else { throw HanlinHostError.denied }
        try installation.install(owner, controller: controller)
    }
    func observeInvalidation(_ callback: @escaping @MainActor () -> Void) { router.observeInvalidation(callback) }
    func revokePresentation() { router.revokePresentation() }
    func context(for session: HanlinHostSession) async throws -> HanlinHostContext {
        try await router.context(for: session)
    }
    func catalog(for context: HanlinHostContext) async throws -> HanlinHostCatalog {
        try await router.catalog(for: context)
    }
    func execute(_ invocation: HanlinHostInvocation,
                 progress: @escaping HanlinHostProgressHandler) async throws -> HanlinHostExecutionResult {
        try await router.execute(invocation, progress: progress)
    }
    func cancel(_ id: HanlinToolInvocationID) async { await router.cancel(id) }
    func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult? {
        await router.drainCancelledInvocation(id)
    }
    func open(_ destination: HanlinHostDestination) async throws -> HanlinHostNavigationResult {
        try await router.open(destination)
    }
    func targetDidMount(_ destination: HanlinHostDestination,
                        controller: EditorPageController) throws -> HanlinHostNavigationResult {
        try router.validateCurrentSession(session)
        guard destination.context == session.context, let write else { throw HanlinHostError.staleContext }
        return try write.targetDidMount(destination, controller: controller)
    }
    func makeReturnHandoff(_ destination: HanlinHostDestination,
                           controller: PinkhaHanlinChatController) throws -> PinkhaHanlinNavigationHandoff {
        try router.validateCurrentSession(session)
        guard destination.context == session.context, let write else { throw HanlinHostError.staleContext }
        return try write.makeReturnHandoff(destination, controller: controller)
    }
    func requestContextReadConsent() async throws { try await router.requestContextReadConsent() }
    func metadataReceipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? { router.metadataReceipt(for: id) }
    func invalidate() async { await router.invalidate() }
}

/// The two concrete native runners delegate execution/cancellation to the ONE
/// shared Core worker. This private shape only composes their original I/O.
@MainActor
private protocol PinkhaHanlinHeartWriteRunning: AnyObject {
    init(context: PinkhaHanlinCreatePageContext, journal: PinkhaHanlinWriteJournal) throws
    func execute(_ invocation: HanlinHostInvocation,
                 approval: PinkhaHanlinCreateApproval) async throws -> HanlinHostExecutionResult
    func cancel(_ id: HanlinToolInvocationID) async
    func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult?
    func receipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult?
    func validateCreationAvailability() throws
}

extension PinkhaHanlinCreatePageRunner: PinkhaHanlinHeartWriteRunning {}
extension PinkhaHanlinSaveMessageRunner: PinkhaHanlinHeartWriteRunning {}

private typealias PinkhaHanlinCreateBinding =
    PinkhaHanlinHeartWriteBinding<PinkhaHanlinCreatePagePlan, PinkhaHanlinCreatePageRunner>
private typealias PinkhaHanlinSaveBinding =
    PinkhaHanlinHeartWriteBinding<PinkhaHanlinSaveMessagePlan, PinkhaHanlinSaveMessageRunner>

/// One mounted presentation/consent owner is shared by both routes. No second
/// prompt controller, account lifetime or native authority is introduced.
@MainActor
private final class PinkhaHanlinHeartWriteInstallation {
    let context: PinkhaHanlinCreatePageContext
    private weak var owner: PinkhaHanlinChatPresentation?

    init(context: PinkhaHanlinCreatePageContext) { self.context = context }

    var missingInstallation: [PinkhaHanlinWriteInstallationRequirement] {
        guard let owner, (try? owner.validateInstallation(for: context.session)) != nil else {
            return PinkhaHanlinWriteInstallationRequirement.missing
        }
        return []
    }

    func install(_ owner: PinkhaHanlinChatPresentation, controller: PinkhaHanlinChatController) throws {
        try owner.validateInstallation(for: context.session)
        try context.installPromptOwner(controller)
        self.owner = owner
    }
}

/// Original preflight, permission, account journal and retained-worker drain,
/// shared by the title-only and complete-body writers without changing their
/// logical tools, plans, approvals or distinct native operations.
@MainActor
private final class PinkhaHanlinHeartWriteBinding<Plan: PinkhaHanlinNativeWritePlan,
    Runner: PinkhaHanlinHeartWriteRunning>: PinkhaHanlinWriteBinding {
    private let installation: PinkhaHanlinHeartWriteInstallation
    private var context: PinkhaHanlinCreatePageContext { installation.context }
    private let tool: HanlinHostTool
    private let validatePlan: @MainActor (Plan) throws -> Void
    private let requestConfirmation: @MainActor (Plan) async throws -> PinkhaHanlinCreateApproval
    private var journal: PinkhaHanlinWriteJournal?
    private var runner: Runner?
    private var opening = false
    private let preflight = PinkhaHanlinWritePreflight()

    var missingInstallation: [PinkhaHanlinWriteInstallationRequirement] { installation.missingInstallation }

    func observeInvalidation(_ callback: @escaping @MainActor () -> Void) {
        context.observeInvalidation(callback)
    }

    init(installation: PinkhaHanlinHeartWriteInstallation, tool: HanlinHostTool,
         validatePlan: @escaping @MainActor (Plan) throws -> Void,
         requestConfirmation: @escaping @MainActor (Plan) async throws -> PinkhaHanlinCreateApproval) {
        self.installation = installation; self.tool = tool
        self.validatePlan = validatePlan; self.requestConfirmation = requestConfirmation
    }

    func catalogTool() async throws -> HanlinHostTool? {
        guard missingInstallation.isEmpty else { return nil }
        do {
            try await prepareOwner()
            return tool
        } catch {
            try Task.checkCancellation()
            return nil // Missing/denied/uncertain/corrupt journal readiness cannot advertise a write.
        }
    }

    func execute(_ invocation: HanlinHostInvocation, cancellation: PinkhaHanlinRevocationFence,
                 progress: @escaping HanlinHostProgressHandler) async throws -> HanlinHostExecutionResult {
        try await preflight.execute(invocation, prepare: {
            guard missingInstallation.isEmpty else { throw HanlinHostError.denied }
            let plan = try Plan(invocation: invocation)
            try await prepareOwner()
            guard let journal, let runner else { throw HanlinHostError.denied }
            try check(plan, cancellation: cancellation)
            await progress(try .init(invocationID: invocation.request.id, sequence: 1, timestamp: .now,
                                    fractionCompleted: 0, message: "Awaiting confirmation"))
            try check(plan, cancellation: cancellation)
            let approval = try await requestConfirmation(plan)
            try check(plan, cancellation: cancellation)
            try await journal.validateCreationAvailability(namespace: context.session.context.namespace)
            try check(plan, cancellation: cancellation)
            return (runner, approval)
        }, dispatch: { prepared in
            try await prepared.0.execute(invocation, approval: prepared.1)
        })
    }

    private func prepareOwner() async throws {
        guard missingInstallation.isEmpty else { throw HanlinHostError.denied }
        try context.validateConfirmationAvailability()
        if journal == nil {
            guard !opening else { throw HanlinHostError.denied }
            opening = true
            defer { opening = false }
            let opened = try await PinkhaHanlinAccountOwner.shared.journal(for: context.session.context.namespace)
            _ = try context.validateCreationAvailability()
            try await opened.validateCreationAvailability(namespace: context.session.context.namespace)
            _ = try context.validateCreationAvailability()
            let runner = try Runner(context: context, journal: opened)
            self.journal = opened; self.runner = runner
        }
        guard let journal, let runner else { throw HanlinHostError.denied }
        try runner.validateCreationAvailability()
        try await journal.validateCreationAvailability(namespace: context.session.context.namespace)
        _ = try context.validateCreationAvailability()
        try runner.validateCreationAvailability()
        try context.validateConfirmationAvailability()
    }

    private func check(_ plan: Plan, cancellation: PinkhaHanlinRevocationFence) throws {
        guard missingInstallation.isEmpty, !cancellation.isRevoked else {
            throw HanlinHostError.cancelled
        }
        try validatePlan(plan)
    }

    func cancel(_ id: HanlinToolInvocationID) async {
        context.cancelConfirmation(for: id)
        await runner?.cancel(id) // Best-effort request fence/uncertain metadata; never native rollback.
    }
    func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult? {
        let retained = await runner?.drainCancelledInvocation(id)
        return retained?.metadataReceipt() ?? preflight.receipt(for: id)?.metadataReceipt()
    }

    func invalidate() { context.invalidate() }
    func requestContextReadConsent() async throws { try await context.requestContextReadConsent() }
    func metadataReceipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? {
        preflight.receipt(for: id) ?? runner?.receipt(for: id)?.metadataReceipt()
    }
    func targetDidMount(_ destination: HanlinHostDestination,
                        controller: EditorPageController) throws -> HanlinHostNavigationResult {
        try context.targetDidMount(destination, controller: controller)
    }

    func makeReturnHandoff(_ destination: HanlinHostDestination,
                           controller: PinkhaHanlinChatController) throws -> PinkhaHanlinNavigationHandoff {
        try context.makeReturnHandoff(destination, controller: controller)
    }
}
