import Foundation
import PinkhaAnyHost

/// Synchronous UI revocation precedes draining native work during close/sign out.
/// A revoked lifetime is never reactivated; the next mounted workspace owns a new one.
@MainActor
public final class AnyUIPresentationLifetime {
    public private(set) var isActive = true
    public let id = UUID()
    private struct Entry {
        let revoke: @MainActor () -> Void
        let drain: @MainActor () async -> Void
    }
    private var entries: [UUID: Entry] = [:]
    private var revokedEntries: [Entry] = []
    private var drainTask: Task<Void, Never>?

    public init() {}

    @discardableResult
    public func register(revoke: @escaping @MainActor () -> Void,
                         drain: @escaping @MainActor () async -> Void) throws -> UUID {
        guard isActive else { throw AnyHostError.sessionClosed }
        let token = UUID()
        entries[token] = Entry(revoke: revoke, drain: drain)
        return token
    }

    public func unregister(_ token: UUID) {
        entries.removeValue(forKey: token)
    }

    public func requireActive() throws {
        guard isActive else { throw AnyHostError.sessionClosed }
    }

    public func revoke() {
        guard isActive else { return }
        isActive = false
        let active = Array(entries.values)
        entries.removeAll()
        revokedEntries.append(contentsOf: active)
        for entry in active { entry.revoke() }
    }

    public func drain() async {
        revoke()
        if let existing = drainTask { await existing.value; return }
        let draining = revokedEntries
        revokedEntries.removeAll()
        let task = Task { @MainActor in
            for entry in draining { await entry.drain() }
        }
        drainTask = task
        await task.value
    }
}
