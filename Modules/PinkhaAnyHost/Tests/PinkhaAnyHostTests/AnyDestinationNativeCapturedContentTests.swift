#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Actual current content of both original captured Pages. The full original
/// source blockers remain separate and cannot be promoted by this component.
final class AnyDestinationNativeCapturedContentTests: XCTestCase, @unchecked Sendable {
    func testBothOriginalPagesExecuteAndCompareAfterColdNativeReopen() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_DESTINATION_NATIVE_FIXTURE"],
              let workPath = env["PINKHA_DESTINATION_NATIVE_WORK"],
              let originalPath = env["PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE"],
              let phase = env["PINKHA_DESTINATION_NATIVE_PHASE"], ["execute", "reopen"].contains(phase) else {
            throw XCTSkip("Requires the exact native immutable-record controller and original captured source.")
        }
        let fixture = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: URL(fileURLWithPath: fixturePath)))
        try require(fixture["binarySHA256"] == .string("6ff900f1354f11044d8619e3ce1c0a20673d0608fd4bd3b50ff0bd4bb850f9ba"))
        try require(fixture["sourceManifestSHA256"] == .string("39f4ee580af8f2897b2f794f872327b7391828a3a57355cf0235dae7d1626e72"))
        try require(fixture["phase"] == .string(phase == "execute" ? "execute" : "cold-offline"))
        let account = try XCTUnwrap(fixture["accountID"]?.string), space = try XCTUnwrap(fixture["spaceID"]?.string)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: XCTUnwrap(fixture["baseURL"]?.string))), expectedAccountID: account)
        let workspace = try AnyTorahWorkspace(accountID: account, spaceID: space)
        let authorize: AnyDestinationAuthorization = {
            let member = try await client.requestJSON(method: "GET", path: ["v1", "spaces", space, "members", "me"])
            guard member["identity"] == .string(account), member["status"] == .string("active"),
                  member["permission"] == .string("owner") else { throw CapturedContentNativeFailure.unauthorized }
        }
        let originalRoot = URL(fileURLWithPath: originalPath, isDirectory: true)
        let original = try Self.originalCapture(at: originalRoot)
        let composition = try AnyHeartNativeContentComposition(bundle: original)
        try require(original.objects.count == 156 && original.trees.count == 157)
        try require(composition.pages.count == 2 && composition.selection.executedSourceObjectIDs.count == 15)
        try require(composition.selection.remainingSourceObjectIDs.count == 144 &&
                    composition.selection.remainingDefinitionObjectIDs.count == 137)
        try require(composition.selection.retainedAbsentDeclarations.count == 58 &&
                    composition.selection.retainedCompiledDefinitionIDs.count == 7 && !composition.permitsWholeSourceAdmission)
        let originalDefinitions = try AnyHeartNativeDefinitionPlan(catalog: .init(bundle: original))
        XCTAssertThrowsError(try originalDefinitions.admittedSchemaItems())
        for page in composition.pages { XCTAssertThrowsError(try page.admittedCurrentItems()) }
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let planURL = work.appendingPathComponent("captured-content-plan.json")
        let journal = work.appendingPathComponent("journal", isDirectory: true)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let definitions = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace, authorize: authorize)
        let plan: AnyDestinationMigrationPlan
        if phase == "execute" {
            try require(!FileManager.default.fileExists(atPath: planURL.path))
            try FileManager.default.createDirectory(at: journal, withIntermediateDirectories: false,
                                                   attributes: [.posixPermissions: 0o700])
            plan = try composition.currentContentPlan(workspace: workspace, storeID: definitions.capabilities.storeID,
                planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)))
            try encoder.encode(plan).write(to: planURL, options: .withoutOverwriting)
        } else {
            plan = try AnyDestinationMigrationPlan.decode(Data(contentsOf: planURL))
            let same = try composition.currentContentPlan(workspace: workspace, storeID: definitions.capabilities.storeID,
                                                         planID: plan.binding.planID)
            try require(same.canonicalBytes == plan.canonicalBytes)
        }
        try require(plan.items.count == 19 && plan.coverage.count == 15 && plan.binding.workspace == workspace)
        let source = plan.source
        let verifySource: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { candidate in
            guard candidate == source, candidate.semanticPlanSHA256 == composition.contentSHA256,
                  candidate.captureManifestSHA256 == original.manifestSHA256 else {
                throw AnyDestinationMigrationError.changedSource
            }
            // Rehash every original member at every admission. The reader's
            // immutable parsed values need not be decoded hundreds of times.
            try Self.requireOriginalBytes(original, root: originalRoot)
        }
        func stage(_ name: String) throws {
            try Data(name.utf8).write(to: work.appendingPathComponent("current-native-stage.txt"), options: .atomic)
        }
        try stage(phase + ":executor")
        let executor = AnyDestinationMigrationExecutor(client: client, journalDirectory: journal)
        let progress = try await executor.execute(plan: plan,
            payloads: { _ in throw CapturedContentNativeFailure.unexpectedPayload },
            verifySource: verifySource, authorize: authorize)
        try require(progress.allItemsReconciled && progress.mappings.count == 19)
        try stage(phase + ":native-comparison")
        let verified = try await AnyDestinationMigrationVerifier(client: client).verify(plan: plan, progress: progress,
            verifySource: verifySource, authorize: authorize)
        try require(verified.comparedOperationCount == 19 && verified.files.isEmpty)
        let repeated = try await executor.execute(plan: plan,
            payloads: { _ in throw CapturedContentNativeFailure.unexpectedPayload },
            verifySource: verifySource, authorize: authorize)
        try require(encoder.encode(progress.mappings) == encoder.encode(repeated.mappings))
        try stage(phase + ":immutable-originals")
        var facts: [AnyJSON] = []
        for (index, value) in progress.verificationIntents.enumerated() {
            guard case .immutableRecord(let intent) = value else { continue }
            let item = plan.items[index]
            let snapshot = try XCTUnwrap(original.objects.first { $0.sourceObjectID == item.sourceObjectID })
            let response = try await client.requestJSON(method: "POST", path: ["v1", "spaces", space, "query"],
                body: .object(["objectId": .string(intent.objectID), "dataset": .string(intent.schema.dataset),
                               "limit": .integer(2), "includeTotal": .bool(true)]), authorize: authorize)
            try require(response["total"] == .integer(1) && response["hasNext"] == .bool(false) &&
                        response["records"]?.array?.count == 1)
            let row = try XCTUnwrap(response["records"]?.array?.first)
            try require(row["id"]?.string == progress.mappings[index].recordIDs.first)
            try require(row["sourceObject"] == .string(snapshot.sourceObjectID) &&
                        row["sourceSnapshotBase64"]?.string.flatMap({ Data(base64Encoded: $0) }) == snapshot.protobufBytes &&
                        row["sourceViewJSON"]?.string.map({ Data($0.utf8) }) == snapshot.jsonViewBytes &&
                        row["sourceSnapshotSHA256"] == .string(snapshot.snapshotSHA256) &&
                        row["sourceViewSHA256"] == .string(snapshot.viewSHA256))
            try require(row["importedBy"] == .string(account))
            // Production comparison already bound both native stamps to the
            // exact signed creation's noncoalesced history and RecordAt.
            facts.append(row)
        }
        try require(facts.count == 2)
        try stage(phase + ":actual-links")
        let links = try await verifyOriginalLink(composition: composition, client: client, space: space,
                                                mappings: progress.mappings, authorize: authorize)
        let proof: AnyJSON = .object([
            "contract": .string("pinkha-original-captured-current-content-native-v1"),
            "sourceManifestSHA256": .string(original.manifestSHA256),
            "currentContentSHA256": .string(composition.contentSHA256),
            "actualImmutableRows": .array(facts), "actualLinkIndex": links,
            "sourceObjectIDsExecuted": .array(composition.selection.executedSourceObjectIDs.map(AnyJSON.string)),
            "remainingSourceObjectIDs": .array(composition.selection.remainingSourceObjectIDs.map(AnyJSON.string)),
            "remainingDefinitionObjectIDs": .array(composition.selection.remainingDefinitionObjectIDs.map(AnyJSON.string)),
            "retainedCompiledDefinitionIDs": .array(composition.selection.retainedCompiledDefinitionIDs.map(AnyJSON.string)),
            "historicalAuthorIsDestinationSigner": .bool(false),
            "sourceAdmissionPromoted": .bool(false), "wholeSpaceMigration": .bool(false)
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
            try require(fixture["outboundDeniedByOS"] == .bool(true) && fixture["networkPeerCount"] == .integer(0))
        }
        try bytes.write(to: work.appendingPathComponent(phase + "-content.json"), options: .withoutOverwriting)
        try encoder.encode(verified).write(to: work.appendingPathComponent(phase + "-verification.json"), options: .withoutOverwriting)
        try Self.requireOriginalBytes(original, root: originalRoot)
        try stage(phase + ":complete")
        print("NATIVE_CAPTURED_CURRENT_CONTENT prepared_operations=19 original_pages=2 immutable_rows=2 source_ids=15 remaining_heads=144 source_admission=false whole_space_migration=false phase=" + phase)
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
        throw CapturedContentNativeFailure.assertion
    }
    private static func sourceBytes(_ relative: String, under directory: URL) throws -> Data {
        let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
        let root = directory.standardizedFileURL
        guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
              parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }),
              root.path == directory.path, root.resolvingSymlinksInPath().path == root.path else {
            throw CapturedContentNativeFailure.changedSource
        }
        let manager = FileManager.default
        guard try manager.attributesOfItem(atPath: root.path)[.type] as? FileAttributeType == .typeDirectory else {
            throw CapturedContentNativeFailure.changedSource
        }
        var file = root
        for (index, part) in parts.enumerated() {
            file.appendPathComponent(String(part))
            let attributes = try manager.attributesOfItem(atPath: file.path)
            let expected: FileAttributeType = index == parts.count - 1 ? .typeRegular : .typeDirectory
            guard attributes[.type] as? FileAttributeType == expected else {
                throw CapturedContentNativeFailure.changedSource
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
                throw CapturedContentNativeFailure.changedSource
            }
            return (device.uint64Value, inode.uint64Value, size.uint64Value, modified)
        }
        let before = try identity(), bytes = try Data(contentsOf: file), after = try identity()
        guard before == after, UInt64(bytes.count) == before.2 else {
            throw CapturedContentNativeFailure.changedSource
        }
        return bytes
    }
    private static func originalCapture(at root: URL) throws -> AnyHeartNativeSpaceBundle {
        let contextBytes = try sourceBytes("fixture-context.json", under: root)
        guard AnyContentDigest.sha256(contextBytes) == "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a" else { throw CapturedContentNativeFailure.changedSource }
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        guard context["customSchemaAcceptanceStatus"] == .string("FAIL"), context["readOnlyDiagnosticFixture"] == .bool(true),
              context["sourceAdmissionPromoted"] == .bool(false) else { throw CapturedContentNativeFailure.changedSource }
        let directory = root.appendingPathComponent("bundle", isDirectory: true)
        let manifest = try sourceBytes("manifest.json", under: directory)
        guard AnyContentDigest.sha256(manifest) == "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4" else { throw CapturedContentNativeFailure.changedSource }
        return try .init(manifest: manifest, sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try sourceBytes($0.path, under: directory) }
    }
    private func require(_ value: @autoclosure () throws -> Bool) throws {
        guard try value() else { throw CapturedContentNativeFailure.assertion }
    }
}
private enum CapturedContentNativeFailure: Error { case unauthorized, unexpectedPayload, changedSource, assertion }
#endif
