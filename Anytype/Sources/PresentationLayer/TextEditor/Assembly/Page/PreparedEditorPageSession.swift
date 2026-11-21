import Foundation
import Services

/// One prepared document, one assembly and one mounted host. Text/block/table/local-event
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
        sourceBinding: EditorDocumentWriteSourceBinding? = nil,
        onDrained: (@MainActor () -> Void)? = nil
    ) throws {
        let sessionLifetime = EditorDocumentWriteLifetime()
        let owner = try EditorDocumentWriteOwner(
            data: data, lifetimeDocument: document,
            sessionLifetime: sessionLifetime, sourceBinding: sourceBinding, onDrained: onDrained
        )
        let localEvents = DocumentOwnedLocalEventPublisher(owner: owner, publisher: services.localEvents)
        let textHandler = TextServiceHandler(
            textService: DocumentOwnedTextService(owner: owner, service: textService),
            localEvents: localEvents
        )
        let existing = services.blockActionService
        // External sources require one owner and one retained staging/receipt
        // set across both original file delegates and every pasteboard delegate.
        // Existing internal callers without an external source retain their
        // original injected service graph and its established test contract.
        let externalSource = sourceBinding != nil
        let preloads = externalSource ? DocumentOwnedFilePreloads(owner: owner) : nil
        let staging = externalSource ? try DocumentOwnedFileStaging(owner: owner) : nil
        func objects(_ service: any ObjectActionsServiceProtocol) -> any ObjectActionsServiceProtocol {
            guard externalSource else { return service }
            return DocumentOwnedObjectActionsService(owner: owner, service: service)
        }
        func bookmarks(_ service: any BookmarkServiceProtocol) -> any BookmarkServiceProtocol {
            guard externalSource else { return service }
            return DocumentOwnedBookmarkService(owner: owner, service: service)
        }
        func files(_ service: any FileActionsServiceProtocol) throws -> any FileActionsServiceProtocol {
            guard let preloads, let staging else { return service }
            return try DocumentOwnedFileActionsService.bindOriginal(
                service, owner: owner, preloads: preloads, staging: staging
            )
        }
        func blockPasteboard(_ service: any PasteboardBlockServiceProtocol) throws -> any PasteboardBlockServiceProtocol {
            guard let staging else { return service }
            return try PasteboardBlockService.bindOriginal(service, owner: owner, staging: staging)
        }
        func documentPasteboard(_ service: any PasteboardBlockDocumentServiceProtocol) throws -> any PasteboardBlockDocumentServiceProtocol {
            guard let staging else { return service }
            return try PasteboardBlockDocumentService.bindOriginal(service, owner: owner, staging: staging)
        }
        func details(_ service: any DetailsServiceProtocol) throws -> any DetailsServiceProtocol {
            guard let preloads, let staging else { return service }
            return try DocumentOwnedDetailsService.bindOriginal(
                service, owner: owner, preloads: preloads, staging: staging
            )
        }
        func defaultObjects(_ service: any DefaultObjectCreationServiceProtocol) throws -> any DefaultObjectCreationServiceProtocol {
            guard externalSource else { return service }
            return try DocumentOwnedDefaultObjectCreationService.bindOriginal(service, owner: owner)
        }
        func header(_ dependencies: ObjectHeaderViewModelDependencies) throws -> ObjectHeaderViewModelDependencies {
            guard let preloads, let staging else { return dependencies }
            return .init(
                objectHeaderUploadingService: try DocumentOwnedObjectHeaderUploadingService.bindOriginal(
                    dependencies.objectHeaderUploadingService, owner: owner, preloads: preloads, staging: staging
                ),
                documentWriteOwner: owner
            )
        }
        self.data = data
        self.document = document
        self.owner = owner
        self.sessionLifetime = sessionLifetime
        self.services = EditorPageServiceDependencies(
            blockActionService: .init(
                objectActionService: objects(existing.objectActionService),
                textServiceHandler: textHandler,
                blockService: DocumentOwnedBlockService(owner: owner, service: existing.blockService),
                bookmarkService: bookmarks(existing.bookmarkService),
                fileService: try files(existing.fileService),
                objectTypeProvider: existing.objectTypeProvider,
                keyboardInsertedBlocksStorage: existing.keyboardInsertedBlocksStorage,
                documentWriteOwner: externalSource ? owner : nil
            ),
            blockActionHandler: .init(
                blockService: DocumentOwnedBlockService(owner: owner, service: services.blockActionHandler.blockService),
                blockTableService: DocumentOwnedBlockTableService(
                    owner: owner, service: services.blockActionHandler.blockTableService
                ),
                fileService: try files(services.blockActionHandler.fileService),
                objectService: objects(services.blockActionHandler.objectService),
                pasteboardBlockService: try blockPasteboard(services.blockActionHandler.pasteboardBlockService),
                bookmarkService: bookmarks(services.blockActionHandler.bookmarkService),
                objectTypeProvider: services.blockActionHandler.objectTypeProvider,
                documentWriteOwner: externalSource ? owner : nil
            ),
            keyboardHandler: .init(
                blockService: DocumentOwnedBlockService(owner: owner, service: services.keyboardHandler.blockService),
                keyboardInsertedBlocksStorage: services.keyboardHandler.keyboardInsertedBlocksStorage
            ),
            blocksStateManager: .init(
                blockService: DocumentOwnedBlockService(owner: owner, service: services.blocksStateManager.blockService),
                pasteboardService: try documentPasteboard(services.blocksStateManager.pasteboardService),
                documentsProvider: services.blocksStateManager.documentsProvider,
                objectActionsService: objects(services.blocksStateManager.objectActionsService),
                toastPresenter: services.blocksStateManager.toastPresenter
            ),
            blockBuilder: .init(
                tableService: DocumentOwnedBlockTableService(
                    owner: owner, service: services.blockBuilder.tableService
                ),
                detailsService: try details(services.blockBuilder.detailsService),
                audioSessionService: services.blockBuilder.audioSessionService,
                objectTypeProvider: services.blockBuilder.objectTypeProvider,
                pasteboardService: try documentPasteboard(services.blockBuilder.pasteboardService),
                blockService: DocumentOwnedBlockService(owner: owner, service: services.blockBuilder.blockService)
            ),
            simpleTable: .init(
                tableService: DocumentOwnedBlockTableService(
                    owner: owner, service: services.simpleTable.tableService
                ),
                pasteboardService: try documentPasteboard(services.simpleTable.pasteboardService),
                defaultObjectService: try defaultObjects(services.simpleTable.defaultObjectService),
                typesService: services.simpleTable.typesService
            ),
            slashMenu: .init(
                pasteboardService: try documentPasteboard(services.slashMenu.pasteboardService),
                objectDateByTimestampService: services.slashMenu.objectDateByTimestampService
            ),
            header: try header(services.header),
            router: services.router,
            viewModel: .init(
                objectActionsService: objects(services.viewModel.objectActionsService),
                objectTypeProvider: services.viewModel.objectTypeProvider,
                searchService: services.viewModel.searchService,
                templatesSubscriptionService: services.viewModel.templatesSubscriptionService,
                accountManager: services.viewModel.accountManager,
                publishingService: services.viewModel.publishingService,
                participantStorage: services.viewModel.participantStorage,
                publishedUrlBuilder: services.viewModel.publishedUrlBuilder,
                keyboardInsertedBlocksStorage: services.viewModel.keyboardInsertedBlocksStorage,
                blockService: DocumentOwnedBlockService(owner: owner, service: services.viewModel.blockService)
            ),
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

    /// Reject only this bound owner's failed first host attempt. An owner
    /// already attached elsewhere is not revoked by another host's update.
    func rejectUnattachedHost(controller: AnyObject) {
        guard !hostClaimed, boundController === controller else { return }
        retire()
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
