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

private final class MutablePermissionDocument: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, @unchecked Sendable {
    let objectId = "owned", spaceId = "owned-space"
    let mode = DocumentMode.handling
    let isOpened = true, isLocked = false
    let editorWriteLifetime = EditorDocumentWriteLifetime()
    private let lock = NSLock()
    private var stored: ObjectPermissions
    init() {
        var p = ObjectPermissions()
        p.canEditBlocks = true; p.canEditDetails = true; p.canChangeCover = true
        p.canChangeIcon = true; p.canChangeLayout = true
        p.canEditRelationValues = true; p.canEditPropertiesList = true
        stored = p
    }
    var permissions: ObjectPermissions { lock.lock(); defer { lock.unlock() }; return stored }
    func update(_ operation: (inout ObjectPermissions) -> Void) {
        lock.lock(); defer { lock.unlock() }; operation(&stored)
    }
    func deny(_ requirement: EditorDocumentWritePermission) {
        update {
            switch requirement {
            case .editDetails: $0.canEditDetails = false
            case .changeCover: $0.canChangeCover = false
            case .changeIcon: $0.canChangeIcon = false
            case .changeLayout: $0.canChangeLayout = false
            case .editRelationValues: $0.canEditRelationValues = false
            case .editPropertiesList: $0.canEditPropertiesList = false
            }
        }
    }
}

