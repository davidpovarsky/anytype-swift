import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativeImportedSourceFactsTests: XCTestCase {
    func testTwoRetainedSourceFactsKeepCompleteOriginalBytesAndStructure() throws {
        let fixture = try NativeCanonicalSupplementFixture.load()
        let directory = try AnyNativeImportedSourceFactsDirectory(plan: fixture.plan, mappings: fixture.mappings)
        XCTAssertEqual(directory.entries.count, 2)
        XCTAssertFalse(directory.permitsSourceAdmission)
        for entry in directory.entries {
            let value = try AnyNativeImportedSourceFactsValue(values: entry.values, source: directory.source,
                sourceObjectID: entry.sourceObjectID)
            let stem = "snapshot-" + AnyContentDigest.sha256(Data(entry.sourceObjectID.utf8))
            let originalPB = try Data(contentsOf: fixture.bundle.appendingPathComponent(stem + ".pb"))
            let originalJSON = try Data(contentsOf: fixture.bundle.appendingPathComponent(stem + ".json"))
            XCTAssertEqual(value.snapshot.protobufBytes, originalPB)
            XCTAssertEqual(value.snapshot.jsonViewBytes, originalJSON)
            XCTAssertEqual(value.snapshot.snapshotSHA256, entry.sourceSnapshotSHA256)
            XCTAssertEqual(value.snapshot.viewSHA256, entry.sourceJSONViewSHA256)
            XCTAssertEqual(value.snapshot.sourceObjectID, entry.sourceObjectID)
            XCTAssertFalse(value.originalHistoryReconstructed)
            XCTAssertFalse(entry.permitsDestinationWrites)
            let captured = try JSONDecoder().decode(AnyJSON.self, from: originalJSON)
            XCTAssertEqual(.array(value.snapshot.blocks.map(\.raw)), captured["Snapshot"]?["blocks"])
            XCTAssertEqual(.object(value.snapshot.details), captured["Snapshot"]?["details"])
            XCTAssertEqual(.array(value.snapshot.objectTypes.map(AnyJSON.string)), captured["Snapshot"]?["objectTypes"])
            XCTAssertEqual(.array(value.snapshot.relationLinks), captured["Snapshot"]?["relationLinks"])
            XCTAssertEqual(value.snapshot.depthFirstIDs.first, entry.sourceObjectID)
            XCTAssertNil(directory.entry(sourceObjectID: entry.sourceObjectID + "-foreign"))
        }
        try fixture.requireRetainedInputsUnchanged()
    }

    func testHistoricalBindingsRequireCompleteOriginalDerivedValues() throws {
        let fixture = try SyntheticSourceFacts.make()
        let accepted = try AnyNativeImportedSourceFactsValue(values: fixture.values, source: fixture.source,
            sourceObjectID: fixture.objectID)
        XCTAssertEqual(accepted.historicalValues.count, 4)
        XCTAssertEqual(accepted.snapshot.depthFirstIDs, [fixture.objectID, "original-child"])
        XCTAssertEqual(accepted.snapshot.blocks[1].parentID, fixture.objectID)
        XCTAssertEqual(accepted.snapshot.rawSnapshot["futureEnvelope"], .array([.null, .number(1.25), .string("מקור")]))
        XCTAssertEqual(accepted.snapshot.blocks[1].raw["futureBlock"], .object(["preserved": .bool(true)]))
        XCTAssertFalse(accepted.originalHistoryReconstructed)
        let binding = try JSONDecoder().decode(AnyJSON.self,
            from: Data(XCTUnwrap(fixture.values["sourceDerivedBindingsJSON"]?.string).utf8))
        let rows = try XCTUnwrap(binding["historicalValues"]?.array)
        XCTAssertEqual(rows.count, 4)
        for index in rows.indices {
            var changed = try XCTUnwrap(binding.object)
            changed["historicalValues"] = .array(rows.enumerated().filter { $0.offset != index }.map(\.element))
            XCTAssertThrowsError(try fixture.decode(binding: .object(changed))) { error in
                XCTAssertEqual(error as? AnyNativeImportedSourceFactsError, .invalidSource(fixture.objectID))
            }
        }
        var duplicate = try XCTUnwrap(binding.object)
        duplicate["historicalValues"] = .array([rows[0], rows[0], rows[2], rows[3]])
        XCTAssertThrowsError(try fixture.decode(binding: .object(duplicate)))
        var incorrect = try XCTUnwrap(rows[0].object)
        incorrect["originalValue"] = .string("destination-author")
        var altered = try XCTUnwrap(binding.object)
        altered["historicalValues"] = .array([.object(incorrect)] + Array(rows.dropFirst()))
        XCTAssertThrowsError(try fixture.decode(binding: .object(altered)))
        altered = try XCTUnwrap(binding.object)
        altered["historicalAuthorIsDestinationSigner"] = .bool(true)
        XCTAssertThrowsError(try fixture.decode(binding: .object(altered)))
    }

    func testSourceFactsRefuseChangedEvidenceAndInvalidMappings() throws {
        let fixture = try SyntheticSourceFacts.make()
        var changed = fixture.values
        changed["sourceObject"] = .string(fixture.objectID + "-foreign")
        XCTAssertThrowsError(try AnyNativeImportedSourceFactsValue(values: changed,
            source: fixture.source, sourceObjectID: fixture.objectID))
        changed = fixture.values
        changed["sourceSnapshotBase64"] = .string(Data("self-consistent foreign wire".utf8).base64EncodedString())
        changed["sourceSnapshotSHA256"] = .string(AnyContentDigest.sha256(Data("self-consistent foreign wire".utf8)))
        var view = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self,
            from: Data(XCTUnwrap(changed["sourceViewJSON"]?.string).utf8)).object)
        view["SnapshotSHA256"] = changed["sourceSnapshotSHA256"]
        view["SnapshotBytes"] = .integer(Int64(Data("self-consistent foreign wire".utf8).count))
        let viewBytes = try AnyDestinationDefinitionChecks.bytes(.object(view))
        changed["sourceViewJSON"] = .string(String(decoding: viewBytes, as: UTF8.self))
        changed["sourceViewSHA256"] = .string(AnyContentDigest.sha256(viewBytes))
        XCTAssertThrowsError(try AnyNativeImportedSourceFactsValue(values: changed,
            source: fixture.source, sourceObjectID: fixture.objectID))
        changed = fixture.values; changed["importedBy"] = .string("caller-forged-native-stamp")
        XCTAssertThrowsError(try AnyNativeImportedSourceFactsValue(values: changed,
            source: fixture.source, sourceObjectID: fixture.objectID))

        let retained = try NativeCanonicalSupplementFixture.load()
        let directory = try AnyNativeImportedSourceFactsDirectory(plan: retained.plan, mappings: retained.mappings)
        let sourceKey = try XCTUnwrap(directory.entries.first?.sourceKey)
        var rows = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(retained.mappings)).array)
        let index = try XCTUnwrap(rows.firstIndex { $0["sourceKey"] == .string(sourceKey) })
        var row = try XCTUnwrap(rows[index].object)
        row["signedChangeIDs"] = .array([.string("two-distinct-signed-changes"), .string("must-not-be-source-fact-creation")])
        rows[index] = .object(row)
        let invalid = try JSONDecoder().decode([AnyDestinationMigrationMapping].self,
            from: AnyDestinationDefinitionChecks.bytes(.array(rows)))
        XCTAssertThrowsError(try AnyNativeImportedSourceFactsDirectory(plan: retained.plan, mappings: invalid)) { error in
            XCTAssertEqual(error as? AnyNativeImportedSourceFactsError, .invalidMappings)
        }
        try retained.requireRetainedInputsUnchanged()
    }
}

