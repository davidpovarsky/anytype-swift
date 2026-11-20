import XCTest
import Foundation
import Combine
import Factory
import AsyncTools
import AnytypeCore
import Services
import ProtobufMessages
@testable import Anytype

/// Constructor/setter tests of the complete original classes. Explicit service
/// doubles never open an object, create an account, or qualify an editor mount.
/// The original host driver disables parallel XCTest execution; each synchronous
/// test restores Factory's original registration/options/cache state with pop.
@MainActor
final class PreparedDocumentConstructorTests: XCTestCase {
    func testPreparedDocumentDoesNotResolveAnyImplicitFactory() {
        withFactories { provided, record in
            let events = ConstructorEvents()
            let document = makeDocument(mode: .handling, events: events, dependencies: provided)
            XCTAssertEqual(record.calls, [])
            XCTAssertEqual(document.objectId, "constructor-object")
            XCTAssertEqual(document.spaceId, "constructor-space")
            XCTAssertEqual(document.mode, .handling)
            XCTAssertFalse(document.isOpened)
            XCTAssertEqual(events.callbacks, 1)
            XCTAssertEqual(events.starts, 1)
            assertStoredServices(document, provided)
        }
    }

    func testDefaultDocumentResolvesTheSameFourFactoriesOnceInOrder() {
        withFactories { provided, record in
            let events = ConstructorEvents()
            let document = makeDocument(mode: .handling, events: events)
            XCTAssertEqual(record.calls, ["properties", "sync", "history", "user"])
            XCTAssertEqual(events.callbacks, 1)
            XCTAssertEqual(events.starts, 1)
            assertStoredServices(document, provided)
            XCTAssertEqual(record.calls, ["properties", "sync", "history", "user"])
        }
    }

    func testExplicitNilKeepsTheOriginalDefaultConstructorPath() {
        withFactories { provided, record in
            let document = makeDocument(mode: .handling, events: ConstructorEvents(), dependencies: nil)
            assertStoredServices(document, provided)
            XCTAssertEqual(record.calls, ["properties", "sync", "history", "user"])
        }
    }

    func testPreparedPreviewKeepsOriginalListenerAndClosedState() {
        withFactories { provided, record in
            let events = ConstructorEvents()
            let document = makeDocument(mode: .preview, events: events, dependencies: provided)
            XCTAssertEqual(record.calls, [])
            XCTAssertEqual(document.mode, .preview)
            XCTAssertFalse(document.isOpened)
            XCTAssertEqual(events.callbacks, 1)
            XCTAssertEqual(events.starts, 0)
            assertStoredServices(document, provided)
        }
    }

    func testPreparedSetterUsesItsActualUpdaterWithoutResolvingTheDefault() {
        withFactories { _, record in
            let updater = ConstructorMentionUpdater()
            let details = ObjectDetailsStorage()
            let info = InfoContainer()
            let setter = DocumentViewModelSetter(
                detailsStorage: details, restrictionsContainer: ObjectRestrictionsContainer(),
                infoContainer: info, dependencies: .init(mentionTextUpdateHandler: updater)
            )
            setter.objectViewUpdate(rootView())
            XCTAssertEqual(record.calls, [])
            XCTAssertEqual(updater.objectIDs, ["constructor-root"])
            XCTAssertTrue(updater.container === info)
            XCTAssertTrue(updater.storage === details)
            XCTAssertEqual(info.get(id: "constructor-root")?.id, "constructor-root")
        }
    }

    func testDefaultSetterResolvesOneOriginalUpdaterAndKeepsOriginalProjection() {
        withFactories { _, record in
            let details = ObjectDetailsStorage()
            let info = InfoContainer()
            let setter = DocumentViewModelSetter(
                detailsStorage: details, restrictionsContainer: ObjectRestrictionsContainer(), infoContainer: info
            )
            XCTAssertEqual(record.calls, ["mentions"])
            setter.objectViewUpdate(rootView())
            XCTAssertEqual(record.defaultMentionUpdater.objectIDs, ["constructor-root"])
            XCTAssertTrue(record.defaultMentionUpdater.container === info)
            XCTAssertTrue(record.defaultMentionUpdater.storage === details)
            XCTAssertEqual(record.calls, ["mentions"])
        }
    }

    private func withFactories(_ body: (BaseDocumentDependencies, ConstructorResolutionRecord) -> Void) {
        let container = Container.shared
        container.manager.push()
        defer { container.manager.pop() }
        let record = ConstructorResolutionRecord()
        let provided = BaseDocumentDependencies(
            relationBuilder: ConstructorProperties(), syncStatusStorage: ConstructorSync(),
            historyVersionsService: ConstructorHistory(), basicUserInfoStorage: ConstructorUser()
        )
        container.propertiesBuilder.register { record.append("properties"); return provided.relationBuilder }
        container.syncStatusStorage.register { record.append("sync"); return provided.syncStatusStorage }
        container.historyVersionsService.register { record.append("history"); return provided.historyVersionsService }
        container.basicUserInfoStorage.register { record.append("user"); return provided.basicUserInfoStorage }
        container.mentionTextUpdateHandler.register { record.append("mentions"); return record.defaultMentionUpdater }
        body(provided, record)
    }

