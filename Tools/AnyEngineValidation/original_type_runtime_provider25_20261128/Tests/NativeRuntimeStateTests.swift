import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Wire-domain and isolation checks for the versioned native observation API.
/// These synthetic contract samples are not new coordinator or native evidence.
final class NativeRuntimeStateTests: XCTestCase {
    func testGuestScopeAndObservedZeroRemainDistinctFromMissingCoordinatorData() throws {
        let lease = try NativeRuntimeWireFixture.lease()
        let absent = try space(NativeRuntimeWireFixture.space(), lease: lease)
        XCTAssertEqual(absent.scope.authorityIdentity, "loaded-guest")
        XCTAssertNotEqual(absent.scope.authorityIdentity, absent.scope.accountID)
        XCTAssertEqual(absent.generation, lease.generation)
        XCTAssertEqual(absent.engineStartedAt, lease.engineStartedAt)
        XCTAssertEqual(absent.capturedAt.rawValue, NativeRuntimeWireFixture.captured)
        XCTAssertNil(absent.coordinator)
        XCTAssertNil(absent.access.value)
        XCTAssertFalse(absent.access.aclIsEmpty)
        XCTAssertEqual(absent.access.reason, .personalProvenanceUnavailable)
        XCTAssertFalse(absent.permitsDestinationWrites)

        let noLimits = try space(NativeRuntimeWireFixture.space(coordinator: NativeRuntimeWireFixture.coordinator()))
        XCTAssertNil(try XCTUnwrap(noLimits.coordinator).limits)
        let observed = try space(NativeRuntimeWireFixture.space(coordinator:
            NativeRuntimeWireFixture.coordinator(limits: .object([
                "readersLimit": .integer(0), "writersLimit": .integer(Int64(UInt32.max))]))))
        let coordinator = try XCTUnwrap(observed.coordinator)
        XCTAssertEqual(coordinator.limits?.readers, 0)
        XCTAssertEqual(coordinator.limits?.writers, UInt32.max)
        XCTAssertEqual(coordinator.fetchedAt.rawValue, NativeRuntimeWireFixture.confirmed)
        XCTAssertNotEqual(coordinator.fetchedAt, observed.capturedAt)
        XCTAssertNil(observed.access.value, "a sharing answer cannot invent Personal provenance")
    }

    func testAccessKeepsOriginalPersonalFirstClassificationAndRequiresItsProvenance() throws {
        let cases: [(Bool, String?, Int64?, String, AnyJSON, AnyHeartSpaceAccessType?)] = [
            (false, nil, nil, "personal_provenance_unavailable", .null, nil),
            (false, "space", 1, "native_personal", NativeRuntimeWireFixture.coordinator(shared: true), .personal),
            (false, "other-personal", 2, "native_acl_shared", .null, .shared),
            (true, "other-personal", 2, "coordinator_shared", NativeRuntimeWireFixture.coordinator(shared: true), .shared),
            (true, "other-personal", 0, "native_private", NativeRuntimeWireFixture.coordinator(shared: false), .private),
            (true, "other-personal", nil, "coordinator_unavailable", .null, nil)
        ]
        for (empty, personal, value, reason, coordinator, expected) in cases {
            let response = NativeRuntimeWireFixture.space(coordinator: coordinator,
                access: NativeRuntimeWireFixture.access(empty: empty, personal: personal, value: value, reason: reason))
            XCTAssertEqual(try space(response).access.value, expected)
        }
        let contradictions: [AnyJSON] = [
            NativeRuntimeWireFixture.access(empty: false, personal: nil, value: 2, reason: "native_acl_shared"),
            NativeRuntimeWireFixture.access(empty: true, personal: "other-personal", value: 2, reason: "native_acl_shared"),
            NativeRuntimeWireFixture.access(empty: false, personal: "space", value: 2, reason: "native_acl_shared"),
            NativeRuntimeWireFixture.access(empty: false, personal: "other-personal", value: 1, reason: "native_personal"),
            NativeRuntimeWireFixture.access(empty: true, personal: "other-personal", value: 0, reason: "native_private"),
            NativeRuntimeWireFixture.access(empty: true, personal: "other-personal", value: 2, reason: "coordinator_shared"),
            NativeRuntimeWireFixture.access(empty: false, personal: "space", value: nil, reason: "personal_provenance_unavailable"),
            NativeRuntimeWireFixture.access(empty: false, personal: nil, value: 0, reason: "native_private")
        ]
        for evidence in contradictions {
            XCTAssertThrowsError(try space(NativeRuntimeWireFixture.space(access: evidence)))
        }
    }

