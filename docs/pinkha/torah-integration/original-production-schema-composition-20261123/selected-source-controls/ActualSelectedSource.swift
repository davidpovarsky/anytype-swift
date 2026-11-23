import Foundation

// Dependency fixtures for this source-bound portable probe only.
// No account bootstrap, subscription transport, UIKit, native RPC or database is implemented.
struct AccountData: Sendable { let id: String }
struct AccountInfo: Sendable { let accountSpaceId: String; let spaceViewId: String }
struct SpaceView: Sendable {
    let id: String; let targetSpaceId: String
    let accountStatus = 1; let localStatus = 1; let spaceAccessType = 1
    let spaceType = 1; let isLegacyStream = false
}
protocol AccountManagerProtocol: AnyObject, Sendable {
    var account: AccountData { get }
    var editorWriteLifetime: EditorDocumentWriteLifetime? { get }
}
final class AccountManager: AccountManagerProtocol, Sendable {
    let account = AccountData(id: "same-account-data")
    let editorWriteLifetime: EditorDocumentWriteLifetime?
    init(_ lifetime: EditorDocumentWriteLifetime) { editorWriteLifetime = lifetime }
}
protocol SpaceViewsStorageProtocol: AnyObject, Sendable {}
final class SpaceViewsStorage: SpaceViewsStorageProtocol, Sendable {
    let permission: OriginalSpaceViewPermission
    init(_ permission: OriginalSpaceViewPermission) { self.permission = permission }
    func currentOriginalSpaceViewPermission(spaceId: String) throws -> OriginalSpaceViewPermission {
        precondition(spaceId == permission.originalSpaceView.targetSpaceId)
        return permission
    }
}
struct OriginalChannelPinPermission {
    func capture(matching account: EditorDocumentWriteCapture, spaceId: String) throws -> EditorDocumentWriteCapture {
        fatalError("Unused dependency fixture: channel permission was invoked")
    }
}
struct OriginalParticipantEditPermission {
    var originalParticipant: Int { fatalError("Unused participant dependency") }
    func capture(matching account: EditorDocumentWriteCapture, spaceId: String) throws -> EditorDocumentWriteCapture {
        fatalError("Unused dependency fixture: participant permission was invoked")
    }
}
struct SpacePermissions {
    let canEdit: Bool
    init(spaceView: SpaceView, participant: Int, isLocalMode: Bool) {
        fatalError("Unused dependency fixture: SpacePermissions was invoked")
    }
}
enum FixtureNetworkMode { case localOnly }
struct FixtureConfiguration { let middlewareNetworkMode = FixtureNetworkMode.localOnly }
struct FixtureConfigurationStorage { func currentConfiguration() -> FixtureConfiguration { .init() } }
struct Container: Sendable {
    static let shared = Container()
    func serverConfigurationStorage() -> FixtureConfigurationStorage { .init() }
}
@MainActor final class EditorDocumentWriteOwner {
    fileprivate func beginTrackedWork(access: EditorDocumentOperationAccess) throws -> EditorDocumentParentWork {
        .init(owner: self, lease: UUID(), lineage: .current)
    }
    fileprivate func finishTrackedWork(_ lease: UUID, failed: Bool) {}
}
@MainActor final class FixtureCurrentness { var value = true }

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

/// This task-local value only identifies pending operations in their original
/// owners. It cannot create a lease or bypass their captured lifetime checks.
fileprivate enum EditorDocumentOperationAccess: Sendable {
    case mutation
    case read(Set<String>)

    var isMutation: Bool {
        if case .mutation = self { return true }
        return false
    }

    func permits(_ requested: Self) -> Bool {
        switch (self, requested) {
        case (.mutation, _): return true
        case let (.read(allowed), .read(requested)): return requested.isSubset(of: allowed)
        default: return false
        }
    }
}

