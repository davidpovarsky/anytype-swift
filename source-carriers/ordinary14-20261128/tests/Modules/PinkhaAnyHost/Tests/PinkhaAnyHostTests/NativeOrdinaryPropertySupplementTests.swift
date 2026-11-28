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

/// New source-bound component controls for the recovered fourteen definitions.
/// Native effects are synthetic. The original 182 operations are never run.
/// A later native proof must separately qualify actual schema, edits and reopen.
final class NativeOrdinaryPropertySupplementTests: XCTestCase, @unchecked Sendable {
    func testOriginal182CanonicalPlanAndNilEncodingStayByteIdentical() throws {
        let fixture = try Ordinary14Fixture.load()
        let original = fixture.retained.plan
        let raw = try Data(contentsOf: fixture.retained.planURL)
        XCTAssertEqual(AnyContentDigest.sha256(raw),
            "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930")
        XCTAssertEqual(original.items.count, 182)
        XCTAssertNil(original.importedPropertyNamespace)
        let legacy = Ordinary14LegacyContent(version: AnyDestinationMigrationPlan.version,
            source: original.source,
            target: .init(accountID: original.binding.workspace.accountID,
                spaceID: original.binding.workspace.spaceID, storeID: original.binding.storeID,
                planID: original.binding.planID), coverage: original.coverage, items: original.items)
        let legacyBytes = try Ordinary14Wire.encode(legacy)
        XCTAssertEqual(original.canonicalBytes, legacyBytes)
        XCTAssertEqual(AnyContentDigest.sha256(legacyBytes), original.binding.planSHA256)
        let envelope = try Ordinary14Wire.json(original)
        XCTAssertNil(envelope["content"]?["importedPropertyNamespace"])
        let decoded = try AnyDestinationMigrationPlan.decode(Ordinary14Wire.encode(original))
        XCTAssertEqual(decoded.canonicalBytes, legacyBytes)
        XCTAssertEqual(decoded.binding, original.binding)

        let namespace = fixture.supplement.namespace
        let namespaceRoundtrip = try JSONDecoder().decode(AnyDestinationImportedPropertyNamespace.self,
            from: Ordinary14Wire.encode(namespace))
        XCTAssertEqual(namespaceRoundtrip.originalPlanBytes, namespace.originalPlanBytes)
        XCTAssertEqual(namespaceRoundtrip.binding, original.binding)
        XCTAssertEqual(namespaceRoundtrip.intent, namespace.intent)
        XCTAssertFalse(namespaceRoundtrip.permitsDestinationWrites)
        let mappingsAgain = try JSONDecoder().decode([AnyDestinationMigrationMapping].self,
            from: Data(contentsOf: fixture.retained.mappingsURL))
        XCTAssertEqual(try Ordinary14Wire.encode(fixture.retained.mappings), try Ordinary14Wire.encode(mappingsAgain))
        XCTAssertEqual(fixture.retained.plan.canonicalBytes, legacyBytes)
        try fixture.retained.requireRetainedInputsUnchanged()
    }

