import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// An immutable full-tier file plan. Bytes are streamed from a verified private
/// copy; the intent binds exact metadata, byte count and plaintext digest.
public struct AnyPreparedFileIntent: Equatable, Sendable {
    public static let maximumBytes: Int64 = 512 << 20
    public let binding: AnyPreparedMigrationPlanBinding
    public let sourceKey: String
    public let intentID: String
    public let ownerObjectID: String
    public let name: String
    public let mime: String
    public let size: Int64
    public let contentSHA256: String
    public let specBytes: Data
    public let specSHA256: String

    public init(binding: AnyPreparedMigrationPlanBinding, sourceKey: String,
                ownerObjectID: String, name: String, mime: String, size: Int64, contentSHA256: String) throws {
        guard AnyPreparedMigrationPlanBinding.validOpaque(sourceKey, maximum: 4096),
              AnyPreparedMigrationPlanBinding.validOpaque(ownerObjectID, maximum: 256),
              name.utf8.count <= 1024, mime.utf8.count <= 255,
              !name.contains("\0"), !mime.contains("\0"),
              (4096...Self.maximumBytes).contains(size),
              AnyNativeCreationIdentity.isHex(contentSHA256, count: 64) else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        let specification: AnyJSON = .object([
            "ownerObjectId": .string(ownerObjectID), "name": .string(name),
            "mime": .string(mime), "size": .integer(size),
            "contentSHA256": .string(contentSHA256)
        ])
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(specification)
        self.binding = binding
        self.sourceKey = sourceKey
        self.intentID = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            "pinkha-native-prepared-migration-intent/v1", binding.workspace.accountID,
            binding.workspace.spaceID, binding.storeID, binding.planID, sourceKey, "file"
        ]))
        self.ownerObjectID = ownerObjectID
        self.name = name
        self.mime = mime
        self.size = size
        self.contentSHA256 = contentSHA256
        self.specBytes = bytes
        self.specSHA256 = AnyContentDigest.sha256(bytes)
    }

    var prepareBody: AnyJSON { .object([
        "contract": .string(AnyNativePreparedFileMigration.contract),
        "storeId": .string(binding.storeID), "planId": .string(binding.planID),
        "planSHA256": .string(binding.planSHA256), "sourceKey": .string(sourceKey),
        "specSHA256": .string(specSHA256), "specBase64": .string(specBytes.base64EncodedString())
    ]) }
}

/// This capability describes the separate streamed full-tier native route.
/// Generic auto-ID migration and variants remain separate contracts.
public struct AnyPreparedFileCapabilities: Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let storeID: String
    public let maximumBytes: Int64
    public let networkVerified: Bool

    init(_ value: AnyJSON, workspace: AnyTorahWorkspace) throws {
        guard value["contract"]?.string == AnyNativePreparedFileMigration.contract,
              value["accountId"]?.string == workspace.accountID,
              value["spaceId"]?.string == workspace.spaceID,
              let storeID = value["storeId"]?.string,
              AnyPreparedMigrationPlanBinding.validOpaque(storeID, maximum: 256),
              value["preparedFile"]?.integer == 1,
              value["maximumBytes"]?.integer == Int64(AnyPreparedFileIntent.maximumBytes),
              value["file"]?.integer == 0,
              let networkVerified = value["networkVerified"]?.bool else {
            throw AnyPreparedMigrationError.unsupportedContract
        }
        self.workspace = workspace
        self.storeID = storeID
        self.maximumBytes = AnyPreparedFileIntent.maximumBytes
        self.networkVerified = networkVerified
    }
}

public struct AnyPreparedFileReceipt: Equatable, Sendable {
    public enum Stage: String, Sendable {
        case filePrepared = "file-prepared"
        case fileRootCommitted = "file-root-committed"
        case fileRowCommitted = "file-row-committed"
        case complete

