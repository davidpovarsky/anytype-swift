import Foundation

@MainActor
final class TextBlockActionHandler: TextBlockActionHandlerProtocol, LinkToSearchDelegate, CutBoundaryInvoking {
    private let document: any BaseDocumentProtocol
    var info: BlockInformation
    private let actionHandler: any BlockActionHandlerProtocol
    private weak var pasteboardService: (any PasteboardBlockDocumentServiceProtocol)?
    let resetSubject = PassthroughSubject<NSAttributedString?, Never>()
    let focusSubject = PassthroughSubject<BlockFocusPosition, Never>()
    func textBlockActions() -> TextBlockContentConfiguration.Actions { .init() }
    func resetEmptyBlockFork() {}
    func invokeCut(_ range: NSRange) { cut(range: range) }
    private var virtualBlockSession: (any VirtualTrailingBlockSessionProtocol)?
    init(document: any BaseDocumentProtocol, info: BlockInformation, actionHandler: any BlockActionHandlerProtocol,
         service: (any PasteboardBlockDocumentServiceProtocol)?, virtualSession: (any VirtualTrailingBlockSessionProtocol)?) {
        self.document = document
        self.info = info
        self.actionHandler = actionHandler
        self.pasteboardService = service
        self.virtualBlockSession = virtualSession
    }
    private var isVirtualUnmaterialized: Bool {
        guard let virtualBlockSession else { return false }
        return !virtualBlockSession.isMaterialized
    }
    private func cut(range: NSRange) {
        guard !isVirtualUnmaterialized else { return }
        actionHandler.scheduleMutationTask { [self] () -> Void in
            try await pasteboardService?.cut(document: document, blocksIds: [info.id], selectedTextRange: range)
        }
    }
}

final class SimpleTablesTextBlockActionHandler: TextBlockActionHandlerProtocol, LinkToSearchDelegate, CutBoundaryInvoking {
    private let document: any BaseDocumentProtocol
    var info: BlockInformation
    private let actionHandler: any BlockActionHandlerProtocol
    private weak var pasteboardService: (any PasteboardBlockDocumentServiceProtocol)?
    let resetSubject = PassthroughSubject<NSAttributedString?, Never>()
    let focusSubject = PassthroughSubject<BlockFocusPosition, Never>()
    func textBlockActions() -> TextBlockContentConfiguration.Actions { .init() }
    func resetEmptyBlockFork() {}
    func invokeCut(_ range: NSRange) { cut(range: range) }
    init(document: any BaseDocumentProtocol, info: BlockInformation, actionHandler: any BlockActionHandlerProtocol,
         service: (any PasteboardBlockDocumentServiceProtocol)?) {
        self.document = document
        self.info = info
        self.actionHandler = actionHandler
        self.pasteboardService = service
    }
    private func cut(range: NSRange) {
        actionHandler.scheduleMutationTask { [self] () -> Void in
            try await pasteboardService?.cut(document: document, blocksIds: [info.id], selectedTextRange: range)
        }
    }
}
