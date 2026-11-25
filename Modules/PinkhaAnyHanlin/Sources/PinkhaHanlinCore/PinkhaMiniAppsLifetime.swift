import Foundation

/// Owns asynchronous MiniApps work independently of its engine adapter.
/// Revocation stops new work and invalidates callbacks, then waits for actual native
/// operations to return. It never cancels a write whose native completion is unknown.
@MainActor
public final class PinkhaMiniAppsLifetime {
    public struct Lease: Equatable, Sendable {
        fileprivate let generation: UUID
    }

    private var generation = UUID()
    private var holds = Set<UUID>()
    private var operations: [UUID: Task<Void, Never>] = [:]

    public init() {}

    public var acceptsOperations: Bool { holds.isEmpty }

    public func lease() throws -> Lease {
        guard acceptsOperations else { throw CancellationError() }
        return Lease(generation: generation)
    }

    public func isCurrent(_ lease: Lease) -> Bool {
        acceptsOperations && lease.generation == generation
    }

    public func validate(_ lease: Lease) throws {
        guard isCurrent(lease) else { throw CancellationError() }
    }

    public func submit(_ operation: @escaping @MainActor (Lease) async -> Void) throws {
        let lease = try lease()
        let id = UUID()
        operations[id] = Task { @MainActor [weak self] in
            guard let self else { return }
            defer { operations.removeValue(forKey: id) }
            guard isCurrent(lease) else { return }
            await operation(lease)
        }
    }

    /// Each caller owns a separate hold. Releasing an authentication hold cannot
    /// resume work while a different caller still owns an engine-switch hold.
    public func revoke() -> UUID {
        let token = UUID()
        holds.insert(token)
        generation = UUID()
        return token
    }

    /// Call after revoking admission. UI owners may first dismiss their own consent
    /// presentation so a suspended confirmation can return before the native drain.
    public func drain() async {
        let pending = Array(operations.values)
        for operation in pending { await operation.value }
    }

    public func revokeAndDrain() async -> UUID {
        let token = revoke()
        await drain()
        return token
    }

    public func resume(_ token: UUID) {
        holds.remove(token)
    }
}
