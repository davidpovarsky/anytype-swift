import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativeImportedSourceFactsError: Error, Equatable, Sendable {
    case invalidMappings
    case invalidSource(String)
    case missingSource(String)
    case changedNativeRecord(String)
    case changedDuringRead(String)
}

/// An original Heart value, retained separately from the destination's native
/// derived property. Resolving its schema never restamps the original value.
public struct AnyNativeImportedHistoricalValue: Sendable {
    public let sourceRelationKey: String
    public let destinationPropertyID: String
    public let originalValue: AnyJSON
}

public struct AnyNativeImportedSourceFactsValue: Sendable {
    public let snapshot: AnyHeartNativeSnapshotView
    public let historicalValues: [AnyNativeImportedHistoricalValue]
    public let originalBindingJSON: Data
    public var originalHistoryReconstructed: Bool { false }

    static let ordinaryFields: Set<String> = ["sourceObject", "sourceSnapshotBase64", "sourceViewJSON",
        "sourceSnapshotSHA256", "sourceViewSHA256", "sourceDerivedBindingsJSON"]

    init(values: [String: AnyJSON], source: AnyDestinationSourceBinding, sourceObjectID: String) throws {
        guard Set(values.keys) == Self.ordinaryFields,
              values.values.allSatisfy({ $0.string != nil }),
              values["sourceObject"]?.string.map({ Data($0.utf8) }) == Data(sourceObjectID.utf8),
              let encoded = values["sourceSnapshotBase64"]?.string,
              let protobuf = Data(base64Encoded: encoded), protobuf.base64EncodedString() == encoded,
              let view = values["sourceViewJSON"]?.string,
              let binding = values["sourceDerivedBindingsJSON"]?.string else {
            throw AnyNativeImportedSourceFactsError.invalidSource(sourceObjectID)
        }
        let evidence = try AnyDestinationDefinitionEvidence(sourceSpaceID: source.spaceID,
            sourceObjectID: sourceObjectID, protobufBytes: protobuf, jsonViewBytes: Data(view.utf8))
        try evidence.requireSource(source, objectID: sourceObjectID)
        guard values["sourceSnapshotSHA256"] == .string(evidence.snapshotSHA256),
              values["sourceViewSHA256"] == .string(evidence.viewSHA256) else {
            throw AnyNativeImportedSourceFactsError.invalidSource(sourceObjectID)
        }
        let bindingBytes = Data(binding.utf8)
        guard bindingBytes.count <= 1_048_576 else { throw AnyEngineError.readLimit }
        let native = try JSONDecoder().decode(AnyJSON.self, from: bindingBytes)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bindingBytes,
            encoded: AnyDestinationDefinitionChecks.bytes(native))
        guard Set(native.object?.keys.map { $0 } ?? []) == ["contract", "historicalValues", "historicalAuthorIsDestinationSigner"],
              native["contract"] == .string(AnyHeartNativeSourceFacts.contract),
              native["historicalAuthorIsDestinationSigner"] == .bool(false),
              let values = native["historicalValues"]?.array, values.count <= 4 else {
            throw AnyNativeImportedSourceFactsError.invalidSource(sourceObjectID)
        }
        var seen = Set<Data>(), historical: [AnyNativeImportedHistoricalValue] = []
        for value in values {
            guard Set(value.object?.keys.map { $0 } ?? []) == ["sourceRelationKey", "nativePropertyID", "originalValue"],
                  let sourceKey = value["sourceRelationKey"]?.string,
                  let nativeID = value["nativePropertyID"]?.string,
                  let role = AnyDestinationCanonicalPropertyBinding.DerivedRole(rawValue: nativeID),
                  Data(sourceKey.utf8) == Data(role.sourceKey.utf8),
                  seen.insert(Data(sourceKey.utf8)).inserted,
                  let original = value["originalValue"], let captured = evidence.snapshot.details[sourceKey],
                  try AnyDestinationDefinitionChecks.bytes(original) == AnyDestinationDefinitionChecks.bytes(captured) else {
                throw AnyNativeImportedSourceFactsError.invalidSource(sourceObjectID)
            }
            historical.append(.init(sourceRelationKey: sourceKey, destinationPropertyID: nativeID, originalValue: original))
        }
        let derivedRoles: [AnyDestinationCanonicalPropertyBinding.DerivedRole] = [.author, .createdAt, .modifiedAt, .modifiedBy]
        let capturedKeys = Set(derivedRoles.filter { evidence.snapshot.details[$0.sourceKey] != nil }
            .map { Data($0.sourceKey.utf8) })
        guard seen == capturedKeys else { throw AnyNativeImportedSourceFactsError.invalidSource(sourceObjectID) }
        snapshot = evidence.snapshot; historicalValues = historical; originalBindingJSON = bindingBytes
    }
}

