import Foundation
import Observation
import TorahInspectorCore

struct AnyNativeSourceDocumentsRead: Sendable {
    let documents: [TorahRelatedDocument]
    let title: String
    let complete: Bool
}

/// Owns only the Properties result presentation. The caller retains the real
/// native read, current permissions, account/run lease and mounted-document gate.
@MainActor @Observable
final class AnyNativeSourceDocumentsPresentation {
    var documents: [TorahRelatedDocument] = []
    var title: String?
    private(set) var isLoading = false

    private struct Request: Equatable {
        let documentOwner: UUID
        let presentation: UUID
        let id: UUID
    }
    @ObservationIgnored private var documentOwner: UUID?
    @ObservationIgnored private var presentation: UUID?
    @ObservationIgnored private var request: Request?
    @ObservationIgnored private var task: Task<Void, Never>?

    /// A reopened Properties sheet is a new owner even on the same document.
    /// The returned cancelled task joins the document's existing drain list.
    @discardableResult
    func beginPresentation(documentOwner: UUID) -> Task<Void, Never>? {
        let closing = retire()
        self.documentOwner = documentOwner
        presentation = UUID()
        return closing
    }

    @discardableResult
    func retire() -> Task<Void, Never>? {
        documentOwner = nil
        presentation = nil
        request = nil
        isLoading = false
        documents = []
        title = nil
        let closing = task
        task = nil
        closing?.cancel()
        return closing
    }

    /// Called synchronously by the tap action. Ownership is captured before
    /// creating the Task, so a queued old tap cannot borrow a reopened sheet.
    @discardableResult
    func load(
        documentOwner: UUID,
        read: @escaping @MainActor () async throws -> AnyNativeSourceDocumentsRead,
        isOwnerCurrent: @escaping @MainActor () -> Bool,
        canPresent: @escaping @MainActor () -> Bool,
        didComplete: @escaping @MainActor (Result<Bool, Error>) -> Void,
        didFinish: @escaping @MainActor () -> Void
    ) -> Task<Void, Never>? {
        guard self.documentOwner == documentOwner, let presentation,
              request == nil, title == nil, isOwnerCurrent(), canPresent() else { return nil }
        let captured = Request(documentOwner: documentOwner, presentation: presentation, id: UUID())
        request = captured
        isLoading = true
        let started = Task { @MainActor [weak self] in
            guard let self else { return }
            defer {
                if self.owns(captured), isOwnerCurrent() {
                    self.request = nil
                    self.task = nil
                    self.isLoading = false
                    didFinish()
                }
            }
            guard self.owns(captured), isOwnerCurrent(), canPresent(), !Task.isCancelled else { return }
            do {
                let result = try await read()
                guard self.owns(captured), isOwnerCurrent(), canPresent(),
                      self.title == nil, !Task.isCancelled else { return }
                self.documents = result.documents
                self.title = result.title
                didComplete(.success(result.complete))
            } catch is CancellationError {
                // Cancellation retires this consumer, not native authority.
            } catch {
                guard self.owns(captured), isOwnerCurrent(), canPresent(),
                      self.title == nil, !Task.isCancelled else { return }
                didComplete(.failure(error))
            }
        }
        task = started
        return started
    }

    private func owns(_ captured: Request) -> Bool {
        documentOwner == captured.documentOwner && presentation == captured.presentation && request == captured
    }
}
