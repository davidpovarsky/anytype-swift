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


enum OriginalAuthRequestContext {
    @TaskLocal static var parent: OriginalAuthAttempt?
}


enum OriginalAuthFlowError: Error {
    case busy
    case successfulStopRequired
}


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



protocol AuthServiceProtocol: Sendable {
    func createWallet() async throws -> String
    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData
    func walletRecovery(mnemonic: String) async throws
    
    func accountRecover() async throws
   
    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData
    
    /// Get mnemonic (recovery phrase) by entropy from qr code
    func mnemonicByEntropy(_ entropy: String) async throws -> String

    func logout(removeData: Bool) async throws
    func deleteAccount() async throws -> AccountStatus
    func restoreAccount() async throws -> AccountStatus
}


final class OriginalApplicationConsumerDemand: @unchecked Sendable {
    enum ReadinessError: Error {
        case consumerEnded
        case demandNotForwarded
        case alreadyWaiting
    }

    private enum State {
        case waiting
        case requested
        case ended
    }

    private let lock = NSLock()
    private var state: State = .waiting
    private var waiter: CheckedContinuation<Void, Error>?
    private let onEnd: @Sendable () -> Void

    init(onEnd: @escaping @Sendable () -> Void = {}) {
        self.onEnd = onEnd
    }

    /// Called only after a positive request returned from the original
    /// upstream subscription. Completion/cancellation during that call wins.
    func didForwardPositiveDemand() {
        lock.lock()
        guard case .waiting = state else {
            lock.unlock()
            return
        }
        state = .requested
        let continuation = waiter
        waiter = nil
        lock.unlock()
        continuation?.resume()
    }

    func end() {
        lock.lock()
        guard case .ended = state else {
            state = .ended
            let continuation = waiter
            waiter = nil
            lock.unlock()
            continuation?.resume(throwing: ReadinessError.consumerEnded)
            onEnd()
            return
        }
        lock.unlock()
    }

    /// A synchronous admission fact, checked again after every startup await.
    /// It does not claim continuous demand or change AsyncPublisher buffering.
    func validateRequested() throws {
        lock.lock()
        defer { lock.unlock() }
        switch state {
        case .requested: return
        case .waiting: throw ReadinessError.demandNotForwarded
        case .ended: throw ReadinessError.consumerEnded
        }
    }

    func waitUntilRequested() async throws {
        try await withTaskCancellationHandler {
            try Task.checkCancellation()
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                lock.lock()
                switch state {
                case .waiting:
                    guard waiter == nil else {
                        lock.unlock()
                        continuation.resume(throwing: ReadinessError.alreadyWaiting)
                        return
                    }
                    waiter = continuation
                    lock.unlock()
                case .requested:
                    lock.unlock()
                    continuation.resume()
                case .ended:
                    lock.unlock()
                    continuation.resume(throwing: ReadinessError.consumerEnded)
                }
            }
            try Task.checkCancellation()
            try validateRequested()
        } onCancel: {
            self.end()
        }
    }
}




/// Private forwarding ownership. The actual registered service remains the
/// implementation and no account/Space/source identity is accepted as authority.
private enum OriginalEditorAuthCallContext {
    @TaskLocal static var caller: OriginalEditorAuthCaller?
    @TaskLocal static var closing: OriginalEditorAuthCaller?
}

enum OriginalEditorAuthCloseReceipt: Sendable {
    case neverStartedDrained
    case nativeStopCompleted
}

private final class OriginalEditorAuthCallerState: @unchecked Sendable {
    private let lock = NSLock()
    let lifetime: EditorDocumentWriteLifetime
    let capture: EditorDocumentWriteCapture
    private var retired = false
    private var startupAdmitted = false
    private var stopRequired = false
    private var stopCompleted = false

    init() throws {
        let lifetime = EditorDocumentWriteLifetime()
        self.lifetime = lifetime
        capture = try EditorDocumentWriteCapture(lifetime)
    }

