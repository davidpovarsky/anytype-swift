import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

private actor OwnedSessionGate {
    private var open = false
    private var waiting: [CheckedContinuation<Void, Never>] = []
    func wait() async {
        if open { return }
        await withCheckedContinuation { waiting.append($0) }
    }
    func release() {
        open = true
        let pending = waiting; waiting = []
        for item in pending { item.resume() }
    }
}

private final class OwnedSessionCalls: @unchecked Sendable {
    private let lock = NSLock()
    private var log: [String] = []
    private var closeFailures: Int
    init(closeFailures: Int = 0) { self.closeFailures = closeFailures }
    func append(_ item: String) { lock.lock(); defer { lock.unlock() }; log.append(item) }
    func values() -> [String] { lock.lock(); defer { lock.unlock() }; return log }
    func close(_ token: String) throws {
        lock.lock(); defer { lock.unlock() }
        log.append("close:" + token)
        if closeFailures > 0 {
            closeFailures -= 1
            throw AnyHeartNativeSourceAccountError.sessionCloseFailed
        }
    }
}

final class NativeSourceAccountControllerTests: XCTestCase {
    private struct Fixture {
        let parent: URL
        let child: URL
        let bytes: Data
        let session: AnyHeartNativeSourceSession
        let requestID: String
        func remove() { try? FileManager.default.removeItem(at: parent) }
    }

