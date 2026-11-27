import Foundation

/// Native link-index reads are computed snapshots, never writable SDK properties.
/// Record/property selection preserves the source identity instead of flattening
/// a block link or a property-value link into an object-level relation.
public enum AnyNativeLinkSelection: Sendable {
    case object
    case record(dataset: String, recordID: String)
    case property(String)
    case dataset(String)
}

public struct AnyNativeLinkSource: Sendable {
    public let spaceID: String
    public let objectID: String
    public let dataset: String
    public let recordID: String
    public let typeID: String?
    public let field: String?
}

public struct AnyNativeLinkTarget: Sendable {
    public enum Kind: String, Sendable { case object = "o", property = "p", identity = "u", file = "f" }
    public let uri: String
    public let kind: Kind
    public let spaceID: String?
    public let objectID: String?
    public let dataset: String?
    public let recordID: String?
    public let propID: String?
    public let identity: String?
    public let fileID: String?
    public var isPart: Bool { kind == .property || recordID != nil }
}

public struct AnyNativeObjectLink: Sendable {
    public let source: AnyNativeLinkSource
    /// Open native slug set: mention/link/card/embed/relation and future slugs.
    public let kind: String
    public let target: AnyNativeLinkTarget
}

public struct AnyNativeLinksSnapshot: Sendable {
    public let accountID: String
    public let spaceID: String
    public let objectID: String
    public let selection: AnyNativeLinkSelection
    public let links: [AnyNativeObjectLink]
    public let truncated: Bool
}

public struct AnyNativeBacklinksSnapshot: Sendable {
    public let accountID: String
    public let spaceID: String
    public let objectID: String
    public let selection: AnyNativeLinkSelection
    public let object: [AnyNativeObjectLink]
    public let parts: [AnyNativeObjectLink]
    public let truncated: Bool
}

/// Account-scoped, read-only adapter for Any's existing native link index.
/// The native index is device-local: an empty snapshot does not prove that an
/// object exists, or that another device has delivered every change. Native
/// index.disabled and permission errors propagate. No account-wide read or
/// implicit cross-space access is introduced.
public struct AnyNativeObjectLinks: Sendable {
    private let client: AnyHTTPClient
    public init(client: AnyHTTPClient) { self.client = client }

    /// One optional edge-kind filter. Omit it to retain every native edge kind.
    /// Native caps reads at 500 and has no continuation; the default rejects a
    /// truncated response instead of presenting it as a complete migration.
    public func links(
        spaceID: String, objectID: String, selection: AnyNativeLinkSelection = .object,
        kind: String? = nil, limit: Int = 500, requireComplete: Bool = true,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyNativeLinksSnapshot {
        let query = try Self.query(spaceID: spaceID, objectID: objectID,
                                   selection: selection, kind: kind, limit: limit, incoming: false)
        let body = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", spaceID, "objects", objectID, "links"],
            query: query, maximumResponseBytes: 16 << 20, authorize: authorize)
        let snapshot = try Self.decodeLinks(body, accountID: client.expectedAccountID,
            spaceID: spaceID, objectID: objectID, selection: selection, kind: kind,
            limit: limit, requireComplete: requireComplete)
        try await client.checkAccount()
        try await authorize()
        try Task.checkCancellation()
        return snapshot
    }

    /// For an object read, object and parts are disjoint native groups. For a
    /// record/property read, object contains that exact part and parts is empty.
    public func backlinks(
        spaceID: String, objectID: String, selection: AnyNativeLinkSelection = .object,
        kind: String? = nil, limit: Int = 500, requireComplete: Bool = true,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyNativeBacklinksSnapshot {
        let query = try Self.query(spaceID: spaceID, objectID: objectID,
                                   selection: selection, kind: kind, limit: limit, incoming: true)
        let body = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", spaceID, "objects", objectID, "backlinks"],
            query: query, maximumResponseBytes: 16 << 20, authorize: authorize)
        let snapshot = try Self.decodeBacklinks(body, accountID: client.expectedAccountID,
            spaceID: spaceID, objectID: objectID, selection: selection, kind: kind,
            limit: limit, requireComplete: requireComplete)
        try await client.checkAccount()
        try await authorize()
        try Task.checkCancellation()
        return snapshot
    }

