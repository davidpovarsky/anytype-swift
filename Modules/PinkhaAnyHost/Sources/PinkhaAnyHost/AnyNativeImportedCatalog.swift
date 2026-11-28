import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativeImportedCatalogError: Error, Equatable, Sendable {
    case invalidOriginalPlan
    case missingHead(String)
    case snapshotNotCaptured(String)
    case changedSource(String)
}

/// The original immutable catalog record. Its address identifies retained
/// source data, never a replacement destination Type or writable property.
public struct AnyNativeImportedCatalogEntry: Sendable {
    public let sourceObjectID: String
    public let objectID: String
    public let ownerTypeID: String
    public let dataset: String
    public let recordID: String
    public let role: String
    public let nativeTypeText: String
    public let sourceUniqueKey: String
    public let definitionEvidenceKind: AnyHeartNativeDefinitionEvidence.Kind
    public let archiveURI: String
    /// nil means this source head has no captured object snapshot. Its exact
    /// retained row can still be inspected without inventing an empty object.
    public let evidence: AnyDestinationDefinitionEvidence?
    public let originalTreeJSON: Data
    public var permitsDestinationWrites: Bool { false }
    let sourceKey: String
    let values: [String: AnyJSON]
    let mapping: AnyDestinationMigrationMapping
}

/// Routes the complete original catalog from its already committed plan. No
/// original operation is prepared or replayed. Native reads subsequently bind
/// each address to the original immutable intent and signed creation.
public struct AnyNativeImportedCatalogDirectory: Sendable {
    public let binding: AnyPreparedMigrationPlanBinding
    public let source: AnyDestinationSourceBinding
    public let entries: [AnyNativeImportedCatalogEntry]
    public var permitsWholeSourceAdmission: Bool { false }
    private let byID: [Data: AnyNativeImportedCatalogEntry]

