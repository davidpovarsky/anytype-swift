import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// The original capture is read without replaying any migration operation.
/// Altered views below are explicitly synthetic parsing controls, not captures.
final class NativeImportedCatalogMetadataTests: XCTestCase {
    func testCompleteOriginalCatalogKeeps159Heads156SnapshotsAndEveryOriginalByte() throws {
        let fixture = try load()
        let directory = try AnyNativeImportedCatalogDirectory(plan: fixture.plan, mappings: fixture.mappings)
        XCTAssertEqual(directory.entries.count, 159)
        XCTAssertEqual(directory.entries.filter { $0.evidence != nil }.count, 156)
        XCTAssertEqual(directory.entries.filter { $0.evidence == nil }.count, 3)
        XCTAssertFalse(directory.permitsWholeSourceAdmission)
        var addresses = Set<Data>()
        for entry in directory.entries {
            XCTAssertFalse(entry.permitsDestinationWrites)
            XCTAssertTrue(addresses.insert(AnyPreparedMigrationPlanBinding.material([
                entry.objectID, entry.dataset, entry.recordID])).inserted)
            XCTAssertEqual(Data(try XCTUnwrap(directory.entry(sourceObjectID: entry.sourceObjectID)?.sourceObjectID).utf8),
                Data(entry.sourceObjectID.utf8))
            XCTAssertNil(directory.entry(sourceObjectID: entry.sourceObjectID + "-foreign"))
            if let evidence = entry.evidence {
                let stem = "snapshot-" + AnyContentDigest.sha256(Data(entry.sourceObjectID.utf8))
                XCTAssertEqual(evidence.protobufBytes, try Data(contentsOf: fixture.bundle.appendingPathComponent(stem + ".pb")))
                XCTAssertEqual(evidence.jsonViewBytes, try Data(contentsOf: fixture.bundle.appendingPathComponent(stem + ".json")))
                try evidence.requireSource(directory.source, objectID: entry.sourceObjectID)
                XCTAssertEqual(entry.nativeTypeText, String(evidence.snapshot.nativeType))
                XCTAssertEqual(Data(entry.sourceUniqueKey.utf8), Data(evidence.snapshot.uniqueKey.utf8))
            } else {
                XCTAssertEqual(entry.values["snapshotPresent"], .bool(false))
                XCTAssertEqual(entry.values["sourceSnapshotBase64"], .string(""))
                XCTAssertEqual(entry.values["sourceViewJSON"], .string(""))
            }
        }
        try fixture.requireRetainedInputsUnchanged()
    }

    func testAllElevenOriginalDefinitionsAndCapturedOccurrencesRemainHistorical() throws {
        let fixture = try load()
        let directory = try AnyNativeImportedCatalogDirectory(plan: fixture.plan, mappings: fixture.mappings)
        let expected: [AnyHeartOriginalMetadataBinding.Role: Int] = [
            .addedDate: 11, .createdInContext: 0, .globalName: 0, .importType: 0,
            .internalFlags: 150, .oldAnytypeID: 0, .origin: 138, .revision: 138,
            .sourceObject: 138, .timestamp: 0, .uniqueKey: 0
        ]
        XCTAssertEqual(expected.count, 11)
        XCTAssertEqual(AnyHeartOriginalMetadataBinding.Role.allCases.count, 11)
        for role in AnyHeartOriginalMetadataBinding.Role.allCases {
            let definition = try fixture.evidence("rel-" + role.rawValue)
            let binding = try AnyHeartOriginalMetadataBinding(evidence: definition)
            try binding.requireSource(directory.source)
            XCTAssertEqual(binding.role, role)
            XCTAssertEqual(binding.readContract, AnyHeartOriginalMetadataBinding.contract)
            XCTAssertFalse(binding.permitsDestinationWrites)
            XCTAssertFalse(binding.provesCurrentSourceValues)
            XCTAssertEqual(try JSONDecoder().decode(AnyHeartOriginalMetadataBinding.self,
                from: JSONEncoder().encode(binding)), binding)
            var present = 0
            for entry in directory.entries {
                guard let captured = entry.evidence?.snapshot else { continue }
                let original = captured.details.first { $0.key.utf8.elementsEqual(role.rawValue.utf8) }?.value
                switch AnyHeartOriginalMetadataSnapshot.project(role, snapshot: captured) {
                case .absent: XCTAssertNil(original)
                case .present(let value):
                    present += 1
                    XCTAssertEqual(try wire(value), try wire(XCTUnwrap(original)))
                }
            }
            XCTAssertEqual(present, expected[role], role.rawValue)
        }
        try fixture.requireRetainedInputsUnchanged()
    }

    func testHistoricalProjectionDistinguishesMissingNullZeroFalseAndEmptyValues() throws {
        let fixture = try load()
        let source = try fixture.evidence("rel-origin")
        for value in [AnyJSON.null, .integer(0), .bool(false), .string(""), .array([]),
                      .string("e\u{301} — שָׁלוֹם"), .object(["unknownOriginalField": .array([.integer(0), .null])])] {
            let changed = try replacing(source, details: ["createdInContext": value])
            guard case .present(let captured) = AnyHeartOriginalMetadataSnapshot.project(.createdInContext,
                snapshot: changed.snapshot) else { return XCTFail("a present source value disappeared") }
            XCTAssertEqual(try wire(captured), try wire(value))
        }
        guard case .absent = AnyHeartOriginalMetadataSnapshot.project(.createdInContext, snapshot: source.snapshot) else {
            return XCTFail("source absence became a default")
        }
        XCTAssertEqual(source.snapshot.details["origin"], .integer(7))
        try fixture.requireRetainedInputsUnchanged()
    }

