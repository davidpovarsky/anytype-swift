import Foundation
import ProtobufMessages

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

/// Additional original document permissions. These requirements never replace
/// the existing handling, unlocked and block-edit admission checks.
enum EditorDocumentWritePermission: Hashable, Sendable {
    case editDetails
    case changeCover
    case changeIcon
    case changeLayout
    case editRelationValues
    case editPropertiesList

    /// Called by the original document before publishing changed permissions.
    /// The same existing lifetime token closes the prepare-to-GCD queue window;
    /// gaining a permission cannot revive any owner invalidated by an earlier loss.
    static func revokesAdmission(from previous: ObjectPermissions, to current: ObjectPermissions) -> Bool {
        (previous.canEditBlocks && !current.canEditBlocks)
            || (previous.canEditDetails && !current.canEditDetails)
            || (previous.canChangeCover && !current.canChangeCover)
            || (previous.canChangeIcon && !current.canChangeIcon)
            || (previous.canChangeLayout && !current.canChangeLayout)
            || (previous.canEditRelationValues && !current.canEditRelationValues)
            || (previous.canEditPropertiesList && !current.canEditPropertiesList)
    }
}

/// A host-owned source is observed by the same document writer owner. Its
/// currentness check must be synchronous, side-effect free and perform no I/O.
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
    }

    private init(
        inheriting original: Self,
        parentOwner: EditorDocumentWriteOwner,
        captures: [EditorDocumentWriteCapture],
        isCurrent: @escaping @MainActor () -> Bool
    ) {
        lifetime = original.lifetime
        accountCapture = original.accountCapture
        self.parentOwner = parentOwner
        self.captures = captures
        self.isCurrent = isCurrent
    }

    fileprivate func inheritingParent(
        owner: EditorDocumentWriteOwner,
        captures: [EditorDocumentWriteCapture],
        isCurrent: @escaping @MainActor () -> Bool
    ) -> Self {
        Self(inheriting: self, parentOwner: owner, captures: captures, isCurrent: isCurrent)
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
            guard lease.isAccepting, rpcNames.contains(messageName) else {
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

/// A UI callback reserves this one-use handle synchronously before creating its
/// Task. Losing an unstarted handle records a failed edit instead of a false drain.
@MainActor
final class EditorDocumentScheduledWrite {
    private let owner: EditorDocumentWriteOwner
    private let lease: UUID
    private var used = false

    fileprivate init(owner: EditorDocumentWriteOwner, lease: UUID) {
        self.owner = owner
        self.lease = lease
    }

    func run<Value: Sendable>(operation: @Sendable () async throws -> Value) async throws -> Value {
        guard !used else { throw EditorDocumentWriteError.rejected(.invalidLease) }
        used = true
        return try await owner.runScheduled(lease, operation: operation)
    }

    deinit {
        let owner = owner, lease = lease
        Task { @MainActor in owner.abandonScheduled(lease) }
    }
}

@MainActor
final class EditorDocumentWriteOwner {
    private let data: EditorPageObject
    private let document: any BaseDocumentProtocol
    private var accepting = true
    private enum Phase { case ordinary, reserved, running }
    private struct Pending {
        let operation: EditorDocumentWriteOperation
        let access: EditorDocumentOperationAccess
        let tracking: Bool
        let writeIntent: Bool
        let contextId: String
        let requiresEditing: Bool
        let requiredPermissions: Set<EditorDocumentWritePermission>
        let lineage: EditorDocumentOperationLineage
        let parentWork: EditorDocumentParentWork?
        let onDrained: (@MainActor @Sendable () -> Void)?
        var phase: Phase
    }
    private var pending: [UUID: Pending] = [:]
    private var capture: UUID?
    private var releaseCaptureWhenDrained: UUID?
    private var failedWrite = false
    private var drainWaiters: [UUID: CheckedContinuation<Void, Error>] = [:]
    private let dispatchLifetime = EditorDocumentWriteLifetime()
    private var onDrained: (@MainActor () -> Void)?
    private struct LifetimeBinding {
        let source: EditorDocumentWriteLifetime
        let token: EditorDocumentWriteLifetime.Token
        let observation: EditorDocumentWriteLifetime.Observation
    }
    private var lifetimeBindings: [LifetimeBinding] = []
    private var documentLifetimeSource: EditorDocumentWriteLifetime?
    private var sourceIsCurrent: (@MainActor () -> Bool)?
    private var sourceEventBinding: InvocationDispatchBinding?
    private var originalSourceBinding: EditorDocumentWriteSourceBinding?

    var isRetired: Bool { !accepting || !lifetimeIsCurrent }
    var pendingOperationCount: Int { pending.count }
    var isDrained: Bool { pending.isEmpty }
    var isCapturing: Bool { capture != nil }

    init(
        data: EditorPageObject,
        document: any BaseDocumentProtocol,
        onDrained: (@MainActor () -> Void)? = nil
    ) throws {
        try PreparedEditorPageDocument.validate(data: data, document: document)
        self.data = data
        self.document = document
        self.onDrained = onDrained
        guard exactSourceMatches() else {
            throw EditorDocumentWriteError.rejected(.documentChanged)
        }
    }

    convenience init(
        data: EditorPageObject,
        document: any BaseDocumentProtocol,
        sourceBinding: EditorDocumentWriteSourceBinding,
        onDrained: (@MainActor () -> Void)? = nil
    ) throws {
        try self.init(data: data, document: document, onDrained: onDrained)
        try bindSource(sourceBinding)
        try validateOwnership()
    }

    convenience init(
        data: EditorPageObject,
        lifetimeDocument: any BaseDocumentProtocol & EditorDocumentWriteLifetimeProviding,
        sessionLifetime: EditorDocumentWriteLifetime? = nil,
        sourceBinding: EditorDocumentWriteSourceBinding? = nil,
        onDrained: (@MainActor () -> Void)? = nil
    ) throws {
        let sources = [lifetimeDocument.editorWriteLifetime] + (sessionLifetime.map { [$0] } ?? [])
        let captured = try sources.map { source -> (EditorDocumentWriteLifetime, EditorDocumentWriteLifetime.Token) in
            guard let token = source.token() else {
                throw EditorDocumentWriteError.rejected(.retired)
            }
            return (source, token)
        }
        try self.init(data: data, document: lifetimeDocument, onDrained: onDrained)
        self.documentLifetimeSource = captured.first?.0
        for (source, token) in captured {
            let observation = source.observe(token) { [weak self] in
                // Generation checks are synchronous. This hop only delivers
                // retirement/drain notification to the original MainActor owner.
                Task { @MainActor [weak self] in self?.refreshLifetime() }
            }
            lifetimeBindings.append(.init(source: source, token: token, observation: observation))
        }
        if let sourceBinding { try bindSource(sourceBinding) }
        try validateOwnership()
    }

    private func bindSource(_ binding: EditorDocumentWriteSourceBinding) throws {
        try binding.validate()
        for capture in binding.captures {
            let observation = capture.source.observe(capture.token) { [weak self] in
                Task { @MainActor [weak self] in self?.refreshLifetime() }
            }
            lifetimeBindings.append(.init(source: capture.source, token: capture.token, observation: observation))
        }
        sourceIsCurrent = binding.isCurrent
        sourceEventBinding = binding.committedEventBinding
        originalSourceBinding = binding
    }

    func validateOwnership() throws {
        if let reason = rejection(contextId: data.objectId, requiresEditing: false) {
            throw EditorDocumentWriteError.rejected(reason)
        }
    }

    func validateDocument(_ candidate: any BaseDocumentProtocol) throws {
        try validateOwnership()
        guard candidate === document else { throw EditorDocumentWriteError.rejected(.wrongContext) }
    }

    /// A selected original child inherits frozen generations, parent retirement
    /// and the same parent's pending-work/capture boundary without new authority.
    func childSourceBinding() throws -> EditorDocumentWriteSourceBinding {
        try validateOwnership()
        guard let originalSourceBinding else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        let captured = [try EditorDocumentWriteCapture(dispatchLifetime)]
            + lifetimeBindings.map { EditorDocumentWriteCapture(source: $0.source, token: $0.token) }
        return originalSourceBinding.inheritingParent(owner: self, captures: captured) { [weak self] in
            guard let self else { return false }
            return (try? self.validateOwnership()) != nil
        }
    }

    func retire() {
        accepting = false
        dispatchLifetime.markUnavailable()
        for binding in lifetimeBindings { binding.observation.cancel() }
        lifetimeBindings.removeAll()
        notifyDrainIfNeeded()
    }

    func scheduleMutation(
        contextId: String,
        requiredPermissions: Set<EditorDocumentWritePermission> = []
    ) throws -> EditorDocumentScheduledWrite {
        let lease = try admit(contextId: contextId, requiresEditing: true, access: .mutation,
                              requiredPermissions: requiredPermissions, phase: .reserved)
        return EditorDocumentScheduledWrite(owner: self, lease: lease)
    }

    fileprivate func runScheduled<Value: Sendable>(
        _ lease: UUID, operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        guard pending[lease]?.phase == .reserved else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        pending[lease]?.phase = .running
        defer { finish(lease) }
        return try await execute(lease, operation: operation)
    }

    fileprivate func abandonScheduled(_ lease: UUID) {
        guard let entry = pending[lease], entry.phase == .reserved else { return }
        entry.operation.markFailed()
        finish(lease)
    }

    func performMutation<Value: Sendable>(
        contextId: String,
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        onDrained: (@MainActor @Sendable () -> Void)? = nil,
        operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        let lease = try admit(contextId: contextId, requiresEditing: true, access: .mutation,
                              requiredPermissions: requiredPermissions, onDrained: onDrained)
        defer { finish(lease) }
        return try await execute(lease, operation: operation)
    }

    func performMutation<Value: Sendable>(
        spaceId: String,
        createdInContext: String = "",
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        onDrained: (@MainActor @Sendable () -> Void)? = nil,
        operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        guard spaceId.utf8.elementsEqual(data.spaceId.utf8),
              createdInContext.isEmpty || createdInContext.utf8.elementsEqual(data.objectId.utf8) else {
            recordWriteFailure()
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        return try await performMutation(contextId: data.objectId, requiredPermissions: requiredPermissions,
                                         onDrained: onDrained, operation: operation)
    }

    func performRead<Value: Sendable>(
        contextId: String? = nil,
        spaceId: String? = nil,
        rpcNames: Set<String>,
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        onDrained: (@MainActor @Sendable () -> Void)? = nil,
        operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        try await performRead(contextId: contextId ?? data.objectId, spaceId: spaceId ?? data.spaceId,
                              rpcNames: rpcNames, requiredPermissions: requiredPermissions,
                              onDrained: onDrained, operation: operation)
    }

    func performRead<Value: Sendable>(
        contextId: String,
        spaceId: String,
        rpcNames: Set<String> = [],
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        onDrained: (@MainActor @Sendable () -> Void)? = nil,
        operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        try requireSpace(spaceId, writeIntent: false)
        let lease = try admit(contextId: contextId, requiresEditing: false,
                              access: .read(rpcNames), requiredPermissions: requiredPermissions, onDrained: onDrained)
        defer { finish(lease) }
        return try await execute(lease, operation: operation)
    }

    /// Stops fresh UI admissions before waiting. Already registered descendants
    /// may finish through their own leases; raw later tasks cannot reuse a closed
    /// operation. Native export and result validation run under this same gate.
    func withExclusiveRead<Value: Sendable>(
        contextId: String,
        spaceId: String,
        rpcNames: Set<String>,
        retireOnSuccess: Bool = false,
        operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        try requireSpace(spaceId, writeIntent: false)
        if let reason = rejection(contextId: contextId, requiresEditing: false) {
            throw EditorDocumentWriteError.rejected(reason)
        }
        guard capture == nil,
              EditorDocumentOperationLineage.current.leases[ObjectIdentifier(self)] == nil else {
            throw EditorDocumentWriteError.rejected(.captureInProgress)
        }
        let gate = UUID()
        capture = gate
        var lease: UUID?
        defer {
            if let lease { finish(lease) }
            if capture == gate {
                // Cancellation may leave an export or registered child running.
                // Release only when every admitted native operation has drained.
                if pending.isEmpty { capture = nil }
                else { releaseCaptureWhenDrained = gate }
            }
        }
        try await waitForDrain()
        try validateOwnership()
        guard !failedWrite else { throw EditorDocumentWriteError.rejected(.failedWrite) }
        let admitted = try admit(contextId: contextId, requiresEditing: false,
                                 access: .read(rpcNames), captureAdmission: gate)
        lease = admitted
        guard let entry = pending[admitted] else { throw EditorDocumentWriteError.rejected(.invalidLease) }
        let value = try await execute(admitted, operation: operation)
        finish(admitted)
        // Also drain a registered child read or any actual native body retained
        // after the outer export closure. No new UI write is admitted meanwhile.
        try await waitForDrain()
        try validateOwnership()
        guard !failedWrite, !entry.operation.hasFailed else {
            throw EditorDocumentWriteError.rejected(.failedWrite)
        }
        if retireOnSuccess { retire() }
        return value
    }

    func performSynchronousOperation<Value>(
        contextId: String? = nil,
        spaceId: String? = nil,
        requiresEditing: Bool = true,
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        operation: () throws -> Value
    ) throws -> Value {
        if let spaceId { try requireSpace(spaceId, writeIntent: requiresEditing) }
        let contextId = contextId ?? data.objectId
        let lease = try admit(contextId: contextId, requiresEditing: requiresEditing,
                              access: requiresEditing ? .mutation : .read([]), requiredPermissions: requiredPermissions)
        defer { finish(lease) }
        guard let entry = pending[lease] else { throw EditorDocumentWriteError.rejected(.invalidLease) }
        let binding = dispatchBinding(lease: lease)
        let lineage = entry.lineage.dispatching(binding)
        do {
            let value = try EditorDocumentOperationContext.$lineage.withValue(lineage) {
                try InvocationDispatchContext.$binding.withValue(binding, operation: operation)
            }
            if let reason = rejection(contextId: contextId, requiresEditing: entry.requiresEditing,
                                      requiredPermissions: entry.requiredPermissions) {
                throw EditorDocumentWriteError.completedWithoutOwnership(reason)
            }
            return value
        } catch {
            entry.operation.markFailed()
            throw error
        }
    }

    func performPublication(
        contextId: String,
        requiresEditing: Bool = true,
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        operation: @Sendable () async -> Void
    ) async {
        if requiresEditing {
            try? await performMutation(contextId: contextId, requiredPermissions: requiredPermissions, operation: operation)
        } else {
            try? await performRead(contextId: contextId, rpcNames: [],
                                   requiredPermissions: requiredPermissions, operation: operation)
        }
    }

    fileprivate func beginTrackedWork(access: EditorDocumentOperationAccess) throws -> EditorDocumentParentWork {
        let lease = try admit(contextId: data.objectId, requiresEditing: false, access: access, tracking: true)
        guard let entry = pending[lease] else { throw EditorDocumentWriteError.rejected(.invalidLease) }
        return EditorDocumentParentWork(owner: self, lease: lease, lineage: entry.lineage)
    }

    fileprivate func finishTrackedWork(_ lease: UUID, failed: Bool) {
        guard let entry = pending[lease], entry.tracking else { return }
        if failed { entry.operation.markFailed() }
        finish(lease)
    }

    private func requireSpace(_ spaceId: String, writeIntent: Bool) throws {
        guard spaceId.utf8.elementsEqual(data.spaceId.utf8) else {
            if writeIntent || currentOperation?.writeIntent == true { recordWriteFailure() }
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
    }

    private var currentOperation: Pending? {
        guard let lease = EditorDocumentOperationLineage.current.leases[ObjectIdentifier(self)] else { return nil }
        return pending[lease]
    }

    private func recordWriteFailure() {
        failedWrite = true
        currentOperation?.operation.markFailed()
        originalSourceBinding?.parentOwner?.recordWriteFailure()
    }

    private func admit(
        contextId: String,
        requiresEditing: Bool,
        access: EditorDocumentOperationAccess,
        requiredPermissions: Set<EditorDocumentWritePermission> = [],
        tracking: Bool = false,
        phase: Phase = .ordinary,
        onDrained: (@MainActor @Sendable () -> Void)? = nil,
        captureAdmission: UUID? = nil
    ) throws -> UUID {
        let inherited = EditorDocumentOperationLineage.current
        let inheritedID = inherited.leases[ObjectIdentifier(self)]
        let predecessor = inheritedID.flatMap { pending[$0] }
        let writeIntent = access.isMutation || predecessor?.writeIntent == true
        let permissions = requiredPermissions.union(predecessor?.requiredPermissions ?? [])
        let requiresEditing = requiresEditing || !permissions.isEmpty || predecessor?.requiresEditing == true
        do {
            if let reason = rejection(contextId: contextId, requiresEditing: requiresEditing,
                                      requiredPermissions: permissions) {
                throw EditorDocumentWriteError.rejected(reason)
            }
            if inheritedID != nil {
                guard let predecessor, predecessor.operation.isAccepting else {
                    throw EditorDocumentWriteError.rejected(.invalidLease)
                }
                guard (!predecessor.tracking || tracking), predecessor.access.permits(access) else {
                    throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
                }
            }
            if let capture, captureAdmission != capture, inheritedID == nil {
                throw EditorDocumentWriteError.rejected(.captureInProgress)
            }
            let parentWork = try originalSourceBinding?.parentOwner?.beginTrackedWork(access: access)
            let lease = UUID()
            var lineage = parentWork?.lineage ?? inherited
            lineage.leases[ObjectIdentifier(self)] = lease
            let operation = EditorDocumentWriteOperation { [self] _ in
                Task { @MainActor in self.finishDrained(lease) }
            }
            pending[lease] = Pending(operation: operation, access: access, tracking: tracking,
                writeIntent: writeIntent, contextId: contextId, requiresEditing: requiresEditing,
                requiredPermissions: permissions, lineage: lineage, parentWork: parentWork, onDrained: onDrained, phase: phase)
            return lease
        } catch {
            if writeIntent { recordWriteFailure() }
            throw error
        }
    }

    private func execute<Value: Sendable>(
        _ lease: UUID, operation: @Sendable () async throws -> Value
    ) async throws -> Value {
        guard let entry = pending[lease], !entry.tracking, entry.operation.isAccepting else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        let binding = dispatchBinding(lease: lease)
        let lineage = entry.lineage.dispatching(binding)
        do {
            if let reason = rejection(contextId: entry.contextId, requiresEditing: entry.requiresEditing,
                                      requiredPermissions: entry.requiredPermissions) {
                throw EditorDocumentWriteError.rejected(reason)
            }
            let value = try await EditorDocumentOperationContext.$lineage.withValue(lineage) {
                try await InvocationDispatchContext.$binding.withValue(binding, operation: operation)
            }
            if let reason = rejection(contextId: entry.contextId, requiresEditing: entry.requiresEditing,
                                      requiredPermissions: entry.requiredPermissions) {
                throw EditorDocumentWriteError.completedWithoutOwnership(reason)
            }
            guard pending[lease] != nil else {
                throw EditorDocumentWriteError.completedWithoutOwnership(.invalidLease)
            }
            return value
        } catch {
            entry.operation.markFailed()
            throw error
        }
    }

    private func dispatchBinding(lease: UUID) -> InvocationDispatchBinding {
        let events = sourceEventBinding.map { value -> (@Sendable () -> InvocationDispatchBinding?) in { value } }
        return InvocationDispatchBinding(committedEvents: events) { [self] messageName in
            try await self.prepareDispatch(lease: lease, messageName: messageName)
        }
    }

    private func prepareDispatch(lease: UUID, messageName: String) throws -> InvocationDispatchPermit {
        guard let entry = pending[lease] else { throw EditorDocumentWriteError.rejected(.invalidLease) }
        do {
            if let reason = rejection(contextId: entry.contextId, requiresEditing: entry.requiresEditing,
                                      requiredPermissions: entry.requiredPermissions) {
                throw EditorDocumentWriteError.rejected(reason)
            }
            guard entry.operation.isAccepting else { throw EditorDocumentWriteError.rejected(.invalidLease) }
            guard !entry.tracking, documentLifetimeSource != nil,
                  entry.access.permits(.read([messageName])) else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
            let ownerCapture = try EditorDocumentWriteCapture(dispatchLifetime)
            let captured = [ownerCapture] + lifetimeBindings.map { EditorDocumentWriteCapture(source: $0.source, token: $0.token) }
            return entry.operation.permit { try EditorDocumentWriteCapture.acquireAll(captured) }
        } catch {
            entry.operation.markFailed()
            throw error
        }
    }

    private func rejection(
        contextId: String,
        requiresEditing: Bool,
        requiredPermissions: Set<EditorDocumentWritePermission> = []
    ) -> EditorDocumentWriteRejection? {
        refreshLifetime()
        if Task.isCancelled { return .cancelled }
        guard accepting else { return .retired }
        if let sourceIsCurrent, !sourceIsCurrent() {
            // A later matching account/note/revision cannot revive this owner.
            retire()
            return .documentChanged
        }
        guard accepting else { return .retired }
        guard contextId.utf8.elementsEqual(data.objectId.utf8) else { return .wrongContext }
        do {
            try PreparedEditorPageDocument.validate(data: data, document: document)
        } catch {
            return .documentChanged
        }
        guard exactSourceMatches() else { return .documentChanged }
        let permissions = document.permissions
        if requiresEditing {
            guard data.mode == .handling else { return .notHandling }
            guard !document.isLocked, permissions.canEditBlocks else { return .notEditable }
        }
        for requirement in requiredPermissions {
            let allowed: Bool
            switch requirement {
            case .editDetails: allowed = permissions.canEditDetails
            case .changeCover: allowed = permissions.canChangeCover
            case .changeIcon: allowed = permissions.canChangeIcon
            case .changeLayout: allowed = permissions.canChangeLayout
            case .editRelationValues: allowed = permissions.canEditRelationValues
            case .editPropertiesList: allowed = permissions.canEditPropertiesList
            }
            guard allowed else { return .notEditable }
        }
        return nil
    }

    private var lifetimeIsCurrent: Bool {
        if let documentLifetimeSource {
            guard let provider = document as? any EditorDocumentWriteLifetimeProviding,
                  provider.editorWriteLifetime === documentLifetimeSource else { return false }
        }
        return lifetimeBindings.allSatisfy { $0.source.isCurrent($0.token) }
    }

    private func refreshLifetime() {
        if !lifetimeIsCurrent { retire() }
    }

    private func exactSourceMatches() -> Bool {
        guard document.objectId.utf8.elementsEqual(data.objectId.utf8),
              document.spaceId.utf8.elementsEqual(data.spaceId.utf8) else { return false }
        switch (data.mode, document.mode) {
        case (.handling, .handling), (.preview, .preview):
            return true
        case let (.version(expected), .version(actual)):
            return actual.utf8.elementsEqual(expected.utf8)
        default:
            return false
        }
    }

    private func finish(_ lease: UUID) {
        guard let entry = pending[lease], entry.operation.finishOuter() else { return }
        finishDrained(lease)
    }

    private func finishDrained(_ lease: UUID) {
        guard let entry = pending.removeValue(forKey: lease) else { return }
        let failed = entry.operation.hasFailed
        if failed && entry.writeIntent { failedWrite = true }
        entry.parentWork?.finish(failed: failed)
        entry.onDrained?()
        notifyDrainIfNeeded()
    }

    private func waitForDrain() async throws {
        try Task.checkCancellation()
        guard !pending.isEmpty else { return }
        let id = UUID()
        try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                if Task.isCancelled {
                    continuation.resume(throwing: CancellationError())
                } else if !accepting {
                    continuation.resume(throwing: EditorDocumentWriteError.rejected(.retired))
                } else if pending.isEmpty {
                    continuation.resume()
                } else {
                    drainWaiters[id] = continuation
                }
            }
        } onCancel: {
            Task { @MainActor in
                self.drainWaiters.removeValue(forKey: id)?.resume(throwing: CancellationError())
            }
        }
        try Task.checkCancellation()
    }

    private func notifyDrainIfNeeded() {
        if pending.isEmpty, let gate = releaseCaptureWhenDrained {
            if capture == gate { capture = nil }
            releaseCaptureWhenDrained = nil
        }
        if !accepting || pending.isEmpty {
            let waiters = drainWaiters.values
            drainWaiters.removeAll()
            for waiter in waiters {
                if accepting { waiter.resume() }
                else { waiter.resume(throwing: EditorDocumentWriteError.rejected(.retired)) }
            }
        }
        guard !accepting, pending.isEmpty else { return }
        let callback = onDrained
        onDrained = nil
        callback?()
    }
}
