import Foundation
import Services
import SwiftProtobuf
@testable import ProtobufMessages

private struct Request: Message { }
private struct Response: Message, ResultWithError {
    struct Error: PortableRPCError {
        enum ErrorCode: Int, Sendable { case null = 0, failure = 1 }
        let code: ErrorCode
        var isNull: Bool { code == .null }
    }
    let error: Error
    let hasEvent = false
    var event: Anytype_ResponseEvent { .init() }
}
private enum PreparationFailure: Swift.Error { case refused }

private final class NativeBodyProbe: @unchecked Sendable {
    private let lock = NSLock()
    private let semaphore: DispatchSemaphore?
    private let fails: Bool
    private var started = 0
    private var waiters: [CheckedContinuation<Void, Never>] = []
    init(held: Bool = false, fails: Bool = false) {
        semaphore = held ? DispatchSemaphore(value: 0) : nil
        self.fails = fails
    }
    var count: Int { lock.lock(); defer { lock.unlock() }; return started }
    func run() -> Response {
        lock.lock(); started += 1
        let waiters = waiters; self.waiters.removeAll(); lock.unlock()
        for waiter in waiters { waiter.resume() }
        if let semaphore { precondition(semaphore.wait(timeout: .now() + 10) == .success) }
        return Response(error: .init(code: fails ? .failure : .null))
    }
    func entered() async {
        await withCheckedContinuation { continuation in
            lock.lock()
            if started > 0 { lock.unlock(); continuation.resume() }
            else { waiters.append(continuation); lock.unlock() }
        }
    }
    func release() { semaphore?.signal() }
    func invoke(_ name: String = "BlockTextSetText") async throws {
        _ = try await Invocation(messageName: name, request: Request()) { [self] _ in run() }.invoke()
    }
}