fileprivate struct EditorDocumentOperationLineage: Sendable {
    var leases: [ObjectIdentifier: UUID] = [:]
    var dispatchIdentity: UUID?

    static var current: Self {
        let value = EditorDocumentOperationContext.lineage
        // Committed native events deliberately carry only their frozen account
        // binding. They must not inherit an expiring document operation lease.
        guard value.dispatchIdentity == InvocationDispatchContext.binding?.contextIdentity else { return .init() }
        return value
    }

    func dispatching(_ binding: InvocationDispatchBinding) -> Self {
        var copy = self
        copy.dispatchIdentity = binding.contextIdentity
        return copy
    }
}

fileprivate func intersectOriginalRPCRestrictions(_ lhs: Set<String>?, _ rhs: Set<String>?) -> Set<String>? {
    if let lhs, let rhs { return lhs.intersection(rhs) }
    return lhs ?? rhs
}

fileprivate enum EditorDocumentOperationContext {
    @TaskLocal static var lineage = EditorDocumentOperationLineage()
}

/// A child registers work in the same parent owner's existing pending registry.
/// This passive lease cannot dispatch an RPC against the parent document.
@MainActor
fileprivate struct EditorDocumentParentWork {
    let owner: EditorDocumentWriteOwner
    let lease: UUID
    let lineage: EditorDocumentOperationLineage

    func finish(failed: Bool) { owner.finishTrackedWork(lease, failed: failed) }
}

@MainActor
struct EditorDocumentWriteSourceBinding {
    let lifetime: EditorDocumentWriteLifetime
    let captures: [EditorDocumentWriteCapture]
    private let accountCapture: EditorDocumentWriteCapture?
    fileprivate let parentOwner: EditorDocumentWriteOwner?
    fileprivate let rpcRestriction: Set<String>?
    let isCurrent: @MainActor () -> Bool

    init(
        lifetime: EditorDocumentWriteLifetime,
        accountLifetime: EditorDocumentWriteLifetime? = nil,
        additionalLifetimes: [EditorDocumentWriteLifetime] = [],
        isCurrent: @escaping @MainActor () -> Bool
    ) throws {
        self.lifetime = lifetime
        let accountCapture = try accountLifetime.map(EditorDocumentWriteCapture.init)
        self.accountCapture = accountCapture
        self.captures = try ([lifetime] + additionalLifetimes).map(EditorDocumentWriteCapture.init)
            + (accountCapture.map { [$0] } ?? [])
        self.isCurrent = isCurrent
        parentOwner = nil
        rpcRestriction = nil
    }

    private init(
        inheriting original: Self,
        parentOwner: EditorDocumentWriteOwner,
        captures: [EditorDocumentWriteCapture],
        rpcRestriction: Set<String>?,
        isCurrent: @escaping @MainActor () -> Bool
    ) {
        lifetime = original.lifetime
        accountCapture = original.accountCapture
        self.parentOwner = parentOwner
        self.captures = captures
        self.rpcRestriction = intersectOriginalRPCRestrictions(original.rpcRestriction, rpcRestriction)
        self.isCurrent = isCurrent
    }

    fileprivate func inheritingParent(
        owner: EditorDocumentWriteOwner,
        captures: [EditorDocumentWriteCapture],
        rpcRestriction: Set<String>? = nil,
        isCurrent: @escaping @MainActor () -> Bool
    ) -> Self {
        Self(inheriting: self, parentOwner: owner, captures: captures,
             rpcRestriction: rpcRestriction, isCurrent: isCurrent)
    }

    fileprivate func channelPinCapture(
        _ permission: OriginalChannelPinPermission, spaceId: String
    ) throws -> EditorDocumentWriteCapture {
        try validate()
        guard let accountCapture else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        return try permission.capture(matching: accountCapture, spaceId: spaceId)
    }

    private init(restricting original: Self, additionalCaptures: [EditorDocumentWriteCapture]) {
        lifetime = original.lifetime
        captures = original.captures + additionalCaptures
        accountCapture = original.accountCapture
        parentOwner = original.parentOwner
        rpcRestriction = original.rpcRestriction
        isCurrent = original.isCurrent
    }