    // Exercise an unchanged caller that omits the new argument, separately
    // from the explicit-nil and explicitly supplied dependency paths.
    private func makeDocument(mode: DocumentMode, events: ConstructorEvents) -> BaseDocument {
        BaseDocument(
            objectId: "constructor-object", spaceId: "constructor-space", mode: mode,
            objectLifecycleService: ConstructorLifecycle(), propertyDetailsStorage: ConstructorPropertiesStorage(),
            objectTypeProvider: ConstructorTypes(), accountParticipantsStorage: ConstructorParticipants(),
            eventsListener: events, viewModelSetter: ConstructorSetter(), infoContainer: InfoContainer(),
            restrictionsContainer: ObjectRestrictionsContainer(), detailsStorage: ObjectDetailsStorage()
        )
    }

    private func makeDocument(
        mode: DocumentMode, events: ConstructorEvents, dependencies: BaseDocumentDependencies?
    ) -> BaseDocument {
        BaseDocument(
            objectId: "constructor-object", spaceId: "constructor-space", mode: mode,
            objectLifecycleService: ConstructorLifecycle(), propertyDetailsStorage: ConstructorPropertiesStorage(),
            objectTypeProvider: ConstructorTypes(), accountParticipantsStorage: ConstructorParticipants(),
            eventsListener: events, viewModelSetter: ConstructorSetter(), infoContainer: InfoContainer(),
            restrictionsContainer: ObjectRestrictionsContainer(), detailsStorage: ObjectDetailsStorage(),
            dependencies: dependencies
        )
    }

    private func assertStoredServices(_ document: BaseDocument, _ provided: BaseDocumentDependencies) {
        let values = Dictionary(uniqueKeysWithValues: Mirror(reflecting: document).children.compactMap {
            child in child.label.map { ($0, child.value) }
        })
        XCTAssertTrue((values["relationBuilder"] as? ConstructorProperties) === provided.relationBuilder)
        XCTAssertTrue((values["syncStatusStorage"] as? ConstructorSync) === (provided.syncStatusStorage as? ConstructorSync))
        XCTAssertTrue((values["historyVersionsService"] as? ConstructorHistory) === (provided.historyVersionsService as? ConstructorHistory))
        XCTAssertTrue((values["basicUserInfoStorage"] as? ConstructorUser) === provided.basicUserInfoStorage)
    }

    private func rootView() -> ObjectViewModel {
        var model = ObjectViewModel()
        model.rootID = "constructor-root"
        model.blocks = [.with { block in
            block.id = "constructor-root"
            block.content = .smartblock(.init())
        }]
        return model
    }
}

private enum ConstructorUnexpectedCall: Error { case unusedService }

private final class ConstructorResolutionRecord {
    private let lock = NSLock()
    private var values: [String] = []
    let defaultMentionUpdater = ConstructorMentionUpdater()
    var calls: [String] { lock.lock(); defer { lock.unlock() }; return values }
    func append(_ value: String) { lock.lock(); defer { lock.unlock() }; values.append(value) }
}

private final class ConstructorEvents: EventsListenerProtocol {
    private(set) var callbacks = 0
    private(set) var starts = 0
    func setOnUpdateReceice(_ closure: @escaping @Sendable ([DocumentUpdate]) -> Void) { callbacks += 1 }
    func startListening() { starts += 1 }
    func stopListening() { XCTFail("Constructor unexpectedly stopped an event listener") }
}

private final class ConstructorLifecycle: ObjectLifecycleServiceProtocol, Sendable {
    func close(contextId: String, spaceId: String) async throws { throw ConstructorUnexpectedCall.unusedService }
    func open(contextId: String, spaceId: String) async throws -> ObjectViewModel { throw ConstructorUnexpectedCall.unusedService }
    func openForPreview(contextId: String, spaceId: String) async throws -> ObjectViewModel { throw ConstructorUnexpectedCall.unusedService }
}

private final class ConstructorProperties: PropertiesBuilderProtocol {
    func parsedProperties(
        objectProperties: [PropertyDetails], objectFeaturedProperties: [PropertyDetails],
        recommendedProperties: [PropertyDetails], recommendedFeaturedProperties: [PropertyDetails],
        recommendedHiddenProperties: [PropertyDetails], objectId: String,
        propertyValuesIsLocked: Bool, storage: ObjectDetailsStorage
    ) -> ParsedProperties { fatalError("Constructor unexpectedly projected properties") }
}

private final class ConstructorSync: SyncStatusStorageProtocol, Sendable {
    func statusPublisher(spaceId: String) -> AnyPublisher<SpaceSyncStatusInfo, Never> { fatalError("Constructor unexpectedly subscribed") }
    func allSpacesStatusPublisher() -> AnyPublisher<[SpaceSyncStatusInfo], Never> { fatalError("Constructor unexpectedly subscribed") }
    func startSubscription() async { XCTFail("Constructor unexpectedly started sync") }
    func stopSubscriptionAndClean() async { XCTFail("Constructor unexpectedly stopped sync") }
}

