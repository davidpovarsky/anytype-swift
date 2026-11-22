import Foundation



// Convenience wrapper of PasteboardBlockService
final class PasteboardBlockDocumentService: PasteboardBlockDocumentServiceProtocol, Sendable {
    
    private let service: any PasteboardBlockServiceProtocol
    private let documentOwner: EditorDocumentWriteOwner?

    init(service: any PasteboardBlockServiceProtocol = Container.shared.pasteboardBlockService()) {
        self.service = service
        documentOwner = nil
    }

    private init(service: any PasteboardBlockServiceProtocol, documentOwner: EditorDocumentWriteOwner) {
        self.service = service
        self.documentOwner = documentOwner
    }

    @MainActor
    static func bindOriginal(_ service: any PasteboardBlockDocumentServiceProtocol,
                             owner: EditorDocumentWriteOwner,
                             staging: DocumentOwnedFileStaging) throws -> any PasteboardBlockDocumentServiceProtocol {
        guard let original = service as? PasteboardBlockDocumentService, original.documentOwner == nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        let lower = try PasteboardBlockService.bindOriginal(original.service, owner: owner, staging: staging)
        return PasteboardBlockDocumentService(service: lower, documentOwner: owner)
    }
    
    var hasValidURL: Bool {
        service.hasValidURL
    }
    
    func pasteInsideBlock(
        objectId: String,
        spaceId: String,
        focusedBlockId: String,
        range: NSRange,
        handleLongOperation:  @escaping () -> Void,
        completion: @escaping @MainActor (_ pasteResult: PasteboardPasteResult?) -> Void
    ) {
        service.pasteInsideBlock(
            objectId: objectId,
            spaceId: spaceId,
            focusedBlockId: focusedBlockId,
            range: range,
            handleLongOperation: handleLongOperation,
            completion: completion
        )
    }
    
    func pasteInSelectedBlocks(
        objectId: String,
        spaceId: String,
        selectedBlockIds: [String],
        handleLongOperation:  @escaping () -> Void,
        completion: @escaping @MainActor (_ pasteResult: PasteboardPasteResult?) -> Void
    ) {
        service.pasteInSelectedBlocks(
            objectId: objectId,
            spaceId: spaceId,
            selectedBlockIds: selectedBlockIds,
            handleLongOperation: handleLongOperation,
            completion: completion
        )
    }
    
    func copy(document: some BaseDocumentProtocol, blocksIds: [String], selectedTextRange: NSRange) async throws {
        if let documentOwner { try await documentOwner.validateDocument(document) }
        let blockInformations = blocksIds.compactMap { document.infoContainer.get(id: $0) }
        try await service.copy(
            objectId: document.objectId,
            blockInfos: blockInformations,
            blocksIds: blocksIds,
            selectedTextRange: selectedTextRange
        )
    }
    
    func cut(document: some BaseDocumentProtocol, blocksIds: [String], selectedTextRange: NSRange) async throws {
        if let documentOwner { try await documentOwner.validateDocument(document) }
        let blockInformations = blocksIds.compactMap { document.infoContainer.get(id: $0) }
        try await service.cut(
            objectId: document.objectId,
            blockInfos: blockInformations,
            blocksIds: blocksIds,
            selectedTextRange: selectedTextRange
        )
    }
}

private extension PasteboardBlockDocumentService {
    enum Constants {
        static let longOperationTime: Double = 0.5
    }
}
