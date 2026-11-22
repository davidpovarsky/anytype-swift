import Foundation

// ORIGINAL_CHANNEL_PIN_PERMISSION_BEGIN
/// A frozen observation of the actual original participant subscription. Its
/// constructors remain in this file; a caller cannot assert a role or account.
struct OriginalChannelPinPermission: Sendable {
    fileprivate let accountID: String
    fileprivate let spaceID: String
    fileprivate let accountCapture: EditorDocumentWriteCapture
    fileprivate let roleCapture: EditorDocumentWriteCapture

    fileprivate init(accountID: String, spaceID: String,
                     accountCapture: EditorDocumentWriteCapture) throws {
        self.accountID = accountID
        self.spaceID = spaceID
        self.accountCapture = accountCapture
        roleCapture = try EditorDocumentWriteCapture(EditorDocumentWriteLifetime())
    }

    func validate() throws {
        try accountCapture.validate()
        try roleCapture.validate()
    }

    func capture(matching account: EditorDocumentWriteCapture, spaceId: String) throws -> EditorDocumentWriteCapture {
        guard !accountID.isEmpty, spaceID.utf8.elementsEqual(spaceId.utf8),
              accountCapture.source === account.source, accountCapture.token == account.token else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        try account.validate()
        try validate()
        return roleCapture
    }

    fileprivate func retire() { roleCapture.source.markUnavailable() }
}

/// Identity of one actual startSubscription attempt, not a new account/session
/// generation. A delayed callback from a stopped attempt cannot mint a role.
private final class OriginalChannelPinSubscriptionContext: Sendable {
    let accountID: String
    let accountCapture: EditorDocumentWriteCapture

    init(accountID: String, accountCapture: EditorDocumentWriteCapture) {
        self.accountID = accountID
        self.accountCapture = accountCapture
    }
}

/// Passive bookkeeping called only on the original ParticipantsStorage actor.
/// The actual participant decoder supplies these observations; no RPC or writer
/// implementation exists here. The returned immutable snapshot is thread-safe.
private struct OriginalChannelPinPermissionState {
    private var context: OriginalChannelPinSubscriptionContext?
    private var permissions: [String: OriginalChannelPinPermission] = [:]

    mutating func begin(accountID: String, accountCapture: EditorDocumentWriteCapture?) -> OriginalChannelPinSubscriptionContext? {
        stop()
        guard !accountID.isEmpty, let accountCapture,
              (try? accountCapture.validate()) != nil else { return nil }
        let context = OriginalChannelPinSubscriptionContext(accountID: accountID, accountCapture: accountCapture)
        self.context = context
        return context
    }

    @discardableResult
    mutating func stop() -> [String: OriginalChannelPinPermission] {
        context = nil
        for permission in permissions.values { permission.retire() }
        permissions.removeAll()
        return permissions
    }

    mutating func receive(
        _ roles: [(spaceID: String, isModerator: Bool)],
        from candidate: OriginalChannelPinSubscriptionContext?
    ) throws -> [String: OriginalChannelPinPermission] {
        guard let context, context === candidate else {
            // An older stopped subscription cannot replace a newer snapshot.
            return permissions
        }
        guard (try? context.accountCapture.validate()) != nil else { return stop() }
        var next: [String: OriginalChannelPinPermission] = [:]
        var seen: Set<String> = []
        for role in roles {
            // Match the original participantSpaceView first-record semantics.
            guard !role.spaceID.isEmpty, seen.insert(role.spaceID).inserted else { continue }
            guard role.isModerator else { continue }
            if let existing = permissions[role.spaceID], (try? existing.validate()) != nil {
                next[role.spaceID] = existing
            } else {
                next[role.spaceID] = try OriginalChannelPinPermission(
                    accountID: context.accountID, spaceID: role.spaceID,
                    accountCapture: context.accountCapture
                )
            }
        }
        // Revocation precedes both the immutable snapshot and the original
        // participant stream publication. Restoration creates a fresh token.
        for (spaceID, permission) in permissions where next[spaceID] == nil {
            permission.retire()
        }
        permissions = next
        return permissions
    }
}
// ORIGINAL_CHANNEL_PIN_PERMISSION_END

