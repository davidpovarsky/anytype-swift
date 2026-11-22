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



#sourceLocation(file: "auth_controls_review/EditorDocumentWriteOwner.swift", line: 5)
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
#sourceLocation()

#sourceLocation(file: "auth_controls_review/EditorDocumentWriteOwner.swift", line: 18)
enum EditorDocumentWriteError: Error, Sendable, Equatable {
    case rejected(EditorDocumentWriteRejection)
    case completedWithoutOwnership(EditorDocumentWriteRejection)
}
#sourceLocation()

#sourceLocation(file: "auth_controls_review/EditorDocumentWriteOwner.swift", line: 111)
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
#sourceLocation()


/// One existing owner's operation, including native RPCs that outlive caller
/// cancellation. This state grants no authority; each dispatch supplies the
/// captured owner's synchronous validation before the native body may begin.
final class EditorDocumentWriteOperation: @unchecked Sendable {
    private let lock = NSLock()
    private var outerFinished = false
    private var runningRPCs = 0
    private var failed = false
    private var onDrained: (@Sendable (Bool) -> Void)?

    init(onDrained: @escaping @Sendable (Bool) -> Void) { self.onDrained = onDrained }

    var isAccepting: Bool {
        lock.lock()
        defer { lock.unlock() }
        return !outerFinished
    }

    var hasFailed: Bool {
        lock.lock()
        defer { lock.unlock() }
        return failed
    }

    func markFailed() {
        lock.lock()
        failed = true
        lock.unlock()
    }

    func permit(
        acquire: @escaping @Sendable () throws -> [EditorDocumentWriteLifetime.Observation]
    ) -> InvocationDispatchPermit {
        InvocationDispatchPermit { [self] in
            lock.lock()
            let admissions: [EditorDocumentWriteLifetime.Observation]
            do {
                guard !outerFinished else { throw EditorDocumentWriteError.rejected(.invalidLease) }
                admissions = try acquire()
                runningRPCs += 1
                lock.unlock()
            } catch {
                failed = true
                lock.unlock()
                throw error
            }
            return InvocationDispatchCompletion(finish: { [self] in
                for admission in admissions { admission.cancel() }
                finishRPC()
            }, failed: { [self] in markFailed() })
        }
    }

    /// The actor owner removes an already-drained operation synchronously. An
    /// RPC still running keeps the callback until its actual native completion.
    func finishOuter() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        outerFinished = true
        guard runningRPCs == 0 else { return false }
        onDrained = nil
        return true
    }

    private func finishRPC() {
        lock.lock()
        runningRPCs -= 1
        let callback = outerFinished && runningRPCs == 0 ? onDrained : nil
        if callback != nil { onDrained = nil }
        let failed = failed
        lock.unlock()
        callback?(failed)
    }
}



/// A passive fence around the original account transition, not another account
/// selector. A cancelled caller cannot release it while its native RPC runs.
final class EditorAccountWriteTransition: Sendable {
    let binding: InvocationDispatchBinding
    private let operation: EditorDocumentWriteOperation
    private let state: State

    init(lifetime: EditorDocumentWriteLifetime, rpcNames: Set<String>, attemptCaptures: [EditorDocumentWriteCapture] = []) {
        let state = State(lifetime: lifetime)
        let operation = EditorDocumentWriteOperation { _ in state.release() }
        self.state = state
        self.operation = operation
        // This tracker is entered only from the original unbound AuthService.
        // Its ordinary committed global events keep that original context.
        binding = InvocationDispatchBinding(committedEvents: { nil }) { messageName in
            guard rpcNames.contains(messageName) else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
            for capture in attemptCaptures { try capture.validate() }
            await lifetime.waitForOperationsToDrain()
            try Task.checkCancellation()
            for capture in attemptCaptures { try capture.validate() }
            // Recheck the frozen original attempt at the queued native begin,
            // not merely before an await. An empty default preserves old callers.
            return operation.permit {
                try EditorDocumentWriteCapture.acquireAll(attemptCaptures)
            }
        }
    }

