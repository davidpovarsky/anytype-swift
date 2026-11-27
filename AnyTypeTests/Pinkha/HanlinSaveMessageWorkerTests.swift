import Foundation
import Testing
import HanlinHostContracts
import HanlinPlatformContracts
@testable import PinkhaHanlinCore

#if os(iOS) && DEBUG
/// The real shared worker/journal with controlled native callbacks. These are
/// lifetime, cancellation and receipt controls, not actual engine write proof.
@Suite("Hanlin save-message original worker", .serialized)
@MainActor
struct HanlinSaveMessageWorkerTests {
    @Test(.timeLimit(.minutes(1)), arguments: ["anytype", "anytype-any"])
    func stopDuringMetadataPreparationJoinsBeforeReleasingWorker(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { fixture.removeFiles() }
        let journal = try await fixture.open()
        let entered = Latch(), release = Latch(), drainEntered = Latch()
        defer { release.open() }
        var approvals = 0, dispatches = 0, drained = false
        let runner = try fixture.runner(journal: journal, prepare: { approvals += 1 }, reserve: { _ in
            entered.open()
            await release.wait()
            try await journal.reserveSaveMessage(fixture.initial)
        }, dispatch: { _, _, _, _ in dispatches += 1 })
        let execution = Task { @MainActor in try await runner.execute(fixture.invocation, approval: true) }
        await entered.wait()
        await runner.cancel(fixture.invocation.request.id)
        let drain = Task { @MainActor in
            drainEntered.open()
            let result = await runner.drainCancelledInvocation(fixture.invocation.request.id)
            drained = true
            return result
        }
        await drainEntered.wait()
        #expect(!drained && approvals == 0 && dispatches == 0)
        #expect(throws: HanlinHostError.unresolvedWrite) { try runner.validateCreationAvailability() }
        release.open()
        let receipt = await drain.value
        await #expect(throws: HanlinHostError.cancelled) { _ = try await execution.value }
        #expect(drained && approvals == 0 && dispatches == 0)
        #expect(receipt?.effectState == .notDispatched)
        #expect(try await journal.saveMessageProgress(for: fixture.initial.manifest.identity) == nil)
        let entry = try await journal.receipt(for: fixture.initial.manifest.identity)
        #expect(entry?.effect == .notDispatched)
    }

    @Test(.timeLimit(.minutes(1)), arguments: ["anytype", "anytype-any"])
    func initialRecordRacingFirstCloseStillCannotAcquireNativeAuthority(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { fixture.removeFiles() }
        let journal = try await fixture.open()
        let metadataEntered = Latch(), permitInitial = Latch(), initialSaved = Latch()
        let firstCloseReturned = Latch(), permitTerminal = Latch()
        defer { permitInitial.open(); permitTerminal.open() }
        var approvals = 0, effects = 0, closes = 0
        let runner = try fixture.runner(journal: journal, prepare: { approvals += 1 }, reserve: { _ in
            metadataEntered.open()
            await permitInitial.wait()
            try await journal.reserveSaveMessage(fixture.initial)
            initialSaved.open()
        }, close: { plan in
            closes += 1
            let first = closes == 1
            try await journal.closeSaveMessageDispatch(for: plan.identity)
            if first {
                // Exact race: first close found no initial, but its generic
                // terminal journal call has not happened yet.
                firstCloseReturned.open()
                await permitTerminal.wait()
            }
        }, dispatch: { _, _, _, _ in effects += 1 })
        let execution = Task { @MainActor in try await runner.execute(fixture.invocation, approval: true) }
        await metadataEntered.wait()
        let stop = Task { @MainActor in await runner.cancel(fixture.invocation.request.id) }
        await firstCloseReturned.wait()
        permitInitial.open()
        await initialSaved.wait()
        let settled = await runner.drainCancelledInvocation(fixture.invocation.request.id)
        #expect(closes >= 2 && approvals == 0 && effects == 0)
        #expect(settled?.effectState == .notDispatched)
        let progress = try await journal.saveMessageProgress(for: fixture.initial.manifest.identity)
        #expect(progress?.isNotDispatched == true)
        permitTerminal.open()
        await stop.value
        await #expect(throws: HanlinHostError.cancelled) { _ = try await execution.value }
        #expect(approvals == 0 && effects == 0)
    }

