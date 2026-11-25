#if os(macOS) || os(Linux)
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// The controller supplies a real separately launched, source-hashed Any CLI.
/// This qualifies the destination executor with explicit immutable component
/// input. It does not impersonate a live Heart capture or admit blocked spaces.
final class AnyDestinationNativeContentTests: XCTestCase, @unchecked Sendable {
    func testActualNativeExecutionAndColdReadback() async throws {
        do { try await qualifyActualNativeExecutionAndColdReadback() }
        catch {
            if let work = ProcessInfo.processInfo.environment["PINKHA_DESTINATION_NATIVE_WORK"] {
                let native = error as NSError
                var fields: [String: AnyJSON] = ["domain": .string(native.domain), "code": .integer(Int64(native.code)),
                    "userInfoKeys": .array(native.userInfo.keys.sorted().map(AnyJSON.string))]
                for key in ["NSErrorFailingURLStringKey", "NSErrorFailingURLKey"] {
                    let value = (native.userInfo[key] as? URL)?.absoluteString ?? (native.userInfo[key] as? String)
                    if let value, let url = URL(string: value) {
                        fields[key + "Path"] = .string(url.path)
                    }
                }
                let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
                try? encoder.encode(AnyJSON.object(fields)).write(to: URL(fileURLWithPath: work)
                    .appendingPathComponent("native-error-" + UUID().uuidString + ".json"), options: .withoutOverwriting)
            }
            throw error
        }
    }