    func testFourteenOriginalDefinitionsRetainExactShapesAndOutsideBlockers() throws {
        let fixture = try Ordinary14Fixture.load()
        let supplement = fixture.supplement
        let expectedKeys = ["aperture", "artist", "audioAlbum", "audioAlbumTrackNumber",
            "audioGenre", "audioLyrics", "camera", "cameraIso", "done", "exposure",
            "focalRatio", "releasedYear", "source", "tag"]
        XCTAssertEqual(AnyHeartNativeOrdinaryPropertySupplement.relationKeys, expectedKeys)
        XCTAssertEqual(supplement.sourceRelations.map(\.relationKey), expectedKeys)
        XCTAssertEqual(supplement.plan.items.count, 14)
        XCTAssertEqual(supplement.plan.source.sourceObjectIDs.count, 14)
        XCTAssertEqual(supplement.plan.source.definitionManifestBytes,
            fixture.retained.plan.source.definitionManifestBytes)
        XCTAssertEqual(supplement.plan.blockers, [])
        XCTAssertFalse(supplement.permitsSourceAdmission)
        XCTAssertFalse(supplement.permitsDestinationWrites)
        XCTAssertNotEqual(supplement.plan.binding.planID, fixture.retained.plan.binding.planID)
        let originalKeys = Set(fixture.retained.plan.items.map { Data($0.sourceKey.utf8) })
        var kinds: [String: Int] = [:]
        for (item, relation) in zip(supplement.plan.items, supplement.sourceRelations) {
            XCTAssertFalse(originalKeys.contains(Data(item.sourceKey.utf8)))
            XCTAssertEqual(item.sourceObjectID, relation.objectID)
            XCTAssertEqual(item.expectedRecordCount, 1)
            guard case .propertyDefinition(.native(let owner), let kind, _, _, _, let scope,
                                           .some(.literal(let format)), _) = item.operation else {
                return XCTFail("Only a native-owner property definition belongs to this supplement.")
            }
            XCTAssertEqual(Data(owner.utf8), Data(supplement.namespace.ownerID.utf8))
            XCTAssertEqual(scope, "synced")
            kinds[kind, default: 0] += 1
            let key = relation.relationKey
            let expectedFormat = ["audioAlbumTrackNumber", "cameraIso", "focalRatio", "releasedYear"].contains(key)
                ? "number" : key == "done" ? "checkbox" : key == "source" ? "url" : key == "tag" ? "choice" : "longtext"
            XCTAssertEqual(format["type"], .string(expectedFormat))
            XCTAssertEqual(format["pinkhaHeart"]?["sourceObjectID"], .string(relation.objectID))
            XCTAssertEqual(format["pinkhaHeart"]?["sourceUniqueKey"], .string("rel-" + key))
            XCTAssertEqual(format["pinkhaHeart"]?["snapshotSHA256"], .string(relation.snapshot.snapshotSHA256))
            XCTAssertEqual(format["pinkhaHeart"]?["jsonViewSHA256"], .string(relation.snapshot.viewSHA256))
            let details = try XCTUnwrap(format["pinkhaHeart"]?["definitionJSON"]?.string)
            XCTAssertEqual(try Ordinary14Wire.encode(JSONDecoder().decode(AnyJSON.self, from: Data(details.utf8))),
                try Ordinary14Wire.encode(AnyJSON.object(relation.snapshot.details)))
            XCTAssertEqual(relation.defaultValue, .null)
            XCTAssertEqual(relation.readonlyValue, false)
            XCTAssertEqual(relation.maximumCount, key == "tag" ? 0 : 1)
            if key == "tag" {
                XCTAssertEqual(format["config"]?["multiple"], .bool(true))
                XCTAssertEqual(format["options"], .object([:]))
            }
        }
        XCTAssertEqual(kinds, ["string": 8, "number": 4, "boolean": 1, "array": 1])
        let selected = Set(supplement.sourceRelations.map { Data($0.objectID.utf8) })
        let definitions = try AnyHeartNativeDefinitionPlan(catalog: fixture.catalog)
        let expectedIssues = definitions.issues.filter { !selected.contains(Data($0.sourceObjectID.utf8)) }
        XCTAssertFalse(expectedIssues.isEmpty)
        XCTAssertEqual(supplement.outsideSliceIssues.map(Ordinary14Fixture.issueIdentity),
            expectedIssues.map(Ordinary14Fixture.issueIdentity))
        XCTAssertEqual(Set(supplement.outsideSliceRelationObjectIDs.map { Data($0.utf8) }),
            Set(fixture.catalog.relations.map { Data($0.objectID.utf8) }).subtracting(selected))
        try fixture.retained.requireRetainedInputsUnchanged()
    }

