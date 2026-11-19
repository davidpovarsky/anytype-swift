import Foundation
import PinkhaKit
import PinkhaAnyEngine

/// Explicit ownership of new-engine data. This is never inferred from a Heart
/// object ID or a currently displayed Heart document.
public struct AnyTorahWorkspace: Codable, Hashable, Sendable {
    public let accountID: String
    public let spaceID: String

    public init(accountID: String, spaceID: String) throws {
        guard !accountID.isEmpty, !spaceID.isEmpty,
              accountID.utf8.count <= 1024, spaceID.utf8.count <= 1024,
              !accountID.utf8.contains(0), !spaceID.utf8.contains(0) else {
            throw AnyEngineError.invalidIdentity("workspace")
        }
        self.accountID = accountID
        self.spaceID = spaceID
    }

    private enum CodingKeys: String, CodingKey { case accountID, spaceID }

    public init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(accountID: container.decode(String.self, forKey: .accountID),
                      spaceID: container.decode(String.self, forKey: .spaceID))
    }
}

public enum AnyTorahTargetIntent: Sendable { case read, write }

public protocol AnyTorahTargetAccess: Sendable {
    var workspace: AnyTorahWorkspace { get }
    func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) async throws
}

public protocol AnyTorahOperationStore: Sendable {
    var workspace: AnyTorahWorkspace { get }
    func snapshot() async throws -> AnyTorahProjection
    func append(_ operation: AnyTorahOperation,
                authorize: @escaping @Sendable () async throws -> Void) async throws
}

/// Concrete native Any storage. All canonical content remains in Any.
public struct AnyNativeTorahOperationStore: AnyTorahOperationStore, Sendable {
    public let workspace: AnyTorahWorkspace
    public let repository: AnyTorahClaimsRepository

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard client.expectedAccountID == workspace.accountID else {
            throw AnyEngineError.accountChanged
        }
        self.workspace = workspace
        repository = AnyTorahClaimsRepository(client: client, spaceID: workspace.spaceID)
    }

    public func snapshot() async throws -> AnyTorahProjection {
        try await repository.snapshot()
    }

    public func append(_ operation: AnyTorahOperation,
                       authorize: @escaping @Sendable () async throws -> Void) async throws {
        let result = try await repository.append(operation, authorize: authorize)
        guard !result.conflicted else {
            throw TorahAssociationRepositoryError.writeConflict(operation.logicalKey)
        }
    }
}

/// Fail-closed target and membership checks against Any v0.5.0.
///
/// These reads do not provide a transaction across the target object and the
/// operation carrier. The host still needs commit-time domain authority proof
/// before this path can replace the whole application's storage backend.
public struct AnyHTTPTorahTargetAccess: AnyTorahTargetAccess, Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient
    private let allowedTypeIDs: Set<String>
    private let excludedCollectionIDs: Set<String>
    private let blockLimit: Int
    public let editorDataset: String

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                allowedTypeIDs: Set<String>, excludedCollectionIDs: Set<String> = ["bin", "template"],
                blockLimit: Int = 10_000, editorDataset: String = "editor_blocks") throws {
        guard client.expectedAccountID == workspace.accountID, !allowedTypeIDs.isEmpty,
              allowedTypeIDs.allSatisfy({ !$0.isEmpty }),
              (1...10_000).contains(blockLimit), !editorDataset.isEmpty,
              editorDataset.utf8.count <= 1024, !editorDataset.utf8.contains(0) else {
            throw AnyEngineError.invalidIdentity("target validation configuration")
        }
        self.client = client
        self.workspace = workspace
        self.allowedTypeIDs = allowedTypeIDs
        self.excludedCollectionIDs = excludedCollectionIDs
        self.blockLimit = blockLimit
        self.editorDataset = editorDataset
    }

    public func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) async throws {
        try Task.checkCancellation()
        guard !target.objectId.isEmpty, target.blockId?.isEmpty != true else {
            throw TorahAssociationRepositoryError.targetNotFound
        }
        let base = ["v1", "spaces", workspace.spaceID]
        // members/me reads actual ACL; ownRole in the Space list is a mirror.
        let member = try await client.requestJSON(method: "GET", path: base + ["members", "me"])
        try Self.validateMember(member, workspace: workspace, intent: intent)
        let object = try await client.requestJSON(
            method: "GET", path: base + ["objects", target.objectId])
        try Self.validateObject(object, target: target, workspace: workspace,
                                allowedTypeIDs: allowedTypeIDs, excludedCollectionIDs: excludedCollectionIDs)
        guard let blockID = target.blockId else { return }
        let response = try await client.requestJSON(
            method: "POST", path: base + ["query"], body: .object([
                "objectId": .string(target.objectId), "dataset": .string(editorDataset),
                "limit": .integer(Int64(blockLimit + 1)), "includeTotal": .bool(true)
            ]))
        try Self.requireReachableBlock(blockID, response: response, limit: blockLimit)
    }

    public static func validateMember(_ member: AnyJSON, workspace: AnyTorahWorkspace,
                               intent: AnyTorahTargetIntent) throws {
        guard member["identity"]?.string == workspace.accountID,
              member["status"]?.string == "active",
              let permission = member["permission"]?.string else {
            throw TorahAssociationRepositoryError.permissionDenied
        }
        let permissions: Set<String>
        switch intent {
        case .read: permissions = ["owner", "admin", "writer", "reader"]
        case .write: permissions = ["owner", "admin", "writer"]
        }
        guard permissions.contains(permission) else {
            throw TorahAssociationRepositoryError.permissionDenied
        }
    }

    static func validateObject(_ object: AnyJSON, target: TorahAssociationTarget,
                               workspace: AnyTorahWorkspace, allowedTypeIDs: Set<String>,
                               excludedCollectionIDs: Set<String>) throws {
        guard object["objectId"]?.string == target.objectId,
              let record = object["record"], record["id"]?.string == target.objectId,
              record["spaceId"]?.string == workspace.spaceID,
              let typeID = record["any"]?["type"]?.string,
              allowedTypeIDs.contains(typeID) else {
            throw TorahAssociationRepositoryError.targetNotFound
        }
        // Fresh native page records omit any.collections when empty.
        // A present value must still have the documented array shape.
        let collections: [AnyJSON]
        if let value = record["any"]?["collections"] {
            guard let array = value.array else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
            collections = array
        } else { collections = [] }
        guard collections.allSatisfy({ $0.string != nil }),
              Set(collections.compactMap(\.string)).isDisjoint(with: excludedCollectionIDs) else {
            throw TorahAssociationRepositoryError.targetNotFound
        }
    }

    static func requireReachableBlock(_ blockID: String, response: AnyJSON, limit blockLimit: Int) throws {
        guard let records = response["records"]?.array,
              let total = response["total"]?.integer, total >= 0,
              total == records.count, total <= blockLimit,
              response["hasNext"]?.bool == false else {
            throw AnyEngineError.readLimit
        }
        // Existence alone is insufficient: deleted parents can leave orphans.
        var parents: [String: String] = [:]
        for block in records {
            guard let id = block["id"]?.string, !id.isEmpty,
                  let parent = block["nav"]?["parentId"]?.string,
                  parents[id] == nil else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
            parents[id] = parent
        }
        var cursor = blockID
        var visited = Set<String>()
        while !cursor.isEmpty {
            guard visited.insert(cursor).inserted, let parent = parents[cursor] else {
                throw TorahAssociationRepositoryError.targetNotFound
            }
            cursor = parent
        }
    }
}
