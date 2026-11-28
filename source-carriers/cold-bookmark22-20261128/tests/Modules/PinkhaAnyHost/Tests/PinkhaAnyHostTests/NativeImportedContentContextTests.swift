import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// New correspondence and pre-admission controls only. The original retained
/// plan/mappings and capture are read from the qualified isolated fixture copy;
/// no native account, migration execution or current native authority is tested.
final class NativeImportedContentContextTests: XCTestCase, @unchecked Sendable {
    func testOriginalCompletedPlanRoutesBothEditablePagesWithoutCatalogCarrierFallback() throws {
        let fixture = try ImportedContentFixture.load()
        let entries = try fixture.entries()
        XCTAssertEqual(fixture.retained.plan.items.count, 182)
        XCTAssertEqual(entries.count, 2)
        XCTAssertEqual(Set(entries.map { Data($0.objectID.utf8) }).count, 2)
        XCTAssertEqual(Set(entries.map { Data($0.sourceObjectID.utf8) }),
            Set(fixture.composition.selection.objects.map { Data($0.sourceObjectID.utf8) }))
        XCTAssertEqual(Set(fixture.carriers.map { Data($0.utf8) }).count, 1)
        let anchor = try XCTUnwrap(fixture.composition.selection.objects.first)
        let sameSourceOperations = fixture.retained.plan.items.filter {
            Data($0.sourceObjectID.utf8) == Data(anchor.sourceObjectID.utf8) && $0.operation.kind == "object"
        }
        XCTAssertEqual(sameSourceOperations.count, 2)
        let document = try XCTUnwrap(entries.first {
            Data($0.sourceObjectID.utf8) == Data(anchor.sourceObjectID.utf8)
        })
        let expectedSourceKey = AnyHeartNativePageComposition.objectSourceKey(
            spaceID: fixture.retained.plan.source.spaceID, objectID: anchor.sourceObjectID)
        XCTAssertEqual(Data(document.sourceKey.utf8), Data(expectedSourceKey.utf8))
        for entry in entries {
            XCTAssertFalse(fixture.carriers.contains { Data($0.utf8) == Data(entry.objectID.utf8) })
            XCTAssertFalse(entry.grantsNativeAuthority)
            XCTAssertEqual(entry.intent.binding.planID, fixture.retained.plan.binding.planID)
            XCTAssertEqual(entry.intent.binding.planSHA256, fixture.retained.plan.binding.planSHA256)
            XCTAssertEqual(entry.creationIntentID, entry.mapping.intentID)
            let facts = try XCTUnwrap(fixture.sourceFacts.entry(sourceObjectID: entry.sourceObjectID))
            XCTAssertEqual(Data(facts.objectID.utf8), Data(entry.objectID.utf8))
            XCTAssertEqual(Data(facts.ownerTypeID.utf8), Data(entry.nativeTypeID.utf8))
            XCTAssertEqual(facts.sourceSnapshotSHA256, entry.sourceSnapshotSHA256)
            XCTAssertEqual(facts.sourceJSONViewSHA256, entry.sourceJSONViewSHA256)
        }
        try fixture.requireOriginals()
    }

