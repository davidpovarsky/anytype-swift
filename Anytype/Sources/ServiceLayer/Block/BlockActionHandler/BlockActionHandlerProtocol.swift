import Foundation
import Services
import AnytypeCore
import UIKit


@MainActor
protocol BlockActionHandlerProtocol: AnyObject, Sendable {
    var documentWriteOwner: EditorDocumentWriteOwner? { get }
    var documentWriteContextID: String { get }
    func turnInto(_ style: BlockText.Style, blockId: String, route: AnalyticsEventsRouteKind?) async throws
    @discardableResult
    func turnIntoObject(blockId: String) async throws -> String?
    
    func setTextColor(_ color: BlockColor, blockIds: [String], route: AnalyticsEventsRouteKind?)
    func setBackgroundColor(_ color: BlockBackgroundColor, blockIds: [String], route: AnalyticsEventsRouteKind?)
    func duplicate(blockId: String)
    func fetch(url: AnytypeURL, blockId: String) async throws
    func checkbox(selected: Bool, blockId: String)
    func toggle(blockId: String)
    func setAlignment(_ alignment: LayoutAlignment, blockIds: [String], route: AnalyticsEventsRouteKind?)
    func delete(blockIds: [String])
    func moveToPage(blockIds: [String], pageId: String) async throws
    func createEmptyBlock(parentId: String)
    func addLink(targetDetails: ObjectDetails, blockId: String, position: BlockPosition, route: AnalyticsEventsRouteKind) async throws
    func changeMarkup(blockIds: [String], markType: MarkupType, route: AnalyticsEventsRouteKind?)
    @discardableResult
    func addBlock(_ type: BlockContentType, blockId: String, blockText: SafeNSAttributedString?, position: BlockPosition?) async throws -> String
    func toggleWholeBlockMarkup(
        _ attributedString: SafeNSAttributedString?,
        markup: MarkupType,
        info: BlockInformation,
        route: AnalyticsEventsRouteKind?
    ) async throws -> SafeNSAttributedString?
    func upload(blockId: String, filePath: String) async throws
    func createPage(targetId: String, spaceId: String, typeUniqueKey: ObjectTypeUniqueKey, templateId: String) async throws -> String?

    func setObjectType(type: ObjectType) async throws
    @discardableResult
    func turnIntoBookmark(url: AnytypeURL) async throws -> ObjectType
    func setObjectSetType() async throws
    func setObjectCollectionType() async throws
    func applyTemplate(objectId: String, templateId: String) async throws
    func changeText(_ text: SafeNSAttributedString, blockId: String) async throws
    func makeEmptyBlockReplacement(info: BlockInformation, middlewareString: MiddlewareString) -> BlockInformation?
    func replaceEmptyBlock(replacement: BlockInformation, replacingBlockId: String) async throws
    func setTextStyle(
        _ attribute: MarkupType,
        range: NSRange,
        blockId: String,
        currentText: SafeNSAttributedString,
        contentType: BlockContentType
    ) async throws -> SafeNSAttributedString
    func uploadMediaFile(uploadingSource: FileUploadingSource, type: MediaPickerContentType, blockId: String, route: UploadMediaRoute)
    func uploadImage(image: UIImage, type: String, blockId: String, route: UploadMediaRoute)
    func uploadFileAt(localPath: String, blockId: String, route: UploadMediaRoute)
    func createAndFetchBookmark(
        targetID: String,
        position: BlockPosition,
        url: AnytypeURL
    ) async throws
    func setAppearance(blockId: String, appearance: BlockLink.Appearance)
    func createTable(
        blockId: String,
        rowsCount: Int,
        columnsCount: Int,
        blockText: SafeNSAttributedString?
    ) async throws -> String
    func pasteContent()
}

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

    @discardableResult
    func addBlock(_ type: BlockContentType, blockId: String, blockText: SafeNSAttributedString? = nil) async throws -> String {
        try await addBlock(type, blockId: blockId, blockText: blockText, position: nil)
    }
    
    func turnInto(_ style: BlockText.Style, blockId: String) async throws {
        try await turnInto(style, blockId: blockId, route: nil)
    }
    
    func setBackgroundColor(_ color: BlockBackgroundColor, blockIds: [String]) {
        setBackgroundColor(color, blockIds: blockIds, route: nil)
    }
    
    func setAlignment(_ alignment: LayoutAlignment, blockIds: [String]) {
        setAlignment(alignment, blockIds: blockIds, route: nil)
    }
    
    func changeMarkup(blockIds: [String], markType: MarkupType) {
        changeMarkup(blockIds: blockIds, markType: markType, route: nil)
    }
    
    func toggleWholeBlockMarkup(
        _ attributedString: SafeNSAttributedString?,
        markup: MarkupType,
        info: BlockInformation
    ) async throws -> SafeNSAttributedString? {
        return try await toggleWholeBlockMarkup(attributedString, markup: markup, info: info, route: nil)
    }
    
    func setTextColor(_ color: BlockColor, blockIds: [String]) {
        setTextColor(color, blockIds: blockIds, route: nil)
    }

    func addLink(targetDetails: ObjectDetails, blockId: String, route: AnalyticsEventsRouteKind) async throws {
        try await addLink(targetDetails: targetDetails, blockId: blockId, position: .replace, route: route)
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
    operation: @escaping @MainActor @Sendable () async throws -> Value
) -> Task<Value, Error> {
    guard let owner else {
        return Task { @MainActor in try await operation() }
    }
    do {
        let scheduled = try owner.scheduleMutation(contextId: contextId)
        return Task { @MainActor in try await scheduled.run(operation: operation) }
    } catch {
        // A rejected UI intent must not start its original mutation later.
        return Task { throw error }
    }
}
