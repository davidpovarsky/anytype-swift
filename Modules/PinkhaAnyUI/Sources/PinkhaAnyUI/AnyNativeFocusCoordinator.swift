#if canImport(UIKit)
import Foundation
import UIKit
import PinkhaAnyEngine

struct AnyNativeFocusIntent {
    let id = UUID()
    let blockID: String
    let ownerID: UUID
    let nativeVersion: AnyJSON?
    let source: String
    let selection: NSRange
}

/// A one-shot mounted-owner intent, fulfilled only by real UIKit readiness.
/// Native refusal cannot start timed retries, and later input cancels the old
/// request before a detached/reused cell has an opportunity to steal focus.
@MainActor
final class AnyNativeFocusCoordinator: NSObject {
    enum Readiness: Equatable { case layout, attachment, keyWindow }
    private let validate: (AnyNativeFocusIntent) -> Bool
    private let resolve: (AnyNativeFocusIntent) -> UITextView?
    private var pending: AnyNativeFocusIntent?
    private var resolving = false
    private var waitingAfterNativeRefusal = false
    private struct DeferredReadiness {
        let deliveryID: UUID
        let intentID: UUID
        var event: Readiness
    }
    private var deferredReadiness: DeferredReadiness?
    private(set) var applying = false
    var hasPending: Bool { pending != nil }

    init(validate: @escaping (AnyNativeFocusIntent) -> Bool,
         resolve: @escaping (AnyNativeFocusIntent) -> UITextView?) {
        self.validate = validate; self.resolve = resolve
        super.init()
        NotificationCenter.default.addObserver(self, selector: #selector(windowBecameKey),
            name: UIWindow.didBecomeKeyNotification, object: nil)
    }

    deinit { NotificationCenter.default.removeObserver(self) }

    func request(_ intent: AnyNativeFocusIntent, attemptImmediately: Bool = true) {
        deferredReadiness = nil
        pending = intent; waitingAfterNativeRefusal = false
        if attemptImmediately { readinessChanged(.layout) }
    }

    func cancel() { pending = nil; waitingAfterNativeRefusal = false; deferredReadiness = nil }
    func userInteraction() { if !applying { cancel() } }

    /// UIKit may invoke snapshot completions synchronously inside a SwiftUI
    /// representable update. Acquiring a responder on that stack can reenter
    /// UIKit's layout/responder machinery before the update has unwound.
    /// Deliver one coalesced readiness event on the next main-queue turn; this
    /// is not a timer or a retry. The intent and its owner/version are checked
    /// again at delivery, and real user input cancels the queued handoff.
    func readinessChangedAfterUIUpdate(_ event: Readiness) {
        guard !resolving, let intent = pending else { return }
        if waitingAfterNativeRefusal && event == .layout { return }
        if var queued = deferredReadiness, queued.intentID == intent.id {
            // A real attachment/key-window event must not be downgraded to a
            // layout event while waiting after a native refusal.
            if event != .layout { queued.event = event; deferredReadiness = queued }
            return
        }
        let deliveryID = UUID()
        deferredReadiness = .init(deliveryID: deliveryID, intentID: intent.id, event: event)
        DispatchQueue.main.async { [weak self] in
            guard let self, let delivery = self.deferredReadiness,
                  delivery.deliveryID == deliveryID else { return }
            self.deferredReadiness = nil
            guard self.pending?.id == delivery.intentID else { return }
            self.readinessChanged(delivery.event)
        }
    }

    func readinessChanged(_ event: Readiness) {
        guard !resolving, let intent = pending else { return }
        guard validate(intent) else { cancel(); return }
        if waitingAfterNativeRefusal && event == .layout { return }
        resolving = true
        defer { resolving = false }
        guard let input = resolve(intent), let window = input.window,
              window.isKeyWindow, !window.isHidden else { return }
        guard pending?.id == intent.id, validate(intent) else { return }
        guard input.isEditable, input.isSelectable,
              (try? AnyInlineMarkdown(literal: input.text ?? "").sourceRange(for: intent.selection)) != nil else {
            cancel(); return
        }
        // Consume before calling UIKit; its delegate may synchronously deliver
        // editing/selection notifications. A genuine refusal waits for an
        // attachment/key-window event, not another render or queued timer.
        pending = nil; waitingAfterNativeRefusal = false; applying = true
        let acquired = input.isFirstResponder || input.becomeFirstResponder()
        if acquired, input.isFirstResponder { input.selectedRange = intent.selection }
        applying = false
        if !acquired, validate(intent), pending == nil {
            pending = intent; waitingAfterNativeRefusal = true
        }
    }

    @objc private func windowBecameKey(_ notification: Notification) {
        readinessChangedAfterUIUpdate(.keyWindow)
    }
}
#endif