    func validate() throws {
        try Task.checkCancellation()
        lock.lock()
        let retired = retired
        lock.unlock()
        guard !retired else { throw HanlinHostError.staleContext }
        try capture.validate()
    }

    func retire() {
        lock.lock()
        retired = true
        lock.unlock()
        lifetime.markUnavailable()
    }

    /// Retirement and original wrapper admission are one synchronous boundary.
    /// This says nothing about the later Go beginStart registration.
    func makeAttempt(kind: OriginalAuthAttempt.Kind) throws -> OriginalAuthAttempt {
        lock.lock()
        defer { lock.unlock() }
        guard !retired else { throw HanlinHostError.staleContext }
        let attempt = try OriginalAuthAttempt(kind: kind, restricting: [capture])
        if kind == .startup {
            startupAdmitted = true
            stopRequired = true
            stopCompleted = false
        }
        return attempt
    }

    func admitForwarding() throws -> [EditorDocumentWriteLifetime.Observation] {
        lock.lock()
        defer { lock.unlock() }
        guard !retired else { throw HanlinHostError.staleContext }
        try Task.checkCancellation()
        return try EditorDocumentWriteCapture.acquireAll([capture])
    }

    var requiresNativeStop: Bool {
        lock.lock()
        defer { lock.unlock() }
        return stopRequired
    }

    func recordCompletedNativeStop() {
        lock.lock()
        stopRequired = false
        stopCompleted = true
        lock.unlock()
    }

    func drainedReceipt() throws -> OriginalEditorAuthCloseReceipt {
        lock.lock()
        defer { lock.unlock() }
        guard retired, !stopRequired else { throw HanlinHostError.staleContext }
        if startupAdmitted {
            guard stopCompleted else { throw HanlinHostError.staleContext }
            return .nativeStopCompleted
        }
        return stopCompleted ? .nativeStopCompleted : .neverStartedDrained
    }
}

/// Immutable per-presentation caller; its initializer and registered actor are
/// file-private. Escaped original callbacks retain this object explicitly.
final class OriginalEditorAuthCaller: AuthServiceProtocol, Sendable {
    fileprivate let service: PinkhaHanlinAuthService
    fileprivate let state: OriginalEditorAuthCallerState

    fileprivate init(service: PinkhaHanlinAuthService) throws {
        self.service = service
        state = try OriginalEditorAuthCallerState()
    }

    func validateCurrent() throws { try state.validate() }
    func retire() { state.retire() }

    /// Read-only retirement observation for an actual original UI consumer.
    /// It exposes neither the capture nor a new authority constructor.
    func observeRetirement(
        _ invalidated: @escaping @Sendable () -> Void
    ) -> EditorDocumentWriteLifetime.Observation {
        state.lifetime.observe(state.capture.token, invalidated: invalidated)
    }

    var isCurrent: Bool {
        do { try validateCurrent(); return true }
        catch { return false }
    }

    func closeAuthentication() async throws -> OriginalEditorAuthCloseReceipt {
        try await service.closeOriginalEditorCaller(self, retry: false)
    }

    func retryCloseAuthentication() async throws -> OriginalEditorAuthCloseReceipt {
        try await service.closeOriginalEditorCaller(self, retry: true)
    }

    func releaseAfterRuntimeDrain() async throws {
        try await service.releaseOriginalEditorCaller(self)
    }

    private func forward<Value: Sendable>(
        _ operation: @Sendable (PinkhaHanlinAuthService) async throws -> Value
    ) async throws -> Value {
        try validateCurrent()
        if let existing = OriginalEditorAuthCallContext.caller, existing !== self {
            throw HanlinHostError.staleContext
        }
        let admissions = try state.admitForwarding()
        defer { for admission in admissions { admission.cancel() } }
        return try await OriginalEditorAuthCallContext.$caller.withValue(self) {
            try await operation(service)
        }
    }

