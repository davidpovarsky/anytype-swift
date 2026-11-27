import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativeComputedRelationBindingTests: XCTestCase {
    func testComputedRelationsRetainSourceIdentityAndNeverBecomeWritableProperties() throws {
        for role in AnyHeartNativeComputedRelationBinding.Role.allCases {
            let evidence = try evidence(role: role)
            let binding = try AnyHeartNativeComputedRelationBinding(evidence: evidence)
            XCTAssertEqual(binding.role, role)
            XCTAssertEqual(binding.evidence, evidence)
            XCTAssertEqual(binding.sourceRelationKey, role.rawValue)
            XCTAssertEqual(binding.readContract, AnyHeartNativeComputedRelationBinding.contract)
            XCTAssertFalse(binding.permitsDestinationWrites)
            XCTAssertEqual(binding.sourceHidden, false)
            XCTAssertEqual(binding.visibilityKey,
                "derived:v1:pinkha-heart-native-link-index-relation-v1:" + role.rawValue)
            XCTAssertEqual(try JSONDecoder().decode(AnyHeartNativeComputedRelationBinding.self,
                from: JSONEncoder().encode(binding)), binding)
        }
    }

    func testComputedRelationsRejectChangedSourceSemantics() throws {
        let mutations: [(String, AnyJSON)] = [
            ("relationFormat", .integer(11)), ("relationMaxCount", .integer(1)),
            ("relationReadonlyValue", .bool(false)), ("relationDefaultValue", .array([])),
            ("relationFormatIncludeTime", .bool(true)),
            ("relationFormatObjectTypes", .array([.string("other-type")])),
            ("name", .string("Renamed")), ("description", .string("Changed meaning")),
            ("isArchived", .bool(true)), ("isReadonly", .bool(true)),
            ("isHidden", .string("false")), ("internalFlags", .array([.integer(1)])),
            ("unknownFutureSemantic", .bool(true)), ("relationKey", .string("custom_links"))
        ]
        for role in AnyHeartNativeComputedRelationBinding.Role.allCases {
            for (key, value) in mutations {
                XCTAssertThrowsError(try AnyHeartNativeComputedRelationBinding(
                    evidence: evidence(role: role, mutations: [key: value])), "\(role):\(key)")
            }
            XCTAssertThrowsError(try AnyHeartNativeComputedRelationBinding(
                evidence: evidence(role: role, uniqueKey: "rel-custom")))
            XCTAssertThrowsError(try AnyHeartNativeComputedRelationBinding(
                evidence: evidence(role: role, nativeType: 528)))
        }
    }

    func testDecodingRevalidatesRoleAndReadContract() throws {
        let binding = try AnyHeartNativeComputedRelationBinding(evidence: evidence(role: .outgoingLinks))
        let original = try JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(binding))
        for (key, value) in [("role", AnyJSON.string("backlinks")), ("readContract", .string("unqualified-v2"))] {
            var fields = try XCTUnwrap(original.object)
            fields[key] = value
            XCTAssertThrowsError(try JSONDecoder().decode(AnyHeartNativeComputedRelationBinding.self,
                from: JSONEncoder().encode(AnyJSON.object(fields))))
        }
    }

    func testExactOriginal156LinkDefinitionsUseTheReadContract() throws {
        guard let directory = ProcessInfo.processInfo.environment["PINKHA_NATIVE_ORIGINAL156"] else {
            throw XCTSkip("Requires the retained original156 native JSON and protobuf source bundle.")
        }
        let root = URL(fileURLWithPath: directory, isDirectory: true).appendingPathComponent("bundle")
        let files = [
            ("snapshot-499c3540377351bb70bd1c7cd9eaaafc40acc45dffb31820ed89110e0e592fb4", AnyHeartNativeComputedRelationBinding.Role.outgoingLinks),
            ("snapshot-c9c4bed807a227f8ecfe6d68093e99c89b48814361c328f59b5533513e082b86", .backlinks)
        ]
        for (stem, role) in files {
            let jsonURL = root.appendingPathComponent(stem + ".json")
            let pbURL = root.appendingPathComponent(stem + ".pb")
            let jsonBytes = try Data(contentsOf: jsonURL), pbBytes = try Data(contentsOf: pbURL)
            let raw = try JSONDecoder().decode(AnyJSON.self, from: jsonBytes)
            let space = try XCTUnwrap(raw["SpaceID"]?.string), object = try XCTUnwrap(raw["ObjectID"]?.string)
            let view = try AnyHeartNativeSnapshotView(jsonView: jsonBytes, snapshotBytes: pbBytes,
                sourceSpaceID: space, sourceObjectID: object)
            let binding = try AnyHeartNativeComputedRelationBinding(evidence: .init(snapshot: view))
            XCTAssertEqual(binding.role, role)
            XCTAssertEqual(binding.evidence.protobufBytes, pbBytes)
            XCTAssertEqual(binding.evidence.jsonViewBytes, jsonBytes)
            XCTAssertFalse(binding.permitsDestinationWrites)
            XCTAssertEqual(try Data(contentsOf: jsonURL), jsonBytes)
            XCTAssertEqual(try Data(contentsOf: pbURL), pbBytes)
        }
    }

    private func evidence(role: AnyHeartNativeComputedRelationBinding.Role,
                          mutations: [String: AnyJSON] = [:], uniqueKey: String? = nil,
                          nativeType: Int64 = 521) throws -> AnyDestinationDefinitionEvidence {
        let id = "explicit-computed-" + role.rawValue
        var details: [String: AnyJSON] = [
            "name": .string(role == .outgoingLinks ? "Links" : "Backlinks"),
            "description": .string(role == .outgoingLinks ? "Outgoing links" : "List of links coming to object"),
            "relationKey": .string(role.rawValue), "relationFormat": .integer(100),
            "relationMaxCount": .integer(0), "relationReadonlyValue": .bool(true),
            "relationDefaultValue": .null, "relationFormatIncludeTime": .bool(false),
            "relationFormatObjectTypes": .array([]), "isHidden": .bool(false),
            "internalFlags": .array([]), "layout": .integer(5), "revision": .integer(3)
        ]
        for (key, value) in mutations { details[key] = value }
        let marker = Data(("explicit-computed-contract-input-not-captured-native-authority:" + id).utf8)
        let raw: AnyJSON = .object([
            "Contract": .string("pinkha-native-snapshot-json-v1"), "SpaceID": .string("component-space"),
            "ObjectID": .string(id), "NativeType": .integer(nativeType),
            "UniqueKey": .string(uniqueKey ?? "rel-" + role.rawValue),
            "SnapshotSHA256": .string(AnyContentDigest.sha256(marker)), "SnapshotBytes": .integer(Int64(marker.count)),
            "Snapshot": .object(["blocks": .array([]), "details": .object(details),
                "objectTypes": .array([]), "relationLinks": .array([])])
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try .init(snapshot: .init(jsonView: encoder.encode(raw), snapshotBytes: marker,
            sourceSpaceID: "component-space", sourceObjectID: id))
    }
}
