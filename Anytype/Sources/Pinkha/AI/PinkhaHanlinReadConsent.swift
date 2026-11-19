import PinkhaHanlinCore
import Foundation
import UIKit
import HanlinHostContracts

/// A real native user decision for this presentation only. Starts denied; never issued by a model.
@MainActor
final class PinkhaHanlinReadConsent {
    private var decision = PinkhaHanlinReadConsentDecision()
    var authorized: Bool { decision.authorized }
    private var alert: PinkhaHanlinConsentController?

    func request(from presenter: UIViewController, locale: Locale,
                 validate: @escaping @MainActor () throws -> Void) async throws {
        try validate()
        try Task.checkCancellation()
        if authorized { return }
        guard !decision.revoked, !decision.isPending, presenter.presentedViewController == nil else { throw HanlinHostError.denied }
        let current = PinkhaHanlinReadConsentDecision()
        decision = current
        let hebrew = locale.language.languageCode?.identifier == "he"
        let allowed: Bool = await withTaskCancellationHandler {
          await withCheckedContinuation { continuation in
            guard !Task.isCancelled, decision === current, current.begin({ [weak self, weak current] allowed in
                if let self, let current, self.decision === current { self.alert = nil }
                continuation.resume(returning: allowed)
            }) else { continuation.resume(returning: false); return }
            let alert = PinkhaHanlinConsentController(purpose: .readContext,
                title: hebrew ? "לאפשר קריאת טקסט?" : "Allow document text access?",
                explanation: hebrew ? "לאפשר לצ׳אט הזה לקרוא טקסט מהמסמך הנוכחי או מהבלוקים שנבחרו? יצירת דף חדש דורשת אישור נפרד." : "Allow this chat presentation to read plain text from the current document or selected text blocks? Creating a new page requires a separate confirmation.",
                allowTitle: hebrew ? "לאפשר לצ׳אט הזה" : "Allow for this presentation",
                cancelTitle: hebrew ? "ביטול" : "Cancel", decision: current, validate: validate)
            self.alert = alert
            presenter.present(alert, animated: true) { [weak current, weak alert] in
                if alert?.viewIfLoaded?.window == nil { current?.resolve(false) }
            }
          }
        } onCancel: { [weak self] in
            Task { @MainActor in self?.revoke() }
        }
        try validate()
        try Task.checkCancellation()
        guard allowed, decision === current, current.authorized else { throw HanlinHostError.denied }
    }

    func revoke() {
        let ownedAlert = alert
        decision.revoke()
        ownedAlert?.dismiss(animated: false)
    }
}
