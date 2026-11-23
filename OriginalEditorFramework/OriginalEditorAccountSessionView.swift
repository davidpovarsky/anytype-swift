import Foundation
import SwiftUI
import UIKit

/// Composition of the existing original account coordinator and neutral Space
/// picker. The process owner supplies/retains all original consumer tasks.
@MainActor
internal struct OriginalEditorAccountSessionView: View {
    let owner: OriginalEditorAccountRuntimeAttempt

    var body: some View {
        Group {
            if owner.hasFailure {
                failure
            } else if let coordinator = owner.coordinator {
                ApplicationCoordinatorView(
                    model: coordinator,
                    initial: AnyView(LaunchView()),
                    home: AnyView(spacePicker)
                )
            } else {
                LaunchView()
            }
        }
    }

    private var spacePicker: some View {
        QuickCaptureSpacePickerView(
            spaces: owner.spaces,
            selectedSpaceId: owner.selectedSpaceID,
            draftSpaceIds: [],
            isProcessing: owner.isProcessing || owner.isClosing || owner.isClosed,
            onSelect: { owner.select($0) }
        )
    }

    private var failure: some View {
        VStack(spacing: 16) {
            ErrorStateView(message: Loc.Error.Common.message)
            if owner.closeFailed {
                Button(Loc.tryAgain) { owner.requestRetryClose() }
            } else if !owner.isClosed {
                Button(Loc.cancel) { owner.requestClose() }
                    .disabled(owner.isClosing)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.Background.primary)
    }
}

/// All environment effects are scoped to this controller/view, never UIWindow.
/// Dismissal before ready retains the true close operation; dismissal after
/// ready leaves account/event handling alive for the separately held session.
@MainActor
internal final class OriginalEditorAccountHostingController:
    UIHostingController<AnyView>, UIAdaptivePresentationControllerDelegate {
    private let owner: OriginalEditorAccountRuntimeAttempt
    private var appeared = false

    init(owner: OriginalEditorAccountRuntimeAttempt) {
        self.owner = owner
        super.init(rootView: AnyView(EmptyView()))
        loadViewIfNeeded()
        rootView = AnyView(
            OriginalEditorAccountSessionView(owner: owner)
                .setKeyboardDismissEnv(view: view)
                .setPresentedDismissEnv(rootViewController: self)
                .setAppInterfaceStyleEnv(rootViewController: self)
        )
    }

    @available(*, unavailable)
    required dynamic init?(coder aDecoder: NSCoder) {
        fatalError("Original account presentation must be created by its owned factory")
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        appeared = true
        presentationController?.delegate = self
        owner.presentationDidAppear()
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        if appeared && (isBeingDismissed || (presentingViewController == nil && parent == nil)) {
            owner.presentationDidDismiss()
        }
    }

    func presentationControllerDidDismiss(_ presentationController: UIPresentationController) {
        guard presentationController.presentedViewController === self else { return }
        owner.presentationDidDismiss()
    }
}
