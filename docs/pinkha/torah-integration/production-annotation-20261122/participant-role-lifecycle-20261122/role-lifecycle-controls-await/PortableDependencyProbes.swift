import Foundation

// Explicit portable input/dependency probes. These do not implement Anytype
// RPC, protobuf decoding, Combine, Factory DI or native OSAllocatedUnfairLock.
// The production Participant value, permission predicates, AccountManager,
// lifetime/capture and entire ParticipantsStorage actor are retained separately.
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

struct AccountData: Sendable {
    let id: String
    static let empty = AccountData(id: "")
}
public enum ObjectIcon: Sendable, Hashable { case unusedProbeValue }

struct ParticipantDetailsProbe: Sendable {
    let participant: Participant
    let rejects: Bool
}
enum ProbeFailure: Error { case start, stop, decoder }
extension Participant {
    init(details: ParticipantDetailsProbe) throws {
        guard !details.rejects else { throw ProbeFailure.decoder }
        self = details.participant
    }
}
struct SubscriptionStorageState: Sendable { let items: [ParticipantDetailsProbe] }
struct SubscriptionData: Sendable, Equatable { let accountId: String; let identifier: String }

protocol SubscriptionStorageProtocol: AnyObject, Sendable {
    var statePublisher: ProbePublisher<SubscriptionStorageState> { get }
    func startOrUpdateSubscription(data: SubscriptionData) async throws
    func stopSubscription() async throws
}
protocol SubscriptionStorageProviderProtocol: Sendable {
    func createSubscriptionStorage(subId: String) -> any SubscriptionStorageProtocol
}
final class AcountParticipantSubscriptionBuilder {
    func build(accountId: String, subId: String) -> SubscriptionData {
        SubscriptionData(accountId: accountId, identifier: subId)
    }
}
struct ProbeProvider: SubscriptionStorageProviderProtocol {
    let storage: ProbeSubscriptionStorage
    func createSubscriptionStorage(subId: String) -> any SubscriptionStorageProtocol { storage }
}
struct ProbeDependencies {
    let subscriptionStorageProvider: any SubscriptionStorageProviderProtocol
    let accountManager: any AccountManagerProtocol
}
enum ProbeRegistry {
    static let dependencies = AtomicStorage<ProbeDependencies?>(nil)
    static let assertions = AtomicStorage<[String]>([])
}
@propertyWrapper
struct Injected<Value>: @unchecked Sendable {
    let wrappedValue: Value
    init(_ keyPath: KeyPath<ProbeDependencies, Value>) {
        wrappedValue = ProbeRegistry.dependencies.value![keyPath: keyPath]
    }
}
typealias LazyInjected<Value> = Injected<Value>
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

final class ProbeSubscriptionStorage: SubscriptionStorageProtocol, @unchecked Sendable {
    struct Counters: Sendable {
        var starts = 0, stops = 0, cachedStarts = 0
        var accountIDs: [String] = []
    }
    private struct State {
        var counters = Counters()
        var data: SubscriptionData?
        var stopFailures: Int
    }
    let statePublisher = ProbePublisher<SubscriptionStorageState>()
    let startHold: ProbeHold?
    let stopHold: ProbeHold?
    private let failStart: Bool
    private let initial: [Participant]
    private let state: AtomicStorage<State>
    init(
        initial: [Participant], startHold: ProbeHold? = nil,
        stopHold: ProbeHold? = nil, failStart: Bool = false, stopFailures: Int = 0
    ) {
        self.initial = initial
        self.startHold = startHold; self.stopHold = stopHold
        self.failStart = failStart
        state = AtomicStorage(State(stopFailures: stopFailures))
    }
    var counters: Counters { state.value.counters }
    func send(_ participants: [Participant]) {
        statePublisher.send(.init(items: participants.map { .init(participant: $0, rejects: false) }))
    }
    func startOrUpdateSubscription(data: SubscriptionData) async throws {
        let cached = state.access { value -> Bool in
            value.counters.starts += 1
            value.counters.accountIDs.append(data.accountId)
            if value.data == data {
                value.counters.cachedStarts += 1
                return true
            }
            if !failStart { value.data = data }
            return false
        }
        // Explicitly reproduce the reviewed cached-state early return and a
        // successful native start whose outer caller has not yet resumed.
        if cached { send(initial); return }
        if !failStart { send(initial) }
        if let startHold { await startHold.pause() }
        if failStart { throw ProbeFailure.start }
        try Task.checkCancellation()
    }
    func stopSubscription() async throws {
        state.access { $0.counters.stops += 1 }
        if let stopHold { await stopHold.pause() }
        let fail = state.access { value -> Bool in
            if value.stopFailures > 0 {
                value.stopFailures -= 1
                return true
            }
            value.data = nil
            return false
        }
        if fail { throw ProbeFailure.stop }
    }
}
