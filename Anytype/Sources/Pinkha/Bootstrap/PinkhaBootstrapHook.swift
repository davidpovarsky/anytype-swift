import Foundation
import PinkhaKit
import Factory
import ProtobufMessages

public enum PinkhaBootstrapHook {
    #if DEBUG
    struct AcceptanceDependencies: Sendable {
        let stateManager: PinkhaBootstrapStateManager
        let service: any PinkhaSpaceBootstrapServiceProtocol
    }
    // A per-task component fixture. No shared registration, native account,
    // runtime feature gate, or original frozen capture is replaced.
    @TaskLocal static var acceptanceDependencies: AcceptanceDependencies?
    #endif
    /// Invoked when a Space becomes active and its middleware and subscriptions are ready.
    /// Runs Pinkha bootstrap asynchronously in the background with full state observability.
    public static func handleSpaceActivated(spaceId: String) {
        scheduleBootstrap(spaceId: spaceId, accountCapture: nil)
    }

    /// The original selection owns this capture. It is never reacquired inside
    /// the scheduled task, including when a failed Bootstrap claim is retried.
    static func handleSpaceActivated(spaceId: String, accountCapture: EditorDocumentWriteCapture) {
        scheduleBootstrap(spaceId: spaceId, accountCapture: accountCapture)
    }

    private static func scheduleBootstrap(spaceId: String, accountCapture: EditorDocumentWriteCapture?) {
        guard PinkhaRuntime.enabled else { return }
        if let accountCapture, (try? accountCapture.validate()) == nil { return }
        #if DEBUG
        let stateManager = acceptanceDependencies?.stateManager ?? Container.shared.pinkhaBootstrapStateManager()
        #else
        let stateManager = Container.shared.pinkhaBootstrapStateManager()
        #endif
        guard let claim = stateManager.beginProvisioningClaim(spaceId: spaceId) else { return }
        // Keep legacy callers' actual context. A selected-Space invocation uses
        // its frozen original account for every original queued native dispatch.
        let binding = accountCapture?.accountDispatchBinding() ?? InvocationDispatchContext.binding
        Task {
            do {
                // This original lifetime admission precedes all Bootstrap work,
                // including cache/manifest access. Actual account transitions
                // wait for the lease; a task queued until after reopen is denied.
                let admissions = try EditorDocumentWriteCapture.acquireAll(accountCapture.map { [$0] } ?? [])
                defer { for admission in admissions { admission.cancel() } }
                let manifest = try await InvocationDispatchContext.$binding.withValue(binding) {
                    try accountCapture?.validate()
                    #if DEBUG
                    let service = acceptanceDependencies?.service ?? Container.shared.pinkhaBootstrapService()
                    let manifest = try await service.bootstrapSpace(spaceId: spaceId)
                    #else
                    let manifest = try await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: spaceId)
                    #endif
                    try accountCapture?.validate()
                    return manifest
                }
                stateManager.setState(.ready(manifest), for: spaceId, claim: claim)
            } catch PinkhaBootstrapAdmissionError.accountClosed {
                stateManager.setState(.uninitialized, for: spaceId, claim: claim)
            } catch {
                stateManager.setState(.failed(error.localizedDescription), for: spaceId, claim: claim)
            }
        }
    }
}
