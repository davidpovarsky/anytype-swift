import Foundation
import Services

/// Carries the already prepared document into the original property UI. This
/// owns no generation, store, editor or permission policy of its own.
@MainActor
final class OriginalEditorPropertyScope {
    static let valuePermissions: Set<EditorDocumentWritePermission> = [.editDetails, .editRelationValues]
    static let listPermissions: Set<EditorDocumentWritePermission> = [.editDetails, .editPropertiesList]

    let preparedSession: PreparedEditorPageSession
    let objectId: String
    let spaceId: String
    private let document: any BaseDocumentProtocol
    var owner: EditorDocumentWriteOwner { preparedSession.owner }

    init(preparedSession: PreparedEditorPageSession, objectId: String, spaceId: String,
         document: (any BaseDocumentProtocol)? = nil) {
        self.preparedSession = preparedSession
        self.objectId = objectId
        self.spaceId = spaceId
        self.document = document ?? preparedSession.document
    }

    func withCurrent<Value>(
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        _ operation: () throws -> Value
    ) throws -> Value {
        try owner.performSynchronousOperation(
            contextId: objectId, spaceId: spaceId, requiresEditing: false,
            requiredPermissions: requiredPermissions
        ) {
            try owner.validateDocument(document)
            return try operation()
        }
    }

    /// The original callback may synchronously schedule another write. Keep
    /// its named document-action admission; a read publication is deliberately
    /// unable to grant that authority to a descendant.
    func withActionCallback<Value>(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        _ operation: () throws -> Value
    ) throws -> Value {
        try owner.performSynchronousDocumentAction(
            contextId: objectId, spaceId: spaceId, requiredPermissions: requiredPermissions
        ) {
            try owner.validateDocument(document)
            return try operation()
        }
    }

    /// Reserve on the actual UI callback, before creating its original task.
    /// A rejected admission stays a failed write in the same capture barrier.
    func schedule(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) {
        let prepared = prepareAction(requiredPermissions: requiredPermissions, operation: operation)
        Task { try await prepared() }
    }

    func prepareAction(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) -> @MainActor @Sendable () async throws -> Void {
        do {
            let scheduled = try owner.scheduleDocumentAction(
                contextId: objectId, requiredPermissions: requiredPermissions
            )
            // If identity/Space validation fails after reservation, dropping
            // this original one-use handle records the abandoned write.
            try withCurrent {}
            return { try await scheduled.run(operation: operation) }
        } catch { return { throw error } }
    }

    func perform<Value: Sendable>(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @MainActor @Sendable () async throws -> Value
    ) async throws -> Value {
        return try await owner.performDocumentAction(
            contextId: objectId, requiredPermissions: requiredPermissions
        ) { [self] in
            try await withCurrent {}
            return try await operation()
        }
    }

    func originalProperties(_ service: any PropertiesServiceProtocol) throws -> any PropertiesServiceProtocol {
        try withCurrent { try OriginalPropertiesServiceBinding.requireOriginal(service) }
    }

    /// Different existing IDs acquire their own actual documents. The original
    /// selected array is passed to its one original native call only after all
    /// selected owners are retained in the same source/account ancestry.
    func withSelectedObjects<Value: Sendable>(
        ids: [String], requiredPermissions: Set<EditorDocumentWritePermission>,
        operation: @MainActor @Sendable () async throws -> Value
    ) async throws -> Value {
        try withCurrent {}
        guard !ids.isEmpty, !requiredPermissions.isEmpty,
              ids.allSatisfy({ !$0.isEmpty && !$0.utf8.contains(0) }) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        let preparation = try PreparedEditorChildPreparation(owner: owner)
        return try await retainSelectedObjects(
            ids: ids, index: 0, preparation: preparation,
            permissions: requiredPermissions, operation: operation
        )
    }

    private func retainSelectedObjects<Value: Sendable>(
        ids: [String], index: Int, preparation: PreparedEditorChildPreparation,
        permissions: Set<EditorDocumentWritePermission>,
        operation: @MainActor @Sendable () async throws -> Value
    ) async throws -> Value {
        guard index < ids.count else { return try await operation() }
        return try await preparation.performMutation(
            data: .init(objectId: ids[index], spaceId: spaceId),
            requiredPermissions: permissions
        ) { [self] child in
            let next = try await preparation.deriving(owner: child)
            return try await retainSelectedObjects(
                ids: ids, index: index + 1, preparation: next,
                permissions: permissions, operation: operation
            )
        }
    }
}

@MainActor
extension PropertyModuleConfiguration {
    var originalEditorScope: OriginalEditorPropertyScope? {
        preparedSession.map {
            OriginalEditorPropertyScope(preparedSession: $0, objectId: objectId, spaceId: spaceId)
        }
    }

    func scheduleOriginalPropertyAction(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) {
        if let scope = originalEditorScope {
            scope.schedule(requiredPermissions: requiredPermissions, operation: operation)
        } else {
            Task { try await operation() }
        }
    }

    func performOriginalPropertyAction<Value: Sendable>(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @MainActor @Sendable () async throws -> Value
    ) async throws -> Value {
        if let scope = originalEditorScope {
            return try await scope.perform(requiredPermissions: requiredPermissions, operation: operation)
        }
        return try await operation()
    }

    func prepareOriginalPropertyAction(
        requiredPermissions: Set<EditorDocumentWritePermission> = OriginalEditorPropertyScope.valuePermissions,
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) -> @MainActor @Sendable () async throws -> Void {
        originalEditorScope?.prepareAction(requiredPermissions: requiredPermissions, operation: operation) ?? operation
    }

    func originalPropertyButtonPreparation(
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) -> (@MainActor @Sendable () -> (@MainActor @Sendable () async throws -> Void))? {
        guard preparedSession != nil else { return nil }
        return { prepareOriginalPropertyAction(operation: operation) }
    }

    func withCurrentOriginalProperty<Value>(_ operation: () throws -> Value) throws -> Value {
        if let scope = originalEditorScope { return try scope.withCurrent(operation) }
        return try operation()
    }

    func withOriginalPropertyActionCallback<Value>(_ operation: () throws -> Value) throws -> Value {
        if let scope = originalEditorScope { return try scope.withActionCallback(operation) }
        return try operation()
    }

    func originalSelectedOptionsModel(_ model: any PropertySelectedOptionsModelProtocol) throws -> any PropertySelectedOptionsModelProtocol {
        if preparedSession != nil {
            guard let original = model as? PropertySelectedOptionsModel,
                  original.config.preparedSession === preparedSession,
                  original.config.objectId.utf8.elementsEqual(objectId.utf8),
                  original.config.spaceId.utf8.elementsEqual(spaceId.utf8),
                  original.config.relationKey.utf8.elementsEqual(relationKey.utf8) else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
        }
        return model
    }

    func originalPropertiesService(_ service: any PropertiesServiceProtocol) throws -> any PropertiesServiceProtocol {
        if let scope = originalEditorScope { return try scope.originalProperties(service) }
        return service
    }
}