    func testDefinitionAndDecodedContractOverridesCannotBecomeOriginalBindings() throws {
        let fixture = try load()
        for role in AnyHeartOriginalMetadataBinding.Role.allCases {
            let original = try fixture.evidence("rel-" + role.rawValue)
            for (key, value) in [("relationReadonlyValue", AnyJSON.bool(false)),
                                 ("relationDefaultValue", .integer(0)), ("relationKey", .string("foreign")),
                                 ("name", .string("changed original name")), ("unknownSemanticField", .bool(true))] {
                XCTAssertThrowsError(try AnyHeartOriginalMetadataBinding(evidence: replacing(original, details: [key: value])))
            }
            let binding = try AnyHeartOriginalMetadataBinding(evidence: original)
            let encoded = try JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(binding))
            var changed = try XCTUnwrap(encoded.object)
            changed["readContract"] = .string("unqualified-live-metadata")
            XCTAssertThrowsError(try JSONDecoder().decode(AnyHeartOriginalMetadataBinding.self,
                from: wire(.object(changed))))
            changed = try XCTUnwrap(encoded.object)
            changed["role"] = .string(role == .origin ? "revision" : "origin")
            XCTAssertThrowsError(try JSONDecoder().decode(AnyHeartOriginalMetadataBinding.self,
                from: wire(.object(changed))))
        }
        try fixture.requireRetainedInputsUnchanged()
    }

    func testIncompleteMappingsChangedEvidenceAndFalseAbsenceCannotRouteCatalogData() throws {
        let fixture = try load()
        let directory = try AnyNativeImportedCatalogDirectory(plan: fixture.plan, mappings: fixture.mappings)
        XCTAssertThrowsError(try AnyNativeImportedCatalogDirectory(plan: fixture.plan, mappings: Array(fixture.mappings.dropLast())))
        XCTAssertThrowsError(try AnyNativeImportedCatalogDirectory(plan: fixture.plan, mappings: Array(fixture.mappings.reversed())))
        var duplicate = fixture.mappings
        duplicate[duplicate.count - 1] = duplicate[0]
        XCTAssertThrowsError(try AnyNativeImportedCatalogDirectory(plan: fixture.plan, mappings: duplicate))
        let captured = try XCTUnwrap(directory.entries.first { $0.evidence != nil })
        XCTAssertThrowsError(try AnyNativeImportedCatalogChecks.evidence(captured.values,
            source: directory.source, sourceObjectID: captured.sourceObjectID, captured: false))
        for key in ["sourceSnapshotSHA256", "sourceViewSHA256", "sourceNativeType", "sourceUniqueKey"] {
            var changed = captured.values
            changed[key] = .string("changed")
            XCTAssertThrowsError(try AnyNativeImportedCatalogChecks.evidence(changed,
                source: directory.source, sourceObjectID: captured.sourceObjectID, captured: true))
        }
        let noSnapshot = try XCTUnwrap(directory.entries.first { $0.evidence == nil })
        XCTAssertThrowsError(try AnyNativeImportedCatalogChecks.evidence(noSnapshot.values,
            source: directory.source, sourceObjectID: noSnapshot.sourceObjectID, captured: true))
        try fixture.requireRetainedInputsUnchanged()
    }

    func testDestinationAccountScopeIsExactBeforeAnyCatalogRequest() throws {
        let composed = "account-caf\u{00E9}", decomposed = "account-cafe\u{0301}"
        XCTAssertEqual(composed, decomposed)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: "http://127.0.0.1:1")), expectedAccountID: composed)
        let foreign = try AnyTorahWorkspace(accountID: decomposed, spaceID: "space")
        XCTAssertThrowsError(try AnyNativeImportedCatalogStore(client: client, workspace: foreign)) {
            XCTAssertEqual($0 as? AnyHostError, .wrongWorkspace)
        }
        XCTAssertThrowsError(try AnyHeartOriginalMetadataStore(client: client, workspace: foreign)) {
            XCTAssertEqual($0 as? AnyHostError, .wrongWorkspace)
        }
    }

    private func load() throws -> NativeCanonicalSupplementFixture {
        let environment = ProcessInfo.processInfo.environment
        guard environment["PINKHA_NATIVE_DEFINITION_RETAINED"] != nil,
              environment["PINKHA_NATIVE_ORIGINAL156"] != nil else {
            throw AnyNativeImportedCatalogError.invalidOriginalPlan
        }
        return try NativeCanonicalSupplementFixture.load()
    }
    private func wire(_ value: AnyJSON) throws -> Data { try AnyDestinationDefinitionChecks.bytes(value) }

    private func replacing(_ original: AnyDestinationDefinitionEvidence,
                           details changes: [String: AnyJSON]) throws -> AnyDestinationDefinitionEvidence {
        var view = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: original.jsonViewBytes).object)
        var snapshot = try XCTUnwrap(view["Snapshot"]?.object)
        var details = try XCTUnwrap(snapshot["details"]?.object)
        details.merge(changes) { _, replacement in replacement }
        snapshot["details"] = .object(details); view["Snapshot"] = .object(snapshot)
        return try .init(sourceSpaceID: original.sourceSpaceID, sourceObjectID: original.sourceObjectID,
            protobufBytes: original.protobufBytes, jsonViewBytes: wire(.object(view)))
    }
}
