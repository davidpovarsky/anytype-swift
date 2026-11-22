import UIKit
import AnytypeCore
import Services

@MainActor
@Observable
final class UndoRedoViewModel {

    private let objectActionsService: any ObjectActionsServiceProtocol
    @ObservationIgnored
    private let documentWriteOwner: EditorDocumentWriteOwner?

    private let objectId: String

    var toastData: ToastBarData?
    
    init(
        objectId: String,
        objectActionsService: any ObjectActionsServiceProtocol = Container.shared.objectActionsService(),
        documentWriteOwner: EditorDocumentWriteOwner? = nil
    ) {
        self.objectId = objectId
        self.objectActionsService = objectActionsService
        self.documentWriteOwner = documentWriteOwner
    }

    var hasDocumentWriteOwner: Bool { documentWriteOwner != nil }

    /// Called by the original button synchronously, before its SwiftUI task.
    func prepareUndo() -> @MainActor @Sendable () async throws -> Void {
        prepareMutation { [self] in try await undo() }
    }

    func prepareRedo() -> @MainActor @Sendable () async throws -> Void {
        prepareMutation { [self] in try await redo() }
    }

    private func prepareMutation(
        operation: @escaping @MainActor @Sendable () async throws -> Void
    ) -> @MainActor @Sendable () async throws -> Void {
        guard let documentWriteOwner else { return operation }
        do {
            let scheduled = try documentWriteOwner.scheduleMutation(
                contextId: objectId, requiredPermissions: [.undoRedo]
            )
            return { try await scheduled.run(operation: operation) }
        } catch {
            // scheduleMutation records a rejected edit in the same Owner.
            return { throw error }
        }
    }

    private func performMutation(operation: @Sendable () async throws -> Void) async throws {
        if let documentWriteOwner {
            try await documentWriteOwner.performMutation(
                contextId: objectId, requiredPermissions: [.undoRedo], operation: operation
            )
        } else {
            try await operation()
        }
    }

    private func publish(_ operation: () -> Void) throws {
        if let documentWriteOwner {
            try documentWriteOwner.performSynchronousOperation(
                contextId: objectId, requiresEditing: false, requiredPermissions: [.undoRedo], operation: operation
            )
        } else {
            operation()
        }
    }

    func undo() async throws {
        do {
            let service = objectActionsService, objectId = objectId
            let requiresOriginalDelegate = documentWriteOwner != nil
            try await performMutation {
                let original = requiresOriginalDelegate ? try OriginalObjectActionsServiceBinding.requireOriginal(service) : service
                try await original.undo(objectId: objectId)
            }
            try publish { AnytypeAnalytics.instance().logUndo(resultType: .true) }
        } catch let error as ObjectActionsServiceError {
            try publish {
                toastData = ToastBarData(error.localizedDescription, type: .neutral)
                AnytypeAnalytics.instance().logUndo(resultType: .false)
            }
        }
    }

    func redo() async throws {
        do {
            let service = objectActionsService, objectId = objectId
            let requiresOriginalDelegate = documentWriteOwner != nil
            try await performMutation {
                let original = requiresOriginalDelegate ? try OriginalObjectActionsServiceBinding.requireOriginal(service) : service
                try await original.redo(objectId: objectId)
            }
            try publish { AnytypeAnalytics.instance().logRedo(resultType: .true) }
        } catch let error as ObjectActionsServiceError {
            try publish {
                toastData = ToastBarData(error.localizedDescription, type: .neutral)
                AnytypeAnalytics.instance().logRedo(resultType: .false)
            }
        }
    }
}