        fileprivate var order: Int {
            switch self {
            case .filePrepared: 0
            case .fileRootCommitted: 1
            case .fileRowCommitted: 2
            case .complete: 3
            }
        }
    }

    public enum Outcome: String, Sendable {
        case prepared, committed, committedDeleted = "committed_deleted"
        case committedModified = "committed_modified", obsolete
    }

    public let intent: AnyPreparedFileIntent
    public let fingerprint: String
    public let stage: Stage
    public let outcome: Outcome
    /// The immutable payload root; the owning document is intent.ownerObjectID.
    public let objectID: String
    public let changeID: String
    public let fileID: String
    public let recordIDs: [String]
    public let rootCID: String
    public let localFileComplete: Bool
    public let networkVerified: Bool
    public var isCompleteAndCurrent: Bool { stage == .complete && outcome == .committed && localFileComplete }

    init(_ value: AnyJSON, intent: AnyPreparedFileIntent) throws {
        let binding = intent.binding
        guard value["contract"]?.string == AnyNativePreparedFileMigration.contract,
              value["intentId"]?.string == intent.intentID,
              value["storeId"]?.string == binding.storeID,
              value["accountId"]?.string == binding.workspace.accountID,
              value["spaceId"]?.string == binding.workspace.spaceID,
              value["planId"]?.string == binding.planID,
              value["planSHA256"]?.string == binding.planSHA256,
              value["sourceKey"]?.string == intent.sourceKey,
              value["kind"]?.string == "file",
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
              let rootCID = value["rootCid"]?.string, AnyEditorBlock.validID(rootCID),
              let localFileComplete = value["localFileComplete"]?.bool,
              let networkVerified = value["networkVerified"]?.bool,
              localFileComplete == (stage == .complete && outcome == .committed),
              let records = value["recordIds"]?.array,
              records == [.string(fileID)] else {
            throw AnyPreparedMigrationError.mismatchedReceipt
        }
        switch outcome {
        case .prepared:
            guard stage == .filePrepared || stage == .fileRootCommitted else { throw AnyPreparedMigrationError.mismatchedReceipt }
        case .committed, .committedDeleted, .committedModified:
            guard stage == .fileRowCommitted || stage == .complete else { throw AnyPreparedMigrationError.mismatchedReceipt }
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
        self.rootCID = rootCID
        self.localFileComplete = localFileComplete
        self.networkVerified = networkVerified
    }

    fileprivate func hasSameIdentity(as other: Self) -> Bool {
        intent == other.intent && fingerprint == other.fingerprint &&
        objectID == other.objectID && changeID == other.changeID &&
        fileID == other.fileID && recordIDs == other.recordIDs && rootCID == other.rootCID
    }
}

/// Access to the separate native file PREPARED ledger. Each native
/// stage keeps its original signed identity. An uncertain write is returned
/// to the caller; a later call reconciles status before attempting a next stage.
public actor AnyNativePreparedFileMigration {
    public static let contract = AnyNativePreparedMigration.contract
    public nonisolated let capabilities: AnyPreparedFileCapabilities
    public nonisolated var workspace: AnyTorahWorkspace { capabilities.workspace }
    private typealias Request = @Sendable (
        String, [String], AnyJSON?, @escaping @Sendable () async throws -> Void
    ) async throws -> AnyJSON
    private typealias FileRequest = @Sendable ([String], AnyJSON, URL, Int64, String, @escaping @Sendable () async throws -> Void) async throws -> AnyJSON
    private let request: Request
    private let fileRequest: FileRequest

    public static func open(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                            authorize: @escaping @Sendable () async throws -> Void) async throws -> Self {
        guard client.expectedAccountID == workspace.accountID else { throw AnyHostError.wrongWorkspace }
        let request: Request = { method, path, body, authorize in
            try await client.requestJSON(method: method, path: path, body: body,
                maximumResponseBytes: 65_536, authorize: authorize)
        }
        let value = try await request("GET", prefix(workspace) + ["file", "capabilities"], nil, authorize)
        try Task.checkCancellation()
        try await authorize()
        return Self(capabilities: try .init(value, workspace: workspace), request: request, fileRequest: { path, metadata, file, size, digest, authorize in
            try await client.prepareMigrationFileJSON(path: path, metadata: metadata, fileURL: file, size: size, contentSHA256: digest, authorize: authorize)
        })
    }

    /// Internal injection keeps transport controls separate from native proof.
    init(capabilities: AnyPreparedFileCapabilities,
         request: @escaping @Sendable (String, [String], AnyJSON?,
             @escaping @Sendable () async throws -> Void) async throws -> AnyJSON,
         fileRequest: @escaping @Sendable ([String], AnyJSON, URL, Int64, String, @escaping @Sendable () async throws -> Void) async throws -> AnyJSON) {
        self.capabilities = capabilities
        self.request = request
        self.fileRequest = fileRequest
    }

    private static func prefix(_ workspace: AnyTorahWorkspace) -> [String] {
        ["v1", "spaces", workspace.spaceID, "pinkha", "migration"]
    }

    private func path(_ intent: AnyPreparedFileIntent) -> [String] {
        Self.prefix(workspace) + ["intents", intent.intentID, "file"]
    }

    private func check(_ intent: AnyPreparedFileIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard intent.binding.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        guard intent.binding.storeID == capabilities.storeID else { throw AnyPreparedMigrationError.changedStore }
        try Task.checkCancellation()
        try await authorize()
        let current = try AnyPreparedFileCapabilities(
            await request("GET", Self.prefix(workspace) + ["file", "capabilities"], nil, authorize),
            workspace: workspace)
        guard current.storeID == capabilities.storeID else { throw AnyPreparedMigrationError.changedStore }
        try Task.checkCancellation()
        try await authorize()
    }

    public func prepare(_ intent: AnyPreparedFileIntent, fileURL: URL,
                        authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedFileReceipt {
        try await check(intent, authorize: authorize)
        do {
            let known = try await request("GET", path(intent), nil, authorize)
            try await authorize()
            try Task.checkCancellation()
            return try .init(known, intent: intent)
        } catch AnyEngineError.http(status: 404, code: "pinkha.migration_not_found") {
            // Only an exact native not-found permits another prepare attempt.
        }
        let value = try await fileRequest(path(intent) + ["prepare"], intent.prepareBody, fileURL, intent.size, intent.contentSHA256, authorize)
        try await authorize()
        try Task.checkCancellation()
        return try .init(value, intent: intent)
    }

    public func status(_ intent: AnyPreparedFileIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedFileReceipt {
        try await check(intent, authorize: authorize)
        let value = try await request("GET", path(intent), nil, authorize)
        try await authorize()
        try Task.checkCancellation()
        return try .init(value, intent: intent)
    }

    public func commit(_ prepared: AnyPreparedFileReceipt,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedFileReceipt {
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
        for _ in 0..<3 {
            if current.isCompleteAndCurrent { return current }
            guard current.outcome == .prepared || current.outcome == .committed else {
                throw AnyPreparedMigrationError.terminalOutcome(current.outcome.rawValue)
            }
            try await check(intent, authorize: authorize)
            let value = try await request("POST", path(intent) + ["commit"], body, authorize)
            try await authorize()
            try Task.checkCancellation()
            let next = try AnyPreparedFileReceipt(value, intent: intent)
            guard next.hasSameIdentity(as: current) else { throw AnyPreparedMigrationError.changedIntent }
            guard next.outcome == .prepared || next.outcome == .committed else {
                throw AnyPreparedMigrationError.terminalOutcome(next.outcome.rawValue)
            }
            guard next.stage.order > current.stage.order else { throw AnyPreparedMigrationError.incompleteCommit }
            current = next
        }
        guard current.isCompleteAndCurrent else { throw AnyPreparedMigrationError.incompleteCommit }
        return current
    }
}
