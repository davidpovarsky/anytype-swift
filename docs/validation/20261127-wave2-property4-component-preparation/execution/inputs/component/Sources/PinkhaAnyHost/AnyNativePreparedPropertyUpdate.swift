import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// One immutable SET patch after destination object identities are known.
/// The sequence is read from the same native store before the first preparation;
/// a retry must retain this intent, including its original sequence and bytes.
public struct AnyPreparedPropertyUpdateIntent: Equatable, Sendable {
    public static let maximumPatchKeys = 128
    public let binding: AnyPreparedMigrationPlanBinding
    public let sourceKey: String
    public let objectID: String
    public let ownerID: String
    public let expectedApplySequence: Int64
    public let patchKeyCount: Int
    public let intentID: String
    public let specBytes: Data
    public let specSHA256: String

    public init(binding: AnyPreparedMigrationPlanBinding, sourceKey: String,
                objectID: String, ownerID: String, patch: [String: AnyJSON],
                expectedApplySequence: Int64) throws {
        guard AnyPreparedMigrationPlanBinding.validOpaque(sourceKey, maximum: 4096),
              AnyEditorBlock.validID(objectID), objectID.utf8.count <= 256,
              Self.validField(ownerID), expectedApplySequence > 0,
              !patch.isEmpty, patch.count <= Self.maximumPatchKeys else {
            throw AnyPreparedMigrationError.invalidBinding
        }
        for (key, value) in patch {
            guard Self.validField(key), value != .null,
                  !(ownerID == "any" && ["type", "collections", "template"].contains(key)) else {
                throw AnyPreparedMigrationError.invalidBinding
            }
        }
        let specification: AnyJSON = .object([
            "objectId": .string(objectID), "ownerId": .string(ownerID), "patch": .object(patch),
            "expectedApplySeq": .integer(expectedApplySequence)
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(specification)
        guard bytes.count <= 256 * 1024 else { throw AnyPreparedMigrationError.invalidBinding }
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        self.binding = binding; self.sourceKey = sourceKey; self.objectID = objectID
        self.ownerID = ownerID; self.expectedApplySequence = expectedApplySequence
        self.patchKeyCount = patch.count; self.specBytes = bytes
        self.specSHA256 = AnyContentDigest.sha256(bytes)
        self.intentID = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            "pinkha-native-prepared-migration-intent/v1", binding.workspace.accountID,
            binding.workspace.spaceID, binding.storeID, binding.planID, sourceKey, "propertyUpdate"
        ]))
    }

    private static func validField(_ value: String) -> Bool {
        AnyEditorBlock.validID(value) && value.utf8.count <= 256 && !value.contains(".")
    }

    var prepareBody: AnyJSON { .object([
        "contract": .string(AnyNativePreparedPropertyUpdate.contract),
        "storeId": .string(binding.storeID), "planId": .string(binding.planID),
        "planSHA256": .string(binding.planSHA256), "sourceKey": .string(sourceKey),
        "specSHA256": .string(specSHA256), "specBase64": .string(specBytes.base64EncodedString())
    ]) }
}

public struct AnyPreparedPropertyUpdateCapabilities: Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let storeID: String
    public let maximumPatchKeys: Int
    public let networkVerified: Bool

    init(_ value: AnyJSON, workspace: AnyTorahWorkspace) throws {
        guard value["contract"]?.string == AnyNativePreparedPropertyUpdate.contract,
              value["accountId"]?.string == workspace.accountID,
              value["spaceId"]?.string == workspace.spaceID,
              let storeID = value["storeId"]?.string,
              AnyPreparedMigrationPlanBinding.validOpaque(storeID, maximum: 256),
              value["propertyUpdate"]?.integer == 1,
              let bound = value["maxPatchKeys"]?.integer,
              bound > 0, bound <= AnyPreparedPropertyUpdateIntent.maximumPatchKeys,
              let networkVerified = value["networkVerified"]?.bool else {
            throw AnyPreparedMigrationError.unsupportedContract
        }
        self.workspace = workspace; self.storeID = storeID
        self.maximumPatchKeys = Int(bound); self.networkVerified = networkVerified
    }
}

public struct AnyPreparedPropertyUpdateReceipt: Equatable, Sendable {
    public enum Stage: String, Sendable { case prepared = "properties-prepared", complete }
    public typealias Outcome = AnyPreparedMigrationReceipt.Outcome
    public let intent: AnyPreparedPropertyUpdateIntent
    public let fingerprint: String
    public let stage: Stage
    public let outcome: Outcome
    public let objectID: String
    public let changeID: String
    public let recordIDs: [String]
    public var isCompleteAndCurrent: Bool { stage == .complete && outcome == .committed }