    /// This is an injected bridge control using byte-exact original captured
    /// source. It is not reported as a live native capture or native ACL test.
    private func fixture() throws -> Fixture {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_NATIVE_SOURCE_FIXTURE"] else {
            throw XCTSkip("Explicit immutable original capture is required")
        }
        let source = URL(fileURLWithPath: path, isDirectory: true)
        let contextBytes = try Data(contentsOf: source.appendingPathComponent("fixture-context.json"))
        XCTAssertEqual(AnyContentDigest.sha256(contextBytes),
                       "5357d52f5e76b604a40d7a5f2b1bc002e19bc864c419a45f90128bfa965d5850")
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        let account = try XCTUnwrap(context["sourceAccountID"]?.string)
        let space = try XCTUnwrap(context["sourceSpaceID"]?.string)
        let original = source.appendingPathComponent(try XCTUnwrap(context["bundleRelativePath"]?.string))
        let parent = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("account-controller-control-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        do {
            let child = parent.appendingPathComponent("native-source-retained", isDirectory: true)
            try FileManager.default.copyItem(at: original, to: child)
            try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: child.path)
            let enumerator = try XCTUnwrap(FileManager.default.enumerator(at: child,
                includingPropertiesForKeys: [.isDirectoryKey, .isSymbolicLinkKey]))
            for case let url as URL in enumerator {
                let values = try url.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
                XCTAssertNotEqual(values.isSymbolicLink, true)
                try FileManager.default.setAttributes([.posixPermissions: values.isDirectory == true ? 0o700 : 0o400],
                                                       ofItemAtPath: url.path)
            }
            let manifest = try Data(contentsOf: child.appendingPathComponent("manifest.json"))
            XCTAssertEqual(AnyContentDigest.sha256(manifest),
                           "2a1a02987204321aaa1c8cf9f0c7f413f4b50dbce87280d82499c4f9bc7be238")
            let value = try JSONDecoder().decode(AnyJSON.self, from: manifest)
            let requestID = "coordinator-control-" + UUID().uuidString
            let descriptor = AnyJSON.object([
                "contract": .string(AnyHeartNativeCaptureDescriptor.contract), "requestID": .string(requestID),
                "sourceAccountID": .string(account), "sourceSpaceID": .string(space),
                "privateBundleDirectory": .string(child.path),
                "manifestSHA256": .string(AnyContentDigest.sha256(manifest)),
                "sourceRowsSHA256": try XCTUnwrap(value["SourceRows"]?["SHA256"]),
                "nativeTrees": try XCTUnwrap(value["Receipt"]?["NativeTrees"]),
                "capturedObjects": try XCTUnwrap(value["Receipt"]?["CapturedObjects"]),
                "capturedFiles": try XCTUnwrap(value["Receipt"]?["CapturedFiles"]),
                "accountSessionAuthorizedAtCapture": .bool(true), "capturedSnapshotsBoundToCheckpoint": .bool(true),
                "currentFilePayloadCompleteness": try XCTUnwrap(value["Receipt"]?["CurrentFilePayloadCompleteness"]),
                "originalNativeHistoryRowsRetained": .bool(true), "permitsDestinationWrites": .bool(false)])
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            return .init(parent: parent, child: child, bytes: try encoder.encode(descriptor),
                session: try .init(sessionToken: "unit-control-token", accountID: account, spaceID: space),
                requestID: requestID)
        } catch {
            try? FileManager.default.removeItem(at: parent)
            throw error
        }
    }


    private func bridge(_ f: Fixture, calls: OwnedSessionCalls,
                        captureStarted: OwnedSessionGate? = nil, captureFinish: OwnedSessionGate? = nil,
                        validationStarted: OwnedSessionGate? = nil, validationFinish: OwnedSessionGate? = nil,
                        badCapture: Bool = false) -> AnyHeartNativeSourceBridge {
        .init(capture: { token, account, space, parent, request in
            calls.append("capture:" + token)
            XCTAssertEqual(account, f.session.accountID)
            XCTAssertEqual(space, f.session.spaceID)
            XCTAssertEqual(parent, f.parent.path)
            await captureStarted?.release()
            await captureFinish?.wait()
            calls.append("capture-finished")
            if badCapture { return Data("invalid native reply".utf8) }
            var json = try JSONDecoder().decode(AnyJSON.self, from: f.bytes)
            guard case var .object(fields) = json else { throw AnyHeartNativeSourceAccountError.invalidAuthority }
            fields["requestID"] = .string(request)
            json = .object(fields)
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            return try encoder.encode(json)
        }, validate: { token, _, _ in
            calls.append("validate:" + token)
            await validationStarted?.release()
            await validationFinish?.wait()
            calls.append("validate-finished")
        }, cancel: { token, _ in calls.append("cancel:" + token); return true },
        release: { token, _ in calls.append("release:" + token); return true })
    }

    private func authority(_ f: Fixture, calls: OwnedSessionCalls,
                           started: OwnedSessionGate? = nil, finish: OwnedSessionGate? = nil,
                           grant: AnyHeartNativeSourceSessionGrant? = nil) -> AnyHeartNativeSourceSessionAuthority {
        .init(create: { expectedAccount in
            calls.append("mint")
            XCTAssertEqual(expectedAccount, f.session.accountID)
            await started?.release(); await finish?.wait()
            // Models the original Invocation's post-response cancellation
            // check. The controller must not cancel this minting task.
            try Task.checkCancellation()
            calls.append("mint-finished")
            return grant ?? .init(sessionToken: "owned-test-token", accountID: f.session.accountID,
                                  isFull: true, isAppAssociated: false)
        }, close: { token in try calls.close(token) })
    }

    private func waitUntilInvalidating(_ controller: AnyHeartNativeSourceAccountController) async throws {
        for _ in 0..<1000 {
            if case .invalidating = await controller.state { return }
            try await Task.sleep(for: .milliseconds(1))
        }
        XCTFail("Invalidation did not start")
        throw AnyHeartNativeSourceAccountError.invalidLifecycle
    }

    func testFullOwnedSessionReviewsOriginalCensusAndRevalidatesBeforeOneClose() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = OwnedSessionCalls()
        let controller = try AnyHeartNativeSourceAccountController(authority: authority(f, calls: calls),
            bridge: bridge(f, calls: calls), privateDirectory: f.parent)
        let review = try await controller.capture(accountID: f.session.accountID, spaceID: f.session.spaceID)
        XCTAssertEqual(review.bundle.objects.count, 144)
        XCTAssertFalse(review.permitsDestinationWrites)
        XCTAssertFalse(review.unmappedObjects.isEmpty)
        XCTAssertFalse(review.definitionPlan.issues.isEmpty)
        let binding = try review.sourceBinding(semanticPlanSHA256: review.definitionPlan.catalog.contentSHA256)
        try await controller.revalidate(source: binding)
        XCTAssertFalse(calls.values().contains("close:owned-test-token"))
        try await controller.release()
        try await controller.release()
        XCTAssertEqual(calls.values().filter { $0.hasPrefix("close:") }, ["close:owned-test-token"])
        let log = calls.values()
        XCTAssertLessThan(try XCTUnwrap(log.lastIndex(of: "release:owned-test-token")),
                          try XCTUnwrap(log.firstIndex(of: "close:owned-test-token")))
        let state = await controller.state; XCTAssertEqual(state, .idle)
        XCTAssertTrue(FileManager.default.fileExists(atPath: f.child.path))
    }

    func testAccountSwitchDrainsLateMintAndClosesWithoutDispatchingCapture() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = OwnedSessionCalls(), started = OwnedSessionGate(), finish = OwnedSessionGate()
        let controller = try AnyHeartNativeSourceAccountController(
            authority: authority(f, calls: calls, started: started, finish: finish),
            bridge: bridge(f, calls: calls), privateDirectory: f.parent)
        let capture = Task { try await controller.capture(accountID: f.session.accountID, spaceID: f.session.spaceID) }
        await started.wait()
        let invalidation = Task { try await controller.invalidate(reason: .accountChanged); calls.append("switch-finished") }
        try await waitUntilInvalidating(controller)
        XCTAssertFalse(calls.values().contains("switch-finished"))
        XCTAssertFalse(calls.values().contains("close:owned-test-token"))
        do {
            _ = try await controller.capture(accountID: f.session.accountID, spaceID: f.session.spaceID)
            XCTFail("New account capture overtook an old mint")
        } catch { XCTAssertEqual(error as? AnyHeartNativeSourceAccountError, .invalidLifecycle) }
        await finish.release()
        do { _ = try await capture.value; XCTFail("Invalidated mint published a review") }
        catch { XCTAssertTrue(error is CancellationError || error as? AnyHeartNativeSourceAccountError == .inactiveCapture) }
        try await invalidation.value
        XCTAssertEqual(calls.values(), ["mint", "mint-finished", "close:owned-test-token", "switch-finished"])
    }

    func testCallerCancellationCannotLoseLateMintOrLeaveOwnedSession() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = OwnedSessionCalls(), started = OwnedSessionGate(), finish = OwnedSessionGate()
        let controller = try AnyHeartNativeSourceAccountController(
            authority: authority(f, calls: calls, started: started, finish: finish),
            bridge: bridge(f, calls: calls), privateDirectory: f.parent)
        let capture = Task { try await controller.capture(accountID: f.session.accountID, spaceID: f.session.spaceID) }
        await started.wait(); capture.cancel()
        try await waitUntilInvalidating(controller)
        await finish.release()
        do { _ = try await capture.value; XCTFail("Cancelled mint published a review") }
        catch { XCTAssertTrue(error is CancellationError) }
        XCTAssertEqual(calls.values(), ["mint", "mint-finished", "close:owned-test-token"])
        let state = await controller.state; XCTAssertEqual(state, .idle)
    }

    func testCancellationDrainsLateCaptureBeforeClosingItsToken() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = OwnedSessionCalls(), started = OwnedSessionGate(), finish = OwnedSessionGate()
        let controller = try AnyHeartNativeSourceAccountController(authority: authority(f, calls: calls),
            bridge: bridge(f, calls: calls, captureStarted: started, captureFinish: finish), privateDirectory: f.parent)
        let capture = Task { try await controller.capture(accountID: f.session.accountID, spaceID: f.session.spaceID) }
        await started.wait(); capture.cancel()
        try await waitUntilInvalidating(controller)
        XCTAssertFalse(calls.values().contains("close:owned-test-token"))
        await finish.release()
        do { _ = try await capture.value; XCTFail("Cancelled native capture published") }
        catch { XCTAssertTrue(error is CancellationError) }
        let log = calls.values()
        XCTAssertEqual(log.filter { $0.hasPrefix("close:") }, ["close:owned-test-token"])
        XCTAssertLessThan(try XCTUnwrap(log.firstIndex(of: "capture-finished")),
                          try XCTUnwrap(log.firstIndex(of: "close:owned-test-token")))
        XCTAssertTrue(FileManager.default.fileExists(atPath: f.child.path))
    }

    func testRejectedAccountScopeAssociationAndEmptyTokenCannotCapture() async throws {
        let f = try fixture(); defer { f.remove() }
        let grants: [AnyHeartNativeSourceSessionGrant] = [
            .init(sessionToken: "wrong-account", accountID: f.session.accountID + "-other", isFull: true, isAppAssociated: false),
            .init(sessionToken: "limited", accountID: f.session.accountID, isFull: false, isAppAssociated: false),
            .init(sessionToken: "app-associated", accountID: f.session.accountID, isFull: true, isAppAssociated: true),
            .init(sessionToken: "", accountID: f.session.accountID, isFull: true, isAppAssociated: false)
        ]
        for (index, grant) in grants.enumerated() {
            XCTAssertEqual(String(describing: grant), "AnyHeartNativeSourceSessionGrant(redacted)")
            let calls = OwnedSessionCalls()
            let controller = try AnyHeartNativeSourceAccountController(authority: authority(f, calls: calls, grant: grant),
                bridge: bridge(f, calls: calls), privateDirectory: f.parent)
            do {
                _ = try await controller.capture(accountID: f.session.accountID, spaceID: f.session.spaceID)
                XCTFail("Invalid authority admitted")
            } catch {
                XCTAssertTrue(error as? AnyHeartNativeSourceAccountError == .invalidAuthority ||
                              error as? AnyHeartNativeSourceCaptureCoordinatorError == .invalidSession)
            }
            XCTAssertFalse(calls.values().contains { $0.hasPrefix("capture:") })
            XCTAssertEqual(calls.values().filter { $0.hasPrefix("close:") }.count, index == 3 ? 0 : 1)
            let state = await controller.state; XCTAssertEqual(state, .idle)
        }
    }

    func testEngineSwitchWaitsForNativeValidationThenReleasesAndCloses() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = OwnedSessionCalls(), started = OwnedSessionGate(), finish = OwnedSessionGate()
        let controller = try AnyHeartNativeSourceAccountController(authority: authority(f, calls: calls),
            bridge: bridge(f, calls: calls, validationStarted: started, validationFinish: finish), privateDirectory: f.parent)
        let review = try await controller.capture(accountID: f.session.accountID, spaceID: f.session.spaceID)
        let binding = try review.sourceBinding(semanticPlanSHA256: review.definitionPlan.catalog.contentSHA256)
        let validation = Task { try await controller.revalidate(source: binding) }
        await started.wait()
        let invalidation = Task { try await controller.invalidate(reason: .engineChanged); calls.append("switch-finished") }
        try await waitUntilInvalidating(controller)
        XCTAssertFalse(calls.values().contains("close:owned-test-token"))
        XCTAssertFalse(calls.values().contains("switch-finished"))
        await finish.release()
        do { try await validation.value; XCTFail("Invalidated validation became ready") }
        catch { XCTAssertTrue(error is CancellationError || error as? AnyHeartNativeSourceAccountError == .inactiveCapture) }
        try await invalidation.value
        let log = calls.values()
        XCTAssertLessThan(try XCTUnwrap(log.firstIndex(of: "validate-finished")),
                          try XCTUnwrap(log.firstIndex(of: "close:owned-test-token")))
        XCTAssertLessThan(try XCTUnwrap(log.firstIndex(of: "close:owned-test-token")),
                          try XCTUnwrap(log.firstIndex(of: "switch-finished")))
        XCTAssertEqual(log.filter { $0.hasPrefix("close:") }, ["close:owned-test-token"])
    }

    func testCloseFailureKeepsOwnedTokenBlocksNextCaptureAndAllowsExplicitRetry() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = OwnedSessionCalls(closeFailures: 1)
        let controller = try AnyHeartNativeSourceAccountController(authority: authority(f, calls: calls),
            bridge: bridge(f, calls: calls), privateDirectory: f.parent)
        _ = try await controller.capture(accountID: f.session.accountID, spaceID: f.session.spaceID)
        do { try await controller.invalidate(reason: .engineChanged); XCTFail("Failed close admitted engine transfer") }
        catch { XCTAssertEqual(error as? AnyHeartNativeSourceAccountError, .sessionCloseFailed) }
        let failed = await controller.state; XCTAssertEqual(failed, .sessionCloseFailed)
        do {
            _ = try await controller.capture(accountID: f.session.accountID, spaceID: f.session.spaceID)
            XCTFail("New capture abandoned an unclosed token")
        } catch { XCTAssertEqual(error as? AnyHeartNativeSourceAccountError, .invalidLifecycle) }
        try await controller.invalidate(reason: .engineChanged)
        XCTAssertEqual(calls.values().filter { $0.hasPrefix("close:") }, ["close:owned-test-token", "close:owned-test-token"])
        XCTAssertEqual(calls.values().filter { $0 == "mint" }.count, 1)
        let state = await controller.state; XCTAssertEqual(state, .idle)
    }

    func testInvalidNativeReplyClosesOwnedSessionAndPreservesOriginalSource() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = OwnedSessionCalls()
        let controller = try AnyHeartNativeSourceAccountController(authority: authority(f, calls: calls),
            bridge: bridge(f, calls: calls, badCapture: true), privateDirectory: f.parent)
        do {
            _ = try await controller.capture(accountID: f.session.accountID, spaceID: f.session.spaceID)
            XCTFail("Invalid descriptor admitted")
        } catch { XCTAssertFalse(error is CancellationError) }
        XCTAssertEqual(calls.values().filter { $0.hasPrefix("close:") }, ["close:owned-test-token"])
        XCTAssertTrue(FileManager.default.fileExists(atPath: f.child.path))
        let state = await controller.state; XCTAssertEqual(state, .idle)
    }
}