    func testExternalNamespaceRefusesForeignScopeAndArbitraryOwnerInjection() throws {
        let fixture = try Ordinary14Fixture.load()
        let plan = fixture.supplement.plan
        let namespace = fixture.supplement.namespace
        for workspace in [
            AnyTorahWorkspace(accountID: plan.binding.workspace.accountID + "-foreign", spaceID: plan.binding.workspace.spaceID),
            AnyTorahWorkspace(accountID: plan.binding.workspace.accountID, spaceID: plan.binding.workspace.spaceID + "-foreign")
        ] {
            XCTAssertThrowsError(try AnyDestinationMigrationPlan(source: plan.source, workspace: workspace,
                storeID: plan.binding.storeID, planID: plan.binding.planID, coverage: plan.coverage,
                items: plan.items, importedPropertyNamespace: namespace))
        }
        XCTAssertThrowsError(try AnyDestinationMigrationPlan(source: plan.source, workspace: plan.binding.workspace,
            storeID: plan.binding.storeID + "-foreign", planID: plan.binding.planID, coverage: plan.coverage,
            items: plan.items, importedPropertyNamespace: namespace))
        XCTAssertThrowsError(try AnyDestinationMigrationPlan(source: plan.source, workspace: plan.binding.workspace,
            storeID: plan.binding.storeID, planID: namespace.binding.planID, coverage: plan.coverage,
            items: plan.items, importedPropertyNamespace: namespace))
        // The legacy nil contract still refuses an existing external owner.
        XCTAssertThrowsError(try AnyDestinationMigrationPlan(source: plan.source, workspace: plan.binding.workspace,
            storeID: plan.binding.storeID, planID: plan.binding.planID, coverage: plan.coverage, items: plan.items))
        let first = try XCTUnwrap(plan.items.first)
        guard case .propertyDefinition(_, let kind, let name, let key, let description, _, let format, let index) = first.operation else {
            return XCTFail("The fixed slice must begin with a property.")
        }
        for (owner, scope) in [(namespace.ownerID + "-foreign", "synced"), (namespace.ownerID, "local")] {
            var items = plan.items
            items[0] = .init(sourceKey: first.sourceKey, sourceObjectID: first.sourceObjectID,
                operation: .propertyDefinition(owner: .native(owner), kind: kind, name: name,
                    xKey: key, description: description, scope: scope, xFormat: format, index: index))
            XCTAssertThrowsError(try AnyDestinationMigrationPlan(source: plan.source, workspace: plan.binding.workspace,
                storeID: plan.binding.storeID, planID: plan.binding.planID, coverage: plan.coverage,
                items: items, importedPropertyNamespace: namespace))
        }
        var objectItems = plan.items
        objectItems[0] = .init(sourceKey: first.sourceKey, sourceObjectID: first.sourceObjectID,
            operation: .object(type: .native("page"), collections: [], initialProperties: .literal(.object([:]))))
        XCTAssertThrowsError(try namespace.requireSupplement(source: plan.source, binding: plan.binding, items: objectItems))
        var envelope = try XCTUnwrap(Ordinary14Wire.json(namespace).object)
        var mapping = try XCTUnwrap(envelope["mapping"]?.object)
        mapping["intentID"] = .string(String(repeating: "0", count: 64))
        envelope["mapping"] = .object(mapping)
        XCTAssertThrowsError(try JSONDecoder().decode(AnyDestinationImportedPropertyNamespace.self,
            from: Ordinary14Wire.encode(AnyJSON.object(envelope))))
        try fixture.retained.requireRetainedInputsUnchanged()
    }

    func testNamespaceReceiptUsesOriginalIntentAndExactUTF8Identity() throws {
        let fixture = try Ordinary14Fixture.load()
        let namespace = fixture.supplement.namespace
        let committed = try Ordinary14Fixture.namespaceReceipt(namespace)
        XCTAssertEqual(try namespace.requireCurrentReceipt(committed).outcome, .committed)
        let modified = try Ordinary14Wire.replacing(committed, "outcome", .string("committed_modified"))
        XCTAssertEqual(try namespace.requireCurrentReceipt(modified).outcome, .committedModified)
        for outcome in ["committed_deleted", "obsolete"] {
            let value = try Ordinary14Wire.replacing(committed, "outcome", .string(outcome))
            // These are valid typed receipts, then refused by current-namespace admission.
            XCTAssertNoThrow(try AnyPreparedDefinitionReceipt(value, intent: namespace.intent))
            XCTAssertThrowsError(try namespace.requireCurrentReceipt(value))
        }
        var prepared = try XCTUnwrap(committed.object)
        prepared["stage"] = .string("definition-root-prepared"); prepared["outcome"] = .string("prepared")
        prepared["changeId"] = .string(namespace.ownerID); prepared["recordIds"] = .array([])
        XCTAssertNoThrow(try AnyPreparedDefinitionReceipt(.object(prepared), intent: namespace.intent))
        XCTAssertThrowsError(try namespace.requireCurrentReceipt(.object(prepared)))
        for (key, replacement) in [
            ("accountId", namespace.binding.workspace.accountID + "-foreign"),
            ("spaceId", namespace.binding.workspace.spaceID + "-foreign"),
            ("storeId", namespace.binding.storeID + "-foreign"),
            ("planId", namespace.binding.planID + "-foreign"),
            ("planSHA256", String(repeating: "3", count: 64)),
            ("intentId", String(repeating: "1", count: 64)),
            ("fingerprint", String(repeating: "2", count: 64))
        ] {
            XCTAssertThrowsError(try namespace.requireCurrentReceipt(
                Ordinary14Wire.replacing(committed, key, .string(replacement))), key)
        }

        // Native IDs are printable ASCII. Use a valid synthetic owner for the
        // positive receipt/root checks; this is not native creation evidence.
        var wire = try XCTUnwrap(Ordinary14Wire.json(namespace).object)
        var row = try XCTUnwrap(wire["mapping"]?.object)
        row["objectID"] = .string("namespace-owner")
        row["recordIDs"] = .array([.string("namespace-owner")])
        wire["mapping"] = .object(row)
        XCTAssertTrue(AnyEditorBlock.validID("namespace-owner"))
        let synthetic = try JSONDecoder().decode(AnyDestinationImportedPropertyNamespace.self,
            from: Ordinary14Wire.encode(AnyJSON.object(wire)))
        let exact = try Ordinary14Fixture.namespaceReceipt(synthetic)
        XCTAssertNoThrow(try synthetic.requireCurrentReceipt(exact))
        var alias = try XCTUnwrap(exact.object)
        alias["objectId"] = .string("namespace-Owner")
        alias["recordIds"] = .array([.string("namespace-Owner")])
        XCTAssertTrue(AnyEditorBlock.validID("namespace-Owner"))
        XCTAssertNotEqual(Data("namespace-owner".utf8), Data("namespace-Owner".utf8))
        XCTAssertThrowsError(try synthetic.requireCurrentReceipt(.object(alias)))
        let root = try Ordinary14Fixture.root(synthetic)
        XCTAssertNoThrow(try synthetic.requireCurrentRoot(root))
        XCTAssertThrowsError(try synthetic.requireCurrentRoot(
            Ordinary14Wire.replacing(root, "id", .string("namespace-Owner"))))

        // Both Unicode spellings fail the original ID parser before a namespace
        // can be constructed. Neither is a valid positive native-ID fixture.
        let composed = "namespace-\u{e9}", decomposed = "namespace-e\u{301}"
        XCTAssertNotEqual(Data(composed.utf8), Data(decomposed.utf8))
        for invalidID in [composed, decomposed] {
            XCTAssertFalse(AnyEditorBlock.validID(invalidID))
            var invalidWire = wire
            var invalidRow = row
            invalidRow["objectID"] = .string(invalidID)
            invalidRow["recordIDs"] = .array([.string(invalidID)])
            invalidWire["mapping"] = .object(invalidRow)
            XCTAssertThrowsError(try JSONDecoder().decode(AnyDestinationImportedPropertyNamespace.self,
                from: Ordinary14Wire.encode(AnyJSON.object(invalidWire)))) { error in
                guard let migrationError = error as? AnyDestinationMigrationError,
                      case .invalidPlan(let reason) = migrationError else {
                    return XCTFail("The original native ID guard must reject the fixture.")
                }
                XCTAssertEqual(reason, "original namespace identity")
            }
        }
        try fixture.retained.requireRetainedInputsUnchanged()
    }

