import Foundation
import AnytypeCore
import ProtobufMessages
@preconcurrency import Combine

protocol FileErrorEventHandlerProtocol: AnyObject, Sendable {
    var fileLimitReachedPublisher: AnyPublisher<Void, Never> { get async }
    
    func startSubscription() async
}

actor FileErrorEventHandler: FileErrorEventHandlerProtocol, OriginalEmbeddedFileEventRegistration {
    
    // MARK: - Private properties
    
    private let fileLimitReachedSubject = PassthroughSubject<Void, Never>()
    private var cancellable: AnyCancellable?
    // Embedded preparation retains one actual original registration task.
    // Concurrent callers share its result; no duplicate handler is installed.
    private var embeddedRegistrationGeneration = UUID()
    private var pendingEmbeddedRegistration: (id: UUID, task: Task<OriginalEmbeddedFileEventInstallation, Error>)?
    private var embeddedInstallation: OriginalEmbeddedFileEventInstallation?

    
    // MARK: - FileErrorEventHandlerProtocol
    
    var fileLimitReachedPublisher: AnyPublisher<Void, Never> {
        fileLimitReachedSubject.eraseToAnyPublisher()
    }
    
    func startSubscription() async {
        if OriginalRuntimeEnvironment.deploymentMode == .embeddedEditor {
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
    
    func startEmbeddedSubscription() async throws -> EditorDocumentWriteCapture {
        guard OriginalRuntimeEnvironment.deploymentMode == .embeddedEditor else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
        try Task.checkCancellation()
        if let installation = embeddedInstallation {
            try installation.capture.validate()
            return installation.capture
        }
        // An unproven legacy cancellation token is never registration evidence.
        guard cancellable == nil else { throw EditorDocumentWriteError.rejected(.retired) }
        let registration: (id: UUID, task: Task<OriginalEmbeddedFileEventInstallation, Error>)
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

    private func installEmbeddedRegistration(id: UUID, generation: UUID) async throws -> OriginalEmbeddedFileEventInstallation {
        defer {
            if pendingEmbeddedRegistration?.id == id { pendingEmbeddedRegistration = nil }
        }
        let subscription = await EventBunchSubscribtion.default.addHandlerAwaiting { [weak self] events in
            await self?.handle(events: events)
        }
        let installation = try OriginalEmbeddedFileEventInstallation(subscription: subscription)
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
            case .fileLimitReached:
                fileLimitReachedSubject.send(())
            default:
                break
            }
        }
    }
}

// Internal source-readiness seam. It grants no native/account authority.
protocol OriginalEmbeddedFileEventRegistration: Sendable {
    func startEmbeddedSubscription() async throws -> EditorDocumentWriteCapture
}

private final class OriginalEmbeddedFileEventInstallation: @unchecked Sendable {
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
