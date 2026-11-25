import Foundation
import UIKit
import SwiftUI
import Combine
import Services

/// Exact identities supplied by the host's existing annotation persistence owner.
/// This value neither selects an account nor grants access to a Space or object.
public struct AnytypeOriginalEditorBinding: Sendable, Equatable {
    public let accountID: String
    public let spaceID: String
    public let objectID: String
    public let hostProfileID: String
    public let annotationUUID: UUID
    public let expectedRevision: Int64
    public let sourceWitnessSHA256: String

    public init(
        accountID: String,
        spaceID: String,
        objectID: String,
        hostProfileID: String,
        annotationUUID: UUID,
        expectedRevision: Int64,
        sourceWitnessSHA256: String
    ) throws {
        let identities = [accountID, spaceID, objectID, hostProfileID]
        guard identities.allSatisfy({ !$0.isEmpty && !$0.utf8.contains(0) }),
              expectedRevision >= 0,
              sourceWitnessSHA256.utf8.count == 64,
              sourceWitnessSHA256.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
            throw AnytypeOriginalEditorHostError.invalidBinding
        }
        self.accountID = accountID
        self.spaceID = spaceID
        self.objectID = objectID
        self.hostProfileID = hostProfileID
        self.annotationUUID = annotationUUID
        self.expectedRevision = expectedRevision
        self.sourceWitnessSHA256 = sourceWitnessSHA256
    }

    public static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.accountID.utf8.elementsEqual(rhs.accountID.utf8)
            && lhs.spaceID.utf8.elementsEqual(rhs.spaceID.utf8)
            && lhs.objectID.utf8.elementsEqual(rhs.objectID.utf8)
            && lhs.hostProfileID.utf8.elementsEqual(rhs.hostProfileID.utf8)
            && lhs.annotationUUID == rhs.annotationUUID
            && lhs.expectedRevision == rhs.expectedRevision
            && lhs.sourceWitnessSHA256 == rhs.sourceWitnessSHA256
    }
}

public enum AnytypeOriginalEditorHostError: Error, Sendable, Equatable {
    case invalidBinding
    case missingAccount
    case wrongAccount
    case retiredSource
    case sourceAlreadyUsed
    case unsupportedAccountLifetime
    case unsupportedDocumentLifetime
    case notEditable
    case permissionReadinessTimeout
    case alreadyMounted
    case snapshotCaptureInProgress
}

/// The host retires this source synchronously before changing account, profile,
/// note, source witness or revision, including while opening is suspended.
/// Retirement never cancels or rolls back an already admitted original write.
@MainActor
public final class AnytypeOriginalEditorSourceLifetime {
    public nonisolated let binding: AnytypeOriginalEditorBinding
    internal nonisolated let lifetime = EditorDocumentWriteLifetime()
    private var claimed = false

    public init(binding: AnytypeOriginalEditorBinding) {
        self.binding = binding
    }

    public nonisolated var isCurrent: Bool { lifetime.token() != nil }

    public nonisolated func retire() {
        lifetime.markUnavailable()
    }

    internal func claim(for expected: AnytypeOriginalEditorBinding) throws {
        guard binding == expected else { throw AnytypeOriginalEditorHostError.invalidBinding }
        guard isCurrent else { throw AnytypeOriginalEditorHostError.retiredSource }
        guard !claimed else { throw AnytypeOriginalEditorHostError.sourceAlreadyUsed }
        claimed = true
    }
}

/// Retains the original prepared state, controller and coordinator. The host
/// supplies its existing source lifetime; no replacement block engine is created.
@MainActor
public final class AnytypeOriginalEditorHost {
    public let binding: AnytypeOriginalEditorBinding
    internal let preparedSession: PreparedEditorPageSession
    private let coordinator: EditorPageCoordinatorViewModel
    private let navigationProvider: ViewControllerProvider
    private let sourceLifetime: AnytypeOriginalEditorSourceLifetime
    private var accountObservation: AnyCancellable?
    private var mountedViewController: UIViewController?
    // Internal only: assigned from canonical native provenance by the localOnly
    // materializer. A caller cannot use historical provenance as remote authority.
    internal var snapshotTransportOriginHostProfileID: String?
    private var snapshotCaptureInProgress = false
    private var miniAppsInteraction: [CapturedInteraction]?
    private struct CapturedInteraction {
        weak var view: UIView?
        let wasEnabled: Bool
    }
    private var interactionBeforeCapture: [CapturedInteraction] = []

