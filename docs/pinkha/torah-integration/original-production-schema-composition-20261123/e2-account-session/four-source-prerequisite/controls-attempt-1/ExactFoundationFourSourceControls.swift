import Foundation
import Dispatch

private final class OriginalEventDeliveryFence: @unchecked Sendable {
    enum Failure: Error { case ended, counterExhausted, invalidCompletion }
    private let lock = NSLock()
    private var accepted: UInt64 = 0
    private var delivered: UInt64 = 0
    private var failure: Failure?
    private var waiters: [(target: UInt64, continuation: CheckedContinuation<Void, Error>)] = []

    func enqueue(_ data: Data, into continuation: AsyncStream<Data>.Continuation) {
        lock.lock()
        var failed: [CheckedContinuation<Void, Error>] = []
        if failure == nil {
            if accepted == UInt64.max {
                failed = failLocked(.counterExhausted)
            } else {
                accepted += 1
            }
        }
        // Counter order and the original stream's enqueue order share this
        // lock. The original consumer/handler cannot acknowledge beforehand.
        switch continuation.yield(data) {
        case .enqueued:
            break
        case .dropped, .terminated:
            failed += failLocked(.ended)
        @unknown default:
            failed += failLocked(.ended)
        }
        let reason = failure
        lock.unlock()
        if let reason { for waiter in failed { waiter.resume(throwing: reason) } }
    }

    func didDeliverOne() {
        lock.lock()
        guard failure == nil else { lock.unlock(); return }
        guard delivered < accepted else {
            let failed = failLocked(.invalidCompletion)
            lock.unlock()
            for waiter in failed { waiter.resume(throwing: Failure.invalidCompletion) }
            return
        }
        delivered += 1
        let completed = waiters.filter { $0.target <= delivered }.map(\.continuation)
        waiters.removeAll { $0.target <= delivered }
        lock.unlock()
        for waiter in completed { waiter.resume() }
    }

    func waitForCurrentFrontier() async throws {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            lock.lock()
            if let failure {
                lock.unlock()
                continuation.resume(throwing: failure)
            } else if delivered == accepted {
                lock.unlock()
                continuation.resume()
            } else {
                waiters.append((accepted, continuation))
                lock.unlock()
            }
        }
    }

    func end() {
        lock.lock()
        let failed = failLocked(.ended)
        lock.unlock()
        for waiter in failed { waiter.resume(throwing: Failure.ended) }
    }

    private func failLocked(_ reason: Failure) -> [CheckedContinuation<Void, Error>] {
        if failure == nil { failure = reason }
        let failed = waiters.map(\.continuation)
        waiters.removeAll()
        return failed
    }
}

enum OriginalAuthRequestContext {
    @TaskLocal static var parent: OriginalAuthAttempt?
}

enum OriginalAuthFlowError: Error {
    case busy
    case successfulStopRequired
}

/// One actual original Auth/Hanlin operation. The original Lifetime supplies
/// synchronous retirement, admission and actual-operation drain; no new account
/// generation or asynchronous cancellation flag is introduced.
final class OriginalAuthAttempt: Sendable {
    enum Kind: Equatable, Sendable { case startup, ordinary, stop }
    let kind: Kind
    let captures: [EditorDocumentWriteCapture]
    private let lifetime: EditorDocumentWriteLifetime
    private let outer: EditorDocumentWriteLifetime.Observation
    private let parent: OriginalAuthAttempt?
    private let parentObservations: [EditorDocumentWriteLifetime.Observation]

    init(
        kind: Kind,
        parent: OriginalAuthAttempt? = OriginalAuthRequestContext.parent,
        restricting restrictions: [EditorDocumentWriteCapture] = []
    ) throws {
        try Task.checkCancellation()
        try parent?.validate()
        for restriction in restrictions { try restriction.validate() }
        let inheritedCaptures = (parent?.captures ?? []) + restrictions
        let lifetime = EditorDocumentWriteLifetime()
        let capture = try EditorDocumentWriteCapture(lifetime)
        guard let outer = lifetime.admitOperation(capture.token) else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
        self.kind = kind
        self.lifetime = lifetime
        self.outer = outer
        self.parent = parent
        captures = inheritedCaptures + [capture]
        parentObservations = inheritedCaptures.map { value in
            value.source.observe(value.token) { lifetime.markUnavailable() }
        }
    }

