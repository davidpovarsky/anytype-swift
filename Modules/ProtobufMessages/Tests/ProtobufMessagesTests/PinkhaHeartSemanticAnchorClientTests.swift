#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation
import SwiftProtobuf
import XCTest
@testable import ProtobufMessages

@MainActor
private final class HeartCaptureProbe {
    let lifetime = PinkhaNativeReadLifetime()
    let plan: PinkhaHeartSemanticAnchorPlan
    let lease: PinkhaNativeReadLease
    var before: Anytype_Rpc.Object.Show.Response
    var after: Anytype_Rpc.Object.Show.Response
    var reply: Data
    var version = PinkhaHeartSemanticAnchorProfile.runtimeVersion
    var publicationAvailable = true
    var useInvocationHandler = false
    var retireInCapture = false
    var retireInReadback = false
    var holdCapture = false
    private(set) var captureStarted = false
    private var captureWaiters: [CheckedContinuation<Void, Never>] = []
    private var captureGate: CheckedContinuation<Void, Never>?
    private(set) var calls: [String] = []
    private(set) var published: [Anytype_ResponseEvent] = []
    private(set) var requests: [Data] = []
    private(set) var readCancellationStates: [Bool] = []
    private var readCount = 0

    init() throws {
        let fixturePlan = try HeartCaptureFixture.plan()
        plan = fixturePlan
        before = try HeartCaptureFixture.before()
        after = try HeartCaptureFixture.after()
        reply = try HeartCaptureFixture.data("capture-applied-response.json")
        let account = lifetime.beforeInvocation(name: "AccountSelect", request: Anytype_Rpc.Account.Select.Request())
        lifetime.completedInvocation(account, response: Anytype_Rpc.Account.Select.Response.with {
            $0.account = .with { $0.id = "fixture-owned-account"; $0.status.statusType = .active }
        })
        let space = lifetime.beforeInvocation(name: "WorkspaceOpen",
            request: Anytype_Rpc.Workspace.Open.Request.with { $0.spaceID = fixturePlan.request.spaceID })
        lifetime.completedInvocation(space, response: Anytype_Rpc.Workspace.Open.Response.with {
            $0.info = .with { $0.workspaceObjectID = "fixture-native-workspace" }
        })
        lease = try lifetime.lease(forOpenedSpaceID: plan.request.spaceID)
    }

    func retire() {
        _ = lifetime.beforeInvocation(name: "AccountStop", request: Anytype_Rpc.Account.Stop.Request())
    }

    func waitForCapture() async {
        if captureStarted { return }
        await withCheckedContinuation { captureWaiters.append($0) }
    }

    func releaseCapture() {
        let gate = captureGate
        captureGate = nil
        gate?.resume()
    }

    func client() -> PinkhaHeartSemanticAnchorClient {
        .init(io: .init(
            runtimeVersion: { self.calls.append("version"); return self.version },
            read: { spaceID, objectID in
                XCTAssertTrue(spaceID.utf8.elementsEqual(self.plan.request.spaceID.utf8))
                XCTAssertTrue(objectID.utf8.elementsEqual(self.plan.request.objectID.utf8))
                self.readCount += 1
                self.readCancellationStates.append(Task.isCancelled)
                if self.readCount == 1 {
                    self.calls.append("read-before")
                    return self.before
                }
                self.calls.append("read-after")
                if self.retireInReadback { self.retire() }
                return self.after
            },
            capture: { request in
                self.calls.append("capture"); self.requests.append(request)
                self.captureStarted = true
                let waiters = self.captureWaiters
                self.captureWaiters.removeAll()
                for waiter in waiters { waiter.resume() }
                if self.holdCapture { await withCheckedContinuation { self.captureGate = $0 } }
                if self.retireInCapture { self.retire() }
                return self.reply
            },
            canPublish: { self.publicationAvailable },
            publish: { event in
                self.calls.append("publish"); self.published.append(event)
                if self.useInvocationHandler {
                    return await PinkhaHeartSemanticAnchorNativePublication.send(event)
                }
                return self.publicationAvailable
            }
        ))
    }
}

