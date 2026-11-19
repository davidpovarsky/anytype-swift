import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativeCreationError: Error, Equatable, Sendable {
    case invalidIntent
    case contentConflict
    case journalUnavailable
    case corruptJournal
    case journalFull
    case writeUncertain
    case createdObjectIncomplete(String)
}

/// No user title/body enters the metadata journal, only its typed fingerprint.
public struct AnyNativeCreationIdentity: Codable, Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let mutationID: String
    public let kind: String
    public let fingerprint: String
    public var key: String {
        AnyContentDigest.sha256(Data(
            [workspace.accountID, workspace.spaceID, kind, mutationID]
                .map { "\($0.utf8.count):\($0)" }.joined(separator: "|").utf8))
    }
    public init(workspace: AnyTorahWorkspace, mutationID: String,
                kind: String, fingerprint: String) throws {
        guard Self.isHex(mutationID, count: 32), Self.isHex(fingerprint, count: 64),
              ["object", "editorBlock"].contains(kind) else { throw AnyNativeCreationError.invalidIntent }
        self.workspace = workspace; self.mutationID = mutationID
        self.kind = kind; self.fingerprint = fingerprint
    }
    private enum CodingKeys: String, CodingKey { case workspace, mutationID, kind, fingerprint }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(workspace: c.decode(AnyTorahWorkspace.self, forKey: .workspace),
            mutationID: c.decode(String.self, forKey: .mutationID),
            kind: c.decode(String.self, forKey: .kind), fingerprint: c.decode(String.self, forKey: .fingerprint))
    }
    static func isHex(_ value: String, count: Int) -> Bool {
        value.utf8.count == count && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
}

public struct AnyNativeObjectCreationIntent: Codable, Equatable, Sendable {
    public let workspace: AnyTorahWorkspace
    public let mutationID: String
    public let typeID: String
    public let collections: [String]
    public let initialProperties: AnyJSON
    public let fingerprint: String
    public var identity: AnyNativeCreationIdentity {
        // Every field is checked at construction/decoding.
        try! .init(workspace: workspace, mutationID: mutationID, kind: "object", fingerprint: fingerprint)
    }
    public init(workspace: AnyTorahWorkspace, mutationID: String, typeID: String,
                collections: [String] = [], initialProperties: AnyJSON) throws {
        guard AnyNativeCreationIdentity.isHex(mutationID, count: 32),
              AnyEditorBlock.validID(typeID), collections.count <= 128,
              collections.allSatisfy(AnyEditorBlock.validID),
              Set(collections).count == collections.count,
              let groups = initialProperties.object,
              groups.values.allSatisfy({ $0.object != nil }),
              initialProperties["any"]?["type"] == nil,
              initialProperties["any"]?["collections"] == nil else {
            throw AnyNativeCreationError.invalidIntent
        }
        let collections = collections.sorted()
        let canonical: AnyJSON = .object([
            "domain": .string("pinkha-any-object-intent/v1"),
            "account": .string(workspace.accountID), "space": .string(workspace.spaceID),
            "mutationID": .string(mutationID), "type": .string(typeID),
            "collections": .array(collections.map(AnyJSON.string)), "properties": initialProperties])
        self.fingerprint = AnyContentDigest.sha256(try AnyHostCanonical.bytes(canonical))
        self.workspace = workspace; self.mutationID = mutationID; self.typeID = typeID
        self.collections = collections; self.initialProperties = initialProperties
    }
    private enum CodingKeys: String, CodingKey {
        case workspace, mutationID, typeID, collections, initialProperties, fingerprint
    }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(workspace: c.decode(AnyTorahWorkspace.self, forKey: .workspace),
            mutationID: c.decode(String.self, forKey: .mutationID),
            typeID: c.decode(String.self, forKey: .typeID),
            collections: c.decode([String].self, forKey: .collections),
            initialProperties: c.decode(AnyJSON.self, forKey: .initialProperties))
        guard try c.decode(String.self, forKey: .fingerprint) == fingerprint else {
            throw AnyNativeCreationError.contentConflict
        }
    }
    var body: AnyJSON { .object(["type": .string(typeID),
        "collections": .array(collections.map(AnyJSON.string)), "initialProperties": initialProperties]) }
}

public enum AnyNativeCreationState: Codable, Equatable, Sendable {
    case reserved
    case created(String)
    case verified(String)
    public var objectID: String? {
        switch self { case .reserved: nil; case .created(let id), .verified(let id): id }
    }
}
public struct AnyNativeCreationReservation: Sendable {
    public let state: AnyNativeCreationState
    public let ownsDispatch: Bool
    public init(state: AnyNativeCreationState, ownsDispatch: Bool) {
        self.state = state; self.ownsDispatch = ownsDispatch
    }
}

/// One durable owner per account/Space. Reserve is persisted before dispatch;
/// unknown dispatch is retained, never converted to a fresh-object retry.
public protocol AnyNativeCreationJournaling: Sendable {
    var workspace: AnyTorahWorkspace { get }
    func reserve(_ identity: AnyNativeCreationIdentity) async throws -> AnyNativeCreationReservation
    func record(_ state: AnyNativeCreationState, identity: AnyNativeCreationIdentity) async throws
    func lookup(_ identity: AnyNativeCreationIdentity) async throws -> AnyNativeCreationState?
}

