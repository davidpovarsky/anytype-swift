import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Synthetic capture envelopes exercise the new format, never native authority.
/// The mandatory v1 compatibility method separately requires the exact retained
/// original archive and accepted182 plan; absence must remain an explicit skip.
final class NativeDirectCapturePreservationTests: XCTestCase, @unchecked Sendable {
    private let account = "source-account", space = "source-space"
    private func hash(_ text: String) -> String { AnyContentDigest.sha256(Data(text.utf8)) }
    private func encode(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    private func receipt() -> AnyJSON {
        .object([
            "Version": .string("loaded-account-native-space-source-v1"),
            "Source": .object([
                "version": .string("loaded-account-native-witness-v1"),
                "accountAuthority": .string("held-application-account-directory-lease-v1"),
                "sessionAuthority": .string("validated-native-full-unassociated-session-v1"),
                "accountSHA256": .string(hash(account)), "accountDirectorySHA256": .string(hash("unit-directory")),
                "accountSessionAuthorizedAtCapture": .bool(true), "nativeIdentityCensusRequired": .bool(true),
                "source": .object([
                    "version": .string("loaded-native-acl-witness-v1"),
                    "accountSHA256": .string(hash(account)), "spaceSHA256": .string(hash(space)),
                    "alreadyLoaded": .bool(true), "aclReadAuthorizedAtCapture": .bool(true),
                    "aclIdSHA256": .string(hash("acl")), "aclHeadSHA256": .string(hash("head")),
                    "native": .object([
                        "Version": .string("native-localstore-witness-v1"), "SpaceSHA256": .string(hash(space)),
                        "WitnessSHA256": .string(hash("unit-witness")), "LocalDecodedRowsComplete": .bool(true),
                        "Generation": .integer(0)])
                ])
            ]),
            "Inventory": .object(["SpaceSHA256": .string(hash(space)), "SourceWitnessSHA256": .string(hash("unit-witness")),
                "ACLHeadSHA256": .string(hash("head")), "Generation": .integer(0), "Trees": .integer(0),
                "OtherCollections": .integer(0), "OtherCollectionRows": .integer(0)]),
            "AccountSessionAuthorizedAtFinalCapture": .bool(true), "AllNativeHeadRowsAccounted": .bool(true),
            "CapturedSnapshotsBoundToUnchangedCheckpoint": .bool(true), "OriginalNativeHistoryRowsRetained": .bool(true),
            "NativeTrees": .integer(0), "CapturedObjects": .integer(0), "CapturedFiles": .integer(0),
            "FileReferences": .integer(0), "UnresolvedEntries": .integer(0), "ClosedResolverUnmapped": .integer(0),
            "SnapshotBytes": .integer(0), "MetadataBytes": .integer(0), "PlaintextBytes": .integer(0),
            "Tombstones": .integer(0), "SettingsTrees": .integer(0), "UnsupportedTrees": .integer(0),
            "IndexResolverSnapshotBound": .bool(false), "Objects": .array([]),
            "AllCurrentObjectsCaptured": .bool(true), "CurrentFilePayloadCompleteness": .bool(true),
            "PermitsDestinationWrites": .bool(false), "HasNativeSourceAdmission": .bool(false),
            "SemanticCompleteness": .bool(false), "HistorySemanticsValidated": .bool(false)])
    }


    private struct Fixture {
        let bundle: AnyHeartNativeSpaceBundle
        let members: [String: Data]
    }

    private func fixture(withDefinition: Bool = false, declared: Bool = true,
                         missingUsedDefinition: Bool = false, nullDeclaration: Bool = false) throws -> Fixture {
        let rows = Data("synthetic unit control; not a native capture".utf8)
        var members = ["native-source-rows.witness": rows]
        var used: [AnyJSON] = [], descriptors: [AnyJSON] = []
        if withDefinition {
            let identity = "type:synthetic-type", key = "synthetic-type"
            // Deliberately synthetic wire/view pair. Only the real capture
            // bridge can supply native source authority in production.
            let raw = Data([0x0a, 0x01, 0x78])
            let view = try encode(.object([
                "Contract": .string("pinkha-native-bundled-definition-json-v1"),
                "Kind": .string("type"), "Key": .string(key),
                "ProtobufMessage": .string("anytype.model.ObjectType"),
                "ProtobufSHA256": .string(AnyContentDigest.sha256(raw)),
                "ProtobufBytes": .integer(Int64(raw.count)), "Definition": .object(["key": .string(key)])
            ]))
            let stem = "compiled-definition-" + hash(identity)
            members[stem + ".pb"] = raw; members[stem + ".json"] = view
            used = [.string(identity)]
            descriptors = [.object([
                "Kind": .string("type"), "Key": .string(key),
                "ProtobufMessage": .string("anytype.model.ObjectType"),
                "Protobuf": member(stem + ".pb", raw), "JSONView": member(stem + ".json", view)
            ])]
        }
        if missingUsedDefinition { used = [.string("property:missing")] }
        var fields: [String: AnyJSON] = [
            "Contract": .string("pinkha-native-whole-source-bundle-v1"), "Receipt": receipt(),
            "SourceRows": member("native-source-rows.witness", rows),
            "Trees": .array([]), "Objects": .array([]), "Files": .array([]), "FileReferences": .array([]),
            "Gaps": .array([]), "ResolverUnmapped": .array([]), "BundledDefinitionsUsed": .array(used),
            "RetainedOtherCollections": .array([])
        ]
        if declared { fields["BundledDefinitions"] = nullDeclaration ? .null : .array(descriptors) }
        let bundle = try AnyHeartNativeSpaceBundle(manifest: encode(.object(fields)),
            sourceAccountID: account, sourceSpaceID: space) { try XCTUnwrap(members[$0.path]) }
        return .init(bundle: bundle, members: members)
    }

    private func member(_ path: String, _ bytes: Data) -> AnyJSON {
        .object(["Path": .string(path), "Bytes": .integer(Int64(bytes.count)),
                 "SHA256": .string(AnyContentDigest.sha256(bytes))])
    }

    private func archive(_ fixture: Fixture) throws -> AnyHeartNativePreservationArchive {
        try .init(capturedBundle: fixture.bundle) { try XCTUnwrap(fixture.members[$0.path]) }
    }

    func testDirectArchiveRetainsCompleteCapturedDescriptorsWithoutRecovery() throws {
        let f = try fixture(withDefinition: true), archive = try self.archive(f)
        let restored = try AnyHeartNativePreservationArchive.restore(archive.bytes, expected: archive.binding)
        XCTAssertEqual(archive.binding.definitionEvidenceKind, .capturedComplete)
        XCTAssertNil(archive.binding.recoveredManifestSHA256)
        XCTAssertNil(restored.recoveredDefinitions)
        XCTAssertEqual(restored.definitionEvidence.kind, .capturedComplete)
        XCTAssertEqual(restored.recoveredMemberCount, 0)
        XCTAssertEqual(restored.originalMemberCount, f.bundle.verifiedMembers.count + 1)
        XCTAssertEqual(restored.bundle.manifestBytes, f.bundle.manifestBytes)
        XCTAssertEqual(restored.bundle.bundledDefinitionsUsed, ["type:synthetic-type"])
        XCTAssertEqual(restored.bundle.bundledDefinitions.count, 1)
        for declared in f.bundle.verifiedMembers {
            XCTAssertEqual(try restored.capturedMemberData(declared), f.members[declared.path])
        }
        let reopened = try AnyHeartNativePreservationArchive(restoring: archive.bytes, expected: archive.binding)
        XCTAssertEqual(reopened.bytes, archive.bytes)
        XCTAssertEqual(reopened.sha256, archive.sha256)
        XCTAssertFalse(restored.grantsSourceSession)
        XCTAssertFalse(restored.restoresAnAccount)
        XCTAssertFalse(archive.permitsDestinationWrites)
        XCTAssertThrowsError(try restored.recoveredMemberData(f.bundle.sourceRows)) {
            XCTAssertEqual($0 as? AnyHeartNativePreservationError, .member)
        }
        // The empty synthetic source has no genuine native-store context or
        // supported content. An archive cannot manufacture executable coverage.
        XCTAssertThrowsError(try AnyHeartNativeSourcePreservation(capturedBundle: f.bundle, archive: archive)) {
            XCTAssertEqual($0 as? AnyDestinationMigrationError, .invalidPlan("full preservation source contract"))
        }
    }

    func testDirectCaptureRequiresExplicitCompleteDescriptorCensus() throws {
        let empty = try fixture()
        XCTAssertEqual(try self.archive(empty).recoveredMemberCount, 0)
        let explicitNull = try fixture(nullDeclaration: true)
        XCTAssertEqual(explicitNull.bundle.rawManifest["BundledDefinitions"], .null)
        XCTAssertEqual(try self.archive(explicitNull).recoveredMemberCount, 0)
        for value in [try fixture(declared: false),
                      try fixture(declared: false, missingUsedDefinition: true)] {
            XCTAssertThrowsError(try self.archive(value)) {
                XCTAssertEqual($0 as? AnyHeartNativePreservationError, .binding)
            }
        }
        // Mismatched nonempty Used/declaration sets fail the original bundle
        // parser itself; they never reach the direct archive initializer.
        XCTAssertThrowsError(try fixture(declared: true, missingUsedDefinition: true)) {
            XCTAssertEqual($0 as? AnyHeartNativeSpaceBundleError, .inconsistentInventory)
        }
    }

    func testDirectArchiveRejectsOppositeEvidenceHeadersAndCrossVersionBindings() throws {
        let f = try fixture(), original = try self.archive(f)
        for value in [AnyJSON.null, .string(""), .string(String(repeating: "a", count: 64))] {
            let changed = try replacingHeader(original.bytes) { fields in
                fields["recoveredManifestSHA256"] = value
            }
            XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(changed, expected: original.binding)) {
                XCTAssertEqual($0 as? AnyHeartNativePreservationError, .binding)
            }
        }
        for value in [AnyJSON.null, .string(""), .string("recovered-original")] {
            let changed = try replacingHeader(original.bytes) { $0["definitionEvidence"] = value }
            XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(changed, expected: original.binding)) {
                XCTAssertEqual($0 as? AnyHeartNativePreservationError, .binding)
            }
        }
        let historical = try AnyHeartNativePreservationArchive.Binding(
            expectedAccountID: account, expectedSpaceID: space,
            captureManifestSHA256: f.bundle.manifestSHA256, sourceWitnessSHA256: f.bundle.sourceWitnessSHA256,
            recoveredManifestSHA256: String(repeating: "a", count: 64))
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(original.bytes, expected: historical)) {
            XCTAssertEqual($0 as? AnyHeartNativePreservationError, .malformedArchive)
        }
        let foreign = try AnyHeartNativePreservationArchive.Binding(expectedAccountID: "foreign-account",
            expectedSpaceID: space, capturedManifestSHA256: f.bundle.manifestSHA256,
            sourceWitnessSHA256: f.bundle.sourceWitnessSHA256)
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(original.bytes, expected: foreign)) {
            XCTAssertEqual($0 as? AnyHeartNativePreservationError, .binding)
        }
    }

    func testDirectArchiveRejectsPayloadCorruptionExtraBytesAndRecoveryMembers() throws {
        let f = try fixture(withDefinition: true), original = try self.archive(f)
        var corrupted = original.bytes; corrupted[corrupted.count - 1] ^= 1
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(corrupted, expected: original.binding)) {
            XCTAssertEqual($0 as? AnyHeartNativePreservationError, .member)
        }
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(original.bytes + Data([0]),
                                                                           expected: original.binding))
        let recoveryMember = try replacingHeader(original.bytes) { fields in
            var rows = try XCTUnwrap(fields["members"]?.array)
            var first = try XCTUnwrap(rows[0].object)
            first["path"] = .string("recovery/binding.json")
            rows[0] = .object(first); fields["members"] = .array(rows)
        }
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(recoveryMember, expected: original.binding)) {
            XCTAssertEqual($0 as? AnyHeartNativePreservationError, .member)
        }
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive(capturedBundle: f.bundle) {
            try XCTUnwrap(f.members[$0.path]) + Data([0])
        }) { XCTAssertEqual($0 as? AnyHeartNativePreservationError, .member) }
    }

    func testHistoricalReferenceEncodingRetainsExactlyTheOriginalClosedV1Keys() throws {
        let fields = referenceFields()
        let original = try encode(.object(fields))
        let reference = try AnyNativeImportedContextReference.decode(original)
        XCTAssertEqual(try reference.encoded(), original)
        XCTAssertNil(reference.definitionEvidence)
        XCTAssertEqual(reference.recoveredManifestSHA256, String(repeating: "e", count: 64))
        XCTAssertEqual(try reference.expectedArchiveBinding().definitionEvidenceKind, .recoveredOriginal)
        XCTAssertFalse(reference.grantsNativeAuthority)
        var mixed = fields; mixed["definitionEvidence"] = .string("captured-complete")
        XCTAssertThrowsError(try AnyNativeImportedContextReference.decode(encode(.object(mixed)))) {
            XCTAssertEqual($0 as? AnyNativeImportedContextError, .invalidReference)
        }
    }

    func testDirectReferenceRejectsNullEmptyMissingAndOppositeEvidenceFields() throws {
        var fields = referenceFields()
        fields["contract"] = .string(AnyNativeImportedContextReference.capturedVersion)
        fields.removeValue(forKey: "recoveredManifestSHA256")
        fields["definitionEvidence"] = .string("captured-complete")
        let wire = try encode(.object(fields))
        let reference = try AnyNativeImportedContextReference.decode(wire)
        XCTAssertEqual(try reference.encoded(), wire)
        XCTAssertNil(reference.recoveredManifestSHA256)
        XCTAssertEqual(try reference.expectedArchiveBinding().definitionEvidenceKind, .capturedComplete)
        XCTAssertFalse(reference.grantsNativeAuthority)
        for value in [AnyJSON.null, .string(""), .string("recovered-original")] {
            var changed = fields; changed["definitionEvidence"] = value
            XCTAssertThrowsError(try AnyNativeImportedContextReference.decode(encode(.object(changed))))
        }
        for value in [AnyJSON.null, .string(""), .string(String(repeating: "e", count: 64))] {
            var changed = fields; changed["recoveredManifestSHA256"] = value
            XCTAssertThrowsError(try AnyNativeImportedContextReference.decode(encode(.object(changed)))) {
                XCTAssertEqual($0 as? AnyNativeImportedContextError, .invalidReference)
            }
        }
        var missing = fields; missing.removeValue(forKey: "definitionEvidence")
        XCTAssertThrowsError(try AnyNativeImportedContextReference.decode(encode(.object(missing)))) {
            XCTAssertEqual($0 as? AnyNativeImportedContextError, .invalidReference)
        }
    }

    func testActualRetainedV1ArchiveAnd182PlanRemainByteIdentical() throws {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_CAPTURE_PRODUCER_RETAINED_V1_ARCHIVE"] else {
            throw XCTSkip("Mandatory original v1 archive locator is not yet independently recovered; no byte-regression result is claimed.")
        }
        let original = try NativeCanonicalSupplementFixture.load()
        let files = original.plan.items.compactMap { item -> (String, Int64, String)? in
            guard case .file(_, _, let mime, let size, let sha) = item.operation,
                  mime == AnyHeartNativePreservationArchive.mimeType else { return nil }
            return (item.sourceKey, size, sha)
        }
        XCTAssertEqual(files.count, 1)
        let expected = try XCTUnwrap(files.first)
        let url = URL(fileURLWithPath: path)
        let attributes = try url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey])
        guard attributes.isRegularFile == true, attributes.isSymbolicLink != true,
              Int64(try XCTUnwrap(attributes.fileSize)) == expected.1,
              expected.1 <= Int64(AnyHeartNativePreservationArchive.maximumBytes) else {
            throw AnyHeartNativePreservationError.binding
        }
        let bytes = try Data(contentsOf: url)
        XCTAssertEqual(AnyContentDigest.sha256(bytes), expected.2)
        // The actual catalog record values are an .object expression with
        // mapped archiveURI. Its type declaration carries the original literal
        // preservation evidence; select that exact contract/source, not a first
        // arbitrary immutable record.
        let metadataRows = original.plan.items.compactMap { item -> [String: AnyJSON]? in
            guard case .typeDefinition(let draft) = item.operation,
                  case .literal(let value) = draft.meta, let fields = value.object,
                  fields["preservationContract"] == .string(AnyHeartNativeSourcePreservation.contract),
                  fields["sourceCaptureManifestSHA256"] == .string(original.plan.source.captureManifestSHA256)
            else { return nil }
            return fields
        }
        XCTAssertEqual(metadataRows.count, 1)
        let metadata = try XCTUnwrap(metadataRows.first)
        let recovery = try XCTUnwrap(metadata["sourceRecoveryManifestSHA256"]?.string)
        let binding = try AnyHeartNativePreservationArchive.Binding(
            expectedAccountID: original.plan.source.accountID, expectedSpaceID: original.plan.source.spaceID,
            captureManifestSHA256: original.plan.source.captureManifestSHA256,
            sourceWitnessSHA256: original.plan.source.witnessSHA256, recoveredManifestSHA256: recovery)
        let restored = try AnyHeartNativePreservationArchive.restore(bytes, expected: binding)
        let recovered = try XCTUnwrap(restored.recoveredDefinitions)
        let rebuilt = try AnyHeartNativePreservationArchive(bundle: restored.bundle, recovered: recovered,
            memberData: restored.capturedMemberData, recoveredMemberData: restored.recoveredMemberData)
        XCTAssertEqual(rebuilt.bytes, bytes)
        XCTAssertEqual(rebuilt.sha256, expected.2)
        let preservation = try AnyHeartNativeSourcePreservation(bundle: restored.bundle,
            recoveredDefinitions: recovered, archive: rebuilt)
        let plan = try preservation.preservationPlan(workspace: original.plan.binding.workspace,
            storeID: original.plan.binding.storeID, planID: original.plan.binding.planID)
        XCTAssertEqual(plan.items.count, 182)
        XCTAssertEqual(plan.canonicalBytes, original.plan.canonicalBytes)
        try original.requireRetainedInputsUnchanged()
    }

    private func replacingHeader(_ data: Data,
                                 change: (inout [String: AnyJSON]) throws -> Void) throws -> Data {
        let magic = Data("PINKHA-HEART-SOURCE-2\u{0}".utf8)
        XCTAssertEqual(data.prefix(magic.count), magic)
        var length: UInt64 = 0
        for byte in data[magic.count..<(magic.count + 8)] { length = (length << 8) | UInt64(byte) }
        let start = magic.count + 8, end = start + Int(length)
        var fields = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: data.subdata(in: start..<end)).object)
        try change(&fields)
        let header = try encode(.object(fields))
        var result = magic
        for shift in stride(from: 56, through: 0, by: -8) {
            result.append(UInt8((UInt64(header.count) >> UInt64(shift)) & 255))
        }
        result.append(header); result.append(data.subdata(in: end..<data.count))
        return result
    }

    private func referenceFields() -> [String: AnyJSON] {
        [
            "contract": .string(AnyNativeImportedContextReference.version),
            "destinationNetworkID": .string("fixture-network"),
            "destinationAccountID": .string("fixture-account"), "destinationSpaceID": .string("fixture-space"),
            "storeID": .string("fixture-store"), "planID": .string(String(repeating: "2", count: 64)),
            "planSHA256": .string(String(repeating: "a", count: 64)),
            "checkpointSHA256": .string(String(repeating: "b", count: 64)),
            "sourceAccountID": .string("source-account"), "sourceSpaceID": .string("source-space"),
            "captureManifestSHA256": .string(String(repeating: "c", count: 64)),
            "sourceWitnessSHA256": .string(String(repeating: "d", count: 64)),
            "recoveredManifestSHA256": .string(String(repeating: "e", count: 64)),
            "archiveSourceKey": .string("source-archive"), "archiveSHA256": .string(String(repeating: "1", count: 64)),
            "archiveBytes": .integer(4096), "supplementalCanonicalDefinitions": .array([])
        ]
    }
}
