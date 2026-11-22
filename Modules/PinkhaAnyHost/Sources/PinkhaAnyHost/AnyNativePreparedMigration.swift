import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyPreparedMigrationError: Error, Equatable, Sendable {
    case invalidBinding
    case unsupportedContract
    case changedStore
    case mismatchedReceipt
    case changedIntent
    case terminalOutcome(String)
    case incompleteCommit
}

/// A logical plan keeps its ID when its input changes. Its separate content
/// digest makes reuse with changed input a collision in the native ledger.
public struct AnyPreparedMigrationPlanBinding: Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let storeID: String
    public let planID: String
    public let planSHA256: String

    public init(workspace: AnyTorahWorkspace, storeID: String,
                planID: String, planSHA256: String) throws {
        guard Self.validOpaque(storeID, maximum: 256),
              AnyNativeCreationIdentity.isHex(planID, count: 64),
              AnyNativeCreationIdentity.isHex(planSHA256, count: 64) else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        self.workspace = workspace; self.storeID = storeID
        self.planID = planID; self.planSHA256 = planSHA256
    }

    static func validOpaque(_ value: String, maximum: Int) -> Bool {
        !value.isEmpty && value.utf8.count <= maximum &&
        value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }

    static func material(_ parts: [String]) -> Data {
        Data(parts.map { "\($0.utf8.count):\($0)" }.joined(separator: "|").utf8)
    }
}

/// These are the two typed specifications the first native contract admits.
/// The bytes are JSON specifications, never signed DAG envelopes or caller IDs.
public struct AnyPreparedMigrationIntent: Equatable, Sendable {
    public enum Kind: String, Sendable { case object, editorBlock }
    public let binding: AnyPreparedMigrationPlanBinding
    public let sourceKey: String
    public let kind: Kind
    public let intentID: String
    public let specBytes: Data
    public let specSHA256: String
    public let expectedObjectID: String?

    public static func object(binding: AnyPreparedMigrationPlanBinding, sourceKey: String,
                              typeID: String, collections: [String] = [],
                              initialProperties: AnyJSON) throws -> Self {
        let id = try identifier(binding: binding, sourceKey: sourceKey, kind: .object)
        // Reuse the production creation shape and bounds. This does not use
        // the old host-only reservation journal or its unknown auto-ID retry.
        let checked = try AnyNativeObjectCreationIntent(workspace: binding.workspace,
            mutationID: String(id.prefix(32)), typeID: typeID,
            collections: collections, initialProperties: initialProperties)
        return try Self(binding: binding, sourceKey: sourceKey, kind: .object,
            intentID: id, specification: checked.body, expectedObjectID: nil)
    }

    public static func block(binding: AnyPreparedMigrationPlanBinding, sourceKey: String,
                             objectID: String, dataset: String = "editor_blocks",
                             type: String, text: String, style: AnyJSON = .object([:]),
                             parentID: String = "", position: String) throws -> Self {
        let id = try identifier(binding: binding, sourceKey: sourceKey, kind: .editorBlock)
        let checked = try AnyNativeBlockCreationIntent(workspace: binding.workspace,
            mutationID: String(id.prefix(32)), objectID: objectID, dataset: dataset,
            type: type, text: text, style: style, parentID: parentID, position: position)
        var specification = checked.body.object!
        specification["objectId"] = .string(objectID)
        specification["dataset"] = .string(dataset)
        return try Self(binding: binding, sourceKey: sourceKey, kind: .editorBlock,
            intentID: id, specification: .object(specification), expectedObjectID: objectID)
    }

    private init(binding: AnyPreparedMigrationPlanBinding, sourceKey: String, kind: Kind,
                 intentID: String, specification: AnyJSON, expectedObjectID: String?) throws {
        // AnyHostCanonical is a typed revision encoding, not JSON. The native
        // endpoint deliberately parses these exact UTF-8 JSON bytes instead.
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(specification)
        guard !bytes.isEmpty, bytes.count <= 1_048_576 else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        self.binding = binding; self.sourceKey = sourceKey; self.kind = kind
        self.intentID = intentID; self.specBytes = bytes
        self.specSHA256 = AnyContentDigest.sha256(bytes)
        self.expectedObjectID = expectedObjectID
    }

