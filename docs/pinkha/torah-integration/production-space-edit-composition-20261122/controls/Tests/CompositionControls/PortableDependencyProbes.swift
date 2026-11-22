import Foundation

final class AtomicStorage<T>: @unchecked Sendable {
    private let lock = NSLock()
    private var stored: T
    init(_ value: T) { stored = value }
    var value: T {
        get { lock.withLock { stored } }
        set { lock.withLock { stored = newValue } }
    }
    @discardableResult func access<R>(_ body: (inout T) -> R) -> R {
        lock.withLock { body(&stored) }
    }
}

final class ProbePublisher<Value: Sendable>: @unchecked Sendable {
    private struct State {
        var value: Value?
        var subscribers: [UUID: AsyncStream<Value>.Continuation] = [:]
    }
    private let state = AtomicStorage(State())
    var values: AsyncStream<Value> {
        let pair = AsyncStream<Value>.makeStream()
        let id = UUID()
        let current = state.access { state -> Value? in
            state.subscribers[id] = pair.continuation
            return state.value
        }
        pair.continuation.onTermination = { [weak self] _ in
            self?.state.access { _ = $0.subscribers.removeValue(forKey: id) }
        }
        if let current { pair.continuation.yield(current) }
        return pair.stream
    }
    func send(_ value: Value) {
        let targets = state.access { state -> [AsyncStream<Value>.Continuation] in
            state.value = value
            return Array(state.subscribers.values)
        }
        for target in targets { target.yield(value) }
    }
    func throttle(for interval: ProbeInterval, scheduler: DispatchQueue, latest: Bool) -> Self { self }
    func removeDuplicates() -> Self { self }
    func eraseToAnyPublisher() -> Self { self }
}
typealias AnyPublisher<Value: Sendable, Failure: Error> = ProbePublisher<Value>
typealias AnyAsyncSequence<Value: Sendable> = AsyncStream<Value>

final class AtomicPublishedStorage<T: Sendable>: @unchecked Sendable {
    private let storage: AtomicStorage<T>
    let publisher = ProbePublisher<T>()
    init(_ value: T) { storage = AtomicStorage(value); publisher.send(value) }
    var value: T {
        get { storage.value }
        set { storage.value = newValue; publisher.send(newValue) }
    }
}

final class AsyncToManyStream<Value: Sendable>: @unchecked Sendable {
    private let latest = AtomicStorage<Value?>(nil)
    private let publisher = ProbePublisher<Value>()
    var value: Value? { latest.value }
    func send(_ value: Value) { latest.value = value; publisher.send(value) }
    func clearLastValue() { latest.value = nil }
    func eraseToAnyAsyncSequence() -> AnyAsyncSequence<Value> { publisher.values }
}


enum ProbeInterval { case milliseconds(Int) }
final class SynchronizedDictionary<K: Hashable, V>: @unchecked Sendable {
    private let storage = AtomicStorage<[K: V]>([:])
    subscript(key: K) -> V? {
        get { storage.value[key] }
        set { storage.access { $0[key] = newValue } }
    }
}


struct AccountInfo: Sendable, Equatable { let techSpaceId: String }
struct AccountData: Sendable, Equatable {
    let id: String
    let info: AccountInfo
    static let empty = AccountData(id: "", info: .init(techSpaceId: ""))
}
public enum ObjectIcon: Sendable, Hashable { case unusedProbeValue }

enum ProbeSpaceStatus: Sendable, Equatable { case ok, spaceRemoving, spaceDeleted, spaceJoining, loading, unknown }
enum ProbeSpaceType: Sendable, Equatable { case regular, oneToOne }
enum ProbeSpaceUX: Sendable, Equatable { case data, stream }

struct SpaceView: Sendable, Equatable {
    var id: String
    var targetSpaceId: String
    var name: String
    var accountStatus: ProbeSpaceStatus?
    var localStatus: ProbeSpaceStatus?
    var spaceAccessType: SpaceAccessType?
    var spaceType: ProbeSpaceType
    private var uxType: ProbeSpaceUX

