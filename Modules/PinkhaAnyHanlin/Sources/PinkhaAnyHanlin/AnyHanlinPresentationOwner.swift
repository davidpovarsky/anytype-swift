import Foundation
import HanlinHostContracts
import PinkhaAnyHost

/// Captured by the real presenting UI. A model/tool argument cannot supply it.
/// The owner must check actual foreground scene, account, Space, mounted editor,
/// current selection and original presentation identity before returning.
public struct AnyHanlinPresentationScope: Sendable {
    public let accountID: String
    public let spaceID: String
    public let sceneID: UUID
    public let ownerID: UUID
    public let document: AnyEditorSnapshot?
    public let selection: [String]

    public init(accountID: String, spaceID: String, sceneID: UUID, ownerID: UUID,
                document: AnyEditorSnapshot?, selection: [String]) {
        self.accountID = accountID; self.spaceID = spaceID; self.sceneID = sceneID
        self.ownerID = ownerID; self.document = document; self.selection = selection
    }
}

/// Native UI binding; the shared router remains the only SDK authority policy.
/// Installation is explicit. Merely constructing a scope or queueing navigation
/// never constitutes read consent, write approval, or proof of UI presentation.
@MainActor
public protocol AnyHanlinPresentationOwner: AnyObject, Sendable {
    func currentScope() throws -> AnyHanlinPresentationScope
    func install(session: HanlinHostSession,
                 invalidate: @escaping @Sendable () -> Void) throws
    func presentReadConsent(context: HanlinHostContext,
                            answer: @escaping @MainActor (Bool) -> Void) throws
    func dismissPendingPrompts()
    /// Validate the real visible document and, when present, visible block cell.
    /// The callback is called only for a previously queued exact destination.
    func validateMounted(_ destination: HanlinHostDestination) throws
}
