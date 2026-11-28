import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Seven new synthetic correspondence controls for the Ordinary14 producer.
/// These use valid inert source/plan/mapping/intent DTOs, not a native capture,
/// completed journal, current receipt, public native Completion or host lease.
/// The seventeen-ID source and one-item plan are deliberately not the original
/// 159/182 corpus. No private fixture, executor, native call or old method runs.
final class NativeOrdinaryMigrationProducerTests: XCTestCase, @unchecked Sendable {
    private func digest(_ text: String) -> String {
        AnyContentDigest.sha256(Data(text.utf8))
    }

    private func source(accountID: String = "synthetic-source-account",
                        spaceID: String = "synthetic-source-space",
                        witness: String? = nil, capture: String? = nil,
                        semantic: String? = nil, ids: [String]? = nil) throws -> AnyDestinationSourceBinding {
        try .init(accountID: accountID, spaceID: spaceID,
            witnessSHA256: witness ?? digest("synthetic-witness"),
            captureManifestSHA256: capture ?? digest("synthetic-capture"),
            semanticPlanSHA256: semantic ?? digest("synthetic-complete-semantics"),
            sourceObjectIDs: ids ?? (0..<17).map { "synthetic-source-" + String($0) })
    }

    private func subset(of complete: AnyDestinationSourceBinding) throws -> AnyDestinationSourceBinding {
        try source(accountID: complete.accountID, spaceID: complete.spaceID,
            witness: complete.witnessSHA256, capture: complete.captureManifestSHA256,
            semantic: digest("synthetic-fourteen-semantics"),
            ids: Array(complete.sourceObjectIDs.prefix(14)))
    }

    private func copy(_ value: AnyDestinationSourceBinding,
                      accountID: String? = nil, spaceID: String? = nil,
                      witness: String? = nil, capture: String? = nil,
                      semantic: String? = nil, ids: [String]? = nil) throws -> AnyDestinationSourceBinding {
        try source(accountID: accountID ?? value.accountID, spaceID: spaceID ?? value.spaceID,
            witness: witness ?? value.witnessSHA256, capture: capture ?? value.captureManifestSHA256,
            semantic: semantic ?? value.semanticPlanSHA256, ids: ids ?? value.sourceObjectIDs)
    }

    /// The real typed intent constructor is used, but every observation below
    /// remains synthetic. This exercises checkpoint equality, not journal load.
    private func syntheticCheckpoint(name: String = "Synthetic collection") throws
        -> AnyDestinationSavedCheckpoint {
        let source = try self.source(ids: ["synthetic-definition"])
        let item = AnyDestinationMigrationItem(sourceKey: "synthetic-collection",
            sourceObjectID: "synthetic-definition", expectedRecordCount: 1,
            operation: .collectionDefinition(.init(xKey: "synthetic-collection", name: name)))
        let plan = try AnyDestinationMigrationPlan(source: source,
            workspace: .init(accountID: "synthetic-destination-account", spaceID: "synthetic-destination-space"),
            storeID: "synthetic-store", planID: digest("synthetic-plan-id"),
            coverage: [.init(sourceObjectID: item.sourceObjectID,
                             disposition: .mapped(itemSourceKeys: [item.sourceKey]))],
            items: [item])
        try plan.requireExecutable()
        let intent = try AnyDestinationNativeIntent.make(item.operation, binding: plan.binding,
            sourceKey: item.sourceKey, sequence: nil, inlineContent: nil)
        guard case .definition(let definition) = intent, definition.kind == .collectionDefinition else {
            throw SyntheticOrdinaryProducerFailure.fixture
        }
        let mapping = AnyDestinationMigrationMapping(sourceKey: item.sourceKey,
            sourceObjectID: item.sourceObjectID, kind: item.operation.kind,
            intentID: intent.identity.id, objectID: "synthetic-owner",
            recordIDs: ["synthetic-owner"], fileID: nil, fingerprint: digest("synthetic-fingerprint"),
            signedChangeIDs: ["synthetic-change"], currentReceiptSHA256: digest("synthetic-receipt"))
        return .init(plan: plan, mappings: [mapping],
            checkpointSHA256: try AnyDestinationSavedCheckpoint.fingerprint(plan: plan, mappings: [mapping]),
            intents: [intent])
    }