    public init(plan: AnyDestinationMigrationPlan, mappings: [AnyDestinationMigrationMapping]) throws {
        // These existing constructors validate complete mapping cardinality,
        // ordered source keys, signed IDs and every retained Page source fact.
        _ = try AnyNativeImportedDefinitionDirectory(plan: plan, mappings: mappings)
        _ = try AnyNativeImportedSourceFactsDirectory(plan: plan, mappings: mappings)
        guard !plan.source.definitionMembers.isEmpty else { throw AnyNativeImportedCatalogError.invalidOriginalPlan }
        var keyed: [Data: AnyDestinationMigrationMapping] = [:]
        for mapping in mappings {
            guard keyed.updateValue(mapping, forKey: Data(mapping.sourceKey.utf8)) == nil else {
                throw AnyNativeImportedCatalogError.invalidOriginalPlan
            }
        }
        let immutableMappings = keyed
        var catalog: [Data: AnyNativeImportedCatalogEntry] = [:], addresses = Set<Data>()
        for (index, item) in plan.items.enumerated() {
            let operation = try item.operation.resolved(destinationSpaceID: plan.binding.workspace.spaceID) {
                try AnyDestinationMigrationVerifier.resolve($0, in: immutableMappings,
                    destinationSpaceID: plan.binding.workspace.spaceID)
            }
            guard case .immutableRecord(.native(let object), .native(let owner), let key, .literal(let raw)) = operation,
                  key == AnyHeartNativeSourcePreservation.datasetKey else { continue }
            let mapping = mappings[index]
            guard let values = raw.object,
                  let definitionKind = AnyNativeImportedCatalogChecks.definitionKind(values),
                  mapping.recordIDs.count == 1, mapping.signedChangeIDs.count == 1, mapping.fileID == nil,
                  AnyNativeImportedCatalogChecks.same(mapping.objectID, object),
                  values["sourceHeadID"]?.string.map({ AnyNativeImportedCatalogChecks.same($0, item.sourceObjectID) }) == true,
                  values["sourceCaptureManifestSHA256"] == .string(plan.source.captureManifestSHA256),
                  let captured = values["snapshotPresent"]?.bool,
                  case .immutableRecord(_, let originalOwner, _, _) = item.operation else {
                throw AnyNativeImportedCatalogError.invalidOriginalPlan
            }
            try AnyDestinationImmutableRecordChecks.requireOwnedDeclaration(items: plan.items,
                ownerType: originalOwner, datasetKey: key, values: .literal(raw))
            let dataset = try AnyPreparedImmutableRecordIntent.ownedDataset(ownerTypeID: owner, key: key)
            let address = AnyPreparedMigrationPlanBinding.material([object, dataset, mapping.recordIDs[0]])
            guard addresses.insert(address).inserted else { throw AnyNativeImportedCatalogError.invalidOriginalPlan }
            let evidence = try AnyNativeImportedCatalogChecks.evidence(values, source: plan.source,
                sourceObjectID: item.sourceObjectID, captured: captured)
            let tree = Data(values["sourceTreeJSON"]!.string!.utf8)
            guard tree.count <= 262_144 else { throw AnyEngineError.readLimit }
            let parsedTree = try JSONDecoder().decode(AnyJSON.self, from: tree)
            try AnyTorahSourceJSONGuard.validateRoundTrip(original: tree,
                encoded: AnyDestinationDefinitionChecks.bytes(parsedTree))
            let entry = AnyNativeImportedCatalogEntry(sourceObjectID: item.sourceObjectID, objectID: object,
                ownerTypeID: owner, dataset: dataset, recordID: mapping.recordIDs[0],
                role: values["sourceRole"]!.string!, nativeTypeText: values["sourceNativeType"]!.string!,
                sourceUniqueKey: values["sourceUniqueKey"]!.string!, definitionEvidenceKind: definitionKind,
                archiveURI: values["archiveURI"]!.string!,
                evidence: evidence, originalTreeJSON: tree, sourceKey: item.sourceKey, values: values, mapping: mapping)
            guard catalog.updateValue(entry, forKey: Data(item.sourceObjectID.utf8)) == nil else {
                throw AnyNativeImportedCatalogError.invalidOriginalPlan
            }
        }
        guard Set(catalog.keys) == Set(plan.source.sourceObjectIDs.map({ Data($0.utf8) })),
              Set(catalog.values.filter({ $0.evidence != nil }).map({ Data($0.sourceObjectID.utf8) })) ==
                Set(plan.source.definitionMembers.keys) else {
            throw AnyNativeImportedCatalogError.invalidOriginalPlan
        }
        self.binding = plan.binding; self.source = plan.source; self.byID = catalog
        entries = catalog.values.sorted {
            Data($0.sourceObjectID.utf8).lexicographicallyPrecedes(Data($1.sourceObjectID.utf8))
        }
    }

    public func entry(sourceObjectID: String) -> AnyNativeImportedCatalogEntry? { byID[Data(sourceObjectID.utf8)] }
}

public struct AnyNativeImportedCatalogSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let sourceAccountID: String
    public let sourceWitnessSHA256: String
    public let sourceManifestSHA256: String
    public let entry: AnyNativeImportedCatalogEntry
    /// This is the destination import signer and clock, not source authorship.
    public let creation: AnyNativeImportedSourceFactsCreation
    public let raw: AnyJSON
    public var permitsDestinationWrites: Bool { false }
    public var originalHistoryReconstructed: Bool { false }
    public var provesCurrentSourceValues: Bool { false }
}