    func finish(verifiedAccountIsCurrent: @escaping @Sendable () -> Bool = { false }) {
        guard state.finishOuter(verifiedAccountIsCurrent: verifiedAccountIsCurrent) else { return }
        if operation.finishOuter() { state.release() }
    }

    /// Waits for the original transition's actual native drain and release
    /// effects. This does not certify a current account token or subscription.
    func finishAndWaitForRelease(
        verifiedAccountIsCurrent: @escaping @Sendable () -> Bool = { false }
    ) async {
        finish(verifiedAccountIsCurrent: verifiedAccountIsCurrent)
        await state.waitForRelease()
    }

    deinit { finish() }

    private final class State: @unchecked Sendable {
        private let lock = NSLock()
        private let lifetime: EditorDocumentWriteLifetime
        private let closing: EditorDocumentWriteLifetime.Observation
        private var outerFinished = false
        private var released = false
        private var releaseCompleted = false
        private var releaseWaiters: [CheckedContinuation<Void, Never>] = []
        private var verifiedAccountIsCurrent: (@Sendable () -> Bool)?

        init(lifetime: EditorDocumentWriteLifetime) {
            self.lifetime = lifetime
            closing = lifetime.beginClosing()
        }

        func finishOuter(verifiedAccountIsCurrent: @escaping @Sendable () -> Bool) -> Bool {
            lock.lock()
            defer { lock.unlock() }
            guard !outerFinished else { return false }
            outerFinished = true
            self.verifiedAccountIsCurrent = verifiedAccountIsCurrent
            return true
        }

        func waitForRelease() async {
            await withCheckedContinuation { continuation in
                lock.lock()
                if releaseCompleted {
                    lock.unlock()
                    continuation.resume()
                } else {
                    releaseWaiters.append(continuation)
                    lock.unlock()
                }
            }
        }

        func release() {
            lock.lock()
            guard outerFinished, !released else { lock.unlock(); return }
            released = true
            let verify = verifiedAccountIsCurrent
            verifiedAccountIsCurrent = nil
            lock.unlock()
            closing.cancel()
            // Setter confirmation while the close lease existed could not make
            // tokens available. Only a completed verified transition may do so.
            if verify?() == true { lifetime.confirmOpened() }
            // A release claim made before these effects is not completion.
            // Registration and completion share the same lock; resume outside it.
            lock.lock()
            releaseCompleted = true
            let waiters = releaseWaiters
            releaseWaiters.removeAll()
            lock.unlock()
            for waiter in waiters { waiter.resume() }
        }
    }
}

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/ServiceLayer/Auth/AuthService.swift", line: 10)
enum OriginalAuthRequestContext {
    @TaskLocal static var parent: OriginalAuthAttempt?
}
#sourceLocation()

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/ServiceLayer/Auth/AuthService.swift", line: 14)
enum OriginalAuthFlowError: Error {
    case busy
    case successfulStopRequired
}
#sourceLocation()

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/ServiceLayer/Auth/AuthService.swift", line: 22)
final class OriginalAuthAttempt: Sendable {
    enum Kind: Equatable, Sendable { case startup, ordinary, stop }
    let kind: Kind
    let captures: [EditorDocumentWriteCapture]
    private let lifetime: EditorDocumentWriteLifetime
    private let outer: EditorDocumentWriteLifetime.Observation
    private let parent: OriginalAuthAttempt?
    private let parentObservations: [EditorDocumentWriteLifetime.Observation]