@MainActor
final class PinkhaHeartSemanticAnchorClientTests: XCTestCase {
    func testVerifiedFixturePublishesReturnedEventBeforeReadbackOnce() async throws {
        let probe = try HeartCaptureProbe()
        let handler = HeartCaptureInvocationHandler()
        let previous = InvocationSettings.handler
        InvocationSettings.handler = handler
        defer { InvocationSettings.handler = previous }
        probe.useInvocationHandler = true
        let client = probe.client()
        let pending = try client.prepare(probe.plan, lease: probe.lease)
        let result = try await client.apply(pending)
        XCTAssertEqual(result.generation, probe.lease.generation)
        XCTAssertEqual(result.receipt.marker, probe.plan.request.marker)
        XCTAssertEqual(probe.calls, ["version", "read-before", "capture", "publish", "read-after"])
        XCTAssertEqual(probe.requests.count, 1)
        XCTAssertEqual(probe.published.count, 1)
        let event = try Anytype_ResponseEvent(serializedBytes: HeartCaptureFixture.data("capture-response-event.pb"))
        XCTAssertEqual(try probe.published[0].serializedData(), try event.serializedData())
        let received = await handler.events.all()
        XCTAssertEqual(received.count, 1)
        XCTAssertEqual(try received[0].serializedData(), try event.serializedData())
    }

