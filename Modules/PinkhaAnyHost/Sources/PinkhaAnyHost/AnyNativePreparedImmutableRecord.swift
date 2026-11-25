import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// The authenticated native service owns this schema digest. It hashes its
/// normalized Go declaration, not a re-encoded Swift JSON dictionary. The exact
/// descriptor and digest are retained together and re-read before any write.
public struct AnyPreparedImmutableRecordSchema: Codable, Equatable, Sendable {
    public let ownerTypeID: String
    public let dataset: String
    public let nativeSHA256: String
    public let declaration: AnyJSON
    let response: AnyJSON

    init(_ value: AnyJSON, ownerTypeID: String, dataset: String) throws {
        guard Set(value.object?.keys.map { $0 } ?? []) == ["contract", "ownerTypeId", "dataset", "schemaSHA256", "schema"],
              value["contract"]?.string == AnyNativePreparedImmutableRecord.contract,
              value["ownerTypeId"]?.string.map({ Data($0.utf8) }) == Data(ownerTypeID.utf8),
              value["dataset"]?.string.map({ Data($0.utf8) }) == Data(dataset.utf8),
              AnyPreparedImmutableRecordIntent.validField(ownerTypeID),
              dataset.utf8.count <= 512, dataset.hasPrefix(ownerTypeID + "_"),
              let digest = value["schemaSHA256"]?.string, AnyNativeCreationIdentity.isHex(digest, count: 64),
              let declaration = value["schema"], let fields = declaration["properties"]?.object,
              !fields.isEmpty, fields.count <= AnyPreparedImmutableRecordIntent.maximumFields,
              declaration["type"] == .string("object"), declaration["additionalProperties"] == .bool(false),
              declaration["x-delete-by"] == .string("none"),
              declaration["x-id"] == nil || declaration["x-id"] == .string("auto"),
              Set(declaration.object?.keys.map { $0 } ?? []).isSubset(of: [
                "type", "properties", "required", "additionalProperties", "x-delete-by", "x-id", "x-search"
              ]) else { throw AnyPreparedMigrationError.unsupportedContract }
        let required = declaration["required"]?.array ?? []
        guard declaration["required"] == nil || declaration["required"]?.array != nil,
              required.allSatisfy({ $0.string != nil }),
              Set(required.compactMap(\.string)).count == required.count,
              Set(required.compactMap(\.string)).isSubset(of: Set(fields.keys)) else {
            throw AnyPreparedMigrationError.unsupportedContract
        }
        for (key, field) in fields {
            guard AnyPreparedImmutableRecordIntent.validField(key), field.object != nil,
                  field["x-mutable-by"] == nil || field["x-mutable-by"] == .string("never"),
                  field["x-additive"] == nil || field["x-additive"] == .bool(false),
                  field["x-stamp"] == nil || field["x-stamp"]?.string != nil else {
                throw AnyPreparedMigrationError.unsupportedContract
            }
            switch field["x-stamp"]?.string {
            case nil, "none":
                guard field["x-scope"] == .string("synced") else { throw AnyPreparedMigrationError.unsupportedContract }
            case "creator", "createTime":
                guard field["x-scope"] == .string("derived"), !required.contains(.string(key)) else {
                    throw AnyPreparedMigrationError.unsupportedContract
                }
            default: throw AnyPreparedMigrationError.unsupportedContract
            }
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        guard try encoder.encode(value).count <= 1_048_576 else { throw AnyPreparedMigrationError.unsupportedContract }
        self.ownerTypeID = ownerTypeID; self.dataset = dataset
        self.nativeSHA256 = digest; self.declaration = declaration; response = value
    }

    func validate(values: [String: AnyJSON]) throws {
        guard !values.isEmpty, values.count <= AnyPreparedImmutableRecordIntent.maximumFields,
              let fields = declaration["properties"]?.object else { throw AnyPreparedMigrationError.invalidBinding }
        let required = declaration["required"]?.array?.compactMap(\.string) ?? []
        guard required.allSatisfy({ values[$0] != nil }) else { throw AnyPreparedMigrationError.invalidBinding }
        for key in values.keys {
            guard AnyPreparedImmutableRecordIntent.validField(key), let field = fields[key],
                  field["x-scope"] == .string("synced"),
                  field["x-stamp"] == nil || field["x-stamp"] == .string("none") else {
                throw AnyPreparedMigrationError.invalidBinding
            }
        }
    }

    public init(from decoder: any Decoder) throws {
        let value = try decoder.singleValueContainer().decode(AnyJSON.self)
        guard let owner = value["ownerTypeId"]?.string, let dataset = value["dataset"]?.string else {
            throw AnyPreparedMigrationError.unsupportedContract
        }
        try self.init(value, ownerTypeID: owner, dataset: dataset)
    }
    public func encode(to encoder: any Encoder) throws {
        var container = encoder.singleValueContainer(); try container.encode(response)
    }
}

public struct AnyPreparedImmutableRecordIntent: Equatable, Sendable {
    public static let maximumFields = 128
    public let binding: AnyPreparedMigrationPlanBinding
    public let sourceKey: String
    public let objectID: String
    public let schema: AnyPreparedImmutableRecordSchema
    public let values: [String: AnyJSON]
    public let intentID: String
    public let specBytes: Data
    public let specSHA256: String

