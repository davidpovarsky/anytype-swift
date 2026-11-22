import Foundation
import Services

enum PreparedEditorPageSessionFactoryError: Error, Sendable, Equatable {
    case unsupportedAccountLifetime
    case unsupportedDocumentLifetime
    case invalidIdentity
    case notEditable
    case permissionReadinessTimeout
}

/// Holds only the reference acquired by this factory. DocumentsProvider's
/// cache is weak; original final-reference deinit owns close, so releasing
/// this acquisition cannot close a document retained by another original user.
@MainActor
private final class PreparedEditorOpeningDocumentRetention {
    private var document: (any BaseDocumentProtocol)?

    init(_ document: any BaseDocumentProtocol) { self.document = document }
    func release() { document = nil }
}

/// The shared acquisition route for the external Host and deliberately selected
/// original child editors. It uses the original document and service graph.
@MainActor
enum PreparedEditorPageSessionFactory {
    static func prepare(
        data: EditorPageObject,
        sourceBinding: EditorDocumentWriteSourceBinding,
        navigationContext: (any NavigationContextProtocol)? = nil,
        requiredPermissions: Set<EditorDocumentWritePermission> = []
    ) async throws -> PreparedEditorPageSession {
        try sourceBinding.validate()
        guard sourceBinding.committedEventBinding != nil else {
            throw PreparedEditorPageSessionFactoryError.unsupportedAccountLifetime
        }
        let document = Container.shared.documentsProvider().document(
            objectId: data.objectId, spaceId: data.spaceId, mode: data.mode
        )
        guard let ownedDocument = document as? any BaseDocumentProtocol & EditorDocumentWriteLifetimeProviding else {
            throw PreparedEditorPageSessionFactoryError.unsupportedDocumentLifetime
        }
        guard ownedDocument.objectId.utf8.elementsEqual(data.objectId.utf8),
              ownedDocument.spaceId.utf8.elementsEqual(data.spaceId.utf8),
              data.mode.isHandling, ownedDocument.mode == data.mode else {
            throw PreparedEditorPageSessionFactoryError.invalidIdentity
        }
        guard let originalDocument = ownedDocument as? BaseDocument else {
            throw PreparedEditorPageSessionFactoryError.unsupportedDocumentLifetime
        }
        let openingRetention = PreparedEditorOpeningDocumentRetention(ownedDocument)
        try await sourceBinding.performRead(
            rpcNames: ["ObjectOpen"],
            onDrained: { openingRetention.release() }
        ) {
            try await originalDocument.openForOriginalEditorSource()
        }
        try Task.checkCancellation()
        try sourceBinding.validate()
        try PreparedEditorPageDocument.validate(data: data, document: ownedDocument)
        try await waitForOriginalEditPermission(
            document: ownedDocument,
            sourceBinding: sourceBinding,
            participants: Container.shared.participantsStorage(),
            requiredPermissions: requiredPermissions
        )
        let services = EditorPageServiceDependencies(
            blockActionService: .original(),
            blockActionHandler: .original(),
            keyboardHandler: .original(),
            blocksStateManager: .original(),
            blockBuilder: .original(),
            simpleTable: .original(),
            slashMenu: .original(),
            header: .original(),
            router: .original(navigationContext: navigationContext),
            viewModel: .original(),
            localEvents: OriginalEditorLocalEventPublisher()
        )
        return try PreparedEditorPageSession(
            data: data,
            document: ownedDocument,
            textService: Container.shared.textService(),
            services: services,
            sourceBinding: sourceBinding
        )
    }

    /// Observe the original asynchronous participant subscription. This wait
    /// grants no permission and is unrelated to the editor's save barrier.
    private static func waitForOriginalEditPermission(
        document: any BaseDocumentProtocol,
        sourceBinding: EditorDocumentWriteSourceBinding,
        participants: any ParticipantsStorageProtocol,
        requiredPermissions: Set<EditorDocumentWritePermission>
    ) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(15))
        while true {
            try sourceBinding.validate()
            guard document.isOpened, !document.isLocked else {
                throw PreparedEditorPageSessionFactoryError.notEditable
            }
            if let participant = participants.participants.first(where: {
                $0.spaceId.utf8.elementsEqual(document.spaceId.utf8)
            }), !participant.canEdit {
                throw PreparedEditorPageSessionFactoryError.notEditable
            }
            let permissions = document.permissions
            let admitted = requiredPermissions.isEmpty
                ? permissions.canEditBlocks
                : requiredPermissions.allSatisfy { $0.isAllowed(by: permissions) }
            if admitted { return }
            guard clock.now < deadline else {
                throw PreparedEditorPageSessionFactoryError.permissionReadinessTimeout
            }
            try await clock.sleep(for: .milliseconds(50))
        }
    }
}

/// A selected child retains the parent's frozen source/account generations,
/// never a later account with a matching string identifier. It acquires its own
/// original document owner for the actual selected object in the same Space.
@MainActor
struct PreparedEditorChildPreparation {
    private weak var parentOwner: EditorDocumentWriteOwner?
    private let sourceBinding: EditorDocumentWriteSourceBinding
    private let navigationContext: (any NavigationContextProtocol)?

    init(owner: EditorDocumentWriteOwner, navigationContext: (any NavigationContextProtocol)? = nil) throws {
        sourceBinding = try owner.childSourceBinding()
        parentOwner = owner
        self.navigationContext = navigationContext
    }

    func deriving(owner: EditorDocumentWriteOwner) throws -> Self {
        try Self(owner: owner, navigationContext: navigationContext)
    }

    func prepare(data: EditorPageObject, requiredPermissions: Set<EditorDocumentWritePermission> = []) async throws -> PreparedEditorPageSession {
        try validateParent(spaceId: data.spaceId)
        let session = try await PreparedEditorPageSessionFactory.prepare(data: data, sourceBinding: sourceBinding, navigationContext: navigationContext, requiredPermissions: requiredPermissions)
        do {
            try validateParent(spaceId: data.spaceId)
            return session
        } catch {
            session.retire()
            throw error
        }
    }

    /// The caller receives the acquired child Owner so post-await synchronous
    /// original writes use the child, rather than the parent's object authority.
    func performMutation<Value: Sendable>(
        data: EditorPageObject,
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        operation: @Sendable (EditorDocumentWriteOwner) async throws -> Value
    ) async throws -> Value {
        let session = try await prepare(data: data, requiredPermissions: requiredPermissions)
        let childOwner = session.owner
        defer { session.retire() }
        if !requiredPermissions.isEmpty {
            return try await childOwner.performDocumentAction(
                contextId: data.objectId, requiredPermissions: requiredPermissions,
                onDrained: { [session] in withExtendedLifetime(session) {} }
            ) {
                try await operation(childOwner)
            }
        }
        return try await childOwner.performMutation(
            contextId: data.objectId,
            requiredPermissions: requiredPermissions,
            onDrained: { [session] in withExtendedLifetime(session) {} }
        ) {
            try await operation(childOwner)
        }
    }

    private func validateParent(spaceId: String) throws {
        guard let parentOwner else { throw EditorDocumentWriteError.rejected(.retired) }
        try parentOwner.performSynchronousOperation(spaceId: spaceId, requiresEditing: false) {
            try sourceBinding.validate()
        }
    }
}
