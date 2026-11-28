import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// New source-correspondence, synthetic observation-order and pre-admission
/// controls. The retained182 plan/mappings/capture are immutable input. Only
/// the fourteen supplemental receipt rows are synthetic; no executor, native
/// account, original migration replay or current native authority is exercised.
final class NativeImportedOrdinaryPropertyContextTests: XCTestCase, @unchecked Sendable {
    func testClosedSupplementLocatorBindsTheOriginalCheckpointAndExactUTF8() throws {
        let fixture = try ColdOrdinaryFixture.load()
        let reference = fixture.reference
        let encoded = try reference.encoded()
        let decoded = try AnyNativeImportedOrdinaryPropertyReference.decode(encoded)
        XCTAssertEqual(try decoded.encoded(), encoded)
        XCTAssertFalse(decoded.grantsNativeAuthority)
        XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(
            try decoded.binding(preservation: fixture.preservation), fixture.supplement.plan.binding))
        let fields = try XCTUnwrap(try ColdOrdinaryWire.json(reference).object)
        XCTAssertEqual(Set(fields.keys), Set([
            "contract", "checkpointScope", "preservationReferenceSHA256",
            "supplementPlanID", "supplementPlanSHA256", "supplementCheckpointSHA256",
            "namespaceOwnerID", "namespaceIntentID", "namespaceSHA256", "mappingsSHA256"
        ]))
        XCTAssertEqual(reference.supplementCheckpointSHA256, fixture.checkpoint.checkpointSHA256)
        XCTAssertEqual(reference.namespaceOwnerID, fixture.supplement.namespace.ownerID)
        XCTAssertNotEqual(reference.supplementPlanID, fixture.retained.plan.binding.planID)
        XCTAssertEqual(reference.preservationReferenceSHA256,
            AnyContentDigest.sha256(try fixture.preservation.encoded()))
        for kind in ["extra", "missing", "wrong-scope", "unicode-owner"] {
            var changed = fields
            switch kind {
            case "extra": changed["journalPath"] = .string("caller-selected-authority")
            case "missing": changed.removeValue(forKey: "mappingsSHA256")
            case "wrong-scope": changed["checkpointScope"] = .string("completed-preservation-current-content")
            default: changed["namespaceOwnerID"] = .string("namespace-\u{e9}")
            }
            XCTAssertThrowsError(try AnyNativeImportedOrdinaryPropertyReference.decode(
                ColdOrdinaryWire.encode(AnyJSON.object(changed))), kind) {
                XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .invalidReference)
            }
        }
        var duplicate = Data("{\"mappingsSHA256\":\"".utf8)
        duplicate.append(Data(reference.mappingsSHA256.utf8))
        duplicate.append(Data("\",".utf8)); duplicate.append(encoded.dropFirst())
        XCTAssertThrowsError(try AnyNativeImportedOrdinaryPropertyReference.decode(duplicate))
        XCTAssertThrowsError(try AnyNativeImportedOrdinaryPropertyReference.decode(
            Data(repeating: 0x20, count: 4097))) {
            XCTAssertEqual($0 as? AnyEngineError, .readLimit)
        }
        for key in ["destinationAccountID", "destinationSpaceID", "storeID", "destinationNetworkID"] {
            let changed = try fixture.changedPreservation(key, .string("foreign-" + key))
            XCTAssertThrowsError(try reference.binding(preservation: changed), key) {
                XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .invalidReference)
            }
        }
        // Account IDs are opaque UTF8; native definition IDs remain valid ASCII.
        // These decoded locators are not native or archive admission.
        let composed = try fixture.changedPreservation("destinationAccountID", .string("caf\u{e9}"))
        let decomposed = try fixture.changedPreservation("destinationAccountID", .string("cafe\u{301}"))
        var composedFields = fields
        composedFields["preservationReferenceSHA256"] =
            .string(AnyContentDigest.sha256(try composed.encoded()))
        let composedReference = try AnyNativeImportedOrdinaryPropertyReference.decode(
            ColdOrdinaryWire.encode(AnyJSON.object(composedFields)))
        _ = try composedReference.binding(preservation: composed)
        XCTAssertThrowsError(try composedReference.binding(preservation: decomposed)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .invalidReference)
        }
        try fixture.requireOriginals()
    }

    func testCompletedFourteenCheckpointRejectsPlanMappingAndIntentSubstitution() throws {
        let fixture = try ColdOrdinaryFixture.load()
        let checkpoint = fixture.checkpoint
        try fixture.context.requireCheckpoint(checkpoint)
        XCTAssertEqual(checkpoint.plan.items.count, 14)
        XCTAssertEqual(checkpoint.intents.count, 14)
        XCTAssertEqual(checkpoint.mappings.count, 14)
        XCTAssertFalse(fixture.context.provesCurrentNativeState)
        XCTAssertFalse(fixture.context.permitsMigrationReplay)
        XCTAssertFalse(fixture.context.permitsSourceAdmission)

        var wrongIntents = checkpoint.intents
        wrongIntents[0] = .definition(fixture.supplement.namespace.intent)
        let wrongKind = try fixture.checkpointWith(intents: wrongIntents)
        XCTAssertThrowsError(try fixture.makeReference(wrongKind)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .changedCheckpoint)
        }
        XCTAssertThrowsError(try fixture.context.requireCheckpoint(wrongKind)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .changedCheckpoint)
        }
        var reordered = checkpoint.mappings
        reordered.swapAt(0, 1)
        let wrongOrder = try fixture.checkpointWith(mappings: reordered)
        XCTAssertThrowsError(try fixture.makeReference(wrongOrder)) {
            XCTAssertEqual($0 as? AnyNativeImportedDefinitionError, .invalidMappings)
        }
        var wrongMappings = checkpoint.mappings
        let old = wrongMappings[0]
        wrongMappings[0] = .init(sourceKey: old.sourceKey, sourceObjectID: old.sourceObjectID,
            kind: old.kind, intentID: old.intentID, objectID: "foreign-valid-owner",
            recordIDs: old.recordIDs, fileID: old.fileID, fingerprint: old.fingerprint,
            signedChangeIDs: old.signedChangeIDs, currentReceiptSHA256: old.currentReceiptSHA256)
        let foreignOwner = try fixture.checkpointWith(mappings: wrongMappings)
        XCTAssertThrowsError(try fixture.makeReference(foreignOwner)) {
            XCTAssertEqual($0 as? AnyNativeImportedDefinitionError, .invalidMappings)
        }
        let plan = fixture.supplement.plan
        let foreignPlan = try AnyDestinationMigrationPlan(source: plan.source,
            workspace: plan.binding.workspace, storeID: plan.binding.storeID,
            planID: AnyContentDigest.sha256(Data("another-supplement-plan".utf8)),
            coverage: plan.coverage, items: plan.items,
            importedPropertyNamespace: plan.importedPropertyNamespace)
        let wrongPlan = try fixture.checkpointWith(plan: foreignPlan)
        XCTAssertThrowsError(try fixture.makeReference(wrongPlan)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .changedCheckpoint)
        }
        var fields = try XCTUnwrap(try ColdOrdinaryWire.json(fixture.reference).object)
        fields["namespaceIntentID"] = .string(AnyContentDigest.sha256(Data("foreign-intent".utf8)))
        let foreignReference = try AnyNativeImportedOrdinaryPropertyReference.decode(
            ColdOrdinaryWire.encode(AnyJSON.object(fields)))
        XCTAssertThrowsError(try fixture.makeContext(reference: foreignReference)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .changedCheckpoint)
        }
        XCTAssertEqual(try ColdOrdinaryWire.encode(fixture.retained.plan),
            try ColdOrdinaryWire.encode(AnyDestinationMigrationPlan.decode(
                Data(contentsOf: fixture.retained.planURL))))
        try fixture.requireOriginals()
    }

    func testMergedDirectoryPreservesOriginalDocumentsAndSeparatePropertyIntentBindings() throws {
        let fixture = try ColdOrdinaryFixture.load()
        let original = try fixture.originalDirectory()
        let merged = try fixture.context.merging(into: original)
        XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(merged.binding, original.binding))
        XCTAssertEqual(try ColdOrdinaryWire.encode(merged.source),
            try ColdOrdinaryWire.encode(original.source))
        XCTAssertEqual(merged.supplementalCanonicalDefinitions, original.supplementalCanonicalDefinitions)
        XCTAssertEqual(merged.entries.count, original.entries.count + 14)
        XCTAssertEqual(merged.supplementalPropertyBindings.count, 1)
        XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(
            try XCTUnwrap(merged.supplementalPropertyBindings.first), fixture.supplement.plan.binding))
        XCTAssertFalse(merged.permitsSourceAdmission)
        for entry in original.entries {
            let current = try XCTUnwrap(merged.definition(sourceObjectID: entry.sourceObjectID))
            XCTAssertEqual(current.address, entry.address)
            XCTAssertEqual(current.originalDescriptor, entry.originalDescriptor)
            XCTAssertEqual(current.sourceSnapshotSHA256, entry.sourceSnapshotSHA256)
            XCTAssertEqual(current.sourceJSONViewSHA256, entry.sourceJSONViewSHA256)
        }
        for (index, sourceID) in fixture.context.sourceObjectIDs.enumerated() {
            XCTAssertNil(original.definition(sourceObjectID: sourceID))
            let entry = try XCTUnwrap(merged.definition(sourceObjectID: sourceID))
            let mapping = fixture.checkpoint.mappings[index]
            XCTAssertEqual(entry.address, .property(ownerKind: .collection,
                key: try .init(ownerID: fixture.supplement.namespace.ownerID,
                    propertyID: try XCTUnwrap(mapping.recordIDs.first))))
            let intent = try XCTUnwrap(entry.intent)
            XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(intent.binding,
                fixture.supplement.plan.binding))
            XCTAssertNotEqual(intent.binding.planID, original.binding.planID)
            XCTAssertEqual(intent.intentID, mapping.intentID)
            XCTAssertFalse(entry.permitsDestinationWrites)
        }
        XCTAssertEqual(Set(original.unresolvedSourceDefinitionIDs.map { Data($0.utf8) })
            .subtracting(Set(merged.unresolvedSourceDefinitionIDs.map { Data($0.utf8) })),
            Set(fixture.context.sourceObjectIDs.map { Data($0.utf8) }))
        let beforeDocuments = try fixture.documents(definitions: original)
        let afterDocuments = try fixture.documents(definitions: merged)
        XCTAssertEqual(beforeDocuments.count, 2)
        XCTAssertEqual(afterDocuments.count, beforeDocuments.count)
        for (before, after) in zip(beforeDocuments, afterDocuments) {
            XCTAssertEqual(Data(before.objectID.utf8), Data(after.objectID.utf8))
            XCTAssertEqual(Data(before.sourceObjectID.utf8), Data(after.sourceObjectID.utf8))
            XCTAssertEqual(Data(before.sourceKey.utf8), Data(after.sourceKey.utf8))
            XCTAssertEqual(before.intent.intentID, after.intent.intentID)
            XCTAssertEqual(before.nativeTypeID, after.nativeTypeID)
        }
        XCTAssertThrowsError(try fixture.context.merging(into: merged)) {
            XCTAssertEqual($0 as? AnyNativeImportedDefinitionError, .invalidMappings)
        }
        XCTAssertEqual(fixture.retained.plan.items.count, 182)
        let retainedMappings = try JSONDecoder().decode([AnyDestinationMigrationMapping].self,
            from: Data(contentsOf: fixture.retained.mappingsURL))
        XCTAssertEqual(try ColdOrdinaryWire.encode(fixture.retained.mappings),
            try ColdOrdinaryWire.encode(retainedMappings))
        try fixture.requireOriginals()
    }

    func testObservationBracketsAllFourteenReadsWithTheOriginalNamespaceAndNeverWrites() async throws {
        let fixture = try ColdOrdinaryFixture.load()
        let log = ColdOrdinaryObservationLog()
        let driver = ColdOrdinaryReadOnlyDriver(namespace: fixture.supplement.namespace, mode: .normal, log: log)
        try await fixture.context.observe(using: driver, authorize: { try await log.authorize() }) { sourceID in
            await log.read(sourceID)
        }
        let events = await log.events()
        XCTAssertEqual(events, ["status", "root", "root", "status"] +
            fixture.context.sourceObjectIDs.map { "read:" + $0 } +
            ["status", "root", "root", "status"])
        let state = await driver.counts()
        XCTAssertEqual(state.statuses, 4)
        XCTAssertEqual(state.roots, 4)
        XCTAssertEqual(state.writes, 0)
        let readCount = await log.readCount()
        XCTAssertEqual(readCount, 14)
        try fixture.requireOriginals()
    }

    func testObservationWithholdsOnNamespaceDriftDefinitionFailureAndRevocation() async throws {
        let fixture = try ColdOrdinaryFixture.load()
        let firstLog = ColdOrdinaryObservationLog()
        let missing = ColdOrdinaryReadOnlyDriver(namespace: fixture.supplement.namespace,
            mode: .missing, log: firstLog)
        do {
            try await fixture.context.observe(using: missing, authorize: { try await firstLog.authorize() }) {
                await firstLog.read($0)
            }
            XCTFail("missing namespace admitted")
        } catch {
            XCTAssertEqual(error as? AnyEngineError, .http(status: 404, code: "not_found"))
        }
        let missingReads = await firstLog.readCount(), missingCounts = await missing.counts()
        XCTAssertEqual(missingReads, 0)
        XCTAssertEqual(missingCounts.writes, 0)

        let lateLog = ColdOrdinaryObservationLog()
        let late = ColdOrdinaryReadOnlyDriver(namespace: fixture.supplement.namespace,
            mode: .changedFinalRoot, log: lateLog)
        do {
            try await fixture.context.observe(using: late, authorize: { try await lateLog.authorize() }) {
                await lateLog.read($0)
            }
            XCTFail("late namespace replacement delivered")
        } catch {
            XCTAssertEqual(error as? AnyDestinationMigrationError,
                .changedIdentity(fixture.supplement.namespace.mapping.sourceKey))
        }
        let lateReads = await lateLog.readCount(), lateCounts = await late.counts()
        XCTAssertEqual(lateReads, 14)
        XCTAssertEqual(lateCounts.statuses, 3)
        XCTAssertEqual(lateCounts.roots, 3)
        XCTAssertEqual(lateCounts.writes, 0)

        let failedID = fixture.context.sourceObjectIDs[3]
        let failedLog = ColdOrdinaryObservationLog()
        let failed = ColdOrdinaryReadOnlyDriver(namespace: fixture.supplement.namespace,
            mode: .normal, log: failedLog)
        do {
            try await fixture.context.observe(using: failed, authorize: { try await failedLog.authorize() }) {
                await failedLog.read($0)
                if Data($0.utf8) == Data(failedID.utf8) {
                    throw AnyNativeImportedOrdinaryPropertyContextError.changedDefinition($0)
                }
            }
            XCTFail("changed definition delivered")
        } catch {
            XCTAssertEqual(error as? AnyNativeImportedOrdinaryPropertyContextError, .changedDefinition(failedID))
        }
        let failedReads = await failedLog.readCount(), failedCounts = await failed.counts()
        XCTAssertEqual(failedReads, 4)
        XCTAssertEqual(failedCounts.statuses, 2)
        XCTAssertEqual(failedCounts.roots, 2)
        XCTAssertEqual(failedCounts.writes, 0)

        let revokedLog = ColdOrdinaryObservationLog()
        let revoked = ColdOrdinaryReadOnlyDriver(namespace: fixture.supplement.namespace,
            mode: .normal, log: revokedLog)
        do {
            try await fixture.context.observe(using: revoked, authorize: { try await revokedLog.authorize() }) {
                await revokedLog.read($0); await revokedLog.revoke()
            }
            XCTFail("revoked observation delivered")
        } catch {
            XCTAssertEqual(error as? ColdOrdinaryFixtureError, .revoked)
        }
        let revokedReads = await revokedLog.readCount(), revokedCounts = await revoked.counts()
        XCTAssertEqual(revokedReads, 1)
        XCTAssertEqual(revokedCounts.statuses, 2)
        XCTAssertEqual(revokedCounts.roots, 2)
        XCTAssertEqual(revokedCounts.writes, 0)
        try fixture.requireOriginals()
    }

    func testCancellationDuringDefinitionObservationStopsBeforeTheNextRead() async throws {
        let fixture = try ColdOrdinaryFixture.load()
        let context = fixture.context, log = ColdOrdinaryObservationLog()
        let driver = ColdOrdinaryReadOnlyDriver(namespace: fixture.supplement.namespace, mode: .normal, log: log)
        let task = Task {
            try await context.observe(using: driver, authorize: { try await log.authorize() }) {
                await log.read($0)
                withUnsafeCurrentTask { $0?.cancel() }
            }
        }
        do {
            try await task.value
            XCTFail("cancelled observation delivered")
        } catch is CancellationError {
            // Only the requested cancellation is accepted.
        } catch { XCTFail("unexpected cancellation error: \(error)") }
        let readCount = await log.readCount(), state = await driver.counts()
        XCTAssertEqual(readCount, 1)
        XCTAssertEqual(state.statuses, 2)
        XCTAssertEqual(state.roots, 2)
        XCTAssertEqual(state.writes, 0)
        try fixture.requireOriginals()
    }

    func testOwnerRefusesForeignRetiredAndChangedRunBeforeEitherPrivateJournal() async throws {
        let fixture = try ColdOrdinaryFixture.load()
        let root = try privateDirectory()
        let originalJournal = root.appendingPathComponent("original-journal", isDirectory: true)
        let ordinaryJournal = root.appendingPathComponent("ordinary-journal", isDirectory: true)
        for directory in [originalJournal, ordinaryJournal] {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                attributes: [.posixPermissions: 0o700])
            try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: directory.path)
        }
        let originalSentinel = originalJournal.appendingPathComponent("do-not-repair")
        let ordinarySentinel = ordinaryJournal.appendingPathComponent("do-not-repair")
        let originalBytes = Data("owned-test-original-journal-sentinel".utf8)
        let ordinaryBytes = Data("owned-test-supplement-journal-sentinel".utf8)
        try originalBytes.write(to: originalSentinel, options: .withoutOverwriting)
        try ordinaryBytes.write(to: ordinarySentinel, options: .withoutOverwriting)
        for file in [originalSentinel, ordinarySentinel] {
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file.path)
        }
        let absentArchive = root.appendingPathComponent("never-created-archive")
        let content = try fixture.contentLocator()
        let endpoint = try XCTUnwrap(URL(string: "http://127.0.0.1:1"))
        let client = try AnyHTTPClient(baseURL: endpoint, expectedAccountID: fixture.preservation.destinationAccountID)
        let counter = ColdOrdinaryRunCounter()
        let foreignWorkspace = try AnyTorahWorkspace(accountID: fixture.preservation.destinationAccountID,
            spaceID: fixture.preservation.destinationSpaceID + "-foreign")
        let foreign = AnyApplicationSession(workspace: foreignWorkspace, engineStartedAt: "captured-run",
            verifyRun: { await counter.changedRun() })
        do {
            _ = try await AnyNativeImportedContextOwner.openContent(client: client, session: foreign,
                preservationReference: fixture.preservation, preservationJournalDirectory: originalJournal,
                contentReference: content, ordinaryPropertyReference: fixture.reference,
                ordinaryPropertyJournalDirectory: ordinaryJournal, archiveSource: .retainedFile(absentArchive))
            XCTFail("foreign workspace admitted")
        } catch { XCTAssertEqual(error as? AnyHostError, .wrongWorkspace) }
        await foreign.revokeAndDrain()
        let retired = AnyApplicationSession(workspace: fixture.preservation.binding.workspace,
            engineStartedAt: "captured-run", verifyRun: { await counter.changedRun() })
        await retired.revokeAndDrain()
        do {
            _ = try await AnyNativeImportedContextOwner.openContent(client: client, session: retired,
                preservationReference: fixture.preservation, preservationJournalDirectory: originalJournal,
                contentReference: content, ordinaryPropertyReference: fixture.reference,
                ordinaryPropertyJournalDirectory: ordinaryJournal, archiveSource: .retainedFile(absentArchive))
            XCTFail("retired parent admitted")
        } catch { XCTAssertEqual(error as? AnyHostError, .sessionClosed) }
        let beforeRunChange = await counter.count()
        XCTAssertEqual(beforeRunChange, 0)
        let changed = AnyApplicationSession(workspace: fixture.preservation.binding.workspace,
            engineStartedAt: "captured-run", verifyRun: { await counter.changedRun() })
        do {
            _ = try await AnyNativeImportedContextOwner.openContent(client: client, session: changed,
                preservationReference: fixture.preservation, preservationJournalDirectory: originalJournal,
                contentReference: content, ordinaryPropertyReference: fixture.reference,
                ordinaryPropertyJournalDirectory: ordinaryJournal, archiveSource: .retainedFile(absentArchive))
            XCTFail("changed run admitted")
        } catch { XCTAssertEqual(error as? AnyHostError, .engineRestarted) }
        let active = await changed.isActive, calls = await counter.count()
        XCTAssertFalse(active)
        XCTAssertEqual(calls, 1)
        await changed.revokeAndDrain()
        XCTAssertEqual(try Data(contentsOf: originalSentinel), originalBytes)
        XCTAssertEqual(try Data(contentsOf: ordinarySentinel), ordinaryBytes)
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: originalJournal.path), ["do-not-repair"])
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: ordinaryJournal.path), ["do-not-repair"])
        XCTAssertFalse(FileManager.default.fileExists(atPath: absentArchive.path))
        XCTAssertEqual(Set(try FileManager.default.contentsOfDirectory(atPath: root.path)),
            Set(["original-journal", "ordinary-journal"]))
        try fixture.requireOriginals()
    }

    private func privateDirectory() throws -> URL {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_IMPORTED_CONTEXT_FIXTURE_ROOT"] else {
            throw XCTSkip("Requires the isolated component owner's new private fixture parent.")
        }
        let root = URL(fileURLWithPath: path, isDirectory: true).standardizedFileURL
        let attrs = try FileManager.default.attributesOfItem(atPath: root.path)
        guard root.path == path, root.resolvingSymlinksInPath().path == root.path,
              attrs[.type] as? FileAttributeType == .typeDirectory,
              (attrs[.posixPermissions] as? NSNumber)?.intValue == 0o700 else {
            throw ColdOrdinaryFixtureError.unsafeFixture
        }
        let child = root.appendingPathComponent("ordinary-context-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: child, withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700])
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: child.path)
        // Only this newly created synthetic test directory is removed.
        addTeardownBlock { try FileManager.default.removeItem(at: child) }
        return child
    }
}