    public init(binding: AnyPreparedMigrationPlanBinding, sourceKey: String, objectID: String,
                schema: AnyPreparedImmutableRecordSchema, values: [String: AnyJSON]) throws {
        guard AnyPreparedMigrationPlanBinding.validOpaque(sourceKey, maximum: 4096),
              AnyEditorBlock.validID(objectID), objectID.utf8.count <= 256 else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        try schema.validate(values: values)
        let spec: AnyJSON = .object([
            "objectId": .string(objectID), "ownerTypeId": .string(schema.ownerTypeID),
            "dataset": .string(schema.dataset), "schemaSHA256": .string(schema.nativeSHA256), "values": .object(values)
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(spec)
        guard !bytes.isEmpty, bytes.count <= 1_048_576 else { throw AnyPreparedMigrationError.invalidBinding }
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        self.binding = binding; self.sourceKey = sourceKey; self.objectID = objectID
        self.schema = schema; self.values = values; specBytes = bytes; specSHA256 = AnyContentDigest.sha256(bytes)
        intentID = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            "pinkha-native-prepared-migration-intent/v1", binding.workspace.accountID,
            binding.workspace.spaceID, binding.storeID, binding.planID, sourceKey, "immutableRecord"
        ]))
    }

    static func validField(_ value: String) -> Bool {
        AnyEditorBlock.validID(value) && value.utf8.count <= 256 && !value.contains(".")
    }
    static func ownedDataset(ownerTypeID: String, key: String) throws -> String {
        guard validField(ownerTypeID), !key.isEmpty, key.utf8.count <= 128,
              key.first.map({ $0.isASCII && $0 >= "a" && $0 <= "z" }) == true,
              key.utf8.allSatisfy({ (97...122).contains($0) || (48...57).contains($0) || $0 == 95 }) else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        return ownerTypeID + "_" + key
    }
    var prepareBody: AnyJSON { .object([
        "contract": .string(AnyNativePreparedImmutableRecord.contract),
        "storeId": .string(binding.storeID), "planId": .string(binding.planID),
        "planSHA256": .string(binding.planSHA256), "sourceKey": .string(sourceKey),
        "specSHA256": .string(specSHA256), "specBase64": .string(specBytes.base64EncodedString())
    ]) }
}

public struct AnyPreparedImmutableRecordCapabilities: Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let storeID: String
    public let maximumFields: Int
    public let networkVerified: Bool

    init(_ value: AnyJSON, workspace: AnyTorahWorkspace) throws {
        guard value["contract"]?.string == AnyNativePreparedImmutableRecord.contract,
              value["accountId"]?.string.map({ Data($0.utf8) }) == Data(workspace.accountID.utf8),
              value["spaceId"]?.string.map({ Data($0.utf8) }) == Data(workspace.spaceID.utf8),
              let storeID = value["storeId"]?.string, AnyPreparedMigrationPlanBinding.validOpaque(storeID, maximum: 256),
              value["immutableRecord"]?.integer == 1,
              let limit = value["maxFields"]?.integer, (1...128).contains(limit),
              let network = value["networkVerified"]?.bool else { throw AnyPreparedMigrationError.unsupportedContract }
        self.workspace = workspace; self.storeID = storeID; maximumFields = Int(limit); networkVerified = network
    }
}

