import Foundation
import Crypto

public enum AnyContentDigest {
    public static func sha256(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
}

/// Identity is byte-compatible with the pinned T2 operation contract.
/// No trimming, normalization, locale conversion or payload parsing occurs here.
public struct AnyTorahOperation: Codable, Equatable, Sendable {
    public enum Kind: String, Codable, Sendable { case add, remove, replace }
    public let version: UInt32
    public let operationID: String
    public let spaceID: String
    public let authorID: String
    public let kind: Kind
    public let targetObjectID: String
    public let targetBlockID: String
    public let providerID: String
    public let canonicalRef: String
    public let payload: Data
    public let observed: [String]

    public init(
        operationID: String, spaceID: String, authorID: String, kind: Kind,
        targetObjectID: String, targetBlockID: String = "",
        providerID: String = "", canonicalRef: String = "",
        payload: Data = Data(), observed: [String] = []
    ) throws {
        guard Self.hex(operationID, count: 32) else {
            throw AnyEngineError.invalidOperation("operationID must be 32 lowercase hex characters")
        }
        for (key, value, bound, required) in [
            ("space", spaceID, 1024, true), ("author", authorID, 1024, true),
            ("object", targetObjectID, 1024, true), ("block", targetBlockID, 1024, false),
            ("provider", providerID, 256, kind != .remove),
            ("source", canonicalRef, 4096, kind != .remove)
        ] {
            guard (!required || !value.isEmpty), value.utf8.count <= bound,
                  !value.utf8.contains(0) else { throw AnyEngineError.invalidOperation(key) }
        }
        guard payload.count <= 65536, observed.count <= 256,
              observed.allSatisfy(Self.validClaimID) else {
            throw AnyEngineError.invalidOperation("payload or observed bounds")
        }
        if kind == .remove {
            guard payload.isEmpty, providerID.isEmpty, canonicalRef.isEmpty, !observed.isEmpty else {
                throw AnyEngineError.invalidOperation("remove shape")
            }
        } else {
            guard !payload.isEmpty else { throw AnyEngineError.invalidOperation("empty payload") }
            if kind == .replace && observed.isEmpty {
                throw AnyEngineError.invalidOperation("replace requires predecessors")
            }
            if kind == .add && !observed.isEmpty {
                throw AnyEngineError.invalidOperation("add cannot observe predecessors")
            }
        }
        self.version = 1
        self.operationID = operationID
        self.spaceID = spaceID
        self.authorID = authorID
        self.kind = kind
        self.targetObjectID = targetObjectID
        self.targetBlockID = targetBlockID
        self.providerID = providerID
        self.canonicalRef = canonicalRef
        self.payload = payload
        self.observed = Array(Set(observed)).sorted { Array($0.utf8).lexicographicallyPrecedes(Array($1.utf8)) }
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case version, operationID, spaceID, authorID, kind, targetObjectID, targetBlockID
        case providerID, canonicalRef, payload, observed
    }
    private struct RawKey: CodingKey {
        let stringValue: String
        let intValue: Int? = nil
        init(stringValue: String) { self.stringValue = stringValue }
        init?(intValue: Int) { return nil }
    }

    public init(from decoder: any Decoder) throws {
        let raw = try decoder.container(keyedBy: RawKey.self)
        guard Set(raw.allKeys.map(\.stringValue)) == Set(CodingKeys.allCases.map(\.rawValue)) else {
            throw AnyEngineError.invalidOperation("unknown or missing encoded operation field")
        }
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard try c.decode(UInt32.self, forKey: .version) == 1 else {
            throw AnyEngineError.invalidOperation("unsupported operation version")
        }
        let observed = try c.decode([String].self, forKey: .observed)
        try self.init(
            operationID: c.decode(String.self, forKey: .operationID),
            spaceID: c.decode(String.self, forKey: .spaceID),
            authorID: c.decode(String.self, forKey: .authorID),
            kind: c.decode(Kind.self, forKey: .kind),
            targetObjectID: c.decode(String.self, forKey: .targetObjectID),
            targetBlockID: c.decode(String.self, forKey: .targetBlockID),
            providerID: c.decode(String.self, forKey: .providerID),
            canonicalRef: c.decode(String.self, forKey: .canonicalRef),
            payload: c.decode(Data.self, forKey: .payload), observed: observed)
        guard observed == self.observed else {
            throw AnyEngineError.invalidOperation("noncanonical encoded observed set")
        }
    }

    public var canonicalBytes: Data {
        var data = Data("pinkha-t2-operation".utf8)
        data.append(0)
        Self.appendUInt32(version, to: &data)
        for value in [spaceID, operationID, authorID, kind.rawValue,
                      targetObjectID, targetBlockID, providerID, canonicalRef] {
            Self.appendBytes(Data(value.utf8), to: &data)
        }
        Self.appendBytes(payload, to: &data)
        Self.appendUInt32(UInt32(observed.count), to: &data)
        for value in observed { Self.appendBytes(Data(value.utf8), to: &data) }
        return data
    }

    public var logicalKey: String {
        var data = Data("pinkha-t2-operation-key-v1".utf8)
        data.append(0)
        Self.appendBytes(Data(spaceID.utf8), to: &data)
        Self.appendBytes(Data(operationID.utf8), to: &data)
        return AnyContentDigest.sha256(data)
    }
    public var contentHash: String { AnyContentDigest.sha256(canonicalBytes) }
    public var claimID: String { logicalKey + "/" + contentHash }
    /// Any record IDs forbid slash. This reversible storage encoding is 128 hex bytes.
    public var recordID: String { logicalKey + contentHash }

