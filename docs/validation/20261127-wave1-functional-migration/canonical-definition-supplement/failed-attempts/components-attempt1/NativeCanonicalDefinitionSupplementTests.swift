import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// These methods resolve exact captured definitions outside the original
/// content selection. They do not create objects or authorize source replay.
final class NativeCanonicalDefinitionSupplementTests: XCTestCase {
    func testEightOriginalCanonicalDefinitionsRetainEvidenceAndDistinctValueSemantics() throws {
        let fixture = try NativeCanonicalSupplementFixture.load()
        let extra = try fixture.bindings()
        let directory = try AnyNativeImportedDefinitionDirectory(plan: fixture.plan, mappings: fixture.mappings,
            supplementalCanonicalDefinitions: extra)
        XCTAssertEqual(directory.entries.count, 21)
        XCTAssertEqual(directory.unresolvedSourceDefinitionIDs.count, 129)
        XCTAssertEqual(directory.supplementalCanonicalDefinitions, extra)
        XCTAssertFalse(directory.permitsSourceAdmission)
        for canonical in extra {
            let entry = try XCTUnwrap(directory.definition(sourceObjectID: canonical.evidence.sourceObjectID))
            XCTAssertEqual(entry.address, .property(ownerKind: .type,
                key: try .init(ownerID: "any", propertyID: canonical.propertyID)))
            XCTAssertEqual(entry.sourceSnapshotSHA256, canonical.evidence.snapshotSHA256)
            XCTAssertEqual(entry.sourceJSONViewSHA256, canonical.evidence.viewSHA256)
            XCTAssertEqual(entry.sourceUniqueKey, "rel-" + canonical.sourceRelationKey)
            XCTAssertEqual(entry.originalDescriptor, try canonical.expectedNativeDescriptor)
            XCTAssertEqual(entry.canonicalValueSemantics, NativeCanonicalSupplementFixture.meaning(canonical.propertyID))
            XCTAssertNil(entry.intent)
            XCTAssertNil(entry.mapping)
            XCTAssertFalse(entry.permitsDestinationWrites)
            XCTAssertNotEqual(Data(entry.sourceObjectID.utf8), Data(canonical.propertyID.utf8))
        }
        XCTAssertEqual(Set(extra.filter { $0.derivedRole != nil }.map(\.propertyID)),
            Set(["author", "createdAt", "modifiedAt", "modifiedBy"]))
        XCTAssertEqual(Set(extra.filter { $0.identityRole != nil }.map(\.propertyID)), Set(["id", "spaceId", "type"]))
        try fixture.requireRetainedInputsUnchanged()
    }

    func testSupplementRefusesDuplicateExistingAndCallerChosenAliases() throws {
        let fixture = try NativeCanonicalSupplementFixture.load()
        let first = try fixture.binding("description")
        XCTAssertThrowsError(try AnyNativeImportedDefinitionDirectory(plan: fixture.plan, mappings: fixture.mappings,
            supplementalCanonicalDefinitions: [first, first]))
        XCTAssertThrowsError(try AnyNativeImportedDefinitionDirectory(plan: fixture.plan, mappings: fixture.mappings,
            supplementalCanonicalDefinitions: [try fixture.binding("name")]))
        XCTAssertThrowsError(try AnyNativeImportedDefinitionDirectory(plan: fixture.plan, mappings: fixture.mappings,
            supplementalCanonicalDefinitions: Array(repeating: first, count: 10)))
        let raw = try JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(first))
        for (key, value) in [("ownerID", "caller-owned-type"), ("propertyID", "name"),
                             ("nativeContract", "caller-chosen-alias")] {
            var fields = try XCTUnwrap(raw.object)
            fields[key] = .string(value)
            XCTAssertThrowsError(try JSONDecoder().decode(AnyDestinationCanonicalPropertyBinding.self,
                from: AnyDestinationDefinitionChecks.bytes(.object(fields))), key)
        }
        try fixture.requireRetainedInputsUnchanged()
    }

    func testSupplementRefusesSelfConsistentChangedWireAndForeignSourceSpace() throws {
        let fixture = try NativeCanonicalSupplementFixture.load()
        let original = try fixture.binding("description")
        var raw = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: original.evidence.jsonViewBytes).object)
        var changedWire = original.evidence.protobufBytes
        changedWire.append(0)
        raw["SnapshotSHA256"] = .string(AnyContentDigest.sha256(changedWire))
        raw["SnapshotBytes"] = .integer(Int64(changedWire.count))
        let changedEvidence = try AnyDestinationDefinitionEvidence(sourceSpaceID: original.evidence.sourceSpaceID,
            sourceObjectID: original.evidence.sourceObjectID, protobufBytes: changedWire,
            jsonViewBytes: AnyDestinationDefinitionChecks.bytes(.object(raw)))
        let changed = try AnyDestinationCanonicalPropertyBinding(evidence: changedEvidence)
        XCTAssertThrowsError(try AnyNativeImportedDefinitionDirectory(plan: fixture.plan, mappings: fixture.mappings,
            supplementalCanonicalDefinitions: [changed]))
        raw = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: original.evidence.jsonViewBytes).object)
        let foreignSpace = original.evidence.sourceSpaceID + "-foreign"
        raw["SpaceID"] = .string(foreignSpace)
        let foreign = try AnyDestinationCanonicalPropertyBinding(evidence: .init(sourceSpaceID: foreignSpace,
            sourceObjectID: original.evidence.sourceObjectID, protobufBytes: original.evidence.protobufBytes,
            jsonViewBytes: AnyDestinationDefinitionChecks.bytes(.object(raw))))
        XCTAssertThrowsError(try AnyNativeImportedDefinitionDirectory(plan: fixture.plan, mappings: fixture.mappings,
            supplementalCanonicalDefinitions: [foreign]))
        XCTAssertThrowsError(try AnyDestinationCanonicalPropertyBinding(evidence: fixture.evidence("rel-creator"),
            targetTypeEvidence: fixture.evidence("ot-space")))
        try fixture.requireRetainedInputsUnchanged()
    }
}

