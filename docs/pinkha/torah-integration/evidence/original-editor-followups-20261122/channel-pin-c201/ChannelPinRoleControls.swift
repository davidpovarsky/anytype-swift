import Foundation

// These controls exercise actual passive role state, Owner, lifetime and
// Invocation permit classes. GCD callbacks below are explicit disposable probes;
// they neither serialize protobuf nor call Anytype Lib, a database, or UIKit.
private final class RoleDocumentProbe: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, Sendable {
    let objectId: String
    let spaceId = "owned-space"
    let mode = DocumentMode.handling
    let isOpened = true, isLocked = false
    let editorWriteLifetime = EditorDocumentWriteLifetime()
    let permissions = ObjectPermissions(details: .init(restrictionsValue: []), isLocked: false,
        participantCanEdit: true, isVersionMode: false, objectRestrictions: [])
    init(_ objectId: String = "widget") { self.objectId = objectId }
}

private actor RoleHold {
    private var entered = false, released = false
    private var entries: [CheckedContinuation<Void, Never>] = []
    private var releases: [CheckedContinuation<Void, Never>] = []
    func pause() async {
        entered = true
        let entries = entries; self.entries.removeAll()
        for c in entries { c.resume() }
        if !released { await withCheckedContinuation { releases.append($0) } }
    }
    func wait() async { if !entered { await withCheckedContinuation { entries.append($0) } } }
    func resume() {
        released = true
        let releases = releases; self.releases.removeAll()
        for c in releases { c.resume() }
    }
}

private final class DispatchBodyProbe: @unchecked Sendable {
    private let lock = NSLock()
    private let held: DispatchSemaphore?
    private var countValue = 0
    private var entries: [CheckedContinuation<Void, Never>] = []
    init(held: Bool = false) { self.held = held ? DispatchSemaphore(value: 0) : nil }
    var count: Int { lock.lock(); defer { lock.unlock() }; return countValue }
    func entered() async {
        await withCheckedContinuation { c in
            lock.lock()
            if countValue > 0 { lock.unlock(); c.resume() }
            else { entries.append(c); lock.unlock() }
        }
    }
    func release() { held?.signal() }
    func run(_ permit: InvocationDispatchPermit) async throws {
        try await withCheckedThrowingContinuation { (c: CheckedContinuation<Void, Error>) in
            DispatchQueue.global().async { [self] in
                do {
                    let completion = try permit.begin()
                    lock.lock(); countValue += 1
                    let entries = entries; self.entries.removeAll(); lock.unlock()
                    for entry in entries { entry.resume() }
                    if let held { precondition(held.wait(timeout: .now() + 10) == .success) }
                    completion.finish()
                    c.resume()
                } catch { c.resume(throwing: error) }
            }
        }
    }
    func invoke(_ name: String = "BlockCreateWidget") async throws {
        guard let binding = InvocationDispatchContext.binding else { preconditionFailure("missing original Owner binding") }
        try await run(binding.prepare(messageName: name))
    }
}