    func testExactAccountNetworkSpaceAndLeaseBytesCannotCrossCanonicalUnicodeAliases() throws {
        let composed = "caf\u{00E9}"
        let decomposed = "cafe\u{0301}"
        XCTAssertEqual(composed, decomposed)
        XCTAssertNotEqual(Data(composed.utf8), Data(decomposed.utf8))
        let workspace = try AnyTorahWorkspace(accountID: composed, spaceID: composed)
        let lease = try NativeRuntimeWireFixture.lease(workspace: workspace)
        let response = NativeRuntimeWireFixture.space(scope: NativeRuntimeWireFixture.scope(
            account: composed, network: composed, space: composed))
        let original = try AnyNativeRuntimeStateStore.parseSpace(response, workspace: workspace,
            expectedNetworkID: composed, lease: lease)
        for key in ["accountId", "networkId", "spaceId"] {
            let changed = try NativeRuntimeWireFixture.replacing(["scope", key], in: response, with: .string(decomposed))
            XCTAssertThrowsError(try AnyNativeRuntimeStateStore.parseSpace(changed, workspace: workspace,
                expectedNetworkID: composed, lease: lease), key)
        }
        for foreign in [try AnyTorahWorkspace(accountID: decomposed, spaceID: composed),
                        try AnyTorahWorkspace(accountID: composed, spaceID: decomposed)] {
            XCTAssertThrowsError(try AnyNativeRuntimeStateStore.parseSpace(response, workspace: workspace,
                expectedNetworkID: composed, lease: NativeRuntimeWireFixture.lease(workspace: foreign)))
        }
        let changedAuthority = try NativeRuntimeWireFixture.replacing(["scope", "authorityIdentity"],
            in: response, with: .string(composed))
        let changedAuthorityAgain = try NativeRuntimeWireFixture.replacing(["scope", "authorityIdentity"],
            in: response, with: .string(decomposed))
        let first = try AnyNativeRuntimeStateStore.parseSpace(changedAuthority, workspace: workspace,
            expectedNetworkID: composed, lease: lease)
        let second = try AnyNativeRuntimeStateStore.parseSpace(changedAuthorityAgain, workspace: workspace,
            expectedNetworkID: composed, lease: lease)
        XCTAssertNotEqual(first.scope, second.scope)
        XCTAssertEqual(original.scope.aclHeadID, "signed-head")
        XCTAssertThrowsError(try object(NativeRuntimeWireFixture.object(objectID: "foreign-object")))
    }

    func testHistoricalObjectConfirmationDoesNotInventCurrentConnectivityOrObjectExistence() throws {
        let response = NativeRuntimeWireFixture.object()
        let value = try object(response)
        XCTAssertEqual(value.objectSync.state, .synced)
        XCTAssertEqual(value.objectSync.basis, .responsibleSpaceRound)
        XCTAssertEqual(value.objectSync.lastSyncAt?.rawValue, NativeRuntimeWireFixture.confirmed)
        XCTAssertEqual(value.spaceSync.state, .offline)
        XCTAssertEqual(value.spaceSync.p2p, .notConnected)
        XCTAssertNotEqual(value.objectSync.lastSyncAt, value.capturedAt)
        XCTAssertFalse(value.provesObjectExistence)
        XCTAssertFalse(value.permitsDestinationWrites)
        let unknown = try NativeRuntimeWireFixture.replacing(["objectSync"], in: response, with: .object([
            "state": .string("unknown"), "basis": .string("unobserved"), "lastSyncAt": .null]))
        let unobserved = try object(unknown)
        XCTAssertEqual(unobserved.objectSync.state, .unknown)
        XCTAssertNil(unobserved.objectSync.lastSyncAt)
        // The native samples are separate observations, not one atomic rollup.
        let separateFlag = try NativeRuntimeWireFixture.replacing(["spaceSync", "networkProtocolIncompatible"],
            in: unknown, with: .bool(true))
        XCTAssertTrue(try object(separateFlag).spaceSync.networkProtocolIncompatible)
        XCTAssertEqual(try object(separateFlag).spaceSync.state, .offline)
    }