    init(kind: Kind, parent: OriginalAuthAttempt? = OriginalAuthRequestContext.parent) throws {
        try Task.checkCancellation()
        try parent?.validate()
        let lifetime = EditorDocumentWriteLifetime()
        let capture = try EditorDocumentWriteCapture(lifetime)
        guard let outer = lifetime.admitOperation(capture.token) else {
            throw EditorDocumentWriteError.rejected(.retired)
        }
        self.kind = kind
        self.lifetime = lifetime
        self.outer = outer
        self.parent = parent
        captures = (parent?.captures ?? []) + [capture]
        parentObservations = (parent?.captures ?? []).map { value in
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
            return InvocationDispatchPermit {
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
#sourceLocation()

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/ServiceLayer/Auth/LoginStateService.swift", line: 86)
private final class StartupTasks: @unchecked Sendable {
        private let lock = NSLock()
        private var cancelled = false
        private var primary: Task<Void, Error>?
        private var membership: Task<Void, Error>?

        func installPrimary(_ task: Task<Void, Error>) {
            lock.lock()
            primary = task
            let shouldCancel = cancelled
            lock.unlock()
            if shouldCancel { task.cancel() }
        }
        func installMembership(_ task: Task<Void, Error>) {
            lock.lock()
            membership = task
            let shouldCancel = cancelled
            lock.unlock()
            if shouldCancel { task.cancel() }
        }
        func cancel() {
            lock.lock()
            cancelled = true
            let primary = primary
            let membership = membership
            lock.unlock()
            primary?.cancel()
            membership?.cancel()
        }
        private func primaryTask() -> Task<Void, Error>? {
            lock.lock()
            defer { lock.unlock() }
            return primary
        }
        private func membershipTask() -> Task<Void, Error>? {
            lock.lock()
            defer { lock.unlock() }
            return membership
        }
        func drain() async {
            _ = try? await primaryTask()?.value
            // Primary may have installed the owned membership task before it
            // ended; read that handle only after actual primary completion.
            _ = try? await membershipTask()?.value
        }
    }
#sourceLocation()

// Controlled test dependencies, never production account or native middleware.
actor Gate {
    private var opened: Bool
    private var waiters: [CheckedContinuation<Void, Never>] = []
    init(open: Bool = false) { opened = open }
    func wait() async {
        if opened { return }
        await withCheckedContinuation { waiters.append($0) }
    }
    func release() {
        opened = true
        let pending = waiters
        waiters.removeAll()
        for waiter in pending { waiter.resume() }
    }
}

actor ResultBox {
    private var result: String?
    func set(_ value: String) { result = value }
    func get() -> String? { result }
}

enum FixtureError: Error { case nativeStopFailed, assertion(String) }
enum HanlinHostError: Error { case staleContext }

func require(_ value: Bool, _ message: String) throws {
    if !value { throw FixtureError.assertion(message) }
}

func eventually(_ result: ResultBox, milliseconds: Int = 1500) async -> String? {
    for _ in 0..<(milliseconds / 10) {
        if let value = await result.get() { return value }
        try? await Task.sleep(nanoseconds: 10_000_000)
    }
    return await result.get()
}

func errorName(_ error: Error) -> String {
    if error is CancellationError { return "cancelled" }
    if case FixtureError.nativeStopFailed = error { return "nativeStopFailed" }
    if case OriginalAuthFlowError.successfulStopRequired = error { return "successfulStopRequired" }
    if case OriginalAuthFlowError.busy = error { return "busy" }
    if case HanlinHostError.staleContext = error { return "staleContext" }
    return String(describing: error)
}

final class AccountFixture: Sendable {
    struct Account: Sendable { let id = "unit-account" }
    let account = Account()
    let editorWriteLifetime: EditorDocumentWriteLifetime? = EditorDocumentWriteLifetime()
}

actor LoginFixture {
    let entered = Gate()
    let release: Gate
    private(set) var cleanups = 0
    init(hold: Bool = false) { release = Gate(open: !hold) }
    func cleanStateAfterLogout() async {
        await entered.release()
        await release.wait()
        cleanups += 1
    }
}

actor NativeFixture {
    let startupEntered = Gate()
    let releaseStartup = Gate()
    let stopQueued = Gate()
    let releaseStopDispatch: Gate
    let stopCallback = Gate()
    private var remainingFailures: Int
    private(set) var stopDispatches = 0
    init(holdStop: Bool = false, failures: Int = 0) {
        releaseStopDispatch = Gate(open: !holdStop)
        remainingFailures = failures
    }
    func startup() async throws {
        guard let binding = InvocationDispatchContext.binding else { throw FixtureError.assertion("missing startup binding") }
        let permit = try await binding.prepare(messageName: "AccountSelect")
        let completion = try permit.begin()
        defer { completion.finish() }
        await startupEntered.release()
        await releaseStartup.wait()
    }
    func logout(removeData: Bool) async throws {
        guard let binding = InvocationDispatchContext.binding else { throw FixtureError.assertion("missing Stop binding") }
        let permit = try await binding.prepare(messageName: "AccountStop")
        await stopQueued.release()
        await releaseStopDispatch.wait()
        let completion = try permit.begin()
        defer { completion.finish() }
        stopDispatches += 1
        if remainingFailures > 0 {
            remainingFailures -= 1
            completion.markFailed()
            throw FixtureError.nativeStopFailed
        }
        await releaseStartup.release()
        await stopCallback.release()
    }
}

actor BootstrapFixture {
    private(set) var quiesces = 0
    func quiesceAccountOperations() { quiesces += 1 }
}

@MainActor final class PinkhaHanlinAccountOwner {
    static let shared = PinkhaHanlinAccountOwner()
    private(set) var closes = 0
    func closeAccount(_ account: String, removeData: Bool) async throws { closes += 1 }
}

protocol StopProbe: Sendable {
    func logout(removeData: Bool) async throws
    func fixtureStartup() async throws
    func checkCanBegin() async -> String
}

actor AuthStopProbe: StopProbe {
    let authMiddleService: NativeFixture
    let loginStateService: LoginFixture
    let accountManager: AccountFixture
    private var current: OriginalAuthAttempt?
    private var stopping: OriginalAuthAttempt?
    private var successfulStopRequired = false
    init(native: NativeFixture, login: LoginFixture, accounts: AccountFixture) {
        authMiddleService = native; loginStateService = login; accountManager = accounts
    }
    // Synthetic held startup surrounds an actual transition and attempt. This
    // isolates Stop ownership; it does not simulate the full login pipeline.
    func fixtureStartup() async throws {
        let (attempt, transition) = try begin(kind: .startup, rpcNames: ["AccountSelect"])
        do {
            try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
                try await authMiddleService.startup()
            }
            try requireCurrent(attempt)
            await transition?.finishAndWaitForRelease()
            finish(attempt)
        } catch {
            attempt.retire()
            await transition?.finishAndWaitForRelease()
            attempt.finishOuter()
            await attempt.waitForDrain()
            finish(attempt)
            throw error
        }
    }
    func checkCanBegin() async -> String {
        do {
            let (attempt, transition) = try begin(kind: .ordinary, rpcNames: ["WalletCreate"])
            await transition?.finishAndWaitForRelease()
            finish(attempt)
            return "allowed"
        } catch { return errorName(error) }
    }

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/ServiceLayer/Auth/AuthService.swift", line: 299)
func logout(removeData: Bool) async throws {
        guard InvocationDispatchContext.binding == nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        guard stopping == nil else { throw OriginalAuthFlowError.busy }
        let previous = current
        if let previous {
            // Preserve the existing destructive overlap rejection. Only the
            // original Back/logout(false) path can cancel a pending startup.
            guard previous.kind == .startup, !removeData else { throw OriginalAuthFlowError.busy }
        }
        let stop = try OriginalAuthAttempt(kind: .stop)
        stopping = stop
        previous?.retire()
        let transition = accountManager.editorWriteLifetime.map {
            EditorAccountWriteTransition(lifetime: $0, rpcNames: ["AccountStop"], attemptCaptures: stop.captures)
        }
        // Once accepted, Stop owns cleanup independently of the caller. A caller
        // cancellation must not revoke the only native RPC that can release the
        // retired startup's AccountSelect/Create callback.
        let cleanup = Task { [self] in
            do {
                // Real original Stop is invoked BEFORE any retired-start drain await.
                // AccountStop(false) may return while that start is still cleaning.
                try await InvocationDispatchContext.$binding.withValue(transition?.binding) {
                    try await authMiddleService.logout(removeData: removeData)
                }
                await previous?.waitForDrain()
                await loginStateService.cleanStateAfterLogout()
                await transition?.finishAndWaitForRelease()
                successfulStopRequired = false
                stop.finishOuter()
                if stopping === stop { stopping = nil }
            } catch {
                stop.retire()
                await transition?.finishAndWaitForRelease()
                // A failed Stop may leave the retired native startup pending.
                // Keep its cleanup owned by that attempt and admit another Stop;
                // joining it here would prevent the retry needed to release it.
                successfulStopRequired = true
                stop.finishOuter()
                if stopping === stop { stopping = nil }
                throw error
            }
        }
        try await cleanup.value
        try Task.checkCancellation()
    }
#sourceLocation()

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/ServiceLayer/Auth/AuthService.swift", line: 384)
private func begin(kind: OriginalAuthAttempt.Kind, rpcNames: Set<String>) throws -> (OriginalAuthAttempt, EditorAccountWriteTransition?) {
        guard InvocationDispatchContext.binding == nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        guard current == nil, stopping == nil else { throw OriginalAuthFlowError.busy }
        guard !successfulStopRequired else { throw OriginalAuthFlowError.successfulStopRequired }
        let accountLifetime = accountManager.editorWriteLifetime
        if kind == .startup, accountLifetime == nil {
            // A replacement provider without the original account lifetime
            // cannot begin this capture-qualified startup.
            throw EditorDocumentWriteError.rejected(.retired)
        }
        let attempt = try OriginalAuthAttempt(kind: kind)
        let transition = accountLifetime.map {
            EditorAccountWriteTransition(lifetime: $0, rpcNames: rpcNames, attemptCaptures: attempt.captures)
        }
        current = attempt
        return (attempt, transition)
    }
#sourceLocation()

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/ServiceLayer/Auth/AuthService.swift", line: 404)
private func requireCurrent(_ attempt: OriginalAuthAttempt) throws {
        guard current === attempt, stopping == nil else { throw EditorDocumentWriteError.rejected(.retired) }
        try attempt.validate()
    }
#sourceLocation()

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/ServiceLayer/Auth/AuthService.swift", line: 409)
private func finish(_ attempt: OriginalAuthAttempt) {
        attempt.finishOuter()
        if current === attempt { current = nil }
    }
#sourceLocation()

}
actor PinkhaStopProbe: StopProbe {
    let base: AuthStopProbe
    let accounts: AccountFixture
    let bootstrap = BootstrapFixture()
    private var current: OriginalAuthAttempt?
    private var stopping: OriginalAuthAttempt?
    private var successfulStopRequired = false
    init(base: AuthStopProbe, accounts: AccountFixture) { self.base = base; self.accounts = accounts }
    func fixtureStartup() async throws {
        let base = base
        try await perform(kind: .startup) { attempt in
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.fixtureStartup() }
        }
    }
    func checkCanBegin() async -> String {
        do {
            try await perform(kind: .ordinary) { _ in () }
            return "allowed"
        } catch { return errorName(error) }
    }

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/Pinkha/AI/PinkhaHanlinAuthService.swift", line: 93)
func logout(removeData: Bool) async throws {
        guard stopping == nil else { throw HanlinHostError.staleContext }
        let previous = current
        if let previous {
            // Keep the existing busy rejection for destructive overlap. Only
            // the real Back/logout(false) route supersedes a pending startup.
            guard previous.kind == .startup, !removeData else { throw HanlinHostError.staleContext }
        }
        let stop = try OriginalAuthAttempt(kind: .stop)
        stopping = stop
        previous?.retire() // synchronous, also revokes the child's Auth attempt
        let originalAccount = accounts.account.id
        let bootstrap = bootstrap
        // This accepted Stop must outlive cancellation of its UI caller. Its
        // native child is the operation that releases any retired startup.
        let cleanup = Task { [self] in
            do {
                // True removal keeps the original journal poison/flush/removal
                // before native erasure. This path never overlaps a startup.
                try await PinkhaHanlinAccountOwner.shared.closeAccount(originalAccount, removeData: removeData)
                // Dispatch real original Stop before joining any retired startup
                // or bootstrap stage. It can cancel native AccountSelect/Create.
                try await OriginalAuthRequestContext.$parent.withValue(stop) {
                    try await base.logout(removeData: removeData)
                }
                await previous?.waitForDrain()
                await bootstrap.quiesceAccountOperations()
                // An operation admitted before retirement may drain after Stop
                // began. Reclose its non-destructive presentation state afterwards.
                try await PinkhaHanlinAccountOwner.shared.closeAccount(originalAccount, removeData: false)
                let finalAccount = accounts.account.id
                if !finalAccount.utf8.elementsEqual(originalAccount.utf8) {
                    try await PinkhaHanlinAccountOwner.shared.closeAccount(finalAccount, removeData: false)
                }
                successfulStopRequired = false
                stop.finishOuter()
                if stopping === stop { stopping = nil }
            } catch {
                stop.retire()
                // Do not join a native startup after Stop failed: another Stop
                // must remain admissible to release that retired operation.
                successfulStopRequired = true
                stop.finishOuter()
                if stopping === stop { stopping = nil }
                throw error
            }
        }
        try await cleanup.value
        try Task.checkCancellation()
    }
#sourceLocation()

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/Pinkha/AI/PinkhaHanlinAuthService.swift", line: 182)
private func perform<Value: Sendable>(
        kind: OriginalAuthAttempt.Kind,
        operation: @escaping @Sendable (OriginalAuthAttempt) async throws -> Value
    ) async throws -> Value {
        guard current == nil, stopping == nil, !successfulStopRequired else { throw HanlinHostError.staleContext }
        let attempt = try OriginalAuthAttempt(kind: kind)
        current = attempt
        return try await withTaskCancellationHandler {
            do {
                let result = try await operation(attempt)
                try requireCurrent(attempt)
                attempt.finishOuter()
                if current === attempt { current = nil }
                return result
            } catch {
                attempt.retire()
                attempt.finishOuter()
                await attempt.waitForDrain()
                if current === attempt { current = nil }
                throw error
            }
        } onCancel: { attempt.retire() }
    }
#sourceLocation()

#sourceLocation(file: "stageb-review/auth/candidate/Anytype/Sources/Pinkha/AI/PinkhaHanlinAuthService.swift", line: 206)
private func requireCurrent(_ attempt: OriginalAuthAttempt) throws {
        guard current === attempt, stopping == nil else { throw HanlinHostError.staleContext }
        try attempt.validate()
    }
#sourceLocation()

}

struct FixtureSet: Sendable {
    let native: NativeFixture
    let login: LoginFixture
    let probe: any StopProbe
    init(pinkha: Bool, holdStop: Bool = false, holdCleanup: Bool = false, failures: Int = 0) {
        let accounts = AccountFixture()
        native = NativeFixture(holdStop: holdStop, failures: failures)
        login = LoginFixture(hold: holdCleanup)
        let auth = AuthStopProbe(native: native, login: login, accounts: accounts)
        probe = pinkha ? PinkhaStopProbe(base: auth, accounts: accounts) : auth
    }
    func start() -> Task<Void, Never> {
        Task { do { try await probe.fixtureStartup() } catch {} }
    }
    func stop(_ result: ResultBox) -> Task<Void, Never> {
        Task {
            do { try await probe.logout(removeData: false); await result.set("ok") }
            catch { await result.set(errorName(error)) }
        }
    }
}

func queuedCancellation(pinkha: Bool) async throws {
    let fixture = FixtureSet(pinkha: pinkha, holdStop: true)
    let startup = fixture.start()
    await fixture.native.startupEntered.wait()
    let result = ResultBox()
    let stop = fixture.stop(result)
    await fixture.native.stopQueued.wait()
    stop.cancel()
    await fixture.native.releaseStopDispatch.release()
    let observed = await eventually(result)
    // Always release synthetic callbacks after the bounded observation, so a
    // failing old implementation cannot leave the runner suspended forever.
    await fixture.native.releaseStartup.release()
    await startup.value
    await stop.value
    try require(observed == "cancelled", "accepted Stop failed to finish before cancellation surfaced: \(String(describing: observed))")
    try require(await fixture.native.stopDispatches == 1, "queued Stop did not dispatch exactly once")
    try require(await fixture.login.cleanups == 1, "Stop cleanup missing")
    try require(await fixture.probe.checkCanBegin() == "allowed", "successful Stop did not reopen admission")
}

func callbackCancellation(pinkha: Bool) async throws {
    let fixture = FixtureSet(pinkha: pinkha, holdCleanup: true)
    let startup = fixture.start()
    await fixture.native.startupEntered.wait()
    let result = ResultBox()
    let stop = fixture.stop(result)
    await fixture.login.entered.wait()
    stop.cancel()
    try? await Task.sleep(nanoseconds: 30_000_000)
    let returnedEarly = await result.get()
    await fixture.login.release.release()
    let observed = await eventually(result)
    await startup.value
    await stop.value
    try require(returnedEarly == nil, "caller returned before actual cleanup")
    try require(observed == "cancelled", "caller cancellation not surfaced after cleanup")
    try require(await fixture.login.cleanups == 1, "cleanup did not finish exactly once")
}

func failedStopRetry(pinkha: Bool) async throws {
    let fixture = FixtureSet(pinkha: pinkha, failures: 1)
    let startup = fixture.start()
    await fixture.native.startupEntered.wait()
    let firstResult = ResultBox()
    let first = fixture.stop(firstResult)
    let observed = await eventually(firstResult)
    if observed == nil { await fixture.native.releaseStartup.release() }
    await first.value
    let cleanupAfterFailure = await fixture.login.cleanups
    let admissionAfterFailure = await fixture.probe.checkCanBegin()
    let retryResult = ResultBox()
    let retry = fixture.stop(retryResult)
    let retried = await eventually(retryResult)
    await fixture.native.releaseStartup.release()
    await startup.value
    await retry.value
    try require(observed == "nativeStopFailed", "failed Stop joined pending startup instead of permitting retry")
    try require(cleanupAfterFailure == 0, "failed Stop ran logout cleanup prematurely")
    try require(admissionAfterFailure != "allowed", "new work admitted while failed Stop unresolved")
    try require(retried == "ok", "retry Stop failed")
    try require(await fixture.native.stopDispatches == 2, "retry did not dispatch exactly once")
    try require(await fixture.login.cleanups == 1, "successful retry cleanup missing")
    try require(await fixture.probe.checkCanBegin() == "allowed", "successful retry retained failed Stop guard")
}

func failedStopBlocksAfterDrain(pinkha: Bool) async throws {
    let fixture = FixtureSet(pinkha: pinkha, failures: 1)
    let startup = fixture.start()
    await fixture.native.startupEntered.wait()
    let result = ResultBox()
    let stop = fixture.stop(result)
    let observed = await eventually(result)
    await fixture.native.releaseStartup.release()
    await startup.value
    await stop.value
    let next = await fixture.probe.checkCanBegin()
    let retryResult = ResultBox()
    let retry = fixture.stop(retryResult)
    await retry.value
    try require(observed == "nativeStopFailed", "failed Stop did not return independently")
    try require(next == (pinkha ? "staleContext" : "successfulStopRequired"), "failed Stop guard not preserved after original startup drain: \(next)")
    try require(await fixture.probe.checkCanBegin() == "allowed", "successful retry did not clear guard")
}

func cancelledBeforeAdmission() async throws {
    let fixture = FixtureSet(pinkha: false)
    let startup = fixture.start()
    await fixture.native.startupEntered.wait()
    let begin = Gate()
    let result = ResultBox()
    let stop = Task {
        await begin.wait()
        do { try await fixture.probe.logout(removeData: false); await result.set("ok") }
        catch { await result.set(errorName(error)) }
    }
    stop.cancel()
    await begin.release()
    let observed = await eventually(result)
    await stop.value
    let admission = await fixture.probe.checkCanBegin()
    await fixture.native.releaseStartup.release()
    await startup.value
    try require(observed == "cancelled", "cancelled caller was accepted as Stop")
    try require(await fixture.native.stopDispatches == 0, "cancelled caller dispatched native Stop")
    try require(admission == "busy", "cancelled caller removed original startup ownership")
}

func membershipDrain() async throws {
    let tasks = StartupTasks()
    let install = Gate()
    let membershipEntered = Gate()
    let releaseMembership = Gate()
    let cancellation = ResultBox()
    let drained = ResultBox()
    let primary = Task<Void, Error> {
        await install.wait()
        let membership = Task<Void, Error> {
            await membershipEntered.release()
            await releaseMembership.wait()
            await cancellation.set(Task.isCancelled ? "cancelled" : "live")
        }
        tasks.installMembership(membership)
    }
    tasks.installPrimary(primary)
    tasks.cancel()
    let drain = Task { await tasks.drain(); await drained.set("done") }
    await install.release()
    await membershipEntered.wait()
    try? await Task.sleep(nanoseconds: 30_000_000)
    let before = await drained.get()
    await releaseMembership.release()
    await drain.value
    try require(before == nil, "drain skipped late-installed membership")
    try require(await cancellation.get() == "cancelled", "late membership did not inherit cancellation")
    try require(await drained.get() == "done", "owned membership never drained")
}

@main struct Runner {
    static func main() async {
        let cases: [(String, @Sendable () async throws -> Void)] = [
            ("auth_queued_stop_survives_caller_cancellation", { try await queuedCancellation(pinkha: false) }),
            ("pinkha_queued_stop_survives_caller_cancellation", { try await queuedCancellation(pinkha: true) }),
            ("auth_callback_cancellation_waits_cleanup", { try await callbackCancellation(pinkha: false) }),
            ("pinkha_callback_cancellation_waits_cleanup", { try await callbackCancellation(pinkha: true) }),
            ("auth_failed_stop_allows_retry_before_start_drain", { try await failedStopRetry(pinkha: false) }),
            ("pinkha_failed_stop_allows_retry_before_start_drain", { try await failedStopRetry(pinkha: true) }),
            ("auth_failed_stop_blocks_new_work_after_drain", { try await failedStopBlocksAfterDrain(pinkha: false) }),
            ("pinkha_failed_stop_blocks_new_work_after_drain", { try await failedStopBlocksAfterDrain(pinkha: true) }),
            ("cancellation_before_stop_admission_preserves_startup", { try await cancelledBeforeAdmission() }),
            ("membership_installed_after_retirement_is_cancelled_and_drained", { try await membershipDrain() })
        ]
        var rows: [[String: String]] = []
        for (name, body) in cases {
            do { try await body(); rows.append(["id": name, "status": "PASS"]) }
            catch { rows.append(["id": name, "status": "FAIL", "error": String(describing: error)]) }
        }
        let failures = rows.filter { $0["status"] == "FAIL" }.count
        let report: [String: Any] = ["scope": "source-extracted Swift unit controls with controlled native callbacks", "pass": rows.count - failures, "fail": failures, "skip": 0, "cases": rows, "pid": ProcessInfo.processInfo.processIdentifier]
        let data = try! JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
        print(String(data: data, encoding: .utf8)!)
        if failures != 0 { exit(1) }
    }
}
