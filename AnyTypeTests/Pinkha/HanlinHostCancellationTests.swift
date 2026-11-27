@testable import PinkhaHanlinCore
import Foundation
import Testing
import HanlinHostContracts
import HanlinPlatformContracts

#if os(iOS) && DEBUG
/// Actual shared worker and protected metadata journal with a controlled native
/// callback. These prove worker/receipt lifetime, not a real native engine write or UI.
@Suite("Hanlin original worker cancellation drain", .serialized)
@MainActor
struct HanlinHostCancellationTests {
    @Test(.timeLimit(.minutes(1)), arguments: ["anytype", "anytype-any"])
    func cancelledWorkerDrainsOriginalReceiptAfterAccountRevocation(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { try? FileManager.default.removeItem(at: fixture.directory) }
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(fixture.directory,
            namespace: fixture.session.context.namespace)
        let entered = Latch(), completeNative = Latch(), drainStarted = Latch()
        defer { completeNative.open() }
        var currentAccountAvailable = true
        var dispatches = 0, drained = false
        let runner = try PinkhaHanlinCreateRunner<Bool, Void>(journal: journal,
            validatePlan: { plan in
                guard currentAccountAvailable, plan.identity.session == fixture.session else { throw HanlinHostError.staleContext }
            },
            validateAvailable: { if !currentAccountAvailable { throw HanlinHostError.staleContext } },
            invalidate: { currentAccountAvailable = false },
            prepareDispatch: { _, approved in
                guard approved else { throw HanlinHostError.denied }
            },
            dispatch: { _, _, receipt in
                dispatches += 1
                entered.open()
                await completeNative.wait()
                try await receipt("original-native-object")
            })
        let execution = Task { @MainActor in try await runner.execute(fixture.invocation, approval: true) }
        await entered.wait()
        await runner.cancel(fixture.invocation.request.id)
        currentAccountAvailable = false
        let pending = try #require(runner.receipt(for: fixture.invocation.request.id))
        #expect(pending.effectState == .uncertain)
        let drain = Task { @MainActor in
            drainStarted.open()
            let result = await runner.drainCancelledInvocation(fixture.invocation.request.id)
            drained = true
            return result
        }
        await drainStarted.wait()
        #expect(!drained && dispatches == 1)
        #expect(throws: HanlinHostError.unresolvedWrite) { try runner.validateCreationAvailability() }
        completeNative.open()
        let settled = try #require(await drain.value)
        do { _ = try await execution.value; Issue.record("Revoked account received a business completion") }
        catch { #expect(error as? HanlinHostError == .staleContext || error as? HanlinHostError == .cancelled) }
        #expect(drained && dispatches == 1)
        #expect(settled.context == fixture.session.context && settled.effectState == .confirmedCommitted)
        #expect(settled == settled.metadataReceipt())
        let plan = try PinkhaHanlinCreatePagePlan(invocation: fixture.invocation)
        let saved = try #require(await journal.receipt(for: plan.identity))
        #expect(saved.identity.session == fixture.session && saved.createdObjectReference == "original-native-object")
        #expect(throws: HanlinHostError.staleContext) { try runner.validateCreationAvailability() }
    }

    @Test(.timeLimit(.minutes(1)), arguments: ["anytype", "anytype-any"])
    func committedReceiptDoesNotReleaseAnUnfinishedNativeWorker(app: String) async throws {
        let fixture = try Fixture(app: app)
        defer { try? FileManager.default.removeItem(at: fixture.directory) }
        let journal = try await PinkhaHanlinWriteJournal.openInTestDirectory(fixture.directory,
            namespace: fixture.session.context.namespace)
        let receiptSupplied = Latch(), releaseNativeLease = Latch(), drainStarted = Latch()
        defer { releaseNativeLease.open() }
        var drained = false, dispatches = 0
        let runner = try PinkhaHanlinCreateRunner<Bool, Void>(journal: journal,
            validatePlan: { plan in
                guard plan.identity.session == fixture.session else { throw HanlinHostError.staleContext }
            }, validateAvailable: {}, invalidate: {},
            prepareDispatch: { _, approved in
                guard approved else { throw HanlinHostError.denied }
            },
            dispatch: { _, _, receipt in
                dispatches += 1
                try await receipt("original-native-object")
                receiptSupplied.open()
                // Models the native lease remaining held after its receipt callback.
                await releaseNativeLease.wait()
            })
        let execution = Task { @MainActor in try await runner.execute(fixture.invocation, approval: true) }
        await receiptSupplied.wait()
        let delivered = try await execution.value
        #expect(delivered.effectState == .confirmedCommitted)
        await runner.cancel(fixture.invocation.request.id)
        let drain = Task { @MainActor in
            drainStarted.open()
            let result = await runner.drainCancelledInvocation(fixture.invocation.request.id)
            drained = true
            return result
        }
        await drainStarted.wait()
        #expect(!drained && dispatches == 1)
        #expect(throws: HanlinHostError.unresolvedWrite) { try runner.validateCreationAvailability() }
        releaseNativeLease.open()
        let settled = try #require(await drain.value)
        #expect(settled.effectState == .confirmedCommitted && settled.context == fixture.session.context)
        #expect(drained && dispatches == 1)
        try runner.validateCreationAvailability()
    }

    private struct Fixture {
        let directory: URL
        let session: HanlinHostSession
        let invocation: HanlinHostInvocation
        init(app: String) throws {
            directory = FileManager.default.temporaryDirectory.appendingPathComponent(
                "hanlin-cancellation-drain-" + UUID().uuidString, isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
            session = .init(conversationID: UUID(), context: .init(namespace: try .init(app: app,
                account: "disposable-account", workspace: "disposable-space", space: "disposable-space"),
                sceneID: UUID(), generation: UUID()))
            let id = UUID().uuidString.lowercased()
            invocation = .init(request: .init(id: try .init(validating: id),
                logicalToolID: .init(providerInstanceID: try .init(validating: "anytype.host"),
                    localToolID: try .init(validating: "create-page")),
                aliasUsed: PinkhaHanlinCreatePagePlan.alias, descriptorRevision: try .init(1),
                routingTableRevision: .init(1), arguments: .object(["title": .string("Disposable drain fixture")]),
                origin: .assistantModel, idempotencyKey: id, deadline: Date().addingTimeInterval(20),
                limits: try .init(timeoutMilliseconds: 20_000, maximumOutputBytes: 32_768)),
                session: session, runID: UUID(), step: 0, providerCallID: UUID().uuidString,
                writeGuarantee: .independentObjectCreation)
        }
    }

    @MainActor private final class Latch {
        private var opened = false
        private var waiters: [CheckedContinuation<Void, Never>] = []
        func open() {
            opened = true
            let pending = waiters; waiters.removeAll()
            for waiter in pending { waiter.resume() }
        }
        func wait() async {
            if opened { return }
            await withCheckedContinuation { waiters.append($0) }
        }
    }
}
#endif