@main
private struct ChannelPinRoleControls {
    @MainActor private static var passed: [String] = []
    @MainActor private static func fixture(_ account: EditorDocumentWriteLifetime, space: String = "owned-space") throws
      -> (OriginalChannelPinPermissionState, OriginalChannelPinSubscriptionContext, OriginalChannelPinPermission) {
        var state = OriginalChannelPinPermissionState()
        let context = state.begin(accountID: "actual-account", accountCapture: try .init(account))!
        let permission = try state.receive([(spaceID: space, isModerator: true)], from: context)[space]!
        return (state, context, permission)
    }
    @MainActor private static func owner(_ account: EditorDocumentWriteLifetime) throws -> EditorDocumentWriteOwner {
        let d = RoleDocumentProbe()
        return try .init(data: .init(objectId: d.objectId, spaceId: d.spaceId, mode: d.mode), lifetimeDocument: d,
                         sourceBinding: .init(lifetime: .init(), accountLifetime: account, isCurrent: { true }))
    }
    @MainActor private static func failure(_ operation: () async throws -> Void) async -> EditorDocumentWriteError? {
        do { try await operation(); return nil } catch { return error as? EditorDocumentWriteError }
    }
    @MainActor private static func rejected(_ operation: () throws -> Void) -> Bool {
        do { try operation(); return false } catch { return true }
    }
    @MainActor private static func eventually(_ predicate: () -> Bool) async throws {
        for _ in 0..<400 { if predicate() { return }; try await Task.sleep(nanoseconds: 5_000_000) }
        preconditionFailure("actual owner failed to reach bounded drain boundary")
    }
    @MainActor static func main() async throws {
        do {
            let a = EditorDocumentWriteLifetime(), (_, _, p) = try fixture(a)
            let c = try p.capture(matching: .init(a), spaceId: "owned-space")
            let admissions = try EditorDocumentWriteCapture.acquireAll([c]); admissions.forEach { $0.cancel() }
            passed.append("original moderator snapshot binds exact live account and Space")
        }
        do {
            let a = EditorDocumentWriteLifetime(); var s = OriginalChannelPinPermissionState()
            let c = s.begin(accountID: "a", accountCapture: try .init(a))!
            let values = try s.receive([("owned-space", false), ("owned-space", true)], from: c)
            precondition(values.isEmpty)
            passed.append("first actual participant record governs duplicate-Space role observations")
        }
        do {
            let a = EditorDocumentWriteLifetime(); var (s, c, old) = try fixture(a)
            let lost = try s.receive([("owned-space", false)], from: c)
            precondition(lost.isEmpty && rejected { try old.validate() })
            let fresh = try s.receive([("owned-space", true)], from: c)["owned-space"]!
            try fresh.validate(); precondition(rejected { try old.validate() })
            precondition(old.roleCapture.source !== fresh.roleCapture.source)
            passed.append("admin-to-writer then restoration never revives the old capture")
        }
        do {
            let a = EditorDocumentWriteLifetime(); var (s, c, old) = try fixture(a)
            let removed = try s.receive([], from: c)
            precondition(removed.isEmpty && rejected { try old.validate() })
            passed.append("participant removal invalidates before returning the published snapshot")
        }
        do {
            let a = EditorDocumentWriteLifetime(); var (s, c, old) = try fixture(a)
            precondition(s.stop().isEmpty && rejected { try old.validate() })
            let delayed = try s.receive([("owned-space", true)], from: c)
            precondition(delayed.isEmpty && rejected { try old.validate() })
            passed.append("stop revokes before unsubscribe and delayed callback cannot recreate a role")
        }
        do {
            let a = EditorDocumentWriteLifetime(), b = EditorDocumentWriteLifetime()
            var (s, oldContext, old) = try fixture(a)
            let current = s.begin(accountID: "other-account", accountCapture: try .init(b))!
            let fresh = try s.receive([("owned-space", true)], from: current)["owned-space"]!
            let delayed = try s.receive([("owned-space", false)], from: oldContext)
            try fresh.validate(); precondition(delayed["owned-space"]?.roleCapture.source === fresh.roleCapture.source)
            precondition(rejected { try old.validate() })
            passed.append("old subscription cannot replace or revoke a newer account snapshot")
        }
        do {
            let a = EditorDocumentWriteLifetime(); var (s, c, old) = try fixture(a)
            a.invalidate()
            precondition(rejected { _ = try old.capture(matching: .init(a), spaceId: "owned-space") })
            let afterAccountChange = try s.receive([("owned-space", true)], from: c)
            precondition(afterAccountChange.isEmpty)
            passed.append("account generation change rejects equal-string recapture and stale role updates")
        }
        do {
            let a = EditorDocumentWriteLifetime(), (_, _, p) = try fixture(a), o = try owner(a), body = DispatchBodyProbe()
            try await o.performChannelPinMutation(contextId: "widget", permission: p) {
                try await body.invoke(); try await body.invoke("BlockListDelete")
            }
            precondition(body.count == 2 && o.isDrained)
            passed.append("both unchanged original BlockWidget RPC names reach the actual dispatch permit")
        }
        for wrongSpace in [true, false] {
            let a = EditorDocumentWriteLifetime(), b = EditorDocumentWriteLifetime()
            let (_, _, p) = try fixture(wrongSpace ? a : b, space: wrongSpace ? "other-space" : "owned-space")
            let o = try owner(a), body = DispatchBodyProbe()
            let error = await failure { try await o.performChannelPinMutation(contextId: "widget", permission: p) { try await body.invoke() } }
            precondition(error == .rejected(.wrongContext) && body.count == 0)
            passed.append(wrongSpace ? "foreign Space role cannot authorize widget write" : "other actual account source cannot authorize equal-Space widget write")
        }
        do {
            let a = EditorDocumentWriteLifetime(), (_, _, p) = try fixture(a), o = try owner(a), body = DispatchBodyProbe()
            let error = await failure { try await o.performChannelPinMutation(contextId: "foreign", permission: p) { try await body.invoke() } }
            precondition(error == .rejected(.wrongContext) && body.count == 0)
            passed.append("pin-specific entry retains the original exact target guard")
        }
        do {
            let a = EditorDocumentWriteLifetime(), (_, _, p) = try fixture(a), o = try owner(a), body = DispatchBodyProbe()
            let error = await failure { try await o.performChannelPinMutation(contextId: "widget", permission: p) { try await body.invoke("ObjectSetDetails") } }
            precondition(error == .rejected(.unqualifiedDispatch) && body.count == 0)
            passed.append("pin scope cannot dispatch an unrelated original mutation RPC")
        }
        do {
            let a = EditorDocumentWriteLifetime(); var (s, c, p) = try fixture(a)
            let o = try owner(a), body = DispatchBodyProbe(), gate = RoleHold()
            let writing = Task { @MainActor in await failure {
                try await o.performChannelPinMutation(contextId: "widget", permission: p) {
                    let permit = try await InvocationDispatchContext.binding!.prepare(messageName: "BlockCreateWidget")
                    await gate.pause(); try await body.run(permit)
                }
            } }
            await gate.wait(); _ = try s.receive([("owned-space", false)], from: c)
            _ = try s.receive([("owned-space", true)], from: c); await gate.resume()
            let error = await writing.value
            precondition(error == .rejected(.retired) && body.count == 0 && o.isDrained)
            passed.append("prepare-to-real-GCD role loss denies old permit even after role restoration")
        }
        do {
            let a = EditorDocumentWriteLifetime(), (_, _, p) = try fixture(a), o = try owner(a), body = DispatchBodyProbe()
            let error = await failure {
                try await o.performChannelPinMutation(contextId: "widget", permission: p) {
                    try await o.performMutation(contextId: "widget") { try await body.invoke("ObjectSetDetails") }
                }
            }
            precondition(error == .rejected(.unqualifiedDispatch) && body.count == 0)
            passed.append("nested generic mutation cannot discard the pin RPC restriction")
        }
        do {
            let a = EditorDocumentWriteLifetime(); var (s, c, p) = try fixture(a)
            let o = try owner(a), body = DispatchBodyProbe()
            let child = try await o.performChannelPinMutation(contextId: "widget", permission: p) { @MainActor in try o.childSourceBinding() }
            let error = await failure { try await child.performOperation(rpcNames: ["ObjectSetDetails"]) { try await body.invoke("ObjectSetDetails") } }
            precondition(error == .rejected(.unqualifiedDispatch) && body.count == 0)
            _ = try s.receive([("owned-space", false)], from: c)
            precondition(rejected { try child.validate() })
            passed.append("derived child binding retains both the original parent and frozen role restriction")
        }
        do {
            let a = EditorDocumentWriteLifetime(), (_, _, p) = try fixture(a), o = try owner(a), body = DispatchBodyProbe()
            let error = await failure {
                try await o.performRead(contextId: "widget", rpcNames: []) {
                    try await o.performChannelPinMutation(contextId: "widget", permission: p) { try await body.invoke() }
                }
            }
            precondition(error == .rejected(.unqualifiedDispatch) && body.count == 0)
            passed.append("pin API does not upgrade an inherited pure read into write authority")
        }
        do {
            let a = EditorDocumentWriteLifetime(); var (s, c, p) = try fixture(a)
            let o = try owner(a), body = DispatchBodyProbe(), gate = RoleHold()
            var published = false
            let writing = Task { @MainActor in await failure {
                try await o.performChannelPinMutation(contextId: "widget", permission: p) { @MainActor in
                    try await body.invoke(); await gate.pause()
                    try o.performSynchronousOperation(requiresEditing: false) { published = true }
                }
            } }
            await gate.wait(); _ = try s.receive([("owned-space", false)], from: c); await gate.resume()
            let error = await writing.value
            precondition(error == .rejected(.retired) && body.count == 1 && !published)
            passed.append("role loss after real admitted body suppresses publication without inventing rollback")
        }
        do {
            let a = EditorDocumentWriteLifetime(); var (s, c, p) = try fixture(a)
            let o = try owner(a), body = DispatchBodyProbe(held: true), export = DispatchBodyProbe()
            let writing = Task { @MainActor in await failure { try await o.performChannelPinMutation(contextId: "widget", permission: p) { try await body.invoke() } } }
            await body.entered(); _ = try s.receive([("owned-space", false)], from: c)
            let saving = Task { @MainActor in await failure {
                try await o.withExclusiveRead(contextId: "widget", spaceId: "owned-space", rpcNames: ["ObjectListExport"]) { try await export.invoke("ObjectListExport") }
            } }
            try await eventually { o.isCapturing }
            precondition(o.pendingOperationCount == 1 && export.count == 0)
            body.release(); let writeError = await writing.value; let saveError = await saving.value
            precondition(writeError == .completedWithoutOwnership(.retired))
            precondition(saveError == .rejected(.failedWrite) && export.count == 0 && o.isDrained)
            passed.append("role revocation cannot drain an admitted GCD body or produce a successful save receipt")
        }
        precondition(passed.count == 18)
        print(String(data: try JSONSerialization.data(withJSONObject: ["executed": passed.count, "passed": passed.count, "cases": passed, "native_rpc_calls": 0, "native_ui": "NOT_RUN", "scope": "Actual role state, Owner, lifetime and dispatch-permit classes; explicit document and GCD probes only"], options: [.prettyPrinted,.sortedKeys]), encoding: .utf8)!)
    }
}
