import UIKit
import Services
import Combine
import AnytypeCore
import ProtobufMessages

@MainActor
final class BlockActionHandler: BlockActionHandlerProtocol, Sendable {
    private let document: any BaseDocumentProtocol
    let documentWriteOwner: EditorDocumentWriteOwner?
    var documentWriteContextID: String { document.objectId }
    
    private let service: any BlockActionServiceProtocol
    private let markupChanger: any BlockMarkupChangerProtocol
    
    
    private let blockService: any BlockServiceProtocol
    private let blockTableService: any BlockTableServiceProtocol
    private let fileService: any FileActionsServiceProtocol
    private let objectService: any ObjectActionsServiceProtocol
    private let pasteboardBlockService: any PasteboardBlockServiceProtocol
    private let bookmarkService: any BookmarkServiceProtocol
    private let objectTypeProvider: any ObjectTypeProviderProtocol
    private let localEvents: any EditorLocalEventPublishing
    
    init(
        document: some BaseDocumentProtocol,
        markupChanger: some BlockMarkupChangerProtocol,
        service: some BlockActionServiceProtocol,
        dependencies: BlockActionHandlerDependencies = .original(),
        localEvents: any EditorLocalEventPublishing = OriginalEditorLocalEventPublisher()
    ) {
        self.document = document
        self.documentWriteOwner = dependencies.documentWriteOwner
        self.markupChanger = markupChanger
        self.service = service
        self.blockService = dependencies.blockService
        self.blockTableService = dependencies.blockTableService
        self.fileService = dependencies.fileService
        self.objectService = dependencies.objectService
        self.pasteboardBlockService = dependencies.pasteboardBlockService
        self.bookmarkService = dependencies.bookmarkService
        self.objectTypeProvider = dependencies.objectTypeProvider
        self.localEvents = localEvents
    }

    // MARK: - Service proxy

    func turnIntoObject(blockId: String) async throws -> String? {
        try await service.turnIntoObject(blockId: blockId, spaceId: document.spaceId)
    }
    
    func turnInto(_ style: BlockText.Style, blockId: String, route: AnalyticsEventsRouteKind?) async throws {
        switch style {
        case .toggle, .toggleHeader, .toggleHeader2, .toggleHeader3:
            if let blockInformation = document.infoContainer.get(id: blockId),
               blockInformation.childrenIds.count > 0, !blockInformation.isToggled {
                blockInformation.toggle()
            }
            try await service.turnInto(style, blockId: blockId)
        default:
            try await service.turnInto(style, blockId: blockId)
        }
        AnytypeAnalytics.instance().logChangeBlockStyle(style, route: route)
    }
    
    func upload(blockId: String, filePath: String) async throws {
        try await service.upload(blockId: blockId, filePath: filePath)
    }
    
    @MainActor
    func setObjectType(type: ObjectType) async throws {
        HomeCreateObjectTip.objectTypeChanged = true
        try await service.setObjectType(type: type)
    }
    
    @discardableResult
    func turnIntoBookmark(url: AnytypeURL) async throws -> ObjectType {
        let type = try objectTypeProvider.objectType(uniqueKey: .bookmark, spaceId: document.spaceId)
        try await setObjectType(type: type)
        try await bookmarkService.fetchBookmarkContent(bookmarkId: document.objectId, url: url)
        return type
    }

    func setObjectSetType() async throws {
        try await service.setObjectSetType()
    }
    
    func setObjectCollectionType() async throws {
        try await service.setObjectCollectionType()
    }
    
    func applyTemplate(objectId: String, templateId: String) async throws {
        try await objectService.applyTemplate(objectId: objectId, templateId: templateId)
    }
    
    func setTextColor(_ color: BlockColor, blockIds: [String], route: AnalyticsEventsRouteKind? = nil) {
        AnytypeAnalytics.instance().logChangeBlockColor(route: route)
        scheduleMutationTask { [self] in
            try await blockService.setBlockColor(objectId: document.objectId, blockIds: blockIds, color: color.middleware)
        }
    }
    
    func setBackgroundColor(_ color: BlockBackgroundColor, blockIds: [String], route: AnalyticsEventsRouteKind?) {
        AnytypeAnalytics.instance().logChangeBlockBackground(color: color.middleware, route: route)
        service.setBackgroundColor(blockIds: blockIds, color: color)
    }
    
    func duplicate(blockId: String) {
        AnytypeAnalytics.instance().logDuplicateBlock()
        service.duplicate(blockId: blockId)
    }
    
    func fetch(url: AnytypeURL, blockId: String) {
        service.bookmarkFetch(blockId: blockId, url: url)
    }
    
    func checkbox(selected: Bool, blockId: String) {
        service.checked(blockId: blockId, newValue: selected)
    }
    
    func toggle(blockId: String) {
        scheduleMutationTask { [self] in
            await localEvents.setToggled(contextId: document.objectId, blockId: blockId)
        }
    }
    
