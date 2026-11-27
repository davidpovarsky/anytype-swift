#if canImport(UIKit)
import PinkhaHanlinCore
import Foundation
import Observation
import UIKit
import HanlinAgentCore
import HanlinChatCore
import HanlinHostContracts
import HanlinPersistenceAdapters

/// Application lifetime and UI state around ONE canonical Hanlin session/engine.
/// The SDK owns model execution; Anytype owns source authority, native prompts and write receipts.
@MainActor
@Observable
public final class PinkhaHanlinChatPresentation: PinkhaHanlinOwnedPresentation {
    public let session: HanlinHostSession
    public var draft = ""
    public private(set) var messages: [HanlinChatMessage] = []
    public private(set) var receiptMessages: [String] = []
    public private(set) var isStreaming = false
    public private(set) var isStopping = false
    public private(set) var isConfigured = false
    public private(set) var readAllowed = false
    public private(set) var isReturningToSource = false
    public private(set) var errorMessage: String?

    @ObservationIgnored private let host: any PinkhaHanlinPresentationHost
    @ObservationIgnored public let appearance: PinkhaHanlinAppearance
    @ObservationIgnored private let hooks: PinkhaHanlinPresentationHooks
    @ObservationIgnored private weak var controller: PinkhaHanlinChatController?
    @ObservationIgnored private weak var scene: UIWindowScene?
    @ObservationIgnored private var agent: HanlinAgentSession?
    @ObservationIgnored private var modelReference: HanlinModelReference?
    @ObservationIgnored private var running: Task<Void, Never>?
    @ObservationIgnored private var stopping: Task<Void, Never>?
    @ObservationIgnored private var currentRunID: UUID?
    @ObservationIgnored private var requiresReconciliation = false
    @ObservationIgnored private var closing: Task<Void, Never>?
    @ObservationIgnored private var closed = false
    @ObservationIgnored private var receiptIDs = Set<UUID>()
    @ObservationIgnored public private(set) var returnReceipt: PinkhaHanlinNavigationHandoff?

    public var canSend: Bool {
        isConfigured && !closed && !isStreaming && !isStopping && !requiresReconciliation
            && currentRunID == nil && !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && draft.utf8.count <= 32_768 && messages.count < 256
    }
    public var hasSource: Bool { session.context.objectReference != nil }

    public init(host: any PinkhaHanlinPresentationHost, presenter: UIViewController,
                appearance: PinkhaHanlinAppearance = .system,
                hooks: PinkhaHanlinPresentationHooks = .init()) throws {
        self.host = host
        self.session = host.session
        self.scene = presenter.viewIfLoaded?.window?.windowScene
        self.appearance = appearance
        self.hooks = hooks
        try PinkhaHanlinAccountOwner.shared.register(self)
        host.observeInvalidation { [weak self] in
            guard let self else { return }
            self.hooks.invalidated(self.session.id, "nativeAuthorityChanged")
            self.invalidate()
        }
    }

    public func didMount(_ controller: PinkhaHanlinChatController) {
        guard !closed else { controller.dismiss(animated: false); return }
        self.controller = controller
        do {
            try host.install(self, controller: controller)
            hooks.didMount(self, controller)
        }
        catch { invalidate() }
    }

    public func validateInstallation(for session: HanlinHostSession) throws {
        guard !closed, self.session == session,
              PinkhaHanlinAccountOwner.shared.owns(self),
              PinkhaHanlinAccountOwner.shared.isAvailable(namespace: session.context.namespace),
              let scene, let controller, controller.presentation === self,
              controller.presentingViewController != nil,
              controller.viewIfLoaded?.window?.windowScene === scene,
              scene.activationState == .foregroundActive,
              !controller.isBeingDismissed else { throw HanlinHostError.staleContext }
    }

