import Foundation
import Combine
import Testing
import HanlinHostContracts
import HanlinPlatformContracts
@testable import Anytype

/// Actual host adapter/ledger component tests with a private access spy. NOT native authorization/UI proof.
@Suite("Anytype Hanlin read-only adapter boundaries", .serialized)
@MainActor
struct HanlinHostAdapterTests {
    @MainActor
    final class Access: PinkhaHanlinHostAccess {
        let session: HanlinHostSession
        var current: HanlinHostContext
        var permission = true
        var consent = true
        var reads = 0
        var onRead: (@MainActor () async throws -> Void)?
        var overrideSnapshot: PinkhaHanlinTextSnapshot?
        let navigation: PinkhaHanlinNavigationLedger

        init(context: HanlinHostContext) {
            session = .init(conversationID: UUID(), context: context)
            current = context
            navigation = .init(context: context)
        }
        func validate(_ context: HanlinHostContext) throws {
            guard permission else { throw HanlinHostError.denied }
            guard context == current, context == session.context else { throw HanlinHostError.staleContext }
        }
        func validateRead(_ context: HanlinHostContext) throws {
            try validate(context)
            guard consent else { throw HanlinHostError.denied }
        }
        func read(_ context: HanlinHostContext) async throws -> PinkhaHanlinTextSnapshot {
            try validateRead(context)
            reads += 1
            try await onRead?()
            return overrideSnapshot ?? .init(objectReference: "doc", spaceReference: "space", sourceRevision: "r1",
                title: "Authorized title", blocks: [.init(reference: "K", text: "Authorized text")],
                coverage: context.selectionReferences.isEmpty ? "documentTextBlocksOnly" : "selectedTextBlocksOnly")
        }
        func navigate(_ destination: HanlinHostDestination) throws -> HanlinHostNavigationResult {
            try validate(destination.context)
            _ = try navigation.enqueue(destination)
            return try navigation.result(for: destination)
        }
    }

    func context(account: String = "account", space: String = "space", scene: UUID = UUID(),
                 generation: UUID = UUID(), selected: [String] = ["K"], revision: String = "r1") throws -> HanlinHostContext {
        .init(namespace: try .init(app: "anytype", account: account, workspace: space, space: space),
              sceneID: scene, generation: generation, objectReference: "doc", selectionReferences: selected, sourceRevision: revision)
    }

    func invocation(_ access: Access, id: String = UUID().uuidString.lowercased(), run: UUID = UUID(),
                    provider: String = "opaque/Call:A", arguments: HanlinJSONValue = .object([:]),
                    guarantee: HanlinHostWriteGuarantee = .readOnly, revision: String? = nil,
                    deadline: Date = Date().addingTimeInterval(20), maximumOutput: Int = 32_768,
                    timeoutMilliseconds: Int64 = 20_000) throws -> HanlinHostInvocation {
        .init(request: .init(id: try .init(validating: id),
            logicalToolID: .init(providerInstanceID: try .init(validating: "anytype.host"),
                                 localToolID: try .init(validating: "read-context-text")),
            aliasUsed: "anytype_read_context_text", descriptorRevision: try .init(1), routingTableRevision: .init(1),
            arguments: arguments, origin: .assistantModel, deadline: deadline,
            limits: try .init(timeoutMilliseconds: timeoutMilliseconds, maximumOutputBytes: maximumOutput)),
            session: access.session, runID: run, step: 0, providerCallID: provider, writeGuarantee: guarantee, expectedRevision: revision)
    }

