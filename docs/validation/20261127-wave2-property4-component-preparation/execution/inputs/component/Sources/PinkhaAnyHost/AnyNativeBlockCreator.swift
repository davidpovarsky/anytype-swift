
import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public struct AnyNativeBlockCreationIntent: Codable, Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let mutationID: String
    public let objectID: String
    public let dataset: String
    public let type: String
    public let text: String
    public let style: AnyJSON
    public let parentID: String
    public let position: String
    public let fingerprint: String

    public var identity: AnyNativeCreationIdentity {
        try! .init(workspace: workspace, mutationID: mutationID, kind: "editorBlock", fingerprint: fingerprint)
    }

    public init(workspace: AnyTorahWorkspace, mutationID: String, objectID: String,
                dataset: String = "editor_blocks", type: String, text: String,
                style: AnyJSON = .object([:]), parentID: String = "", position: String) throws {
        guard AnyNativeCreationIdentity.isHex(mutationID, count: 32),
              AnyEditorBlock.validID(objectID), AnyEditorBlock.validID(dataset),
              parentID.utf8.count <= 256,
              parentID.isEmpty || AnyEditorBlock.validID(parentID),
              ["paragraph", "heading", "quote", "code", "list_item", "check_list_item"].contains(type),
              text.utf8.count <= 65_536, style.object != nil,
              !position.isEmpty, position.utf8.count <= 256,
              position.utf8.allSatisfy({ $0 >= 33 && $0 <= 126 && $0 != 34 && $0 != 92 }) else {
            throw AnyNativeCreationError.invalidIntent
        }
        let value: AnyJSON = .object([
            "domain": .string("pinkha-any-block-intent/v1"),
            "account": .string(workspace.accountID), "space": .string(workspace.spaceID),
            "mutationID": .string(mutationID), "objectID": .string(objectID),
            "dataset": .string(dataset), "type": .string(type), "text": .string(text),
            "style": style, "parentID": .string(parentID), "position": .string(position)])
        self.fingerprint = AnyContentDigest.sha256(try AnyHostCanonical.bytes(value, maximumBytes: 131_072))
        self.workspace = workspace; self.mutationID = mutationID; self.objectID = objectID
        self.dataset = dataset; self.type = type; self.text = text; self.style = style
        self.parentID = parentID; self.position = position
    }

    private enum CodingKeys: String, CodingKey {
        case workspace, mutationID, objectID, dataset, type, text, style, parentID, position, fingerprint
    }

    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(workspace: c.decode(AnyTorahWorkspace.self, forKey: .workspace),
            mutationID: c.decode(String.self, forKey: .mutationID),
            objectID: c.decode(String.self, forKey: .objectID),
            dataset: c.decode(String.self, forKey: .dataset), type: c.decode(String.self, forKey: .type),
            text: c.decode(String.self, forKey: .text), style: c.decode(AnyJSON.self, forKey: .style),
            parentID: c.decode(String.self, forKey: .parentID), position: c.decode(String.self, forKey: .position))
        guard try c.decode(String.self, forKey: .fingerprint) == fingerprint else {
            throw AnyNativeCreationError.contentConflict
        }
    }

    var body: AnyJSON { .object([
        "type": .string(type), "text": .string(text), "style": style,
        "nav": .object(["parentId": .string(parentID), "pos": .string(position)])]) }
}

