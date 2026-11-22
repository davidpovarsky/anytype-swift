import Foundation

struct AnyPublisher<Output, Failure: Error>: Sendable {}
final class PassthroughSubject<Output, Failure: Error>: Sendable {}
struct ObjectDetailsStorage: Sendable {}
struct ObjectDetails: Sendable {}
struct ParsedProperties: Sendable {}
struct ObjectPermissions: Sendable {}
struct SpaceSyncStatus: Sendable {}
enum DocumentMode: Sendable { case page }
enum BaseDocumentUpdate: Sendable { case changed }
struct BlockFocusPosition: Sendable {}
struct BlockInformation: Sendable, Equatable { let id: String }
enum TextBlockContentConfiguration { struct Actions {} }
protocol LinkToSearchDelegate: AnyObject {}
protocol InfoContainerProtocol: Sendable {
    func get(id: String) -> BlockInformation?
}
final class InfoContainerProbe: InfoContainerProtocol {
    let values: [String: BlockInformation]
    init(values: [String: BlockInformation]) { self.values = values }
    func get(id: String) -> BlockInformation? { values[id] }
}
final class DocumentProbe: BaseDocumentProtocol {
    let infoContainer: any InfoContainerProtocol
    let objectId: String
    let spaceId: String
    let detailsStorage = ObjectDetailsStorage()
    let children: [BlockInformation] = []
    let parsedProperties = ParsedProperties()
    let isLocked = false
    let isEmpty = false
    let isOpened = true
    let mode: DocumentMode = .page
    let details: ObjectDetails? = nil
    let permissions = ObjectPermissions()
    let syncStatus: SpaceSyncStatus? = nil
    let syncPublisher = AnyPublisher<[BaseDocumentUpdate], Never>()
    init(objectId: String, spaceId: String, block: BlockInformation) {
        self.objectId = objectId
        self.spaceId = spaceId
        infoContainer = InfoContainerProbe(values: [block.id: block])
    }
    func subscibeFor(update: [BaseDocumentUpdate]) -> AnyPublisher<[BaseDocumentUpdate], Never> {
        AnyPublisher()
    }
    @MainActor func open() async throws {}
    @MainActor func update() async throws {}
    @MainActor func close() async throws {}
}
@MainActor protocol VirtualTrailingBlockSessionProtocol: AnyObject {
    var isMaterialized: Bool { get }
}
@MainActor final class VirtualSessionProbe: VirtualTrailingBlockSessionProtocol {
    let isMaterialized: Bool
    init(isMaterialized: Bool) { self.isMaterialized = isMaterialized }
}

