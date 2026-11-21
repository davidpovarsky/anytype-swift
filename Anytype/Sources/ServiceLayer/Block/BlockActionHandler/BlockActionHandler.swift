import UIKit
import Services
import Combine
import AnytypeCore
import ProtobufMessages

@MainActor
final class BlockActionHandler: BlockActionHandlerProtocol, Sendable {
    private let document: any BaseDocumentProtocol
    
    private let service: any BlockActionServiceProtocol
    private let markupChanger: any BlockMarkupChangerProtocol

    // A local event is optimistic, not a native acknowledgement. Keep failed
    // payloads retryable, and order all callers (including simple-table cells)
    // through one native tail per block.
    private struct NativeTextWrite {
        let id: UUID
        let value: MiddlewareString
        let task: Task<Void, any Error>
    }
    private var nativeTextWrites: [String: NativeTextWrite] = [:]
    private var unacknowledgedNativeText: [String: MiddlewareString] = [:]
    
    
    @Injected(\.blockService)
    private var blockService: any BlockServiceProtocol
    @Injected(\.blockTableService)
    private var blockTableService: any BlockTableServiceProtocol
    @Injected(\.fileActionsService)
    private var fileService: any FileActionsServiceProtocol
    @Injected(\.objectActionsService)
    private var objectService: any ObjectActionsServiceProtocol
    @Injected(\.pasteboardBlockService)
    private var pasteboardBlockService: any PasteboardBlockServiceProtocol
    @Injected(\.bookmarkService)
    private var bookmarkService: any BookmarkServiceProtocol
    @Injected(\.objectTypeProvider)
    private var objectTypeProvider: any ObjectTypeProviderProtocol
    
    init(
        document: some BaseDocumentProtocol,
        markupChanger: some BlockMarkupChangerProtocol,
        service: some BlockActionServiceProtocol
    ) {
        self.document = document
        self.markupChanger = markupChanger
        self.service = service
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
        Task {
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
        Task {
            await EventsBunch(contextId: document.objectId, localEvents: [.setToggled(blockId: blockId)])
                .send()
        }
    }
    
    func setAlignment(_ alignment: LayoutAlignment, blockIds: [String], route: AnalyticsEventsRouteKind?) {
        AnytypeAnalytics.instance().logSetAlignment(alignment, isBlock: blockIds.isNotEmpty, route: route)
        Task {
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
        Task {
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
        Task {
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
        let value = AttributedTextConverter.asMiddleware(attributedText: text.value)
        let currentContent = document.infoContainer.get(id: blockId)?.textContent
        let modelMatches = currentContent.map {
            $0.text.utf8.elementsEqual(value.text.utf8) && $0.marks == value.marks
        } ?? false
        let pending = nativeTextWrites[blockId]

        // A duplicate optimistic callback must await the native result. Returning
        // success here would clear the shared editor's dirty state before an
        // in-flight write can fail.
        if modelMatches, let pending, Self.sameNativeText(pending.value, value) {
            try await pending.task.value
            return
        }

        let needsRetry = unacknowledgedNativeText[blockId].map {
            Self.sameNativeText($0, value)
        } ?? false
        // Keep this decision before the first suspension: a no-op focus callback
        // must not become a whole-value LWW write after a peer changes the model.
        // Swift String equality is canonical; text persistence needs exact UTF-8.
        if pending == nil, modelMatches, !needsRetry { return }

        let writeID = UUID()
        let predecessor = pending?.task
        let task = Task<Void, any Error> { @MainActor [self] in
            // An older failed write must not discard a newer accepted edit.
            if let predecessor { _ = await predecessor.result }
            defer {
                if nativeTextWrites[blockId]?.id == writeID {
                    nativeTextWrites.removeValue(forKey: blockId)
                }
            }
            unacknowledgedNativeText[blockId] = value
            await EventsBunch(
                contextId: document.objectId,
                localEvents: [.setText(blockId: blockId, text: value)]
            ).send()
            try await service.setText(
                contextId: document.objectId, blockId: blockId, middlewareString: value
            )
            // Only the serial native writer's successful acknowledgement clears
            // the failed/pending payload; optimistic model equality never does.
            unacknowledgedNativeText.removeValue(forKey: blockId)
        }
        nativeTextWrites[blockId] = NativeTextWrite(id: writeID, value: value, task: task)
        try await task.value
    }

    private static func sameNativeText(_ lhs: MiddlewareString, _ rhs: MiddlewareString) -> Bool {
        lhs.text.utf8.elementsEqual(rhs.text.utf8) && lhs.marks == rhs.marks
    }

    // MARK: - Public methods
    func uploadMediaFile(uploadingSource: FileUploadingSource, type: MediaPickerContentType, blockId: String, route: UploadMediaRoute) {
        
        Task {
            await EventsBunch(
                contextId: document.objectId,
                localEvents: [.setLoadingState(blockId: blockId)]
            ).send()
            
            try await fileService.uploadDataAt(source: uploadingSource, contextID: document.objectId, blockID: blockId)
        }

        AnytypeAnalytics.instance().logUploadMedia(type: type.asFileBlockContentType, route: route)
    }
    
    func uploadImage(image: UIImage, type: String, blockId: String, route: UploadMediaRoute) {
        Task {
            guard let fileData = try? fileService.createFileData(image: image, type: type) else {
                return
            }
            
            await EventsBunch(
                contextId: document.objectId,
                localEvents: [.setLoadingState(blockId: blockId)]
            ).send()
            
            try await fileService.uploadDataAt(data: fileData, contextID: document.objectId, blockID: blockId)
        }

        AnytypeAnalytics.instance().logUploadMedia(type: .image, route: route)
    }
    
    func uploadFileAt(localPath: String, blockId: String, route: UploadMediaRoute) {
        AnytypeAnalytics.instance().logUploadMedia(type: .file, route: route)
        
        Task {
            await EventsBunch(
                contextId: document.objectId,
                localEvents: [.setLoadingState(blockId: blockId)]
            ).send()
            
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
        Task {
            try await blockService.setLinkAppearance(objectId: document.objectId, blockIds: [blockId], appearance: appearance)
        }
    }
    
    func pasteContent() {
        Task {
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