    func setAlignment(_ alignment: LayoutAlignment, blockIds: [String], route: AnalyticsEventsRouteKind?) {
        AnytypeAnalytics.instance().logSetAlignment(alignment, isBlock: blockIds.isNotEmpty, route: route)
        scheduleMutationTask { [self] in
            try await blockService.setAlign(objectId: document.objectId, blockIds: blockIds, alignment: alignment)
            try await PinkhaTextDirectionPersistence.markExplicitAlignmentIfNeeded(
                document: document,
                blockIds: blockIds,
                alignment: alignment,
                blockService: blockService
            )
        }
    }
    
    func delete(blockIds: [String]) {
        service.delete(blockIds: blockIds)
    }
    
    func moveToPage(blockIds: [String], pageId: String) async throws {
        AnytypeAnalytics.instance().logMoveBlock()
        try await blockService.moveToPage(objectId: document.objectId, blockIds: blockIds, pageId: pageId)
    }


    func createEmptyBlock(parentId: String) {
        scheduleMutationTask { [self] in
            let emptyBlock = BlockInformation.emptyText
            AnytypeAnalytics.instance().logCreateBlock(type: emptyBlock.content.type, spaceId: document.spaceId)
            try await service.addChild(info: emptyBlock, parentId: parentId)
        }
    }
    
    func addLink(targetDetails: ObjectDetails, blockId: String, position: BlockPosition, route: AnalyticsEventsRouteKind) async throws {
        let isBookmarkType = targetDetails.resolvedLayoutValue == .bookmark
        AnytypeAnalytics.instance().logCreateLink(
            objectType: targetDetails.objectType.analyticsType,
            route: route
        )
        try await service.add(
            info: isBookmarkType ? .bookmark(targetId: targetDetails.id) : .emptyLink(targetId: targetDetails.id),
            targetBlockId: blockId,
            position: position
        )
    }
    
    func changeMarkup(blockIds: [String], markType: MarkupType, route: AnalyticsEventsRouteKind?) {
        scheduleMutationTask { [self] in
            AnytypeAnalytics.instance().logChangeBlockStyle(markType, route: route)
            try await blockService.changeMarkup(objectId: document.objectId, blockIds: blockIds, markType: markType)
        }
    }
    
    // MARK: - Markup changer proxy
    func toggleWholeBlockMarkup(
        _ attributedString: SafeNSAttributedString?,
        markup: MarkupType,
        info: BlockInformation,
        route: AnalyticsEventsRouteKind?
    ) async throws -> SafeNSAttributedString? {
        guard let textContent = info.textContent, let attributedString else { return nil }
        AnytypeAnalytics.instance().logChangeBlockStyle(markup, route: route)
        
        let changedAttributedString = markupChanger.toggleMarkup(
            attributedString.value,
            markup: markup,
            contentType: .text(textContent.contentType)
        ).sendable()
        
        try await changeText(changedAttributedString, blockId: info.id)
        
        return changedAttributedString
    }

    func setTextStyle(
        _ attribute: MarkupType,
        range: NSRange,
        blockId: String,
        currentText: SafeNSAttributedString,
        contentType: BlockContentType
    ) async throws -> SafeNSAttributedString {
        
        let newText = markupChanger.setMarkup(
            attribute,
            range: range,
            attributedString: currentText.value,
            contentType: contentType
        ).sendable()

        AnytypeAnalytics.instance().logChangeTextStyle(markupType: attribute, objectType: .custom)

        try await changeText(newText, blockId: blockId)
        
        return newText
    }
    
    // The block that replaces an empty block on first fill. The id is minted client-side, so
    // the caller knows the block's final identity synchronously — before the replace
    // round-trips. Everything else the empty block had (style, checked, color, background,
    // align) is carried over. `fields` is set on the model but BlockInformationConverter
    // currently drops it from the wire request.
    func makeEmptyBlockReplacement(info: BlockInformation, middlewareString: MiddlewareString) -> BlockInformation? {
        guard var content = info.textContent else {
            anytypeAssertionFailure("Replace of a non-text block")
            return nil
        }
        content.text = middlewareString.text
        content.marks = middlewareString.marks

        return BlockInformation(
            id: BlockIdGenerator.mint(),
            content: .text(content),
            backgroundColor: info.backgroundColor,
            horizontalAlignment: info.horizontalAlignment,
            childrenIds: [],
            configurationData: info.configurationData,
            fields: info.fields
        )
    }

    // First content into an existing empty block forks its identity: BlockReplace removes the
    // old id and creates the replacement carrying the content in a single atomic change, so
    // two clients filling the same empty block concurrently end up with two blocks instead of
    // one last-writer-wins text.
    func replaceEmptyBlock(replacement: BlockInformation, replacingBlockId: String) async throws {
        let newBlockId = try await service.replaceBlock(info: replacement, blockId: replacingBlockId)
        if newBlockId != replacement.id {
            anytypeAssertionFailure(
                "BlockReplace did not echo the client-minted id",
                info: ["minted": replacement.id, "created": newBlockId]
            )
        }
    }

