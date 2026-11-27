import Foundation

public struct AnyTorahLiveSnapshot: Sendable {
    public let generation: UUID
    public let projection: AnyTorahProjection
    public let initial: Bool
    public init(generation: UUID, projection: AnyTorahProjection, initial: Bool) {
        self.generation = generation
        self.projection = projection
        self.initial = initial
    }
}

extension AnyTorahClaimsRepository {
    /// Reads an existing, verified bundle; it never installs a declaration.
    /// A terminal error invalidates this view. Reopen to receive a fresh atomic
    /// snapshot; never resume from an old versionId or keep applying deltas.
    public func watch(
        session: AnyStreamSession, limit: Int = 10000
    ) async throws -> AsyncThrowingStream<AnyTorahLiveSnapshot, Error> {
        guard (1...10000).contains(limit) else { throw AnyEngineError.readLimit }
        let location = try await storageLocation()
        let spaceID = self.spaceID
        let upstream = try await client.subscribeQuery(
            spaceID: spaceID,
            query: .object([
                "objectId": .string(location.root), "dataset": .string(location.collection),
                "sort": .array([.string("id")]), "limit": .integer(Int64(limit + 1)),
                "includeTotal": .bool(true), "mailboxCapacity": .integer(128)
            ]),
            streamSession: session, maximumRecords: limit, requireComplete: true)
        return AsyncThrowingStream(bufferingPolicy: .bufferingOldest(2)) { continuation in
            let worker = Task {
                do {
                    for try await update in upstream {
                        try Task.checkCancellation()
                        try await session.requireActive(generation: update.generation)
                        guard update.removed.isEmpty else {
                            throw AnyEngineError.invalidClaim("an append-only claim disappeared")
                        }
                        let projection = try Self.project(
                            records: update.records, spaceID: spaceID, rootID: location.root, limit: limit)
                        try await session.requireActive(generation: update.generation)
                        let next = AnyTorahLiveSnapshot(
                            generation: update.generation, projection: projection, initial: update.initial)
                        switch continuation.yield(next) {
                        case .enqueued: break
                        case .dropped: throw AnyLiveQueryError.bufferOverflow
                        case .terminated: throw CancellationError()
                        @unknown default: throw AnyLiveQueryError.bufferOverflow
                        }
                    }
                    throw AnyLiveQueryError.disconnected
                } catch { continuation.finish(throwing: error) }
            }
            continuation.onTermination = { @Sendable _ in worker.cancel() }
        }
    }

    nonisolated static func project(
        records: [AnyJSON], spaceID: String, rootID: String, limit: Int
    ) throws -> AnyTorahProjection {
        let claims = try records.map { record -> AnyTorahClaim in
            guard record["_objectId"]?.string == rootID else {
                throw AnyEngineError.invalidClaim("record belongs to another root")
            }
            let operation = try AnyTorahOperation.fromRecord(record, expectedSpaceID: spaceID)
            guard record["id"]?.string == rootID + "/" + operation.recordID else {
                throw AnyEngineError.invalidClaim("shared record ID disagrees with its owner")
            }
            return try AnyTorahClaim(operation: operation, creator: record.requireString("creator"))
        }
        return try AnyTorahProjection(claims: claims, limit: limit)
    }
}
