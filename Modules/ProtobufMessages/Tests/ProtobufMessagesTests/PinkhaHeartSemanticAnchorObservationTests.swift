#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation
import SwiftProtobuf
import XCTest
@testable import ProtobufMessages

/// New diagnostic coverage only. I/O below is an explicit fixture; this does
/// not invoke Lib, UIKit, the mounted editor, native storage, or a simulator.
@MainActor
final class PinkhaHeartSemanticAnchorObservationTests: XCTestCase {
    func testPhaseDiagnosticsPreserveRealClientErrorsAndCallCounts() async throws {
        typealias Observation = PinkhaHeartSemanticAnchorApplyObservation
        let successPhases: [Observation.Phase] = [
            .checkingPreflight, .readingRuntime, .checkingRuntime,
            .readingCurrent, .checkingCurrent, .consumed, .checkingQueuedOwner,
            .invokingNative, .checkingCapturedOwner, .decodingReply,
            .validatingEvent, .checkingEventOwner, .creatingPublicationFence,
            .publishing, .checkingPublishedOwner, .readingReadback,
            .checkingReadbackOwner, .validatingReadback, .verified
        ]
        for scenario in ObservationFixture.Scenario.allCases {
            let probe = try ObservationFixture(scenario: scenario)
            let client = probe.client()
            let pending = try client.prepare(probe.plan, lease: probe.lease)
            if scenario == .preflightRetired { probe.retire() }
            var returnedError: PinkhaHeartSemanticAnchorError?
            do {
                _ = try await client.apply(pending)
                XCTAssertEqual(scenario, .verified)
            } catch {
                returnedError = try XCTUnwrap(error as? PinkhaHeartSemanticAnchorError)
                XCTAssertNotEqual(scenario, .verified)
            }
            let value = pending.applyObservation
            XCTAssertFalse(value.phasesTruncated)
            let expectedPhase: Observation.Phase
            let expectedOriginalFailure: Observation.Failure?
            let expectedOutcome: PinkhaHeartSemanticAnchorOutcome?
            switch scenario {
            case .preflightRetired:
                expectedPhase = .checkingPreflight
                expectedOriginalFailure = nil // The unchanged preflight throw is not collapsed.
                expectedOutcome = nil
                XCTAssertEqual(returnedError, .retiredOwner)
            case .nativeUncertain:
                expectedPhase = .decodingReply
                expectedOriginalFailure = .nativeRefusal
                expectedOutcome = .uncertain
                XCTAssertEqual(returnedError, .nativeRefusal(.uncertain))
            case .malformedReply:
                expectedPhase = .decodingReply
                expectedOriginalFailure = .invalidReply
                expectedOutcome = nil
                XCTAssertEqual(returnedError, .uncertain)
            case .invalidEvent:
                expectedPhase = .validatingEvent
                expectedOriginalFailure = .invalidReply
                expectedOutcome = .applied
                XCTAssertEqual(returnedError, .uncertain)
            case .publicationDeclined:
                expectedPhase = .publishing
                expectedOriginalFailure = .uncertain
                expectedOutcome = .applied
                XCTAssertEqual(value.publicationReturned, false)
                XCTAssertEqual(returnedError, .uncertain)
            case .readbackError:
                expectedPhase = .readingReadback
                expectedOriginalFailure = .other
                expectedOutcome = .applied
                XCTAssertEqual(returnedError, .uncertain)
            case .readbackMismatch:
                expectedPhase = .validatingReadback
                expectedOriginalFailure = .uncertain
                expectedOutcome = .applied
                XCTAssertEqual(returnedError, .uncertain)
            case .verified:
                expectedPhase = .verified
                expectedOriginalFailure = nil
                expectedOutcome = .applied
                XCTAssertNil(returnedError)
            }
            let lastIndex = try XCTUnwrap(successPhases.firstIndex(of: expectedPhase))
            XCTAssertEqual(value.phases, Array(successPhases[...lastIndex]))
            XCTAssertEqual(value.latestPhase, expectedPhase)
            XCTAssertEqual(value.firstFailure, expectedOriginalFailure)
            XCTAssertEqual(value.firstFailurePhase, expectedOriginalFailure == nil ? nil : expectedPhase)
            XCTAssertEqual(value.decodedNativeOutcome, expectedOutcome)
            let decodedApplied = [ObservationFixture.Scenario.invalidEvent, .publicationDeclined, .readbackError,
                                  .readbackMismatch, .verified].contains(scenario)
            XCTAssertEqual(value.nativeReceiptDecoded, decodedApplied)
            XCTAssertEqual(probe.captureCalls, scenario == .preflightRetired ? 0 : 1)
            XCTAssertEqual(value.nativeReplyBytes, scenario == .preflightRetired ? nil : probe.reply.count)
            let publishReached = [ObservationFixture.Scenario.publicationDeclined, .readbackError, .readbackMismatch, .verified].contains(scenario)
            XCTAssertEqual(probe.publishCalls, publishReached ? 1 : 0)
            let readbackReached = [ObservationFixture.Scenario.readbackError, .readbackMismatch, .verified].contains(scenario)
            XCTAssertEqual(probe.readCalls, scenario == .preflightRetired ? 0 : (readbackReached ? 2 : 1))
            XCTAssertEqual(value.publicationReturned, publishReached ? (scenario != .publicationDeclined) : nil)
            if expectedOriginalFailure != nil {
                var copy = value
                copy.recordFailure(CancellationError())
                XCTAssertEqual(copy.firstFailure, value.firstFailure)
                XCTAssertEqual(copy.firstFailurePhase, value.firstFailurePhase)
                XCTAssertEqual(copy.decodedNativeOutcome, value.decodedNativeOutcome)
            }
        }

        // The metadata store is finite even if a future caller misuses Pending.
        // No additional apply call or retry is made by this bound check.
        var bounded = Observation()
        for _ in 0...Observation.maximumPhaseCount { bounded.record(.checkingPreflight) }
        XCTAssertEqual(bounded.phases.count, 32)
        XCTAssertTrue(bounded.phasesTruncated)
        XCTAssertNil(bounded.firstFailure)
        bounded.record(.readingRuntime)
        bounded.recordFailure(CancellationError())
        XCTAssertEqual(bounded.phases.count, 32)
        XCTAssertEqual(bounded.latestPhase, .readingRuntime)
        XCTAssertEqual(bounded.firstFailurePhase, .readingRuntime)
        XCTAssertEqual(bounded.firstFailure, .cancellation)
    }
}

