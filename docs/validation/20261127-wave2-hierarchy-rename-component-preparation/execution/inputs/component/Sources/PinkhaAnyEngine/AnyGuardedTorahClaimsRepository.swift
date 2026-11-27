import Foundation

/// Explicit native module lane. Reads never install a bundle and no operation
/// falls back to the generic records adapter. The application must own the
/// engine lifetime and execute calls inside its account/run lease.
public actor AnyGuardedTorahClaimsRepository {
    public let client: AnyHTTPClient
    public let spaceID: String
    private var expectedRootID: String?
    private var appendTail: Task<Void, Never>?

    public init(client: AnyHTTPClient, spaceID: String) throws {
        guard !spaceID.isEmpty, spaceID.utf8.count <= 1024, !spaceID.utf8.contains(0) else {
            throw AnyEngineError.invalidIdentity("space")
        }
        self.client = client; self.spaceID = spaceID
    }

    public func verifyCapabilities() async throws -> AnyGuardedTorahCapabilities {
        try AnyGuardedTorahCapabilities(response: await client.requestJSON(
            method: "GET", path: ["v1", "pinkha", "capabilities"]))
    }

    public func install(
        authorize: @escaping @Sendable () async throws -> Void = {}
    ) async throws {
        _ = try await verifyCapabilities()
        let value = try await client.requestJSON(
            method: "POST", path: base + ["pinkha", "install"], authorize: authorize)
        guard value["contract"]?.string == AnyGuardedTorahCapabilities.contract,
              value["bundleId"]?.string == AnyGuardedTorahCapabilities.bundleID,
              value["dataset"]?.string == AnyGuardedTorahCapabilities.dataset,
              value["module"]?.string == AnyGuardedTorahCapabilities.module else {
            throw AnyEngineError.incompatibleSchema("native install")
        }
        let root = try value.requireString("rootObjectId")
        try acceptRoot(root)
        guard try await storageRoot() == root else {
            throw AnyEngineError.incompatibleSchema("native install root")
        }
        try await authorize()
    }

    public func readSnapshot(limit: Int = 10000) async throws -> AnyGuardedTorahSnapshot {
        guard (1...10000).contains(limit) else { throw AnyEngineError.readLimit }
        _ = try await verifyCapabilities()
        let root = try await storageRoot()
        let response = try await client.requestJSON(
            method: "GET", path: base + ["pinkha", "claims"], query: ["limit": String(limit)],
            maximumResponseBytes: AnyGuardedTorahCapabilities.maximumBytes)
        return try AnyGuardedTorahSnapshot(
            response: response, expectedSpaceID: spaceID, expectedRootObjectID: root, limit: limit)
    }

    public func snapshot(limit: Int = 10000) async throws -> AnyTorahProjection {
        try await readSnapshot(limit: limit).projection
    }


    public func readObjectSnapshot(
        objectID: String, limit: Int = 10000
    ) async throws -> AnyGuardedTorahObjectSnapshot {
        try AnyGuardedTorahObjectSnapshot.validateObjectID(objectID)
        guard (1...10000).contains(limit) else { throw AnyEngineError.readLimit }
        let capabilities = try await verifyCapabilities()
        guard capabilities.nativeObjectClaimsSnapshot else {
            throw AnyEngineError.incompatibleSchema("nativeObjectClaimsSnapshot")
        }
        let root = try await storageRoot()
        let response = try await client.requestJSON(method: "GET",
            path: base + ["pinkha", "objects", objectID, "claims"], query: ["limit": String(limit)],
            maximumResponseBytes: AnyGuardedTorahCapabilities.maximumBytes)
        return try .init(response: response, expectedSpaceID: spaceID,
                         expectedRootObjectID: root, expectedObjectID: objectID, limit: limit)
    }

    public func append(
        _ operation: AnyTorahOperation,
        authorize: @escaping @Sendable () async throws -> Void = {}
    ) async throws -> AnyTorahAppendResult {
        let previous = appendTail
        let pending = Task {
            if let previous { await previous.value }
            try Task.checkCancellation()
            return try await self.performAppend(operation, authorize: authorize)
        }
        appendTail = Task { _ = try? await pending.value }
        return try await withTaskCancellationHandler {
            try await pending.value
        } onCancel: { pending.cancel() }
    }

    private var base: [String] { ["v1", "spaces", spaceID] }

    func storageRoot() async throws -> String {
        let value = try await client.requestJSON(
            method: "GET", path: base + ["bundles", AnyGuardedTorahCapabilities.bundleID])
        guard let bundle = value["bundle"], bundle["derived"]?.bool == true,
              bundle["losers"]?.array?.isEmpty != false else {
            throw AnyEngineError.incompatibleSchema("existing native bundle")
        }
        let root = try bundle.requireString("rootId")
        try acceptRoot(root)
        return root
    }

    private func acceptRoot(_ root: String) throws {
        guard !root.isEmpty, root.utf8.count <= 1024, !root.utf8.contains(0),
              expectedRootID == nil || expectedRootID == root else {
            throw AnyEngineError.incompatibleSchema("native root changed")
        }
        expectedRootID = root
    }

    private func performAppend(
        _ operation: AnyTorahOperation, authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyTorahAppendResult {
        guard operation.spaceID == spaceID, operation.authorID == client.expectedAccountID else {
            throw AnyEngineError.invalidOperation("native account or space")
        }
        let validated = try AnyTorahOperation(
            operationID: operation.operationID, spaceID: operation.spaceID,
            authorID: operation.authorID, kind: operation.kind,
            targetObjectID: operation.targetObjectID, targetBlockID: operation.targetBlockID,
            providerID: operation.providerID, canonicalRef: operation.canonicalRef,
            payload: operation.payload, observed: operation.observed)
        guard validated == operation else { throw AnyEngineError.invalidOperation("noncanonical native operation") }
        try await authorize()
        // The object closure covers every predecessor/retry and every global
        // variant of its seeded keys. Native ValidateLocal performs the final
        // indexed space-wide check for a NEW operation key used on another
        // object, under its actual carrier/target/ACL storage guards.
        let before = try await readObjectSnapshot(objectID: operation.targetObjectID)
        let existing = before.projection.all.first { $0.id == operation.claimID }
        guard !before.projection.all.contains(where: {
            $0.operation.logicalKey == operation.logicalKey && $0.id != operation.claimID
        }) || existing != nil else { throw AnyEngineError.collision(operation.logicalKey) }
        if existing == nil {
            for id in operation.observed {
                guard let predecessor = before.projection.all.first(where: { $0.id == id }),
                      predecessor.operation.targetObjectID == operation.targetObjectID,
                      predecessor.operation.targetBlockID == operation.targetBlockID else {
                    throw AnyEngineError.invalidOperation("unknown or cross-target observed predecessor")
                }
            }
        }
        let response: AnyJSON
        do {
            // Even exact retries enter native authority checks. A client-side
            // preexisting row is not a substitute for current writer/target ACL.
            response = try await client.requestJSON(
                method: "POST", path: base + ["modify"],
                body: .object([
                    "objectId": .string(before.rootObjectID),
                    "dataset": .string(AnyGuardedTorahCapabilities.dataset),
                    "records": .array([.object([
                        "id": .string(operation.recordID), "upsert": .bool(true),
                        "ops": .array([.object(["type": .string("$set"), "value": operation.fields])])
                    ])])
                ]), authorize: authorize)
        } catch {
            if error as? AnyEngineError == .http(status: 409, code: "pinkha.ordered_operation_collision") {
                throw AnyEngineError.collision(operation.logicalKey)
            }
            // Definite server refusals stay refusals. Only an ambiguous
            // transport/write outcome can be reconciled as persisted data.
            guard error as? AnyEngineError == .writeUncertain else { throw error }
            if let after = try? await readObjectSnapshot(objectID: operation.targetObjectID),
               let claim = after.projection.all.first(where: { $0.id == operation.claimID }) {
                try await authorize()
                return .init(acknowledgment: .readbackAfterFailure, claim: claim, created: false,
                    conflicted: after.projection.conflicts[operation.logicalKey] != nil, changeID: nil)
            }
            throw error
        }
        guard response["recordIds"]?.array == [.string(operation.recordID)],
              let changeID = response["changeId"]?.string,
              response["versionId"]?.string != nil else {
            throw AnyEngineError.unverifiedWrite
        }
        let after = try await readObjectSnapshot(objectID: operation.targetObjectID)
        guard let exact = after.projection.all.first(where: { $0.id == operation.claimID }) else {
            throw AnyEngineError.unverifiedWrite
        }
        try await authorize()
        return .init(acknowledgment: existing == nil ? .nativeReply : .preexisting,
            claim: exact, created: existing == nil && !changeID.isEmpty,
            conflicted: after.projection.conflicts[operation.logicalKey] != nil,
            changeID: changeID.isEmpty ? nil : changeID)
    }
}