private actor Hold {
    private var entered = false, released = false
    private var entry: [CheckedContinuation<Void, Never>] = []
    private var release: [CheckedContinuation<Void, Never>] = []
    var didEnter: Bool { entered }
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

private final class BarrierDocument: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, Sendable {
    let objectId: String
    let spaceId = "owned-space"
    let mode = DocumentMode.handling
    let isOpened = true, isLocked = false
    let permissions = PortablePermissions()
    let editorWriteLifetime = EditorDocumentWriteLifetime()
    init(_ id: String = "owned") { objectId = id }
}

@main
private struct WriterBarrierControls {
    @MainActor private static var passed: [String] = []

    @MainActor
    private static func owner(source: EditorDocumentWriteLifetime = .init()) throws -> EditorDocumentWriteOwner {
        let document = BarrierDocument()
        let binding = try EditorDocumentWriteSourceBinding(lifetime: source, accountLifetime: .init(), isCurrent: { true })
        return try EditorDocumentWriteOwner(data: .init(objectId: "owned", spaceId: "owned-space", mode: .handling),
                                            lifetimeDocument: document, sourceBinding: binding)
    }

    @MainActor
    private static func child(_ parent: EditorDocumentWriteOwner) throws -> EditorDocumentWriteOwner {
        try EditorDocumentWriteOwner(data: .init(objectId: "child", spaceId: "owned-space", mode: .handling),
            lifetimeDocument: BarrierDocument("child"), sourceBinding: parent.childSourceBinding())
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
        preconditionFailure("Registered original work did not reach its explicit boundary")
    }

    @MainActor
    private static func capture(_ owner: EditorDocumentWriteOwner, probe: NativeBodyProbe = .init(),
                                terminal: Bool = false) async throws {
        try await owner.withExclusiveRead(contextId: "owned", spaceId: "owned-space",
                                          rpcNames: ["ObjectListExport"], retireOnSuccess: terminal) {
            try await probe.invoke("ObjectListExport")
        }
    }

    @MainActor
    private static func expectFailedWrite(_ owner: EditorDocumentWriteOwner) async {
        let probe = NativeBodyProbe()
        let error = await failure { try await capture(owner, probe: probe) } as? EditorDocumentWriteError
        precondition(error == .rejected(.failedWrite) && probe.count == 0)
    }

    @MainActor
    static func main() async throws {
        do {
            let owner = try owner(), gate = Hold(), edit = NativeBodyProbe(), export = NativeBodyProbe()
            let writing = scheduleOriginalEditorMutation(owner: owner, contextId: "owned") {
                await gate.pause(); try await edit.invoke()
            }
            // Same UI call stack, before the scheduled MainActor Task can begin.
            precondition(owner.pendingOperationCount == 1)
            let saving = Task { @MainActor in try await capture(owner, probe: export) }
            await gate.wait(); try await eventually { owner.isCapturing }
            precondition(export.count == 0)
            await gate.resume(); try await writing.value; try await saving.value
            precondition(edit.count == 1 && export.count == 1 && owner.isDrained)
            passed.append("actual UI helper reserves before Task creation and capture waits for that registered edit")
        }
        do {
            let owner = try owner(), gate = Hold(), edit = NativeBodyProbe(), export = NativeBodyProbe()
            let registered = try owner.scheduleMutation(contextId: "owned")
            let writing = Task { @MainActor in
                try await registered.run {
                    await gate.pause()
                    return try await MainActor.run { try owner.scheduleMutation(contextId: "owned") }
                }
            }
            await gate.wait()
            let saving = Task { @MainActor in try await capture(owner, probe: export) }
            try await eventually { owner.isCapturing }; await gate.resume()
            let descendant = try await writing.value
            precondition(owner.pendingOperationCount == 1 && export.count == 0)
            try await descendant.run { try await edit.invoke() }
            try await saving.value
            precondition(edit.count == 1 && export.count == 1)
            passed.append("registered descendant may be queued during capture and outlive its already-finished parent task")
        }
        do {
            let owner = try owner(), edit = NativeBodyProbe(held: true), export = NativeBodyProbe()
            let writing = scheduleOriginalEditorMutation(owner: owner, contextId: "owned") { try await edit.invoke() }
            await edit.entered(); writing.cancel()
            let editError = await failure { try await writing.value }
            precondition(editError is CancellationError && owner.pendingOperationCount == 1)
            let saving = Task { @MainActor in await failure { try await capture(owner, probe: export) } }
            try await eventually { owner.isCapturing }
            precondition(export.count == 0 && owner.pendingOperationCount == 1)
            edit.release()
            let error = await saving.value as? EditorDocumentWriteError
            precondition(error == .rejected(.failedWrite) && export.count == 0 && owner.isDrained)
            passed.append("cancelled UI caller cannot drain its live GCD body or yield a successful snapshot")
        }
        do {
            let owner = try owner(), edit = NativeBodyProbe(fails: true)
            let writing = scheduleOriginalEditorMutation(owner: owner, contextId: "owned") { _ = try? await edit.invoke() }
            try await writing.value
            precondition(edit.count == 1 && owner.isDrained)
            await expectFailedWrite(owner)
            passed.append("original native response error remains sticky when its UI closure catches it")
        }
        do {
            let owner = try owner()
            let writing = scheduleOriginalEditorMutation(owner: owner, contextId: "owned") {
                _ = try? owner.performSynchronousOperation(requiresEditing: false) { throw PreparationFailure.refused }
            }
            try await writing.value
            await expectFailedWrite(owner)
            passed.append("caught synchronous file-preparation error inside registered edit prevents successful capture")
        }
        do {
            let owner = try owner(), export = NativeBodyProbe(held: true), edit = NativeBodyProbe()
            let saving = Task { @MainActor in await failure { try await capture(owner, probe: export) } }
            await export.entered()
            let writing = scheduleOriginalEditorMutation(owner: owner, contextId: "owned") { try await edit.invoke() }
            let error = await failure { try await writing.value } as? EditorDocumentWriteError
            precondition(error == .rejected(.captureInProgress) && edit.count == 0)
            export.release()
            let saveError = await saving.value as? EditorDocumentWriteError
            precondition(saveError == .rejected(.failedWrite) && !owner.isRetired && owner.isDrained)
            passed.append("fresh UI write is refused during export and cannot silently save the previous content")
        }
        do {
            let owner = try owner(), export = NativeBodyProbe(held: true)
            let saving = Task { @MainActor in try await capture(owner, probe: export) }
            await export.entered(); saving.cancel()
            let error = await failure { try await saving.value }
            precondition(error is CancellationError && owner.isCapturing && owner.pendingOperationCount == 1)
            let duplicate = await failure { try await capture(owner) } as? EditorDocumentWriteError
            precondition(duplicate == .rejected(.captureInProgress))
            export.release(); try await eventually { owner.isDrained && !owner.isCapturing }
            precondition(!owner.isRetired)
            passed.append("cancelled export retains the exclusive gate until its actual native body drains")
        }
        do {
            let source = EditorDocumentWriteLifetime(), owner = try owner(source: source), export = NativeBodyProbe()
            let scheduled = try owner.scheduleMutation(contextId: "owned")
            let saving = Task { @MainActor in await failure { try await capture(owner, probe: export) } }
            try await eventually { owner.isCapturing }; source.markUnavailable()
            let error = await saving.value as? EditorDocumentWriteError
            precondition(error == .rejected(.retired) && export.count == 0)
            _ = await failure { try await scheduled.run {} }
            precondition(owner.isDrained && !owner.isCapturing && owner.isRetired)
            passed.append("source retirement wakes a waiting capture without executing export or reviving a queued edit")
        }
        do {
            let owner = try owner(), export = NativeBodyProbe()
            try await capture(owner, probe: export, terminal: true)
            precondition(owner.isRetired && !owner.isCapturing && owner.isDrained && export.count == 1)
            var rejected: EditorDocumentWriteError?
            do { _ = try owner.scheduleMutation(contextId: "owned") } catch { rejected = error as? EditorDocumentWriteError }
            precondition(rejected == .rejected(.retired))
            passed.append("successful terminal capture retires admissions inside the exclusive gate before returning")
        }
        do {
            let owner = try owner(), edit = NativeBodyProbe()
            try await owner.performRead(contextId: "owned", rpcNames: ["ObjectListExport"]) {
                _ = try? await owner.performMutation(contextId: "owned") { try await edit.invoke() }
                _ = try? await MainActor.run { try owner.scheduleMutation(contextId: "owned") }
            }
            precondition(edit.count == 0 && owner.isDrained)
            await expectFailedWrite(owner)
            passed.append("read operation cannot promote itself through a nested mutation or scheduling wrapper")
        }
        do {
            let parent = try owner(), child = try child(parent), edit = NativeBodyProbe(), export = NativeBodyProbe()
            let scheduled = try child.scheduleMutation(contextId: "child")
            precondition(parent.pendingOperationCount == 1 && child.pendingOperationCount == 1)
            let saving = Task { @MainActor in try await capture(parent, probe: export) }
            try await eventually { parent.isCapturing }; precondition(export.count == 0)
            try await scheduled.run { try await edit.invoke() }
            try await saving.value
            precondition(edit.count == 1 && export.count == 1 && parent.isDrained && child.isDrained)
            passed.append("parent capture drains a selected child editor's synchronously registered real write")
        }
        do {
            let parent = try owner(), binding = try parent.childSourceBinding()
            let opening = NativeBodyProbe(held: true), export = NativeBodyProbe()
            let open = Task { @MainActor in
                try await binding.performRead(rpcNames: ["ObjectOpen"]) { try await opening.invoke("ObjectOpen") }
            }
            await opening.entered(); open.cancel(); _ = await failure { try await open.value }
            precondition(parent.pendingOperationCount == 1)
            let saving = Task { @MainActor in try await capture(parent, probe: export) }
            try await eventually { parent.isCapturing }; precondition(export.count == 0)
            opening.release(); try await saving.value
            precondition(parent.isDrained && export.count == 1)
            passed.append("captured child pre-open source lease holds parent drain through actual cancelled RPC completion")
        }
        do {
            let parent = try owner(), child = try child(parent), edit = NativeBodyProbe(fails: true)
            let writing = scheduleOriginalEditorMutation(owner: child, contextId: "child") { _ = try? await edit.invoke() }
            try await writing.value
            await expectFailedWrite(parent)
            precondition(child.isDrained && parent.isDrained)
            passed.append("swallowed selected-child native mutation failure poisons the same parent capture")
        }
        do {
            let owner = try owner()
            var scheduled: EditorDocumentScheduledWrite? = try owner.scheduleMutation(contextId: "owned")
            precondition(scheduled != nil && owner.pendingOperationCount == 1)
            scheduled = nil
            try await eventually { owner.isDrained }
            await expectFailedWrite(owner)
            passed.append("abandoned unstarted registration drains with a failed-edit latch instead of hanging or passing")
        }
        do {
            let parent = try owner(), child = try child(parent)
            let writing = scheduleOriginalEditorMutation(owner: parent, contextId: "owned") {
                _ = try? await child.performRead(contextId: "child", rpcNames: []) { throw PreparationFailure.refused }
            }
            try await writing.value
            await expectFailedWrite(parent)
            passed.append("caught child read-preparation failure under a registered parent write remains visible to parent capture")
        }
        do {
            let parent = try owner(), child = try child(parent), edit = NativeBodyProbe()
            try await child.performRead(contextId: "child", rpcNames: ["ObjectShow"]) {
                _ = try? await parent.performMutation(contextId: "owned") { try await edit.invoke() }
            }
            precondition(edit.count == 0)
            await expectFailedWrite(parent)
            passed.append("passive parent tracking cannot authorize direct parent-document RPCs from a child operation")
        }
        do {
            let probe = NativeBodyProbe()
            try await scheduleOriginalEditorMutation(owner: nil, contextId: "legacy") { try await probe.invoke() }.value
            precondition(probe.count == 1)
            passed.append("actual UI helper's nil-owner route preserves original asynchronous unbound invocation")
        }
        let report: [String: Any] = ["status": "PORTABLE_ORIGINAL_SCHEDULED_CAPTURE_CONTROLS_PASS",
            "executed": passed.count, "passed": passed.count, "controls": passed,
            "native_rpc_or_account_calls": 0, "apple_native": "NOT_RUN", "editable_host": "NOT_RUN",
            "prior_core14_and_additions6": "HISTORICAL_SCOPED_RECEIPTS_NOT_RERUN",
            "scope": "Actual owner, operation, source binding, Invocation and original UI scheduling helper; explicit held native-body/type probes"]
        print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