    @Test(.timeLimit(.minutes(1)), arguments: ["anytype", "anytype-any"])
    func stopAfterKnownRootPreventsAnotherEffectAndRetainsUncertainty(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { fixture.removeFiles() }
        let journal = try await fixture.open()
        let rootKnown = Latch(), resume = Latch()
        defer { resume.open() }
        var effects = 0, approvals = 0
        let runner = try fixture.runner(journal: journal, prepare: { approvals += 1 },
            reserve: { _ in try await journal.reserveSaveMessage(fixture.initial) }, dispatch: { _, _, authorize, _ in
                try authorize()
                var state = try await journal.advanceSaveMessage(fixture.initial, event: .rootDispatched)
                effects += 1
                state = try await journal.advanceSaveMessage(state, event: .rootKnown(reference: "root-original"))
                rootKnown.open()
                await resume.wait()
                try authorize()
                effects += 1 // The original job's Stop fence must reject this point.
            })
        let execution = Task { @MainActor in try await runner.execute(fixture.invocation, approval: true) }
        await rootKnown.wait()
        await runner.cancel(fixture.invocation.request.id)
        let beforeDrain = try await journal.saveMessageProgress(for: fixture.initial.manifest.identity)
        #expect(beforeDrain?.dispatchClosed == true && beforeDrain?.root.reference == "root-original")
        resume.open()
        let receipt = await runner.drainCancelledInvocation(fixture.invocation.request.id)
        await #expect(throws: HanlinHostError.cancelled) { _ = try await execution.value }
        #expect(approvals == 1 && effects == 1 && receipt?.effectState == .uncertain)
        let saved = try await journal.receipt(for: fixture.initial.manifest.identity)
        #expect(saved?.effect == .uncertain && saved?.createdObjectReference == nil)
        #expect(try await journal.knownCreatedObjectReference(for: fixture.initial.manifest.identity) == "root-original")
        // A fresh invocation cannot erase the retained unresolved reservation.
        let next = try fixture.nextInvocation()
        await #expect(throws: HanlinHostError.unresolvedWrite) { _ = try await runner.execute(next, approval: true) }
        #expect(approvals == 1 && effects == 1)
    }

    @Test(.timeLimit(.minutes(1)), arguments: ["anytype", "anytype-any"])
    func aggregateReceiptStillWaitsForOriginalNativeLease(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { fixture.removeFiles() }
        let journal = try await fixture.open()
        let delivered = Latch(), releaseLease = Latch(), drainEntered = Latch()
        defer { releaseLease.open() }
        var retainedAuthorization: PinkhaHanlinWriteRunner<SavePlan, Bool, Void>.EffectAuthorization?
        var drained = false, approvals = 0
        let runner = try fixture.runner(journal: journal, prepare: { approvals += 1 },
            reserve: { _ in try await journal.reserveSaveMessage(fixture.initial) }, dispatch: { _, _, authorize, receive in
                retainedAuthorization = authorize
                try authorize()
                var state = try await journal.advanceSaveMessage(fixture.initial, event: .rootDispatched)
                state = try await journal.advanceSaveMessage(state, event: .rootVerified(reference: "root-original",
                    readbackSHA256: state.manifest.expectedRootReadbackSHA256))
                try authorize()
                state = try await journal.advanceSaveMessage(state, event: .blockDispatched(index: 0))
                state = try await journal.advanceSaveMessage(state, event: .blockVerified(index: 0, reference: "block-original",
                    readbackSHA256: state.manifest.blockSHA256[0]))
                state = try await journal.advanceSaveMessage(state, event: .bodyVerified(.init(
                    manifestSHA256: try state.manifest.canonicalSHA256(), objectReference: "root-original",
                    blockReferences: ["block-original"], nativeReadbackSHA256: state.manifest.expectedBodyReadbackSHA256)))
                #expect(state.isReadyForCommit)
                try await receive("root-original")
                delivered.open()
                await releaseLease.wait()
            })
        let execution = Task { @MainActor in try await runner.execute(fixture.invocation, approval: true) }
        await delivered.wait()
        let result = try await execution.value
        #expect(result.effectState == .confirmedCommitted && approvals == 1)
        await runner.cancel(fixture.invocation.request.id)
        let drain = Task { @MainActor in
            drainEntered.open()
            let receipt = await runner.drainCancelledInvocation(fixture.invocation.request.id)
            drained = true
            return receipt
        }
        await drainEntered.wait()
        #expect(!drained)
        #expect(throws: HanlinHostError.unresolvedWrite) { try runner.validateCreationAvailability() }
        releaseLease.open()
        let receipt = try #require(await drain.value)
        #expect(drained && receipt.effectState == .confirmedCommitted && receipt == receipt.metadataReceipt())
        let stale = try #require(retainedAuthorization)
        #expect(throws: HanlinHostError.cancelled) { try stale() }
    }

