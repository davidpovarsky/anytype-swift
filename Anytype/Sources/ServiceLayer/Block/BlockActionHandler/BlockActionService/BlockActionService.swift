import Combine
import Services
import UIKit
import Logger
import ProtobufMessages
import AnytypeCore

@MainActor
final class BlockActionService: BlockActionServiceProtocol {
    private let documentId: String
    private let documentWriteOwner: EditorDocumentWriteOwner?
    private let cursorManager: EditorCursorManager

    private let objectActionService: any ObjectActionsServiceProtocol
    private let textServiceHandler: any TextServiceProtocol
    private let blockService: any BlockServiceProtocol
    private let bookmarkService: any BookmarkServiceProtocol
    private let fileService: any FileActionsServiceProtocol
    private let objectTypeProvider: any ObjectTypeProviderProtocol
    private let keyboardInsertedBlocksStorage: any KeyboardInsertedBlocksStorageProtocol
    private let localEvents: any EditorLocalEventPublishing

    private weak var modelsHolder: EditorMainItemModelsHolder?

    init(
        documentId: String,
        modelsHolder: EditorMainItemModelsHolder,
        cursorManager: EditorCursorManager,
        dependencies: BlockActionServiceDependencies = .original(),
        localEvents: any EditorLocalEventPublishing = OriginalEditorLocalEventPublisher()
    ) {
        self.documentId = documentId
        self.documentWriteOwner = dependencies.documentWriteOwner
        self.modelsHolder = modelsHolder
        self.cursorManager = cursorManager
        self.objectActionService = dependencies.objectActionService
        self.textServiceHandler = dependencies.textServiceHandler
        self.blockService = dependencies.blockService
        self.bookmarkService = dependencies.bookmarkService
        self.fileService = dependencies.fileService
        self.objectTypeProvider = dependencies.objectTypeProvider
        self.keyboardInsertedBlocksStorage = dependencies.keyboardInsertedBlocksStorage
        self.localEvents = localEvents
    }

    // MARK: Actions

    func addChild(info: BlockInformation, parentId: String) async throws -> String {
        try await add(info: info, targetBlockId: parentId, position: .inner)
    }

    func add(info: BlockInformation, targetBlockId: String, position: BlockPosition, setFocus: Bool) async throws -> String {
        let blockId = try await blockService.add(contextId: documentId, targetId: targetBlockId, info: info, position: position)
        SessionCreatedBlockIdsStorage.shared.register(blockId)

        if setFocus {
            cursorManager.blockFocus = BlockFocus(id: blockId, position: .beginning)
        }

        return blockId
    }

    func replaceBlock(info: BlockInformation, blockId: String) async throws -> String {
        let newBlockId = try await blockService.replaceBlock(contextId: documentId, blockId: blockId, info: info)
        SessionCreatedBlockIdsStorage.shared.register(newBlockId)
        return newBlockId
    }

    func setAndSplit(
        _ string: SafeNSAttributedString,
        blockId: String,
        mode: Anytype_Rpc.Block.Split.Request.Mode,
        range: NSRange,
        newBlockContentType: BlockText.Style
    ) async throws {
        let middlewareString = AttributedTextConverter.asMiddleware(attributedText: string.value)
        try await textServiceHandler.setText(
            contextId: documentId,
            blockId: blockId,
            middlewareString: middlewareString
        )
        let blockId = try await textServiceHandler.split(
            contextId: documentId,
            blockId: blockId,
            range: range,
            style: newBlockContentType,
            mode: mode
        )
        SessionCreatedBlockIdsStorage.shared.register(blockId)

        // The events bunch below renders the created row while this task is suspended, so the
        // keyboard-insert registration and the focus intent must both be in place first —
        // the editor then shows the row, moves the caret into it and scrolls it visible in one
        // render commit instead of three visible steps.
        keyboardInsertedBlocksStorage.register(blockId: blockId)
        cursorManager.focus(at: blockId, position: .beginning)
        cursorManager.blockFocus = BlockFocus(id: blockId, position: .beginning)

        await localEvents.refresh(contextId: documentId)
    }