// ORIGINAL_PARTICIPANT_EDIT_PERMISSION_BEGIN
/// An opaque observation of the actual original participant subscription.
/// This proves the captured participant role only. Full Space edit admission
/// must additionally use the original SpaceView restrictions and its lifetime.
struct OriginalParticipantEditPermission: Sendable {
    fileprivate let accountID: String
    fileprivate let participant: Participant
    fileprivate let accountCapture: EditorDocumentWriteCapture
    fileprivate let roleCapture: EditorDocumentWriteCapture

    fileprivate init(
        accountID: String, participant: Participant,
        accountCapture: EditorDocumentWriteCapture
    ) throws {
        self.accountID = accountID
        self.participant = participant
        self.accountCapture = accountCapture
        roleCapture = try EditorDocumentWriteCapture(EditorDocumentWriteLifetime())
    }

    /// The native value may be inspected by the original composition; copying
    /// it does not copy or construct this permission's captured authority.
    var originalParticipant: Participant { participant }

    func validate() throws {
        try accountCapture.validate()
        try roleCapture.validate()
    }

    func capture(
        matching account: EditorDocumentWriteCapture, spaceId: String
    ) throws -> EditorDocumentWriteCapture {
        guard !accountID.isEmpty,
              participant.spaceId.utf8.elementsEqual(spaceId.utf8),
              accountCapture.source === account.source,
              accountCapture.token == account.token else {
            throw EditorDocumentWriteError.rejected(.wrongContext)
        }
        try account.validate()
        try validate()
        return roleCapture
    }

    fileprivate func retainsRole(of value: Participant) -> Bool {
        participant.id.utf8.elementsEqual(value.id.utf8)
            && participant.identity.utf8.elementsEqual(value.identity.utf8)
            && participant.spaceId.utf8.elementsEqual(value.spaceId.utf8)
            && participant.permission == value.permission
            && participant.status == value.status
    }

    fileprivate func retire() { roleCapture.source.markUnavailable() }
}

/// Only the existing ParticipantsStorage actor calls this passive state.
/// It shares the original subscription attempt and frozen account capture;
/// there is no new subscription, account generation or caller role assertion.
private struct OriginalParticipantEditPermissionState {
    private var context: OriginalChannelPinSubscriptionContext?
    private var permissions: [String: OriginalParticipantEditPermission] = [:]

    mutating func begin(
        from candidate: OriginalChannelPinSubscriptionContext?
    ) -> [String: OriginalParticipantEditPermission] {
        stop()
        guard let candidate, !candidate.accountID.isEmpty,
              (try? candidate.accountCapture.validate()) != nil else { return permissions }
        context = candidate
        return permissions
    }

    @discardableResult
    mutating func stop() -> [String: OriginalParticipantEditPermission] {
        context = nil
        for permission in permissions.values { permission.retire() }
        permissions.removeAll()
        return permissions
    }

    mutating func receive(
        _ participants: [Participant],
        from candidate: OriginalChannelPinSubscriptionContext?
    ) throws -> [String: OriginalParticipantEditPermission] {
        guard let context, context === candidate else { return permissions }
        guard (try? context.accountCapture.validate()) != nil else { return stop() }
        var next: [String: OriginalParticipantEditPermission] = [:]
        var seen: Set<String> = []
        for participant in participants {
            // Keep the original first-record-per-Space selection. A denied or
            // mismatched first record cannot be replaced by a later duplicate.
            guard !participant.spaceId.isEmpty,
                  seen.insert(participant.spaceId).inserted else { continue }
            guard !participant.id.isEmpty,
                  participant.identity.utf8.elementsEqual(context.accountID.utf8),
                  participant.status == .active,
                  participant.permission.canEdit else { continue }
            if let existing = permissions[participant.spaceId],
               existing.retainsRole(of: participant),
               (try? existing.validate()) != nil {
                next[participant.spaceId] = existing
            } else {
                next[participant.spaceId] = try OriginalParticipantEditPermission(
                    accountID: context.accountID, participant: participant,
                    accountCapture: context.accountCapture
                )
            }
        }
        // Even owner -> admin -> writer must retire the earlier capture:
        // canEdit stays true, but legacy-stream editing requires the owner.
        // Invalidation precedes both snapshots and the original stream.
        for (spaceID, permission) in permissions {
            if let retained = next[spaceID],
               retained.roleCapture.source === permission.roleCapture.source { continue }
            permission.retire()
        }
        permissions = next
        return permissions
    }
}
// ORIGINAL_PARTICIPANT_EDIT_PERMISSION_END

