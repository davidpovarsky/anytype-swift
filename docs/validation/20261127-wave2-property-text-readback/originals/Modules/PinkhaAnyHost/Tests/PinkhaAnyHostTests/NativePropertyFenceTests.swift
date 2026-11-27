import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Client-side capture/dispatch/Undo regressions. Native CAS races are exercised
/// separately against the actual v8 server; these fixtures do not claim that proof.
final class NativePropertyFenceTests: XCTestCase, @unchecked Sendable {
    private let originalGeneration = UUID(uuidString: "11111111-1111-1111-1111-111111111111")!
    private let originalVersion: AnyJSON = .object([
        "any": .object(["type": .string("type-v1"), "collections": .string("collections-v1")]),
        "collection-a": .object(["count": .string("count-v1")])
    ])

    private func workspace(account: String = "account", space: String = "space") throws -> AnyTorahWorkspace {
        try .init(accountID: account, spaceID: space)
    }
    private func store() throws -> AnyNativePropertyStore {
        try .init(client: .init(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account"),
                  workspace: workspace(), policy: .init())
    }
    private func owner(_ id: String, eligible: Bool = false) throws -> AnyNativePropertyOwner {
        try .init(raw: .object(["id": .string(id), "name": .string(id)]), documentEligible: eligible)
    }
    private func definition(_ owner: String, _ id: String, _ kind: String) throws -> AnyNativePropertyDefinition {
        try .init(ownerID: owner, raw: .object([
            "id": .string(id), "name": .string(id), "kind": .string(kind), "scope": .string("synced")
        ]))
    }
    private func raw(sequence: AnyJSON? = .integer(17), count: Int64 = 42,
                     version: AnyJSON? = nil, objectID: String = "document", spaceID: String = "space") -> AnyJSON {
        var fields: [String: AnyJSON] = [
            "id": .string(objectID), "spaceId": .string(spaceID),
            "_ver": version ?? originalVersion,
            "any": .object(["type": .string("page"), "collections": .array([
                .string("collection-a"), .string(AnyNativePropertyStore.presentationCollectionID)
            ])]),
            "collection-a": .object(["count": .integer(count), "unknown": .string("unchanged")]),
            AnyNativePropertyStore.presentationCollectionID: .object([
                AnyNativePropertyStore.hiddenPropertiesID: .array([.string("future:v2:retained")])
            ])
        ]
        fields["_applySeq"] = sequence
        return .object(fields)
    }
    private func snapshot(sequence: AnyJSON? = .integer(17), count: Int64 = 42,
                          version: AnyJSON? = nil, run: String = "run-original",
                          generation: UUID? = nil, account: String = "account",
                          objectID: String = "document", spaceID: String = "space") throws -> AnyNativePropertySnapshot {
        let catalog = try AnyNativePropertyCatalog(workspace: workspace(account: account, space: spaceID),
            generation: generation ?? originalGeneration, engineStartedAt: run,
            types: [owner("page", eligible: true), owner("custom", eligible: true)],
            collections: [owner("collection-a"), owner("collection-b"),
                          owner(AnyNativePropertyStore.presentationCollectionID)])
        let definitions = try [
            definition("any", "type", "string"), definition("any", "collections", "array"),
            definition("collection-a", "count", "number"),
            definition(AnyNativePropertyStore.presentationCollectionID,
                       AnyNativePropertyStore.hiddenPropertiesID, "array")
        ]
        return try AnyNativePropertyStore.materialize(
            raw: raw(sequence: sequence, count: count, version: version, objectID: objectID, spaceID: spaceID),
            objectID: objectID, catalog: catalog, definitions: definitions, policy: .init())
    }
    private func edit(_ value: AnyNativePropertySnapshot? = nil) throws -> AnyPreparedPropertyEdit {
        try store().prepareSetValue(value ?? snapshot(),
            key: .init(ownerID: "collection-a", propertyID: "count"), value: .integer(43))
    }
    private func success(sequence: AnyJSON? = .integer(18), run: String = "run-original",
                         version: AnyJSON? = nil) -> AnyJSON {
        var value: [String: AnyJSON] = [
            "engineStartedAt": .string(run), "propertiesVersion": version ?? originalVersion
        ]
        value["applySeq"] = sequence
        return .object(value)
    }
    private func undo() throws -> AnyPreparedPropertyEdit {
        let subject = try store(), prepared = try edit()
        let accepted = try AnyNativePropertyStore.acceptedFence(success(), original: prepared.fence)
        let result = subject.receipt(for: prepared, accepted: accepted,
                                    readback: try snapshot(sequence: .integer(18), count: 43))
        return try XCTUnwrap(result.undo)
    }

    func testSnapshotRejectsMissingOrInexactApplySequence() throws {
        let invalid: [AnyJSON?] = [nil, .null, .integer(0), .integer(-1),
            .number(17.0), .number(17.5), .number(9_223_372_036_854_776_000.0),
            .string("17"), .bool(true)]
        for sequence in invalid {
            XCTAssertThrowsError(try snapshot(sequence: sequence))
        }
        let maximum = try snapshot(sequence: .integer(Int64.max))
        XCTAssertEqual(maximum.applySequence, Int64.max)
        XCTAssertEqual(maximum.engineStartedAt, "run-original")
        XCTAssertEqual(maximum.fence.nativeVersion, originalVersion)
    }

    func testEveryPreparedMutationRetainsTheSameObservedFence() throws {
        let subject = try store(), value = try snapshot()
        let prepared = try [
            edit(value),
            subject.prepareSetType(value, typeID: "custom"),
            subject.prepareAttachCollection(value, collectionID: "collection-b"),
            subject.prepareDetachCollection(value, collectionID: "collection-a"),
            subject.prepareVisibility(value, key: .init(derived: .sources), visible: false)
        ]
        for mutation in prepared {
            XCTAssertEqual(mutation.fence, value.fence)
            XCTAssertEqual(mutation.applySequence, 17)
            XCTAssertEqual(mutation.engineStartedAt, "run-original")
            XCTAssertEqual(mutation.generation, originalGeneration)
            let body = mutation.fence.requestBody(patch: mutation.patch)
            XCTAssertEqual(body["ifVersion"], value.nativeVersion)
            XCTAssertEqual(body["ifApplySeq"], .integer(17))
            XCTAssertEqual(body["ifStartedAt"], .string("run-original"))
        }
    }

    func testPreparedEditRejectsLateCommutativeSequenceChangeWithIdenticalVersionAndValues() throws {
        let prepared = try edit()
        XCTAssertNoThrow(try prepared.requireMatchingRecord(raw()))
        let late = raw(sequence: .integer(18))
        XCTAssertEqual(late["_ver"], prepared.nativeVersion)
        XCTAssertEqual(late["collection-a"], raw()["collection-a"])
        XCTAssertThrowsError(try prepared.requireMatchingRecord(late)) {
            XCTAssertEqual($0 as? AnyHostError, .changedDocument)
        }
        XCTAssertThrowsError(try prepared.requireMatchingRecord(raw(sequence: nil)))
        XCTAssertThrowsError(try prepared.requireMatchingRecord(raw(objectID: "other-document")))
        XCTAssertThrowsError(try prepared.requireMatchingRecord(raw(spaceID: "other-space")))
        XCTAssertEqual(prepared.applySequence, 17, "A fresh row must not rebase the pending mutation.")
    }

    func testApplySequenceAboveDoublePrecisionIsPreservedExactlyOnWire() throws {
        let precise: Int64 = 9_007_199_254_740_993
        let prepared = try edit(snapshot(sequence: .integer(precise)))
        let body = prepared.fence.requestBody(patch: prepared.patch)
        let bytes = try JSONEncoder().encode(body)
        let decoded = try JSONDecoder().decode(AnyJSON.self, from: bytes)
        XCTAssertEqual(decoded["ifApplySeq"], .integer(precise))
        XCTAssertTrue(String(decoding: bytes, as: UTF8.self).contains("9007199254740993"))
        XCTAssertEqual(decoded["ifStartedAt"], .string("run-original"))
        XCTAssertEqual(decoded["ifVersion"], prepared.nativeVersion)
    }

    func testAcceptedWriteRequiresExactPositiveSequenceAndOriginalRun() throws {
        let prepared = try edit()
        let invalid: [AnyJSON?] = [nil, .null, .integer(0), .integer(-1),
                                  .integer(16), .integer(17), .number(18.0), .string("18")]
        for sequence in invalid {
            XCTAssertThrowsError(try AnyNativePropertyStore.acceptedFence(
                success(sequence: sequence), original: prepared.fence)) {
                XCTAssertEqual($0 as? AnyHostError, .writeUncertain)
            }
        }
        XCTAssertThrowsError(try AnyNativePropertyStore.acceptedFence(
            success(run: "replacement-run"), original: prepared.fence)) {
            XCTAssertEqual($0 as? AnyHostError, .writeUncertain)
        }
        XCTAssertThrowsError(try AnyNativePropertyStore.acceptedFence(
            success(version: .string("not-a-version-tree")), original: prepared.fence))
        XCTAssertEqual(try AnyNativePropertyStore.acceptedFence(success(), original: prepared.fence).applySequence, 18)
    }

    func testLaterReadbackWithSameVersionAndRequestedValueCannotMintUndo() throws {
        let subject = try store(), prepared = try edit()
        let accepted = try AnyNativePropertyStore.acceptedFence(success(), original: prepared.fence)
        let later = try snapshot(sequence: .integer(19), count: 43)
        XCTAssertEqual(later.nativeVersion, accepted.nativeVersion)
        XCTAssertEqual(later.raw["collection-a"]?["count"], prepared.patch["count"])
        let result = subject.receipt(for: prepared, accepted: accepted, readback: later)
        XCTAssertEqual(result.readback, .nativeAcceptedButCurrentStateUnverified)
        XCTAssertNil(result.snapshot)
        XCTAssertNil(result.undo)
    }

    func testExactAcknowledgementBindsUndoToItsSequenceWithoutChangingOriginalIntent() throws {
        let subject = try store(), prepared = try edit()
        let accepted = try AnyNativePropertyStore.acceptedFence(success(), original: prepared.fence)
        let readback = try snapshot(sequence: .integer(18), count: 43)
        let result = subject.receipt(for: prepared, accepted: accepted, readback: readback)
        XCTAssertEqual(result.readback, .verifiedCurrent)
        XCTAssertEqual(result.snapshot?.fence, accepted)
        let inverse = try XCTUnwrap(result.undo)
        XCTAssertEqual(inverse.patch, ["count": .integer(42)])
        XCTAssertEqual(inverse.fence, readback.fence)
        XCTAssertEqual(inverse.engineStartedAt, "run-original")
        XCTAssertEqual(inverse.generation, originalGeneration)
        XCTAssertEqual(prepared.applySequence, 17)
        XCTAssertNoThrow(try inverse.requireMatchingRecord(readback.raw))
        XCTAssertThrowsError(try inverse.requireMatchingRecord(raw(sequence: .integer(19), count: 43))) {
            XCTAssertEqual($0 as? AnyHostError, .changedDocument)
        }
    }

    func testReadbackFromDifferentOwnerEpochOrTargetCannotCertifyTheWrite() throws {
        let subject = try store(), prepared = try edit()
        let accepted = try AnyNativePropertyStore.acceptedFence(success(), original: prepared.fence)
        let wrong = try [
            snapshot(sequence: .integer(18), count: 43, run: "replacement-run"),
            snapshot(sequence: .integer(18), count: 43, generation: UUID()),
            snapshot(sequence: .integer(18), count: 43, account: "other-account"),
            snapshot(sequence: .integer(18), count: 43, objectID: "other-document"),
            snapshot(sequence: .integer(18), count: 43, spaceID: "other-space"),
            snapshot(sequence: .integer(18), count: 44)
        ]
        for readback in wrong {
            let result = subject.receipt(for: prepared, accepted: accepted, readback: readback)
            XCTAssertEqual(result.readback, .nativeAcceptedButCurrentStateUnverified)
            XCTAssertNil(result.snapshot)
            XCTAssertNil(result.undo)
        }
    }

    func testPendingEditAndUndoRefuseReplacedAccountSpaceRunAndGenerationBeforeTransport() async throws {
        let subject = try store()
        let prepared = try [edit(), undo()]
        let scopes: [(AnyTorahWorkspace, UUID, String)] = try [
            (workspace(account: "other-account"), originalGeneration, "run-original"),
            (workspace(space: "other-space"), originalGeneration, "run-original"),
            (workspace(), originalGeneration, "replacement-run"),
            (workspace(), UUID(), "run-original")
        ]
        for mutation in prepared {
            for (scope, generation, run) in scopes {
                let lease = AnyHostLease(workspace: scope, generation: generation, engineStartedAt: run, check: {})
                do {
                    _ = try await subject.apply(mutation, lease: lease)
                    XCTFail("An old property mutation must not cross its original account, Space, run or generation.")
                } catch {
                    XCTAssertEqual(error as? AnyHostError, .wrongWorkspace)
                }
            }
        }
    }

    func testPendingEditAndUndoHonorRevokedLeaseWithoutReplacingCapturedFence() async throws {
        let subject = try store()
        let prepared = try [edit(), undo()]
        let lease = AnyHostLease(workspace: try workspace(), generation: originalGeneration,
            engineStartedAt: "run-original", check: { throw AnyHostError.engineRestarted })
        for mutation in prepared {
            do {
                _ = try await subject.apply(mutation, lease: lease)
                XCTFail("A revoked owner must stop before transport.")
            } catch {
                XCTAssertEqual(error as? AnyHostError, .engineRestarted)
            }
            XCTAssertEqual(mutation.engineStartedAt, "run-original")
        }
        XCTAssertEqual(prepared[0].applySequence, 17)
        XCTAssertEqual(prepared[1].applySequence, 18)
    }
}
