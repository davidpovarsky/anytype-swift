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

    var isRetired: Bool { !accepting }
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

    func retire() {
        accepting = false
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