    func testRetiredOwnerBeforeDispatchHasNoNativeCall() async throws {
        let probe = try HeartCaptureProbe()
        let client = probe.client()
        let pending = try client.prepare(probe.plan, lease: probe.lease)
        probe.retire()
        do { _ = try await client.apply(pending); XCTFail("Retired owner was accepted") }
        catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .retiredOwner) }
        XCTAssertTrue(probe.calls.isEmpty)
        XCTAssertTrue(probe.requests.isEmpty)
    }

    func testOwnerRetiredInsideNativeCallPreventsPublicationAndRetry() async throws {
        let probe = try HeartCaptureProbe()
        probe.retireInCapture = true
        let client = probe.client()
        let pending = try client.prepare(probe.plan, lease: probe.lease)
        do { _ = try await client.apply(pending); XCTFail("Retired result was accepted") }
        catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .uncertain) }
        XCTAssertEqual(probe.requests.count, 1)
        XCTAssertTrue(probe.published.isEmpty)
        do { _ = try await client.apply(pending); XCTFail("Consumed intent was retried") }
        catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .invalidRequest) }
        XCTAssertEqual(probe.requests.count, 1)
    }

    func testUnsupportedRuntimeAndMissingPublicationPreventMutation() async throws {
        for unavailable in [false, true] {
            let probe = try HeartCaptureProbe()
            if unavailable { probe.publicationAvailable = false }
            else { probe.version = "production139-without-page154" }
            let client = probe.client()
            let pending = try client.prepare(probe.plan, lease: probe.lease)
            do { _ = try await client.apply(pending); XCTFail("Unsupported boundary was accepted") }
            catch {
                XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError,
                    unavailable ? .unavailablePublication : .unsupportedRuntime)
            }
            XCTAssertTrue(probe.requests.isEmpty)
            XCTAssertTrue(probe.published.isEmpty)
        }
    }

    func testChangedCurrentNativeBlockPreventsMutation() async throws {
        let probe = try HeartCaptureProbe()
        probe.before = try HeartCaptureFixture.alterTarget(probe.before) { $0.backgroundColor = "changed" }
        let client = probe.client()
        let pending = try client.prepare(probe.plan, lease: probe.lease)
        do { _ = try await client.apply(pending); XCTFail("Stale complete block was accepted") }
        catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .changedDocument) }
        XCTAssertEqual(probe.calls, ["version", "read-before"])
        XCTAssertTrue(probe.requests.isEmpty)
    }

    func testCancellationAfterDispatchCompletesPublicationAndReadback() async throws {
        let probe = try HeartCaptureProbe()
        probe.holdCapture = true
        let client = probe.client()
        let pending = try client.prepare(probe.plan, lease: probe.lease)
        let task = Task { @MainActor in try await client.apply(pending) }
        await probe.waitForCapture()
        task.cancel()
        probe.releaseCapture()
        let result = try await task.value
        XCTAssertTrue(task.isCancelled)
        XCTAssertEqual(result.receipt.marker, probe.plan.request.marker)
        XCTAssertEqual(probe.calls, ["version", "read-before", "capture", "publish", "read-after"])
        XCTAssertEqual(probe.readCancellationStates, [false, false])
        XCTAssertEqual(probe.requests.count, 1)
        XCTAssertEqual(probe.published.count, 1)
    }

    func testDivergentReadbackOrRetiredOwnerNeverReturnsVerifiedReceipt() async throws {
        for retired in [false, true] {
            let probe = try HeartCaptureProbe()
            if retired { probe.retireInReadback = true }
            else { probe.after = try HeartCaptureFixture.alterTarget(probe.after) { $0.backgroundColor = "changed" } }
            let client = probe.client()
            let pending = try client.prepare(probe.plan, lease: probe.lease)
            do { _ = try await client.apply(pending); XCTFail("Unverified readback was accepted") }
            catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .uncertain) }
            XCTAssertEqual(probe.requests.count, 1)
            XCTAssertEqual(probe.published.count, 1)
            XCTAssertEqual(probe.calls.last, "read-after")
        }
    }

    func testSuccessfulPendingIntentCannotBeSubmittedAgain() async throws {
        let probe = try HeartCaptureProbe()
        let client = probe.client()
        let pending = try client.prepare(probe.plan, lease: probe.lease)
        _ = try await client.apply(pending)
        let before = probe.calls
        do { _ = try await client.apply(pending); XCTFail("Successful intent was retried") }
        catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .invalidRequest) }
        XCTAssertEqual(probe.calls, before)
        XCTAssertEqual(probe.requests.count, 1)
    }

    func testRefusedAndMalformedRepliesNeverPublishOrRetry() async throws {
        for malformed in [false, true] {
            let probe = try HeartCaptureProbe()
            probe.reply = Data((malformed ? #"{"protocolVersion":1,"outcome":"applied"}"#
                : #"{"protocolVersion":1,"outcome":"changed"}"#).utf8)
            let client = probe.client()
            let pending = try client.prepare(probe.plan, lease: probe.lease)
            do { _ = try await client.apply(pending); XCTFail("Invalid reply was accepted") }
            catch {
                XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError,
                    malformed ? .uncertain : .nativeRefusal(.changed))
            }
            XCTAssertEqual(probe.requests.count, 1)
            XCTAssertTrue(probe.published.isEmpty)
            do { _ = try await client.apply(pending); XCTFail("Refused intent was retried") }
            catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .invalidRequest) }
            XCTAssertEqual(probe.requests.count, 1)
        }
    }

    func testCancellationBeforeDispatchLeavesIntentUnconsumed() async throws {
        let probe = try HeartCaptureProbe()
        let client = probe.client()
        let pending = try client.prepare(probe.plan, lease: probe.lease)
        let task = Task { @MainActor in try await client.apply(pending) }
        task.cancel()
        do { _ = try await task.value; XCTFail("Cancelled pre-dispatch task continued") }
        catch { XCTAssertTrue(error is CancellationError) }
        XCTAssertTrue(probe.calls.isEmpty)
        _ = try await client.apply(pending)
        XCTAssertEqual(probe.requests.count, 1)
    }

    func testForeignSpaceCannotAcquirePendingIntentFromOwnedLease() async throws {
        let probe = try HeartCaptureProbe()
        let foreign = try PinkhaHeartSemanticAnchorPlan(spaceID: probe.plan.request.spaceID + "-foreign",
            objectID: probe.plan.request.objectID, anchorID: probe.plan.request.anchorID,
            range: NSRange(location: Int(probe.plan.request.from), length: Int(probe.plan.request.to - probe.plan.request.from)),
            nativeBlock: probe.plan.originalBlock)
        XCTAssertThrowsError(try probe.client().prepare(foreign, lease: probe.lease)) {
            XCTAssertEqual($0 as? PinkhaHeartSemanticAnchorError, .retiredOwner)
        }
        XCTAssertTrue(probe.calls.isEmpty)
    }
}
private actor HeartCapturePublishedEvents {
    private var values: [Anytype_ResponseEvent] = []
    func append(_ event: Anytype_ResponseEvent) { values.append(event) }
    func all() -> [Anytype_ResponseEvent] { values }
}

private final class HeartCaptureInvocationHandler: InvocationMesagesHandlerProtocol {
    let events = HeartCapturePublishedEvents()
    var isLogEnabled: Bool { false }
    func logHandler(message: InvocationMessage) { XCTFail("Capture publication must not log its wire body") }
    func eventHandler(event: Anytype_ResponseEvent) async { await events.append(event) }
    func assertationHandler(message: String, domain: String, info: [String: String],
                           file: StaticString, function: String, line: UInt) {
        XCTFail("Unexpected invocation assertion")
    }
}
#endif
