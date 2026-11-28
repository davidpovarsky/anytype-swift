import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativeImportedContentContextError: Error, Equatable, Sendable {
    case invalidReference
    case changedContentCheckpoint
    case missingContentCheckpoint
    case unmappedDocument(String)
    case changedDocument(String)
}

/// A separate editable-content view of the existing completed preservation
/// checkpoint. That whole plan already contains current content and its distinct
/// immutable catalog carrier. No second execution or new checkpoint is needed.
/// Neither locator grants current native authority.
public struct AnyNativeImportedContentContextReference: Codable, Sendable {
    public static let version = "pinkha-native-imported-content-context-v1"
    public static let maximumBytes = 4096
    public let contract: String
    public let checkpointScope: String
    public let preservationReferenceSHA256: String
    public let contentPlanID: String
    public let contentPlanSHA256: String
    public let contentCheckpointSHA256: String
    public let contentSHA256: String
    public var grantsNativeAuthority: Bool { false }

    public init(preservationReference: AnyNativeImportedContextReference,
                preservation: AnyHeartNativeSourcePreservation,
                checkpoint: AnyDestinationSavedCheckpoint) throws {
        let exactPreservation = try AnyNativeImportedContextReference(
            networkID: preservationReference.destinationNetworkID, preservation: preservation,
            checkpoint: checkpoint,
            supplementalCanonicalDefinitions: preservationReference.supplementalCanonicalDefinitions)
        let plan = checkpoint.plan
        guard try exactPreservation.encoded() == preservationReference.encoded(),
              checkpoint.intents.count == plan.items.count,
              checkpoint.mappings.count == plan.items.count,
              checkpoint.checkpointSHA256 == preservationReference.checkpointSHA256 else {
            throw AnyNativeImportedContentContextError.invalidReference
        }
        // ff103's preservationPlan contains current.items + added, sorted by
        // the original phases. Project by the exact source keys, retaining the
        // original whole-plan binding and receipts; never rebind native intents.
        let current = preservation.currentContent
        _ = try current.currentContentPlan(workspace: plan.binding.workspace,
            storeID: plan.binding.storeID, planID: plan.binding.planID)
        let keys = Set(current.items.map { Data($0.sourceKey.utf8) })
        let projection = plan.items.filter { keys.contains(Data($0.sourceKey.utf8)) }
        guard keys.count == current.items.count,
              projection.count == current.items.count,
              try AnyDestinationMigrationJournal.encoded(projection) ==
                AnyDestinationMigrationJournal.encoded(current.items) else {
            throw AnyNativeImportedContentContextError.invalidReference
        }
        contract = Self.version; checkpointScope = "completed-preservation-current-content"
        preservationReferenceSHA256 = AnyContentDigest.sha256(try preservationReference.encoded())
        contentPlanID = plan.binding.planID; contentPlanSHA256 = plan.binding.planSHA256
        contentCheckpointSHA256 = checkpoint.checkpointSHA256; contentSHA256 = current.contentSHA256
        try validate()
    }

    public func binding(preservation: AnyNativeImportedContextReference) throws -> AnyPreparedMigrationPlanBinding {
        try validate()
        guard AnyContentDigest.sha256(try preservation.encoded()) == preservationReferenceSHA256,
              Self.same(contentPlanID, preservation.planID),
              contentPlanSHA256 == preservation.planSHA256,
              contentCheckpointSHA256 == preservation.checkpointSHA256 else {
            throw AnyNativeImportedContentContextError.invalidReference
        }
        return try .init(workspace: preservation.binding.workspace, storeID: preservation.storeID,
                         planID: contentPlanID, planSHA256: contentPlanSHA256)
    }

    public func encoded() throws -> Data {
        try validate()
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(self)
        guard bytes.count <= Self.maximumBytes else { throw AnyEngineError.readLimit }
        return bytes
    }

