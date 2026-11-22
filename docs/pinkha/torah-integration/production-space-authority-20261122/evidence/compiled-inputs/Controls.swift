import Foundation

struct ControlFailure: Error, CustomStringConvertible {
    let description: String
    init(_ message: String) { description = message }
}
func require(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
    guard try condition() else { throw ControlFailure(message) }
}
func rejected<T>(_ expected: EditorDocumentWriteRejection? = nil, _ body: () throws -> T) throws {
    do {
        _ = try body()
        throw ControlFailure("Expected original rejection, but operation succeeded")
    } catch let error as EditorDocumentWriteError {
        guard case .rejected(let actual) = error else { throw ControlFailure("Unexpected post-operation outcome") }
        if let expected { try require(actual == expected, "Unexpected rejection: \(actual)") }
    }
}
func waitFor(_ label: String, _ predicate: @escaping @Sendable () async -> Bool) async throws {
    let deadline = ProcessInfo.processInfo.systemUptime + 8
    repeat {
        if await predicate() { return }
        await Task.yield()
    } while ProcessInfo.processInfo.systemUptime < deadline
    throw ControlFailure("Timed out waiting for actual actor state: \(label)")
}

struct Environment: Sendable {
    let account: AccountManager
    let native: ProbeSubscriptionStorage
    let storage: SpaceViewsStorage
    var accountCapture: EditorDocumentWriteCapture {
        get throws { try EditorDocumentWriteCapture(account.editorWriteLifetime!) }
    }
    func permission(_ space: String = "space-A") throws -> OriginalSpaceViewPermission {
        try storage.currentOriginalSpaceViewPermission(spaceId: space)
    }
}
func environment(
    initial: [SpaceView] = [.init()], beforeCallback: ProbeHold? = nil,
    afterCallback: ProbeHold? = nil, duringStop: ProbeHold? = nil,
    failStart: Bool = false, stopFailures: Int = 0,
    onBuild: (@Sendable () -> Void)? = nil
) -> Environment {
    let account = AccountManager()
    account.account = .init(id: "account-A", info: .init(techSpaceId: "tech-A"))
    let native = ProbeSubscriptionStorage(
        initial: initial, beforeCallback: beforeCallback, afterCallback: afterCallback,
        duringStop: duringStop, failStart: failStart, stopFailures: stopFailures
    )
    ProbeRegistry.dependencies.value = .init(
        builder: ProbeSpaceBuilder(onBuild: onBuild),
        provider: ProbeProvider(storage: native), account: account
    )
    return .init(account: account, native: native, storage: SpaceViewsStorage())
}
func viewCapture(_ permission: OriginalSpaceViewPermission, _ e: Environment) throws -> EditorDocumentWriteCapture {
    try permission.capture(matching: e.accountCapture, spaceId: "space-A")
}
func invalid(_ capture: EditorDocumentWriteCapture) -> Bool { (try? capture.validate()) == nil }

