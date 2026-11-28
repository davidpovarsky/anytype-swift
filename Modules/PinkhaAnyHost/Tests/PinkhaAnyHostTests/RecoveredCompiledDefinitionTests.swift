#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyHost
@testable import PinkhaAnyIntegration

/// Actual historical source and independently qualified recovered registry bytes.
/// These controls neither open an engine nor confer whole-source admission.
final class RecoveredCompiledDefinitionTests: XCTestCase, @unchecked Sendable {
    private struct Evidence {
        let bundle: AnyHeartNativeSpaceBundle
        let manifest: Data
        let producer: Data
        let recovery: Data
        let exported: Data
        let members: [String: Data]

        func recovered(manifest override: Data? = nil, producer producerOverride: Data? = nil,
                       recovery recoveryOverride: Data? = nil, exported exportOverride: Data? = nil,
                       expectedHash: String? = nil, members memberOverride: [String: Data]? = nil) throws
        -> AnyHeartNativeRecoveredDefinitions {
            let binding = override ?? manifest
            let source = memberOverride ?? members
            return try .init(bundle: bundle, manifest: binding,
                expectedManifestSHA256: expectedHash ?? AnyContentDigest.sha256(binding),
                originalProducer: producerOverride ?? producer,
                recoveryReceipt: recoveryOverride ?? recovery, registryExport: exportOverride ?? exported) {
                    try XCTUnwrap(source[$0.path])
                }
        }
    }

