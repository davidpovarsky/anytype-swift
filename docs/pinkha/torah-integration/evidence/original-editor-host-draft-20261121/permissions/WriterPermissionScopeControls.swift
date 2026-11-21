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

private enum BaseDocumentUpdate { case permissions }
private final class RevocationDocument: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, @unchecked Sendable {
    let objectId = "owned", spaceId = "owned-space"
    let mode = DocumentMode.handling
    let isOpened = true, isLocked = false
    let editorWriteLifetime = EditorDocumentWriteLifetime()
    private let lock = NSLock()
    private var stored: ObjectPermissions
    private let originalAccountDispatch: InvocationDispatchBinding?
    init(sourceQualified: Bool = true) {
        originalAccountDispatch = sourceQualified
            ? try! EditorDocumentWriteCapture(EditorDocumentWriteLifetime()).accountDispatchBinding() : nil
        var p = ObjectPermissions()
        p.canEditBlocks = true; p.canEditDetails = true; p.canChangeCover = true
        p.canChangeIcon = true; p.canChangeLayout = true
        p.canEditRelationValues = true; p.canEditPropertiesList = true; p.canPublish = true
        stored = p
    }
    var permissions: ObjectPermissions {
        get { lock.lock(); defer { lock.unlock() }; return stored }
        set { lock.lock(); stored = newValue; lock.unlock() }
    }
    func update(_ operation: (inout ObjectPermissions) -> Void) {
        var next = permissions; operation(&next); _ = applyOriginalPermissionTransition(next)
    }
    // Exact production BaseDocument transition body, not a control reimplementation.
    private func applyOriginalPermissionTransition(_ newPermissios: ObjectPermissions) -> [BaseDocumentUpdate] {
        if permissions != newPermissios {
            if (permissions.canEditBlocks && !newPermissios.canEditBlocks)
                || (originalAccountDispatch != nil
                    && EditorDocumentWritePermission.revokesAdmission(from: permissions, to: newPermissios)) {
                editorWriteLifetime.invalidate()
            }
            permissions = newPermissios
            return [.permissions]
        }
        
        return []
    }
    func deny(_ requirement: EditorDocumentWritePermission?) {
        update {
            switch requirement {
            case .editDetails?: $0.canEditDetails = false
            case .changeCover?: $0.canChangeCover = false
            case .changeIcon?: $0.canChangeIcon = false
            case .changeLayout?: $0.canChangeLayout = false
            case .editRelationValues?: $0.canEditRelationValues = false
            case .editPropertiesList?: $0.canEditPropertiesList = false
            case nil: $0.canEditBlocks = false
            }
        }
    }
}

@main
private struct WriterPermissionScopeControls {
    @MainActor private static var passed: [String] = []
    @MainActor
    private static func owner(_ document: RevocationDocument, sourceQualified: Bool) throws -> EditorDocumentWriteOwner {
        let binding: EditorDocumentWriteSourceBinding? = sourceQualified
            ? try .init(lifetime: .init(), accountLifetime: .init(), isCurrent: { true }) : nil
        return try EditorDocumentWriteOwner(data: .init(objectId: "owned", spaceId: "owned-space", mode: .handling),
            lifetimeDocument: document, sourceBinding: binding)
    }
    @MainActor
    private static func failure(_ operation: () async throws -> Void) async -> (any Swift.Error)? {
        do { try await operation(); return nil } catch { return error }
    }
    @MainActor
    static func main() async throws {
        do {
            let document = RevocationDocument(sourceQualified: false), owner = try owner(document, sourceQualified: false)
            let token = document.editorWriteLifetime.token()!, probe = NativeBodyProbe()
            for requirement: EditorDocumentWritePermission in [.editDetails, .changeCover, .changeIcon, .changeLayout, .editRelationValues, .editPropertiesList] {
                document.deny(requirement)
                precondition(document.editorWriteLifetime.isCurrent(token))
                try owner.validateOwnership()
            }
            try await owner.performMutation(contextId: "owned") { try await probe.invoke() }
            precondition(probe.count == 1 && !owner.isRetired)
            passed.append("legacy source-unbound document preserves its original block owner through all six additional flag losses")
        }
        do {
            let document = RevocationDocument(sourceQualified: false), owner = try owner(document, sourceQualified: false)
            let token = document.editorWriteLifetime.token()!, probe = NativeBodyProbe()
            document.deny(nil)
            let error = await failure { try await owner.performMutation(contextId: "owned") { try await probe.invoke() } } as? EditorDocumentWriteError
            precondition(!document.editorWriteLifetime.isCurrent(token) && error == .rejected(.retired) && probe.count == 0)
            passed.append("legacy nil-source route retains original canEditBlocks revocation and refused native dispatch")
        }
        do {
            let document = RevocationDocument(sourceQualified: true), owner = try owner(document, sourceQualified: true)
            let probe = NativeBodyProbe(), gate = Hold()
            let writing = Task { @MainActor in
                await failure {
                    try await owner.performMutation(contextId: "owned", requiredPermissions: [.changeCover]) {
                        let original = InvocationDispatchContext.binding!
                        let held = InvocationDispatchBinding { name in
                            let permit = try await original.prepare(messageName: name)
                            await gate.pause(); return permit
                        }
                        try await InvocationDispatchContext.$binding.withValue(held) { try await probe.invoke("ObjectSetDetails") }
                    }
                }
            }
            await gate.wait(); document.deny(.changeCover); await gate.resume()
            let error = await writing.value as? EditorDocumentWriteError
            precondition(error == .rejected(.retired) && probe.count == 0 && owner.isRetired)
            passed.append("source-qualified document still fences cover revocation after prepare and before actual GCD begin")
        }
        precondition(passed.count == 3)
        let report: [String: Any] = ["status": "PORTABLE_ORIGINAL_PERMISSION_SCOPE_CONTROLS_PASS",
            "executed": passed.count, "passed": passed.count, "controls": passed,
            "native_rpc_or_account_calls": 0, "apple_native": "NOT_RUN", "editable_host": "NOT_RUN",
            "prior_barrier17_permission18_queue11": "EXACT_SCOPED_RECEIPTS_RETAINED_NOT_RERUN",
            "scope": "Exact original BaseDocument transition body with qualified/nil account marker; real Owner, Invocation and lifetime"]
        print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