    func testMissingObsoleteOrForeignNamespaceRefusesBeforeJournalOrNewWrites() async throws {
        let fixture = try Ordinary14Fixture.load()
        for mode in [Ordinary14FixtureDriver.Mode.missingNamespace, .obsoleteNamespace, .foreignRoot] {
            let parent = try directory()
            let driver = try Ordinary14FixtureDriver(supplement: fixture.supplement, mode: mode)
            do {
                _ = try await execute(fixture.supplement.plan, parent: parent, driver: driver)
                XCTFail("An unavailable original namespace must stop before a new journal.")
            } catch AnyEngineError.http(let status, _) where mode == .missingNamespace {
                XCTAssertEqual(status, 404)
            } catch AnyDestinationMigrationError.changedIdentity(_) {
                XCTAssertNotEqual(mode, .missingNamespace)
            }
            let counts = await driver.counts()
            XCTAssertEqual(counts.prepared, [])
            XCTAssertEqual(counts.committed, [])
            XCTAssertEqual(counts.originalWrites, 0)
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: parent.path), [])
        }
        try fixture.retained.requireRetainedInputsUnchanged()
    }

    func testNamespaceObservationRefusesRootOrReceiptDriftBetweenReads() async throws {
        let fixture = try Ordinary14Fixture.load()
        for mode in [Ordinary14FixtureDriver.Mode.changedRoot, .changedReceipt] {
            let driver = try Ordinary14FixtureDriver(supplement: fixture.supplement, mode: mode)
            do {
                try await fixture.supplement.namespace.observe(using: driver, authorize: {})
                XCTFail("A changing prerequisite must not be delivered.")
            } catch AnyDestinationMigrationError.changedIdentity(_) {}
            let counts = await driver.counts()
            XCTAssertEqual(counts.namespaceRoots, 2)
            XCTAssertEqual(counts.namespaceStatuses, mode == .changedRoot ? 1 : 2)
            XCTAssertEqual(counts.prepared, [])
            XCTAssertEqual(counts.committed, [])
            XCTAssertEqual(counts.originalWrites, 0)
        }
        try fixture.retained.requireRetainedInputsUnchanged()
    }

    func testCurrentAuthorizationRevocationStopsBeforeTheNextDurableEffect() async throws {
        let fixture = try Ordinary14Fixture.load(), parent = try directory()
        let gate = Ordinary14Authorization()
        let driver = try Ordinary14FixtureDriver(supplement: fixture.supplement, mode: .normal,
            afterFirstPrepare: { await gate.revoke() })
        do {
            _ = try await execute(fixture.supplement.plan, parent: parent, driver: driver,
                authorize: { try await gate.check() })
            XCTFail("Revocation after preparation must stop before commitment.")
        } catch Ordinary14FixtureFailure.revoked {}
        let stopped = await driver.counts()
        XCTAssertEqual(stopped.prepared.count, 1)
        XCTAssertEqual(stopped.committed, [])
        XCTAssertEqual(stopped.originalWrites, 0)
        let before = try journalDigest(parent)
        do {
            _ = try await execute(fixture.supplement.plan, parent: parent, driver: driver,
                authorize: { try await gate.check() })
            XCTFail("A revoked caller cannot resume a prepared intent.")
        } catch Ordinary14FixtureFailure.revoked {}
        let after = await driver.counts()
        XCTAssertEqual(after, stopped)
        XCTAssertEqual(try journalDigest(parent), before)
        try fixture.retained.requireRetainedInputsUnchanged()
    }

    func testLostAcknowledgementResumesOnlyFourteenIntentsAndMergesTheirReceiptBindings() async throws {
        let fixture = try Ordinary14Fixture.load(), parent = try directory()
        let supplement = fixture.supplement
        let driver = try Ordinary14FixtureDriver(supplement: supplement, mode: .lostFirstCommit)
        do {
            _ = try await execute(supplement.plan, parent: parent, driver: driver)
            XCTFail("The first lost acknowledgement must escape without an internal retry.")
        } catch Ordinary14FixtureFailure.lostAcknowledgement {}
        let failed = await driver.counts()
        XCTAssertEqual(failed.prepared.count, 1)
        XCTAssertEqual(failed.committed.count, 1)
        XCTAssertEqual(failed.originalWrites, 0)
        let progress = try await execute(supplement.plan, parent: parent, driver: driver)
        XCTAssertTrue(progress.allItemsReconciled)
        XCTAssertEqual(progress.totalItems, 14)
        let complete = await driver.counts()
        XCTAssertEqual(complete.prepared.count, 14)
        XCTAssertEqual(complete.committed.count, 14)
        XCTAssertEqual(Set(complete.prepared).count, 14)
        XCTAssertEqual(Set(complete.committed).count, 14)
        XCTAssertEqual(complete.originalWrites, 0)
        XCTAssertFalse(complete.prepared.contains(supplement.namespace.intent.intentID))
        XCTAssertFalse(complete.committed.contains(supplement.namespace.intent.intentID))

        let old = try AnyNativeImportedDefinitionDirectory(plan: fixture.retained.plan, mappings: fixture.retained.mappings)
        let directory = try supplement.directory(mappings: progress.mappings)
        XCTAssertEqual(directory.binding, old.binding)
        XCTAssertEqual(directory.entries.count, old.entries.count + 14)
        XCTAssertEqual(directory.supplementalPropertyBindings, [supplement.plan.binding])
        for mapping in progress.mappings {
            let entry = try XCTUnwrap(directory.definition(sourceObjectID: mapping.sourceObjectID))
            XCTAssertEqual(entry.intent?.binding, supplement.plan.binding)
            XCTAssertEqual(entry.intent?.intentID, mapping.intentID)
            XCTAssertEqual(entry.mapping?.currentReceiptSHA256, mapping.currentReceiptSHA256)
            XCTAssertEqual(entry.address, .property(ownerKind: .collection,
                key: try .init(ownerID: supplement.namespace.ownerID, propertyID: try XCTUnwrap(mapping.recordIDs.first))))
            XCTAssertFalse(entry.permitsDestinationWrites)
        }
        for entry in old.entries {
            let retained = try XCTUnwrap(directory.definition(sourceObjectID: entry.sourceObjectID))
            XCTAssertEqual(retained.address, entry.address)
            XCTAssertEqual(retained.originalDescriptor, entry.originalDescriptor)
            XCTAssertEqual(retained.intent, entry.intent)
            XCTAssertEqual(retained.mapping?.currentReceiptSHA256, entry.mapping?.currentReceiptSHA256)
        }
        let standalone = try AnyNativeImportedDefinitionDirectory(plan: supplement.plan, mappings: progress.mappings)
        XCTAssertThrowsError(try AnyNativeImportedDefinitionDirectory(preservation: directory, propertySupplement: standalone))
        let oldBytes = try journalDigest(parent)
        let checkpoint = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: parent, binding: supplement.plan.binding)
        XCTAssertEqual(try Ordinary14Wire.encode(checkpoint.mappings), try Ordinary14Wire.encode(progress.mappings))
        XCTAssertEqual(checkpoint.plan.importedPropertyNamespace?.binding, supplement.namespace.binding)
        XCTAssertEqual(checkpoint.nativeOperationsPerformed, 0)
        XCTAssertFalse(checkpoint.provesCurrentNativeState)
        let afterCold = await driver.counts()
        XCTAssertEqual(afterCold, complete)
        XCTAssertEqual(try journalDigest(parent), oldBytes)
        try fixture.retained.requireRetainedInputsUnchanged()
    }

    private func execute(_ plan: AnyDestinationMigrationPlan, parent: URL, driver: Ordinary14FixtureDriver,
                         authorize: @escaping AnyDestinationAuthorization = {}) async throws -> AnyDestinationMigrationProgress {
        let source = try Ordinary14Wire.encode(plan.source)
        return try await AnyDestinationMigrationExecutor(journalDirectory: parent, driver: driver).execute(plan: plan,
            payloads: { _ in throw Ordinary14FixtureFailure.unexpectedOperation },
            verifySource: { current in
                guard try Ordinary14Wire.encode(current) == source else { throw AnyDestinationMigrationError.changedSource }
            }, authorize: authorize)
    }

    private func directory() throws -> URL {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_ORDINARY14_FIXTURE_ROOT"] else {
            throw XCTSkip("Requires a new owned Ordinary14 journal fixture parent.")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true)
        var info = stat()
        guard lstat(root.path, &info) == 0, info.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR),
              info.st_uid == geteuid(), info.st_mode & mode_t(0o7777) == mode_t(0o700) else {
            throw Ordinary14FixtureFailure.unsafeFixture
        }
        let child = root.appendingPathComponent("ordinary14-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: child, withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700])
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: child.path)
        addTeardownBlock { try FileManager.default.removeItem(at: child) }
        return child
    }

    private func journalDigest(_ root: URL) throws -> [String: String] {
        var pending = [root], result: [String: String] = [:]
        var logical = 0
        while let path = pending.popLast() {
            guard result.count < 100 else { throw Ordinary14FixtureFailure.unsafeFixture }
            var value = stat()
            guard lstat(path.path, &value) == 0 else { throw Ordinary14FixtureFailure.unsafeFixture }
            let kind = value.st_mode & mode_t(S_IFMT)
            if kind == mode_t(S_IFDIR) {
                result[path.path] = "directory"
                pending += try FileManager.default.contentsOfDirectory(at: path, includingPropertiesForKeys: nil)
            } else if kind == mode_t(S_IFREG) {
                guard value.st_nlink == 1, value.st_size >= 0, value.st_size <= 32 * 1024 * 1024,
                      logical <= 48 * 1024 * 1024 - Int(value.st_size) else {
                    throw Ordinary14FixtureFailure.unsafeFixture
                }
                let bytes = try Data(contentsOf: path); logical += bytes.count
                result[path.path] = AnyContentDigest.sha256(bytes)
            } else { throw Ordinary14FixtureFailure.unsafeFixture }
        }
        return result
    }
}