    func createWallet() async throws -> String {
        try await forward { try await $0.createWallet() }
    }

    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        try await forward { try await $0.createAccount(name: name, iconOption: iconOption, imagePath: imagePath) }
    }

    func walletRecovery(mnemonic: String) async throws {
        try await forward { try await $0.walletRecovery(mnemonic: mnemonic) }
    }

    func accountRecover() async throws {
        try await forward { try await $0.accountRecover() }
    }

    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        try await forward { try await $0.selectAccount(id: id, preferredSpaceId: preferredSpaceId) }
    }

    func mnemonicByEntropy(_ entropy: String) async throws -> String {
        try await forward { try await $0.mnemonicByEntropy(entropy) }
    }

    func logout(removeData: Bool) async throws {
        try await forward { try await $0.logout(removeData: removeData) }
    }

    func deleteAccount() async throws -> AccountStatus {
        try await forward { try await $0.deleteAccount() }
    }

    func restoreAccount() async throws -> AccountStatus {
        try await forward { try await $0.restoreAccount() }
    }

    /// Hold the original lifetime across the complete UI operation, including
    /// its Seed/default-space/state continuation after an Auth service returns.
    /// Preserve the preexisting Auth parent; the temporary view task must not
    /// become a new ancestor of a successful original LoginState startup source.
    @MainActor
    func withUIOperation(_ operation: @MainActor () async throws -> Void) async throws {
        let attempt = try state.makeAttempt(kind: .ordinary)
        let admissions = try attempt.admitStage()
        try await withTaskCancellationHandler {
            do {
                try await OriginalEditorAuthCallContext.$caller.withValue(self) {
                    try await operation()
                }
                try attempt.validate()
                for admission in admissions { admission.cancel() }
                attempt.finishOuter()
            } catch {
                attempt.retire()
                for admission in admissions { admission.cancel() }
                attempt.finishOuter()
                await attempt.waitForDrain()
                throw error
            }
        } onCancel: { attempt.retire() }
    }

    @MainActor
    func withUIAction(_ operation: @MainActor () throws -> Void) throws {
        let attempt = try state.makeAttempt(kind: .ordinary)
        let admissions = try attempt.admitStage()
        defer {
            for admission in admissions { admission.cancel() }
            attempt.finishOuter()
        }
        try operation()
        try attempt.validate()
    }

    @MainActor
    static func withUIOperation(
        _ caller: OriginalEditorAuthCaller?,
        _ operation: @MainActor () async throws -> Void
    ) async throws {
        if let caller { try await caller.withUIOperation(operation) }
        else { try await operation() }
    }

    @MainActor
    static func withUIAction(
        _ caller: OriginalEditorAuthCaller?,
        _ operation: @MainActor () throws -> Void
    ) throws {
        if let caller { try caller.withUIAction(operation) }
        else { try operation() }
    }

    /// The four auxiliary original services invoke outside AuthService. Their
    /// actual named native return owns the lease, even after early await cancel.
    /// A preexisting unrelated binding is rejected, never silently replaced.
    @MainActor
    func withNamedNativeRPC<Value: Sendable>(
        _ rpcName: String,
        _ operation: @MainActor () async throws -> Value
    ) async throws -> Value {
        guard InvocationDispatchContext.binding == nil else { throw HanlinHostError.staleContext }
        let attempt = try state.makeAttempt(kind: .ordinary)
        let admissions = try attempt.admitStage()
        return try await withTaskCancellationHandler {
            do {
                let value = try await InvocationDispatchContext.$binding.withValue(
                    Self.namedBinding(attempt, names: [rpcName])
                ) { try await operation() }
                try attempt.validate()
                for admission in admissions { admission.cancel() }
                attempt.finishOuter()
                // Invocation resumes its Swift await before its native completion
                // releases these exact leases. Join the real release as well.
                await attempt.waitForDrain()
                try attempt.validate()
                return value
            } catch {
                attempt.retire()
                for admission in admissions { admission.cancel() }
                attempt.finishOuter()
                await attempt.waitForDrain()
                throw error
            }
        } onCancel: { attempt.retire() }
    }

    fileprivate static func namedBinding(
        _ attempt: OriginalAuthAttempt, names: Set<String>
    ) -> InvocationDispatchBinding {
        InvocationDispatchBinding(committedEvents: { nil }) { name in
            guard names.contains(name) else { throw HanlinHostError.staleContext }
            try attempt.validate()
            return InvocationDispatchPermit {
                try attempt.validate()
                let admissions = try EditorDocumentWriteCapture.acquireAll(attempt.captures)
                return InvocationDispatchCompletion {
                    for admission in admissions { admission.cancel() }
                }
            }
        }
    }
}


