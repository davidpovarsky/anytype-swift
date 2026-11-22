import Foundation

// ORIGINAL_SPACE_VIEW_PERMISSION_BEGIN
/// A passive observation minted only by the original SpaceView callback.
/// This is the SpaceView prerequisite, not the participant's edit permission.
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

/// One original subscribe attempt freezes the account and its actual technical
/// Space. No caller-provided SpaceView or boolean can construct a permission.
private final class OriginalSpaceViewSubscriptionAttempt: Sendable {
    let accountID: String
    let techSpaceID: String
    let accountCapture: EditorDocumentWriteCapture?
    let capture: EditorDocumentWriteCapture

    init(
        accountID: String, techSpaceID: String,
        accountCapture: EditorDocumentWriteCapture?
    ) throws {
        self.accountID = accountID
        self.techSpaceID = techSpaceID
        self.accountCapture = accountCapture
        capture = try EditorDocumentWriteCapture(EditorDocumentWriteLifetime())
    }

    // The start task may be cancelled while the original native call still
    // drains. This closes admission immediately, including other-task callbacks.
    func retire() { capture.source.markUnavailable() }
}

private final class OriginalSpaceViewStopAttempt: Sendable {}

/// All compound mutations run on the original SpaceViewsStorage actor.
/// AtomicStorage below contains only the already committed immutable snapshot.
private struct OriginalSpaceViewPermissionState {
    private var permissions: [String: OriginalSpaceViewPermission] = [:]

    @discardableResult
    mutating func stop() -> [String: OriginalSpaceViewPermission] {
        for permission in permissions.values { permission.retire() }
        permissions.removeAll()
        return permissions
    }

    mutating func receive(
        _ spaces: [SpaceView], from attempt: OriginalSpaceViewSubscriptionAttempt
    ) throws -> [String: OriginalSpaceViewPermission] {
        guard (try? attempt.capture.validate()) != nil,
              !attempt.accountID.isEmpty, !attempt.techSpaceID.isEmpty,
              let accountCapture = attempt.accountCapture,
              (try? accountCapture.validate()) != nil else { return stop() }
        var next: [String: OriginalSpaceViewPermission] = [:]
        var seen: Set<String> = []
        for space in spaces {
            // Preserve the original first-record selection for a target Space.
            // An inactive first record cannot be replaced by a later duplicate.
            guard !space.targetSpaceId.isEmpty,
                  seen.insert(space.targetSpaceId).inserted else { continue }
            guard !space.id.isEmpty, space.isActive else { continue }
            if let existing = permissions[space.targetSpaceId],
               existing.retainsAuthority(of: space),
               (try? existing.validate()) != nil {
                next[space.targetSpaceId] = existing.updatingOriginalValue(space)
            } else {
                next[space.targetSpaceId] = try OriginalSpaceViewPermission(
                    accountID: attempt.accountID, techSpaceID: attempt.techSpaceID,
                    spaceView: space, accountCapture: accountCapture,
                    subscriptionCapture: attempt.capture
                )
            }
        }
        // Missing/restricted/replaced views retire before either snapshot or UI
        // publication. A subsequent restoration always needs a fresh capture.
        for (spaceID, permission) in permissions {
            if let retained = next[spaceID],
               retained.viewCapture.source === permission.viewCapture.source { continue }
            permission.retire()
        }
        permissions = next
        return permissions
    }
}
// ORIGINAL_SPACE_VIEW_PERMISSION_END

// ORIGINAL_SPACE_VIEW_SUBSCRIPTION_LIFECYCLE_BEGIN
/// One actor owns reservation, callback admission and teardown. The original
/// storage awaits its initial update, so that exact starting attempt may publish.
private struct OriginalSpaceViewSubscriptionLifecycle {
    private enum Phase {
        case idle
        case starting(OriginalSpaceViewSubscriptionAttempt)
        case active(OriginalSpaceViewSubscriptionAttempt)
        case stopping(OriginalSpaceViewStopAttempt)
        case blocked
    }

    private var phase: Phase = .idle
    private var pendingStart: OriginalSpaceViewSubscriptionAttempt?
    private var startWaiters: [CheckedContinuation<Void, Never>] = []
    private var stopWaiters: [CheckedContinuation<Void, Never>] = []

    var mayStart: Bool {
        if case .idle = phase { return true }
        return false
    }

    mutating func beginStart(_ attempt: OriginalSpaceViewSubscriptionAttempt) {
        pendingStart = attempt
        phase = .starting(attempt)
    }

