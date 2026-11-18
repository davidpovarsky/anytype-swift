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
final class PinkhaHanlinChatPresentation {
    let session: HanlinHostSession
    var draft = ""
    private(set) var messages: [HanlinChatMessage] = []
    private(set) var receiptMessages: [String] = []
    private(set) var isStreaming = false
    private(set) var isConfigured = false
    private(set) var readAllowed = false
    private(set) var isReturningToSource = false
    private(set) var errorMessage: String?

    @ObservationIgnored private let host: PinkhaHanlinReadWriteHost
    @ObservationIgnored private weak var controller: PinkhaHanlinChatController?
    @ObservationIgnored private weak var scene: UIWindowScene?
    @ObservationIgnored private var agent: HanlinAgentSession?
    @ObservationIgnored private var modelReference: HanlinModelReference?
    @ObservationIgnored private var running: Task<Void, Never>?
    @ObservationIgnored private var closed = false
    @ObservationIgnored private var receiptIDs = Set<UUID>()
    @ObservationIgnored private(set) var returnReceipt: PinkhaHanlinNavigationHandoff?
    #if DEBUG && targetEnvironment(simulator)
    @ObservationIgnored private weak var acceptanceSource: UIViewController?
    @ObservationIgnored private weak var acceptanceRouteOwner: SpaceHubCoordinatorViewModel?
    #endif

    var canSend: Bool {
        isConfigured && !closed && !isStreaming && !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && draft.utf8.count <= 32_768 && messages.count < 256
    }
    var hasSource: Bool { session.context.objectReference != nil }

    init(presenter: UIViewController, routeOwner: SpaceHubCoordinatorViewModel,
         conversationID: UUID, locale: Locale) throws {
        let host = try PinkhaHanlinReadWriteHost.make(presenter: presenter, routeOwner: routeOwner,
            conversationID: conversationID, locale: locale)
        self.host = host
        self.session = host.session
        self.scene = presenter.viewIfLoaded?.window?.windowScene
        #if DEBUG && targetEnvironment(simulator)
        self.acceptanceSource = presenter
        self.acceptanceRouteOwner = routeOwner
        #endif
        try PinkhaHanlinAccountOwner.shared.register(self)
        host.observeInvalidation { [weak self] in
            #if DEBUG && targetEnvironment(simulator)
            if let self {
                PinkhaHanlinNativeAcceptanceDriver.observedInvalidation(sessionID: self.session.id, cause: "nativeAuthorityChanged")
            }
            #endif
            self?.invalidate()
        }
    }

    func didMount(_ controller: PinkhaHanlinChatController) {
        guard !closed else { controller.dismiss(animated: false); return }
        self.controller = controller
        do {
            try host.install(self, controller: controller)
            #if DEBUG && targetEnvironment(simulator)
            PinkhaHanlinNativeAcceptanceDriver.startIfRequested(host: host, presentation: self,
                controller: controller, source: acceptanceSource, routeOwner: acceptanceRouteOwner)
            PinkhaHanlinSelectionAcceptanceDriver.startIfRequested(host: host, presentation: self,
                controller: controller, source: acceptanceSource)
            #endif
        }
        catch { invalidate() }
    }

    func validateInstallation(for session: HanlinHostSession) throws {
        guard !closed, self.session == session,
              PinkhaHanlinAccountOwner.shared.owns(self),
              PinkhaHanlinAccountOwner.shared.isAvailable(account: session.context.namespace.account),
              let scene, let controller, controller.presentation === self,
              controller.presentingViewController != nil,
              controller.viewIfLoaded?.window?.windowScene === scene,
              scene.activationState == .foregroundActive,
              !controller.isBeingDismissed else { throw HanlinHostError.staleContext }
    }

    /// Credentials are supplied explicitly by the user and live only inside this presentation's
    /// canonical engine. No Keychain/AppGroup discovery, request logging or cross-app credential read.
    func configure(endpoint: String, model: String, credential: String) {
        guard !closed, !isConfigured, !isStreaming else { return }
        do {
            try validateInstallation(for: session)
            let configuration = try PinkhaHanlinModelConfiguration.make(endpoint: endpoint, model: model, credential: credential)
            let engine = try HanlinAISDKAgentEngine(configuration: configuration,
                fetch: HanlinAISDKProviderFactory.makeFetch(sessionConfiguration: .ephemeral))
            let agent = HanlinAgentSession(identity: session, host: host, engine: engine,
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

    func requestContextReadConsent() {
        guard !closed, !isStreaming, hasSource else { return }
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

    func send() {
        guard canSend, let agent, let modelReference else { return }
        let prompt = draft
        draft = ""
        messages.append(.user(prompt))
        let history = messages.map { HanlinAISDKMessage(role: $0.role == "user" ? .user : .assistant, text: $0.content) }
        let answerID = UUID()
        messages.append(.init(id: answerID, role: "assistant", content: ""))
        isStreaming = true
        errorMessage = nil
        running = Task { @MainActor [weak self] in
            guard let self else { return }
            defer { self.isStreaming = false; self.running = nil }
            do {
                try self.validateInstallation(for: self.session)
                let stream = try await agent.stream(messages: history, modelReference: modelReference,
                    maxSteps: 8, presentationReference: "anytype.hanlin@1")
                for try await event in stream {
                    try Task.checkCancellation()
                    try self.validateInstallation(for: event.session)
                    if case .textDelta(let delta) = event.event,
                       let index = self.messages.firstIndex(where: { $0.id == answerID }) {
                        guard self.messages[index].content.utf8.count + delta.utf8.count <= 262_144 else {
                            throw HanlinHostError.outputLimitExceeded
                        }
                        self.messages[index].content += delta
                    }
                }
            } catch {
                // Provider errors may contain request details. Never log or expose them verbatim.
                if !self.closed { self.errorMessage = PinkhaHanlinStrings.requestFailed }
            }
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
    func returnToSource() {
        guard !closed, !isReturningToSource, let object = session.context.objectReference else { return }
        isReturningToSource = true
        Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                try validateInstallation(for: session)
                let selection = session.context.selectionReferences
                let destination = HanlinHostDestination(context: session.context, objectReference: object,
                    blockReference: selection.count == 1 ? selection.first : nil)
                let queued = try await host.open(destination)
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

    func invalidate() {
        close(completion: nil)
    }

    private func close(completion: (@MainActor @Sendable () -> Void)?) {
        guard !closed else { return }
        #if DEBUG && targetEnvironment(simulator)
        PinkhaHanlinNativeAcceptanceDriver.observedInvalidation(sessionID: session.id, cause: "explicitCloseOrOwner")
        #endif
        closed = true
        host.revokePresentation()
        running?.cancel()
        let agent = agent
        self.agent = nil
        modelReference = nil
        draft = ""
        messages.removeAll()
        receiptMessages.removeAll()
        receiptIDs.removeAll()
        isConfigured = false
        PinkhaHanlinAccountOwner.shared.unregister(session.id)
        controller?.dismiss(animated: true, completion: completion)
        Task { [host] in
            await agent?.invalidate()
            await host.invalidate()
        }
    }
}

enum PinkhaHanlinModelConfiguration {
    static func make(endpoint: String, model: String, credential: String) throws -> HanlinChatModelConfiguration {
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
