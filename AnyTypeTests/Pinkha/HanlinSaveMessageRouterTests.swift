@testable import PinkhaHanlinCore
import Foundation
import Testing
import HanlinHostContracts
import HanlinPlatformContracts

#if DEBUG
/// The real router/read adapter with controlled write delegates. These prove
/// dispatch identity, replay and lifetime routing, not native body persistence.
@Suite("Hanlin save-message routing and original worker ownership", .serialized)
@MainActor
struct HanlinSaveMessageRouterTests {
    @Test func absentBodyBindingNeverRoutesSaveToTitleOnlyCreation() async throws {
        let access = try access()
        let creation = Binding(tool: try PinkhaHanlinCreatePageTool.make())
        let router = try router(access, create: creation, save: nil)
        let catalog = try await router.catalog(for: access.session.context)
        #expect(!catalog.tools.contains { $0.route.alias == PinkhaHanlinSaveMessagePlan.alias })
        let request = try invocation(access.session)
        _ = try PinkhaHanlinSaveMessagePlan(invocation: request)
        let result = try await router.execute(request) { _ in }
        #expect(result.effectState == .notDispatched)
        #expect(creation.invocations.isEmpty && access.reads == 0)
        #expect(router.metadataReceipt(for: request.request.id) == nil)
    }

    @Test(arguments: [false, true])
    func bindingsCannotAdvertiseTheOtherWriteRoute(saveMisrouted: Bool) async throws {
        let access = try access()
        let mismatchedTool = try (saveMisrouted ? PinkhaHanlinCreatePageTool.make() : PinkhaHanlinSaveMessageTool.make())
        let creation = Binding(tool: mismatchedTool)
        let save = Binding(tool: mismatchedTool)
        let router = try router(access, create: creation, save: save)
        do {
            _ = try await router.catalog(for: access.session.context)
            Issue.record("A binding exposed the other write route")
        } catch HanlinHostError.resultMismatch {}
        #expect(creation.invocations.isEmpty && save.invocations.isEmpty)
    }

    @Test func exactBodyReplayAndCrossRouteProviderIdentityStayBoundAfterCapabilityLoss() async throws {
        let access = try access()
        let creation = Binding(tool: try PinkhaHanlinCreatePageTool.make())
        let save = Binding(tool: try PinkhaHanlinSaveMessageTool.make())
        let router = try router(access, create: creation, save: save)
        let body = "# כותרת\n\n**גוף מלא** e\u{301}\n\n```swift\nlet x = 1\n```"
        let request = try invocation(access.session, markdown: body)
        _ = try await router.execute(request) { _ in }
        let delegated = try #require(save.invocations.first)
        #expect(delegated.resultID == request.resultID && delegated.runID == request.runID)
        #expect(delegated.session == request.session && delegated.providerCallID == request.providerCallID)
        #expect(delegated.request == request.request && delegated.step == request.step)
        #expect(delegated.originalArgumentsJSON == request.originalArgumentsJSON)
        #expect(try PinkhaHanlinSaveMessagePlan(invocation: delegated).markdown.utf8.elementsEqual(body.utf8))
        save.available = false
        do { _ = try await router.execute(request) { _ in }; Issue.record("Exact save replay dispatched twice") }
        catch HanlinHostError.duplicateInvocation {}
        let changed = try invocation(access.session, id: request.request.id.rawValue,
            run: request.runID, provider: request.providerCallID, markdown: body + "changed",
            deadline: request.request.deadline)
        do { _ = try await router.execute(changed) { _ in }; Issue.record("Changed save body reused identity") }
        catch HanlinHostError.idempotencyConflict {}
        let reminted = try HanlinHostWriteTests().invocation(session: access.session,
            run: request.runID, provider: request.providerCallID)
        do { _ = try await router.execute(reminted) { _ in }; Issue.record("Save identity reminted as title-only create") }
        catch HanlinHostError.idempotencyConflict {}
        #expect(save.invocations.count == 1 && creation.invocations.isEmpty && access.reads == 0)
    }

