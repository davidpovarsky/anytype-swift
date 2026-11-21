import Services
@preconcurrency import Foundation
import Combine
import AnytypeCore

final class PasteboardBlockService: PasteboardBlockServiceProtocol, Sendable {
    
    private let pasteboardHelper: any PasteboardHelperProtocol
    private let pasteboardMiddlewareService: any PasteboardMiddlewareServiceProtocol
    private let documentOwner: EditorDocumentWriteOwner?
    private let ownedStaging: DocumentOwnedFileStaging?
    
    private let tasks = SynchronizedArray<AnyCancellable>()

    init() {
        pasteboardHelper = Container.shared.pasteboardHelper()
        pasteboardMiddlewareService = Container.shared.pasteboardMiddleService()
        documentOwner = nil
        ownedStaging = nil
    }

    private init(original: PasteboardBlockService, owner: EditorDocumentWriteOwner, staging: DocumentOwnedFileStaging) {
        pasteboardHelper = original.pasteboardHelper
        pasteboardMiddlewareService = original.pasteboardMiddlewareService
        documentOwner = owner
        ownedStaging = staging
    }

    @MainActor
    static func bindOriginal(_ service: any PasteboardBlockServiceProtocol,
                             owner: EditorDocumentWriteOwner,
                             staging: DocumentOwnedFileStaging) throws -> any PasteboardBlockServiceProtocol {
        guard let original = service as? PasteboardBlockService, original.documentOwner == nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        try owner.validateOwnership()
        try staging.requireOwner(owner)
        return PasteboardBlockService(original: original, owner: owner, staging: staging)
    }
    
    var hasValidURL: Bool {
        guard let documentOwner else { return pasteboardHelper.hasValidURL }
        guard Thread.isMainThread else { return false }
        return MainActor.assumeIsolated {
            (try? documentOwner.performSynchronousOperation(requiresEditing: false) { pasteboardHelper.hasValidURL }) ?? false
        }
    }
    
    var pasteboardContent: PasteboardContent? {
        guard let documentOwner else { return pasteboardHelper.pasteboardContent }
        guard Thread.isMainThread else { return nil }
        return MainActor.assumeIsolated {
            try? documentOwner.performSynchronousOperation(requiresEditing: false) { pasteboardHelper.pasteboardContent }
        }
    }
    
    func pasteInsideBlock(
        objectId: String,
        spaceId: String,
        focusedBlockId: String,
        range: NSRange,
        handleLongOperation:  @escaping () -> Void,
        completion: @escaping @MainActor (_ pasteResult: PasteboardPasteResult?) -> Void
    ) {
        let context = PasteboardActionContext.focused(blockId: focusedBlockId, range: range)
        paste(objectId: objectId, spaceId: spaceId, context: context, handleLongOperation: handleLongOperation, completion: completion)
    }
    
    func pasteInSelectedBlocks(
        objectId: String,
        spaceId: String,
        selectedBlockIds: [String],
        handleLongOperation:  @escaping () -> Void,
        completion: @escaping @MainActor (_ pasteResult: PasteboardPasteResult?) -> Void
    ) {
        let context = PasteboardActionContext.selected(blockIds: selectedBlockIds)
        paste(objectId: objectId, spaceId: spaceId, context: context, handleLongOperation: handleLongOperation, completion: completion)
    }
    