    private static func identifier(binding: AnyPreparedMigrationPlanBinding,
                                   sourceKey: String, kind: Kind) throws -> String {
        guard AnyPreparedMigrationPlanBinding.validOpaque(sourceKey, maximum: 4096) else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        return AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            "pinkha-native-prepared-migration-intent/v1", binding.workspace.accountID,
            binding.workspace.spaceID, binding.storeID, binding.planID, sourceKey, kind.rawValue
        ]))
    }

    var prepareBody: AnyJSON { .object([
        "contract": .string(AnyNativePreparedMigration.contract),
        "storeId": .string(binding.storeID), "planId": .string(binding.planID),
        "planSHA256": .string(binding.planSHA256), "sourceKey": .string(sourceKey),
        "specSHA256": .string(specSHA256), "specBase64": .string(specBytes.base64EncodedString())
    ]) }
}

public struct AnyPreparedMigrationCapabilities: Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let storeID: String
    public let networkVerified: Bool

    init(_ value: AnyJSON, workspace: AnyTorahWorkspace) throws {
        guard value["contract"]?.string == AnyNativePreparedMigration.contract,
              value["accountId"]?.string == workspace.accountID,
              value["spaceId"]?.string == workspace.spaceID,
              let storeID = value["storeId"]?.string,
              AnyPreparedMigrationPlanBinding.validOpaque(storeID, maximum: 256),
              value["object"]?.integer == 1, value["editorBlock"]?.integer == 1,
              value["file"]?.integer == 0,
              let networkVerified = value["networkVerified"]?.bool else {
            throw AnyPreparedMigrationError.unsupportedContract
        }
        self.workspace = workspace; self.storeID = storeID; self.networkVerified = networkVerified
    }
}

public struct AnyPreparedMigrationReceipt: Equatable, Sendable {
    public enum Stage: String, Sendable {
        case rootPrepared = "root-prepared", rootCommitted = "root-committed"
        case bootstrapPrepared = "bootstrap-prepared", blockPrepared = "block-prepared", complete
    }
    public enum Outcome: String, Sendable {
        case prepared, committed, committedDeleted = "committed_deleted"
        case committedModified = "committed_modified", obsolete
    }
    public let intent: AnyPreparedMigrationIntent
    public let fingerprint: String
    public let stage: Stage
    public let outcome: Outcome
    public let objectID: String?
    public let changeID: String?
    public let recordIDs: [String]

    /// An original successful create that was later edited or deleted is
    /// retained as such. It is never converted to a current migration success.
    public var isCompleteAndCurrent: Bool { stage == .complete && outcome == .committed }