    /// Narrow the same host/account source to the original selected attempt.
    /// Equal Space IDs or a later account generation cannot replace its capture.
    func requiringOriginalSelectedSpace(_ selection: OriginalActiveSpaceSelection) throws -> Self {
        try validate()
        guard let accountCapture else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        let selectedCapture = try selection.capture(
            matching: accountCapture, spaceId: selection.accountInfo.accountSpaceId
        )
        let restricted = Self(restricting: self, additionalCaptures: [selectedCapture])
        try restricted.validate()
        return restricted
    }

    func requiringSpaceEditPermission(
        participant: OriginalParticipantEditPermission,
        spaceView: OriginalSpaceViewPermission,
        spaceId: String
    ) throws -> Self {
        try validate()
        guard let accountCapture else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        let participantCapture = try participant.capture(matching: accountCapture, spaceId: spaceId)
        let viewCapture = try spaceView.capture(matching: accountCapture, spaceId: spaceId)
        let permissions = SpacePermissions(
            spaceView: spaceView.originalSpaceView,
            participant: participant.originalParticipant,
            isLocalMode: Container.shared.serverConfigurationStorage().currentConfiguration().middlewareNetworkMode == .localOnly
        )
        guard permissions.canEdit else {
            throw EditorDocumentWriteError.rejected(.notEditable)
        }
        let restricted = Self(
            restricting: self, additionalCaptures: [participantCapture, viewCapture]
        )
        try restricted.validate()
        return restricted
    }

    var committedEventBinding: InvocationDispatchBinding? {
        accountCapture?.accountDispatchBinding()
    }

    func validate() throws {
        if Task.isCancelled { throw EditorDocumentWriteError.rejected(.cancelled) }
        for capture in captures { try capture.validate() }
        guard isCurrent() else {
            lifetime.markUnavailable()
            throw EditorDocumentWriteError.rejected(.documentChanged)
        }
    }

    /// Opening uses exactly the source/account generations the eventual owner
    /// receives. Parent capture also waits for this original open to drain.
    func performRead<Value: Sendable>(
        rpcNames: Set<String>,
        onDrained: (@MainActor @Sendable () -> Void)? = nil,
        operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        try await performOperation(access: .read(rpcNames), rpcNames: rpcNames,
                                   onDrained: onDrained, operation: operation)
    }

    /// The same fence supports explicitly owned qualification operations. An
    /// import or creation is intentionally not described as a read.
    func performOperation<Value: Sendable>(
        rpcNames: Set<String>,
        onDrained: (@MainActor @Sendable () -> Void)? = nil,
        operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        try await performOperation(access: .mutation, rpcNames: rpcNames,
                                   onDrained: onDrained, operation: operation)
    }

    private func performOperation<Value: Sendable>(
        access: EditorDocumentOperationAccess,
        rpcNames: Set<String>,
        onDrained: (@MainActor @Sendable () -> Void)?,
        operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        try validate()
        let parentWork = try parentOwner?.beginTrackedWork(access: access)
        let lease = EditorDocumentWriteOperation { failed in
            Task { @MainActor in
                parentWork?.finish(failed: failed)
                onDrained?()
            }
        }
        defer {
            if lease.finishOuter() {
                parentWork?.finish(failed: lease.hasFailed)
                onDrained?()
            }
        }
        let events = committedEventBinding.map { value -> (@Sendable () -> InvocationDispatchBinding?) in { value } }
        let binding = InvocationDispatchBinding(committedEvents: events) { messageName in
            try await self.prepareDispatch(messageName: messageName, rpcNames: rpcNames, lease: lease)
        }
        let lineage = (parentWork?.lineage ?? .current).dispatching(binding)
        do {
            let value = try await EditorDocumentOperationContext.$lineage.withValue(lineage) {
                try await InvocationDispatchContext.$binding.withValue(binding, operation: operation)
            }
            try validate()
            return value
        } catch {
            lease.markFailed()
            throw error
        }
    }