private struct Ordinary14LegacyContent: Encodable {
    let version: String
    let source: AnyDestinationSourceBinding
    struct Target: Encodable {
        let accountID: String; let spaceID: String; let storeID: String; let planID: String
    }
    let target: Target
    let coverage: [AnyDestinationCoverage]
    let items: [AnyDestinationMigrationItem]
}

private enum Ordinary14Wire {
    static func encode<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    static func json<T: Encodable>(_ value: T) throws -> AnyJSON {
        try JSONDecoder().decode(AnyJSON.self, from: encode(value))
    }
    static func replacing(_ value: AnyJSON, _ key: String, _ new: AnyJSON) throws -> AnyJSON {
        var fields = try XCTUnwrap(value.object); fields[key] = new; return .object(fields)
    }
}

private struct Ordinary14Fixture {
    let retained: NativeCanonicalSupplementFixture
    let catalog: AnyHeartNativeDefinitionCatalog
    let supplement: AnyHeartNativeOrdinaryPropertySupplement

    static func load() throws -> Self {
        let retained = try NativeCanonicalSupplementFixture.load()
        let manifest = try Data(contentsOf: retained.bundle.appendingPathComponent("manifest.json"))
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: retained.plan.source.accountID, sourceSpaceID: retained.plan.source.spaceID) { member in
            let parts = member.path.split(separator: "/", omittingEmptySubsequences: false)
            guard !member.path.hasPrefix("/"), !member.path.contains("\\"), !member.path.contains("\0"),
                  parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }),
                  member.byteCount >= 0, member.byteCount <= 32 * 1024 * 1024 else {
                throw Ordinary14FixtureFailure.unsafeFixture
            }
            var path = retained.bundle
            for (index, part) in parts.enumerated() {
                path.appendPathComponent(String(part))
                let attributes = try FileManager.default.attributesOfItem(atPath: path.path)
                guard attributes[.type] as? FileAttributeType ==
                    (index == parts.count - 1 ? .typeRegular : .typeDirectory) else {
                    throw Ordinary14FixtureFailure.unsafeFixture
                }
            }
            let attributes = try FileManager.default.attributesOfItem(atPath: path.path)
            guard (attributes[.size] as? NSNumber)?.intValue == member.byteCount else {
                throw Ordinary14FixtureFailure.unsafeFixture
            }
            return try Data(contentsOf: path)
        }
        return try .init(retained: retained, catalog: AnyHeartNativeDefinitionCatalog(bundle: bundle),
            supplement: AnyHeartNativeOrdinaryPropertySupplement(bundle: bundle,
                completedPreservationPlan: retained.plan, completedPreservationMappings: retained.mappings))
    }

    static func issueIdentity(_ value: AnyHeartNativeDefinitionPlan.Issue) -> String {
        value.sourceObjectID + "\u{0}" + value.field + "\u{0}" + value.reason
    }
    static func namespaceReceipt(_ namespace: AnyDestinationImportedPropertyNamespace) throws -> AnyJSON {
        let intent = namespace.intent
        return .object([
            "contract": .string(AnyNativePreparedDefinitionMigration.contract),
            "accountId": .string(intent.binding.workspace.accountID), "spaceId": .string(intent.binding.workspace.spaceID),
            "storeId": .string(intent.binding.storeID), "planId": .string(intent.binding.planID),
            "planSHA256": .string(intent.binding.planSHA256), "sourceKey": .string(intent.sourceKey),
            "kind": .string(intent.kind.rawValue), "intentId": .string(intent.intentID),
            "specSHA256": .string(intent.specSHA256), "fingerprint": .string(namespace.mapping.fingerprint),
            "stage": .string("complete"), "outcome": .string("committed"),
            "objectId": .string(namespace.ownerID),
            "recordIds": .array(namespace.mapping.recordIDs.map(AnyJSON.string)),
            "changeId": .string(try XCTUnwrap(namespace.mapping.signedChangeIDs.last))
        ])
    }
    static func root(_ namespace: AnyDestinationImportedPropertyNamespace) throws -> AnyJSON {
        try AnyDestinationContentProjection.root(namespace.originalNamespace, id: namespace.ownerID, type: false)
    }
}