    private func replacing(_ original: AnyDestinationSavedCheckpoint,
                           mappings: [AnyDestinationMigrationMapping]? = nil,
                           intents: [AnyDestinationNativeIntent]? = nil,
                           checkpointSHA256: String? = nil) throws -> AnyDestinationSavedCheckpoint {
        let mappings = mappings ?? original.mappings
        let fingerprint = try checkpointSHA256 ??
            AnyDestinationSavedCheckpoint.fingerprint(plan: original.plan, mappings: mappings)
        return .init(plan: original.plan, mappings: mappings, checkpointSHA256: fingerprint,
                     intents: intents ?? original.intents)
    }

    func testExactSubsetReturnsTheUnmodifiedCompleteSourceBinding() throws {
        let complete = try source()
        let selected = try subset(of: complete)
        let observed = try AnyHeartNativeOrdinaryExecutionStage.completeCaptureSource(
            for: selected, expectedSubset: selected, completeSource: complete)
        XCTAssertEqual(selected.sourceObjectIDs.count, 14)
        XCTAssertEqual(observed.sourceObjectIDs.count, 17)
        XCTAssertEqual(try AnyDestinationMigrationJournal.encoded(observed),
                       AnyDestinationMigrationJournal.encoded(complete))
        XCTAssertNotEqual(try AnyDestinationMigrationJournal.encoded(observed),
                          AnyDestinationMigrationJournal.encoded(selected))
        XCTAssertEqual(observed.semanticPlanSHA256, complete.semanticPlanSHA256)
        XCTAssertNotEqual(observed.semanticPlanSHA256, selected.semanticPlanSHA256)
        XCTAssertNil(observed.definitionManifestBytes)
    }

    func testChangedOrForeignSubsetIsRefusedAtTheCorrespondenceBoundary() throws {
        let complete = try source()
        let selected = try subset(of: complete)
        var foreignIDs = selected.sourceObjectIDs
        foreignIDs[0] = "synthetic-foreign-definition"
        let candidates: [(String, AnyDestinationSourceBinding)] = [
            ("account", try copy(selected, accountID: "foreign-account")),
            ("space", try copy(selected, spaceID: "foreign-space")),
            ("witness", try copy(selected, witness: digest("other-witness"))),
            ("capture", try copy(selected, capture: digest("other-capture"))),
            ("semantic", try copy(selected, semantic: digest("other-semantics"))),
            ("ordered-identities", try copy(selected, ids: Array(selected.sourceObjectIDs.reversed()))),
            ("foreign-identity", try copy(selected, ids: foreignIDs)),
            ("whole-source-in-subset-slot", complete)
        ]
        for (label, candidate) in candidates {
            // Each constructor above already succeeded; refusal must come from
            // the new exact comparison, not an unrelated DTO decode error.
            XCTAssertThrowsError(try AnyHeartNativeOrdinaryExecutionStage.completeCaptureSource(
                for: candidate, expectedSubset: selected, completeSource: complete), label) {
                XCTAssertEqual($0 as? AnyDestinationMigrationError, .changedSource)
            }
        }
    }

