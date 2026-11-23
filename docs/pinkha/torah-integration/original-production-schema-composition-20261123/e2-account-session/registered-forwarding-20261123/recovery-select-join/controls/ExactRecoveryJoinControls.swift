import Foundation

@MainActor
private final class OriginalLoginAccountRecovery {
    let caller: OriginalEditorAuthCaller
    let task: Task<Void, Error>
    // Stable for this real recovery, distinct for an explicit later recovery
    // of the same account ID. This is only the existing SwiftUI task's item.
    let selectionIdentity = UUID().uuidString

    init(caller: OriginalEditorAuthCaller, operation: @escaping @MainActor () async throws -> Void) {
        self.caller = caller
        task = Task { @MainActor in
            try caller.validateCurrent()
            try await operation()
            try caller.validateCurrent()
        }
    }
}


// Only the new model method/class/receiver/registration above are exact source.
// Observation/SwiftUI/Combine scheduling and omitted UI effects are NOT executed.
@MainActor
private final class ExactLoginJoinModel {
    let originalEditorCaller: OriginalEditorAuthCaller?
    var originalAccountRecovery: OriginalLoginAccountRecovery?
    var accountShowRecovery: OriginalLoginAccountRecovery?
    var accountId: String?
    var originalAccountSelectionTaskId: String?
    var selected=0
    var originalSelectionErrors=0
    init(_ caller: OriginalEditorAuthCaller) { originalEditorCaller=caller }
    func install(_ recovery: OriginalLoginAccountRecovery) {
                originalAccountRecovery = recovery
                accountShowRecovery = nil
                accountId = nil
                originalAccountSelectionTaskId = nil
    }
    func receive(_ accountId: String) {
        guard let caller=originalEditorCaller else { return }
                try? caller.withUIAction {
                    guard let recovery = originalAccountRecovery, recovery.caller === caller else { return }
                    // Record the exact operation before the existing SwiftUI task
                    // is scheduled. This consumer never waits for recovery.
                    accountShowRecovery = recovery
                    self.accountId = accountId
                    originalAccountSelectionTaskId = recovery.selectionIdentity + ":" + accountId
                }
    }
    func selectAccount() async {
        do {
            try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                if let caller = originalEditorCaller {
                    guard let recovery = accountShowRecovery,
                          recovery === originalAccountRecovery,
                          recovery.caller === caller, let observedID = accountId else {
                        throw EditorDocumentWriteError.rejected(.retired)
                    }
                    // This is the separately scheduled original SwiftUI select
                    // task, not the native callback or AccountShow consumer.
                    try await recovery.task.value
                    try caller.validateCurrent()
                    guard recovery === originalAccountRecovery,
                          recovery === accountShowRecovery,
                          accountId?.utf8.elementsEqual(observedID.utf8) == true else {
                        throw EditorDocumentWriteError.rejected(.retired)
                    }
                }
                await selectAccountInOriginalFlow()
            }
        } catch {
            // A late AccountShow or SwiftUI task cannot select for a new owner.
        }
    }
    private func selectAccountInOriginalFlow() async {
        guard let caller=originalEditorCaller, let accountId else { return }
        do {
            _ = try await caller.selectAccount(id:accountId,preferredSpaceId:"")
            selected+=1
        } catch {
            originalSelectionErrors+=1
        }
    }
}