    public static func decode(_ bytes: Data) throws -> Self {
        guard !bytes.isEmpty, bytes.count <= maximumBytes else { throw AnyEngineError.readLimit }
        let value = try JSONDecoder().decode(Self.self, from: bytes)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: value.encoded())
        return value
    }

    private func validate() throws {
        guard Self.same(contract, Self.version),
              Self.same(checkpointScope, "completed-preservation-current-content"),
              [preservationReferenceSHA256, contentPlanID, contentPlanSHA256,
               contentCheckpointSHA256, contentSHA256].allSatisfy(AnyDestinationPlanChecks.digest) else {
            throw AnyNativeImportedContentContextError.invalidReference
        }
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case contract, checkpointScope, preservationReferenceSHA256, contentPlanID, contentPlanSHA256
        case contentCheckpointSHA256, contentSHA256
    }

    public init(from decoder: any Decoder) throws {
        let all = try decoder.container(keyedBy: AnyImportedContentCodingKey.self)
        guard Set(all.allKeys.map(\.stringValue)) == Set(CodingKeys.allCases.map(\.rawValue)) else {
            throw AnyNativeImportedContentContextError.invalidReference
        }
        let c = try decoder.container(keyedBy: CodingKeys.self)
        contract = try c.decode(String.self, forKey: .contract)
        checkpointScope = try c.decode(String.self, forKey: .checkpointScope)
        preservationReferenceSHA256 = try c.decode(String.self, forKey: .preservationReferenceSHA256)
        contentPlanID = try c.decode(String.self, forKey: .contentPlanID)
        contentPlanSHA256 = try c.decode(String.self, forKey: .contentPlanSHA256)
        contentCheckpointSHA256 = try c.decode(String.self, forKey: .contentCheckpointSHA256)
        contentSHA256 = try c.decode(String.self, forKey: .contentSHA256)
        try validate()
    }

    static func same(_ a: String, _ b: String) -> Bool { Data(a.utf8) == Data(b.utf8) }
    static func sameWorkspace(_ a: AnyTorahWorkspace, _ b: AnyTorahWorkspace) -> Bool {
        same(a.accountID, b.accountID) && same(a.spaceID, b.spaceID)
    }
}

/// This address comes from the completed content plan's exact object operation.
/// It is never a catalog carrier, title search, Type alias or caller-selected ID.
/// Current existence, Type and native receipts are checked by withDocument.
public struct AnyNativeImportedDocumentEntry: Sendable {
    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let sourceTypeObjectID: String
    public let sourceSnapshotSHA256: String
    public let sourceJSONViewSHA256: String
    public let sourceKey: String
    public let objectID: String
    public let nativeTypeID: String
    public let creationIntentID: String
    public var grantsNativeAuthority: Bool { false }
    let intent: AnyPreparedMigrationIntent
    let mapping: AnyDestinationMigrationMapping

    /// Identity checks on a read response. The caller still owns current native
    /// READ and run/lease admission; parsing this value grants no authority.
    func requireCurrentObject(_ response: AnyJSON) throws {
        let record = try AnyDestinationMigrationVerifier.objectRecord(
            response, id: objectID, spaceID: intent.binding.workspace.spaceID)
        guard record["any"]?["type"]?.string.map({ Data($0.utf8) }) == Data(nativeTypeID.utf8) else {
            throw AnyNativeImportedContentContextError.changedDocument(objectID)
        }
    }

    func requireCurrentReceipt(_ receipt: AnyPreparedMigrationReceipt) throws {
        // Editable content may differ from its original values. Its immutable
        // creation identity must still exist; deletion/obsolescence refuse.
        guard receipt.stage == .complete,
              receipt.outcome == .committed || receipt.outcome == .committedModified,
              receipt.intent.intentID == creationIntentID,
              receipt.intent.specBytes == intent.specBytes,
              AnyNativeImportedContextReference.sameBinding(receipt.intent.binding, intent.binding),
              receipt.fingerprint == mapping.fingerprint,
              receipt.objectID.map({ Data($0.utf8) }) == Data(objectID.utf8),
              receipt.recordIDs.map({ Data($0.utf8) }) == [Data(objectID.utf8)],
              let expectedChange = mapping.signedChangeIDs.last,
              receipt.changeID.map({ Data($0.utf8) }) == Data(expectedChange.utf8) else {
            throw AnyNativeImportedContentContextError.changedDocument(objectID)
        }
    }
}

/// The editable routing context is separate from the immutable catalog context.
/// All source definitions remain represented; only definitions actually present
/// in this completed plan have native addresses. Unsupported Types stay nil.
public struct AnyNativeImportedContentContext: Sendable {
    public let reference: AnyNativeImportedContentContextReference
    public let savedPlan: AnyDestinationMigrationPlan
    public let mappings: [AnyDestinationMigrationMapping]
    public let definitionDirectory: AnyNativeImportedDefinitionDirectory
    public let sourceFactsDirectory: AnyNativeImportedSourceFactsDirectory
    public let typeReferences: AnyHeartNativeTypeReferencePlan
    public let documents: [AnyNativeImportedDocumentEntry]
    public var permitsMigrationReplay: Bool { false }
    public var qualifiesWholeSourceBehavior: Bool { false }
    public var provesCurrentNativeState: Bool { false }
    private let byDestination: [Data: Int]
    private let bySource: [Data: Int]

