#if canImport(UIKit)
import UIKit
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyUI

@MainActor
final class AnyNativeFocusHandoffTests: XCTestCase {
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

    private func intent(_ location: Int = 0, ownerID: UUID = UUID(),
                        version: AnyJSON = .string("v1")) -> AnyNativeFocusIntent {
        .init(blockID: "block", ownerID: ownerID, nativeVersion: version,
              source: "abc אבג", selection: .init(location: location, length: 0))
    }

    private func turn() async {
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            DispatchQueue.main.async { continuation.resume() }
        }
    }

    func testSnapshotCompletionUnwindsBeforeResponderAcquisition() async {
        let fixture = window(), view = input(), delegate = HandoffAttemptObserver()
        let table = UITableView(frame: fixture.rootViewController!.view.bounds, style: .plain)
        table.rowHeight = 100
        table.register(UITableViewCell.self, forCellReuseIdentifier: "block")
        fixture.rootViewController!.view.addSubview(table)
        var insideSnapshotApply = false, insideCompletion = false
        delegate.onAttempt = {
            XCTAssertFalse(insideSnapshotApply, "Responder acquisition must leave the snapshot apply stack")
            XCTAssertFalse(insideCompletion, "Responder acquisition must leave the snapshot completion")
        }
        view.delegate = delegate
        let dataSource = UITableViewDiffableDataSource<Int, String>(tableView: table) { table, path, _ in
            let cell = table.dequeueReusableCell(withIdentifier: "block", for: path)
            cell.contentView.addSubview(view)
            return cell
        }
        let coordinator = AnyNativeFocusCoordinator(validate: { _ in true }, resolve: { _ in
            table.layoutIfNeeded()
            return view
        })
        defer { coordinator.cancel(); fixture.endEditing(true); fixture.isHidden = true }
        coordinator.request(intent(7), attemptImmediately: false)
        var snapshot = NSDiffableDataSourceSnapshot<Int, String>()
        snapshot.appendSections([0]); snapshot.appendItems(["block"])
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            insideSnapshotApply = true
            dataSource.apply(snapshot, animatingDifferences: false) {
                insideCompletion = true
                coordinator.readinessChangedAfterUIUpdate(.layout)
                XCTAssertEqual(delegate.attempts, 0)
                XCTAssertFalse(view.isFirstResponder)
                insideCompletion = false
                continuation.resume()
            }
            insideSnapshotApply = false
        }
        await turn()
        XCTAssertEqual(dataSource.snapshot().itemIdentifiers, ["block"])
        XCTAssertEqual(delegate.attempts, 1)
        XCTAssertTrue(view.isFirstResponder)
        XCTAssertEqual(view.selectedRange, NSRange(location: 7, length: 0))
        XCTAssertFalse(coordinator.hasPending)
    }

    func testReadinessBurstAndReentrantLayoutDeliverOnlyOneAttempt() async {
        let fixture = window(), view = input(), delegate = HandoffAttemptObserver()
        fixture.rootViewController!.view.addSubview(view); view.delegate = delegate
        var resolved = 0
        var duringResolve: (() -> Void)?
        let coordinator = AnyNativeFocusCoordinator(validate: { _ in true }, resolve: { _ in
            resolved += 1
            duringResolve?()
            return view
        })
        duringResolve = { [weak coordinator] in coordinator?.readinessChangedAfterUIUpdate(.layout) }
        defer { coordinator.cancel(); duringResolve = nil; fixture.endEditing(true); fixture.isHidden = true }
        coordinator.request(intent(7), attemptImmediately: false)
        for event in [AnyNativeFocusCoordinator.Readiness.layout, .attachment, .layout, .keyWindow, .layout] {
            coordinator.readinessChangedAfterUIUpdate(event)
        }
        XCTAssertEqual(resolved, 0); XCTAssertEqual(delegate.attempts, 0)
        await turn()
        XCTAssertEqual(resolved, 1); XCTAssertEqual(delegate.attempts, 1)
        XCTAssertTrue(view.isFirstResponder); XCTAssertFalse(coordinator.hasPending)
        coordinator.readinessChangedAfterUIUpdate(.layout)
        await turn()
        XCTAssertEqual(resolved, 1); XCTAssertEqual(delegate.attempts, 1)
    }

    func testQueuedDeliveryRevalidatesOwnerVersionAndHonorsCancellationAndReplacement() async {
        let fixture = window(), view = input(), delegate = HandoffAttemptObserver()
        fixture.rootViewController!.view.addSubview(view); view.delegate = delegate
        var owner = UUID(), version = AnyJSON.string("v1"), resolved = 0
        let coordinator = AnyNativeFocusCoordinator(validate: {
            $0.ownerID == owner && $0.nativeVersion == version
        }, resolve: { _ in resolved += 1; return view })
        defer { coordinator.cancel(); fixture.endEditing(true); fixture.isHidden = true }

        coordinator.request(intent(ownerID: owner, version: version), attemptImmediately: false)
        coordinator.readinessChangedAfterUIUpdate(.layout)
        owner = UUID()
        await turn()
        XCTAssertEqual(resolved, 0); XCTAssertFalse(coordinator.hasPending)

        coordinator.request(intent(ownerID: owner, version: version), attemptImmediately: false)
        coordinator.readinessChangedAfterUIUpdate(.attachment)
        version = .string("v2")
        await turn()
        XCTAssertEqual(resolved, 0); XCTAssertFalse(coordinator.hasPending)

        coordinator.request(intent(ownerID: owner, version: version), attemptImmediately: false)
        coordinator.readinessChangedAfterUIUpdate(.layout)
        coordinator.userInteraction()
        await turn()
        XCTAssertEqual(resolved, 0); XCTAssertEqual(delegate.attempts, 0)

        coordinator.request(intent(1, ownerID: owner, version: version), attemptImmediately: false)
        coordinator.readinessChangedAfterUIUpdate(.layout)
        coordinator.request(intent(7, ownerID: owner, version: version), attemptImmediately: false)
        coordinator.readinessChangedAfterUIUpdate(.attachment)
        await turn()
        XCTAssertEqual(resolved, 1); XCTAssertEqual(delegate.attempts, 1)
        XCTAssertEqual(view.selectedRange, NSRange(location: 7, length: 0))
        XCTAssertFalse(coordinator.hasPending)
    }

    func testDeferredNativeRefusalWaitsForActualReadinessWithoutLayoutRetries() async {
        let fixture = window(), view = input(), delegate = HandoffAttemptObserver()
        fixture.rootViewController!.view.addSubview(view); view.delegate = delegate
        delegate.allow = false
        let coordinator = AnyNativeFocusCoordinator(validate: { _ in true }, resolve: { _ in view })
        defer { coordinator.cancel(); fixture.endEditing(true); fixture.isHidden = true }
        coordinator.request(intent(), attemptImmediately: false)
        coordinator.readinessChangedAfterUIUpdate(.layout)
        await turn()
        XCTAssertEqual(delegate.attempts, 1); XCTAssertFalse(view.isFirstResponder)
        XCTAssertTrue(coordinator.hasPending)
        for _ in 0..<5 { coordinator.readinessChangedAfterUIUpdate(.layout) }
        await turn()
        XCTAssertEqual(delegate.attempts, 1)
        delegate.allow = true
        let other = window()
        defer { other.isHidden = true }
        fixture.makeKeyAndVisible()
        XCTAssertEqual(delegate.attempts, 1, "A key-window notification must not acquire inline")
        await turn()
        XCTAssertEqual(delegate.attempts, 2)
        XCTAssertTrue(view.isFirstResponder); XCTAssertFalse(coordinator.hasPending)
    }
}

@MainActor
private final class HandoffAttemptObserver: NSObject, UITextViewDelegate {
    var allow = true
    var onAttempt: (() -> Void)?
    private(set) var attempts = 0
    func textViewShouldBeginEditing(_ textView: UITextView) -> Bool {
        attempts += 1; onAttempt?(); return allow
    }
}
#endif
