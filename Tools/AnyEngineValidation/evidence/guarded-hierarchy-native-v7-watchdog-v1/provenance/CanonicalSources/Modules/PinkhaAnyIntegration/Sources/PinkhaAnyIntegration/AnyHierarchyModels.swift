import Foundation
import PinkhaKit
import PinkhaAnyEngine

public enum AnyHierarchyError: Error, Sendable, Equatable {
    case malformedRow(String)
    case incompatibleSchema
    case stalePlan(String)
    case unsupportedChild(String)
    case cyclicParent(String)
    case incompleteWrite(String)
}

public struct AnyHierarchySchema: Codable, Sendable, Equatable {
    public static let bundleID = "system:wiki/v1"
    public let collectionID: String
    public let parentPropertyID: String
    public let positionPropertyID: String
    public let folderPropertyID: String

    public init(collectionID: String, parentPropertyID: String,
                positionPropertyID: String, folderPropertyID: String) throws {
        let values = [collectionID, parentPropertyID, positionPropertyID, folderPropertyID]
        guard values.allSatisfy(Self.validID),
              Set([parentPropertyID, positionPropertyID, folderPropertyID]).count == 3 else {
            throw AnyHierarchyError.incompatibleSchema
        }
        self.collectionID = collectionID
        self.parentPropertyID = parentPropertyID
        self.positionPropertyID = positionPropertyID
        self.folderPropertyID = folderPropertyID
    }

    private enum CodingKeys: String, CodingKey {
        case collectionID, parentPropertyID, positionPropertyID, folderPropertyID
    }
    public init(from decoder: any Decoder) throws {
        let value = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(collectionID: value.decode(String.self, forKey: .collectionID),
                      parentPropertyID: value.decode(String.self, forKey: .parentPropertyID),
                      positionPropertyID: value.decode(String.self, forKey: .positionPropertyID),
                      folderPropertyID: value.decode(String.self, forKey: .folderPropertyID))
    }
    static func validID(_ id: String) -> Bool {
        !id.isEmpty && id.utf8.count <= 1024 && !id.utf8.contains(0)
    }
}

public struct AnyHierarchyItem: Sendable, Equatable {
    public let objectID: String
    public let typeID: String
    public let title: String
    public let parentID: String?
    public let position: String
    public let kind: PinkhaHierarchyNodeKind
}

public struct AnyHierarchyIssue: Sendable, Equatable {
    public enum Kind: String, Sendable { case missingParent, cycle }
    public let objectID: String
    public let kind: Kind
}

