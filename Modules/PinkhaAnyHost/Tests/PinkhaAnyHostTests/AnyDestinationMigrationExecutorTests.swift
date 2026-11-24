import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Host orchestration/real-filesystem controls. The injected native driver is
/// deliberately identified as a fixture; these are not native migration or
/// whole-Space acceptance evidence.
final class AnyDestinationMigrationExecutorTests: XCTestCase, @unchecked Sendable {
    func testCoverageValidatedDecodeExactUTF8AndOwnedMutationTargets() async throws {
        let plan = try fixturePlan()
        let encoded = try AnyDestinationMigrationJournal.encoded(plan)
        let decoded = try AnyDestinationMigrationPlan.decode(encoded)
        XCTAssertEqual(decoded.canonicalBytes, plan.canonicalBytes)
        let source = try AnyDestinationSourceBinding(accountID: "source-account", spaceID: "source-space",
            witnessSHA256: digest("witness"), captureManifestSHA256: digest("capture"), semanticPlanSHA256: digest("semantic"),
            sourceObjectIDs: ["é", "e\u{301}"])
        let items = ["é", "e\u{301}"].map { key in
            AnyDestinationMigrationItem(sourceKey: key, sourceObjectID: key,
                operation: .object(type: .native("page"), collections: [], initialProperties: .literal(.object([:]))))
        }
        let exact = try AnyDestinationMigrationPlan(source: source, workspace: plan.binding.workspace,
            storeID: plan.binding.storeID, planID: digest("utf8-plan"),
            coverage: items.map { .init(sourceObjectID: $0.sourceObjectID, disposition: .mapped(itemSourceKeys: [$0.sourceKey])) }, items: items)
        XCTAssertNotEqual(Data(exact.items[0].sourceKey.utf8), Data(exact.items[1].sourceKey.utf8))
        XCTAssertEqual(try AnyDestinationMigrationPlan.decode(AnyDestinationMigrationJournal.encoded(exact)).canonicalBytes, exact.canonicalBytes)

        var damaged = try JSONDecoder().decode(AnyJSON.self, from: encoded).object!
        damaged["planSHA256"] = .string(String(repeating: "0", count: 64))
        XCTAssertThrowsError(try AnyDestinationMigrationPlan.decode(AnyDestinationMigrationJournal.encoded(AnyJSON.object(damaged))))
        let arbitrary = AnyDestinationMigrationItem(sourceKey: "foreign-write", sourceObjectID: "source-a",
            operation: .propertyUpdate(object: .native("preexisting-destination"), owner: .native("any"),
                                       patch: .literal(.object(["name": .string("forbidden")]))))
        XCTAssertThrowsError(try replacing(plan, adding: arbitrary))

        let unknown = try AnyDestinationSourceBinding(accountID: plan.source.accountID, spaceID: plan.source.spaceID,
            witnessSHA256: plan.source.witnessSHA256, captureManifestSHA256: plan.source.captureManifestSHA256,
            semanticPlanSHA256: plan.source.semanticPlanSHA256, sourceObjectIDs: plan.source.sourceObjectIDs + ["unmapped-history"])
        let blocked = try AnyDestinationMigrationPlan(source: unknown, workspace: plan.binding.workspace,
            storeID: plan.binding.storeID, planID: digest("blocked"),
            coverage: plan.coverage + [.init(sourceObjectID: "unmapped-history", disposition: .blocked(reasons: ["history has no destination representation"]))], items: plan.items)
        let driver = DestinationFixtureDriver()
        let executor = AnyDestinationMigrationExecutor(journalDirectory: try directory(), driver: driver)
        await expectFailure { _ = try await executor.execute(plan: blocked, payloads: { _ in throw FixtureFailure.noPayload },
            verifySource: { _ in }, authorize: {}) }
        let stats = await driver.stats(); XCTAssertTrue(stats.preparations.isEmpty)
    }

