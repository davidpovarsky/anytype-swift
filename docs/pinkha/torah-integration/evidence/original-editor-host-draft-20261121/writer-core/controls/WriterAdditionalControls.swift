import Foundation
import Services
import SwiftProtobuf
@testable import ProtobufMessages

private struct Request: Message { }
private struct Response: Message, ResultWithError {
    struct Error: PortableRPCError {
        enum ErrorCode: Int, Sendable { case null = 0 }
        let code = ErrorCode.null
        var isNull: Bool { true }
    }
    let error = Error()
    let hasEvent: Bool
    var event: Anytype_ResponseEvent { .init(messages: hasEvent ? [1] : []) }
}

private final class NativeBodyProbe: @unchecked Sendable {
    private let lock = NSLock()
    private let semaphore: DispatchSemaphore?
    private var started = 0
    private var waiters: [CheckedContinuation<Void, Never>] = []
    init(held: Bool = false) { semaphore = held ? DispatchSemaphore(value: 0) : nil }
    var count: Int { lock.lock(); defer { lock.unlock() }; return started }
    func run(event: Bool = false) -> Response {
        lock.lock()
        started += 1
        let waiters = waiters
        self.waiters.removeAll()
        lock.unlock()
        for waiter in waiters { waiter.resume() }
        if let semaphore { precondition(semaphore.wait(timeout: .now() + 10) == .success) }
        return Response(hasEvent: event)
    }
    func entered() async {
        await withCheckedContinuation { continuation in
            lock.lock()
            if started > 0 { lock.unlock(); continuation.resume() }
            else { waiters.append(continuation); lock.unlock() }
        }
    }
    func release() { semaphore?.signal() }
    func invoke(_ name: String = "BlockTextSetText", event: Bool = false) async throws {
        _ = try await Invocation(messageName: name, request: Request()) { [self] _ in run(event: event) }.invoke()
    }
}

private actor Hold {
    private var entered = false
    private var released = false
    private var entry: [CheckedContinuation<Void, Never>] = []
    private var release: [CheckedContinuation<Void, Never>] = []
    func pause() async {
        entered = true
        let current = entry; entry.removeAll()
        for waiter in current { waiter.resume() }
        if !released { await withCheckedContinuation { release.append($0) } }
    }
    func wait() async {
        if !entered { await withCheckedContinuation { entry.append($0) } }
    }
    func resume() {
        released = true
        let current = release; release.removeAll()
        for waiter in current { waiter.resume() }
    }
}

private final class BindingCapture: InvocationMesagesHandlerProtocol, @unchecked Sendable {
    private let lock = NSLock()
    private var stored: InvocationDispatchBinding?
    let isLogEnabled = false
    func save(_ binding: InvocationDispatchBinding?) { lock.lock(); stored = binding; lock.unlock() }
    var value: InvocationDispatchBinding? { lock.lock(); defer { lock.unlock() }; return stored }
    func eventHandler(event: Anytype_ResponseEvent) async { save(InvocationDispatchContext.binding) }
    func logHandler(message: InvocationMessage) { }
    func assertationHandler(message: String, domain: String, info: [String: String], file: StaticString, function: String, line: UInt) { }
}

private actor EventOutcome {
    private(set) var rejected = 0
    func invoke(_ probe: NativeBodyProbe) async {
        do { try await probe.invoke("ObjectShow") }
        catch { precondition(error as? EditorDocumentWriteError == .rejected(.retired)); rejected += 1 }
    }
}