private final class ConstructorHistory: HistoryVersionsServiceProtocol, Sendable {
    func getVersions(objectId: String, lastVersionId: String) async throws -> [VersionHistory] { throw ConstructorUnexpectedCall.unusedService }
    func showVersion(objectId: String, versionId: String) async throws -> ObjectViewModel { throw ConstructorUnexpectedCall.unusedService }
    func diffVersions(objectId: String, spaceId: String, currentVersionId: String, previousVersionId: String) async throws -> VersionHistoryDiff { throw ConstructorUnexpectedCall.unusedService }
    func setVersion(objectId: String, versionId: String) async throws { throw ConstructorUnexpectedCall.unusedService }
}

private final class ConstructorUser: BasicUserInfoStorageProtocol, @unchecked Sendable {
    private let lock = NSLock()
    private var user = ""
    private var analytics: String?
    var usersId: String {
        get { lock.lock(); defer { lock.unlock() }; return user }
        set { lock.lock(); defer { lock.unlock() }; user = newValue }
    }
    var analyticsId: String? {
        get { lock.lock(); defer { lock.unlock() }; return analytics }
        set { lock.lock(); defer { lock.unlock() }; analytics = newValue }
    }
    func cleanUserIdAfterLogout() { usersId = "" }
}

private final class ConstructorMentionUpdater: MentionTextUpdateHandlerProtocol {
    private(set) var objectIDs: [String] = []
    private(set) var container: (any InfoContainerProtocol)?
    private(set) var storage: ObjectDetailsStorage?
    func updateMentionsTextsIfNeeded(objectId: String, infoContainer: some InfoContainerProtocol, detailsStorage: ObjectDetailsStorage) -> [String] {
        objectIDs.append(objectId); container = infoContainer; storage = detailsStorage
        return []
    }
}

private final class ConstructorSetter: DocumentViewModelSetterProtocol {
    func objectViewUpdate(_ data: ObjectViewModel) { XCTFail("Constructor unexpectedly opened a document") }
}

private final class ConstructorPropertiesStorage: PropertyDetailsStorageProtocol, Sendable {
    func relationsDetails(keys: [String], spaceId: String) -> [PropertyDetails] { fatalError("Unused property read") }
    func relationsDetails(key: String, spaceId: String) throws -> PropertyDetails { throw ConstructorUnexpectedCall.unusedService }
    func relationsDetails(bundledKey: BundledPropertyKey, spaceId: String) throws -> PropertyDetails { throw ConstructorUnexpectedCall.unusedService }
    func relationsDetails(ids: [String], spaceId: String) -> [PropertyDetails] { fatalError("Unused property read") }
    func relationsDetails(spaceId: String) -> [PropertyDetails] { fatalError("Unused property read") }
    var syncPublisher: AnyPublisher<Void, Never> { fatalError("Unused property subscription") }
    func startSubscription(spaceId: String) async { XCTFail("Unused property subscription") }
    func stopSubscription() async { XCTFail("Unused property subscription") }
    func prepareData(spaceId: String) async { XCTFail("Unused property preparation") }
}

private final class ConstructorTypes: ObjectTypeProviderProtocol, Sendable {
    var syncPublisher: AnyPublisher<Void, Never> { fatalError("Unused type subscription") }
    func setDefaultObjectType(type: ObjectType, spaceId: String, route: AnalyticsDefaultObjectTypeChangeRoute) { XCTFail("Unused type mutation") }
    func defaultObjectType(spaceId: String) throws -> ObjectType { throw ConstructorUnexpectedCall.unusedService }
    func defaultObjectTypePublisher(spaceId: String) -> AnyPublisher<ObjectType, Never> { fatalError("Unused type subscription") }
    func objectType(id: String) throws -> ObjectType { throw ConstructorUnexpectedCall.unusedService }
    func objectType(recommendedLayout: DetailsLayout, spaceId: String) throws -> ObjectType { throw ConstructorUnexpectedCall.unusedService }
    func objectType(uniqueKey: ObjectTypeUniqueKey, spaceId: String) throws -> ObjectType { throw ConstructorUnexpectedCall.unusedService }
    func objectTypes(spaceId: String) -> [ObjectType] { fatalError("Unused type read") }
    func deletedObjectType(id: String) -> ObjectType { fatalError("Unused type read") }
    func startSubscription(spaceId: String) async { XCTFail("Unused type subscription") }
    func stopSubscription() async { XCTFail("Unused type subscription") }
    func prepareData(spaceId: String) async { XCTFail("Unused type preparation") }
}

private final class ConstructorParticipants: ParticipantsStorageProtocol, Sendable {
    var participants: [Participant] { fatalError("Unused participant read") }
    var participantsSequence: AnyAsyncSequence<[Participant]> { fatalError("Unused participant subscription") }
    func startSubscription() async { XCTFail("Unused participant subscription") }
    func stopSubscription() async { XCTFail("Unused participant subscription") }
}
