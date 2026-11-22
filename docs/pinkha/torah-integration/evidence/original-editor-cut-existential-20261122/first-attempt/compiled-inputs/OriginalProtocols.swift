import Foundation


protocol BaseDocumentProtocol: AnyObject, Sendable {
    var infoContainer: any InfoContainerProtocol { get }
    var detailsStorage: ObjectDetailsStorage { get }
    var children: [BlockInformation] { get }
    var parsedProperties: ParsedProperties { get }
    var objectId: String { get }
    var spaceId: String { get }
    var isLocked: Bool { get }
    var isEmpty: Bool { get }
    var isOpened: Bool { get }
    var mode: DocumentMode { get }
    var details: ObjectDetails? { get }
    var permissions: ObjectPermissions { get }
    var syncStatus: SpaceSyncStatus? { get }
    
    func subscibeFor(update: [BaseDocumentUpdate]) -> AnyPublisher<[BaseDocumentUpdate], Never>
    var syncPublisher: AnyPublisher<[BaseDocumentUpdate], Never> { get }
    
    @MainActor
    func open() async throws
    
    @MainActor
    func update() async throws
    
    @MainActor
    func close() async throws
}


protocol PasteboardBlockDocumentServiceProtocol: AnyObject, Sendable {
    var hasValidURL: Bool { get }
    
    func pasteInsideBlock(
        objectId: String,
        spaceId: String,
        focusedBlockId: String,
        range: NSRange,
        handleLongOperation: @escaping () -> Void,
        completion: @escaping @MainActor (_ pasteResult: PasteboardPasteResult?) -> Void
    )
    func pasteInSelectedBlocks(
        objectId: String,
        spaceId: String,
        selectedBlockIds: [String],
        handleLongOperation:  @escaping () -> Void,
        completion: @escaping @MainActor (_ pasteResult: PasteboardPasteResult?) -> Void
    )
    
    func copy(document: some BaseDocumentProtocol, blocksIds: [String], selectedTextRange: NSRange) async throws
    func cut(document: some BaseDocumentProtocol, blocksIds: [String], selectedTextRange: NSRange) async throws
}



@MainActor
protocol TextBlockActionHandlerProtocol: AnyObject {
    var info: BlockInformation { get set }

    var resetSubject: PassthroughSubject<NSAttributedString?, Never> { get }
    var focusSubject: PassthroughSubject<BlockFocusPosition, Never> { get }

    func textBlockActions() -> TextBlockContentConfiguration.Actions
    /// Undo restored the block this handler forked away from; a completed or in-flight fork
    /// must not gate a fresh first fill nor rebind to the deleted id.
    func resetEmptyBlockFork()
}