public struct AnyPreparedImmutableRecordReceipt: Equatable, Sendable {
    public enum Stage: String, Sendable { case prepared = "immutable-record-prepared", complete }
    public typealias Outcome = AnyPreparedMigrationReceipt.Outcome
    public let intent: AnyPreparedImmutableRecordIntent
    public let fingerprint: String
    public let stage: Stage
    public let outcome: Outcome
    public let objectID: String
    public let changeID: String
    public let recordIDs: [String]
    public var isCompleteAndCurrent: Bool { stage == .complete && outcome == .committed }

    init(_ value: AnyJSON, intent: AnyPreparedImmutableRecordIntent) throws {
        let binding = intent.binding
        func same(_ key: String, _ expected: String) -> Bool {
            value[key]?.string.map({ Data($0.utf8) }) == Data(expected.utf8)
        }
        guard same("contract", AnyNativePreparedImmutableRecord.contract), same("intentId", intent.intentID),
              same("storeId", binding.storeID), same("accountId", binding.workspace.accountID),
              same("spaceId", binding.workspace.spaceID), same("planId", binding.planID),
              same("planSHA256", binding.planSHA256), same("sourceKey", intent.sourceKey),
              same("kind", "immutableRecord"), same("specSHA256", intent.specSHA256),
              same("objectId", intent.objectID),
              let fingerprint = value["fingerprint"]?.string, AnyNativeCreationIdentity.isHex(fingerprint, count: 64),
              let rawStage = value["stage"]?.string, let stage = Stage(rawValue: rawStage),
              let rawOutcome = value["outcome"]?.string, let outcome = Outcome(rawValue: rawOutcome),
              let changeID = value["changeId"]?.string, AnyEditorBlock.validID(changeID),
              let records = value["recordIds"]?.array, records.count == 1,
              let recordID = records[0].string, AnyEditorBlock.validID(recordID) else {
            throw AnyPreparedMigrationError.mismatchedReceipt
        }
        let committed = [.committed, .committedDeleted, .committedModified].contains(outcome)
        guard (stage == .complete) == committed else { throw AnyPreparedMigrationError.mismatchedReceipt }
        self.intent = intent; self.fingerprint = fingerprint; self.stage = stage; self.outcome = outcome
        objectID = intent.objectID; self.changeID = changeID; recordIDs = [recordID]
    }
}