    func testMalformedDomainsAndContradictoryNativeProvenanceFailClosed() throws {
        let response = NativeRuntimeWireFixture.object()
        let invalid: [([String], AnyJSON)] = [
            (["objectSync", "state"], .integer(0)),
            (["objectSync", "state"], .string("queued")),
            (["objectSync", "state"], .string("offline")),
            (["objectSync", "basis"], .string("unobserved")),
            (["objectSync", "lastSyncAt"], .null),
            (["spaceSync", "p2p"], .string("connected-to-cloud")),
            (["spaceSync", "synced"], .integer(2)),
            (["spaceSync", "total"], .integer(-1)),
            (["spaceSync", "networkPeers"], .number(0.5)),
            (["spaceSync", "localPeers"], .bool(false)),
            (["spaceSync", "globalPeers"], .string("0")),
            (["spaceSync", "spaceId"], .string("other-space")),
            (["capturedAt"], .string("2026-11-27T21:00:00.1234567890Z"))
        ]
        for (path, value) in invalid {
            XCTAssertThrowsError(try object(NativeRuntimeWireFixture.replacing(path, in: response, with: value)), path.joined(separator: "."))
        }
        for key in ["accountId", "networkId", "spaceId", "authorityIdentity", "aclHeadId"] {
            for invalid in ["", "nul\u{0}", String(repeating: "a", count: 1_025)] {
                XCTAssertThrowsError(try space(NativeRuntimeWireFixture.replacing(["scope", key],
                    in: NativeRuntimeWireFixture.space(), with: .string(invalid))))
            }
        }
        for limit in [AnyJSON.integer(-1), .integer(Int64(UInt32.max) + 1), .number(0.5), .null] {
            let raw = NativeRuntimeWireFixture.space(coordinator: NativeRuntimeWireFixture.coordinator(limits:
                .object(["readersLimit": limit, "writersLimit": .integer(0)])))
            XCTAssertThrowsError(try space(raw))
        }
    }

    func testClosedVersionedSchemasDoNotSilentlyEraseMalformedOrMissingData() throws {
        let inputs: [(AnyJSON, [[String]], (AnyJSON) throws -> Void)] = [
            (NativeRuntimeWireFixture.space(), [[], ["scope"], ["access"]], { _ = try self.space($0) }),
            (NativeRuntimeWireFixture.object(), [[], ["scope"], ["objectSync"], ["spaceSync"]], { _ = try self.object($0) })
        ]
        for (raw, paths, parse) in inputs {
            for path in paths {
                let group = try NativeRuntimeWireFixture.value(path, in: raw)
                let fields = try XCTUnwrap(group.object)
                for key in fields.keys {
                    var missing = fields
                    missing.removeValue(forKey: key)
                    XCTAssertThrowsError(try parse(NativeRuntimeWireFixture.replacing(path, in: raw, with: .object(missing))),
                        (path + [key]).joined(separator: "."))
                }
                var extra = fields
                extra["unexpected"] = .bool(true)
                XCTAssertThrowsError(try parse(NativeRuntimeWireFixture.replacing(path, in: raw, with: .object(extra))))
            }
            XCTAssertThrowsError(try parse(NativeRuntimeWireFixture.replacing(["contract"], in: raw, with: .string("future-contract"))))
        }
        XCTAssertThrowsError(try space(NativeRuntimeWireFixture.space(coordinator: .object([:]))))
        XCTAssertThrowsError(try space(NativeRuntimeWireFixture.space(coordinator: .bool(false))))
        XCTAssertThrowsError(try object(.null))
    }