@MainActor
private final class ObservationFixture {
    enum Scenario: CaseIterable, Equatable {
        case preflightRetired
        case nativeUncertain
        case malformedReply
        case invalidEvent
        case publicationDeclined
        case readbackError
        case readbackMismatch
        case verified
    }
    private enum FixtureFailure: Error { case readback }
    private struct Request: Decodable {
        let spaceID: String
        let objectID: String
        let blockID: String
        let anchorID: String
        let from: Int32
        let to: Int32
    }

    private let scenario: Scenario
    private let lifetime = PinkhaNativeReadLifetime()
    let plan: PinkhaHeartSemanticAnchorPlan
    let lease: PinkhaNativeReadLease
    let before: Anytype_Rpc.Object.Show.Response
    let after: Anytype_Rpc.Object.Show.Response
    let reply: Data
    private(set) var captureCalls = 0
    private(set) var publishCalls = 0
    private(set) var readCalls = 0

    init(scenario: Scenario) throws {
        self.scenario = scenario
        let request = try JSONDecoder().decode(Request.self, from: Self.data("capture-applied-request.json"))
        let parsedBefore = try Anytype_Rpc.Object.Show.Response(
            serializedBytes: Self.data("capture-before-object-show.pb"))
        let parsedAfter = try Anytype_Rpc.Object.Show.Response(
            serializedBytes: Self.data("capture-after-object-show.pb"))
        before = parsedBefore
        after = parsedAfter
        let block = try XCTUnwrap(parsedBefore.objectView.blocks.first {
            $0.id.utf8.elementsEqual(request.blockID.utf8)
        })
        plan = try .init(spaceID: request.spaceID, objectID: request.objectID,
            anchorID: request.anchorID,
            range: NSRange(location: Int(request.from), length: Int(request.to - request.from)),
            nativeBlock: block)
        let originalReply = try Self.data("capture-applied-response.json")
        switch scenario {
        case .nativeUncertain:
            reply = Data(#"{"protocolVersion":1,"outcome":"uncertain"}"#.utf8)
        case .malformedReply:
            reply = Data([0xff])
        case .invalidEvent:
            var object = try XCTUnwrap(JSONSerialization.jsonObject(with: originalReply) as? [String: Any])
            object["responseEvent"] = Data([0]).base64EncodedString()
            reply = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        default:
            reply = originalReply
        }
        let account = lifetime.beforeInvocation(name: "AccountSelect", request: Anytype_Rpc.Account.Select.Request())
        lifetime.completedInvocation(account, response: Anytype_Rpc.Account.Select.Response.with {
            $0.account = .with { $0.id = "observation-fixture-account"; $0.status.statusType = .active }
        })
        let space = lifetime.beforeInvocation(name: "WorkspaceOpen",
            request: Anytype_Rpc.Workspace.Open.Request.with { $0.spaceID = request.spaceID })
        lifetime.completedInvocation(space, response: Anytype_Rpc.Workspace.Open.Response.with {
            $0.info = .with { $0.workspaceObjectID = "observation-fixture-workspace" }
        })
        lease = try lifetime.lease(forOpenedSpaceID: request.spaceID)
    }

    private static func data(_ name: String) throws -> Data {
        let root = try XCTUnwrap(Bundle.module.url(forResource: "NativePage", withExtension: nil))
        return try Data(contentsOf: root.appendingPathComponent(name))
    }

    func retire() {
        _ = lifetime.beforeInvocation(name: "AccountStop", request: Anytype_Rpc.Account.Stop.Request())
    }

    func client() -> PinkhaHeartSemanticAnchorClient {
        .init(io: .init(
            runtimeVersion: { PinkhaHeartSemanticAnchorProfile.runtimeVersion },
            read: { spaceID, objectID in
                XCTAssertTrue(spaceID.utf8.elementsEqual(self.plan.request.spaceID.utf8))
                XCTAssertTrue(objectID.utf8.elementsEqual(self.plan.request.objectID.utf8))
                self.readCalls += 1
                if self.readCalls == 1 { return self.before }
                if self.scenario == .readbackError { throw FixtureFailure.readback }
                return self.scenario == .readbackMismatch ? self.before : self.after
            },
            capture: { _ in
                self.captureCalls += 1
                return self.reply
            },
            canPublish: { true },
            publish: { _ in
                self.publishCalls += 1
                return self.scenario != .publicationDeclined
            }
        ))
    }
}
#endif
