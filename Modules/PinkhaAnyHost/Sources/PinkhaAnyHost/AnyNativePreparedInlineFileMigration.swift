import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// An immutable, bounded inline-file plan. Large files and variants require a
/// different native contract; they are never truncated or converted here.
public struct AnyPreparedInlineFileIntent: Equatable, Sendable {
    public static let maximumBytes = 4095
    public let binding: AnyPreparedMigrationPlanBinding
    public let sourceKey: String
    public let intentID: String
    public let ownerObjectID: String
    public let name: String
    public let mime: String
    public let size: Int
    public let contentSHA256: String
    public let specBytes: Data
    public let specSHA256: String

    public init(binding: AnyPreparedMigrationPlanBinding, sourceKey: String,
                ownerObjectID: String, name: String, mime: String, content: Data) throws {
        guard AnyPreparedMigrationPlanBinding.validOpaque(sourceKey, maximum: 4096),
              AnyPreparedMigrationPlanBinding.validOpaque(ownerObjectID, maximum: 256),
              name.utf8.count <= 1024, mime.utf8.count <= 255,
              !name.contains("\0"), !mime.contains("\0"),
              content.count <= Self.maximumBytes else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        let contentSHA256 = AnyContentDigest.sha256(content)
        let specification: AnyJSON = .object([
            "ownerObjectId": .string(ownerObjectID), "name": .string(name),
            "mime": .string(mime), "content": .string(content.base64EncodedString()),
            "contentSHA256": .string(contentSHA256)
        ])
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(specification)
        self.binding = binding
        self.sourceKey = sourceKey
        self.intentID = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            "pinkha-native-prepared-migration-intent/v1", binding.workspace.accountID,
            binding.workspace.spaceID, binding.storeID, binding.planID, sourceKey, "inlineFile"
        ]))
        self.ownerObjectID = ownerObjectID
        self.name = name
        self.mime = mime
        self.size = content.count
        self.contentSHA256 = contentSHA256
        self.specBytes = bytes
        self.specSHA256 = AnyContentDigest.sha256(bytes)
    }

    var prepareBody: AnyJSON { .object([
        "contract": .string(AnyNativePreparedInlineFileMigration.contract),
        "storeId": .string(binding.storeID), "planId": .string(binding.planID),
        "planSHA256": .string(binding.planSHA256), "sourceKey": .string(sourceKey),
        "specSHA256": .string(specSHA256), "specBase64": .string(specBytes.base64EncodedString())
    ]) }
}

/// This capability describes only the bounded native inline-file route.
/// General file migration remains unavailable in this contract.
public struct AnyPreparedInlineFileCapabilities: Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let storeID: String
    public let maximumInlineBytes: Int
    public let networkVerified: Bool

    init(_ value: AnyJSON, workspace: AnyTorahWorkspace) throws {
        guard value["contract"]?.string == AnyNativePreparedInlineFileMigration.contract,
              value["accountId"]?.string == workspace.accountID,
              value["spaceId"]?.string == workspace.spaceID,
              let storeID = value["storeId"]?.string,
              AnyPreparedMigrationPlanBinding.validOpaque(storeID, maximum: 256),
              value["inlineFile"]?.integer == 1,
              value["maximumInlineBytes"]?.integer == Int64(AnyPreparedInlineFileIntent.maximumBytes),
              value["file"]?.integer == 0,
              let networkVerified = value["networkVerified"]?.bool else {
            throw AnyPreparedMigrationError.unsupportedContract
        }
        self.workspace = workspace
        self.storeID = storeID
        self.maximumInlineBytes = AnyPreparedInlineFileIntent.maximumBytes
        self.networkVerified = networkVerified
    }
}

public struct AnyPreparedInlineFileReceipt: Equatable, Sendable {
    public enum Stage: String, Sendable {
        case filePrepared = "file-prepared"
        case fileRootCommitted = "file-root-committed"
        case complete

        fileprivate var order: Int {
            switch self {
            case .filePrepared: 0
            case .fileRootCommitted: 1
            case .complete: 2
            }
        }
    }

    public enum Outcome: String, Sendable {
        case prepared, committed, committedDeleted = "committed_deleted"
        case committedModified = "committed_modified", obsolete
    }

    public let intent: AnyPreparedInlineFileIntent
    public let fingerprint: String
    public let stage: Stage
    public let outcome: Outcome
    /// The immutable payload root; the owning document is intent.ownerObjectID.
    public let objectID: String
    public let changeID: String
    public let fileID: String
    public let recordIDs: [String]
    public var isCompleteAndCurrent: Bool { stage == .complete && outcome == .committed }