/// A read-only facade over the existing immutable records, history and native
/// membership APIs. It preserves all source snapshots/unknown fields and the
/// no-snapshot distinction. Equal reads bound one local observation; no atomic
/// whole-Space, source-history decryption or cross-peer barrier is asserted.
public struct AnyNativeImportedCatalogStore: Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard AnyNativeImportedCatalogChecks.same(client.expectedAccountID, workspace.accountID) else {
            throw AnyHostError.wrongWorkspace
        }
        self.client = client; self.workspace = workspace
    }

    public func read(sourceObjectID: String, directory: AnyNativeImportedCatalogDirectory,
                     lease: AnyHostLease) async throws -> AnyNativeImportedCatalogSnapshot {
        try await validate(directory, lease: lease)
        guard let entry = directory.entry(sourceObjectID: sourceObjectID) else {
            throw AnyNativeImportedCatalogError.missingHead(sourceObjectID)
        }
        try await membership(lease)
        let reader = try await AnyNativePreparedImmutableRecord.open(client: client, workspace: workspace,
            authorize: { try await lease.validate() })
        let schema = try await reader.schema(ownerTypeID: entry.ownerTypeID, dataset: entry.dataset,
            authorize: { try await lease.validate() })
        try AnyNativeImportedCatalogChecks.schema(schema, definitionEvidenceKind: entry.definitionEvidenceKind)
        let intent = try AnyPreparedImmutableRecordIntent(binding: directory.binding, sourceKey: entry.sourceKey,
            objectID: entry.objectID, schema: schema, values: entry.values)
        guard intent.intentID == entry.mapping.intentID else { throw AnyNativeImportedCatalogError.changedSource(sourceObjectID) }
        let before = try await reader.status(intent, authorize: { try await lease.validate() })
        try AnyNativeImportedCatalogChecks.receipt(before, entry: entry)
        let first = try await row(entry, lease: lease)
        let authority = try await creation(entry, intent: intent, lease: lease)
        let observed = try AnyDestinationMigrationVerifier.immutableRecordProjection(first, intent: intent, authority: authority)
        let original = try AnyDestinationMigrationVerifier.immutableRecordProjection(authority.recordAtChange,
            intent: intent, authority: authority)
        guard try AnyDestinationDefinitionChecks.bytes(observed) == AnyDestinationDefinitionChecks.bytes(original),
              let values = observed["values"]?.object,
              try AnyDestinationDefinitionChecks.bytes(.object(values)) == AnyDestinationDefinitionChecks.bytes(.object(entry.values)) else {
            throw AnyNativeImportedCatalogError.changedSource(sourceObjectID)
        }
        let second = try await row(entry, lease: lease)
        let after = try await reader.status(intent, authorize: { try await lease.validate() })
        try AnyNativeImportedCatalogChecks.receipt(after, entry: entry)
        guard before == after,
              try AnyDestinationDefinitionChecks.bytes(first) == AnyDestinationDefinitionChecks.bytes(second) else {
            throw AnyNativeImportedCatalogError.changedSource(sourceObjectID)
        }
        try await membership(lease)
        try await validate(directory, lease: lease)
        return .init(workspace: workspace, generation: lease.generation, engineStartedAt: lease.engineStartedAt,
            sourceAccountID: directory.source.accountID, sourceWitnessSHA256: directory.source.witnessSHA256,
            sourceManifestSHA256: directory.source.captureManifestSHA256, entry: entry,
            creation: .init(changeID: authority.changeID, destinationAuthor: authority.author,
                destinationAuthorClockSeconds: authority.timestampSeconds), raw: second)
    }

    private func validate(_ directory: AnyNativeImportedCatalogDirectory, lease: AnyHostLease) async throws {
        for candidate in [directory.binding.workspace, lease.workspace] {
            guard AnyNativeImportedCatalogChecks.same(candidate.accountID, workspace.accountID),
                  AnyNativeImportedCatalogChecks.same(candidate.spaceID, workspace.spaceID) else { throw AnyHostError.wrongWorkspace }
        }
        try await lease.validate()
        try Task.checkCancellation()
    }

    private func request(_ suffix: [String], body: AnyJSON? = nil, query: [String: String] = [:],
                         lease: AnyHostLease) async throws -> AnyJSON {
        try await lease.validate()
        // POST is used only for the existing read-only query endpoint.
        let value = try await client.requestJSON(method: body == nil ? "GET" : "POST",
            path: ["v1", "spaces", workspace.spaceID] + suffix, body: body, query: query,
            maximumResponseBytes: 4 * 1024 * 1024, authorize: { try await lease.validate() })
        try await lease.validate()
        return value
    }

    private func membership(_ lease: AnyHostLease) async throws {
        let value = try await request(["members", "me"], lease: lease)
        guard value["identity"]?.string.map({ AnyNativeImportedCatalogChecks.same($0, workspace.accountID) }) == true else {
            throw AnyHostError.wrongWorkspace
        }
        try AnyHTTPTorahTargetAccess.validateMember(value, workspace: workspace, intent: .read)
    }

    private func row(_ entry: AnyNativeImportedCatalogEntry, lease: AnyHostLease) async throws -> AnyJSON {
        let response = try await request(["query"], body: .object([
            "objectId": .string(entry.objectID), "dataset": .string(entry.dataset),
            "filter": .object(["id": .string(entry.recordID)]),
            "limit": .integer(2), "offset": .integer(0), "includeTotal": .bool(true)
        ]), lease: lease)
        guard response["total"] == .integer(1), response["hasNext"] == .bool(false),
              let rows = response["records"]?.array, rows.count == 1,
              rows[0]["id"]?.string.map({ AnyNativeImportedCatalogChecks.same($0, entry.recordID) }) == true else {
            throw AnyNativeImportedCatalogError.changedSource(entry.sourceObjectID)
        }
        return rows[0]
    }

    private func creation(_ entry: AnyNativeImportedCatalogEntry, intent: AnyPreparedImmutableRecordIntent,
                          lease: AnyHostLease) async throws -> AnyDestinationImmutableRecordAuthority {
        let changeID = entry.mapping.signedChangeIDs[0]
        var selected: AnyJSON?, cursor: String?, cursors = Set<Data>(), versions = Set<Data>()
        for page in 0..<64 {
            var query = ["dataset": entry.dataset, "recordId": entry.recordID, "coalesce": "false", "limit": "200"]
            if let cursor { query["cursor"] = cursor }
            let response = try await request(["objects", entry.objectID, "history"], query: query, lease: lease)
            guard let changes = response["changes"]?.array, changes.count <= 200,
                  response["cursor"] == nil || response["cursor"]?.string != nil else {
                throw AnyNativeHistoryError.malformedResponse
            }
            for value in changes {
                let change = try AnyNativeHistoryChange(native: value)
                guard versions.insert(Data(change.version.utf8)).inserted else { throw AnyNativeHistoryError.paginationChanged }
                if AnyNativeImportedCatalogChecks.same(change.version, changeID) { selected = value }
            }
            let next = response["cursor"]?.string ?? ""
            guard next.utf8.count <= 8192, !next.utf8.contains(0),
                  next.isEmpty || (!changes.isEmpty && cursors.insert(Data(next.utf8)).inserted) else {
                throw AnyNativeHistoryError.paginationChanged
            }
            if selected != nil || next.isEmpty { break }
            guard page < 63 else { throw AnyNativeHistoryError.paginationLimit }
            cursor = next
        }
        guard let selected else { throw AnyNativeHistoryError.versionNotFound }
        let snapshot = try await request(["objects", entry.objectID, "history", changeID,
            "datasets", entry.dataset, "records", entry.recordID], lease: lease)
        return try .init(change: selected, snapshot: snapshot, intent: intent,
            recordID: entry.recordID, expectedChangeID: changeID)
    }
}

