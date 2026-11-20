import Foundation
import Services

/// One prepared document, one assembly and one mounted host. Text/table/local-event
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
            blockActionHandler: .init(
                blockService: services.blockActionHandler.blockService,
                blockTableService: DocumentOwnedBlockTableService(
                    owner: owner, service: services.blockActionHandler.blockTableService
                ),
                fileService: services.blockActionHandler.fileService,
                objectService: services.blockActionHandler.objectService,
                pasteboardBlockService: services.blockActionHandler.pasteboardBlockService,
                bookmarkService: services.blockActionHandler.bookmarkService,
                objectTypeProvider: services.blockActionHandler.objectTypeProvider
            ),
            keyboardHandler: services.keyboardHandler,
            blocksStateManager: services.blocksStateManager,
            blockBuilder: .init(
                tableService: DocumentOwnedBlockTableService(
                    owner: owner, service: services.blockBuilder.tableService
                ),
                detailsService: services.blockBuilder.detailsService,
                audioSessionService: services.blockBuilder.audioSessionService,
                objectTypeProvider: services.blockBuilder.objectTypeProvider,
                pasteboardService: services.blockBuilder.pasteboardService,
                blockService: services.blockBuilder.blockService
            ),
            simpleTable: .init(
                tableService: DocumentOwnedBlockTableService(
                    owner: owner, service: services.simpleTable.tableService
                ),
                pasteboardService: services.simpleTable.pasteboardService,
                defaultObjectService: services.simpleTable.defaultObjectService,
                typesService: services.simpleTable.typesService
            ),
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
