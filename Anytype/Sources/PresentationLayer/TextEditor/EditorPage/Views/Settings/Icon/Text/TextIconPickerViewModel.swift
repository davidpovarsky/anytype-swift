import Foundation
import Services
import UniformTypeIdentifiers
import AnytypeCore

struct TextIconPickerData: Identifiable, Hashable {
    let contextId: String
    let objectId: String
    let spaceId: String

    var id: Int { hashValue }
}

@MainActor
@Observable
final class TextIconPickerViewModel {

    @ObservationIgnored
    private let fileService: any FileActionsServiceProtocol
    @ObservationIgnored
    private let textServiceHandler: any TextServiceProtocol
    @ObservationIgnored
    private let documentWriteOwner: EditorDocumentWriteOwner?

    @ObservationIgnored
    private let contextId: String
    @ObservationIgnored
    private let objectId: String
    @ObservationIgnored
    private let spaceId: String

    init(data: TextIconPickerData, dependencies: BlockActionServiceDependencies = .original()) {
        self.contextId = data.contextId
        self.objectId = data.objectId
        self.spaceId = data.spaceId
        self.fileService = dependencies.fileService
        self.textServiceHandler = dependencies.textServiceHandler
        self.documentWriteOwner = dependencies.documentWriteOwner
    }
    

    func setEmoji(_ emojiUnicode: String)  {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: contextId) { [self] in
            try validateSource()
            try await textServiceHandler.setTextIcon(
                contextId: contextId,
                blockId: objectId,
                imageObjectId: "",
                emojiUnicode: emojiUnicode
            )
        }
    }

    func uploadImage(from itemProvider: NSItemProvider) {
        let safeSendableItemProvider = itemProvider.sendable()
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: contextId) { [self] in
            try validateSource()
            let fileDetails = try await fileService.uploadImage(spaceId: spaceId, source: .itemProvider(safeSendableItemProvider.value), origin: .none, createdInContext: contextId, createdInContextRef: objectId)
            try await textServiceHandler.setTextIcon(
                contextId: contextId,
                blockId: objectId,
                imageObjectId: fileDetails.id,
                emojiUnicode: ""
            )
        }
    }

    private func validateSource() throws {
        try documentWriteOwner?.performSynchronousOperation(
            contextId: contextId, spaceId: spaceId, requiresEditing: false
        ) { }
    }
}

