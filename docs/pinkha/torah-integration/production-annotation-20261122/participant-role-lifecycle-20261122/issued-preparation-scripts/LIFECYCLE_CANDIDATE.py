import pathlib,subprocess,json,hashlib,difflib,datetime
w=pathlib.Path(r'C:\Users\DAVID\Code\anytype-original-annotation-production-20261122')
out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-original-annotation-authority-20261122')
base='b854e7f3f59690134bcabdef88527b61517d5ab5'
path='Anytype/Sources/ServiceLayer/ParticipantStorage/ParticipantsStorage.swift'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(w),*args],timeout=45)
assert git('rev-parse','HEAD').decode().strip()==base
assert not git('status','--porcelain=v1')
original=git('show',base+':'+path)
candidate=out/'candidate'/path
before=candidate.read_bytes()
assert sha(before)=='061136d8c9bf5cd49d97a6095ccf556d468d7fc7bd6ea473c24fb9cac293402d'
(out/'PARTICIPANT_ROLE_BEFORE_LIFECYCLE.swift').write_bytes(before)
text=before.decode()
region="// ORIGINAL_PARTICIPANT_SUBSCRIPTION_LIFECYCLE_BEGIN\n/// Identity of one original subscription transition, not an account generation.\nprivate final class OriginalParticipantSubscriptionAttempt: Sendable {}\n\n/// Used only on ParticipantsStorage's original actor. A stop drains an already\n/// issued start before the original unsubscribe; callbacks cannot revive it.\nprivate struct OriginalParticipantSubscriptionLifecycle {\n    private enum Phase {\n        case idle\n        case starting(OriginalParticipantSubscriptionAttempt)\n        case active(OriginalParticipantSubscriptionAttempt)\n        case stopping(OriginalParticipantSubscriptionAttempt)\n        case blocked\n    }\n\n    private var phase: Phase = .idle\n    private var pendingStart: OriginalParticipantSubscriptionAttempt?\n    private var startWaiters: [CheckedContinuation<Void, Never>] = []\n    private var stopWaiters: [CheckedContinuation<Void, Never>] = []\n\n    mutating func beginStart() -> OriginalParticipantSubscriptionAttempt? {\n        guard case .idle = phase else { return nil }\n        let attempt = OriginalParticipantSubscriptionAttempt()\n        pendingStart = attempt\n        phase = .starting(attempt)\n        return attempt\n    }\n\n    /// Every original start result settles the drain, including errors and\n    /// cancellation. Only the still-current start may install its consumer.\n    mutating func finishStart(_ attempt: OriginalParticipantSubscriptionAttempt) -> Bool {\n        guard pendingStart === attempt else { return false }\n        pendingStart = nil\n        let mayInstall: Bool\n        if case .starting(let current) = phase, current === attempt {\n            phase = .active(attempt)\n            mayInstall = true\n        } else {\n            mayInstall = false\n        }\n        let waiters = startWaiters\n        startWaiters.removeAll()\n        for waiter in waiters { waiter.resume() }\n        return mayInstall\n    }\n\n    func acceptsPublication(from attempt: OriginalParticipantSubscriptionAttempt) -> Bool {\n        guard case .active(let current) = phase else { return false }\n        return current === attempt\n    }\n\n    mutating func beginStop() -> OriginalParticipantSubscriptionAttempt? {\n        if case .stopping = phase { return nil }\n        let attempt = OriginalParticipantSubscriptionAttempt()\n        phase = .stopping(attempt)\n        return attempt\n    }\n\n    mutating func waitForPendingStart(_ continuation: CheckedContinuation<Void, Never>) {\n        if pendingStart != nil {\n            startWaiters.append(continuation)\n        } else {\n            continuation.resume()\n        }\n    }\n\n    mutating func waitForCurrentStop(_ continuation: CheckedContinuation<Void, Never>) {\n        if case .stopping = phase {\n            stopWaiters.append(continuation)\n        } else {\n            continuation.resume()\n        }\n    }\n\n    /// An unsubscribe failure can leave the native storage's old data live.\n    /// Refuse another start until an explicit stop retry actually succeeds.\n    mutating func finishStop(\n        _ attempt: OriginalParticipantSubscriptionAttempt, succeeded: Bool\n    ) {\n        guard case .stopping(let current) = phase, current === attempt,\n              pendingStart == nil else { return }\n        phase = succeeded ? .idle : .blocked\n        let waiters = stopWaiters\n        stopWaiters.removeAll()\n        for waiter in waiters { waiter.resume() }\n    }\n}\n// ORIGINAL_PARTICIPANT_SUBSCRIPTION_LIFECYCLE_END\n\n"
old='protocol ParticipantsStorageProtocol: AnyObject, Sendable {'
assert text.count(old)==1
text=text.replace(old,region+old,1)
old='    private var subscription: Task<Void, Never>?\n'
assert text.count(old)==1
text=text.replace(old,old+'    private var subscriptionLifecycle = OriginalParticipantSubscriptionLifecycle()\n',1)
start=text.index('    func startSubscription() async {\n')
end=text.index('    private func publishParticipants(\n',start)
replacement=r'''    func startSubscription() async {
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
                self?.publishParticipants(
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

'''
text=text[:start]+replacement+text[end:]
old='        _ participants: [Participant], channelPinContext: OriginalChannelPinSubscriptionContext?\n    ) {\n'
new='        _ participants: [Participant], channelPinContext: OriginalChannelPinSubscriptionContext?,\n        attempt: OriginalParticipantSubscriptionAttempt\n    ) {\n        guard subscriptionLifecycle.acceptsPublication(from: attempt) else { return }\n'
assert text.count(old)==1
text=text.replace(old,new,1)
old='        // Preserve the original decoded data and stream behavior unchanged.\n'
new='        // Preserve the original decoded data for the current subscription.\n'
assert text.count(old)==1;text=text.replace(old,new,1)
after=text.encode()
def block(raw,start,end):return raw.split(start,1)[1].split(end,1)[0]
for tag in ('CHANNEL_PIN_PERMISSION','PARTICIPANT_EDIT_PERMISSION'):
 a=('// ORIGINAL_'+tag+'_BEGIN').encode();b=('// ORIGINAL_'+tag+'_END').encode()
 assert block(before,a,b)==block(after,a,b)
candidate.write_bytes(after)
patch=''.join(difflib.unified_diff(before.decode().splitlines(keepends=True),text.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path)).encode()
full=''.join(difflib.unified_diff(original.decode().splitlines(keepends=True),text.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path)).encode()
(out/'PARTICIPANT_LIFECYCLE.patch').write_bytes(patch)
(out/'PARTICIPANT_ROLE_AND_LIFECYCLE.patch').write_bytes(full)
m={'schema':1,'base':base,'path':path,'before_candidate_sha256':sha(before),'candidate_sha256':sha(after),'lifecycle_region_sha256':sha(region.encode()),'lifecycle_patch_sha256':sha(patch),'full_patch_sha256':sha(full),'unchanged_regions':['ORIGINAL_CHANNEL_PIN_PERMISSION','ORIGINAL_PARTICIPANT_EDIT_PERMISSION'],'worktree_changed':False,'actual_native_calls':0,'prepared_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Actor-owned original start/stop lifecycle; participant prerequisite only, not full Space authority.'}
(out/'PARTICIPANT_LIFECYCLE_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
print(json.dumps(m))
