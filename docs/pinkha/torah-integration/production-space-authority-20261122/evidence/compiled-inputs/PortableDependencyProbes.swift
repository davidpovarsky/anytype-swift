import Foundation

// Explicit portable dependency probes. They do not implement Combine, Factory,
// ObjectDetails decoding, native subscriptions/RPC or OSAllocatedUnfairLock.
// The exact original actor, Lifetime/Capture/Binding/AccountManager and native
// isActive/isLegacyStream predicates are compiled separately without body edits.
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
    private let observers = AtomicStorage<[UUID: @Sendable (Value) -> Void]>([:])
    func observe(_ body: @escaping @Sendable (Value) -> Void) -> UUID {
        let id = UUID()
        observers.access { $0[id] = body }
        return id
    }
    func removeObserver(_ id: UUID) { observers.access { _ = $0.removeValue(forKey: id) } }
    func send(_ value: Value) {
        let callbacks = observers.value
        for callback in callbacks.values { callback(value) }
    }
    func throttle(for interval: ProbeInterval, scheduler: DispatchQueue, latest: Bool) -> Self { self }
    func removeDuplicates() -> Self { self }
    func eraseToAnyPublisher() -> Self { self }
}
enum ProbeInterval { case milliseconds(Int) }
typealias AnyPublisher<Value: Sendable, Failure: Error> = ProbePublisher<Value>

final class AtomicPublishedStorage<T: Sendable>: @unchecked Sendable {
    private let storage: AtomicStorage<T>
    let publisher = ProbePublisher<T>()
    init(_ value: T) { storage = AtomicStorage(value) }
    var value: T {
        get { storage.value }
        set { storage.value = newValue; publisher.send(newValue) }
    }
}

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
enum ProbeSpaceStatus: Sendable, Equatable { case ok, spaceRemoving, spaceDeleted, spaceJoining, loading, unknown }
enum ProbeSpaceAccess: Sendable, Equatable { case personal, shared }
enum ProbeSpaceType: Sendable, Equatable { case regular, oneToOne }
enum ProbeSpaceUX: Sendable, Equatable { case data, stream }

// Disposable already-decoded field inputs. The two predicates below are exact
// original source fragments; the ObjectDetails/protobuf decoder is NOT compiled.
struct SpaceView: Sendable, Equatable {
    var id: String
    var targetSpaceId: String
    var name: String
    var accountStatus: ProbeSpaceStatus?
    var localStatus: ProbeSpaceStatus?
    var spaceAccessType: ProbeSpaceAccess?
    var spaceType: ProbeSpaceType
    private var uxType: ProbeSpaceUX

    init(id: String = "native-view-A", targetSpaceId: String = "space-A",
         name: String = "Initial", legacy: Bool = false,
         accountStatus: ProbeSpaceStatus? = .ok, localStatus: ProbeSpaceStatus? = .ok,
         access: ProbeSpaceAccess? = .personal, type: ProbeSpaceType = .regular) {
        self.id = id; self.targetSpaceId = targetSpaceId; self.name = name
        self.accountStatus = accountStatus; self.localStatus = localStatus
        spaceAccessType = access; spaceType = type; uxType = legacy ? .stream : .data
    }
    init(details: SpaceView) { self = details }

    var isActive: Bool {
        let spaceIsNotDeleted = accountStatus != .spaceRemoving && accountStatus != .spaceDeleted
        let spaceIsNotJoining = accountStatus != .spaceJoining
        return localStatus == .ok && spaceIsNotDeleted && spaceIsNotJoining
    }

    var isLegacyStream: Bool {
        uxType == .stream
    }

}

struct SubscriptionStorageState: Sendable { let items: [SpaceView] }
struct SubscriptionData: Sendable, Equatable { let identifier: String; let spaceId: String }
protocol SubscriptionStorageProtocol: AnyObject, Sendable {
    func startOrUpdateSubscription(data: SubscriptionData,
        update: @escaping @Sendable (_ state: SubscriptionStorageState) async -> Void) async throws
    func stopSubscription() async throws
}
protocol SubscriptionStorageProviderProtocol: AnyObject, Sendable {
    func createSubscriptionStorage(subId: String) -> any SubscriptionStorageProtocol
}
protocol SpaceViewsSubscriptionBuilderProtocol: AnyObject, Sendable {
    var subscriptionId: String { get }
    func build(techSpaceId: String) -> SubscriptionData
}

