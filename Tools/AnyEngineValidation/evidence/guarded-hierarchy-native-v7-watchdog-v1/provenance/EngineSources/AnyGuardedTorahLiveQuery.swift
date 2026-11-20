import Foundation

protocol AnyGuardedWatchSnapshot: Sendable {
    var readinessGeneration: String { get }
    var projection: AnyTorahProjection { get }
    var provenance: [String: AnyGuardedClaimProvenance] { get }
    func sameState(as other: Self) -> Bool
}
extension AnyGuardedTorahSnapshot: AnyGuardedWatchSnapshot {
    func sameState(as other: Self) -> Bool {
        projection == other.projection && provenance == other.provenance
    }
}
extension AnyGuardedTorahObjectSnapshot: AnyGuardedWatchSnapshot {
    func sameState(as other: Self) -> Bool {
        projection == other.projection && provenance == other.provenance
            && reachableClaimBlockIDs == other.reachableClaimBlockIDs
            && targetObjectID == other.targetObjectID
    }
}

/// Native watch events are full states, never deltas or every-operation logs.
/// Both scopes share the same bounded framing and monotonic immutable history.
struct AnyGuardedSnapshotWatchWindow<Snapshot: AnyGuardedWatchSnapshot> {
    private let decode: @Sendable (AnyJSON) throws -> Snapshot
    private var previous: Snapshot?
    init(decode: @escaping @Sendable (AnyJSON) throws -> Snapshot) { self.decode = decode }

    mutating func apply(_ frame: AnySSEFrame) throws -> (snapshot: Snapshot, initial: Bool)? {
        if frame.event == "error" { throw AnyLiveQueryError.closed("native snapshot unavailable") }
        guard frame.event == "snapshot" else {
            throw AnyLiveQueryError.invalidEvent("native full snapshot required")
        }
        guard frame.data.count <= AnyGuardedTorahCapabilities.maximumBytes else {
            throw AnyLiveQueryError.windowTooLarge
        }
        let next = try decode(JSONDecoder().decode(AnyJSON.self, from: frame.data))
        guard frame.id == next.readinessGeneration else {
            throw AnyLiveQueryError.invalidSequence("native readiness event ID")
        }
        if let previous {
            let current = Dictionary(uniqueKeysWithValues: next.projection.all.map { ($0.id, $0) })
            guard previous.projection.all.allSatisfy({ current[$0.id] == $0 }) else {
                throw AnyEngineError.invalidClaim("an immutable native claim disappeared or changed")
            }
            if previous.readinessGeneration == next.readinessGeneration {
                guard previous.sameState(as: next) else {
                    throw AnyLiveQueryError.invalidSequence("native generation reused for different state")
                }
                return nil
            }
        }
        let initial = previous == nil
        previous = next
        return (next, initial)
    }
}

/// Kept as the explicit full-workspace window for diagnostics/migration callers.
struct AnyGuardedTorahWatchWindow {
    private var window: AnyGuardedSnapshotWatchWindow<AnyGuardedTorahSnapshot>
    init(spaceID: String, rootID: String, limit: Int) {
        window = .init { try .init(response: $0, expectedSpaceID: spaceID,
                                  expectedRootObjectID: rootID, limit: limit) }
    }
    mutating func apply(_ frame: AnySSEFrame) throws -> (snapshot: AnyGuardedTorahSnapshot, initial: Bool)? {
        try window.apply(frame)
    }
}

struct AnyGuardedTorahObjectWatchWindow {
    private var window: AnyGuardedSnapshotWatchWindow<AnyGuardedTorahObjectSnapshot>
    init(spaceID: String, rootID: String, objectID: String, limit: Int) {
        window = .init { try .init(response: $0, expectedSpaceID: spaceID,
                                  expectedRootObjectID: rootID, expectedObjectID: objectID, limit: limit) }
    }
    mutating func apply(_ frame: AnySSEFrame) throws -> (snapshot: AnyGuardedTorahObjectSnapshot, initial: Bool)? {
        try window.apply(frame)
    }
}

extension AnyGuardedTorahClaimsRepository {
    public func watch(
        session: AnyStreamSession, limit: Int = 10000
    ) async throws -> AsyncThrowingStream<AnyTorahLiveSnapshot, Error> {
        guard (1...10000).contains(limit) else { throw AnyEngineError.readLimit }
        _ = try await verifyCapabilities()
        let root = try await storageRoot()
        let spaceID = self.spaceID
        return try await nativeWatch(path: ["v1", "spaces", spaceID, "pinkha", "claims", "subscribe"],
            session: session, limit: limit,
            decode: { try AnyGuardedTorahSnapshot(response: $0, expectedSpaceID: spaceID,
                                                 expectedRootObjectID: root, limit: limit) },
            update: { .init(generation: $0, projection: $1.projection, initial: $2) })
    }

    public func watchObject(
        objectID: String, session: AnyStreamSession, limit: Int = 10000
    ) async throws -> AsyncThrowingStream<AnyGuardedTorahObjectLiveSnapshot, Error> {
        try AnyGuardedTorahObjectSnapshot.validateObjectID(objectID)
        guard (1...10000).contains(limit) else { throw AnyEngineError.readLimit }
        let capabilities = try await verifyCapabilities()
        guard capabilities.nativeObjectClaimsSnapshot, capabilities.nativeObjectClaimsWatch else {
            throw AnyEngineError.incompatibleSchema("nativeObjectClaimsSnapshot/nativeObjectClaimsWatch")
        }
        let root = try await storageRoot()
        let spaceID = self.spaceID
        return try await nativeWatch(
            path: ["v1", "spaces", spaceID, "pinkha", "objects", objectID, "claims", "subscribe"],
            session: session, limit: limit,
            decode: { try AnyGuardedTorahObjectSnapshot(response: $0, expectedSpaceID: spaceID,
                expectedRootObjectID: root, expectedObjectID: objectID, limit: limit) },
            update: { .init(generation: $0, snapshot: $1, initial: $2) })
    }

    private func nativeWatch<Snapshot: AnyGuardedWatchSnapshot, Update: Sendable>(
        path: [String], session: AnyStreamSession, limit: Int,
        decode: @escaping @Sendable (AnyJSON) throws -> Snapshot,
        update: @escaping @Sendable (UUID, Snapshot, Bool) -> Update
    ) async throws -> AsyncThrowingStream<Update, Error> {
        let generation = session.generation
        let frames = try await client.subscribeFrames(method: "GET", path: path,
            query: ["limit": String(limit)], streamSession: session,
            maximumFrameBytes: AnyGuardedTorahCapabilities.maximumBytes + 1024)
        return AsyncThrowingStream(bufferingPolicy: .bufferingOldest(2)) { continuation in
            let worker = Task {
                do {
                    var window = AnyGuardedSnapshotWatchWindow(decode: decode)
                    for try await frame in frames {
                        try Task.checkCancellation()
                        try await session.requireActive(generation: generation)
                        guard let value = try window.apply(frame) else { continue }
                        try await session.requireActive(generation: generation)
                        switch continuation.yield(update(generation, value.snapshot, value.initial)) {
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
}
