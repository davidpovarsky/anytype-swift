import Foundation
import UIKit
import HanlinHostContracts

/// A real native user decision for this presentation only. Starts denied; never issued by a model.
@MainActor
final class PinkhaHanlinReadConsent {
    private let decision = PinkhaHanlinReadConsentDecision()
    var authorized: Bool { decision.authorized }
    private var alert: UIAlertController?

    func request(from presenter: UIViewController, locale: Locale,
                 validate: @escaping @MainActor () throws -> Void) async throws {
        try validate()
        try Task.checkCancellation()
        if authorized { return }
        guard !decision.revoked, !decision.isPending, presenter.presentedViewController == nil else { throw HanlinHostError.denied }
        let hebrew = locale.language.languageCode?.identifier == "he"
        let allowed: Bool = await withTaskCancellationHandler {
          await withCheckedContinuation { continuation in
            guard !Task.isCancelled, decision.begin({ [weak self] allowed in
                self?.alert = nil
                continuation.resume(returning: allowed)
            }) else { continuation.resume(returning: false); return }
            let alert = UIAlertController(title: hebrew ? "לאפשר קריאת טקסט?" : "Allow document text access?",
                message: hebrew ? "לאפשר לצ׳אט הזה לקרוא טקסט מהמסמך הנוכחי או מהבלוקים שנבחרו? יצירת דף חדש דורשת אישור נפרד." : "Allow this chat presentation to read plain text from the current document or selected text blocks? Creating a new page requires a separate confirmation.",
                preferredStyle: .alert)
            self.alert = alert
            // A supported UIView lifecycle observer detects programmatic removal too; no UIAlertController subclass.
            let disappearance = PinkhaHanlinPromptWindowObserver()
            disappearance.onDisappearance = { [weak self] in self?.decision.resolve(false) }
            disappearance.isUserInteractionEnabled = false
            disappearance.isAccessibilityElement = false
            alert.view.addSubview(disappearance)
            alert.addAction(UIAlertAction(title: hebrew ? "ביטול" : "Cancel", style: .cancel) { [weak self] _ in self?.decision.resolve(false) })
            alert.addAction(UIAlertAction(title: hebrew ? "לאפשר לצ׳אט הזה" : "Allow for this presentation", style: .default) { [weak self] _ in
                do { try validate(); self?.decision.resolve(true) }
                catch { self?.decision.resolve(false) }
            })
            presenter.present(alert, animated: true) { [weak self, weak alert] in
                if alert?.viewIfLoaded?.window == nil { self?.decision.resolve(false) }
            }
          }
        } onCancel: { [weak self] in
            Task { @MainActor in self?.revoke() }
        }
        try validate()
        try Task.checkCancellation()
        guard allowed, decision.authorized else { throw HanlinHostError.denied }
    }

    func revoke() {
        let ownedAlert = alert
        decision.revoke()
        ownedAlert?.dismiss(animated: false)
    }
}

@MainActor
private final class PinkhaHanlinPromptWindowObserver: UIView {
    var onDisappearance: (() -> Void)?
    private var wasMounted = false

    override func didMoveToWindow() {
        super.didMoveToWindow()
        if window != nil { wasMounted = true }
        else if wasMounted {
            let callback = onDisappearance
            onDisappearance = nil
            callback?()
        }
    }
}
