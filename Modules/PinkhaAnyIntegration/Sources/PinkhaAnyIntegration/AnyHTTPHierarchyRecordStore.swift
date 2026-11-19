import Foundation
import PinkhaAnyEngine

public protocol AnyHierarchyRecordStore: Sendable {
    var workspace: AnyTorahWorkspace { get }
    var schema: AnyHierarchySchema { get }
    func validateMembership(intent: AnyTorahTargetIntent) async throws
    func readRows() async throws -> [AnyJSON]
    func readObject(objectID: String) async throws -> AnyJSON
    func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
               authorize: @escaping @Sendable () async throws -> Void) async throws
    func setArchived(objectID: String, archived: Bool,
                     authorize: @escaping @Sendable () async throws -> Void) async throws
}

public protocol AnyHierarchyObservableRecordStore: AnyHierarchyRecordStore {
    func watch(session: AnyStreamSession) async throws -> AsyncThrowingStream<AnyQueryUpdate, Error>
}

/// Uses the native wiki declaration and native object/property APIs. Opening a
/// reader never installs, repairs or rewrites a declaration.
public struct AnyHTTPHierarchyRecordStore: AnyHierarchyObservableRecordStore, Sendable {
    public let workspace: AnyTorahWorkspace
    public let schema: AnyHierarchySchema
    public let maximumNodes: Int
    private let client: AnyHTTPClient

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                schema: AnyHierarchySchema, maximumNodes: Int = 10_000) throws {
        guard client.expectedAccountID == workspace.accountID,
              (1...10_000).contains(maximumNodes) else {
            throw AnyEngineError.invalidIdentity("hierarchy workspace")
        }
        self.client = client; self.workspace = workspace; self.schema = schema
        self.maximumNodes = maximumNodes
    }

    public static func installWiki(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                                   authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyHierarchySchema {
        guard client.expectedAccountID == workspace.accountID else { throw AnyEngineError.accountChanged }
        _ = try await client.requestJSON(
            method: "POST", path: ["v1", "catalog", "wiki", "setup"],
            body: .object(["spaceId": .string(workspace.spaceID)]), authorize: {
                try await authorize()
                let membership = try await client.requestJSON(method: "GET",
                    path: ["v1", "spaces", workspace.spaceID, "members", "me"])
                try AnyHTTPTorahTargetAccess.validateMember(membership, workspace: workspace, intent: .write)
            })
        return try await readSchema(client: client, workspace: workspace)
    }

    public static func readSchema(client: AnyHTTPClient, workspace: AnyTorahWorkspace) async throws -> AnyHierarchySchema {
        guard client.expectedAccountID == workspace.accountID else { throw AnyEngineError.accountChanged }
        let base = ["v1", "spaces", workspace.spaceID]
        let response = try await client.requestJSON(method: "GET",
            path: base + ["bundles", AnyHierarchySchema.bundleID])
        guard let bundle = response["bundle"], bundle["id"]?.string == AnyHierarchySchema.bundleID,
              bundle["losers"]?.array?.isEmpty != false,
              let root = bundle["rootId"]?.string, AnyHierarchySchema.validID(root) else {
            throw AnyHierarchyError.incompatibleSchema
        }
        let definition = try await client.requestJSON(method: "GET", path: base + ["collections", root])
        let properties = try await client.requestJSON(method: "GET", path: base + ["collections", root, "properties"])
        return try verifySchema(rootID: root, definition: definition, properties: properties)
    }

    static func verifySchema(rootID: String, definition: AnyJSON, properties: AnyJSON) throws -> AnyHierarchySchema {
        guard definition["id"]?.string == rootID, definition["xKey"]?.string == "wiki",
              let properties = properties["properties"]?.array else { throw AnyHierarchyError.incompatibleSchema }
        var resolved: [String: String] = [:]
        for (key, kind) in [("parentId", "string"), ("pos", "string"), ("folder", "boolean")] {
            let matches = properties.filter { $0["xKey"]?.string == key }
            guard matches.count == 1, let property = matches.first,
                  let id = property["id"]?.string, AnyHierarchySchema.validID(id),
                  property["kind"]?.string == kind, property["scope"]?.string == "synced",
                  property["invalid"]?.bool != true,
                  kind != "string" || property["meta"]?["index"]?.string == "none" else {
                throw AnyHierarchyError.incompatibleSchema
            }
            resolved[key] = id
        }
        return try .init(collectionID: rootID, parentPropertyID: resolved["parentId"]!,
                         positionPropertyID: resolved["pos"]!, folderPropertyID: resolved["folder"]!)
    }

    public func validateMembership(intent: AnyTorahTargetIntent) async throws {
        let membership = try await client.requestJSON(method: "GET", path: base + ["members", "me"])
        try AnyHTTPTorahTargetAccess.validateMember(membership, workspace: workspace, intent: intent)
    }

    public func readRows() async throws -> [AnyJSON] {
        try await validateMembership(intent: .read)
        try await requireCurrentSchema()
        let result = try await client.requestJSON(method: "POST", path: base + ["objects", "query"], body: query)
        guard let rows = result["records"]?.array,
              let total = result["total"]?.integer,
              total >= 0, total == rows.count, total <= maximumNodes,
              result["hasNext"]?.bool == false else { throw AnyEngineError.readLimit }
        try await validateMembership(intent: .read)
        return rows
    }

    public func readObject(objectID: String) async throws -> AnyJSON {
        guard AnyHierarchySchema.validID(objectID) else { throw AnyEngineError.invalidIdentity("hierarchy object") }
        try await validateMembership(intent: .read)
        let response = try await client.requestJSON(method: "GET", path: base + ["objects", objectID])
        guard response["objectId"]?.string == objectID, let record = response["record"],
              record["id"]?.string == objectID, record["spaceId"]?.string == workspace.spaceID else {
            throw AnyHierarchyError.malformedRow(objectID)
        }
        return record
    }

    public func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
                      authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard !values.isEmpty, AnyHierarchySchema.validID(objectID) else { throw AnyHierarchyError.incompatibleSchema }
        let supported: Set<String>
        if ownerID == schema.collectionID {
            supported = [schema.parentPropertyID, schema.positionPropertyID, schema.folderPropertyID]
        } else if ownerID == "any" {
            supported = ["name"]
        } else { throw AnyHierarchyError.incompatibleSchema }
        guard Set(values.keys).isSubset(of: supported) else { throw AnyHierarchyError.incompatibleSchema }
        try await requireCurrentSchema()
        _ = try await client.requestJSON(method: "POST",
            path: base + ["properties", objectID, "set", ownerID],
            body: .object(["patch": .object(values)]), authorize: {
                try await authorize()
                try await validateMembership(intent: .write)
            })
    }

    public func setArchived(objectID: String, archived: Bool,
                            authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard AnyHierarchySchema.validID(objectID) else { throw AnyEngineError.invalidIdentity("hierarchy object") }
        _ = try await client.requestJSON(method: archived ? "POST" : "DELETE",
            path: base + ["properties", objectID, "collections", "bin"], authorize: {
                try await authorize()
                try await validateMembership(intent: .write)
            })
    }

    public func watch(session: AnyStreamSession) async throws -> AsyncThrowingStream<AnyQueryUpdate, Error> {
        try await validateMembership(intent: .read)
        try await requireCurrentSchema()
        return try await client.subscribeObjectQuery(
            spaceID: workspace.spaceID, query: query, streamSession: session,
            maximumRecords: maximumNodes, requireComplete: true)
    }

    private var base: [String] { ["v1", "spaces", workspace.spaceID] }
    private var query: AnyJSON {
        .object([
            "filter": .object(["$and": .array([
                .object(["any.collections": .string(schema.collectionID)]),
                .object(["any.collections": .object(["$nin": .array([.string("bin"), .string("template")])])])
            ])]),
            "sort": .array([.string(schema.collectionID + "." + schema.positionPropertyID), .string("id")]),
            "limit": .integer(Int64(maximumNodes + 1)), "includeTotal": .bool(true)
        ])
    }

    private func requireCurrentSchema() async throws {
        guard try await Self.readSchema(client: client, workspace: workspace) == schema else {
            throw AnyHierarchyError.incompatibleSchema
        }
    }
}