    @Test func invalidOrOversizedBodyNeverReachesEitherWriteDelegate() async throws {
        let access = try access()
        let creation = Binding(tool: try PinkhaHanlinCreatePageTool.make())
        let save = Binding(tool: try PinkhaHanlinSaveMessageTool.make())
        let router = try router(access, create: creation, save: save)
        let invalid: [HanlinJSONValue] = [
            .object(["title": .string("Title")]),
            .object(["title": .string("Title"), "markdown": .string("")]),
            .object(["title": .string("Title"), "markdown": .string(String(repeating: "א", count: 32_769))]),
            .object(["title": .string("Title"), "markdown": .string("Body"), "space": .string("foreign")])
        ]
        for arguments in invalid {
            let request = try invocation(access.session, arguments: arguments)
            let result = try await router.execute(request) { _ in }
            #expect(result.effectState == .notDispatched)
        }
        #expect(save.invocations.isEmpty && creation.invocations.isEmpty && access.reads == 0)
    }

    @Test(.timeLimit(.minutes(1)), arguments: [false, true])
    func cancelOrInvalidateJoinsOnlyOriginalSaveWorkerAfterAccountChange(invalidate: Bool) async throws {
        let access = try access()
        let creation = Binding(tool: try PinkhaHanlinCreatePageTool.make())
        let save = Binding(tool: try PinkhaHanlinSaveMessageTool.make(), holdExecution: true)
        let router = try router(access, create: creation, save: save)
        let request = try invocation(access.session)
        defer { save.releaseExecution() }
        let execution = Task { @MainActor in try await router.execute(request) { _ in } }
        await save.entered.wait()
        access.current = try HanlinHostAdapterTests().context(account: "other-account",
            scene: access.session.context.sceneID, generation: access.session.context.generation)
        var joined = false
        let drain = Task { @MainActor in
            if invalidate { await router.invalidate() }
            else { await router.cancel(request.request.id) }
            let result = await router.drainCancelledInvocation(request.request.id)
            joined = true
            return result
        }
        await save.drainEntered.wait()
        #expect(!joined)
        #expect(save.fence?.isRevoked == true)
        #expect(save.cancelled == [request.request.id] && creation.cancelled.isEmpty)
        save.releaseExecution()
        let metadata = try #require(await drain.value)
        do { _ = try await execution.value; Issue.record("Foreign account received a save completion") }
        catch { #expect(error as? HanlinHostError == .staleContext || error as? HanlinHostError == .cancelled) }
        #expect(joined && save.invocations.count == 1)
        #expect(metadata.context == request.session.context && metadata.effectState == .uncertain)
        #expect(metadata == metadata.metadataReceipt())
        #expect(creation.invocations.isEmpty && access.reads == 0)
    }

    @Test(.timeLimit(.minutes(1)))
    func accountChangeDuringSaveReadinessPreventsRouteClaim() async throws {
        let access = try access()
        let save = Binding(tool: try PinkhaHanlinSaveMessageTool.make(), holdCatalog: true)
        let router = try router(access, create: nil, save: save)
        let request = try invocation(access.session)
        defer { save.releaseCatalog() }
        let execution = Task { @MainActor in try await router.execute(request) { _ in } }
        await save.catalogEntered.wait()
        access.current = try HanlinHostAdapterTests().context(account: "other-account",
            scene: access.session.context.sceneID, generation: access.session.context.generation)
        save.releaseCatalog()
        let result = try await execution.value
        #expect(result.effectState == .notDispatched)
        #expect(save.invocations.isEmpty && router.metadataReceipt(for: request.request.id) == nil)
        #expect(access.reads == 0)
    }

    private func access() throws -> HanlinHostAdapterTests.Access {
        .init(context: try HanlinHostAdapterTests().context())
    }

    private func router(_ access: HanlinHostAdapterTests.Access, create: Binding?, save: Binding?) throws -> PinkhaHanlinHostRouter {
        try .init(read: PinkhaHanlinHostAdapter(access: access), session: access.session,
                  write: create, saveMessage: save)
    }

    private func invocation(_ session: HanlinHostSession, id: String = UUID().uuidString.lowercased(),
                            run: UUID = UUID(), provider: String = UUID().uuidString,
                            markdown: String = "Complete message", deadline: Date? = nil,
                            arguments: HanlinJSONValue? = nil) throws -> HanlinHostInvocation {
        .init(request: .init(id: try .init(validating: id),
            logicalToolID: .init(providerInstanceID: try .init(validating: "anytype.host"),
                                localToolID: try .init(validating: "save-message")),
            aliasUsed: PinkhaHanlinSaveMessagePlan.alias, descriptorRevision: try .init(1), routingTableRevision: .init(1),
            arguments: arguments ?? .object(["title": .string("Title"), "markdown": .string(markdown)]),
            origin: .assistantModel, deadline: deadline ?? Date().addingTimeInterval(20),
            limits: try .init(timeoutMilliseconds: 20_000, maximumOutputBytes: 32_768)),
            session: session, runID: run, step: 0, providerCallID: provider, writeGuarantee: .independentObjectCreation)
    }

    @MainActor private final class Binding: PinkhaHanlinWriteBinding {
        let tool: HanlinHostTool
        var missingInstallation: [PinkhaHanlinWriteInstallationRequirement] { [] }
        var available = true
        var invocations: [HanlinHostInvocation] = []
        var cancelled: [HanlinToolInvocationID] = []
        var fence: PinkhaHanlinRevocationFence?
        let entered = Gate(), drainEntered = Gate(), catalogEntered = Gate()
        private let executionRelease: Gate, catalogRelease: Gate, ended = Gate()
        private var result: HanlinHostExecutionResult?

        init(tool: HanlinHostTool, holdExecution: Bool = false, holdCatalog: Bool = false) {
            self.tool = tool
            executionRelease = .init(opened: !holdExecution)
            catalogRelease = .init(opened: !holdCatalog)
        }
        func observeInvalidation(_ callback: @escaping @MainActor () -> Void) {}
        func catalogTool() async throws -> HanlinHostTool? {
            catalogEntered.open()
            await catalogRelease.wait()
            return available ? tool : nil
        }
        func execute(_ invocation: HanlinHostInvocation, cancellation: PinkhaHanlinRevocationFence,
                     progress: @escaping HanlinHostProgressHandler) async throws -> HanlinHostExecutionResult {
            invocations.append(invocation); fence = cancellation
            entered.open()
            await executionRelease.wait()
            let outcome = HanlinHostExecutionResult(result: .init(invocationID: invocation.request.id,
                logicalToolID: invocation.request.logicalToolID,
                outcome: .failed(.init(code: .operationUnavailable, userMessage: "Controlled router delegate")), completedAt: .now),
                effectState: cancellation.isRevoked ? .uncertain : .notDispatched, context: invocation.session.context)
            result = outcome
            ended.open()
            return outcome
        }
        func cancel(_ id: HanlinToolInvocationID) async { cancelled.append(id) }
        func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult? {
            guard invocations.contains(where: { $0.request.id == id }) else { return nil }
            drainEntered.open()
            await ended.wait()
            return result?.metadataReceipt()
        }
        func invalidate() { available = false }
        func requestContextReadConsent() async throws {}
        func metadataReceipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? {
            guard result?.result.invocationID == id else { return nil }
            return result?.metadataReceipt()
        }
        func releaseExecution() { executionRelease.open() }
        func releaseCatalog() { catalogRelease.open() }
    }

    @MainActor private final class Gate {
        private var opened: Bool
        private var waiters: [CheckedContinuation<Void, Never>] = []
        init(opened: Bool = false) { self.opened = opened }
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
