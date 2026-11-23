import Foundation
import AnytypeCore
import ProtobufMessages
@preconcurrency import Combine
import Services

protocol AccountEventHandlerProtocol: Sendable {
    func startSubscription() async
    func stopSubscription() async
    
    var accountShowPublisher: AnyPublisher<String, Never> { get async }
    var accountStatusPublisher: AnyPublisher<AccountStatus, Never> { get async }
}

actor AccountEventHandler: AccountEventHandlerProtocol, OriginalEmbeddedAccountEventRegistration {
    
    private var cancellable: AnyCancellable?
    // Embedded preparation retains one actual original registration task.
    // Concurrent callers share its result; no duplicate handler is installed.
    private var embeddedRegistrationGeneration = UUID()
    private var pendingEmbeddedRegistration: (id: UUID, task: Task<OriginalEmbeddedAccountEventInstallation, Error>)?
    private var embeddedInstallation: OriginalEmbeddedAccountEventInstallation?

    @Injected(\.accountManager)
    private var accountManager: any AccountManagerProtocol
    
    private let accountShowSubject = PassthroughSubject<String, Never>()
    private let accountStatusSubject = PassthroughSubject<AccountStatus, Never>()
    
    // MARK: - AccountEventHandlerProtocol
    
    var accountShowPublisher: AnyPublisher<String, Never> {
        return accountShowSubject.eraseToAnyPublisher()
    }
    
    var accountStatusPublisher: AnyPublisher<AccountStatus, Never> {
        return accountStatusSubject.eraseToAnyPublisher()
    }
    
    func startSubscription() async {
        if OriginalRuntimeEnvironment.mode == .embeddedEditor {
            // The closed bootstrap calls the throwing path below and checks
            // its actual installation capture before wallet recovery.
            _ = try? await startEmbeddedSubscription()
            return
        }
        guard cancellable == nil else { return }
        
        cancellable = EventBunchSubscribtion.default.addHandler { [weak self] events in
            await self?.handle(events: events)
        }
    }
    
    func stopSubscription() {
        if OriginalRuntimeEnvironment.mode == .embeddedEditor {
            embeddedRegistrationGeneration = UUID()
            pendingEmbeddedRegistration?.task.cancel()
            pendingEmbeddedRegistration = nil
            embeddedInstallation?.retire()
            embeddedInstallation = nil
        }
        cancellable = nil
    }
    
    func startEmbeddedSubscription() async throws -> EditorDocumentWriteCapture {
        guard OriginalRuntimeEnvironment.mode == .embeddedEditor else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
        try Task.checkCancellation()
        if let installation = embeddedInstallation {
            try installation.capture.validate()
            return installation.capture
        }
        // An unproven legacy cancellation token is never registration evidence.
        guard cancellable == nil else { throw EditorDocumentWriteError.rejected(.retired) }
        let registration: (id: UUID, task: Task<OriginalEmbeddedAccountEventInstallation, Error>)
        if let pending = pendingEmbeddedRegistration {
            registration = pending
        } else {
            let id = UUID()
            let generation = embeddedRegistrationGeneration
            let task = Task { [self] in
                try await installEmbeddedRegistration(id: id, generation: generation)
            }
            registration = (id, task)
            pendingEmbeddedRegistration = registration
        }
        let installation = try await registration.task.value
        try Task.checkCancellation()
        guard embeddedInstallation === installation else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
        try installation.capture.validate()
        return installation.capture
    }

    private func installEmbeddedRegistration(id: UUID, generation: UUID) async throws -> OriginalEmbeddedAccountEventInstallation {
        defer {
            if pendingEmbeddedRegistration?.id == id { pendingEmbeddedRegistration = nil }
        }
        let subscription = await EventBunchSubscribtion.default.addHandlerAwaiting { [weak self] events in
            await self?.handle(events: events)
        }
        let installation = try OriginalEmbeddedAccountEventInstallation(subscription: subscription)
        guard !Task.isCancelled, embeddedRegistrationGeneration == generation,
              pendingEmbeddedRegistration?.id == id, embeddedInstallation == nil else {
            installation.retire()
            throw EditorDocumentWriteError.rejected(.retired)
        }
        cancellable = subscription
        embeddedInstallation = installation
        return installation
    }

    // MARK: - Private
    
    private func handle(events: EventsBunch) {
        for event in events.middlewareEvents {
            switch event.value {
            case let .accountShow(data):
                accountShowSubject.send(data.account.id)
            case let .accountUpdate(data):
                if data.hasStatus, let status = try? data.status.asModel() {
                    handleStatus(status)
                }
                // Other account events
            case .accountDetails,
                    .accountConfigUpdate:
                break
            default:
                break
            }
        }
    }
    
    private func handleStatus(_ newStatus: AccountStatus) {
        
        let currentStatus = accountManager.account.status
        guard currentStatus != newStatus else { return }
        accountManager.account.status = newStatus
        
        accountStatusSubject.send(newStatus)
    }
}

// Internal source-readiness seam. It grants no native/account authority.
protocol OriginalEmbeddedAccountEventRegistration: Sendable {
    func startEmbeddedSubscription() async throws -> EditorDocumentWriteCapture
}

private final class OriginalEmbeddedAccountEventInstallation: @unchecked Sendable {
    let capture: EditorDocumentWriteCapture
    private let lifetime: EditorDocumentWriteLifetime
    private let subscription: AnyCancellable

    init(subscription: AnyCancellable) throws {
        let lifetime = EditorDocumentWriteLifetime()
        self.capture = try EditorDocumentWriteCapture(lifetime)
        self.lifetime = lifetime
        self.subscription = subscription
    }

    func retire() {
        lifetime.markUnavailable()
        subscription.cancel()
    }

    deinit { retire() }
}