/// Uses the exact same per-workspace protected journal as native object creation.
/// A lost auto-ID reply remains uncertain; no content search guesses ownership.
public actor AnyNativeBlockCreator {
    public nonisolated let workspace: AnyTorahWorkspace
    private let journal: any AnyNativeCreationJournaling
    private let dispatch: @Sendable (AnyNativeBlockCreationIntent, @escaping @Sendable () async throws -> Void) async throws -> String
    private let inspect: @Sendable (AnyNativeBlockCreationIntent, String) async throws -> AnyJSON
    private let validateCreation: @Sendable (AnyNativeBlockCreationIntent) async throws -> Void

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                journal: any AnyNativeCreationJournaling, allowedTypeIDs: Set<String>,
                documentTypePolicy: AnyTorahDocumentPolicy = .explicitTypeAllowlist) throws {
        guard client.expectedAccountID == workspace.accountID, journal.workspace == workspace else {
            throw AnyHostError.wrongWorkspace
        }
        self.workspace = workspace; self.journal = journal
        self.validateCreation = { intent in
            let capabilities = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"])
            guard capabilities["contract"]?.string == "pinkha-torah-native-v1",
                  capabilities["currentWriterBlockCreate"]?.integer == 1 else {
                throw AnyEngineError.incompatibleSchema("current-writer native block creation unavailable")
            }
            let access = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace,
                allowedTypeIDs: allowedTypeIDs, editorDataset: intent.dataset,
                documentTypePolicy: documentTypePolicy)
            try await access.validate(.object(objectId: intent.objectID), intent: .write)
            if !intent.parentID.isEmpty {
                try await access.validate(.block(objectId: intent.objectID, blockId: intent.parentID), intent: .write)
            }
        }
        self.dispatch = { intent, authorize in
            let value = try await client.requestJSON(method: "POST",
                path: ["v1", "spaces", workspace.spaceID, "pinkha", "objects", intent.objectID,
                       "editor", intent.dataset, "blocks"],
                body: intent.body, authorize: authorize)
            guard let ids = value["recordIds"]?.array, ids.count == 1,
                  let id = ids.first?.string, AnyEditorBlock.validID(id) else {
                throw AnyNativeCreationError.writeUncertain
            }
            return id
        }
        self.inspect = { intent, id in
            let access = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace,
                allowedTypeIDs: allowedTypeIDs, editorDataset: intent.dataset,
                documentTypePolicy: documentTypePolicy)
            try await access.validate(.block(objectId: intent.objectID, blockId: id), intent: .read)
            let value = try await client.requestJSON(method: "POST", path: ["v1", "spaces", workspace.spaceID, "query"],
                body: .object(["objectId": .string(intent.objectID), "dataset": .string(intent.dataset),
                    "filter": .object(["id": .string(id)]), "limit": .integer(2), "includeTotal": .bool(true)]))
            guard value["total"]?.integer == 1, value["hasNext"]?.bool == false,
                  let rows = value["records"]?.array, rows.count == 1, let row = rows.first,
                  row["id"]?.string == id else { throw AnyNativeCreationError.createdObjectIncomplete(id) }
            return row
        }
    }

    init(workspace: AnyTorahWorkspace, journal: any AnyNativeCreationJournaling,
         dispatch: @escaping @Sendable (AnyNativeBlockCreationIntent, @escaping @Sendable () async throws -> Void) async throws -> String,
         inspect: @escaping @Sendable (AnyNativeBlockCreationIntent, String) async throws -> AnyJSON,
         validateCreation: @escaping @Sendable (AnyNativeBlockCreationIntent) async throws -> Void = { _ in }) {
        self.workspace = workspace; self.journal = journal; self.dispatch = dispatch; self.inspect = inspect
        self.validateCreation = validateCreation
    }

    public func recordedBlockID(for intent: AnyNativeBlockCreationIntent) async throws -> String? {
        guard intent.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        return try await journal.lookup(intent.identity)?.objectID
    }

    public func ensureBlock(_ intent: AnyNativeBlockCreationIntent,
        authorize: @escaping @Sendable () async throws -> Void,
        onNativeConfirmed: @escaping @Sendable (String) async throws -> Void = { _ in }
    ) async throws -> String {
        guard intent.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        try Task.checkCancellation(); try await authorize()
        // A known unsupported contract or denied target must not reserve an
        // intent that was never eligible for dispatch.
        try await validateCreation(intent)
        try Task.checkCancellation(); try await authorize()
        let reservation = try await journal.reserve(intent.identity)
        if !reservation.ownsDispatch, reservation.state == .reserved {
            throw AnyNativeCreationError.writeUncertain
        }
        let journal = journal, dispatch = dispatch, inspect = inspect, validateCreation = validateCreation
        let fence = AnyCreationDispatchFence()
        let id = try await withTaskCancellationHandler {
            let worker = Task.detached { () async throws -> String in
                let id: String
                var state = reservation.state
                if reservation.ownsDispatch {
                    do {
                        id = try await dispatch(intent) {
                            try fence.check()
                            try await validateCreation(intent)
                            try await authorize(); try fence.beginDispatch()
                        }
                    } catch { throw AnyNativeCreationError.writeUncertain }
                    guard AnyEditorBlock.validID(id) else { throw AnyNativeCreationError.writeUncertain }
                    do { try await journal.record(.created(id), identity: intent.identity) }
                    catch { throw AnyNativeCreationError.createdObjectIncomplete(id) }
                    state = .created(id)
                } else {
                    guard let recorded = state.objectID else { throw AnyNativeCreationError.writeUncertain }
                    id = recorded
                }
                do {
                    let row = try await inspect(intent, id)
                    guard row["id"]?.string == id, row["type"]?.string == intent.type else {
                        throw AnyNativeCreationError.createdObjectIncomplete(id)
                    }
                    if case .created = state {
                        var expected = intent.body.object!
                        if intent.style.object?.isEmpty == true { expected.removeValue(forKey: "style") }
                        // Native creation omits an exactly empty text field.
                        // Only absence has that meaning; null and other values
                        // must still match the original intent exactly.
                        if intent.text.isEmpty, row["text"] == nil {
                            expected.removeValue(forKey: "text")
                        }
                        guard AnyNativeObjectCreator.containsExpected(row, expected: .object(expected)) else {
                            throw AnyNativeCreationError.createdObjectIncomplete(id)
                        }
                        try await journal.record(.verified(id), identity: intent.identity)
                    }
                    try await onNativeConfirmed(id)
                } catch {
                    // The native reply already identified this exact block.
                    // Preserve that ID even if later journal/readback/callback
                    // work fails; uncertainty never permits a fresh-ID retry.
                    throw AnyNativeCreationError.createdObjectIncomplete(id)
                }
                return id
            }
            return try await worker.value
        } onCancel: { fence.revoke() }
        try Task.checkCancellation(); try await authorize()
        return id
    }
}