    func validate() throws {
        try Task.checkCancellation()
        for capture in captures { try capture.validate() }
    }

    var isCurrent: Bool {
        captures.allSatisfy { $0.source.isCurrent($0.token) }
    }

    func retire() { lifetime.markUnavailable() }
    func finishOuter() { outer.cancel() }
    func waitForDrain() async { await lifetime.waitForOperationsToDrain() }

    func admitStage() throws -> [EditorDocumentWriteLifetime.Observation] {
        try validate()
        return try EditorDocumentWriteCapture.acquireAll(captures)
    }

    /// Startup native calls are tracked by this exact attempt, not added to the
    /// account-operation drain which AccountStop itself must wait before dispatch.
    func startupBinding(validating: @escaping @Sendable () throws -> Void = {}) -> InvocationDispatchBinding {
        InvocationDispatchBinding(committedEvents: { nil }) { [self] _ in
            try validate()
            try validating()
            return InvocationDispatchPermit { [self] in
                try validate()
                try validating()
                let admissions = try EditorDocumentWriteCapture.acquireAll(captures)
                return InvocationDispatchCompletion {
                    for admission in admissions { admission.cancel() }
                }
            }
        }
    }

    deinit {
        retire()
        finishOuter()
    }
}


enum EditorDocumentWriteRejection: Sendable, Equatable {
    case retired
    case wrongContext
    case documentChanged
    case notHandling
    case notEditable
    case cancelled
    case invalidLease
    case unqualifiedDispatch
    case captureInProgress
    case failedWrite
}

enum EditorDocumentWriteError: Error, Sendable, Equatable {
    case rejected(EditorDocumentWriteRejection)
    case completedWithoutOwnership(EditorDocumentWriteRejection)
}


struct EditorDocumentWriteCapture: Sendable {
    let source: EditorDocumentWriteLifetime
    let token: EditorDocumentWriteLifetime.Token

    init(_ source: EditorDocumentWriteLifetime) throws {
        guard let token = source.token() else { throw EditorDocumentWriteError.rejected(.retired) }
        self.source = source
        self.token = token
    }

    init(source: EditorDocumentWriteLifetime, token: EditorDocumentWriteLifetime.Token) {
        self.source = source
        self.token = token
    }

    func validate() throws {
        guard source.isCurrent(token) else { throw EditorDocumentWriteError.rejected(.retired) }
    }

    static func acquireAll(_ captures: [Self]) throws -> [EditorDocumentWriteLifetime.Observation] {
        var admissions: [EditorDocumentWriteLifetime.Observation] = []
        do {
            for capture in captures {
                guard let admission = capture.source.admitOperation(capture.token) else {
                    throw EditorDocumentWriteError.rejected(.retired)
                }
                admissions.append(admission)
            }
            return admissions
        } catch {
            for admission in admissions { admission.cancel() }
            throw error
        }
    }

    func accountDispatchBinding() -> InvocationDispatchBinding {
        InvocationDispatchBinding { _ in
            try validate()
            return InvocationDispatchPermit {
                let admissions = try Self.acquireAll([self])
                return InvocationDispatchCompletion { for admission in admissions { admission.cancel() } }
            }
        }
    }
}


import Foundation

protocol EditorDocumentWriteLifetimeProviding: AnyObject, Sendable {
    var editorWriteLifetime: EditorDocumentWriteLifetime { get }
}

/// A passive generation belonging to one actual document. Invalidation does not
/// close the document, cancel an admitted service operation, or undo its effects.
final class EditorDocumentWriteLifetime: @unchecked Sendable {
    struct Token: Equatable, Sendable {
        fileprivate let source: UUID
        fileprivate let generation: UInt64
    }