// ORIGINAL_PARTICIPANT_SUBSCRIPTION_LIFECYCLE_BEGIN
/// Identity of one original subscription transition, not an account generation.
private final class OriginalParticipantSubscriptionAttempt: Sendable {}

/// Used only on ParticipantsStorage's original actor. A stop drains an already
/// issued start before the original unsubscribe; callbacks cannot revive it.
private struct OriginalParticipantSubscriptionLifecycle {
    private enum Phase {
        case idle
        case starting(OriginalParticipantSubscriptionAttempt)
        case active(OriginalParticipantSubscriptionAttempt)
        case stopping(OriginalParticipantSubscriptionAttempt)
        case blocked
    }

    private var phase: Phase = .idle
    private var pendingStart: OriginalParticipantSubscriptionAttempt?
    private var startWaiters: [CheckedContinuation<Void, Never>] = []
    private var stopWaiters: [CheckedContinuation<Void, Never>] = []

    mutating func beginStart() -> OriginalParticipantSubscriptionAttempt? {
        guard case .idle = phase else { return nil }
        let attempt = OriginalParticipantSubscriptionAttempt()
        pendingStart = attempt
        phase = .starting(attempt)
        return attempt
    }

    /// Every original start result settles the drain, including errors and
    /// cancellation. Only the still-current start may install its consumer.
    mutating func finishStart(_ attempt: OriginalParticipantSubscriptionAttempt) -> Bool {
        guard pendingStart === attempt else { return false }
        pendingStart = nil
        let mayInstall: Bool
        if case .starting(let current) = phase, current === attempt {
            phase = .active(attempt)
            mayInstall = true
        } else {
            mayInstall = false
        }
        let waiters = startWaiters
        startWaiters.removeAll()
        for waiter in waiters { waiter.resume() }
        return mayInstall
    }

    func acceptsPublication(from attempt: OriginalParticipantSubscriptionAttempt) -> Bool {
        guard case .active(let current) = phase else { return false }
        return current === attempt
    }

    mutating func beginStop() -> OriginalParticipantSubscriptionAttempt? {
        if case .stopping = phase { return nil }
        let attempt = OriginalParticipantSubscriptionAttempt()
        phase = .stopping(attempt)
        return attempt
    }

    mutating func waitForPendingStart(_ continuation: CheckedContinuation<Void, Never>) {
        if pendingStart != nil {
            startWaiters.append(continuation)
        } else {
            continuation.resume()
        }
    }

    mutating func waitForCurrentStop(_ continuation: CheckedContinuation<Void, Never>) {
        if case .stopping = phase {
            stopWaiters.append(continuation)
        } else {
            continuation.resume()
        }
    }

    /// An unsubscribe failure can leave the native storage's old data live.
    /// Refuse another start until an explicit stop retry actually succeeds.
    mutating func finishStop(
        _ attempt: OriginalParticipantSubscriptionAttempt, succeeded: Bool
    ) {
        guard case .stopping(let current) = phase, current === attempt,
              pendingStart == nil else { return }
        phase = succeeded ? .idle : .blocked
        let waiters = stopWaiters
        stopWaiters.removeAll()
        for waiter in waiters { waiter.resume() }
    }
}
// ORIGINAL_PARTICIPANT_SUBSCRIPTION_LIFECYCLE_END

protocol ParticipantsStorageProtocol: AnyObject, Sendable {
    var participants: [Participant] { get }
    var participantsSequence: AnyAsyncSequence<[Participant]> { get }
    func startSubscription() async
    func stopSubscription() async
}

