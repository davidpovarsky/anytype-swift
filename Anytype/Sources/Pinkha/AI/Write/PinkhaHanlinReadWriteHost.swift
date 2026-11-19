import Foundation
import UIKit
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore

/// UIKit ownership stays in the application. Routing, replay protection and
/// original-scope receipts use the same shared implementation as the Any host.
@MainActor
final class PinkhaHanlinReadWriteHost: HanlinHostIntegration {
    nonisolated let apiVersion = HanlinAPIVersion(major: 1, minor: 0)
    let session: HanlinHostSession
    private let router: PinkhaHanlinHostRouter
    private let write: PinkhaHanlinCreateBinding?

    static func make(presenter: UIViewController, routeOwner: SpaceHubCoordinatorViewModel,
                     conversationID: UUID, locale: Locale = .autoupdatingCurrent) throws -> PinkhaHanlinReadWriteHost {
        let context = try PinkhaHanlinCreatePageContext(presenter: presenter, routeOwner: routeOwner,
            conversationID: conversationID, locale: locale)
        return try .init(read: context.makeReadAdapter(), session: context.session,
                         write: PinkhaHanlinCreateBinding(context: context))
    }

    private init(read: PinkhaHanlinHostAdapter, session: HanlinHostSession,
                 write: PinkhaHanlinCreateBinding?) throws {
        self.session = session; self.write = write
        self.router = try .init(read: read, session: session, write: write)
    }

    #if DEBUG
    static func readOnlyForTesting(read: PinkhaHanlinHostAdapter,
                                   session: HanlinHostSession) throws -> PinkhaHanlinReadWriteHost {
        try .init(read: read, session: session, write: nil)
    }
    #endif

    var missingWriteInstallation: [PinkhaHanlinWriteInstallationRequirement] { router.missingWriteInstallation }

    func install(_ owner: PinkhaHanlinChatPresentation, controller: PinkhaHanlinChatController) throws {
        try router.validateCurrentSession(owner.session)
        guard let write else { throw HanlinHostError.denied }
        try write.install(owner, controller: controller)
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

/// Composition of concrete reviewed helpers; not an alternate permission/journal/SDK implementation.
@MainActor
private final class PinkhaHanlinCreateBinding: PinkhaHanlinWriteBinding {
    private let context: PinkhaHanlinCreatePageContext
    private let tool: HanlinHostTool
    private var journal: PinkhaHanlinWriteJournal?
    private var runner: PinkhaHanlinCreatePageRunner?
    private var opening = false
    private weak var owner: PinkhaHanlinChatPresentation?
    private let preflight = PinkhaHanlinWritePreflight()

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

    func observeInvalidation(_ callback: @escaping @MainActor () -> Void) {
        context.observeInvalidation(callback)
    }

    init(context: PinkhaHanlinCreatePageContext) throws {
        self.context = context
        self.tool = try PinkhaHanlinCreatePageTool.make()
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
            let plan = try PinkhaHanlinCreatePagePlan(invocation: invocation)
            try await prepareOwner()
            guard let journal, let runner else { throw HanlinHostError.denied }
            try check(plan, cancellation: cancellation)
            await progress(try .init(invocationID: invocation.request.id, sequence: 1, timestamp: .now,
                                    fractionCompleted: 0, message: "Awaiting confirmation"))
            try check(plan, cancellation: cancellation)
            let approval = try await context.requestConfirmation(for: plan)
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
            let runner = try PinkhaHanlinCreatePageRunner(context: context, journal: opened)
            self.journal = opened; self.runner = runner
        }
        guard let journal, let runner else { throw HanlinHostError.denied }
        try runner.validateCreationAvailability()
        try await journal.validateCreationAvailability(namespace: context.session.context.namespace)
        _ = try context.validateCreationAvailability()
        try runner.validateCreationAvailability()
        try context.validateConfirmationAvailability()
    }

    private func check(_ plan: PinkhaHanlinCreatePagePlan, cancellation: PinkhaHanlinRevocationFence) throws {
        guard missingInstallation.isEmpty, !cancellation.isRevoked else {
            throw HanlinHostError.cancelled
        }
        _ = try context.validate(plan)
    }

    func cancel(_ id: HanlinToolInvocationID) async {
        context.cancelConfirmation(for: id)
        await runner?.cancel(id) // Best-effort request fence/uncertain metadata; never native rollback.
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