    private func prepareDispatch(
        messageName: String,
        rpcNames: Set<String>,
        lease: EditorDocumentWriteOperation
    ) throws -> InvocationDispatchPermit {
        do {
            try validate()
            guard lease.isAccepting, rpcNames.contains(messageName),
                  rpcRestriction?.contains(messageName) != false else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
            let captured = captures
            return lease.permit { try EditorDocumentWriteCapture.acquireAll(captured) }
        } catch {
            lease.markFailed()
            throw error
        }
    }
}


struct OriginalActiveSpaceSelection: Sendable {
    let accountID: String
    let accountInfo: AccountInfo

    private let attempt: OriginalActiveSpaceSelectionAttempt

    fileprivate init(attempt: OriginalActiveSpaceSelectionAttempt, info: AccountInfo) throws {
        try attempt.validateReturnedInfo(info)
        guard let accountID = attempt.accountID, attempt.spaceViewCapture != nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        self.accountID = accountID
        accountInfo = info
        self.attempt = attempt
        try validate()
    }

    func validate() throws {
        try attempt.validate()
        try attempt.validateReturnedInfo(accountInfo)
    }

    func capture(
        matching account: EditorDocumentWriteCapture, spaceId: String
    ) throws -> EditorDocumentWriteCapture {
        guard let original = attempt.accountCapture,
              original.source === account.source,
              original.token == account.token,
              accountInfo.accountSpaceId.utf8.elementsEqual(spaceId.utf8) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        try account.validate()
        try validate()
        return attempt.capture
    }
}

fileprivate final class OriginalActiveSpaceSelectionAttempt: Sendable {
    let requestedSpaceID: String?
    let accountID: String?
    let accountCapture: EditorDocumentWriteCapture?
    let capture: EditorDocumentWriteCapture
    let spaceViewCapture: EditorDocumentWriteCapture?

    private let spaceView: OriginalSpaceViewPermission?
    private let accountRetirement: EditorDocumentWriteLifetime.Observation?
    private let viewRetirement: EditorDocumentWriteLifetime.Observation?

    init(
        spaceId: String?,
        accountManager: any AccountManagerProtocol,
        workspaceStorage: any SpaceViewsStorageProtocol
    ) throws {
        let lifetime = EditorDocumentWriteLifetime()
        requestedSpaceID = spaceId
        capture = try EditorDocumentWriteCapture(lifetime)
        if let spaceId {
            guard !spaceId.isEmpty,
                  accountManager is AccountManager,
                  let accountLifetime = accountManager.editorWriteLifetime else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
            let capturedAccount = try EditorDocumentWriteCapture(accountLifetime)
            let account = accountManager.account
            try capturedAccount.validate()
            guard !account.id.isEmpty else {
                throw EditorDocumentWriteError.rejected(.wrongContext)
            }
            accountID = account.id
            accountCapture = capturedAccount

            let view = (workspaceStorage as? SpaceViewsStorage).flatMap {
                try? $0.currentOriginalSpaceViewPermission(spaceId: spaceId)
            }
            let capturedView = try view?.capture(matching: capturedAccount, spaceId: spaceId)
            spaceView = view
            spaceViewCapture = capturedView
            accountRetirement = capturedAccount.source.observe(capturedAccount.token) {
                lifetime.markUnavailable()
            }
            viewRetirement = capturedView.map { value in
                value.source.observe(value.token) { lifetime.markUnavailable() }
            }
        } else {
            accountID = nil
            accountCapture = nil
            spaceView = nil
            spaceViewCapture = nil
            accountRetirement = nil
            viewRetirement = nil
        }
        try validate()
    }

    func validate() throws {
        try Task.checkCancellation()
        try capture.validate()
        try accountCapture?.validate()
        try spaceViewCapture?.validate()
    }

    func validateReturnedInfo(_ info: AccountInfo) throws {
        try validate()
        guard let requestedSpaceID,
              info.accountSpaceId.utf8.elementsEqual(requestedSpaceID.utf8),
              !info.spaceViewId.isEmpty else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        if let spaceView {
            guard spaceView.originalSpaceView.targetSpaceId.utf8.elementsEqual(requestedSpaceID.utf8),
                  spaceView.originalSpaceView.id.utf8.elementsEqual(info.spaceViewId.utf8) else {
                throw EditorDocumentWriteError.rejected(.wrongContext)
            }
            try spaceView.validate()
        }
    }

    @MainActor
    func workspaceBinding() throws -> EditorDocumentWriteSourceBinding {
        try validate()
        guard let accountCapture, requestedSpaceID != nil else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        let additional = spaceViewCapture.map { [$0.source] } ?? []
        let binding = try EditorDocumentWriteSourceBinding(
            lifetime: capture.source,
            accountLifetime: accountCapture.source,
            additionalLifetimes: additional,
            isCurrent: { (try? self.validate()) != nil }
        )
        let expected = [capture] + (spaceViewCapture.map { [$0] } ?? []) + [accountCapture]
        guard binding.captures.count == expected.count,
              zip(binding.captures, expected).allSatisfy({ pair in
                  pair.0.source === pair.1.source && pair.0.token == pair.1.token
              }) else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        try validate()
        try binding.validate()
        return binding
    }

    func retire() {
        capture.source.markUnavailable()
        accountRetirement?.cancel()
        viewRetirement?.cancel()
    }

    deinit {
        retire()
    }
}