@main
struct RecoveryJoinControls {
    @MainActor static func main() async {
        do {
            try await successOutsideCallback()
            try await failedSameIDRetry()
            try await selectCancellation()
            try await callerRetirement()
            try await staleOperationAndID()
            try await recoveryCancellation()
            let result:[String:Any]=["status":"PASS","controls":Check.passed.count,"assertions":Check.assertions,"passed":Check.passed,"scope":"Exact new recovery task class, select method, synchronous receiver action and registration statements with unchanged original Foundation caller/attempt/binding and explicit boundary doubles. No Combine/SwiftUI/native execution."]
            print("RESULT_JSON "+String(data:try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]),encoding:.utf8)!)
        } catch {
            print("RESULT_JSON "+String(data:try! JSONSerialization.data(withJSONObject:["status":"FAIL","passed":Check.passed,"assertions":Check.assertions,"error":String(reflecting:error)],options:[.sortedKeys]),encoding:.utf8)!)
            exit(1)
        }
    }

    @MainActor static func successOutsideCallback() async throws {
        let base=AuthBoundaryDouble(), entered=Gate(), release=Gate()
        await base.configureRecovery(entered:entered,release:release)
        let service=PinkhaHanlinAuthService(base:base), caller=try await service.makeOriginalEditorCaller()
        let model=ExactLoginJoinModel(caller)
        let recovery=OriginalLoginAccountRecovery(caller:caller) { try await caller.accountRecover() }
        model.install(recovery)
        await entered.wait()
        model.receive("account")
        let callbackReturned=true
        let select=Task { await model.selectAccount() }
        try await Check.briefObservation()
        try Check.that(callbackReturned && model.selected==0, "receiver returns while recovery stays held")
        try Check.that(await base.count("AccountSelect")==0, "no early select overlaps original ordinary Auth")
        await release.open()
        await select.value
        try Check.that(model.selected==1 && model.originalSelectionErrors==0, "exact original select begins after real recovery return")
        _=try await caller.closeAuthentication()
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("real_task_join_occurs_only_in_separate_select")
    }

    @MainActor static func failedSameIDRetry() async throws {
        let base=AuthBoundaryDouble(), entered1=Gate(), release1=Gate()
        await base.configureRecovery(entered:entered1,release:release1)
        let service=PinkhaHanlinAuthService(base:base), caller=try await service.makeOriginalEditorCaller()
        let model=ExactLoginJoinModel(caller)
        let first=OriginalLoginAccountRecovery(caller:caller) {
            try await caller.accountRecover()
            throw TestError.synthetic
        }
        model.install(first)
        await entered1.wait()
        model.receive("same-account")
        let firstID=model.originalAccountSelectionTaskId
        let select1=Task { await model.selectAccount() }
        await release1.open()
        await select1.value
        try Check.that(model.selected==0 && model.originalSelectionErrors==0, "failed recovery cannot call original select")
        let entered2=Gate(), release2=Gate()
        await base.configureRecovery(entered:entered2,release:release2)
        let second=OriginalLoginAccountRecovery(caller:caller) { try await caller.accountRecover() }
        model.install(second)
        await entered2.wait()
        model.receive("same-account")
        let secondID=model.originalAccountSelectionTaskId
        try Check.that(firstID != nil && secondID != nil && firstID != secondID, "same native ID on a new recovery has a new actual UI item")
        model.receive("same-account")
        try Check.that(secondID==model.originalAccountSelectionTaskId, "same-operation duplicate keeps stable UI item")
        let select2=Task { await model.selectAccount() }
        await release2.open()
        await select2.value
        try Check.that(model.selected==1, "explicit same-ID retry can select after actual second recovery")
        _=try await caller.closeAuthentication()
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("failed_recovery_same_id_retry_and_duplicate_identity")
    }

    @MainActor static func selectCancellation() async throws {
        let base=AuthBoundaryDouble(), entered=Gate(), release=Gate()
        await base.configureRecovery(entered:entered,release:release)
        let service=PinkhaHanlinAuthService(base:base), caller=try await service.makeOriginalEditorCaller()
        let model=ExactLoginJoinModel(caller)
        let recovery=OriginalLoginAccountRecovery(caller:caller) { try await caller.accountRecover() }
        model.install(recovery);await entered.wait();model.receive("account")
        let select=Task { await model.selectAccount() }
        try await Check.briefObservation()
        select.cancel()
        try Check.that(!recovery.task.isCancelled && caller.isCurrent, "select cancellation does not cancel recovery or borrow new ownership")
        await release.open()
        try await recovery.task.value
        await select.value
        let selectCount=await base.count("AccountSelect")
        try Check.that(model.selected==0 && selectCount==0, "actual post-await Task cancellation rejects before startup")
        _=try await caller.closeAuthentication()
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("select_cancellation_is_checked_after_real_recovery")
    }

    @MainActor static func callerRetirement() async throws {
        let base=AuthBoundaryDouble(), entered=Gate(), release=Gate()
        await base.configureRecovery(entered:entered,release:release)
        let service=PinkhaHanlinAuthService(base:base), caller=try await service.makeOriginalEditorCaller()
        let model=ExactLoginJoinModel(caller)
        let recovery=OriginalLoginAccountRecovery(caller:caller) { try await caller.accountRecover() }
        model.install(recovery);await entered.wait();model.receive("account")
        let select=Task { await model.selectAccount() }
        caller.retire()
        let closed=Locked(false)
        let close=Task { let result=try await caller.closeAuthentication();closed.set(true);return result }
        try await Check.briefObservation()
        try Check.that(!closed.get(), "retired caller still owns actual in-flight recovery")
        await release.open()
        try Check.that(await Check.rejected { try await recovery.task.value }, "actual retired recovery returns failure")
        await select.value
        try Check.that(model.selected==0, "retired result cannot select")
        try Check.that(Check.neverStarted(try await close.value), "ordinary recovery closure reports honest drain-only state")
        try await caller.releaseAfterRuntimeDrain()
        let next=try await service.makeOriginalEditorCaller()
        let oldID=model.accountId
        model.receive("late-other-account")
        try Check.that(model.accountId==oldID && next.isCurrent, "old receiver cannot attach to replacement caller")
        _=try await next.closeAuthentication()
        try await next.releaseAfterRuntimeDrain()
        Check.pass("retired_recovery_and_late_event_stay_with_old_owner")
    }

    @MainActor static func staleOperationAndID() async throws {
        let service=PinkhaHanlinAuthService(base:AuthBoundaryDouble()), caller=try await service.makeOriginalEditorCaller()
        let model=ExactLoginJoinModel(caller)
        let held=Gate(), entered=Gate()
        let first=OriginalLoginAccountRecovery(caller:caller) { await entered.open();await held.wait() }
        model.install(first);await entered.wait();model.receive("same")
        let select1=Task { await model.selectAccount() }
        try await Check.briefObservation()
        let replacement=OriginalLoginAccountRecovery(caller:caller) {}
        model.install(replacement);model.receive("same")
        await held.open();await select1.value
        try Check.that(model.selected==0, "selector cannot use a replaced recovery reference")
        let held2=Gate(), entered2=Gate()
        let same=OriginalLoginAccountRecovery(caller:caller) { await entered2.open();await held2.wait() }
        model.install(same);await entered2.wait();model.receive("old-id")
        let select2=Task { await model.selectAccount() }
        try await Check.briefObservation()
        model.receive("changed-id")
        await held2.open();await select2.value
        try Check.that(model.selected==0, "selector cannot change account ID during its actual join")
        _=try await caller.closeAuthentication()
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("operation_reference_and_observed_id_revalidated")
    }

    @MainActor static func recoveryCancellation() async throws {
        let base=AuthBoundaryDouble(), entered=Gate(), release=Gate()
        await base.configureRecovery(entered:entered,release:release)
        let service=PinkhaHanlinAuthService(base:base), caller=try await service.makeOriginalEditorCaller()
        let model=ExactLoginJoinModel(caller)
        let recovery=OriginalLoginAccountRecovery(caller:caller) { try await caller.accountRecover() }
        model.install(recovery);await entered.wait();model.receive("account")
        let select=Task { await model.selectAccount() }
        recovery.task.cancel()
        try await Check.briefObservation()
        try Check.that(await base.nativeCount("AccountRecover")==1 && model.selected==0, "cancel request is not a native drain or select receipt")
        await release.open()
        try Check.that(await Check.rejected { try await recovery.task.value }, "canceled recovery joins actual return then fails")
        await select.value
        try Check.that(model.selected==0, "canceled recovery cannot authorize startup")
        _=try await caller.closeAuthentication()
        try await caller.releaseAfterRuntimeDrain()
        Check.pass("recovery_cancel_is_not_completion")
    }
}