/// Exact original native changes are reconciled; a changed schema is never
/// silently refreshed after preparation. Current-authority refusal does not
/// assert that an earlier durable append was rolled back.
public actor AnyNativePreparedImmutableRecord {
    public static let contract = "pinkha-native-prepared-immutable-record-v1"
    public nonisolated let capabilities: AnyPreparedImmutableRecordCapabilities
    public nonisolated var workspace: AnyTorahWorkspace { capabilities.workspace }
    typealias Request = @Sendable (String, [String], AnyJSON?, [String: String],
        @escaping @Sendable () async throws -> Void) async throws -> AnyJSON
    private let request: Request

    public static func open(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                            authorize: @escaping @Sendable () async throws -> Void) async throws -> Self {
        guard Data(client.expectedAccountID.utf8) == Data(workspace.accountID.utf8) else { throw AnyHostError.wrongWorkspace }
        let request: Request = { method, path, body, query, authorize in
            try await client.requestJSON(method: method, path: path, body: body, query: query,
                maximumResponseBytes: 1_048_576, authorize: authorize)
        }
        let value = try await request("GET", prefix(workspace) + ["immutable-record", "capabilities"], nil, [:], authorize)
        try Task.checkCancellation(); try await authorize()
        return Self(capabilities: try .init(value, workspace: workspace), request: request)
    }
    init(capabilities: AnyPreparedImmutableRecordCapabilities, request: @escaping Request) {
        self.capabilities = capabilities; self.request = request
    }
    private static func prefix(_ workspace: AnyTorahWorkspace) -> [String] {
        ["v1", "spaces", workspace.spaceID, "pinkha", "migration"]
    }
    private func checkStore(authorize: @escaping @Sendable () async throws -> Void) async throws {
        try Task.checkCancellation(); try await authorize()
        let current = try AnyPreparedImmutableRecordCapabilities(
            await request("GET", Self.prefix(workspace) + ["immutable-record", "capabilities"], nil, [:], authorize),
            workspace: workspace)
        guard Data(current.storeID.utf8) == Data(capabilities.storeID.utf8),
              current.maximumFields == capabilities.maximumFields else { throw AnyPreparedMigrationError.changedStore }
        try Task.checkCancellation(); try await authorize()
    }
    public func schema(ownerTypeID: String, dataset: String,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedImmutableRecordSchema {
        try await checkStore(authorize: authorize)
        let value = try await request("GET", Self.prefix(workspace) + ["immutable-record", "schema"], nil,
            ["ownerTypeId": ownerTypeID, "dataset": dataset], authorize)
        try await authorize(); try Task.checkCancellation()
        return try .init(value, ownerTypeID: ownerTypeID, dataset: dataset)
    }
    private func check(_ intent: AnyPreparedImmutableRecordIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard intent.binding.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        guard Data(intent.binding.storeID.utf8) == Data(capabilities.storeID.utf8) else { throw AnyPreparedMigrationError.changedStore }
        guard intent.values.count <= capabilities.maximumFields else { throw AnyPreparedMigrationError.unsupportedContract }
        let current = try await schema(ownerTypeID: intent.schema.ownerTypeID, dataset: intent.schema.dataset, authorize: authorize)
        guard current == intent.schema else { throw AnyPreparedMigrationError.changedIntent }
    }
    public func prepare(_ intent: AnyPreparedImmutableRecordIntent,
                        authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedImmutableRecordReceipt {
        try await check(intent, authorize: authorize)
        let value = try await request("PUT", Self.prefix(workspace) + ["intents", intent.intentID, "immutable-record", "prepare"],
            intent.prepareBody, [:], authorize)
        try await authorize(); try Task.checkCancellation()
        return try .init(value, intent: intent)
    }
    public func status(_ intent: AnyPreparedImmutableRecordIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedImmutableRecordReceipt {
        try await check(intent, authorize: authorize)
        let value = try await request("GET", Self.prefix(workspace) + ["intents", intent.intentID, "immutable-record"],
            nil, [:], authorize)
        try await authorize(); try Task.checkCancellation()
        return try .init(value, intent: intent)
    }
    public func commit(_ prepared: AnyPreparedImmutableRecordReceipt,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedImmutableRecordReceipt {
        let intent = prepared.intent
        let current = try await status(intent, authorize: authorize)
        try Self.compare(prepared, current)
        if current.isCompleteAndCurrent { return current }
        guard current.outcome == .prepared else { throw AnyPreparedMigrationError.terminalOutcome(current.outcome.rawValue) }
        try await check(intent, authorize: authorize)
        let body: AnyJSON = .object([
            "contract": .string(Self.contract), "storeId": .string(intent.binding.storeID),
            "planId": .string(intent.binding.planID), "planSHA256": .string(intent.binding.planSHA256),
            "fingerprint": .string(current.fingerprint)
        ])
        let value = try await request("POST", Self.prefix(workspace) + ["intents", intent.intentID, "immutable-record", "commit"],
            body, [:], authorize)
        try await authorize(); try Task.checkCancellation()
        let next = try AnyPreparedImmutableRecordReceipt(value, intent: intent)
        try Self.compare(current, next)
        if next.outcome == .prepared { throw AnyPreparedMigrationError.incompleteCommit }
        guard next.isCompleteAndCurrent else { throw AnyPreparedMigrationError.terminalOutcome(next.outcome.rawValue) }
        return next
    }
    private static func compare(_ a: AnyPreparedImmutableRecordReceipt, _ b: AnyPreparedImmutableRecordReceipt) throws {
        guard a.fingerprint == b.fingerprint, Data(a.objectID.utf8) == Data(b.objectID.utf8),
              Data(a.changeID.utf8) == Data(b.changeID.utf8),
              a.recordIDs.map({ Data($0.utf8) }) == b.recordIDs.map({ Data($0.utf8) }),
              a.stage != .complete || b.stage == .complete else { throw AnyPreparedMigrationError.changedIntent }
    }
}