    func testDocumentProjectionRejectsCarrierSubstitutionAndChangedOperationIdentity() throws {
        let fixture = try ImportedContentFixture.load()
        let entry = try XCTUnwrap(try fixture.entries().first)
        let index = try XCTUnwrap(fixture.retained.mappings.firstIndex {
            Data($0.sourceKey.utf8) == Data(entry.sourceKey.utf8)
        })
        let old = fixture.retained.mappings[index]
        let carrier = try XCTUnwrap(fixture.carriers.first)
        var substituted = fixture.retained.mappings
        substituted[index] = .init(sourceKey: old.sourceKey, sourceObjectID: old.sourceObjectID,
            kind: old.kind, intentID: old.intentID, objectID: carrier, recordIDs: [carrier],
            fileID: nil, fingerprint: old.fingerprint, signedChangeIDs: old.signedChangeIDs,
            currentReceiptSHA256: old.currentReceiptSHA256)
        XCTAssertThrowsError(try fixture.entries(mappings: substituted))

        // A syntactically well-formed mapping is insufficient when its original
        // object-operation key or intent identity has changed.
        for change in ["sourceKey", "sourceObjectID", "intentID"] {
            var changed = fixture.retained.mappings
            changed[index] = .init(
                sourceKey: change == "sourceKey" ? old.sourceKey + "-foreign" : old.sourceKey,
                sourceObjectID: change == "sourceObjectID" ? old.sourceObjectID + "-foreign" : old.sourceObjectID,
                kind: old.kind,
                intentID: change == "intentID" ? String(repeating: "f", count: 64) : old.intentID,
                objectID: old.objectID, recordIDs: old.recordIDs, fileID: old.fileID,
                fingerprint: old.fingerprint, signedChangeIDs: old.signedChangeIDs,
                currentReceiptSHA256: old.currentReceiptSHA256)
            XCTAssertThrowsError(try fixture.entries(mappings: changed), change)
        }
        // The exact current-content projection is required even when all
        // preserved catalog rows and mapping counts are still present.
        let plan = fixture.retained.plan
        var items = plan.items
        let item = items[index]
        guard case .object(let type, let collections, .literal(let initial)) = item.operation else {
            return XCTFail("the selected item must be the original object operation")
        }
        var fields = try XCTUnwrap(initial.object)
        var any = fields["any"]?.object ?? [:]
        any["name"] = .string("changed-plan-fixture")
        fields["any"] = .object(any)
        items[index] = .init(sourceKey: item.sourceKey, sourceObjectID: item.sourceObjectID,
            expectedRecordCount: item.expectedRecordCount,
            operation: .object(type: type, collections: collections, initialProperties: .literal(.object(fields))))
        let changedPlan = try AnyDestinationMigrationPlan(source: plan.source,
            workspace: plan.binding.workspace, storeID: plan.binding.storeID, planID: plan.binding.planID,
            coverage: plan.coverage, items: items)
        XCTAssertNotEqual(changedPlan.canonicalBytes, plan.canonicalBytes)
        XCTAssertThrowsError(try fixture.entries(plan: changedPlan))
        try fixture.requireOriginals()
    }

    func testEditedDocumentCreationReceiptRetainsIdentityAndRefusesDeletedOrForeignState() throws {
        let fixture = try ImportedContentFixture.load()
        let entry = try XCTUnwrap(try fixture.entries().first)
        let committed = try AnyPreparedMigrationReceipt(receipt(entry, outcome: "committed"), intent: entry.intent)
        let modified = try AnyPreparedMigrationReceipt(receipt(entry, outcome: "committed_modified"), intent: entry.intent)
        try entry.requireCurrentReceipt(committed)
        try entry.requireCurrentReceipt(modified)
        XCTAssertFalse(modified.isCompleteAndCurrent)
        XCTAssertEqual(committed.intent.specBytes, modified.intent.specBytes)
        let current = nativeObject(entry, typeID: entry.nativeTypeID, name: "edited ordinary name")
        try entry.requireCurrentObject(current)
        let editedAgain = nativeObject(entry, typeID: entry.nativeTypeID, name: "another ordinary edit")
        try entry.requireCurrentObject(editedAgain)
        XCTAssertNotEqual(try wire(current), try wire(editedAgain))
        XCTAssertThrowsError(try entry.requireCurrentObject(
            nativeObject(entry, typeID: "foreign-type", name: "edited ordinary name")))
        var wrongSpace = try XCTUnwrap(current["record"]?.object)
        wrongSpace["spaceId"] = .string(entry.intent.binding.workspace.spaceID + "-foreign")
        XCTAssertThrowsError(try entry.requireCurrentObject(.object([
            "objectId": .string(entry.objectID), "record": .object(wrongSpace)
        ])))
        var noSequence = try XCTUnwrap(current["record"]?.object)
        noSequence["_applySeq"] = .integer(0)
        XCTAssertThrowsError(try entry.requireCurrentObject(.object([
            "objectId": .string(entry.objectID), "record": .object(noSequence)
        ])))
        for outcome in ["committed_deleted", "obsolete"] {
            let value = try AnyPreparedMigrationReceipt(receipt(entry, outcome: outcome), intent: entry.intent)
            XCTAssertThrowsError(try entry.requireCurrentReceipt(value), outcome)
        }
        let alternatives: [(String, AnyJSON)] = [
            ("fingerprint", .string(String(repeating: "f", count: 64))),
            ("changeId", .string("foreign-signed-change"))
        ]
        for (field, value) in alternatives {
            var fields = try XCTUnwrap(try receipt(entry, outcome: "committed_modified").object)
            fields[field] = value
            let parsed = try AnyPreparedMigrationReceipt(.object(fields), intent: entry.intent)
            XCTAssertThrowsError(try entry.requireCurrentReceipt(parsed), field)
        }
        var foreign = try XCTUnwrap(try receipt(entry, outcome: "committed_modified").object)
        foreign["objectId"] = .string("foreign-object")
        foreign["recordIds"] = .array([.string("foreign-object")])
        let parsed = try AnyPreparedMigrationReceipt(.object(foreign), intent: entry.intent)
        XCTAssertThrowsError(try entry.requireCurrentReceipt(parsed))
        var incomplete = try XCTUnwrap(try receipt(entry, outcome: "committed").object)
        incomplete["stage"] = .string("root-committed")
        incomplete["outcome"] = .string("prepared")
        incomplete["recordIds"] = .array([])
        let unfinished = try AnyPreparedMigrationReceipt(.object(incomplete), intent: entry.intent)
        XCTAssertThrowsError(try entry.requireCurrentReceipt(unfinished))
        try fixture.requireOriginals()
    }

