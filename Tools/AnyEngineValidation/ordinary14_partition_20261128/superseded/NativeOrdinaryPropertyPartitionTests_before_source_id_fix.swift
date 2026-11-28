import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

/// Actual original archive/plan bytes supply the fourteen captured descriptors.
/// Destination plans, mappings, intent observations and locators in this file
/// are explicitly synthetic. Small collection carriers supply inert coverage;
/// they are not a newly qualified preservation plan or a real native checkpoint.
/// No original182 operation, journal, client, source grant or producer executes.
/// The all-present case has NO fabricated second checkpoint or verification.
final class NativeOrdinaryPropertyPartitionTests: XCTestCase, @unchecked Sendable {
    private func hash(_ value: String) -> String { AnyContentDigest.sha256(Data(value.utf8)) }
    private func encode(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }

    private struct Fixture {
        let bundle: AnyHeartNativeSpaceBundle
        let checkpoint: AnyDestinationSavedCheckpoint
        let reference: AnyNativeImportedContextReference
        let relations: [AnyHeartNativeDefinitionCatalog.Relation]
    }

    private func fixture(_ retained: Retained, reused keys: [String],
                         changedDescriptor: Bool = false,
                         changedProvenance: Bool = false) throws -> Fixture {
        let bundle = retained.restored.bundle
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: bundle)
        let definitions = try AnyHeartNativeDefinitionPlan(catalog: catalog)
        let selected = try AnyHeartNativeOrdinaryPropertySupplement.relationKeys.map {
            try XCTUnwrap(catalog.relation(key: $0))
        }
        XCTAssertEqual(Set(selected.map { Data($0.objectID.utf8) }).count, 14)
        XCTAssertTrue(keys.allSatisfy(AnyHeartNativeOrdinaryPropertySupplement.relationKeys.contains))
        XCTAssertEqual(Set(keys).count, keys.count)
        let namespaceKey = "fixture-original-namespace"
        let first = try XCTUnwrap(selected.first)
        let namespace = AnyDestinationRootDefinition(xKey: "fixture.original.namespace",
            name: "Synthetic original property namespace", meta: .literal(.object([
                "heartSourceSpaceID": .string(bundle.sourceSpaceID),
                "heartCaptureSHA256": .string(bundle.manifestSHA256),
                "heartPropertyNamespace": .bool(true)
            ])))
        var items = [AnyDestinationMigrationItem(sourceKey: namespaceKey,
            sourceObjectID: first.objectID, operation: .collectionDefinition(namespace))]
        // Explicit synthetic carriers keep full selected source coverage without
        // representing their source relations as imported property definitions.
        for (index, relation) in selected.dropFirst().enumerated() {
            items.append(.init(sourceKey: "fixture-carrier-" + String(index),
                sourceObjectID: relation.objectID,
                operation: .collectionDefinition(.init(xKey: "fixture.carrier." + String(index),
                    name: "Synthetic coverage carrier", meta: .literal(.object([
                        "syntheticPartitionControl": .bool(true)
                    ]))))))
        }
        for relation in selected where keys.contains(relation.relationKey) {
            let binding = try XCTUnwrap(definitions.property(sourceKey: relation.relationKey))
            let originals = definitions.schemaItems.filter {
                Data($0.sourceKey.utf8) == Data(binding.sourceKey.utf8) &&
                    Data($0.sourceObjectID.utf8) == Data(relation.objectID.utf8)
            }
            XCTAssertEqual(originals.count, 1)
            let item = try XCTUnwrap(originals.first)
            guard case .propertyDefinition(_, let kind, let name, let xKey, let description,
                                           let scope, let format, let index) = item.operation else {
                throw AnyDestinationMigrationError.invalidPlan("fixture property operation")
            }
            var selectedFormat = format
            if changedProvenance, relation.relationKey == keys.first,
               case .literal(let value)? = format {
                var fields = try XCTUnwrap(value.object)
                var origin = try XCTUnwrap(fields["pinkhaHeart"]?.object)
                origin["snapshotSHA256"] = .string(hash("different captured descriptor"))
                fields["pinkhaHeart"] = .object(origin); selectedFormat = .literal(.object(fields))
            }
            items.append(.init(sourceKey: item.sourceKey, sourceObjectID: item.sourceObjectID,
                expectedRecordCount: item.expectedRecordCount,
                operation: .propertyDefinition(
                    owner: .mapped(sourceKey: namespaceKey, slot: .objectID, encoding: .rawID),
                    kind: kind, name: changedDescriptor && relation.relationKey == keys.first
                        ? name + " changed" : name, xKey: xKey, description: description,
                    scope: scope, xFormat: selectedFormat, index: index)))
        }
        let source = try AnyDestinationSourceBinding(bundle: bundle,
            semanticPlanSHA256: hash("synthetic selected fourteen coverage"),
            sourceObjectIDs: selected.map(\.objectID))
        let coverage = selected.map { relation in
            AnyDestinationCoverage(sourceObjectID: relation.objectID, disposition: .mapped(
                itemSourceKeys: items.filter {
                    Data($0.sourceObjectID.utf8) == Data(relation.objectID.utf8)
                }.map(\.sourceKey)))
        }
        let plan = try AnyDestinationMigrationPlan(source: source,
            workspace: .init(accountID: "fixture-account", spaceID: "fixture-space"),
            storeID: "fixture-store", planID: hash("synthetic-preservation-partition"),
            coverage: coverage, items: items)
        let checkpoint = try syntheticCheckpoint(plan)
        return .init(bundle: bundle, checkpoint: checkpoint,
            reference: try syntheticReference(retained, checkpoint: checkpoint), relations: selected)
    }

    private func syntheticCheckpoint(_ plan: AnyDestinationMigrationPlan) throws -> AnyDestinationSavedCheckpoint {
        var mappings: [AnyDestinationMigrationMapping] = []
        var intents: [AnyDestinationNativeIntent] = []
        var keyed: [Data: AnyDestinationMigrationMapping] = [:]
        for (index, item) in plan.items.enumerated() {
            let frozen = keyed
            let operation = try item.operation.resolved(destinationSpaceID: plan.binding.workspace.spaceID) {
                try AnyDestinationMigrationVerifier.resolve($0, in: frozen,
                    destinationSpaceID: plan.binding.workspace.spaceID)
            }
            let native = try AnyDestinationNativeIntent.make(operation, binding: plan.binding,
                sourceKey: item.sourceKey, sequence: nil, inlineContent: nil)
            let objectID: String, recordID: String
            switch operation {
            case .collectionDefinition:
                objectID = item.sourceKey == "fixture-original-namespace"
                    ? "fixture-native-namespace" : "fixture-native-carrier-" + String(index)
                recordID = objectID
            case .propertyDefinition(.native(let owner), _, _, _, _, _, _, _):
                objectID = owner; recordID = "fixture-native-property-" + String(index)
            default: throw AnyDestinationMigrationError.invalidPlan("unexpected fixture operation")
            }
            let mapping = AnyDestinationMigrationMapping(sourceKey: item.sourceKey,
                sourceObjectID: item.sourceObjectID, kind: item.operation.kind,
                intentID: native.identity.id, objectID: objectID, recordIDs: [recordID], fileID: nil,
                fingerprint: hash("synthetic fingerprint " + native.identity.id),
                signedChangeIDs: ["fixture-change-" + String(index)],
                currentReceiptSHA256: hash("synthetic receipt " + native.identity.id))
            mappings.append(mapping); intents.append(native); keyed[Data(item.sourceKey.utf8)] = mapping
        }
        return .init(plan: plan, mappings: mappings,
            checkpointSHA256: try AnyDestinationSavedCheckpoint.fingerprint(plan: plan, mappings: mappings),
            intents: intents)
    }

    private func syntheticReference(_ retained: Retained, checkpoint: AnyDestinationSavedCheckpoint) throws
        -> AnyNativeImportedContextReference {
        let source = checkpoint.plan.source, binding = checkpoint.plan.binding
        return try .decode(encode(.object([
            "contract": .string(AnyNativeImportedContextReference.version),
            "destinationNetworkID": .string("fixture-network"),
            "destinationAccountID": .string(binding.workspace.accountID),
            "destinationSpaceID": .string(binding.workspace.spaceID), "storeID": .string(binding.storeID),
            "planID": .string(binding.planID), "planSHA256": .string(binding.planSHA256),
            "checkpointSHA256": .string(checkpoint.checkpointSHA256),
            "sourceAccountID": .string(source.accountID), "sourceSpaceID": .string(source.spaceID),
            "captureManifestSHA256": .string(source.captureManifestSHA256),
            "sourceWitnessSHA256": .string(source.witnessSHA256),
            "recoveredManifestSHA256": .string(retained.recovered.manifestSHA256),
            "archiveSourceKey": .string("explicit-synthetic-locator-only"),
            "archiveSHA256": .string(AnyContentDigest.sha256(retained.archiveBytes)),
            "archiveBytes": .integer(Int64(retained.archiveBytes.count)),
            "supplementalCanonicalDefinitions": .array([])
        ])))
    }

    func testAllNewKeepsExactLegacyPlanAndClosedV1ReferenceBytes() throws {
        let retained = try self.retained()
        defer { XCTAssertNoThrow(try requireRetainedInputsUnchanged(retained)) }
        let f = try fixture(retained, reused: [])
        let strict = try AnyHeartNativeOrdinaryPropertySupplement(bundle: f.bundle,
            completedPreservationPlan: f.checkpoint.plan,
            completedPreservationMappings: f.checkpoint.mappings)
        let completed = try AnyHeartNativeOrdinaryPropertyCompletionPlan(bundle: f.bundle,
            preservation: f.checkpoint)
        let plan = try XCTUnwrap(completed.missingPlan)
        XCTAssertEqual(try AnyDestinationMigrationJournal.encoded(plan),
                       try AnyDestinationMigrationJournal.encoded(strict.plan))
        XCTAssertTrue(completed.partition.reusedSourceObjectIDs.isEmpty)
        XCTAssertEqual(completed.partition.newSourceObjectIDs, f.relations.map(\.objectID))
        let supplemental = try syntheticCheckpoint(plan)
        let old = try AnyNativeImportedOrdinaryPropertyReference(preservationReference: f.reference,
            bundle: f.bundle, completedPreservationPlan: f.checkpoint.plan,
            completedPreservationMappings: f.checkpoint.mappings, checkpoint: supplemental)
        let current = try AnyNativeImportedOrdinaryPropertyReference(preservationReference: f.reference,
            bundle: f.bundle, preservationCheckpoint: f.checkpoint, supplementalCheckpoint: supplemental)
        XCTAssertEqual(try current.encoded(), try old.encoded())
        XCTAssertNil(current.partition)
        let fields = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: current.encoded()).object)
        XCTAssertEqual(Set(fields.keys), Set(["contract", "checkpointScope", "preservationReferenceSHA256",
            "supplementPlanID", "supplementPlanSHA256", "supplementCheckpointSHA256",
            "namespaceOwnerID", "namespaceIntentID", "namespaceSHA256", "mappingsSHA256"]))
        XCTAssertEqual(try AnyNativeImportedOrdinaryPropertyReference.decode(current.encoded()).encoded(),
                       try current.encoded())
    }

    func testPartialOverlapImportsOnlyMissingAndPreservesOriginalCreationBindings() throws {
        let retained = try self.retained()
        defer { XCTAssertNoThrow(try requireRetainedInputsUnchanged(retained)) }
        let f = try fixture(retained, reused: ["source", "tag"])
        let completion = try AnyHeartNativeOrdinaryPropertyCompletionPlan(bundle: f.bundle,
            preservation: f.checkpoint)
        let source = try XCTUnwrap(f.relations.first { $0.relationKey == "source" })
        let tag = try XCTUnwrap(f.relations.first { $0.relationKey == "tag" })
        XCTAssertEqual(completion.partition.reusedSourceObjectIDs, [source.objectID, tag.objectID])
        let plan = try XCTUnwrap(completion.missingPlan)
        XCTAssertEqual(plan.items.count, 12)
        XCTAssertEqual(plan.source.sourceObjectIDs, completion.partition.newSourceObjectIDs)
        XCTAssertTrue(plan.items.allSatisfy { $0.operation.kind == "propertyDefinition" })
        XCTAssertFalse(plan.items.contains { [source.objectID, tag.objectID].contains($0.sourceObjectID) })
        XCTAssertTrue(Set(completion.partition.reusedSourceObjectIDs).isDisjoint(
            with: Set(completion.partition.newSourceObjectIDs)))
        XCTAssertEqual(Set(completion.partition.reusedSourceObjectIDs + completion.partition.newSourceObjectIDs),
                       Set(f.relations.map(\.objectID)))
        let supplemental = try syntheticCheckpoint(plan)
        let directory = try completion.directory(checkpoint: supplemental)
        for relation in f.relations {
            let entry = try XCTUnwrap(directory.definition(sourceObjectID: relation.objectID))
            XCTAssertEqual(entry.sourceSnapshotSHA256, relation.snapshot.snapshotSHA256)
            XCTAssertEqual(entry.sourceJSONViewSHA256, relation.snapshot.viewSHA256)
            let intent = try XCTUnwrap(entry.intent)
            let expected = [source.objectID, tag.objectID].contains(relation.objectID)
                ? f.checkpoint.plan.binding : plan.binding
            XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(intent.binding, expected))
        }
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryPropertySupplement(bundle: f.bundle,
            completedPreservationPlan: f.checkpoint.plan,
            completedPreservationMappings: f.checkpoint.mappings)) {
            guard case AnyDestinationMigrationError.invalidPlan(let reason) = $0 else {
                return XCTFail("strict legacy constructor must keep its original refusal")
            }
            XCTAssertEqual(reason, "ordinary14 original definition: source")
        }
    }

    func testAllPresentKeepsOriginalCheckpointAndHasNoSecondPlanOrCompletion() throws {
        let retained = try self.retained()
        defer { XCTAssertNoThrow(try requireRetainedInputsUnchanged(retained)) }
        let f = try fixture(retained, reused: AnyHeartNativeOrdinaryPropertySupplement.relationKeys)
        let completion = try AnyHeartNativeOrdinaryPropertyCompletionPlan(bundle: f.bundle,
            preservation: f.checkpoint)
        XCTAssertNil(completion.missingPlan)
        XCTAssertTrue(completion.partition.newSourceObjectIDs.isEmpty)
        XCTAssertEqual(completion.partition.reusedSourceObjectIDs, f.relations.map(\.objectID))
        let directory = try completion.directory(checkpoint: nil)
        XCTAssertTrue(directory.supplementalPropertyBindings.isEmpty)
        XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(directory.binding, f.checkpoint.plan.binding))
        let reference = try AnyNativeImportedOrdinaryPropertyReference(preservationReference: f.reference,
            bundle: f.bundle, preservationCheckpoint: f.checkpoint, supplementalCheckpoint: nil)
        XCTAssertFalse(reference.hasSupplementalCheckpoint)
        XCTAssertEqual(reference.checkpointScope, "ordinary14-already-imported-in-preservation")
        XCTAssertEqual(reference.supplementPlanID, f.checkpoint.plan.binding.planID)
        XCTAssertEqual(reference.supplementCheckpointSHA256, f.checkpoint.checkpointSHA256)
        XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(
            try reference.binding(preservation: f.reference), f.checkpoint.plan.binding))
        XCTAssertThrowsError(try completion.directory(checkpoint: f.checkpoint)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .changedCheckpoint)
        }
        XCTAssertThrowsError(try AnyNativeImportedOrdinaryPropertyReference(
            preservationReference: f.reference, bundle: f.bundle,
            preservationCheckpoint: f.checkpoint, supplementalCheckpoint: f.checkpoint)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .changedCheckpoint)
        }
    }

    func testReusedMappingIntentAndExactDescriptorProvenanceCannotBeSubstituted() throws {
        let retained = try self.retained()
        defer { XCTAssertNoThrow(try requireRetainedInputsUnchanged(retained)) }
        let f = try fixture(retained, reused: ["source", "tag"])
        let first = try XCTUnwrap(f.checkpoint.plan.items.indices.first {
            f.checkpoint.plan.items[$0].operation.kind == "propertyDefinition"
        })
        let second = first + 1
        XCTAssertTrue(f.checkpoint.intents.indices.contains(second))
        var intents = f.checkpoint.intents; intents.swapAt(first, second)
        let wrongIntent = AnyDestinationSavedCheckpoint(plan: f.checkpoint.plan,
            mappings: f.checkpoint.mappings, checkpointSHA256: f.checkpoint.checkpointSHA256, intents: intents)
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryPropertyCompletionPlan(
            bundle: f.bundle, preservation: wrongIntent)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError,
                .changedDefinition(f.checkpoint.plan.items[first].sourceObjectID))
        }
        var mappings = f.checkpoint.mappings
        let old = mappings[first]
        mappings[first] = .init(sourceKey: old.sourceKey, sourceObjectID: old.sourceObjectID,
            kind: old.kind, intentID: hash("foreign immutable intent"), objectID: old.objectID,
            recordIDs: old.recordIDs, fileID: old.fileID, fingerprint: old.fingerprint,
            signedChangeIDs: old.signedChangeIDs, currentReceiptSHA256: old.currentReceiptSHA256)
        let wrongMapping = AnyDestinationSavedCheckpoint(plan: f.checkpoint.plan, mappings: mappings,
            checkpointSHA256: try AnyDestinationSavedCheckpoint.fingerprint(plan: f.checkpoint.plan, mappings: mappings),
            intents: f.checkpoint.intents)
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryPropertyCompletionPlan(
            bundle: f.bundle, preservation: wrongMapping)) {
            XCTAssertEqual($0 as? AnyNativeImportedDefinitionError, .invalidMappings)
        }
        let sourceID = try XCTUnwrap(f.relations.first { $0.relationKey == "source" }).objectID
        let changed = try fixture(retained, reused: ["source"], changedDescriptor: true)
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryPropertyCompletionPlan(
            bundle: changed.bundle, preservation: changed.checkpoint)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError,
                .changedDefinition(sourceID))
        }
        let provenance = try fixture(retained, reused: ["source"], changedProvenance: true)
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryPropertyCompletionPlan(
            bundle: provenance.bundle, preservation: provenance.checkpoint)) {
            XCTAssertEqual($0 as? AnyNativeImportedDefinitionError,
                .invalidOrigin(sourceID))
        }
    }

    func testColdPartialReferenceReconstructsBothExactBindingsAndRejectsChangedPartition() throws {
        let retained = try self.retained()
        defer { XCTAssertNoThrow(try requireRetainedInputsUnchanged(retained)) }
        let f = try fixture(retained, reused: ["source"])
        let completion = try AnyHeartNativeOrdinaryPropertyCompletionPlan(bundle: f.bundle, preservation: f.checkpoint)
        let supplemental = try syntheticCheckpoint(XCTUnwrap(completion.missingPlan))
        let reference = try AnyNativeImportedOrdinaryPropertyReference(preservationReference: f.reference,
            bundle: f.bundle, preservationCheckpoint: f.checkpoint, supplementalCheckpoint: supplemental)
        let bytes = try reference.encoded()
        let decoded = try AnyNativeImportedOrdinaryPropertyReference.decode(bytes)
        XCTAssertEqual(try decoded.encoded(), bytes)
        let context = try AnyNativeImportedOrdinaryPropertyContext(reference: decoded,
            preservationReference: f.reference, bundle: f.bundle,
            completedPreservationPlan: f.checkpoint.plan,
            completedPreservationMappings: f.checkpoint.mappings,
            checkpoint: supplemental, preservationCheckpoint: f.checkpoint)
        let combined = try context.merging(into: completion.preservationDirectory)
        XCTAssertEqual(combined.supplementalPropertyBindings.count, 1)
        for relation in f.relations {
            let expected = relation.relationKey == "source" ? f.checkpoint.plan.binding : supplemental.plan.binding
            XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(
                try context.expectedCreationBinding(sourceObjectID: relation.objectID), expected))
        }
        var fields = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: bytes).object)
        var partition = try XCTUnwrap(fields["partition"]?.object)
        var reused = try XCTUnwrap(partition["reusedSourceObjectIDs"]?.array)
        var added = try XCTUnwrap(partition["newSourceObjectIDs"]?.array)
        let original = reused[0]; reused[0] = added[0]; added[0] = original
        partition["reusedSourceObjectIDs"] = .array(reused)
        partition["newSourceObjectIDs"] = .array(added); fields["partition"] = .object(partition)
        let changed = try AnyNativeImportedOrdinaryPropertyReference.decode(encode(.object(fields)))
        XCTAssertThrowsError(try AnyNativeImportedOrdinaryPropertyContext(reference: changed,
            preservationReference: f.reference, bundle: f.bundle,
            completedPreservationPlan: f.checkpoint.plan,
            completedPreservationMappings: f.checkpoint.mappings,
            checkpoint: supplemental, preservationCheckpoint: f.checkpoint)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .changedCheckpoint)
        }
    }

    func testColdAllPresentUsesOnlyOriginalCheckpointAndRejectsForeignBinding() throws {
        let retained = try self.retained()
        defer { XCTAssertNoThrow(try requireRetainedInputsUnchanged(retained)) }
        let f = try fixture(retained, reused: AnyHeartNativeOrdinaryPropertySupplement.relationKeys)
        let completion = try AnyHeartNativeOrdinaryPropertyCompletionPlan(bundle: f.bundle, preservation: f.checkpoint)
        let reference = try AnyNativeImportedOrdinaryPropertyReference(preservationReference: f.reference,
            bundle: f.bundle, preservationCheckpoint: f.checkpoint, supplementalCheckpoint: nil)
        let cold = try AnyNativeImportedOrdinaryPropertyReference.decode(reference.encoded())
        let context = try AnyNativeImportedOrdinaryPropertyContext(reference: cold,
            preservationReference: f.reference, bundle: f.bundle,
            completedPreservationPlan: f.checkpoint.plan,
            completedPreservationMappings: f.checkpoint.mappings,
            checkpoint: f.checkpoint, preservationCheckpoint: f.checkpoint)
        XCTAssertNil(context.expectedSupplementalBinding)
        XCTAssertEqual(context.savedPlan.canonicalBytes, f.checkpoint.plan.canonicalBytes)
        XCTAssertTrue(try context.merging(into: completion.preservationDirectory).supplementalPropertyBindings.isEmpty)
        for relation in f.relations {
            XCTAssertTrue(AnyNativeImportedContextReference.sameBinding(
                try context.expectedCreationBinding(sourceObjectID: relation.objectID), f.checkpoint.plan.binding))
        }
        var fields = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: f.reference.encoded()).object)
        fields["destinationAccountID"] = .string("foreign-account")
        let foreign = try AnyNativeImportedContextReference.decode(encode(.object(fields)))
        XCTAssertThrowsError(try cold.binding(preservation: foreign)) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .invalidReference)
        }
        XCTAssertFalse(context.provesCurrentNativeState)
        XCTAssertFalse(context.permitsMigrationReplay)
    }

    func testPartitionCodecRefusesDuplicatesUnknownFieldsAndLegacyFieldInjection() throws {
        let reused = (0..<2).map { "source-" + String($0) }
        let new = (2..<14).map { "source-" + String($0) }
        let partition = try AnyHeartNativeOrdinaryPropertyPartition(reused: reused, new: new)
        let bytes = try AnyDestinationMigrationJournal.encoded(partition)
        let decoded = try JSONDecoder().decode(AnyHeartNativeOrdinaryPropertyPartition.self, from: bytes)
        XCTAssertEqual(decoded.reusedSourceObjectIDs, reused)
        XCTAssertEqual(decoded.newSourceObjectIDs, new)
        XCTAssertThrowsError(try AnyHeartNativeOrdinaryPropertyPartition(reused: reused, new: [reused[0]] + Array(new.dropFirst()))) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .invalidReference)
        }
        var fields = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: bytes).object)
        fields["authority"] = .bool(true)
        XCTAssertThrowsError(try JSONDecoder().decode(AnyHeartNativeOrdinaryPropertyPartition.self,
            from: encode(.object(fields)))) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .invalidReference)
        }
        let retained = try self.retained()
        defer { XCTAssertNoThrow(try requireRetainedInputsUnchanged(retained)) }
        let f = try fixture(retained, reused: [])
        let complete = try AnyHeartNativeOrdinaryPropertyCompletionPlan(bundle: f.bundle, preservation: f.checkpoint)
        let supplemental = try syntheticCheckpoint(XCTUnwrap(complete.missingPlan))
        let old = try AnyNativeImportedOrdinaryPropertyReference(preservationReference: f.reference,
            bundle: f.bundle, completedPreservationPlan: f.checkpoint.plan,
            completedPreservationMappings: f.checkpoint.mappings, checkpoint: supplemental)
        var oldFields = try XCTUnwrap(JSONDecoder().decode(AnyJSON.self, from: old.encoded()).object)
        oldFields["partition"] = .null
        XCTAssertThrowsError(try AnyNativeImportedOrdinaryPropertyReference.decode(encode(.object(oldFields)))) {
            XCTAssertEqual($0 as? AnyNativeImportedOrdinaryPropertyContextError, .invalidReference)
        }
    }

    func testCancellationRefusesPartitionBeforeReturningHistoricalCorrespondence() async throws {
        let retained = try self.retained()
        defer { XCTAssertNoThrow(try requireRetainedInputsUnchanged(retained)) }
        let f = try fixture(retained, reused: ["source"])
        let task = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            XCTAssertThrowsError(try AnyHeartNativeOrdinaryPropertyCompletionPlan(
                bundle: f.bundle, preservation: f.checkpoint)) {
                XCTAssertTrue($0 is CancellationError)
            }
        }
        await task.value
    }

    private struct Retained {
        let archiveBytes: Data
        let planBytes: Data
        let plan: AnyDestinationMigrationPlan
        let restored: AnyHeartNativePreservationArchive.Restored
        let recovered: AnyHeartNativeRecoveredDefinitions
    }

    private func retained() throws -> Retained {
        let archiveBytes = try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_ARCHIVE", bytes: 1_634_696,
            sha256: "5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463")
        let planBytes = try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_PLAN", bytes: 1_823_803,
            sha256: "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930")
        let plan = try AnyDestinationMigrationPlan.decode(planBytes)
        XCTAssertEqual(plan.items.count, 182)
        let files = plan.items.compactMap { item -> (Int64, String)? in
            guard case .file(_, _, let mime, let size, let sha) = item.operation,
                  mime == AnyHeartNativePreservationArchive.mimeType else { return nil }
            return (size, sha)
        }
        XCTAssertEqual(files.count, 1)
        let expectedFile = try XCTUnwrap(files.first)
        XCTAssertEqual(expectedFile.0, Int64(archiveBytes.count))
        XCTAssertEqual(expectedFile.1, AnyContentDigest.sha256(archiveBytes))
        // Actual catalog values are .object expressions with a mapped URI.
        // Select the unique type declaration's literal contract/source metadata.
        let metadataRows = plan.items.compactMap { item -> [String: AnyJSON]? in
            guard case .typeDefinition(let draft) = item.operation,
                  case .literal(let value) = draft.meta, let fields = value.object,
                  fields["preservationContract"] == .string(AnyHeartNativeSourcePreservation.contract),
                  fields["sourceCaptureManifestSHA256"] == .string(plan.source.captureManifestSHA256)
            else { return nil }
            return fields
        }
        XCTAssertEqual(metadataRows.count, 1)
        let metadata = try XCTUnwrap(metadataRows.first)
        let recovery = try XCTUnwrap(metadata["sourceRecoveryManifestSHA256"]?.string)
        let binding = try AnyHeartNativePreservationArchive.Binding(
            expectedAccountID: plan.source.accountID, expectedSpaceID: plan.source.spaceID,
            captureManifestSHA256: plan.source.captureManifestSHA256,
            sourceWitnessSHA256: plan.source.witnessSHA256, recoveredManifestSHA256: recovery)
        let restored = try AnyHeartNativePreservationArchive.restore(archiveBytes, expected: binding)
        return .init(archiveBytes: archiveBytes, planBytes: planBytes, plan: plan, restored: restored,
                     recovered: try XCTUnwrap(restored.recoveredDefinitions))
    }

    private func requireRetainedInputsUnchanged(_ value: Retained) throws {
        XCTAssertEqual(try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_ARCHIVE", bytes: 1_634_696,
            sha256: "5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463"), value.archiveBytes)
        XCTAssertEqual(try fixedInput("PINKHA_CAPTURE_PRODUCER_RETAINED_V1_PLAN", bytes: 1_823_803,
            sha256: "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930"), value.planBytes)
    }

    /// Reads only a later controller's two exact private fixture inputs. No
    /// original loose-member tree, journal, account or network is consulted.
    private func fixedInput(_ variable: String, bytes expectedBytes: Int, sha256: String) throws -> Data {
        guard let path = ProcessInfo.processInfo.environment[variable] else {
            throw XCTSkip("Required retained original input is not supplied; selected admission must reject a skip.")
        }
        let fd = open(path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        guard fd >= 0 else { throw AnyHeartNativePreservationError.binding }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        var before = stat(), after = stat(), named = stat()
        guard fstat(fd, &before) == 0,
              before.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG),
              before.st_nlink == 1, before.st_size == Int64(expectedBytes),
              expectedBytes <= AnyHeartNativePreservationArchive.maximumBytes else {
            throw AnyHeartNativePreservationError.binding
        }
        var data = Data()
        while data.count <= expectedBytes {
            let part = try handle.read(upToCount: min(65_536, expectedBytes + 1 - data.count)) ?? Data()
            if part.isEmpty { break }; data.append(part)
        }
        guard data.count == expectedBytes, AnyContentDigest.sha256(data) == sha256,
              fstat(fd, &after) == 0, lstat(path, &named) == 0,
              sameFile(before, after), sameFile(before, named) else {
            throw AnyHeartNativePreservationError.binding
        }
        try handle.close()
        return data
    }

    private func sameFile(_ a: stat, _ b: stat) -> Bool {
        guard a.st_dev == b.st_dev, a.st_ino == b.st_ino, a.st_mode == b.st_mode,
              a.st_uid == b.st_uid, a.st_gid == b.st_gid, a.st_nlink == b.st_nlink,
              a.st_size == b.st_size else { return false }
        #if canImport(Darwin)
        return a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
            a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
        #else
        return a.st_mtim.tv_sec == b.st_mtim.tv_sec && a.st_mtim.tv_nsec == b.st_mtim.tv_nsec &&
            a.st_ctim.tv_sec == b.st_ctim.tv_sec && a.st_ctim.tv_nsec == b.st_ctim.tv_nsec
        #endif
    }


}
