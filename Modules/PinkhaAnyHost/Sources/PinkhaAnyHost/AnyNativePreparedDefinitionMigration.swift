import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Closed definition seeds use ordinary native validation. The caller supplies
/// descriptive values, never signed changes, root IDs or replacement IDs.
public struct AnyPreparedDefinitionIntent: Equatable, Sendable {
    public enum Kind: String, Sendable {
        case typeDefinition, collectionDefinition, propertyDefinition, partDefinition
    }
    public enum PropertyKind: String, Sendable {
        case string, number, boolean, null, array, object, datetime
    }
    public enum PropertyScope: String, Sendable { case synced, account, local }

    public let binding: AnyPreparedMigrationPlanBinding
    public let sourceKey: String
    public let kind: Kind
    public let intentID: String
    public let specBytes: Data
    public let specSHA256: String
    public let expectedOwnerID: String?

    public static func type(binding: AnyPreparedMigrationPlanBinding, sourceKey: String,
                            xKey: String, name: String, description: String = "",
                            iconCID: String = "", layout: AnyJSON? = nil,
                            hidden: Bool = false, meta: AnyJSON = .object([:])) throws -> Self {
        var seed = try rootSeed(xKey: xKey, name: name, description: description,
                                iconCID: iconCID, hidden: hidden, meta: meta)
        if let layout {
            guard layout.object != nil else { throw AnyPreparedMigrationError.invalidBinding }
            seed["layout"] = layout
        }
        return try Self(binding: binding, sourceKey: sourceKey, kind: .typeDefinition,
                        ownerID: nil, seedKey: "type", seed: .object(seed))
    }

    public static func collection(binding: AnyPreparedMigrationPlanBinding, sourceKey: String,
                                  xKey: String, name: String, description: String = "",
                                  iconCID: String = "", hidden: Bool = false,
                                  meta: AnyJSON = .object([:])) throws -> Self {
        let seed = try rootSeed(xKey: xKey, name: name, description: description,
                                iconCID: iconCID, hidden: hidden, meta: meta)
        return try Self(binding: binding, sourceKey: sourceKey, kind: .collectionDefinition,
                        ownerID: nil, seedKey: "collection", seed: .object(seed))
    }

    public static func property(binding: AnyPreparedMigrationPlanBinding, sourceKey: String,
                                ownerID: String, kind: PropertyKind, name: String,
                                xKey: String = "", description: String = "",
                                scope: PropertyScope = .synced, xFormat: AnyJSON? = nil,
                                index: String? = nil) throws -> Self {
        var seed: [String: AnyJSON] = ["kind": .string(kind.rawValue), "name": .string(name),
            "xKey": .string(xKey), "description": .string(description), "scope": .string(scope.rawValue)]
        if let xFormat {
            guard xFormat.object != nil else { throw AnyPreparedMigrationError.invalidBinding }
            seed["xFormat"] = xFormat
        }
        if let index { seed["meta"] = .object(["index": .string(index)]) }
        return try Self(binding: binding, sourceKey: sourceKey, kind: .propertyDefinition,
                        ownerID: ownerID, seedKey: "property", seed: .object(seed))
    }

    /// The ordinary part draft includes its complete atomic dataset/field/index
    /// definitions. Its native capability must be advertised before dispatch.
    public static func part(binding: AnyPreparedMigrationPlanBinding, sourceKey: String,
                            ownerID: String, draft: AnyJSON) throws -> Self {
        let allowed: Set<String> = ["key", "name", "icon", "pos", "hidden", "ui", "uses", "datasets"]
        guard let fields = draft.object, !fields.isEmpty,
              Set(fields.keys).isSubset(of: allowed),
              let key = fields["key"]?.string,
              AnyPreparedMigrationPlanBinding.validOpaque(key, maximum: 256) else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        return try Self(binding: binding, sourceKey: sourceKey, kind: .partDefinition,
                        ownerID: ownerID, seedKey: "part", seed: draft)
    }

    private static func rootSeed(xKey: String, name: String, description: String,
                                 iconCID: String, hidden: Bool, meta: AnyJSON) throws -> [String: AnyJSON] {
        guard AnyPreparedMigrationPlanBinding.validOpaque(xKey, maximum: 256),
              let metadata = meta.object, metadata.count <= 256 else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        for (key, value) in metadata {
            guard !key.isEmpty, key.utf8.count <= 64, !key.contains("."), !key.contains("$") else {
                throw AnyPreparedMigrationError.invalidBinding
            }
            switch value {
            case .string, .bool, .integer, .number: break
            default: throw AnyPreparedMigrationError.invalidBinding
            }
        }
        return ["xKey": .string(xKey), "name": .string(name), "description": .string(description),
                "iconCid": .string(iconCID), "hidden": .bool(hidden), "meta": meta]
    }