enum AnyNativeImportedCatalogChecks {
    static let stringFields: Set<String> = ["sourceHeadID", "sourceRole", "sourceNativeType", "sourceUniqueKey",
        "sourceTreeJSON", "sourceSnapshotBase64", "sourceViewJSON", "sourceSnapshotSHA256",
        "sourceViewSHA256", "sourceCaptureManifestSHA256", "sourceRecoveryManifestSHA256", "archiveURI"]
    static let ordinaryFields = stringFields.union(["snapshotPresent"])
    static let capturedStringFields = stringFields.subtracting(["sourceRecoveryManifestSHA256"])
        .union(["sourceDefinitionEvidence"])
    static let capturedOrdinaryFields = capturedStringFields.union(["snapshotPresent"])

    /// Closed, disjoint catalog versions. A direct capture has no recovery SHA,
    /// including no empty/null placeholder or caller-created recovery receipt.
    static func definitionKind(_ values: [String: AnyJSON]) -> AnyHeartNativeDefinitionEvidence.Kind? {
        if Set(values.keys) == ordinaryFields,
           stringFields.allSatisfy({ values[$0]?.string != nil }),
           values["sourceRecoveryManifestSHA256"]?.string.map(AnyDestinationPlanChecks.digest) == true {
            return .recoveredOriginal
        }
        if Set(values.keys) == capturedOrdinaryFields,
           capturedStringFields.allSatisfy({ values[$0]?.string != nil }),
           values["sourceDefinitionEvidence"] == .string(AnyHeartNativeDefinitionEvidence.Kind.capturedComplete.rawValue) {
            return .capturedComplete
        }
        return nil
    }