    init(_ value: AnyJSON, intent: AnyPreparedMigrationIntent) throws {
        let binding = intent.binding
        guard value["contract"]?.string == AnyNativePreparedMigration.contract,
              value["intentId"]?.string == intent.intentID,
              value["storeId"]?.string == binding.storeID,
              value["accountId"]?.string == binding.workspace.accountID,
              value["spaceId"]?.string == binding.workspace.spaceID,
              value["planId"]?.string == binding.planID,
              value["planSHA256"]?.string == binding.planSHA256,
              value["sourceKey"]?.string == intent.sourceKey,
              value["kind"]?.string == intent.kind.rawValue,
              value["specSHA256"]?.string == intent.specSHA256,
              let fingerprint = value["fingerprint"]?.string,
              AnyNativeCreationIdentity.isHex(fingerprint, count: 64),
              let rawStage = value["stage"]?.string, let stage = Stage(rawValue: rawStage),
              let rawOutcome = value["outcome"]?.string, let outcome = Outcome(rawValue: rawOutcome) else {
            throw AnyPreparedMigrationError.mismatchedReceipt
        }
        guard (intent.kind == .object && stage != .blockPrepared) ||
              (intent.kind == .editorBlock && (stage == .blockPrepared || stage == .complete)),
              !(stage == .complete && outcome == .prepared),
              !(outcome == .committed && stage != .complete) else {
            throw AnyPreparedMigrationError.mismatchedReceipt
        }
        func optionalID(_ key: String) throws -> String? {
            guard let item = value[key] else { return nil }
            guard let id = item.string, AnyEditorBlock.validID(id) else {
                throw AnyPreparedMigrationError.mismatchedReceipt
            }
            return id
        }
        let objectID = try optionalID("objectId")
        let changeID = try optionalID("changeId")
        var recordIDs: [String] = []
        if let field = value["recordIds"] {
            guard let values = field.array, values.count <= 16 else {
                throw AnyPreparedMigrationError.mismatchedReceipt
            }
            recordIDs = try values.map {
                guard let id = $0.string, AnyEditorBlock.validID(id) else {
                    throw AnyPreparedMigrationError.mismatchedReceipt
                }
                return id
            }
            guard Set(recordIDs).count == recordIDs.count else {
                throw AnyPreparedMigrationError.mismatchedReceipt
            }
        }
        if let expected = intent.expectedObjectID, objectID != expected {
            throw AnyPreparedMigrationError.mismatchedReceipt
        }
        if stage == .complete {
            guard let objectID, changeID != nil, recordIDs.count == 1,
                  intent.kind != .object || recordIDs == [objectID] else {
                throw AnyPreparedMigrationError.mismatchedReceipt
            }
        }
        self.intent = intent; self.fingerprint = fingerprint; self.stage = stage
        self.outcome = outcome; self.objectID = objectID; self.changeID = changeID
        self.recordIDs = recordIDs
    }
}

