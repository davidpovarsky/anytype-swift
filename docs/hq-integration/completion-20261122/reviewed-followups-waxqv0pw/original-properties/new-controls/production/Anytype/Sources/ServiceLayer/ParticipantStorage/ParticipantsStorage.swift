import Foundation
import Services
import Combine
import AnytypeCore
import AsyncTools
import AsyncAlgorithms

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

protocol ParticipantsStorageProtocol: AnyObject, Sendable {
    var participants: [Participant] { get }
    var participantsSequence: AnyAsyncSequence<[Participant]> { get }
    func startSubscription() async
    func stopSubscription() async
}

extension ParticipantsStorageProtocol {
    func participantSequence(spaceId: String) -> AnyAsyncSequence<Participant> {
        participantsSequence.compactMap { $0.first { $0.spaceId == spaceId } }.removeDuplicates().eraseToAnyAsyncSequence()
    }

    func permissionSequence(spaceId: String) -> AnyAsyncSequence<ParticipantPermissions> {
        participantSequence(spaceId: spaceId).map(\.permission).removeDuplicates().eraseToAnyAsyncSequence()
    }

    func canEditSequence(spaceId: String) -> AnyAsyncSequence<Bool> {
        participantSequence(spaceId: spaceId).map(\.permission.canEdit).removeDuplicates().eraseToAnyAsyncSequence()
    }

    func canEdit(spaceId: String) -> Bool {
        participants.first { $0.spaceId == spaceId }?.canEdit ?? false
    }
}

actor ParticipantsStorage: ParticipantsStorageProtocol, Sendable {

    private let subscriptionId = "SubscriptionId.Participant-\(UUID().uuidString)"

    // MARK: - DI
    
    private let stream = AsyncToManyStream<[Participant]>()
    private var subscription: Task<Void, Never>?
    private var channelPinPermissionState = OriginalChannelPinPermissionState()
    private let channelPinPermissions = AtomicStorage<[String: OriginalChannelPinPermission]>([:])
    
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

    func startSubscription() async {
        guard subscription.isNil else {
            anytypeAssertionFailure("You are trying to start ParticipantsStorage multiple times")
            return
        }
        
        let channelPinAccountCapture: EditorDocumentWriteCapture?
        if accountManager is AccountManager, let lifetime = accountManager.editorWriteLifetime {
            channelPinAccountCapture = try? EditorDocumentWriteCapture(lifetime)
        } else {
            channelPinAccountCapture = nil
        }
        let channelPinContext = channelPinPermissionState.begin(
            accountID: accountManager.account.id, accountCapture: channelPinAccountCapture
        )
        channelPinPermissions.value = [:]
        let data = subscriptionBuilder.build(accountId: accountManager.account.id, subId: subscriptionId)
        try? await subscriptionStorage.startOrUpdateSubscription(data: data)
        
        subscription = Task { [weak self, subscriptionStorage] in
            for await state in subscriptionStorage.statePublisher.values {
                let participants = state.items.compactMap { try? Participant(details: $0) }
                self?.publishParticipants(participants, channelPinContext: channelPinContext)
            }
        }
    }

    func stopSubscription() async {
        // Stop pin admissions before the original asynchronous unsubscribe.
        channelPinPermissions.value = channelPinPermissionState.stop()
        try? await subscriptionStorage.stopSubscription()
        subscription?.cancel()
        subscription = nil
        stream.clearLastValue()
    }

    private func publishParticipants(
        _ participants: [Participant], channelPinContext: OriginalChannelPinSubscriptionContext?
    ) {
        do {
            channelPinPermissions.value = try channelPinPermissionState.receive(
                participants.map { (spaceID: $0.spaceId, isModerator: $0.permission.isModerator) },
                from: channelPinContext
            )
        } catch {
            channelPinPermissions.value = channelPinPermissionState.stop()
        }
        // Preserve the original decoded data and stream behavior unchanged.
        stream.send(participants)
    }
}
