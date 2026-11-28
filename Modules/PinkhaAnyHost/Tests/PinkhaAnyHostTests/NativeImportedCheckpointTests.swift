import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

/// New local checkpoint controls. The driver is deliberately synthetic; no
/// original account, source capture, native HTTP or migration is replayed.
final class NativeImportedCheckpointTests: XCTestCase, @unchecked Sendable {
    func testCompletedCheckpointColdReadsKeepExactMappingsAndDoNotCallTheDriver() async throws {
        let parent = try directory(), plan = try makePlan()
        let driver = ImportedCheckpointFixtureDriver()
        let progress = try await complete(parent: parent, plan: plan, driver: driver)
        let calls = await driver.callCount()
        let before = try inventory(parent)
        let first = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: parent, binding: plan.binding)
        let cold = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: parent, binding: plan.binding)
        XCTAssertEqual(first.plan.canonicalBytes, plan.canonicalBytes)
        XCTAssertEqual(try encode(first.mappings), try encode(progress.mappings))
        XCTAssertEqual(try encode(cold.mappings), try encode(first.mappings))
        XCTAssertEqual(first.checkpointSHA256, cold.checkpointSHA256)
        XCTAssertEqual(first.mappings.map(\.sourceKey), plan.items.map(\.sourceKey))
        XCTAssertEqual(first.nativeOperationsPerformed, 0)
        XCTAssertFalse(first.provesCurrentNativeState)
        let finalCalls = await driver.callCount()
        XCTAssertEqual(finalCalls, calls)
        XCTAssertEqual(try inventory(parent), before)
    }

    func testMissingAndIncompleteCheckpointNeverCreatesOrReconcilesJournalEntries() async throws {
        let parent = try directory(), plan = try makePlan()
        let empty = try inventory(parent)
        XCTAssertThrowsError(try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: parent, binding: plan.binding)) { error in
            XCTAssertEqual(error as? AnyDestinationMigrationError, .journalUnavailable)
        }
        XCTAssertEqual(try inventory(parent), empty)
        let driver = ImportedCheckpointFixtureDriver()
        let executor = AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver,
            checkpointHook: { _ in throw ImportedCheckpointFixtureFailure.interrupted })
        do {
            _ = try await executor.execute(plan: plan, payloads: { _ in
                throw ImportedCheckpointFixtureFailure.unexpectedPayload
            }, verifySource: { _ in }, authorize: {})
            XCTFail("the deliberate pre-dispatch checkpoint interruption was ignored")
        } catch ImportedCheckpointFixtureFailure.interrupted {}
        let before = try inventory(parent), calls = await driver.callCount()
        XCTAssertThrowsError(try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: parent, binding: plan.binding)) { error in
            XCTAssertEqual(error as? AnyDestinationMigrationError, .journalCorrupt)
        }
        let finalCalls = await driver.callCount()
        XCTAssertEqual(finalCalls, calls)
        XCTAssertEqual(try inventory(parent), before)
    }

    func testOriginalExclusiveWriterAndSharedColdReaderUseOneLockWithoutWrites() async throws {
        let parent = try directory(), plan = try makePlan()
        _ = try await complete(parent: parent, plan: plan, driver: ImportedCheckpointFixtureDriver())
        do {
            let writer = try AnyDestinationMigrationJournal(parent: parent, plan: plan)
            try withExtendedLifetime(writer) {
                XCTAssertThrowsError(try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
                    journalDirectory: parent, binding: plan.binding)) { error in
                    XCTAssertEqual(error as? AnyDestinationMigrationError, .alreadyExecuting)
                }
            }
        }
        let before = try inventory(parent)
        do {
            let reader = try AnyDestinationMigrationJournal(readOnlyParent: parent, expectedBinding: plan.binding)
            try withExtendedLifetime(reader) {
                XCTAssertThrowsError(try AnyDestinationMigrationJournal(parent: parent, plan: plan)) { error in
                    XCTAssertEqual(error as? AnyDestinationMigrationError, .alreadyExecuting)
                }
                let entry = try XCTUnwrap(reader.load(index: 0))
                XCTAssertThrowsError(try reader.save(entry)) { error in
                    XCTAssertEqual(error as? AnyDestinationMigrationError, .journalUnavailable)
                }
                let secondReader = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
                    journalDirectory: parent, binding: plan.binding)
                XCTAssertEqual(secondReader.plan.canonicalBytes, plan.canonicalBytes)
                try reader.finishReadOnly()
            }
        }
        XCTAssertEqual(try inventory(parent), before)
        let writer = try AnyDestinationMigrationJournal(parent: parent, plan: plan)
        withExtendedLifetime(writer) {}
    }

    func testChangedReceiptIdentityRefusesEvenWhenItsJournalEnvelopeIsValid() async throws {
        let parent = try directory(), plan = try makePlan()
        let driver = ImportedCheckpointFixtureDriver()
        _ = try await complete(parent: parent, plan: plan, driver: driver)
        do {
            let journal = try AnyDestinationMigrationJournal(parent: parent, plan: plan)
            var entry = try XCTUnwrap(journal.load(index: 0))
            XCTAssertGreaterThanOrEqual(entry.receipts.count, 2)
            var last = try XCTUnwrap(entry.receipts.last?.object)
            last["objectId"] = .string("foreign-owner")
            entry.receipts[entry.receipts.count - 1] = .object(last)
            try journal.save(entry)
        }
        let before = try inventory(parent), calls = await driver.callCount()
        XCTAssertThrowsError(try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: parent, binding: plan.binding))
        let finalCalls = await driver.callCount()
        XCTAssertEqual(finalCalls, calls)
        XCTAssertEqual(try inventory(parent), before)
    }

    func testExactBindingRejectsUnicodeAliasAndChangedPlanWithoutRepair() async throws {
        let parent = try directory(), plan = try makePlan(accountID: "caf\u{e9}")
        _ = try await complete(parent: parent, plan: plan, driver: ImportedCheckpointFixtureDriver())
        let before = try inventory(parent)
        let unicodeAlias = try AnyPreparedMigrationPlanBinding(
            workspace: .init(accountID: "cafe\u{301}", spaceID: plan.binding.workspace.spaceID),
            storeID: plan.binding.storeID, planID: plan.binding.planID, planSHA256: plan.binding.planSHA256)
        XCTAssertNotEqual(Data(unicodeAlias.workspace.accountID.utf8), Data(plan.binding.workspace.accountID.utf8))
        XCTAssertThrowsError(try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: parent, binding: unicodeAlias))
        let changedPlan = try AnyPreparedMigrationPlanBinding(workspace: plan.binding.workspace,
            storeID: plan.binding.storeID, planID: plan.binding.planID, planSHA256: digest("different-plan"))
        XCTAssertThrowsError(try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: parent, binding: changedPlan)) { error in
            XCTAssertEqual(error as? AnyDestinationMigrationError, .changedPlan)
        }
        XCTAssertEqual(try inventory(parent), before)
    }

    func testAliasAndReplacedOwnerLockRefuseBeforeColdDelivery() async throws {
        let parent = try directory(), plan = try makePlan()
        _ = try await complete(parent: parent, plan: plan, driver: ImportedCheckpointFixtureDriver())
        let alias = parent.appendingPathComponent("journal-alias", isDirectory: true)
        try FileManager.default.createSymbolicLink(at: alias, withDestinationURL: parent)
        let beforeAlias = try inventory(parent)
        XCTAssertThrowsError(try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: alias, binding: plan.binding)) { error in
            XCTAssertEqual(error as? AnyDestinationMigrationError, .journalUnavailable)
        }
        XCTAssertEqual(try inventory(parent), beforeAlias)
        let reader = try AnyDestinationMigrationJournal(readOnlyParent: parent, expectedBinding: plan.binding)
        let directory = scopeDirectory(parent: parent, binding: plan.binding)
        let owner = directory.appendingPathComponent("owner.lock")
        let retained = parent.appendingPathComponent("retained-owner.lock")
        try FileManager.default.moveItem(at: owner, to: retained)
        try Data().write(to: owner, options: .withoutOverwriting)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: owner.path)
        let beforeDelivery = try inventory(parent)
        try withExtendedLifetime(reader) {
            XCTAssertThrowsError(try reader.finishReadOnly()) { error in
                XCTAssertEqual(error as? AnyDestinationMigrationError, .journalCorrupt)
            }
        }
        XCTAssertEqual(try inventory(parent), beforeDelivery)
    }

    func testCancelledColdReadLeavesCompletedCheckpointAndDriverUntouched() async throws {
        let parent = try directory(), plan = try makePlan()
        let driver = ImportedCheckpointFixtureDriver()
        _ = try await complete(parent: parent, plan: plan, driver: driver)
        let before = try inventory(parent), calls = await driver.callCount()
        let task = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            return try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
                journalDirectory: parent, binding: plan.binding)
        }
        do {
            _ = try await task.value
            XCTFail("cancelled cold read returned private mappings")
        } catch is CancellationError {}
        let finalCalls = await driver.callCount()
        XCTAssertEqual(finalCalls, calls)
        XCTAssertEqual(try inventory(parent), before)
    }

    private func complete(parent: URL, plan: AnyDestinationMigrationPlan,
                          driver: ImportedCheckpointFixtureDriver) async throws -> AnyDestinationMigrationProgress {
        try await AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver).execute(
            plan: plan, payloads: { _ in throw ImportedCheckpointFixtureFailure.unexpectedPayload },
            verifySource: { _ in }, authorize: {})
    }

    private func makePlan(accountID: String = "destination-account") throws -> AnyDestinationMigrationPlan {
        let source = try AnyDestinationSourceBinding(accountID: "synthetic-source-account", spaceID: "synthetic-source-space",
            witnessSHA256: digest("synthetic-witness"), captureManifestSHA256: digest("synthetic-capture"),
            semanticPlanSHA256: digest("synthetic-plan"), sourceObjectIDs: ["original-first", "original-second"])
        let items: [AnyDestinationMigrationItem] = [
            .init(sourceKey: "first", sourceObjectID: "original-first",
                  operation: .object(type: .native("page"), collections: [],
                                     initialProperties: .literal(.object(["any": .object(["name": .string("e\u{301} שלום")])])))),
            .init(sourceKey: "second", sourceObjectID: "original-second",
                  operation: .object(type: .native("page"), collections: [],
                                     initialProperties: .literal(.object(["any": .object(["name": .string("second")])])))),
            .init(sourceKey: "body", sourceObjectID: "original-first",
                  operation: .editorBlock(owner: .mapped(sourceKey: "first", slot: .objectID, encoding: .rawID),
                    dataset: "editor_blocks", type: "paragraph", text: "exact e\u{301} 😀",
                    style: .literal(.object([:])), parent: nil, position: "A"))
        ]
        return try .init(source: source,
            workspace: .init(accountID: accountID, spaceID: "destination-space"), storeID: "destination-store",
            planID: digest("fixed-local-checkpoint"),
            coverage: [
                .init(sourceObjectID: "original-first", disposition: .mapped(itemSourceKeys: ["first", "body"])),
                .init(sourceObjectID: "original-second", disposition: .mapped(itemSourceKeys: ["second"]))
            ], items: items)
    }

    private func directory() throws -> URL {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_IMPORTED_CONTEXT_FIXTURE_ROOT"] else {
            throw XCTSkip("Requires the separately owned imported-context component fixture root.")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true)
        var info = stat()
        guard lstat(root.path, &info) == 0, info.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR),
              info.st_uid == geteuid(), info.st_mode & mode_t(0o7777) == mode_t(0o700) else {
            throw ImportedCheckpointFixtureFailure.unsafeRoot
        }
        let target = root.appendingPathComponent("checkpoint-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: false,
                                               attributes: [.posixPermissions: 0o700])
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: target.path)
        addTeardownBlock { try FileManager.default.removeItem(at: target) }
        return target
    }

    private func scopeDirectory(parent: URL, binding: AnyPreparedMigrationPlanBinding) -> URL {
        let hash = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            binding.workspace.accountID, binding.workspace.spaceID, binding.storeID, binding.planID]))
        return parent.appendingPathComponent("AnyDestinationMigrationV1", isDirectory: true)
            .appendingPathComponent(hash, isDirectory: true)
    }

    private func inventory(_ root: URL) throws -> [String: String] {
        var rows: [String: String] = [:], paths = [root]
        var index = 0, total = 0
        while index < paths.count {
            let path = paths[index]; index += 1
            guard paths.count <= 32 else { throw ImportedCheckpointFixtureFailure.unsafeRoot }
            var value = stat()
            guard lstat(path.path, &value) == 0 else { throw ImportedCheckpointFixtureFailure.unsafeRoot }
            let kind = value.st_mode & mode_t(S_IFMT)
            let payload: String
            if kind == mode_t(S_IFDIR) {
                paths += try FileManager.default.contentsOfDirectory(at: path, includingPropertiesForKeys: nil)
                    .sorted { Data($0.lastPathComponent.utf8).lexicographicallyPrecedes(Data($1.lastPathComponent.utf8)) }
                payload = "directory"
            } else if kind == mode_t(S_IFREG) {
                guard value.st_size >= 0, Int64(value.st_size) <= Int64(1_048_576 - total) else {
                    throw ImportedCheckpointFixtureFailure.unsafeRoot
                }
                let bytes = try Data(contentsOf: path); total += bytes.count
                payload = AnyContentDigest.sha256(bytes)
            } else if kind == mode_t(S_IFLNK) {
                payload = try FileManager.default.destinationOfSymbolicLink(atPath: path.path)
            } else { throw ImportedCheckpointFixtureFailure.unsafeRoot }
            #if canImport(Darwin)
            let times = "\(value.st_mtimespec.tv_sec):\(value.st_mtimespec.tv_nsec):\(value.st_ctimespec.tv_sec):\(value.st_ctimespec.tv_nsec)"
            #else
            let times = "\(value.st_mtim.tv_sec):\(value.st_mtim.tv_nsec):\(value.st_ctim.tv_sec):\(value.st_ctim.tv_nsec)"
            #endif
            rows[path.path] = "\(value.st_dev):\(value.st_ino):\(value.st_mode):\(value.st_nlink):\(value.st_uid):\(value.st_gid):\(value.st_size):\(times):\(payload)"
        }
        return rows
    }

    private func encode<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    private func digest(_ value: String) -> String { AnyContentDigest.sha256(Data(value.utf8)) }
}

