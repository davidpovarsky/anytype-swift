
import Foundation
import PinkhaKit
import PinkhaAnyEngine

public enum AnyNativeIndexCoverage: String, Sendable, Equatable {
    case complete
    case unsupportedPayload = "incomplete-unsupported-payload"
    case conflictOrPending = "incomplete-conflict-or-pending"
}

public struct AnyNativeIndexReadiness: Sendable, Equatable {
    public let coverage: AnyNativeIndexCoverage
    public let generation: String
    public var complete: Bool { coverage == .complete }

    static func parse(_ value: AnyJSON, coverage: AnyNativeIndexCoverage) throws -> Self {
        guard value["version"]?.integer == 1,
              value["state"]?.string == (coverage == .complete ? "ready-local-snapshot" : "incomplete"),
              let generation = value["generation"]?.string, digest(generation) else {
            throw AnyEngineError.malformedResponse("native indexed readiness")
        }
        return .init(coverage: coverage, generation: generation)
    }
    static func digest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
}

public struct AnyNativeSourceQueryResult: Sendable {
    public let field: String
    public let identity: String
    public let objectIDs: [String]
    public let conflictedObjectIDs: [String]
    public let unsupportedClaimsPresent: Bool
    public let readiness: AnyNativeIndexReadiness
}

public struct AnyNativeRelatedTarget: Sendable, Equatable {
    public let target: TorahAssociationTarget
    public let contextItemIDs: [String]
    public let sourceQuoteItemIDs: [String]
    public let canSafelyUnlink: Bool
    public let semanticInputSHA256: String
}

public struct AnyNativeRelatedQueryResult: Sendable {
    public let identity: String
    public let targets: [AnyNativeRelatedTarget]
    public let conflictingTargets: [TorahAssociationTarget]
    public let unsupportedClaimsPresent: Bool
    public let readiness: AnyNativeIndexReadiness
}

public struct AnyNativeDerivedDocumentProperties: Sendable {
    public let objectID: String
    public let sourceIdentities: [String]
    public let topicIdentities: [String]
    public let wordIdentities: [String]
    /// Read-only native labels and original canonical records. Persistence never
    /// writes a rendered/decoded projection over opaque canonical operation data.
    public let labels: [String: AnyJSON]
    public let records: [AnyJSON]
    public let inputSHA256: String
    public let readiness: AnyNativeIndexReadiness
}