    final class Observation: @unchecked Sendable {
        private let lock = NSLock()
        private var cancelBody: (@Sendable () -> Void)?

        init(cancel: @escaping @Sendable () -> Void) { cancelBody = cancel }
        func cancel() {
            lock.lock()
            let body = cancelBody
            cancelBody = nil
            lock.unlock()
            body?()
        }
        deinit { cancel() }
    }

    private let lock = NSLock()
    private let source = UUID()
    private var generation: UInt64 = 0
    private var exhausted = false
    private var available: Bool
    private var closingLeases: Set<UUID> = []
    private var admittedOperations: Set<UUID> = []
    private var drainWaiters: [CheckedContinuation<Void, Never>] = []
    private var observers: [UUID: @Sendable () -> Void] = [:]

    init(isAvailable: Bool = true) { available = isAvailable }

    func token() -> Token? {
        lock.lock()
        defer { lock.unlock() }
        return available && !exhausted ? Token(source: source, generation: generation) : nil
    }

    func isCurrent(_ token: Token) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return available && !exhausted && token.source == source && token.generation == generation
    }

    /// Admission and retirement use the same lock. A native call admitted before
    /// retirement keeps its lease until the actual synchronous RPC body returns.
    func admitOperation(_ token: Token) -> Observation? {
        let id = UUID()
        lock.lock()
        guard available, !exhausted, token.source == source, token.generation == generation else {
            lock.unlock()
            return nil
        }
        admittedOperations.insert(id)
        lock.unlock()
        return Observation { [self] in finishOperation(id) }
    }

    /// Used after beginClosing has synchronously stopped new admissions. Caller
    /// cancellation cannot make a still-running original native body disappear.
    func waitForOperationsToDrain() async {
        await withCheckedContinuation { continuation in
            lock.lock()
            if admittedOperations.isEmpty {
                lock.unlock()
                continuation.resume()
            } else {
                drainWaiters.append(continuation)
                lock.unlock()
            }
        }
    }

    private func finishOperation(_ id: UUID) {
        lock.lock()
        admittedOperations.remove(id)
        let waiters = admittedOperations.isEmpty ? drainWaiters : []
        if admittedOperations.isEmpty { drainWaiters.removeAll() }
        lock.unlock()
        for waiter in waiters { waiter.resume() }
    }

    func invalidate() {
        lock.lock()
        let callbacks = invalidateLocked()
        lock.unlock()
        for callback in callbacks { callback() }
    }

    /// The original close RPC may suspend while the document still reports open.
    /// Block new admissions as well as retiring captured tokens during that gap.
    func beginClosing() -> Observation {
        let id = UUID()
        lock.lock()
        closingLeases.insert(id)
        available = false
        let callbacks = invalidateLocked()
        lock.unlock()
        for callback in callbacks { callback() }
        return Observation { [weak self] in self?.finishClosing(id) }
    }

    func markUnavailable() {
        lock.lock()
        available = false
        let callbacks = invalidateLocked()
        lock.unlock()
        for callback in callbacks { callback() }
    }

    /// Called only after the original document has installed an opened view.
    /// A still-admitted close must finish before a later open can grant authority.
    func confirmOpened() {
        lock.lock()
        available = !exhausted && closingLeases.isEmpty
        lock.unlock()
    }

    private func finishClosing(_ id: UUID) {
        lock.lock()
        closingLeases.remove(id)
        // Completion, including failure, does not itself prove a fresh open.
        lock.unlock()
    }

    private func invalidateLocked() -> [@Sendable () -> Void] {
        if generation == UInt64.max {
            exhausted = true
        } else {
            generation += 1
        }
        let callbacks = Array(observers.values)
        observers.removeAll()
        return callbacks
    }

    /// Registration checks the expected token under the same lock as invalidation,
    /// so a change between capture and subscription cannot disappear.
    func observe(_ expected: Token, invalidated: @escaping @Sendable () -> Void) -> Observation {
        let id = UUID()
        lock.lock()
        let current = available && !exhausted && expected.source == source && expected.generation == generation
        if current { observers[id] = invalidated }
        lock.unlock()
        if !current { invalidated() }
        return Observation { [weak self] in self?.removeObserver(id) }
    }

    private func removeObserver(_ id: UUID) {
        lock.lock()
        observers.removeValue(forKey: id)
        lock.unlock()
    }
}