    init(_ value: AnyJSON, intent: AnyPreparedPropertyUpdateIntent) throws {
        let binding = intent.binding
        guard value["contract"]?.string == AnyNativePreparedPropertyUpdate.contract,
              value["intentId"]?.string == intent.intentID,
              value["storeId"]?.string == binding.storeID,
              value["accountId"]?.string == binding.workspace.accountID,
              value["spaceId"]?.string == binding.workspace.spaceID,
              value["planId"]?.string == binding.planID,
              value["planSHA256"]?.string == binding.planSHA256,
              value["sourceKey"]?.string.map({ Data($0.utf8) }) == Data(intent.sourceKey.utf8),
              value["kind"]?.string == "propertyUpdate",
              value["specSHA256"]?.string == intent.specSHA256,
              let fingerprint = value["fingerprint"]?.string,
              AnyNativeCreationIdentity.isHex(fingerprint, count: 64),
              let rawStage = value["stage"]?.string, let stage = Stage(rawValue: rawStage),
              let rawOutcome = value["outcome"]?.string, let outcome = Outcome(rawValue: rawOutcome),
              let objectID = value["objectId"]?.string,
              Data(objectID.utf8) == Data(intent.objectID.utf8),
              let changeID = value["changeId"]?.string, AnyEditorBlock.validID(changeID),
              let records = value["recordIds"]?.array, records.count == 1,
              records[0].string.map({ Data($0.utf8) }) == Data(intent.objectID.utf8) else {
            throw AnyPreparedMigrationError.mismatchedReceipt
        }
        let committed = [.committed, .committedDeleted, .committedModified].contains(outcome)
        guard (stage == .complete) == committed else { throw AnyPreparedMigrationError.mismatchedReceipt }
        self.intent = intent; self.fingerprint = fingerprint; self.stage = stage; self.outcome = outcome
        self.objectID = objectID; self.changeID = changeID; self.recordIDs = [objectID]
    }
}

/// Resumes the same signed native SET. No retry refreshes the expected revision,
/// creates replacement objects, or overwrites terminally changed/deleted fields.
public actor AnyNativePreparedPropertyUpdate {
    public static let contract = "pinkha-native-prepared-property-update-v1"
    public nonisolated let capabilities: AnyPreparedPropertyUpdateCapabilities
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
        let value = try await request("GET", prefix(workspace) + ["property-update", "capabilities"], nil, authorize)
        try Task.checkCancellation(); try await authorize()
        return Self(capabilities: try .init(value, workspace: workspace), request: request)
    }

    init(capabilities: AnyPreparedPropertyUpdateCapabilities,
         request: @escaping @Sendable (String, [String], AnyJSON?,
             @escaping @Sendable () async throws -> Void) async throws -> AnyJSON) {
        self.capabilities = capabilities; self.request = request
    }

    private static func prefix(_ workspace: AnyTorahWorkspace) -> [String] {
        ["v1", "spaces", workspace.spaceID, "pinkha", "migration"]
    }

    private func check(_ intent: AnyPreparedPropertyUpdateIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard intent.binding.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        guard intent.binding.storeID == capabilities.storeID else { throw AnyPreparedMigrationError.changedStore }
        try Task.checkCancellation(); try await authorize()
        let current = try AnyPreparedPropertyUpdateCapabilities(
            await request("GET", Self.prefix(workspace) + ["property-update", "capabilities"], nil, authorize),
            workspace: workspace)
        guard current.storeID == capabilities.storeID else { throw AnyPreparedMigrationError.changedStore }
        guard intent.patchKeyCount <= current.maximumPatchKeys else { throw AnyPreparedMigrationError.unsupportedContract }
        try Task.checkCancellation(); try await authorize()
    }

    public func prepare(_ intent: AnyPreparedPropertyUpdateIntent,
                        authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedPropertyUpdateReceipt {
        try await check(intent, authorize: authorize)
        let value = try await request("PUT", Self.prefix(workspace) +
            ["intents", intent.intentID, "property-update", "prepare"], intent.prepareBody, authorize)
        try await authorize(); try Task.checkCancellation()
        return try .init(value, intent: intent)
    }

    public func status(_ intent: AnyPreparedPropertyUpdateIntent,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedPropertyUpdateReceipt {
        try await check(intent, authorize: authorize)
        let value = try await request("GET", Self.prefix(workspace) + ["intents", intent.intentID, "property-update"], nil, authorize)
        try await authorize(); try Task.checkCancellation()
        return try .init(value, intent: intent)
    }

    public func commit(_ prepared: AnyPreparedPropertyUpdateReceipt,
                       authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyPreparedPropertyUpdateReceipt {
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
        let value = try await request("POST", Self.prefix(workspace) +
            ["intents", intent.intentID, "property-update", "commit"], body, authorize)
        try await authorize(); try Task.checkCancellation()
        let next = try AnyPreparedPropertyUpdateReceipt(value, intent: intent)
        try Self.compare(current, next)
        if next.outcome == .prepared { throw AnyPreparedMigrationError.incompleteCommit }
        guard next.isCompleteAndCurrent else { throw AnyPreparedMigrationError.terminalOutcome(next.outcome.rawValue) }
        return next
    }

    private static func compare(_ previous: AnyPreparedPropertyUpdateReceipt,
                                _ current: AnyPreparedPropertyUpdateReceipt) throws {
        guard previous.fingerprint == current.fingerprint,
              Data(previous.changeID.utf8) == Data(current.changeID.utf8),
              previous.stage != .complete || current.stage == .complete else {
            throw AnyPreparedMigrationError.changedIntent
        }
    }
}