struct OriginalSpaceViewPermission: Sendable {
    fileprivate let accountID: String
    fileprivate let techSpaceID: String
    fileprivate var spaceView: SpaceView
    fileprivate let accountCapture: EditorDocumentWriteCapture
    fileprivate let viewCapture: EditorDocumentWriteCapture
    private let subscriptionCapture: EditorDocumentWriteCapture
    private let subscriptionRetirement: EditorDocumentWriteLifetime.Observation
    private let accountRetirement: EditorDocumentWriteLifetime.Observation

    fileprivate init(
        accountID: String, techSpaceID: String, spaceView: SpaceView,
        accountCapture: EditorDocumentWriteCapture,
        subscriptionCapture: EditorDocumentWriteCapture
    ) throws {
        self.accountID = accountID
        self.techSpaceID = techSpaceID
        self.spaceView = spaceView
        self.accountCapture = accountCapture
        self.subscriptionCapture = subscriptionCapture
        let lifetime = EditorDocumentWriteLifetime()
        viewCapture = try EditorDocumentWriteCapture(lifetime)
        // AccountManager retires its original generation before publishing a
        // replacement account. Retire this view synchronously in that callback.
        accountRetirement = accountCapture.source.observe(accountCapture.token) {
            lifetime.markUnavailable()
        }
        subscriptionRetirement = subscriptionCapture.source.observe(subscriptionCapture.token) {
            lifetime.markUnavailable()
        }
        try validate()
    }

    var originalSpaceView: SpaceView { spaceView }

    func validate() throws {
        try accountCapture.validate()
        try subscriptionCapture.validate()
        try viewCapture.validate()
    }

    func capture(
        matching account: EditorDocumentWriteCapture, spaceId: String
    ) throws -> EditorDocumentWriteCapture {
        guard !accountID.isEmpty, !techSpaceID.isEmpty,
              !spaceView.id.isEmpty,
              spaceView.targetSpaceId.utf8.elementsEqual(spaceId.utf8),
              accountCapture.source === account.source,
              accountCapture.token == account.token else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        try account.validate()
        try validate()
        return viewCapture
    }