import Foundation

/// Carries an existing owner's admission through asynchronous original services.
/// The binding is optional; ordinary invocations keep their original behavior.
public struct InvocationDispatchBinding: Sendable {
    /// Identity for passive caller bookkeeping; it grants no dispatch authority.
    public let contextIdentity = UUID()
    private let prepareBody: @Sendable (String) async throws -> InvocationDispatchPermit
    private let committedEvents: (@Sendable () -> InvocationDispatchBinding?)?

    public init(
        committedEvents: (@Sendable () -> InvocationDispatchBinding?)? = nil,
        prepare: @escaping @Sendable (String) async throws -> InvocationDispatchPermit
    ) {
        self.committedEvents = committedEvents
        prepareBody = prepare
    }

    func prepare(messageName: String) async throws -> InvocationDispatchPermit {
        try await prepareBody(messageName)
    }

    public func bindingForCommittedEvents() -> InvocationDispatchBinding? {
        if let committedEvents { return committedEvents() }
        return self
    }

    /// Checks a retained original context without dispatching native work. Used
    /// when an opened document is reused and must prove its original account.
    public func validateForOperation(named messageName: String) async throws {
        _ = try await prepareBody(messageName)
    }
}

/// Preparation may suspend. Admission itself runs synchronously on the original
/// RPC queue, immediately before invoking the unchanged native middleware body.
public struct InvocationDispatchPermit: Sendable {
    private let beginBody: @Sendable () throws -> InvocationDispatchCompletion

    public init(begin: @escaping @Sendable () throws -> InvocationDispatchCompletion) {
        beginBody = begin
    }

    func begin() throws -> InvocationDispatchCompletion { try beginBody() }
}

/// Finishes only after the actual native RPC returns, even if its awaiting caller
/// already received cancellation. Calling finish twice has no additional effect.
public final class InvocationDispatchCompletion: @unchecked Sendable {
    private let lock = NSLock()
    private var finishBody: (@Sendable () -> Void)?
    private var failureBody: (@Sendable () -> Void)?

    public init(finish: @escaping @Sendable () -> Void) {
        finishBody = finish
        failureBody = nil
    }

    public init(finish: @escaping @Sendable () -> Void, failed: @escaping @Sendable () -> Void) {
        finishBody = finish
        failureBody = failed
    }

    public func markFailed() {
        lock.lock()
        let body = finishBody != nil ? failureBody : nil
        failureBody = nil
        lock.unlock()
        body?()
    }

    public func finish() {
        lock.lock()
        let body = finishBody
        finishBody = nil
        failureBody = nil
        lock.unlock()
        body?()
    }

    deinit { finish() }
}

public enum InvocationDispatchContext {
    @TaskLocal public static var binding: InvocationDispatchBinding?
}


private enum ControlFailure: Error { case failed(String) }

private final class Checks {
    var count = 0
    func require(_ value: Bool, _ reason: String) throws {
        count += 1
        if !value { throw ControlFailure.failed(reason) }
    }
    func retired(_ operation: () throws -> Void) throws {
        count += 1
        do { try operation() }
        catch EditorDocumentWriteError.rejected(.retired) { return }
        throw ControlFailure.failed("Expected original retired rejection")
    }
}

private final class Flag: @unchecked Sendable {
    private let lock = NSLock()
    private var value = false
    func set() { lock.lock(); value = true; lock.unlock() }
    func read() -> Bool { lock.lock(); defer { lock.unlock() }; return value }
}