    init(reference: AnyNativeImportedContentContextReference,
         preservationReference: AnyNativeImportedContextReference,
         preservation: AnyHeartNativeSourcePreservation,
         checkpoint: AnyDestinationSavedCheckpoint,
         catalog: AnyHeartNativeDefinitionCatalog,
         catalogCarrierObjectIDs: [String]) throws {
        let expected = try AnyNativeImportedContentContextReference(
            preservationReference: preservationReference, preservation: preservation, checkpoint: checkpoint)
        let composition = preservation.currentContent
        guard try reference.encoded() == expected.encoded(),
              checkpoint.intents.count == checkpoint.plan.items.count,
              checkpoint.mappings.count == checkpoint.plan.items.count else {
            throw AnyNativeImportedContentContextError.changedContentCheckpoint
        }
        let plan = checkpoint.plan, mappings = checkpoint.mappings
        let base = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: mappings)
        var supplements: [AnyDestinationCanonicalPropertyBinding] = []
        for binding in preservationReference.supplementalCanonicalDefinitions {
            try binding.validate()
            let evidence = binding.evidence
            if let present = base.definition(sourceObjectID: evidence.sourceObjectID) {
                guard present.canonical,
                      present.address == .property(ownerKind: .type,
                        key: try .init(ownerID: binding.ownerID, propertyID: binding.propertyID)),
                      Self.same(present.sourceUniqueKey, evidence.snapshot.uniqueKey),
                      present.sourceSnapshotSHA256 == evidence.snapshotSHA256,
                      present.sourceJSONViewSHA256 == evidence.viewSHA256 else {
                    throw AnyNativeImportedContentContextError.changedContentCheckpoint
                }
            } else { supplements.append(binding) }
        }
        let definitions = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: mappings,
            supplementalCanonicalDefinitions: supplements)
        let sourceFacts = try AnyNativeImportedSourceFactsDirectory(plan: plan, mappings: mappings)
        let references = try AnyHeartNativeTypeReferencePlan(catalog: catalog, directory: definitions)
        let documents = try Self.documentEntries(plan: plan, mappings: mappings,
            composition: composition, definitions: definitions, sourceFacts: sourceFacts,
            catalogCarrierObjectIDs: catalogCarrierObjectIDs)
        var bySource: [Data: Int] = [:], byDestination: [Data: Int] = [:]
        for (index, entry) in documents.enumerated() {
            guard bySource.updateValue(index, forKey: Data(entry.sourceObjectID.utf8)) == nil,
                  byDestination.updateValue(index, forKey: Data(entry.objectID.utf8)) == nil else {
                throw AnyNativeImportedContentContextError.changedContentCheckpoint
            }
        }
        self.reference = reference; savedPlan = plan; self.mappings = mappings
        definitionDirectory = definitions; sourceFactsDirectory = sourceFacts; typeReferences = references
        self.documents = documents; self.bySource = bySource; self.byDestination = byDestination
        try Task.checkCancellation()
    }

    /// Shared pure correspondence used by the owner and focused source controls.
    /// It proves routing from exact plan operations, never current native access.
    static func documentEntries(
        plan: AnyDestinationMigrationPlan, mappings: [AnyDestinationMigrationMapping],
        composition: AnyHeartNativeContentComposition,
        definitions: AnyNativeImportedDefinitionDirectory,
        sourceFacts: AnyNativeImportedSourceFactsDirectory,
        catalogCarrierObjectIDs: [String]
    ) throws -> [AnyNativeImportedDocumentEntry] {
        let keys = Set(composition.items.map { Data($0.sourceKey.utf8) })
        let projection = plan.items.filter { keys.contains(Data($0.sourceKey.utf8)) }
        guard mappings.count == plan.items.count, keys.count == composition.items.count,
              Self.same(plan.source.accountID, composition.bundle.sourceAccountID),
              Self.same(plan.source.spaceID, composition.bundle.sourceSpaceID),
              plan.source.captureManifestSHA256 == composition.bundle.manifestSHA256,
              plan.source.witnessSHA256 == composition.bundle.sourceWitnessSHA256,
              plan.source.definitionManifestBytes == composition.bundle.manifestBytes,
              AnyNativeImportedContextReference.sameBinding(plan.binding, definitions.binding),
              AnyNativeImportedContextReference.sameBinding(plan.binding, sourceFacts.binding),
              try AnyDestinationMigrationJournal.encoded(projection) ==
                AnyDestinationMigrationJournal.encoded(composition.items) else {
            throw AnyNativeImportedContentContextError.changedContentCheckpoint
        }
        var keyed: [Data: AnyDestinationMigrationMapping] = [:]
        for mapping in mappings {
            guard keyed.updateValue(mapping, forKey: Data(mapping.sourceKey.utf8)) == nil else {
                throw AnyNativeImportedContentContextError.changedContentCheckpoint
            }
        }
        let immutableMappings = keyed
        let carriers = Set(catalogCarrierObjectIDs.map { Data($0.utf8) })
        var documents: [AnyNativeImportedDocumentEntry] = []
        var bySource: [Data: Int] = [:], byDestination: [Data: Int] = [:]
        for selected in composition.selection.objects {
            try Task.checkCancellation()
            let sourceKey = AnyHeartNativePageComposition.objectSourceKey(
                spaceID: plan.source.spaceID, objectID: selected.sourceObjectID)
            let indexes = plan.items.indices.filter { Self.same(plan.items[$0].sourceKey, sourceKey) }
            guard indexes.count == 1, let index = indexes.first,
                  Self.same(plan.items[index].sourceObjectID, selected.sourceObjectID),
                  plan.items[index].operation.kind == "object" else {
                throw AnyNativeImportedContentContextError.changedContentCheckpoint
            }
            let operation = try plan.items[index].operation.resolved(
                destinationSpaceID: plan.binding.workspace.spaceID) {
                try AnyDestinationMigrationVerifier.resolve($0, in: immutableMappings,
                    destinationSpaceID: plan.binding.workspace.spaceID)
            }
            guard case .object(.native(let typeID), let collections, .literal(let initial)) = operation,
                  let type = definitions.definition(sourceObjectID: selected.typeObjectID),
                  type.address == .type(objectID: typeID),
                  let facts = sourceFacts.entry(sourceObjectID: selected.sourceObjectID) else {
                throw AnyNativeImportedContentContextError.changedContentCheckpoint
            }
            let intent = try AnyPreparedMigrationIntent.object(binding: plan.binding, sourceKey: sourceKey,
                typeID: typeID, collections: collections.map(AnyDestinationMigrationVerifier.native),
                initialProperties: initial)
            let mapping = mappings[index]
            guard Self.same(mapping.sourceKey, sourceKey),
                  Self.same(mapping.sourceObjectID, selected.sourceObjectID),
                  Self.same(mapping.intentID, intent.intentID),
                  mapping.kind == "object", mapping.fileID == nil,
                  mapping.recordIDs.map({ Data($0.utf8) }) == [Data(mapping.objectID.utf8)],
                  Self.same(facts.objectID, mapping.objectID), Self.same(facts.ownerTypeID, typeID),
                  facts.sourceSnapshotSHA256 == selected.snapshotSHA256,
                  facts.sourceJSONViewSHA256 == selected.jsonViewSHA256,
                  !carriers.contains(Data(mapping.objectID.utf8)),
                  bySource[Data(selected.sourceObjectID.utf8)] == nil,
                  byDestination[Data(mapping.objectID.utf8)] == nil else {
                throw AnyNativeImportedContentContextError.changedContentCheckpoint
            }
            bySource[Data(selected.sourceObjectID.utf8)] = documents.count
            byDestination[Data(mapping.objectID.utf8)] = documents.count
            documents.append(.init(sourceSpaceID: plan.source.spaceID,
                sourceObjectID: selected.sourceObjectID, sourceTypeObjectID: selected.typeObjectID,
                sourceSnapshotSHA256: selected.snapshotSHA256, sourceJSONViewSHA256: selected.jsonViewSHA256,
                sourceKey: sourceKey, objectID: mapping.objectID, nativeTypeID: typeID,
                creationIntentID: intent.intentID, intent: intent, mapping: mapping))
        }
        guard !documents.isEmpty,
              Set(sourceFacts.entries.map { Data($0.sourceObjectID.utf8) }) == Set(bySource.keys),
              documents.count == composition.selection.objects.count else {
            throw AnyNativeImportedContentContextError.changedContentCheckpoint
        }
        return documents
    }

    public func document(destinationObjectID: String) -> AnyNativeImportedDocumentEntry? {
        byDestination[Data(destinationObjectID.utf8)].map { documents[$0] }
    }

    public func document(sourceObjectID: String) -> AnyNativeImportedDocumentEntry? {
        bySource[Data(sourceObjectID.utf8)].map { documents[$0] }
    }

    private static func same(_ a: String, _ b: String) -> Bool {
        AnyNativeImportedContentContextReference.same(a, b)
    }
}

private struct AnyImportedContentCodingKey: CodingKey {
    let stringValue: String
    var intValue: Int? { nil }
    init?(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { return nil }
}