enum CutProbeFailure: Error, Equatable { case backend }
enum EditorDocumentWritePermission: Hashable { case edit }
enum EditorDocumentWriteRejection: Sendable { case unqualifiedDispatch }
enum EditorDocumentWriteError: Error {
    case rejected(EditorDocumentWriteRejection)
}
struct DocumentOwnedFileStaging {}
@MainActor
final class EditorDocumentWriteOwner {
    var registrations: [String] = []
    var validations: [ObjectIdentifier] = []
    var completion: String?
    private var isReleased = false
    private var releaseWaiters: [CheckedContinuation<Void, Never>] = []
    private var completionWaiters: [CheckedContinuation<String, Never>] = []
    func scheduleMutation(contextId: String, requiredPermissions: Set<EditorDocumentWritePermission>) throws -> ScheduledCutProbe {
        registrations.append(contextId)
        return ScheduledCutProbe(owner: self)
    }
    func validateDocument(_ document: some BaseDocumentProtocol) throws {
        validations.append(ObjectIdentifier(document))
    }
    func waitForRelease() async {
        if isReleased { return }
        await withCheckedContinuation { releaseWaiters.append($0) }
    }
    func release() {
        isReleased = true
        let waiters = releaseWaiters
        releaseWaiters.removeAll()
        for waiter in waiters { waiter.resume() }
    }
    func complete(_ value: String) {
        completion = value
        let waiters = completionWaiters
        completionWaiters.removeAll()
        for waiter in waiters { waiter.resume(returning: value) }
    }
    func waitForCompletion() async -> String {
        if let completion { return completion }
        return await withCheckedContinuation { completionWaiters.append($0) }
    }
}
@MainActor
struct ScheduledCutProbe {
    let owner: EditorDocumentWriteOwner
    func run<Value: Sendable>(operation: @escaping @MainActor @Sendable () async throws -> Value) async throws -> Value {
        await owner.waitForRelease()
        do {
            let value = try await operation()
            owner.complete("success")
            return value
        } catch {
            owner.complete((error as? CutProbeFailure) == .backend ? "backend-error" : "other-error")
            throw error
        }
    }
}
@MainActor
protocol BlockActionHandlerProtocol: AnyObject, Sendable {
    var documentWriteOwner: EditorDocumentWriteOwner? { get }
    var documentWriteContextID: String { get }
}
@MainActor
final class ActionHandlerProbe: BlockActionHandlerProtocol {
    let documentWriteOwner: EditorDocumentWriteOwner?
    let documentWriteContextID: String
    init(owner: EditorDocumentWriteOwner?, contextID: String) {
        documentWriteOwner = owner
        documentWriteContextID = contextID
    }
}
struct PasteboardPasteResult: Sendable {}
protocol PasteboardBlockServiceProtocol: AnyObject, Sendable {
    var hasValidURL: Bool { get }
    func pasteInsideBlock(objectId: String, spaceId: String, focusedBlockId: String, range: NSRange,
                          handleLongOperation: @escaping () -> Void,
                          completion: @escaping @MainActor (PasteboardPasteResult?) -> Void)
    func pasteInSelectedBlocks(objectId: String, spaceId: String, selectedBlockIds: [String],
                               handleLongOperation: @escaping () -> Void,
                               completion: @escaping @MainActor (PasteboardPasteResult?) -> Void)
    func copy(objectId: String, blockInfos: [BlockInformation], blocksIds: [String], selectedTextRange: NSRange) async throws
    func cut(objectId: String, blockInfos: [BlockInformation], blocksIds: [String], selectedTextRange: NSRange) async throws
}
struct CutObservation: Sendable, Equatable {
    let objectId: String
    let blockInfos: [BlockInformation]
    let blocksIds: [String]
    let range: NSRange
}
actor PasteboardBlockService: PasteboardBlockServiceProtocol {
    nonisolated let hasValidURL = false
    private let throwsBackend: Bool
    private var observations: [CutObservation] = []
    private var observers: [CheckedContinuation<CutObservation, Never>] = []
    init(throwsBackend: Bool = false) { self.throwsBackend = throwsBackend }
    @MainActor
    static func bindOriginal(_ service: any PasteboardBlockServiceProtocol,
                             owner: EditorDocumentWriteOwner,
                             staging: DocumentOwnedFileStaging) throws -> any PasteboardBlockServiceProtocol {
        service
    }
    nonisolated func pasteInsideBlock(objectId: String, spaceId: String, focusedBlockId: String, range: NSRange,
                                     handleLongOperation: @escaping () -> Void,
                                     completion: @escaping @MainActor (PasteboardPasteResult?) -> Void) {}
    nonisolated func pasteInSelectedBlocks(objectId: String, spaceId: String, selectedBlockIds: [String],
                                          handleLongOperation: @escaping () -> Void,
                                          completion: @escaping @MainActor (PasteboardPasteResult?) -> Void) {}
    func copy(objectId: String, blockInfos: [BlockInformation], blocksIds: [String], selectedTextRange: NSRange) async throws {}
    func cut(objectId: String, blockInfos: [BlockInformation], blocksIds: [String], selectedTextRange: NSRange) async throws {
        let value = CutObservation(objectId: objectId, blockInfos: blockInfos, blocksIds: blocksIds, range: selectedTextRange)
        observations.append(value)
        let waiting = observers
        observers.removeAll()
        for observer in waiting { observer.resume(returning: value) }
        if throwsBackend { throw CutProbeFailure.backend }
    }
    func values() -> [CutObservation] { observations }
    func firstObservation() async -> CutObservation {
        if let first = observations.first { return first }
        return await withCheckedContinuation { observers.append($0) }
    }
}
struct Container: Sendable {
    static let shared = Container()
    func pasteboardBlockService() -> any PasteboardBlockServiceProtocol { PasteboardBlockService() }
}
@MainActor
protocol CutBoundaryInvoking: AnyObject {
    func invokeCut(_ range: NSRange)
}
enum CutBoundaryKind { case text, table }
@MainActor
func makeCutBoundary(kind: CutBoundaryKind, document: any BaseDocumentProtocol, info: BlockInformation,
                     actionHandler: any BlockActionHandlerProtocol,
                     service: (any PasteboardBlockDocumentServiceProtocol)?,
                     virtualSession: (any VirtualTrailingBlockSessionProtocol)? = nil) -> any CutBoundaryInvoking {
    switch kind {
    case .text:
        return TextBlockActionHandler(document: document, info: info, actionHandler: actionHandler,
                                      service: service, virtualSession: virtualSession)
    case .table:
        return SimpleTablesTextBlockActionHandler(document: document, info: info, actionHandler: actionHandler,
                                                  service: service)
    }
}