    internal init(
        binding: AnytypeOriginalEditorBinding,
        preparedSession: PreparedEditorPageSession,
        coordinator: EditorPageCoordinatorViewModel,
        navigationProvider: ViewControllerProvider,
        sourceLifetime: AnytypeOriginalEditorSourceLifetime,
        accountManager: any AccountManagerProtocol
    ) {
        self.binding = binding
        self.preparedSession = preparedSession
        self.coordinator = coordinator
        self.navigationProvider = navigationProvider
        self.sourceLifetime = sourceLifetime
        accountObservation = accountManager.accountPublisher.sink { [sourceLifetime, expected = binding.accountID] account in
            if !account.id.utf8.elementsEqual(expected.utf8) { sourceLifetime.retire() }
        }
    }

    internal func validateCurrentSource() throws {
        guard sourceLifetime.isCurrent else { throw AnytypeOriginalEditorHostError.retiredSource }
        try preparedSession.owner.validateOwnership()
    }

    /// Mount exactly the original EditorPageView and its prepared-session
    /// representable. A second mount cannot claim this session's first Host lease.
    public func makeViewController() throws -> UIViewController {
        try validateCurrentSource()
        guard mountedViewController == nil else { throw AnytypeOriginalEditorHostError.alreadyMounted }
        let controller = UIHostingController(rootView: EditorPageCoordinatorView(preparedModel: coordinator))
        navigationProvider.setScopedRootViewController(controller)
        mountedViewController = controller
        return controller
    }

    public func retire() {
        sourceLifetime.retire()
        preparedSession.retire()
        for view in ownedPresentedViews() { view.isUserInteractionEnabled = false }
        snapshotCaptureInProgress = false
        miniAppsInteraction = nil
        interactionBeforeCapture = []
        accountObservation = nil
    }

    /// UIKit sheets have their own view trees. Traverse only this Host's
    /// retained controller and its presentations, never another app window.
    private func ownedPresentedViews() -> [UIView] {
        var result: [UIView] = []
        var current = mountedViewController
        var visited = Set<ObjectIdentifier>()
        while let controller = current, visited.insert(ObjectIdentifier(controller)).inserted {
            if let view = controller.viewIfLoaded { result.append(view) }
            current = controller.presentedViewController
        }
        return result
    }

    /// The original callbacks reserve pending writes before the Owner drain.
    /// Only this retained Host's views are frozen. It is not a storage transaction.
    internal func beginMiniAppsInteraction() throws {
        try validateCurrentSource()
        guard miniAppsInteraction == nil, !snapshotCaptureInProgress else {
            throw AnytypeOriginalEditorHostError.snapshotCaptureInProgress
        }
        let views = ownedPresentedViews()
        miniAppsInteraction = views.map {
            CapturedInteraction(view: $0, wasEnabled: $0.isUserInteractionEnabled)
        }
        for view in views.reversed() { view.endEditing(true) }
        for view in views { view.isUserInteractionEnabled = false }
    }

    internal func endMiniAppsInteraction(restore: Bool = true) {
        let previous = miniAppsInteraction
        miniAppsInteraction = nil
        guard restore, let previous, (try? validateCurrentSource()) != nil,
              !preparedSession.owner.isCapturing else { return }
        for item in previous { item.view?.isUserInteractionEnabled = item.wasEnabled }
    }

    /// Original end-editing callbacks synchronously register their pending UI
    /// jobs before the exclusive Owner barrier starts. Freezing interaction is
    /// only admission control; it never substitutes for the real RPC drain.
    internal func beginSnapshotCapture() throws {
        try validateCurrentSource()
        guard !snapshotCaptureInProgress, miniAppsInteraction == nil else {
            throw AnytypeOriginalEditorHostError.snapshotCaptureInProgress
        }
        snapshotCaptureInProgress = true
        do {
            let views = ownedPresentedViews()
            // Synchronous original callbacks reserve their same-owner work
            // before any capture await. A child editor is included through its
            // actual presented controller and the existing parent tracking.
            for view in views.reversed() { view.endEditing(true) }
            try validateCurrentSource()
            interactionBeforeCapture = views.map {
                CapturedInteraction(view: $0, wasEnabled: $0.isUserInteractionEnabled)
            }
            for view in views { view.isUserInteractionEnabled = false }
        } catch {
            snapshotCaptureInProgress = false
            interactionBeforeCapture = []
            throw error
        }
    }

    /// The exclusive Owner operation already retired admissions before it
    /// released its barrier. Finish the source/controller cleanup before the
    /// terminal captured snapshot is returned to the persistence owner.
    internal func completeSnapshotCapture() {
        retire()
    }