actor ParticipantsStorage: ParticipantsStorageProtocol, Sendable {

    private let subscriptionId = "SubscriptionId.Participant-\(UUID().uuidString)"

    // MARK: - DI
    
    private let stream = AsyncToManyStream<[Participant]>()
    private var subscription: Task<Void, Never>?
    private var subscriptionLifecycle = OriginalParticipantSubscriptionLifecycle()
    private var channelPinPermissionState = OriginalChannelPinPermissionState()
    private let channelPinPermissions = AtomicStorage<[String: OriginalChannelPinPermission]>([:])
    private var participantEditPermissionState = OriginalParticipantEditPermissionState()
    private let participantEditPermissions = AtomicStorage<[String: OriginalParticipantEditPermission]>([:])
    
    @LazyInjected(\.subscriptionStorageProvider)
    private var subscriptionStorageProvider: any SubscriptionStorageProviderProtocol
    @Injected(\.accountManager)
    private var accountManager: any AccountManagerProtocol
    
    private lazy var subscriptionStorage: any SubscriptionStorageProtocol = {
        subscriptionStorageProvider.createSubscriptionStorage(subId: subscriptionId)
    }()
    
    private let subscriptionBuilder = AcountParticipantSubscriptionBuilder()
    
    // MARK: - State

    nonisolated var participants: [Participant] { stream.value ?? [] }
    nonisolated var participantsSequence: AnyAsyncSequence<[Participant]> { stream.eraseToAnyAsyncSequence() }

    /// Synchronous at the actual UI callback, before its original Task is
    /// created. The snapshot is minted only by this original actor's updates.
    nonisolated func currentChannelPinPermission(spaceId: String) throws -> OriginalChannelPinPermission {
        guard let permission = channelPinPermissions.value[spaceId] else {
            throw EditorDocumentWriteError.rejected(.notEditable)
        }
        try permission.validate()
        return permission
    }

    /// A participant-role prerequisite minted by the actual original decoder.
    /// This is not the full SpacePermissions/SpaceView creation authority.
    nonisolated func currentParticipantEditPermission(spaceId: String) throws -> OriginalParticipantEditPermission {
        guard let permission = participantEditPermissions.value[spaceId] else {
            throw EditorDocumentWriteError.rejected(.notEditable)
        }
        try permission.validate()
        return permission
    }

    func startSubscription() async {
        guard let attempt = subscriptionLifecycle.beginStart() else {
            anytypeAssertionFailure("You are trying to start ParticipantsStorage multiple times")
            return
        }

        let channelPinAccountCapture: EditorDocumentWriteCapture?
        if accountManager is AccountManager, let lifetime = accountManager.editorWriteLifetime {
            channelPinAccountCapture = try? EditorDocumentWriteCapture(lifetime)
        } else {
            channelPinAccountCapture = nil
        }
        // Freeze one account value for both the original filter and its role
        // context; begin validates the capture after reading that value.
        let accountID = accountManager.account.id
        let channelPinContext = channelPinPermissionState.begin(
            accountID: accountID, accountCapture: channelPinAccountCapture
        )
        channelPinPermissions.value = [:]
        participantEditPermissions.value = participantEditPermissionState.begin(from: channelPinContext)
        let data = subscriptionBuilder.build(accountId: accountID, subId: subscriptionId)
        let started: Bool
        do {
            try await subscriptionStorage.startOrUpdateSubscription(data: data)
            started = true
        } catch {
            started = false
        }

        // A concurrent stop owns teardown and waits for this exact start.
        guard subscriptionLifecycle.finishStart(attempt) else { return }
        guard started, !Task.isCancelled else {
            await stopSubscription()
            return
        }
        subscription = Task { [weak self, subscriptionStorage] in
            for await state in subscriptionStorage.statePublisher.values {
                guard !Task.isCancelled else { return }
                let participants = state.items.compactMap { try? Participant(details: $0) }
                await self?.publishParticipants(
                    participants, channelPinContext: channelPinContext, attempt: attempt
                )
            }
        }
    }

    func stopSubscription() async {
        guard let attempt = subscriptionLifecycle.beginStop() else {
            // A duplicate stop joins the same original teardown.
            await withCheckedContinuation { subscriptionLifecycle.waitForCurrentStop($0) }
            return
        }
        // Retire admissions and cancel the consumer before any suspension.
        channelPinPermissions.value = channelPinPermissionState.stop()
        participantEditPermissions.value = participantEditPermissionState.stop()
        subscription?.cancel()
        subscription = nil
        // The original storage can finish a pending subscribe after stop was
        // requested. Drain it before issuing the one native unsubscribe.
        await withCheckedContinuation { subscriptionLifecycle.waitForPendingStart($0) }
        let stopped: Bool
        do {
            try await subscriptionStorage.stopSubscription()
            stopped = true
        } catch {
            stopped = false
        }
        stream.clearLastValue()
        subscriptionLifecycle.finishStop(attempt, succeeded: stopped)
    }

    private func publishParticipants(
        _ participants: [Participant], channelPinContext: OriginalChannelPinSubscriptionContext?,
        attempt: OriginalParticipantSubscriptionAttempt
    ) {
        guard subscriptionLifecycle.acceptsPublication(from: attempt) else { return }
        do {
            channelPinPermissions.value = try channelPinPermissionState.receive(
                participants.map { (spaceID: $0.spaceId, isModerator: $0.permission.isModerator) },
                from: channelPinContext
            )
        } catch {
            channelPinPermissions.value = channelPinPermissionState.stop()
        }
        do {
            participantEditPermissions.value = try participantEditPermissionState.receive(
                participants, from: channelPinContext
            )
        } catch {
            participantEditPermissions.value = participantEditPermissionState.stop()
        }
        // Preserve the original decoded data for the current subscription.
        stream.send(participants)
    }
}