func initialCallback() async throws -> [String] {
    let gate = ProbeHold()
    let e = environment(afterCallback: gate)
    let start = Task { await e.storage.startSubscription() }
    await gate.wait()
    let permission = try e.permission()
    try permission.validate()
    try viewCapture(permission, e).validate()
    try require(e.native.counters.starts == 1 && e.native.counters.stops == 0, "Startup callback did not precede settlement")
    try require(e.native.counters.technicalSpaces == ["tech-A"], "Original frozen technical Space was not passed to builder")
    try require(e.storage.allSpaceViews == [.init()], "Original UI value was not preserved")
    await gate.release(); await start.value
    await e.storage.stopSubscription()
    return ["actual callback admitted during starting", "exact tech-A", "one start and awaited cleanup"]
}
func displayUpdate() async throws -> [String] {
    let e = environment(); await e.storage.startSubscription()
    let old = try e.permission(); let oldCapture = try viewCapture(old, e)
    var changed = SpaceView(); changed.name = "Renamed"
    await e.native.emit([changed])
    let fresh = try e.permission(); let capture = try viewCapture(fresh, e)
    try require(oldCapture.source === capture.source && oldCapture.token == capture.token, "Display-only change revoked unchanged authority")
    try require(fresh.originalSpaceView.name == "Renamed" && e.storage.allSpaceViews == [changed], "Updated native value was not retained")
    try old.validate()
    await e.storage.stopSubscription()
    return ["display value refreshed", "same actual view token"]
}
func disappearance() async throws -> [String] {
    let e = environment(); await e.storage.startSubscription()
    let old = try e.permission(); let capture = try viewCapture(old, e)
    let observed = AtomicStorage<[Bool]>([])
    let id = e.storage.allSpaceViewsPublisher.observe { _ in observed.access { $0.append(invalid(capture)) } }
    await e.native.emit([])
    e.storage.allSpaceViewsPublisher.removeObserver(id)
    try require(observed.value == [true], "Disappearance published before retiring the actual capture")
    try rejected(.retired) { try old.validate() }
    try rejected(.notEditable) { try e.permission() }
    try require(e.storage.allSpaceViews.isEmpty, "Original disappearance UI update missing")
    await e.storage.stopSubscription()
    return ["retired before synchronous publication probe", "no permission after disappearance"]
}
func legacyRestriction() async throws -> [String] {
    let e = environment(); await e.storage.startSubscription()
    let old = try e.permission(); let capture = try viewCapture(old, e)
    let observed = AtomicStorage<[Bool]>([])
    let id = e.storage.allSpaceViewsPublisher.observe { _ in observed.access { $0.append(invalid(capture)) } }
    await e.native.emit([.init(legacy: true)])
    e.storage.allSpaceViewsPublisher.removeObserver(id)
    let fresh = try e.permission()
    try require(observed.value == [true], "Legacy restriction published before retirement")
    try require(fresh.originalSpaceView.isLegacyStream, "Original legacy value missing")
    try require(try viewCapture(fresh, e).source !== capture.source, "Restriction restored the old token")
    try rejected(.retired) { try old.validate() }
    await e.storage.stopSubscription()
    return ["legacy value preserved for future owner predicate", "old view capture retired before publication", "no full-canEdit claim"]
}
func inactiveDuplicate() async throws -> [String] {
    let e = environment(); await e.storage.startSubscription()
    let old = try e.permission(); let oldCapture = try viewCapture(old, e)
    let inactive = SpaceView(localStatus: .loading)
    let activeDuplicate = SpaceView(id: "other-native-view", name: "Second")
    await e.native.emit([inactive, activeDuplicate])
    try rejected(.notEditable) { try e.permission() }
    try rejected(.retired) { try old.validate() }
    try require(e.storage.allSpaceViews == [inactive, activeDuplicate], "Original UI first-record data changed")
    await e.native.emit([.init()])
    let restored = try e.permission()
    try require(try viewCapture(restored, e).source !== oldCapture.source,
                "Restoration revived the retired capture")
    await e.storage.stopSubscription()
    return ["inactive first record denied", "later duplicate cannot grant", "restoration requires new token"]
}
func identityReplacement() async throws -> [String] {
    let e = environment(); await e.storage.startSubscription()
    let old = try e.permission(); let capture = try viewCapture(old, e)
    await e.native.emit([.init(id: "native-view-B")])
    let next = try e.permission(); let nextCapture = try viewCapture(next, e)
    try rejected(.retired) { try old.validate() }
    try require(capture.source !== nextCapture.source, "Native view replacement reused old authority")
    try require(next.originalSpaceView.id == "native-view-B", "Wrong native view retained")
    await e.storage.stopSubscription()
    return ["exact native view identity changed", "fresh capture required"]
}
func authorityFields() async throws -> [String] {
    let e = environment(); await e.storage.startSubscription()
    var count = 0
    let inputs: [SpaceView] = [
        .init(access: .shared), .init(access: .shared, type: .oneToOne),
        .init(accountStatus: nil, access: .shared, type: .oneToOne)
    ]
    for input in inputs {
        let old = try e.permission(); let capture = try viewCapture(old, e)
        let observed = AtomicStorage(false)
        let id = e.storage.allSpaceViewsPublisher.observe { _ in observed.value = invalid(capture) }
        await e.native.emit([input])
        e.storage.allSpaceViewsPublisher.removeObserver(id)
        try require(observed.value, "Original authority field changed before retirement")
        try rejected(.retired) { try old.validate() }
        try e.permission().validate()
        count += 1
    }
    await e.storage.stopSubscription()
    return ["\(count) exact access/type/status transitions retire before publication", "original isActive predicate retained"]
}
func accountReplacement() async throws -> [String] {
    let e = environment(); await e.storage.startSubscription()
    let old = try e.permission(); let capture = try viewCapture(old, e)
    let observed = AtomicStorage<[Bool]>([])
    let observer = e.account.accountPublisher.observe { _ in observed.access { $0.append(invalid(capture)) } }
    e.account.account = .init(id: "account-B", info: .init(techSpaceId: "tech-B"))
    e.account.accountPublisher.removeObserver(observer)
    try require(observed.value == [true], "View lifetime was not retired before original AccountManager publication")
    try rejected(.retired) { try old.validate() }
    try rejected(.retired) { try e.permission() }
    var oldCallback = SpaceView(); oldCallback.name = "Late old account"
    await e.native.emit([oldCallback])
    try require(e.storage.allSpaceViews == [.init()], "Old-account callback replaced the guarded UI cache")
    await e.storage.stopSubscription()
    return ["actual AccountManager generation retired before publication", "old-account callback denied"]
}
func sameAccountRelogin() async throws -> [String] {
    let e = environment(); await e.storage.startSubscription()
    let old = try e.permission(); let before = try e.accountCapture
    e.account.account = .init(id: "account-A", info: .init(techSpaceId: "tech-A"))
    let after = try e.accountCapture
    try require(before.source === after.source && before.token != after.token, "Original account generation was not replaced")
    try rejected(.retired) { try old.validate() }
    try rejected(.wrongContext) { try old.capture(matching: after, spaceId: "space-A") }
    await e.storage.stopSubscription(); await e.storage.startSubscription()
    try e.permission().capture(matching: after, spaceId: "space-A").validate()
    await e.storage.stopSubscription()
    return ["same textual account does not revive old generation", "fresh start matches new actual token"]
}
func wrongContexts() async throws -> [String] {
    let e = environment(); await e.storage.startSubscription()
    let permission = try e.permission()
    let foreign = try EditorDocumentWriteCapture(EditorDocumentWriteLifetime())
    try rejected(.wrongContext) { try permission.capture(matching: foreign, spaceId: "space-A") }
    try rejected(.wrongContext) { try permission.capture(matching: e.accountCapture, spaceId: "space-B") }
    try rejected(.wrongContext) { try permission.capture(matching: e.accountCapture, spaceId: "SPACE-A") }
    try rejected(.notEditable) { try e.storage.currentOriginalSpaceViewPermission(spaceId: "SPACE-A") }
    try permission.validate()
    await e.storage.stopSubscription()
    return ["foreign source denied", "wrong Space denied", "byte-case variant denied"]
}
func foreignManager() async throws -> [String] {
    let foreign = ForeignAccountManager(account: .init(id: "account-A", info: .init(techSpaceId: "tech-A")))
    let native = ProbeSubscriptionStorage(initial: [.init()])
    ProbeRegistry.dependencies.value = .init(builder: ProbeSpaceBuilder(), provider: ProbeProvider(storage: native), account: foreign)
    let storage = SpaceViewsStorage(); await storage.startSubscription()
    try rejected(.notEditable) { try storage.currentOriginalSpaceViewPermission(spaceId: "space-A") }
    try require(storage.allSpaceViews == [.init()], "Unqualified protocol implementation lost original UI behavior")
    await storage.stopSubscription()
    return ["protocol-conforming foreign account cannot mint", "public UI path preserved"]
}
func stopBeforeAwait() async throws -> [String] {
    let hold = ProbeHold()
    let e = environment(duringStop: hold); await e.storage.startSubscription()
    let old = try e.permission(); let capture = try viewCapture(old, e)
    let stop = Task { await e.storage.stopSubscription() }
    await hold.wait()
    try require(invalid(capture), "Stop suspended before retiring original view lifetime")
    try rejected(.notEditable) { try e.permission() }
    await e.native.emit([.init(name: "Late stopped")])
    try require(e.storage.allSpaceViews == [.init()], "Stopped callback replaced UI cache")
    await hold.release(); await stop.value
    try require(e.native.counters.stops == 1, "Stop performed duplicate native teardown")
    return ["retired before original stop await", "late callback denied", "one unsubscribe"]
}
func pendingStartDrain() async throws -> [String] {
    let hold = ProbeHold()
    let e = environment(beforeCallback: hold)
    let start = Task { await e.storage.startSubscription() }
    await hold.wait()
    let stop = Task { await e.storage.stopSubscription() }
    try await waitFor("stop waiting for pending start") { await e.storage.probeWaiterCounts().start == 1 }
    try require(e.native.counters.stops == 0, "Unsubscribe raced ahead of original pending subscribe")
    await Task.detached { await e.native.emit([.init(name: "Other-task callback")]) }.value
    try rejected(.notEditable) { try e.permission() }
    try require(e.storage.allSpaceViews.isEmpty, "Stopped starting callback published")
    await hold.release(); await start.value; await stop.value
    try require(e.native.counters.starts == 1 && e.native.counters.stops == 1, "Pending-start drain duplicated subscribe/unsubscribe")
    return ["start drain precedes one unsubscribe", "other-task callback denied while stopping", "no callback/stop deadlock"]
}
func duplicateTransitions() async throws -> [String] {
    let hold = ProbeHold()
    let e = environment(duringStop: hold); await e.storage.startSubscription()
    await e.storage.startSubscription()
    try require(e.native.counters.starts == 1, "Duplicate active start reached native storage")
    let first = Task { await e.storage.stopSubscription() }
    await hold.wait()
    let second = Task { await e.storage.stopSubscription() }
    try await waitFor("joined stop waiter") { await e.storage.probeWaiterCounts().stop == 1 }
    await e.storage.startSubscription()
    try require(e.native.counters.starts == 1 && e.native.counters.stops == 1, "Overlap issued extra native transition")
    await hold.release(); await first.value; await second.value
    try require(e.native.counters.stops == 1, "Joined stop performed another unsubscribe")
    return ["duplicate start denied", "second stop joined original actor waiter", "one native stop"]
}
func failedStopRetry() async throws -> [String] {
    let e = environment(stopFailures: 1); await e.storage.startSubscription()
    let old = try e.permission(); let oldCapture = try viewCapture(old, e)
    await e.storage.stopSubscription()
    try rejected(.retired) { try old.validate() }
    await e.storage.startSubscription()
    try require(e.native.counters.starts == 1 && e.native.counters.stops == 1, "Failed unsubscribe permitted restart")
    await e.native.emit([.init(name: "Blocked old callback")])
    try rejected(.notEditable) { try e.permission() }
    await e.storage.stopSubscription()
    await e.storage.startSubscription()
    let fresh = try viewCapture(e.permission(), e)
    try require(fresh.source !== oldCapture.source, "Retry revived earlier view authority")
    try require(e.native.counters.starts == 2 && e.native.counters.stops == 2 &&
                e.native.counters.cachedStarts == 0, "Explicit retry did not clean original cached-data path")
    await e.storage.stopSubscription()
    return ["failed unsubscribe blocks start", "explicit successful stop retry enables fresh start", "no same-data cached restart"]
}
func oldAttemptCallback() async throws -> [String] {
    let e = environment(); await e.storage.startSubscription()
    await e.storage.stopSubscription(); await e.storage.startSubscription()
    let current = try e.permission(); let capture = try viewCapture(current, e)
    await Task.detached { await e.native.emit([.init(id: "old-view", name: "Old")], callback: 0) }.value
    let after = try viewCapture(e.permission(), e)
    try require(after.source === capture.source && after.token == capture.token, "Old attempt replaced new capture")
    try require(e.storage.allSpaceViews == [.init()], "Old attempt replaced current UI snapshot")
    await e.storage.stopSubscription()
    return ["old original callback index rejected", "new attempt snapshot and token unchanged"]
}
func preHandlerCancellation() async throws -> [String] {
    let taskBox = AtomicStorage<Task<Void, Never>?>(nil)
    let events = AtomicStorage<[String]>([])
    let e = environment(onBuild: {
        events.access { $0.append("original builder entered before handler") }
        taskBox.value!.cancel()
        events.access { $0.append("initiating task cancelled") }
    })
    let gate = ProbeHold()
    let start = Task { await gate.pause(); await e.storage.startSubscription() }
    taskBox.value = start
    await gate.wait(); await gate.release(); await start.value
    try require(events.value == ["original builder entered before handler", "initiating task cancelled"], "Cancellation was not injected at exact pre-handler boundary")
    try require(e.native.counters.starts == 0 && e.native.counters.stops == 1, "Cancelled pre-handler operation dispatched subscribe or failed to settle cleanup")
    try rejected(.notEditable) { try e.permission() }
    try require(e.storage.allSpaceViews.isEmpty, "Cancelled pre-handler start published")
    taskBox.value = nil
    return events.value + ["zero subscribes", "awaited original empty teardown"]
}
func pendingCancellationOtherTask() async throws -> [String] {
    let gate = ProbeHold(); let e = environment(beforeCallback: gate)
    let start = Task { await e.storage.startSubscription() }
    await gate.wait()
    start.cancel()
    await Task.detached { await e.native.emit([.init(name: "Uncancelled other task")]) }.value
    try rejected(.notEditable) { try e.permission() }
    try require(e.storage.allSpaceViews.isEmpty && e.native.counters.stops == 0, "Cancellation did not fence other task or unsubscribe raced drain")
    await gate.release(); await start.value
    try rejected(.notEditable) { try e.permission() }
    try require(e.native.counters.starts == 1 && e.native.counters.stops == 1, "Cancelled native start was not drained once")
    return ["other task callback denied before initial start returns", "late initiating callback denied", "one awaited unsubscribe after drain"]
}
func synchronousCancellation() async throws -> [String] {
    let gate = ProbeHold(); let e = environment(afterCallback: gate)
    let start = Task { await e.storage.startSubscription() }
    await gate.wait()
    let old = try e.permission(); let capture = try viewCapture(old, e)
    let observed = AtomicStorage(false)
    let observation = capture.source.observe(capture.token) { observed.value = true }
    start.cancel()
    // No await occurs between cancellation and these original-token checks.
    try require(observed.value && invalid(capture), "Cancellation only queued retirement onto actor")
    try rejected(.retired) { try old.validate() }
    await Task.detached { await e.native.emit([.init(name: "Late cancelled")]) }.value
    try require(e.storage.allSpaceViews == [.init()], "Canceled attempt callback replaced guarded UI cache")
    await gate.release(); await start.value
    try require(e.native.counters.stops == 1, "Cancelled startup did not retain one teardown owner")
    observation.cancel()
    return ["actual view observer fired before cancel returned", "no actor hop before capture rejection", "late other-task callback denied"]
}
final class WeakSpaceStorage: @unchecked Sendable {
    weak var value: SpaceViewsStorage?
    init(_ value: SpaceViewsStorage) { self.value = value }
}
func discardedSource() async throws -> (OriginalSpaceViewPermission, EditorDocumentWriteCapture, EditorDocumentWriteCapture, WeakSpaceStorage, ProbeSubscriptionStorage) {
    let e = environment(); await e.storage.startSubscription()
    let permission = try e.permission()
    return (permission, try viewCapture(permission, e), try e.accountCapture, WeakSpaceStorage(e.storage), e.native)
}
func storageDeallocation() async throws -> [String] {
    let (permission, capture, account, weakStorage, native) = try await discardedSource()
    try require(weakStorage.value == nil, "Fixture still retains original actor")
    try account.validate()
    try rejected(.retired) { try permission.validate() }
    try rejected(.retired) { try capture.validate() }
    try require(native.counters.stops == 0, "Deinit unexpectedly started native cleanup")
    await native.emit([.init(name: "After source release")])
    try rejected(.retired) { try permission.validate() }
    return ["actual weak original actor released", "account still current", "retained view rejected", "no deinit RPC or revival"]
}
func failedStart() async throws -> [String] {
    let e = environment(failStart: true); await e.storage.startSubscription()
    try rejected(.notEditable) { try e.permission() }
    try require(e.storage.allSpaceViews.isEmpty, "Failed original subscribe published")
    await e.native.emit([.init(name: "Late failed-start")])
    try rejected(.notEditable) { try e.permission() }
    try require(e.native.counters.starts == 1 && e.native.counters.stops == 1, "Failed start cleanup owner incorrect")
    return ["failed original start settled", "late callback rejected", "one original teardown"]
}
func alreadyCancelled() async throws -> [String] {
    let e = environment(); let gate = ProbeHold()
    let start = Task { await gate.pause(); await e.storage.startSubscription() }
    await gate.wait(); start.cancel(); await gate.release(); await start.value
    try require(e.native.counters.starts == 0 && e.native.counters.stops == 0, "Already-cancelled task invoked original storage")
    try rejected(.notEditable) { try e.permission() }
    return ["zero original start calls", "zero cleanup calls", "no authority"]
}