public actor AnyNativeObjectCreator {
    public nonisolated let workspace: AnyTorahWorkspace
    private let journal: any AnyNativeCreationJournaling
    private let dispatch: @Sendable (AnyNativeObjectCreationIntent, @escaping @Sendable () async throws -> Void) async throws -> String
    private let inspect: @Sendable (String) async throws -> AnyJSON

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                journal: any AnyNativeCreationJournaling) throws {
        guard client.expectedAccountID == workspace.accountID, journal.workspace == workspace else {
            throw AnyHostError.wrongWorkspace
        }
        self.workspace = workspace; self.journal = journal
        self.dispatch = { intent, authorize in
            let value = try await client.requestJSON(method: "POST",
                path: ["v1", "spaces", workspace.spaceID, "objects"],
                body: intent.body, authorize: authorize)
            let id = try value.requireString("objectId")
            guard AnyEditorBlock.validID(id) else { throw AnyNativeCreationError.writeUncertain }
            return id
        }
        self.inspect = { id in
            let value = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", workspace.spaceID, "objects", id])
            guard value["objectId"]?.string == id, let record = value["record"],
                  record["id"]?.string == id, record["spaceId"]?.string == workspace.spaceID else {
                throw AnyNativeCreationError.createdObjectIncomplete(id)
            }
            return record
        }
    }

    /// Injection for crash/cancellation contracts; production uses native HTTP.
    init(workspace: AnyTorahWorkspace, journal: any AnyNativeCreationJournaling,
         dispatch: @escaping @Sendable (AnyNativeObjectCreationIntent, @escaping @Sendable () async throws -> Void) async throws -> String,
         inspect: @escaping @Sendable (String) async throws -> AnyJSON) {
        self.workspace = workspace; self.journal = journal; self.dispatch = dispatch; self.inspect = inspect
    }

    public func recordedObjectID(for intent: AnyNativeObjectCreationIntent) async throws -> String? {
        guard intent.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        return try await journal.lookup(intent.identity)?.objectID
    }

    public func ensureObject(_ intent: AnyNativeObjectCreationIntent,
        authorize: @escaping @Sendable () async throws -> Void,
        onNativeConfirmed: @escaping @Sendable (String) async throws -> Void = { _ in }
    ) async throws -> String {
        guard intent.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        try Task.checkCancellation()
        try await authorize()
        let reservation = try await journal.reserve(intent.identity)
        if !reservation.ownsDispatch, reservation.state == .reserved {
            throw AnyNativeCreationError.writeUncertain
        }
        let journal = journal, dispatch = dispatch, inspect = inspect
        // Await this worker even if the caller is cancelled. Its session lease
        // must not drain until the original native/SDK receipts are persisted.
        let fence = AnyCreationDispatchFence()
        let id = try await withTaskCancellationHandler {
          let worker = Task.detached { () async throws -> String in
            let id: String
            var state = reservation.state
            if reservation.ownsDispatch {
                do {
                    id = try await dispatch(intent) {
                        try fence.check()
                        try await authorize()
                        try fence.beginDispatch()
                    }
                }
                catch { throw AnyNativeCreationError.writeUncertain }
                guard AnyEditorBlock.validID(id) else { throw AnyNativeCreationError.writeUncertain }
                try await journal.record(.created(id), identity: intent.identity)
                state = .created(id)
            } else {
                guard let recorded = state.objectID else { throw AnyNativeCreationError.writeUncertain }
                id = recorded
            }
            let record = try await inspect(id)
            guard record["any"]?["type"]?.string == intent.typeID,
                  record["any"]?["collections"] == nil || record["any"]?["collections"]?.array != nil else {
                throw AnyNativeCreationError.createdObjectIncomplete(id)
            }
            let collections = record["any"]?["collections"]?.array ?? []
            guard collections.allSatisfy({ $0.string != nil }),
                  !collections.contains(.string("template")) || intent.collections.contains("template"),
                  !collections.contains(.string("bin")),
                  Set(intent.collections).isSubset(of: Set(collections.compactMap(\.string))) else {
                throw AnyNativeCreationError.createdObjectIncomplete(id)
            }
            if case .created = state {
                guard Self.containsExpected(record, expected: intent.initialProperties) else {
                    throw AnyNativeCreationError.createdObjectIncomplete(id)
                }
                try await journal.record(.verified(id), identity: intent.identity)
            }
            // The callback refines the ORIGINAL Hanlin receipt before revocation
            // can suppress caller delivery; no additional approval is consumed.
            try await onNativeConfirmed(id)
            return id
        }
          return try await worker.value
        } onCancel: { fence.revoke() }
        try Task.checkCancellation()
        try await authorize()
        return id
    }

    static func containsExpected(_ actual: AnyJSON, expected: AnyJSON) -> Bool {
        if let object = expected.object {
            guard actual.object != nil else { return false }
            return object.allSatisfy { key, value in
                guard let candidate = actual[key] else { return false }
                return containsExpected(candidate, expected: value)
            }
        }
        return actual == expected
    }
}


// The lock covers the synchronous cancellation/dispatch fence only. Native
// dispatch is never cancelled after this boundary; its original receipt settles.
final class AnyCreationDispatchFence: @unchecked Sendable {
    private let lock = NSLock()
    private var cancelled = false
    private var dispatched = false
    func revoke() { lock.withLock { cancelled = true } }
    func check() throws {
        try lock.withLock { if cancelled { throw CancellationError() } }
    }
    func beginDispatch() throws {
        try lock.withLock {
            guard !cancelled, !dispatched else { throw CancellationError() }
            dispatched = true
        }
    }
}