// Test-only readout/injection, appended in the same portable file. The exact
// production actor and helper regions above are not rewritten for these probes.
private extension OriginalParticipantSubscriptionLifecycle {
    var probePhase: String {
        switch phase {
        case .idle: return "idle"
        case .starting: return "starting"
        case .active: return "active"
        case .stopping: return "stopping"
        case .blocked: return "blocked"
        }
    }
    var probeActiveAttempt: OriginalParticipantSubscriptionAttempt? {
        if case .active(let attempt) = phase { return attempt }
        return nil
    }
}
private extension OriginalChannelPinPermissionState {
    var probeContext: OriginalChannelPinSubscriptionContext? { context }
}
private extension ParticipantsStorage {
    func probePhase() -> String { subscriptionLifecycle.probePhase }
    func probeCurrentAttempt() -> (OriginalParticipantSubscriptionAttempt, OriginalChannelPinSubscriptionContext)? {
        guard let attempt = subscriptionLifecycle.probeActiveAttempt,
              let context = channelPinPermissionState.probeContext else { return nil }
        return (attempt, context)
    }
    func probeDelayedPublication(
        _ participants: [Participant],
        attempt: OriginalParticipantSubscriptionAttempt,
        context: OriginalChannelPinSubscriptionContext
    ) {
        publishParticipants(participants, channelPinContext: context, attempt: attempt)
    }
}

@main
private struct ParticipantRoleLifecycleControls {
    @MainActor private static var passed: [String] = []
    private static func check(_ condition: Bool, file: StaticString = #filePath, line: UInt = #line) {
        precondition(condition, "control condition failed", file: file, line: line)
    }
    private static func participant(
        _ permission: ParticipantPermissions = .writer,
        status: ParticipantStatus = .active,
        id: String = "native-participant", identity: String = "actual-account",
        space: String = "actual-space", name: String = "display"
    ) -> Participant {
        Participant(id: id, localName: name, globalName: "", icon: nil,
                    status: status, permission: permission, identity: identity,
                    identityProfileLink: "", spaceId: space, type: "participant-type")
    }
    private static func rejects(_ operation: () throws -> Void) -> Bool {
        do { try operation(); return false } catch { return true }
    }
    @MainActor private static func roleFixture()
      throws -> (EditorDocumentWriteLifetime, OriginalParticipantEditPermissionState, OriginalChannelPinSubscriptionContext) {
        let account = EditorDocumentWriteLifetime()
        var original = OriginalChannelPinPermissionState()
        let context = original.begin(accountID: "actual-account", accountCapture: try .init(account))!
        var state = OriginalParticipantEditPermissionState()
        _ = state.begin(from: context)
        return (account, state, context)
    }
    @MainActor private static func storage(
        _ probe: ProbeSubscriptionStorage
    ) -> (ParticipantsStorage, AccountManager) {
        let account = AccountManager()
        account.account = .init(id: "actual-account")
        ProbeRegistry.dependencies.value = ProbeDependencies(
            subscriptionStorageProvider: ProbeProvider(storage: probe), accountManager: account
        )
        return (ParticipantsStorage(), account)
    }
    @MainActor private static func until(
        _ reason: String, _ predicate: () async -> Bool
    ) async {
        for _ in 0..<20000 {
            if await predicate() { return }
            await Task.yield()
        }
        preconditionFailure("bounded probe did not reach " + reason)
    }
    @MainActor private static func published(_ sut: ParticipantsStorage) async {
        await until("actual actor role publication") {
            (try? sut.currentParticipantEditPermission(spaceId: "actual-space")) != nil
        }
    }