    func duplicate(blockId: String) {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: documentId) { [self] in
            try await blockService.duplicate(
                contextId: documentId,
                targetId: blockId,
                blockIds: [blockId],
                position: .bottom
            )
        }
    }

    func createPage(targetId: String, spaceId: String, typeUniqueKey: ObjectTypeUniqueKey, position: BlockPosition, templateId: String) async throws -> String {
        try await blockService.createBlockLink(
            contextId: documentId,
            targetId: targetId,
            spaceId: spaceId,
            details: [.name("")],
            typeUniqueKey: typeUniqueKey,
            position: position,
            templateId: templateId
        )
    }

    func turnInto(_ style: BlockText.Style, blockId: String) async throws {
        try await textServiceHandler.setStyle(contextId: documentId, blockId: blockId, style: style)
    }
    
    func turnIntoObject(blockId: String, spaceId: String) async throws -> String? {
        let defaultObjectType = try objectTypeProvider.defaultObjectType(spaceId: spaceId)
        AnytypeAnalytics.instance().logCreateObject(objectType: defaultObjectType.analyticsType, spaceId: spaceId, route: .turnInto)

        return try await blockService.convertChildrenToObjects(
            contextId: documentId,
            blocksIds: [blockId],
            typeUniqueKey: defaultObjectType.uniqueKey,
            templateId: defaultObjectType.defaultTemplateId
        ).first
    }
    
    func checked(blockId: String, newValue: Bool) {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: documentId) { [self] in
            try await textServiceHandler.checked(contextId: documentId, blockId: blockId, newValue: newValue)
        }
    }
    
    func merge(secondBlockId: String) async throws {
        guard
            let previousBlock = modelsHolder?.findModel(
                beforeBlockId: secondBlockId,
                acceptingTypes: BlockContentType.allTextTypes
            ),
            previousBlock.content != .unsupported
        else {
            delete(blockIds: [secondBlockId])
            return
        }

        if let textContent = previousBlock.info.textContent {
            cursorManager.focus(
                at: previousBlock.blockId,
                position: .at(NSRange(location: Int(textContent.text.utf16.count), length: 0))
            )
            cursorManager.blockFocus = BlockFocus(id: previousBlock.blockId, position: .at(NSRange(location: textContent.text.utf16.count, length: 0)))
        }
        try await textServiceHandler.merge(contextId: documentId, firstBlockId: previousBlock.blockId, secondBlockId: secondBlockId)
    }
    
    func delete(blockIds: [String]) {
        AnytypeAnalytics.instance().logDeleteBlock()
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: documentId) { [self] in
            try await blockService.delete(contextId: documentId, blockIds: blockIds)
        }
    }
    
    func setText(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        try await textServiceHandler.setText(contextId: contextId, blockId: blockId, middlewareString: middlewareString)
    }

    func setTextForced(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        try await textServiceHandler.setTextForced(contextId: contextId, blockId: blockId, middlewareString: middlewareString)
    }
    
    func setObjectType(type: ObjectType) async throws {
        try await objectActionService.setObjectType(objectId: documentId, typeUniqueKey: type.uniqueKey)
    }

    func setObjectSetType() async throws {
        try await objectActionService.setObjectSetType(objectId: documentId)
    }
    
    func setObjectCollectionType() async throws {
        try await objectActionService.setObjectCollectionType(objectId: documentId)
    }

    private func setFocus(model: some BlockViewModelProtocol) {
        model.set(focus: .end)
    }
}

// MARK: - BookmarkFetch

extension BlockActionService {
    func bookmarkFetch(blockId: String, url: AnytypeURL) {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: documentId) { [self] in
            try await bookmarkService.fetchBookmark(objectId: documentId, blockID: blockId, url: url)
        }
    }

    func createAndFetchBookmark(
        contextID: String,
        targetID: String,
        position: BlockPosition,
        url: AnytypeURL
    ) {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: documentId) { [self] in
            try await bookmarkService.createAndFetchBookmark(
                objectId: contextID,
                targetID: targetID,
                position: position,
                url: url
            )
        }
    }
}

// MARK: - SetBackgroundColor

extension BlockActionService {
    func setBackgroundColor(blockIds: [String], color: BlockBackgroundColor) {
        setBackgroundColor(blockIds: blockIds, color: color.middleware)
    }
    
    func setBackgroundColor(blockIds: [String], color: MiddlewareColor) {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: documentId) { [self] in
            try await blockService.setBackgroundColor(objectId: documentId, blockIds: blockIds, color: color)
        }
    }
}

// MARK: - UploadFile

extension BlockActionService {
    func upload(blockId: String, filePath: String) async throws {
        try await fileService.uploadDataAt(source: .path(filePath), contextID: documentId, blockID: blockId)
    }
}
