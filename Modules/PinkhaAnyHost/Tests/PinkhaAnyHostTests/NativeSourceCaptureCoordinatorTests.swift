import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

private actor CaptureGate {
    private var opened = false
    private var waiting: [CheckedContinuation<Void, Never>] = []
    func wait() async {
        if opened { return }
        await withCheckedContinuation { waiting.append($0) }
    }
    func open() {
        opened = true
        let previous = waiting; waiting.removeAll()
        for continuation in previous { continuation.resume() }
    }
}

private final class CaptureBridgeCalls: @unchecked Sendable {
    enum Call: Equatable {
        case capture(String, String, String, String, String)
        case validate(String, String, String)
        case cancel(String, String)
        case release(String, String)
    }
    private let lock = NSLock()
    private var calls: [Call] = []
    func record(_ call: Call) { lock.lock(); defer { lock.unlock() }; calls.append(call) }
    func values() -> [Call] { lock.lock(); defer { lock.unlock() }; return calls }
}

final class NativeSourceCaptureCoordinatorTests: XCTestCase {
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
            .appendingPathComponent("capture-coordinator-control-" + UUID().uuidString, isDirectory: true)
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

    private func bridge(_ fixture: Fixture, calls: CaptureBridgeCalls,
                        started: CaptureGate? = nil, finish: CaptureGate? = nil,
                        denyValidation: Bool = false) -> AnyHeartNativeSourceBridge {
        .init(capture: { token, account, space, parent, request in
            calls.record(.capture(token, account, space, parent, request))
            await started?.open()
            await finish?.wait()
            return fixture.bytes
        }, validate: { token, request, manifest in
            calls.record(.validate(token, request, manifest))
            if denyValidation { throw AnyHeartNativeSourceCaptureCoordinatorError.inactiveCapture }
        }, cancel: { token, request in calls.record(.cancel(token, request)); return true },
        release: { token, request in calls.record(.release(token, request)); return true })
    }

