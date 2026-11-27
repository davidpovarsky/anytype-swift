#if canImport(UIKit)
import PinkhaHanlinCore
import Foundation
import Observation
import UIKit
import HanlinAgentCore
import HanlinChatCore
import HanlinHostContracts
import HanlinPersistenceAdapters
import HanlinAgentActivityCore
import HanlinPresentationKit

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
    private(set) var activities: [UUID: PinkhaHanlinMessageActivity] = [:]

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
    private var receiptState: PinkhaHanlinReceiptPresentationState
    private var requiresReconciliation: Bool { receiptState.requiresReconciliation }
    @ObservationIgnored private var closing: Task<Void, Never>?
    @ObservationIgnored private var closed = false
    private let speech = PinkhaHanlinMessageSpeech()
    @ObservationIgnored public private(set) var returnReceipt: PinkhaHanlinNavigationHandoff?

    private var canStartRun: Bool {
        isConfigured && !closed && !isStreaming && !isStopping && receiptState.permitsNewRun
            && currentRunID == nil
    }
    public var canSend: Bool {
        canStartRun && !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && draft.utf8.count <= 32_768 && messages.count <= 254
    }
    public var canModifyTranscript: Bool {
        !closed && !isStreaming && !isStopping && currentRunID == nil
    }
    public var hasSource: Bool { session.context.objectReference != nil }

    public init(host: any PinkhaHanlinPresentationHost, presenter: UIViewController,
                appearance: PinkhaHanlinAppearance = .system,
                hooks: PinkhaHanlinPresentationHooks = .init()) throws {
        self.host = host
        self.session = host.session
        self.receiptState = .init(session: host.session)
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
        guard canSend else { return }
        let prompt = draft
        draft = ""
        messages.append(.user(prompt))
        startRun()
    }

    /// A UI action is bound to an actual message in this mounted, account-owned
    /// presentation. An old menu/preview cannot act after account or source loss.
    public func canAccessMessage(_ id: UUID) -> Bool {
        !closed && messages.contains(where: { $0.id == id })
            && (try? validateInstallation(for: session)) != nil
    }

    @discardableResult
    public func copyMessage(_ id: UUID, selection: String? = nil) -> Bool {
        guard canAccessMessage(id), let message = messages.first(where: { $0.id == id }) else { return false }
        // Selection text is emitted by the original Markdown selection surface.
        // It remains local and is never treated as a command or tool permission.
        UIPasteboard.general.string = selection ?? message.content
        return true
    }

    public func isSpeaking(_ id: UUID) -> Bool { speech.messageID == id }

    public func speak(_ id: UUID) {
        guard canAccessMessage(id), let message = messages.first(where: { $0.id == id }) else { return }
        speech.toggle(messageID: id, text: message.content,
                      localeIdentifier: session.context.localeIdentifier)
    }

    public func deleteMessage(_ id: UUID) {
        guard canModifyTranscript, canAccessMessage(id) else { return }
        if speech.messageID == id { speech.stop() }
        messages.removeAll { $0.id == id }
        activities[id] = nil
        // Native effect receipts and the unresolved-write barrier are not
        // deleted with a transcript row and never imply native rollback.
    }

    public func canRepeatResponse(_ id: UUID) -> Bool {
        guard canStartRun, canAccessMessage(id), let last = messages.last,
              last.id == id, last.role == "assistant" else { return false }
        return messages.dropLast().last?.role == "user"
    }

    public func canContinueResponse(_ id: UUID) -> Bool {
        canRepeatResponse(id) && messages.count <= 254 && messages.last?.content.isEmpty == false
    }

    public func retryMessage(_ id: UUID) {
        guard canRepeatResponse(id) else { return }
        if speech.messageID == id { speech.stop() }
        messages.removeLast()
        activities[id] = nil
        // This explicit user action uses the same SDK and fresh native consent.
        // It never repeats an uncertain operation, and it preserves the draft.
        startRun()
    }

    public func continueResponse(_ id: UUID) {
        guard canContinueResponse(id) else { return }
        messages.append(.user(PinkhaHanlinStrings.continuePrompt))
        startRun()
    }

    func openSource(_ source: HanlinSourceReference, messageID: UUID) {
        guard canAccessMessage(messageID), let sourceURL = source.url,
              activities[messageID]?.sources.contains(source) == true else { return }
        UIApplication.shared.open(sourceURL)
    }

    private func startRun() {
        guard canStartRun, messages.count < 256, let agent, let modelReference else { return }
        let history = messages.map { HanlinAISDKMessage(role: $0.role == "user" ? .user : .assistant, text: $0.content) }
        let answerID = UUID()
        let runID = UUID()
        currentRunID = runID
        messages.append(.init(id: answerID, role: "assistant", content: ""))
        activities[answerID] = .init(session: session, messageID: answerID)
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
                    if !self.isStopping, self.currentRunID == runID {
                        guard var activity = self.activities[answerID] else { throw HanlinHostError.staleContext }
                        try activity.consume(event.event, session: event.session,
                                             runID: event.runID, sequence: event.sequence)
                        self.activities[answerID] = activity
                        if case .textDelta(let delta) = event.event,
                           let index = self.messages.firstIndex(where: { $0.id == answerID }) {
                            guard self.messages[index].content.utf8.count + delta.utf8.count <= 262_144 else {
                                throw HanlinHostError.outputLimitExceeded
                            }
                            self.messages[index].content += delta
                        }
                    }
                }
                if !self.closed, !self.isStopping, self.currentRunID == runID {
                    self.activities[answerID]?.finish(status: .completed)
                }
            } catch {
                // Provider errors may contain request details. Never log or expose them verbatim.
                if !self.closed, !self.isStopping, self.currentRunID == runID {
                    // A local projection/output limit can end the consumer before
                    // producer EOF. Retain the run fence until the original SDK
                    // and native workers have drained, just as the Stop path does.
                    if (error as? HanlinHostError) == .unresolvedWrite { self.receiptState.requireReconciliation() }
                    do {
                        let result = try await agent.cancelCurrentRun()
                        if result?.requiresReconciliation == true { self.receiptState.requireReconciliation() }
                    } catch {
                        self.receiptState.requireReconciliation()
                    }
                    guard !self.closed, !self.isStopping, self.currentRunID == runID else { return }
                    self.activities[answerID]?.finish(status: .failed)
                    self.errorMessage = self.requiresReconciliation
                        ? PinkhaHanlinStrings.uncertain : PinkhaHanlinStrings.requestFailed
                }
            }
        }
    }

    public func stop() {
        guard !closed, isStreaming, !isStopping, let agent, let runID = currentRunID else { return }
        isStopping = true
        errorMessage = nil
        let consumer = running
        let answerID = messages.last?.id
        stopping = Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                let result = try await agent.cancelCurrentRun()
                await consumer?.value
                guard !self.closed, self.currentRunID == runID else { return }
                try self.validateInstallation(for: self.session)
                if result?.requiresReconciliation == true { self.receiptState.requireReconciliation() }
                if self.requiresReconciliation { self.errorMessage = PinkhaHanlinStrings.uncertain }
            } catch {
                await consumer?.value
                guard !self.closed, self.currentRunID == runID else { return }
                // A failed metadata save or uncertain host outcome cannot silently
                // restore permission to retry the operation in this conversation.
                self.receiptState.requireReconciliation()
                self.errorMessage = PinkhaHanlinStrings.uncertain
            }
            guard !self.closed, self.currentRunID == runID else { return }
            if let answerID { self.activities[answerID]?.finish(status: .cancelled) }
            self.isStopping = false
            self.isStreaming = false
            self.running = nil
            self.stopping = nil
            self.currentRunID = nil
        }
    }

    private func receive(_ event: HanlinHostResultEvent) {
        guard !closed else { return }
        let appendDisplayLabel = receiptState.observe(event)
        if requiresReconciliation { errorMessage = PinkhaHanlinStrings.uncertain }
        guard appendDisplayLabel else { return }
        // The presentation owns only safe outcome labels; payloads never enter a receipt log.
        switch event.result.effectState {
        case .confirmedCommitted: receiptMessages.append(PinkhaHanlinStrings.pageCreated)
        case .uncertain:
            receiptMessages.append(PinkhaHanlinStrings.uncertain)
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
        let consumer = running
        let stop = stopping
        consumer?.cancel()
        currentRunID = nil
        isStreaming = false
        isStopping = false
        let agent = agent
        self.agent = nil
        speech.stop()
        modelReference = nil
        draft = ""
        messages.removeAll()
        activities.removeAll()
        receiptMessages.removeAll()
        isConfigured = false
        PinkhaHanlinAccountOwner.shared.unregister(session.id)
        if dismissController { controller?.dismiss(animated: true, completion: completion) }
        closing = Task { [host] in
            await agent?.invalidate()
            await host.invalidate()
            // A close during Stop joins the same original stream/persistence
            // boundary before the account owner may release this presentation.
            await stop?.value
            await consumer?.value
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