struct NativeCanonicalSupplementFixture: Sendable {
    static let sourceKeys = ["description", "id", "spaceId", "type", "creator", "createdDate", "lastModifiedDate", "lastModifiedBy"]
    let plan: AnyDestinationMigrationPlan
    let mappings: [AnyDestinationMigrationMapping]
    let bundle: URL
    let manifest: AnyJSON
    let planURL: URL
    let mappingsURL: URL

    static func load() throws -> Self {
        let env = ProcessInfo.processInfo.environment
        guard let retainedPath = env["PINKHA_NATIVE_DEFINITION_RETAINED"],
              let originalPath = env["PINKHA_NATIVE_ORIGINAL156"] else {
            throw XCTSkip("Requires exact retained original156 source and accepted destination mappings.")
        }
        let retained = URL(fileURLWithPath: retainedPath, isDirectory: true)
        let planURL = retained.appendingPathComponent("source-preservation-plan.json")
        let mappingsURL = retained.appendingPathComponent("execute-mappings.json")
        let bundle = URL(fileURLWithPath: originalPath, isDirectory: true).appendingPathComponent("bundle")
        let bytes = try Data(contentsOf: bundle.appendingPathComponent("manifest.json"))
        guard AnyContentDigest.sha256(bytes) == "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4" else {
            throw NativeCanonicalSupplementFailure.identity
        }
        let value = Self(plan: try AnyDestinationMigrationPlan.decode(Data(contentsOf: planURL)),
            mappings: try JSONDecoder().decode([AnyDestinationMigrationMapping].self, from: Data(contentsOf: mappingsURL)),
            bundle: bundle, manifest: try JSONDecoder().decode(AnyJSON.self, from: bytes),
            planURL: planURL, mappingsURL: mappingsURL)
        try value.requireRetainedInputsUnchanged()
        return value
    }

    func requireRetainedInputsUnchanged() throws {
        guard AnyContentDigest.sha256(try Data(contentsOf: planURL)) == "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930",
              AnyContentDigest.sha256(try Data(contentsOf: mappingsURL)) == "eabdf2e362189abd5a2e78f7c13f1f1d77d8339c27109d2a6ec19ccdbb2755a3",
              AnyContentDigest.sha256(try Data(contentsOf: bundle.appendingPathComponent("manifest.json"))) == "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4" else {
            throw NativeCanonicalSupplementFailure.identity
        }
    }

    func bindings() throws -> [AnyDestinationCanonicalPropertyBinding] {
        try Self.sourceKeys.map(binding)
    }

    func binding(_ key: String) throws -> AnyDestinationCanonicalPropertyBinding {
        let target: String?
        switch key {
        case "spaceId": target = "ot-space"
        case "type": target = "ot-objectType"
        case "creator", "lastModifiedBy": target = "ot-participant"
        default: target = nil
        }
        return try .init(evidence: evidence("rel-" + key), targetTypeEvidence: target.map(evidence))
    }

    func evidence(_ uniqueKey: String) throws -> AnyDestinationDefinitionEvidence {
        let rows = try XCTUnwrap(manifest["Objects"]?.array).filter { $0["UniqueKey"] == .string(uniqueKey) }
        guard rows.count == 1, let id = rows[0]["ObjectID"]?.string else {
            throw NativeCanonicalSupplementFailure.identity
        }
        let stem = "snapshot-" + AnyContentDigest.sha256(Data(id.utf8))
        guard rows[0]["Snapshot"]?["Path"] == .string(stem + ".pb"),
              rows[0]["NativeJSONView"]?["Path"] == .string(stem + ".json") else {
            throw NativeCanonicalSupplementFailure.identity
        }
        let pb = try Data(contentsOf: bundle.appendingPathComponent(stem + ".pb"))
        let json = try Data(contentsOf: bundle.appendingPathComponent(stem + ".json"))
        let evidence = try AnyDestinationDefinitionEvidence(sourceSpaceID: plan.source.spaceID,
            sourceObjectID: id, protobufBytes: pb, jsonViewBytes: json)
        try evidence.requireSource(plan.source, objectID: id)
        return evidence
    }

    static func meaning(_ propertyID: String) -> AnyNativeCanonicalValueSemantics {
        switch propertyID {
        case "id", "spaceId", "type": .translatedIdentity
        case "author", "createdAt", "modifiedAt", "modifiedBy": .destinationDerived
        default: .ordinaryProperty
        }
    }
}

enum NativeCanonicalSupplementFailure: Error { case identity, assertion }