    init(_ value: AnyJSON, intent: AnyPreparedInlineFileIntent) throws {
        let binding = intent.binding
        guard value["contract"]?.string == AnyNativePreparedInlineFileMigration.contract,
              value["intentId"]?.string == intent.intentID,
              value["storeId"]?.string == binding.storeID,
              value["accountId"]?.string == binding.workspace.accountID,
              value["spaceId"]?.string == binding.workspace.spaceID,
              value["planId"]?.string == binding.planID,
              value["planSHA256"]?.string == binding.planSHA256,
              value["sourceKey"]?.string == intent.sourceKey,
              value["kind"]?.string == "inlineFile",
              value["specSHA256"]?.string == intent.specSHA256,
              value["ownerObjectId"]?.string == intent.ownerObjectID,
              value["contentSHA256"]?.string == intent.contentSHA256,
              value["size"]?.integer == Int64(intent.size),
              let fingerprint = value["fingerprint"]?.string,
              AnyNativeCreationIdentity.isHex(fingerprint, count: 64),
              let rawStage = value["stage"]?.string, let stage = Stage(rawValue: rawStage),
              let rawOutcome = value["outcome"]?.string, let outcome = Outcome(rawValue: rawOutcome),
              let objectID = value["objectId"]?.string, AnyEditorBlock.validID(objectID),
              let changeID = value["changeId"]?.string, AnyEditorBlock.validID(changeID),
              let fileID = value["fileId"]?.string, AnyEditorBlock.validID(fileID),
              let records = value["recordIds"]?.array,
              records == [.string(fileID)] else {
            throw AnyPreparedMigrationError.mismatchedReceipt
        }
        switch outcome {
        case .prepared:
            guard stage != .complete else { throw AnyPreparedMigrationError.mismatchedReceipt }
        case .committed, .committedDeleted, .committedModified:
            guard stage == .complete else { throw AnyPreparedMigrationError.mismatchedReceipt }
        case .obsolete:
            break
        }
        self.intent = intent
        self.fingerprint = fingerprint
        self.stage = stage
        self.outcome = outcome
        self.objectID = objectID
        self.changeID = changeID
        self.fileID = fileID
        self.recordIDs = [fileID]
    }

    fileprivate func hasSameIdentity(as other: Self) -> Bool {
        intent == other.intent && fingerprint == other.fingerprint &&
        objectID == other.objectID && changeID == other.changeID &&
        fileID == other.fileID && recordIDs == other.recordIDs
    }
}

/// Access to the separate native inline-file PREPARED ledger. Each native
/// stage keeps its original signed identity. An uncertain write is returned
/// to the caller; a later call reconciles status before attempting a next stage.
public actor AnyNativePreparedInlineFileMigration {
    public static let contract = AnyNativePreparedMigration.contract
    public nonisolated let capabilities: AnyPreparedInlineFileCapabilities
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
        let value = try await request("GET", prefix(workspace) + ["inline-file", "capabilities"], nil, authorize)
        try Task.checkCancellation()
        try await authorize()
        return Self(capabilities: try .init(value, workspace: workspace), request: request)
    }

    /// Internal injection keeps transport controls separate from native proof.
    init(capabilities: AnyPreparedInlineFileCapabilities,
         request: @escaping @Sendable (String, [String], AnyJSON?,
             @escaping @Sendable () async throws -> Void) async throws -> AnyJSON) {
        self.capabilities = capabilities
        self.request = request
    }

    private static func prefix(_ workspace: AnyTorahWorkspace) -> [String] {
        ["v1", "spaces", workspace.spaceID, "pinkha", "migration"]
    }

    private func path(_ intent: AnyPreparedInlineFileIntent) -> [String] {
        Self.prefix(workspace) + ["intents", intent.intentID, "inline-file"]
    }

    private func check(_ intent: AnyPreparedInlineFileIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard intent.binding.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        guard intent.binding.storeID == capabilities.storeID else { throw AnyPreparedMigrationError.changedStore }
        try Task.checkCancellation()
        try await authorize()
        let current = try AnyPreparedInlineFileCapabilities(
            await request("GET", Self.prefix(workspace) + ["inline-file", "capabilities"], nil, authorize),
            workspace: workspace)
        guard current.storeID == capabilities.storeID else { throw AnyPreparedMigrationError.changedStore }
        try Task.checkCancellation()
        try await authorize()
    }

    public func prepare(_ intent: AnyPreparedInlineFileIntent,
                        authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedInlineFileReceipt {
        try await check(intent, authorize: authorize)
        let value = try await request("PUT", path(intent) + ["prepare"], intent.prepareBody, authorize)
        try await authorize()
        try Task.checkCancellation()
        return try .init(value, intent: intent)
    }

    public func status(_ intent: AnyPreparedInlineFileIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedInlineFileReceipt {
        try await check(intent, authorize: authorize)
        let value = try await request("GET", path(intent), nil, authorize)
        try await authorize()
        try Task.checkCancellation()
        return try .init(value, intent: intent)
    }

    public func commit(_ prepared: AnyPreparedInlineFileReceipt,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedInlineFileReceipt {
        let intent = prepared.intent
        var current = try await status(intent, authorize: authorize)
        guard current.hasSameIdentity(as: prepared), current.stage.order >= prepared.stage.order else {
            throw AnyPreparedMigrationError.changedIntent
        }
        let body: AnyJSON = .object([
            "contract": .string(Self.contract), "storeId": .string(intent.binding.storeID),
            "planId": .string(intent.binding.planID), "planSHA256": .string(intent.binding.planSHA256),
            "fingerprint": .string(prepared.fingerprint)
        ])
        for _ in 0..<2 {
            if current.isCompleteAndCurrent { return current }
            guard current.outcome == .prepared else {
                throw AnyPreparedMigrationError.terminalOutcome(current.outcome.rawValue)
            }
            try await check(intent, authorize: authorize)
            let value = try await request("POST", path(intent) + ["commit"], body, authorize)
            try await authorize()
            try Task.checkCancellation()
            let next = try AnyPreparedInlineFileReceipt(value, intent: intent)
            guard next.hasSameIdentity(as: current) else { throw AnyPreparedMigrationError.changedIntent }
            guard next.outcome == .prepared || next.isCompleteAndCurrent else {
                throw AnyPreparedMigrationError.terminalOutcome(next.outcome.rawValue)
            }
            guard next.stage.order > current.stage.order else { throw AnyPreparedMigrationError.incompleteCommit }
            current = next
        }
        guard current.isCompleteAndCurrent else { throw AnyPreparedMigrationError.incompleteCommit }
        return current
    }
}
