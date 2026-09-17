import Foundation
import PinkhaKit
import Factory

public enum PinkhaBootstrapHook {
    /// Invoked when a Space becomes active and its middleware and subscriptions are ready.
    /// Runs Pinkha bootstrap asynchronously in the background.
    public static func handleSpaceActivated(spaceId: String) {
        guard PinkhaRuntime.enabled else { return }
        Task {
            _ = try? await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: spaceId)
        }
    }
}