    func testCanonicallyEquivalentUnicodeStillRequiresExactSourceBytes() throws {
        let complete = try source(accountID: "synthetic-caf\u{e9}")
        let selected = try subset(of: complete)
        let alias = try copy(selected, accountID: "synthetic-cafe\u{301}")
        XCTAssertEqual(alias.accountID, selected.accountID)
        XCTAssertNotEqual(Data(alias.accountID.utf8), Data(selected.accountID.utf8))
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryExecutionStage.completeCaptureSource(
            for: alias, expectedSubset: selected, completeSource: complete)) {
            XCTAssertEqual($0 as? AnyDestinationMigrationError, .changedSource)
        }
        let exact = try AnyHeartNativeOrdinaryExecutionStage.completeCaptureSource(
            for: selected, expectedSubset: selected, completeSource: complete)
        XCTAssertEqual(Data(exact.accountID.utf8), Data(complete.accountID.utf8))
    }

    func testExactCheckpointComparisonRetainsOnlyHistoricalEvidence() throws {
        let checkpoint = try syntheticCheckpoint()
        try AnyHeartNativeOrdinaryExecutionStage.requireSameCheckpoint(
            checkpoint, expected: checkpoint, referenceSHA256: checkpoint.checkpointSHA256)
        XCTAssertEqual(checkpoint.plan.items.count, 1)
        XCTAssertEqual(checkpoint.mappings.count, 1)
        XCTAssertEqual(checkpoint.intents.count, 1)
        XCTAssertEqual(checkpoint.nativeOperationsPerformed, 0)
        XCTAssertFalse(checkpoint.provesCurrentNativeState)
        XCTAssertEqual(checkpoint.checkpointSHA256,
            try AnyDestinationSavedCheckpoint.fingerprint(plan: checkpoint.plan, mappings: checkpoint.mappings))
    }

    func testSelfConsistentChangedMappingPlanOrReferenceCannotReplaceTheCheckpoint() throws {
        let expected = try syntheticCheckpoint()
        let old = try XCTUnwrap(expected.mappings.first)
        let changedMapping = AnyDestinationMigrationMapping(sourceKey: old.sourceKey,
            sourceObjectID: old.sourceObjectID, kind: old.kind, intentID: old.intentID,
            objectID: "other-synthetic-owner", recordIDs: ["other-synthetic-owner"],
            fileID: nil, fingerprint: old.fingerprint, signedChangeIDs: old.signedChangeIDs,
            currentReceiptSHA256: old.currentReceiptSHA256)
        let changed = try replacing(expected, mappings: [changedMapping])
        XCTAssertEqual(changed.checkpointSHA256,
            try AnyDestinationSavedCheckpoint.fingerprint(plan: changed.plan, mappings: changed.mappings))
        XCTAssertNotEqual(changed.checkpointSHA256, expected.checkpointSHA256)
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryExecutionStage.requireSameCheckpoint(
            changed, expected: expected, referenceSHA256: expected.checkpointSHA256)) {
            XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .changedCheckpoint)
        }
        let otherPlan = try syntheticCheckpoint(name: "Changed collection")
        XCTAssertNotEqual(otherPlan.plan.canonicalBytes, expected.plan.canonicalBytes)
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryExecutionStage.requireSameCheckpoint(
            otherPlan, expected: expected, referenceSHA256: expected.checkpointSHA256)) {
            XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .changedCheckpoint)
        }
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryExecutionStage.requireSameCheckpoint(
            expected, expected: expected, referenceSHA256: digest("foreign-reference"))) {
            XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .changedCheckpoint)
        }
        let corruptFingerprint = try replacing(expected, checkpointSHA256: digest("corrupt-fingerprint"))
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryExecutionStage.requireSameCheckpoint(
            corruptFingerprint, expected: expected, referenceSHA256: corruptFingerprint.checkpointSHA256)) {
            XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .changedCheckpoint)
        }
    }

    func testMissingOrSubstitutedIntentIsRefusedEvenWithUnchangedPlanAndMappings() throws {
        let expected = try syntheticCheckpoint()
        let foreign = try syntheticCheckpoint(name: "Different intent specification")
        for candidate in [try replacing(expected, intents: []),
                          try replacing(expected, intents: foreign.intents)] {
            XCTAssertEqual(candidate.plan.canonicalBytes, expected.plan.canonicalBytes)
            XCTAssertEqual(try AnyDestinationMigrationJournal.encoded(candidate.mappings),
                           AnyDestinationMigrationJournal.encoded(expected.mappings))
            XCTAssertEqual(candidate.checkpointSHA256, expected.checkpointSHA256)
            XCTAssertThrowsError(try AnyHeartNativeOrdinaryExecutionStage.requireSameCheckpoint(
                candidate, expected: expected, referenceSHA256: expected.checkpointSHA256)) {
                XCTAssertEqual($0 as? AnyHeartNativeMigrationProducerError, .changedCheckpoint)
            }
        }
    }

    func testCancellationRefusesBothPureDeliveries() async throws {
        let complete = try source()
        let selected = try subset(of: complete)
        let checkpoint = try syntheticCheckpoint()
        let task = Task<[Bool], Never> {
            withUnsafeCurrentTask { $0?.cancel() }
            var refused: [Bool] = []
            do {
                _ = try AnyHeartNativeOrdinaryExecutionStage.completeCaptureSource(
                    for: selected, expectedSubset: selected, completeSource: complete)
                refused.append(false)
            } catch is CancellationError { refused.append(true) }
              catch { refused.append(false) }
            do {
                try AnyHeartNativeOrdinaryExecutionStage.requireSameCheckpoint(
                    checkpoint, expected: checkpoint, referenceSHA256: checkpoint.checkpointSHA256)
                refused.append(false)
            } catch is CancellationError { refused.append(true) }
              catch { refused.append(false) }
            return refused
        }
        let refused = await task.value
        XCTAssertEqual(refused, [true, true])
    }
}

private enum SyntheticOrdinaryProducerFailure: Error { case fixture }