    func testLostPreparationReplyResumesOriginalIDsAndCyclicReferences() async throws {
        let plan = try fixturePlan(), parent = try directory()
        let driver = DestinationFixtureDriver(failAfterPrepare: "a")
        let first = AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver)
        await expectFailure { _ = try await first.execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload },
            verifySource: { _ in }, authorize: {}) }
        let before = await driver.stats()
        let next = AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver)
        let result = try await next.execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload },
            verifySource: { _ in }, authorize: {})
        XCTAssertTrue(result.allItemsReconciled); XCTAssertEqual(result.mappings.count, plan.items.count)
        let a = try XCTUnwrap(result.mappings.first { $0.sourceKey == "a" })
        let b = try XCTUnwrap(result.mappings.first { $0.sourceKey == "b" })
        XCTAssertEqual(a.objectID, before.preparedObjects["a"])
        let stats = await driver.stats()
        XCTAssertEqual(stats.preparations["a"], 1)
        XCTAssertEqual(stats.propertyPatches["a-links"]?.object?.values.first, .array([.string("any://" + b.objectID)]))
        XCTAssertEqual(stats.propertyPatches["b-links"]?.object?.values.first, .array([.string("any://" + a.objectID)]))
        let reopened = try await AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver)
            .execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload }, verifySource: { _ in }, authorize: {})
        XCTAssertEqual(reopened.mappings.map(\.intentID), result.mappings.map(\.intentID))
        XCTAssertEqual(reopened.mappings.map(\.objectID), result.mappings.map(\.objectID))
        let final = await driver.stats(); XCTAssertEqual(final.preparations, stats.preparations)
    }

    func testPropertyRevisionCheckpointPrecedesDispatchAndIsNeverRefreshed() async throws {
        let plan = try fixturePlan(), parent = try directory()
        let driver = DestinationFixtureDriver()
        let propertyIndex = try XCTUnwrap(plan.items.firstIndex { $0.sourceKey == "a-links" })
        let first = AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver, checkpointHook: { index in
            if index == propertyIndex { throw FixtureFailure.interrupted }
        })
        await expectFailure { _ = try await first.execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload },
            verifySource: { _ in }, authorize: {}) }
        var checkpoint: AnyDestinationMigrationJournal? = try .init(parent: parent, plan: plan)
        let original = try XCTUnwrap(checkpoint?.load(index: propertyIndex))
        XCTAssertEqual(original.expectedApplySequence, 1)
        let specification = try JSONDecoder().decode(AnyJSON.self, from: original.specBytes)
        XCTAssertEqual(specification["expectedApplySeq"]?.integer, 1)
        let object = try XCTUnwrap(specification["objectId"]?.string)
        await driver.changeSequence(object, to: 9)
        // A second process cannot acquire the still-live inspection owner.
        await expectFailure { _ = try await AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver)
            .execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload }, verifySource: { _ in }, authorize: {}) }
        checkpoint = nil
        await expectFailure { _ = try await AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver)
            .execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload }, verifySource: { _ in }, authorize: {}) }
        let stats = await driver.stats()
        XCTAssertEqual(stats.sequenceReads.values.reduce(0, +), 1)
        XCTAssertNil(stats.preparations["a-links"])
        XCTAssertEqual(stats.attemptedPropertySequences["a-links"], [1])
        XCTAssertEqual(original.expectedApplySequence, 1)
    }

    func testInlineAndFullFileResumeWithoutOriginalPayloadPaths() async throws {
        let inline = Data((0..<4095).map { UInt8($0 % 251) })
        let full = Data((0..<(2 << 20)).map { UInt8($0 % 253) })
        let plan = try fixturePlan(files: [("small", inline), ("large", full)])
        let parent = try directory(), payloadRoot = try directory()
        let small = payloadRoot.appendingPathComponent("small"), large = payloadRoot.appendingPathComponent("large")
        try inline.write(to: small); try full.write(to: large)
        let driver = DestinationFixtureDriver(failAfterPrepare: "large")
        let inlineIndex = try XCTUnwrap(plan.items.firstIndex { $0.sourceKey == "small" })
        let first = AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver, checkpointHook: { index in
            if index == inlineIndex { throw FixtureFailure.interrupted }
        })
        let paths: @Sendable (String) async throws -> URL = { key in
            if key == "small" { return small }; if key == "large" { return large }; throw FixtureFailure.noPayload
        }
        await expectFailure { _ = try await first.execute(plan: plan, payloads: paths, verifySource: { _ in }, authorize: {}) }
        try FileManager.default.removeItem(at: small)
        await expectFailure { _ = try await AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver)
            .execute(plan: plan, payloads: { key in
                guard key == "large" else { throw FixtureFailure.noPayload }; return large
            }, verifySource: { _ in }, authorize: {}) }
        let before = await driver.stats(); let originalLarge = before.preparedObjects["large"]
        try FileManager.default.removeItem(at: large)
        let result = try await AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver)
            .execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload }, verifySource: { _ in }, authorize: {})
        XCTAssertTrue(result.allItemsReconciled)
        XCTAssertEqual(result.mappings.first { $0.sourceKey == "large" }?.objectID, originalLarge)
        let after = await driver.stats()
        XCTAssertEqual(after.preparations["small"], 1); XCTAssertEqual(after.preparations["large"], 1)
        XCTAssertEqual(after.fileDigests["small"], digest(inline)); XCTAssertEqual(after.fileDigests["large"], digest(full))
    }

    func testNativeTerminalAndChangedPlanNeverCreateReplacementIDs() async throws {
        let plan = try fixturePlan(), parent = try directory(), driver = DestinationFixtureDriver()
        _ = try await AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver)
            .execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload }, verifySource: { _ in }, authorize: {})
        let before = await driver.stats()
        await driver.setTerminal(sourceKey: "a", outcome: "committed_modified")
        for _ in 0..<2 {
            await expectFailure { _ = try await AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver)
                .execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload }, verifySource: { _ in }, authorize: {}) }
        }
        let changed = try fixturePlan(title: "changed source content")
        XCTAssertEqual(changed.binding.planID, plan.binding.planID)
        XCTAssertNotEqual(changed.binding.planSHA256, plan.binding.planSHA256)
        await expectFailure { _ = try await AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver)
            .execute(plan: changed, payloads: { _ in throw FixtureFailure.noPayload }, verifySource: { _ in }, authorize: {}) }
        let after = await driver.stats(); XCTAssertEqual(after.preparations, before.preparations)
        XCTAssertEqual(after.preparedObjects, before.preparedObjects)
    }

    func testJournalOwnershipNamespaceIntegrityAndSourceWithdrawal() async throws {
        let plan = try fixturePlan(), parent = try directory()
        try FileManager.default.setAttributes([.posixPermissions: 0o770], ofItemAtPath: parent.path)
        XCTAssertThrowsError(try AnyDestinationMigrationJournal(parent: parent, plan: plan))
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: parent.path)
        do {
            let owner = try AnyDestinationMigrationJournal(parent: parent, plan: plan)
            XCTAssertThrowsError(try AnyDestinationMigrationJournal(parent: parent, plan: plan))
            let scopes = try FileManager.default.contentsOfDirectory(at: parent.appendingPathComponent("AnyDestinationMigrationV1"), includingPropertiesForKeys: nil)
            let scope = try XCTUnwrap(scopes.first)
            try FileManager.default.moveItem(at: scope, to: scope.appendingPathExtension("old"))
            try FileManager.default.createDirectory(at: scope, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
            XCTAssertThrowsError(try owner.load(index: 0))
        }
        let driver = DestinationFixtureDriver(), another = try directory()
        await expectFailure { _ = try await AnyDestinationMigrationExecutor(journalDirectory: another, driver: driver)
            .execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload },
                     verifySource: { _ in throw FixtureFailure.withdrawn }, authorize: {}) }
        let before = await driver.stats(); XCTAssertTrue(before.preparations.isEmpty)
        _ = try await AnyDestinationMigrationExecutor(journalDirectory: another, driver: driver)
            .execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload }, verifySource: { _ in }, authorize: {})
        let files = try FileManager.default.subpathsOfDirectory(atPath: another.path).filter { $0.contains("entry-0-") }
        let checkpoint = another.appendingPathComponent(try XCTUnwrap(files.first))
        var bytes = try Data(contentsOf: checkpoint); bytes[bytes.count / 2] ^= 1
        try bytes.write(to: checkpoint); try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: checkpoint.path)
        let stable = await driver.stats()
        await expectFailure { _ = try await AnyDestinationMigrationExecutor(journalDirectory: another, driver: driver)
            .execute(plan: plan, payloads: { _ in throw FixtureFailure.noPayload }, verifySource: { _ in }, authorize: {}) }
        let after = await driver.stats(); XCTAssertEqual(after.preparations, stable.preparations)
    }

    private func directory() throws -> URL {
        let path = FileManager.default.temporaryDirectory.appendingPathComponent("destination-executor-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: path, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        addTeardownBlock { try? FileManager.default.removeItem(at: path) }; return path
    }
    private func expectFailure(_ operation: () async throws -> Void, file: StaticString = #filePath, line: UInt = #line) async {
        do { try await operation(); XCTFail("Expected a closed refusal", file: file, line: line) } catch {}
    }
    private func digest(_ text: String) -> String { digest(Data(text.utf8)) }
    private func digest(_ data: Data) -> String { AnyContentDigest.sha256(data) }
    private func ref(_ key: String, _ slot: AnyDestinationReference.Slot = .objectID,
                     _ encoding: AnyDestinationReference.Encoding = .rawID) -> AnyDestinationReference {
        .mapped(sourceKey: key, slot: slot, encoding: encoding)
    }
    private func fixturePlan(title: String = "שלום e\u{301} 😀", files: [(String, Data)] = []) throws -> AnyDestinationMigrationPlan {
        var items: [AnyDestinationMigrationItem] = [
            .init(sourceKey: "type", sourceObjectID: "source-type", operation: .typeDefinition(.init(xKey: "migration.test", name: "Owned type"))),
            .init(sourceKey: "relation", sourceObjectID: "source-relation", operation: .propertyDefinition(owner: ref("type"),
                kind: "array", name: "Related", xKey: "related", description: "", scope: "synced",
                xFormat: .literal(.object(["type": .string("relation")])), index: nil)),
            .init(sourceKey: "a", sourceObjectID: "source-a", operation: .object(type: ref("type"), collections: [],
                initialProperties: .literal(.object(["any": .object(["name": .string(title)])])))),
            .init(sourceKey: "b", sourceObjectID: "source-b", operation: .object(type: ref("type"), collections: [],
                initialProperties: .literal(.object(["any": .object(["name": .string("second")])])))),
            .init(sourceKey: "a-block", sourceObjectID: "source-a", operation: .editorBlock(owner: ref("a"), dataset: "editor_blocks",
                type: "paragraph", text: "תוכן שמור e\u{301} 😀", style: .literal(.object([:])), parent: nil, position: "m"))]
        for (key, bytes) in files {
            items.append(.init(sourceKey: key, sourceObjectID: "source-a", operation: .file(owner: ref("a"),
                name: key + ".bin", mime: "application/octet-stream", size: Int64(bytes.count), contentSHA256: digest(bytes))))
        }
        for (key, other) in [("a", "b"), ("b", "a")] {
            items.append(.init(sourceKey: key + "-links", sourceObjectID: "source-" + key,
                operation: .propertyUpdate(object: ref(key), owner: ref("type"),
                    patch: .object([.init(key: ref("relation", .record(index: 0)),
                        value: .array([.reference(ref(other, .objectID, .anyURI))]))]))))
        }
        let source = try AnyDestinationSourceBinding(accountID: "source-account", spaceID: "source-space",
            witnessSHA256: digest("witness"), captureManifestSHA256: digest("capture"), semanticPlanSHA256: digest("semantic"),
            sourceObjectIDs: ["source-type", "source-relation", "source-a", "source-b"])
        let coverage = source.sourceObjectIDs.map { id in
            AnyDestinationCoverage(sourceObjectID: id, disposition: .mapped(itemSourceKeys: items.filter { $0.sourceObjectID == id }.map(\.sourceKey)))
        }
        return try .init(source: source, workspace: .init(accountID: "destination-account", spaceID: "destination-space"),
            storeID: "destination-store", planID: digest("logical-plan"), coverage: coverage, items: items)
    }
    private func replacing(_ plan: AnyDestinationMigrationPlan, adding item: AnyDestinationMigrationItem) throws -> AnyDestinationMigrationPlan {
        let coverage = plan.coverage.map { entry -> AnyDestinationCoverage in
            if entry.sourceObjectID == item.sourceObjectID, case .mapped(let keys) = entry.disposition {
                return .init(sourceObjectID: entry.sourceObjectID, disposition: .mapped(itemSourceKeys: keys + [item.sourceKey]))
            }; return entry
        }
        return try .init(source: plan.source, workspace: plan.binding.workspace, storeID: plan.binding.storeID,
                         planID: plan.binding.planID, coverage: coverage, items: plan.items + [item])
    }
}