    private func space(_ raw: AnyJSON, lease: AnyHostLease? = nil) throws -> AnyNativeSpaceRuntimeSnapshot {
        let workspace = try NativeRuntimeWireFixture.workspace()
        return try AnyNativeRuntimeStateStore.parseSpace(raw, workspace: workspace,
            expectedNetworkID: "network", lease: lease ?? NativeRuntimeWireFixture.lease(workspace: workspace))
    }

    private func object(_ raw: AnyJSON) throws -> AnyNativeObjectRuntimeSnapshot {
        let workspace = try NativeRuntimeWireFixture.workspace()
        return try AnyNativeRuntimeStateStore.parseObject(raw, objectID: "object", workspace: workspace,
            expectedNetworkID: "network", lease: NativeRuntimeWireFixture.lease(workspace: workspace))
    }
}

enum NativeRuntimeWireFixture {
    static let confirmed = "2026-11-27T05:42:46.340108716Z"
    static let captured = "2026-11-27T21:00:00.000000001Z"

    static func workspace() throws -> AnyTorahWorkspace { try .init(accountID: "account", spaceID: "space") }
    static func lease(workspace: AnyTorahWorkspace? = nil,
                      check: @escaping @Sendable () async throws -> Void = {}) throws -> AnyHostLease {
        try .init(workspace: workspace ?? Self.workspace(), generation: UUID(), engineStartedAt: "original-run", check: check)
    }
    static func scope(account: String = "account", network: String = "network", space: String = "space") -> AnyJSON {
        .object(["accountId": .string(account), "networkId": .string(network), "spaceId": .string(space),
            "authorityIdentity": .string("loaded-guest"), "aclHeadId": .string("signed-head")])
    }
    static func coordinator(shared: Bool = false, limits: AnyJSON = .null) -> AnyJSON {
        .object(["fetchedAt": .string(confirmed), "status": .string("original-coordinator-label"),
            "isShared": .bool(shared), "limits": limits])
    }
    static func access(empty: Bool = false, personal: String? = nil, value: Int64? = nil,
                       reason: String = "personal_provenance_unavailable") -> AnyJSON {
        .object(["aclIsEmpty": .bool(empty), "personalSpaceId": personal.map(AnyJSON.string) ?? .null,
            "value": value.map(AnyJSON.integer) ?? .null, "reason": .string(reason)])
    }
    static func space(coordinator: AnyJSON = .null, access: AnyJSON? = nil, scope: AnyJSON? = nil) -> AnyJSON {
        .object(["contract": .string("pinkha-space-runtime-state-v1"), "scope": scope ?? Self.scope(),
            "capturedAt": .string(captured), "coordinator": coordinator, "access": access ?? Self.access()])
    }
    static func object(objectID: String = "object") -> AnyJSON {
        .object(["contract": .string("pinkha-object-runtime-state-v1"), "scope": scope(), "objectId": .string(objectID),
            "capturedAt": .string(captured),
            "objectSync": .object(["state": .string("synced"), "basis": .string("responsible_space_round"),
                "lastSyncAt": .string(confirmed)]),
            "spaceSync": .object(["spaceId": .string("space"), "state": .string("offline"),
                "lastSyncedAt": .string(confirmed), "synced": .integer(1), "total": .integer(1),
                "networkPeers": .integer(0), "localPeers": .integer(0), "globalPeers": .integer(0),
                "p2p": .string("notconnected"), "networkProtocolIncompatible": .bool(false)])])
    }
    static func value(_ path: [String], in raw: AnyJSON) throws -> AnyJSON {
        guard let first = path.first else { return raw }
        return try value(Array(path.dropFirst()), in: XCTUnwrap(raw[first]))
    }
    static func replacing(_ path: [String], in raw: AnyJSON, with replacement: AnyJSON) throws -> AnyJSON {
        guard let first = path.first else { return replacement }
        var fields = try XCTUnwrap(raw.object)
        fields[first] = try replacing(Array(path.dropFirst()), in: XCTUnwrap(fields[first]), with: replacement)
        return .object(fields)
    }
}
