import Foundation
import PinkhaKit
import os.log

private let pinkhaLog = OSLog(subsystem: "com.anytype.pinkha", category: "Bootstrap")

public final class PinkhaBootstrapStateManager: Sendable {
    private let states = PinkhaBootstrapStateStorage()

    public init() {}

    public func state(for spaceId: String) -> PinkhaSpaceBootstrapState {
        states.state(for: spaceId)
    }

    public func setState(_ state: PinkhaSpaceBootstrapState, for spaceId: String) {
        states.setState(state, for: spaceId)
        logState(state, for: spaceId)
    }

    public func setState(_ state: PinkhaSpaceBootstrapState, for spaceId: String, claim: UUID) {
        let accepted = states.setState(state, for: spaceId, claim: claim)
        if accepted { logState(state, for: spaceId) }
    }

    public func resetForAccountChange() {
        states.resetForAccountChange()
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
        let claim = states.beginProvisioningClaim(spaceId: spaceId)
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