    private func qualifyActualNativeExecutionAndColdReadback() async throws {
        let env = ProcessInfo.processInfo.environment
        guard let fixturePath = env["PINKHA_DESTINATION_NATIVE_FIXTURE"],
              let workPath = env["PINKHA_DESTINATION_NATIVE_WORK"],
              let phase = env["PINKHA_DESTINATION_NATIVE_PHASE"], ["execute", "reopen", "refusal"].contains(phase) else {
            throw XCTSkip("Requires the explicit retained real-native controller and phase.")
        }
        let fixture = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: URL(fileURLWithPath: fixturePath)))
        let base = try XCTUnwrap(fixture["baseURL"]?.string)
        let accountID = try XCTUnwrap(fixture["accountID"]?.string)
        let spaceID = try XCTUnwrap(fixture["spaceID"]?.string)
        XCTAssertEqual(fixture["binarySHA256"]?.string, "bc73441d05a502e3e77df479f54279540489869b00ca1aecf4e1e9f681fa0f49")
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: base)), expectedAccountID: accountID)
        let workspace = try AnyTorahWorkspace(accountID: accountID, spaceID: spaceID)
        let work = URL(fileURLWithPath: workPath, isDirectory: true)
        let journal = work.appendingPathComponent("journal", isDirectory: true)
        let planURL = work.appendingPathComponent("plan.json")
        let sourceURL = work.appendingPathComponent("component-input.json")
        let smallURL = work.appendingPathComponent("inline-input")
        let fullURL = work.appendingPathComponent("full-input")
        let capabilities = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace, authorize: {})
        let plan: AnyDestinationMigrationPlan
        if phase == "execute", !FileManager.default.fileExists(atPath: planURL.path) {
            try FileManager.default.createDirectory(at: journal, withIntermediateDirectories: false,
                                                   attributes: [.posixPermissions: 0o700])
            let small = Data("קובץ inline e\u{301} — source bytes".utf8)
            let full = Data(repeating: 0xa7, count: 8192)
            try small.write(to: smallURL, options: .withoutOverwriting)
            try full.write(to: fullURL, options: .withoutOverwriting)
            let items = Self.items(nonce: UUID().uuidString.lowercased().replacingOccurrences(of: "-", with: ""),
                                   small: small, full: full)
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            let input = try encoder.encode(items)
            try input.write(to: sourceURL, options: .withoutOverwriting)
            let digest = AnyContentDigest.sha256(input)
            let sourceIDs = Array(Set(items.map(\.sourceObjectID))).sorted()
            let source = try AnyDestinationSourceBinding(accountID: "explicit-component-input",
                spaceID: "explicit-component-input", witnessSHA256: digest, captureManifestSHA256: digest,
                semanticPlanSHA256: digest, sourceObjectIDs: sourceIDs)
            let coverage = sourceIDs.map { sourceID in
                AnyDestinationCoverage(sourceObjectID: sourceID,
                    disposition: .mapped(itemSourceKeys: items.filter { $0.sourceObjectID == sourceID }.map(\.sourceKey)))
            }
            plan = try AnyDestinationMigrationPlan(source: source, workspace: workspace,
                storeID: capabilities.capabilities.storeID, planID: AnyContentDigest.sha256(Data(UUID().uuidString.utf8)),
                coverage: coverage, items: items)
            try encoder.encode(plan).write(to: planURL, options: .withoutOverwriting)
        } else {
            plan = try AnyDestinationMigrationPlan.decode(Data(contentsOf: planURL))
        }
        let source = plan.source
        let verifySource: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { candidate in
            guard candidate == source,
                  AnyContentDigest.sha256(try Data(contentsOf: sourceURL)) == source.captureManifestSHA256 else {
                throw AnyDestinationMigrationError.changedSource
            }
        }
        let authorize: @Sendable () async throws -> Void = {
            let member = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", spaceID, "members", "me"])
            guard member["identity"]?.string == accountID, member["status"]?.string == "active",
                  ["owner", "writer"].contains(member["permission"]?.string ?? "") else {
                throw NativeDestinationControlFailure.unauthorized
            }
        }
        func stage(_ value: String) throws {
            try Data(value.utf8).write(to: work.appendingPathComponent("current-native-stage.txt"), options: .atomic)
        }
        try stage("executor")
        let executor = AnyDestinationMigrationExecutor(client: client, journalDirectory: journal)
        let progress = try await executor.execute(plan: plan, payloads: { key in
            guard phase == "execute" else { throw NativeDestinationControlFailure.unexpectedPayloadReplay }
            return key == "inline-file" ? smallURL : fullURL
        }, verifySource: verifySource, authorize: authorize)
        try stage("executor-returned-complete")
        XCTAssertTrue(progress.allItemsReconciled)
        let verifier = AnyDestinationMigrationVerifier(client: client)
        if phase == "refusal" {
            let object = try XCTUnwrap(progress.mappings.first { $0.sourceKey == "a" })
            _ = try await client.requestJSON(method: "POST",
                path: ["v1", "spaces", spaceID, "properties", object.objectID, "set", "any"],
                body: .object(["patch": .object(["name": .string("Actual native mutation after original acceptance")])]),
                authorize: authorize)
            do {
                _ = try await verifier.verify(plan: plan, progress: progress, verifySource: verifySource, authorize: authorize)
                XCTFail("A current native modification was accepted as original migration content")
            } catch is AnyDestinationContentVerificationError {
                try Data("actual-native-modification-refused\n".utf8)
                    .write(to: work.appendingPathComponent("refusal.txt"), options: .withoutOverwriting)
            }
            return
        }
        try stage("verifier")
        let verification = try await verifier.verify(plan: plan, progress: progress,
                                                     verifySource: verifySource, authorize: authorize)
        try stage("verifier-returned-complete")
        XCTAssertEqual(verification.comparedOperationCount, plan.items.count)
        XCTAssertEqual(verification.files.count, 2)
        XCTAssertTrue(verification.retainedSourceSystemObjectIDs.isEmpty)
        try stage("native-cycle-index")
        let cycles = try await verifyNativeCycles(client: client, spaceID: spaceID,
                                                  mappings: progress.mappings, authorize: authorize)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .prettyPrinted]
        try encoder.encode(cycles).write(to: work.appendingPathComponent(phase + "-native-cycle-index.json"),
                                        options: .withoutOverwriting)
        let resultURL = work.appendingPathComponent(phase + "-verification.json")
        try encoder.encode(verification).write(to: resultURL, options: .withoutOverwriting)
        let mappings = try encoder.encode(progress.mappings)
        if phase == "execute" {
            try mappings.write(to: work.appendingPathComponent("execute-mappings.json"), options: .withoutOverwriting)
        } else {
            let previous = try JSONDecoder().decode(AnyDestinationContentVerification.self,
                from: Data(contentsOf: work.appendingPathComponent("execute-verification.json")))
            XCTAssertEqual(verification.observations, previous.observations)
            XCTAssertEqual(mappings, try Data(contentsOf: work.appendingPathComponent("execute-mappings.json")))
        }
    }

    private func verifyNativeCycles(client: AnyHTTPClient, spaceID: String,
                                    mappings: [AnyDestinationMigrationMapping],
                                    authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyJSON {
        let property = try XCTUnwrap(mappings.first { $0.sourceKey == "links" }?.recordIDs.first)
        let a = try XCTUnwrap(mappings.first { $0.sourceKey == "a" }?.objectID)
        let b = try XCTUnwrap(mappings.first { $0.sourceKey == "b" }?.objectID)
        let clock = ContinuousClock(), deadline = ContinuousClock.now + .seconds(30)
        var evidence: [AnyJSON] = []
        for (source, target) in [(a, b), (b, a)] {
            var complete = false
            repeat {
                let forward = try await client.requestJSON(method: "GET",
                    path: ["v1", "spaces", spaceID, "objects", source, "links"],
                    query: ["kind": "relation", "prop": property, "limit": "2"], authorize: authorize)
                let reverse = try await client.requestJSON(method: "GET",
                    path: ["v1", "spaces", spaceID, "objects", target, "backlinks"],
                    query: ["kind": "relation", "limit": "2"], authorize: authorize)
                let expectedURI = "any://o/" + spaceID + "/" + target
                func matches(_ edge: AnyJSON) -> Bool {
                    edge["kind"]?.string == "relation" &&
                    edge["source"]?["spaceId"]?.string == spaceID &&
                    edge["source"]?["objectId"]?.string == source &&
                    edge["source"]?["dataset"]?.string == "prop" &&
                    edge["source"]?["recordId"]?.string == property &&
                    edge["target"]?["uri"]?.string == expectedURI &&
                    edge["target"]?["objectId"]?.string == target
                }
                if let links = forward["links"]?.array, links.count == 1, matches(links[0]),
                   let backlinks = reverse["object"]?.array, backlinks.count == 1, matches(backlinks[0]),
                   reverse["parts"]?.array?.isEmpty == true,
                   forward["truncated"]?.bool != true, reverse["truncated"]?.bool != true {
                    evidence.append(.object(["forward": forward, "reverse": reverse])); complete = true; break
                }
                try Task.checkCancellation()
                if clock.now < deadline { try await Task.sleep(for: .milliseconds(100)) }
            } while clock.now < deadline
            XCTAssertTrue(complete, "Actual native link and backlink index did not expose the exact cycle")
            guard complete else { throw NativeDestinationControlFailure.nativeCycleMissing }
        }
        return .array(evidence)
    }

    private static func items(nonce: String, small: Data, full: Data) -> [AnyDestinationMigrationItem] {
        func ref(_ key: String, _ slot: AnyDestinationReference.Slot = .objectID,
                 _ encoding: AnyDestinationReference.Encoding = .rawID) -> AnyDestinationReference {
            .mapped(sourceKey: key, slot: slot, encoding: encoding)
        }
        func field(_ key: AnyDestinationReference, _ value: AnyDestinationValue) -> AnyDestinationField {
            .init(key: key, value: value)
        }
        func item(_ key: String, source: String? = nil, records: Int = 1,
                  _ operation: AnyDestinationMigrationOperation) -> AnyDestinationMigrationItem {
            .init(sourceKey: key, sourceObjectID: source ?? key, expectedRecordCount: records, operation: operation)
        }
        let type = ref("type"), collection = ref("collection")
        let initialA = AnyDestinationValue.object([
            field(.native("any"), .literal(.object(["name": .string("מקור א e\u{301}")] ))),
            field(type, .object([
                field(ref("title", .record(index: 0)), .literal(.string(""))),
                field(ref("date", .record(index: 0)), .literal(.object(["$date": .integer(1_700_000_000_123)])))
            ])),
            field(collection, .object([field(ref("group", .record(index: 0)), .literal(.string("initial collection")))]))
        ])
        let initialB = AnyDestinationValue.object([
            field(.native("any"), .literal(.object(["name": .string("Source B")]))),
            field(type, .object([field(ref("title", .record(index: 0)), .literal(.string("עברית English e\u{301} 🧪")))]))
        ])
        let part = AnyJSON.object([
            "key": .string("content"), "name": .string("תוכן"), "ui": .object(["type": .string("document")]),
            "datasets": .array([
                .object(["key": .string("editor_blocks"), "module": .string("editor")]),
                .object(["key": .string("notes"), "module": .string("records"),
                    "fields": .array([
                        .object(["key": .string("title"), "kind": .string("string"), "required": .bool(true)]),
                        .object(["key": .string("score"), "kind": .string("number")])
                    ]),
                    "indexes": .array([.object(["key": .string("title_index"), "fields": .array([.string("title")])])])])
            ])
        ])
        return [
            item("type", .typeDefinition(.init(xKey: "c_type_" + nonce, name: "סוג מועבר",
                description: "Native content comparison", layout: .literal(.object(["type": .string("page")])),
                meta: .literal(.object(["source": .string("explicit component fixture")]))))),
            item("collection", .collectionDefinition(.init(xKey: "c_collection_" + nonce, name: "אוסף מועבר", hidden: true))),
            item("title", .propertyDefinition(owner: type, kind: "string", name: "כותרת", xKey: "title",
                description: "", scope: "synced", xFormat: nil, index: nil)),
            item("links", .propertyDefinition(owner: type, kind: "array", name: "קשרים", xKey: "links",
                description: "", scope: "synced", xFormat: .literal(.object([
                    "type": .string("relation"), "config": .object(["multiple": .bool(true)]),
                    "relation": .object(["targetTypes": .array([.string("c_type_" + nonce)])])
                ])), index: nil)),
            item("date", .propertyDefinition(owner: type, kind: "datetime", name: "Date", xKey: "source_date",
                description: "", scope: "synced", xFormat: .literal(.object(["type": .string("datetime")])), index: nil)),
            item("group", .propertyDefinition(owner: collection, kind: "string", name: "קבוצה", xKey: "source_group",
                description: "", scope: "synced", xFormat: nil, index: nil)),
            item("part", source: "type", records: 6, .partDefinition(owner: type, draft: .literal(part))),
            item("a", .object(type: type, collections: [collection], initialProperties: initialA)),
            item("b", .object(type: type, collections: [collection], initialProperties: initialB)),
            item("parent-block", source: "a", .editorBlock(owner: ref("a"), dataset: "editor_blocks", type: "paragraph",
                text: "**שלום** e\u{301} 🧪 — [מקור](https://example.org/a)", style: .literal(.object([:])), parent: nil, position: "a")),
            item("child-block", source: "a", .editorBlock(owner: ref("a"), dataset: "editor_blocks", type: "paragraph",
                text: "Child / ילד", style: .literal(.object([:])), parent: ref("parent-block", .record(index: 0)), position: "b")),
            item("b-block", source: "b", .editorBlock(owner: ref("b"), dataset: "editor_blocks", type: "paragraph",
                text: "Second page", style: .literal(.object([:])), parent: nil, position: "a")),
            item("inline-file", .file(owner: ref("a"), name: "source.txt", mime: "text/plain",
                size: Int64(small.count), contentSHA256: AnyContentDigest.sha256(small))),
            item("full-file", .file(owner: ref("b"), name: "source.bin", mime: "application/octet-stream",
                size: Int64(full.count), contentSHA256: AnyContentDigest.sha256(full))),
            item("a-cycle", source: "a", .propertyUpdate(object: ref("a"), owner: type,
                patch: .object([field(ref("links", .record(index: 0)), .array([.reference(ref("b", .objectID, .anyURI))]))]))),
            item("b-cycle", source: "b", .propertyUpdate(object: ref("b"), owner: type,
                patch: .object([field(ref("links", .record(index: 0)), .array([.reference(ref("a", .objectID, .anyURI))]))]))),
            item("b-group", source: "b", .propertyUpdate(object: ref("b"), owner: collection,
                patch: .object([field(ref("group", .record(index: 0)), .literal(.string("deferred collection value")))])))
        ]
    }
}
private enum NativeDestinationControlFailure: Error { case unexpectedPayloadReplay, unauthorized, nativeCycleMissing }
#endif
