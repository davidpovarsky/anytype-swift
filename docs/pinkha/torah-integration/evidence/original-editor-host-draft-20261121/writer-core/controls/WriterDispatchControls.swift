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

@main
private struct WriterDispatchControls {
    @MainActor private static var passed: [String] = []

    @MainActor
    private static func owner(
        source: EditorDocumentWriteLifetime = .init(),
        account: EditorDocumentWriteLifetime = .init(),
        onDrained: (@MainActor () -> Void)? = nil
    ) throws -> EditorDocumentWriteOwner {
        let document = PortableDocument()
        let binding = try EditorDocumentWriteSourceBinding(lifetime: source, accountLifetime: account, isCurrent: { true })
        return try EditorDocumentWriteOwner(
            data: .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode),
            lifetimeDocument: document, sourceBinding: binding, onDrained: onDrained
        )
    }

    @MainActor
    private static func failure(_ operation: () async throws -> Void) async -> (any Swift.Error)? {
        do { try await operation(); return nil } catch { return error }
    }

    @MainActor
    private static func eventually(_ check: () -> Bool) async throws {
        for _ in 0..<400 {
            if check() { return }
            try await Task.sleep(nanoseconds: 5_000_000)
        }
        preconditionFailure("A held native probe did not drain")
    }

    @MainActor
    static func main() async throws {
        do {
            let probe = NativeBodyProbe()
            try await probe.invoke()
            precondition(probe.count == 1)
            passed.append("original unbound Invocation reaches its unchanged synchronous body")
        }
        do {
            let source = EditorDocumentWriteLifetime(), gate = Hold(), probe = NativeBodyProbe()
            let owner = try owner(source: source)
            let task = Task { @MainActor in
                await failure {
                    try await owner.performMutation(contextId: "owned") {
                        await gate.pause()
                        try await probe.invoke()
                    }
                }
            }
            await gate.wait(); source.markUnavailable(); await gate.resume()
            let error = await task.value as? EditorDocumentWriteError
            precondition(error == .rejected(.retired) && probe.count == 0 && owner.isDrained)
            passed.append("retirement during service await refuses original RPC dispatch")
        }
        do {
            let source = EditorDocumentWriteLifetime(), gate = Hold(), probe = NativeBodyProbe()
            let owner = try owner(source: source)
            let task = Task { @MainActor in
                await failure {
                    try await owner.performMutation(contextId: "owned") {
                        let original = InvocationDispatchContext.binding!
                        let held = InvocationDispatchBinding { name in
                            let permit = try await original.prepare(messageName: name)
                            await gate.pause()
                            return permit
                        }
                        try await InvocationDispatchContext.$binding.withValue(held) { try await probe.invoke() }
                    }
                }
            }
            await gate.wait(); source.markUnavailable(); await gate.resume()
            let error = await task.value as? EditorDocumentWriteError
            precondition(error == .rejected(.retired) && probe.count == 0 && owner.isDrained)
            passed.append("source retired after actor preparation is refused inside actual GCD dispatch")
        }
        do {
            let probe = NativeBodyProbe(held: true)
            var drained = 0
            let owner = try owner(onDrained: { drained += 1 })
            let task = Task { @MainActor in
                await failure { try await owner.performMutation(contextId: "owned") { try await probe.invoke() } }
            }
            await probe.entered(); task.cancel()
            let error = await task.value
            owner.retire()
            precondition(error is CancellationError && owner.pendingOperationCount == 1 && drained == 0 && probe.count == 1)
            probe.release()
            try await eventually { owner.isDrained }
            precondition(drained == 1 && probe.count == 1)
            passed.append("caller cancellation cannot drain an actually running GCD RPC; completion drains once")
        }
        do {
            let owner = try owner(), capture = BindingCapture(), probe = NativeBodyProbe()
            try await owner.performMutation(contextId: "owned") { capture.save(InvocationDispatchContext.binding) }
            precondition(owner.isDrained)
            let error = await failure {
                try await InvocationDispatchContext.$binding.withValue(capture.value) { try await probe.invoke() }
            } as? EditorDocumentWriteError
            precondition(error == .rejected(.invalidLease) && probe.count == 0)
            passed.append("a completed outer operation cannot lend its captured dispatch binding to a later task")
        }
        do {
            let owner = try owner(), probe = NativeBodyProbe()
            let error = await failure {
                try await owner.performRead(contextId: "owned", spaceId: "owned-space", rpcNames: ["ObjectListExport"]) {
                    try await probe.invoke("ObjectSetDetails")
                }
            } as? EditorDocumentWriteError
            precondition(error == .rejected(.unqualifiedDispatch) && probe.count == 0)
            passed.append("read capability cannot dispatch an undeclared write command")
        }
        do {
            let source = EditorDocumentWriteLifetime(), account = EditorDocumentWriteLifetime()
            let owner = try owner(source: source, account: account), capture = BindingCapture(), probe = NativeBodyProbe()
            InvocationSettings.handler = capture
            try await owner.performMutation(contextId: "owned") { try await probe.invoke(event: true) }
            InvocationSettings.handler = nil
            precondition(capture.value != nil && owner.isDrained)
            source.markUnavailable()
            try await InvocationDispatchContext.$binding.withValue(capture.value) { try await probe.invoke("ObjectShow") }
            account.markUnavailable()
            let error = await failure {
                try await InvocationDispatchContext.$binding.withValue(capture.value) { try await probe.invoke("ObjectShow") }
            } as? EditorDocumentWriteError
            precondition(error == .rejected(.retired) && probe.count == 2)
            passed.append("committed-event RPCs retain frozen account scope without an expired document operation")
        }
        do {
            let manager = AccountManager()
            manager.account = AccountData(id: "same-account")
            let lifetime = manager.editorWriteLifetime!, original = lifetime.token()!
            let transition = EditorAccountWriteTransition(lifetime: lifetime, rpcNames: ["AccountSelect"])
            manager.account = AccountData(id: "same-account")
            precondition(lifetime.token() == nil && !lifetime.isCurrent(original))
            transition.finish { manager.account.id == "same-account" }
            precondition(lifetime.token() != nil && !lifetime.isCurrent(original))
            transition.finish()
            precondition(lifetime.token() != nil)
            passed.append("actual account setter cannot reopen during transition or revive an old same-ID token")
        }
        do {
            let manager = AccountManager(), probe = NativeBodyProbe(held: true)
            manager.account = AccountData(id: "old-account")
            let lifetime = manager.editorWriteLifetime!
            let transition = EditorAccountWriteTransition(lifetime: lifetime, rpcNames: ["AccountSelect"])
            let task = Task { @MainActor in
                defer { transition.finish() }
                return await failure {
                    try await InvocationDispatchContext.$binding.withValue(transition.binding) {
                        try await probe.invoke("AccountSelect")
                    }
                }
            }
            await probe.entered(); task.cancel()
            let error = await task.value
            manager.account = AccountData(id: "new-account")
            precondition(error is CancellationError && lifetime.token() == nil)
            probe.release()
            try await Task.sleep(nanoseconds: 100_000_000)
            precondition(lifetime.token() == nil)
            manager.account = AccountData(id: "verified-later-account")
            precondition(lifetime.token() != nil)
            passed.append("cancelled account caller keeps closing fence through actual native completion and never auto-reopens")
        }
        do {
            let account = EditorDocumentWriteLifetime(), source = EditorDocumentWriteLifetime(), probe = NativeBodyProbe()
            let binding = try EditorDocumentWriteSourceBinding(lifetime: source, accountLifetime: account, isCurrent: { true })
            let transition = EditorAccountWriteTransition(lifetime: account, rpcNames: ["AccountSelect"])
            transition.finish { true }
            let error = await failure {
                try await binding.performRead(rpcNames: ["ObjectOpen"]) { try await probe.invoke("ObjectOpen") }
            } as? EditorDocumentWriteError
            precondition(error == .rejected(.retired) && probe.count == 0)
            passed.append("pre-open binding reuses its original account token instead of recapturing a later generation")
        }
        do {
            let owner = try owner(), probe = NativeBodyProbe()
            let first = await failure {
                try await owner.performMutation(spaceId: "other-space") { try await probe.invoke("FileUpload") }
            } as? EditorDocumentWriteError
            let second = await failure {
                try await owner.performMutation(spaceId: "owned-space", createdInContext: "other-object") {
                    try await probe.invoke("ObjectCreateBookmark")
                }
            } as? EditorDocumentWriteError
            precondition(first == .rejected(.wrongContext) && second == .rejected(.wrongContext) && probe.count == 0)
            passed.append("space-only original creation APIs still require exact owned Space and optional document identity")
        }
        do {
            let account = EditorDocumentWriteLifetime(), writer = try owner(account: account)
            let oldRPC = NativeBodyProbe(held: true), accountRPC = NativeBodyProbe(), attempted = Hold()
            let writing = Task { @MainActor in
                await failure { try await writer.performMutation(contextId: "owned") { try await oldRPC.invoke() } }
            }
            await oldRPC.entered()
            let transition = EditorAccountWriteTransition(lifetime: account, rpcNames: ["AccountSelect"])
            await attempted.resume()
            let observed = InvocationDispatchBinding { name in
                await attempted.pause()
                return try await transition.binding.prepare(messageName: name)
            }
            let switching = Task {
                defer { transition.finish() }
                try await InvocationDispatchContext.$binding.withValue(observed) { try await accountRPC.invoke("AccountSelect") }
            }
            await attempted.wait()
            try await Task.sleep(nanoseconds: 50_000_000)
            precondition(accountRPC.count == 0 && oldRPC.count == 1 && account.token() == nil)
            oldRPC.release()
            _ = await writing.value
            try await switching.value
            precondition(accountRPC.count == 1 && account.token() == nil)
            passed.append("pre-account transition drains admitted old-account native calls before its original RPC begins")
        }
        do {
            let owner = try owner(), probe = NativeBodyProbe(held: true)
            var operationDrained = 0
            let task = Task { @MainActor in
                await failure {
                    try await owner.performMutation(contextId: "owned", onDrained: { operationDrained += 1 }) {
                        try await probe.invoke()
                    }
                }
            }
            await probe.entered(); task.cancel(); _ = await task.value
            precondition(operationDrained == 0 && owner.pendingOperationCount == 1 && !owner.isRetired)
            probe.release()
            try await eventually { operationDrained == 1 }
            precondition(owner.isDrained && !owner.isRetired)
            passed.append("per-operation cleanup notification waits for native completion without requiring owner retirement")
        }
        do {
            let source = EditorDocumentWriteLifetime(), owner = try owner(source: source)
            var publications = 0
            try owner.performSynchronousOperation(requiresEditing: false) {
                precondition(owner.pendingOperationCount == 1)
                publications += 1
            }
            var completedError: EditorDocumentWriteError?
            do {
                try owner.performSynchronousOperation {
                    publications += 1
                    source.markUnavailable()
                }
            } catch { completedError = error as? EditorDocumentWriteError }
            var rejected: EditorDocumentWriteError?
            do { try owner.performSynchronousOperation { publications += 1 } }
            catch { rejected = error as? EditorDocumentWriteError }
            precondition(publications == 2 && completedError == .completedWithoutOwnership(.retired)
                         && rejected == .rejected(.retired) && owner.isDrained)
            passed.append("synchronous preparation/publication uses the original lease and both ownership checks")
        }
        let report: [String: Any] = ["status": "PORTABLE_ORIGINAL_DISPATCH_CONTROLS_PASS", "executed": passed.count,
            "passed": passed.count, "controls": passed, "native_rpc_or_account_calls": 0,
            "apple_native": "NOT_RUN", "editable_host": "NOT_RUN",
            "scope": "Actual Invocation, owner, lifetime, operation, account transition and setter; explicit type probes and portable lock substitution only"]
        print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