    func testClosedContentLocatorBindsTheSameWholeCheckpointAndExactPreservationBytes() throws {
        let preservation = try AnyNativeImportedContextReference.decode(wire(.object(preservationFields())))
        let fields = try contentFields(preservation)
        let bytes = try wire(.object(fields))
        let locator = try AnyNativeImportedContentContextReference.decode(bytes)
        let binding = try locator.binding(preservation: preservation)
        XCTAssertFalse(locator.grantsNativeAuthority)
        XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(binding, preservation.binding))
        let encoded = try locator.encoded()
        let roundTrip = try AnyNativeImportedContentContextReference.decode(encoded).encoded()
        XCTAssertEqual(encoded, roundTrip)

        var extra = fields; extra["contentJournal"] = .string("a-second-journal")
        XCTAssertThrowsError(try AnyNativeImportedContentContextReference.decode(wire(.object(extra))))
        var missing = fields; missing.removeValue(forKey: "checkpointScope")
        XCTAssertThrowsError(try AnyNativeImportedContentContextReference.decode(wire(.object(missing))))
        var duplicate = Data("{\"contentSHA256\":\"".utf8)
        duplicate.append(Data(String(repeating: "c", count: 64).utf8))
        duplicate.append(Data("\",".utf8)); duplicate.append(bytes.dropFirst())
        XCTAssertThrowsError(try AnyNativeImportedContentContextReference.decode(duplicate))
        var separate = fields; separate["checkpointScope"] = .string("separate-content-plan")
        XCTAssertThrowsError(try AnyNativeImportedContentContextReference.decode(wire(.object(separate))))
        for key in ["contentPlanID", "contentPlanSHA256", "contentCheckpointSHA256", "preservationReferenceSHA256"] {
            var changed = fields; changed[key] = .string(String(repeating: "f", count: 64))
            let value = try AnyNativeImportedContentContextReference.decode(wire(.object(changed)))
            XCTAssertThrowsError(try value.binding(preservation: preservation), key)
        }

