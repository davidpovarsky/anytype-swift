
import Foundation
import PinkhaAnyEngine

/// The expected version belongs to the prepared domain mutation, not a later
/// refresh performed by a transport adapter immediately before an unsafe write.
public protocol AnyHierarchyConditionalRecordStore: AnyHierarchyRecordStore {
    func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
               expectedVersion: AnyJSON,
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
              value["conditionalPropertiesSet"]?.integer == 1 else {
            throw AnyEngineError.incompatibleSchema("conditional hierarchy properties unavailable")
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

    /// Calling the unguarded protocol method is an integration error, never a fallback.
    public func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
                      authorize: @escaping @Sendable () async throws -> Void) async throws {
        throw AnyEngineError.incompatibleSchema("native hierarchy patch requires captured _ver")
    }

    public func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
                      expectedVersion: AnyJSON,
                      authorize: @escaping @Sendable () async throws -> Void) async throws {
        try AnyHierarchyNativeVersion.validate(expectedVersion)
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
            body: .object(["patch": .object(values), "ifVersion": expectedVersion,
                           "ifStartedAt": .string(engineStartedAt)]),
            authorize: {
                try await authorize()
                try await validateMembership(intent: .write)
            })
        try await requireRun()
    }

    /// Archive and recovery preserve every other collection membership and use
    /// the complete captured row version. The native route holds current writer
    /// and definition authority through the durable write, including exact noops.
    /// Folder removal is still a recoverable sequence across separate objects.
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
        guard let values = row["any"]?["collections"]?.array,
              values.allSatisfy({ $0.string.map(AnyHierarchySchema.validID) == true }),
              Set(values.compactMap(\.string)).count == values.count,
              values.contains(.string(schema.collectionID)),
              !values.contains(.string("template")),
              let expectedVersion = row["_ver"] else {
            throw AnyHierarchyError.malformedRow(objectID)
        }
        try AnyHierarchyNativeVersion.validate(expectedVersion)
        var memberships = values
        if archived {
            if !memberships.contains(.string("bin")) { memberships.append(.string("bin")) }
        } else {
            memberships.removeAll { $0 == .string("bin") }
        }
        _ = try await client.requestJSON(method: "POST",
            path: ["v1", "spaces", workspace.spaceID, "pinkha", "properties", objectID, "set", "any"],
            body: .object(["patch": .object(["collections": .array(memberships)]),
                           "ifVersion": expectedVersion, "ifStartedAt": .string(engineStartedAt)]),
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