private enum FixtureFailure: Error { case interrupted, noPayload, withdrawn, sequenceChanged }

private actor DestinationFixtureDriver: AnyDestinationNativeDriving {
    struct Stats: Sendable {
        var preparations: [String: Int] = [:]
        var preparedObjects: [String: String] = [:]
        var sequenceReads: [String: Int] = [:]
        var propertyPatches: [String: AnyJSON] = [:]
        var attemptedPropertySequences: [String: [Int64]] = [:]
        var fileDigests: [String: String] = [:]
    }
    private var values: [String: AnyJSON] = [:]
    private var sequence: [String: Int64] = [:]
    private var observed = Stats()
    private var failAfterPrepare: String?
    init(failAfterPrepare: String? = nil) { self.failAfterPrepare = failAfterPrepare }
    func stats() -> Stats { observed }
    func changeSequence(_ id: String, to value: Int64) { sequence[id] = value }
    func setTerminal(sourceKey: String, outcome: String) {
        for (key, value) in values where value["sourceKey"]?.string == sourceKey {
            var fields = value.object!; fields["outcome"] = .string(outcome); values[key] = .object(fields)
        }
    }
    func status(_ intent: AnyDestinationNativeIntent, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await authorize()
        guard let value = values[intent.identity.id] else { throw AnyEngineError.http(status: 404, code: "not_found") }; return value
    }
    func applySequence(objectID: String, authorize: @escaping AnyDestinationAuthorization) async throws -> Int64 {
        try await authorize(); observed.sequenceReads[objectID, default: 0] += 1
        guard let value = sequence[objectID] else { throw FixtureFailure.sequenceChanged }; return value
    }
    func prepare(_ intent: AnyDestinationNativeIntent, payload: URL?, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await authorize()
        if let existing = values[intent.identity.id] { return existing }
        let n = observed.preparations.values.reduce(0, +) + 1
        let metadata = try metadata(intent, number: n)
        let key = metadata["sourceKey"]!.string!
        if case .properties(let input) = intent {
            observed.attemptedPropertySequences[key, default: []].append(input.expectedApplySequence)
            guard sequence[input.objectID] == input.expectedApplySequence else { throw FixtureFailure.sequenceChanged }
            let spec = try JSONDecoder().decode(AnyJSON.self, from: input.specBytes)
            observed.propertyPatches[key] = spec["patch"]
        }
        if case .file(let input) = intent {
            guard let payload else { throw FixtureFailure.noPayload }
            let bytes = try Data(contentsOf: payload)
            guard Int64(bytes.count) == input.size, AnyContentDigest.sha256(bytes) == input.contentSHA256 else { throw FixtureFailure.noPayload }
            observed.fileDigests[key] = AnyContentDigest.sha256(bytes)
        }
        if case .inlineFile(let input) = intent { observed.fileDigests[key] = input.contentSHA256 }
        values[intent.identity.id] = .object(metadata)
        observed.preparations[key, default: 0] += 1; observed.preparedObjects[key] = metadata["objectId"]?.string
        if key == failAfterPrepare { failAfterPrepare = nil; throw AnyEngineError.writeUncertain }
        return .object(metadata)
    }
    func commit(_ intent: AnyDestinationNativeIntent, receipt: AnyJSON, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await authorize()
        var fields = try XCTUnwrap(values[intent.identity.id]?.object)
        if fields["outcome"]?.string == "committed" { return .object(fields) }
        let kind = fields["kind"]!.string!, object = fields["objectId"]!.string!
        fields["stage"] = .string("complete"); fields["outcome"] = .string("committed")
        if ["object", "typeDefinition", "collectionDefinition"].contains(kind) {
            fields["recordIds"] = .array([.string(object)])
            fields["changeId"] = .string("bootstrap-" + intent.identity.id)
        }
        if kind == "object" { sequence[object] = 1 }
        if kind == "propertyUpdate" { sequence[object, default: 0] += 1 }
        if kind == "file" { fields["localFileComplete"] = .bool(true) }
        values[intent.identity.id] = .object(fields); return .object(fields)
    }
    private func metadata(_ intent: AnyDestinationNativeIntent, number: Int) throws -> [String: AnyJSON] {
        let binding: AnyPreparedMigrationPlanBinding, sourceKey: String, contract: String, kind: String
        let stage: String, object: String, records: [String]
        var extra: [String: AnyJSON] = [:]
        let fresh = "destination-\(number)"
        switch intent {
        case .definition(let i):
            binding = i.binding; sourceKey = i.sourceKey; contract = AnyNativePreparedDefinitionMigration.contract; kind = i.kind.rawValue
            object = i.expectedOwnerID ?? fresh
            switch i.kind {
            case .typeDefinition, .collectionDefinition: stage = "definition-root-prepared"; records = []
            case .propertyDefinition: stage = "definition-property-prepared"; records = ["property-\(number)"]
            case .partDefinition: stage = "definition-part-prepared"; records = ["part-\(number)"]
            }
        case .object(let i):
            binding = i.binding; sourceKey = i.sourceKey; contract = AnyNativePreparedMigration.contract; kind = i.kind.rawValue
            object = i.expectedObjectID ?? fresh
            stage = i.kind == .object ? "root-prepared" : "block-prepared"
            records = i.kind == .object ? [] : ["block-\(number)"]
        case .properties(let i):
            binding = i.binding; sourceKey = i.sourceKey; contract = AnyNativePreparedPropertyUpdate.contract; kind = "propertyUpdate"
            object = i.objectID; stage = "properties-prepared"; records = [object]
        case .inlineFile(let i):
            binding = i.binding; sourceKey = i.sourceKey; contract = AnyNativePreparedInlineFileMigration.contract; kind = "inlineFile"
            object = fresh; stage = "file-prepared"; records = ["file-\(number)"]
            extra = ["fileId": .string(records[0]), "ownerObjectId": .string(i.ownerObjectID),
                     "size": .integer(Int64(i.size)), "contentSHA256": .string(i.contentSHA256)]
        case .file(let i):
            binding = i.binding; sourceKey = i.sourceKey; contract = AnyNativePreparedFileMigration.contract; kind = "file"
            object = fresh; stage = "file-prepared"; records = ["file-\(number)"]
            extra = ["fileId": .string(records[0]), "ownerObjectId": .string(i.ownerObjectID), "size": .integer(i.size),
                     "contentSHA256": .string(i.contentSHA256), "rootCid": .string("root-\(number)"),
                     "localFileComplete": .bool(false), "networkVerified": .bool(false)]
        }
        var value: [String: AnyJSON] = ["contract": .string(contract), "intentId": .string(intent.identity.id),
            "storeId": .string(binding.storeID), "accountId": .string(binding.workspace.accountID), "spaceId": .string(binding.workspace.spaceID),
            "planId": .string(binding.planID), "planSHA256": .string(binding.planSHA256), "sourceKey": .string(sourceKey), "kind": .string(kind),
            "specSHA256": .string(intent.identity.sha), "fingerprint": .string(AnyContentDigest.sha256(intent.identity.spec)),
            "stage": .string(stage), "outcome": .string("prepared"), "objectId": .string(object),
            "changeId": .string("signed-" + intent.identity.id), "recordIds": .array(records.map(AnyJSON.string))]
        if ["typeDefinition", "collectionDefinition", "object"].contains(kind) {
            // The signed root CID is also the native object's identity.
            value["changeId"] = .string(object)
        }
        value.merge(extra) { _, b in b }; return value
    }
}