    /// Credentials are supplied explicitly by the user and live only inside this presentation's
    /// canonical engine. No Keychain/AppGroup discovery, request logging or cross-app credential read.
    public func configure(endpoint: String, model: String, credential: String) {
        guard !closed, !isConfigured, !isStreaming else { return }
        do {
            try validateInstallation(for: session)
            let configuration = try PinkhaHanlinModelConfiguration.make(endpoint: endpoint, model: model, credential: credential)
            let engine = try HanlinAISDKAgentEngine(configuration: configuration,
                fetch: HanlinAISDKProviderFactory.makeFetch(sessionConfiguration: .ephemeral))
            let agent = HanlinAgentSession(identity: session, host: host.integration, engine: engine,
                store: HanlinInMemoryConversationStore())
            agent.onHostResult = { [weak self] event in self?.receive(event) }
            agent.onSessionInvalidated = { [weak self] _ in self?.invalidate() }
            self.agent = agent
            modelReference = .init(provider: HanlinAISDKProviderFactory.descriptor(for: configuration).kind.rawValue,
                                   modelID: configuration.baseModelID)
            isConfigured = true
            errorMessage = nil
        } catch {
            errorMessage = PinkhaHanlinStrings.configurationFailed
        }
    }

    public func requestContextReadConsent() {
        guard !closed, !isStreaming, !isStopping, hasSource else { return }
        Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                try await self.host.requestContextReadConsent()
                try self.validateInstallation(for: self.session)
                self.readAllowed = true
                self.errorMessage = nil
            } catch {
                if !self.closed { self.errorMessage = PinkhaHanlinStrings.contextNotShared }
            }
        }
    }

    public func send() {
        guard canSend, let agent, let modelReference else { return }
        let prompt = draft
        draft = ""
        messages.append(.user(prompt))
        let history = messages.map { HanlinAISDKMessage(role: $0.role == "user" ? .user : .assistant, text: $0.content) }
        let answerID = UUID()
        let runID = UUID()
        currentRunID = runID
        messages.append(.init(id: answerID, role: "assistant", content: ""))
        errorMessage = nil
        running = Task { @MainActor [weak self] in
            guard let self, !self.closed, self.currentRunID == runID else { return }
            self.isStreaming = true
            defer {
                if self.currentRunID == runID {
                    self.isStreaming = false
                    self.running = nil
                    if !self.isStopping { self.currentRunID = nil }
                }
            }
            do {
                try self.validateInstallation(for: self.session)
                let stream = try await agent.stream(messages: history, modelReference: modelReference,
                    maxSteps: 8, presentationReference: "anytype.hanlin@1")
                for try await event in stream {
                    try Task.checkCancellation()
                    try self.validateInstallation(for: event.session)
                    if !self.isStopping, self.currentRunID == runID,
                       case .textDelta(let delta) = event.event,
                       let index = self.messages.firstIndex(where: { $0.id == answerID }) {
                        guard self.messages[index].content.utf8.count + delta.utf8.count <= 262_144 else {
                            throw HanlinHostError.outputLimitExceeded
                        }
                        self.messages[index].content += delta
                    }
                }
            } catch {
                // Provider errors may contain request details. Never log or expose them verbatim.
                if !self.closed, !self.isStopping, self.currentRunID == runID {
                    self.errorMessage = PinkhaHanlinStrings.requestFailed
                }
            }
        }
    }

    public func stop() {
        guard !closed, isStreaming, !isStopping, let agent, let runID = currentRunID else { return }
        isStopping = true
        errorMessage = nil
        let consumer = running
        stopping = Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                let result = try await agent.cancelCurrentRun()
                await consumer?.value
                guard !self.closed, self.currentRunID == runID else { return }
                try self.validateInstallation(for: self.session)
                self.requiresReconciliation = result?.requiresReconciliation ?? false
                if self.requiresReconciliation { self.errorMessage = PinkhaHanlinStrings.uncertain }
            } catch {
                await consumer?.value
                guard !self.closed, self.currentRunID == runID else { return }
                // A failed metadata save or uncertain host outcome cannot silently
                // restore permission to retry the operation in this conversation.
                self.requiresReconciliation = true
                self.errorMessage = PinkhaHanlinStrings.uncertain
            }
            guard !self.closed, self.currentRunID == runID else { return }
            self.isStopping = false
            self.isStreaming = false
            self.running = nil
            self.stopping = nil
            self.currentRunID = nil
        }
    }

    private func receive(_ event: HanlinHostResultEvent) {
        guard !closed, event.call.session == session, receiptIDs.count < 256,
              receiptIDs.insert(event.resultID).inserted else { return }
        // The presentation owns only safe outcome labels; payloads never enter a receipt log.
        switch event.result.effectState {
        case .confirmedCommitted: receiptMessages.append(PinkhaHanlinStrings.pageCreated)
        case .uncertain: receiptMessages.append(PinkhaHanlinStrings.uncertain)
        case .notDispatched: receiptMessages.append(PinkhaHanlinStrings.notDispatched)
        case .confirmedNoEffect:
            if case .completed = event.result.result.outcome { receiptMessages.append(PinkhaHanlinStrings.contextRead) }
            else { receiptMessages.append(PinkhaHanlinStrings.requestFailed) }
        }
    }

    /// The native Return action completes its queued request before closing the SDK session.
    /// The later UI receipt is never delivered as a response to that invalidated SDK session.
    public func returnToSource() {
        guard !closed, !isReturningToSource, let object = session.context.objectReference else { return }
        isReturningToSource = true
        Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                try validateInstallation(for: session)
                let selection = session.context.selectionReferences
                let destination = HanlinHostDestination(context: session.context, objectReference: object,
                    blockReference: selection.count == 1 ? selection.first : nil)
                let queued = try await host.integration.open(destination)
                guard case .queued = queued else { throw HanlinHostError.resultMismatch }
                try validateInstallation(for: session)
                guard let controller else { throw HanlinHostError.staleContext }
                let handoff = try host.makeReturnHandoff(destination, controller: controller)
                returnReceipt = handoff
                close { _ = try? handoff.acknowledgeMounted() }
            } catch {
                guard !closed else { return }
                isReturningToSource = false
                errorMessage = PinkhaHanlinStrings.returnFailed
            }
        }
    }

    public func invalidate() {
        close(completion: nil)
    }

    /// UI owners await SDK/host cancellation before draining the native session.
    /// Already dispatched native writes remain owned by that session until their
    /// original-scope receipts settle; cancellation never claims rollback.
    public func revokeAndDrain() async {
        close(completion: nil)
        await closing?.value
    }

    /// UIKit/its coordinator has already started dismissing this owned host.
    /// Revoke synchronously before any queued Allow action without another dismiss.
    public func observedInvalidation(_ cause: String) {
        hooks.invalidated(session.id, cause)
    }

    public func ownerWillDisappear() {
        close(completion: nil, dismissController: false)
    }

    private func close(completion: (@MainActor @Sendable () -> Void)?, dismissController: Bool = true) {
        guard !closed else { return }
        hooks.invalidated(session.id, "explicitCloseOrOwner")
        closed = true
        host.revokePresentation()
        running?.cancel()
        currentRunID = nil
        isStreaming = false
        isStopping = false
        let agent = agent
        self.agent = nil
        modelReference = nil
        draft = ""
        messages.removeAll()
        receiptMessages.removeAll()
        receiptIDs.removeAll()
        isConfigured = false
        PinkhaHanlinAccountOwner.shared.unregister(session.id)
        if dismissController { controller?.dismiss(animated: true, completion: completion) }
        closing = Task { [host] in
            await agent?.invalidate()
            await host.invalidate()
        }
    }
}

public enum PinkhaHanlinModelConfiguration {
    public static func make(endpoint: String, model: String, credential: String) throws -> HanlinChatModelConfiguration {
        let model = model.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: endpoint.trimmingCharacters(in: .whitespacesAndNewlines)),
              url.scheme == "https", let hostname = url.host, !hostname.isEmpty,
              url.user == nil, url.password == nil, url.query == nil, url.fragment == nil,
              !model.isEmpty, model.utf8.count <= 128, !credential.isEmpty, credential.utf8.count <= 4_096 else {
            throw HanlinHostError.invalidArguments
        }
        return .init(modelID: model, company: "OPENAI", apiType: "OpenAI", endpoint: url,
                     apiKey: credential, supportsToolUse: true)
    }
}

#endif