    mutating func finishStart(_ attempt: OriginalSpaceViewSubscriptionAttempt) -> Bool {
        guard pendingStart === attempt else { return false }
        pendingStart = nil
        let mayContinue: Bool
        if case .starting(let current) = phase, current === attempt {
            phase = .active(attempt)
            mayContinue = true
        } else {
            mayContinue = false
        }
        let waiters = startWaiters
        startWaiters.removeAll()
        for waiter in waiters { waiter.resume() }
        return mayContinue
    }

    func acceptsPublication(from attempt: OriginalSpaceViewSubscriptionAttempt) -> Bool {
        switch phase {
        case .starting(let current), .active(let current): return current === attempt
        default: return false
        }
    }

    mutating func beginStop() -> OriginalSpaceViewStopAttempt? {
        if case .stopping = phase { return nil }
        let retiringStart: OriginalSpaceViewSubscriptionAttempt?
        switch phase {
        case .starting(let current), .active(let current): retiringStart = current
        default: retiringStart = nil
        }
        let attempt = OriginalSpaceViewStopAttempt()
        phase = .stopping(attempt)
        retiringStart?.retire()
        return attempt
    }

    mutating func waitForPendingStart(_ continuation: CheckedContinuation<Void, Never>) {
        if pendingStart != nil { startWaiters.append(continuation) }
        else { continuation.resume() }
    }

    mutating func waitForCurrentStop(_ continuation: CheckedContinuation<Void, Never>) {
        if case .stopping = phase { stopWaiters.append(continuation) }
        else { continuation.resume() }
    }

    mutating func finishStop(_ attempt: OriginalSpaceViewStopAttempt, succeeded: Bool) {
        guard case .stopping(let current) = phase, current === attempt,
              pendingStart == nil else { return }
        // A failed unsubscribe may leave the original storage's same-data fast
        // path live. Only an explicit successful stop retry permits a new start.
        phase = succeeded ? .idle : .blocked
        let waiters = stopWaiters
        stopWaiters.removeAll()
        for waiter in waiters { waiter.resume() }
    }
}
// ORIGINAL_SPACE_VIEW_SUBSCRIPTION_LIFECYCLE_END

protocol SpaceViewsStorageProtocol: AnyObject, Sendable {
    var allSpaceViews: [SpaceView] { get }
    var allSpaceViewsPublisher: AnyPublisher<[SpaceView], Never> { get }
    func startSubscription() async
    func stopSubscription() async
    func spaceView(spaceViewId: String) -> SpaceView?
    func spaceView(spaceId: String) -> SpaceView?
    func spaceInfo(spaceId: String) -> AccountInfo?
    // TODO: Kostyl. Waiting when middleware to add method for receive account info without set active space
    func addSpaceInfo(spaceId: String, info: AccountInfo)
}

