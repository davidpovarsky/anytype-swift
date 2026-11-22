import Foundation

enum UIAlertAction {
    enum Style: Sendable {
        case cancel
        case `default`
    }
}
enum Loc {
    static let cancel = "fixture-cancel"
    static let ok = "fixture-ok"
    static let undoTyping = "fixture-undo-typing"
    static let undo = "fixture-undo"
}

protocol BaseDocumentProtocol: AnyObject, Sendable {
    var objectId: String { get }
}
final class DocumentProbe: BaseDocumentProtocol {
    let objectId: String
    init(objectId: String) { self.objectId = objectId }
}
protocol ObjectActionsServiceProtocol: Sendable {
    func undo(objectId: String) async throws
}
@MainActor
protocol EditorRouterProtocol: AnyObject {
    func showAlert(alertModel: AlertModel)
}
@MainActor
final class RouterProbe: EditorRouterProtocol {
    var alert: AlertModel?
    func showAlert(alertModel: AlertModel) { alert = alertModel }
}
@MainActor
final class TraceProbe {
    var entries: [String] = []
}
@MainActor
final class UndoServiceProbe: ObjectActionsServiceProtocol {
    private(set) var objectIDs: [String] = []
    private var firstCallWaiter: CheckedContinuation<String, Never>?
    let trace: TraceProbe
    init(trace: TraceProbe) { self.trace = trace }
    func undo(objectId: String) async throws {
        objectIDs.append(objectId)
        trace.entries.append("undo:" + objectId)
        firstCallWaiter?.resume(returning: objectId)
        firstCallWaiter = nil
    }
    func firstCall() async -> String {
        if let first = objectIDs.first { return first }
        return await withCheckedContinuation { firstCallWaiter = $0 }
    }
}
enum EditorDocumentWritePermission: Hashable, Sendable { case fixtureOnly }
enum ProbeAdmissionError: Error { case rejected }
@MainActor
final class EditorDocumentWriteOwner {
    let trace: TraceProbe
    let rejects: Bool
    private(set) var contexts: [String] = []
    init(trace: TraceProbe, rejects: Bool = false) {
        self.trace = trace
        self.rejects = rejects
    }
    func scheduleMutation(
        contextId: String, requiredPermissions: Set<EditorDocumentWritePermission>
    ) throws -> ScheduledMutationProbe {
        trace.entries.append("attempt:" + contextId)
        if rejects { throw ProbeAdmissionError.rejected }
        contexts.append(contextId)
        return ScheduledMutationProbe(trace: trace)
    }
}
@MainActor
struct ScheduledMutationProbe {
    let trace: TraceProbe
    func run<Value: Sendable>(
        operation: @escaping @MainActor @Sendable () async throws -> Value
    ) async throws -> Value {
        trace.entries.append("deferred-body")
        return try await operation()
    }
}
@MainActor
protocol BlockActionHandlerProtocol: AnyObject, Sendable {
    var documentWriteOwner: EditorDocumentWriteOwner? { get }
    var documentWriteContextID: String { get }
}
@MainActor
final class ActionHandlerProbe: BlockActionHandlerProtocol {
    let documentWriteOwner: EditorDocumentWriteOwner?
    let documentWriteContextID: String
    init(owner: EditorDocumentWriteOwner?, contextID: String) {
        documentWriteOwner = owner
        documentWriteContextID = contextID
    }
}