@main
private struct WriterAdditionalControls {
    @MainActor
    static func makeOwner(source: EditorDocumentWriteLifetime = .init(), account: EditorDocumentWriteLifetime = .init()) throws
        -> (EditorDocumentWriteOwner, PortableDocument) {
        let document = PortableDocument()
        let binding = try EditorDocumentWriteSourceBinding(lifetime: source, accountLifetime: account, isCurrent: { true })
        return (try EditorDocumentWriteOwner(
            data: .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode),
            lifetimeDocument: document, sourceBinding: binding
        ), document)
    }

    @MainActor
    static func main() async throws {
        var passed: [String] = []
        do {
            let (owner, actual) = try makeOwner()
            try owner.validateDocument(actual)
            var rejection: EditorDocumentWriteError?
            do { try owner.validateDocument(PortableDocument()) }
            catch { rejection = error as? EditorDocumentWriteError }
            precondition(rejection == .rejected(.wrongContext))
            passed.append("same-value identities cannot substitute another actual prepared document instance")
        }
        do {
            let (owner, _) = try makeOwner()
            var writes = 0
            var rejection: EditorDocumentWriteError?
            do { try owner.performSynchronousOperation(spaceId: "foreign-space") { writes += 1 } }
            catch { rejection = error as? EditorDocumentWriteError }
            precondition(rejection == .rejected(.wrongContext) && writes == 0)
            try owner.performSynchronousOperation(spaceId: "owned-space") { writes += 1 }
            precondition(writes == 1 && owner.isDrained)
            let probe = NativeBodyProbe()
            do {
                try await owner.performRead(spaceId: "foreign-space", rpcNames: ["ObjectShow"]) { try await probe.invoke("ObjectShow") }
                preconditionFailure("foreign Space read was admitted")
            } catch { precondition(error as? EditorDocumentWriteError == .rejected(.wrongContext)) }
            precondition(probe.count == 0)
            passed.append("new synchronous and read Space conveniences preserve the original exact owned-Space boundary")
        }
        do {
            let (owner, _) = try makeOwner(), probe = NativeBodyProbe()
            let child = try owner.childSourceBinding()
            owner.retire()
            do {
                try await child.performOperation(rpcNames: ["ObjectOpen"]) { try await probe.invoke("ObjectOpen") }
                preconditionFailure("retired parent granted child open")
            } catch { precondition(error as? EditorDocumentWriteError == .rejected(.retired)) }
            precondition(probe.count == 0)
            passed.append("selected child source binding is transitively retired with its exact parent owner")
        }
        do {
            let account = EditorDocumentWriteLifetime(), source = EditorDocumentWriteLifetime()
            let (owner, _) = try makeOwner(source: source, account: account), probe = NativeBodyProbe()
            let child = try owner.childSourceBinding()
            account.markUnavailable(); account.confirmOpened()
            precondition(account.token() != nil)
            do {
                try await child.performOperation(rpcNames: ["ObjectOpen"]) { try await probe.invoke("ObjectOpen") }
                preconditionFailure("child captured a newer account generation")
            } catch { precondition(error as? EditorDocumentWriteError == .rejected(.retired)) }
            precondition(probe.count == 0)
            passed.append("child source binding never recaptures authority after a matching account is reopened")
        }
        do {
            let account = EditorDocumentWriteLifetime(), source = EditorDocumentWriteLifetime()
            let (owner, _) = try makeOwner(source: source, account: account)
            let boundProbe = NativeBodyProbe(), unboundProbe = NativeBodyProbe(), outcome = EventOutcome()
            let token = try await owner.performRead(rpcNames: []) {
                await EventBunchSubscribtion.default.addHandlerAwaiting { _ in await outcome.invoke(boundProbe) }
            }
            defer { token.cancel() }
            owner.retire(); source.markUnavailable()
            await EventsBunch(contextId: "owned", localEvents: [.general]).send()
            precondition(boundProbe.count == 1)
            account.markUnavailable(); account.confirmOpened()
            await EventsBunch(contextId: "owned", localEvents: [.general]).send()
            let rejected = await outcome.rejected
            precondition(boundProbe.count == 1 && rejected == 1)
            passed.append("actual original subscriber retains account-only authority across later unbound push delivery and refuses an account switch")
            let unbound = await EventBunchSubscribtion.default.addHandlerAwaiting { _ in try? await unboundProbe.invoke("ObjectShow") }
            defer { unbound.cancel() }
            await EventsBunch(contextId: "owned", localEvents: [.general]).send()
            precondition(unboundProbe.count == 1 && boundProbe.count == 1)
            passed.append("original unbound event subscribers keep their existing dispatch behavior")
        }
        let report: [String: Any] = ["status": "PORTABLE_ORIGINAL_WRITER_ADDITIONS_PASS", "executed": passed.count,
            "passed": passed.count, "controls": passed, "previous_core_14": "REUSED_FROM_V3_NOT_RERUN",
            "native_rpc_or_account_calls": 0, "apple_native": "NOT_RUN", "editable_host": "NOT_RUN"]
        print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), encoding: .utf8)!)
    }
}