    public var fields: AnyJSON {
        .object([
            "version": .integer(Int64(version)), "operationId": .string(operationID),
            "spaceId": .string(spaceID), "authorId": .string(authorID),
            "kind": .string(kind.rawValue), "targetObjectId": .string(targetObjectID),
            "targetBlockId": .string(targetBlockID), "providerId": .string(providerID),
            "canonicalRef": .string(canonicalRef), "payload": .string(payload.base64EncodedString()),
            "observed": .array(observed.map(AnyJSON.string)),
            "logicalKey": .string(logicalKey), "contentHash": .string(contentHash)
        ])
    }

    public static func fromRecord(_ record: AnyJSON, expectedSpaceID: String) throws -> Self {
        guard record["version"]?.integer == 1,
              let kind = Kind(rawValue: try record.requireString("kind")),
              let payload = Data(base64Encoded: try record.requireString("payload")),
              let observedJSON = record["observed"]?.array else {
            throw AnyEngineError.invalidClaim("unsupported or malformed record")
        }
        let observed = try observedJSON.map { value -> String in
            guard let s = value.string else { throw AnyEngineError.invalidClaim("observed") }
            return s
        }
        let operation = try Self(
            operationID: record.requireString("operationId"),
            spaceID: record.requireString("spaceId"), authorID: record.requireString("authorId"),
            kind: kind, targetObjectID: record.requireString("targetObjectId"),
            targetBlockID: record.requireString("targetBlockId"),
            providerID: record.requireString("providerId"), canonicalRef: record.requireString("canonicalRef"),
            payload: payload, observed: observed
        )
        guard operation.spaceID == expectedSpaceID,
              observed == operation.observed,
              record["payload"]?.string == payload.base64EncodedString(),
              record["logicalKey"]?.string == operation.logicalKey,
              record["contentHash"]?.string == operation.contentHash,
              let id = record["id"]?.string,
              id.split(separator: "/").last.map(String.init) == operation.recordID else {
            throw AnyEngineError.invalidClaim("identity, space or canonical encoding mismatch")
        }
        return operation
    }

    private static func appendUInt32(_ value: UInt32, to data: inout Data) {
        data.append(contentsOf: [UInt8((value >> 24) & 255), UInt8((value >> 16) & 255),
                                UInt8((value >> 8) & 255), UInt8(value & 255)])
    }
    private static func appendBytes(_ value: Data, to data: inout Data) {
        appendUInt32(UInt32(value.count), to: &data)
        data.append(value)
    }
    private static func hex(_ value: String, count: Int) -> Bool {
        value.utf8.count == count && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    private static func validClaimID(_ value: String) -> Bool {
        let parts = value.split(separator: "/", omittingEmptySubsequences: false)
        return parts.count == 2 && parts.allSatisfy { hex(String($0), count: 64) }
    }
}

public struct AnyTorahClaim: Equatable, Sendable {
    public let operation: AnyTorahOperation
    public let creator: String
    public var id: String { operation.claimID }

    public init(operation: AnyTorahOperation, creator: String) throws {
        guard creator == operation.authorID, !creator.isEmpty else {
            throw AnyEngineError.invalidClaim("native creator differs from canonical author")
        }
        self.operation = operation
        self.creator = creator
    }
}

/// Complete bounded snapshot. Conflicts quarantine every variant before any
/// tombstone is folded, including a variant naming another target.
public struct AnyTorahProjection: Equatable, Sendable {
    public let all: [AnyTorahClaim]
    public let live: [AnyTorahClaim]
    public let conflicts: [String: [AnyTorahClaim]]
    public let pendingObserved: [String]

    public init(claims: [AnyTorahClaim], limit: Int = 10000) throws {
        guard (1...10000).contains(limit), claims.count <= limit else { throw AnyEngineError.readLimit }
        var byID: [String: AnyTorahClaim] = [:]
        for claim in claims {
            if let prior = byID[claim.id], prior != claim { throw AnyEngineError.invalidClaim("hash collision") }
            byID[claim.id] = claim
        }
        let all = byID.values.sorted { $0.id < $1.id }
        guard Set(all.map { $0.operation.spaceID }).count <= 1 else {
            throw AnyEngineError.invalidClaim("mixed spaces")
        }
        let groups = Dictionary(grouping: all, by: { $0.operation.logicalKey })
        guard groups.values.allSatisfy({ $0.count <= 256 }) else { throw AnyEngineError.readLimit }
        let conflicts = groups.filter { $0.value.count > 1 }
        let accepted = all.filter { conflicts[$0.operation.logicalKey] == nil }
        var removed = Set<String>()
        var pending = Set<String>()
        let acceptedIDs = Set(accepted.map(\.id))
        for claim in accepted {
            let op = claim.operation
            for id in op.observed {
                if let predecessor = byID[id] {
                    guard predecessor.operation.targetObjectID == op.targetObjectID,
                          predecessor.operation.targetBlockID == op.targetBlockID else {
                        throw AnyEngineError.invalidClaim("cross-target predecessor")
                    }
                }
                // Missing predecessors stay effective when delivered later.
                removed.insert(id)
                if !acceptedIDs.contains(id) { pending.insert(id) }
            }
        }
        self.all = all
        self.conflicts = conflicts
        self.pendingObserved = pending.sorted()
        self.live = accepted.filter { $0.operation.kind != .remove && !removed.contains($0.id) }.sorted {
            if $0.operation.operationID != $1.operation.operationID {
                return $0.operation.operationID < $1.operation.operationID
            }
            return $0.id < $1.id
        }
    }
}