        var composedFields = preservationFields()
        composedFields["destinationAccountID"] = .string("caf\u{e9}")
        let composed = try AnyNativeImportedContextReference.decode(wire(.object(composedFields)))
        let composedLocator = try AnyNativeImportedContentContextReference.decode(wire(.object(contentFields(composed))))
        composedFields["destinationAccountID"] = .string("cafe\u{301}")
        let decomposed = try AnyNativeImportedContextReference.decode(wire(.object(composedFields)))
        XCTAssertThrowsError(try composedLocator.binding(preservation: decomposed))
        XCTAssertThrowsError(try AnyNativeImportedContentContextReference.decode(Data(repeating: 0x20, count: 4097))) {
            XCTAssertEqual($0 as? AnyEngineError, .readLimit)
        }
        // A locator's content digest is re-derived from the complete admitted
        // archive by owner.openContent; syntax alone is never an authority test.
    }

    func testOwnerRefusesForeignRetiredAndChangedRunBeforeOpeningPrivateInputs() async throws {
        let parent = try privateDirectory()
        let journal = parent.appendingPathComponent("never-created-journal", isDirectory: true)
        let archive = parent.appendingPathComponent("never-created-archive")
        let preservation = try AnyNativeImportedContextReference.decode(wire(.object(preservationFields())))
        let content = try AnyNativeImportedContentContextReference.decode(wire(.object(contentFields(preservation))))
        let endpoint = try XCTUnwrap(URL(string: "http://127.0.0.1:1"))
        let client = try AnyHTTPClient(baseURL: endpoint, expectedAccountID: preservation.destinationAccountID)
        let counter = ImportedContentRunCounter()
        let foreignWorkspace = try AnyTorahWorkspace(accountID: preservation.destinationAccountID,
            spaceID: preservation.destinationSpaceID + "-foreign")
        let foreign = AnyApplicationSession(workspace: foreignWorkspace, engineStartedAt: "captured-run",
            verifyRun: { await counter.changedRun() })
        do {
            _ = try await AnyNativeImportedContextOwner.openContent(client: client, session: foreign,
                preservationReference: preservation, preservationJournalDirectory: journal,
                contentReference: content, archiveSource: .retainedFile(archive))
            XCTFail("foreign workspace admitted")
        } catch {
            XCTAssertEqual(error as? AnyHostError, .wrongWorkspace)
        }
        await foreign.revokeAndDrain()
        let retired = AnyApplicationSession(workspace: preservation.binding.workspace,
            engineStartedAt: "captured-run", verifyRun: { await counter.changedRun() })
        await retired.revokeAndDrain()
        do {
            _ = try await AnyNativeImportedContextOwner.openContent(client: client, session: retired,
                preservationReference: preservation, preservationJournalDirectory: journal,
                contentReference: content, archiveSource: .retainedFile(archive))
            XCTFail("retired parent admitted")
        } catch {
            XCTAssertEqual(error as? AnyHostError, .sessionClosed)
        }
        let beforeRunChange = await counter.count()
        XCTAssertEqual(beforeRunChange, 0)
        let changed = AnyApplicationSession(workspace: preservation.binding.workspace,
            engineStartedAt: "captured-run", verifyRun: { await counter.changedRun() })
        do {
            _ = try await AnyNativeImportedContextOwner.openContent(client: client, session: changed,
                preservationReference: preservation, preservationJournalDirectory: journal,
                contentReference: content, archiveSource: .retainedFile(archive))
            XCTFail("changed native run admitted")
        } catch {
            XCTAssertEqual(error as? AnyHostError, .engineRestarted)
        }
        let active = await changed.isActive, calls = await counter.count()
        XCTAssertFalse(active)
        XCTAssertEqual(calls, 1)
        await changed.revokeAndDrain()
        XCTAssertFalse(FileManager.default.fileExists(atPath: journal.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: archive.path))
        XCTAssertTrue(try FileManager.default.contentsOfDirectory(atPath: parent.path).isEmpty)
    }

    private func nativeObject(_ entry: AnyNativeImportedDocumentEntry, typeID: String, name: String) -> AnyJSON {
        .object(["objectId": .string(entry.objectID), "record": .object([
            "id": .string(entry.objectID), "spaceId": .string(entry.intent.binding.workspace.spaceID),
            "_applySeq": .integer(41),
            "any": .object(["type": .string(typeID), "name": .string(name)])
        ])])
    }

    private func receipt(_ entry: AnyNativeImportedDocumentEntry, outcome: String) throws -> AnyJSON {
        let intent = entry.intent, binding = intent.binding
        return .object([
            "contract": .string(AnyNativePreparedMigration.contract),
            "intentId": .string(intent.intentID), "storeId": .string(binding.storeID),
            "accountId": .string(binding.workspace.accountID), "spaceId": .string(binding.workspace.spaceID),
            "planId": .string(binding.planID), "planSHA256": .string(binding.planSHA256),
            "sourceKey": .string(intent.sourceKey), "kind": .string(intent.kind.rawValue),
            "specSHA256": .string(intent.specSHA256), "fingerprint": .string(entry.mapping.fingerprint),
            "stage": .string("complete"), "outcome": .string(outcome),
            "objectId": .string(entry.objectID),
            "recordIds": .array([.string(entry.objectID)]),
            "changeId": .string(try XCTUnwrap(entry.mapping.signedChangeIDs.last))
        ])
    }

    private func preservationFields() -> [String: AnyJSON] {
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

    private func contentFields(_ preservation: AnyNativeImportedContextReference) throws -> [String: AnyJSON] {
        [
            "contract": .string(AnyNativeImportedContentContextReference.version),
            "checkpointScope": .string("completed-preservation-current-content"),
            "preservationReferenceSHA256": .string(AnyContentDigest.sha256(try preservation.encoded())),
            "contentPlanID": .string(preservation.planID), "contentPlanSHA256": .string(preservation.planSHA256),
            "contentCheckpointSHA256": .string(preservation.checkpointSHA256),
            "contentSHA256": .string(String(repeating: "3", count: 64))
        ]
    }

    private func privateDirectory() throws -> URL {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_IMPORTED_CONTEXT_FIXTURE_ROOT"] else {
            throw XCTSkip("Requires the isolated component owner's private fixture directory.")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true).standardizedFileURL
        let attributes = try FileManager.default.attributesOfItem(atPath: root.path)
        guard root.path == path, root.resolvingSymlinksInPath().path == root.path,
              attributes[.type] as? FileAttributeType == .typeDirectory,
              (attributes[.posixPermissions] as? NSNumber)?.intValue == 0o700 else {
            throw ImportedContentFixtureError.invalidFixture
        }
        let directory = root.appendingPathComponent("content-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700])
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: directory.path)
        addTeardownBlock { try FileManager.default.removeItem(at: directory) }
        return directory
    }

    private func wire(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(value)
    }
}

