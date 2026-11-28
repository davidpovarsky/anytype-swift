import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

/// Synthetic capture envelopes exercise the new format, never native authority.
/// The two original-data methods use only the exact retained archive and saved
/// 182-operation plan as inert inputs. One proves v1 byte compatibility; the other
/// deliberately re-encodes a synthetic complete-capture derivative. Neither
/// executes those operations or supplies a source/native authority token.
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
        let f = try retained()
        let rebuilt = try AnyHeartNativePreservationArchive(bundle: f.restored.bundle, recovered: f.recovered,
            memberData: f.restored.capturedMemberData, recoveredMemberData: f.restored.recoveredMemberData)
        XCTAssertEqual(rebuilt.bytes, f.archiveBytes)
        XCTAssertEqual(rebuilt.sha256, "5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463")
        let preservation = try AnyHeartNativeSourcePreservation(bundle: f.restored.bundle,
            recoveredDefinitions: f.recovered, archive: rebuilt)
        let plan = try preservation.preservationPlan(workspace: f.plan.binding.workspace,
            storeID: f.plan.binding.storeID, planID: f.plan.binding.planID)
        XCTAssertEqual(plan.items.count, 182)
        XCTAssertEqual(plan.canonicalBytes, f.plan.canonicalBytes)
        try requireRetainedInputsUnchanged(f)
    }

    func testSyntheticCompleteCaptureDerivativeAdmitsV2PlanCatalogAndLocatorPair() throws {
        let f = try retained()
        let old = f.restored.bundle
        // The original archive, plan, receipt and capture bytes stay immutable.
        // This is a re-encoded synthetic view: historically recovered exact
        // descriptor bytes are declared as capture members for format coverage.
        // It is NOT an actual App capture and grants no live source authority.
        let definitions = (old.bundledDefinitions + f.recovered.definitions).sorted {
            Data($0.identity.utf8).lexicographicallyPrecedes(Data($1.identity.utf8))
        }
        XCTAssertEqual(definitions.map(\.identity), old.bundledDefinitionsUsed)
        var members: [String: Data] = [:]
        for member in old.verifiedMembers { members[member.path] = try f.restored.capturedMemberData(member) }
        var descriptors: [AnyJSON] = []
        for definition in definitions {
            let stem = "compiled-definition-" + hash(definition.identity)
            for (path, bytes) in [(stem + ".pb", definition.protobufBytes),
                                  (stem + ".json", definition.jsonViewBytes)] {
                if let original = members[path] { XCTAssertEqual(original, bytes) }
                else { members[path] = bytes }
            }
            descriptors.append(.object([
                "Kind": .string(definition.kind.rawValue), "Key": .string(definition.key),
                "ProtobufMessage": .string(definition.protobufMessage),
                "Protobuf": member(stem + ".pb", definition.protobufBytes),
                "JSONView": member(stem + ".json", definition.jsonViewBytes)
            ]))
        }
        var fields = try XCTUnwrap(old.rawManifest.object)
        fields["BundledDefinitions"] = .array(descriptors)
        let syntheticManifest = try encode(.object(fields))
        XCTAssertNotEqual(syntheticManifest, old.manifestBytes)
        let synthetic = try AnyHeartNativeSpaceBundle(manifest: syntheticManifest,
            sourceAccountID: old.sourceAccountID, sourceSpaceID: old.sourceSpaceID) {
                try XCTUnwrap(members[$0.path])
            }
        var restoredFields = try XCTUnwrap(synthetic.rawManifest.object)
        if let original = old.rawManifest["BundledDefinitions"] { restoredFields["BundledDefinitions"] = original }
        else { restoredFields.removeValue(forKey: "BundledDefinitions") }
        XCTAssertEqual(.object(restoredFields), old.rawManifest)
        XCTAssertEqual(synthetic.bundledDefinitions.map(\.identity), old.bundledDefinitionsUsed)
        let archive = try AnyHeartNativePreservationArchive(capturedBundle: synthetic) {
            try XCTUnwrap(members[$0.path])
        }
        let preservation = try AnyHeartNativeSourcePreservation(capturedBundle: synthetic, archive: archive)
        XCTAssertEqual(preservation.preservationContract, AnyHeartNativeSourcePreservation.capturedContract)
        XCTAssertEqual(preservation.definitionEvidence.kind, .capturedComplete)
        XCTAssertNil(preservation.recoveredDefinitions)
        XCTAssertEqual(archive.recoveredMemberCount, 0)
        let plan = try preservation.preservationPlan(workspace: f.plan.binding.workspace,
            storeID: f.plan.binding.storeID, planID: f.plan.binding.planID)
        try plan.requireExecutable()
        XCTAssertEqual(plan.items.count, 182)
        XCTAssertNotEqual(plan.canonicalBytes, f.plan.canonicalBytes)
        XCTAssertEqual(plan.source.captureManifestSHA256, synthetic.manifestSHA256)
        let catalog = try XCTUnwrap(plan.items.first {
            Data($0.sourceKey.utf8) == Data(preservation.catalogTypeSourceKey.utf8)
        })
        guard case .typeDefinition(let draft) = catalog.operation,
              case .literal(let metadata) = draft.meta else {
            return XCTFail("Synthetic v2 catalog must retain the actual typed declaration.")
        }
        XCTAssertEqual(metadata["preservationContract"], .string(AnyHeartNativeSourcePreservation.capturedContract))
        XCTAssertEqual(metadata["sourceDefinitionEvidence"], .string("captured-complete"))
        XCTAssertNil(metadata["sourceRecoveryManifestSHA256"])
        // These are explicitly synthetic, inert saved-locator fixtures. Their
        // paired codecs/binding are exercised; a real completed checkpoint and
        // native owner are NOT fabricated or returned by the producer.
        var reference = referenceFields()
        reference["contract"] = .string(AnyNativeImportedContextReference.capturedVersion)
        reference["destinationAccountID"] = .string(plan.binding.workspace.accountID)
        reference["destinationSpaceID"] = .string(plan.binding.workspace.spaceID)
        reference["storeID"] = .string(plan.binding.storeID)
        reference["planID"] = .string(plan.binding.planID)
        reference["planSHA256"] = .string(plan.binding.planSHA256)
        reference["sourceAccountID"] = .string(synthetic.sourceAccountID)
        reference["sourceSpaceID"] = .string(synthetic.sourceSpaceID)
        reference["captureManifestSHA256"] = .string(synthetic.manifestSHA256)
        reference["sourceWitnessSHA256"] = .string(synthetic.sourceWitnessSHA256)
        reference["archiveSourceKey"] = .string(preservation.archiveItemSourceKey)
        reference["archiveSHA256"] = .string(archive.sha256)
        reference["archiveBytes"] = .integer(Int64(archive.bytes.count))
        reference.removeValue(forKey: "recoveredManifestSHA256")
        reference["definitionEvidence"] = .string("captured-complete")
        let encoded = try encode(.object(reference))
        let locator = try AnyNativeImportedContextReference.decode(encoded)
        XCTAssertEqual(try locator.encoded(), encoded)
        XCTAssertEqual(try locator.expectedArchiveBinding(), archive.binding)
        let contentBytes = try encode(.object([
            "contract": .string(AnyNativeImportedContentContextReference.version),
            "checkpointScope": .string("completed-preservation-current-content"),
            "preservationReferenceSHA256": .string(AnyContentDigest.sha256(encoded)),
            "contentPlanID": .string(plan.binding.planID), "contentPlanSHA256": .string(plan.binding.planSHA256),
            "contentCheckpointSHA256": .string(locator.checkpointSHA256),
            "contentSHA256": .string(preservation.currentContent.contentSHA256)
        ]))
        let content = try AnyNativeImportedContentContextReference.decode(contentBytes)
        XCTAssertEqual(try content.encoded(), contentBytes)
        XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(
            try content.binding(preservation: locator), plan.binding))
        XCTAssertFalse(locator.grantsNativeAuthority)
        XCTAssertFalse(content.grantsNativeAuthority)
        try requireRetainedInputsUnchanged(f)
    }

    private struct Retained {
        let archiveBytes: Data
        let planBytes: Data
        let plan: AnyDestinationMigrationPlan
        let restored: AnyHeartNativePreservationArchive.Restored
        let recovered: AnyHeartNativeRecoveredDefinitions
    }

    private func retained() throws -> Retained {
        let archiveBytes = try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_ARCHIVE", bytes: 1_634_696,
            sha256: "5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463")
        let planBytes = try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_PLAN", bytes: 1_823_803,
            sha256: "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930")
        let plan = try AnyDestinationMigrationPlan.decode(planBytes)
        XCTAssertEqual(plan.items.count, 182)
        let files = plan.items.compactMap { item -> (Int64, String)? in
            guard case .file(_, _, let mime, let size, let sha) = item.operation,
                  mime == AnyHeartNativePreservationArchive.mimeType else { return nil }
            return (size, sha)
        }
        XCTAssertEqual(files.count, 1)
        let expectedFile = try XCTUnwrap(files.first)
        XCTAssertEqual(expectedFile.0, Int64(archiveBytes.count))
        XCTAssertEqual(expectedFile.1, AnyContentDigest.sha256(archiveBytes))
        // Actual catalog values are .object expressions with a mapped URI.
        // Select the unique type declaration's literal contract/source metadata.
        let metadataRows = plan.items.compactMap { item -> [String: AnyJSON]? in
            guard case .typeDefinition(let draft) = item.operation,
                  case .literal(let value) = draft.meta, let fields = value.object,
                  fields["preservationContract"] == .string(AnyHeartNativeSourcePreservation.contract),
                  fields["sourceCaptureManifestSHA256"] == .string(plan.source.captureManifestSHA256)
            else { return nil }
            return fields
        }
        XCTAssertEqual(metadataRows.count, 1)
        let metadata = try XCTUnwrap(metadataRows.first)
        let recovery = try XCTUnwrap(metadata["sourceRecoveryManifestSHA256"]?.string)
        let binding = try AnyHeartNativePreservationArchive.Binding(
            expectedAccountID: plan.source.accountID, expectedSpaceID: plan.source.spaceID,
            captureManifestSHA256: plan.source.captureManifestSHA256,
            sourceWitnessSHA256: plan.source.witnessSHA256, recoveredManifestSHA256: recovery)
        let restored = try AnyHeartNativePreservationArchive.restore(archiveBytes, expected: binding)
        return .init(archiveBytes: archiveBytes, planBytes: planBytes, plan: plan, restored: restored,
                     recovered: try XCTUnwrap(restored.recoveredDefinitions))
    }

    private func requireRetainedInputsUnchanged(_ value: Retained) throws {
        XCTAssertEqual(try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_ARCHIVE", bytes: 1_634_696,
            sha256: "5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463"), value.archiveBytes)
        XCTAssertEqual(try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_PLAN", bytes: 1_823_803,
            sha256: "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930"), value.planBytes)
    }

    /// Reads only a later controller's two exact private fixture inputs. No
    /// original loose-member tree, journal, account or network is consulted.
    private func fixedInput(_ variable: String, bytes expectedBytes: Int, sha256: String) throws -> Data {
        guard let path = ProcessInfo.processInfo.environment[variable] else {
            throw XCTSkip("Required retained original input is not supplied; selected admission must reject a skip.")
        }
        let fd = open(path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        guard fd >= 0 else { throw AnyHeartNativePreservationError.binding }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        var before = stat(), after = stat(), named = stat()
        guard fstat(fd, &before) == 0,
              before.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG),
              before.st_nlink == 1, before.st_size == Int64(expectedBytes),
              expectedBytes <= AnyHeartNativePreservationArchive.maximumBytes else {
            throw AnyHeartNativePreservationError.binding
        }
        var data = Data()
        while data.count <= expectedBytes {
            let part = try handle.read(upToCount: min(65_536, expectedBytes + 1 - data.count)) ?? Data()
            if part.isEmpty { break }; data.append(part)
        }
        guard data.count == expectedBytes, AnyContentDigest.sha256(data) == sha256,
              fstat(fd, &after) == 0, lstat(path, &named) == 0,
              sameFile(before, after), sameFile(before, named) else {
            throw AnyHeartNativePreservationError.binding
        }
        try handle.close()
        return data
    }

    private func sameFile(_ a: stat, _ b: stat) -> Bool {
        guard a.st_dev == b.st_dev, a.st_ino == b.st_ino, a.st_mode == b.st_mode,
              a.st_uid == b.st_uid, a.st_gid == b.st_gid, a.st_nlink == b.st_nlink,
              a.st_size == b.st_size else { return false }
        #if canImport(Darwin)
        return a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
            a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
        #else
        return a.st_mtim.tv_sec == b.st_mtim.tv_sec && a.st_mtim.tv_nsec == b.st_mtim.tv_nsec &&
            a.st_ctim.tv_sec == b.st_ctim.tv_sec && a.st_ctim.tv_nsec == b.st_ctim.tv_nsec
        #endif
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