    @Test func scopedReadReturnsWhitelistedTextAndMetadataOnlyReceipt() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        let call = try invocation(access)
        let result = try await adapter.execute(call) { _ in }
        #expect(access.reads == 1)
        #expect(result.effectState == .confirmedNoEffect)
        guard case .completed(let contents) = result.result.outcome else { Issue.record("read failed"); return }
        #expect(contents.count == 1)
        guard case .completed(let receiptContents) = adapter.receipt(for: call.request.id)?.result.outcome else {
            Issue.record("missing original receipt"); return
        }
        #expect(receiptContents.isEmpty)
    }

    @Test func catalogNeverAdvertisesWriteAndConsentStartsUnavailable() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        access.consent = false
        #expect(try await adapter.catalog(for: access.current).tools.isEmpty)
        access.consent = true
        let catalog = try await adapter.catalog(for: access.current)
        #expect(catalog.tools.count == 1)
        #expect(catalog.tools.allSatisfy { $0.writeGuarantee == .readOnly })
    }

    @Test func unknownPermissionOrConsentDoesNotDispatch() async throws {
        for consentOnly in [false, true] {
            let access = Access(context: try context())
            access.permission = consentOnly
            access.consent = !consentOnly
            let adapter = try PinkhaHanlinHostAdapter(access: access)
            let result = try await adapter.execute(invocation(access)) { _ in }
            #expect(result.effectState == .notDispatched)
            #expect(access.reads == 0)
        }
    }

    @Test func conditionalAndIndependentWritesAlwaysFailBeforeNativeDispatch() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        for guarantee in [HanlinHostWriteGuarantee.atomicRevisionMutation, .independentObjectCreation] {
            #expect(try await adapter.execute(invocation(access, guarantee: guarantee)) { _ in }.effectState == .notDispatched)
        }
        #expect(try await adapter.execute(invocation(access, revision: "r1")) { _ in }.effectState == .notDispatched)
        #expect(access.reads == 0)
    }

    @Test func badSchemaIsRejectedRatherThanIgnoringForeignTarget() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        for args in [HanlinJSONValue.array([]), .object(["objectID": .string("foreign")]), .null] {
            #expect(try await adapter.execute(invocation(access, arguments: args)) { _ in }.effectState == .notDispatched)
        }
        #expect(access.reads == 0)
    }

    @Test func staleAccountSpaceSceneGenerationSelectionRevisionAreRejected() async throws {
        for change in 0..<6 {
            let original = try context()
            let access = Access(context: original)
            let adapter = try PinkhaHanlinHostAdapter(access: access)
            let call = try invocation(access)
            access.current = try context(account: change == 0 ? "other" : "account", space: change == 1 ? "other" : "space",
                scene: change == 2 ? UUID() : original.sceneID, generation: change == 3 ? UUID() : original.generation,
                selected: change == 4 ? ["other"] : ["K"], revision: change == 5 ? "r2" : "r1")
            #expect(try await adapter.execute(call) { _ in }.effectState == .notDispatched)
            #expect(access.reads == 0)
        }
    }

    @Test func revokeDuringProgressAwaitPreventsNativeRead() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        do {
            _ = try await adapter.execute(invocation(access)) { _ in await MainActor.run { access.permission = false } }
            Issue.record("revoked call returned")
        } catch HanlinHostError.denied {}
        #expect(access.reads == 0)
    }

    @Test func originalReceiptPrecedesStalePostReadDeliveryRejection() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        let call = try invocation(access)
        access.onRead = { access.current = try context() }
        do { _ = try await adapter.execute(call) { _ in }; Issue.record("stale result delivered") }
        catch HanlinHostError.staleContext {}
        #expect(access.reads == 1)
        #expect(adapter.receipt(for: call.request.id)?.context == call.session.context)
        #expect(adapter.receipt(for: call.request.id)?.effectState == .confirmedNoEffect)
    }

    @Test func cancelBeforeDispatchDoesNotRead() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        let call = try invocation(access)
        await adapter.cancel(call.request.id)
        do { _ = try await adapter.execute(call) { _ in }; Issue.record("cancelled call delivered") }
        catch HanlinHostError.cancelled {}
        #expect(access.reads == 0)
        #expect(adapter.receipt(for: call.request.id)?.effectState == .notDispatched)
    }

    @Test func cancelAfterReadKeepsOriginalNoWriteReceiptAndSuppressesDelivery() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        let call = try invocation(access)
        access.onRead = { await adapter.cancel(call.request.id) }
        do { _ = try await adapter.execute(call) { _ in }; Issue.record("cancelled result delivered") }
        catch HanlinHostError.cancelled {}
        #expect(access.reads == 1)
        #expect(adapter.receipt(for: call.request.id)?.effectState == .confirmedNoEffect)
    }

    @Test func duplicateAndChangedArgumentsNeverReadTwice() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        let call = try invocation(access)
        _ = try await adapter.execute(call) { _ in }
        do { _ = try await adapter.execute(call) { _ in }; Issue.record("duplicate dispatched") }
        catch HanlinHostError.duplicateInvocation {}
        let changed = try invocation(access, id: call.request.id.rawValue, run: call.runID,
            arguments: .object(["target": .string("other")]), deadline: call.request.deadline!)
        do { _ = try await adapter.execute(changed) { _ in }; Issue.record("conflict accepted") }
        catch HanlinHostError.idempotencyConflict {}
        #expect(access.reads == 1)
    }

    @Test func opaqueProviderIDIsNotLossilySanitized() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        let run = UUID()
        _ = try await adapter.execute(invocation(access, run: run, provider: "Call/A")) { _ in }
        _ = try await adapter.execute(invocation(access, run: run, provider: "Call:A")) { _ in }
        #expect(access.reads == 2)
    }

    @Test func expiredDeadlineAndOutputOverflowFailWithoutPayloadLeak() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        #expect(try await adapter.execute(invocation(access, deadline: .distantPast)) { _ in }.effectState == .notDispatched)
        let call = try invocation(access, maximumOutput: 1)
        let result = try await adapter.execute(call) { _ in }
        guard case .failed = result.result.outcome else { Issue.record("oversized payload returned"); return }
        #expect(adapter.receipt(for: call.request.id)?.reconciliationReference == nil)
    }

    @Test func foreignReadSnapshotCannotBeDelivered() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        access.overrideSnapshot = .init(objectReference: "foreign", spaceReference: "other", sourceRevision: "r1",
            title: "Secret", blocks: [.init(reference: "K", text: "Secret")], coverage: "selectedTextBlocksOnly")
        let result = try await adapter.execute(invocation(access)) { _ in }
        guard case .failed = result.result.outcome else { Issue.record("foreign payload delivered"); return }
    }

    @Test func queueIsNotPresentationAndExactMountAcknowledgementIsRequired() throws {
        let context = try context()
        let ledger = PinkhaHanlinNavigationLedger(context: context)
        let target = HanlinHostDestination(context: context, objectReference: "doc", blockReference: "K")
        #expect(try ledger.enqueue(target))
        #expect(try !ledger.result(for: target).presentationAcknowledged)
        let wrong = HanlinHostNavigationResult.presented(requestID: target.requestID, context: context,
                                                       objectReference: "other", blockReference: "K")
        #expect(throws: HanlinHostError.resultMismatch) { try ledger.acknowledge(wrong, for: target) }
        let correct = HanlinHostNavigationResult.presented(requestID: target.requestID, context: context,
                                                         objectReference: "doc", blockReference: "K")
        try ledger.acknowledge(correct, for: target)
        #expect(try ledger.result(for: target).presentationAcknowledged)
    }

    @Test func navigationReusedIDWithChangedTargetOrContextIsRejected() throws {
        let context = try context()
        let ledger = PinkhaHanlinNavigationLedger(context: context)
        let target = HanlinHostDestination(context: context, objectReference: "doc", blockReference: "K")
        _ = try ledger.enqueue(target)
        #expect(try !ledger.enqueue(target))
        let wrong = HanlinHostDestination(requestID: target.requestID, context: context, objectReference: "doc", blockReference: "Q")
        #expect(throws: HanlinHostError.resultMismatch) { try ledger.enqueue(wrong) }
    }

    @Test func presentationFenceCannotBeRearmed() {
        let fence = PinkhaHanlinRevocationFence()
        #expect(!fence.isRevoked)
        fence.revoke(); fence.revoke()
        #expect(fence.isRevoked)
    }

    @Test func nativeSelectionCurrentValueIsCheckedWithoutSkippingFirstEmission() {
        for initiallyMatches in [true, false] {
            let execution = PinkhaHanlinRevocationFence()
            let navigation = PinkhaHanlinRevocationFence()
            let states = CurrentValueSubject<EditorEditingState, Never>(
                .selecting(blocks: [initiallyMatches ? "K" : "foreign"], allSelected: false))
            let observation = PinkhaHanlinNativeAccess.observeSelection(states.eraseToAnyPublisher(), expected: ["K"]) {
                execution.revoke(); navigation.revoke()
            }
            defer { observation.cancel() }
            #expect(execution.isRevoked == !initiallyMatches && navigation.isRevoked == !initiallyMatches)
            states.send(.selecting(blocks: ["K"], allSelected: true))
            #expect(execution.isRevoked == !initiallyMatches && navigation.isRevoked == !initiallyMatches)
        }
    }

    @Test func nativeSelectionDoneAndReselectCannotRestoreEitherFence() {
        let execution = PinkhaHanlinRevocationFence()
        let navigation = PinkhaHanlinRevocationFence()
        let states = CurrentValueSubject<EditorEditingState, Never>(.selecting(blocks: ["K"], allSelected: false))
        let observation = PinkhaHanlinNativeAccess.observeSelection(states.eraseToAnyPublisher(), expected: ["K"]) {
            execution.revoke(); navigation.revoke()
        }
        defer { observation.cancel() }
        #expect(!execution.isRevoked && !navigation.isRevoked)
        states.send(.editing) // The production Done action emits this without resetting selectedBlocks.
        #expect(execution.isRevoked && navigation.isRevoked)
        states.send(.selecting(blocks: ["K"], allSelected: false))
        #expect(execution.isRevoked && navigation.isRevoked)
    }

    @Test func nativeSelectionChangedOrderAndUnicodeAliasCannotRearmAuthority() {
        for (original, changed) in [(["K"], ["other"]), (["K", "Q"], ["Q", "K"]),
                                     (["e\u{301}"], ["\u{E9}"])] {
            let execution = PinkhaHanlinRevocationFence()
            let navigation = PinkhaHanlinRevocationFence()
            let states = CurrentValueSubject<EditorEditingState, Never>(.selecting(blocks: original, allSelected: false))
            let observation = PinkhaHanlinNativeAccess.observeSelection(states.eraseToAnyPublisher(), expected: original) {
                execution.revoke(); navigation.revoke()
            }
            defer { observation.cancel() }
            #expect(!execution.isRevoked && !navigation.isRevoked)
            states.send(.selecting(blocks: changed, allSelected: false))
            #expect(execution.isRevoked && navigation.isRevoked)
            states.send(.selecting(blocks: original, allSelected: false))
            #expect(execution.isRevoked && navigation.isRevoked)
        }
    }

    @Test func nativeSelectionTableAndNonselectionModesUseTheEmittedValue() {
        let menu = SimpleTableMenuModel(tabs: [], items: [], onDone: {})
        let initial = EditorEditingState.simpleTablesSelection(block: "table", selectedBlocks: ["K"], simpleTableMenuModel: menu)
        for changed in [EditorEditingState.editing, .readonly, .loading, .moving(indexPaths: []),
                        .simpleTablesSelection(block: "table", selectedBlocks: ["other"], simpleTableMenuModel: menu)] {
            let execution = PinkhaHanlinRevocationFence()
            let navigation = PinkhaHanlinRevocationFence()
            let states = CurrentValueSubject<EditorEditingState, Never>(initial)
            let observation = PinkhaHanlinNativeAccess.observeSelection(states.eraseToAnyPublisher(), expected: ["K"]) {
                execution.revoke(); navigation.revoke()
            }
            defer { observation.cancel() }
            #expect(!execution.isRevoked && !navigation.isRevoked)
            states.send(changed)
            #expect(execution.isRevoked && navigation.isRevoked)
            states.send(initial)
            #expect(execution.isRevoked && navigation.isRevoked)
        }
    }

    @MainActor
    final class NoncooperativeRead {
        private var continuation: CheckedContinuation<Void, Never>?
        var entered: Bool { continuation != nil }
        func wait() async { await withCheckedContinuation { continuation = $0 } }
        func release() { let pending = continuation; continuation = nil; pending?.resume() }
    }

    func waitUntil(_ condition: @MainActor () -> Bool) async throws {
        let limit = ContinuousClock.now + .seconds(1)
        while !condition(), ContinuousClock.now < limit { try await Task.sleep(for: .milliseconds(5)) }
    }

    @Test func noncooperativeReadTimesOutBeforeCallbackAndLateResultCannotReplaceReceipt() async throws {
        let access = Access(context: try context())
        let adapter = try PinkhaHanlinHostAdapter(access: access)
        let stalled = NoncooperativeRead()
        defer { stalled.release() }
        access.onRead = { await stalled.wait() } // Intentionally ignores cancellation.
        let call = try invocation(access, timeoutMilliseconds: 200)
        var finished = false
        let operation = Task { @MainActor in
            defer { finished = true }
            return try await adapter.execute(call) { _ in }
        }
        try await waitUntil { stalled.entered }
        #expect(stalled.entered)
        try await waitUntil { finished }
        #expect(finished, "timeout must finish BEFORE the noncooperative callback is released")
        if finished {
            let receipt = adapter.receipt(for: call.request.id)
            guard case .failed(let failure) = receipt?.result.outcome else { Issue.record("missing timeout receipt"); return }
            #expect(failure.code == .timedOut)
            let blocked = try await adapter.execute(invocation(access)) { _ in }
            #expect(blocked.effectState == .notDispatched)
            #expect(access.reads == 1)
        }
        stalled.release() // Never release the native continuation before checking the timeout result.
        let result = try await operation.value
        guard case .failed(let failure) = result.result.outcome else { Issue.record("late read payload delivered"); return }
        #expect(failure.code == .timedOut)
        #expect(result.effectState == .confirmedNoEffect)
        await Task.yield()
        guard case .failed(let receiptFailure) = adapter.receipt(for: call.request.id)?.result.outcome else {
            Issue.record("late result replaced timeout receipt"); return
        }
        #expect(receiptFailure.code == .timedOut)
    }

    @Test func noncooperativeReadCancellationCompletesBeforeCallback() async throws {
        for explicitCancel in [false, true] {
            let access = Access(context: try context())
            let adapter = try PinkhaHanlinHostAdapter(access: access)
            let stalled = NoncooperativeRead()
            defer { stalled.release() }
            access.onRead = { await stalled.wait() }
            let call = try invocation(access)
            var finished = false
            let operation = Task { @MainActor in
                defer { finished = true }
                return try await adapter.execute(call) { _ in }
            }
            try await waitUntil { stalled.entered }
            #expect(stalled.entered)
            if explicitCancel { await adapter.cancel(call.request.id) } else { operation.cancel() }
            try await waitUntil { finished }
            #expect(finished, "cancellation must finish BEFORE releasing the native callback")
            #expect(adapter.receipt(for: call.request.id)?.effectState == .confirmedNoEffect)
            stalled.release()
            do { _ = try await operation.value; Issue.record("cancelled payload delivered") }
            catch HanlinHostError.cancelled {}
        }
    }

    @Test func cancelledRaceNeverBeginsQueuedDispatch() {
        let race = PinkhaHanlinReadRace()
        race.cancel()
        #expect(!race.beginDispatch())
        #expect(!race.wasDispatched)
    }

    @Test func signalRevocationResolvesPendingConsentOnceAndLateAllowCannotAuthorize() async {
        let fence = PinkhaHanlinRevocationFence()
        let decision = PinkhaHanlinReadConsentDecision()
        var decisions: [Bool] = []
        #expect(decision.begin { decisions.append($0) })
        fence.onRevoke { Task { @MainActor in decision.revoke() } }
        fence.revoke(); fence.revoke()
        for _ in 0..<10 where decision.isPending { await Task.yield() }
        #expect(!decision.isPending)
        #expect(decisions == [false])
        decision.resolve(true)
        #expect(!decision.authorized)
        #expect(!decision.begin { decisions.append($0) })
        #expect(decisions == [false])
    }

    @Test func promptDisappearanceUsesSameSingleCompletionAndAllowsFreshDecision() {
        let decision = PinkhaHanlinReadConsentDecision()
        var decisions: [Bool] = []
        #expect(decision.begin { decisions.append($0) })
        decision.resolve(false) // The real window-removal observer uses this same completion.
        decision.resolve(true)
        #expect(decisions == [false])
        #expect(!decision.authorized)
        #expect(decision.begin { decisions.append($0) })
        decision.resolve(true)
        #expect(decision.authorized)
        decision.revoke()
        #expect(!decision.authorized)
        #expect(decisions == [false, true])
    }

    @Test func nativeReturnReceiptCompletesOnceWithoutRearmingExecution() throws {
        let context = try context()
        let ledger = PinkhaHanlinNavigationLedger(context: context)
        let target = HanlinHostDestination(context: context, objectReference: "doc", blockReference: "K")
        #expect(try ledger.enqueue(target))
        let execution = PinkhaHanlinRevocationFence()
        var mountChecks = 0
        let handoff = try ledger.makeHandoff(for: target) {
            mountChecks += 1
            #expect(execution.isRevoked)
            return .presented(requestID: target.requestID, context: context, objectReference: "doc", blockReference: "K")
        }
        execution.revoke() // Ordinary Chat close remains final for all execution authority.
        #expect(!(try ledger.result(for: target)).presentationAcknowledged)
        let receipt = try handoff.acknowledgeMounted()
        #expect(receipt.presentationAcknowledged)
        #expect(try handoff.acknowledgeMounted() == receipt)
        handoff.cancel() // Later lifecycle changes cannot rewrite an already observed mount.
        #expect(handoff.receipt == receipt && handoff.state == .mounted)
        #expect(execution.isRevoked && mountChecks == 1)
        #expect(try ledger.result(for: target) == receipt)
    }

    @Test func nativeReturnHandoffCannotBeMintedTwiceOrForAnAliasedTarget() throws {
        let context = try context()
        let ledger = PinkhaHanlinNavigationLedger(context: context)
        let target = HanlinHostDestination(context: context, objectReference: "doc", blockReference: "e\u{301}")
        #expect(try ledger.enqueue(target))
        let handoff = try ledger.makeHandoff(for: target) {
            Issue.record("Uncompleted handoff must not validate a mount")
            return .queued(requestID: target.requestID, context: context)
        }
        defer { handoff.cancel() }
        #expect(throws: HanlinHostError.resultMismatch) {
            try ledger.makeHandoff(for: target) { .queued(requestID: target.requestID, context: context) }
        }
        let alias = HanlinHostDestination(requestID: target.requestID, context: context,
            objectReference: "doc", blockReference: "\u{E9}")
        #expect(throws: HanlinHostError.resultMismatch) { try ledger.enqueue(alias) }
        #expect(throws: HanlinHostError.resultMismatch) { try ledger.result(for: alias) }
        #expect(throws: HanlinHostError.resultMismatch) {
            try ledger.makeHandoff(for: alias) { .queued(requestID: alias.requestID, context: context) }
        }
    }

    @Test func nativeReturnCannotAcknowledgeQueuedOrDifferentMountedTargets() throws {
        let context = try context()
        let foreign = try self.context(account: "another-account")
        for mismatch in 0..<4 {
            let ledger = PinkhaHanlinNavigationLedger(context: context)
            let target = HanlinHostDestination(context: context, objectReference: "doc", blockReference: "K")
            _ = try ledger.enqueue(target)
            var mountChecks = 0
            let handoff = try ledger.makeHandoff(for: target) {
                mountChecks += 1
                switch mismatch {
                case 0: return .queued(requestID: target.requestID, context: context)
                case 1: return .presented(requestID: target.requestID, context: foreign, objectReference: "doc", blockReference: "K")
                case 2: return .presented(requestID: target.requestID, context: context, objectReference: "another-doc", blockReference: "K")
                default: return .presented(requestID: target.requestID, context: context, objectReference: "doc", blockReference: "another-block")
                }
            }
            #expect(throws: HanlinHostError.resultMismatch) { try handoff.acknowledgeMounted() }
            #expect(throws: HanlinHostError.resultMismatch) { try handoff.acknowledgeMounted() }
            #expect(handoff.state == .cancelled && handoff.receipt == nil && mountChecks == 1)
            #expect(!(try ledger.result(for: target)).presentationAcknowledged)
        }
    }

    @Test func cancelledOrExpiredNativeReturnNeverRunsMountValidation() throws {
        let context = try context()
        for expires in [false, true] {
            let ledger = PinkhaHanlinNavigationLedger(context: context)
            let target = HanlinHostDestination(context: context, objectReference: "doc")
            _ = try ledger.enqueue(target)
            var mountChecks = 0
            let handoff = try ledger.makeHandoff(for: target, timeout: expires ? .zero : .seconds(10)) {
                mountChecks += 1
                return .presented(requestID: target.requestID, context: context, objectReference: "doc", blockReference: nil)
            }
            if !expires { handoff.cancel() }
            #expect(throws: HanlinHostError.staleContext) { try handoff.acknowledgeMounted() }
            #expect(throws: HanlinHostError.staleContext) { try handoff.acknowledgeMounted() }
            #expect(handoff.state == .cancelled && handoff.receipt == nil && mountChecks == 0)
            #expect(!(try ledger.result(for: target)).presentationAcknowledged)
        }

        // A layout/reveal callback can cross the deadline while blocking the expiry task.
        // Advancing the injected monotonic clock proves this without wall-clock sleeps.
        let ledger = PinkhaHanlinNavigationLedger(context: context)
        let target = HanlinHostDestination(context: context, objectReference: "doc")
        _ = try ledger.enqueue(target)
        var instant = ContinuousClock.now
        var mountChecks = 0
        let handoff = try ledger.makeHandoff(for: target, now: { instant }) {
            mountChecks += 1
            instant = instant.advanced(by: .seconds(11))
            return .presented(requestID: target.requestID, context: context, objectReference: "doc", blockReference: nil)
        }
        #expect(throws: HanlinHostError.staleContext) { try handoff.acknowledgeMounted() }
        #expect(throws: HanlinHostError.staleContext) { try handoff.acknowledgeMounted() }
        #expect(handoff.state == .cancelled && handoff.receipt == nil && mountChecks == 1)
        #expect(!(try ledger.result(for: target)).presentationAcknowledged)
    }

    @Test func nativeReturnScopeLossPreservesQueuedReceiptWithoutRetry() throws {
        let context = try context()
        let ledger = PinkhaHanlinNavigationLedger(context: context)
        let target = HanlinHostDestination(context: context, objectReference: "doc")
        _ = try ledger.enqueue(target)
        var mountChecks = 0
        let handoff = try ledger.makeHandoff(for: target) {
            mountChecks += 1
            throw HanlinHostError.staleContext // The real native owner rejects account/Space/scene/editor changes.
        }
        #expect(throws: HanlinHostError.staleContext) { try handoff.acknowledgeMounted() }
        #expect(throws: HanlinHostError.staleContext) { try handoff.acknowledgeMounted() }
        #expect(handoff.state == .cancelled && handoff.receipt == nil && mountChecks == 1)
        #expect(!(try ledger.result(for: target)).presentationAcknowledged)
    }

    @Test func reentrantNativeReturnCancellationCannotPublishMountedReceipt() throws {
        let context = try context()
        let ledger = PinkhaHanlinNavigationLedger(context: context)
        let target = HanlinHostDestination(context: context, objectReference: "doc")
        _ = try ledger.enqueue(target)
        var retained: PinkhaHanlinNavigationHandoff?
        let handoff = try ledger.makeHandoff(for: target) {
            retained?.cancel()
            return .presented(requestID: target.requestID, context: context, objectReference: "doc", blockReference: nil)
        }
        retained = handoff
        #expect(throws: HanlinHostError.staleContext) { try handoff.acknowledgeMounted() }
        #expect(handoff.state == .cancelled && handoff.receipt == nil)
        #expect(!(try ledger.result(for: target)).presentationAcknowledged)
    }
}