/// Complete native wiki rows, with the existing Pinkha tree as a derived view.
/// Unknown properties stay in native records; legacy numeric order is presentation
/// only. A malformed supported row fails rather than becoming an empty tree.
public struct AnyHierarchySnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let schema: AnyHierarchySchema
    public let items: [AnyHierarchyItem]
    public let itemsByID: [String: AnyHierarchyItem]
    public let nativeRows: [String: AnyJSON]
    public let tree: PinkhaHierarchySnapshot
    public let issues: [AnyHierarchyIssue]

    public init(workspace: AnyTorahWorkspace, schema: AnyHierarchySchema, rows: [AnyJSON],
                allowedTypeIDs: Set<String>, excludedObjectIDs: Set<String> = [],
                maximumNodes: Int = 10_000) throws {
        guard !allowedTypeIDs.isEmpty, (1...10_000).contains(maximumNodes),
              rows.count <= maximumNodes else { throw AnyEngineError.readLimit }
        var native: [String: AnyJSON] = [:]
        var items: [AnyHierarchyItem] = []
        for row in rows {
            guard let id = row["id"]?.string, AnyHierarchySchema.validID(id), native[id] == nil,
                  row["spaceId"]?.string == workspace.spaceID,
                  let type = row["any"]?["type"]?.string,
                  let collections = row["any"]?["collections"]?.array,
                  collections.allSatisfy({ $0.string != nil }),
                  collections.contains(.string(schema.collectionID)),
                  !collections.contains(.string("bin")),
                  !collections.contains(.string("template")) else {
                throw AnyHierarchyError.malformedRow(row["id"]?.string ?? "")
            }
            native[id] = row
            guard let values = row[schema.collectionID],
                  let parent = values[schema.parentPropertyID]?.string,
                  let position = values[schema.positionPropertyID]?.string,
                  AnyLexicographicPosition.isValid(position),
                  let folder = values[schema.folderPropertyID]?.bool,
                  parent.isEmpty || AnyHierarchySchema.validID(parent),
                  row["any"]?["name"] == nil || row["any"]?["name"]?.string != nil else {
                throw AnyHierarchyError.malformedRow(id)
            }
            guard allowedTypeIDs.contains(type), !excludedObjectIDs.contains(id) else { continue }
            let title = row["any"]?["name"]?.string ?? ""
            items.append(.init(objectID: id, typeID: type, title: title,
                               parentID: parent.isEmpty ? nil : parent, position: position,
                               kind: folder ? .folder : .writingDocument))
        }
        items.sort { $0.position == $1.position ? $0.objectID < $1.objectID : $0.position < $1.position }
        let byID = Dictionary(uniqueKeysWithValues: items.map { ($0.objectID, $0) })
        var issues: [AnyHierarchyIssue] = []
        for item in items {
            var cursor = item.objectID
            var visited = Set<String>()
            while let current = byID[cursor], let parent = current.parentID {
                guard visited.insert(cursor).inserted else {
                    issues.append(.init(objectID: item.objectID, kind: .cycle)); break
                }
                guard byID[parent] != nil else {
                    issues.append(.init(objectID: item.objectID, kind: .missingParent)); break
                }
                cursor = parent
                // The original builder is recursive. Refuse an adversarially deep
                // tree before invoking it rather than risking the UI stack.
                guard visited.count <= 512 else { throw AnyEngineError.readLimit }
            }
        }
        let raw = items.enumerated().map { offset, item in
            PinkhaHierarchyRawItem(objectId: item.objectID, typeId: item.typeID, title: item.title,
                                   parentId: item.parentID, order: Double(offset), kind: item.kind)
        }
        self.workspace = workspace
        self.schema = schema
        self.items = items
        self.itemsByID = byID
        self.nativeRows = native
        self.tree = PinkhaHierarchyBuilder.build(items: raw)
        self.issues = issues
    }

    public func children(of parentID: String?) -> [AnyHierarchyItem] {
        items.filter { $0.parentID == parentID }
    }

    func validateMove(objectID: String, parentID: String?) throws {
        try PinkhaHierarchyMutationValidator.validateMove(
            objectId: objectID, newParentId: parentID, in: tree)
        var cursor = parentID
        var visited = Set<String>()
        while let id = cursor {
            guard id != objectID else {
                throw PinkhaHierarchyError.cycleDetected(objectId: objectID, targetParentId: parentID ?? "")
            }
            guard visited.insert(id).inserted else { throw AnyHierarchyError.cyclicParent(id) }
            guard let item = itemsByID[id] else { throw PinkhaHierarchyError.parentNotFound(parentId: id) }
            cursor = item.parentID
        }
    }
}

public struct AnyHierarchyCreationPlan: Codable, Sendable, Equatable {
    public let workspace: AnyTorahWorkspace
    public let mutationID: String
    public let schema: AnyHierarchySchema
    public let typeID: String
    public let title: String
    public let parentID: String?
    public let position: String
    public let kind: PinkhaHierarchyNodeKind

    public init(workspace: AnyTorahWorkspace,
                mutationID: String = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                schema: AnyHierarchySchema, typeID: String, title: String,
                parentID: String?, position: String, kind: PinkhaHierarchyNodeKind) throws {
        guard mutationID.utf8.count == 32,
              mutationID.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
              AnyHierarchySchema.validID(typeID), parentID.map(AnyHierarchySchema.validID) ?? true,
              title.utf8.count <= 4096, !title.utf8.contains(0),
              AnyLexicographicPosition.isValid(position) else {
            throw AnyEngineError.invalidIdentity("hierarchy creation plan")
        }
        self.workspace = workspace; self.mutationID = mutationID; self.schema = schema
        self.typeID = typeID; self.title = title; self.parentID = parentID
        self.position = position; self.kind = kind
    }
    public var collections: [String] { [schema.collectionID] }
    public var initialProperties: AnyJSON {
        .object(["any": .object(["name": .string(title)]),
                 schema.collectionID: .object([
                    schema.parentPropertyID: .string(parentID ?? ""),
                    schema.positionPropertyID: .string(position),
                    schema.folderPropertyID: .bool(kind == .folder)])])
    }
    public var fingerprint: String {
        let parts = ["pinkha-any-hierarchy-create-v1", workspace.accountID, workspace.spaceID,
                     mutationID, schema.collectionID, schema.parentPropertyID, schema.positionPropertyID,
                     schema.folderPropertyID, typeID, title, parentID ?? "", position, kind.rawValue]
        return AnyContentDigest.sha256(Data(parts.map { "\($0.utf8.count):\($0)" }.joined(separator: "|").utf8))
    }
    private enum CodingKeys: String, CodingKey {
        case workspace, mutationID, schema, typeID, title, parentID, position, kind
    }
    public init(from decoder: any Decoder) throws {
        let value = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(workspace: value.decode(AnyTorahWorkspace.self, forKey: .workspace),
                      mutationID: value.decode(String.self, forKey: .mutationID),
                      schema: value.decode(AnyHierarchySchema.self, forKey: .schema),
                      typeID: value.decode(String.self, forKey: .typeID),
                      title: value.decode(String.self, forKey: .title),
                      parentID: value.decodeIfPresent(String.self, forKey: .parentID),
                      position: value.decode(String.self, forKey: .position),
                      kind: value.decode(PinkhaHierarchyNodeKind.self, forKey: .kind))
    }
}