    init(id: String = "native-view-A", targetSpaceId: String = "space-A",
         name: String = "Initial", legacy: Bool = false,
         accountStatus: ProbeSpaceStatus? = .ok, localStatus: ProbeSpaceStatus? = .ok,
         access: SpaceAccessType? = .personal, type: ProbeSpaceType = .regular) {
        self.id = id; self.targetSpaceId = targetSpaceId; self.name = name
        self.accountStatus = accountStatus; self.localStatus = localStatus
        spaceAccessType = access; spaceType = type; uxType = legacy ? .stream : .data
    }
    init(details: SubscriptionDetailsProbe) {
        guard case .space(let value) = details else { preconditionFailure("Space fixture route mismatch") }
        self = value
    }

    var isActive: Bool {
        let spaceIsNotDeleted = accountStatus != .spaceRemoving && accountStatus != .spaceDeleted
        let spaceIsNotJoining = accountStatus != .spaceJoining
        return localStatus == .ok && spaceIsNotDeleted && spaceIsNotJoining
    }

    var isLegacyStream: Bool {
        uxType == .stream
    }

    var isOneToOne: Bool {
        spaceType == .oneToOne
    }

}


enum SubscriptionDetailsProbe: Sendable {
    case participant(Participant)
    case space(SpaceView)
}
enum ProbeFailure: Error { case route, decoder }
extension Participant {
    init(details: SubscriptionDetailsProbe) throws {
        guard case .participant(let value) = details else { throw ProbeFailure.decoder }
        self = value
    }
}
struct SubscriptionStorageState: Sendable { let items: [SubscriptionDetailsProbe] }
struct SubscriptionData: Sendable, Equatable {
    let identifier: String
    let accountId: String
    let spaceId: String
    init(accountId: String, identifier: String) {
        self.accountId = accountId; self.identifier = identifier; spaceId = ""
    }
    init(identifier: String, spaceId: String) {
        self.identifier = identifier; self.spaceId = spaceId; accountId = ""
    }
}
protocol SubscriptionStorageProtocol: AnyObject, Sendable {
    var statePublisher: ProbePublisher<SubscriptionStorageState> { get }
    func startOrUpdateSubscription(data: SubscriptionData) async throws
    func startOrUpdateSubscription(data: SubscriptionData,
        update: @escaping @Sendable (SubscriptionStorageState) async -> Void) async throws
    func stopSubscription() async throws
}
protocol SubscriptionStorageProviderProtocol: AnyObject, Sendable {
    func createSubscriptionStorage(subId: String) -> any SubscriptionStorageProtocol
}
protocol SpaceViewsSubscriptionBuilderProtocol: AnyObject, Sendable {
    var subscriptionId: String { get }
    func build(techSpaceId: String) -> SubscriptionData
}
final class AcountParticipantSubscriptionBuilder {
    func build(accountId: String, subId: String) -> SubscriptionData {
        .init(accountId: accountId, identifier: subId)
    }
}
final class ProbeSpaceBuilder: SpaceViewsSubscriptionBuilderProtocol, Sendable {
    let subscriptionId = "SubscriptionId.SpaceViews"
    func build(techSpaceId: String) -> SubscriptionData {
        .init(identifier: subscriptionId, spaceId: techSpaceId)
    }
}
final class ParticipantSubscriptionProbe: SubscriptionStorageProtocol, @unchecked Sendable {
    let statePublisher = ProbePublisher<SubscriptionStorageState>()
    private let current: AtomicStorage<[Participant]>
    init(_ values: [Participant]) { current = AtomicStorage(values) }
    func send(_ values: [Participant]) {
        current.value = values
        statePublisher.send(.init(items: values.map { .participant($0) }))
    }
    func startOrUpdateSubscription(data: SubscriptionData) async throws {
        send(current.value)
    }
    func startOrUpdateSubscription(data: SubscriptionData,
        update: @escaping @Sendable (SubscriptionStorageState) async -> Void) async throws {
        throw ProbeFailure.route
    }
    func stopSubscription() async throws {}
}
final class SpaceSubscriptionProbe: SubscriptionStorageProtocol, @unchecked Sendable {
    typealias Update = @Sendable (SubscriptionStorageState) async -> Void
    let statePublisher = ProbePublisher<SubscriptionStorageState>()
    private let current: AtomicStorage<[SpaceView]>
    private let callback = AtomicStorage<Update?>(nil)
    init(_ values: [SpaceView]) { current = AtomicStorage(values) }
    func emit(_ values: [SpaceView]) async {
        current.value = values
        guard let update = callback.value else { return }
        await update(.init(items: values.map { .space($0) }))
    }
    func startOrUpdateSubscription(data: SubscriptionData) async throws {
        throw ProbeFailure.route
    }
    func startOrUpdateSubscription(data: SubscriptionData,
        update: @escaping Update) async throws {
        callback.value = update
        await update(.init(items: current.value.map { .space($0) }))
    }
    func stopSubscription() async throws {}
}
final class ProbeProvider: SubscriptionStorageProviderProtocol, Sendable {
    let participant: ParticipantSubscriptionProbe
    let space: SpaceSubscriptionProbe
    init(participant: ParticipantSubscriptionProbe, space: SpaceSubscriptionProbe) {
        self.participant = participant; self.space = space
    }
    func createSubscriptionStorage(subId: String) -> any SubscriptionStorageProtocol {
        if subId.hasPrefix("SubscriptionId.Participant-") { return participant }
        if subId == "SubscriptionId.SpaceViews" { return space }
        preconditionFailure("Unexpected original subscription identifier")
    }
}
enum ProbeNetworkMode: Sendable { case localOnly, defaultConfig }
struct ProbeNetworkConfiguration: Sendable { let middlewareNetworkMode: ProbeNetworkMode }
final class ProbeServerConfigurationStorage: Sendable {
    let local = AtomicStorage(false)
    func currentConfiguration() -> ProbeNetworkConfiguration {
        .init(middlewareNetworkMode: local.value ? .localOnly : .defaultConfig)
    }
}
struct ProbeDependencies: Sendable {
    let subscriptionStorageProvider: any SubscriptionStorageProviderProtocol
    let accountManager: any AccountManagerProtocol
    let spaceViewsSubscriptionBuilder: any SpaceViewsSubscriptionBuilderProtocol
    let serverConfigurationStorage: ProbeServerConfigurationStorage
}
enum ProbeRegistry {
    static let dependencies = AtomicStorage<ProbeDependencies?>(nil)
    static let assertions = AtomicStorage<[String]>([])
    static func current() -> ProbeDependencies {
        guard let value = dependencies.value else { preconditionFailure("Fixture dependencies are not installed") }
        return value
    }
}
@propertyWrapper
struct Injected<Value>: @unchecked Sendable {
    let wrappedValue: Value
    init(_ keyPath: KeyPath<ProbeDependencies, Value>) {
        wrappedValue = ProbeRegistry.current()[keyPath: keyPath]
    }
}
typealias LazyInjected<Value> = Injected<Value>
final class Container: Sendable {
    static let shared = Container()
    func spaceViewsSubscriptionBuilder() -> any SpaceViewsSubscriptionBuilderProtocol {
        ProbeRegistry.current().spaceViewsSubscriptionBuilder
    }
    func subscriptionStorageProvider() -> any SubscriptionStorageProviderProtocol {
        ProbeRegistry.current().subscriptionStorageProvider
    }
    func accountManager() -> any AccountManagerProtocol { ProbeRegistry.current().accountManager }
    func serverConfigurationStorage() -> ProbeServerConfigurationStorage {
        ProbeRegistry.current().serverConfigurationStorage
    }
}
func anytypeAssertionFailure(_ message: String) {
    ProbeRegistry.assertions.access { $0.append(message) }
}
actor ProbeHold {
    private var entered = false, released = false
    private var entries: [CheckedContinuation<Void, Never>] = []
    private var releases: [CheckedContinuation<Void, Never>] = []
    func pause() async {
        entered = true
        let entries = entries; self.entries.removeAll()
        for c in entries { c.resume() }
        if !released { await withCheckedContinuation { releases.append($0) } }
    }
    func wait() async {
        if !entered { await withCheckedContinuation { entries.append($0) } }
    }
    func release() {
        released = true
        let releases = releases; self.releases.removeAll()
        for c in releases { c.resume() }
    }
}