/// Typed access to the native PREPARED-byte ledger in one persistent native
/// store. It never falls back to generic auto-ID creation or content search.
/// A full-space migration still needs source admission, complete planning,
/// semantic readback, cold reopen and mounted-app acceptance above this client.
public actor AnyNativePreparedMigration {
    public static let contract = "pinkha-native-prepared-migration-v1"
    public nonisolated let capabilities: AnyPreparedMigrationCapabilities
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
                maximumResponseBytes: 65_536, authorize: authorize)
        }
        let value = try await request("GET", prefix(workspace) + ["capabilities"], nil, authorize)
        try Task.checkCancellation(); try await authorize()
        return Self(capabilities: try .init(value, workspace: workspace), request: request)
    }

    /// Internal transport injection exercises publication/collision boundaries;
    /// production open() always uses the authenticated account-bound client.
    init(capabilities: AnyPreparedMigrationCapabilities,
         request: @escaping @Sendable (String, [String], AnyJSON?,
             @escaping @Sendable () async throws -> Void) async throws -> AnyJSON) {
        self.capabilities = capabilities; self.request = request
    }

    private static func prefix(_ workspace: AnyTorahWorkspace) -> [String] {
        ["v1", "spaces", workspace.spaceID, "pinkha", "migration"]
    }

    private func check(_ intent: AnyPreparedMigrationIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard intent.binding.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        guard intent.binding.storeID == capabilities.storeID else { throw AnyPreparedMigrationError.changedStore }
        try Task.checkCancellation(); try await authorize()
        let current = try AnyPreparedMigrationCapabilities(
            await request("GET", Self.prefix(workspace) + ["capabilities"], nil, authorize),
            workspace: workspace)
        guard current.storeID == capabilities.storeID else { throw AnyPreparedMigrationError.changedStore }
        try Task.checkCancellation(); try await authorize()
    }

    public func prepare(_ intent: AnyPreparedMigrationIntent,
                        authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedMigrationReceipt {
        try await check(intent, authorize: authorize)
        let endpoint = intent.kind == .object ? "object" : "block"
        let value = try await request("PUT", Self.prefix(workspace) +
            ["intents", intent.intentID, endpoint, "prepare"], intent.prepareBody, authorize)
        // If authority/ownership changes after dispatch, the caller reconciles
        // this same immutable intent. It must not publish an unscoped receipt.
        try await authorize(); try Task.checkCancellation()
        return try AnyPreparedMigrationReceipt(value, intent: intent)
    }

    public func status(_ intent: AnyPreparedMigrationIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedMigrationReceipt {
        try await check(intent, authorize: authorize)
        let value = try await request("GET", Self.prefix(workspace) + ["intents", intent.intentID], nil, authorize)
        try await authorize(); try Task.checkCancellation()
        return try AnyPreparedMigrationReceipt(value, intent: intent)
    }

    /// Advance only confirmed, immutable native stages. Object root, bootstrap
    /// preparation and bootstrap append require at most three POSTs; a block
    /// requires one. A failed/uncertain request is never replayed in this call.
    /// Calling commit again first reconciles the original native status, then
    /// resumes only remaining stages without preparing a replacement identity.
    public func commit(_ prepared: AnyPreparedMigrationReceipt,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedMigrationReceipt {
        let intent = prepared.intent
        var current = try await status(intent, authorize: authorize)
        guard current.fingerprint == prepared.fingerprint else { throw AnyPreparedMigrationError.changedIntent }
        let body: AnyJSON = .object([
            "contract": .string(Self.contract), "storeId": .string(intent.binding.storeID),
            "planId": .string(intent.binding.planID), "planSHA256": .string(intent.binding.planSHA256),
            "fingerprint": .string(current.fingerprint)
        ])
        func order(_ stage: AnyPreparedMigrationReceipt.Stage) -> Int {
            switch stage {
            case .rootPrepared, .blockPrepared: 0
            case .rootCommitted: 1
            case .bootstrapPrepared: 2
            case .complete: 3
            }
        }
        if let originalObject = prepared.objectID, current.objectID != originalObject {
            throw AnyPreparedMigrationError.changedIntent
        }
        guard order(current.stage) >= order(prepared.stage) else {
            throw AnyPreparedMigrationError.changedIntent
        }
        for _ in 0..<(intent.kind == .object ? 3 : 1) {
            if current.isCompleteAndCurrent { return current }
            guard current.outcome == .prepared else {
                throw AnyPreparedMigrationError.terminalOutcome(current.outcome.rawValue)
            }
            // Every durable stage reacquires current store/account/owner
            // admission. The native ledger performs the atomic write fences.
            try await check(intent, authorize: authorize)
            let value = try await request("POST", Self.prefix(workspace) +
                ["intents", intent.intentID, "commit"], body, authorize)
            try await authorize(); try Task.checkCancellation()
            let next = try AnyPreparedMigrationReceipt(value, intent: intent)
            guard next.fingerprint == current.fingerprint else { throw AnyPreparedMigrationError.changedIntent }
            if let objectID = current.objectID, next.objectID != objectID {
                throw AnyPreparedMigrationError.changedIntent
            }
            guard next.outcome == .prepared || next.isCompleteAndCurrent else {
                throw AnyPreparedMigrationError.terminalOutcome(next.outcome.rawValue)
            }
            guard order(next.stage) > order(current.stage) else {
                throw AnyPreparedMigrationError.incompleteCommit
            }
            let sameSignedStage = intent.kind == .editorBlock ||
                (current.stage == .rootPrepared && next.stage == .rootCommitted) ||
                (current.stage == .bootstrapPrepared && next.stage == .complete)
            if sameSignedStage, let changeID = current.changeID, next.changeID != changeID {
                throw AnyPreparedMigrationError.changedIntent
            }
            current = next
        }
        guard current.isCompleteAndCurrent else { throw AnyPreparedMigrationError.incompleteCommit }
        return current
    }
}
