import Foundation
import PinkhaAnyEngine

/// Native writes must retain the reviewed record fence and original engine run.
public protocol AnyHierarchyConditionalRecordStore: AnyHierarchyRecordStore {
    var engineStartedAt: String { get }
    func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
               fence: AnyConditionalPropertyFence,
               authorize: @escaping @Sendable () async throws -> Void) async throws
}

/// Native hierarchy writes use the dedicated guarded route. Stock Any cannot
/// silently ignore these preconditions because it has no such route.
public struct AnyGuardedHTTPHierarchyRecordStore: AnyHierarchyObservableRecordStore,
                                                AnyHierarchyConditionalRecordStore, Sendable {
    public let workspace: AnyTorahWorkspace
    public let schema: AnyHierarchySchema
    public let engineStartedAt: String
    private let client: AnyHTTPClient
    private let reader: AnyHTTPHierarchyRecordStore

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace, schema: AnyHierarchySchema,
                engineStartedAt: String, maximumNodes: Int = 10_000) throws {
        guard !engineStartedAt.isEmpty, engineStartedAt.utf8.count <= 256 else {
            throw AnyEngineError.invalidIdentity("native hierarchy run")
        }
        self.reader = try .init(client: client, workspace: workspace, schema: schema, maximumNodes: maximumNodes)
        self.workspace = workspace; self.schema = schema
        self.engineStartedAt = engineStartedAt; self.client = client
    }

    public func verifyCapabilities() async throws {
        try await requireRun()
        let value = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"])
        guard value["contract"]?.string == "pinkha-torah-native-v1",
              value["conditionalPropertiesSet"]?.integer == 1,
              value["conditionalPropertiesApplySeq"]?.integer == 1 else {
            throw AnyEngineError.incompatibleSchema("conditional hierarchy property fence unavailable")
        }
        try await requireRun()
    }

    public func validateMembership(intent: AnyTorahTargetIntent) async throws {
        try await requireRun()
        try await reader.validateMembership(intent: intent)
        try await requireRun()
    }

    public func readRows() async throws -> [AnyJSON] {
        try await requireRun()
        let value = try await reader.readRows()
        try await requireRun(); return value
    }

    public func readObject(objectID: String) async throws -> AnyJSON {
        try await requireRun()
        let value = try await reader.readObject(objectID: objectID)
        try await requireRun(); return value
    }

    /// Calling either legacy method is an integration error, never a fallback.
    public func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
                      authorize: @escaping @Sendable () async throws -> Void) async throws {
        throw AnyEngineError.incompatibleSchema("native hierarchy patch requires captured property fence")
    }

    public func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
                      expectedVersion: AnyJSON,
                      authorize: @escaping @Sendable () async throws -> Void) async throws {
        throw AnyEngineError.incompatibleSchema("native hierarchy patch requires captured property fence")
    }

    public func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
                      fence: AnyConditionalPropertyFence,
                      authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard fence.engineStartedAt == engineStartedAt else {
            throw AnyHierarchyError.stalePlan(objectID)
        }
        guard !values.isEmpty, AnyHierarchySchema.validID(objectID) else { throw AnyHierarchyError.incompatibleSchema }
        let supported: Set<String>
        if ownerID == schema.collectionID {
            supported = [schema.parentPropertyID, schema.positionPropertyID, schema.folderPropertyID]
        } else if ownerID == "any" { supported = ["name"] }
        else { throw AnyHierarchyError.incompatibleSchema }
        guard Set(values.keys).isSubset(of: supported) else { throw AnyHierarchyError.incompatibleSchema }
        try await verifyCapabilities()
        let actualSchema = try await AnyHTTPHierarchyRecordStore.readSchema(client: client, workspace: workspace)
        guard actualSchema == schema else { throw AnyHierarchyError.incompatibleSchema }
        _ = try await client.requestJSON(method: "POST",
            path: ["v1", "spaces", workspace.spaceID, "pinkha", "properties", objectID, "set", ownerID],
            body: fence.requestBody(patch: values),
            authorize: {
                try await authorize()
                try await validateMembership(intent: .write)
            })
        try await requireRun()
    }

    /// Archive and recovery preserve ordered memberships and the exact captured
    /// row fence. An identical retry still reaches native current-writer and
    /// definition checks, using its explicit no-history contract.
    /// Folder removal remains a recoverable sequence across separate objects.
    public func setArchived(objectID: String, archived: Bool,
                            authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard AnyHierarchySchema.validID(objectID) else {
            throw AnyEngineError.invalidIdentity("hierarchy object")
        }
        try await authorize()
        try await verifyCapabilities()
        let capabilities = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"])
        guard capabilities["conditionalMembershipSet"]?.integer == 1 else {
            throw AnyEngineError.incompatibleSchema("conditional hierarchy membership unavailable")
        }
        let actualSchema = try await AnyHTTPHierarchyRecordStore.readSchema(client: client, workspace: workspace)
        guard actualSchema == schema else { throw AnyHierarchyError.incompatibleSchema }
        try await validateMembership(intent: .write)
        let row = try await readObject(objectID: objectID)
        let request = try AnyHierarchyArchiveRequest(record: row, objectID: objectID,
            workspace: workspace, schema: schema, archived: archived,
            engineStartedAt: engineStartedAt, capabilities: capabilities)
        _ = try await client.requestJSON(method: "POST", path: request.path, body: request.body,
            authorize: {
                try await requireRun()
                try await authorize()
                try await validateMembership(intent: .write)
            })
        try await requireRun()
    }

    public func watch(session: AnyStreamSession) async throws -> AsyncThrowingStream<AnyQueryUpdate, Error> {
        try await requireRun()
        return try await reader.watch(session: session)
    }

    private func requireRun() async throws {
        let health = try await client.requestJSON(method: "GET", path: ["v1", "health"])
        guard health["status"]?.string == "ok",
              health["account"]?.string == workspace.accountID,
              health["startedAt"]?.string == engineStartedAt else {
            throw AnyEngineError.incompatibleSchema("native hierarchy engine run changed")
        }
    }
}