    private func paste(
        objectId: String,
        spaceId: String,
        context: PasteboardActionContext,
        handleLongOperation:  @escaping () -> Void,
        completion: @escaping @MainActor (_ pasteResult: PasteboardPasteResult?) -> Void
    ) {
        let scheduled: EditorDocumentScheduledWrite?
        if let documentOwner {
            guard Thread.isMainThread else { return }
            scheduled = MainActor.assumeIsolated {
                try? documentOwner.performSynchronousOperation(contextId: objectId, spaceId: spaceId) {
                    try documentOwner.scheduleMutation(contextId: objectId)
                }
            }
            guard scheduled != nil else { return }
        } else {
            scheduled = nil
        }
        
        let workItem = DispatchWorkItem {
            if let documentOwner = self.documentOwner {
                guard Thread.isMainThread else { return }
                MainActor.assumeIsolated {
                    try? documentOwner.performSynchronousOperation(contextId: objectId, requiresEditing: false) { handleLongOperation() }
                }
            } else {
                handleLongOperation()
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + Constants.longOperationTime, execute: workItem)
        
        let pasteboardTask = PasteboardTask(
            objectId: objectId,
            spaceId: spaceId,
            pasteboardHelper: pasteboardHelper,
            pasteboardMiddlewareService: pasteboardMiddlewareService,
            context: context,
            ownedStaging: ownedStaging
        )
        
        let task = Task { @Sendable in
            if let documentOwner = self.documentOwner, let scheduled {
                // Reservation precedes this Task. Both the original native paste
                // and its actual MainActor completion remain within that lease.
                try? await scheduled.run {
                    let pasteResult = try? await documentOwner.performMutation(spaceId: spaceId, createdInContext: objectId) {
                        try await pasteboardTask.start()
                    }
                    try await MainActor.run {
                        try documentOwner.performSynchronousOperation(contextId: objectId) { completion(pasteResult) }
                    }
                }
                workItem.cancel()
            } else {
                let pasteResult = try? await pasteboardTask.start()
                DispatchQueue.main.async {
                    workItem.cancel()
                    completion(pasteResult)
                }
            }
        }
        .cancellable()
        
        tasks.append(task)
    }
    
    func copy(
        objectId: String,
        blockInfos: [BlockInformation],
        blocksIds: [String],
        selectedTextRange: NSRange
    ) async throws {
        if let documentOwner {
            let result = try await documentOwner.performRead(contextId: objectId, rpcNames: ["BlockCopy"]) { [pasteboardMiddlewareService] in
                try await pasteboardMiddlewareService.copy(
                    blockInformations: blockInfos, objectId: objectId, selectedTextRange: selectedTextRange
                )
            }
            if let result {
                try await MainActor.run {
                    try documentOwner.performSynchronousOperation(contextId: objectId, requiresEditing: false) {
                        pasteboardHelper.setItems(textSlot: result.textSlot, htmlSlot: result.htmlSlot, blocksSlots: result.blockSlot)
                    }
                }
            }
            return
        }
        if let result = try await pasteboardMiddlewareService.copy(
            blockInformations: blockInfos,
            objectId: objectId,
            selectedTextRange: selectedTextRange
        ) {
            pasteboardHelper.setItems(textSlot: result.textSlot, htmlSlot: result.htmlSlot, blocksSlots: result.blockSlot)
        }
    }
    
    func cut(
        objectId: String,
        blockInfos: [BlockInformation],
        blocksIds: [String],
        selectedTextRange: NSRange
    ) async throws {
        if let documentOwner {
            let result = try await documentOwner.performMutation(contextId: objectId) { [pasteboardMiddlewareService] in
                try await pasteboardMiddlewareService.cut(
                    blockInformations: blockInfos, objectId: objectId, selectedTextRange: selectedTextRange
                )
            }
            if let result {
                try await MainActor.run {
                    try documentOwner.performSynchronousOperation(contextId: objectId) {
                        pasteboardHelper.setItems(textSlot: result.textSlot, htmlSlot: result.htmlSlot, blocksSlots: result.blockSlot)
                    }
                }
            }
            return
        }
        if let result = try await pasteboardMiddlewareService.cut(blockInformations: blockInfos, objectId: objectId, selectedTextRange: selectedTextRange) {
            pasteboardHelper.setItems(textSlot: result.textSlot, htmlSlot: result.htmlSlot, blocksSlots: result.blockSlot)
        }
    }
}

private extension PasteboardBlockService {
    enum Constants {
        static let longOperationTime: Double = 0.5
    }
}