    static func same(_ a: String, _ b: String) -> Bool { a.utf8.elementsEqual(b.utf8) }

    static func evidence(_ values: [String: AnyJSON], source: AnyDestinationSourceBinding,
                         sourceObjectID: String, captured: Bool) throws -> AnyDestinationDefinitionEvidence? {
        if !captured {
            guard source.definitionMembers[Data(sourceObjectID.utf8)] == nil,
                  ["sourceSnapshotBase64", "sourceViewJSON", "sourceSnapshotSHA256", "sourceViewSHA256", "sourceUniqueKey"]
                    .allSatisfy({ values[$0] == .string("") }) else {
                throw AnyNativeImportedCatalogError.changedSource(sourceObjectID)
            }
            return nil
        }
        guard let encoded = values["sourceSnapshotBase64"]?.string,
              let protobuf = Data(base64Encoded: encoded), protobuf.base64EncodedString() == encoded,
              let view = values["sourceViewJSON"]?.string else { throw AnyNativeImportedCatalogError.changedSource(sourceObjectID) }
        let evidence = try AnyDestinationDefinitionEvidence(sourceSpaceID: source.spaceID,
            sourceObjectID: sourceObjectID, protobufBytes: protobuf, jsonViewBytes: Data(view.utf8))
        try evidence.requireSource(source, objectID: sourceObjectID)
        guard values["sourceSnapshotSHA256"] == .string(evidence.snapshotSHA256),
              values["sourceViewSHA256"] == .string(evidence.viewSHA256),
              values["sourceNativeType"] == .string(String(evidence.snapshot.nativeType)),
              values["sourceUniqueKey"]?.string.map({ same($0, evidence.snapshot.uniqueKey) }) == true else {
            throw AnyNativeImportedCatalogError.changedSource(sourceObjectID)
        }
        return evidence
    }

    static func receipt(_ receipt: AnyPreparedImmutableRecordReceipt, entry: AnyNativeImportedCatalogEntry) throws {
        guard receipt.isCompleteAndCurrent, receipt.fingerprint == entry.mapping.fingerprint,
              same(receipt.objectID, entry.objectID), receipt.recordIDs.map({ Data($0.utf8) }) == [Data(entry.recordID.utf8)],
              same(receipt.changeID, entry.mapping.signedChangeIDs[0]) else {
            throw AnyNativeImportedCatalogError.changedSource(entry.sourceObjectID)
        }
    }

    static func schema(_ schema: AnyPreparedImmutableRecordSchema,
                       definitionEvidenceKind: AnyHeartNativeDefinitionEvidence.Kind = .recoveredOriginal) throws {
        let stringFields = definitionEvidenceKind == .recoveredOriginal ? Self.stringFields : capturedStringFields
        let ordinaryFields = definitionEvidenceKind == .recoveredOriginal ? Self.ordinaryFields : capturedOrdinaryFields
        guard let fields = schema.declaration["properties"]?.object,
              Set(fields.keys) == ordinaryFields.union(["importedBy", "importedAt"]),
              let required = schema.declaration["required"]?.array, required.count == ordinaryFields.count,
              required.allSatisfy({ $0.string != nil }), Set(required.compactMap(\.string)) == ordinaryFields,
              stringFields.allSatisfy({ fields[$0]?["type"] == .string("string") }),
              fields["snapshotPresent"]?["type"] == .string("boolean"),
              fields["importedBy"]?["x-stamp"] == .string("creator"),
              fields["importedAt"]?["x-stamp"] == .string("createTime") else {
            throw AnyNativeImportedCatalogError.invalidOriginalPlan
        }
    }
}
