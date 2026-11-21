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
    private let state: EditorPageViewState
    private let sourceLifetime: AnytypeOriginalEditorSourceLifetime
    private var accountObservation: AnyCancellable?
    private var mountedViewController: UIViewController?
    private var snapshotCaptureInProgress = false
    private var interactionBeforeCapture: Bool?

    internal init(
        binding: AnytypeOriginalEditorBinding,
        preparedSession: PreparedEditorPageSession,
        state: EditorPageViewState,
        sourceLifetime: AnytypeOriginalEditorSourceLifetime,
        accountManager: any AccountManagerProtocol
    ) {
        self.binding = binding
        self.preparedSession = preparedSession
        self.state = state
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
        let controller = UIHostingController(rootView: EditorPageView(preparedState: state))
        mountedViewController = controller
        return controller
    }

    public func retire() {
        sourceLifetime.retire()
        preparedSession.retire()
        mountedViewController?.viewIfLoaded?.isUserInteractionEnabled = false
        snapshotCaptureInProgress = false
        interactionBeforeCapture = nil
        accountObservation = nil
    }

    /// Original end-editing callbacks synchronously register their pending UI
    /// jobs before the exclusive Owner barrier starts. Freezing interaction is
    /// only admission control; it never substitutes for the real RPC drain.
    internal func beginSnapshotCapture() throws {
        try validateCurrentSource()
        guard !snapshotCaptureInProgress else {
            throw AnytypeOriginalEditorHostError.snapshotCaptureInProgress
        }
        snapshotCaptureInProgress = true
        do {
            if let view = mountedViewController?.viewIfLoaded {
                let previous = view.isUserInteractionEnabled
                view.endEditing(true)
                try validateCurrentSource()
                interactionBeforeCapture = previous
                view.isUserInteractionEnabled = false
            }
        } catch {
            snapshotCaptureInProgress = false
            interactionBeforeCapture = nil
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
        interactionBeforeCapture = nil
        guard let previous, sourceLifetime.isCurrent, !preparedSession.owner.isCapturing,
              (try? preparedSession.owner.validateOwnership()) != nil else { return }
        mountedViewController?.viewIfLoaded?.isUserInteractionEnabled = previous
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
            let data = EditorPageObject(objectId: binding.objectID, spaceId: binding.spaceID, mode: .handling)
            let session = try await PreparedEditorPageSessionFactory.prepare(
                data: data, sourceBinding: sourceBinding
            )
            let state = try EditorPageModuleAssembly().buildStateModel(
                preparedSession: session, output: nil, showHeader: true, torahSession: nil
            )
            let host = AnytypeOriginalEditorHost(
                binding: binding, preparedSession: session, state: state,
                sourceLifetime: sourceLifetime, accountManager: accountManager
            )
            try host.validateCurrentSource()
            return host
        } catch {
            sourceLifetime.retire()
            throw error
        }
    }

}
