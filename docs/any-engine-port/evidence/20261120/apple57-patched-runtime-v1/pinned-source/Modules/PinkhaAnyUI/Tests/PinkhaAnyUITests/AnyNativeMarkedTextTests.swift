#if canImport(UIKit)
import UIKit
import XCTest
@testable import PinkhaAnyUI

/// Exercises the production UITextView subclass and real UITextInput marked
/// ranges. These are simulator contracts, not a claim about every keyboard.
@MainActor
final class AnyNativeMarkedTextTests: XCTestCase {
    private func mounted(_ text: String) -> (UIWindow, AnyNativeTextView) {
        let window: UIWindow
        if let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene })
            .first(where: { $0.activationState == .foregroundActive }) {
            window = UIWindow(windowScene: scene)
        } else { window = UIWindow(frame: .zero) }
        window.frame = CGRect(x: 0, y: 0, width: 400, height: 800)
        let controller = UIViewController()
        window.rootViewController = controller
        let input = AnyNativeTextView(frame: CGRect(x: 0, y: 0, width: 360, height: 300))
        controller.view.addSubview(input)
        input.text = text
        window.makeKeyAndVisible()
        XCTAssertTrue(input.becomeFirstResponder())
        return (window, input)
    }

    func testFirstMarkedInputBeginsBeforeMutationAndRepeatedUpdatesKeepTheMarkedRange() throws {
        let (window, input) = mounted("אב")
        defer { input.resignFirstResponder(); window.isHidden = true }
        input.selectedRange = NSRange(location: 2, length: 0)
        var begins = 0, ends = 0
        input.onMarkedBegin = { view in
            begins += 1
            XCTAssertEqual(view.text, "אב")
            XCTAssertTrue(view.isComposingMarkedText)
            return true
        }
        input.onMarkedEnd = { _, allowed in ends += 1; XCTAssertTrue(allowed) }
        input.setMarkedText("שָ", selectedRange: NSRange(location: 2, length: 0))
        XCTAssertEqual(input.text, "אבשָ")
        XCTAssertNotNil(input.markedTextRange)
        XCTAssertTrue(input.isComposingMarkedText)
        input.setMarkedText("שָׁ", selectedRange: NSRange(location: 3, length: 0))
        XCTAssertEqual(input.text, "אבשָׁ")
        XCTAssertNotNil(input.markedTextRange)
        XCTAssertEqual(begins, 1); XCTAssertEqual(ends, 0)
        input.unmarkText(); input.unmarkText()
        XCTAssertNil(input.markedTextRange)
        XCTAssertFalse(input.isComposingMarkedText)
        XCTAssertEqual(ends, 1)
    }

    func testActualMarkedBufferUsesImmutableRawProjectionUntilCommit() throws {
        let original = try AnyNativeTextComposition(source: "**ש**", selection: NSRange(location: 1, length: 0))
        let (window, input) = mounted(original.baseline.display)
        defer { input.resignFirstResponder(); window.isHidden = true }
        input.selectedRange = original.initialSelection
        var raw = original.baseline.source
        input.onMarkedProposal = { _, display, selection in
            do { raw = try original.source(display: display, selection: selection); return true }
            catch { XCTFail("Unexpected projection failure: \(error)"); return false }
        }
        input.setMarkedText("ָ", selectedRange: NSRange(location: 1, length: 0))
        input.setMarkedText("ָׁ", selectedRange: NSRange(location: 2, length: 0))
        XCTAssertEqual(input.text, "שָׁ")
        XCTAssertEqual(raw, "**שָׁ**")
        XCTAssertEqual(original.baseline.source, "**ש**")
        XCTAssertNotNil(input.markedTextRange)
        input.unmarkText()
        XCTAssertEqual(input.text, "שָׁ")
    }

    func testRecoveryCapturesLatestVisibleTextAndNeverRequestsASave() {
        let (window, input) = mounted("a")
        defer { input.resignFirstResponder(); window.isHidden = true }
        input.selectedRange = NSRange(location: 1, length: 0)
        var captured = "", endings: [Bool] = []
        input.onMarkedChanged = { captured = $0.text }
        input.onMarkedEnd = { view, allow in captured = view.text; endings.append(allow) }
        input.setMarkedText("😀ש", selectedRange: NSRange(location: 3, length: 0))
        input.captureCompositionForRecovery(); input.captureCompositionForRecovery()
        XCTAssertEqual(captured, "a😀ש")
        XCTAssertEqual(input.text, captured)
        XCTAssertEqual(endings, [false])
        XCTAssertFalse(input.isComposingMarkedText)
    }

    func testRejectedBeginOrProposalDoesNotReplaceVisibleSource() {
        let (window, input) = mounted("before")
        defer { input.resignFirstResponder(); window.isHidden = true }
        input.selectedRange = NSRange(location: 6, length: 0)
        input.onMarkedBegin = { _ in false }
        input.setMarkedText("lost", selectedRange: NSRange(location: 4, length: 0))
        XCTAssertEqual(input.text, "before"); XCTAssertFalse(input.isComposingMarkedText)
        input.onMarkedBegin = { _ in true }
        input.onMarkedProposal = { _, _, _ in false }
        var ending: Bool?
        input.onMarkedEnd = { _, value in ending = value }
        input.setMarkedText("lost", selectedRange: NSRange(location: 4, length: 0))
        XCTAssertEqual(input.text, "before"); XCTAssertNil(input.markedTextRange)
        XCTAssertFalse(input.isComposingMarkedText); XCTAssertEqual(ending, false)
    }

    func testUnmarkAndResignEndOnceAndNormalTextInputStillWorks() {
        let (window, input) = mounted("")
        defer { window.isHidden = true }
        var ended = 0
        input.onMarkedEnd = { _, _ in ended += 1 }
        input.setMarkedText("你", selectedRange: NSRange(location: 1, length: 0))
        XCTAssertTrue(input.resignFirstResponder())
        XCTAssertEqual(ended, 1)
        XCTAssertEqual(input.text, "你")
        XCTAssertNil(input.markedTextRange)
        XCTAssertTrue(input.becomeFirstResponder())
        input.insertText("好")
        XCTAssertEqual(input.text, "你好")
        XCTAssertEqual(ended, 1)
        input.resignFirstResponder()
    }
}
#endif