    private init(binding: AnyPreparedMigrationPlanBinding, sourceKey: String, kind: Kind,
                 ownerID: String?, seedKey: String, seed: AnyJSON) throws {
        guard AnyPreparedMigrationPlanBinding.validOpaque(sourceKey, maximum: 4096),
              ownerID.map({ AnyEditorBlock.validID($0) && $0.utf8.count <= 256 }) ?? true else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        let intentID = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            "pinkha-native-prepared-migration-intent/v1", binding.workspace.accountID,
            binding.workspace.spaceID, binding.storeID, binding.planID, sourceKey, kind.rawValue
        ]))
        var specification: [String: AnyJSON] = ["kind": .string(kind.rawValue), seedKey: seed]
        if let ownerID { specification["ownerObjectId"] = .string(ownerID) }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(AnyJSON.object(specification))
        guard !bytes.isEmpty, bytes.count <= 256 * 1024 else { throw AnyPreparedMigrationError.invalidBinding }
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        self.binding = binding; self.sourceKey = sourceKey; self.kind = kind; self.intentID = intentID
        self.specBytes = bytes; self.specSHA256 = AnyContentDigest.sha256(bytes); self.expectedOwnerID = ownerID
    }

    var prepareBody: AnyJSON { .object([
        "contract": .string(AnyNativePreparedDefinitionMigration.contract),
        "storeId": .string(binding.storeID), "planId": .string(binding.planID),
        "planSHA256": .string(binding.planSHA256), "sourceKey": .string(sourceKey),
        "specSHA256": .string(specSHA256), "specBase64": .string(specBytes.base64EncodedString())
    ]) }
}

public struct AnyPreparedDefinitionCapabilities: Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let storeID: String
    public let supportsParts: Bool
    public let networkVerified: Bool

    init(_ value: AnyJSON, workspace: AnyTorahWorkspace) throws {
        guard value["contract"]?.string == AnyNativePreparedDefinitionMigration.contract,
              value["accountId"]?.string == workspace.accountID,
              value["spaceId"]?.string == workspace.spaceID,
              let storeID = value["storeId"]?.string,
              AnyPreparedMigrationPlanBinding.validOpaque(storeID, maximum: 256),
              value["typeDefinition"]?.integer == 1,
              value["collectionDefinition"]?.integer == 1,
              value["propertyDefinition"]?.integer == 1,
              let networkVerified = value["networkVerified"]?.bool else {
            throw AnyPreparedMigrationError.unsupportedContract
        }
        let parts = value["partDefinition"]
        guard parts == nil || parts?.integer == 0 || parts?.integer == 1 else {
            throw AnyPreparedMigrationError.unsupportedContract
        }
        self.workspace = workspace; self.storeID = storeID
        self.supportsParts = parts?.integer == 1; self.networkVerified = networkVerified
    }
}

public struct AnyPreparedDefinitionReceipt: Equatable, Sendable {
    public enum Stage: String, Sendable {
        case rootPrepared = "definition-root-prepared"
        case rootCommitted = "definition-root-committed"
        case bootstrapPrepared = "definition-bootstrap-prepared"
        case propertyPrepared = "definition-property-prepared"
        case partPrepared = "definition-part-prepared"
        case complete

        fileprivate var order: Int {
            switch self {
            case .rootPrepared, .propertyPrepared, .partPrepared: 0
            case .rootCommitted: 1
            case .bootstrapPrepared: 2
            case .complete: 3
            }
        }
    }
    public typealias Outcome = AnyPreparedMigrationReceipt.Outcome
    public let intent: AnyPreparedDefinitionIntent
    public let fingerprint: String
    public let stage: Stage
    public let outcome: Outcome
    public let objectID: String
    public let changeID: String
    /// Atomic part batches retain this exact order, including all dataset IDs.
    public let recordIDs: [String]
    public var isCompleteAndCurrent: Bool { stage == .complete && outcome == .committed }