    static func query(spaceID: String, objectID: String, selection: AnyNativeLinkSelection,
                      kind: String?, limit: Int, incoming: Bool) throws -> [String: String] {
        guard validID(spaceID), validID(objectID) else { throw AnyEngineError.invalidIdentity("link scope") }
        guard (1...500).contains(limit), kind.map(validKind) ?? true else {
            throw AnyEngineError.invalidOperation("link read bounds")
        }
        var query = ["limit": String(limit)]
        if let kind { query["kind"] = kind }
        switch selection {
        case .object: break
        case let .record(dataset, recordID):
            guard validID(dataset), validID(recordID), !same(dataset, "prop") else {
                throw AnyEngineError.invalidOperation("link record selection")
            }
            query["dataset"] = dataset
            query["record"] = recordID
        case .property(let propID):
            guard validID(propID) else { throw AnyEngineError.invalidIdentity("link property") }
            query["prop"] = propID
        case .dataset(let dataset):
            guard !incoming, validID(dataset) else {
                throw AnyEngineError.invalidOperation("backlinks require a record or property")
            }
            query["dataset"] = dataset
        }
        return query
    }

    static func decodeLinks(_ body: AnyJSON, accountID: String, spaceID: String, objectID: String,
                            selection: AnyNativeLinkSelection, kind: String?, limit: Int,
                            requireComplete: Bool) throws -> AnyNativeLinksSnapshot {
        let edges = try array(body, "links")
        guard edges.count <= limit else { throw AnyEngineError.readLimit }
        let truncated = try truncation(body, requireComplete: requireComplete)
        for edge in edges {
            guard same(edge.source.spaceID, spaceID), same(edge.source.objectID, objectID),
                  sourceMatches(edge.source, selection), kind.map({ same($0, edge.kind) }) ?? true else {
                throw AnyEngineError.malformedResponse("link source scope")
            }
        }
        return AnyNativeLinksSnapshot(accountID: accountID, spaceID: spaceID, objectID: objectID,
                                      selection: selection, links: edges, truncated: truncated)
    }

    static func decodeBacklinks(_ body: AnyJSON, accountID: String, spaceID: String, objectID: String,
                                selection: AnyNativeLinkSelection, kind: String?, limit: Int,
                                requireComplete: Bool) throws -> AnyNativeBacklinksSnapshot {
        let objects = try array(body, "object")
        let parts = try array(body, "parts")
        guard objects.count + parts.count <= limit else { throw AnyEngineError.readLimit }
        let truncated = try truncation(body, requireComplete: requireComplete)
        for (isPartGroup, edges) in [(false, objects), (true, parts)] {
            for edge in edges {
                guard same(edge.source.spaceID, spaceID),
                      edge.target.spaceID.map({ same($0, spaceID) }) == true,
                      edge.target.objectID.map({ same($0, objectID) }) == true,
                      kind.map({ same($0, edge.kind) }) ?? true else {
                    throw AnyEngineError.malformedResponse("backlink scope")
                }
                switch selection {
                case .object:
                    guard edge.target.isPart == isPartGroup else {
                        throw AnyEngineError.malformedResponse("backlink object/part group")
                    }
                case .record(let dataset, let recordID):
                    guard !isPartGroup, edge.target.kind == .object,
                          edge.target.dataset.map({ same($0, dataset) }) == true,
                          edge.target.recordID.map({ same($0, recordID) }) == true else {
                        throw AnyEngineError.malformedResponse("backlink record selection")
                    }
                case .property(let propID):
                    guard !isPartGroup, edge.target.kind == .property,
                          edge.target.propID.map({ same($0, propID) }) == true else {
                        throw AnyEngineError.malformedResponse("backlink property selection")
                    }
                case .dataset: throw AnyEngineError.invalidOperation("backlinks require a record or property")
                }
            }
        }
        return AnyNativeBacklinksSnapshot(accountID: accountID, spaceID: spaceID, objectID: objectID,
            selection: selection, object: objects, parts: parts, truncated: truncated)
    }

    private static func array(_ body: AnyJSON, _ key: String) throws -> [AnyNativeObjectLink] {
        guard let values = body[key]?.array else { throw AnyEngineError.malformedResponse("link array " + key) }
        guard values.count <= 500 else { throw AnyEngineError.readLimit }
        return try values.map(decodeLink)
    }

