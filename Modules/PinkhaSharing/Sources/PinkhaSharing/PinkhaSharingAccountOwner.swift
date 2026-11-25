import Foundation

/// A common account-change fence for sharing work. Native ACL checks remain mandatory.
public actor PinkhaSharingAccountOwner {
    public static let shared = PinkhaSharingAccountOwner()
    private struct Account {
        let id: String
        let generation: UUID
        var closing = false
        var calls: [UUID: @Sendable () -> Void] = [:]
        var waiters: [CheckedContinuation<Void, Never>] = []
    }
    private var accounts: [PinkhaSharingEngine: Account] = [:]

    public init() {}

    public func didOpen(engine: PinkhaSharingEngine, accountID: String) throws {
        guard PinkhaSharingScope.validID(accountID) else { throw PinkhaSharingError.invalidInput }
        if let old = accounts[engine] {
            guard !old.closing, old.id == accountID else { throw PinkhaSharingError.staleContext }
            return
        }
        accounts[engine] = Account(id: accountID, generation: UUID())
    }

    public func perform<Value: Sendable>(scope: PinkhaSharingScope,
        _ operation: @escaping @Sendable () async throws -> Value) async throws -> Value {
        guard let account = accounts[scope.engine], !account.closing, account.id == scope.accountID else {
            throw PinkhaSharingError.staleContext
        }
        let id = UUID(), generation = account.generation
        let task = Task<Value, Error> {
            try Task.checkCancellation()
            let value = try await operation()
            try Task.checkCancellation()
            return value
        }
        accounts[scope.engine]?.calls[id] = { task.cancel() }
        defer { finish(engine: scope.engine, id: id, generation: generation) }
        return try await withTaskCancellationHandler {
            let value = try await task.value
            guard let current = accounts[scope.engine], !current.closing,
                  current.id == scope.accountID, current.generation == generation else {
                throw PinkhaSharingError.staleContext
            }
            return value
        } onCancel: { task.cancel() }
    }

    /// Call before account selection, sign-out, engine stop or data removal.
    public func closeAndDrain(engine: PinkhaSharingEngine) async {
        guard var account = accounts[engine] else { return }
        account.closing = true
        accounts[engine] = account
        for cancel in account.calls.values { cancel() }
        if !account.calls.isEmpty {
            await withCheckedContinuation { continuation in
                accounts[engine]?.waiters.append(continuation)
            }
        }
        if accounts[engine]?.generation == account.generation { accounts.removeValue(forKey: engine) }
    }

    private func finish(engine: PinkhaSharingEngine, id: UUID, generation: UUID) {
        guard var account = accounts[engine], account.generation == generation else { return }
        account.calls.removeValue(forKey: id)
        let waiting = account.calls.isEmpty ? account.waiters : []
        if account.calls.isEmpty { account.waiters.removeAll() }
        accounts[engine] = account
        for waiter in waiting { waiter.resume() }
    }
}