    init(_ value: AnyJSON, intent: AnyPreparedDefinitionIntent) throws {
        let binding = intent.binding
        guard value["contract"]?.string == AnyNativePreparedDefinitionMigration.contract,
              value["intentId"]?.string == intent.intentID,
              value["storeId"]?.string == binding.storeID,
              value["accountId"]?.string == binding.workspace.accountID,
              value["spaceId"]?.string == binding.workspace.spaceID,
              value["planId"]?.string == binding.planID,
              value["planSHA256"]?.string == binding.planSHA256,
              value["sourceKey"]?.string.map({ Data($0.utf8) }) == Data(intent.sourceKey.utf8),
              value["kind"]?.string == intent.kind.rawValue,
              value["specSHA256"]?.string == intent.specSHA256,
              let fingerprint = value["fingerprint"]?.string,
              AnyNativeCreationIdentity.isHex(fingerprint, count: 64),
              let rawStage = value["stage"]?.string, let stage = Stage(rawValue: rawStage),
              let rawOutcome = value["outcome"]?.string, let outcome = Outcome(rawValue: rawOutcome),
              let objectID = value["objectId"]?.string, AnyEditorBlock.validID(objectID),
              let changeID = value["changeId"]?.string, AnyEditorBlock.validID(changeID) else {
            throw AnyPreparedMigrationError.mismatchedReceipt
        }
        guard !(stage == .complete && outcome == .prepared),
              !([.committed, .committedDeleted, .committedModified].contains(outcome) && stage != .complete) else {
            throw AnyPreparedMigrationError.mismatchedReceipt
        }
        var ids: [String] = []
        if let records = value["recordIds"] {
            guard let values = records.array, values.count <= 1024 else { throw AnyPreparedMigrationError.mismatchedReceipt }
            ids = try values.map {
                guard let id = $0.string, AnyEditorBlock.validID(id) else { throw AnyPreparedMigrationError.mismatchedReceipt }
                return id
            }
            guard Set(ids.map { Data($0.utf8) }).count == ids.count else { throw AnyPreparedMigrationError.mismatchedReceipt }
        }
        switch intent.kind {
        case .typeDefinition, .collectionDefinition:
            guard [.rootPrepared, .rootCommitted, .bootstrapPrepared, .complete].contains(stage) else {
                throw AnyPreparedMigrationError.mismatchedReceipt
            }
            if stage == .rootPrepared || stage == .rootCommitted {
                guard ids.isEmpty, objectID == changeID else { throw AnyPreparedMigrationError.mismatchedReceipt }
            } else {
                guard ids == [objectID] else { throw AnyPreparedMigrationError.mismatchedReceipt }
            }
        case .propertyDefinition:
            guard [.propertyPrepared, .complete].contains(stage), ids.count == 1,
                  objectID == intent.expectedOwnerID else { throw AnyPreparedMigrationError.mismatchedReceipt }
        case .partDefinition:
            guard [.partPrepared, .complete].contains(stage), !ids.isEmpty,
                  objectID == intent.expectedOwnerID else { throw AnyPreparedMigrationError.mismatchedReceipt }
        }
        self.intent = intent; self.fingerprint = fingerprint; self.stage = stage; self.outcome = outcome
        self.objectID = objectID; self.changeID = changeID; self.recordIDs = ids
    }
}

