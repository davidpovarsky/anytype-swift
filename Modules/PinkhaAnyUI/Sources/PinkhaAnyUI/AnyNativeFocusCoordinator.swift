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
        pending = intent; waitingAfterNativeRefusal = false
        if attemptImmediately { readinessChanged(.layout) }
    }

    func cancel() { pending = nil; waitingAfterNativeRefusal = false }
    func userInteraction() { if !applying { cancel() } }

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

    @objc private func windowBecameKey(_ notification: Notification) { readinessChanged(.keyWindow) }
}
#endif