/// A synthetic envelope exercises parsing/refusal only; it is never admitted
/// as a native source capture, destination operation or signed history proof.
private struct SyntheticSourceFacts {
    let objectID: String
    let source: AnyDestinationSourceBinding
    let values: [String: AnyJSON]

    func decode(binding: AnyJSON) throws -> AnyNativeImportedSourceFactsValue {
        var changed = values
        changed["sourceDerivedBindingsJSON"] = .string(String(decoding:
            try AnyDestinationDefinitionChecks.bytes(binding), as: UTF8.self))
        return try .init(values: changed, source: source, sourceObjectID: objectID)
    }

    static func make() throws -> Self {
        let objectID = "source-document", space = "source-space", account = "source-account"
        let protobuf = Data("synthetic-source-facts-wire-control".utf8)
        let witness = String(repeating: "b", count: 64)
        let details: [String: AnyJSON] = ["creator": .array([.string("original-actor-א")]),
            "createdDate": .integer(-7), "lastModifiedDate": .integer(Int64.max),
            "lastModifiedBy": .array([]), "futureMetadata": .object(["exact": .integer(9_007_199_254_740_993)])]
        let view: AnyJSON = .object([
            "Contract": .string("pinkha-native-snapshot-json-v1"), "SpaceID": .string(space),
            "ObjectID": .string(objectID), "NativeType": .integer(16), "UniqueKey": .string("page"),
            "SnapshotSHA256": .string(AnyContentDigest.sha256(protobuf)), "SnapshotBytes": .integer(Int64(protobuf.count)),
            "Snapshot": .object(["details": .object(details), "objectTypes": .array([.string("original-type")]),
                "relationLinks": .array([]), "futureEnvelope": .array([.null, .number(1.25), .string("מקור")]),
                "blocks": .array([
                    .object(["id": .string(objectID), "childrenIds": .array([.string("original-child")]), "smartblock": .object([:])]),
                    .object(["id": .string("original-child"), "childrenIds": .array([]),
                        "text": .object(["text": .string("טקסט a\u{301} 😀"), "style": .integer(0)]),
                        "futureBlock": .object(["preserved": .bool(true)])])])])])
        let viewBytes = try AnyDestinationDefinitionChecks.bytes(view)
        let snapshot = try AnyHeartNativeSnapshotView(jsonView: viewBytes, snapshotBytes: protobuf,
            sourceSpaceID: space, sourceObjectID: objectID)
        let stem = "snapshot-" + AnyContentDigest.sha256(Data(objectID.utf8))
        let accountSHA = AnyContentDigest.sha256(Data(account.utf8)), spaceSHA = AnyContentDigest.sha256(Data(space.utf8))
        let manifest = try AnyDestinationDefinitionChecks.bytes(.object([
            "Contract": .string("pinkha-native-whole-source-bundle-v1"),
            "Objects": .array([.object(["ObjectID": .string(objectID), "UniqueKey": .string("page"), "NativeType": .integer(16),
                "Snapshot": .object(["Path": .string(stem + ".pb"), "SHA256": .string(snapshot.snapshotSHA256), "Bytes": .integer(Int64(protobuf.count))]),
                "NativeJSONView": .object(["Path": .string(stem + ".json"), "SHA256": .string(snapshot.viewSHA256), "Bytes": .integer(Int64(viewBytes.count))])])]),
            "Receipt": .object(["Version": .string("loaded-account-native-space-source-v1"),
                "AccountSessionAuthorizedAtFinalCapture": .bool(true), "AllNativeHeadRowsAccounted": .bool(true),
                "CapturedSnapshotsBoundToUnchangedCheckpoint": .bool(true),
                "Inventory": .object(["SpaceSHA256": .string(spaceSHA), "SourceWitnessSHA256": .string(witness)]),
                "Source": .object(["accountSHA256": .string(accountSHA), "source": .object([
                    "accountSHA256": .string(accountSHA), "spaceSHA256": .string(spaceSHA),
                    "native": .object(["WitnessSHA256": .string(witness)])])])])]))
        let source = try AnyDestinationSourceBinding(accountID: account, spaceID: space, witnessSHA256: witness,
            captureManifestSHA256: AnyContentDigest.sha256(manifest), semanticPlanSHA256: String(repeating: "c", count: 64),
            sourceObjectIDs: [objectID], definitionManifestBytes: manifest)
        let roles: [AnyDestinationCanonicalPropertyBinding.DerivedRole] = [.author, .createdAt, .modifiedAt, .modifiedBy]
        let bindings = roles.map { role in AnyJSON.object(["sourceRelationKey": .string(role.sourceKey),
            "nativePropertyID": .string(role.rawValue), "originalValue": details[role.sourceKey]!]) }
        let bindingBytes = try AnyDestinationDefinitionChecks.bytes(.object([
            "contract": .string(AnyHeartNativeSourceFacts.contract), "historicalValues": .array(bindings),
            "historicalAuthorIsDestinationSigner": .bool(false)]))
        return .init(objectID: objectID, source: source, values: ["sourceObject": .string(objectID),
            "sourceSnapshotBase64": .string(protobuf.base64EncodedString()),
            "sourceViewJSON": .string(String(decoding: viewBytes, as: UTF8.self)),
            "sourceSnapshotSHA256": .string(snapshot.snapshotSHA256), "sourceViewSHA256": .string(snapshot.viewSHA256),
            "sourceDerivedBindingsJSON": .string(String(decoding: bindingBytes, as: UTF8.self))])
    }
}