    func testOriginalSourceReviewRetainsSemanticIssuesAndUsesExactNativeRevalidation() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = CaptureBridgeCalls()
        let coordinator = try AnyHeartNativeSourceCaptureCoordinator(bridge: bridge(f, calls: calls),
                                                                     privateDirectory: f.parent)
        let review = try await coordinator.capture(session: f.session, requestID: f.requestID)
        XCTAssertEqual(review.bundle.objects.count, 144)
        // The original source never contained a Pinkha schema manifest.
        XCTAssertNil(review.pinkhaSource)
        XCTAssertNil(review.pinkhaSourceIssue)
        XCTAssertEqual(review.definitionPlan.catalog.types.count, 19)
        XCTAssertEqual(review.definitionPlan.catalog.relations.count, 119)
        XCTAssertFalse(review.definitionPlan.issues.isEmpty)
        XCTAssertFalse(review.permitsDestinationWrites)
        XCTAssertFalse(review.descriptor.permitsDestinationWrites)
        XCTAssertThrowsError(try review.definitionPlan.admittedSchemaItems())
        XCTAssertFalse(review.unmappedObjects.isEmpty)
        let binding = try review.sourceBinding(semanticPlanSHA256: review.definitionPlan.catalog.contentSHA256)
        let census = try XCTUnwrap(review.bundle.nativeStoreContext?.headCensus)
        XCTAssertEqual(binding.sourceObjectIDs.count, review.bundle.trees.count + 2)
        XCTAssertEqual(Set(binding.sourceObjectIDs), Set(census.sourceHeadIDs))
        for tree in review.bundle.trees where tree.status == "space-settings-retained" {
            XCTAssertTrue(review.unmappedObjects.contains { $0.sourceObjectID == tree.objectID })
        }
        XCTAssertTrue(review.unmappedObjects.contains { $0.sourceObjectID == census.nativeACLID })
        try await coordinator.revalidate(source: binding)
        XCTAssertEqual(calls.values().filter {
            if case .validate = $0 { return true }; return false
        }, [.validate("unit-control-token", f.requestID, review.descriptor.manifestSHA256)])
        let ready = await coordinator.state; XCTAssertEqual(ready, .ready)
        await coordinator.invalidate(.engineChanged)
        let invalidated = await coordinator.state; XCTAssertEqual(invalidated, .invalidated(.engineChanged))
        XCTAssertTrue(FileManager.default.fileExists(atPath: f.child.appendingPathComponent("manifest.json").path))
        do { try await coordinator.revalidate(source: binding); XCTFail("Released native capture reused") }
        catch { XCTAssertEqual(error as? AnyHeartNativeSourceCaptureCoordinatorError, .inactiveCapture) }
    }

    func testChangedSourceIdentityManifestOrPartialCensusNeverCallsNativeValidation() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = CaptureBridgeCalls()
        let coordinator = try AnyHeartNativeSourceCaptureCoordinator(bridge: bridge(f, calls: calls),
                                                                     privateDirectory: f.parent)
        let review = try await coordinator.capture(session: f.session, requestID: f.requestID)
        let source = try review.sourceBinding(semanticPlanSHA256: review.definitionPlan.catalog.contentSHA256)
        for field in ["account", "space", "witness", "manifest", "members", "census", "snapshot-only"] {
            let changed = try AnyDestinationSourceBinding(
                accountID: field == "account" ? "another-account" : source.accountID,
                spaceID: field == "space" ? "another-space" : source.spaceID,
                witnessSHA256: field == "witness" ? String(repeating: "a", count: 64) : source.witnessSHA256,
                captureManifestSHA256: field == "manifest" ? String(repeating: "b", count: 64) : source.captureManifestSHA256,
                semanticPlanSHA256: source.semanticPlanSHA256,
                sourceObjectIDs: field == "census" ? Array(source.sourceObjectIDs.dropLast()) :
                    field == "snapshot-only" ? review.bundle.objects.map(\.sourceObjectID) : source.sourceObjectIDs,
                definitionManifestBytes: ["census", "snapshot-only"].contains(field) ? source.definitionManifestBytes : nil)
            do { try await coordinator.revalidate(source: changed); XCTFail("Changed source admitted: \(field)") }
            catch { XCTAssertEqual(error as? AnyHeartNativeSourceCaptureCoordinatorError, .sourceBinding) }
        }
        XCTAssertFalse(calls.values().contains { if case .validate = $0 { return true }; return false })
        try await coordinator.revalidate(source: source)
        await coordinator.release()
    }

    func testAccountSwitchDiscardsAndReleasesLateNativeReplyWithoutDeletingSource() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = CaptureBridgeCalls(), started = CaptureGate(), finish = CaptureGate()
        let coordinator = try AnyHeartNativeSourceCaptureCoordinator(
            bridge: bridge(f, calls: calls, started: started, finish: finish), privateDirectory: f.parent)
        let task = Task { try await coordinator.capture(session: f.session, requestID: f.requestID) }
        await started.wait()
        do { _ = try await coordinator.capture(session: f.session, requestID: "second"); XCTFail("Concurrent capture admitted") }
        catch { XCTAssertEqual(error as? AnyHeartNativeSourceCaptureCoordinatorError, .invalidLifecycle) }
        await coordinator.invalidate(.accountChanged)
        await finish.open()
        do { _ = try await task.value; XCTFail("Late native result became ready") }
        catch { XCTAssertEqual(error as? AnyHeartNativeSourceCaptureCoordinatorError, .inactiveCapture) }
        let state = await coordinator.state; XCTAssertEqual(state, .invalidated(.accountChanged))
        XCTAssertTrue(calls.values().contains(.cancel("unit-control-token", f.requestID)))
        XCTAssertTrue(calls.values().contains(.release("unit-control-token", f.requestID)))
        XCTAssertTrue(FileManager.default.fileExists(atPath: f.child.path))
    }

    func testCancellationSignalsNativeAndDoesNotPublishItsLateReply() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = CaptureBridgeCalls(), started = CaptureGate(), finish = CaptureGate()
        let coordinator = try AnyHeartNativeSourceCaptureCoordinator(
            bridge: bridge(f, calls: calls, started: started, finish: finish), privateDirectory: f.parent)
        let task = Task { try await coordinator.capture(session: f.session, requestID: f.requestID) }
        await started.wait(); task.cancel(); await finish.open()
        do { _ = try await task.value; XCTFail("Cancelled source became ready") }
        catch { XCTAssertTrue(error is CancellationError) }
        let state = await coordinator.state; XCTAssertEqual(state, .invalidated(.userCancelled))
        XCTAssertTrue(calls.values().contains(.cancel("unit-control-token", f.requestID)))
        XCTAssertTrue(calls.values().contains(.release("unit-control-token", f.requestID)))
        XCTAssertTrue(FileManager.default.fileExists(atPath: f.child.path))
    }

    func testUnknownOrRevokedNativeCheckpointRequiresNewCapture() async throws {
        let f = try fixture(); defer { f.remove() }
        let calls = CaptureBridgeCalls()
        let coordinator = try AnyHeartNativeSourceCaptureCoordinator(
            bridge: bridge(f, calls: calls, denyValidation: true), privateDirectory: f.parent)
        let review = try await coordinator.capture(session: f.session, requestID: f.requestID)
        let source = try review.sourceBinding(semanticPlanSHA256: review.definitionPlan.catalog.contentSHA256)
        do { try await coordinator.revalidate(source: source); XCTFail("Unknown native checkpoint accepted") }
        catch { XCTAssertEqual(error as? AnyHeartNativeSourceCaptureCoordinatorError, .inactiveCapture) }
        let state = await coordinator.state; XCTAssertEqual(state, .invalidated(.nativeValidationFailed))
        do { try await coordinator.revalidate(source: source); XCTFail("Failed native checkpoint reused") }
        catch { XCTAssertEqual(error as? AnyHeartNativeSourceCaptureCoordinatorError, .inactiveCapture) }
        XCTAssertEqual(calls.values().filter { if case .validate = $0 { return true }; return false }.count, 1)
        XCTAssertTrue(calls.values().contains(.release("unit-control-token", f.requestID)))
        XCTAssertTrue(FileManager.default.fileExists(atPath: f.child.path))
    }

    func testCancelledPrivateReadStopsAndSessionPresentationRedactsToken() async throws {
        let f = try fixture(); defer { f.remove() }
        XCTAssertFalse(String(describing: f.session).contains("unit-control-token"))
        XCTAssertFalse(String(reflecting: f.session).contains("unit-control-token"))
        XCTAssertThrowsError(try AnyHeartNativeSourceSession(sessionToken: "", accountID: "a", spaceID: "s"))
        XCTAssertThrowsError(try AnyHeartNativeSourceSession(sessionToken: "t", accountID: "", spaceID: "s"))
        let ready = CaptureGate(), finish = CaptureGate()
        let read = Task.detached {
            await ready.open(); await finish.wait()
            let descriptor = try AnyHeartNativeCaptureDescriptor(data: f.bytes, expectedAccountID: f.session.accountID,
                expectedSpaceID: f.session.spaceID, expectedRequestID: f.requestID)
            return try descriptor.loadBundle(under: f.parent)
        }
        await ready.wait(); read.cancel(); await finish.open()
        do { _ = try await read.value; XCTFail("Cancelled private bundle read continued") }
        catch { XCTAssertTrue(error is CancellationError) }
        XCTAssertTrue(FileManager.default.fileExists(atPath: f.child.path))
    }
}
