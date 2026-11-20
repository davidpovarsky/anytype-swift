import Foundation

public struct AnyTorahAppendResult: Sendable {
    public enum Acknowledgment: String, Sendable { case nativeReply, preexisting, readbackAfterFailure }
    public let acknowledgment: Acknowledgment
    public let claim: AnyTorahClaim
    public let created: Bool
    public let conflicted: Bool
    /// Native write acknowledgment, absent when recovery had to prove persisted state.
    /// This is not an independently verified signed ACL receipt.
    public let changeID: String?
}

public enum AnyTorahSchema {
    public static let bundleID = "pinkha.torah.operations/v1"
    public static let datasetKey = "claims"

    public static var fields: [AnyJSON] {
        let keys = ["operationId", "spaceId", "authorId", "kind", "targetObjectId",
                    "targetBlockId", "providerId", "canonicalRef", "payload",
                    "logicalKey", "contentHash"]
        return keys.map { key in
            .object(["key": .string(key), "kind": .string("string"),
                     "required": .bool(true), "mutableBy": .string("never")])
        } + [
            .object(["key": .string("version"), "kind": .string("number"),
                     "required": .bool(true), "mutableBy": .string("never")]),
            .object(["key": .string("observed"), "kind": .string("array"),
                     "required": .bool(true), "mutableBy": .string("never"),
                     "shape": .object(["kind": .string("array"),
                                       "items": .object(["kind": .string("string")])])]),
            .object(["key": .string("creator"), "stamp": .string("creator")])
        ]
    }
    public static var indexes: [AnyJSON] {
        [
            .object(["key": .string("by_operation"), "fields": .array([.string("logicalKey")])]),
            .object(["key": .string("by_target"),
                     "fields": .array([.string("targetObjectId"), .string("targetBlockId")])]),
            .object(["key": .string("by_source"),
                     "fields": .array([.string("providerId"), .string("canonicalRef")])])
        ]
    }

    public static var bundle: AnyJSON {
        .object([
            "id": .string(bundleID), "name": .string("Pinkha Torah operations"),
            "derived": .bool(true), "hidden": .bool(true),
            "parts": .array([.object([
                "key": .string("operations"), "hidden": .bool(true),
                "datasets": .array([.object([
                    "key": .string(datasetKey), "idRule": .string("user"),
                    "idPattern": .string("^[0-9a-f]{128}$"), "idMaxLen": .integer(128),
                    "deleteBy": .string("none"), "shared": .bool(true),
                    "fields": .array(fields), "indexes": .array(indexes)
                ])])
            ])])
        ])
    }

    public static func verify(_ definition: AnyJSON, rootID: String) throws -> String {
        guard definition["key"]?.string == datasetKey,
              definition["module"]?.string == "records",
              definition["idRule"]?.string == "user",
              definition["idPattern"]?.string == "^[0-9a-f]{128}$",
              definition["idMaxLen"]?.integer == 128,
              definition["deleteBy"]?.string == "none",
              definition["shared"]?.bool == true,
              definition["dynamic"]?.bool != true,
              definition["invalid"]?.bool != true,
              let actual = definition["fields"]?.array,
              actual.count == fields.count else { throw AnyEngineError.incompatibleSchema("claim dataset") }
        for expected in fields {
            let key = try expected.requireString("key")
            guard let found = actual.first(where: { $0["key"]?.string == key }),
                  found["scope"]?.string != "local" && found["scope"]?.string != "account" else {
                throw AnyEngineError.incompatibleSchema("field " + key)
            }
            if let stamp = expected["stamp"] {
                guard found["stamp"] == stamp else { throw AnyEngineError.incompatibleSchema("creator stamp") }
            } else {
                guard found["kind"] == expected["kind"],
                      found["required"]?.bool == true,
                      found["mutableBy"]?.string == "never" else {
                    throw AnyEngineError.incompatibleSchema("immutable field " + key)
                }
                if let shape = expected["shape"], found["shape"] != shape {
                    throw AnyEngineError.incompatibleSchema("field shape " + key)
                }
            }
        }
        for expected in indexes {
            guard let found = definition["indexes"]?.array?.first(where: { $0["key"] == expected["key"] }),
                  found["fields"] == expected["fields"], found["invalid"]?.bool != true else {
                throw AnyEngineError.incompatibleSchema("declared index")
            }
        }
        let collection = try definition.requireString("collection")
        guard collection == rootID + "_" + datasetKey else {
            throw AnyEngineError.incompatibleSchema("collection owner")
        }
        return collection
    }
}