private enum ColdOrdinaryWire {
    static func encode<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    static func json<T: Encodable>(_ value: T) throws -> AnyJSON {
        try JSONDecoder().decode(AnyJSON.self, from: encode(value))
    }
}

private struct ColdOrdinaryFixture: Sendable {
    let retained: NativeCanonicalSupplementFixture
    let bundle: AnyHeartNativeSpaceBundle
    let supplement: AnyHeartNativeOrdinaryPropertySupplement
    let preservation: AnyNativeImportedContextReference
    let checkpoint: AnyDestinationSavedCheckpoint
    let reference: AnyNativeImportedOrdinaryPropertyReference
    let context: AnyNativeImportedOrdinaryPropertyContext

    static func load() throws -> Self {
        let retained = try NativeCanonicalSupplementFixture.load()
        let manifest = try Data(contentsOf: retained.bundle.appendingPathComponent("manifest.json"))
        let bundle = try AnyHeartNativeSpaceBundle(manifest: manifest,
            sourceAccountID: retained.plan.source.accountID, sourceSpaceID: retained.plan.source.spaceID) { member in
            let parts = member.path.split(separator: "/", omittingEmptySubsequences: false)
            guard !member.path.hasPrefix("/"), !member.path.contains("\\"), !member.path.contains("\0"),
                  parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }),
                  member.byteCount >= 0, member.byteCount <= 32 * 1024 * 1024 else {
                throw ColdOrdinaryFixtureError.unsafeFixture
            }
            var path = retained.bundle
            for (index, part) in parts.enumerated() {
                path.appendPathComponent(String(part))
                let attrs = try FileManager.default.attributesOfItem(atPath: path.path)
                guard attrs[.type] as? FileAttributeType ==
                    (index == parts.count - 1 ? .typeRegular : .typeDirectory) else {
                    throw ColdOrdinaryFixtureError.unsafeFixture
                }
            }
            let attrs = try FileManager.default.attributesOfItem(atPath: path.path)
            guard (attrs[.size] as? NSNumber)?.intValue == member.byteCount else {
                throw ColdOrdinaryFixtureError.unsafeFixture
            }
            return try Data(contentsOf: path)
        }
        let supplement = try AnyHeartNativeOrdinaryPropertySupplement(bundle: bundle,
            completedPreservationPlan: retained.plan, completedPreservationMappings: retained.mappings)
        let base = try AnyNativeImportedDefinitionDirectory(plan: retained.plan, mappings: retained.mappings)
        let canonical = try retained.bindings().filter {
            base.definition(sourceObjectID: $0.evidence.sourceObjectID) == nil
        }
        let files = retained.plan.items.filter {
            if case .file(_, _, let mime, _, _) = $0.operation {
                return mime == AnyHeartNativePreservationArchive.mimeType
            }
            return false
        }
        guard files.count == 1, let archive = files.first,
              case .file(_, _, _, let archiveBytes, let archiveSHA) = archive.operation else {
            throw ColdOrdinaryFixtureError.unexpectedOperation
        }
        let source = retained.plan.source, binding = retained.plan.binding
        // The original plan/mappings and archive seed are retained evidence.
        // Network and recovered-archive manifest fields below are explicitly
        // synthetic locator syntax. No complete archive/native open is claimed.
        let fields: [String: AnyJSON] = [
            "contract": .string(AnyNativeImportedContextReference.version),
            "destinationNetworkID": .string("synthetic-cold-context-network"),
            "destinationAccountID": .string(binding.workspace.accountID),
            "destinationSpaceID": .string(binding.workspace.spaceID),
            "storeID": .string(binding.storeID), "planID": .string(binding.planID),
            "planSHA256": .string(binding.planSHA256),
            "checkpointSHA256": .string(try AnyDestinationSavedCheckpoint.fingerprint(
                plan: retained.plan, mappings: retained.mappings)),
            "sourceAccountID": .string(source.accountID), "sourceSpaceID": .string(source.spaceID),
            "captureManifestSHA256": .string(source.captureManifestSHA256),
            "sourceWitnessSHA256": .string(source.witnessSHA256),
            "recoveredManifestSHA256": .string(AnyContentDigest.sha256(Data("synthetic-unadmitted-archive-manifest".utf8))),
            "archiveSourceKey": .string(archive.sourceKey), "archiveSHA256": .string(archiveSHA),
            "archiveBytes": .integer(archiveBytes),
            "supplementalCanonicalDefinitions": try ColdOrdinaryWire.json(canonical)
        ]
        let preservation = try AnyNativeImportedContextReference.decode(
            ColdOrdinaryWire.encode(AnyJSON.object(fields)))
        var intents: [AnyDestinationNativeIntent] = []
        var mappings: [AnyDestinationMigrationMapping] = []
        for item in supplement.plan.items {
            let resolved = try item.operation.resolved(
                destinationSpaceID: supplement.plan.binding.workspace.spaceID) { reference in
                    switch reference {
                    case .native(let id): return id
                    case .mapped: throw ColdOrdinaryFixtureError.unexpectedOperation
                    }
                }
            let native = try AnyDestinationNativeIntent.make(resolved, binding: supplement.plan.binding,
                sourceKey: item.sourceKey, sequence: nil, inlineContent: nil)
            guard case .definition(let intent) = native, intent.kind == .propertyDefinition,
                  intent.expectedOwnerID == supplement.namespace.ownerID else {
                throw ColdOrdinaryFixtureError.unexpectedOperation
            }
            let recordID = "cold-ordinary-" + String(intent.intentID.prefix(32))
            let fingerprint = AnyContentDigest.sha256(intent.specBytes)
            let changeID = "synthetic-change-" + intent.intentID
            let receipt: AnyJSON = .object([
                "contract": .string(AnyNativePreparedDefinitionMigration.contract),
                "accountId": .string(intent.binding.workspace.accountID),
                "spaceId": .string(intent.binding.workspace.spaceID),
                "storeId": .string(intent.binding.storeID), "planId": .string(intent.binding.planID),
                "planSHA256": .string(intent.binding.planSHA256), "sourceKey": .string(intent.sourceKey),
                "kind": .string(intent.kind.rawValue), "intentId": .string(intent.intentID),
                "specSHA256": .string(intent.specSHA256), "fingerprint": .string(fingerprint),
                "stage": .string("complete"), "outcome": .string("committed"),
                "objectId": .string(supplement.namespace.ownerID),
                "recordIds": .array([.string(recordID)]), "changeId": .string(changeID)
            ])
            let parsed = try AnyPreparedDefinitionReceipt(receipt, intent: intent)
            guard parsed.isCompleteAndCurrent else { throw ColdOrdinaryFixtureError.unexpectedOperation }
            intents.append(native)
            mappings.append(.init(sourceKey: item.sourceKey, sourceObjectID: item.sourceObjectID,
                kind: item.operation.kind, intentID: intent.intentID, objectID: supplement.namespace.ownerID,
                recordIDs: [recordID], fileID: nil, fingerprint: fingerprint,
                signedChangeIDs: [changeID], currentReceiptSHA256: AnyContentDigest.sha256(
                    try ColdOrdinaryWire.encode(receipt))))
        }
        let checkpoint = AnyDestinationSavedCheckpoint(plan: supplement.plan, mappings: mappings,
            checkpointSHA256: try AnyDestinationSavedCheckpoint.fingerprint(plan: supplement.plan, mappings: mappings),
            intents: intents)
        let reference = try AnyNativeImportedOrdinaryPropertyReference(preservationReference: preservation,
            bundle: bundle, completedPreservationPlan: retained.plan,
            completedPreservationMappings: retained.mappings, checkpoint: checkpoint)
        let context = try AnyNativeImportedOrdinaryPropertyContext(reference: reference,
            preservationReference: preservation, bundle: bundle, completedPreservationPlan: retained.plan,
            completedPreservationMappings: retained.mappings, checkpoint: checkpoint)
        return .init(retained: retained, bundle: bundle, supplement: supplement, preservation: preservation,
            checkpoint: checkpoint, reference: reference, context: context)
    }

    func changedPreservation(_ key: String, _ value: AnyJSON) throws -> AnyNativeImportedContextReference {
        var fields = try XCTUnwrap(try ColdOrdinaryWire.json(preservation).object)
        fields[key] = value
        return try AnyNativeImportedContextReference.decode(ColdOrdinaryWire.encode(AnyJSON.object(fields)))
    }

    func checkpointWith(plan: AnyDestinationMigrationPlan? = nil,
                        mappings: [AnyDestinationMigrationMapping]? = nil,
                        intents: [AnyDestinationNativeIntent]? = nil) throws -> AnyDestinationSavedCheckpoint {
        let plan = plan ?? checkpoint.plan, mappings = mappings ?? checkpoint.mappings
        return .init(plan: plan, mappings: mappings,
            checkpointSHA256: try AnyDestinationSavedCheckpoint.fingerprint(plan: plan, mappings: mappings),
            intents: intents ?? checkpoint.intents)
    }

    func makeReference(_ candidate: AnyDestinationSavedCheckpoint) throws
        -> AnyNativeImportedOrdinaryPropertyReference {
        try .init(preservationReference: preservation, bundle: bundle,
            completedPreservationPlan: retained.plan, completedPreservationMappings: retained.mappings,
            checkpoint: candidate)
    }

    func makeContext(reference candidate: AnyNativeImportedOrdinaryPropertyReference) throws
        -> AnyNativeImportedOrdinaryPropertyContext {
        try .init(reference: candidate, preservationReference: preservation, bundle: bundle,
            completedPreservationPlan: retained.plan, completedPreservationMappings: retained.mappings,
            checkpoint: checkpoint)
    }

    func originalDirectory() throws -> AnyNativeImportedDefinitionDirectory {
        try .init(plan: retained.plan, mappings: retained.mappings,
            supplementalCanonicalDefinitions: preservation.supplementalCanonicalDefinitions)
    }

    func documents(definitions: AnyNativeImportedDefinitionDirectory) throws -> [AnyNativeImportedDocumentEntry] {
        let composition = try AnyHeartNativeContentComposition(bundle: bundle)
        let sourceFacts = try AnyNativeImportedSourceFactsDirectory(plan: retained.plan, mappings: retained.mappings)
        let carriers = try AnyNativeImportedCatalogDirectory(plan: retained.plan, mappings: retained.mappings)
        return try AnyNativeImportedContentContext.documentEntries(plan: retained.plan,
            mappings: retained.mappings, composition: composition, definitions: definitions,
            sourceFacts: sourceFacts, catalogCarrierObjectIDs: carriers.entries.map(\.objectID))
    }

    func contentLocator() throws -> AnyNativeImportedContentContextReference {
        let fields: [String: AnyJSON] = [
            "contract": .string(AnyNativeImportedContentContextReference.version),
            "checkpointScope": .string("completed-preservation-current-content"),
            "preservationReferenceSHA256": .string(AnyContentDigest.sha256(try preservation.encoded())),
            "contentPlanID": .string(preservation.planID),
            "contentPlanSHA256": .string(preservation.planSHA256),
            "contentCheckpointSHA256": .string(preservation.checkpointSHA256),
            "contentSHA256": .string(try AnyHeartNativeContentComposition(bundle: bundle).contentSHA256)
        ]
        return try AnyNativeImportedContentContextReference.decode(
            ColdOrdinaryWire.encode(AnyJSON.object(fields)))
    }

    func requireOriginals() throws { try retained.requireRetainedInputsUnchanged() }

    static func namespaceReceipt(_ namespace: AnyDestinationImportedPropertyNamespace) throws -> AnyJSON {
        let intent = namespace.intent
        return .object([
            "contract": .string(AnyNativePreparedDefinitionMigration.contract),
            "accountId": .string(intent.binding.workspace.accountID),
            "spaceId": .string(intent.binding.workspace.spaceID),
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
}

private enum ColdOrdinaryFixtureError: Error, Equatable { case unsafeFixture, unexpectedOperation, revoked }

private actor ColdOrdinaryObservationLog {
    private var values: [String] = []
    private var active = true
    func authorize() throws {
        try Task.checkCancellation()
        if !active { throw ColdOrdinaryFixtureError.revoked }
    }
    func revoke() { active = false }
    func append(_ value: String) { values.append(value) }
    func read(_ sourceID: String) { values.append("read:" + sourceID) }
    func readCount() -> Int { values.filter { $0.hasPrefix("read:") }.count }
    func events() -> [String] { values }
}

private actor ColdOrdinaryReadOnlyDriver: AnyDestinationNativeDriving {
    enum Mode: Sendable { case normal, missing, changedFinalRoot }
    struct Counts: Sendable {
        var statuses = 0
        var roots = 0
        var writes = 0
    }
    let namespace: AnyDestinationImportedPropertyNamespace
    let mode: Mode
    let log: ColdOrdinaryObservationLog
    private var state = Counts()

    init(namespace: AnyDestinationImportedPropertyNamespace, mode: Mode, log: ColdOrdinaryObservationLog) {
        self.namespace = namespace; self.mode = mode; self.log = log
    }
    func counts() -> Counts { state }

    func status(_ intent: AnyDestinationNativeIntent,
                authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await authorize()
        guard case .definition(let definition) = intent, definition == namespace.intent else {
            throw ColdOrdinaryFixtureError.unexpectedOperation
        }
        state.statuses += 1; await log.append("status")
        if case .missing = mode { throw AnyEngineError.http(status: 404, code: "not_found") }
        return try ColdOrdinaryFixture.namespaceReceipt(namespace)
    }

    func importedPropertyNamespace(ownerID: String,
        authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        try await authorize()
        guard Data(ownerID.utf8) == Data(namespace.ownerID.utf8) else {
            throw ColdOrdinaryFixtureError.unexpectedOperation
        }
        state.roots += 1; await log.append("root")
        let root = try AnyDestinationContentProjection.root(namespace.originalNamespace, id: ownerID, type: false)
        if case .changedFinalRoot = mode, state.roots == 3 {
            var fields = try XCTUnwrap(root.object); fields["id"] = .string("foreign-valid-owner")
            return .object(fields)
        }
        return root
    }

    func prepare(_ intent: AnyDestinationNativeIntent, payload: URL?,
        authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        state.writes += 1; throw ColdOrdinaryFixtureError.unexpectedOperation
    }
    func commit(_ intent: AnyDestinationNativeIntent, receipt: AnyJSON,
        authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        state.writes += 1; throw ColdOrdinaryFixtureError.unexpectedOperation
    }
    func applySequence(objectID: String, authorize: @escaping AnyDestinationAuthorization) async throws -> Int64 {
        state.writes += 1; throw ColdOrdinaryFixtureError.unexpectedOperation
    }
}

private actor ColdOrdinaryRunCounter {
    private var calls = 0
    func changedRun() -> String { calls += 1; return "replacement-run" }
    func count() -> Int { calls }
}
