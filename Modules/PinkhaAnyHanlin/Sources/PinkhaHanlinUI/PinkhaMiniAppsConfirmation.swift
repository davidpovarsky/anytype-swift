#if canImport(UIKit)
import UIKit

/// A returned operation may not silently expand the user's original request.
/// Engine owners cancel this exact presentation before transferring authority.
@MainActor
public final class PinkhaMiniAppsConfirmation: NSObject, UIAdaptivePresentationControllerDelegate {
    private var continuation: CheckedContinuation<Bool, Never>?
    private weak var alert: UIAlertController?

    private var unregister: (@MainActor (UIViewController) -> Void)?

    public override init() { super.init() }

    public func request(from presenter: UIViewController, title: String, message: String,
                        applyTitle: String, cancelTitle: String,
                        register: @escaping @MainActor (UIViewController) -> Void = { _ in },
                        unregister: @escaping @MainActor (UIViewController) -> Void = { _ in }) async -> Bool {
        guard continuation == nil, presenter.presentedViewController == nil else { return false }
        return await withTaskCancellationHandler {
            await withCheckedContinuation { continuation in
                guard !Task.isCancelled else { continuation.resume(returning: false); return }
                self.continuation = continuation
                self.unregister = unregister
                let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
                alert.addAction(UIAlertAction(title: cancelTitle, style: .cancel) { [weak self] _ in self?.finish(false) })
                alert.addAction(UIAlertAction(title: applyTitle, style: .default) { [weak self] _ in self?.finish(true) })
                alert.view.accessibilityIdentifier = "pinkha-miniapps-operation-confirmation"
                self.alert = alert
                alert.presentationController?.delegate = self
                register(alert)
                presenter.present(alert, animated: true)
            }
        } onCancel: {
            Task { @MainActor [weak self] in self?.cancel() }
        }
    }

    public func cancel() { finish(false) }

    public func presentationControllerDidDismiss(_ presentationController: UIPresentationController) { finish(false) }

    private func finish(_ accepted: Bool) {
        guard let pending = continuation else { return }
        continuation = nil
        let alert = alert; self.alert = nil
        let unregister = unregister; self.unregister = nil
        guard let alert, alert.presentingViewController != nil else {
            if let alert { unregister?(alert) }
            pending.resume(returning: accepted); return
        }
        alert.dismiss(animated: accepted) {
            unregister?(alert)
            pending.resume(returning: accepted)
        }
    }
}
#endif