private enum ImportedCheckpointFixtureFailure: Error { case interrupted, unexpectedPayload, unsafeRoot }

/// Uses the existing executor and original typed receipt validators. It cannot
/// access native state; call counts make any accidental reconciliation visible.
private actor ImportedCheckpointFixtureDriver: AnyDestinationNativeDriving {
    private var receipts: [String: AnyJSON] = [:]
    private var calls = 0
    func callCount() -> Int { calls }

    func status(_ intent: AnyDestinationNativeIntent, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        calls += 1; try await authorize()
        guard let value = receipts[intent.identity.id] else {
            throw AnyEngineError.http(status: 404, code: "not_found")
        }
        return value
    }

    func prepare(_ intent: AnyDestinationNativeIntent, payload: URL?,
                 authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        calls += 1; try await authorize()
        guard case .object(let value) = intent, payload == nil else {
            throw ImportedCheckpointFixtureFailure.unexpectedPayload
        }
        if let old = receipts[intent.identity.id] { return old }
        let object = value.expectedObjectID ?? "fixture-" + value.sourceKey
        let root = value.kind == .object
        let raw: AnyJSON = .object([
            "contract": .string(AnyNativePreparedMigration.contract),
            "intentId": .string(value.intentID), "storeId": .string(value.binding.storeID),
            "accountId": .string(value.binding.workspace.accountID), "spaceId": .string(value.binding.workspace.spaceID),
            "planId": .string(value.binding.planID), "planSHA256": .string(value.binding.planSHA256),
            "sourceKey": .string(value.sourceKey), "kind": .string(value.kind.rawValue),
            "specSHA256": .string(value.specSHA256), "fingerprint": .string(AnyContentDigest.sha256(value.specBytes)),
            "stage": .string(root ? "root-prepared" : "block-prepared"), "outcome": .string("prepared"),
            "objectId": .string(object), "changeId": .string(root ? object : "signed-" + value.intentID),
            "recordIds": .array(root ? [] : [.string("fixture-block-" + value.sourceKey)])
        ])
        receipts[value.intentID] = raw
        return raw
    }

    func commit(_ intent: AnyDestinationNativeIntent, receipt: AnyJSON,
                authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        calls += 1; try await authorize()
        var fields = try XCTUnwrap(receipts[intent.identity.id]?.object)
        fields["stage"] = .string("complete"); fields["outcome"] = .string("committed")
        if fields["kind"] == .string("object") {
            fields["recordIds"] = .array([try XCTUnwrap(fields["objectId"])])
            fields["changeId"] = .string("bootstrap-" + intent.identity.id)
        }
        let value = AnyJSON.object(fields); receipts[intent.identity.id] = value; return value
    }

    func applySequence(objectID: String, authorize: @escaping AnyDestinationAuthorization) async throws -> Int64 {
        calls += 1; throw ImportedCheckpointFixtureFailure.unexpectedPayload
    }
}