/// Resumption reconciles the same native ledger entry before appending. Lost
/// acknowledgements propagate; no call allocates a substitute definition.
public actor AnyNativePreparedDefinitionMigration {
    public static let contract = "pinkha-native-prepared-definitions-v1"
    public nonisolated let capabilities: AnyPreparedDefinitionCapabilities
    public nonisolated var workspace: AnyTorahWorkspace { capabilities.workspace }
    private typealias Request = @Sendable (
        String, [String], AnyJSON?, @escaping @Sendable () async throws -> Void
    ) async throws -> AnyJSON
    private let request: Request

    public static func open(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                            authorize: @escaping @Sendable () async throws -> Void) async throws -> Self {
        guard client.expectedAccountID == workspace.accountID else { throw AnyHostError.wrongWorkspace }
        let request: Request = { method, path, body, authorize in
            try await client.requestJSON(method: method, path: path, body: body,
                                         maximumResponseBytes: 262_144, authorize: authorize)
        }
        let value = try await request("GET", prefix(workspace) + ["definition", "capabilities"], nil, authorize)
        try Task.checkCancellation(); try await authorize()
        return Self(capabilities: try .init(value, workspace: workspace), request: request)
    }

    init(capabilities: AnyPreparedDefinitionCapabilities,
         request: @escaping @Sendable (String, [String], AnyJSON?,
             @escaping @Sendable () async throws -> Void) async throws -> AnyJSON) {
        self.capabilities = capabilities; self.request = request
    }

    private static func prefix(_ workspace: AnyTorahWorkspace) -> [String] {
        ["v1", "spaces", workspace.spaceID, "pinkha", "migration"]
    }

    private func check(_ intent: AnyPreparedDefinitionIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard intent.binding.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        guard intent.binding.storeID == capabilities.storeID else { throw AnyPreparedMigrationError.changedStore }
        try Task.checkCancellation(); try await authorize()
        let current = try AnyPreparedDefinitionCapabilities(
            await request("GET", Self.prefix(workspace) + ["definition", "capabilities"], nil, authorize),
            workspace: workspace)
        guard current.storeID == capabilities.storeID else { throw AnyPreparedMigrationError.changedStore }
        guard intent.kind != .partDefinition || current.supportsParts else { throw AnyPreparedMigrationError.unsupportedContract }
        try Task.checkCancellation(); try await authorize()
    }

    public func prepare(_ intent: AnyPreparedDefinitionIntent,
                        authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedDefinitionReceipt {
        try await check(intent, authorize: authorize)
        let value = try await request("PUT", Self.prefix(workspace) +
            ["intents", intent.intentID, "definition", "prepare"], intent.prepareBody, authorize)
        try await authorize(); try Task.checkCancellation()
        return try .init(value, intent: intent)
    }

    public func status(_ intent: AnyPreparedDefinitionIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedDefinitionReceipt {
        try await check(intent, authorize: authorize)
        let value = try await request("GET", Self.prefix(workspace) + ["intents", intent.intentID, "definition"], nil, authorize)
        try await authorize(); try Task.checkCancellation()
        return try .init(value, intent: intent)
    }

    public func commit(_ prepared: AnyPreparedDefinitionReceipt,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedDefinitionReceipt {
        let intent = prepared.intent
        var current = try await status(intent, authorize: authorize)
        try Self.compare(prepared, current)
        let body: AnyJSON = .object([
            "contract": .string(Self.contract), "storeId": .string(intent.binding.storeID),
            "planId": .string(intent.binding.planID), "planSHA256": .string(intent.binding.planSHA256),
            "fingerprint": .string(current.fingerprint)
        ])
        let root = intent.kind == .typeDefinition || intent.kind == .collectionDefinition
        for _ in 0..<(root ? 3 : 1) {
            if current.isCompleteAndCurrent { return current }
            guard current.outcome == .prepared else { throw AnyPreparedMigrationError.terminalOutcome(current.outcome.rawValue) }
            try await check(intent, authorize: authorize)
            let value = try await request("POST", Self.prefix(workspace) +
                ["intents", intent.intentID, "definition", "commit"], body, authorize)
            try await authorize(); try Task.checkCancellation()
            let next = try AnyPreparedDefinitionReceipt(value, intent: intent)
            try Self.compare(current, next)
            guard next.outcome == .prepared || next.isCompleteAndCurrent else {
                throw AnyPreparedMigrationError.terminalOutcome(next.outcome.rawValue)
            }
            guard next.stage.order > current.stage.order else { throw AnyPreparedMigrationError.incompleteCommit }
            current = next
        }
        guard current.isCompleteAndCurrent else { throw AnyPreparedMigrationError.incompleteCommit }
        return current
    }

    private static func compare(_ previous: AnyPreparedDefinitionReceipt,
                                _ current: AnyPreparedDefinitionReceipt) throws {
        guard previous.fingerprint == current.fingerprint, previous.objectID == current.objectID,
              current.stage.order >= previous.stage.order else { throw AnyPreparedMigrationError.changedIntent }
        if !previous.recordIDs.isEmpty, previous.recordIDs != current.recordIDs {
            throw AnyPreparedMigrationError.changedIntent
        }
        // The root and bootstrap are distinct signed changes. An already
        // prepared bootstrap/property/part must keep its original signed ID.
        let sameSignedStage = previous.stage == current.stage ||
            (previous.stage == .rootPrepared && current.stage == .rootCommitted) ||
            [.bootstrapPrepared, .propertyPrepared, .partPrepared, .complete].contains(previous.stage)
        if sameSignedStage, previous.changeID != current.changeID { throw AnyPreparedMigrationError.changedIntent }
    }
}
