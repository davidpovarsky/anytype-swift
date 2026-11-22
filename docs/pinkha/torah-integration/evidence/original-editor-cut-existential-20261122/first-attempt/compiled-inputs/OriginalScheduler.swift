import Foundation

extension BlockActionHandlerProtocol {
    var documentWriteOwner: EditorDocumentWriteOwner? { nil }
    var documentWriteContextID: String { "" }

    /// Register on the UI call stack, before the original asynchronous edit can
    /// wait in the MainActor queue. The same Owner retains real RPC completion.
    @discardableResult
    func scheduleMutationTask<Value: Sendable>(
        operation: @escaping @MainActor @Sendable () async throws -> Value
    ) -> Task<Value, Error> {
        scheduleOriginalEditorMutation(
            owner: documentWriteOwner,
            contextId: documentWriteContextID,
            operation: operation
        )
    }

}

/// This helper adds no write authority or second queue. A registered operation
/// still traverses the original service and Invocation boundaries. In particular,
/// an optimistic document event is never the completion of this registration.
@MainActor
@discardableResult
func scheduleOriginalEditorMutation<Value: Sendable>(
    owner: EditorDocumentWriteOwner?,
    contextId: String,
    requiredPermissions: Set<EditorDocumentWritePermission> = [],
    operation: @escaping @MainActor @Sendable () async throws -> Value
) -> Task<Value, Error> {
    guard let owner else {
        return Task { @MainActor in try await operation() }
    }
    do {
        let scheduled = try owner.scheduleMutation(contextId: contextId, requiredPermissions: requiredPermissions)
        return Task { @MainActor in try await scheduled.run(operation: operation) }
    } catch {
        // A rejected UI intent must not start its original mutation later.
        return Task { throw error }
    }
}