    @MainActor static func main() async throws {
        do {
            for permission in [ParticipantPermissions.writer, .admin, .owner] {
                let (account, originalState, context) = try roleFixture()
                var state = originalState
                let result = try state.receive([participant(permission)], from: context)
                let role = result["actual-space"]!
                let capture = try role.capture(matching: .init(account), spaceId: "actual-space")
                let lease = try EditorDocumentWriteCapture.acquireAll([capture])
                lease.forEach { $0.cancel() }
                check(role.originalParticipant.permission == permission)
            }
            for permission in [ParticipantPermissions.reader, .noPermissions, .UNRECOGNIZED(72)] {
                let (_, originalState, context) = try roleFixture()
                var state = originalState
                check(try state.receive([participant(permission)], from: context).isEmpty)
            }
            passed.append("actual role state distinguishes native writer/admin/owner from read-only and unknown values")
        }
        do {
            for status in [ParticipantStatus.joining, .removed, .declined, .removing, .canceled, .UNRECOGNIZED(72)] {
                let (_, originalState, context) = try roleFixture()
                var state = originalState
                check(try state.receive([participant(.owner, status: status)], from: context).isEmpty)
            }
            passed.append("only the actual active participant status can mint edit-role capture")
        }
        do {
            for first in [participant(.reader), participant(.owner, identity: "other-account"),
                          participant(.owner, id: "")] {
                let (_, originalState, context) = try roleFixture()
                var state = originalState
                let result = try state.receive([first, participant(.owner)], from: context)
                check(result.isEmpty)
            }
            passed.append("first denied or mismatched native record cannot be overridden by a later same-Space record")
        }
        do {
            let (_, originalState, context) = try roleFixture()
            var state = originalState
            let old = try state.receive([participant(.owner)], from: context)["actual-space"]!
            let same = try state.receive([participant(.owner, name: "renamed")], from: context)["actual-space"]!
            check(same.roleCapture.source === old.roleCapture.source)
            let admin = try state.receive([participant(.admin)], from: context)["actual-space"]!
            check(rejects { try old.validate() })
            let writer = try state.receive([participant(.writer)], from: context)["actual-space"]!
            check(rejects { try admin.validate() })
            try writer.validate()
            passed.append("display-only change retains capture; owner-to-admin-to-writer retires every earlier security role")
        }
        do {
            let (_, originalState, context) = try roleFixture()
            var state = originalState
            let old = try state.receive([participant()], from: context)["actual-space"]!
            let changed = try state.receive([participant(id: "replacement-participant")], from: context)["actual-space"]!
            check(rejects { try old.validate() })
            check(changed.roleCapture.source !== old.roleCapture.source)
            let removed = try state.receive([], from: context)
            check(removed.isEmpty && rejects { try changed.validate() })
            passed.append("native participant replacement and removal revoke before the returned snapshot")
        }
        do {
            let (account, originalState, context) = try roleFixture()
            var state = originalState
            let old = try state.receive([participant()], from: context)["actual-space"]!
            account.invalidate()
            check(rejects { try old.validate() })
            check(try state.receive([participant()], from: context).isEmpty)
            passed.append("an equal-string account generation change rejects the old capture and delayed role input")
        }
        do {
            let (account, originalState, context) = try roleFixture()
            var state = originalState
            let role = try state.receive([participant()], from: context)["actual-space"]!
            let foreign = EditorDocumentWriteLifetime()
            check(rejects { _ = try role.capture(matching: .init(foreign), spaceId: "actual-space") })
            check(rejects { _ = try role.capture(matching: .init(account), spaceId: "ACTUAL-SPACE") })
            passed.append("role capture requires exact original account source/token and byte-exact Space")
        }
        do {
            let (_, originalState, oldContext) = try roleFixture()
            var state = originalState
            let old = try state.receive([participant()], from: oldContext)["actual-space"]!
            check(state.stop().isEmpty && rejects { try old.validate() })
            check(try state.receive([participant(.owner)], from: oldContext).isEmpty)
            let (_, _, nextContext) = try roleFixture()
            _ = state.begin(from: nextContext)
            let current = try state.receive([participant(.admin)], from: nextContext)["actual-space"]!
            let late = try state.receive([], from: oldContext)
            check(late["actual-space"]?.roleCapture.source === current.roleCapture.source)
            try current.validate()
            passed.append("stopped or earlier subscription context cannot restore, replace or revoke a later role")
        }
        do {
            let hold = ProbeHold()
            let probe = ProbeSubscriptionStorage(initial: [participant()], startHold: hold)
            let (sut, _) = storage(probe)
            let start = Task { await sut.startSubscription() }
            await hold.wait()
            check(await sut.probePhase() == "starting")
            await sut.startSubscription()
            check(probe.counters.starts == 1 && probe.counters.cachedStarts == 0)
            await hold.release()
            await start.value; await published(sut)
            check(probe.counters.accountIDs == ["actual-account"])
            await sut.stopSubscription()
            passed.append("exact actor reserves start before suspension and refuses duplicate cached-state startup")
        }
        do {
            let startHold = ProbeHold(), stopHold = ProbeHold()
            let probe = ProbeSubscriptionStorage(initial: [participant(.owner)], startHold: startHold, stopHold: stopHold)
            let (sut, _) = storage(probe)
            let start = Task { await sut.startSubscription() }
            await startHold.wait()
            let stop = Task { await sut.stopSubscription() }
            await until("stop waiting for exact original start") { await sut.probePhase() == "stopping" }
            await sut.startSubscription()
            check(probe.counters.starts == 1 && probe.counters.cachedStarts == 0 && probe.counters.stops == 0)
            check(rejects { _ = try sut.currentParticipantEditPermission(spaceId: "actual-space") })
            await startHold.release()
            await stopHold.wait()
            await start.value
            check(probe.counters.stops == 1 && sut.participants.isEmpty)
            check(rejects { _ = try sut.currentParticipantEditPermission(spaceId: "actual-space") })
            await stopHold.release(); await stop.value
            check(await sut.probePhase() == "idle")
            await sut.startSubscription(); await published(sut)
            check(probe.counters.starts == 2 && probe.counters.cachedStarts == 0)
            await sut.stopSubscription()
            passed.append("reviewed start-stop-start interleaving drains owned start before one unsubscribe and never installs stale consumer")
        }
        do {
            let hold = ProbeHold()
            let probe = ProbeSubscriptionStorage(initial: [participant(.owner)], stopHold: hold)
            let (sut, _) = storage(probe)
            await sut.startSubscription(); await published(sut)
            let role = try sut.currentParticipantEditPermission(spaceId: "actual-space")
            let done = AtomicStorage<[String]>([])
            let first = Task { await sut.stopSubscription(); done.access { $0.append("first") } }
            await hold.wait()
            let second = Task { await sut.stopSubscription(); done.access { $0.append("second") } }
            await sut.startSubscription()
            await Task.yield()
            check(done.value.isEmpty && probe.counters.stops == 1)
            check(rejects { try role.validate() })
            await hold.release(); await first.value; await second.value
            check(done.value.count == 2 && probe.counters.stops == 1)
            check(await sut.probePhase() == "idle")
            passed.append("duplicate stop joins one teardown and roles retire before its asynchronous completion")
        }
        do {
            let hold = ProbeHold()
            let probe = ProbeSubscriptionStorage(initial: [participant()], startHold: hold, failStart: true)
            let (sut, _) = storage(probe)
            let start = Task { await sut.startSubscription() }
            await hold.wait()
            let stop = Task { await sut.stopSubscription() }
            await until("failed start drain") { await sut.probePhase() == "stopping" }
            await hold.release()
            await start.value; await stop.value
            check(await sut.probePhase() == "idle")
            check(probe.counters.starts == 1 && probe.counters.stops == 1 && sut.participants.isEmpty)
            passed.append("original startup error settles a concurrent stop drain without stale publication or duplicate cleanup")
        }
        do {
            let hold = ProbeHold()
            let probe = ProbeSubscriptionStorage(initial: [participant()], startHold: hold)
            let (sut, _) = storage(probe)
            let start = Task { await sut.startSubscription() }
            await hold.wait(); start.cancel(); await hold.release(); await start.value
            check(await sut.probePhase() == "idle")
            check(probe.counters.starts == 1 && probe.counters.stops == 1 && sut.participants.isEmpty)
            check(rejects { _ = try sut.currentParticipantEditPermission(spaceId: "actual-space") })
            passed.append("cancelled original start settles and cleans up before any consumer or authority can escape")
        }
        do {
            let probe = ProbeSubscriptionStorage(initial: [participant()], failStart: true)
            let (sut, _) = storage(probe)
            await sut.startSubscription()
            check(await sut.probePhase() == "idle")
            check(probe.counters.starts == 1 && probe.counters.stops == 1)
            check(rejects { _ = try sut.currentParticipantEditPermission(spaceId: "actual-space") })
            passed.append("startup failure without concurrent stop follows the same owned teardown")
        }
        do {
            let probe = ProbeSubscriptionStorage(initial: [participant()], stopFailures: 1)
            let (sut, _) = storage(probe)
            await sut.startSubscription(); await published(sut)
            let old = try sut.currentParticipantEditPermission(spaceId: "actual-space")
            await sut.stopSubscription()
            check(await sut.probePhase() == "blocked")
            await sut.startSubscription()
            check(probe.counters.starts == 1 && probe.counters.stops == 1 && probe.counters.cachedStarts == 0)
            check(rejects { try old.validate() })
            await sut.stopSubscription()
            check(await sut.probePhase() == "idle" && probe.counters.stops == 2)
            await sut.startSubscription(); await published(sut)
            check(probe.counters.starts == 2 && probe.counters.cachedStarts == 0)
            check(rejects { try old.validate() })
            await sut.stopSubscription()
            passed.append("failed unsubscribe blocks cached restart until explicit successful stop retry; old role never revives")
        }
        do {
            let probe = ProbeSubscriptionStorage(initial: [participant(.writer)])
            let (sut, account) = storage(probe)
            await sut.startSubscription(); await published(sut)
            let (oldAttempt, oldContext) = await sut.probeCurrentAttempt()!
            await sut.stopSubscription()
            await sut.startSubscription(); await published(sut)
            let role = try sut.currentParticipantEditPermission(spaceId: "actual-space")
            await sut.probeDelayedPublication([participant(.owner, name: "stale")], attempt: oldAttempt, context: oldContext)
            check(sut.participants.first?.localName == "display")
            let after = try sut.currentParticipantEditPermission(spaceId: "actual-space")
            check(after.roleCapture.source === role.roleCapture.source)
            account.account = .init(id: "actual-account")
            check(rejects { try role.validate() })
            await sut.stopSubscription()
            passed.append("actual publication wiring rejects old attempt after restart and actual AccountManager setter invalidates equal ID")
        }
        check(passed.count == 16)
        let result: [String: Any] = [
            "executed": passed.count, "passed": passed.count, "cases": passed,
            "native_rpc_calls": 0, "native_decoder_execution": false,
            "apple_or_ui_acceptance": "NOT_RUN",
            "scope": "Exact role/lifecycle regions and complete ParticipantsStorage actor; unchanged actual Lifetime/Capture/AccountManager and native participant value/predicates; explicit portable DI/publisher/subscription/decoded-input probes only",
            "prior_suites_rerun": false
        ]
        print(String(data: try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys]), encoding: .utf8)!)
    }
}
