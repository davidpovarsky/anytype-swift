
private final class WeakParticipantStorageProbe: @unchecked Sendable {
    private let lock = NSLock()
    private weak var storage: ParticipantsStorage?
    init(_ storage: ParticipantsStorage) { self.storage = storage }
    var isReleased: Bool { lock.withLock { storage == nil } }
}

@main
private struct ParticipantDeinitControl {
    private struct ReleasedFixture: Sendable {
        let weakStorage: WeakParticipantStorageProbe
        let channelPin: OriginalChannelPinPermission
        let editRole: OriginalParticipantEditPermission
        let account: EditorDocumentWriteCapture
    }
    private static func check(_ condition: Bool) {
        precondition(condition, "actual actor deallocation control failed")
    }
    private static func rejected(_ body: () throws -> Void) -> Bool {
        do { try body(); return false } catch { return true }
    }
    @MainActor private static func until(_ reason: String, _ condition: () -> Bool) async {
        for _ in 0..<20000 {
            if condition() { return }
            await Task.yield()
        }
        preconditionFailure("bounded wait failed: " + reason)
    }
    @MainActor private static func acquireThenRelease(
        probe: ProbeSubscriptionStorage, account: AccountManager
    ) async throws -> ReleasedFixture {
        ProbeRegistry.dependencies.value = ProbeDependencies(
            subscriptionStorageProvider: ProbeProvider(storage: probe), accountManager: account
        )
        let storage = ParticipantsStorage()
        await storage.startSubscription()
        await until("actual actor permission publication") {
            (try? storage.currentParticipantEditPermission(spaceId: "actual-space")) != nil
        }
        let pin = try storage.currentChannelPinPermission(spaceId: "actual-space")
        let edit = try storage.currentParticipantEditPermission(spaceId: "actual-space")
        try pin.validate(); try edit.validate()
        check(probe.statePublisher.probeSubscriberCount == 1)
        // No strong reference to the actual storage is returned.
        return ReleasedFixture(weakStorage: .init(storage), channelPin: pin, editRole: edit,
                               account: try .init(account.editorWriteLifetime!))
    }
    @MainActor static func main() async throws {
        let account = AccountManager()
        account.account = .init(id: "actual-account")
        let value = Participant(
            id: "native-participant", localName: "owner", globalName: "", icon: nil,
            status: .active, permission: .owner, identity: "actual-account",
            identityProfileLink: "", spaceId: "actual-space", type: "participant-type"
        )
        let probe = ProbeSubscriptionStorage(initial: [value])
        let fixture = try await acquireThenRelease(probe: probe, account: account)
        await until("weak storage deallocation") { fixture.weakStorage.isReleased }
        try fixture.account.validate()
        check(rejected { try fixture.channelPin.validate() })
        check(rejected { try fixture.editRole.validate() })
        await until("actual subscription Task cancellation") {
            probe.statePublisher.probeSubscriberCount == 0
                && probe.statePublisher.probeCancelledSubscriptions == 1
        }
        probe.send([value])
        check(rejected { try fixture.channelPin.validate() })
        check(rejected { try fixture.editRole.validate() })
        try fixture.account.validate()
        check(probe.counters.starts == 1 && probe.counters.stops == 0)
        let result: [String: Any] = [
            "executed": 1, "passed": 1,
            "cases": ["Actual ParticipantsStorage deallocates despite its weak consumer; deinit retires retained channel-pin and edit-role captures while original account remains current, cancels the live consumer, and later input cannot revive either capture"],
            "source_scope": "Exact original actor with new deinit; actual Lifetime/Capture/AccountManager, explicit portable decoded-input/DI/publisher/subscription probes",
            "weak_storage_release_observed": true,
            "consumer_cancellation_observed": true,
            "native_rpc_calls": 0,
            "native_decoder_execution": false,
            "apple_or_ui_acceptance": "NOT_RUN",
            "prior_16_controls_replayed": false
        ]
        print(String(data: try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys]), encoding: .utf8)!)
    }
}
