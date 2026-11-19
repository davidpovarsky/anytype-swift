import Foundation
import PinkhaKit
import Factory
import os.log

private let pinkhaLog = OSLog(subsystem: "com.anytype.pinkha", category: "Bootstrap")

public final class PinkhaBootstrapStateManager: Sendable {
    private struct Entry: Sendable {
        let state: PinkhaSpaceBootstrapState
        let claim: UUID
    }
    private let states = LockIsolated<[String: Entry]>([:])

    public init() {}

    public func state(for spaceId: String) -> PinkhaSpaceBootstrapState {
        states.value[spaceId]?.state ?? .uninitialized
    }

    public func setState(_ state: PinkhaSpaceBootstrapState, for spaceId: String) {
        states.withValue { dict in
            dict[spaceId] = Entry(state: state, claim: UUID())
        }
        logState(state, for: spaceId)
    }

    public func setState(_ state: PinkhaSpaceBootstrapState, for spaceId: String, claim: UUID) {
        let accepted = states.withValue { dict in
            guard dict[spaceId]?.claim == claim else { return false }
            dict[spaceId] = Entry(state: state, claim: claim)
            return true
        }
        if accepted { logState(state, for: spaceId) }
    }

    public func resetForAccountChange() {
        states.withValue { $0.removeAll(keepingCapacity: true) }
    }

    private func logState(_ state: PinkhaSpaceBootstrapState, for spaceId: String) {
        switch state {
        case .uninitialized:
            os_log("[Pinkha] Space %{public}@ bootstrap uninitialized", log: pinkhaLog, type: .info, spaceId)
        case .provisioning:
            os_log("[Pinkha] Space %{public}@ bootstrap started (provisioning)", log: pinkhaLog, type: .info, spaceId)
        case .ready(let manifest):
            os_log("[Pinkha] Space %{public}@ bootstrap ready (schemaVersion: %ld, objectId: %{public}@)", log: pinkhaLog, type: .info, spaceId, manifest.schemaVersion, manifest.manifestObjectId ?? "nil")
        case .failed(let message):
            os_log("[Pinkha] Space %{public}@ bootstrap failed: %{public}@", log: pinkhaLog, type: .error, spaceId, message)
        }
    }

    /// Atomically claims bootstrap ownership for a Space. Callers that lose the race must
    /// observe the in-flight state instead of starting a second schema mutation sequence.
    @discardableResult
    public func beginProvisioningIfNeeded(spaceId: String) -> Bool {
        beginProvisioningClaim(spaceId: spaceId) != nil
    }

    public func beginProvisioningClaim(spaceId: String) -> UUID? {
        let claim = states.withValue { dict -> UUID? in
            guard case .uninitialized = dict[spaceId]?.state ?? .uninitialized else {
                return nil
            }
            let claim = UUID()
            dict[spaceId] = Entry(state: .provisioning, claim: claim)
            return claim
        }
        if claim != nil { logState(.provisioning, for: spaceId) }
        return claim
    }

    /// Allows Phase 2 or any caller to asynchronously await readiness without polling blindly.
    public func awaitReadiness(spaceId: String, timeoutSeconds: TimeInterval = 10.0) async throws -> PinkhaSpaceManifest {
        let deadline = Date().addingTimeInterval(timeoutSeconds)
        while Date() < deadline {
            let current = state(for: spaceId)
            switch current {
            case .ready(let manifest):
                return manifest
            case .failed(let message):
                throw PinkhaBootstrapError.manifestStoreError("Bootstrap failed for space \(spaceId): \(message)")
            case .provisioning, .uninitialized:
                try await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }
        throw PinkhaBootstrapError.manifestStoreError("Timed out waiting for space \(spaceId) bootstrap readiness")
    }
}

private final class LockIsolated<Value>: @unchecked Sendable {
    private var _value: Value
    private var _lock = os_unfair_lock()

    init(_ value: Value) {
        self._value = value
    }

    var value: Value {
        os_unfair_lock_lock(&_lock)
        defer { os_unfair_lock_unlock(&_lock) }
        return _value
    }

    func withValue<Result>(_ body: (inout Value) throws -> Result) rethrows -> Result {
        os_unfair_lock_lock(&_lock)
        defer { os_unfair_lock_unlock(&_lock) }
        return try body(&_value)
    }
}