/// Native Auth remains the account owner. These exact attempts only restrict
/// the existing Hanlin shutdown/resume calls and admit original Back cancellation.
actor PinkhaHanlinAuthService: AuthServiceProtocol {
    private let base: any AuthServiceProtocol
    private let accounts = Container.shared.accountManager()
    private var bootstrap: any PinkhaSpaceBootstrapServiceProtocol { Container.shared.pinkhaBootstrapService() }
    private var current: OriginalAuthAttempt?
    private var stopping: OriginalAuthAttempt?
    private var successfulStopRequired = false
    private var originalEditorCaller: OriginalEditorAuthCaller?
    private var originalEditorCloseTask: Task<OriginalEditorAuthCloseReceipt, Error>?
    private var originalEditorCloseResult: OriginalEditorAuthCloseReceipt?
    private var originalEditorCloseFailed = false
    private var originalEditorStopTask: Task<Void, Error>?

    init(base: any AuthServiceProtocol) { self.base = base }

    /// All throwing work precedes owner installation; no await or validation
    /// after assignment can strand a caller not returned to the presentation.
    func makeOriginalEditorCaller() throws -> OriginalEditorAuthCaller {
        guard OriginalRuntimeEnvironment.deploymentMode == .embeddedEditor,
              originalEditorCaller == nil, current == nil, stopping == nil,
              !successfulStopRequired, InvocationDispatchContext.binding == nil else {
            throw HanlinHostError.staleContext
        }
        let caller = try OriginalEditorAuthCaller(service: self)
        originalEditorCaller = caller
        return caller
    }

    private func originalEditorAdmissionCaller(allowHistoricalClose: Bool = false) throws -> OriginalEditorAuthCaller? {
        guard OriginalRuntimeEnvironment.deploymentMode == .embeddedEditor else { return nil }
        guard let caller = originalEditorCaller,
              OriginalEditorAuthCallContext.caller === caller else {
            throw HanlinHostError.staleContext
        }
        if allowHistoricalClose, OriginalEditorAuthCallContext.closing === caller,
           originalEditorCloseTask != nil {
            return caller
        }
        try caller.validateCurrent()
        return caller
    }

    fileprivate func closeOriginalEditorCaller(
        _ caller: OriginalEditorAuthCaller, retry: Bool
    ) async throws -> OriginalEditorAuthCloseReceipt {
        guard originalEditorCaller === caller else { throw HanlinHostError.staleContext }
        if retry {
            guard originalEditorCloseFailed, let previousClose = originalEditorCloseTask else {
                throw HanlinHostError.staleContext
            }
            originalEditorCloseFailed = false
            _ = await previousClose.result
            guard originalEditorCaller === caller, originalEditorCloseResult == nil else {
                throw HanlinHostError.staleContext
            }
            originalEditorCloseTask = nil
        }
        if let existing = originalEditorCloseTask { return try await existing.value }
        caller.retire()
        let previous = current
        let cleanup = Task { [self] in
            do {
                if let alreadyStopping = originalEditorStopTask {
                    // The same historical Stop already owns the native call.
                    // Its result includes actual Stop drain, not UI await cancel.
                    try await alreadyStopping.value
                } else if caller.state.requiresNativeStop || successfulStopRequired {
                    guard InvocationDispatchContext.binding == nil else { throw HanlinHostError.staleContext }
                    // Historical cancellation does not need renewed current-write
                    // authority from the retired UI parent.
                    try await OriginalAuthRequestContext.$parent.withValue(nil) {
                        try await OriginalEditorAuthCallContext.$caller.withValue(caller) {
                            try await OriginalEditorAuthCallContext.$closing.withValue(caller) {
                                try await logout(removeData: false)
                            }
                        }
                    }
                }
                // A failed Stop exits above: do not join a possibly blocked
                // native startup or declare stopped after ACCOUNT_IS_NOT_RUNNING.
                await previous?.waitForDrain()
                await caller.state.lifetime.waitForOperationsToDrain()
                guard originalEditorCaller === caller, current == nil,
                      stopping == nil, !successfulStopRequired else {
                    throw HanlinHostError.staleContext
                }
                let receipt = try caller.state.drainedReceipt()
                originalEditorCloseResult = receipt
                return receipt
            } catch {
                originalEditorCloseFailed = true
                throw error
            }
        }
        originalEditorCloseTask = cleanup
        return try await cleanup.value
    }

    /// Called only by the original process owner after its additional FIFO,
    /// selected-operation and consumer-task joins. This method grants none of
    /// those facts and cannot release a failed or pending authentication close.
    fileprivate func releaseOriginalEditorCaller(_ caller: OriginalEditorAuthCaller) async throws {
        guard originalEditorCaller === caller, originalEditorCloseResult != nil,
              !originalEditorCloseFailed, !successfulStopRequired else {
            throw HanlinHostError.staleContext
        }
        await caller.state.lifetime.waitForOperationsToDrain()
        guard originalEditorCaller === caller, originalEditorCloseResult != nil,
              current == nil, stopping == nil, !successfulStopRequired else {
            throw HanlinHostError.staleContext
        }
        originalEditorCaller = nil
        originalEditorCloseTask = nil
        originalEditorCloseResult = nil
        originalEditorCloseFailed = false
        originalEditorStopTask = nil
    }



    func createWallet() async throws -> String {
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.createWallet() }
        }
    }

    func walletRecovery(mnemonic: String) async throws {
        let base = base
        try await perform(kind: .ordinary) { attempt in
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.walletRecovery(mnemonic: mnemonic) }
        }
    }

    func accountRecover() async throws {
        let base = base
        try await perform(kind: .ordinary) { attempt in
            try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.accountRecover() }
        }
    }

    func mnemonicByEntropy(_ entropy: String) async throws -> String {
        guard OriginalRuntimeEnvironment.deploymentMode == .embeddedEditor else {
            return try await base.mnemonicByEntropy(entropy)
        }
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            guard InvocationDispatchContext.binding == nil else { throw HanlinHostError.staleContext }
            return try await OriginalAuthRequestContext.$parent.withValue(attempt) {
                try await InvocationDispatchContext.$binding.withValue(
                    OriginalEditorAuthCaller.namedBinding(attempt, names: ["WalletConvert"])
                ) { try await base.mnemonicByEntropy(entropy) }
            }
        }
    }

    func createAccount(name: String, iconOption: Int, imagePath: String) async throws -> AccountData {
        let base = base
        let bootstrap = bootstrap
        let previousAccount = accounts.account.id
        return try await perform(kind: .startup) { attempt in
            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.closeAccount(previousAccount, removeData: false)
            }
            try await self.stage(attempt) { await bootstrap.quiesceAccountOperations() }
            let account = try await self.stage(attempt) {
                try await OriginalAuthRequestContext.$parent.withValue(attempt) {
                    try await base.createAccount(name: name, iconOption: iconOption, imagePath: imagePath)
                }
            }
            try await self.stage(attempt) { try await bootstrap.resumeAccountOperations() }
            try await self.stage(attempt) {
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account.id)
                }
            }
            return account
        }
    }

    func selectAccount(id: String, preferredSpaceId: String) async throws -> AccountData {
        let base = base
        let bootstrap = bootstrap
        let previousAccount = accounts.account.id
        return try await perform(kind: .startup) { attempt in
            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.closeAccount(previousAccount, removeData: false)
            }
            try await self.stage(attempt) { await bootstrap.quiesceAccountOperations() }
            let account = try await self.stage(attempt) {
                try await OriginalAuthRequestContext.$parent.withValue(attempt) {
                    try await base.selectAccount(id: id, preferredSpaceId: preferredSpaceId)
                }
            }
            try await self.stage(attempt) { try await bootstrap.resumeAccountOperations() }
            try await self.stage(attempt) {
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account.id)
                }
            }
            return account
        }
    }

    func logout(removeData: Bool) async throws {
        guard stopping == nil else { throw HanlinHostError.staleContext }
        let originalCaller = try originalEditorAdmissionCaller(allowHistoricalClose: true)
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
                if let originalCaller {
                    await stop.waitForDrain()
                    originalCaller.state.recordCompletedNativeStop()
                    originalEditorStopTask = nil
                }
                if stopping === stop { stopping = nil }
            } catch {
                stop.retire()
                // Do not join a native startup after Stop failed: another Stop
                // must remain admissible to release that retired operation.
                successfulStopRequired = true
                stop.finishOuter()
                if originalCaller != nil {
                    await stop.waitForDrain()
                    originalEditorStopTask = nil
                }
                if stopping === stop { stopping = nil }
                throw error
            }
        }
        if originalCaller != nil { originalEditorStopTask = cleanup }
        try await cleanup.value
        try Task.checkCancellation()
    }

    func deleteAccount() async throws -> AccountStatus {
        let base = base
        let account = accounts.account.id
        return try await perform(kind: .ordinary) { attempt in
            try await self.stage(attempt) {
                try await PinkhaHanlinAccountOwner.shared.closeAccount(account, removeData: false)
            }
            return try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.deleteAccount() }
        }
    }

    func restoreAccount() async throws -> AccountStatus {
        let base = base
        return try await perform(kind: .ordinary) { attempt in
            let status = try await OriginalAuthRequestContext.$parent.withValue(attempt) { try await base.restoreAccount() }
            let account = self.accounts.account.id
            try await self.stage(attempt) {
                try await MainActor.run {
                    try attempt.validate()
                    try PinkhaHanlinAccountOwner.shared.accountDidOpen(account)
                }
            }
            return status
        }
    }

    private func stage<Value: Sendable>(
        _ attempt: OriginalAuthAttempt,
        operation: @escaping @Sendable () async throws -> Value
    ) async throws -> Value {
        try requireCurrent(attempt)
        let admissions = try attempt.admitStage()
        defer { for admission in admissions { admission.cancel() } }
        let result = try await operation()
        try requireCurrent(attempt)
        return result
    }

    private func perform<Value: Sendable>(
        kind: OriginalAuthAttempt.Kind,
        operation: @escaping @Sendable (OriginalAuthAttempt) async throws -> Value
    ) async throws -> Value {
        guard current == nil, stopping == nil, !successfulStopRequired else { throw HanlinHostError.staleContext }
        let attempt: OriginalAuthAttempt
        if let caller = try originalEditorAdmissionCaller() {
            attempt = try caller.state.makeAttempt(kind: kind)
        } else {
            attempt = try OriginalAuthAttempt(kind: kind)
        }
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

    private func requireCurrent(_ attempt: OriginalAuthAttempt) throws {
        guard current === attempt, stopping == nil else { throw HanlinHostError.staleContext }
        try attempt.validate()
    }
}
