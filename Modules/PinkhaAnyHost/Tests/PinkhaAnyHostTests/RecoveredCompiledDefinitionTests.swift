#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyHost
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
