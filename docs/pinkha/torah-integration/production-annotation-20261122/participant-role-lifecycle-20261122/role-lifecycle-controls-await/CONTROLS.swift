
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