// Test-only read observations. Original implementation text is not rewritten.
private extension OriginalEventDeliveryFence {
    func controlSnapshot() -> (accepted: UInt64, delivered: UInt64, waiters: Int, failed: Bool) {
        lock.lock(); defer { lock.unlock() }
        return (accepted, delivered, waiters.count, failure != nil)
    }
}
private extension EditorDocumentWriteLifetime {
    func controlSnapshot() -> (admitted: Int, waiting: Int) {
        lock.lock(); defer { lock.unlock() }
        return (admittedOperations.count, drainWaiters.count)
    }
}

private func until(_ predicate: @Sendable () -> Bool) async throws {
    let limit = ContinuousClock.now.advanced(by: .seconds(5))
    while !predicate() {
        if ContinuousClock.now >= limit { throw ControlFailure.failed("Bounded state handshake did not arrive") }
        await Task.yield()
    }
}

private actor HeldSink {
    private var entered = 0
    private var released = 0
    private var held: [(Int, CheckedContinuation<Void, Never>)] = []
    private var enteredWaiters: [(Int, CheckedContinuation<Void, Never>)] = []
    private var completed: [Int] = []
    func receive(_ data: Data) async {
        entered += 1
        let ordinal = entered
        let ready = enteredWaiters.filter { $0.0 <= entered }
        enteredWaiters.removeAll { $0.0 <= entered }
        for row in ready { row.1.resume() }
        if ordinal > released {
            await withCheckedContinuation { held.append((ordinal, $0)) }
        }
        completed.append(Int(String(decoding: data, as: UTF8.self))!)
    }
    func waitForEntered(_ count: Int) async {
        if entered >= count { return }
        await withCheckedContinuation { enteredWaiters.append((count, $0)) }
    }
    func releaseThrough(_ count: Int) {
        released = max(released, count)
        let ready = held.filter { $0.0 <= released }
        held.removeAll { $0.0 <= released }
        for row in ready { row.1.resume() }
    }
    func values() -> [Int] { completed }
}

private struct FIFOFixture {
    let fence: OriginalEventDeliveryFence
    let continuation: AsyncStream<Data>.Continuation
    let sink: HeldSink
    let consumer: Task<Void, Never>
    init() {
        let fence = OriginalEventDeliveryFence()
        let (stream, continuation) = AsyncStream.makeStream(of: Data.self)
        let sink = HeldSink()
        self.fence = fence; self.continuation = continuation; self.sink = sink
        // Foundation transport harness only. The actual Lib decoder and event
        // handlers are not present or claimed to have executed here.
        consumer = Task {
            defer { fence.end() }
            for await data in stream {
                defer { fence.didDeliverOne() }
                await sink.receive(data)
            }
        }
    }
    func enqueue(_ value: Int) { fence.enqueue(Data(String(value).utf8), into: continuation) }
    func finish() async { continuation.finish(); await consumer.value }
}

