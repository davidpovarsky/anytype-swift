import Foundation
import Services

/// One prepared document, one assembly and one mounted host. Text/local-event
/// operations share its owner; other injected services retain their existing
/// contracts and still require independent writer qualification.
@MainActor
final class PreparedEditorPageSession {
    let data: EditorPageObject
    let document: any BaseDocumentProtocol & EditorDocumentWriteLifetimeProviding
    let owner: EditorDocumentWriteOwner
    let services: EditorPageServiceDependencies

    private let sessionLifetime: EditorDocumentWriteLifetime
    private var assemblyClaimed = false
    private var hostClaimed = false
    private var controllerBound = false
    private weak var boundController: AnyObject?

    init(
        data: EditorPageObject,
        document: any BaseDocumentProtocol & EditorDocumentWriteLifetimeProviding,
        textService: any TextServiceProtocol,
        services: EditorPageServiceDependencies,
        onDrained: (@MainActor () -> Void)? = nil
    ) throws {
        let sessionLifetime = EditorDocumentWriteLifetime()
        let owner = try EditorDocumentWriteOwner(
            data: data, lifetimeDocument: document,
            sessionLifetime: sessionLifetime, onDrained: onDrained
        )
        let localEvents = DocumentOwnedLocalEventPublisher(owner: owner, publisher: services.localEvents)
        let textHandler = TextServiceHandler(
            textService: DocumentOwnedTextService(owner: owner, service: textService),
            localEvents: localEvents
        )
        let existing = services.blockActionService
        self.data = data
        self.document = document
        self.owner = owner
        self.sessionLifetime = sessionLifetime
        self.services = EditorPageServiceDependencies(
            blockActionService: .init(
                objectActionService: existing.objectActionService,
                textServiceHandler: textHandler,
                blockService: existing.blockService,
                bookmarkService: existing.bookmarkService,
                fileService: existing.fileService,
                objectTypeProvider: existing.objectTypeProvider,
                keyboardInsertedBlocksStorage: existing.keyboardInsertedBlocksStorage
            ),
            blockActionHandler: services.blockActionHandler,
            keyboardHandler: services.keyboardHandler,
            blocksStateManager: services.blocksStateManager,
            blockBuilder: services.blockBuilder,
            simpleTable: services.simpleTable,
            slashMenu: services.slashMenu,
            header: services.header,
            router: services.router,
            viewModel: services.viewModel,
            localEvents: localEvents
        )
        try owner.validateOwnership()
    }

    func claimAssembly() throws {
        try owner.validateOwnership()
        guard !assemblyClaimed else { throw EditorDocumentWriteError.rejected(.invalidLease) }
        assemblyClaimed = true
    }

    func bind(controller: AnyObject) throws {
        try owner.validateOwnership()
        guard assemblyClaimed, !controllerBound else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        controllerBound = true
        boundController = controller
    }

    func attachHost(controller: AnyObject) throws -> EditorDocumentWriteLifetime.Observation {
        try owner.validateOwnership()
        guard boundController === controller, !hostClaimed else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        hostClaimed = true
        return .init { [sessionLifetime] in sessionLifetime.invalidate() }
    }

    func retire(controller: AnyObject) {
        guard boundController === controller else { return }
        retire()
    }

    func retire() {
        sessionLifetime.invalidate()
        owner.retire()
    }

    deinit {
        // A retained asynchronous writer cannot gain authority merely because
        // the prepared session or its original host was released.
        sessionLifetime.invalidate()
    }
}
