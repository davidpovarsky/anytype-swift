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
    var failInReadback = false
    var retireInBeforeRead = false
    var retireInPublication = false
    private(set) var publicationFence: PinkhaHeartSemanticAnchorPublicationFence?
    private(set) var stateDeliveries = 0
    private(set) var mainDeliveries = 0

    func recordMainDelivery() { mainDeliveries += 1 }
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
                if self.requests.isEmpty {
                    self.calls.append("read-before")
                    if self.retireInBeforeRead { self.retire() }
                    return self.before
                }
                self.calls.append("read-after")
                if self.retireInReadback { self.retire() }
                if self.failInReadback { throw NSError(domain: "OwnedReadbackFailure", code: 1) }
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
                self.publicationFence = PinkhaHeartSemanticAnchorPublication.current
                if self.retireInPublication { self.retire() }
                _ = self.publicationFence?.withCurrentDocumentState(spaceID: self.lease.spaceID,
                    objectID: self.plan.request.objectID) { self.stateDeliveries += 1 }
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

    func testProjectionAndMarksPublishTheOriginalNativeEventWithNoAdditionalRead() async throws {
        let probe = try HeartCaptureProbe()
        let values = HeartCaptureFixture.projectionValues()
        probe.before = try HeartCaptureFixture.withProjection(probe.before, values: values)
        probe.after = try HeartCaptureFixture.withProjection(probe.after, values: values)
        probe.reply = try HeartCaptureFixture.projectionReply(values: values)
        let expected = try PinkhaHeartSemanticAnchorAppliedReply.decode(probe.reply, request: probe.plan.request)
        let client = probe.client()
        let verified = try await client.apply(client.prepare(probe.plan, lease: probe.lease))
        XCTAssertEqual(verified.receipt.marker, probe.plan.request.marker)
        XCTAssertEqual(probe.calls, ["version", "read-before", "capture", "read-after", "publish"])
        XCTAssertEqual(probe.requests.count, 1)
        XCTAssertEqual(probe.published.count, 1)
        XCTAssertEqual(probe.stateDeliveries, 1)
        let event = try XCTUnwrap(probe.published.first)
        XCTAssertEqual(event.messages.count, 2)
        XCTAssertEqual(try event.serializedData(), expected.responseEvent)
        XCTAssertTrue(try XCTUnwrap(probe.publicationFence).matches(event: event))
        XCTAssertNil(PinkhaHeartSemanticAnchorPublication.current)
    }


    func testNewlyMaterializedProjectionIsReadBeforeSingleOriginalPublication() async throws {
        let probe = try HeartCaptureProbe()
        let values = HeartCaptureFixture.projectionValues()
        let row = try XCTUnwrap(probe.before.objectView.details.firstIndex { $0.id == probe.plan.request.objectID })
        for key in values.keys { probe.before.objectView.details[row].details.fields.removeValue(forKey: key) }
        probe.after = try HeartCaptureFixture.withProjection(probe.after, values: values)
        probe.reply = try HeartCaptureFixture.projectionReply(values: values)
        let expected = try PinkhaHeartSemanticAnchorAppliedReply.decode(probe.reply, request: probe.plan.request)
        let client = probe.client()
        let capture = try await client.apply(client.prepare(probe.plan, lease: probe.lease))
        XCTAssertEqual(capture.receipt.marker, probe.plan.request.marker)
        XCTAssertEqual(probe.calls, ["version", "read-before", "capture", "read-after", "publish"])
        XCTAssertEqual(probe.requests.count, 1)
        XCTAssertEqual(probe.published.count, 1)
        XCTAssertEqual(probe.stateDeliveries, 1)
        XCTAssertEqual(try XCTUnwrap(probe.published.first).serializedData(), expected.responseEvent)
    }

    func testProjectionReadbackFailuresPreventPublicationAndRetry() async throws {
        for variant in ["missing-field", "changed-projection", "foreign-root", "foreign-space", "changed-block", "read-error"] {
            let probe = try HeartCaptureProbe()
            let values = HeartCaptureFixture.projectionValues()
            probe.after = try HeartCaptureFixture.withProjection(probe.after, values: values)
            probe.reply = try HeartCaptureFixture.projectionReply(values: values)
            let row = try XCTUnwrap(probe.after.objectView.details.firstIndex { $0.id == probe.plan.request.objectID })
            switch variant {
            case "missing-field": probe.after.objectView.details[row].details.fields.removeValue(forKey: "_pinkhaTorahReady")
            case "changed-projection": probe.after.objectView.details[row].details.fields["_pinkhaTorahCacheIntegrity"]?.stringValue = String(repeating: "c", count: 64)
            case "foreign-root": probe.after.objectView.rootID += "-foreign"
            case "foreign-space": probe.after.objectView.details[row].details.fields["spaceId"]?.stringValue += "-foreign"
            case "changed-block": probe.after = try HeartCaptureFixture.alterTarget(probe.after) { $0.backgroundColor = "changed" }
            default: probe.failInReadback = true
            }
            let client = probe.client()
            let pending = try client.prepare(probe.plan, lease: probe.lease)
            do { _ = try await client.apply(pending); XCTFail("Invalid post-Apply state accepted: " + variant) }
            catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .uncertain, variant) }
            XCTAssertEqual(probe.calls, ["version", "read-before", "capture", "read-after"], variant)
            XCTAssertEqual(probe.requests.count, 1)
            XCTAssertTrue(probe.published.isEmpty, variant)
            do { _ = try await client.apply(pending); XCTFail("Uncertain capture retried: " + variant) }
            catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .invalidRequest, variant) }
            XCTAssertEqual(probe.requests.count, 1)
        }
    }

    func testVerifiedFixturePublishesReturnedEventAfterReadbackOnce() async throws {
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
        XCTAssertEqual(probe.calls, ["version", "read-before", "capture", "read-after", "publish"])
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
        XCTAssertEqual(probe.calls, ["version", "read-before", "capture", "read-after", "publish"])
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
            XCTAssertEqual(probe.published.count, 0)
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

    func testFreshSemanticDocumentReadUsesOriginalNativeTreeWithoutCaptureOrPublication() async throws {
        let probe = try HeartCaptureProbe()
        probe.publicationAvailable = false // Read-only sources need no event publisher.
        let request = probe.plan.request
        let read = try await probe.client().readCurrentDocument(spaceID: request.spaceID,
            objectID: request.objectID, lease: probe.lease)
        XCTAssertEqual(read.spaceID, request.spaceID)
        XCTAssertEqual(read.objectID, request.objectID)
        XCTAssertEqual(read.blocks.first(where: { $0.id == request.blockID })?.text, request.expected)
        XCTAssertEqual(Set(read.blocks.map(\.id)).count, read.blocks.count)
        XCTAssertEqual(probe.calls, ["version", "read-before"])
        XCTAssertTrue(probe.requests.isEmpty)
        XCTAssertTrue(probe.published.isEmpty)
        for filename in ["capture-after-object-show.pb", "cold-reopen-object-show.pb"] {
            let response = try Anytype_Rpc.Object.Show.Response(serializedBytes: HeartCaptureFixture.data(filename))
            let current = try PinkhaHeartSemanticAnchorDocument(response: response,
                spaceID: request.spaceID, objectID: request.objectID)
            XCTAssertEqual(current.blocks.first(where: { $0.id == request.blockID })?.text,
                           try request.plannedSnapshot())
        }
    }

    func testSemanticDocumentReadRejectsRetiredForeignIncompleteAndAmbiguousNativeTrees() async throws {
        for variant in ["retired", "foreign-space", "wrong-root", "root-kind", "wrong-details", "duplicate",
                        "missing-child", "cycle", "unreachable", "runtime", "cancelled"] {
            let probe = try HeartCaptureProbe(), request = probe.plan.request
            switch variant {
            case "retired": probe.retireInBeforeRead = true
            case "wrong-root": probe.before.objectView.rootID += "-foreign"
            case "root-kind":
                let index = try XCTUnwrap(probe.before.objectView.blocks.firstIndex { $0.id == request.objectID })
                probe.before.objectView.blocks[index].text = .init()
            case "wrong-details":
                let index = try XCTUnwrap(probe.before.objectView.details.firstIndex { $0.id == request.objectID })
                probe.before.objectView.details[index].details.fields["spaceId"] = .with { $0.stringValue = "other" }
            case "duplicate": probe.before.objectView.blocks.append(try XCTUnwrap(probe.before.objectView.blocks.first))
            case "missing-child", "cycle":
                let index = try XCTUnwrap(probe.before.objectView.blocks.firstIndex { $0.id == request.objectID })
                probe.before.objectView.blocks[index].childrenIds.append(variant == "cycle" ? request.objectID : "missing-native-child")
            case "unreachable":
                var extra = try XCTUnwrap(probe.before.objectView.blocks.first { $0.id == request.blockID })
                extra.id = "unreachable-native-copy"; extra.childrenIds = []
                probe.before.objectView.blocks.append(extra)
            case "runtime": probe.version = "unsupported-runtime"
            default: break
            }
            let work = Task { @MainActor in
                try await probe.client().readCurrentDocument(
                    spaceID: variant == "foreign-space" ? "foreign" : request.spaceID,
                    objectID: request.objectID, lease: probe.lease)
            }
            if variant == "cancelled" { work.cancel() }
            do { _ = try await work.value; XCTFail("Invalid semantic read accepted: " + variant) }
            catch {
                if variant == "cancelled" { XCTAssertTrue(error is CancellationError) }
                else if variant == "runtime" { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .unsupportedRuntime) }
                else if ["retired", "foreign-space"].contains(variant) {
                    XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .retiredOwner)
                } else { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .changedDocument) }
            }
            XCTAssertTrue(probe.requests.isEmpty)
            XCTAssertTrue(probe.published.isEmpty)
        }
    }

    func testVisibleSelectionPreparationRequiresExplicitApply() async throws {
        let probe = try HeartCaptureProbe()
        let client = probe.client()
        let request = probe.plan.request
        let pending = try await client.prepareVisibleSelection(spaceID: request.spaceID,
            objectID: request.objectID, blockID: request.blockID, anchorID: request.anchorID,
            visibleText: request.expected.text,
            range: NSRange(location: Int(request.from), length: Int(request.to - request.from)), lease: probe.lease)
        XCTAssertEqual(pending.marker, request.marker)
        XCTAssertEqual(probe.calls, ["version", "read-before"])
        XCTAssertTrue(probe.requests.isEmpty)
        XCTAssertTrue(probe.published.isEmpty)
        _ = try await client.apply(pending)
        XCTAssertEqual(probe.requests.count, 1)
        XCTAssertEqual(probe.calls, ["version", "read-before", "version", "read-before",
            "capture", "read-after", "publish"])
    }

    func testVisiblePreparationRejectsChangedMissingForeignAndRetiredOwners() async throws {
        for variant in ["changed-text", "missing-block", "foreign-space", "retired-during-read"] {
            let probe = try HeartCaptureProbe()
            let request = probe.plan.request
            if variant == "retired-during-read" { probe.retireInBeforeRead = true }
            do {
                _ = try await probe.client().prepareVisibleSelection(
                    spaceID: variant == "foreign-space" ? request.spaceID + "-other" : request.spaceID,
                    objectID: request.objectID,
                    blockID: variant == "missing-block" ? "missing-native-block" : request.blockID,
                    anchorID: request.anchorID,
                    visibleText: request.expected.text + (variant == "changed-text" ? "changed" : ""),
                    range: NSRange(location: Int(request.from), length: Int(request.to - request.from)),
                    lease: probe.lease)
                XCTFail("Invalid visible preparation was accepted: " + variant)
            } catch {
                let expected: PinkhaHeartSemanticAnchorError =
                    ["foreign-space", "retired-during-read"].contains(variant) ? .retiredOwner : .changedDocument
                XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, expected)
            }
            XCTAssertTrue(probe.requests.isEmpty)
            XCTAssertTrue(probe.published.isEmpty)
        }
    }

    func testVisiblePreparationRefusesUnsupportedPublicationAndCancellation() async throws {
        for variant in ["runtime", "publisher", "cancelled"] {
            let probe = try HeartCaptureProbe()
            let request = probe.plan.request
            if variant == "runtime" { probe.version = "production139" }
            if variant == "publisher" { probe.publicationAvailable = false }
            let task = Task { @MainActor in
                try await probe.client().prepareVisibleSelection(spaceID: request.spaceID,
                    objectID: request.objectID, blockID: request.blockID, anchorID: request.anchorID,
                    visibleText: request.expected.text,
                    range: NSRange(location: Int(request.from), length: Int(request.to - request.from)),
                    lease: probe.lease)
            }
            if variant == "cancelled" { task.cancel() }
            do { _ = try await task.value; XCTFail("Unavailable preparation was accepted") }
            catch {
                if variant == "cancelled" { XCTAssertTrue(error is CancellationError) }
                else {
                    XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError,
                        variant == "runtime" ? .unsupportedRuntime : .unavailablePublication)
                }
            }
            XCTAssertTrue(probe.requests.isEmpty)
            XCTAssertTrue(probe.published.isEmpty)
        }
    }

    func testPublicationCarriesOnlyExactEventSpaceObjectAndGeneration() async throws {
        let probe = try HeartCaptureProbe()
        let client = probe.client()
        let result = try await client.apply(client.prepare(probe.plan, lease: probe.lease))
        let fence = try XCTUnwrap(probe.publicationFence)
        let event = try XCTUnwrap(probe.published.first)
        XCTAssertTrue(fence.matches(event: event))
        XCTAssertTrue(fence.matches(spaceID: probe.lease.spaceID, objectID: probe.plan.request.objectID))
        XCTAssertEqual(fence.accountID, probe.lease.accountID)
        XCTAssertEqual(fence.generation, result.generation)
        XCTAssertEqual(probe.stateDeliveries, 1)
        var foreign = event
        foreign.messages[0].spaceID += "-other"
        XCTAssertFalse(fence.matches(event: foreign))
        foreign = event
        foreign.messages[0].blockSetText.marks.value.marks[0].param += "-other"
        XCTAssertFalse(fence.matches(event: foreign))
        XCTAssertFalse(fence.matches(spaceID: probe.lease.spaceID + "-other", objectID: event.contextID))
        XCTAssertFalse(fence.matches(spaceID: probe.lease.spaceID, objectID: event.contextID + "-other"))
        XCTAssertNil(PinkhaHeartSemanticAnchorPublication.current)
    }

    func testRetirementDuringPublicationPreventsStateDeliveryAndVerifiedReceipt() async throws {
        let probe = try HeartCaptureProbe()
        probe.retireInPublication = true
        let client = probe.client()
        let pending = try client.prepare(probe.plan, lease: probe.lease)
        do { _ = try await client.apply(pending); XCTFail("Retired publication returned a verified receipt") }
        catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .uncertain) }
        XCTAssertEqual(probe.requests.count, 1)
        XCTAssertEqual(probe.published.count, 1)
        XCTAssertEqual(probe.stateDeliveries, 0)
        XCTAssertEqual(probe.calls.last, "publish")
        XCTAssertNil(PinkhaHeartSemanticAnchorPublication.current)
        do { _ = try await client.apply(pending); XCTFail("Uncertain capture was retried") }
        catch { XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .invalidRequest) }
        XCTAssertEqual(probe.requests.count, 1)
    }

    func testRetiredFenceRefusesNativeStateAndMainConsumer() throws {
        let probe = try HeartCaptureProbe()
        let event = try Anytype_ResponseEvent(serializedBytes: HeartCaptureFixture.data("capture-response-event.pb"))
        let fence = try PinkhaHeartSemanticAnchorPublicationFence(
            lease: probe.lease, objectID: probe.plan.request.objectID, event: event)
        XCTAssertEqual(fence.withCurrentDocumentState(spaceID: probe.lease.spaceID,
            objectID: event.contextID) { 7 }, 7)
        XCTAssertNil(fence.withCurrentDocumentState(spaceID: probe.lease.spaceID,
            objectID: "foreign-object") { XCTFail("Foreign state consumer ran"); return 1 })
        probe.retire()
        XCTAssertNil(fence.withCurrentDocumentState(spaceID: probe.lease.spaceID,
            objectID: event.contextID) { XCTFail("Retired state consumer ran"); return 1 })
        XCTAssertFalse(fence.withCurrentMainDelivery(spaceID: probe.lease.spaceID,
            objectID: event.contextID) { XCTFail("Retired main consumer ran") })
    }

    func testExplicitOwnerCarryAcrossMainQueueRejectsRetiredDelivery() async throws {
        for retired in [false, true] {
            let probe = try HeartCaptureProbe()
            let event = try Anytype_ResponseEvent(serializedBytes: HeartCaptureFixture.data("capture-response-event.pb"))
            let fence = try PinkhaHeartSemanticAnchorPublicationFence(
                lease: probe.lease, objectID: event.contextID, event: event)
            let task = PinkhaHeartSemanticAnchorPublication.$current.withValue(fence) {
                Task { @MainActor in
                    let carried = PinkhaHeartSemanticAnchorPublication.current
                    return await withCheckedContinuation { continuation in
                        DispatchQueue.main.async {
                            let accepted = carried?.withCurrentMainDelivery(spaceID: probe.lease.spaceID,
                                objectID: event.contextID) { probe.recordMainDelivery() } ?? false
                            continuation.resume(returning: accepted)
                        }
                    }
                }
            }
            if retired { probe.retire() }
            let accepted = await task.value
            XCTAssertEqual(accepted, !retired)
            XCTAssertEqual(probe.mainDeliveries, retired ? 0 : 1)
            XCTAssertNil(PinkhaHeartSemanticAnchorPublication.current)
        }
    }

    func testVisiblePreparationPreservesUnicodeByteIdentity() async throws {
        for matching in [false, true] {
            let probe = try HeartCaptureProbe()
            probe.before = try HeartCaptureFixture.alterTarget(probe.before) {
                $0.text.text = "\u{00e9}"
                $0.text.marks = .init()
            }
            let request = probe.plan.request
            do {
                _ = try await probe.client().prepareVisibleSelection(spaceID: request.spaceID,
                    objectID: request.objectID, blockID: request.blockID, anchorID: request.anchorID,
                    visibleText: matching ? "\u{00e9}" : "e\u{0301}",
                    range: NSRange(location: 0, length: 1), lease: probe.lease)
                XCTAssertTrue(matching, "Canonically equivalent but byte-different text was accepted")
            } catch {
                XCTAssertFalse(matching)
                XCTAssertEqual(error as? PinkhaHeartSemanticAnchorError, .changedDocument)
            }
            XCTAssertTrue(probe.requests.isEmpty)
        }
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