@main private struct FourSourceControls {
    static func main() async throws {
        guard CommandLine.arguments.count == 2 else { throw ControlFailure.failed("One case required") }
        let name = CommandLine.arguments[1]
        let checks = Checks()
        switch name {
        case "fifo-empty-frontier":
            let fence = OriginalEventDeliveryFence()
            try await fence.waitForCurrentFrontier()
            let state = fence.controlSnapshot()
            try checks.require(state.accepted == 0 && state.delivered == 0 && state.waiters == 0 && !state.failed, "Empty frontier")
        case "fifo-held-and-frozen-frontiers":
            let fixture = FIFOFixture()
            fixture.enqueue(1)
            await fixture.sink.waitForEntered(1)
            let firstDone = Flag(), secondDone = Flag()
            let first = Task { try await fixture.fence.waitForCurrentFrontier(); firstDone.set() }
            try await until { fixture.fence.controlSnapshot().waiters == 1 }
            fixture.enqueue(2)
            let second = Task { try await fixture.fence.waitForCurrentFrontier(); secondDone.set() }
            try await until { fixture.fence.controlSnapshot().waiters == 2 }
            try checks.require(!firstDone.read() && !secondDone.read(), "Accepted is not delivered")
            try checks.require(fixture.fence.controlSnapshot().delivered == 0, "Handler has not returned")
            await fixture.sink.releaseThrough(1)
            try await first.value
            await fixture.sink.waitForEntered(2)
            try checks.require(firstDone.read() && !secondDone.read(), "Later event cannot extend first captured frontier")
            try checks.require(fixture.fence.controlSnapshot().delivered == 1, "Second handler is still held")
            await fixture.sink.releaseThrough(2)
            try await second.value
            try checks.require(await fixture.sink.values() == [1, 2], "Actual one-consumer delivery order")
            try checks.require(fixture.fence.controlSnapshot().delivered == 2, "Both handlers returned")
            await fixture.finish()
        case "fifo-canceled-waiter-retained":
            let fixture = FIFOFixture()
            fixture.enqueue(7); await fixture.sink.waitForEntered(1)
            let ended = Flag()
            let waiter = Task {
                do {
                    try await fixture.fence.waitForCurrentFrontier()
                    // Exact public adapter's post-wait cancellation check.
                    try Task.checkCancellation()
                    ended.set(); return false
                } catch is CancellationError { ended.set(); return true }
            }
            try await until { fixture.fence.controlSnapshot().waiters == 1 }
            waiter.cancel()
            try checks.require(!ended.read() && fixture.fence.controlSnapshot().waiters == 1, "Cancel cannot erase held delivery")
            try checks.require(fixture.fence.controlSnapshot().delivered == 0, "No native/handler completion inferred")
            await fixture.sink.releaseThrough(1)
            try checks.require(try await waiter.value, "Canceled caller rejects only after actual frontier")
            try checks.require(await fixture.sink.values() == [7], "Cancellation did not cancel underlying handler")
            await fixture.finish()
        case "fifo-end-rejects-unresolved":
            let fence = OriginalEventDeliveryFence()
            let (stream, continuation) = AsyncStream.makeStream(of: Data.self)
            fence.enqueue(Data("1".utf8), into: continuation)
            let waiter = Task {
                do { try await fence.waitForCurrentFrontier(); return false }
                catch OriginalEventDeliveryFence.Failure.ended { return true }
            }
            try await until { fence.controlSnapshot().waiters == 1 }
            fence.end()
            try checks.require(try await waiter.value, "Actual consumer-end hook rejects pending frontier")
            try checks.require(fence.controlSnapshot().delivered == 0 && fence.controlSnapshot().failed, "Termination is not delivery")
            do { try await fence.waitForCurrentFrontier(); throw ControlFailure.failed("Ended fence admitted") }
            catch OriginalEventDeliveryFence.Failure.ended { try checks.require(true, "Terminal remains terminal") }
            continuation.finish(); withExtendedLifetime(stream) {}
        case "fifo-terminated-yield-rejected":
            let fence = OriginalEventDeliveryFence()
            let (stream, continuation) = AsyncStream.makeStream(of: Data.self)
            continuation.finish()
            fence.enqueue(Data("1".utf8), into: continuation)
            do { try await fence.waitForCurrentFrontier(); throw ControlFailure.failed("Terminated yield admitted") }
            catch OriginalEventDeliveryFence.Failure.ended { try checks.require(true, "Actual terminated AsyncStream yield fails") }
            try checks.require(fence.controlSnapshot().delivered == 0 && fence.controlSnapshot().failed, "No completion from failed enqueue")
            withExtendedLifetime(stream) {}
        case "fifo-concurrent-enqueue":
            let fixture = FIFOFixture()
            await withTaskGroup(of: Void.self) { group in
                for value in 0..<128 { group.addTask { fixture.enqueue(value) } }
                await group.waitForAll()
            }
            await fixture.sink.waitForEntered(1)
            let waiter = Task { try await fixture.fence.waitForCurrentFrontier() }
            try await until { fixture.fence.controlSnapshot().waiters == 1 }
            try checks.require(fixture.fence.controlSnapshot().accepted == 128 && fixture.fence.controlSnapshot().delivered == 0, "Concurrent enqueues retained while handler held")
            await fixture.sink.releaseThrough(128)
            try await waiter.value
            let values = await fixture.sink.values()
            try checks.require(values.count == 128 && Set(values) == Set(0..<128), "Every actual concurrent input delivered once")
            try checks.require(fixture.fence.controlSnapshot().delivered == 128 && !fixture.fence.controlSnapshot().failed, "Counts follow actual handler returns")
            await fixture.finish()
        case "auth-frozen-parent-and-restriction":
            let parent = try OriginalAuthAttempt(kind: .ordinary, parent: nil)
            let lifetime = EditorDocumentWriteLifetime()
            let restriction = try EditorDocumentWriteCapture(lifetime)
            let plain = try OriginalAuthRequestContext.$parent.withValue(parent) { try OriginalAuthAttempt(kind: .ordinary) }
            let child = try OriginalAuthRequestContext.$parent.withValue(parent) { try OriginalAuthAttempt(kind: .startup, restricting: [restriction]) }
            defer { child.finishOuter(); plain.finishOuter(); parent.finishOuter() }
            try checks.require(plain.captures.count == 2 && child.captures.count == 3, "Default parent lineage plus exact extra restriction")
            try checks.require(child.captures[0].source === parent.captures[0].source && child.captures[0].token == parent.captures[0].token, "Frozen parent retained")
            try checks.require(child.captures[1].source === restriction.source && child.captures[1].token == restriction.token, "Frozen restriction retained")
            lifetime.markUnavailable()
            try checks.require(!child.isCurrent && parent.isCurrent && plain.isCurrent, "Only restricted descendant retires")
            try checks.retired { _ = try child.admitStage() }
            parent.retire()
            try checks.require(!plain.isCurrent, "Original default parent retirement preserved")
        case "auth-retired-restriction-rejected":
            let lifetime = EditorDocumentWriteLifetime()
            let restriction = try EditorDocumentWriteCapture(lifetime)
            lifetime.markUnavailable()
            try checks.retired { _ = try OriginalAuthAttempt(kind: .ordinary, parent: nil, restricting: [restriction]) }
            try checks.require(lifetime.controlSnapshot().admitted == 0, "Rejected constructor does not admit retired restriction")
        case "auth-permit-rechecks-restriction":
            let lifetime = EditorDocumentWriteLifetime()
            let restriction = try EditorDocumentWriteCapture(lifetime)
            let child = try OriginalAuthAttempt(kind: .startup, parent: nil, restricting: [restriction])
            defer { child.finishOuter() }
            let permit = try await child.startupBinding().prepare(messageName: "AccountSelect")
            lifetime.markUnavailable()
            try checks.retired { _ = try permit.begin() }
            try checks.require(lifetime.controlSnapshot().admitted == 0, "No admission after prepare-to-begin retirement")
        case "auth-admitted-restriction-real-completion-drain":
            let lifetime = EditorDocumentWriteLifetime()
            let restriction = try EditorDocumentWriteCapture(lifetime)
            let child = try OriginalAuthAttempt(kind: .startup, parent: nil, restricting: [restriction])
            let permit = try await child.startupBinding().prepare(messageName: "AccountSelect")
            let completion = try permit.begin()
            try checks.require(lifetime.controlSnapshot().admitted == 1, "Actual original permit admitted restriction")
            lifetime.markUnavailable()
            let drained = Flag()
            let waiter = Task { await lifetime.waitForOperationsToDrain(); drained.set() }
            try await until { lifetime.controlSnapshot().waiting == 1 }
            waiter.cancel()
            try checks.require(!drained.read() && lifetime.controlSnapshot().admitted == 1, "Caller cancellation cannot erase admitted work")
            completion.finish()
            await waiter.value
            try checks.require(drained.read() && lifetime.controlSnapshot().admitted == 0, "Original completion released actual admission")
            completion.finish()
            try checks.require(lifetime.controlSnapshot().admitted == 0 && !child.isCurrent, "Duplicate completion does not revive ownership")
            child.finishOuter(); await child.waitForDrain()
        default: throw ControlFailure.failed("Unknown case")
        }
        print("PASS \(name) assertions=\(checks.count)")
    }
}