    @Test(arguments: ["anytype", "anytype-any"])
    func failedMetadataPreparationConsumesNoApprovalAndDispatchesNothing(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { fixture.removeFiles() }
        let journal = try await fixture.open()
        var approvals = 0, effects = 0
        let runner = try fixture.runner(journal: journal, prepare: { approvals += 1 },
            reserve: { _ in throw PinkhaHanlinSaveMessageError.unsupportedDocument },
            dispatch: { _, _, _, _ in effects += 1 })
        let result = try await runner.execute(fixture.invocation, approval: true)
        let drained = await runner.drainCancelledInvocation(fixture.invocation.request.id)
        #expect(result.effectState == .notDispatched && drained?.effectState == .notDispatched)
        #expect(approvals == 0 && effects == 0)
        #expect(try await journal.saveMessageProgress(for: fixture.initial.manifest.identity) == nil)
    }

    /// Test-only conformance adapter around the REAL strict save parser. It
    /// changes no invocation fields and remains usable before the native binder
    /// tranche adds production conformance to that same value type.
    private struct SavePlan: PinkhaHanlinNativeWritePlan {
        static let localToolID = "save-message"
        let original: PinkhaHanlinSaveMessagePlan
        var identity: PinkhaHanlinWriteIdentity { original.identity }
        init(invocation: HanlinHostInvocation) throws { original = try .init(invocation: invocation) }
    }

    private struct Fixture {
        let parent: URL
        let session: HanlinHostSession
        let invocation: HanlinHostInvocation
        let initial: PinkhaHanlinSaveMessageProgress
        init(app: String) throws {
            parent = FileManager.default.temporaryDirectory.appendingPathComponent("hanlin-save-worker-" + UUID().uuidString, isDirectory: true)
            try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
            session = .init(conversationID: UUID(), context: .init(namespace: try .init(app: app,
                account: "disposable-account", workspace: "disposable-space", space: "disposable-space"),
                sceneID: UUID(), generation: UUID()))
            invocation = try Self.invocation(session: session)
            func digest(_ value: String) -> String { PinkhaHanlinCreatePagePlan.digest(Data(value.utf8)) }
            initial = try .init(manifest: .init(plan: PinkhaHanlinSaveMessagePlan(invocation: invocation),
                bodyPlanSHA256: digest("exact-plan"), expectedRootReadbackSHA256: digest("root-title-kind"),
                expectedBodyReadbackSHA256: digest("complete-body"), blockSHA256: [digest("block-style-content-order")]))
        }
        static func invocation(session: HanlinHostSession) throws -> HanlinHostInvocation {
            let id = UUID().uuidString.lowercased()
            return .init(request: .init(id: try .init(validating: id), logicalToolID: .init(
                providerInstanceID: try .init(validating: "anytype.host"), localToolID: try .init(validating: "save-message")),
                aliasUsed: PinkhaHanlinSaveMessagePlan.alias, descriptorRevision: try .init(1), routingTableRevision: .init(1),
                arguments: .object(["title": .string("Disposable title"), "markdown": .string("Disposable body")]),
                origin: .assistantModel, idempotencyKey: id, deadline: Date().addingTimeInterval(20),
                limits: try .init(timeoutMilliseconds: 20_000, maximumOutputBytes: 32_768)),
                session: session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
                writeGuarantee: .independentObjectCreation)
        }
        func nextInvocation() throws -> HanlinHostInvocation { try Self.invocation(session: session) }
        func open() async throws -> PinkhaHanlinWriteJournal {
            try await PinkhaHanlinWriteJournal.openInTestDirectory(parent, namespace: session.context.namespace)
        }
        @MainActor func runner(journal: PinkhaHanlinWriteJournal, prepare: @escaping @MainActor () -> Void,
                    reserve: @escaping @MainActor (SavePlan) async throws -> Void,
                    close: (@MainActor (SavePlan) async throws -> Void)? = nil,
                    dispatch: @escaping PinkhaHanlinWriteRunner<SavePlan, Bool, Void>.Dispatch) throws
            -> PinkhaHanlinWriteRunner<SavePlan, Bool, Void> {
            try .init(journal: journal, validatePlan: { plan in
                guard plan.identity.session == session else { throw HanlinHostError.staleContext }
            }, validateAvailable: {}, invalidate: {}, prepareDispatch: { _, approved in
                guard approved else { throw HanlinHostError.denied }
                prepare()
            }, reserveMetadata: reserve,
            closeDispatch: { plan in
                if let close { try await close(plan) }
                else { try await journal.closeSaveMessageDispatch(for: plan.identity) }
            }, dispatch: dispatch)
        }
        func removeFiles() { try? FileManager.default.removeItem(at: parent) }
    }

    @MainActor private final class Latch {
        private var opened = false
        private var waiters: [CheckedContinuation<Void, Never>] = []
        func open() {
            opened = true
            let original = waiters; waiters.removeAll()
            for waiter in original { waiter.resume() }
        }
        func wait() async {
            if opened { return }
            await withCheckedContinuation { waiters.append($0) }
        }
    }
}
#endif
