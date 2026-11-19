#if canImport(UIKit)
import UIKit
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyUI

@MainActor
final class AnyNativeFocusLifecycleTests: XCTestCase {
    private func window() -> UIWindow {
        let value: UIWindow
        if let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene })
            .first(where: { $0.activationState == .foregroundActive }) {
            value = UIWindow(windowScene: scene)
        } else { value = UIWindow(frame: .zero) }
        value.frame = CGRect(x: 0, y: 0, width: 400, height: 800)
        value.rootViewController = UIViewController()
        value.makeKeyAndVisible()
        return value
    }
    private func input() -> AnyNativeTextView {
        let value = AnyNativeTextView(frame: CGRect(x: 0, y: 0, width: 360, height: 100))
        value.text = "abc אבג"; value.blockID = "block"
        return value
    }
    private func intent(_ location: Int = 0) -> AnyNativeFocusIntent {
        .init(blockID: "block", ownerID: UUID(), nativeVersion: .object(["text": .string("v1")]),
              source: "abc אבג", selection: .init(location: location, length: 0))
    }
    private func turn() async {
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            DispatchQueue.main.async { continuation.resume() }
        }
    }

    func testDetachedRequestWaitsForAttachmentAndIsConsumedOnce() async {
        let fixture = window(), view = input()
        defer { view.onAttachmentReadiness = nil; fixture.endEditing(true); fixture.isHidden = true }
        let coordinator = AnyNativeFocusCoordinator(validate: { _ in true }, resolve: { _ in view })
        view.onAttachmentReadiness = { coordinator.readinessChanged(.attachment) }
        coordinator.request(intent(7))
        XCTAssertFalse(view.isFirstResponder); XCTAssertTrue(coordinator.hasPending)
        fixture.rootViewController!.view.addSubview(view)
        await turn()
        XCTAssertTrue(view.isFirstResponder); XCTAssertFalse(coordinator.hasPending)
        XCTAssertEqual(view.selectedRange, NSRange(location: 7, length: 0))
        view.selectedRange = NSRange(location: 2, length: 0)
        coordinator.readinessChanged(.layout)
        XCTAssertEqual(view.selectedRange, NSRange(location: 2, length: 0))
    }

    func testKeyWindowReadinessRetriesNativeRefusalWithoutRenderPolling() async {
        let fixture = window(), view = input(), refusal = FocusNativeRefusal()
        defer { fixture.endEditing(true); fixture.isHidden = true }
        fixture.rootViewController!.view.addSubview(view)
        view.delegate = refusal
        let coordinator = AnyNativeFocusCoordinator(validate: { _ in true }, resolve: { _ in view })
        coordinator.request(intent())
        XCTAssertEqual(refusal.attempts, 1); XCTAssertFalse(view.isFirstResponder)
        for _ in 0..<5 { coordinator.readinessChanged(.layout) }
        await turn()
        XCTAssertEqual(refusal.attempts, 1)
        refusal.allow = true
        let other = window()
        defer { other.isHidden = true }
        XCTAssertTrue(other.isKeyWindow)
        fixture.makeKeyAndVisible()
        await turn()
        XCTAssertEqual(refusal.attempts, 2)
        XCTAssertTrue(view.isFirstResponder); XCTAssertFalse(coordinator.hasPending)
    }

    func testNewUserFocusCancelsDetachedRequest() async {
        let fixture = window(), pending = input(), selected = input()
        defer { fixture.endEditing(true); fixture.isHidden = true }
        fixture.rootViewController!.view.addSubview(selected)
        let coordinator = AnyNativeFocusCoordinator(validate: { _ in true }, resolve: { _ in pending })
        coordinator.request(intent())
        XCTAssertTrue(selected.becomeFirstResponder())
        coordinator.userInteraction()
        selected.selectedRange = NSRange(location: 3, length: 0)
        fixture.rootViewController!.view.addSubview(pending)
        coordinator.readinessChanged(.attachment)
        await turn()
        XCTAssertTrue(selected.isFirstResponder); XCTAssertFalse(pending.isFirstResponder)
        XCTAssertEqual(selected.selectedRange, NSRange(location: 3, length: 0))
        XCTAssertFalse(coordinator.hasPending)
    }

    func testOwnerOrVersionChangeCancelsOldRequestBeforeRebind() {
        let fixture = window(), view = input()
        defer { fixture.endEditing(true); fixture.isHidden = true }
        var current = true
        let coordinator = AnyNativeFocusCoordinator(validate: { _ in current }, resolve: { _ in view })
        coordinator.request(intent())
        current = false
        fixture.rootViewController!.view.addSubview(view)
        coordinator.readinessChanged(.attachment)
        XCTAssertFalse(view.isFirstResponder); XCTAssertFalse(coordinator.hasPending)
        current = true
        coordinator.readinessChanged(.keyWindow)
        XCTAssertFalse(view.isFirstResponder)
        coordinator.request(intent(7))
        XCTAssertTrue(view.isFirstResponder)
    }

    func testLockedViewDenialDoesNotReviveAfterUnlock() {
        let fixture = window(), view = input()
        defer { fixture.endEditing(true); fixture.isHidden = true }
        fixture.rootViewController!.view.addSubview(view)
        view.isEditable = false
        let coordinator = AnyNativeFocusCoordinator(validate: { _ in true }, resolve: { _ in view })
        coordinator.request(intent())
        XCTAssertFalse(coordinator.hasPending); XCTAssertFalse(view.isFirstResponder)
        view.isEditable = true
        coordinator.readinessChanged(.keyWindow)
        XCTAssertFalse(view.isFirstResponder)
    }

    func testCurrentResponderRequestDoesNotStealFocusAfterLaterInput() async {
        let fixture = window(), first = input(), second = input()
        defer { fixture.endEditing(true); fixture.isHidden = true }
        fixture.rootViewController!.view.addSubview(first)
        fixture.rootViewController!.view.addSubview(second)
        XCTAssertTrue(first.becomeFirstResponder())
        let coordinator = AnyNativeFocusCoordinator(validate: { _ in true }, resolve: { _ in first })
        coordinator.request(intent(7))
        XCTAssertEqual(first.selectedRange, NSRange(location: 7, length: 0))
        XCTAssertTrue(second.becomeFirstResponder())
        coordinator.readinessChanged(.layout); coordinator.readinessChanged(.keyWindow)
        await turn()
        XCTAssertTrue(second.isFirstResponder); XCTAssertFalse(first.isFirstResponder)
    }
}

@MainActor private final class FocusNativeRefusal: NSObject, UITextViewDelegate {
    var allow = false
    private(set) var attempts = 0
    func textViewShouldBeginEditing(_ textView: UITextView) -> Bool {
        attempts += 1; return allow
    }
}
#endif