/// Host delegates this to its single durable native object-creation journal.
/// Unknown dispatch is retained and must never become a fresh-ID retry.
public protocol AnyHierarchyObjectCreating: Sendable {
    var workspace: AnyTorahWorkspace { get }
    func ensureHierarchyObject(plan: AnyHierarchyCreationPlan,
                               authorize: @escaping @Sendable () async throws -> Void) async throws -> String
}

/// Native _ver is a recursively nested field-version tree, not a timestamp or
/// a flat map. Treat it as an opaque exact fence after validating its shape.
enum AnyHierarchyNativeVersion {
    static func validate(_ version: AnyJSON) throws {
        var nodes = 0
        func visit(_ value: AnyJSON, depth: Int) throws {
            nodes += 1
            guard nodes <= 4096, depth <= 64 else { throw AnyEngineError.readLimit }
            switch value {
            case .string(let stamp):
                guard !stamp.isEmpty, stamp.utf8.count <= 1024, !stamp.utf8.contains(0) else {
                    throw AnyHierarchyError.incompatibleSchema
                }
            case .object(let map):
                guard !map.isEmpty else { throw AnyHierarchyError.incompatibleSchema }
                for (key, child) in map {
                    guard !key.isEmpty, key.utf8.count <= 1024, !key.utf8.contains(0) else {
                        throw AnyHierarchyError.incompatibleSchema
                    }
                    try visit(child, depth: depth + 1)
                }
            default: throw AnyHierarchyError.incompatibleSchema
            }
        }
        try visit(version, depth: 0)
    }
}

public struct AnyHierarchyPlacementPlan: Codable, Sendable, Equatable {
    public let workspace: AnyTorahWorkspace
    public let schema: AnyHierarchySchema
    public let objectID: String
    public let previousParentID: String?
    public let previousPosition: String
    public let expectedVersion: AnyJSON
    public let parentID: String?
    public let position: String

    public init(workspace: AnyTorahWorkspace, schema: AnyHierarchySchema, objectID: String,
                previousParentID: String?, previousPosition: String, expectedVersion: AnyJSON,
                parentID: String?, position: String) throws {
        guard AnyHierarchySchema.validID(objectID),
              [previousParentID, parentID].allSatisfy({ $0.map(AnyHierarchySchema.validID) ?? true }),
              AnyLexicographicPosition.isValid(previousPosition),
              AnyLexicographicPosition.isValid(position) else {
            throw AnyEngineError.invalidIdentity("hierarchy placement plan")
        }
        try AnyHierarchyNativeVersion.validate(expectedVersion)
        self.expectedVersion = expectedVersion
        self.workspace = workspace; self.schema = schema; self.objectID = objectID
        self.previousParentID = previousParentID; self.previousPosition = previousPosition
        self.parentID = parentID; self.position = position
    }
    private enum CodingKeys: String, CodingKey {
        case workspace, schema, objectID, previousParentID, previousPosition, expectedVersion, parentID, position
    }
    public init(from decoder: any Decoder) throws {
        let value = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(workspace: value.decode(AnyTorahWorkspace.self, forKey: .workspace),
                      schema: value.decode(AnyHierarchySchema.self, forKey: .schema),
                      objectID: value.decode(String.self, forKey: .objectID),
                      previousParentID: value.decodeIfPresent(String.self, forKey: .previousParentID),
                      previousPosition: value.decode(String.self, forKey: .previousPosition),
                      expectedVersion: value.decode(AnyJSON.self, forKey: .expectedVersion),
                      parentID: value.decodeIfPresent(String.self, forKey: .parentID),
                      position: value.decode(String.self, forKey: .position))
    }
}

public struct AnyHierarchyRemovalReceipt: Sendable {
    public let folderID: String
    public let reparentedIDs: [String]
    public let folderArchived: Bool?
    public let complete: Bool
    public let recoveryError: (any Error)?
    /// Per-object native writes and final reads; no cross-object atomicity claim.
    public let atomicAcrossObjects = false
}
