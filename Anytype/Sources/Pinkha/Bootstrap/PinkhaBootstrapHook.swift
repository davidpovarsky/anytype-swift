import Foundation
import PinkhaKit
import Factory

public enum PinkhaBootstrapHook {
    /// Invoked when a Space becomes active and its middleware and subscriptions are ready.
    /// Runs Pinkha bootstrap asynchronously in the background with full state observability.
    public static func handleSpaceActivated(spaceId: String) {
        guard PinkhaRuntime.enabled else { return }
        let stateManager = Container.shared.pinkhaBootstrapStateManager()
        guard stateManager.beginProvisioningIfNeeded(spaceId: spaceId) else { return }
        Task {
            do {
                let manifest = try await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: spaceId)
                stateManager.setState(.ready(manifest), for: spaceId)
            } catch {
                stateManager.setState(.failed(error.localizedDescription), for: spaceId)
            }
        }
    }
}
