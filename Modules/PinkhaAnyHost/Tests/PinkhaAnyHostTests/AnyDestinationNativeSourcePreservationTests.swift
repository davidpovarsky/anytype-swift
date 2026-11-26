#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Actual explicit preservation of every historical native head, alongside the
/// supported current Pages. Unsupported type usability remains a separate gate.
final class AnyDestinationNativeSourcePreservationTests: XCTestCase, @unchecked Sendable {
    func testAllOriginalHeadsAndFileSurviveColdNativeReopen() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_DESTINATION_NATIVE_FIXTURE"],
              let workPath = env["PINKHA_DESTINATION_NATIVE_WORK"],
              let originalPath = env["PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE"],
              let recoveryPath = env["PINKHA_RECOVERED_DEFINITION_EVIDENCE"],
              let repositoryPath = env["PINKHA_RECOVERED_DEFINITION_REPOSITORY"],
              let phase = env["PINKHA_DESTINATION_NATIVE_PHASE"], ["execute", "reopen"].contains(phase) else {
            throw XCTSkip("Requires the pinned native preservation controller and original historical source.")
        }
        let fixture = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: URL(fileURLWithPath: fixturePath)))
        try require(fixture["binarySHA256"] == .string("8df7897ee6f45cdcef28c42fe025ad6f69062f15db779a660660cdc4016b00f7"))
        try require(fixture["sourceManifestSHA256"] == .string("12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c"))
        try require(fixture["phase"] == .string(phase == "execute" ? "execute" : "cold-offline"))
        let account = try XCTUnwrap(fixture["accountID"]?.string), space = try XCTUnwrap(fixture["spaceID"]?.string)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(fixture["baseURL"]?.string))), expectedAccountID: account)
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        let authorize: AnyDestinationAuthorization = {
            let member = try await client.requestJSON(method: "GET", path: ["v1", "spaces", space, "members", "me"])
            guard member["identity"] == .string(account), member["status"] == .string("active"),
                  member["permission"] == .string("owner") else { throw PreservationNativeFailure.unauthorized }
        }
        let originalRoot = URL(fileURLWithPath: originalPath, isDirectory: true)
        let recoveryRoot = URL(fileURLWithPath: recoveryPath, isDirectory: true)
        let repositoryRoot = URL(fileURLWithPath: repositoryPath, isDirectory: true)
        let original = try Self.originalCapture(at: originalRoot)
        let recovered = try Self.recoveredDefinitions(original, evidence: recoveryRoot, repository: repositoryRoot)
        let originalBundle = originalRoot.appendingPathComponent("bundle", isDirectory: true)
        let recoveredMembers = recoveryRoot.appendingPathComponent("descriptors", isDirectory: true)
        let archive = try AnyHeartNativePreservationArchive(bundle: original, recovered: recovered,
            memberData: { try Self.sourceBytes($0.path, under: originalBundle) },
            recoveredMemberData: { try Self.sourceBytes($0.path, under: recoveredMembers) })
        let preservation = try AnyHeartNativeSourcePreservation(bundle: original, recoveredDefinitions: recovered, archive: archive)
        let composition = preservation.currentContent
        try require(original.objects.count == 156 && original.trees.count == 157 && preservation.records.count == 159)
        try require(composition.pages.count == 2 && composition.items.count == 19)
        try require(preservation.uninstantiatedDefinitionIDs.count == 137 && preservation.preservedContextIDs.count == 4)
        try require(!preservation.allImportedTypesUsable && !preservation.permitsWholeSourceAdmission &&
                    !preservation.changesDestinationACL && !preservation.sourceHistoryBecameTargetHistory)
        try require(archive.originalMemberCount == 314 && archive.recoveredMemberCount == 18 &&
                    archive.bytes.count == 1_634_696 &&
                    archive.sha256 == "5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463")
        XCTAssertThrowsError(try AnyHeartNativeDefinitionPlan(catalog: .init(bundle: original,
            recoveredDefinitions: recovered)).admittedSchemaItems())
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let planURL = work.appendingPathComponent("source-preservation-plan.json")
        let journal = work.appendingPathComponent("journal", isDirectory: true)
        let payloadURL = work.appendingPathComponent("original-source.pinkha-heart-source")
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let definitions = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace, authorize: authorize)
        let plan: AnyDestinationMigrationPlan
        let interruptedPlanSHA256 = fixture["interruptedPlanSHA256"]?.string
        if phase == "execute" && interruptedPlanSHA256 == nil {
            try require(!FileManager.default.fileExists(atPath: planURL.path))
            try FileManager.default.createDirectory(at: journal, withIntermediateDirectories: false,
                                                   attributes: [.posixPermissions: 0o700])
            plan = try preservation.preservationPlan(workspace: workspace, storeID: definitions.capabilities.storeID,
                planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)))
            try encoder.encode(plan).write(to: planURL, options: .withoutOverwriting)
            try archive.bytes.write(to: payloadURL, options: .withoutOverwriting)
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: payloadURL.path)
        } else {
            let retainedPlanBytes = try Self.sourceBytes(planURL.lastPathComponent, under: work)
            if phase == "execute" {
                try require(interruptedPlanSHA256 == AnyContentDigest.sha256(retainedPlanBytes))
            }
            plan = try AnyDestinationMigrationPlan.decode(retainedPlanBytes)
            let same = try preservation.preservationPlan(workspace: workspace, storeID: definitions.capabilities.storeID,
                                                         planID: plan.binding.planID)
            try require(same.canonicalBytes == plan.canonicalBytes)
        }
        try require(plan.items.count == 182 && plan.coverage.count == 159 && plan.binding.workspace == workspace)
        try require(try Self.sourceBytes(payloadURL.lastPathComponent, under: work) == archive.bytes)
        // This fixture is an immutable historical capture. Authenticate all original
        // members at phase boundaries, then bind every callback to those exact bytes
        // through the independently reconstructed archive. Native account/lease/ACL
        // authorization still executes around every native request below.
        try Self.requireOriginalBytes(original, root: originalRoot)
        try Self.requireRecoveryBytes(recovered, evidence: recoveryRoot, repository: repositoryRoot)
        let source = plan.source
        let verifySource: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { candidate in
            guard candidate == source, candidate.semanticPlanSHA256 == preservation.contentSHA256,
                  candidate.captureManifestSHA256 == original.manifestSHA256 else {
                throw AnyDestinationMigrationError.changedSource
            }
            try Task.checkCancellation()
            guard try Self.sourceBytes(payloadURL.lastPathComponent, under: work) == archive.bytes else {
                throw AnyDestinationMigrationError.changedSource
            }
        }
        let payloads: @Sendable (String) async throws -> URL = { key in
            guard Data(key.utf8) == Data(preservation.archiveItemSourceKey.utf8),
                  try Self.sourceBytes(payloadURL.lastPathComponent, under: work) == archive.bytes else {
                throw PreservationNativeFailure.unexpectedPayload
            }
            return payloadURL
        }
        func stage(_ name: String) throws {
            try Data(name.utf8).write(to: work.appendingPathComponent("current-native-stage.txt"), options: .atomic)
        }
        try stage(phase + ":executor")
        let executor = AnyDestinationMigrationExecutor(client: client, journalDirectory: journal)
        let progress = try await executor.execute(plan: plan, payloads: payloads, verifySource: verifySource, authorize: authorize)
        try require(progress.allItemsReconciled && progress.mappings.count == 182)
        try stage(phase + ":native-comparison")
        let verified = try await AnyDestinationMigrationVerifier(client: client).verify(plan: plan, progress: progress,
            verifySource: verifySource, authorize: authorize)
        try require(verified.comparedOperationCount == 182 && verified.files.count == 1)
        let repeated = try await executor.execute(plan: plan, payloads: payloads, verifySource: verifySource, authorize: authorize)
        try require(encoder.encode(progress.mappings) == encoder.encode(repeated.mappings))
        try stage(phase + ":catalog-native-readback")
        let typeID = try XCTUnwrap(progress.mappings.first { $0.sourceKey == preservation.catalogTypeSourceKey }?.objectID)
        let catalogID = try XCTUnwrap(progress.mappings.first { $0.sourceKey == preservation.catalogObjectSourceKey }?.objectID)
        let fileID = try XCTUnwrap(progress.mappings.first { $0.sourceKey == preservation.archiveItemSourceKey }?.fileID)
        let dataset = try AnyPreparedImmutableRecordIntent.ownedDataset(ownerTypeID: typeID,
                                                                         key: AnyHeartNativeSourcePreservation.datasetKey)
        let response = try await client.requestJSON(method: "POST", path: ["v1", "spaces", space, "query"],
            body: .object(["objectId": .string(catalogID), "dataset": .string(dataset),
                "sort": .array([.string("id")]), "limit": .integer(200), "includeTotal": .bool(true)]),
            maximumResponseBytes: 8 << 20, authorize: authorize)
        let rows = try XCTUnwrap(response["records"]?.array)
        try require(response["total"] == .integer(159) && response["hasNext"] == .bool(false) && rows.count == 159)
        let actualIDs = rows.compactMap { $0["sourceHeadID"]?.string }.map { Data($0.utf8) }
        try require(actualIDs.count == 159 && Set(actualIDs).count == 159 &&
                    Set(actualIDs) == Set(preservation.records.map { Data($0.sourceHeadID.utf8) }))
        let snapshots = Dictionary(uniqueKeysWithValues: original.objects.map { (Data($0.sourceObjectID.utf8), $0) })
        let archiveURI = try AnyNativeFileReference(spaceID: space, fileID: fileID).uri
        for sourceRecord in preservation.records {
            let found = rows.filter { $0["sourceHeadID"]?.string.map({ Data($0.utf8) }) == Data(sourceRecord.sourceHeadID.utf8) }
            try require(found.count == 1)
            let row = found[0]
            let mapping = try XCTUnwrap(progress.mappings.first { $0.sourceKey == sourceRecord.sourceKey })
            try require(row["id"]?.string == mapping.recordIDs.first &&
                        row["sourceRole"] == .string(sourceRecord.role) &&
                        row["archiveURI"] == .string(archiveURI) &&
                        row["sourceCaptureManifestSHA256"] == .string(original.manifestSHA256) &&
                        row["sourceRecoveryManifestSHA256"] == .string(recovered.manifestSHA256) &&
                        row["importedBy"] == .string(account))
            if let snapshot = snapshots[Data(sourceRecord.sourceHeadID.utf8)] {
                try require(row["snapshotPresent"] == .bool(true) &&
                    row["sourceSnapshotBase64"]?.string.flatMap({ Data(base64Encoded: $0) }) == snapshot.protobufBytes &&
                    row["sourceViewJSON"]?.string.map({ Data($0.utf8) }) == snapshot.jsonViewBytes &&
                    row["sourceSnapshotSHA256"] == .string(snapshot.snapshotSHA256) &&
                    row["sourceViewSHA256"] == .string(snapshot.viewSHA256))
            } else {
                try require(row["snapshotPresent"] == .bool(false) && row["sourceSnapshotBase64"] == .string("") &&
                            row["sourceViewJSON"] == .string(""))
            }
        }
        // The production verifier independently bound every immutable native
        // creator/time stamp to its exact signed change, history and RecordAt.
        try stage(phase + ":file-download-restore")
        let download = work.appendingPathComponent(phase + "-downloaded-source.pinkha-heart-source")
        let downloadedSHA = try await client.downloadFileContent(spaceID: space, fileID: fileID,
            size: Int64(archive.bytes.count), mime: AnyHeartNativePreservationArchive.mimeType,
            to: download, expectedSHA256: archive.sha256, authorize: authorize)
        let downloaded = try Self.sourceBytes(download.lastPathComponent, under: work)
        try require(downloadedSHA == archive.sha256 && downloaded == archive.bytes)
        let restored = try AnyHeartNativePreservationArchive.restore(downloaded, expected: archive.binding)
        try require(restored.bundle.manifestBytes == original.manifestBytes &&
                    restored.recoveredDefinitions.manifestBytes == recovered.manifestBytes &&
                    restored.originalMemberCount == 314 && restored.recoveredMemberCount == 18 &&
                    !restored.grantsSourceSession && !restored.restoresAnAccount)
        for member in original.verifiedMembers {
            try require(restored.capturedMemberData(member) == Self.sourceBytes(member.path, under: originalBundle))
        }
        for member in recovered.verifiedMembers {
            try require(restored.recoveredMemberData(member) == Self.sourceBytes(member.path, under: recoveredMembers))
        }
        try stage(phase + ":actual-links")
        let links = try await verifyOriginalLink(composition: composition, client: client, space: space,
                                                mappings: progress.mappings, authorize: authorize)
        let proof: AnyJSON = .object([
            "contract": .string("pinkha-historical156-full-source-native-preservation-v1"),
            "sourceManifestSHA256": .string(original.manifestSHA256),
            "recoveryManifestSHA256": .string(recovered.manifestSHA256),
            "preservationContentSHA256": .string(preservation.contentSHA256),
            "archiveSHA256": .string(archive.sha256), "archiveBytes": .integer(Int64(downloaded.count)),
            "capturedMembersRestored": .integer(314), "recoveredMembersRestored": .integer(18),
            "snapshotObjects": .integer(156), "nativeHeads": .integer(159),
            "preparedOperations": .integer(182), "actualCatalogRows": .array(rows),
            "actualLinkIndex": links, "fileID": .string(fileID),
            "uninstantiatedDefinitionIDs": .array(preservation.uninstantiatedDefinitionIDs.map(AnyJSON.string)),
            "preservedContextIDs": .array(preservation.preservedContextIDs.map(AnyJSON.string)),
            "historicalAuthorIsDestinationSigner": .bool(false), "sourceHistoryBecameTargetHistory": .bool(false),
            "destinationACLChanged": .bool(false), "allImportedTypesUsable": .bool(false),
            "sourceAdmissionPromoted": .bool(false), "wholeSpaceSemanticMigration": .bool(false)
        ])
        let bytes = try encoder.encode(proof), mappings = try encoder.encode(progress.mappings)
        if phase == "execute" {
            try mappings.write(to: work.appendingPathComponent("execute-mappings.json"), options: .withoutOverwriting)
        } else {
            try require(bytes == Data(contentsOf: work.appendingPathComponent("execute-content.json")))
            try require(mappings == Data(contentsOf: work.appendingPathComponent("execute-mappings.json")))
            let warm = try JSONDecoder().decode(AnyDestinationContentVerification.self,
                from: Data(contentsOf: work.appendingPathComponent("execute-verification.json")))
            try require(verified.observations == warm.observations)
            let currentFile = try XCTUnwrap(verified.files.first), priorFile = try XCTUnwrap(warm.files.first)
            try require(currentFile.fileID == priorFile.fileID && currentFile.byteCount == priorFile.byteCount &&
                        currentFile.plaintextSHA256 == priorFile.plaintextSHA256 && currentFile.cached && priorFile.cached)
            try require(fixture["outboundDeniedByOS"] == .bool(true) && fixture["networkPeerCount"] == .integer(0))
        }
        try bytes.write(to: work.appendingPathComponent(phase + "-content.json"), options: .withoutOverwriting)
        try encoder.encode(verified).write(to: work.appendingPathComponent(phase + "-verification.json"), options: .withoutOverwriting)
        try Self.requireOriginalBytes(original, root: originalRoot)
        try Self.requireRecoveryBytes(recovered, evidence: recoveryRoot, repository: repositoryRoot)
        try stage(phase + ":complete")
        print("NATIVE_FULL_SOURCE_PRESERVATION prepared_operations=182 original_pages=2 native_heads=159 snapshot_objects=156 restored_members=332 source_admission=false all_imported_types_usable=false phase=" + phase)
    }

    private static func recoveredDefinitions(_ original: AnyHeartNativeSpaceBundle, evidence: URL,
        repository: URL) throws -> AnyHeartNativeRecoveredDefinitions {
        let binding = try sourceBytes("historical156-binding.json", under: evidence)
        let producer = try sourceBytes("Tools/AnyEngineValidation/native_file_peer/retained-scheduling-45492064232/producer-result.json",
                                       under: repository)
        let recovery = try sourceBytes("receipt.json", under: evidence)
        let exported = try sourceBytes("descriptors/export.json", under: evidence)
        guard AnyContentDigest.sha256(binding) == "3434ad74ec339f1d08818e2cb0bac069ec479c8e2f55e411754c63b31c6964b4",
              AnyContentDigest.sha256(producer) == "10dcb731241232985f626fcb8d084ec8a138c9e0aeffa46190f417d2da05c157",
              AnyContentDigest.sha256(recovery) == "b4561fa708141c463fce941ba4e266e42d12760d81cc63524d1cb96766ad7eb6",
              AnyContentDigest.sha256(exported) == "50458de19c0c9c8ae0bfc1b9cca1b6c5e29fbcf53d63bf32c5caabd0a3358ebb" else {
            throw PreservationNativeFailure.changedSource
        }
        return try .init(bundle: original, manifest: binding,
            expectedManifestSHA256: "3434ad74ec339f1d08818e2cb0bac069ec479c8e2f55e411754c63b31c6964b4",
            originalProducer: producer, recoveryReceipt: recovery, registryExport: exported) {
                try sourceBytes($0.path, under: evidence.appendingPathComponent("descriptors", isDirectory: true))
            }
    }
    private static func requireRecoveryBytes(_ recovered: AnyHeartNativeRecoveredDefinitions, evidence: URL,
                                            repository: URL) throws {
        guard try sourceBytes("historical156-binding.json", under: evidence) == recovered.manifestBytes,
              try sourceBytes("receipt.json", under: evidence) == recovered.recoveryReceiptBytes,
              try sourceBytes("descriptors/export.json", under: evidence) == recovered.exportManifestBytes,
              try sourceBytes("Tools/AnyEngineValidation/native_file_peer/retained-scheduling-45492064232/producer-result.json",
                  under: repository) == recovered.originalProducerBytes else {
            throw AnyDestinationMigrationError.changedSource
        }
        for member in recovered.verifiedMembers {
            let bytes = try sourceBytes(member.path, under: evidence.appendingPathComponent("descriptors", isDirectory: true))
            guard bytes.count == member.byteCount, AnyContentDigest.sha256(bytes) == member.sha256 else {
                throw AnyDestinationMigrationError.changedSource
            }
        }
    }
    private static func requireOriginalBytes(_ original: AnyHeartNativeSpaceBundle, root: URL) throws {
        guard AnyContentDigest.sha256(try sourceBytes("fixture-context.json", under: root)) ==
                "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a",
              AnyContentDigest.sha256(try sourceBytes("bundle/manifest.json", under: root)) == original.manifestSHA256 else {
            throw AnyDestinationMigrationError.changedSource
        }
        let directory = root.appendingPathComponent("bundle", isDirectory: true)
        for member in original.verifiedMembers {
            let bytes = try sourceBytes(member.path, under: directory)
            guard bytes.count == member.byteCount, AnyContentDigest.sha256(bytes) == member.sha256 else {
                throw AnyDestinationMigrationError.changedSource
            }
        }
    }

    private func verifyOriginalLink(composition: AnyHeartNativeContentComposition, client: AnyHTTPClient,
        space: String, mappings: [AnyDestinationMigrationMapping], authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        let a = try XCTUnwrap(composition.pages.first { $0.layout.title == "Owned typed document A" })
        let b = try XCTUnwrap(composition.pages.first { $0.layout.title == "Owned typed document B" })
        let aID = try XCTUnwrap(mappings.first { $0.sourceKey == a.sourceKey }?.objectID)
        let bID = try XCTUnwrap(mappings.first { $0.sourceKey == b.sourceKey }?.objectID)
        try require(aID != bID)
        let property = try XCTUnwrap(composition.definitions.properties.first { $0.relation.name == "Owned source object" })
        let propertyID = try XCTUnwrap(mappings.first { $0.sourceKey == property.sourceKey }?.recordIDs.first)
        // Original Any41c API declares bool,truncated with omitempty:
        // absence is false; null, strings and other non-Bool values refuse.
        func notTruncated(_ response: AnyJSON) -> Bool {
            response["truncated"] == nil || response["truncated"] == .bool(false)
        }
        let deadline = ContinuousClock.now + .seconds(30)
        repeat {
            let empty = try await client.requestJSON(method: "GET", path: ["v1", "spaces", space, "objects", aID, "links"],
                query: ["kind": "relation", "prop": propertyID, "limit": "2"], authorize: authorize)
            let forward = try await client.requestJSON(method: "GET", path: ["v1", "spaces", space, "objects", bID, "links"],
                query: ["kind": "relation", "prop": propertyID, "limit": "2"], authorize: authorize)
            let reverse = try await client.requestJSON(method: "GET", path: ["v1", "spaces", space, "objects", aID, "backlinks"],
                query: ["kind": "relation", "limit": "2"], authorize: authorize)
            func matches(_ edge: AnyJSON) -> Bool {
                edge["kind"] == .string("relation") && edge["source"]?["spaceId"] == .string(space) &&
                edge["source"]?["objectId"] == .string(bID) && edge["source"]?["dataset"] == .string("prop") &&
                edge["source"]?["recordId"] == .string(propertyID) && edge["target"]?["objectId"] == .string(aID) &&
                edge["target"]?["uri"] == .string("any://o/" + space + "/" + aID)
            }
            if empty["links"]?.array?.isEmpty == true,
               let edges = forward["links"]?.array, edges.count == 1, matches(edges[0]),
               let back = reverse["object"]?.array, back.count == 1, matches(back[0]),
               reverse["parts"]?.array?.isEmpty == true,
               notTruncated(empty), notTruncated(forward), notTruncated(reverse) {
                return .object(["emptySource": empty, "forward": forward, "reverse": reverse])
            }
            try Task.checkCancellation()
            if ContinuousClock.now < deadline { try await Task.sleep(for: .milliseconds(100)) }
        } while ContinuousClock.now < deadline
        throw PreservationNativeFailure.assertion
    }
    private static func sourceBytes(_ relative: String, under directory: URL) throws -> Data {
        let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
        let root = directory.standardizedFileURL
        guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
              parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }),
              root.path == directory.path, root.resolvingSymlinksInPath().path == root.path else {
            throw PreservationNativeFailure.changedSource
        }
        let manager = FileManager.default
        guard try manager.attributesOfItem(atPath: root.path)[.type] as? FileAttributeType == .typeDirectory else {
            throw PreservationNativeFailure.changedSource
        }
        var file = root
        for (index, part) in parts.enumerated() {
            file.appendPathComponent(String(part))
            let attributes = try manager.attributesOfItem(atPath: file.path)
            let expected: FileAttributeType = index == parts.count - 1 ? .typeRegular : .typeDirectory
            guard attributes[.type] as? FileAttributeType == expected else {
                throw PreservationNativeFailure.changedSource
            }
        }
        func identity() throws -> (UInt64, UInt64, UInt64, Date) {
            let attributes = try manager.attributesOfItem(atPath: file.path)
            guard attributes[.type] as? FileAttributeType == .typeRegular,
                  let inode = attributes[.systemFileNumber] as? NSNumber,
                  let device = attributes[.systemNumber] as? NSNumber,
                  let size = attributes[.size] as? NSNumber,
                  let links = attributes[.referenceCount] as? NSNumber, links.uint64Value == 1,
                  let modified = attributes[.modificationDate] as? Date,
                  size.uint64Value <= 32 * 1024 * 1024 else {
                throw PreservationNativeFailure.changedSource
            }
            return (device.uint64Value, inode.uint64Value, size.uint64Value, modified)
        }
        let before = try identity(), bytes = try Data(contentsOf: file), after = try identity()
        guard before == after, UInt64(bytes.count) == before.2 else {
            throw PreservationNativeFailure.changedSource
        }
        return bytes
    }
    private static func originalCapture(at root: URL) throws -> AnyHeartNativeSpaceBundle {
        let contextBytes = try sourceBytes("fixture-context.json", under: root)
        guard AnyContentDigest.sha256(contextBytes) == "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a" else { throw PreservationNativeFailure.changedSource }
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        guard context["customSchemaAcceptanceStatus"] == .string("FAIL"), context["readOnlyDiagnosticFixture"] == .bool(true),
              context["sourceAdmissionPromoted"] == .bool(false) else { throw PreservationNativeFailure.changedSource }
        let directory = root.appendingPathComponent("bundle", isDirectory: true)
        let manifest = try sourceBytes("manifest.json", under: directory)
        guard AnyContentDigest.sha256(manifest) == "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4" else { throw PreservationNativeFailure.changedSource }
        return try .init(manifest: manifest, sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try sourceBytes($0.path, under: directory) }
    }
    private func require(_ value: @autoclosure () throws -> Bool) throws {
        guard try value() else { throw PreservationNativeFailure.assertion }
    }
}
private enum PreservationNativeFailure: Error { case unauthorized, unexpectedPayload, changedSource, assertion }
#endif