private enum Ordinary14FixtureFailure: Error { case unsafeFixture, unexpectedOperation, lostAcknowledgement, revoked }

private actor Ordinary14Authorization {
    private var active = true
    func revoke() { active = false }
    func check() throws { if !active { throw Ordinary14FixtureFailure.revoked } }
}

private actor Ordinary14FixtureDriver: AnyDestinationNativeDriving {
    enum Mode: Equatable, Sendable {
        case normal, missingNamespace, obsoleteNamespace, foreignRoot, changedRoot, changedReceipt, lostFirstCommit
    }
    struct Counts: Equatable, Sendable {
        var namespaceStatuses = 0
        var namespaceRoots = 0
        var prepared: [String] = []
        var committed: [String] = []
        var originalWrites = 0
    }
    private let namespace: AnyDestinationImportedPropertyNamespace
    private let expected: [String: AnyPreparedDefinitionIntent]
    private let mode: Mode
    private let afterFirstPrepare: (@Sendable () async -> Void)?
    private var values: [String: AnyJSON] = [:]
    private var state = Counts()
    private var lostAcknowledgement = false

    init(supplement: AnyHeartNativeOrdinaryPropertySupplement, mode: Mode,
         afterFirstPrepare: (@Sendable () async -> Void)? = nil) throws {
        let originalNamespace = supplement.namespace
        namespace = originalNamespace; self.mode = mode; self.afterFirstPrepare = afterFirstPrepare
        var expected: [String: AnyPreparedDefinitionIntent] = [:]
        for item in supplement.plan.items {
            let operation = try item.operation.resolved(destinationSpaceID: supplement.plan.binding.workspace.spaceID) { reference in
                switch reference {
                case .native(let id): return id
                case .mapped: throw Ordinary14FixtureFailure.unexpectedOperation
                }
            }
            guard case .definition(let intent) = try AnyDestinationNativeIntent.make(operation,
                binding: supplement.plan.binding, sourceKey: item.sourceKey, sequence: nil, inlineContent: nil),
                intent.kind == .propertyDefinition, intent.expectedOwnerID == originalNamespace.ownerID,
                expected.updateValue(intent, forKey: intent.intentID) == nil else {
                throw Ordinary14FixtureFailure.unexpectedOperation
            }
        }
        self.expected = expected
    }

    func counts() -> Counts { state }

    func status(_ intent: AnyDestinationNativeIntent, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await authorize()
        guard case .definition(let definition) = intent else { throw Ordinary14FixtureFailure.unexpectedOperation }
        if definition == namespace.intent {
            state.namespaceStatuses += 1
            if mode == .missingNamespace { throw AnyEngineError.http(status: 404, code: "not_found") }
            var value = try Ordinary14Fixture.namespaceReceipt(namespace)
            if mode == .obsoleteNamespace || (mode == .changedReceipt && state.namespaceStatuses == 2) {
                value = try Ordinary14Wire.replacing(value, "outcome",
                    .string(mode == .obsoleteNamespace ? "obsolete" : "committed_modified"))
            }
            return value
        }
        guard expected[definition.intentID] == definition else { throw Ordinary14FixtureFailure.unexpectedOperation }
        guard let value = values[definition.intentID] else { throw AnyEngineError.http(status: 404, code: "not_found") }
        return value
    }

    func importedPropertyNamespace(ownerID: String,
        authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await authorize()
        guard Data(ownerID.utf8) == Data(namespace.ownerID.utf8) else { throw Ordinary14FixtureFailure.unexpectedOperation }
        state.namespaceRoots += 1
        let root = try Ordinary14Fixture.root(namespace)
        if mode == .foreignRoot { return try Ordinary14Wire.replacing(root, "id", .string(ownerID + "-foreign")) }
        if mode == .changedRoot && state.namespaceRoots == 2 {
            return try Ordinary14Wire.replacing(root, "name", .string("Changed between current observations"))
        }
        return root
    }

    func prepare(_ intent: AnyDestinationNativeIntent, payload: URL?,
        authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await authorize()
        guard case .definition(let definition) = intent else { throw Ordinary14FixtureFailure.unexpectedOperation }
        if definition == namespace.intent {
            state.originalWrites += 1; throw Ordinary14FixtureFailure.unexpectedOperation
        }
        guard payload == nil, expected[definition.intentID] == definition, values[definition.intentID] == nil else {
            throw Ordinary14FixtureFailure.unexpectedOperation
        }
        let record = "ordinary14-" + String(definition.intentID.prefix(32))
        let receipt: AnyJSON = .object([
            "contract": .string(AnyNativePreparedDefinitionMigration.contract),
            "accountId": .string(definition.binding.workspace.accountID), "spaceId": .string(definition.binding.workspace.spaceID),
            "storeId": .string(definition.binding.storeID), "planId": .string(definition.binding.planID),
            "planSHA256": .string(definition.binding.planSHA256), "sourceKey": .string(definition.sourceKey),
            "kind": .string(definition.kind.rawValue), "intentId": .string(definition.intentID),
            "specSHA256": .string(definition.specSHA256),
            "fingerprint": .string(AnyContentDigest.sha256(definition.specBytes)),
            "stage": .string("definition-property-prepared"), "outcome": .string("prepared"),
            "objectId": .string(namespace.ownerID), "recordIds": .array([.string(record)]),
            "changeId": .string("signed-" + definition.intentID)
        ])
        _ = try AnyPreparedDefinitionReceipt(receipt, intent: definition)
        values[definition.intentID] = receipt; state.prepared.append(definition.intentID)
        if state.prepared.count == 1, let afterFirstPrepare { await afterFirstPrepare() }
        return receipt
    }

    func commit(_ intent: AnyDestinationNativeIntent, receipt: AnyJSON,
        authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await authorize()
        guard case .definition(let definition) = intent else { throw Ordinary14FixtureFailure.unexpectedOperation }
        if definition == namespace.intent {
            state.originalWrites += 1; throw Ordinary14FixtureFailure.unexpectedOperation
        }
        guard expected[definition.intentID] == definition, let old = values[definition.intentID],
              try Ordinary14Wire.encode(old) == Ordinary14Wire.encode(receipt),
              old["outcome"] == .string("prepared") else {
            throw Ordinary14FixtureFailure.unexpectedOperation
        }
        let complete = try Ordinary14Wire.replacing(
            Ordinary14Wire.replacing(old, "stage", .string("complete")), "outcome", .string("committed"))
        _ = try AnyPreparedDefinitionReceipt(complete, intent: definition)
        values[definition.intentID] = complete; state.committed.append(definition.intentID)
        if mode == .lostFirstCommit && !lostAcknowledgement {
            lostAcknowledgement = true
            throw Ordinary14FixtureFailure.lostAcknowledgement
        }
        return complete
    }

    func applySequence(objectID: String, authorize: @escaping AnyDestinationAuthorization) async throws -> Int64 {
        throw Ordinary14FixtureFailure.unexpectedOperation
    }
}