public struct AnyNativeImportedSourceFactsEntry: Sendable {
    public let sourceObjectID: String
    public let objectID: String
    public let ownerTypeID: String
    public let dataset: String
    public let recordID: String
    public let sourceSnapshotSHA256: String
    public let sourceJSONViewSHA256: String
    public var permitsDestinationWrites: Bool { false }
    let sourceKey: String
    let values: [String: AnyJSON]
    let mapping: AnyDestinationMigrationMapping
}

/// Exact source-to-native addresses for the already imported source-fact
/// records. A saved mapping is a routing hint; the store rechecks its native
/// immutable intent, current row and signed creation on every ordinary read.
public struct AnyNativeImportedSourceFactsDirectory: Sendable {
    public let binding: AnyPreparedMigrationPlanBinding
    public let source: AnyDestinationSourceBinding
    public let entries: [AnyNativeImportedSourceFactsEntry]
    public var permitsSourceAdmission: Bool { false }
    private let bySource: [Data: AnyNativeImportedSourceFactsEntry]

    public init(plan: AnyDestinationMigrationPlan, mappings: [AnyDestinationMigrationMapping]) throws {
        guard mappings.count == plan.items.count, !plan.source.definitionMembers.isEmpty else {
            throw AnyNativeImportedSourceFactsError.invalidMappings
        }
        var keyed: [Data: AnyDestinationMigrationMapping] = [:]
        for (item, mapping) in zip(plan.items, mappings) {
            guard Data(item.sourceKey.utf8) == Data(mapping.sourceKey.utf8),
                  Data(item.sourceObjectID.utf8) == Data(mapping.sourceObjectID.utf8),
                  item.operation.kind == mapping.kind,
                  mapping.recordIDs.count == item.expectedRecordCount,
                  AnyEditorBlock.validID(mapping.objectID), mapping.recordIDs.allSatisfy(AnyEditorBlock.validID),
                  Set(mapping.recordIDs.map { Data($0.utf8) }).count == mapping.recordIDs.count,
                  [mapping.intentID, mapping.fingerprint, mapping.currentReceiptSHA256].allSatisfy(AnyDestinationPlanChecks.digest),
                  !mapping.signedChangeIDs.isEmpty, mapping.signedChangeIDs.allSatisfy(AnyEditorBlock.validID),
                  Set(mapping.signedChangeIDs.map { Data($0.utf8) }).count == mapping.signedChangeIDs.count,
                  keyed.updateValue(mapping, forKey: Data(item.sourceKey.utf8)) == nil else {
                throw AnyNativeImportedSourceFactsError.invalidMappings
            }
        }
        let immutableMappings = keyed
        let resolved = try plan.items.map { item in
            try item.operation.resolved(destinationSpaceID: plan.binding.workspace.spaceID) {
                try AnyDestinationMigrationVerifier.resolve($0, in: immutableMappings,
                    destinationSpaceID: plan.binding.workspace.spaceID)
            }
        }
        var entries: [Data: AnyNativeImportedSourceFactsEntry] = [:], addresses = Set<Data>()
        for (index, operation) in resolved.enumerated() {
            guard case .immutableRecord(.native(let object), .native(let owner), let key, .literal(let raw)) = operation,
                  key == AnyHeartNativeSourceFacts.datasetKey else { continue }
            let item = plan.items[index], mapping = mappings[index]
            guard let values = raw.object, mapping.recordIDs.count == 1, mapping.signedChangeIDs.count == 1,
                  mapping.fileID == nil, Data(mapping.objectID.utf8) == Data(object.utf8) else {
                throw AnyNativeImportedSourceFactsError.invalidMappings
            }
            try AnyDestinationImmutableRecordChecks.requireOwnedDeclaration(items: plan.items,
                ownerType: Self.originalOwner(item.operation), datasetKey: key, values: .literal(raw))
            let original = try AnyNativeImportedSourceFactsValue(values: values, source: plan.source,
                sourceObjectID: item.sourceObjectID)
            let dataset = try AnyPreparedImmutableRecordIntent.ownedDataset(ownerTypeID: owner, key: key)
            let address = AnyPreparedMigrationPlanBinding.material([object, dataset])
            guard addresses.insert(address).inserted else { throw AnyNativeImportedSourceFactsError.invalidMappings }
            let entry = AnyNativeImportedSourceFactsEntry(sourceObjectID: item.sourceObjectID, objectID: object,
                ownerTypeID: owner, dataset: dataset, recordID: mapping.recordIDs[0],
                sourceSnapshotSHA256: original.snapshot.snapshotSHA256, sourceJSONViewSHA256: original.snapshot.viewSHA256,
                sourceKey: item.sourceKey, values: values, mapping: mapping)
            guard entries.updateValue(entry, forKey: Data(item.sourceObjectID.utf8)) == nil else {
                throw AnyNativeImportedSourceFactsError.invalidMappings
            }
        }
        self.binding = plan.binding; source = plan.source; bySource = entries
        self.entries = entries.values.sorted { Data($0.sourceObjectID.utf8).lexicographicallyPrecedes(Data($1.sourceObjectID.utf8)) }
    }

