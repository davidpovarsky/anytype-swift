import Foundation

enum EditorDocumentWriteRejection: Sendable, Equatable {
    case retired
    case wrongContext
    case documentChanged
    case notHandling
    case notEditable
    case cancelled
    case invalidLease
}

enum EditorDocumentWriteError: Error, Sendable, Equatable {
    case rejected(EditorDocumentWriteRejection)
    case completedWithoutOwnership(EditorDocumentWriteRejection)
}

@MainActor
final class EditorDocumentWriteOwner {
    private let data: EditorPageObject
    private let document: any BaseDocumentProtocol
    private var accepting = true
    private var pending = Set<UUID>()
    private var onDrained: (@MainActor () -> Void)?
    private struct LifetimeBinding {
        let source: EditorDocumentWriteLifetime
        let token: EditorDocumentWriteLifetime.Token
        let observation: EditorDocumentWriteLifetime.Observation
    }
    private var lifetimeBindings: [LifetimeBinding] = []
    private var documentLifetimeSource: EditorDocumentWriteLifetime?

    var isRetired: Bool { !accepting || !lifetimeIsCurrent }
    var pendingOperationCount: Int { pending.count }
    var isDrained: Bool { pending.isEmpty }

    init(
        data: EditorPageObject,
        document: any BaseDocumentProtocol,
        onDrained: (@MainActor () -> Void)? = nil
    ) throws {
        try PreparedEditorPageDocument.validate(data: data, document: document)
        self.data = data
        self.document = document
        self.onDrained = onDrained
        guard exactSourceMatches() else {
            throw EditorDocumentWriteError.rejected(.documentChanged)
        }
    }

    convenience init(
        data: EditorPageObject,
        lifetimeDocument: any BaseDocumentProtocol & EditorDocumentWriteLifetimeProviding,
        sessionLifetime: EditorDocumentWriteLifetime? = nil,
        onDrained: (@MainActor () -> Void)? = nil
    ) throws {
        let sources = [lifetimeDocument.editorWriteLifetime] + (sessionLifetime.map { [$0] } ?? [])
        let captured = try sources.map { source -> (EditorDocumentWriteLifetime, EditorDocumentWriteLifetime.Token) in
            guard let token = source.token() else {
                throw EditorDocumentWriteError.rejected(.retired)
            }
            return (source, token)
        }
        try self.init(data: data, document: lifetimeDocument, onDrained: onDrained)
        self.documentLifetimeSource = captured.first?.0
        for (source, token) in captured {
            let observation = source.observe(token) { [weak self] in
                // Generation checks are synchronous. This hop only delivers
                // retirement/drain notification to the original MainActor owner.
                Task { @MainActor [weak self] in self?.refreshLifetime() }
            }
            lifetimeBindings.append(.init(source: source, token: token, observation: observation))
        }
        try validateOwnership()
    }

    func validateOwnership() throws {
        if let reason = rejection(contextId: data.objectId, requiresEditing: false) {
            throw EditorDocumentWriteError.rejected(reason)
        }
    }

    func retire() {
        accepting = false
        for binding in lifetimeBindings { binding.observation.cancel() }
        lifetimeBindings.removeAll()
        notifyDrainIfNeeded()
    }

    func performMutation<Value: Sendable>(
        contextId: String,
        operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        let lease = try admit(contextId: contextId, requiresEditing: true)
        defer { finish(lease) }
        let value = try await operation()
        if let reason = rejection(contextId: contextId, requiresEditing: true) {
            throw EditorDocumentWriteError.completedWithoutOwnership(reason)
        }
        guard pending.contains(lease) else {
            throw EditorDocumentWriteError.completedWithoutOwnership(.invalidLease)
        }
        return value
    }

    func performPublication(
        contextId: String,
        requiresEditing: Bool = true,
        operation: @Sendable () async -> Void
    ) async {
        guard let lease = try? admit(contextId: contextId, requiresEditing: requiresEditing) else { return }
        defer { finish(lease) }
        await operation()
        refreshLifetime()
    }

    private func admit(contextId: String, requiresEditing: Bool) throws -> UUID {
        if let reason = rejection(contextId: contextId, requiresEditing: requiresEditing) {
            throw EditorDocumentWriteError.rejected(reason)
        }
        let lease = UUID()
        guard pending.insert(lease).inserted else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        return lease
    }

    private func rejection(contextId: String, requiresEditing: Bool) -> EditorDocumentWriteRejection? {
        refreshLifetime()
        if Task.isCancelled { return .cancelled }
        guard accepting else { return .retired }
        guard contextId.utf8.elementsEqual(data.objectId.utf8) else { return .wrongContext }
        do {
            try PreparedEditorPageDocument.validate(data: data, document: document)
        } catch {
            return .documentChanged
        }
        guard exactSourceMatches() else { return .documentChanged }
        if requiresEditing {
            guard data.mode == .handling else { return .notHandling }
            guard !document.isLocked, document.permissions.canEditBlocks else { return .notEditable }
        }
        return nil
    }

    private var lifetimeIsCurrent: Bool {
        if let documentLifetimeSource {
            guard let provider = document as? any EditorDocumentWriteLifetimeProviding,
                  provider.editorWriteLifetime === documentLifetimeSource else { return false }
        }
        return lifetimeBindings.allSatisfy { $0.source.isCurrent($0.token) }
    }

    private func refreshLifetime() {
        if !lifetimeIsCurrent { retire() }
    }

    private func exactSourceMatches() -> Bool {
        guard document.objectId.utf8.elementsEqual(data.objectId.utf8),
              document.spaceId.utf8.elementsEqual(data.spaceId.utf8) else { return false }
        switch (data.mode, document.mode) {
        case (.handling, .handling), (.preview, .preview):
            return true
        case let (.version(expected), .version(actual)):
            return actual.utf8.elementsEqual(expected.utf8)
        default:
            return false
        }
    }

    private func finish(_ lease: UUID) {
        guard pending.remove(lease) != nil else { return }
        notifyDrainIfNeeded()
    }

    private func notifyDrainIfNeeded() {
        guard !accepting, pending.isEmpty else { return }
        let callback = onDrained
        onDrained = nil
        callback?()
    }
}