actor SpaceViewsStorage: SpaceViewsStorageProtocol {
    // MARK: - DI

    private let subscriptionBuilder: any SpaceViewsSubscriptionBuilderProtocol = Container.shared.spaceViewsSubscriptionBuilder()
    private let subscriptionStorageProvider: any SubscriptionStorageProviderProtocol = Container.shared.subscriptionStorageProvider()
    private let subscriptionStorage: any SubscriptionStorageProtocol
    private let accountManager: any AccountManagerProtocol = Container.shared.accountManager()


    // MARK: - State

    private let spaceInfos = SynchronizedDictionary<String, AccountInfo>()

    private var permissionState = OriginalSpaceViewPermissionState()
    private let permissions = AtomicStorage<[String: OriginalSpaceViewPermission]>([:])
    private var subscriptionLifecycle = OriginalSpaceViewSubscriptionLifecycle()

    private let allSpaceViewsStorage = AtomicPublishedStorage<[SpaceView]>([])
    nonisolated var allSpaceViews: [SpaceView] { allSpaceViewsStorage.value }
    nonisolated var allSpaceViewsPublisher: AnyPublisher<[SpaceView], Never> {
        allSpaceViewsStorage.publisher
            .throttle(for: .milliseconds(50), scheduler: DispatchQueue.global(), latest: true)
            .removeDuplicates()
            .eraseToAnyPublisher()
    }

    init() {
        self.subscriptionStorage = subscriptionStorageProvider.createSubscriptionStorage(subId: subscriptionBuilder.subscriptionId)
    }

    deinit {
        for permission in permissions.value.values { permission.retire() }
    }

    /// Synchronous capture from the original callback, before any UI throttle.
    /// The caller must still compose the actual Participant and legacy-owner rule.
    nonisolated func currentOriginalSpaceViewPermission(spaceId: String) throws -> OriginalSpaceViewPermission {
        guard let permission = permissions.value[spaceId],
              permission.originalSpaceView.targetSpaceId.utf8.elementsEqual(spaceId.utf8) else {
            throw EditorDocumentWriteError.rejected(.notEditable)
        }
        try permission.validate()
        return permission
    }

    func startSubscription() async {
        guard !Task.isCancelled, subscriptionLifecycle.mayStart else { return }
        let accountCapture: EditorDocumentWriteCapture?
        if accountManager is AccountManager, let lifetime = accountManager.editorWriteLifetime {
            accountCapture = try? EditorDocumentWriteCapture(lifetime)
        } else {
            accountCapture = nil
        }
        // Capture before the one account read, and validate on the original
        // callback. Any intervening AccountManager replacement retires the token.
        let account = accountManager.account
        guard let attempt = try? OriginalSpaceViewSubscriptionAttempt(
            accountID: account.id, techSpaceID: account.info.techSpaceId,
            accountCapture: accountCapture
        ) else { return }
        subscriptionLifecycle.beginStart(attempt)
        permissions.value = permissionState.stop()
        let data = subscriptionBuilder.build(techSpaceId: attempt.techSpaceID)
        await withTaskCancellationHandler {
            let started: Bool
            do {
                // Cancellation before handler installation is also denied
                // before the original subscribe is invoked.
                try Task.checkCancellation()
                try attempt.capture.validate()
                try await subscriptionStorage.startOrUpdateSubscription(data: data) { [weak self] data in
                    let spaces = data.items.map { SpaceView(details: $0) }
                    await self?.publishSpaceViews(spaces, from: attempt)
                }
                started = true
            } catch {
                started = false
            }
            guard subscriptionLifecycle.finishStart(attempt) else { return }
            if !started || Task.isCancelled { await stopSubscription() }
        } onCancel: {
            // Do not queue this invalidation onto the actor: its initial callback
            // may arrive before the still-running subscribe has returned.
            attempt.retire()
        }
    }

    func stopSubscription() async {
        guard let attempt = subscriptionLifecycle.beginStop() else {
            await withCheckedContinuation { subscriptionLifecycle.waitForCurrentStop($0) }
            return
        }
        // Revoke before the first suspension. A late initial callback is denied,
        // allowing the pending original subscribe to drain without reviving UI.
        permissions.value = permissionState.stop()
        await withCheckedContinuation { subscriptionLifecycle.waitForPendingStart($0) }
        let stopped: Bool
        do {
            try await subscriptionStorage.stopSubscription()
            stopped = true
        } catch {
            stopped = false
        }
        subscriptionLifecycle.finishStop(attempt, succeeded: stopped)
    }

    private func publishSpaceViews(
        _ spaces: [SpaceView], from attempt: OriginalSpaceViewSubscriptionAttempt
    ) {
        guard subscriptionLifecycle.acceptsPublication(from: attempt),
              (try? attempt.capture.validate()) != nil else { return }
        do {
            permissions.value = try permissionState.receive(spaces, from: attempt)
        } catch {
            permissions.value = permissionState.stop()
        }
        // Recheck before updating the UI cache. These guards do not make UI
        // publication an atomic cross-thread rollback; captures are the authority.
        guard (try? attempt.capture.validate()) != nil else { return }
        if let accountCapture = attempt.accountCapture,
           (try? accountCapture.validate()) == nil { return }
        allSpaceViewsStorage.value = spaces
    }

    nonisolated func spaceView(spaceViewId: String) -> SpaceView? {
        return allSpaceViewsStorage.value.first(where: { $0.id == spaceViewId })
    }

    nonisolated func spaceView(spaceId: String) -> SpaceView? {
        return allSpaceViewsStorage.value.first(where: { $0.targetSpaceId == spaceId })
    }


    nonisolated func spaceInfo(spaceId: String) -> AccountInfo? {
        spaceInfos[spaceId]
    }

    nonisolated func addSpaceInfo(spaceId: String, info: AccountInfo) {
        spaceInfos[spaceId] = info
    }

}

// Fixture-only readouts appended after the complete unchanged actor projection.
// These expose waiter counts without changing phase, admission, state or bodies.
extension OriginalSpaceViewSubscriptionLifecycle {
    fileprivate var probeStartWaiterCount: Int { startWaiters.count }
    fileprivate var probeStopWaiterCount: Int { stopWaiters.count }
}
extension SpaceViewsStorage {
    func probeWaiterCounts() -> (start: Int, stop: Int) {
        (subscriptionLifecycle.probeStartWaiterCount, subscriptionLifecycle.probeStopWaiterCount)
    }
}
