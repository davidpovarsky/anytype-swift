import Foundation
import PinkhaKit
import Factory
import os.log

private let pinkhaLog = OSLog(subsystem: "com.anytype.pinkha", category: "Bootstrap")

public final class PinkhaBootstrapStateManager: Sendable {
    private let states = LockIsolated<[String: PinkhaSpaceBootstrapState]>([:])

    public init() {}

    public func state(for spaceId: String) -> PinkhaSpaceBootstrapState {
        states.value[spaceId] ?? .uninitialized
    }

    public func setState(_ state: PinkhaSpaceBootstrapState, for spaceId: String) {
        states.withValue { dict in
            dict[spaceId] = state
        }
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
