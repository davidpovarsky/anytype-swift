import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyHostError: Error, Equatable, Sendable {
    case sessionClosed
    case engineRestarted
    case wrongWorkspace
    case invalidDocument(String)
    case incompleteDocument
    case changedDocument
    case invalidSelection
    case writeUncertain
}

/// A lease belongs to one account, Space and native engine run. Construction
/// stays inside the session owner; a Heart document cannot manufacture one.
public struct AnyHostLease: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    private let check: @Sendable () async throws -> Void

    init(workspace: AnyTorahWorkspace, generation: UUID, engineStartedAt: String,
         check: @escaping @Sendable () async throws -> Void) {
        self.workspace = workspace
        self.generation = generation
        self.engineStartedAt = engineStartedAt
        self.check = check
    }

    public func validate() async throws {
        try Task.checkCancellation()
        try await check()
        try Task.checkCancellation()
    }
}

/// Owns work against ONE native account/Space. The application must revoke and
/// drain this owner before signing out or stopping its AnyEmbeddedRuntime.
/// This is an application lifetime fence, not a substitute for native ACLs.
public actor AnyApplicationSession {
    public nonisolated let workspace: AnyTorahWorkspace
    public nonisolated let generation: UUID
    public nonisolated let engineStartedAt: String
    private let verifyRun: @Sendable () async throws -> String
    private enum State { case active, revoked, closed }
    private var state = State.active
    private var calls: [UUID: @Sendable () -> Void] = [:]
    private var drainWaiters: [CheckedContinuation<Void, Never>] = []

    public static func connect(client: AnyHTTPClient, workspace: AnyTorahWorkspace) async throws -> AnyApplicationSession {
        guard client.expectedAccountID == workspace.accountID else { throw AnyHostError.wrongWorkspace }
        let readRun: @Sendable () async throws -> String = {
            let health = try await client.requestJSON(method: "GET", path: ["v1", "health"])
            guard health["status"]?.string == "ok",
                  health["account"]?.string == workspace.accountID,
                  let started = health["startedAt"]?.string, !started.isEmpty else {
                throw AnyHostError.engineRestarted
            }
            return started
        }
        let started = try await readRun()
        return .init(workspace: workspace, engineStartedAt: started, verifyRun: readRun)
    }

    /// Internal injection exercises lifetime races without inventing native authority.
    init(workspace: AnyTorahWorkspace, engineStartedAt: String,
         verifyRun: @escaping @Sendable () async throws -> String) {
        self.workspace = workspace
        self.generation = UUID()
        self.engineStartedAt = engineStartedAt
        self.verifyRun = verifyRun
    }

    public func perform<Value: Sendable>(
        _ operation: @escaping @Sendable (AnyHostLease) async throws -> Value
    ) async throws -> Value {
        try requireActive()
        let id = UUID()
        let lease = AnyHostLease(workspace: workspace, generation: generation,
            engineStartedAt: engineStartedAt, check: { try await self.validateCurrentRun() })
        let task = Task<Value, Error> {
            try await lease.validate()
            let value = try await operation(lease)
            // Do not deliver data or a successful receipt to a revoked session.
            try await lease.validate()
            return value
        }
        calls[id] = { task.cancel() }
        defer { finish(id) }
        return try await withTaskCancellationHandler {
            let result = try await task.value
            try requireActive()
            return result
        } onCancel: { task.cancel() }
    }

    /// Marks revoked before its first suspension. In-flight work is cancelled,
    /// then awaited. The owner may stop/switch the native engine after return.
    public func revokeAndDrain() async {
        if case .closed = state { return }
        revoke()
        if !calls.isEmpty {
            await withCheckedContinuation { continuation in
                drainWaiters.append(continuation)
            }
        }
        state = .closed
    }

    public var isActive: Bool {
        if case .active = state { true } else { false }
    }

    private func validateCurrentRun() async throws {
        try requireActive()
        try Task.checkCancellation()
        let current: String
        do { current = try await verifyRun() }
        catch AnyEngineError.accountChanged {
            revoke()
            throw AnyHostError.wrongWorkspace
        } catch AnyHostError.engineRestarted {
            revoke()
            throw AnyHostError.engineRestarted
        }
        try requireActive()
        guard current == engineStartedAt else {
            revoke()
            throw AnyHostError.engineRestarted
        }
    }

    private func requireActive() throws {
        guard case .active = state else { throw AnyHostError.sessionClosed }
    }

    private func revoke() {
        state = .revoked
        for cancel in calls.values { cancel() }
    }

    private func finish(_ id: UUID) {
        calls.removeValue(forKey: id)
        if calls.isEmpty {
            let waiting = drainWaiters
            drainWaiters.removeAll()
            for continuation in waiting { continuation.resume() }
        }
    }
}