/// Reads the native indexed handler. It never scans the entire claims dataset or
/// falls back to stock generic queries when native coverage/version is missing.
public struct AnyGuardedTorahIndex: Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient
    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard client.expectedAccountID == workspace.accountID else { throw AnyEngineError.accountChanged }
        self.client = client; self.workspace = workspace
    }

    public func documents(with item: TorahAssociationItem, limit: Int = 1000) async throws -> AnyNativeSourceQueryResult {
        guard !item.canonicalKey.hasPrefix("anytype-note:") else {
            throw AnyEngineError.invalidIdentity("internal Note is not an external source")
        }
        let field: String
        switch item.kind {
        case .ref: field = "pinkhaSources"
        case .topic: field = "pinkhaTopics"
        case .word: field = "pinkhaWords"
        }
        let identity = TorahDerivedQueryProjection.identity(item)
        try validate(identity: identity, limit: limit)
        try await requireCapability("nativeIndexedSourceQuery")
        let value = try await client.requestJSON(method: "GET", path: base + ["sources"],
            query: ["field": field, "identity": identity, "limit": String(limit)],
            maximumResponseBytes: 16_777_216)
        return try Self.parseSources(value, field: field, identity: identity, limit: limit)
    }

    public func related(to source: T5SourceIdentity, limit: Int = 1000) async throws -> AnyNativeRelatedQueryResult {
        guard !source.canonicalReference.hasPrefix("anytype-note:") else {
            throw AnyEngineError.invalidIdentity("internal Note is not an external source")
        }
        let identity = source.indexValue
        try validate(identity: identity, limit: limit)
        try await requireCapability("nativeRelatedVersion")
        let value = try await client.requestJSON(method: "GET", path: base + ["related"],
            query: ["identity": identity, "limit": String(limit)], maximumResponseBytes: 16_777_216)
        return try Self.parseRelated(value, workspace: workspace, identity: identity, limit: limit)
    }

    public func documentProperties(objectID: String) async throws -> AnyNativeDerivedDocumentProperties {
        guard Self.validNativeID(objectID) else { throw AnyEngineError.invalidIdentity("derived target") }
        try await requireCapability("nativeDocumentProperties")
        let value = try await client.requestJSON(method: "GET", path: base + ["targets", objectID],
            query: ["limit": "10000"], maximumResponseBytes: 16_777_216)
        guard value["contract"]?.string == "pinkha-torah-native-v1",
              value["target"]?["objectId"]?.string == objectID,
              value["target"]?["blockId"] == nil || value["target"]?["blockId"]?.string == "",
              let semantic = value["semantic"], semantic["version"]?.integer == 1,
              let coverage = semantic["coverage"]?.string.flatMap(AnyNativeIndexCoverage.init(rawValue:)),
              let hash = semantic["inputSHA256"]?.string, AnyNativeIndexReadiness.digest(hash),
              let labels = semantic["labels"]?.object, labels.count <= 10_000,
              let records = semantic["records"]?.array, records.count <= 10_000,
              let readiness = value["readiness"] else { throw AnyEngineError.malformedResponse("native derived properties") }
        return try .init(objectID: objectID,
            sourceIdentities: Self.stringList(semantic["sources"], maximum: 10_000),
            topicIdentities: Self.stringList(semantic["topics"], maximum: 10_000),
            wordIdentities: Self.stringList(semantic["words"], maximum: 10_000),
            labels: labels, records: records, inputSHA256: hash,
            readiness: .parse(readiness, coverage: coverage))
    }

    static func parseSources(_ value: AnyJSON, field: String, identity: String, limit: Int) throws -> AnyNativeSourceQueryResult {
        let (coverage, unsupported, readiness) = try header(value, identity: identity)
        guard value["field"]?.string == field else { throw AnyEngineError.malformedResponse("native source field") }
        let ids = try nativeIDs(value["objectIds"], maximum: limit)
        let conflicts = try nativeIDs(value["conflictedObjectIds"], maximum: limit)
        guard Set(ids).isDisjoint(with: Set(conflicts)), ids.count + conflicts.count <= limit,
              coverage != .complete || (!unsupported && conflicts.isEmpty) else {
            throw AnyEngineError.malformedResponse("native source coverage")
        }
        return .init(field: field, identity: identity, objectIDs: ids, conflictedObjectIDs: conflicts,
                     unsupportedClaimsPresent: unsupported, readiness: readiness)
    }

    static func parseRelated(_ value: AnyJSON, workspace: AnyTorahWorkspace, identity: String, limit: Int) throws -> AnyNativeRelatedQueryResult {
        let (coverage, unsupported, readiness) = try header(value, identity: identity)
        guard value["version"]?.integer == 1, let raw = value["targets"]?.array,
              let rawConflicts = value["conflictingTargets"]?.array,
              raw.count + rawConflicts.count <= limit else { throw AnyEngineError.malformedResponse("native related version/window") }
        var targets: [AnyNativeRelatedTarget] = []
        var seen = Set<TorahAssociationTarget>()
        for row in raw {
            guard row["spaceId"]?.string == workspace.spaceID else {
                throw TorahAssociationRepositoryError.targetOutsideSpace
            }
            let target = try Self.target(row, emptyBlockAllowed: false)
            let contexts = try stringList(row["contextItemIds"], maximum: 10_000)
            let quotes = try stringList(row["sourceQuoteItemIds"], maximum: 10_000)
            guard seen.insert(target).inserted, !contexts.isEmpty || !quotes.isEmpty,
                  Set(contexts).isDisjoint(with: Set(quotes)),
                  let unlink = row["canSafelyUnlink"]?.bool,
                  !unlink || (target.blockId == nil && !contexts.isEmpty && quotes.isEmpty),
                  let hash = row["semanticInputSHA256"]?.string, AnyNativeIndexReadiness.digest(hash) else {
                throw AnyEngineError.malformedResponse("native related target")
            }
            targets.append(.init(target: target, contextItemIDs: contexts, sourceQuoteItemIDs: quotes,
                                 canSafelyUnlink: unlink, semanticInputSHA256: hash))
        }
        var conflicts: [TorahAssociationTarget] = []
        for row in rawConflicts {
            let conflict = try target(row, emptyBlockAllowed: true)
            guard seen.insert(conflict).inserted else { throw AnyEngineError.malformedResponse("native related duplicate conflict") }
            conflicts.append(conflict)
        }
        guard coverage != .complete || (!unsupported && conflicts.isEmpty) else {
            throw AnyEngineError.malformedResponse("native related coverage")
        }
        return .init(identity: identity, targets: targets, conflictingTargets: conflicts,
                     unsupportedClaimsPresent: unsupported, readiness: readiness)
    }

    private func requireCapability(_ key: String) async throws {
        let value = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"])
        guard value["contract"]?.string == "pinkha-torah-native-v1", value[key]?.integer == 1,
              value["nativeSemanticPayload"]?.string == "canonical-associations-v2-single-record",
              ["nativeSignedClaims", "spaceWideOperationConflictDomain", "currentACLCommitFence", "targetTreeCommitFence"]
                .allSatisfy({ value[$0]?.integer == 1 }) else {
            throw AnyEngineError.incompatibleSchema("native indexed capability " + key)
        }
    }
    private var base: [String] { ["v1", "spaces", workspace.spaceID, "pinkha"] }
    private func validate(identity: String, limit: Int) throws {
        guard (1...1000).contains(limit), !identity.isEmpty, identity.utf8.count <= 4096,
              !identity.utf8.contains(0) else { throw AnyEngineError.invalidIdentity("native index query bounds") }
    }
    private static func header(_ value: AnyJSON, identity: String) throws -> (AnyNativeIndexCoverage, Bool, AnyNativeIndexReadiness) {
        guard value["contract"]?.string == "pinkha-torah-native-v1",
              value["identity"]?.string == identity,
              let coverage = value["coverage"]?.string.flatMap(AnyNativeIndexCoverage.init(rawValue:)),
              let unsupported = value["unsupportedClaimsPresent"]?.bool,
              coverage != .unsupportedPayload || unsupported,
              let readiness = value["readiness"] else { throw AnyEngineError.malformedResponse("native index envelope") }
        return (coverage, unsupported, try .parse(readiness, coverage: coverage))
    }
    private static func target(_ value: AnyJSON, emptyBlockAllowed: Bool) throws -> TorahAssociationTarget {
        guard let object = value["objectId"]?.string, validNativeID(object) else {
            throw AnyEngineError.malformedResponse("native related object identity")
        }
        guard let rawBlock = value["blockId"] else { return .object(objectId: object) }
        guard let block = rawBlock.string else { throw AnyEngineError.malformedResponse("native related block identity") }
        if emptyBlockAllowed && block.isEmpty { return .object(objectId: object) }
        guard validNativeID(block) else { throw AnyEngineError.malformedResponse("native related block identity") }
        return .block(objectId: object, blockId: block)
    }
    private static func nativeIDs(_ value: AnyJSON?, maximum: Int) throws -> [String] {
        let values = try stringList(value, maximum: maximum)
        guard values.allSatisfy(validNativeID) else { throw AnyEngineError.malformedResponse("native object IDs") }
        return values
    }
    private static func stringList(_ value: AnyJSON?, maximum: Int) throws -> [String] {
        guard let raw = value?.array, raw.count <= maximum else { throw AnyEngineError.readLimit }
        let values = raw.compactMap(\.string)
        guard values.count == raw.count, Set(values).count == values.count,
              values.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 16_384 && !$0.utf8.contains(0) }) else {
            throw AnyEngineError.malformedResponse("native index strings")
        }
        return values
    }
    private static func validNativeID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1024 && value.utf8.allSatisfy { $0 >= 33 && $0 <= 126 }
    }
}