@main
private struct WriterPermissionControls {
    @MainActor private static var passed: [String] = []
    @MainActor
    private static func owner(_ document: MutablePermissionDocument) throws -> EditorDocumentWriteOwner {
        try EditorDocumentWriteOwner(data: .init(objectId: "owned", spaceId: "owned-space", mode: .handling),
            lifetimeDocument: document,
            sourceBinding: .init(lifetime: .init(), accountLifetime: .init(), isCurrent: { true }))
    }
    @MainActor
    private static func failure(_ operation: () async throws -> Void) async -> (any Swift.Error)? {
        do { try await operation(); return nil } catch { return error }
    }
    @MainActor
    static func main() async throws {
        let requirements: [EditorDocumentWritePermission] = [
            .editDetails, .changeCover, .changeIcon, .changeLayout, .editRelationValues, .editPropertiesList
        ]
        for requirement in requirements {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe()
            document.deny(requirement)
            let owner = try owner(document)
            let error = await failure {
                try await owner.performMutation(contextId: "owned", requiredPermissions: [requirement]) {
                    try await probe.invoke("ObjectSetDetails")
                }
            } as? EditorDocumentWriteError
            precondition(error == .rejected(.notEditable) && probe.count == 0 && owner.isDrained)
            passed.append("actual original permission \(requirement) refuses its own false flag before execution")
        }
        do {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe(), owner = try owner(document)
            document.update { $0.canEditBlocks = false }
            let error = await failure {
                try await owner.performMutation(contextId: "owned", requiredPermissions: [.editDetails]) {
                    try await probe.invoke("ObjectSetDetails")
                }
            } as? EditorDocumentWriteError
            precondition(error == .rejected(.notEditable) && probe.count == 0)
            passed.append("additional details permission never replaces the original block-edit requirement")
        }
        do {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe(), owner = try owner(document)
            document.deny(.editDetails)
            try await owner.performMutation(contextId: "owned") { try await probe.invoke() }
            precondition(probe.count == 1)
            passed.append("legacy default block mutation does not acquire an unrelated details requirement")
        }
        do {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe(), owner = try owner(document)
            try await owner.performMutation(contextId: "owned", requiredPermissions: [.editDetails, .changeCover]) {
                try await owner.performMutation(contextId: "owned") {
                    try await owner.performRead(contextId: "owned", rpcNames: ["ObjectShow"]) {
                        try await probe.invoke("ObjectShow")
                    }
                }
            }
            precondition(probe.count == 1 && owner.isDrained)
            passed.append("all-allowed additional union traverses original nested mutation and explicit read routes")
        }
        do {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe(), gate = Hold(), owner = try owner(document)
            let writing = Task { @MainActor in
                await failure {
                    try await owner.performMutation(contextId: "owned", requiredPermissions: [.editDetails]) {
                        try await owner.performMutation(contextId: "owned") {
                            await gate.pause(); try await probe.invoke("ObjectSetDetails")
                        }
                    }
                }
            }
            await gate.wait(); document.deny(.editDetails); await gate.resume()
            let error = await writing.value as? EditorDocumentWriteError
            precondition(error == .rejected(.notEditable) && probe.count == 0 && owner.isDrained)
            passed.append("default lower ObjectActions mutation retains outer details at actual post-await Invocation.prepare")
        }
        do {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe(), gate = Hold(), owner = try owner(document)
            let writing = Task { @MainActor in
                await failure {
                    try await owner.performMutation(contextId: "owned", requiredPermissions: [.editDetails]) {
                        try await owner.performMutation(contextId: "owned", requiredPermissions: [.changeCover]) {
                            await gate.pause(); try await probe.invoke("ObjectSetDetails")
                        }
                    }
                }
            }
            await gate.wait(); document.deny(.editDetails); await gate.resume()
            let error = await writing.value as? EditorDocumentWriteError
            precondition(error == .rejected(.notEditable) && probe.count == 0)
            passed.append("an explicitly different nested cover requirement unions with rather than erasing outer details")
        }
        do {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe(), owner = try owner(document)
            let scheduled = try await owner.performMutation(contextId: "owned", requiredPermissions: [.editDetails]) {
                try await MainActor.run { try owner.scheduleMutation(contextId: "owned") }
            }
            precondition(owner.pendingOperationCount == 1)
            document.deny(.editDetails)
            let error = await failure { try await scheduled.run { try await probe.invoke("ObjectSetDetails") } } as? EditorDocumentWriteError
            precondition(error == .rejected(.notEditable) && probe.count == 0 && owner.isDrained)
            passed.append("queued descendant keeps inherited details after the originating outer lease has finished")
        }
        do {
            let document = MutablePermissionDocument(), gate = Hold(), owner = try owner(document)
            var publications = 0
            let writing = Task { @MainActor in
                await failure {
                    try await owner.performMutation(contextId: "owned", requiredPermissions: [.editDetails, .changeIcon]) {
                        await gate.pause()
                        try await MainActor.run {
                            try owner.performSynchronousOperation { publications += 1 }
                        }
                    }
                }
            }
            await gate.wait(); document.deny(.changeIcon); await gate.resume()
            let error = await writing.value as? EditorDocumentWriteError
            precondition(error == .rejected(.notEditable) && publications == 0)
            passed.append("actual synchronous UI publication rechecks inherited icon requirement after an await")
        }
        do {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe(held: true), owner = try owner(document)
            let writing = Task { @MainActor in
                await failure {
                    try await owner.performMutation(contextId: "owned", requiredPermissions: [.editDetails]) {
                        try await probe.invoke("ObjectSetDetails")
                    }
                }
            }
            await probe.entered(); document.deny(.editDetails); probe.release()
            let error = await writing.value as? EditorDocumentWriteError
            precondition(error == .completedWithoutOwnership(.notEditable) && probe.count == 1 && owner.isDrained)
            let export = NativeBodyProbe()
            let saveError = await failure {
                try await owner.withExclusiveRead(contextId: "owned", spaceId: "owned-space", rpcNames: ["ObjectListExport"]) {
                    try await export.invoke("ObjectListExport")
                }
            } as? EditorDocumentWriteError
            precondition(saveError == .rejected(.failedWrite) && export.count == 0)
            passed.append("permission change during completed native work reports completedWithoutOwnership and prevents false save")
        }
        do {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe(), gate = Hold(), owner = try owner(document)
            let writing = Task { @MainActor in
                await failure {
                    try await owner.performMutation(contextId: "owned", requiredPermissions: [.editDetails]) {
                        try await owner.performRead(contextId: "owned", rpcNames: ["ObjectShow"]) {
                            await gate.pause(); try await probe.invoke("ObjectShow")
                        }
                    }
                }
            }
            await gate.wait(); document.update { $0.canEditBlocks = false }; await gate.resume()
            let error = await writing.value as? EditorDocumentWriteError
            precondition(error == .rejected(.notEditable) && probe.count == 0)
            passed.append("nested read cannot erase its same-owner ancestor's original block-edit admission")
        }
        do {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe(), owner = try owner(document)
            let error = await failure {
                try await owner.performRead(contextId: "owned", rpcNames: ["ObjectShow"], requiredPermissions: [.editDetails]) {
                    try await owner.performMutation(contextId: "owned") { try await probe.invoke("ObjectSetDetails") }
                }
            } as? EditorDocumentWriteError
            precondition(error == .rejected(.unqualifiedDispatch) && probe.count == 0)
            passed.append("permission-qualified read stays read-only and cannot promote itself to a mutation")
        }
        do {
            let document = MutablePermissionDocument(), probe = NativeBodyProbe(), owner = try owner(document)
            let scheduled = try owner.scheduleMutation(contextId: "owned", requiredPermissions: [.changeCover])
            document.deny(.changeCover)
            let error = await failure { try await scheduled.run { try await probe.invoke("ObjectSetDetails") } } as? EditorDocumentWriteError
            precondition(error == .rejected(.notEditable) && probe.count == 0 && owner.isDrained)
            passed.append("directly scheduled cover requirement is retained and rechecked before queued UI body starts")
        }
        do {
            let document = MutablePermissionDocument(), owner = try owner(document)
            document.deny(.changeIcon)
            var publications = 0
            await owner.performPublication(contextId: "owned", requiredPermissions: [.changeIcon]) {
                await MainActor.run { publications += 1 }
            }
            precondition(publications == 0 && owner.isDrained)
            passed.append("nonthrowing original publication convenience forwards its explicit icon requirement")
        }
        precondition(passed.count == 18)
        let report: [String: Any] = ["status": "PORTABLE_ADDITIVE_ORIGINAL_PERMISSION_CONTROLS_PASS",
            "executed": passed.count, "passed": passed.count, "controls": passed,
            "native_rpc_or_account_calls": 0, "apple_native": "NOT_RUN", "editable_host": "NOT_RUN",
            "queue_barrier17": "RETAINED_EXACT_PRIOR_RECEIPT_NOT_RERUN",
            "permission_storage": "Exact original ObjectPermissions declaration; deliberately controlled values, original details evaluator not executed",
            "scope": "Real permission-union Owner, original Invocation/operation and targeted mutable original permission flags"]
        print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
