import Foundation

public enum PinkhaBootstrapAdmissionError: Error, Sendable {
    case accountClosed
    case operationsInFlight
}

/// Owns the lifetime of actual bootstrap calls. Retirement stops admission and
/// drains the original operation, including any nested provisioning tasks it owns.
public actor PinkhaBootstrapOperations<Value: Sendable> {
    public private(set) var accepting = true
    private var tasks: [UUID: Task<Value, Error>] = [:]

    public init() {}

    public func run(
        _ operation: @escaping @Sendable () async throws -> Value
    ) async throws -> Value {
        try Task.checkCancellation()
        guard accepting else { throw PinkhaBootstrapAdmissionError.accountClosed }
        let id = UUID()
        let task = Task { try await operation() }
        tasks[id] = task
        defer { tasks[id] = nil }
        return try await task.value
    }

    public func closeAndDrain() async {
        accepting = false
        let pending = tasks
        // Finishing the original writer preserves its commit/rollback semantics.
        // Cancelling only its caller would not stop its nested retained tasks.
        for (id, task) in pending {
            _ = try? await task.value
            tasks[id] = nil
        }
    }

    public func reopen() throws {
        guard tasks.isEmpty else { throw PinkhaBootstrapAdmissionError.operationsInFlight }
        accepting = true
    }
}
