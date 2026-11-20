import Foundation

public enum Anytype_Model_Block {
    public enum Content {
        public enum Text {
            public struct Marks: Equatable, Sendable {
                public var retainedFixtureMarks: [String] = []
                public init() {}
            }
        }
    }
}
public enum BlockText {
    public enum Style: Sendable, Equatable { case text, quote }
}
public enum Anytype_Rpc {
    public enum Block {
        public enum Split {
            public enum Request {
                public enum Mode: Sendable, Equatable { case fixture }
            }
        }
    }
}
enum ObjectHeaderEmptyUsecase: Hashable, Codable { case full }
enum ObjectHeaderExpectedLayout: Hashable, Codable { case fixture }
protocol InfoContainerProtocol: AnyObject, Sendable {}
final class FixtureInfo: InfoContainerProtocol {}
final class ObjectDetailsStorage: Sendable {}
struct BlockInformation: Sendable {}
struct ParsedProperties: Sendable {}
struct ObjectDetails: Sendable {}
struct ObjectPermissions: Sendable {}
struct SpaceSyncStatus: Sendable {}
enum BaseDocumentUpdate: Sendable { case fixture }
struct AnyPublisher<Output, Failure: Error>: Sendable {}
actor DocumentLifecycleProbe {
    private var operations: [String] = []
    func record(_ operation: String) { operations.append(operation) }
    func snapshot() -> [String] { operations }
}
final class DocumentProbe: BaseDocumentProtocol, @unchecked Sendable {
    let objectId: String
    let spaceId: String
    let mode: DocumentMode
    let isOpened: Bool
    let lifecycle: DocumentLifecycleProbe
    let infoContainer: any InfoContainerProtocol = FixtureInfo()
    let detailsStorage = ObjectDetailsStorage()
    var children: [BlockInformation] { [] }
    var parsedProperties: ParsedProperties { ParsedProperties() }
    var isLocked: Bool { false }
    var isEmpty: Bool { false }
    var details: ObjectDetails? { nil }
    var permissions: ObjectPermissions { ObjectPermissions() }
    var syncStatus: SpaceSyncStatus? { nil }
    var syncPublisher: AnyPublisher<[BaseDocumentUpdate], Never> { AnyPublisher() }
    init(_ object: String = "object", space: String = "space", mode: DocumentMode = .handling,
         opened: Bool = true, lifecycle: DocumentLifecycleProbe = DocumentLifecycleProbe()) {
        objectId = object; spaceId = space; self.mode = mode; isOpened = opened; self.lifecycle = lifecycle
    }
    func subscibeFor(update: [BaseDocumentUpdate]) -> AnyPublisher<[BaseDocumentUpdate], Never> { AnyPublisher() }
    @MainActor func open() async throws { await lifecycle.record("open") }
    @MainActor func update() async throws { await lifecycle.record("update") }
    @MainActor func close() async throws { await lifecycle.record("close") }
}
struct TextCall: Sendable {
    let operation: String
    let context: String
    let block: String
    var body: MiddlewareString?
    var payload: [String] = []
    var range: NSRange?
    var style: TextServiceProtocol.Style?
    var mode: TextServiceProtocol.SplitMode?
}
enum TextProbeFailure: Error, Equatable, Sendable { case deliberate, cancel }
actor TextProbe: TextServiceProtocol {
    let failure: TextProbeFailure?
    private var calls: [TextCall] = []
    init(failure: TextProbeFailure? = nil) { self.failure = failure }
    func snapshot() -> [TextCall] { calls }
    private func record(_ call: TextCall) throws {
        calls.append(call)
        if failure == .cancel { throw CancellationError() }
        if let failure { throw failure }
    }
    func setText(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        try record(.init(operation: "text", context: contextId, block: blockId, body: middlewareString))
    }
    func setTextForced(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        try record(.init(operation: "forced", context: contextId, block: blockId, body: middlewareString))
    }
    func setStyle(contextId: String, blockId: String, style: Style) async throws {
        try record(.init(operation: "style", context: contextId, block: blockId, style: style))
    }
    func split(contextId: String, blockId: String, range: NSRange, style: Style, mode: SplitMode) async throws -> String {
        try record(.init(operation: "split", context: contextId, block: blockId, range: range, style: style, mode: mode))
        return "injected-created-block"
    }
    func checked(contextId: String, blockId: String, newValue: Bool) async throws {
        try record(.init(operation: "checked", context: contextId, block: blockId, payload: [String(newValue)]))
    }
    func merge(contextId: String, firstBlockId: String, secondBlockId: String) async throws {
        try record(.init(operation: "merge", context: contextId, block: firstBlockId, payload: [secondBlockId]))
    }
    func setTextIcon(contextId: String, blockId: String, imageObjectId: String, emojiUnicode: String) async throws {
        try record(.init(operation: "icon", context: contextId, block: blockId, payload: [imageObjectId, emojiUnicode]))
    }
}
enum LocalEvent: Sendable {
    case general
    case setStyle(blockId: String)
    case setToggled(blockId: String)
    case setText(blockId: String, text: MiddlewareString)
    case setLoadingState(blockId: String)
}
actor EventProbe {
    static let shared = EventProbe()
    private var events: [[String]] = []
    private var detailed: [TextCall] = []
    func record(_ context: String, _ block: String) { events.append([context, block]) }
    func recordDetailed(_ call: TextCall) { detailed.append(call) }
    func snapshot() -> [[String]] { events }
    func detailedSnapshot() -> [TextCall] { detailed }
}
struct EventsBunch: Sendable {
    let contextId: String
    let localEvents: [LocalEvent]
    func send() async {
        for event in localEvents {
            let call: TextCall
            switch event {
            case .general: call = .init(operation: "general", context: contextId, block: "")
            case .setStyle(let block):
                await EventProbe.shared.record(contextId, block)
                call = .init(operation: "style", context: contextId, block: block)
            case .setToggled(let block): call = .init(operation: "toggle", context: contextId, block: block)
            case .setText(let block, let text): call = .init(operation: "text", context: contextId, block: block, body: text)
            case .setLoadingState(let block): call = .init(operation: "loading", context: contextId, block: block)
            }
            await EventProbe.shared.recordDetailed(call)
        }
    }
}
actor LocalPublisherProbe: EditorLocalEventPublishing {
    private var calls: [TextCall] = []
    let service: TextProbe?
    init(service: TextProbe? = nil) { self.service = service }
    func snapshot() -> [TextCall] { calls }
    func refresh(contextId: String) { calls.append(.init(operation: "general", context: contextId, block: "")) }
    func setStyle(contextId: String, blockId: String) async {
        let completed = await service?.snapshot().map(\.operation) ?? []
        calls.append(.init(operation: "style", context: contextId, block: blockId, payload: completed))
    }
    func setToggled(contextId: String, blockId: String) { calls.append(.init(operation: "toggle", context: contextId, block: blockId)) }
    func setText(contextId: String, blockId: String, text: MiddlewareString) {
        calls.append(.init(operation: "text", context: contextId, block: blockId, body: text))
    }
    func setLoadingState(contextId: String, blockId: String) {
        calls.append(.init(operation: "loading", context: contextId, block: blockId))
    }
}
protocol ObjectActionsServiceProtocol: AnyObject, Sendable {}
protocol BlockServiceProtocol: AnyObject, Sendable {}
protocol BookmarkServiceProtocol: AnyObject, Sendable {}
protocol FileActionsServiceProtocol: AnyObject, Sendable {}
protocol ObjectTypeProviderProtocol: AnyObject, Sendable {}
@MainActor protocol KeyboardInsertedBlocksStorageProtocol: AnyObject {}
final class ServiceMarker: ObjectActionsServiceProtocol, BlockServiceProtocol, BookmarkServiceProtocol,
    FileActionsServiceProtocol, ObjectTypeProviderProtocol, Sendable {
    let name: String
    init(_ name: String) { self.name = name }
}
@MainActor final class KeyboardMarker: KeyboardInsertedBlocksStorageProtocol {
    let name: String
    init(_ name: String) { self.name = name }
}
struct Container: Sendable {
    static let shared = Container()
    let nativeText = TextProbe()
    let nativeHandler: TextServiceHandler
    let object = ServiceMarker("original-object")
    let block = ServiceMarker("original-block")
    let bookmark = ServiceMarker("original-bookmark")
    let file = ServiceMarker("original-file")
    let types = ServiceMarker("original-types")
    @MainActor static let originalKeyboard = KeyboardMarker("original-keyboard")
    @MainActor var keyboard: KeyboardMarker { Self.originalKeyboard }
    init() { nativeHandler = TextServiceHandler(textService: nativeText) }
    func textService() -> any TextServiceProtocol { nativeText }
    func textServiceHandler() -> any TextServiceProtocol { nativeHandler }
    func objectActionsService() -> any ObjectActionsServiceProtocol { object }
    func blockService() -> any BlockServiceProtocol { block }
    func bookmarkService() -> any BookmarkServiceProtocol { bookmark }
    func fileActionsService() -> any FileActionsServiceProtocol { file }
    func objectTypeProvider() -> any ObjectTypeProviderProtocol { types }
    @MainActor func keyboardInsertedBlocksStorage() -> any KeyboardInsertedBlocksStorageProtocol { keyboard }
}
@MainActor protocol BlockActionServiceProtocol {}
@MainActor final class EditorMainItemModelsHolder {}
@MainActor final class EditorCursorManager {}
struct BoundaryCheck: Codable { let name: String; let passed: Bool }
@MainActor final class BoundaryChecks {
    private(set) var checks: [BoundaryCheck] = []
    func expect(_ condition: Bool, _ name: String) { checks.append(.init(name: name, passed: condition)) }
    func validate(_ name: String, data: EditorPageObject, document: DocumentProbe,
                  expected: PreparedEditorPageDocumentError? = nil) {
        do {
            try PreparedEditorPageDocument.validate(data: data, document: document)
            expect(expected == nil, name)
        } catch {
            expect((error as? PreparedEditorPageDocumentError) == expected && expected != nil, name)
        }
    }
}
enum BoundaryFixtureError: Error { case failed }
@main struct OriginalEditorBoundaryFixture {
    @MainActor static func main() async throws {
        let result = BoundaryChecks()
        let lifecycle = DocumentLifecycleProbe()
        let original = DocumentProbe(lifecycle: lifecycle)
        for (name, mode) in [("opened_handling", DocumentMode.handling), ("opened_preview", .preview),
                             ("same_history_version", .version("version-one"))] {
            result.validate(name, data: .init(objectId: "object", spaceId: "space", mode: mode),
                            document: DocumentProbe(mode: mode, lifecycle: lifecycle))
        }
        for (name, object, space) in [("empty_object", "", "space"), ("whitespace_object", " \n", "space"),
                                      ("empty_space", "object", ""), ("whitespace_space", "object", "\t")] {
            result.validate(name, data: .init(objectId: object, spaceId: space), document: original, expected: .emptyIdentity)
        }
        result.validate("other_object", data: .init(objectId: "other", spaceId: "space"), document: original, expected: .objectMismatch)
        result.validate("other_space", data: .init(objectId: "object", spaceId: "other"), document: original, expected: .spaceMismatch)
        result.validate("other_mode", data: .init(objectId: "object", spaceId: "space", mode: .preview), document: original, expected: .modeMismatch)
        result.validate("other_history_version", data: .init(objectId: "object", spaceId: "space", mode: .version("second")),
                        document: DocumentProbe(mode: .version("first")), expected: .modeMismatch)
        result.validate("closed_document", data: .init(objectId: "object", spaceId: "space"),
                        document: DocumentProbe(opened: false), expected: .documentNotOpened)
        result.validate("identifier_not_normalized", data: .init(objectId: " object ", spaceId: "space"),
                        document: original, expected: .objectMismatch)
        result.expect(await lifecycle.snapshot().isEmpty, "validation_did_not_open_or_close")
        let custom = TextProbe()
        let handler = TextServiceHandler(textService: custom)
        var marks = Anytype_Model_Block.Content.Text.Marks()
        marks.retainedFixtureMarks = ["bold:0:4", "link:5:8"]
        let body = MiddlewareString(text: "שלום English 👩🏽‍💻", marks: marks)
        try await handler.setText(contextId: "doc", blockId: "first", middlewareString: body)
        var calls = await custom.snapshot()
        result.expect(calls.count == 1 && calls[0].operation == "text" && calls[0].context == "doc"
                      && calls[0].block == "first" && calls[0].body?.text == body.text && calls[0].body?.marks == marks,
                      "custom_text_preserves_body_and_marks")
        try await handler.setTextForced(contextId: "doc", blockId: "second", middlewareString: body)
        calls = await custom.snapshot()
        result.expect(calls.count == 2 && calls[1].operation == "forced" && calls[1].block == "second"
                      && calls[1].body?.marks == marks, "forced_text_forwarded")
        let beforeSplit = await EventProbe.shared.snapshot()
        let range = NSRange(location: 2, length: "👩🏽‍💻".utf16.count)
        let created = try await handler.split(contextId: "doc", blockId: "first", range: range, style: .quote, mode: .fixture)
        calls = await custom.snapshot()
        result.expect(created == "injected-created-block" && calls.last?.range == range && calls.last?.style == .quote
                      && calls.last?.mode == .fixture, "split_result_and_utf16")
        result.expect(await EventProbe.shared.snapshot() == beforeSplit, "split_does_not_publish")
        try await handler.checked(contextId: "doc", blockId: "first", newValue: true)
        result.expect(await custom.snapshot().last?.payload == ["true"], "checked_payload")
        try await handler.merge(contextId: "doc", firstBlockId: "first", secondBlockId: "second")
        calls = await custom.snapshot()
        result.expect(calls.last?.block == "first" && calls.last?.payload == ["second"], "merge_order")
        try await handler.setTextIcon(contextId: "doc", blockId: "first", imageObjectId: "image", emojiUnicode: "📖")
        result.expect(await custom.snapshot().last?.payload == ["image", "📖"], "icon_payload")
        try await handler.setStyle(contextId: "doc", blockId: "first", style: .quote)
        calls = await custom.snapshot()
        let eventsAfterStyle = await EventProbe.shared.snapshot()
        result.expect(calls.last?.operation == "style" && calls.last?.style == .quote
                      && eventsAfterStyle.last == ["doc", "first"], "style_follows_service_then_event")
        let failed = TextProbe(failure: .deliberate)
        let eventsBeforeFailure = await EventProbe.shared.snapshot()
        var failedAsExpected = false
        do { try await TextServiceHandler(textService: failed).setStyle(contextId: "failed", blockId: "first", style: .text) }
        catch { failedAsExpected = (error as? TextProbeFailure) == .deliberate }
        let failedCalls = await failed.snapshot()
        let eventsAfterFailure = await EventProbe.shared.snapshot()
        result.expect(failedAsExpected && failedCalls.count == 1 && eventsAfterFailure == eventsBeforeFailure,
                      "style_failure_propagates_without_publish")
        let cancelled = TextProbe(failure: .cancel)
        var cancelledAsExpected = false
        do { try await TextServiceHandler(textService: cancelled).setText(contextId: "cancelled", blockId: "first", middlewareString: body) }
        catch { cancelledAsExpected = error is CancellationError }
        result.expect(cancelledAsExpected, "text_cancellation_propagates")
        let second = TextProbe()
        try await TextServiceHandler(textService: second).setText(contextId: "second-doc", blockId: "first", middlewareString: .init(text: "שני"))
        let secondCalls = await second.snapshot()
        let firstCallsAfterSecond = await custom.snapshot()
        result.expect(secondCalls.count == 1 && secondCalls.first?.context == "second-doc" && firstCallsAfterSecond.count == 7,
                      "two_handler_instances_isolated")
        result.expect(await Container.shared.nativeText.snapshot().isEmpty, "injected_service_no_native_fallback")
        try await TextServiceHandler().setText(contextId: "native-doc", blockId: "native-block", middlewareString: body)
        let defaultCalls = await Container.shared.nativeText.snapshot()
        result.expect(defaultCalls.count == 1 && defaultCalls.first?.context == "native-doc", "default_service_unchanged")
        let object = ServiceMarker("object"), block = ServiceMarker("block"), bookmark = ServiceMarker("bookmark")
        let file = ServiceMarker("file"), types = ServiceMarker("types"), keyboard = KeyboardMarker("keyboard")
        let dependencies = BlockActionServiceDependencies(objectActionService: object, textServiceHandler: handler,
            blockService: block, bookmarkService: bookmark, fileService: file, objectTypeProvider: types,
            keyboardInsertedBlocksStorage: keyboard)
        let holder = EditorMainItemModelsHolder(), cursor = EditorCursorManager()
        let action = BlockActionService(documentId: "owned-document", modelsHolder: holder, cursorManager: cursor, dependencies: dependencies)
        let mirrored = Dictionary(uniqueKeysWithValues: Mirror(reflecting: action).children.compactMap { child -> (String, Any)? in
            child.label.map { ($0, child.value) }
        })
        let expected: [(String, AnyObject)] = [("objectActionService", object), ("textServiceHandler", handler),
            ("blockService", block), ("bookmarkService", bookmark), ("fileService", file),
            ("objectTypeProvider", types), ("keyboardInsertedBlocksStorage", keyboard)]
        result.expect(expected.allSatisfy { key, value in
            guard let actual = mirrored[key] else { return false }
            return ObjectIdentifier(actual as AnyObject) == ObjectIdentifier(value)
        }, "all_seven_dependencies_forwarded")
        let nativeDependencies = BlockActionServiceDependencies.original()
        result.expect(nativeDependencies.objectActionService === Container.shared.object
                      && (nativeDependencies.textServiceHandler as AnyObject) === Container.shared.nativeHandler
                      && nativeDependencies.blockService === Container.shared.block
                      && nativeDependencies.bookmarkService === Container.shared.bookmark
                      && nativeDependencies.fileService === Container.shared.file
                      && nativeDependencies.objectTypeProvider === Container.shared.types
                      && nativeDependencies.keyboardInsertedBlocksStorage === Container.shared.keyboard,
                      "default_deps_original")
        let isolatedService = TextProbe()
        let isolatedEvents = LocalPublisherProbe(service: isolatedService)
        let isolatedHandler = TextServiceHandler(textService: isolatedService, localEvents: isolatedEvents)
        let globalBeforeInjected = await EventProbe.shared.snapshot()
        try await isolatedHandler.setStyle(contextId: "owned-one", blockId: "same-block", style: .quote)
        let isolatedCalls = await isolatedEvents.snapshot()
        result.expect(isolatedCalls.count == 1 && isolatedCalls[0].context == "owned-one"
                      && isolatedCalls[0].block == "same-block", "injected_style_event_context_identity")
        result.expect(isolatedCalls.first?.payload == ["style"], "injected_style_after_completed_service")
        result.expect(await EventProbe.shared.snapshot() == globalBeforeInjected, "injected_events_no_global_fallback")
        let failureEvents = LocalPublisherProbe()
        var injectedFailure = false
        do {
            try await TextServiceHandler(textService: TextProbe(failure: .deliberate), localEvents: failureEvents)
                .setStyle(contextId: "owned-failed", blockId: "same-block", style: .text)
        } catch { injectedFailure = (error as? TextProbeFailure) == .deliberate }
        let failedEventCalls = await failureEvents.snapshot()
        result.expect(injectedFailure && failedEventCalls.isEmpty, "injected_style_failure_no_event")
        var injectedCancellation = false
        do {
            try await TextServiceHandler(textService: TextProbe(failure: .cancel), localEvents: failureEvents)
                .setStyle(contextId: "owned-cancelled", blockId: "same-block", style: .text)
        } catch { injectedCancellation = error is CancellationError }
        let cancelledEventCalls = await failureEvents.snapshot()
        result.expect(injectedCancellation && cancelledEventCalls.isEmpty, "injected_style_cancellation_no_event")
        _ = try await isolatedHandler.split(contextId: "owned-one", blockId: "same-block",
            range: range, style: .quote, mode: .fixture)
        result.expect(await isolatedEvents.snapshot().count == 1, "injected_split_no_early_event")
        let otherEvents = LocalPublisherProbe()
        try await TextServiceHandler(textService: TextProbe(), localEvents: otherEvents)
            .setStyle(contextId: "owned-two", blockId: "same-block", style: .text)
        let firstPublished = await isolatedEvents.snapshot(), secondPublished = await otherEvents.snapshot()
        result.expect(firstPublished.count == 1 && firstPublished[0].context == "owned-one"
                      && secondPublished.count == 1 && secondPublished[0].context == "owned-two",
                      "two_event_publishers_separate")
        let originalPublisher = OriginalEditorLocalEventPublisher()
        await originalPublisher.refresh(contextId: "native-events")
        await originalPublisher.setStyle(contextId: "native-events", blockId: "style-block")
        await originalPublisher.setToggled(contextId: "native-events", blockId: "toggle-block")
        await originalPublisher.setText(contextId: "native-events", blockId: "text-block", text: body)
        await originalPublisher.setLoadingState(contextId: "native-events", blockId: "loading-block")
        let published = await EventProbe.shared.detailedSnapshot().filter { $0.context == "native-events" }
        result.expect(published.count == 5 && published[0].operation == "general" && published[0].block == "",
                      "original_refresh_event_mapping")
        result.expect(published.count == 5 && published[1].operation == "style" && published[1].block == "style-block",
                      "original_style_event_mapping")
        result.expect(published.count == 5 && published[2].operation == "toggle" && published[2].block == "toggle-block",
                      "original_toggle_event_mapping")
        result.expect(published.count == 5 && published[3].operation == "text" && published[3].block == "text-block"
                      && published[3].body?.text == body.text && published[3].body?.marks == body.marks,
                      "original_text_event_body_marks")
        result.expect(published.count == 5 && published[4].operation == "loading" && published[4].block == "loading-block",
                      "original_loading_event_mapping")
        let data = try JSONEncoder().encode(result.checks)
        print(String(decoding: data, as: UTF8.self))
        if result.checks.contains(where: { !$0.passed }) { throw BoundaryFixtureError.failed }
    }
}
