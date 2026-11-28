import Foundation
import XCTest
@testable import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Seven new contract controls. Original catalog evidence is read only through
/// the retained canonical fixture. The other values are explicitly synthetic.
/// No native account, HTTP server, mutation, or earlier test method is invoked.
final class NativePersonalNavigationContractTests: XCTestCase, @unchecked Sendable {
    func testOriginalLastOpenedDescriptorAndDecodedBindingKeepExactSourceIdentity() throws {
        let fixture = try NativeCanonicalSupplementFixture.load()
        defer { XCTAssertNoThrow(try fixture.requireRetainedInputsUnchanged()) }
        let evidence = try fixture.evidence("rel-lastOpenedDate")
        let binding = try AnyHeartLastOpenedBinding(evidence: evidence)
        XCTAssertEqual(evidence.snapshot.nativeType, 521)
        XCTAssertEqual(evidence.snapshot.uniqueKey, "rel-lastOpenedDate")
        XCTAssertEqual(evidence.viewSHA256,
            "988a27967531491f7dc196fd6ef610a956b030aa339c3062b36d518a16bcf52a")
        XCTAssertEqual(evidence.snapshotSHA256,
            "f0081c0e631ee938a9e4f096e3dd5acad5b96b81e1c08784a84575e7e068e52d")
        XCTAssertEqual(try canonical(.object(evidence.snapshot.details)),
                       try canonical(Self.originalLastOpenedDescriptor))
        XCTAssertEqual(binding.readContract, "pinkha-heart-last-opened-provider-v1")
        XCTAssertFalse(binding.sourceHidden)
        XCTAssertTrue(binding.sourceDeclaresReadonlyValue)
        XCTAssertEqual(binding.nativeOwnerID, "any")
        XCTAssertEqual(binding.nativePropertyID, "pinkhaLastOpenedV1")
        XCTAssertFalse(binding.permitsArchivedValueReplay)
        try binding.requireSource(fixture.plan.source)

        let encoded = try JSONEncoder().encode(binding)
        let decoded = try JSONDecoder().decode(AnyHeartLastOpenedBinding.self, from: encoded)
        XCTAssertEqual(decoded, binding)
        try decoded.requireSource(fixture.plan.source)
        var fields = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: encoded).object)
        fields["readContract"] = .string("caller-selected-current-provider")
        XCTAssertThrowsError(try JSONDecoder().decode(AnyHeartLastOpenedBinding.self,
            from: jsonBytes(.object(fields))))
        XCTAssertThrowsError(try AnyHeartLastOpenedBinding(evidence: fixture.evidence("rel-createdDate")))

        // A self-consistent outer source from another Space is still foreign
        // to the retained plan. The typed descriptor alone grants no authority.
        var view = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: evidence.jsonViewBytes).object)
        let foreignSpace = evidence.sourceSpaceID + "-foreign"
        view["SpaceID"] = .string(foreignSpace)
        let foreign = try AnyHeartLastOpenedBinding(evidence: .init(
            sourceSpaceID: foreignSpace, sourceObjectID: evidence.sourceObjectID,
            protobufBytes: evidence.protobufBytes, jsonViewBytes: jsonBytes(.object(view))))
        XCTAssertThrowsError(try foreign.requireSource(fixture.plan.source))

        for (key, replacement) in [
            ("isHidden", AnyJSON.bool(true)),
            ("description", .string("Date when the object was last opened")),
            ("relationDefaultValue", .string("")),
            ("internalFlags", .null),
            ("relationFormatObjectTypes", .null),
            ("sourceObject", .string("pinkhaLastOpenedV1"))
        ] {
            XCTAssertThrowsError(try changedDescriptorBinding(evidence, key: key, value: replacement), key)
        }
    }

    func testHomePreservesAbsentEmptyUnknownAndClosedWireVariants() throws {
        if case .absent = AnyNativeHomeValue.project(nil) {} else {
            XCTFail("missing native preference became a route")
        }
        if case .selection(.empty) = AnyNativeHomeValue.project(.string("")) {} else {
            XCTFail("explicit empty preference was erased")
        }
        for raw in [AnyJSON.null, .integer(0), .object([:]), .string("future native preference")] {
            guard case .unsupported(let retained) = AnyNativeHomeValue.project(raw) else {
                return XCTFail("unsupported preference became a default route")
            }
            XCTAssertEqual(try canonical(retained), try canonical(raw))
        }
        XCTAssertEqual(try AnyNativeHomeSelection.empty.wireValue(), .string(""))
        for builtIn in AnyNativeHomeSelection.BuiltIn.allCases {
            let selection = AnyNativeHomeSelection.builtIn(builtIn)
            let raw = try selection.wireValue()
            XCTAssertEqual(AnyNativeHomeSelection.decode(raw), selection)
            let fields = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self,
                from: Data(try XCTUnwrap(raw.string).utf8)).object)
            XCTAssertEqual(Set(fields.keys), ["contract", "kind", "value"])
            XCTAssertEqual(fields["contract"], .string("pinkha-current-home-v1"))
            XCTAssertEqual(fields["value"], .string(builtIn.rawValue))
        }
        let object = AnyNativeHomeSelection.object("known-native-object")
        XCTAssertEqual(AnyNativeHomeSelection.decode(try object.wireValue()), object)
        let invalid: [[String: AnyJSON]] = [
            ["contract": .string("future-contract"), "kind": .string("builtin"), "value": .string("graph")],
            ["contract": .string("pinkha-current-home-v1"), "kind": .string("builtin"), "value": .string("future")],
            ["contract": .string("pinkha-current-home-v1"), "kind": .string("builtin"), "value": .string("graph"), "objectId": .string("extra")],
            ["contract": .string("pinkha-current-home-v1"), "kind": .string("object")],
            ["contract": .string("pinkha-current-home-v1"), "kind": .string("object"), "objectId": .string("")],
            ["contract": .string("pinkha-current-home-v1"), "kind": .string("object"), "objectId": .string("id"), "value": .string("graph")],
            ["kind": .string("builtin"), "value": .string("graph")],
            ["contract": .string("pinkha-current-home-v1"), "kind": .string("unknown"), "value": .string("graph")]
        ]
        for fields in invalid {
            let raw = try homeWire(fields)
            XCTAssertNil(AnyNativeHomeSelection.decode(raw))
            guard case .unsupported(let retained) = AnyNativeHomeValue.project(raw) else {
                return XCTFail("closed invalid home shape selected a route")
            }
            XCTAssertEqual(try canonical(retained), try canonical(raw))
        }
        XCTAssertNil(AnyNativeHomeSelection.decode(.string(String(repeating: "x", count: 16_385))))
        for invalidID in ["", ".", "..", "a b", "a\u{0000}b", "a\u{007f}b"] {
            XCTAssertThrowsError(try AnyNativeHomeSelection.object(invalidID).wireValue())
        }
    }

    func testObjectWorkspaceAndEngineBindingIdentitiesUseExactUTF8() throws {
        let composed = "id-\u{00e9}"
        let decomposed = "id-e\u{0301}"
        XCTAssertEqual(composed, decomposed, "the control deliberately uses canonical Unicode aliases")
        XCTAssertNotEqual(Data(composed.utf8), Data(decomposed.utf8))
        XCTAssertNotEqual(AnyNativeHomeSelection.object(composed), .object(decomposed))
        let one = try AnyNativeHomeSelection.object(composed).wireValue()
        let two = try AnyNativeHomeSelection.object(decomposed).wireValue()
        XCTAssertFalse(AnyNativePersonalNavigationStore.sameRaw(one, two))
        XCTAssertFalse(AnyNativePersonalNavigationStore.same(composed, decomposed))
        XCTAssertEqual(AnyNativeHomeSelection.decode(one), .object(composed))
        XCTAssertNotEqual(AnyNativeHomeSelection.decode(one), .object(decomposed))

        let account = try AnyTorahWorkspace(accountID: composed, spaceID: "space")
        let accountAlias = try AnyTorahWorkspace(accountID: decomposed, spaceID: "space")
        let space = try AnyTorahWorkspace(accountID: "account", spaceID: composed)
        let spaceAlias = try AnyTorahWorkspace(accountID: "account", spaceID: decomposed)
        XCTAssertFalse(AnyNativePersonalNavigationStore.sameWorkspace(account, accountAlias))
        XCTAssertFalse(AnyNativePersonalNavigationStore.sameWorkspace(space, spaceAlias))
        let binding = try AnyNativeAccountRunBinding(accountID: composed, networkID: "network",
            runID: String(repeating: "a", count: 64))
        let alias = try AnyNativeAccountRunBinding(accountID: decomposed, networkID: "network",
            runID: String(repeating: "a", count: 64))
        XCTAssertNotEqual(binding, alias)
        let raw: AnyJSON = .object([
            "contract": .string("pinkha-any-http-engine-binding-v1"),
            "accountId": .string(composed), "networkId": .string("network"),
            "runId": .string(String(repeating: "a", count: 64))
        ])
        XCTAssertThrowsError(try AnyNativeAccountRunBinding.decode(raw,
            expectedAccountID: decomposed, expectedNetworkID: "network")) {
            XCTAssertEqual($0 as? AnyEngineError, .accountChanged)
        }
        XCTAssertTrue(AnyNativePersonalNavigationStore.validID(String(repeating: "x", count: 4096)))
        XCTAssertFalse(AnyNativePersonalNavigationStore.validID(String(repeating: "x", count: 4097)))
        XCTAssertTrue(AnyNativePersonalNavigationStore.validID(String(repeating: "\u{00e9}", count: 2048)))
        XCTAssertFalse(AnyNativePersonalNavigationStore.validID(String(repeating: "\u{00e9}", count: 2049)))
        XCTAssertFalse(AnyNativePersonalNavigationStore.sameRaw(nil, .string("")))
    }

    func testOpenedDateUsesWholeUnixSecondsAndExactNativeMilliseconds() throws {
        XCTAssertEqual(try AnyNativePersonalNavigationStore.openedSecond(
            Date(timeIntervalSince1970: 1_760_000_123.999)), 1_760_000_123)
        XCTAssertEqual(try AnyNativePersonalNavigationStore.openedSecond(
            Date(timeIntervalSince1970: 0)), 0)
        XCTAssertEqual(try AnyNativePersonalNavigationStore.openedSecond(
            Date(timeIntervalSince1970: 253_402_300_799)), 253_402_300_799)
        for invalid in [-0.001, 253_402_300_800, Double.infinity, -Double.infinity, Double.nan] {
            XCTAssertThrowsError(try AnyNativePersonalNavigationStore.openedSecond(
                Date(timeIntervalSince1970: invalid))) {
                XCTAssertEqual($0 as? AnyNativePersonalNavigationError, .invalidOpenedDate)
            }
        }
        XCTAssertNil(try AnyNativePersonalNavigationStore.lastOpenedMilliseconds(nil))
        for (raw, expected) in [
            (AnyJSON.object(["$date": .integer(0)]), Int64(0)),
            (.object(["$date": .integer(1_760_000_123_000)]), 1_760_000_123_000),
            (.object(["$date": .integer(253_402_300_799_000)]), 253_402_300_799_000),
            (.object(["$date": .string("1970-01-01T00:00:00.000Z")]), 0),
            (.object(["$date": .string("2025-10-09T08:55:23.000Z")]), 1_760_000_123_000),
            (.object(["$date": .string("2025-10-09T08:55:23Z")]), 1_760_000_123_000)
        ] {
            XCTAssertEqual(try AnyNativePersonalNavigationStore.lastOpenedMilliseconds(raw), expected)
        }
        let malformed: [AnyJSON] = [
            .null, .integer(0), .object([:]),
            .object(["$date": .integer(-1000)]),
            .object(["$date": .integer(1_760_000_123_001)]),
            .object(["$date": .integer(253_402_300_800_000)]),
            .object(["$date": .string("2025-10-09T08:55:23.001Z")]),
            .object(["$date": .string("not-a-date")]),
            .object(["$date": .null]),
            .object(["$date": .bool(false)]),
            .object(["$date": .integer(0), "extra": .bool(true)])
        ]
        for raw in malformed {
            XCTAssertThrowsError(try AnyNativePersonalNavigationStore.lastOpenedMilliseconds(raw))
        }
    }

    func testLastOpenedBuiltinRequiresOneImmutableLocalDatetimeDescriptor() throws {
        let original = Self.lastOpenedDefinition
        try AnyNativePersonalNavigationStore.validateLastOpenedDefinition(
            .object(["properties": .array([original])]))
        let other = AnyJSON.object(["id": .string("name"), "kind": .string("string"), "scope": .string("synced")])
        try AnyNativePersonalNavigationStore.validateLastOpenedDefinition(
            .object(["properties": .array([other, original])]))
        var invalidRows: [[AnyJSON]] = [[], [other], [original, original], [other, other, original],
                                      [.object(["kind": .string("string")]), original]]
        for (key, replacement) in [
            ("kind", AnyJSON.string("string")), ("scope", .string("synced")),
            ("scope", .string("derived")), ("xFormat", .null),
            ("xFormat", .object(["type": .string("datetime"), "contract": .string("foreign"), "precision": .string("seconds")])),
            ("xFormat", .object(["type": .string("text"), "contract": .string("pinkha-last-opened-local-v1"), "precision": .string("seconds")])),
            ("xFormat", .object(["type": .string("datetime"), "contract": .string("pinkha-last-opened-local-v1"), "precision": .string("milliseconds")]))
        ] {
            var fields = try XCTUnwrap(original.object)
            fields[key] = replacement
            invalidRows.append([.object(fields)])
        }
        for key in ["id", "kind", "scope", "xFormat"] {
            var fields = try XCTUnwrap(original.object)
            fields.removeValue(forKey: key)
            invalidRows.append([.object(fields)])
        }
        for rows in invalidRows {
            XCTAssertThrowsError(try AnyNativePersonalNavigationStore.validateLastOpenedDefinition(
                .object(["properties": .array(rows)]))) {
                XCTAssertEqual($0 as? AnyNativePersonalNavigationError, .unavailableContract)
            }
        }
        XCTAssertThrowsError(try AnyNativePersonalNavigationStore.validateLastOpenedDefinition(.object([:])))
        // Other declaration IDs are byte identities, not canonical Unicode keys.
        try AnyNativePersonalNavigationStore.validateLastOpenedDefinition(.object(["properties": .array([
            .object(["id": .string("id-\u{00e9}")]), .object(["id": .string("id-e\u{0301}")]), original
        ])]))
    }

    func testLocalAcknowledgmentRequiresOneExactTargetAndNoSharedOrPartialEffect() throws {
        let target = "native-\u{00e9}"
        let original: [String: AnyJSON] = [
            "versionId": .string("current-native-version"), "changeId": .string(""),
            "recordIds": .array([.string(target)])
        ]
        try AnyNativePersonalNavigationStore.requireLocalModifyResult(.object(original), expectedObjectID: target)
        var explicitEmpty = original
        explicitEmpty["rejections"] = .array([])
        try AnyNativePersonalNavigationStore.requireLocalModifyResult(.object(explicitEmpty), expectedObjectID: target)
        var invalid: [[String: AnyJSON]] = []
        for (key, replacement) in [
            ("versionId", AnyJSON.string("")), ("versionId", .null),
            ("changeId", .string("signed-shared-change")), ("changeId", .null),
            ("recordIds", .array([])), ("recordIds", .array([.string("")])),
            ("recordIds", .array([.string("foreign")])),
            ("recordIds", .array([.string("native-e\u{0301}")])),
            ("recordIds", .array([.string(target), .string(target)])),
            ("recordIds", .null), ("rejections", .null),
            ("rejections", .array([.object(["recordId": .string(target), "reason": .string("partial refusal")])]))
        ] {
            var fields = original
            fields[key] = replacement
            invalid.append(fields)
        }
        for key in ["versionId", "changeId", "recordIds"] {
            var fields = original
            fields.removeValue(forKey: key)
            invalid.append(fields)
        }
        for fields in invalid {
            XCTAssertThrowsError(try AnyNativePersonalNavigationStore.requireLocalModifyResult(
                .object(fields), expectedObjectID: target)) {
                XCTAssertEqual($0 as? AnyEngineError, .writeUncertain)
            }
        }
    }

    func testForeignWorkspaceBindingAndLeaseFailBeforeAnyIO() async throws {
        let account = "owner-\u{00e9}"
        let alias = "owner-e\u{0301}"
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: "space-\u{00e9}")
        let binding = try AnyNativeAccountRunBinding(accountID: account, networkID: "network",
            runID: String(repeating: "a", count: 64))
        let endpoint = try XCTUnwrap(URL(string: "http://127.0.0.1:9"))
        let client = try AnyHTTPClient(baseURL: endpoint, expectedAccountID: account)
        let wrongClient = try AnyHTTPClient(baseURL: endpoint, expectedAccountID: alias)
        XCTAssertThrowsError(try AnyNativePersonalNavigationStore(
            client: wrongClient, workspace: workspace, binding: binding)) {
            XCTAssertEqual($0 as? AnyHostError, .wrongWorkspace)
        }
        let wrongBinding = try AnyNativeAccountRunBinding(accountID: alias, networkID: "network",
            runID: String(repeating: "a", count: 64))
        XCTAssertThrowsError(try AnyNativePersonalNavigationStore(
            client: client, workspace: workspace, binding: wrongBinding)) {
            XCTAssertEqual($0 as? AnyHostError, .wrongWorkspace)
        }
        let store = try AnyNativePersonalNavigationStore(client: client, workspace: workspace, binding: binding)
        let probe = PersonalNavigationContractLeaseProbe()
        let foreignWorkspaces = [
            try AnyTorahWorkspace(accountID: "other", spaceID: workspace.spaceID),
            try AnyTorahWorkspace(accountID: account, spaceID: "other"),
            try AnyTorahWorkspace(accountID: alias, spaceID: workspace.spaceID),
            try AnyTorahWorkspace(accountID: account, spaceID: "space-e\u{0301}")
        ]
        for foreign in foreignWorkspaces {
            let lease = AnyHostLease(workspace: foreign, generation: UUID(),
                engineStartedAt: "synthetic-original-run", check: {
                    await probe.record()
                    throw PersonalNavigationContractProbeError.unexpectedLeaseEvaluation
                })
            do { _ = try await store.readHome(lease: lease); XCTFail("foreign home read reached I/O") }
            catch let error as AnyHostError { XCTAssertEqual(error, .wrongWorkspace) }
            do { _ = try await store.prepareHome(.builtIn(.graph), lease: lease); XCTFail("foreign home preparation reached I/O") }
            catch let error as AnyHostError { XCTAssertEqual(error, .wrongWorkspace) }
            do { _ = try await store.readLastOpened(objectID: "object", lease: lease); XCTFail("foreign local read reached I/O") }
            catch let error as AnyHostError { XCTAssertEqual(error, .wrongWorkspace) }
            do { _ = try await store.prepareActualOpen(objectID: "object",
                observedAt: Date(timeIntervalSince1970: 1_760_000_123), lease: lease)
                XCTFail("foreign local preparation reached I/O")
            } catch let error as AnyHostError { XCTAssertEqual(error, .wrongWorkspace) }
        }
        let evaluations = await probe.count()
        XCTAssertEqual(evaluations, 0, "workspace refusal precedes the lease callback and all HTTP")
    }

    private func canonical(_ value: AnyJSON) throws -> Data {
        try AnyHostCanonical.bytes(value, maximumBytes: 65_536)
    }

    // Native wire/evidence payloads are JSON. Canonical typed bytes above are
    // used only for exact value comparisons and must never reach a JSON parser.
    private func jsonBytes(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let bytes = try encoder.encode(value)
        guard bytes.count <= 65_536 else { throw AnyEngineError.readLimit }
        return bytes
    }

    private func homeWire(_ fields: [String: AnyJSON]) throws -> AnyJSON {
        .string(String(decoding: try jsonBytes(.object(fields)), as: UTF8.self))
    }

    private func changedDescriptorBinding(_ evidence: AnyDestinationDefinitionEvidence,
                                           key: String, value: AnyJSON) throws -> AnyHeartLastOpenedBinding {
        var outer = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: evidence.jsonViewBytes).object)
        var snapshot = try XCTUnwrap(outer["Snapshot"]?.object)
        var details = try XCTUnwrap(snapshot["details"]?.object)
        details[key] = value
        snapshot["details"] = .object(details)
        outer["Snapshot"] = .object(snapshot)
        return try .init(evidence: .init(sourceSpaceID: evidence.sourceSpaceID,
            sourceObjectID: evidence.sourceObjectID, protobufBytes: evidence.protobufBytes,
            jsonViewBytes: jsonBytes(.object(outer))))
    }

    private static let lastOpenedDefinition: AnyJSON = .object([
        "id": .string("pinkhaLastOpenedV1"), "name": .string("Last opened"),
        "kind": .string("datetime"), "scope": .string("local"),
        "xFormat": .object(["type": .string("datetime"),
            "contract": .string("pinkha-last-opened-local-v1"), "precision": .string("seconds")])
    ])

    // Exact captured details, including the original typo, false/null and arrays.
    private static let originalLastOpenedDescriptor: AnyJSON = .object([
        "apiObjectKey": .string("last_opened_date"),
        "description": .string("Date when the object was modified last opened"),
        "internalFlags": .array([]), "isHidden": .bool(false), "layout": .integer(5),
        "name": .string("Last opened date"), "origin": .integer(7),
        "relationDefaultValue": .null, "relationFormat": .integer(4),
        "relationFormatIncludeTime": .bool(true), "relationFormatObjectTypes": .array([]),
        "relationKey": .string("lastOpenedDate"), "relationMaxCount": .integer(1),
        "relationReadonlyValue": .bool(true), "revision": .integer(1),
        "sourceObject": .string("_brlastOpenedDate")
    ])
}

private enum PersonalNavigationContractProbeError: Error {
    case unexpectedLeaseEvaluation
}

private actor PersonalNavigationContractLeaseProbe {
    private var evaluations = 0
    func record() { evaluations += 1 }
    func count() -> Int { evaluations }
}