    internal func failSnapshotCapture() {
        let previous = interactionBeforeCapture
        snapshotCaptureInProgress = false
        interactionBeforeCapture = []
        guard sourceLifetime.isCurrent, !preparedSession.owner.isCapturing,
              (try? preparedSession.owner.validateOwnership()) != nil else { return }
        for item in previous { item.view?.isUserInteractionEnabled = item.wasEnabled }
    }

    deinit {
        sourceLifetime.retire()
    }
}

extension AnytypeOriginalEditorModule {
    /// Opens only an explicitly bound, existing original object. Account/Space
    /// selection, authentication, import and repository creation remain outside
    /// this operation. The original open RPC and permissions must actually pass.
    ///
    /// `sourceIsCurrent` must be a synchronous, side-effect-free observation of
    /// the host's captured source. It must not perform database or network I/O.
    @MainActor
    public static func openExistingEditor(
        binding: AnytypeOriginalEditorBinding,
        sourceLifetime: AnytypeOriginalEditorSourceLifetime,
        sourceIsCurrent: @escaping @MainActor (AnytypeOriginalEditorBinding) -> Bool
    ) async throws -> AnytypeOriginalEditorHost {
        try sourceLifetime.claim(for: binding)
        do {
            try Task.checkCancellation()
            let accountManager = Container.shared.accountManager()
            let basicUserInfo = Container.shared.basicUserInfoStorage()
            guard !accountManager.account.id.isEmpty, !basicUserInfo.usersId.isEmpty else {
                throw AnytypeOriginalEditorHostError.missingAccount
            }
            guard accountManager.account.id.utf8.elementsEqual(binding.accountID.utf8),
                  basicUserInfo.usersId.utf8.elementsEqual(binding.accountID.utf8) else {
                throw AnytypeOriginalEditorHostError.wrongAccount
            }
            guard let accountLifetime = accountManager.editorWriteLifetime else {
                throw AnytypeOriginalEditorHostError.unsupportedAccountLifetime
            }
            let sourceCheck: @MainActor () -> Bool = {
                sourceLifetime.isCurrent
                    && accountManager.account.id.utf8.elementsEqual(binding.accountID.utf8)
                    && basicUserInfo.usersId.utf8.elementsEqual(binding.accountID.utf8)
                    && sourceIsCurrent(binding)
            }
            guard sourceCheck() else { throw AnytypeOriginalEditorHostError.retiredSource }
            // Capture both generations before opening, then give this exact
            // binding to the eventual owner. A later account/source value that
            // looks equal cannot recapture authority after retirement.
            let sourceBinding = try EditorDocumentWriteSourceBinding(
                lifetime: sourceLifetime.lifetime,
                accountLifetime: accountLifetime,
                isCurrent: sourceCheck
            )
            return try await makeHost(
                binding: binding, sourceLifetime: sourceLifetime,
                sourceBinding: sourceBinding, accountManager: accountManager
            )
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }

    /// Shared original construction for an already claimed host source. Callers
    /// retain the one-use claim and retire that source on failure. The exact
    /// captured binding reaches the original prepared session without recapture.
    @MainActor
    internal static func makeHost(
        binding: AnytypeOriginalEditorBinding,
        sourceLifetime: AnytypeOriginalEditorSourceLifetime,
        sourceBinding: EditorDocumentWriteSourceBinding,
        accountManager: any AccountManagerProtocol
    ) async throws -> AnytypeOriginalEditorHost {
        guard sourceLifetime.binding == binding,
              sourceBinding.lifetime === sourceLifetime.lifetime else {
            throw AnytypeOriginalEditorHostError.invalidBinding
        }
        try sourceBinding.validate()
        let data = EditorPageObject(objectId: binding.objectID, spaceId: binding.spaceID, mode: .handling)
        let navigationProvider = ViewControllerProvider()
        let navigationContext = NavigationContext(viewControllerProvider: navigationProvider)
        let session = try await PreparedEditorPageSessionFactory.prepare(
            data: data, sourceBinding: sourceBinding, navigationContext: navigationContext
        )
        // Keep the original coordinator as the real output and modal owner;
        // the already acquired root session is never opened a second time.
        let coordinator = try EditorPageCoordinatorViewModel(
            preparedSession: session, showHeader: true
        )
        let host = AnytypeOriginalEditorHost(
            binding: binding, preparedSession: session, coordinator: coordinator,
            navigationProvider: navigationProvider,
            sourceLifetime: sourceLifetime, accountManager: accountManager
        )
        try sourceBinding.validate()
        try host.validateCurrentSource()
        return host
    }

}