    public func entry(sourceObjectID: String) -> AnyNativeImportedSourceFactsEntry? { bySource[Data(sourceObjectID.utf8)] }

    private static func originalOwner(_ operation: AnyDestinationMigrationOperation) throws -> AnyDestinationReference {
        guard case .immutableRecord(_, let owner, _, _) = operation else { throw AnyNativeImportedSourceFactsError.invalidMappings }
        return owner
    }
}

/// This describes the destination import event, not original Heart authorship.
public struct AnyNativeImportedSourceFactsCreation: Sendable {
    public let changeID: String
    public let destinationAuthor: String
    public let destinationAuthorClockSeconds: Int64
}

public struct AnyNativeImportedSourceFactsSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let sourceAccountID: String
    public let sourceWitnessSHA256: String
    public let sourceManifestSHA256: String
    public let entry: AnyNativeImportedSourceFactsEntry
    /// Parsed from the current native immutable row after byte-for-byte
    /// comparison with the original capture and signed destination creation.
    public let original: AnyNativeImportedSourceFactsValue
    public let creation: AnyNativeImportedSourceFactsCreation
    public let raw: AnyJSON
    public var permitsDestinationWrites: Bool { false }
    public var originalHistoryReconstructed: Bool { false }
}

/// Ordinary native reads of preserved structured Heart metadata, blocks and
/// hierarchy. Their original IDs and unknown fields stay in the captured view.
/// They are not current edited destination blocks or reconstructed Heart DAGs.
/// Two equal row reads and current intent checks bound a local observation;
/// they do not establish a whole-Space transaction or peer delivery barrier.
public struct AnyNativeImportedSourceFactsStore: Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard Data(client.expectedAccountID.utf8) == Data(workspace.accountID.utf8) else { throw AnyHostError.wrongWorkspace }
        self.client = client; self.workspace = workspace
    }

    public func read(sourceObjectID: String, directory: AnyNativeImportedSourceFactsDirectory,
                     lease: AnyHostLease) async throws -> AnyNativeImportedSourceFactsSnapshot {
        guard Data(directory.binding.workspace.accountID.utf8) == Data(workspace.accountID.utf8),
              Data(directory.binding.workspace.spaceID.utf8) == Data(workspace.spaceID.utf8),
              Data(lease.workspace.accountID.utf8) == Data(workspace.accountID.utf8),
              Data(lease.workspace.spaceID.utf8) == Data(workspace.spaceID.utf8) else { throw AnyHostError.wrongWorkspace }
        try await lease.validate()
        guard let entry = directory.entry(sourceObjectID: sourceObjectID) else {
            throw AnyNativeImportedSourceFactsError.missingSource(sourceObjectID)
        }
        try await requireReadMembership(lease)
        let reader = try await AnyNativePreparedImmutableRecord.open(client: client, workspace: workspace,
            authorize: { try await lease.validate() })
        let schema = try await reader.schema(ownerTypeID: entry.ownerTypeID, dataset: entry.dataset,
            authorize: { try await lease.validate() })
        try Self.requireSourceFactSchema(schema)
        let intent = try AnyPreparedImmutableRecordIntent(binding: directory.binding, sourceKey: entry.sourceKey,
            objectID: entry.objectID, schema: schema, values: entry.values)
        guard intent.intentID == entry.mapping.intentID else { throw AnyNativeImportedSourceFactsError.invalidMappings }
        let before = try await reader.status(intent, authorize: { try await lease.validate() })
        try Self.requireReceipt(before, entry: entry)
        let first = try await currentRow(entry, lease: lease)
        let authority = try await signedCreation(entry, intent: intent, lease: lease)
        let observed = try AnyDestinationMigrationVerifier.immutableRecordProjection(first, intent: intent, authority: authority)
        let historical = try AnyDestinationMigrationVerifier.immutableRecordProjection(authority.recordAtChange, intent: intent, authority: authority)
        guard try AnyDestinationDefinitionChecks.bytes(observed) == AnyDestinationDefinitionChecks.bytes(historical) else {
            throw AnyNativeImportedSourceFactsError.changedNativeRecord(sourceObjectID)
        }
        let second = try await currentRow(entry, lease: lease)
        guard try AnyDestinationDefinitionChecks.bytes(first) == AnyDestinationDefinitionChecks.bytes(second) else {
            throw AnyNativeImportedSourceFactsError.changedDuringRead(sourceObjectID)
        }
        let after = try await reader.status(intent, authorize: { try await lease.validate() })
        try Self.requireReceipt(after, entry: entry)
        guard before == after, let values = observed["values"]?.object else {
            throw AnyNativeImportedSourceFactsError.changedDuringRead(sourceObjectID)
        }
        let original = try AnyNativeImportedSourceFactsValue(values: values, source: directory.source,
            sourceObjectID: sourceObjectID)
        try await requireReadMembership(lease)
        try await lease.validate()
        return .init(workspace: workspace, generation: lease.generation, engineStartedAt: lease.engineStartedAt,
            sourceAccountID: directory.source.accountID, sourceWitnessSHA256: directory.source.witnessSHA256,
            sourceManifestSHA256: directory.source.captureManifestSHA256, entry: entry, original: original,
            creation: .init(changeID: authority.changeID, destinationAuthor: authority.author,
                destinationAuthorClockSeconds: authority.timestampSeconds), raw: first)
    }

    private func request(_ suffix: [String], body: AnyJSON? = nil, query: [String: String] = [:],
                         lease: AnyHostLease) async throws -> AnyJSON {
        try await lease.validate()
        // POST is used only by the native read-only query endpoint. Its
        // authorization callback is a repeatable lease check, never a writer.
        let value = try await client.requestJSON(method: body == nil ? "GET" : "POST",
            path: ["v1", "spaces", workspace.spaceID] + suffix, body: body, query: query,
            maximumResponseBytes: 4 * 1024 * 1024, authorize: { try await lease.validate() })
        try await lease.validate()
        return value
    }

    private func requireReadMembership(_ lease: AnyHostLease) async throws {
        let value = try await request(["members", "me"], lease: lease)
        guard value["identity"]?.string.map({ Data($0.utf8) }) == Data(workspace.accountID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        try AnyHTTPTorahTargetAccess.validateMember(value, workspace: workspace, intent: .read)
    }

    private func currentRow(_ entry: AnyNativeImportedSourceFactsEntry, lease: AnyHostLease) async throws -> AnyJSON {
        let value = try await request(["query"], body: .object([
            "objectId": .string(entry.objectID), "dataset": .string(entry.dataset),
            "sort": .array([.string("id")]), "limit": .integer(2), "offset": .integer(0), "includeTotal": .bool(true)
        ]), lease: lease)
        guard value["total"] == .integer(1), value["hasNext"] == .bool(false),
              let rows = value["records"]?.array, rows.count == 1,
              rows[0]["id"]?.string.map({ Data($0.utf8) }) == Data(entry.recordID.utf8) else {
            throw AnyNativeImportedSourceFactsError.changedNativeRecord(entry.sourceObjectID)
        }
        return rows[0]
    }

    private func signedCreation(_ entry: AnyNativeImportedSourceFactsEntry, intent: AnyPreparedImmutableRecordIntent,
                                lease: AnyHostLease) async throws -> AnyDestinationImmutableRecordAuthority {
        let changeID = entry.mapping.signedChangeIDs[0]
        var selected: AnyJSON?, cursor: String?, cursors = Set<Data>(), versions = Set<Data>()
        for page in 0..<64 {
            var query = ["dataset": entry.dataset, "recordId": entry.recordID, "coalesce": "false", "limit": "200"]
            if let cursor { query["cursor"] = cursor }
            let history = try await request(["objects", entry.objectID, "history"], query: query, lease: lease)
            guard let changes = history["changes"]?.array, changes.count <= 200,
                  history["cursor"] == nil || history["cursor"]?.string != nil else { throw AnyNativeHistoryError.malformedResponse }
            for value in changes {
                let change = try AnyNativeHistoryChange(native: value)
                guard versions.insert(Data(change.version.utf8)).inserted else { throw AnyNativeHistoryError.paginationChanged }
                if Data(change.version.utf8) == Data(changeID.utf8) { selected = value }
            }
            let next = history["cursor"]?.string ?? ""
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
        return try .init(change: selected, snapshot: snapshot, intent: intent, recordID: entry.recordID, expectedChangeID: changeID)
    }

    private static func requireReceipt(_ receipt: AnyPreparedImmutableRecordReceipt, entry: AnyNativeImportedSourceFactsEntry) throws {
        guard receipt.isCompleteAndCurrent, receipt.fingerprint == entry.mapping.fingerprint,
              Data(receipt.objectID.utf8) == Data(entry.objectID.utf8),
              receipt.recordIDs.map({ Data($0.utf8) }) == [Data(entry.recordID.utf8)],
              Data(receipt.changeID.utf8) == Data(entry.mapping.signedChangeIDs[0].utf8) else {
            throw AnyNativeImportedSourceFactsError.changedNativeRecord(entry.sourceObjectID)
        }
    }

    private static func requireSourceFactSchema(_ schema: AnyPreparedImmutableRecordSchema) throws {
        // The schema constructor already rejects non-string and duplicate
        // required entries; this check narrows that validated set to this part.
        let ordinary = AnyNativeImportedSourceFactsValue.ordinaryFields
        guard let fields = schema.declaration["properties"]?.object,
              Set(fields.keys) == ordinary.union(["importedBy", "importedAt"]),
              Set(schema.declaration["required"]?.array?.compactMap(\.string) ?? []) == ordinary,
              fields["importedBy"]?["x-stamp"] == .string("creator"),
              fields["importedAt"]?["x-stamp"] == .string("createTime"),
              ordinary.allSatisfy({ fields[$0]?["type"] == .string("string") }) else {
            throw AnyNativeImportedSourceFactsError.invalidSource("source-facts schema")
        }
    }
}