    fileprivate func retainsAuthority(of value: SpaceView) -> Bool {
        spaceView.id.utf8.elementsEqual(value.id.utf8)
            && spaceView.targetSpaceId.utf8.elementsEqual(value.targetSpaceId.utf8)
            && spaceView.accountStatus == value.accountStatus
            && spaceView.localStatus == value.localStatus
            && spaceView.spaceAccessType == value.spaceAccessType
            && spaceView.spaceType == value.spaceType
            && spaceView.isLegacyStream == value.isLegacyStream
    }

    fileprivate func updatingOriginalValue(_ value: SpaceView) -> Self {
        var copy = self
        copy.spaceView = value
        return copy
    }

    fileprivate func retire() {
        viewCapture.source.markUnavailable()
        accountRetirement.cancel()
        subscriptionRetirement.cancel()
    }
}



@main private struct SelectedSourceControls {
    @MainActor
    static func selection(_ account: EditorDocumentWriteLifetime) throws
        -> (OriginalActiveSpaceSelection, OriginalActiveSpaceSelectionAttempt, EditorDocumentWriteLifetime) {
        let subscription = EditorDocumentWriteLifetime()
        let permission = try OriginalSpaceViewPermission(
            accountID: "same-account-data", techSpaceID: "fixture-tech",
            spaceView: .init(id: "fixture-view", targetSpaceId: "fixture-space"),
            accountCapture: EditorDocumentWriteCapture(account),
            subscriptionCapture: EditorDocumentWriteCapture(subscription)
        )
        let attempt = try OriginalActiveSpaceSelectionAttempt(
            spaceId: "fixture-space", accountManager: AccountManager(account),
            workspaceStorage: SpaceViewsStorage(permission)
        )
        return (try OriginalActiveSpaceSelection(
            attempt: attempt, info: .init(accountSpaceId: "fixture-space", spaceViewId: "fixture-view")
        ), attempt, subscription)
    }

    @MainActor
    static func expect(_ expected: EditorDocumentWriteError, _ body: () throws -> Void) {
        do { try body(); preconditionFailure("Required rejection was absent: \(expected)") }
        catch { precondition(error as? EditorDocumentWriteError == expected, "\(error)") }
    }