/// New-engine storage. It does not fall back to Heart or a local canonical JSON
/// file. Domain interpretation is downstream; CRDT storage remains Any's.
public actor AnyTorahClaimsRepository {
    public let client: AnyHTTPClient
    public let spaceID: String
    private var rootID: String?
    private var collection: String?
    private var appendTail: Task<Void, Never>?

    public init(client: AnyHTTPClient, spaceID: String) {
        self.client = client
        self.spaceID = spaceID
    }

    public func install() async throws {
        guard !spaceID.isEmpty else { throw AnyEngineError.invalidIdentity("space") }
        let response = try await client.requestJSON(
            method: "POST", path: base + ["bundles"], body: AnyTorahSchema.bundle)
        guard let bundle = response["bundle"],
              bundle["derived"]?.bool == true,
              bundle["losers"]?.array?.isEmpty != false else {
            throw AnyEngineError.incompatibleSchema("bundle root conflict")
        }
        let root = try bundle.requireString("rootId")
        let definitions = try await client.requestJSON(
            method: "GET", path: base + ["types", root, "datasets"])
        guard let def = definitions["datasets"]?.array?.first(where: {
            $0["key"]?.string == AnyTorahSchema.datasetKey
        }) else { throw AnyEngineError.incompatibleSchema("missing claims") }
        let name = try AnyTorahSchema.verify(def, rootID: root)
        rootID = root
        collection = name
    }

    public func snapshot(limit: Int = 10000) async throws -> AnyTorahProjection {
        guard (1...10000).contains(limit) else { throw AnyEngineError.readLimit }
        let location = try await ready()
        // One native read snapshot includes every logical variant. A target-only
        // query can hide a conflicting variant that names another object.
        let response = try await client.requestJSON(method: "POST", path: base + ["query"], body: .object([
            "objectId": .string(location.root), "dataset": .string(location.collection),
            "sort": .array([.string("id")]), "limit": .integer(Int64(limit + 1)),
            "includeTotal": .bool(true)
        ]))
        guard let records = response["records"]?.array,
              let total = response["total"]?.integer,
              let hasNext = response["hasNext"]?.bool else {
            throw AnyEngineError.malformedResponse("bounded snapshot metadata")
        }
        guard total >= 0, total <= Int64(limit), total == records.count,
              !hasNext, records.count <= limit else { throw AnyEngineError.readLimit }
        return try Self.project(records: records, spaceID: spaceID, rootID: location.root, limit: limit)
    }

    public func append(
        _ operation: AnyTorahOperation,
        authorize: @escaping @Sendable () async throws -> Void = {}
    ) async throws -> AnyTorahAppendResult {
        let previous = appendTail
        let task = Task {
            if let previous { await previous.value }
            try Task.checkCancellation()
            return try await self.performAppend(operation, authorize: authorize)
        }
        appendTail = Task { _ = try? await task.value }
        return try await withTaskCancellationHandler {
            try await task.value
        } onCancel: {
            task.cancel()
        }
    }

    public func storageLocation() async throws -> (root: String, collection: String) {
        try await ready()
    }

    private var base: [String] { ["v1", "spaces", spaceID] }

    private func ready() async throws -> (root: String, collection: String) {
        // Opening a reader never installs or heals a declaration.
        let response = try await client.requestJSON(
            method: "GET", path: base + ["bundles", AnyTorahSchema.bundleID])
        guard let bundle = response["bundle"], bundle["derived"]?.bool == true,
              bundle["losers"]?.array?.isEmpty != false else {
            throw AnyEngineError.incompatibleSchema("existing bundle root")
        }
        let root = try bundle.requireString("rootId")
        let definitions = try await client.requestJSON(
            method: "GET", path: base + ["types", root, "datasets"])
        guard let definition = definitions["datasets"]?.array?.first(where: {
            $0["key"]?.string == AnyTorahSchema.datasetKey
        }) else { throw AnyEngineError.incompatibleSchema("missing claims") }
        let name = try AnyTorahSchema.verify(definition, rootID: root)
        rootID = root
        collection = name
        return (root, name)
    }

    private func performAppend(
        _ operation: AnyTorahOperation, authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyTorahAppendResult {
        guard operation.spaceID == spaceID,
              operation.authorID == client.expectedAccountID,
              operation.version == 1 else { throw AnyEngineError.invalidOperation("account or space") }
        // Codable input is revalidated too; no alternate constructor bypasses bounds.
        let validated = try AnyTorahOperation(
            operationID: operation.operationID, spaceID: operation.spaceID,
            authorID: operation.authorID, kind: operation.kind,
            targetObjectID: operation.targetObjectID, targetBlockID: operation.targetBlockID,
            providerID: operation.providerID, canonicalRef: operation.canonicalRef,
            payload: operation.payload, observed: operation.observed)
        guard validated == operation else { throw AnyEngineError.invalidOperation("noncanonical operation") }
        try await authorize()
        let location = try await ready()
        let before = try await snapshot()
        if let exact = before.all.first(where: { $0.id == operation.claimID }) {
            return .init(acknowledgment: .preexisting, claim: exact, created: false,
                         conflicted: before.conflicts[operation.logicalKey] != nil, changeID: nil)
        }
        guard !before.all.contains(where: { $0.operation.logicalKey == operation.logicalKey }) else {
            throw AnyEngineError.collision(operation.logicalKey)
        }
        for id in operation.observed {
            guard let predecessor = before.all.first(where: { $0.id == id }),
                  predecessor.operation.targetObjectID == operation.targetObjectID,
                  predecessor.operation.targetBlockID == operation.targetBlockID else {
                throw AnyEngineError.invalidOperation("unknown or cross-target observed predecessor")
            }
        }
        let response: AnyJSON
        do {
            response = try await client.requestJSON(method: "POST", path: base + ["upsert"], body: .object([
                "objectId": .string(location.root), "dataset": .string(location.collection),
                "records": .array([.object(["id": .string(operation.recordID), "fields": operation.fields])]),
                "pageSize": .integer(1)
            ]), authorize: authorize)
        } catch {
            // Lost acknowledgment is not a reason to mint another operation ID.
            // A read proves persisted state; it cannot prove a native signed ACL receipt.
            if let after = try? await snapshot(),
               let exact = after.all.first(where: { $0.id == operation.claimID }) {
                return .init(acknowledgment: .readbackAfterFailure, claim: exact, created: false,
                             conflicted: after.conflicts[operation.logicalKey] != nil, changeID: nil)
            }
            throw error
        }
        let after = try await snapshot()
        guard let exact = after.all.first(where: { $0.id == operation.claimID }) else {
            throw AnyEngineError.unverifiedWrite
        }
        return .init(acknowledgment: .nativeReply, claim: exact, created: response["created"]?.integer == 1,
                     conflicted: after.conflicts[operation.logicalKey] != nil,
                     changeID: response["pages"]?.array?.first?["changeId"]?.string)
    }
}