private struct ImportedContentFixture {
    let retained: NativeCanonicalSupplementFixture
    let composition: AnyHeartNativeContentComposition
    let definitions: AnyNativeImportedDefinitionDirectory
    let sourceFacts: AnyNativeImportedSourceFactsDirectory
    let carriers: [String]

    static func load() throws -> Self {
        let retained = try NativeCanonicalSupplementFixture.load()
        let manifest = try Data(contentsOf: retained.bundle.appendingPathComponent("manifest.json"))
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: retained.plan.source.accountID, sourceSpaceID: retained.plan.source.spaceID) { member in
            let parts = member.path.split(separator: "/", omittingEmptySubsequences: false)
            guard !member.path.hasPrefix("/"), !member.path.contains("\\"),
                  !member.path.contains("\0"), parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
                throw ImportedContentFixtureError.invalidFixture
            }
            var path = retained.bundle
            for (index, part) in parts.enumerated() {
                path.appendPathComponent(String(part))
                let attributes = try FileManager.default.attributesOfItem(atPath: path.path)
                guard attributes[.type] as? FileAttributeType ==
                    (index == parts.count - 1 ? .typeRegular : .typeDirectory) else {
                    throw ImportedContentFixtureError.invalidFixture
                }
            }
            let attributes = try FileManager.default.attributesOfItem(atPath: path.path)
            guard (attributes[.size] as? NSNumber)?.intValue == member.byteCount,
                  member.byteCount >= 0, member.byteCount <= 32 * 1024 * 1024 else {
                throw ImportedContentFixtureError.invalidFixture
            }
            return try Data(contentsOf: path)
        }
        let composition = try AnyHeartNativeContentComposition(bundle: bundle)
        let definitions = try AnyNativeImportedDefinitionDirectory(plan: retained.plan, mappings: retained.mappings)
        let facts = try AnyNativeImportedSourceFactsDirectory(plan: retained.plan, mappings: retained.mappings)
        let catalog = try AnyNativeImportedCatalogDirectory(plan: retained.plan, mappings: retained.mappings)
        return .init(retained: retained, composition: composition, definitions: definitions,
            sourceFacts: facts, carriers: catalog.entries.map(\.objectID))
    }

    func entries(plan: AnyDestinationMigrationPlan? = nil,
                 mappings: [AnyDestinationMigrationMapping]? = nil) throws -> [AnyNativeImportedDocumentEntry] {
        try AnyNativeImportedContentContext.documentEntries(plan: plan ?? retained.plan,
            mappings: mappings ?? retained.mappings, composition: composition, definitions: definitions,
            sourceFacts: sourceFacts, catalogCarrierObjectIDs: carriers)
    }

    func requireOriginals() throws { try retained.requireRetainedInputsUnchanged() }
}

private actor ImportedContentRunCounter {
    private var calls = 0
    func changedRun() -> String { calls += 1; return "replacement-run" }
    func count() -> Int { calls }
}
private enum ImportedContentFixtureError: Error { case invalidFixture }