    @MainActor static func main() async throws {
        var passed: [String] = []
        do {
            let source = EditorDocumentWriteLifetime(), account = EditorDocumentWriteLifetime()
            let additional = EditorDocumentWriteLifetime(), current = FixtureCurrentness()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: source, accountLifetime: account,
                additionalLifetimes: [additional], isCurrent: { current.value }
            )
            let parent = EditorDocumentWriteOwner()
            let child = original.inheritingParent(
                owner: parent, captures: original.captures,
                rpcRestriction: ["ObjectShow", "ObjectOpen"], isCurrent: { current.value }
            ).inheritingParent(
                owner: parent, captures: original.captures,
                rpcRestriction: ["ObjectShow"], isCurrent: { current.value }
            )
            let (selected, attempt, subscription) = try selection(account)
            let restricted = try child.requiringOriginalSelectedSpace(selected)
            precondition(restricted.lifetime === child.lifetime)
            precondition(restricted.parentOwner === parent && restricted.rpcRestriction == ["ObjectShow"])
            precondition(restricted.captures.count == child.captures.count + 1)
            for (before, after) in zip(child.captures, restricted.captures) {
                precondition(before.source === after.source && before.token == after.token)
            }
            precondition(restricted.captures.last!.source === attempt.capture.source)
            precondition(restricted.captures.last!.token == attempt.capture.token)
            try restricted.validate()
            _ = subscription
            passed.append("preserves original lifetime, all captures, parent identity and intersected RPC restriction")
        }
        do {
            let original = try EditorDocumentWriteSourceBinding(lifetime: .init(), isCurrent: { true })
            let (selected, _, _) = try selection(.init())
            expect(.rejected(.unqualifiedDispatch)) {
                _ = try original.requiringOriginalSelectedSpace(selected)
            }
            passed.append("rejects a source without an original private account capture")
        }
        do {
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: .init(), isCurrent: { true }
            )
            let (selected, _, _) = try selection(.init())
            expect(.rejected(.wrongContext)) {
                _ = try original.requiringOriginalSelectedSpace(selected)
            }
            passed.append("same account and Space data do not replace another original account lifetime")
        }
        do {
            let account = EditorDocumentWriteLifetime()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: account, isCurrent: { true }
            )
            account.markUnavailable(); account.confirmOpened()
            let (selected, _, _) = try selection(account)
            expect(.rejected(.retired)) { _ = try original.requiringOriginalSelectedSpace(selected) }
            passed.append("reopened account generation cannot recapture authority for an older source")
        }
        do {
            let account = EditorDocumentWriteLifetime()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: account, isCurrent: { true }
            )
            let (selected, attempt, _) = try selection(account)
            let restricted = try original.requiringOriginalSelectedSpace(selected)
            var sawRejection = false
            do {
                try await restricted.performOperation(rpcNames: ["ObjectShow"]) {
                    let permit = try await InvocationDispatchContext.binding!.prepare(messageName: "ObjectShow")
                    attempt.retire()
                    attempt.capture.source.confirmOpened()
                    let completion = try permit.begin()
                    completion.finish()
                    preconditionFailure("A retired selected attempt reached admitted work")
                }
            } catch {
                precondition(error as? EditorDocumentWriteError == .rejected(.retired))
                sawRejection = true
            }
            precondition(sawRejection)
            passed.append("selection retirement closes a prepared original permit before begin even after reopening")
        }
        do {
            let account = EditorDocumentWriteLifetime()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: account, isCurrent: { true }
            )
            let (selected, _, subscription) = try selection(account)
            let restricted = try original.requiringOriginalSelectedSpace(selected)
            subscription.markUnavailable(); subscription.confirmOpened()
            expect(.rejected(.retired)) { try restricted.validate() }
            passed.append("actual SpaceView subscription retirement propagates through original selection capture")
        }
        do {
            let account = EditorDocumentWriteLifetime(), current = FixtureCurrentness()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: account, isCurrent: { current.value }
            )
            let (selected, _, _) = try selection(account)
            let restricted = try original.requiringOriginalSelectedSpace(selected)
            current.value = false
            expect(.rejected(.documentChanged)) { try restricted.validate() }
            precondition(original.lifetime.token() == nil)
            passed.append("selection restriction retains host currentness predicate and original lifetime retirement")
        }
        do {
            let account = EditorDocumentWriteLifetime()
            let original = try EditorDocumentWriteSourceBinding(
                lifetime: .init(), accountLifetime: account, isCurrent: { true }
            )
            let parent = EditorDocumentWriteOwner()
            let child = original.inheritingParent(
                owner: parent, captures: original.captures, rpcRestriction: ["ObjectShow"], isCurrent: { true }
            )
            let (selected, _, _) = try selection(account)
            let restricted = try child.requiringOriginalSelectedSpace(selected)
            do {
                try await restricted.performOperation(rpcNames: ["ObjectShow", "ObjectOpen"]) {
                    _ = try await InvocationDispatchContext.binding!.prepare(messageName: "ObjectOpen")
                    preconditionFailure("Inherited RPC restriction was widened")
                }
                preconditionFailure("Forbidden RPC returned successfully")
            } catch { precondition(error as? EditorDocumentWriteError == .rejected(.unqualifiedDispatch)) }
            passed.append("actual source dispatch preserves inherited named RPC restriction")
        }
        let report: [String: Any] = [
            "status": "PORTABLE_SELECTED_SOURCE_BOUNDARY_PASS",
            "executed": passed.count, "passed": passed.count, "controls": passed,
            "native_rpc_calls": 0, "account_bootstrap": "NOT_RUN",
            "actual_parent_writer_runtime": "NOT_RUN_IDENTITY_FIXTURE_ONLY",
            "UIKit": "NOT_RUN", "Apple_native": "NOT_RUN", "device": "NOT_RUN",
            "historical_245_and_38": "NOT_REPLAYED"
        ]
        print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
