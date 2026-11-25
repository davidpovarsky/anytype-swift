#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Four actual prepared native operations, with the real last commit reply
/// discarded after success. The next process reconciles the persisted intent.
/// This preserves captured facts; it does not admit the entire source Space.
final class AnyDestinationNativeImmutableRecordTests: XCTestCase, @unchecked Sendable {
    func testActualCapturedSourceFactsSurviveLostReplyAndColdNativeReopen() async throws {
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
                  member["permission"] == .string("owner") else { throw ImmutableNativeFailure.unauthorized }
        }
        let originalRoot = URL(fileURLWithPath: originalPath, isDirectory: true)
        let original = try Self.originalCapture(at: originalRoot)
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: original)
        let mapper = try AnyHeartNativeDefinitionPlan(catalog: catalog)
        try require(original.objects.count == 156 && catalog.types.count == 20 && catalog.relations.count == 126)
        try require(!catalog.permitsDestinationWrites && !mapper.permitsDestinationWrites)
        XCTAssertThrowsError(try mapper.admittedSchemaItems())
        let source = try XCTUnwrap(catalog.types.first { $0.recommendedLayout == 0 })
        let manifest = try JSONDecoder().decode(AnyJSON.self,
            from: Data(contentsOf: originalRoot.appendingPathComponent("bundle/manifest.json")))
        let sourceRow = try XCTUnwrap(manifest["Objects"]?.array?.first { $0["ObjectID"]?.string == source.objectID })
        let viewPath = try XCTUnwrap(sourceRow["NativeJSONView"]?["Path"]?.string)
        let view = try Self.sourceBytes(viewPath, under: originalRoot.appendingPathComponent("bundle"))
        try require(AnyContentDigest.sha256(view) == source.snapshot.viewSHA256)
        let rawSource = try XCTUnwrap(String(data: view, encoding: .utf8))
        let values: AnyJSON = .object(["sourceObject": .string(source.objectID), "sourceValue": .string(rawSource),
                                       "sourceDigest": .string(AnyContentDigest.sha256(view))])
        let owner: AnyDestinationReference = .mapped(sourceKey: "type", slot: .objectID, encoding: .rawID)
        let object: AnyDestinationReference = .mapped(sourceKey: "object", slot: .objectID, encoding: .rawID)
        let part: AnyJSON = .object(["key": .string("source_provenance"), "name": .string("Original source facts"),
            "datasets": .array([.object(["key": .string("source_provenance"), "module": .string("records"),
                "deleteBy": .string("none"), "fields": .array([
                    .object(["key": .string("sourceObject"), "kind": .string("string"), "required": .bool(true)]),
                    .object(["key": .string("sourceValue"), "kind": .string("string"), "required": .bool(true)]),
                    .object(["key": .string("sourceDigest"), "kind": .string("string"), "required": .bool(true)]),
                    .object(["key": .string("importedBy"), "stamp": .string("creator")]),
                    .object(["key": .string("importedAt"), "stamp": .string("createTime")])
                ])])])])
        let items: [AnyDestinationMigrationItem] = [
            .init(sourceKey: "type", sourceObjectID: source.objectID,
                operation: .typeDefinition(.init(xKey: "native_source_provenance_component", name: "Captured source facts"))),
            .init(sourceKey: "part", sourceObjectID: source.objectID, expectedRecordCount: 7,
                operation: .partDefinition(owner: owner, draft: .literal(part))),
            .init(sourceKey: "object", sourceObjectID: source.objectID,
                operation: .object(type: owner, collections: [], initialProperties: .literal(.object([:])))),
            .init(sourceKey: "facts", sourceObjectID: source.objectID,
                operation: .immutableRecord(object: object, ownerType: owner, datasetKey: "source_provenance", values: .literal(values)))
        ]
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let input = try encoder.encode(items)
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let inputURL = work.appendingPathComponent("immutable-component-input.json")
        let planURL = work.appendingPathComponent("immutable-plan.json")
        let journalURL = work.appendingPathComponent("journal", isDirectory: true)
        let definitions = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace, authorize: authorize)
        let plan: AnyDestinationMigrationPlan
        if phase == "execute" {
            try require(!FileManager.default.fileExists(atPath: planURL.path))
            try FileManager.default.createDirectory(at: journalURL, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
            try input.write(to: inputURL, options: .withoutOverwriting)
            let hash = AnyContentDigest.sha256(input)
            let component = try AnyDestinationSourceBinding(accountID: "explicit-source-facts-component", spaceID: "explicit-source-facts-component",
                witnessSHA256: hash, captureManifestSHA256: hash, semanticPlanSHA256: hash, sourceObjectIDs: [source.objectID])
            plan = try .init(source: component, workspace: workspace, storeID: definitions.capabilities.storeID,
                planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)),
                coverage: [.init(sourceObjectID: source.objectID, disposition: .mapped(itemSourceKeys: ["type", "part", "object", "facts"]))], items: items)
            try encoder.encode(plan).write(to: planURL, options: .withoutOverwriting)
        } else {
            try require(input == Data(contentsOf: inputURL))
            plan = try AnyDestinationMigrationPlan.decode(Data(contentsOf: planURL))
        }
        let component = plan.source
        let verifySource: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { candidate in
            guard candidate == component,
                  AnyContentDigest.sha256(try Data(contentsOf: inputURL)) == component.captureManifestSHA256,
                  try Self.originalCapture(at: originalRoot).manifestSHA256 == original.manifestSHA256 else {
                throw AnyDestinationMigrationError.changedSource
            }
        }
        try require(plan.items.count == 4 && plan.binding.workspace == workspace)
        let native = try await AnyDestinationNativeClients.open(client: client, plan: plan, authorize: authorize)
        let acknowledgement: AnyJSON
        let intent: AnyPreparedImmutableRecordIntent
        if phase == "execute" {
            let losing = DropActualImmutableReply(driver: native)
            let executor = AnyDestinationMigrationExecutor(journalDirectory: journalURL, driver: losing)
            do {
                _ = try await executor.execute(plan: plan, payloads: { _ in throw ImmutableNativeFailure.unexpectedPayload },
                                               verifySource: verifySource, authorize: authorize)
                XCTFail("The actual committed reply must be discarded before checkpoint reconciliation")
                throw ImmutableNativeFailure.assertion
            } catch AnyEngineError.writeUncertain { }
            let received = await losing.received()
            acknowledgement = try XCTUnwrap(received)
            let entry = try Self.entry(journalURL, plan: plan)
            let schema = try XCTUnwrap(entry.immutableRecordSchema)
            let operation = try JSONDecoder().decode(AnyDestinationMigrationOperation.self, from: entry.resolvedOperation)
            guard case .immutableRecord(let restored) = try AnyDestinationNativeIntent.make(operation,
                binding: plan.binding, sourceKey: entry.sourceKey, sequence: nil, inlineContent: nil, immutableSchema: schema) else {
                throw ImmutableNativeFailure.assertion
            }
            intent = restored
            try require(entry.intentID == intent.intentID && entry.specSHA256 == intent.specSHA256)
            let saved = try XCTUnwrap(entry.receipts.last)
            try require(saved["outcome"]?.string == "prepared" && saved["stage"]?.string == "immutable-record-prepared")
            try require(saved["changeId"] == acknowledgement["changeId"] && saved["recordIds"] == acknowledgement["recordIds"])
            try encoder.encode(entry).write(to: work.appendingPathComponent("lost-reply-journal-entry.json"), options: .withoutOverwriting)
            try encoder.encode(acknowledgement).write(to: work.appendingPathComponent("actual-committed-reply.json"), options: .withoutOverwriting)
        } else {
            acknowledgement = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: work.appendingPathComponent("actual-committed-reply.json")))
            let executor = AnyDestinationMigrationExecutor(client: client, journalDirectory: journalURL)
            let progress = try await executor.execute(plan: plan, payloads: { _ in throw ImmutableNativeFailure.unexpectedPayload },
                                                       verifySource: verifySource, authorize: authorize)
            try require(progress.allItemsReconciled && progress.mappings.count == 4)
            let repeated = try await executor.execute(plan: plan, payloads: { _ in throw ImmutableNativeFailure.unexpectedPayload },
                                                       verifySource: verifySource, authorize: authorize)
            try require(encoder.encode(progress.mappings) == encoder.encode(repeated.mappings))
            guard case .immutableRecord(let restored) = repeated.verificationIntents[3] else { throw ImmutableNativeFailure.assertion }
            intent = restored
            try require(repeated.mappings[3].signedChangeIDs == [acknowledgement["changeId"]?.string]
                .compactMap { $0 } && repeated.mappings[3].recordIDs == acknowledgement["recordIds"]?.array?.compactMap(\.string))
            let verified = try await AnyDestinationMigrationVerifier(client: client).verify(plan: plan, progress: repeated,
                                                                                           verifySource: verifySource, authorize: authorize)
            try require(verified.comparedOperationCount == 4)
            try encoder.encode(verified).write(to: work.appendingPathComponent("cold-verification.json"), options: .withoutOverwriting)
            try require(fixture["outboundDeniedByOS"] == .bool(true) && fixture["networkPeerCount"] == .integer(0))
        }
        let valid = try AnyPreparedImmutableRecordReceipt(acknowledgement, intent: intent)
        try require(valid.isCompleteAndCurrent && valid.recordIDs.count == 1)
        let recordID = valid.recordIDs[0], changeID = valid.changeID
        try await authorize()
        let prefix = ["v1", "spaces", space]
        let listing = try await client.requestJSON(method: "POST", path: prefix + ["query"], body: .object([
            "objectId": .string(intent.objectID), "dataset": .string(intent.schema.dataset),
            "limit": .integer(2), "includeTotal": .bool(true)]))
        try require(listing["total"]?.integer == 1 && listing["hasNext"]?.bool == false && listing["records"]?.array?.count == 1)
        let row = try XCTUnwrap(listing["records"]?.array?.first)
        try require(row["id"]?.string == recordID)
        let history = try await client.requestJSON(method: "GET", path: prefix + ["objects", intent.objectID, "history"],
            query: ["dataset":intent.schema.dataset,"recordId":recordID,"coalesce":"false","limit":"200"])
        let changes = try XCTUnwrap(history["changes"]?.array).filter { $0["version"]?.string == changeID }
        try require(changes.count == 1)
        let snapshot = try await client.requestJSON(method: "GET", path: prefix + ["objects",intent.objectID,"history",changeID,
            "datasets",intent.schema.dataset,"records",recordID])
        try await authorize()
        let authority = try AnyDestinationImmutableRecordAuthority(change: changes[0], snapshot: snapshot, intent: intent,
                                                                   recordID: recordID, expectedChangeID: changeID)
        let projection = try AnyDestinationMigrationVerifier.immutableRecordProjection(row, intent: intent, authority: authority)
        try require(projection == AnyDestinationMigrationVerifier.immutableRecordProjection(authority.recordAtChange, intent: intent, authority: authority))
        let proof: AnyJSON = .object(["contract": .string("pinkha-source-facts-native-immutable-component-v1"),
            "sourceManifestSHA256": .string(original.manifestSHA256), "sourceSnapshotSHA256": .string(source.snapshot.snapshotSHA256),
            "sourceViewSHA256": .string(source.snapshot.viewSHA256), "actualSignedNativeCreation": projection,
            "historicalAuthorMigrated": .bool(false), "sourceAdmissionPromoted": .bool(false), "wholeSpaceMigration": .bool(false)])
        let bytes = try encoder.encode(proof)
        if phase == "reopen" { try require(bytes == Data(contentsOf: work.appendingPathComponent("execute-immutable.json"))) }
        try bytes.write(to: work.appendingPathComponent(phase + "-immutable.json"), options: .withoutOverwriting)
        print("NATIVE_IMMUTABLE_RECORD_COMPONENT prepared_operations=4 immutable_rows=1 actual_commit_reply_discarded=true source_admission=false whole_space_migration=false phase=" + phase)
    }
    private static func entry(_ root: URL, plan: AnyDestinationMigrationPlan) throws -> AnyDestinationJournalEntry {
        let journal = try AnyDestinationMigrationJournal(parent: root, plan: plan)
        return try XCTUnwrap(journal.load(index: 3))
    }
    private static func sourceBytes(_ relative: String, under directory: URL) throws -> Data {
        let parts = relative.split(separator: "/", omittingEmptySubsequences: false)
        guard !relative.hasPrefix("/"), !relative.contains("\\"), !relative.contains("\0"),
              parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else { throw ImmutableNativeFailure.changedSource }
        let file = directory.appendingPathComponent(relative).resolvingSymlinksInPath().standardizedFileURL
        guard file.path.hasPrefix(directory.path + "/"), try file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else {
            throw ImmutableNativeFailure.changedSource
        }
        return try Data(contentsOf: file, options: [.mappedIfSafe])
    }
    private static func originalCapture(at root: URL) throws -> AnyHeartNativeSpaceBundle {
        let contextBytes = try sourceBytes("fixture-context.json", under: root)
        guard AnyContentDigest.sha256(contextBytes) == "bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a" else { throw ImmutableNativeFailure.changedSource }
        let context = try JSONDecoder().decode(AnyJSON.self, from: contextBytes)
        guard context["customSchemaAcceptanceStatus"] == .string("FAIL"), context["readOnlyDiagnosticFixture"] == .bool(true),
              context["sourceAdmissionPromoted"] == .bool(false) else { throw ImmutableNativeFailure.changedSource }
        let directory = root.appendingPathComponent("bundle", isDirectory: true)
        let manifest = try sourceBytes("manifest.json", under: directory)
        guard AnyContentDigest.sha256(manifest) == "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4" else { throw ImmutableNativeFailure.changedSource }
        return try .init(manifest: manifest, sourceAccountID: XCTUnwrap(context["sourceAccountID"]?.string),
            sourceSpaceID: XCTUnwrap(context["sourceSpaceID"]?.string)) { try sourceBytes($0.path, under: directory) }
    }
    private func require(_ value: @autoclosure () throws -> Bool) throws {
        guard try value() else { throw ImmutableNativeFailure.assertion }
    }
}
private actor DropActualImmutableReply: AnyDestinationNativeDriving {
    let driver: AnyDestinationNativeClients
    var discarded: AnyJSON?
    init(driver: AnyDestinationNativeClients) { self.driver = driver }
    func received() -> AnyJSON? { discarded }
    func status(_ intent: AnyDestinationNativeIntent, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await driver.status(intent, authorize: authorize)
    }
    func prepare(_ intent: AnyDestinationNativeIntent, payload: URL?, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await driver.prepare(intent, payload: payload, authorize: authorize)
    }
    func commit(_ intent: AnyDestinationNativeIntent, receipt: AnyJSON, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        let actual = try await driver.commit(intent, receipt: receipt, authorize: authorize)
        if case .immutableRecord = intent, discarded == nil {
            discarded = actual
            throw AnyEngineError.writeUncertain
        }
        return actual
    }
    func applySequence(objectID: String, authorize: @escaping AnyDestinationAuthorization) async throws -> Int64 {
        try await driver.applySequence(objectID: objectID, authorize: authorize)
    }
    func immutableSchema(ownerTypeID: String, dataset: String, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyPreparedImmutableRecordSchema {
        try await driver.immutableSchema(ownerTypeID: ownerTypeID, dataset: dataset, authorize: authorize)
    }
}
private enum ImmutableNativeFailure: Error { case unauthorized, unexpectedPayload, changedSource, assertion }
#endif