struct CaseResult: Codable {
    let name: String
    let status: String
    let observations: [String]
    let seconds: Double
}
struct PacketResult: Codable {
    let schema: Int
    let candidateSHA256: String
    let scope: String
    let processID: Int32
    let originalNativeCalls: Int
    let priorSuitesRerun: Bool
    let results: [CaseResult]
}

@main struct SpaceViewControls {
    static func main() async {
        let entries: [(String, @Sendable () async throws -> [String])] = [
            ("initial_callback_before_start_returns", initialCallback),
            ("display_update_retains_authority_token", displayUpdate),
            ("disappearance_retires_before_publication", disappearance),
            ("legacy_change_retires_before_publication", legacyRestriction),
            ("inactive_first_duplicate_denies_authority", inactiveDuplicate),
            ("native_view_identity_replacement_retires_capture", identityReplacement),
            ("access_status_type_changes_retire_capture", authorityFields),
            ("account_change_retires_before_account_publication", accountReplacement),
            ("same_account_relogin_does_not_revive_generation", sameAccountRelogin),
            ("wrong_account_space_and_byte_case_are_denied", wrongContexts),
            ("foreign_account_manager_cannot_mint_permission", foreignManager),
            ("stop_revokes_before_native_stop_returns", stopBeforeAwait),
            ("stop_drains_pending_start_before_unsubscribe", pendingStartDrain),
            ("duplicate_stop_joins_and_duplicate_start_is_denied", duplicateTransitions),
            ("failed_stop_blocks_start_until_successful_retry", failedStopRetry),
            ("old_attempt_callback_cannot_replace_new_snapshot", oldAttemptCallback),
            ("cancellation_before_handler_installation_denies_subscribe", preHandlerCancellation),
            ("cancelled_pending_start_rejects_other_task_callback", pendingCancellationOtherTask),
            ("cancellation_after_initial_snapshot_retires_synchronously", synchronousCancellation),
            ("retained_capture_dies_with_storage_source", storageDeallocation),
            ("failed_start_cannot_leave_authority", failedStart),
            ("already_cancelled_start_does_not_subscribe", alreadyCancelled)
        ]
        let args = CommandLine.arguments
        guard args.count >= 2 else { fatalError("Result path is required") }
        let selected = args.count >= 3 ? Set(args[2].split(separator: ",").map(String.init)) : Set(entries.map(\.0))
        guard selected.isSubset(of: Set(entries.map(\.0))), !selected.isEmpty else { fatalError("Unknown or empty selection") }
        var results: [CaseResult] = []
        for (name, body) in entries where selected.contains(name) {
            let began = ProcessInfo.processInfo.systemUptime
            let result: CaseResult
            do {
                let observations = try await body()
                result = .init(name: name, status: "PASS", observations: observations,
                               seconds: ProcessInfo.processInfo.systemUptime - began)
            } catch {
                result = .init(name: name, status: "FAIL", observations: [String(describing: error)],
                               seconds: ProcessInfo.processInfo.systemUptime - began)
            }
            results.append(result)
            FileHandle.standardOutput.write(Data("\(result.status) \(name)\n".utf8))
        }
        let packet = PacketResult(
            schema: 1, candidateSHA256: "f1570f8cff28d87152ea455ded6bc0bdfeb729e0beb3a70e3a47fb06b4710a57",
            scope: "Actual original actor/lifetimes/account with explicit portable input/dependency probes; no native decoder, Combine, RPC, Apple or full Space capability qualification",
            processID: ProcessInfo.processInfo.processIdentifier,
            originalNativeCalls: 0, priorSuitesRerun: false, results: results
        )
        do {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            try encoder.encode(packet).write(to: URL(fileURLWithPath: args[1]))
        } catch { fatalError("Could not retain actual result: \(error)") }
        if results.contains(where: { $0.status != "PASS" }) { exit(1) }
    }
}