    private static func decodeLink(_ value: AnyJSON) throws -> AnyNativeObjectLink {
        guard let source = value["source"], source.object != nil,
              let target = value["target"], target.object != nil else {
            throw AnyEngineError.malformedResponse("link edge")
        }
        let spaceID = try required(source, "spaceId")
        let objectID = try required(source, "objectId")
        let dataset = try source.requireString("dataset")
        let recordID = try source.requireString("recordId")
        guard (dataset.isEmpty || validID(dataset)), (recordID.isEmpty || validID(recordID)),
              dataset.isEmpty == recordID.isEmpty else {
            throw AnyEngineError.malformedResponse("link source record")
        }
        let typeID = try optional(source, "typeId")
        let field = try optional(source, "field")
        if typeID != nil && !same(dataset, "prop") {
            throw AnyEngineError.malformedResponse("link source declaring type")
        }
        let kind = try value.requireString("kind")
        guard validKind(kind) else { throw AnyEngineError.malformedResponse("link edge kind") }
        let rawKind = try target.requireString("kind")
        guard let targetKind = AnyNativeLinkTarget.Kind(rawValue: rawKind) else {
            throw AnyEngineError.incompatibleSchema("native link target kind")
        }
        let uri = try target.requireString("uri")
        let targetSpace = try optional(target, "spaceId")
        let targetObject = try optional(target, "objectId")
        let targetDataset = try optional(target, "dataset")
        let targetRecord = try optional(target, "recordId")
        let propID = try optional(target, "propId")
        let identity = try optional(target, "identity")
        let fileID = try optional(target, "fileId")
        let segments: [String]
        switch targetKind {
        case .object:
            guard let targetSpace, let targetObject, propID == nil, identity == nil, fileID == nil,
                  (targetDataset == nil) == (targetRecord == nil) else {
                throw AnyEngineError.malformedResponse("link object target")
            }
            segments = ["o", targetSpace, targetObject] + (targetDataset.map { [$0, targetRecord!] } ?? [])
        case .property:
            guard let targetSpace, let targetObject, let propID,
                  targetDataset == nil, targetRecord == nil, identity == nil, fileID == nil else {
                throw AnyEngineError.malformedResponse("link property target")
            }
            segments = ["p", targetSpace, targetObject, propID]
        case .identity:
            guard let identity, targetSpace == nil, targetObject == nil, targetDataset == nil,
                  targetRecord == nil, propID == nil, fileID == nil else {
                throw AnyEngineError.malformedResponse("link identity target")
            }
            segments = ["u", identity]
        case .file:
            guard let targetSpace, let fileID, targetObject == nil, targetDataset == nil,
                  targetRecord == nil, propID == nil, identity == nil else {
                throw AnyEngineError.malformedResponse("link file target")
            }
            segments = ["f", targetSpace, fileID]
        }
        guard same(uri, "any://" + segments.joined(separator: "/")) else {
            throw AnyEngineError.malformedResponse("link canonical URI differs")
        }
        return AnyNativeObjectLink(source: AnyNativeLinkSource(spaceID: spaceID, objectID: objectID,
            dataset: dataset, recordID: recordID, typeID: typeID, field: field), kind: kind,
            target: AnyNativeLinkTarget(uri: uri, kind: targetKind, spaceID: targetSpace,
                objectID: targetObject, dataset: targetDataset, recordID: targetRecord,
                propID: propID, identity: identity, fileID: fileID))
    }

    private static func sourceMatches(_ source: AnyNativeLinkSource,
                                      _ selection: AnyNativeLinkSelection) -> Bool {
        switch selection {
        case .object: return true
        case let .record(dataset, recordID): return same(source.dataset, dataset) && same(source.recordID, recordID)
        case .property(let propID): return same(source.dataset, "prop") && same(source.recordID, propID)
        case .dataset(let dataset): return same(source.dataset, dataset)
        }
    }

    private static func truncation(_ body: AnyJSON, requireComplete: Bool) throws -> Bool {
        let truncated: Bool
        if let value = body["truncated"] {
            guard let flag = value.bool else { throw AnyEngineError.malformedResponse("link truncation") }
            truncated = flag
        } else { truncated = false }
        if truncated && requireComplete { throw AnyEngineError.readLimit }
        return truncated
    }

    private static func required(_ value: AnyJSON, _ key: String) throws -> String {
        let result = try value.requireString(key)
        guard validID(result) else { throw AnyEngineError.malformedResponse("link identity " + key) }
        return result
    }

    private static func optional(_ value: AnyJSON, _ key: String) throws -> String? {
        guard let raw = value[key] else { return nil }
        guard let result = raw.string, validID(result) else {
            throw AnyEngineError.malformedResponse("link optional identity " + key)
        }
        return result
    }

    private static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 && value != "." && value != ".." &&
        value.utf8.allSatisfy { $0 > 32 && $0 != 127 && ![35, 37, 47, 63, 92].contains($0) }
    }
    private static func validKind(_ value: String) -> Bool {
        (1...64).contains(value.utf8.count) && value.utf8.allSatisfy {
            (97...122).contains($0) || (48...57).contains($0) || $0 == 45 || $0 == 95
        }
    }
    private static func same(_ left: String, _ right: String) -> Bool {
        left.utf8.elementsEqual(right.utf8)
    }
}