    func testActualHistorical156AndSevenOriginalDescriptorsRemainSeparate() throws {
        let e = try evidence()
        let baseline = try AnyHeartNativeDefinitionCatalog(bundle: e.bundle)
        let recovered = try e.recovered()
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: e.bundle, recoveredDefinitions: recovered)
        XCTAssertEqual(e.bundle.objects.count, 156)
        XCTAssertEqual(e.bundle.trees.count, 157)
        XCTAssertTrue(e.bundle.bundledDefinitions.isEmpty)
        XCTAssertEqual(recovered.definitions.count, 7)
        XCTAssertEqual(recovered.verifiedMembers.count, 14)
        XCTAssertFalse(recovered.permitsDestinationWrites)
        XCTAssertFalse(recovered.replacesHistoricalCapturedMembers)
        XCTAssertEqual(catalog.types.count, 20)
        XCTAssertEqual(catalog.relations.count, 126)
        XCTAssertEqual(catalog.options.count, 4)
        XCTAssertEqual(catalog.compiledRelations.count, 7)
        XCTAssertEqual(catalog.recoveredDefinitionManifestSHA256, recovered.manifestSHA256)
        XCTAssertNotEqual(catalog.contentSHA256, baseline.contentSHA256)
        XCTAssertEqual(baseline.contentSHA256, try AnyHeartNativeDefinitionCatalog(bundle: e.bundle).contentSHA256)
        XCTAssertEqual(baseline.compiledRelations.count, 0)
        XCTAssertNil(baseline.recoveredDefinitionManifestSHA256)
        XCTAssertEqual(recovered.originalProducerBytes, e.producer)
        XCTAssertEqual(try decode(e.producer)["status"], .string("FAIL"))
        XCTAssertFalse(catalog.permitsDestinationWrites)
        XCTAssertThrowsError(try AnyHeartNativeDefinitionPlan(catalog: catalog).admittedSchemaItems())
        for value in recovered.definitions {
            let stem = AnyContentDigest.sha256(Data(value.identity.utf8))
            XCTAssertEqual(value.protobufBytes, e.members[stem + ".pb"])
            XCTAssertEqual(value.jsonViewBytes, e.members[stem + ".json"])
        }
    }

    func testActualGeneratedFormatsReadonlyFlagsAndAbsentDefaults() throws {
        let e = try evidence()
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: e.bundle, recoveredDefinitions: e.recovered())
        let rows = Dictionary(uniqueKeysWithValues: catalog.compiledRelations.map { ($0.relationKey, $0) })
        let expected: [(String, Int64, Bool, Int64)] = [
            ("analyticsSpaceId", 0, true, 1), ("apiObjectKey", 0, false, 1),
            ("headerRelationsLayout", 2, false, 1), ("homepage", 0, false, 1),
            ("migrationObjectContext", 2, true, 1), ("orderId", 0, true, 1),
            ("relationFormatIncludeTime", 6, true, 0),
        ]
        XCTAssertEqual(Set(rows.keys), Set(expected.map(\.0)))
        for (key, format, readonly, maximum) in expected {
            let value = try XCTUnwrap(rows[key])
            XCTAssertEqual(value.rawFormat, format)
            XCTAssertEqual(value.readonlyValue, readonly)
            XCTAssertTrue(value.readonlyDefinition)
            XCTAssertTrue(value.hidden)
            XCTAssertFalse(value.multiple)
            XCTAssertEqual(value.maximumCount, maximum)
            XCTAssertEqual(value.scope, 1)
            XCTAssertEqual(value.dataSource, 0)
            XCTAssertNil(value.defaultValue)
            XCTAssertTrue(value.unknownFields.isEmpty)
        }
        XCTAssertEqual(rows["headerRelationsLayout"]?.revision, 1)
    }

    func testWrongExpectedDigestAndEveryCaptureIdentityRefuse() throws {
        let e = try evidence()
        XCTAssertThrowsError(try e.recovered(expectedHash: String(repeating: "0", count: 64)))
        for key in ["ManifestSHA256", "SourceWitnessSHA256", "AccountSHA256", "SpaceSHA256"] {
            let changed = try replacing(e.manifest, at: ["OriginalCapture", key],
                                        with: .string(String(repeating: "0", count: 64)))
            XCTAssertThrowsError(try e.recovered(manifest: changed), key)
        }
    }

    func testChangedOriginalProducerAndAuthorityDigestsRefuse() throws {
        let e = try evidence()
        for path in [["source", "manifest_sha256"], ["input_sha256", "source"], ["binary", "sha256"], ["heart_sha"]] {
            let changed = try replacing(e.producer, at: path, with: .string(String(repeating: "0", count: path == ["heart_sha"] ? 40 : 64)))
            let binding = try replacing(e.manifest, at: ["OriginalProducer", "ReceiptSHA256"],
                                        with: .string(AnyContentDigest.sha256(changed)))
            XCTAssertThrowsError(try e.recovered(manifest: binding, producer: changed))
        }
        for key in ["SourceArchiveSHA256", "SourceManifestSHA256", "NativeBinarySHA256", "HeartCommit"] {
            let changed = try replacing(e.manifest, at: ["OriginalProducer", key],
                                        with: .string(String(repeating: "0", count: key == "HeartCommit" ? 40 : 64)))
            XCTAssertThrowsError(try e.recovered(manifest: changed), key)
        }
    }

    func testRecoveryCannotClaimCapturedMembersOrSourceAdmission() throws {
        let e = try evidence()
        for (key, value) in [
            ("originalCapturedMembersReplaced", AnyJSON.bool(true)),
            ("sourceAdmission", .bool(true)), ("destinationWrites", .bool(true)),
            ("accountOrSpaceCalls", .integer(1)), ("nativeEngineBuilds", .integer(1)),
            ("original59826SourceFilesUnchanged", .bool(false)),
            ("originalCompiledWireAndFullDecodedModelEqual", .bool(false)),
        ] {
            let changed = try replacing(e.recovery, at: [key], with: value)
            let binding = try replacing(e.manifest, at: ["RecoveryReceiptSHA256"],
                                        with: .string(AnyContentDigest.sha256(changed)))
            XCTAssertThrowsError(try e.recovered(manifest: binding, recovery: changed), key)
        }
    }

    func testClosedExportOriginAndNoAccountAuthorityRefuse() throws {
        let e = try evidence()
        for (key, value) in [
            ("Origin", AnyJSON.string("historical-captured-member")),
            ("OriginalCapturedMember", .bool(true)), ("AccountOrSpaceOpened", .bool(true)),
            ("DestinationWrites", .bool(true)), ("ProtobufDecodeEqualsRegistry", .bool(false)),
            ("JSONDecodeEqualsRegistry", .bool(false)), ("RegistryUnchangedAfterExport", .bool(false)),
        ] {
            let exported = try replacing(e.exported, at: [key], with: value)
            let (binding, recovery) = try rebinding(e, exported: exported)
            XCTAssertThrowsError(try e.recovered(manifest: binding, recovery: recovery, exported: exported), key)
        }
    }

    func testMissingDuplicateAndForeignDefinitionDeclarationsRefuse() throws {
        let e = try evidence()
        let originalIDs = try XCTUnwrap(try decode(e.manifest)["DefinitionIDs"]?.array)
        for ids in [Array(originalIDs.dropLast()), originalIDs + [originalIDs[0]],
                    [.string("property:foreign")] + Array(originalIDs.dropFirst())] {
            let binding = try replacing(e.manifest, at: ["DefinitionIDs"], with: .array(ids))
            XCTAssertThrowsError(try e.recovered(manifest: binding))
        }
    }

    func testDescriptorTraversalAndAlteredProtobufOrJSONRefuse() throws {
        let e = try evidence()
        var exported = try XCTUnwrap(try decode(e.exported).object)
        var rows = try XCTUnwrap(exported["Descriptors"]?.array)
        var first = try XCTUnwrap(rows[0].object)
        var pb = try XCTUnwrap(first["Protobuf"]?.object)
        pb["Path"] = .string("../other.pb")
        first["Protobuf"] = .object(pb); rows[0] = .object(first); exported["Descriptors"] = .array(rows)
        let changed = try encode(.object(exported))
        let (binding, recovery) = try rebinding(e, exported: changed)
        XCTAssertThrowsError(try e.recovered(manifest: binding, recovery: recovery, exported: changed))
        for suffix in [".pb", ".json"] {
            var members = e.members
            let key = try XCTUnwrap(members.keys.sorted().first { $0.hasSuffix(suffix) })
            members[key]!.append(0x20)
            XCTAssertThrowsError(try e.recovered(members: members))
        }
    }

    func testDuplicateJSONKeysUnknownBindingFieldsAndMemberReplacementRefuse() throws {
        let e = try evidence()
        let text = try XCTUnwrap(String(data: e.manifest, encoding: .utf8))
        let duplicate = Data(("{\"Contract\":\"pinkha-recovered-compiled-definition-sidecar-v1\"," + text.dropFirst()).utf8)
        XCTAssertThrowsError(try e.recovered(manifest: duplicate))
        var fields = try XCTUnwrap(try decode(e.manifest).object)
        fields["DestinationWrites"] = .bool(false)
        XCTAssertThrowsError(try e.recovered(manifest: encode(.object(fields))))
        XCTAssertThrowsError(try e.recovered(manifest: replacing(e.manifest,
            at: ["OriginalCapturedMembersReplaced"], with: .bool(true))))
    }


    func testProduceRecoveredFullSourceCensusWithoutDestinationCalls() throws {
        let e = try evidence()
        let recovered = try e.recovered()
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: e.bundle, recoveredDefinitions: recovered)
        let plan = try AnyHeartNativeDefinitionPlan(catalog: catalog)
        let types: [AnyJSON] = catalog.types.map { type in
            .object(["sourceObjectID": .string(type.objectID), "typeKey": .string(type.typeKey),
                "recommendedLayout": type.recommendedLayout.map(AnyJSON.integer) ?? .null,
                "recommendedRelations": .array(type.recommendedRelations.map(AnyJSON.string)),
                "featuredRelations": .array(type.featuredRelations.map(AnyJSON.string)),
                "hiddenRelations": .array(type.hiddenRelations.map(AnyJSON.string)),
                "fileRelations": .array(type.fileRelations.map(AnyJSON.string)),
                "presentFields": .array(type.snapshot.details.keys.sorted().map(AnyJSON.string))])
        }
        let relations: [AnyJSON] = catalog.relations.map { relation in
            .object(["sourceObjectID": .string(relation.objectID), "relationKey": .string(relation.relationKey),
                "rawFormat": .integer(relation.rawFormat), "readonlyValue": relation.readonlyValue.map(AnyJSON.bool) ?? .null,
                "maximumCount": relation.maximumCount.map(AnyJSON.integer) ?? .null,
                "isReadonly": relation.snapshot.details["isReadonly"] ?? .null,
                "isArchived": relation.snapshot.details["isArchived"] ?? .null,
                "targetTypeKeys": .array(relation.targetTypeIDs.map { id in
                    .string(catalog.types.first { $0.objectID == id }?.typeKey ?? "UNRESOLVED:" + id)
                }),
                "presentFields": .array(relation.snapshot.details.keys.sorted().map(AnyJSON.string))])
        }
        let schemaIssues: [AnyJSON] = plan.issues.map {
            .object(["sourceObjectID": .string($0.sourceObjectID), "field": .string($0.field), "reason": .string($0.reason)])
        }
        let catalogIssues: [AnyJSON] = catalog.issues.map {
            .object(["sourceObjectID": .string($0.sourceObjectID), "field": .string($0.field), "kind": .string($0.kind.rawValue)])
        }
        let bundleIssues: [AnyJSON] = e.bundle.issues.map {
            .object(["sourceObjectID": $0.sourceID.map(AnyJSON.string) ?? .null, "field": .string($0.field), "code": .string($0.code)])
        }
        let objects: [AnyJSON] = e.bundle.objects.map {
            .object(["sourceObjectID": .string($0.sourceObjectID), "nativeType": .integer($0.nativeType),
                "uniqueKey": .string($0.uniqueKey), "objectTypes": .array($0.objectTypes.map(AnyJSON.string)),
                "presentDetailKeys": .array($0.details.keys.sorted().map(AnyJSON.string)),
                "blockKinds": .array($0.blocks.map { $0.contentKind.map(AnyJSON.string) ?? .null }),
                "snapshotIssueCount": .integer(Int64($0.issues.count))])
        }
        let value: AnyJSON = .object([
            "contract": .string("pinkha-historical156-recovered-full-census-v1"),
            "sourceManifestSHA256": .string(e.bundle.manifestSHA256),
            "recoveredManifestSHA256": .string(recovered.manifestSHA256),
            "catalogSHA256": .string(catalog.contentSHA256),
            "objects": .array(objects), "types": .array(types), "relations": .array(relations),
            "catalogIssues": .array(catalogIssues), "schemaIssues": .array(schemaIssues),
            "originalBundleIssues": .array(bundleIssues), "resolverUnmapped": .array(e.bundle.resolverUnmapped),
            "sourceGaps": .array(e.bundle.sourceGaps), "retainedOtherCollections": .array(e.bundle.retainedOtherCollections),
            "unmappedNativeCollections": .array((e.bundle.nativeStoreContext?.unmappedCollectionNames ?? []).map(AnyJSON.string)),
            "schemaItemCount": .integer(Int64(plan.schemaItems.count)),
            "definitionCoverageCount": .integer(Int64(plan.definitionCoverage.count)),
            "nativeCalls": .integer(0), "wholeSourceAdmission": .bool(false), "destinationWrites": .bool(false),
        ])
        guard let output = ProcessInfo.processInfo.environment["PINKHA_RECOVERED_DEFINITION_CENSUS"] else {
            throw Refusal.invalidFixture
        }
        let url = URL(fileURLWithPath: output)
        guard url.deletingLastPathComponent().resolvingSymlinksInPath().path == url.deletingLastPathComponent().path else {
            throw Refusal.invalidFixture
        }
        try encode(value).write(to: url, options: .withoutOverwriting)
        XCTAssertEqual(e.bundle.objects.count, 156)
        XCTAssertEqual(e.bundle.trees.count, 157)
        XCTAssertEqual(recovered.definitions.count, 7)
        XCTAssertFalse(catalog.permitsDestinationWrites)
        XCTAssertFalse(plan.permitsDestinationWrites)
        XCTAssertThrowsError(try plan.admittedSchemaItems())
    }

    private func rebinding(_ e: Evidence, exported: Data) throws -> (Data, Data) {
        let value = try decode(exported)
        var recovery = try XCTUnwrap(try decode(e.recovery).object)
        recovery["exportManifestSHA256"] = .string(AnyContentDigest.sha256(exported))
        recovery["descriptors"] = try XCTUnwrap(value["Descriptors"])
        let recoveryBytes = try encode(.object(recovery))
        var binding = try XCTUnwrap(try decode(e.manifest).object)
        binding["RegistryExportSHA256"] = .string(AnyContentDigest.sha256(exported))
        binding["RecoveryReceiptSHA256"] = .string(AnyContentDigest.sha256(recoveryBytes))
        return (try encode(.object(binding)), recoveryBytes)
    }


    func testPreservationArchiveRestoresEveryOriginalMemberAndRecoveredDescriptor() throws {
        let f = try preservationInput()
        let restored = try AnyHeartNativePreservationArchive.restore(f.archive.bytes, expected: f.archive.binding)
        XCTAssertEqual(restored.bundle.manifestBytes, f.evidence.bundle.manifestBytes)
        XCTAssertEqual(restored.bundle.objects.count, 156)
        XCTAssertEqual(restored.bundle.trees.count, 157)
        XCTAssertEqual(restored.bundle.nativeStoreContext?.headCensus?.sourceHeadIDs.count, 159)
        XCTAssertEqual(restored.originalMemberCount, f.evidence.bundle.verifiedMembers.count + 1)
        XCTAssertEqual(restored.recoveredMemberCount, 18)
        XCTAssertFalse(restored.grantsSourceSession)
        XCTAssertFalse(restored.restoresAnAccount)
        XCTAssertFalse(f.archive.permitsDestinationWrites)
        for member in f.evidence.bundle.verifiedMembers {
            XCTAssertEqual(try restored.capturedMemberData(member), try bytes(member.path, under: f.bundleRoot), member.path)
        }
        for member in f.recovered.verifiedMembers {
            XCTAssertEqual(try restored.recoveredMemberData(member), f.evidence.members[member.path], member.path)
        }
        let restoredRecovery = try XCTUnwrap(restored.recoveredDefinitions)
        XCTAssertEqual(restoredRecovery.originalProducerBytes, f.evidence.producer)
        XCTAssertEqual(try decode(restoredRecovery.originalProducerBytes)["status"], .string("FAIL"))
        XCTAssertTrue(restored.bundle.bundledDefinitions.isEmpty)
        XCTAssertEqual(restoredRecovery.definitions.count, 7)
        XCTAssertEqual(f.archive.sha256, AnyContentDigest.sha256(f.archive.bytes))
    }

    func testPreservationArchiveRefusesCorruptionTraversalBindingAndTrailingBytes() throws {
        let f = try preservationInput(), original = f.archive.bytes
        var corrupt = original; corrupt[corrupt.count - 1] ^= 1
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(corrupt, expected: f.archive.binding))
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(original.dropLast(), expected: f.archive.binding))
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(original + Data([0]), expected: f.archive.binding))
        for field in ["accountID", "spaceID", "captureManifestSHA256", "sourceWitnessSHA256", "recoveredManifestSHA256"] {
            let altered = try preservationHeader(original) {
                try replacing($0, at: [field], with: .string("different"))
            }
            XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(altered, expected: f.archive.binding), field)
        }
        let duplicate = try preservationHeader(original) {
            Data(#"{"contract":"duplicate","#.utf8) + $0.dropFirst()
        }
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(duplicate, expected: f.archive.binding))
        for path in ["../escape", "capture/foreign-member", "capture//empty", "/absolute"] {
            let altered = try preservationHeader(original) { bytes in
                var header = try XCTUnwrap(decode(bytes).object)
                var members = try XCTUnwrap(header["members"]?.array)
                var first = try XCTUnwrap(members[0].object)
                first["path"] = .string(path); members[0] = .object(first); header["members"] = .array(members)
                return try encode(.object(header))
            }
            XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(altered, expected: f.archive.binding), path)
        }
        var oversizeHeader = original
        let start = Data("PINKHA-HEART-SOURCE-1\u{0}".utf8).count
        oversizeHeader.replaceSubrange(start..<(start + 8), with: Data(repeating: 255, count: 8))
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive.restore(oversizeHeader, expected: f.archive.binding))
    }

    func testPreservationArchiveRefusesChangedCapturedOrRecoveredMemberBytes() throws {
        let f = try preservationInput()
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive(bundle: f.evidence.bundle, recovered: f.recovered,
            memberData: { try self.bytes($0.path, under: f.bundleRoot) + Data([0]) },
            recoveredMemberData: { try XCTUnwrap(f.evidence.members[$0.path]) }))
        XCTAssertThrowsError(try AnyHeartNativePreservationArchive(bundle: f.evidence.bundle, recovered: f.recovered,
            memberData: { try self.bytes($0.path, under: f.bundleRoot) },
            recoveredMemberData: { try XCTUnwrap(f.evidence.members[$0.path]) + Data([0]) }))
    }

    func testPreservationFull159HeadPlanKeepsNativeContentAndAllInactiveOriginals() throws {
        let f = try preservationInput()
        let composed = try AnyHeartNativeSourcePreservation(bundle: f.evidence.bundle,
            recoveredDefinitions: f.recovered, archive: f.archive)
        let workspace = try AnyTorahWorkspace(accountID: "preservation-component-account", spaceID: "preservation-component-space")
        let plan = try composed.preservationPlan(workspace: workspace, storeID: "preservation-component-store",
                                                 planID: String(repeating: "a", count: 64))
        XCTAssertEqual(composed.currentContent.pages.count, 2)
        XCTAssertEqual(composed.currentContent.items.count, 19)
        XCTAssertEqual(plan.items.count, 182)
        XCTAssertEqual(plan.coverage.count, 159)
        XCTAssertEqual(plan.source.sourceObjectIDs.count, 159)
        XCTAssertEqual(composed.records.count, 159)
        XCTAssertEqual(composed.uninstantiatedDefinitionIDs.count, 137)
        XCTAssertEqual(composed.preservedContextIDs.count, 4)
        XCTAssertFalse(composed.allImportedTypesUsable)
        XCTAssertFalse(composed.permitsWholeSourceAdmission)
        XCTAssertFalse(composed.changesDestinationACL)
        XCTAssertFalse(composed.sourceHistoryBecameTargetHistory)
        XCTAssertEqual(Set(composed.records.map { Data($0.sourceHeadID.utf8) }),
                       Set(try XCTUnwrap(f.evidence.bundle.nativeStoreContext?.headCensus).sourceHeadIDs.map { Data($0.utf8) }))
        let native = Dictionary(uniqueKeysWithValues: plan.items.map { ($0.sourceKey, $0) })
        for item in composed.currentContent.items { XCTAssertEqual(native[item.sourceKey], item) }
        let actual = Dictionary(uniqueKeysWithValues: plan.coverage.map { ($0.sourceObjectID, $0.disposition) })
        var canonical = 0, embedded = 0
        for entry in composed.currentContent.coverage {
            switch entry.disposition {
            case .canonicalProperty(let original):
                guard case .preservedCanonicalProperty(let retained, let keys) = actual[entry.sourceObjectID] else {
                    return XCTFail("Canonical native admission was replaced by a provenance-only row")
                }
                XCTAssertEqual(original, retained); XCTAssertEqual(keys.count, 1); canonical += 1
            case .embeddedOption(let property, let evidence, let hash):
                guard case .preservedEmbeddedOption(let keptProperty, let keptEvidence, let keptHash, let keys) = actual[entry.sourceObjectID] else {
                    return XCTFail("Embedded native option admission was replaced by a provenance-only row")
                }
                XCTAssertEqual(property, keptProperty); XCTAssertEqual(evidence, keptEvidence)
                XCTAssertEqual(hash, keptHash); XCTAssertEqual(keys.count, 1); embedded += 1
            default: break
            }
        }
        XCTAssertGreaterThan(canonical, 0)
        XCTAssertGreaterThan(embedded, 0)
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: f.evidence.bundle, recoveredDefinitions: f.recovered)
        XCTAssertThrowsError(try AnyHeartNativeDefinitionPlan(catalog: catalog).admittedSchemaItems())
        let restoredPlan = try AnyDestinationMigrationPlan.decode(encodePlan(plan))
        XCTAssertEqual(restoredPlan.canonicalBytes, plan.canonicalBytes)
        let roleCounts = Dictionary(grouping: composed.records, by: \.role).mapValues(\.count)
        XCTAssertEqual(roleCounts["active-current-content"], 2)
        XCTAssertEqual(roleCounts["source-context"], 4)
        XCTAssertEqual(roleCounts["original-space-settings"], 1)
        XCTAssertEqual(roleCounts["original-native-acl"], 1)
        XCTAssertEqual(roleCounts["original-empty-native-kv"], 1)
        if let output = ProcessInfo.processInfo.environment["PINKHA_PRESERVATION_PLAN_OUTPUT"] {
            let root = URL(fileURLWithPath: output, isDirectory: true)
            try f.archive.bytes.write(to: root.appendingPathComponent("source-preservation-file.pinkha-heart-source"),
                                      options: .withoutOverwriting)
            let proof: AnyJSON = .object([
                "contract": .string(AnyHeartNativeSourcePreservation.contract),
                "sourceManifestSHA256": .string(f.evidence.bundle.manifestSHA256),
                "recoveredManifestSHA256": .string(f.recovered.manifestSHA256),
                "archiveSHA256": .string(f.archive.sha256), "archiveBytes": .integer(Int64(f.archive.bytes.count)),
                "originalMemberCount": .integer(Int64(f.archive.originalMemberCount)),
                "recoveredMemberCount": .integer(Int64(f.archive.recoveredMemberCount)),
                "nativeHeads": .integer(159), "snapshotObjects": .integer(156),
                "operations": .integer(182), "currentContentOperations": .integer(19),
                "canonicalPropertiesRetained": .integer(Int64(canonical)),
                "embeddedOptionsRetained": .integer(Int64(embedded)),
                "allImportedTypesUsable": .bool(false), "sourceAdmission": .bool(false),
                "nativeCalls": .integer(0), "destinationWrites": .bool(false),
            ])
            try encode(proof).write(to: root.appendingPathComponent("source-preservation-component.json"),
                                    options: .withoutOverwriting)
        }
    }

    func testPreservationCoverageRejectsWritableShadowsDroppedRecordsAndChangedSourceOwnership() throws {
        let f = try preservationInput()
        let composed = try AnyHeartNativeSourcePreservation(bundle: f.evidence.bundle,
            recoveredDefinitions: f.recovered, archive: f.archive)
        let workspace = try AnyTorahWorkspace(accountID: "preservation-component-account", spaceID: "preservation-component-space")
        let plan = try composed.preservationPlan(workspace: workspace, storeID: "preservation-component-store",
                                                 planID: String(repeating: "b", count: 64))
        for entry in plan.coverage {
            let keys: [String]
            switch entry.disposition {
            case .preservedCanonicalProperty(_, let found), .preservedEmbeddedOption(_, _, _, let found): keys = found
            default: continue
            }
            let key = try XCTUnwrap(keys.first)
            let index = try XCTUnwrap(plan.items.firstIndex { $0.sourceKey == key })
            let old = plan.items[index]
            var writable = plan.items
            writable[index] = .init(sourceKey: old.sourceKey, sourceObjectID: old.sourceObjectID,
                operation: .propertyUpdate(
                    object: .mapped(sourceKey: composed.catalogObjectSourceKey, slot: .objectID, encoding: .rawID),
                    owner: .native("any"), patch: .literal(.object(["description": .string("forbidden shadow")]))))
            writable = writable.enumerated().sorted {
                $0.element.operation.phase == $1.element.operation.phase ? $0.offset < $1.offset :
                    $0.element.operation.phase < $1.element.operation.phase
            }.map(\.element)
            XCTAssertThrowsError(try AnyDestinationMigrationPlan(source: plan.source, workspace: workspace,
                storeID: plan.binding.storeID, planID: plan.binding.planID, coverage: plan.coverage, items: writable)) {
                XCTAssertEqual($0 as? AnyDestinationMigrationError,
                               .invalidPlan("preserved definition requires immutable records"))
            }
            var foreign = plan.items
            foreign[index] = .init(sourceKey: old.sourceKey, sourceObjectID: composed.currentContent.selection.objects[0].sourceObjectID,
                                   operation: old.operation)
            XCTAssertThrowsError(try AnyDestinationMigrationPlan(source: plan.source, workspace: workspace,
                storeID: plan.binding.storeID, planID: plan.binding.planID, coverage: plan.coverage, items: foreign))
            XCTAssertThrowsError(try AnyDestinationMigrationPlan(source: plan.source, workspace: workspace,
                storeID: plan.binding.storeID, planID: plan.binding.planID, coverage: plan.coverage,
                items: plan.items.filter { $0.sourceKey != key }))
        }
    }

    private struct PreservationInput {
        let evidence: Evidence
        let recovered: AnyHeartNativeRecoveredDefinitions
        let archive: AnyHeartNativePreservationArchive
        let bundleRoot: URL
    }
    private func preservationInput() throws -> PreservationInput {
        let e = try evidence(), recovered = try e.recovered()
        let root = URL(fileURLWithPath: try XCTUnwrap(ProcessInfo.processInfo.environment["PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE"]),
                       isDirectory: true).appendingPathComponent("bundle", isDirectory: true)
        let archive = try AnyHeartNativePreservationArchive(bundle: e.bundle, recovered: recovered,
            memberData: { try self.bytes($0.path, under: root) },
            recoveredMemberData: { try XCTUnwrap(e.members[$0.path]) })
        return .init(evidence: e, recovered: recovered, archive: archive, bundleRoot: root)
    }
    private func preservationHeader(_ data: Data, replace: (Data) throws -> Data) throws -> Data {
        let magic = Data("PINKHA-HEART-SOURCE-1\u{0}".utf8)
        var length: UInt64 = 0
        for value in data[magic.count..<(magic.count + 8)] { length = (length << 8) | UInt64(value) }
        let start = magic.count + 8, end = start + Int(length)
        let header = try replace(data.subdata(in: start..<end))
        var output = magic
        for shift in stride(from: 56, through: 0, by: -8) {
            output.append(UInt8((UInt64(header.count) >> UInt64(shift)) & 255))
        }
        output.append(header); output.append(data.subdata(in: end..<data.count))
        return output
    }
    private func encodePlan(_ value: AnyDestinationMigrationPlan) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }

    private func evidence() throws -> Evidence {
        let env = ProcessInfo.processInfo.environment
        guard let original = env["PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE"],
              let source = env["PINKHA_RECOVERED_DEFINITION_EVIDENCE"],
              let repo = env["PINKHA_RECOVERED_DEFINITION_REPOSITORY"] else {
            throw XCTSkip("Requires the retained historical156 source and qualified original-source registry recovery.")
        }
        let originalRoot = URL(fileURLWithPath: original, isDirectory: true)
        let proofRoot = URL(fileURLWithPath: source, isDirectory: true)
        let contextBytes = try bytes("fixture-context.json", under: originalRoot)
        XCTAssertEqual(AnyContentDigest.sha256(contextBytes), "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a")
        let context = try decode(contextBytes)
        guard context["customSchemaAcceptanceStatus"] == .string("FAIL"),
              context["readOnlyDiagnosticFixture"] == .bool(true),
              context["sourceAdmissionPromoted"] == .bool(false) else { throw Refusal.invalidFixture }
        let bundleRoot = originalRoot.appendingPathComponent("bundle", isDirectory: true)
        let manifestBytes = try bytes("manifest.json", under: bundleRoot)
        guard AnyContentDigest.sha256(manifestBytes) == "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4" else {
            throw Refusal.invalidFixture
        }
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifestBytes,
            sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try bytes($0.path, under: bundleRoot) }
        let binding = try bytes("historical156-binding.json", under: proofRoot)
        let producer = try bytes("Tools/AnyEngineValidation/native_file_peer/retained-scheduling-45492064232/producer-result.json",
                                 under: URL(fileURLWithPath: repo, isDirectory: true))
        let recovery = try bytes("receipt.json", under: proofRoot)
        let exported = try bytes("descriptors/export.json", under: proofRoot)
        guard AnyContentDigest.sha256(binding) == "3434ad74ec339f1d08818e2cb0bac069ec479c8e2f55e411754c63b31c6964b4",
              AnyContentDigest.sha256(producer) == "10dcb731241232985f626fcb8d084ec8a138c9e0aeffa46190f417d2da05c157",
              AnyContentDigest.sha256(recovery) == "b4561fa708141c463fce941ba4e266e42d12760d81cc63524d1cb96766ad7eb6",
              AnyContentDigest.sha256(exported) == "50458de19c0c9c8ae0bfc1b9cca1b6c5e29fbcf53d63bf32c5caabd0a3358ebb" else {
            throw Refusal.invalidFixture
        }
        var members: [String: Data] = [:]
        for row in try XCTUnwrap(try decode(exported)["Descriptors"]?.array) {
            for kind in ["Protobuf", "JSONView"] {
                let member = try XCTUnwrap(row[kind])
                let path = try XCTUnwrap(member["Path"]?.string)
                let data = try bytes(path, under: proofRoot.appendingPathComponent("descriptors", isDirectory: true))
                guard member["Bytes"] == .integer(Int64(data.count)),
                      AnyContentDigest.sha256(data) == member["SHA256"]?.string,
                      members.updateValue(data, forKey: path) == nil else { throw Refusal.invalidFixture }
            }
        }
        return .init(bundle: bundle, manifest: binding, producer: producer, recovery: recovery, exported: exported, members: members)
    }

    private func bytes(_ relative: String, under root: URL) throws -> Data {
        guard !relative.hasPrefix("/"), !relative.split(separator: "/").contains("..") else { throw Refusal.invalidFixture }
        let path = root.appendingPathComponent(relative)
        guard root.resolvingSymlinksInPath().path == root.path,
              path.resolvingSymlinksInPath().path == path.path else { throw Refusal.invalidFixture }
        let values = try path.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey])
        guard values.isRegularFile == true, values.isSymbolicLink != true,
              let count = values.fileSize, count > 0, count <= 4_194_304 else { throw Refusal.invalidFixture }
        let before = try FileManager.default.attributesOfItem(atPath: path.path)
        let data = try Data(contentsOf: path)
        let after = try FileManager.default.attributesOfItem(atPath: path.path)
        for key in [FileAttributeKey.systemNumber, .systemFileNumber, .size, .modificationDate, .posixPermissions] {
            guard (before[key] as? NSObject) == (after[key] as? NSObject) else { throw Refusal.invalidFixture }
        }
        guard data.count == count else { throw Refusal.invalidFixture }
        return data
    }

    private func replacing(_ data: Data, at path: [String], with value: AnyJSON) throws -> Data {
        func put(_ node: AnyJSON, _ keys: ArraySlice<String>) throws -> AnyJSON {
            guard let key = keys.first, var object = node.object else { throw Refusal.invalidFixture }
            object[key] = keys.count == 1 ? value : try put(XCTUnwrap(object[key]), keys.dropFirst())
            return .object(object)
        }
        return try encode(put(decode(data), path[...]))
    }
    private func decode(_ data: Data) throws -> AnyJSON { try JSONDecoder().decode(AnyJSON.self, from: data) }
    private func encode(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    private enum Refusal: Error { case invalidFixture }
}
#endif