    func changeText(_ text: SafeNSAttributedString, blockId: String) async throws {
        let middlewareString = AttributedTextConverter.asMiddleware(attributedText: text.value)

        // Focus and other UIKit quirks can fire text-change callbacks without an actual edit.
        // Syncing unchanged text is not just wasted traffic: every BlockTextSetText writes the
        // whole-value LWW text register and can clobber a concurrent peer edit.
        if let currentContent = document.infoContainer.get(id: blockId)?.textContent,
           currentContent.text == middlewareString.text,
           currentContent.marks == middlewareString.marks {
            return
        }

        await localEvents.setText(contextId: document.objectId, blockId: blockId, text: middlewareString)


        try await service.setText(contextId: document.objectId, blockId: blockId, middlewareString: middlewareString)
    }
    
    // MARK: - Public methods
    func uploadMediaFile(uploadingSource: FileUploadingSource, type: MediaPickerContentType, blockId: String, route: UploadMediaRoute) {
        
        scheduleMutationTask { [self] in
            await localEvents.setLoadingState(contextId: document.objectId, blockId: blockId)
            
            try await fileService.uploadDataAt(source: uploadingSource, contextID: document.objectId, blockID: blockId)
        }

        AnytypeAnalytics.instance().logUploadMedia(type: type.asFileBlockContentType, route: route)
    }
    
    func uploadImage(image: UIImage, type: String, blockId: String, route: UploadMediaRoute) {
        scheduleMutationTask { [self] in
            guard let fileData = try? fileService.createFileData(image: image, type: type) else {
                return
            }
            
            await localEvents.setLoadingState(contextId: document.objectId, blockId: blockId)
            
            try await fileService.uploadDataAt(data: fileData, contextID: document.objectId, blockID: blockId)
        }

        AnytypeAnalytics.instance().logUploadMedia(type: .image, route: route)
    }
    
    func uploadFileAt(localPath: String, blockId: String, route: UploadMediaRoute) {
        AnytypeAnalytics.instance().logUploadMedia(type: .file, route: route)
        
        scheduleMutationTask { [self] in
            await localEvents.setLoadingState(contextId: document.objectId, blockId: blockId)
            
            try await upload(blockId: blockId, filePath: localPath)
        }
    }
    
    func createPage(targetId: String, spaceId: String, typeUniqueKey: ObjectTypeUniqueKey, templateId: String) async throws -> String? {
        guard let info = document.infoContainer.get(id: targetId) else { return nil }
        var position: BlockPosition
        if case .text(let blockText) = info.content, blockText.text.isEmpty {
            position = .replace
        } else {
            position = .bottom
        }
        return try await service.createPage(targetId: targetId, spaceId: spaceId, typeUniqueKey: typeUniqueKey, position: position, templateId: templateId)
    }

    func createTable(
        blockId: String,
        rowsCount: Int,
        columnsCount: Int,
        blockText: SafeNSAttributedString?
    ) async throws -> String {
        guard let isTextAndEmpty = blockText?.value.string.isEmpty
                ?? document.infoContainer.get(id: blockId)?.isTextAndEmpty else { return "" }
        
        let position: BlockPosition = isTextAndEmpty ? .replace : .bottom

        AnytypeAnalytics.instance().logCreateBlock(type: TableBlockType.simpleTableBlock.rawValue, spaceId: document.spaceId)
        
        return try await blockTableService.createTable(
            contextId: document.objectId,
            targetId: blockId,
            position: position,
            rowsCount: rowsCount,
            columnsCount: columnsCount
        )
    }


    func addBlock(_ type: BlockContentType, blockId: String, blockText: SafeNSAttributedString?, position: BlockPosition?) async throws -> String {
        guard type != .smartblock(.page) else {
            anytypeAssertionFailure("Use createPage func instead")
            throw CommonError.undefined
        }
            
        guard let newBlock = BlockBuilder.createNewBlock(type: type) else { throw CommonError.undefined }

        guard let isTextAndEmpty = blockText?.value.string.isEmpty
            ?? document.infoContainer.get(id: blockId)?.isTextAndEmpty else { throw CommonError.undefined }
        
        let position: BlockPosition = isTextAndEmpty ? .replace : (position ?? .bottom)
        
        AnytypeAnalytics.instance().logCreateBlock(type: newBlock.content.type, spaceId: document.spaceId)
        return try await service.add(info: newBlock, targetBlockId: blockId, position: position)
    }

    func createAndFetchBookmark(
        targetID: String,
        position: BlockPosition,
        url: AnytypeURL
    ) {
        service.createAndFetchBookmark(
            contextID: document.objectId,
            targetID: targetID,
            position: position,
            url: url
        )
    }

    func setAppearance(blockId: String, appearance: BlockLink.Appearance) {
        scheduleMutationTask { [self] in
            try await blockService.setLinkAppearance(objectId: document.objectId, blockIds: [blockId], appearance: appearance)
        }
    }
    
    func pasteContent() {
        scheduleMutationTask { [self] in
            let blockId = try await blockService.addFirstBlock(contextId: document.objectId, info: .emptyText)
            pasteboardBlockService.pasteInsideBlock(
                objectId: document.objectId,
                spaceId: document.spaceId,
                focusedBlockId: blockId,
                range: .zero,
                handleLongOperation: { },
                completion: { _ in }
            )
        }
    }
}