final class ProbeSpaceBuilder: SpaceViewsSubscriptionBuilderProtocol, Sendable {
    let subscriptionId = "SubscriptionId.SpaceViews"
    let onBuild: (@Sendable () -> Void)?
    init(onBuild: (@Sendable () -> Void)? = nil) { self.onBuild = onBuild }
    func build(techSpaceId: String) -> SubscriptionData {
        onBuild?()
        return .init(identifier: subscriptionId, spaceId: techSpaceId)
    }
}
final class ProbeProvider: SubscriptionStorageProviderProtocol, Sendable {
    let storage: ProbeSubscriptionStorage
    init(storage: ProbeSubscriptionStorage) { self.storage = storage }
    func createSubscriptionStorage(subId: String) -> any SubscriptionStorageProtocol { storage }
}
struct ProbeDependencies: Sendable {
    let builder: any SpaceViewsSubscriptionBuilderProtocol
    let provider: any SubscriptionStorageProviderProtocol
    let account: any AccountManagerProtocol
}
enum ProbeRegistry {
    static let dependencies = AtomicStorage<ProbeDependencies?>(nil)
}
final class Container: Sendable {
    static let shared = Container()
    func spaceViewsSubscriptionBuilder() -> any SpaceViewsSubscriptionBuilderProtocol {
        ProbeRegistry.dependencies.value!.builder
    }
    func subscriptionStorageProvider() -> any SubscriptionStorageProviderProtocol {
        ProbeRegistry.dependencies.value!.provider
    }
    func accountManager() -> any AccountManagerProtocol {
        ProbeRegistry.dependencies.value!.account
    }
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


enum ProbeFailure: Error { case start, stop }

final class ProbeSubscriptionStorage: SubscriptionStorageProtocol, @unchecked Sendable {
    typealias Update = @Sendable (SubscriptionStorageState) async -> Void
    struct Counters: Sendable {
        var starts = 0, stops = 0, cachedStarts = 0
        var technicalSpaces: [String] = []
    }
    private struct State {
        var counters = Counters()
        var data: SubscriptionData?
        var callbacks: [Update] = []
        var stopFailures: Int
    }
    private let state: AtomicStorage<State>
    let initial: [SpaceView]
    let beforeCallback: ProbeHold?
    let afterCallback: ProbeHold?
    let duringStop: ProbeHold?
    let failStart: Bool
    init(initial: [SpaceView], beforeCallback: ProbeHold? = nil,
         afterCallback: ProbeHold? = nil, duringStop: ProbeHold? = nil,
         failStart: Bool = false, stopFailures: Int = 0) {
        self.initial = initial; self.beforeCallback = beforeCallback
        self.afterCallback = afterCallback; self.duringStop = duringStop
        self.failStart = failStart; state = AtomicStorage(State(stopFailures: stopFailures))
    }
    var counters: Counters { state.value.counters }
    var callbackCount: Int { state.value.callbacks.count }
    func emit(_ spaces: [SpaceView], callback index: Int? = nil) async {
        let callbacks = state.value.callbacks
        guard !callbacks.isEmpty else { return }
        let selected = index ?? (callbacks.count - 1)
        await callbacks[selected](.init(items: spaces))
    }
    func startOrUpdateSubscription(
        data: SubscriptionData, update: @escaping Update
    ) async throws {
        state.access {
            $0.counters.starts += 1
            $0.counters.technicalSpaces.append(data.spaceId)
            if $0.data == data { $0.counters.cachedStarts += 1 }
            $0.callbacks.append(update)
        }
        if let beforeCallback { await beforeCallback.pause() }
        if failStart { throw ProbeFailure.start }
        state.access { $0.data = data }
        // Deliberately allow the original callback after cancellation; the
        // actual production actor/capture must reject it, not this fixture.
        await update(.init(items: initial))
        if let afterCallback { await afterCallback.pause() }
    }
    func stopSubscription() async throws {
        state.access { $0.counters.stops += 1 }
        if let duringStop { await duringStop.pause() }
        let failure = state.access { value -> Bool in
            if value.stopFailures > 0 { value.stopFailures -= 1; return true }
            value.data = nil
            return false
        }
        if failure { throw ProbeFailure.stop }
    }
}

final class ForeignAccountManager: AccountManagerProtocol, @unchecked Sendable {
    private let storage: AtomicPublishedStorage<AccountData>
    private let foreignLifetime = EditorDocumentWriteLifetime()
    init(account: AccountData) { storage = AtomicPublishedStorage(account) }
    var account: AccountData {
        get { storage.value }
        set { storage.value = newValue }
    }
    var accountPublisher: AnyPublisher<AccountData, Never> { storage.publisher }
    var editorWriteLifetime: EditorDocumentWriteLifetime? { foreignLifetime }
}
